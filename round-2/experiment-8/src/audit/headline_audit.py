#!/usr/bin/env python3
"""Headline-number audit: recompute every number quoted in the README / final response from the RAW files with code
independent of the pipeline (pandas + scipy, no import of analysis.py / supplementary.py / natural_frlp.py), then run
each statistical test on shuffled or placebo input and check that it FAILS there.

Raw inputs: data/samples.jsonl (behaviour labels), data/token_lp/*.npz (per-token log-probs), data/frlp_programs.jsonl
(halves, prompt counts via results/frlp_programs_summary.json), data/natural_frlp_scores.jsonl, results/c5.json
wordings (pi = projection, banned share; pi itself is re-derived from work/c5_hR.npz by audit/rederive.py).
Writes results/headline_audit.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
X = {"t1": "bfs", "t2": "dijkstra"}
W = ["W1", "W2", "W3", "W4", "W5"]
rng = np.random.default_rng(2026)
out: dict = {"checks": [], "placebo_tests": []}


def check(name: str, mine: float, reported: float, tol: float = 1e-6) -> None:
    ok = bool(np.isfinite(mine) and np.isfinite(reported) and abs(mine - reported) <= tol * max(1.0, abs(reported)))
    out["checks"].append({"name": name, "recomputed": float(mine), "reported": float(reported), "match": ok})


an = json.loads((ROOT / "results/analysis.json").read_text())
sup = json.loads((ROOT / "results/supplementary.json").read_text())

# ---------------------------------------------------------------- 1. behaviour shares (pandas counting)
S = pd.read_json(ROOT / "data/samples.jsonl", lines=True)
S["banned_x"] = [lab == X[t] for lab, t in zip(S["label"], S["task"])]
share = S.groupby(["task", "condition"])["banned_x"].mean()
for t in X:
    for arm in ("a", "b", "c", "d", "K1", "K2"):
        check(f"behaviour {t} banned share {arm}", share[(t, arm)], an["behaviour"]["per_task"][t][arm]["banned_share"])
    check(f"behaviour {t} banned share K0", share[(t, "K0")], sup["behaviour_contrasts"][t]["K0_banned_share"]["share"])
    sb, sa, sc, sd = (share[(t, k)] for k in ("b", "a", "c", "d"))
    check(f"behaviour {t} F_direct_beh", (sb - sd) / (sb - sa), an["behaviour"]["per_task"][t]["F_direct_beh"])
    check(f"behaviour {t} F_prompt_beh", (sb - sc) / (sb - sa), an["behaviour"]["per_task"][t]["F_prompt_beh"])

# McNemar a vs b on matched CRN pairs, and the same test after randomly swapping arm labels within pairs
for t in X:
    piv = S[(S.task == t) & S.condition.isin(["a", "b"])].pivot_table(index=["template", "sample_id"],
                                                                        columns="condition", values="banned_x")
    a_, b_ = piv["a"].astype(bool).values, piv["b"].astype(bool).values
    n10, n01 = int((a_ & ~b_).sum()), int((~a_ & b_).sum())
    p_real = stats.binomtest(n10, n10 + n01, 0.5).pvalue
    rep = an["behaviour"]["per_task"][t]["matched_flips"]["a_vs_b"]
    check(f"McNemar {t} a vs b p", p_real, rep["mcnemar_exact_p"])
    rej = 0
    for _ in range(500):
        swap = rng.random(len(a_)) < 0.5
        aa, bb = np.where(swap, b_, a_), np.where(swap, a_, b_)
        m10, m01 = int((aa & ~bb).sum()), int((~aa & bb).sum())
        rej += (stats.binomtest(m10, m10 + m01, 0.5).pvalue < 0.05) if m10 + m01 else 0
    out["placebo_tests"].append({"test": f"McNemar a vs b ({t}) on arm labels swapped at random within pairs",
                                 "real_p": float(p_real), "rejection_rate_at_0.05": rej / 500,
                                 "fails_on_placebo": bool(rej / 500 <= 0.10)})

# ---------------------------------------------------------------- 2. FRLP from the per-token npz (independent sums)
progs = pd.read_json(ROOT / "data/frlp_programs.jsonl", lines=True)
counts = json.loads((ROOT / "results/frlp_programs_summary.json").read_text())["per_algorithm"]
ll = {}
for f in (ROOT / "data/token_lp").glob("*.npz"):
    stem = f.name.split("__")[0].split("_")
    task, half, tmpl, cond = stem[0], stem[-1], stem[-2], "_".join(stem[1:-2])
    z = np.load(f)
    for i, u in enumerate(z["uids"]):
        ll[(task, cond, tmpl, half, str(u))] = z["lp"][z["offsets"][i]:z["offsets"][i + 1]].astype(np.float64).sum()


def lw_matrix(t: str, cond: str, noun_half: str | None = None) -> np.ndarray:
    """[template, program] log weights for X programs under arm cond (own-half noun unless noun_half='B')."""
    P = progs[(progs.task == t) & (progs.algorithm == X[t])].sort_values(["half", "prog_index"])
    c = counts[f"{t}:{X[t]}"]["prompt_counts"]
    tot = sum(c.values())
    M = np.full((len(W), len(P)), np.nan)
    for j, (_, p) in enumerate(P.iterrows()):
        uid = f"{t}:{X[t]}:{p.prog_index}"
        terms = [n / tot * np.exp(ll[(t, f"forced_{X[t]}_{'p' if k.startswith('para') else 'd'}{k.split(':')[1]}",
                                      "F", "all", uid)] - 0.0) for k, n in c.items()]
        den = np.log(np.sum(terms)) if np.all(np.isfinite(terms)) and np.sum(terms) > 0 else np.nan
        if not np.isfinite(den):  # underflow-safe version
            vals = np.array([ll[(t, f"forced_{X[t]}_{'p' if k.startswith('para') else 'd'}{k.split(':')[1]}", "F",
                                 "all", uid)] for k in c])
            wts = np.array(list(c.values())) / tot
            den = vals.max() + np.log(np.sum(wts * np.exp(vals - vals.max())))
        for i, w in enumerate(W):
            if cond in ("a", "pl", "K0", "K1", "K2", "B1", "B2", "B3", "mention"):
                key = (t, cond, w, "all", uid)
            elif noun_half == "B":
                key = (t, cond, w, "2" if p.half == 2 else "xh1", uid)
            else:
                key = (t, cond, w, str(p.half), uid)
            M[i, j] = ll[key] - den if key in ll else np.nan
    return M


def L(M: np.ndarray) -> np.ndarray:
    m = M.max(axis=1, keepdims=True)
    return (m + np.log(np.mean(np.exp(M - m), axis=1, keepdims=True)))[:, 0]


def ess(M: np.ndarray) -> np.ndarray:
    e = np.exp(M - M.max(axis=1, keepdims=True))
    return e.sum(1) ** 2 / (e ** 2).sum(1)


def D(Ma: np.ndarray, Mb: np.ndarray) -> float:
    om = np.minimum(1.0, np.minimum(ess(Ma), ess(Mb)) / 5.0)
    return float(np.sum(om * (L(Ma) - L(Mb))) / np.sum(om))


Dt = {}
for t in X:
    Mb = lw_matrix(t, "b")
    Dt[t] = {arm: D(lw_matrix(t, arm), Mb) for arm in ("a", "c", "d", "e", "f")}
    for arm in ("a", "c", "d"):
        check(f"FRLP {t} D_X({arm})", Dt[t][arm], an["route_frlp"]["per_task"][t]["D"][arm])
    check(f"FRLP {t} F_R", Dt[t]["e"] / Dt[t]["a"], an["route_frlp"]["per_task"][t]["F_R"])
    check(f"FRLP {t} F_spec", Dt[t]["f"] / Dt[t]["a"], an["route_frlp"]["per_task"][t]["F_spec"])
    # reported placebo value: plain template mean of L(pl) - L(b, noun B) (no ESS weighting)
    d_pl_plain = float(np.mean(L(lw_matrix(t, "pl")) - L(lw_matrix(t, "b", noun_half="B"))))
    check(f"FRLP {t} placebo D_pl (plain mean)", d_pl_plain, an["route_frlp"]["per_task"][t]["placebo"]["D_pl"])
    # placebo: the neutral-A/neutral-B splice against b under noun B must show no 'ban effect' (CI includes 0),
    # whereas the real ban's CI excludes 0 -- same bootstrap (templates x programs within halves) for both.
    Mpl, MbB, Ma = lw_matrix(t, "pl"), lw_matrix(t, "b", noun_half="B"), lw_matrix(t, "a")
    halves = progs[(progs.task == t) & (progs.algorithm == X[t])].sort_values(["half", "prog_index"])["half"].values
    h1, h2 = np.where(halves == 1)[0], np.where(halves == 2)[0]
    bpl, bban, bshuf = [], [], []
    for _ in range(1000):
        wi = rng.integers(0, len(W), len(W))
        pj = np.concatenate([rng.choice(h1, len(h1)), rng.choice(h2, len(h2))])
        bpl.append(D(Mpl[wi][:, pj], MbB[wi][:, pj]))
        bban.append(D(Ma[wi][:, pj], Mb[wi][:, pj]))
        # label-shuffle placebo: swap the 'ban' and 'neutral' scores of each (template, program) at random
        sw = rng.random(Ma.shape) < 0.5
        A2, B2 = np.where(sw, Mb, Ma), np.where(sw, Ma, Mb)
        bshuf.append(D(A2[wi][:, pj], B2[wi][:, pj]))
    ci_pl, ci_ban, ci_sh = (np.percentile(v, [2.5, 97.5]).tolist() for v in (bpl, bban, bshuf))
    out["placebo_tests"].append({
        "test": f"FRLP prerequisite (ban effect CI excludes 0), {t}",
        "real_ban_D": Dt[t]["a"], "real_ban_ci": ci_ban, "real_passes": bool(ci_ban[1] < 0),
        "placebo_splice_D": D(Mpl, MbB), "placebo_ci": ci_pl, "label_shuffled_ci": ci_sh,
        "fails_on_placebo": bool(ci_pl[0] < 0 < ci_pl[1]), "fails_on_label_shuffle": bool(ci_sh[0] < 0 < ci_sh[1])})
pool_a = sum(Dt[t]["a"] for t in X)
check("FRLP pooled F_prompt", sum(Dt[t]["c"] for t in X) / pool_a, an["route_frlp"]["pooled"]["F_prompt"])
check("FRLP pooled F_direct", sum(Dt[t]["d"] for t in X) / pool_a, an["route_frlp"]["pooled"]["F_direct"])

# opening-line shares (string test on the raw code) and first-16-token share of the drop (raw per-token arrays)
def opens_with_import(code: object) -> bool:
    for ln in str(code or "").splitlines():
        if ln.strip():
            return ln.strip().startswith(("import ", "from "))
    return False


S["import_open"] = S["code"].map(opens_with_import)
imp = S.groupby(["task", "condition"])["import_open"].mean()
for t in X:
    for arm in ("a", "b", "c", "d", "K0"):
        check(f"opening {t} import-first share {arm}", imp[(t, arm)],
              sup["opening_lines"][t][arm]["share_import_opening"])
tok_lp = {}
for f in (ROOT / "data/token_lp").glob("*.npz"):
    stem = f.name.split("__")[0].split("_")
    z = np.load(f)
    for i, u in enumerate(z["uids"]):
        tok_lp[(stem[0], "_".join(stem[1:-2]), stem[-2], stem[-1], str(u))] = z["lp"][z["offsets"][i]:z["offsets"][i + 1]]
for t in X:
    for arm in ("a", "c", "d"):
        tot = first = 0.0
        for _, p in progs[(progs.task == t) & (progs.algorithm == X[t])].iterrows():
            uid = f"{t}:{X[t]}:{p.prog_index}"
            for w in W:
                ref = tok_lp[(t, "b", w, str(p.half), uid)].astype(np.float64)
                src = tok_lp[(t, arm, w, "all" if arm == "a" else str(p.half), uid)].astype(np.float64)
                dlt = src - ref
                tot += dlt.sum()
                first += dlt[:16].sum()
        check(f"token localisation {t} first-16 share {arm}", first / tot,
              an["token_localisation"][t][arm]["first16_share_of_delta"])

# ---------------------------------------------------------------- 3. natural-proposal readout (pandas)
N = pd.read_json(ROOT / "data/natural_frlp_scores.jsonl", lines=True)
nat = json.loads((ROOT / "results/natural_frlp.json").read_text())
wide = N.pivot_table(index=["task", "template", "sample_id"], columns="arm", values="ll")
Dn = {}
for t in X:
    sub = wide.loc[t]
    Dn[t] = {}
    for arm in ("a", "c", "d"):
        per_w = [np.log(np.mean(np.exp((g[arm] - g["b"]) - (g[arm] - g["b"]).max()))) + (g[arm] - g["b"]).max()
                 for _, g in sub.groupby(level=0)]
        Dn[t][arm] = float(np.mean(per_w))
        check(f"natural {t} D_nat({arm})", Dn[t][arm], nat["per_task"][t]["D_nat"][arm])
pa = sum(Dn[t]["a"] for t in X)
check("natural pooled F_prompt", sum(Dn[t]["c"] for t in X) / pa, nat["pooled"]["F_prompt_nat"])
check("natural pooled F_direct", sum(Dn[t]["d"] for t in X) / pa, nat["pooled"]["F_direct_nat"])

# ---------------------------------------------------------------- 4. C5 combined rho + permutation test (scipy loop)
c5 = json.loads((ROOT / "results/c5.json").read_text())
cw = pd.DataFrame(c5["wordings"])
cw["cell"] = cw["exp"] + "|" + cw["task"]


def combined(df: pd.DataFrame, col: str = "banned_share") -> float:
    num = den = 0.0
    for _, g in df.groupby("cell"):
        if len(g) > 3 and g[col].std() > 0 and g["pi"].std() > 0:
            r = stats.spearmanr(g["pi"], g[col]).statistic
            num += (len(g) - 3) * np.arctanh(np.clip(r, -0.999999, 0.999999))
            den += len(g) - 3
    return float(np.tanh(num / den))


def perm_p(df: pd.DataFrame, n: int = 2000) -> float:
    obs = combined(df)
    null = []
    for _ in range(n):
        d2 = df.copy()
        d2["perm"] = d2.groupby("cell")["banned_share"].transform(lambda s: rng.permutation(s.values))
        null.append(combined(d2, "perm"))
    return float((1 + np.sum(np.array(null) <= obs)) / (1 + n))


rho = combined(cw)
check("C5 combined rho", rho, c5["shared_ban_direction"]["test"]["rho"])
p_real = perm_p(cw)
rej = []
for _ in range(40):
    d2 = cw.copy()
    d2["banned_share"] = d2.groupby("cell")["banned_share"].transform(lambda s: rng.permutation(s.values))
    rej.append(perm_p(d2, n=300) < 0.05)
out["placebo_tests"].append({"test": "C5 stratified permutation test, real vs within-cell shuffled banned shares",
                             "real_rho": rho, "real_p_independent": p_real,
                             "reported_p": c5["shared_ban_direction"]["test"]["p_one_sided"],
                             "shuffled_rejection_rate_at_0.05": float(np.mean(rej)),
                             "fails_on_placebo": bool(np.mean(rej) <= 0.15)})

out["n_checks"] = len(out["checks"])
out["n_mismatches"] = sum(not c["match"] for c in out["checks"])
out["all_placebos_fail"] = all(v for p in out["placebo_tests"] for k, v in p.items() if k.startswith("fails_on"))
(ROOT / "results/headline_audit.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: out[k] for k in ("n_checks", "n_mismatches", "all_placebos_fail")}))
for c in out["checks"]:
    if not c["match"]:
        print("MISMATCH", c)
for p in out["placebo_tests"]:
    print(p)
