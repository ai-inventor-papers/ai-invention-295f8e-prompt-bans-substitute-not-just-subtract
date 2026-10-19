#!/usr/bin/env python3
"""Phase B (HF): read-position states, R gate + layer choice, centroids, manifold, directions/anchors,
decomposition basis, and the hash-COMMITTED forecasts (before any Phase C/D sample exists).

Inputs : prompts/prompts.jsonl (with succession prompts), data/samples_phaseA.jsonl, results/phaseA_summary.json
Outputs: cache/hR_layer{l}.npy + cache/hR_index.jsonl, cache/suffix_means_{task}.npz, results/gate.json,
         results/geometry_b.json, cache/directions_{task}.npz, cache/anchors_{task}.npz, cache/basis_{task}.npz,
         predictions/predictions_v1.json + predictions/commit_log.jsonl
"""
from __future__ import annotations

import argparse
import datetime
import gc
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "gen"))
sys.path.insert(0, str(ROOT / "analysis"))
from common import (CACHE_LAYERS, CATALOGUE, TASKS, add_deviation, append_jsonl, js_div, log_timing,  # noqa: E402
                    read_jsonl, set_limits, setup_logger, sha256_file)
from geometry import attach, geodesic_between, knn_graph, pca95, softmax_neg  # noqa: E402

logger = setup_logger("phase_b")
CACHE = ROOT / "cache"
N_SHUF = 20
GEN_T = 64


# ============================================================================================ 7a forward passes
def forward_states(model, tok, prompts: list[dict], batch: int = 16):
    import torch
    from hf_engine import left_pad

    N = len(prompts)
    D = model.config.hidden_size
    H = {l: np.zeros((N, D), np.float16) for l in CACHE_LAYERS}
    named = {}
    for t in TASKS:
        L = next(p["suffix_len"] for p in prompts if p["task"] == t)
        named[t] = {"L_s": L, "sum": {m: torch.zeros(len(CACHE_LAYERS), L, D, dtype=torch.float32, device="cuda")
                                      for m in CATALOGUE[t]}, "n": Counter()}
    order = sorted(range(N), key=lambda i: prompts[i]["n_tokens"])
    t0 = time.time()
    for s in range(0, N, batch):
        idx = order[s:s + batch]
        ids, att = left_pad([prompts[i]["prompt_ids"] for i in idx], "cuda")
        pos = (att.cumsum(-1) - 1).clamp(min=0)
        with torch.inference_mode():
            out = model.model(input_ids=ids, attention_mask=att, position_ids=pos, output_hidden_states=True,
                              use_cache=False)
        hs = out.hidden_states
        for li, l in enumerate(CACHE_LAYERS):
            H[l][idx] = hs[l + 1][:, -1, :].float().cpu().numpy().astype(np.float16)
        for bi, i in enumerate(idx):
            p = prompts[i]
            if p["condition"].startswith("forced:"):
                t = p["task"]
                m = p["condition"].split(":", 1)[1]
                L = named[t]["L_s"]
                for li, l in enumerate(CACHE_LAYERS):
                    named[t]["sum"][m][li] += hs[l + 1][bi, -L:, :].float()
                named[t]["n"][m] += 1
        del out, hs
    logger.info(f"7a: {N} prompts forward in {time.time() - t0:.0f}s")
    log_timing("B", "forward_states", N, time.time() - t0)
    return H, named


def padding_check(model, tok, prompts: list[dict], H: dict) -> dict:
    """h_R of a prompt alone vs inside the left-padded batch (testing plan 5d)."""
    import torch

    res = []
    for i in [0, len(prompts) // 2, len(prompts) - 1]:
        ids = torch.tensor([prompts[i]["prompt_ids"]], device="cuda")
        with torch.inference_mode():
            out = model.model(input_ids=ids, output_hidden_states=True, use_cache=False)
        for l in (CACHE_LAYERS[0], 20, CACHE_LAYERS[-1]):
            a = out.hidden_states[l + 1][0, -1].float().cpu().numpy()
            b = H[l][i].astype(np.float32)
            res.append(float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)))
    return {"min_cos": min(res), "cosines": res, "pass": min(res) > 0.999}


# ============================================================================================ 7b gate
def _gate_one_layer(l: int, Xn, yn, gn, Xm, ym, Xb, base_dist, K: int, seed: int) -> dict:
    from threadpoolctl import threadpool_limits

    with threadpool_limits(1):
        return _gate_one_layer_inner(l, Xn, yn, gn, Xm, ym, Xb, base_dist, K, seed)


def _gate_one_layer_inner(l: int, Xn, yn, gn, Xm, ym, Xb, base_dist, K: int, seed: int) -> dict:
    from functools import partial

    from sklearn.decomposition import PCA
    from sklearn.linear_model import LogisticRegression as _LR
    from sklearn.model_selection import GroupKFold

    LogisticRegression = partial(_LR, tol=1e-3)

    rng = np.random.default_rng(seed + l)
    nc = min(50, Xn.shape[0] - 12)
    folds = list(GroupKFold(n_splits=len(np.unique(gn))).split(Xn, yn, gn))
    Z = []
    correct = 0
    ll = 0.0
    for tr, te in folds:
        pca = PCA(nc, random_state=0, svd_solver='randomized').fit(Xn[tr])
        Ztr, Zte = pca.transform(Xn[tr]), pca.transform(Xn[te])
        clf = LogisticRegression(C=1.0, max_iter=3000).fit(Ztr, yn[tr])
        pr = clf.predict_proba(Zte)
        correct += int((clf.classes_[pr.argmax(1)] == yn[te]).sum())
        cls = list(clf.classes_)
        ll += float(np.sum(np.log(np.clip([pr[i, cls.index(y)] if y in cls else 1e-9 for i, y in enumerate(yn[te])], 1e-9, 1))))
        Z.append((tr, te, Ztr, Zte))
    named_acc = correct / len(yn)
    null_named = []
    for s in range(N_SHUF):
        yp = rng.permutation(yn)
        c = 0
        for tr, te, Ztr, Zte in Z:
            clf = LogisticRegression(C=1.0, max_iter=300).fit(Ztr, yp[tr])
            c += int((clf.predict(Zte) == yn[te]).sum())
        null_named.append(c / len(yn))
    pca = PCA(nc, random_state=0, svd_solver='randomized').fit(Xn)
    Zn, Zm, Zb = pca.transform(Xn), pca.transform(Xm), pca.transform(Xb)
    clf = LogisticRegression(C=1.0, max_iter=3000).fit(Zn, yn)
    transfer = float((clf.predict(Zm) == ym).mean())
    pdec = np.zeros(K)
    pdec[clf.classes_] = clf.predict_proba(Zb).mean(0)
    js = js_div(pdec, base_dist)
    null_tr, null_js = [], []
    for s in range(N_SHUF):
        yp = rng.permutation(yn)
        c2 = LogisticRegression(C=1.0, max_iter=300).fit(Zn, yp)
        null_tr.append(float((c2.predict(Zm) == ym).mean()))
        q = np.zeros(K)
        q[c2.classes_] = c2.predict_proba(Zb).mean(0)
        null_js.append(js_div(q, base_dist))
    return {"layer": l, "named_acc": named_acc, "named_loglik": ll, "null_named_p95": float(np.percentile(null_named, 95)),
            "null_named_mean": float(np.mean(null_named)), "transfer_acc": transfer,
            "null_transfer_p95": float(np.percentile(null_tr, 95)), "null_transfer_mean": float(np.mean(null_tr)),
            "decoder_js": js, "null_js_p5": float(np.percentile(null_js, 5)), "null_js_mean": float(np.mean(null_js)),
            "decoder_dist": pdec.tolist()}


def run_gate(H, index, summA) -> dict:
    from joblib import Parallel, delayed

    out = {}
    for t in TASKS:
        cat = CATALOGUE[t]
        K = len(cat)
        sel = lambda pref: [i for i, r in enumerate(index) if r["task"] == t and r["condition"].startswith(pref)]  # noqa: E731
        iN, iM, iB = sel("forced:"), sel("masked:"), [i for i, r in enumerate(index) if r["task"] == t and r["condition"] == "baseline"]
        yn = np.array([cat.index(index[i]["condition"].split(":")[1]) for i in iN])
        gn = np.array([index[i]["frame_id"] for i in iN])
        ym = np.array([cat.index(index[i]["condition"].split(":")[1]) for i in iM])
        bc = summA[t]["baseline_label_counts"]
        base_dist = np.array([bc.get(m, 0) for m in cat], float)
        base_dist = base_dist / max(base_dist.sum(), 1)
        t0 = time.time()
        res = Parallel(n_jobs=6, backend="loky")(
            delayed(_gate_one_layer)(l, H[l][iN].astype(np.float32), yn, gn, H[l][iM].astype(np.float32), ym,
                                     H[l][iB].astype(np.float32), base_dist, K, 1234) for l in CACHE_LAYERS)
        logger.info(f"7b gate {t}: {len(res)} layers in {time.time() - t0:.0f}s")
        best = max(res, key=lambda r: (round(r["transfer_acc"], 6), -r["decoder_js"]))
        lstar = best["layer"]
        band = [l for l in range(lstar - 3, lstar + 4) if CACHE_LAYERS[0] <= l <= CACHE_LAYERS[-1]]
        passed = (best["named_acc"] >= best["null_named_p95"] + 0.20 and
                  best["transfer_acc"] >= best["null_transfer_p95"] + 0.20 and best["decoder_js"] < best["null_js_p5"])
        out[t] = {"per_layer": res, "l_star": lstar, "band": band, "gate_pass": bool(passed),
                  "baseline_dist": base_dist.tolist(), "criterion": "argmax masked-transfer accuracy (ties: lower decoder JS)"}
        if not passed:
            ll_best = max(res, key=lambda r: r["named_loglik"])
            out[t]["R_gate_failed"] = True
            add_deviation(f"{t}: R gate failed at l*={lstar} (named {best['named_acc']:.2f} vs null95 "
                          f"{best['null_named_p95']:.2f}; transfer {best['transfer_acc']:.2f} vs null95 "
                          f"{best['null_transfer_p95']:.2f}; decoder JS {best['decoder_js']:.3f} vs null p5 "
                          f"{best['null_js_p5']:.3f}). Geometry and C3 are reported descriptively with the flag "
                          f"'R gate failed'; best named log-likelihood layer = {ll_best['layer']}.")
        logger.info(f"{t}: l*={lstar} band={band} named={best['named_acc']:.2f} (null95 {best['null_named_p95']:.2f}) "
                    f"transfer={best['transfer_acc']:.2f} (null95 {best['null_transfer_p95']:.2f}) "
                    f"decoderJS={best['decoder_js']:.3f} (null p5 {best['null_js_p5']:.3f}) pass={passed}")
    add_deviation("Layer choice: named-only probe accuracy saturates because the algorithm name is in context, so l* "
                  "is the argmax of named->masked transfer accuracy (as pre-declared).")
    return out


# ============================================================================================ helpers
def centroids(H, index, t, l, kind="forced"):
    cat = CATALOGUE[t]
    C = np.stack([H[l][[i for i, r in enumerate(index) if r["task"] == t and r["condition"] == f"{kind}:{m}"]]
                  .astype(np.float32).mean(0) for m in cat])
    return C


def within_pcs(H, index, t, l, k=3):
    cat = CATALOGUE[t]
    R = []
    for m in cat:
        X = H[l][[i for i, r in enumerate(index) if r["task"] == t and r["condition"] == f"forced:{m}"]].astype(np.float32)
        R.append(X - X.mean(0))
    R = np.concatenate(R)
    _, _, Vt = np.linalg.svd(R, full_matrices=False)
    return Vt[:k]


def orth(v, B):
    for b in B:
        b = b / (np.linalg.norm(b) + 1e-12)
        v = v - (v @ b) * b
    return v


def unit(v):
    return v / (np.linalg.norm(v) + 1e-12)


def auc(pos, neg):
    from sklearn.metrics import roc_auc_score

    y = np.r_[np.ones(len(pos)), np.zeros(len(neg))]
    return float(roc_auc_score(y, np.r_[pos, neg]))


def direction(H, index, t, l, X, rows=None):
    """d_X = c_X - mean_{j!=X} c_j, orthogonalised against the top-3 within-mode PCs, unit norm."""
    cat = CATALOGUE[t]
    sel = [i for i, r in enumerate(index) if r["task"] == t and r["condition"].startswith("forced:")]
    if rows is not None:
        sel = [i for i in sel if i in rows]
    Xs = H[l][sel].astype(np.float32)
    ms = [index[i]["condition"].split(":")[1] for i in sel]
    C = {m: Xs[[k for k, mm in enumerate(ms) if mm == m]].mean(0) for m in cat}
    W = np.concatenate([Xs[[k for k, mm in enumerate(ms) if mm == m]] - C[m] for m in cat])
    _, _, Vt = np.linalg.svd(W, full_matrices=False)
    d = C[X] - np.mean([C[m] for m in cat if m != X], 0)
    return unit(orth(d, Vt[:3])), Vt[:3]


# ============================================================================================ main
@logger.catch(reraise=True)
def main() -> None:
    import torch

    ap = argparse.ArgumentParser()
    ap.add_argument("--reuse-cache", action="store_true", help="skip 7a if cache/hR_* exist")
    args = ap.parse_args()
    set_limits(45)
    prompts = [p for p in read_jsonl(ROOT / "prompts" / "prompts.jsonl") if p["kind"] == "geom"]
    rowsA = read_jsonl(ROOT / "data" / "samples_phaseA.jsonl")
    summA = json.loads((ROOT / "results" / "phaseA_summary.json").read_text())
    modal = {t: summA[t]["modal"] for t in TASKS}
    CACHE.mkdir(exist_ok=True)
    from hf_engine import load_model

    model, tok = load_model(logger)
    t_all = time.time()
    if args.reuse_cache and (CACHE / "hR_index.jsonl").exists():
        index = read_jsonl(CACHE / "hR_index.jsonl")
        H = {l: np.load(CACHE / f"hR_layer{l}.npy") for l in CACHE_LAYERS}
        suffix_means = {t: {m: np.load(CACHE / f"suffix_means_{t}_{m}.npy") for m in CATALOGUE[t]} for t in TASKS}
        pad = {"skipped": True}
    else:
        H, named = forward_states(model, tok, prompts)
        index = [{k: p.get(k) for k in ("prompt_id", "task", "condition", "paraphrase_id", "frame_id", "n_tokens",
                                        "ids_sha256", "suffix_len")} for p in prompts]
        for l in CACHE_LAYERS:
            np.save(CACHE / f"hR_layer{l}.npy", H[l])
        from common import write_jsonl

        write_jsonl(CACHE / "hR_index.jsonl", index)
        suffix_means = {}
        for t in TASKS:
            suffix_means[t] = {m: (named[t]["sum"][m] / max(named[t]["n"][m], 1)).cpu().numpy().astype(np.float16)
                               for m in CATALOGUE[t]}
            for m in CATALOGUE[t]:  # one file per mode keeps every file below the 100 MB limit
                np.save(CACHE / f"suffix_means_{t}_{m}.npy", suffix_means[t][m])
        del named
        torch.cuda.empty_cache()
        pad = padding_check(model, tok, prompts, H)
        logger.info(f"padding check: {pad}")

    # ---------------------------------------------------------------- 7b gate
    gate = run_gate(H, index, summA)
    gate["padding_check"] = pad
    (ROOT / "results" / "gate.json").write_text(json.dumps(gate, indent=1))

    geo_out: dict = {}
    preds: dict = {"created_utc": None, "model": "Qwen3-8B", "events": {}, "notes": [
        "association = Borda A(X_k -> .) restricted to survivors (ladder rule); association_X1 = A(X_1 -> .) sensitivity",
        "frequency = baseline counts + 1 restricted to survivors", "geodesic = softmax(-d_geo/median inter-centroid d_geo)",
        "decoder (exploratory) = l* probe on the mean h_R of the event's ban prompt; removal uses the affine-ablated "
        "baseline h_R"]}
    for t in TASKS:
        cat = CATALOGUE[t]
        X1 = modal[t]
        lstar, band = gate[t]["l_star"], gate[t]["band"]
        g: dict = {"l_star": lstar, "band": band}
        # ---------------------------------------------------------------- 7c centroids + masked robustness
        from scipy.spatial import procrustes

        Cn = centroids(H, index, t, lstar)
        Cm = centroids(H, index, t, lstar, "masked")
        _, _, disp = procrustes(Cn - Cn.mean(0), Cm - Cm.mean(0))
        cosm = [float(unit(a) @ unit(b)) for a, b in zip(Cn - Cn.mean(0), Cm - Cm.mean(0))]
        g["procrustes_disparity_named_vs_masked"] = float(disp)
        g["per_mode_cos_named_vs_masked"] = dict(zip(cat, cosm))
        # ---------------------------------------------------------------- 7d manifold at l*
        iN = [i for i, r in enumerate(index) if r["task"] == t and r["condition"].startswith("forced:")]
        labN = [index[i]["condition"].split(":")[1] for i in iN]
        Xn = H[lstar][iN].astype(np.float32)
        mu, comps, ev = pca95(Xn)
        P = (Xn - mu) @ comps.T
        Cp = (Cn - mu) @ comps.T
        G, ginfo = knn_graph(P, 10)
        Dc = geodesic_between(G, P, Cp, 10)
        Dc = (Dc + Dc.T) / 2
        off = Dc[np.triu_indices(len(cat), 1)]
        med = float(np.median(off))
        g.update({"pca_dims": int(comps.shape[0]), "pca_explained": float(ev.sum()), "graph": ginfo,
                  "centroid_geodesic": Dc.tolist(), "median_intercentroid_geodesic": med})
        rob = {}
        from scipy.stats import spearmanr

        for k in (5, 15, 20):
            Gk, _ = knn_graph(P, k)
            Dk = geodesic_between(Gk, P, Cp, k)
            rob[f"k{k}"] = float(spearmanr(Dk[np.triu_indices(len(cat), 1)], off)[0])
        Gc, _ = knn_graph(Xn, 10, "cosine")
        Dcos = geodesic_between(Gc, Xn, Cn, 10, "cosine")
        rob["cosine_full"] = float(spearmanr(Dcos[np.triu_indices(len(cat), 1)], off)[0])
        g["geodesic_robustness_spearman_vs_k10"] = rob
        # ---------------------------------------------------------------- 7f directions + anchors (modal X)
        dirs: dict = {}
        sm = suffix_means[t]
        surv = [m for m in cat if m != X1]
        auc_R = {}
        d_hat, wpcs = {}, {}
        for l in band:
            d, W3 = direction(H, index, t, l, X1)
            d_hat[l], wpcs[l] = d, W3
            # held-out AUC at R: GroupKFold(5) by frame, d refit on training folds
            from sklearn.model_selection import GroupKFold

            frames = np.array([index[i]["frame_id"] for i in iN])
            y = np.array([m == X1 for m in labN])
            scores = np.zeros(len(iN))
            for tr, te in GroupKFold(5).split(iN, y, frames):
                dtr, _ = direction(H, index, t, l, X1, rows=set(np.array(iN)[tr].tolist()))
                scores[te] = H[l][np.array(iN)[te]].astype(np.float32) @ dtr
            auc_R[l] = auc(scores[y], scores[~y])
        # teacher forcing on generated positions
        from hf_engine import left_pad

        base_prompts = sorted([p for p in prompts if p["task"] == t and p["condition"] == "baseline"],
                              key=lambda p: p["paraphrase_id"])
        bx = [r for r in rowsA if r["task"] == t and r["condition"] == "baseline" and r["label"] == X1 and r.get("code")]
        bx = sorted(bx, key=lambda r: (not r["passed"], r["paraphrase_id"], r["sample_id"]))[:32]
        pool_nat = [r for r in rowsA if r["task"] == t and r["condition"] == "baseline" and r["label"] in surv and r["passed"]]
        pool_forced = [r for r in rowsA if r["task"] == t and r["condition"].startswith("forced:") and
                       r["label"] == r["condition"].split(":")[1] and r["label"] in surv and r["passed"]]
        chosen = []
        per_mode_quota = {m: 0 for m in surv}
        quota = int(np.ceil(32 / len(surv)))
        for r in pool_nat + pool_forced:
            if len(chosen) >= 32:
                break
            if per_mode_quota[r["label"]] < quota:
                chosen.append(r)
                per_mode_quota[r["label"]] += 1
        progs = [(r, 1) for r in bx] + [(r, 0) for r in chosen]
        states = {l: [] for l in band}  # per program [T_i, D]
        tf_check = []
        for j in range(0, len(progs), 8):
            chunk = progs[j:j + 8]
            seqs, plens, glens = [], [], []
            for k, (r, _) in enumerate(chunk):
                bp = base_prompts[(j + k) % len(base_prompts)]
                gids = tok(r["raw_text"], add_special_tokens=False)["input_ids"][:GEN_T]
                tf_check.append(tok.decode(gids) == r["raw_text"][:len(tok.decode(gids))])
                seqs.append(bp["prompt_ids"] + gids)
                plens.append(len(bp["prompt_ids"]))
                glens.append(len(gids))
            ids, att = left_pad(seqs, "cuda")
            pos = (att.cumsum(-1) - 1).clamp(min=0)
            with torch.inference_mode():
                out = model.model(input_ids=ids, attention_mask=att, position_ids=pos, output_hidden_states=True,
                                  use_cache=False)
            Tm = ids.shape[1]
            for k in range(len(chunk)):
                # generated index t sits at absolute position (Tm - len(seq)) + plen + t
                st = Tm - len(seqs[k]) + plens[k]
                for l in band:
                    states[l].append(out.hidden_states[l + 1][k, st:st + glens[k]].float().cpu().numpy())
            del out
        is_x = np.array([lab for _, lab in progs]) == 1
        prog_modes = [r["label"] for r, _ in progs]
        auc_gen, auc_gen_dgen, use_dgen, d_gen = {}, {}, {}, {}
        m_gen, m_gen_pool, m_prompt = {}, {}, {}
        dropped = []
        for l in band:
            # per-t AUC of the R direction
            aucs = []
            for tt in range(GEN_T):
                pos_s = [s[tt] @ d_hat[l] for s, x in zip(states[l], is_x) if x and len(s) > tt]
                neg_s = [s[tt] @ d_hat[l] for s, x in zip(states[l], is_x) if (not x) and len(s) > tt]
                if len(pos_s) >= 5 and len(neg_s) >= 5:
                    aucs.append(auc(np.array(pos_s), np.array(neg_s)))
            auc_gen[l] = float(np.mean(aucs)) if aucs else float("nan")
            # d_X_gen by difference in means on half of the programs, AUC on the other half
            half = np.arange(len(progs)) % 2 == 0
            mean_vec = [s.mean(0) for s in states[l]]
            def dm(mask):
                a = np.mean([v for v, x, mk in zip(mean_vec, is_x, mask) if x and mk], 0)
                b = np.mean([v for v, x, mk in zip(mean_vec, is_x, mask) if (not x) and mk], 0)
                return unit(a - b)
            dg = dm(half)
            ps = [s[tt] @ dg for s, x, h in zip(states[l], is_x, half) if x and not h for tt in range(len(s))]
            ns = [s[tt] @ dg for s, x, h in zip(states[l], is_x, half) if (not x) and not h for tt in range(len(s))]
            auc_gen_dgen[l] = auc(np.array(ps), np.array(ns)) if ps and ns else float("nan")
            use_dgen[l] = bool(not (auc_gen[l] >= 0.9))
            d_gen[l] = dm(np.ones(len(progs), bool)) if use_dgen[l] else d_hat[l]
            # anchors at generated positions: equal weight per survivor mode, modes with < 5 programs dropped
            per_mode = {}
            for s, x, m in zip(states[l], is_x, prog_modes):
                if not x:
                    per_mode.setdefault(m, []).append(s)
            keep = {m: v for m, v in per_mode.items() if len(v) >= 5}
            for m in per_mode:
                if m not in keep:
                    dropped.append((l, m, len(per_mode[m])))
            if keep:
                mt = np.zeros((GEN_T, H[l].shape[1]), np.float32)
                for tt in range(GEN_T):
                    mm = [np.mean([s[tt] for s in v if len(s) > tt], 0) for v in keep.values()
                          if any(len(s) > tt for s in v)]
                    mt[tt] = np.mean(mm, 0) if mm else np.mean([np.concatenate(v).mean(0) for v in keep.values()], 0)
                m_gen[l] = mt
                m_gen_pool[l] = np.mean([np.concatenate(v).mean(0) for v in keep.values()], 0)
            # anchors at prompt positions: equal-weight mean over survivor modes of the suffix means
            li = CACHE_LAYERS.index(l)
            m_prompt[l] = np.mean([sm[m][li].astype(np.float32) for m in surv], 0)
        gen_variant = "affine" if len(m_gen) == len(band) else "plain_at_generated"
        if gen_variant != "affine":
            add_deviation(f"{t}: generated-position anchors had < 5 programs per survivor mode for some layers; "
                          "variant 'R-plus-prompt affine, plain at generated'.")
        if dropped:
            logger.info(f"{t}: dropped survivor modes for generated anchors: {dropped[:10]}")
        # random control directions: Gaussian, orthogonalised against d_hat and the 3 within-mode PCs, 2 seeds
        rnd = {}
        for sidx, seed in enumerate((101, 202)):
            rs = np.random.default_rng(seed)
            for l in band:
                v = rs.standard_normal(H[l].shape[1]).astype(np.float32)
                v = orth(v, [d_hat[l], d_gen[l]] + list(wpcs[l]))
                rnd[(sidx, l)] = unit(v)
        cos_ren = {}
        for l in band:
            Cl = centroids(H, index, t, l)
            c_bar = Cl.mean(0)
            u_ren = -unit(Cl[cat.index(X1)] - c_bar)
            cos_ren[l] = float(d_hat[l] @ -u_ren)
        np.savez(CACHE / f"directions_{t}.npz", band=np.array(band), d_hat=np.stack([d_hat[l] for l in band]),
                 d_gen=np.stack([d_gen[l] for l in band]), r1=np.stack([rnd[(0, l)] for l in band]),
                 r2=np.stack([rnd[(1, l)] for l in band]), wpcs=np.stack([wpcs[l] for l in band]))
        np.savez(CACHE / f"anchors_{t}.npz", band=np.array(band),
                 m_prompt=np.stack([m_prompt[l] for l in band]).astype(np.float32),
                 m_gen=np.stack([m_gen.get(l, np.zeros((GEN_T, H[l].shape[1]), np.float32)) for l in band]),
                 m_gen_pool=np.stack([m_gen_pool.get(l, np.zeros(H[l].shape[1], np.float32)) for l in band]),
                 has_gen=np.array([l in m_gen for l in band]))
        dirs.update({"modal": X1, "auc_R_heldout": auc_R, "auc_gen_Rdir": auc_gen, "auc_gen_dgen_heldout": auc_gen_dgen,
                     "use_dgen": use_dgen, "cos_dhat_neg_uren": cos_ren, "n_tf_programs": {"X": int(is_x.sum()),
                     "survivor": int((~is_x).sum()), "per_mode": dict(Counter(prog_modes))},
                     "teacher_forcing_retokenise_match": float(np.mean(tf_check)), "gen_anchor_variant": gen_variant})
        if any(v < 0.9 for v in auc_R.values()):
            add_deviation(f"{t}: d_X AUC at R below 0.9 for some band layers ({auc_R}); removal run anyway (flagged).")
        g["directions"] = dirs
        # ---------------------------------------------------------------- 7g decomposition basis for all X, all layers
        assoc = summA[t]["association"]
        pc_counts = {m: summA[t]["baseline_label_counts"].get(m, 0) for m in cat}
        basis_meta = {}
        B = np.zeros((len(cat), len(CACHE_LAYERS), 4, H[CACHE_LAYERS[0]].shape[1]), np.float32)
        Bgs = np.zeros_like(B)
        for xi, X in enumerate(cat):
            sv = [m for m in cat if m != X]
            alt = assoc[X]["borda_winner"]
            typ = max(sv, key=lambda m: (pc_counts[m], -cat.index(m)))
            dX = Dc[cat.index(X)]
            rel_c = sorted([m for m in sv if m not in (alt, typ)], key=lambda m: dX[cat.index(m)])
            rel = rel_c[0] if rel_c else None
            basis_meta[X] = {"alt": alt, "typ": typ if typ != alt else "n/a", "rel": rel}
            for li, l in enumerate(CACHE_LAYERS):
                Cl = centroids(H, index, t, l)
                c_bar = Cl.mean(0)
                cX = Cl[xi]
                m_other = np.mean([Cl[cat.index(m)] for m in sv], 0)
                u_ren = -unit(cX - c_bar)
                u_sub = unit(orth(Cl[cat.index(alt)] - m_other, [u_ren]))
                u_typ = unit(orth(Cl[cat.index(typ)] - m_other, [u_ren])) if typ != alt else np.zeros_like(u_ren)
                u_rel = unit(orth(Cl[cat.index(rel)] - m_other, [u_ren, u_sub] + ([u_typ] if typ != alt else []))) \
                    if rel else np.zeros_like(u_ren)
                B[xi, li] = np.stack([u_ren, u_sub, u_typ, u_rel])
                # Gram-Schmidt orthonormal version for squared-norm shares
                gs = []
                for v in (u_ren, u_sub, u_typ, u_rel):
                    if np.linalg.norm(v) < 1e-6:
                        gs.append(np.zeros_like(v))
                        continue
                    w = orth(v, [q for q in gs if np.linalg.norm(q) > 0])
                    gs.append(unit(w))
                Bgs[xi, li] = np.stack(gs)
        np.savez(CACHE / f"basis_{t}.npz", B=B, Bgs=Bgs, layers=np.array(CACHE_LAYERS))
        g["basis_meta"] = basis_meta
        geo_out[t] = g

        # ---------------------------------------------------------------- 7e nominations
        from sklearn.decomposition import PCA
        from sklearn.linear_model import LogisticRegression

        yN = np.array([cat.index(m) for m in labN])
        pca_l = PCA(min(50, len(iN) - 12), random_state=0).fit(Xn)
        probe = LogisticRegression(C=1.0, max_iter=3000).fit(pca_l.transform(Xn), yN)

        def decoder_dist(hmean):
            p = np.zeros(len(cat))
            p[probe.classes_] = probe.predict_proba(pca_l.transform(hmean[None]))[0]
            return p

        def mean_h(cond):
            ii = [i for i, r in enumerate(index) if r["task"] == t and r["condition"] == cond]
            return H[lstar][ii].astype(np.float32).mean(0) if ii else None

        strata = summA[t]["strata"]
        events = [("ban", [X1])] + [("ban", [m]) for m in cat if strata[m] == "present_minor"]
        events += [("ban", [X1, a]) for a in cat if a != X1]
        events += [("ban", [X1, a, b]) for a in cat for b in cat if len({X1, a, b}) == 3]
        events += [("removal", [X1])]
        base_lab = [r["label"] for r in rowsA if r["task"] == t and r["condition"] == "baseline" and r["label"] in cat]
        rng = np.random.default_rng(7)
        # bootstrap distributions for stability (shared across events)
        boot_counts = []
        for _ in range(1000):
            bs = rng.choice(len(base_lab), len(base_lab), replace=True)
            c = Counter(base_lab[i] for i in bs)
            boot_counts.append(np.array([c.get(m, 0) for m in cat], float))
        Pmode = {m: P[[k for k, mm in enumerate(labN) if mm == m]] for m in cat}
        boot_geo = []
        for _ in range(1000):
            Cb = np.stack([Pmode[m][rng.integers(0, len(Pmode[m]), len(Pmode[m]))].mean(0) for m in cat])
            Db = geodesic_between(G, P, Cb, 10)
            boot_geo.append((Db + Db.T) / 2)
        counts = np.array([Counter(base_lab).get(m, 0) for m in cat], float)
        # affine-ablated baseline h_R at l* (for the removal decoder nomination)
        hb = mean_h("baseline")
        if lstar in d_hat:
            mR = m_prompt[lstar][-1]
            hb_abl = hb - ((hb - mR) @ d_hat[lstar]) * d_hat[lstar]
        else:
            hb_abl = hb
        for kind, bset in events:
            S = [m for m in cat if m not in bset]
            Xk = bset[-1]
            sidx = [cat.index(m) for m in S]
            eid = f"{t}|{kind}:{'+'.join(bset)}"
            A = np.array([assoc[Xk]["borda_A"].get(m, 0.0) for m in S])
            A = A / A.sum()
            A1 = np.array([assoc[X1]["borda_A"].get(m, 0.0) if m != X1 else 0 for m in S])
            A1 = A1 / A1.sum() if A1.sum() > 0 else np.ones(len(S)) / len(S)
            Fq = (counts[sidx] + 1) / (counts[sidx] + 1).sum()
            Gk = softmax_neg(Dc[cat.index(Xk)][sidx], med)
            hm = hb_abl if kind == "removal" else mean_h(f"ban:{'+'.join(bset)}")
            Dd = decoder_dist(hm)[sidx] if hm is not None else np.ones(len(S))
            Dd = Dd / Dd.sum()
            dists = {"association": A, "association_X1": A1, "frequency": Fq, "geodesic": Gk, "decoder": Dd}
            top1 = {k: S[int(np.argmax(v))] for k, v in dists.items()}
            tied = {k: bool(len(v) > 1 and np.sort(v)[-1] - np.sort(v)[-2] < 1e-9) for k, v in dists.items()}
            # stability
            fq_top = [S[int(np.argmax(bc[sidx] + 1))] for bc in boot_counts]
            geo_top = [S[int(np.argmin(Db[cat.index(Xk)][sidx]))] for Db in boot_geo]
            srt_f = np.sort(Fq)[::-1]
            dgeo = np.sort(Dc[cat.index(Xk)][sidx])
            stab = {"frequency_share_same_top1": float(np.mean([x == top1["frequency"] for x in fq_top])),
                    "frequency_margin": float(srt_f[0] - srt_f[1]) if len(S) > 1 else 1.0,
                    "geodesic_share_same_nearest": float(np.mean([x == top1["geodesic"] for x in geo_top])),
                    "geodesic_margin": float(dgeo[1] - dgeo[0]) if len(S) > 1 else float("inf")}
            stab["frequency_stable"] = stab["frequency_share_same_top1"] >= 0.8
            stab["geodesic_stable"] = stab["geodesic_share_same_nearest"] >= 0.8
            if t == "t2" and summA[t]["modal_share_parseable"] >= 0.999:
                stab["frequency_stable"] = False
                stab["note"] = "T2 baseline ~100% modal: frequency nominations unstable by construction"
            preds["events"][eid] = {
                "task": t, "kind": kind, "banset": bset, "survivors": S, "X_k": Xk,
                "distributions": {k: dict(zip(S, map(float, v))) for k, v in dists.items()},
                "top1": top1, "top1_tied": tied, "concordance": {"AF": top1["association"] == top1["frequency"],
                                              "AG": top1["association"] == top1["geodesic"]},
                "stability": stab, "ambiguity_flag": assoc[Xk]["ambiguity_flag"]}
        logger.info(f"{t}: {sum(1 for e in preds['events'].values() if e['task'] == t)} events nominated")
        gc.collect()

    (ROOT / "results" / "geometry_b.json").write_text(json.dumps(geo_out, indent=1, default=str))
    # ---------------------------------------------------------------- COMMIT
    preds["created_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    pdir = ROOT / "predictions"
    pdir.mkdir(exist_ok=True)
    pf = pdir / "predictions_v1.json"
    pf.write_text(json.dumps(preds, indent=1))
    h = sha256_file(pf)
    append_jsonl(pdir / "commit_log.jsonl", [{"file": "predictions/predictions_v1.json", "sha256": h,
                                               "utc": preds["created_utc"], "unix": time.time(),
                                               "n_events": len(preds["events"])}])
    logger.info(f"COMMITTED predictions_v1.json sha256={h} ({len(preds['events'])} events)")
    logger.info(f"Phase B done in {(time.time() - t_all) / 60:.1f} min")


if __name__ == "__main__":
    main()
