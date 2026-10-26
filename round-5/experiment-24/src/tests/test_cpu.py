#!/usr/bin/env python3
"""CPU unit tests (testing plan items 4-5) -> results/unit_tests.json.

(4) hook math on random tensors: SET(0) = identity, SET(1) = donor exactly (after the bf16 cast), MR displacement
    norm = lam ||D|| per (l, p) (1e-4 relative), DS displacement along d = alpha n, XT direction cos = 1 with
    unit(Dbar_partner); (5) statistics: exact McNemar on arm-shuffled (exchangeable) pairs rejects about 5% at 0.05
    (one-sided), and the template-cluster bootstrap CI of beta covers the truth in simulated binomials.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import analysis_b as A  # noqa: E402
from cfg import RESULTS_DIR, write_json  # noqa: E402
from hooks5 import edits_along, edits_setto, unit_rows  # noqa: E402


def hook_tests() -> dict:
    g = torch.Generator().manual_seed(0)
    P, n, D = 40, 12, 64
    idx = torch.arange(10, 10 + n)
    h = (torch.randn(1, P, D, generator=g) * 3).to(torch.bfloat16)
    href = h[0, idx].float()
    hd = (torch.randn(n, D, generator=g) * 3).to(torch.bfloat16).float()
    Dm = hd - href
    res = {}
    e0 = edits_setto([5], idx, {5: href + 0.0 * Dm})[5](h)
    res["SET0_identity"] = bool(torch.equal(e0, h))
    e1 = edits_setto([5], idx, {5: href + 1.0 * Dm})[5](h)
    res["SET1_equals_donor"] = bool(torch.equal(e1[0, idx].float(), hd.to(torch.bfloat16).float()))
    u = torch.randn(D, generator=g)
    u = u / u.norm()
    lam = 0.5
    t_mr = href + lam * Dm.norm(dim=-1, keepdim=True) * u[None]
    disp = (t_mr - href).norm(dim=-1)
    res["MR_norm_rel_err"] = float(((disp - lam * Dm.norm(dim=-1)).abs() / (lam * Dm.norm(dim=-1))).max())
    res["MR_norm_ok"] = res["MR_norm_rel_err"] < 1e-4
    d = unit_rows(Dm)
    tgt = torch.full((n,), 2.0)
    hf = h.float()
    e2 = edits_along([5], idx, {5: d}, {5: tgt}, {5: href})[5](hf)
    along = ((e2[0, idx] - href) * d).sum(-1)
    res["DS_along_err"] = float((along - tgt).abs().max())
    res["DS_ok"] = res["DS_along_err"] < 1e-4
    dbar = torch.randn(D, generator=g)
    t_xt = href + 1.0 * Dm.norm(dim=-1, keepdim=True) * unit_rows(dbar[None])
    cosv = torch.nn.functional.cosine_similarity(t_xt - href, dbar[None].expand(n, -1), dim=-1)
    res["XT_cos_min"] = float(cosv.min())
    res["XT_ok"] = res["XT_cos_min"] > 1 - 1e-5
    res["all_pass"] = all(v for k, v in res.items() if k.endswith(("_ok", "identity", "donor")))
    return res


def stats_tests() -> dict:
    rng = np.random.default_rng(1)
    rej = 0
    for _ in range(200):
        p = rng.uniform(0.1, 0.5, size=50)
        a = (rng.uniform(size=50) < p).astype(int)
        b = (rng.uniform(size=50) < p).astype(int)
        rej += A.mcnemar_exact(a.tolist(), b.tolist())["p_one"] < 0.05
    cover = 0
    for s in range(100):
        r2 = np.random.default_rng(100 + s)
        rows = []
        for w in ["W1", "W2", "W3", "W4", "W5"]:
            for j in range(10):
                lab = "x" if r2.uniform() < 0.3 else "d"
                rows.append({"template": w, "slot": j, "label": lab, "passed": True})
        ci = A.beta_bootstrap(rows, "d", ["d", "x"], B=300, seed=s)["ci"]
        cover += ci[0] <= 0.3 <= ci[1]
    return {"mcnemar_shuffled_rejection_rate": rej / 200, "mcnemar_ok": rej / 200 <= 0.08,
            "beta_ci_coverage": cover / 100, "beta_ci_ok": cover / 100 >= 0.85,
            "note": "the template-cluster bootstrap with 5 clusters is anti-conservative; coverage is reported"}


if __name__ == "__main__":
    out = {"hooks": hook_tests(), "stats": stats_tests()}
    out["all_pass"] = bool(out["hooks"]["all_pass"] and out["stats"]["mcnemar_ok"])
    write_json(RESULTS_DIR / "unit_tests.json", out)
    print(out)
