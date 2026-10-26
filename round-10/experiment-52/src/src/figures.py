#!/usr/bin/env python3
"""S12 figures (PDF + PNG, matplotlib, colour-blind palette). F1 best-so-far selection F vs calls; F2 discovery curves;
F3 held-out excess of each arm's best vs baselines; F4 behaviour map (classical MDS of 1 - P10 agreement: behaviour
space, NOT activation space; stress stated); F5 DTB/RPB diagnostics; F6 validity and error types; F7 V5 reversion and
V6 rename rates."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

import analysis as AN  # noqa: E402
import clusters as CL  # noqa: E402
import common as C  # noqa: E402

plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})
COL = {"T1.0": "#0072B2", "T1.6": "#56B4E9", "DTB": "#D55E00", "RPB": "#E69F00", "IDEA": "#009E73", "NS": "#7f7f7f"}
ARMS = ["T1.0", "T1.6", "DTB", "RPB", "IDEA", "NS"]


def save(fig, name: str) -> None:
    for ext in ("pdf", "png"):
        fig.savefig(C.FIGS / f"{name}.{ext}", bbox_inches="tight")
    plt.close(fig)


def f1_best_so_far(ev: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.2), sharey=True)
    for ax, S in zip(axes, C.SEEDS):
        for a in ARMS:
            calls = sorted(c for (s, arm, c) in ev if s == S and arm == a)
            if not calls:
                continue
            best, ys = 1.0, []
            for c in calls:
                e = ev[(S, a, c)]
                if e["valid"] and e["F"] is not None:
                    best = min(best, e["F"])
                ys.append(best)
            ax.plot(np.array(calls) + 1, ys, label=a, color=COL[a], lw=1.4)
        ax.set_title(f"seed {S}")
        ax.set_xlabel("calls (LLM samples)")
        ax.axhline(1.0, color="k", lw=0.6, ls=":")
    axes[0].set_ylabel("best-so-far selection F (BF = 1, lower is better)")
    axes[1].legend(frameon=False, fontsize=8)
    fig.suptitle("F1. Best-so-far selection fitness vs calls")
    save(fig, "F1_best_so_far")


def f2_discovery(cl: dict) -> None:
    fig, ax = plt.subplots(figsize=(5.5, 3.4))
    for a in ARMS:
        curves = [np.array(cl["per_arm_seed"][f"S{S}-{a}"]["discovery_curve"]) for S in C.SEEDS
                  if f"S{S}-{a}" in cl["per_arm_seed"]]
        if not curves:
            continue
        n = min(len(c) for c in curves)
        M = np.stack([c[:n] for c in curves])
        x = np.arange(1, n + 1)
        ax.plot(x, M.mean(0), color=COL[a], label=a, lw=1.5)
        ax.fill_between(x, M.min(0), M.max(0), color=COL[a], alpha=0.2, lw=0)
    ax.set_xlabel("calls")
    ax.set_ylabel("behaviour clusters discovered")
    ax.set_title("F2. Discovery curves (mean of seeds 2-3; band = seed range)")
    ax.legend(frameon=False, fontsize=8)
    save(fig, "F2_discovery_curves")


def f3_heldout(hb: dict) -> None:
    sets = ["H-FSW5k", "H-OR3", "H-W5k", "H-W10k", "H-SHIFT", "H-OR1", "H-OR2", "H-OR4"]
    rows = [("BF", {s: hb["bf"][s] for s in sets})]
    for a in ARMS:
        if a in hb["artifact_best"]:
            rows.append((f"best {a}", hb["artifact_best"][a]["excess"]))
    comp = hb["comparison"]
    tn = [k for k in comp if k.startswith("tuned_ab")][0]
    for k, lab in [(tn, "tuned ab"), ("FunSearch-c12-vec", "c12"), ("FunSearch-c14", "c14"),
                   ("RAISE-appendixE.1.1", "RAISE")]:
        if k in comp:
            rows.append((lab, comp[k]["excess"]))
    fig, ax = plt.subplots(figsize=(10, 3.6))
    w = 0.8 / len(rows)
    cmap = plt.get_cmap("tab20")
    for i, (lab, ex) in enumerate(rows):
        vals = [100 * ex.get(s, np.nan) if ex.get(s) is not None else np.nan for s in sets]
        ax.bar(np.arange(len(sets)) + i * w, vals, w, label=lab,
               color=COL.get(lab.replace("best ", ""), cmap(i % 20)))
    ax.set_xticks(np.arange(len(sets)) + 0.4 - w / 2)
    ax.set_xticklabels(sets)
    ax.set_ylabel("excess bins over L1 (%)")
    ax.set_title("F3. Held-out excess of each arm's best program (selected on SEL only) vs baselines")
    ax.legend(frameon=False, fontsize=7, ncol=4)
    save(fig, "F3_heldout_excess")


def classical_mds(D: np.ndarray, k: int = 2) -> tuple[np.ndarray, float]:
    n = len(D)
    J = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * J @ (D ** 2) @ J
    w, V = np.linalg.eigh(B)
    idx = np.argsort(w)[::-1][:k]
    X = V[:, idx] * np.sqrt(np.clip(w[idx], 0, None))
    Dh = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(-1))
    stress = float(np.sqrt(((D - Dh) ** 2).sum() / (D ** 2).sum()))
    return X, stress


def f4_behaviour_map(gen: dict, ev: dict, dec: np.ndarray) -> None:
    Cs = AN.matched_calls(ev)
    pts, lab, kind = [], [], []
    for S in C.SEEDS:
        for a in ARMS:
            n_arm = len([1 for (s, arm, c) in ev if s == S and arm == a])
            Cm = min(Cs[S], n_arm) if a != "NS" else n_arm
            vecs, kept = AN.offspring_vectors(AN.arm_calls(ev, S, a, Cm), dec)
            if not kept:
                continue
            labs, _ = AN.cluster_programs(vecs)
            sizes = {}
            for l in labs:
                sizes[int(l)] = sizes.get(int(l), 0) + 1
            for l, _ in sorted(sizes.items(), key=lambda x: -x[1])[:25]:
                i = int(np.nonzero(labs == l)[0][0])
                pts.append(vecs[i])
                lab.append(a)
                kind.append("cluster")
    cor = json.loads((C.RESULTS / "corpus.json").read_text())["entries"]
    cdec = np.load(C.DATA / "corpus_decisions.npy")
    for e, v in zip(cor, cdec):
        if e["priority_form"] and e.get("p10_sha256") and not e["name"].startswith("dep-"):
            pts.append(v)
            lab.append("corpus")
            kind.append(e["family"])
    ab = np.load(C.DATA / "ab_decisions.npy")
    for j in range(0, len(ab), 97):
        pts.append(ab[j])
        lab.append("ab grid (every 97th)")
        kind.append("ab")
    v3 = json.loads((C.RESULTS / "v3_final.json").read_text())
    for c in v3:
        if c.get("pass_novelty_filter"):
            pts.append(dec[c["probe_row"]])
            lab.append("V3 candidate (both filters)")
            kind.append("v3")
    P = np.stack(pts)
    A = CL.agreement_matrix(P, P)
    D = 1 - (A + A.T) / 2
    np.fill_diagonal(D, 0)
    X, stress = classical_mds(D)
    fig, ax = plt.subplots(figsize=(6.5, 5.2))
    style = {"corpus": ("k", "s", 22), "ab grid (every 97th)": ("#999999", ".", 12),
             "V3 candidate (both filters)": ("#CC79A7", "*", 40)}
    for g in dict.fromkeys(lab):
        ii = [i for i, x in enumerate(lab) if x == g]
        c, m, s = style.get(g, (COL.get(g, "b"), "o", 14))
        ax.scatter(X[ii, 0], X[ii, 1], c=c, marker=m, s=s, label=g, alpha=0.75, linewidths=0)
    ax.set_title(f"F4. Behaviour map: classical MDS of 1 - P10 agreement (stress {stress:.2f})\n"
                 "behaviour space (bin choices on 2,000 probe states), not activation space", fontsize=8)
    ax.set_xlabel("MDS 1")
    ax.set_ylabel("MDS 2")
    ax.legend(frameon=False, fontsize=7, markerscale=1.2)
    save(fig, "F4_behaviour_map")
    C.write_json(C.RESULTS / "behaviour_map.json", {"stress": stress, "n_points": len(P),
                                                    "groups": {g: lab.count(g) for g in dict.fromkeys(lab)}})


def f5_branch(gen: dict) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.1))
    for a in ("DTB", "RPB"):
        Hs = np.full((0, 48), np.nan)
        js, cls = [], {}
        prof = []
        for S in C.SEEDS:
            for (s, arm, c), r in gen.items():
                if s != S or arm != a or not r.get("branch"):
                    continue
                br = r["branch"]
                h = np.full(48, np.nan)
                h[:len(br["H"])] = br["H"][:48]
                prof.append(h)
                if br.get("j") is not None:
                    js.append(br["j"])
                    cls[br.get("token_class_gen_j", "other")] = cls.get(br.get("token_class_gen_j", "other"), 0) + 1
        Hs = np.stack(prof) if prof else Hs
        axes[0].plot(np.arange(48), np.nanmean(Hs, 0), color=COL[a], label=a)
        axes[1].hist(js, bins=np.arange(0, 49), color=COL[a], alpha=0.5, label=a)
        keys = ["identifier", "number", "operator", "keyword", "np-call", "other"]
        tot = max(1, sum(cls.values()))
        axes[2].bar(np.arange(len(keys)) + (0.4 if a == "RPB" else 0), [cls.get(k, 0) / tot for k in keys], 0.4,
                    color=COL[a], label=a)
        axes[2].set_xticks(np.arange(len(keys)) + 0.2)
        axes[2].set_xticklabels(keys, rotation=30, fontsize=7)
    axes[0].set_title("mean entropy of r1 position (top-20)")
    axes[0].set_xlabel("body token position")
    axes[1].set_title("forced position j")
    axes[1].set_xlabel("j")
    axes[2].set_title("token class at j (sampled token)")
    for ax in axes:
        ax.legend(frameon=False, fontsize=7)
    fig.suptitle("F5. DTB vs RPB diagnostics (seeds 2-3)")
    save(fig, "F5_branch_diagnostics")


def f6_validity(cl: dict) -> None:
    keys = ["ok", "syntax", "forbidden", "runtime", "shape", "nonfinite", "timeout", "memory", "gen_failed"]
    fig, ax = plt.subplots(figsize=(8, 3.2))
    labels = []
    bottom = np.zeros(0)
    data = []
    for S in C.SEEDS:
        for a in ARMS:
            k = f"S{S}-{a}"
            if k not in cl["per_arm_seed"]:
                continue
            et = cl["per_arm_seed"][k]["desc"]["error_types"]
            n = sum(et.values())
            data.append([et.get(x, 0) / n for x in keys])
            labels.append(k)
    data = np.array(data)
    bottom = np.zeros(len(labels))
    cmap = plt.get_cmap("tab10")
    for i, x in enumerate(keys):
        ax.bar(np.arange(len(labels)), data[:, i], bottom=bottom, label=x, color=cmap(i))
        bottom += data[:, i]
    ax.set_xticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, rotation=45, fontsize=7, ha="right")
    ax.set_ylabel("share of calls")
    ax.set_title("F6. Validity and error types per arm-seed (calls 1..C)")
    ax.legend(frameon=False, fontsize=7, ncol=5, loc="lower right")
    save(fig, "F6_validity_errors")


def f7_rates(vd: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(8, 3))
    rr = vd["V6"]["rates"]
    arms = [a for a in ARMS if a in rr and rr[a]["rename"] is not None]
    axes[0].bar(arms, [rr[a]["rename"] for a in arms], color=[COL[a] for a in arms])
    axes[0].axhline(0.4, ls=":", color="k", lw=0.8)
    axes[0].set_title("V6: share of valid offspring agreeing >= 0.95 with a parent", fontsize=8)
    v5p = C.RESULTS / "v5.json"
    if v5p.exists():
        s = json.loads(v5p.read_text())["summary"]
        vals = [s.get("decision_reversion_mean"), s.get("control_reversion_mean")]
        axes[1].bar(["decision position", "random control"], [v if v is not None else 0 for v in vals],
                    color=["#D55E00", "#999999"])
        axes[1].set_title(f"V5: reversion to a parent after forcing the argmax (n={s.get('n_paired')})", fontsize=8)
    else:
        axes[1].text(0.5, 0.5, "V5 not run", ha="center")
    save(fig, "F7_v5_v6_rates")


@logger.catch(reraise=True)
def main() -> None:
    C.setup_logging("figures")
    gen, ev = AN.load_rows()
    dec = AN.load_decisions()
    cl = json.loads((C.RESULTS / "analysis_clusters.json").read_text())
    hb = json.loads((C.RESULTS / "heldout_best.json").read_text())
    vd = json.loads((C.RESULTS / "verdicts.json").read_text())
    for f, args in [(f1_best_so_far, (ev,)), (f2_discovery, (cl,)), (f3_heldout, (hb,)),
                    (f4_behaviour_map, (gen, ev, dec)), (f5_branch, (gen,)), (f6_validity, (cl,)), (f7_rates, (vd,))]:
        try:
            f(*args)
            logger.info(f"{f.__name__} done")
        except Exception:  # noqa: BLE001 - one failing figure must not stop the others
            logger.exception(f"{f.__name__} failed")


if __name__ == "__main__":
    main()
