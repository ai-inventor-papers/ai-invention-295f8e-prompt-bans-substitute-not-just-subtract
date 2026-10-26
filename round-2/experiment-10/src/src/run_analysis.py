#!/usr/bin/env python3
"""S6 driver (frozen with src/analysis_c1.py in commitments.log): loads the score matrices, writes frlp/cells.jsonl and
per-task score parquet files, and computes collapse (6.1), sampled events (6.2), the FRLP gate (6.3), C1 under both
references with the template x implementation bootstrap (6.4-6.9), cosine table (6.10), route test (6.11) and the
sensitivity block (6.12). Results go to results/*.json; figures are drawn by src/figures.py."""

from __future__ import annotations

import collections
import json
import time
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from src.ws import C, DATA, FRLP_DIR, MODEL_TAG, RESULTS, read_jsonl, setup_logging, write_json
from src import analysis_c1 as A

TASKS = ("t1", "t2")
VARIANTS = ("full", "body", "gen_proposal", "exp1_5tpl", "correct_only")


# ------------------------------------------------------------------------------------------------ loading
def load_task(task: str) -> A.TaskData:
    sel = json.loads((RESULTS / "selections.json").read_text())
    summ = json.loads((RESULTS / "forced_set_summary.json").read_text())["per_algorithm"]
    fs = [r for r in read_jsonl(DATA / "forced_set.jsonl") if r["task"] == task and r["scrub_mode"] != "dropped"
          and not summ[f"{task}:{r['j']}"]["excluded_M_lt_10"]]
    order = list(C.MODES[task])
    algs = [j for j in order if any(r["j"] == j for r in fs)]
    fs.sort(key=lambda r: (algs.index(r["j"]), r["half"], r["program_id"]))
    prog = pd.DataFrame([{"program_id": r["program_id"], "j": r["j"], "half": r["half"], "passed": r["passed"],
                          "generating_cond": r["generating_cond"], "n_tokens": r["n_tokens"]} for r in fs])
    parts = sorted((FRLP_DIR / "parts" / task).glob("*.parquet"))
    df = pd.concat([pd.read_parquet(p, columns=["program_id", "cond", "l_full", "l_body", "n_tokens"]) for p in parts],
                   ignore_index=True)
    df = df[df["program_id"].isin(set(prog["program_id"]))]
    conds = sorted(df["cond"].unique())
    pf = df.pivot_table(index="program_id", columns="cond", values="l_full", aggfunc="first")
    pb = df.pivot_table(index="program_id", columns="cond", values="l_body", aggfunc="first")
    pf = pf.reindex(index=prog["program_id"], columns=conds)
    pb = pb.reindex(index=prog["program_id"], columns=conds)
    sub = sel[f"{task}_substitute"]["s_star"] if f"{task}_substitute" in sel else None
    return A.TaskData(task=task, algs=algs, d=sel[f"{task}_default"], s_star=sub, prog=prog, conds=conds,
                      lf=pf.to_numpy(dtype=float), lb=pb.to_numpy(dtype=float))


def disputed_rows() -> set[str]:
    p = RESULTS / "llama_label_audit.json"
    return set(json.loads(p.read_text()).get("disputed_row_ids", [])) if p.exists() else set()


def variant_cells(td: A.TaskData, variant: str, counts: np.ndarray | None = None) -> A.Cells:
    base = variant if variant not in ("correct_only", "audit_disputed_removed") else "full"
    D = A.importance(td, base)
    mask = None
    if variant == "correct_only":
        mask = td.prog["passed"].to_numpy(dtype=float)
    elif variant == "audit_disputed_removed":  # plan S1: audit agreement < 0.9 -> C1 without the disputed forced programs
        bad = disputed_rows()
        mask = np.array([0.0 if pid.split("|", 2)[2] in bad else 1.0 for pid in td.prog["program_id"]])
    return A.make_cells(td, D, counts=counts, mask=mask)


def cond_meta(cond: str) -> dict[str, Any]:
    parts = cond.split(":")
    out = {"template": None, "half": None}
    for p in parts[1:]:
        if p.startswith("w") and p[1:].isdigit():
            out["template"] = int(p[1:])
        elif p.startswith("h") and p[1:].isdigit():
            out["half"] = int(p[1:])
        elif p.startswith("s") and p[1:].isdigit():
            out["template"] = f"s{p[1:]}"
        elif p.startswith("p") and p[1:].isdigit():
            out["template"] = f"p{p[1:]}"
        elif p.startswith("k") and p[1:].isdigit():
            out["template"] = f"k{p[1:]}"
    return out


def write_cells(tds: dict[str, A.TaskData]) -> None:
    rows = []
    for task, td in tds.items():
        for variant in VARIANTS:
            cl = variant_cells(td, variant)
            for ci, cond in enumerate(td.conds):
                if cond.startswith("forced"):
                    continue
                m = cond_meta(cond)
                for j, a in enumerate(td.algs):
                    hs = [m["half"]] if m["half"] else [None, 1, 2]
                    for h in hs:
                        if h is None:
                            L, e, n = cl.La[j, ci], cl.ESSa[j, ci], int(cl.Nh[j].sum())
                        else:
                            L, e, n = cl.Lh[j, h - 1, ci], cl.ESSh[j, h - 1, ci], int(cl.Nh[j, h - 1])
                        if np.isnan(L):
                            continue
                        rows.append({"task": task, "model": MODEL_TAG, "condition": cond, "template": m["template"],
                                     "algorithm": a, "L": float(L), "ess": float(e), "n_programs": n,
                                     "half": h if h else "all", "variant": variant})
    C.write_jsonl(FRLP_DIR / "cells.jsonl", rows)
    # per-program score matrices (long format) for audit/rederive.py
    for task, td in tds.items():
        long = []
        for ci, cond in enumerate(td.conds):
            for r in range(len(td.prog)):
                if not np.isnan(td.lf[r, ci]):
                    long.append((td.prog["program_id"].iat[r], cond, td.lf[r, ci], td.lb[r, ci]))
        pd.DataFrame(long, columns=["program_id", "condition_id", "l_full", "l_body"]).merge(
            td.prog[["program_id", "n_tokens"]], on="program_id").to_parquet(FRLP_DIR / f"scores_{task}.parquet", index=False)
    logger.info(f"cells.jsonl: {len(rows)} rows")


# ------------------------------------------------------------------------------------------------ 6.1 / 6.2
def collapse(lab: list[dict[str, Any]]) -> dict[str, Any]:
    out = {}
    for task in TASKS:
        rs = [r for r in lab if r["task"] == task and r["kind"] == "baseline"]
        att = [r for r in rs if r["label"] != "no_code"]
        cor = [r for r in att if r["passed"]]
        ca = collections.Counter(r["label"] for r in att)
        cc = collections.Counter(r["label"] for r in cor)
        p = np.array(list(cc.values()), dtype=float)
        hill1 = float(np.exp(-np.sum((p / p.sum()) * np.log(p / p.sum())))) if p.sum() > 0 else None
        mode, nm = ca.most_common(1)[0]
        mc = cc.get(mode, 0)
        out[task] = {"N": len(rs), "attempted": len(att), "no_code": len(rs) - len(att), "attempted_counts": dict(ca),
                     "pass_rate": len(cor) / max(1, len(rs)), "pass_rate_wilson": C.wilson_ci(len(cor), len(rs)),
                     "correct_counts": dict(cc), "hill1_correct": hill1, "modal_label": mode,
                     "modal_share_attempted": nm / max(1, len(att)), "modal_share_wilson": C.wilson_ci(nm, len(att)),
                     "modal_share_correct": mc / max(1, len(cor)), "modal_share_correct_wilson": C.wilson_ci(mc, len(cor)),
                     "non_collapsed_flag": nm / max(1, len(att)) < 0.9}
    return out


def events(lab: list[dict[str, Any]], sel: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for task in TASKS:
        d = sel[f"{task}_default"]
        s = sel[f"{task}_substitute"]["s_star"]
        evs = [("baseline", lambda r: r["kind"] == "baseline", []),
               (f"ban:{d} (modal)", lambda r, d=d: r["kind"] == "ban" and r["X"] == d and r["phase"] == "A4", [d]),
               (f"mention:{d}", lambda r, d=d: r["kind"] == "mention" and r["X"] == d, []),
               ("listall", lambda r: r["kind"] == "listall", [])]
        for x in sel.get(f"{task}_nondefault_bans", []):
            evs.append((f"ban:{x} (non-default)", lambda r, x=x: r["kind"] == "ban" and r["X"] == x and r["phase"] == "C", [x]))
        evs.append((f"twostep:{d}+{s}", lambda r: r["kind"] == "twostep", [d, s]))
        out[task] = []
        for name, f, banned in evs:
            rs = [r for r in lab if r["task"] == task and f(r)]
            att = [r for r in rs if r["label"] != "no_code"]
            nb = [r for r in att if r["label"] not in banned]
            c_att = collections.Counter(r["label"] for r in att)
            c_nb = collections.Counter(r["label"] for r in nb)
            banned_share = (len(att) - len(nb)) / max(1, len(att))
            top = c_nb.most_common(2)
            mode = top[0][0] if top else None
            lead = (top[0][1] - (top[1][1] if len(top) > 1 else 0)) / max(1, len(nb)) if top else 0.0
            clear = bool(top) and lead >= A.EVENT_GATE["clear_margin"] and mode != "other"
            comp = sum(1 for r in rs if r["passed"] and r["label"] not in banned and r["label"] != "no_code")
            ev = {"name": name, "task": task, "N": len(rs), "no_code": len(rs) - len(att), "attempted_counts": dict(c_att),
                  "banned": banned, "banned_share": banned_share, "avoidance": 1 - banned_share,
                  "compliant_share": comp / max(1, len(rs)), "compliant_wilson": C.wilson_ci(comp, len(rs)),
                  "n_attempted_nonbanned": len(nb), "nonbanned_counts": dict(c_nb), "mode": mode, "mode_lead": lead,
                  "clear_mode": clear,
                  "event_gate": bool((1 - banned_share) >= A.EVENT_GATE["avoidance"] and len(nb) >= A.EVENT_GATE["min_nonbanned"]),
                  "landing_wilson": {k: C.wilson_ci(v, len(att)) for k, v in c_att.items()},
                  "conds": sorted({r["condition"] for r in rs}),
                  "samples": [{"cond": r["condition"], "label": r["label"], "row_id": r["row_id"]} for r in rs]}
            out[task].append(ev)
    return out


def association(sel: dict[str, Any]) -> dict[str, dict[str, dict[str, int]]]:
    fr = read_jsonl(DATA / "free_answers.jsonl")
    out: dict[str, dict[str, dict[str, int]]] = {}
    for task in TASKS:
        out[task] = {}
        for r in fr:
            if r["task"] == task:
                out[task].setdefault(r["X"], collections.Counter())[r["label"]] += 1
        out[task] = {x: dict(c) for x, c in out[task].items()}
    _ = sel
    return out


# ------------------------------------------------------------------------------------------------ proximity
def norm_tokens(code: str) -> list[str]:
    import io
    import keyword
    import tokenize

    out = []
    try:
        for t in tokenize.generate_tokens(io.StringIO(code).readline):
            if t.type == tokenize.NAME:
                out.append(t.string if keyword.iskeyword(t.string) or t.string in dir(__builtins__) else "ID")
            elif t.type == tokenize.NUMBER:
                out.append("NUM")
            elif t.type == tokenize.STRING:
                out.append("STR")
            elif t.type == tokenize.OP:
                out.append(t.string)
            elif t.type in (tokenize.INDENT, tokenize.DEDENT, tokenize.NEWLINE):
                out.append(tokenize.tok_name[t.type])
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return out


def proximity(td: A.TaskData, lab: list[dict[str, Any]]) -> dict[str, Any]:
    from rapidfuzz.distance import Levenshtein

    fs = {r["program_id"]: r for r in read_jsonl(DATA / "forced_set.jsonl") if r["task"] == td.task}
    toks = {a: [norm_tokens(fs[p]["code_scrubbed"]) for p in td.prog["program_id"][td.prog["j"] == a]] for a in td.algs}
    nat = [norm_tokens(r["code"]) for r in lab if r["task"] == td.task and r["kind"] == "baseline"
           and r["label"] == td.d and r.get("code")][:30]

    def mdist(A_: list[list[str]], B_: list[list[str]]) -> float:
        return float(np.mean([Levenshtein.normalized_distance(a, b) for a in A_ for b in B_]))

    P = {X: {j: -mdist(toks[X], toks[j]) for j in td.algs if j != X} for X in td.algs}
    Pd = {j: -mdist(nat, toks[j]) for j in td.algs} if nat else {}
    return {"P_forced": P, "P_from_default_natural": Pd, "n_default_natural": len(nat)}


# ------------------------------------------------------------------------------------------------ C1 bundle
def c1_bundle(views: dict[str, A.View], assoc: dict[str, Any], **kw: Any) -> dict[str, Any]:
    out = {}
    for ref in ("neutral", "mention"):
        per = {t: A.c1_task(v, ref=ref, assoc=assoc.get(t), **kw) for t, v in views.items()}
        out[ref] = {"per_task": per, "pooled": A.pool(list(per.values()))}
    return out


def summarise(res: dict[str, Any]) -> dict[str, Any]:
    return {ref: {"pooled": {k: res[ref]["pooled"][k] for k in ("V_u", "V_s", "V_tot", "SHARE", "AIM", "AIM_assoc", "n_rows")},
                  **{t: {k: r[k] for k in ("V_u", "V_s", "V_tot", "SHARE", "AIM", "AIM_assoc", "n_rows")}
                     for t, r in res[ref]["per_task"].items()}} for ref in res}


def bootstrap(tds: dict[str, A.TaskData], assoc: dict[str, Any], B: int, variant: str = "full", seed: int = 0,
              **kw: Any) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    keys = ("V_u", "V_s", "V_tot", "SHARE", "AIM", "AIM_assoc")
    acc: dict[str, list[float]] = collections.defaultdict(list)
    route: dict[str, list[float]] = collections.defaultdict(list)
    rows_acc: dict[str, list[np.ndarray]] = collections.defaultdict(list)  # post-hoc diagnostic: per-row gbar draws
    for b in range(B):
        tw = list(rng.integers(1, 6, size=5))
        views = {}
        for t, td in tds.items():
            cnt = A.boot_counts(td, rng)
            views[t] = A.View(td, variant_cells(td, variant, counts=cnt), tw)
        res = c1_bundle(views, assoc, **kw)
        for ref in res:
            for k in keys:
                acc[f"{ref}|pooled|{k}"].append(res[ref]["pooled"][k] if res[ref]["pooled"][k] is not None else np.nan)
                for t in res[ref]["per_task"]:
                    vv = res[ref]["per_task"][t][k]
                    acc[f"{ref}|{t}|{k}"].append(vv if vv is not None else np.nan)
        for ref in res:
            for t, r_ in res[ref]["per_task"].items():
                for row in r_["rows"]:
                    rows_acc[f"{ref}|{t}|{row['X']}|{','.join(row['survivors'])}"].append(np.asarray(row["gbar"]))
        rt = A.route_numbers(list(views.values()))
        if rt:
            for k in ("F_direct", "F_prompt", "interaction"):
                route[k].append(rt[k])
    out = {k: {"ci95": A.ci(v), "mean": float(np.nanmean(v)) if np.any(~np.isnan(np.asarray(v, dtype=float))) else None,
               "n": int(np.sum(~np.isnan(np.asarray(v, dtype=float))))} for k, v in acc.items()}
    out["route"] = {k: {"ci95": A.ci(v)} for k, v in route.items()}
    out["_row_gbar_draws"] = rows_acc
    return out


def bootstrap_diagnostics(boot: dict[str, Any], res: dict[str, Any], views: dict[str, A.View]) -> dict[str, Any]:
    """POST-HOC diagnostics (not part of the frozen decision rule): (i) bootstrap bias and basic (reverse-percentile)
    intervals of the quadratic C1 statistics, whose percentile intervals are shifted upward when program resampling --
    shared by the 5 templates of a half -- adds variance the exchangeable-replicate Sigma cannot see; (ii) a
    bootstrap-variance noise correction: V computed with Var_boot(gbar) (programs + templates) in place of Sigma."""
    draws = boot.get("_row_gbar_draws", {})
    out: dict[str, Any] = {"basic_intervals": {}, "bootstrap_variance_correction": {}}
    for key, v in boot.items():
        if key.startswith("_") or key == "route" or not isinstance(v, dict) or "ci95" not in v:
            continue
        ref, scope, stat = key.split("|")
        obs = (res[ref]["pooled"] if scope == "pooled" else res[ref]["per_task"][scope]).get(stat)
        if obs is None or v["mean"] is None or (isinstance(obs, float) and np.isnan(obs)):
            continue
        lo, hi = v["ci95"]
        out["basic_intervals"][key] = {"point": obs, "boot_mean": v["mean"], "bias": v["mean"] - obs,
                                       "percentile_ci95": [lo, hi], "basic_ci95": [2 * obs - hi, 2 * obs - lo]}
    for ref in res:
        tot = {"V_u": 0.0, "V_s": 0.0, "V_tot": 0.0}
        per = {}
        for t, r_ in res[ref]["per_task"].items():
            u = views[t].u()
            tt = {"V_u": 0.0, "V_s": 0.0, "V_tot": 0.0, "rows": []}
            for row in r_["rows"]:
                key = f"{ref}|{t}|{row['X']}|{','.join(row['survivors'])}"
                dr = np.array(draws.get(key, []))
                if len(dr) < 10:
                    continue
                Vb = np.cov(dr.T, ddof=1)
                g = np.asarray(row["gbar"])
                vh = A.unit(A.centre(u[[views[t].td.algs.index(j) for j in row["survivors"]]]))
                a_ = float(g @ vh)
                nu = float(vh @ Vb @ vh)
                trV = float(np.trace(Vb))
                tt["V_u"] += a_ * a_ - nu
                tt["V_s"] += float(g @ g) - a_ * a_ - (trV - nu)
                tt["V_tot"] += float(g @ g) - trV
                tt["rows"].append({"X": row["X"], "trace_boot_var": trV, "trace_replicate_Sigma": row["trSigma"],
                                   "ratio": trV / row["trSigma"] if row["trSigma"] > 0 else None})
            tt["SHARE"] = A.clip_share(tt["V_u"], tt["V_s"])
            per[t] = tt
            for k in tot:
                tot[k] += tt[k]
        tot["SHARE"] = A.clip_share(tot["V_u"], tot["V_s"])
        out["bootstrap_variance_correction"][ref] = {"per_task": per, "pooled": tot}
    out["note"] = ("post-hoc: the frozen branch uses the percentile intervals; these diagnostics quantify how much of the "
                   "between-survivor gain variance the program-level (importance-sampling) noise can explain")
    return out


def aim_nulls(res: dict[str, Any], ref: str) -> dict[str, Any]:
    rows_by_task = {t: r["rows"] for t, r in res[ref]["per_task"].items()}
    out = {}
    all_pv, all_a = [], []
    for t, rows in rows_by_task.items():
        vals_pv, vals_a = [], []
        for row in rows:
            s1, s2 = row["s_half"][1], row["s_half"][2]
            p1, p2 = row["pv_half"][1], row["pv_half"][2]
            vals_pv.append(A.row_null(s1, s2, p1, p2))
            if row.get("A_vec") is not None:
                vals_a.append(A.row_null_single(s1, s2, row["A_vec"]))
        all_pv += vals_pv
        all_a += vals_a
        nl = A.pooled_null(vals_pv)
        obs = res[ref]["per_task"][t]["AIM"]
        out[t] = {"prime_and_veto": {"observed": obs, "null_method": nl.get("method"), "null_q95": nl.get("q95"),
                                     "p": A.null_p(nl, obs), "pass": bool(nl.get("q95") is not None and obs is not None
                                                                          and not np.isnan(obs) and obs > nl["q95"])}}
        if vals_a:
            na = A.pooled_null(vals_a)
            oa = res[ref]["per_task"][t]["AIM_assoc"]
            out[t]["association"] = {"observed": oa, "null_q95": na.get("q95"), "p": A.null_p(na, oa),
                                     "pass": bool(na.get("q95") is not None and oa is not None and oa > na["q95"])}
    nl = A.pooled_null(all_pv)
    obs = res[ref]["pooled"]["AIM"]
    out["pooled"] = {"prime_and_veto": {"observed": obs, "null_method": nl.get("method"), "null_q95": nl.get("q95"),
                                        "p": A.null_p(nl, obs), "pass": bool(nl.get("q95") is not None and obs is not None
                                                                             and not np.isnan(obs) and obs > nl["q95"]),
                                        "null_support": nl.get("support"), "null_pmf": nl.get("pmf")}}
    if all_a:
        na = A.pooled_null(all_a)
        oa = res[ref]["pooled"]["AIM_assoc"]
        out["pooled"]["association"] = {"observed": oa, "null_q95": na.get("q95"), "p": A.null_p(na, oa),
                                        "pass": bool(na.get("q95") is not None and oa is not None and oa > na["q95"])}
    return out


def attach_assoc_vectors(res: dict[str, Any], assoc: dict[str, Any]) -> None:
    for ref in res:
        for t, r in res[ref]["per_task"].items():
            for row in r["rows"]:
                cnt = assoc.get(t, {}).get(row["X"], {})
                nA = np.array([cnt.get(j, 0) for j in row["survivors"]], dtype=float)
                row["A_vec"] = (nA + 1.0) / (nA.sum() + len(row["survivors"]))


@logger.catch(reraise=True)
def main(B: int = A.B_DEFAULT, B_sens: int = 400) -> None:
    setup_logging("s6_analysis")
    t0 = time.time()
    sel = json.loads((RESULTS / "selections.json").read_text())
    lab = read_jsonl(DATA / "labelled.jsonl")
    tds = {t: load_task(t) for t in TASKS}
    for t, td in tds.items():
        logger.info(f"{t}: algs={td.algs} programs={len(td.prog)} conds={len(td.conds)} d={td.d} s*={td.s_star}")
    write_cells(tds)
    col = collapse(lab)
    evs = events(lab, sel)
    assoc = association(sel)
    views = {t: A.View(td, variant_cells(td, "full")) for t, td in tds.items()}
    gate = A.frlp_gate(views, {t: evs[t] for t in TASKS}, col)
    # ESS histogram (primary cells)
    cl = [r for r in read_jsonl(FRLP_DIR / "cells.jsonl") if r["variant"] == "full"]
    ess = np.array([r["ess"] for r in cl])
    gate["ess_summary"] = {"n_cells": len(ess), "median": float(np.median(ess)), "share_below_5": float(np.mean(ess < 5)),
                           "hist_edges": [1, 2, 3, 5, 10, 15, 20, 31], "hist": np.histogram(ess, bins=[1, 2, 3, 5, 10, 15, 20, 31])[0].tolist()}
    gate["coverage"] = json.loads((RESULTS / "coverage.json").read_text())
    logger.info(f"FRLP gate: a={gate['a_pass']} b={gate['b_pass']} ({gate['b_mean_delta']}) c={gate['c_pass']} "
                f"({gate['c_hit_rate']}) -> GATE={gate['GATE']}")
    # ---- C1 (observed)
    res = {}
    for ref in ("neutral", "mention"):
        per = {t: A.c1_task(v, ref=ref, assoc=assoc.get(t), want_rows=True) for t, v in views.items()}
        res[ref] = {"per_task": per, "pooled": A.pool(list(per.values()))}
    attach_assoc_vectors(res, assoc)
    nulls = {ref: aim_nulls(res, ref) for ref in res}
    ladders = {t: A.ladder_exists(v) for t, v in views.items()}
    boot = bootstrap(tds, assoc, B)
    logger.info(f"bootstrap B={B} done ({time.time() - t0:.0f}s)")
    diag = bootstrap_diagnostics(boot, res, views)
    boot.pop("_row_gbar_draws", None)
    write_json(RESULTS / "bootstrap_diagnostics.json", A.jsonable(diag))
    # ---- branches
    branches: dict[str, Any] = {}
    for ref in res:
        branches[ref] = {}
        for scope in list(res[ref]["per_task"].keys()) + ["pooled"]:
            r = res[ref]["pooled"] if scope == "pooled" else res[ref]["per_task"][scope]
            if r["n_rows"] == 0:
                branches[ref][scope] = {"branch": "not computable (no row with >= 3 survivors)"}
                continue
            sc = boot[f"{ref}|{scope}|SHARE"]["ci95"]
            vc = boot[f"{ref}|{scope}|V_tot"]["ci95"]
            nl = nulls[ref][scope]
            lad = ladders[scope]["ladder_exists"] if scope != "pooled" else all(
                ladders[t]["ladder_exists"] for t in res[ref]["per_task"] if res[ref]["per_task"][t]["n_rows"] > 0)
            br = A.branch(sc, vc, nl["prime_and_veto"]["pass"], nl.get("association", {}).get("pass", False), lad)
            branches[ref][scope] = {"branch": br, "SHARE": r["SHARE"], "SHARE_ci95": sc, "V_tot": r["V_tot"],
                                    "V_tot_ci95": vc, "V_u": r["V_u"], "V_s": r["V_s"],
                                    "V_u_ci95": boot[f"{ref}|{scope}|V_u"]["ci95"],
                                    "V_s_ci95": boot[f"{ref}|{scope}|V_s"]["ci95"], "AIM": r["AIM"],
                                    "AIM_ci95": boot[f"{ref}|{scope}|AIM"]["ci95"], "AIM_null": nl, "ladder_exists": lad,
                                    "n_rows": r["n_rows"]}
    for scope in branches["neutral"]:
        a_, b_ = branches["neutral"][scope]["branch"], branches["mention"].get(scope, {}).get("branch")
        branches["neutral"][scope]["robust"] = bool(a_ == b_)
    # ---- cosine, route, proximity
    cos = {t: A.cosine_table(views[t], res["neutral"]["per_task"][t]["rows"]) for t in TASKS}
    route = A.route_numbers(list(views.values()))
    if route:
        route["bootstrap"] = boot.get("route")
        route["label"] = "FRLP-only, descriptive (2 events)"
    prox = {t: proximity(tds[t], lab) for t in TASKS}
    for t in TASKS:
        for row in res["neutral"]["per_task"][t]["rows"]:
            S = row["survivors"]
            pX = prox[t]["P_forced"][row["X"]]
            row["proximity_spearman_s"] = A.spearman(row["s"], np.array([pX[j] for j in S]))
            if prox[t]["P_from_default_natural"]:
                row["proximity_default_spearman_s"] = A.spearman(row["s"], np.array([prox[t]["P_from_default_natural"][j] for j in S]))
    # ---- sensitivities (point estimates + B_sens bootstrap of the neutral-reference SHARE)
    sens: dict[str, Any] = {}
    specs = {"correct_only": ("correct_only", {}), "gen_proposal": ("gen_proposal", {}), "exp1_5tpl": ("exp1_5tpl", {}),
             "body_only": ("body", {}), "unweighted": ("full", {"weighted": False}), "isotropic_noise": ("full", {"iso": True}),
             "raw_mean_u": ("full", {"raw_u": True}), "flagged_cells_dropped": ("full", {"drop_flagged": True}),
             "default_ceiling": ("full", {"drop_default": True}),
             "template_mean_noise": ("full", {"noise": "template_mean"}),
             "audit_disputed_removed": ("audit_disputed_removed", {})}
    for name, (variant, kw) in specs.items():
        try:
            vv = {t: A.View(td, variant_cells(td, variant)) for t, td in tds.items()}
            r = c1_bundle(vv, assoc, **kw)
            bs = bootstrap(tds, assoc, B_sens, variant=variant, seed=1, **kw)
            bs.pop("_row_gbar_draws", None)
            sens[name] = {"point": summarise(r), "SHARE_ci95_neutral_pooled": bs["neutral|pooled|SHARE"]["ci95"],
                          "V_tot_ci95_neutral_pooled": bs["neutral|pooled|V_tot"]["ci95"], "B": B_sens}
            if variant != "full":
                sens[name]["gate"] = {k: v for k, v in A.frlp_gate(vv, {t: evs[t] for t in TASKS}, col).items()
                                      if k in ("a_pass", "b_pass", "b_mean_delta", "c_pass", "c_hit_rate", "GATE")}
        except (ValueError, KeyError, IndexError, ZeroDivisionError) as e:
            logger.error(f"sensitivity {name} failed: {e}")
            sens[name] = {"error": str(e)}
    # free-form: local Llama vs exp1's OpenRouter Llama (by mode key)
    sens["freeform_vs_exp1_openrouter_llama"] = freeform_compare(assoc)
    # ---- write
    write_json(RESULTS / "collapse.json", col)
    write_json(RESULTS / "events.json", A.jsonable({t: [{k: v for k, v in e.items() if k != "samples"} for e in evs[t]] for t in TASKS}))
    write_json(RESULTS / "frlp_gate.json", A.jsonable(gate))
    c1_out = {ref: {"per_task": {t: {**{k: v for k, v in r.items() if k != "rows"},
                                     "rows": [{k: v for k, v in row.items() if k not in ("s_half", "pv_half")} for row in r["rows"]]}
                                 for t, r in res[ref]["per_task"].items()}, "pooled": res[ref]["pooled"]} for ref in res}
    write_json(RESULTS / "c1.json", A.jsonable({"c1": c1_out, "aim_nulls": {ref: {s: {k: (v if k != "prime_and_veto" else {kk: vv for kk, vv in v.items() if kk not in ("null_support", "null_pmf")}) for k, v in d_.items()} for s, d_ in n_.items()} for ref, n_ in nulls.items()},
                                                "branches": branches, "bootstrap": boot, "ladder": ladders, "cosine": cos,
                                                "route": route, "proximity": prox, "association_counts": assoc,
                                                "B": B, "seed": 0}))
    pn = nulls["neutral"]["pooled"]["prime_and_veto"]
    write_json(RESULTS / "aim_null_pooled.json", A.jsonable({"support": pn.get("null_support"), "pmf": pn.get("null_pmf"),
                                                             "observed": pn["observed"], "q95": pn["null_q95"]}))
    write_json(RESULTS / "sensitivities.json", A.jsonable(sens))
    logger.info(f"branches: { {ref: {s: b['branch'] for s, b in br.items()} for ref, br in branches.items()} }")
    logger.info(f"S6 done in {time.time() - t0:.0f}s")


def freeform_compare(assoc: dict[str, Any]) -> dict[str, Any]:
    from src.names import parse_free
    from src.ws import CANON

    ext = read_jsonl(CANON / "elicitation" / "ext_freetext.jsonl")
    out = {}
    for task in TASKS:
        out[task] = {}
        for x, cnt in assoc[task].items():
            mine = max(cnt, key=cnt.get) if cnt else None
            rows = [r for r in ext if r.get("task") == task and r.get("mode_X") == x]  # exp1 schema: mode_X, raw, parsed
            labels = collections.Counter()
            for r in rows:
                labels[parse_free(r.get("raw") or "", task, x)] += 1  # re-parsed with the v2 name table (by mode key)
            theirs = labels.most_common(1)[0][0] if labels else None
            out[task][x] = {"local_top1": mine, "exp1_openrouter_top1": theirs, "agree": mine == theirs if theirs else None,
                            "n_exp1": sum(labels.values()), "exp1_counts": dict(labels), "local_counts": cnt}
    vals = [v["agree"] for t in out for v in out[t].values() if v["agree"] is not None]
    out["top1_agreement"] = float(np.mean(vals)) if vals else None
    return out


if __name__ == "__main__":
    main()
