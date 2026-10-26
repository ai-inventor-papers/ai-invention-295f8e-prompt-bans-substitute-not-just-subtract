"""T3: leave-one-task-out direction maths on the saved S2 arrays: vraw[t] equals the mean over the 13 other tasks of
their task-mean displacement (blocks 12-23); perturbing the held-out task's displacement leaves v[t] unchanged while
perturbing another task changes it; vhat is the unit-normalised vraw; norms are per (block, position)."""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from cfg import ALL_TASKS, SAMPLED_TASKS, SAVE_BLOCKS, V_BLOCKS
D = np.load(ROOT / "directions" / "task_dbar.npz")
vb = [SAVE_BLOCKS.index(l) for l in V_BLOCKS]
res = {}
for t in SAMPLED_TASKS:
    vraw = np.load(ROOT / "directions" / f"vraw_{t}.npy")
    vhat = np.load(ROOT / "directions" / f"v_{t}.npy")
    others = [u for u in ALL_TASKS if u != t]
    rec = np.mean([D[u][vb] for u in others], axis=0)
    pert = {u: D[u][vb] + (100.0 if u == t else 0.0) for u in ALL_TASKS}
    rec_pert_self = np.mean([pert[u] for u in others], axis=0)
    other = others[0]
    pert2 = {u: D[u][vb] + (100.0 if u == other else 0.0) for u in ALL_TASKS}
    rec_pert_other = np.mean([pert2[u] for u in others], axis=0)
    norms = np.load(ROOT / "directions" / f"norms_{t}.npy")
    res[t] = {"max_abs_err_vraw": float(np.abs(rec - vraw).max()),
              "unit_ok": bool(np.allclose(np.linalg.norm(vhat, axis=1), 1, atol=1e-5)),
              "vhat_matches_vraw": bool(np.allclose(vhat, vraw / np.linalg.norm(vraw, axis=1, keepdims=True), atol=1e-5)),
              "held_out_perturbation_changes_v": bool(not np.allclose(rec_pert_self, rec)),
              "other_task_perturbation_changes_v": bool(not np.allclose(rec_pert_other, rec)),
              "norms_shape": list(norms.shape)}
ok = all(r["max_abs_err_vraw"] < 1e-3 and r["unit_ok"] and r["vhat_matches_vraw"]
         and not r["held_out_perturbation_changes_v"] and r["other_task_perturbation_changes_v"] for r in res.values())
out = {"per_task": res, "pass": ok}
(ROOT / "results" / "test_direction_maths.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out)[:800])
