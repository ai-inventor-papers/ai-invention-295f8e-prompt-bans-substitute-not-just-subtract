#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers through DIFFERENT code paths than src/analysis_S.py, each with a
placebo that must fail. Reads raw files only (cache/states/variants.pt, data/*.jsonl, results/logit_sweep.jsonl).

H1 readout: leave-one-noun-out R2 of y_v from SAE codes (FORK, layer 29) with a numpy closed-form ridge (not the
   sklearn Lasso of the main analysis) vs a template+noun-norm control; placebo = y permuted within template.
H2 sampling validation: Spearman(y_v, logit BFS share) with hand-written average ranks; placebo = shuffled y.
H3 dose-response at the fork (layer 22): mean dy of FEAT-input k20/k50 lam 1 vs DiM / RANDF / ISO at matched norm,
   recomputed row by row from results/logit_sweep.jsonl; placebo = ISO (isotropic) must be ~0.
H4 TOP5 vs its twin: BFS indicators per CRN slot from data/labels.jsonl, exact McNemar by direct binomial sum;
   placebo = the TOP5 twin against itself with slots shuffled within template (must not be significant).
Usage: .venv/bin/python audit/rederive_headlines.py   (from the artifact root)
"""
import json
import math
import random
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]


def jl(p):
    return [json.loads(x) for x in (ROOT / p).read_text().splitlines() if x.strip()]


def ranks(x):
    o = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and x[o[j + 1]] == x[o[i]]:
            j += 1
        for k in range(i, j + 1):
            r[o[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = ranks(a), ranks(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    return num / math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))


def ridge_lono(X, y, groups, alpha):
    pred = np.zeros_like(y)
    for g in sorted(set(groups)):
        te = np.array([gg == g for gg in groups])
        Xtr, ytr = X[~te], y[~te]
        mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-6
        A = (Xtr - mu) / sd
        w = np.linalg.solve(A.T @ A + alpha * np.eye(A.shape[1]), A.T @ (ytr - ytr.mean()))
        pred[te] = ((X[te] - mu) / sd) @ w + ytr.mean()
    return 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()


def binom_two_sided(a, b):
    n = a + b
    if n == 0:
        return 1.0
    k = min(a, b)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def main():
    out = {}
    # ---------------- H1
    V = torch.load(ROOT / "cache" / "states" / "variants.pt")
    y = np.array([v["y"] for v in V])
    tpl = [v["template"] for v in V]
    noun = [v["noun"] for v in V]
    T = np.array([[1.0 if t == w else 0.0 for w in ("W1", "W2", "W3", "W4", "W5")] for t in tpl])
    F = np.stack([v["codes_fork"][29].float().numpy() for v in V])
    F = np.log1p(np.maximum(F, 0))
    F = F[:, (F > 0).sum(0) >= 2]
    cand = {c["word"]: c for c in json.loads((ROOT / "inputs" / "dep_extract" / "noun_candidates.json").read_text())}
    lex = np.array([[float((cand.get(n) or {}).get("concreteness") or 0), math.log1p(float((cand.get(n) or {}).get("subtlex") or 0))]
                    for n in noun])
    r2_sae = ridge_lono(np.hstack([F, T]), y, noun, alpha=float(F.shape[1]))
    r2_ctl = ridge_lono(np.hstack([lex, T]), y, noun, alpha=1.0)
    rng = np.random.default_rng(11)
    plac = []
    for _ in range(20):
        yp = y.copy()
        for w in set(tpl):
            idx = [i for i, t in enumerate(tpl) if t == w]
            yp[idx] = rng.permutation(yp[idx])
        plac.append(ridge_lono(np.hstack([F, T]), yp, noun, alpha=float(F.shape[1])) -
                    ridge_lono(np.hstack([lex, T]), yp, noun, alpha=1.0))
    out["H1_readout"] = {"y_sd": float(y.std(ddof=1)), "y_mean": float(y.mean()), "R2_lono_ridge_SAE_FORK29": float(r2_sae),
                         "R2_lono_ridge_template_nounnorms": float(r2_ctl), "delta": float(r2_sae - r2_ctl),
                         "placebo_within_template_permuted_delta_mean": float(np.mean(plac)),
                         "placebo_max": float(np.max(plac)), "placebo_fails": bool(np.max(plac) < r2_sae - r2_ctl)}
    # ---------------- H2
    rows = jl("data/sampling_validation_labels.jsonl")
    by = {}
    for r in rows:
        by.setdefault((r["template"], r["noun"]), []).append(r)
    ys, ls = [], []
    for rr in by.values():
        k = sum(r["cls"] == "bfs" for r in rr)
        ys.append(rr[0]["y"])
        ls.append(math.log((k + 0.5) / (len(rr) - k + 0.5)))
    rho = spearman(ys, ls)
    rnd = random.Random(5)
    pl = []
    for _ in range(200):
        yy = ys[:]
        rnd.shuffle(yy)
        pl.append(spearman(yy, ls))
    out["H2_sampling_validation"] = {"n_variants": len(ys), "spearman": rho, "placebo_mean": float(np.mean(pl)),
                                     "placebo_p95": float(np.quantile(pl, 0.95)), "placebo_fails": bool(np.quantile(pl, 0.95) < rho)}
    # ---------------- H3
    sw = jl("results/logit_sweep.jsonl")
    h3 = {}
    for kind, src in (("FEAT", "input"), ("DiM", "input"), ("RANDF", "input"), ("ISO", "input"), ("FEAT", "output")):
        for k in (20, 50):
            v = [r["dy"] for r in sw if r["site"] == "FORK" and r["layer"] == 22 and r["kind"] == kind and r["src"] == src
                 and r["k"] == k and r["lam"] == 1.0 and r["dy"] is not None]
            h3[f"{kind}|{src}|k{k}"] = {"n": len(v), "mean_dy": float(np.mean(v)) if v else None}
    h3["placebo_ISO_near_zero"] = bool(abs(h3["ISO|input|k20"]["mean_dy"]) < 0.3)
    h3["DiM_over_FEAT_k20"] = h3["DiM|input|k20"]["mean_dy"] / h3["FEAT|input|k20"]["mean_dy"]
    out["H3_dose_response_FORK_L22"] = h3
    # ---------------- H4
    lab = {r["row_id"]: r for r in jl("data/labels.jsonl")}
    def ind(arm):
        d = {}
        for r in jl("data/raw_contrast.jsonl"):
            if r.get("arm") == arm and r["row_id"] in lab:
                d[(r["template"], r["slot"])] = 1 if lab[r["row_id"]]["label"] == "bfs" else 0
        return d
    a, b = ind("top5"), ind("top5_twin")
    keys = sorted(set(a) & set(b))
    n10 = sum(1 for k in keys if a[k] and not b[k])
    n01 = sum(1 for k in keys if b[k] and not a[k])
    sh = {}
    for w in set(k[0] for k in keys):
        ks = [k for k in keys if k[0] == w]
        vals = [b[k] for k in ks]
        random.Random(3).shuffle(vals)
        sh.update(dict(zip(ks, vals)))
    p10 = sum(1 for k in keys if sh[k] and not b[k])
    p01 = sum(1 for k in keys if b[k] and not sh[k])
    out["H4_top5_vs_twin"] = {"n_pairs": len(keys), "top5_bfs": sum(a[k] for k in keys), "twin_bfs": sum(b[k] for k in keys),
                              "a_only": n10, "b_only": n01, "p": binom_two_sided(n10, n01),
                              "placebo_twin_vs_shuffled_twin_p": binom_two_sided(p10, p01),
                              "placebo_fails": binom_two_sided(p10, p01) > 0.05}
    (ROOT / "results" / "rederive_headlines.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
