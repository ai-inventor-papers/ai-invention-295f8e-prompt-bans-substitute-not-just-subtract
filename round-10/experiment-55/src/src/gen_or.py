#!/usr/bin/env python3
"""Stage 1.1 / 1.3 / 1.4 / 1.6: cell table, prompt audit, COMMIT #0a, and forced Qwen3-32B generation on OpenRouter.

Decoding (as iteration 9's top-ups, E46 src/stage_or.py): qwen/qwen3-32b, provider DeepInfra pinned (fp8, no
fallbacks), thinking off (reasoning {enabled: false} plus the Qwen3 ' /no_think' soft switch, E46 deviation D10),
T 1.0, top_p 1, max_tokens 2048, seed = slot + 1, async with a semaphore of 8. GET /key before every batch, running
usage.cost ledger (results/costs.json and logs/cost.jsonl), hard stop at a cumulative USD 0.70 for generation, and
cancellation of everything queued or in flight at the first 403 'AI Inventor per-run OpenRouter budget'.

Usage:
  python src/gen_or.py cells                      # predictions/cells.json + prompt audit + COMMIT #0a
  python src/gen_or.py gen <round> [cells,...] [--limit N]
  python src/gen_or.py topup <alg> <wave>         # named forced programs (bibfs/iddfs/jps/biastar)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import aiohttp
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BUDGET_MSG, add_cost, append_jsonl, read_jsonl, total_cost, trunc  # noqa: E402
from tpg2 import (ALL_CELLS, CELL_INSTR, CELL_INSTR_R3, DATA, FRAMES, LOGS, PRED, RESULTS, TAIL, cell_dc,  # noqa: E402
                  cell_prompt, commit, forbidden_regex, sha256_text, utc_now, write_json)

MODEL = "qwen/qwen3-32b"
PIN = {"order": ["DeepInfra"], "allow_fallbacks": False, "quantizations": ["fp8"]}
MAX_TOKENS = 2048
CONCURRENCY = 8
GEN_STOP_USD = 0.70
ARTIFACT_CAP_USD = 0.80
FACT_OUT = DATA / "raw_factorial.jsonl"
TOPUP_OUT = DATA / "raw_topups_v10.jsonl"
PER_ROUND = 20

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(LOGS / "gen_or.log"), rotation="30 MB", level="DEBUG")


class Stop:
    def __init__(self) -> None:
        self.flag, self.reason = False, ""

    def set(self, reason: str) -> None:
        if not self.flag:
            logger.error(f"STOP: {reason}")
        self.flag, self.reason = True, self.reason or reason


async def key_status(session: aiohttp.ClientSession) -> Any:
    url = os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/key"
    try:
        async with session.get(url, headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
                               timeout=aiohttp.ClientTimeout(total=30)) as r:
            txt = await r.text()
            d = json.loads(txt) if r.status == 200 else {"status": r.status, "text": txt[:300]}
    except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as e:
        d = {"error": type(e).__name__}
    append_jsonl(RESULTS / "openrouter_key_checks.jsonl", {"utc": utc_now(), "key": d})
    return d


def body(prompt: str, slot: int) -> dict[str, Any]:
    return {"model": MODEL, "messages": [{"role": "user", "content": prompt + " /no_think"}], "temperature": 1.0,
            "top_p": 1.0, "seed": int(slot) + 1, "max_tokens": MAX_TOKENS, "usage": {"include": True},
            "provider": PIN, "reasoning": {"enabled": False}}


async def call(session: aiohttp.ClientSession, sem: asyncio.Semaphore, stop: Stop, item: dict[str, Any],
               purpose: str, cap: float, out_path: Path) -> dict[str, Any] | None:
    async with sem:
        if stop.flag:                      # checked again after the slot is obtained
            return None
        if total_cost() >= cap:
            stop.set(f"generation stop at USD {cap} reached")
            return None
        url = os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/chat/completions"
        hdr = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}
        b = body(item["prompt"], item["slot"])
        d, t0 = None, time.time()
        for attempt in range(4):
            if stop.flag:
                return None
            try:
                async with session.post(url, json=b, headers=hdr, timeout=aiohttp.ClientTimeout(total=240)) as r:
                    txt = await r.text()
                    if r.status == 403 and BUDGET_MSG in txt:
                        add_cost(purpose, 0.0, refused=True)
                        stop.set(f"budget 403: {trunc(txt, 200)}")
                        return None
                    if r.status != 200:
                        logger.warning(f"{purpose} {item['cell']} slot {item['slot']} HTTP {r.status}: {trunc(txt, 160)}")
                        await asyncio.sleep(2 * (attempt + 1))
                        continue
                    d = json.loads(txt)
                    if "error" in d and not d.get("choices"):
                        logger.warning(f"{purpose} provider error {trunc(d['error'], 160)}")
                        d = None
                        await asyncio.sleep(2 * (attempt + 1))
                        continue
                    break
            except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as e:
                logger.warning(f"{purpose} {item['cell']} slot {item['slot']} attempt {attempt}: {type(e).__name__}")
                await asyncio.sleep(2 * (attempt + 1))
        if d is None:
            return None
        usage = d.get("usage") or {}
        cost = float(usage.get("cost") or 0.0)
        tot = add_cost(purpose, cost)
        ch = (d.get("choices") or [{}])[0]
        content = (ch.get("message") or {}).get("content") or ""
        if "</think>" in content:
            content = content.split("</think>", 1)[1].strip()
        row = {**item, "content": content, "provider": d.get("provider"), "finish_reason": ch.get("finish_reason"),
               "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
               "cost_usd": cost, "model": MODEL, "author": "qwen3-32b", "engine": "openrouter-deepinfra-fp8",
               "seed": int(item["slot"]) + 1, "gen_seconds": round(time.time() - t0, 2), "utc": utc_now(),
               "or_id": d.get("id")}
        append_jsonl(out_path, row)
        append_jsonl(LOGS / "cost.jsonl", {"utc": row["utc"], "purpose": purpose, "cell": item["cell"],
                                          "slot": item["slot"], "cost_usd": cost, "cumulative_usd": tot})
        logger.debug(f"{purpose} {item['cell']} slot {item['slot']} {row['provider']} ${cost:.6f} total ${tot:.4f}: "
                     f"{trunc(content, 100)}")
        return row


async def run_batch(items: list[dict[str, Any]], purpose: str, out_path: Path, cap: float = GEN_STOP_USD
                    ) -> dict[str, Any]:
    sem = asyncio.Semaphore(CONCURRENCY)
    stop = Stop()
    t0 = time.time()
    async with aiohttp.ClientSession() as session:
        ks = await key_status(session)
        logger.info(f"[{purpose}] key {trunc(ks, 240)}; artifact spend ${total_cost():.4f}; {len(items)} calls")
        tasks = [asyncio.create_task(call(session, sem, stop, it, purpose, cap, out_path)) for it in items]
        done = 0
        for f in asyncio.as_completed(tasks):
            try:
                await f
            except Exception as e:  # noqa: BLE001 - one failed call must not stop the batch
                logger.error(f"call exception {type(e).__name__}: {e}")
            done += 1
            if done % 40 == 0 or done == len(tasks):
                logger.info(f"[{purpose}] {done}/{len(tasks)} {time.time() - t0:.0f}s spend ${total_cost():.4f}")
            if stop.flag:
                for t in tasks:
                    t.cancel()
                break
    dt = time.time() - t0
    append_jsonl(RESULTS / "timing.jsonl", {"key": purpose, "seconds": round(dt, 1), "units": len(items),
                                            "sec_per_unit": round(dt / max(1, len(items)), 3), "utc": utc_now()})
    return {"stopped": stop.flag, "reason": stop.reason, "n": len(items), "seconds": round(dt, 1)}


# ---------------------------------------------------------------------------------------------- stage: cells
def stage_cells() -> None:
    rx = forbidden_regex()
    rows, hits = [], []
    for cell in ALL_CELLS:
        d, c = cell_dc(cell)
        for reworded in (False, True):
            for t in range(len(FRAMES)):
                p = cell_prompt(cell, t, reworded)
                seg = p.split("\n\n")[0]
                h = [m.group(0) for m in rx.finditer(seg)]
                if h:
                    hits.append({"cell": cell, "template": t, "reworded": reworded, "hits": h})
                rows.append({"cell": cell, "template": t, "reworded": reworded, "segment": seg,
                             "prompt_sha256": sha256_text(p)})
    out = {"cells": {cell: {"requested_discipline": cell_dc(cell)[0], "requested_container": cell_dc(cell)[1],
                            "instruction": CELL_INSTR[cell], "instruction_round3": CELL_INSTR_R3[cell],
                            "in_g1_primary": cell != "PROBE"} for cell in ALL_CELLS},
           "frames": FRAMES, "tail": TAIL, "prompts": rows, "forbidden_audit": {"n_prompts": len(rows),
                                                                               "n_hits": len(hits), "hits": hits},
           "decoding": {"model": MODEL, "provider_pin": PIN, "thinking": "off (reasoning disabled + /no_think)",
                        "temperature": 1.0, "top_p": 1.0, "max_tokens": MAX_TOKENS, "seed": "slot + 1",
                        "concurrency": CONCURRENCY},
           "rounds": {"per_round": PER_ROUND, "max_rounds": 3, "target_accepted": 12, "floor": 10,
                      "round3": "reworded instruction (instruction_round3)"},
           "budget": {"generation_stop_usd": GEN_STOP_USD, "artifact_cap_usd": ARTIFACT_CAP_USD},
           "acceptance_rule": "both suites 100% (48-case tests.json + 41-case hidden_tests_t1.json) on the raw AND the "
                              "scrubbed code; alias audit 0 hits after scrub; dedupe by scrubbed sha256 and AST 4-gram "
                              "Jaccard >= 0.95 (keep first); measured (disc, cont) == requested cell -> accept; "
                              "== another planned cell -> reassign (logged); else reject",
           "utc": utc_now()}
    p = PRED / "cells.json"
    write_json(p, out)
    assert not hits, f"forbidden words in prompts: {hits}"
    e = commit(p, "COMMIT0a", "cells, prompts (forbidden-word audit 0 hits), decoding, budget, acceptance rule; "
                              "the instrument and its gate follow as COMMIT0b before any program is classified")
    logger.info(f"cells.json: {len(ALL_CELLS)} cells, {len(rows)} prompts audited, 0 hits; commit line {e['i']}")


# ---------------------------------------------------------------------------------------------- stage: gen
def items_for(cell: str, rnd: int) -> list[dict[str, Any]]:
    out = []
    for i in range(PER_ROUND):
        slot = rnd * 1000 + i
        t = i % len(FRAMES)
        reworded = rnd >= 2
        hint = rnd == 1
        hint2 = rnd >= 2
        p = cell_prompt(cell, t, reworded, hint, hint2)
        out.append({"cell": cell, "round": rnd, "slot": slot, "template": t, "reworded": reworded, "edge_hint": hint, "edge_hint2": hint2,
                    "prompt": p,
                    "prompt_sha256": sha256_text(p), "requested_discipline": cell_dc(cell)[0],
                    "requested_container": cell_dc(cell)[1], "call_index": i})
    return out


def stage_gen(rnd: int, cells: list[str], limit: int | None) -> dict[str, Any]:
    done = {(r["cell"], r["slot"]) for r in read_jsonl(FACT_OUT)}
    items = [it for c in cells for it in items_for(c, rnd) if (c, it["slot"]) not in done]
    if limit:
        items = items[:limit]
    res = asyncio.run(run_batch(items, f"factorial_r{rnd}", FACT_OUT))
    logger.info(f"gen round {rnd}: {res}")
    return res


def stage_topup(alg: str, wave: int, n: int) -> dict[str, Any]:
    import prompts_tp

    ps = [p for p in prompts_tp.forced_set() if p["algorithm"] == alg]
    done = {(r["cell"], r["slot"]) for r in read_jsonl(TOPUP_OUT)}
    items = []
    for i in range(n):
        p = ps[i % len(ps)]
        slot = 5000 + wave * 100 + i
        if (alg, slot) in done:
            continue
        from tpg2 import EDGE_HINT, EDGE_HINT2, spec

        prompt = (p["prompt"] + "\n\n" + EDGE_HINT) if wave == 0 else (p["segment"] + " " + EDGE_HINT2 + "\n\n" + spec())
        items.append({"cell": alg, "algorithm": alg, "round": wave, "slot": slot, "template": p["template"],
                      "alias": p["alias"], "prompt": prompt, "prompt_sha256": sha256_text(prompt),
                      "call_index": i, "named": True, "edge_hint": True})
    res = asyncio.run(run_batch(items, f"topup_{alg}_w{wave}", TOPUP_OUT))
    logger.info(f"top-up {alg} wave {wave}: {res}")
    return res


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "cells":
        stage_cells()
    elif cmd == "gen":
        rnd = int(sys.argv[2])
        cells = sys.argv[3].split(",") if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else ALL_CELLS
        lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
        stage_gen(rnd, cells, lim)
    elif cmd == "topup":
        stage_topup(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else 30)
    else:
        raise SystemExit(f"unknown command {cmd}")
