#!/usr/bin/env python3
"""Label Phase A programs, run the labeller gate (gold set), and summarise Phase A.

Outputs
  data/samples_phaseA.jsonl         shared row schema + diagnostics
  labeller/gold_set.json            gold items with runtime / AST / two judges / resolver / adjudicated labels
  results/labeller_gate.json        gate statistics per task (+ judge-primary decision)
  results/phaseA_summary.json       baseline distributions, strata, manipulation checks, association objects
"""
from __future__ import annotations

import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tasks"))
sys.path.insert(0, str(ROOT / "labeller"))
from common import (CATALOGUE, TASKS, add_deviation, hill1, read_jsonl, setup_logger, wilson,  # noqa: E402
                    write_jsonl)
from label import (GOLD_JUDGES, GOLD_RESOLVER, combine, cpu_label_one, cpu_stage, finalize_row,  # noqa: E402
                   judge_many, spent_usd)
from references import REFS  # noqa: E402

logger = setup_logger("label_a")


def cohen_kappa(a: list[str], b: list[str]) -> float:
    n = len(a)
    if n == 0:
        return float("nan")
    cats = sorted(set(a) | set(b))
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[c] * cb[c] for c in cats) / (n * n)
    return 1.0 if pe >= 1.0 else (po - pe) / (1 - pe)


def run_gate(rows: list[dict]) -> tuple[dict, set[str]]:
    rng = random.Random(11)
    gate: dict = {}
    judge_primary: set[str] = set()
    gold_all = []
    for task in TASKS:
        items = []
        for lab, var, src in REFS[task]:
            r = cpu_label_one(task, src)
            items.append({"task": task, "kind": "reference", "name": var, "true": lab, "code": src,
                          "rt": r["rt_label"], "ast": r["ast_label"], "rt_conf": r["rt_conf"], "ast_conf": r["ast_conf"]})
        base = [r for r in rows if r["task"] == task and r["condition"] == "baseline" and r.get("code")]
        forced = [r for r in rows if r["task"] == task and r["condition"].startswith("forced:") and r.get("code")]
        for kind, pool in (("baseline", base), ("forced", forced)):
            for r in rng.sample(pool, min(10, len(pool))):
                items.append({"task": task, "kind": kind, "name": f"{r['condition']}|p{r['paraphrase_id']}|s{r['sample_id']}",
                              "true": None, "code": r["code"], "rt": r["rt_label"], "ast": r["ast_label"],
                              "rt_conf": r["rt_conf"], "ast_conf": r["ast_conf"]})
        # two independent judges, a third resolves disagreements
        js = {}
        for jm in GOLD_JUDGES:
            res = judge_many([(task, it["code"]) for it in items], jm, logger)
            js[jm] = [x.get("label") for x in res]
        disagree = [i for i in range(len(items)) if js[GOLD_JUDGES[0]][i] != js[GOLD_JUDGES[1]][i]]
        res3 = judge_many([(task, items[i]["code"]) for i in disagree], GOLD_RESOLVER, logger)
        r3 = {i: x.get("label") for i, x in zip(disagree, res3)}
        for i, it in enumerate(items):
            it["judge_a"], it["judge_b"] = js[GOLD_JUDGES[0]][i], js[GOLD_JUDGES[1]][i]
            it["resolver"] = r3.get(i)
            adj = it["judge_a"] if i not in r3 else (r3[i] or it["judge_a"])
            it["adjudicated"] = it["true"] if it["true"] is not None else adj
        refs = [it for it in items if it["kind"] == "reference"]
        ref_ok = sum(it["rt"] == it["true"] and it["ast"] == it["true"] for it in refs) / len(refs)
        rt_l = [str(it["rt"]) for it in items]
        ast_l = [str(it["ast"]) for it in items]
        kappa = cohen_kappa(rt_l, ast_l)
        rt_vs_adj = sum(it["rt"] == it["adjudicated"] for it in items) / len(items)
        judge_ref_acc = sum(it["judge_a"] == it["true"] for it in refs) / len(refs)
        combo_cov = sum(it["rt_conf"] and it["ast_conf"] and it["rt"] == it["ast"] for it in items) / len(items)
        passed = ref_ok == 1.0 and kappa >= 0.8 and rt_vs_adj >= 0.9
        gate[task] = {"n_gold": len(items), "ref_runtime_ast_agreement": ref_ok, "kappa_runtime_ast": kappa,
                      "runtime_vs_adjudicated": rt_vs_adj, "primary_judge_acc_on_references": judge_ref_acc,
                      "judge_pair_agreement": 1 - len(disagree) / len(items), "runtime_ast_confident_coverage": combo_cov,
                      "pass": passed}
        if not passed:
            judge_primary.add(task)
            add_deviation(f"Labeller gate failed for {task} ({gate[task]}); the blind judge is the primary labeller "
                          f"for {task} (no revision round fitted in the time budget).")
        gold_all.extend(items)
        logger.info(f"gate {task}: {gate[task]}")
    (ROOT / "labeller" / "gold_set.json").write_text(json.dumps(gold_all, indent=1))
    return gate, judge_primary


def borda_objects(el_rows: list[dict], task: str, x: str) -> dict:
    others = [m for m in CATALOGUE[task] if m != x]
    K = len(CATALOGUE[task])
    pts = Counter({m: 1.0 for m in others})  # 1 pseudo-point
    first = Counter({m: 1.0 for m in others})  # 1 pseudo-count
    rankings = [r["ranking"] for r in el_rows if r["task"] == task and r["condition"] == f"elicit:{x}" and r.get("ranking")]
    for rk in rankings:
        for pos, m in enumerate(rk):
            pts[m] += (K - 2 - pos)
        first[rk[0]] += 1
    tot = sum(pts.values())
    A = {m: pts[m] / tot for m in others}
    ftot = sum(first.values())
    F = {m: first[m] / ftot for m in others}
    winner = max(others, key=lambda m: (A[m], -others.index(m)))
    clarity = sum(rk[0] == winner for rk in rankings) / len(rankings) if rankings else float("nan")
    # Kendall's W over the rankings (rank 1 = most standard)
    W = float("nan")
    if len(rankings) >= 2:
        m_, n_ = len(rankings), len(others)
        R = Counter()
        for rk in rankings:
            for pos, mm in enumerate(rk):
                R[mm] += pos + 1
        Rbar = m_ * (n_ + 1) / 2
        S = sum((R[mm] - Rbar) ** 2 for mm in others)
        W = 12 * S / (m_ ** 2 * (n_ ** 3 - n_))
    fr = Counter(rk[0] for rk in rankings)
    H = -sum((c / len(rankings)) * math.log(c / len(rankings)) for c in fr.values()) if rankings else float("nan")
    Hn = H / math.log(len(others)) if rankings and len(others) > 1 else float("nan")
    plurality_F = max(others, key=lambda m: (F[m], -others.index(m)))
    return {"X": x, "n_rankings": len(rankings), "borda_A": A, "first_rank_F": F, "borda_winner": winner,
            "clarity": clarity, "kendall_W": W, "first_rank_entropy_norm": Hn,
            "ambiguity_flag": plurality_F != winner}


def summarise(rows: list[dict], el_rows: list[dict]) -> dict:
    out: dict = {}
    for task in TASKS:
        cat = CATALOGUE[task]
        base = [r for r in rows if r["task"] == task and r["condition"] == "baseline"]
        counts = Counter(r["label"] for r in base)
        correct = Counter(r["label"] for r in base if r["passed"])
        n = len(base)
        npass = sum(r["passed"] for r in base)
        parse = [r for r in base if r["label"] not in ("no_code",)]
        pc = Counter(r["label"] for r in parse)
        modal = max(cat, key=lambda m: (pc.get(m, 0), -cat.index(m)))
        strata = {}
        for m in cat:
            share = pc.get(m, 0) / max(len(parse), 1)
            strata[m] = "modal" if m == modal else ("present_minor" if share >= 0.10 else "absent")
        manip = {}
        for m in cat:
            for kind in ("forced", "masked"):
                rr = [r for r in rows if r["task"] == task and r["condition"] == f"{kind}:{m}"]
                k = sum(r["label"] == m for r in rr)
                manip[f"{kind}:{m}"] = {"n": len(rr), "share_labelled_X": k / max(len(rr), 1),
                                        "wilson": wilson(k, len(rr)), "pass_rate": sum(r["passed"] for r in rr) / max(len(rr), 1),
                                        "label_counts": dict(Counter(r["label"] for r in rr))}
        out[task] = {
            "baseline_n": n, "baseline_label_counts": dict(counts), "baseline_correct_label_counts": dict(correct),
            "pass_rate": npass / max(n, 1), "pass_wilson": wilson(npass, n), "hill_cc": hill1(correct),
            "modal": modal, "modal_share_parseable": pc.get(modal, 0) / max(len(parse), 1),
            "modal_wilson": wilson(pc.get(modal, 0), len(parse)), "strata": strata,
            "label_wilson": {m: wilson(pc.get(m, 0), len(parse)) for m in list(cat) + ["other"]},
            "manipulation_check": manip,
            "forced_overall_share": sum(v["share_labelled_X"] * v["n"] for k, v in manip.items() if k.startswith("forced"))
            / max(sum(v["n"] for k, v in manip.items() if k.startswith("forced")), 1),
            "labeller_sources": dict(Counter(r["labeller_source"] for r in rows if r["task"] == task)),
            "truncated": sum(r.get("finish_reason") == "length" for r in rows if r["task"] == task),
            "association": {x: borda_objects(el_rows, task, x) for x in cat},
        }
        if task == "t1":
            out[task]["bfs_fraction_T1_T1.0"] = counts.get("bfs", 0) / max(n, 1)
    return out


@logger.catch(reraise=True)
def main() -> None:
    rows = read_jsonl(ROOT / "data" / "raw_phaseA.jsonl")
    el_rows = read_jsonl(ROOT / "data" / "elicit_phaseA.jsonl")
    logger.info(f"labelling {len(rows)} Phase-A programs")
    cpu_stage(rows, workers=6, logger=logger)
    gate, judge_primary = run_gate(rows)
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "labeller_gate.json").write_text(json.dumps({"gate": gate, "judge_primary_tasks": sorted(judge_primary),
                                                                     "spend_usd": spent_usd()}, indent=1))
    combine(rows, logger, judge_primary_tasks=judge_primary)
    for r in rows:
        finalize_row(r, [])
    write_jsonl(ROOT / "data" / "samples_phaseA.jsonl", rows)
    summ = summarise(rows, el_rows)
    (ROOT / "results" / "phaseA_summary.json").write_text(json.dumps(summ, indent=1, default=str))
    for t in TASKS:
        s = summ[t]
        logger.info(f"{t}: modal={s['modal']} ({s['modal_share_parseable']:.2f}) pass={s['pass_rate']:.2f} "
                    f"hill={s['hill_cc']:.2f} counts={s['baseline_label_counts']} strata={s['strata']} "
                    f"forced_overall={s['forced_overall_share']:.2f}")
    logger.info(f"spend so far ${spent_usd():.3f}")


if __name__ == "__main__":
    main()
