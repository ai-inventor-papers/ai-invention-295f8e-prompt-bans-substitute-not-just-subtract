"""Recompute the PCA coordinates behind iteration 6's Gemma geometry figures (art_zNyBP6zieI5u src/figures_S.py:geometry),
so the report can draw them from numbers. Read-only on the artifact; writes work/geom/gemma_geom.json."""
import json, sys
from pathlib import Path
import numpy as np
import torch
from sklearn.decomposition import PCA

ART = Path(__file__).resolve().parents[4] / "round-6/experiment-31/src"
OUT = Path(__file__).with_name("gemma_geom.json")
V = torch.load(ART / "cache/states/variants.pt", map_location="cpu", weights_only=False)
C = torch.load(ART / "cache/states/contrast.pt", map_location="cpu", weights_only=False)
pts, kinds, modes, yv = [], [], [], []
for c in C:
    g = c["group"]
    if g.startswith("forced_"):
        pts.append(c); kinds.append("forced"); modes.append(g[len("forced_"):]); yv.append(None)
    elif g in ("ban_bfs", "ban_dfs", "top5", "top5_twin"):
        pts.append(c); kinds.append(g); modes.append(None); yv.append(None)
for v in V:
    pts.append(v); kinds.append("variant"); modes.append(None); yv.append(float(v["y"]))
res = {"n_points": len(pts), "kinds": kinds, "modes": modes, "yv": yv, "spaces": {}}
for space in ("raw", "sae"):
    for l in (17, 22):
        if space == "raw":
            X = np.stack([p["spec_mean"][l].float().numpy() for p in pts])
            massive = np.argsort(-np.abs(X).mean(0))[:5]
            X[:, massive] = 0.0
        else:
            X = np.log1p(np.stack([p["codes_spec_mean"][l].float().numpy() for p in pts]).clip(min=0))
        pca = PCA(n_components=10, random_state=0).fit(X)
        Z = pca.transform(X)[:, :2]
        res["spaces"][f"{space}|L{l}"] = {"var": pca.explained_variance_ratio_[:2].tolist(), "xy": Z.round(4).tolist()}
        print(space, l, pca.explained_variance_ratio_[:2], flush=True)
OUT.write_text(json.dumps(res))
print("done", len(pts))
