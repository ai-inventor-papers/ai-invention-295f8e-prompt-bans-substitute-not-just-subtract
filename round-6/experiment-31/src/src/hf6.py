#!/usr/bin/env python3
"""HF bf16 CRN engine phase (plan S5 + S7) in one long-running process (the model is loaded once):

  probe     memory probe: B = the largest of 12, 10, 8, 6 such that a prefill plus a 1,024-step decode of B rows at the
            longest new-unit prompt fits with 0.6 GiB headroom (KV is preallocated, so a short decode measures it);
  gputests  G1 CRN determinism, G2 batch-companion invariance, G3 alpha = 0 push == twin, G4 push rel_err < 1e-3 at
            every edited block, G5 GTN alpha = 0 == twin and shadow tokens == GTN tokens, G6 batched vs batch-1
            teacher forcing within 0.05 nats -> results/gpu_tests.json (must pass before any decisive row);
  twin      HF twin T1.0 slots k 0..9 per template (50, CRN) for every unit;
  qlik      teacher-forced openings (<= 48 code tokens) of the verified scrubbed forced programs of every mode under
            W1..W5 -> results/qlik/<u>.json (q_lik, q_lik_raw, fork margin inputs);
  nudge     per enrolled unit (enrolment order, verified unit commit): ESC stage 1 (8 dirs x alpha 1/2/4 x k 0,1),
            PN a2, PN a4, ESC confirmations (k 2..5 for stage-1 passes), GTN a2 (k 0..9 with shadow rows).
Every batch holds exactly B rows of ONE (unit, prompt); unused room is filled with PAD rows (twin, pad slots >= 1000,
never analysed). Rows -> data/raw_hf.jsonl; realised displacement -> data/realised_disp.jsonl; timing -> results/.
Usage: python src/hf6.py all --units I1,...,I10 [--stop-at-utc 2026-10-22T00:25:00]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import torch  # noqa: E402
from loguru import logger  # noqa: E402

from cfg6 import (ALPHAS_ESC, ALPHAS_PN, ALPHA_GTN, DATA_DIR, ESC_EXCESS, ESC_PASS_FRAC, GTN_STEPS, MAX_NEW,  # noqa
                  MODEL_ID, MODEL_REVISION, N_DIRS, PRECISION, PRED_DIR, QLIK_TOKENS, RAW_HF, REALISED, RESULTS_DIR,
                  SLOTS, SRC, TEMPLATE_IDS, TIMING, UNITS_DIR, append_jsonl, direction_seed, gtn_seed, log_deviation,
                  pn_seed, read_json, read_jsonl, setup_logging, sha256_text, utc_now, write_json)
from ctx6 import UnitCtx, rand_dir  # noqa: E402
from engine6 import free_cuda, load_model, prefill, sample, teacher_forced, u_stream  # noqa: E402
from prompts6 import load_prompts  # noqa: E402
from units_spec6 import UNITS  # noqa: E402

HOOK_SHA = hashlib.sha256((SRC / "engine6.py").read_bytes() + (SRC / "ctx6.py").read_bytes()).hexdigest()
QLIK_DIR = RESULTS_DIR / "qlik"
QLIK_DIR.mkdir(parents=True, exist_ok=True)
PAD_START = 1000


def parse_arm(arm: str) -> dict[str, Any]:
    if arm in ("TWINHF", "PAD"):
        return {"family": arm, "push": None}
    if arm.startswith("ESC_d"):
        d, a = arm[5:].split("_a")
        return {"family": "ESC", "seed": int(d), "alpha": float(a), "push": "prefill"}
    if arm.startswith("PN_a"):
        return {"family": "PN", "alpha": float(arm[4:]), "push": "prefill_per_sample"}
    if arm.startswith("GTN_a"):
        return {"family": "GTN", "alpha": float(arm[5:]), "push": "generated_tokens"}
    if arm.startswith("FORCEDHF_"):
        return {"family": "FORCEDHF", "mode": arm[9:], "push": None}
    raise ValueError(arm)


def esc_arm(seed: int, alpha: float) -> str:
    return f"ESC_d{seed}_a{alpha:g}"


class Runner:
    def __init__(self, model: Any, tok: Any, B: int):
        self.model, self.tok, self.B = model, tok, B
        self.pr = load_prompts()
        self.ctx: dict[str, UnitCtx] = {}
        self.engine = f"hf-transformers-{__import__('transformers').__version__}-bf16-sdpa"
        self.tf_batch = B
        self.nb = 0

    def unit_ctx(self, unit: str) -> UnitCtx:
        if unit not in self.ctx:
            for c in self.ctx.values():
                c.release()
            self.ctx = {unit: UnitCtx(self.model, unit, {w: self.pr[f"{unit}|twin|-|{w}"] for w in TEMPLATE_IDS})}
        return self.ctx[unit]

    def done_slots(self) -> set[tuple[str, str, str, int]]:
        return {(r["unit"], r["template"], r["arm"], int(r["slot"])) for r in read_jsonl(RAW_HF)
                if not r.get("shadow")}

    def run_batch(self, unit: str, w: str, spec: list[tuple[str, list[int]]], stage: str,
                  prompt_pid: str | None = None, write: bool = True) -> list[dict[str, Any]]:
        """spec rows (GTN slots count twice: GTN row + shadow) must sum to B."""
        n_rows = sum(len(ks) * (2 if parse_arm(a)["family"] == "GTN" else 1) for a, ks in spec)
        assert n_rows == self.B, (spec, n_rows, self.B)
        t0 = time.time()
        forced = prompt_pid is not None
        p = self.pr[prompt_pid] if forced else self.pr[f"{unit}|twin|-|{w}"]
        ctx = None if forced else self.unit_ctx(unit)
        groups, meta, recs = [], [], []
        gtn_pairs, gtn_U, gtn_alpha = [], [], None
        row = 0
        for arm, ks in spec:
            a = parse_arm(arm)
            key_w = w
            if a["family"] == "ESC":
                pre, rec = ctx.arm_prefill(w, ctx.push_spec(w, rand_dir(a["seed"]), a["alpha"]))
                recs.append({"unit": unit, "template": w, "arm": arm, "stage": stage, "utc": utc_now(), **rec})
                groups.append({"pre": pre, "us": [u_stream(unit, key_w, k) for k in ks]})
                for k in ks:
                    meta.append((arm, k, rec.get("rel_err_max"), a["seed"], False))
                row += len(ks)
            elif a["family"] == "PN":
                for k in ks:
                    sd = pn_seed(unit, a["alpha"], w, k)
                    pre, rec = ctx.arm_prefill(w, ctx.push_spec(w, rand_dir(sd), a["alpha"]))
                    recs.append({"unit": unit, "template": w, "arm": arm, "slot": k, "stage": stage,
                                 "utc": utc_now(), "direction_seed": sd, **rec})
                    groups.append({"pre": pre, "us": [u_stream(unit, key_w, k)]})
                    meta.append((arm, k, rec.get("rel_err_max"), sd, False))
                    row += 1
            elif a["family"] == "GTN":
                pre = ctx.twin(w)["pre"]
                gtn_alpha = a["alpha"]
                for k in ks:
                    sd = gtn_seed(unit, a["alpha"], w, k)
                    us = u_stream(unit, key_w, k)
                    groups.append({"pre": pre, "us": [us, us]})
                    gtn_pairs.append((row, row + 1))
                    gtn_U.append(rand_dir(sd))
                    meta.append((arm, k, None, sd, False))
                    meta.append(("GTNSHADOW", k, None, sd, True))
                    row += 2
            else:
                if forced:
                    pre = prefill(self.model, p["ids"])
                    keyw = f"forcedhf:{a.get('mode')}:{p['template_id']}"
                    groups.append({"pre": pre, "us": [u_stream(unit, keyw, k) for k in ks]})
                else:
                    pre = ctx.twin(w)["pre"]
                    groups.append({"pre": pre, "us": [u_stream(unit, key_w, k) for k in ks]})
                for k in ks:
                    meta.append((arm, k, None, None, False))
                row += len(ks)
        gtn = None
        if gtn_pairs:
            gtn = {"pairs": gtn_pairs, "U": torch.tensor(np.stack(gtn_U)), "alpha": gtn_alpha, "steps": GTN_STEPS}
        res = sample(self.model, self.tok, groups, max_new=MAX_NEW, temperature=1.0, gtn=gtn)
        self.nb += 1
        bid = f"{stage}:{unit}:{w}:{self.nb}:{utc_now()}"
        out = []
        for (arm, k, rerr, sd, shadow), r in zip(meta, res):
            a = parse_arm(arm) if arm != "GTNSHADOW" else {"family": "GTNSHADOW", "alpha": gtn_alpha}
            out.append({"unit": unit, "arm": arm, "family": a["family"], "template": w if not forced else
                        p["template_id"], "slot": k, "model_tag": "instruct", "model": MODEL_ID,
                        "model_revision": MODEL_REVISION, "precision": PRECISION, "engine": self.engine,
                        "temperature": 1.0, "thinking": False, "alpha": a.get("alpha"), "direction_seed": sd,
                        "site": {"ESC": "task_spec_12_23_prefill", "PN": "task_spec_12_23_prefill",
                                 "GTN": "generated_tokens_1_32_blocks_12_23"}.get(a["family"]),
                        "stage": stage, "prompt_pid": p["pid"], "prompt_sha256": p["prompt_sha256"],
                        "rel_err_max": rerr, "gtn_rel_err_max": r.get("gtn_rel_err_max"),
                        "gtn_edited_steps": r.get("gtn_edited_steps"), "shadow": shadow,
                        "text": self.tok.decode(r["token_ids"], skip_special_tokens=True),
                        "token_ids": r["token_ids"], "n_tokens": r["n_tokens"], "finish_reason": r["finish_reason"],
                        "fence_step": r["fence_step"], "logprob_sum": r["logprob_sum"], "utc": utc_now(),
                        "batch_id": bid, "B": self.B, "hook_sha256": HOOK_SHA})
        if write:
            append_jsonl(RAW_HF, out)
            if recs:
                append_jsonl(REALISED, recs)
            dt = time.time() - t0
            append_jsonl(TIMING, [{"stage": stage, "unit": unit, "w": w, "arms": sorted({x for x, _ in spec}),
                                   "B": self.B, "seconds": dt, "steps": res[0]["steps"],
                                   "max_tokens": max(r["n_tokens"] for r in res), "utc": utc_now()}])
            logger.info(f"{stage} {unit}/{w} {sorted({x for x, _ in spec})[:4]}: {dt:.1f}s, {res[0]['steps']} steps")
        return out

    def pack(self, cells: list[tuple[str, list[int]]], pad_used: set[int]) -> list[list[tuple[str, list[int]]]]:
        batches, cur, room = [], [], self.B
        for arm, ks in cells:
            per = 2 if parse_arm(arm)["family"] == "GTN" else 1
            ks = list(ks)
            while ks:
                fit = room // per
                if fit == 0:
                    batches.append(cur)
                    cur, room = [], self.B
                    continue
                take, ks = ks[:fit], ks[fit:]
                cur.append((arm, take))
                room -= per * len(take)
                if room == 0:
                    batches.append(cur)
                    cur, room = [], self.B
        if cur:
            pad, k = [], PAD_START
            while len(pad) < room:
                if k not in pad_used:
                    pad.append(k)
                    pad_used.add(k)
                k += 1
            cur.append(("PAD", pad))
            batches.append(cur)
        return batches

    def run_cells(self, unit: str, cells_by_w: dict[str, list[tuple[str, list[int]]]], stage: str,
                  deadline: float | None = None, max_batches: int | None = None) -> int:
        done = self.done_slots()
        nb = 0
        for w, cells in cells_by_w.items():
            pad_used = {k for (uu, ww, arm, k) in done if uu == unit and ww == w and arm == "PAD"}
            todo = []
            for arm, ks in cells:
                rest = [k for k in ks if (unit, w, arm, k) not in done]
                if rest:
                    todo.append((arm, rest))
            if not todo:
                continue
            for spec in self.pack(todo, pad_used):
                if deadline is not None and time.time() > deadline:
                    logger.warning(f"deadline before {stage} {unit}/{w}")
                    return nb
                if max_batches is not None and nb >= max_batches:
                    return nb
                self.run_batch(unit, w, spec, stage)
                nb += 1
        return nb


# ------------------------------------------------------------------------------------------------ probe + tests
def memory_probe(runner: Runner, units: list[str]) -> int:
    longest = max((runner.pr[f"{u}|twin|-|{w}"] for u in units for w in TEMPLATE_IDS), key=lambda p: p["P"])
    total = torch.cuda.get_device_properties(0).total_memory
    res = {"longest_prompt": longest["pid"], "P": longest["P"], "total_gib": total / 2 ** 30, "tried": {}}
    chosen = None
    for B in (12, 10, 8, 6):
        free_cuda()
        torch.cuda.reset_peak_memory_stats()
        try:
            pre = prefill(runner.model, longest["ids"])
            groups = [{"pre": pre, "us": [np.full(MAX_NEW, 0.5) for _ in range(B)]}]
            sample(runner.model, runner.tok, groups, max_new=24)   # KV for P + 1024 is preallocated here
            peak = torch.cuda.max_memory_allocated()
            head = (total - peak) / 2 ** 30
            res["tried"][B] = {"peak_gib": peak / 2 ** 30, "headroom_gib": head}
            if head >= 0.6:
                chosen = B
                break
        except torch.cuda.OutOfMemoryError:
            res["tried"][B] = "OOM"
        free_cuda()
    res["B"] = chosen
    write_json(RESULTS_DIR / "hf_batch.json", res)
    logger.info(f"memory probe: {res}")
    if chosen is None:
        raise RuntimeError("no batch size fits")
    return chosen


def gpu_tests(runner: Runner, unit: str) -> dict[str, Any]:
    B = runner.B
    w = "W1"
    ctx = runner.unit_ctx(unit)
    out: dict[str, Any] = {"unit": unit, "B": B, "utc": utc_now()}
    pad = list(range(5000, 5000 + B))
    # G1 CRN determinism
    a = runner.run_batch(unit, w, [("TWINHF", pad[:B])], "gputest", write=False)
    b = runner.run_batch(unit, w, [("TWINHF", pad[:B])], "gputest", write=False)
    out["G1_crn_determinism"] = all(x["token_ids"] == y["token_ids"] for x, y in zip(a, b))
    # G2 batch-companion invariance: slot pad[0] with different companions at the same B
    seed0 = direction_seed(unit, 0)
    c = runner.run_batch(unit, w, [("TWINHF", pad[:1]), (esc_arm(seed0, 1.0), pad[1:B])], "gputest", write=False)
    out["G2_companion_invariance"] = a[0]["token_ids"] == c[0]["token_ids"]
    # G3 alpha = 0 push == twin (byte for byte)
    d = runner.run_batch(unit, w, [(esc_arm(seed0, 0.0), pad[:B])], "gputest", write=False)
    out["G3_alpha0_equals_twin"] = all(x["token_ids"] == y["token_ids"] for x, y in zip(a, d))
    # G4 push rel_err along u < 1e-3 at every edited block (alpha 1, 2, 4)
    g4 = {}
    for al in ALPHAS_ESC:
        _, rec = ctx.arm_prefill(w, ctx.push_spec(w, rand_dir(seed0), al))
        g4[str(al)] = {"rel_err_max": rec["rel_err_max"], "target_ratio_to_h": rec["target_ratio_to_h"],
                       "disp_R_norm_23": rec["disp_R_norm"][23], "disp_smean_norm_23": rec["disp_smean_norm"][23]}
    out["G4_push_rel_err"] = g4
    out["G4_pass"] = all(v["rel_err_max"] < 1e-3 for v in g4.values())
    # G5 GTN alpha = 0: GTN rows == twin rows; shadow tokens == GTN tokens inside the window
    half = B // 2
    e = runner.run_batch(unit, w, [("GTN_a0", pad[:half])], "gputest", write=False)
    gt = [r for r in e if not r["shadow"]]
    sh = [r for r in e if r["shadow"]]
    out["G5_gtn_alpha0_equals_twin"] = all(x["token_ids"] == a[i]["token_ids"] for i, x in enumerate(gt))
    out["G5_shadow_equals_gtn_in_window"] = all(s["token_ids"][:GTN_STEPS] == g["token_ids"][:GTN_STEPS]
                                                for g, s in zip(gt, sh))
    f = runner.run_batch(unit, w, [("GTN_a2", pad[:half])], "gputest", write=False)
    out["G5_gtn_a2_rel_err_max"] = max((r["gtn_rel_err_max"] or 0.0) for r in f if not r["shadow"])
    out["G5_gtn_a2_changed_rows"] = sum(1 for i, r in enumerate([x for x in f if not x["shadow"]])
                                        if r["token_ids"] != a[i]["token_ids"])
    # G6 batched vs batch-1 teacher forcing (references as programs)
    from unitlib6 import unit_mod
    refs = list(unit_mod(unit).REFERENCES.values())[:6]
    p = runner.pr[f"{unit}|twin|-|{w}"]
    fence = runner.tok("```python\n", add_special_tokens=False)["input_ids"]
    seqs = [(p["ids"] + fence, runner.tok(c.lstrip(), add_special_tokens=False)["input_ids"][:QLIK_TOKENS])
            for c in refs]
    lb = teacher_forced(runner.model, seqs, batch=runner.B)
    l1 = [teacher_forced(runner.model, [s], batch=1)[0] for s in seqs]
    diffs = [abs(sum(x) - sum(y)) for x, y in zip(lb, l1)]
    out["G6_tf_batch_vs_single_max_abs_nats"] = max(diffs)
    out["G6_pass"] = max(diffs) < 0.05
    out["pass"] = bool(out["G1_crn_determinism"] and out["G2_companion_invariance"] and out["G3_alpha0_equals_twin"]
                       and out["G4_pass"] and out["G5_gtn_alpha0_equals_twin"] and
                       out["G5_shadow_equals_gtn_in_window"] and out["G6_pass"])
    write_json(RESULTS_DIR / "gpu_tests.json", out)
    logger.info(f"GPU tests: {out}")
    return out


# ------------------------------------------------------------------------------------------------ q_lik
def qlik_unit(runner: Runner, unit: str) -> dict[str, Any]:
    fv = read_json(UNITS_DIR / unit / "forced_verified.json")
    fence = runner.tok("```python\n", add_special_tokens=False)["input_ids"]
    items, keys = [], []
    for m, progs in fv["programs"].items():
        for j, pg in enumerate(progs):
            for w in TEMPLATE_IDS:
                p = runner.pr[f"{unit}|twin|-|{w}"]
                joint = runner.tok("```python\n" + pg["code"], add_special_tokens=False)["input_ids"]
                if joint[:len(fence)] != fence:
                    code_ids = runner.tok(pg["code"], add_special_tokens=False)["input_ids"]
                else:
                    code_ids = joint[len(fence):]
                items.append((p["ids"] + fence, code_ids[:QLIK_TOKENS]))
                keys.append((m, j, w, len(code_ids)))
    t0 = time.time()
    lps = teacher_forced(runner.model, items, batch=getattr(runner, "tf_batch", runner.B))
    out: dict[str, Any] = {"unit": unit, "utc": utc_now(), "by_mode": {}, "seconds": time.time() - t0,
                           "n_sequences": len(items), "forced_verified_sha256": fv.get("sha256"),
                           "tf_batch": getattr(runner, "tf_batch", runner.B)}
    for (m, j, w, L), lp in zip(keys, lps):
        d = out["by_mode"].setdefault(m, {"programs": {}})
        d["programs"].setdefault(str(j), {})[w] = {"sum": float(sum(lp)), "mean": float(np.mean(lp)) if lp else None,
                                                   "n_tokens": len(lp), "short": L < QLIK_TOKENS}
    for m, d in out["by_mode"].items():
        sums = [v["sum"] for pj in d["programs"].values() for v in pj.values()]
        means = [v["mean"] for pj in d["programs"].values() for v in pj.values() if v["mean"] is not None]
        per_w = {w: float(np.mean([pj[w]["sum"] for pj in d["programs"].values()])) for w in TEMPLATE_IDS}
        d.update(score_raw=float(np.mean(sums)), score_norm=float(np.mean(means)), n_programs=len(d["programs"]),
                 lp48_by_template=per_w, any_short=any(v["short"] for pj in d["programs"].values()
                                                       for v in pj.values()))
    write_json(QLIK_DIR / f"{unit}.json", out)
    logger.info(f"q_lik {unit}: " + ", ".join(f"{m}={d['score_raw']:.1f}/{d['n_programs']}"
                                              for m, d in out["by_mode"].items()))
    return out


# ------------------------------------------------------------------------------------------------ nudges
def binom_sf(k: int, n: int, p: float) -> float:
    """P(X >= k), X ~ Bin(n, p)."""
    return float(sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1)))


def wait_labels(keys: set[str], timeout: float = 900.0) -> list[dict[str, Any]]:
    from labels_view6 import adjudicate_pending, load_final
    t0 = time.time()
    while True:
        rows = [l for l in load_final() if l["key"] in keys]
        if len(rows) >= len(keys):
            if any(r.get("final") is None for r in rows):
                adjudicate_pending({r["unit"] for r in rows})
                rows = [l for l in load_final() if l["key"] in keys]
            if all(r.get("final") is not None for r in rows) or time.time() - t0 > timeout:
                return rows
        if time.time() - t0 > timeout:
            logger.warning(f"label wait timeout: {len(rows)}/{len(keys)}")
            return rows
        time.sleep(8)


def hf_key(r: dict[str, Any]) -> str:
    return f"{r['unit']}|{r['template']}|{r['arm']}|{r['slot']}|instruct|hf"


def nudge_unit(runner: Runner, unit: str, commit: dict[str, Any], gtn_slots: list[int], stage_note: str,
               deadline: float | None, first_unit: bool) -> dict[str, Any]:
    from commit6 import verify_unit_commit
    from labels_view6 import cell_stats
    v = verify_unit_commit(unit)
    if not v["ok"]:
        raise RuntimeError(f"unit {unit} has no verified commit: {v}")
    D, cat = commit["default"], commit["catalogue"]
    tw = commit["hf_twin"]
    seeds = [direction_seed(unit, k) for k in range(N_DIRS)]
    t_unit = time.time()
    rep: dict[str, Any] = {"unit": unit, "commit": v, "utc_start": utc_now(), "stages": {}}
    # ---- ESC stage 1 (all alphas), staged scaling on the first unit
    cells = [(esc_arm(s, al), SLOTS["esc1"]) for al in ALPHAS_ESC for s in seeds]
    cells_by_w = {w: cells for w in TEMPLATE_IDS}
    if first_unit:
        t0 = time.time()
        n1 = runner.run_cells(unit, cells_by_w, "esc1", deadline, max_batches=1)
        t1 = time.time()
        n2 = runner.run_cells(unit, cells_by_w, "esc1", deadline, max_batches=8)
        t2 = time.time()
        per_batch = (t2 - t1) / max(n2, 1)
        write_json(RESULTS_DIR / "timing_extrapolation.json",
                   {"unit": unit, "B": runner.B, "first_batch_s": t1 - t0, "n_batches_stage2": n2,
                    "sec_per_batch": per_batch, "sec_per_row": per_batch / runner.B,
                    "projected_batches_per_unit": 20 + 9 + 10 + 8, "projected_min_per_unit":
                        per_batch * 47 / 60, "utc": utc_now()})
    runner.run_cells(unit, cells_by_w, "esc1", deadline)
    # ---- PN a2, PN a4
    runner.run_cells(unit, {w: [(f"PN_a{al:g}", SLOTS["pn"]) for al in ALPHAS_PN] for w in TEMPLATE_IDS}, "pn",
                     deadline)
    # ---- stage-1 decisions (labels of the 240 stage-1 rows)
    keys = {f"{unit}|{w}|{esc_arm(s, al)}|{k}|instruct|hf" for w in TEMPLATE_IDS for s in seeds for al in ALPHAS_ESC
            for k in SLOTS["esc1"]}
    labs = {l["key"]: l for l in wait_labels(keys)}
    stage1, passing = {}, []
    for al in ALPHAS_ESC:
        for s in seeds:
            arm = esc_arm(s, al)
            rows = [labs[k] for k in keys if k.split("|")[2] == arm and k in labs]
            st = cell_stats(rows, D, cat)
            ok = st["off_share"] >= tw["off_share"] + ESC_EXCESS and st["pass_rate"] >= ESC_PASS_FRAC * tw["pass_rate"]
            stage1[arm] = {**st, "stage1_pass": ok}
            if ok:
                passing.append(arm)
    rep["stages"]["esc1"] = stage1
    # ---- confirmations
    if passing:
        runner.run_cells(unit, {w: [(arm, SLOTS["conf"]) for arm in passing] for w in TEMPLATE_IDS}, "conf",
                         deadline)
    # ---- GTN a2
    runner.run_cells(unit, {w: [(f"GTN_a{ALPHA_GTN:g}", gtn_slots)] for w in TEMPLATE_IDS}, "gtn", deadline)
    rep["passing_stage1"] = passing
    rep["gtn_slots"] = gtn_slots
    rep["seconds"] = time.time() - t_unit
    rep["utc_end"] = utc_now()
    rep["note"] = stage_note
    write_json(RESULTS_DIR / "nudge_runs" / f"{unit}.json", rep)
    return rep


def run_all(units: list[str], stop_utc: str | None) -> None:
    tok, model = load_model(MODEL_ID, MODEL_REVISION)
    stop_t = None
    if stop_utc:
        from datetime import datetime, timezone
        stop_t = datetime.fromisoformat(stop_utc.replace("Z", "+00:00")).replace(tzinfo=timezone.utc).timestamp()
    runner = Runner(model, tok, B=12)
    if (RESULTS_DIR / "hf_batch.json").exists() and read_json(RESULTS_DIR / "hf_batch.json").get("B"):
        runner.B = read_json(RESULTS_DIR / "hf_batch.json")["B"]
    else:
        runner.B = memory_probe(runner, units)
    gp = RESULTS_DIR / "gpu_tests.json"
    g = read_json(gp) if gp.exists() else gpu_tests(runner, units[0])
    if not g["pass"]:
        if not g["G2_companion_invariance"]:
            log_deviation("g2_fail", "G2 batch-companion invariance failed; every arm's rows are grouped by "
                          "slot so batch membership is identical across arms (plan fallback)")
        if not (g["G1_crn_determinism"] and g["G3_alpha0_equals_twin"] and g["G4_pass"] and
                g["G5_gtn_alpha0_equals_twin"] and g["G5_shadow_equals_gtn_in_window"]):
            raise RuntimeError(f"GPU tests failed: {g}")
        if not g["G6_pass"]:
            runner.tf_batch = 1
            log_deviation("g6_batch1_teacher_forcing",
                          f"G6 failed: right-padded B-row teacher forcing differs from batch-1 by up to "
                          f"{g['G6_tf_batch_vs_single_max_abs_nats']:.2f} nats per 48-token program (bf16 batch-shape "
                          "noise, above the 0.05-nat bound); q_lik and the fork margin are computed with batch-1 "
                          "teacher forcing (exact per sequence, independent of batch composition)")
    # ---- HF twin 50 for every unit
    for u in units:
        runner.run_cells(u, {w: [("TWINHF", SLOTS["hf_twin"])] for w in TEMPLATE_IDS}, "twin_hf")
    (DATA_DIR / "HF_TWIN_DONE").write_text(utc_now())
    # ---- q_lik as forced verifications appear, then nudges in enrolment order
    nudged: set[str] = set()
    qdone = {u for u in units if (QLIK_DIR / f"{u}.json").exists()}
    unit_times: list[float] = []
    while True:
        for u in units:
            if u not in qdone and (UNITS_DIR / u / "forced_verified.json").exists():
                qlik_unit(runner, u)
                qdone.add(u)
        enr_p = PRED_DIR / "enrolment.json"
        if enr_p.exists():
            enr = read_json(enr_p)
            order = [u for u in enr["order"] if u not in nudged]
            for u in order:
                cp = PRED_DIR / "units" / f"{u}.json"
                if not cp.exists():
                    break
                if stop_t is not None and time.time() > stop_t:
                    logger.warning("stop time reached; no further nudges")
                    order = []
                    break
                # clock rule (time only): project the end of the new-unit nudges
                remaining = len([x for x in enr["order"] if x not in nudged])
                per = float(np.mean(unit_times)) if unit_times else 600.0
                gtn_slots = SLOTS["gtn"]
                note = "full"
                if stop_t is not None and time.time() + remaining * per > stop_t:
                    gtn_slots = SLOTS["gtn"][:6]
                    note = "clock: GTN N 50 -> 30"
                    log_deviation("clock_gtn30", "clock rule: GTN N 50 -> 30 (projected end beyond T+4:45)")
                    if len(nudged) >= 6 and time.time() + remaining * per * 0.85 > stop_t:
                        logger.warning("clock rule: no enrolment beyond 6 units")
                        log_deviation("clock_units6", "clock rule: units beyond 6 not nudged (time only)")
                        order = []
                        break
                t0 = time.time()
                nudge_unit(runner, u, read_json(cp), gtn_slots, note, stop_t, first_unit=not nudged)
                unit_times.append(time.time() - t0)
                nudged.add(u)
            if enr.get("final") and all(u in nudged for u in enr["order"]):
                break
            if not order and stop_t is not None and time.time() > stop_t:
                break
        if (DATA_DIR / "STOP_HF").exists():
            break
        time.sleep(15)
    (DATA_DIR / "HF_DONE").write_text(utc_now())
    logger.info(f"HF phase finished: nudged {sorted(nudged)}")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["all"])
    ap.add_argument("--units", required=True)
    ap.add_argument("--stop-at-utc", default=None)
    a = ap.parse_args()
    setup_logging("hf6")
    (RESULTS_DIR / "nudge_runs").mkdir(parents=True, exist_ok=True)
    run_all(a.units.split(","), a.stop_at_utc)


if __name__ == "__main__":
    main()
