"""Recompute the per-task PCA coordinates behind iteration 6's NLA figure F6_geometry
(art_dbUtqBjT0tPf src/figures.py:f6_geometry): forced-mode centroids, twin and ban READ states per template.
Read-only on the artifact; writes work/geom/nla_geom.json."""
import json
from pathlib import Path
import numpy as np
ART = Path(__file__).resolve().parents[4] / "round-6/experiment-32/src"
idx = [json.loads(l) for l in open(ART / "cache/states_index.jsonl")]
z = np.load(ART / "cache/states_L20.npz")
conv = json.load(open(ART / "results/layer_convention.json"))["chosen"]
H = z["H20"] if conv == "hs20" else z["H21"]
beh = json.load(open(ART / "results/behaviour.json"))
out = {"convention": conv, "tasks": {}}
for t in ["T1", "T2", "T03", "T05", "T06", "T10", "T04", "R6"]:
    rows = [r for r in idx if r.get("task") == t and r["kind"] == "PREFILL" and r["position"] == "READ"]
    forced = [r for r in rows if r["condition"] == "forced"]
    if len(forced) < 3:
        continue
    F = H[[r["row"] for r in forced]].astype(np.float64)
    mu = F.mean(0)
    U, S, Vt = np.linalg.svd(F - mu, full_matrices=False)
    pcs = Vt[:2]; ve = (S[:2] ** 2) / (S ** 2).sum()
    proj = lambda X: ((np.atleast_2d(X).astype(np.float64) - mu) @ pcs.T)
    res = {"var": ve.round(4).tolist(), "centroids": {}, "twin": {}, "ban": {}, "seed": [], "adherence": {}}
    for m in sorted({r["mode"] for r in forced}):
        P = proj(H[[r["row"] for r in forced if r["mode"] == m]])
        res["centroids"][m] = P.mean(0).round(3).tolist()
        res["adherence"][m] = beh["tasks"][t]["forced"].get(m, {}).get("adherence")
    for r in rows:
        if r["condition"] in ("twin", "ban"):
            res[r["condition"]][r["template"]] = proj(H[r["row"]])[0].round(3).tolist()
        elif r["condition"] == "seed":
            res["seed"].append(proj(H[r["row"]])[0].round(3).tolist())
    out["tasks"][t] = res
Path(__file__).with_name("nla_geom.json").write_text(json.dumps(out, indent=1))
print("done", list(out["tasks"]))
