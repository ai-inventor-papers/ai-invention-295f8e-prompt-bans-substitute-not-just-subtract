"""Re-run src/subspace.py end to end on the SPLIT state files with every write captured in memory, and compare its
predictors and subspace arrays with the committed ones (predictions/c2_commit.json, states/subspace_*.npz)."""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import cfg4  # noqa: E402,F401
import subspace  # noqa: E402

cap = {}
subspace.np.savez = lambda path, **kw: cap.__setitem__(Path(path).name, kw)
subspace.write_json = lambda path, obj: cap.__setitem__(Path(path).name, obj)
rep = subspace.run_subspace()
committed = json.loads((ROOT / "predictions/c2_commit.json").read_text())["predictors"]
md = 0.0
n = 0
for t, d in rep["directions"].items():
    for s, p in d.items():
        for k, v in p.items():
            md = max(md, abs(v - committed[t][s][k]))
            n += 1
ad = 0.0
for name, arrs in cap.items():
    if name.startswith("subspace_") and name.endswith(".npz"):
        z = np.load(ROOT / "states" / name)
        for k, v in arrs.items():
            if np.issubdtype(np.asarray(v).dtype, np.number):
                ad = max(ad, float(np.max(np.abs(np.asarray(v, float) - z[k].astype(float)))))
print(json.dumps({"n_predictor_values": n, "max_abs_diff_predictors_vs_commit": md,
                  "max_abs_diff_subspace_arrays_vs_committed_files": ad,
                  "n_subspace_files_compared": sum(1 for k in cap if k.startswith("subspace_") and k.endswith(".npz"))}))
