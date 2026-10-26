#!/usr/bin/env python3
"""R hybrids: every correct lambda-sweep program at 0.2 <= lambda <= 1.0 that the labellers flag (label 'other' or
runtime/AST disagreement) goes to one cheap judge ('single catalogue algorithm or a hybrid of X and Y?'). Cap USD 0.05;
the first 403 'AI Inventor per-run OpenRouter budget' stops the batch. Writes results/r_hybrids.json."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger

from cfg import read_json, read_jsonl, setup_logging, write_json
from cfg7 import BUDGET_MSG7, LABELS7, results7

MODEL = "openai/gpt-4.1-mini"
CAP = 0.05
STATE = {"cost": 0.0, "stopped": None}
PROMPT = """A Python program solves the single-pair shortest-path problem on a directed graph with non-negative integer
weights. Decide whether it implements ONE catalogue algorithm (Dijkstra with a priority queue or array scan,
Bellman-Ford / SPFA, bidirectional Dijkstra, Floyd-Warshall, Dial's buckets) or a HYBRID that mixes the mechanisms of
two of them (e.g. a priority-queue Dijkstra whose nodes are re-relaxed like SPFA). Answer with one JSON object:
{{"class": "SINGLE" or "HYBRID", "algorithms": ["..."], "reason": "<= 25 words"}}.

Program:
```python
{code}
```"""


async def ask(client, code: str, sem: asyncio.Semaphore) -> dict | None:
    from openai import PermissionDeniedError
    async with sem:
        if STATE["stopped"] or STATE["cost"] >= CAP:
            return None
        try:
            r = await client.chat.completions.create(model=MODEL, messages=[{"role": "user",
                                                                             "content": PROMPT.format(code=code[:5000])}],
                                                     temperature=0, max_tokens=150,
                                                     extra_body={"usage": {"include": True}})
        except PermissionDeniedError as e:
            if BUDGET_MSG7 in str(e):
                STATE["stopped"] = str(e)[:200]
            return None
        except Exception as e:  # noqa: BLE001 - one failed call stays unresolved
            logger.error(f"hybrid judge failed: {str(e)[:200]}")
            return None
        u = getattr(r, "usage", None)
        cost = getattr(u, "cost", None) if u is not None else None
        if cost is None and u is not None and hasattr(u, "model_extra"):
            cost = (u.model_extra or {}).get("cost")
        STATE["cost"] += float(cost or 0.0)
        txt = (r.choices[0].message.content or "").strip()
        try:
            return json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
        except (ValueError, json.JSONDecodeError):
            return {"class": None, "raw": txt[:200]}


async def run(items: list[dict]) -> list[dict | None]:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"])
    sem = asyncio.Semaphore(6)
    return await asyncio.gather(*[ask(client, it["code"], sem) for it in items])


def main() -> None:
    setup_logging("hybrid7")
    rr = read_json(results7("r_discreteness.json"))
    ids = set(rr["hybrid_candidates"])
    labs = {r["sample_id"]: r for r in read_jsonl(LABELS7)}
    items = [{"sample_id": s, "code": labs[s].get("code") or ""} for s in sorted(ids) if labs.get(s)]
    res = asyncio.run(run(items)) if items else []
    rows = [{"sample_id": it["sample_id"], "judge": j} for it, j in zip(items, res)]
    n_h = sum(1 for r in rows if (r["judge"] or {}).get("class") == "HYBRID")
    n_corr = rr["n_correct_0.2_1.0"]
    out = {"n_candidates": len(items), "n_hybrid": n_h, "n_correct_0.2_1.0": n_corr,
           "hybrid_share_of_correct": n_h / n_corr if n_corr else None, "rows": rows, "cost_usd": STATE["cost"],
           "stopped_by_budget": STATE["stopped"], "model": MODEL,
           "DISCRETE": bool(rr["fit"]["width_10_90"] <= 0.3 and (n_h / n_corr if n_corr else 0) <= 0.05)}
    write_json(results7("r_hybrids.json"), out)
    print(out["n_candidates"], out["n_hybrid"], out["DISCRETE"], round(STATE["cost"], 5))


if __name__ == "__main__":
    main()
