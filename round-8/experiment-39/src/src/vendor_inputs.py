#!/usr/bin/env python3
"""Stage -1 (setup): copy every prior input this artifact reads into inputs/ (read-only copies, never written again)
and record sha256 of source and copy in inputs/input_hashes.json and inputs/SHA256SUMS.

Sources are the iteration-6/7 artifact workspaces of this run (shared protocol v8: only the dataset is declared as a
dependency; every other input is read by path, copied, hashed). The absolute source root is taken from the
environment variable AII_RUN_LOOP (default: this run's 3_invention_loop folder, derived from the workspace location)
and is NOT written into any published file: hashes are keyed by the relative source path.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "inputs"
LOOP = Path(os.environ.get("AII_RUN_LOOP") or ROOT.parents[2])     # .../3_invention_loop

X35 = "round-7/experiment-35/src"
X34 = "round-7/experiment-34/src"
X38 = "round-7/experiment-38/src"
X36 = "round-7/experiment-36/src"
X37 = "round-7/experiment-37/src"
X29 = "round-6/experiment-29/src"

# (relative source under LOOP, destination under inputs/)
COPIES: list[tuple[str, str]] = [
    # exp35's own vendored iteration-2..6 inputs (units, labellers, bench, iteration-6 engine), same folder names
    (f"{X35}/inputs/iter2_exp11", "iter2_exp11"),
    (f"{X35}/inputs/iter2_exp7", "iter2_exp7"),
    (f"{X35}/inputs/iter3_exp18", "iter3_exp18"),
    (f"{X35}/inputs/iter5_exp25", "iter5_exp25"),
    (f"{X35}/inputs/iter5_exp26", "iter5_exp26"),
    (f"{X35}/inputs/iter6_exp30", "iter6_exp30"),
    (f"{X35}/inputs/dep_extract.json", "exp35/dep_extract.json"),
    # exp35 code, prompts, results, raw rows
    (f"{X35}/src", "exp35/src"),
    (f"{X35}/prompts", "exp35/prompts"),
    (f"{X35}/results/forks.json", "exp35/results/forks.json"),
    (f"{X35}/results/test3.json", "exp35/results/test3.json"),
    (f"{X35}/results/predictions_view.json", "exp35/results/predictions_view.json"),
    (f"{X35}/results/calibration.json", "exp35/results/calibration.json"),
    (f"{X35}/results/opening_classifier.json", "exp35/results/opening_classifier.json"),
    (f"{X35}/results/posthoc.json", "exp35/results/posthoc.json"),
    (f"{X35}/results/s4b.json", "exp35/results/s4b.json"),
    (f"{X35}/results/twins.json", "exp35/results/twins.json"),
    (f"{X35}/results/engine_check.json", "exp35/results/engine_check.json"),
    (f"{X35}/results/table_1ac.json", "exp35/results/table_1ac.json"),
    (f"{X35}/predictions/collapsed_raw.json", "exp35/predictions/collapsed_raw.json"),
    (f"{X35}/predictions/commit1_forks.json", "exp35/predictions/commit1_forks.json"),
    (f"{X35}/data/samples_raw.jsonl", "exp35/data/samples_raw.jsonl"),
    (f"{X35}/data/labels.jsonl", "exp35/data/labels.jsonl"),
    (f"{X35}/data/collapsed_conts.jsonl", "exp35/data/collapsed_conts.jsonl"),
    (f"{X35}/data/collapsed_conts_labels.jsonl", "exp35/data/collapsed_conts_labels.jsonl"),
    # exp34 (T10 forks, forced-token cells, T10 twins)
    (f"{X34}/results/forks.json", "exp34/results/forks.json"),
    (f"{X34}/results/force_token.json", "exp34/results/force_token.json"),
    (f"{X34}/results/fork_token_probs.json", "exp34/results/fork_token_probs.json"),
    (f"{X34}/data/samples_raw.jsonl", "exp34/data/samples_raw.jsonl"),
    (f"{X34}/data/labels.jsonl", "exp34/data/labels.jsonl"),
    (f"{X34}/data/samples_raw_force.jsonl", "exp34/data/samples_raw_force.jsonl"),
    (f"{X34}/data/labels_force.jsonl", "exp34/data/labels_force.jsonl"),
    (f"{X34}/src/fork7.py", "exp34/src/fork7.py"),
    # exp38 (Gemma engine, prompts via the iteration-6 Gemma artifact, g3 calibration and predictions)
    (f"{X38}/src", "exp38/src"),
    (f"{X38}/inputs/iter6_gemma", "exp38/inputs/iter6_gemma"),
    (f"{X38}/results/g3_cal.json", "exp38/results/g3_cal.json"),
    (f"{X38}/results/g3_predictions.json", "exp38/results/g3_predictions.json"),
    (f"{X38}/results/g3_sweep.json", "exp38/results/g3_sweep.json"),
    (f"{X38}/results/engine_check.json", "exp38/results/engine_check.json"),
    (f"{X38}/data/raw_engine.jsonl", "exp38/data/raw_engine.jsonl"),
    (f"{X38}/data/raw_g3.jsonl", "exp38/data/raw_g3.jsonl"),
    (f"{X38}/data/raw_g3cal.jsonl", "exp38/data/raw_g3cal.jsonl"),
    (f"{X38}/data/labels.jsonl", "exp38/data/labels.jsonl"),
    # comparator rows and novelty/HR comparison sets
    (f"{X36}/data/samples.jsonl", "exp36/data/samples.jsonl"),
    (f"{X36}/data/labels.jsonl", "exp36/data/labels.jsonl"),
    (f"{X37}/results/program_classes.json", "exp37/results/program_classes.json"),
    (f"{X37}/results/manual_reads.jsonl", "exp37/results/manual_reads.jsonl"),
    (f"{X29}/results/known_solutions.json", "exp29/results/known_solutions.json"),
]
SKIP_DIRS = {"__pycache__", ".venv", "cache", "logs"}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def files_of(p: Path) -> list[Path]:
    if p.is_file():
        return [p]
    out = []
    for q in sorted(p.rglob("*")):
        if q.is_file() and not any(part in SKIP_DIRS for part in q.relative_to(p).parts):
            out.append(q)
    return out


def main() -> int:
    INPUTS.mkdir(parents=True, exist_ok=True)
    report: dict = {"missing": [], "copied": {}, "mismatch": []}
    sums: list[str] = []
    for rel, dst in COPIES:
        src = LOOP / rel
        if not src.exists():
            report["missing"].append(rel)
            print(f"MISSING {rel}", flush=True)
            continue
        for f in files_of(src):
            sub = f.relative_to(src) if src.is_dir() else Path("")
            out = INPUTS / dst / sub if src.is_dir() else INPUTS / dst
            out.parent.mkdir(parents=True, exist_ok=True)
            if not out.exists() or out.stat().st_size != f.stat().st_size:
                shutil.copy2(f, out)
            hs, hc = sha(f), sha(out)
            key = str(out.relative_to(INPUTS))
            report["copied"][key] = {"source": f"{rel}/{sub}" if src.is_dir() else rel, "sha256": hc,
                                     "source_sha256": hs, "match": hs == hc}
            if hs != hc:
                report["mismatch"].append(key)
            sums.append(f"{hc}  {key}")
    # bench commitment check (exp11 bench sha256 list, if present)
    (INPUTS / "input_hashes.json").write_text(json.dumps(report, indent=1))
    (INPUTS / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    print(f"copied {len(report['copied'])} files; missing {len(report['missing'])}; mismatch {len(report['mismatch'])}")
    return 0 if not report["mismatch"] else 1


if __name__ == "__main__":
    sys.exit(main())
