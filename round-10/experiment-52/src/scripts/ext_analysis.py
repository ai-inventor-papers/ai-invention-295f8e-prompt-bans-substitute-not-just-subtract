#!/usr/bin/env python3
"""Exploratory extension (amendment commit #3): the FROZEN analysis functions applied to seeds 4 and 5, plus held-out
scoring of their best programs and 4-seed pooled descriptive ratios. Outputs: results/*_ext45.json."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import common as C
_orig_write = C.write_json
REDIRECT = {"analysis_clusters.json": "analysis_clusters_ext45.json", "best_programs.json": "best_programs_ext45.json",
            "v3_candidates.json": "v3_candidates_ext45.json"}
def _write(path, obj, indent=1):
    p = Path(path)
    if p.name in REDIRECT:
        p = p.with_name(REDIRECT[p.name])
    _orig_write(p, obj, indent)
def main():
    C.write_json = _write
    C.SEEDS = [4, 5]
    import analysis as AN
    import heldout as HO
    import sandbox
    C.setup_logging("ext_analysis")
    _cp, _bp = C.RESULTS / 'analysis_clusters_ext45.json', C.RESULTS / 'best_programs_ext45.json'
    cl = json.loads(_cp.read_text()) if _cp.exists() else AN.stage_clusters()  # resume: reuse saved stages
    best = json.loads(_bp.read_text()) if _bp.exists() else AN.stage_best()
    bf = HO.bf_reference()
    pool = sandbox.EvalPool(10, C.ROOT)
    try:
        res = HO.score(pool, {k: r["code"] for k, r in best["seed_best"].items()}, HO.HELDOUT)
    finally:
        pool.close()
    hb = {"seed_best": {k: dict(HO.summarise(res[k], bf), F=r["F"], call=r["call"]) for k, r in best["seed_best"].items()}}
    hb["artifact_best"] = {a: hb["seed_best"][f"S{r['seed']}-{a}"] for a, r in best["artifact_best"].items()}
    heldout = {a: {s: r["excess"].get(s) for s in ("H-FSW5k", "H-OR3")} for a, r in hb["artifact_best"].items()}
    v1 = AN.v1_verdict(heldout)
    m = {a: sum(heldout[a][s] / AN.BF_EXC[s] for s in ("H-FSW5k", "H-OR3")) / 2 for a in heldout}
    v2 = AN.v2_verdict(cl["V2_stats"], m)
    _orig_write(C.RESULTS / "heldout_best_ext45.json", hb)
    # 4-seed pooled descriptive ratios (seeds 2-5), same definition as V2's R_X
    cl23 = json.loads((C.RESULTS / "analysis_clusters.json").read_text())["per_arm_seed"]
    pa = dict(cl23); pa.update(cl["per_arm_seed"])
    def rate(a):
        k = sum(pa[f"S{S}-{a}"]["clusters"] for S in (2, 3, 4, 5) if f"S{S}-{a}" in pa)
        n = sum(pa[f"S{S}-{a}"]["C"] for S in (2, 3, 4, 5) if f"S{S}-{a}" in pa)
        return k / n
    pooled = {X: rate("DTB") / rate(X) for X in ("T1.0", "T1.6", "RPB", "IDEA")}
    per_seed_rpb = {S: (pa[f"S{S}-DTB"]["clusters"] / pa[f"S{S}-RPB"]["clusters"]) for S in (2, 3, 4, 5)}
    out = {"note": "EXPLORATORY (not part of the pre-registered verdicts)", "V1_rule_on_ext": v1, "V2_rule_on_ext": v2,
           "clusters": {k: {"clusters": v["clusters"], "C": v["C"], "validity": v["desc"]["validity"]} for k, v in cl["per_arm_seed"].items()},
           "pooled_4seed_R": pooled, "per_seed_DTB_over_RPB_clusters": per_seed_rpb,
           "heldout_artifact_best": {a: {"F": r["F"], "excess": r["excess"]} for a, r in hb["artifact_best"].items()}}
    _orig_write(C.RESULTS / "extension_ext45.json", out)
    print(json.dumps({"V1": v1["verdict"], "V2": v2["verdict"], "failed": v2["failed"], "R": v2["R"], "pooled": pooled,
                      "per_seed_rpb": per_seed_rpb}, default=str))


if __name__ == "__main__":
    main()
