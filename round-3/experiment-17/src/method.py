#!/usr/bin/env python3
"""Where in Qwen3-8B a coding ban lives -- orchestrator.

Stages (each resumable; see README.md):
  prompts   S1 (CPU)                     ban prompts + token-aligned neutral twins, 14 tasks x W1-W5
  gpu1      S2 + GPU unit tests + commit #1 + U7 + S5 (ban-free arms) + C2f head means
  label     label worker (CPU): labels every raw sample as it appears (exp8 suite for T1/T2, exp11 bench label_one)
  commit2   S6 (CPU): S5 summaries, ADD-landing forecast, commit #2
  gpu2      S7 (ban arms, SUB, heads, W4 top-up) + S8 state extraction
  zerog     0g SAE transfer (GPU, base model in a separate load)
  analyze   S9 analyses (C2d, C2e, C2f, 0g report, 5a, 5c) + figures + method_out.json
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from loguru import logger  # noqa: E402

from cfg import (RESULTS_DIR, SAMPLED_TASKS, read_json, read_jsonl, set_ram_limit, setup_logging,  # noqa: E402
                 utc_now, write_json)


def gpu1(deadline: float, optional_until: float) -> None:
    import torch

    from direction import stage_direction
    from engine import load_model
    from gpu_tests import run_gpu_tests
    from prereg import write_commit1
    from prompts import load_prompts
    from sampling import TaskContext, run_batch, run_task_phase, s5_batches

    torch.cuda.set_per_process_memory_fraction(0.97, 0)
    tok, model = load_model()
    prompts = load_prompts()
    if not (RESULTS_DIR / "direction.json").exists():
        stage_direction(model)
    if not (RESULTS_DIR / "unit_tests_gpu.json").exists():
        res = run_gpu_tests(model, tok, prompts)
        if not res["all_pass"]:
            logger.error("GPU unit tests failed -- see results/unit_tests_gpu.json")
            raise SystemExit(2)
    if not (ROOT / "predictions" / "commit1.json").exists():
        c = write_commit1()
        logger.info(f"commit #1: {len(c['chain'])} files hash-chained")
    # U7 engine validation against exp8 (T2, exp8 frozen prompts and exp8 uniform keys ('beh', 't2', w, s))
    raw = read_jsonl(ROOT / "data" / "samples_raw.jsonl")
    if not any(r.get("block_id", "").startswith("U7") for r in raw):
        ctx = TaskContext(model, tok, prompts, "T2")
        for arm in ("BAN", "NEUTRAL"):
            rows = run_batch(ctx, "W1", [(arm, list(range(20)))], f"U7:T2:W1:{arm}", ukey=("beh", "t2"),
                             arm_prefix="U7_")
            logger.info(f"U7 {arm}: {len(rows)} rows sampled with exp8 keys")
    # S5 required arms, whole tasks in the frozen order
    for t in SAMPLED_TASKS:
        n = run_task_phase(model, tok, prompts, t, s5_batches(), "S5", deadline=deadline)
        logger.info(f"S5 {t}: {n} new batches")
    # optional S5 arms (RAND alpha 2 for seeds 9002/9003, then ADD alpha 0.5) while time allows
    for t in SAMPLED_TASKS:
        if time.time() > optional_until:
            break
        run_task_phase(model, tok, prompts, t, s5_batches(optional=True), "S5", deadline=optional_until)
    write_json(RESULTS_DIR / "gpu1_done.json", {"utc": utc_now()})


EXTRA_SEEDS = list(range(9004, 9016))


def s8c() -> None:
    """Re-extract the 5c states of every non-ban/neutral arm at batch 1, so all 5c points share one extraction mode
    (BAN/NEUTRAL were re-extracted at batch 1 in gpu3; mixing batch-20 and batch-1 states would add a systematic
    row-position offset between arms)."""
    from engine import load_model
    from gpu2 import _raw_by_arm
    from prompts import load_prompts
    from states import BLOCKS_5C, save_arm

    tok, model = load_model()
    prompts = load_prompts()
    t0 = time.time()
    for (t, arm), rows in sorted(_raw_by_arm().items()):
        if t not in SAMPLED_TASKS or arm in ("BAN", "NEUTRAL", "BAN_TOPUP") or arm.startswith(("U7", "RAND90")) \
                and arm not in ("RAND9001_a1.0", "RAND9002_a1.0", "RAND9003_a1.0", "RAND9001_a2.0", "RAND9002_a2.0",
                                "RAND9003_a2.0"):
            continue
        kind = "twin" if (arm.startswith("ADD") or arm.startswith("RAND")) else "ban"
        save_arm(model, prompts, t, arm, rows, tag=f"5c_{t}_{arm}", blocks=BLOCKS_5C, full=False, prompt_kind=kind,
                 bs=1, overwrite=True)
    write_json(RESULTS_DIR / "s8c_done.json", {"utc": utc_now(), "seconds": time.time() - t0})


def u1b(model, tok, prompts) -> None:
    """U1b: (a) decode is row-position independent: rows with identical prefill and identical uniforms placed at
    different batch positions give identical tokens; (b) teacher forcing at batch 1 is deterministic and depends only on
    the prefix; (c) teacher forcing in a 20-row batch is NOT (FP8 GEMM tiling), quantified."""
    import numpy as np

    from engine import forward_capture, sample, u_stream
    from sampling import TaskContext

    ctx = TaskContext(model, tok, prompts, "T2")
    pre = ctx.clean_prefill("W1", "twin")["pre"]
    us = [u_stream("u1b", j % 10) for j in range(20)]  # row j and row j+10 share uniforms
    res = sample(model, [{"pre": pre, "us": us}], max_new=96)
    same = [res[j]["token_ids"] == res[j + 10]["token_ids"] for j in range(10)]
    pr = prompts[("T2", "W1", "ban")]
    ids = pr["ids"] + [73594, 12669, 198]
    P = pr["P"]
    a = forward_capture(model, [ids], [20, 28], [P - 1, P])
    b = forward_capture(model, [ids], [20, 28], [P - 1, P])
    batch = forward_capture(model, [ids] * 20, [20, 28], [P - 1, P])
    d1 = float((a["states"][28] - b["states"][28]).abs().max())
    xs = batch["states"][28]
    rel = float(((xs - xs[0:1]).norm(dim=-1) / xs[0:1].norm(dim=-1)).max())
    rel_b1_vs_batch = float(((xs - a["states"][28]).norm(dim=-1) / a["states"][28].norm(dim=-1)).max())
    out = {"decode_rows_identical_given_same_uniforms": all(same), "n_pairs": len(same),
           "batch1_repeat_max_abs_diff_block28": d1,
           "batch20_identical_rows_max_rel_l2_diff_block28": rel,
           "batch20_vs_batch1_max_rel_l2_diff_block28": rel_b1_vs_batch,
           "note": "(a) decode at M=20 is position independent, so CRN coupling across arms is exact; (b)/(c) teacher "
                   "forcing must run at batch 1 for states to depend only on the prefix"}
    write_json(RESULTS_DIR / "unit_tests_u1b.json", out)
    logger.info(f"U1b: {out}")


def gpu3(deadline: float) -> None:
    """EXPLORATORY (not in the frozen rules): 12 more random directions at alpha 1 on T2, T1, T03 -- where does ADD's
    avoidance sit in the distribution of random-direction effects? Same construction, CRN slots k 0-9."""
    import torch

    from engine import load_model
    from prompts import load_prompts
    from sampling import K10, run_task_phase

    tok, model = load_model()
    prompts = load_prompts()
    if not (RESULTS_DIR / "unit_tests_u1b.json").exists():
        u1b(model, tok, prompts)
    # S8 re-extraction at batch 1 (the plan's specification; see unit_tests_u1b.json and README)
    if not (RESULTS_DIR / "s8_batch1_done.json").exists():
        from gpu2 import _raw_by_arm
        from states import stage_states_b1

        stage_states_b1(model, prompts, _raw_by_arm(), list(SAMPLED_TASKS))
        write_json(RESULTS_DIR / "s8_batch1_done.json", {"utc": utc_now()})
    # conditional causal patch (9.2): only for tasks where C2e found a locus (k*, L*)
    c2e_p = RESULTS_DIR / "c2e.json"
    if c2e_p.exists():
        from patch import analyse_patch, run_patch

        for t, v in read_json(c2e_p)["primary"].items():
            if v.get("locus") and not (RESULTS_DIR / f"c2e_patch_{t}.json").exists():
                run_patch(model, tok, prompts, t, v["locus"]["k"], v["locus"]["block"])
                analyse_patch(t)
    # exploratory C2e extension: states at generated positions 24-96 (the frozen window ends before the fork)
    from c2e_ext import extract, run_all_ext

    try:
        extract(model, prompts)
    except Exception as e:  # noqa: BLE001 - exploratory; never block the remaining stage
        logger.exception(f"C2e extension extraction failed: {e}")
    batches = [[(f"RAND{a}_a1.0", K10), (f"RAND{b}_a1.0", K10)] for a, b in zip(EXTRA_SEEDS[::2], EXTRA_SEEDS[1::2])]
    for t in ("T2", "T1", "T03"):
        if time.time() > deadline:
            break
        n = run_task_phase(model, tok, prompts, t, batches, "X1", deadline=deadline)
        logger.info(f"X1 extra random directions {t}: {n} batches")
    torch.cuda.empty_cache()
    try:
        if not (RESULTS_DIR / "c2e_extension.json").exists():
            run_all_ext()
    except Exception as e:  # noqa: BLE001
        logger.exception(f"C2e extension decoders failed: {e}")
    write_json(RESULTS_DIR / "gpu3_done.json", {"utc": utc_now()})


def c2e_stage(deadline: float) -> None:
    """9.2 C2e decoders on the GPU (primary per sampled task; secondary archive-pooled analysis for T1/T2)."""
    from analysis.c2e import run_task

    out_p = RESULTS_DIR / "c2e.json"
    res = read_json(out_p) if out_p.exists() else {"primary": {}, "secondary_archive_pooled": {}}
    for t in SAMPLED_TASKS:
        if t in res["primary"] or time.time() > deadline:
            continue
        t0 = time.time()
        res["primary"][t] = run_task(t, n_perm=500 if t in ("T1", "T2") else 200)
        res["primary"][t]["seconds"] = time.time() - t0
        write_json(out_p, res)
        logger.info(f"C2e {t}: {res['primary'][t].get('status')} locus={res['primary'][t].get('locus')} "
                    f"({time.time() - t0:.0f}s)")
    for t in ("T1", "T2"):
        if t in res["secondary_archive_pooled"] or time.time() > deadline:
            continue
        r = run_task(t, n_perm=200, archive=True)
        r["label"] = "secondary, archive-pooled (exp8 arm a + exp12 fresh pool; blocks 8-28 every 2nd block)"
        res["secondary_archive_pooled"][t] = r
        write_json(out_p, res)
    res["n_perm"] = {"T1": 500, "T2": 500, "bench": 200, "archive": 200}
    write_json(out_p, res)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage")
    ap.add_argument("--minutes", type=float, default=60.0, help="deadline for required work (from now)")
    ap.add_argument("--optional-minutes", type=float, default=0.0, help="extra time allowed for optional arms")
    a = ap.parse_args()
    setup_logging(a.stage)
    if a.stage in ("prompts", "label", "commit2", "analyze"):
        set_ram_limit(24)  # never on CUDA processes: the driver reserves a large virtual address space
    now = time.time()
    deadline = now + a.minutes * 60
    optional_until = now + a.optional_minutes * 60
    logger.info(f"stage {a.stage}: deadline in {a.minutes:.0f} min, optional until +{a.optional_minutes:.0f} min")
    if a.stage == "prompts":
        from prompts import stage_prompts
        stage_prompts()
    elif a.stage == "gpu1":
        gpu1(deadline, optional_until)
    elif a.stage == "label":
        from label_worker import run_worker
        run_worker(follow=True, deadline=deadline)
    elif a.stage == "commit2":
        from analysis.commit2 import stage_commit2
        stage_commit2()
    elif a.stage == "gpu2":
        from gpu2 import gpu2
        gpu2(deadline, optional_until)
    elif a.stage == "s8c":
        s8c()
    elif a.stage == "gpu3":
        gpu3(deadline)
    elif a.stage == "c2e":
        c2e_stage(deadline)
    elif a.stage == "zerog":
        from zerog import stage_zerog
        stage_zerog(deadline)
    elif a.stage == "analyze":
        from analysis.run_all import run_all
        run_all()
    else:
        raise SystemExit(f"unknown stage {a.stage}")


if __name__ == "__main__":
    logger.catch(reraise=True)(main)()
