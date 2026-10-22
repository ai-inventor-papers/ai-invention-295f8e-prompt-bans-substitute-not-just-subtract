#!/usr/bin/env python3
"""STEP 10: label audit, runtime/AST disagreement statistics and the novelty audit (OpenRouter, capped).

(a) Gemma label audit: 60 random valid labelled programs (4 per task), judged blind by a judge that the labeller did
    not use (bench: j2 openai/gpt-4.1-mini on name-scrubbed code; T1/T2: google/gemini-2.5-flash with the suite
    judge prompt); agreement with the combined label per task.
(b) Disagreement rate per task (runtime vs AST -> judge or disputed) on Gemma programs (F7 flag at > 15%).
(c) Novelty audit of every CORRECT 'other' program from all arms: two blind judges from different families
    (openai/gpt-4.1-mini, google/gemini-2.5-flash) classify NOVEL_ALGORITHM / CATALOGUE_VARIANT (named) /
    LABELLER_MISS / DEGENERATE; deepseek/deepseek-chat-v3.1 resolves disagreements; the nearest known solution
    (Zhang-Shasha on normalised ASTs) from the exp18 index (472) and the declared dependency's program corpus.
The first HTTP 403 whose message starts 'AI Inventor per-run OpenRouter budget' stops every remaining call.
"""

from __future__ import annotations

import asyncio
import collections
import json
import os
import random
import re
import sys
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (ALL_TASKS, BUDGET_MSG, DATA_DIR, DEP1, E18, EXP8_TASK, LOG_DIR, OPENROUTER_CAP_USD, PATH_TASKS,
                 RESULTS_DIR, ROOT, bench_paths, read_json, read_jsonl, setup_logging, write_json)

bench_paths()
LEDGER = LOG_DIR / "openrouter_spend_audit.jsonl"
CLASSES = ("NOVEL_ALGORITHM", "CATALOGUE_VARIANT", "LABELLER_MISS", "DEGENERATE")


def total_spend() -> float:
    s = 0.0
    for p in (LOG_DIR / "openrouter_spend.jsonl", LEDGER):
        if p.exists():
            s += sum((json.loads(l).get("cost") or 0.0) for l in p.read_text().splitlines() if l.strip())
    cp = RESULTS_DIR / "openrouter_cost_paths.json"
    if cp.exists():
        s += float(read_json(cp).get("total_usd", 0.0))
    return s


class Client:
    def __init__(self, cap: float):
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"],
                                  timeout=90, max_retries=2)
        self.cap = cap
        self.stop = False
        self.reason = None

    async def ask(self, sem, model: str, prompt: str, purpose: str, max_tokens: int = 300) -> str | None:
        async with sem:
            if self.stop:
                return None
            if total_spend() >= self.cap:
                self.stop, self.reason = True, "artifact cap reached"
                return None
            try:
                r = await self.client.chat.completions.create(model=model, temperature=0, max_tokens=max_tokens,
                                                              messages=[{"role": "user", "content": prompt}])
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                if BUDGET_MSG in msg:
                    self.stop, self.reason = True, "budget_403"
                    logger.error("OpenRouter phase budget exhausted: stopping the audit batch")
                else:
                    logger.warning(f"{model} call failed: {msg[:200]}")
                return None
            if self.stop:
                return None
            cost = float(getattr(r.usage, "cost", 0.0) or 0.0) if r.usage else 0.0
            with LEDGER.open("a") as f:
                f.write(json.dumps({"purpose": purpose, "model": model, "cost": cost,
                                    "prompt_tokens": r.usage.prompt_tokens if r.usage else None}) + "\n")
            return r.choices[0].message.content or ""


# ------------------------------------------------------------------------------------------------ (a) label audit
def label_audit(per_task: int = 4, seed: int = 0) -> dict[str, Any]:
    import bench.common.judge as BJ
    import labeller.judge as J

    BJ.PERSONAL_CAP = OPENROUTER_CAP_USD
    J.CACHE = DATA_DIR / "judge_cache_paths_audit.jsonl"
    J.COST_FILE = RESULTS_DIR / "openrouter_cost_paths_audit.json"
    labs = [r for r in read_jsonl(DATA_DIR / "labels.jsonl") if r.get("valid") and r.get("code")
            and r["label"] not in ("disputed",)]
    rng = random.Random(seed)
    picks = []
    for t in ALL_TASKS:
        rr = sorted((r for r in labs if r["task"] == t), key=lambda r: r["row_id"])
        picks += rng.sample(rr, min(per_task, len(rr)))
    bench = [r for r in picks if r["task"] not in PATH_TASKS]
    path = [r for r in picks if r["task"] in PATH_TASKS]
    out_rows = []
    if bench and total_spend() < OPENROUTER_CAP_USD:
        recs = BJ.Judge(ROOT).label_many([("j2", r["task"], r["code"]) for r in bench])
        for r, rec in zip(bench, recs):
            out_rows.append({"row_id": r["row_id"], "task": r["task"], "combined": r["label"], "audit": rec.get("label"),
                             "judge": BJ.JUDGES["j2"]})
    if path and total_spend() < OPENROUTER_CAP_USD:
        res, _ = J.judge_many([{"task": EXP8_TASK[r["task"]], "code": r["code"]} for r in path],
                              "google/gemini-2.5-flash", "iter4_label_audit_paths", 0.10)
        for r, rec in zip(path, res):
            out_rows.append({"row_id": r["row_id"], "task": r["task"], "combined": r["label"],
                             "audit": (rec or {}).get("label"), "judge": "google/gemini-2.5-flash"})
    per = collections.defaultdict(lambda: [0, 0])
    for o in out_rows:
        if o["audit"] is None:
            continue
        per[o["task"]][1] += 1
        per[o["task"]][0] += int(o["audit"] == o["combined"])
    agree = {t: v[0] / v[1] for t, v in per.items() if v[1]}
    n = sum(v[1] for v in per.values())
    return {"n": n, "overall_agreement": sum(v[0] for v in per.values()) / max(n, 1), "per_task": agree,
            "flagged_tasks_below_0.85": sorted(t for t, a in agree.items() if a < 0.85), "rows": out_rows}


def disagreement_stats() -> dict[str, Any]:
    labs = [r for r in read_jsonl(DATA_DIR / "labels.jsonl") if r.get("valid")]
    out = {}
    for t in ALL_TASKS:
        rr = [r for r in labs if r["task"] == t]
        d = sum(1 for r in rr if r["labeller_source"] in ("judge", "judge_unavailable") or r["label"] == "disputed")
        out[t] = {"n_valid": len(rr), "n_disagreement": d, "rate": d / max(len(rr), 1),
                  "n_disputed": sum(1 for r in rr if r["label"] == "disputed"), "flag_gt_0.15": d / max(len(rr), 1) > 0.15}
    return out


# ------------------------------------------------------------------------------------------------ (c) novelty audit
def task_card(t: str) -> tuple[str, str]:
    if t in PATH_TASKS:
        import common as SC

        et = EXP8_TASK[t]
        cat = "\n".join(f"- {m}: {d}" for m, d in SC.MODE_DEFINITIONS[et].items())
        return SC.DESCRIPTION[et], cat
    from bench.common.catalogue import TASKS

    c = TASKS[t]
    return c["description"], "\n".join(f"- {m} ({d[0]}): {d[1]}" for m, d in c["modes"].items())


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
            return {"class": c if c in CLASSES else None, "family": j.get("family"), "rationale": str(j.get("rationale"))[:300]}
        except json.JSONDecodeError:
            pass
    for c in CLASSES:
        if c in (txt or ""):
            return {"class": c}
    return {"class": None}


def nearest_known(t: str, code: str, corpus: dict[str, list[dict[str, Any]]], k: int = 40) -> dict[str, Any] | None:
    from prox import zs_pair

    cands = corpus.get(t, [])[:k]
    best = None
    for c in cands:
        d = zs_pair(code, c["code"])
        if d is not None and (best is None or d < best["distance"]):
            best = {"distance": d, "source": c["source"], "hint": c.get("hint"), "code_head": c["code"][:300]}
    return best


def known_corpus() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for r in read_jsonl(E18 / "inputs" / "known_solutions.jsonl"):
        out[r["task"]].append({"source": "exp18:" + r["source"], "hint": r.get("mode_hint"), "code": r["code"]})
    tmap = {"T03_kth_smallest": "T03", "T04_substring_search": "T04", "T05_two_sum": "T05", "T06_find_duplicate": "T06",
            "T10_connected_components": "T10", "R1": "R1", "R2": "R2", "R3": "R3", "R6": "R6", "T08_fibonacci": "T08",
            "T11_longest_increasing_subsequence": "T11", "T13_merge_intervals": "T13", "T14_top_k_frequent": "T14",
            "T01_grid_path": "T1", "T02_weighted_shortest_path": "T2"}
    for r in read_jsonl(DEP1 / "known_solution_corpus.jsonl"):
        bt = str(r.get("bench_task") or "")
        t = tmap.get(bt) or tmap.get(bt.split("_")[0]) if bt else None
        if t:
            out[t].append({"source": "art_j3Rm:" + r["source"], "hint": r.get("named"), "code": r["code"]})
    return dict(out)


async def _novelty(items: list[dict[str, Any]], cl: Client) -> list[dict[str, Any]]:
    sem = asyncio.Semaphore(8)
    jA, jB, jC = "openai/gpt-4.1-mini", "google/gemini-2.5-flash", "deepseek/deepseek-chat-v3.1"
    pa = [cl.ask(sem, jA, novelty_prompt(it["task"], it["code"]), "novelty_A") for it in items]
    pb = [cl.ask(sem, jB, novelty_prompt(it["task"], it["code"]), "novelty_B") for it in items]
    ra = await asyncio.gather(*pa)
    rb = await asyncio.gather(*pb)
    out = []
    need = []
    for it, a, b in zip(items, ra, rb):
        A, Bc = parse_class(a), parse_class(b)
        rec = {**{k: it[k] for k in ("row_id", "task", "arm", "label")}, "judge_A": A, "judge_B": Bc}
        if A["class"] and A["class"] == Bc["class"]:
            rec["final"] = A["class"]
        else:
            need.append(len(out))
        out.append(rec)
    if need and not cl.stop:
        rc = await asyncio.gather(*[cl.ask(sem, jC, novelty_prompt(items[i]["task"], items[i]["code"]), "novelty_C")
                                    for i in need])
        for i, c in zip(need, rc):
            C = parse_class(c)
            out[i]["judge_C"] = C
            out[i]["final"] = C["class"] or "UNRESOLVED"
    for o in out:
        o.setdefault("final", "UNRESOLVED")
    return out


def novelty_audit() -> dict[str, Any]:
    labs = [r for r in read_jsonl(DATA_DIR / "labels.jsonl") if r.get("passed") and r["label"] == "other" and r.get("code")]
    if not labs:
        return {"n_correct_other": 0, "rows": [], "by_arm": {}, "novel_count": 0,
                "rule_of_three_upper_95": None, "note": "no correct 'other' program in any arm"}
    cl = Client(OPENROUTER_CAP_USD)
    res = asyncio.run(_novelty(labs, cl))
    corpus = known_corpus()
    for o, r in zip(res, labs):
        o["nearest_known"] = nearest_known(r["task"], r["code"], corpus)
        o["code_head"] = r["code"][:600]
    by_arm = collections.defaultdict(collections.Counter)
    for o in res:
        by_arm[o["arm"]][o["final"]] += 1
    n_novel = sum(1 for o in res if o["final"] == "NOVEL_ALGORITHM")
    n_all = len(res)
    return {"n_correct_other": n_all, "rows": res, "by_arm": {k: dict(v) for k, v in by_arm.items()},
            "novel_count": n_novel, "stopped": cl.reason,
            "rule_of_three_upper_95": (3 / n_all) if (n_novel == 0 and n_all) else None,
            "judges": {"A": "openai/gpt-4.1-mini", "B": "google/gemini-2.5-flash", "C": "deepseek/deepseek-chat-v3.1"}}


def main() -> None:
    setup_logging("judge_audit")
    la = label_audit()
    write_json(RESULTS_DIR / "label_audit.json", {**la, "disagreement": disagreement_stats()})
    logger.info(f"label audit: n={la['n']} agreement={la['overall_agreement']:.3f} flagged={la['flagged_tasks_below_0.85']}")
    na = novelty_audit()
    write_json(RESULTS_DIR / "novelty_audit.json", na)
    logger.info(f"novelty audit: {na['n_correct_other']} correct 'other'; novel={na['novel_count']}; by arm {na['by_arm']}")
    write_json(RESULTS_DIR / "costs.json", {"openrouter_usd_total_artifact": total_spend(), "cap_usd": OPENROUTER_CAP_USD})


if __name__ == "__main__":
    main()
