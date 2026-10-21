#!/usr/bin/env python3
"""GPU orchestration: model load, GPU unit tests U1-U6, the R2 ban-free unit (0.7), the engine check (3), stage 10,
then (after the commitment flag exists) stage 100, the timing extrapolation and the full priority queue.

Usage: python src/gpu_stage.py --deadline-utc <ISO> [--skip-tests]
Every step is resumable: finished steps leave a result file and are skipped on restart.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import (ARMS, BENCH12, DATA_DIR, E17, E6_TASKS, HELDOUT, MAX_NEW_TOKENS, P3_TASKS, PATH_TASKS, PRED_DIR,
                 RESULTS_DIR, TEMPLATE_IDS, V_BLOCKS, append_deviation, append_jsonl, read_json, read_jsonl,
                 set_ram_limit, setup_logging, utc_now, write_json)
from engine_v4 import (_inverse_cdf, load_model, prefill, sample, sample_exp17, step_probs, u_stream)
from prompts_v4 import load_prompts, prompt_for
from sampling_v4 import (K10, RAW, TaskContext, load_norms, run_batch, run_queue)

COMMIT_FLAG = PRED_DIR / "COMMITTED"
EC_RAW = DATA_DIR / "engine_check_raw.jsonl"
UT = RESULTS_DIR / "unit_tests_gpu.json"
TEST_ARMS = {
    "PN_a0": {"prompt": "twin", "T": 1.0, "top_k": 0, "min_p": 0.0, "alpha": 0.0, "knob": "TEST"},
}


def _extract_bench(text: str) -> str | None:
    from cfg import E11

    if str(E11) not in sys.path:
        sys.path.insert(0, str(E11))
    from bench.common.harness import extract_code

    return extract_code(text)


def _extract_path(text: str) -> str | None:
    from cfg import SUITE

    if str(SUITE) not in sys.path:
        sys.path.insert(0, str(SUITE))
    from labeller.extract import extract_code

    return extract_code(text)[0]


# ------------------------------------------------------------------------------------------------ unit tests
def gpu_tests(model: Any, tok: Any, prompts: dict) -> dict[str, Any]:
    if UT.exists():
        return read_json(UT)
    res: dict[str, Any] = {"utc": utc_now()}
    defs = {**ARMS, **TEST_ARMS}
    K20 = list(range(20))
    ctx = TaskContext(model, tok, prompts, "T03", log_realised=True)
    # U1 CRN determinism + bit-identity of the extended sampler with exp17's sampler (T=1, untruncated)
    a = run_batch(ctx, "W1", [("TWIN", K20)], "U1a", fence=None, write=False)
    b = run_batch(ctx, "W1", [("TWIN", K20)], "U1b", fence=None, write=False)
    pre = ctx.clean_prefill("W1", "twin")["pre"]
    old = sample_exp17(model, [{"pre": pre, "us": [u_stream("T03", "W1", k) for k in K20]}])
    res["U1_determinism"] = sum(x["token_ids"] == y["token_ids"] for x, y in zip(a, b))
    res["U1_vs_exp17_sampler"] = sum(x["token_ids"] == y["token_ids"] for x, y in zip(a, old))
    # U2 exact coupling at alpha 0 (fresh directions), and with different batch-mates
    c = run_batch(ctx, "W1", [("PN_a0", K20)], "U2a", fence=None, arm_defs=defs, write=False)
    res["U2_alpha0_vs_twin_20"] = sum(x["token_ids"] == y["token_ids"] for x, y in zip(a, c))
    d = run_batch(ctx, "W1", [("PN_a0", K10), ("PN_a1", K10)], "U2b", fence=None, arm_defs=defs, write=False)
    res["U2_alpha0_other_mates_10"] = sum(x["token_ids"] == y["token_ids"] for x, y in zip(a[:10], d[:10]))
    res["U2_alpha1_changed_10"] = sum(x["token_ids"] != y["token_ids"] for x, y in zip(a[:10], d[10:]))
    # U3 displacement accuracy (alpha 1 records written by edited_prefill)
    n = load_norms("T03")
    recs = []
    for k in range(3):
        from sampling_v4 import pn_direction

        seed, u = pn_direction("T03", "PN_a1", "W1", k)
        _, rec = ctx.edited_prefill("W1", "twin", torch.tensor(u, device=model.device), 1.0,
                                    {"arm": "PN_a1", "slot": k, "direction_seed": seed})
        recs.append(rec)
    res["U3_max_relerr_along_u"] = max(max(r["rel_err_along_u"].values()) for r in recs)
    res["U3_disp_b12_over_n12"] = float(np.mean([r["disp_S"][12] for r in recs]) / float(n[0].mean()))
    res["U3_pass"] = res["U3_max_relerr_along_u"] <= 1e-2 and abs(res["U3_disp_b12_over_n12"] - 1) <= 0.05
    # U5 fence-stop invariance (bench T03, path T2)
    e = run_batch(ctx, "W1", [("TWIN", K20)], "U5_bench_fence", fence="bench", write=False)
    res["U5_bench_same_code"] = sum(_extract_bench(x["text"]) == _extract_bench(y["text"]) for x, y in zip(a, e))
    res["U5_bench_steps_saved"] = [a[0].get("n_new_tokens"), e[0].get("n_new_tokens")]
    ctx2 = TaskContext(model, tok, prompts, "T2")
    f1 = run_batch(ctx2, "W1", [("TWIN", K20)], "U5_path_nofence", fence=None, write=False)
    f2 = run_batch(ctx2, "W1", [("TWIN", K20)], "U5_path_fence", fence="path", write=False)
    res["U5_path_same_code"] = sum(_extract_path(x["text"]) == _extract_path(y["text"]) for x, y in zip(f1, f2))
    res["U5_path_tokens_nofence_vs_fence"] = [sum(x["n_new_tokens"] for x in f1), sum(x["n_new_tokens"] for x in f2)]
    del ctx2
    # U4 memory probe: full preallocated cache for the longest prompt at B = 20, 16 decode steps
    torch.cuda.reset_peak_memory_stats()
    longest = max((p for p in prompts.values()), key=lambda p: p["P"])
    pre_l = prefill(model, longest["ids"])
    from engine_v4 import prealloc_cache

    kv = [(K.expand(20, -1, -1, -1).contiguous(), V.expand(20, -1, -1, -1).contiguous()) for K, V in pre_l["kv"]]
    cache = prealloc_cache(kv, longest["P"] + MAX_NEW_TOKENS + 1)
    del kv
    tokn = torch.full((20, 1), 13, device=model.device, dtype=torch.long)
    with torch.no_grad():
        for s in range(16):
            pos = torch.full((20, 1), longest["P"] + s, device=model.device, dtype=torch.long)
            model.model(input_ids=tokn, past_key_values=cache, position_ids=pos, use_cache=True)
    del cache
    free, total = torch.cuda.mem_get_info(0)
    res["U4_peak_GB"] = torch.cuda.max_memory_allocated() / 1e9
    res["U4_total_GB"] = total / 1e9
    res["U4_longest_P"] = longest["P"]
    res["U4_pass"] = res["U4_peak_GB"] < 0.95 * res["U4_total_GB"]
    gc.collect()
    torch.cuda.empty_cache()
    # U6 sampler masks on 1,000 synthetic logit rows
    g = torch.Generator(device=model.device).manual_seed(0)
    V = 151936
    ok_id, ok_topk, ok_minp = 0, 0, 0
    for chunk in range(10):
        L = (torch.randn(100, V, device=model.device, generator=g, dtype=torch.float64) * 4.0)
        u = torch.rand(100, device=model.device, generator=g, dtype=torch.float64)
        ones = torch.ones(100, 1, dtype=torch.float64, device=model.device)
        p_new = step_probs(L, ones, 0, torch.zeros(100, dtype=torch.bool, device=model.device),
                           torch.zeros(100, dtype=torch.long, device=model.device),
                           torch.zeros(100, 1, dtype=torch.float64, device=model.device), False, False)
        p_old = torch.softmax(L / 1.0, dim=-1)
        ok_id += int((_inverse_cdf(p_new, u) == _inverse_cdf(p_old, u)).sum()) if torch.equal(p_new, p_old) else 0
        pk = step_probs(L, ones, 10, torch.ones(100, dtype=torch.bool, device=model.device),
                        torch.full((100,), 9, dtype=torch.long, device=model.device),
                        torch.zeros(100, 1, dtype=torch.float64, device=model.device), True, False)
        tk = _inverse_cdf(pk, u)
        top10 = L.topk(10, dim=-1).indices
        ok_topk += int((top10 == tk[:, None]).any(dim=1).sum())
        mp = step_probs(L * 0.5, ones * 1.6, 0, torch.zeros(100, dtype=torch.bool, device=model.device),
                        torch.zeros(100, dtype=torch.long, device=model.device),
                        torch.full((100, 1), 0.1, dtype=torch.float64, device=model.device), False, True)
        tm = _inverse_cdf(mp, u)
        p_full = torch.softmax(L * 0.5 / 1.6, dim=-1)
        ok_minp += int((p_full.gather(-1, tm[:, None])[:, 0] >= 0.1 * p_full.max(-1).values - 1e-15).sum())
    res["U6_untruncated_identical_1000"] = ok_id
    res["U6_topk10_allowed_1000"] = ok_topk
    res["U6_minp_allowed_1000"] = ok_minp
    res["all_pass"] = (res["U1_determinism"] == 20 and res["U1_vs_exp17_sampler"] == 20
                       and res["U2_alpha0_vs_twin_20"] == 20 and res["U2_alpha0_other_mates_10"] == 10
                       and res["U3_pass"] and res["U4_pass"] and res["U5_bench_same_code"] == 20
                       and res["U5_path_same_code"] == 20 and ok_id == 1000 and ok_topk == 1000 and ok_minp == 1000)
    write_json(UT, res)
    logger.info(f"GPU unit tests: {res}")
    return res


# ------------------------------------------------------------------------------------------------ R2 unit (0.7)
@torch.no_grad()
def r2_unit(model: Any, tok: Any, prompts: dict) -> dict[str, Any]:
    out_p = RESULTS_DIR / "unit_r2.json"
    if out_p.exists() and (RESULTS_DIR / "unit_R2.npy").exists():
        return read_json(out_p)
    hnorm: dict[str, np.ndarray] = {}
    for t in BENCH12 + ("R2",):
        acc = []
        for w in TEMPLATE_IDS:
            p = prompt_for(prompts, t, w, "twin")
            a, b = p["p1"], p["spec_end"]
            cap: dict[int, torch.Tensor] = {}

            def mk(l):
                def g(h):
                    cap[l] = h[0, a:b].float().norm(dim=-1).cpu()
                return g
            prefill(model, p["ids"], capture={l: mk(l) for l in V_BLOCKS})
            acc.append(torch.stack([cap[l] for l in V_BLOCKS]).numpy())
        hnorm[t] = np.mean(acc, axis=0)  # [12, S]
    ratios = {t: load_norms(t) / hnorm[t] for t in BENCH12}
    rho = np.median(np.concatenate([ratios[t] for t in BENCH12], axis=1), axis=1)  # [12]
    n_r2 = (rho[:, None] * hnorm["R2"]).astype(np.float32)
    np.save(RESULTS_DIR / "unit_R2.npy", n_r2)
    loto = {}
    for t in BENCH12:
        rho_t = np.median(np.concatenate([ratios[s] for s in BENCH12 if s != t], axis=1), axis=1)
        pred = rho_t[:, None] * hnorm[t]
        loto[t] = np.median(np.abs(np.log(pred / load_norms(t))), axis=1).round(4).tolist()
    per_layer = np.median(np.array([loto[t] for t in BENCH12]), axis=0)
    res = {"rho_per_block": dict(zip(V_BLOCKS, rho.round(5).tolist())),
           "n_R2_mean_per_block": dict(zip(V_BLOCKS, n_r2.mean(1).round(3).tolist())),
           "R2_S_len": int(n_r2.shape[1]),
           "loto_median_abs_log_ratio_per_task": loto,
           "loto_median_abs_log_ratio_per_block_median_over_tasks": dict(zip(V_BLOCKS, per_layer.round(4).tolist())),
           "note": "rho_l = median over 12 bench tasks and spec positions of n_t[l,p] / mean_w ||h_twin[l,p]||; "
                   "n_R2 = rho_l * mean_w ||h_twin,R2,w[l,p]|| (FP8 prefill states, exp13 bf16 ban units)",
           "utc": utc_now()}
    write_json(out_p, res)
    logger.info(f"R2 unit: rho {res['rho_per_block']}; LOTO median |log ratio| {res['loto_median_abs_log_ratio_per_block_median_over_tasks']}")
    return res


# ------------------------------------------------------------------------------------------------ engine check (3)
def engine_check(model: Any, tok: Any, prompts: dict) -> int:
    done = {(r["task"], r["template"], r["arm"], int(r["slot"])) for r in read_jsonl(EC_RAW)}
    n = 0
    for task, seed in (("T03", 9002), ("T2", 9004)):
        nm = load_norms(task, source="exp17")
        ctx = TaskContext(model, tok, prompts, task, norms=nm)
        rdir = np.load(E17 / "directions" / f"rand_{seed}.npy").astype(np.float32)
        defs = {"NEUTRAL": {"prompt": "twin", "T": 1.0, "top_k": 0, "min_p": 0.0, "alpha": None, "knob": "EC"},
                f"RAND{seed}_a1.0": {"prompt": "twin", "T": 1.0, "top_k": 0, "min_p": 0.0, "alpha": 1.0,
                                     "knob": "EC", "fixed_dir": rdir, "fixed_seed": seed,
                                     "norms": {l: torch.tensor(nm[j], device=model.device)
                                               for j, l in enumerate(V_BLOCKS)}}}
        for w in TEMPLATE_IDS:
            spec = [("NEUTRAL", K10), (f"RAND{seed}_a1.0", K10)]
            if all((task, w, a, k) in done for a, ks in spec for k in ks):
                continue
            rows = run_batch(ctx, w, spec, f"EC:{task}:{w}", fence="auto", arm_defs=defs, write=False)
            append_jsonl(EC_RAW, rows)
            n += 1
        ctx.clean.clear()
        torch.cuda.empty_cache()
    return n


# ------------------------------------------------------------------------------------------------ queue plans
def plan_items(stage: str, n_p3_templates: int = 3, p3_drop: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    if stage == "stage10":
        return [{"prio": p, "task": t, "templates": ["W1"]} for t in ("T03", "T2") for p in ("P1", "P2")]
    if stage == "stage100":
        return [{"prio": p, "task": "T03", "templates": TEMPLATE_IDS} for p in ("P1", "P2")]
    order = ("T03", "T05", "T06", "T10", "T2", "T1", "R2")
    items = [{"prio": "P1", "task": t, "templates": TEMPLATE_IDS} for t in order]
    items += [{"prio": "P2", "task": t, "templates": TEMPLATE_IDS} for t in order]
    p3 = [t for t in ("T04", "R1", "T08", "R3", "T13", "R6", "T14", "T11") if t not in p3_drop]
    items += [{"prio": "P3", "task": t, "templates": TEMPLATE_IDS[:n_p3_templates]} for t in p3]
    return items


def timing_plan(deadline: float) -> dict[str, Any]:
    """Seconds per batch by batch kind from the timing log; extrapolate the rest of the queue; choose N for P3 and
    drops BEFORE the full run (rules fixed in the plan's fallback order)."""
    rows = read_jsonl(RESULTS_DIR / "timing_batches.jsonl")
    by: dict[str, list[float]] = {}
    for r in rows:
        key = ("path" if r["task"] in PATH_TASKS else "bench") + ":" + "+".join(r["arms"])
        by.setdefault(key, []).append(r["seconds"])
    mean_by = {k: float(np.mean(v)) for k, v in by.items()}

    def est(kind: str, arms: list[str]) -> float:
        k = kind + ":" + "+".join(arms)
        if k in mean_by:
            return mean_by[k] * (1.0 if kind == "bench" else 1.0)
        # path task without a measurement: scale the bench mean of the same arms by the T2/T03 ratio
        kb = "bench:" + "+".join(arms)
        base = mean_by.get(kb, 30.0)
        return base * (2.5 if kind == "path" else 1.0)

    from sampling_v4 import task_batches

    def queue_seconds(items, done_keys):
        s = 0.0
        for it in items:
            kind = "path" if it["task"] in PATH_TASKS else "bench"
            for w in it["templates"]:
                for spec in task_batches(it["task"], it["prio"]):
                    if all((it["task"], w, a, k) in done_keys for a, ks in spec for k in ks):
                        continue
                    s += est(kind, [a for a, _ in spec])
        return s

    from sampling_v4 import done_slots

    done_keys = done_slots()
    remaining = deadline - time.time()
    decisions = []
    full = plan_items("full", 5)
    t_full = queue_seconds(full, done_keys)
    choice = {"n_p3_templates": 5, "p3_drop": [], "dropped_arms": []}
    if t_full > remaining:
        choice["n_p3_templates"] = 3
        decisions.append("P3 N reduced to 30 (W1-W3)")
    t = queue_seconds(plan_items("full", choice["n_p3_templates"]), done_keys)
    drop_seq = [("arms", ["MINP_T2.0", "VS"]), ("arms", ["MINP_T1.6"]), ("arms", ["PN_a8"]), ("arms", ["PNPLAIN_a1"])]
    p3_order = ["T11", "T14", "R6", "T13", "R3", "T08", "R1", "T04"]
    while t > remaining * 0.95 and (drop_seq or p3_order):
        if drop_seq:
            _, arms = drop_seq.pop(0)
            choice["dropped_arms"] += arms
            decisions.append(f"drop arms {arms}")
        else:
            choice["p3_drop"].append(p3_order.pop(0))
            decisions.append(f"drop P3 task {choice['p3_drop'][-1]}")
        # recompute with drops: approximate by removing the dropped arms' batch estimates
        t = 0.0
        for it in plan_items("full", choice["n_p3_templates"], tuple(choice["p3_drop"])):
            kind = "path" if it["task"] in PATH_TASKS else "bench"
            for w in it["templates"]:
                for spec in task_batches(it["task"], it["prio"]):
                    keep = [(a, ks) for a, ks in spec if a not in choice["dropped_arms"]]
                    if not keep or all((it["task"], w, a, k) in done_keys for a, ks in keep for k in ks):
                        continue
                    t += est(kind, [a for a, _ in keep])
    res = {"mean_seconds_by_batch_kind": mean_by, "remaining_seconds": remaining, "t_full_estimate": t_full,
           "t_after_decisions": t, "decisions": decisions, "choice": choice, "utc": utc_now()}
    write_json(RESULTS_DIR / "timing_plan.json", res)
    logger.info(f"timing plan: {decisions}; est {t:.0f}s vs remaining {remaining:.0f}s")
    return res


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deadline-utc", required=True, help="hard stop for NEW batches (ISO, UTC)")
    ap.add_argument("--only", default="", help="comma list: tests,r2,ec,stage10,full")
    args = ap.parse_args()
    setup_logging("gpu_stage")
    # no RLIMIT_AS here: CUDA reserves a large virtual address space at init (RLIMIT_AS makes cudaGetDeviceCount fail)
    deadline = datetime.fromisoformat(args.deadline_utc.replace("Z", "+00:00")).timestamp()
    only = set(x for x in args.only.split(",") if x)
    tok, model = load_model(fp8=True)
    prompts = load_prompts()
    if not only or "tests" in only:
        ut = gpu_tests(model, tok, prompts)
        if not ut.get("all_pass"):
            logger.error("GPU unit tests did not all pass -- see results/unit_tests_gpu.json")
    if not only or "r2" in only:
        r2_unit(model, tok, prompts)
    if not only or "ec" in only:
        engine_check(model, tok, prompts)
        (RESULTS_DIR / "engine_check_generated.flag").write_text(utc_now())
    if not only or "stage10" in only:
        run_queue(model, tok, prompts, plan_items("stage10"), deadline)
        (RESULTS_DIR / "stage10_done.flag").write_text(utc_now())
    if not only or "full" in only:
        while not COMMIT_FLAG.exists():
            logger.info("waiting for the commitment (predictions/COMMITTED) before stage 100 ...")
            time.sleep(30)
        r = run_queue(model, tok, prompts, plan_items("stage100"), deadline)
        tp = timing_plan(deadline)
        ch = tp["choice"]
        for d in tp["decisions"]:
            append_deviation(f"TIME-{d}", f"time rule at stage 100 (extrapolation only): {d}")
        r = run_queue(model, tok, prompts, plan_items("full", ch["n_p3_templates"], tuple(ch["p3_drop"])),
                      deadline, dropped=set(ch["dropped_arms"]))
        write_json(RESULTS_DIR / "queue_result.json", {**r, "choice": ch, "utc": utc_now()})
        (RESULTS_DIR / "gpu_done.flag").write_text(utc_now())
    logger.info("gpu stage finished")


if __name__ == "__main__":
    main()
