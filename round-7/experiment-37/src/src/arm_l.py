#!/usr/bin/env python3
"""LEVEL 4 (optional, CPU + API only): the large-mutator arm L on T03.

The same S loop (own 4-island database, same prompts, same evaluator / labeller / critic), 500 children (4 independent
calls per prompt), mutator qwen/qwen3-235b-a22b-2507 at T 1.0 / top-p 1 (fallback qwen/qwen3-coder: same family as
the mutator, never a judge family). Concurrency 8; usage.cost tracked; stop at USD 1.0 (ORClient guard, 403 rule).
Rows: data/rows_L.jsonl (arm 'L'), state data/search_state_L.json, archive results/archive_L.json.
"""

from __future__ import annotations

import asyncio
import time

from loguru import logger

from common import CAP_USD, read_json, write_json, RESULTS, utc_now

MODEL = "qwen/qwen3-235b-a22b-2507"
FALLBACK = "qwen/qwen3-coder"


def stage_l(n: int = 500) -> None:
    from critic import Critic
    from engine import APIEngine
    from inputs import load_task
    from orclient import ORClient
    from run import Evaluator, run_task
    client = ORClient("L", CAP_USD["L"], concurrency=8)
    # availability probe (one tiny call; falls back to the coder model of the same family)
    model = MODEL
    r = asyncio.run(client.chat(MODEL, [{"role": "user", "content": "Reply with OK."}], temperature=0.0,
                                max_tokens=5, use_cache=False, tag="L:probe"))
    if r is None or r.get("text") is None:
        logger.warning(f"{MODEL} unavailable ({r}); using {FALLBACK}")
        model = FALLBACK
    client2 = ORClient("L", CAP_USD["L"], concurrency=8)
    eng = APIEngine(model, client2, fallback=FALLBACK if model == MODEL else None)
    obj = load_task("T03")
    critic = Critic()
    ev = Evaluator({"T03": obj}, critic, workers=3)
    t0 = time.time()
    run_task("T03", obj, {"S": n}, eng, ev, critic, {}, deadline_epoch=time.time() + 3 * 3600, s_arm="L", tag="L",
             model_meta={"model": model, "precision": "api", "gpu": None})
    write_json(RESULTS / "L_arm.json", {"utc": utc_now(), "model": model, "n_target": n,
                                        "usd": client2.spent, "stop_reason": client2.stop_reason,
                                        "wall_s": round(time.time() - t0, 1)})
    _ = read_json
