#!/usr/bin/env python3
"""S0.4: snapshot every upstream input READ-ONLY into inputs/ and verify the frozen bench against commitment.json.

Bench files are checked with exp11's own rule (bench/common/report.py freeze()): per task, sha256 of every listed
file, the catalogue hash = sha256(canon_json(spec.catalogue)), task_sha256 = sha256(canon_json(files)), and the
combined hash over the sorted tasks. A mismatch aborts (fallback F1). bench/common is not covered by the
commitment, so its sha256s are recorded on copy.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from loguru import logger

from cfg import (BENCH, DATASET_DIR, E7, E8, E9, E12, EXP_DIRS, INPUTS, LABEL_ROOT, RESULTS_DIR, STAGE_A, TASK_DIR,
                 sha256_file, sha256_text, write_json)

EXP8_FILES = ["engine.py", "arms.py", "cfg.py", "behaviour.py", "labelling.py", "method.py", "reproducibility.md",
              "prompts/frozen_prompts.json", "data/samples.jsonl", "results/analysis.json",
              "results/supplementary.json", "results/labeller_recheck.json"]
EXP7_FILES = ["frozen/templates_nouns_padding.json", "data/forced_labelled.jsonl", "data/forced_selected.jsonl"]
EXP11_FILES = ["bench/commitment.json", "bench/__init__.py", "data/samples_forced.jsonl", "data/judge_cache.jsonl",
               "data/samples_pilot.jsonl", "commitments.log"]


def canon_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _copy(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(str(src))
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    else:
        shutil.copy2(src, dst)


def snapshot() -> dict[str, Any]:
    missing = []
    for rel in EXP8_FILES:
        try:
            _copy(EXP_DIRS["exp8"] / rel, E8 / rel)
        except FileNotFoundError as e:
            missing.append(f"exp8/{rel}")
            logger.error(f"missing input {e}")
    _copy(EXP_DIRS["exp8"] / "suite", E8 / "suite")
    for rel in EXP7_FILES:
        try:
            _copy(EXP_DIRS["exp7"] / rel, E7 / rel)
        except FileNotFoundError:
            missing.append(f"exp7/{rel}")
    for rel in EXP11_FILES:
        dst = (INPUTS / rel) if rel.startswith("bench/") else (INPUTS / "exp11" / rel)
        try:
            _copy(EXP_DIRS["exp11"] / rel, dst)
        except FileNotFoundError:
            missing.append(f"exp11/{rel}")
    _copy(EXP_DIRS["exp11"] / "bench" / "common", BENCH / "common")
    for t in STAGE_A:
        _copy(EXP_DIRS["exp11"] / "bench" / TASK_DIR[t], BENCH / TASK_DIR[t])
    try:
        _copy(EXP_DIRS["exp9"] / "data" / "samples.jsonl", E9 / "data" / "samples.jsonl")
    except FileNotFoundError:
        missing.append("exp9/data/samples.jsonl")
    try:
        _copy(EXP_DIRS["exp12"] / "results" / "raw" / "c1_fresh_pool.jsonl", E12 / "results/raw/c1_fresh_pool.jsonl")
    except FileNotFoundError:
        missing.append("exp12/results/raw/c1_fresh_pool.jsonl")
    for rel in ("mini_data_out.json", "preview_data_out.json", "reproducibility.md"):
        try:
            _copy(DATASET_DIR / rel, INPUTS / "dataset" / rel)
        except FileNotFoundError:
            missing.append(f"dataset/{rel}")
    # bench judge cache seeds this run's judge cache (cached by model, task and code hash); spend log starts empty
    jc = INPUTS / "exp11" / "data" / "judge_cache.jsonl"
    if jc.exists() and not (LABEL_ROOT / "data" / "judge_cache.jsonl").exists():
        shutil.copy2(jc, LABEL_ROOT / "data" / "judge_cache.jsonl")
    return {"missing": missing}


def verify_bench() -> dict[str, Any]:
    com = json.loads((BENCH / "commitment.json").read_text())
    per: dict[str, Any] = {}
    mismatches = []
    for t in STAGE_A:
        d = BENCH / TASK_DIR[t]
        want = com["tasks"][t]["files"]
        got = {}
        for f, h in want.items():
            if f == "catalogue":
                got[f] = sha256_text(canon_json(json.loads((d / "spec.json").read_text())["catalogue"]))
            else:
                got[f] = sha256_file(d / f) if (d / f).exists() else None
            if got[f] != h:
                mismatches.append({"task": t, "file": f, "want": h, "got": got[f]})
        tsha = sha256_text(canon_json(got))
        if tsha != com["tasks"][t]["task_sha256"]:
            mismatches.append({"task": t, "file": "task_sha256", "want": com["tasks"][t]["task_sha256"], "got": tsha})
        per[t] = {"n_files": len(want), "task_sha256": tsha, "ok": tsha == com["tasks"][t]["task_sha256"]}
    # the combined hash covers the 12 frozen tasks (R2 was excluded by the 12-task cap)
    combined = sha256_text("".join(com["tasks"][t]["task_sha256"] for t in sorted(com["tasks"])))
    extra = {}
    for t in STAGE_A:  # files outside the commitment that this artifact reads, hashed on copy
        d = BENCH / TASK_DIR[t]
        for f in ("pilot_rows.jsonl", "forced_programs.jsonl", "association.jsonl", "neutral_nouns.json", "gate.json"):
            extra[f"{t}/{f}"] = sha256_file(d / f) if (d / f).exists() else None
    common = {p.name: sha256_file(p) for p in sorted((BENCH / "common").glob("*.py"))}
    others = {}
    for p in sorted(list(E8.rglob("*")) + list(E7.rglob("*")) + list(E9.rglob("*")) + list(E12.rglob("*"))
                    + list((INPUTS / "exp11").rglob("*")) + list((INPUTS / "dataset").rglob("*"))):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
            others[str(p.relative_to(INPUTS))] = sha256_file(p)
    out = {"commitment_combined_sha256": com["combined_sha256"], "recomputed_combined_sha256": combined,
           "combined_ok": combined == com["combined_sha256"], "tasks": per, "mismatches": mismatches,
           "all_ok": not mismatches and combined == com["combined_sha256"],
           "uncommitted_bench_files_sha256": extra, "bench_common_sha256": common, "other_inputs_sha256": others}
    return out


def stage_s0() -> dict[str, Any]:
    snap = snapshot()
    ver = verify_bench()
    ver["missing_inputs"] = snap["missing"]
    write_json(RESULTS_DIR / "input_hashes.json", ver)
    logger.info(f"S0: bench sha256 all_ok={ver['all_ok']} (combined {ver['recomputed_combined_sha256'][:12]}); "
                f"{len(ver['other_inputs_sha256'])} other input files hashed; missing={snap['missing']}")
    if not ver["all_ok"]:
        raise RuntimeError(f"bench commitment mismatch: {ver['mismatches'][:5]} -- fallback F1 applies")
    return ver


if __name__ == "__main__":
    from cfg import setup_logging

    setup_logging("s0")
    stage_s0()
    _ = hashlib  # keep import explicit for readers
