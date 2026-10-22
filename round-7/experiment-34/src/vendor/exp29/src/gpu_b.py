#!/usr/bin/env python3
"""GPU process on weight set B (bf16 weights on the GPU, embeddings on the CPU): engines d (BF16) and c (W16A8).

Order (committed drop order applied against --deadline-min):
  0  memory probe -> B (largest batch whose KV buffer of P_max + cap tokens fits with headroom) and unit tests
     U3/U4/U5 for d and c, U6 (capped sampler == vendored sampler on rows that finish within cap)
  1  d: twins k 0-9 + POP alpha 2 screen (40 dirs, k 0-1) [+ POSCTRL 9004 alpha 1 on T2, k 0-3]   [never dropped]
  2  d: confirmations (k 2-5) of every screen-passing direction                                     [never dropped]
  3  c: twins + screen (+ POSCTRL)
  4  PN alpha 1, 2 (exp19 slots W1-W5 x k 0-9, per-sample seeds) for d, then c                       [protected]
  5  teacher-forced diagnostics (T10 first) for d and c
  6  c: confirmations (dropped last, per the committed drop order; else screen-level E for c, flagged)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import torch  # noqa: E402
from loguru import logger  # noqa: E402

import c6  # noqa: E402,F401
from c6 import (DEFAULTS, K_CONFIRM, K_PN, K_SCREEN, K_TWIN, POSCTRL_SEED, RESULTS, SEEDS_POP, read_jsonl,  # noqa: E402
                setup_logging, utc_now, write_json)

KV_TOKEN_BYTES = 36 * 2 * 8 * 128 * 2


def catalogue(task: str) -> set[str]:
    import cfg4  # noqa: F401
    from screen import catalogue as cat
    return set(cat(task))


def probe_B(model: Any, tok: Any, prompts: dict, cap: int, headroom_mib: float = 350.0) -> dict[str, Any]:
    """Largest B <= 20 such that a PN batch (one prefill group per row, the hungriest layout) of the longest prompt
    runs with a cap-token KV buffer while `headroom_mib` stays free."""
    import engines as EN
    from gen import Runner

    EN.set_mode("c")
    P = max(prompts[f"{t}|twin|-|{w}|-"]["P"] for t in ("T10", "T2") for w in ("W1", "W2", "W3", "W4", "W5"))
    free0, total = torch.cuda.mem_get_info(0)
    tried = {}
    for B in (16, 14, 12, 11, 10, 9, 8, 7, 6, 5, 4):
        need = B * KV_TOKEN_BYTES * (P + cap + 1)
        if need > free0 - headroom_mib * 2 ** 20:
            tried[B] = "kv buffer alone exceeds free memory"
            continue
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        filler = None
        try:
            from ctx4 import TaskCtx
            # reserve the KV buffer the real batches will allocate, then run a short PN batch on top of it
            filler = torch.empty(int(need), dtype=torch.uint8, device="cuda")
            r = Runner(model, tok, prompts, "c", B=B, cap=8)
            ctx = TaskCtx(model, prompts, "T2")
            groups, meta, recs = r._groups(ctx, "W5", [("PN_a2", list(range(B)))])
            import sampler6
            sampler6.sample(model, tok, groups, fence="path", max_new=8, cap=8)
            del groups
            ctx.release()
            peak = torch.cuda.max_memory_allocated(0)
            free_after = total - peak
            tried[B] = {"peak_gib": peak / 2 ** 30, "free_at_peak_mib": free_after / 2 ** 20}
            if free_after / 2 ** 20 >= headroom_mib:
                del filler
                torch.cuda.empty_cache()
                return {"B": B, "cap": cap, "P_max": P, "free_before_gib": free0 / 2 ** 30, "tried": tried,
                        "headroom_mib": headroom_mib}
        except torch.cuda.OutOfMemoryError as e:
            tried[B] = f"OOM: {str(e)[:80]}"
        finally:
            filler = None
            torch.cuda.empty_cache()
    return {"B": 4, "cap": cap, "P_max": P, "tried": tried, "note": "fallback"}


def unit_tests_b(model: Any, tok: Any, prompts: dict, B: int, cap: int) -> dict[str, Any]:
    import engines as EN
    import gpu_tests6 as GT
    import sampler6
    from ctx4 import TaskCtx, ban_unit, push_spec, rand_dir
    from engine4 import sample, u_stream

    out: dict[str, Any] = {"utc": utc_now(), "weight_set": "B", "B": B, "cap": cap}
    for m in ("d", "c"):
        out[f"U4_{m}"] = GT.u4(model, prompts, m)
        out[f"U3_U5_{m}"] = GT.u3_u5(model, tok, prompts, m, B=B)
        logger.info(f"U4 {m} {out[f'U4_{m}']} U3/U5 {out[f'U3_U5_{m}']}")
    # max |d logit| of one decode step over batch sizes 1, B, 10, 20 (short cache -> fits)
    for m in ("d", "c"):
        EN.set_mode(m)
        ctx = TaskCtx(model, prompts, "T10")
        tw = ctx.twin("W1")
        from engine import prealloc_cache
        import engine as VE
        P = tw["pre"]["P"]
        rows = {}
        first = 785  # a fixed token id fed at position P (any id works for a numerics probe)
        for bs in sorted({1, 2, B}):
            kv = [(K.expand(bs, -1, -1, -1).contiguous(), V.expand(bs, -1, -1, -1).contiguous()) for K, V in tw["pre"]["kv"]]
            cache = prealloc_cache(kv, P + 2)
            VE.clear_act_cache()
            hh = model.model(input_ids=torch.full((bs, 1), first, device=model.device, dtype=torch.long),
                             past_key_values=cache, position_ids=torch.full((bs, 1), P, device=model.device,
                                                                            dtype=torch.long), use_cache=True).last_hidden_state
            rows[bs] = model.lm_head(hh[:, -1]).float()[0].clone()
            del cache, kv
        out[f"dlogit_vs_B_{m}"] = {str(bs): float((v - rows[B]).abs().max()) for bs, v in rows.items()}
        ctx.release()
    # U6: capped sampler == vendored sampler (full buffer) on a 4-row batch; and the overflow path runs
    EN.set_mode("d")
    ctx = TaskCtx(model, prompts, "T10")
    tw = ctx.twin("W2")
    p1, _ = ctx.arm_prefill("W2", push_spec(model.device, rand_dir(9105), ban_unit("T10"), 2.0))
    g = [{"pre": tw["pre"], "us": [u_stream("T10", "W2", k) for k in (0, 1)]},
         {"pre": p1, "us": [u_stream("T10", "W2", k) for k in (0, 1)]}]
    ref = sample(model, tok, g, fence="bench", max_new=1024)
    capd = sampler6.sample(model, tok, g, fence="bench", max_new=1024, cap=cap)
    ovf = sampler6.sample(model, tok, g, fence="bench", max_new=1024, cap=24)
    out["U6_capped_equals_vendored"] = all(a["token_ids"] == b["token_ids"] for a, b in zip(ref, capd))
    out["U6_overflow_path"] = {"rows_identical_to_vendored": sum(a["token_ids"] == b["token_ids"] for a, b in zip(ref, ovf)),
                               "n": len(ref), "overflow_steps": [b["overflow_at_step"] for b in ovf]}
    ctx.release()
    return out


def run_engine_screen(model, tok, prompts, m: str, B: int, cap: int, deadline: float) -> None:
    import engines as EN
    from gen import Runner

    EN.set_mode(m)
    run = Runner(model, tok, prompts, m, B=B, cap=cap)
    for task in ("T10", "T2"):
        cells = [("TWIN", K_TWIN)] + [(f"POP_d{s}_a2.0", K_SCREEN) for s in SEEDS_POP]
        if task == "T2":
            cells.append((f"POP_d{POSCTRL_SEED}_a1.0", [0, 1, 2, 3]))
        run.run_cells(task, cells, "S1S2_screen", deadline=deadline)


def run_engine_confirm(model, tok, prompts, m: str, B: int, cap: int, deadline: float) -> dict[str, list[int]]:
    import engines as EN
    from escape import needs_confirmation
    from gen import Runner
    from rows6 import engine_rows, wait_labels

    EN.set_mode(m)
    run = Runner(model, tok, prompts, m, B=B, cap=cap)
    todo = {}
    for task in ("T10", "T2"):
        wait_labels(m, task, timeout=900)
        rows = engine_rows(m, task)
        dirs = needs_confirmation(rows, SEEDS_POP, catalogue(task), DEFAULTS[task], 2.0)
        todo[task] = dirs
        logger.info(f"[{m}] {task}: {len(dirs)} screen-passing directions to confirm: {dirs}")
        if dirs:
            run.run_cells(task, [(f"POP_d{s}_a2.0", K_CONFIRM) for s in dirs], "S2S3_confirm", deadline=deadline)
    return todo


def run_pn(model, tok, prompts, m: str, B: int, cap: int, deadline: float) -> None:
    import engines as EN
    from gen import Runner

    EN.set_mode(m)
    run = Runner(model, tok, prompts, m, B=B, cap=cap)
    for task in ("T10", "T2"):
        run.run_cells(task, [("PN_a1", K_PN), ("PN_a2", K_PN)], "S4_PN", deadline=deadline)


def sec_per_program(m: str) -> float:
    t = [r for r in read_jsonl(RESULTS / "timing.jsonl") if r["engine"] == m]
    if not t:
        return 4.0
    return sum(r["seconds"] for r in t) / sum(r["B"] for r in t)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deadline-min", type=float, default=175.0)
    ap.add_argument("--cap", type=int, default=448)
    ap.add_argument("--skip-tests", action="store_true")
    args = ap.parse_args()
    setup_logging("gpu_b")
    torch.backends.cuda.matmul.allow_tf32 = False
    t_start = time.time()
    deadline = t_start + args.deadline_min * 60
    import engines as EN
    from prompts4 import load_prompts4

    tok, model = EN.load_b()
    prompts = load_prompts4()
    log: dict[str, Any] = {"start_utc": utc_now(), "deadline_min": args.deadline_min, "stages": []}
    pr = probe_B(model, tok, prompts, args.cap)
    B, cap = pr["B"], pr["cap"]
    log["probe"] = pr
    write_json(RESULTS / "gpu_b_log.json", log)
    logger.info(f"memory probe: B = {B}, cap = {cap}: {pr}")
    if not args.skip_tests:
        try:
            ut = unit_tests_b(model, tok, prompts, B, cap)
            write_json(RESULTS / "unit_tests_b.json", ut)
            logger.info(f"unit tests B: U6 {ut['U6_capped_equals_vendored']} {ut['U6_overflow_path']} "
                        f"dlogit d {ut['dlogit_vs_B_d']} c {ut['dlogit_vs_B_c']}")
        except Exception as e:  # noqa: BLE001 - a failing non-decisive test is recorded, never fatal
            logger.exception(f"unit tests B failed: {e}")
            write_json(RESULTS / "unit_tests_b.json", {"error": str(e)})
        torch.cuda.empty_cache()

    def stage(name: str, fn, *a) -> None:
        t0 = time.time()
        if time.time() > deadline:
            log["stages"].append({"stage": name, "status": "dropped (deadline)"})
            write_json(RESULTS / "gpu_b_log.json", log)
            return
        res = fn(*a)
        log["stages"].append({"stage": name, "status": "done", "minutes": (time.time() - t0) / 60,
                              "result": res, "utc": utc_now()})
        write_json(RESULTS / "gpu_b_log.json", log)

    stage("d screen", run_engine_screen, model, tok, prompts, "d", B, cap, deadline)
    stage("d confirm", run_engine_confirm, model, tok, prompts, "d", B, cap, deadline)
    stage("c screen", run_engine_screen, model, tok, prompts, "c", B, cap, deadline)
    stage("d PN", run_pn, model, tok, prompts, "d", B, cap, deadline)
    stage("c PN", run_pn, model, tok, prompts, "c", B, cap, deadline)
    try:
        import diag6
        stage("diagnostics B", diag6.run_weight_set, model, tok, prompts, ("d", "c"), deadline)
    except ImportError as e:
        log["stages"].append({"stage": "diagnostics B", "status": f"not available: {e}"})
    stage("c confirm", run_engine_confirm, model, tok, prompts, "c", B, cap, deadline)
    log["end_utc"] = utc_now()
    log["sec_per_program"] = {m: sec_per_program(m) for m in ("d", "c")}
    write_json(RESULTS / "gpu_b_log.json", log)
    logger.info("gpu_b done")


if __name__ == "__main__":
    main()
