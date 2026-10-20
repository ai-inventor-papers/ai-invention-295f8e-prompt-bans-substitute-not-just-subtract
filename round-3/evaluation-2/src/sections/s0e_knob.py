"""(0e) Knob table under a declared class rule, rebuilt from per-sample files.

Unit = experiment x task x condition x decoding (x arm for exp5). Reference = that experiment's own baseline for the
same task (same decoding, except decoding knobs, which are referenced to the default-decoding baseline); the map is
written to tables/knob_reference_map.csv. Class rule (regex + manual map, tables/knob_class_map.csv):
CONTROL (listed, never ranked), KNOB, CEILING (generate-then-select). Statistic: rarefied Hill-1 over correct compliant
programs at depth 25 (mean of exp(H) over 1,000 subsamples without replacement); rows with < 25 such programs are
flagged and not ranked. Also: second-algorithm share (Wilson), 90% bootstrap interval, pass points with a Newcombe 90%
interval.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from common.paths import RESULTS, SEED, TABLES, write_json
from common.rows import MODAL, T1_K6, T2_K5
from common.stats import boot_rarefied_hill1, newcombe_diff, rarefied_hill1, wilson

DEPTH = 25
PRIMARY_EXPS = ("exp1", "exp2", "exp3", "exp4", "exp5", "exp6", "exp8", "exp9", "exp12")
DEFAULT_DEC = "T1.0|kNone|p1.0|thinkFalse"
AUDIT_TARGETS = [
    {"name": "semantic seed T2 (exp6 seed_semantic)", "exp": "exp6", "task": "t2", "condition": "seed_semantic",
     "target": "BF/SPFA 61, Dijkstra 30, 7 pass points, Hill 1.935 [1.534, 2.076]", "hill": 1.935, "points": 7},
    {"name": "A* mention (exp1 mention:astar_gbfs, a CONTROL)", "exp": "exp1", "task": "t1",
     "condition": "mention:astar_gbfs", "target": "Hill 2.69 at 11 points", "hill": 2.69, "points": 11},
    {"name": "modal ban T2 (exp1 ban:dijkstra)", "exp": "exp1", "task": "t2", "condition": "ban:dijkstra",
     "target": "Hill 1.0", "hill": 1.0, "points": None},
    {"name": "modal ban T2 (exp9 single:dijkstra)", "exp": "exp9", "task": "t2", "condition": "single:dijkstra",
     "target": "Hill 1.0", "hill": 1.0, "points": None},
    {"name": "gen-then-select T1 (exp6)", "exp": "exp6", "task": "t1", "condition": "gen_then_select",
     "target": "3-4 algorithms at 24-42 points", "hill": None, "points": None},
    {"name": "gen-then-select T2 (exp6)", "exp": "exp6", "task": "t2", "condition": "gen_then_select",
     "target": "3-4 algorithms at 24-42 points", "hill": None, "points": None},
]


def k6(r: dict[str, Any]) -> str:
    if r["exp"] == "exp9" and r["task"] == "t1" and r["label_fine"] in ("dijkstra_unit", "unit_dijkstra"):
        return "dijkstra"
    lab = r["label"]
    cat = T1_K6 if r["task"] == "t1" else T2_K5
    if lab in cat:
        return lab
    if lab == "idastar":
        return "idastar"
    return "unparseable" if lab == "unparseable" else "other"


def unit_key(r: dict[str, Any]) -> tuple:
    arm = r["arm"] if r["exp"] in ("exp5",) else (r["arm"] if r["exp"] == "exp12" else "")
    if r["exp"] == "exp12" and r["arm"] not in ("C1_fresh_pool", "E5_crn"):
        arm = r["arm"]
    return (r["exp"], r["model"], r["task"], r["condition"], arm or "", r["decoding_key"])


def classify(exp: str, task: str, cond: str, arm: str, dec: str, banned: list[str]) -> tuple[str, str]:
    c = cond.lower()
    if exp == "exp6" and c == "gen_then_select":
        return "CEILING", "generate-then-select"
    if c.startswith("mention") or "listall" in c or c.startswith("forced") or c.startswith("masked") \
            or c in ("baseline_empty",) or c == "b" and exp == "exp8":
        return "CONTROL", {"b": "neutral twin"}.get(c, "mention twin / listing / forced or masked prompt / format")
    if exp == "exp5" and arm in ("instruct_tf", "base_tf", "base_chat") and c == "baseline":
        return "CONTROL", "format or weights arm (reference set, not a knob)"
    if c in ("steer:dc:c=0:l=18", "removal:hooked_alpha0") or (exp == "exp5" and arm.startswith("steer:none")):
        return "CONTROL", "hooked c = 0 baseline"
    if banned:
        if MODAL.get(task) not in banned:
            return "CONTROL", "sham / absent-mode ban (modal algorithm not banned)"
        if exp in ("exp8",) and c in ("c", "d", "k0", "k1", "k2"):
            return "KNOB", "activation intervention on a ban prompt (KV splice / attention knockout)"
        return "KNOB", "prompt ban (single, multi or two-step)"
    if c.startswith("steer") or c.startswith("removal") or (exp == "exp5" and arm.startswith("steer")):
        return "KNOB", "activation intervention (steering / removal / random direction)"
    if c.startswith("seed_"):
        return "KNOB", "seed"
    if c.startswith("instr_") or c.startswith("enumerate"):
        return "KNOB", "instruction"
    if c in ("baseline", "baseline_t13") and dec != DEFAULT_DEC:
        return "KNOB", "decoding setting"
    if c in ("baseline", "baseline_t13", "a") or c.startswith("baseline"):
        return "REFERENCE", "baseline"
    return "KNOB", "other perturbation"


def reference_for(exp: str, task: str, cond: str, arm: str, dec: str, cls: str, why: str,
                  units: dict[tuple, list]) -> tuple | None:
    def find(cond_ref: str, dec_ref: str, arm_ref: str = "") -> tuple | None:
        for k in units:
            if k[0] == exp and k[2] == task and k[3] == cond_ref and k[5] == dec_ref and (k[4] == arm_ref):
                return k
        return None

    if exp == "exp8":
        return find("b", dec)
    if exp == "exp4" and cond.startswith("steer"):
        return find("steer:dc:c=0:L=18", dec) or find("baseline", dec)
    if exp == "exp2" and cond.startswith("removal"):
        return find("removal:hooked_alpha0", dec)
    if exp == "exp5":
        if arm.startswith("steer"):
            return find("baseline", dec, "steer:none:c=0") or find("baseline", dec, "instruct_chat")
        if arm == "base_tf":
            return find("baseline", dec, "base_tf")
        if arm == "base_chat":
            return find("baseline", dec, "base_chat")
        return find("baseline", dec, "instruct_chat")
    if exp == "exp12":
        if arm == "E5_crn" and cond == "ban":
            return find("baseline", dec, "E5_crn")
        return find("baseline", "T1.0|kNone|p1.0|thinkFalse", "E5_crn")
    d_ref = DEFAULT_DEC if why == "decoding setting" else dec
    for cand in ("baseline",):
        k = find(cand, d_ref)
        if k:
            return k
    # fall back: default-decoding baseline of the same experiment and task
    for k in units:
        if k[0] == exp and k[2] == task and k[3] == "baseline":
            return k
    return None


def stats_for(rs: list[dict[str, Any]], rng: np.random.Generator, boot: bool = True) -> dict[str, Any]:
    banned = rs[0]["banned_set"]
    labs = [k6(r) for r in rs]
    cc = [lab for lab, r in zip(labs, rs) if r["passed"] is True and lab != "unparseable" and lab not in banned]
    cnt = Counter(cc)
    counts = [v for _, v in cnt.most_common()]
    n_pass = sum(1 for r in rs if r["passed"] is True)
    out = {"N": len(rs), "n_pass": n_pass, "pass_rate": n_pass / len(rs), "n_cc": len(cc),
           "cc_counts": dict(cnt.most_common()), "n_algorithms_cc": len(cnt),
           "hill_rar25": rarefied_hill1(counts, DEPTH, 1000, rng) if len(cc) >= DEPTH else math.nan,
           "rankable_n": len(cc) >= DEPTH}
    sec = counts[1] if len(counts) > 1 else 0
    out["second_share"] = sec / len(cc) if cc else math.nan
    out["second_share_wilson"] = wilson(sec, len(cc)) if cc else (math.nan, math.nan)
    out["second_algorithm"] = cnt.most_common()[1][0] if len(counts) > 1 else None
    if boot and len(cc) >= DEPTH:
        out["hill_rar25_ci90"] = boot_rarefied_hill1(counts, DEPTH, n_boot=2000, n_sub=200, rng=rng, conf=0.90)
    else:
        out["hill_rar25_ci90"] = (math.nan, math.nan)
    return out


def build(rows: list[dict[str, Any]], exps: tuple[str, ...], models: tuple[str, ...], rng: np.random.Generator,
          shuffle_classes: bool = False) -> list[dict[str, Any]]:
    units: dict[tuple, list] = defaultdict(list)
    for r in rows:
        if r["exp"] in exps and r["model"] in models and r["task"] in ("t1", "t2"):
            if r["exp"] == "exp12" and r["arm"] == "C3_continuation":
                continue
            units[unit_key(r)].append(r)
    out = []
    cache: dict[tuple, dict[str, Any]] = {}
    for k, rs in sorted(units.items(), key=lambda kv: str(kv[0])):
        exp, model, task, cond, arm, dec = k
        cls, why = classify(exp, task, cond, arm, dec, rs[0]["banned_set"])
        ref = reference_for(exp, task, cond, arm, dec, cls, why, units) if cls != "REFERENCE" else None
        st = stats_for(rs, rng)
        rec = {"exp": exp, "model": model, "task": task, "condition": cond, "arm": arm, "decoding": dec,
               "class": cls, "class_reason": why, "banned_set": rs[0]["banned_set"], **st,
               "reference": "|".join(ref[3:6]) if ref else None, "source": rs[0]["source"]}
        if ref:
            if ref not in cache:
                cache[ref] = stats_for(units[ref], rng, boot=False)
            rf = cache[ref]
            d, lo, hi = newcombe_diff(rf["n_pass"], rf["N"], st["n_pass"], st["N"], conf=0.90)
            rec.update({"ref_pass_rate": rf["pass_rate"], "pass_points": 100 * d, "pass_points_ci90": (100 * lo, 100 * hi),
                        "ref_hill_rar25": rf["hill_rar25"], "ref_N": rf["N"]})
        else:
            rec.update({"ref_pass_rate": None, "pass_points": None, "pass_points_ci90": (None, None)})
        out.append(rec)
    if shuffle_classes:          # placebo 5: classes shuffled across rows
        cl = [(r["class"], r["class_reason"]) for r in out]
        rng.shuffle(cl)
        for r, (c, w) in zip(out, cl):
            r["class"], r["class_reason"] = c, w
    return out


def ranking(table: list[dict[str, Any]], max_points: float = 20.0) -> list[dict[str, Any]]:
    cand = [r for r in table if r["class"] == "KNOB" and r["rankable_n"] and r["pass_points"] is not None
            and r["pass_points"] < max_points and np.isfinite(r["hill_rar25"])]
    cand.sort(key=lambda r: -r["hill_rar25"])
    for r in cand:
        lo, hi = r["hill_rar25_ci90"]
        r["interval_includes_2"] = bool(np.isfinite(lo) and lo <= 2 <= hi)
    return cand


def run(rows: list[dict[str, Any]]) -> dict[str, Any]:
    rng = np.random.default_rng(SEED)
    primary = build(rows, PRIMARY_EXPS, ("Qwen/Qwen3-8B",), rng)
    supp_base = build(rows, ("exp5",), ("Qwen/Qwen3-8B-Base",), rng)
    supp_llama = build(rows, ("exp10",), ("meta-llama/Llama-3.1-8B-Instruct",), rng)
    rank = ranking(primary)
    best = rank[0] if rank else None
    any2 = [r for r in rank if r["hill_rar25"] >= 2.0]
    if best:
        verdict = (f"Among {len(rank)} rankable KNOB rows costing fewer than 20 pass points, "
                   + (f"{len(any2)} reach rarefied Hill-1 >= 2 at depth 25; " if any2 else "none reaches rarefied Hill-1 of 2 at depth 25; ")
                   + f"the best is {best['exp']} {best['task']} {best['condition']} ({best['decoding']}) at "
                   f"{best['hill_rar25']:.3f} [90% {best['hill_rar25_ci90'][0]:.3f}, {best['hill_rar25_ci90'][1]:.3f}] "
                   f"for {best['pass_points']:.1f} pass points"
                   + ("; its interval includes 2." if best.get("interval_includes_2") else "; its interval excludes 2."))
    else:
        verdict = "No KNOB row is rankable (>= 25 correct compliant programs and < 20 pass points)."
    repro = []
    for tgt in AUDIT_TARGETS:
        r = next((x for x in primary if x["exp"] == tgt["exp"] and x["task"] == tgt["task"] and x["condition"] == tgt["condition"]
                  and x["decoding"] in (DEFAULT_DEC, "T1.0|kNone|p1.0|thinkNone")), None)
        if r is None:
            repro.append({**tgt, "rebuilt": None, "explanation": "row not found in rebuilt table"})
            continue
        dh = (r["hill_rar25"] - tgt["hill"]) if (tgt["hill"] is not None and np.isfinite(r["hill_rar25"])) else None
        dp = (r["pass_points"] - tgt["points"]) if (tgt["points"] is not None and r["pass_points"] is not None) else None
        expl = []
        if dh is not None and abs(dh) > 0.05:
            expl.append("Hill differs by > 0.05: the audit's statistic is not known to be rarefied at depth 25 over "
                        "correct compliant programs (plug-in Hill on all correct programs is "
                        f"{_plugin(r['cc_counts']):.3f}); the class set here merges 'other' into one class")
        if dp is not None and abs(dp) > 1:
            expl.append("pass points differ by > 1: different reference row (this table uses the experiment's own "
                        "baseline at the same decoding)")
        repro.append({**tgt, "rebuilt": {"cc_counts": r["cc_counts"], "hill_rar25": r["hill_rar25"],
                                         "hill_rar25_ci90": r["hill_rar25_ci90"], "hill_plugin_cc": _plugin(r["cc_counts"]),
                                         "pass_points": r["pass_points"], "pass_points_ci90": r["pass_points_ci90"],
                                         "n_algorithms_cc": r["n_algorithms_cc"], "class": r["class"]},
                      "diff_hill": dh, "diff_points": dp, "explanation": "; ".join(expl) or "within tolerance"})
    out = {"n_rows_primary": len(primary), "n_rows_primary_without_exp5": sum(1 for r in primary if r["exp"] != "exp5"),
           "n_rows_audit": 249, "n_rows_supp_base": len(supp_base), "n_rows_supp_llama": len(supp_llama),
           "class_counts": dict(Counter(r["class"] for r in primary)), "ranking": rank[:25],
           "n_rankable_knobs": len(rank), "verdict": verdict, "reproduction": repro, "depth": DEPTH,
           "primary": primary, "supplementary_base": supp_base, "supplementary_llama": supp_llama}
    write_json(RESULTS / "knob_table.json", out)
    cols = ["exp", "model", "task", "condition", "arm", "decoding", "class", "class_reason", "N", "pass_rate", "n_cc",
            "cc_counts", "n_algorithms_cc", "hill_rar25", "hill_rar25_ci90", "rankable_n", "second_algorithm",
            "second_share", "second_share_wilson", "reference", "ref_pass_rate", "pass_points", "pass_points_ci90", "source"]
    pd.DataFrame(primary)[cols].to_csv(TABLES / "knob_table.csv", index=False)
    pd.DataFrame(supp_base + supp_llama)[cols].to_csv(TABLES / "knob_table_supplementary.csv", index=False)
    pd.DataFrame([{k: r[k] for k in ("exp", "task", "condition", "arm", "decoding", "class", "class_reason")}
                  for r in primary + supp_base + supp_llama]).to_csv(TABLES / "knob_class_map.csv", index=False)
    pd.DataFrame([{k: r[k] for k in ("exp", "task", "condition", "arm", "decoding", "reference")}
                  for r in primary + supp_base + supp_llama]).to_csv(TABLES / "knob_reference_map.csv", index=False)
    pd.DataFrame(repro).to_csv(TABLES / "knob_reproduction.csv", index=False)
    logger.info(verdict)
    return out


def _plugin(cnt: dict[str, int]) -> float:
    from common.stats import hill1

    return hill1(list(cnt.values())) if cnt else math.nan
