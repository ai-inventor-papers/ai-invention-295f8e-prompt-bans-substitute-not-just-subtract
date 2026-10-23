#!/usr/bin/env python3
"""Decision-site stages for one unit (T10 on Qwen3-8B, GRID on gemma-3-4b-it), trained network:

S3  teacher-force every prompt with the opening prefilled -> class distribution at d, top-50 tokens; token map
    (iteration-7 maps + forced-token continuations for unmapped tokens with >= 2% mass); adherence for classes
    without an iteration-7 record; class list; pairs (commit #1).
S4  state cache at d (all blocks) + base keys/values (DecSite).
U   unit tests U1-U3 (KV path), U9 (mini-fit).
S6  scan (every 2nd block, rank 1, 2-fold leave-family-out CV, 100 steps) -> L*; main fits (3 seeds) + rank-1-only
    fit; k*; controls c1 (50 Haar subspaces / rank), c2 (3 label-control refits), c4 (reverse), c5/c5b (projection on
    natural PCs), c6/c6b (variance share), c7 (principal angles); baselines DiM-1, PCA-k, logit lens.

Usage: python src/run_dec.py --unit T10|GRID [--quick]
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import torch
from loguru import logger

import stats8 as ST
from cfg8 import (BATCH_DEC, DATA, FIT_SEEDS, FIT_STEPS, HELD_PAIR_CAP, INPUTS, LABEL_CONTROL_SEEDS, LR, MAPS,
                  N_RANDOM_SUBSPACES, OFF_MANIFOLD, PROMPTS_DIR, RANDOM_SEED0, RANKS, RESULTS, SCAN_STEPS, THRESH,
                  TRAIN_PAIR_CAP, UNITS, add_deviation, append_jsonl, read_json, read_jsonl, set_ram_limit,
                  setup_logging, u_stream, write_json, write_jsonl)
from commit8 import commit, committed
from das8 import ClassMap, DecSite, haar, kl, orth, pca_basis, principal_cosines, project_map, variance_share
from engine8 import decode, load_lm, prefill, states_at

T10_MAP0 = {66564: "bfs", 25792: "dfs", 1477: "union_find", 11300: "union_find"}
GRID_MAP0 = {107: "bfs", 584: "bfs", 15204: "bfs", 236809: "bfs", 53227: "dfs"}
FAM_KEY = {"T10": "fam", "GRID": "fam"}


def load_prompts(unit: str) -> dict[str, dict[str, Any]]:
    f = PROMPTS_DIR / ("t10_prompts.jsonl" if unit == "T10" else "grid_prompts.jsonl")
    return {r["key"]: r for r in read_jsonl(f)}


def fam_of(r: dict[str, Any]) -> int:
    f = r.get("fam")
    return int(f[1:]) - 1 if isinstance(f, str) else int(f)


# ================================================================================================ S3
def gen_continuations(lm: Any, ids: list[int], n: int, max_new: int, fence: str, key: tuple) -> list[list[int]]:
    pre = prefill(lm, ids)
    us = [u_stream(*key, s) for s in range(n)]
    res = decode(lm, [pre] * n, us, max_new, fence)
    del pre
    return [r["token_ids"] for r in res]


def labeller(unit: str):
    import label8 as L8

    L8.setup_paths(unit)
    return lambda text: L8.label_text(unit, text)


def stage_s3(unit: str, lm: Any, P: dict[str, dict[str, Any]], quick: bool) -> dict[str, Any]:
    out_p = RESULTS / f"s3_{unit}.json"
    if out_p.exists():
        return read_json(out_p)
    U = UNITS[unit]
    t0 = time.time()
    keys = list(P)
    st = states_at(lm, [P[k]["dec_ids"] for k in keys], blocks=[lm.N - 1])
    lg = st["logits"]
    probs = torch.softmax(lg.float(), -1)
    top = torch.topk(probs, 50, -1)
    tf = {k: {"top_ids": top.indices[i].tolist(), "top_p": [round(float(x), 5) for x in top.values[i]]}
          for i, k in enumerate(keys)}
    map0 = dict(T10_MAP0 if unit == "T10" else GRID_MAP0)
    # candidate classes: T10 bfs/dfs/union_find; GRID bfs/dfs + astar_gbfs/iddfs (if adherent)
    modes = ["bfs", "dfs", "union_find"] if unit == "T10" else ["bfs", "dfs", "astar_gbfs", "iddfs"]
    # unmapped tokens with >= 2% mass under any prompt (forced, twins, padtwins)
    mass: dict[int, float] = {}
    for k in keys:
        if P[k]["kind"] not in ("forced", "twin", "padtwin"):
            continue
        for t, p in zip(tf[k]["top_ids"], tf[k]["top_p"]):
            if p >= 0.02 and t not in map0:
                mass[t] = max(mass.get(t, 0.0), p)
    lab = labeller(unit)
    twin_key = next(k for k in keys if P[k]["kind"] == "twin" and P[k]["w"] == "W1")
    open_txt = lm.tok.decode(P[twin_key]["dec_ids"][P[twin_key]["P"]:])
    cont = {}
    n_cont = 10
    for t in sorted(mass, key=lambda x: -mass[x])[:12]:
        ids = P[twin_key]["dec_ids"] + [t]
        seqs = gen_continuations(lm, ids, n_cont, 384 if unit == "T10" else 640, U["fence"], (unit, "tokmap", t))
        labels = []
        for s in seqs:
            text = open_txt + lm.tok.decode([t] + s, skip_special_tokens=True)
            labels.append(lab(text)["label"])
        cnt = {x: labels.count(x) for x in set(labels)}
        maj = max(cnt, key=cnt.get)
        cls = maj if (cnt[maj] / len(labels) >= 0.8 and maj in modes) else "other"
        cont[int(t)] = {"token": lm.tok.decode([t]), "max_mass": mass[t], "labels": cnt, "class": cls}
        if cls != "other":
            map0[int(t)] = cls
        logger.info(f"tokmap {unit}: {lm.tok.decode([t])!r} mass {mass[t]:.3f} -> {cnt} => {cls}")
    # class probabilities under each forced prompt with the current map
    sets = {c: [t for t, cc in map0.items() if cc == c] for c in modes}
    sets = {c: v for c, v in sets.items() if v}

    def cmass(k: str, c: str) -> float:
        if c not in sets:
            return 0.0
        return float(probs[keys.index(k), sets[c]].sum())

    adh = {}
    for c in modes:
        fk = [k for k in keys if P[k]["kind"] == "forced" and P[k]["Y"] == c]
        own = float(np.mean([cmass(k, c) for k in fk])) if fk else 0.0
        adh[c] = {"mean_own_class_mass_at_d": own, "n_forced": len(fk)}
    # free-generation adherence (no opening prefill) for classes without an iteration-7 record
    need = ["union_find"] if unit == "T10" else ["astar_gbfs", "iddfs"]
    for c in need:
        fk = [k for k in keys if P[k]["kind"] == "forced" and P[k]["Y"] == c and P[k].get("name_idx") == 0]
        labels = []
        n_per = 4 if not quick else 2
        for k in fk:
            seqs = gen_continuations(lm, P[k]["ids"], n_per, 512 if unit == "T10" else 1024, U["fence"],
                                     (unit, "adh", k))
            for s in seqs:
                labels.append(lab(lm.tok.decode(s, skip_special_tokens=True))["label"])
        share = labels.count(c) / max(1, len(labels))
        adh[c].update({"free_labels": {x: labels.count(x) for x in set(labels)}, "own_label_share": share,
                       "n_free": len(labels)})
    classes = []
    for c in modes:
        a = adh[c]
        if c in need:
            keep = a.get("own_label_share", 0) >= 0.7 and a["mean_own_class_mass_at_d"] >= 0.5
        else:
            keep = a["mean_own_class_mass_at_d"] >= 0.5 or c in ("union_find",)
        a["kept"] = bool(keep and c in sets)
        if a["kept"]:
            classes.append(c)
    res = {"unit": unit, "tf_top50": tf, "unmapped_candidates": cont, "token_map": {str(k): v for k, v in map0.items()},
           "class_sets": sets, "adherence": adh, "classes": classes, "seconds": round(time.time() - t0, 1)}
    write_json(out_p, res)
    logger.info(f"S3 {unit}: classes {classes}; adherence {json.dumps({c: round(a['mean_own_class_mass_at_d'], 3) for c, a in adh.items()})}")
    return res


# ================================================================================================ pairs
def build_pairs(unit: str, P: dict[str, dict[str, Any]], cls: dict[str, int], classes: list[str]
                ) -> dict[str, Any]:
    rng = np.random.default_rng(8002)
    src_ok, excluded = [], []
    for k, r in P.items():
        if r["kind"] != "forced" or r["Y"] not in classes:
            continue
        if classes[cls[k]] != r["Y"]:
            excluded.append({"key": k, "Y": r["Y"], "tf_class": classes[cls[k]]})
            continue
        src_ok.append(k)
    if unit == "T10":
        bases_tr = [k for k, r in P.items() if (r["kind"] == "twin" and r["split"] == "train") or
                    (r["kind"] == "padtwin" and r["split"] == "train")]
        bases_he = [k for k, r in P.items() if (r["kind"] == "twin" and r["split"] == "held") or
                    (r["kind"] == "padtwin" and r["split"] == "held")]
    else:
        bases_tr = [k for k, r in P.items() if r["kind"] == "twin" and r["split"] == "train"]
        bases_he = [k for k, r in P.items() if r["kind"] == "twin" and r["split"] == "held"]
    src_tr = [k for k in src_ok if P[k]["split"] == "train"]
    src_he = [k for k in src_ok if P[k]["split"] == "held"]

    def cross(S: list[str], B: list[str], cap: int) -> list[tuple[str, str]]:
        allp = [(s, b) for s in S for b in B if cls[s] != cls[b]]
        if len(allp) <= cap:
            return allp
        strata: dict[tuple[int, int], list[tuple[str, str]]] = {}
        for p in allp:
            strata.setdefault((cls[p[0]], cls[p[1]]), []).append(p)
        out = []
        for key, ps in sorted(strata.items()):
            n = max(1, int(round(cap * len(ps) / len(allp))))
            ix = rng.choice(len(ps), size=min(n, len(ps)), replace=False)
            out += [ps[i] for i in sorted(ix)]
        return out
    train = cross(src_tr, bases_tr, TRAIN_PAIR_CAP)
    held = cross(src_he, bases_he, HELD_PAIR_CAP)
    return {"train": train, "held": held, "sources_train": src_tr, "sources_held": src_he, "bases_train": bases_tr,
            "bases_held": bases_he, "excluded_sources": excluded}


# ================================================================================================ helpers
def recov(site: DecSite, L: int, pairs: list[tuple[str, str]], R: Any, full: dict[str, np.ndarray],
          tgt_cls: dict | None = None, seed: int = 0) -> dict[str, Any]:
    ev = site.evaluate(L, pairs, R, tgt_cls=tgt_cls)
    r = ST.recovery(ev["delta"], full["delta"], [p[0] for p in pairs], [p[1] for p in pairs], seed=seed)
    r["delta"] = ev["delta"]
    return r


def by_class(site: DecSite, pairs: list[tuple[str, str]], ev_delta: np.ndarray, full_delta: np.ndarray,
             classes: list[str]) -> dict[str, Any]:
    out = {}
    for ci, c in enumerate(classes):
        ix = [i for i, p in enumerate(pairs) if site.cls[p[0]] == ci]
        if not ix:
            continue
        r = ST.recovery(ev_delta[ix], full_delta[ix], [pairs[i][0] for i in ix], [pairs[i][1] for i in ix],
                        n_boot=500)
        out[c] = {k: v for k, v in r.items() if k != "delta"}
    return out


def strip(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if k != "delta"}


# ================================================================================================ main stage
def stage_dec(unit: str, quick: bool = False, force_L: int | None = None) -> None:
    rtag = f"_L{force_L}" if force_L is not None else ""
    out_p = RESULTS / f"dec_{unit}{rtag}.json"
    if out_p.exists():
        logger.info(f"{out_p.name} exists; skipping")
        return
    U = UNITS[unit]
    fam = U["family"]
    P = load_prompts(unit)
    lm = load_lm(fam)
    t_all = time.time()
    s3 = stage_s3(unit, lm, P, quick)
    classes = s3["classes"]
    cmap = ClassMap(classes, {c: s3["class_sets"][c] for c in classes})
    if len(classes) < 3:
        add_deviation(f"{unit}_two_class", f"{unit} has {len(classes)} adherent classes {classes}; c2 cyclic "
                                           f"derangements replaced by the prompt-level balanced shuffle (F2/F3)")
    # ---- class of every prompt (TF argmax over the kept classes)
    keys_all = list(P)
    base_kinds = ("twin", "padtwin") if unit == "T10" else ("twin",)
    base_keys = [k for k in keys_all if P[k]["kind"] in base_kinds]
    forced_keys = [k for k in keys_all if P[k]["kind"] == "forced" and P[k]["Y"] in classes]
    site = DecSite(lm, P, cmap, base_keys=base_keys + forced_keys, all_keys=keys_all, G=4, Q=12)
    cls = site.cls
    pairs = build_pairs(unit, P, cls, classes)
    train, held = pairs["train"], pairs["held"]
    logger.info(f"{unit}: {len(train)} train / {len(held)} held pairs; excluded sources {len(pairs['excluded_sources'])}")
    base_cls_counts = {classes[c]: sum(cls[b] == c for b in base_keys) for c in range(len(classes))}
    commit(f"commit1_{unit}", {
        "unit": unit, "classes": classes, "class_token_sets": {c: cmap.sets[c] for c in classes},
        "token_strings": {c: [lm.tok.decode([t]) for t in cmap.sets[c]] for c in classes},
        "decision_position": "last prefilled opening token (T10: token 10 ' def' after 'def solve(n, edges):'; GRID: "
                             "c*[31])", "n_train_pairs": len(train), "n_held_pairs": len(held),
        "train_pairs_sha256": __import__("hashlib").sha256(json.dumps(train).encode()).hexdigest(),
        "held_pairs_sha256": __import__("hashlib").sha256(json.dumps(held).encode()).hexdigest(),
        "excluded_sources": pairs["excluded_sources"], "base_class_counts": base_cls_counts,
        "natural_basis": "twins (c5/c6); twins + forced + placement prompts (c5b/c6b)",
        "scan_rule": "blocks 0,2,..; rank 1, seed 0, 2-fold leave-family-out CV inside train, 100 steps; L* = argmax "
                     "median CV recovery (ties -> earlier)", "fit": {"steps": FIT_STEPS, "lr": LR, "G": 4, "Q": 12,
                                                                      "val_every": 20, "patience": 3}})
    write_json(DATA / f"pairs_{unit}.json", pairs)
    # ---- unit tests (KV path)
    ut = unit_tests(site, lm, P, train, held, unit)
    # ---- scan
    N = lm.N
    scan_blocks = list(range(0, N - 1, 2))
    fams_tr = sorted({fam_of(P[s]) for s in pairs["sources_train"]})
    folds = [fams_tr[-1], fams_tr[0]]
    scan = {}
    t0 = time.time()
    reuse_scan = force_L is None and (RESULTS / f"scan_{unit}.json").exists()
    for L in (scan_blocks if (force_L is None and not reuse_scan) else []):
        rec = []
        fh = site.evaluate(L, held[:96], None)
        if float(np.mean(np.abs(fh["delta"]) >= 1.0)) < 0.10:
            scan[L] = {"cv_recovery_by_fold": [], "cv_median_recovery": float("nan"),
                       "full_state_mean_delta_held96": float(fh["delta"].mean()),
                       "full_state_flip_share_held96": float(np.mean(fh["delta"] > 0)),
                       "note": "full-state exchange moves < 10% of pairs by >= 1 nat: recovery undefined, not fitted"}
            logger.info(f"scan {unit} L{L}: no full-state effect ({scan[L]['full_state_mean_delta_held96']:.3f})")
            continue
        for fo in folds:
            tp = [p for p in train if fam_of(P[p[0]]) != fo]
            vp = [p for p in train if fam_of(P[p[0]]) == fo]
            vp = [vp[i] for i in np.random.default_rng(L).choice(len(vp), size=min(96, len(vp)), replace=False)]
            fit = site.fit(L, tp, [], seed=0, steps=SCAN_STEPS if not quick else 20, ranks=(1,), log_name=f"scan L{L}")
            full = site.evaluate(L, vp, None)
            r = recov(site, L, vp, fit["R"][:, :1], full)
            rec.append(r["recovery"] if r["recovery"] is not None else float("nan"))
        scan[L] = {"cv_recovery_by_fold": rec, "cv_median_recovery": float(np.nanmedian(rec)),
                   "full_state_mean_delta_held96": float(fh["delta"].mean()),
                   "full_state_flip_share_held96": float(np.mean(fh["delta"] > 0))}
        logger.info(f"scan {unit} L{L}: {scan[L]} ({time.time() - t0:.0f}s)")
    if force_L is not None or reuse_scan:
        scan = read_json(RESULTS / f"scan_{unit}.json")
        scan = {int(k): v for k, v in scan.items()}
    else:
        write_json(RESULTS / f"scan_{unit}.json", scan)
    def _score(L: int) -> float:
        v = scan[L]["cv_median_recovery"]
        return round(float(v), 6) if (v is not None and np.isfinite(float(v))) else -np.inf
    Lstar = max(scan_blocks, key=lambda L: (_score(L), -L)) if force_L is None else force_L
    readout_proximal = Lstar >= N - 4
    logger.info(f"{unit}: L* = {Lstar} (readout-proximal {readout_proximal})")
    # ---- main fits
    L = Lstar
    full_h = site.evaluate(L, held, None)
    fits = {}
    for sd in (FIT_SEEDS if not quick else (0,)):
        vf = fams_tr[sd % len(fams_tr)]
        tp = [p for p in train if fam_of(P[p[0]]) != vf]
        vp = [p for p in train if fam_of(P[p[0]]) == vf]
        vp = [vp[i] for i in np.random.default_rng(sd).choice(len(vp), size=min(96, len(vp)), replace=False)]
        mp = MAPS / f"{unit}_dec_L{L}_seed{sd}.pt"
        if mp.exists() and force_L is None:
            fits[sd] = {"R": torch.load(mp), "best_step": None, "note": "map reused from an earlier run of this "
                        "stage (identical code, seed and pairs) that crashed after fitting", "hist": []}
            continue
        fits[sd] = site.fit(L, tp, vp, seed=sd, steps=FIT_STEPS if not quick else 40, log_name=f"{unit} L{L} s{sd}")
        torch.save(fits[sd]["R"], mp)
    vf = fams_tr[0]
    tp = [p for p in train if fam_of(P[p[0]]) != vf]
    vp = [p for p in train if fam_of(P[p[0]]) == vf][:96]
    r1p = MAPS / f"{unit}_dec_L{L}_rank1only.pt"
    if r1p.exists() and force_L is None:
        fit_r1 = {"R": torch.load(r1p)}
    else:
        fit_r1 = site.fit(L, tp, vp, seed=0, steps=FIT_STEPS if not quick else 40, ranks=(1,),
                          log_name=f"{unit} r1only")
        torch.save(fit_r1["R"], r1p)
    R0 = fits[0]["R"]
    # ---- held-out recovery by rank / seed / class
    tf_rows = []
    rec_rank: dict[int, Any] = {}
    for sd, f in fits.items():
        for k in RANKS:
            r = recov(site, L, held, f["R"][:, :k], full_h, seed=sd)
            if sd == 0:
                rec_rank[k] = {**strip(r), "by_class": by_class(site, held, r["delta"], full_h["delta"], classes)}
            else:
                rec_rank.setdefault(f"seed{sd}", {})[k] = strip(r)
            for i, p in enumerate(held):
                tf_rows.append({"unit": unit, "site": "dec", "layer": L, "fit": f"seed{sd}", "rank_k": k,
                                "src": p[0], "base": p[1], "class_src": classes[cls[p[0]]],
                                "class_base": classes[cls[p[1]]], "delta": float(r["delta"][i]),
                                "delta_full": float(full_h["delta"][i])})
    best = max(RANKS, key=lambda k: rec_rank[k]["recovery"] or -9)
    kstar = min(k for k in RANKS if (rec_rank[k]["recovery"] or -9) >= 0.9 * rec_rank[best]["recovery"])
    r1only = strip(recov(site, L, held, fit_r1["R"][:, :1], full_h))
    Rk = R0[:, :kstar]
    main = rec_rank[kstar]
    logger.info(f"{unit}: k* = {kstar}; recovery {main['recovery']:.3f} CI {main['ci95']}")
    # ---- c1 random subspaces
    c1 = {}
    for k in RANKS:
        vals = []
        for i in range(N_RANDOM_SUBSPACES if not quick else 5):
            r = recov(site, L, held, haar(RANDOM_SEED0 + i, lm.D, k), full_h)
            vals.append(r["recovery"])
        vals = np.array([v for v in vals if v is not None])
        c1[k] = {"median": float(np.median(vals)), "p95": float(np.percentile(vals, 95)), "max": float(vals.max()),
                 "n": int(len(vals)), "pass": bool(np.median(vals) <= THRESH["c1_median_max"])}
        logger.info(f"c1 {unit} k{k}: {c1[k]}")
    # ---- c2 label controls
    true_d = np.array([r["delta"] for r in tf_rows if r["fit"] == "seed0" and r["rank_k"] == kstar])
    c2 = label_controls(site, P, L, train, held, full_h, classes, cls, main, kstar, fams_tr, quick, true_d)
    # ---- c4 reverse
    c4 = reverse_test(site, P, L, Rk, classes, cls, unit, pairs)
    # ---- c5 / c6 natural basis
    twins = [k for k in keys_all if P[k]["kind"] == "twin"]
    Xn = torch.stack([site.H[k][L] for k in twins])
    allnat = [k for k in keys_all if P[k]["kind"] in ("twin", "forced", "ban", "top5", "instr_novel", "seed_rand1",
                                                       "seed_rand2", "instr_new", "padtwin", "p0")]
    Xb = torch.stack([site.H[k][L] for k in allnat])
    c5, c6 = {}, {}
    for tag, X in (("twins", Xn), ("twins_forced_bans", Xb)):
        U64, S = pca_basis(X, 64)
        Rp = project_map(Rk, U64)
        if Rp is None:
            c5[tag] = {"retention": 0.0, "note": "projection lost rank", "n_states": int(X.shape[0])}
        else:
            rp = recov(site, L, held, Rp, full_h)
            c5[tag] = {"recovery_proj": rp["recovery"], "retention": (rp["recovery"] or 0) / main["recovery"]
                       if main["recovery"] else None, "n_states": int(X.shape[0])}
        share = variance_share(Rk, S)
        rs = np.array([variance_share(haar(50000 + i, lm.D, kstar), S) for i in range(1000)])
        c6[tag] = {"share": share, "random_p95": float(np.percentile(rs, 95)), "random_median": float(np.median(rs)),
                   "percentile": float((rs < share).mean() * 100), "pass": bool(share > np.percentile(rs, 95)),
                   "n_states": int(X.shape[0])}
    c5["pass"] = bool((c5["twins"].get("retention") or 0) >= THRESH["c5_min"])
    c5["pass_b"] = bool((c5["twins_forced_bans"].get("retention") or 0) >= THRESH["c5_min"])
    # ---- c7 principal angles
    cos = []
    sds = sorted(fits)
    for a in range(len(sds)):
        for b in range(a + 1, len(sds)):
            cos.append(float(principal_cosines(fits[sds[a]]["R"][:, :kstar], fits[sds[b]]["R"][:, :kstar])[0]))
    rnd = [float(principal_cosines(haar(60000 + i, lm.D, kstar), haar(61000 + i, lm.D, kstar))[0]) for i in range(1000)]
    c7 = {"first_cosines": cos, "median_first_cosine": float(np.median(cos)) if cos else None,
          "random_p99": float(np.percentile(rnd, 99)),
          "pass": bool(cos and np.median(cos) >= THRESH["c7_cos_min"] and np.median(cos) > np.percentile(rnd, 99))}
    # ---- baselines: DiM-1 per class, PCA-k, logit lens
    try:
        base_tab = baselines(site, P, L, held, full_h, classes, cls, twins, lm, cmap, Rk, kstar)
    except (RuntimeError, ValueError, KeyError, IndexError) as e:
        logger.error(f"baselines failed: {e}")
        base_tab = {"error": str(e)}
    # ---- iteration-7 Gemma subspaces (side table)
    try:
        side = iter7_side(site, L, held, full_h, Xn, lm) if unit == "GRID" else None
    except (RuntimeError, ValueError, KeyError, IndexError, TypeError, AttributeError) as e:
        logger.error(f"iter7 side table failed: {e}")
        side = {"error": str(e)}
    res = {"unit": unit, "family": fam, "classes": classes, "L_star": Lstar, "readout_proximal": readout_proximal,
           "k_star": kstar, "scan": scan, "unit_tests": ut, "n_train_pairs": len(train), "n_held_pairs": len(held),
           "recovery_by_rank": rec_rank, "rank1_only": r1only, "main": main,
           "off_manifold_flag": bool(main["recovery"] and main["recovery"] > OFF_MANIFOLD),
           "full_state_held": {"mean_delta": float(full_h["delta"].mean()),
                               "flip_share": float(np.mean(full_h["delta"] > 0)),
                               "share_abs_ge_1": float(np.mean(np.abs(full_h["delta"]) >= 1))},
           "fits": {str(s): {k: v for k, v in f.items() if k not in ("R", "hist")} | {"hist_tail": f.get("hist", [])[-3:]}
                    for s, f in fits.items()},
           "c1": c1, "c2": c2, "c4": c4, "c5": c5, "c6": c6, "c7": c7, "baselines": base_tab, "iter7_side": side,
           "seconds": round(time.time() - t_all, 1)}
    write_jsonl(DATA / f"tf_{unit}_dec{rtag}.jsonl", tf_rows)
    torch.save({k: site.H[k].to(torch.bfloat16) for k in keys_all}, RESULTS.parent / "cache" / f"states_{unit}_dec_trained.pt")
    torch.save({k: site.q[k] for k in keys_all}, RESULTS.parent / "cache" / f"q_{unit}_dec_trained.pt")
    write_json(out_p, res)
    logger.info(f"dec {unit} done in {time.time() - t_all:.0f}s")
    site.free()
    lm.free()


def unit_tests(site: DecSite, lm: Any, P: dict, train: list, held: list, unit: str) -> dict[str, Any]:
    p = RESULTS / f"unit_tests_gpu_{unit}.json"
    if p.exists():
        return read_json(p)
    from engine8 import block_hooks
    out: dict[str, Any] = {}
    L = lm.N // 2
    bases = sorted({b for _, b in held})[:4]
    # U1: zero-rank edit on the KV path == unedited KV path (bit-identical expected)
    Hb = torch.stack([site.H[b][L] for b in bases]).to(lm.dev)[:, None].expand(4, 12, -1).contiguous()
    with torch.no_grad():
        a = site.forward(L, bases, Hb)
        b = site.forward(L, bases, Hb.clone())
    out["U1_max_abs_logit_diff"] = float((a - b).abs().max())
    # U2: KV path vs full recompute (unedited) margin difference
    diffs, diffs_full = [], []
    for bk in bases:
        ids = P[bk]["dec_ids"]
        with torch.no_grad():
            lg_full = prefill(lm, ids)["logits"]
            lg_kv = site.forward(L, [bk] * 4, torch.stack([site.H[bk][L]] * 4).to(lm.dev)[:, None].expand(4, 12, -1)
                                 .contiguous())[0, 0]
        lpf = site.cmap.lp(lg_full)
        lpk = site.cmap.lp(lg_kv)
        diffs.append(float((lpf - lpk).abs().max()))
        # U3: full-state edit via the KV path vs full recompute with the replaced state
        s = next(s for s, b in held if b == bk)
        hs = site.H[s][L].to(lm.dev)

        def ed(h: torch.Tensor) -> torch.Tensor:
            h = h.clone()
            h[:, -1] = hs.to(h.dtype)
            return h
        with torch.no_grad():
            lg_full_e = prefill(lm, ids, edits={L: ed})["logits"]
            lg_kv_e = site.forward(L, [bk] * 4, hs[None, None].expand(4, 12, -1).contiguous())[0, 0]
        diffs_full.append(float((site.cmap.lp(lg_full_e) - site.cmap.lp(lg_kv_e)).abs().max()))
    out["U2_max_abs_logP_class_diff_kv_vs_full"] = max(diffs)
    out["U3_max_abs_logP_class_diff_fullstate_edit"] = max(diffs_full)
    out["U2_pass_0.3"] = bool(max(diffs) <= 0.3)
    # U9: 20-step mini fit reduces inner-validation KL by >= 20%
    tp = train[: min(len(train), 600)]
    vp = held[:48]
    ev0 = float(np.mean(site.evaluate(L, vp, haar(1000, lm.D, 1))["kl"]))
    f = site.fit(L, tp, [], seed=0, steps=20, ranks=(1,), log_name="U9")
    ev1 = float(np.mean(site.evaluate(L, vp, f["R"][:, :1])["kl"]))
    out["U9"] = {"kl_random_init_map": ev0, "kl_after_20_steps": ev1, "reduction": 1 - ev1 / ev0 if ev0 else None}
    out["U7_memory_peak_GB"] = round(torch.cuda.max_memory_allocated() / 1e9, 2)
    write_json(p, out)
    logger.info(f"unit tests {unit}: {out}")
    return out


def label_controls(site: DecSite, P: dict, L: int, train: list, held: list, full_h: dict, classes: list[str],
                   cls: dict, main: dict, kstar: int, fams_tr: list[int], quick: bool,
                   true_deltas: np.ndarray | None = None) -> dict[str, Any]:
    C = len(classes)
    # class-mean target distributions (over train sources of each class)
    srcs = sorted({s for s, _ in train})
    cmean = {}
    for c in range(C):
        ss = [s for s in srcs if cls[s] == c]
        if ss:
            cmean[c] = torch.stack([site.q[s] for s in ss]).mean(0)
    perms = []
    if C >= 3:
        perms.append(("pi1", {c: (c + 1) % C for c in range(C)}))
        perms.append(("pi2", {c: (c + 2) % C for c in range(C)}))
    rng = np.random.default_rng(12)
    # prompt-level balanced derangement: every train source gets a label different from its true class
    plab = {}
    for i, s in enumerate(sorted(srcs, key=lambda x: (cls[x], x))):
        others = [c for c in range(C) if c != cls[s] and c in cmean]
        plab[s] = others[i % len(others)]
    if C >= 3:
        perms.append(("prompt", plab))
    else:
        # F3 (2 classes): a derangement sends every source to its base's class, so all pairs would be dropped;
        # use iteration-7-style balanced prompt-level shuffles instead (no dropping; evaluated toward true labels)
        for j in range(3):
            r2 = np.random.default_rng(12 + j)
            ss = sorted(srcs)
            lab0 = [cls[x] for x in ss]
            perm = list(r2.permutation(lab0))
            perms.append((f"shuffle{j}", {x: int(c) for x, c in zip(ss, perm)}))
    out: dict[str, Any] = {"note": "targets = class-mean q of the permuted class; pairs whose permuted target equals "
                                   "class_base are dropped (100% of retained targets differ from source and base)"
                                   if C >= 3 else "2-class unit (F3): balanced prompt-level label shuffles, no pair "
                                   "dropped, evaluated toward the true labels (weaker than a derangement)"}
    true_rec = main["recovery"]
    for (name, pm), sd in zip(perms, list(LABEL_CONTROL_SEEDS) + [13, 14]):
        def pt(s: str) -> int:
            return pm[s] if (name == "prompt" or name.startswith("shuffle")) else pm[cls[s]]
        if name.startswith("shuffle"):
            tr = [p for p in train if pt(p[0]) in cmean]
        else:
            tr = [p for p in train if pt(p[0]) != cls[p[1]] and pt(p[0]) in cmean]
        ptg = {p: cmean[pt(p[0])] for p in tr}
        vf = fams_tr[sd % len(fams_tr)]
        tp = [p for p in tr if fam_of(P[p[0]]) != vf]
        vp = [p for p in tr if fam_of(P[p[0]]) == vf][:96]
        f = site.fit(L, tp, vp, seed=sd, pair_targets=ptg, steps=FIT_STEPS if not quick else 40,
                     log_name=f"c2 {name}")
        torch.save(f["R"], MAPS / f"{P[train[0][0]]['unit']}_dec_L{L}_perm_{name}.pt")
        Rk = f["R"][:, :kstar]
        r_true = recov(site, L, held, Rk, full_h)
        rec = {"fit": {k: v for k, v in f.items() if k not in ("R", "hist")},
               "n_train_pairs_retained": len(tr),
               "share_targets_changed": float(np.mean([pt(p[0]) != cls[p[0]] for p in tr])) if tr else None,
               "heldout_recovery_toward_true_class": strip(r_true),
               "ratio_to_true_fit": (r_true["recovery"] / true_rec) if (true_rec and r_true["recovery"] is not None)
               else None}
        rec["pass"] = bool(rec["ratio_to_true_fit"] is not None and rec["ratio_to_true_fit"] <= THRESH["c2_ratio_max"])
        if true_deltas is not None:
            rec["test_true_gt_perm"] = ST.cluster_wilcoxon_p(true_deltas, r_true["delta"], [p[0] for p in held],
                                                             [p[1] for p in held])
            append_jsonl(DATA / f"tf_{P[train[0][0]]['unit']}_dec_perm_L{L}.jsonl",
                         [{"fit": f"perm_{name}", "rank_k": kstar, "src": p[0], "base": p[1],
                           "delta": float(r_true["delta"][i])} for i, p in enumerate(held)])
        if name in ("pi1", "pi2"):
            hp = [p for p in held if pm[cls[p[0]]] != cls[p[1]]]
            tc = {p: pm[cls[p[0]]] for p in hp}
            ev = site.evaluate(L, hp, Rk, tgt_cls=tc)
            evf = site.evaluate(L, hp, "none", tgt_cls=tc)
            rec["secondary_mean_delta_toward_permuted_class"] = float(ev["delta"].mean()) if len(hp) else None
            rec["secondary_n_pairs"] = len(hp)
        trs = tr[:192]
        evt = site.evaluate(L, trs, Rk)
        rec["train_fit_kl_to_permuted_targets"] = float(np.mean([float(kl(ptg[p], torch.tensor(evt["q"][i])))
                                                                 for i, p in enumerate(trs)]))
        out[name] = rec
        logger.info(f"c2 {name}: ratio {rec['ratio_to_true_fit']}")
    out["pass"] = bool(all(out[n]["pass"] for n, _ in perms))
    out["primary_statistic"] = "held-out recovery toward the TRUE source class under each label-control fit <= 0.1 x " \
                               "true-fit recovery"
    return out


def reverse_test(site: DecSite, P: dict, L: int, Rk: torch.Tensor, classes: list[str], cls: dict, unit: str,
                 pairs: dict) -> dict[str, Any]:
    """c4: base = held-out forced source, source = its own padding twin (GRID: the W-twin of the same template);
    Delta toward the twin's class (DAS) / the same for the full-state reverse."""
    rows = []
    for s in pairs["sources_held"]:
        if unit == "T10":
            tw = P[s]["key"].replace("|forced|", "|padtwin|")
        else:
            w = "W" + P[s]["template"][1:]
            tw = next(k for k, r in P.items() if r["kind"] == "twin" and r["w"] == w)
        if tw not in site.H or cls[tw] == cls[s]:
            continue
        rows.append((tw, s))
    if not rows:
        return {"n": 0, "pass": False, "note": "no reverse pairs with distinct classes"}
    full = site.evaluate(L, rows, None)
    das = site.evaluate(L, rows, Rk)
    r = ST.recovery(das["delta"], full["delta"], [a for a, _ in rows], [b for _, b in rows], min_full=0.0)
    r["pass"] = bool(r["recovery"] is not None and r["recovery"] >= THRESH["c4_min"])
    r["n_pairs"] = len(rows)
    return strip(r)


def baselines(site: DecSite, P: dict, L: int, held: list, full_h: dict, classes: list[str], cls: dict,
              twins: list[str], lm: Any, cmap: ClassMap, Rk: torch.Tensor, kstar: int) -> dict[str, Any]:
    out = {}
    mt = torch.stack([site.H[k][L] for k in twins]).mean(0)
    for ci, c in enumerate(classes):
        fk = [k for k in P if P[k]["kind"] == "forced" and P[k]["Y"] == c and P[k]["split"] == "train"]
        if not fk:
            continue
        v = torch.stack([site.H[k][L] for k in fk]).mean(0) - mt
        if float(v.norm()) == 0:
            continue
        u = (v / v.norm())[:, None]
        ix = [i for i, p in enumerate(held) if cls[p[0]] == ci]
        if not ix:
            continue
        hp = [held[i] for i in ix]
        ev = site.evaluate(L, hp, u)
        r = ST.recovery(ev["delta"], full_h["delta"][ix], [p[0] for p in hp], [p[1] for p in hp], n_boot=500)
        out[f"DiM1_{c}"] = strip(r) | {"cos_with_R1": float(abs((u[:, 0] @ Rk[:, 0])))}
    allf = [k for k in P if P[k]["kind"] in ("forced", "twin")]
    U8, _ = pca_basis(torch.stack([site.H[k][L] for k in allf]), 8)
    for k in (1, 2, 4, 8):
        out[f"PCA{k}"] = strip(recov(site, L, held, U8[:, :k], full_h))
    # logit lens: cosine of R_1 with the final-norm-adjusted unembedding difference of the two leading class tokens
    try:
        W = lm.model.lm_head.weight.float()
        g = lm.mm.norm.weight.float()
        if lm.family == "gemma":
            g = 1.0 + g
        c_off = classes[0] if classes[0] != "union_find" else classes[1]
        ta = cmap.sets[c_off][0]
        tb = cmap.sets[classes[-1]][0] if classes[-1] != c_off else cmap.sets[classes[1]][0]
        dvec = ((W[ta] - W[tb]).to(g.device) * g).cpu()
        out["logit_lens_cos_R1"] = float(abs(dvec @ Rk[:, 0]) / dvec.norm())
        out["logit_lens_tokens"] = [lm.tok.decode([ta]), lm.tok.decode([tb])]
    except (RuntimeError, IndexError, KeyError) as e:
        out["logit_lens_error"] = str(e)
    return out


def iter7_side(site: DecSite, L: int, held: list, full_h: dict, Xn: torch.Tensor, lm: Any) -> dict[str, Any]:
    """c4-c6-style checks and principal angles on iteration 7's das_L17 subspaces (dormancy checks it never ran)."""
    out = {}
    d = INPUTS / "exp38" / "das_subspaces"
    U64, S = pca_basis(Xn, 64)
    Rs = []
    for sd in range(3):
        f = d / f"das_L17_seed{sd}.pt"
        if not f.exists():
            continue
        obj = torch.load(f, map_location="cpu")
        R = obj["R"] if isinstance(obj, dict) and "R" in obj else obj
        R = R.float()
        if R.shape[0] != lm.D:
            R = R.T
        Rs.append(R)
        share = variance_share(R[:, :4], S)
        out[f"seed{sd}"] = {"variance_share_rank4_twins_atL": share}
    if Rs:
        out["note"] = f"iteration-7 subspaces were fitted at block 17; shares computed on block-{L} twin states"
        cs = [float(principal_cosines(Rs[a][:, :4], Rs[b][:, :4])[0]) for a in range(len(Rs)) for b in
              range(a + 1, len(Rs))]
        out["iter7_seed_first_cosines_rank4"] = cs
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit", required=True)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--force_L", type=int, default=None)
    a = ap.parse_args()
    setup_logging(f"run_dec_{a.unit}")
    # no RLIMIT_AS here: CUDA reserves far more virtual address space than RSS (host RSS is monitored instead)
    stage_dec(a.unit, quick=a.quick, force_L=a.force_L)


if __name__ == "__main__":
    main()
