#!/usr/bin/env python3
"""Label audits (OpenRouter; exp28's blind two-family judge client with a tie-break, cached, capped).

pt   (S3): per task 15 programs from the set entering q_base (correct programs if >= 20 correct, else valid attempts):
           every non-default program up to 10 (r_u's support stratum first: r_u-labelled, then the rest) + seeded random
           fill; judges A google/gemini-2.5-flash, B openai/gpt-4.1-mini, C deepseek/deepseek-chat-v3.1 on A/B
           disagreement; adjudicated = majority. Agreement of the labeller with the adjudication: overall
           (stratum-weighted to the population), on the r_u stratum, per task; kappa A-B; correct vs failing.
           Gate: overall >= 0.8 AND r_u stratum >= 0.8. FAIL -> one revision (every runtime 'unknown' and every
           runtime-AST disagreement of the affected tasks' q_base rows re-judged by the A/B/C adjudication, labels
           replaced) and a re-audit on a FRESH 15/task sample of the affected tasks; still < 0.8 -> AUDIT_FAIL.
it style re-gate (S4): 30 it programs (T 1.3 twin + forced), same judges; target >= 0.9.
novelty  (S10): every CORRECT 'other' program of the it model's iteration-6 rows (twin, forced, push), pt few-shot
           separately; exp28's novelty classifier + nearest known solutions.
Usage: python src/audit6.py pt | it_regate | novelty
"""

from __future__ import annotations

import asyncio
import collections
import json
import random
import sys
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (ALL_TASKS, AUDIT_GATE, AUDIT_PER_TASK, DATA_DIR, E28_DATA, OPENROUTER_CAP6_USD, RESULTS_DIR,
                 read_json, read_jsonl, setup_logging, write_json, write_jsonl)
import analysis_L as AL
import prompts6 as P6
from regate import Client, adjudicate, kappa, total_spend

REVISED = DATA_DIR / "labels_pt_revised.jsonl"


def all_labels() -> dict[str, dict[str, Any]]:
    labs = {r["row_id"]: r for r in read_jsonl(E28_DATA / "labels.jsonl")}
    labs.update({r["row_id"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl")})
    for r in read_jsonl(REVISED):      # revision-round labels (pt rows of AUDIT tasks only)
        if r["row_id"] in labs:
            labs[r["row_id"]] = {**labs[r["row_id"]], **r}
    return labs


def twin300(labs: dict[str, dict[str, Any]], t: str) -> list[dict[str, Any]]:
    return [r for r in labs.values() if r["task"] == t and ((r.get("stage") == "twin" and r.get("arm") == "twin")
                                                            or r.get("stage") == "twin6")]


def pt_rows(labs: dict[str, dict[str, Any]], t: str) -> list[dict[str, Any]]:
    return [r for r in labs.values() if r["task"] == t and r.get("stage") in ("ptchat", "ptplain", "ptfs6")]


def qbase_set(labs: dict[str, dict[str, Any]], t: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cat = P6.catalogue(t)
    D = AL.default_rule(twin300(labs, t), cat)["D"]
    pr = pt_rows(labs, t)
    bf = AL.base_forecast(pr, D, cat)
    if bf["LOW_CORRECT"]:
        s = [r for r in pr if AL.is_valid_attempt(r) and r.get("code")]
    else:
        s = [r for r in pr if AL.is_correct(r) and r.get("code")]
    return s, {"D": D, **{k: bf[k] for k in ("r_u", "LOW_CORRECT", "n_correct", "n_valid")}}


def sample_pt(labs: dict[str, dict[str, Any]], t: str, seed: int, exclude: set[str]) -> list[dict[str, Any]]:
    s, info = qbase_set(labs, t)
    s = sorted([r for r in s if r["row_id"] not in exclude], key=lambda r: r["row_id"])
    rng = random.Random(seed)
    D, r_u = info["D"], info["r_u"]
    ru = [r for r in s if r_u and r["label"] == r_u]
    nd = [r for r in s if r["label"] != D and r not in ru]
    rng.shuffle(ru)
    rng.shuffle(nd)
    strat = (ru + nd)[:10]
    rest = [r for r in s if r not in strat]
    rng.shuffle(rest)
    pick = strat + rest[:AUDIT_PER_TASK - len(strat)]
    out = []
    for r in pick:
        out.append({"row_id": r["row_id"], "task": t, "label": r["label"], "code": r["code"], "stage": r["stage"],
                    "passed": bool(r.get("passed")), "runtime_label": r.get("runtime_label"),
                    "ast_label": r.get("ast_label"), "labeller_source": r.get("labeller_source"),
                    "stratum": "r_u" if (r_u and r["label"] == r_u) else ("nondefault" if r["label"] != D else "fill"),
                    "pop_n": len(s), "pop_nondefault": sum(1 for x in s if x["label"] != D),
                    "pop_ru": sum(1 for x in s if r_u and x["label"] == r_u)})
    return out


def summarise(adj: list[dict[str, Any]], tasks: list[str]) -> dict[str, Any]:
    per = {}
    weighted_num, weighted_den = 0.0, 0.0
    ru_ok, ru_n = 0, 0
    for t in tasks:
        ss = [a for a in adj if a["task"] == t and a.get("adjudicated") not in (None, "UNRESOLVED")]
        if not ss:
            per[t] = {"n": 0}
            continue
        strata = collections.defaultdict(list)
        for a in ss:
            strata[a["stratum"]].append(a["adjudicated"] == a["label"])
        pop = {"r_u": ss[0]["pop_ru"], "nondefault": ss[0]["pop_nondefault"] - ss[0]["pop_ru"],
               "fill": ss[0]["pop_n"] - ss[0]["pop_nondefault"]}
        w_acc = sum(pop[k] * (sum(v) / len(v)) for k, v in strata.items() if v) / max(
            sum(pop[k] for k, v in strata.items() if v), 1)
        ab = [a for a in ss if a.get("judge_A") and a.get("judge_B")]
        per[t] = {"n": len(ss), "agree_raw": sum(a["adjudicated"] == a["label"] for a in ss) / len(ss),
                  "agree_stratum_weighted": w_acc,
                  "agree_r_u_stratum": (sum(strata["r_u"]) / len(strata["r_u"])) if strata["r_u"] else None,
                  "n_r_u_stratum": len(strata["r_u"]),
                  "kappa_A_B": kappa([a["judge_A"] for a in ab], [a["judge_B"] for a in ab]) if ab else None,
                  "agree_correct": (lambda c: sum(a["adjudicated"] == a["label"] for a in c) / len(c) if c else None)(
                      [a for a in ss if a["passed"]]),
                  "agree_failing": (lambda c: sum(a["adjudicated"] == a["label"] for a in c) / len(c) if c else None)(
                      [a for a in ss if not a["passed"]]),
                  "population": pop}
        weighted_num += w_acc * ss[0]["pop_n"]
        weighted_den += ss[0]["pop_n"]
        ru_ok += sum(strata["r_u"])
        ru_n += len(strata["r_u"])
    allr = [a for a in adj if a.get("adjudicated") not in (None, "UNRESOLVED")]
    ab = [a for a in allr if a.get("judge_A") and a.get("judge_B")]
    return {"per_task": per, "n": len(adj), "n_resolved": len(allr),
            "overall_raw": (sum(a["adjudicated"] == a["label"] for a in allr) / len(allr)) if allr else None,
            "overall_stratum_weighted": weighted_num / weighted_den if weighted_den else None,
            "r_u_stratum": ru_ok / ru_n if ru_n else None, "n_r_u_stratum": ru_n,
            "kappa_A_B": kappa([a["judge_A"] for a in ab], [a["judge_B"] for a in ab]) if ab else None,
            "task_pass": {t: bool(v.get("n")) and v["agree_stratum_weighted"] >= AUDIT_GATE
                          and (v["agree_r_u_stratum"] is None or v["agree_r_u_stratum"] >= AUDIT_GATE)
                          for t, v in per.items()}}


def revise(cl: Client, labs: dict[str, dict[str, Any]], tasks: list[str]) -> dict[str, Any]:
    """Revision round: every q_base-set row of the affected tasks whose runtime label is 'unknown' or disagrees with
    its AST label (or that was judge-labelled) is re-judged by the A/B/C adjudication; resolved labels replace it."""
    items = []
    for t in tasks:
        s, _ = qbase_set(labs, t)
        for r in s:
            rl, al = r.get("runtime_label"), r.get("ast_label")
            if rl in ("unknown", None) or (al not in ("unknown", None) and al != rl) or r.get("labeller_source") == "judge":
                items.append({"row_id": r["row_id"], "task": t, "label": r["label"], "code": r["code"]})
    adj = asyncio.run(adjudicate(items, "pt_revision", cl)) if items else []
    out = []
    for a in adj:
        if a.get("adjudicated") not in (None, "UNRESOLVED"):
            out.append({"row_id": a["row_id"], "label": a["adjudicated"], "labeller_source": "revision_adjudicated",
                        "label_before_revision": a["label"]})
    write_jsonl(REVISED, read_jsonl(REVISED) + out)
    return {"n_rejudged": len(items), "n_relabelled": sum(1 for o in out if o["label"] != o["label_before_revision"])}


def pt_audit() -> dict[str, Any]:
    cl = Client(OPENROUTER_CAP6_USD)
    labs = all_labels()
    items = [it for t in ALL_TASKS for it in sample_pt(labs, t, seed=60, exclude=set())]
    adj = asyncio.run(adjudicate(items, "pt_label_audit6", cl))
    s1 = summarise(adj, list(ALL_TASKS))
    res: dict[str, Any] = {"round1": s1, "rows_round1": adj, "spend_after_round1": total_spend()}
    failing = [t for t, ok in s1["task_pass"].items() if not ok]
    gate1 = (s1["overall_stratum_weighted"] or 0) >= AUDIT_GATE and (s1["r_u_stratum"] or 0) >= AUDIT_GATE
    res["gate_round1"] = gate1
    res["affected_tasks"] = failing
    final_fail = []
    if failing and not cl.stop:
        res["revision"] = revise(cl, labs, failing)
        labs = all_labels()
        seen = {a["row_id"] for a in adj}
        items2 = [it for t in failing for it in sample_pt(labs, t, seed=61, exclude=seen)]
        adj2 = asyncio.run(adjudicate(items2, "pt_label_audit6_round2", cl)) if items2 else []
        s2 = summarise(adj2, failing)
        res["round2"] = s2
        res["rows_round2"] = adj2
        final_fail = [t for t, ok in s2["task_pass"].items() if not ok]
    res["AUDIT_FAIL"] = sorted(final_fail)
    res["label_limited"] = len(final_fail) >= 5
    res["stopped"] = cl.reason
    res["spend_total_artifact_usd"] = total_spend()
    res["judges"] = {"A": "google/gemini-2.5-flash", "B": "openai/gpt-4.1-mini", "C": "deepseek/deepseek-chat-v3.1"}
    write_json(RESULTS_DIR / "pt_label_audit6.json", res)
    logger.info(f"pt audit: round1 overall {s1['overall_stratum_weighted']}, r_u stratum {s1['r_u_stratum']}, "
                f"affected {failing}, AUDIT_FAIL {final_fail}; spend {total_spend():.3f}")
    return res


def it_regate() -> dict[str, Any]:
    cl = Client(OPENROUTER_CAP6_USD)
    labs = {r["row_id"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl")}
    rng = random.Random(62)
    hot = sorted([r for r in labs.values() if r.get("stage") == "twin6" and r.get("arm") == "twin_T13"
                  and r.get("valid") and r.get("code")], key=lambda r: r["row_id"])
    forced = sorted([r for r in labs.values() if r.get("stage") == "forced6" and r.get("valid") and r.get("code")],
                    key=lambda r: r["row_id"])
    # off-default programs first (the labels that matter for q_tail), then random fill
    pick = rng.sample(hot, min(15, len(hot))) + rng.sample(forced, min(15, len(forced)))
    items = [{"row_id": r["row_id"], "task": r["task"], "label": r["label"], "code": r["code"], "stage": r["stage"],
              "passed": bool(r.get("passed"))} for r in pick]
    adj = asyncio.run(adjudicate(items, "it_regate6", cl))
    ok = [a for a in adj if a.get("adjudicated") not in (None, "UNRESOLVED")]
    res = {"n": len(adj), "n_resolved": len(ok),
           "agreement": (sum(a["adjudicated"] == a["label"] for a in ok) / len(ok)) if ok else None,
           "by_stage": {s: (lambda c: sum(a["adjudicated"] == a["label"] for a in c) / len(c) if c else None)(
               [a for a in ok if a["stage"] == s]) for s in ("twin6", "forced6")},
           "rows": adj, "target": 0.9}
    res["pass"] = res["agreement"] is not None and res["agreement"] >= 0.9
    write_json(RESULTS_DIR / "it_regate6.json", res)
    logger.info(f"it style re-gate: {res['agreement']} on {res['n_resolved']}")
    return res


def ast_4grams(code: str) -> set[tuple[str, ...]]:
    """Identifier-normalised AST 4-grams: the pre-order sequence of node-type names (names, constants and attribute
    strings dropped), as a set of 4-grams."""
    import ast as _ast

    try:
        tree = _ast.parse(code)
    except (SyntaxError, ValueError):
        return set()
    seq = [type(n).__name__ for n in _ast.walk(tree)]
    return {tuple(seq[i:i + 4]) for i in range(max(0, len(seq) - 3))}


def nearest3(t: str, code: str, corpus: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    a = ast_4grams(code)
    sims = []
    for c in corpus.get(t, []):
        b = ast_4grams(c["code"])
        if a and b:
            sims.append((len(a & b) / len(a | b), c))
    sims.sort(key=lambda x: -x[0])
    return [{"jaccard_ast4": round(j, 4), "source": c["source"], "hint": c.get("hint"), "code_head": c["code"][:300]}
            for j, c in sims[:3]]


def novelty() -> dict[str, Any]:
    import novelty_audit as NA

    cl = Client(OPENROUTER_CAP6_USD)
    labs = [r for r in read_jsonl(DATA_DIR / "labels.jsonl")
            if r.get("stage") in ("twin6", "forced6", "push6", "confirm6", "ptfs6")]
    it_rows = [r for r in labs if r.get("stage") != "ptfs6"]
    pt_r = [r for r in labs if r.get("stage") == "ptfs6"]
    res_it = NA.novelty_audit(cl, it_rows)
    res_pt = NA.novelty_audit(cl, pt_r)
    corpus = NA.known_corpus()
    code_of = {r["row_id"]: r.get("code") for r in labs}
    for res_ in (res_it, res_pt):
        for o in res_.get("rows", []):
            c = code_of.get(o["row_id"])
            o["nearest3_ast4_jaccard"] = nearest3(o["task"], c, corpus) if c else []
    res = {"it_model_iteration6": res_it, "pt_fewshot": res_pt, "spend_total_artifact_usd": total_spend()}
    write_json(RESULTS_DIR / "novelty_audit6.json", res)
    logger.info(f"novelty: it {res_it['n_correct_other']} correct other, novel {res_it['novel_count']}; "
                f"pt {res_pt['n_correct_other']} / novel {res_pt['novel_count']}")
    return res


@logger.catch(reraise=True)
def main() -> None:
    cmd = sys.argv[1]
    setup_logging(f"audit6_{cmd}")
    if cmd == "pt":
        pt_audit()
    elif cmd == "it_regate":
        it_regate()
    elif cmd == "novelty":
        novelty()


if __name__ == "__main__":
    main()
