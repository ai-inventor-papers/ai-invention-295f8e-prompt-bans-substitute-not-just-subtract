#!/usr/bin/env python3
"""Two-family novelty audit of every correct 'other' program (plan STEP 10).

Each correct program labelled 'other' goes to two blind judges from different families (google/gemini-2.5-flash-lite,
openai/gpt-4.1-mini); a third (deepseek/deepseek-chat-v3.1) resolves disagreements. Beside it, a manual-style difflib
comparison with the nearest known solution (bench reference programs + the art_j3Rm_lr2nzR6 known-solution corpus for
the task). Classes: NOVEL / CATALOGUE_VARIANT / LABELLER_MISS / DEGENERATE. Spend cap USD 0.15 for this audit; the first
403 'AI Inventor per-run OpenRouter budget' stops the batch.
"""

from __future__ import annotations

import asyncio
import difflib
import json
import os
import sys
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import INPUTS, RESULTS_DIR, ROOT, read_json, read_jsonl, setup_logging, write_json
from cfg6 import BUDGET_MSG6, DEFAULT6, JUDGE_CAP_NOVELTY, LABELS, SAMPLES

JUDGES = ("google/gemini-2.5-flash-lite", "openai/gpt-4.1-mini")
TIE = "deepseek/deepseek-chat-v3.1"
CLASSES = ("NOVEL", "CATALOGUE_VARIANT", "LABELLER_MISS", "DEGENERATE")
CACHE = ROOT / "data" / "novelty_cache.jsonl"
STATE = {"cost": 0.0, "stopped": None}


def task_info(task: str) -> tuple[str, list[str]]:
    if task in ("T1", "T2"):
        spec = (INPUTS / "exp8" / "suite" / "tasks" / ("t1_grid" if task == "T1" else "t2_wsp") / "spec.txt").read_text()
        cat = {"T1": ["bfs", "dfs", "bidirectional bfs", "iddfs", "a* / greedy best-first", "dijkstra"],
               "T2": ["dijkstra", "bellman-ford / spfa", "bidirectional dijkstra", "dial buckets", "floyd-warshall",
                      "a*"]}[task]
        return spec, cat
    for d in (INPUTS / "exp11" / "bench").iterdir():
        if d.is_dir() and d.name.startswith(task + "_"):
            sp = read_json(d / "spec.json")
            return sp["spec_text"], [f"{c.get('mode') or c.get('name')}: {c.get('display_name', '')}"
                                     for c in sp["catalogue"]]
    return "", []


def known_solutions(task: str) -> list[tuple[str, str]]:
    out = []
    for d in (INPUTS / "exp11" / "bench").iterdir():
        if d.is_dir() and d.name.startswith(task + "_"):
            out += [(f"reference:{f.stem}", f.read_text()) for f in sorted((d / "references").glob("*.py"))]
    if task in ("T1", "T2"):
        d = INPUTS / "exp8" / "suite" / "tasks" / ("t1_grid" if task == "T1" else "t2_wsp") / "references"
        out += [(f"reference:{f.stem}", f.read_text()) for f in sorted(d.glob("*.py"))]
    dep = read_json(ROOT / "data" / "dep_extract.json")
    tmap = {"T2": "T02"}
    out += [(c["src"], c["code"]) for c in dep["known_solution_corpus"] if c["task"] in (task, tmap.get(task))]
    return out


def nearest(code: str, sols: list[tuple[str, str]]) -> dict[str, Any]:
    best = (None, 0.0)
    for name, s in sols:
        r = difflib.SequenceMatcher(None, code, s, autojunk=False).ratio()
        if r > best[1]:
            best = (name, r)
    return {"nearest": best[0], "similarity": round(best[1], 4), "n_compared": len(sols)}


PROMPT = """You audit programs for algorithmic novelty. Task specification:
---
{spec}
---
Known algorithm catalogue for this task: {cat}.
The program below passes all hidden tests, but an automatic labeller could not assign it to the catalogue.
Classify it as exactly one of:
NOVEL - a genuinely different algorithm, neither in the catalogue nor a standard textbook method for this task;
CATALOGUE_VARIANT - a standard or catalogue algorithm with cosmetic or implementation-level changes;
LABELLER_MISS - plainly one of the catalogue algorithms that the labeller should have recognised (a standard-library
call that implements a catalogue algorithm, e.g. sorted() for a full sort or heapq.nsmallest for a heap, counts as that
catalogue algorithm);
DEGENERATE - hard-coded answers or special-casing that passes only by exploiting the tests, not a general algorithm.
Reply with JSON only: {{"class": "...", "catalogue_name": "... or null", "reason": "one sentence"}}
Program:
```python
{code}
```"""


async def ask(client: Any, model: str, prompt: str, sem: asyncio.Semaphore) -> dict[str, Any] | None:
    from openai import PermissionDeniedError

    async with sem:
        if STATE["stopped"] or STATE["cost"] >= JUDGE_CAP_NOVELTY:
            return None
        try:
            r = await client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}],
                                                     temperature=0, max_tokens=200,
                                                     extra_body={"usage": {"include": True}})
        except PermissionDeniedError as e:
            if BUDGET_MSG6 in str(e):
                STATE["stopped"] = str(e)[:200]
                logger.error(f"OpenRouter budget refusal: batch stopped ({e})")
            return None
        except Exception as e:  # noqa: BLE001 - one failed judge call is logged and left unresolved
            logger.error(f"judge {model} failed: {str(e)[:200]}")
            return None
        u = getattr(r, "usage", None)
        cost = getattr(u, "cost", None) if u is not None else None
        if cost is None and u is not None and hasattr(u, "model_extra"):
            cost = (u.model_extra or {}).get("cost")
        STATE["cost"] += float(cost or 0.0)
        txt = (r.choices[0].message.content or "").strip()
        logger.debug(f"{model}: {txt[:200]}")
        try:
            j = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
        except (ValueError, json.JSONDecodeError):
            return {"class": None, "raw": txt[:200]}
        c = str(j.get("class", "")).upper().replace(" ", "_")
        return {"class": c if c in CLASSES else None, "catalogue_name": j.get("catalogue_name"),
                "reason": str(j.get("reason", ""))[:200]}


async def audit(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"])
    sem = asyncio.Semaphore(8)
    prompts = []
    for it in items:
        spec, cat = task_info(it["task"])
        prompts.append(PROMPT.format(spec=spec[:3000], cat="; ".join(cat), code=it["code"][:6000]))
    res = await asyncio.gather(*[asyncio.gather(*[ask(client, m, p, sem) for m in JUDGES]) for p in prompts])
    out = []
    for it, p, (a, b) in zip(items, prompts, res):
        ca, cb = (a or {}).get("class"), (b or {}).get("class")
        final, tie = None, None
        if ca and ca == cb:
            final = ca
        elif ca or cb:
            tie = await ask(client, TIE, p, sem)
            final = (tie or {}).get("class") or "UNRESOLVED"
        else:
            final = "UNRESOLVED"
        out.append({**{k: it[k] for k in ("sample_id", "task", "arm")}, "judge_a": a, "judge_b": b, "tie": tie,
                    "class": final, "difflib": it["difflib"]})
    return out


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("novelty6")
    labs = read_jsonl(LABELS)
    arms = {r["sample_id"]: r["arm"] for r in read_jsonl(SAMPLES)}
    items = []
    for r in labs:
        if r.get("passed") and r.get("label") == "other" and r.get("code"):
            items.append({"sample_id": r["sample_id"], "task": r["task"], "arm": arms.get(r["sample_id"], r["arm"]),
                          "code": r["code"]})
    sols = {t: known_solutions(t) for t in {it["task"] for it in items}}
    for it in items:
        it["difflib"] = nearest(it["code"], sols[it["task"]])
    logger.info(f"novelty audit: {len(items)} correct 'other' programs")
    res = asyncio.run(audit(items)) if items else []
    counts: dict[str, int] = {}
    for r in res:
        counts[r["class"]] = counts.get(r["class"], 0) + 1
    out = {"n_correct_other": len(items), "classes": counts, "rows": res, "cost_usd": round(STATE["cost"], 5),
           "stopped_by_budget": STATE["stopped"], "judges": list(JUDGES), "tie_breaker": TIE,
           "defaults": DEFAULT6}
    write_json(RESULTS_DIR / "novelty_audit.json", out)
    logger.info(f"novelty audit: {counts}; cost USD {STATE['cost']:.4f}")


if __name__ == "__main__":
    main()
