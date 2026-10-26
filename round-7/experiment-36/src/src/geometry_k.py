#!/usr/bin/env python3
"""E2 (exploratory, CPU only, not pre-registered): is the downstream displacement's DIRECTION, not its size, what
separates escapes? Uses the fp16 displacement vectors logged for every pushed row (cache/disp: spec-mean at blocks 23
and 35, read position R at block 35, generated position 1 at block 35) of the S1 designs, D5 and E1 on T10 and T2.

  (a) 5-fold CV AUC of the attempt indicator A from: the two log norms (S35, R35); the unit-normalised R35 direction;
      the unit-normalised gen-1 direction; the spec-mean-35 direction (PCA-32 inside each fold, then logistic).
  (b) transfer: an escape axis = difference of the mean unit-normalised R35 vectors of attempted and default rows of
      the U_abs designs (D1, D2; alpha 1-2); AUC of the projection on held-out U_abs rows (2-fold by template) and on
      every U_bf-family row (D3, D4, D5, E1) never used to build it.
  (c) per-design mean projection on the axis (figure F7: projection vs block-35 R norm, coloured by outcome).

usage: .venv/bin/python src/geometry_k.py
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

import k_cfg as K  # noqa: E402
from k_cfg import FIGS, RESULTS, write_json  # noqa: E402


def load_vectors() -> dict[str, dict[str, np.ndarray]]:
    vecs: dict[str, dict[str, np.ndarray]] = defaultdict(dict)
    for p in sorted((K.CACHE / "disp").glob("*.npz")):
        z = np.load(p)
        for k in z.files:
            key, kind = k.split("::")
            vecs[key][kind] = z[k].astype(np.float32)
    return vecs


def unit_rows(X: np.ndarray) -> np.ndarray:
    return X / np.maximum(np.linalg.norm(X, axis=1, keepdims=True), 1e-9)


def cv_auc(X: np.ndarray, y: np.ndarray, pca: int | None = 32) -> float | None:
    from sklearn.decomposition import PCA
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    if y.sum() < 5 or (len(y) - y.sum()) < 5:
        return None
    steps = [StandardScaler()]
    if pca:
        steps.append(PCA(n_components=min(pca, X.shape[1], len(y) // 3)))
    steps.append(LogisticRegression(C=0.1, max_iter=5000))
    pr = cross_val_predict(make_pipeline(*steps), X, y, cv=StratifiedKFold(5, shuffle=True, random_state=0),
                           method="predict_proba")[:, 1]
    return float(roc_auc_score(y, pr))


def auc(score: np.ndarray, y: np.ndarray) -> float | None:
    from sklearn.metrics import roc_auc_score
    if y.sum() == 0 or y.sum() == len(y):
        return None
    return float(roc_auc_score(y, score))


def slot_concordance() -> dict:
    """Per-slot concordance of outcomes across designs that share the slot's token stream (phi coefficient, joint
    count vs independence) and across doses with the same direction (D1 alpha 1 -> alpha 2)."""
    import analysis_k as A

    rows = A.load_joined()
    out: dict = {}

    def phi(a: np.ndarray, b: np.ndarray) -> float | None:
        if a.std() == 0 or b.std() == 0:
            return None
        return float(np.corrcoef(a, b)[0, 1])
    for task in ("T10", "T2"):
        for key in ("Y", "A"):
            slots, M = A.paired_matrix(rows, task, 2.0, ["D1", "D2", "D3", "D4"], key, A.COMMITTED_KS[(task, 2.0)])
            if len(slots) < 10:
                continue
            d1, d2, d3, d4 = M.T
            out[f"{task}|{key}|alpha2"] = {
                "n_slots": len(slots), "phi_D1_D2_same_stream_diff_u": phi(d1, d2),
                "joint_D1_D2": int(((d1 == 1) & (d2 == 1)).sum()),
                "joint_expected_if_independent": float(d1.mean() * d2.mean() * len(d1)),
                "phi_D1_D3_same_u_diff_unit": phi(d1, d3), "phi_D2_D4_same_u_diff_unit": phi(d2, d4)}
        c1, c2 = A.cell(rows, task, "D1_a1", K.K10), A.cell(rows, task, "D1_a2", K.K10)
        s_ = sorted(set(c1) & set(c2))
        a = np.array([c1[x]["A"] for x in s_])
        b = np.array([c2[x]["A"] for x in s_])
        out[f"{task}|A|D1_alpha1_to_alpha2_same_u_same_stream"] = {
            "n": len(s_), "P_escape_a2_given_escape_a1": float(b[a == 1].mean()) if a.sum() else None,
            "P_escape_a2_marginal": float(b.mean()), "n_escape_a1": int(a.sum())}
    return out


@logger.catch(reraise=True)
def main() -> None:
    import analysis_k as A

    K.setup_logging("geometry_k")
    rows = {r["key"]: r for r in A.load_joined() if r.get("labelled")}
    vecs = load_vectors()
    out: dict = {}
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    for ax, task in zip(axes, ("T10", "T2")):
        sel = [k for k in vecs if k in rows and rows[k]["task"] == task and rows[k]["design"] in
               ("D1", "D2", "D3", "D4", "D5") and all(f in vecs[k] for f in ("R35", "smean35", "gen1_35"))
               and rows[k]["k"] in A.COMMITTED_KS.get((task, rows[k]["alpha"]), list(range(10)))]
        if len(sel) < 40:
            continue
        y = np.array([rows[k]["A"] for k in sel])
        R = np.stack([vecs[k]["R35"] for k in sel])
        G = np.stack([vecs[k]["gen1_35"] for k in sel])
        S = np.stack([vecs[k]["smean35"] for k in sel])
        norms = np.column_stack([np.log(np.linalg.norm(S, axis=1)), np.log(np.linalg.norm(R, axis=1))])
        res = {"n": len(sel), "n_attempted": int(y.sum()),
               "cv_auc_log_norms": cv_auc(norms, y, pca=None),
               "cv_auc_R35_direction": cv_auc(unit_rows(R), y),
               "cv_auc_gen1_direction": cv_auc(unit_rows(G), y),
               "cv_auc_specmean35_direction": cv_auc(unit_rows(S), y)}
        # (b) escape axis built on U_abs rows only (alpha 1-2), 2-fold by template for its own AUC
        des = np.array([rows[k]["design"] for k in sel])
        alp = np.array([rows[k]["alpha"] for k in sel])
        # (a') the same comparison at a FIXED unit family and dose (alpha 2), so dose cannot drive the norm AUC
        strata = {}
        for name, m in (("U_abs_alpha2 (D1+D2)", np.isin(des, ("D1", "D2")) & (alp == 2.0)),
                        ("U_bf_family_alpha2 (D3+D4+D5)", np.isin(des, ("D3", "D4", "D5")) & (alp == 2.0))):
            if m.sum() >= 40:
                strata[name] = {"n": int(m.sum()), "n_attempted": int(y[m].sum()),
                                "cv_auc_log_norms": cv_auc(norms[m], y[m], pca=None),
                                "cv_auc_R35_direction": cv_auc(unit_rows(R[m]), y[m], pca=16),
                                "cv_auc_gen1_direction": cv_auc(unit_rows(G[m]), y[m], pca=16)}
        res["fixed_dose_strata"] = strata
        tmpl = np.array([rows[k]["template"] for k in sel])
        Ru = unit_rows(R)
        absm = np.isin(des, ("D1", "D2")) & np.isin(alp, (1.0, 2.0))
        own = np.zeros(len(sel))
        for fold in (("W1", "W2"), ("W3", "W4", "W5")):
            tr = absm & ~np.isin(tmpl, fold)
            te = absm & np.isin(tmpl, fold)
            ax_ = Ru[tr & (y == 1)].mean(0) - Ru[tr & (y == 0)].mean(0)
            own[te] = Ru[te] @ (ax_ / np.linalg.norm(ax_))
        axis = Ru[absm & (y == 1)].mean(0) - Ru[absm & (y == 0)].mean(0)
        axis /= np.linalg.norm(axis)
        proj = Ru @ axis
        bfm = np.isin(des, ("D3", "D4", "D5"))
        res["escape_axis"] = {"built_on": "U_abs designs D1, D2 at alpha 1-2 (attempted vs default)",
                              "auc_heldout_templates_U_abs": auc(own[absm], y[absm]),
                              "auc_transfer_to_U_bf_family": auc(proj[bfm], y[bfm]),
                              "mean_projection_by_design_alpha": {
                                  f"{d}_a{a:g}": float(proj[(des == d) & (alp == a)].mean())
                                  for d in ("D1", "D2", "D3", "D4", "D5") for a in sorted(set(alp))
                                  if ((des == d) & (alp == a)).any()},
                              "mean_projection_attempted_vs_default_U_bf": [
                                  float(proj[bfm & (y == 1)].mean()) if (bfm & (y == 1)).any() else None,
                                  float(proj[bfm & (y == 0)].mean()) if (bfm & (y == 0)).any() else None]}
        out[task] = res
        rn = np.linalg.norm(R, axis=1)
        for d, mk in (("D1", "o"), ("D2", "s"), ("D3", "^"), ("D4", "v"), ("D5", "D")):
            for yy, c in ((0, "#9a9a9a"), (1, "#1b6ca8" if d in ("D1", "D2") else "#d1495b")):
                m = (des == d) & (y == yy)
                if m.any():
                    ax.scatter(rn[m], proj[m], marker=mk, s=14, color=c, alpha=0.7, edgecolor="none",
                               label=f"{d} {'attempted' if yy else 'default'}")
        ax.set_xscale("log")
        ax.set_xlabel("||delta h|| at block 35, read position (log)")
        ax.set_ylabel("projection of unit delta h on the U_abs escape axis")
        ax.set_title(f"{task}: axis AUC held-out {res['escape_axis']['auc_heldout_templates_U_abs']:.2f}, "
                     f"transfer to U_bf {res['escape_axis']['auc_transfer_to_U_bf_family'] or float('nan'):.2f}")
        ax.legend(frameon=False, fontsize=6, ncol=2, loc="lower right")
    fig.suptitle("F7 (exploratory E2): projection on an escape axis built from U_abs rows vs the size of the downstream displacement",
                 y=1.02)
    fig.savefig(FIGS / "F7_escape_axis.pdf", bbox_inches="tight")
    fig.savefig(FIGS / "F7_escape_axis.png", bbox_inches="tight", dpi=170)
    plt.close(fig)
    out["slot_concordance"] = slot_concordance()
    write_json(RESULTS / "e2_geometry.json", out)
    logger.info({t: {k: v for k, v in r.items() if k not in ("escape_axis",)} for t, r in out.items()})
    logger.info({t: {k: v for k, v in r["escape_axis"].items() if k != "mean_projection_by_design_alpha"}
                 for t, r in out.items()})


if __name__ == "__main__":
    main()
