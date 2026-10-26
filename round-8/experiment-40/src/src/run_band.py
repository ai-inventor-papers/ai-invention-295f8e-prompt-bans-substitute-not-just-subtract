#!/usr/bin/env python3
"""S7: task-band DAS on Qwen3-8B T10 (blocks 12-23, every spec position, ONE shared R), same map class, objective,
readout and early stopping as the decision site. Controls: c1 (random subspaces on a stratified 96-pair held-out
subsample), c2 (label-control refits), c4 (reverse), c5/c6 (pooled natural-variance basis over (block, spec
position), centred per (block, position) across twins), c7 (principal angles). U4: zero-rank identity and the band
full-state exchange identity check.

Usage: python src/run_band.py [--minutes 45]
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
from cfg8 import (CACHE, DATA, FAMILY, FIT_STEPS, LABEL_CONTROL_SEEDS, MAPS, RANDOM_SEED0, RANKS, RESULTS, THRESH,
                  add_deviation, read_json, setup_logging, write_json, write_jsonl)
from das8 import BandSite, ClassMap, haar, kl, orth, principal_cosines, project_map, variance_share
from engine8 import load_lm, prefill
from run_dec import fam_of, load_prompts


def stratified(pairs: list[tuple[str, str]], cls: dict[str, int], n: int, seed: int) -> list[tuple[str, str]]:
    rng = np.random.default_rng(seed)
    strata: dict[tuple, list] = {}
    for p in pairs:
        strata.setdefault((cls[p[0]], p[0]), []).append(p)
    keys = sorted(strata)
    out = []
    i = 0
    while len(out) < min(n, len(pairs)):
        k = keys[i % len(keys)]
        if strata[k]:
            out.append(strata[k].pop(int(rng.integers(len(strata[k])))))
        i += 1
        if i > 100000:
            break
    return out


def pooled_cov(site: BandSite, keys: list[str]) -> tuple[torch.Tensor, int]:
    """Sigma pooled over (block, spec position) after centring per (block, position) across prompts."""
    lm = site.lm
    D = lm.D
    S2 = torch.zeros(D, D, dtype=torch.float64, device=lm.dev)
    M = torch.zeros(len(site.band), site.n_spec, D, dtype=torch.float64, device=lm.dev)
    n = 0
    for k in keys:
        r = site.P[k]
        store, pre = site._capture(r["dec_ids"], r["p1"], site.band)
        X = torch.stack([store[l][:site.n_spec] for l in site.band]).double()       # [nb, S, D]
        M += X
        Xf = X.reshape(-1, D)
        S2 += Xf.T @ Xf
        n += 1
        del pre, store
    M /= n
    Mf = M.reshape(-1, D)
    S = (S2 - n * (Mf.T @ Mf)) / max(1, n * Mf.shape[0] - 1)
    return S.float(), n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=45)
    a = ap.parse_args()
    setup_logging("run_band_T10")
    out_p = RESULTS / "band_T10.json"
    if out_p.exists():
        logger.info("band_T10.json exists; skipping")
        return
    deadline = time.time() + a.minutes * 60
    unit = "T10"
    P = load_prompts(unit)
    s3 = read_json(RESULTS / f"s3_{unit}.json")
    classes = s3["classes"]
    cmap = ClassMap(classes, {c: s3["class_sets"][c] for c in classes})
    pairs = read_json(DATA / f"pairs_{unit}.json")
    q_tr = torch.load(CACHE / f"q_{unit}_dec_trained.pt")
    cls = {k: int(v[:len(classes)].argmax()) for k, v in q_tr.items()}
    train = [tuple(p) for p in pairs["train"]]
    held = [tuple(p) for p in pairs["held"]]
    lm = load_lm("qwen")
    band = list(FAMILY["qwen"]["band"])
    held96 = stratified(held, cls, 96, 0)
    fams_tr = sorted({fam_of(P[s]) for s in pairs["sources_train"]})
    # train subsample (band steps are costly; pairs are sampled per step anyway)
    base_keys = sorted({b for _, b in train} | {b for _, b in held96})
    src_keys = sorted({s for s, _ in train} | {s for s, _ in held96})
    rev_rows = []
    for s in pairs["sources_held"]:
        tw = P[s]["key"].replace("|forced|", "|padtwin|")
        if tw in P and cls[tw] != cls[s]:
            rev_rows.append((tw, s))
    site = BandSite(lm, P, cmap, tuple(band), base_keys + [s for _, s in rev_rows],
                    src_keys + [t for t, _ in rev_rows], cls)
    res: dict[str, Any] = {"unit": unit, "band": band, "n_train_pairs": len(train), "n_held_subsample": len(held96)}
    # ---- U4: zero-rank identity and full-state identity check
    t0 = time.time()
    with torch.no_grad():
        b0 = held96[0][1]
        lg_none = site.forward([held96[0]], "none")[0]
        lg_full = prefill(lm, P[b0]["dec_ids"])["logits"]
        u4a = float((cmap.lp(lg_none) - cmap.lp(lg_full)).abs().max())
    t_fwd = time.time() - t0
    full96 = site.evaluate(held96, None)
    m0_96 = site.base_margins(held96)
    d_full96 = full96["m"] - m0_96
    flip = float(np.mean(np.array([int(np.argmax(q[:len(classes)])) == cls[p[0]] for q, p in zip(full96["q"], held96)])))
    res["U4"] = {"zero_rank_vs_full_recompute_max_abs_logP_class": u4a,
                 "full_state_flip_to_source_class_share_held96": flip,
                 "pass_flip_0.9": bool(flip >= 0.9), "mean_delta_full": float(d_full96.mean())}
    logger.info(f"U4: {res['U4']}")
    # ---- timing probe
    t0 = time.time()
    f_probe = site.fit(train, held96[:16], seed=99, q_tgt=q_tr, steps=3, val_every=1000, log_name="probe")
    sec_step = (time.time() - t0) / 3
    t0 = time.time()
    site.evaluate(held96[:16], f_probe["R"][:, :1])
    sec_eval16 = time.time() - t0
    remaining = deadline - time.time()
    # budget: main fits (2-3) + c2 (3) + c1 + c4/c5/c6
    per_fit = FIT_STEPS * sec_step + (FIT_STEPS / 20) * 4 * sec_eval16 * 3
    logger.info(f"band timing: {sec_step:.2f}s/step, eval16 {sec_eval16:.2f}s; est per fit {per_fit / 60:.1f} min; "
                f"remaining {remaining / 60:.1f} min")
    steps = FIT_STEPS
    n_fits = 5
    if per_fit * n_fits > 0.75 * remaining:
        steps = max(60, int(FIT_STEPS * (0.75 * remaining / n_fits) / per_fit))
        add_deviation("band_steps", f"band fits run {steps} steps (timing {sec_step:.2f} s/step; same budget for every "
                                    f"band fit, controls included)")
    res["timing"] = {"sec_per_step": sec_step, "sec_eval16": sec_eval16, "steps": steps}
    # ---- main fits
    fits = {}
    for sd in (0, 1):
        vf = fams_tr[sd % len(fams_tr)]
        tp = [p for p in train if fam_of(P[p[0]]) != vf]
        vp = stratified([p for p in train if fam_of(P[p[0]]) == vf], cls, 32, sd)
        fits[sd] = site.fit(tp, vp, seed=sd, q_tgt=q_tr, steps=steps, log_name=f"band s{sd}", deadline=deadline)
        torch.save(fits[sd]["R"], MAPS / f"T10_band_seed{sd}.pt")
    rec_rank = {}
    tf_rows = []
    for sd, f in fits.items():
        for k in RANKS:
            ev = site.evaluate(held96, f["R"][:, :k])
            d = ev["m"] - m0_96
            r = ST.recovery(d, d_full96, [p[0] for p in held96], [p[1] for p in held96], seed=sd)
            if sd == 0:
                bc = {}
                for ci, c in enumerate(classes):
                    ix = [i for i, p in enumerate(held96) if cls[p[0]] == ci]
                    if ix:
                        bc[c] = ST.recovery(d[ix], d_full96[ix], [held96[i][0] for i in ix],
                                            [held96[i][1] for i in ix], n_boot=500)
                rec_rank[k] = {**r, "by_class": bc}
            else:
                rec_rank.setdefault(f"seed{sd}", {})[k] = r
            for i, p in enumerate(held96):
                tf_rows.append({"unit": unit, "site": "band", "fit": f"seed{sd}", "rank_k": k, "src": p[0],
                                "base": p[1], "class_src": classes[cls[p[0]]], "class_base": classes[cls[p[1]]],
                                "delta": float(d[i]), "delta_full": float(d_full96[i])})
    best = max(RANKS, key=lambda k: rec_rank[k]["recovery"] or -9)
    kstar = min(k for k in RANKS if (rec_rank[k]["recovery"] or -9) >= 0.9 * rec_rank[best]["recovery"])
    R0 = fits[0]["R"]
    Rk = R0[:, :kstar]
    main_r = rec_rank[kstar]
    logger.info(f"band k* = {kstar}; recovery {main_r['recovery']}")
    res.update({"k_star": kstar, "recovery_by_rank": rec_rank, "main": main_r,
                "off_manifold_flag": bool(main_r["recovery"] and main_r["recovery"] > 1.5),
                "fits": {str(s): {k: v for k, v in f.items() if k not in ("R", "hist")} for s, f in fits.items()}})
    write_json(RESULTS / "band_T10_partial.json", res)
    # ---- c2 label controls
    C = len(classes)
    srcs = sorted({s for s, _ in train})
    cmean = {c: torch.stack([q_tr[s] for s in srcs if cls[s] == c]).mean(0) for c in range(C)
             if any(cls[s] == c for s in srcs)}
    perms = [("pi1", {c: (c + 1) % C for c in range(C)}), ("pi2", {c: (c + 2) % C for c in range(C)})] if C >= 3 else []
    plab = {}
    for i, s in enumerate(sorted(srcs, key=lambda x: (cls[x], x))):
        others = [c for c in range(C) if c != cls[s] and c in cmean]
        plab[s] = others[i % len(others)]
    perms.append(("prompt", plab))
    c2: dict[str, Any] = {}
    for (name, pm), sd in zip(perms, LABEL_CONTROL_SEEDS):
        if time.time() > deadline - 300:
            add_deviation("band_c2_time", f"band c2 refit {name} not run (time)")
            continue

        def pt(s: str) -> int:
            return pm[s] if name == "prompt" else pm[cls[s]]
        tr = [p for p in train if pt(p[0]) != cls[p[1]] and pt(p[0]) in cmean]
        ptg = {p: cmean[pt(p[0])] for p in tr}
        vf = fams_tr[sd % len(fams_tr)]
        tp = [p for p in tr if fam_of(P[p[0]]) != vf]
        vp = [p for p in tr if fam_of(P[p[0]]) == vf][:32]
        f = site.fit(tp, vp, seed=sd, q_tgt=q_tr, pair_targets=ptg, steps=steps, log_name=f"band c2 {name}",
                     deadline=deadline)
        torch.save(f["R"], MAPS / f"T10_band_perm_{name}.pt")
        ev = site.evaluate(held96, f["R"][:, :kstar])
        d = ev["m"] - m0_96
        r = ST.recovery(d, d_full96, [p[0] for p in held96], [p[1] for p in held96])
        ratio = (r["recovery"] / main_r["recovery"]) if (main_r["recovery"] and r["recovery"] is not None) else None
        c2[name] = {"heldout_recovery_toward_true_class": r, "ratio_to_true_fit": ratio,
                    "pass": bool(ratio is not None and ratio <= THRESH["c2_ratio_max"]),
                    "fit": {k: v for k, v in f.items() if k not in ("R", "hist")}}
        logger.info(f"band c2 {name}: ratio {ratio}")
    c2["pass"] = bool(c2 and all(v["pass"] for k, v in c2.items() if isinstance(v, dict) and "pass" in v))
    res["c2"] = c2
    # ---- c1 random subspaces (stratified held96)
    c1 = {}
    for k in RANKS:
        n_r = 50 if k in (kstar, 1) else 10
        if time.time() > deadline - 240:
            n_r = min(n_r, 10)
        vals = []
        for i in range(n_r):
            ev = site.evaluate(held96, haar(RANDOM_SEED0 + i, lm.D, k).to(lm.dev))
            r = ST.recovery(ev["m"] - m0_96, d_full96, [p[0] for p in held96], [p[1] for p in held96], n_boot=10)
            vals.append(r["recovery"])
        vals = np.array([v for v in vals if v is not None])
        c1[k] = {"median": float(np.median(vals)), "p95": float(np.percentile(vals, 95)), "max": float(vals.max()),
                 "n": int(len(vals)), "pass": bool(np.median(vals) <= THRESH["c1_median_max"])}
        logger.info(f"band c1 k{k}: {c1[k]}")
    res["c1"] = c1
    # ---- c4 reverse
    if rev_rows:
        fr = site.evaluate(rev_rows, None)
        m0r = site.base_margins(rev_rows)
        dr = site.evaluate(rev_rows, Rk)
        r4 = ST.recovery(dr["m"] - m0r, fr["m"] - m0r, [a for a, _ in rev_rows], [b for _, b in rev_rows],
                         min_full=0.0)
        r4["pass"] = bool(r4["recovery"] is not None and r4["recovery"] >= THRESH["c4_min"])
        r4["n_pairs"] = len(rev_rows)
        res["c4"] = r4
    else:
        res["c4"] = {"n_pairs": 0, "pass": False}
    # ---- c5 / c6 pooled natural basis
    twins = [k for k, r in P.items() if r["kind"] == "twin"]
    S_tw, n_tw = pooled_cov(site, twins)
    extra = [k for k, r in P.items() if r["kind"] in ("forced", "ban", "seed_rand1", "seed_rand2", "instr_new",
                                                       "instr_novel", "p0")]
    S_b, n_b = pooled_cov(site, twins + extra)
    c5, c6 = {}, {}
    for tag, S, n in (("twins", S_tw, n_tw), ("twins_forced_bans", S_b, n_b)):
        ev_, U = torch.linalg.eigh(S.double().cpu())
        U64 = U[:, torch.argsort(ev_, descending=True)[:64]].float()
        Rp = project_map(Rk, U64)
        if Rp is None:
            c5[tag] = {"retention": 0.0, "note": "projection lost rank"}
        else:
            ev = site.evaluate(held96, Rp)
            r = ST.recovery(ev["m"] - m0_96, d_full96, [p[0] for p in held96], [p[1] for p in held96])
            c5[tag] = {"recovery_proj": r["recovery"], "retention": (r["recovery"] or 0) / main_r["recovery"]
                       if main_r["recovery"] else None, "n_prompts": n}
        share = variance_share(Rk, S.cpu())
        rs = np.array([variance_share(haar(50000 + i, lm.D, kstar), S.cpu()) for i in range(1000)])
        c6[tag] = {"share": share, "random_p95": float(np.percentile(rs, 95)), "random_median": float(np.median(rs)),
                   "percentile": float((rs < share).mean() * 100), "pass": bool(share > np.percentile(rs, 95)),
                   "n_prompts": n}
    c5["pass"] = bool((c5["twins"].get("retention") or 0) >= THRESH["c5_min"])
    c5["pass_b"] = bool((c5["twins_forced_bans"].get("retention") or 0) >= THRESH["c5_min"])
    res["c5"], res["c6"] = c5, c6
    torch.save(S_tw.cpu(), CACHE / "band_T10_sigma_twins.pt")
    # ---- c7
    cos = [float(principal_cosines(fits[0]["R"][:, :kstar], fits[1]["R"][:, :kstar])[0])]
    rnd = [float(principal_cosines(haar(60000 + i, lm.D, kstar), haar(61000 + i, lm.D, kstar))[0]) for i in range(1000)]
    res["c7"] = {"first_cosines": cos, "median_first_cosine": float(np.median(cos)),
                 "random_p99": float(np.percentile(rnd, 99)),
                 "pass": bool(np.median(cos) >= THRESH["c7_cos_min"] and np.median(cos) > np.percentile(rnd, 99)),
                 "note": "2 seeds (seed 2 dropped by the 2:25 checkpoint rule)"}
    # ---- principal angles with the iteration-7 handle
    try:
        old = torch.load(Path(__file__).resolve().parents[1] / "inputs" / "exp33" / "T10_MAIN_LY.pt",
                         map_location="cpu")
        Wold = old["basis"] if isinstance(old, dict) and "basis" in old else old
        if isinstance(Wold, dict):
            Wold = next(v for v in Wold.values() if isinstance(v, torch.Tensor))
        Wold = Wold.float()
        if Wold.shape[0] != lm.D:
            Wold = Wold.T
        res["iter7_handle_first_cosines"] = {k: float(principal_cosines(orth(Wold[:, :k]), Rk)[0]) for k in (1, 2, 4)
                                             if k <= Wold.shape[1]}
    except (FileNotFoundError, RuntimeError, KeyError, StopIteration, AttributeError) as e:
        res["iter7_handle_first_cosines"] = {"error": str(e)}
    write_jsonl(DATA / "tf_T10_band.jsonl", tf_rows)
    write_json(out_p, res)
    logger.info("band done")
    site.free()
    lm.free()


if __name__ == "__main__":
    main()
