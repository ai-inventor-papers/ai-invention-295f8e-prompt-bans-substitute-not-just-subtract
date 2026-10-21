#!/usr/bin/env python3
"""Runs the FROZEN analysis (analysis_a1a2.main_final, committed at #0) on two unit sets without editing it:
  extension set  = every committed unit (A1-A7 gated + reserves A8/A9)  -> results/*_with_extension.json
  primary set    = the pre-registered units A1-A7 (gated, with a default) -> results/a1.json, a2.json, ... (canonical)
The frozen code reads predictions/unit_*.json; for each run it is pointed at a directory holding only the selected
prediction files (copies, byte-identical, sha256-checked against commitments.log).
Then the plan's descriptive 'half + screen' view (Step 1's committed beta for the 15 existing tasks + this run's
Extra-arm-A E_t, beside the new units) is computed with the frozen a1_analysis function -> results/half_screen.json.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

import analysis_a1a2 as A  # noqa: E402
from cfg5 import (COMMIT_LOG, EXISTING, NEW_UNITS, PRED, RESERVE_UNITS, RESULTS, ROOT, read_json,  # noqa: E402
                  setup_logging, sha256_file, write_json)

# Step 1 of this iteration (workspace gen_art_experiment_24): its committed predictions/commit1.json and commitments.log,
# copied into inputs/step1/ (sha256 6adc77a5...); STEP1_COMMIT_FILE overrides the location (its commitments.log must sit
# two folders up, as in the artifact's own layout, or beside it).
STEP1 = Path(os.environ.get("STEP1_COMMIT_FILE", str(ROOT / "inputs" / "step1" / "commit1.json")))


def run_set(units: list[str], suffix: str) -> dict:
    tmp = ROOT / "predictions_view" / (suffix or "primary")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    log = COMMIT_LOG.read_text()
    used = []
    for u in units:
        p = PRED / f"unit_{u}.json"
        if p.exists():
            assert sha256_file(p) in log, f"{p.name} does not match its commitment"
            shutil.copy(p, tmp / p.name)
            used.append(u)
    A.PRED = tmp
    res = A.main_final()
    if suffix:
        for name in ("a1", "a2", "unit_summaries", "repertoire_check", "outside_base_repertoire", "knob_rows"):
            src = RESULTS / f"{name}.json"
            if src.exists():
                shutil.copy(src, RESULTS / f"{name}_{suffix}.json")
    shutil.rmtree(tmp)
    res["units_used"] = used
    return res


def half_screen(units_res: dict, xa: dict) -> dict:
    """Descriptive: new units (beta_u, E_u) + 15 existing tasks (Step 1 committed beta_t, this run's E_t)."""
    out = {"step1_file": ("inputs/step1/commit1.json (copy of Step 1's predictions/commit1.json)"
                          if STEP1.exists() else None)}
    if not STEP1.exists():
        out["status"] = "PENDING_STEP1"
        return out
    logp = STEP1.parent / "commitments.log"
    if not logp.exists():
        logp = STEP1.parents[1] / "commitments.log"
    log = logp.read_text()
    h = sha256_file(STEP1)
    out["step1_sha256"] = h
    out["step1_sha256_in_its_commitments_log"] = h in log
    s1 = read_json(STEP1)["per_task"]
    rows = []
    for u, s in units_res.items():
        if "prediction" in s and s["prediction"].get("beta") is not None and s["outcome"].get("E") is not None:
            rows.append({"unit": u, "kind": "new", "beta": s["prediction"]["beta"], "E": s["outcome"]["E"],
                         "rivals": {}, "cluster": u})
    for t in EXISTING:
        if t in s1 and s1[t].get("beta") is not None and t in xa and xa[t].get("E") is not None:
            rows.append({"unit": t, "kind": "existing", "beta": s1[t]["beta"], "E": xa[t]["E"], "rivals": {},
                         "cluster": t, "step1_stratum": s1[t].get("stratum"), "step1_r": s1[t].get("r_t"),
                         "landing_E": xa[t].get("landing")})
    out["rows"] = rows
    out["all"] = A.a1_analysis(rows)
    out["existing_only"] = A.a1_analysis([r for r in rows if r["kind"] == "existing"])
    # landing check on the existing tasks that escaped: Step 1's predicted landing vs this run's landing
    hits = []
    for t in EXISTING:
        if t in xa and xa[t].get("landing") and t in s1:
            hits.append({"task": t, "step1_r": s1[t].get("r_t"), "landing": xa[t]["landing"],
                         "hit": s1[t].get("r_t") == xa[t]["landing"]})
    out["existing_landing_checks"] = hits
    out["note"] = ("descriptive only (plan Stage 6 'half + screen'); A6 failed its gate, so the A6-T10 permutation "
                   "cluster and the without-A6 sensitivity are moot; Step 1 beta comes from a parallel artifact of this "
                   "iteration (same models, bf16 engine on the same GPU class) and is hash-verified")
    return out


def main() -> None:
    setup_logging("final_run")
    primary = [u for u in NEW_UNITS]
    ext = primary + list(RESERVE_UNITS)
    r_ext = run_set(ext, "with_extension")
    r_pri = run_set(primary, "")
    hs = half_screen(r_pri["summaries"], r_pri["extra_arm_a"])
    hs_ext = half_screen(r_ext["summaries"], r_ext["extra_arm_a"])
    write_json(RESULTS / "half_screen.json", {"primary": hs, "with_extension": hs_ext})
    logger.info(f"primary units {r_pri['units_used']}: rho {r_pri['a1']['rho_beta_E']} p {r_pri['a1']['perm_p_one_sided']}"
                f"; with extension {r_ext['units_used']}: rho {r_ext['a1']['rho_beta_E']} "
                f"p {r_ext['a1']['perm_p_one_sided']}; half+screen n={hs.get('all', {}).get('n_units')} rho "
                f"{hs.get('all', {}).get('rho_beta_E')} p {hs.get('all', {}).get('perm_p_one_sided')}")
    print(json.dumps({"primary": {k: r_pri["a1"].get(k) for k in ("n_units", "rho_beta_E", "perm_p_one_sided",
                                                                   "collapsed_immovable", "diverse_immovable")},
                      "primary_a2": {k: r_pri["a2"].get(k) for k in ("n_events", "hits", "p_poisson_binomial")},
                      "extension": {k: r_ext["a1"].get(k) for k in ("n_units", "rho_beta_E", "perm_p_one_sided",
                                                                     "collapsed_immovable", "diverse_immovable")},
                      "extension_a2": {k: r_ext["a2"].get(k) for k in ("n_events", "hits", "p_poisson_binomial")},
                      "half_screen": {k: hs.get("all", {}).get(k) for k in ("n_units", "rho_beta_E",
                                                                            "perm_p_one_sided",
                                                                            "collapsed_immovable",
                                                                            "diverse_immovable")}}, indent=1))


if __name__ == "__main__":
    main()
