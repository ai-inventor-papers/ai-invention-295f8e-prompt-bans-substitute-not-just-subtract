#!/usr/bin/env python3
"""S9: method_out.json (exp_gen_sol_out schema) + figures.

Datasets: one example per behaviour sample (input = prompt + arm, output = mechanism label, predict_* = the label
the matched common-random-numbers sample received under each other arm, pass flag and noun); one example per C5
wording (output = banned share, predict_* = projections); one example per (task, template, arm) FRLP route cell.
metadata: every analysis, deviations, stage times, OpenRouter spend, pre-registration hash.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
from loguru import logger

from cfg import (DATA_DIR, FIG_DIR, PROMPTS_DIR, RESULTS_DIR, ROOT, TASKS, TEMPLATE_IDS, X_KEY, model_revision,
                 read_jsonl, sha256_file, write_json)

ARM_DESC = {
    "a": "arm a: full ban (ban KV cache, ban R logits)",
    "b": "arm b: full neutral twin (baseline)",
    "c": "arm c: PROMPT ROUTE (neutral condition-segment cache + ban task-spec/R cache, ban R logits)",
    "d": "arm d: DIRECT ROUTE (ban condition-segment cache + neutral task-spec/R cache, neutral R logits)",
    "K1": "arm a with condition-span attention knockout for generated index < 16",
    "K2": "arm a with condition-span attention knockout for generated index >= 16",
}
TASK_NAME = {"t1": "T1_grid_path_ban_BFS", "t2": "T2_weighted_shortest_path_ban_Dijkstra"}


def _behaviour_examples(fp: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    S = read_jsonl(DATA_DIR / "samples.jsonl")
    idx = {(s["task"], s["template"], s["sample_id"], s["condition"]): s for s in S}
    out: dict[str, list[dict[str, Any]]] = {t: [] for t in TASKS}
    for s in S:
        t, w = s["task"], s["template"]
        tw = fp["tasks"][t]["templates"][w]
        if s["condition"] in ("b", "c", "d") and s.get("noun_slot") in ("A", "B"):
            seg = tw[f"neutral_{s['noun_slot']}"]["segment"]
        else:
            seg = tw["ban"]["segment"]
        ex = {"input": f"[{ARM_DESC.get(s['condition'], s['condition'])}] [template {w}] [ban segment: "
                       f"{tw['ban']['segment']}] [neutral segment: {seg}]\n\n{tw['ban']['user_text']}",
              "output": str(s["label"]),
              "predict_passed": str(bool(s["passed"])), "predict_noun": str(s.get("noun") or "-"),
              "predict_banned": str(bool(s["label"] == X_KEY[t]))}
        for arm in ("a", "b", "c", "d"):
            m = idx.get((t, w, s["sample_id"], arm))
            ex[f"predict_label_arm_{arm}"] = str(m["label"]) if m else "not_sampled"
        ex.update({"metadata_task": t, "metadata_arm": s["condition"], "metadata_template": w,
                   "metadata_sample_id": s["sample_id"], "metadata_seed": s["seed"], "metadata_decoding": s["decoding"],
                   "metadata_labeller_source": s["labeller_source"], "metadata_runtime_label": s.get("runtime_label"),
                   "metadata_ast_label": s.get("ast_label"), "metadata_n_tokens": s["n_tokens"],
                   "metadata_finish_reason": s["finish_reason"], "metadata_code_sha256": s.get("code_sha256"),
                   "metadata_code": s.get("code"), "metadata_judge_skipped": s.get("judge_skipped", False)})
        out[t].append(ex)
    return out


def _c5_examples(c5: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not c5:
        return []
    ex = []
    for w in c5["wordings"]:
        ex.append({"input": f"[{w['exp']} {w['task']}] {w['text']}", "output": f"{w['banned_share']:.4f}",
                   "predict_projection_shared_ban_direction": f"{w['pi']:.4f}",
                   "predict_projection_decommitment_axis": f"{w['pi_dc']:.4f}",
                   "metadata_experiment": w["exp"], "metadata_task": w["task"], "metadata_n_samples": w["n"],
                   "metadata_composition": w["composition"], "metadata_ids_source": w["ids_source"],
                   "metadata_substitute_share_nonbanned": w.get("subst_share_nonbanned")})
    return ex


def _route_examples(an: dict[str, Any]) -> list[dict[str, Any]]:
    ex = []
    rp = an["route_frlp"]["per_task"]
    for t, e in rp.items():
        for w, pw in e.get("per_template", {}).items():
            for arm, d in pw["D"].items():
                if d is None or arm == "b":
                    continue
                ex.append({"input": f"FRLP drop of the banned algorithm {X_KEY[t]} on {t}, template {w}, arm {arm}",
                           "output": f"{d:.4f}", "predict_ess_arm": f"{pw['ESS'][arm]:.2f}",
                           "predict_ess_neutral": f"{pw['ESS']['b']:.2f}",
                           "metadata_task": t, "metadata_template": w, "metadata_arm": arm})
    return ex


def _deviations(an: dict[str, Any]) -> list[str]:
    dev = [
        "vLLM 0.11 could not start (torch-inductor requires a C compiler absent on this machine); fallback F2: FRLP "
        "programs were generated with the HF engine's inverse-CDF sampler (T=1.0, independent PCG64 stream per "
        "sample), so the importance-sampling proposal is exactly the scoring model's distribution.",
        "GPU was an RTX 4090 (24 GB), not the planned RTX A4500; batch sizes were set for 24 GB.",
        "All 718 neutral-noun candidates are single Qwen3 tokens, so the closest-token-count rule reduces to SUBTLEX "
        "frequency (nouns 'man' and 'guy' for both bans); length matching used companion-noun phrases including "
        "article variants ('the {N}', '{N} and {C1}', ...) to reach token differences that are not multiples of 3.",
        "Per-token log-probs are stored as float32 (not float16) so the re-derivation audit is exact.",
        "Neutral-noun companions are shared by nouns A and B, so the placebo splice differs only in the head noun.",
        "Program generation order: rounds of 4 samples per paraphrase generated two rounds per block; the first 30 "
        "accepted in (round, paraphrase, index) order were kept.",
        "Knockout restorations net of the neutral-prompt K0 control subtract the FULL-span, all-generated-positions "
        "control from the windowed and band knockouts too (an upper bound on their generic damage); raw values are "
        "reported beside them, and the K1-K2 contrast is unaffected.",
        "Scoring runs at batch 1 and behaviour batches are never pruned (constant batch shape): U3/U5 showed that bf16 "
        "kernel choice depends on batch shape (only 40% of sampled sequences identical when the batch shape changes), "
        "so cross-arm comparisons must share shapes; with shared shapes repeats are bit-identical.",
        "K1/K2 behaviour used all 20 streams per template (N = 100 per task per variant, plan: N = 50) so that their "
        "batches have arm a's exact shape.",
        "Additions beyond the plan (supplementary, not part of the pre-registered decision): (i) natural-proposal FRLP "
        "(natural_frlp.py) re-scoring the arm-b X programs, exact draws from p(.|b), under every arm; (ii) a full "
        "condition-span knockout K0 behaviour arm (extra_k0_behaviour.py, N = 100 per task, same CRN streams); "
        "(iii) opening-line and per-program shift distributions (supplementary.py).",
        "The lens commitment token (token before the first banned-signature token) falls right after 'from'/'import' "
        "in default programs, i.e. after the actual fork (first line 'from collections import deque' vs 'def solve'), "
        "so the veto layer is undefined there; the fork itself is documented by the opening-line analysis.",
    ]
    summ = json.loads((RESULTS_DIR / "frlp_programs_summary.json").read_text())
    dev += summ.get("deviations", [])
    for name in ("prereg_amendments.json",):
        p = RESULTS_DIR / name
        if p.exists():
            dev += [f"post-commit amendment: {a}" for a in json.loads(p.read_text())]
    return dev


def stage_outputs() -> dict[str, Any]:
    fp = json.loads((PROMPTS_DIR / "frozen_prompts.json").read_text())
    an = json.loads((RESULTS_DIR / "analysis.json").read_text())
    beh = _behaviour_examples(fp)
    datasets = [{"dataset": TASK_NAME[t] + "_behaviour_crn", "examples": beh[t]} for t in TASKS if beh[t]]
    c5ex = _c5_examples(an.get("c5"))
    if c5ex:
        datasets.append({"dataset": "C5_modal_ban_wordings_iter1_plus_frozen", "examples": c5ex})
    rex = _route_examples(an)
    if rex:
        datasets.append({"dataset": "FRLP_route_cells_per_template", "examples": rex})
    stage_times = read_jsonl(RESULTS_DIR / "stage_times.jsonl")
    from labelling import judge_spent

    meta = {
        "method_name": "KV-cache splice route test (C2) + compliance-at-R test (C5)",
        "title": "Where an algorithm ban takes effect",
        "model": "Qwen/Qwen3-8B", "model_revision": model_revision(), "dtype": "bfloat16", "thinking": "off",
        "baseline": "arm b (length-matched neutral twin: an irrelevant noun inside the same prohibition frame); the "
                    "route arms c and d are compared against the full ban (a) and this baseline on identical "
                    "continuations (FRLP) and identical uniform streams (behaviour)",
        "prereg_sha256": (RESULTS_DIR / "prereg_commit.txt").read_text().split()[0]
        if (RESULTS_DIR / "prereg_commit.txt").exists() else None,
        "analysis_py_sha256_now": sha256_file(ROOT / "analysis.py"),
        "frozen_prompts_sha256": sha256_file(PROMPTS_DIR / "frozen_prompts.json"),
        "route_frlp": an["route_frlp"], "sensitivities": an["sensitivities"],
        "survivor_gains": an["survivor_gains"], "frlp_cells_summary": an["frlp_cells_summary"],
        "behaviour": an["behaviour"], "token_localisation": an["token_localisation"],
        "coverage_shingles": an.get("coverage_shingles"),
        "lens": {k: v for k, v in (an.get("lens") or {}).items() if k != "records"},
        "c5": {k: v for k, v in (an.get("c5") or {}).items() if k != "wordings"},
        "labeller_recheck": {k: v for k, v in json.loads((RESULTS_DIR / "labeller_recheck.json").read_text()).items()
                             if k != "references"},
        "tests": json.loads((RESULTS_DIR / "tests.json").read_text()) if (RESULTS_DIR / "tests.json").exists() else None,
        "frlp_programs": json.loads((RESULTS_DIR / "frlp_programs_summary.json").read_text()),
        "raw_p_values_for_cross_artifact_holm": an.get("raw_p_values_for_cross_artifact_holm"),
        "supplementary": json.loads((RESULTS_DIR / "supplementary.json").read_text())
        if (RESULTS_DIR / "supplementary.json").exists() else None,
        "rederive_audit": json.loads((RESULTS_DIR / "rederive.json").read_text())
        if (RESULTS_DIR / "rederive.json").exists() else None,
        "headline_audit": json.loads((RESULTS_DIR / "headline_audit.json").read_text())
        if (RESULTS_DIR / "headline_audit.json").exists() else None,
        "deviations": _deviations(an), "stage_times": stage_times,
        "openrouter_spend_usd": judge_spent(),
        "neutral_nouns": {t: fp["tasks"][t]["nouns"] for t in TASKS},
    }
    out = {"metadata": meta, "datasets": datasets}
    write_json(ROOT / "method_out.json", out)
    logger.info(f"method_out.json: {[(d['dataset'], len(d['examples'])) for d in datasets]}")
    try:
        make_figures(an)
    except Exception as e:  # noqa: BLE001 - figures must not block the main output
        logger.error(f"figure generation failed: {e}")
    return out


# ------------------------------------------------------------------------------------------------ figures
def make_figures(an: dict[str, Any]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})
    C = {"t1": "#3b6fb6", "t2": "#d9822b", "pooled": "#444444"}
    rp = an["route_frlp"]
    # fig1: D_X per arm with CIs
    arms = ["a", "c", "d", "e", "f", "K0", "K1", "K2", "B1", "B2", "B3", "K0b", "mention"]
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    for k, t in enumerate(TASKS):
        e = rp["per_task"].get(t)
        if not e:
            continue
        xs = np.arange(len(arms)) + (k - 0.5) * 0.35
        ys = [e["D"].get(a, np.nan) for a in arms]
        lo = [e["D_ci"][a][0] if e["D_ci"].get(a) else np.nan for a in arms]
        hi = [e["D_ci"][a][1] if e["D_ci"].get(a) else np.nan for a in arms]
        ys, lo, hi = (np.array(v, dtype=float) for v in (ys, lo, hi))
        ax.errorbar(xs, ys, yerr=[ys - lo, hi - ys], fmt="o", ms=4, color=C[t], label=f"{t} (ban {X_KEY[t]})",
                    capsize=2, lw=1)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xticks(np.arange(len(arms)))
    ax.set_xticklabels(arms)
    ax.set_ylabel("FRLP drop $D_X$(arm) [nats]")
    ax.set_title("Banned-algorithm FRLP drop per arm (95% bootstrap CI)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig1_frlp_drop_per_arm.png", dpi=200)
    fig.savefig(FIG_DIR / "fig1_frlp_drop_per_arm.pdf")
    plt.close(fig)
    # fig2: token localisation
    tl = an.get("token_localisation") or {}
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.8))
    for k, t in enumerate(TASKS):
        e = tl.get(t, {})
        arms2 = [a for a in ("a", "c", "d", "K0", "K1", "K2") if a in e]
        xs = np.arange(len(arms2)) + (k - 0.5) * 0.35
        axs[0].bar(xs, [e[a]["signature_share_of_delta"] for a in arms2], width=0.35, color=C[t], label=t)
        axs[0].scatter(xs, [e[a]["signature_share_of_tokens"] for a in arms2], color="k", s=8, zorder=3)
        axs[1].bar(xs, [e[a]["first16_share_of_delta"] for a in arms2], width=0.35, color=C[t], label=t)
        axs[0].set_xticks(np.arange(len(arms2)))
        axs[0].set_xticklabels(arms2)
        axs[1].set_xticks(np.arange(len(arms2)))
        axs[1].set_xticklabels(arms2)
    axs[0].set_title("share of drop at signature tokens\n(dots: their share of tokens)")
    axs[1].set_title("share of drop in first 16 tokens")
    axs[0].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig2_token_localisation.png", dpi=200)
    fig.savefig(FIG_DIR / "fig2_token_localisation.pdf")
    plt.close(fig)
    # fig3: knockout restoration
    fig, ax = plt.subplots(figsize=(6.0, 2.8))
    ks = ["K0", "K1", "K2", "B1", "B2", "B3"]
    for k, t in enumerate(TASKS):
        e = rp["per_task"].get(t)
        if not e:
            continue
        ko = e["knockouts"]
        xs = np.arange(len(ks)) + (k - 0.5) * 0.35
        ys = np.array([ko[x]["R_raw"] for x in ks])
        lo = np.array([ko[x]["R_raw_ci"][0] for x in ks])
        hi = np.array([ko[x]["R_raw_ci"][1] for x in ks])
        ax.errorbar(xs, ys, yerr=[ys - lo, hi - ys], fmt="s", ms=4, color=C[t], capsize=2, lw=1, label=t)
    ax.axhline(0, color="k", lw=0.6)
    ax.axhline(1, color="k", lw=0.6, ls=":")
    ax.set_xticks(np.arange(len(ks)))
    ax.set_xticklabels(["K0 all", "K1 g<16", "K2 g>=16", "B1 L0-11", "B2 L12-23", "B3 L24-35"])
    ax.set_ylabel("restoration of the ban gap")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig3_knockout_restoration.png", dpi=200)
    fig.savefig(FIG_DIR / "fig3_knockout_restoration.pdf")
    plt.close(fig)
    # fig4: lens curves
    lens = an.get("lens") or {}
    ll = lens.get("logit_lens") or {}
    if ll:
        fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.8))
        for k, t in enumerate(TASKS):
            e = ll.get(f"{t}_default")
            if not e:
                continue
            m = np.array(e["X_lnrank_ban_minus_neu_mean"])
            lo, hi = (np.array(v) for v in e["X_lnrank_ban_minus_neu_ci"])
            xs = np.arange(len(m))
            axs[k].plot(xs, m, color=C[t], label="banned set (ban - neutral)")
            axs[k].fill_between(xs, lo, hi, color=C[t], alpha=0.25)
            s = np.array(e["SUB_lnrank_ban_minus_neu_mean"])
            axs[k].plot(xs, s, color="#666666", ls="--", label="substitute set")
            axs[k].axhline(0, color="k", lw=0.6)
            axs[k].axhline(1, color="k", lw=0.6, ls=":")
            axs[k].set_title(f"{t}: commitment token, n={e['n']}")
            axs[k].set_xlabel("layer")
        axs[0].set_ylabel("ln rank(ban) - ln rank(neutral)")
        axs[0].legend(frameon=False, fontsize=7)
        fig.tight_layout()
        fig.savefig(FIG_DIR / "fig4_lens_curves.png", dpi=200)
        fig.savefig(FIG_DIR / "fig4_lens_curves.pdf")
        plt.close(fig)
    # fig5: C5 scatter
    c5 = an.get("c5")
    if c5 and c5.get("wordings"):
        fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.0))
        W = c5["wordings"]
        exps = sorted({w["exp"] for w in W})
        cmap = plt.get_cmap("tab10")
        for k, t in enumerate(TASKS):
            for i, e in enumerate(exps):
                ws = [w for w in W if w["task"] == t and w["exp"] == e]
                axs[k].scatter([w["pi"] for w in ws], [w["banned_share"] for w in ws], s=12, color=cmap(i), label=e)
            axs[k].set_title(f"{t}: banned share vs projection at R")
            axs[k].set_xlabel("projection on LOEO shared ban direction (z)")
        axs[0].set_ylabel("per-wording banned share")
        tst = c5["shared_ban_direction"]["test"]
        axs[1].text(0.98, 0.98, f"combined rho={tst['rho']:.2f}, p={tst['p_one_sided']:.4f}\n"
                                f"random-dir null mean={tst['random_direction_null']['mean']:.2f}\n"
                                f"ceiling={c5['shared_ban_direction']['noise_ceiling']['mean_ceiling']:.2f}",
                    transform=axs[1].transAxes, fontsize=7, ha="right", va="top")
        axs[0].legend(frameon=False, fontsize=6)
        fig.tight_layout()
        fig.savefig(FIG_DIR / "fig5_c5_scatter.png", dpi=200)
        fig.savefig(FIG_DIR / "fig5_c5_scatter.pdf")
        plt.close(fig)
    # fig6: behaviour per arm (banned share with Wilson CI) and share of programs opening with an import line
    sp = RESULTS_DIR / "supplementary.json"
    beh = an.get("behaviour") or {}
    if sp.exists() and beh:
        sup = json.loads(sp.read_text())
        from cfg import wilson_ci

        arms6 = ["b", "d", "c", "a", "K0", "K1", "K2"]
        fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.9), sharey=True)
        for k, t in enumerate(TASKS):
            ol = sup["opening_lines"][t]
            bt = beh["per_task"][t]
            k0 = sup["behaviour_contrasts"][t].get("K0_banned_share")
            xs = np.arange(len(arms6))
            share, lo, hi, imp = [], [], [], []
            for a in arms6:
                if a == "K0":
                    if k0:
                        share.append(k0["share"])
                        lo.append(k0["wilson_ci"][0])
                        hi.append(k0["wilson_ci"][1])
                    else:
                        share.append(np.nan)
                        lo.append(np.nan)
                        hi.append(np.nan)
                else:
                    share.append(bt[a]["banned_share"])
                    lo.append(bt[a]["banned_ci"][0])
                    hi.append(bt[a]["banned_ci"][1])
                imp.append(ol.get(a, {}).get("share_import_opening", np.nan))
            share, lo, hi = (np.array(v, dtype=float) for v in (share, lo, hi))
            axs[k].bar(xs - 0.18, share, width=0.36, color=C[t], label=f"banned share ({X_KEY[t]})",
                       yerr=[share - lo, hi - share], capsize=2)
            axs[k].bar(xs + 0.18, imp, width=0.36, color="#bbbbbb", label="opens with an import line")
            axs[k].set_xticks(xs)
            axs[k].set_xticklabels(arms6)
            axs[k].set_title(f"{t}: behaviour per arm (N=100 each)")
            axs[k].legend(frameon=False, fontsize=7)
        axs[0].set_ylabel("share of samples")
        fig.tight_layout()
        fig.savefig(FIG_DIR / "fig6_behaviour_opening_line.png", dpi=200)
        fig.savefig(FIG_DIR / "fig6_behaviour_opening_line.pdf")
        plt.close(fig)
    logger.info("figures written")
