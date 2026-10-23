#!/usr/bin/env python3
"""Figures F1-F5, F7 (F6 = top5geo.py), PNG + PDF, from the results JSONs (numbers only from saved results).
F1 outcome series per position with change points and the fork token table; F2 m vs y per task with the logistic
fit and the tie ceiling; F3 (b) vs y beside the competitors; F4 rho_b(L) layer profile; F5 targeted-push
dose-response (axis vs matched random); F7 mediator clamp."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from c7 import FIGS, RESULTS, read_json  # noqa: E402

plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42, "ps.fonttype": 42})


def save(fig, name: str) -> None:
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIGS / f"{name}.{ext}", dpi=150)
    plt.close(fig)


def f1() -> None:
    d = read_json(RESULTS / "forks.json")["tasks"]
    tasks = [t for t in ("T10", "T2", "T03") if t in d]
    fig, axes = plt.subplots(1, len(tasks), figsize=(6 * len(tasks), 4.2))
    for ax, t in zip(np.atleast_1d(axes), tasks):
        v = d[t]
        cols = {}
        for pid, a in v["per_path"].items():
            s = a["series"]
            rate = [k / n if n else np.nan for k, n in zip(s["k"], s["n"])]
            key = f"{a['class']} ({a['cell']})"
            c = cols.setdefault(key, plt.get_cmap("tab10")(len(cols)))
            ax.plot(s["t"], rate, "-o", ms=3, color=c, alpha=0.6, label=key if key not in ax.get_legend_handles_labels()[1]
                    else None)
            if a["cp"]["p_value"] < 0.01:
                for i in a["cp"]["cps"]:
                    ax.axvline((s["t"][i - 1] + s["t"][i]) / 2, color=c, ls=":", lw=0.8)
        lines = []
        for f in v.get("forks", []):
            ax.axvline(f, color="k", lw=2, alpha=0.5)
            tm = v["token_maps"][str(f)]
            top = sorted(tm.values(), key=lambda x: -x["n"])[:4]
            dt = v.get("default_token_at_fork", {}).get(str(f), {}).get("tok")
            lines.append(f"fork f={f} (default token {dt!r}):")
            lines += [f"  {x['tok']!r}: q={x['q']:.2f} (n={x['n']})" for x in top]
        if lines:
            ax.text(0.98, 0.98, "\n".join(lines), transform=ax.transAxes, ha="right", va="top", fontsize=7,
                    family="monospace", bbox=dict(fc="w", alpha=0.9))
        ax.set_title(f"{t}: {v.get('status')} (forks {v.get('forks')})")
        ax.set_xlabel("generated-token position t of the base path")
        ax.set_ylabel("share of continuations whose label differs from the base path")
        ax.set_ylim(-0.03, 1.03)
        ax.legend(fontsize=7, loc="center right")
    save(fig, "F1_fork_series")


def f2_f3_f4() -> None:
    fa = read_json(RESULTS / "f_analysis.json")
    pa = read_json(RESULTS / "p2_analysis.json")
    cal = fa["F"]["calibration"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for ax, t in zip(axes, ("T10", "T2")):
        rows = fa["cells"][t]
        m = np.array([r["m"] for r in rows])
        y = np.array([r["y"] for r in rows])
        conf = np.array([r["confirmed"] for r in rows])
        ax.scatter(m[conf == 0], y[conf == 0], s=18, label="POP direction (not confirmed)")
        ax.scatter(m[conf == 1], y[conf == 1], s=30, marker="D", label="confirmed escaper (exp29 rule)")
        others = [c for c in cal["cells"] if c["cell"].startswith(t + "|") and "POP_" not in c["cell"]]
        for c in others:
            ax.scatter(c["m"], c["y"], marker="x", color="gray")
            ax.annotate(c["cell"].split("|")[1], (c["m"], c["y"]), fontsize=6, color="gray")
        xs = np.linspace(min(list(m) + [c["m"] for c in others]) - 0.5, max(list(m) + [c["m"] for c in others]) + 0.5,
                         100)
        ax.plot(xs, 1 / (1 + np.exp(-(cal["b0"] + cal["b1"] * xs))), "k-", lw=1, label="binomial GLM (all cells)")
        F = fa["F"][t]
        import c7
        src = read_json(c7.c3_path())["cells"].get(f"{t}|TWIN", {}).get("margin_source", "")
        ax.set_title(f"{t}: Spearman {F['rho']:.2f} (perm p {F['p_perm']:.3g}); tie ceiling {F['rho_max_ties']:.2f}")
        ax.set_xlabel("fork margin m (nats; T10 forks at generated tokens 10-11)" if "llr" not in src else
                      "48-token opening LLR (nats; fallback: no single fork on T2)")
        ax.set_ylabel("correct off-default share y")
        ax.legend(fontsize=7)
    save(fig, "F2_margin_vs_outcome")
    fig, axes = plt.subplots(2, 4, figsize=(15, 7))
    for row, t in enumerate(("T10", "T2")):
        rows = fa["cells"][t]
        y = np.array([r["y"] for r in rows])
        for ax, (k, nm) in zip(axes[row], (("b", "axis projection (b)"), ("pi_Pt", "P_t energy share"),
                                           ("norm", "raw displacement norm"), ("a_share", "U4 energy share (a)"))):
            x = np.array([r[k] for r in rows])
            ax.scatter(x, y, s=15)
            P = pa["P2"][t]
            rho = P["rho_b"] if k == "b" else P["competitors"][k]["rho"]
            ax.set_title(f"{t}: {nm}\nSpearman {rho:.2f}", fontsize=8)
            ax.set_xlabel(nm)
            ax.set_ylabel("y")
    save(fig, "F3_axis_vs_competitors")
    fig, ax = plt.subplots(figsize=(6, 4))
    for t in ("T10", "T2"):
        prof = pa["P2"][t]["layer_profile"]
        L = sorted(int(k) for k in prof)
        ax.plot(L, [prof[str(l)] for l in L], "-o", ms=3, label=t)
    ax.axhline(0, color="k", lw=0.5)
    ax.set_xlabel("block L")
    ax.set_ylabel("Spearman of (b)_L with y")
    ax.set_title("layer profile of the axis predictor (descriptive, no selection)")
    ax.legend()
    save(fig, "F4_rho_b_profile")


def f5() -> None:
    d = read_json(RESULTS / "targeted_push.json")
    tasks = [t for t in ("T10", "T2", "T03") if t in d]
    fig, axes = plt.subplots(1, len(tasks), figsize=(5 * len(tasks), 4))
    for ax, t in zip(np.atleast_1d(axes), tasks):
        for kind, c in (("AX", "tab:red"), ("RX", "tab:gray")):
            arms = [v for k, v in d[t]["arms"].items() if v["kind"] == kind]
            arms.sort(key=lambda v: v["s"])
            s = [v["s"] for v in arms]
            ax.plot(s, [v["y_runner_up"] for v in arms], "-o", color=c, label=f"{kind} correct runner-up")
            ax.plot(s, [v["pass"] for v in arms], "--", color=c, alpha=0.6, label=f"{kind} pass rate")
        ax.axhline(d[t]["twin"]["k_runner_up_correct"] / d[t]["twin"]["n"], color="b", lw=0.8, label="twin")
        ax.set_xscale("log")
        ax.set_xlabel("s (fraction of the default-to-runner-up distance along a)")
        ax.axvline(1.0, color="k", ls=":", lw=0.8)
        ax.text(1.05, 0.5, "committed s <= 1 | descriptive s 2-8 (fallback 8)", rotation=90, fontsize=7, va="center")
        cr = d[t].get("descriptive_crossing", {})
        ax.set_title(f"{t} (single-layer edit at block {d[t]['L_ax']}): escape at committed s<=1: "
                     f"{d[t]['smallest_escaping_s']}; axis escapes at s {cr.get('axis_escaping_s_incl_2_4_8')}, "
                     f"random at {cr.get('random_escaping_s_incl_2_4_8')}", fontsize=8)
        ax.set_ylabel("share of N = 30 CRN slots")
        ax.set_ylim(-0.03, 1.03)
        ax.legend(fontsize=7)
    save(fig, "F5_targeted_push")


def f7() -> None:
    d = read_json(RESULTS / "clamp.json")
    if d.get("status") == "not run":
        return
    keys = [k for k in d if "|" in k]
    fig, ax = plt.subplots(figsize=(1.2 * len(keys) + 3, 4))
    x = np.arange(len(keys))
    for i, (nm, c) in enumerate((("CLU", "tab:blue"), ("CLA", "tab:red"), ("CLR", "tab:gray"))):
        ax.bar(x + (i - 1) * 0.27, [d[k][nm]["y"] or 0 for k in keys], 0.27, color=c,
               label={"CLU": "push only", "CLA": "push + axis clamp", "CLR": "push + random clamp"}[nm])
    ax.set_xticks(x)
    ax.set_xticklabels(keys, rotation=30, fontsize=7)
    ax.set_ylabel("correct off-default share (N = 20, CRN-paired)")
    ax.set_title(f"mediator clamp: removed share axis {d['pooled']['removed_share']['CLA']}, random "
                 f"{d['pooled']['removed_share']['CLR']}")
    ax.legend(fontsize=7)
    save(fig, "F7_clamp")


def main() -> None:
    for f in (f1, f2_f3_f4, f5, f7):
        try:
            f()
        except (FileNotFoundError, KeyError, ValueError, TypeError, IndexError) as e:
            print(f"figure {f.__name__} skipped: {e}")


if __name__ == "__main__":
    main()
