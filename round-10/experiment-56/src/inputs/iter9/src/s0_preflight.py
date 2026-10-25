#!/usr/bin/env python3
"""S0.1-0.2: hardware record, then copy every read-only input into vendor/<artifact id>/<relpath> with sha256
(vendor/inputs.json). Missing files are listed (the fallback table in the README applies)."""

from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path

from loguru import logger

from cfg9 import (PRED_DIR, SRCS, VENDOR, container_ram_gb, detect_cpus, setup_logging, sha256_file, utc_now,
                  write_json)

# (artifact id, relative path) — directories are copied recursively
WANT: list[tuple[str, str]] = [
    ("art_18XvfcJJZi1O", "src"),
    ("art_18XvfcJJZi1O", "results/summary.json"),
    ("art_18XvfcJJZi1O", "results/contrasts.json"),
    ("art_18XvfcJJZi1O", "results/nouns.json"),
    ("art_18XvfcJJZi1O", "results/selection_C1forced.json"),
    ("art_18XvfcJJZi1O", "results/selection_C1nat.json"),
    ("art_18XvfcJJZi1O", "results/selection_C2a.json"),
    ("art_18XvfcJJZi1O", "results/circuit_C1nat.json"),
    ("art_18XvfcJJZi1O", "results/circuit_C1forced.json"),
    ("art_18XvfcJJZi1O", "results/circuit_C2a.json"),
    ("art_18XvfcJJZi1O", "results/circuit_C1mix.json"),
    ("art_18XvfcJJZi1O", "results/circuit_C1natB.json"),
    ("art_18XvfcJJZi1O", "data/validation_rows_C1forced.jsonl"),
    ("art_18XvfcJJZi1O", "cache/write_norms_C1forced.npy"),
    ("art_18XvfcJJZi1O", "inputs/exp35"),
    ("art_18XvfcJJZi1O", "inputs/exp34"),
    ("art_18XvfcJJZi1O", "inputs/dep_noun_bank.json"),
    ("art_18XvfcJJZi1O", "inputs/iter6_exp30/src"),
    ("art_18XvfcJJZi1O", "inputs/iter5_exp26"),            # frozen B3 labeller + hidden tests (generation scoring)
    ("art_18XvfcJJZi1O", "inputs/iter6_exp30/inputs"),     # exp11 bench / exp8 suite used by label_worker_v4 (T10)
    ("art_lzuosbrb34wB", "src/base_arm.py"),
    ("art_lzuosbrb34wB", "src/engine8.py"),
    ("art_lzuosbrb34wB", "src/prompts8.py"),
    ("art_lzuosbrb34wB", "src/label7.py"),
    ("art_lzuosbrb34wB", "src/label8.py"),
    ("art_lzuosbrb34wB", "src/locate8.py"),
    ("art_lzuosbrb34wB", "src/cfg8.py"),
    ("art_lzuosbrb34wB", "results/base_subarm.json"),
    ("art_lzuosbrb34wB", "results/locate_B3.json"),
    ("art_lzuosbrb34wB", "results/locate_G-T04.json"),
    ("art_lzuosbrb34wB", "results/locate_G-R6.json"),
    ("art_lzuosbrb34wB", "results/locate_L-T1.json"),
    ("art_lzuosbrb34wB", "prompts/prompts8.jsonl"),
    ("art_lzuosbrb34wB", "data/samples_raw.jsonl"),
    ("art_MZAfDPVhM6Ui", "predictions/collapsed_raw.json"),
    ("art_MZAfDPVhM6Ui", "data/samples_raw.jsonl"),
    ("art_zNyBP6zieI5u", "results/fork.json"),
    ("art_zNyBP6zieI5u", "results/nouns.json"),
    ("art_zNyBP6zieI5u", "data/prompts_fed.jsonl"),
    ("art_zNyBP6zieI5u", "data/raw_s3.jsonl"),
    ("art_FJMIE9T9_PMv", "data/samples.jsonl"),
    ("exp38", "results/g1_pathpatch.json"),
    ("exp38", "results/g1_validation.json"),
    ("art_j3Rm_lr2nzR6", "preview_data_out.json"),
    ("art_j3Rm_lr2nzR6", "mini_data_out.json"),
]


def hardware() -> dict:
    import torch
    import transformers
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version",
                          "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
    hw = {"gpu": gpu, "cpus": detect_cpus(), "ram_limit_GB": container_ram_gb(), "python": platform.python_version(),
          "torch": torch.__version__, "cuda": torch.version.cuda, "transformers": transformers.__version__,
          "utc": utc_now()}
    write_json(PRED_DIR / "hardware.json", hw)
    return hw


def vendor() -> dict:
    rows, missing = [], []
    for art, rel in WANT:
        src = SRCS[art] / rel
        dst = VENDOR / art / rel
        if not src.exists():
            missing.append(f"{art}/{rel}")
            logger.warning(f"missing input {art}/{rel}")
            continue
        files = [src] if src.is_file() else sorted(p for p in src.rglob("*") if p.is_file() and
                                                   "__pycache__" not in p.parts)
        for f in files:
            d = dst if src.is_file() else dst / f.relative_to(src)
            d.parent.mkdir(parents=True, exist_ok=True)
            if not d.exists() or d.stat().st_size != f.stat().st_size:
                shutil.copy2(f, d)
            rows.append({"artifact": art, "path": str(d.relative_to(VENDOR)), "bytes": d.stat().st_size,
                         "sha256": sha256_file(d)})
    out = {"utc": utc_now(), "n_files": len(rows), "missing": missing, "files": rows}
    write_json(VENDOR / "inputs.json", out)
    logger.info(f"vendored {len(rows)} files; missing {missing}")
    return out


if __name__ == "__main__":
    setup_logging("s0_preflight")
    logger.info(hardware())
    vendor()
