#!/usr/bin/env python3
"""PREFLIGHT (CPU): stage every upstream input into inputs/ (read-only copies, sha256 in inputs/SHA256SUMS), verify the
frozen bench against the ITER2 bench/commitment.json, extract the declared dependency (art_j3Rm_lr2nzR6, all 10
datasets), audit the fresh direction seeds against every earlier seed list, and re-check the frozen labellers on
their gold sets and references (re-gate step 5a).

Upstream artifacts are sibling folders named by artifact id (AII_ARTIFACTS_DIR overrides their parent); the unpublished
paths.local.json can override individual locations (absolute server paths never enter published files). Bench, suite and templates are taken from the iteration-4 Gemma artifact's sha256-verified inputs/ copies
(exp23), which were themselves verified against the iteration-2 originals; the bench is re-verified here against the
original ITER2 commitment.json.
"""

from __future__ import annotations

import collections
import json
import os
import re
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (BENCH, BENCH_TASKS, DEP1, DIR_SEEDS, E23, INPUTS, PATHS_LOCAL, RESULTS_DIR, ROOT, SUITE, bench_paths,
                 read_json, read_jsonl, rel, setup_logging, sha256_file, write_json, write_jsonl)

# (source key, relative source path, destination under inputs/)
COPIES: list[tuple[str, str, str]] = [
    ("exp23", "inputs/exp11/bench", "exp11/bench"),
    ("exp23", "inputs/exp11/results", "exp11/results"),
    ("exp23", "inputs/exp8/suite", "exp8/suite"),
    ("exp23", "inputs/exp8/prompts", "exp8/prompts"),
    ("exp23", "inputs/exp7/frozen", "exp7/frozen"),
    ("exp23", "inputs/exp7/prompts", "exp7/prompts"),
    ("exp23", "inputs/exp18/inputs/known_solutions.jsonl", "exp18/inputs/known_solutions.jsonl"),
    ("exp18", "results/known_solutions_summary.json", "exp18/results/known_solutions_summary.json"),
    ("exp23", "inputs/exp18/results/novelty_audit.json", "exp18/results/novelty_audit.json"),
    # iteration-4 Gemma record (exp23): engine-check reference, rivals, re-scoring appendix, unit ratio
    ("exp23", "results/qwen_ratio.json", "exp23/results/qwen_ratio.json"),
    ("exp23", "results/escape.json", "exp23/results/escape.json"),
    ("exp23", "results/c3b.json", "exp23/results/c3b.json"),
    ("exp23", "results/proximity.json", "exp23/results/proximity.json"),
    ("exp23", "results/opening_ladder.json", "exp23/results/opening_ladder.json"),
    ("exp23", "results/rivals.json", "exp23/results/rivals.json"),
    ("exp23", "results/bans.json", "exp23/results/bans.json"),
    ("exp23", "results/posthoc_t2_relabel.json", "exp23/results/posthoc_t2_relabel.json"),
    ("exp23", "results/unit_sensitivity.json", "exp23/results/unit_sensitivity.json"),
    ("exp23", "results/banfree_predictors.json", "exp23/results/banfree_predictors.json"),
    ("exp23", "predictions/commit1.json", "exp23/predictions/commit1.json"),
    ("exp23", "predictions/commit_preban.json", "exp23/predictions/commit_preban.json"),
    ("exp23", "data/samples.jsonl", "exp23/data/samples.jsonl"),
    ("exp23", "src", "exp23/src"),
    # seed lists of earlier iterations (seed audit) and the frozen iteration-4 screen
    ("exp22", "src/cfg4.py", "exp22/src/cfg4.py"),
    ("eval3", "screen.json", "eval3/screen.json"),
    ("eval3", "screen.sha256", "eval3/screen.sha256"),
]
DEP_FILE = "full_data_out.json"


# Upstream artifacts are sibling folders of this one in the published repository, named by artifact id. ONE environment
# variable, AII_ARTIFACTS_DIR, overrides their common parent (default: the parent folder of this artifact). The optional,
# unpublished paths.local.json {short name: path} overrides individual locations (used on the original run server,
# whose folders are not named by id).
ARTIFACTS_DIR = Path(os.environ.get("AII_ARTIFACTS_DIR", str(ROOT.parent)))
UPSTREAM_IDS = {
    "exp23": "art_k6nzFCDLOjQP",            # iteration-4 Gemma artifact (engine, push, units, labellers, records)
    "exp11": "art_0ndRfWKBWclR",            # frozen 13-task bench (bench/commitment.json for the sha256 check)
    "exp8": "art_8_ULPE8jJQc_",             # T1/T2 suite (staged through exp23's verified copy)
    "exp7": "art_6zBfl3kDjeiP",             # frozen templates / nouns (staged through exp23's verified copy)
    "exp18": "art_ccAbfJVcv0LO",            # known-solutions index for the novelty audit
    "eval3": "art_sV0cQ3ef1ZRQ",            # iteration-4 evaluation: frozen screen.json
    "art_j3Rm_lr2nzR6": "art_j3Rm_lr2nzR6",  # declared dependency: source data (10 datasets)
}
# exp22 (iteration-4 gen_art_experiment_22, whose src/cfg4.py lists the seeds 9001-9016 / 9101-9140 / 9301+ already
# used) has no artifact id recorded in this run's files; it is resolved through paths.local.json only, and the
# published inputs/exp22/src/cfg4.py is the copy the seed audit actually read.


def upstream() -> dict[str, Path]:
    out = {k: ARTIFACTS_DIR / v for k, v in UPSTREAM_IDS.items()}
    if PATHS_LOCAL.exists():
        out.update({k: Path(v) for k, v in read_json(PATHS_LOCAL).items()})
    return out


def _copy(src: Path, dst: Path) -> None:
    if src.is_dir():
        if dst.exists():
            return
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(src, dst)


def stage_copies() -> dict[str, Any]:
    up = upstream()
    missing, done = [], []
    for key, src_rel, dst_rel in COPIES:
        if key not in up:
            missing.append(f"{key}/{src_rel}")
            logger.warning(f"no location for upstream {key} (set paths.local.json); the published inputs/{dst_rel} is used")
            continue
        src = up[key] / src_rel
        if not src.exists():
            missing.append(f"{key}/{src_rel}")
            logger.warning(f"missing upstream input {key}/{src_rel}")
            continue
        _copy(src, INPUTS / dst_rel)
        done.append(dst_rel)
    return {"missing": missing, "copied": done}


def verify_bench_against_iter2() -> dict[str, Any]:
    """Every bench task dir (our copy) vs the ORIGINAL iteration-2 bench/commitment.json."""
    bench_paths()
    from bench.common.catalogue import TASKS

    com = read_json(upstream()["exp11"] / "bench" / "commitment.json")
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
                out["mismatches"].append({"task": t, "file": f, "expected": h, "got": got})
            else:
                ok += 1
        out["bench"][t] = {"files_checked": ok}
    out["pass"] = not out["mismatches"]
    return out


def extract_dependency() -> dict[str, Any]:
    """Read the declared dependency once; keep the subsets this artifact uses (the 96 MB file is not copied).
    Every one of the 10 datasets is used (results/dependency_usage.json says how)."""
    src = upstream()["art_j3Rm_lr2nzR6"] / DEP_FILE
    DEP1.mkdir(parents=True, exist_ok=True)
    usage: dict[str, Any] = {"source_file": f"art_j3Rm_lr2nzR6/{DEP_FILE}", "source_sha256": sha256_file(src)}
    d = json.loads(src.read_text())
    by = {ds["dataset"]: ds["examples"] for ds in d["datasets"]}
    usage["datasets"] = {k: len(v) for k, v in by.items()}
    cn = [e for e in by["concreteness_norms"] if e.get("metadata_noun_bank_candidate") in (True, "True")]
    write_json(DEP1 / "concreteness_noun_bank_candidates.json",
               [{"word": e["input"], "concreteness": float(e["output"]), "subtlex": e.get("metadata_subtlex_frequency"),
                 "qwen3_tokens_ws": e.get("metadata_qwen3_tokens_with_leading_space"),
                 "oewn": e.get("metadata_oewn_noun_lexfiles")} for e in cn])
    corpus = []
    for name in ("leetcodedataset", "mercury", "thealgorithms_python", "kodcode_algorithmic", "xlcost_python"):
        for e in by.get(name, []):
            code = e.get("output")
            if not isinstance(code, str) or "def " not in code:
                continue
            corpus.append({"source": name, "row": e.get("metadata_row_index"),
                           "bench_task": e.get("metadata_bench_task"),
                           "named": e.get("metadata_named_algorithms") or e.get("metadata_bench_mode"),
                           "tasks_named": e.get("metadata_bench_tasks_named"), "code": code[:6000]})
    write_jsonl(DEP1 / "known_solution_corpus.jsonl", corpus)
    # R6 / first-last-position solutions (TheAlgorithms, KodCode, Mercury, LeetCode): source of the R6 linear-scan
    # extended-catalogue reference if the structural audit needs one
    r6 = [c for c in corpus if str(c.get("bench_task") or "").startswith("R6")]
    write_jsonl(DEP1 / "r6_known_solutions.jsonl", r6)
    clrs = sorted({e.get("metadata_algorithm") for e in by.get("clrs_text", []) if e.get("metadata_algorithm")})
    write_json(DEP1 / "clrs_algorithm_names.json", clrs)
    llmc = collections.Counter(e.get("output") for e in by.get("llm_creativity", []))
    write_json(DEP1 / "llm_creativity_t02_modes.json", dict(llmc))
    hep = [{"task_id": e.get("metadata_task_id"), "prompt": e["input"], "solution": e["output"],
            "entry_point": e.get("metadata_entry_point"), "test": e.get("metadata_test")}
           for e in by.get("humanevalplus", [])[:20]]
    write_jsonl(DEP1 / "humanevalplus_first20.jsonl", hep)
    ena = [{"task_id": e.get("metadata_task_id"), "reference_body": e.get("metadata_reference_body"),
            "prompt": e["input"], "entry_point": e.get("metadata_entry_point")} for e in by.get("enamel", [])[:20]]
    write_jsonl(DEP1 / "enamel_first20.jsonl", ena)
    usage["used"] = {
        "concreteness_norms": f"{len(cn)} noun-bank candidates -> neutral-twin noun bank (re-tokenised by Gemma; "
                              "the frozen exp23 twins use these nouns)",
        "leetcodedataset|mercury|thealgorithms_python|kodcode_algorithmic|xlcost_python":
            f"{len(corpus)} programs -> known-solution corpus for the novelty audit (nearest known solution); "
            f"{len(r6)} R6 programs -> extended-catalogue reference pool",
        "clrs_text": f"{len(clrs)} textbook algorithm names -> novelty-audit name check",
        "humanevalplus": "first 20 canonical solutions -> sandbox-harness sanity check",
        "enamel": "first 20 expert references -> sandbox-harness sanity check (compile + entry point)",
        "llm_creativity": "T02 blind-judge mode labels -> external reference composition for T2",
    }
    del d, by
    return usage


def harness_sanity() -> dict[str, Any]:
    """Run HumanEval+ canonical solutions with their own tests in an isolated interpreter (-I)."""
    import subprocess

    rows = read_jsonl(DEP1 / "humanevalplus_first20.jsonl")
    ok = 0
    res = []
    for r in rows:
        prog = r["prompt"] + r["solution"] + "\n\n" + (r["test"] or "") + f"\n\ncheck({r['entry_point']})\n"
        try:
            pr = subprocess.run([sys.executable, "-I", "-"], input=prog, capture_output=True, text=True, timeout=120)
            good = pr.returncode == 0
        except subprocess.TimeoutExpired:
            good = False
        ok += good
        res.append({"task_id": r["task_id"], "ok": good})
    ena = read_jsonl(DEP1 / "enamel_first20.jsonl")
    e_ok = 0
    for r in ena:
        try:
            compile((r["prompt"] or "") + "\n" + (r["reference_body"] or ""), "<e>", "exec")
            e_ok += 1
        except SyntaxError:
            pass
    return {"humanevalplus_pass": ok, "humanevalplus_n": len(rows), "enamel_compile": e_ok, "enamel_n": len(ena),
            "rows": res}


def seed_audit() -> dict[str, Any]:
    """Regex-scan ITER3 and ITER4 directions/ and src/ (and the iteration-4 cfg seed lists) for any of the fresh
    seeds 52001-52016 or a seed range that overlaps them."""
    up = upstream()
    # original server: the iteration-3 and iteration-4 gen_art folders; elsewhere: every sibling artifact folder
    roots = [up["iter3"], up["iter4"]] if ("iter3" in up and "iter4" in up) else [ARTIFACTS_DIR]
    pat = re.compile(r"\b(520(0[1-9]|1[0-6]))\b")
    rng_pat = re.compile(r"range\(\s*(\d+)\s*,\s*(\d+)\s*\)")
    hits, n_files = [], 0
    for root in roots:
        for sub in root.glob("*/"):
            for d in ("src", "directions"):
                base = sub / d
                if not base.exists():
                    continue
                for p in base.rglob("*"):
                    if not p.is_file() or p.suffix not in (".py", ".json", ".txt", ".yaml", ".md"):
                        continue
                    if p.stat().st_size > 5_000_000:
                        continue
                    n_files += 1
                    txt = p.read_text(errors="ignore")
                    for m in pat.finditer(txt):
                        hits.append({"file": f"{p.parent.parent.name}/{p.relative_to(sub)}", "match": m.group(0)})
                    for m in rng_pat.finditer(txt):
                        a, b = int(m.group(1)), int(m.group(2))
                        if a < max(DIR_SEEDS) + 1 and b > min(DIR_SEEDS) and a > 1000:
                            hits.append({"file": f"{p.parent.parent.name}/{p.relative_to(sub)}",
                                         "match": m.group(0), "kind": "overlapping range"})
    prior = {"exp23_escape": "9001-9008", "exp22_screen": "9001-9016", "exp22_population": "9101-9140",
             "exp22_targeted": "9301+"}
    return {"fresh_seeds": [min(DIR_SEEDS), max(DIR_SEEDS)], "n_files_scanned": n_files, "hits": hits,
            "prior_seed_lists": prior, "pass": not hits}


def input_hashes() -> dict[str, Any]:
    lines = []
    for p in sorted(INPUTS.rglob("*")):
        if p.is_file() and "__pycache__" not in str(p):
            lines.append(f"{sha256_file(p)}  {rel(p)}")
    (INPUTS / "SHA256SUMS").write_text("\n".join(lines) + "\n")
    return {"n_files_hashed": len(lines)}


def bench_recheck() -> dict[str, Any]:
    bench_paths()
    from bench.common.catalogue import TASKS
    from bench.common.labeling import label_one
    from bench.common.testgen import read_tests

    res: dict[str, Any] = {}
    for t in BENCH_TASKS:
        d = BENCH / TASKS[t]["task_id"]
        cases = read_tests(d / "tests.jsonl")
        refs = sorted((d / "references").glob("*.py"))

        def lab(code: str, sid: str) -> dict[str, Any]:
            return label_one({"sample_id": sid, "task": t, "condition": "recheck", "mode": None, "paraphrase_id": None,
                              "round": None, "attempt_idx": None, "seed": 0, "finish_reason": "stop",
                              "text": "```python\n" + code + "\n```"}, cases)
        with ThreadPoolExecutor(4) as ex:
            rl = list(ex.map(lambda p: (p.stem, lab(p.read_text(), p.stem)), refs))
        ref_ok = sum(1 for m, l in rl if l.get("runtime_label") == m and l.get("passed"))
        gold = read_jsonl(d / "gold_set.jsonl")
        with ThreadPoolExecutor(4) as ex:
            gl = list(ex.map(lambda g: lab(g["code"], g["gold_id"]), gold))
        agree = [l.get("runtime_label") == g["adjudicated"] for g, l in zip(gold, gl)]
        gate = read_json(d / "gate.json")
        exp = gate["gold"]["runtime_vs_adjudicated"]
        acc = sum(agree) / max(len(agree), 1)
        res[t] = {"references_ok": ref_ok, "n_references": len(refs), "gold_n": len(gold),
                  "gold_runtime_vs_adjudicated": acc, "gate_runtime_vs_adjudicated": exp,
                  "reproduces_gate": abs(acc - exp) <= 1e-9, "references_pass": ref_ok == len(refs)}
        logger.info(f"recheck {t}: refs {ref_ok}/{len(refs)}, gold runtime acc {acc:.4f} (gate {exp:.4f})")
    return res


def suite_recheck() -> dict[str, Any]:
    bench_paths()
    from labeller import ast_rules, runtime_rules
    from tasks.harness import evaluate_program

    gr = read_json(SUITE / "labeller" / "gate_report.json")
    refs = []
    for tdir, t in (("t1_grid", "t1"), ("t2_wsp", "t2")):
        for p in sorted((SUITE / "tasks" / tdir / "references").glob("*.py")):
            refs.append((t, p))
    ref_modes = {k: v["mode"] for k, v in (gr["references"].items() if isinstance(gr["references"], dict) else [])}

    def one(tp):
        t, p = tp
        code = p.read_text()
        ev = evaluate_program(t, code)
        rl = runtime_rules.label(t, ev["probes"])[0]
        al = ast_rules.label(code, t)[0]
        return {"file": f"{t}/{p.name}", "runtime": rl, "ast": al, "passed": bool(ev["tests"].get("passed")),
                "mode": ref_modes.get(f"{t}/{p.name}")}
    with ThreadPoolExecutor(4) as ex:
        rr = list(ex.map(one, refs))
    ok = sum(1 for r in rr if r["mode"] is not None and r["runtime"] == r["mode"] and r["ast"] == r["mode"])
    gold = [g for g in read_jsonl(SUITE / "labeller" / "gold_set.jsonl") if g.get("split") == "eval"]
    adj_key = next((k for k in ("adjudicated", "gold_label", "label") if gold and k in gold[0]), None)

    def gone(g):
        ev = evaluate_program(g["task"], g["code"])
        return runtime_rules.label(g["task"], ev["probes"])[0], ast_rules.label(g["code"], g["task"])[0]
    with ThreadPoolExecutor(4) as ex:
        gl = list(ex.map(gone, gold))
    out: dict[str, Any] = {"references_ok": ok, "n_references": len(rr), "references": rr}
    if adj_key:
        acc_rt = sum(1 for g, (r, a) in zip(gold, gl) if r == g[adj_key]) / max(len(gold), 1)
        acc_ast = sum(1 for g, (r, a) in zip(gold, gl) if a == g[adj_key]) / max(len(gold), 1)
        em = gr["eval_metrics"]
        out.update({"gold_eval_n": len(gold), "acc_runtime_vs_adjudicated": acc_rt, "acc_ast_vs_adjudicated": acc_ast,
                    "gate_acc_runtime": em["acc_runtime_vs_adjudicated"], "gate_acc_ast": em["acc_ast_vs_adjudicated"],
                    "reproduces_gate_runtime": abs(acc_rt - em["acc_runtime_vs_adjudicated"]) <= 1e-9,
                    "exp23_reproduced_value": 0.804})
    logger.info(f"suite recheck: refs {ok}/{len(rr)}; {({k: v for k, v in out.items() if k.startswith('acc')})}")
    return out


def main() -> None:
    setup_logging("stage_inputs")
    st = stage_copies()
    logger.info(f"staged {len(st['copied'])} inputs; missing: {st['missing']}")
    usage = extract_dependency()
    usage["harness_sanity"] = harness_sanity()
    write_json(RESULTS_DIR / "dependency_usage.json", usage)
    logger.info(f"dependency usage: {usage['datasets']}; harness {usage['harness_sanity']['humanevalplus_pass']}/20")
    vb = verify_bench_against_iter2()
    sa = seed_audit()
    ih = input_hashes()
    write_json(RESULTS_DIR / "preflight_inputs.json", {"staging": st, "bench_vs_iter2_commitment": vb,
                                                       "seed_audit": sa, **ih})
    logger.info(f"bench vs ITER2 commitment: pass={vb['pass']} ({len(vb['mismatches'])} mismatches); "
                f"seed audit pass={sa['pass']} ({sa['n_files_scanned']} files); {ih['n_files_hashed']} files hashed")
    if "--recheck" in sys.argv:
        lr = {"bench": bench_recheck(), "exp8_suite": suite_recheck(),
              "note": "re-gate 5a: mechanical labels only (runtime/AST) on gold sets + references"}
        write_json(RESULTS_DIR / "labeller_recheck.json", lr)
    logger.info("preflight staging done")


if __name__ == "__main__":
    main()
