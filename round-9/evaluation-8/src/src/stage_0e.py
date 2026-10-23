#!/usr/bin/env python3
"""Runner for item 0e (alias-named manifold). Called by eval.py after predictions/commit_s0e.json is on disk."""
from __future__ import annotations

import csv
import gc
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger
from scipy.stats import rankdata

import alias_geometry as AG

ART_TP = "art_R-HSmXq2t97f"


def _avg_rank_map(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    uniq, counts = np.unique(values, return_counts=True)
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    return uniq, starts + (counts + 1) / 2.0


def exact_null(values: np.ndarray) -> np.ndarray:
    """Spearman null over every distinct arrangement of the overlap multiset (g ranks 1..n, no ties in g)."""
    A = AG.distinct_assignments(list(values))
    uniq, avg = _avg_rank_map(values)
    R = avg[np.searchsorted(uniq, A)]
    R = R - R.mean(1, keepdims=True)
    gr = np.arange(1, A.shape[1] + 1, dtype=float)
    gr -= gr.mean()
    return (R @ gr) / np.sqrt((R ** 2).sum(1) * (gr ** 2).sum())


def mc_null(values: np.ndarray, n: int, rng: np.random.Generator) -> np.ndarray:
    rx = rankdata(values)
    gr = np.arange(1, len(values) + 1, dtype=float)
    gr -= gr.mean()
    out = np.empty(n)
    for s in range(0, n, 50_000):
        m = min(50_000, n - s)
        R = rng.permuted(np.tile(rx, (m, 1)), axis=1)
        R = R - R.mean(1, keepdims=True)
        out[s:s + m] = (R @ gr) / np.sqrt((R ** 2).sum(1) * (gr ** 2).sum())
    return out


def pvals(rho: float, null: np.ndarray) -> dict[str, float]:
    eps = 1e-12
    return {"p_lower": float(np.mean(null <= rho + eps)), "p_two_sided": float(np.mean(np.abs(null) >= abs(rho) - eps)),
            "n_null": int(len(null))}


def five_centroid(g_alg: np.ndarray, x_alg: np.ndarray) -> dict[str, Any]:
    import itertools
    obs = AG.spearman(g_alg, x_alg)
    rhos = np.array([AG.spearman(g_alg, x_alg[list(p)]) for p in itertools.permutations(range(len(x_alg)))])
    eps = 1e-12
    # attainable floor: the number of permutations that reproduce the most extreme (lowest) rho
    floor = float(np.mean(rhos <= rhos.min() + eps))
    return {"rho": obs, "p_lower": float(np.mean(rhos <= obs + eps)),
            "p_two_sided": float(np.mean(np.abs(rhos) >= abs(obs) - eps)), "n_perm": len(rhos),
            "floor_lower": floor, "floor_nominal": 1 / len(rhos)}


def run(art_dir: Path, out_dir: Path, rng_seed: int = AG.SEED) -> dict[str, Any]:
    src = art_dir / "src"
    res: dict[str, Any] = {"gates": {}, "flags": []}
    alias_table = AG.read_literal(src / "common.py", "ALIAS_TABLE")
    canon = AG.read_literal(src / "common.py", "CANON_ORDER")
    rows = AG.overlap_table(alias_table)
    prim_by = {a: [r["primary"] for r in rows if r["algorithm"] == a] for a in AG.NONBANNED}
    res["primary_vectors"] = prim_by
    res["primary_vectors_match_commit"] = prim_by == AG.EXPECTED_PRIMARY
    assert res["primary_vectors_match_commit"], f"detector code wrong: {prim_by} != {AG.EXPECTED_PRIMARY}"
    x1 = np.array([r["primary"] for r in rows], dtype=float)
    x2 = np.array([r["secondary"] for r in rows], dtype=float)
    x0 = (x1 > 0).astype(float)
    res["overlap_rows"] = rows
    res["primary_multiset"] = {int(v): int(c) for v, c in zip(*np.unique(x1, return_counts=True))}

    # ---------------------------------------------------------------------------------------- load stored state
    geo_p = art_dir / "cache/states/geo_C6_nf4.npz"
    sm_p = art_dir / "cache/states/smean_C6_nf4.npz"
    zg = np.load(geo_p, allow_pickle=False)
    geo = {15: zg["geo_k15"].astype(np.float64), 10: zg["geo_k10"].astype(np.float64)}
    labels_geo = zg["labels"].astype(str)
    L = int(zg["L"])
    have_states = sm_p.exists()
    if have_states:
        zs = np.load(sm_p, allow_pickle=False)
    else:   # published copy: the 181 MB states file is not published; use the vendored index (same rows, hashed)
        import json as _json
        zs = {k: np.array(v) for k, v in _json.loads((out_dir / "inputs/forced_index_C6_nf4.json").read_text()).items()
              if isinstance(v, list)}
        res["flags"].append("states file not available: E1-E3 run on the vendored index, E4 not run")
    kind = zs["kind"].astype(str)
    F = kind == "forced"
    labels = zs["algorithm"].astype(str)[F]
    group = zs["group"].astype(int)[F]
    template = zs["template"].astype(str)[F]
    blocks = [int(b) for b in zs["blocks"]]

    # E1 labels
    e1 = bool(len(labels) == len(labels_geo) and np.all(labels == labels_geo))
    res["gates"]["E1_labels_equal"] = e1
    # E2 multiset of (algorithm, template, alias) equals forced_set() of prompts_tp.py
    trip = list(zip(labels.tolist(), (group // 3).tolist(), (group % 3).tolist()))
    expect = [(a, t, j) for a in canon for t in range(10) for j in range(3)]
    e2 = sorted(trip) == sorted(expect) and len(set(trip)) == 300
    res["gates"]["E2_multiset_equal_forced_set"] = bool(e2)
    res["gates"]["E2_order_equal_forced_set"] = bool(trip == expect)
    res["gates"]["E2_template_field_consistent"] = bool(np.all(template == (group // 3).astype(str)))
    # E3 algorithm-level g against geometry_M1.json
    m1 = json.loads((art_dir / "results/geometry_M1.json").read_text())["M1"]
    e3 = {}
    for k in (15, 10):
        ga = AG.g_algorithm(geo[k], labels_geo)
        diff = max(abs(ga[a] - m1[f"k{k}"]["g"][a]) for a in AG.NONBANNED)
        cls = AG.classify(ga)
        e3[f"k{k}"] = {"max_abs_diff": diff, "classes_match": cls == m1[f"k{k}"]["classes"], "g": ga, "classes": cls}
    res["gates"]["E3_detail"] = e3
    res["gates"]["E3_g_matches_M1"] = bool(all(v["max_abs_diff"] < 1e-9 and v["classes_match"] for v in e3.values()))
    res["L"] = L
    # E4 independent cross-check from smean at block 31
    if not have_states:
        res["gates"]["E4_pass"] = None
        res["gates"]["E4_spearman_vs_stored_k15"] = None
    try:
        if not have_states:
            raise ValueError("states file not available")
        X = zs["smean"][F][:, blocks.index(L)].astype(np.float64)
        geo_x, ncomp = AG.knn_geodesic_independent(X, 15)
        iu = np.triu_indices(300, 1)
        rho_e4 = AG.spearman(geo_x[iu], geo[15][iu])
        rel = float(np.max(np.abs(geo_x[iu] - geo[15][iu]) / np.maximum(geo[15][iu], 1e-12)))
        res["gates"]["E4_spearman_vs_stored_k15"] = rho_e4
        res["gates"]["E4_max_rel_diff"] = rel
        res["gates"]["E4_components_before_join"] = ncomp
        res["gates"]["E4_pass"] = bool(rho_e4 >= 0.999)
        if rho_e4 < 0.999:
            res["flags"].append("E4_below_0.999")
        if rho_e4 < 0.99:
            res["flags"].append("geodesics not independently reproduced")
        del X, geo_x
    except (KeyError, ValueError, MemoryError) as exc:
        logger.error(f"E4 failed to run: {exc}")
        res["gates"]["E4_pass"] = None if not have_states else False
        res["flags"].append(f"E4_not_run: {exc}")
    del zs
    gc.collect()
    hard = res["gates"]["E1_labels_equal"] and res["gates"]["E2_multiset_equal_forced_set"] and res["gates"][
        "E3_g_matches_M1"]
    res["gates"]["hard_gates_pass"] = bool(hard)
    if not hard:
        res["flags"].append("hard gate failed: alias-level numbers withheld")
        return res

    rng = np.random.default_rng(rng_seed)
    null1 = exact_null(x1)
    null0 = exact_null(x0)
    n_sec = AG.n_distinct_assignments(list(x2))
    null2 = exact_null(x2) if n_sec <= 2_000_000 else mc_null(x2, AG.N_MC_SECONDARY, rng)
    res["null_sizes"] = {"primary_exact": int(len(null1)), "binary_exact": int(len(null0)),
                         "secondary_distinct": int(n_sec), "secondary_method": "exact" if n_sec <= 2_000_000 else
                         f"monte_carlo_{AG.N_MC_SECONDARY}"}
    order = [(a, j) for a in AG.NONBANNED for j in range(3)]
    xa1 = np.array([np.mean(prim_by[a]) for a in AG.NONBANNED])
    xa2 = np.array([np.mean([r["secondary"] for r in rows if r["algorithm"] == a]) for a in AG.NONBANNED])
    tblocks = {}
    per_k: dict[str, Any] = {}
    W = np.stack([np.bincount(rng.integers(0, 10, 10), minlength=10) for _ in range(AG.N_BOOT)]).astype(float)
    for k in (15, 10):
        ga = AG.g_alias(geo[k], labels_geo, group)
        g15 = np.array([ga[o] for o in order])
        galg = np.array([e3[f"k{k}"]["g"][a] for a in AG.NONBANNED])
        if len(np.unique(g15)) < 15:
            res["flags"].append(f"ties in alias-level g at k{k}")
        r1, r2, r0 = AG.spearman(g15, x1), AG.spearman(g15, x2), AG.spearman(g15, x0)
        st2 = AG.stratified_exact(g15.reshape(5, 3), x2.reshape(5, 3))
        st1 = AG.stratified_exact(g15.reshape(5, 3), x1.reshape(5, 3))
        c5 = five_centroid(galg, xa1)
        c5s = five_centroid(galg, xa2)
        tblocks[k] = AG.template_blocks(geo[k], labels_geo, group)
        GB = AG.boot_g(tblocks[k], W)
        GA = AG.boot_g_alg(tblocks[k], W)
        b1, b2 = AG.rowwise_spearman(GB, x1), AG.rowwise_spearman(GB, x2)
        b5 = np.array([AG.spearman(GA[i], xa1) for i in range(len(GA))])
        ci = lambda v: [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))]  # noqa: E731
        per_k[f"k{k}"] = {
            "g_alias": {f"{a}|{j}": float(ga[(a, j)]) for a, j in order}, "g_algorithm": dict(zip(AG.NONBANNED, galg.tolist())),
            "rho_primary": r1, **{f"primary_{kk}": v for kk, v in pvals(r1, null1).items()},
            "rho_secondary": r2, **{f"secondary_{kk}": v for kk, v in pvals(r2, null2).items()},
            "rho_binary": r0, **{f"binary_{kk}": v for kk, v in pvals(r0, null0).items()},
            "ci95_primary": ci(b1), "ci95_secondary": ci(b2), "ci95_5centroid": ci(b5),
            "boot_frac_rho_primary_le_-0.6": float(np.mean(b1 <= -0.6)),
            "five_centroid_primary": c5, "five_centroid_secondary": c5s,
            "stratified_secondary": st2, "stratified_primary": st1}
        logger.info(f"0e k{k}: rho1 {r1:.3f} p {per_k[f'k{k}']['primary_p_lower']:.4f}; rho2 {r2:.3f}; "
                    f"5c {c5['rho']:.3f} p {c5['p_lower']:.3f}; strat2 {st2['stat']:.3f} p {st2['p_lower']:.3f}")
    res["per_k"] = per_k

    # ---------------------------------------------------------------------------------------- placebos and control
    g15 = np.array([per_k["k15"]["g_alias"][f"{a}|{j}"] for a, j in order])
    alias_lab = np.array([f"{a}|{j}" for a, j in zip(labels_geo, group % 3)])
    rho_p1, p_p1 = [], []
    for _ in range(AG.N_PLACEBO):
        perm = rng.permutation(300)
        lab_s = labels_geo[perm]
        grp_s = group[perm]
        gs = AG.g_alias(geo[15], lab_s, grp_s)
        v = np.array([gs[o] for o in order])
        r = AG.spearman(v, x1)
        rho_p1.append(r)
        p_p1.append(pvals(r, null1)["p_lower"])
    rho_p1, p_p1 = np.array(rho_p1), np.array(p_p1)
    p_p2 = np.array([pvals(AG.spearman(g15, rng.permutation(x1)), null1)["p_lower"] for _ in range(AG.N_PLACEBO)])
    s_p3 = []
    for _ in range(AG.N_PLACEBO):
        gp = np.stack([g15.reshape(5, 3)[a][rng.permutation(3)] for a in range(5)])
        s_p3.append(AG.stratified_stat(gp, x2.reshape(5, 3))[0])
    s_p3 = np.array(s_p3)
    planted = []
    for s in range(200):
        r_ = np.random.default_rng(10_000 + s)
        gp = 12 - 2 * x1 + r_.normal(0, 0.5, size=15)
        rr = AG.spearman(gp, x1)
        planted.append((rr, pvals(rr, null1)["p_lower"]))
    planted = np.array(planted)
    res["placebos"] = {
        "P1_shuffled_alias_labels": {"n": AG.N_PLACEBO, "rho_mean": float(rho_p1.mean()), "rho_sd": float(rho_p1.std()),
                                     "share_p_lt_0.05": float(np.mean(p_p1 < 0.05)),
                                     "fails_as_required": bool(np.mean(p_p1 < 0.05) <= 0.10 and abs(rho_p1.mean()) < 0.1)},
        "P2_random_overlap_vector": {"n": AG.N_PLACEBO, "share_p_lt_0.05": float(np.mean(p_p2 < 0.05)),
                                     "p_deciles": np.percentile(p_p2, np.arange(10, 100, 10)).round(3).tolist(),
                                     "fails_as_required": bool(np.mean(p_p2 < 0.05) <= 0.10)},
        "P3_within_algorithm_shuffles": {"n": AG.N_PLACEBO, "stat_mean": float(np.nanmean(s_p3)),
                                         "stat_sd": float(np.nanstd(s_p3)),
                                         "fails_as_required": bool(abs(np.nanmean(s_p3)) < 0.1)},
        "C1_planted": {"seed0_rho": float(planted[0, 0]), "seed0_p_lower": float(planted[0, 1]),
                       "seed0_succeeds": bool(planted[0, 0] <= -0.6 and planted[0, 1] < 0.05),
                       "power_200_seeds": float(np.mean((planted[:, 0] <= -0.6) & (planted[:, 1] < 0.05)))}}
    k15 = per_k["k15"]
    code, sentence = AG.verdict_sentence(k15["rho_primary"], k15["primary_p_lower"],
                                         k15["stratified_secondary"]["p_lower"])
    res["verdict"] = {"code": code, "sentence": sentence,
                      "rule_inputs": {"rho_k15_primary": k15["rho_primary"], "p_k15_primary": k15["primary_p_lower"],
                                      "stratified_secondary_p": k15["stratified_secondary"]["p_lower"]}}
    _write_tables(out_dir, per_k, rows, order)
    try:
        _figure(out_dir, geo[15], labels_geo, group, per_k, rows, order, m1)
        res["figure"] = ["figures/alias_overlap.pdf", "figures/alias_overlap.png"]
    except (ValueError, RuntimeError) as exc:
        logger.error(f"figure failed: {exc}")
        res["flags"].append(f"figure_failed: {exc}")
    return res


def _write_tables(out_dir: Path, per_k: dict[str, Any], rows: list[dict[str, Any]], order: list) -> None:
    with (out_dir / "tables/alias_g.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["level", "algorithm", "alias_index", "alias", "primary_overlap", "secondary_overlap", "g_k15",
                    "g_k10"])
        for r, (a, j) in zip(rows, order):
            w.writerow(["alias", a, j, r["alias"], r["primary"], round(r["secondary"], 6),
                        round(per_k["k15"]["g_alias"][f"{a}|{j}"], 6), round(per_k["k10"]["g_alias"][f"{a}|{j}"], 6)])
        for a in AG.NONBANNED:
            p = [r["primary"] for r in rows if r["algorithm"] == a]
            s = [r["secondary"] for r in rows if r["algorithm"] == a]
            w.writerow(["centroid", a, "", AG.DISPLAY[a], round(float(np.mean(p)), 6), round(float(np.mean(s)), 6),
                        round(per_k["k15"]["g_algorithm"][a], 6), round(per_k["k10"]["g_algorithm"][a], 6)])
    with (out_dir / "tables/alias_stats.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["k", "statistic", "value", "p_lower", "p_two_sided", "ci95_low", "ci95_high", "null", "note"])
        for k, d in per_k.items():
            w.writerow([k, "spearman_15_primary", d["rho_primary"], d["primary_p_lower"], d["primary_p_two_sided"],
                        *d["ci95_primary"], f"exact {d['primary_n_null']}", "committed primary"])
            w.writerow([k, "spearman_15_secondary", d["rho_secondary"], d["secondary_p_lower"],
                        d["secondary_p_two_sided"], *d["ci95_secondary"], f"{d['secondary_n_null']}", "content Jaccard"])
            w.writerow([k, "spearman_15_binary", d["rho_binary"], d["binary_p_lower"], d["binary_p_two_sided"], "", "",
                        f"exact {d['binary_n_null']}", "any overlap (sensitivity)"])
            c5 = d["five_centroid_primary"]
            w.writerow([k, "spearman_5_centroid_primary", c5["rho"], c5["p_lower"], c5["p_two_sided"],
                        *d["ci95_5centroid"], "exact 120", f"attainable floor {c5['floor_lower']:.4f}"])
            c5s = d["five_centroid_secondary"]
            w.writerow([k, "spearman_5_centroid_secondary", c5s["rho"], c5s["p_lower"], c5s["p_two_sided"], "", "",
                        "exact 120", f"attainable floor {c5s['floor_lower']:.4f}"])
            for nm in ("stratified_secondary", "stratified_primary"):
                s = d[nm]
                w.writerow([k, nm, s["stat"], s["p_lower"], s["p_two_sided"], "", "",
                            f"exact {s['n_arrangements_nominal']} (effective {s['n_arrangements_effective']})",
                            f"{s['n_algorithms_used']} algorithms used"])
                w.writerow([k, f"fe_beta_{nm.split('_')[1]}", s["beta"], s["beta_p_lower"], s["beta_p_two_sided"], "",
                            "", "same stratified null", "g = alpha_algorithm + beta * overlap"])


def _figure(out_dir: Path, geo15: np.ndarray, labels: np.ndarray, group: np.ndarray, per_k: dict[str, Any],
            rows: list[dict[str, Any]], order: list, m1: dict[str, Any]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42, "ps.fonttype": 42})
    col = {"bibfs": "#0072B2", "biastar": "#56B4E9", "idastar": "#009E73", "jps": "#E69F00", "dijkstra_unit": "#D55E00"}
    mk = ["o", "s", "^"]
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2))
    jit = np.random.default_rng(7).uniform(-0.12, 0.12, size=15)
    for ax, k in zip(axes[:2], ("k15", "k10")):
        d = per_k[k]
        for i, ((a, j), r) in enumerate(zip(order, rows)):
            ax.scatter(r["primary"] + jit[i], d["g_alias"][f"{a}|{j}"], c=col[a], marker=mk[j], s=46,
                       edgecolor="k", linewidth=0.4, zorder=3)
        for a in AG.NONBANNED:
            xm = np.mean([r["primary"] for r in rows if r["algorithm"] == a])
            ax.scatter(xm, d["g_algorithm"][a], c=col[a], marker="*", s=330, edgecolor="k", linewidth=0.7, zorder=4,
                       alpha=0.85)
            ax.annotate(f"{AG.DISPLAY[a]} ({m1[k]['classes'][a].lower()})", (xm, d["g_algorithm"][a]),
                        xytext=(6, -3), textcoords="offset points", fontsize=7.5)
        ci = d["ci95_primary"]
        ax.set_title(f"{'A' if k == 'k15' else 'B'}. alias-level g at {k.replace('k', 'k = ')}: rho {d['rho_primary']:.2f}, "
                     f"exact p {d['primary_p_lower']:.3g}\n(template-bootstrap 95% CI {ci[0]:.2f} to {ci[1]:.2f}; "
                     f"5 centroids rho {d['five_centroid_primary']['rho']:.2f}, p {d['five_centroid_primary']['p_lower']:.3g})",
                     fontsize=8.5)
        ax.set_xlabel("primary lexical overlap with banned names (distinct detectors matched; jittered)")
        ax.set_ylabel("g: min over banned of mean geodesic (block 31)")
        ax.set_xticks([0, 1, 2, 3])
        ax.grid(alpha=0.3)
    Y, stress = AG.classical_mds(geo15)
    ax = axes[2]
    ban = np.isin(labels, AG.BANNED)
    ax.scatter(Y[ban, 0], Y[ban, 1], c="#BBBBBB", s=10, label="banned five (pooled)")
    for a in AG.NONBANNED:
        for j in range(3):
            ix = np.where((labels == a) & (group % 3 == j))[0]
            ax.scatter(Y[ix, 0], Y[ix, 1], c=col[a], marker=mk[j], s=16, edgecolor="k", linewidth=0.25,
                       label=f"{AG.DISPLAY[a]}" if j == 0 else None)
            hull = AG.convex_outline(Y[ix])
            ax.plot(hull[:, 0], hull[:, 1], color=col[a], lw=0.9, ls=["-", "--", ":"][j], alpha=0.8)
    ax.set_title(f"C. classical MDS of the stored k = 15 geodesics (300 forced prompts, block 31)\n"
                 f"stress-1 {stress:.2f}; outlines = 15 alias sets (line style = alias 0/1/2)", fontsize=8.5)
    ax.set_xlabel("MDS 1 (geodesic units)")
    ax.set_ylabel("MDS 2")
    ax.legend(fontsize=7, loc="best", markerscale=1.2)
    handles = [plt.Line2D([], [], marker=mk[j], ls="", color="k", label=f"alias {j}") for j in range(3)]
    axes[0].legend(handles=handles, fontsize=7, loc="upper right")
    fig.suptitle("Is iteration 8's 'opposite' landing a property of the alias-named manifold? (iteration-9 Step 0, "
                 "item 0e; stored geodesics of art_R-HSmXq2t97f, Qwen3-32B NF4)", fontsize=10)
    fig.tight_layout()
    fig.savefig(out_dir / "figures/alias_overlap.pdf")
    fig.savefig(out_dir / "figures/alias_overlap.png", dpi=160)
    plt.close(fig)
    per_k["k15"]["mds_stress1"] = stress
