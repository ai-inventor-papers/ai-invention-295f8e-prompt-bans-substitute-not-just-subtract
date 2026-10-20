#!/usr/bin/env python3
"""S0.1-S0.2: copy the frozen exp11 bench and the exp7/exp8 sources into inputs/, verify every file hash listed in
bench/commitment.json (abort on mismatch), record provenance hashes of the non-committed bench files as the first
commitments.log entries, write results/env.json, and check the bench's hidden tests against the iteration-1
dependency dataset (provenance only)."""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
from pathlib import Path

from loguru import logger

from common import (BENCH, COMMIT_LOG, DATA, DEP_DATASET, EXP7, EXP8, EXP11, INPUTS, MODEL_ID, RESULTS, REVISION,
                    TASK_ORDER, bench_import, canon, model_path, read_jsonl, sha256_file, utc_now, write_json)

PROVENANCE_FILES = ["pilot_rows.jsonl", "forced_programs.jsonl", "association.jsonl", "neutral_nouns.json",
                    "frlp_sets.json", "frlp_baseline.jsonl"]


def copy_inputs() -> None:
    src = EXP11 / "bench"
    BENCH.mkdir(parents=True, exist_ok=True)
    bench_import()
    for name in ["__init__.py", "commitment.json"]:
        shutil.copy2(src / name, BENCH / name)
    if (BENCH / "common").exists():
        shutil.rmtree(BENCH / "common")
    shutil.copytree(src / "common", BENCH / "common", ignore=shutil.ignore_patterns("__pycache__"))
    from bench.common.catalogue import TASKS  # noqa: E402  (import after copy)

    for t in TASK_ORDER:
        tid = TASKS[t]["task_id"]
        if (BENCH / tid).exists():
            shutil.rmtree(BENCH / tid)
        shutil.copytree(src / tid, BENCH / tid, ignore=shutil.ignore_patterns("__pycache__"))
    (INPUTS / "exp7").mkdir(exist_ok=True)
    (INPUTS / "exp8").mkdir(exist_ok=True)
    (INPUTS / "exp11").mkdir(exist_ok=True)
    shutil.copy2(EXP7 / "frozen" / "templates_nouns_padding.json", INPUTS / "exp7" / "templates_nouns_padding.json")
    for f in ["engine.py", "arms.py", "cfg.py"]:
        shutil.copy2(EXP8 / f, INPUTS / "exp8" / f)
    shutil.copy2(EXP11 / "data" / "frlp_cells.jsonl", INPUTS / "exp11" / "frlp_cells.jsonl")
    shutil.copy2(EXP11 / "commitments.log", INPUTS / "exp11" / "commitments.log")
    # judge answers are cached by (judge model, task, sha256 of scrubbed code): reusing exp11's cache is exact
    DATA.mkdir(parents=True, exist_ok=True)
    jc = DATA / "judge_cache.jsonl"
    if not jc.exists():
        shutil.copy2(EXP11 / "data" / "judge_cache.jsonl", jc)
    logger.info("inputs copied")


def verify_commitment() -> dict:
    bench_import()
    from bench.common.catalogue import TASKS

    com = json.loads((BENCH / "commitment.json").read_text())
    report = {"checked": 0, "mismatch": [], "not_files": [], "tasks": {}}
    for t in TASK_ORDER:
        files = com["tasks"][t]["files"]
        tdir = BENCH / TASKS[t]["task_id"]
        ok = 0
        for name, h in files.items():
            p = tdir / name
            if not p.exists():
                report["not_files"].append(f"{t}:{name}")
                continue
            report["checked"] += 1
            if sha256_file(p) != h:
                report["mismatch"].append(f"{t}:{name}")
            else:
                ok += 1
        report["tasks"][t] = {"n_files_ok": ok, "n_listed": len(files)}
    # files listed that are not on disk must be non-file digests (the catalogue card); check that and nothing else
    bad_missing = [x for x in report["not_files"] if not x.endswith(":catalogue")]
    if report["mismatch"] or bad_missing:
        raise RuntimeError(f"bench commitment check FAILED: mismatch={report['mismatch']} missing={bad_missing}")
    logger.info(f"bench commitment verified: {report['checked']} files, 0 mismatches "
                f"({len(report['not_files'])} non-file catalogue digests skipped)")
    return report


def provenance_commits() -> list[dict]:
    """First commitments.log entries: sha256 of the bench files that commitment.json does not cover."""
    bench_import()
    from bench.common.catalogue import TASKS
    from bench.common.commit import commit, sha256_text

    if COMMIT_LOG.exists() and COMMIT_LOG.read_text().strip():
        logger.info("commitments.log already has entries; provenance not re-committed")
        return []
    files = {}
    for t in TASK_ORDER:
        tdir = BENCH / TASKS[t]["task_id"]
        for name in PROVENANCE_FILES:
            files[f"{t}/{name}"] = sha256_file(tdir / name)
    files["exp11/frlp_cells.jsonl"] = sha256_file(INPUTS / "exp11" / "frlp_cells.jsonl")
    files["exp7/templates_nouns_padding.json"] = sha256_file(INPUTS / "exp7" / "templates_nouns_padding.json")
    for f in ["engine.py", "arms.py", "cfg.py"]:
        files[f"exp8/{f}"] = sha256_file(INPUTS / "exp8" / f)
    files["bench/commitment.json"] = sha256_file(BENCH / "commitment.json")
    manifest = INPUTS / "provenance_manifest.json"
    manifest.write_text(json.dumps(files, indent=1, sort_keys=True))
    rec = commit(COMMIT_LOG, "provenance", sha256_text(canon(files)),
                 {"n_files": len(files), "manifest": "inputs/provenance_manifest.json", "utc": utc_now()})
    logger.info(f"provenance committed: {rec['sha256'][:16]} ({len(files)} files)")
    return [rec]


def env_json() -> dict:
    import importlib.metadata as md

    vers = {}
    for pkg in ["vllm", "torch", "transformers", "numpy", "scipy", "statsmodels", "zss", "apted", "openai"]:
        try:
            vers[pkg] = md.version(pkg)
        except md.PackageNotFoundError:
            vers[pkg] = None
    mp = Path(model_path())
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
                         capture_output=True, text=True).stdout.strip()
    env = {"utc": utc_now(), "python": platform.python_version(), "platform": platform.platform(), "gpu": gpu,
           "model": MODEL_ID, "revision": REVISION, "snapshot_dir_basename": mp.name,
           "safetensors_index_sha256": sha256_file(mp / "model.safetensors.index.json"),
           "config_sha256": sha256_file(mp / "config.json"),
           "generation_config": json.loads((mp / "generation_config.json").read_text()),
           "packages": vers, "c_compiler": shutil.which("gcc") or shutil.which("cc"),
           "sandbox_python": shutil.which("python3.12")}
    write_json(RESULTS / "env.json", env)
    logger.info(f"env: {env['gpu']} python {env['python']} vllm {vers['vllm']} torch {vers['torch']}")
    return env


def dependency_provenance() -> dict:
    """The bench's 'parsed' hidden tests come from the iteration-1 dataset's LeetCode cases (case ids
    leetcodedataset:<qid>:<idx>); check every such id exists there with the same expected value."""
    bench_import()
    from bench.common.catalogue import TASKS

    full = DEP_DATASET / "full_data_out.json"
    if not full.exists():
        return {"available": False}
    d = json.loads(full.read_text())
    cases = {}
    n_examples = {}
    for ds in d["datasets"]:
        n_examples[ds["dataset"]] = len(ds["examples"])
        if ds["dataset"] != "leetcodedataset":
            continue
        for e in ds["examples"]:
            if not e.get("metadata_bench_task"):
                continue
            try:
                tc = json.loads(e.get("metadata_test_cases_json") or "[]")
            except json.JSONDecodeError:
                continue
            for c in tc:
                cid = c.get("case_id")
                if cid:
                    cases[cid] = c
    del d
    rep = {"available": True, "dataset_sizes": n_examples, "tasks": {}}
    for t in TASK_ORDER:
        rows = read_jsonl(BENCH / TASKS[t]["task_id"] / "tests.jsonl")
        parsed = [r for r in rows if str(r.get("case_id", "")).startswith("leetcodedataset:")]
        found = [r for r in parsed if r["case_id"] in cases]
        same = sum(1 for r in found if json.dumps(cases[r["case_id"]].get("expected"), sort_keys=True)
                   == json.dumps(r.get("expected"), sort_keys=True))
        rep["tasks"][t] = {"n_tests": len(rows), "n_parsed_from_dependency": len(parsed), "n_ids_found": len(found),
                           "n_expected_identical": same}
    write_json(RESULTS / "dependency_provenance.json", rep)
    logger.info("dependency provenance: " + ", ".join(f"{t}:{v['n_ids_found']}/{v['n_parsed_from_dependency']}"
                                                       for t, v in rep["tasks"].items()))
    return rep


def main() -> None:
    copy_inputs()
    rep = verify_commitment()
    write_json(RESULTS / "bench_verification.json", rep)
    provenance_commits()
    env_json()
    dependency_provenance()


if __name__ == "__main__":
    from common import setup_logging

    setup_logging("s0_setup")
    main()
