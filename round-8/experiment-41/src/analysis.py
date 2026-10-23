#!/usr/bin/env python3
"""K3 analysis (CPU): validation statistics, generation statistics, the committed motif test (Gemma's file first),
stability (pair sets A vs B), K3 verdicts, figures, data/rows.jsonl and method_out.json (exp_gen_sol_out)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import k3motif as KM  # noqa: E402
from k3cfg import (DATA_DIR, FIG_DIR, PRED_DIR, RESULTS_DIR, read_json, read_jsonl, setup_logging,  # noqa: E402
                   utc_now, write_json, write_jsonl)

CONTRASTS = ("C1nat", "C1forced", "C1mix", "C1natB", "C2a")
GEMMA = ROOT / "inputs" / "exp38" / "results"


def load(name: str) -> dict[str, Any] | None:
    p = RESULTS_DIR / f"circuit_{name}.json"
    return read_json(p) if p.exists() else None


# ================================================================================================ motif
def motif_test() -> dict[str, Any]:
    g = read_json(GEMMA / "g1_pathpatch.json")
    gx = g["exact"]
    n_g = len(gx[0]["noise_per_pair"])
    # FIRST: the committed function on Gemma's file (FORK ~0.53, COND ~0.36 +- 0.02)
    g_all = KM.motif(gx, list(range(n_g)), class_map=KM.G2Q)
    ok = abs(g_all["DEC"] - 0.53) <= 0.02 and abs(g_all["COND"] - 0.36) <= 0.02
    out: dict[str, Any] = {"gemma_check": {"shares": g_all, "reproduces_printed": ok, "variant": "unsigned, all 60 "
                                           "exact nodes (top 40 by |AtP| + 20 random), 15 pairs"}}
    g_nat = KM.motif(gx, list(range(10)), class_map=KM.G2Q)
    g_forced = KM.motif(gx, list(range(10, 15)), class_map=KM.G2Q)
    inj = lambda kind, L, cl: cl == "COND" and L in (0, 1)  # noqa: E731
    g_inj = KM.motif(gx, list(range(n_g)), exclude=inj, class_map=KM.G2Q)
    g_depth = KM.dec_stack_depth(gx, list(range(n_g)), 15, 34, class_map=KM.G2Q)
    out["gemma"] = {"all15": g_all, "natural10": g_nat, "forced5": g_forced, "injection_excluded": g_inj,
                    "signed": KM.motif(gx, list(range(n_g)), signed=True, class_map=KM.G2Q),
                    "dec_stack": g_depth, "label_vs_bands": KM.label(g_all, g_depth["depth"])}
    q: dict[str, Any] = {}
    for name in ("C1nat", "C1forced", "C1mix", "C1natB", "C2a"):
        r = load(name)
        if r is None:
            continue
        ex = r["exact"]
        prim = [e for e in ex if e["in_top40_atp"] or e["calibration"]]
        idx = list(range(r["n_pairs"]))
        sh = KM.motif(prim, idx)
        dep = KM.dec_stack_depth(prim, idx, 15, 36)
        rec = {"n_nodes": len(prim), "shares": sh, "all80": KM.motif(ex, idx), "signed": KM.motif(prim, idx, signed=True),
               "injection_excluded": KM.motif(prim, idx, exclude=(inj if name != "C2a" else
                                                                 (lambda k, L, c: c == "SPEC" and L in (0, 1)))),
               "dec_stack": dep}
        if r.get("exact_extended"):
            pool = {}
            for e in r["exact"] + r.get("reliability_rows", []) + r["exact_extended"]:
                pool.setdefault(e["node"], e)
            top60 = sorted(pool.values(), key=lambda e: -abs(float(np.mean(e["noise_per_pair"]))))[:60]
            rec["extended_top60_by_exact"] = KM.motif(top60, idx)
            rec["extended_top60_dec_stack"] = KM.dec_stack_depth(top60, idx, 15, 36)
            rec["n_exact_noised_total"] = len(pool)
            mlp_cond = [e for e in pool.values() if e["node"].startswith("mlp") and e["node"].endswith("|COND")]
            rec["cond_mlp_effects"] = sorted([(e["node"], float(np.mean(e["noise_per_pair"]))) for e in mlp_cond],
                                             key=lambda t: -abs(t[1]))[:6]
        if name == "C2a":
            rec["note"] = ("C2a is an intervention-defined contrast: COND nodes have zero effect by construction, so C2a "
                           "is reported as a SPEC-to-decision routing map and excluded from the COND/SPEC share test")
        else:
            rec["label_vs_bands"] = KM.label(sh, dep["depth"])
        q[name] = rec
    out["qwen"] = q
    r5 = load("C1forced")
    if r5 is not None:
        prim5 = [e for e in r5["exact"] if e["in_top40_atp"] or e["calibration"]]
        out["qwen_C1forced_first5_pairs"] = KM.motif(prim5, list(range(min(5, r5["n_pairs"]))))
    prim_name = "C1mix" if "C1mix" in q else ("C1nat" if "C1nat" in q else None)
    if prim_name:
        out["primary_comparison"] = {"qwen_set": prim_name, "gemma_set": "all 15 pairs (10 natural + 5 forced)",
                                     "qwen": q[prim_name]["shares"], "gemma": g_all,
                                     "label": q[prim_name]["label_vs_bands"]["label"],
                                     "differs_on": q[prim_name]["label_vs_bands"]["differs_on"],
                                     "qwen_dec_depth": q[prim_name]["dec_stack"]["depth"],
                                     "gemma_dec_depth": g_depth["depth"]}
    return out


# ================================================================================================ stability
def stability() -> dict[str, Any] | None:
    a, b = load("C1nat"), load("C1natB")
    if a is None or b is None:
        return None

    def jac(x: list[str], y: list[str]) -> float:
        return len(set(x) & set(y)) / max(len(set(x) | set(y)), 1)
    ea = {e["node"]: e["noise_mean"] for e in a["exact"]}
    eb = {e["node"]: e["noise_mean"] for e in b["exact"]}
    union = sorted(set(a["top60_exact"]) | set(b["top60_exact"]))
    common = [k for k in union if k in ea and k in eb]
    from scipy.stats import spearmanr
    rho = float(spearmanr([ea[k] for k in common], [eb[k] for k in common]).statistic) if len(common) > 3 else None
    ka = {(e["sender"], e["receiver"]) for e in a.get("edges_kept", [])}
    kb = {(e["sender"], e["receiver"]) for e in b.get("edges_kept", [])}
    return {"jaccard_top10": jac(a["top10"], b["top10"]), "jaccard_top15": jac(a["top15"], b["top15"]),
            "spearman_exact_union_top60": rho, "n_union_measured_in_both": len(common),
            "class_shares_A": KM.motif([e for e in a["exact"] if e["in_top40_atp"] or e["calibration"]],
                                       list(range(a["n_pairs"]))),
            "class_shares_B": KM.motif([e for e in b["exact"] if e["in_top40_atp"] or e["calibration"]],
                                       list(range(b["n_pairs"]))),
            "edges_kept_both": sorted(["->".join(e) for e in ka & kb]), "n_edges_A": len(ka), "n_edges_B": len(kb),
            "P5_jaccard_ge_0.4": jac(a["top10"], b["top10"]) >= 0.4, "TE_A": a["TE_mean"], "TE_B": b["TE_mean"]}


# ================================================================================================ verdict
def verdict(val: dict[str, Any] | None, gen: dict[str, Any] | None) -> dict[str, Any]:
    if val is None:
        return {"verdict": "NOT RUN"}
    node_ok = val["n_pass_both_holm20"] >= 5
    pre = (gen or {}).get("PREFILL", {})
    gen_ok = bool(pre.get("criteria", {}).get("all", False))
    if node_ok and gen_ok:
        v = "PASS"
    elif node_ok != gen_ok:
        v = "PARTIAL"
    elif not val["any_node_passes_any_test"]:
        v = "DISCONFIRMED"
    else:
        v = "NOT SUPPORTED"
    gen_ok1 = bool(pre.get("criteria", {}).get("all_one_sided", False))
    if node_ok and gen_ok1:
        v1 = "PASS"
    elif node_ok != gen_ok1:
        v1 = "PARTIAL"
    elif not val["any_node_passes_any_test"]:
        v1 = "DISCONFIRMED"
    else:
        v1 = "NOT SUPPORTED"
    return {"verdict": v, "verdict_if_one_sided_mcnemar": v1, "node_criterion": node_ok,
            "n_nodes_pass_both": val["n_pass_both_holm20"],
            "generation_criterion": gen_ok, "generation_criteria": pre.get("criteria"),
            "mcnemar_top5_vs_rand5_p": pre.get("criteria", {}).get("mcnemar_top5_vs_rand5_p"),
            "mcnemar_top5_vs_rand5_p_one_sided": pre.get("criteria", {}).get("mcnemar_top5_vs_rand5_p_one_sided"),
            "rule": "PASS = >= 5 of 10 nodes pass both tests (Holm over 20) AND PREFILL top-5 meets all three "
                    "generation criteria; PARTIAL = exactly one; DISCONFIRMED = no top-10 node passes either test; "
                    "NOT SUPPORTED = neither criterion although some node passes one test"}


def gemma_recount() -> dict[str, Any]:
    """Gemma's G1 validation pass count under both multiplicity conventions, from its p_sign_flip values."""
    import k3stats as KS
    gv = read_json(GEMMA / "g1_validation.json")
    pn = gv["per_node"]
    pa = [r["p_sign_flip"] for r in pn["ablate"]]
    ps = [r["p_sign_flip"] for r in pn["steer"]]
    h20 = KS.holm(pa + ps)
    ha, hs = KS.holm(pa), KS.holm(ps)
    return {"within_test_holm": {"ablate": int(sum(p < 0.05 for p in ha)), "steer": int(sum(p < 0.05 for p in hs)),
                                 "both": int(sum(a < 0.05 and s < 0.05 for a, s in zip(ha, hs)))},
            "holm_over_20": {"ablate": int(sum(p < 0.05 for p in h20[:10])), "steer": int(sum(p < 0.05 for p in h20[10:])),
                             "both": int(sum(a < 0.05 and s < 0.05 for a, s in zip(h20[:10], h20[10:])))},
            "printed_n_node_claims": gv.get("n_node_claims")}


# ================================================================================================ figures
def figures(summary: dict[str, Any]) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42, "ps.fonttype": 42})
    made = []
    cls_x = {"COND": 0, "SPEC": 1, "OPEN": 2, "DEC": 3}

    def save(fig, stem: str) -> None:
        for ext in ("png", "pdf"):
            fig.savefig(FIG_DIR / f"{stem}.{ext}", dpi=170, bbox_inches="tight")
        plt.close(fig)
        made.append(stem)
    # circuit graphs
    for name in ("C1forced", "C2a", "C1nat", "C1natB"):
        r = load(name)
        if r is None or "edges_kept" not in r:
            continue
        fig, ax = plt.subplots(figsize=(7.5, 6.0))
        eff = {}
        for e in r["exact"] + r.get("reliability_rows", []) + r.get("exact_extended", []):
            eff.setdefault(e["node"], float(np.mean(e["noise_per_pair"])))
        top = r["top15"]
        coords = {}
        slot: dict[str, int] = {}
        for k in sorted(top, key=lambda k: int(k.split("|")[1][1:])):
            kind, L, H, cl = k.split("|")
            i = slot.get(cl, 0)
            slot[cl] = i + 1
            coords[k] = (cls_x[cl] - 0.3 + 0.2 * (i % 4), int(L[1:]))
        for e in r["edges_kept"]:
            if e["receiver"] == "logits(m)" or e["sender"] not in coords or e["receiver"] not in coords:
                continue
            (x0, y0), (x1, y1) = coords[e["sender"]], coords[e["receiver"]]
            ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                        arrowprops=dict(arrowstyle="->", lw=0.5 + 3 * abs(e["effect_mean"]) / max(r["TE_mean"], 1e-6),
                                        color="#c0392b" if e["effect_mean"] > 0 else "#2471a3", alpha=0.7))
        for k, (x, y) in coords.items():
            v = eff.get(k, 0.0)
            ax.scatter([x], [y], s=40 + 400 * abs(v) / max(r["TE_mean"], 1e-6),
                       c="#c0392b" if v > 0 else "#2471a3", marker="s" if k.startswith("mlp") else "o", alpha=0.8,
                       edgecolors="k", linewidths=0.4, zorder=3)
            ax.text(x + 0.05, y + 0.45, k.replace("|H-1", "").replace("head|", "").replace("mlp|", "MLP ")
                    .rsplit("|", 1)[0] + f" ({v:+.1f})", fontsize=5.5, zorder=4)
        lg = {e["sender"]: e["effect_mean"] for e in r.get("edges_all", []) if e["receiver"] == "logits(m)"}
        ax.set_xticks(range(4), list(cls_x))
        ax.set_ylabel("layer")
        ax.set_xlim(-0.6, 3.9)
        ax.set_ylim(-1, 36)
        ax.set_title(f"{name}: top-15 nodes (size = |noising effect| / TE) and kept edges\n"
                     f"TE {r['TE_mean']:.2f} nats; edge threshold {r.get('edge_threshold', 0):.2f}; "
                     f"{len(lg)} sender->logit edges measured", fontsize=8)
        save(fig, f"circuit_{name}")
    # AtP vs exact
    rs = [(n, load(n)) for n in ("C1nat", "C2a", "C1forced")]
    rs = [(n, r) for n, r in rs if r is not None and r.get("reliability_rows")]
    if rs:
        fig, axs = plt.subplots(1, len(rs), figsize=(4 * len(rs), 3.6))
        axs = np.atleast_1d(axs)
        for ax, (n, r) in zip(axs, rs):
            a = np.array([x for e in r["reliability_rows"] for x in e["atp_per_pair"]])
            b = np.array([x for e in r["reliability_rows"] for x in e["noise_per_pair"]])
            ax.scatter(a, b, s=4, alpha=0.4)
            lim = max(np.abs(a).max(), np.abs(b).max()) * 1.05
            ax.plot([-lim, lim], [-lim, lim], "k--", lw=0.6)
            st = r["atp_vs_exact_random160"]
            ax.set_title(f"{n}: Spearman {st['spearman']:.2f}, Pearson {st['pearson']:.2f}", fontsize=8)
            ax.set_xlabel("AtP estimate (nats)")
            ax.set_ylabel("exact noising effect (nats)")
        save(fig, "atp_vs_exact")
    # faithfulness
    rs = [(n, load(n)) for n in ("C1nat", "C2a", "C1forced")]
    rs = [(n, r) for n, r in rs if r is not None and r.get("faithfulness")]
    if rs:
        fig, axs = plt.subplots(1, len(rs), figsize=(4 * len(rs), 3.4))
        axs = np.atleast_1d(axs)
        for ax, (n, r) in zip(axs, rs):
            f = r["faithfulness"]
            for key, lab, col in (("type1", "frozen corrupt (type 1)", "#2471a3"),
                                  ("type2", "frozen class mean (type 2)", "#85c1e9"),
                                  ("completeness", "completeness (top-k noised)", "#c0392b"),
                                  ("sufficiency", "sufficiency (top-k denoised)", "#27ae60")):
                if f"{key}_mean" in f:
                    ax.errorbar(f["k"], f[f"{key}_mean"], yerr=f[f"{key}_sd"], marker="o", ms=3, capsize=2, label=lab,
                                color=col)
            ax.set_xscale("log")
            ax.set_xticks(f["k"], [str(k) for k in f["k"]])
            ax.minorticks_off()
            ax.axhline(1, color="k", lw=0.5, ls=":")
            ax.set_xlabel("top-k nodes")
            ax.set_ylabel("fraction of TE")
            ax.set_title(n, fontsize=9)
            ax.legend(fontsize=6)
        save(fig, "faithfulness")
    # validation distributions
    for name in ("C1forced", "C2a", "C1nat"):
        v = summary.get("validation", {}).get(name)
        if not v:
            continue
        fig, axs = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
        for ax, mode in zip(axs, ("ablate", "steer")):
            recs = v["per_node"][mode]
            data = [r["d_per_prompt"] for r in recs]
            ax.boxplot(data, showfliers=False)
            for i, r in enumerate(recs):
                ax.scatter(np.full(len(r["d_per_prompt"]), i + 1) + np.random.default_rng(i).normal(0, 0.06,
                           len(r["d_per_prompt"])), r["d_per_prompt"], s=4, alpha=0.5)
                ax.text(i + 1, ax.get_ylim()[1] if False else max(r["d_per_prompt"] + [0]) + 0.05,
                        f"{r['p_holm_20']:.0e}", fontsize=5, ha="center", rotation=90)
            ax.axhline(0, color="k", lw=0.5)
            ax.set_xticks(range(1, len(recs) + 1), [r["node"].replace("|H-1", "") for r in recs], rotation=70,
                          fontsize=6)
            ax.set_title(f"{name} {mode}: d = dm(node) - mean dm(50 matched random)", fontsize=8)
        axs[0].set_ylabel("oriented dm difference (nats)")
        save(fig, f"validation_{name}")
    # generation bars
    gens = summary.get("generation", {})
    if gens:
        fig, axs = plt.subplots(1, len(gens), figsize=(4.2 * len(gens), 3.4))
        axs = np.atleast_1d(axs)
        import k3stats as KS
        for ax, (name, g) in zip(axs, gens.items()):
            xs, labs = 0, []
            for cond, col in (("PREFILL", "#2c3e50"), ("FREE", "#95a5a6")):
                if cond not in g:
                    continue
                for arm in ("TWIN", "TOP5", "RAND5"):
                    a = g[cond]["arms"].get(arm)
                    if not a:
                        continue
                    k, n = a["correct_target"], a["n"]
                    lo, hi = KS.wilson(k, n)
                    ax.bar(xs, k / n, color=col, alpha=0.85)
                    ax.errorbar(xs, k / n, yerr=[[max(0.0, k / n - lo)], [max(0.0, hi - k / n)]], color="k", capsize=3)
                    labs.append(f"{cond[:4]}\n{arm}")
                    xs += 1
            ax.set_xticks(range(len(labs)), labs, fontsize=7)
            ax.set_ylabel("correct target-algorithm programs / N")
            ax.set_ylim(0, 1)
            ax.set_title(f"{name} generation (N = 30 CRN slots)", fontsize=8)
        save(fig, "generation")
    # dose response (post hoc)
    ds = summary.get("dose_sensitivity") or {}
    if ds:
        fig, axs = plt.subplots(1, len(ds), figsize=(4.2 * len(ds), 3.4))
        axs = np.atleast_1d(axs)
        for ax, (name, d) in zip(axs, ds.items()):
            lp = d.get("logit_p_minority_mean") or {}
            for arm, col in (("TOP5", "#c0392b"), ("RAND5", "#7f8c8d")):
                if arm in lp:
                    xs = sorted(float(k) for k in lp[arm])
                    ax.plot(xs, [lp[arm][str(x)] if str(x) in lp[arm] else lp[arm][f"{x}"] for x in xs], "o-",
                            color=col, label=f"{arm}: P(minority token) at DEC")
            gx = sorted(float(k) for k in d["doses"])
            gen = (summary.get("generation", {}).get(name, {}).get("PREFILL", {}).get("arms", {}))
            for arm, col in (("TOP5", "#c0392b"), ("RAND5", "#7f8c8d")):
                ys = [d["doses"][str(x)][f"{arm}_correct_target"] / d["doses"][str(x)]["n"] for x in gx]
                if arm in gen:
                    gx2, ys2 = gx + [2.0], ys + [gen[arm]["correct_target"] / gen[arm]["n"]]
                else:
                    gx2, ys2 = gx, ys
                ax.plot(gx2, ys2, "s--", color=col, alpha=0.7, label=f"{arm}: correct minority programs / 30")
            tw = d.get("logit_twin_p_minority_mean")
            if tw is not None:
                ax.axhline(tw, color="k", lw=0.6, ls=":", label="twin P(minority token)")
            ax.set_xscale("log", base=2)
            ax.set_xlabel("steering dose (committed: 2)")
            ax.set_ylim(0, 1.03)
            ax.set_title(f"{name}: post-hoc dose response", fontsize=8)
            ax.legend(fontsize=5.5)
        save(fig, "dose_response")
    # motif panel
    mt = summary.get("motif", {})
    if mt.get("qwen"):
        g = read_json(GEMMA / "g1_pathpatch.json")["exact"]
        qn = next(n for n in ("C1mix", "C1forced", "C1nat", "C2a") if n in mt["qwen"])
        r = load(qn)
        r5 = load("C1forced")
        ext = []
        if r5 is not None:
            pool = {}
            for e in r5["exact"] + r5.get("reliability_rows", []) + r5.get("exact_extended", []):
                pool.setdefault(e["node"], e)
            ext = sorted(pool.values(), key=lambda e: -abs(float(np.mean(e["noise_per_pair"]))))[:60]
        panels = [(g, "Gemma-3-4B-it G1 (depth l/33)", 34, KM.G2Q),
                  ([e for e in r["exact"] if e["in_top40_atp"] or e["calibration"]],
                   f"Qwen3-8B {qn}: committed composition (depth l/35)", 36, None)]
        if ext:
            panels.append((ext, "Qwen3-8B C1forced: top 60 of exhaustive sweep", 36, None))
        fig, axs = plt.subplots(1, len(panels), figsize=(4.5 * len(panels), 4), sharey=True)
        for ax, (rows, title, nl, cmap) in zip(axs, panels):
            mx = max(abs(float(np.mean(x["noise_per_pair"]))) for x in rows)
            for e in rows:
                kind, L, H, cl = e["node"].split("|")
                cl = (cmap or {}).get(cl, cl)
                v = float(np.mean(e["noise_per_pair"]))
                ax.scatter(cls_x[cl] + (0.2 if kind == "mlp" else -0.1), int(L[1:]) / (nl - 1), s=8 + 300 * abs(v) / mx,
                           c="#c0392b" if v > 0 else "#2471a3", marker="s" if kind == "mlp" else "o", alpha=0.6)
            ax.set_xticks(range(4), ["COND", "SPEC", "OPEN\n(CSTAR)", "DEC\n(FORK)"])
            ax.set_title(title, fontsize=8)
        axs[0].set_ylabel("normalised depth")
        save(fig, "motif_panel")
    # stability
    st = summary.get("stability")
    if st:
        a, b = load("C1nat"), load("C1natB")
        ea = {e["node"]: e["noise_mean"] for e in a["exact"]}
        eb = {e["node"]: e["noise_mean"] for e in b["exact"]}
        ks = [k for k in set(ea) & set(eb)]
        fig, ax = plt.subplots(figsize=(4, 3.6))
        ax.scatter([ea[k] for k in ks], [eb[k] for k in ks], s=6)
        ax.set_xlabel("exact noising effect, pair set A")
        ax.set_ylabel("pair set B")
        ax.set_title(f"stability: Jaccard top-10 {st['jaccard_top10']:.2f}, Spearman {st['spearman_exact_union_top60']}",
                     fontsize=7)
        save(fig, "stability")
    return made


# ================================================================================================ outputs
def method_out(summary: dict[str, Any]) -> dict[str, Any]:
    datasets = []
    from transformers import AutoTokenizer
    from k3cfg import model_path
    tok = AutoTokenizer.from_pretrained(model_path())
    import k3prompts as KP
    for name, unit in (("C1forced", "B3"), ("C2a", "T10")):
        raw = read_jsonl(DATA_DIR / f"gen_raw_{name}.jsonl")
        lab = {r["sid"]: r for r in read_jsonl(DATA_DIR / f"gen_labels_{name}.jsonl")}
        if not raw:
            continue
        twins = KP.b3_twins(tok) if unit == "B3" else KP.t10_twins(tok)
        ex = []
        for cond in ("PREFILL", "FREE"):
            for w in ("W1", "W2", "W3", "W4", "W5"):
                for k in range(6):
                    cell = {r["arm"]: r for r in raw if r["condition"] == cond and r["template"] == w and r["slot"] == k}
                    if not cell:
                        continue
                    e = {"input": tok.decode(twins[w]["ids"]) + (tok.decode(KP.b3_opening() if unit == "B3" else
                                                                           KP.t10_prefix()) if cond == "PREFILL" else ""),
                         "output": ("correct Prim's algorithm (prim_heap or prim_array) program" if unit == "B3" else
                                    "correct depth-first-search (dfs) program") + " = the steered minority target",
                         "metadata_contrast": name, "metadata_unit": unit, "metadata_condition": cond,
                         "metadata_template": w, "metadata_slot": k}
                    for arm in ("TWIN", "TOP5", "RAND5"):
                        r = cell.get(arm)
                        if r is None:
                            continue
                        L = lab.get(r["row_id"], {})
                        e[f"predict_{arm}"] = f"{L.get('label', 'unlabelled')}|{'pass' if L.get('passed') else 'fail'}"
                        e[f"metadata_{arm}_reached_decision"] = r.get("reached_decision")
                        e[f"metadata_{arm}_n_new_tokens"] = r.get("n_new_tokens")
                    ex.append(e)
        datasets.append({"dataset": f"{unit}_{'mst_weight' if unit == 'B3' else 'connected_components'}_"
                                    f"{name}_generation", "examples": ex})
    return {"metadata": {"method_name": "K3 circuit discovery and validation for the algorithm-choice decision token",
                         "model": "Qwen/Qwen3-8B@b968826d (bf16, thinking off)", "utc": utc_now(),
                         "baselines": "matched random components (50 per node, same type and position class, matched "
                                      "write norm); RAND5 matched random five in generation; TWIN unedited",
                         "summary": summary}, "datasets": datasets}


def rows_jsonl(summary: dict[str, Any]) -> int:
    """data/rows.jsonl in the shared per-sample schema (every generated program: generation arms and engine check)."""
    import hashlib
    gpu = "NVIDIA L4"
    out = []
    for name in ("C1forced", "C2a"):
        sel_p = RESULTS_DIR / f"selection_{name}.json"
        sel = read_json(sel_p) if sel_p.exists() else {}
        lab = {r["sid"]: r for r in read_jsonl(DATA_DIR / f"gen_labels_{name}.jsonl")}
        lab.update({r["sid"]: r for r in read_jsonl(DATA_DIR / f"gen_dose_labels_{name}.jsonl")})
        for r in read_jsonl(DATA_DIR / f"gen_raw_{name}.jsonl") + read_jsonl(DATA_DIR / f"gen_dose_raw_{name}.jsonl"):
            L = lab.get(r["row_id"], {})
            code = L.get("code") or ""
            nodes = (sel.get("gen_top5") if r["arm"] == "TOP5" else sel.get("rand5") if r["arm"] == "RAND5" else [])
            out.append({"model": "Qwen/Qwen3-8B@b968826d", "task": r["unit"], "arm": f"{r['arm']}|{r['condition']}",
                        "site": ";".join(nodes or []) or None, "layer": None, "rank_k": len(nodes or []) or None,
                        "dose": (r.get("dose") or 2.0) if r["arm"] != "TWIN" else 0.0, "temperature": 1.0,
                        "top_k": None,
                        "decision_pos": r.get("decision_pos"), "reached_decision": r.get("reached_decision"),
                        "template": r["template"], "noun": r.get("noun"), "slot": r["slot"], "precision": "bf16",
                        "gpu": gpu, "prompt_sha256": r.get("prompt_sha256"), "label": L.get("label"),
                        "labeller_source": L.get("labeller_source"), "passed": L.get("passed"),
                        "n_new_tokens": r.get("n_new_tokens"),
                        "code_sha256": hashlib.sha256(code.encode()).hexdigest() if code else None, "code": code,
                        "contrast": name, "row_id": r["row_id"]})
    lab = {r["sid"]: r for r in read_jsonl(DATA_DIR / "engine_check_labels.jsonl")}
    for r in read_jsonl(DATA_DIR / "engine_check_raw.jsonl"):
        L = lab.get(r["row_id"], {})
        code = L.get("code") or ""
        out.append({"model": "Qwen/Qwen3-8B@b968826d", "task": r["unit"], "arm": "TWIN|engine_check", "site": None,
                    "layer": None, "rank_k": None, "dose": 0.0, "temperature": 1.0, "top_k": None, "decision_pos": None,
                    "reached_decision": None, "template": r["template"], "noun": None, "slot": r["slot"],
                    "precision": "bf16", "gpu": gpu, "prompt_sha256": None, "label": L.get("label"),
                    "labeller_source": L.get("labeller_source"), "passed": L.get("passed"),
                    "n_new_tokens": len(r.get("token_ids") or []),
                    "code_sha256": hashlib.sha256(code.encode()).hexdigest() if code else None, "code": code,
                    "contrast": "engine_check", "row_id": r["row_id"]})
    write_jsonl(DATA_DIR / "rows.jsonl", out)
    return len(out)


def main() -> None:
    setup_logging("analysis")
    import method as M
    summary: dict[str, Any] = {"utc": utc_now()}
    summary["contrasts"] = read_json(RESULTS_DIR / "contrasts.json") if (RESULTS_DIR / "contrasts.json").exists() else None
    summary["circuits"] = {}
    for n in CONTRASTS:
        r = load(n)
        if r:
            summary["circuits"][n] = {k: r.get(k) for k in ("n_pairs", "TE_mean", "TE_sd", "screen",
                                                           "atp_vs_exact_random160", "ig_vs_exact_random160",
                                                           "atp_vs_exact_top", "top10", "top5", "top15",
                                                           "edge_threshold", "atp_class_mass")}
            summary["circuits"][n]["n_edges_kept"] = len(r.get("edges_kept", []))
            summary["circuits"][n]["edges_kept"] = [{k: e[k] for k in ("sender", "receiver", "effect_mean",
                                                                         "effect_sd")} for e in r.get("edges_kept", [])]
            if r.get("faithfulness"):
                summary["circuits"][n]["faithfulness"] = {k: v for k, v in r["faithfulness"].items()
                                                          if k.endswith("_mean") or k.endswith("_auc_logk") or k == "k"}
    summary["validation"] = {}
    for n in ("C1forced", "C2a", "C1nat"):
        if (DATA_DIR / f"validation_rows_{n}.jsonl").exists():
            summary["validation"][n] = M.validation_stats(n)
    summary["validation_sensitivity"] = {n: M.validation_sens_stats(n) for n in ("C1forced", "C2a")
                                         if (DATA_DIR / f"validation_sens_rows_{n}.jsonl").exists()}
    summary["generation"] = {}
    summary["U7_crn_determinism"] = {}
    for n in ("C1forced", "C2a"):
        if (DATA_DIR / f"gen_labels_{n}.jsonl").exists():
            summary["generation"][n] = M.gen_stats(n)
            raw = read_jsonl(DATA_DIR / f"gen_raw_{n}.jsonl")
            pre = {(r["arm"], r["template"], r["slot"]): r["token_ids"] for r in raw if r["condition"] == "PREFILL"}
            fr = [r for r in raw if r["condition"] == "FREE" and r.get("reached_decision")]
            same = sum(pre.get((r["arm"], r["template"], r["slot"])) == r["token_ids"] for r in fr)
            summary["U7_crn_determinism"][n] = {
                "free_rows_reaching_decision": len(fr), "identical_to_prefill_program": same,
                "note": "a FREE row that reproduces the opening must equal the PREFILL program of its slot (same CRN "
                        "uniforms, same edits); differences can only come from batch-composition bf16 noise"}
    summary["dose_sensitivity"] = {n: M.dose_stats(n) for n in ("C1forced", "C2a")
                                   if (DATA_DIR / f"gen_dose_raw_{n}.jsonl").exists()}
    summary["motif"] = motif_test()
    ov = {}
    names = [n for n in ("C1forced", "C2a", "C1nat") if load(n)]
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ta, tb = set(load(a)["top15"]), set(load(b)["top15"])
            strip = lambda ks: {k.rsplit("|", 1)[0] for k in ks}  # noqa: E731  (component identity, any class)
            ov[f"{a}_vs_{b}"] = {"shared_top15_nodes": sorted(ta & tb), "jaccard_top15": len(ta & tb) / len(ta | tb),
                                 "shared_components_any_class": sorted(strip(ta) & strip(tb))}
    summary["cross_contrast_overlap"] = ov
    summary["stability"] = stability()
    summary["gemma_recount"] = gemma_recount()
    summary["K3"] = {"C1_primary": verdict(summary["validation"].get("C1forced"),
                                           summary["generation"].get("C1forced")),
                     "C1_primary_contrast": "C1forced (amendment 0a: F2 triggered, C1-nat set A mean TE 0.89 < 1 nat)",
                     "C2a_replication": verdict(summary["validation"].get("C2a"), summary["generation"].get("C2a"))}
    for f in ("engine_check.json", "gpu_tests.json", "tests_cpu.json", "deviations.json", "memory_probe.json",
              "labeller_check.json", "novelty_audit.json", "positioning.json", "transcoder_precheck.json",
              "rederive.json", "contrasts.json"):
        p = RESULTS_DIR / f
        if p.exists():
            d = read_json(p)
            summary[f.replace(".json", "")] = ({k: v for k, v in d.items() if k != "rows"} if isinstance(d, dict) else d)
    summary["commit_chain"] = [l for l in (ROOT / "commitments.log").read_text().splitlines() if l.strip()]
    summary["stage_timing"] = read_jsonl(RESULTS_DIR / "stage_timing.jsonl")
    summary["gpu_seconds_total"] = float(sum(r["seconds"] for r in summary["stage_timing"]))
    summary["openrouter_usd"] = (summary.get("novelty_audit") or {}).get("usd", 0.0)
    flags = []
    for n, g in summary["generation"].items():
        for cond, gg in g.items():
            for arm, a in gg.get("arms", {}).items():
                if a.get("other_share", 0) > 0.2:
                    flags.append(f"{n} {cond} {arm}: other share {a['other_share']:.2f} > 0.2 (F9 adjudication)")
    summary["F9_other_flags"] = flags
    summary["n_rows_jsonl"] = rows_jsonl(summary)
    summary["figures"] = figures(summary)
    write_json(RESULTS_DIR / "summary.json", summary)
    mo = method_out(summary)
    write_json(ROOT / "method_out.json", mo)
    logger.info(f"K3: {summary['K3']}")


if __name__ == "__main__":
    main()
