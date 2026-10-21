#!/usr/bin/env python3
"""EXPLORATORY (outside the committed rules; written after the population was sampled): where along depth does the
realised push displacement start to predict which random pushes move the algorithm?

For each movable task, block l (12-35) and population direction u (alpha 1 and 2 averaged over templates), from the
prefill-only realised S-mean displacements delta_l (states/disp_<task>.npz):
  proj_r(l)   = <delta_l, r_l> / D_r,l       (signed progress toward the runner-up centroid, units of the distance)
  proj_a(l)   = <delta_l, a_l> / ||delta_l|| (signed alignment with the mean non-default axis)
  pi(l)       = ||Q_l^T delta_l||^2 / ||delta_l||^2
  norm(l)     = ||delta_l||
and Spearman of each with y (the committed C2a outcome). Also at R (the last prompt position): the R-position
displacement projected on the R-centroid runner-up axis. Permutation p (2,000 shuffles) per block; no multiplicity
correction (descriptive profile).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from cfg4 import CAP_BLOCKS, DEFAULT4, MOVABLE, SEEDS_POP, STATES_DIR, TEMPLATE_IDS
from common import perm_spearman
import npz_parts


def run(rows, commit: dict[str, Any], esc: dict[str, Any]) -> dict[str, Any]:
    import json
    from cfg4 import RESULTS_DIR
    c2a = json.loads((RESULTS_DIR / "c2a.json").read_text())
    out: dict[str, Any] = {"note": "EXPLORATORY: not committed before sampling", "tasks": {}}
    for t in MOVABLE:
        if t not in c2a.get("per_task", {}):
            continue
        y = np.array(c2a["per_task"][t]["y"])
        zf = npz_parts.load(STATES_DIR / f"disp_{t}.npz")
        z = {"delta": zf["delta"], "deltaR": zf["deltaR"], "keys": zf["keys"]}
        keys = [str(k) for k in z["keys"]]
        ix = {k: i for i, k in enumerate(keys)}
        sub = np.load(STATES_DIR / f"subspace_{t}.npz")
        Q, r_ax, a_ax, Dr = sub["Q"].astype(np.float64), sub["r"].astype(np.float64), sub["a"].astype(np.float64), \
            sub["D_r"]
        st = npz_parts.load(STATES_DIR / f"states_{t}.npz")
        modes = [str(m) for m in sub["modes"]]
        d = DEFAULT4[t]
        ru = commit["tasks"][t]["runner_up"]["runner_up"]
        from prompts4 import load_prompts4
        pm = load_prompts4()
        pids = [str(p) for p in st["pids"]]
        R = st["R"].astype(np.float32)
        named = {m: [i for i, p in enumerate(pids) if pm[p]["kind"] == "named" and pm[p]["X"] == m] for m in modes}
        cR = {m: R[ii].mean(0) for m, ii in named.items()}
        prof: dict[str, list[float]] = {"proj_r": [], "proj_a": [], "pi": [], "norm": [], "proj_r_p": [],
                                        "proj_a_p": [], "pi_p": [], "norm_p": []}
        feats_R = []
        for bi, l in enumerate(CAP_BLOCKS):
            fr, fa, fp, fn = [], [], [], []
            for s in SEEDS_POP:
                vr, va, vp, vn = [], [], [], []
                for a in ("1.0", "2.0"):
                    for w in TEMPLATE_IDS:
                        dl = z["delta"][ix[f"POP|{s}|{a}|{w}"]][bi].astype(np.float64)
                        nrm = np.linalg.norm(dl)
                        vr.append(dl @ r_ax[bi] / Dr[bi])
                        va.append(dl @ a_ax[bi] / max(nrm, 1e-9))
                        vp.append(float(np.sum((Q[bi].T @ dl) ** 2) / max(nrm ** 2, 1e-30)))
                        vn.append(nrm)
                fr.append(np.mean(vr))
                fa.append(np.mean(va))
                fp.append(np.mean(vp))
                fn.append(np.mean(vn))
            for nm, x in (("proj_r", fr), ("proj_a", fa), ("pi", fp), ("norm", fn)):
                r = perm_spearman(np.array(x), y, n_perm=2000, seed=bi)
                prof[nm].append(r["rho"])
                prof[nm + "_p"].append(r["p"])
        # R position: runner-up axis from R-state centroids at each block
        rR = []
        for bi, l in enumerate(CAP_BLOCKS):
            ax = cR[ru][bi] - cR[d][bi]
            DR = np.linalg.norm(ax)
            ax = ax / max(DR, 1e-9)
            x = []
            for s in SEEDS_POP:
                v = [z["deltaR"][ix[f"POP|{s}|{a}|{w}"]][bi].astype(np.float64) @ ax / DR
                     for a in ("1.0", "2.0") for w in TEMPLATE_IDS]
                x.append(np.mean(v))
            rR.append(perm_spearman(np.array(x), y, n_perm=2000, seed=100 + bi)["rho"])
        # N = 30 at alpha 2 for every direction (only when the exploratory top-up extension ran)
        tab = c2a["per_task"][t]["direction_table"]
        n30 = [tab[str(s)]["2.0"]["pooled"]["n_valid"] for s in SEEDS_POP]
        y30 = None
        if min(n30) >= 25:
            y30 = np.array([tab[str(s)]["2.0"]["pooled"]["share"] for s in SEEDS_POP])
            pr = commit["predictors"][t]
            out_n30 = {nm: perm_spearman(np.array([pr[str(s)][nm] for s in SEEDS_POP]), y30, n_perm=10000, seed=5)
                       for nm in ("pi", "pi_masked", "s", "s_runner_up", "pi_real_a2.0", "gain_a2.0") if nm in pr[str(SEEDS_POP[0])]}
            out_n30["proj_r_by_block"] = []
            for bi, l in enumerate(CAP_BLOCKS):
                x = [np.mean([z["delta"][ix[f"POP|{s}|2.0|{w}"]][bi].astype(np.float64) @ r_ax[bi] / Dr[bi]
                              for w in TEMPLATE_IDS]) for s in SEEDS_POP]
                out_n30["proj_r_by_block"].append(perm_spearman(np.array(x), y30, n_perm=2000, seed=200 + bi)["rho"])
        else:
            out_n30 = {"note": f"not all directions topped up at alpha 2 (min N = {min(n30)})"}
        out["tasks"].setdefault(t, {})
        out["tasks"][t]["alpha2_N30"] = out_n30
        # reliability of the outcome itself: is a direction's effect a stable property of the direction?
        ya1 = np.array([tab[str(s)]["1.0"]["first10"]["share"] for s in SEEDS_POP])
        ya2 = np.array([tab[str(s)]["2.0"]["first10"]["share"] for s in SEEDS_POP])
        rel_alpha = perm_spearman(ya1, ya2, n_perm=5000, seed=11)
        from cfg4 import DEFAULT4 as _D
        from screen import catalogue as _cat
        cat_t = set(_cat(t))
        by = {}
        for r in rows:
            if r["task"] == t and r["family"] == "POP" and int(r["sample_id"]) in (0, 1) and r["label"] not in ("invalid", "disputed"):
                by.setdefault((r["direction_seed"], r["template"] in ("W1", "W3", "W5")), []).append(
                    int(r["label"] in cat_t and r["label"] != _D[t]))
        hA = np.array([np.mean(by.get((s, True), [np.nan])) for s in SEEDS_POP])
        hB = np.array([np.mean(by.get((s, False), [np.nan])) for s in SEEDS_POP])
        ok_ = np.isfinite(hA) & np.isfinite(hB)
        rel_half = perm_spearman(hA[ok_], hB[ok_], n_perm=5000, seed=12)
        sb = (2 * rel_half["rho"] / (1 + rel_half["rho"])) if rel_half["rho"] > -1 else None
        out["tasks"][t]["y_reliability"] = {"rho_alpha1_vs_alpha2": rel_alpha["rho"], "p_alpha": rel_alpha["p"],
                                            "rho_template_halves": rel_half["rho"], "p_halves": rel_half["p"],
                                            "spearman_brown_full_length": sb}
        out["tasks"][t].update({"blocks": CAP_BLOCKS, "profile": prof, "R_proj_runner_up_rho": rR, "runner_up": ru,
                           "max_rho_proj_r": float(np.max(prof["proj_r"])),
                           "argmax_block_proj_r": int(CAP_BLOCKS[int(np.argmax(prof["proj_r"]))])})
    return out
