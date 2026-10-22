#!/usr/bin/env python3
"""CPU unit tests (plan Stage A). Writes results/unit_tests_cpu.json; exits non-zero if any test fails.
Run: cd src && ../.venv/bin/python ../tests/test_cpu.py"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
import types
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import decide as D  # noqa: E402
import geometry as G  # noqa: E402
from hooks import edit_batched, make_prefill_edits  # noqa: E402
from stats import code_start, first_divergence, holm, mantel_haenszel, mcnemar_exact, mcnemar_one_sided  # noqa: E402


def _load(path: Path, name: str, stub_cfg: dict | None = None):
    saved = sys.modules.get("cfg")
    if stub_cfg is not None:
        m = types.ModuleType("cfg")
        m.__dict__.update(stub_cfg)
        sys.modules["cfg"] = m
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if stub_cfg is not None:
        if saved is not None:
            sys.modules["cfg"] = saved
        else:
            del sys.modules["cfg"]
    return mod


def t1_edits() -> dict:
    torch.manual_seed(0)
    D_, T, n0, n1 = 64, 20, 5, 15
    h = torch.randn(1, T, D_) * 30
    href = h[0, n0:n1] + torch.randn(n1 - n0, D_)  # the twin differs a little from the row's clean state
    u = torch.nn.functional.normalize(torch.randn(D_), dim=0)
    tgt = torch.rand(n1 - n0) * 5
    idx = torch.arange(n0, n1)
    e20 = _load(ROOT / "inputs" / "exp20" / "src" / "hooks.py", "hooks_exp20")
    e27 = _load(ROOT / "inputs" / "exp27" / "src" / "hooks.py", "hooks_exp27",
                {"HEAD_DIM": 128, "N_HEADS": 32, "V_BLOCKS": [12]})
    ours = make_prefill_edits([12], idx, {12: u}, {12: tgt}, {12: href})[12](h)
    a20 = e20.make_prefill_edits([12], idx, {12: u}, {12: tgt}, {12: href})[12](h)
    a27 = e27.make_edits("RAND", n0, n1, {12: u}, {12: tgt}, {12: href}, alpha=1.0)[12](h)
    bat = edit_batched(h, idx, u[None], tgt[None], href)
    along = ((ours[0, n0:n1] - href) @ u)
    d1 = float((ours - a20).abs().max())
    d2 = float((ours - a27).abs().max())
    d3 = float((ours - bat).abs().max())
    rel = float(((along - tgt).abs() / tgt.abs()).max())
    return {"max_abs_vs_exp20": d1, "max_abs_vs_exp27_RAND": d2, "max_abs_vs_batched": d3,
            "max_rel_along_u": rel, "pass": d1 < 1e-5 and d2 < 1e-5 and d3 < 1e-5 and rel < 1e-4}


def t2_mcnemar() -> dict:
    from statsmodels.stats.contingency_tables import mcnemar

    ok = True
    worst = 0.0
    for b in range(0, 12):
        for c in range(0, 12):
            n = b + c
            enum = 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)
            sm = 1.0 if n == 0 else float(mcnemar([[5, b], [c, 5]], exact=True).pvalue)
            ours = mcnemar_exact(b, c)
            worst = max(worst, abs(ours - enum), abs(ours - sm))
            ok &= abs(ours - enum) < 1e-12 and abs(ours - sm) < 1e-9
    ok &= abs(mcnemar_exact(6, 0) - 2 ** -5) < 1e-12 and abs(mcnemar_exact(8, 0) - 2 ** -7) < 1e-12
    one = mcnemar_one_sided(7, 1)
    ok &= abs(one - sum(math.comb(8, i) for i in range(7, 9)) / 2 ** 8) < 1e-12
    return {"max_abs_diff": worst, "p_6_0": mcnemar_exact(6, 0), "p_8_0": mcnemar_exact(8, 0), "pass": bool(ok)}


def t3_holm() -> dict:
    p = [0.01, 0.04, 0.03, 0.005]
    exp = [0.03, 0.06, 0.06, 0.02]
    got = holm(p)
    return {"got": got, "expected": exp, "pass": all(abs(a - b) < 1e-12 for a, b in zip(got, exp))}


def t4_mh() -> dict:
    from statsmodels.stats.contingency_tables import StratifiedTable

    rng = np.random.default_rng(0)
    tabs = [tuple(int(x) for x in rng.integers(1, 30, 4)) for _ in range(8)]
    ours = mantel_haenszel(tabs)
    st = StratifiedTable([np.array([[a, b], [c, d]]) for a, b, c, d in tabs])
    ci = st.oddsratio_pooled_confint()
    ok = abs(ours["or"] - st.oddsratio_pooled) < 1e-9 and abs(ours["ci"][0] - ci[0]) < 1e-6 and \
        abs(ours["ci"][1] - ci[1]) < 1e-6
    return {"ours": [ours["or"], ours["ci"]], "statsmodels": [float(st.oddsratio_pooled), [float(ci[0]), float(ci[1])]],
            "pass": bool(ok)}


def t5_divergence() -> dict:
    ok = first_divergence([1, 2, 3, 4], [1, 2, 9, 4]) == 2 and first_divergence([1, 2], [1, 2, 3]) == 2 and \
        first_divergence([5], [6]) == 0
    toks = ["```", "python", "\n", "def", " solve", "(..."]
    ok &= code_start(toks) == 3
    ok &= code_start(["```python\n", "def"]) == 1
    ok &= code_start(["Here", " is", "```", "py", "\n", "x"]) == 5
    # divergence before the fence: d = first_div - code_start < 0
    tw = [10, 11, 12, 13, 14, 15]  # 10 = 'Sure', 11 = '```', 12 = 'python', 13 = '\n'
    pu = [20, 11, 12, 13, 14, 15]
    d = first_divergence(tw, pu) - 4
    ok &= d < 0
    return {"pass": bool(ok), "d_before_fence": d}


def t6_geometry() -> dict:
    th = np.linspace(0, np.pi, 150)
    P = np.c_[np.cos(th), np.sin(th)] + np.random.default_rng(1).normal(0, 0.003, (150, 2))
    g = G.geodesics(P, 150)
    geo = g[10]["geo"]
    eu = float(np.linalg.norm(P[0] - P[-1]))
    Y, stress = G.mds2(geo)
    # two separated blobs: disconnected at k 5 is possible; the fallback picks the smallest connecting k
    rng = np.random.default_rng(2)
    B = np.vstack([rng.normal(0, 0.1, (40, 2)), rng.normal(50, 0.1, (40, 2))])
    gb = G.geodesics(B, 80, ks=(5, 10, 45))
    ok = geo[0, -1] > eu and stress < 0.05 and (not gb[5]["connected"]) and gb["chosen_k"] == 45
    return {"geodesic": float(geo[0, -1]), "euclid": eu, "stress1": stress, "blobs_chosen_k": gb["chosen_k"],
            "pass": bool(ok)}


def t7_null() -> dict:
    # 2 survivors with d = (1, 2): D = mean of n Bernoulli(1/2) picks; closed form P(D <= D_obs)
    land = ["a"] * 3 + ["b"] * 1
    r = G.edge_test(land, ["a", "b"], {"a": 1.0, "b": 2.0})
    n = 4
    k_b = 1  # D_obs = (3 * 1 + 1 * 2) / 4
    closed = sum(math.comb(n, i) for i in range(0, k_b + 1)) / 2 ** n
    ok = abs(r["p_edge"] - closed) < 1e-12
    # exact vs Monte Carlo on a 3-survivor case
    land3 = ["a"] * 6 + ["b"] * 3 + ["c"] * 1
    d3 = {"a": 0.5, "b": 1.0, "c": 3.0}
    ex = G.edge_test(land3, ["a", "b", "c"], d3)
    rng = np.random.default_rng(0)
    vals = np.array([0.5, 1.0, 3.0])
    Dn = vals[rng.integers(0, 3, size=(200000, 10))].mean(1)
    mc = float((Dn <= ex["D_obs"] + 1e-12).mean())
    ok &= abs(ex["p_edge"] - mc) < 0.01
    return {"p_edge_2": r["p_edge"], "closed_form": closed, "p_edge_exact_3": ex["p_edge"], "p_edge_mc_3": mc,
            "pass": bool(ok)}


def _rows(task, arm, site, alpha, ys, passes=None, slot0=0):
    out = []
    for i, y in enumerate(ys):
        ok = True if passes is None else passes[i]
        lab = ("quickselect" if task == "T03" else "dfs") if y else D.DEFAULTS[task]
        out.append({"task": task, "arm": arm, "site": site, "alpha": alpha, "template": f"W{1 + i // 6}",
                    "k": (slot0 + i) % 6, "passed": ok, "label": lab})
    return out


def t8_selection() -> dict:
    rows = []
    for t in ("T03", "T10"):
        rows += _rows(t, "TWIN", "TWIN", 0.0, [0] * 30)
        for a in (1.0, 2.0, 4.0):
            for s in ("S1", "S2", "S5"):
                rows += _rows(t, f"{s}_a{a:g}", s, a, [0] * 30)
        rows += _rows(t, "S0_a1", "S0", 1.0, [1] * 9 + [0] * 21)
        rows += _rows(t, "S4_a1", "S4", 1.0, [1] * 9 + [0] * 21)   # tie with S0 at alpha 1 -> S0 wins
        rows += _rows(t, "S0_a2", "S0", 2.0, [1] * 20 + [0] * 10, passes=[True] * 10 + [False] * 20)  # gated out
        rows += _rows(t, "S4_a2", "S4", 2.0, [0] * 30)
        rows += _rows(t, "S0_a4", "S0", 4.0, [0] * 30)
        rows += _rows(t, "S4_a4", "S4", 4.0, [0] * 30)
    res = D.s_a(rows)
    sel = {t: res["tasks"][t]["selected"] for t in ("T03", "T10")}
    ok = all(sel[t]["site"] == "S0" and sel[t]["alpha"] == 1.0 for t in sel)
    c = res["tasks"]["T03"]["contrasts"]["S1"]
    ok &= c["b"] == 9 and c["c"] == 0 and abs(c["p"] - 2 ** -8) < 1e-12
    ok &= abs(c["p_selection_aware"] - min(1, 6 * 2 ** -8)) < 1e-12
    ok &= res["verdict"].startswith("PASS")
    # no gated cell at all -> no selection, not PASS
    rows2 = [dict(r, passed=False) if r["site"] in ("S0", "S4") else r for r in rows]
    r2 = D.s_a(rows2)
    ok &= r2["tasks"]["T03"]["selected"] is None and not r2["verdict"].startswith("PASS")
    return {"selected": sel, "verdict": res["verdict"], "p_S1": c["p"], "pass": bool(ok)}


def t9_units() -> dict:
    rng = np.random.default_rng(3)
    normS = rng.uniform(50, 150, (36, 40))
    normR = rng.uniform(50, 150, 36)
    rq = rng.uniform(0.01, 0.12, 36)
    nS, nR = normS * rq[:, None], normR * rq
    pb = list(range(12, 24))
    c = math.sqrt((nS[pb] ** 2).sum() / (nR[pb] ** 2).sum())
    for alpha in (1.0, 2.0, 4.0):
        eS = ((alpha * nS[pb]) ** 2).sum()
        eR = ((alpha * c * nR[pb]) ** 2).sum()
        if abs(eS - eR) / eS > 1e-6:
            return {"pass": False}
    return {"c": c, "pass": True}


def main() -> int:
    out = {}
    for name, f in (("T1_edits", t1_edits), ("T2_mcnemar", t2_mcnemar), ("T3_holm", t3_holm), ("T4_mh", t4_mh),
                    ("T5_divergence", t5_divergence), ("T6_geometry", t6_geometry), ("T7_null", t7_null),
                    ("T8_selection", t8_selection), ("T9_units", t9_units)):
        try:
            out[name] = f()
        except Exception as e:  # noqa: BLE001
            out[name] = {"pass": False, "error": repr(e)}
        print(name, out[name].get("pass"), {k: v for k, v in out[name].items() if k != "pass"})
    out["all_pass"] = all(v.get("pass") for v in out.values() if isinstance(v, dict))
    (ROOT / "results" / "unit_tests_cpu.json").write_text(json.dumps(out, indent=1, default=str))
    return 0 if out["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
