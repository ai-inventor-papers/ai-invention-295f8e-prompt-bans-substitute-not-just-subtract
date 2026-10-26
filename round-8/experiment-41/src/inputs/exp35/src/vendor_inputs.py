#!/usr/bin/env python3
"""Step A1: vendor every prior-artifact input this pipeline reads into inputs/<origin>/ (read-only sources, copied
once) and write the sha256 of every copied file to inputs/input_hashes.json (+ inputs/SHA256SUMS).

Origins (absolute run layout of the original server, overridable with AII_RUNS_DIR):
  iter6_exp30  run_0oWBKrKEGsmU iter 6 gen_art_experiment_30 (bf16 engine, hooks, prompts, collapsed-task rows,
               the exp8 suite and exp11 bench labellers it vendored)
  iter6_exp29  run_0oWBKrKEGsmU iter 6 gen_art_experiment_29 (sampler6/escape/engines, known_solutions.json)
  iter5_exp25  run_aRfWvcSWjssb iter 5 gen_art_experiment_25 (A3 unit: newbench/A3 + common labeller, prompts, labels)
  iter5_exp26  run_aRfWvcSWjssb iter 5 gen_art_experiment_26 (B3/B6 units, unit labeller, prompts, labels)
  iter4_exp22  run_aRfWvcSWjssb iter 4 gen_art_experiment_22 (rand_9101..9108 directions, units() rule)
  iter3_exp18  run_aRfWvcSWjssb iter 3 gen_art_experiment_18 (known_solutions_summary.json)
  iter2_exp7   run_aRfWvcSWjssb iter 2 gen_art_experiment_7 (frozen W1-W5 frames)
  iter2_exp11  run_aRfWvcSWjssb iter 2 gen_art_experiment_11 (bench commitment.json + forced programs of T03/T10)
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = Path(os.environ.get("AII_RUNS_DIR", str(ROOT.parents[4])))   # <runs>/<run>/3_invention_loop/iter_7/gen_art/<this>
R6 = RUNS / "run_0oWBKrKEGsmU" / "." / "round-6" / "."
RA = RUNS / "run_aRfWvcSWjssb" / "."
E30 = R6 / "experiment-30/src"
E29 = R6 / "experiment-29/src"
E25 = RA / "round-5" / "." / "experiment-25/src"
E26 = RA / "round-5" / "." / "experiment-26/src"
E22 = RA / "round-4" / "." / "experiment-22/src"
E18 = RA / "round-3" / "." / "experiment-18/src"
E7 = RA / "round-2" / "." / "experiment-7/src"
E11 = RA / "round-2" / "." / "experiment-11/src"

# (source, destination relative to inputs/, required)
ITEMS: list[tuple[Path, str, bool]] = [
    (E30 / "src", "iter6_exp30/src", True),
    (E30 / "prompts", "iter6_exp30/prompts", True),
    (E30 / "data" / "samples_raw.jsonl", "iter6_exp30/data/samples_raw.jsonl", True),
    (E30 / "data" / "labels.jsonl", "iter6_exp30/data/labels.jsonl", True),
    (E30 / "inputs" / "exp8", "iter6_exp30/inputs/exp8", True),
    (E30 / "inputs" / "exp11", "iter6_exp30/inputs/exp11", True),
    (E30 / "inputs" / "exp23", "iter6_exp30/inputs/exp23", False),
    (E30 / "results" / "engine_check.json", "iter6_exp30/results/engine_check.json", False),
    (E30 / "predictions" / "hardware.json", "iter6_exp30/predictions/hardware.json", False),
    (E29 / "src" / "sampler6.py", "iter6_exp29/src/sampler6.py", False),
    (E29 / "src" / "escape.py", "iter6_exp29/src/escape.py", False),
    (E29 / "src" / "engines.py", "iter6_exp29/src/engines.py", False),
    (E29 / "results" / "known_solutions.json", "iter6_exp29/results/known_solutions.json", True),
    (E25 / "newbench" / "__init__.py", "iter5_exp25/newbench/__init__.py", True),
    (E25 / "newbench" / "common", "iter5_exp25/newbench/common", True),
    (E25 / "newbench" / "A3_trapping_rain_water", "iter5_exp25/newbench/A3_trapping_rain_water", True),
    (E25 / "data" / "labels" / "A3.jsonl", "iter5_exp25/data/labels/A3.jsonl", True),
    (E25 / "data" / "prompts_new.jsonl", "iter5_exp25/data/prompts_new.jsonl", True),
    (E26 / "src", "iter5_exp26/src", True),
    (E26 / "units" / "B3", "iter5_exp26/units/B3", True),
    (E26 / "units" / "B6", "iter5_exp26/units/B6", True),
    (E26 / "data" / "prompts.jsonl", "iter5_exp26/data/prompts.jsonl", True),
    (E26 / "data" / "labels.jsonl", "iter5_exp26/data/labels.jsonl", True),
    (E22 / "directions", "iter4_exp22/directions", True),
    (E22 / "src" / "gpu_phase1.py", "iter4_exp22/src/gpu_phase1.py", False),
    (E22 / "src" / "ctx4.py", "iter4_exp22/src/ctx4.py", False),
    (E18 / "results" / "known_solutions_summary.json", "iter3_exp18/results/known_solutions_summary.json", False),
    (E7 / "frozen" / "templates_nouns_padding.json", "iter2_exp7/frozen/templates_nouns_padding.json", False),
    (E11 / "bench" / "commitment.json", "iter2_exp11/bench/commitment.json", False),
    (E11 / "bench" / "T03_kth_smallest" / "forced_programs.jsonl", "iter2_exp11/bench/T03_forced_programs.jsonl",
     False),
    (E11 / "bench" / "T10_connected_components" / "forced_programs.jsonl",
     "iter2_exp11/bench/T10_forced_programs.jsonl", False),
]
SKIP_DIRS = {"__pycache__", ".venv", "cache", "states", "mutants"}
DIR_FILTER = {"directions": lambda p: p.name.startswith("rand_91") and p.suffix == ".npy"}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_item(src: Path, dst: Path, hashes: dict[str, str]) -> int:
    n = 0
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(src, dst)
        hashes[str(dst.relative_to(ROOT / "inputs"))] = sha256_file(dst)
        return 1
    flt = DIR_FILTER.get(src.name)
    for p in sorted(src.rglob("*")):
        if any(part in SKIP_DIRS for part in p.relative_to(src).parts) or not p.is_file():
            continue
        if flt is not None and not flt(p):
            continue
        n += copy_item(p, dst / p.relative_to(src), hashes)
    return n


def main() -> int:
    hashes: dict[str, str] = {}
    report = {"items": [], "missing_required": [], "missing_optional": []}
    for src, rel, req in ITEMS:
        if not src.exists():
            (report["missing_required"] if req else report["missing_optional"]).append(str(src))
            continue
        n = copy_item(src, ROOT / "inputs" / rel, hashes)
        report["items"].append({"source": str(src).replace(str(RUNS), "<runs>"), "dest": f"inputs/{rel}", "files": n})
    # bench files verified against the exp11 commitment (the iteration-6 copy of the bench)
    com = ROOT / "inputs" / "iter2_exp11" / "bench" / "commitment.json"
    bench = ROOT / "inputs" / "iter6_exp30" / "inputs" / "exp11" / "bench"
    if com.exists() and bench.exists():
        c = json.loads(com.read_text())
        files = c.get("files") or c.get("sha256") or {}
        checked = bad = 0
        if isinstance(files, dict):
            for rel, h in files.items():
                p = bench / rel
                if p.exists() and isinstance(h, str) and len(h) == 64:
                    checked += 1
                    bad += sha256_file(p) != h
        report["bench_commitment_check"] = {"checked": checked, "mismatch": bad}
    (ROOT / "inputs" / "input_hashes.json").write_text(json.dumps(hashes, indent=1, sort_keys=True))
    (ROOT / "inputs" / "SHA256SUMS").write_text("".join(f"{h}  {k}\n" for k, h in sorted(hashes.items())))
    (ROOT / "inputs" / "vendor_report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({k: (v if k != "items" else len(v)) for k, v in report.items()}, indent=1))
    print(f"{len(hashes)} files hashed")
    return 1 if report["missing_required"] else 0


if __name__ == "__main__":
    sys.exit(main())
