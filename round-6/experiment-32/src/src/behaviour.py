#!/usr/bin/env python3
"""S3 bookkeeping on the labelled behaviour rows: defaults (commit #1), substitutes Y*, MIXED conditions, forced
adherence, per-task reports (correct / attempted compositions, pass rate, rarefied correct-only Hill-1 at depth 25,
catalogue-only ban avoidance, W4 separately, 'other' and 'invalid' columns), the batch-invariance check (S2c) and
the style re-gate (two blind code judges + tie-break, before any NLA call).

Usage: python src/behaviour.py defaults | report | regate
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import (ADHERENT_MIN, BUDGET_MSG, DATA_DIR, DEFAULT_SHARE, DEPTH, EXP8_TASK, MIXED_SHARE, PRED_DIR,
                 RESULTS_DIR, ROOT, TASKS, TEMPLATE_IDS, YSTAR_MIN, YSTAR_SHARE, bench_paths, read_json, read_jsonl,
                 setup_logging, stable_seed, write_json)
from commit import commit
import prompts as PR

LABELS = DATA_DIR / "labels.jsonl"


def load_labels(arms: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    rows = {r["sample_id"]: r for r in read_jsonl(LABELS)}
    out = list(rows.values())
    if arms:
        out = [r for r in out if r["arm"] in arms]
    return out


def correct(r: dict[str, Any]) -> bool:
    return bool(r.get("passed")) and bool(r.get("valid"))


def hill1_rarefied(labels: list[str], depth: int = DEPTH, n_draw: int = 1000, seed: int = 0) -> float | None:
    if not labels:
        return None
    rng = np.random.default_rng(seed)
    arr = np.array(labels)
    d = min(depth, len(arr))
    vals = []
    for _ in range(n_draw):
        sub = rng.choice(arr, size=d, replace=False)
        c = np.array(list(Counter(sub.tolist()).values()), dtype=float)
        p = c / c.sum()
        vals.append(math.exp(-(p * np.log(p)).sum()))
    return float(np.mean(vals))


def composition(rows: list[dict[str, Any]]) -> dict[str, Any]:
    cor = [r["label"] for r in rows if correct(r)]
    att = [r["label"] for r in rows]
    return {"n": len(rows), "n_correct": len(cor), "pass_rate": len(cor) / len(rows) if rows else None,
            "correct": dict(Counter(cor).most_common()), "attempted": dict(Counter(att).most_common()),
            "n_other": sum(l == "other" for l in att), "n_invalid": sum(l == "invalid" for l in att),
            "hill1_d25": hill1_rarefied(cor, seed=len(cor)), "hill1_flag_lt25": len(cor) < DEPTH}


def stage_defaults() -> dict[str, Any]:
    rows = load_labels(("TWIN",))
    out: dict[str, Any] = {"rule": f"DEFAULT := modal correct twin label if share >= {DEFAULT_SHARE}", "tasks": {}}
    for t in TASKS:
        rs = [r for r in rows if r["task"] == t and int(r["slot"]) < 10]
        comp = composition(rs)
        cor = Counter(r["label"] for r in rs if correct(r))
        D, share = None, None
        if cor:
            m, c = cor.most_common(1)[0]
            share = c / sum(cor.values())
            D = m if (share >= DEFAULT_SHARE and m not in ("other", "invalid")) else None
        minority = 1 - share if share is not None else None
        out["tasks"][t] = {"default": D, "modal_share": share, "n_twin": len(rs), "composition": comp,
                           "mixed": bool(minority is not None and minority >= MIXED_SHARE)}
    rec = commit("commit1_defaults", out)
    logger.info(f"commit1: {json.dumps({t: (v['default'], round(v['modal_share'] or 0, 2)) for t, v in out['tasks'].items()})}")
    return rec


def per_task_report() -> dict[str, Any]:
    c1 = read_json(PRED_DIR / "commit1_defaults.json")
    rows = load_labels()
    rep: dict[str, Any] = {"tasks": {}}
    for t in TASKS:
        D = c1["tasks"][t]["default"]
        tw = [r for r in rows if r["task"] == t and r["arm"] == "TWIN" and int(r["slot"]) < 10]
        tw_extra = [r for r in rows if r["task"] == t and r["arm"] == "TWIN" and int(r["slot"]) >= 10]
        bn = [r for r in rows if r["task"] == t and r["arm"] == "BAN"]
        fo = [r for r in rows if r["task"] == t and r["arm"] == "FORCED"]
        sd = [r for r in rows if r["task"] == t and r["arm"] == "SEED"]
        cat = [c["mode"] for c in PR.catalogue(t)]
        R: dict[str, Any] = {"default": D, "twin": composition(tw), "twin_extra_slots": composition(tw_extra) if tw_extra else None}
        if bn:
            R["ban"] = composition(bn)
            R["ban_noW4"] = composition([r for r in bn if r["template"] != "W4"])
            R["ban_W4"] = composition([r for r in bn if r["template"] == "W4"])
            R["ban_by_template"] = {w: composition([r for r in bn if r["template"] == w]) for w in TEMPLATE_IDS}
            cb = [r for r in bn if correct(r)]
            # catalogue-only ban avoidance: share of correct ban programs whose label is a catalogue mode other than D
            R["ban_avoidance_catalogue"] = (sum(r["label"] in cat and r["label"] != D for r in cb) / len(cb)) if cb else None
            R["ban_default_rate_attempted"] = sum(r["label"] == D for r in bn) / len(bn)
            nd = Counter(r["label"] for r in cb if r["label"] != D and r["label"] not in ("other", "invalid"))
            ystar = None
            if nd:
                m, c = nd.most_common(1)[0]
                if c / len(cb) >= YSTAR_SHARE and c >= YSTAR_MIN:
                    ystar = m
            R["Ystar"] = ystar
            R["Ystar_count"] = nd.most_common(1)[0][1] if nd else 0
            R["Ystar_share_of_correct_ban"] = (nd.most_common(1)[0][1] / len(cb)) if (nd and cb) else None
            R["ban_failure"] = ystar is None
            labs = Counter(r["label"] for r in cb)
            R["ban_mixed"] = bool(cb and (1 - labs.most_common(1)[0][1] / len(cb)) >= MIXED_SHARE)
            # paired twin/ban flips on the same CRN slots
            tmap = {(r["template"], int(r["slot"])): r for r in tw}
            R["paired_flip"] = Counter(f"{tmap[(r['template'], int(r['slot']))]['label']}->{r['label']}"
                                       for r in bn if (r["template"], int(r["slot"])) in tmap).most_common(12)
        adh = {}
        for m in cat:
            fr = [r for r in fo if r.get("mode") == m]
            adh[m] = {"n": len(fr), "adherence": (sum(correct(r) and r["label"] == m for r in fr) / len(fr)) if fr else None,
                      "pass_rate": (sum(correct(r) for r in fr) / len(fr)) if fr else None,
                      "labels": dict(Counter(r["label"] for r in fr).most_common())}
        R["forced"] = adh
        if sd:
            R["seed"] = composition(sd)
        rep["tasks"][t] = R
    return rep


def batch_invariance() -> dict[str, Any]:
    rows = load_labels()
    b1 = {(r["template"], int(r["slot"])): r for r in rows if r["arm"] == "ENGCHK_C1"}
    bn = {(r["template"], int(r["slot"])): r for r in rows if r["arm"] == "TWIN" and r["task"] == "T03"}
    keys = sorted(set(b1) & set(bn))
    agree = sum(b1[k]["label"] == bn[k]["label"] for k in keys)
    tok_eq = sum(b1[k]["code_sha256"] == bn[k]["code_sha256"] for k in keys)
    return {"n": len(keys), "label_agreement": agree / len(keys) if keys else None, "code_identical": tok_eq,
            "pass": bool(keys and agree / len(keys) >= 0.9)}


def stage_report() -> dict[str, Any]:
    rep = per_task_report()
    rep["batch_invariance"] = batch_invariance()
    eng = RESULTS_DIR / "engine_check.json"
    rep["engine_check"] = read_json(eng) if eng.exists() else None
    write_json(RESULTS_DIR / "behaviour.json", rep)
    for t, R in rep["tasks"].items():
        logger.info(f"{t}: default={R['default']} twin={R['twin']['correct']} pass={R['twin']['pass_rate']:.2f}; "
                    f"Y*={R.get('Ystar')} ban={R.get('ban', {}).get('correct')}")
    return rep


# ------------------------------------------------------------------------------------------------ style re-gate
def stage_regate(n_per_task: int = 30) -> dict[str, Any]:
    """30 programs per task stratified by label x arm; two blind code judges (gemini-2.5-flash, gpt-4.1-mini) and a
    DeepSeek tie-break; PASS iff the frozen labeller agrees with the adjudicated label on >= 27/30."""
    bench_paths()
    rows = [r for r in load_labels(("TWIN", "BAN", "FORCED", "SEED")) if r.get("valid") and r.get("code")]
    out: dict[str, Any] = {"tasks": {}, "judges": ["google/gemini-2.5-flash", "openai/gpt-4.1-mini",
                                                    "deepseek/deepseek-chat-v3.1"]}
    picks: dict[str, list[dict[str, Any]]] = {}
    for t in TASKS:
        rs = [r for r in rows if r["task"] == t]
        strata: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for r in rs:
            strata.setdefault((r["label"], r["arm"]), []).append(r)
        rng = np.random.default_rng(stable_seed("regate", t) % (2 ** 32))
        keys = sorted(strata)
        chosen: list[dict[str, Any]] = []
        # round-robin over strata
        pools = {k: list(rng.permutation(len(strata[k]))) for k in keys}
        while len(chosen) < min(n_per_task, len(rs)):
            progressed = False
            for k in keys:
                if pools[k] and len(chosen) < n_per_task:
                    chosen.append(strata[k][pools[k].pop()])
                    progressed = True
            if not progressed:
                break
        picks[t] = chosen
    judged = _judge_codes(picks)
    for t in TASKS:
        agree, n, recs = 0, 0, []
        for r in picks[t]:
            j = judged.get(r["sample_id"], {})
            adj = j.get("adjudicated")
            if adj is None:
                continue
            n += 1
            agree += adj == r["label"]
            recs.append({"sample_id": r["sample_id"], "label": r["label"], **j})
        out["tasks"][t] = {"n": n, "agree": agree, "pass": bool(n >= 25 and agree >= math.ceil(0.9 * n)),
                           "items": recs}
    tc = read_json(RESULTS_DIR / "tests_cpu.json")
    out["references_correct"] = f"{tc['label_correct']}/{tc['n_references']}"
    write_json(RESULTS_DIR / "regate.json", out)
    logger.info(f"re-gate: { {t: (v['agree'], v['n'], v['pass']) for t, v in out['tasks'].items()} }")
    return out


def _judge_codes(picks: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    import bench.common.judge as BJ
    import labeller.judge as J

    J.CACHE = DATA_DIR / "judge_cache_paths.jsonl"
    J.COST_FILE = RESULTS_DIR / "openrouter_cost_paths.json"
    BJ.JUDGES.update({"jA": "google/gemini-2.5-flash", "jB": "openai/gpt-4.1-mini", "jC": "deepseek/deepseek-chat-v3.1"})
    BJ.PERSONAL_CAP = 0.6
    res: dict[str, dict[str, Any]] = {}
    bj = BJ.Judge(ROOT)
    for jkey, model in (("jA", "google/gemini-2.5-flash"), ("jB", "openai/gpt-4.1-mini")):
        bench_items = [(t, r) for t, rs in picks.items() if t not in EXP8_TASK for r in rs]
        recs = bj.label_many([(jkey, t, r["code"]) for t, r in bench_items])
        for (t, r), rec in zip(bench_items, recs):
            res.setdefault(r["sample_id"], {})[jkey] = (rec or {}).get("label")
        path_items = [(t, r) for t, rs in picks.items() if t in EXP8_TASK for r in rs]
        if path_items:
            pr, _ = J.judge_many([{"task": EXP8_TASK[t], "code": r["code"]} for t, r in path_items], model,
                                 f"regate_{jkey}", 0.3)
            for (t, r), rec in zip(path_items, pr):
                res.setdefault(r["sample_id"], {})[jkey] = (rec or {}).get("label")
    # tie-break on disagreement
    dis = [(t, r) for t, rs in picks.items() for r in rs
           if res.get(r["sample_id"], {}).get("jA") != res.get(r["sample_id"], {}).get("jB")]
    if dis:
        bi = [(t, r) for t, r in dis if t not in EXP8_TASK]
        recs = bj.label_many([("jC", t, r["code"]) for t, r in bi]) if bi else []
        for (t, r), rec in zip(bi, recs):
            res[r["sample_id"]]["jC"] = (rec or {}).get("label")
        pi = [(t, r) for t, r in dis if t in EXP8_TASK]
        if pi:
            pr, _ = J.judge_many([{"task": EXP8_TASK[t], "code": r["code"]} for t, r in pi],
                                 "deepseek/deepseek-chat-v3.1", "regate_jC", 0.2)
            for (t, r), rec in zip(pi, pr):
                res[r["sample_id"]]["jC"] = (rec or {}).get("label")
    for sid, d in res.items():
        a, b = d.get("jA"), d.get("jB")
        d["adjudicated"] = a if (a is not None and a == b) else d.get("jC") or a or b
    return res


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage")
    args = ap.parse_args()
    setup_logging(f"behaviour_{args.stage}")
    {"defaults": stage_defaults, "report": stage_report, "regate": stage_regate}[args.stage]()


if __name__ == "__main__":
    main()
