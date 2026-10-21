#!/usr/bin/env python3
"""Analysis ADDENDUM (hash-committed before the first push sample of any P_/V_ unit; logged deviation): the two A1
views of plan section 11 that analysis/a1a2.py does not compute, plus the P_/V_ outcome table.

- PANEL + PARENTS view: the 7 new units plus every existing task with a same-engine, ban-free beta and E measured
  here (the paired parent re-measures P_<t>): Spearman(beta, E), one-sided permutation p (10,000 shuffles when
  n > 9, exact enumeration otherwise). Descriptive.
- CLUSTERED A1 (new units + variants + parents): beta permuted among clusters of equal size -- singletons among
  singletons, parent-variant pairs as blocks among pairs -- 10,000 shuffles, one-sided p for Spearman(beta, E) over
  all units.
- results/unit_outcomes_extra.json: a1a2.unit_outcomes for every P_/V_ unit (E, per-direction table, landing).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "analysis"))

import units_extra  # noqa: E402,F401  (registers the P_/V_ cards)
from a1a2 import perm_p, spearman, unit_outcomes  # noqa: E402
from cfg5 import PRED_DIR, RESULTS_DIR, read_json, utc_now, write_json  # noqa: E402

RNG = np.random.default_rng(11)


def collect() -> list[dict]:
    out = []
    for p in sorted((PRED_DIR / "units").glob("*.json")):
        u = p.stem
        pr = read_json(p)
        if pr["default"] == "NO_DEFAULT" or pr["base"]["beta_u"] is None:
            continue
        o = unit_outcomes(u, pr)
        if o["n_push_rows"] == 0:
            continue
        out.append({"unit": u, "beta": pr["base"]["beta_u"], "E": o["E_u"], "kind": u[:2] if u[:2] in ("P_", "V_")
                    else "new", "parent": u[2:] if u[:2] in ("P_", "V_") else None, "outcome": o})
    return out


def clustered_p(units: list[dict], n_shuffle: int = 10000) -> dict:
    beta = np.array([x["beta"] for x in units])
    E = [x["E"] for x in units]
    r0 = spearman(list(beta), E)
    if r0 is None:
        return {"rho": None, "p": None}
    singles = [i for i, x in enumerate(units) if x["kind"] == "new"]
    pairs: dict[str, list[int]] = {}
    for i, x in enumerate(units):
        if x["kind"] != "new":
            pairs.setdefault(x["parent"], []).append(i)
    full_pairs = [sorted(v, key=lambda i: units[i]["kind"]) for v in pairs.values() if len(v) == 2]
    lone = [v[0] for v in pairs.values() if len(v) == 1]
    singles = singles + lone
    cnt = 0
    for _ in range(n_shuffle):
        b = beta.copy()
        ps = RNG.permutation(len(singles))
        b[singles] = beta[[singles[j] for j in ps]]
        pp = RNG.permutation(len(full_pairs))
        for dst, src in zip(full_pairs, [full_pairs[j] for j in pp]):
            b[dst] = beta[src]
        r = spearman(list(b), E)
        cnt += (r is not None and r >= r0 - 1e-12)
    return {"rho": r0, "p": (cnt + 1) / (n_shuffle + 1), "n_units": len(units), "n_singletons": len(singles),
            "n_pair_clusters": len(full_pairs), "method": f"{n_shuffle} cluster-preserving shuffles"}


def main() -> None:
    U = collect()
    extra = [x for x in U if x["kind"] != "new"]
    write_json(RESULTS_DIR / "unit_outcomes_extra.json",
               {"utc": utc_now(), "units": [{"unit": x["unit"], **x["outcome"]} for x in extra]})
    new_par = [x for x in U if x["kind"] in ("new", "P_")]
    res = {"utc": utc_now(),
           "panel_plus_parents": {**perm_p([x["beta"] for x in new_par], [x["E"] for x in new_par]),
                                  "units": [x["unit"] for x in new_par],
                                  "reading": "descriptive; parents re-measured on this engine with the ban-free unit"},
           "clustered_all": {**clustered_p(U), "units": [x["unit"] for x in U]},
           "values": {x["unit"]: {"beta": x["beta"], "E": x["E"]} for x in U}}
    write_json(RESULTS_DIR / "a1_extended.json", res)
    print({k: (v if k != "values" else len(v)) for k, v in res.items()})


if __name__ == "__main__":
    main()
