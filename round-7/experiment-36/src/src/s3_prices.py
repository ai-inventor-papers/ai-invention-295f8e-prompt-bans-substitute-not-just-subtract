#!/usr/bin/env python3
"""S3 prices (hashed in COMMIT #2 before the first S3 sample): plan noise at the moving design D* against iteration
5's knobs, each priced on its own full-simplex randomisation hull (exp27 src/hull_full.py + src/hull_exp20.py,
vendored unchanged and loaded by file path).

Hull settings per (task, class), TWIN first: PN* = {TWIN, D*_a1, D*_a2}; BINT = {TWIN, BINT}; EAP = {TWIN, EAP};
IFG = {TWIN, IFG_hot}; TEMP = {TWIN, T1.3}; TOPK10 = {TWIN, TOPK10}. Slots W1-W5 x k 0-9 (N 50 per arm). A setting
= correct-only labels ('other' is its own category) + pass rate = passed / N (invalid and failed rows stay in N).
Knob rows: exp27's rows relabelled here when the knob check reused them (arm 'E27:<knob>'), else this artifact's.
Point prices: hull_prices_full(n_draws 1,000, seed 0, frontier kept) -> H5 (max correct-only Hill-1 rarefied at
depth 25 at pass cost <= 0.05), P15, P20. Bootstrap: 2,000 replicates; each resamples k within each template jointly
for every arm of the task and re-selects every class's best mixture (grid 0.05 + local refinement 0.01, 200 draws;
exp27's replicate settings). Hill-0 (richness) and Hill-2 at the point H5 mixture as sensitivities.
Readings: WIN if P_boot(H5_PN* > H5_BINT) >= 0.8, LOSS if <= 0.2, else TIE; replay of iteration 5's rule
(D_t = H5_PN* - max(H5 BINT, EAP, IFG); PN* wins t if round(H5_PN*, 2) >= round(best text, 2)).

usage: .venv/bin/python src/s3_prices.py [g5|prices|retag|all]
"""

from __future__ import annotations

import importlib.util
import math
import multiprocessing as mp
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

import k_cfg as K  # noqa: E402
from k_cfg import DEFAULTS, LABELS, RESULTS, read_json, read_jsonl, write_json  # noqa: E402

V27SRC = K.V27 / "src"
D5 = ("T03", "T10", "T2", "T05", "T1")
KNOBS = ("BINT", "EAP", "IFG_hot", "T1.3", "TOPK10")
TEXT = ("BINT", "EAP", "IFG")
N_BOOT = 2000
BOOT_RAREFY = 200
BOOT_SEED5 = 20261021
TASK_INDEX = {"T03": 0, "T10": 1, "T2": 2, "T05": 3, "T1": 4}


def _load_hull():
    for name in ("hull_exp20", "hull_full"):
        if name not in sys.modules:
            spec = importlib.util.spec_from_file_location(name, V27SRC / f"{name}.py")
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod
            spec.loader.exec_module(mod)
    return sys.modules["hull_full"], sys.modules["hull_exp20"]


def classes(dstar: str, knob_src: dict[str, str]) -> dict[str, list[str]]:
    """knob_src[knob] = arm name holding that knob's rows for this task ('E27:<knob>' or '<knob>')."""
    return {"PN*": ["TWIN", f"{dstar}_a1", f"{dstar}_a2"], "BINT": ["TWIN", knob_src["BINT"]],
            "EAP": ["TWIN", knob_src["EAP"]], "IFG": ["TWIN", knob_src["IFG_hot"]],
            "TEMP": ["TWIN", knob_src["T1.3"]], "TOPK10": ["TWIN", knob_src["TOPK10"]]}


def load_index() -> dict[tuple[str, str], dict[tuple[str, int], dict[str, Any]]]:
    """(task, arm) -> {(w, k): {'label', 'passed'}} over this artifact's rows, knob rows and relabelled exp27 rows."""
    labs = {l["key"]: l for l in read_jsonl(LABELS)}
    idx: dict = defaultdict(dict)
    for name in ("raw_k.jsonl", "knobs_norm.jsonl", "reuse_exp27.jsonl"):
        for r in read_jsonl(K.RAW_DIR / name):
            k = int(r["sample_id"])
            if k > 9 or r["task"] not in D5:
                continue
            l = labs.get(K.row_key(r))
            if l is None:
                continue
            idx[(r["task"], r["arm"])][(r["template"], k)] = {"label": l.get("label") or "invalid",
                                                              "passed": bool(l.get("passed"))}
    return idx


def settings(idx, task: str, arms: list[str], mapping: list[tuple[str, int]] | None = None) -> list[dict] | None:
    out = []
    for a in arms:
        cell = idx.get((task, a))
        if not cell or len(cell) < 30:
            if a == "TWIN":
                return None
            continue
        rs = [cell[s] for s in mapping if s in cell] if mapping is not None else list(cell.values())
        if not rs:
            continue
        out.append({"arm": a, "correct_labels": [r["label"] for r in rs if r["passed"]],
                    "pass": sum(r["passed"] for r in rs) / len(rs), "n": len(rs)})
    if len(out) < 2 or out[0]["arm"] != "TWIN":
        return None
    return out


def hill_q_at(st: list[dict], w: list[float], n_draws: int = 1000, seed: int = 0) -> dict[str, float]:
    """Hill-0 (richness), Hill-1 and Hill-2 at mixture w under exp20's two-stage CRN draw (mirrors hill_of)."""
    _, h20 = _load_hull()
    hs = h20.HullSampler(st, n_draws=n_draws, seed=seed)
    w = np.asarray(w, dtype=float)
    a = w * hs.pass_
    if a.sum() <= 0:
        return {"hill0": float("nan"), "hill1": float("nan"), "hill2": float("nan")}
    pi = a / a.sum()
    cdf = np.cumsum(pi)
    cdf[-1] = 1.0
    j_of = np.searchsorted(cdf, hs.U, side="right").clip(max=len(pi) - 1)
    comp = 0
    for j in range(len(pi)):
        nj = (j_of == j).sum(1)
        if pi[j] > 0:
            comp = comp + np.take_along_axis(hs.C[j], nj[:, None, None], axis=1)[:, 0]
    comp = np.asarray(comp, dtype=float)
    p = comp / np.maximum(comp.sum(-1, keepdims=True), 1e-12)
    h0 = (comp > 0).sum(-1).mean()
    h2 = (1.0 / np.maximum((p ** 2).sum(-1), 1e-12)).mean()
    return {"hill0": float(h0), "hill1": float(h20.hill1(comp).mean()), "hill2": float(h2)}


def _boot_worker(args: tuple) -> list[dict[str, float]]:
    idx, task, cls_map, seeds = args
    hf, _ = _load_hull()
    slots_by_w = defaultdict(set)
    for (t, a), cell in idx.items():
        if t == task:
            for (w, k) in cell:
                slots_by_w[w].add(k)
    out = []
    for sd in seeds:
        rng = np.random.default_rng(sd)
        mapping = []
        for w in sorted(slots_by_w):
            ks = sorted(slots_by_w[w])
            draw = rng.choice(ks, size=len(ks), replace=True)
            mapping += [(w, int(k)) for k in draw]
        rec: dict[str, float] = {}
        for cls, arms in cls_map.items():
            st = settings(idx, task, arms, mapping)
            if st is None:
                continue
            k = len(st)
            r = hf.hull_prices_full(st, n_draws=BOOT_RAREFY, seed=int(sd % (2 ** 31)), step=0.05 if k <= 4 else 0.1,
                                    refine=True, refine_step=0.01)
            rec[cls] = r["H5"]
            rec[cls + "_P15"] = r["P15"]
            rec[cls + "_P20"] = r["P20"]
        out.append(rec)
    return out


def bootstrap(idx, task: str, cls_map: dict[str, list[str]], n_boot: int, n_workers: int) -> list[dict[str, float]]:
    tidx = {k: v for k, v in idx.items() if k[0] == task}
    seeds = [BOOT_SEED5 * 1000 + i + 7919 * TASK_INDEX[task] for i in range(n_boot)]
    chunks = [seeds[i::n_workers] for i in range(n_workers)]
    with ProcessPoolExecutor(max_workers=n_workers, mp_context=mp.get_context("spawn")) as ex:
        parts = list(ex.map(_boot_worker, [(tidx, task, cls_map, c) for c in chunks if c]))
    return [x for p in parts for x in p]


def ci(vals: list[float]) -> list[float | None]:
    v = [x for x in vals if x is not None and np.isfinite(x)]
    if not v:
        return [None, None]
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]


def knob_sources() -> dict[str, dict[str, str]]:
    kc = read_json(RESULTS / "knob_check.json") if (RESULTS / "knob_check.json").exists() else {"cells": {}}
    out = {}
    for t in D5:
        out[t] = {}
        for a in KNOBS:
            v = kc["cells"].get(f"{t}|{a}")
            out[t][a] = f"E27:{a}" if (v and v.get("reuse")) else a
    return out


def prices(n_boot: int = N_BOOT, n_workers: int = 16) -> dict[str, Any]:
    hf, _ = _load_hull()
    dstar = read_json(K.PRED / "commit2.json")["D_star"]
    idx = load_index()
    src = knob_sources()
    res: dict[str, Any] = {"D_star": dstar, "knob_sources": src, "per_task": {}, "cells": {}}
    boots = {}
    for t in D5:
        cm = classes(dstar, src[t])
        pt: dict[str, Any] = {}
        for cls, arms in cm.items():
            st = settings(idx, t, arms)
            if st is None:
                continue
            p = hf.hull_prices_full(st, n_draws=1000, seed=0, keep_frontier=True)
            pe = hf.hull_prices_full(st, n_draws=1000, seed=0, max_nonzero=2)
            p["H5_edge"] = pe["H5"]
            p["arms"] = [s["arm"] for s in st]
            p["n_per_arm"] = [s["n"] for s in st]
            p["pass_per_arm"] = [s["pass"] for s in st]
            if p.get("H5_mixture") is not None:
                p["hill_q_at_H5"] = hill_q_at(st, p["H5_mixture"])
            pt[cls] = p
        for arms in cm.values():
            for a in arms:
                cell = idx.get((t, a), {})
                if cell:
                    rs = list(cell.values())
                    corr = [r["label"] for r in rs if r["passed"]]
                    res["cells"][f"{t}|{a}"] = {"N": len(rs), "pass": sum(r["passed"] for r in rs) / len(rs),
                                                "correct_composition": dict(Counter(corr)),
                                                "correct_off_default": sum(1 for x in corr if x != DEFAULTS[t])}
        res["per_task"][t] = pt
        logger.info(f"S3 point prices {t}: " + ", ".join(f"{c} {v['H5']:.2f}" for c, v in pt.items()))
        boots[t] = bootstrap(idx, t, cm, n_boot, n_workers)
    write_json(RESULTS / "s3_bootstrap.json", boots)
    # readings
    read: dict[str, Any] = {}
    wins_tie = 0
    replay_wins, dts = 0, {}
    for t in D5:
        pt = res["per_task"][t]
        if "PN*" not in pt or "BINT" not in pt:
            read[t] = {"evaluable": False}
            continue
        bt = boots[t]
        cmp = [b["PN*"] > b["BINT"] for b in bt if "PN*" in b and "BINT" in b and np.isfinite(b["PN*"])
               and np.isfinite(b["BINT"])]
        pw = float(np.mean(cmp)) if cmp else None
        verdict = "WIN" if pw is not None and pw >= 0.8 else ("LOSS" if pw is not None and pw <= 0.2 else "TIE")
        wins_tie += verdict in ("WIN", "TIE")
        tx = {c: pt[c]["H5"] for c in TEXT if c in pt and np.isfinite(pt[c]["H5"])}
        best_c = max(tx, key=lambda c: tx[c]) if tx else None
        d_t = pt["PN*"]["H5"] - tx[best_c] if best_c else None
        rw = bool(best_c and round(pt["PN*"]["H5"], 2) >= round(tx[best_c], 2))
        replay_wins += rw
        dts[t] = d_t
        p_ge_best = [b["PN*"] >= max(b[c] for c in TEXT if c in b) for b in bt
                     if "PN*" in b and any(c in b for c in TEXT)]
        read[t] = {"H5": {c: v["H5"] for c, v in pt.items()}, "P15": {c: v["P15"] for c, v in pt.items()},
                   "P20": {c: v["P20"] for c, v in pt.items()}, "P_boot_PN_gt_BINT": pw, "vs_BINT": verdict,
                   "H5_ci95": {c: ci([b.get(c) for b in bt]) for c in pt},
                   "best_text": best_c, "D_t": d_t, "replay_PN_ge_best_text": rw,
                   "P_boot_PN_ge_best_text": float(np.mean(p_ge_best)) if p_ge_best else None}
    nrep = min((len(boots[t]) for t in D5), default=0)
    rep_dbar = []
    for i in range(nrep):
        d_ = []
        for t in D5:
            b = boots[t][i]
            tx = [b[c] for c in TEXT if c in b and np.isfinite(b[c])]
            if "PN*" in b and tx:
                d_.append(b["PN*"] - max(tx))
        if d_:
            rep_dbar.append(float(np.mean(d_)))
    res["readings"] = read
    res["headline"] = {"matches_or_beats_BINT": wins_tie, "of": len(D5), "committed_prediction": 3,
                       "H5_PNstar_ge_2": [t for t in D5 if read.get(t, {}).get("H5", {}).get("PN*", 0) >= 2.0],
                       "replay_iteration5_rule": {"PN_ge_best_text_wins": replay_wins, "threshold": 3,
                                                  "verdict": "SUPPORTED" if replay_wins >= 3 else "DISCONFIRMED",
                                                  "D_bar": float(np.mean([v for v in dts.values() if v is not None]))
                                                  if dts else None, "D_bar_ci95": ci(rep_dbar)}}
    write_json(RESULTS / "s3_prices.json", res)
    return res


def g5_gate() -> dict[str, Any]:
    """Vendored hull + exp27's own rows and labels reproduce exp27's H5 for T10 BINT (2.527) and T03 PN (1.984)."""
    hf, _ = _load_hull()
    labs = {r["sample_id"]: r for r in read_jsonl(K.E27 / "data" / "labels.jsonl")}
    idx: dict = defaultdict(dict)
    seen = set()
    for r in read_jsonl(K.E27 / "data" / "samples_raw.jsonl"):
        sid = r["sample_id"]
        if sid in seen or sid not in labs:
            continue
        seen.add(sid)
        l = labs[sid]
        idx[(r["task"], r["arm"])][(r["template"], int(r["slot"]))] = {"label": l.get("label") or "invalid",
                                                                       "passed": bool(l.get("passed"))}
    out = {}
    for t, cls, arms, ref in (("T10", "BINT", ["TWIN", "BINT"], 2.527), ("T03", "PN", ["TWIN", "PN_a1", "PN_a2"],
                                                                          1.984)):
        st = settings(idx, t, arms)
        p = hf.hull_prices_full(st, n_draws=1000, seed=0, keep_frontier=True)
        out[f"{t}|{cls}"] = {"H5": p["H5"], "exp27": ref, "abs_diff": abs(p["H5"] - ref),
                             "pass": abs(p["H5"] - ref) <= 0.01}
    out["pass"] = all(v["pass"] for v in out.values() if isinstance(v, dict))
    out["hull_unit_tests"] = hf.unit_tests()
    return out


def retag() -> dict[str, Any]:
    """Re-tag iteration 5's verdicts and state the corrected ones at D* (plan 5.5)."""
    import analysis_k as A

    rows = A.load_joined()
    dstar = read_json(K.PRED / "commit2.json")["D_star"]
    s3 = read_json(RESULTS / "s3_prices.json") if (RESULTS / "s3_prices.json").exists() else None
    mov = {}
    for t in D5:
        tw = A.cell(rows, t, "TWIN", K.K10)
        c2 = A.cell(rows, t, f"{dstar}_a2", K.K10)
        if not tw or not c2:
            continue
        dt, dc = A.describe(tw), A.describe(c2)
        exc_any = dc["Y_any"]["share"] - dt["Y_any"]["share"]
        exc_y = dc["Y"]["share"] - dt["Y"]["share"]
        ok_pass = dc["pass_rate"] >= 0.8 * dt["pass_rate"]
        mov[t] = {"twin_Y_any": dt["Y_any"]["share"], "Dstar_a2_Y_any": dc["Y_any"]["share"],
                  "excess_Y_any": exc_any, "excess_Y": exc_y, "pass_twin": dt["pass_rate"],
                  "pass_Dstar_a2": dc["pass_rate"], "pass_clause": ok_pass,
                  "movable": bool(exc_any >= 0.20 and ok_pass)}
    e27 = read_json(K.E27 / "results" / "claim_c.json")
    out = {
        "tag": "ban-free unit and iteration-5 seeds",
        "iteration5_plan_sampler_verdict": {"verdict": e27.get("verdict"), "wins": e27["primary"]["wins"],
                                            "tag": "ban-free unit and iteration-5 seeds"},
        "iteration5_movability_verdict": {"statement": "Extra arm A: T05/T06/T1/T2 lost 'movable' in bf16",
                                          "tag": "ban-free unit and iteration-5 seeds"},
        "D_star": dstar,
        "movability_at_D_star": mov,
        "rule": "movable := alpha-2 correct off-default share (Y_any) - twin >= 0.20 at pass >= 0.8 x twin",
    }
    if s3:
        h = s3["headline"]
        out["replacement_sentences"] = [
            f"iteration-7 correction: at the moving design D* = {dstar}, plan noise matches or beats base-written "
            f"intent on {h['matches_or_beats_BINT']} of 5 decisive tasks (committed prediction 3); under iteration "
            f"5's own rule it matches or beats the best text sampler on {h['replay_iteration5_rule']['PN_ge_best_text_wins']}"
            f" of 5 ({h['replay_iteration5_rule']['verdict']}).",
            "iteration-7 correction: movability at D* (alpha 2): " + ", ".join(
                f"{t} {'movable' if v['movable'] else 'not movable'} (excess {v['excess_Y_any']:+.2f}, pass "
                f"{v['pass_Dstar_a2']:.2f} vs twin {v['pass_twin']:.2f})" for t, v in mov.items()) +
            "; T06 untested here."]
    write_json(RESULTS / "retag.json", out)
    return out


@logger.catch(reraise=True)
def main() -> None:
    K.setup_logging("s3_prices")
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("g5", "all"):
        g = g5_gate()
        logger.info(f"G5: {g}")
        write_json(RESULTS / "g5_hull_gate.json", g)
    if what in ("prices", "all"):
        r = prices()
        logger.info(f"S3 headline: {r['headline']}")
    if what in ("retag", "all"):
        logger.info(f"retag: {retag()}")


if __name__ == "__main__":
    main()
