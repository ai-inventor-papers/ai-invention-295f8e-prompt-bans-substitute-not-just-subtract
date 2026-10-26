"""Data figures (matplotlib, deterministic): landing bars per Y across arms, forest plot of per-event log-score
differences, copy rate vs avoidance, default share by arm.  PNG + PDF under figures/."""

from __future__ import annotations

import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

from analysis import c1  # noqa: E402

from .core import FIGS  # noqa: E402

plt.rcParams.update({"font.size": 8, "pdf.fonttype": 42, "ps.fonttype": 42, "axes.spines.top": False,
                     "axes.spines.right": False})
ROLE_COLORS = {"Y (shown)": "#9e9e9e", "default": "#1f3b73", "other survivor": "#4daf4a", "'other'": "#e6a023",
               "invalid": "#d9d9d9"}


def _save(fig, name: str) -> None:
    FIGS.mkdir(exist_ok=True)
    fig.savefig(FIGS / f"{name}.png", dpi=180, bbox_inches="tight")
    fig.savefig(FIGS / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    logger.info(f"figure {name} written")


def _short(label: str) -> str:
    return label.replace("_", " ")[:14]


def landing_bars(meta: dict, fc: dict, arms: dict) -> None:
    keys = list(meta)
    ncol = 6
    nrow = math.ceil(len(keys) / ncol)
    fig, axes = plt.subplots(nrow, ncol, figsize=(2.6 * ncol, 2.5 * nrow), squeeze=False)
    for ax, key in zip(axes.flat, keys):
        m = meta[key]
        a = arms.get(key, {})
        vr = m["veto_round_used"]
        cols = [("COPY", a.get("copy")), (f"VETO r{vr}" if vr else "VETO", a.get(f"veto_r{vr or 1}")),
                ("NAMED", a.get("named")), ("UNNAMED", a.get("unnamed"))]
        for i, (name, st) in enumerate(cols):
            if not st or not st["n_programs"]:
                continue
            n = st["n_programs"]
            lc = st["label_counts"]
            parts = {"Y (shown)": lc.get(m["Y"], 0), "default": lc.get(m["default"], 0),
                     "other survivor": sum(v for k, v in lc.items() if k in m["survivors"] and k != m["default"]),
                     "'other'": sum(v for k, v in lc.items() if k not in m["survivors"] and k not in (m["Y"], "invalid")),
                     "invalid": lc.get("invalid", 0)}
            bottom = 0.0
            for role, v in parts.items():
                ax.bar(i, v / n, bottom=bottom, color=ROLE_COLORS[role], width=0.7, edgecolor="white", linewidth=0.3)
                bottom += v / n
            mod = st.get("modal_nonY") or []
            if mod:
                ax.text(i, 1.02, _short(mod[0]), ha="center", va="bottom", fontsize=5.5, rotation=60)
        ax.set_xticks(range(4))
        ax.set_xticklabels(["COPY", "VETO", "NAMED", "UNN."], fontsize=6)
        ax.set_ylim(0, 1.45)
        ax.set_yticks([0, 0.5, 1])
        t1 = {f: c1.top1(fc[key][f], m["survivors"]) for f in c1.FAMILIES}
        ax.set_title(f"{key}{' *' if m['priority'] else ''}\n"
                     f"S:{_short('/'.join(t1['SUBTRACT']))[:12]} L:{_short(t1['LADDER'][0])[:10]} "
                     f"A:{_short('/'.join(t1['ASSOCIATE']))[:12]} P:{_short('/'.join(t1['PROXIMITY']))[:12]}",
                     fontsize=5.5)
    for ax in list(axes.flat)[len(keys):]:
        ax.axis("off")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in ROLE_COLORS.values()]
    fig.legend(handles, list(ROLE_COLORS), loc="lower center", ncol=5, fontsize=8, frameon=False)
    fig.suptitle("Program composition per banned algorithm Y and arm (label above bar = modal non-Y label; "
                 "S/L/A/P = committed SUBTRACT / LADDER / ASSOCIATE / PROXIMITY top-1; * = priority Y)", fontsize=9)
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))
    _save(fig, "landing_bars")


def forest(named: list[dict], res: dict) -> None:
    sel = [e for e in named if e["gate_pass"] and e["disagreeing"]]
    if not sel:
        return
    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    for i, (a, b) in enumerate(c1.TEST_PAIRS):
        d = [e["logscore"][a] - e["logscore"][b] for e in sel]
        y = np.full(len(d), i) + np.linspace(-0.25, 0.25, len(d)) if len(d) > 1 else np.full(len(d), i)
        ax.scatter(d, y, s=10, color="#555555", alpha=0.7, zorder=3)
        tests = res["tests"].get("tests") if res["tests"].get("run") else None
        mean = float(np.mean(d))
        if tests:
            t = tests[i]
            ax.errorbar(mean, i, xerr=[[mean - t["ci95_task_cluster"][0]], [t["ci95_task_cluster"][1] - mean]],
                        fmt="D", color="#c0392b", capsize=3, zorder=4)
            ax.text(ax.get_xlim()[1] if False else max(d) + 0.3, i, f"p_Holm={t['p_holm']:.3f}", va="center", fontsize=7)
        else:
            ax.scatter([mean], [i], marker="D", color="#c0392b", zorder=4)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_yticks(range(len(c1.TEST_PAIRS)))
    ax.set_yticklabels([f"{a} - {b}" for a, b in c1.TEST_PAIRS])
    ax.set_xlabel("per-event difference in mean log score (nats); > 0 favours the ban-free family")
    ax.set_title(f"Gated disagreeing NAMED events (n = {len(sel)}); diamonds = mean with task-cluster 95% CI")
    _save(fig, "forest_logscore_differences")


def copy_vs_avoidance(meta: dict, arms: dict) -> None:
    xs, ys, pr = [], [], []
    for key, m in meta.items():
        a = arms.get(key, {})
        if "copy" in a and "named" in a:
            xs.append(a["copy"]["Y_share"])
            ys.append(a["named"]["avoidance"])
            pr.append(m["priority"])
    if not xs:
        return
    fig, ax = plt.subplots(figsize=(4, 3.4))
    for p, c, lab in [(True, "#c0392b", "priority Y"), (False, "#1f3b73", "non-priority Y")]:
        ax.scatter([x for x, q in zip(xs, pr) if q == p], [y for y, q in zip(ys, pr) if q == p], s=18, color=c, label=lab)
    ax.axhline(0.5, color="gray", lw=0.7, ls="--")
    ax.set_xlabel("copy rate (share of COPY-twin attempts labelled Y)")
    ax.set_ylabel("NAMED avoidance (1 - share labelled Y)")
    ax.set_xlim(-0.03, 1.03)
    ax.set_ylim(-0.03, 1.03)
    ax.legend(frameon=False, fontsize=7)
    _save(fig, "copy_rate_vs_avoidance")


def default_share(meta: dict, arms: dict) -> None:
    cols = ["copy", "veto_final", "named", "unnamed"]
    vals = {c: [] for c in cols}
    for key, m in meta.items():
        a = arms.get(key, {})
        vk = sorted(k for k in a if k.startswith("veto_r"))
        mp = {"copy": a.get("copy"), "veto_final": a.get(vk[-1]) if vk else None, "named": a.get("named"),
              "unnamed": a.get("unnamed")}
        for c in cols:
            if mp[c] and mp[c]["n_attempts"]:
                vals[c].append(mp[c]["default_share"])
    fig, ax = plt.subplots(figsize=(4.2, 3.2))
    for i, c in enumerate(cols):
        v = vals[c]
        if not v:
            continue
        ax.bar(i, np.mean(v), color="#9ecae1", width=0.6)
        ax.scatter(np.full(len(v), i) + np.linspace(-0.2, 0.2, len(v)), v, s=8, color="#1f3b73", zorder=3)
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels(["COPY", "VETO (final)", "NAMED", "UNNAMED"])
    ax.set_ylabel("share of attempts = context-free default")
    ax.set_title("Snap-back to the default (bars = mean over Y)")
    _save(fig, "default_share_by_arm")


def make_figures(samples, meta, fc, arms, named, res_named) -> None:
    landing_bars(meta, fc, arms)
    forest(named, res_named)
    copy_vs_avoidance(meta, arms)
    default_share(meta, arms)
