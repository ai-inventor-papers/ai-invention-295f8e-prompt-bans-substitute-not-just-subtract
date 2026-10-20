"""(0a) C1 likelihood diagnostics restricted to estimable mass.

(i)   argmax-versus-landing table for every sampled single-ban event (Qwen: exp1 single bans, exp8 arm a, exp9
      single:<X>, exp12 fresh pool; Llama: the 14 exp10 events).
(ii)  C1 recomputed on implied mass with survivors of >= 1% mass and ESS >= 5 in both cells.
(iii) bootstrap-versus-replicate variance on Qwen (two-stage: templates then programs; one-stage sensitivity), basic and
      percentile intervals for V_u, V_s, SHARE in both models.
(iv)  mention-reference AIM bias: derivation + 10,000-draw null simulation.
(v)   the ESS-weighted 1.24 'share' recomputed and named.
(vi)  importance-weight arithmetic (Kish, lognormal, PSIS k-hat) -> programs, GPU-hours, bench events.
Exp7's own cell code is vendored (vendor/exp7, path-patched only) so every L_j is rebuilt exactly as exp7 built it.
"""

from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from common.paths import RESULTS, SEED, TABLES, WS, dep, read_json, read_jsonl, src, write_json
from common.rows import MODAL, T1_K6, T2_K5, iter_rows
from common.stats import kish_ess, psis_khat, spearman, wilson

sys.path.insert(0, str(WS / "vendor" / "exp7"))

CAT = {"t1": T1_K6, "t2": T2_K5}
ESS_MIN, MASS_MIN = 5.0, 0.01


def _e7():
    import c1 as e7c1  # noqa: E402  (vendored)
    import config as e7cfg  # noqa: E402
    import frlp as e7frlp  # noqa: E402

    return e7cfg, e7frlp, e7c1


def k6(r: dict[str, Any]) -> str:
    """Label in exp7's K=6 / K=5 analysis space (exp9's unit-weight Dijkstra counts as T1 'dijkstra' here)."""
    if r["exp"] == "exp9" and r["task"] == "t1" and r["label_fine"] in ("dijkstra_unit", "unit_dijkstra"):
        return "dijkstra"
    lab = r["label"]
    if lab in CAT.get(r["task"], []):
        return lab
    return "unparseable" if lab == "unparseable" else "other"


def softmax(L: np.ndarray) -> np.ndarray:
    m = np.nanmax(L)
    p = np.exp(L - m)
    p = np.where(np.isfinite(p), p, 0.0)
    return p / p.sum() if p.sum() > 0 else np.full(len(L), np.nan)


# ------------------------------------------------------------------------------------------------ cell access
class Cells:
    """Rebuilt exp7 cells (L and ESS for halves h1/h2/all) for every condition C1 needs."""

    def __init__(self) -> None:
        e7cfg, e7frlp, e7c1 = _e7()
        self.cfg, self.frlp, self.c1 = e7cfg, e7frlp, e7c1
        self.tds = e7frlp.build_task_data()
        self.ca, self.cx, self.e2, self.L, self.E = {}, {}, {}, {}, {}
        for t in ("t1", "t2"):
            td = self.tds[t]
            conds, virtual = e7c1.needed_conds(t)
            e2 = e7c1.edit2_conds(td)
            ca = e7frlp.CellArrays(td, conds + e2, "primary", virtual)
            L, E = ca.cells(with_ess=True)
            self.ca[t], self.e2[t], self.L[t], self.E[t] = ca, e2, L, E
            self.cx[t] = e7c1.Ctx(ca, L, E)

    def js(self, t: str) -> list[str]:
        return self.ca[t].js

    def v(self, t: str, cond: str, h: str = "all") -> np.ndarray:
        return self.cx[t].v(cond, h)

    def e(self, t: str, cond: str, h: str = "all") -> np.ndarray:
        return self.cx[t].e(cond, h)

    def point(self, t: str, ref: str = "neutral", templates: list[str] | None = None, W: np.ndarray | None = None,
              dirs: list[str] | None = None, ess_weight: bool = False) -> dict[str, Any]:
        c1 = self.c1
        ca = self.ca[t]
        if W is None:
            cx = self.cx[t]
        else:
            cx = c1.Ctx(ca, ca.cells(W), self.E[t])
        return c1.task_point(self.tds[t], ca, cx, templates or self.cfg.WS, dirs or c1.RAND_NAMES, "primary", ref,
                             ess_weight, self.e2[t])


# ------------------------------------------------------------------------------------------------ (i) event table
def qwen_events(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ev = []
    for r in rows:
        if r["model"] != "Qwen/Qwen3-8B":
            continue
        e, c, t = r["exp"], r["condition"], r["task"]
        key = None
        if e == "exp1" and c.startswith("ban:") and "+" not in c:
            X = c.split(":", 1)[1]
            key = (f"exp1|{t}|{c}", t, X, "modal" if X == MODAL[t] else "absent-mode (sham)", src("exp1", "data/samples.jsonl"))
        elif e == "exp8" and c == "a":
            key = (f"exp8|{t}|arm_a", t, MODAL[t], "modal", src("exp8", "data/samples.jsonl"))
        elif e == "exp9" and c.startswith("single:"):
            X = c.split(":", 1)[1]
            key = (f"exp9|{t}|{c}", t, X, "modal" if X == MODAL[t] else "absent-mode (sham)", src("exp9", "data/samples.jsonl"))
        elif e == "exp12" and c == "ban" and r["arm"] == "C1_fresh_pool" and r["source"].endswith("results/samples.jsonl"):
            key = (f"exp12|{t}|fresh_pool", t, MODAL[t], "modal", src("exp12", "results/samples.jsonl"))
        if key:
            r = dict(r)
            r["_ev"] = key
            ev.append(r)
    groups: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for r in ev:
        groups[r["_ev"]].append(r)
    out = []
    for (name, t, X, kind, source), rs in sorted(groups.items()):
        out.append(_event_summary(name, "Qwen/Qwen3-8B", t, X, kind, source, [k6(r) for r in rs],
                                  [bool(r["passed"]) for r in rs]))
    return out


def _event_summary(name: str, model: str, t: str, X: str, kind: str, source: str, labels: list[str],
                   passed: list[bool]) -> dict[str, Any]:
    att = [lab for lab in labels if lab != "unparseable"]
    nb = [lab for lab in att if lab != X]
    cnb = [lab for lab, p in zip(labels, passed) if lab not in ("unparseable", X) and p]
    ca, cn, cc = Counter(att), Counter(nb), Counter(cnb)
    surv = [j for j in CAT[t] if j != X]
    modal = max(surv, key=lambda j: (cn.get(j, 0), -surv.index(j))) if nb else None
    modal_c = max(surv, key=lambda j: (cc.get(j, 0), -surv.index(j))) if cnb else None
    k = cn.get(modal, 0) if modal else 0
    return {"event": name, "model": model, "task": t, "banned": X, "ban_kind": kind, "source": source,
            "n_total": len(labels), "n_attempted": len(att), "n_nonbanned": len(nb), "n_correct_nonbanned": len(cnb),
            "attempted_counts": dict(ca), "nonbanned_counts": dict(cn), "correct_nonbanned_counts": dict(cc),
            "modal_landing": modal, "modal_landing_share": k / len(nb) if nb else math.nan,
            "modal_landing_wilson": wilson(k, len(nb)) if nb else (math.nan, math.nan),
            "modal_correct_landing": modal_c, "survivors": surv,
            "other_share_nonbanned": cn.get("other", 0) / len(nb) if nb else math.nan}


def llama_events() -> list[dict[str, Any]]:
    ev = read_json(dep("exp10", "results/events.json"))
    lab = read_jsonl(dep("exp10", "data/labelled.jsonl"))
    by_cond: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for r in lab:
        by_cond[(r["task"], r["condition"])].append(r)
    out = []
    for t in ("t1", "t2"):
        for e in ev[t]:
            rs = [r for c in e["conds"] for r in by_cond.get((t, c), [])]
            labels = []
            for r in rs:
                L = str(r.get("label"))
                L = "unparseable" if L in ("None", "no_code") or not (r.get("code") or "").strip() else L
                labels.append(L if L in CAT[t] or L == "unparseable" else "other")
            X = e["banned"][0] if len(e["banned"]) == 1 else ("+".join(e["banned"]) if e["banned"] else "")
            kind = ("modal" if X == MODAL[t] else "absent-mode (sham)") if len(e["banned"]) == 1 else \
                ("two-step" if e["banned"] else "no ban")
            s = _event_summary(f"exp10|{t}|{e['name']}", "meta-llama/Llama-3.1-8B-Instruct", t, X, kind,
                               src("exp10", "data/labelled.jsonl"), labels, [str(r.get("passed")) == "True" for r in rs])
            s["events_json_attempted_counts"] = e["attempted_counts"]
            s["events_json_N"] = e["N"]
            s["single_ban"] = len(e["banned"]) == 1
            out.append(s)
    return out


def _rank_of(vals: dict[str, float], target: str | None) -> float:
    if target is None or target not in vals or not np.isfinite(vals[target]):
        return math.nan
    order = sorted(vals, key=lambda j: -vals[j])
    return float(order.index(target) + 1)


def _argmax(vals: dict[str, float]) -> tuple[str | None, float]:
    v = {k: x for k, x in vals.items() if x is not None and np.isfinite(x)}
    if not v:
        return None, math.nan
    k = max(v, key=v.get)
    return k, float(v[k])


def implied_ban_mass_qwen(cells: Cells, t: str, X: str) -> tuple[dict[str, float], dict[str, float]]:
    js = cells.js(t)
    S = [j for j in js if j != X]
    idx = [js.index(j) for j in S]
    ps, ess = [], []
    for w in cells.cfg.WS:
        L = cells.v(t, f"ban|{X}|{w}")[idx]
        if np.isfinite(L).all():
            ps.append(softmax(L))
            ess.append(cells.e(t, f"ban|{X}|{w}")[idx])
    if not ps:
        return {}, {}
    p = np.mean(ps, axis=0)
    return dict(zip(S, p.tolist())), dict(zip(S, np.median(ess, axis=0).tolist()))


def llama_cells() -> dict[tuple, float]:
    out = {}
    for r in read_jsonl(dep("exp10", "frlp/cells.jsonl")):
        if r.get("half") == "all" and r.get("variant") == "full":
            out[(r["task"], r["condition"], r["algorithm"])] = (r["L"], r.get("ess"))
    return out


def event_table(rows: list[dict[str, Any]], cells: Cells) -> dict[str, Any]:
    c1j = read_json(dep("exp7", "results/c1.json"))
    e8 = read_json(dep("exp8", "results/analysis.json"))["survivor_gains"]
    l10 = read_json(dep("exp10", "results/c1.json"))
    lc = llama_cells()
    table = []
    for e in qwen_events(rows) + llama_events():
        t, X = e["task"], e["banned"]
        rec = dict(e)
        preds: dict[str, dict[str, float]] = {}
        if e["model"].startswith("Qwen"):
            for ref, key in (("neutral", "primary_neutral"), ("mention", "reference_mention")):
                row = c1j[key]["tasks"][t]["rows"].get(X)
                if row:
                    preds[f"Gbar_{ref}"] = row["Gbar"]
                    preds[f"s_{ref}"] = row["s"]
                    if ref == "neutral":
                        rec["median_ess_per_survivor"] = row["median_ess"]
                        rec["fitted_ladder"] = row["fitted_ladder"]
            mass, mess = implied_ban_mass_qwen(cells, t, X)
            if mass:
                preds["mass"] = mass
                rec["implied_mass_median_ess"] = mess
            if e["event"].startswith("exp8") and t in e8:
                g = e8[t]
                preds["G_exp8_arm_a"] = dict(zip(g["survivors"], g["G_a"]))
                rec["exp8_median_ess_arm_a"] = {j: v.get("a") for j, v in g["median_ess"].items()}
            rec["reference_source"] = src("exp7", "results/c1.json")
        else:
            if e.get("single_ban"):
                for ref in ("neutral", "mention"):
                    rows_l = l10["c1"][ref]["per_task"].get(t, {}).get("rows", [])
                    row = next((r for r in rows_l if r["X"] == X), None)
                    if row:
                        preds[f"Gbar_{ref}"] = dict(zip(row["survivors"], row["gbar"]))
                        preds[f"s_{ref}"] = dict(zip(row["survivors"], row["s"]))
                # implied ban mass over the survivors with cells in exp10 frlp/cells.jsonl
                algs = sorted({a for (tt, c, a) in lc if tt == t})
                S = [j for j in algs if j != X]
                ps = []
                for w in range(1, 6):
                    L = np.array([lc.get((t, f"ban:{X}:w{w}", j), (np.nan, None))[0] for j in S], dtype=float)
                    if np.isfinite(L).all() and len(L):
                        ps.append(softmax(L))
                if ps:
                    preds["mass"] = dict(zip(S, np.mean(ps, axis=0).tolist()))
                rec["reference_source"] = src("exp10", "results/c1.json") + " ; " + src("exp10", "frlp/cells.jsonl")
        landing = e["modal_landing"]
        for name, vals in preds.items():
            vals = {k: v for k, v in vals.items() if k in e["survivors"] or not e["model"].startswith("Qwen")}
            am, av = _argmax(vals)
            rec[f"argmax_{name}"] = am
            rec[f"argmax_{name}_value"] = av
            rec[f"hit_{name}"] = (am == landing) if (am is not None and landing is not None) else None
            rec[f"rank_landing_{name}"] = _rank_of(vals, landing)
            rec[f"values_{name}"] = vals
        table.append(rec)
    # metrics
    def hit_block(model_prefix: str | None, pred: str, kinds: tuple[str, ...] | None = None) -> dict[str, Any]:
        sel = [r for r in table if (model_prefix is None or r["model"].startswith(model_prefix))
               and r.get(f"hit_{pred}") is not None and (kinds is None or r["ban_kind"] in kinds)]
        k = sum(bool(r[f"hit_{pred}"]) for r in sel)
        ranks = [r[f"rank_landing_{pred}"] for r in sel if np.isfinite(r[f"rank_landing_{pred}"])]
        return {"hits": k, "n": len(sel), "rate": k / len(sel) if sel else math.nan,
                "wilson": wilson(k, len(sel)) if sel else (math.nan, math.nan),
                "mean_rank_landing": float(np.mean(ranks)) if ranks else math.nan,
                "mean_n_survivors": float(np.mean([len(r["survivors"]) for r in sel])) if sel else math.nan,
                "chance_rate": float(np.mean([1 / len(r["survivors"]) for r in sel])) if sel else math.nan}

    metrics = {}
    for m in ("Qwen", "meta-llama", None):
        for p in ("Gbar_neutral", "s_neutral", "mass", "Gbar_mention", "s_mention", "G_exp8_arm_a"):
            b = hit_block(m, p)
            if b["n"]:
                metrics[f"{m or 'pooled'}|{p}|all_events"] = b
            b = hit_block(m, p, ("modal",))
            if b["n"]:
                metrics[f"{m or 'pooled'}|{p}|modal_bans"] = b
    # reproduction of the quoted numbers
    c1n = c1j["primary_neutral"]["tasks"]
    repro = {"t2_dijkstra_ban_s": c1n["t2"]["rows"]["dijkstra"]["s"], "t1_bfs_ban_s": c1n["t1"]["rows"]["bfs"]["s"],
             "t1_bfs_ban_s_iddfs_check_7.988": round(c1n["t1"]["rows"]["bfs"]["s"]["iddfs"], 3),
             "exp8_survivor_gains_G_a": {t: dict(zip(e8[t]["survivors"], e8[t]["G_a"])) for t in e8}}
    pooled = {}
    for t, j in (("t1", "dfs"), ("t2", "bf_spfa")):
        for scope, pref in (("iter2_modal_draws(exp8a+exp9single+exp12pool)", ("exp8", "exp9", "exp12")),
                            ("all_qwen_modal(exp1+exp8a+exp9single+exp12pool)", ("exp1", "exp8", "exp9", "exp12"))):
            sel = [r for r in table if r["model"].startswith("Qwen") and r["task"] == t and r["ban_kind"] == "modal"
                   and r["event"].split("|")[0] in pref]
            kc = sum(r["correct_nonbanned_counts"].get(j, 0) for r in sel)
            nc = sum(r["n_correct_nonbanned"] for r in sel)
            ka = sum(r["nonbanned_counts"].get(j, 0) for r in sel)
            na = sum(r["n_nonbanned"] for r in sel)
            pooled[f"{t}|{j}|{scope}"] = {"correct": f"{kc}/{nc}", "attempted_nonbanned": f"{ka}/{na}",
                                          "events": [r["event"] for r in sel]}
    repro["pooled_landing_counts"] = pooled
    return {"table": table, "metrics": metrics, "reproduction": repro}


# ------------------------------------------------------------------------------------------------ (ii) implied mass
def mass_c1(cells: Cells, W: dict[str, np.ndarray] | None = None, templates: list[str] | None = None) -> dict[str, Any]:
    cfg = cells.cfg
    tw = templates or cfg.WS
    out_rows, dropped = [], []
    for t in ("t1", "t2"):
        js = cells.js(t)
        ca = cells.ca[t]
        L = cells.L[t] if W is None else ca.cells(W[t])
        cx = cells.c1.Ctx(ca, L, cells.E[t])
        for B in js:
            S = [j for j in js if j != B]
            if len(S) < 3:
                continue
            idx = np.array([js.index(j) for j in S])
            pb, pr, eb, er = [], [], [], []
            for w in tw:
                Lb, Lr = cx.v(f"ban|{B}|{w}")[idx], cx.v(f"neutral|{B}|{w}|AB")[idx]
                if not (np.isfinite(Lb).all() and np.isfinite(Lr).all()):
                    continue
                pb.append(softmax(Lb))
                pr.append(softmax(Lr))
                eb.append(cx.e(f"ban|{B}|{w}", "all")[idx])
                er.append(cx.e(f"neutral|{B}|{w}|AB", "all")[idx])
            if not pb:
                continue
            p_ban, p_ref = np.mean(pb, 0), np.mean(pr, 0)
            ess_b, ess_r = np.nanmedian(eb, 0), np.nanmedian(er, 0)
            keep = ((p_ban >= MASS_MIN) | (p_ref >= MASS_MIN)) & (ess_b >= ESS_MIN) & (ess_r >= ESS_MIN)
            info = {"task": t, "B": B, "survivors": S, "p_ban": dict(zip(S, p_ban.tolist())),
                    "p_ref": dict(zip(S, p_ref.tolist())), "ess_ban": dict(zip(S, ess_b.tolist())),
                    "ess_ref": dict(zip(S, ess_r.tolist())), "kept": [j for j, k in zip(S, keep) if k],
                    "n_mass_ge_1pct": int(((p_ban >= MASS_MIN) | (p_ref >= MASS_MIN)).sum()),
                    "n_ess_ge_5_both": int(((ess_b >= ESS_MIN) & (ess_r >= ESS_MIN)).sum())}
            if keep.sum() < 3:
                info["status"] = f"dropped: {int(keep.sum())} survivor(s) pass the 1%-mass and ESS>=5 restriction"
                dropped.append(info)
                continue
            K = idx[keep]
            kept = info["kept"]

            def mk(Lv: np.ndarray) -> np.ndarray:
                return softmax(Lv[K])

            reps = []
            for w in tw:
                for h, ns in (("h1", "A"), ("h2", "B")):
                    reps.append(mk(cx.v(f"ban|{B}|{w}", h)) - mk(cx.v(f"neutral|{B}|{w}|{ns}", h)))
            G = np.array(reps)
            dm = G.mean(0)
            base = mk(cx.v("base0"))
            fam = {"NONCE": np.mean([mk(cx.v(f"ban|nonce|{w}")) - mk(cx.v(f"neutral|nonce|{w}|AB")) for w in cfg.WS], 0),
                   "RAND": np.mean([mk(cx.v(f"edit|{d}")) - base for d in cells.c1.RAND_NAMES], 0),
                   "NOV": mk(cx.v("novelty")) - base}
            u = np.mean([fam["NONCE"], fam["RAND"], fam["NOV"]], 0)
            u = u - u.mean()
            un = np.linalg.norm(u)
            uhat = u / un if un > 0 else u
            a = float(dm @ uhat)
            s = dm - a * uhat
            R = len(G)
            tot = float(G.var(axis=0, ddof=1).sum() / R)
            sig2 = tot / (len(K) - 1)
            wB = float(p_ban[keep].sum())
            info.update({"status": "kept", "dmass": dict(zip(kept, dm.tolist())), "a": a, "s": dict(zip(kept, s.tolist())),
                         "a2": a * a, "ss_s": float(s @ s), "N_u": sig2, "N_s": (len(K) - 2) * sig2, "weight": wB,
                         "tot_noise": tot})
            out_rows.append(info)
    if out_rows:
        V_u = sum(r["weight"] * (r["a2"] - r["N_u"]) for r in out_rows)
        V_s = sum(r["weight"] * (r["ss_s"] - r["N_s"]) for r in out_rows)
        share = V_s / (V_u + V_s) if (V_u + V_s) != 0 else math.nan
    else:
        V_u = V_s = share = math.nan
    return {"rows": out_rows, "dropped": dropped, "V_u": V_u, "V_s": V_s, "SHARE": share,
            "n_rows_kept": len(out_rows), "n_rows_total": len(out_rows) + len(dropped)}


# ------------------------------------------------------------------------------------------------ (iii) bootstrap
def bootstrap(cells: Cells, n_boot: int, two_stage: bool = True, seed: int = SEED,
              keep_cells: bool = False) -> dict[str, Any]:
    rng = np.random.default_rng(seed + (0 if two_stage else 1))
    cfg = cells.cfg
    comps = {"t1": [], "t2": []}
    cellv = defaultdict(list)
    for b in range(n_boot):
        tw = list(rng.choice(cfg.WS, size=len(cfg.WS), replace=True)) if two_stage else list(cfg.WS)
        for t in ("t1", "t2"):
            ca = cells.ca[t]
            W = ca.boot_weights(rng)
            pb = cells.point(t, "neutral", templates=tw, W=W)
            sh = pb["share"]
            comps[t].append({"V_u": sh["V_u"], "V_s": sh["V_s"], "SHARE": sh["SHARE"],
                             "Gbar": {r["B"]: r["Gbar"] for r in pb["rows"]}})
            if keep_cells:
                Lb = ca.cells(W)
                cx = cells.c1.Ctx(ca, Lb, cells.E[t])
                for B in ca.js:
                    for w in cfg.WS:
                        for kind, cond in (("ban", f"ban|{B}|{w}"), ("mention", f"mention|{B}|{w}"),
                                           ("neutral", f"neutral|{B}|{w}|AB")):
                            v = cx.v(cond)
                            cellv[(t, kind, B, w)].append(v)
    return {"comps": comps, "cellv": cellv}


def _intervals(boot: np.ndarray, point: float) -> dict[str, Any]:
    v = boot[np.isfinite(boot)]
    if len(v) == 0:
        return {}
    lo, hi = np.quantile(v, [0.025, 0.975])
    basic = (2 * point - hi, 2 * point - lo)
    return {"point": point, "boot_mean": float(v.mean()), "bias": float(v.mean() - point),
            "percentile_ci95": (float(lo), float(hi)), "basic_ci95": (float(basic[0]), float(basic[1])),
            "basic_crosses_unit_interval": bool(basic[0] < 0 or basic[1] > 1),
            "basic_crosses_zero": bool(basic[0] < 0)}


def variance_ratio(cells: Cells, boot: dict[str, Any], point_rows: dict[str, list]) -> dict[str, Any]:
    out = {"rows": [], "cells": []}
    for t in ("t1", "t2"):
        for r in point_rows[t]:
            B = r["B"]
            G = np.array([c["Gbar"][B] for c in boot["comps"][t] if B in c["Gbar"]])
            vb = G.var(axis=0, ddof=1)
            # replicate variance of the mean per survivor, exactly as exp7 c1.py row_stats: var_r(c_Br(j)) / R
            per = r["_rep_var_mean"]
            out["rows"].append({"task": t, "B": B, "trace_boot_var": float(vb.sum()), "tot_noise_method_py": r["tot_noise"],
                                "ratio": float(vb.sum() / r["tot_noise"]) if r["tot_noise"] > 0 else math.nan,
                                "replicate_sd_sq_over_5_trace": float(r["replicate_sd"] ** 2 / 5 * len(r["survivors"])),
                                "n_survivors": len(r["survivors"])})
            for j, a, bvar in zip(r["survivors"], per, vb):
                out["cells"].append({"task": t, "B": B, "j": j, "var_boot": float(bvar), "var_rep_mean": float(a),
                                     "ratio": float(bvar / a) if a > 0 else math.nan})
    rr = np.array([x["ratio"] for x in out["rows"]])
    cr = np.array([x["ratio"] for x in out["cells"]])
    out["row_ratio_median"] = float(np.nanmedian(rr))
    out["row_ratio_range"] = (float(np.nanmin(rr)), float(np.nanmax(rr)))
    out["cell_ratio_median"] = float(np.nanmedian(cr))
    out["frac_rows_ratio_gt_1"] = float(np.mean(rr > 1))
    return out


def point_rows_with_rep(cells: Cells) -> dict[str, list]:
    out = {}
    for t in ("t1", "t2"):
        pt = cells.point(t, "neutral")
        rows = []
        for r in pt["rows"]:
            # rebuild the replicate matrix C to get per-survivor replicate variances (row_stats keeps only the total)
            js = cells.js(t)
            S = r["survivors"]
            idx = np.array([js.index(j) for j in S])
            reps = []
            for w in cells.cfg.WS:
                for h, ns in (("h1", "A"), ("h2", "B")):
                    g = (cells.v(t, f"ban|{r['B']}|{w}", h) - cells.v(t, f"neutral|{r['B']}|{w}|{ns}", h))[idx]
                    reps.append(g - g.mean())
            C = np.array(reps)
            r = dict(r)
            r["_rep_var_mean"] = C.var(axis=0, ddof=1) / len(C)
            r["replicate_sd"] = math.sqrt(r["tot_noise"] * r["R"] / len(S))
            assert abs(r["_rep_var_mean"].sum() - r["tot_noise"]) < 1e-9
            rows.append(r)
        out[t] = rows
    return out


# ------------------------------------------------------------------------------------------------ (iv) AIM null
def aim_stat(s_h1: list[np.ndarray], s_h2: list[np.ndarray], pv_h1: list[np.ndarray], pv_h2: list[np.ndarray]) -> float:
    vals = []
    for a1, a2, p1, p2 in zip(s_h1, s_h2, pv_h1, pv_h2):
        vals.append(np.nanmean([spearman(a1, p2), spearman(a2, p1)]))
    return float(np.nanmean(vals))


def _rank_rows(M: np.ndarray) -> np.ndarray:
    return np.argsort(np.argsort(M, axis=1), axis=1).astype(float)


def _spearman_rows(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    ra, rb = _rank_rows(A), _rank_rows(B)
    ra -= ra.mean(1, keepdims=True)
    rb -= rb.mean(1, keepdims=True)
    return (ra * rb).sum(1) / np.sqrt((ra * ra).sum(1) * (rb * rb).sum(1))


def aim_null_sim(uhats: list[np.ndarray], var: dict[str, dict[str, float]], n_sim: int, mode: str,
                 seed: int = SEED) -> np.ndarray:
    """Null AIM (mention reference) with zero X-specific signal. Each cell profile (template-averaged, per half) =
    shared component (identical prompt in both halves) + half-specific importance-sampling component.
    mode 'split_half': the exp7 split-half design, only the shared component of the mention twin enters both s and PV.
    mode 'shared_cell': the plan's simple model: the SAME mention draw enters gain and PV.
    mode 'independent_mention' (placebo 3): independent mention copies in gain and PV -> bias ~ 0."""
    rng = np.random.default_rng(seed)
    total = np.zeros(n_sim)
    for uh in uhats:
        n = len(uh)

        def draw(kind: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
            sh = rng.normal(0, math.sqrt(var[kind]["shared"]), (n_sim, n))
            i1 = rng.normal(0, math.sqrt(var[kind]["is"]), (n_sim, n))
            i2 = rng.normal(0, math.sqrt(var[kind]["is"]), (n_sim, n))
            return sh, i1, i2

        bs, b1, b2 = draw("ban")
        ms, m1, m2 = draw("mention")
        ns, n1, n2 = draw("neutral")
        if mode == "split_half":
            ban1, ban2 = bs + b1, bs + b2
            men_g1, men_g2 = ms + m1, ms + m2           # mention in the gain (half h)
            men_p1, men_p2 = men_g1, men_g2              # the same half-specific cells form PV of that half
            neu1, neu2 = ns + n1, ns + n2
        elif mode == "shared_cell":
            ban1, ban2 = bs + b1, bs + b2
            men_g1 = men_g2 = men_p1 = men_p2 = ms + m1
            neu1, neu2 = ns + n1, ns + n2
        else:  # independent_mention
            ban1, ban2 = bs + b1, bs + b2
            men_g1, men_g2 = ms + m1, ms + m2
            ms2, mq1, mq2 = draw("mention")
            men_p1, men_p2 = ms2 + mq1, ms2 + mq2
            neu1, neu2 = ns + n1, ns + n2

        def resid(g: np.ndarray) -> np.ndarray:
            g = g - g.mean(1, keepdims=True)
            return g - (g @ uh)[:, None] * uh[None, :]

        s1, s2 = resid(ban1 - men_g1), resid(ban2 - men_g2)
        p1, p2 = men_p1 - neu1, men_p2 - neu2
        if mode == "shared_cell":
            row = 0.5 * (_spearman_rows(s1, p2) + _spearman_rows(s2, p1))
        else:
            row = 0.5 * (_spearman_rows(s1, p2) + _spearman_rows(s2, p1))
        total += row
    return total / len(uhats)


def variance_components(cells: Cells) -> dict[str, dict[str, float]]:
    """Per cell type: shared (cross-half covariance of the template-averaged centred survivor profile) and
    half-specific variance (half the mean squared h1-h2 difference), pooled (median) over rows."""
    comp = defaultdict(lambda: {"shared": [], "is": []})
    for t in ("t1", "t2"):
        js = cells.js(t)
        for B in js:
            S = [j for j in js if j != B]
            if len(S) < 3:
                continue
            idx = np.array([js.index(j) for j in S])
            for kind in ("ban", "mention", "neutral"):
                prof = {}
                for h, ns in (("h1", "A"), ("h2", "B")):
                    cond = {"ban": "ban|{B}|{w}", "mention": "mention|{B}|{w}", "neutral": "neutral|{B}|{w}|" + ns}[kind]
                    v = np.nanmean([cells.v(t, cond.format(B=B, w=w), h)[idx] for w in cells.cfg.WS], axis=0)
                    prof[h] = v - v.mean()
                if not (np.isfinite(prof["h1"]).all() and np.isfinite(prof["h2"]).all()):
                    continue
                n = len(S)
                comp[kind]["shared"].append(max(0.0, float((prof["h1"] * prof["h2"]).sum() / (n - 1))))
                comp[kind]["is"].append(float(((prof["h1"] - prof["h2"]) ** 2).sum() / (n - 1) / 2))
    return {k: {"shared": float(np.median(v["shared"])), "is": float(np.median(v["is"])),
                "n_rows": len(v["shared"])} for k, v in comp.items()}


# ------------------------------------------------------------------------------------------------ (vi) M arithmetic
def m_arithmetic(cells: Cells) -> dict[str, Any]:
    timings = read_json(dep("exp7", "results/timings.json"))
    units = read_jsonl(dep("exp7", "scores/units_done.jsonl"))
    tok_per_prog = np.mean([u["n_tokens"] / max(1, u["n_programs"]) + u.get("prompt_tokens", 0) for u in units])
    tok_s = sum(v["tokens"] for v in timings["scoring_by_queue"].values()) / timings["scoring_gpu_seconds"]
    gen_s = sum(v for k, v in timings["generation"].items() if k.startswith("round"))
    n_gen = 1170
    gen_s_per_prog = gen_s / n_gen
    rows = []
    pooled_lw = defaultdict(list)
    for t in ("t1", "t2"):
        ca = cells.ca[t]
        for ci, cond in enumerate(ca.conds):
            fam = cond.split("|")[0]
            for k, j in enumerate(ca.js):
                m = ca.pj == k
                lw = ca.lw[ci, m]
                lw = lw[np.isfinite(lw)]
                if len(lw) < 3:
                    continue
                M = len(lw)
                ess = kish_ess(lw)
                cv2 = M / ess - 1
                sig = float(np.std(lw, ddof=1))
                rows.append({"model": "Qwen/Qwen3-8B", "task": t, "condition": cond, "family": fam, "j": j, "M": M,
                             "kish_ess": ess, "cv2_plugin": cv2, "M5_plugin_lower_bound": 5 * (1 + cv2),
                             "sigma_logw": sig, "M5_lognormal": 5 * math.exp(min(sig * sig, 700)),
                             "khat_cell": psis_khat(lw)})
                lwn = lw - (np.log(np.mean(np.exp(lw - lw.max()))) + lw.max())   # normalise each cell to mean weight 1
                pooled_lw[("Qwen", t, j, fam)].extend(lwn.tolist())
    # Llama: per-program weights reconstructed from exp10 per-program scores (mixture over the forced prompts)
    lrows, lpooled = llama_logweights()
    rows += lrows
    for k, v in lpooled.items():
        pooled_lw[k].extend(v)
    khat = []
    for (mdl, t, j, fam), v in pooled_lw.items():
        if fam in ("ban", "neutral", "mention"):
            khat.append({"model": mdl, "task": t, "j": j, "family": fam, "n_draws_pooled": len(v),
                         "khat_pooled": psis_khat(np.array(v)),
                         "flag": "pooled across cells (different targets); unstable below ~100 draws per cell"})
    df = pd.DataFrame(rows)
    summ = []
    for (mdl, j), g in df[df["family"].isin(["ban", "neutral", "mention"])].groupby(["model", "j"]):
        summ.append({"model": mdl, "j": j, "n_cells": len(g),
                     "M5_plugin_median": float(g["M5_plugin_lower_bound"].median()),
                     "M5_plugin_p90": float(g["M5_plugin_lower_bound"].quantile(0.9)),
                     "M5_lognormal_median": float(g["M5_lognormal"].median()),
                     "M5_lognormal_p90": float(g["M5_lognormal"].quantile(0.9)),
                     "sigma_logw_median": float(g["sigma_logw"].median()),
                     "kish_ess_median": float(g["kish_ess"].median())})
    dq = df[(df["model"] == "Qwen/Qwen3-8B") & df["family"].isin(["ban", "neutral", "mention"])]
    m5p, m5l = float(dq["M5_plugin_lower_bound"].median()), float(dq["M5_lognormal"].median())
    # cost of one mass-level C1 event at M5 programs per algorithm: K algorithms x (ban + neutral A/B + mention over
    # 5 templates = 20 prompts) + 10 forced proposal prompts per program
    K = 6
    passes_per_prog = 20 + 10
    conv = {}
    for name, m5 in (("plugin_median_lower_bound", m5p), ("lognormal_median", m5l)):
        progs = m5 * K
        scored_tokens = progs * passes_per_prog * tok_per_prog
        gpu_h = scored_tokens / tok_s / 3600 + progs * gen_s_per_prog / 3600
        conv[name] = {"M5_per_algorithm": m5, "programs_per_event": progs, "scoring_passes_per_program": passes_per_prog,
                      "gpu_hours_per_event": gpu_h, "events_in_3_gpu_hours": 3 / gpu_h if gpu_h > 0 else math.nan,
                      "reachable_in_2_3_gpu_hours_for_one_event": bool(gpu_h <= 3)}
    k = pd.DataFrame(khat)
    return {"cells": rows, "summary": summ, "khat": khat,
            "khat_frac_gt_0.7": float((k["khat_pooled"] > 0.7).mean()) if len(k) else math.nan,
            "khat_frac_gt_0.7_qwen": float((k[k["model"] == "Qwen"]["khat_pooled"] > 0.7).mean()) if len(k) else math.nan,
            "M5_plugin_median_qwen": m5p, "M5_lognormal_median_qwen": m5l,
            "conversion": conv, "constants": {"mean_tokens_per_scoring_pass": float(tok_per_prog),
                                              "scored_tokens_per_s": float(tok_s),
                                              "generation_s_per_program": float(gen_s_per_prog),
                                              "sources": [src("exp7", "results/timings.json"),
                                                          src("exp7", "scores/units_done.jsonl")]}}


def llama_logweights() -> tuple[list[dict[str, Any]], dict[tuple, list[float]]]:
    rows, pooled = [], defaultdict(list)
    for t in ("t1", "t2"):
        p = dep("exp10", f"frlp/scores_{t}.parquet")
        if not p.exists():
            continue
        df = pd.read_parquet(p, columns=["program_id", "condition_id", "l_full"])
        piv = df.pivot_table(index="program_id", columns="condition_id", values="l_full", aggfunc="first")
        progs = piv.index.tolist()
        jj = np.array([pid.split("|")[1] for pid in progs])
        forced_cols = [c for c in piv.columns if c.startswith("forced:")]
        lq = np.full(len(progs), np.nan)
        for j in sorted(set(jj)):
            cols = [c for c in forced_cols if c.split(":")[1] == j]
            if not cols:
                continue
            sub = piv.loc[jj == j, cols].to_numpy(dtype=float)
            mx = np.nanmax(sub, axis=1, keepdims=True)
            lq[jj == j] = (mx[:, 0] + np.log(np.nanmean(np.exp(sub - mx), axis=1)))
        for cond in piv.columns:
            if cond.startswith("forced:"):
                continue
            fam = cond.split(":")[0]
            fam = {"ban": "ban", "mention": "mention", "neutral": "neutral"}.get(fam, fam)
            for j in sorted(set(jj)):
                m = jj == j
                lw = piv.loc[m, cond].to_numpy(dtype=float) - lq[m]
                lw = lw[np.isfinite(lw)]
                if len(lw) < 3:
                    continue
                M = len(lw)
                ess = kish_ess(lw)
                sig = float(np.std(lw, ddof=1))
                rows.append({"model": "meta-llama/Llama-3.1-8B-Instruct", "task": t, "condition": cond, "family": fam,
                             "j": j, "M": M, "kish_ess": ess, "cv2_plugin": M / ess - 1,
                             "M5_plugin_lower_bound": 5 * (M / ess), "sigma_logw": sig,
                             "M5_lognormal": 5 * math.exp(min(sig * sig, 700)), "khat_cell": psis_khat(lw)})
                lwn = lw - (np.log(np.mean(np.exp(lw - lw.max()))) + lw.max())
                pooled[("Llama", t, j, fam)].extend(lwn.tolist())
    return rows, pooled


def events_needed(sd_e: float, share: float, mdd: float | None = None) -> float:
    d = abs(share - 0.5) if mdd is None else mdd
    return float(((1.96 + 0.84) * sd_e / d) ** 2) if d > 0 else math.inf


# ------------------------------------------------------------------------------------------------ main
def run(n_boot: int = 2000, n_sim: int = 10000) -> dict[str, Any]:
    rows = list(iter_rows())
    cells = Cells()
    logger.info("0a(i) event table")
    ev = event_table(rows, cells)
    logger.info(f"   {len(ev['table'])} events")
    logger.info("0a(ii) implied-mass C1")
    mass = mass_c1(cells)
    logger.info(f"   rows kept {mass['n_rows_kept']} / {mass['n_rows_total']}")
    mass_boot = None
    if mass["n_rows_kept"]:
        rng = np.random.default_rng(SEED + 7)
        vals = []
        for _ in range(400):
            tw = list(rng.choice(cells.cfg.WS, 5))
            Wt = {t: cells.ca[t].boot_weights(rng) for t in ("t1", "t2")}
            m = _mass_boot_once(cells, Wt, tw)
            vals.append((m["V_u"], m["V_s"], m["SHARE"]))
        vals = np.array(vals, dtype=float)
        mass_boot = {"V_u": _intervals(vals[:, 0], mass["V_u"]), "V_s": _intervals(vals[:, 1], mass["V_s"]),
                     "SHARE": _intervals(vals[:, 2], mass["SHARE"]), "V_tot_ci": tuple(np.nanquantile(vals[:, 0] + vals[:, 1], [0.025, 0.975]))}
    protocol = read_json(dep("exp7", "results/protocol.json"))
    if mass["n_rows_kept"] == 0:
        mass_branch = "C1 not decidable on estimable mass (no row keeps >= 3 survivors with >= 1% mass and ESS >= 5)"
    else:
        bs = mass_boot or {}
        mass_branch = cells.c1.branch(bs.get("SHARE", {}).get("percentile_ci95", (math.nan, math.nan)),
                                      bs.get("V_tot_ci", (math.nan, math.nan)), None, None, False, mass["n_rows_kept"])
    logger.info("0a(iii) bootstrap vs replicate (two-stage primary)")
    prow = point_rows_with_rep(cells)
    b2 = bootstrap(cells, n_boot, two_stage=True, keep_cells=True)
    b1 = bootstrap(cells, max(200, n_boot // 4), two_stage=False)
    vr2 = variance_ratio(cells, b2, prow)
    vr1 = variance_ratio(cells, b1, prow)
    pts = {t: cells.point(t, "neutral")["share"] for t in ("t1", "t2")}
    intervals = {}
    for t in ("t1", "t2"):
        for key in ("V_u", "V_s", "SHARE"):
            intervals[f"qwen|{t}|{key}"] = _intervals(np.array([c[key] for c in b2["comps"][t]], float), pts[t][key])
    pu = np.array([a["V_u"] + b["V_u"] for a, b in zip(b2["comps"]["t1"], b2["comps"]["t2"])])
    ps = np.array([a["V_s"] + b["V_s"] for a, b in zip(b2["comps"]["t1"], b2["comps"]["t2"])])
    pV_u, pV_s = pts["t1"]["V_u"] + pts["t2"]["V_u"], pts["t1"]["V_s"] + pts["t2"]["V_s"]
    intervals["qwen|pooled|V_u"] = _intervals(pu, pV_u)
    intervals["qwen|pooled|V_s"] = _intervals(ps, pV_s)
    intervals["qwen|pooled|SHARE"] = _intervals(ps / (pu + ps), pV_s / (pV_u + pV_s))
    # Llama: recompute the basic intervals from exp10's stored point estimates and bootstrap percentiles
    bd = read_json(dep("exp10", "results/bootstrap_diagnostics.json"))
    llama_int = {}
    for k, v in bd["basic_intervals"].items():
        if k.startswith("neutral|") and any(k.endswith(x) for x in ("V_u", "V_s", "SHARE", "V_tot")):
            lo, hi = v["percentile_ci95"]
            rb = (2 * v["point"] - hi, 2 * v["point"] - lo)
            llama_int[k] = {"point": v["point"], "percentile_ci95": v["percentile_ci95"], "basic_ci95_recomputed": rb,
                            "basic_ci95_exp10": v["basic_ci95"],
                            "max_abs_diff": float(max(abs(rb[0] - v["basic_ci95"][0]), abs(rb[1] - v["basic_ci95"][1]))),
                            "basic_crosses_unit_interval": bool(k.endswith("SHARE") and (rb[0] < 0 or rb[1] > 1))}
    llama_ratio = [r["ratio"] for r in bd["bootstrap_variance_correction"]["neutral"]["per_task"]["t1"]["rows"]]
    logger.info("0a(iv) AIM null")
    c1j = read_json(dep("exp7", "results/c1.json"))
    aim_q_obs = c1j["reference_mention"]["aim_prime_veto"]["aim"]
    aim_q_neu = c1j["primary_neutral"]["aim_prime_veto"]["aim"]
    l10 = read_json(dep("exp10", "results/c1.json"))
    aim_l_obs = l10["c1"]["mention"]["pooled"]["AIM"]
    aim_l_neu = l10["c1"]["neutral"]["pooled"]["AIM"]
    vc = variance_components(cells)
    uh_q = []
    for t in ("t1", "t2"):
        for B, row in c1j["reference_mention"]["tasks"][t]["rows"].items():
            fl = np.array(list(row["fitted_ladder"].values()))
            uh_q.append(fl / row["a"] if row["a"] != 0 else fl)
    # bootstrap cell variances (single-cell L, template level) from (iii)
    bvar = defaultdict(list)
    for (t, kind, B, w), vals in b2["cellv"].items():
        V = np.array(vals)
        bvar[kind].append(float(np.nanmedian(np.nanvar(V, axis=0, ddof=1))))
    boot_cell_var = {k: float(np.median(v)) for k, v in bvar.items()}
    eq = {k: {"shared": 1.0, "is": 0.0} for k in ("ban", "mention", "neutral")}
    sim = {}
    sim["qwen_split_half_estimated"] = aim_null_sim(uh_q, vc, n_sim, "split_half")
    shared_boot = {k: {"shared": boot_cell_var.get(k, 1.0), "is": 0.0} for k in ("ban", "mention", "neutral")}
    sim["qwen_shared_cell_bootvar"] = aim_null_sim(uh_q, shared_boot, n_sim, "shared_cell")
    sim["qwen_shared_cell_equal_var"] = aim_null_sim(uh_q, eq, n_sim, "shared_cell")
    sim["placebo_independent_mention"] = aim_null_sim(uh_q, vc, n_sim, "independent_mention")
    rng = np.random.default_rng(SEED)
    uh_l = []
    for row in l10["c1"]["mention"]["per_task"]["t1"]["rows"]:
        v = rng.normal(size=len(row["survivors"]))
        v -= v.mean()
        uh_l.append(v / np.linalg.norm(v))
    sim["llama_shared_cell_equal_var"] = aim_null_sim(uh_l, eq, n_sim, "shared_cell")
    sim["llama_split_half_qwen_components"] = aim_null_sim(uh_l, vc, n_sim, "split_half")

    def q(arr: np.ndarray, x: float) -> float:
        return float(np.mean(arr <= x))

    aim = {"derivation": ("gain = L_ban - L_men, PV = L_men - L_neu. With independent cell noise of variances s_b^2, "
                          "s_m^2, s_n^2 and the SAME mention cell in both: cov(gain, PV) = -s_m^2, so the null "
                          "corr(gain, PV) = -s_m^2 / sqrt((s_b^2 + s_m^2)(s_m^2 + s_n^2)) = -0.5 at equal variances. "
                          "In exp7's split-half AIM the mention cells of the two halves share only the template-level "
                          "(prompt) component, so the bias scales with that shared variance."),
           "observed": {"qwen_mention_ref": aim_q_obs, "qwen_neutral_ref": aim_q_neu, "llama_mention_ref": aim_l_obs,
                        "llama_neutral_ref": aim_l_neu},
           "variance_components_split_half": vc, "bootstrap_cell_variance_median": boot_cell_var,
           "null": {k: {"mean": float(v.mean()), "sd": float(v.std()), "q05": float(np.quantile(v, 0.05)),
                        "q95": float(np.quantile(v, 0.95)), "n_sim": len(v)} for k, v in sim.items()},
           "observed_quantile": {"qwen_mention_ref|split_half_estimated": q(sim["qwen_split_half_estimated"], aim_q_obs),
                                 "qwen_mention_ref|shared_cell_bootvar": q(sim["qwen_shared_cell_bootvar"], aim_q_obs),
                                 "qwen_mention_ref|shared_cell_equal_var": q(sim["qwen_shared_cell_equal_var"], aim_q_obs),
                                 "llama_mention_ref|shared_cell_equal_var": q(sim["llama_shared_cell_equal_var"], aim_l_obs),
                                 "llama_mention_ref|split_half_qwen_components": q(sim["llama_split_half_qwen_components"], aim_l_obs)},
           "sources": [src("exp7", "results/c1.json"), src("exp10", "results/c1.json"), src("exp7", "src/c1.py")]}
    logger.info("0a(v) ESS-weighted share")
    ew = c1j["ess_weighted"]["tasks"]["t1"]
    sp = ew["share_point"]
    essw = {"reported_SHARE_t1": sp["SHARE"], "reported_ci": ew["bootstrap"]["SHARE_ci"],
            "V_u": sp["V_u"], "V_s": sp["V_s"], "recomputed_SHARE": sp["V_s"] / (sp["V_u"] + sp["V_s"]),
            "pooled_point": c1j["ess_weighted"]["pooled"]["share_point"],
            "pooled_ci": c1j["ess_weighted"]["pooled"]["bootstrap"]["SHARE_ci"],
            "mechanism": ("noise-corrected V terms: V_u = sum(a^2 - N_u) went negative (-35.4) after the ESS weights shrank "
                          "the ladder projection below its noise allowance, so V_s / (V_u + V_s) = 181.3 / 145.9 > 1"),
            "verdict": "impossible as a proportion", "source": src("exp7", "results/c1.json") + "#ess_weighted"}
    logger.info("0a(vi) M arithmetic")
    ma = m_arithmetic(cells)
    # event-level SHARE per row and the bench events needed
    def row_share(a2, nu, ss, ns):
        den = (a2 - nu) + (ss - ns)
        return (ss - ns) / den if den != 0 else math.nan

    q_sh = [row_share(r["a2"], r["N_u"], r["ss_s"], r["N_s"]) for t in ("t1", "t2")
            for r in c1j["primary_neutral"]["tasks"][t]["rows"].values()]
    l_sh = [row_share(r["f2"], r["noise_u"], r["s2"], r["noise_s"]) for r in l10["c1"]["neutral"]["per_task"]["t1"]["rows"]]
    sdq, sdl = float(np.nanstd(q_sh, ddof=1)), float(np.nanstd(l_sh, ddof=1))
    shq = c1j["primary_neutral"]["pooled"]["share_point"]["SHARE"]
    shl = l10["c1"]["neutral"]["pooled"]["SHARE"]
    bench = {"qwen": {"sd_event_share": sdq, "event_shares": q_sh, "observed_SHARE": shq,
                      "n_observed_dev": events_needed(sdq, shq), "n_mdd_0.10": events_needed(sdq, shq, 0.10),
                      "n_mdd_0.20": events_needed(sdq, shq, 0.20)},
             "llama": {"sd_event_share": sdl, "event_shares": l_sh, "observed_SHARE": shl,
                       "n_observed_dev": events_needed(sdl, shl), "n_mdd_0.10": events_needed(sdl, shl, 0.10),
                       "n_mdd_0.20": events_needed(sdl, shl, 0.20)}}
    out = {"event_table": ev, "mass_c1": mass, "mass_bootstrap": mass_boot, "mass_branch": mass_branch,
           "mass_prediction_stated_before": "few or no rows survive -> 'C1 not decidable on estimable mass'",
           "frozen_thresholds": {k: protocol.get(k) for k in protocol if "thresh" in k.lower() or "branch" in k.lower()},
           "variance_ratio_two_stage": vr2, "variance_ratio_one_stage": vr1, "intervals": intervals,
           "llama_intervals": llama_int, "llama_variance_ratio_exp10": {"rows": llama_ratio,
                                                                        "range": (min(llama_ratio), max(llama_ratio))},
           "aim": aim, "ess_weighted": essw, "m_arithmetic": {k: v for k, v in ma.items() if k != "cells"},
           "bench_events": bench, "n_boot": n_boot,
           "notes": ["two-stage bootstrap resamples templates then programs within algorithm-halves (random directions "
                     "fixed); exp7's own bootstrap also resampled directions",
                     "var_replicate uses exp7 c1.py's tot_noise = sum_j var_r(c_Br(j)) / R (R = 10 template x half "
                     "replicates); replicate_sd^2/5 x |S| equals 2 x tot_noise, a factor-2 difference recorded here"]}
    write_json(RESULTS / "c1_diagnostics.json", out)
    pd.DataFrame(ma["cells"]).to_csv(TABLES / "m_arithmetic_cells.csv", index=False)
    pd.DataFrame(ma["summary"]).to_csv(TABLES / "m_arithmetic.csv", index=False)
    cols = ["event", "model", "task", "banned", "ban_kind", "n_total", "n_attempted", "n_nonbanned",
            "n_correct_nonbanned", "modal_landing", "modal_landing_share", "modal_landing_wilson",
            "modal_correct_landing", "argmax_Gbar_neutral", "argmax_Gbar_neutral_value", "argmax_s_neutral",
            "argmax_s_neutral_value", "argmax_mass", "argmax_mass_value", "argmax_Gbar_mention", "argmax_s_mention",
            "argmax_G_exp8_arm_a", "rank_landing_Gbar_neutral", "rank_landing_s_neutral", "rank_landing_mass",
            "hit_Gbar_neutral", "hit_s_neutral", "hit_mass", "hit_Gbar_mention", "hit_s_mention",
            "attempted_counts", "correct_nonbanned_counts", "median_ess_per_survivor", "source", "reference_source"]
    df = pd.DataFrame(ev["table"])
    df[[c for c in cols if c in df.columns]].to_csv(TABLES / "c1_argmax_vs_landing.csv", index=False)
    logger.info("0a written")
    return out


def _mass_boot_once(cells: Cells, Wt: dict[str, np.ndarray], tw: list[str]) -> dict[str, Any]:
    return mass_c1(cells, W=Wt, templates=tw)
