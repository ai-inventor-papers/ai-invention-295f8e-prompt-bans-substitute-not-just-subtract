#!/usr/bin/env python3
"""T6 independent re-derivation: recompute 10 random FRLP cells, the gate statistics (a, b, c), the C1 point SHARE
(primary reference, both tasks + pooled) and the AIM point value directly from the raw parquet score files with
separate code (no import of frlp.py / gate.py / c1.py), and compare with results/*.json (tolerance 1e-9).
Placebo: template labels permuted across ban rows -> the AIM should sit at its null."""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parent.parent
MODES = {"t1": ["bfs", "dfs", "bibfs", "iddfs", "astar_gbfs", "dijkstra"],
         "t2": ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"]}
WS = ["W1", "W2", "W3", "W4", "W5"]
RAND = ["A1001", "A1002", "A1003", "B2001", "B2002", "B2003"]


def lse(x):
    x = np.asarray(x, dtype=float)
    m = x.max()
    return float(m + np.log(np.exp(x - m).sum()))


def load():
    units = [json.loads(l) for l in (ROOT / "scores" / "units_done.jsonl").read_text().splitlines() if l.strip()]
    seen, recs = set(), []
    for u in units:
        if (u["task"], u["uid"]) in seen:
            continue
        seen.add((u["task"], u["uid"]))
        df = pd.read_parquet(ROOT / "scores" / "cells" / u["task"] / f"{u['uid']}.parquet")
        key = u["variant"] + "|" + u["cond_id"]
        for pid, tot in zip(df["prog_id"], df["total"]):
            recs.append((u["task"], key, pid, float(tot)))
    S = {}
    for t, k, p, v in recs:
        S.setdefault(t, {}).setdefault(k, {})[p] = v
    return S


def main() -> None:
    S = load()
    sel = [json.loads(l) for l in (ROOT / "data" / "forced_selected.jsonl").read_text().splitlines() if l.strip()]
    yl = json.loads((ROOT / "results" / "yields.json").read_text())["yields"]
    tp = json.loads((ROOT / "logs" / "throughput.json").read_text())
    M = int(tp["M"])
    progs = {t: [r for r in sel if r["task"] == t and r["rank"] < min(r["m_j"], M)] for t in MODES}
    meas = {t: [j for j in MODES[t] if yl[f"{t}|{j}"]["measurable"] and any(r["j"] == j for r in progs[t])]
            for t in MODES}
    lq = {}
    for t in MODES:
        for r in progs[t]:
            v = [S[t].get(f"primary|forced|{r['j']}|{r['family']}|k{k}", {}).get(r["prog_id"]) for k in range(10)]
            if all(x is not None for x in v):
                lq[r["prog_id"]] = lse(v) - math.log(10)

    def L(t, cond, j, half="all"):
        key = cond if "|" in cond.split("|")[0] or cond.startswith(("primary|", "edit|", "edit2|")) else cond
        key = ("edit" if cond.startswith("edit|") else "primary") + "|" + cond
        ps = [r for r in progs[t] if r["j"] == j and (half == "all" or r["half"] == half)]
        lw = [S[t][key][r["prog_id"]] - lq[r["prog_id"]] for r in ps if key in S[t] and r["prog_id"] in S[t][key]
              and r["prog_id"] in lq]
        if not lw:
            return float("nan")
        return math.log(yl[f"{t}|{j}"]["yield"]) + lse(lw) - math.log(len(lw))

    def Lmix(t, condA, condB, j, half="all"):
        """virtual neutral: noun A on h1, noun B on h2"""
        ps = [r for r in progs[t] if r["j"] == j and (half == "all" or r["half"] == half)]
        lw = []
        for r in ps:
            key = "primary|" + (condA if r["half"] == "h1" else condB)
            if key in S[t] and r["prog_id"] in S[t][key] and r["prog_id"] in lq:
                lw.append(S[t][key][r["prog_id"]] - lq[r["prog_id"]])
        return math.log(yl[f"{t}|{j}"]["yield"]) + lse(lw) - math.log(len(lw)) if lw else float("nan")

    out = {"checks": {}}
    # 10 random FRLP cells
    cells = [json.loads(l) for l in (ROOT / "results" / "frlp_cells.jsonl").read_text().splitlines() if l.strip()]
    prim = [c for c in cells if c["variant"] == "primary" and not c["condition"].startswith("edit2")]
    random.Random(3).shuffle(prim)
    diffs = []
    for c in prim[:10]:
        v = L(c["task"], c["condition"], c["algorithm"], c["half"])
        diffs.append(abs(v - c["L"]))
    out["checks"]["frlp_cells_max_absdiff"] = max(diffs)
    # gate (a)
    gate = json.loads((ROOT / "results" / "gate.json").read_text())["primary"]
    ev = json.loads((ROOT / "results" / "gate_events.json").read_text())
    npara = int(tp.get("gate_paraphrases", 5))
    Ss, ms = [], []
    for t in MODES:
        base = next(e for e in ev["events"] if e["event_id"] == f"{t}|baseline")
        for p in base["paraphrases"][:npara]:
            Ls = {j: L(t, f"exp1|baseline|p{p['paraphrase_id']}", j) for j in meas[t]}
            tot = sum(math.exp(v) for v in Ls.values())
            Ss.append(tot)
            ms.append(math.exp(Ls[{"t1": "bfs", "t2": "dijkstra"}[t]]) / tot)
    out["checks"]["gate_a_S_absdiff"] = abs(np.mean(Ss) - gate["a"]["mean_S"])
    out["checks"]["gate_a_m_absdiff"] = abs(np.mean(ms) - gate["a"]["mean_m_default"])
    # gate (b)/(c)
    des, hits, ncl = [], 0, 0
    for e in ev["events"]:
        t = e["task"]
        allowed = [j for j in MODES[t] if j not in e["banned"]]
        qs, ds = [], []
        for p in e["paraphrases"][:npara]:
            Ls = {j: L(t, f"exp1|{e['condition']}|p{p['paraphrase_id']}", j, "h1") for j in allowed if j in meas[t]}
            mx = max(Ls.values())
            z = sum(math.exp(v - mx) for v in Ls.values())
            q = {j: (math.exp(Ls[j] - mx) / z if j in Ls else 0.0) for j in allowed}
            qs.append(q)
            vals = []
            for lbl in p["labels"]:
                lbl = lbl if lbl in MODES[t] else "other"
                if lbl in e["banned"]:
                    continue
                vals.append(0.0 if lbl == "other" else math.log(0.93 * q[lbl] + 0.05 / len(allowed))
                            - math.log(0.98 / len(allowed)))
            ds.append(np.mean(vals) if vals else float("nan"))
        des.append(np.nanmean(ds))
        qbar = {j: np.mean([q[j] for q in qs]) for j in allowed}
        if e["clear_mode"]:
            ncl += 1
            hits += int(max(qbar, key=qbar.get) == e["realised_mode"])
    out["checks"]["gate_b_absdiff"] = abs(np.mean(des) - gate["b"]["mean_d_e"])
    out["checks"]["gate_c_hits_equal"] = float(hits == gate["c"]["hits"] and ncl == gate["c"]["n_clear"])
    # C1 point SHARE (primary reference) and AIM
    c1 = json.loads((ROOT / "results" / "c1.json").read_text())["primary_neutral"]
    assoc = json.loads((ROOT / "results" / "association.json").read_text())["profiles"]
    pooled = {"Vu": 0.0, "Vs": 0.0}
    aims = []
    placebo_rows = []
    for t in MODES:
        js = meas[t]
        nonce = np.mean([[L(t, f"ban|nonce|{w}", j) - Lmix(t, f"neutral|nonce|{w}|A", f"neutral|nonce|{w}|B", j)
                          for j in js] for w in WS], axis=0)
        base = np.array([L(t, "base0", j) for j in js])
        rand = np.mean([[L(t, f"edit|{d}", j) for j in js] for d in RAND], axis=0) - base
        nov = np.array([L(t, "novelty", j) for j in js]) - base
        u = (nonce + rand + nov) / 3
        Vu = Vs = 0.0
        for B in MODES[t]:
            Sv = [j for j in js if j != B]
            if len(Sv) < 3:
                continue
            idx = [js.index(j) for j in Sv]
            reps, r_h = [], []
            for w in WS:
                for h, ns in (("h1", "A"), ("h2", "B")):
                    g = np.array([L(t, f"ban|{B}|{w}", j, h) - L(t, f"neutral|{B}|{w}|{ns}", j, h) for j in Sv])
                    reps.append(g - g.mean())
                    r_h.append(h)
            C = np.array(reps)
            G = C.mean(0)
            ub = u[idx] - u[idx].mean()
            uh = ub / np.linalg.norm(ub)
            a = G @ uh
            s = G - a * uh
            tot = C.var(axis=0, ddof=1).sum() / len(C)
            sig = tot / (len(Sv) - 1)
            Vu += a * a - sig
            Vs += s @ s - (len(Sv) - 2) * sig
            res_h = {}
            for hn in ("h1", "h2"):
                Gh = np.array([c for c, hh in zip(C, r_h) if hh == hn]).mean(0)
                res_h[hn] = Gh - (Gh @ uh) * uh
            pv = {}
            for hn, ns in (("h1", "A"), ("h2", "B")):
                pv[hn] = np.mean([[L(t, f"mention|{B}|{w}", j, hn) - L(t, f"neutral|{B}|{w}|{ns}", j, hn) for j in Sv]
                                  for w in WS], axis=0)
            rho = np.nanmean([spearmanr(res_h["h1"], pv["h2"]).correlation, spearmanr(res_h["h2"], pv["h1"]).correlation])
            aims.append(rho)
            placebo_rows.append((res_h, pv))
        share = Vs / (Vs + Vu)
        out["checks"][f"share_{t}_absdiff"] = abs(share - c1["tasks"][t]["share_point"]["SHARE"])
        pooled["Vu"] += Vu
        pooled["Vs"] += Vs
    out["checks"]["share_pooled_absdiff"] = abs(pooled["Vs"] / (pooled["Vs"] + pooled["Vu"])
                                                - c1["pooled"]["share_point"]["SHARE"])
    aim_c1 = json.loads((ROOT / "results" / "c1.json").read_text())["primary_neutral"].get("aim_prime_veto", {})
    out["checks"]["aim_absdiff"] = abs(float(np.nanmean(aims)) - aim_c1.get("aim", float("nan")))
    # placebo: PV profiles shuffled across rows (template/row labels permuted) -> aim near its null
    rng = np.random.default_rng(5)
    pl = []
    for _ in range(200):
        vals = []
        for res_h, pv in placebo_rows:
            perm = rng.permutation(len(pv["h1"]))
            vals.append(np.nanmean([spearmanr(res_h["h1"], pv["h2"][perm]).correlation,
                                    spearmanr(res_h["h2"], pv["h1"][perm]).correlation]))
        pl.append(np.nanmean(vals))
    out["placebo_aim"] = {"mean": float(np.mean(pl)), "sd": float(np.std(pl)), "observed": float(np.nanmean(aims))}
    tol = 1e-9
    out["all_match"] = bool(all((v < tol) if "absdiff" in k else (v == 1.0) for k, v in out["checks"].items()))
    (ROOT / "results" / "independent_rederivation.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
