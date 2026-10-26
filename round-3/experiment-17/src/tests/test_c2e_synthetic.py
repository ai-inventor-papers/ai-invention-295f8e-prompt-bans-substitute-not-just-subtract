"""T4: decoder pipeline on simulated data. (a) a class signal planted in the state is decoded (BA high, above the
layer-max permutation null); (b) a template-only signal (class rate differs by template, state encodes only the
template) does NOT exceed the within-template permutation null; (c) Tc equals the Bayes rule on a toy prefix tree;
(d) the batched IRLS matches sklearn's LogisticRegression on one fit."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np, torch
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from analysis.c2e import (fold_features, decode, inner_masks, within_template_perms, ba_t, tc_prefix_ba, irls,
                          bal_weights, DEV, DT)
rng = np.random.default_rng(0)
N, D, G = 150, 512, 3
g = np.array([f"W{i % 5 + 1}" for i in range(N)])
res = {}
def run(X, y, g, n_perm=60):
    strata = np.array([f"{a}|{b}" for a, b in zip(g, y)])
    skf = StratifiedKFold(5, shuffle=True, random_state=0)
    outer = []
    for tr, _ in skf.split(np.zeros(len(y)), strata if min(np.unique(strata, return_counts=True)[1]) >= 5 else y):
        m = np.zeros(len(y), bool); m[tr] = True; outer.append(m)
    inner = [inner_masks(y, strata, m, 1 + i) for i, m in enumerate(outer)]
    perms = within_template_perms(y, g, n_perm, 100)
    Yb = torch.as_tensor(np.concatenate([y[None], perms]), device=DEV, dtype=DT)
    Z = fold_features(torch.as_tensor(X, device=DEV, dtype=DT), outer)
    P = decode(Z, Yb, outer, inner, chunk=20)
    ba = ba_t(Yb[None].expand_as(P), P)
    obs = ba[:, 0].cpu().numpy(); lmax = ba[:, 1:].max(0).values.cpu().numpy()
    return float(obs.max()), float(np.quantile(lmax, 0.95))
t0 = time.time()
# (a) planted class signal in block 1 only
y = (rng.random(N) < 0.3).astype(int)
X = rng.standard_normal((G, N, D)).astype(np.float32)
X[1] += 0.6 * y[:, None] * rng.standard_normal(D)[None].astype(np.float32)
res["a_planted"] = run(X, y, g)
# (b) template-only signal: class rate depends on template, the state encodes only the template
rate = {"W1": 0.1, "W2": 0.2, "W3": 0.5, "W4": 0.7, "W5": 0.9}
y2 = np.array([int(rng.random() < rate[w]) for w in g])
X2 = rng.standard_normal((G, N, D)).astype(np.float32)
tv = {w: rng.standard_normal(D).astype(np.float32) for w in rate}
for i, w in enumerate(g):
    X2[:, i] += 1.5 * tv[w]
res["b_template_only"] = run(X2, y2, g)
# (c) Tc on a toy prefix tree: identical prefixes within a template -> LOO majority of the same prefix
tok = [[1, 2, 3] if i % 2 == 0 else [1, 2, 4] for i in range(40)]
yc = np.array([1 if t[2] == 3 else 0 for t in tok])
gc_ = np.array(["W1"] * 40)
res["c_tc_k3"] = tc_prefix_ba(tok, yc, gc_, 3)   # Bayes rule decodes perfectly at k=3
res["c_tc_k2"] = tc_prefix_ba(tok, yc, gc_, 2)   # prefixes identical at k=2 -> template majority (chance)
# (d) IRLS vs sklearn on one fit (balanced weights, C=0.1)
Xs = rng.standard_normal((120, 10)); ys = (Xs[:, 0] + 0.5 * rng.standard_normal(120) > 0.3).astype(int)
Z1 = torch.as_tensor(np.concatenate([Xs, np.ones((120, 1))], 1), device=DEV, dtype=DT)
Y1 = torch.as_tensor(ys, device=DEV, dtype=DT); M = torch.ones(120, device=DEV, dtype=DT)
b = irls(Z1, Y1, bal_weights(Y1, M), torch.tensor(10.0, device=DEV)).cpu().numpy()
sk = LogisticRegression(C=0.1, class_weight="balanced", max_iter=5000, tol=1e-10).fit(Xs, ys)
res["d_irls_vs_sklearn_max_abs_coef_diff"] = float(np.abs(b[:-1] - sk.coef_[0]).max())
res["d_intercept_diff"] = float(abs(b[-1] - sk.intercept_[0]))
res["pass"] = (res["a_planted"][0] > res["a_planted"][1] and res["a_planted"][0] > 0.75
               and res["b_template_only"][0] <= res["b_template_only"][1] + 0.02
               and res["c_tc_k3"] == 1.0 and res["d_irls_vs_sklearn_max_abs_coef_diff"] < 1e-2)
res["seconds"] = time.time() - t0
print(res)
import json; Path(__file__).resolve().parents[1].joinpath("results", "test_c2e_synthetic.json").write_text(json.dumps(res, indent=1))
