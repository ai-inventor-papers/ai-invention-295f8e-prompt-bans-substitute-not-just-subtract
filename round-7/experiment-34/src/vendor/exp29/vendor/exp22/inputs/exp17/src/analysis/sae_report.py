#!/usr/bin/env python3
"""9.4 0g report: FR_zero, FR_mean, KL, dCE, FVU, L0 per (model, text, layer); the frozen PASS rule and companions."""

from __future__ import annotations

import json
from typing import Any

import numpy as np

from cfg import E12, RESULTS_DIR, read_json

LAYERS = ["15", "20", "27"]


def _fr(clean: float, spl: float, abl: float) -> float:
    den = abl - clean
    return float((abl - spl) / den) if den != 0 else float("nan")


def cell(d: dict[str, Any]) -> dict[str, Any]:
    out = {"n_seq": d["n_seq"], "ce_clean": float(np.mean(d["ce_clean"])), "layers": {}}
    for L in LAYERS:
        x = d["layers"].get(L) or d["layers"].get(int(L))
        if x is None:
            continue
        cc = float(np.mean(d["ce_clean"]))
        cs, cz, cm = (float(np.mean(x["ce_sae"])), float(np.mean(x["ce_zero"])), float(np.mean(x["ce_mean"])))
        # per-sequence bootstrap of FR_zero
        a = np.array(d["ce_clean"])
        s, z = np.array(x["ce_sae"]), np.array(x["ce_zero"])
        rng = np.random.default_rng(int(L))
        bs = []
        for _ in range(2000):
            i = rng.integers(0, len(a), len(a))
            bs.append(_fr(a[i].mean(), s[i].mean(), z[i].mean()))
        out["layers"][L] = {"ce_sae": cs, "ce_zero": cz, "ce_mean": cm, "dce": cs - cc,
                            "fr_zero": _fr(cc, cs, cz), "fr_zero_ci95": [float(np.quantile(bs, 0.025)),
                                                                        float(np.quantile(bs, 0.975))],
                            "fr_mean": _fr(cc, cs, cm), "kl_sae": float(np.mean(x["kl_sae"])),
                            "kl_zero": float(np.mean(x["kl_zero"])), "kl_mean": float(np.mean(x["kl_mean"])),
                            "fvu": x["fvu"], "l0_positive_mean": x["l0_positive_mean"], "l0_topk": x["l0_topk"]}
    return out


def run_sae_report() -> dict[str, Any] | None:
    p = RESULTS_DIR / "sae_transfer_raw.json"
    if not p.exists():
        return None
    raw = json.loads(p.read_text())
    cells = {k: cell(raw[k]) for k in ("inst_own", "base_own", "inst_on_base", "base_on_inst") if k in raw}
    res: dict[str, Any] = {"design": "2x2 (model x text source); instruct text = exp12 transfer corpus (exp1 programs, "
                                     "25 per group = 100); base text = 100 Qwen3-8B-Base outputs generated here",
                           "cells": cells, "rule": "FROZEN PASS(L) := FR_zero(instruct, own text) >= 0.9 x "
                                                   "FR_zero(base, own text)", "per_layer": {}}
    for L in LAYERS:
        if "inst_own" in cells and "base_own" in cells and L in cells["inst_own"]["layers"]:
            fi = cells["inst_own"]["layers"][L]["fr_zero"]
            fb = cells["base_own"]["layers"][L]["fr_zero"]
            mi = cells["inst_own"]["layers"][L]["fr_mean"]
            mb = cells["base_own"]["layers"][L]["fr_mean"]
            res["per_layer"][L] = {
                "fr_zero_inst_own": fi, "fr_zero_base_own": fb, "frozen_pass": bool(fi >= 0.9 * fb),
                "abs_gap_fr_zero": fb - fi, "fr_mean_inst_own": mi, "fr_mean_base_own": mb,
                "fr_mean_pass_same_rule": bool(mi >= 0.9 * mb),
                "dce_ratio_own_text": cells["inst_own"]["layers"][L]["dce"] / max(cells["base_own"]["layers"][L]["dce"],
                                                                                  1e-9),
                "kl_sae_inst_own": cells["inst_own"]["layers"][L]["kl_sae"],
                "kl_sae_base_own": cells["base_own"]["layers"][L]["kl_sae"]}
    res["displacement_preservation"] = raw.get("displacement_preservation")
    res["sanity"] = {"base": raw.get("sanity_base"), "instruct": raw.get("sanity_inst")}
    res["state_code_fvu"] = raw.get("state_code_fvu")
    res["frozen_pass_any_layer"] = any(v["frozen_pass"] for v in res["per_layer"].values()) if res["per_layer"] else None
    res["frozen_pass_all_layers"] = all(v["frozen_pass"] for v in res["per_layer"].values()) if res["per_layer"] else None
    # T5 arithmetic on exp12's stored numbers (documents the leniency of the frozen rule)
    ts = read_json(E12 / "results" / "transfer_summary.json")
    ce_zero_l15 = float(np.mean([r["ce_zero_splice"] for r in ts["splice_sanity"]["rows"]]))
    res["exp12_arithmetic"] = {
        "dce_ratio_inst_over_base": {L: ts["layers"][L]["ratio"] for L in LAYERS},
        "fr_zero_inst_exp12_L15_approx": 1 - ts["layers"]["15"]["dce_inst"] / (ce_zero_l15 - ts["ce_clean_inst"]),
        "ce_zero_L15": ce_zero_l15}
    if "inst_own" in cells:
        res["u5_fvu_vs_exp12"] = {L: {"ours_inst_own": cells["inst_own"]["layers"][L]["fvu"],
                                      "exp12_inst": ts["layers"][L]["fvu_inst"],
                                      "abs_diff": abs(cells["inst_own"]["layers"][L]["fvu"] - ts["layers"][L]["fvu_inst"]),
                                      "within_0.03": abs(cells["inst_own"]["layers"][L]["fvu"] - ts["layers"][L]["fvu_inst"]) <= 0.03}
                                  for L in LAYERS if L in cells["inst_own"]["layers"]}
        res["u5_note"] = ("exp12 scored 200 sequences with the bf16 model; ours are 100 of them with the FP8 model and the "
                          "special-token exclusion, so the FVU comparison is approximate")
    res["note"] = ("The zero-ablation denominator (~12 nats) makes the frozen rule lenient by construction; a PASS "
                   "licenses little by itself. 5a stays descriptive whatever 0g shows.")
    return res
