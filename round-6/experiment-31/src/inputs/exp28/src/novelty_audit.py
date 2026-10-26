#!/usr/bin/env python3
"""NOVELTY AUDIT and pt LABEL AUDIT (OpenRouter, capped; port of exp23 judge_audit.py).

(a) Novelty audit: every CORRECT 'other' program from every arm (pt included) is classified by two blind judges from
    different families (openai/gpt-4.1-mini, google/gemini-2.5-flash) as NOVEL_ALGORITHM / CATALOGUE_VARIANT (named)
    / LABELLER_MISS / DEGENERATE; deepseek/deepseek-chat-v3.1 resolves disagreements; the nearest known solution
    (Zhang-Shasha on normalised ASTs) is found among the exp18 index (472) and the declared dependency's program corpus.
    'No correct novel algorithm' is claimed only at a count of 0, with the rule-of-three upper bound 3/n.
(b) pt label audit: up to 15 pt programs per unit (stratified by label) read by two judges; agreement with the
    combined label per unit (iteration 1 base-model kappa was 0.20-0.50).
The first HTTP 403 'AI Inventor per-run OpenRouter budget' stops every remaining call.
"""

from __future__ import annotations

import asyncio
import collections
import json
import random
import re
import sys
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (ALL_TASKS, DATA_DIR, DEP1, E18, OPENROUTER_CAP_USD, PATH_TASKS, RESULTS_DIR, read_jsonl,
                 setup_logging, write_json)
from regate import Client, adjudicate, kappa, total_spend

CLASSES = ("NOVEL_ALGORITHM", "CATALOGUE_VARIANT", "LABELLER_MISS", "DEGENERATE")
JA, JB, JC = "openai/gpt-4.1-mini", "google/gemini-2.5-flash", "deepseek/deepseek-chat-v3.1"


def task_card(t: str) -> tuple[str, str]:
    import prompts as PG

    mech = PG.mechanism_texts(t)
    return PG.description(t), "\n".join(f"- {m}: {d}" for m, d in mech.items())


def novelty_prompt(t: str, code: str) -> str:
    desc, cat = task_card(t)
    return (f"A program was written for this task:\n{desc}\n\nKnown algorithm families for this task:\n{cat}\n\n"
            "An automatic labeller could not match the program to any family above. Classify the program's MAIN "
            "mechanism into exactly one class:\n- NOVEL_ALGORITHM: a correct mechanism that is genuinely different "
            "from every listed family and is not a standard textbook algorithm for this task\n- CATALOGUE_VARIANT: a "
            "variant, combination or re-implementation of a listed family (name it) or of another standard textbook "
            "algorithm (name it)\n- LABELLER_MISS: plainly one of the listed families\n- DEGENERATE: no real algorithm "
            "(hard-coded cases, brute enumeration of outputs, or trivial library delegation)\n\nProgram:\n```python\n"
            + code[:5000] + "\n```\n\nAnswer with JSON only: {\"class\": \"<CLASS>\", \"family\": \"<name or none>\", "
            "\"rationale\": \"<one sentence>\"}")


def parse_class(txt: str | None) -> dict[str, Any]:
    if not txt:
        return {"class": None}
    m = re.search(r"\{.*\}", txt, re.S)
    if m:
        try:
            j = json.loads(m.group(0))
            c = str(j.get("class", "")).upper().strip()
            return {"class": c if c in CLASSES else None, "family": j.get("family"),
                    "rationale": str(j.get("rationale"))[:300]}
        except json.JSONDecodeError:
            pass
    for c in CLASSES:
        if c in txt:
            return {"class": c}
    return {"class": None}


def known_corpus() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for r in read_jsonl(E18 / "inputs" / "known_solutions.jsonl"):
        out[r["task"]].append({"source": "exp18:" + str(r.get("source")), "hint": r.get("mode_hint"), "code": r["code"]})
    tmap = {"T03": "T03", "T04": "T04", "T05": "T05", "T06": "T06", "T10": "T10", "R1": "R1", "R2": "R2", "R3": "R3",
            "R6": "R6", "T08": "T08", "T11": "T11", "T13": "T13", "T14": "T14", "T01": "T1", "T02": "T2"}
    for r in read_jsonl(DEP1 / "known_solution_corpus.jsonl"):
        bt = str(r.get("bench_task") or "")
        t = tmap.get(bt.split("_")[0]) if bt else None
        if t:
            out[t].append({"source": "art_j3Rm:" + r["source"], "hint": r.get("named"), "code": r["code"]})
    return dict(out)


def nearest_known(t: str, code: str, corpus: dict[str, list[dict[str, Any]]], k: int = 40) -> dict[str, Any] | None:
    from prox import zs_pair

    best = None
    for c in corpus.get(t, [])[:k]:
        d = zs_pair(code, c["code"])
        if d is not None and (best is None or d < best["distance"]):
            best = {"distance": d, "source": c["source"], "hint": c.get("hint"), "code_head": c["code"][:300]}
    return best


async def _novelty(items: list[dict[str, Any]], cl: Client) -> list[dict[str, Any]]:
    sem = asyncio.Semaphore(10)
    ra = await asyncio.gather(*[cl.ask(sem, JA, novelty_prompt(it["task"], it["code"]), "novelty_A", 250) for it in items])
    rb = await asyncio.gather(*[cl.ask(sem, JB, novelty_prompt(it["task"], it["code"]), "novelty_B", 250) for it in items])
    out, need = [], []
    for it, a, b in zip(items, ra, rb):
        A_, B_ = parse_class(a), parse_class(b)
        rec = {**{k: it[k] for k in ("row_id", "task", "arm", "stage", "label")}, "judge_A": A_, "judge_B": B_}
        if A_["class"] and A_["class"] == B_["class"]:
            rec["final"] = A_["class"]
        else:
            need.append(len(out))
        out.append(rec)
    if need and not cl.stop:
        rc = await asyncio.gather(*[cl.ask(sem, JC, novelty_prompt(items[i]["task"], items[i]["code"]), "novelty_C", 250)
                                    for i in need])
        for i, c in zip(need, rc):
            C_ = parse_class(c)
            out[i]["judge_C"] = C_
            out[i]["final"] = C_["class"] or "UNRESOLVED"
    for o in out:
        o.setdefault("final", "UNRESOLVED")
    return out


def novelty_audit(cl: Client, labs: list[dict[str, Any]]) -> dict[str, Any]:
    items = [r for r in labs if r.get("passed") and r["label"] == "other" and r.get("code")]
    if not items:
        return {"n_correct_other": 0, "rows": [], "by_arm": {}, "novel_count": 0, "rule_of_three_upper_95": None,
                "note": "no correct 'other' program in any arm"}
    res = asyncio.run(_novelty(items, cl))
    corpus = known_corpus()
    for o, r in zip(res, items):
        o["nearest_known"] = nearest_known(r["task"], r["code"], corpus)
        o["code_head"] = r["code"][:600]
    by_arm = collections.defaultdict(collections.Counter)
    for o in res:
        by_arm[f"{o['stage']}:{o['arm']}"][o["final"]] += 1
    n_novel = sum(1 for o in res if o["final"] == "NOVEL_ALGORITHM")
    return {"n_correct_other": len(res), "rows": res, "by_arm": {k: dict(v) for k, v in by_arm.items()},
            "novel_count": n_novel, "stopped": cl.reason,
            "rule_of_three_upper_95": (3 / len(res)) if n_novel == 0 else None,
            "judges": {"A": JA, "B": JB, "C": JC}}


def pt_label_audit(cl: Client, labs: list[dict[str, Any]], per_unit: int = 15) -> dict[str, Any]:
    rng = random.Random(7)
    items = []
    for t in ALL_TASKS:
        pt = [r for r in labs if r.get("stage") in ("ptchat", "ptplain") and r["task"] == t and r.get("valid")
              and r.get("code") and r["label"] not in ("disputed",)]
        by = collections.defaultdict(list)
        for r in sorted(pt, key=lambda r: r["row_id"]):
            by[r["label"]].append(r)
        pick: list[dict[str, Any]] = []
        while len(pick) < min(per_unit, len(pt)):
            for lab in sorted(by, key=lambda k: -len(by[k])):
                if by[lab] and len(pick) < per_unit:
                    pick.append(by[lab].pop(rng.randrange(len(by[lab]))))
        for r in pick:
            items.append({"row_id": r["row_id"], "task": t, "label": r["label"], "runtime_label": r.get("runtime_label"),
                          "ast_label": r.get("ast_label"), "code": r["code"], "stage": r["stage"]})
    adj = asyncio.run(adjudicate(items, "pt_label_audit", cl)) if items else []
    per = {}
    for t in ALL_TASKS:
        ss = [a for a in adj if a["task"] == t and a.get("judge_A") and a.get("judge_B")]
        if not ss:
            continue
        per[t] = {"n": len(ss), "agree_A": sum(1 for a in ss if a["judge_A"] == a["label"]) / len(ss),
                  "agree_B": sum(1 for a in ss if a["judge_B"] == a["label"]) / len(ss),
                  "agree_adjudicated": sum(1 for a in ss if a["adjudicated"] == a["label"]) / len(ss),
                  "kappa_label_vs_A": kappa([a["label"] for a in ss], [a["judge_A"] for a in ss]),
                  "kappa_A_vs_B": kappa([a["judge_A"] for a in ss], [a["judge_B"] for a in ss])}
    allr = [a for a in adj if a.get("adjudicated") not in (None, "UNRESOLVED")]
    return {"n": len(adj), "per_unit": per,
            "overall_agreement_adjudicated": (sum(1 for a in allr if a["adjudicated"] == a["label"]) / len(allr)) if allr else None,
            "rows": adj}


def main() -> None:
    setup_logging("novelty_audit")
    labs = read_jsonl(DATA_DIR / "labels.jsonl")
    cl = Client(OPENROUTER_CAP_USD)
    na = novelty_audit(cl, labs)
    write_json(RESULTS_DIR / "novelty_audit.json", na)
    logger.info(f"novelty audit: {na['n_correct_other']} correct 'other'; novel={na['novel_count']}; by arm {na['by_arm']}")
    if "--no-pt-audit" not in sys.argv:
        la = pt_label_audit(cl, labs)
        write_json(RESULTS_DIR / "pt_label_audit.json", la)
        logger.info(f"pt label audit: n={la['n']} agreement={la['overall_agreement_adjudicated']}")
    write_json(RESULTS_DIR / "costs.json", {"openrouter_usd_total_artifact": total_spend(), "cap_usd": OPENROUTER_CAP_USD})


if __name__ == "__main__":
    main()
