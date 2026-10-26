#!/usr/bin/env python3
"""GPU driver of iteration 7: loads bf16 Qwen3-8B once and runs the requested stages in order.

usage: .venv/bin/python src/run_gpu7.py STAGES [--tasks T2,T10] [--deadline-min N]
stages: utest, s0, profile, fit, tfeval, gen, gen2, m, r, randinit (see method.py for the full pipeline)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import torch
from loguru import logger

from cfg import PRED_DIR, setup_logging, utc_now, write_json
from cfg7 import BATCH7, ENGINE7, MAX_NEW7, results7
import gpu7
from prompts7 import load_prompts7


def hardware(info: dict) -> None:
    import transformers
    p = PRED_DIR / "hardware.json"
    hw = {"gpu": torch.cuda.get_device_name(0), "total_vram_GB": info["total_vram_GB"],
          "free_vram_after_load_GB": info["free_vram_after_GB"], "driver_cuda": torch.version.cuda,
          "torch": torch.__version__, "transformers": transformers.__version__, "precision": "bf16",
          "cpu_embedding": info["cpu_embedding"], "engine": ENGINE7, "batch_sizes": BATCH7, "max_new": MAX_NEW7,
          "load_seconds": info["load_seconds"], "utc": utc_now()}
    try:
        import subprocess
        hw["nvidia_smi"] = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                                           "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
    except OSError:
        pass
    if p.exists():
        import json
        old = json.loads(p.read_text())
        old.update({k: v for k, v in hw.items() if k not in old})
        hw = old
    write_json(p, hw)


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stages")
    ap.add_argument("--tasks", default="T2,T10")
    ap.add_argument("--deadline-min", type=float, default=1e9)
    args = ap.parse_args()
    setup_logging("gpu7")
    gpu7.STATE["deadline"] = time.time() + 60 * args.deadline_min
    torch.manual_seed(0)
    if args.stages in ("randinit", "randinitly"):  # the random network must not share the GPU with the trained one
        import stages_c7 as C
        P7 = load_prompts7()
        for t in [t for t in args.tasks.split(",") if t]:
            C.stage_randinit(None, P7, t, objective="C" if args.stages == "randinit" else "lmeY")
        write_json(results7(f"stage_{args.stages}_{args.tasks.replace(',', '_')}_done.json"), {"utc": utc_now()})
        return
    tok, model, info = gpu7.load7()
    hardware(info)
    P7 = load_prompts7()
    tasks = [t for t in args.tasks.split(",") if t]
    for st in args.stages.split(","):
        t0 = time.time()
        logger.info(f"=== stage {st} ({tasks}) ===")
        if st == "utest":
            import stages_a7 as A
            ut = A.stage_utest(model, tok, P7)
            ut.update(A.stage_utest_gen(model, tok, P7))
            write_json(results7("unit_tests_gpu.json"), ut)
            logger.info(f"unit tests: {ut}")
        elif st == "s0":
            import stages_a7 as A
            for t in tasks:
                A.run_stage0(model, tok, P7, t)
        else:
            import stages_b7 as Bst
            Bst.run_stage(st, model, tok, P7, tasks)
        write_json(results7(f"stage_{st}_{'_'.join(tasks)}_done.json"), {"seconds": round(time.time() - t0, 1),
                                                                          "utc": utc_now()})
        logger.info(f"=== stage {st} done in {time.time() - t0:.0f}s ===")


if __name__ == "__main__":
    main()
