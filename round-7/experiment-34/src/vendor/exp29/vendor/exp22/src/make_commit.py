#!/usr/bin/env python3
"""S4 COMMIT (before the first population sample): predictions/c2_commit.json + commitments.log entries.

Entry #0 = results/screen.json; then the commit file, the analysis code, the CPU test results, the subspace files and
the GPU unit tests. Analyses written later (decomp, c2c, c2b, c3b, geometry, novelty) are chained as addenda, each
before the corresponding analysis is run; the reading rules for ALL of them are committed verbatim here.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg4 import (ANALYSIS_DIR, COMMIT_LOG, DOSES, MOVABLE, OTHER9, PRED_DIR, RESULTS_DIR, SEEDS_C2C, SEEDS_OTHER,  # noqa: E402
                  SEEDS_POP, STATES_DIR, TASKS15, read_json, sha256_file, utc_now, write_json)
from commit4 import commit  # noqa: E402

RULES = {
    "C2a_primary": (
        "One-sided within-task Spearman rho(pi, y), y = a direction's off-default share (catalogue-only, over valid "
        "attempts) over the FIRST 10 samples (k 0-1 x W1-W5), averaged over alpha 1 and 2; p from 10,000 shuffles of "
        "y. PASS: rho >= 0.4 and p < 0.01 on >= 4 of 6 movable tasks, and the same for pi_masked on >= 3 of 6. "
        "DISCONFIRM: rho < 0.2 on most (>= 4 of 6) tasks. Tasks with fewer than 5 directions with y > 0 are flagged "
        "underpowered and still count in the primary."),
    "escape_confirmation": (
        "Screen pass at N = 10: excess >= 0.20 over the twin (N = 50, k 0-9; others N = 30, k 0-5) and pass >= 0.8 x "
        "twin. CONFIRMED if the pooled 30 (k 0-5) keeps excess >= 0.20 with one-sided exact binomial p < 0.05 against "
        "p0 = (k_twin + 0.5) / (n_twin + 1), and pass >= 0.8 x twin. E_t(alpha) = confirmed / run; MOVABLE := E_t > 0 "
        "at alpha <= 2."),
    "decomposition": (
        "R_arm = (share_arm - share_twin) / (share_orig - share_twin) on the same CRN slots (k 0-3). 'P_t not needed' "
        "if median R_uperp >= 0.7 with bootstrap lower bound >= 0.4; 'Necessary' if R_uperp <= 0.3 (upper bound <= "
        "0.5); 'Sufficient (amplified)' if u_P passes the escape rule at N = 20; otherwise 'mixed'."),
    "C2c": (
        "Correct-only Hill-1 >= 1.8 within 5 pass points (of the twin) at 1 x b_t (s = 0.5) on >= 4 of 6 tasks, with "
        "nu(0.5) <= 0.5 x the median alpha of this artifact's confirmed escaping random directions. DISCONFIRM: the "
        "targeted-minus-random difference in off-default share and in Hill (paired CRN bootstrap) has CI including 0 "
        "on >= 4 of 6."),
    "C2b": (
        "Pooled within-task Spearman(pi(delta_knob), recorded off-default share) >= 0.5, and pi beats ||delta|| "
        "(paired bootstrap of the rho difference > 0)."),
    "C3b": "Descriptive: push-landing and opening-ladder forecasts scored with exp13 score.py smoothing/log score "
           "against the 5 gated iteration-3 bench landings (already seen).",
    "novelty": "'No correct novel algorithm' is claimed only at 0 NOVEL verdicts (rule-of-three bound 3/n).",
    "geometry": "Descriptive; persistent H1 vs a 200-draw coordinate-permutation null with a planted-circle power check.",
}


def main() -> None:
    raw = Path(RESULTS_DIR).parent / "data" / "samples_raw.jsonl"
    if raw.exists():
        assert not any('"family": "POP"' in r for r in raw.read_text().splitlines()), \
            "population rows exist before the commit"
    if not COMMIT_LOG.exists():
        commit([RESULTS_DIR / "screen.json"], "entry0_screen")
    rep = read_json(RESULTS_DIR / "subspace_report.json")
    screen_sha = sha256_file(RESULTS_DIR / "screen.json")
    afiles = [ANALYSIS_DIR / "common.py", ANALYSIS_DIR / "c2a.py", ANALYSIS_DIR / "tests_cpu.py"]
    c = {
        "utc": utc_now(), "screen_sha256": screen_sha, "rules": RULES,
        "design": {"movable": list(MOVABLE), "other9": list(OTHER9), "seeds_population": SEEDS_POP,
                   "seeds_other": SEEDS_OTHER, "seeds_c2c_random": SEEDS_C2C, "doses_s": list(DOSES),
                   "alphas_population": [1.0, 2.0], "alphas_sweep": [4.0, 8.0], "B": 20,
                   "haar_null_seed": 4242, "n_perm": 10000},
        "tasks": {t: {k: v for k, v in rep["tasks"][t].items()} for t in TASKS15},
        "predictors": rep["directions"],
        "analysis_sha256": {str(p.relative_to(p.parents[1])): sha256_file(p) for p in afiles},
        "subspace_files_sha256": {f"states/subspace_{t}.npz": sha256_file(STATES_DIR / f"subspace_{t}.npz")
                                  for t in TASKS15},
        "c2c_bt": {t: {"b_t_s": 0.5, "nu": rep["tasks"][t]["nu"], "s_prime": rep["tasks"][t]["s_prime"]}
                   for t in MOVABLE},
    }
    p = PRED_DIR / "c2_commit.json"
    write_json(p, c)
    files = [p] + afiles + [RESULTS_DIR / "tests_cpu.json", RESULTS_DIR / "subspace_report.json",
                            RESULTS_DIR / "units.json", RESULTS_DIR / "unit_tests_gpu.json"] + \
        [STATES_DIR / f"subspace_{t}.npz" for t in TASKS15]
    out = commit(files, "commit1_predictors_rules")
    print(f"committed {len(out)} files; last: {out[-1]['line']}")


if __name__ == "__main__":
    main()
