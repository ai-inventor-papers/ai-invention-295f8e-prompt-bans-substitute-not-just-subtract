#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers from the raw files (no import of analysis.py).

FRLP: per-program log-likelihoods are re-summed from data/token_lp/*.npz (not the JSONL sums), denominators rebuilt
from the per-prompt sample counts, D_X(arm) recomputed with the ESS-down-weighted template mean, then F_direct,
F_prompt, I, and the knockout restorations. C5: projections recomputed from work/c5_hR.npz and the combined
within-cell Spearman from scipy. Every number is compared with results/analysis.json; prints the mismatch count.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ["W1", "W2", "W3", "W4", "W5"]
X = {"t1": "bfs", "t2": "dijkstra"}
TOL = 1e-6


def rd(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def token_sums() -> dict:
    ll = {}
    for f in sorted((ROOT / "data" / "token_lp").glob("*.npz")):
        base = f.name.rsplit("__", 1)[0]
        parts = base.split("_")
        t, half, w = parts[0], parts[-1], parts[-2]
        cond = "_".join(parts[1:-2])
        z = np.load(f)
        o = z["offsets"]
        for i, u in enumerate(z["uids"]):
            ll[(t, cond, w, half, str(u))] = float(np.sum(z["lp"][o[i]:o[i + 1]].astype(np.float64)))
    return ll


def lookup(ll: dict, t: str, cond: str, w: str, uid: str, half: int) -> float:
    if cond in ("a", "K0", "K1", "K2", "B1", "B2", "B3", "mention", "pl"):
        return ll.get((t, cond, w, "all", uid), np.nan)
    return ll.get((t, cond, w, str(half), uid), np.nan)


def lme(v: np.ndarray) -> float:
    m = v.max()
    return float(m + np.log(np.mean(np.exp(v - m))))


def ess(v: np.ndarray) -> float:
    e = np.exp(v - v.max())
    return float(e.sum() ** 2 / (e ** 2).sum())


def main() -> int:
    an = json.loads((ROOT / "results" / "analysis.json").read_text())
    progs = rd(ROOT / "data" / "frlp_programs.jsonl")
    summ = json.loads((ROOT / "results" / "frlp_programs_summary.json").read_text())["per_algorithm"]
    ll = token_sums()
    mism, checks = [], 0

    def cmp(name: str, mine: float, theirs: float) -> None:
        nonlocal checks
        checks += 1
        if theirs is None or mine is None or not np.isfinite(mine) or not np.isfinite(theirs):
            if not (theirs is None and (mine is None or not np.isfinite(mine))):
                mism.append((name, mine, theirs))
            return
        if abs(mine - theirs) > TOL * max(1.0, abs(theirs)):
            mism.append((name, mine, theirs))

    Dtask = {}
    for t in ("t1", "t2"):
        x = X[t]
        P = sorted([p for p in progs if p["task"] == t and p["algorithm"] == x], key=lambda p: (p["half"], p["prog_index"]))
        uids = [f"{t}:{x}:{p['prog_index']}" for p in P]
        halves = [p["half"] for p in P]
        counts = summ[f"{t}:{x}"]["prompt_counts"]
        tot = sum(counts.values())
        den = []
        for u in uids:
            acc = []
            for k, n in counts.items():
                kind, idx = k.split(":")
                cond = f"forced_{x}_{'p' if kind == 'paraphrase' else 'd'}{idx}"
                acc.append((n / tot, ll[(t, cond, "F", "all", u)]))
            m = max(v for _, v in acc)
            den.append(m + np.log(sum(wt * np.exp(v - m) for wt, v in acc)))
        den = np.array(den)
        D = {}
        Lw = defaultdict(dict)
        Ew = defaultdict(dict)
        for cond in ("a", "b", "c", "d", "e", "f", "K0", "K1", "K2", "B1", "B2", "B3", "K0b", "mention"):
            for w in TEMPLATES:
                v = np.array([lookup(ll, t, cond, w, u, h) for u, h in zip(uids, halves)]) - den
                if np.isfinite(v).all():
                    Lw[cond][w] = lme(v)
                    Ew[cond][w] = ess(v)
        for cond in Lw:
            if len(Lw[cond]) < len(TEMPLATES):
                continue
            num = dnm = 0.0
            for w in TEMPLATES:
                om = min(1.0, min(Ew[cond][w], Ew["b"][w]) / 5.0)
                num += om * (Lw[cond][w] - Lw["b"][w])
                dnm += om
            D[cond] = num / dnm
            cmp(f"{t} D[{cond}]", D[cond], an["route_frlp"]["per_task"][t]["D"].get(cond))
        e = an["route_frlp"]["per_task"][t]
        cmp(f"{t} F_direct", D["d"] / D["a"], e["F_direct"])
        cmp(f"{t} F_prompt", D["c"] / D["a"], e["F_prompt"])
        cmp(f"{t} I", D["a"] - D["c"] - D["d"], e["I"])
        for k in ("K0", "K1", "K2", "B1", "B2", "B3"):
            if k in D:
                cmp(f"{t} R_raw[{k}]", (D[k] - D["a"]) / (-D["a"]), e["knockouts"][k]["R_raw"])
        Dtask[t] = D
    pooled = an["route_frlp"].get("pooled")
    if pooled:
        ok = an["route_frlp"]["tasks_in_pool"]
        cmp("pooled F_direct", sum(Dtask[t]["d"] for t in ok) / sum(Dtask[t]["a"] for t in ok), pooled["F_direct"])
        cmp("pooled F_prompt", sum(Dtask[t]["c"] for t in ok) / sum(Dtask[t]["a"] for t in ok), pooled["F_prompt"])
    # C5
    c5 = an.get("c5")
    if c5 and (ROOT / "work" / "c5_hR.npz").exists():
        z = np.load(ROOT / "work" / "c5_hR.npz")
        H, wids, kinds, tasks, exps = z["H"], list(z["wids"]), list(z["kinds"]), list(z["tasks"]), list(z["exps"])
        keep_ban = {w["wid"] for w in c5["wordings"]}
        L = list(range(0, 21))  # HS_IDX 8..29 -> layers 8..28 are the first 21 entries
        ref_mean, shift = {}, {}
        for e_ in sorted(set(exps)):
            for t in ("t1", "t2"):
                r = [i for i in range(len(wids)) if exps[i] == e_ and tasks[i] == t and kinds[i] != "ban"]
                b = [i for i in range(len(wids)) if exps[i] == e_ and tasks[i] == t and kinds[i] == "ban"
                     and wids[i] in keep_ban]
                if r and b:
                    ref_mean[(e_, t)] = H[r][:, L].mean(0)
                    shift[(e_, t)] = H[b][:, L].mean(0) - ref_mean[(e_, t)]
        ban_order = [w["wid"] for w in c5["wordings"]]
        pos = {w: i for i, w in enumerate(wids)}
        proj = np.zeros((len(ban_order), len(L)))
        for k, wid in enumerate(ban_order):
            i = pos[wid]
            e_, t = exps[i], tasks[i]
            d = np.mean([s / np.linalg.norm(s, axis=-1, keepdims=True) for (ee, tt), s in shift.items() if ee != e_],
                        axis=0)
            d = d / np.linalg.norm(d, axis=-1, keepdims=True)
            proj[k] = np.sum((H[i][L] - ref_mean[(e_, t)]) * d, axis=-1)
        zz = (proj - proj.mean(0)) / (proj.std(0) + 1e-12)
        pi = zz.mean(1)
        share = np.array([w["banned_share"] for w in c5["wordings"]])
        cells = [f"{w['exp']}|{w['task']}" for w in c5["wordings"]]
        num = wsum = 0.0
        for c in sorted(set(cells)):
            g = [i for i, cc in enumerate(cells) if cc == c]
            if len(g) <= 3 or np.std(share[g]) == 0 or np.std(pi[g]) == 0:
                continue
            r = stats.spearmanr(pi[g], share[g]).statistic
            num += (len(g) - 3) * np.arctanh(np.clip(r, -0.999999, 0.999999))
            wsum += len(g) - 3
        cmp("C5 combined rho", float(np.tanh(num / wsum)), c5["shared_ban_direction"]["test"]["rho"])
        for k, w in enumerate(c5["wordings"]):
            if abs(pi[k] - w["pi"]) > 1e-5:
                mism.append((f"C5 pi {w['wid']}", pi[k], w["pi"]))
                break
    out = {"checks": checks, "mismatches": len(mism), "details": [list(map(str, m)) for m in mism]}
    (ROOT / "results" / "rederive.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return 0 if not mism else 1


if __name__ == "__main__":
    sys.exit(main())
