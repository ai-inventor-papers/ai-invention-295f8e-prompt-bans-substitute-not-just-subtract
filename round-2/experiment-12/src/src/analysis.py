#!/usr/bin/env python3
"""Stage 'analyse' (CPU): E3 readouts from the E2 tensors, D1 thought anchors, transfer-test verdicts, J-lens summary.

(i)   replication: exp3-fitted readout objects (top-1 latent, top-20-latent logistic, DiM, raw logistic, top-20 raw
      dimensions, DiM on the SAE code) applied to the fresh pool's k_pre / k16 states (cross-prompt-set AUC, pooled
      and within-template, bootstrap over runs), plus the full nested selection rerun inside the fresh pool
      (leave-one-template-out, within-template permutation null) and the overlap of the top-20 latent lists.
(ii)  attention from the k_pre query to the condition segment under ban vs neutral vs mention twins (same continuation),
      per head, per layer third, per segment token; outcome split with a within-template permutation test.
(iii) prime-veto: NAME(X), NAME(X'), IMPL(X), IMPL(X') latent sets and the DiM projection at R, k_pre and averaged over
      generated tokens 0..c, under ban / mention / neutral, paired per run, split by outcome.
D1    thought anchors: outcome distribution per resample point, TVD importance with a simulated multinomial floor,
      drift toward the trace's own outcome, sentence categories, early-label validity.
Every readout is descriptive.
"""

from __future__ import annotations

import gc
from collections import Counter, defaultdict
from typing import Any

import numpy as np
from loguru import logger
from scipy.stats import binomtest

from core import BANNED, RESULTS, SUBSTITUTE, TASKS, TEMPLATE_IDS, TENSORS, Timer, read_json, read_jsonl, write_json

UNRES = {"no_code", "unresolved", None}
CONDS = ["ban", "mention", "neutral"]
N_BOOT = 2000


def _labels() -> dict[tuple, dict[str, Any]]:
    return {(r["task"], r["template"], r["sample_id"]): r for r in read_jsonl(RESULTS / "labelled_c1.jsonl")}


def _boot_runs(y: np.ndarray, s: np.ndarray, g: np.ndarray, n_boot: int = N_BOOT, seed: int = 3) -> dict[str, Any]:
    from readout_i import auc, within_auc

    rng = np.random.default_rng(seed)
    pa, wa = [], []
    n = len(y)
    for _ in range(n_boot):
        ii = rng.integers(0, n, n)
        a = auc(y[ii], s[ii])
        if np.isfinite(a):
            pa.append(a)
        w, npair = within_auc(y[ii], s[ii], g[ii])
        if npair:
            wa.append(w)
    q = lambda v: [float(np.quantile(v, .025)), float(np.quantile(v, .975))] if len(v) > 20 else [None, None]  # noqa: E731
    return {"pooled_ci_runs": q(pa), "within_ci_runs": q(wa)}


def _codes(H: np.ndarray, S: dict[str, np.ndarray]) -> np.ndarray:
    from readout_i import sae_encode

    Z, _ = sae_encode(H.astype(np.float32), S, chunk=128)
    return Z


# ---------------------------------------------------------------- (i) replication
def readout_i_replication() -> dict[str, Any]:
    from readout_i import TOPN, apply_objects, auc, load_sae, nested_with_null, rank_units, within_auc

    E = np.load(TENSORS / "e2_states.npz")
    st, layers, pos_keys = E["states"], [int(x) for x in E["layers"]], [str(x) for x in E["pos_keys"]]
    meta = read_json(RESULTS / "e2_meta.json")["runs"]
    lab = _labels()
    DISC = read_json(RESULTS / "readout_i_discovery.json")
    out: dict[str, Any] = {"configs": {}, "class_counts": {}}
    for li, L in enumerate(layers):
        S = load_sae(L)
        for t in TASKS:
            idx = [m["i"] for m in meta if m["task"] == t]
            labs = [lab.get((t, meta[i]["template"], meta[i]["sample_id"]), {}) for i in idx]
            keep = [(i, r) for i, r in zip(idx, labs) if r.get("label") in (BANNED[t], SUBSTITUTE[t])]
            out["class_counts"][t] = {"n_banned": sum(r["label"] == BANNED[t] for _, r in keep),
                                      "n_substitute": sum(r["label"] == SUBSTITUTE[t] for _, r in keep),
                                      "per_template": {w: [sum(r["label"] == BANNED[t] for i, r in keep
                                                               if meta[i]["template"] == w),
                                                           sum(r["label"] == SUBSTITUTE[t] for i, r in keep
                                                               if meta[i]["template"] == w)] for w in TEMPLATE_IDS}}
            for pos in ("k_pre", "k16"):
                pj = pos_keys.index(pos)
                rows = [(i, r) for i, r in keep if np.isfinite(st[i, 0, pj, li, 0])]
                key = f"{t}|L{L}|{pos}"
                if len(rows) < 10:
                    out["configs"][key] = {"status": "too few runs", "n": len(rows)}
                    continue
                ii = np.array([i for i, _ in rows])
                y = np.array([int(r["label"] == BANNED[t]) for _, r in rows])
                g = np.array([TEMPLATE_IDS.index(meta[i]["template"]) for i in ii])
                neg = np.array([bool(r.get("negated_first_mention")) for _, r in rows])
                H = st[ii, 0, pj, li].astype(np.float32)
                Z = _codes(H, S)
                rec: dict[str, Any] = {"n": int(len(y)), "n_banned": int(y.sum()), "n_negated_first_mention": int(neg.sum()),
                                       "transfer_from_exp3": {}}
                obj = DISC["objects"].get(key)
                rec["run_index"] = ii.tolist()
                if obj is not None and int(y.sum()) > 0 and int(len(y) - y.sum()) > 0:
                    sc = apply_objects(obj, H, Z)
                    rec["run_scores"] = {m: np.asarray(v, dtype=float).round(5).tolist() for m, v in sc.items()}
                    for m, s in sc.items():
                        a = auc(y, s)
                        w, npair = within_auc(y, s, g)
                        r2 = {"auc_pooled": a, "auc_within_template": w, "n_within_pairs": npair,
                              **_boot_runs(y, s, g)}
                        if neg.any() and pos == "k_pre":
                            k = ~neg
                            if y[k].sum() > 0 and (1 - y[k]).sum() > 0:
                                r2["auc_pooled_without_negated"] = auc(y[k], s[k])
                                r2["auc_within_without_negated"] = within_auc(y[k], s[k], g[k])[0]
                        rec["transfer_from_exp3"][m] = r2
                # nested selection inside the fresh pool (leave-one-template-out) + nulls
                act = (Z != 0).sum(0) >= 5
                if act.sum() >= TOPN and len(np.unique(g)) >= 3 and y.sum() >= 3 and (1 - y).sum() >= 3:
                    Za = Z[:, act]
                    act_ids = np.where(act)[0]
                    res = nested_with_null(H, Za, y, g, n_perm=100, seed=L)
                    rec["nested_in_fresh_pool"] = res["methods"]
                    scr, sgn = rank_units(Za, y)
                    top = [int(act_ids[j]) for j in np.argsort(-scr, kind="stable")[:TOPN]]
                    ex = DISC["configs"].get(key, {}).get("final_top20", [])
                    ex_ids = [int(x["latent"]) for x in ex]
                    ov = len(set(top) & set(ex_ids))
                    n_union_active = int(act.sum())
                    rec["top20_fresh"] = top
                    rec["top20_overlap_with_exp3"] = {"overlap": ov, "jaccard": ov / len(set(top) | set(ex_ids))
                                                      if ex_ids else None,
                                                      "expected_overlap_by_chance": TOPN * len(ex_ids) / max(1, n_union_active),
                                                      "n_active_fresh": n_union_active}
                out["configs"][key] = rec
                logger.info(f"(i) {key}: n={len(y)} banned={int(y.sum())} " + " ".join(
                    f"{m}={v['auc_within_template']:.2f}" for m, v in rec["transfer_from_exp3"].items()
                    if v.get("auc_within_template") is not None and np.isfinite(v["auc_within_template"])))
        del S
        gc.collect()
    write_json(RESULTS / "readout_i_replication.json", out)
    return out


# ---------------------------------------------------------------- (ii) attention
def readout_ii_attention() -> dict[str, Any]:
    A = np.load(TENSORS / "e2_attention.npz")
    mass, segtok, regions = A["mass"], A["segtok"], [str(x) for x in A["regions"]]
    meta = read_json(RESULTS / "e2_meta.json")["runs"]
    P = read_json(RESULTS.parent / "prompts" / "prompts_v2.json")["prompts"]
    PO = read_json(RESULTS / "prompt_only_meta.json")["prompts"]
    lab = _labels()
    seg_i = regions.index("segment")
    out: dict[str, Any] = {"note": "descriptive: attention weights are not explanations; causal claims belong to C2",
                           "tasks": {}}
    rng = np.random.default_rng(11)
    for t in TASKS:
        idx = np.array([m["i"] for m in meta if m["task"] == t and np.isfinite(mass[m["i"], 0, 0, 0, 0, seg_i])])
        if len(idx) < 5:
            out["tasks"][t] = {"status": "too few runs"}
            continue
        seglen = {c: np.array([len(P[f"{t}|{c}|{meta[i]['template']}"]["nothink"]["spans"]["segment"]) for i in idx])
                  for c in CONDS}
        tot = {c: mass[idx, CONDS.index(c), 0, :, :, seg_i] for c in CONDS}  # (n, 36, 32)
        pert = {c: tot[c] / seglen[c][:, None, None] for c in CONDS}
        diff = tot["ban"] - tot["neutral"]
        mdiff = diff.mean(0)
        order = np.dstack(np.unravel_index(np.argsort(-mdiff, axis=None), mdiff.shape))[0][:10]
        heads = []
        for L, h in order:
            d = diff[:, L, h]
            bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(1000)]
            heads.append({"layer": int(L), "head": int(h), "ban_minus_neutral_total": float(d.mean()),
                          "ci95": [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))],
                          "m_ban": float(tot["ban"][:, L, h].mean()), "m_neutral": float(tot["neutral"][:, L, h].mean()),
                          "m_mention": float(tot["mention"][:, L, h].mean()),
                          "ban_minus_neutral_per_token": float((pert["ban"] - pert["neutral"])[:, L, h].mean()),
                          "ban_minus_mention_per_token": float((pert["ban"] - pert["mention"])[:, L, h].mean())})
        thirds = {}
        for name, (a, b) in {"layers_0_11": (0, 12), "layers_12_23": (12, 24), "layers_24_35": (24, 36)}.items():
            thirds[name] = {"ban_minus_neutral_total": float(diff[:, a:b].mean()),
                            "ban_minus_neutral_per_token": float((pert["ban"] - pert["neutral"])[:, a:b].mean()),
                            "ban_minus_mention_per_token": float((pert["ban"] - pert["mention"])[:, a:b].mean()),
                            "m_ban_total": float(tot["ban"][:, a:b].mean()),
                            "m_neutral_total": float(tot["neutral"][:, a:b].mean())}
        # per-token share inside the ban segment for the top-10 heads (per template; tokens decoded)
        tokshare = {}
        for w in TEMPLATE_IDS:
            iw = [k for k, i in enumerate(idx) if meta[i]["template"] == w]
            if not iw:
                continue
            toks = PO.get(f"{t}|ban|{w}", {}).get("segment_tokens", [])
            sh = np.zeros(len(toks))
            for L, h in order:
                v = segtok[idx[iw], 0, L, h, :len(toks)].astype(np.float64)
                v = v / np.maximum(v.sum(1, keepdims=True), 1e-12)
                sh += v.mean(0)
            sh /= len(order)
            tokshare[w] = {"tokens": toks, "share": sh.round(4).tolist(),
                           "most_attended": toks[int(np.argmax(sh))] if len(toks) else None,
                           "most_attended_index": int(np.argmax(sh)) if len(toks) else None}
        # outcome split: compliant (coded, not X) vs non-compliant (X); permutation within template
        labs = [lab.get((t, meta[i]["template"], meta[i]["sample_id"]), {}).get("label") for i in idx]
        ok = np.array([l not in UNRES for l in labs])
        nonc = np.array([l == BANNED[t] for l in labs])
        g = np.array([meta[i]["template"] for i in idx])
        stat_v = diff[:, order[:, 0], order[:, 1]].mean(1)  # per run: mean ban-specific attention over top-10 heads

        def split(v: np.ndarray) -> dict[str, Any]:
            vc, vn = v[ok & ~nonc], v[ok & nonc]
            if len(vc) < 3 or len(vn) < 3:
                return {"n_compliant": int(len(vc)), "n_noncompliant": int(len(vn)), "status": "too few"}
            obs = vc.mean() - vn.mean()
            null = []
            for _ in range(2000):
                perm = nonc.copy()
                for gg in np.unique(g):
                    m = (g == gg) & ok
                    perm[m] = rng.permutation(nonc[m])
                null.append(v[ok & ~perm].mean() - v[ok & perm].mean())
            null = np.array(null)
            return {"n_compliant": int(len(vc)), "n_noncompliant": int(len(vn)), "compliant_mean": float(vc.mean()),
                    "noncompliant_mean": float(vn.mean()), "diff": float(obs),
                    "p_two_sided_within_template_perm": float((1 + np.sum(np.abs(null) >= abs(obs))) / (1 + len(null)))}

        outcome = {"top10_heads_ban_minus_neutral": split(stat_v)}
        for name, (a, b) in {"layers_0_11": (0, 12), "layers_12_23": (12, 24), "layers_24_35": (24, 36)}.items():
            outcome[name] = split(diff[:, a:b].mean((1, 2)))
        outcome["raw_ban_mass_all_heads"] = split(tot["ban"].mean((1, 2)))
        kpost = mass[idx, 0, 1, :, :, seg_i] - mass[idx, 2, 1, :, :, seg_i]
        out["tasks"][t] = {"n_runs": int(len(idx)), "top10_heads": heads, "thirds": thirds, "token_share_top10": tokshare,
                           "outcome_split": outcome, "heatmap_ban_minus_neutral_total": mdiff.round(5).tolist(),
                           "k_post_query_thirds_ban_minus_neutral": {
                               n2: float(kpost[:, a:b].mean()) for n2, (a, b) in
                               {"layers_0_11": (0, 12), "layers_12_23": (12, 24), "layers_24_35": (24, 36)}.items()},
                           "region_mass_ban_kpre_mean_over_heads": {regions[r]: float(mass[idx, 0, 0, :, :, r].mean())
                                                                     for r in range(len(regions))}}
        logger.info(f"(ii) {t}: top head L{heads[0]['layer']}H{heads[0]['head']} ban-neutral "
                    f"{heads[0]['ban_minus_neutral_total']:.4f}; thirds "
                    f"{ {k: round(v['ban_minus_neutral_total'], 4) for k, v in thirds.items()} }")
    write_json(RESULTS / "readout_ii_attention.json", out)
    return out


# ---------------------------------------------------------------- (iii) prime-veto
def readout_iii_prime_veto(attn: dict[str, Any] | None = None) -> dict[str, Any]:
    from readout_i import load_sae

    E = np.load(TENSORS / "e2_states.npz")
    st, layers, pos_keys = E["states"], [int(x) for x in E["layers"]], [str(x) for x in E["pos_keys"]]
    meta = read_json(RESULTS / "e2_meta.json")["runs"]
    PO = np.load(TENSORS / "prompt_only_states.npz")
    POm = read_json(RESULTS / "prompt_only_meta.json")["prompts"]
    DISC = read_json(RESULTS / "readout_i_discovery.json")
    lab = _labels()
    out: dict[str, Any] = {"pattern": "NAME(X) active at R or k_pre under the ban (>= mention, > neutral) while "
                                      "IMPL(X) at k_pre is lower under ban than neutral for the same text",
                           "configs": {}, "attended_token_latents": {}}
    rng = np.random.default_rng(5)

    def name_acts(t: str, cond: str, li: int, S: dict) -> np.ndarray:
        vs = []
        for w in TEMPLATE_IDS:
            k = f"{t}|{cond}|{w}"
            m = POm[k]
            arr = PO[k.replace("|", "__")].astype(np.float32)  # (n_seg + 1, nL, 4096)
            sel = [m["segment_positions"].index(p) for p in m["name_positions"] if p in m["segment_positions"]]
            if sel:
                vs.append(_codes(arr[sel, li], S).mean(0))
        return np.mean(vs, 0)

    def paired(d: np.ndarray) -> dict[str, Any]:
        d = d[np.isfinite(d)]
        if len(d) < 3:
            return {"n": int(len(d))}
        npos, nneg = int((d > 0).sum()), int((d < 0).sum())
        bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(1000)]
        return {"n": int(len(d)), "mean": float(d.mean()), "ci95": [float(np.quantile(bs, .025)),
                                                                     float(np.quantile(bs, .975))],
                "n_pos": npos, "n_neg": nneg,
                "sign_test_p": float(binomtest(npos, npos + nneg).pvalue) if npos + nneg else None}

    for li, L in enumerate(layers):
        S = load_sae(L)
        for t in TASKS:
            key = f"{t}|L{L}"
            neu = name_acts(t, "neutral", li, S)
            nx = np.argsort(-(name_acts(t, "mention", li, S) - neu))[:10]
            nxs = np.argsort(-(name_acts(t, "submention", li, S) - neu))[:10]
            fin = DISC["configs"].get(f"{t}|L{L}|k_pre", {}).get("final_top20", [])
            impl_x = [int(x["latent"]) for x in fin if x["sign"] > 0]
            impl_xs = [int(x["latent"]) for x in fin if x["sign"] < 0]
            dim = DISC["objects"].get(f"{t}|L{L}|k_pre", {}).get("raw_dim")
            sets = {"NAME_X": nx.tolist(), "NAME_Xsub": nxs.tolist(), "IMPL_X": impl_x, "IMPL_Xsub": impl_xs}
            idx = [m["i"] for m in meta if m["task"] == t]
            res: dict[str, Any] = {"sets": sets, "positions": {}}
            labs = np.array([lab.get((t, meta[i]["template"], meta[i]["sample_id"]), {}).get("label") for i in idx],
                            dtype=object)
            nonc = np.array([l == BANNED[t] for l in labs])
            coded = np.array([l not in UNRES for l in labs])
            for pname in ("k_pre", "meangen"):
                pj = pos_keys.index(pname)
                ok = np.array([np.isfinite(st[i, 0, pj, li, 0]) for i in idx])
                ii = np.array(idx)[ok]
                acts = {}
                proj = {}
                for ci, c in enumerate(CONDS):
                    H = st[ii, ci, pj, li].astype(np.float32)
                    Z = _codes(H, S)
                    acts[c] = {s: Z[:, v].sum(1) if v else np.full(len(ii), np.nan) for s, v in sets.items()}
                    if dim is not None:
                        proj[c] = H @ np.array(dim["w"]) - dim["mid"]
                pr: dict[str, Any] = {}
                for s in sets:
                    pr[s] = {}
                    for a, b in (("ban", "neutral"), ("ban", "mention"), ("mention", "neutral")):
                        d = acts[a][s] - acts[b][s]
                        pr[s][f"{a}-{b}"] = {"all": paired(d), "compliant": paired(d[coded[ok] & ~nonc[ok]]),
                                             "noncompliant": paired(d[nonc[ok]])}
                    pr[s]["means"] = {c: float(np.nanmean(acts[c][s])) for c in CONDS}
                if proj:
                    pr["DiM_projection"] = {f"{a}-{b}": {"all": paired(proj[a] - proj[b]),
                                                         "compliant": paired((proj[a] - proj[b])[coded[ok] & ~nonc[ok]]),
                                                         "noncompliant": paired((proj[a] - proj[b])[nonc[ok]])}
                                            for a, b in (("ban", "neutral"), ("ban", "mention"), ("mention", "neutral"))}
                    pr["DiM_projection"]["means"] = {c: float(np.mean(proj[c])) for c in CONDS}
                res["positions"][pname] = pr
            # R: identical within a template -> one value per template (prompt-only passes), 5 templates
            rr: dict[str, Any] = {}
            for c in CONDS:
                zs = []
                for w in TEMPLATE_IDS:
                    arr = PO[f"{t}__{c}__{w}"].astype(np.float32)
                    zs.append(_codes(arr[-1:, li], S)[0])
                Zr = np.stack(zs)
                rr[c] = {s: (Zr[:, v].sum(1) if v else np.full(5, np.nan)) for s, v in sets.items()}
            res["positions"]["R_per_template"] = {s: {c: rr[c][s].round(4).tolist() for c in CONDS} for s in sets}
            # verdicts
            kp = res["positions"]["k_pre"]
            nxr = res["positions"]["R_per_template"]["NAME_X"]
            name_r = (np.mean(nxr["ban"]) >= np.mean(nxr["mention"])) and (np.mean(nxr["ban"]) > np.mean(nxr["neutral"]))
            name_k = (kp["NAME_X"]["ban-mention"]["all"].get("mean", np.nan) >= 0 and
                      kp["NAME_X"]["ban-neutral"]["all"].get("mean", np.nan) > 0)
            impl = kp["IMPL_X"]["ban-neutral"]["all"].get("mean", np.nan) < 0
            dimv = kp.get("DiM_projection", {}).get("ban-neutral", {}).get("all", {}).get("mean", np.nan)
            res["verdict"] = {"NAME_X_ban_ge_mention_gt_neutral_at_R": bool(name_r),
                              "NAME_X_ban_ge_mention_gt_neutral_at_k_pre": bool(name_k),
                              "IMPL_X_lower_under_ban_than_neutral_at_k_pre": bool(impl),
                              "DiM_projection_lower_under_ban_than_neutral_at_k_pre": bool(dimv < 0)
                              if np.isfinite(dimv) else None,
                              "prime_veto_pattern_present": bool((name_r or name_k) and impl),
                              "latent_result_reproduced_by_DiM": bool(impl == (dimv < 0)) if np.isfinite(dimv) else None}
            out["configs"][key] = res
            logger.info(f"(iii) {key}: {res['verdict']}")
            # latents at the most-attended ban-segment tokens (top-10 heads of readout ii)
            if attn and t in attn.get("tasks", {}) and "token_share_top10" in attn["tasks"][t]:
                tl = {}
                for w, v in attn["tasks"][t]["token_share_top10"].items():
                    j = v.get("most_attended_index")
                    if j is None:
                        continue
                    arr = PO[f"{t}__ban__{w}"].astype(np.float32)
                    z = _codes(arr[j:j + 1, li], S)[0]
                    top = np.argsort(-z)[:10]
                    tl[w] = {"token": v["most_attended"], "top10_latents": top.tolist(),
                             "activations": z[top].round(3).tolist()}
                out["attended_token_latents"][key] = tl
        del S
        gc.collect()
    write_json(RESULTS / "readout_iii_prime_veto.json", out)
    return out


def latent_contexts(n_ctx: int = 10, width: int = 12) -> dict[str, Any]:
    """Top-activating contexts (+-12 tokens) in the E1 instruct context corpus for the readout latents."""
    from transformers import AutoTokenizer

    from core import MODEL_HF
    from hf_stage import transfer_corpus

    tok = AutoTokenizer.from_pretrained(MODEL_HF)
    corpus = transfer_corpus(tok)
    DISC = read_json(RESULTS / "readout_i_discovery.json")
    PV = read_json(RESULTS / "readout_iii_prime_veto.json", {})
    out: dict[str, Any] = {"note": "top-activating contexts are hypotheses, not explanations", "layers": {}}
    for f in sorted(TENSORS.glob("context_codes_L*.npz")):
        if "smoke" in f.name:
            continue
        L = int(f.stem.split("_L")[1])
        C = np.load(f)
        idx, val, off = C["idx"], C["val"].astype(np.float32), C["offsets"]
        want = set()
        for key, c in DISC["configs"].items():
            if f"|L{L}|" in key and "final_top20" in c:
                want |= {int(x["latent"]) for x in c["final_top20"][:5]}
        for key, c in PV.get("configs", {}).items():
            if key.endswith(f"|L{L}"):
                want |= set(c["sets"]["NAME_X"][:3]) | set(c["sets"]["NAME_Xsub"][:3])
        seq_of = np.searchsorted(off, np.arange(len(idx)), side="right") - 1
        res = {}
        for lat in sorted(want):
            hit = (idx == lat)
            rows = np.where(hit.any(1))[0]
            if len(rows) == 0:
                res[str(lat)] = {"n_tokens_active": 0, "contexts": []}
                continue
            acts = (val * hit).sum(1)[rows]
            top = rows[np.argsort(-acts)[:n_ctx]]
            ctx = []
            for r in top:
                s = seq_of[r]
                p = r - off[s] + 1  # position in the sequence (codes start at position 1)
                ids = corpus[s]["ids"]
                ctx.append({"seq": int(s), "task": corpus[s]["task"], "condition": corpus[s]["condition"],
                            "act": float((val[r] * hit[r]).sum()),
                            "left": tok.decode(ids[max(0, p - width):p]), "token": tok.decode([ids[p]]),
                            "right": tok.decode(ids[p + 1:p + 1 + width])})
            res[str(lat)] = {"n_tokens_active": int(len(rows)), "contexts": ctx}
        out["layers"][str(L)] = res
    write_json(RESULTS / "latent_contexts.json", out)
    return out


# ---------------------------------------------------------------- transfer verdicts + J-lens summary
def transfer_summary() -> dict[str, Any]:
    TT = read_json(RESULTS / "transfer_test.json", {})
    if "instruct" not in TT or "base" not in TT:
        return {"status": "incomplete", "have": list(TT)}
    rng = np.random.default_rng(2)
    out: dict[str, Any] = {"rule": "PASS(L) := dCE_inst(L) <= 1.5 x dCE_base(L) (spliced-in CE over response tokens)",
                           "ce_clean_inst": float(np.mean(TT["instruct"]["ce_clean_per_seq"])),
                           "ce_clean_base": float(np.mean(TT["base"]["ce_clean_per_seq"])), "layers": {},
                           "splice_sanity": TT.get("splice_sanity"), "eager_check": TT.get("eager_check")}
    for L, ri in TT["instruct"]["layers"].items():
        rb = TT["base"]["layers"][L]
        di, db = np.array(ri["dce_per_seq"]), np.array(rb["dce_per_seq"])
        bs = []
        for _ in range(N_BOOT):
            k = rng.integers(0, len(di), len(di))
            if db[k].mean() > 0:
                bs.append(di[k].mean() / db[k].mean())
        ratio = di.mean() / db.mean() if db.mean() > 0 else float("inf")
        out["layers"][L] = {"dce_inst": float(di.mean()), "dce_base": float(db.mean()), "ratio": float(ratio),
                            "ratio_ci95": [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))] if bs else None,
                            "pass": bool(ratio <= 1.5),
                            "fvu_inst": ri["fvu"], "fvu_base": rb["fvu"], "rel_mse_inst": ri["rel_mse_mean"],
                            "rel_mse_base": rb["rel_mse_mean"], "cos_inst": ri["cos_mean"], "cos_base": rb["cos_mean"],
                            "share_norm_gt_5x_median_inst": ri["share_norm_gt_5x_median"]}
    out["n_pass"] = sum(v["pass"] for v in out["layers"].values())
    write_json(RESULTS / "transfer_summary.json", out)
    return out


def jlens_summary() -> dict[str, Any]:
    JL = read_json(RESULTS / "jlens.json", {})
    if not JL:
        return {"status": "not run"}
    meta = read_json(RESULTS / "e2_meta.json")["runs"]
    lab = _labels()
    app = JL["application"]
    names = app["tokens"]
    out: dict[str, Any] = {"gate": JL["gate"], "fresh_by_class": {}, "R": {}}
    for key, v in app["fresh"].items():
        runs = v["run_index"]
        P_, R_ = np.array(v["prob"]), np.array(v["rank"])
        for t in TASKS:
            for cls in (BANNED[t], SUBSTITUTE[t]):
                sel = [k for k, i in enumerate(runs) if meta[i]["task"] == t and
                       lab.get((t, meta[i]["template"], meta[i]["sample_id"]), {}).get("label") == cls]
                if sel:
                    out["fresh_by_class"][f"{t}|{cls}|{key}"] = {
                        "n": len(sel), "mean_prob": dict(zip(names, P_[sel].mean(0).round(6).tolist())),
                        "median_rank": dict(zip(names, np.median(R_[sel], 0).tolist()))}
    out["R"] = app["R"]
    write_json(RESULTS / "jlens_summary.json", out)
    return out


# ---------------------------------------------------------------- D1 thought anchors
def thought_anchors() -> dict[str, Any]:
    from early_label import early_label, sentence_category

    traces = {r["trace_id"]: r for r in read_jsonl(RESULTS / "labelled_c2.jsonl")}
    conts = read_jsonl(RESULTS / "labelled_c3.jsonl") or read_jsonl(RESULTS / "raw" / "c3_continuations.jsonl")
    comps = read_jsonl(RESULTS / "labelled_c4.jsonl")
    bounds = read_json(RESULTS / "thought_anchor_boundaries.json", {})
    out: dict[str, Any] = {"traces": {}, "completion": {}, "validity": {}}
    for t in TASKS:
        tr = [r for r in traces.values() if r["task"] == t]
        k = sum(bool(r.get("complete")) for r in tr)
        closed = sum(r.get("think_close_idx") is not None for r in tr)
        from core import wilson

        out["completion"][t] = {"n": len(tr), "complete_within_8192": k, "wilson": wilson(k, len(tr)),
                                "closed_thinking_within_9600": closed,
                                "think_tokens": [r.get("think_close_idx") for r in tr],
                                "code_labels": [r.get("label") for r in tr]}
    rng = np.random.default_rng(13)
    pooled_cat = Counter()
    anchor_cat = Counter()
    for tid_s, b in bounds.items():
        tid = int(tid_s)
        tr = traces.get(tid)
        if tr is None:
            continue
        t = tr["task"]
        cs = [c for c in conts if c["trace_id"] == tid]
        if not cs:
            continue
        think = tr["text"].split("</think>", 1)[0]
        own_early = early_label(t, think)["label"]
        final = tr.get("label") if tr.get("label") not in UNRES else own_early

        def outcome(c: dict[str, Any]) -> str:
            el = c.get("early_label")
            if el in (None, "None") and c.get("reached_code"):
                return str(c.get("label") or "undecided")
            return str(el or "undecided")

        npts = len(b["points"])
        D, ns = [], []
        for kk in range(npts):
            oc = [outcome(c) for c in cs if c["boundary_k"] == kk]
            D.append(Counter(oc))
            ns.append(len(oc))
        cats = sorted(set().union(*[set(d) for d in D]))
        Dv = np.array([[d[c] / max(1, n) for c in cats] for d, n in zip(D, ns)])
        tv, floor, anchors = [], [], []
        sents = b["sentences"]
        scat = [sentence_category(t, s, BANNED[t]) for s in sents]
        for kk in range(1, npts):
            tvd = 0.5 * np.abs(Dv[kk] - Dv[kk - 1]).sum()
            pool = (Dv[kk] + Dv[kk - 1]) / 2
            pool = pool / pool.sum() if pool.sum() > 0 else np.ones(len(cats)) / len(cats)
            a = rng.multinomial(ns[kk], pool, size=10000) / max(1, ns[kk])
            bb = rng.multinomial(ns[kk - 1], pool, size=10000) / max(1, ns[kk - 1])
            q95 = float(np.quantile(0.5 * np.abs(a - bb).sum(1), 0.95))
            tv.append(float(tvd))
            floor.append(q95)
            if tvd > q95:
                anchors.append(kk)
        fi = cats.index(final) if final in cats else None
        delta = [float(Dv[kk, fi] - Dv[kk - 1, fi]) if fi is not None else None for kk in range(1, npts)]
        mx = int(np.argmax(tv)) + 1 if tv else None
        for kk in anchors:
            anchor_cat[scat[kk - 1]] += 1
        if mx is not None:
            pooled_cat[scat[mx - 1]] += 1
        out["traces"][str(tid)] = {"task": t, "complete": tr.get("complete"), "final_reference": final,
                                   "final_reference_source": "code label" if tr.get("label") not in UNRES else
                                   "early label of the trace text", "own_early_label": own_early,
                                   "categories": cats, "D": Dv.round(3).tolist(), "n_per_point": ns,
                                   "D0_max_share": float(Dv[0].max()), "D0_fixed_ge_5of6": bool(Dv[0].max() >= 5 / 6),
                                   "tvd": tv, "noise_floor_q95": floor, "anchors": anchors,
                                   "delta_toward_final": delta, "max_tvd_sentence": mx,
                                   "sentences": sents, "sentence_categories": scat,
                                   "boundary_check": b.get("boundary_check")}
    out["pooled_max_tvd_sentence_category"] = dict(pooled_cat)
    out["pooled_anchor_category"] = dict(anchor_cat)
    # early-label validity: base traces (early label of the thinking text vs code label) + C4 completions
    pairs = []
    for r in traces.values():
        if r.get("label") in UNRES:
            continue
        el = early_label(r["task"], r["text"].split("</think>", 1)[0])["label"]
        pairs.append(("base_trace", el, r["label"]))
    for r in comps:
        if r.get("label") in UNRES:
            continue
        pairs.append(("completion", r.get("early_label_at_chunk"), r["label"]))
    agree = [a == b for _, a, b in pairs if a not in (None, "undecided")]
    out["validity"] = {"pairs": pairs, "n_decided": len(agree), "agreement": float(np.mean(agree)) if agree else None,
                       "F7_stated_plan_wording": bool(agree and np.mean(agree) < 0.8)}
    write_json(RESULTS / "thought_anchors.json", out)
    return out


def run_stage_analyse() -> None:
    parts = {}
    for name, fn in (("transfer_summary", transfer_summary), ("readout_i_replication", readout_i_replication),
                     ("readout_ii_attention", readout_ii_attention)):
        with Timer(f"analyse_{name}", gpu=False):
            try:
                parts[name] = fn()
            except Exception as e:  # noqa: BLE001 - each readout is reported independently
                logger.exception(f"{name} failed: {e!r}")
                parts[name] = {"status": f"failed: {e!r}"[:300]}
    for name, fn in (("readout_iii_prime_veto", lambda: readout_iii_prime_veto(parts.get("readout_ii_attention"))),
                     ("latent_contexts", latent_contexts), ("jlens_summary", jlens_summary),
                     ("thought_anchors", thought_anchors)):
        with Timer(f"analyse_{name}", gpu=False):
            try:
                parts[name] = fn()
            except Exception as e:  # noqa: BLE001
                logger.exception(f"{name} failed: {e!r}")
                parts[name] = {"status": f"failed: {e!r}"[:300]}
    write_json(RESULTS / "analysis_status.json", {k: ("ok" if not (isinstance(v, dict) and str(v.get("status", ""))
                                                                    .startswith("failed")) else v["status"])
                                                  for k, v in parts.items()})
