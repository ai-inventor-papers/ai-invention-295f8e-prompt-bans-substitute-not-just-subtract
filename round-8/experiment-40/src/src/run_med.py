#!/usr/bin/env python3
"""S10 mediation (Qwen3-8B T10): do iteration 4's 40 random pushes act through the fitted T10 task-band subspace?

1. Realised displacement D_u(l, p) = h_push - h_twin of each direction (alpha 2, absolute unit n[l, p] = exp13
   norms_T10 'norm', blocks 12-23, spec positions, prefill only, iteration 4's displacement-targeted edit) on the five
   iteration-7 n0 twins (W1-W5, noun 'ship'); cross-check against exp34's dbar_T10.npz.
2. Predictor (computed before any outcome file is opened): z_u = mean_(w,l,p) R^T D_u; g_c = mean over forced-c prompts
   of mean_(l,p) R^T (h_c - h_twin); pi_u = max_c <z_u, g_c> / ||g_c||^2 -> COMMIT #3 (with the top-10 list).
3. Outcome = correct off-default share of the direction's POP_d<seed>_a2.0 programs (art_lpQalcAXMGr1 engine-d rows;
   engine-c rows reported alone and pooled). Spearman(pi, escape) and partial Spearman controlling ||D_u||.
4. CLAMP on the 10 most-escaping directions (N = 30 CRN slots): PUSH, PUSH + TASK-CLAMP (h <- h - R R^T (h - h_twin)
   at every band block, rank k*), PUSH + RAND-CLAMP (equal-rank Haar subspaces, 3 seeds rotating over directions),
   PUSH + DEC-CLAMP (N = 10; the twin's decision-site coordinates written at d at L* once generation has reproduced
   the canonical opening through token 10; reach rate reported).
5. PROSPECTIVE: 24 new directions (seeds 98001-98024, exp22 generator) -> pi_u -> COMMIT #4 -> PUSH-only N = 10.

Usage: python src/run_med.py [--minutes 30]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import torch
from loguru import logger

import stats8 as ST
from cfg8 import (CACHE, DATA, FAMILY, INPUTS, MAPS, OPEN_T10, PROSPECTIVE_SEEDS, RESULTS, ROOT, UNITS, add_deviation,
                  read_json, read_jsonl, setup_logging, sha256_file, u_stream, write_json)
from commit8 import commit
from das8 import haar
from engine8 import decode, load_lm, prefill
from gen8 import done_ids, push_clamp_edit, run_rows
from run_dec import load_prompts

ALPHA = 2.0
SEEDS40 = list(range(9101, 9141))
OFF = ("bfs", "dfs", "label_propagation")


def direction(seed: int) -> np.ndarray:
    f = INPUTS / "exp22" / "directions" / f"rand_{seed}.npy"
    if f.exists():
        return np.load(f).astype(np.float32)
    x = np.random.Generator(np.random.PCG64(seed)).standard_normal(4096)
    return (x / np.linalg.norm(x)).astype(np.float32)


def capture_band(lm: Any, ids: list[int], p1: int, S: int, blocks: list[int], edits: dict | None = None,
                 post: dict | None = None) -> dict[int, torch.Tensor]:
    """Block outputs at spec positions AFTER any edit at that block (edits wrapped to record their output)."""
    store: dict[int, torch.Tensor] = {}
    wrapped = {}
    for l in blocks:
        f = (edits or {}).get(l)

        def mk(l: int, f: Any) -> Any:
            def g(h: torch.Tensor) -> torch.Tensor:
                h2 = f(h) if f is not None else h
                store[l] = h2[0, p1:p1 + S].float().clone()
                return h2
            return g
        wrapped[l] = mk(l, f)
    prefill(lm, ids, edits=wrapped)
    return store


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=30)
    ap.add_argument("--n_clamp", type=int, default=30)
    a = ap.parse_args()
    setup_logging("run_med_T10")
    deadline = time.time() + a.minutes * 60
    out_p = RESULTS / "mediation_T10.json"
    unit = "T10"
    P = load_prompts(unit)
    band = read_json(RESULTS / "band_T10.json")
    dec = read_json(RESULTS / "dec_T10.json")
    kb = band["k_star"]
    Rb = torch.load(MAPS / "T10_band_seed0.pt")[:, :kb]
    L, kd = dec["L_star"], dec["k_star"]
    Rd = torch.load(MAPS / f"T10_dec_L{L}_seed0.pt")[:, :kd]
    s3 = read_json(RESULTS / f"s3_{unit}.json")
    classes = s3["classes"]
    bl = list(FAMILY["qwen"]["band"])
    twins = [f"T10|twin|W{i}|ship" for i in range(1, 6)]
    S = P[twins[0]]["spec_end"] - P[twins[0]]["p1"]
    norms = np.load(INPUTS / "exp13" / "norms_T10.npz")["norm"].astype(np.float32)
    assert norms.shape == (len(bl), S), (norms.shape, S)
    n_t = torch.tensor(norms)
    lm = load_lm("qwen")
    res: dict[str, Any] = {"unit": unit, "alpha": ALPHA, "k_star_band": kb, "L_star": L, "k_star_dec": kd}
    # ---- clean twin states (band + block 35) and forced-class centroids
    blocks_cap = bl + [lm.N - 1]
    clean = {w: capture_band(lm, P[w]["ids"], P[w]["p1"], S, blocks_cap) for w in twins}
    h_tw_mean = {l: torch.stack([clean[w][l] for w in twins]).mean(0) for l in bl}
    twin_ht = {w: torch.stack([clean[w][l] for l in bl]) for w in twins}      # one copy per twin (shared by all rows)
    g = {}
    for c in ("bfs", "dfs"):
        fk = [k for k, r in P.items() if r["kind"] == "forced" and r["Y"] == c]
        acc = []
        for k in fk:
            st = capture_band(lm, P[k]["ids"], P[k]["p1"], S, bl)
            acc.append(torch.stack([(st[l] - h_tw_mean[l]).mean(0) for l in bl]).mean(0))
        g[c] = (torch.stack(acc).mean(0) @ Rb.to(lm.dev))                                   # [kb]
    # ---- realised displacement and predictor for the 40 directions (+ 24 prospective)
    def predictor(seed: int) -> dict[str, Any]:
        u = torch.tensor(direction(seed))
        zs, nb, n35 = [], [], []
        for w in twins:
            ed = push_clamp_edit(bl, P[w]["p1"], S, u, ALPHA, n_t, twin_ht[w], None)
            st = capture_band(lm, P[w]["ids"], P[w]["p1"], S, blocks_cap, edits=ed)
            D = torch.stack([st[l] - clean[w][l] for l in bl])                                # [nb, S, D]
            zs.append((D.mean((0, 1)) @ Rb.to(lm.dev)))
            nb.append(float(D.norm(dim=-1).mean()))
            n35.append(float((st[lm.N - 1] - clean[w][lm.N - 1]).norm(dim=-1).mean()))
        z = torch.stack(zs).mean(0)
        pis = {c: float((z @ g[c]) / (g[c] @ g[c])) for c in g}
        return {"seed": seed, "pi": max(pis.values()), "pi_by_class": pis, "norm_D_band": float(np.mean(nb)),
                "norm_D_block35": float(np.mean(n35)), "z_norm": float(z.norm())}
    t0 = time.time()
    pred = {s: predictor(s) for s in SEEDS40}
    logger.info(f"predictor for 40 directions in {time.time() - t0:.0f}s")
    # cross-check with exp34 dbar_T10.npz (mean displacement), where shapes match
    try:
        z = np.load(INPUTS / "exp34" / "dbar_T10.npz")
        res["dbar_crosscheck_keys"] = list(z.files)[:10]
    except (FileNotFoundError, OSError) as e:
        res["dbar_crosscheck_keys"] = f"unavailable: {e}"
    # ---- outcomes (opened only after the predictor exists): which directions escape most
    labs = read_jsonl(INPUTS / "exp29" / "labels.jsonl")
    esc: dict[str, dict[int, list[int]]] = {"d": {}, "c": {}}
    for r in labs:
        if r.get("task") != "T10" or not str(r.get("arm", "")).startswith("POP_d"):
            continue
        sd = int(r["arm"].split("_d")[1].split("_")[0])
        e = r.get("engine")
        if e not in esc:
            continue
        ok = str(r.get("passed")) == "True" and r.get("label") in OFF
        esc[e].setdefault(sd, []).append(int(ok))
    y = {}
    for sd in SEEDS40:
        vd, vc = esc["d"].get(sd, []), esc["c"].get(sd, [])
        y[sd] = {"escape_d": float(np.mean(vd)) if vd else None, "escape_c": float(np.mean(vc)) if vc else None,
                 "escape_pooled": float(np.mean(vd + vc)) if (vd or vc) else None, "n_d": len(vd), "n_c": len(vc)}
    have = [s for s in SEEDS40 if y[s]["escape_pooled"] is not None]
    top10 = sorted(have, key=lambda s: -y[s]["escape_pooled"])[:10]
    commit("commit3_mediation", {"pi": {str(s): pred[s] for s in SEEDS40}, "top10_escaping": top10,
                                 "code_sha256": sha256_file(Path(__file__)),
                                 "note": "pi computed from activations only; outcomes read afterwards"})
    for s in SEEDS40:
        pred[s].update(y[s])
    xs = np.array([pred[s]["pi"] for s in have])
    for key in ("escape_pooled", "escape_d", "escape_c"):
        hv = [s for s in have if pred[s][key] is not None]
        ys = np.array([pred[s][key] for s in hv])
        xv = np.array([pred[s]["pi"] for s in hv])
        res[f"spearman_{key}"] = ST.spearman_perm(xv, ys)
    ys = np.array([pred[s]["escape_pooled"] for s in have])
    res["partial_spearman_ctrl_normD_band"] = ST.partial_spearman(xs, ys, np.array([pred[s]["norm_D_band"] for s in have]))
    res["partial_spearman_ctrl_normD_block35"] = ST.partial_spearman(xs, ys,
                                                                     np.array([pred[s]["norm_D_block35"] for s in have]))
    for c in ("bfs", "dfs"):
        res[f"spearman_pi_{c}"] = ST.spearman_perm(np.array([pred[s]["pi_by_class"][c] for s in have]), ys, n_perm=2000)
    res["placebo_random_predictor"] = ST.spearman_perm(np.random.default_rng(5).permutation(xs), ys, n_perm=2000)
    res["directions"] = {str(s): pred[s] for s in SEEDS40}
    res["top10_escaping"] = top10
    write_json(out_p, res)
    logger.info(f"mediation Spearman pooled: {res['spearman_escape_pooled']}")
    # ---- CLAMP generation
    fence = UNITS[unit]["fence"]
    rows = []
    rand_cl = [haar(80000 + i, lm.D, kb) for i in range(3)]
    for j, sd in enumerate(top10):
        u = torch.tensor(direction(sd))
        for s in range(a.n_clamp):
            w = twins[s % 5]
            ht = twin_ht[w]
            for arm, cl in (("PUSH", None), ("TASK", Rb), ("RAND", rand_cl[j % 3])):
                ed = push_clamp_edit(bl, P[w]["p1"], S, u, ALPHA, n_t, ht, cl)
                rows.append({"sample_id": f"T10|med|{arm}|{sd}|{s}", "ids": P[w]["ids"], "edits": ed,
                             "ukey": (unit, "med", "iter8", s), "prefix_ids": [], "max_new": 512,
                             "meta": {"unit": unit, "site": "mediation", "cell": f"med|{arm}", "arm": arm,
                                      "direction_seed": sd, "slot": s, "base_key": w, "edit": arm.lower(),
                                      "rank_k": kb if arm != "PUSH" else None}})
    rows.sort(key=lambda r: (r["meta"]["slot"], r["meta"]["arm"]))
    run_rows(lm, unit, rows, fence, 16, "med-clamp", deadline - 8 * 60)
    # ---- DEC-CLAMP (N = 10): continue PUSH rows that reproduced the canonical opening, clamped at d at L*
    samples = {r["sample_id"]: r for r in read_jsonl(DATA / f"samples_{unit}.jsonl")}
    tok = lm.tok
    dec_rows, reach = [], {}
    from engine8 import states_at
    hdec = {w: states_at(lm, [P[w]["dec_ids"]], blocks=[L])["h"][0][0] for w in twins}
    for sd in top10:
        for s in range(10):
            pr = samples.get(f"T10|med|PUSH|{sd}|{s}")
            if pr is None:
                continue
            ids_gen = tok(pr["text"], add_special_tokens=False)["input_ids"]
            ok = ids_gen[:len(OPEN_T10)] == OPEN_T10
            reach[f"{sd}|{s}"] = bool(ok)
            if ok:
                dec_rows.append((sd, s))
    res["dec_clamp_reach_rate"] = float(np.mean(list(reach.values()))) if reach else None
    done = done_ids(unit)
    n_dec = 0
    for i in range(0, len(dec_rows), 16):
        if time.time() > deadline - 4 * 60:
            add_deviation("dec_clamp_time", "DEC-CLAMP rows cut by the time budget")
            break
        chunk = [x for x in dec_rows[i:i + 16] if f"T10|med|DEC|{x[0]}|{x[1]}" not in done]
        if not chunk:
            continue
        pres, us, metas = [], [], []
        for sd, s in chunk:
            w = twins[s % 5]
            u = torch.tensor(direction(sd))
            ed = push_clamp_edit(bl, P[w]["p1"], S, u, ALPHA, n_t, twin_ht[w], None)
            hd = hdec[w].to(lm.dev)
            Rdd = Rd.to(lm.dev)

            def dclamp(h: torch.Tensor, hd: torch.Tensor = hd) -> torch.Tensor:
                h = h.clone()
                x = h[:, -1].float()
                h[:, -1] = (x - ((x - hd) @ Rdd) @ Rdd.T).to(h.dtype)
                return h
            ed[L] = dclamp if L not in ed else (lambda h, f1=ed[L], f2=dclamp: f2(f1(h)))
            pres.append(prefill(lm, P[w]["ids"] + OPEN_T10, edits=ed))
            us.append(u_stream(unit, "med", "iter8", s, n=1536)[len(OPEN_T10):])
            metas.append((sd, s, w))
        P0 = [p["P"] for p in pres]
        groups: dict[int, list[int]] = {}
        for k, p in enumerate(P0):
            groups.setdefault(p, []).append(k)
        out = []
        for _, ix in groups.items():
            rr = decode(lm, [pres[k] for k in ix], [us[k] for k in ix], 512, fence)
            for k, o in zip(ix, rr):
                sd, s, w = metas[k]
                text = tok.decode(OPEN_T10 + [t for t in o["token_ids"] if t < len(tok)], skip_special_tokens=True)
                out.append({"sample_id": f"T10|med|DEC|{sd}|{s}", "unit": unit, "text": text, "site": "mediation",
                            "cell": "med|DEC", "arm": "DEC", "direction_seed": sd, "slot": s, "base_key": w,
                            "edit": "dec_clamp", "n_new_tokens": o["n_tokens"], "finish_reason": o["finish_reason"]})
        from cfg8 import append_jsonl
        append_jsonl(DATA / f"samples_{unit}.jsonl", out)
        done.update(o["sample_id"] for o in out)
        n_dec += len(out)
    res["n_dec_clamp_rows"] = n_dec
    # ---- PROSPECTIVE
    used = {int(f.stem.split("_")[1]) for f in (INPUTS / "exp22" / "directions").glob("rand_*.npy")}
    assert not (set(PROSPECTIVE_SEEDS) & used), "prospective seeds collide with earlier directions"
    ppred = {s: predictor(s) for s in PROSPECTIVE_SEEDS}
    commit("commit4_prospective", {"pi": {str(s): ppred[s] for s in PROSPECTIVE_SEEDS},
                                   "generator": "u = x / ||x||, x ~ N(0, I_4096) from PCG64(seed) (exp22; replicated "
                                                "exactly on rand_9101.npy)"})
    prow = []
    for sd in PROSPECTIVE_SEEDS:
        u = torch.tensor(direction(sd))
        for s in range(10):
            w = twins[s % 5]
            ed = push_clamp_edit(bl, P[w]["p1"], S, u, ALPHA, n_t, twin_ht[w], None)
            prow.append({"sample_id": f"T10|pro|PUSH|{sd}|{s}", "ids": P[w]["ids"], "edits": ed,
                         "ukey": (unit, "med", "iter8", s), "prefix_ids": [], "max_new": 512,
                         "meta": {"unit": unit, "site": "prospective", "cell": "pro|PUSH", "arm": "PUSH",
                                  "direction_seed": sd, "slot": s, "base_key": w, "edit": "push"}})
    run_rows(lm, unit, prow, fence, 16, "prospective", deadline)
    res["prospective_pi"] = {str(s): ppred[s] for s in PROSPECTIVE_SEEDS}
    res["clamp_reach"] = reach
    write_json(out_p, res)
    (RESULTS / "gen_done_T10.flag").write_text("done")
    lm.free()
    logger.info("mediation done")


if __name__ == "__main__":
    main()
