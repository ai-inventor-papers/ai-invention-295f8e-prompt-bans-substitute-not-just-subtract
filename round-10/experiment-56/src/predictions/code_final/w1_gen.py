#!/usr/bin/env python3
"""W1 generation: does restoring the base fork-class unembedding rows change the algorithm the model WRITES?

Iteration 9's common-random-number engine (b2gen9.sample: float64 inverse CDF in token-id order, T 1, top-p 1; 30 slots
= W1-W5 x 6, uniforms np.random.default_rng(9101 + s).random(MAX_NEW); the instruct opening prefilled; the slot prompt =
the first units.json prompt of each template). One batch of the template's 6 slots per arm at a FIXED batch shape
B = 6, so every arm runs identical GEMM shapes. At the fork every arm uses an fp32 full-vocabulary readout of the same
instruct h_fin (TWIN included):
  TWIN W_I; ROWS W_I with the S rows = base; RAND_MED / RAND_MAX / RAND_0 the committed RAND_ISO draws; FPD the base
  model's fp32 fork logits (S0 capture); FULL_UNEMB_FORK all rows base (run only if committed TV > 0.05);
  ROWS_ALLSTEPS ROWS at the fork AND the S rows of the bf16 lm_head swapped in place for every later step.
Later steps use the unmodified instruct bf16 lm_head (except ROWS_ALLSTEPS). Programs are labelled by the frozen
label_k3.py (hidden tests + runtime tracer + AST).

Usage: w1_gen.py gpu [budget_seconds] | g5 | label | analyze
"""

from __future__ import annotations

import gc
import sys
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg10 import (CACHE_DIR, CORRECT, DATA_DIR, EOS_IDS, GEN_B, I9_RES, MAX_NEW, MINORITY, PRED_DIR, RESULTS_DIR,
                   SEED0, SLOTS_PER_T, THRESH, TEMPLATES, append_jsonl, import_iter9, ledger, log_deviation,
                   partial_status, read_json, read_jsonl, setup_logging, sha256_text, utc_now, write_json)
from capture10 import CM, full_logits, load
from w1_tf import load_readout

import_iter9()
import stats9 as S9  # noqa: E402
from b2gen9 import sample, slot_prompts  # noqa: E402

RAW = DATA_DIR / "gen_samples.jsonl"
LAB = DATA_DIR / "gen_labels.jsonl"
CORE = ("TWIN", "ROWS", "RAND_MED", "FPD")
ORDER = ("TWIN", "ROWS", "RAND_MED", "FPD", "RAND_MAX", "RAND_0", "ROWS_ALLSTEPS", "FULL_UNEMB_FORK")
DOSE_ARMS = ("ROWS_L2", "ROWS_L3", "RAND_MED_L2", "RAND_MED_L3",   # extension (COMMIT #4, w1_dose_gen.py)
             "RAND_RESID_MED_L3", "RAND_RESID_MAX_L3", "DELTA_SWAP_MED_L3", "DELTA_SWAP_MAX_L3")   # COMMIT #5
DROP_ORDER = ("FULL_UNEMB_FORK", "ROWS_ALLSTEPS", "RAND_0", "B3")


def gen_plan() -> dict[str, Any]:
    return read_json(PRED_DIR / "commit2_w1tf_genplan.json")


@torch.no_grad()
def generate(model: Any, tok: Any, kv: list, ids: list[int], fork_logits_fn, Urows: torch.Tensor, mx: int,
             swap_rows: tuple[list[int], torch.Tensor] | None = None) -> tuple[list[list[int]], list[bool]]:
    """One fixed-shape batch: one-token forward of the fork token over the prefix KV, fork token from
    fork_logits_fn(h_fin [B, d]) -> fp32 logits [B, V], then plain instruct decoding (bf16 lm_head)."""
    B = Urows.shape[0]
    cache = CM.build_cache(kv, B)
    pos = len(ids) - 1
    o = model.model(input_ids=torch.full((B, 1), ids[-1], device="cuda", dtype=torch.long), past_key_values=cache,
                    position_ids=torch.full((B, 1), pos, device="cuda"),
                    cache_position=torch.tensor([pos], device="cuda"), use_cache=True)
    lg = fork_logits_fn(o.last_hidden_state[:, -1])
    nxt = sample(lg, Urows[:, 0])
    gen = [[int(t)] for t in nxt.tolist()]
    fin = [int(t) in EOS_IDS for t in nxt.tolist()]
    W = model.lm_head.weight
    saved = None
    if swap_rows is not None:
        rows, new = swap_rows
        saved = W.data[rows].clone()
        W.data[rows] = new.to(W.dtype).to(W.device)
    try:
        for t in range(1, mx):
            if all(fin):
                break
            cur = pos + t
            o = model.model(input_ids=nxt[:, None], past_key_values=cache,
                            position_ids=torch.full((B, 1), cur, device="cuda"),
                            cache_position=torch.tensor([cur], device="cuda"), use_cache=True)
            lg = model.lm_head(o.last_hidden_state[:, -1]).float()
            nxt = sample(lg, Urows[:, t])
            for r in range(B):
                if not fin[r]:
                    gen[r].append(int(nxt[r]))
                    if len(gen[r]) % 8 == 0 or int(nxt[r]) in EOS_IDS:
                        txt = tok.decode(gen[r])
                        if "```" in txt or int(nxt[r]) in EOS_IDS:
                            fin[r] = True
    finally:
        if saved is not None:
            W.data[swap_rows[0]] = saved
    del cache, o
    return gen, fin


def uniforms(ti: int, mx: int) -> tuple[list[int], torch.Tensor]:
    slots = [ti * SLOTS_PER_T + k for k in range(SLOTS_PER_T)]
    U = torch.tensor(np.stack([np.random.default_rng(SEED0 + s).random(mx) for s in slots]))
    return slots, U


@torch.no_grad()
def gpu(budget_s: float = 3600.0) -> None:
    t0 = time.time()
    ledger("W1GEN_start")
    model, tok, info = load("qwen")
    units = read_json(I9_RES / "units.json")
    plan = gen_plan()
    WB_cpu, _ = load_readout("qwen_base")
    W = model.lm_head.weight
    done = {r["sid"] for r in read_jsonl(RAW)}
    g6: dict[str, Any] = {}
    unit_arms: dict[str, list[str]] = {}
    for u in ("T10", "B3"):
        arms = [a for a in ORDER if a != "FULL_UNEMB_FORK" or plan["gen_predictions"][u]["run_FULL_UNEMB_FORK"]]
        unit_arms[u] = arms
    n_batches = sum(len(unit_arms[u]) * len(TEMPLATES) for u in unit_arms)
    timing: list[float] = []
    dropped: list[str] = []
    for u in ("T10", "B3"):
        if "B3" in dropped and u == "B3":
            break
        U = units[u]
        f = U["forks"][0]
        S = [int(t) for t in f["D"]] + [int(t) for t in f["A"]]
        nul = np.load(RESULTS_DIR / f"null_draws_{u}.npz")
        assert list(nul["S"]) == S
        gp = plan["gen_predictions"][u]
        WI_S = W[S].float()
        WB_S = WB_cpu[S].float().cuda()
        rand_rows = {a: (WI_S + torch.from_numpy(nul["RAND_ISO"][k]).cuda()) for a, k in gp["rand_draws"].items()}
        cb = torch.load(CACHE_DIR / f"fork_base_{u}.pt")
        base_logits = {c["pid"]: c["logits"].float() for c in cb["caps"]}
        del cb
        mx = MAX_NEW[u]
        open_txt = tok.decode(f["opening"])
        for ti, (i, p) in enumerate(slot_prompts(U)):
            ids = p["ids"] + f["opening"]
            kv = CM.prefix_kv(model, ids)
            slots, Urows = uniforms(ti, mx)
            for a in unit_arms[u]:
                if a in dropped:
                    continue
                sids = [f"{u}|{a}|{p['template']}|{k}" for k in range(SLOTS_PER_T)]
                if all(s in done for s in sids):
                    continue
                tb = time.time()

                def fork_fn(h: torch.Tensor, a: str = a) -> torch.Tensor:
                    if a == "FPD":
                        return base_logits[p["pid"]].cuda()[None].expand(h.shape[0], -1).contiguous()
                    if a == "FULL_UNEMB_FORK":
                        return torch.cat([h.float() @ WB_cpu[c:c + 16384].cuda().float().T
                                          for c in range(0, WB_cpu.shape[0], 16384)], -1)
                    z = full_logits(W, h)
                    if a in ("ROWS", "ROWS_ALLSTEPS"):
                        z[:, S] = h.float() @ WB_S.T
                    elif a in rand_rows:
                        z[:, S] = h.float() @ rand_rows[a].T
                    return z
                swap = (S, WB_S) if a == "ROWS_ALLSTEPS" else None
                before = W.data[S].clone() if swap else None
                gen, fin = generate(model, tok, kv, ids, fork_fn, Urows, mx, swap_rows=swap)
                if swap:
                    ok = bool(torch.equal(W.data[S], before))
                    g6[f"{u}|{p['template']}"] = ok
                    assert ok, "lm_head rows not restored bit-exactly"
                recs = []
                for r in range(GEN_B):
                    txt = tok.decode(gen[r])
                    if "```" in txt:
                        txt = txt[:txt.index("```") + 3]
                    full = open_txt + txt
                    recs.append({"sid": sids[r], "unit": u, "task": u, "arm": a, "template": p["template"],
                                 "prompt_id": p["pid"], "slot": slots[r], "seed": SEED0 + slots[r],
                                 "fork_token": tok.decode([gen[r][0]]), "fork_token_id": gen[r][0],
                                 "n_tokens": len(gen[r]), "truncated": not fin[r], "text": full,
                                 "code_sha256": sha256_text(full), "engine": "hf-bf16", "batch_shape": GEN_B,
                                 "utc": utc_now()})
                append_jsonl(RAW, recs)
                dt = time.time() - tb
                timing.append(dt)
                logger.info(f"[{u}] {p['template']} {a}: {GEN_B} programs in {dt:.1f}s; fork tokens "
                            f"{[x['fork_token'] for x in recs]}; max tokens {max(len(g) for g in gen)}")
                if len(timing) == 2:
                    est = float(np.mean(timing)) * n_batches
                    ledger("W1GEN_extrapolation", per_batch_s=float(np.mean(timing)), n_batches=n_batches,
                           est_total_s=est, budget_s=budget_s)
                    logger.info(f"extrapolated total {est:.0f}s for {n_batches} batches (budget {budget_s:.0f}s)")
                    while est > budget_s and len(dropped) < len(DROP_ORDER):
                        d_ = DROP_ORDER[len(dropped)]
                        dropped.append(d_)
                        nb = sum(len([a_ for a_ in unit_arms[u_] if a_ not in dropped]) * len(TEMPLATES)
                                 for u_ in unit_arms if u_ not in dropped)
                        est = float(np.mean(timing)) * nb
                        log_deviation(f"gen_drop_{d_}", f"generation arm/unit {d_} dropped: extrapolated "
                                                        f"{est:.0f}s vs budget {budget_s:.0f}s")
            del kv
            torch.cuda.empty_cache()
            partial_status("W1_GEN", unit=u, template=p["template"], n_done=len(read_jsonl(RAW)))
        del base_logits
        gc.collect()
    write_json(RESULTS_DIR / "w1_gen_gpu.json", {"utc": utc_now(), "load": info, "G6_lm_head_restore_bit_exact": g6,
                                                  "dropped": dropped, "batch_seconds": timing,
                                                  "seconds": round(time.time() - t0, 1)})
    ledger("W1GEN_end", seconds=round(time.time() - t0, 1))


@torch.no_grad()
def g5() -> None:
    """G5: generation determinism (TWIN on one template's 6 slots twice gives identical token ids) and CRN sanity (an
    arm whose fork logits equal TWIN's, ROWS at lambda = 0 via the S-row replacement path, gives identical programs).
    Truncated at 160 new tokens to bound time."""
    model, tok, info = load("qwen")
    units = read_json(I9_RES / "units.json")
    U = units["T10"]
    f = U["forks"][0]
    S = [int(t) for t in f["D"]] + [int(t) for t in f["A"]]
    W = model.lm_head.weight
    i, p = slot_prompts(U)[0]
    ids = p["ids"] + f["opening"]
    kv = CM.prefix_kv(model, ids)
    slots, Urows = uniforms(0, MAX_NEW["T10"])
    mx = 160

    def twin(h):
        return full_logits(W, h)

    def rows_l0(h):
        z = full_logits(W, h)
        z[:, S] = h.float() @ W[S].float().T
        return z
    a, _ = generate(model, tok, kv, ids, twin, Urows, mx)
    b, _ = generate(model, tok, kv, ids, twin, Urows, mx)
    c, _ = generate(model, tok, kv, ids, rows_l0, Urows, mx)
    out = {"utc": utc_now(), "template": p["template"], "max_new": mx, "twin_repeat_identical": a == b,
           "rows_lambda0_identical_to_twin": a == c, "n_rows": len(a),
           "fork_tokens": [tok.decode([g[0]]) for g in a]}
    tests = read_json(RESULTS_DIR / "tests_gpu.json") if (RESULTS_DIR / "tests_gpu.json").exists() else {}
    tests["G5"] = out
    write_json(RESULTS_DIR / "tests_gpu.json", tests)
    logger.info(f"G5: {out}")


def label() -> None:
    from inputs10 import run_labeller
    rows = read_jsonl(RAW)
    done = {r["sid"] for r in read_jsonl(LAB)}
    todo = [{"sid": r["sid"], "unit": r["task"], "text": r["text"]} for r in rows if r["sid"] not in done]
    if not todo:
        logger.info("nothing to label")
        return
    t0 = time.time()
    out = run_labeller(todo, "gen")
    append_jsonl(LAB, out)
    logger.info(f"labelled {len(out)} programs in {time.time() - t0:.1f}s")


def analyze() -> dict[str, Any]:
    raw = {r["sid"]: r for r in read_jsonl(RAW)}
    lab = {r["sid"]: r for r in read_jsonl(LAB)}
    plan = gen_plan()
    gpu_meta = read_json(RESULTS_DIR / "w1_gen_gpu.json") if (RESULTS_DIR / "w1_gen_gpu.json").exists() else {}
    i9 = read_json(I9_RES / "b2_generation.json")
    out: dict[str, Any] = {"utc": utc_now(), "dropped": gpu_meta.get("dropped", []), "units": {}}
    for u in ("T10", "B3"):
        rs_u = [r for r in raw.values() if r["unit"] == u]
        if not rs_u:
            continue
        gp = plan["gen_predictions"][u]
        dose_plan = read_json(PRED_DIR / "commit4_dose_gen.json") if (PRED_DIR / "commit4_dose_gen.json").exists() \
            else None
        strong_plan = read_json(PRED_DIR / "commit5_strong_null_gen.json") \
            if (PRED_DIR / "commit5_strong_null_gen.json").exists() else None
        for pl in (dose_plan, strong_plan):
            if pl:
                gp = dict(gp, unit_mean={**gp["unit_mean"], **pl["units"][u]["predicted_shares"]},
                          unit_mean_unmapped={**gp["unit_mean_unmapped"], **pl["units"][u]["predicted_unmapped"]},
                          predicted_count_correct_class_of_30={**gp["predicted_count_correct_class_of_30"],
                                                               **pl["units"][u]["predicted_correct_count_of_30"]})
        bins = gp["bins"]
        arms = [a for a in ORDER + DOSE_ARMS if any(r["arm"] == a for r in rs_u)]
        cells: dict[str, Any] = {}
        for a in arms:
            rs = [r for r in rs_u if r["arm"] == a]
            labs = [lab[r["sid"]] for r in rs if r["sid"] in lab]
            n = len(labs)
            cnt: dict[str, int] = {}
            cnt_pass: dict[str, int] = {}
            for l_ in labs:
                cnt[l_["label"]] = cnt.get(l_["label"], 0) + 1
                if l_["passed"]:
                    cnt_pass[l_["label"]] = cnt_pass.get(l_["label"], 0) + 1
            corr = sum(1 for l_ in labs if l_["label"] in CORRECT[u] and l_["passed"])
            corr_min = sum(1 for l_ in labs if l_["label"] in MINORITY[u] and l_["passed"])
            npass = sum(1 for l_ in labs if l_["passed"])
            ft: dict[str, int] = {}
            for r in rs:
                ft[r["fork_token"]] = ft.get(r["fork_token"], 0) + 1
            obs = {b: cnt.get(b, 0) / n if n else None for b in bins}
            pm = gp["unit_mean"].get(a)
            cells[a] = {"n": n, "label_counts": cnt, "label_counts_passing": cnt_pass, "n_pass": npass,
                        "pass_rate": npass / n if n else None, "pass_ci95": S9.wilson(npass, n),
                        "n_correct": corr, "correct_rate": corr / n if n else None,
                        "correct_ci95": S9.wilson(corr, n), "n_correct_minority": corr_min,
                        "truncated": sum(1 for r in rs if r["truncated"]), "fork_token_counts": ft,
                        "observed_shares": obs, "predicted_shares": pm,
                        "predicted_unmapped": gp["unit_mean_unmapped"].get(a),
                        "predicted_correct_count": gp["predicted_count_correct_class_of_30"].get(a),
                        "mae_pred_vs_obs": float(np.mean([abs((obs[b] or 0) - pm[b]) for b in bins])) if pm and n
                        else None,
                        "n_other_correct": sum(1 for l_ in labs if l_["label"] == "other" and l_["passed"])}

        def ind(a: str, which: set[str]) -> dict[tuple[str, int], int]:
            d = {}
            for r in rs_u:
                if r["arm"] == a and r["sid"] in lab:
                    d[(r["template"], r["slot"])] = int(lab[r["sid"]]["label"] in which and lab[r["sid"]]["passed"])
            return d
        pairs = [("ROWS", "TWIN"), ("ROWS", "RAND_MED"), ("ROWS", "RAND_MAX"), ("ROWS", "RAND_0"), ("FPD", "TWIN"),
                 ("ROWS", "FPD"), ("ROWS_ALLSTEPS", "ROWS"), ("ROWS_ALLSTEPS", "TWIN"), ("FULL_UNEMB_FORK", "ROWS"),
                 ("RAND_MED", "TWIN"), ("ROWS_L2", "TWIN"), ("ROWS_L3", "TWIN"), ("ROWS_L2", "RAND_MED_L2"),
                 ("ROWS_L3", "RAND_MED_L3"), ("RAND_MED_L2", "TWIN"), ("RAND_MED_L3", "TWIN"), ("ROWS_L2", "ROWS"),
                 ("ROWS_L3", "FPD"), ("ROWS_L3", "RAND_RESID_MED_L3"), ("ROWS_L3", "RAND_RESID_MAX_L3"),
                 ("ROWS_L3", "DELTA_SWAP_MED_L3"), ("ROWS_L3", "DELTA_SWAP_MAX_L3")]
        tests: dict[str, Any] = {}
        for which_name, which in (("correct", CORRECT[u]), ("correct_minority", MINORITY[u])):
            for a, b in pairs:
                if a not in cells or b not in cells:
                    continue
                x, y = ind(a, which), ind(b, which)
                ks = sorted(set(x) & set(y))
                b_ = sum(1 for k in ks if x[k] == 1 and y[k] == 0)
                c_ = sum(1 for k in ks if x[k] == 0 and y[k] == 1)
                key = f"{a}_vs_{b}" + ("" if which_name == "correct" else "|minority")
                tests[key] = {"n_pairs": len(ks), "b_first_only": b_, "c_second_only": c_,
                              "p_exact_two_sided": S9.mcnemar_exact(b_, c_),
                              "pass_diff_newcombe95": S9.newcombe(cells[a]["n_pass"], cells[a]["n"],
                                                                  cells[b]["n_pass"], cells[b]["n"])
                              if cells[a]["n"] and cells[b]["n"] else None}
        prim = [k for k in ("ROWS_vs_TWIN", "ROWS_vs_RAND_MED") if k in tests]
        for k, adj in zip(prim, S9.holm([tests[k]["p_exact_two_sided"] for k in prim])):
            tests[k]["p_holm_primary"] = adj
        rand_arms = [a for a in ("RAND_MED", "RAND_MAX", "RAND_0") if a in cells]
        verdict = None
        if u == "T10" and "ROWS" in cells:
            ok = (cells["ROWS"]["n_correct"] >= THRESH["W1GEN_rows_min_correct"] and
                  all(cells[a]["n_correct"] <= THRESH["W1GEN_rand_max_correct"] for a in rand_arms) and
                  all(tests[k].get("p_holm_primary", 1) < THRESH["W1GEN_alpha"] for k in prim))
            verdict = "SUPPORTED" if ok else "NOT SUPPORTED"
        i9u = i9.get(u, {}).get("cells", {})
        out["units"][u] = {
            "cells": cells, "tests": tests, "verdict": verdict, "verdict_role": "primary" if u == "T10" else
            "descriptive", "rand_draws": gp["rand_draws"], "rand_draw_tf_shares": gp["rand_draw_tf_shares"],
            "engine_check_vs_iter9": {"TWIN_correct_minority_iter9": i9u.get("TWIN", {}).get("n_correct_minority"),
                                      "TWIN_correct_minority_here": cells.get("TWIN", {}).get("n_correct_minority"),
                                      "FPD_correct_minority_iter9": i9u.get("FPD", {}).get("n_correct_minority"),
                                      "FPD_correct_minority_here": cells.get("FPD", {}).get("n_correct_minority"),
                                      "FPD_vs_TWIN_iter9": i9.get(u, {}).get("tests", {}).get("FPD_vs_TWIN")}}
        logger.info(f"generation {u}: " + "; ".join(f"{a}: correct {cells[a]['n_correct']}/{cells[a]['n']} "
                                                     f"(pred {cells[a]['predicted_correct_count']:.1f}) pass "
                                                     f"{cells[a]['n_pass']}" for a in arms) + f" -> {verdict}")
    write_json(RESULTS_DIR / "w1_generation.json", out)
    partial_status("W1_GEN_analysis", verdict=out["units"].get("T10", {}).get("verdict"))
    return out


if __name__ == "__main__":
    setup_logging(f"w1_gen_{sys.argv[1]}")
    cmd = sys.argv[1]
    if cmd == "gpu":
        gpu(float(sys.argv[2]) if len(sys.argv) > 2 else 3600.0)
    else:
        {"g5": g5, "label": label, "analyze": analyze}[cmd]()
