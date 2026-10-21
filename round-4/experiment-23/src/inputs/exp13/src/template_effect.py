#!/usr/bin/env python3
"""Template (wording) effect on the banned share (frozen).

Per-template banned share per task with Wilson 95% intervals; pooled statsmodels BinomialBayesMixedGLM:
banned ~ task fixed effects + random template and template:task intercepts (variational Bayes; posterior SDs of the
variance components reported); fixed-effects logistic likelihood-ratio test of template (df = 4) as a check.
banned = 1 if an attempted program's label is the banned default D.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pandas as pd

from score import wilson


def frame(rows: list[dict], defaults: dict[str, str]) -> pd.DataFrame:
    recs = [{"task": r["task"], "template": r["template"], "banned": int(r["label"] == defaults[r["task"]])}
            for r in rows if r["label"] != "invalid"]
    return pd.DataFrame(recs)


def per_template(df: pd.DataFrame) -> dict[str, Any]:
    out = {}
    for (t, w), g in df.groupby(["task", "template"]):
        k, n = int(g["banned"].sum()), len(g)
        lo, hi = wilson(k, n)
        out.setdefault(t, {})[w] = {"k": k, "n": n, "share": k / n if n else None, "wilson95": [lo, hi]}
    return out


def lr_test(df: pd.DataFrame) -> dict[str, Any]:
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    from scipy import stats

    # tasks whose banned indicator is constant carry no information about templates (and separate perfectly)
    keep = df.groupby("task")["banned"].transform(lambda s: 0 < s.mean() < 1).astype(bool)
    d = df[keep]
    if d.empty or d["task"].nunique() < 1:
        return {"defined": False, "reason": "every task has a constant banned indicator"}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        f0 = smf.glm("banned ~ C(task)", d, family=sm.families.Binomial()).fit()
        f1 = smf.glm("banned ~ C(task) + C(template)", d, family=sm.families.Binomial()).fit()
    lr = 2 * (f1.llf - f0.llf)
    dfree = int(f1.df_model - f0.df_model)
    return {"defined": True, "LR": float(lr), "df": dfree, "p": float(stats.chi2.sf(lr, dfree)),
            "n_rows": int(len(d)), "tasks_used": sorted(d["task"].unique().tolist()),
            "tasks_dropped_constant": sorted(set(df["task"]) - set(d["task"]))}


def mixed(df: pd.DataFrame) -> dict[str, Any]:
    from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM

    if df["banned"].nunique() < 2:
        return {"defined": False, "reason": "constant outcome"}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = BinomialBayesMixedGLM.from_formula(
            "banned ~ C(task)", {"template": "0 + C(template)", "template_task": "0 + C(template):C(task)"}, df)
        res = model.fit_vb()
    names = list(model.vcp_names)
    return {"defined": True, "vc_names": names,
            "log_sd_posterior_mean": [float(x) for x in res.vcp_mean],
            "log_sd_posterior_sd": [float(x) for x in res.vcp_sd],
            "sd_point": [float(np.exp(x)) for x in res.vcp_mean],
            "sd_95": [[float(np.exp(m - 1.96 * s)), float(np.exp(m + 1.96 * s))] for m, s in zip(res.vcp_mean,
                                                                                                 res.vcp_sd)]}


def analyse(rows: list[dict], defaults: dict[str, str]) -> dict[str, Any]:
    df = frame(rows, defaults)
    out: dict[str, Any] = {"n_rows": int(len(df)), "per_template": per_template(df)}
    try:
        out["mixed_glm"] = mixed(df)
    except Exception as e:  # noqa: BLE001 - reported, never hidden
        out["mixed_glm"] = {"defined": False, "error": repr(e)[:300]}
    try:
        out["fixed_effects_lr"] = lr_test(df)
    except Exception as e:  # noqa: BLE001
        out["fixed_effects_lr"] = {"defined": False, "error": repr(e)[:300]}
    return out


def placebo(rows: list[dict], defaults: dict[str, str], seed: int = 5) -> dict[str, Any]:
    """Template labels shuffled within task: the LR test should show no effect."""
    rng = np.random.default_rng(seed)
    df = frame(rows, defaults)
    df["template"] = df.groupby("task")["template"].transform(lambda s: rng.permutation(s.values))
    try:
        return lr_test(df)
    except Exception as e:  # noqa: BLE001
        return {"defined": False, "error": repr(e)[:300]}
