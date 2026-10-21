#!/usr/bin/env python3
"""GPU runner of artifact E: device rule + memory probe, GPU tests, smoke run, the generation queue (engine-check
gate, factorial blocks, unit cross, T03, dither, REAL cells) and the mechanism readouts.

Usage: python src/run_e.py --stage {tests,smoke,gen,readouts} [--deadline-min M] [--B 20]
One model load per process; families are installed from the CPU copy of the bf16 decoder linears.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import numpy as np
import torch
from loguru import logger

from cfg import TEMPLATE_IDS, V_BLOCKS, append_jsonl, read_jsonl, setup_logging, utc_now, write_json
from cfg_e import (DATA_DIR, K10, POP_SEEDS, PRED_DIR, RAW_E, RESULTS_DIR, ROOT, TIMING_E, load_json, pop_arm,
                   sample_id)

PAIR_TWIN = [("TWIN", K10), ("PN_a0.5", K10)]
PAIR_PN = [("PN_a1", K10), ("PN_a2", K10)]
PAIR_UNIT = [("PNF_a1", K10), ("PNF_a2", K10)]


def pair_dither(v: int) -> list[tuple[str, list[int]]]:
    return [(f"DITHER_TWIN_v{v}", K10), (f"DITHER_PN2_v{v}", K10)]


def pop_batches(B: int, k_slots: list[int] = [0, 1], seeds: list[int] = POP_SEEDS) -> list[list[tuple[str, list[int]]]]:
    per = B // len(k_slots)
    return [[(pop_arm(s), list(k_slots)) for s in seeds[i:i + per]] for i in range(0, len(seeds), per)]


def split_spec(spec: list[tuple[str, list[int]]], B: int) -> list[list[tuple[str, list[int]]]]:
    """B = 20: exp19 pairs as they are; B = 10: one 10-slot block per batch (device rule)."""
    if sum(len(k) for _, k in spec) == B:
        return [spec]
    out = []
    for arm, ks in spec:
        for i in range(0, len(ks), B):
            out.append([(arm, ks[i:i + B])])
    return out


# ---------------------------------------------------------------------------------------------- queue
def build_queue(B: int, real: bool) -> list[dict[str, Any]]:
    """Ordered work items {block, precision, task, w, spec, tag, prio}. prio 0 = never drop; higher = dropped first
    (time-only drop order: 8 REAL population cells, 7 REAL T03 [extras beyond the plan], then the frozen order 6 dither ii, 5 dither i, 4 unit cross, 3 T03 middle precisions, 2 POP middle k1)."""
    Q: list[dict[str, Any]] = []

    def add(block, prec, task, ws, specs, tag, prio=0):
        for w in ws:
            for spec in specs:
                for s in split_spec(spec, B):
                    Q.append({"block": block, "precision": prec, "task": task, "w": w, "spec": s, "tag": tag,
                              "prio": prio})

    W = TEMPLATE_IDS
    # Stage D: REAL engine check at exp19's exact layout (T2 W1-W3), then the EMU gate rows (first W8A8 rows)
    if real:
        add("D_real", "W8A8REAL", "T2", ["W1", "W2", "W3"], [PAIR_TWIN, PAIR_PN], "engine_check_real")
    # BLOCK 1 (FAM_W8): W8A8 core (T2 first: holds the gate), W8A16 core, T03, unit cross W8A8
    for prec in ("W8A8", "W8A16"):
        for task in ("T2", "T10"):
            add("B1", prec, task, W, [PAIR_TWIN, PAIR_PN], "core")
        for task in ("T2", "T10"):
            pb = pop_batches(B, [0, 1])
            if prec == "W8A8":
                add("B1", prec, task, W, pb, "pop40")
            else:   # middle precision: k0 batches never dropped, k1 batches droppable (POP down to N 5)
                add("B1", prec, task, W, pop_batches(B, [0]), "pop40_k0")
                add("B1", prec, task, W, pop_batches(B, [1]), "pop40_k1", prio=2)
    add("B1", "W8A8", "T03", W, [PAIR_TWIN, PAIR_PN], "t03")
    add("B1", "W8A16", "T03", W, [PAIR_TWIN, PAIR_PN], "t03", prio=3)
    for task in ("T10", "T2"):
        add("B1", "W8A8", task, W, [PAIR_UNIT], "unit_cross", prio=4)
    # BLOCK 2 (FAM_W16): W16A16 core (+ anchor), W16A8 core, T03, unit cross W16A16
    for prec in ("W16A16", "W16A8"):
        for task in ("T2", "T10"):
            add("B2", prec, task, W, [PAIR_TWIN, PAIR_PN], "core")
        for task in ("T2", "T10"):
            if prec == "W16A16":
                add("B2", prec, task, W, pop_batches(B, [0, 1]), "pop40")
            else:
                add("B2", prec, task, W, pop_batches(B, [0]), "pop40_k0")
                add("B2", prec, task, W, pop_batches(B, [1]), "pop40_k1", prio=2)
    add("B2", "W16A16", "T03", W, [PAIR_TWIN, PAIR_PN], "t03")
    add("B2", "W16A8", "T03", W, [PAIR_TWIN, PAIR_PN], "t03", prio=3)
    for task in ("T10", "T2"):
        add("B2", "W16A16", task, W, [PAIR_UNIT], "unit_cross", prio=4)
    # BLOCK 3 (FAM_W16): dither (i) then (ii)
    for v, pr in ((1, 5), (2, 6)):
        for task in ("T10", "T2"):
            add("B3", "W16A16", task, W, [pair_dither(v)], f"dither_v{v}", prio=pr)
    # BLOCK 4 (REAL): REAL vs EMU cells (T2 W4-W5, T10, T03) and the REAL population arm
    if real:
        add("B4", "W8A8REAL", "T2", ["W4", "W5"], [PAIR_TWIN, PAIR_PN], "real_cells")
        add("B4", "W8A8REAL", "T10", W, [PAIR_TWIN, PAIR_PN], "real_cells")
        add("B4", "W8A8REAL", "T03", W, [PAIR_TWIN, PAIR_PN], "real_cells", prio=7)
        for task in ("T10", "T2"):
            add("B4", "W8A8REAL", task, W, pop_batches(B, [0, 1]), "real_pop40", prio=8)
    # POST-HOC (added after commit #0, run after the frozen queue): replication of iteration 5's PN cells
    for prec in ("W16A16", "W8A8"):
        for task in ("T10", "T2"):
            add("P1", prec, task, W, [[("IT5_a1", K10), ("IT5_a2", K10)]], "posthoc_it5", prio=9)
    return Q


def item_ids(it: dict[str, Any]) -> list[str]:
    return [sample_id(it["task"], it["precision"], arm, it["w"], k) for arm, ks in it["spec"] for k in ks]


# ---------------------------------------------------------------------------------------------- setup
def load_all() -> tuple[Any, Any, Any, dict]:
    from prompts_v4 import load_prompts
    from qlinear import load_model_cpu

    tok, model, fm = load_model_cpu()
    torch.cuda.set_per_process_memory_fraction(0.96, 0)
    return tok, model, fm, load_prompts()


def r_q_table() -> dict[int, float]:
    d = load_json(ROOT / "inputs" / "exp23" / "results" / "qwen_ratio.json")["r_Q"]
    return {int(l): float(v["median"]) for l, v in d.items() if int(l) in V_BLOCKS}


def _blas() -> str:
    try:
        return str(torch.backends.cuda.preferred_blas_library())
    except (AttributeError, RuntimeError):
        return "unknown"


def device_rule(model: Any, tok: Any, prompts: dict, fm: Any) -> dict[str, Any]:
    """Memory probe under FAM_W8 with ACT_Q on (the most memory-hungry configuration) at the longest prompt."""
    from engine_e import TaskContextE, run_batch_e

    p = PRED_DIR / "device_rule.json"
    if p.exists():
        return load_json(p)
    cap = torch.cuda.get_device_capability(0)
    props = torch.cuda.get_device_properties(0)
    rule: dict[str, Any] = {"device": torch.cuda.get_device_name(0), "capability": list(cap),
                            "vram_total_gb": round(props.total_memory / 1e9, 2), "torch": torch.__version__,
                            "cuda": torch.version.cuda, "cublas": _blas(),
                            "transformers": __import__("transformers").__version__,
                            "driver": os.popen("nvidia-smi --query-gpu=driver_version --format=csv,noheader").read().strip(),
                            "W8A8_REAL_AVAILABLE": tuple(cap) >= (8, 9), "probe": [], "utc": utc_now()}
    fm.set_precision("W8A8")
    lens = {w: prompts[("T2", w, "twin")]["P"] for w in TEMPLATE_IDS}
    wmax = max(lens, key=lens.get)
    chosen = None
    for B in (20, 10, 5):
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        try:
            ctx = TaskContextE(model, tok, prompts, "T2", "W8A8")
            half = B // 2
            spec = [("TWIN", list(range(half))), ("PN_a2", list(range(half)))]
            run_batch_e(ctx, wmax, spec, f"probe:B{B}", B, write=False, stage="probe")
            peak = torch.cuda.max_memory_reserved()
            free_after = props.total_memory - peak
            ok = free_after >= 1.0 * 1024 ** 3
            rule["probe"].append({"B": B, "peak_reserved_gb": round(peak / 1e9, 2),
                                  "free_at_peak_gib": round(free_after / 1024 ** 3, 2), "pass": ok})
            ctx.clean.clear()
            del ctx
            if ok:
                chosen = B
                break
        except torch.cuda.OutOfMemoryError as e:
            rule["probe"].append({"B": B, "oom": str(e)[:200], "pass": False})
            gc.collect()
            torch.cuda.empty_cache()
    rule["B"] = chosen
    rule["batch_composition"] = ("one (task, template, prompt ids) per batch; B = 20 -> exp19 pairs [TWIN k0-9 + "
                                 "PN_a0.5 k0-9], [PN_a1 k0-9 + PN_a2 k0-9]; 40-direction arm: 10 directions x k0-1")
    write_json(p, rule)
    logger.info(f"device rule: {rule}")
    return rule


# ---------------------------------------------------------------------------------------------- generation
def run_queue(model: Any, tok: Any, prompts: dict, fm: Any, B: int, real: bool, deadline: float,
              only_tags: set[str] | None = None, max_items: int | None = None) -> dict[str, Any]:
    from engine_e import TaskContextE, done_ids, run_batch_e

    Q = build_queue(B, real)
    if only_tags:
        Q = [it for it in Q if it["tag"] in only_tags]
    done = done_ids()
    todo = [it for it in Q if not all(s in done for s in item_ids(it))]
    logger.info(f"queue: {len(Q)} items, {len(todo)} to run (B = {B})")
    dropped_prio: set[int] = set()
    sec_hist: list[float] = []
    ctxs: dict[tuple[str, str], Any] = {}
    n_run = 0
    t_start = time.time()
    rq = r_q_table()
    for i, it in enumerate(todo):
        if max_items is not None and n_run >= max_items:
            break
        # time-only drop rule: extrapolate the remaining never-dropped + kept work
        if len(sec_hist) >= 10:
            per = float(np.mean(sec_hist))            # mean over every batch run so far (stable estimate)
            for pr in (9, 8, 7, 6, 5, 4, 3, 2):          # REAL extras beyond the plan first, then the plan's order
                rest = [x for x in todo[i:] if x["prio"] not in dropped_prio]
                if time.time() + per * len(rest) * 1.05 <= deadline:
                    break
                if pr not in dropped_prio and any(x["prio"] == pr for x in todo[i:]):
                    dropped_prio.add(pr)
                    append_jsonl(RESULTS_DIR / "drops.jsonl", [{"utc": utc_now(), "dropped_prio": pr,
                                                               "reason": "time extrapolation",
                                                               "sec_per_batch": per, "remaining": len(rest)}])
                    logger.warning(f"DROP prio {pr} (time): {per:.1f}s/batch x {len(rest)} remaining")
        if it["prio"] in dropped_prio:
            continue
        if time.time() > deadline:
            logger.warning("deadline reached; stopping queue")
            break
        prec, task = it["precision"], it["task"]
        if fm.precision != prec:
            ctxs.clear()
            gc.collect()
            torch.cuda.empty_cache()
            fm.set_precision(prec)
        key = (prec, task)
        if key not in ctxs:
            ctxs.clear()
            torch.cuda.empty_cache()
            ctxs[key] = TaskContextE(model, tok, prompts, task, prec)
        ctx = ctxs[key]
        if any(arm.startswith("PNF_") for arm, _ in it["spec"]) and ctx.n_free is None:
            nf = ctx.banfree_unit(rq, TEMPLATE_IDS)
            np.save(RESULTS_DIR / f"unit_banfree_{task}_{prec}.npy", nf)
        dh = None
        if any(arm.startswith("DITHER_") for arm, _ in it["spec"]):
            from dither import DitherHooks
            assert prec == "W16A16"
            dh = DitherHooks(model)
        try:
            bid = f"{it['block']}:{it['tag']}:{prec}:{task}:{it['w']}:{'+'.join(a for a, _ in it['spec'])[:60]}"
            t0 = time.time()
            run_batch_e(ctx, it["w"], it["spec"], bid, B, stage=it["tag"])
            sec_hist.append(time.time() - t0)
            n_run += 1
        finally:
            if dh is not None:
                dh.remove()
        if n_run % 10 == 0:
            el = time.time() - t_start
            logger.info(f"progress {n_run} batches in {el:.0f}s; median {np.median(sec_hist[-20:]):.1f}s/batch; "
                        f"peak VRAM {torch.cuda.max_memory_allocated() / 1e9:.1f} GB")
    res = {"n_batches": n_run, "seconds": round(time.time() - t_start, 1), "dropped_prio": sorted(dropped_prio),
           "median_sec_per_batch": float(np.median(sec_hist)) if sec_hist else None, "utc": utc_now()}
    append_jsonl(RESULTS_DIR / "queue_runs.jsonl", [res])
    return res


def run_smoke(model: Any, tok: Any, prompts: dict, fm: Any, B: int) -> None:
    """Smoke run (rows to data/smoke_*.jsonl, never mixed with the factorial): every arm type end to end."""
    import engine_e
    from dither import DitherHooks
    from engine_e import TaskContextE, run_batch_e

    engine_e.RAW_E = DATA_DIR / "smoke_raw.jsonl"
    engine_e.REALISED_E = DATA_DIR / "smoke_realised.jsonl"
    engine_e.TIMING_E = RESULTS_DIR / "smoke_timing.jsonl"
    if engine_e.RAW_E.exists():
        logger.info("smoke rows exist; skipping")
        return
    q = B // 5
    fm.set_precision("W8A8")
    ctx = TaskContextE(model, tok, prompts, "T2", "W8A8")
    ctx.banfree_unit(r_q_table(), TEMPLATE_IDS)
    spec = [("TWIN", list(range(q))), ("PN_a1", list(range(q))), ("PN_a2", list(range(q))),
            (pop_arm(9101), list(range(q // 2))), (pop_arm(9102), list(range(q - q // 2))), ("PNF_a2", list(range(q)))]
    run_batch_e(ctx, "W1", spec, "smoke:W8A8:T2:W1", B, stage="smoke")
    fm.set_precision("W16A16")
    ctx = TaskContextE(model, tok, prompts, "T10", "W16A16")
    dh = DitherHooks(model)
    try:
        run_batch_e(ctx, "W1", [("DITHER_TWIN_v2", list(range(B // 2))), ("DITHER_PN2_v2", list(range(B // 2)))],
                    "smoke:W16A16:T10:W1:dither", B, stage="smoke")
    finally:
        dh.remove()
    ctx = TaskContextE(model, tok, prompts, "T03", "W16A16")
    run_batch_e(ctx, "W1", [("TWIN", list(range(B // 2))), ("PN_a2", list(range(B // 2)))], "smoke:W16A16:T03:W1",
                B, stage="smoke")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["tests", "gen", "readouts", "probe", "smoke"])
    ap.add_argument("--deadline-min", type=float, default=600.0, help="minutes from now")
    ap.add_argument("--tags", default=None)
    ap.add_argument("--max-items", type=int, default=None)
    ap.add_argument("--precisions", default="W16A16,W16A16mm,W16A8,W8A8,W8A16,W8A8REAL")
    args = ap.parse_args()
    setup_logging(f"run_e_{args.stage}")
    deadline = time.time() + 60 * args.deadline_min
    tok, model, fm, prompts = load_all()
    rule = device_rule(model, tok, prompts, fm)
    B, real = int(rule["B"]), bool(rule["W8A8_REAL_AVAILABLE"])
    if args.stage == "probe":
        return
    if args.stage == "tests":
        from tests_gpu import run_all

        res = run_all(model, tok, prompts, fm, B, real)
        write_json(RESULTS_DIR / "tests_gpu.json", res)
        logger.info(f"GPU tests all_pass={res['all_pass']}")
        return
    if args.stage == "smoke":
        run_smoke(model, tok, prompts, fm, B)
        return
    if args.stage == "gen":
        tags = set(args.tags.split(",")) if args.tags else None
        res = run_queue(model, tok, prompts, fm, B, real, deadline, only_tags=tags, max_items=args.max_items)
        logger.info(f"queue result: {res}")
        return
    if args.stage == "readouts":
        from readouts import run_readouts

        precs = [p for p in args.precisions.split(",") if p != "W8A8REAL" or real]
        out = {}
        for prec in precs:
            out[prec] = run_readouts(model, tok, prompts, fm, prec, ("T10", "T2"), TEMPLATE_IDS, K10, deadline)
        append_jsonl(RESULTS_DIR / "readouts_runs.jsonl", [{"utc": utc_now(), **out}])
        return


if __name__ == "__main__":
    main()
