#!/usr/bin/env python3
"""Step 9: method_out.json (exp_gen_sol_out schema) and figures F1-F6 from the results/ files."""

from __future__ import annotations

import json
import math
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

from config import (DATA, FIGS, LOGS, MODEL_ID, MODEL_REV, MODES, PROMPTS, RESULTS, ROOT, SCORES, TASKS,  # noqa: E402
                    read_json, read_jsonl, setup_logging, utc_now, write_json)

plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})


def _load(name: str) -> Any:
    p = RESULTS / name
    return read_json(p) if p.exists() else None


def js(o: Any) -> str:
    return json.dumps(o, sort_keys=True, default=lambda x: None if isinstance(x, float) and math.isnan(x) else x)


def clean(o: Any) -> Any:
    if isinstance(o, float):
        return None if (math.isnan(o) or math.isinf(o)) else o
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating,)):
        return clean(float(o))
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def build_method_out() -> dict[str, Any]:
    gate = _load("gate.json")
    c1 = _load("c1.json")
    events = read_json(RESULTS / "gate_events.json")
    ex_gate = []
    gmap = {e["event_id"]: e for e in (gate["primary"]["events"] if gate else [])}
    for e in events["events"]:
        g = gmap.get(e["event_id"])
        allowed = [j for j in MODES[e["task"]] if j not in e["banned"]]
        uni = {j: 0.98 / len(allowed) for j in allowed}
        uni["other"] = 0.02
        n_al = sum(e["distribution_allowed"].values()) or 1
        ex_gate.append({
            "input": f"[{e['event_id']}] exp1 prompt (paraphrase {e['paraphrases'][0]['paraphrase_id']}):\n"
                     + e["paraphrases"][0]["prompt"],
            "output": js({k: v / n_al for k, v in e["distribution_allowed"].items()}),
            "predict_frlp": js(g["implied_mean"]) if g else "null",
            "predict_uniform": js(uni),
            "metadata_task": e["task"], "metadata_condition": e["condition"], "metadata_banned": e["banned"],
            "metadata_n_samples": e["n_samples"], "metadata_realised_mode": e["realised_mode"],
            "metadata_clear_mode": e["clear_mode"], "metadata_d_e_nats": clean(g["d_e"]) if g else None,
            "metadata_argmax_hit": g["hit"] if g else None,
            "metadata_paraphrase_d": clean([p["d"] for p in g["paraphrases"]]) if g else None,
            "metadata_cell_ess": clean([p["ess"] for p in g["paraphrases"]]) if g else None,
        })
    ex_rows = []
    if c1:
        P = c1["primary_neutral"]
        R2 = c1["reference_mention"]
        assoc = read_json(RESULTS / "association.json")["profiles"]
        for t in TASKS:
            for B, r in P["tasks"][t]["rows"].items():
                r2 = R2["tasks"][t]["rows"].get(B, {})
                pv = {j: (r["pv_h1"][j] + r["pv_h2"][j]) / 2 for j in r["survivors"]}
                ex_rows.append({
                    "input": f"[{t}|ban:{B}] centred FRLP gain profile Gbar_B over survivors {r['survivors']} "
                             f"(ban vs token-matched neutral twin, 5 templates x 2 program halves)",
                    "output": js(clean(r["Gbar"])),
                    "predict_ladder": js(clean(r["fitted_ladder"])),
                    "predict_prime_and_veto": js(clean(pv)),
                    "predict_association": js(clean({j: assoc.get(f"{t}|{B}", {}).get(j) for j in r["survivors"]})),
                    "metadata_task": t, "metadata_ban": B, "metadata_a_ladder": clean(r["a"]),
                    "metadata_ss_ladder": clean(r["a2"]), "metadata_ss_specific": clean(r["ss_s"]),
                    "metadata_noise_N_u": clean(r["N_u"]), "metadata_noise_N_s": clean(r["N_s"]),
                    "metadata_x_specific_residual": clean(r["s"]), "metadata_rho_prime_veto": clean(r["rho_pv"]),
                    "metadata_rho_association": clean(r["rho_assoc"]),
                    "metadata_cos_with_ladder": clean(r["cos_with_u"]),
                    "metadata_n_low_ess_cells": r["n_flagged_cells"],
                    "metadata_Gbar_mention_reference": clean(r2.get("Gbar")),
                })
    meta = {
        "method_name": "FRLP output-space share test (substitute vs ladder)",
        "description": "Forced-ratio latent probabilities (mixture-proposal importance sampling over forced programs, "
                       "yield-corrected) scored by teacher forcing on Qwen3-8B; single-ban gain profiles decomposed "
                       "into a generic ladder share (external profile from nonce bans, matched-norm random prompt-band "
                       "edits and a novelty instruction) and an X-specific residual, with an aim test against the "
                       "prime-and-veto and free-form association profiles.",
        "model": MODEL_ID, "model_revision": MODEL_REV, "utc": utc_now(),
        "labeller_recheck": _load("labeller_recheck.json"), "yields": _load("yields.json"),
        "gate": gate, "c1": c1, "sensitivity": _load("sensitivity.json"), "secondary": _load("secondary.json"),
        "coverage": _load("coverage.json"), "ess": _load("ess_table.json"), "association": _load("association.json"),
        "synthetic_c1_test": _load("synthetic_c1_test.json"),
        "scorer_validation": read_json(LOGS / "scorer_validation.json") if (LOGS / "scorer_validation.json").exists() else None,
        "throughput": read_json(LOGS / "throughput.json") if (LOGS / "throughput.json").exists() else None,
        "queue": read_json(LOGS / "queue_final.json") if (LOGS / "queue_final.json").exists() else None,
        "timings": _load("timings.json"), "openrouter_cost": _load("openrouter_cost.json"),
        "deviations": _load("deviations.json"), "protocol": _load("protocol.json"),
        "mixture_identity": _load("mixture_identity.json"), "rederivation": _load("independent_rederivation.json"),
    }
    out = {"metadata": clean(meta), "datasets": [{"dataset": "frlp_gate_events", "examples": ex_gate}]}
    if ex_rows:
        out["datasets"].append({"dataset": "c1_rows", "examples": ex_rows})
    return out


# ------------------------------------------------------------------------------------------------ figures
def fig_gate(gate: dict[str, Any]) -> None:
    ev = gate["primary"]["events"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    xs, ys, cs = [], [], []
    for e in ev:
        n = sum(v for v in e["realised_allowed"].values()) or 1
        for j, q in e["implied_mean"].items():
            xs.append(q)
            ys.append(e["realised_allowed"].get(j, 0) / n)
            cs.append("tab:blue" if e["event_id"].startswith("t1") else "tab:orange")
    axes[0].scatter(xs, ys, c=cs, s=14, alpha=0.75)
    axes[0].plot([0, 1], [0, 1], "k--", lw=0.8)
    axes[0].set_xlabel("FRLP-implied share (mean over paraphrases)")
    axes[0].set_ylabel("realised attempted share (exp1)")
    axes[0].set_title(f"Gate (b,c): pooled Spearman {gate['primary']['pooled_spearman_implied_vs_realised']:.2f} "
                      "(blue T1, orange T2)", fontsize=9)
    names = [e["event_id"] for e in ev]
    d = [e["d_e"] for e in ev]
    axes[1].barh(range(len(names)), d, color=["tab:green" if e["hit"] else "tab:red" for e in ev])
    axes[1].axvline(0.3, color="k", ls="--", lw=0.8)
    axes[1].set_yticks(range(len(names)))
    axes[1].set_yticklabels(names, fontsize=7)
    axes[1].set_xlabel("d_e (nats over uniform); green = argmax hit")
    a = gate["primary"]["a"]
    axes[1].set_title(f"(a) mean S={a['mean_S']:.2f}, m={a['mean_m_default']:.2f}; verdict {gate['verdict']}",
                      fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGS / "F1_gate.png", dpi=160)
    fig.savefig(FIGS / "F1_gate.pdf")
    plt.close(fig)


def fig_heatmaps(c1: dict[str, Any]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    for ci, key in enumerate(("primary_neutral", "reference_mention")):
        for ti, t in enumerate(TASKS):
            ax = axes[ti, ci]
            rows = c1[key]["tasks"][t]["rows"]
            js_ = c1[key]["tasks"][t]["measurable"]
            M = np.full((len(MODES[t]), len(js_)), np.nan)
            for bi, B in enumerate(MODES[t]):
                if B in rows:
                    for j, v in rows[B]["Gbar"].items():
                        M[bi, js_.index(j)] = v
            lim = np.nanmax(np.abs(M)) if np.isfinite(M).any() else 1
            im = ax.imshow(M, cmap="RdBu_r", vmin=-lim, vmax=lim, aspect="auto")
            ax.set_xticks(range(len(js_)))
            ax.set_xticklabels(js_, rotation=40, fontsize=7)
            ax.set_yticks(range(len(MODES[t])))
            ax.set_yticklabels([f"ban {b}" for b in MODES[t]], fontsize=7)
            for (i, k), v in np.ndenumerate(M):
                if np.isfinite(v):
                    ax.text(k, i, f"{v:.2f}", ha="center", va="center", fontsize=6)
            ax.set_title(f"{t}: centred gain vs {'neutral' if ci == 0 else 'mention'} twin", fontsize=8)
            fig.colorbar(im, ax=ax, fraction=0.04)
    fig.tight_layout()
    fig.savefig(FIGS / "F2_gain_heatmaps.png", dpi=160)
    fig.savefig(FIGS / "F2_gain_heatmaps.pdf")
    plt.close(fig)


def fig_share(c1: dict[str, Any]) -> None:
    P = c1["primary_neutral"]
    labels, lad, spec, nu, ns = [], [], [], [], []
    for t in TASKS:
        for B, r in P["tasks"][t]["rows"].items():
            labels.append(f"{t}:{B}")
            lad.append(r["a2"])
            spec.append(r["ss_s"])
            nu.append(r["N_u"])
            ns.append(r["N_s"])
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(x - 0.2, lad, 0.4, label="ladder SS (a_B^2)", color="tab:blue")
    ax.bar(x + 0.2, spec, 0.4, label="X-specific SS (||s_B||^2)", color="tab:red")
    ax.scatter(x - 0.2, nu, marker="_", color="k", s=120, label="noise expectation")
    ax.scatter(x + 0.2, ns, marker="_", color="k", s=120)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=40, fontsize=7)
    pb = P["pooled"].get("bootstrap", {})
    sp = P["pooled"]["share_point"]
    ci = pb.get("SHARE_ci", [math.nan, math.nan])
    ax.set_title(f"Pooled X-specific SHARE = {sp['SHARE']:.2f} [95% CI {ci[0]:.2f}, {ci[1]:.2f}]; "
                 f"branch {P['pooled'].get('branch')}", fontsize=9)
    ax.set_ylabel("sum of squares (nats^2)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGS / "F3_share.png", dpi=160)
    fig.savefig(FIGS / "F3_share.pdf")
    plt.close(fig)


def fig_cos(c1: dict[str, Any]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for ax, t in zip(axes, TASKS):
        le = c1["primary_neutral"]["tasks"][t].get("ladder_exists", {})
        mat = le.get("matrix", {})
        names = list(mat)
        M = np.array([[mat[a][b] for b in names] for a in names]) if names else np.zeros((1, 1))
        im = ax.imshow(M, cmap="RdBu_r", vmin=-1, vmax=1)
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels(names, rotation=60, fontsize=6)
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names, fontsize=6)
        ax.set_title(f"{t}: generic-profile centred cosine (mean {le.get('mean_pairwise_centred_cosine', math.nan):.2f})",
                     fontsize=8)
        fig.colorbar(im, ax=ax, fraction=0.04)
    fig.tight_layout()
    fig.savefig(FIGS / "F4_generic_cosines.png", dpi=160)
    fig.savefig(FIGS / "F4_generic_cosines.pdf")
    plt.close(fig)


def fig_prime_veto(c1: dict[str, Any]) -> None:
    P = c1["primary_neutral"]
    labels, pr, ve = [], [], []
    for t in TASKS:
        for B, x in P["tasks"][t].get("extras", {}).items():
            labels.append(f"{t}:{B}")
            pr.append(x["prime_share_of_ss"])
            ve.append(x["veto_share_of_ss"])
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(10, 3.6))
    ax.bar(x - 0.2, pr, 0.4, label="prime (mention - neutral)")
    ax.bar(x + 0.2, ve, 0.4, label="veto (ban - mention)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=40, fontsize=7)
    ax.set_ylabel("share of between-survivor SS of the ban gain")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGS / "F5_prime_veto.png", dpi=160)
    fig.savefig(FIGS / "F5_prime_veto.pdf")
    plt.close(fig)


def fig_ess() -> None:
    rows = read_jsonl(RESULTS / "frlp_cells.jsonl")
    fig, ax = plt.subplots(figsize=(7, 3.6))
    for t, c in (("t1", "tab:blue"), ("t2", "tab:orange")):
        e = [r["ess"] for r in rows if r["task"] == t and r["variant"] == "primary" and r["half"] != "all"
             and r["ess"] is not None]
        if e:
            ax.hist(e, bins=40, alpha=0.6, label=f"{t} (n={len(e)}, {np.mean(np.array(e) < 5):.0%} < 5)", color=c)
    ax.axvline(5, color="k", ls="--", lw=0.8)
    ax.set_xlabel("ESS per half-cell (primary)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGS / "F6_ess.png", dpi=160)
    fig.savefig(FIGS / "F6_ess.pdf")
    plt.close(fig)


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("outputs")
    gate = _load("gate.json")
    c1 = _load("c1.json")
    for fn, arg in ((fig_gate, gate), (fig_heatmaps, c1), (fig_share, c1), (fig_cos, c1), (fig_prime_veto, c1)):
        if arg is not None:
            try:
                fn(arg)
            except (KeyError, ValueError, TypeError) as e:
                logger.error(f"figure {fn.__name__} failed: {e}")
    try:
        fig_ess()
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"figure ess failed: {e}")
    out = build_method_out()
    write_json(ROOT / "method_out.json", out)
    logger.info(f"method_out.json: {[ (d['dataset'], len(d['examples'])) for d in out['datasets']]}")


if __name__ == "__main__":
    main()
