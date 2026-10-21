"""Figures (PDF + PNG, Okabe-Ito colourblind palette, Type 42 fonts) drawn only from results/*.json."""

from __future__ import annotations

import json
from collections import Counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from config import ALL_TASKS, FIGS, RESULTS, TASKS  # noqa: E402

plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.size": 8, "axes.titlesize": 9})
OKABE = ["#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7", "#999999", "#000000"]


def colour_map(labels: list[str]) -> dict[str, str]:
    cm, i = {}, 0
    for l in labels:
        if l == "invalid":
            cm[l] = "#BBBBBB"
        elif l == "other":
            cm[l] = "#000000"
        else:
            cm[l] = OKABE[i % 7]
            i += 1
    return cm


def save(fig, name: str) -> None:
    for ext in ("pdf", "png"):
        fig.savefig(FIGS / f"{name}.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_walk(walk: dict) -> None:
    tasks = [t for t in ALL_TASKS if isinstance(walk.get(t), dict) and walk[t].get("steps")]
    if not tasks:
        return
    fig, axes = plt.subplots(1, len(tasks), figsize=(3.0 * len(tasks), 2.8), squeeze=False)
    for ax, t in zip(axes[0], tasks):
        steps = walk[t]["steps"]
        labs = TASKS[t]["catalogue"] + ["other", "invalid"]
        cm = colour_map(labs)
        xs = [f"s{s['step']}r{s['round']}" for s in steps]
        bottom = [0.0] * len(steps)
        for l in labs:
            vals = [s["counts"].get(l, 0) / max(1, s["n"]) for s in steps]
            if sum(vals) == 0:
                continue
            ax.bar(xs, vals, bottom=bottom, color=cm[l], label=l, width=0.8)
            bottom = [b + v for b, v in zip(bottom, vals)]
        ax.plot(xs, [s["pass_rate"] or 0 for s in steps], "k--", marker="o", ms=3, lw=1, label="pass rate (attempted)")
        ax.set_title(f"{t}: {walk[t]['status']}")
        ax.set_ylim(0, 1.05)
        ax.tick_params(axis="x", rotation=60)
        ax.legend(fontsize=5, loc="lower left")
    axes[0][0].set_ylabel("share of 50 programs")
    fig.suptitle("Token walk: composition per step/mask round (vetoed set grows left to right)", y=1.04)
    save(fig, "fig1_token_walk")


def fig_will_can(c3: dict) -> None:
    cells = c3.get("cells", [])
    if not cells:
        return
    fig, ax = plt.subplots(figsize=(5.0, 3.8))
    seen = set()
    for c in cells:
        if c["will"] is None or c["can"] is None:
            continue
        mk = {1: "s", 2: "^"}.get(c["rung"], "o")
        col = OKABE[ALL_TASKS.index(c["task"]) % 7]
        lab = c["task"] if c["task"] not in seen else None
        seen.add(c["task"])
        ax.scatter(c["can"], c["will"], marker=mk, color=col, edgecolor="k", s=40, lw=0.5, label=lab,
                   zorder=3)
    q = sorted([c for c in cells if c.get("qualifies") and c["will"] is not None and c["can"] is not None],
               key=lambda c: (c["task"], c["S"]))
    key_lines = []
    for j, c in enumerate(q, 1):
        same = [x for x in q[:j - 1] if abs(x["can"] - c["can"]) < 0.03 and abs(x["will"] - c["will"]) < 0.03]
        ax.annotate(str(j), (c["can"], c["will"]), fontsize=6, xytext=(4 + 7 * len(same), 4),
                    textcoords="offset points", fontweight="bold")
        key_lines.append(f"{j} {c['task']}:{c['S']} (will {c['will']:.2f})")
    if key_lines:
        ax.text(0.02, 0.62, "C3 cells\n" + "\n".join(key_lines), transform=ax.transAxes, fontsize=5.5,
                va="top", bbox={"boxstyle": "round", "fc": "white", "ec": "#999999", "lw": 0.5})
    ax.axhline(0.10, color="k", ls=":", lw=0.8)
    ax.axhline(0.30, color="k", ls="--", lw=0.8)
    ax.axvline(0.7, color="#999999", ls=":", lw=0.8)
    ax.set_xlabel("can (forced, labelled-and-correct)")
    ax.set_ylabel("will (LOS: share labelled S)")
    ax.set_xlim(-0.03, 1.05)
    ax.set_ylim(-0.05, 1.08)
    ax.legend(fontsize=6, loc="upper left", title="task", title_fontsize=6)
    ax.set_title("Will vs can; numbered = C3 cells (rung >= 3, can >= 0.7)\n"
                 "square rung 1, triangle rung 2, circle rung >= 3; lines at 0.10 / 0.30", fontsize=7)
    save(fig, "fig2_will_vs_can")


def fig_reemergence(walk: dict) -> None:
    tasks = [t for t in ALL_TASKS if isinstance(walk.get(t), dict) and walk[t].get("steps")]
    if not tasks:
        return
    fig, ax = plt.subplots(figsize=(4.2, 2.6))
    for i, t in enumerate(tasks):
        steps = [s for s in walk[t]["steps"] if s["step"] >= 1]
        if not steps:
            continue
        xs = list(range(len(steps)))
        re = [max(s["reemergence"].values()) if s["reemergence"] else 0 for s in steps]
        inv = [s["invalid_share"] or 0 for s in steps]
        ax.plot(xs, re, marker="o", color=OKABE[i % 7], label=f"{t} max re-emergence")
        ax.plot(xs, inv, marker="x", ls="--", color=OKABE[i % 7], label=f"{t} invalid share")
    ax.set_xlabel("veto round index (step >= 1)")
    ax.set_ylabel("share")
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=5, ncol=1, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    ax.set_title("Vetoed algorithms come back or the code degenerates")
    save(fig, "fig3_reemergence")


def fig_longform(lf: dict) -> None:
    """Role-based colours (labels differ per task): default / other catalogue algorithms / off-catalogue / invalid;
    the modal non-default catalogue algorithm is written on each bar."""
    if not lf:
        return
    keys = list(lf)
    roles = [("default", OKABE[0]), ("other catalogue algorithms", OKABE[4]), ("off-catalogue ('other')", "#000000"),
             ("invalid (no / broken code)", "#BBBBBB")]
    fig, ax = plt.subplots(figsize=(max(5, 0.5 * len(keys)), 3.2))
    for i, k in enumerate(keys):
        t = k.split("|")[0]
        cnt, n = lf[k]["counts"], max(1, lf[k]["N"])
        D = TASKS[t]["default"]
        alt = {l: v for l, v in cnt.items() if l in TASKS[t]["catalogue"] and l != D}
        vals = [cnt.get(D, 0) / n, sum(alt.values()) / n, cnt.get("other", 0) / n, cnt.get("invalid", 0) / n]
        b = 0.0
        for (name, col), v in zip(roles, vals):
            ax.bar(i, v, bottom=b, color=col, label=name if i == 0 else None, width=0.8)
            b += v
        top = max(alt, key=alt.get) if alt else ""
        if top:
            ax.text(i, vals[0] + vals[1] / 2, top.replace("_", " "), ha="center", va="center", fontsize=4.2,
                    rotation=90, color="white")
        ax.text(i, 1.01, f"N={lf[k]['N']}\nnovel={lf[k]['novel_count']}", ha="center", fontsize=4.2)
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels([k.replace("|think_", "|").replace("|", "\n") for k in keys], fontsize=4.5)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("share of programs")
    ax.legend(fontsize=5, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    ax.set_title("Long-form novelty instructions (LF1/LF2): what the code actually is", fontsize=8)
    save(fig, "fig4_longform")


def fig_sham(walk: dict) -> None:
    rows = [(t, walk[t]["sham_vs_distinctive"]) for t in ALL_TASKS if isinstance(walk.get(t), dict)
            and "sham_ngram" in (walk[t].get("sham_vs_distinctive") or {})]
    if not rows:
        return
    fig, ax = plt.subplots(figsize=(3.6, 2.4))
    xs = range(len(rows))
    ax.bar([x - 0.2 for x in xs], [r["sham_default_share"] or 0 for _, r in rows], 0.4, color=OKABE[1],
           label="sham veto")
    ax.bar([x + 0.2 for x in xs], [r["distinctive_default_share"] or 0 for _, r in rows], 0.4, color=OKABE[5],
           label="distinctive veto (step 1, round 0)")
    for x, (_, r) in zip(xs, rows):
        ax.text(x + 0.2, (r["distinctive_default_share"] or 0) + 0.02,
                f"invalid\n{(r.get('distinctive_invalid_share') or 0):.0%}", ha="center", fontsize=5)
        ax.text(x - 0.2, (r["sham_default_share"] or 0) + 0.02,
                f"invalid\n{(r.get('sham_invalid_share') or 0):.0%}", ha="center", fontsize=5)
    ax.set_xticks(list(xs))
    ax.set_xticklabels([t for t, _ in rows])
    ax.set_ylabel("default share of attempted programs")
    ax.set_ylim(0, 1.25)
    ax.legend(fontsize=6, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    ax.set_title("Sham vs distinctive n-gram veto (bars: default share of valid programs)", fontsize=7)
    save(fig, "fig5_sham_vs_distinctive")


def main() -> None:
    def rj(n):
        p = RESULTS / n
        return json.loads(p.read_text()) if p.exists() else {}

    walk = rj("walk.json")
    fig_walk(walk)
    fig_will_can(rj("c3.json"))
    fig_reemergence(walk)
    fig_longform(rj("longform.json"))
    fig_sham(walk)


if __name__ == "__main__":
    main()
