#!/usr/bin/env python3
"""Adds leave-one-out nearest-class predictions on F0 for the accepted top-up programs to method_out.json
(predict_nearest_class_F0_<model>, predict_class_F0_<model> vs the F0 non-banned median)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402

import analysis_g2 as A  # noqa: E402
import geometry  # noqa: E402
import run_analysis as RA  # noqa: E402
from tpg2 import K_PRIMARY, ROOT  # noqa: E402

B5 = ["bfs", "dfs", "iddfs", "astar", "gbfs"]
NB5 = ["dijkstra_unit", "idastar", "bibfs", "jps", "biastar"]

if __name__ == "__main__":
    mo = json.loads((ROOT / "method_out.json").read_text())
    ds = next(d for d in mo["datasets"] if d["dataset"] == "tpg2_topups")
    for tag in ("8b", "32b"):
        D = RA.load_all(tag)
        F0 = RA.build_frames(D)["F0"]
        idx = {u: i for i, u in enumerate(F0["ids"])}
        for ex in ds["examples"]:
            u = ex["metadata_uid"]
            if u not in idx:
                x = RA.X_new(D, [u])[0]
                X, lab = F0["X"], F0["alg"]
            else:
                i = idx[u]
                keep = np.ones(len(F0["X"]), bool)
                keep[i] = False
                x, X, lab = F0["X"][i], F0["X"][keep], F0["alg"][keep]
            geo, _ = geometry.geodesics(X, K_PRIMARY)
            dv = A.oos(x, X, geo, K_PRIMARY)
            means = {a: float(dv[lab == a].mean()) for a in sorted(set(lab.tolist()))}
            B = [b for b in B5 if b in means]
            NB = [a for a in NB5 if a in means and (lab == a).sum() >= 10]
            g, _ = geometry.g_values(geo, lab, B, NB)
            _, med = geometry.classify(g)
            ex[f"predict_nearest_class_F0_{tag}"] = min(means, key=means.get)
            ex[f"predict_class_F0_{tag}"] = A.class_of(min(means[b] for b in B), med)
    acc = {t: float(np.mean([ex[f"predict_nearest_class_F0_{t}"] == ex["output"] for ex in ds["examples"]])) for t in ("8b", "32b")}
    mo["metadata"]["topup_loo_nearest_class_accuracy"] = acc
    (ROOT / "method_out.json").write_text(json.dumps(mo, indent=1, default=str))
    print(acc)
