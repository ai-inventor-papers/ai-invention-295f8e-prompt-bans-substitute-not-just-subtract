#!/usr/bin/env python3
"""(G3, 0c-0g) Harmonisation, cross-experiment perturbation table, record corrections, one-statistic knob table,
PREDICT on gated events, BUY quotes, seeds, missing outputs and sham-ban promotions.

Every number is recomputed from the iteration-1 sample files and cited as expN/<relative path>[#filter].
Usage: uv run tables.py
"""
from __future__ import annotations

import ast as pyast
import json
import math
import re
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
from loguru import logger

from common import (CATALOGUE, DEFAULT, EXP, RES, RUNNER_UP, TAB, UNMAPPED, clean, clopper_pearson, fisher_p,
                    h_label, h_task, jdump, newcombe, prop, read_jsonl, setup_logging, to_bool, wilson)

# extra raw-name synonyms seen in the iteration-1 files (logged in harmonise.json)
EXTRA = {"T1": {"astar_gbfs": "ASTAR", "astar_greedy": "ASTAR", "bibfs": "BIDIR_BFS", "bidirectional_bfs": "BIDIR_BFS",
                "dijkstra": "UNIT_DIJKSTRA", "a_star": "ASTAR", "other": "OTHER", "no_code": "NOT_ATTEMPTED",
                "unparseable": "NOT_ATTEMPTED"},
         "T2": {"bf_spfa": "BF_SPFA", "floyd": "FW", "bidijkstra": "BIDIR_DIJKSTRA", "bidirectional_dijkstra": "BIDIR_DIJKSTRA",
                "other": "OTHER", "no_code": "NOT_ATTEMPTED", "unparseable": "NOT_ATTEMPTED", "other:dag_dp": "DAG_DP"}}
RAW_SEEN: dict[str, Counter] = defaultdict(Counter)


def H(task: str, raw) -> str:
    s = None if raw is None else str(raw).strip()
    RAW_SEEN[task][s] += 1
    if s is None or s in ("None", "nan", ""):
        return "NOT_ATTEMPTED"
    k = s.lower()
    if k in EXTRA[task]:
        return EXTRA[task][k]
    if k.startswith("other"):
        return "OTHER"
    return h_label(task, s)


def parse_list(v) -> list:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    s = str(v)
    try:
        return list(pyast.literal_eval(s))
    except (ValueError, SyntaxError):
        return [x.strip() for x in s.strip("[]").split(",") if x.strip()]


def parse_dict(v) -> dict:
    if isinstance(v, dict):
        return v
    try:
        return json.loads(v)
    except (TypeError, json.JSONDecodeError):
        try:
            return pyast.literal_eval(str(v))
        except (ValueError, SyntaxError):
            return {}


# ===================================================================================== load + harmonise samples
def load_all() -> pd.DataFrame:
    recs = []

    def add(exp, src, r, task, cond, ctype, engine, decoding, banned, label, ref, filt):
        lab = H(task, label)
        rt = H(task, r.get("runtime_label", r.get("rt_label", r.get("label_runtime"))))
        at = H(task, r.get("ast_label", r.get("label_ast")))
        passed = to_bool(r.get("passed"))
        recs.append({"exp": exp, "src": src, "task": task, "cond": cond, "type": ctype, "engine": engine,
                     "decoding": decoding, "banned": tuple(sorted(banned)), "label": lab, "raw_label": r.get("label"),
                     "attempted": lab != "NOT_ATTEMPTED", "correct": bool(passed) if passed is not None else False,
                     "rt": rt, "ast": at, "pid": str(r.get("paraphrase_id")), "ref": ref, "filter": filt,
                     "fail": failure_kind(exp, r), "code_present": lab != "NOT_ATTEMPTED"})

    # ---------------- exp1
    sham1 = {"T1": {"ban:astar_gbfs", "ban:bibfs", "ban:dfs", "ban:dijkstra", "ban:iddfs"},
             "T2": {"ban:bf_spfa", "ban:bidijkstra", "ban:dial", "ban:floyd"}}
    for r in read_jsonl(EXP["exp1"] / "data" / "samples.jsonl"):
        t = h_task(r["task"])
        c = r["condition"]
        banned = [H(t, x) for x in parse_list(r.get("banned_set"))]
        if c == "baseline":
            ty, ref = "baseline", None
        elif c == "baseline_T13":
            ty, ref = "temperature", "baseline"
        elif c == "baseline_empty":
            ty, ref = "other", "baseline"
        elif c.startswith("forced:"):
            ty, ref = "forced", "baseline"
        elif c == "listall":
            ty, ref = "listall", "baseline"
        elif c.startswith("mention:"):
            ty, ref = "mention", "baseline"
        elif c.startswith("succession"):
            ty, ref = "ban_cumulative", "baseline"
        elif c in sham1[t]:
            ty, ref = "sham_ban", "baseline"
        else:
            ty, ref = "ban_single", "baseline"
        add("exp1", "data/samples.jsonl", r, t, c, ty, "vllm", r.get("decoding"), banned, r.get("label"), ref,
            f"condition=={c}")
    # ---------------- exp2
    for ph in ("A", "C", "D"):
        for r in read_jsonl(EXP["exp2"] / "data" / f"samples_phase{ph}.jsonl"):
            t = h_task(r["task"])
            c = r["condition"]
            banned = []
            if c.startswith("ban:"):
                banned = [H(t, x) for x in c[4:].split("+")]
            if c == "baseline":
                ty, ref = "baseline", None
            elif c.startswith("forced:"):
                ty, ref = "forced", "baseline"
            elif c.startswith("masked:"):
                ty, ref = "other", "baseline"
            elif c.startswith("mention:"):
                ty, ref = "mention", "baseline"
            elif c.startswith("ban:"):
                ty, ref = ("ban_cumulative" if "+" in c else "ban_single"), "baseline"
            elif c == "removal:hooked_alpha0":
                ty, ref = "baseline", None
            elif c.startswith("removal:"):
                kind = c.split(":")[1]
                ty = "steer_random" if ("r1_" in kind or "r2_" in kind) else "steer_removal"
                ref = "removal:hooked_alpha0"
            else:
                ty, ref = "other", "baseline"
            eng = "hf_hooked" if ph == "D" else "hf"
            add("exp2", f"data/samples_phase{ph}.jsonl", r, t, c, ty, eng, r.get("decoding"), banned, r.get("label"),
                ref, f"condition=={c}")
    # ---------------- exp3
    for f in ("pools", "knob"):
        for r in read_jsonl(EXP["exp3"] / "generations" / f"{f}.jsonl"):
            t = h_task(r["task"])
            arm = r["arm"]
            banned = [DEFAULT[t]] if arm == "G2" else []
            if arm == "G1":
                c, ty, ref = "G1:baseline", "baseline", None
            elif arm == "G2":
                c, ty, ref = "G2:ban", "ban_single", "G1:baseline"
            elif arm.startswith("G3"):
                c, ty, ref = f"{arm}:baseline", "temperature", "G1:baseline"
            else:
                c, ty, ref = arm, "fork_knob", "G1:baseline"
            add("exp3", f"generations/{f}.jsonl", r, t, c, ty, "vllm", r.get("decoding"), banned, r.get("label"), ref,
                f"arm=={arm}")
    # ---------------- exp4
    for r in read_jsonl(EXP["exp4"] / "data" / "samples.jsonl"):
        t = h_task(r["task"])
        c = r["condition"]
        banned = []
        if c.startswith("steer:"):
            d = c.split(":")[1]
            ty = {"dc": "steer_decommit", "rand1": "steer_random", "rand2": "steer_random", "placebo": "steer_placebo",
                  "breadth": "steer_breadth", "dcxfer": "steer_transfer"}.get(d, "steer_other")
            ref = "steer:dc:c=0:L=18"
            if c == "steer:dc:c=0:L=18":
                ty, ref = "baseline", None
        elif c == "baseline":
            ty, ref = "baseline", None
        elif c.startswith("ban:"):
            ty, ref = "ban_single", "baseline"
            banned = [H(t, c[4:])]
        elif c.startswith("mention:"):
            ty, ref = "mention", "baseline"
        elif c.startswith("enumerate"):
            ty, ref = "instr_enumerate", "baseline"
        elif c.startswith("succession"):
            ty, ref = "ban_cumulative", "baseline"
            banned = ["BFS", "DFS"] if t == "T1" else ["DIJKSTRA", "BF_SPFA"]
        else:
            ty, ref = "other", "baseline"
        add("exp4", "data/samples.jsonl", r, t, c, ty, r.get("engine"), r.get("decoding"), banned, r.get("label"), ref,
            f"condition=={c}")
    # ---------------- exp5
    for r in read_jsonl(EXP["exp5"] / "runs" / "samples.jsonl"):
        t = h_task(r["task"])
        arm, cond = r["arm"], r["condition"]
        c = arm if cond == "baseline" else f"{arm}|{cond}"
        banned = [H(t, cond.split(":")[1].lower())] if cond.startswith("ban:") else []
        if arm == "instruct_chat" and cond == "baseline":
            ty, ref = "baseline", None
        elif arm == "steer:none:c=0":
            ty, ref = "baseline", None
        elif cond.startswith("ban:"):
            ty, ref = "ban_single", arm
        elif arm == "base_chat":
            ty, ref = "base_chat", "instruct_chat"
        elif arm == "base_tf":
            ty, ref = "base_tf", "instruct_chat"
        elif arm == "instruct_tf":
            ty, ref = "other", "instruct_chat"
        elif "Ronly" in arm:
            ty, ref = "R_only_edit", "steer:none:c=0"
        elif arm.startswith("steer:random"):
            ty, ref = "steer_random", "steer:none:c=0"
        elif arm.startswith("steer:sharpen"):
            ty, ref = "steer_sharpen", "steer:none:c=0"
        elif arm.startswith("steer:single18"):
            ty, ref = "steer_single18", "steer:none:c=0"
        else:
            ty, ref = "other", "instruct_chat"
        add("exp5", "runs/samples.jsonl", r, t, c, ty, r.get("engine"), r.get("decoding"), banned, r.get("label"), ref,
            f"arm=={arm}&condition=={cond}")
    # ---------------- exp6
    for r in read_jsonl(EXP["exp6"] / "results" / "samples.jsonl"):
        t = h_task(r["task"])
        arm, cond = r["arm"], r["condition"]
        d = parse_dict(r.get("decoding"))
        T, smp, th = d.get("T"), d.get("sampler"), bool(d.get("thinking"))
        if arm == "A0":
            c, ty, ref = "A0", "baseline", None
        elif arm == "A1":
            c, ty = f"A1|T{T}|{smp}", "temperature"
            ref = None if T == 1.0 else f"A1|T1.0|{smp}"
            if T == 1.0:
                ty = "baseline"
        elif arm.startswith("A6"):
            c, ty = f"A6|T{T}|{smp}|think", "temperature"
            ref = None if T == 1.0 else f"A6|T1.0|{smp}|think"
            if T == 1.0:
                ty = "baseline"
        elif arm == "A2":
            c, ty, ref = f"A2|{cond}", cond, "A0"
        elif arm == "A3":
            c = f"A3|{cond}"
            ty = {"instr_creative": "instr_creative", "instr_new_algo": "instr_new", "instr_fully_novel": "instr_novel2000",
                  "instr_enumerate": "instr_enumerate"}.get(cond, "other")
            ref = "A0"
        elif arm.startswith("A4"):
            c, ty, ref = "A4|gen_then_select", "gen_then_select", "A0"
        elif arm == "A5":
            c, ty, ref = f"A5|{cond}", "forced", "A0"
        else:
            c, ty, ref = f"{arm}|{cond}", "other", "A0"
        add("exp6", "results/samples.jsonl", r, t, c, ty, "vllm", f"T={T},{smp},think={th}", [], r.get("label"), ref,
            f"arm=={arm}&condition=={cond}&T=={T}&sampler=={smp}")
    df = pd.DataFrame(recs)
    df["banned_hit"] = [l in b for l, b in zip(df["label"], df["banned"])]
    df["compliant"] = df["correct"] & ~df["banned_hit"]
    return df


def failure_kind(exp: str, r: dict) -> str | None:
    """wrong_answer / timeout / runtime_error from the stored failure fields (None if passed or unknown)."""
    if to_bool(r.get("passed")):
        return None
    s = " ".join(str(r.get(k)) for k in ("test_error", "fail_kind", "first_failure", "error", "first_fail")
                 if r.get(k) not in (None, "None"))
    s = s.lower()
    if not s:
        return "unknown"
    if "timeout" in s or "time" in s and "limit" in s:
        return "timeout"
    if "wrong" in s or "mismatch" in s or "invalid" in s or "no_path" in s or "not shortest" in s or "answer" in s:
        return "wrong_answer"
    if "exception" in s or "error" in s or "runtime" in s or "crash" in s or "traceback" in s:
        return "runtime_error"
    return "other:" + s[:40]


# ===================================================================================== 0c perturbation table
def perturbation_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (e, t, c), g in df.groupby(["exp", "task", "cond"], sort=True):
        ref = g["ref"].iloc[0]
        gr = df[(df.exp == e) & (df.task == t) & (df.cond == ref)] if ref else None
        N = len(g)
        att = int(g.attempted.sum())
        cor = int(g.correct.sum())
        comp_c = Counter(g[g.correct].label)
        comp_a = Counter(g[g.attempted].label)
        ru, de = RUNNER_UP[t], DEFAULT[t]
        r = {"experiment": e, "task": t, "condition": c, "type": g["type"].iloc[0], "reference": ref or "",
             "engine": g["engine"].iloc[0], "decoding": str(g["decoding"].iloc[0])[:80], "N": N, "attempted": att,
             "correct": cor, "pass_rate": cor / N if N else None}
        if gr is not None and len(gr):
            d, lo, hi = newcombe(int(gr.correct.sum()), len(gr), cor, N)
            r.update({"ref_N": len(gr), "ref_pass_rate": gr.correct.mean(), "pass_cost_pts": 100 * d,
                      "pass_cost_ci_lo": 100 * lo, "pass_cost_ci_hi": 100 * hi})
        r["composition_correct"] = json.dumps(dict(comp_c.most_common()))
        r["composition_attempted"] = json.dumps(dict(comp_a.most_common()))
        for nm, cnt, n in (("correct", comp_c, cor), ("attempted", comp_a, att)):
            k = cnt.get(ru, 0)
            lo, hi = wilson(k, n) if n else (float("nan"), float("nan"))
            r[f"runner_up_share_{nm}"] = k / n if n else None
            r[f"runner_up_ci_{nm}"] = f"[{lo:.3f},{hi:.3f}]"
            kd = cnt.get(de, 0)
            lo, hi = wilson(kd, n) if n else (float("nan"), float("nan"))
            r[f"default_share_{nm}"] = kd / n if n else None
            r[f"default_ci_{nm}"] = f"[{lo:.3f},{hi:.3f}]"
        r["n_distinct_labels_attempted"] = len([k for k in comp_a if k not in ("OTHER",)])
        sub = g[g.attempted]
        r["runtime_vs_ast_disagree"] = int(((sub.rt != sub.ast) & (sub.rt != "NOT_ATTEMPTED") & (sub.ast != "NOT_ATTEMPTED")).sum())
        r["source"] = f"{e}/{g['src'].iloc[0]}#{g['filter'].iloc[0]}"
        rows.append(r)
    return pd.DataFrame(rows)


def rival_statement(pt: pd.DataFrame) -> dict:
    semantic = {"mention", "listall", "instr_creative", "instr_new", "instr_novel2000", "instr_enumerate", "seed_semantic",
                "seed_word"}
    out = {}
    for t in ("T1", "T2"):
        ru, de = RUNNER_UP[t], DEFAULT[t]
        sel = pt[(pt.task == t) & ~pt.type.isin(["baseline", "forced", "ban_single", "ban_cumulative", "sham_ban",
                                                   "other", "base_chat", "base_tf", "gen_then_select"])]
        rows = []
        for _, r in sel.iterrows():
            comp = json.loads(r.composition_correct)
            nd = sum(v for k, v in comp.items() if k != de)
            if nd < 10:
                continue
            k = comp.get(ru, 0)
            rows.append({"experiment": r.experiment, "condition": r.condition, "type": r.type,
                         "semantic": r.type in semantic, "n_nondefault_correct": nd, "runner_up": k,
                         "majority_runner_up": k > nd / 2})
        sem = [x for x in rows if x["semantic"]]
        non = [x for x in rows if not x["semantic"]]
        bans = pt[(pt.task == t) & pt.type.isin(["ban_single"])]
        ban_ru = []
        for _, r in bans.iterrows():
            comp = json.loads(r.composition_correct)
            nd = sum(v for k, v in comp.items() if k != de)
            ban_ru.append((r.experiment, r.condition, comp.get(ru, 0), nd))
        out[t] = {"rows": rows, "n_rows": len(rows),
                  "share_majority_runner_up": (np.mean([x["majority_runner_up"] for x in rows]) if rows else None),
                  "semantic": {"n": len(sem), "majority_runner_up": sum(x["majority_runner_up"] for x in sem)},
                  "non_semantic": {"n": len(non), "majority_runner_up": sum(x["majority_runner_up"] for x in non)},
                  "modal_bans_runner_up_of_nondefault_correct": ban_ru}
    t2, t1 = out["T2"], out["T1"]
    out["sentence_T2"] = (f"T2: {t2['non_semantic']['majority_runner_up']}/{t2['non_semantic']['n']} non-semantic and "
                          f"{t2['semantic']['majority_runner_up']}/{t2['semantic']['n']} semantic perturbation rows with >=10 correct "
                          f"non-Dijkstra programs are majority BF_SPFA (random directions included): perturbations of every kind "
                          f"land on the runner-up.")
    out["sentence_T1"] = (f"T1: only {t1['n_rows']} non-ban perturbation rows leave BFS with >=10 correct programs "
                          f"({t1['non_semantic']['majority_runner_up']}/{t1['non_semantic']['n']} non-semantic and "
                          f"{t1['semantic']['majority_runner_up']}/{t1['semantic']['n']} semantic are majority DFS); generic "
                          f"perturbations rarely leave BFS while bans land on DFS.")
    return out


# ===================================================================================== 0d corrections
MODAL_DRAWS = {"T1": [("exp1", "ban:bfs"), ("exp2", "ban:bfs"), ("exp3", "G2:ban"), ("exp4", "ban:bfs"),
                      ("exp5", "instruct_chat|ban:BFS")],
               "T2": [("exp1", "ban:dijkstra"), ("exp2", "ban:dijkstra"), ("exp3", "G2:ban"), ("exp4", "ban:dijkstra"),
                      ("exp5", "instruct_chat|ban:Dijkstra")]}


def modal_ban_draws(df: pd.DataFrame, rng: np.random.Generator) -> dict:
    out = {}
    for t, draws in MODAL_DRAWS.items():
        ru = RUNNER_UP[t]
        rows = []
        for e, c in draws:
            g = df[(df.exp == e) & (df.task == t) & (df.cond == c)]
            comp = g[g.compliant]
            k, n = int((comp.label == ru).sum()), len(comp)
            cc = Counter(comp.label)
            mode = cc.most_common(1)[0][0] if cc else None
            lead = (cc.most_common(2)[0][1] - (cc.most_common(2)[1][1] if len(cc) > 1 else 0)) / n if n else 0
            rows.append({"experiment": e, "condition": c, "compliant": n, "substitute": k, "share": k / n if n else None,
                         "wilson": list(wilson(k, n)), "composition": dict(cc), "mode": mode,
                         "clear_mode": bool(lead >= 0.2), "realised_mode_is_runner_up": bool(mode == ru and lead >= 0.2),
                         "source": f"{e}/{g['src'].iloc[0]}#{g['filter'].iloc[0]}"})
        K = sum(r["substitute"] for r in rows)
        N = sum(r["compliant"] for r in rows)
        boots = []
        for _ in range(2000):
            idx = rng.integers(0, len(rows), len(rows))
            kk = sum(rows[i]["substitute"] for i in idx)
            nn = sum(rows[i]["compliant"] for i in idx)
            boots.append(kk / nn if nn else np.nan)
        out[t] = {"draws": rows, "pooled": {"substitute": K, "compliant": N, "share": K / N, "wilson": list(wilson(K, N)),
                                            "draw_cluster_bootstrap_95": [float(np.nanpercentile(boots, 2.5)),
                                                                          float(np.nanpercentile(boots, 97.5))]},
                  "n_draws_realised_mode_runner_up": sum(r["realised_mode_is_runner_up"] for r in rows), "runner_up": ru}
    return out


def cumulative_bans(df: pd.DataFrame) -> dict:
    draws = [("exp4", "succession:2", "decommitment"), ("exp2", "ban:bfs+dfs", "geometry"),
             ("exp1", "succession:2", "association")]
    res = []
    for e, c, role in draws:
        g = df[(df.exp == e) & (df.task == "T1") & (df.cond == c)]
        att = g[g.attempted]
        ban = att.label.isin(["BFS", "DFS"])
        comp = g[g.compliant]
        cand = {"banned_share_of_attempted": ban.mean(), "banned_share_of_all": (g.label.isin(["BFS", "DFS"])).mean(),
                "pass_rate": g.correct.mean(), "banned_share_of_correct": g[g.correct].label.isin(["BFS", "DFS"]).mean()
                if g.correct.any() else None, "attempted_share": g.attempted.mean(),
                "compliance_all": (~g.label.isin(["BFS", "DFS"]) & g.attempted).mean(),
                "pass_rate_attempted": att.correct.mean() if len(att) else None,
                "banned_share_runtime_label": att.rt.isin(["BFS", "DFS"]).mean() if len(att) else None,
                "banned_share_ast_label": att.ast.isin(["BFS", "DFS"]).mean() if len(att) else None,
                "pass_rate_banned": att[ban].correct.mean() if ban.any() else None,
                "pass_rate_nonbanned": att[~ban].correct.mean() if (~ban).any() else None,
                "share_correct_among_nonbanned_or_banned": None}
        res.append({"experiment": e, "role": role, "condition": c, "N": len(g), "attempted": len(att),
                    "banned_share_mechanism": float(ban.mean()) if len(att) else None,
                    "pass_rate": float(g.correct.mean()), "compliant": len(comp), "compliant_composition": dict(Counter(comp.label)),
                    "candidate_measures": {k: (float(v) if v is not None else None) for k, v in cand.items()},
                    "source": f"{e}/{g['src'].iloc[0]}#{g['filter'].iloc[0]}"})
    quoted = [(0.88, 1.00), (0.96, 0.99), (0.53, 0.933)]
    ident = []
    for (a, b), r in zip(quoted, res):
        ma = [k for k, v in r["candidate_measures"].items() if v is not None and abs(v - a) <= 0.005]
        mb = [k for k, v in r["candidate_measures"].items() if v is not None and abs(v - b) <= 0.005]
        ident.append({"pair": [a, b], "draw": r["role"], "first_element_matches": ma, "second_element_matches": mb})
    comps = [tuple(sorted(r["compliant_composition"].items())) for r in res]
    return {"draws": res, "quoted_pairs_identification": ident,
            "non_replicating": bool(len(set(comps)) > 1),
            "verdict": "non-replicating" if len(set(comps)) > 1 else "replicating"}


def hill_counts(counts: np.ndarray) -> np.ndarray:
    p = counts / counts.sum(-1, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        Hh = -np.where(p > 0, p * np.log(p), 0.0).sum(-1)
    return np.exp(Hh)


def rarefied_from_counts(cnt: np.ndarray, depth: int, n_draws: int, rng: np.random.Generator) -> float:
    if cnt.sum() < depth:
        return float("nan")
    s = rng.multivariate_hypergeometric(cnt.astype(np.int64), depth, size=n_draws)
    return float(hill_counts(s.astype(float)).mean())


def knob_table(df: pd.DataFrame, pt: pd.DataFrame, rng: np.random.Generator, depth: int = 25) -> pd.DataFrame:
    rows = []
    for _, r in pt.iterrows():
        if r.type in ("baseline", "forced", "other"):
            continue
        g = df[(df.exp == r.experiment) & (df.task == r.task) & (df.cond == r.condition)]
        rows.append(knob_row(g, r, rng, depth, label=f"{r.experiment}:{r.condition}"))
    # pooled-over-draws rows for knobs repeated across draws
    for t, draws in MODAL_DRAWS.items():
        gs = [df[(df.exp == e) & (df.task == t) & (df.cond == c)] for e, c in draws]
        g = pd.concat(gs)
        per = [knob_row(x, None, rng, depth, label="", n_boot=0)["hill1_rarefied"] for x in gs]
        rr = knob_row(g, None, rng, depth, label=f"POOLED modal ban ({len(draws)} draws)", n_boot=1000)
        rr.update({"task": t, "type": "ban_single_pooled", "between_draw_spread": [np.nanmin(per), np.nanmax(per)],
                   "per_draw_hill": per,
                   "pass_points": float(np.mean([pt[(pt.experiment == e) & (pt.task == t) & (pt.condition == c)].pass_cost_pts.iloc[0]
                                                 for e, c in draws]))})
        rows.append(rr)
    repeated = {
        "mention_pooled": {"T1": [("exp1", "mention:bfs"), ("exp2", "mention:bfs"), ("exp4", "mention:bfs")],
                           "T2": [("exp1", "mention:dijkstra"), ("exp2", "mention:dijkstra"), ("exp4", "mention:dijkstra")]},
        "steer_random_pooled": {"T1": [("exp4", "steer:rand1:c=0.1:L=18"), ("exp4", "steer:rand2:c=0.1:L=18"),
                                       ("exp5", "steer:random1"), ("exp5", "steer:random2")],
                                "T2": [("exp4", "steer:rand1:c=0.25:L=18"), ("exp4", "steer:rand2:c=0.25:L=18"),
                                       ("exp5", "steer:random1"), ("exp5", "steer:random2")]},
        "instr_enumerate_pooled": {"T1": [("exp4", "enumerate"), ("exp6", "A3|instr_enumerate")],
                                   "T2": [("exp4", "enumerate"), ("exp6", "A3|instr_enumerate")]}}
    for typ, by_task in repeated.items():
        for t, draws in by_task.items():
            gs = [df[(df.exp == e) & (df.task == t) & (df.cond == c)] for e, c in draws]
            if any(len(x) == 0 for x in gs):
                continue
            per = [knob_row(x, None, rng, depth, label="", n_boot=0)["hill1_rarefied"] for x in gs]
            rr = knob_row(pd.concat(gs), None, rng, depth, label=f"POOLED {typ.replace('_pooled', '')} ({len(draws)} draws)", n_boot=1000)
            pp = [pt[(pt.experiment == e) & (pt.task == t) & (pt.condition == c)].pass_cost_pts.iloc[0] for e, c in draws]
            rr.update({"task": t, "type": typ, "between_draw_spread": [np.nanmin(per), np.nanmax(per)] if np.isfinite(per).any() else None,
                       "per_draw_hill": per, "pass_points": float(np.nanmean(pp)), "draws": [f"{e}:{c}" for e, c in draws]})
            rows.append(rr)
    kt = pd.DataFrame(rows)
    named = {"mention", "listall", "forced", "mention_pooled"}
    kt["knob_class"] = np.where(kt.type.isin(list(named)), "named_mode_cue",
                                np.where(kt.type.isin(["base_chat", "base_tf"]), "model_swap",
                                         np.where(kt.type.isin(["ban_single", "ban_cumulative", "sham_ban", "ban_single_pooled"]),
                                                  "ban", np.where(kt.type == "gen_then_select", "ceiling", "diversity_knob"))))
    kt["positive_target_literal"] = (kt.hill1_rarefied >= 2) & (kt.pass_points < 20)
    kt["positive_target"] = kt.positive_target_literal & kt.knob_class.isin(["diversity_knob", "ban"])
    kt["ceiling_row"] = kt.type == "gen_then_select"
    return kt


def knob_row(g: pd.DataFrame, r, rng, depth: int, label: str, n_boot: int = 1000) -> dict:
    comp = g[g.compliant]
    labs = sorted(set(g.label) | {"_"})
    li = {l: i for i, l in enumerate(labs)}
    cnt = np.zeros(len(labs))
    for l in comp.label:
        cnt[li[l]] += 1
    hill = rarefied_from_counts(cnt, depth, 1000, rng)
    out = {"knob": label, "n_compliant": int(cnt.sum()), "compliant_composition": json.dumps(dict(Counter(comp.label))),
           "hill1_rarefied": hill, "below_depth": bool(cnt.sum() < depth), "hill1_plugin_compliant": float(hill_counts(cnt[None])[0]) if cnt.sum() else None}
    if r is not None:
        out.update({"experiment": r.experiment, "task": r.task, "condition": r.condition, "type": r.type,
                    "reference": r.reference, "pass_points": r.get("pass_cost_pts"), "pass_rate": r.pass_rate,
                    "source": r.source})
    if n_boot and not out["below_depth"]:
        att = g[g.attempted]
        pids = att.pid.values
        up = np.unique(pids)
        groups = {p: att[att.pid == p] for p in up}
        gc_ = {p: np.bincount([li[l] for l in grp[grp.compliant].label], minlength=len(labs)) for p, grp in groups.items()}
        bs = []
        for _ in range(n_boot):
            pick = rng.choice(up, len(up), replace=True)
            c2 = np.sum([gc_[p] for p in pick], axis=0)
            bs.append(rarefied_from_counts(c2, depth, 200, rng))
        bs = np.array(bs, dtype=float)
        out["hill1_ci90"] = [float(np.nanpercentile(bs, 5)), float(np.nanpercentile(bs, 95))] if np.isfinite(bs).any() else None
        out["boot_below_depth_share"] = float(np.mean(~np.isfinite(bs)))
    return out


# ===================================================================================== 0d(iv) PREDICT on gated events
FAMILY = [("freq_listall", "listall_typicality"), ("listall", "listall_typicality"), ("freetext", "freetext_association"),
          ("assoc", "association"), ("association", "association"), ("freq", "frequency"), ("frequency", "frequency"),
          ("uniform", "uniform"), ("geodesic", "geodesic"), ("decoder", "decoder"), ("dc", "decommitted"),
          ("base", "base_model"), ("typical", "typicality"), ("mention", "mention"), ("euclid", "euclidean")]


def canon_family(name: str) -> str:
    n = name.lower()
    for k, v in FAMILY:
        if n.startswith(k):
            return v
    return n


def collect_forecasts() -> list[dict]:
    ev = []
    for t in ("t1", "t2"):
        for f in (f"predictions/{t}_single_bans.json", f"predictions/{t}_succ_step2.json"):
            d = json.loads((EXP["exp1"] / f).read_text())
            items = d["events"].items() if "events" in d else [(d.get("event_id", "succession:2"), d)]
            for eid, e in items:
                cond = eid.split("|")[-1] if "|" in eid else eid
                if f.endswith("succ_step2.json"):
                    cond = "succession:2"
                ev.append({"exp": "exp1", "task": t.upper(), "event": f"{t}|{cond}", "cond": cond,
                           "families": e.get("composed", {}), "source": f"exp1/{f}"})
    d = json.loads((EXP["exp2"] / "predictions" / "predictions_v1.json").read_text())
    for eid, e in d["events"].items():
        ev.append({"exp": "exp2", "task": e["task"].upper(), "event": eid, "cond": eid.split("|")[1],
                   "families": e.get("distributions", {}), "source": "exp2/predictions/predictions_v1.json"})
    for f in sorted((EXP["exp4"] / "forecast").glob("predict_*.json")):
        e = json.loads(f.read_text())
        t = e["task"].upper()
        cond = ("ban:" + e["banned"][0]) if "ban1" in f.name else "succession:2"
        ev.append({"exp": "exp4", "task": t, "event": e["event"], "cond": cond, "families": e.get("forecasts", {}),
                   "source": f"exp4/forecast/{f.name}"})
    d = json.loads((EXP["exp5"] / "predictions" / "predict_modal_ban.json").read_text())
    for t, e in d["events"].items():
        cond = "instruct_chat|ban:BFS" if t == "t1" else "instruct_chat|ban:Dijkstra"
        ev.append({"exp": "exp5", "task": t.upper(), "event": e["event"], "cond": cond,
                   "families": {k: v.get("p", {}) for k, v in e.get("predictors", {}).items()},
                   "source": "exp5/predictions/predict_modal_ban.json"})
    return ev


def stored_scores(e: dict) -> dict:
    """The experiment's own stored per-family mean log score for the event, where it exists."""
    try:
        if e["exp"] == "exp1":
            c = json.loads((EXP["exp1"] / "results" / "contest.json").read_text())
            for x in c["events"]:
                if x["event_id"] == e["event"]:
                    return {k: v.get("log_score") for k, v in x["per_predictor"].items()}
        if e["exp"] == "exp2":
            c = json.loads((EXP["exp2"] / "results" / "contest.json").read_text())
            x = c["events"].get(e["event"], {})
            return {k: v.get("log_score_mean") for k, v in x.get("predictors", {}).items()}
        if e["exp"] == "exp4":
            c = json.loads((EXP["exp4"] / "results" / "predict_row.json").read_text())
            x = c.get(e["event"], {})
            return {k: v.get("mean_log_score") for k, v in x.get("forecasts", {}).items()}
        if e["exp"] == "exp5":
            md = json.loads((EXP["exp5"] / "full_method_out.json").read_text())["metadata"]["rows"]["PREDICT"]
            return {x["predictor"]: x.get("log_score") for x in md if x["event"] == e["event"]}
    except (KeyError, FileNotFoundError, json.JSONDecodeError) as ex:
        logger.warning(f"stored score lookup failed for {e['event']}: {ex}")
    return {}


def predict_gated(df: pd.DataFrame) -> dict:
    evs = collect_forecasts()
    out_ev = []
    for e in evs:
        t = e["task"]
        g = df[(df.exp == e["exp"]) & (df.task == t) & (df.cond == e["cond"])]
        if not len(g):
            out_ev.append({**{k: e[k] for k in ("exp", "task", "event", "cond", "source")}, "generated": False})
            continue
        banned = set(g.banned.iloc[0])
        surv = [m for m in CATALOGUE[t] if m not in banned]
        att = g[g.attempted]
        nb = att[~att.label.isin(banned)]
        comp = g[g.compliant]
        avoid = 1 - att.label.isin(banned).mean() if len(att) else 0
        gate1 = bool(avoid >= 0.5 and len(nb) >= 20)
        gate2 = bool((len(comp) / len(att) if len(att) else 0) >= 0.5 and len(comp) >= 20)
        fams = {}
        for fname, dist in e["families"].items():
            if not isinstance(dist, dict) or not dist:
                continue
            p = defaultdict(float)
            for k, v in dist.items():
                try:
                    p[H(t, k)] += float(v)
                except (TypeError, ValueError):
                    continue
            ps = np.array([p.get(s, 0.0) for s in surv])
            if ps.sum() <= 0:
                ps = np.ones(len(surv))
            ps = ps / ps.sum()
            q = 0.98 * (0.95 * ps + 0.05 / len(surv))
            qd = dict(zip(surv, q))

            def score(labels):
                if not len(labels):
                    return None
                return float(np.mean([math.log(qd.get(l, 0.02)) if l in qd else math.log(0.02) for l in labels]))

            top = [surv[i] for i in np.flatnonzero(ps == ps.max())]
            fams[fname] = {"canonical": canon_family(fname), "top1": top[0] if len(top) == 1 else "tie",
                           "score_attempted_nonbanned": score(list(nb.label)), "score_compliant": score(list(comp.label))}
        st = stored_scores(e)
        for k in fams:
            fams[k]["stored_score"] = st.get(k)
        out_ev.append({**{k: e[k] for k in ("exp", "task", "event", "cond", "source")}, "generated": True,
                       "banned": sorted(banned), "survivors": surv, "n": len(g), "attempted": len(att),
                       "attempted_nonbanned": len(nb), "compliant": len(comp), "avoidance": float(avoid),
                       "compliant_share": float(len(comp) / len(att)) if len(att) else 0.0,
                       "gate_primary": gate1, "gate_compliant": gate2, "families": fams,
                       "realised_nonbanned": dict(Counter(nb.label)), "realised_compliant": dict(Counter(comp.label))})
    sham_conds = {"T1": {"ban:astar_gbfs", "ban:bibfs", "ban:dfs", "ban:dijkstra", "ban:iddfs"},
                  "T2": {"ban:bf_spfa", "ban:bidijkstra", "ban:dial", "ban:floyd"}}
    for x in out_ev:
        x["sham_absent_mode_ban"] = bool(x["exp"] == "exp1" and x["cond"] in sham_conds.get(x["task"], set()))
    gated_literal = [x for x in out_ev if x.get("gate_primary")]
    gated = [x for x in gated_literal if not x["sham_absent_mode_ban"]]
    # per-family means on gated events (canonical families)
    fam_means = defaultdict(list)
    for x in gated:
        best = {}
        for fn, f in x["families"].items():
            c = f["canonical"]
            v = f["score_attempted_nonbanned"]
            if v is not None and (c not in best or v > best[c]):
                best[c] = v
        for c, v in best.items():
            fam_means[c].append(v)
    fam_summary = {c: {"mean_log_score": float(np.mean(v)), "n_events": len(v)} for c, v in fam_means.items()}
    # PREDICT rule
    wins = Counter()
    disagree_events = []
    for x in gated:
        per = {}
        tops = {}
        for fn, f in x["families"].items():
            c = f["canonical"]
            v = f["score_attempted_nonbanned"]
            if v is None:
                continue
            if c not in per or v > per[c]:
                per[c] = v
                tops[c] = f["top1"]
        if len(set(tops.values()) - {"tie"}) + (1 if "tie" in tops.values() else 0) <= 1:
            continue
        srt = sorted(per.items(), key=lambda kv: -kv[1])
        margin = srt[0][1] - srt[1][1] if len(srt) > 1 else float("inf")
        disagree_events.append({"event": f"{x['exp']}:{x['event']}", "best": srt[0][0], "margin_nats": margin})
        if margin >= 0.10:
            wins[srt[0][0]] += 1
    adv = [f for f, n in wins.items() if n >= 3]
    return {"events": out_ev, "n_events_with_forecasts": len(out_ev), "n_generated": sum(x["generated"] for x in out_ev),
            "n_gated_primary_literal": len(gated_literal), "n_gated_primary": len(gated),
            "gated_literal_event_ids": [f"{x['exp']}:{x['event']}" for x in gated_literal],
            "gating_note": ("the literal gate also admits exp1's nine bans of absent modes (avoidance ~1 by construction, "
                            "realised samples are the default mode); they are excluded from the contest as uninformative "
                            "(exp1/results/event_table.json marks them informative=false)"),
            "n_gated_compliant": sum(1 for x in out_ev if x.get("gate_compliant") and not x["sham_absent_mode_ban"]),
            "gated_event_ids": [f"{x['exp']}:{x['event']}" for x in gated], "family_means_gated": fam_summary,
            "disagreement_events": disagree_events, "n_disagreement_events": len(disagree_events),
            "wins_by_0.10_nats": dict(wins), "families_advancing": adv,
            "rule": ("a family advances only if its calibrated mean log score beats the next best by >= 0.10 nats on >= 3 "
                     "events where top-1 nominations disagree"),
            "outcome": ("no family can advance under the rule" if not adv else f"advancing: {adv}"),
            "smoothing": "5% uniform over survivors, 2% 'other' floor, applied to every family identically",
            "unforecast": {"exp3": "no family forecasts (fork/locus screen): its G2 ban events are unforecast",
                           "exp6": "forecasts are claim-type predictions P1-P8 (results/analysis.json#forecast_check), not "
                                   "family distributions over survivors"}}


# ===================================================================================== 0g sham bans
NEIGH = {"T1": [{"BFS", "BIDIR_BFS"}, {"DFS", "IDDFS"}, {"UNIT_DIJKSTRA", "ASTAR"}],
         "T2": [{"DIJKSTRA", "BIDIR_DIJKSTRA", "DIAL"}, {"BF_SPFA", "FW"}]}


def sham_bans(df: pd.DataFrame) -> dict:
    out = []
    s1 = json.loads((EXP["exp1"] / "results" / "s1_sham_control.json").read_text())
    s1_ids = [x["event_id"] for x in s1["per_event"]]
    for t in ("T1", "T2"):
        base = df[(df.exp == "exp1") & (df.task == t) & (df.cond == "baseline") & df.attempted]
        conds = sorted(df[(df.exp == "exp1") & (df.task == t) & (df.type == "sham_ban")].cond.unique())
        for c in conds:
            g = df[(df.exp == "exp1") & (df.task == t) & (df.cond == c) & df.attempted]
            X = g.banned.iloc[0][0]
            mname = "mention:" + c.split(":")[1]
            mt = df[(df.exp == "exp1") & (df.task == t) & (df.cond == mname) & df.attempted]
            for s in CATALOGUE[t]:
                if s == X:
                    continue
                k1, n1 = int((g.label == s).sum()), len(g)
                k0, n0 = int((base.label == s).sum()), len(base)
                km, nm = int((mt.label == s).sum()), len(mt)
                d, lo, hi = newcombe(k1, n1, k0, n0)
                fp = fisher_p(k1, n1, k0, n0)
                promoted = bool(d >= 0.10 and fp < 0.05)
                cls = None
                if promoted:
                    nb = any(X in grp and s in grp for grp in NEIGH[t])
                    ru = s == RUNNER_UP[t]
                    cls = "both" if (nb and ru) else ("neighbour" if nb else ("runner-up" if ru else "neither"))
                out.append({"task": t, "event": c, "banned": X, "survivor": s, "share_ban": k1 / n1, "k_ban": k1, "n_ban": n1,
                            "cp_ban": list(clopper_pearson(k1, n1)), "share_baseline": k0 / n0, "k_base": k0, "n_base": n0,
                            "cp_base": list(clopper_pearson(k0, n0)), "share_mention": km / nm if nm else None,
                            "diff": d, "newcombe": [lo, hi], "fisher_p": fp, "promoted": promoted, "class": cls,
                            "in_s1_sham_control": f"{t.lower()}|{c}" in s1_ids})
    pr = [x for x in out if x["promoted"]]
    return {"rows": out, "n_sham_events": len({(x["task"], x["event"]) for x in out}), "n_promotions": len(pr),
            "promotions": [{k: x[k] for k in ("task", "event", "survivor", "diff", "fisher_p", "class")} for x in pr],
            "all_promoted_are_runner_up": bool(pr and all(x["survivor"] == RUNNER_UP[x["task"]] for x in pr)),
            "note": "shares among attempted programs; baseline = exp1 'baseline' (primary reference); mention twin beside it",
            "s1_sham_control_events": s1_ids}


# ===================================================================================== helpers for recompute-then-compare
def find_number(obj, target: float, tol: float, path: str = "") -> list[str]:
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            hits += find_number(v, target, tol, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits += find_number(v, target, tol, f"{path}[{i}]")
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        if math.isfinite(obj) and abs(obj - target) <= tol:
            hits.append(path)
    return hits[:10]


CHECKS: list[dict] = []


def check(name: str, expected, recomputed, kind: str = "share", note: str = "", source: str = "") -> None:
    if expected is None or recomputed is None:
        m = False
    elif kind == "string":
        m = str(expected) == str(recomputed)
    elif kind == "count":
        m = int(round(float(recomputed))) == int(expected)
    else:
        m = abs(float(recomputed) - float(expected)) <= (0.005 if kind == "share" else float(kind))
    CHECKS.append({"name": name, "expected": expected, "recomputed": recomputed, "match": bool(m), "note": note,
                   "source": source})


# ===================================================================================== 0e seeds, 0f missing outputs
def seeds(df: pd.DataFrame) -> dict:
    a = json.loads((EXP["exp6"] / "results" / "analysis.json").read_text())
    out = {"behaviour": {}, "activation_paths": {}}
    implied = {"T1": "BIDIR_BFS", "T2": "BF_SPFA"}
    for t in ("T1", "T2"):
        base = df[(df.exp == "exp6") & (df.task == t) & (df.cond == "A0") & df.attempted]
        for s in ("seed_entropy", "seed_word", "seed_semantic"):
            g = df[(df.exp == "exp6") & (df.task == t) & (df.cond == f"A2|{s}") & df.attempted]
            rec = {}
            gc_, bc_ = g[g.correct], base[base.correct]
            gk_, bk_ = g[g.label.isin(CATALOGUE[t])], base[base.label.isin(CATALOGUE[t])]
            for lab in sorted(set(CATALOGUE[t])):
                k1, n1 = int((g.label == lab).sum()), len(g)
                k0, n0 = int((base.label == lab).sum()), len(base)
                if k1 == 0 and k0 == 0:
                    continue
                d, lo, hi = newcombe(k1, n1, k0, n0)
                c1, m1 = int((gc_.label == lab).sum()), len(gc_)
                c0, m0 = int((bc_.label == lab).sum()), len(bc_)
                dc, loc, hic = newcombe(c1, m1, c0, m0)
                q1, r1 = int((gk_.label == lab).sum()), len(gk_)
                q0, r0 = int((bk_.label == lab).sum()), len(bk_)
                dk, lok, hik = newcombe(q1, r1, q0, r0)
                rec[lab] = {"share_seed": k1 / n1, "share_A0": k0 / n0, "diff_pts": 100 * d, "newcombe_pts": [100 * lo, 100 * hi],
                            "fisher_p": fisher_p(k1, n1, k0, n0),
                            "diff_pts_among_correct": 100 * dc, "newcombe_pts_among_correct": [100 * loc, 100 * hic],
                            "diff_pts_among_classified": 100 * dk, "newcombe_pts_among_classified": [100 * lok, 100 * hik],
                            "denominators": {"attempted": [n1, n0], "correct": [m1, m0], "classified": [r1, r0]}}
            out["behaviour"][f"{t}|{s}"] = rec
    for nm, tgt, tol in (("T1 semantic seed cosine to implied centroid", 0.493, 0.0006),
                         ("T2 semantic seed cosine", -0.087, 0.0006), ("T1 word seed probe shift toward ASTAR", 0.88, 0.006),
                         ("T2 entropy seed Hill interval upper", 1.596, 0.0006), ("T2 semantic seed DIJKSTRA share change", -67.39, 0.006),
                         ("T2 semantic seed change pp", 66.3, 0.06), ("T1 semantic seed change pp", 2.2, 0.06)):
        out["activation_paths"][nm] = {"value": tgt, "json_paths": find_number(a, tgt, tol)}
    t2 = out["behaviour"]["T2|seed_semantic"].get("BF_SPFA", {})
    t1 = out["behaviour"]["T1|seed_semantic"].get(implied["T1"], {})
    out["double_dissociation"] = (
        f"On T1 the semantic seed moves the read-position state toward the implied mode (cosine 0.493, exp6 analysis) yet "
        f"behaviour moves {t1.get('diff_pts', float('nan')):+.1f} points; on T2 the cosine is -0.087 yet behaviour moves "
        f"{t2.get('diff_pts', float('nan')):+.1f} points toward BF_SPFA. Activation shift and behavioural shift dissociate in "
        f"both directions, so the read-position subspace picture does not predict behaviour.")
    return out


def gpu_hours() -> dict:
    """GPU-phase wall time from log timestamps. Rule: per GPU-phase log file, last minus first parsable timestamp;
    summed over files of the experiment (overlapping files would double count; none overlap in these logs)."""
    pat = re.compile(r"(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})")
    pat_t = re.compile(r"^(\d{2}:\d{2}:\d{2})\|")
    out = {}
    gpu_name = re.compile(r"(gen|state|steer|vllm|hf|gpu|phase|run_|acts|engine|S\d)", re.I)
    for e in ("exp1", "exp2", "exp3", "exp4", "exp5", "exp6"):
        files = []
        for f in sorted((EXP[e] / "logs").glob("*")):
            if not f.is_file() or f.stat().st_size > 50_000_000 or not gpu_name.search(f.name):
                continue
            try:
                txt = f.read_text(errors="ignore")
            except OSError:
                continue
            ts = [pd.Timestamp(m.group(1)) for m in pat.finditer(txt)]
            if len(ts) < 2:
                tt = [m.group(1) for line in txt.splitlines() for m in [pat_t.match(line)] if m]
                if len(tt) >= 2:
                    a, b = pd.Timestamp("2026-10-19 " + tt[0]), pd.Timestamp("2026-10-19 " + tt[-1])
                    if b < a:
                        b += pd.Timedelta(days=1)
                    files.append({"file": f"{e}/logs/{f.name}", "start": a, "end": b, "hours": (b - a).total_seconds() / 3600})
                continue
            files.append({"file": f"{e}/logs/{f.name}", "start": min(ts), "end": max(ts),
                          "hours": (max(ts) - min(ts)).total_seconds() / 3600})
        extra = {}
        if e == "exp5" and (EXP[e] / "time_log.json").exists():
            extra["time_log"] = json.loads((EXP[e] / "time_log.json").read_text())
        if e == "exp4" and (EXP[e] / "logs" / "hardware.json").exists():
            extra["hardware"] = json.loads((EXP[e] / "logs" / "hardware.json").read_text())
        iv = sorted((x["start"], x["end"]) for x in files)
        union, cur = 0.0, None
        for a, b in iv:
            if cur is None or a > cur[1]:
                if cur is not None:
                    union += (cur[1] - cur[0]).total_seconds()
                cur = [a, b]
            else:
                cur[1] = max(cur[1], b)
        if cur is not None:
            union += (cur[1] - cur[0]).total_seconds()
        for x in files:
            x["start"], x["end"] = str(x["start"]), str(x["end"])
        out[e] = {"files": files, "gpu_hours_union_of_phase_log_spans": union / 3600, **extra}
    out["rule"] = ("per GPU-phase log file (name matches gen|state|steer|vllm|hf|gpu|phase|run_|acts|engine), first and "
                   "last timestamp; the union of these spans per experiment (overlapping logs of one phase counted once). "
                   "Upper bound on GPU-busy time (includes waits); exp1 has no GPU-phase log file under logs/ (not extracted).")
    return out


def missing_outputs(df: pd.DataFrame, pt: pd.DataFrame) -> dict:
    out = {}
    # exp1 forced conditions
    fr = pt[(pt.experiment == "exp1") & (pt.type == "forced")]
    out["exp1_forced"] = [{"task": r.task, "condition": r.condition, "pass": f"{r.correct}/{r.N}",
                           "labels_attempted": json.loads(r.composition_attempted), "source": r.source} for _, r in fr.iterrows()]
    c1 = json.loads((EXP["exp1"] / "results" / "contest.json").read_text())
    out["exp1_sharpness_matched_paths"] = {"-1.386": find_number(c1, -1.386, 0.0006), "-1.475": find_number(c1, -1.475, 0.0006)}
    out["exp1_robustness_block"] = c1.get("robustness")
    nt = json.loads((EXP["exp3"] / "summaries" / "next_token.json").read_text())
    by = defaultdict(list)
    for x in nt:
        by[x["kind"]].append(x["entropy_bits_full"])
    out["exp3_next_token_summary"] = {k: {"n": len(v), "mean_entropy_bits": float(np.mean(v)), "max": float(np.max(v))}
                                      for k, v in by.items()}
    out["exp3_t6_sensitivity"] = json.loads((EXP["exp3"] / "summaries" / "t6_sensitivity.json").read_text())
    out["exp3_test_engine"] = json.loads((EXP["exp3"] / "logs" / "test_engine.json").read_text())
    c1rows = pt[(pt.experiment == "exp4") & pt.condition.isin(["steer:dc:c=1:L=14", "steer:dc:c=1:L=22"])]
    out["exp4_c1_L14_L22"] = [{"task": r.task, "condition": r.condition, "pass": f"{r.correct}/{r.N}"} for _, r in c1rows.iterrows()]
    gb = json.loads((EXP["exp2"] / "results" / "geometry_b.json").read_text())
    out["exp2_procrustes"] = {t: gb[t]["procrustes_disparity_named_vs_masked"] for t in ("t1", "t2")}
    out["exp2_deviations"] = json.loads((EXP["exp2"] / "results" / "deviations.json").read_text())
    en = pt[(pt.experiment == "exp6") & (pt.type == "instr_enumerate")]
    out["exp6_enumeration_all_labels"] = [{"task": r.task, "attempted": json.loads(r.composition_attempted),
                                           "correct": json.loads(r.composition_correct)} for _, r in en.iterrows()]
    out["gpu_hours"] = gpu_hours()
    # grid failure taxonomy: failing T1 programs per condition, from stored failure fields
    tax = []
    t1f = df[(df.task == "T1") & df.attempted & ~df.correct]
    for (e, c), g in t1f.groupby(["exp", "cond"]):
        tax.append({"experiment": e, "condition": c, "n_failing": len(g), **{k: int(v) for k, v in Counter(g.fail).items()}})
    out["grid_failure_taxonomy"] = tax
    dfs1 = df[(df.exp == "exp1") & (df.task == "T1") & (df.label == "DFS")]
    f = dfs1[~dfs1.correct]
    out["exp1_dfs_failures"] = {"n_dfs": len(dfs1), "n_failing": len(f), "kinds": dict(Counter(f.fail))}
    out["none_as_empty_rescue"] = ("not computed: the stored failure fields (test_error/fail_case) do not hold the returned "
                                   "value; re-execution was the first item of the drop order and was dropped")
    # base-model caveats
    b = {}
    md = json.loads((EXP["exp5"] / "full_method_out.json").read_text())["metadata"]
    raw5 = read_jsonl(EXP["exp5"] / "runs" / "samples.jsonl")
    for t in ("t1", "t2"):
        rows = [r for r in raw5 if r["task"] == t and r["arm"] == "base_chat"]
        parse = sum(to_bool(r["parse_ok"]) or False for r in rows)
        T = t.upper()
        g = df[(df.exp == "exp5") & (df.task == T) & (df.cond == "base_chat")]
        tf = df[(df.exp == "exp5") & (df.task == T) & (df.cond == "base_tf")]
        sub = g[g.attempted]
        from sklearn.metrics import cohen_kappa_score
        ok = (sub.rt != "NOT_ATTEMPTED") & (sub.ast != "NOT_ATTEMPTED")
        kap = float(cohen_kappa_score(sub.rt[ok], sub.ast[ok])) if ok.sum() > 5 else None
        b[T] = {"base_chat_parse_rate": parse / len(rows), "parse_wilson": list(wilson(parse, len(rows))),
                "base_chat_correct": int(g.correct.sum()), "base_chat_N": len(g), "runtime_ast_kappa_base_chat": kap,
                "base_tf_correct_composition": dict(Counter(tf[tf.correct].label)), "base_tf_correct": int(tf.correct.sum())}
    cs = md.get("collapse_screen", {})
    b["verdicts"] = {t: {k: v for k, v in cs.get(t, {}).items() if "verdict" in k.lower()} for t in ("t1", "t2")}
    b["alternate_passes_screen"] = {k: cs.get(k) for k in ("alternate_passes_screen_cc", "alternate_passes_screen_all")}
    b["collapse_screen_keys"] = list(md.get("collapse_screen", {}).keys())
    out["base_model_caveats"] = b
    return out


# ===================================================================================== BUY
def buy_quotes(kt: pd.DataFrame) -> dict:
    pre = json.loads((EXP["exp4"] / "results" / "preregistration.json").read_text())["rules"]
    q = {k: pre[k] for k in ("S_flat", "S_specific", "S_vs_prompt", "overall", "PREDICT") if k in pre}
    md = json.loads((EXP["exp5"] / "full_method_out.json").read_text())["metadata"]["rows"]["BUY"]
    fields5 = sorted({k for r in md for k in r})
    buy2 = json.loads((EXP["exp2"] / "results" / "buy.json").read_text())
    out = {"exp4_preregistration_rules_verbatim": q, "exp2_buy_json_verbatim": buy2,
           "exp5_rows_BUY_fields": fields5, "exp5_rows_BUY_n": len(md),
           "operational_rule": ("BUY (exp4 S_vs_prompt): efficiency = delta_hill / delta_pass_pts with CIs; 'best knob' only "
                                "if the 90% CIs separate. Recomputed here with the one-statistic knob table (compliant-only "
                                "rarefied Hill-1 at depth 25)."), "per_task": {}}
    for t in ("T1", "T2"):
        k = kt[(kt.task == t) & ~kt.ceiling_row & ~kt.below_depth & kt.hill1_rarefied.notna()].copy()
        k = k[(k.type != "ban_single_pooled") & k.knob_class.isin(["diversity_knob", "ban"])]
        k["delta_hill"] = k.hill1_rarefied - 1.0
        k["efficiency"] = k.delta_hill / k.pass_points.clip(lower=1.0)
        k = k.sort_values("hill1_rarefied", ascending=False)
        top = k.head(5)
        sep = None
        if len(k) >= 2 and isinstance(k.iloc[0].get("hill1_ci90"), list) and isinstance(k.iloc[1].get("hill1_ci90"), list):
            sep = bool(k.iloc[0]["hill1_ci90"][0] > k.iloc[1]["hill1_ci90"][1])
        out["per_task"][t] = {"top_by_hill": [{"knob": r.knob, "type": r.type, "hill": r.hill1_rarefied, "ci90": r.get("hill1_ci90"),
                                               "pass_points": r.pass_points, "efficiency": r.efficiency} for _, r in top.iterrows()],
                              "best_knob_ci_separated": sep,
                              "advance": (top.iloc[0].knob if sep else "none (90% CIs do not separate)") if len(top) else "none",
                              "scope": "diversity knobs and bans only (named-mode cues, model swaps and the gen-then-select ceiling excluded)",
                              "positive_target_met_by": [r.knob for _, r in k.iterrows() if r.hill1_rarefied >= 2 and r.pass_points < 20]}
    return out


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("tables")
    rng = np.random.default_rng(20261020)
    df = load_all()
    logger.info(f"loaded {len(df)} labelled programs from 6 experiments")
    # harmonisation outputs
    pt = perturbation_table(df)
    harm = {"task_map": "t1/T1/grid -> T1; t2/T2/shortest_path -> T2",
            "label_synonyms_extra": EXTRA, "raw_labels_seen": {t: dict(c) for t, c in RAW_SEEN.items()},
            "unmapped_to_OTHER": dict(UNMAPPED),
            "condition_types": {f"{r.experiment}|{r.task}|{r.condition}": r.type for _, r in pt.iterrows()}}
    jdump(clean(harm), RES / "harmonise.json")
    refmap = {f"{r.experiment}|{r.task}|{r.condition}": (r.reference if isinstance(r.reference, str) and r.reference else None)
              for _, r in pt.iterrows()}
    jdump(clean(refmap), RES / "reference_map.json")
    pt.to_csv(TAB / "perturbation_table.csv", index=False)
    logger.info(f"perturbation table: {len(pt)} rows")
    # checks from the plan
    def comp_of(e, t, c):
        r = pt[(pt.experiment == e) & (pt.task == t) & (pt.condition == c)]
        return (json.loads(r.composition_correct.iloc[0]), int(r.correct.iloc[0]), json.loads(r.composition_attempted.iloc[0])) if len(r) else ({}, 0, {})
    cc, n, _ = comp_of("exp4", "T2", "steer:rand1:c=0.25:L=18")
    check("exp4 rand1 c=0.25 correct BF_SPFA", 26, cc.get("BF_SPFA"), "count", f"of {n} correct (plan: 26 of 79)",
          "exp4/data/samples.jsonl#condition==steer:rand1:c=0.25:L=18")
    check("exp4 rand1 c=0.25 n correct", 79, n, "count", source="exp4/data/samples.jsonl")
    cc, n, _ = comp_of("exp4", "T2", "steer:dc:c=0:L=18")
    check("exp4 c=0 correct BF_SPFA", 7, cc.get("BF_SPFA"), "count", f"of {n} correct (plan: 7 of 95)", "exp4/data/samples.jsonl")
    cc, n, _ = comp_of("exp5", "T2", "steer:random2")
    check("exp5 random2 c=0.5 correct BF_SPFA", 33, cc.get("BF_SPFA"), "count", f"of {n} correct (plan: 33 of 33)", "exp5/runs/samples.jsonl")
    cc, n, _ = comp_of("exp5", "T2", "steer:none:c=0")
    check("exp5 control correct DIJKSTRA", 100, cc.get("DIJKSTRA"), "count", f"of {n} correct", "exp5/runs/samples.jsonl")
    cc, n, ca = comp_of("exp6", "T2", "A3|instr_enumerate")
    check("exp6 enumeration BF_SPFA written", 33, ca.get("BF_SPFA"), "count", "attempted", "exp6/results/samples.jsonl")
    check("exp6 enumeration BF_SPFA correct", 8, cc.get("BF_SPFA"), "count", "correct", "exp6/results/samples.jsonl")
    riv = rival_statement(pt)
    # corrections
    mb = modal_ban_draws(df, rng)
    check("T2 pooled BF_SPFA substitutes", 272, mb["T2"]["pooled"]["substitute"], "count", source="0d(i)")
    check("T2 pooled compliant", 272, mb["T2"]["pooled"]["compliant"], "count", source="0d(i)")
    check("T1 pooled DFS substitutes", 116, mb["T1"]["pooled"]["substitute"], "count", source="0d(i)")
    check("T1 pooled compliant", 128, mb["T1"]["pooled"]["compliant"], "count", source="0d(i)")
    for (e, c), (k, n) in zip(MODAL_DRAWS["T1"], [(38, 38), (10, 18), (40, 41), (16, 18), (12, 13)]):
        d = next(x for x in mb["T1"]["draws"] if x["experiment"] == e)
        check(f"T1 {e} DFS/compliant", f"{k}/{n}", f"{d['substitute']}/{d['compliant']}", "string",
              note="string compare", source=d["source"])
        CHECKS[-1]["match"] = (f"{k}/{n}" == f"{d['substitute']}/{d['compliant']}")
    cum = cumulative_bans(df)
    kt = knob_table(df, pt, rng)
    kt.to_csv(TAB / "knob_table.csv", index=False)
    logger.info(f"knob table: {len(kt)} rows")
    pg = predict_gated(df)
    check("n gated events (primary, informative)", 2, pg["n_gated_primary"], "count", "plan expectation: only exp1's two modal bans; literal gate incl. sham bans = " + str(pg["n_gated_primary_literal"]), "0d(iv)")
    buy = buy_quotes(kt)
    sd = seeds(df)
    mo = missing_outputs(df, pt)
    check("exp1 DFS programs", 273, mo["exp1_dfs_failures"]["n_dfs"], "count", source="exp1/data/samples.jsonl")
    check("exp1 failing DFS programs", 161, mo["exp1_dfs_failures"]["n_failing"], "count", source="exp1/data/samples.jsonl")
    for kname, exp_n in (("wrong_answer", 127), ("timeout", 31), ("runtime_error", 3)):
        check(f"exp1 failing DFS {kname}", exp_n, mo["exp1_dfs_failures"]["kinds"].get(kname, 0), "count",
              source="exp1/data/samples.jsonl#test_error")
    sh = sham_bans(df)
    for t, ev, s, val in (("T2", "ban:floyd", "BF_SPFA", 0.23), ("T1", "ban:iddfs", "DFS", 0.12), ("T1", "ban:dijkstra", "DFS", 0.08)):
        r = next((x for x in sh["rows"] if x["task"] == t and x["event"] == ev and x["survivor"] == s), None)
        check(f"sham {ev} -> {s} share", val, r["share_ban"] if r else None, "0.01", "share among attempted", "exp1/data/samples.jsonl")
    # knob checks
    def krow(e, t, c):
        r = kt[(kt.experiment == e) & (kt.task == t) & (kt.condition == c)]
        return r.iloc[0] if len(r) else None
    r = krow("exp6", "T2", "A2|seed_semantic")
    check("T2 semantic seed rarefied Hill", 1.99, r.hill1_rarefied if r is not None else None, "0.05", "", "knob_table")
    for e, t, c, val in (("exp4", "T2", "steer:dc:c=0.25:L=18", 1.9), ("exp4", "T2", "steer:rand1:c=0.25:L=18", 1.9)):
        r = krow(e, t, c)
        check(f"{e} {c} rarefied Hill", val, r.hill1_rarefied if r is not None else None, "0.15", "", "knob_table")
    t1max = kt[(kt.task == "T1") & (kt.knob_class == "diversity_knob")].hill1_rarefied.max()
    check("no grid knob reaches Hill 2 (T1 max rarefied Hill over diversity knobs)", "<2", float(t1max), "string", "named-mode cues (mention:astar_gbfs 2.69) excluded: they recommend a named mode", "knob_table")
    CHECKS[-1]["match"] = bool(t1max < 2)
    out = {"perturbation_rows": len(pt), "rival": riv, "corrections": {"modal_ban_draws": mb, "cumulative_bans": cum},
           "predict_gated": pg, "buy": buy, "seeds": sd, "missing_outputs": mo, "sham": sh, "checks": CHECKS}
    jdump(clean(out), RES / "tables.json")
    logger.info(f"wrote results/tables.json; {sum(c['match'] for c in CHECKS)}/{len(CHECKS)} checks match")
    for c in CHECKS:
        logger.info(f"CHECK {'OK ' if c['match'] else 'MISMATCH'} {c['name']}: expected {c['expected']} recomputed {c['recomputed']} {c['note']}")


if __name__ == "__main__":
    main()
