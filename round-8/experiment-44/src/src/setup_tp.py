#!/usr/bin/env python3
"""Stage 0: hardware record, read-only copies of the prior-iteration inputs (inputs/ + SHA256SUMS), the vendored
harness + labeller (vendor/exp9, vendor/exp2), carried screen rows C9/C10, dependency-dataset usage, and the
labeller re-validation (references, gold set, mutants, exp2 suite agreement)."""

from __future__ import annotations

import collections
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from loguru import logger

from common import (CANON_ORDER, DATA, INPUTS, PRED, RESULTS, ROOT, SRC_PATHS, VENDOR, deviation, read_json,
                    read_jsonl, sha256_file, sha256_text, write_json, write_jsonl)

COPY_PLAN: list[tuple[str, str, str]] = [
    # (source key, relative source path, destination under inputs/)
    ("exp9", "tasks/t1_grid/spec.txt", "exp9/tasks/t1_grid/spec.txt"),
    ("exp9", "tasks/t1_grid/tests.json", "exp9/tasks/t1_grid/tests.json"),
    ("exp9", "tasks/t1_grid/tests_small.json", "exp9/tasks/t1_grid/tests_small.json"),
    ("exp9", "tasks/t1_grid/limits.json", "exp9/tasks/t1_grid/limits.json"),
    ("exp9", "tasks/t1_grid/references", "exp9/tasks/t1_grid/references"),
    ("exp9", "tasks/harness.py", "exp9/tasks/harness.py"),
    ("exp9", "tasks/sandbox_tests.py", "exp9/tasks/sandbox_tests.py"),
    ("exp9", "tasks/tests_gen.py", "exp9/tasks/tests_gen.py"),
    ("exp9", "canon/tasks/sandbox_tests.py", "exp9/canon/tasks/sandbox_tests.py"),
    ("exp9", "canon/labeller", "exp9/canon/labeller"),
    ("exp9", "labeller_ext", "exp9/labeller_ext"),
    ("exp9", "prompts/frozen_prompts.json", "exp9/prompts/frozen_prompts.json"),
    ("exp9", "mb/prompts.py", "exp9/mb/prompts.py"),
    ("exp9", "common.py", "exp9/common.py"),
    ("exp9", "results/catalogue_keep.json", "exp9/results/catalogue_keep.json"),
    ("exp9", "results/sets_and_geometry.json", "exp9/results/sets_and_geometry.json"),
    ("exp9", "results/manifold.json", "exp9/results/manifold.json"),
    ("exp9", "results/persistence.json", "exp9/results/persistence.json"),
    ("exp9", "results/landing.json", "exp9/results/landing.json"),
    ("exp2", "tasks/hidden_tests_t1.json", "exp2/tasks/hidden_tests_t1.json"),
    ("exp2", "tasks/harness.py", "exp2/tasks/harness.py"),
    ("exp2", "tasks/references.py", "exp2/tasks/references.py"),
    ("exp2", "tasks/tasklib.py", "exp2/tasks/tasklib.py"),
    ("exp34", "src/top5geo.py", "exp34/src/top5geo.py"),
    ("exp34", "results/top5_geometry.json", "exp34/results/top5_geometry.json"),
    ("exp34", "results/top5_landing.json", "exp34/results/top5_landing.json"),
    ("exp34", "cache/known_corpus.jsonl", "exp34/cache/known_corpus.jsonl"),
    ("exp29", "results/known_solutions.json", "exp29/results/known_solutions.json"),
    ("exp18", "results/known_solutions_summary.json", "exp18/results/known_solutions_summary.json"),
]
EXP31_TOP5 = SRC_PATHS["exp31"] / "results" / "top5.json"   # art_zNyBP6zieI5u


def _copy(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "judge_cache.jsonl"))
    else:
        shutil.copy2(src, dst)
    return True


def hardware() -> dict[str, Any]:
    def sh(cmd: str) -> str:
        try:
            return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30).stdout.strip()
        except subprocess.TimeoutExpired:
            return "timeout"
    hw = {"nvidia_smi": sh("nvidia-smi --query-gpu=name,memory.total,memory.used,driver_version --format=csv"),
          "cpu_quota": sh("cat /sys/fs/cgroup/cpu/cpu.cfs_quota_us /sys/fs/cgroup/cpu/cpu.cfs_period_us"),
          "ram_limit_bytes": sh("cat /sys/fs/cgroup/memory/memory.limit_in_bytes"),
          "cpu_model": sh("lscpu | grep 'Model name'"), "df": sh("df -h . | tail -1"),
          "c_compiler": sh("which gcc cc clang || echo none"), "planned_gpu": "RTX A4500 20 GB",
          "note": "actual GPU differs from the plan (RTX 2000 Ada, 16 GB); see deviation D8"}
    write_json(PRED / "hardware.json", hw)
    return hw


def verify_inputs() -> bool:
    """True if inputs/SHA256SUMS exists and every listed file matches (the published repository ships inputs/)."""
    sums = INPUTS / "SHA256SUMS"
    if not sums.exists():
        return False
    for line in sums.read_text().splitlines():
        if not line.strip():
            continue
        h, rel = line.split("  ", 1)
        p = ROOT / rel
        if not p.exists() or sha256_file(p) != h:
            logger.warning(f"inputs checksum mismatch or missing: {rel}")
            return False
    return True


def copy_inputs(force: bool = False) -> dict[str, Any]:
    if not force and verify_inputs():
        logger.info("inputs/SHA256SUMS verifies: reusing the copied inputs (set force to re-copy from TP_DEP_*)")
        return read_json(RESULTS / "inputs_status.json") if (RESULTS / "inputs_status.json").exists() else \
            {"copied": [], "missing": [], "reused": True}
    status: dict[str, Any] = {"copied": [], "missing": []}
    for key, rel, dst in COPY_PLAN:
        src = SRC_PATHS[key] / rel
        ok = _copy(src, INPUTS / dst)
        (status["copied"] if ok else status["missing"]).append({"src_key": key, "rel": rel, "dst": dst})
        if not ok:
            logger.warning(f"input missing: {key}/{rel}")
    if _copy(EXP31_TOP5, INPUTS / "exp31" / "results" / "top5.json"):
        status["copied"].append({"src_key": "exp31", "rel": "results/top5.json", "dst": "exp31/results/top5.json"})
    else:
        status["missing"].append({"src_key": "exp31", "rel": "results/top5.json"})
    # iteration-2 TOP5 raw + labelled rows (renderer byte check, carried row C9)
    e9 = SRC_PATHS["exp9"]   # resolved through TP_DEP_EXP9 / TP_DEPS_DIR
    raw = [r for r in read_jsonl(e9 / "data" / "raw_session2.jsonl") if r.get("condition") == "multi:TOP5"]
    lab = [r for r in read_jsonl(e9 / "data" / "labelled_session2.jsonl") if r.get("condition") == "multi:TOP5"]
    (INPUTS / "exp9" / "data").mkdir(parents=True, exist_ok=True)
    write_jsonl(INPUTS / "exp9" / "data" / "top5_raw_rows.jsonl",
                [{k: v for k, v in r.items() if k != "token_ids"} for r in raw])
    write_jsonl(INPUTS / "exp9" / "data" / "top5_labelled_rows.jsonl",
                [{k: r.get(k) for k in ("req_id", "condition", "template", "label", "passed", "labeller_source",
                                        "runtime_label", "ast_label", "code")} for r in lab])
    status["exp9_top5_rows"] = {"raw": len(raw), "labelled": len(lab)}
    # dependency dataset: sha256 of the full file + the corpus rows the novelty audit needs
    ds_src = SRC_PATHS["dataset"] / "full_data_out.json"
    status["dataset"] = dataset_extract(ds_src)
    # vendored executable copies (harness + labeller) used by every stage
    for sub in ("tasks", "labeller_ext"):
        _copy(INPUTS / "exp9" / sub, VENDOR / sub)
    (VENDOR / "__init__.py").touch()
    _copy(INPUTS / "exp2" / "tasks" / "harness.py", ROOT / "vendor" / "exp2" / "harness.py")
    _copy(INPUTS / "exp2" / "tasks" / "hidden_tests_t1.json", ROOT / "vendor" / "exp2" / "hidden_tests_t1.json")
    sums = []
    for base in (INPUTS, ROOT / "vendor"):
        for p in sorted(base.rglob("*")):
            if p.is_file() and p.name != "SHA256SUMS" and "__pycache__" not in p.parts:
                sums.append(f"{sha256_file(p)}  {p.relative_to(ROOT)}")
    (INPUTS / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    status["n_files_hashed"] = len(sums)
    write_json(RESULTS / "inputs_status.json", status)
    if status["missing"]:
        deviation("D-inputs-missing", f"missing inputs (fallbacks applied where needed): {status['missing']}")
    return status


def dataset_extract(ds_src: Path) -> dict[str, Any]:
    """Uses every dataset of art_j3Rm_lr2nzR6: per-dataset counts (all 10) and the grid/graph-search rows that form
    the novelty-audit corpus (thealgorithms_python, kodcode_algorithmic, xlcost_python naming BFS/DFS/A*/Dijkstra,
    plus LeetCode 1091 shortest path in a binary matrix and the llm_creativity T1/T02 labels as an external prior)."""
    out: dict[str, Any] = {"source_sha256": sha256_file(ds_src) if ds_src.exists() else None}
    if not ds_src.exists():
        deviation("D-dataset-missing", "dependency dataset full_data_out.json not found")
        return out
    data = json.loads(ds_src.read_text())
    rx = __import__("re").compile(r"\b(bfs|dfs|breadth[- _]first|depth[- _]first|a\*|a[_ ]?star|dijkstra|greedy "
                                  r"best|best[- _]first|iterative deepening|ida\*|jump point|bidirectional)\b",
                                  __import__("re").IGNORECASE)
    corpus, counts, creativity = [], {}, collections.Counter()
    for ds in data["datasets"]:
        name = ds["dataset"]
        counts[name] = len(ds["examples"])
        for i, ex in enumerate(ds["examples"]):
            text = str(ex.get("output") or "")
            if name in ("thealgorithms_python", "kodcode_algorithmic", "xlcost_python"):
                names = str(ex.get("metadata_named_algorithms") or "") + " " + str(ex.get("input", ""))[:400]
                if rx.search(names) or rx.search(text[:3000]):
                    if "def " in text and len(text) < 20000:
                        corpus.append({"source": name, "idx": i, "named": trunc_s(names, 200), "code": text})
            elif name == "leetcodedataset" and str(ex.get("metadata_question_id")) in ("1091",):
                corpus.append({"source": name, "idx": i, "named": "LeetCode 1091 shortest path in binary matrix",
                               "code": text})
            elif name == "llm_creativity":
                creativity[str(ex.get("metadata_t02_mode") or ex.get("metadata_strategy") or "na")] += 1
    (INPUTS / "dataset").mkdir(parents=True, exist_ok=True)
    write_jsonl(INPUTS / "dataset" / "corpus_rows.jsonl", corpus)
    out.update({"per_dataset_counts": counts, "n_corpus_rows": len(corpus),
                "corpus_by_source": dict(collections.Counter(c["source"] for c in corpus)),
                "llm_creativity_mode_counts": dict(creativity),
                "usage": {
                    "thealgorithms_python/kodcode_algorithmic/xlcost_python": "novelty-audit known-solution corpus "
                    "(grid/graph-search rows naming a catalogue algorithm) and corpus prior of algorithm names",
                    "leetcodedataset": "problem 1091 (grid shortest path) reference added to the known corpus",
                    "llm_creativity": "external T02 mode distribution (repository labels) reported as context",
                    "mercury/clrs_text/humanevalplus/enamel/concreteness_norms": "counted and recorded; not needed "
                    "by this artifact's analysis (T1 task, judges and harness come from iterations 1-2)"}})
    del data
    return out


def trunc_s(s: str, n: int) -> str:
    return s if len(s) <= n else s[:n]


def carried_rows() -> dict[str, Any]:
    """C9 (Qwen3-8B thinking off, iteration-2 TOP5) and C10 (gemma-3-4b-it, iteration-6 exp31 TOP5)."""
    out: dict[str, Any] = {}
    lab = read_jsonl(INPUTS / "exp9" / "data" / "top5_labelled_rows.jsonl")
    top5 = {"bfs", "dfs", "gbfs", "iddfs", "astar"}
    if lab:
        c = collections.Counter(r["label"] for r in lab)
        cs = sum(1 for r in lab if r.get("passed") and r["label"] not in top5 and r["label"] not in
                 ("no_code", "invalid", "unknown"))
        out["C9"] = {"n": len(lab), "composition": dict(c), "n_correct_survivors": cs,
                     "pass_rate": sum(bool(r.get("passed")) for r in lab) / len(lab), "banned_set": sorted(top5),
                     "banned_share": sum(c[k] for k in top5) / len(lab), "source": "art_IVZc3TWCeE9f TOP5 rows"}
    p = INPUTS / "exp31" / "results" / "top5.json"
    if p.exists():
        t = read_json(p)["top5"]
        out["C10"] = {"n": t["n"], "composition": t["attempted"], "correct": t["correct"],
                      "n_correct_survivors": 0 if t.get("survivor_share", 0) == 0 else None,
                      "pass_rate": t["pass_rate"], "banned_share": t["banned_share"],
                      "banned_set": ["bfs", "dfs", "gbfs", "iddfs", "astar"],
                      "source": "art_zNyBP6zieI5u (ITER6 exp31) results/top5.json"}
    write_json(RESULTS / "carried_rows.json", out)
    return out


# ---------------------------------------------------------------------------------------------- labeller validation
MUTANTS = {
    "bfs_off_by_one_neighbour": '''from collections import deque
def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    q = deque([start]); par = {start: None}
    while q:
        u = q.popleft()
        if u == goal:
            out = []
            while u is not None:
                out.append(u); u = par[u]
            return out[::-1]
        for v in ((u[0] + 2, u[1]), (u[0] - 1, u[1]), (u[0], u[1] + 1), (u[0], u[1] - 1)):
            if 0 <= v[0] < R and 0 <= v[1] < C and grid[v[0]][v[1]] == '.' and v not in par:
                par[v] = u; q.append(v)
    return []
''',
    "bfs_through_walls": '''from collections import deque
def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    q = deque([start]); par = {start: None}
    while q:
        u = q.popleft()
        if u == goal:
            out = []
            while u is not None:
                out.append(u); u = par[u]
            return out[::-1]
        for v in ((u[0] + 1, u[1]), (u[0] - 1, u[1]), (u[0], u[1] + 1), (u[0], u[1] - 1)):
            if 0 <= v[0] < R and 0 <= v[1] < C and v not in par:
                par[v] = u; q.append(v)
    return []
''',
}


def validate_labeller() -> dict[str, Any]:
    from label_tp import evaluate_unique, mechanical, ref_mode
    from labeller_ext.combine import combine

    refs = sorted((INPUTS / "exp9" / "tasks" / "t1_grid" / "references").glob("*.py"))
    gold = [g for g in read_jsonl(INPUTS / "exp9" / "labeller_ext" / "gold_set_iter1.jsonl") if g.get("task") == "t1"]
    codes = [p.read_text() for p in refs] + [g["code"] for g in gold] + list(MUTANTS.values())
    cache = evaluate_unique(codes)
    ref_rows = []
    for p in refs:
        code = p.read_text()
        ev = cache[sha256_text(code)]
        mk = mechanical(code, ev)
        lbl, src = combine(mk["runtime_label"], mk["ast_label"], None, mk["force_judge"])
        exp = ref_mode(p.name)
        ref_rows.append({"file": p.name, "expect": exp, "runtime": mk["runtime_label"], "ast": mk["ast_label"],
                         "combined": lbl, "source": src, "passed": ev["passed"], "n_passed": ev.get("n_passed"),
                         "n_cases": ev.get("n_cases"), "passed_exp2": ev.get("passed_exp2"),
                         "own_class": lbl == exp})
    # gold (iteration-1 label space: astar_gbfs merges A*/greedy; dijkstra = unit Dijkstra; unresolved excluded)
    to_iter1 = {"astar": "astar_gbfs", "gbfs": "astar_gbfs", "dijkstra_unit": "dijkstra"}
    conf: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    gold_rows = []
    for g in gold:
        ev = cache[sha256_text(g["code"])]
        mk = mechanical(g["code"], ev)
        lbl, src = combine(mk["runtime_label"], mk["ast_label"], None, mk["force_judge"])
        mapped = to_iter1.get(lbl, lbl)
        conf[g["adjudicated"]][mapped] += 1
        gold_rows.append({"adjudicated_iter1": g["adjudicated"], "ours": lbl, "ours_mapped": mapped, "source": src,
                          "agree": mapped == g["adjudicated"]})
    scored = [r for r in gold_rows if r["adjudicated_iter1"] != "unresolved"]
    mut_rows = []
    for name, code in MUTANTS.items():
        ev = cache[sha256_text(code)]
        mut_rows.append({"mutant": name, "passed": ev["passed"], "fails_as_expected": not ev["passed"],
                         "error": ev.get("error"), "passed_exp2": ev.get("passed_exp2")})
    res = {"references": ref_rows, "refs_own_class": sum(r["own_class"] for r in ref_rows), "n_refs": len(ref_rows),
           "refs_pass_all": sum(bool(r["passed"]) for r in ref_rows),
           "refs_pass_exp2": sum(bool(r["passed_exp2"]) for r in ref_rows),
           "suite_agreement_on_refs": sum(bool(r["passed"]) == bool(r["passed_exp2"]) for r in ref_rows),
           "n_cases_primary": ref_rows[0]["n_cases"] if ref_rows else None,
           "gold_n_scored": len(scored), "gold_agree": sum(r["agree"] for r in scored),
           "gold_agreement": sum(r["agree"] for r in scored) / max(len(scored), 1),
           "gold_confusion": {k: dict(v) for k, v in conf.items()},
           "gold_note": "mechanical labeller only (no judge) vs iteration-1 adjudicated labels; A*/greedy merged "
                        "and unit Dijkstra = 'dijkstra' in the iteration-1 label space; 'unresolved' excluded",
           "mutants": mut_rows, "mutants_fail": sum(r["fails_as_expected"] for r in mut_rows)}
    write_json(RESULTS / "labeller_validation.json", res)
    logger.info(f"labeller validation: refs own class {res['refs_own_class']}/{res['n_refs']}, pass "
                f"{res['refs_pass_all']}/{res['n_refs']} (exp2 {res['refs_pass_exp2']}), gold "
                f"{res['gold_agree']}/{res['gold_n_scored']}, mutants fail {res['mutants_fail']}/{len(mut_rows)}")
    bad = [r for r in ref_rows if not r["own_class"] or not r["passed"]]
    for r in bad:
        logger.warning(f"reference issue: {r}")
    return res
