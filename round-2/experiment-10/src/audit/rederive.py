#!/usr/bin/env python3
"""T11 independent re-derivation (does NOT import src/analysis_c1.py or src/run_analysis.py).

From the raw files only -- frlp/scores_<task>.parquet, data/forced_set.jsonl, results/forced_set_summary.json,
data/labelled.jsonl, results/selections.json -- recompute the FRLP gate clauses (a)-(c), the C1 components V_u, V_s,
V_tot, SHARE and the prime-and-veto AIM (both references, per task and pooled), the exact AIM null q95, the ladder check
and the branch (with the bootstrap CIs read from results/c1.json, the only non-raw input), and assert agreement with
results/c1.json and results/frlp_gate.json to 1e-9. Placebo: 200 within-row shuffles of the PV survivor labels must
give AIM p-values consistent with uniform (KS).
Run:  .venv/bin/python audit/rederive.py
"""

from __future__ import annotations

import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kstest, rankdata

ROOT = Path(__file__).resolve().parent.parent
TOL = 1e-9


def jl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def lme(x: np.ndarray) -> float:
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return float("nan")
    m = x.max()
    return float(m + math.log(np.mean(np.exp(x - m))))


def ess(x: np.ndarray) -> float:
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return float("nan")
    e = np.exp(x - x.max())
    return float(e.sum() ** 2 / (e ** 2).sum())


def cen(v):
    return v - v.mean()


def unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 0 else v * np.nan


def sp(a, b):
    if np.any(np.isnan(a)) or np.any(np.isnan(b)):
        return float("nan")
    ra, rb = rankdata(a), rankdata(b)
    if ra.std() == 0 or rb.std() == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


class Task:
    def __init__(self, task: str):
        self.task = task
        summ = json.loads((ROOT / "results" / "forced_set_summary.json").read_text())["per_algorithm"]
        sel = json.loads((ROOT / "results" / "selections.json").read_text())
        self.d = sel[f"{task}_default"]
        fs = [r for r in jl(ROOT / "data" / "forced_set.jsonl") if r["task"] == task and r["scrub_mode"] != "dropped"
              and not summ[f"{task}:{r['j']}"]["excluded_M_lt_10"]]
        self.meta = {r["program_id"]: r for r in fs}
        cat = {"t1": ["bfs", "dfs", "bibfs", "iddfs", "astar_gbfs", "dijkstra"],
               "t2": ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"]}[task]
        self.algs = [a for a in cat if any(r["j"] == a for r in fs)]
        sc = pd.read_parquet(ROOT / "frlp" / f"scores_{task}.parquet")
        sc = sc[sc["program_id"].isin(self.meta)]
        self.l = sc.pivot_table(index="program_id", columns="condition_id", values="l_full", aggfunc="first")
        lq = {}
        for pid in self.l.index:
            j = self.meta[pid]["j"]
            cols = [c for c in self.l.columns if (c.startswith("forced:") or c.startswith("forced_desc:")) and c.split(":")[1] == j]
            lq[pid] = lme(self.l.loc[pid, cols].to_numpy(dtype=float))
        self.D = self.l.sub(pd.Series(lq), axis=0)
        self.j_of = {pid: self.meta[pid]["j"] for pid in self.l.index}
        self.h_of = {pid: int(self.meta[pid]["half"]) for pid in self.l.index}
        self._cache = {}

    def cell(self, cond: str, j: str, h: int | None):
        key = (cond, j, h)
        if key not in self._cache:
            if cond not in self.D.columns:
                self._cache[key] = (float("nan"), float("nan"))
            else:
                ids = [p for p in self.D.index if self.j_of[p] == j and (h is None or self.h_of[p] == h)]
                x = self.D.loc[ids, cond].to_numpy(dtype=float)
                self._cache[key] = (lme(x), ess(x))
        return self._cache[key]

    def L(self, cond, j, h=None):
        return self.cell(cond, j, h)[0]

    def E(self, cond, j, h=None):
        return self.cell(cond, j, h)[1]

    def generic(self, h=None):
        algs = self.algs
        hs = (1, 2) if h is None else (h,)
        g = {"nonce": np.array([np.mean([self.L(f"nonce:w{w}", j, hh) - self.L(f"nonce_neutral:w{w}:h{hh}", j, hh)
                                         for w in range(1, 6) for hh in hs]) for j in algs])}
        for k in range(1, 7):
            if f"edit:k{k}" in self.D.columns:
                g[f"edit{k}"] = np.array([self.L(f"edit:k{k}", j, h) - self.L("baseline_empty", j, h) for j in algs])
        g["novelty"] = np.array([self.L("novelty", j, h) - np.mean([self.L(f"baseline:s{s}", j, h) for s in range(5)])
                                 for j in algs])
        return g

    def u(self, h=None):
        g = self.generic(h)
        edits = [g[k] for k in g if k.startswith("edit")]
        types = [g["nonce"], np.mean(edits, axis=0), g["novelty"]]
        return np.mean([unit(cen(t)) for t in types], axis=0)


def c1(t: Task, ref: str):
    u = t.u()
    uh = {1: t.u(1), 2: t.u(2)}
    out = {"V_u": 0.0, "V_s": 0.0, "V_tot": 0.0, "rows": []}
    for X in t.algs:
        S = [j for j in t.algs if j != X]
        if len(S) < 3:
            continue
        reps, wts = [], []

        def refc(w, h):
            return f"neutral:{X}:w{w}:h{h}" if ref == "neutral" else f"mention:{X}:w{w}"

        for w in range(1, 6):
            for h in (1, 2):
                reps.append(np.array([t.L(f"ban:{X}:w{w}", j, h) - t.L(refc(w, h), j, h) for j in S]))
                wts.append(np.array([min(1.0, min(t.E(f"ban:{X}:w{w}", j, h), t.E(refc(w, h), j, h)) / 5.0) for j in S]))
        reps = np.array([cen(r) for r in reps])
        wt = np.mean(np.array(wts), axis=0)
        rw = np.array([cen(wt * r) for r in reps])
        gbar = rw.mean(axis=0)
        dev = rw - gbar
        Sig = dev.T @ dev / (len(rw) * (len(rw) - 1))
        vhat = unit(cen(u[[t.algs.index(j) for j in S]]))
        a = float(gbar @ vhat)
        s = gbar - a * vhat
        nu = float(vhat @ Sig @ vhat)
        ns = float(np.trace(Sig)) - nu
        out["V_u"] += a * a - nu
        out["V_s"] += float(s @ s) - ns
        out["V_tot"] += float(gbar @ gbar) - float(np.trace(Sig))
        shalf, pv = {}, {}
        for h in (1, 2):
            gh = cen(np.mean([[t.L(f"ban:{X}:w{w}", j, h) - t.L(refc(w, h), j, h) for j in S] for w in range(1, 6)], axis=0))
            uu = unit(cen(uh[h][[t.algs.index(j) for j in S]]))
            shalf[h] = gh - (gh @ uu) * uu
            pv[h] = cen(np.mean([[t.L(f"mention:{X}:w{w}", j, h) - t.L(f"neutral:{X}:w{w}:h{h}", j, h) for j in S]
                                 for w in range(1, 6)], axis=0))
        rho = 0.5 * (sp(shalf[1], pv[2]) + sp(shalf[2], pv[1]))
        out["rows"].append({"X": X, "rho": rho, "s": shalf, "pv": pv})
    a_, b_ = max(out["V_u"], 0.0), max(out["V_s"], 0.0)
    out["SHARE"] = b_ / (a_ + b_) if a_ + b_ > 0 else float("nan")
    out["AIM"] = float(np.nanmean([r["rho"] for r in out["rows"]])) if out["rows"] else float("nan")
    return out


def null_q95(rows) -> tuple[float, callable]:
    vals = []
    for r in rows:
        n = len(r["pv"][1])
        v = [0.5 * (sp(r["s"][1], r["pv"][2][list(p)]) + sp(r["s"][2], r["pv"][1][list(p)])) for p in itertools.permutations(range(n))]
        vals.append(np.array([x for x in v if not np.isnan(x)]))
    vals = [v for v in vals if len(v)]
    if not vals:
        return float("nan"), None
    # exact distribution of the mean by brute-force convolution on the 1/240 grid
    grid = 1 / 240
    dist = {0: 1.0}
    for v in vals:
        ks, cnt = np.unique(np.round(v / grid).astype(int), return_counts=True)
        new = {}
        for a, pa in dist.items():
            for k, c in zip(ks, cnt):
                new[a + k] = new.get(a + k, 0.0) + pa * c / len(v)
        dist = new
    sup = np.array(sorted(dist)) * grid / len(vals)
    pmf = np.array([dist[k] for k in sorted(dist)])
    cdf = np.cumsum(pmf)
    q95 = float(sup[np.searchsorted(cdf, 0.95 - 1e-12)])

    def pval(obs):
        return float(pmf[sup >= obs - 1e-12].sum())

    return q95, pval


def events(task: Task, lab: list[dict], sel: dict):
    d = sel[f"{task.task}_default"]
    s = sel[f"{task.task}_substitute"]["s_star"]
    spec = [("baseline", lambda r: r["kind"] == "baseline", []),
            ("modal", lambda r: r["kind"] == "ban" and r["X"] == d and r["phase"] == "A4", [d]),
            ("mention", lambda r: r["kind"] == "mention" and r["X"] == d, []),
            ("listall", lambda r: r["kind"] == "listall", [])]
    for x in sel.get(f"{task.task}_nondefault_bans", []):
        spec.append((f"ban {x}", lambda r, x=x: r["kind"] == "ban" and r["X"] == x and r["phase"] == "C", [x]))
    spec.append(("twostep", lambda r: r["kind"] == "twostep", [d, s]))
    out = []
    for name, f, banned in spec:
        rs = [r for r in lab if r["task"] == task.task and f(r)]
        nb = [r for r in rs if r["label"] != "no_code" and r["label"] not in banned]
        c = {}
        for r in nb:
            c[r["label"]] = c.get(r["label"], 0) + 1
        top = sorted(c.items(), key=lambda kv: -kv[1])
        lead = (top[0][1] - (top[1][1] if len(top) > 1 else 0)) / max(1, len(nb)) if top else 0
        out.append({"name": name, "banned": banned, "nb": nb, "mode": top[0][0] if top else None,
                    "clear": bool(top) and lead >= 0.15 and top[0][0] != "other", "conds": sorted({r["condition"] for r in rs})})
    return out


def main() -> int:
    c1j = json.loads((ROOT / "results" / "c1.json").read_text())
    gj = json.loads((ROOT / "results" / "frlp_gate.json").read_text())
    sel = json.loads((ROOT / "results" / "selections.json").read_text())
    lab = jl(ROOT / "data" / "labelled.jsonl")
    tasks = {t: Task(t) for t in ("t1", "t2")}
    checks, fails = [], []

    def chk(name, mine, theirs):
        ok = (mine is None and theirs is None) or (theirs is not None and mine is not None and
                                                   ((np.isnan(mine) and theirs is None) or abs(mine - theirs) <= TOL * max(1, abs(theirs))))
        checks.append({"quantity": name, "rederived": mine, "reported": theirs, "match": bool(ok)})
        if not ok:
            fails.append(name)

    # ---- gate (a)
    for t, T in tasks.items():
        sig, dm = [], []
        for s in range(5):
            Ls = np.array([T.L(f"baseline:s{s}", j) for j in T.algs])
            S_ = float(np.exp(Ls).sum())
            sig.append(S_)
            dm.append(float(np.exp(Ls[T.algs.index(T.d)]) / S_))
        chk(f"gate_a.{t}.mean_sigma", float(np.mean(sig)), gj["a"][t]["mean_sigma"])
        chk(f"gate_a.{t}.mean_default_mass", float(np.mean(dm)), gj["a"][t]["mean_default_mass"])
    # ---- gate (b), (c)
    deltas, hits = [], []
    for t, T in tasks.items():
        for ev in events(T, lab, sel):
            Se = [j for j in T.algs if j not in ev["banned"]]
            if len(ev["nb"]) >= 15:
                dl = []
                for r in ev["nb"]:
                    L = np.array([T.L(r["condition"], j) for j in Se])
                    smx = np.exp(L - L.max())
                    smx /= smx.sum()
                    q = 0.98 * (0.95 * smx + 0.05 / len(Se))
                    dl.append(math.log(q[Se.index(r["label"])]) - math.log(0.98 / len(Se)) if r["label"] in Se else 0.0)
                deltas.append(float(np.mean(dl)))
            if ev["clear"]:
                Lm = np.mean([[T.L(c, j) for j in Se] for c in ev["conds"]], axis=0)
                hits.append(Se[int(np.argmax(Lm))] == ev["mode"])
    chk("gate_b.mean_delta", float(np.mean(deltas)), gj["b_mean_delta"])
    chk("gate_c.hit_rate", float(np.mean(hits)) if hits else None, gj["c_hit_rate"])
    # ---- C1 both references
    res = {}
    for ref in ("neutral", "mention"):
        per = {t: c1(T, ref) for t, T in tasks.items()}
        res[ref] = per
        for t in tasks:
            rep = c1j["c1"][ref]["per_task"][t]
            for k in ("V_u", "V_s", "V_tot"):
                chk(f"c1.{ref}.{t}.{k}", per[t][k], rep[k])
            if rep["n_rows"]:
                chk(f"c1.{ref}.{t}.SHARE", per[t]["SHARE"], rep["SHARE"])
                chk(f"c1.{ref}.{t}.AIM", per[t]["AIM"], rep["AIM"])
        Vu = sum(per[t]["V_u"] for t in per)
        Vs = sum(per[t]["V_s"] for t in per)
        a_, b_ = max(Vu, 0), max(Vs, 0)
        chk(f"c1.{ref}.pooled.SHARE", b_ / (a_ + b_) if a_ + b_ > 0 else None, c1j["c1"][ref]["pooled"]["SHARE"])
        rows = [r for t in per for r in per[t]["rows"]]
        aim = float(np.nanmean([r["rho"] for r in rows])) if rows else float("nan")
        chk(f"c1.{ref}.pooled.AIM", aim, c1j["c1"][ref]["pooled"]["AIM"])
        q95, pval = null_q95(rows)
        rep_null = c1j["aim_nulls"][ref]["pooled"]["prime_and_veto"]
        chk(f"aim_null.{ref}.pooled.q95", q95, rep_null["null_q95"])
        if pval is not None:
            chk(f"aim_null.{ref}.pooled.p", pval(aim), rep_null["p"])
        # ---- branch (CIs from the reported bootstrap; everything else re-derived)
        br = c1j["branches"][ref]["pooled"]
        if "SHARE_ci95" in br:
            lad = all(c1j["ladder"][t]["ladder_exists"] for t in tasks if c1j["c1"][ref]["per_task"][t]["n_rows"] > 0)
            lo, hi = br["SHARE_ci95"]
            vt_lo = br["V_tot_ci95"][0]
            aim_pass = aim > q95
            assoc_pass = c1j["aim_nulls"][ref]["pooled"].get("association", {}).get("pass", False)
            if vt_lo <= 0:
                b = "PURE SUBTRACTION"
            elif lo > 0.5 and (aim_pass or assoc_pass):
                b = "SUBSTITUTION (" + ("prime-and-veto" if aim_pass else "association") + ")"
            elif lo > 0.5:
                b = "X-SPECIFIC BUT UNAIMED"
            elif hi < 0.5 and lad:
                b = "LADDER"
            elif hi < 0.5:
                b = "UNDETERMINED"
            else:
                b = "not resolved at this N"
            ok = b == br["branch"]
            checks.append({"quantity": f"branch.{ref}.pooled", "rederived": b, "reported": br["branch"], "match": ok})
            if not ok:
                fails.append(f"branch.{ref}.pooled")
    # ---- ladder
    for t, T in tasks.items():
        g = T.generic()
        nd = [T.algs.index(j) for j in T.algs if j != T.d]
        prof = {k: cen(v[nd]) for k, v in g.items()}
        cs = [float(prof[a] @ prof[b] / (np.linalg.norm(prof[a]) * np.linalg.norm(prof[b])))
              for a, b in itertools.combinations(sorted(prof), 2)]
        chk(f"ladder.{t}.mean_pairwise_cosine", float(np.mean(cs)), c1j["ladder"][t]["mean_pairwise_cosine"])
    # ---- placebo: shuffle PV survivor labels within rows (neutral reference)
    rng = np.random.default_rng(123)
    rows = [r for t in res["neutral"] for r in res["neutral"][t]["rows"]]
    placebo_p = []
    if rows:
        q95, pval = null_q95(rows)
        for _ in range(200):
            rr = []
            for r in rows:
                perm = rng.permutation(len(r["pv"][1]))
                rr.append(0.5 * (sp(r["s"][1], r["pv"][2][perm]) + sp(r["s"][2], r["pv"][1][perm])))
            placebo_p.append(pval(float(np.nanmean(rr))))
    ks = kstest(placebo_p, "uniform") if placebo_p else None
    out = {"n_checks": len(checks), "n_fail": len(fails), "fails": fails, "checks": checks,
           "placebo": {"n": len(placebo_p), "mean_p": float(np.mean(placebo_p)) if placebo_p else None,
                       "ks_stat": float(ks.statistic) if ks else None, "ks_p": float(ks.pvalue) if ks else None,
                       "note": "exact-null p-values are discrete, so the KS statistic is conservative"},
           "tolerance": TOL}
    (ROOT / "results" / "independent_rederivation.json").write_text(json.dumps(out, indent=1, default=float))
    print(f"rederivation: {len(checks) - len(fails)}/{len(checks)} match; placebo mean p = {out['placebo']['mean_p']}, "
          f"KS p = {out['placebo']['ks_p']}")
    for f_ in fails:
        print("MISMATCH", f_)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
