#!/usr/bin/env python3
"""GPU unit tests run after commit #1 on T2's frozen exp8 prompts only (T2's ban outcome is already published).

U1 CRN determinism: the same batch twice -> identical ids.
U2 splice identities: splice(ban, ban) == arm a and splice(twin, twin) == arm b, id for id.
U3 knockout correctness: eager twin with recorded weights -> zero attention mass from generated queries to [p0, p1)
   in every layer under K0, non-zero without; plus the per-row sampling mask reproduces the global-config knockout.
U9 engine validation against exp8: T2 arms a, b, c, d, templates W1/W2, k 0-9 (exp8 uniform keys); labelled by the
   label worker; pass bands a <= 6/20, b >= 17/20, c <= 7/20, d >= 16/20 banned; agreement with exp8 same-slot rows.
U4-U6 are checked on the production rows by audit/rederive.py (veto prefix identity, persistent veto absence,
prefill verbatim), on far more than the planned 20 slots.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg import E8, RESULTS_DIR, read_jsonl, utc_now, write_json
from engine import KO, RECORD, knockout, prefill, sample, set_attn, splice, u_stream


def _rows(W: Any, task: str, w: str, arm: str, ks: range, kv_override: Any = None) -> list[dict[str, Any]]:
    st = W.arm_state(task, w, arm)
    out = []
    for k in ks:
        uk = ("beh", task, w, k)
        out.append({"kv": kv_override["kv"] if kv_override else st["kv"],
                    "r_logits": kv_override["r_logits"] if kv_override else st["r_logits"],
                    "u": u_stream(*uk), "u2": u_stream(*uk, "veto", n=256), "veto": None,
                    "stop": "path", "prefix_text": ""})
    return out


def run_tests(W: Any) -> dict[str, Any]:
    t0 = time.time()
    task = "t2"
    res: dict[str, Any] = {"utc": utc_now(), "B": W.B}
    # ---- U9 production batches (written to RAW for the label worker), W1 and W2
    n = W.run_rows("U9", [{"task": task, "w": w, "k": k, "arm": a} for w in ("W1", "W2") for a in ("a", "b", "c", "d")
                          for k in range(10)])
    res["U9_rows_written"] = n
    raw = {r["uid"]: r for r in read_jsonl(W_RAW())}
    # ---- U1: rerun the W1 batch exactly (same composition and order) and compare ids
    batch = []
    for a in ("a", "b", "c", "d"):
        batch += _rows(W, task, "W1", a, range(10))
    batch = (batch + batch)[:W.B] if len(batch) < W.B else batch[:W.B]
    rep = sample(W.model, batch, tick_ids=W.tick_ids, decode=W.decode)
    arms_order = [a for a in ("a", "b", "c", "d") for _ in range(10)][:W.B]
    ks = [k for _ in ("a", "b", "c", "d") for k in range(10)][:W.B]
    same = [raw[f"{task}|{a}|W1|{k}"]["token_ids"] == r["token_ids"] for a, k, r in zip(arms_order, ks, rep)]
    res["U1_identical_fraction"] = float(np.mean(same))
    # ---- U2: splice identities in the same batch shape
    ban, ta = W.prompts[(task, "W1", "ban")], W.prompts[(task, "W1", "twin_A")]
    pb, pa = W.pre(ban["ids"]), W.pre(ta["ids"])
    p1 = ban["p1"]
    s_bb = {"kv": splice(pb["kv"], pb["kv"], p1), "r_logits": pb["r_logits"]}
    s_aa = {"kv": splice(pa["kv"], pa["kv"], p1), "r_logits": pa["r_logits"]}
    rows = _rows(W, task, "W1", "a", range(10), s_bb) + _rows(W, task, "W1", "b", range(10), s_aa)
    rows = rows + _rows(W, task, "W1", "c", range(10)) + _rows(W, task, "W1", "d", range(10))
    rows = rows[:W.B] if len(rows) >= W.B else (rows * 4)[:W.B]
    out = sample(W.model, rows, tick_ids=W.tick_ids, decode=W.decode)
    eq_a = [raw[f"{task}|a|W1|{k}"]["token_ids"] == out[k]["token_ids"] for k in range(10)]
    eq_b = [raw[f"{task}|b|W1|{k}"]["token_ids"] == out[10 + k]["token_ids"] for k in range(10)]
    res["U2_splice_ban_ban_equals_a"] = float(np.mean(eq_a))
    res["U2_splice_twin_twin_equals_b"] = float(np.mean(eq_b))
    # ---- U3: eager knockout with recorded attention
    p0 = ban["p0"]
    gen = raw[f"{task}|a|W1|0"]["token_ids"][:8]
    ids = ban["ids"] + gen
    P = len(ban["ids"])
    set_attn(W.model, "ko_eager")
    try:
        RECORD["on"] = True
        RECORD["weights"] = {}
        with torch.no_grad(), knockout({"p0": p0, "p1": p1, "P": P}):
            W.model.model(input_ids=torch.tensor([ids], device=W.model.device))
        ko_mass = [float(RECORD["weights"][l][0, :, P:, p0:p1].sum()) for l in sorted(RECORD["weights"])]
        RECORD["weights"] = {}
        with torch.no_grad():
            W.model.model(input_ids=torch.tensor([ids], device=W.model.device))
        base_mass = [float(RECORD["weights"][l][0, :, P:, p0:p1].sum()) for l in sorted(RECORD["weights"])]
    finally:
        RECORD["on"] = False
        RECORD["weights"] = {}
        set_attn(W.model, "ko_sdpa")
    res["U3_max_mass_under_K0"] = max(ko_mass)
    res["U3_min_mass_without_K0"] = min(base_mass)
    res["U3_n_layers"] = len(ko_mass)
    res["U3_pass"] = bool(max(ko_mass) == 0.0 and min(base_mass) > 0.0)
    # production K0 (condition span dropped from the cache, stock SDPA) vs exp8's masked knockout: logits of the
    # first generated position, and the per-row sampling mask path as a third implementation
    with torch.no_grad():
        full = prefill(W.model, ban["ids"])
        from engine import build_cache, drop_span

        cache = build_cache(drop_span(full["kv"], p0, p1), 1)
        h1 = W.model.model(input_ids=torch.tensor([[gen[0]]], device=W.model.device), past_key_values=cache,
                           position_ids=torch.tensor([[P]], device=W.model.device), use_cache=True).last_hidden_state
        cache3 = build_cache(full["kv"], 1)
        rm = torch.ones((1, 1, 1, P + 2), dtype=torch.bool, device=W.model.device)
        rm[:, :, :, p0:p1] = False
        KO["rowmask"] = rm
        try:
            h3 = W.model.model(input_ids=torch.tensor([[gen[0]]], device=W.model.device), past_key_values=cache3,
                               position_ids=torch.tensor([[P]], device=W.model.device), use_cache=True).last_hidden_state
        finally:
            KO["rowmask"] = None
        cache2 = build_cache(full["kv"], 1)
        with knockout({"p0": p0, "p1": p1, "P": P}):
            h2 = W.model.model(input_ids=torch.tensor([[gen[0]]], device=W.model.device), past_key_values=cache2,
                               position_ids=torch.tensor([[P]], device=W.model.device), use_cache=True).last_hidden_state
        l1 = W.model.lm_head(h1[:, -1]).float()
        l2 = W.model.lm_head(h2[:, -1]).float()
        l3 = W.model.lm_head(h3[:, -1]).float()
        res["U3_spandrop_vs_masked_max_abs_logit_diff"] = float((l1 - l2).abs().max())
        res["U3_rowmask_vs_masked_max_abs_logit_diff"] = float((l3 - l2).abs().max())
        p1_, p2_ = torch.softmax(l1, -1), torch.softmax(l2, -1)
        res["U3_spandrop_vs_masked_tv_distance"] = float(0.5 * (p1_ - p2_).abs().sum())
        res["U3_spandrop_pass"] = bool(res["U3_spandrop_vs_masked_tv_distance"] < 0.02)
    W.clear()
    # ---- U9 labels: wait for the label worker, then score the pass bands
    from gpu import all_labelled, labelled_uids

    uids = [f"{task}|{a}|{w}|{k}" for w in ("W1", "W2") for a in ("a", "b", "c", "d") for k in range(10)]
    W.wait_for(lambda: all_labelled(uids), "U9 labels", poll=10)
    lab = labelled_uids()
    e8 = {(r["condition"], r["template"], r["sample_id"]): r for r in read_jsonl(E8 / "data" / "samples.jsonl")
          if r["task"] == task}
    bands = {"a": ("<=", 6), "b": (">=", 17), "c": ("<=", 7), "d": (">=", 16)}
    out9 = {}
    for a, (op, thr) in bands.items():
        rows = [lab[f"{task}|{a}|{w}|{k}"] for w in ("W1", "W2") for k in range(10)]
        nb = sum(r["label"] == "dijkstra" for r in rows)
        ok = nb <= thr if op == "<=" else nb >= thr
        agree = [lab[f"{task}|{a}|{w}|{k}"]["label"] == e8[(a, w, k)]["label"] for w in ("W1", "W2") for k in range(10)
                 if (a, w, k) in e8]
        same_ids = [lab[f"{task}|{a}|{w}|{k}"]["token_ids"] == e8[(a, w, k)]["token_ids"] for w in ("W1", "W2")
                    for k in range(10) if (a, w, k) in e8]
        out9[a] = {"banned": nb, "n": len(rows), "band": f"{op}{thr}", "pass": bool(ok),
                   "label_agreement_with_exp8_same_slot": float(np.mean(agree)) if agree else None,
                   "identical_ids_with_exp8_same_slot": float(np.mean(same_ids)) if same_ids else None}
    res["U9"] = out9
    res["U9_pass"] = all(v["pass"] for v in out9.values())
    order_ok = (out9["a"]["banned"] < out9["b"]["banned"] and out9["c"]["banned"] < out9["d"]["banned"])
    res["U9_ordering_holds"] = bool(order_ok)
    res["seconds"] = time.time() - t0
    write_json(RESULTS_DIR / "engine_validation.json", res)
    logger.info(f"engine tests: U1 {res['U1_identical_fraction']:.2f}, U2 {res['U2_splice_ban_ban_equals_a']:.2f}/"
                f"{res['U2_splice_twin_twin_equals_b']:.2f}, U3 {res['U3_pass']} "
                f"(span-drop vs mask TV {res['U3_spandrop_vs_masked_tv_distance']:.4f}), U9 pass={res['U9_pass']} "
                f"{ {a: v['banned'] for a, v in out9.items()} }")
    return res


def W_RAW():
    from cfg import RAW

    return RAW
