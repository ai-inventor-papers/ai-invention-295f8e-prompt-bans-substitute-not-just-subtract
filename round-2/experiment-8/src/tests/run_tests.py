#!/usr/bin/env python3
"""U0-U7 + U9 tests (results/tests.json). GPU tests use the same HF engine as the stages.

U0 environment; U1 labeller (results/labeller_recheck.json from S0 + smoke labels); U2 prompt alignment;
U3 engine equivalence; U4 knockout correctness (eager twin, recorded attention); U5 CRN determinism + marginal;
U6 FRLP mini sanity + sampler/scorer self-consistency; U7 placebo / neutral-knockout control on the mini run;
U9 synthetic analysis checks.
"""

from __future__ import annotations

import json
import time
from typing import Any

import numpy as np
import torch
from loguru import logger
from scipy import stats

from cfg import (DATA_DIR, PROMPTS_DIR, RESULTS_DIR, TASKS, TEMPLATE_IDS, X_KEY, read_jsonl, write_json, chat_ids,
                 TEMPLATE_TAIL)

OUT = RESULTS_DIR / "tests.json"


def _save(res: dict[str, Any]) -> None:
    write_json(OUT, res)


def u2_alignment(fp: dict[str, Any]) -> dict[str, Any]:
    out = {"cells": [], "all_ok": True}
    for t in TASKS:
        for w in TEMPLATE_IDS:
            tw = fp["tasks"][t]["templates"][w]
            b = tw["ban"]
            for slot in ("neutral_A", "neutral_B"):
                n = tw[slot]
                diff = [i for i, (x, y) in enumerate(zip(b["ids"], n["ids"])) if x != y]
                ok = (len(b["ids"]) == len(n["ids"]) and b["ids"][b["p1"]:] == n["ids"][n["p1"]:]
                      and b["ids"][-1] == n["ids"][-1] and min(diff) >= b["p0"] and max(diff) < b["p1"])
                out["cells"].append({"task": t, "template": w, "slot": slot, "ok": ok, "P": len(b["ids"]),
                                     "p0": b["p0"], "p1": b["p1"], "diff_span": [min(diff), max(diff) + 1],
                                     "ban_segment": b["segment"], "neutral_segment": n["segment"]})
                out["all_ok"] &= ok
    return out


def run_all() -> dict[str, Any]:
    from analysis import synthetic_checks
    from arms import build_arm, ko_config
    from engine import (RECORD, knockout, load_model, prefill, sample, score, set_attn, splice, u_stream)

    fp = json.loads((PROMPTS_DIR / "frozen_prompts.json").read_text())
    res: dict[str, Any] = json.loads(OUT.read_text()) if OUT.exists() else {}
    res["U2"] = u2_alignment(fp)
    res["U9"] = synthetic_checks()
    res["U1"] = json.loads((RESULTS_DIR / "labeller_recheck.json").read_text())
    res["U1"] = {k: v for k, v in res["U1"].items() if k != "references"}
    _save(res)
    tok, model = load_model()
    free, total = torch.cuda.mem_get_info(0)
    ids = chat_ids(tok, "hi")
    res["U0"] = {"gpu": torch.cuda.get_device_name(0), "total_gb": total / 1e9, "free_gb_after_load": free / 1e9,
                 "free_ok": free / 1e9 >= 2.5, "last6_ids": ids[-6:], "last6_decoded": tok.decode(ids[-6:]),
                 "ends_with_empty_think": tok.decode(ids).endswith(TEMPLATE_TAIL)}
    _save(res)
    progs = [p for p in read_jsonl(DATA_DIR / "frlp_programs.jsonl")]
    # ---------------------------------------------------------------- U3
    u3: dict[str, Any] = {}
    for t in TASKS:
        tw = fp["tasks"][t]["templates"]["W1"]
        pp = [p for p in progs if p["task"] == t][:3]
        ban = prefill(model, tw["ban"]["ids"])
        neu = prefill(model, tw["neutral_A"]["ids"])
        seqs = [p["score_ids"] for p in pp]
        lp_cache = score(model, ban, seqs)
        diffs = []
        for s, lpc in zip(seqs, lp_cache):
            full = torch.tensor([tw["ban"]["ids"] + s], device=model.device)
            with torch.no_grad():
                logits = model(input_ids=full).logits[0].float()
            P = len(tw["ban"]["ids"])
            lsm = torch.log_softmax(logits[P - 1:P - 1 + len(s)], -1)
            lp_full = lsm.gather(-1, torch.tensor(s, device=model.device)[:, None])[:, 0].cpu().numpy()
            diffs.append(float(np.mean(np.abs(lp_full - lpc))))
        # splice identity
        p1 = tw["ban"]["p1"]
        lp_a2 = score(model, ban, seqs[:2])
        aa = {"kv": splice(ban["kv"], ban["kv"], p1), "r_logits": ban["r_logits"]}
        lp_aa = score(model, aa, seqs[:2])
        bb = {"kv": splice(neu["kv"], neu["kv"], p1), "r_logits": neu["r_logits"]}
        lp_b = score(model, neu, seqs[:2])
        lp_bb = score(model, bb, seqs[:2])
        ident_a = all(np.array_equal(x, y) for x, y in zip(lp_aa, lp_a2))
        batch1_repro = all(np.array_equal(x, y) for x, y in zip(lp_a2, lp_cache[:2]))
        ident_b = all(np.array_equal(x, y) for x, y in zip(lp_bb, lp_b))
        # ko_sdpa inactive vs stock sdpa
        set_attn(model, "sdpa")
        lp_stock = score(model, ban, seqs[:2])
        set_attn(model, "ko_sdpa")
        stock_diff = max(float(np.max(np.abs(x - y))) for x, y in zip(lp_stock, lp_a2))
        # empty-span KO == no KO
        lp_empty = score(model, ban, seqs[:2], ko={"p0": 5, "p1": 5, "g_lo": 0, "g_hi": 10 ** 9, "layers": None})
        empty_diff = max(float(np.max(np.abs(x - y))) for x, y in zip(lp_empty, lp_a2))
        lp_b2 = score(model, ban, seqs[:2], max_batch=2)
        batch2_diff = max(float(np.max(np.abs(x - y))) for x, y in zip(lp_b2, lp_a2))
        batch2_mean = float(np.mean([np.mean(np.abs(x - y)) for x, y in zip(lp_b2, lp_a2)]))
        u3[t] = {"prefill_vs_single_pass_mean_abs": diffs, "prefill_ok": max(diffs) < 0.02,
                 "splice_ban_ban_identical": ident_a, "splice_neu_neu_identical": ident_b,
                 "ko_inactive_vs_stock_max_abs": stock_diff, "stock_ok": stock_diff < 1e-3,
                 "empty_span_max_abs": empty_diff, "empty_ok": empty_diff < 1e-6,
                 "batch1_reproducible_across_calls": batch1_repro,
                 "batch2_vs_batch1_max_abs_per_token": batch2_diff, "batch2_vs_batch1_mean_abs_per_token": batch2_mean}
    res["U3"] = u3
    _save(res)
    logger.info(f"U3: {u3}")
    # ---------------------------------------------------------------- U4
    t = "t1"
    tw = fp["tasks"][t]["templates"]["W1"]
    p0, p1 = tw["ban"]["p0"], tw["ban"]["p1"]
    prog = [p for p in progs if p["task"] == t][0]["score_ids"][:40]
    ids = tw["ban"]["ids"] + prog
    P = len(tw["ban"]["ids"])
    L = 20
    u4: dict[str, Any] = {}
    set_attn(model, "ko_eager")
    try:
        def run(cfg):
            RECORD["on"], RECORD["weights"] = True, {}
            with knockout(cfg), torch.no_grad():
                model.model(input_ids=torch.tensor([ids], device=model.device))
            RECORD["on"] = False
            return dict(RECORD["weights"])

        w0 = run(None)
        wk = run({"p0": p0, "p1": p1, "P": P, "g_lo": 0, "g_hi": 10 ** 9, "layers": {L}})
        wk1 = run({"p0": p0, "p1": p1, "P": P, "g_lo": 0, "g_hi": 16, "layers": {L}})
        wk2 = run({"p0": p0, "p1": p1, "P": P, "g_lo": 16, "g_hi": 10 ** 9, "layers": {L}})
        gen_rows = slice(P, len(ids))
        mass = float(wk[L][0, :, gen_rows, p0:p1].sum(-1).max())
        mass0 = float(w0[L][0, :, gen_rows, p0:p1].sum(-1).mean())
        unchanged_before = max(float((wk[l] - w0[l]).abs().max()) for l in range(L))
        k1_rows_blocked = float(wk1[L][0, :, P:P + 16, p0:p1].sum(-1).max())
        k1_rows_open = float(wk1[L][0, :, P + 16:, p0:p1].sum(-1).mean())
        k2_rows_blocked = float(wk2[L][0, :, P + 16:, p0:p1].sum(-1).max())
        k2_rows_open = float(wk2[L][0, :, P:P + 16, p0:p1].sum(-1).mean())
        prompt_rows_same = float((wk[L][0, :, :P] - w0[L][0, :, :P]).abs().max())
        u4 = {"layer": L, "blocked_mass_max": mass, "baseline_mass_mean": mass0, "blocked_ok": mass < 1e-6,
              "layers_before_unchanged_max_abs": unchanged_before, "prompt_rows_unchanged_max_abs": prompt_rows_same,
              "K1_blocked_rows_mass": k1_rows_blocked, "K1_open_rows_mass": k1_rows_open,
              "K2_blocked_rows_mass": k2_rows_blocked, "K2_open_rows_mass": k2_rows_open,
              "K1_K2_ok": k1_rows_blocked < 1e-6 and k2_rows_blocked < 1e-6 and k1_rows_open > 1e-4
              and k2_rows_open > 1e-4}
        # ko_eager vs ko_sdpa log-prob agreement under the same knockout
        ban = prefill(model, tw["ban"]["ids"])
        set_attn(model, "ko_sdpa")
        kcfg = ko_config("K0", p0, p1)
        lp_s = score(model, {"kv": ban["kv"], "r_logits": ban["r_logits"]}, [prog], ko=kcfg)[0]
        set_attn(model, "ko_eager")
        lp_e = score(model, {"kv": ban["kv"], "r_logits": ban["r_logits"]}, [prog], ko=kcfg)[0]
        u4["sdpa_vs_eager_ko_max_abs"] = float(np.max(np.abs(lp_s - lp_e)))
    finally:
        RECORD["on"] = False
        set_attn(model, "ko_sdpa")
    res["U4"] = u4
    _save(res)
    logger.info(f"U4: {u4}")
    # ---------------------------------------------------------------- U5
    u5: dict[str, Any] = {}
    tw = fp["tasks"]["t1"]["templates"]["W1"]
    ban = prefill(model, tw["ban"]["ids"])
    rows = [{"kv": ban["kv"], "r_logits": ban["r_logits"], "u": u_stream("u5test", s)} for s in range(20)]
    t0 = time.time()
    r1 = sample(model, rows, prune=False)
    r2 = sample(model, rows, prune=False)
    t_batch = time.time() - t0
    same = sum(a["token_ids"] == b["token_ids"] for a, b in zip(r1, r2))
    aa = {"kv": splice(ban["kv"], ban["kv"], tw["ban"]["p1"]), "r_logits": ban["r_logits"]}
    r3 = sample(model, [{**r, "kv": aa["kv"]} for r in rows], prune=False)
    same_splice = sum(a["token_ids"] == b["token_ids"] for a, b in zip(r1, r3))
    r4 = sample(model, rows[:10], prune=True)
    same_comp = sum(a["token_ids"] == b["token_ids"] for a, b in zip(r1[:10], r4))
    # marginal check at R: 2000 inverse-CDF draws vs softmax
    from engine import _inverse_cdf

    probs = torch.softmax(ban["r_logits"].double(), -1)
    u = torch.tensor(np.random.default_rng(1).random(2000), dtype=torch.float64, device=probs.device)
    draws = torch.cat([_inverse_cdf(probs[None].expand(len(u[i:i + 100]), -1).contiguous(), u[i:i + 100])
                       for i in range(0, 2000, 100)]).cpu().numpy()
    pr = probs.cpu().numpy()
    top = np.argsort(-pr)
    exp_counts, obs_counts, acc = [], [], 0.0
    for tid in top:
        if pr[tid] * 2000 < 5:
            break
        exp_counts.append(pr[tid] * 2000)
        obs_counts.append(int((draws == tid).sum()))
        acc += pr[tid]
    exp_counts.append((1 - acc) * 2000)
    obs_counts.append(2000 - sum(obs_counts))
    if exp_counts[-1] < 1e-9:
        exp_counts, obs_counts = exp_counts[:-1], obs_counts[:-1]
    if len(exp_counts) >= 2:
        chi = stats.chisquare(obs_counts, np.array(exp_counts) * sum(obs_counts) / sum(exp_counts))
        chi_p = float(chi.pvalue)
    else:
        chi_p = 1.0
    u5 = {"self_agreement_identical_share": same / 20, "floor_ok": same / 20 >= 0.95,
          "splice_ban_ban_identical_share": same_splice / 20,
          "different_batch_shape_identical_share": same_comp / 10, "chi2_p_marginal_R": chi_p,
          "chi2_bins": len(exp_counts), "marginal_ok": chi_p > 0.01, "seconds_per_batch20": t_batch / 2,
          "mean_tokens": float(np.mean([r["n_tokens"] for r in r1]))}
    res["U5"] = u5
    _save(res)
    logger.info(f"U5: {u5}")
    # ---------------------------------------------------------------- U6 / U7 (mini FRLP: T1, W1, 10 BFS programs)
    from engine import ess, logmeanexp

    t = "t1"
    tw = fp["tasks"][t]["templates"]["W1"]
    X = [p for p in progs if p["task"] == t and p["algorithm"] == X_KEY[t]][:10]
    pre = {"ban": prefill(model, tw["ban"]["ids"]), "A": prefill(model, tw["neutral_A"]["ids"]),
           "B": prefill(model, tw["neutral_B"]["ids"])}
    fr = fp["tasks"][t]["forced"][X_KEY[t]]
    den = []
    for k in range(10):
        pk = prefill(model, fr["paraphrases"][k]["ids"])
        den.append([float(x.sum()) for x in score(model, pk, [p["score_ids"] for p in X])])
    den = np.array(den)  # [10, M]
    lden = logmeanexp(den, axis=0)
    seqs = [p["score_ids"] for p in X]
    ll = {}
    for arm, noun in (("a", "A"), ("b", "A"), ("pl", "B"), ("K0b", "A"), ("bB", "B")):
        a = build_arm("b" if arm == "bB" else arm, pre, noun, tw["ban"]["p1"])
        ko = ko_config(arm, tw["ban"]["p0"], tw["ban"]["p1"])
        ll[arm] = np.array([float(x.sum()) for x in score(model, a, seqs, ko=ko)])
    Lx = {k: float(logmeanexp(v - lden)) for k, v in ll.items()}
    E = {k: ess(v - lden) for k, v in ll.items()}
    # self-consistency: unscrubbed generated tokens under their generating paraphrase vs sampler log-prob
    sc = []
    for p in X[:5]:
        if p["prompt_kind"] != "paraphrase":
            continue
        pk = prefill(model, fr["paraphrases"][p["prompt_index"]]["ids"])
        lp = score(model, pk, [p["gen_token_ids"]])[0]
        if p.get("sampled_logprob") is not None:
            sc.append(abs(float(lp.sum()) - p["sampled_logprob"]) / len(lp))
    summ = json.loads((RESULTS_DIR / "frlp_programs_summary.json").read_text())
    u6 = {"L_b_minus_L_a": Lx["b"] - Lx["a"], "ban_effect_positive": Lx["b"] - Lx["a"] > 0, "ESS": E,
          "L": Lx, "self_consistency_mean_abs_per_token": sc,
          "self_consistency_ok": bool(sc) and max(sc) < 0.05, "scrub": summ["scrub"]}
    u7 = {"D_placebo": Lx["pl"] - Lx["bB"], "D_a": Lx["a"] - Lx["b"],
          "placebo_ok": abs(Lx["pl"] - Lx["bB"]) < 0.2 * abs(Lx["a"] - Lx["b"]),
          "K0b_delta": Lx["K0b"] - Lx["b"], "K0b_ok": abs(Lx["K0b"] - Lx["b"]) < abs(Lx["a"] - Lx["b"])}
    res["U6"], res["U7"] = u6, u7
    _save(res)
    logger.info(f"U6: {u6}\nU7: {u7}")
    return res
