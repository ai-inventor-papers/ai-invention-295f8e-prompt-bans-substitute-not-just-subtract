#!/usr/bin/env python3
"""S1 screen file and S2 power expectation (CPU).

S1 recomputes, from exp17 data/labels.jsonl (FP8, RTX 2000 Ada) and exp13 data/samples.jsonl (bf16 HF, protocol-v4
unit), per task in {T1, T2, T03} and alpha in {1, 2}: per random direction N, off-default share minus the twin's (same
slots k 0-9), pass ratio (pass rate / twin pass rate), the escape flag, E_t = escapes / directions run, and the
push-landing distribution (off-default labels of each direction weighted by its excess).

ESCAPE RULE. The 'N=10 rule (no top-up)' is not defined anywhere on the run volume, so it is reconstructed here and
both readings are reported: N=10 means the screen's 10 slots per template (k 0-9, N = 50 per direction) with no top-up
to k 10-19; rule A = excess >= 0.20; rule B = excess >= 0.20 AND pass ratio >= 0.85 (B is the descriptive flag used
downstream). The headline counts to reproduce are T03 7/15 and T2 3/15 escaping at alpha 1 (testing plan (4));
mismatches are reported, not fixed.

S2 simulates the subset-averaged changed-seed count C_PN for 20 seeds and 6 directions drawn with replacement from
the screen directions (per-seed change probability p_d = max(0, excess)), 20,000 reps, and P(C_T >= 2) under exp12's
same-seed change rate of 1/30. No design change follows from it.
"""

from __future__ import annotations

import itertools
import math
from collections import Counter, defaultdict
from typing import Any

import numpy as np
from loguru import logger

from cfg import RESULTS_DIR, ROOT, read_jsonl, sha256_file, utc_now, write_json
from cfg4 import C1_EVENT_SET, DEFAULT4, PN_SEEDS

EXCL = {"invalid", "disputed", "unresolved", None}
SCREEN = RESULTS_DIR / "screen.json"
EXPECT = RESULTS_DIR / "expectations.json"


def _stats(rows: list[dict[str, Any]], default: str) -> dict[str, Any]:
    att = [r for r in rows if r.get("valid", True) and r.get("label") not in EXCL]
    off = [r for r in att if r["label"] != default]
    passed = sum(1 for r in rows if str(r.get("passed")) in ("True", "true", "1") or r.get("passed") is True)
    return {"N": len(rows), "n_attempted": len(att), "n_off": len(off), "share_off": len(off) / max(len(att), 1),
            "pass_rate": passed / max(len(rows), 1), "landing": dict(Counter(r["label"] for r in off).most_common())}


def screen_exp17() -> dict[str, Any]:
    rows = read_jsonl(ROOT / "inputs/exp17/data/labels.jsonl")
    out: dict[str, Any] = {}
    for t in ("T2", "T03", "T1"):
        de = DEFAULT4[t]
        tw_all = [r for r in rows if r["task"] == t and r["arm"] == "NEUTRAL"]
        tw10 = [r for r in tw_all if int(r["sample_id"]) < 10]
        twin = _stats(tw10, de)
        cell: dict[str, Any] = {"default": de, "twin_k0_9": twin, "twin_k0_19": _stats(tw_all, de), "alpha": {}}
        for alpha in ("1.0", "2.0"):
            dirs = {}
            for s in range(9001, 9016):
                rr = [r for r in rows if r["task"] == t and r["arm"] == f"RAND{s}_a{alpha}"]
                if not rr:
                    continue
                st = _stats(rr, de)
                st["excess"] = st["share_off"] - twin["share_off"]
                st["pass_ratio"] = st["pass_rate"] / max(twin["pass_rate"], 1e-9)
                st["escape_ruleA"] = st["excess"] >= 0.20
                st["escape_ruleB"] = st["excess"] >= 0.20 and st["pass_ratio"] >= 0.85
                st["modal_survivor"] = next(iter(st["landing"]), None)
                dirs[f"rand{s}"] = st
            if not dirs:
                continue
            land: dict[str, float] = defaultdict(float)
            for st in dirs.values():
                if st["n_off"] and st["excess"] > 0:
                    for lab, c in st["landing"].items():
                        land[lab] += st["excess"] * c / st["n_off"]
            tot = sum(land.values())
            cell["alpha"][alpha] = {
                "directions": dirs, "n_directions": len(dirs),
                "escapes_ruleA": sum(d["escape_ruleA"] for d in dirs.values()),
                "escapes_ruleB": sum(d["escape_ruleB"] for d in dirs.values()),
                "E_t_ruleB": sum(d["escape_ruleB"] for d in dirs.values()) / len(dirs),
                "E_t_ruleA": sum(d["escape_ruleA"] for d in dirs.values()) / len(dirs),
                "mean_excess": float(np.mean([d["excess"] for d in dirs.values()])),
                "push_landing_weighted": {k: v / tot for k, v in sorted(land.items(), key=lambda x: -x[1])} if tot else {},
                "push_landing_modal": max(land, key=land.get) if land else None}
        out[t] = cell
    return out


def screen_exp13() -> dict[str, Any]:
    rows = [r for r in read_jsonl(ROOT / "inputs/exp13/data/samples.jsonl") if r.get("task") == "T03"]
    for r in rows:
        r["valid"] = r.get("label") not in ("invalid", None)
    de = "full_sort"
    out = {"note": "exp13 bench screen arms (bf16 HF on an RTX 4090, protocol-v4 unit = exp13 norms_T03.npz), "
                   "T03 only; rand1-3 are its matched-norm random directions at the task-spec states, blocks 12-23"}
    for arm in ("twin", "hf_twin", "rand1", "rand2", "rand3", "bandpatch", "ban"):
        rr = [r for r in rows if r["condition"] == arm]
        if rr:
            out[arm] = _stats(rr, de)
    tw = out.get("hf_twin") or out.get("twin")
    for arm in ("rand1", "rand2", "rand3"):
        if arm in out and tw:
            out[arm]["excess_vs_hf_twin"] = out[arm]["share_off"] - tw["share_off"]
            out[arm]["pass_ratio"] = out[arm]["pass_rate"] / max(tw["pass_rate"], 1e-9)
    return out


# ------------------------------------------------------------------------------------------------ S2
def simulate_cpn(p_pool: list[float], landings: list[dict[str, int]], twin_share: float, reps: int = 20000,
                 n_seeds: int = 20, n_dirs: int = 6, k: int = 3, seed: int = 20261021) -> dict[str, Any]:
    """Monte Carlo of C_PN with categorical labels: NOPN is off-default w.p. twin_share (label 'twin_off'); PN(d) is
    off-default w.p. p_d with a label drawn from d's landing distribution (or 'off' if none)."""
    rng = np.random.default_rng(seed)
    subs = list(itertools.combinations(range(n_dirs), k))
    vals = np.empty(reps)
    xs_means = np.empty(reps)
    for r in range(reps):
        di = rng.integers(0, len(p_pool), size=n_dirs)
        nopn = np.where(rng.random(n_seeds) < twin_share, 1, 0)           # 0 = default, 1 = other
        lab = np.zeros((n_seeds, n_dirs), dtype=np.int64)
        for j, d in enumerate(di):
            off = rng.random(n_seeds) < p_pool[d]
            land = landings[d]
            if land:
                names = list(land)
                pr = np.array([land[n] for n in names], float)
                pr /= pr.sum()
                pick = rng.choice(len(names), size=n_seeds, p=pr) + 2      # 2.. = landing labels
            else:
                pick = np.full(n_seeds, 2)
            lab[:, j] = np.where(off, pick, 0)
        tot = 0.0
        per_seed = np.zeros(n_seeds)
        for S in subs:
            m = np.concatenate([nopn[:, None], lab[:, list(S)]], axis=1)
            ch = (m != m[:, :1]).any(axis=1)
            tot += ch.sum()
            per_seed += ch
        vals[r] = tot / len(subs)
        xs_means[r] = per_seed.mean() / len(subs)
    return {"E_C_PN": float(vals.mean()), "sd_C_PN": float(vals.std()), "P_C_PN_ge5": float((vals >= 5).mean()),
            "q05": float(np.quantile(vals, 0.05)), "q50": float(np.quantile(vals, 0.5)),
            "q95": float(np.quantile(vals, 0.95)), "reps": reps}


def power_hcon(p2: list[float], l2: list[dict], p3: list[float], l3: list[dict], rate_t: float = 1 / 30,
               reps: int = 1000, flips: int = 4000, seed: int = 99) -> dict[str, Any]:
    """P(sign-flip p < 0.05) for the pooled x_s contrast (T2 + T03, 40 seeds) under the screen pools."""
    rng = np.random.default_rng(seed)
    subs = list(itertools.combinations(range(6), 3))
    hits = 0
    for _ in range(reps):
        xs = []
        for pool, lands in ((p2, l2), (p3, l3)):
            di = rng.integers(0, len(pool), size=6)
            off = np.stack([rng.random(20) < pool[d] for d in di], axis=1)
            ch = np.array([[off[s, list(S)].any() for S in subs] for s in range(20)]).mean(axis=1)
            ct = (rng.random(20) < rate_t).astype(float)
            xs.append(ch - ct)
        x = np.concatenate(xs)
        if np.allclose(x, 0):
            continue
        signs = rng.integers(0, 2, size=(flips, len(x))) * 2 - 1
        p = (1 + ((signs * x).mean(axis=1) >= x.mean() - 1e-12).sum()) / (1 + flips)
        hits += p < 0.05
    return {"P_HCON_p_lt_0.05": hits / reps, "reps": reps, "flips": flips}


def run_screen() -> dict[str, Any]:
    s17 = screen_exp17()
    s13 = screen_exp13()
    import numpy as _np
    n17 = _np.load(ROOT / "directions/norms_T03.npy")
    n13 = _np.load(ROOT / "inputs/exp13/results/tensors/norms_T03.npz")["norm"]
    ratio = n17 / n13
    unit = {"median_ratio_exp17_over_exp13_per_block": [float(x) for x in _np.median(ratio, axis=1)],
            "overall_median_ratio": float(_np.median(ratio)),
            "max_rel_diff": float(_np.max(_np.abs(n17 - n13) / _np.abs(n13))),
            "deviation": "max relative difference > 1e-4: exp17 recomputed the T03 unit under FP8 from its own "
                         "ban/twin prompts; the 2x2 uses the protocol-v4 unit (exp13), so alpha 1 on T03 here is "
                         "about 1/ratio of the screen's alpha-1 push"}
    head = {"T03_alpha1": (s17["T03"]["alpha"]["1.0"]["escapes_ruleA"], s17["T03"]["alpha"]["1.0"]["escapes_ruleB"]),
            "T2_alpha1": (s17["T2"]["alpha"]["1.0"]["escapes_ruleA"], s17["T2"]["alpha"]["1.0"]["escapes_ruleB"])}
    check = {"expected": {"T03_alpha1": 7, "T2_alpha1": 3},
             "ruleA": {"T03_alpha1": head["T03_alpha1"][0], "T2_alpha1": head["T2_alpha1"][0]},
             "ruleB": {"T03_alpha1": head["T03_alpha1"][1], "T2_alpha1": head["T2_alpha1"][1]}}
    check["ruleA_matches"] = check["ruleA"] == check["expected"]
    check["ruleB_matches"] = check["ruleB"] == check["expected"]
    screen = {"created_utc": utc_now(), "source": {"exp17": "inputs/exp17/data/labels.jsonl",
                                                    "exp13": "inputs/exp13/data/samples.jsonl"},
              "escape_rule": "N=10 slots per template (k 0-9, N=50), no top-up; rule A: excess >= 0.20; rule B: "
                             "excess >= 0.20 and pass ratio >= 0.85 (B = descriptive flag downstream)",
              "headline_check": check, "exp17": s17, "exp13_T03": s13, "T03_unit_comparison": unit,
              "C1_event_set_frozen": C1_EVENT_SET, "pn_direction_seeds_this_artifact": list(PN_SEEDS)}
    write_json(SCREEN, screen)
    h = sha256_file(SCREEN)
    (ROOT / "predictions").mkdir(exist_ok=True)
    (ROOT / "predictions/screen.sha256").write_text(h + "  results/screen.json\n")
    logger.info(f"S1 screen.json sha256 {h[:16]}; headline check {check}")
    # ---------------------------------------------------------------- S2
    exp: dict[str, Any] = {"created_utc": utc_now(), "method": "20,000 MC reps; 6 directions with replacement from "
                           "the task's screen directions; p_d = max(0, excess); landing labels from each direction's "
                           "off-default distribution; NOPN off-default w.p. the twin share", "cells": {}}
    pools = {}
    for t in ("T2", "T03", "T1"):
        tw = s17[t]["twin_k0_9"]["share_off"]
        for alpha in ("1.0", "2.0"):
            a = s17[t]["alpha"].get(alpha)
            if not a:
                continue
            p = [max(0.0, d["excess"]) for d in a["directions"].values()]
            l = [d["landing"] for d in a["directions"].values()]
            pools[(t, alpha)] = (p, l)
            sim = simulate_cpn(p, l, tw, seed=hash((t, alpha)) % 2**32)
            exp["cells"][f"{t}_a{alpha}"] = {**sim, "n_screen_directions": len(p), "mean_p": float(np.mean(p))}
            logger.info(f"S2 {t} a{alpha}: E[C_PN]={sim['E_C_PN']:.2f} P(>=5)={sim['P_C_PN_ge5']:.3f}")
    # T03 unit-adjusted sensitivities
    r = unit["overall_median_ratio"]
    p, l = pools[("T03", "1.0")]
    sim_adj = simulate_cpn([min(1.0, x / r) for x in p], l, s17["T03"]["twin_k0_9"]["share_off"], seed=17)
    exp["T03_a1.0_unit_adjusted_linear_dose"] = {**sim_adj, "scale": 1 / r, "note": "p_d scaled by 1/ratio "
                                                 "(alpha 1 here ~ alpha 1/ratio at the screen's unit; linear dose)"}
    e13 = [s13[a] for a in ("rand1", "rand2", "rand3") if a in s13]
    if e13:
        p13 = [max(0.0, d.get("excess_vs_hf_twin", 0.0)) for d in e13]
        sim13 = simulate_cpn(p13, [d["landing"] for d in e13], s13["hf_twin"]["share_off"], seed=13)
        exp["T03_a1.0_exp13_protocol_unit_pool"] = {**sim13, "p_pool": p13, "note": "pool = exp13 rand1-3 (bf16, "
                                                    "protocol-v4 unit, alpha 1), 3 directions"}
    # temperature
    q = 1 / 30
    pt = 1 - (1 - q) ** 20 - 20 * q * (1 - q) ** 19
    exp["temperature"] = {"rate_per_seed": q, "P_C_T_ge2": pt, "source": "exp12 same-seed CRN: 0/30 seeds changed "
                          "in 10 of 12 cells (rate 1/30 used as the stated prior)"}
    exp["H_CON_power"] = power_hcon(*pools[("T2", "1.0")], *pools[("T03", "1.0")])
    exp["note"] = ("No design change follows: more directions only shrink the lottery variance, they do not raise "
                   "E[C_PN]. The T03 rows are optimistic: the screen used exp17's T03 unit, ~"
                   f"{r:.2f}x the protocol-v4 unit used here.")
    write_json(EXPECT, exp)
    logger.info(f"S2 temperature P(C_T>=2)={pt:.3f}; H-CON power {exp['H_CON_power']}")
    return {"screen_sha256": h, "expectations": exp}
