#!/usr/bin/env python3
"""Post-queue restoration (amendment A2, logged): the committed drop order was decided from stage-100 timings whose
multi-stage batches held 2 rows each, so the extrapolation over-estimated the queue (15,530 s). When the committed
queue finishes before the hard generation deadline, the dropped cells are run in REVERSE drop order
(IFG_paper on D5 -> ND10 PLAIN/PNPLAIN_a1 -> ND10 DMD_a2 -> the SEMSEED rerun -> ND10 k 4-5 top-up of the P4 arms ->
P5) until the same deadline; every restored row carries block_id 'restore:<step>'. Nothing in the committed rule
changes; the analysis reports both the committed (drop-order) cell set and the restored one.

usage: .venv/bin/python src/gen5_restore.py   (waits for results/gpu_done.flag, then loads the model)
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import torch
from loguru import logger

import cfg as C
from cfg import RESULTS_DIR, TEMPLATE_IDS, append_deviation, read_json, utc_now, write_json
from cfg5 import D5, K_D5, K_ND10, ND10, P4, PRED_DIR, gen_deadline_unix
import gen5 as G
from engine_v4 import load_model
from prompts5 import load_prompts


def steps() -> list[tuple[str, list[tuple[str, list[str], list[tuple[str, int]]]]]]:
    nd_all = [(w, k) for w in TEMPLATE_IDS for k in K_ND10]
    d5_all = [(w, k) for w in TEMPLATE_IDS for k in K_D5]
    return [
        ("IFG_paper", [(t, ["IFG_paper"], d5_all) for t in D5]),
        ("ND10_PLAIN_PNPLAIN", [(t, ["PLAIN", "PNPLAIN_a1"], nd_all) for t in ND10]),
        ("ND10_DMD_a2", [(t, ["DMD_a2"], nd_all) for t in ND10]),
        ("SEMSEED_rerun", [(t, ["SEMSEED"], d5_all) for t in ("T1", "T2")]),
        ("ND10_N30_topup", [(t, [a for a in P4 if a not in ("PLAIN", "PNPLAIN_a1", "DMD_a2")], nd_all) for t in ND10]),
        ("P5", [(t, ["PSL", "BINT"], nd_all) for t in ND10]),
    ]


@logger.catch(reraise=True)
def main() -> None:
    C.setup_logging("gen5_restore")
    flag = RESULTS_DIR / "gpu_done.flag"
    while not flag.exists():
        time.sleep(20)
    deadline = gen_deadline_unix()
    if time.time() > deadline - 300:
        logger.info("no time left before the generation deadline: nothing restored")
        write_json(RESULTS_DIR / "restore_result.json", {"restored": [], "utc": utc_now()})
        (RESULTS_DIR / "restore_done.flag").write_text(utc_now())
        return
    append_deviation("A2-restore", "the committed queue finished before the deadline; dropped cells are restored in "
                     "reverse drop order until the same deadline (block_id 'restore:<step>'); analyses report the "
                     "committed and the restored cell sets")
    prompts = load_prompts()
    tok, model = load_model(fp8=False, vram_fraction=0.97)
    dmd = read_json(PRED_DIR / "dmd_temperatures.json")
    log = []
    for name, items in steps():
        for task, arms, slots in items:
            if time.time() > deadline:
                log.append({"step": name, "task": task, "status": "not run (deadline)"})
                continue
            n = G.run_cell_group(model, tok, prompts, task, arms, slots, f"restore:{name}", dmd, deadline)
            log.append({"step": name, "task": task, "arms": arms, "rows": n, "utc": utc_now()})
            torch.cuda.empty_cache()
    write_json(RESULTS_DIR / "restore_result.json", {"restored": log, "utc": utc_now()})
    (RESULTS_DIR / "restore_done.flag").write_text(utc_now())


if __name__ == "__main__":
    main()
