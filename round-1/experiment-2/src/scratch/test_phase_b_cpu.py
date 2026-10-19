import sys, json, time
import numpy as np
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
for d in ("", "gen", "analysis", "hf"): sys.path.insert(0, str(ROOT / d))
import phase_b as pb
from geometry import knn_graph, geodesic_between, pca95, attach, twonn_id
rng = np.random.default_rng(0)
cat = ["bfs","dfs","bidir_bfs","iddfs","astar","dijkstra_unit"]
D = 256
cent = rng.standard_normal((6, D)) * 3
index, Hl = [], []
for k, m in enumerate(cat):
    for f in range(10):
        for v in range(3):
            index.append({"task": "t1", "condition": f"forced:{m}", "frame_id": f, "paraphrase_id": f*3+v})
            Hl.append(cent[k] + rng.standard_normal(D))
            index.append({"task": "t1", "condition": f"masked:{m}", "frame_id": f, "paraphrase_id": f*3+v})
            Hl.append(cent[k] + rng.standard_normal(D) * 1.5)
for p in range(10):
    index.append({"task": "t1", "condition": "baseline", "frame_id": p, "paraphrase_id": p}); Hl.append(cent[0] + rng.standard_normal(D))
H = {l: np.array(Hl, np.float32) for l in pb.CACHE_LAYERS}
iN = [i for i, r in enumerate(index) if r["condition"].startswith("forced:")]
iM = [i for i, r in enumerate(index) if r["condition"].startswith("masked:")]
iB = [i for i, r in enumerate(index) if r["condition"] == "baseline"]
yn = np.array([cat.index(index[i]["condition"].split(":")[1]) for i in iN]); gn = np.array([index[i]["frame_id"] for i in iN])
ym = np.array([cat.index(index[i]["condition"].split(":")[1]) for i in iM])
t0 = time.time()
res = pb._gate_one_layer(10, H[10][iN], yn, gn, H[10][iM], ym, H[10][iB], np.array([0.9,0.02,0.02,0.02,0.02,0.02]), 6, 1)
print("gate one layer", round(time.time()-t0,1), "s", {k: (round(v,3) if isinstance(v,float) else v) for k, v in res.items() if k != "decoder_dist"})
d, W = pb.direction(H, index, "t1", 10, "bfs")
print("dir norm", np.linalg.norm(d), "cos with true", float(d @ pb.unit(cent[0] - cent[1:].mean(0))))
C = pb.centroids(H, index, "t1", 10)
Xn = H[10][iN]; mu, comps, ev = pca95(Xn); P = (Xn - mu) @ comps.T
G, info = knn_graph(P, 10); Dc = geodesic_between(G, P, (C - mu) @ comps.T, 10)
print("graph", info, "pca dims", comps.shape, "Dc sym err", float(np.abs(Dc - Dc.T).max()), "diag", np.diag(Dc)[:3])
from scipy.spatial.distance import cdist
Pe = cdist((C - mu) @ comps.T, (C - mu) @ comps.T); print("geo>=eucl", bool((Dc + 1e-6 >= Pe).all()))
print("twonn", twonn_id(P))
