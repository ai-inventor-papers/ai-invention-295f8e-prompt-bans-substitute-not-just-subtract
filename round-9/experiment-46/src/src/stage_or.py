#!/usr/bin/env python3
"""Stage 3 (OpenRouter): naming gate for the descriptions (3a) and forced top-ups of Qwen3-32B programs (3b).

Requests use iteration 8's C5 builder (sample_or.body_for: qwen/qwen3-32b, DeepInfra fp8 pinned with
allow_fallbacks false, reasoning disabled plus the ' /no_think' soft switch, T 1.0, top_p 1.0). At most 8 calls in
flight. GET <base_url>/key before every batch; running usage.cost total in results/costs.json; artifact cap
USD 0.40 (top-ups stop at USD 0.32); the first HTTP 403 'AI Inventor per-run OpenRouter budget' stops the batch and
cancels everything queued or in flight (checked again after each call gets its slot).
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from typing import Any

import aiohttp
from loguru import logger

import sample_or
from common import (BUDGET_MSG, CANON_ORDER, CONFIGS, add_cost, append_jsonl, deviation, read_json, read_jsonl,
                    sha256_text, total_cost, trunc, utc_now, write_json)
from tpg import (DATA, NAMING_N, NAMING_PASS, OR_CAP_USD, OR_PIN, RESULTS, TOPUP_MAX_ATTEMPTS, TOPUP_STOP_USD,
                 TOPUP_TARGET)

NAMING_Q = ("The following describes an algorithm for finding a path between two cells of a 2-D grid with walls "
            "(4-neighbour moves, each move costs 1): \"{desc}\". What is the standard name of this algorithm? Reply "
            "with the name only.")
PRECEDENCE = ["idastar", "biastar", "bibfs", "iddfs", "jps", "gbfs", "astar", "dijkstra_unit", "bfs", "dfs"]


def score_name(ans: str) -> str | None:
    """Dedicated naming patterns (not SHORT_FORMS); first algorithm in PRECEDENCE whose pattern matches."""
    s = (ans or "").lower()
    s = re.sub(r"<think>.*?</think>", " ", s, flags=re.S)
    astar = r"(a\*|a-star|a star|\bastar\b)"
    pats = {
        "idastar": r"(ida\*|ida-star|ida star|\bidastar\b|iterative[- ]deepening a(\*|-star| star))",
        "biastar": rf"bidirectional.*{astar}|{astar}.*bidirectional",
        "bibfs": r"bidirectional.*(bfs|breadth)|(bfs|breadth).*bidirectional",
        "iddfs": r"(iterative[- ]deepening|\biddfs\b)",
        "jps": r"(jump[- ]point|\bjps\b)",
        "gbfs": r"(greedy|best[- ]first)",
        "astar": r"(?<!id)(?<!ida)(?<!ida )(a\*|a-star|a star|\bastar\b)",
        "dijkstra_unit": r"(dijkstra|uniform[- ]cost)",
        "bfs": r"(\bbfs\b|breadth[- ]first)",
        "dfs": r"(\bdfs\b|depth[- ]first)",
    }
    for a in PRECEDENCE:
        if re.search(pats[a], s):
            return a
    return None


SCORER_TESTS = [("IDA*", "idastar"), ("Iterative Deepening A*", "idastar"), ("IDA* search", "idastar"),
                ("Bidirectional A*", "biastar"), ("Bidirectional A* search", "biastar"),
                ("bidirectional a-star", "biastar"), ("Bidirectional BFS", "bibfs"),
                ("Bidirectional Breadth-First Search", "bibfs"), ("Bidirectional search", None),
                ("Iterative Deepening Depth-First Search", "iddfs"), ("IDDFS", "iddfs"),
                ("Jump Point Search", "jps"), ("JPS", "jps"), ("Greedy Best-First Search", "gbfs"),
                ("Best-First Search", "gbfs"), ("A* search", "astar"), ("A-star", "astar"), ("A* algorithm", "astar"),
                ("Dijkstra's algorithm", "dijkstra_unit"), ("Uniform Cost Search", "dijkstra_unit"),
                ("Uniform-cost search", "dijkstra_unit"), ("Breadth-First Search", "bfs"), ("BFS", "bfs"),
                ("Breadth-first search (BFS)", "bfs"), ("Depth-First Search", "dfs"), ("DFS", "dfs"),
                ("Depth-first search with backtracking", "dfs"), ("Flood fill", None), ("Lee algorithm", None),
                ("<think>\n\n</think>\n\nA* Search", "astar")]


def scorer_unit_test() -> dict[str, Any]:
    res = [{"answer": a, "expected": e, "got": score_name(a)} for a, e in SCORER_TESTS]
    ok = all(r["expected"] == r["got"] for r in res)
    return {"n": len(res), "pass": ok, "failures": [r for r in res if r["expected"] != r["got"]]}


# ---------------------------------------------------------------------------------------------- client
class Stop:
    def __init__(self) -> None:
        self.flag = False
        self.reason = ""

    def set(self, r: str) -> None:
        if not self.flag:
            logger.error(f"STOP: {r}")
        self.flag, self.reason = True, self.reason or r


async def key_status(session: aiohttp.ClientSession) -> dict[str, Any]:
    url = os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/key"
    try:
        async with session.get(url, headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
                               timeout=aiohttp.ClientTimeout(total=30)) as r:
            txt = await r.text()
            d = json.loads(txt) if r.status == 200 else {"status": r.status, "text": trunc(txt, 200)}
    except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as e:
        d = {"error": type(e).__name__}
    append_jsonl(RESULTS / "openrouter_key_checks.jsonl", {"utc": utc_now(), "key": d})
    return d


def body(prompt: str, slot: int, max_tokens: int) -> dict[str, Any]:
    b = sample_or.body_for("C5", CONFIGS["C5"], prompt, slot, OR_PIN, True)
    b["max_tokens"] = max_tokens
    return b


async def call(session: aiohttp.ClientSession, sem: asyncio.Semaphore, stop: Stop, item: dict[str, Any],
               purpose: str, max_tokens: int, cap: float, out_path: Any) -> dict[str, Any] | None:
    async with sem:
        if stop.flag:
            return None
        if total_cost() >= cap:
            stop.set(f"artifact cap {cap} reached")
            return None
        url = os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/chat/completions"
        hdr = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}
        b = body(item["prompt"], item["slot"], max_tokens)
        d = None
        t0 = time.time()
        for attempt in range(4):
            if stop.flag:
                return None
            try:
                async with session.post(url, json=b, headers=hdr, timeout=aiohttp.ClientTimeout(total=300)) as r:
                    txt = await r.text()
                    if r.status == 403 and BUDGET_MSG in txt:
                        add_cost(purpose, 0.0, refused=True)
                        stop.set(f"budget 403: {trunc(txt, 200)}")
                        return None
                    if r.status != 200:
                        logger.warning(f"{purpose} slot {item['slot']} HTTP {r.status}: {trunc(txt, 160)}")
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
                logger.warning(f"{purpose} slot {item['slot']} attempt {attempt}: {type(e).__name__}")
                await asyncio.sleep(2 * (attempt + 1))
        if d is None:
            return None
        usage = d.get("usage") or {}
        cost = float(usage.get("cost") or 0.0)
        tot = add_cost(purpose, cost)
        ch = (d.get("choices") or [{}])[0]
        msg = ch.get("message") or {}
        content = msg.get("content") or ""
        if "</think>" in content:
            content = content.split("</think>", 1)[1].strip()
        row = {**item, "content": content, "provider": d.get("provider"), "finish_reason": ch.get("finish_reason"),
               "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
               "cost_usd": cost, "model": "qwen/qwen3-32b", "engine": "openrouter", "seed": int(item["slot"]) + 1,
               "gen_seconds": round(time.time() - t0, 2), "utc": utc_now(), "or_id": d.get("id")}
        append_jsonl(out_path, row)
        logger.debug(f"{purpose} {item.get('key')} slot {item['slot']} {row['provider']} ${cost:.6f} total "
                     f"${tot:.4f}: {trunc(content, 80)}")
        return row


async def run_batch(items: list[dict[str, Any]], purpose: str, max_tokens: int, cap: float, out_path: Any,
                    concurrency: int = 8) -> dict[str, Any]:
    sem = asyncio.Semaphore(concurrency)
    stop = Stop()
    async with aiohttp.ClientSession() as session:
        ks = await key_status(session)
        logger.info(f"[{purpose}] key status {trunc(ks, 200)}; artifact spend ${total_cost():.4f}; {len(items)} calls")
        tasks = [asyncio.create_task(call(session, sem, stop, it, purpose, max_tokens, cap, out_path)) for it in items]
        done = 0
        for f in asyncio.as_completed(tasks):
            try:
                await f
            except Exception as e:  # noqa: BLE001 - one failed call must not stop the batch
                logger.error(f"call exception {type(e).__name__}: {e}")
            done += 1
            if done % 50 == 0 or done == len(tasks):
                logger.info(f"[{purpose}] {done}/{len(tasks)} spend ${total_cost():.4f}")
            if stop.flag:
                for t in tasks:
                    t.cancel()
                break
    return {"stopped": stop.flag, "reason": stop.reason, "n": len(items)}


# ---------------------------------------------------------------------------------------------- 3a naming gate
def _naming_round(descs: list[dict[str, Any]], tag: str) -> dict[str, list[dict[str, Any]]]:
    out_path = DATA / "naming_calls.jsonl"
    done = {(r["key"], r["slot"]) for r in read_jsonl(out_path)}
    items = []
    for d in descs:
        for s in range(NAMING_N):
            if (d["key"], s) not in done:
                items.append({"key": d["key"], "algorithm": d["algorithm"], "text": d["text"], "slot": s,
                              "round": tag, "prompt": NAMING_Q.format(desc=d["text"])})
    if items:
        res = asyncio.run(run_batch(items, "naming_gate", 40, OR_CAP_USD, out_path))
        if res["stopped"]:
            deviation("F5-budget-naming", f"naming gate stopped: {res['reason']}")
    rows = read_jsonl(out_path)
    by: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by.setdefault(r["key"], []).append(r)
    return by


def stage_naming(*args: str) -> None:
    ut = scorer_unit_test()
    write_json(RESULTS / "naming_scorer_test.json", ut)
    assert ut["pass"], f"naming scorer unit test failed: {ut['failures']}"
    dv = read_json(DATA / "descriptions_v0.json")
    current = []
    for r in dv["descriptions"]:
        current.append({"key": f"{r['algorithm']}|D{r['desc_index'] + 1}|v0", "algorithm": r["algorithm"],
                        "desc_index": r["desc_index"], "text": r["text"], "version": 0})
    final: dict[str, dict[str, Any]] = {}
    history: dict[str, list[dict[str, Any]]] = {}
    used_texts = {(c["algorithm"], c["text"]) for c in current}
    for rnd in range(3):
        by = _naming_round(current, f"r{rnd}")
        nxt = []
        for c in current:
            rows = by.get(c["key"], [])[:NAMING_N]
            names = [score_name(r["content"]) for r in rows]
            k = sum(1 for n in names if n == c["algorithm"])
            modal = max(set(names), key=names.count) if names else None
            rec = {**c, "n": len(rows), "n_correct": k, "rate": k / max(len(rows), 1), "modal": modal,
                   "answers": [trunc(r["content"], 60) for r in rows], "pass": k >= NAMING_PASS}
            slot = f"{c['algorithm']}|{c['desc_index']}"
            history.setdefault(slot, []).append(rec)
            if rec["pass"]:
                final[slot] = rec
            elif rnd < 2:
                rw = dv["rewrites"].get(c["algorithm"], [[]])[0]
                cand = [t for t in rw if (c["algorithm"], t) not in used_texts]
                if cand:
                    t = cand[0]
                    used_texts.add((c["algorithm"], t))
                    nxt.append({"key": f"{c['algorithm']}|D{c['desc_index'] + 1}|v{rnd + 1}",
                                "algorithm": c["algorithm"], "desc_index": c["desc_index"], "text": t,
                                "version": rnd + 1})
        current = nxt
        if not current:
            break
    rows_out = []
    for slot, hist in history.items():
        best = max(hist, key=lambda h: h["rate"])
        rows_out.append({"slot": slot, "algorithm": hist[0]["algorithm"], "desc_index": hist[0]["desc_index"],
                         "passed": slot in final, "final": final.get(slot), "best_rate": best["rate"],
                         "attempts": hist})
    excluded = [r for r in rows_out if not r["passed"]]
    per_alg = {a: sum(1 for r in rows_out if r["algorithm"] == a and r["passed"]) for a in CANON_ORDER}
    write_json(RESULTS / "naming_gate.json", {"rule": f">= {NAMING_PASS}/{NAMING_N} at T 1.0, top_p 1.0, thinking off",
                                              "question": NAMING_Q, "rows": rows_out, "passing_per_algorithm": per_alg,
                                              "excluded": [(r["slot"], r["best_rate"]) for r in excluded],
                                              "spend_usd": total_cost(), "utc": utc_now()})
    logger.info(f"naming gate: passing per algorithm {per_alg}; excluded {[(r['slot'], r['best_rate']) for r in excluded]}")


# ---------------------------------------------------------------------------------------------- 3b top-ups
def topup_items(alg: str, wave: int) -> list[dict[str, Any]]:
    import prompts_tp

    ps = [p for p in prompts_tp.forced_set() if p["algorithm"] == alg]
    return [{"key": alg, "algorithm": alg, "template": p["template"], "alias": p["alias"], "group": p["group"],
             "prompt": p["prompt"], "prompt_id": f"forced|{alg}|t{p['template']}|j{p['alias']}",
             "slot": wave * 30 + i, "wave": wave} for i, p in enumerate(ps)]


def stage_topups(*args: str) -> None:
    import label_tp
    import programs
    import stage_cpu
    import expansion

    out_path = DATA / "topups.jsonl"
    grids = read_json(DATA / "probe_grids.json")["grids"]
    refs = stage_cpu.references()
    rt = read_json(DATA / "reference_traces.json")["traces"]
    ref_algs = [r["algorithm"] for r in refs]
    accepted: dict[str, int] = {}
    report: dict[str, Any] = {"waves": []}
    for wave in range(TOPUP_MAX_ATTEMPTS // 30):
        rows = read_jsonl(out_path)
        todo_algs = []
        for a in CANON_ORDER:
            n_acc = accepted.get(a, 0)
            n_att = sum(1 for r in rows if r["algorithm"] == a)
            if n_acc < TOPUP_TARGET and n_att < TOPUP_MAX_ATTEMPTS:
                todo_algs.append(a)
        if not todo_algs or total_cost() >= TOPUP_STOP_USD:
            break
        done = {(r["algorithm"], r["slot"]) for r in rows}
        items = [it for a in todo_algs for it in topup_items(a, wave) if (a, it["slot"]) not in done]
        res = asyncio.run(run_batch(items, "topups", 1536, TOPUP_STOP_USD, out_path))
        rows = read_jsonl(out_path)
        codes = [(label_tp.extract_last_fence(r["content"])[0], r["algorithm"]) for r in rows]
        acc = programs.accept(codes, grids, rt, ref_algs)
        accepted = {}
        for (c, a), r in zip(codes, acc):
            accepted[a] = accepted.get(a, 0) + int(bool(r.get("accepted")))
        report["waves"].append({"wave": wave, "algorithms": todo_algs, "n_calls": len(items), "batch": res,
                                "accepted_after": dict(accepted), "spend_usd": total_cost()})
        logger.info(f"top-ups wave {wave}: accepted {accepted} spend ${total_cost():.4f}")
        if res["stopped"]:
            deviation("F5-budget-topups", f"top-ups stopped: {res['reason']}")
            break
    report["accepted"] = accepted
    report["spend_usd"] = total_cost()
    write_json(RESULTS / "topups.json", report)
    _ = expansion, sha256_text
