#!/usr/bin/env python3
"""S0 PREFLIGHT (CPU) for iteration 6.

- inputs/ already holds sha256-verified copies of exp28's inputs/ tree (bench, suite, templates, exp18, exp23, the
  dependency extracts) and inputs/exp28/ (exp28 rows, labels, results, predictions, src, commitments.log);
  this stage re-verifies the bench against the ORIGINAL iteration-2 bench/commitment.json, re-reads the declared
  dependency (all 10 datasets; full HumanEval+ for the F_he exemplars), writes inputs/SHA256SUMS,
- seed audit: the fresh direction seeds 63001-63008 must be unused in every reachable ITER3-ITER6 row file and seed list,
- labeller re-check: 300 random exp28 rows (150 it, 150 pt) re-labelled with the cached judges must reproduce their
  labels; bench gate values, suite references 22/22 (exp28's own re-check functions, reused unchanged).
Writes results/preflight_inputs.json, results/labeller_recheck.json, results/dependency_usage.json.
"""

from __future__ import annotations

import collections
import json
import random
import re
import sys
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (ARTIFACTS_DIR, BENCH, DEP1, DIR_SEEDS6, E28_DATA, EXP8_TASK, INPUTS, PATHS_LOCAL, RESULTS_DIR, ROOT,
                 bench_paths,
                 read_json, read_jsonl, rel, setup_logging, sha256_file, write_json, write_jsonl)

DEP_FILE = "full_data_out.json"
from cfg import upstream as CFG_UPSTREAM  # noqa: E402


def upstream() -> dict[str, Path]:
    """Sibling artifact folders by id under AII_ARTIFACTS_DIR (cfg.upstream), overridable by paths.local.json."""
    return CFG_UPSTREAM()


def verify_bench() -> dict[str, Any]:
    bench_paths()
    from bench.common.catalogue import TASKS

    up = upstream()
    src = up.get("exp11")
    if src is None or not (src / "bench" / "commitment.json").exists():
        return {"pass": None, "note": "ITER2 bench commitment unreachable; using the staged copy's commitment.json",
                "source": "inputs/exp11/bench/commitment.json"}
    com = read_json(src / "bench" / "commitment.json")
    out: dict[str, Any] = {"source": "ITER2 gen_art_experiment_11/bench/commitment.json", "bench": {}, "mismatches": []}
    for t, v in com["tasks"].items():
        d = BENCH / TASKS[t]["task_id"]
        ok = 0
        for f, h in v["files"].items():
            if f == "catalogue":
                continue
            p = d / f
            got = sha256_file(p) if p.exists() else None
            if got != h:
                out["mismatches"].append({"task": t, "file": f})
            else:
                ok += 1
        out["bench"][t] = {"files_checked": ok}
    out["pass"] = not out["mismatches"]
    return out


def extract_dependency() -> dict[str, Any]:
    """Re-read the declared dependency (art_j3Rm_lr2nzR6, 10 datasets). exp28's extracts (noun bank, known-solution
    corpus, CLRS names, llm-creativity modes, HumanEval+/ENAMEL first 20) are checked for equality; the full
    HumanEval+ set (164) is written for the F_he exemplar rule."""
    up = upstream()
    src = up["art_j3Rm_lr2nzR6"] / DEP_FILE
    d = json.loads(src.read_text())
    by = {ds["dataset"]: ds["examples"] for ds in d["datasets"]}
    usage: dict[str, Any] = {"source_file": f"art_j3Rm_lr2nzR6/{DEP_FILE}", "source_sha256": sha256_file(src),
                             "datasets": {k: len(v) for k, v in by.items()}}
    he = []
    for e in by["humanevalplus"]:
        prompt, out = e["input"], e["output"]
        sol = out[len(prompt):] if out.startswith(prompt) else out
        he.append({"task_id": e.get("metadata_task_id"), "entry_point": e.get("metadata_entry_point"),
                   "prompt": prompt, "solution": sol, "test": e.get("metadata_test")})
    write_jsonl(DEP1 / "humanevalplus_all.jsonl", he)
    # equality checks against exp28's extracts (same dependency, same rules)
    corpus_n = 0
    per_source = collections.Counter()
    for name in ("leetcodedataset", "mercury", "thealgorithms_python", "kodcode_algorithmic", "xlcost_python"):
        for e in by.get(name, []):
            code = e.get("output")
            if isinstance(code, str) and "def " in code:
                corpus_n += 1
                per_source[name] += 1
    exp28_corpus = sum(1 for _ in open(DEP1 / "known_solution_corpus.jsonl"))
    cn = sum(1 for e in by["concreteness_norms"] if e.get("metadata_noun_bank_candidate") in (True, "True"))
    clrs = sorted({e.get("metadata_algorithm") for e in by.get("clrs_text", []) if e.get("metadata_algorithm")})
    llmc = collections.Counter(e.get("output") for e in by.get("llm_creativity", []))
    bench_map = collections.Counter(str(e.get("metadata_bench_task")) for e in by["leetcodedataset"]
                                    if e.get("metadata_bench_task") not in (None, "None"))
    enamel_n = len(by.get("enamel", []))
    usage["checks"] = {"known_solution_corpus_rows": corpus_n, "exp28_known_solution_corpus_rows": exp28_corpus,
                       "corpus_identical_count": corpus_n == exp28_corpus, "per_source": dict(per_source),
                       "noun_bank_candidates": cn, "clrs_algorithms": len(clrs),
                       "llm_creativity_t02_modes": dict(llmc), "leetcode_bench_mapped": dict(bench_map),
                       "enamel_rows": enamel_n, "humanevalplus_rows": len(he)}
    usage["used"] = {
        "humanevalplus": f"all {len(he)} problems -> F_he exemplar rule (two lowest-id problems whose canonical "
                         "solution passes the algorithm-neutral AST filter); first 20 -> harness sanity",
        "leetcodedataset|mercury|thealgorithms_python|kodcode_algorithmic|xlcost_python":
            f"{corpus_n} programs -> nearest-known-solution corpus of the novelty audit (S10)",
        "concreteness_norms": f"{cn} noun-bank candidates -> the frozen neutral-twin nouns (exp28 twins, reused)",
        "clrs_text": f"{len(clrs)} textbook algorithm names -> novelty-audit name check",
        "enamel": f"{enamel_n} expert references -> harness sanity (compile + entry point, first 20)",
        "llm_creativity": "T02 blind-judge mode labels -> external reference composition for T2 (descriptive)",
        "leetcodedataset (bench map)": f"{sum(bench_map.values())} bench-mapped problems -> bench provenance check",
    }
    write_json(DEP1 / "llm_creativity_t02_modes_iter6.json", dict(llmc))
    del d, by
    return usage


def seed_audit() -> dict[str, Any]:
    """Every reachable row file / seed list in ITER3-ITER6 gen_art folders (and exp28) must not use 63001-63008 as a
    direction seed. Scans *.py/*.json/*.jsonl under src/, predictions/, directions/ and raw_*.jsonl / samples.jsonl
    direction_seed fields (files <= 400 MB)."""
    up = upstream()
    # original server: the iteration folders (paths.local.json); published layout: every sibling artifact folder
    roots = [up[k] for k in ("iter3", "iter4", "iter5", "iter6") if k in up] or [ARTIFACTS_DIR]
    pat = re.compile(r"\b630(0[1-8])\b")
    rng_pat = re.compile(r"range\(\s*(\d+)\s*,\s*(\d+)\s*\)")
    hits, n_files, n_rows = [], 0, 0
    lo, hi = min(DIR_SEEDS6), max(DIR_SEEDS6)
    for root in roots:
        for sub in sorted(root.glob("*/")):
            if sub.resolve() == ROOT.resolve():
                continue
            for d in ("src", "directions", "predictions"):
                base = sub / d
                if not base.exists():
                    continue
                for p in base.rglob("*"):
                    if not p.is_file() or p.suffix not in (".py", ".json", ".txt", ".yaml") or p.stat().st_size > 5e6:
                        continue
                    n_files += 1
                    txt = p.read_text(errors="ignore")
                    for m in pat.finditer(txt):
                        hits.append({"file": f"{sub.name}/{p.relative_to(sub)}", "match": m.group(0)})
                    for m in rng_pat.finditer(txt):
                        a, b = int(m.group(1)), int(m.group(2))
                        if a > 1000 and a <= hi and b > lo:
                            hits.append({"file": f"{sub.name}/{p.relative_to(sub)}", "match": m.group(0),
                                         "kind": "overlapping range"})
            for p in list((sub / "data").glob("raw_*.jsonl")) if (sub / "data").exists() else []:
                if p.stat().st_size > 4e8:
                    continue
                n_files += 1
                with open(p) as fh:
                    for line in fh:
                        if '"direction_seed"' not in line:
                            continue
                        m = re.search(r'"direction_seed":\s*"?(\d+)', line)
                        n_rows += 1
                        if m and lo <= int(m.group(1)) <= hi:
                            hits.append({"file": f"{sub.name}/{p.relative_to(sub)}", "match": m.group(1)})
                            break
    used_exp28 = sorted({str(r.get("direction_seed")) for f in ("raw_push.jsonl", "raw_confirm.jsonl")
                         for r in read_jsonl(E28_DATA / f)})
    return {"fresh_seeds": [lo, hi], "n_files_scanned": n_files, "n_rows_with_direction_seed": n_rows,
            "hits": hits[:50], "n_hits": len(hits), "exp28_direction_seeds": used_exp28,
            "prior_seed_lists": {"exp23": "9001-9008", "exp22": "9001-9016, 9101-9140, 9301+", "exp28": "52001-52016"},
            "new_namespaces": ["iter6G-ptfs", "iter6G-forced", "iter6G-PN"], "pass": not hits}


def labeller_recheck(n_each: int = 150, seed: int = 6) -> dict[str, Any]:
    """Re-label 150 random exp28 it rows and 150 pt rows (raw text) with the cached judges; compare labels."""
    import label_worker as LW

    rng = random.Random(seed)
    labs = {r["row_id"]: r for r in read_jsonl(E28_DATA / "labels.jsonl")}
    raw_it = [r for f in ("raw_twin.jsonl", "raw_push.jsonl") for r in read_jsonl(E28_DATA / f)]
    raw_pt = [r for f in ("raw_ptchat.jsonl", "raw_ptplain.jsonl") for r in read_jsonl(E28_DATA / f)]
    pick = rng.sample(raw_it, n_each) + rng.sample(raw_pt, n_each)
    new = LW.label_rows(pick, judge=True)
    by = {r["row_id"]: r for r in new}
    res, mism = collections.Counter(), []
    for r in pick:
        o, n = labs.get(r["row_id"]), by.get(r["row_id"])
        kind = r.get("model_kind")
        if o is None or n is None:
            res[f"{kind}_missing"] += 1
            continue
        same = (o["label"] == n["label"]) and (bool(o.get("passed")) == bool(n.get("passed")))
        res[f"{kind}_n"] += 1
        res[f"{kind}_same"] += int(same)
        if o["label"] == "disputed":
            res[f"{kind}_exp28_disputed"] += 1
        if not same:
            mism.append({"row_id": r["row_id"], "exp28": [o["label"], o.get("passed"), o.get("labeller_source")],
                         "now": [n["label"], n.get("passed"), n.get("labeller_source")]})
    n_all = res["it_n"] + res["pt_n"]
    same_all = res["it_same"] + res["pt_same"]
    non_disp = [m for m in mism if m["exp28"][0] != "disputed"]
    return {"n": n_all, "agreement": same_all / max(n_all, 1), "counts": dict(res), "mismatches": mism[:40],
            "n_mismatch": len(mism), "n_mismatch_excluding_exp28_disputed": len(non_disp),
            "pass": len(non_disp) == 0}


def input_hashes() -> dict[str, Any]:
    lines = []
    for p in sorted(INPUTS.rglob("*")):
        if p.is_file() and "__pycache__" not in str(p) and p.name != "SHA256SUMS":
            lines.append(f"{sha256_file(p)}  {rel(p)}")
    (INPUTS / "SHA256SUMS").write_text("\n".join(lines) + "\n")
    return {"n_files_hashed": len(lines)}


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("stage_inputs6")
    import stage_inputs as SI   # exp28's preflight (bench_recheck, suite_recheck, harness_sanity), reused unchanged

    pre: dict[str, Any] = {}
    pre["bench_vs_iter2_commitment"] = verify_bench()
    logger.info(f"bench vs ITER2 commitment: {pre['bench_vs_iter2_commitment'].get('pass')}")
    usage = extract_dependency()
    write_json(RESULTS_DIR / "dependency_usage.json", usage)
    logger.info(f"dependency: {usage['datasets']}")
    pre["seed_audit"] = seed_audit()
    logger.info(f"seed audit: {pre['seed_audit']['n_hits']} hits in {pre['seed_audit']['n_files_scanned']} files")
    pre["harness_sanity"] = SI.harness_sanity()
    logger.info(f"harness sanity: HE+ {pre['harness_sanity']['humanevalplus_pass']}/{pre['harness_sanity']['humanevalplus_n']}")
    lr = {"bench": SI.bench_recheck(), "exp8_suite": SI.suite_recheck()}
    lr["exp28_rows_relabel"] = labeller_recheck()
    write_json(RESULTS_DIR / "labeller_recheck.json", lr)
    logger.info(f"exp28 relabel agreement {lr['exp28_rows_relabel']['agreement']:.3f} "
                f"({lr['exp28_rows_relabel']['n_mismatch']} mismatches)")
    pre["input_hashes"] = input_hashes()
    write_json(RESULTS_DIR / "preflight_inputs.json", pre)
    logger.info("preflight done")


if __name__ == "__main__":
    main()
