#!/usr/bin/env python3
"""Independent re-derivation of the Step-0 headlines and six placebos that must fail.

Deliberately imports NOTHING from eval.py, common/ or sections/: every raw file is parsed here with its own code
(label normalisation, landing counts, softmax masses, Hill numbers, kappa, geometry, persistence). Deterministic values
must match the reported ones to 1e-9 (1e-6 where float32 linear algebra is involved); stochastic values must agree
within 3 Monte Carlo standard errors. Output: audit/rederive_report.json.
"""

from __future__ import annotations

import json
import math
import os
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

WS = Path(__file__).resolve().parent.parent
RUNS = Path(os.environ.get("AII_RUNS_ROOT", str(WS.parents[4])))
I1 = "run_4VFKidE1bxPG/3_invention_loop/iter_1/gen_art"
I2 = "run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art"
IDS = {"exp1": ("art__skdlFp_o3e9", f"{I1}/gen_art_experiment_1"), "exp2": ("art_D6Z0Snf09sFL", f"{I1}/gen_art_experiment_2"),
       "exp4": ("art_U5UKkFrOgSsE", f"{I1}/gen_art_experiment_4"), "exp5": ("art_HF8nK8B_Lqyy", f"{I1}/gen_art_experiment_5"),
       "exp6": ("art_UoCVh2Qe5RZ0", f"{I1}/gen_art_experiment_6"), "exp7": ("art_6zBfl3kDjeiP", f"{I2}/gen_art_experiment_7"),
       "exp8": ("art_8_ULPE8jJQc_", f"{I2}/gen_art_experiment_8"), "exp9": ("art_IVZc3TWCeE9f", f"{I2}/gen_art_experiment_9"),
       "exp10": ("art_-QPYRaFERCBX", f"{I2}/gen_art_experiment_10"), "exp11": ("art_0ndRfWKBWclR", f"{I2}/gen_art_experiment_11"),
       "exp12": ("art_3iv5G76C3yoX", f"{I2}/gen_art_experiment_12")}


def _where(aid: str, run_rel: str) -> Path:
    # same order as the main code, written separately: $AII_DEPS_ROOT/<id>, ../<id>, run-volume layout
    if os.environ.get("AII_DEPS_ROOT"):
        return Path(os.environ["AII_DEPS_ROOT"]) / aid
    return WS.parent / aid if (WS.parent / aid).is_dir() else RUNS / run_rel


E = {k: _where(aid, rr) for k, (aid, rr) in IDS.items()}
RES = WS / "results"
MODAL = {"t1": "bfs", "t2": "dijkstra"}
K6 = {"t1": ["bfs", "dfs", "bibfs", "iddfs", "astar_gbfs", "dijkstra"], "t2": ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"]}
CHECKS: list[dict] = []
PLACEBOS: list[dict] = []


def jl(p: Path) -> list[dict]:
    out = []
    for line in Path(p).read_text().splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def jr(p: Path):
    return json.loads(Path(p).read_text())


def check(name: str, mine, reported, tol: float = 1e-9, kind: str = "deterministic", se: float | None = None) -> None:
    if isinstance(mine, (int, float)) and isinstance(reported, (int, float)):
        d = abs(float(mine) - float(reported))
        lim = 3 * se if (kind == "stochastic" and se is not None) else tol
        ok = d <= lim
    else:
        ok = mine == reported
        d = None
    CHECKS.append({"name": name, "rederived": mine, "reported": reported, "abs_diff": d, "kind": kind,
                   "tolerance": (3 * se if se is not None else tol) if isinstance(mine, (int, float)) else "exact", "pass": bool(ok)})


def lab(task: str, raw, exp: str = "") -> str:
    s = str(raw).strip().lower() if raw is not None else "none"
    if s in ("none", "no_code", "unparseable", "invalid", ""):
        return "unparseable"
    if s.startswith("other") or s == "unknown":
        return "other"
    t1 = {"bfs": "bfs", "dfs": "dfs", "bibfs": "bibfs", "bidir_bfs": "bibfs", "bidirectional_bfs": "bibfs", "iddfs": "iddfs",
          "astar": "astar_gbfs", "gbfs": "astar_gbfs", "astar_gbfs": "astar_gbfs", "astar_greedy": "astar_gbfs",
          "dijkstra": "dijkstra", "dijkstra_unit": "dijkstra", "unit_dijkstra": "dijkstra"}
    t2 = {"dijkstra": "dijkstra", "bf_spfa": "bf_spfa", "bellman_ford_spfa": "bf_spfa", "bellman_ford": "bf_spfa",
          "spfa": "bf_spfa", "bidijkstra": "bidijkstra", "bidir_dijkstra": "bidijkstra",
          "bidirectional_dijkstra": "bidijkstra", "floyd": "floyd", "floyd_warshall": "floyd", "dial": "dial"}
    m = t1 if task == "t1" else t2
    return m.get(s, "other")


def passed(v) -> bool:
    return str(v) in ("True", "true", "1")


def hill(c) -> float:
    c = np.array([x for x in c if x > 0], float)
    if c.sum() == 0:
        return math.nan
    p = c / c.sum()
    return float(math.exp(-(p * np.log(p)).sum()))


def softmax(L):
    L = np.asarray(L, float)
    e = np.exp(L - L.max())
    return e / e.sum()


# ---------------------------------------------------------------------------------------------- A. landings
def qwen_event_rows() -> dict[str, list[tuple[str, str, bool]]]:
    ev = defaultdict(list)
    for r in jl(E["exp1"] / "data/samples.jsonl"):
        c = r["condition"]
        if c.startswith("ban:") and "+" not in c:
            ev[f"exp1|{r['task']}|{c}"].append((r["task"], lab(r["task"], r["label"]), passed(r["passed"]), c.split(":")[1]))
    for r in jl(E["exp8"] / "data/samples.jsonl"):
        if r["condition"] == "a":
            ev[f"exp8|{r['task']}|arm_a"].append((r["task"], lab(r["task"], r["label"]), passed(r["passed"]), MODAL[r["task"]]))
    for r in jl(E["exp9"] / "data/samples.jsonl"):
        if r["condition"].startswith("single:"):
            ev[f"exp9|{r['task']}|{r['condition']}"].append((r["task"], lab(r["task"], r["label"]), passed(r["passed"]), r["condition"].split(":")[1]))
    for r in jl(E["exp12"] / "results/samples.jsonl"):
        if r["condition"] == "ban" and r.get("arm") == "C1_fresh_pool":
            ev[f"exp12|{r['task']}|fresh_pool"].append((r["task"], lab(r["task"], r["label"]), passed(r["passed"]), MODAL[r["task"]]))
    return ev


def landing(rs) -> tuple[str | None, Counter, int]:
    t, X = rs[0][0], rs[0][3]
    surv = [j for j in K6[t] if j != X]
    nb = Counter(l for _, l, _, _ in rs if l not in ("unparseable", X))
    if not nb:
        return None, nb, 0
    return max(surv, key=lambda j: (nb.get(j, 0), -surv.index(j))), nb, sum(nb.values())


def main() -> None:
    rep_c1 = jr(RES / "c1_diagnostics.json")
    ev = qwen_event_rows()
    pooled = {}
    for t, j, keys in (("t1", "dfs", ("exp8|t1|arm_a", "exp9|t1|single:bfs", "exp12|t1|fresh_pool")),
                       ("t2", "bf_spfa", ("exp8|t2|arm_a", "exp9|t2|single:dijkstra", "exp12|t2|fresh_pool"))):
        k = n = 0
        for key in keys:
            _, nb, nn = landing(ev[key])
            k += nb.get(j, 0)
            n += nn
        pooled[t] = f"{k}/{n}"
    rp = rep_c1["event_table"]["reproduction"]["pooled_landing_counts"]
    check("A1 iter-2 pooled T1 DFS (attempted non-banned)", pooled["t1"],
          rp["t1|dfs|iter2_modal_draws(exp8a+exp9single+exp12pool)"]["attempted_nonbanned"])
    check("A2 iter-2 pooled T2 BF/SPFA (attempted non-banned)", pooled["t2"],
          rp["t2|bf_spfa|iter2_modal_draws(exp8a+exp9single+exp12pool)"]["attempted_nonbanned"])
    tab = {r["event"]: r for r in rep_c1["event_table"]["table"]}
    for key in ("exp1|t1|ban:bfs", "exp1|t2|ban:dijkstra", "exp9|t1|single:bfs", "exp12|t2|fresh_pool"):
        m, nb, nn = landing(ev[key])
        check(f"A3 modal landing {key}", f"{m}:{nb.get(m, 0)}/{nn}",
              f"{tab[key]['modal_landing']}:{tab[key]['nonbanned_counts'].get(tab[key]['modal_landing'], 0)}/{tab[key]['n_nonbanned']}")
    # ------------------------------------------------------------------------------------------ B. argmax hits
    c1 = jr(E["exp7"] / "results/c1.json")
    cells = defaultdict(dict)
    for r in jl(E["exp7"] / "results/frlp_cells.jsonl"):
        if r["variant"] == "primary" and r["half"] == "all":
            cells[(r["task"], r["condition"])][r["algorithm"]] = (r["L"], r["ess"])
    hits = {"Gbar": 0, "s": 0, "mass": 0}
    n_ev = 0
    land_list, mass_list = [], []
    for key, rs in sorted(ev.items()):
        t, X = rs[0][0], rs[0][3]
        m, _, _ = landing(rs)
        row = c1["primary_neutral"]["tasks"][t]["rows"].get(X)
        if row is None or m is None:
            continue
        n_ev += 1
        hits["Gbar"] += max(row["Gbar"], key=row["Gbar"].get) == m
        hits["s"] += max(row["s"], key=row["s"].get) == m
        S = [j for j in K6[t] if j != X]
        ps = []
        for w in ("W1", "W2", "W3", "W4", "W5"):
            c = cells.get((t, f"ban|{X}|{w}"), {})
            if all(j in c for j in S):
                ps.append(softmax([c[j][0] for j in S]))
        pm = np.mean(ps, 0)
        mass_list.append(dict(zip(S, pm)))
        land_list.append(m)
        hits["mass"] += S[int(np.argmax(pm))] == m
    met = rep_c1["event_table"]["metrics"]
    check("B1 Qwen events with a C1 row", n_ev, met["Qwen|Gbar_neutral|all_events"]["n"])
    check("B2 hits argmax full gain", hits["Gbar"], met["Qwen|Gbar_neutral|all_events"]["hits"])
    check("B3 hits argmax residual", hits["s"], met["Qwen|s_neutral|all_events"]["hits"])
    check("B4 hits argmax implied mass (from frlp_cells.jsonl)", hits["mass"], met["Qwen|mass|all_events"]["hits"])
    # placebo 1: landings shuffled across events
    rng = np.random.default_rng(7)
    sh = []
    for _ in range(2000):
        perm = rng.permutation(len(land_list))
        sh.append(np.mean([max(mass_list[i], key=mass_list[i].get) == land_list[perm[i]]
                           if land_list[perm[i]] in mass_list[i] else False for i in range(len(land_list))]))
    obs = hits["mass"] / n_ev
    PLACEBOS.append({"name": "P1 landings shuffled across events (implied-mass argmax)", "observed_hit_rate": obs,
                     "shuffled_mean_hit_rate": float(np.mean(sh)), "shuffled_q95": float(np.quantile(sh, 0.95)),
                     "fails_as_required": bool(np.mean(sh) < obs - 0.2)})
    # placebo 2: survivor names shuffled within an event
    sh2 = []
    for _ in range(2000):
        hh = 0
        for mm, ll in zip(mass_list, land_list):
            names = list(mm.keys())
            vals = list(mm.values())
            rng.shuffle(names)
            hh += names[int(np.argmax(vals))] == ll
        sh2.append(hh / len(land_list))
    PLACEBOS.append({"name": "P2 survivor names shuffled within an event", "observed_hit_rate": obs,
                     "shuffled_mean_hit_rate": float(np.mean(sh2)), "fails_as_required": bool(np.mean(sh2) < obs - 0.2)})
    # ------------------------------------------------------------------------------------------ C. mass restriction
    kept_rows = 0
    for t in ("t1", "t2"):
        for X in K6[t]:
            S = [j for j in K6[t] if j != X]
            pb, pr, eb, er = [], [], [], []
            for w in ("W1", "W2", "W3", "W4", "W5"):
                cb, ca, cbb = cells.get((t, f"ban|{X}|{w}"), {}), cells.get((t, f"neutral|{X}|{w}|A"), {}), cells.get((t, f"neutral|{X}|{w}|B"), {})
                if not all(j in cb and j in ca and j in cbb for j in S):
                    continue
                pb.append(softmax([cb[j][0] for j in S]))
                pr.append(0.5 * (softmax([ca[j][0] for j in S]) + softmax([cbb[j][0] for j in S])))
                eb.append([cb[j][1] for j in S])
                er.append([min(ca[j][1], cbb[j][1]) for j in S])
            if not pb:
                continue
            p1, p2 = np.mean(pb, 0), np.mean(pr, 0)
            e1, e2 = np.median(eb, 0), np.median(er, 0)
            keep = ((p1 >= 0.01) | (p2 >= 0.01)) & (e1 >= 5) & (e2 >= 5)
            kept_rows += int(keep.sum() >= 3)
    check("C1 rows surviving the 1%-mass and ESS>=5 restriction", kept_rows, rep_c1["mass_c1"]["n_rows_kept"])
    # ------------------------------------------------------------------------------------------ D. variance ratio
    for r in rep_c1["variance_ratio_two_stage"]["rows"][:4]:
        tn = c1["primary_neutral"]["tasks"][r["task"]]["rows"][r["B"]]["tot_noise"]
        check(f"D1 tot_noise {r['task']}|{r['B']} vs exp7 c1.json", r["tot_noise_method_py"], tn, tol=1e-9)
        check(f"D2 ratio {r['task']}|{r['B']}", r["trace_boot_var"] / tn, r["ratio"], tol=1e-9)
    rr = [r["trace_boot_var"] / c1["primary_neutral"]["tasks"][r["task"]]["rows"][r["B"]]["tot_noise"]
          for r in rep_c1["variance_ratio_two_stage"]["rows"]]
    check("D3 median bootstrap/replicate ratio", float(np.median(rr)), rep_c1["variance_ratio_two_stage"]["row_ratio_median"])
    # ------------------------------------------------------------------------------------------ E. AIM null
    check("E1 observed Qwen AIM (mention reference)", c1["reference_mention"]["aim_prime_veto"]["aim"],
          rep_c1["aim"]["observed"]["qwen_mention_ref"])
    rng = np.random.default_rng(12345)
    n_sim = 4000
    vals, vals_ind = [], []
    uh = []
    for t in ("t1", "t2"):
        for B, row in c1["reference_mention"]["tasks"][t]["rows"].items():
            fl = np.array(list(row["fitted_ladder"].values()))
            uh.append(fl / row["a"])
    def rank_rows(M):
        return np.argsort(np.argsort(M, axis=1), axis=1).astype(float)
    def sp(A, B):
        ra, rb = rank_rows(A), rank_rows(B)
        ra -= ra.mean(1, keepdims=True); rb -= rb.mean(1, keepdims=True)
        return (ra * rb).sum(1) / np.sqrt((ra * ra).sum(1) * (rb * rb).sum(1))
    tot = np.zeros(n_sim); tot_ind = np.zeros(n_sim)
    for u in uh:
        n = len(u)
        b1, b2, men, n1, n2, menB = (rng.normal(size=(n_sim, n)) for _ in range(6))
        def res(g):
            g = g - g.mean(1, keepdims=True)
            return g - (g @ u)[:, None] * u[None, :]
        tot += 0.5 * (sp(res(b1 - men), men - n2) + sp(res(b2 - men), men - n1))
        tot_ind += 0.5 * (sp(res(b1 - men), menB - n2) + sp(res(b2 - men), menB - n1))
    tot /= len(uh); tot_ind /= len(uh)
    rep_null = rep_c1["aim"]["null"]["qwen_shared_cell_equal_var"]
    check("E2 AIM null mean (shared mention cell, equal variances)", float(tot.mean()), rep_null["mean"],
          kind="stochastic", se=float(math.sqrt(tot.var() / n_sim + rep_null["sd"] ** 2 / rep_null["n_sim"])))
    PLACEBOS.append({"name": "P3 AIM null with independent mention copies", "null_mean": float(tot_ind.mean()),
                     "shared_null_mean": float(tot.mean()), "fails_as_required": bool(abs(tot_ind.mean()) < 0.05)})
    # ------------------------------------------------------------------------------------------ F. M arithmetic
    import csv
    mine = {}
    with (WS / "tables" / "m_arithmetic_cells.csv").open() as fh:
        for r in csv.DictReader(fh):
            if r["model"] == "Qwen/Qwen3-8B":
                mine[(r["task"], r["condition"], r["j"])] = float(r["M5_plugin_lower_bound"])
    diffs, m5 = [], []
    for (t, cond), d in cells.items():
        if not cond.split("|")[0] in ("ban", "neutral", "mention"):
            continue
        for j, (L, ess) in d.items():
            key = (t, cond, j)
            if key in mine and ess and ess > 0:
                # exp7 cells store ESS on the all-programs half; M = 20 programs per algorithm (11 for bidijkstra)
                pass
    # cell-by-cell: M5 = 5 * M / ESS with M taken from frlp_cells n_programs
    nprog = {}
    for r in jl(E["exp7"] / "results/frlp_cells.jsonl"):
        if r["variant"] == "primary" and r["half"] == "all":
            nprog[(r["task"], r["condition"], r["algorithm"])] = (r["n_programs"], r["ess"])
    for key, v in mine.items():
        if key in nprog and nprog[key][1]:
            m5v = 5 * nprog[key][0] / nprog[key][1]
            diffs.append(abs(m5v - v) / max(1.0, abs(v)))
            m5.append(m5v)
    check("F1 M5 plug-in, cell-by-cell max relative difference vs frlp_cells.jsonl ESS", float(max(diffs)) if diffs else math.nan,
          0.0, tol=1e-6)
    check("F2 number of cells compared", len(diffs) > 300, True)
    # ------------------------------------------------------------------------------------------ G. manifold
    man = jr(RES / "manifold.json")
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import connected_components, shortest_path
    from scipy.spatial.distance import cdist
    algs = ["bfs", "dfs", "bibfs", "iddfs", "astar", "gbfs", "idastar"]
    Xs, metas = [], []
    for p in sorted((E["exp9"] / "states/t1/base").glob("part_*.npz")):
        z = np.load(p, allow_pickle=False)
        Xs.append(z["X"][:, 4, 1, :].astype(np.float32))       # layer 24 (index 4 of 20..28), position g16 (index 1)
        metas += json.loads(str(z["meta"]))
    Xa = np.concatenate(Xs)
    keep = [i for i, m in enumerate(metas) if m.get("kind") == "forced" and m.get("algorithm") in algs]
    Y = Xa[keep]
    labs = np.array([metas[i]["algorithm"] for i in keep])
    mu = Y.mean(0, keepdims=True)
    _, _, Vt = np.linalg.svd(Y - mu, full_matrices=False)
    Z = (Y - mu) @ Vt[:50].T
    D0 = cdist(Z, Z)
    k = 10
    idx = np.argsort(D0, 1)[:, 1:k + 1]
    W = np.zeros_like(D0)
    rows_ = np.repeat(np.arange(len(Z)), k)
    W[rows_, idx.ravel()] = D0[rows_, idx.ravel()]
    W = np.maximum(W, W.T)
    nc, cl = connected_components(csr_matrix(W > 0), directed=False)
    while nc > 1:
        best = None
        for c in range(1, nc):
            a, b = np.where(cl == 0)[0], np.where(cl == c)[0]
            sub = D0[np.ix_(a, b)]
            i, j = np.unravel_index(np.argmin(sub), sub.shape)
            if best is None or sub[i, j] < best[0]:
                best = (sub[i, j], a[i], b[j])
        W[best[1], best[2]] = W[best[2], best[1]] = best[0]
        nc, cl = connected_components(csr_matrix(W > 0), directed=False)
    G = shortest_path(csr_matrix(W), method="D", directed=False)

    def cmat(lb):
        Kk = len(algs)
        M = np.zeros((Kk, Kk))
        for i, a in enumerate(algs):
            for j, b in enumerate(algs):
                ia, ib = np.where(lb == a)[0], np.where(lb == b)[0]
                sub = G[np.ix_(ia, ib)]
                M[i, j] = np.median(sub[~np.eye(len(ia), dtype=bool)]) if i == j else np.median(sub)
        return M / np.median(M[~np.eye(Kk, dtype=bool)])

    Dm = cmat(labs)
    ib, jb = algs.index("bfs"), algs.index("bibfs")
    sep = Dm[ib, jb] / (0.5 * (Dm[ib, ib] + Dm[jb, jb]))
    rep_sep = next(r["bfs_bibfs"]["separability"] for r in man["tasks"]["t1"]["grid"] if r["layer"] == 24 and r["position"] == "g16" and r["k"] == 10)
    check("G1 BFS-BiBFS separability at (24, g16, k10)", float(sep), rep_sep, tol=1e-6)
    nn_bfs = algs[int(np.argsort(np.where(np.arange(len(algs)) == ib, np.inf, Dm[ib]))[0])]
    check("G2 nearest neighbour of BFS at g16", nn_bfs, man["tasks"]["t1"]["nulls_layer24_k10"]["g16"]["nearest"]["bfs"])
    # placebo 4a: global label permutation destroys the BFS-BiBFS identity
    rng = np.random.default_rng(99)
    same = 0
    for _ in range(300):
        lp = rng.permutation(labs)
        Dp = cmat(lp)
        same += algs[int(np.argsort(np.where(np.arange(len(algs)) == ib, np.inf, Dp[ib]))[0])] == "bibfs"
    PLACEBOS.append({"name": "P4a global label permutation (BFS-BiBFS nearest-neighbour identity)",
                     "fraction_of_permutations_with_bibfs_nearest": same / 300, "chance": 1 / 6,
                     "fails_as_required": bool(same / 300 < 0.5)})
    from ripser import ripser
    mu20 = Y.mean(0, keepdims=True)
    _, _, Vt20 = np.linalg.svd(Y - mu20, full_matrices=False)
    P = (Y - mu20) @ Vt20[:20].T
    dg = ripser(P, maxdim=1)["dgms"][1]
    life = float(np.max(dg[:, 1] - dg[:, 0])) if len(dg) else 0.0
    rep_life = man["tasks"]["t1"]["persistence"]["L24|g16"]["max_lifetime"]
    check("G3 per-sample max H1 lifetime at L24 g16 (all forced points, 20 PCs)", life, rep_life, tol=1e-3)
    rng = np.random.default_rng(5)
    cov = np.cov(P.T)
    null = []
    for _ in range(60):
        Q = rng.multivariate_normal(np.zeros(P.shape[1]), cov, size=len(P))
        d2 = ripser(Q, maxdim=1)["dgms"][1]
        null.append(float(np.max(d2[:, 1] - d2[:, 0])) if len(d2) else 0.0)
    pval = (np.sum(np.array(null) >= life) + 1) / (len(null) + 1)
    check("G4 H1 Gaussian-null p-value (>= 0.5 in both)", bool(pval >= 0.5), bool(man["tasks"]["t1"]["persistence"]["L24|g16"]["p"] >= 0.5))
    pw0 = man["tasks"]["t1"]["persistence"]["L24|g16"]["power"]["radius0_placebo_rate"]
    PLACEBOS.append({"name": "P4b radius-0 planted loop (power must equal alpha)", "rate": pw0, "alpha": 0.05,
                     "fails_as_required": bool(pw0 < 0.15)})
    # ------------------------------------------------------------------------------------------ H. novelty
    nov = jr(RES / "novelty_audit.json")
    files = [("exp1", "data/samples.jsonl"), ("exp2", "data/samples_phaseA.jsonl"), ("exp2", "data/samples_phaseC.jsonl"),
             ("exp2", "data/samples_phaseD.jsonl"), ("exp4", "data/samples.jsonl"), ("exp5", "runs/samples.jsonl"),
             ("exp6", "results/samples.jsonl"), ("exp8", "inputs/iter1/exp3/generations/pools.jsonl"),
             ("exp8", "data/samples.jsonl"), ("exp9", "data/samples.jsonl"), ("exp10", "data/labelled.jsonl"),
             ("exp11", "data/samples_pilot.jsonl"), ("exp11", "data/samples_llama_pilot.jsonl"),
             ("exp11", "data/samples_forced.jsonl"), ("exp12", "results/samples.jsonl")] + \
            [("exp12", f"results/labelled_{k}.jsonl") for k in ("c1", "c2", "c3", "c4", "crn", "det", "rep10")]
    import hashlib
    keys = set()
    for e, rel in files:
        for r in jl(E[e] / rel):
            code = r.get("code") if isinstance(r.get("code"), str) else None
            if not code or not code.strip() or not passed(r.get("passed")):
                continue
            t = str(r.get("task"))
            t = t.lower() if t.upper() in ("T1", "T2") else t
            raw = str(r.get("label")).lower()
            is_other = raw.startswith("other") or raw in ("unknown",) or (raw == "none" and code.strip())
            if t == "t1" and raw in ("jps", "biastar"):
                is_other = True
            if e == "exp9" and t == "t1" and raw in ("dijkstra_unit", "unit_dijkstra"):
                is_other = True
            if is_other:
                norm = "\n".join(l.rstrip() for l in code.strip().splitlines())
                keys.add(f"{t}|{hashlib.sha256(norm.encode()).hexdigest()}")
    check("H1 unique correct out-of-catalogue programs (Set A)", len(keys), nov["novelty_answer"]["correct_other_unique"])
    cache = defaultdict(dict)
    for r in jl(WS / "audit/judge_cache.jsonl"):
        if r.get("parsed") and r["item_id"] != "SMOKE":
            cache[r["item_id"]][r["judge"]] = r["parsed"].get("class")
    sel = {r["item_id"]: r for r in jl(WS / "audit/selection.jsonl")}
    finals = {}
    for iid, d in cache.items():
        a, b, c = d.get("A"), d.get("B"), d.get("C")
        finals[iid] = a if (a and a == b) else (c if c else (a or b))
    nA = sum(1 for iid, s in sel.items() if s.get("set") == "A" and finals.get(iid) == "NOVEL_ALGORITHM")
    check("H2 Set A programs judged NOVEL (final class)", nA, nov["novelty_answer"]["confirmed_novel_correct"])
    pairs = [(d["A"], d["B"]) for iid, d in cache.items() if "A" in d and "B" in d and sel.get(iid, {}).get("set") in ("A", "B", "B_TOP")]
    cats = sorted({x for p in pairs for x in p})
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[c] * cb[c] for c in cats) / n / n
    check("H3 Cohen's kappa judge A vs judge B", (po - pe) / (1 - pe), nov["kappa_A_B"], tol=1e-9)
    s9 = [r for r in jl(E["exp9"] / "data/samples.jsonl") if r["condition"] == "multi:TOP"]
    banned = {"bfs", "dfs", "gbfs", "iddfs"}
    nb = sum(1 for r in s9 if str(r["label"]) not in banned)
    top = next(a for a in nov["multiban_avoidance"] if a["condition"] == "multi:TOP")
    check("H4 TOP raw avoidance", nb / len(s9), top["avoidance_raw"], tol=1e-9)
    check("H5 TOP corrected avoidance (no 'other' judged a banned mechanism)", nb / len(s9) - top["n_reassigned_to_banned"] / len(s9),
          top["avoidance_corrected"], tol=1e-9)
    ctrl = nov["controls"]["pos_rows"]
    wrong = [r["expected"] for r in ctrl]
    wrong = wrong[1:] + wrong[:1]
    hits_wrong = sum(1 for r, w in zip(ctrl, wrong) if r["final_class"] == "LABELLER_MISS" and r["matched"] == w)
    PLACEBOS.append({"name": "P6 judge positive controls scored against wrong catalogue names", "hits_true_names": nov["controls"]["pos_hits"],
                     "hits_wrong_names": hits_wrong, "fails_as_required": bool(hits_wrong <= 2)})
    # ------------------------------------------------------------------------------------------ I. Llama
    lla = jr(RES / "llama_correct_only.json")
    evj = jr(E["exp10"] / "results/events.json")
    labl = jl(E["exp10"] / "data/labelled.jsonl")
    by = defaultdict(list)
    for r in labl:
        by[(r["task"], r["condition"])].append(r)
    rep_ev = {(e["task"], e["event"]): e for e in lla["events"]}
    for t in ("t1", "t2"):
        for e in evj[t]:
            rs = [r for c in e["conds"] for r in by[(t, c)]]
            cc = Counter()
            for r in rs:
                L = str(r.get("label"))
                if L in ("None", "no_code") or not (r.get("code") or "").strip() or not passed(r.get("passed")) or L in e["banned"]:
                    continue
                cc[L] += 1
            h = hill(list(cc.values())) if cc else math.nan
            hr = rep_ev[(t, e["name"])]["hill_cc"]
            if not (isinstance(hr, float) or isinstance(hr, int)) or hr is None:
                check(f"I1 Llama Hill_cc {t} {e['name']}", "nan" if math.isnan(h) else h, "nan")
            else:
                check(f"I1 Llama Hill_cc {t} {e['name']}", h, hr, tol=1e-9)
    lp = jl(E["exp11"] / "data/samples_llama_pilot.jsonl")
    repb = {b["task"]: b for b in lla["bench"]}
    for task in sorted({r["task"] for r in lp}):
        cc = Counter(str(r["label"]) for r in lp if r["task"] == task and passed(r["passed"]) and (r.get("code") or "").strip()
                     and str(r["label"]) not in ("None", "no_code", "invalid", "unparseable"))
        check(f"I2 Llama bench Hill_cc {task}", hill(list(cc.values())), repb[task]["llama"]["hill_cc"], tol=1e-9)
    # ------------------------------------------------------------------------------------------ J. knob table
    knob = jr(RES / "knob_table.json")
    rng = np.random.default_rng(2026)
    for r in knob["ranking"][:5]:
        c = np.array(sorted(r["cc_counts"].values(), reverse=True), dtype=np.int64)
        Msub = rng.multivariate_hypergeometric(c, 25, size=1000).astype(float)
        p = Msub / 25
        hv = np.exp(-(np.where(Msub > 0, p * np.log(np.where(Msub > 0, p, 1)), 0)).sum(1))
        se = float(hv.std() / math.sqrt(1000)) * math.sqrt(2)
        check(f"J1 rarefied Hill-1 (depth 25) {r['exp']} {r['task']} {r['condition']} {r['arm']}", float(hv.mean()), r["hill_rar25"],
              kind="stochastic", se=se)
    # pass points of the top-5 rows: deterministic from the same rows
    for r in knob["ranking"][:5]:
        check(f"J2 pass points {r['exp']} {r['task']} {r['condition']} {r['arm']}",
              round(100 * (r["ref_pass_rate"] - r["pass_rate"]), 9), round(r["pass_points"], 9), tol=1e-6)
    # placebo 5: classes shuffled -> ranking changes
    prim = knob["primary"]
    real_top = [(r["exp"], r["task"], r["condition"], r["arm"], r["decoding"]) for r in knob["ranking"][:5]]
    changed = 0
    for s in range(200):
        rr = random.Random(s)
        cl = [r["class"] for r in prim]
        rr.shuffle(cl)
        cand = [(r["hill_rar25"], (r["exp"], r["task"], r["condition"], r["arm"], r["decoding"])) for r, c in zip(prim, cl)
                if c == "KNOB" and r["rankable_n"] and r["pass_points"] is not None and r["pass_points"] < 20
                and r["hill_rar25"] is not None and not (isinstance(r["hill_rar25"], float) and math.isnan(r["hill_rar25"]))]
        cand.sort(key=lambda x: -x[0])
        changed += [x[1] for x in cand[:5]] != real_top
    PLACEBOS.append({"name": "P5 knob classes shuffled across rows", "fraction_of_shuffles_with_a_different_top5": changed / 200,
                     "fails_as_required": bool(changed / 200 > 0.9)})
    # ------------------------------------------------------------------------------------------ K/L. positioning, corrections
    pos = jr(RES / "positioning.json")
    import re as _re
    nv = 0
    for r in pos["rows"]:
        txt = (WS / r["evidence_file"]).read_text(errors="ignore")
        q = r["neighbour_finding_quote"]
        norm = lambda s: _re.sub(r"\s+", " ", s.replace("**", "").replace("\\", "")).strip().lower()
        nv += bool(q) and norm(q) in norm(txt)
    check("K1 positioning quotes found verbatim in the saved pages", nv, pos["n_verified"])
    cor = jr(WS / "corrections.json")
    check("L1 corrections items with sourced numbers", sum(1 for c in cor["items"] if c["numbers"]), 12)
    out = {"n_checks": len(CHECKS), "n_passed": sum(c["pass"] for c in CHECKS), "checks": CHECKS,
           "placebos": PLACEBOS, "n_placebos": len(PLACEBOS), "n_placebos_ok": sum(p["fails_as_required"] for p in PLACEBOS),
           "note": "independent parser; no imports from eval.py, common/ or sections/"}
    (WS / "audit" / "rederive_report.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"checks {out['n_passed']}/{out['n_checks']} passed; placebos {out['n_placebos_ok']}/{out['n_placebos']} failed as required")
    for c in CHECKS:
        if not c["pass"]:
            print("FAILED:", c["name"], c["rederived"], c["reported"])
    for p in PLACEBOS:
        print("PLACEBO", p["name"], "OK" if p["fails_as_required"] else "DID NOT FAIL", {k: v for k, v in p.items() if k not in ("name",)})


if __name__ == "__main__":
    main()
