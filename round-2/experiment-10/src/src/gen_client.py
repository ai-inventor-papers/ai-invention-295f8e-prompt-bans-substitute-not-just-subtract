#!/usr/bin/env python3
"""S1 / S4 vLLM sessions: builds the request list of a phase and sends it to the running `vllm serve` process as
token-id prompts with every SamplingParams field set explicitly and a per-request seed
int(sha256('task|cond|tpl|sample_id')[:8], 16). Rows are appended to data/raw_gen.jsonl; already-present row ids are
skipped, so every phase resumes.

Phases: A1 baseline (5 x 20 per task), A2 forced round 1 (10 x 4 per algorithm), A3 free-form (20 per X, max 48 tokens),
A4 (modal ban W1-5 x 20, mention twin x 10, listall x 10; needs A1 labels), A5 (two-step ban x 10; needs A4 labels),
A6 forced top-ups (rounds of 40 until 30 kept or 120 attempts; descriptive variant after 80 attempts with < 15 kept),
C (the two highest-baseline-FRLP non-default single bans per task, W1-5 x 10).
"""

from __future__ import annotations

import argparse
import asyncio
import collections
import json
import time
from pathlib import Path
from typing import Any

import aiohttp
from loguru import logger

from src.ws import DATA, DECODING, DECODING_FREE, LOGS, MODEL_TAG, RESULTS, append_jsonl, read_jsonl, setup_logging, write_json
from src import config as K

RAW = DATA / "raw_gen.jsonl"
LABELLED = DATA / "labelled.jsonl"
FREE = DATA / "free_answers.jsonl"
SERVED = "llama31"
N_FORCED_ROUND = 4  # per paraphrase per round (40 per algorithm)
FORCED_TARGET = 30
FORCED_MAX_ATTEMPTS = 120
DESC_AFTER = 80
DESC_MIN_KEPT = 15


def sampling(max_tokens: int, seed: int, logprobs: bool) -> dict[str, Any]:
    p = {"n": 1, "temperature": 1.0, "top_p": 1.0, "top_k": -1, "min_p": 0.0, "repetition_penalty": 1.0,
         "presence_penalty": 0.0, "frequency_penalty": 0.0, "max_tokens": max_tokens, "seed": seed,
         "stop_token_ids": K.EOS_IDS, "skip_special_tokens": True, "include_stop_str_in_output": False,
         "ignore_eos": False}
    if logprobs:
        p.update({"logprobs": 1, "return_tokens_as_token_ids": True})
    return p


def req(prompt: dict[str, Any], *, phase: str, sample_id: int, max_tokens: int = 1024,
        tpl: Any = None) -> dict[str, Any]:
    tpl = tpl if tpl is not None else (prompt["w"] if prompt["w"] is not None else prompt["pid"])
    seed = K.request_seed(prompt["task"], prompt["cond"], tpl, sample_id)
    return {"row_id": f"{phase}|{prompt['task']}|{prompt['cond']}|{sample_id}", "phase": phase,
            "task": prompt["task"], "condition": prompt["cond"], "kind": prompt["kind"], "X": prompt["X"],
            "template": prompt["w"], "paraphrase_id": prompt["pid"], "sample_id": sample_id, "seed": seed,
            "prompt_sha": prompt["sha"], "ids": prompt["ids"], "max_tokens": max_tokens}


# ------------------------------------------------------------------------------------------------ label helpers
def labelled_rows() -> list[dict[str, Any]]:
    return read_jsonl(LABELLED)


def attempted(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in rows if r.get("label") not in (None, "no_code")]


def modal_default(task: str) -> str:
    rows = [r for r in attempted(labelled_rows()) if r["task"] == task and r["kind"] == "baseline"]
    c = collections.Counter(r["label"] for r in rows if r["label"] in K.MODES[task])
    if not c:
        raise RuntimeError(f"no labelled baseline programs for {task}")
    return c.most_common(1)[0][0]


def realised_substitute(task: str, d: str) -> tuple[str, bool, dict[str, int]]:
    rows = [r for r in attempted(labelled_rows()) if r["task"] == task and r["kind"] == "ban" and r["X"] == d]
    c = collections.Counter(r["label"] for r in rows if r["label"] != d)
    cat = collections.Counter({k: v for k, v in c.items() if k in K.MODES[task]})
    if not cat:
        raise RuntimeError(f"no attempted non-banned catalogue programs under ban {d} ({task})")
    top = cat.most_common(2)
    n_nb = sum(c.values())
    clear = (len(top) == 1 or (top[0][1] - top[1][1]) / max(1, n_nb) >= 0.15) and c.most_common(1)[0][0] != "other"
    return top[0][0], clear, dict(c)


def forced_status(task: str, x: str) -> tuple[int, int, int]:
    """(attempts, kept = labelled x, descriptive attempts) over all forced rows of (task, x)."""
    raw = [r for r in read_jsonl(RAW) if r["task"] == task and r["kind"] in ("forced", "forced_desc") and r["X"] == x]
    lab = {r["row_id"]: r for r in labelled_rows()}
    kept = sum(1 for r in raw if lab.get(r["row_id"], {}).get("label") == x)
    return len(raw), kept, sum(1 for r in raw if r["kind"] == "forced_desc")


def selections() -> dict[str, Any]:
    p = RESULTS / "selections.json"
    return json.loads(p.read_text()) if p.exists() else {}


def save_selection(key: str, val: Any) -> None:
    s = selections()
    s[key] = val
    write_json(RESULTS / "selections.json", s)


# ------------------------------------------------------------------------------------------------ phases
def phase_requests(phase: str, limit: int | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if phase == "A1":
        for task in K.TASKS:
            for s in range(5):
                p = K.p_baseline(task, s)
                out += [req(p, phase="A1", sample_id=i, tpl=s) for i in range(20)]
    elif phase == "A2":
        for task in K.TASKS:
            for x in K.MODES[task]:
                for k in range(10):
                    p = K.p_forced(task, x, k)
                    out += [req(p, phase="A2", sample_id=i, tpl=k) for i in range(N_FORCED_ROUND)]
    elif phase == "A3":
        for task in K.TASKS:
            for x in K.MODES[task]:
                p = K.p_free(task, x)
                out += [req(p, phase="A3", sample_id=i, max_tokens=48, tpl=0) for i in range(20)]
    elif phase == "A4":
        for task in K.TASKS:
            d = modal_default(task)
            save_selection(f"{task}_default", d)
            logger.info(f"{task}: sampled default d = {d}")
            for w in K.WS_:
                out += [req(K.p_ban(task, d, w), phase="A4", sample_id=i) for i in range(20)]
                out += [req(K.p_mention(task, d, w), phase="A4", sample_id=i) for i in range(10)]
            for p_ in range(5):
                out += [req(K.p_listall(task, p_), phase="A4", sample_id=i) for i in range(10)]
    elif phase == "A5":
        for task in K.TASKS:
            d = selections()[f"{task}_default"]
            s, clear, counts = realised_substitute(task, d)
            save_selection(f"{task}_substitute", {"s_star": s, "clear_mode": clear, "counts": counts})
            logger.info(f"{task}: realised substitute s* = {s} (clear={clear}) counts={counts}")
            for w in K.WS_:
                out += [req(K.p_twostep(task, d, s, w), phase="A5", sample_id=i) for i in range(10)]
    elif phase == "A6":
        log = []
        for task in K.TASKS:
            for x in K.MODES[task]:
                att, kept, n_desc = forced_status(task, x)
                if kept >= FORCED_TARGET or att >= FORCED_MAX_ATTEMPTS:
                    continue
                desc = att >= DESC_AFTER and kept < DESC_MIN_KEPT
                rnd = att // (10 * N_FORCED_ROUND)  # rounds done so far
                for k in range(10):
                    p = K.p_forced(task, x, k, descriptive=desc)
                    out += [req(p, phase="A6", sample_id=rnd * N_FORCED_ROUND + i, tpl=k) for i in range(N_FORCED_ROUND)]
                log.append({"task": task, "x": x, "attempts": att, "kept": kept, "descriptive": desc, "round": rnd})
        logger.info(f"A6 top-up plan: {log}")
        append_jsonl(LOGS / "forced_topup.jsonl", [{"utc": time.time(), **e} for e in log])
    elif phase == "C":
        for task in K.TASKS:
            bans = selections()[f"{task}_nondefault_bans"]
            for x in bans:
                for w in K.WS_:
                    out += [req(K.p_ban(task, x, w), phase="C", sample_id=i) for i in range(10)]
    else:
        raise ValueError(phase)
    done = {r["row_id"] for r in read_jsonl(RAW)}
    todo = [r for r in out if r["row_id"] not in done]
    logger.info(f"phase {phase}: {len(out)} requests, {len(todo)} not yet generated")
    return todo[:limit] if limit else todo


# ------------------------------------------------------------------------------------------------ client
async def _one(session: aiohttp.ClientSession, sem: asyncio.Semaphore, url: str, r: dict[str, Any],
               keep_lp: bool, sink: list[dict[str, Any]], fh) -> None:
    body = {"model": SERVED, "prompt": r["ids"], **sampling(r["max_tokens"], r["seed"], logprobs=True)}
    async with sem:
        for attempt in range(4):
            try:
                async with session.post(url, json=body, timeout=aiohttp.ClientTimeout(total=900)) as resp:
                    js = await resp.json()
                    if resp.status != 200:
                        raise RuntimeError(f"HTTP {resp.status}: {str(js)[:300]}")
                break
            except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError) as e:
                logger.warning(f"request {r['row_id']} failed (attempt {attempt + 1}): {e}")
                await asyncio.sleep(3 * (attempt + 1))
        else:
            logger.error(f"request {r['row_id']} failed 4 times; skipped")
            return
    ch = js["choices"][0]
    lp = ch.get("logprobs") or {}
    gen_ids = [int(t.split(":", 1)[1]) for t in (lp.get("tokens") or [])]
    row = {k: v for k, v in r.items() if k not in ("ids",)}
    row.update({"model": MODEL_TAG, "decoding": DECODING_FREE if r["max_tokens"] == 48 else DECODING,
                "text": ch["text"], "finish_reason": ch.get("finish_reason"),
                "n_gen_tokens": (js.get("usage") or {}).get("completion_tokens", len(gen_ids)),
                "n_prompt_tokens": len(r["ids"]), "gen_ids": gen_ids})
    if keep_lp:
        row["gen_logprobs"] = lp.get("token_logprobs")
    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    fh.flush()
    sink.append(row)


async def run_requests(reqs: list[dict[str, Any]], port: int, concurrency: int = 48,
                       keep_logprobs_first: int = 0) -> list[dict[str, Any]]:
    url = f"http://127.0.0.1:{port}/v1/completions"
    sem = asyncio.Semaphore(concurrency)
    sink: list[dict[str, Any]] = []
    t0 = time.time()
    async with aiohttp.ClientSession() as session:
        with RAW.open("a") as fh:
            await asyncio.gather(*[_one(session, sem, url, r, i < keep_logprobs_first, sink, fh)
                                   for i, r in enumerate(reqs)])
    dt = time.time() - t0
    ntok = sum(r["n_gen_tokens"] or 0 for r in sink)
    logger.info(f"generated {len(sink)}/{len(reqs)} in {dt:.1f}s ({ntok} tokens, {ntok / max(dt, 1e-9):.0f} tok/s)")
    append_jsonl(LOGS / "timing.jsonl", [{"utc": time.time(), "stage": "vllm", "n": len(sink), "seconds": round(dt, 2),
                                          "gen_tokens": ntok, "per_unit_s": round(dt / max(1, len(sink)), 4)}])
    return sink


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--keep-logprobs-first", type=int, default=0)
    ap.add_argument("--concurrency", type=int, default=48)
    a = ap.parse_args()
    setup_logging(f"gen_{a.phase}")
    port = int((LOGS / "vllm_port.txt").read_text().strip())
    reqs = phase_requests(a.phase, a.limit)
    if reqs:
        asyncio.run(run_requests(reqs, port, a.concurrency, a.keep_logprobs_first))


if __name__ == "__main__":
    main()
