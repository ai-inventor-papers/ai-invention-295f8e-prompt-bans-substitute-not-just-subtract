#!/usr/bin/env python3
"""Copy every earlier-artifact input of step K into ./inputs/ and ./vendor/ (read-only sources) and write
inputs/MANIFEST.tsv (published path, source path relative to its iteration root, size, sha256).

Source roots are relative to this file (no absolute paths); each can be overridden by one environment variable:
  DEP          = declared dependency art_j3Rm_lr2nzR6, published as the sibling folder ../art_j3Rm_lr2nzR6
                 (override: AII_DEP_ART_J3RM)
  ITER6        = iteration 6 of this run, <run>/3_invention_loop/iter_6/gen_art, i.e. ../../iter_6/gen_art in the
                 run tree (override: AII_ITER6_ROOT); holds exp29 = art_lpQalcAXMGr1 and exp30 = art_rMlbrjVB1c__
  ITER2..ITER5 = the earlier run run_aRfWvcSWjssb, <runs>/run_aRfWvcSWjssb/3_invention_loop/iter_<n>/gen_art
                 (override: AII_ITER25_RUN); holds exp27 = art_jR6Pyy3W9xum, exp19 = art_mWn-MQEnNelg, exp23,
                 exp13, exp17, exp18, exp11
The verified copies already ship in inputs/ and vendor/: an item whose destination exists is kept as it is and only
re-hashed, so the script also runs where the source folders are absent. Nothing under vendor/ or inputs/ is edited
after the copy; `--check` re-hashes everything against MANIFEST.tsv.

usage: .venv/bin/python src/setup_inputs.py [--check]
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT.parents[4]
ITER6 = Path(os.environ.get("AII_ITER6_ROOT", str(ROOT.parents[2] / "round-6" / ".")))
ITER25_RUN = Path(os.environ.get("AII_ITER25_RUN", str(RUNS / "run_aRfWvcSWjssb")))
DEP = Path(os.environ.get("AII_DEP_ART_J3RM", str(ROOT.parent / "art_j3Rm_lr2nzR6")))
MANIFEST = ROOT / "inputs" / "MANIFEST.tsv"
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "logs", ".venv", "figures", "states", "boot_cache")


def it(n: int) -> Path:
    return ITER6 if n == 6 else ITER25_RUN / "." / f"iter_{n}" / "."


def tag_of(src: Path) -> str:
    """Source path relative to its symbolic root (ITER<n>/... or DEP/...)."""
    for n in (6, 5, 4, 3, 2):
        try:
            return f"ITER{n}/" + str(src.relative_to(it(n)))
        except ValueError:
            continue
    try:
        return "DEP/" + str(src.relative_to(DEP))
    except ValueError:
        return src.name


E29, E30 = it(6) / "gen_art_experiment_29", it(6) / "gen_art_experiment_30"
E27, E19, E23 = it(5) / "gen_art_experiment_27", it(4) / "gen_art_experiment_19", it(4) / "gen_art_experiment_23"
E13, E17, E18 = it(3) / "gen_art_experiment_13", it(3) / "gen_art_experiment_17", it(3) / "gen_art_experiment_18"
E11, E8, E7 = it(2) / "gen_art_experiment_11", it(2) / "gen_art_experiment_8", it(2) / "gen_art_experiment_7"

# (source, destination relative to ROOT). Directories are copied whole (minus IGNORE).
ITEMS: list[tuple[Path, str]] = [
    # --- (a) exp29 = art_lpQalcAXMGr1 (engine control): vendored exp22/exp19/exp28 code + its own src and anchor rows
    (E29 / "vendor" / "exp22", "vendor/exp22"),
    (E29 / "vendor" / "exp19", "vendor/exp19"),
    (E29 / "vendor" / "exp28", "vendor/exp28"),
    (E29 / "vendor" / "SHA256SUMS", "vendor/SHA256SUMS_exp29"),
    (E29 / "src", "inputs/exp29/src"),
    (E29 / "data" / "raw" / "raw_d.jsonl", "inputs/exp29/data/raw/raw_d.jsonl"),
    (E29 / "data" / "labels.jsonl", "inputs/exp29/data/labels.jsonl"),
    (E29 / "data" / "samples.jsonl", "inputs/exp29/data/samples.jsonl"),
    (E29 / "results" / "pn.json", "inputs/exp29/results/pn.json"),
    (E29 / "results" / "known_solutions.json", "inputs/exp29/results/known_solutions.json"),
    (E29 / "results" / "verdict.json", "inputs/exp29/results/verdict.json"),
    (E29 / "results" / "unit_tests_b.json", "inputs/exp29/results/unit_tests_b.json"),
    (E29 / "inputs" / "exp22" / "units.json", "inputs/exp22/units.json"),
    (E29 / "inputs" / "exp22" / "input_hashes.json", "inputs/exp22/input_hashes.json"),
    (E29 / "inputs" / "exp19" / "samples.jsonl", "inputs/exp29/inputs/exp19/samples.jsonl"),
    # --- (b) exp27 = art_jR6Pyy3W9xum (iteration-5 plan noise and prices): code (vendored to run its knob paths)
    (E27 / "src", "vendor/exp27/src"),
    (E27 / "prompts", "vendor/exp27/prompts"),
    (E27 / "inputs", "vendor/exp27/inputs"),
    (E27 / "predictions" / "model_revisions.json", "vendor/exp27/predictions/model_revisions.json"),
    (E27 / "predictions" / "precision_rule.json", "vendor/exp27/predictions/precision_rule.json"),
    (E27 / "predictions" / "commit1.json", "inputs/exp27/predictions/commit1.json"),
    (E27 / "results" / "cells.json", "inputs/exp27/results/cells.json"),
    (E27 / "results" / "prices.json", "inputs/exp27/results/prices.json"),
    (E27 / "results" / "unit_ratio.json", "inputs/exp27/results/unit_ratio.json"),
    (E27 / "results" / "engine_check.json", "inputs/exp27/results/engine_check.json"),
    (E27 / "results" / "claim_c.json", "inputs/exp27/results/claim_c.json"),
    (E27 / "results" / "knob_table.json", "inputs/exp27/results/knob_table.json"),
    (E27 / "results" / "defaults.json", "inputs/exp27/results/defaults.json"),
    (E27 / "results" / "input_hashes.json", "inputs/exp27/results/input_hashes.json"),
    (E27 / "results" / "labeller_recheck.json", "inputs/exp27/results/labeller_recheck.json"),
    (E27 / "data" / "samples_raw.jsonl", "inputs/exp27/data/samples_raw.jsonl"),
    (E27 / "data" / "labels.jsonl", "inputs/exp27/data/labels.jsonl"),
    (E27 / "data" / "base_intents.jsonl", "inputs/exp27/data/base_intents.jsonl"),
    (E27 / "data" / "realised.jsonl", "inputs/exp27/data/realised.jsonl"),
    (E27 / "data" / "stages.jsonl", "inputs/exp27/data/stages.jsonl"),
    # --- (c) exp19 = art_mWn-MQEnNelg (FP8 PN at U_abs): the S3 prior
    (E19 / "data" / "samples.jsonl", "inputs/exp19/data/samples.jsonl"),
    (E19 / "results" / "prices.json", "inputs/exp19/results/prices.json"),
    # --- (d) unit sources (originals; the vendored exp22 inputs hold copies that are hash-checked against these)
    (E13 / "results" / "tensors" / "norms_T03.npz", "inputs/exp13/results/tensors/norms_T03.npz"),
    (E13 / "results" / "tensors" / "norms_T05.npz", "inputs/exp13/results/tensors/norms_T05.npz"),
    (E13 / "results" / "tensors" / "norms_T10.npz", "inputs/exp13/results/tensors/norms_T10.npz"),
    (E17 / "directions" / "norms_T1.npy", "inputs/exp17/directions/norms_T1.npy"),
    (E17 / "directions" / "norms_T2.npy", "inputs/exp17/directions/norms_T2.npy"),
    (E23 / "results" / "qwen_ratio.json", "inputs/exp23/results/qwen_ratio.json"),
    # --- (e) exp30 = art_rMlbrjVB1c__ (hooks, labeller, positions, twin labels)
    (E30 / "src" / "engine6.py", "inputs/exp30/src/engine6.py"),
    (E30 / "src" / "hooks.py", "inputs/exp30/src/hooks.py"),
    (E30 / "src" / "sampling_v4.py", "inputs/exp30/src/sampling_v4.py"),
    (E30 / "src" / "label6.py", "inputs/exp30/src/label6.py"),
    (E30 / "src" / "regate_rules.py", "inputs/exp30/src/regate_rules.py"),
    (E30 / "src" / "prompts6.py", "inputs/exp30/src/prompts6.py"),
    (E30 / "prompts" / "positions.json", "inputs/exp30/prompts/positions.json"),
    (E30 / "data" / "labels.jsonl", "inputs/exp30/data/labels.jsonl"),
    # --- (f) bench (exp11) and novelty-audit summaries (exp18)
    (E11 / "bench" / "commitment.json", "inputs/exp11/bench/commitment.json"),
    (E18 / "results" / "known_solutions_summary.json", "inputs/exp18/results/known_solutions_summary.json"),
    # --- declared dependency art_j3Rm_lr2nzR6 (dataset)
    (DEP / "full_data_out.json", "inputs/dep_art_j3Rm/full_data_out.json"),
    (DEP / "mini_data_out.json", "inputs/dep_art_j3Rm/mini_data_out.json"),
    (DEP / "preview_data_out.json", "inputs/dep_art_j3Rm/preview_data_out.json"),
    (DEP / "data.py", "inputs/dep_art_j3Rm/data.py"),
    (DEP / "reproducibility.md", "inputs/dep_art_j3Rm/reproducibility.md"),
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_all() -> list[tuple[str, str, int, str]]:
    rows = []
    missing = []
    for src, dst in ITEMS:
        d = ROOT / dst
        if not src.exists() and not d.exists():
            missing.append(tag_of(src))
            logger.warning(f"MISSING input {tag_of(src)} -> {dst} (fallback applies)")
            continue
        d.parent.mkdir(parents=True, exist_ok=True)
        if d.is_dir() or (not d.exists() and src.is_dir()):
            if not d.exists():
                shutil.copytree(src, d, ignore=IGNORE)
            files = [p for p in sorted(d.rglob("*")) if p.is_file() and "__pycache__" not in p.parts]
            for p in files:
                rel = p.relative_to(d)
                rows.append((str(p.relative_to(ROOT)), tag_of(src / rel), p.stat().st_size, sha256_file(p)))
        else:
            if not d.exists():
                shutil.copy2(src, d)
            rows.append((dst, tag_of(src), d.stat().st_size, sha256_file(d)))
        logger.info(f"{'copied' if src.exists() else 'kept existing copy of'} {tag_of(src)} -> {dst}")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST, "w") as f:
        f.write("path\tsource\tsize\tsha256\n")
        for r in rows:
            f.write("\t".join(str(x) for x in r) + "\n")
        for m in missing:
            f.write(f"MISSING\t{m}\t0\t-\n")
    logger.info(f"MANIFEST: {len(rows)} files, {len(missing)} missing")
    return rows


def check() -> int:
    bad = 0
    n = 0
    for line in MANIFEST.read_text().splitlines()[1:]:
        path, src, size, h = line.split("\t")
        if path == "MISSING":
            continue
        n += 1
        p = ROOT / path
        if not p.exists() or sha256_file(p) != h:
            bad += 1
            logger.error(f"changed or missing: {path}")
    logger.info(f"manifest check: {n} files, {bad} changed")
    return bad


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    (ROOT / "logs").mkdir(exist_ok=True)
    logger.add(str(ROOT / "logs" / "setup_inputs.log"), rotation="30 MB", level="DEBUG")
    if "--check" in sys.argv:
        sys.exit(1 if check() else 0)
    copy_all()
