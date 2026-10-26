#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers from the RAW row files, through code paths that share nothing
with src/analysis_*.py (pandas group-bys; a direct-simulation hull estimator instead of exp20's CRN HullSampler; a
hand-written exact binomial test instead of scipy's), plus placebos that must FAIL.

Checks:
  F   literal cell: C_T (seeds whose final label is not constant over the 4 temperatures), completion, noise floor.
  C   per D5 task: H5 of PN and of each text sampler by direct simulation (grid 0.05 on the full simplex, 400 draws;
      tolerance 0.10 vs results/prices.json), the Claim-C win count and verdict.
  M   PN vs DMD and PN plain vs PN twin discordant counts and exact McNemar p (vs results/*.json).
  P1  placebo: arm labels shuffled within task (among the Claim-C arms, 20 shuffles, 150 draws, grid 0.1): the win count should sit near
      the chance level, not at the observed one; the verdict should not be stable.
  P2  placebo: PN rows replaced by TWIN rows (PN_a1, PN_a2 := TWIN at the same slots): D_t = H5_PN - best_text <= 0.
  H   the sha256 chain of commitments.log verifies and every committed file is unchanged since its last commit.
-> results/rederive.json
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
D5 = ["T03", "T10", "T2", "T05", "T1"]
CLASSES = {"PN": ["TWIN", "PN_a1", "PN_a2"], "IFG": ["TWIN", "IFG_hot", "IFG_paper"], "PSL": ["TWIN", "PSL"],
           "EAP": ["TWIN", "EAP"], "BINT": ["TWIN", "BINT"]}
TEXT = ["IFG", "PSL", "EAP", "BINT"]


def jl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def frame() -> pd.DataFrame:
    raw = pd.DataFrame(jl(ROOT / "data" / "samples_raw.jsonl"))[["sample_id", "task", "arm", "template", "slot"]]
    raw = raw.drop_duplicates("sample_id")
    lab = pd.DataFrame(jl(ROOT / "data" / "labels.jsonl"))[["sample_id", "label", "passed"]].drop_duplicates("sample_id")
    df = raw.merge(lab, on="sample_id", how="inner")
    df["passed"] = df["passed"].fillna(False).astype(bool)
    df["label"] = df["label"].fillna("invalid")
    return df


def hill_exp_entropy(labels: list[str]) -> float:
    c = Counter(labels)
    n = sum(c.values())
    return float(math.exp(-sum(v / n * math.log(v / n) for v in c.values()))) if n else float("nan")


def direct_hull(settings: list[tuple[float, list[str]]], rng: np.random.Generator, draws: int = 400,
                depth: int = 25, step: float = 0.05) -> float:
    """settings = [(pass, correct_labels)], TWIN first. For each mixture w (grid on the full simplex) simulate `draws`
    samples of 25 correct programs: each program comes from setting j with probability proportional to w_j pass_j and
    is a uniform draw (with replacement) from that setting's correct programs; Hill = exp(Shannon entropy) of each
    sample's label counts; H5 = max mean Hill at cost <= 0.05. (Vectorised numpy; independent of exp20's sampler.)"""
    k = len(settings)
    m = int(round(1 / step))
    cats = sorted({l for _, labs in settings for l in labs})
    ci = {c: i for i, c in enumerate(cats)}
    pools = [np.array([ci[l] for l in s[1]], dtype=np.int64) for s in settings]
    pas = np.array([s[0] for s in settings])
    p0 = pas[0]
    best = float("nan")
    rows = np.repeat(np.arange(draws), depth)
    for comb in np.ndindex(*([m + 1] * (k - 1))):
        if sum(comb) > m:
            continue
        w = np.array(list(comb) + [m - sum(comb)], float) / m
        if p0 - float((w * pas).sum()) > 0.05 + 1e-12:
            continue
        a = w * pas
        for j in range(k):
            if len(pools[j]) == 0:
                a[j] = 0.0
        if a.sum() <= 0:
            continue
        pi = a / a.sum()
        js = rng.choice(k, size=(draws, depth), p=pi)
        labs = np.empty((draws, depth), dtype=np.int64)
        for j in range(k):
            msk = js == j
            if msk.any():
                labs[msk] = pools[j][rng.integers(len(pools[j]), size=int(msk.sum()))]
        cnt = np.zeros((draws, max(len(cats), 1)))
        np.add.at(cnt, (rows, labs.ravel()), 1)
        pr = cnt / depth
        with np.errstate(divide="ignore", invalid="ignore"):
            hh = np.exp(-np.where(pr > 0, pr * np.log(pr), 0.0).sum(1))
        h = float(hh.mean())
        if not np.isfinite(best) or h > best:
            best = h
    return best


def class_settings(df: pd.DataFrame, task: str, arms: list[str], min_n: int = 30):
    out = []
    for a in arms:
        sub = df[(df.task == task) & (df.arm == a)]
        if len(sub) < min_n:
            if a == "TWIN":
                return None
            continue
        out.append((float(sub.passed.mean()), list(sub[sub.passed].label)))
    return out if len(out) >= 2 else None


def binom_two_sided(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return float(min(1.0, 2 * tail))


def claim_counts(df: pd.DataFrame, rng: np.random.Generator, draws: int = 400, step: float = 0.05) -> dict:
    per = {}
    wins = 0
    for t in D5:
        h = {}
        for c, arms in CLASSES.items():
            st = class_settings(df, t, arms)
            if st is not None:
                h[c] = direct_hull(st, rng, draws=draws, step=step)
        tx = {c: v for c, v in h.items() if c in TEXT}
        if "PN" in h and tx:
            win = round(h["PN"], 2) >= round(max(tx.values()), 2)
            wins += win
            per[t] = {"H5": h, "PN_wins": bool(win), "D_t": h["PN"] - max(tx.values())}
    return {"per_task": per, "wins": wins, "verdict": "SUPPORTED" if wins >= 3 else "DISCONFIRMED"}


def main() -> None:
    out: dict = {}
    rng = np.random.default_rng(99)
    # ---------------------------------------------------------------- F
    lr = pd.DataFrame(jl(ROOT / "data" / "literal_raw.jsonl"))
    ll = pd.DataFrame(jl(ROOT / "data" / "literal_labels.jsonl"))[["sample_id", "label", "passed"]]
    lf = lr.merge(ll, on="sample_id")
    main_t = lf[~lf.repeat.astype(bool)]
    g = main_t.groupby(["template", "slot"])
    complete = g.filter(lambda x: x.completed.astype(bool).all() and x.temperature.nunique() == 4)
    ct = int(complete.groupby(["template", "slot"]).label.nunique().gt(1).sum())
    n_seeds = int(complete.groupby(["template", "slot"]).ngroups)
    rep = lf[lf.repeat.astype(bool)].set_index(["template", "slot"])
    t07 = main_t[main_t.temperature.astype(float) == 0.7].set_index(["template", "slot"])
    both = t07.join(rep, lsuffix="_a", rsuffix="_b", how="inner")
    out["F"] = {"C_T": ct, "n_seeds": n_seeds, "completion": float(lf.completed.astype(bool).mean()),
                "noise_floor_byte_identical": int(sum(a == b for a, b in zip(both.think_ids_a, both.think_ids_b))),
                "noise_floor_label_agreement": float((both.label_a == both.label_b).mean())}
    lc = json.loads((ROOT / "results" / "literal_cell.json").read_text())
    out["F"]["matches_analysis"] = (ct == lc["C_T"]["n_change_final_label"] and n_seeds == lc["C_T"]["n_seeds_all4_completed"]
                                    and out["F"]["noise_floor_byte_identical"] == lc["noise_floor"]["byte_identical_thinking"])
    # ---------------------------------------------------------------- C
    df = frame()
    cc = claim_counts(df, rng)
    pr = json.loads((ROOT / "results" / "prices.json").read_text())
    cmp_ = {}
    for t, v in cc["per_task"].items():
        for c, h in v["H5"].items():
            ref = pr.get(t, {}).get(c, {}).get("H5")
            cmp_[f"{t}|{c}"] = {"rederived": h, "analysis": ref, "abs_diff": abs(h - ref) if ref is not None else None}
    claim = json.loads((ROOT / "results" / "claim_c.json").read_text())
    out["C"] = {"rederived": cc, "H5_comparison": cmp_,
                "max_abs_diff": max((x["abs_diff"] for x in cmp_.values() if x["abs_diff"] is not None), default=None),
                "analysis_wins": claim["primary"]["wins"], "analysis_verdict": claim["verdict"],
                "verdict_matches": cc["verdict"] == claim["verdict"]}
    # ---------------------------------------------------------------- M
    dfl = json.loads((ROOT / "results" / "defaults.json").read_text())
    pvd = json.loads((ROOT / "results" / "pn_vs_dmd.json").read_text())["per_task"]
    mm = {}
    for t in D5:
        d = dfl[t]["default"]
        if d is None:
            continue
        piv = df[df.task == t].assign(off=lambda x: (x.passed & (x.label != d)).astype(int)).pivot_table(
            index=["template", "slot"], columns="arm", values="off", aggfunc="first")
        for a in ("1", "2"):
            if f"PN_a{a}" in piv and f"DMD_a{a}" in piv and "TWIN" in piv:
                sub = piv[[f"PN_a{a}", f"DMD_a{a}", "TWIN"]].dropna()
                b = int(((sub[f"PN_a{a}"] == 1) & (sub[f"DMD_a{a}"] == 0)).sum())
                c = int(((sub[f"PN_a{a}"] == 0) & (sub[f"DMD_a{a}"] == 1)).sum())
                ref = pvd.get(t, {}).get(f"alpha{a}", {}).get("mcnemar_PN_vs_DMD", {})
                mm[f"{t}|alpha{a}"] = {"PN_only": b, "DMD_only": c, "p": binom_two_sided(b, c),
                                       "matches": (b == ref.get("x_only") and c == ref.get("y_only")
                                                   and abs(binom_two_sided(b, c) - ref.get("p_exact", -1)) < 1e-9)}
    out["M"] = mm
    # ---------------------------------------------------------------- placebos
    arms_c = sorted({a for v in CLASSES.values() for a in v})
    shuf = []
    rs = random.Random(5)
    for i in range(20):
        d2 = df.copy()
        for t in D5:
            m = (d2.task == t) & d2.arm.isin(arms_c)
            vals = list(d2.loc[m, "arm"])
            rs.shuffle(vals)
            d2.loc[m, "arm"] = vals
        shuf.append(claim_counts(d2, np.random.default_rng(1000 + i), draws=150, step=0.1)["wins"])
    out["P1_arm_shuffle"] = {"win_counts": dict(Counter(shuf)), "mean_wins": float(np.mean(shuf)),
                             "observed_wins": cc["wins"],
                             "fraction_reaching_observed_or_more": float(np.mean([w >= cc["wins"] for w in shuf]))}
    d3 = df[~df.arm.isin(["PN_a1", "PN_a2"])].copy()
    tw = d3[d3.arm == "TWIN"]
    d3 = pd.concat([d3, tw.assign(arm="PN_a1"), tw.assign(arm="PN_a2")])
    p2 = claim_counts(d3, np.random.default_rng(3))
    out["P2_PN_as_TWIN"] = {"D_t": {t: v["D_t"] for t, v in p2["per_task"].items()},
                            "all_D_le_0": all(v["D_t"] <= 1e-9 for v in p2["per_task"].values()),
                            "wins": p2["wins"]}
    # ---------------------------------------------------------------- H
    prev = "0" * 64
    breaks = 0
    last = {}
    for line in (ROOT / "commitments.log").read_text().splitlines():
        if not line.strip():
            continue
        utc, rp, h, chain, tag = line.split()[:5]
        if hashlib.sha256((prev + h + utc + rp).encode()).hexdigest() != chain:
            breaks += 1
        prev = chain
        last[rp] = h
    changed = [rp for rp, h in last.items() if hashlib.sha256((ROOT / rp).read_bytes()).hexdigest() != h]
    out["H"] = {"chain_breaks": breaks, "files_changed_since_last_commit": changed}
    (ROOT / "results" / "rederive.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({"F": out["F"], "C_verdict_matches": out["C"]["verdict_matches"],
                      "C_max_abs_diff": out["C"]["max_abs_diff"], "M_all_match": all(v["matches"] for v in mm.values()),
                      "P1": out["P1_arm_shuffle"], "P2": out["P2_PN_as_TWIN"], "H": out["H"]}, indent=1, default=str))


if __name__ == "__main__":
    main()
