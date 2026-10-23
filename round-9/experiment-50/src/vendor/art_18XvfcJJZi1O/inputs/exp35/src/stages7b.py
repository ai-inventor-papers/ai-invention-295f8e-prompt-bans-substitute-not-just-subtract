#!/usr/bin/env python3
"""Part D (predict: teacher forcing, token conditionals, collapsed margins, S4 teacher-forced numbers -> COMMIT #2
by cpu-side commit_predictions) and Part E (sweep, collapsed T 1.3 check, S4(a) pushes, S4(b) exchange arms) and the
F7 geometry capture."""

from __future__ import annotations

import json
import math
import random
from collections import Counter, defaultdict
from typing import Any

import numpy as np
import torch
from loguru import logger

import engine7 as EN
import predict as PR
import replay
from cfg7 import (ALPHA_PUSH, CACHE_DIR, COLLAPSED, COLLAPSED_INFO, DIRECTIONS, E22, I6, PRED_DIR, RESULTS_DIR,
                  S4A_SLOTS, S4B_SLOTS, SAMPLERS, SWEEP_SLOTS, TEMPLATES, TEMPS, UNITS, V_BLOCKS, log_deviation,
                  read_json, read_jsonl, stable_seed, u_stream, utc_now, write_json)
from gpu7 import clear_prefills, label_pending, prog_spec, run_specs
from prompts7 import load_prompts
from stages7 import a_min_of, cat_index, cats, cont_labels, run_conts, twin_table

N_TOK_MAX = 40
N_W1, N_OTHER, N_RESID = 20, 5, 20
TF_DIR = CACHE_DIR / "tf"


# ------------------------------------------------------------------------------------------------ teacher forcing
def tf_open(model: Any, prompt: dict[str, Any], O: list[int], edits: dict | None = None,
            cap_blocks: list[int] | None = None) -> dict[str, Any]:
    """Logits predicting o_1..o_|O| (rows 0..|O|-1) and the fork logits (row |O|), fp32 numpy."""
    ids = prompt["ids"] + list(O)
    r = EN.teacher_force(model, ids, len(prompt["ids"]), edits=edits,
                         capture_blocks=cap_blocks, capture_pos=[len(ids) - 1] if cap_blocks else None)
    lg = r["logits"].cpu().numpy().astype(np.float64)
    return {"Z_open": lg[:len(O)], "z_fork": lg[len(O)], "caps": {l: v.cpu().numpy() for l, v in r["caps"].items()}}


def logp_vec(z: np.ndarray) -> np.ndarray:
    z = z - z.max()
    return z - np.log(np.exp(z).sum())


def fork_tokens(zs: list[np.ndarray]) -> tuple[list[int], np.ndarray]:
    """Expanded token set: template-averaged pi_1 >= 0.002 or top 20, capped at 40 (by mass)."""
    pi = np.mean([np.exp(logp_vec(z)) for z in zs], 0)
    order = np.argsort(-pi)
    toks = [int(t) for t in order[:20]] + [int(t) for t in order[20:200] if pi[t] >= 0.002]
    toks = sorted(dict.fromkeys(toks), key=lambda t: -pi[t])[:N_TOK_MAX]
    return toks, pi


def tok_items(unit: str, P: dict, cid: str, O: list[int], t: int, n_w1: int = N_W1, n_other: int = N_OTHER,
              T: float = 1.0, tag: str = "tok") -> list[dict[str, Any]]:
    items = []
    for w in TEMPLATES:
        n = n_w1 if w == "W1" else n_other
        for j in range(n):
            items.append({"cid": f"{unit}|{tag}|{cid}|{t}|{w}|{j}|T{T}", "unit": unit, "w": w,
                          "prompt_ids": P[(unit, w, "twin")]["ids"], "prefix": list(O) + [t],
                          "ukey": ["iter7fork", unit, f"{tag}|{cid}|{t}|{w}|T{T}", len(O) + 1, j], "T": T,
                          "top_k": 0, "kind": tag, "cluster": cid, "tok": t, "k": len(O) + 1})
    return items


def counts_of(unit: str, rows: list[dict[str, Any]]) -> np.ndarray:
    v = np.zeros(len(cats(unit)))
    for r in rows:
        v[cat_index(unit, r["final_label"])] += 1
    return v


# ------------------------------------------------------------------------------------------------ Part D
def stage_predict(model: Any, tok: Any, units: list[str]) -> None:
    P = load_prompts()
    F = read_json(RESULTS_DIR / "forks.json")
    TF_DIR.mkdir(parents=True, exist_ok=True)
    out = read_json(PRED_DIR / "predictions_raw.json") if (PRED_DIR / "predictions_raw.json").exists() else {}
    for u in units:
        if u not in F:
            continue
        D, A = F[u]["D"], F[u]["A_min"]
        C = cats(u)
        clusters = F[u]["opening"]["clusters"]
        U = {"D": D, "A_min": A, "cats": C, "mode": F[u]["mode"], "clusters": {}}
        tw = twin_table(u)
        # q_rest: label shares among twin programs off every listed opening
        off = [r for r in tw if not any(r["token_ids"][:len(c["O"])] == c["O"] for c in clusters)]
        q_src = off if len(off) >= 10 else tw
        q_rest = counts_of(u, [{"final_label": r["label"]} for r in q_src])
        q_rest = q_rest / q_rest.sum()
        U["q_rest"] = q_rest.tolist()
        U["q_rest_n"] = len(q_src)
        U["q_rest_source"] = "off-opening twin programs" if len(off) >= 10 else "all twin programs (< 10 off)"
        U["twin_pass_rate_a_min"] = float(np.mean([r["passed"] for r in tw if r["label"] == A])) if any(
            r["label"] == A for r in tw) else 0.0
        for c in clusters:
            cid, O = c["id"], c["O"]
            tfs = {w: tf_open(model, P[(u, w, "twin")], O) for w in TEMPLATES}
            np.savez_compressed(TF_DIR / f"{u}_{cid}.npz", **{f"zf_{w}": tfs[w]["z_fork"].astype(np.float32)
                                                              for w in TEMPLATES},
                                **{f"Zo_{w}": tfs[w]["Z_open"].astype(np.float32) for w in TEMPLATES})
            toks, pi = fork_tokens([tfs[w]["z_fork"] for w in TEMPLATES])
            items = []
            for t in toks:
                items += tok_items(u, P, cid, O, t)
            # residual bin: first token drawn from the renormalised remainder of W1's fork distribution
            p1 = np.exp(logp_vec(tfs["W1"]["z_fork"]))
            rem = p1.copy()
            rem[toks] = 0.0
            rem_mass = float(rem.sum())
            rng = np.random.default_rng(stable_seed("resid", u, cid) % 2 ** 32)
            resid_toks = [int(x) for x in rng.choice(len(rem), size=N_RESID, p=rem / rem.sum())] if rem_mass > 0 \
                else []
            for j, t in enumerate(resid_toks):
                items.append({"cid": f"{u}|resid|{cid}|{j}", "unit": u, "w": "W1", "prompt_ids":
                              P[(u, "W1", "twin")]["ids"], "prefix": list(O) + [t],
                              "ukey": ["iter7fork", u, f"resid|{cid}", len(O) + 1, j], "T": 1.0, "top_k": 0,
                              "kind": "resid", "cluster": cid, "tok": t, "k": len(O) + 1})
            run_conts(model, tok, u, items, f"tokcond:{u}:{cid}")
            rows = cont_labels(lambda r: r["unit"] == u and r.get("cluster") == cid and r.get("kind") in
                               ("tok", "resid"))
            by_tok = defaultdict(list)
            for r in rows:
                by_tok[r["tok"] if r["kind"] == "tok" else "resid"].append(r)
            cnt = {t: counts_of(u, by_tok[t]) for t in toks}
            cnt_res = counts_of(u, by_tok["resid"]) if by_tok["resid"] else q_rest * 0
            # TREE expansion (depth 2) for undecided tokens when the unit is in TREE mode
            tree = {}
            if F[u]["mode"] == "TREE":
                for t in toks:
                    ph = cnt[t] / max(cnt[t].sum(), 1)
                    if 0.1 <= ph[C.index(D)] <= 0.9 and pi[t] >= 0.02:
                        sub = {w: tf_open(model, P[(u, w, "twin")], list(O) + [t]) for w in TEMPLATES}
                        toks2, pi2 = fork_tokens([sub[w]["z_fork"] for w in TEMPLATES])
                        toks2 = toks2[:10]
                        it2 = []
                        for t2 in toks2:
                            it2 += [{"cid": f"{u}|tree|{cid}|{t}|{t2}|{j}", "unit": u, "w": "W1",
                                     "prompt_ids": P[(u, "W1", "twin")]["ids"], "prefix": list(O) + [t, t2],
                                     "ukey": ["iter7fork", u, f"tree|{cid}|{t}|{t2}", len(O) + 2, j], "T": 1.0,
                                     "top_k": 0, "kind": "tree", "cluster": cid, "tok": t, "tok2": t2,
                                     "k": len(O) + 2} for j in range(20)]
                        run_conts(model, tok, u, it2, f"tree:{u}:{cid}:{t}")
                        r2 = cont_labels(lambda r: r["unit"] == u and r.get("kind") == "tree" and
                                         r.get("cluster") == cid and r.get("tok") == t)
                        c2 = {t2: counts_of(u, [r for r in r2 if r["tok2"] == t2]).tolist() for t2 in toks2}
                        np.savez_compressed(TF_DIR / f"{u}_{cid}_tree_{t}.npz",
                                            **{f"zf_{w}": sub[w]["z_fork"].astype(np.float32) for w in TEMPLATES})
                        tree[str(t)] = {"toks2": toks2, "counts2": c2, "pi2_avg": [float(pi2[x]) for x in toks2]}
            # persistence check: 20 continuations per class at T 1.3 from the class's most probable fork token
            persist = {}
            for cls in (D, A):
                cands = [t for t in toks if cnt[t].sum() and C[int(np.argmax(cnt[t]))] == cls]
                if not cands:
                    continue
                t0 = max(cands, key=lambda t: pi[t])
                it3 = tok_items(u, P, cid, O, t0, n_w1=20, n_other=0, T=1.3, tag="persist")
                run_conts(model, tok, u, it3, f"persist:{u}:{cid}:{cls}")
                r3 = cont_labels(lambda r: r["unit"] == u and r.get("kind") == "persist" and r.get("cluster") == cid
                                 and r.get("tok") == t0)
                persist[cls] = {"tok": t0, "tok_text": tok.decode([t0]), "counts": counts_of(u, r3).tolist()}
            # G4 teacher-forced vs generation logits along O (decode the opening under W1 with forced tokens)
            g4 = g4_check(model, P[(u, "W1", "twin")], O, tfs["W1"])
            U["clusters"][cid] = {
                "O": O, "len_O": len(O), "cov": c["cov"], "O_text": tok.decode(O), "toks": toks,
                "tok_text": {str(t): tok.decode([t]) for t in toks},
                "pi1_avg": {str(t): float(pi[t]) for t in toks},
                "pi1_by_template": {w: {str(t): float(np.exp(logp_vec(tfs[w]["z_fork"]))[t]) for t in toks}
                                    for w in TEMPLATES},
                "rank_by_template": {w: {str(t): int((tfs[w]["z_fork"] > tfs[w]["z_fork"][t]).sum()) + 1
                                         for t in toks} for w in TEMPLATES},
                "counts": {str(t): cnt[t].tolist() for t in toks}, "resid_counts": cnt_res.tolist(),
                "resid_mass_W1": rem_mass, "resid_toks": resid_toks, "tree": tree, "persistence": persist,
                "G4": g4}
            del tfs
            torch.cuda.empty_cache()
            logger.info(f"{u}/{cid}: {len(toks)} fork tokens expanded; residual mass {rem_mass:.4f}")
        out[u] = U
        write_json(PRED_DIR / "predictions_raw.json", out)
    clear_prefills()


@torch.no_grad()
def g4_check(model: Any, prompt: dict[str, Any], O: list[int], tf: dict[str, Any]) -> dict[str, Any]:
    """Incremental decoding with forced opening tokens (the generation path) vs one teacher-forced pass."""
    pre = EN.prefill(model, prompt["ids"])
    from transformers.cache_utils import DynamicCache
    cache = DynamicCache()
    for l, (K, V) in enumerate(pre["kv"]):
        cache.update(K, V, l)
    gl = [pre["r_logits"].double().cpu().numpy()]
    dev = EN.dev_of(model)
    for i, t in enumerate(O):
        h = model.model(input_ids=torch.tensor([[t]], device=dev), past_key_values=cache,
                        position_ids=torch.tensor([[len(prompt["ids"]) + i]], device=dev),
                        use_cache=True).last_hidden_state
        gl.append(model.lm_head(h[:, -1]).double()[0].cpu().numpy())
    G = np.stack(gl)                                         # [|O|+1, V]
    Tz = np.concatenate([tf["Z_open"], tf["z_fork"][None]], 0)
    am = float(np.mean(G.argmax(1) == Tz.argmax(1)))
    return {"max_abs_logit_diff": float(np.abs(G - Tz).max()), "argmax_agreement": am,
            "n_positions": int(G.shape[0]), "fallback_F12_needed": am < 0.99}


# ------------------------------------------------------------------------------------------------ collapsed (D5)
def collapsed_programs(task: str) -> dict[str, Any]:
    """Twin programs (iteration-6 TWIN rows + this artifact's TWIN6 rows) and the model's own alternative programs
    (iteration-6 BAN / X / FORCED arms, with token ids) labelled off-default."""
    lab6 = {r["sample_id"]: r for r in read_jsonl(I6 / "data" / "labels.jsonl")}
    twin, alt = [], []
    Dl = COLLAPSED_INFO[task]["default"]
    for r in read_jsonl(I6 / "data" / "samples_raw.jsonl"):
        if r["task"] != task:
            continue
        ids = json.loads(r["token_ids"]) if isinstance(r["token_ids"], str) else r["token_ids"]
        lab = lab6.get(r["sample_id"], {}).get("label")
        if r["arm"] == "TWIN":
            twin.append({"ids": ids, "label": lab, "src": r["sample_id"]})
        elif lab not in (None, Dl, "other", "invalid", "disputed") and r["arm"] in (
                "BAN", "X_0-35", "X_12-23", "FORCED", "FORCEDX_0-35", "MR_0-35", "PLACEBO", "COND"):
            alt.append({"ids": ids, "label": lab, "src": r["sample_id"]})
    for r in twin_table(task, "TWIN6"):
        twin.append({"ids": r["token_ids"], "label": r["label"], "src": r["sid"]})
    return {"twin": twin, "alt": alt}


def modal_path(progs: list[list[int]], min_n: int = 2) -> list[int]:
    path: list[int] = []
    sub = progs
    while True:
        c = Counter(g[len(path)] for g in sub if len(g) > len(path))
        if not c:
            return path
        t, n = c.most_common(1)[0]
        if n < min_n:
            return path
        path.append(t)
        sub = [g for g in sub if len(g) > len(path) - 1 and g[len(path) - 1] == t]


def stage_collapsed_margins(model: Any, tok: Any) -> None:
    P = load_prompts()
    out = read_json(PRED_DIR / "collapsed_raw.json") if (PRED_DIR / "collapsed_raw.json").exists() else {}
    for task in COLLAPSED:
        if task in out and out[task].get("done"):
            continue
        info = COLLAPSED_INFO[task]
        Dl = info["default"]
        cp = collapsed_programs(task)
        O = modal_path([p["ids"] for p in cp["twin"]])
        alt = cp["alt"][:60]
        deps = []
        for a in alt:
            j = next((i for i, (x, y) in enumerate(zip(a["ids"], O)) if x != y), min(len(a["ids"]), len(O)))
            deps.append(j)
        j_mod = Counter(deps).most_common(1)[0][0] if deps else 0
        node = O[:j_mod]
        alt_toks = Counter(a["ids"][j_mod] for a, j in zip(alt, deps) if j == j_mod and len(a["ids"]) > j_mod)
        prompt = P[(task, "W1", "twin")]
        tf = tf_open(model, prompt, node)
        z = tf["z_fork"]
        pi = np.exp(logp_vec(z))
        top = [int(t) for t in np.argsort(-pi)[:10]]
        toks = list(dict.fromkeys(top + [int(t) for t in alt_toks]))
        # continuations (to the fence, full frozen labeller): 10 per top token, 20 per alternative token
        specs = []
        for t in toks:
            n = 20 if t in alt_toks else 10
            for j in range(n):
                specs.append(_cont_spec(task, prompt, node + [t], f"cm|{t}", j, 1.0))
        rows = _run_full_conts(model, tok, task, specs, f"collapsed_tok:{task}")
        cnt = defaultdict(lambda: [0, 0])
        for s, r in rows:
            t = int(s["tok"])
            cnt[t][1] += 1
            cnt[t][0] += r["label"] not in (Dl,) and r["label"] not in ("invalid", "other", "disputed", None)
        ph_off = {t: cnt[t][0] / max(cnt[t][1], 1) for t in toks}
        alt_class = [t for t in toks if ph_off[t] >= 0.5]
        path_info = None
        if alt_class:
            m = math.log(max(1e-300, float(sum(pi[t] for t in toks if t not in alt_class)) +
                             float(1 - sum(pi[t] for t in toks)))) - math.log(float(sum(pi[t] for t in alt_class)))
            seg = None
        else:
            # walk the runner-up's modal path from the node (bisection over at most 16 tokens)
            alt_tail = [a["ids"][j_mod:] for a, j in zip(alt, deps) if j == j_mod]
            seg_full = modal_path(alt_tail, 1)[:16] if alt_tail else []
            lo, hi, best = 1, len(seg_full), None
            tried = {}
            while lo <= hi and seg_full:
                mid = (lo + hi) // 2
                specs = [_cont_spec(task, prompt, node + seg_full[:mid], f"seg|{mid}", j, 1.0) for j in range(10)]
                rr = _run_full_conts(model, tok, task, specs, f"collapsed_seg:{task}:{mid}")
                off = sum(r["label"] not in (Dl, "invalid", "other", "disputed", None) for _, r in rr) / max(len(rr), 1)
                tried[mid] = off
                if off >= 0.8:
                    best, hi = mid, mid - 1
                else:
                    lo = mid + 1
            seg = seg_full[:best] if best else seg_full
            if seg:
                tf2 = tf_open(model, prompt, node + seg)
                lp_seg = sum(float(logp_vec(z0)[t]) for z0, t in zip(
                    np.concatenate([tf["z_fork"][None], tf2["Z_open"][len(node) + 1:]], 0) if len(seg) > 1
                    else tf["z_fork"][None], seg))
                lp_seg = float(PR.seq_logprob(np.concatenate([tf["z_fork"][None], tf2["Z_open"][len(node) + 1:]], 0)
                                              if len(seg) > 1 else tf["z_fork"][None], seg, 1.0, 0))
                m = math.log(max(1e-300, 1 - math.exp(lp_seg))) - lp_seg
                path_info = {"segment": seg, "segment_text": tok.decode(seg), "bisection": tried,
                             "logp_segment": lp_seg}
            else:
                m = float("inf")
        # predicted p_T(off-default) at the node, full and top-k 10
        def p_off(T: float, k: int) -> float:
            if alt_class:
                d = PR.dist(z, T, k)
                return float(sum(d[t] * ph_off[t] for t in toks))
            if path_info:
                Zs = np.concatenate([tf["z_fork"][None], tf_open(model, prompt, node + seg)["Z_open"][len(node) + 1:]],
                                    0) if len(seg) > 1 else tf["z_fork"][None]
                return float(math.exp(PR.seq_logprob(Zs, seg, T, k)))
            return 0.0
        preds = {f"T{T}_{s}": p_off(T, k) for T in (0.3, 0.7, 1.0, 1.3) for s, k in SAMPLERS.items()}
        # bound check: 100 continuations at T 1.3 from the node
        specs = [_cont_spec(task, prompt, node, "bound", j, 1.3) for j in range(100)]
        rr = _run_full_conts(model, tok, task, specs, f"collapsed_bound:{task}")
        n_off = sum(r["label"] not in (Dl, "invalid", "other", "disputed", None) for _, r in rr)
        # 48-token opening log-likelihood ratio (>= 5 default twin programs vs >= 5 alternative programs)
        def lme(progs: list[list[int]]) -> float:
            vals = []
            for g in progs[:8]:
                g48 = g[:48]
                t2 = tf_open(model, prompt, g48)
                vals.append(PR.seq_logprob(t2["Z_open"], g48, 1.0, 0))
            return float(np.logaddexp.reduce(vals) - math.log(len(vals))) if vals else float("nan")
        llr48 = lme([p["ids"] for p in cp["twin"] if p["label"] == Dl]) - lme([a["ids"] for a in alt])
        out[task] = {"default": Dl, "n_twin": len(cp["twin"]), "n_twin_default": sum(p["label"] == Dl
                                                                                       for p in cp["twin"]),
                     "n_alt": len(alt), "alt_labels": dict(Counter(a["label"] for a in alt)),
                     "O_len": len(O), "fork_node_index": j_mod, "fork_node_text": tok.decode(node[-30:]),
                     "departures": dict(Counter(deps)), "alt_tokens": {str(t): n for t, n in alt_toks.items()},
                     "tokens": toks, "tok_text": {str(t): tok.decode([t]) for t in toks},
                     "pi1": {str(t): float(pi[t]) for t in toks}, "phat_off": {str(t): ph_off[t] for t in toks},
                     "n_cont": {str(t): cnt[t][1] for t in toks}, "alt_class_tokens": alt_class,
                     "margin_nats": m, "path": path_info, "pred_p_off": preds,
                     "delta_pred_13_03": preds["T1.3_p1"] - preds["T0.3_p1"],
                     "bound_check": {"n": len(rr), "n_off": n_off, "phat_off_T13": n_off / max(len(rr), 1),
                                     "logit_based_T13": preds["T1.3_p1"],
                                     "overstated": bool(n_off >= 3 and n_off / max(len(rr), 1) >=
                                                        3 * preds["T1.3_p1"])},
                     "llr48": llr48, "done": True}
        write_json(PRED_DIR / "collapsed_raw.json", out)
        logger.info(f"collapsed {task}: node {j_mod}, margin {m:.2f} nats, p_off(T1.3) {preds['T1.3_p1']:.4f}, "
                    f"bound {n_off}/{len(rr)}")
        clear_prefills()


def _cont_spec(task: str, prompt: dict[str, Any], prefix: list[int], tag: str, j: int, T: float) -> dict[str, Any]:
    return {"sid": f"{task}|CM|{tag}|{len(prefix)}|{j}|T{T}", "unit": task, "prompt_ids": prompt["ids"],
            "prefix": prefix, "ukey": ["iter7fork", task, tag, len(prefix), j, T], "T": T, "tok": tag.split("|")[-1]}


def _run_full_conts(model: Any, tok: Any, task: str, specs: list[dict[str, Any]], tag: str,
                    batch: int = 40) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Collapsed-task continuations to the fence, labelled by the frozen labeller (label7 subprocess)."""
    from cfg7 import DATA_DIR, append_jsonl
    path = DATA_DIR / "collapsed_conts.jsonl"
    lpath = DATA_DIR / "collapsed_conts_labels.jsonl"
    have = {r["sid"]: r for r in read_jsonl(path)}
    todo = [s for s in specs if s["sid"] not in have]
    fence = COLLAPSED_INFO[task]["fence"]
    for i in range(0, len(todo), batch):
        part = todo[i:i + batch]
        pres = {}
        rows = []
        for s in part:
            key = tuple(s["prefix"])
            if key not in pres:
                pres[key] = EN.prefill(model, s["prompt_ids"] + s["prefix"])
            rows.append({"pre": pres[key], "u": u_stream(*s["ukey"]), "T": s["T"], "top_k": 0, "max_new":
                         max(32, COLLAPSED_INFO[task]["max_new"] - len(s["prefix"])), "fence": True,
                         "text_prefix": tok.decode(s["prefix"])})
        res = EN.decode_stop(model, rows, tok, fence, None, check_every=8)
        recs = [{"sid": s["sid"], "unit": task, "tag": tag, "prefix_len": len(s["prefix"]), "T": s["T"],
                 "token_ids": r["token_ids"], "finish_reason": r["finish_reason"],
                 "text": rows[j]["text_prefix"] + tok.decode(r["token_ids"], skip_special_tokens=True)}
                for j, (s, r) in enumerate(zip(part, res))]
        append_jsonl(path, recs)
        del pres, rows
        torch.cuda.empty_cache()
    label_pending(path, lpath)
    labs = {r["sid"]: r for r in read_jsonl(lpath)}
    return [(s, labs[s["sid"]]) for s in specs if s["sid"] in labs]


# ------------------------------------------------------------------------------------------------ S4 (D6)
def spec_states(model: Any, prompt: dict[str, Any], blocks: list[int]) -> dict[int, torch.Tensor]:
    S = torch.arange(prompt["p1"], prompt["spec_end"], device=EN.dev_of(model))
    H: dict[int, torch.Tensor] = {}
    EN.prefill(model, prompt["ids"], capture=EN.capture_hooks(H, S, blocks))
    return H


def dose_unit(model: Any, P: dict, u: str) -> dict[str, Any]:
    """n[l, p] = mean over W1-W5 of ||h_ban - h_twin|| at blocks 12-23 and spec offsets (iteration-4 units() rule,
    outliers > 10 x block median flagged, not clipped)."""
    ns = []
    for w in TEMPLATES:
        hb = spec_states(model, P[(u, w, "ban")], V_BLOCKS)
        ht = spec_states(model, P[(u, w, "twin")], V_BLOCKS)
        ns.append(torch.stack([(hb[l] - ht[l]).norm(dim=1) for l in V_BLOCKS]).cpu().numpy())
    n = np.mean(ns, 0)                                       # [12, |S|]
    med = np.median(n, axis=1, keepdims=True)
    outl = np.argwhere(n > 10 * med)
    return {"n": n, "mean": float(n.mean()), "outliers": [{"block": int(V_BLOCKS[i]), "pos": int(p),
                                                           "n": float(n[i, p])} for i, p in outl[:50]]}


def load_dirs() -> dict[int, np.ndarray]:
    out = {}
    for d in DIRECTIONS:
        x = np.load(E22 / "directions" / f"rand_{d}.npy").astype(np.float32).reshape(-1)
        assert x.shape == (4096,)
        out[d] = x / np.linalg.norm(x)
    return out


def stage_s4_predict(model: Any, tok: Any, units: list[str]) -> None:
    P = load_prompts()
    F = read_json(RESULTS_DIR / "forks.json")
    out = read_json(PRED_DIR / "s4_raw.json") if (PRED_DIR / "s4_raw.json").exists() else {}
    dirs = load_dirs()
    for u in units:
        if u not in F or (u in out and out[u].get("done")):
            continue
        c0 = F[u]["opening"]["clusters"][0]
        O = c0["O"]
        rec: dict[str, Any] = {"cluster": c0["id"], "push": {}, "exchange": {}}
        dose = dose_unit(model, P, u)
        np.save(CACHE_DIR / f"dose_{u}.npy", dose["n"].astype(np.float32))
        rec["dose_mean"] = dose["mean"]
        rec["dose_outliers"] = dose["outliers"]
        dev = EN.dev_of(model)
        for d, x in dirs.items():
            ud = torch.from_numpy(x).to(dev)
            per_w = {}
            for w in TEMPLATES:
                pr = P[(u, w, "twin")]
                href = spec_states(model, pr, V_BLOCKS)
                n_t = {l: torch.from_numpy(dose["n"][j]).float().to(dev) for j, l in enumerate(V_BLOCKS)}
                log: dict = {}
                ed = EN.push_edits(pr["p1"], pr["spec_end"], ud, n_t, href, ALPHA_PUSH, log)
                tf = tf_open(model, pr, O, edits=ed)
                np.savez_compressed(TF_DIR / f"{u}_push{d}_{w}.npz", zf=tf["z_fork"].astype(np.float32),
                                    Zo=tf["Z_open"].astype(np.float32))
                per_w[w] = {"realised_edit_mean_by_block": {str(l): float(np.mean(v)) for l, v in log.items()}}
            rec["push"][str(d)] = per_w
        # exchange: forced 'Implement A_min' spec states (all blocks) into the padding twin; MR control
        f, fp = P[(u, "F", "forced")], P[(u, "F", "forced_pad")]
        S = torch.arange(f["p1"], f["spec_end"], device=dev)
        Hf = spec_states(model, f, list(range(36)))
        Hp = spec_states(model, fp, list(range(36)))
        ex = EN.set_rows_edit(S, Hf)
        norms = {l: (Hf[l] - Hp[l]).norm(dim=1) for l in range(36)}
        mr, real = EN.mr_edit(S, Hp, norms, stable_seed("MR_tf", u) % 2 ** 32)
        rec["exchange"]["norm_mean_by_block"] = {str(l): float(v.mean()) for l, v in norms.items()}
        rec["exchange"]["mr_realised_by_block"] = {str(l): v for l, v in real.items()}
        for name, ed, pr in (("forced", None, f), ("forced_pad", None, fp), ("exchange", ex, fp), ("MR", mr, fp)):
            tf = tf_open(model, pr, O, edits=ed)
            np.savez_compressed(TF_DIR / f"{u}_{name}.npz", zf=tf["z_fork"].astype(np.float32),
                                Zo=tf["Z_open"].astype(np.float32))
        rec["forced_Y"] = f.get("Y")
        rec["done"] = True
        out[u] = rec
        write_json(PRED_DIR / "s4_raw.json", out)
        del Hf, Hp
        clear_prefills()


# ------------------------------------------------------------------------------------------------ Part E
def stage_sweep(model: Any, tok: Any, units: list[str], n_slots: int | None = None) -> None:
    P = load_prompts()
    slots = list(SWEEP_SLOTS)[:n_slots] if n_slots else list(SWEEP_SLOTS)
    for u in units:
        for w in TEMPLATES:
            pr = P[(u, w, "twin")]
            for sname, k in SAMPLERS.items():
                specs = [prog_spec(u, "SWEEP", f"T{T}_{sname}", w, s, pr, T, k) for T in TEMPS for s in slots]
                run_specs(model, tok, specs, 4 * len(slots), f"sweep:{u}:{w}:{sname}")
            clear_prefills()
        label_pending()


def stage_collapsed_check(model: Any, tok: Any) -> None:
    P = load_prompts()
    for task in COLLAPSED:
        specs = []
        for w in ("W1", "W2", "W3", "W5"):
            specs += [prog_spec(task, "T13CHK", "T1.3_p1", w, k, P[(task, w, "twin")], 1.3, 0, ukey=(task, w, k))
                      for k in range(5)]
        run_specs(model, tok, specs, 20 if task in ("T03", "T10") else 10, f"collapsed13:{task}")
        clear_prefills()
    label_pending()


def stage_s4a(model: Any, tok: Any, units: list[str]) -> None:
    P = load_prompts()
    dirs = load_dirs()
    dev = EN.dev_of(model)
    for u in units:
        n = np.load(CACHE_DIR / f"dose_{u}.npy")
        for w in TEMPLATES:
            pr = P[(u, w, "twin")]
            href = spec_states(model, pr, V_BLOCKS)
            n_t = {l: torch.from_numpy(n[j]).float().to(dev) for j, l in enumerate(V_BLOCKS)}
            specs = []
            for d, x in dirs.items():
                ed = EN.push_edits(pr["p1"], pr["spec_end"], torch.from_numpy(x).to(dev), n_t, href, ALPHA_PUSH)
                for s in S4A_SLOTS:
                    sp = prog_spec(u, "S4A", f"push{d}", w, s, pr, 1.0, 0, pre_key=f"{u}|{w}|push{d}", direction=d,
                                   alpha=ALPHA_PUSH)
                    sp["edits"] = ed
                    specs.append(sp)
            specs += [prog_spec(u, "S4A", "twin0", w, s, pr, 1.0, 0) for s in S4A_SLOTS]
            run_specs(model, tok, specs, len(specs), f"s4a:{u}:{w}")
            clear_prefills()
        label_pending()


def stage_s4b(model: Any, tok: Any, units: list[str]) -> None:
    P = load_prompts()
    dev = EN.dev_of(model)
    for u in units:
        f, fp = P[(u, "F", "forced")], P[(u, "F", "forced_pad")]
        S = torch.arange(f["p1"], f["spec_end"], device=dev)
        Hf = spec_states(model, f, list(range(36)))
        Hp = spec_states(model, fp, list(range(36)))
        ex = EN.set_rows_edit(S, Hf)
        norms = {l: (Hf[l] - Hp[l]).norm(dim=1) for l in range(36)}
        n_slots = len(S4B_SLOTS) * 5
        for arm in ("FORCED", "FORCEDPAD", "EXCH", "MR"):
            specs = []
            for s in range(n_slots):
                pr = f if arm == "FORCED" else fp
                sp = prog_spec(u, "S4B", arm, "F", s, pr, 1.0, 0, pre_key=f"{u}|F|{arm}" + (f"|{s}" if arm == "MR"
                                                                                           else ""),
                               ukey=("iter7T", u, "F", s))
                if arm == "EXCH":
                    sp["edits"] = ex
                elif arm == "MR":
                    sp["edits_fn"] = (lambda s=s: EN.mr_edit(S, Hp, norms, stable_seed("MR", u, s) % 2 ** 32)[0])
                specs.append(sp)
            run_specs(model, tok, specs, 30, f"s4b:{u}:{arm}")
            clear_prefills()
        del Hf, Hp
        label_pending()


# ------------------------------------------------------------------------------------------------ F7 geometry
def stage_geometry(model: Any, tok: Any, units: list[str]) -> None:
    """Block-24 residual (HF hidden_states[25]) at the fork-token position for each candidate fork token (W1), plus
    the pushed / exchanged / MR fork states (state at the argmax fork token under the edit)."""
    P = load_prompts()
    R = read_json(PRED_DIR / "predictions_raw.json")
    S4 = read_json(PRED_DIR / "s4_raw.json") if (PRED_DIR / "s4_raw.json").exists() else {}
    dirs = load_dirs()
    dev = EN.dev_of(model)
    for u in units:
        if u not in R:
            continue
        cid = sorted(R[u]["clusters"])[0]
        cl = R[u]["clusters"][cid]
        O = cl["O"]
        pr = P[(u, "W1", "twin")]
        toks = cl["toks"]
        res = EN.batch_last_states(model, [pr["ids"] + O + [t] for t in toks], [24])
        X = res["caps"][24].cpu().numpy()
        extra_names, extra = [], []
        n = np.load(CACHE_DIR / f"dose_{u}.npy") if (CACHE_DIR / f"dose_{u}.npy").exists() else None
        href = spec_states(model, pr, V_BLOCKS)
        for d, x in dirs.items():
            if n is None:
                break
            n_t = {l: torch.from_numpy(n[j]).float().to(dev) for j, l in enumerate(V_BLOCKS)}
            ed = EN.push_edits(pr["p1"], pr["spec_end"], torch.from_numpy(x).to(dev), n_t, href, ALPHA_PUSH)
            tf = EN.teacher_force(model, pr["ids"] + O, len(pr["ids"]), edits=ed)
            tstar = int(tf["logits"][-1].argmax())
            r2 = EN.teacher_force(model, pr["ids"] + O + [tstar], len(pr["ids"]), edits=ed, capture_blocks=[24],
                                  capture_pos=[len(pr["ids"]) + len(O)])
            extra.append(r2["caps"][24][0].cpu().numpy())
            extra_names.append(f"push{d}|{tok.decode([tstar])}")
        f, fp = P[(u, "F", "forced")], P[(u, "F", "forced_pad")]
        S = torch.arange(f["p1"], f["spec_end"], device=dev)
        Hf = spec_states(model, f, list(range(36)))
        Hp = spec_states(model, fp, list(range(36)))
        norms = {l: (Hf[l] - Hp[l]).norm(dim=1) for l in range(36)}
        for name, ed, p_ in (("forced", None, f), ("forced_pad", None, fp), ("exchange", EN.set_rows_edit(S, Hf), fp),
                             ("MR", EN.mr_edit(S, Hp, norms, stable_seed("MR_tf", u) % 2 ** 32)[0], fp)):
            tf = EN.teacher_force(model, p_["ids"] + O, len(p_["ids"]), edits=ed)
            tstar = int(tf["logits"][-1].argmax())
            r2 = EN.teacher_force(model, p_["ids"] + O + [tstar], len(p_["ids"]), edits=ed, capture_blocks=[24],
                                  capture_pos=[len(p_["ids"]) + len(O)])
            extra.append(r2["caps"][24][0].cpu().numpy())
            extra_names.append(f"{name}|{tok.decode([tstar])}")
        np.savez_compressed(CACHE_DIR / f"geometry_{u}.npz", X=X.astype(np.float32), toks=np.array(toks),
                            extra=np.array(extra, dtype=np.float32), extra_names=np.array(extra_names))
        logger.info(f"geometry {u}: {X.shape[0]} candidate fork states + {len(extra)} edited states")
        del Hf, Hp
        clear_prefills()


def run_stage(st: str, model: Any, tok: Any, units: list[str]) -> None:
    if st == "predict":
        stage_predict(model, tok, units)
    elif st == "collapsed_margins":
        stage_collapsed_margins(model, tok)
    elif st == "s4predict":
        stage_s4_predict(model, tok, units)
    elif st == "sweep":
        stage_sweep(model, tok, units)
    elif st.startswith("sweep10"):
        stage_sweep(model, tok, units, n_slots=2)
    elif st == "collapsed":
        stage_collapsed_check(model, tok)
    elif st == "s4a":
        stage_s4a(model, tok, units)
    elif st == "s4b":
        stage_s4b(model, tok, units)
    elif st == "geometry":
        stage_geometry(model, tok, units)
    else:
        raise ValueError(st)
