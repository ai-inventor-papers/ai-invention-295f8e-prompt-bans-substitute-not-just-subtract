#!/usr/bin/env python3
"""Weight set B follow-up (S5, only if time remains): POP alpha 1 (40 directions, screen k 0-1, then confirmation of
screen passers) for the listed engines and tasks, at the SAME batch size and KV cap as gpu_b.py (read from
results/gpu_b_log.json) so the batch shape of each engine is unchanged. Alpha 1 halves the absolute dose; at block 12
it is below iteration 5's ban-free PN dose (0.66 x the alpha-2 ban dose), so it also locates the dose boundary between
this artifact's escapes and iteration 5's bf16 PN null (the committed NOT_REPRODUCED_HIGH follow-up)."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import torch  # noqa: E402
from loguru import logger  # noqa: E402

import c6  # noqa: E402,F401
from c6 import DEFAULTS, K_CONFIRM, K_SCREEN, RESULTS, SEEDS_POP, read_json, setup_logging, utc_now, write_json  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engines", default="d")
    ap.add_argument("--tasks", default="T10,T2")
    ap.add_argument("--deadline-min", type=float, default=40.0)
    args = ap.parse_args()
    setup_logging("gpu_b2")
    from c6 import DATA
    if (DATA / "SKIP_B2").exists():
        logger.info("data/SKIP_B2 present: the alpha-1 follow-up is skipped (GPU time goes to engine-b confirmations)")
        write_json(RESULTS / "gpu_b2_log.json", {"skipped": True, "reason": (DATA / "SKIP_B2").read_text(),
                                                  "utc": utc_now()})
        return
    torch.backends.cuda.matmul.allow_tf32 = False
    deadline = time.time() + args.deadline_min * 60
    import engines as EN
    from escape import needs_confirmation
    from gen import Runner
    from gpu_b import catalogue
    from prompts4 import load_prompts4
    from rows6 import engine_rows, wait_labels

    probe = read_json(RESULTS / "gpu_b_log.json")["probe"]
    B, cap = int(probe["B"]), int(probe["cap"])
    tok, model = EN.load_b()
    prompts = load_prompts4()
    log = {"start_utc": utc_now(), "B": B, "cap": cap, "stages": []}
    tasks = args.tasks.split(",")
    for m in args.engines.split(","):
        EN.set_mode(m)
        run = Runner(model, tok, prompts, m, B=B, cap=cap)
        for task in tasks:
            n = run.run_cells(task, [(f"POP_d{s}_a1.0", K_SCREEN) for s in SEEDS_POP], "S5_screen_a1", deadline=deadline)
            log["stages"].append({"engine": m, "task": task, "stage": "S5 screen", "batches": n, "utc": utc_now()})
            write_json(RESULTS / "gpu_b2_log.json", log)
        for task in tasks:
            if time.time() > deadline:
                log["stages"].append({"engine": m, "task": task, "stage": "S5 confirm", "status": "dropped (deadline)"})
                continue
            wait_labels(m, task, timeout=600)
            dirs = needs_confirmation(engine_rows(m, task), SEEDS_POP, catalogue(task), DEFAULTS[task], 1.0)
            n = run.run_cells(task, [(f"POP_d{s}_a1.0", K_CONFIRM) for s in dirs], "S5_confirm_a1", deadline=deadline)
            log["stages"].append({"engine": m, "task": task, "stage": "S5 confirm", "dirs": dirs, "batches": n,
                                  "utc": utc_now()})
            write_json(RESULTS / "gpu_b2_log.json", log)
    log["end_utc"] = utc_now()
    write_json(RESULTS / "gpu_b2_log.json", log)
    logger.info("gpu_b2 done")


if __name__ == "__main__":
    main()
