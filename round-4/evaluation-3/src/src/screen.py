"""(0a) direction counts, Table 110, verification targets, per-task verdicts; (0i) frozen screen file."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from collections import Counter

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats as sps

from src.labels import BENCH12, QWEN14, catalogue, default_of
from src.paths import WS, cite, p
from src.stats import cell_seed, coverage_standardised_hill1, upper_bound_zero_of_k

DATA, RES, TAB = WS / "data", WS / "results", WS / "tables"
C1_SET = ["T03", "T05", "T06", "T10", "T1", "T2"]


def _load_rule():
    spec = importlib.util.spec_from_file_location("screen_rule", WS / "screen_rule.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _comp(s: str) -> dict:
    return json.loads(s) if isinstance(s, str) and s else {}


def random_direction_rows(knob: pd.DataFrame) -> list[dict]:
    """Per-direction rows for the screen: exp17 RAND90xx (HF, FP8 linears) and exp13 rand1-3 (HF, bf16)."""
    k = knob.set_index(["exp", "task", "arm", "dial", "precision"], drop=False)
    out = []
    sel = knob[(knob.family == "activation-random") & knob.exp.isin(["exp13", "exp17"]) & knob.task.isin(QWEN14)]
    for _, r in sel.iterrows():
        ref = k.loc[tuple(json.loads(r.ref_key))]
        if r.exp == "exp17":
            did, alpha = "exp17:" + r.arm.split("_a")[0], float(r.arm.split("_a")[1])
            engine = "hf-fp8"
        else:
            did, alpha, engine = "exp13:" + r.arm, 1.0, "hf-bf16"
        att = _comp(r.attempted_composition)
        d = default_of(r.task)
        cat = set(catalogue(r.task))
        offcat = {l: c for l, c in att.items() if l in cat and l != d}
        out.append({"task": r.task, "alpha": alpha, "direction_id": did, "engine": engine, "n": int(r.n),
                    "n_attempted": int(r.n_attempted), "n_default": int(att.get(d, 0)), "n_passed": int(r.n_correct),
                    "twin_n": int(ref.n), "twin_n_attempted": int(ref.n_attempted),
                    "twin_n_default": int(_comp(ref.attempted_composition).get(d, 0)),
                    "twin_n_passed": int(ref.n_correct), "offdef_cat_counts": dict(sorted(offcat.items())),
                    "n_other": int(att.get("other", 0)), "H1r25": None if not np.isfinite(r.H1r25) else round(float(r.H1r25), 4),
                    "pass_cost_pts": round(float(r.pass_cost_pts), 2), "qualify": bool(r.qualify),
                    "knob_row_id": r.row_id, "source": r.sources})
    return out


def ban_avoidance(knob: pd.DataFrame) -> tuple[dict, dict]:
    """Catalogue-only modal-ban avoidance: exp13 arm ban (bench); exp9 single-ban rows (T1/T2)."""
    av, src = {}, {}
    for t in BENCH12:
        r = knob[(knob.exp == "exp13") & (knob.task == t) & (knob.arm == "ban")].iloc[0]
        av[t] = float(r.cat_only_avoidance)
        src[t] = {"source": r.sources, "plain_avoidance": float(r.offdef_share), "n_attempted": int(r.n_attempted)}
    for t, arm in (("T1", "single:bfs"), ("T2", "single:dijkstra")):
        r = knob[(knob.exp == "exp9") & (knob.task == t) & (knob.arm == arm)].iloc[0]
        av[t] = float(r.cat_only_avoidance)
        src[t] = {"source": r.sources, "plain_avoidance": float(r.offdef_share), "n_attempted": int(r.n_attempted)}
    sp = json.loads(p("exp16", "results/screen_paths.json").read_text())["iteration2_ban_landings"]
    for t, key, dflt in (("T1", "t1", "bfs"), ("T2", "t2", "dijkstra")):
        d = sp[key]
        cat_nd = sum(v for l, v in d["counts"].items() if l in catalogue(t) and l != dflt)
        src[t]["exp16_screen_paths_pooled_cat_only_avoidance"] = cat_nd / d["n_attempted"]
        src[t]["exp16_screen_paths_source"] = cite("exp16", "results/screen_paths.json")
    return av, src


def direction_counts_table(drows: list[dict]) -> pd.DataFrame:
    rule = _load_rule()
    recs = []
    for t in QWEN14:
        for a in (1.0, 2.0):
            ra = [r for r in drows if r["task"] == t and r["alpha"] == a]
            if not ra:
                continue
            esc = [r for r in ra if rule.escape_of(r)[0]]
            qual = [r for r in esc if r["qualify"]]
            qual_all = [r for r in ra if r["qualify"]]
            rec = {"task": t, "alpha": a, "engine": "pooled", "n_run": len(ra), "n_escape": len(esc),
                   "n_qualify": len(qual_all), "n_escape_and_qualify": len(qual),
                   "escaping_ids": ";".join(r["direction_id"] for r in esc),
                   "qualifying_ids": ";".join(r["direction_id"] for r in qual_all),
                   "denominator": f"{len(esc)}/{len(ra)}"}
            for eng in ("hf-fp8", "hf-bf16"):
                re_ = [r for r in ra if r["engine"] == eng]
                rec[f"n_run_{eng}"] = len(re_)
                rec[f"n_escape_{eng}"] = sum(rule.escape_of(r)[0] for r in re_)
                rec[f"n_qualify_{eng}"] = sum(r["qualify"] for r in re_)
            recs.append(rec)
    return pd.DataFrame(recs)


def table110(knob: pd.DataFrame) -> pd.DataFrame:
    sel = knob[(knob.exp == "exp17") & knob.arm.isin(["RAND9001_a2.0", "RAND9002_a2.0", "RAND9003_a2.0", "ADD_a2.0"])]
    return sel[["task", "arm", "n", "n_attempted", "offdef_share", "cat_only_avoidance", "pass_rate", "pass_cost_pts",
                "H1r25", "attempted_composition", "correct_composition", "sources"]].rename(
        columns={"offdef_share": "avoidance"}).sort_values(["task", "arm"])


# ------------------------------------------------------------------------------------------------ targets
def _cell(knob, exp, task, arm, dial=None):
    q = knob[(knob.exp == exp) & (knob.task == task) & (knob.arm == arm)]
    if dial is not None:
        q = q[q.dial == json.dumps(dial, sort_keys=True)]
    return q.iloc[0] if len(q) else None


def verification_targets(knob: pd.DataFrame, drows: list[dict]) -> pd.DataFrame:
    rule = _load_rule()
    T: list[dict] = []

    def add(tid, desc, expected, recomputed, match, source, kind):
        T.append({"target_id": tid, "description": desc, "expected": json.dumps(expected),
                  "recomputed": json.dumps(recomputed), "match": bool(match), "tolerance": kind, "source": source})

    def dir_rows(task, alpha, eng="hf-fp8"):
        return [r for r in drows if r["task"] == task and r["alpha"] == alpha and r["engine"] == eng]

    src17 = cite("exp17", "data/labels.jsonl")
    src13 = cite("exp13", "data/samples.jsonl")
    # T03 alpha 1
    ra = dir_rows("T03", 1.0)
    esc = [r for r in ra if rule.escape_of(r)[0]]
    add("T03_a1_escape", "T03 alpha 1: escaping directions of 15 (exp17)", "7/15", f"{len(esc)}/{len(ra)}",
        len(esc) == 7 and len(ra) == 15, src17, "exact")
    hs = sorted([r["H1r25"] for r in esc if r["n_passed"] / r["n"] >= 0.96 and r["H1r25"]], reverse=True)[:5]
    exp_h = [2.92, 2.42, 2.32, 2.14, 2.10]
    add("T03_a1_hill", "T03 escaping-direction Hill at pass >= 0.96", exp_h, hs,
        len(hs) == 5 and all(abs(a - b) <= 0.03 for a, b in zip(hs, exp_h)), src17, "+-0.03")
    best = max(esc, key=lambda r: r["H1r25"] or 0)
    bc = _comp(_cell(knob, "exp17", "T03", best["direction_id"].split(":")[1] + "_a1.0").correct_composition)
    add("T03_best_comp", "T03 best direction correct composition", {"size_k_heap": 19, "quickselect": 16, "full_sort": 15},
        bc, bc == {"size_k_heap": 19, "quickselect": 16, "full_sort": 15}, src17, "exact")
    # T2
    ra = dir_rows("T2", 1.0)
    esc = [r for r in ra if rule.escape_of(r)[0]]
    minpass = min(r["n_passed"] / r["n"] for r in esc) if esc else None
    add("T2_a1_escape", "T2 alpha 1: escaping of 15 at pass >= 0.88", "3/15, min pass 0.88",
        f"{len(esc)}/{len(ra)}, min pass {minpass}", len(esc) == 3 and len(ra) == 15 and abs(minpass - 0.88) <= 0.005,
        src17, "exact/+-0.005")
    best = max(esc, key=lambda r: r["H1r25"] or 0)
    c = _cell(knob, "exp17", "T2", best["direction_id"].split(":")[1] + "_a1.0")
    bc = _comp(c.correct_composition)
    ok = bc.get("dijkstra") == 26 and bc.get("bf_spfa") == 22 and abs(c.pass_rate - 0.96) <= 0.005 and abs(c.H1r25 - 1.97) <= 0.03
    add("T2_best", "T2 best direction: Dijkstra 26, BF/SPFA 22, pass 0.96, Hill 1.97",
        {"dijkstra": 26, "bf_spfa": 22, "pass": 0.96, "H1r25": 1.97},
        {**bc, "pass": c.pass_rate, "H1r25": round(c.H1r25, 3)}, ok, src17, "exact/+-0.03")
    lands = sorted({l for r in esc for l in r["offdef_cat_counts"]})
    add("T2_landing", "T2 every escaping landing is BF/SPFA", ["bf_spfa"], lands, lands == ["bf_spfa"], src17, "exact")
    # T05
    r1 = dir_rows("T05", 1.0)
    r2 = dir_rows("T05", 2.0)
    e1 = [r for r in r1 if rule.escape_of(r)[0]]
    e2 = [r for r in r2 if rule.escape_of(r)[0]]
    h2 = sorted([r["H1r25"] for r in e2], reverse=True)
    p2 = sorted(r["n_passed"] / r["n"] for r in e2)
    add("T05_escape", "T05: 0 of 3 at alpha 1, 2 of 3 at alpha 2 (exp17)", "0/3; 2/3",
        f"{len(e1)}/{len(r1)}; {len(e2)}/{len(r2)}", len(e1) == 0 and len(r1) == 3 and len(e2) == 2 and len(r2) == 3,
        src17, "exact")
    add("T05_a2_hill", "T05 alpha-2 escaping Hill 2.13 and 1.90 at pass 1.00", [2.13, 1.90, 1.0, 1.0], h2 + p2,
        len(h2) == 2 and abs(h2[0] - 2.13) <= 0.03 and abs(h2[1] - 1.90) <= 0.03 and all(abs(x - 1.0) <= 0.005 for x in p2),
        src17, "+-0.03")
    comps = [_comp(_cell(knob, "exp17", "T05", r["direction_id"].split(":")[1] + "_a2.0").correct_composition) for r in e2]
    hm = any(cc.get("hash_map") == 26 and cc.get("brute_force") == 23 for cc in comps)
    add("T05_a2_comp", "T05 alpha-2 best: hash map 26, brute force 23", {"hash_map": 26, "brute_force": 23}, comps, hm,
        src17, "exact")
    # T06
    r2 = dir_rows("T06", 2.0)
    e2 = [r for r in r2 if rule.escape_of(r)[0]]
    cc = [_comp(_cell(knob, "exp17", "T06", r["direction_id"].split(":")[1] + "_a2.0").correct_composition) for r in e2]
    pp = [round(r["n_passed"] / r["n"], 4) for r in e2]
    ok = len(e2) == 1 and len(r2) == 3 and cc[0].get("sort_adjacent") == 30 and sum(cc[0].values()) == 41 and abs(pp[0] - 0.82) <= 0.005
    add("T06_a2", "T06: 1 of 3 at alpha 2; sort_adjacent 30 of 41 correct, pass 0.82", "1/3; 30/41; 0.82",
        f"{len(e2)}/{len(r2)}; {cc}; {pp}", ok, src17, "exact/+-0.005")
    # T04
    r4 = dir_rows("T04", 1.0) + dir_rows("T04", 2.0)
    e4 = [r for r in r4 if rule.escape_of(r)[0]]
    add("T04_escape", "T04: 0 of 6 direction-alpha cells escape (exp17)", "0/6", f"{len(e4)}/{len(r4)}",
        len(e4) == 0 and len(r4) == 6, src17, "exact")
    # exp13 random rows
    c = _cell(knob, "exp13", "T03", "rand3")
    cc = _comp(c.correct_composition)
    add("exp13_T03_rand", "exp13 T03 random row: quickselect 34, full sort 9", {"quickselect": 34, "full_sort": 9}, cc,
        cc.get("quickselect") == 34 and cc.get("full_sort") == 9, src13, "exact")
    c = _cell(knob, "exp13", "T10", "rand3")
    cc = _comp(c.correct_composition)
    add("exp13_T10_rand", "exp13 T10 random row: DFS 13 of 50 at pass 1.00", {"dfs": 13, "n": 50, "pass": 1.0},
        {"dfs": cc.get("dfs"), "n": int(c.n), "pass": c.pass_rate}, cc.get("dfs") == 13 and c.n == 50 and c.pass_rate == 1.0,
        src13, "exact")
    # exp4
    src4 = cite("exp4", "data/samples.jsonl")
    c = _cell(knob, "exp4", "T2", "steer:dc", {"c": 0.25, "layer": 18})
    ci = json.loads(c.H1r25_ci90)
    add("exp4_dc025", "exp4 decommitment c=0.25 (T2): 1.913 [1.705, 2.088] at 17 points",
        {"H1r25": 1.913, "ci90": [1.705, 2.088], "cost": 17},
        {"H1r25": round(c.H1r25, 3), "ci90": ci, "ci90_iid": json.loads(c.H1r25_ci90_iid), "cost": round(c.pass_cost_pts, 1)},
        abs(c.H1r25 - 1.913) <= 0.03 and abs(c.pass_cost_pts - 17) <= 0.5, src4, "+-0.03 / +-0.5 pts")
    c = _cell(knob, "exp4", "T2", "steer:rand1", {"c": 0.25, "layer": 18})
    add("exp4_rand1", "exp4 rand1 (T2): 1.858 at 16 points", {"H1r25": 1.858, "cost": 16},
        {"H1r25": round(c.H1r25, 3), "cost": round(c.pass_cost_pts, 1)},
        abs(c.H1r25 - 1.858) <= 0.03 and abs(c.pass_cost_pts - 16) <= 0.5, src4, "+-0.03 / +-0.5 pts")
    # exp6
    src6 = cite("exp6", "results/samples.jsonl")
    c = _cell(knob, "exp6", "T2", "A2:seed_semantic")
    add("exp6_semantic", "exp6 semantic seed on T2: 1.940 [1.770, 2.094]", {"H1r25": 1.94, "ci90": [1.77, 2.094]},
        {"H1r25": round(c.H1r25, 3), "ci90": json.loads(c.H1r25_ci90), "cost": round(c.pass_cost_pts, 1)},
        abs(c.H1r25 - 1.94) <= 0.03, src6, "+-0.03")
    # exp13 rows
    vals = {a: _cell(knob, "exp13", "T03", a) for a in ("oneshot", "persistent", "iter1")}
    hv = {a: (round(v.H1r25, 3), round(v.pass_cost_pts, 1)) for a, v in vals.items()}
    add("T03_vetoes", "T03 vetoes 1.89-1.91 at 2 points", "1.89-1.91 @ 2", hv,
        all(1.86 <= v[0] <= 1.94 and abs(v[1] - 2) <= 0.5 for v in hv.values()), src13, "+-0.03")
    c = _cell(knob, "exp13", "T03", "bandpatch")
    add("T03_bandpatch", "T03 band patch 1.98", 1.98, round(c.H1r25, 3), abs(c.H1r25 - 1.98) <= 0.03, src13, "+-0.03")
    trip = {a: _cell(knob, "exp13", "T10", a) for a in ("rand3", "novelty", "bandpatch")}
    tv = {a: (round(v.H1r25, 3), round(v.pass_cost_pts, 1)) for a, v in trip.items()}
    ok = abs(tv["rand3"][0] - 1.76) <= 0.03 and abs(tv["novelty"][0] - 1.68) <= 0.03 and abs(tv["bandpatch"][0] - 1.88) <= 0.03 \
        and all(abs(v[1]) <= 0.5 for v in tv.values())
    add("T10_rows", "T10 random 1.76, novelty 1.68, band patch 1.88, all at 0 points",
        {"rand": 1.76, "novelty": 1.68, "bandpatch": 1.88, "cost": 0}, tv, ok, src13, "+-0.03")
    c = _cell(knob, "exp13", "T04", "novelty")
    add("T04_novelty", "T04 novelty 1.97-1.99 at pass 1.00", "1.97-1.99 @ 1.00", (round(c.H1r25, 3), c.pass_rate),
        1.94 <= c.H1r25 <= 2.02 and c.pass_rate == 1.0, src13, "+-0.03")
    c = _cell(knob, "exp13", "T06", "iter1")
    cc = _comp(c.correct_composition)
    ok = abs(c.H1r25 - 2.49) <= 0.03 and abs(c.pass_cost_pts - 2) <= 0.5 and cc == {"sort_adjacent": 32, "floyd": 9,
                                                                                    "hash_set": 7, "index_marking": 1}
    add("T06_iter1", "T06 iter1 2.49 at 2 points (sort_adjacent 32, floyd 9, hash_set 7, index_marking 1)",
        {"H1r25": 2.49, "cost": 2, "comp": {"sort_adjacent": 32, "floyd": 9, "hash_set": 7, "index_marking": 1}},
        {"H1r25": round(c.H1r25, 3), "cost": c.pass_cost_pts, "comp": cc}, ok, src13, "+-0.03")
    c = _cell(knob, "exp13", "T08", "novelty")
    add("T08_novelty", "T08 novelty 1.90 at 24 points", {"H1r25": 1.90, "cost": 24},
        {"H1r25": round(c.H1r25, 3), "cost": c.pass_cost_pts}, abs(c.H1r25 - 1.90) <= 0.03 and abs(c.pass_cost_pts - 24) <= 0.5,
        src13, "+-0.03")
    # Table 110 alpha-2 rows (exp17)
    def t110(task, arm):
        return _cell(knob, "exp17", task, arm)

    c = t110("T03", "RAND9001_a2.0")
    add("T110_kth", "Table 110: kth smallest alpha-2 avoidance 0.96", 0.96, round(c.offdef_share, 4),
        abs(c.offdef_share - 0.96) <= 0.005, src17, "+-0.005")
    c = t110("T06", "RAND9003_a2.0")
    att = _comp(c.attempted_composition)
    land = sorted(((k, v) for k, v in att.items() if k != "hash_set"), key=lambda kv: -kv[1])
    add("T110_dup", "Table 110: find duplicate alpha-2 avoidance 0.86, landing on sort and adjacent check",
        {"avoidance": 0.86, "modal_landing": "sort_adjacent"}, {"avoidance": round(c.offdef_share, 4), "landing": land},
        abs(c.offdef_share - 0.86) <= 0.005 and land and land[0][0] == "sort_adjacent", src17, "+-0.005")
    a2, a3 = t110("T05", "RAND9002_a2.0"), t110("T05", "RAND9003_a2.0")
    add("T110_twosum", "Table 110: two sum alpha-2 avoidance 0.48 and 0.36", [0.48, 0.36],
        [round(a2.offdef_share, 4), round(a3.offdef_share, 4)],
        abs(a2.offdef_share - 0.48) <= 0.005 and abs(a3.offdef_share - 0.36) <= 0.005, src17, "+-0.005")
    d6, d5 = t110("T06", "ADD_a2.0"), t110("T05", "ADD_a2.0")
    add("T110_add", "Table 110: ADD at alpha 2 gives 0.00 on find duplicate and on two sum", [0.0, 0.0],
        [round(d6.offdef_share, 4), round(d5.offdef_share, 4), f"pass {d5.pass_rate:.2f} on two sum"],
        d6.offdef_share == 0 and d5.offdef_share == 0, src17, "exact")
    q = knob[knob.task.isin(["R1", "R3", "R6", "T11", "T13", "T14"]) & knob.model.str.startswith("Qwen")
             & knob["class"].isin(["knob"]) & (knob.pass_cost_pts <= 20) & (knob.H1r25 >= 1.5)]
    add("immovable_six", "R1, R3, R6, T11, T13, T14: no Qwen knob row reaches Hill 1.5 under 20 points",
        0, q[["exp", "task", "arm", "H1r25", "pass_cost_pts"]].round(3).values.tolist(), len(q) == 0,
        "tables/knob_table.csv", "exact")
    return pd.DataFrame(T)


# ------------------------------------------------------------------------------------------------ verdicts
NON_ACTIVATION = ("decoding", "prompt:")


def per_task_verdict(knob: pd.DataFrame, dcounts: pd.DataFrame) -> pd.DataFrame:
    recs = []
    for t in QWEN14:
        q_all = knob[(knob.task == t) & knob.model.str.startswith("Qwen") & knob["class"].isin(["knob"])
                     & knob.H1r25.notna() & knob.pass_cost_pts.notna()]
        # ban-derived band patching is shown and flagged but never ranked as a knob
        bp = q_all[q_all.family == "activation-ban-derived"]
        q = q_all[q_all.family != "activation-ban-derived"]
        row = {"task": t, "bandpatch_H1r25_flagged": (round(float(bp.H1r25.max()), 3) if len(bp) else None)}
        for cap in (5, 20):
            qq = q[q.pass_cost_pts <= cap].sort_values(["H1r25", "pass_cost_pts"], ascending=[False, True])
            if len(qq):
                b = qq.iloc[0]
                row[f"best_le{cap}_row"] = b.row_id
                row[f"best_le{cap}_arm"] = f"{b.exp}:{b.arm}{'' if b.dial == '{}' else ' ' + b.dial}"
                row[f"best_le{cap}_class"] = b.family
                row[f"best_le{cap}_H1r25"] = round(float(b.H1r25), 3)
                row[f"best_le{cap}_cost"] = round(float(b.pass_cost_pts), 1)
            else:
                row[f"best_le{cap}_arm"] = None
        dc = dcounts[dcounts.task == t]
        row["n_qualifying_random_directions"] = int(dc.n_qualify.sum()) if len(dc) else 0
        row["n_random_directions_run"] = int(dc.n_run.sum()) if len(dc) else 0
        na = q[q.family.str.startswith(NON_ACTIVATION) & (q.family != "activation-ban-derived") & (q.pass_cost_pts <= 20)
               & (q.H1r25 >= 1.5)]
        row["non_activation_reaches_1.5_le20"] = bool(len(na))
        row["non_activation_best"] = (f"{na.sort_values('H1r25').iloc[-1].exp}:{na.sort_values('H1r25').iloc[-1].arm}"
                                      if len(na) else None)
        # lowest-cost qualifying row (any class except controls / ban-derived)
        qual = q[(q.H1r25 >= 2) & (q.pass_cost_pts <= 20) & (q.family != "activation-ban-derived")]
        if len(qual):
            lc = qual.sort_values(["pass_cost_pts", "H1r25"], ascending=[True, False]).iloc[0]
            row["lowest_cost_qualifying"] = f"{lc.exp}:{lc.arm} ({lc.family}, {lc.pass_cost_pts:.0f} pts, H {lc.H1r25:.2f})"
            row["lowest_cost_qualifying_family"] = lc.family
        else:
            row["lowest_cost_qualifying"] = None
            row["lowest_cost_qualifying_family"] = None
        # coverage-standardised sensitivity: Hill-1 at the minimum coverage across this task's knob cells
        cells = q[(q.n_correct >= 10)]
        if len(cells):
            covs = cells.coverage.astype(float)
            target = float(covs.min())
            best_cs = None
            for _, c in cells.iterrows():
                cnt = list(_comp(c.correct_composition).values())
                v, m = coverage_standardised_hill1(cnt, target, np.random.default_rng(cell_seed(c.row_id + "|cov")))
                if best_cs is None or (np.isfinite(v) and c.pass_cost_pts <= 20 and v > best_cs[1]):
                    best_cs = (f"{c.exp}:{c.arm}", v, m) if c.pass_cost_pts <= 20 else best_cs
            row["coverage_target"] = round(target, 4)
            if best_cs:
                row["cov_std_best_le20"] = best_cs[0]
                row["cov_std_best_le20_hill"] = round(float(best_cs[1]), 3)
                row["cov_std_best_le20_m"] = best_cs[2]
        b20 = row.get("best_le20_H1r25")
        sent = (f"{t}: best non-control knob within 20 points is {row.get('best_le20_arm')} "
                f"(Hill {b20}, {row.get('best_le20_cost')} pts, {row.get('best_le20_class')}); "
                f"{row['n_qualifying_random_directions']} of {row['n_random_directions_run']} random direction-alpha cells qualify; "
                f"non-activation knob reaching 1.5 within 20 points: {'yes (' + str(row['non_activation_best']) + ')' if row['non_activation_reaches_1.5_le20'] else 'no'}.")
        row["sentence"] = sent
        row["review_sentence_diff"] = ("review sentence not among the declared inputs; the generated sentence is the "
                                       "replacement")
        recs.append(row)
    return pd.DataFrame(recs)


# ------------------------------------------------------------------------------------------------ stage
def run_screen_stage() -> None:
    rule = _load_rule()
    knob = pd.read_parquet(DATA / "knob.parquet")
    drows = random_direction_rows(knob)
    av, av_src = ban_avoidance(knob)
    dcounts = direction_counts_table(drows)
    dcounts.to_csv(TAB / "random_direction_counts.csv", index=False)
    table110(knob).to_csv(TAB / "table110_alpha2.csv", index=False)
    vt = verification_targets(knob, drows)
    expl = {"immovable_six": ("denominator: the review's sentence holds only for non-exposure, non-ban knobs; counting the "
                              "exp13 T14 modal ban (Hill 1.78 at 17 points) and the exp14 exposure arms (five shown "
                              "programs of Y: R6 exponential-search vetoes, T11 NAMED fenwick / patience, T14 UNNAMED "
                              "quickselect-counts), rows reach Hill >= 1.5 within 20 points; the recomputed rows become "
                              "the record"),
            "exp4_dc025": "interval: the 90% CI differs from the recorded [1.705, 2.088] because the cluster unit differs "
                          "(exp4 had no template field: program-level bootstrap); the point value matches",
            "T110_twosum": ("denominator: one RAND9002 alpha-2 row on two sum is not an attempted program, so the "
                            "off-default share is 1 - 26/49 = 0.469 on the attempted denominator (0.48 is 1 - 26/50 on all "
                            "rows); 0.469 becomes the record value")}
    vt["explanation"] = [expl.get(t, "") if not m else "" for t, m in zip(vt.target_id, vt.match)]
    vt.to_csv(TAB / "verification_targets.csv", index=False)
    logger.info(f"verification targets: {int(vt.match.sum())}/{len(vt)} matched")
    for _, r in vt[~vt.match].iterrows():
        logger.warning(f"target mismatch {r.target_id}: expected {r.expected} got {r.recomputed}")
    ptv = per_task_verdict(knob, dcounts)
    ptv.to_csv(TAB / "per_task_verdict.csv", index=False)
    # screen core via the stdlib rule
    src_sha = {cite("exp17", "data/labels.jsonl"): None, cite("exp13", "data/samples.jsonl"): None,
               cite("exp9", "data/samples.jsonl"): None}
    from src.stages import sha256_file
    for c in list(src_sha):
        aid, rel = c.split(":", 1)
        src_sha[c] = sha256_file(p(aid, rel))
    inp = {"direction_rows": [{k: v for k, v in r.items() if k in (
        "task", "alpha", "direction_id", "engine", "n", "n_attempted", "n_default", "n_passed", "twin_n",
        "twin_n_attempted", "twin_n_default", "twin_n_passed", "offdef_cat_counts")} for r in drows],
        "ban_avoidance": {t: round(v, 6) for t, v in av.items()}, "tasks": QWEN14, "c1_event_set": C1_SET,
        "source_sha256": src_sha}
    (WS / "screen_input.json").write_text(json.dumps(inp, indent=1, sort_keys=True))
    core = rule.build_core(inp)
    b = rule.canonical_bytes(core)
    (WS / "screen.json").write_bytes(b)
    sha = hashlib.sha256(b).hexdigest()
    (WS / "screen.sha256").write_text(f"{sha}  screen.json\n")
    logger.info(f"screen.json sha256 {sha}; movable {core['movable_tasks']}")
    # extras (not hashed)
    movable = {t: core["tasks"][t]["movable"] for t in QWEN14}
    comp = {t: int(av[t] >= 0.5) for t in QWEN14}
    from src.stats import balanced_accuracy, fisher_2x2
    fis = fisher_2x2([movable[t] for t in QWEN14], [comp[t] for t in QWEN14], alternative="greater")
    ba = balanced_accuracy([movable[t] for t in QWEN14], [comp[t] for t in QWEN14])
    k_mov = sum(movable.values())
    n_comp = sum(comp.values())
    power = {}
    for t in QWEN14:
        k = sum(1 for r in drows if r["task"] == t)
        n_esc = sum(rule.escape_of(r)[0] for r in drows if r["task"] == t)
        power[t] = {"K_direction_alpha_cells": k, "n_escape": n_esc,
                    "ub90_per_direction_escape_if_zero": round(upper_bound_zero_of_k(k), 4) if n_esc == 0 else None}
    per_engine = {}
    for t in QWEN14:
        for eng in ("hf-fp8", "hf-bf16"):
            rr = [r for r in drows if r["task"] == t and r["engine"] == eng]
            if rr:
                per_engine.setdefault(t, {})[eng] = {
                    "n_run": len(rr), "n_escape": sum(rule.escape_of(r)[0] for r in rr),
                    "escaping": [r["direction_id"] + f"@a{r['alpha']}" for r in rr if rule.escape_of(r)[0]],
                    "H1r25": {r["direction_id"] + f"@a{r['alpha']}": r["H1r25"] for r in rr}}
    disc = []
    for t in C1_SET:
        if not movable[t]:
            disc.append({"task": t, "note": f"{t} is in the frozen C1 event set by the hypothesis's decree but does not "
                                             "escape mechanically under the pass >= 0.8 x twin rule; the set is not edited."})
    for t in QWEN14:
        if movable[t] and not comp[t]:
            disc.append({"task": t, "note": "movable but catalogue-only ban avoidance < 0.5 (screen rule violated)"})
        if not movable[t] and comp[t]:
            disc.append({"task": t, "note": "not movable but ban avoidance >= 0.5 (screen rule violated)"})
    extras = {"per_direction_rows": drows, "per_engine": per_engine, "power_note": power,
              "power_note_text": "With K direction-alpha cells and 0 escapes, the one-sided 90% upper bound on a task's "
                                 "per-direction escape probability is 1 - 0.1^(1/K) (0.54 at K=3, 0.32 at K=6, 0.14 at K=15): "
                                 "the immovable side is weakly tested; more directions belong to the plan-subspace artifact.",
              "fisher_movable_vs_avoidance": {**fis, "label": "descriptive only: screen, not confirmation (rule read off the same data)"},
              "hypergeometric_one_sided_if_perfect": 1 / math.comb(len(QWEN14), max(k_mov, 1)) if k_mov == n_comp else None,
              "balanced_accuracy": ba, "n_movable": k_mov, "n_ban_avoidance_ge_0_5": n_comp,
              "ban_avoidance_sources": av_src, "discrepancies": disc,
              "escaping_engine_per_task": {t: sorted({r["engine"] for r in drows if r["task"] == t and rule.escape_of(r)[0]})
                                           for t in QWEN14},
              "screen_sha256": sha}
    (WS / "screen_extras.json").write_text(json.dumps(extras, indent=1, default=str))
    summary = {"sha256": sha, "movable_tasks": core["movable_tasks"], "n_movable": k_mov,
               "fisher_p_descriptive": fis["p"], "table": fis["table"], "balanced_accuracy": ba,
               "verification": {"n_targets": int(len(vt)), "n_matched": int(vt.match.sum())},
               "E": {f"{t}_a{int(a)}": core["tasks"][t][f"alpha_{int(a)}"]["E_t"] for t in QWEN14 for a in (1.0, 2.0)}}
    (RES / "screen_summary.json").write_text(json.dumps(summary, indent=1, default=str))
