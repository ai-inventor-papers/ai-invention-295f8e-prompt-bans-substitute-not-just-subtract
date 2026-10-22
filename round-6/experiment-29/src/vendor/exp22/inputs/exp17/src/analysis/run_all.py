#!/usr/bin/env python3
"""S9/S10: run every CPU analysis, render figures, write method_out.json (exp_gen_sol_out) and the audit."""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

import numpy as np
from loguru import logger

from analysis.c2d import run_c2d
from analysis.c2f import run_c2f
from analysis.common import merged
from analysis.sae_report import run_sae_report
from cfg import (DATA_DIR, DEFAULT, FIG_DIR, PRED_DIR, QUANT, RESULTS_DIR, ROOT, SAMPLED_TASKS, read_json,
                 read_jsonl, utc_now, write_json)

DEVIATIONS = [
    {"id": "D1", "what": "FP8 W8A8-dynamic quantisation (E4M3, per-output-channel weight scales, per-token activation "
                         "scales; lm_head/embeddings/norms bf16) of the pinned bf16 Qwen3-8B weights",
     "why": "the GPU is a 16 GB RTX 2000 Ada (plan: 20 GB A4500); bf16 weights need 16.4 GB. F2 named bitsandbytes "
            "8-bit only because it assumed a GPU without FP8; no C compiler is available for Triton kernels",
     "check": "U7: T2 ban 2/20 Dijkstra (<= 6/20 required), twin 20/20 (>= 17/20 required) with exp8's prompts and "
              "uniform keys"},
    {"id": "D2", "what": "batches of 20 rows (two 10-slot blocks of the same task and template, or one 20-slot block)",
     "why": "throughput; every batch in every arm has the same shape, so CRN coupling stays exact (U1, U2a, U2d)"},
    {"id": "D3", "what": "N=50 arms without a natural batch partner get the slots k 10-19 as extra rows (SUB_plain on "
                         "all tasks; ADD alpha 1 when ADD alpha 0.5 ran)", "why": "filling the constant batch shape"},
    {"id": "D4", "what": "analysis code hash-committed at commit #2 (before any ban sample) instead of commit #1",
     "why": "time; the decision rules were committed verbatim at commit #1"},
    {"id": "D5", "what": "U3 criterion: aligned teacher-forced vs sampling states differ by <= 15% (max) and the mean "
                         "aligned difference is < 1/4 of the off-by-one difference",
     "why": "FP8 decode and prefill use different GEMM shapes, so the same state differs by a few % (aligned mean 5.2% "
            "vs 82% off by one); the test confirms the position convention"},
    {"id": "D6", "what": "judge cap raised from USD 0.20 to 0.40", "why": "T2 ban programs often leave both mechanical "
                                                                           "labellers unresolved"},
    {"id": "D7", "what": "clean twin states for the ADD/RAND/SUB_affine hooks are recomputed at sampling time from a "
                         "clean prefill (identical prompt and engine) instead of being stored on disk",
     "why": "equivalent and cheaper; U2a shows alpha=0 reproduces the clean twin exactly"},
    {"id": "D8", "what": "0g uses 100 sequences per corpus (25 per exp12 group) and base outputs capped at 512 new "
                         "tokens", "why": "time; the base model runs in a separate load"},
    {"id": "D9", "what": "5c H1 null uses 100 coordinate permutations (plan: 500) and figures are rendered with "
                         "matplotlib directly", "why": "time"},
    {"id": "D10", "what": "C2e permutation null: 500 within-template permutations for T1/T2, 200 for bench tasks and "
                          "the archive-pooled secondary analysis; full refits incl. inner CV",
     "why": "time (bench tasks are secondary to T1/T2 for C2e)"},
    {"id": "D11", "what": "displacement-targeted ADD (protocol clarification from the plan) and SUBTRACT run in the "
                          "prompt prefill only; generation reads the edited KV cache with no decode-time hooks",
     "why": "as planned"},
    {"id": "D12", "what": "teacher-forced states were first extracted in 20-row batches; under FP8 W8A8 a row's state "
                          "then depends on its position in the batch (GEMM tiling): identical prefixes differed by 4-8% "
                          "(relative L2). The C2e and 5a states were re-extracted at batch 1 as the plan specifies; the "
                          "batch-20 C2e run is kept as a sensitivity analysis (results/c2e_batch20_sensitivity.json); "
                          "the 5c states stay from 20-row batches (descriptive only)",
     "why": "found by the C2e determinism check; U1b quantifies it and shows decode at M=20 is row-position independent, "
            "so the CRN coupling of the behavioural arms is unaffected"},
    {"id": "D13", "what": "exploratory additions outside the frozen rules: 12 extra random directions (seeds 9004-9015, "
                          "same construction) at alpha 1 on T2, T1, T03; a C2e extension to generated positions 24-96 "
                          "with a bag-of-tokens text control (results/c2e_extension.json)",
     "why": "the frozen C2e window (tokens 1-16) ends before the class-divergent text (T2 median first divergence = 29 "
            "tokens); 3 random controls give a coarse picture of the random-direction distribution"},
    {"id": "D14", "what": "0g: the first attempt stopped at an assertion (exp1 sample ids repeat across paraphrases; the "
                          "corpus key now includes paraphrase_id) and produced no numbers; it was re-run after S8",
     "why": "bug fix"},
]


def _san(a: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", a.replace(".", "p"))


# ------------------------------------------------------------------------------------------------ figures
def figures(c2d: dict, c2e: dict | None, c2f: dict, sae: dict | None, man: dict | None) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 8, "pdf.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False})
    made = []
    pal = {"NEUTRAL": "#9e9e9e", "BAN": "#1f77b4", "ADD": "#d62728", "RAND": "#7f7f7f", "SUB": "#2ca02c",
           "HEADS": "#9467bd"}

    def col(a: str) -> str:
        for k, v in pal.items():
            if a.startswith(k):
                return v
        return "#333333"
    # (1) avoidance by arm, per task
    tasks = [t for t in SAMPLED_TASKS if t in c2d["per_task"]]
    fig, axes = plt.subplots(2, 3, figsize=(10, 5.5), sharey=True)
    for ax, t in zip(axes.flat, tasks):
        arms = [a for a in ["NEUTRAL", "BAN", "ADD_a0.5", "ADD_a1.0", "ADD_a2.0", "RAND9001_a1.0", "RAND9002_a1.0",
                            "RAND9003_a1.0", "RAND9001_a2.0", "RAND9002_a2.0", "RAND9003_a2.0"]
                if a in c2d["per_task"][t]["arms"]]
        v = [c2d["per_task"][t]["arms"][a]["avoidance"] for a in arms]
        ci = [c2d["per_task"][t]["arms"][a]["avoidance_ci95"] for a in arms]
        err = np.array([[max(0, x - c[0]) for x, c in zip(v, ci)], [max(0, c[1] - x) for x, c in zip(v, ci)]])
        ax.bar(range(len(arms)), v, color=[col(a) for a in arms], yerr=err, capsize=2)
        ax.set_xticks(range(len(arms)))
        ax.set_xticklabels([a.replace("_a", " a") for a in arms], rotation=70, ha="right", fontsize=6)
        ax.set_title(f"{t} (default: {DEFAULT[t]})")
        ax.set_ylim(0, 1.05)
    axes[0, 0].set_ylabel("avoidance (1 - default share)")
    axes[1, 0].set_ylabel("avoidance (1 - default share)")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIG_DIR / f"fig1_avoidance_by_arm.{ext}", dpi=200)
    plt.close(fig)
    made.append("fig1_avoidance_by_arm")
    # (2) landing composition ADD (best alpha) vs BAN vs RAND alpha 1 pooled
    fig, axes = plt.subplots(1, len(tasks), figsize=(2.1 * len(tasks), 3.2))
    for ax, t in zip(np.atleast_1d(axes), tasks):
        pt = c2d["per_task"][t]
        ba = (pt.get("forecast") or {}).get("best_alpha") or 1.0
        rows = {"BAN": pt["arms"].get("BAN", {}).get("landing", {}), f"ADD a{ba}": pt["arms"].get(f"ADD_a{ba}", {}).get("landing", {})}
        pooled: Counter = Counter()
        for s in (9001, 9002, 9003):
            pooled.update(pt["arms"].get(f"RAND{s}_a1.0", {}).get("landing", {}))
        rows["RAND a1 (pooled)"] = dict(pooled)
        labs = sorted({l for d in rows.values() for l in d})
        bottom = np.zeros(len(rows))
        cm = plt.get_cmap("tab20")
        for i, l in enumerate(labs):
            vals = np.array([d.get(l, 0) / max(sum(d.values()), 1) for d in rows.values()])
            ax.bar(range(len(rows)), vals, bottom=bottom, color=cm(i % 20), label=l)
            bottom += vals
        ax.set_xticks(range(len(rows)))
        ax.set_xticklabels(list(rows), rotation=45, ha="right", fontsize=6)
        ax.set_title(t, fontsize=8)
        ax.legend(fontsize=5, loc="upper right")
    np.atleast_1d(axes)[0].set_ylabel("share of non-default attempts")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIG_DIR / f"fig2_landing_composition.{ext}", dpi=200)
    plt.close(fig)
    made.append("fig2_landing_composition")
    # (3) SUBTRACT panel
    fig, ax = plt.subplots(figsize=(6, 3))
    xs, labels = 0, []
    for t in tasks:
        for arm in ("SUB_plain", "SUB_affine", "SUB_rand9001"):
            s = c2d["per_task"][t]["subtract"].get(arm)
            if not s:
                continue
            ax.errorbar(xs, s["delta_banned_share"], yerr=[[s["delta_banned_share"] - s["ci95"][0]],
                                                           [s["ci95"][1] - s["delta_banned_share"]]],
                        fmt="o", color={"SUB_plain": "#2ca02c", "SUB_affine": "#17becf", "SUB_rand9001": "#7f7f7f"}[arm])
            labels.append(f"{t}\n{arm.replace('SUB_', '')}")
            xs += 1
    ax.axhline(0, color="k", lw=0.5)
    ax.axhline(0.3, color="r", lw=0.5, ls="--")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=6)
    ax.set_ylabel("delta banned share (SUB - ban)")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIG_DIR / f"fig3_subtract.{ext}", dpi=200)
    plt.close(fig)
    made.append("fig3_subtract")
    # (4) C2e BA curves
    if c2e:
        el = [t for t, v in c2e["primary"].items() if v.get("status") == "testable"]
        if el:
            fig, axes = plt.subplots(1, len(el), figsize=(4 * len(el), 3), squeeze=False)
            for ax, t in zip(axes[0], el):
                v = c2e["primary"][t]
                pos = ["R"] + [f"k{k}" for k in range(1, 9)]
                st = [v["state_curves"][p]["max_ba"] for p in pos]
                nq = [v["null_layer_max"][p]["q95"] for p in pos]
                ax.plot(range(len(pos)), st, "o-", color="#d62728", label="state (max over blocks)")
                ax.fill_between(range(len(pos)), 0.5, nq, color="#d62728", alpha=0.12, label="layer-max null q95")
                for key, c in (("Ta", "#1f77b4"), ("Tb", "#2ca02c"), ("Tc", "#ff7f0e")):
                    ys = [np.nan] + [v["text_controls"][f"k{k}"].get(key, np.nan) for k in range(1, 9)]
                    ax.plot(range(len(pos)), ys, "s--", ms=3, color=c, label=f"text {key}")
                ax.axhline(v["state_curves"]["R"]["max_ba"], color="k", lw=0.6, ls=":", label="R (template-only)")
                ax.set_xticks(range(len(pos)))
                ax.set_xticklabels(pos)
                ax.set_ylim(0.3, 1.02)
                ax.set_title(f"{t}: n={v['n']} (default {v['n_default']} / other {v['n_other']})", fontsize=8)
                ax.set_ylabel("balanced accuracy")
            axes[0][0].legend(fontsize=5)
            fig.tight_layout()
            for ext in ("png", "pdf"):
                fig.savefig(FIG_DIR / f"fig4_c2e_ba_curves.{ext}", dpi=200)
            plt.close(fig)
            made.append("fig4_c2e_ba_curves")
    # (5) head ablation
    if c2f.get("per_task"):
        fig, ax = plt.subplots(figsize=(5, 3))
        arms = ["BAN_k0_9", "HEADS_target", "HEADS_rand7101", "HEADS_rand7102", "HEADS_rand7103"]
        w = 0.38
        for i, t in enumerate(("T1", "T2")):
            r = c2f["per_task"].get(t)
            if not r:
                continue
            vals = [r["banned_share"].get(a, np.nan) for a in arms]
            cis = [r["arms"][a]["avoidance_ci95"] if a in r["arms"] else [np.nan, np.nan] for a in arms]
            err = np.array([[max(0.0, v - (1 - c[1])) for v, c in zip(vals, cis)],
                            [max(0.0, (1 - c[0]) - v) for v, c in zip(vals, cis)]])
            ax.bar(np.arange(len(arms)) + (i - 0.5) * w, vals, w, yerr=err, capsize=2,
                   label=f"{t} (Wilson 95% CI)", color=["#1f77b4", "#ff7f0e"][i])
        ax.set_xticks(range(len(arms)))
        ax.set_xticklabels([a.replace("HEADS_", "") for a in arms], rotation=30, fontsize=7)
        ax.set_ylabel("banned (default) share")
        ax.legend()
        fig.tight_layout()
        for ext in ("png", "pdf"):
            fig.savefig(FIG_DIR / f"fig5_head_ablation.{ext}", dpi=200)
        plt.close(fig)
        made.append("fig5_head_ablation")
    # (6) 0g 2x2 table
    if sae and sae.get("cells"):
        fig, ax = plt.subplots(figsize=(6, 2.6))
        cells = ["inst_own", "base_on_inst", "inst_on_base", "base_own"]
        M = np.array([[sae["cells"][c]["layers"][L]["fr_zero"] if c in sae["cells"] and L in sae["cells"][c]["layers"]
                       else np.nan for L in ("15", "20", "27")] for c in cells])
        im = ax.imshow(M, cmap="viridis", aspect="auto", vmin=np.nanmin(M) - 0.01, vmax=1)
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                ax.text(j, i, f"{M[i, j]:.3f}", ha="center", va="center", color="w", fontsize=7)
        ax.set_xticks(range(3))
        ax.set_xticklabels(["L15", "L20", "L27"])
        ax.set_yticks(range(4))
        ax.set_yticklabels(["instruct / own text", "base / instruct text", "instruct / base text", "base / own text"])
        ax.set_title("FR_zero (fraction of CE recovered vs zero-ablation)")
        fig.colorbar(im, ax=ax)
        fig.tight_layout()
        for ext in ("png", "pdf"):
            fig.savefig(FIG_DIR / f"fig6_sae_transfer_2x2.{ext}", dpi=200)
        plt.close(fig)
        made.append("fig6_sae_transfer_2x2")
    # (7) manifold panels (MDS of centroid geodesics, k = 10)
    if man and man.get("clouds"):
        keys = [k for k in sorted(man["clouds"]) if "knn" in man["clouds"][k] and k.endswith("k1-3")]
        if keys:
            n = len(keys)
            fig, axes = plt.subplots(2, (n + 1) // 2, figsize=(3.2 * ((n + 1) // 2), 6), squeeze=False)
            for ax, k in zip(axes.flat, keys):
                rec = man["clouds"][k]["knn"].get("10") or man["clouds"][k]["knn"].get(10)
                if not rec or "mds_xy" not in rec:
                    continue
                xy = np.array(rec["mds_xy"])
                sizes = [man["clouds"][k]["groups"][nm] for nm in rec["centroid_names"]]
                ax.scatter(xy[:, 0], xy[:, 1], s=np.array(sizes) * 4, c=[col(nm.split("|")[0]) for nm in
                                                                          rec["centroid_names"]], alpha=0.6)
                for (x, y), nm in zip(xy, rec["centroid_names"]):
                    ax.text(x, y, nm.replace("|", "\n"), fontsize=4)
                ax.set_title(f"{k} stress={rec.get('kruskal_stress1', float('nan')):.2f}", fontsize=7)
            fig.tight_layout()
            for ext in ("png", "pdf"):
                fig.savefig(FIG_DIR / f"fig7_manifold.{ext}", dpi=200)
            plt.close(fig)
            made.append("fig7_manifold")
    # (8) exploratory: C2e extension curves (state vs text at later generated positions)
    ext_p = RESULTS_DIR / "c2e_extension.json"
    if ext_p.exists():
        ext = read_json(ext_p)
        ts = [t for t in ext if ext[t].get("positions")]
        if ts:
            fig, axes = plt.subplots(1, len(ts), figsize=(4 * len(ts), 3), squeeze=False)
            for ax, t in zip(axes[0], ts):
                ks = [k for k, v in ext[t]["positions"].items() if "state_max_ba" in v]
                xs = [int(k) for k in ks]
                ax.plot(xs, [ext[t]["positions"][k]["state_max_ba"] for k in ks], "o-", color="#d62728", label="state")
                ax.plot(xs, [ext[t]["positions"][k]["null_layer_max_q95"] for k in ks], ":", color="#d62728",
                        label="null q95")
                for key, c in (("Ta", "#1f77b4"), ("Td", "#9467bd"), ("Tc", "#ff7f0e"), ("template_only", "k")):
                    ax.plot(xs, [ext[t]["positions"][k]["text"][key] for k in ks], "s--", ms=3, color=c, label=key)
                ax.set_title(f"{t} (exploratory, k = 24-96)", fontsize=8)
                ax.set_xlabel("generated position k")
                ax.set_ylabel("balanced accuracy")
                ax.set_ylim(0.3, 1.02)
            axes[0][0].legend(fontsize=5)
            fig.tight_layout()
            for ext_ in ("png", "pdf"):
                fig.savefig(FIG_DIR / f"fig8_c2e_extension.{ext_}", dpi=200)
            plt.close(fig)
            made.append("fig8_c2e_extension")
    # (9) exploratory: ADD alpha 1 against the distribution of random directions
    erd = c2d.get("exploratory_random_distribution") or {}
    if erd:
        fig, ax = plt.subplots(figsize=(5, 3))
        for i, (t, v) in enumerate(erd.items()):
            vals = list(v["random_avoidance"].values())
            ax.scatter([i] * len(vals), vals, color="#7f7f7f", s=12, alpha=0.7, label="random directions" if i == 0 else None)
            ax.scatter([i], [v["add_avoidance_k0_9"]], color="#d62728", s=40, marker="D", label="ADD (v)" if i == 0 else None)
        ax.set_xticks(range(len(erd)))
        ax.set_xticklabels(list(erd))
        ax.set_ylabel("avoidance at alpha 1 (k 0-9 slots)")
        ax.set_title("exploratory: v against random directions of the same norm", fontsize=8)
        ax.legend(fontsize=6)
        fig.tight_layout()
        for ext_ in ("png", "pdf"):
            fig.savefig(FIG_DIR / f"fig9_random_distribution.{ext_}", dpi=200)
        plt.close(fig)
        made.append("fig9_random_distribution")
    return made


# ------------------------------------------------------------------------------------------------ method_out
def method_out(rows: list[dict], c2d: dict, c2e: dict | None, c2f: dict, sae: dict | None, meta: dict) -> dict:
    from prompts import load_prompts

    pr = load_prompts()
    ds = []
    # c2d_arms: one example per CRN slot (task, template, k)
    slots: dict[tuple, dict] = {}
    for r in rows:
        if "label" not in r or r["arm"].startswith("U7") or r["arm"].startswith("HEADS"):
            continue
        k = (r["task"], r["template"], int(r["sample_id"]))
        slots.setdefault(k, {})[r["arm"]] = f"{r['label']}|{'pass' if r.get('passed') else 'fail'}"
    ex = []
    for (t, w, k), arms in sorted(slots.items()):
        e = {"input": f"task={t} template={w} slot k={k}. Ban prompt: {pr[(t, w, 'ban')]['user_text'][:400]}",
             "output": arms.get("BAN", arms.get("BAN_TOPUP", "not sampled")).split("|")[0],
             "metadata_task": t, "metadata_template": w, "metadata_k": k, "metadata_default": DEFAULT[t]}
        for a, v in sorted(arms.items()):
            e[f"predict_{_san(a)}"] = v
        ex.append(e)
    ds.append({"dataset": "c2d_arms", "examples": ex})
    # c2f_heads
    ex = []
    for (t, w, k), _ in sorted(slots.items()):
        if t not in ("T1", "T2") or k >= 10:
            continue
        e = {"input": f"task={t} template={w} slot k={k} (named ban, head mean-ablation arms)",
             "output": slots[(t, w, k)].get("BAN", "not sampled").split("|")[0], "metadata_task": t,
             "metadata_template": w, "metadata_k": k}
        for r in rows:
            if r["task"] == t and r["template"] == w and int(r["sample_id"]) == k and r["arm"].startswith("HEADS") \
                    and "label" in r:
                e[f"predict_{_san(r['arm'])}"] = f"{r['label']}|{'pass' if r.get('passed') else 'fail'}"
        ex.append(e)
    if ex:
        ds.append({"dataset": "c2f_heads", "examples": ex})
    # c2e_locus: one example per (task, position)
    ex = []
    if c2e:
        for t, v in c2e["primary"].items():
            if v.get("status") != "testable":
                ex.append({"input": f"task={t} C2e within-ban decoding", "output": v.get("status", "not run"),
                           "metadata_task": t})
                continue
            for p, cv in v["state_curves"].items():
                tc = v["text_controls"].get(p, {})
                e = {"input": f"task={t} position={p}: decode default-vs-other from the residual state",
                     "output": f"locus={v['locus']}" if v["locus"] else "no locus",
                     "predict_state_decoder_max_ba": f"{cv['max_ba']:.4f} (block {cv['argmax_block']})",
                     "predict_null_layer_max_q95": f"{v['null_layer_max'][p]['q95']:.4f}",
                     "metadata_task": t, "metadata_position": p}
                for key in ("Ta", "Tb", "Tc"):
                    if key in tc:
                        e[f"predict_text_{key}"] = f"{tc[key]:.4f}"
                ex.append(e)
    if ex:
        ds.append({"dataset": "c2e_locus", "examples": ex})
    # sae_transfer
    ex = []
    if sae and sae.get("cells"):
        for c, cv in sae["cells"].items():
            for L, lv in cv["layers"].items():
                ex.append({"input": f"0g cell={c} layer={L}: CE over response tokens with the Qwen-Scope SAE spliced in",
                           "output": f"FR_zero={lv['fr_zero']:.4f}",
                           "predict_fr_mean": f"{lv['fr_mean']:.4f}", "predict_dce": f"{lv['dce']:.4f}",
                           "predict_kl_sae": f"{lv['kl_sae']:.4f}", "predict_fvu": f"{lv['fvu']:.4f}",
                           "metadata_cell": c, "metadata_layer": L})
    if ex:
        ds.append({"dataset": "sae_transfer", "examples": ex})
    return {"metadata": meta, "datasets": ds}


def timing() -> dict[str, Any]:
    tb = read_jsonl(RESULTS_DIR / "timing_batches.jsonl")
    out: dict[str, Any] = {"n_batches": len(tb), "rows": 20 * len(tb), "gpu_seconds_sampling": float(sum(t["seconds"] for t in tb))}
    by = {}
    for t in tb:
        ph = t["block_id"].split(":")[0]
        by.setdefault(ph, []).append(t["seconds"])
    out["by_phase"] = {k: {"n_batches": len(v), "seconds": float(sum(v)), "mean_s_per_batch": float(np.mean(v))}
                       for k, v in by.items()}
    out["drop_decisions"] = ["secondary C1 rows: forecasts committed (commit #2), event rows not scored (drop item 1)"]
    return out


def run_all() -> None:
    rows = merged()
    c2d = run_c2d(rows)
    from analysis.c2d import exploratory_random_distribution

    c2d["exploratory_random_distribution"] = exploratory_random_distribution(rows)
    write_json(RESULTS_DIR / "c2d.json", c2d)
    c2f = run_c2f(rows)
    write_json(RESULTS_DIR / "c2f.json", c2f)
    c2e = read_json(RESULTS_DIR / "c2e.json") if (RESULTS_DIR / "c2e.json").exists() else None
    sae = run_sae_report()
    if sae:
        write_json(RESULTS_DIR / "sae_transfer.json", sae)
    sr = None
    try:
        from analysis.sae_readout import run_sae_readout

        sr = run_sae_readout()
        sr["zero_g_frozen_pass_any_layer"] = sae.get("frozen_pass_any_layer") if sae else None
        write_json(RESULTS_DIR / "sae_readout.json", sr)
    except Exception as e:  # noqa: BLE001 - descriptive analysis; record and continue
        logger.exception(f"5a failed: {e}")
    man = None
    try:
        from analysis.manifold import run_manifold

        lstar = {}
        if c2e:
            for t, v in c2e["primary"].items():
                if v.get("locus"):
                    lstar[t] = v["locus"]["block"]
        man = run_manifold(lstar)
        write_json(RESULTS_DIR / "manifold.json", man)
    except Exception as e:  # noqa: BLE001
        logger.exception(f"5c failed: {e}")
    write_json(RESULTS_DIR / "deviations.json", DEVIATIONS)
    tm = timing()
    write_json(RESULTS_DIR / "timing.json", tm)
    made = figures(c2d, c2e, c2f, sae, man)
    from commit import verify

    chain = verify()
    meta = {
        "method_name": "Where in Qwen3 a coding ban lives (iteration 3, internal locus)",
        "model": "Qwen/Qwen3-8B @ b968826d9c46dd6066d109eabc6255188de91218", "quantisation": QUANT,
        "conventions": {"block": "block l = decoder block l (0-based); output = hidden_states[l+1]",
                        "S": "[p1, spec_end): first token of 'Task:' .. last user token", "R": "P-1",
                        "k": "generated position k = absolute P+k-1 (token k is the input; predicts k+1)",
                        "crn": "slot (task, template, k) -> u_stream(task, template, k), identical in every arm"},
        "c2d": {"verdict": c2d["verdict"], "denominator_tasks": c2d["denominator_tasks"], "n_add_pass": c2d["n_add_pass"],
                "pooled_subtract": c2d["pooled_subtract"], "within_random_range": c2d["tasks_add_within_random_range"],
                "per_task_add": {t: {"add_pass": v["add_pass"], "event_gate": v["event_gate"]["pass"],
                                     "avoidance": {a: v["arms"][a]["avoidance"] for a in v["arms"]}}
                                 for t, v in c2d["per_task"].items()}},
        "c2e": ({t: {"status": v.get("status"), "locus": v.get("locus"), "locus_table": v.get("locus_table")}
                 for t, v in c2e["primary"].items()} if c2e else None),
        "c2f": {k: v for k, v in c2f.items() if k != "per_task"},
        "zero_g": ({"per_layer": sae["per_layer"], "frozen_pass_any_layer": sae["frozen_pass_any_layer"]} if sae else None),
        "c2e_batch20_sensitivity": ({t: {"status": v.get("status"), "locus": v.get("locus")} for t, v in
                                     read_json(RESULTS_DIR / "c2e_batch20_sensitivity.json")["primary"].items()}
                                    if (RESULTS_DIR / "c2e_batch20_sensitivity.json").exists() else None),
        "c2e_extension_exploratory": (read_json(RESULTS_DIR / "c2e_extension.json")
                                      if (RESULTS_DIR / "c2e_extension.json").exists() else None),
        "exploratory_random_distribution": c2d.get("exploratory_random_distribution"),
        "unit_tests": {"gpu": read_json(RESULTS_DIR / "unit_tests_gpu.json"),
                       "u1b": read_json(RESULTS_DIR / "unit_tests_u1b.json") if (RESULTS_DIR / "unit_tests_u1b.json").exists() else None,
                       "c2e_synthetic": read_json(RESULTS_DIR / "test_c2e_synthetic.json")},
        "deviations": DEVIATIONS, "hash_chain": chain, "figures": made, "timing": tm,
        "predictions": read_json(PRED_DIR / "commit1.json")["predictions"],
        "created_utc": utc_now()}
    mo = method_out(rows, c2d, c2e, c2f, sae, meta)
    write_json(ROOT / "method_out.json", mo)
    logger.info(f"method_out.json: {sum(len(d['examples']) for d in mo['datasets'])} examples in {len(mo['datasets'])} datasets")
