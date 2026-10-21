"""S2 FREEZE (0f): screen inputs hashed into a commit chain before any S3 analysis output exists.

F1 m_candidates.json   M candidates on the 30 iteration-5 units (re-timed runtime merit from S1) + screen ranking
F2 e_inputs.json       iteration-4 FP8 rows, slots, seeds and directions the engine control must reproduce
F3 l3_screen.json      descriptive L3 fit (q_base^gamma vs uniform / association / q_tail) on iteration-5 events
F4 f2_screen.json      stored and harmonised twin opening margins
adjudication_design.json   S4 design (items, controls, judge, order seed, outcome rule) before any judge call
"""

from __future__ import annotations

import ast
import math
import os
import re
import time
from collections import Counter, defaultdict
from typing import Any

import numpy as np
from loguru import logger
from scipy import stats

from common import (ART, EXP22, ITER6_GENART, WS, Inputs, canon, clopper_pearson, fisher_two_sided, prov,
                    sha256_file, sha256_str, spearman, spearman_perm_p, parse_dictish)
from load import (BENCH_DIR, EXISTING, PANEL, PANEL_A, PANEL_B, PRIMARY13, UNITS30, base_pooled, beta_v6, t_u,
                  twin_modal)

FROZEN = WS / "frozen"
GENESIS = sha256_str("iter6_step0")


# --------------------------------------------------------------------------------------------- protocol strings
def protocol_strings(inp: Inputs) -> dict[str, str]:
    """SHARED / PANEL PROTOCOL v6 from the strategy script (local only: it names server paths), else from the published
    redacted copy, whose M CANDIDATES clause is identical (it names no path)."""
    if not inp.exists("protocol", "scripts/build_strategy.py"):
        return dict(inp.json("protocol", "protocol_strings_redacted.json")["strings"])
    src = inp.text("protocol", "scripts/build_strategy.py")
    out = {}
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if getattr(t, "id", None) in ("SHARED", "PANEL"):
                    out[t.id] = ast.literal_eval(node.value)  # literal only, the file is never executed
    return out


def m_clause(shared: str) -> str:
    i = shared.index("M CANDIDATES (frozen definitions):")
    j = shared.index(" ESCAPE:", i)
    return shared[i:j].strip()


# --------------------------------------------------------------------------------------------- runtime merit
def runtime_merit(retime: dict, U: dict) -> dict[str, dict[str, Any]]:
    rows = [r for r in retime["rows"] if r]
    out = {}
    for u in UNITS30:
        rs = [r for r in rows if r["unit"] == u]
        mode_t: dict[str, tuple[float, str, bool]] = {}
        for r in rs:
            if not r.get("passes_all") or r.get("t_median") is None:
                continue
            m = r["mode"]
            if m not in mode_t or r["t_median"] < mode_t[m][0]:
                mode_t[m] = (float(r["t_median"]), r["ref"], bool(r.get("unstable")))
        d = U[u]["default"]
        cat = U[u]["catalogue"]
        passing_cat = sorted(m for m in mode_t if m in cat)
        rec: dict[str, Any] = {"default": d, "K_passing": len(passing_cat), "passing_modes": passing_cat,
                               "n_refs": len(rs), "n_refs_passing": sum(bool(r.get("passes_all")) for r in rs),
                               "mode_time_s": {m: mode_t[m][0] for m in sorted(mode_t)},
                               "mode_ref": {m: mode_t[m][1] for m in sorted(mode_t)}}
        alts = {m: v for m, v in mode_t.items() if m != d and m in cat}
        if d in mode_t and alts:
            best = min(alts, key=lambda m: alts[m][0])
            rec.update(merit=math.log2(mode_t[d][0] / max(alts[best][0], 1e-9)), fastest_alt=best,
                       t_default=mode_t[d][0], t_fastest_alt=alts[best][0],
                       unstable=bool(mode_t[d][2] or alts[best][2]))
        else:
            rec.update(merit=None, status="NOT_COMPUTABLE: default or every alternative lacks a passing reference")
        out[u] = rec
    return out


def auc_perm(x: np.ndarray, y01: np.ndarray, n_perm: int, seed: int) -> tuple[float, float]:
    """Mann-Whitney AUC of x for class 1 over class 0, one-sided permutation p (class 1 higher)."""
    def auc(lbl: np.ndarray) -> float:
        a, b = x[lbl == 1], x[lbl == 0]
        if len(a) == 0 or len(b) == 0:
            return float("nan")
        return float(((a[:, None] > b[None, :]).sum() + 0.5 * (a[:, None] == b[None, :]).sum()) / (len(a) * len(b)))
    obs = auc(y01)
    rng = np.random.default_rng(seed)
    cnt = 0
    for _ in range(n_perm):
        if auc(rng.permutation(y01)) >= obs - 1e-12:
            cnt += 1
    return obs, (cnt + 1) / (n_perm + 1)


def f1_m_candidates(inp: Inputs, U: dict, retime: dict, shared: str) -> dict[str, Any]:
    clause = m_clause(shared)
    merit = runtime_merit(retime, U)
    units = {}
    for u in UNITS30:
        x = U[u]
        bp = base_pooled(x)
        n_corr = sum(bp.values())
        modal_base = sorted(bp.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if bp else None
        tm, tk, tn = twin_modal(x)
        units[u] = {
            "set": x["set"], "default": x["default"], "catalogue": x["catalogue"],
            "beta_v6": beta_v6(x), "beta_v6_incl_other": beta_v6(x, include_other=True),
            "beta_iter5_committed": x["beta_committed"], "beta_iter5_src": x["beta_committed_src"],
            "base_correct_pooled": dict(bp), "base_correct_n_pooled": n_corr,
            "base_chat_correct_n": sum(x["base_chat_correct"].values()),
            "base_plain_correct_n": sum(x["base_plain_correct"].values()), "base_src": x["base_src"],
            "LOW_SUPPORT": n_corr < 20, "base_modal_correct": modal_base,
            "replacement_class": int(modal_base is not None and modal_base != x["default"]),
            "runtime_merit": merit[u].get("merit"), "runtime_merit_detail": merit[u],
            "twin_modal": tm, "twin_modal_share_correct": (tk / tn) if tn else None,
            "twin_modal_share_of_N": tk / x["twin_n"], "twin_n": x["twin_n"], "twin_n_correct": tn,
            "twin_flag": "N 50 (v6 uses N 300 on new units)", "twin_src": x["twin_src"],
            "K_catalogue": len(x["catalogue"]), "K": merit[u]["K_passing"],
            "fork_margin": "no screen value",
            "E_u": x["E"], "E_u_alpha1": x["E1"], "E_u_alpha2": x["E2"], "E_src": x["E_src"],
            "E_flag": "bf16, ban-free unit, 8 directions, alphas 1-2 (v6 confirmation uses alpha up to 4)"}
    # screen ranking: Spearman, one-sided permutation p in the pre-declared direction; replacement class by AUC
    cands = {"beta_v6": 1, "runtime_merit": 1, "twin_modal_share_correct": -1, "K": 1}
    sets = {"all30": UNITS30, "new15": PANEL, "existing15": EXISTING}
    ranking: dict[str, Any] = {}
    for sname, us in sets.items():
        ranking[sname] = {}
        for c, sign in cands.items():
            pairs = [(units[u][c], units[u]["E_u"]) for u in us if units[u][c] is not None]
            xs = np.array([p[0] for p in pairs], float)
            es = np.array([p[1] for p in pairs], float)
            rho = spearman(xs, es)
            p = (spearman_perm_p(sign * xs, es, 100_000, 6001, "greater")
                 if not math.isnan(rho) else float("nan"))
            ranking[sname][c] = {"n": len(pairs), "sign": sign, "rho": rho, "oriented_rho": sign * rho,
                                 "p_one_sided_perm": p, "n_perm": 100_000}
        xs = np.array([units[u]["E_u"] for u in us], float)
        y = np.array([units[u]["replacement_class"] for u in us], int)
        a, p = auc_perm(xs, y, 20_000, 6002)
        ranking[sname]["replacement_class"] = {"n": len(us), "n_class1": int(y.sum()), "auc_E_class1_over_0": a,
                                               "p_one_sided_perm": p, "n_perm": 20_000}
    # descriptive replacement pattern on the new units (diverse = committed beta >= 0.2; movable = E > 0)
    pat = {}
    for bname in ("beta_iter5_committed", "beta_v6"):
        di = [u for u in PANEL if (units[u][bname] or 0) >= 0.2 and units[u]["E_u"] == 0]
        mv = [u for u in PANEL if units[u]["E_u"] > 0]
        a = sum(units[u]["replacement_class"] for u in di)
        c = sum(units[u]["replacement_class"] for u in mv)
        pat[bname] = {"diverse_immovable": di, "replacement_in_diverse_immovable": a, "movable": mv,
                      "replacement_in_movable": c,
                      "fisher_p_two_sided": fisher_two_sided(a, len(di) - a, c, len(mv) - c),
                      "record_claim": "3 of the 6 base-diverse immovable new units against 1 of the 7 movable"}
    for sub, us in (("primary13", PRIMARY13),):
        pat[f"{sub}_note"] = f"primary units {us}"
    return {"stage": "F1", "definitions_clause": clause, "definitions_sha256": sha256_str(clause),
            "beta_definition": "correct base programs (chat + plain pooled) whose catalogue label differs from the "
                               "twin default / all correct base programs; 'other' excluded from the numerator "
                               "(exp24 convention); beta_v6_incl_other beside",
            "units": units, "screen_ranking": ranking, "replacement_pattern": pat,
            "alpha_flag": "E_u at alphas 1-2 (iteration 5); v6 confirmation uses alpha up to 4",
            "retime_source": "retime/raw_times.json (S1, one harness, src/time_child.py)"}


# --------------------------------------------------------------------------------------------- F2
def f2_e_inputs(inp: Inputs) -> dict[str, Any]:
    tasks, arms = ("T10", "T2", "T03"), ("PN_a1", "PN_a2")
    real = {}
    for r in inp.jsonl("exp19", "data/realised.jsonl"):
        if r["task"] in tasks and r["arm"] in arms:
            real[(r["task"], r["w"], r["arm"], int(r["slot"]))] = r
    rows = []
    for s in inp.jsonl("exp19", "data/samples.jsonl"):
        if s.get("task") in tasks and s.get("arm") in arms:
            k = (s["task"], s["template"], s["arm"], int(s["slot"]))
            r = real.get(k, {})
            tm = parse_dictish(r.get("target_mean"))
            alpha = float(s["alpha"])
            rows.append({"task": s["task"], "w": s["template"], "arm": s["arm"], "slot": int(s["slot"]),
                         "direction_seed": s.get("direction_seed"), "u_seed": s.get("u_seed"),
                         "label": s.get("label"), "passed": s.get("passed") in (True, "True"),
                         "code_sha256": s.get("code_sha256"), "alpha": alpha,
                         "target_mean": {k2: float(v) for k2, v in tm.items()},
                         "ban_unit_per_block": {k2: float(v) / alpha for k2, v in tm.items()},
                         "disp_S": {k2: float(v) for k2, v in parse_dictish(r.get("disp_S")).items()},
                         "disp_R": {k2: float(v) for k2, v in parse_dictish(r.get("disp_R")).items()},
                         "realised_row_found": bool(r)})
    rows.sort(key=lambda z: (z["task"], z["arm"], z["w"], z["slot"]))
    # the 40 fresh directions of exp22
    esc = inp.json("exp22", "results/escape.json")
    arms22 = inp.json("exp22", "results/arms.json")
    seeds_conf = sorted({int(c["seed"]) for t in esc for c in esc[t].get("confirmed", [])})
    files = sorted(p.name for p in (EXP22 / "directions").glob("rand_91*.npy"))
    ids = sorted(int(re.findall(r"\d+", f)[0]) for f in files)
    arms_txt = canon(arms22)
    in_arms = [i for i in ids if f"d{i}" in arms_txt or str(i) in arms_txt]
    dirs = {}
    for i in ids:
        p = inp.path("exp22", f"directions/rand_{i}.npy")
        dirs[str(i)] = {"sha256": sha256_file(p), "file": prov("exp22", f"directions/rand_{i}.npy")}
    slots = defaultdict(list)
    pat = re.compile(r"^POP\w*_d(\d+)_a2\.0$")
    for r in inp.jsonl("exp22", "data/labels.jsonl"):
        m = pat.match(str(r.get("arm", "")))
        if m and r.get("task") in ("T10", "T2") and 9101 <= int(m.group(1)) <= 9140:
            slots[f"{r['task']}|{m.group(1)}"].append({"arm": r["arm"], "template": r.get("template"),
                                                       "sample_id": r.get("sample_id"), "label": r.get("label"),
                                                       "passed": r.get("passed") in (True, "True"),
                                                       "code_sha256": r.get("code_sha256")})
    units22 = defaultdict(list)
    for r in inp.jsonl("exp22", "data/realised_disp.jsonl"):
        m = pat.match(str(r.get("arm", "")))
        if m and r.get("task") in ("T10", "T2") and 9101 <= int(m.group(1)) <= 9140:
            units22[f"{r['task']}|{m.group(1)}"].append({"template": r.get("template"), "block_id": r.get("block_id"),
                                                         "target_mean": float(r.get("target_mean")),
                                                         "disp_smean_norm": {k: float(v) for k, v in
                                                                             parse_dictish(r.get("disp_smean_norm")).items()}})
    # reproduction targets (Clopper-Pearson 95%)
    sw = inp.json("exp19", "results/alpha_sweep.json")
    targets = {"exp19_PN_off_default": {}, "exp22_escape": {}}
    rec_pn = {"T10": (0.12, 0.60), "T2": (0.26, 0.54), "T03": (0.28, 0.50)}
    rec_es = {"T10": (0.38, 0.73), "T2": (0.18, 0.20), "T03": (0.30, 0.63)}
    dflt = {"T10": "union_find", "T2": "dijkstra", "T03": "full_sort"}
    for t in tasks:
        for e in sw[t]["sweep"]:
            if e["alpha"] in (1.0, 2.0):
                k = round(e["off_default_share"] * e["n"])
                kc = sum(v for m, v in e["correct_comp"].items() if m != dflt[t])
                targets["exp19_PN_off_default"][f"{t}|a{int(e['alpha'])}"] = {
                    "recorded": rec_pn[t][int(e["alpha"]) - 1], "off_default_share": e["off_default_share"],
                    "k": k, "n": e["n"], "cp95": clopper_pearson(k, e["n"]), "pass": e["pass"],
                    "correct_off_default_k": kc, "correct_off_default_share": kc / e["n"],
                    "src": prov("exp19", "results/alpha_sweep.json", f"{t}.sweep[alpha={e['alpha']}]")}
        for a in ("1.0", "2.0"):
            et = esc[t]["E_t"][a]
            targets["exp22_escape"][f"{t}|a{a[0]}"] = {
                "recorded": rec_es[t][int(a[0]) - 1], "E_t": et["E_t"], "k": et["n_confirmed"], "n": et["n_run"],
                "cp95": clopper_pearson(et["n_confirmed"], et["n_run"]),
                "src": prov("exp22", "results/escape.json", f"{t}.E_t.{a}")}
    src_files = {p: v["sha256"] for p, v in inp.files.items() if p.startswith((ART["exp19"], ART["exp22"]))}
    return {"stage": "F2", "pn_rows": rows, "n_pn_rows": len(rows),
            "pn_rows_src": [prov("exp19", "data/realised.jsonl"), prov("exp19", "data/samples.jsonl")],
            "directions": {"ids": ids, "expected": list(range(9101, 9141)), "ids_match_expected":
                           ids == list(range(9101, 9141)), "ids_in_escape_confirmed": [i for i in ids if i in seeds_conf],
                           "ids_referenced_in_arms_json": len(in_arms), "files": dirs},
            "alpha2_slots_T10_T2": dict(slots), "bench_unit_per_block_T10_T2": dict(units22),
            "reproduction_targets": targets, "source_sha256": src_files,
            "note": "exp19 'off_default_share' counts attempts (failing programs included); "
                    "'off_default_share_invalid_counts' also counts invalid output; neither is the correct-only "
                    "share, which is given beside as correct_off_default_share"}


# --------------------------------------------------------------------------------------------- F3
def _addone(counts: dict[str, float], cats: list[str]) -> dict[str, float]:
    tot = sum(counts.get(c, 0) for c in cats) + len(cats)
    return {c: (counts.get(c, 0) + 1) / tot for c in cats}


def l3_events(inp: Inputs, U: dict) -> list[dict[str, Any]]:
    """Iteration-5 landing events with their survivor sets, landing counts and forecast ingredients."""
    ev = []
    for u in ("A1", "A3", "A7"):
        x = U[u]
        lc = Counter()
        for c in x["escape_cells"]:
            if str(c.get("confirmed")) == "True":
                lc.update({k: int(v) for k, v in parse_dictish(c.get("landing_counts")).items()})
        S = [m for m in x["catalogue"] if m != x["default"]]
        ev.append({"event": f"QWEN_NEW_A|{u}", "unit": u, "S": S, "landing_counts": dict(lc),
                   "base_counts": dict(base_pooled(x)), "tail_counts": {k: v for k, v in x["twin_correct"].items()
                                                                        if k != x["default"]},
                   "assoc_counts": {k: v for k, v in (x.get("assoc_counts") or {}).items()},
                   "assoc_src": prov("exp25", "pooled_inputs.json", f"units[{u}].rivals.assoc_counts")})
    for u in ("B2", "B3", "B4", "B7"):
        x = U[u]
        S = [m for m in (x["forecasts"] or {}).get("BASE", {}) if m != "other"]
        ev.append({"event": f"QWEN_NEW_B|{u}", "unit": u, "S": S, "landing_counts": dict(x["landing_composition"]),
                   "base_counts": dict(base_pooled(x)),
                   "tail_counts": {k: v for k, v in x["twin_correct"].items() if k != x["default"]},
                   "assoc_dist": {k: v for k, v in x["forecasts"]["ASSOC"].items() if k != "other"},
                   "assoc_src": prov("exp26", "pooled_inputs.json", f"records[{u}].forecasts.ASSOC")})
    e2 = inp.json("exp28", "results/e_a2.json")
    pr = inp.json("exp28", "results/predictors.json")["units"]
    defined = {r["unit"]: r["q_assoc_defined"] for r in e2["log_scores"]}
    for e in e2["events"]:
        t = e["unit"]
        p = pr[t]
        att = Counter(p["pt_chat"].get("attempt_counts", {})) + Counter(p["pt_plain"].get("attempt_counts", {}))
        att = Counter({k: v for k, v in att.items() if k not in ("invalid",)})
        d = p["default"]["D"]
        ev.append({"event": f"GEMMA|{t}", "unit": t, "S": list(e["survivors"]), "landing_counts": e["landing_composition"],
                   "base_counts": dict(att), "base_basis": "valid attempts (LOW_CORRECT)",
                   "tail_counts": {k: v for k, v in p["default"]["correct_counts"].items() if k != d},
                   "assoc_dist": e["q_assoc"] if defined.get(t) else None,
                   "assoc_src": prov("exp28", "results/e_a2.json", f"events[{t}].q_assoc")})
    xa = inp.json("exp25", "results/extra_arm_a.json")
    for t in ("T03", "T10"):
        x = U[t]
        lc = Counter()
        for c in xa[t]["cells"]:
            if str(c.get("confirmed")) == "True":
                lc.update({k: int(v) for k, v in parse_dictish(c.get("landing_counts")).items()})
        S = [m for m in x["catalogue"] if m != x["default"]]
        asc = Counter(r["mapped"] for r in inp.jsonl("exp25", f"inputs/exp11/bench/{BENCH_DIR[t]}/association.jsonl")
                      if r.get("X") == x["default"] and r.get("mapped"))
        ev.append({"event": f"QWEN_BF16_REMEASURE|{t}", "unit": t, "S": S, "landing_counts": dict(lc),
                   "base_counts": dict(base_pooled(x)),
                   "tail_counts": {k: v for k, v in x["twin_bf16_landing_correct"].items()},
                   "assoc_counts": dict(asc),
                   "assoc_src": prov("exp25", f"inputs/exp11/bench/{BENCH_DIR[t]}/association.jsonl", "X=default")})
    return ev


def fp8_screen_landing_counts(inp: Inputs) -> dict[str, Counter]:
    """Correct off-default labels in exp22's confirmed (direction, alpha) cells: the FP8 landing counts."""
    esc = inp.json("exp22", "results/escape.json")
    conf = {t: {(int(c["seed"]), str(c["alpha"])) for c in esc[t].get("confirmed", [])} for t in
            ("T03", "T2", "T05", "T10", "T1")}
    pat = re.compile(r"^POP\w*_d(\d+)_a(\d\.\d)$")
    out = {t: Counter() for t in conf}
    defaults = {"T03": "full_sort", "T2": "dijkstra", "T05": "hash_map", "T10": "union_find", "T1": "bfs"}
    for r in inp.jsonl("exp22", "data/labels.jsonl"):
        t = r.get("task")
        if t not in conf:
            continue
        m = pat.match(str(r.get("arm", "")))
        if not m or (int(m.group(1)), m.group(2)) not in conf[t]:
            continue
        if r.get("passed") in (True, "True") and r.get("label") not in (None, "other", "invalid", defaults[t]):
            out[t][r["label"]] += 1
    return out


def f3_l3_screen(inp: Inputs, U: dict) -> dict[str, Any]:
    ev = l3_events(inp, U)
    fp8 = fp8_screen_landing_counts(inp)
    for t, lc in fp8.items():
        x = U[t]
        S = [m for m in x["catalogue"] if m != x["default"]]
        asc = Counter(r["mapped"] for r in inp.jsonl("exp25", f"inputs/exp11/bench/{BENCH_DIR[t]}/association.jsonl")
                      if r.get("X") == x["default"] and r.get("mapped")) if t in BENCH_DIR else Counter()
        ev.append({"event": f"QWEN_FP8_SCREEN|{t}", "unit": t, "S": S, "landing_counts": dict(lc),
                   "base_counts": dict(base_pooled(x)), "tail_counts": {},
                   "assoc_counts": dict(asc) if asc else None,
                   "assoc_src": prov("exp25", f"inputs/exp11/bench/{BENCH_DIR.get(t, t)}/association.jsonl")
                   if t in BENCH_DIR else "undefined (path task, no bench association file)",
                   "landing_src": prov("exp22", "data/labels.jsonl", "confirmed POP cells, correct off-default")})
    rng = np.random.default_rng(6003)
    grid = np.round(np.arange(0, 5.0001, 0.05), 2)
    out_ev = []
    for e in ev:
        S = [s for s in e["S"] if s != "other"]
        if len(S) < 2:
            continue
        lc = {k: v for k, v in e["landing_counts"].items() if k in S}
        progs = [k for k, v in lc.items() for _ in range(int(v))]
        if len(progs) < 2:
            e.update(status="too few landing programs")
            out_ev.append(e)
            continue
        qb = _addone(e["base_counts"], S + ["other"])
        qt = _addone(e["tail_counts"], S + ["other"])
        qb_s = np.array([qb[s] for s in S]) / sum(qb[s] for s in S)
        qt_s = np.array([qt[s] for s in S]) / sum(qt[s] for s in S)
        if e.get("assoc_counts"):
            qa = _addone(e["assoc_counts"], S + ["other"])
            qa_s = np.array([qa[s] for s in S]) / sum(qa[s] for s in S)
            a_def = True
        elif e.get("assoc_dist"):
            qa_s = np.array([max(e["assoc_dist"].get(s, 0.0), 1e-6) for s in S])
            qa_s = qa_s / qa_s.sum()
            a_def = True
        else:
            qa_s, a_def = np.ones(len(S)) / len(S), False
        idx = np.array([S.index(p) for p in progs])
        scores = {"q_base_gamma": [], "uniform": [], "association": [], "q_tail": [], "q_base_raw": []}
        gammas = []
        lg = np.log(qb_s)
        for _ in range(200):
            perm = rng.permutation(len(idx))
            h = len(idx) // 2
            fit, test = idx[perm[:h]], idx[perm[h:]]
            ll = [(np.log(np.exp(g * lg) / np.exp(g * lg).sum()))[fit].sum() for g in grid]
            g = float(grid[int(np.argmax(ll))])
            gammas.append(g)
            qg = np.exp(g * lg) / np.exp(g * lg).sum()
            scores["q_base_gamma"].append(float(np.log(qg)[test].mean()))
            scores["uniform"].append(float(np.log(np.ones(len(S)) / len(S))[test].mean()))
            scores["association"].append(float(np.log(qa_s)[test].mean()))
            scores["q_tail"].append(float(np.log(qt_s)[test].mean()))
            scores["q_base_raw"].append(float(np.log(qb_s)[test].mean()))
        nz = [i for i in range(len(S)) if qb_s[i] > min(qb_s) or (e["base_counts"].get(S[i], 0) > 0) or
              (e["tail_counts"].get(S[i], 0) > 0)]
        tau = None
        if len([s for s in S if e["base_counts"].get(s, 0) > 0 or e["tail_counts"].get(s, 0) > 0]) >= 3:
            tb = [e["base_counts"].get(s, 0) for s in S]
            tt = [e["tail_counts"].get(s, 0) for s in S]
            tau = float(stats.kendalltau(tb, tt, variant="b").statistic)
        e.update(S=S, n_landing_programs=len(progs), q_base=dict(zip(S, qb_s.round(6).tolist())),
                 q_tail=dict(zip(S, qt_s.round(6).tolist())), q_assoc=dict(zip(S, qa_s.round(6).tolist())),
                 assoc_defined=a_def, gamma_median=float(np.median(gammas)),
                 gamma_q=[float(np.quantile(gammas, 0.1)), float(np.quantile(gammas, 0.9))],
                 heldout_logscore={k: float(np.mean(v)) for k, v in scores.items()},
                 kendall_tau_b_base_vs_tail=tau, n_nonzero_used=len(nz))
        out_ev.append(e)
    scored = [e for e in out_ev if "heldout_logscore" in e]
    pooled = {k: float(np.mean([e["heldout_logscore"][k] for e in scored])) for k in
              ("q_base_gamma", "uniform", "association", "q_tail", "q_base_raw")}
    pooled_def = {k: float(np.mean([e["heldout_logscore"][k] for e in scored if e["assoc_defined"]]))
                  for k in ("q_base_gamma", "association")} if any(e["assoc_defined"] for e in scored) else {}
    taus = [e["kendall_tau_b_base_vs_tail"] for e in scored if e["kendall_tau_b_base_vs_tail"] is not None
            and not math.isnan(e["kendall_tau_b_base_vs_tail"])]
    pos, neg = sum(t > 0 for t in taus), sum(t < 0 for t in taus)
    return {"stage": "F3", "label": "DESCRIPTIVE SCREEN ONLY (N 50 twin tail, thin base support); never evidence",
            "events": out_ev, "n_events_scored": len(scored), "pooled_mean_heldout_logscore": pooled,
            "pooled_defined_assoc_only": pooled_def,
            "kendall": {"n_events": len(taus), "taus": taus, "positive": pos, "negative": neg,
                        "sign_test_p_two_sided": float(stats.binomtest(pos, pos + neg, 0.5).pvalue) if pos + neg else None},
            "method": "gamma grid 0-5 step 0.05, ML fit on a random half of the event's landing programs, mean "
                      "held-out log score per program on the other half, 200 seeded split-halves (seed 6003); "
                      "all forecasts add-one smoothed over S+other then renormalised over S; undefined association "
                      "scored as uniform, defined-only beside"}


# --------------------------------------------------------------------------------------------- F4
def f4_f2_screen(inp: Inputs, U: dict) -> dict[str, Any]:
    out = {}
    mb = inp.json("exp26", "results/margins.json")
    for u in PANEL:
        x = U[u]
        d = x["default"]
        if u in PANEL_A:
            stored = x["rivals"].get("opening_margin")
            raw = inp.json("exp25", f"results/margins/{u}.json")
            perw = raw["per_w"] if isinstance(raw["per_w"], dict) else parse_dictish(raw["per_w"])
            vals = []
            for w, res in perw.items():
                others = [v for m, v in res.items() if m != d]
                if d in res and others:
                    vals.append(res[d] - max(others))
            src = prov("exp25", f"results/margins/{u}.json", "per_w")
            formula = "exp25 src/unit_commit.py::margin_value: mean_W [lp(default) - max_{m != default} lp(m)], " \
                      "first <= 16 body tokens (src/gpu_worker.py::run_margin), twin templates W1-W5"
        else:
            stored = x["rivals"].get("R_margin")
            bm = mb.get(u, {}).get("by_mode", {})
            vals = []
            if d in bm:
                for w in bm[d]["logp"]:
                    others = [bm[m]["logp"][w] for m in bm if m != d]
                    if others:
                        vals.append(bm[d]["logp"][w] - max(others))
            src = prov("exp26", "results/margins.json", f"{u}.by_mode")
            formula = "exp26 src/quantities.py: R_margin = -(mean_W [lp(default) - max_{survivor} lp(survivor)]), " \
                      "first <= 16 body tokens (src/margins.py), twin templates W1-W5"
        m = float(np.mean(vals)) if vals else None
        out[u] = {"stored": stored, "stored_formula": formula, "harmonised_m": m,
                  "harmonised_formula": "mean_W [lp(default opening) - max over non-default catalogue modes lp]",
                  "exp_minus_m_over_T1.3": math.exp(-m / 1.3) if m is not None and m > -700 * 1.3 else None,
                  "src": src, "E_u": x["E"]}
    null_tasks = ["T2", "T1", "T03"]
    return {"stage": "F4", "units": out,
            "harmonisation": "HARMONISABLE by recomputation: both panels logged teacher-forced log-probs of the first "
                             "<= 16 body tokens under W1-W5; panel B stored the NEGATED margin over survivors, panel A "
                             "the margin over all other modes; m is recomputed from the raw per-template log-probs with "
                             "one formula. Stored values are kept beside.",
            "same_seed_null_tasks": null_tasks, "overlap_with_panel_units": sorted(set(null_tasks) & set(PANEL)),
            "overlap_statement": "empty: the same-seed null tasks are existing tasks, the margin screen covers new units"}


# --------------------------------------------------------------------------------------------- adjudication design
def adjudication_design(inp: Inputs) -> dict[str, Any]:
    na = inp.json("exp24", "results/novelty_audit.json")
    items = na["items"]
    def jcls(it: dict, k: str) -> str:
        j = parse_dictish(it.get(k)) if it.get(k) else {}
        return j.get("class", "")
    def votes(it: dict) -> list[str]:  # judge_c is blank when judges a and b agreed (exp24 tie-break design)
        return [c for c in (jcls(it, k) for k in ("judge_a", "judge_b", "judge_c")) if c]
    nov = [it for it in items if it.get("final_class") == "NOVEL_ALGORITHM"]
    deg = [it for it in items if len(votes(it)) >= 2 and all(c == "DEGENERATE" for c in votes(it))]
    known = [it for it in items if it.get("manual_class") == "KNOWN, OUTSIDE THE CATALOGUE" and len(votes(it)) >= 2 and
             all(c in ("CATALOGUE_VARIANT", "KNOWN_TECHNIQUE_OUTSIDE_CATALOGUE", "LABELLER_MISS", "DEGENERATE") for c in votes(it))
             and it.get("final_class") != "DEGENERATE"]
    deg = sorted(deg, key=lambda it: it["code_sha256"])[:3]
    known = sorted(known, key=lambda it: it["code_sha256"])[:2]
    cat_refs = [("R6", "binary_search"), ("T14", "heap"), ("T10", "dfs")]
    controls = []
    for t, m in cat_refs:
        rel = f"inputs/exp11/bench/{BENCH_DIR[t]}/references/{m}.py"
        controls.append({"control_id": f"CAT_{t}_{m}", "task": t, "expect": "CATALOGUE_VARIANT", "source": prov("exp25", rel),
                         "code_sha256": sha256_file(inp.path("exp25", rel)), "scrub": "identifiers and comments naming the mode removed"})
    for it in deg:
        controls.append({"control_id": f"DEG_{it['code_sha256'][:10]}", "task": it["task"], "expect": "DEGENERATE",
                         "source": prov("exp24", "results/novelty_audit.json", f"items[sha={it['code_sha256'][:12]}]"),
                         "code_sha256": it["code_sha256"]})
    for it in known:
        controls.append({"control_id": f"KNOWN_{it['code_sha256'][:10]}", "task": it["task"],
                         "expect": "KNOWN_TECHNIQUE_OUTSIDE_CATALOGUE",
                         "source": prov("exp24", "results/novelty_audit.json", f"items[sha={it['code_sha256'][:12]}]"),
                         "code_sha256": it["code_sha256"]})
    return {"stage": "S4 design", "items": [{"task": it["task"], "code_sha256": it["code_sha256"]} for it in nov],
            "n_items": len(nov), "controls": controls, "n_controls": len(controls),
            "judge_primary": "anthropic/claude-haiku-4.5",
            "judge_fallbacks": ["mistralai/mistral-medium-3.1", "meta-llama/llama-4-maverick"],
            "excluded_families": ["google", "openai", "deepseek (exp24 judges a/b/c)", "qwen (studied model)"],
            "order_seed": 6006, "temperature": 0, "passes": 2,
            "pass_orders": "pass 1 nearest-known solutions by descending similarity, pass 2 ascending",
            "gate": "judge valid only with >= 6 of 8 controls correct; else the fallback judge runs",
            "budget": {"plan_usd": 0.25, "hard_stop_usd": 0.45},
            "outcome_rule": {"zero": "'judges 14 of 48 (two of three), manual 0, third-family blind judge 0 of 14', "
                                     "rule-of-three bound 3/48",
                             "k_positive": "executor writes a blind manual verdict for those k with the earlier note "
                                           "hidden until its own verdict is written; reported 'unresolved' unless both "
                                           "say NOT NOVEL",
                             "not_completed": "'judges 14 of 48, manual 0'"},
            "output_schema": "{class in NOVEL_ALGORITHM|CATALOGUE_VARIANT|KNOWN_TECHNIQUE_OUTSIDE_CATALOGUE|"
                             "LABELLER_MISS|DEGENERATE, named_technique, nearest_known_index, rationale}"}


# --------------------------------------------------------------------------------------------- commit chain
def commit(files: list[str]) -> list[str]:
    log = WS / "commitments.log"
    prev = GENESIS
    lines = []
    if log.exists():
        old = [ln for ln in log.read_text().splitlines() if ln.strip()]
        if old:
            prev = old[-1].split(" | ")[-1]
            lines = old
    for f in files:
        sha = sha256_file(FROZEN / f)
        chain = sha256_str(prev + sha)
        lines.append(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} | frozen/{f} | {sha} | {prev} | {chain}")
        prev = chain
    log.write_text("\n".join(lines) + "\n")
    return lines


def run(inp: Inputs, U: dict, retime: dict) -> dict[str, Any]:
    FROZEN.mkdir(exist_ok=True)
    if (WS / "commitments.log").exists():  # a fresh freeze restarts the chain at genesis; the old chain is kept
        (WS / "commitments.log").rename(WS / f"commitments_superseded_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.log")
    ps = protocol_strings(inp)
    listing = sorted(os.listdir(ITER6_GENART)) if ITER6_GENART and ITER6_GENART.exists() else []
    (WS / "results").mkdir(exist_ok=True)
    (WS / "results" / "iter6_genart_listing.json").write_text(canon(
        {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "names_only": listing,
         "note": "names-only listing of iteration 6's gen_art folder at freeze time; nothing in it was opened"}))
    outs = {"m_candidates.json": f1_m_candidates(inp, U, retime, ps["SHARED"]),
            "e_inputs.json": f2_e_inputs(inp),
            "l3_screen.json": f3_l3_screen(inp, U),
            "f2_screen.json": f4_f2_screen(inp, U),
            "adjudication_design.json": adjudication_design(inp)}
    outs["m_candidates.json"]["protocol_sha256"] = {"SHARED": sha256_str(ps["SHARED"]), "PANEL": sha256_str(ps["PANEL"])}
    for name, obj in outs.items():
        (FROZEN / name).write_text(canon(obj))
        logger.info(f"frozen/{name}: {(FROZEN / name).stat().st_size / 1e3:.1f} kB")
    lines = commit(list(outs))
    return {"outs": outs, "chain": lines, "protocol": ps}
