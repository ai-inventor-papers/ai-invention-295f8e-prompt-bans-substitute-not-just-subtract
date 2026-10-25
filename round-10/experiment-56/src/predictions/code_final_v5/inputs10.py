#!/usr/bin/env python3
"""S_-1: vendor the read-only inputs, write inputs_manifest.json (source path, sha256, bytes), cross-check the
vendored files against iteration 9's vendor/inputs.json, record hardware/env, and run the LABELLER GATE (the frozen
label_k3.py must reproduce iteration 9's labels of its 240 stored programs on >= 0.99 of them).

Usage: inputs10.py copy | hardware | gate
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from loguru import logger

from cfg10 import (DATA_DIR, DEP_DATASET, I9, ITER9, PRED_DIR, RESULTS_DIR, ROOT, THRESH, V41, container_ram_gb,
                   detect_cpus, log_deviation, read_json, read_jsonl, setup_logging, sha256_file, utc_now,
                   write_json)

I9_RESULTS = ["units.json", "b2_summary.json", "b2_generation.json", "weight_change.json", "b2_tf_B3.jsonl",
              "b2_tf_T10.jsonl", "b1_gemma_G-GRID.json", "b1_summary.json", "b1_tf_gemma.json", "b1_tf_gemma_pt.json",
              "capture_base.json", "capture_instr.json", "random_sets.json", "gpu_tests_b2.json", "deviations.json",
              "summary.json"]
CRITICAL = {"results/units.json", "vendor/art_18XvfcJJZi1O/src/label_k3.py"}


def copy_inputs() -> dict[str, Any]:
    """Copy (if absent) and hash every input; stop on a mismatch of units.json or label_k3.py."""
    if not ITER9.exists():
        raise FileNotFoundError(f"ITER9 folder missing: {ITER9} (REBUILD fallback F0 would apply)")
    pairs: list[tuple[Path, Path]] = []
    for f in I9_RESULTS:
        pairs.append((ITER9 / "results" / f, I9 / "results" / f))
    for f in ("samples.jsonl", "labels_gen.jsonl"):
        pairs.append((ITER9 / "data" / f, I9 / "data" / f))
    for f in ("pyproject.toml", "README.md", "commitments.log"):
        pairs.append((ITER9 / f, I9 / f))
    for p in sorted((ITER9 / "src").glob("*.py")):
        pairs.append((p, I9 / "src" / p.name))
    for p in sorted((ITER9 / "predictions").glob("*.json")):
        pairs.append((p, I9 / "predictions" / p.name))
    for p in sorted((ITER9 / "vendor").rglob("*")):
        if p.is_file():
            pairs.append((p, I9 / "vendor" / p.relative_to(ITER9 / "vendor")))
    files = []
    for src, dst in pairs:
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        s_src, s_dst = sha256_file(src), sha256_file(dst)
        files.append({"source": str(src), "dest": str(dst.relative_to(ROOT)), "sha256": s_dst,
                      "bytes": dst.stat().st_size, "copy_ok": s_src == s_dst})
    # cross-check the vendored files against iteration 9's own vendor/inputs.json
    vin = read_json(I9 / "vendor" / "inputs.json")
    mism, checked = [], 0
    for r in vin["files"]:
        p = I9 / "vendor" / r["path"]
        if not p.exists():
            mism.append({"path": r["path"], "issue": "missing"})
            continue
        checked += 1
        if sha256_file(p) != r["sha256"]:
            mism.append({"path": r["path"], "issue": "sha256 differs from vendor/inputs.json"})
    bad_copy = [f for f in files if not f["copy_ok"]]
    crit_bad = [m for m in mism if "vendor/" + m["path"] in CRITICAL] + \
        [f for f in bad_copy if f["dest"].replace("inputs/iter9/", "") in CRITICAL]
    # declared dependency (iteration-1 dataset): used only by the REBUILD fallback; record its presence and hashes
    dep = {"workspace": str(DEP_DATASET), "exists": DEP_DATASET.exists(), "files": []}
    for f in ("mini_data_out.json", "preview_data_out.json", "reproducibility.md", "data.py"):
        p = DEP_DATASET / f
        if p.exists():
            dep["files"].append({"path": str(p), "sha256": sha256_file(p), "bytes": p.stat().st_size})
    out = {"utc": utc_now(), "iter9_source": str(ITER9), "n_files": len(files), "files": files,
           "vendor_inputs_json_checked": checked, "vendor_mismatches": mism, "copy_mismatches": bad_copy,
           "critical_mismatch": crit_bad, "declared_dependency_art_j3Rm_lr2nzR6": dep}
    write_json(ROOT / "inputs_manifest.json", out)
    logger.info(f"inputs: {len(files)} files, vendor cross-check {checked} files, {len(mism)} mismatches, "
                f"{len(bad_copy)} copy mismatches")
    for m in mism:
        log_deviation(f"vendor_mismatch_{m['path']}", f"vendored file {m['path']}: {m['issue']}")
    if crit_bad:
        raise RuntimeError(f"critical input mismatch: {crit_bad}")
    return out


def hardware() -> dict[str, Any]:
    import torch
    out: dict[str, Any] = {"utc": utc_now(), "cpus_cgroup": detect_cpus(), "ram_limit_GB": container_ram_gb(),
                           "disk_free_GB": round(shutil.disk_usage(ROOT).free / 1e9, 1)}
    try:
        out["nvidia_smi"] = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version",
                                            "--format=csv,noheader"], capture_output=True, text=True,
                                           timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError) as e:
        out["nvidia_smi"] = f"error: {e}"
    if torch.cuda.is_available():
        free, total = torch.cuda.mem_get_info(0)
        out.update(gpu=torch.cuda.get_device_name(0), vram_free_GB=round(free / 1e9, 2),
                   vram_total_GB=round(total / 1e9, 2), capability=list(torch.cuda.get_device_capability(0)))
    import importlib.metadata as md
    env = {"python": sys.version.split()[0]}
    for pkg in ("torch", "transformers", "safetensors", "accelerate", "numpy", "scipy", "loguru", "matplotlib",
                "scikit-learn", "tokenizers", "huggingface-hub"):
        try:
            env[pkg] = md.version(pkg)
        except md.PackageNotFoundError:
            env[pkg] = None
    env["cuda_runtime"] = torch.version.cuda
    write_json(PRED_DIR / "hardware.json", out)
    write_json(PRED_DIR / "env.json", env)
    logger.info(f"hardware {out}; env {env}")
    return out


def run_labeller(rows: list[dict[str, Any]], tag: str) -> list[dict[str, Any]]:
    """Run the frozen label_k3.py in its own process (it imports clashing module names); rows: {sid, unit, text}."""
    tmp_in, tmp_out = DATA_DIR / f"label_in_{tag}.tmp.jsonl", DATA_DIR / f"label_out_{tag}.tmp.jsonl"
    tmp_in.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    if tmp_out.exists():
        tmp_out.unlink()
    subprocess.run([sys.executable, "label_k3.py", str(tmp_in), str(tmp_out)], cwd=V41 / "src", check=True,
                   timeout=3600)
    out = read_jsonl(tmp_out)
    tmp_in.unlink()
    tmp_out.unlink()
    return out


def gate() -> dict[str, Any]:
    t0 = time.time()
    samples = read_jsonl(I9 / "data" / "samples.jsonl")
    ref = {r["sid"]: r for r in read_jsonl(I9 / "data" / "labels_gen.jsonl")}
    rows = [{"sid": s["sid"], "unit": s["task"], "text": s["text"]} for s in samples]
    got = {r["sid"]: r for r in run_labeller(rows, "gate")}
    agree_label = sum(1 for s in ref if s in got and got[s]["label"] == ref[s]["label"])
    agree_both = sum(1 for s in ref if s in got and got[s]["label"] == ref[s]["label"]
                     and bool(got[s]["passed"]) == bool(ref[s]["passed"]))
    dis = [{"sid": s, "ref": (ref[s]["label"], ref[s]["passed"]), "got": (got.get(s, {}).get("label"),
                                                                           got.get(s, {}).get("passed"))}
           for s in ref if s not in got or got[s]["label"] != ref[s]["label"] or
           bool(got[s]["passed"]) != bool(ref[s]["passed"])]
    n = len(ref)
    out = {"utc": utc_now(), "n_programs": n, "agree_label": agree_label, "agree_label_and_pass": agree_both,
           "rate_label_and_pass": agree_both / n if n else None, "threshold": THRESH["labeller_gate"],
           "pass": n > 0 and agree_both / n >= THRESH["labeller_gate"], "disagreements": dis,
           "seconds": round(time.time() - t0, 1)}
    write_json(RESULTS_DIR / "labeller_gate.json", out)
    logger.info(f"labeller gate: {agree_both}/{n} agree (label and pass) -> pass={out['pass']} in {out['seconds']}s")
    if not out["pass"]:
        log_deviation("labeller_gate_failed", f"label_k3.py reproduced {agree_both}/{n} iteration-9 labels "
                                              f"(< {THRESH['labeller_gate']}); fallback F4 applies", "major")
    return out


if __name__ == "__main__":
    setup_logging(f"inputs10_{sys.argv[1]}")
    {"copy": copy_inputs, "hardware": hardware, "gate": gate}[sys.argv[1]]()
