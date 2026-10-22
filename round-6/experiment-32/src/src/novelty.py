#!/usr/bin/env python3
"""Novelty audit of every correct 'other' program in every arm (behaviour and causal): two blind judges from
different families (google/gemini-2.5-flash, openai/gpt-4.1-mini), a third (deepseek/deepseek-chat-v3.1) on
disagreement, and the nearest known solution from the dependency pool (LeetCode references, Mercury human solutions,
TheAlgorithms, KodCode, XLCoST) by normalised-code similarity for the manual comparison.
Classes: NOVEL / CATALOGUE_VARIANT / LABELLER_MISS / DEGENERATE. Writes results/novelty.json."""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger

from cfg import BUDGET_MSG, DATA_DIR, RESULTS_DIR, append_jsonl, read_jsonl, setup_logging, utc_now, write_json
import prompts as PR

MODELS = ("google/gemini-2.5-flash", "openai/gpt-4.1-mini", "deepseek/deepseek-chat-v3.1")
CLASSES = ("NOVEL", "CATALOGUE_VARIANT", "LABELLER_MISS", "DEGENERATE")


def norm_code(c: str) -> str:
    c = re.sub(r"#.*", "", c or "")
    c = re.sub(r'"""[\s\S]*?"""', "", c)
    return re.sub(r"\s+", " ", c).strip()


def nearest(code: str, task: str, pool: list[dict[str, Any]]) -> dict[str, Any] | None:
    from rapidfuzz import fuzz

    cands = [p for p in pool if p["task"] == task]
    if not cands:
        return None
    nc = norm_code(code)
    best = max(cands, key=lambda p: fuzz.ratio(nc, norm_code(p["code"])))
    return {"source": best["source"], "id": best["id"], "similarity": fuzz.ratio(nc, norm_code(best["code"])) / 100,
            "code_head": best["code"][:600]}


def prompt(task: str, code: str) -> str:
    from judges import TITLES

    cat = "\n".join(f"- {c['mode']}: {c['display_name']}: {c['mechanism']}" for c in PR.catalogue(task))
    return (f"A Python program solves this task correctly (it passes hidden tests): {TITLES[task]}.\nKnown algorithm "
            f"catalogue for the task:\n{cat}\n\nAn automatic labeller could not assign any catalogue label to it. Decide "
            "which class fits the program's actual mechanism:\n- LABELLER_MISS: it plainly implements one catalogue "
            "algorithm (the labeller missed it).\n- CATALOGUE_VARIANT: a recognisable variant or hybrid of catalogue "
            "algorithms.\n- DEGENERATE: no real algorithm (hard-coded answers, a library call that does all the work, "
            "or a trivial special case).\n- NOVEL: a genuinely different algorithm, not a catalogue algorithm or a "
            "standard textbook method for this task.\n\nProgram:\n```python\n" + code[:4000] + "\n```\n\nAnswer with "
            "JSON only: {\"class\": \"<LABELLER_MISS|CATALOGUE_VARIANT|DEGENERATE|NOVEL>\", \"closest_mode\": \"<id or "
            "none>\", \"reason\": \"<one sentence>\"}")


async def judge_all(items: list[dict[str, Any]], model: str) -> list[dict[str, Any] | None]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"],
                         timeout=90, max_retries=2)
    sem = asyncio.Semaphore(8)
    stop = {"v": False}

    async def one(it):
        async with sem:
            if stop["v"]:
                return None
            try:
                r = await client.chat.completions.create(model=model, temperature=0, max_tokens=200,
                                                         messages=[{"role": "user", "content": prompt(it["task"], it["code"])}],
                                                         extra_body={"usage": {"include": True}})
            except Exception as e:  # noqa: BLE001
                if BUDGET_MSG in str(e):
                    stop["v"] = True
                logger.warning(f"novelty judge {model}: {str(e)[:150]}")
                return None
            cost = float(getattr(r.usage, "cost", 0) or 0) if r.usage else 0.0
            append_jsonl(RESULTS_DIR / "costs_judges.jsonl", [{"model": model, "mode": "NOVELTY", "cost": cost,
                                                              "utc": utc_now()}])
            m = re.search(r"\{.*\}", r.choices[0].message.content or "", re.S)
            try:
                d = json.loads(m.group(0)) if m else None
            except json.JSONDecodeError:
                d = None
            if d and d.get("class") in CLASSES:
                return d
            return None

    return await asyncio.gather(*[one(it) for it in items])


def main() -> dict[str, Any]:
    setup_logging("novelty")
    rows = (read_jsonl(DATA_DIR / "labels.jsonl") + read_jsonl(DATA_DIR / "labels_causal.jsonl")
            + read_jsonl(DATA_DIR / "labels_causal_extra.jsonl") + read_jsonl(DATA_DIR / "labels_causal_extra2.jsonl"))
    items = [r for r in rows if r.get("passed") and r.get("label") == "other" and r.get("code")]
    pool = read_jsonl(DATA_DIR / "novelty_pool.jsonl")
    out: dict[str, Any] = {"n_correct_other": len(items), "items": []}
    if items:
        res = {m: asyncio.run(judge_all(items, m)) for m in MODELS[:2]}
        dis = [i for i, (a, b) in enumerate(zip(res[MODELS[0]], res[MODELS[1]]))
               if not (a and b and a["class"] == b["class"])]
        r3 = asyncio.run(judge_all([items[i] for i in dis], MODELS[2])) if dis else []
        third = dict(zip(dis, r3))
        for i, it in enumerate(items):
            a, b = res[MODELS[0]][i], res[MODELS[1]][i]
            if a and b and a["class"] == b["class"]:
                cls = a["class"]
            else:
                vals = [x["class"] for x in (a, b, third.get(i)) if x]
                top = Counter(vals).most_common(1)
                cls = top[0][0] if top and top[0][1] >= 2 else "UNRESOLVED"
            out["items"].append({"sample_id": it["sample_id"], "task": it["task"], "arm": it.get("arm"),
                                 "cell": it.get("cell"), "class": cls, "j1": a, "j2": b, "j3": third.get(i),
                                 "nearest_known": nearest(it["code"], it["task"], pool), "code": it["code"]})
    out["classes"] = dict(Counter(x["class"] for x in out["items"]))
    write_json(RESULTS_DIR / "novelty.json", out)
    logger.info(f"novelty audit: {out['n_correct_other']} correct 'other' programs -> {out['classes']}")
    return out


if __name__ == "__main__":
    main()
