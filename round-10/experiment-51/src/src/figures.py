#!/usr/bin/env python3
"""Figures F1-F8 (PDF + PNG, every axis labelled) from the raw rows and results/*.json."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis  # noqa: E402
import cluster  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "figures"
RES = ROOT / "results"
COL = {"T1.0": "#1f77b4", "T1.6": "#ff7f0e", "DTB": "#d62728", "RPB": "#9467bd", "IDEA": "#2ca02c", "NS": "#7f7f7f",
       "corpus": "#000000"}
plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42, "ps.fonttype": 42, "axes.spines.top": False,
                     "axes.spines.right": False})


def save(fig, name: str) -> None:
    FIG.mkdir(exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIG / f"{name}.pdf")
    fig.savefig(FIG / f"{name}.png", dpi=160)
    plt.close(fig)


def rj(name: str):
    p = RES / name
    return json.loads(p.read_text()) if p.exists() else None


def f1(rows_main, rows_ns, corpus_tab, tuned_name):
    ref = {e["name"]: e for e in corpus_tab}
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
    for ax, s in zip(axes, (0, 1)):
        for arm in ["T1.0", "T1.6", "DTB", "RPB", "IDEA"]:
            rs = analysis.stream_rows(rows_main, s, arm)
            f = np.array([r["F"] if r["F"] is not None else np.inf for r in rs])
            ax.plot(np.arange(1, len(f) + 1), np.minimum.accumulate(np.minimum(f, 1.0)), color=COL[arm], label=arm, lw=1.4)
        if rows_ns:
            rs = analysis.stream_rows(rows_ns, s, "NS")
            f = np.array([r["F"] if r["F"] is not None else np.inf for r in rs])
            ax.plot(np.arange(1, len(f) + 1), np.minimum.accumulate(np.minimum(f, 1.0)), color=COL["NS"], label="NS",
                    lw=1.2, ls="--")
        for nm, lab, ls in (("BF", "best fit (F=1)", ":"), (tuned_name, "tuned ab", "-."), ("c12", "c12", "--")):
            if nm in ref and ref[nm]["F"] is not None:
                ax.axhline(ref[nm]["F"], color="k", ls=ls, lw=0.8)
                ax.text(5, ref[nm]["F"] + 0.004, f"{lab} {ref[nm]['F']:.3f}", fontsize=7)
        if "c14" in ref:
            ax.text(5, 1.012, f"c14 F={ref['c14']['F']:.2f} (off scale)", fontsize=7)
        ax.set_title(f"seed {s}")
        ax.set_xlabel("LLM calls in the stream")
        ax.set_ylim(0.65, 1.03)
    axes[0].set_ylabel("best-so-far selection F (best fit = 1, lower is better)")
    axes[1].legend(fontsize=7, loc="lower left", ncol=2)
    save(fig, "F1_best_so_far")


def f2(cl):
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    for arm in ["T1.0", "T1.6", "DTB", "RPB", "IDEA", "NS"]:
        cur = [v["curves"] for k, v in cl["streams"].items() if v["arm"] == arm]
        if not cur:
            continue
        n = min(len(c["complete"]) for c in cur)
        x = np.array(cur[0]["calls"][:n])
        Y = np.array([c["complete"][:n] for c in cur], dtype=float)
        axes[0].plot(x, Y.mean(0), color=COL[arm], label=arm)
        axes[0].fill_between(x, Y.min(0), Y.max(0), color=COL[arm], alpha=0.15)
        m = min(len(c["leader_cum"]) for c in cur)
        L = np.array([c["leader_cum"][:m] for c in cur], dtype=float)
        xx = np.arange(1, m + 1)
        axes[1].plot(xx, L.mean(0), color=COL[arm], label=arm)
        axes[1].fill_between(xx, L.min(0), L.max(0), color=COL[arm], alpha=0.15)
    axes[0].set_xlabel("LLM calls (prefix)")
    axes[0].set_ylabel("behaviour clusters (complete linkage, >= 0.95)")
    axes[0].set_title("complete linkage on prefixes (mean of 2 seeds; band = seed range)")
    axes[1].set_xlabel("LLM calls")
    axes[1].set_ylabel("leader clusters (call order)")
    axes[1].set_title("leader clustering (band = seed range)")
    axes[0].legend(fontsize=7)
    save(fig, "F2_discovery_curves")


def f3(v1, corpus_tab, tuned_name):
    ref = {e["name"]: e["heldout_excess_pct"] for e in corpus_tab}
    ref["c12"] = ref.get("c12_vec", ref.get("c12"))
    sets = ["H-FSW5k", "H-OR3", "H-OR1", "H-OR2", "H-OR4", "H-W5k", "H-W10k", "H-SHIFT"]
    series = []
    for arm in ["T1.0", "T1.6", "DTB", "RPB"]:
        series.append((arm, v1["per_arm_heldout"].get(arm) or {}, COL[arm]))
    for arm in ("IDEA", "NS"):
        b = (v1.get("beside") or {}).get(arm) or {}
        series.append((arm, b.get("heldout_excess_pct") or {}, COL[arm]))
    for nm, c in (("BF", "#bbbbbb"), (tuned_name, "#444444"), ("c12", "#8c564b"), ("c14", "#e377c2"),
                  ("abWF_1_21", "#17becf")):
        series.append((nm if nm != tuned_name else f"tuned {nm}", ref.get(nm) or {}, c))
    fig, ax = plt.subplots(figsize=(11, 4))
    w = 0.8 / len(series)
    for i, (nm, d, c) in enumerate(series):
        y = [d.get(s, np.nan) for s in sets]
        ax.bar(np.arange(len(sets)) + i * w, y, width=w, color=c, label=nm)
    ax.set_xticks(np.arange(len(sets)) + 0.4 - w / 2)
    ax.set_xticklabels(sets)
    ax.set_ylabel("held-out excess over L1 (%)")
    ax.set_xlabel("held-out set")
    ax.set_yscale("log")
    ax.axhline(analysis.THR_FSW5K, color="r", lw=0.6, ls=":")
    ax.axhline(analysis.THR_OR3, color="r", lw=0.6, ls="--")
    ax.text(7.6, analysis.THR_OR3 * 1.05, "V1 bar OR3", fontsize=7, color="r")
    ax.text(7.6, analysis.THR_FSW5K * 0.82, "V1 bar FSW5k", fontsize=7, color="r")
    ax.legend(fontsize=7, ncol=6, loc="upper left")
    save(fig, "F3_heldout_excess")


def classical_mds(Dist: np.ndarray, k: int = 2) -> tuple[np.ndarray, float]:
    n = len(Dist)
    J = np.eye(n) - np.ones((n, n)) / n
    Bm = -0.5 * J @ (Dist ** 2) @ J
    w, V = np.linalg.eigh(Bm)
    idx = np.argsort(w)[::-1][:k]
    X = V[:, idx] * np.sqrt(np.maximum(w[idx], 0))
    dhat = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(-1))
    iu = np.triu_indices(n, 1)
    stress = float(np.sqrt(((Dist[iu] - dhat[iu]) ** 2).sum() / (Dist[iu] ** 2).sum()))
    return X, stress


def f4(cl, rows_by_stream, corpus, novel_pids):
    pts = []
    for key, st in cl["streams"].items():
        rows, D = rows_by_stream[key]
        vm = [analysis.valid(r) and not r.get("probe_failed") for r in rows]
        vr = [r for r, m in zip(rows, vm) if m]
        Dv = D[np.array(vm, dtype=bool)]
        best = {}
        for i, (r, l) in enumerate(zip(vr, st["labels"])):
            if l not in best or r["F"] < vr[best[l]]["F"]:
                best[l] = i
        for l, i in best.items():
            pts.append((vr[i]["F"], st["arm"], vr[i]["pid"], Dv[i]))
    pts.sort(key=lambda p: p[0])
    pts = pts[:300]
    ents = [e for e in corpus["entries"] if e.get("decisions") is not None]
    V = np.stack([p[3] for p in pts] + [np.array(e["decisions"], dtype=np.uint16) for e in ents])
    C = cluster.agree_counts(V)
    Dist = 1.0 - C / cluster.N_STATES
    np.fill_diagonal(Dist, 0.0)
    Dist = np.maximum(Dist, Dist.T)
    X, stress = classical_mds(Dist)
    fig, ax = plt.subplots(figsize=(7.5, 6))
    for arm in ["T1.0", "T1.6", "DTB", "RPB", "IDEA", "NS"]:
        m = [i for i, p in enumerate(pts) if p[1] == arm]
        if m:
            ax.scatter(X[m, 0], X[m, 1], s=12, color=COL[arm], label=f"{arm} ({len(m)})", alpha=0.75)
    off = len(pts)
    ax.scatter(X[off:, 0], X[off:, 1], s=18, marker="x", color="k", label=f"corpus ({len(ents)})")
    for j, e in enumerate(ents):
        if e["name"] in ("BF", "FF", "WF", "AWF", "SS", "c12", "c14", "abFF_5_24", "abWF_1_21") or \
                e["family"] == "ab_tuned":
            ax.annotate(e["name"], X[off + j], fontsize=7)
    nov = [i for i, p in enumerate(pts) if p[2] in novel_pids]
    if nov:
        ax.scatter(X[nov, 0], X[nov, 1], s=120, marker="*", color="gold", edgecolor="k", label="NOVEL", zorder=5)
    ax.set_xlabel("MDS dimension 1 (behaviour space: 1 - decision agreement)")
    ax.set_ylabel("MDS dimension 2")
    ax.set_title(f"Behaviour space (not activations): classical MDS of 1 - agreement, top-300 cluster leaders by F "
                 f"+ corpus; stress-1 = {stress:.3f}", fontsize=8)
    ax.legend(fontsize=7, loc="best")
    save(fig, "F4_behaviour_mds")
    return stress


def f5(rows_main):
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.5))
    for arm in ("DTB", "RPB"):
        forks = [r["fork"] for r in rows_main if r["arm"] == arm and r.get("fork")]
        H = np.full((len(forks), 48), np.nan)
        for i, f in enumerate(forks):
            h = f.get("H") or []
            H[i, :len(h)] = h
        axes[0].plot(np.arange(48), np.nanmean(H, 0), color=COL[arm], label=arm)
        js = [f["j"] for f in forks if not f.get("unforced") and f.get("j") is not None]
        axes[1].hist(js, bins=np.arange(0, 49), color=COL[arm], alpha=0.55, label=f"{arm} (n={len(js)})")
        cnt = Counter(f.get("class_realised") for f in forks if not f.get("unforced"))
        cls = ["identifier", "number", "operator", "keyword", "np-call", "punctuation"]
        x = np.arange(len(cls)) + (0.0 if arm == "DTB" else 0.4)
        axes[2].bar(x, [cnt.get(c, 0) / max(1, sum(cnt.values())) for c in cls], width=0.4, color=COL[arm], label=arm)
        axes[2].set_xticks(np.arange(len(cls)) + 0.2)
        axes[2].set_xticklabels(cls, rotation=30, fontsize=7)
    axes[0].set_xlabel("completion token position (REQ1)")
    axes[0].set_ylabel("mean top-20 entropy (nats)")
    axes[1].set_xlabel("fork position j")
    axes[1].set_ylabel("calls")
    axes[2].set_ylabel("share of forks")
    axes[2].set_xlabel("class of the realised token at j")
    for a in axes:
        a.legend(fontsize=7)
    save(fig, "F5_dtb_rpb_diagnostics")


def f6(rows_main, rows_ns):
    arms = ["T1.0", "T1.6", "DTB", "RPB", "IDEA"] + (["NS"] if rows_ns else [])
    types = ["ok", "syntax", "runtime", "shape", "timeout", "memory", "forbidden", "http"]
    cols = ["#2ca02c", "#d62728", "#ff7f0e", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#000000"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    bottom = np.zeros(len(arms))
    for t, c in zip(types, cols):
        v = []
        for a in arms:
            rs = [r for r in (rows_ns if a == "NS" else rows_main) if r["arm"] == a]
            v.append(sum(r["error_type"] == t for r in rs) / max(1, len(rs)))
        axes[0].bar(arms, v, bottom=bottom, color=c, label=t)
        bottom += np.array(v)
    axes[0].set_ylabel("share of calls")
    axes[0].set_xlabel("arm")
    axes[0].set_title("outcome of each call")
    axes[0].legend(fontsize=6, ncol=2)
    tr = [np.mean([r["truncated"] for r in (rows_ns if a == "NS" else rows_main) if r["arm"] == a]) for a in arms]
    dup = [np.mean([r["duplicate"] for r in (rows_ns if a == "NS" else rows_main) if r["arm"] == a]) for a in arms]
    x = np.arange(len(arms))
    axes[1].bar(x - 0.2, tr, width=0.4, label="truncated (no stop in 512 tokens)", color="#444444")
    axes[1].bar(x + 0.2, dup, width=0.4, label="in-stream duplicate", color="#aaaaaa")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(arms)
    axes[1].set_ylabel("share of calls")
    axes[1].set_xlabel("arm")
    axes[1].legend(fontsize=7)
    save(fig, "F6_validity_errors")


def f7(v5):
    if not v5:
        return
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.5))
    for k, c in (("births", "#d62728"), ("controls", "#7f7f7f")):
        r = [x["reversion_rate"] for x in v5["per_position"] if x["kind"] == k and x["reversion_rate"] is not None]
        axes[0].hist(r, bins=np.linspace(0, 1, 11), alpha=0.6, color=c, label=f"{k} (n={len(r)})")
    axes[0].set_xlabel("reversion rate per position (share of 20 continuations agreeing >= 0.95 with a parent)")
    axes[0].set_ylabel("positions")
    axes[0].legend(fontsize=7)
    fm = v5["per_founder_max"]
    axes[1].scatter([x["control_max"] for x in fm], [x["birth_max"] for x in fm], s=14, color="k")
    axes[1].plot([0, 1], [0, 1], ls=":", color="grey")
    axes[1].set_xlabel("max reversion at control positions")
    axes[1].set_ylabel("max reversion at birth positions")
    axes[1].set_title(f"sign test p = {v5['sign_test']['p_two_sided']}", fontsize=8)
    save(fig, "F7_v5_reversion")


def f8(v6):
    if not v6:
        return
    arms = list(v6["per_arm"])
    r = [v6["per_arm"][a]["rate"] for a in arms]
    lo = [v6["per_arm"][a]["rate"] - v6["per_arm"][a]["wilson"][0] for a in arms]
    hi = [v6["per_arm"][a]["wilson"][1] - v6["per_arm"][a]["rate"] for a in arms]
    cl = [v6["per_arm"][a]["new_idea_claim_share"] for a in arms]
    fig, ax = plt.subplots(figsize=(6.5, 3.5))
    x = np.arange(len(arms))
    ax.bar(x - 0.2, r, width=0.4, yerr=[lo, hi], color=[COL[a] for a in arms], capsize=3,
           label="rename rate (>= 0.95 agreement with a prompt parent)")
    ax.bar(x + 0.2, cl, width=0.4, color="#cccccc", label="comments claim a new idea (regex)")
    ax.axhline(0.4, color="k", ls=":", lw=0.7)
    ax.axhline(0.2, color="k", ls="--", lw=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(arms)
    ax.set_xlabel("arm")
    ax.set_ylabel("share of valid offspring")
    ax.legend(fontsize=7)
    save(fig, "F8_v6_renames")


def main() -> None:
    rows_main = analysis.load_rows("main")
    rows_ns = analysis.load_rows("ns")
    corpus_res = rj("corpus.json")
    c2 = json.loads((ROOT / "predictions" / "commit2.json").read_text())
    tuned = c2["tuned_ab"]["name"]
    cl = rj("clusters.json")
    v1 = rj("v1.json")
    corpus = json.loads((ROOT / "data" / "corpus" / "corpus.json").read_text())
    f1(rows_main, rows_ns, corpus_res["table"], tuned)
    f2(cl)
    if v1:
        f3(v1, corpus_res["table"], tuned)
    rows_by_stream = {}
    for key, st in cl["streams"].items():
        rows = analysis.stream_rows(rows_ns if st["run"] == "ns" else rows_main, st["seed"], st["arm"], st["calls"])
        rows_by_stream[key] = (rows, analysis.load_decisions(st["run"], st["seed"], st["arm"])[:len(rows)])
    v3 = rj("v3_final.json") or {}
    novel = {c["pid"] for c in v3.get("novel", [])}
    stress = f4(cl, rows_by_stream, corpus, novel)
    f5(rows_main)
    f6(rows_main, rows_ns)
    f7(rj("v5.json"))
    f8(rj("v6.json"))
    (RES / "figures_meta.json").write_text(json.dumps({"F4_stress1": stress}, indent=1))
    print("figures written; F4 stress", stress)


if __name__ == "__main__":
    main()
