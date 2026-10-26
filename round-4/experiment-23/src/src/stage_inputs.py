#!/usr/bin/env python3
"""STEP 1: stage every upstream input into inputs/ (sha256-recorded), verify the frozen bench against
bench/commitment.json, re-check the frozen labellers on their gold sets and references, build the Gemma noun bank from
the declared dependency (art_j3Rm_lr2nzR6 concreteness_norms) and extract the dependency's known-solution corpus.

Every dataset of the declared dependency is used (results/dependency_usage.json says how):
  concreteness_norms -> neutral-noun bank; leetcodedataset, mercury, thealgorithms_python, kodcode_algorithmic,
  xlcost_python -> known-solution corpus of the novelty audit; clrs_text -> catalogue of textbook algorithm names
  for the novelty audit; humanevalplus, enamel -> sandbox-harness sanity check; llm_creativity -> external T2
  mode-composition reference (labels only).
"""

from __future__ import annotations

import collections
import json
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (BENCH, BENCH_TASKS, DEP1, E11, INPUTS, RESULTS_DIR, SUITE, bench_paths, read_json, read_jsonl,
                 rel, sha256_file, upstream, write_json, write_jsonl)

COPIES: dict[str, list[str]] = {
    "exp11": ["bench", "results/pilot_stats.json", "results/frozen_tasks.json"],
    "exp8": ["suite", "prompts/frozen_prompts.json", "engine.py"],
    "exp7": ["frozen/templates_nouns_padding.json", "prompts/prompts_v2.json"],
    "exp17": ["src/hooks.py", "src/sampling.py", "src/engine.py", "src/cfg.py", "src/prompts.py",
              "src/label_worker.py", "prompts/prompts.jsonl", "prompts/prompts_summary.json", "data/labels.jsonl",
              "data/realised_norms.jsonl", "results/unit_tests_gpu.json", "directions/direction_hashes.json"]
             + [f"directions/norms_{t}.npy" for t in ("T1", "T2", "T03", "T04", "T05", "T06")]
             + [f"directions/rand_{s}.npy" for s in range(9001, 9009)],
    "exp13": ["results/tensors", "data/samples.jsonl", "src"],
    "exp15": ["src"],
    "exp18": ["inputs/known_solutions.jsonl", "results/known_solutions_summary.json", "results/novelty_audit.json"],
    "exp16": ["src"],
}
DEP_FILE = "full_data_out.json"


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
    missing = []
    for key, items in COPIES.items():
        for it in items:
            src = up[key] / it
            if not src.exists():
                missing.append(f"{key}/{it}")
                logger.warning(f"missing upstream input {key}/{it}")
                continue
            _copy(src, INPUTS / key / it)
    return {"missing": missing}


def extract_dependency() -> dict[str, Any]:
    """Read the declared dependency once; keep the subsets this artifact uses (the 96 MB file itself is not copied)."""
    src = upstream()["art_j3Rm_lr2nzR6"] / DEP_FILE
    DEP1.mkdir(parents=True, exist_ok=True)
    out_flag = DEP1 / "concreteness_noun_bank_candidates.json"
    usage: dict[str, Any] = {"source_file": f"art_j3Rm_lr2nzR6/{DEP_FILE}", "source_sha256": sha256_file(src)}
    d = json.loads(src.read_text())
    by = {ds["dataset"]: ds["examples"] for ds in d["datasets"]}
    usage["datasets"] = {k: len(v) for k, v in by.items()}
    cn = [e for e in by["concreteness_norms"] if e.get("metadata_noun_bank_candidate")]
    write_json(out_flag, [{"word": e["input"], "concreteness": float(e["output"]),
                           "subtlex": e.get("metadata_subtlex_frequency"),
                           "qwen3_tokens_ws": e.get("metadata_qwen3_tokens_with_leading_space"),
                           "oewn": e.get("metadata_oewn_noun_lexfiles")} for e in cn])
    # known-solution corpus: every program row of the five program datasets (text kept for the AST nearest search)
    corpus = []
    for name in ("leetcodedataset", "mercury", "thealgorithms_python", "kodcode_algorithmic", "xlcost_python"):
        for e in by.get(name, []):
            code = e.get("output") if name != "kodcode_algorithmic" else e.get("output")
            if not isinstance(code, str) or "def " not in code:
                continue
            corpus.append({"source": name, "row": e.get("metadata_row_index"),
                           "bench_task": e.get("metadata_bench_task"),
                           "named": e.get("metadata_named_algorithms") or e.get("metadata_bench_mode"),
                           "tasks_named": e.get("metadata_bench_tasks_named"), "code": code[:6000]})
    write_jsonl(DEP1 / "known_solution_corpus.jsonl", corpus)
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
        "concreteness_norms": f"{len(cn)} noun-bank candidates -> neutral-twin noun bank (re-tokenised by Gemma)",
        "leetcodedataset|mercury|thealgorithms_python|kodcode_algorithmic|xlcost_python":
            f"{len(corpus)} programs -> known-solution corpus for the novelty audit (nearest known solution)",
        "clrs_text": f"{len(clrs)} textbook algorithm names -> novelty-audit name check",
        "humanevalplus": "first 20 canonical solutions -> sandbox-harness sanity check",
        "enamel": "first 20 expert references -> sandbox-harness sanity check (compile + entry point)",
        "llm_creativity": "T02 blind-judge mode labels -> external reference composition for T2",
    }
    del d, by
    return usage


def harness_sanity() -> dict[str, Any]:
    """Run HumanEval+ canonical solutions with their own tests in the bench sandbox interpreter (-I -S)."""
    import subprocess

    from cfg import DEP1 as D

    py = sys.executable  # EvalPlus tests import numpy: the project venv interpreter (isolated mode, -I)
    rows = read_jsonl(D / "humanevalplus_first20.jsonl")
    ok = 0
    res = []
    for r in rows:
        prog = r["prompt"] + r["solution"] + "\n\n" + (r["test"] or "") + f"\n\ncheck({r['entry_point']})\n"
        try:
            pr = subprocess.run([py, "-I", "-"], input=prog, capture_output=True, text=True, timeout=120)
            good = pr.returncode == 0
        except subprocess.TimeoutExpired:
            good = False
        ok += good
        res.append({"task_id": r["task_id"], "ok": good})
    ena = read_jsonl(D / "enamel_first20.jsonl")
    e_ok = 0
    for r in ena:
        try:
            compile((r["prompt"] or "") + "\n" + (r["reference_body"] or ""), "<e>", "exec")
            e_ok += 1
        except SyntaxError:
            pass
    return {"humanevalplus_pass": ok, "humanevalplus_n": len(rows), "enamel_compile": e_ok, "enamel_n": len(ena),
            "rows": res}


def input_hashes() -> dict[str, Any]:
    bench_paths()
    from bench.common.catalogue import TASKS

    com = read_json(BENCH / "commitment.json")
    out: dict[str, Any] = {"bench": {}, "mismatches": []}
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
    lines = []
    for p in sorted(INPUTS.rglob("*")):
        if p.is_file() and "__pycache__" not in str(p):
            lines.append(f"{sha256_file(p)}  {rel(p)}")
    (INPUTS / "SHA256SUMS").write_text("\n".join(lines) + "\n")
    out["n_files_hashed"] = len(lines)
    return out


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
                    "reproduces_gate_runtime": abs(acc_rt - em["acc_runtime_vs_adjudicated"]) <= 1e-9})
    logger.info(f"suite recheck: refs {ok}/{len(rr)}; {({k: v for k, v in out.items() if k.startswith('acc')})}")
    return out


def main() -> None:
    from cfg import setup_logging

    setup_logging("stage_inputs")
    st = stage_copies()
    logger.info(f"staged copies; missing: {st['missing']}")
    usage = extract_dependency()
    usage["harness_sanity"] = harness_sanity()
    write_json(RESULTS_DIR / "dependency_usage.json", usage)
    logger.info(f"dependency usage: {usage['datasets']}; harness {usage['harness_sanity']['humanevalplus_pass']}/20")
    ih = input_hashes()
    ih["missing_upstream"] = st["missing"]
    write_json(RESULTS_DIR / "input_hashes.json", ih)
    logger.info(f"bench vs commitment.json: pass={ih['pass']} mismatches={len(ih['mismatches'])}")
    lr = {"bench": bench_recheck(), "exp8_suite": suite_recheck(),
          "note": "mechanical labels only (runtime/AST); the judge is not re-run (spend)"}
    write_json(RESULTS_DIR / "labeller_recheck.json", lr)
    logger.info("STEP 1 done")


if __name__ == "__main__":
    main()
