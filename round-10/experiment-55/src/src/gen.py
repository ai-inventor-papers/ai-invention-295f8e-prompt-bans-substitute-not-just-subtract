#!/usr/bin/env python3
"""TP-G2 Stage 1: OpenRouter generation (qwen/qwen3-32b, thinking off) + verification queue (plan 1.1-1.6).

Every call is appended to data/gen_raw_v10.jsonl and every verification to data/programs_v10.jsonl immediately;
every stage resumes from those checkpoints (rows already present are skipped).
Budget: running total of usage.cost (results/costs_v10.json); the whole batch stops at the first HTTP 403 whose
message starts with the AI Inventor budget text (checked after each call gets its semaphore slot) and at a
cumulative USD 0.90 for this artifact.
Stages (CLI): smoke | pilot | main [--deadline-min N] | paraphrase | status
"""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import json
import multiprocessing as mp
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import aiohttp
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cells  # noqa: E402
from common import sha256_text, trunc, utc_now  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA, RESULTS, LOGS = ROOT / "data", ROOT / "results", ROOT / "logs"
RAW = DATA / "gen_raw_v10.jsonl"
PROGS = DATA / "programs_v10.jsonl"
COSTS = RESULTS / "costs_v10.json"
KEYLOG = RESULTS / "openrouter_key_checks.jsonl"
MODEL = "qwen/qwen3-32b"
PIN = {"order": ["DeepInfra"], "allow_fallbacks": False}
PIN_FALLBACKS = [{"order": ["DeepInfra"], "allow_fallbacks": False}, {"order": ["Nebius"], "allow_fallbacks": False},
                 {"order": ["Groq"], "allow_fallbacks": False}]
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
HARD_STOP_USD = 0.90
CONCURRENCY = 16
N_VERIFY_WORKERS = 5
TARGET = 12
FLOOR = 10
CAP_CELL = 48
CAP_TOPUP = 100
WAVE_A_CELL = 12
WAVE_A_TOPUP = 20
for _d in (DATA, RESULTS, LOGS):
    _d.mkdir(parents=True, exist_ok=True)


def append_jsonl(p: Path, row: dict[str, Any]) -> None:
    with p.open("a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        fcntl.flock(fh, fcntl.LOCK_UN)


def read_jsonl(p: Path) -> list[dict[str, Any]]:
    if not p.exists():
        return []
    out = []
    for ln in p.read_text().splitlines():
        ln = ln.strip()
        if ln:
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                logger.warning(f"malformed line in {p.name}")
    return out


def cost_total() -> float:
    return float(json.loads(COSTS.read_text())["total_usd"]) if COSTS.exists() else 0.0


def add_cost(usd: float, purpose: str, refused: bool = False) -> float:
    lock = RESULTS / ".cost_v10.lock"
    with lock.open("w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        c = json.loads(COSTS.read_text()) if COSTS.exists() else {"total_usd": 0.0, "n_calls": 0, "by_purpose": {},
                                                                  "budget_refusals": 0}
        c["total_usd"] = round(c["total_usd"] + float(usd or 0.0), 6)
        c["n_calls"] += 1
        c["by_purpose"][purpose] = round(c["by_purpose"].get(purpose, 0.0) + float(usd or 0.0), 6)
        c["budget_refusals"] += int(refused)
        c["updated_utc"] = utc_now()
        COSTS.write_text(json.dumps(c, indent=1))
        fcntl.flock(lk, fcntl.LOCK_UN)
        return c["total_usd"]


class Stop:
    def __init__(self) -> None:
        self.flag = False
        self.reason = ""

    def set(self, reason: str) -> None:
        if not self.flag:
            logger.error(f"STOP: {reason}")
        self.flag, self.reason = True, self.reason or reason


async def key_check(session: aiohttp.ClientSession, tag: str) -> dict[str, Any]:
    url = os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/key"
    hdr = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}
    try:
        async with session.get(url, headers=hdr, timeout=aiohttp.ClientTimeout(total=30)) as r:
            d = json.loads(await r.text())
    except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as e:
        d = {"error": type(e).__name__}
    data = d.get("data", d)
    row = {"utc": utc_now(), "tag": tag, "limit": data.get("limit"), "usage": data.get("usage"),
           "limit_remaining": data.get("limit_remaining"), "artifact_spend_usd": cost_total()}
    append_jsonl(KEYLOG, row)
    logger.info(f"GET /key [{tag}]: limit={row['limit']} usage={row['usage']} remaining={row['limit_remaining']} "
                f"artifact=${row['artifact_spend_usd']:.4f}")
    return row


async def call(session: aiohttp.ClientSession, sem: asyncio.Semaphore, stop: Stop, job: dict[str, Any],
               purpose: str) -> dict[str, Any] | None:
    """job: uid, messages, seed, meta. Returns the raw row (also appended to RAW) or None."""
    async with sem:
        if stop.flag:
            return None
        if cost_total() >= HARD_STOP_USD:
            stop.set(f"artifact hard stop USD {HARD_STOP_USD} reached")
            return None
        url = os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/chat/completions"
        hdr = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}", "User-Agent": "aii-tpg2/1.0"}
        msgs = [dict(m) for m in job["messages"]]
        msgs[-1]["content"] = msgs[-1]["content"] + " /no_think"
        body = {"model": MODEL, "messages": msgs, "temperature": 1.0, "top_p": 1.0, "max_tokens": 2048,
                "seed": int(job["seed"]), "reasoning": {"enabled": False}, "usage": {"include": True},
                "provider": job.get("pin") or PIN}
        t0 = time.time()
        d = None
        for attempt in range(3):            # 1 try + at most 2 retries
            if stop.flag:
                return None
            try:
                async with session.post(url, json=body, headers=hdr, timeout=aiohttp.ClientTimeout(total=180)) as r:
                    txt = await r.text()
                    if r.status == 403 and BUDGET_MSG in txt:
                        add_cost(0.0, purpose, refused=True)
                        stop.set(f"budget 403: {trunc(txt, 200)}")
                        return None
                    if r.status != 200:
                        logger.warning(f"{job['uid']} HTTP {r.status} (try {attempt}): {trunc(txt, 200)}")
                        await asyncio.sleep(3 * (attempt + 1))
                        continue
                    d = json.loads(txt)
                    if "error" in d and not d.get("choices"):
                        logger.warning(f"{job['uid']} provider error: {trunc(d['error'], 200)}")
                        d = None
                        await asyncio.sleep(3 * (attempt + 1))
                        continue
                    break
            except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as e:
                logger.warning(f"{job['uid']} try {attempt}: {type(e).__name__}")
                await asyncio.sleep(3 * (attempt + 1))
        if d is None:
            row = {**job["meta"], "uid": job["uid"], "failed": True, "utc": utc_now(), "purpose": purpose}
            append_jsonl(RAW, row)
            return row
        usage = d.get("usage") or {}
        cost = float(usage.get("cost") or 0.0)
        tot = add_cost(cost, purpose)
        ch = (d.get("choices") or [{}])[0]
        msg = ch.get("message") or {}
        content = msg.get("content") or ""
        reasoning = msg.get("reasoning") or ""
        if "</think>" in content:
            pre, post = content.split("</think>", 1)
            reasoning = (reasoning + pre.replace("<think>", "")).strip()
            content = post.strip()
        rtok = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
        row = {**job["meta"], "uid": job["uid"], "failed": False, "content": content,
               "reasoning_chars": len(reasoning), "reasoning_tokens": rtok, "provider": d.get("provider"),
               "engine": f"OpenRouter {MODEL} provider={d.get('provider')}", "cost": cost,
               "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
               "finish_reason": ch.get("finish_reason"), "seconds": round(time.time() - t0, 2), "utc": utc_now(),
               "purpose": purpose, "seed": job["seed"]}
        append_jsonl(RAW, row)
        logger.debug(f"{job['uid']} {row['provider']} ${cost:.5f} total ${tot:.4f} rtok={rtok} "
                     f"ctok={row['completion_tokens']} {row['seconds']}s")
        if cost_total() >= HARD_STOP_USD:
            stop.set(f"artifact hard stop USD {HARD_STOP_USD} reached")
        return row


# ---------------------------------------------------------------------------------------------- jobs
def cell_seed(cell: str, slot: int, kind: str) -> int:
    return int(sha256_text(f"{cell}|{slot}|{kind}")[:8], 16) % 2_000_000_000


def initial_job(cell: str, slot: int, wave: str) -> dict[str, Any]:
    p = cells.topup_prompt(cell, slot) if cell in cells.TOPUP_CLASSES else cells.cell_prompt(cell, slot)
    uid = f"{cell}|{wave}|{slot}"
    meta = {k: v for k, v in p.items() if k != "prompt"}
    meta.update({"wave": wave, "repair": False, "source": "generated", "author": "qwen/qwen3-32b",
                 "messages0": p["prompt"]})
    return {"uid": uid, "messages": [{"role": "user", "content": p["prompt"]}], "seed": cell_seed(cell, slot, wave),
            "meta": meta}


def repair_job(raw: dict[str, Any], repair_text: str) -> dict[str, Any]:
    tail = ("Fix the program. Keep exactly the same storage and the same selection rule as required above. Return "
            "only one ```python code block containing the function solve and any helpers, with no example usage "
            "and no explanation.")
    msgs = [{"role": "user", "content": raw["messages0"]}, {"role": "assistant", "content": raw["content"]},
            {"role": "user", "content": repair_text + "\n\n" + tail}]
    meta = {k: v for k, v in raw.items() if k in ("kind", "cell", "discipline", "container", "slot", "wording",
                                                   "heur_key", "prompt_id", "prompt_sha256", "wave", "source",
                                                   "author", "messages0")}
    meta.update({"repair": True, "repair_of": raw["uid"], "repair_text": repair_text})
    return {"uid": raw["uid"] + "|r", "messages": msgs, "seed": cell_seed(raw["cell"], raw["slot"], "repair"),
            "meta": meta}


def paraphrase_job(cell: str, k: int, seed_code: str, seed_uid: str, seed_kind: str) -> dict[str, Any]:
    spec = cells.spec_text()
    text = ("Here is a Python program that solves the task below.\n\n```python\n" + seed_code.rstrip() + "\n```\n\n"
            "Rewrite it from scratch with different names, a different helper structure and different comments, "
            "keeping exactly the same search procedure: the same storage, the same selection rule, the same "
            "marking and the same stopping rule.\n\n" + spec)
    uid = f"{cell}|para|{k}"
    meta = {"kind": "paraphrase", "cell": cell, "discipline": cell.split("-")[0] if "-" in cell else cell,
            "container": cell.split("-")[1] if "-" in cell else None, "slot": 1000 + k, "wording": "PARA",
            "heur_key": None, "prompt_id": f"{cell}|PARA", "prompt_sha256": sha256_text(text), "wave": "para",
            "repair": False, "source": "paraphrase", "paraphrase_of": seed_uid, "paraphrase_seed_kind": seed_kind,
            "author": "qwen/qwen3-32b", "messages0": text}
    return {"uid": uid, "messages": [{"role": "user", "content": text}], "seed": cell_seed(cell, k, "para"),
            "meta": meta}


# ---------------------------------------------------------------------------------------------- verification
def _verify_worker(item: tuple[str, str | None, str]) -> tuple[str, dict[str, Any]]:
    os.environ.setdefault("PYTHONHASHSEED", "0")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import verify

    return verify.worker(item)


def extract_code(content: str | None) -> str | None:
    import label_tp

    code, _how = label_tp.extract_last_fence(content)
    return code


def prog_row(raw: dict[str, Any], v: dict[str, Any], code: str | None) -> dict[str, Any]:
    keep = ("uid", "kind", "cell", "discipline", "container", "slot", "wording", "heur_key", "prompt_id",
            "prompt_sha256", "wave", "repair", "repair_of", "source", "paraphrase_of", "paraphrase_seed_kind",
            "author", "provider", "engine", "cost", "seed", "utc")
    row = {k: raw.get(k) for k in keep}
    row.update({"raw_code": code, "code_sha256": sha256_text(code) if code else None,
                "scrubbed_code": v.get("scrubbed_code"),
                "scrubbed_sha256": sha256_text(v["scrubbed_code"]) if v.get("scrubbed_code") else None,
                "scrub_map": (v.get("scrub") or {}).get("scrub_map"), "suite48": v.get("suite48"),
                "suite41": v.get("suite41"), "suite48_detail": v.get("suite48_detail"),
                "suite41_detail": v.get("suite41_detail"), "tracer": v.get("tracer"), "ast": v.get("ast"),
                "container_check": v.get("container_check"), "discipline_check": v.get("discipline_check"),
                "topup_check": v.get("topup_check"), "scrub": v.get("scrub"), "verdict": v.get("verdict"),
                "reasons": v.get("reasons"), "needs_hand_read": v.get("needs_hand_read"),
                "repair_text": v.get("repair_text"), "verified_utc": utc_now(), "pilot": raw.get("wave") == "pilot"})
    return row


# ---------------------------------------------------------------------------------------------- counting
def counts(rows: list[dict[str, Any]], include_hand: bool = True) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for r in rows:
        if r.get("pilot"):
            continue
        c = out.setdefault(r["cell"], {"accept": 0, "hand": 0, "reject": 0, "attempts_initial": 0, "para": 0})
        if r["verdict"] == "ACCEPT":
            c["accept"] += 1
        elif r["verdict"] == "HAND":
            c["hand"] += 1
        else:
            c["reject"] += 1
        if r.get("source") == "paraphrase" and r["verdict"] in ("ACCEPT", "HAND"):
            c["para"] += 1
    return out


def hand_verdicts() -> dict[str, str]:
    return {r["uid"]: r["verdict"] for r in read_jsonl(DATA / "hand_reads_v10.jsonl")}


def verified_count(c: dict[str, int], cell: str, hv_cell_reject: int = 0) -> int:
    return c.get("accept", 0) + c.get("hand", 0) - hv_cell_reject


# ---------------------------------------------------------------------------------------------- driver
class Driver:
    def __init__(self, purpose: str, deadline: float | None) -> None:
        self.purpose = purpose
        self.deadline = deadline
        self.stop = Stop()
        self.sem = asyncio.Semaphore(CONCURRENCY)
        self.loop = asyncio.get_event_loop()
        self.pool = ProcessPoolExecutor(max_workers=N_VERIFY_WORKERS, mp_context=mp.get_context("spawn"))
        self.raw_done = {r["uid"]: r for r in read_jsonl(RAW)}
        self.prog_done = {r["uid"]: r for r in read_jsonl(PROGS)}
        self.inflight: set[str] = set()
        self.t0 = time.time()

    async def verify_raw(self, raw: dict[str, Any]) -> dict[str, Any] | None:
        if raw.get("failed"):
            return None
        if raw["uid"] in self.prog_done:
            return self.prog_done[raw["uid"]]
        code = extract_code(raw.get("content"))
        uid, v = await self.loop.run_in_executor(self.pool, _verify_worker, (raw["uid"], code, raw["cell"]))
        row = prog_row(raw, v, code)
        append_jsonl(PROGS, row)
        self.prog_done[uid] = row
        logger.info(f"verified {uid}: {row['verdict']} {row['reasons']} "
                    f"[{(row.get('discipline_check') or {}).get('tracer_class')}]")
        return row

    async def one(self, session: aiohttp.ClientSession, job: dict[str, Any], allow_repair: bool = True) -> None:
        if job["uid"] in self.inflight:
            return
        self.inflight.add(job["uid"])
        try:
            raw = self.raw_done.get(job["uid"])
            if raw is None:
                if self.deadline and time.time() > self.deadline:
                    return
                raw = await call(session, self.sem, self.stop, job, self.purpose)
                if raw is None:
                    return
                self.raw_done[raw["uid"]] = raw
            row = await self.verify_raw(raw)
            if row is None or not allow_repair or raw.get("repair") or self.stop.flag:
                return
            if "fails_suites" in (row.get("reasons") or []) and row.get("repair_text") and raw.get("content"):
                await self.one(session, repair_job(raw, row["repair_text"]), allow_repair=False)
        finally:
            self.inflight.discard(job["uid"])

    async def run_jobs(self, session: aiohttp.ClientSession, jobs: list[dict[str, Any]]) -> None:
        tasks = [asyncio.create_task(self.one(session, j)) for j in jobs]
        done = 0
        for f in asyncio.as_completed(tasks):
            try:
                await f
            except Exception as e:  # noqa: BLE001 - one job must not stop the batch
                logger.error(f"job exception {type(e).__name__}: {e}")
            done += 1
            if done % 20 == 0 or done == len(tasks):
                logger.info(f"[{self.purpose}] {done}/{len(tasks)} jobs, {time.time() - self.t0:.0f}s, "
                            f"spend ${cost_total():.4f}")
            if self.stop.flag:
                for t in tasks:
                    t.cancel()
                break
        write_status()


def write_status() -> None:
    rows = read_jsonl(PROGS)
    raws = read_jsonl(RAW)
    st = {"utc": utc_now(), "spend_usd": cost_total(), "n_raw": len(raws), "n_verified": len(rows),
          "counts": counts(rows), "pilot": counts([{**r, "pilot": False} for r in rows if r.get("pilot")]),
          "hand_reads": len(hand_verdicts())}
    (RESULTS / "partial_status.json").write_text(json.dumps(st, indent=1))


async def stage_smoke() -> None:
    async with aiohttp.ClientSession() as session:
        await key_check(session, "smoke")
        d = Driver("smoke", None)
        jobs = [initial_job("BFSO-DEQUE", 900, "smoke"), initial_job("COST-HEAP", 901, "smoke")]
        await d.run_jobs(session, jobs)
        for j in jobs:
            r = d.raw_done.get(j["uid"])
            if r:
                logger.info(f"SMOKE {j['uid']}: provider={r.get('provider')} rtok={r.get('reasoning_tokens')} "
                            f"reasoning_chars={r.get('reasoning_chars')} cost={r.get('cost')} "
                            f"fin={r.get('finish_reason')} ctok={r.get('completion_tokens')}")
        d.pool.shutdown()


async def stage_pilot() -> None:
    async with aiohttp.ClientSession() as session:
        await key_check(session, "pilot")
        d = Driver("pilot", None)
        jobs = [initial_job(c, s, "pilot") for c in cells.all_cells() for s in range(3)]
        await d.run_jobs(session, jobs)
        d.pool.shutdown()


def needed(rows: list[dict[str, Any]], target: int) -> dict[str, int]:
    cnt = counts(rows)
    hv = hand_verdicts()
    rej = {}
    for r in rows:
        if hv.get(r["uid"]) == "REJECT" and r["verdict"] == "HAND" and not r.get("pilot"):
            rej[r["cell"]] = rej.get(r["cell"], 0) + 1
    out = {}
    for c in cells.all_cells() + cells.TOPUP_CLASSES:
        v = verified_count(cnt.get(c, {}), c, rej.get(c, 0))
        out[c] = max(0, target - v)
    return out


def attempts(cell: str, raws: dict[str, dict[str, Any]]) -> int:
    return sum(1 for u, r in raws.items() if r.get("cell") == cell and not r.get("repair") and
               r.get("wave") in ("A", "B"))


async def stage_main(deadline_min: float, committed: list[str]) -> None:
    deadline = time.time() + deadline_min * 60
    async with aiohttp.ClientSession() as session:
        await key_check(session, "waveA")
        d = Driver("main", deadline)
        jobs = [initial_job(c, s, "A") for c in committed for s in range(WAVE_A_CELL)]
        jobs += [initial_job(c, s, "A") for c in cells.TOPUP_CLASSES for s in range(WAVE_A_TOPUP)]
        await d.run_jobs(session, jobs)
        rows = list(d.prog_done.values())
        cnt = counts(rows)
        logger.info("WAVE A yields: " + json.dumps({c: cnt.get(c) for c in committed + cells.TOPUP_CLASSES}))
        (RESULTS / "waveA_yield.json").write_text(json.dumps({"utc": utc_now(), "counts": cnt,
                                                              "spend_usd": cost_total()}, indent=1))
        rnd = 0
        while not d.stop.flag and time.time() < deadline:
            rnd += 1
            await key_check(session, f"waveB{rnd}")
            need = needed(list(d.prog_done.values()), TARGET)
            jobs = []
            for c in committed + cells.TOPUP_CLASSES:
                n_att = attempts(c, d.raw_done)
                cap = CAP_TOPUP if c in cells.TOPUP_CLASSES else CAP_CELL
                if need.get(c, 0) <= 0 or n_att >= cap:
                    continue
                yld = _yield(c, list(d.prog_done.values()))
                k = min(cap - n_att, max(2, int(need[c] / max(yld, 0.15) + 0.999)))
                k = min(k, 24)
                jobs += [initial_job(c, s, "B") for s in range(n_att, n_att + k)]
            if not jobs:
                logger.info(f"wave B round {rnd}: nothing to do")
                break
            logger.info(f"wave B round {rnd}: {len(jobs)} jobs over {len({j['meta']['cell'] for j in jobs})} cells")
            await d.run_jobs(session, jobs)
        d.pool.shutdown()
    write_status()


def _yield(cell: str, rows: list[dict[str, Any]]) -> float:
    rs = [r for r in rows if r["cell"] == cell and not r.get("pilot") and not r.get("repair")]
    if not rs:
        return 0.3
    ok = sum(1 for r in rows if r["cell"] == cell and not r.get("pilot") and r["verdict"] in ("ACCEPT", "HAND"))
    return ok / len(rs)


async def stage_paraphrase(committed: list[str], deadline_min: float) -> None:
    """Fallback F1: cells / classes below FLOOR get paraphrases of verified same-cell programs (or of the S3
    reference for top-ups), at most 50% of the cell."""
    deadline = time.time() + deadline_min * 60
    rows = read_jsonl(PROGS)
    hv = hand_verdicts()
    need = needed(rows, TARGET)
    jobs = []
    ref_dir = ROOT / "vendor/exp9/tasks/t1_grid/references"
    ref_of = {"bibfs": ["bibfs_deques.py", "bibfs_sets.py"], "iddfs": ["iddfs_recursive.py", "iddfs_iterative.py"],
              "jps": ["jps4.py"], "biastar": ["biastar.py"]}
    for c in committed + cells.TOPUP_CLASSES:
        if need.get(c, 0) <= 0:
            continue
        ok = [r for r in rows if r["cell"] == c and not r.get("pilot") and r["source"] == "generated" and
              (r["verdict"] == "ACCEPT" or (r["verdict"] == "HAND" and hv.get(r["uid"]) == "ACCEPT"))]
        n_par = min(need[c] + 2, max(2, TARGET // 2))
        if c in cells.TOPUP_CLASSES:          # S3-seeded top-ups: no 50% cap (deviation D-topup-paraphrase)
            n_par = min(need[c] + 4, 16)
        seeds = [(r["raw_code"], r["uid"], "verified_same_cell") for r in ok]
        if not seeds and c in ref_of:
            seeds = [((ref_dir / f).read_text(), f"S3:{f}", "S3_reference") for f in ref_of[c]]
        if not seeds:
            planted = ROOT / "tests" / "planted" / f"{c}.py"
            if planted.exists():
                seeds = [(planted.read_text(), f"planted:{c}", "executor_planted")]
        if not seeds:
            continue
        for k in range(n_par):
            code, su, kind = seeds[k % len(seeds)]
            jobs.append(paraphrase_job(c, k, code, su, kind))
    logger.info(f"paraphrase fallback: {len(jobs)} jobs")
    async with aiohttp.ClientSession() as session:
        await key_check(session, "paraphrase")
        d = Driver("paraphrase", deadline)
        await d.run_jobs(session, jobs)
        d.pool.shutdown()
    write_status()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["smoke", "pilot", "main", "paraphrase", "status"])
    ap.add_argument("--deadline-min", type=float, default=90.0)
    a = ap.parse_args()
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(LOGS / f"gen_{a.stage}.log"), rotation="30 MB", level="DEBUG")
    committed = cells.all_cells()
    cf = ROOT / "predictions" / "commit1.json"
    if cf.exists():
        committed = json.loads(cf.read_text())["committed_cells"]
    if a.stage == "smoke":
        asyncio.run(stage_smoke())
    elif a.stage == "pilot":
        asyncio.run(stage_pilot())
    elif a.stage == "main":
        assert cf.exists(), "wave A requires COMMIT #1"
        asyncio.run(stage_main(a.deadline_min, committed))
    elif a.stage == "paraphrase":
        asyncio.run(stage_paraphrase(committed, a.deadline_min))
    write_status()
    print(json.dumps(json.loads((RESULTS / "partial_status.json").read_text())["counts"], indent=0)[:3000])


if __name__ == "__main__":
    main()
