#!/usr/bin/env python3
"""S4 B2 generation (MST = B3, CC = T10): N = 30 common-random-number slots per arm (W1-W5 x 6; seeds 9101-9130; one
uniform per generated token, float64 inverse CDF over the full vocabulary in token-id order, T 1, top-p 1).

Arms differ ONLY at the fork step (the last input position, whose logits choose the decision token):
  TWIN    instruct logits;
  FSTACK  instruct logits with the prompt's cached base FSTACK outputs patched at the fork (one-token path, v2 cache);
  RAND    same with the matched random set whose teacher-forced share is the median of the 50 on that unit;
  FPD     Fork-Patched Decoding at the counterfactual fork only: the fork token is sampled from the BASE model's
          fork logits (cached).
Every later step is unpatched instruct (the fork position's K/V carry the patch for FSTACK / RAND rows). The opening is
the instruct model's own on-policy opening, prefilled in every arm. Programs are labelled by the frozen iteration-5/6
labellers (vendored art_18XvfcJJZi1O src/label_k3.py: hidden tests + runtime tracer + AST).
COMMIT #1 (predicted algorithm shares per arm = sum_tok p_arm(tok) P_I(alg | tok), token maps from locate_B3 o0 and
the T10 class map; unmapped mass reported) is written before any generated token.
Usage: b2gen9.py gpu | label | analyze
"""

from __future__ import annotations

import subprocess
import sys
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

import stats9 as S
from cfg9 import (CACHE_DIR, DATA_DIR, FSTACK, RESULTS_DIR, TEMPLATES, V41, append_jsonl, commit, read_json,
                  read_jsonl, setup_logging, sha256_text, stage_time, utc_now, write_json)
from units9 import load_units

ARMS = ("TWIN", "FSTACK", "RAND", "FPD")
SLOTS_PER_T = 6
SEED0 = 9101
MAX_NEW = {"B3": 768, "T10": 1024}
RAW = DATA_DIR / "samples.jsonl"
LAB = DATA_DIR / "labels_gen.jsonl"
MINORITY = {"B3": {"prim_heap", "prim_array"}, "T10": {"dfs", "bfs"}}


def sample(logits: torch.Tensor, u: torch.Tensor) -> torch.Tensor:
    """Row-wise float64 inverse CDF of softmax(logits) in token-id order."""
    p = torch.softmax(logits.double(), -1)
    c = torch.cumsum(p, -1)
    tgt = (u.double().to(c.device) * c[:, -1]).unsqueeze(-1)
    return torch.searchsorted(c, tgt).squeeze(-1).clamp(max=logits.shape[-1] - 1)


def slot_prompts(U: dict) -> list[tuple[int, dict]]:
    out = []
    for w in TEMPLATES:
        i = [j for j, p in enumerate(U["prompts"]) if p["template"] == w][0]
        out.append((i, U["prompts"][i]))
    return out


def token_map(u: str, f: dict) -> tuple[list[str], dict[int, np.ndarray]]:
    if u == "B3":
        bins = list(f["bins"])
        return bins, {int(t): np.asarray(v, dtype=float) for t, v in f["phat"].items()}
    bins = ["union_find", "dfs", "bfs"]
    m = {}
    for t, c in f["class_of"].items():
        v = np.zeros(3)
        v[bins.index(c)] = 1.0
        m[int(t)] = v
    return bins, m


@torch.no_grad()
def gpu() -> None:
    t0 = time.time()
    import cmap9 as CM
    model, tok = CM.load("qwen")
    units = load_units()
    rsets = read_json(RESULTS_DIR / "random_sets.json")
    b2s = read_json(RESULTS_DIR / "b2_summary.json")
    ot = CM.OneTok(model)
    plan: dict[str, Any] = {}
    for u in ("B3", "T10"):
        U = units[u]
        f = U["forks"][0]
        sh = b2s["units"][u]["null_R"]["shares"]
        med = int(np.argsort(sh)[len(sh) // 2])
        plan[u] = {"rand_set_index": med, "rand_set": rsets[u]["R"]["sets"][med], "rand_set_tf_share": sh[med]}
    # ---------------- COMMIT #1: fork distributions per arm and predicted algorithm shares (before any generation)
    pred: dict[str, Any] = {}
    fork_logits: dict[tuple[str, int], torch.Tensor] = {}
    for u in ("B3", "T10"):
        U = units[u]
        f = U["forks"][0]
        bins, tmap = token_map(u, f)
        ci, cb = torch.load(CACHE_DIR / f"instr_{u}.pt"), torch.load(CACHE_DIR / f"base_{u}.pt")
        rec = {}
        for i, p in slot_prompts(U):
            ids = p["ids"] + f["opening"]
            kv = CM.prefix_kv(model, ids)
            b = cb["caps"][i]["ot"]

            def ops(keys):
                o = []
                for k in keys:
                    kind, l, h = CM.parse(k)
                    o.append(("mlp", l, b["mlp"][l]) if kind == "mlp" else ("head", l, h, b["writes"][l, h]))
                return o
            rows = [[], ops(FSTACK), ops(plan[u]["rand_set"])]
            hs = ot.hooks(rows + [[] for _ in range(CM.ROWS - len(rows))])
            try:
                cache = CM.build_cache(kv, CM.ROWS)
                pos = len(ids) - 1
                o = model.model(input_ids=torch.full((CM.ROWS, 1), ids[-1], device="cuda", dtype=torch.long),
                                past_key_values=cache, position_ids=torch.full((CM.ROWS, 1), pos, device="cuda"),
                                cache_position=torch.tensor([pos], device="cuda"), use_cache=True)
            finally:
                for h in hs:
                    h.remove()
            lg = model.lm_head(o.last_hidden_state[:3, -1]).float().cpu()
            lb = cb["caps"][i]["logits_full"].float()
            arm_lg = {"TWIN": lg[0], "FSTACK": lg[1], "RAND": lg[2], "FPD": lb}
            for a, x in arm_lg.items():
                fork_logits[(u, i, a)] = x
            r_i = {}
            for a, x in arm_lg.items():
                pr = torch.softmax(x.double(), -1).numpy()
                mix = np.zeros(len(bins))
                mapped = 0.0
                for t, v in tmap.items():
                    mix += pr[t] * v
                    mapped += pr[t]
                top = np.argsort(-pr)[:8]
                r_i[a] = {"predicted_shares": dict(zip(bins, mix.tolist())), "unmapped": 1 - mapped,
                          "top": [(tok.decode([int(t)]), float(pr[t])) for t in top]}
            rec[p["pid"]] = r_i
            del kv, cache, o
        pred[u] = {"by_prompt": rec, "bins": bins,
                   "unit_mean": {a: {b_: float(np.mean([rec[k][a]["predicted_shares"][b_] for k in rec])) for b_ in bins}
                                 for a in ARMS},
                   "unit_mean_unmapped": {a: float(np.mean([rec[k][a]["unmapped"] for k in rec])) for a in ARMS}}
        del ci, cb
    pred["plan"] = plan
    pred["predicted_mcnemar_directions"] = {
        "B3": "FSTACK > TWIN and FPD > TWIN in correct Prim programs (Prim is the base's majority fork class)",
        "T10": "FSTACK >= TWIN in DFS/BFS programs only if its fork share of minority tokens is material; a TF share "
               "< 0.85 of the 4.5-nat gap leaves the minority probability small, so 0 vs 0 is the null prediction"}
    commit("commit1_gen", pred)
    # ---------------- generation
    done = {r["sid"] for r in read_jsonl(RAW)}
    for u in ("B3", "T10"):
        U = units[u]
        f = U["forks"][0]
        for ti, (i, p) in enumerate(slot_prompts(U)):
            sids = [f"{u}|{a}|{p['template']}|{k}" for a in ARMS for k in range(SLOTS_PER_T)]
            if all(s in done for s in sids):
                continue
            tb = time.time()
            ids = p["ids"] + f["opening"]
            kv = CM.prefix_kv(model, ids)
            B = len(ARMS) * SLOTS_PER_T
            slots = [ti * SLOTS_PER_T + k for k in range(SLOTS_PER_T)]
            mx = MAX_NEW[u]
            U_ = torch.tensor(np.stack([np.random.default_rng(SEED0 + s).random(mx) for s in slots]))
            Urows = torch.cat([U_ for _ in ARMS], 0)                                     # [B, mx], CRN across arms
            # fork step: recompute the TWIN / FSTACK / RAND rows in one fixed-shape forward (cache gets their K/V)
            cb_i = torch.load(CACHE_DIR / f"base_{u}.pt")["caps"][i]["ot"]

            def ops(keys):
                o = []
                for k in keys:
                    kind, l, h = CM.parse(k)
                    o.append(("mlp", l, cb_i["mlp"][l]) if kind == "mlp" else ("head", l, h, cb_i["writes"][l, h]))
                return o
            arm_ops = {"TWIN": [], "FSTACK": ops(FSTACK), "RAND": ops(plan[u]["rand_set"]), "FPD": []}
            rows = [arm_ops[a] for a in ARMS for _ in range(SLOTS_PER_T)]
            hs = ot.hooks(rows)
            try:
                cache = CM.build_cache(kv, B)
                pos = len(ids) - 1
                o = model.model(input_ids=torch.full((B, 1), ids[-1], device="cuda", dtype=torch.long),
                                past_key_values=cache, position_ids=torch.full((B, 1), pos, device="cuda"),
                                cache_position=torch.tensor([pos], device="cuda"), use_cache=True)
            finally:
                for h in hs:
                    h.remove()
            lg = model.lm_head(o.last_hidden_state[:, -1]).float()
            fpd = [j for j, a in enumerate([a for a in ARMS for _ in range(SLOTS_PER_T)]) if a == "FPD"]
            lg[fpd] = fork_logits[(u, i, "FPD")].to(lg.device)
            nxt = sample(lg, Urows[:, 0])
            gen = [[int(t)] for t in nxt.tolist()]
            fin = [False] * B
            for t in range(1, mx):
                cur = pos + t
                o = model.model(input_ids=nxt[:, None], past_key_values=cache,
                                position_ids=torch.full((B, 1), cur, device="cuda"),
                                cache_position=torch.tensor([cur], device="cuda"), use_cache=True)
                lg = model.lm_head(o.last_hidden_state[:, -1]).float()
                nxt = sample(lg, Urows[:, t])
                for r in range(B):
                    if not fin[r]:
                        gen[r].append(int(nxt[r]))
                        if len(gen[r]) % 8 == 0 or int(nxt[r]) in (151645, 151643):
                            txt = tok.decode(gen[r])
                            if "```" in txt or int(nxt[r]) in (151645, 151643):
                                fin[r] = True
                if all(fin):
                    break
            del cache, kv, o
            torch.cuda.empty_cache()
            open_txt = tok.decode(f["opening"])
            recs = []
            for r in range(B):
                a = ARMS[r // SLOTS_PER_T]
                k = r % SLOTS_PER_T
                txt = tok.decode(gen[r])
                if "```" in txt:
                    txt = txt[:txt.index("```") + 3]
                full = open_txt + txt
                recs.append({"sid": f"{u}|{a}|{p['template']}|{k}", "model": "Qwen/Qwen3-8B", "engine": "hf-bf16",
                             "provider": "local", "task": u, "arm": a, "condition": "PREFILL-opening", "k": None,
                             "template": p["template"], "prompt_id": p["pid"], "slot": slots[k],
                             "seed": SEED0 + slots[k], "fork_token": tok.decode([gen[r][0]]),
                             "fork_token_id": gen[r][0], "n_tokens": len(gen[r]), "truncated": not fin[r],
                             "text": full, "code_sha256": sha256_text(full), "utc": utc_now()})
            append_jsonl(RAW, recs)
            logger.info(f"[{u}] {p['template']}: {B} programs in {time.time() - tb:.0f}s; fork tokens "
                        f"{[(a, [recs[j]['fork_token'] for j in range(len(recs)) if recs[j]['arm'] == a][:6]) for a in ARMS]}")
    stage_time("b2_generation", time.time() - t0)


def label() -> None:
    rows = read_jsonl(RAW)
    done = {r["sid"] for r in read_jsonl(LAB)}
    todo = [{"sid": r["sid"], "unit": r["task"], "text": r["text"]} for r in rows if r["sid"] not in done]
    if not todo:
        return
    tmp_in, tmp_out = DATA_DIR / "label_in.tmp.jsonl", DATA_DIR / "label_out.tmp.jsonl"
    tmp_in.write_text("\n".join(__import__("json").dumps(r) for r in todo) + "\n")
    subprocess.run([sys.executable, "label_k3.py", str(tmp_in), str(tmp_out)], cwd=V41 / "src", check=True)
    append_jsonl(LAB, read_jsonl(tmp_out))
    tmp_in.unlink()
    tmp_out.unlink()


def analyze() -> dict[str, Any]:
    raw = {r["sid"]: r for r in read_jsonl(RAW)}
    lab = {r["sid"]: r for r in read_jsonl(LAB)}
    pred = read_json(sorted((RESULTS_DIR.parent / "predictions").glob("commit1_gen.json"))[0])
    out: dict[str, Any] = {"utc": utc_now()}
    for u in ("B3", "T10"):
        cells = {}
        for a in ARMS:
            rs = [r for s, r in raw.items() if r["task"] == u and r["arm"] == a]
            labs = [lab[r["sid"]] for r in rs if r["sid"] in lab]
            n = len(labs)
            cnt: dict[str, int] = {}
            for l_ in labs:
                cnt[l_["label"]] = cnt.get(l_["label"], 0) + 1
            corr_min = sum(1 for l_ in labs if l_["label"] in MINORITY[u] and l_["passed"])
            npass = sum(1 for l_ in labs if l_["passed"])
            cells[a] = {"n": n, "label_counts": cnt, "n_pass": npass, "pass_rate": npass / n if n else None,
                        "pass_ci95": S.wilson(npass, n), "n_correct_minority": corr_min,
                        "correct_minority_rate": corr_min / n if n else None,
                        "correct_minority_ci95": S.wilson(corr_min, n),
                        "truncated": sum(1 for r in rs if r["truncated"]),
                        "observed_shares": {b: cnt.get(b, 0) / n if n else None for b in pred[u]["bins"]},
                        "predicted_shares": pred[u]["unit_mean"][a],
                        "predicted_unmapped": pred[u]["unit_mean_unmapped"][a]}
            obs = cells[a]["observed_shares"]
            cells[a]["mae_pred_vs_obs"] = float(np.mean([abs((obs[b] or 0) - pred[u]["unit_mean"][a][b])
                                                         for b in pred[u]["bins"]]))
        # paired exact McNemar on correct-minority programs (CRN slots)
        def ind(a):
            d = {}
            for s, r in raw.items():
                if r["task"] == u and r["arm"] == a and s in lab:
                    d[(r["template"], r["slot"])] = int(lab[s]["label"] in MINORITY[u] and lab[s]["passed"])
            return d
        tests = {}
        for a, bb in (("FSTACK", "TWIN"), ("FSTACK", "RAND"), ("FSTACK", "FPD"), ("FPD", "TWIN"), ("RAND", "TWIN")):
            x, y = ind(a), ind(bb)
            ks = sorted(set(x) & set(y))
            b_ = sum(1 for k in ks if x[k] == 1 and y[k] == 0)
            c_ = sum(1 for k in ks if x[k] == 0 and y[k] == 1)
            px = [lab_ for lab_ in []]
            tests[f"{a}_vs_{bb}"] = {"n_pairs": len(ks), "b_first_only": b_, "c_second_only": c_,
                                     "p_exact_two_sided": S.mcnemar_exact(b_, c_),
                                     "pass_diff_newcombe95": S.newcombe(cells[a]["n_pass"], cells[a]["n"],
                                                                         cells[bb]["n_pass"], cells[bb]["n"])
                                     if cells[a]["n"] and cells[bb]["n"] else None}
            del px
        prim = ["FSTACK_vs_TWIN", "FSTACK_vs_RAND", "FSTACK_vs_FPD"]
        adj = S.holm([tests[k]["p_exact_two_sided"] for k in prim])
        for k, a_ in zip(prim, adj):
            tests[k]["p_holm_within_unit"] = a_
        out[u] = {"cells": cells, "tests": tests, "rand_set": pred["plan"][u]}
    write_json(RESULTS_DIR / "b2_generation.json", out)
    for u in ("B3", "T10"):
        logger.info(f"generation {u}: " + "; ".join(f"{a}: {out[u]['cells'][a]['label_counts']} pass "
                                                      f"{out[u]['cells'][a]['n_pass']}/{out[u]['cells'][a]['n']}"
                                                      for a in ARMS))
    return out


if __name__ == "__main__":
    setup_logging(f"b2gen9_{sys.argv[1]}")
    {"gpu": gpu, "label": label, "analyze": analyze}[sys.argv[1]]()
