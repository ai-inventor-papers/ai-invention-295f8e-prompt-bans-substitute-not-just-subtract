#!/usr/bin/env python3
"""B1: base vs instruct teacher-forced on IDENTICAL ids at counterfactually located forks (Gemma-3-4b pt/it on G-GRID,
G-T04, G-R6; Llama-3.1-8B base/instruct on L-GRID), generalising iteration 8's base_arm (art_lzuosbrb34wB).

GPU (one model per call): per unit, prompt, fork and template mode (chat / template-free 'plain'): the fork distribution
(top-256 log-probs + entropy + argmax), log P(D class) - log P(A class), P(D), P(A); the instruct model's log P(opening)
(on-policy check); per phrasing program (20 instruct programs per unit): per-position entropy, log-prob and rank of the
program token, and top-256 log-probs over the first 64 generated tokens. Llama base also records the chat-token
embedding-norm check.
Analysis: margins and gains (bootstrap 10,000), phrasing entropy change, JS at fork / entropy-matched / rate-matched
random / phrasing positions, URIAL ranks, argmax agreement, the base fork distribution pushed through the instruct
token map, Cantarero's base-entropy fork set (q 0.90), and the committed P1-P4 verdict.
Usage: b1_9.py gpu <gemma|gemma_pt|llama|llama_base> | analyze
"""

from __future__ import annotations

import gc
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger

import stats9 as S
from cfg9 import (GEMMA_MASS_MIN, LLAMA_CHAT_NORM_FRAC, N_BOOT, NEAR_COLLAPSE, NPOS, ONPOLICY_MIN_LOGP, Q_FORK,
                  RESULTS_DIR, SEED_BOOT, THRESH, TOPK, V43, model_path, read_json, setup_logging, stage_time,
                  utc_now, write_json)
from units9 import load_units

FAMILY_UNITS = {"gemma": ("G-GRID", "G-T04", "G-R6"), "llama": ("L-GRID",)}
PAIR = {"gemma": ("gemma", "gemma_pt"), "llama": ("llama", "llama_base")}


def _load_gemma(path: str) -> Any:
    """Text-only Gemma3ForCausalLM from the multimodal checkpoint (iteration-8 engine8._load_gemma)."""
    from safetensors import safe_open
    from transformers import AutoConfig, Gemma3ForCausalLM
    cfg = AutoConfig.from_pretrained(path)
    tcfg = cfg.text_config
    tcfg._attn_implementation = "sdpa"
    old = torch.get_default_dtype()
    torch.set_default_dtype(torch.bfloat16)
    try:
        with torch.device("cuda"):
            model = Gemma3ForCausalLM(tcfg)
    finally:
        torch.set_default_dtype(old)
    sd = model.state_dict()
    loaded = set()
    idx = json.loads((Path(path) / "model.safetensors.index.json").read_text())
    for fn in sorted(set(idx["weight_map"].values())):
        with safe_open(str(Path(path) / fn), framework="pt", device="cuda") as fh:
            for k in fh.keys():
                for pre in ("language_model.model.", "model.language_model."):
                    if k.startswith(pre):
                        nk = "model." + k[len(pre):]
                        break
                else:
                    continue
                assert nk in sd, f"unexpected key {k}"
                t = fh.get_tensor(k)
                assert sd[nk].shape == t.shape, (nk, sd[nk].shape, t.shape)
                sd[nk].copy_(t.to(sd[nk].dtype))
                loaded.add(nk)
                del t
    model.tie_weights()
    missing = sorted(set(k for k in sd if not k.startswith("lm_head")) - loaded)
    assert not missing, f"weights not loaded: {missing[:5]}"
    return model


def load(key: str) -> tuple[Any, Any, dict]:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    t0 = time.time()
    path = model_path(key)
    tok = AutoTokenizer.from_pretrained(model_path("gemma" if key.startswith("gemma") else "llama"))
    if key.startswith("gemma"):
        model = _load_gemma(path)
    else:
        model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, attn_implementation="sdpa",
                                                     device_map={"": 0}, low_cpu_mem_usage=True)
    model.eval()
    model.requires_grad_(False)
    gc.collect()
    torch.cuda.empty_cache()
    free, _ = torch.cuda.mem_get_info(0)
    info = {"model": key, "snapshot": path.split("/")[-1], "load_s": round(time.time() - t0, 1),
            "free_vram_after_GB": round(free / 1e9, 2)}
    logger.info(f"loaded {key}: {info}")
    return model, tok, info


@torch.no_grad()
def fork_rec(model: Any, ids: list[int], f: dict, n_open: int) -> dict[str, Any]:
    o = model(input_ids=torch.tensor([ids], device="cuda"), use_cache=False, logits_to_keep=n_open + 1)
    lg = o.logits[0].float()
    lp_all = torch.log_softmax(lg.double(), -1)
    lp = lp_all[-1]
    lD = float(torch.logsumexp(lp[f["D"]], 0))
    lA = float(torch.logsumexp(lp[f["A"]], 0))
    top = torch.topk(lp, TOPK)
    op = f["opening"]
    logp_open = float(sum(lp_all[j, op[j]] for j in range(len(op))))
    rec = {"logP_D": lD, "logP_A": lA, "margin": lD - lA, "pD": float(np.exp(lD)), "pA": float(np.exp(lA)),
           "entropy": float(-(lp.exp() * lp).sum()), "argmax": int(lp.argmax()), "top_ids": top.indices.tolist(),
           "top_lp": [round(float(x), 5) for x in top.values], "logp_opening": logp_open,
           "p_tokens": {t: float(lp[int(t)].exp()) for t in f.get("phat", {})}}
    del o
    return rec


@torch.no_grad()
def prog_rec(model: Any, pids: list[int], prog: list[int]) -> dict[str, Any]:
    prog = prog[:NPOS]
    ids = torch.tensor([list(pids) + list(prog)], device="cuda")
    o = model(input_ids=ids, use_cache=False, logits_to_keep=len(prog) + 1)
    lp = torch.log_softmax(o.logits[0, :len(prog)].float(), -1)
    t = torch.tensor(prog, device="cuda")
    ent = (-(lp.exp() * lp).sum(-1)).tolist()
    lpt = lp.gather(-1, t[:, None]).squeeze(-1)
    rank = ((lp > lpt[:, None]).sum(-1) + 1).tolist()
    top = torch.topk(lp, TOPK, -1)
    out = {"ids": prog, "entropy": ent, "logp": lpt.tolist(), "rank": rank,
           "top_ids": top.indices.cpu().numpy().astype(np.int32).tolist(),
           "top_lp": np.round(top.values.cpu().numpy(), 4).tolist()}
    del o, lp
    return out


def gpu(key: str) -> None:
    t0 = time.time()
    fam = "gemma" if key.startswith("gemma") else "llama"
    model, tok, info = load(key)
    U = load_units()
    out: dict[str, Any] = {"model": key, "load": info, "units": {}, "utc": utc_now()}
    if key == "llama_base":
        W = model.model.embed_tokens.weight.float()
        norms = W.norm(dim=-1)
        med = float(norms.median())
        ids = {"<|start_header_id|>": 128006, "<|end_header_id|>": 128007, "<|eot_id|>": 128009}
        chk = {k: float(norms[v]) for k, v in ids.items()}
        out["chat_token_norm_check"] = {"row_norms": chk, "median_row_norm": med,
                                        "ratio": {k: v / med for k, v in chk.items()},
                                        "template_free_primary": any(v < LLAMA_CHAT_NORM_FRAC * med
                                                                     for v in chk.values())}
        logger.info(f"Llama base chat-token norms: {out['chat_token_norm_check']}")
        del W, norms
    for u in FAMILY_UNITS[fam]:
        Uu = U[u]
        recs = []
        for p in Uu["prompts"]:
            r = {"pid": p["pid"], "template": p["template"], "rank": p.get("rank", 0), "forks": {}}
            for f in Uu["forks"]:
                r["forks"][f["fork_id"]] = {mode: fork_rec(model, (p["ids"] if mode == "chat" else p["ids_plain"]) +
                                                           f["opening"], f, len(f["opening"]))
                                            for mode in ("chat", "plain")}
            recs.append(r)
        progs = []
        P0 = {p["template"]: p for p in Uu["prompts"] if p.get("rank", 0) == 0}
        for pr in Uu["programs"][:20]:
            pp = P0[pr["template"]]
            progs.append(dict(prog_rec(model, pp["ids"], pr["ids"]), template=pr["template"], slot=pr["slot"]))
        out["units"][u] = {"prompts": recs, "programs": progs}
        f0 = Uu["forks"][0]["fork_id"]
        logger.info(f"{key} {u}: chat margins {[round(r['forks'][f0]['chat']['margin'], 2) for r in recs][:8]}")
    write_json(RESULTS_DIR / f"b1_tf_{key}.json", out)
    del model
    gc.collect()
    torch.cuda.empty_cache()
    stage_time(f"b1_gpu_{key}", time.time() - t0)


# ================================================================================================ analysis
def _rank_bucket(r: int) -> str:
    return "1" if r == 1 else ("2-3" if r <= 3 else ">3")


def analyze_unit(fam: str, u: str, Uu: dict, I: dict, B: dict, rng: np.random.Generator,
                 llama_tf_primary: bool | None) -> dict[str, Any]:
    pI = {r["pid"]: r for r in I["units"][u]["prompts"]}
    pB = {r["pid"]: r for r in B["units"][u]["prompts"]}
    out: dict[str, Any] = {"family": fam, "unit": u, "forks": {}}
    f0 = Uu["forks"][0]
    # on-policy selection (instruct only, chat mode, every fork's own opening)
    keep, dropped = [], []
    for p in Uu["prompts"]:
        lps = [pI[p["pid"]]["forks"][f["fork_id"]]["chat"]["logp_opening"] for f in Uu["forks"]]
        (keep if min(lps) >= ONPOLICY_MIN_LOGP else dropped).append((p["pid"], min(lps)))
    keep_ids = [k for k, _ in keep][:Uu.get("max_prompts", 20)]
    out["on_policy"] = {"kept": keep_ids, "dropped": dropped, "n_candidates": len(Uu["prompts"])}
    out["descriptive_only"] = False
    if not keep_ids:
        # committed rule drops every prompt: report descriptively on all prompts, excluded from the verdict
        keep_ids = [p["pid"] for p in Uu["prompts"]][:Uu.get("max_prompts", 20)]
        out["descriptive_only"] = True
        out["on_policy"]["note"] = ("every prompt fails the committed on-policy rule (instruct log P(opening) < -5); "
                                    "numbers below use all prompts and are DESCRIPTIVE, excluded from P1-P4")
    # phrasing positions (shared across forks of the unit)
    progI, progB = I["units"][u]["programs"], B["units"][u]["programs"]
    for f in Uu["forks"]:
        fid = f["fork_id"]
        d = len(f["opening"])
        res: dict[str, Any] = {}
        for mode in ("chat", "plain"):
            mi = np.array([pI[k]["forks"][fid][mode]["margin"] for k in keep_ids])
            mb = np.array([pB[k]["forks"][fid][mode]["margin"] for k in keep_ids])
            g = mi - mb
            res[mode] = {"margin_instr": mi.tolist(), "margin_base": mb.tolist(), "gain": g.tolist(),
                         "gain_mean": float(g.mean()), "gain_ci95": S.boot_mean_ci(g, N_BOOT, SEED_BOOT),
                         "pD_instr_mean": float(np.mean([pI[k]["forks"][fid][mode]["pD"] for k in keep_ids])),
                         "pD_base_mean": float(np.mean([pB[k]["forks"][fid][mode]["pD"] for k in keep_ids])),
                         "pDA_base_mean": float(np.mean([pB[k]["forks"][fid][mode]["pD"] +
                                                         pB[k]["forks"][fid][mode]["pA"] for k in keep_ids])),
                         "entropy_instr_mean": float(np.mean([pI[k]["forks"][fid][mode]["entropy"] for k in keep_ids])),
                         "entropy_base_mean": float(np.mean([pB[k]["forks"][fid][mode]["entropy"] for k in keep_ids])),
                         "argmax_differs": [pI[k]["forks"][fid][mode]["argmax"] != pB[k]["forks"][fid][mode]["argmax"]
                                            for k in keep_ids],
                         "js_fork": [S.js_div(pI[k]["forks"][fid][mode]["top_ids"], pI[k]["forks"][fid][mode]["top_lp"],
                                              pB[k]["forks"][fid][mode]["top_ids"], pB[k]["forks"][fid][mode]["top_lp"])
                                     for k in keep_ids]}
            # rank of the instruct argmax under the base model at the fork
            rk = []
            for k in keep_ids:
                a = pI[k]["forks"][fid][mode]["argmax"]
                tb = pB[k]["forks"][fid][mode]["top_ids"]
                rk.append(tb.index(a) + 1 if a in tb else TOPK + 1)
            res[mode]["base_rank_of_instr_argmax"] = rk
            # pushed-through mix: sum_tok p_base(tok) P_I(alg | tok)
            if f.get("phat"):
                bins = f.get("bins") or []
                mix = np.zeros(len(bins))
                mapped = 0.0
                for k in keep_ids:
                    pt = pB[k]["forks"][fid][mode]["p_tokens"]
                    for t, ph in f["phat"].items():
                        mix += pt.get(t, 0.0) * np.asarray(ph, dtype=float) / len(keep_ids)
                        mapped += pt.get(t, 0.0) / len(keep_ids)
                mixI = np.zeros(len(bins))
                for k in keep_ids:
                    pt = pI[k]["forks"][fid][mode]["p_tokens"]
                    for t, ph in f["phat"].items():
                        mixI += pt.get(t, 0.0) * np.asarray(ph, dtype=float) / len(keep_ids)
                res[mode]["pushed_through_base"] = {b: float(x) for b, x in zip(bins, mix)}
                res[mode]["pushed_through_instr"] = {b: float(x) for b, x in zip(bins, mixI)}
                res[mode]["base_mass_mapped"] = mapped
                res[mode]["base_mass_unmapped"] = 1 - mapped
        # phrasing statistics (chat mode programs)
        dH, prog_dh, jsP, Hb_all, ranks, dec_rank = [], [], [], [], {}, {}
        for a, b in zip(progI, progB):
            on_dec = a["ids"][:d] == f["opening"]
            per = []
            for k in range(min(len(a["entropy"]), len(b["entropy"]))):
                if k == d and on_dec:
                    bk = _rank_bucket(b["rank"][k])
                    dec_rank[bk] = dec_rank.get(bk, 0) + 1
                    continue
                per.append(b["entropy"][k] - a["entropy"][k])
                Hb_all.append(b["entropy"][k])
                bk = _rank_bucket(b["rank"][k])
                ranks[bk] = ranks.get(bk, 0) + 1
                jsP.append((S.js_div(a["top_ids"][k], a["top_lp"][k], b["top_ids"][k], b["top_lp"][k]),
                            b["entropy"][k]))
            dH += per
            prog_dh.append(per)
        js_arr = np.array([x for x, _ in jsP])
        Hjs = np.array([h for _, h in jsP])
        Hb_arr = np.array(Hb_all)
        fork_mode = "chat"
        js_dec = np.array(res[fork_mode]["js_fork"])
        Hb_dec = float(np.mean([pB[k]["forks"][fid][fork_mode]["entropy"] for k in keep_ids]))
        qs = np.quantile(Hb_arr, np.linspace(0, 1, 11))
        dq = int(np.clip(np.searchsorted(qs[1:-1], Hb_dec), 0, 9))
        lo, hi = qs[dq], qs[dq + 1]
        matched = js_arr[(Hjs >= lo) & (Hjs <= hi)]
        rsel = rng.choice(len(js_arr), size=min(len(js_arr), 5 * len(js_dec)), replace=False)
        rand = js_arr[rsel]
        boots = []
        for _ in range(1000):
            ii = rng.integers(0, len(prog_dh), len(prog_dh))
            v = [x for i in ii for x in prog_dh[i]]
            boots.append(float(np.mean(v)) if v else 0.0)
        # Cantarero fork set: base entropy >= q90 of the unit's pooled base entropies (phrasing + fork positions)
        pooled = np.concatenate([Hb_arr, [pB[k]["forks"][fid][fork_mode]["entropy"] for k in keep_ids]])
        thr = float(np.quantile(pooled, Q_FORK))
        inside = Hjs >= thr
        js_in = js_arr[inside]
        js_out = js_arr[~inside]
        # entropy-adjusted: each inside position vs the outside position with the nearest base entropy
        out_idx = np.where(~inside)[0]
        order = out_idx[np.argsort(Hjs[out_idx])]
        Hs = Hjs[order]
        adj = []
        for i in np.where(inside)[0]:
            j = int(np.clip(np.searchsorted(Hs, Hjs[i]), 1, len(Hs) - 1)) if len(Hs) > 1 else 0
            cand = [order[max(j - 1, 0)], order[min(j, len(order) - 1)]]
            nn = min(cand, key=lambda c: abs(Hjs[c] - Hjs[i]))
            adj.append(js_arr[nn])
        rate = float(inside.mean())
        rr = []
        for _ in range(1000):
            m = rng.random(len(js_arr)) < rate
            if m.sum() and (~m).sum():
                rr.append(float(js_arr[m].mean() / max(js_arr[~m].mean(), 1e-12)))
        res["phrasing"] = {
            "n_positions": len(dH), "dH_mean": float(np.mean(dH)) if dH else None,
            "dH_ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
            "urial_rank_phrasing": ranks, "urial_rank1_share": ranks.get("1", 0) / max(1, sum(ranks.values())),
            "urial_rank_decision_programs": dec_rank, "js_phrasing_mean": float(js_arr.mean()),
            "js_fork_mean": float(js_dec.mean()), "js_entropy_matched_mean": float(matched.mean()) if len(matched)
            else None, "n_entropy_matched": int(len(matched)), "js_random_mean": float(rand.mean()),
            "ratio_fork_vs_matched": float(js_dec.mean() / matched.mean()) if len(matched) else None,
            "ratio_random_vs_phrasing": float(rand.mean() / js_arr.mean()),
            "ratio_fork_vs_phrasing": float(js_dec.mean() / js_arr.mean()),
            "fork_base_entropy_mean": Hb_dec, "fork_base_entropy_pctile": float((Hb_arr < Hb_dec).mean() * 100),
            "entropy_decile_of_fork": dq}
        res["cantarero"] = {"q": Q_FORK, "threshold_nats": thr, "n_inside": int(inside.sum()),
                            "js_inside_mean": float(js_in.mean()) if len(js_in) else None,
                            "js_outside_mean": float(js_out.mean()) if len(js_out) else None,
                            "ratio_inside_outside": float(js_in.mean() / js_out.mean()) if len(js_in) and len(js_out)
                            else None,
                            "ratio_inside_vs_entropy_nn_outside": float(js_in.mean() / np.mean(adj)) if adj else None,
                            "rate_matched_random_ratio_mean": float(np.mean(rr)) if rr else None,
                            "rate_matched_random_ratio_p95": float(np.percentile(rr, 95)) if rr else None,
                            "counterfactual_fork_inside": bool(Hb_dec >= thr)}
        # template-primary rules (committed)
        if fam == "gemma":
            prim = "plain" if res["chat"]["pDA_base_mean"] < GEMMA_MASS_MIN else "chat"
            rule = f"pt mass on D or A under chat = {res['chat']['pDA_base_mean']:.4f} (< {GEMMA_MASS_MIN} -> plain)"
        else:
            prim = "plain" if llama_tf_primary else "chat"
            rule = f"Llama chat-token norm rule -> {'plain' if llama_tf_primary else 'chat'}"
        res["primary_mode"] = prim
        res["primary_rule"] = rule
        pm = res[prim]
        res["near_collapsed"] = bool(pm["pD_instr_mean"] >= NEAR_COLLAPSE)
        res["P1_gain_ge_2"] = bool(pm["gain_mean"] >= THRESH["B1_P1_gain"])
        res["P4_argmax_differs_majority"] = bool(np.mean(pm["argmax_differs"]) > 0.5)
        out["forks"][fid] = res
    return out


def analyze() -> dict[str, Any]:
    U = load_units()
    rng = np.random.default_rng(SEED_BOOT + 5)
    summary: dict[str, Any] = {"units": {}, "utc": utc_now()}
    llama_rule = None
    for fam, (ki, kb) in PAIR.items():
        pi, pb = RESULTS_DIR / f"b1_tf_{ki}.json", RESULTS_DIR / f"b1_tf_{kb}.json"
        if not (pi.exists() and pb.exists()):
            logger.warning(f"B1 {fam}: missing {pi.name} or {pb.name}")
            continue
        I, B = read_json(pi), read_json(pb)
        if fam == "llama":
            llama_rule = B.get("chat_token_norm_check", {}).get("template_free_primary")
            summary["llama_chat_token_norm_check"] = B.get("chat_token_norm_check")
        for u in FAMILY_UNITS[fam]:
            if u not in I["units"] or u not in B["units"]:
                continue
            r = analyze_unit(fam, u, U[u], I, B, rng, llama_rule)
            write_json(RESULTS_DIR / f"b1_{fam}_{u}.json", r)
            summary["units"][u] = r
    # Qwen iteration-8 rows carried and tagged
    q8 = read_json(V43 / "results" / "base_subarm.json")["tasks"]
    summary["qwen_iter8_carried"] = {t: {k: q8[t][k] for k in ("margin_gain_mean", "phrasing_dH_mean",
                                                                "js_ratio_decision_vs_entropy_matched",
                                                                "js_ratio_decision_vs_phrasing",
                                                                "margin_gain_template_free_mean")}
                                     for t in q8}
    # committed verdict over Gemma and Llama forks
    forks = [(u, fid, fr) for u, r in summary["units"].items() for fid, fr in r["forks"].items()
             if not r.get("descriptive_only")]
    summary["excluded_from_verdict"] = [u for u, r in summary["units"].items() if r.get("descriptive_only")]
    nc = [(u, fid, fr) for u, fid, fr in forks if fr["near_collapsed"]]
    P1 = all(fr["P1_gain_ge_2"] for _, _, fr in nc) if nc else None
    P2 = all(abs(fr["phrasing"]["dH_mean"]) < THRESH["B1_P2_dH"] for _, _, fr in forks)
    unit_fv = {}
    unit_rp = {}
    unit_p4 = {}
    for u, fid, fr in forks:
        unit_fv.setdefault(u, []).append(fr["phrasing"]["ratio_fork_vs_matched"] or 0)
        unit_rp.setdefault(u, []).append(fr["phrasing"]["ratio_random_vs_phrasing"])
        unit_p4.setdefault(u, []).append(fr["P4_argmax_differs_majority"])
    n_u = len(unit_fv)
    P3a = sum(max(v) >= THRESH["B1_P3_fork_vs_matched"] for v in unit_fv.values()) >= n_u / 2 if n_u else None
    P3b = all(max(v) <= THRESH["B1_P3_random_vs_phrasing"] for v in unit_rp.values()) if n_u else None
    P3 = bool(P3a and P3b) if n_u else None
    P4 = sum(any(v) for v in unit_p4.values()) >= n_u / 2 if n_u else None
    gem = [fr[fr["primary_mode"]]["gain_mean"] for u, fid, fr in forks if u.startswith("G-")]
    if nc:
        disc = all(fr[fr["primary_mode"]]["gain_mean"] < THRESH["B1_disconfirm_gain"] for _, _, fr in nc)
    else:
        disc = bool(gem) and float(np.mean(gem)) < THRESH["B1_disconfirm_gain"]
    verdict = "PASS" if (P1 is not False and nc and P2 and P3 and P4) else ("DISCONFIRMED" if disc else "PARTIAL")
    summary["verdict"] = {"near_collapsed_forks": [f"{u}:{fid}" for u, fid, _ in nc], "P1": P1, "P2": P2,
                          "P3_fork_vs_matched_half": P3a, "P3_random_vs_phrasing_all": P3b, "P3": P3, "P4": P4,
                          "gemma_mean_gain_primary": float(np.mean(gem)) if gem else None,
                          "P1_untestable": not nc, "verdict": verdict}
    write_json(RESULTS_DIR / "b1_summary.json", summary)
    logger.info(f"B1 verdict: {summary['verdict']}")
    return summary


if __name__ == "__main__":
    setup_logging(f"b1_9_{sys.argv[1]}{'_' + sys.argv[2] if len(sys.argv) > 2 else ''}")
    if sys.argv[1] == "gpu":
        gpu(sys.argv[2])
    else:
        analyze()
