#!/usr/bin/env python3
"""COMMIT #0 (before any sample): protocol8L.json (units, held-out set, Llama candidate order, keys, caps, N, MAE
definition, thresholds, baselines, placebos, base sub-arm thresholds, drop order) and the sha256 of every code file."""

from __future__ import annotations

from cfg8 import (FAMILIES, FAMILY_ORDER, LLAMA_BENCH_KEEP, LLAMA_BENCH_ORDER, LLAMA_MINORITY_BAR, NS_FIT_L, NS_FORCE,
                  NS_LOC, NS_REFINE, NS_SECOND, NS_SWEEP, PRED_DIR, ROOT, SRC, SWEEP_SLOTS, FIT_SLOTS, TEMPLATES,
                  TEMPS, THRESH, UNITS, sha256_file, write_json)
from commit8 import commit, verify

PROTOCOL = {
    "claim": "L: a frozen two-decision temperature law predicts the attempted-label distribution of sampled programs",
    "units": {u: {k: v for k, v in s.items()} for u, s in UNITS.items()},
    "held_out": [u for u, s in UNITS.items() if s["held_out"]],
    "llama_candidates": {"order": LLAMA_BENCH_ORDER, "keep": LLAMA_BENCH_KEEP, "minority_bar": LLAMA_MINORITY_BAR},
    "families": FAMILIES, "family_order": FAMILY_ORDER,
    "keys": {"fit": "Qwen ('iter7T', unit, w, slot) | Gemma ('iter5E'|'iter6S', task, w, slot) | Llama seed8('%s', "
                    "model, unit, w, slot)" % NS_FIT_L,
             "sweep": f"seed8('{NS_SWEEP}', model, unit, w, slot)", "locator": NS_LOC, "refine": NS_REFINE,
             "force": NS_FORCE, "second": NS_SECOND},
    "N": {"fit": len(FIT_SLOTS) * 5, "sweep_per_cell": len(SWEEP_SLOTS) * 5}, "templates": TEMPLATES, "temps": TEMPS,
    "samplers": {"p1": "top-p 1", "k10": "top-k 10 (exact shadow sampling on the same uniforms)"},
    "mae": "MAE_u = mean over the 4 top-p-1 temperatures of TVD(predicted, observed attempted-label distribution) "
           "over all label bins (catalogue + other + invalid)",
    "thresholds": THRESH,
    "verdict": {"unit_pass": "MAE_u <= 0.10 and H_u <= 0.3 bits (boundary units: MAE only)",
                "claim_pass": ">= 70% of scored units pass AND >= 3 held-out units pass with >= 4 held-out scored",
                "disconfirmed": "MAE > 0.20 on >= 3 scored held-out units", "else": "PARTIAL",
                "holm_input": "exact one-sided sign test over scored units of MAE_L < MAE_B0"},
    "baselines": {"B0": "fit-twin shares at every T", "B1": "q(A)^(1/T) renormalised",
                  "B2": "single-decision law (no second level)", "BH": "entropy-located rival (CPU-side Phat)"},
    "placebos": ["temperature permutation (23 non-identity permutations; true summed MAE below the 5th percentile)",
                 "token-map shuffle (Phat rows permuted across tokens within a unit)",
                 "temperature-label shuffle within slots for the drop test"],
    "base_subarm": {"collapsed": ["T1", "T10", "T2"], "descriptive": ["B3", "A3"],
                    "margin_gain_nats": THRESH["base_margin_gain"], "phrasing_dH_nats": THRESH["base_phrasing_dH"]},
    "drop_order": ["base sub-arm", "Llama units beyond the grid", "top-k cells at T 0.7"],
    "never_dropped": ["A3/B6 with second decisions", "B3 fresh streams", "Gemma T04/R6", "Llama grid",
                      "top-p sweep", "novelty audit"],
}

if __name__ == "__main__":
    write_json(ROOT / "protocol8L.json", PROTOCOL)
    code = {str(p.relative_to(ROOT)): sha256_file(p) for p in sorted(SRC.glob("*.py"))}
    code["protocol8L.json"] = sha256_file(ROOT / "protocol8L.json")
    print(commit("commit0", {"protocol": PROTOCOL, "code_sha256": code}))
    print(verify())
