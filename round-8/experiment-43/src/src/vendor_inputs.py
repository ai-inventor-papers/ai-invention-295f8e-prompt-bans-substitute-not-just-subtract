#!/usr/bin/env python3
"""S0.4: copy every prior-artifact file this pipeline reads into inputs/src_<name>/<relative path> and write
inputs/SHA256SUMS (plus the sha256 of the 96 MB dependency file, which is read in place and not copied).
cfg8.SRCS falls back to these copies when the run-volume paths do not exist (e.g. in a fresh clone)."""

from __future__ import annotations

import shutil
from pathlib import Path

from cfg8 import INPUTS, SRCS, sha256_file

FILES = {
    "exp35": ["prompts/prompts7.jsonl", "data/samples_raw.jsonl", "data/labels.jsonl", "predictions/collapsed_raw.json",
              "results/test2.json", "results/forks.json", "results/predictions_view.json", "src/predict.py",
              "src/replay.py", "src/forks.py", "src/opening_cls.py", "src/label7.py", "src/commit7.py", "src/cfg7.py"],
    "exp31": ["data/raw_s3.jsonl", "data/labels.jsonl", "data/prompts_fed.jsonl", "results/natural_split.json"],
    "exp38": ["src/engine.py", "results/g3_predictions.json"],
    "exp10": ["canon/prompts/conditions.json", "data/raw_gen.jsonl", "results/collapse.json"],
    "exp11": ["data/samples_llama_pilot.jsonl", "bench/commitment.json"],
    "exp24": ["method_out.json"],
    "exp29": ["results/known_solutions.json"],
}


def main() -> None:
    lines = []
    for k, rels in FILES.items():
        for rel in rels:
            src = SRCS[k] / rel
            dst = INPUTS / f"src_{k}" / rel
            if not src.exists():
                print("MISSING", src)
                continue
            if src.resolve() != dst.resolve():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            lines.append(f"{sha256_file(dst)}  {dst.relative_to(INPUTS)}")
    for p in sorted(INPUTS.rglob("*")):
        if p.is_file() and not p.name.startswith("SHA256SUMS") and "src_" not in str(p.relative_to(INPUTS)).split("/")[0]:
            lines.append(f"{sha256_file(p)}  {p.relative_to(INPUTS)}")
    dep = SRCS["dep"] / "full_data_out.json"
    if dep.exists():
        lines.append(f"{sha256_file(dep)}  (read in place) art_j3Rm_lr2nzR6/full_data_out.json")
    (INPUTS / "SHA256SUMS").write_text("\n".join(lines) + "\n")
    print(len(lines), "files hashed")


if __name__ == "__main__":
    main()
