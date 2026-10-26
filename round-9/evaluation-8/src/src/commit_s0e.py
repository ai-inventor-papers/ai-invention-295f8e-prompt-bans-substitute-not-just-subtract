#!/usr/bin/env python3
"""Write predictions/commit_s0e.json and append its sha256 to commitments.log BEFORE any alias-level number exists.

Never overwrites an existing commit. If the 0e code later changes, eval.py appends an amendment line with the new code
hash instead (hash chain), so the record shows what was committed and what ran.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path

import alias_geometry as AG

ROOT = Path(__file__).resolve().parent.parent
import recompute as RC  # noqa: E402 - one place resolves the iteration-8 artifacts (S0_DEPS_DIR)

TP = RC.ART[RC.TP]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def code_hash() -> dict[str, str]:
    return {p: sha(ROOT / p) for p in ("src/alias_geometry.py", "src/stage_0e.py")}


def build() -> dict:
    return {
        "commit": "S0-0e alias-overlap test", "utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "plan": "gen_plan_evaluation_1_idx1, item 0e",
        "question": "Is iteration 8's 'opposite' landing (unit-weight Dijkstra farthest from the banned five) a property "
                    "of the alias-named manifold of 300 forced prompts?",
        "inputs": {"geo": "art_R-HSmXq2t97f:cache/states/geo_C6_nf4.npz", "smean": "art_R-HSmXq2t97f:cache/states/"
                   "smean_C6_nf4.npz", "alias_table": "art_R-HSmXq2t97f:src/common.py#ALIAS_TABLE",
                   "short_forms": "art_R-HSmXq2t97f:src/common.py#SHORT_FORMS",
                   "geometry_M1": "art_R-HSmXq2t97f:results/geometry_M1.json#M1"},
        "input_sha256": {"geo_C6_nf4.npz": sha(TP / "cache/states/geo_C6_nf4.npz"),
                         "common.py": sha(TP / "src/common.py"), "prompts_tp.py": sha(TP / "src/prompts_tp.py"),
                         "geometry_M1.json": sha(TP / "results/geometry_M1.json")},
        "detectors_case_insensitive": dict(AG.DETECTORS),
        "primary_overlap": "number of distinct detectors D1-D11 matching the alias string",
        "expected_primary_vectors_alias_0_1_2": AG.EXPECTED_PRIMARY,
        "expected_primary_multiset": {"0": 6, "1": 7, "2": 1, "3": 1},
        "secondary_overlap": "max content-token Jaccard with any of the 15 banned aliases; tokens = lowercase split on "
                             "[^a-z0-9*]",
        "stopwords": sorted(AG.STOPWORDS),
        "tertiary_overlap": "optional Qwen3 BPE token-set Jaccard; run only if the tokenizer is already cached offline",
        "g_definition": "g(alg, alias) = min over banned b of mean geodesic between the 10 points of (alg, alias) and "
                        "the 30 points of b; algorithm-level g as in geometry.py",
        "k": {"primary": 15, "secondary": 10},
        "statistics": [
            "Spearman (average ranks) of alias-level g against the primary overlap over 15 alias sets; exact one-sided "
            "lower-tail p over all 360,360 distinct assignments of the overlap multiset; two-sided p reported",
            "same with the secondary overlap (exact if <= 2e6 distinct arrangements, else 200,000 Monte Carlo draws)",
            "same with binary any-overlap (sensitivity)",
            "5-centroid Spearman of algorithm g against mean primary overlap; exact p over 5! = 120 permutations; "
            "attainable floor printed (4/120 = 0.033 for the tied vector (1, 1, 2, 0, 0))",
            "within-algorithm stratified test: mean over algorithms with non-constant secondary overlap of the 3-point "
            "Spearman; exact null over (3!)^5 = 7,776 within-algorithm relabelings (effective 6^m); also primary",
            "fixed-effects OLS g = alpha_algorithm + beta * overlap_secondary; beta's stratified-permutation p",
            "95% intervals from 2,000 cluster-bootstrap resamples of the 10 templates, geodesics held fixed"],
        "gates": {"E1": "smean algorithm[kind == forced] equals geo labels (hard)",
                  "E2": "multiset (algorithm, group // 3, group % 3) equals forced_set() (hard); order recorded",
                  "E3": "algorithm-level g from stored geo_k15/geo_k10 matches geometry_M1.json to 1e-9, classes "
                        "match (hard)",
                  "E4": "independent kNN geodesics from smean block 31 (float64, raw coordinates): Spearman with stored "
                        "geo_k15 >= 0.999 (cross-check; < 0.99 flags 'geodesics not independently reproduced')"},
        "placebos_must_fail": {"P1": "1,000 random reassignments of the 300 point labels: rho centred near 0, share "
                                     "p < 0.05 at most 0.10",
                               "P2": "1,000 random permutations of the overlap multiset: share p < 0.05 at most 0.10",
                               "P3": "within-algorithm shuffles: stratified statistic centred near 0"},
        "planted_control_must_succeed": "g = 12 - 2 * overlap + N(0, 0.5): rho <= -0.6 with p < 0.05",
        "verdict_rules": {
            "rho_k15 <= -0.6 and stratified p < 0.05": "names move the geometry even with the algorithm held fixed",
            "rho_k15 <= -0.6 and stratified p >= 0.05": "g follows alias overlap across algorithms (rho, p), but the "
            "pattern is carried by algorithm identity; on this manifold names and mechanisms are confounded, and TP-G's "
            "name-free manifolds decide",
            "rho_k15 > -0.6": "iteration 8's geodesics do not track alias overlap at the committed strength (rho)",
            "rescoring": "report every outcome; never re-score"},
        "non_blind_expectation": "Iteration 8's algorithm-level g (bidirectional BFS 10.9, bidirectional A* 11.6, IDA* "
                                 "13.3, JPS 15.9, unit Dijkstra 21.6) is public. If each alias carries its algorithm's g, "
                                 "the 15-point Spearman with count overlap is about -0.70, the 5-centroid one about -0.63, "
                                 "and with binary any-overlap about -0.87. Only the within-algorithm statistic and the "
                                 "bootstrap interval are genuinely unseen.",
        "code_sha256": code_hash(), "seed": AG.SEED}


def main() -> int:
    out = ROOT / "predictions/commit_s0e.json"
    log = ROOT / "commitments.log"
    if out.exists():
        print(f"commit exists: {out} (not overwritten)")
        return 0
    out.write_text(json.dumps(build(), indent=2))
    h = sha(out)
    with log.open("a") as f:
        f.write(f"{dt.datetime.now(dt.timezone.utc).isoformat()} COMMIT S0-0e predictions/commit_s0e.json sha256={h}\n")
    print(f"committed {out} sha256={h}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
