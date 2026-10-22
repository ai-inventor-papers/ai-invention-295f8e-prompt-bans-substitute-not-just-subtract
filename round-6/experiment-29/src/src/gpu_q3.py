#!/usr/bin/env python3
"""Weight set Q continuation: finish engine b's confirmations (resumable by done slots) after gpu_q2 hit its deadline.
Same engine b implementation as gpu_q2 (results/w8a16_impl.json), same B = 20, same cells."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import torch  # noqa: E402
from loguru import logger  # noqa: E402

import c6  # noqa: E402,F401
from c6 import DEFAULTS, K_CONFIRM, RESULTS, SEEDS_POP, read_json, setup_logging, utc_now, write_json  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deadline-min", type=float, default=12.0)
    args = ap.parse_args()
    setup_logging("gpu_q3")
    torch.backends.cuda.matmul.allow_tf32 = False
    deadline = time.time() + args.deadline_min * 60
    import engines as EN
    from escape import needs_confirmation
    from gen import PRECISION, Runner
    from gpu_q2 import catalogue
    from prompts4 import load_prompts4
    from rows6 import engine_rows, wait_labels

    imp = read_json(RESULTS / "w8a16_impl.json")
    tok, model = EN.load_q()
    EN.MODE["b_impl"] = imp["chosen"]
    PRECISION["b"] += f" [impl: {imp['chosen']}]"
    prompts = load_prompts4()
    EN.set_mode("b")
    run = Runner(model, tok, prompts, "b", B=20)
    log = {"start_utc": utc_now(), "impl": imp["chosen"], "tasks": {}}
    for task in ("T10", "T2"):
        wait_labels("b", task, timeout=300)
        from escape import escape_table
        tab = escape_table(engine_rows("b", task), SEEDS_POP, catalogue(task), DEFAULTS[task], alphas=(2.0,))
        dirs = [s for s in SEEDS_POP if (tab["cells"].get(f"{s}|2.0") or {}).get("screen_pass")]
        n = run.run_cells(task, [(f"POP_d{s}_a2.0", K_CONFIRM) for s in dirs], "S3_confirm", deadline=deadline)
        log["tasks"][task] = {"dirs_needing_confirmation": dirs, "batches": n}
        write_json(RESULTS / "gpu_q3_log.json", log)
    log["end_utc"] = utc_now()
    write_json(RESULTS / "gpu_q3_log.json", log)
    logger.info("gpu_q3 done")


if __name__ == "__main__":
    main()
