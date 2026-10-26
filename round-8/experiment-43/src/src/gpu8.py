#!/usr/bin/env python3
"""gpu8: the per-family GPU driver (S1 load/check/fit, S3 locate, S4 predict, S5 sweep, S6.1 instruct side).

Usage: gpu8.py <family> [stage,...]   family in gemma | llama | qwen; stages default to all, in order:
  tests, fit, select (llama only), locate, commit1, predict, commit2, sweep, base_instr (qwen only)
Every stage writes results/<stage>_<family or unit>.json and resumes from it; COMMIT #1/#2 refuse to overwrite.
A held-out family's COMMIT #2 precedes any of its sweep samples; families run gemma -> llama -> qwen.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger
from scipy.stats import fisher_exact

import engine8 as E
import locate8 as L8
import oc8
import predict8 as P8
from cfg8 import (CONTS, FAMILIES, INPUTS, LABELS, LLAMA_BENCH_KEEP, LLAMA_BENCH_ORDER, LLAMA_MINORITY_BAR,
                  LOG_DIR, N_FORCE, N_LOC, N_REFINE, NS_FORCE, NS_LOC, NS_REFINE, NS_SECOND, PRED_DIR, RESULTS_DIR,
                  SAMPLES_RAW, SECOND_SPAN, SRC, SRCS, SWEEP_SLOTS, FIT_SLOTS, TEMPLATES, TEMPS, THRESH,
                  TOPN_FORCE, TOPN_FORCE2, UNITS, append_jsonl, fit_seed, log_deviation, log_timing, read_json,
                  read_jsonl, seed8, setup_logging, sha256_file, sweep_seed, u_from_seed, utc_now, write_json)
from commit8 import commit, verify
from prompts8 import load_prompts

FIT_MAX_NEW = {"A3": 640, "B6": 384, "B3": 768}        # iteration-7 twin caps (the fit twin doubles as engine check)
CONT_BATCH = {"gemma": 64, "llama": 32, "qwen": 32}
STOP_CHECK = 8
COLLAPSED_QWEN = ("T1", "T10", "T2")


# ------------------------------------------------------------------------------------------------ labeller
class Labeller:
    def __init__(self) -> None:
        err = open(LOG_DIR / "label_server.err", "a")
        self.p = subprocess.Popen([sys.executable, str(SRC / "label8.py"), "--serve"], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=err, text=True, cwd=str(SRC), bufsize=1)

    def label(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return []
        out: list[dict[str, Any]] = []
        for i in range(0, len(rows), 200):
            chunk = rows[i:i + 200]
            self.p.stdin.write(json.dumps(chunk) + "\n")
            self.p.stdin.flush()
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError("label server died (see logs/label_server.err)")
            out.extend(json.loads(line))
        return out

    def close(self) -> None:
        try:
            self.p.stdin.close()
            self.p.wait(timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            self.p.kill()


def route(unit: str) -> str:
    return unit if unit in ("A3", "B3", "B6") else UNITS[unit]["task"]


def bench_catalogue(task: str) -> list[str]:
    for d in (INPUTS / "iter6_exp30" / "inputs" / "exp11" / "bench").iterdir():
        if d.name.startswith(task + "_"):
            spec = read_json(d / "spec.json")
            return [c["mode"] for c in spec["catalogue"]]
    return []


def unit_bins(unit: str, fit_labels: list[str] | None = None) -> list[str]:
    cat = list(UNITS[unit].get("catalogue") or bench_catalogue(UNITS[unit]["task"]))
    for l in fit_labels or []:
        if l not in cat and l not in ("other", "invalid", "disputed", "label_error"):
            cat.append(l)
    return cat + ["other", "invalid"]


def to_bin(label: str | None, bins: list[str]) -> str:
    if label in bins:
        return label
    return "invalid" if label in ("invalid", "no_code") else "other"


# ------------------------------------------------------------------------------------------------ runner
class Runner:
    def __init__(self, family: str) -> None:
        self.fam = family
        self.tok, self.model, self.info = E.load(family)
        self.prompts = load_prompts()
        self.lab = Labeller()
        self.nv = E.lm_rows(self.model)

    def close(self) -> None:
        self.lab.close()
        E.free(self.model)

    def decode(self, ids: list[int]) -> str:
        return self.tok.decode([t for t in ids if t < self.nv], skip_special_tokens=True)

    def P(self, unit: str, w: str) -> dict[str, Any]:
        return self.prompts[(unit, w)]

    # ---- coupled programs (fit, sweep)
    def programs(self, unit: str, arm: str, T: float, seeds: dict[tuple[str, int], int], max_new: int,
                 shadow_k: int = 0, top_k: int = 0) -> list[dict[str, Any]]:
        spec = UNITS[unit]
        B = spec["batch"]
        rows_out = []
        by_w: dict[str, list[int]] = {}
        for (w, s) in seeds:
            by_w.setdefault(w, []).append(s)
        for w, slots in by_w.items():
            slots = sorted(slots)
            Pw = self.P(unit, w)
            for b0 in range(0, len(slots), B):
                part = slots[b0:b0 + B]
                rows = [{"prompt_ids": Pw["ids"], "prefix_ids": [], "u": u_from_seed(seeds[(w, s)]), "T": T,
                         "top_k": top_k, "max_new": max_new} for s in part]
                t0 = time.time()
                outs = E.generate(self.model, self.tok, rows, coupled=True, fence_kind=spec["fence"],
                                  shadow_k=shadow_k)
                dt = time.time() - t0
                bid = f"{unit}:{arm}:{w}:T{T}:k{top_k}:{part[0]}-{part[-1]}"
                log_timing(arm, unit, len(part), dt, steps=max(o["n_tokens"] for o in outs), batch=len(part))
                for s, o in zip(part, outs):
                    rows_out.append({"sid": f"{unit}|{arm}|{w}|{s}|T{T}|k{top_k}", "unit": unit, "family": self.fam,
                                     "arm": arm, "template": w, "slot": s, "T": T, "top_k": top_k,
                                     "seed": seeds[(w, s)], "prompt_sha256": Pw["prompt_sha256"],
                                     "token_ids": o["token_ids"], "n_tokens": o["n_tokens"],
                                     "finish_reason": o["finish_reason"], "text": self.decode(o["token_ids"]),
                                     "shadow_div_step": o["shadow_div_step"], "shadow_tok": o["shadow_tok"],
                                     "batch_id": bid, "batch_B": len(part), "max_new": max_new,
                                     "engine_path": o["engine_path"], "utc": utc_now()})
        return rows_out

    def label_programs(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        lab = self.lab.label([{"sid": r["sid"], "unit": route(r["unit"]), "text": r["text"]} for r in rows])
        out = []
        for r, l in zip(rows, lab):
            out.append({"sid": r["sid"], "unit": r["unit"], "label": l.get("label"), "passed": bool(l.get("passed")),
                        "valid": bool(l.get("valid")), "labeller_source": l.get("labeller_source"),
                        "runtime_label": l.get("runtime_label"), "ast_label": l.get("ast_label")})
        return out

    # ---- free continuations (locator, forced tokens)
    def continuations(self, unit: str, jobs: list[dict[str, Any]], oc_ok: bool, bins: list[str]) -> list[str]:
        """Labelled continuations; a job whose deterministic cid (same prefix, same seed) is already in
        data/continuations.jsonl is reused instead of resampled (restarts cost nothing)."""
        if not hasattr(self, "_cache"):
            self._cache = {c["cid"]: c for c in read_jsonl(CONTS) if UNITS.get(c["unit"], {}).get("family") == self.fam}
        for j in jobs:                    # a cached row is valid only for the same prefix length and template
            c = self._cache.get(j["cid"])
            if c is not None and (c.get("prefix_len", len(j["prefix_ids"])) != len(j["prefix_ids"]) or
                                  c.get("w", j["w"]) != j["w"]):
                del self._cache[j["cid"]]
        cached = [j for j in jobs if j["cid"] in self._cache]
        for j in cached:
            c = self._cache[j["cid"]]
            j.update({"_new": c["new_ids"], "_finish": c["finish_reason"], "_oc": c["oc_label"],
                      "_label": to_bin(c["label"], bins)})
        todo = [j for j in jobs if j["cid"] not in self._cache]
        if todo:
            self._continuations_new(unit, todo, oc_ok, bins)
            for j in todo:
                self._cache[j["cid"]] = {"cid": j["cid"], "new_ids": j["_new"], "finish_reason": j["_finish"],
                                         "oc_label": j["_oc"], "label": j["_label"],
                                         "prefix_len": len(j["prefix_ids"]), "w": j["w"]}
        return [j["_label"] for j in jobs]

    def _continuations_new(self, unit: str, jobs: list[dict[str, Any]], oc_ok: bool, bins: list[str]) -> list[str]:
        spec = UNITS[unit]
        task = spec["task"]
        cap = getattr(self, "cont_cap", None)
        rows = [{"prompt_ids": self.P(unit, j["w"])["ids"], "prefix_ids": j["prefix_ids"],
                 "u": u_from_seed(j["seed"]), "T": 1.0, "top_k": 0,
                 "max_new": max(8, min(j["max_new"], cap) if cap else j["max_new"])} for j in jobs]

        def stop_fn(row: dict[str, Any], full: list[int]) -> bool:
            return oc8.classify(unit, task, self.decode(full)) != "undecided"
        t0 = time.time()
        outs = E.run_batches(self.model, self.tok, rows, CONT_BATCH[self.fam], coupled=False,
                             fence_kind=spec["fence"], stop_fn=stop_fn if oc_ok else None, check_every=STOP_CHECK)
        log_timing("continuations", unit, len(jobs), time.time() - t0, sub=jobs[0].get("stage") if jobs else None)
        labels: list[str | None] = [None] * len(jobs)
        need = []
        for i, (j, o) in enumerate(zip(jobs, outs)):
            full = list(j["prefix_ids"]) + o["token_ids"]
            text = self.decode(full)
            oc = oc8.classify(unit, task, text) if oc_ok else "undecided"
            j["_new"] = o["token_ids"]
            j["_finish"] = o["finish_reason"]
            j["_oc"] = oc
            if oc != "undecided":
                labels[i] = oc
            else:
                need.append(i)
        if need:
            lab = self.lab.label([{"sid": jobs[i]["cid"], "unit": route(unit),
                                   "text": self.decode(list(jobs[i]["prefix_ids"]) + jobs[i]["_new"])} for i in need])
            for i, l in zip(need, lab):
                labels[i] = l.get("label")
        rows_out = []
        for j, lab_ in zip(jobs, labels):
            b = to_bin(lab_, bins)
            j["_label"] = b
            rows_out.append({"cid": j["cid"], "unit": unit, "stage": j.get("stage"), "w": j["w"],
                             "prefix_len": len(j["prefix_ids"]), "seed": j["seed"], "new_ids": j["_new"],
                             "finish_reason": j["_finish"], "oc_label": j["_oc"], "label": b,
                             "meta": {k: v for k, v in j.items() if not k.startswith("_") and k not in
                                      ("prefix_ids", "cid", "w", "seed", "stage")}, "utc": utc_now()})
        append_jsonl(CONTS, rows_out)
        return [j["_label"] for j in jobs]

    # ---- teacher forcing
    def tf(self, unit: str, w: str, cont: list[int]) -> torch.Tensor:
        return E.teacher_force(self.model, self.P(unit, w)["ids"], cont)


# ------------------------------------------------------------------------------------------------ helpers
def label_map() -> dict[str, dict[str, Any]]:
    return {r["sid"]: r for r in read_jsonl(LABELS)}


def fit_programs(unit: str) -> list[dict[str, Any]]:
    labs = label_map()
    rows = [r for r in read_jsonl(SAMPLES_RAW) if r["unit"] == unit and r["arm"] == "fit"]
    bins = unit_bins(unit, [labs[r["sid"]]["label"] for r in rows if r["sid"] in labs])
    out = []
    for r in rows:
        lab = labs.get(r["sid"], {}).get("label")
        ids = [t for t in r["token_ids"] if t < 10 ** 9]
        stops = set(FAMILIES[r["family"]]["stop_ids"])
        while ids and ids[-1] in stops:
            ids = ids[:-1]
        out.append({"gen_ids": ids, "label": to_bin(lab, bins), "w": r["template"], "slot": r["slot"],
                    "passed": labs.get(r["sid"], {}).get("passed")})
    out.sort(key=lambda p: (p["w"], p["slot"]))
    return out


def shares(labels: list[str], bins: list[str]) -> np.ndarray:
    c = Counter(labels)
    v = np.array([c.get(b, 0) for b in bins], dtype=float)
    return v / v.sum() if v.sum() else v


def fam_units(fam: str) -> list[str]:
    if fam == "llama":
        sel = RESULTS_DIR / "select_llama.json"
        kept = read_json(sel)["kept"] if sel.exists() else []
        drop = RESULTS_DIR / "drop_llama_units.json"          # time-box drop (plan drop order item 2)
        if drop.exists():
            kept = [u for u in kept if u not in read_json(drop)["drop"]]
        return ["L-T1"] + kept
    return [u for u, s in UNITS.items() if s["family"] == fam and not s.get("candidate")]


def max_new_sweep(unit: str) -> int:
    cap = 1536 if UNITS[unit]["fence"] == "path" else 1024
    longest = max(len(p["gen_ids"]) for p in fit_programs(unit))
    return int(min(cap, 2 * longest + 8))


# ------------------------------------------------------------------------------------------------ S1 tests
def stage_tests(R: Runner, unit: str) -> dict[str, Any]:
    out_p = RESULTS_DIR / f"gpu_tests_{R.fam}.json"
    if out_p.exists():
        return read_json(out_p)
    spec = UNITS[unit]
    Pw = R.P(unit, "W1")
    seeds = [fit_seed(unit, "W1", s) for s in range(10)]
    mk = lambda T: [{"prompt_ids": Pw["ids"], "prefix_ids": [], "u": u_from_seed(sd), "T": T, "top_k": 0,
                     "max_new": 64} for sd in seeds]
    a = E.generate(R.model, R.tok, mk(1.0), coupled=True, fence_kind=spec["fence"], record=True)
    b = E.generate(R.model, R.tok, mk(1.0), coupled=True, fence_kind=spec["fence"])
    crn = sum(x["token_ids"] == y["token_ids"] for x, y in zip(a, b))
    # batch-size sensitivity (reported): the same 10 slots inside a 20-row batch
    seeds20 = seeds + [fit_seed(unit, "W1", s) for s in range(10, 20)]
    c = E.generate(R.model, R.tok, [{"prompt_ids": Pw["ids"], "prefix_ids": [], "u": u_from_seed(sd), "T": 1.0,
                                     "top_k": 0, "max_new": 64} for sd in seeds20], coupled=True,
                   fence_kind=spec["fence"])
    bs = sum(x["token_ids"] == y["token_ids"] for x, y in zip(a, c[:10]))
    # teacher-forced vs incremental logits along 5 openings
    agree, n, maxdiff = 0, 0, 0.0
    for x in a[:5]:
        ids = x["token_ids"]
        if not ids:
            continue
        Z = R.tf(unit, "W1", ids[:-1])                  # rows predict ids[0..]
        tf_arg = Z.argmax(-1).tolist()
        for i, (a1, m1, c1) in enumerate(x["record"][:len(ids)]):
            n += 1
            agree += tf_arg[i] == a1
            maxdiff = max(maxdiff, abs(float(Z[i, ids[i]]) - c1))
    res = {"family": R.fam, "unit": unit, "crn_identical": f"{crn}/10", "crn_pass": crn == 10,
           "batch10_vs_batch20_identical": f"{bs}/10", "tf_vs_incremental_argmax_agreement": agree / max(n, 1),
           "tf_vs_incremental_max_abs_logit_diff": maxdiff, "n_positions": n, "load": R.info}
    write_json(out_p, res)
    logger.info(f"gpu tests {R.fam}: {res}")
    return res


# ------------------------------------------------------------------------------------------------ S1.3 fit
def stage_fit(R: Runner, unit: str) -> dict[str, Any]:
    out_p = RESULTS_DIR / f"fit_{unit}.json"
    if out_p.exists():
        return read_json(out_p)
    spec = UNITS[unit]
    mx = FIT_MAX_NEW.get(unit, 1536 if spec["fence"] == "path" else 1024)
    seeds = {(w, s): fit_seed(unit, w, s) for w in TEMPLATES for s in FIT_SLOTS}
    t0 = time.time()
    rows = R.programs(unit, "fit", 1.0, seeds, mx)
    labs = R.label_programs(rows)
    append_jsonl(SAMPLES_RAW, rows)
    append_jsonl(LABELS, labs)
    bins = unit_bins(unit, [l["label"] for l in labs])
    lb = [to_bin(l["label"], bins) for l in labs]
    c = Counter(lb)
    res = {"unit": unit, "N": len(rows), "counts": dict(c), "bins": bins,
           "pass_rate": float(np.mean([l["passed"] for l in labs])), "max_new": mx,
           "cap_hits": sum(r["finish_reason"] == "length" for r in rows),
           "longest": max(r["n_tokens"] for r in rows), "seconds": round(time.time() - t0, 1),
           "by_template": {w: dict(Counter(to_bin(l["label"], bins) for r, l in zip(rows, labs)
                                           if r["template"] == w)) for w in TEMPLATES}}
    write_json(out_p, res)
    logger.info(f"fit {unit}: {res['counts']} pass {res['pass_rate']:.2f} ({res['seconds']}s)")
    return res


def stage_select_llama(R: Runner) -> dict[str, Any]:
    out_p = RESULTS_DIR / "select_llama.json"
    if out_p.exists():
        return read_json(out_p)
    kept, tried = [], []
    for t in LLAMA_BENCH_ORDER:
        u = f"L-{t}"
        f = stage_fit(R, u)
        algs = [(k, v) for k, v in sorted(f["counts"].items(), key=lambda kv: -kv[1]) if k not in ("other", "invalid")]
        second = algs[1][1] / f["N"] if len(algs) > 1 else 0.0
        tried.append({"unit": u, "counts": f["counts"], "second_share": second})
        if second >= LLAMA_MINORITY_BAR:
            kept.append(u)
        if len(kept) >= LLAMA_BENCH_KEEP:
            break
    res = {"order": list(LLAMA_BENCH_ORDER), "bar": LLAMA_MINORITY_BAR, "tried": tried, "kept": kept}
    write_json(out_p, res)
    commit("commit1a_llama_selection", res)
    logger.info(f"Llama bench selection: kept {kept}")
    return res


# ------------------------------------------------------------------------------------------------ S3 locate
def oc_gate(R: Runner, unit: str, fit: list[dict[str, Any]]) -> dict[str, Any]:
    val = [p for p in fit if p["w"] in ("W4", "W5") and p["label"] not in ("other", "invalid")]
    v = oc8.validate(unit, UNITS[unit]["task"], val, R.tok)
    v["gate_pass"] = bool(v["decided_agreement"] >= THRESH["oc_agree"] and v["full_agreement"] >= 0.95)
    return v


def _tf_dist(R: Runner, unit: str, prefix: list[int]) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Template-averaged T 1 next-token distribution after the generated prefix (and per template)."""
    per = {}
    for w in TEMPLATES:
        z = R.tf(unit, w, prefix)[-1]
        per[w] = torch.softmax(z.double(), -1).cpu().numpy()
    return np.mean(list(per.values()), axis=0), per


def _force(R: Runner, unit: str, prefix: list[int], tokens: list[int], tag: str, oc_ok: bool, bins: list[str],
           mx: int, n_per: int = N_FORCE) -> dict[int, Counter]:
    jobs = []
    for t in tokens:
        for j in range(n_per):
            w = TEMPLATES[j % 5]
            jobs.append({"cid": f"{unit}|{tag}|{t}|{j}", "stage": tag, "w": w, "prefix_ids": prefix + [t],
                         "seed": seed8(NS_FORCE, unit, tag, t, j), "max_new": mx - len(prefix) - 1, "tok": t})
    labs = R.continuations(unit, jobs, oc_ok, bins)
    out: dict[int, Counter] = {t: Counter() for t in tokens}
    for j, l in zip(jobs, labs):
        out[j["tok"]][l] += 1
    return out, jobs


def _scan(R: Runner, unit: str, paths: list[dict[str, Any]], stage: str, ns: str, oc_ok: bool, bins: list[str],
          mx: int, n_cont: int, chunk: int = 8, early: bool = True) -> dict[str, dict[int, Counter]]:
    """Prefix resampling over each path's grid in rounds of `chunk` positions; early stop per path once a change point
    is detected and the last 8 positions are 8/8 the path's own label."""
    counts: dict[str, dict[int, Counter]] = {p["pid"]: {} for p in paths}
    ptr = {p["pid"]: 0 for p in paths}
    active = {p["pid"] for p in paths if p["grid"]}
    byid = {p["pid"]: p for p in paths}
    while active:
        jobs = []
        for pid in sorted(active):
            p = byid[pid]
            ks = p["grid"][ptr[pid]:ptr[pid] + chunk]
            ptr[pid] += len(ks)
            for k in ks:
                for j in range(n_cont):
                    jobs.append({"cid": f"{unit}|{stage}|{pid}|{k}|{j}", "stage": stage, "w": p["w"],
                                 "prefix_ids": p["ids"][:k], "seed": seed8(ns, unit, p["key"], k, j),
                                 "max_new": mx - k, "pid": pid, "k": k})
        if not jobs:
            break
        labs = R.continuations(unit, jobs, oc_ok, bins)
        for j, l in zip(jobs, labs):
            counts[j["pid"]].setdefault(j["k"], Counter())[l] += 1
        for pid in list(active):
            p = byid[pid]
            if ptr[pid] >= len(p["grid"]):
                active.discard(pid)
                continue
            if not early:
                continue
            ks = sorted(counts[pid])
            series = np.array([[counts[pid][k].get(b, 0) for b in bins] for k in ks])
            det = L8.detect(series, THRESH["cp_pchange"], THRESH["cp_tv"])
            last = ks[-8:]
            if det["detected"] and len(last) == 8 and all(counts[pid][k].get(p["label"], 0) == n_cont for k in last):
                active.discard(pid)
    return counts


def stage_locate(R: Runner, unit: str) -> dict[str, Any]:
    out_p = RESULTS_DIR / f"locate_{unit}.json"
    if out_p.exists():
        return read_json(out_p)
    t_start = time.time()
    spec = UNITS[unit]
    fit = fit_programs(unit)
    bins = unit_bins(unit, [p["label"] for p in fit])
    for p in fit:
        p["label"] = to_bin(p["label"], bins)
    lab_c = Counter(p["label"] for p in fit)
    algs = [l for l, _ in lab_c.most_common() if l not in ("other", "invalid")]
    default = algs[0] if algs else None
    minority = algs[1] if len(algs) > 1 else None
    mx = max_new_sweep(unit)
    gate = oc_gate(R, unit, fit)
    oc_ok = gate["gate_pass"]
    if not oc_ok:
        log_deviation(f"oc_fail_{unit}", f"{unit}: opening classifier failed its gate ({gate}); continuations are "
                      "completed and labelled by the frozen labeller.")
    cls = L8.clusters([p["gen_ids"] for p in fit], THRESH["cluster_cov"], THRESH["max_clusters"])
    thin = (not oc_ok) and UNITS[unit]["family"] == "llama"
    bp = L8.choose_base_paths(fit, cls, minority, n_paths=4 if thin else 6)
    if thin:
        bp = bp[:4]
        lens = sorted(len(p["gen_ids"]) for p in fit)
        R.cont_cap = int(1.5 * lens[int(0.9 * (len(lens) - 1))]) + 32
        log_deviation(f"thin_{unit}", f"{unit}: the opening classifier failed its gate, so every continuation is "
                      f"completed and labelled by the frozen labeller; the extrapolated locator cost exceeded 25 "
                      f"GPU-minutes, so (plan rule) the grid is thinned to 4 base paths and every 4th token beyond "
                      f"k = 32, and continuations are capped at {R.cont_cap} new tokens (1.5 x the fit twin's p90 "
                      f"length + 32; capped continuations are labelled as they stand).")
    else:
        R.cont_cap = None
    p90 = gate.get("first_decision_p90") or 64
    W_u = int(min(160, max(64, max(len(c["O"]) for c in cls) + 8, p90)))

    def _grid(n: int) -> list[int]:
        g = L8.grid(W_u, n)
        return [k for k in g if k <= 32 or k % 4 == 0] if thin else g
    paths = [{"pid": f"p{j}", "key": f"{fit[i]['w']}:{fit[i]['slot']}", "ids": fit[i]["gen_ids"],
              "w": fit[i]["w"], "label": fit[i]["label"], "grid": _grid(len(fit[i]["gen_ids"]))}
             for j, i in enumerate(bp)]
    logger.info(f"locate {unit}: bins {bins} default {default} minority {minority} clusters "
                f"{[(c['id'], len(c['O']), round(c['cov'], 2)) for c in cls]} W_u {W_u} oc_ok {oc_ok}")
    counts = _scan(R, unit, paths, "loc", NS_LOC, oc_ok, bins, mx, N_LOC)
    n_loc = sum(sum(sum(c.values()) for c in d.values()) for d in counts.values())
    # 3.4 change points + refinement
    cps = []
    for p in paths:
        ks = sorted(counts[p["pid"]])
        if len(ks) < 3:
            cps.append({"pid": p["pid"], "detected": False})
            continue
        series = np.array([[counts[p["pid"]][k].get(b, 0) for b in bins] for k in ks])
        det = L8.detect(series, THRESH["cp_pchange"], THRESH["cp_tv"])
        rec = {"pid": p["pid"], "detected": det["detected"], "p_change": det["p_change"], "tv": det["tv"],
               "ks": ks, "series": series.tolist()}
        if det["detected"]:
            lo, hi = ks[det["tau"] - 1], ks[det["tau"]]
            jobs = []
            for k in range(lo, hi + 1):
                for j in range(N_REFINE):
                    jobs.append({"cid": f"{unit}|refine|{p['pid']}|{k}|{j}", "stage": "refine", "w": p["w"],
                                 "prefix_ids": p["ids"][:k], "seed": seed8(NS_REFINE, unit, p["key"], k, j),
                                 "max_new": mx - k, "k": k})
            labs = R.continuations(unit, jobs, oc_ok, bins)
            dists: dict[int, np.ndarray] = {}
            for j, l in zip(jobs, labs):
                dists.setdefault(j["k"], np.zeros(len(bins)))
                dists[j["k"]][bins.index(l)] += 1
            kstar, tv = L8.change_position(dists, lo, hi, THRESH["refine_tv"])
            rec.update({"tau_bracket": [lo, hi], "refine": {k: v.tolist() for k, v in dists.items()},
                        "k_star": kstar, "refine_tv": tv, "d": kstar - 1})
        cps.append(rec)
    cands = [{"O": next(p for p in paths if p["pid"] == c["pid"])["ids"][:c["d"]], "paths": [c["pid"]], "d": c["d"]}
             for c in cps if c.get("detected") and c.get("d", -1) >= 0]
    # amendment 2: every distinct candidate opening is force-confirmed first; nested openings are resolved among the
    # CONFIRMED ones only (a shorter candidate that fails confirmation no longer hides a longer confirmed decision)
    uniq: dict[tuple, dict[str, Any]] = {}
    for c in cands:
        if tuple(c["O"]) in uniq:
            uniq[tuple(c["O"])]["paths"] += c["paths"]
        else:
            uniq[tuple(c["O"])] = {**c, "paths": list(c["paths"])}
    openings = sorted(uniq.values(), key=lambda c: (len(c["O"]), c["paths"][0]))
    # 3.5 forced tokens
    ops = []
    for oi, op in enumerate(openings):
        O = list(op["O"])
        avg, per = _tf_dist(R, unit, O)
        top = [int(t) for t in np.argsort(-avg)[:TOPN_FORCE]]
        mass = avg[top]
        ftag = ctag("f", O)
        tc, jobs = _force(R, unit, O, top, ftag, oc_ok, bins, mx)
        phat = {t: L8.phat_from_counts(tc[t], bins) for t in top}
        on = [p for p in fit if p["gen_ids"][:len(O)] == O]
        off_top = [p["label"] for p in on if len(p["gen_ids"]) > len(O) and p["gen_ids"][len(O)] not in top]
        resid_phat = shares(off_top, bins) if off_top else (shares([p["label"] for p in on], bins) if on
                                                            else shares([p["label"] for p in fit], bins))
        resid_mass = float(max(0.0, 1.0 - mass.sum()))
        cl = L8.classes(top, mass, phat, resid_mass, resid_phat, bins, THRESH["class_phat_min"])
        ci = L8.h_bootstrap(tc, top, mass, resid_mass, resid_phat, bins, n_boot=300, seed=oi)
        rec = {"id": f"o{oi}", "force_tag": ftag, "O": O, "d": len(O), "paths": op["paths"], "tokens": top,
               "mass_T1": mass.tolist(),
               "mass_T1_by_template": {w: per[w][top].tolist() for w in TEMPLATES},
               "counts": {str(t): dict(tc[t]) for t in top}, "phat": {str(t): phat[t].tolist() for t in top},
               "resid_mass_T1": resid_mass, "resid_phat": resid_phat.tolist(), "n_on_fit": len(on),
               "classes": cl, "H_bits_first": cl["H_bits"], "H_ci_first": ci,
               "decision": cl["n_alg_classes"] >= 2, "token_strs": [R.tok.decode([t]) for t in top]}
        ops.append(rec)
    n_cand = len(ops)
    conf = [o for o in ops if o["decision"]]
    ops = [o for o in conf if not any(len(q["O"]) < len(o["O"]) and o["O"][:len(q["O"])] == q["O"] for q in conf)]
    logger.info(f"locate {unit}: {n_cand} candidate openings, {len(conf)} confirmed, {len(ops)} minimal confirmed")
    # 3.6 second decisions
    triggers = []
    for o in ops:
        o["second"] = {}
        cl = o["classes"]
        by_class: dict[str, list[tuple[float, int]]] = {}
        for t, m in zip(o["tokens"], o["mass_T1"]):
            by_class.setdefault(cl["class_of"][str(t)], []).append((m, t))
        for c, lst in by_class.items():
            cm = sum(m for m, _ in lst)
            if cm < THRESH["second_trigger_mass"]:
                continue
            m1, t1 = max(lst)
            ph = np.asarray(o["phat"][str(t1)])
            if L8.tok_entropy_bits(ph) <= THRESH["second_trigger_H"]:
                continue
            on_w = float(np.mean(list(on_cover_of(o, fit).values())))
            triggers.append((cm * on_w, o["id"], t1))
    # cost cap (deviation second_cap): at most 2 second-decision searches per unit, largest class mass first
    triggers.sort(reverse=True)
    if len(triggers) > 2:
        log_deviation(f"second_cap_{unit}", f"{unit}: {len(triggers)} classes met the second-decision trigger; only "
                      f"the 2 with the largest T-1 mass x opening coverage were searched (cost cap); the rest keep their "
                      f"empirical Phat.")
    for _, oid, t1 in triggers[:2]:
        o = next(x for x in ops if x["id"] == oid)
        sec = _second(R, unit, o, t1, oc_ok, bins, mx)
        if sec:
            o["second"][str(t1)] = sec
    for o in ops:
        o["H_bits"], o["H_leaves"] = composed_H(o, bins)
        o["decision_spread"] = o["H_bits"] > THRESH["unit_H_bits_pass"]
    # 3.9 entropy-located rival (BH): argmax T 1 entropy over the scanned dense grid of each base path
    bh_cands = []
    for p in paths:
        L = min(len(p["ids"]), 64)
        Z = R.tf(unit, p["w"], p["ids"][:L])
        ent = (-(torch.softmax(Z.double(), -1) * torch.log_softmax(Z.double(), -1)).sum(-1)).cpu().numpy()
        ks = [k for k in sorted(counts[p["pid"]]) if k <= 62 and k < len(ent)]
        if not ks:
            continue
        dH = max(ks, key=lambda k: ent[k])
        groups: dict[int, Counter] = {}
        pooled: Counter = Counter()
        for c in read_conts_at(unit, "loc", p["pid"], dH):
            if c["new_ids"]:
                groups.setdefault(int(c["new_ids"][0]), Counter())[c["label"]] += 1
            pooled[c["label"]] += 1
        bh_cands.append({"O": p["ids"][:dH], "paths": [p["pid"]], "d": dH, "entropy": float(ent[dH]),
                         "groups": {str(t): dict(v) for t, v in groups.items()}, "pooled": dict(pooled)})
    bh = []
    for i, c in enumerate(L8.minimal_openings(bh_cands)):
        groups = c["groups"]
        bh.append({"id": f"h{i}", "O": c["O"], "d": c["d"], "entropy": c["entropy"], "tokens": [int(t) for t in groups],
                   "phat": {t: L8.phat_from_counts(Counter(v), bins).tolist() for t, v in groups.items()},
                   "resid_phat": L8.phat_from_counts(Counter(c["pooled"]), bins).tolist(), "second": {}})
    # calibration: pooled k = 0 resamples vs the fit twin (minority share, Fisher)
    k0 = Counter()
    for pid in counts:
        k0.update(counts[pid].get(0, Counter()))
    calib = None
    if minority:
        a, n_a = k0.get(minority, 0), sum(k0.values())
        b, n_b = lab_c.get(minority, 0), len(fit)
        calib = {"k0_minority": f"{a}/{n_a}", "fit_minority": f"{b}/{n_b}",
                 "fisher_p": float(fisher_exact([[a, n_a - a], [b, n_b - b]])[1]) if n_a else None}
    on_cover = {}
    for o in ops:
        on_cover[o["id"]] = {w: sum(p["gen_ids"][:o["d"]] == o["O"] for p in fit if p["w"] == w) / 20 for w in TEMPLATES}
    rest = [p["label"] for p in fit if not any(p["gen_ids"][:o["d"]] == o["O"] for o in ops)]
    q_rest = shares(rest, bins) if rest else shares([p["label"] for p in fit], bins)
    n_cont_total = sum(1 for c in read_jsonl(CONTS) if c["unit"] == unit)
    res = {"unit": unit, "bins": bins, "default": default, "minority": minority, "fit_counts": dict(lab_c),
           "fit_shares": shares([p["label"] for p in fit], bins).tolist(), "oc_gate": gate, "oc_ok": oc_ok,
           "clusters": [{"id": c["id"], "O": c["O"], "len": len(c["O"]), "cov": c["cov"],
                         "cov_by_template": {w: sum(fit[i]["w"] == w for i in c["members"]) / 20 for w in TEMPLATES}}
                        for c in cls],
           "W_u": W_u, "base_paths": [{k: v for k, v in p.items() if k != "ids"} | {"len": len(p["ids"])}
                                      for p in paths],
           "change_points": cps, "openings": ops, "boundary": len(ops) == 0, "bh_openings": bh,
           "q_rest": q_rest.tolist(), "on_cover_fit": on_cover, "calibration_k0": calib,
           "n_loc_continuations": n_loc, "n_continuations_total": n_cont_total, "max_new_sweep": mx,
           "seconds": round(time.time() - t_start, 1)}
    res["H_unit_bits"] = max([o["H_bits"] for o in ops], default=None)
    write_json(out_p, res)
    logger.info(f"locate {unit}: {len(ops)} openings {[(o['id'], o['d'], round(o['H_bits'], 3)) for o in ops]} "
                f"second {[(o['id'], list(o['second'])) for o in ops]} ({res['seconds']}s, {n_cont_total} conts)")
    return res


def ctag(kind: str, ids: list[int]) -> str:
    """Content-addressed tag of a forced prefix (continuation ids and seeds are then unique to the prefix)."""
    import hashlib
    return kind + hashlib.sha1(json.dumps([int(i) for i in ids]).encode()).hexdigest()[:12]


def on_cover_of(o: dict[str, Any], fit: list[dict[str, Any]]) -> dict[str, float]:
    return {w: sum(p["gen_ids"][:o["d"]] == o["O"] for p in fit if p["w"] == w) / 20 for w in TEMPLATES}


def read_conts_at(unit: str, stage: str, pid: str, k: int) -> list[dict[str, Any]]:
    pre = f"{unit}|{stage}|{pid}|{k}|"
    return [c for c in read_jsonl(CONTS) if c["cid"].startswith(pre)]


def _second(R: Runner, unit: str, o: dict[str, Any], t1: int, oc_ok: bool, bins: list[str],
            mx: int) -> dict[str, Any] | None:
    """3.6: second decision inside the t1 branch (4 base paths from t1's forced continuations, resampling at every token
    d+1 .. d+24, change point, forced top-10 tokens at d2)."""
    d = o["d"]
    O = list(o["O"])
    fc = [c for c in read_jsonl(CONTS) if c["unit"] == unit and c["cid"].startswith(f"{unit}|{o['force_tag']}|{t1}|")]
    if not fc:
        return None
    lab = Counter(c["label"] for c in fc)
    lead = [l for l, _ in lab.most_common(2)]
    per_lead = 2 if oc_ok else 1          # completion-labelled units: 1 path per leading algorithm (deviation)
    picks = []
    for l in lead:
        picks += [c for c in fc if c["label"] == l and len(c["new_ids"]) >= 4][:per_lead]
    if len(picks) < 2:
        return None
    paths = []
    stag = ctag("s", O + [t1])
    for j, c in enumerate(picks[:4]):
        ids = O + [t1] + c["new_ids"]
        ks = list(range(d + 1, min(d + 1 + SECOND_SPAN, len(ids))))
        ptag = ctag("p", ids[:d + 1 + SECOND_SPAN])
        paths.append({"pid": ptag, "key": ptag, "ids": ids, "w": c["w"], "label": c["label"], "grid": ks})
    counts = _scan(R, unit, paths, stag, NS_SECOND, oc_ok, bins, mx, N_LOC, chunk=24, early=False)
    best = None
    for p in paths:
        ks = sorted(counts[p["pid"]])
        if len(ks) < 3:
            continue
        series = np.array([[counts[p["pid"]][k].get(b, 0) for b in bins] for k in ks])
        det = L8.detect(series, THRESH["cp_pchange"], THRESH["cp_tv"])
        if det["detected"]:
            dists = {k: np.array([counts[p["pid"]][k].get(b, 0) for b in bins], float) for k in ks}
            kstar, tv = L8.change_position(dists, ks[det["tau"] - 1], ks[det["tau"]], THRESH["refine_tv"])
            if best is None or tv > best["tv"]:
                best = {"pid": p["pid"], "k_star": kstar, "tv": tv, "p_change": det["p_change"], "ids": p["ids"]}
    if best is None:
        return {"found": False, "paths": [p["pid"] for p in paths]}
    d2 = best["k_star"] - 1
    O2 = best["ids"][d + 1:d2]
    pre2 = O + [t1] + O2
    avg, per = _tf_dist(R, unit, pre2)
    top2 = [int(t) for t in np.argsort(-avg)[:TOPN_FORCE2]]
    tc2, _ = _force(R, unit, pre2, top2, ctag("g", pre2), oc_ok, bins, mx)
    phat2 = {str(t): L8.phat_from_counts(tc2[t], bins).tolist() for t in top2}
    off = [c["label"] for c in fc if (O + [t1] + c["new_ids"])[d + 1:d2] != O2]
    ph1 = np.asarray(o["phat"][str(t1)])
    return {"found": True, "t1": t1, "d2": d2, "O2": O2, "tokens2": top2, "mass2_T1": avg[top2].tolist(),
            "counts2": {str(t): dict(tc2[t]) for t in top2}, "phat2": phat2,
            "resid2_phat": ph1.tolist(), "phat_off": (shares(off, bins) if off else ph1).tolist(),
            "n_off": len(off), "base": best["pid"], "tv": best["tv"], "token_strs2": [R.tok.decode([t]) for t in top2],
            "O2_str": R.tok.decode(O2)}


def composed_H(o: dict[str, Any], bins: list[str]) -> tuple[float, list[dict[str, Any]]]:
    """H(A | decision classes) over the composed tree at T 1 (template-averaged masses): tokens without a second
    decision are leaves classed at d; a token with one splits into (class at d, class at d2) leaves plus an off-O2 leaf
    (the O2 path probability is approximated at T 1 by the share of t1's forced continuations that stay on O2)."""
    leaves = []
    for t, m in zip(o["tokens"], o["mass_T1"]):
        sec = o.get("second", {}).get(str(t))
        ph = np.asarray(o["phat"][str(t)])
        c1 = o["classes"]["class_of"][str(t)]
        if not sec or not sec.get("found"):
            leaves.append({"key": c1, "m": m, "ph": ph})
            continue
        n_fc = sum(o["counts"][str(t)].values())
        w2 = max(0.0, 1.0 - sec["n_off"] / max(n_fc, 1))
        m2 = np.asarray(sec["mass2_T1"])
        for t2, mm in zip(sec["tokens2"], m2):
            p2 = np.asarray(sec["phat2"][str(t2)])
            j = int(np.argmax(p2))
            leaves.append({"key": f"{c1}>{bins[j] if p2[j] >= 0.7 else L8.UNDEC}", "m": m * w2 * mm, "ph": p2})
        leaves.append({"key": f"{c1}>resid2", "m": m * w2 * max(0.0, 1 - m2.sum()),
                       "ph": np.asarray(sec["resid2_phat"])})
        leaves.append({"key": f"{c1}>off", "m": m * (1 - w2), "ph": np.asarray(sec["phat_off"])})
    leaves.append({"key": o["classes"]["class_of"]["resid"], "m": o["resid_mass_T1"], "ph": np.asarray(o["resid_phat"])})
    agg: dict[str, list] = {}
    for lf in leaves:
        a = agg.setdefault(lf["key"], [0.0, np.zeros(len(bins))])
        a[0] += lf["m"]
        a[1] += lf["m"] * lf["ph"]
    tot = sum(v[0] for v in agg.values())
    H = 0.0
    for k, (m, mix) in agg.items():
        if m > 0:
            H += (m / tot) * P8.entropy_bits(mix / m)
    return H, [{"key": k, "mass": v[0] / tot} for k, v in agg.items()]


# ------------------------------------------------------------------------------------------------ S4 predict
def _compact(Z: torch.Tensor, O: list[int], tokens: list[int]) -> dict[str, Any]:
    """Z rows predict O[0..] and the last row is the decision distribution. Returns per (sampler|T) quantities."""
    out = {}
    Zd = Z.double()
    for T in TEMPS:
        lp = torch.log_softmax(Zd / T, -1)
        for s, k in (("p1", 0), ("k10", 10)):
            if k:
                kth = torch.topk(Zd, k, -1).values[:, -1:]
                masked = torch.where(Zd >= kth, Zd / T, torch.full_like(Zd, -math.inf))
                lpk = torch.log_softmax(masked, -1)
            else:
                lpk = lp
            lo = float(lpk[torch.arange(len(O), device=Z.device),
                           torch.tensor(O, dtype=torch.long, device=Z.device)].sum()) if O else 0.0
            pd = torch.exp(lpk[len(O)])
            pt = pd[torch.tensor(tokens, dtype=torch.long, device=Z.device)].tolist() if tokens else []
            out[f"{s}|{T}"] = {"lp_open": lo, "p_top": pt, "resid": float(max(0.0, 1.0 - sum(pt)))}
    return out


def _replay_walk(Zs: dict[str, torch.Tensor], ops: list[dict[str, Any]], U: torch.Tensor, T: float,
                 k: int) -> list[dict[str, Any]]:
    """Per-slot replay: walk the openings' trie with each slot's uniforms (U [S, L]) under the tempered teacher-forced
    distributions, then pick the decision token(s). Zs[op_id] = TF logits along O (rows predict O[i]; last = at d);
    Zs[op_id + '|' + t1] = TF logits along O + t1 + O2 (rows predict O2[j]; last = at d2)."""
    S = U.shape[0]
    res = []

    def pick_rows(z: torch.Tensor, u: torch.Tensor) -> torch.Tensor:
        p = torch.softmax(z.double() / T, -1)
        if k:
            kth = torch.topk(p, k, -1).values[..., -1:]
            p = torch.where(p < kth, torch.zeros_like(p), p)
        return E.inverse_cdf(p[None].expand(len(u), -1) if p.dim() == 1 else p, u)
    for s in range(S):
        cons = list(ops)
        i = 0
        out = {"status": "off", "op": None, "t1": None, "t2": None, "alg_idx": None}
        while cons:
            hit = [o for o in cons if len(o["O"]) == i]
            if hit:
                o = hit[0]
                z = Zs[o["id"]][i]
                t1 = int(pick_rows(z, U[s:s + 1, i])[0])
                out.update({"status": "on", "op": o["id"], "t1": t1, "pos": i})
                ph = o["phat"].get(str(t1))
                ph = np.asarray(ph if ph is not None else o["resid_phat"])
                sec = o.get("second", {}).get(str(t1))
                if sec and sec.get("found") and (o["id"] + "|" + str(t1)) in Zs:
                    Z2 = Zs[o["id"] + "|" + str(t1)]
                    on2 = True
                    for j, tok in enumerate(sec["O2"]):
                        if int(pick_rows(Z2[j], U[s:s + 1, i + 1 + j])[0]) != tok:
                            on2 = False
                            break
                    if on2:
                        t2 = int(pick_rows(Z2[len(sec["O2"])], U[s:s + 1, i + 1 + len(sec["O2"])])[0])
                        out["t2"] = t2
                        p2 = sec["phat2"].get(str(t2))
                        ph = np.asarray(p2 if p2 is not None else sec["resid2_phat"])
                    else:
                        out["t2"] = "off"
                        ph = np.asarray(sec["phat_off"])
                out["alg_idx"] = int(np.argmax(ph))
                break
            z = Zs[cons[0]["id"]][i]
            t = int(pick_rows(z, U[s:s + 1, i])[0])
            cons = [o for o in cons if o["O"][i] == t]
            i += 1
        res.append(out)
    return res


def bh_openings(R: Runner, unit: str, loc: dict[str, Any]) -> list[dict[str, Any]]:
    """BH rival (3.9, corrected before COMMIT #2): d_H = argmax over prefix lengths k < 64 that have locator or
    refinement continuations of the base paths' mean T 1 next-token entropy; one opening per distinct base-path prefix
    ids[:d_H]; Phat^H(A | t) from those continuations grouped by the token they sampled at d_H (no forced-token
    confirmation); the residual bin is the pooled share at d_H."""
    bins = loc["bins"]
    fit = {f"{p['w']}:{p['slot']}": p for p in fit_programs(unit)}
    by_pk: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for c in read_jsonl(CONTS):
        if c["unit"] != unit or c["stage"] not in ("loc", "refine"):
            continue
        parts = c["cid"].split("|")
        by_pk.setdefault((parts[2], int(parts[3])), []).append(c)
    ents: dict[int, list[float]] = {}
    for p in loc["base_paths"]:
        ids = fit[p["key"]]["gen_ids"]
        L = min(len(ids), 64)
        Z = R.tf(unit, p["w"], ids[:L]).double()
        ent = (-(torch.softmax(Z, -1) * torch.log_softmax(Z, -1)).sum(-1)).cpu().numpy()
        for k in range(L):
            if (p["pid"], k) in by_pk:
                ents.setdefault(k, []).append(float(ent[k]))
    if not ents:
        return []
    dH = max(ents, key=lambda k: float(np.mean(ents[k])))
    groups: dict[tuple, dict[str, Any]] = {}
    for p in loc["base_paths"]:
        if (p["pid"], dH) not in by_pk:
            continue
        ids = fit[p["key"]]["gen_ids"]
        g = groups.setdefault(tuple(ids[:dH]), {"tok": {}, "pooled": Counter(), "paths": []})
        g["paths"].append(p["pid"])
        for c in by_pk[(p["pid"], dH)]:
            if c["new_ids"]:
                g["tok"].setdefault(int(c["new_ids"][0]), Counter())[c["label"]] += 1
            g["pooled"][c["label"]] += 1
    out = []
    for i, (O, g) in enumerate(groups.items()):
        out.append({"id": f"h{i}", "O": list(O), "d": dH, "mean_entropy_nats": float(np.mean(ents[dH])),
                    "paths": g["paths"], "tokens": list(g["tok"]),
                    "phat": {str(t): L8.phat_from_counts(v, bins).tolist() for t, v in g["tok"].items()},
                    "counts": {str(t): dict(v) for t, v in g["tok"].items()},
                    "resid_phat": L8.phat_from_counts(g["pooled"], bins).tolist(), "second": {}})
    return out


def template_matched_calibration(unit: str, loc: dict[str, Any]) -> dict[str, Any] | None:
    """Sampler calibration (S4.5) with the templates matched: the k = 0 resamples come from the base paths' own
    templates (stratified, so not template-balanced); the expected minority count is the sum over those resamples of
    the fit twin's minority share in the same template; two-sided exact binomial test (Poisson-binomial approximated by
    the binomial at the mean rate)."""
    from scipy.stats import binomtest
    minority = loc["minority"]
    if not minority:
        return None
    fit = fit_programs(unit)
    rate = {w: (sum(p["label"] == minority for p in fit if p["w"] == w) / max(1, sum(p["w"] == w for p in fit)))
            for w in TEMPLATES}
    wof = {p["pid"]: p["w"] for p in loc["base_paths"]}
    k = n = 0
    exp_ = 0.0
    for c in read_jsonl(CONTS):
        if c["unit"] != unit or c["stage"] != "loc":
            continue
        parts = c["cid"].split("|")
        if int(parts[3]) != 0:
            continue
        n += 1
        k += c["label"] == minority
        exp_ += rate[wof[parts[2]]]
    if not n:
        return None
    p = float(binomtest(k, n, min(max(exp_ / n, 1e-9), 1 - 1e-9)).pvalue)
    return {"k0_minority": f"{k}/{n}", "expected_template_matched": exp_, "binom_p": p,
            "pass": p > THRESH["calib_fisher_p"]}


def stage_predict(R: Runner, unit: str) -> dict[str, Any]:
    out_p = RESULTS_DIR / f"predict_{unit}.json"
    if out_p.exists():
        return read_json(out_p)
    loc = read_json(RESULTS_DIR / f"locate_{unit}.json")
    loc["bh_openings"] = bh_openings(R, unit, loc)
    log_deviation("bh_rule", "BH rival rule corrected before COMMIT #2 (no sweep sample existed): d_H is the argmax "
                  "of the base paths' mean T-1 entropy over every prefix length < 64 that has locator or refinement "
                  "continuations (the COMMIT #1 version only searched even grid positions per path and kept the "
                  "shortest opening). BH openings are committed at COMMIT #2.")
    bins = loc["bins"]
    fit_sh = np.asarray(loc["fit_shares"])
    law = {"q_rest": loc["q_rest"], "openings": loc["openings"]}
    lawH = {"q_rest": loc["q_rest"], "openings": loc["bh_openings"]}
    tf_by_w: dict[str, dict[str, Any]] = {}
    tfH_by_w: dict[str, dict[str, Any]] = {}
    replay: dict[str, Any] = {}
    for w in TEMPLATES:
        tf: dict[str, Any] = {}
        Zs: dict[str, torch.Tensor] = {}
        for o in loc["openings"]:
            Z = R.tf(unit, w, o["O"])
            Zs[o["id"]] = Z
            tf[o["id"]] = _compact(Z, o["O"], o["tokens"])
            tf[o["id"]]["second"] = {}
            for t1, sec in o.get("second", {}).items():
                if not sec.get("found"):
                    continue
                pre = list(o["O"]) + [int(t1)] + list(sec["O2"])
                Z2full = R.tf(unit, w, pre)
                Z2 = Z2full[len(o["O"]) + 1:]                        # rows predict O2[j]; last row at d2
                Zs[o["id"] + "|" + t1] = Z2
                c2 = _compact(Z2, sec["O2"], sec["tokens2"])
                tf[o["id"]]["second"][t1] = {k: {"lp_O2": v["lp_open"], "p_top2": v["p_top"], "resid2": v["resid"]}
                                             for k, v in c2.items()}
        tf_by_w[w] = tf
        tfh: dict[str, Any] = {}
        for o in loc["bh_openings"]:
            tfh[o["id"]] = _compact(R.tf(unit, w, o["O"]), o["O"], o["tokens"])
            tfh[o["id"]]["second"] = {}
        tfH_by_w[w] = tfh
        # replay predictions for this template's sweep slots
        if loc["openings"]:
            dmax = max(o["d"] + 2 + max([len(s.get("O2", [])) for s in o.get("second", {}).values()] or [0])
                       for o in loc["openings"])
            U = torch.tensor(np.stack([u_from_seed(sweep_seed(unit, w, s))[:dmax + 2] for s in SWEEP_SLOTS]),
                             dtype=torch.float64, device=E.dev_of(R.model))
            for T in TEMPS:
                for sname, kk in (("p1", 0), ("k10", 10)):
                    rr = _replay_walk(Zs, loc["openings"], U, T, kk)
                    for s, r in zip(SWEEP_SLOTS, rr):
                        replay[f"{w}|{s}|{sname}|{T}"] = r
        del Zs
        torch.cuda.empty_cache()
    cells: dict[str, Any] = {}
    for sname in ("p1", "k10"):
        for T in TEMPS:
            key = f"{sname}|{T}"
            if loc["openings"]:
                L = P8.cell_prediction(law, tf_by_w, T, sname)
                B2 = P8.cell_prediction(law, tf_by_w, T, sname, single=True)
                PL, on, B2P = L["P"], L["on_opening"], B2["P"]
            else:                                              # boundary unit: flat prediction
                PL, on, B2P = fit_sh, None, fit_sh
            BH = P8.cell_prediction(lawH, tfH_by_w, T, sname)["P"] if loc["bh_openings"] else fit_sh
            cells[key] = {"L": np.asarray(PL).tolist(), "B0": P8.b0(fit_sh, T).tolist(), "B1": P8.b1(fit_sh, T).tolist(),
                          "B2": np.asarray(B2P).tolist(), "BH": np.asarray(BH).tolist(), "on_opening": on}
    # replay-implied shares
    q_rest = np.asarray(loc["q_rest"])
    rep_sh = {}
    for sname in ("p1", "k10"):
        for T in TEMPS:
            v = np.zeros(len(bins))
            for w in TEMPLATES:
                for s in SWEEP_SLOTS:
                    r = replay.get(f"{w}|{s}|{sname}|{T}")
                    if r and r["status"] == "on" and r["alg_idx"] is not None:
                        v[r["alg_idx"]] += 1
                    else:
                        v += q_rest
            rep_sh[f"{sname}|{T}"] = (v / v.sum()).tolist()
    minority = loc["minority"]
    j = bins.index(minority) if minority in bins else None
    drop = None
    if j is not None:
        drop = {"minority": minority, "pred_T1": cells["p1|1.0"]["L"][j], "pred_T03": cells["p1|0.3"]["L"][j],
                "pred_drop": cells["p1|1.0"]["L"][j] - cells["p1|0.3"]["L"][j]}
    gate_tvd = P8.tvd(cells["p1|1.0"]["L"], fit_sh)
    calib_tm = template_matched_calibration(unit, loc)
    res = {"unit": unit, "bins": bins, "cells": cells, "replay_implied": rep_sh, "replay": replay,
           "bh_openings": loc["bh_openings"],
           "tf_compact": tf_by_w, "tfH_compact": tfH_by_w, "predicted_drop": drop,
           "consistency": {"tvd_T1_vs_fit": gate_tvd, "pass": gate_tvd <= THRESH["consistency_tvd"],
                           "calibration_k0": loc["calibration_k0"], "calibration_k0_template_matched": calib_tm}}
    write_json(out_p, res)
    logger.info(f"predict {unit}: L p1 = {[round(cells[f'p1|{T}']['L'][j], 3) for T in TEMPS] if j is not None else None}"
                f" consistency TVD {gate_tvd:.3f}")
    return res


# ------------------------------------------------------------------------------------------------ S5 sweep
def stage_sweep(R: Runner, unit: str, validate_topk: bool) -> dict[str, Any]:
    out_p = RESULTS_DIR / f"sweep_{unit}.json"
    if out_p.exists():
        return read_json(out_p)
    t0 = time.time()
    mx = max_new_sweep(unit)
    seeds = {(w, s): sweep_seed(unit, w, s) for w in TEMPLATES for s in SWEEP_SLOTS}
    allrows = []
    for T in TEMPS:
        rows = R.programs(unit, "sweep", T, seeds, mx, shadow_k=10)
        allrows += rows
        # top-k 10 programs by exact shadow sampling on the same uniforms
        regen, regen_idx = [], []
        tk_rows = []
        for r in rows:
            base = {k: v for k, v in r.items()}
            base.update({"sid": r["sid"].replace("|k0", "|k10"), "arm": "topk", "top_k": 10})
            if r["shadow_div_step"] is None:
                base.update({"shadow": "identical"})
                tk_rows.append(base)
            else:
                D = r["shadow_div_step"]
                pre = r["token_ids"][:D] + [r["shadow_tok"]]
                u = u_from_seed(r["seed"])[D + 1:]
                regen.append({"prompt_ids": R.P(unit, r["template"])["ids"], "prefix_ids": pre, "u": u, "T": T,
                              "top_k": 10, "max_new": max(1, mx - D - 1)})
                regen_idx.append((len(tk_rows), pre))
                base.update({"shadow": "regenerated", "regen_from": D})
                tk_rows.append(base)
        if regen:
            outs = E.run_batches(R.model, R.tok, regen, CONT_BATCH[R.fam], coupled=False,
                                 fence_kind=UNITS[unit]["fence"])
            for (i, pre), o in zip(regen_idx, outs):
                ids = pre + o["token_ids"]
                tk_rows[i].update({"token_ids": ids, "n_tokens": len(ids), "finish_reason": o["finish_reason"],
                                   "text": R.decode(ids)})
        allrows += tk_rows
        logger.info(f"sweep {unit} T{T}: {len(rows)} programs, {len(regen)} top-k regenerations")
    labs = R.label_programs(allrows)
    append_jsonl(SAMPLES_RAW, allrows)
    append_jsonl(LABELS, labs)
    val = None
    if validate_topk:
        # 20 slots (W1) under top-k 10 directly, fixed composition, at T 1.3 (the most divergent cell)
        sd = {("W1", s): seeds[("W1", s)] for s in SWEEP_SLOTS}
        direct = R.programs(unit, "topk_val", 1.3, sd, mx, top_k=10)
        shadow = {(r["template"], r["slot"]): r for r in allrows if r["arm"] == "topk" and r["T"] == 1.3}
        ident = sum(d["token_ids"] == shadow[(d["template"], d["slot"])]["token_ids"] for d in direct)
        val = {"unit": unit, "T": 1.3, "n": len(direct), "token_identical": ident,
               "rate": ident / len(direct), "pass": ident / len(direct) >= THRESH["shadow_ident"],
               "n_regenerated_in_cell": sum(1 for r in shadow.values() if r.get("shadow") == "regenerated")}
        append_jsonl(SAMPLES_RAW, direct)
        write_json(RESULTS_DIR / f"topk_validation_{R.fam}.json", val)
    res = {"unit": unit, "n_programs": len(allrows), "max_new": mx, "seconds": round(time.time() - t0, 1),
           "cap_hits": sum(r["finish_reason"] == "length" for r in allrows), "topk_validation": val,
           "n_regenerated": sum(1 for r in allrows if r.get("shadow") == "regenerated")}
    write_json(out_p, res)
    return res


# ------------------------------------------------------------------------------------------------ engine checks
def engine_check(unit: str) -> dict[str, Any]:
    """Per-slot label (and token) agreement of the fit twin with the source artifact's rows at the same keys."""
    labs = label_map()
    mine = {(r["template"], r["slot"]): r for r in read_jsonl(SAMPLES_RAW) if r["unit"] == unit and r["arm"] == "fit"}
    fam = UNITS[unit]["family"]
    ref: dict[tuple[str, int], tuple[str | None, list[int] | None]] = {}
    if fam == "qwen":
        src_l = {r["sid"]: r.get("label") for r in read_jsonl(SRCS["exp35"] / "data" / "labels.jsonl")}
        for r in read_jsonl(SRCS["exp35"] / "data" / "samples_raw.jsonl"):
            if r["unit"] == unit and str(r.get("arm")).upper() == "TWIN":
                ref[(r["template"], r["slot"])] = (src_l.get(r["sid"]), r.get("token_ids"))
    elif fam == "gemma":
        src_l = {r["row_id"]: r.get("label") for r in read_jsonl(SRCS["exp31"] / "data" / "labels.jsonl")}
        for r in read_jsonl(SRCS["exp31"] / "data" / "raw_s3.jsonl"):
            if r["task"] == UNITS[unit]["task"] and r["arm"] == "twin" and r["slot"] < 20:
                ids = json.loads(r["token_ids"]) if isinstance(r["token_ids"], str) else r["token_ids"]
                ref[(r["template"], r["slot"])] = (src_l.get(r["row_id"]), ids)
    n = agree = tok_id = 0
    for key, r in mine.items():
        if key not in ref:
            continue
        n += 1
        agree += labs.get(r["sid"], {}).get("label") == ref[key][0]
        if ref[key][1] is not None:
            a, b = r["token_ids"], list(ref[key][1])
            stops = set(FAMILIES[fam]["stop_ids"])
            a = [t for t in a if t not in stops]
            b = [t for t in b if t not in stops]
            tok_id += a == b
    return {"unit": unit, "n_matched_slots": n, "label_agreement": agree / n if n else None,
            "token_identical": tok_id, "pass": (agree / n >= THRESH["engine_agree"]) if n else None}


# ------------------------------------------------------------------------------------------------ S6.1 instruct side
def stage_base_instr(R: Runner) -> dict[str, Any]:
    """Qwen3-8B instruct side of the base sub-arm: 20 fit programs (4 slots x 5 templates, iteration-7 keys) of the
    collapsed twins T1, T10, T2 (B3/A3 reuse their fit twins). The base model is teacher-forced on the same ids later."""
    out_p = RESULTS_DIR / "base_instr_programs.json"
    if out_p.exists():
        return read_json(out_p)
    res = {}
    for u in COLLAPSED_QWEN:
        seeds = {(w, s): fit_seed_collapsed(u, w, s) for w in TEMPLATES for s in range(4)}
        rows = []
        for w in TEMPLATES:
            Pw = R.prompts[(u, w)]
            batch = [{"prompt_ids": Pw["ids"], "prefix_ids": [], "u": u_from_seed(seeds[(w, s)]), "T": 1.0,
                      "top_k": 0, "max_new": 160} for s in range(4)]
            outs = E.generate(R.model, R.tok, batch, coupled=True, fence_kind=None)
            for s, o in zip(range(4), outs):
                rows.append({"unit": u, "w": w, "slot": s, "token_ids": o["token_ids"]})
        res[u] = rows
    write_json(out_p, res)
    return res


def fit_seed_collapsed(u: str, w: str, s: int) -> int:
    from cfg8 import stable_seed
    return stable_seed("iter7T", u, w, s)


# ------------------------------------------------------------------------------------------------ orchestration
def commit_family(fam: str, which: str) -> None:
    units = fam_units(fam)
    name = f"commit{which}_{fam}"
    if any(l.split("  ")[1] == name for l in (Path(PRED_DIR.parent / "commitments.log").read_text().splitlines()
                                               if (PRED_DIR.parent / "commitments.log").exists() else [])):
        logger.info(f"{name} exists")
        return
    if which == "1":
        payload = {"family": fam, "units": {u: read_json(RESULTS_DIR / f"locate_{u}.json") for u in units}}
    else:
        code = {f: sha256_file(SRC / f) for f in ("analysis_L.py", "predict8.py", "replay.py", "predict.py")
                if (SRC / f).exists()}
        payload = {"family": fam, "scoring_code_sha256": code,
                   "units": {u: {k: v for k, v in read_json(RESULTS_DIR / f"predict_{u}.json").items()
                                 if k not in ("tf_compact", "tfH_compact")} for u in units}}
    commit(name, payload)
    logger.info(f"{name} committed; chain {verify()}")


def run_family(fam: str, stages: list[str]) -> None:
    setup_logging(f"gpu8_{fam}")
    R = Runner(fam)
    try:
        units_fixed = [u for u, s in UNITS.items() if s["family"] == fam and not s.get("candidate")]
        if "tests" in stages:
            stage_tests(R, units_fixed[0])
        if "fit" in stages:
            for u in units_fixed:
                stage_fit(R, u)
            if fam == "llama":
                stage_select_llama(R)
            ec = {u: engine_check(u) for u in fam_units(fam) if fam != "llama"}
            if fam == "llama":
                f = read_json(RESULTS_DIR / "fit_L-T1.json")
                c = f["counts"]
                bfs, n = c.get("bfs", 0), f["N"]
                ec["L-T1"] = {"vs_exp10_vllm_fp8": {"exp10": {"bfs": 77, "dfs": 20, "other": 3}, "new": c,
                                                    "fisher_p_bfs": float(fisher_exact([[bfs, n - bfs], [77, 23]])[1])}}
            write_json(RESULTS_DIR / f"engine_check_{fam}.json", ec)
            logger.info(f"engine check {fam}: {ec}")
        units = fam_units(fam)
        if "locate" in stages:
            for u in units:
                stage_locate(R, u)
        if "commit1" in stages:
            commit_family(fam, "1")
        if "predict" in stages:
            for u in units:
                stage_predict(R, u)
        if "commit2" in stages:
            if fam == "llama" and not (RESULTS_DIR / "regate.json").exists():
                # S1.4 style re-gate of the Llama labels (two blind judges + tiebreak), committed before COMMIT #2-L
                subprocess.run([sys.executable, str(SRC / "novelty8.py"), "regate"], cwd=str(SRC), check=False,
                               stdout=open(LOG_DIR / "regate.out", "a"), stderr=subprocess.STDOUT)
                if (RESULTS_DIR / "regate.json").exists():
                    rg = read_json(RESULTS_DIR / "regate.json")
                    commit("commit1b_llama_regate", {u: {k: v for k, v in r.items() if k != "rows"}
                                                     for u, r in rg.items()})
            commit_family(fam, "2")
        if "sweep" in stages:
            for i, u in enumerate(units):
                stage_sweep(R, u, validate_topk=(i == 0))
        if "base_instr" in stages and fam == "qwen":
            stage_base_instr(R)
    finally:
        R.close()


if __name__ == "__main__":
    fam = sys.argv[1]
    st = sys.argv[2].split(",") if len(sys.argv) > 2 else ["tests", "fit", "locate", "commit1", "predict", "commit2",
                                                         "sweep", "base_instr"]
    run_family(fam, st)
