"""(0j) Rival ban-free predictors of compliance on the 14-task screen (descriptive: screen, not confirmation)."""

from __future__ import annotations

import json
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
from loguru import logger

from src.labels import QWEN14, default_of
from src.paths import WS, cite, p
from src.route import frlp_runner_up
from src.stats import balanced_accuracy, fisher_2x2, holm, spearman_perm

RES, TAB = WS / "results", WS / "tables"
T7 = {"T1": "t1", "T2": "t2"}
T7_DEFAULT = {"t1": "bfs", "t2": "dijkstra"}


def _jsonl(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def _true(v) -> bool:
    return v is True or str(v) == "True"


def can_scores() -> dict[str, float]:
    out = {}
    per = defaultdict(lambda: [0, 0])
    for r in _jsonl(p("exp11", "data/samples_forced.jsonl")):
        m = r.get("forced_mode")
        per[(r["task"], m)][1] += 1
        per[(r["task"], m)][0] += int(_true(r.get("passed")) and r.get("label") == m)
    for t in QWEN14:
        if t in T7:
            continue
        d = default_of(t)
        vals = [k / n for (tt, m), (k, n) in per.items() if tt == t and m != d and n > 0]
        out[t] = max(vals) if vals else np.nan
    per7 = defaultdict(lambda: [0, 0])
    for r in _jsonl(p("exp7", "data/forced_labelled.jsonl")):
        per7[(r["task"], r["j"])][1] += 1
        per7[(r["task"], r["j"])][0] += int(_true(r.get("passed")) and r.get("label") == r["j"])
    for T, t in T7.items():
        vals = [k / n for (tt, m), (k, n) in per7.items() if tt == t and m != T7_DEFAULT[t] and n > 0]
        out[T] = max(vals) if vals else np.nan
    return out


def clarity_scores() -> dict[str, float]:
    out = {}
    rows = _jsonl(p("exp11", "data/association.jsonl"))
    for t in QWEN14:
        if t in T7:
            continue
        ans = [r.get("mapped") for r in rows if r["task"] == t and r["X"] == default_of(t)]
        c = Counter(ans)
        out[t] = max(c.values()) / len(ans) if ans else np.nan
    a7 = json.loads(p("exp7", "results/association.json").read_text())
    for T, t in T7.items():
        key = f"{t}|{T7_DEFAULT[t]}"
        cnt = (a7.get("counts") or {}).get(key)
        if isinstance(cnt, dict) and sum(cnt.values()) > 0:
            out[T] = max(cnt.values()) / sum(cnt.values())
        else:
            prof = a7["profiles"][key]
            out[T] = max(prof.values())
    return out


def frlp_mass() -> dict[str, float]:
    out = {t: v[2] for t, v in frlp_runner_up().items()}
    cells = [r for r in _jsonl(p("exp7", "results/frlp_cells.jsonl")) if r["condition"] == "base0"
             and r["variant"] == "primary" and r["half"] == "all"]
    for T, t in T7.items():
        L = {r["algorithm"]: float(r["L"]) for r in cells if r["task"] == t}
        m = max(L.values())
        z = sum(np.exp(v - m) for v in L.values())
        nd = {k: v for k, v in L.items() if k != T7_DEFAULT[t]}
        out[T] = float(np.exp(max(nd.values()) - m) / z)
    return out


def run_rivals_stage() -> None:
    screen = json.loads((WS / "screen.json").read_text())["tasks"]
    knob = pd.read_parquet(WS / "data" / "knob.parquet")
    y = {t: screen[t]["cat_only_ban_avoidance"] for t in QWEN14}
    mov = {t: screen[t]["movable"] for t in QWEN14}
    maxE = {t: max(v for v in (screen[t]["alpha_1"]["E_t"], screen[t]["alpha_2"]["E_t"]) if v is not None) for t in QWEN14}
    can, clar, frlp = can_scores(), clarity_scores(), frlp_mass()

    def kshare(exp, arm, t):
        q = knob[(knob.exp == exp) & (knob.task == t) & (knob.arm == arm)]
        return float(q.iloc[0].offdef_share) if len(q) else np.nan

    nonce = {t: (kshare("exp13", "nonce", t) if t not in T7 else np.nan) for t in QWEN14}
    nov = {t: (kshare("exp13", "novelty", t) if t not in T7 else kshare("exp6", "A3:instr_fully_novel", t)) for t in QWEN14}
    preds = {"movable": mov, "max_E_t": maxE, "can": can, "clarity": clar, "frlp_runner_up_mass": frlp,
             "nonce_offdef": nonce, "novelty_offdef": nov}
    tab = pd.DataFrame({"task": QWEN14, "cat_only_ban_avoidance": [y[t] for t in QWEN14],
                        **{k: [v.get(t, np.nan) for t in QWEN14] for k, v in preds.items()}})
    tab["novelty_flag"] = ["exp6 'fully novel' instruction (flagged)" if t in T7 else "" for t in QWEN14]
    tab.to_csv(TAB / "rival_predictor_values.csv", index=False)
    yv = np.array([y[t] for t in QWEN14], float)
    ybin = (yv >= 0.5).astype(int)
    recs = []
    for k, v in preds.items():
        x = np.array([v.get(t, np.nan) for t in QWEN14], float)
        sp = spearman_perm(x, yv)
        ok = np.isfinite(x)
        cut = None
        if k == "movable":
            xb = x.copy()
        else:
            cut = float(np.nanmedian(x))
            xb = np.where(np.isfinite(x), (x > cut).astype(float), np.nan)
        okb = np.isfinite(xb)
        fis = fisher_2x2(xb[okb].astype(int), ybin[okb]) if okb.sum() >= 4 else {"table": None, "p": np.nan}
        ba = balanced_accuracy(xb[okb].astype(int), ybin[okb]) if okb.sum() >= 4 else np.nan
        loo = []
        for i, t in enumerate(QWEN14):
            keep = [j for j in range(len(QWEN14)) if j != i]
            r = spearman_perm(x[keep], yv[keep], n_perm=20_000)
            loo.append(r["rho"])
        loo = np.array(loo, float)
        recs.append({"predictor": k, "n": int(ok.sum()), "spearman_rho": sp["rho"], "p_perm": sp["p_perm"],
                     "perm_method": sp.get("method"), "kendall_tau_b": sp.get("kendall_tau_b"),
                     "median_cut": cut, "confusion_table": json.dumps(fis["table"]), "balanced_accuracy": ba,
                     "fisher_p": fis["p"], "loo_rho_min": float(np.nanmin(loo)) if np.isfinite(loo).any() else np.nan,
                     "loo_rho_max": float(np.nanmax(loo)) if np.isfinite(loo).any() else np.nan,
                     "label": "screen, not confirmation"})
    df = pd.DataFrame(recs)
    df["p_holm_transparency_only"] = holm(df.p_perm.tolist())
    df.to_csv(TAB / "rival_predictors.csv", index=False)
    out = {"table": "tables/rival_predictors.csv", "values": "tables/rival_predictor_values.csv",
           "rows": df.to_dict("records"), "label": "descriptive: screen, not confirmation; median cuts declared before outcomes were read",
           "sources": [cite("exp11", "data/samples_forced.jsonl"), cite("exp7", "data/forced_labelled.jsonl"),
                       cite("exp11", "data/association.jsonl"), cite("exp7", "results/association.json"),
                       cite("exp11", "data/frlp_cells.jsonl"), cite("exp7", "results/frlp_cells.jsonl"),
                       cite("exp13", "data/samples.jsonl"), cite("exp6", "results/samples.jsonl"), "screen.json"]}
    (RES / "rivals.json").write_text(json.dumps(out, indent=1, default=str))
    logger.info("rivals: " + "; ".join(f"{r['predictor']} rho={r['spearman_rho']:.2f} p={r['p_perm']:.3g}" for r in recs))
