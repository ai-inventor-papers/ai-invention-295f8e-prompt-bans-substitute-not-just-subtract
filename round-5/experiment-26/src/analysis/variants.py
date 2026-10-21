#!/usr/bin/env python3
"""Frozen within-parent analysis of the extra arm (plan section 11, WITHIN-PARENT, descriptive).

Pairs: (P_<task>, V_<task>) = paired parent re-measure and narrative-disguised variant, same engine, same ban-free
unit and the SAME 8 direction seeds (keyed on the parent id). Per pair: delta_beta = beta_V - beta_P,
delta_E = E_V - E_P, the per-(direction, alpha) paired escape table with an exact McNemar count (confirmed escapes;
stage-1 passes as a secondary), and whether the twin default shifted ('default shift' pairs reported separately).
Across pairs: sign agreement of delta_beta and delta_E, and Spearman(delta_beta, delta_E).
Reads predictions/units/{P,V}_<task>.json and the outcome rows; writes results/variants.json.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "analysis"))

from a1a2 import perm_p, unit_outcomes  # noqa: E402
from cfg5 import PRED_DIR, RESULTS_DIR, read_json, utc_now, write_json  # noqa: E402

PARENTS = ["T03", "T10", "T2", "T05", "T1", "T06", "T04", "T08", "T14", "R1"]


def mcnemar(a: list[bool], b: list[bool]) -> dict[str, Any]:
    n01 = sum(1 for x, y in zip(a, b) if x and not y)
    n10 = sum(1 for x, y in zip(a, b) if y and not x)
    n = n01 + n10
    p = float(stats.binomtest(min(n01, n10), n, 0.5).pvalue) if n > 0 else None
    return {"parent_only": n01, "variant_only": n10, "both": sum(1 for x, y in zip(a, b) if x and y),
            "neither": sum(1 for x, y in zip(a, b) if not x and not y), "exact_p_two_sided": p}


def main() -> None:
    pairs = []
    for t in PARENTS:
        pp, pv = PRED_DIR / "units" / f"P_{t}.json", PRED_DIR / "units" / f"V_{t}.json"
        if not (pp.exists() and pv.exists()):
            continue
        P, V = read_json(pp), read_json(pv)
        oP, oV = unit_outcomes(f"P_{t}", P), unit_outcomes(f"V_{t}", V)
        key = lambda c: (c["seed"], c["alpha"])  # noqa: E731
        dP = {key(c): c for c in oP["per_direction"]}
        dV = {key(c): c for c in oV["per_direction"]}
        ks = sorted(set(dP) & set(dV))
        rec = {"parent": t, "default_parent": P["default"], "default_variant": V["default"],
               "default_shift": P["default"] != V["default"],
               "beta_parent": P["base"]["beta_u"], "beta_variant": V["base"]["beta_u"],
               "E_parent": oP["E_u"], "E_variant": oV["E_u"],
               "delta_beta": None if P["base"]["beta_u"] is None or V["base"]["beta_u"] is None else
               V["base"]["beta_u"] - P["base"]["beta_u"], "delta_E": oV["E_u"] - oP["E_u"],
               "mcnemar_confirmed": mcnemar([dP[k]["confirmed"] for k in ks], [dV[k]["confirmed"] for k in ks]),
               "mcnemar_stage1": mcnemar([dP[k]["stage1_passed"] for k in ks], [dV[k]["stage1_passed"] for k in ks]),
               "per_direction": [{"seed": k[0], "alpha": k[1], "parent": dP[k], "variant": dV[k]} for k in ks]}
        pairs.append(rec)
    ok = [p for p in pairs if not p["default_shift"] and p["delta_beta"] is not None]
    signs = [(p["delta_beta"] > 0) == (p["delta_E"] > 0) for p in ok if p["delta_beta"] != 0 and p["delta_E"] != 0]
    out = {"utc": utc_now(), "n_pairs": len(pairs), "pairs": pairs,
           "n_pairs_no_default_shift": len(ok), "sign_agreement": {"agree": sum(signs), "n": len(signs)},
           "spearman_delta_beta_delta_E": perm_p([p["delta_beta"] for p in ok], [p["delta_E"] for p in ok])
           if len(ok) >= 3 else None,
           "default_shift_pairs": [p["parent"] for p in pairs if p["default_shift"]],
           "reading": "descriptive; within-parent wording change holds the computational task fixed"}
    write_json(RESULTS_DIR / "variants.json", out)
    print({k: v for k, v in out.items() if k != "pairs"})


if __name__ == "__main__":
    main()
