#!/usr/bin/env python3
"""Analyses, decision rules, figures (F1-F7) and method_out.json for iteration 7 (CPU only)."""

from __future__ import annotations

import json
import math
from collections import Counter
from typing import Any

import numpy as np
from loguru import logger

from cfg import (DATA_DIR, DOSES, FIG_DIR, I6_DATA, I6_NATURAL, I6_RESULTS, PRED_DIR, RESULTS_DIR, ROOT, STATES_DIR,
                 SUBSPACE_DIR, TEMPLATE_IDS, TEMPS, read_json, read_jsonl, wilson_ci, write_json)


# ================================================================================================ helpers
def labels() -> dict[str, dict[str, Any]]:
    return {r["row_id"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl")}


def merged(raw_name: str) -> list[dict[str, Any]]:
    lab = labels()
    out = []
    for r in read_jsonl(DATA_DIR / raw_name):
        L = lab.get(r["row_id"])
        if L is None:
            continue
        out.append({**{k: v for k, v in r.items() if k not in ("token_ids",)}, "label": L["label"],
                    "passed": bool(L["passed"]), "code": L.get("code"), "token_ids": r["token_ids"]})
    return out


def mcnemar(b: int, c: int, alternative: str = "greater") -> float:
    from scipy.stats import binomtest

    n = b + c
    if n == 0:
        return 1.0
    return float(binomtest(b, n, 0.5, alternative=alternative).pvalue)


def holm(ps: list[float]) -> list[float]:
    m = len(ps)
    order = np.argsort(ps)
    adj = [0.0] * m
    run = 0.0
    for r, i in enumerate(order):
        run = max(run, (m - r) * ps[i])
        adj[i] = min(1.0, run)
    return adj


def cell_stats(rows: list[dict], target: str) -> dict[str, Any]:
    n = len(rows)
    att = sum(r["label"] == target for r in rows)
    cor = sum(r["label"] == target and r["passed"] for r in rows)
    pas = sum(r["passed"] for r in rows)
    return {"n": n, "attempted_target": att, "attempted_share": att / max(n, 1), "correct_target": cor,
            "correct_share": cor / max(n, 1), "pass_rate": pas / max(n, 1),
            "attempted_ci95": list(wilson_ci(att, n)), "labels": dict(Counter(r["label"] for r in rows))}


def paired(a: dict, b: dict, fn) -> tuple[int, int, int]:
    com = sorted(set(a) & set(b))
    x = sum(fn(a[s]) and not fn(b[s]) for s in com)
    y = sum(fn(b[s]) and not fn(a[s]) for s in com)
    return x, y, len(com)


# ================================================================================================ parts
def engine_check() -> dict[str, Any]:
    rows = merged("raw_engine.jsonl")
    i6lab = {r["row_id"]: r for r in read_jsonl(I6_DATA / "labels.jsonl") if r["row_id"].startswith("s3|T1|")}
    i6raw = {r["row_id"]: r for r in read_jsonl(I6_DATA / "raw_s3.jsonl") if r["row_id"].startswith("s3|T1|")}
    per, agree, ident, k6 = [], 0, 0, 0
    for r in rows:
        key = f"s3|T1|{r['template']}|twin|{r['slot']}"
        o = i6lab.get(key)
        orow = i6raw.get(key)
        same = orow is not None and orow["token_ids"] == r["token_ids"]
        per.append({"template": r["template"], "slot": r["slot"], "label": r["label"], "passed": r["passed"],
                    "iter6_label": o["label"] if o else None, "iter6_passed": o["passed"] if o else None,
                    "identical_program": same})
        agree += bool(o and o["label"] == r["label"])
        ident += same
        k6 += bool(o and o["label"] == "bfs")
    k = sum(r["label"] == "bfs" for r in rows)
    n = len(rows)
    lo, hi = I6_NATURAL["ci95"]
    return {"n": n, "bfs": k, "share": k / max(n, 1), "wilson95": list(wilson_ci(k, n)),
            "iter6_ci95_for_61_of_200": [lo, hi], "pass": bool(lo <= k / max(n, 1) <= hi),
            "iter6_share_on_same_50_slots": k6 / max(n, 1), "per_slot_label_agreement": agree / max(n, 1),
            "identical_program_share": ident / max(n, 1), "pass_rate": sum(r["passed"] for r in rows) / max(n, 1),
            "correct_bfs": sum(r["label"] == "bfs" and r["passed"] for r in rows), "per_slot": per,
            "note": "slots keyed with iteration 6's own slot_key ('iter5E', T1, W, k); B_CRN 25 here vs 20 there"}


def g1_generation() -> dict[str, Any]:
    rows = merged("raw_g1gen.jsonl")
    by: dict[str, dict] = {}
    for r in rows:
        by.setdefault(r["cell"], {})[(r["template"], r["slot"])] = r
    out = {"arms": {}, "tests": {}}
    for arm, d in by.items():
        tgt = "dfs" if arm.endswith("_dfs") else "bfs"
        out["arms"][arm] = cell_stats(list(d.values()), tgt)
    tw = by.get("twin", {})
    for arm, d in by.items():
        if arm == "twin":
            continue
        tgt = "dfs" if arm.endswith("_dfs") else "bfs"
        cor = lambda r, t=tgt: r["label"] == t and r["passed"]  # noqa: E731
        att = lambda r, t=tgt: r["label"] == t  # noqa: E731
        x, y, n = paired(d, tw, cor)
        xa, ya, _ = paired(d, tw, att)
        res = {"n_pairs": n, "correct_arm_only": x, "correct_twin_only": y, "p_correct_one_sided": mcnemar(x, y),
               "attempted_arm_only": xa, "attempted_twin_only": ya, "p_attempted_one_sided": mcnemar(xa, ya)}
        ctrl = arm.replace("top5", "rand5") if arm.startswith("top5") and "rand" not in arm else None
        if ctrl and ctrl in by:
            x2, y2, _ = paired(d, by[ctrl], cor)
            xa2, ya2, _ = paired(d, by[ctrl], att)
            res.update({"vs_random_arm": ctrl, "p_correct_vs_random": mcnemar(x2, y2),
                        "p_attempted_vs_random": mcnemar(xa2, ya2), "attempted_vs_random_counts": [xa2, ya2]})
        out["tests"][arm] = res
    return out


def g2_dose() -> dict[str, Any]:
    rows = merged("raw_g2dose.jsonl")
    by: dict[str, dict] = {}
    for r in rows:
        by.setdefault(r["cell"], {})[(r["template"], r["slot"])] = r
    tw = by.get("twin", {})
    twin_stats = cell_stats(list(tw.values()), "bfs")
    tf = read_json(RESULTS_DIR / "g2_dose_tf_pred.json") if (RESULTS_DIR / "g2_dose_tf_pred.json").exists() else {}
    cells = {}
    for name, d in by.items():
        if name == "twin":
            cells[name] = twin_stats
            continue
        parts = name.split("|")
        tgt = parts[1] if len(parts) > 1 and parts[1] in ("bfs", "dfs") else "bfs"
        st = cell_stats(list(d.values()), tgt)
        cor = lambda r, t=tgt: r["label"] == t and r["passed"]  # noqa: E731
        att = lambda r, t=tgt: r["label"] == t  # noqa: E731
        x, y, n = paired(d, tw, cor)
        xa, ya, _ = paired(d, tw, att)
        st.update({"target": tgt, "mcnemar_correct": [x, y], "p_correct_one_sided": mcnemar(x, y),
                   "mcnemar_attempted": [xa, ya], "p_attempted_one_sided": mcnemar(xa, ya)})
        if name in tf:
            st["tf_pred_attempted_bfs"] = float(np.mean([t["pred_attempted_bfs"] for t in tf[name]]))
            st["tf_mean_m"] = float(np.mean([t["m"] for t in tf[name]]))
        cells[name] = st
    if "twin" in tf:
        cells["twin"]["tf_pred_attempted_bfs"] = float(np.mean([t["pred_attempted_bfs"] for t in tf["twin"]]))
        cells["twin"]["tf_mean_m"] = float(np.mean([t["m"] for t in tf["twin"]]))
    knob = {}
    for meth in ("DAS", "DiM"):
        for Y in ("bfs", "dfs"):
            names = [f"{meth}|{Y}|{lam}" for lam in DOSES if f"{meth}|{Y}|{lam}" in cells]
            if not names:
                continue
            adj = holm([cells[n]["p_correct_one_sided"] for n in names])
            for n_, a in zip(names, adj):
                cells[n_]["p_correct_holm"] = a
            twin_target = sum(r["label"] == Y and r["passed"] for r in tw.values())
            ok = [n_ for n_ in names if cells[n_]["p_correct_holm"] < 0.05
                  and cells[n_]["pass_rate"] >= 0.8 * twin_stats["pass_rate"]]
            frontier = [n_ for n_ in names if cells[n_]["pass_rate"] >= 0.8 * twin_stats["pass_rate"]]
            best = max(frontier, key=lambda n_: cells[n_]["correct_target"]) if frontier else None
            collapse = [n_ for n_ in names if cells[n_]["pass_rate"] < 0.5 * twin_stats["pass_rate"]]
            knob[f"{meth}|{Y}"] = {"G2_KNOB": bool(ok) if Y == "bfs" else None, "doses_meeting_rule": ok,
                                   "twin_correct_target": twin_target,
                                   "frontier_best_correct_at_pass_ge_0.8x": best,
                                   "frontier_best_correct": cells[best]["correct_target"] if best else None,
                                   "cheapest_collapse_dose": collapse[0] if collapse else None}
    return {"cells": cells, "knob": knob, "twin": twin_stats}


def g2_decisions() -> dict[str, Any]:
    das = read_json(RESULTS_DIR / "g2_das.json")
    rinit = read_json(RESULTS_DIR / "g2_rinit.json") if (RESULTS_DIR / "g2_rinit.json").exists() else None
    Ls = str(das["L_star"])
    lay = das["layers"][Ls]
    out = {"L_star": das["L_star"], "k_star": das["k_star"], "per_k": {}}
    for k in ("1", "2", "4", "8"):
        rec = [lay["seeds"][sd]["per_k"][k]["recovery"].get("median", float("nan")) for sd in lay["seeds"]]
        das_rec = float(np.median(rec))
        rand_rec = lay["controls"]["RAND"][k]["median_recovery_median"]
        wil = lay["controls"]["WILCOXON_DAS_vs_RAND"].get(k, {})
        shuf = [v["heldout_true_targets"][k]["recovery"].get("median", float("nan"))
                for v in lay["controls"].get("SHUF", {}).values()]
        shuf_rec = float(np.median(shuf)) if shuf else None
        trained_eff = float(np.median([lay["seeds"][sd]["per_k"][k]["dy_dir_mean"] for sd in lay["seeds"]]))
        rinit_eff = rinit["seeds"]["0"]["per_k"][k]["dy_dir_mean"] if rinit and "seeds" in rinit else None
        real = bool(das_rec - rand_rec >= 0.4 and wil.get("p", 1.0) < 0.01 and shuf_rec is not None
                    and shuf_rec <= 0.1 and rinit_eff is not None and rinit_eff < 0.5 * trained_eff)
        out["per_k"][k] = {"das_recovery_seed_median": das_rec, "das_recovery_by_seed": rec, "rand_recovery": rand_rec,
                           "wilcoxon_p": wil.get("p"), "shuf_heldout_recovery_median": shuf_rec,
                           "trained_dy_dir_mean": trained_eff, "rinit_dy_dir_mean": rinit_eff,
                           "iia_seed_median": float(np.median([lay["seeds"][sd]["per_k"][k]["iia"] for sd in lay["seeds"]])),
                           "G2_DAS_REAL_at_k": real}
    out["G2_DAS_REAL"] = any(v["G2_DAS_REAL_at_k"] for v in out["per_k"].values())
    suff = [int(k) for k, v in out["per_k"].items() if v["das_recovery_seed_median"] >= 0.8]
    out["smallest_sufficient_rank"] = min(suff) if suff else None
    nat = lay["controls"]["NATURAL_VARIANCE"]
    out["natural_variance"] = nat
    out["dormant_flag"] = nat.get("dormant_flag")
    sp = nat["spearman_R1_coord_vs_yv"]
    out["one_dim_preconditions"] = {"k1_recovery_ge_0.8": out["per_k"]["1"]["das_recovery_seed_median"] >= 0.8,
                                    "abs_spearman_ge_0.5_p_lt_0.01": bool(abs(sp["rho"]) >= 0.5 and sp["p_perm"] < 0.01),
                                    "note": "the sign of R_1 is arbitrary, so |rho| is used"}
    out["dim_rank1"] = lay["controls"]["DiM_rank1_interchange"]
    out["second_layer"] = {}
    for L in das["layers"]:
        if L == Ls:
            continue
        lay2 = das["layers"][L]
        out["second_layer"][L] = {
            "per_k_recovery_seed_median": {k: float(np.median([lay2["seeds"][sd]["per_k"][k]["recovery"].get("median", float("nan"))
                                                               for sd in lay2["seeds"]])) for k in ("1", "2", "4", "8")},
            "per_k_dy_dir_seed_median": {k: float(np.median([lay2["seeds"][sd]["per_k"][k]["dy_dir_mean"] for sd in lay2["seeds"]]))
                                         for k in ("1", "2", "4", "8")},
            "rand_recovery": {k: lay2["controls"]["RAND"][k]["median_recovery_median"] for k in ("1", "2", "4", "8")},
            "dim_rank1_recovery": lay2["controls"]["DiM_rank1_interchange"]["recovery"].get("median"),
            "natural_variance_k1": lay2["controls"]["NATURAL_VARIANCE"]["1"],
            "spearman_R1_coord_vs_yv": lay2["controls"]["NATURAL_VARIANCE"]["spearman_R1_coord_vs_yv"],
            "seed_principal_cosines_k1": lay2.get("seed_principal_cosines_at_kstar")}
    out["seed_principal_cosines_at_kstar_Lstar"] = lay.get("seed_principal_cosines_at_kstar")
    out["full_state_dy_dir_mean_Lstar"] = None
    return out


def g1_extras() -> dict[str, Any]:
    """Natural-pair vs forced-pair top-20 overlap (Jaccard, among the exact-patched nodes), exact-effect mass by
    position class, and the cross-check against iteration 6's first-order SAE attribution nodes."""
    d = read_json(RESULTS_DIR / "g1_pathpatch.json")
    nat_idx = [i for i, p in enumerate(d["pairs"]) if not p["clean"].startswith("forced|")]
    frc_idx = [i for i, p in enumerate(d["pairs"]) if p["clean"].startswith("forced|")]
    rows = d["exact"]

    def top(idx: list[int], n: int = 20) -> set[str]:
        sc = [(abs(np.mean([r["noise_per_pair"][i] for i in idx])), r["node"]) for r in rows]
        return {k for _, k in sorted(sc, reverse=True)[:n]}
    tn, tf = top(nat_idx), top(frc_idx)
    mass = {}
    for r in rows:
        c = r["node"].split("|")[-1]
        mass[c] = mass.get(c, 0.0) + abs(r["noise_mean"])
    tot = sum(mass.values())
    i6 = read_json(I6_RESULTS / "attribution.json")
    i6_layers = sorted({n["layer"] for n in i6["nodes"]})
    fork_layers = sorted({int(r["node"].split("|")[1][1:]) for r in rows[:15] if r["node"].endswith("FORK")})
    return {"jaccard_top20_natural_vs_forced": len(tn & tf) / max(len(tn | tf), 1), "top20_natural": sorted(tn),
            "top20_forced": sorted(tf), "exact_effect_share_by_class": {k: v / tot for k, v in mass.items()},
            "iter6_first_order_nodes": [{"layer": n["layer"], "latent": n["latent"], "ablate_dy_mean": n["ablate_dy_mean"]}
                                        for n in i6["nodes"]],
            "iter6_site": "FORK (resid_post SAE latents)", "iter6_layers": i6_layers,
            "g1p_top15_fork_layers": fork_layers,
            "cross_check": "iteration 6's strongest first-order nodes sit at the FORK position at layers "
                           f"{i6_layers}; the G1-P top-15 FORK nodes sit at layers {fork_layers}"}


def timing() -> dict[str, Any]:
    st = read_jsonl(RESULTS_DIR / "stage_timing.jsonl")
    tb = read_jsonl(ROOT / "logs" / "timing_batches.jsonl")
    by: dict[str, float] = {}
    for r in st:
        by[r["stage"]] = by.get(r["stage"], 0.0) + float(r["seconds"])
    return {"seconds_by_stage": by, "n_generation_batches": len(tb),
            "generation_seconds_total": float(sum(r["seconds"] for r in tb)),
            "median_seconds_per_batch": float(np.median([r["seconds"] for r in tb])) if tb else None}


def costs() -> dict[str, Any]:
    tot = 0.0
    parts = {}
    for f in ("openrouter_cost_paths.json", "openrouter_cost_novelty.json"):
        p = RESULTS_DIR / f
        if p.exists():
            d = read_json(p)
            parts[f] = d
            tot += float(d.get("total_usd", 0.0))
    sp = read_jsonl(ROOT / "logs" / "openrouter_spend_s13.jsonl")
    s13 = float(sum(float(r.get("cost") or 0.0) for r in sp))
    return {"total_usd": tot + s13, "labeller_judge": parts, "novelty_and_regate_usd": s13}


# ================================================================================================ stages
def stage_novelty(args: Any) -> None:
    import novelty as NV

    NV.SPEND = ROOT / "logs" / "openrouter_spend_s13.jsonl"
    rows = []
    for f in sorted(DATA_DIR.glob("raw_*.jsonl")):
        rows += [dict(r, task="T1", arm=r.get("cell") or r.get("arm") or f.stem) for r in merged(f.name)]
    res = NV.audit(rows)
    reg = NV.regate([r for r in rows if r.get("code")], n=30)
    logger.info(f"novelty: {res['n_correct_other']} candidates; regate {reg['agree_judge_a']}/{reg['n']}, "
                f"{reg['agree_judge_b']}/{reg['n']}")


def stage_analysis(args: Any) -> None:
    import g3

    out = {}
    for name, fn in (("engine_check", engine_check), ("g3_sweep", g3.g3_analysis), ("g1_generation", g1_generation),
                     ("g2_dose", g2_dose), ("g2_decisions", g2_decisions), ("g1_extras", g1_extras),
                     ("timing", timing), ("costs", costs)):
        try:
            res = fn()
            if name not in ("g3_sweep",):
                write_json(RESULTS_DIR / f"{name}.json", res)
            out[name] = "ok"
        except (FileNotFoundError, KeyError, ValueError, ZeroDivisionError, TypeError) as e:
            logger.exception(f"analysis part {name} failed: {e}")
            out[name] = f"failed: {type(e).__name__}: {e}"
    write_json(RESULTS_DIR / "analysis_status.json", out)
    logger.info(f"analysis: {out}")


# ================================================================================================ figures
def _style() -> Any:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42,
                         "ps.fonttype": 42, "figure.dpi": 150, "savefig.bbox": "tight"})
    return plt


def _save(fig: Any, name: str) -> None:
    fig.savefig(FIG_DIR / f"{name}.png")
    fig.savefig(FIG_DIR / f"{name}.pdf")


def fig_graph(plt: Any) -> None:
    d = read_json(RESULTS_DIR / "g1_pathpatch.json")
    cls_x = {"COND": 0, "SPEC": 1, "CSTAR": 2, "FORK": 3, "logits(m)": 4}
    eff = {r["node"]: r["noise_mean"] for r in d["exact"]}
    nodes = set()
    for e in d["edges_kept"]:
        nodes.add(e["sender"])
        nodes.add(e["receiver"])
    nodes |= set(d["top10"])

    def xy(n: str) -> tuple[float, float]:
        if n == "logits(m)":
            return 4.0, 35.0
        kind, L, H, c = n.split("|")
        l = int(L[1:])
        dx = 0.18 if kind == "mlp" else -0.18 + 0.03 * int(H[1:])
        return cls_x[c] + dx, l + (0.5 if kind == "mlp" else 0.0)
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    for e in d["edges_kept"]:
        (x0, y0), (x1, y1) = xy(e["sender"]), xy(e["receiver"])
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="-|>", lw=0.6 + 3 * abs(e["dm_mean"]) /
                                                                     max(abs(x["dm_mean"]) for x in d["edges_kept"]),
                                                                     color="#c0392b" if e["dm_mean"] > 0 else "#2471a3", alpha=0.7))
    for n in nodes:
        x, y = xy(n)
        if n == "logits(m)":
            ax.scatter([x], [y], s=160, marker="s", color="black")
            ax.text(x + 0.08, y, "m (fork margin)", va="center", fontsize=8)
            continue
        v = eff.get(n, 0.0)
        ax.scatter([x], [y], s=40 + 60 * min(abs(v), 4), marker="o" if n.startswith("mlp") else "^",
                   color="#c0392b" if v > 0 else "#2471a3", edgecolor="black", lw=0.5, zorder=3)
        ax.text(x + 0.07, y, n.replace("|H-1", "").replace("|", " ").replace("mlp", "MLP"), fontsize=6, va="center")
    ax.set_xticks(list(cls_x.values()))
    ax.set_xticklabels(["COND (condition)", "SPEC (task spec)", "CSTAR (c*[0..30])", "FORK (p_f)", "logits"])
    ax.set_ylabel("layer")
    ax.set_ylim(-1, 36.5)
    ax.set_title("F1. G1-P path-patching graph at the fork (edges kept: |dm| >= 5% of the total effect)\n"
                 "node size = exact noising effect (nats); red = pushes toward BFS; circles = MLPs, triangles = heads",
                 fontsize=8)
    _save(fig, "F1_g1_graph")
    plt.close(fig)


def fig_validation(plt: Any) -> None:
    v = read_json(RESULTS_DIR / "g1_validation.json")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), sharey=False)
    fig.subplots_adjust(wspace=0.3)
    for ax, mode in zip(axes, ("ablate", "steer")):
        recs = v["per_node"][mode]
        for i, r in enumerate(recs):
            d = np.array(r["d_per_prompt"])
            ax.scatter(np.full(len(d), i) + np.random.default_rng(i).uniform(-0.15, 0.15, len(d)), d, s=8,
                       color="#c0392b" if r["NODE_CLAIM"] else "#7f8c8d", alpha=0.8)
            ax.plot([i - 0.3, i + 0.3], [np.median(d)] * 2, color="black", lw=1.2)
        ax.axhline(0, color="black", lw=0.6, ls=":")
        ax.set_xticks(range(len(recs)))
        ax.set_xticklabels([r["node"].replace("|H-1", "").replace("mlp", "MLP") for r in recs], rotation=60, ha="right",
                           fontsize=6)
        ax.set_ylabel("d_i = dm(node) - mean dm(50 matched random)\n(oriented toward the opposite class, nats)")
        ax.set_title(f"F2 ({mode.upper()}): 20 twin variants per node vs matched null\nred = NODE CLAIM; bar = median",
                     fontsize=8)
    _save(fig, "F2_g1_validation")
    plt.close(fig)


def fig_das(plt: Any) -> None:
    das = read_json(RESULTS_DIR / "g2_das.json")
    dec = read_json(RESULTS_DIR / "g2_decisions.json")
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4))
    fig.subplots_adjust(wspace=0.55)
    ceil = das["full_state_ceiling_by_layer"]
    Ls = sorted(int(k) for k in ceil)
    axes[0].plot(Ls, [ceil[str(L)]["dy_full_bfs_src_mean"] for L in Ls], "o-", color="#c0392b", label="BFS sources")
    axes[0].plot(Ls, [ceil[str(L)]["dy_full_dfs_src_mean"] for L in Ls], "o-", color="#2471a3", label="DFS sources")
    sc = das["layer_scan"]["by_layer"]
    ax2 = axes[0].twinx()
    ax2.plot([int(k) for k in sc], [sc[k]["cv_median_recovery"] for k in sc], "s--", color="#27ae60",
             label="rank-1 DAS train-CV recovery")
    ax2.set_ylabel("rank-1 recovery (train CV)", color="#27ae60")
    axes[0].set_xlabel("layer L (interchange at p_f)")
    axes[0].set_ylabel("full-state interchange dy (nats, held-out)")
    axes[0].axhline(0, color="black", lw=0.5)
    axes[0].legend(fontsize=7, loc="upper left")
    axes[0].set_title(f"F3a. Ceiling by layer; L* = {das['L_star']}", fontsize=8)
    ks = [1, 2, 4, 8]
    pk = dec["per_k"]
    axes[1].plot(ks, [pk[str(k)]["das_recovery_seed_median"] for k in ks], "o-", color="#c0392b", label="DAS (seed median)")
    for sd in range(3):
        axes[1].plot(ks, [pk[str(k)]["das_recovery_by_seed"][sd] if sd < len(pk[str(k)]["das_recovery_by_seed"]) else np.nan
                          for k in ks], ".", color="#c0392b", alpha=0.4)
    axes[1].plot(ks, [pk[str(k)]["rand_recovery"] for k in ks], "o-", color="#7f8c8d", label="RAND (50 Haar subspaces)")
    axes[1].plot(ks, [pk[str(k)]["shuf_heldout_recovery_median"] for k in ks], "o-", color="#8e44ad",
                 label="SHUF (true held-out targets)")
    dim = dec["dim_rank1"]["recovery"].get("median")
    axes[1].scatter([1], [dim], marker="*", s=120, color="#f39c12", label="DiM (rank-1)", zorder=4)
    r_tr = [pk[str(k)]["trained_dy_dir_mean"] for k in ks]
    r_ri = [pk[str(k)]["rinit_dy_dir_mean"] for k in ks]
    if all(x is not None for x in r_ri):
        axes[1].plot(ks, [a / b if b else np.nan for a, b in zip(r_ri, r_tr)], "x--", color="black",
                     label="RINIT effect / trained effect")
    axes[1].set_xscale("log", base=2)
    axes[1].set_xticks(ks)
    axes[1].set_xticklabels(ks)
    axes[1].axhline(0.8, color="black", lw=0.5, ls=":")
    axes[1].set_xlabel("rank k")
    axes[1].set_ylabel("held-out recovery = dy_DAS / dy_full (median)")
    axes[1].legend(fontsize=6)
    axes[1].set_title(f"F3b. Held-out recovery at L* (W4/W5 x F4/F5)", fontsize=8)
    _save(fig, "F3_g2_das")
    plt.close(fig)


def fig_geometry(plt: Any) -> None:
    import torch

    das = read_json(RESULTS_DIR / "g2_das.json")
    L = int(das["L_star"])
    R = torch.load(SUBSPACE_DIR / f"das_L{L}_seed0.pt").float()[:, :2]
    u = torch.load(SUBSPACE_DIR / f"dim_L{L}.pt").float()
    V = torch.load(STATES_DIR / "fork_variants.pt")
    S = torch.load(STATES_DIR / "fork_sources.pt")
    Hv = torch.stack([v["h"][L] for v in V]).float()
    Hs = torch.stack([s["h"][L] for s in S]).float()
    pv = (Hv @ R).numpy()
    ps = (Hs @ R).numpy()
    yv = np.array([v["y"] for v in V])
    fig, ax = plt.subplots(figsize=(6.4, 5.2))
    sc = ax.scatter(pv[:, 0], pv[:, 1], c=yv, cmap="coolwarm", s=18, edgecolor="black", lw=0.3,
                    label="120 twin variants (colour = y_v)")
    plt.colorbar(sc, ax=ax, label="y_v = fork margin (nats)")
    mb = np.array([s["mode"] == "bfs" for s in S])
    ax.scatter(ps[mb, 0], ps[mb, 1], marker="^", s=40, color="#c0392b", edgecolor="black", lw=0.4, label="forced-BFS sources")
    ax.scatter(ps[~mb, 0], ps[~mb, 1], marker="v", s=40, color="#2471a3", edgecolor="black", lw=0.4, label="forced-DFS sources")
    c0 = pv.mean(0)
    ud = (u @ R).numpy()
    tb = ps[mb].mean(0)
    scale = 0.5 * float(np.linalg.norm(tb - c0)) / max(float(np.linalg.norm(ud)), 1e-9)
    ax.annotate("", xy=(c0[0] + ud[0] * scale, c0[1] + ud[1] * scale), xytext=(c0[0], c0[1]),
                arrowprops=dict(arrowstyle="-|>", color="#f39c12", lw=1.8))
    ax.text(c0[0] + ud[0] * scale, c0[1] + ud[1] * scale, f"  DiM (|proj| = {np.linalg.norm(ud):.2f} of a unit vector)",
            color="#f39c12", fontsize=6)
    for lam in DOSES:
        q = c0 + lam * (tb - c0)
        ax.scatter([q[0]], [q[1]], s=10, color="black")
    ax.plot([c0[0], tb[0]], [c0[1], tb[1]], color="black", lw=0.6, ls="--", label="DAS dose path (lambda 0.1..1)")
    ax.set_xlabel(f"R_1 coordinate (layer {L}, p_f)")
    ax.set_ylabel(f"R_2 coordinate (layer {L}, p_f)")
    ax.legend(fontsize=6, loc="best")
    ax.set_title("F4. Fork states in the DAS plane (actual activation coordinates); orange arrow = DiM direction",
                 fontsize=8)
    _save(fig, "F4_g2_geometry")
    plt.close(fig)


def fig_dose(plt: Any) -> None:
    d = read_json(RESULTS_DIR / "g2_dose.json")
    c = d["cells"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, Y in zip(axes, ("bfs", "dfs")):
        for meth, col in (("DAS", "#c0392b"), ("DiM", "#f39c12")):
            xs = [lam for lam in DOSES if f"{meth}|{Y}|{lam}" in c]
            if not xs:
                continue
            tag = " (one strong edit, D17)" if (meth == "DiM" and Y == "dfs") else ""
            ax.plot(xs, [c[f"{meth}|{Y}|{lam}"]["attempted_share"] for lam in xs], "o-", color=col,
                    label=f"{meth} attempted {Y.upper()}{tag}")
            ax.plot(xs, [c[f"{meth}|{Y}|{lam}"]["correct_share"] for lam in xs], "s--", color=col,
                    label=f"{meth} correct {Y.upper()}")
            ax.plot(xs, [c[f"{meth}|{Y}|{lam}"]["pass_rate"] for lam in xs], ":", color=col, label=f"{meth} pass rate")
        tw = c.get("twin", {})
        tgt_tw = (tw.get("labels", {}).get(Y, 0)) / max(tw.get("n", 1), 1)
        ax.axhline(tgt_tw, color="black", lw=0.8, label=f"twin attempted {Y.upper()}")
        ax.axhline(tw.get("pass_rate", np.nan), color="gray", lw=0.8, ls=":", label="twin pass rate")
        if Y == "bfs" and "forced_bfs_F5" in c:
            ax.axhline(c["forced_bfs_F5"]["correct_share"], color="#27ae60", lw=0.8, ls="--",
                       label="forced-BFS prompt (correct)")
        if Y == "bfs" and "DAS-L|bfs|1.0" in c:
            ax.scatter([1.0], [c["DAS-L|bfs|1.0"]["correct_share"]], marker="*", s=90, color="#8e44ad",
                       label="DAS logit-only (correct)", zorder=4)
        ax.set_xlabel("dose lambda")
        ax.set_title(f"F5. Dose sweep toward {Y.upper()} (N = 50 per cell, CRN)", fontsize=8)
        ax.legend(fontsize=5.5)
    axes[0].set_ylabel("share of N")
    _save(fig, "F5_g2_dose")
    plt.close(fig)


def fig_temperature(plt: Any) -> None:
    g = read_json(RESULTS_DIR / "g3_sweep.json")
    c = g["cells"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    for smp, col in (("topp1", "#c0392b"), ("topk10", "#2471a3")):
        xs = [T for T in TEMPS if f"T{T}|{smp}" in c]
        obs = [c[f"T{T}|{smp}"]["attempted_share"] for T in xs]
        lo = [c[f"T{T}|{smp}"]["ci95"][0] for T in xs]
        hi = [c[f"T{T}|{smp}"]["ci95"][1] for T in xs]
        pr = [c[f"T{T}|{smp}"]["pred_primary"] for T in xs]
        axes[0].errorbar(np.array(xs) + (0.01 if smp == "topk10" else 0), obs,
                         yerr=[np.array(obs) - lo, np.array(hi) - obs], fmt="o", color=col, label=f"observed ({smp})")
        axes[0].plot(xs, pr, "--", color=col, label=f"committed prediction ({smp})")
    axes[0].set_xlabel("temperature T")
    axes[0].set_ylabel("attempted BFS share (N = 50, Wilson 95%)")
    axes[0].set_title("F6. Fork-margin account of temperature: predicted vs observed", fontsize=8)
    axes[0].legend(fontsize=6)
    Ts = [float(t) for t in g["H_by_T"]]
    axes[1].plot(Ts, [g["H_by_T"][str(t)] if str(t) in g["H_by_T"] else g["H_by_T"][t] for t in g["H_by_T"]], "o-",
                 color="black")
    axes[1].axhline(0.3, color="#c0392b", ls=":", lw=0.8, label="G3-CONC threshold 0.3 bits")
    axes[1].set_xlabel("temperature T")
    axes[1].set_ylabel("H(label | fork class) (bits)")
    axes[1].set_title(f"F7. Label entropy given the fork-token class (pooled {g['H_label_given_fork_pooled_bits']:.3f} bits)",
                      fontsize=8)
    axes[1].legend(fontsize=6)
    _save(fig, "F6_F7_g3_temperature")
    plt.close(fig)


def stage_figures(args: Any) -> None:
    plt = _style()
    for name, fn in (("F1", fig_graph), ("F2", fig_validation), ("F3", fig_das), ("F4", fig_geometry), ("F5", fig_dose),
                     ("F6F7", fig_temperature)):
        try:
            fn(plt)
            logger.info(f"figure {name} ok")
        except (FileNotFoundError, KeyError, ValueError, TypeError, IndexError, RuntimeError) as e:
            logger.exception(f"figure {name} failed: {e}")


# ================================================================================================ outputs
def _lp(r: dict | None) -> str:
    if r is None:
        return "missing"
    return f"{r['label']}|{'pass' if r['passed'] else 'fail'}"


def _slug(x: Any) -> str:
    return str(x).replace(".", "p").replace("-", "_").replace("|", "_").replace(" ", "_")


def stage_outputs(args: Any) -> None:
    import fork7 as FK

    datasets = []
    twin_text = {w: FK.twin(w)["text"] for w in TEMPLATE_IDS}
    # engine check
    eng = read_json(RESULTS_DIR / "engine_check.json")
    rows = {(r["template"], r["slot"]): r for r in merged("raw_engine.jsonl")}
    ex = []
    for p in eng["per_slot"]:
        r = rows.get((p["template"], p["slot"]))
        ex.append({"input": twin_text[p["template"]], "output": _lp(r),
                   "predict_iter6": f"{p['iter6_label']}|{'pass' if p['iter6_passed'] else 'fail'}",
                   "metadata_template": p["template"], "metadata_slot": p["slot"],
                   "metadata_identical_program": p["identical_program"],
                   "metadata_program": (r or {}).get("code") or ""})
    datasets.append({"dataset": "engine_check", "examples": ex})
    # U6
    u6 = {r["row_id"]: r for r in merged("raw_u6.jsonl")}
    import fork as F

    ex = []
    for w in TEMPLATE_IDS:
        for k in range(40):
            a, b = u6.get(f"u6a|{w}|{k}"), u6.get(f"u6b|{w}|{k}")
            if not (a and b):
                continue
            ex.append({"input": twin_text[w], "output": _lp(b), "predict_u6a_multi_prompt_full_labeller": _lp(a),
                       "predict_u6a_multi_prompt_partial_labeller": F.partial_label(a["text"]) or "other",
                       "metadata_template": w, "metadata_slot": k, "metadata_fork_token_b": b.get("fork_token"),
                       "metadata_fork_token_a": a.get("fork_token")})
    datasets.append({"dataset": "u6_calibration", "examples": ex})
    # G3-cal
    tt6 = FK.token_table()
    ex = [{"input": twin_text[r["template"]] + " [prefilled: c* + forced fork token]", "output": _lp(r),
           "predict_iter6_fork_token_table": "bfs" if (tt6.get(int(r["forced_fork_token"]), {}).get("p_bfs") or 0) >= 0.5
           else "dfs",
           "metadata_forced_fork_token": r["forced_fork_token"], "metadata_template": r["template"],
           "metadata_slot": r["slot"], "metadata_program": r.get("code") or ""} for r in merged("raw_g3cal.jsonl")]
    if ex:
        datasets.append({"dataset": "g3_calibration_fork_token", "examples": ex})
    # G1 nodes
    if (RESULTS_DIR / "g1_validation.json").exists():
        v = read_json(RESULTS_DIR / "g1_validation.json")
        ex = []
        for mode, recs in v["per_node"].items():
            for r in recs:
                ex.append({"input": f"{mode} node {r['node']} on 20 twin variants (teacher-forced fork margin)",
                           "output": f"{r['mean_dm_node_oriented']}",
                           "predict_random_null": f"{(r['mean_dm_node_oriented'] or 0) - (r['mean_d'] or 0)}",
                           "metadata_mode": mode, "metadata_node": r["node"], "metadata_p_holm": r["p_holm"],
                           "metadata_node_claim": r["NODE_CLAIM"], "metadata_d_per_prompt": r["d_per_prompt"]})
        datasets.append({"dataset": "g1_nodes", "examples": ex})
    # G1 generation
    g1 = merged("raw_g1gen.jsonl")
    if g1:
        by = {}
        for r in g1:
            by.setdefault((r["template"], r["slot"]), {})[r["cell"]] = r
        ex = []
        for (w, k), arms in sorted(by.items()):
            e = {"input": twin_text[w] + " [prefilled: c*]", "output": _lp(arms.get("twin")),
                 "metadata_template": w, "metadata_slot": k}
            for arm, r in arms.items():
                if arm != "twin":
                    e[f"predict_{_slug(arm)}"] = _lp(r)
            ex.append(e)
        datasets.append({"dataset": "g1_generation", "examples": ex})
    # G2 teacher-forced held-out pairs
    if (RESULTS_DIR / "g2_pairs.json").exists():
        gp = read_json(RESULTS_DIR / "g2_pairs.json")
        ex = []
        for row in gp["rows"]:
            e = {"input": f"base {row['base']} <- source {row['source']} at layer {gp['L']}, p_f",
                 "output": f"{row['dy_full']:.4f}", "metadata_source_class": row["source_class"]}
            for k, v in row["pred"].items():
                e[f"predict_{_slug(k)}"] = f"{v:.4f}"
            ex.append(e)
        datasets.append({"dataset": "g2_teacher_forced", "examples": ex})
    # G2 dose sweep
    g2 = merged("raw_g2dose.jsonl")
    if g2:
        by = {}
        for r in g2:
            by.setdefault((r["template"], r["slot"]), {})[r["cell"]] = r
        ex = []
        for (w, k), cells in sorted(by.items()):
            e = {"input": twin_text[w] + " [prefilled: c*; one edit at (L*, p_f)]", "output": _lp(cells.get("twin")),
                 "metadata_template": w, "metadata_slot": k}
            for cell, r in cells.items():
                if cell != "twin":
                    e[f"predict_{_slug(cell)}"] = _lp(r)
            ex.append(e)
        datasets.append({"dataset": "g2_dose_sweep", "examples": ex})
    # G3 temperature
    g3r = merged("raw_g3.jsonl")
    if g3r:
        preds = read_json(RESULTS_DIR / "g3_predictions.json")
        by = {}
        for r in g3r:
            by.setdefault((r["sampler"], r["template"], r["slot"]), {})[r["T"]] = r
        ex = []
        for (smp, w, k), Ts in sorted(by.items()):
            e = {"input": twin_text[w] + f" [natural sampling, sampler {smp}]", "output": _lp(Ts.get(1.0)),
                 "metadata_sampler": smp, "metadata_template": w, "metadata_slot": k,
                 "metadata_predicted_bfs_share_by_T": {str(T): preds["cells"][f"T{T}|{smp}"]["pred_bfs_primary"]
                                                       for T in TEMPS}}
            for T, r in Ts.items():
                if T != 1.0:
                    e[f"predict_T{_slug(T)}"] = _lp(r)
                    e[f"metadata_fork_token_T{_slug(T)}"] = r.get("fork_token")
            ex.append(e)
        datasets.append({"dataset": "g3_temperature", "examples": ex})
    meta = {"method_name": "Circuit and dose dial at Gemma's BFS-vs-DFS fork (iteration 7)",
            "model": "google/gemma-3-4b-it@093f9f388b31de276ce2de164bdc2081324b9767 (bf16)",
            "results": {}}
    for f in sorted(RESULTS_DIR.glob("*.json")):
        if f.name in ("g1_validation_rows.json",) or f.stat().st_size > 3_000_000:
            meta["results"][f.stem] = {"omitted_here": f"see results/{f.name} ({f.stat().st_size} bytes)"}
            continue
        meta["results"][f.stem] = read_json(f)
    out = {"metadata": meta, "datasets": [d for d in datasets if d["examples"]]}
    write_json(ROOT / "method_out.json", out, indent=None)
    logger.info(f"method_out.json: {len(out['datasets'])} datasets, "
                f"{sum(len(d['examples']) for d in out['datasets'])} examples")
    _ = (PRED_DIR, I6_RESULTS, math)
