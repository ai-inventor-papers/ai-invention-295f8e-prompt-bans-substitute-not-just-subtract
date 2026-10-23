#!/usr/bin/env python3
"""S0 preflight: hardware + the precision rule (written BEFORE any sample), input hashes (inputs/SHA256SUMS, bench
files vs exp11 bench/commitment.json, the frozen movability screen sha256), and the seed-collision registry.

usage: .venv/bin/python src/s0.py {precision|hashes|seeds|recheck|all}
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger

from cfg import (INPUTS, PRED_DIR, RESULTS_DIR, detect_cpus, read_json, setup_logging, sha256_file, stable_seed,
                 utc_now, write_json)
from cfg5 import CAL_K, CAL_W, D5, EVAL3, ND10, TASKS15, slots_for

SCREEN_SHA = "d6a2ca9711f461973c39482314a523d448d0590cb40e32432826dec1da4846e8"


def hardware() -> dict[str, Any]:
    q = subprocess.run(["nvidia-smi", "--query-gpu=name,compute_cap,memory.total,memory.free,driver_version",
                        "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=30)
    name, cc, tot, free, drv = [x.strip() for x in q.stdout.strip().splitlines()[0].split(",")]
    du = shutil.disk_usage(str(INPUTS))
    ram = None
    for p in ("/sys/fs/cgroup/memory/memory.limit_in_bytes", "/sys/fs/cgroup/memory.max"):
        try:
            v = Path(p).read_text().strip()
            if v != "max":
                ram = int(v) / 1e9
                break
        except (FileNotFoundError, ValueError):
            continue
    return {"gpu": name, "compute_capability": cc, "vram_total_mib": float(tot), "vram_free_mib": float(free),
            "driver": drv, "gcc": shutil.which("gcc"), "cc": shutil.which("cc"), "nvcc": shutil.which("nvcc"),
            "cpus": detect_cpus(), "ram_gb_container": ram, "disk_free_gb": du.free / 1e9}


def precision_rule() -> dict[str, Any]:
    p = PRED_DIR / "precision_rule.json"
    if p.exists():
        return read_json(p)
    hw = hardware()
    cc = float(hw["compute_capability"])
    vram_gib = hw["vram_total_mib"] / 1024
    if cc >= 8.9 and vram_gib < 19.5:
        eng = "hf_fp8"
    else:
        eng = "hf_bf16"
    vram_b = hw["vram_total_mib"] * 2 ** 20
    kv_seqs_bf16 = (0.90 * vram_b - 16.4e9 - 1.5 * 2 ** 30) / (18432 * 147_456)
    rule = {"utc": utc_now(), "hardware": hw,
            "rule": ("Ada/Hopper (cc >= 8.9) with < 19.5 GiB -> HF FP8 W8A8 engine (engine_v4 'hf_fp8'); otherwise -> "
                     "HF bf16 with batch size from a memory probe (rows x (P + max_new) x 147,456 B <= 0.8 x free "
                     "VRAM). vLLM literal cell: bf16 only if the KV cache fits >= 4 sequences of 18,432 tokens, else "
                     "Qwen/Qwen3-8B-FP8 rev 220b46e3."),
            "hf_engine": eng, "vram_gib": vram_gib, "compute_capability": cc,
            "vllm_kv_seqs_bf16": kv_seqs_bf16, "vllm_checkpoint": "bf16" if kv_seqs_bf16 >= 4 else "fp8_official",
            "consequence": ("bf16: iteration-4 FP8 rows cannot be reused slot for slot; T1.3, TOPK10, NOVELTY and "
                            "SEMSEED are rerun on D5 (P3); everything else from iteration 4 is carried flagged "
                            "'other engine'; the engine-check difference is reported as precision sensitivity")
            if eng == "hf_bf16" else "fp8: reuse allowed per arm only if the engine check is byte-identical",
            "vllm_no_compiler_flags": hw["gcc"] is None and hw["cc"] is None}
    write_json(p, rule)
    logger.info(f"precision rule: {rule['hf_engine']} on {hw['gpu']} ({vram_gib:.1f} GiB, cc {cc}); vLLM "
                f"{rule['vllm_checkpoint']}")
    return rule


def hashes() -> dict[str, Any]:
    from s0_checks import input_hashes

    ih = input_hashes()
    ih["screen_sha256"] = sha256_file(EVAL3 / "screen.json")
    ih["screen_sha256_expected"] = SCREEN_SHA
    ih["screen_ok"] = ih["screen_sha256"] == SCREEN_SHA
    ih["pass"] = ih["pass"] and ih["screen_ok"]
    write_json(RESULTS_DIR / "input_hashes.json", ih)
    logger.info(f"input hashes: pass={ih['pass']} bench mismatches={len(ih['mismatches'])} screen_ok={ih['screen_ok']}")
    if not ih["pass"]:
        raise SystemExit("input hash mismatch: abort (plan S0.1)")
    return ih


def seeds() -> dict[str, Any]:
    """New seed tags vs every integer seed in the iteration-3/4 direction and seed files."""
    new: dict[int, str] = {}
    from cfg5 import F_SEED_K
    for t in TASKS15:
        for w in ("W1", "W2", "W3", "W4", "W5"):
            for k in range(10):
                for tag in ("PN5", "PNCAL"):
                    new[stable_seed(t, tag, w, k)] = f"{t}|{tag}|{w}|{k}"
                for tag in ("CAL", "IFG:intent", "BINT:intent", "PSL:A", "PSL:B", "EAP:A", "EAP_pick", "PSL_pair"):
                    new[stable_seed(t, w, k, tag)] = f"{t}|{w}|{k}|{tag}"
    old: set[int] = set()
    import re as _re
    for root in (INPUTS / "exp17", INPUTS / "exp19", INPUTS / "exp21", INPUTS / "exp13"):
        for p in root.rglob("*.json"):
            if p.stat().st_size > 5_000_000:
                continue
            try:
                txt = p.read_text()
            except UnicodeDecodeError:
                continue
            for m in _re.finditer(r"\b(\d{4,19})\b", txt):
                old.add(int(m.group(1)))
    # the iteration-4 per-row seeds (direction_seed, u_seed) in exp19 samples.jsonl
    for line in open(INPUTS / "exp19" / "data" / "samples.jsonl"):
        r = json.loads(line)
        for k in ("direction_seed", "u_seed"):
            if r.get(k) is not None:
                old.add(int(r[k]))
    coll = sorted(set(new) & old)
    res = {"n_new": len(new), "n_old_scanned": len(old), "collisions": len(coll),
           "collision_tags": [new[c] for c in coll][:20], "utc": utc_now()}
    write_json(RESULTS_DIR / "seed_collisions.json", res)
    logger.info(f"seed registry: {res['n_new']} new seeds, {res['collisions']} collisions")
    return res


def recheck() -> None:
    from s0_checks import bench_recheck, suite_recheck

    lr = {"bench": bench_recheck(), "exp8_suite": suite_recheck(),
          "note": "mechanical labels only (runtime/AST); the judge is not re-run (spend)"}
    lr["all_bench_refs_pass"] = all(v["references_pass"] for v in lr["bench"].values())
    lr["all_gold_within_0.02"] = all(v["within_0.02"] for v in lr["bench"].values())
    write_json(RESULTS_DIR / "labeller_recheck.json", lr)
    logger.info(f"labeller recheck: refs pass {lr['all_bench_refs_pass']}, gold within 0.02 {lr['all_gold_within_0.02']}")


if __name__ == "__main__":
    setup_logging("s0")
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("precision", "all"):
        precision_rule()
    if what in ("hashes", "all"):
        hashes()
    if what in ("seeds", "all"):
        seeds()
    if what in ("recheck", "all"):
        recheck()
