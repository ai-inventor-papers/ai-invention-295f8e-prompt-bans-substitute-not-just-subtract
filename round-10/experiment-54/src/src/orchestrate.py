#!/usr/bin/env python3
"""S8 sampling orchestrator (one asyncio process).

(1) BASE (50 per model; a 10-call stage, then 40) for q8 (local vLLM), q32 and q14 (OpenRouter), with the naming
    checks (thinking off) in parallel.
(2) When a model's BASE rows are evaluated (evalq.py): frequency order -> B_1..B_5, S_desc -> COMMIT #2_<model>.
(3) Ban / described / held-out / instruction cells. q8 runs all its cells locally (concurrency 32). OpenRouter calls go
    through one priority queue served by a fixed number of workers. Priority = (tier, group, position, cell):
    tier 0 = decisive cells (NAME_1..5, DESC_5, HOLD_5) at ladder positions 0-29 (10/10/10 and 15/15 slots);
    tier 1 = INSTR cells (N 30); tier 2 = decisive positions 30-39 (N 40); tier 3 = positions 40-49 (N 50).
    Group order: q32 NAME+DESC, q14 NAME+DESC, HOLD_5 q32, HOLD_5 q14, INSTR q32, INSTR q14. Positions interleave
    templates, so a time cut leaves every cell balanced across templates and the reduction ladder N 50 -> 40 -> 30
    is applied before any INSTR row is dropped.
A hard stop time ends the starting of new requests; the first budget 403 stops everything (sample_or.Stop).
"""
from __future__ import annotations

import asyncio
import fcntl
import os
import time
from collections import Counter
from typing import Any

import aiohttp
from loguru import logger

import analysis
import extract
import lexical
import prompts
import sample_local
import sample_or
from common import (DATA, PRED, RESULTS, append_jsonl, commit, commit_time, deviation, read_json, elapsed_h, milestone, partial_status,
                    read_jsonl, sha256_text, setup_logging, start_epoch, total_cost, write_json)

OR_MODELS = ["q32", "q14"]
STOP_NEW_OR_H = float(os.environ.get("NOVR_STOP_OR_H", "4.57"))      # no new OpenRouter request after this
STOP_NEW_LOCAL_H = float(os.environ.get("NOVR_STOP_LOCAL_H", "4.70"))
OR_WORKERS = int(os.environ.get("NOVR_OR_WORKERS", "12"))
BASE_N = 50
DECISIVE = ["NAME_1", "NAME_2", "NAME_3", "NAME_4", "NAME_5", "DESC_5", "HOLD_5"]
INSTR_CELLS = ["INSTR_NEW", "INSTR_LONG"]
CELL_RANK = {c: i for i, c in enumerate(["NAME_1", "NAME_2", "NAME_3", "NAME_4", "NAME_5", "DESC_5", "HOLD_5",
                                         "INSTR_NEW", "INSTR_LONG"])}


def raw_path(mk: str):
    return DATA / f"samples_raw_{mk}.jsonl"


def naming_path(mk: str):
    return DATA / f"naming_raw_{mk}.jsonl"


def interleaved_positions(cell: str) -> list[int]:
    """Slots of a 50-slot cell in priority order: the N=30 ladder slots interleaved by template, then the N=40
    additions, then the rest."""
    kind = prompts.CELLS[cell][1]
    if kind in ("base", "instr"):
        return list(range(50))
    s30 = prompts.slots_for(cell, 30)
    s40 = [s for s in prompts.slots_for(cell, 40) if s not in s30]
    s50 = [s for s in prompts.slots_for(cell, 50) if s not in s30 and s not in s40]

    def inter(slots: list[int]) -> list[int]:
        by: dict[str, list[int]] = {}
        for s in slots:
            by.setdefault(prompts.template_for(cell, s, 50), []).append(s)
        out, i = [], 0
        keys = sorted(by)
        while any(i < len(by[k]) for k in keys):
            for k in keys:
                if i < len(by[k]):
                    out.append(by[k][i])
            i += 1
        return out
    return inter(s30) + inter(s40) + inter(s50)


def or_priority(mk: str, cell: str, pos: int) -> tuple[int, int, int, int]:
    if cell in INSTR_CELLS:
        tier = 1
        group = 4 + OR_MODELS.index(mk)
    else:
        tier = 0 if pos < 30 else (2 if pos < 40 else 3)
        group = (0 if mk == "q32" else 1) if cell != "HOLD_5" else (2 if mk == "q32" else 3)
    return (tier, group, pos, CELL_RANK[cell])


def single_instance(name: str):
    """Hold an exclusive non-blocking lock on predictions/.<name>.lock for the life of the process. Two orchestrators
    ran at once before the container crash (a killed shell wrapper left its Python child alive): they wrote 5 duplicate
    rows and overwrote two commit #2 payload files after their hashes were logged."""
    fh = (PRED / f".{name}.lock").open("w")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit(f"another {name} process holds predictions/.{name}.lock")
    fh.write(str(os.getpid()))
    fh.flush()
    return fh


class Orchestrator:
    def __init__(self, models: list[str]) -> None:
        self.models = models
        self.stop = sample_or.Stop()
        self.q: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.counter = 0
        self.big_sem = asyncio.Semaphore(10_000)
        self.url = os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/chat/completions"
        self.t_or: list[float] = []

    def stop_time(self, h: float) -> float:
        return start_epoch() + h * 3600.0

    # -------------------------------------------------------------------------------------- OpenRouter workers
    async def or_worker(self, session: aiohttp.ClientSession, wid: int) -> None:
        while True:
            prio, _, item, fut = await self.q.get()
            try:
                if self.stop.flag or time.time() > self.stop_time(STOP_NEW_OR_H) or total_cost() >= 4.5:
                    fut.set_result(None)
                    continue
                thinking = item.pop("_thinking", True)
                max_tokens = item.pop("_max_tokens", sample_or.MAX_TOKENS)
                out = item.pop("_out")
                r = await sample_or.call_one(session, self.big_sem, self.stop, item, out, item.get("_purpose", "or"),
                                             self.url, thinking=thinking, max_tokens=max_tokens)
                if r is not None and thinking:
                    self.t_or.append(float(r.get("gen_seconds") or 0))
                fut.set_result(r)
            except Exception as e:  # noqa: BLE001
                logger.error(f"or_worker {wid}: {e!r}")
                if not fut.done():
                    fut.set_result(None)
            finally:
                self.q.task_done()

    def enqueue(self, prio: tuple, item: dict[str, Any]) -> asyncio.Future:
        self.counter += 1
        fut = asyncio.get_event_loop().create_future()
        self.q.put_nowait((prio, self.counter, item, fut))
        return fut

    # -------------------------------------------------------------------------------------- items
    def base_items(self, mk: str) -> list[dict[str, Any]]:
        out = []
        for s in range(BASE_N):
            r = prompts.render("BASE", s, [])
            out.append({"model_key": mk, **r})
        return out

    def done_keys(self, mk: str) -> set:
        return {(r["cell"], int(r["slot"])) for r in read_jsonl(raw_path(mk))}

    async def run_local(self, items: list[dict[str, Any]], label: str) -> dict[str, Any]:
        items = [it for it in items if time.time() < self.stop_time(STOP_NEW_LOCAL_H)]
        t0 = time.time()
        r = await sample_local.run_items(items, lambda it: raw_path("q8"), concurrency=32)
        self.throughput("q8", label, r["n_tasks"], time.time() - t0)
        return r

    def throughput(self, mk: str, label: str, n: int, secs: float) -> None:
        append_jsonl(RESULTS / "throughput.jsonl", {"model": mk, "stage": label, "n_calls": n,
                                                     "seconds": round(secs, 1),
                                                     "sec_per_call_wall": round(secs / max(n, 1), 2),
                                                     "elapsed_h": round(elapsed_h(), 3), "spend": total_cost()})

    async def run_or_batch(self, mk: str, items: list[dict[str, Any]], prio: tuple, label: str,
                           thinking: bool = True, max_tokens: int = sample_or.MAX_TOKENS,
                           out_path=None, keyf=None) -> list[Any]:
        out_path = out_path or raw_path(mk)
        keyf = keyf or (lambda r: (r.get("cell"), int(r.get("slot"))))
        have = {keyf(r) for r in read_jsonl(out_path)}
        futs = []
        t0 = time.time()
        for it in items:
            if keyf(it) in have:
                continue
            futs.append(self.enqueue(prio, {**it, "_out": out_path, "_thinking": thinking,
                                            "_max_tokens": max_tokens, "_purpose": f"{mk}:{label}"}))
        res = await asyncio.gather(*futs)
        self.throughput(mk, label, len(futs), time.time() - t0)
        return res

    # -------------------------------------------------------------------------------------- naming checks
    async def naming(self, mk: str) -> dict[str, Any]:
        out: dict[str, Any] = {}

        async def run_version(rule: str, v: int) -> tuple[int, list[str], bool]:
            desc = prompts.DESCRIPTIONS[rule][v]
            q = prompts.NAMING_PROMPT.format(description=desc)
            # OpenRouter (DeepInfra) still emits reasoning with reasoning disabled, so the plan's fallback applies:
            # ' /no_think' is appended and the cap is 1,024 tokens (logged deviation NAMING_NOTHINK).
            items = [{"model_key": mk, "cell": f"NAMING:{rule}:{v}", "slot": i,
                      "seed": 900000 + 100 * list(prompts.DESCRIPTIONS).index(rule) + 20 * v + i + 1,
                      "prompt": q, "rule": rule, "version": v, "no_think_suffix": mk != "q8"}
                     for i in range(prompts.NAMING_N)]
            if mk == "q8":
                await sample_local.run_items(items, lambda it: naming_path(mk), concurrency=20, max_tokens=64)
            else:
                await self.run_or_batch(mk, items, (-1, 0, 0, 0), "naming", thinking=False, max_tokens=1024,
                                        out_path=naming_path(mk))
            rows = [r for r in read_jsonl(naming_path(mk)) if r.get("cell") == f"NAMING:{rule}:{v}"]
            replies = [r.get("content") or "" for r in rows]
            think_seen = any((r.get("reasoning_tokens") or 0) > 0 or (r.get("reasoning") or "").strip() for r in rows)
            replies = [extract.visible_only(t) for t in replies]
            correct = sum(1 for t in replies if lexical.rules_hit(t) == {rule})
            return correct, replies, think_seen

        async def one_rule(rule: str) -> None:
            rec = {"versions": []}
            for v in range(3):
                c, replies, think_seen = await run_version(rule, v)
                rec["versions"].append({"version": v, "correct": c, "n": len(replies), "replies_head":
                                        [x[:60] for x in replies[:20]], "reasoning_seen": think_seen})
                if think_seen and mk != "q8":
                    deviation(f"NAMING_THINK_{mk}", f"reasoning appeared in naming replies of {mk} despite "
                                                    f"reasoning disabled (recorded per version)")
                if c >= prompts.NAMING_PASS:
                    rec["passed"] = True
                    rec["version_used"] = v
                    rec["text"] = prompts.DESCRIPTIONS[rule][v]
                    break
            else:
                rec["passed"] = False
                rec["best_rate"] = max(x["correct"] for x in rec["versions"]) / prompts.NAMING_N
            out[rule] = rec
        await asyncio.gather(*[one_rule(r) for r in prompts.DESCRIPTIONS])
        return out

    # -------------------------------------------------------------------------------------- per model
    async def wait_base_evaluated(self, mk: str, timeout_s: float = 1500.0) -> list[dict[str, Any]]:
        t0 = time.time()
        while True:
            n_raw = sum(1 for r in read_jsonl(raw_path(mk)) if r["cell"] == "BASE")
            rows = [r for r in analysis.load_rows() if r.get("model") == mk and r.get("cell") == "BASE"
                    and "label" in r]
            if n_raw >= BASE_N and len(rows) >= n_raw:
                return rows
            if time.time() - t0 > timeout_s:
                deviation(f"BASE_EVAL_TIMEOUT_{mk}", f"order computed on {len(rows)} of {n_raw} BASE rows after "
                                                      f"{timeout_s:.0f} s")
                return rows
            await asyncio.sleep(10)

    async def model_pipeline(self, mk: str, session: aiohttp.ClientSession) -> None:
        try:
            if commit_time(f"commit2_{mk}"):
                payload = read_json(PRED / f"commit2_{mk}.json")
                if mk in OR_MODELS:
                    await self.resume_or(mk, payload)
                else:
                    await self.ban_cells(mk, payload)
                milestone(f"sampling_done_{mk}")
                return
            base = self.base_items(mk)
            if mk == "q8":
                naming_task = asyncio.create_task(self.naming(mk))
                await self.run_local(base[:10], "BASE_10")
                await self.run_local(base[10:], "BASE_40")
            else:
                naming_task = asyncio.create_task(self.naming(mk))
                await self.run_or_batch(mk, base[:10], (-2, 0, 0, 0), "BASE_10")
                await self.run_or_batch(mk, base[10:], (-2, 0, 0, 0), "BASE_40")
            milestone(f"BASE_sampled_{mk}")
            nm = await naming_task
            write_json(RESULTS / f"naming_checks_{mk}.json", nm)
            rows = await self.wait_base_evaluated(mk)
            order = analysis.frequency_order(rows)
            b5 = order["B"][5]
            s_desc = [r for r in b5 if nm.get(r, {}).get("passed")]
            desc_text = {r: nm[r]["text"] for r in s_desc}
            rendered = {}
            n_dec = 50 if mk == "q8" else 50
            for cell in DECISIVE + INSTR_CELLS:
                k = prompts.CELLS[cell][2]
                banned = order["B"][k] if cell.startswith("NAME_") else b5
                n_cell = 50 if (mk == "q8" or cell not in INSTR_CELLS) else 30
                if cell == "DESC_5" and not s_desc:
                    continue
                for s in prompts.slots_for(cell, n_cell):
                    r = prompts.render(cell, s, banned, s_desc, desc_text)
                    rendered[f"{cell}|{s}"] = r["prompt_sha256"]
            payload = {"model": mk, "label": f"commit2_{mk}", "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                                                   time.gmtime()),
                       "order": order["order"], "counts": order["counts"], "other": order["other"],
                       "n_valid_base": order["n_valid"], "n_base": order["n"], "all_fallback": order["all_fallback"],
                       "B": {str(k): v for k, v in order["B"].items()}, "S_desc": s_desc, "desc_text": desc_text,
                       "naming": {r: {"passed": v.get("passed"), "version_used": v.get("version_used"),
                                      "rates": [x["correct"] / max(1, x["n"]) for x in v["versions"]]}
                                  for r, v in nm.items()},
                       "rendered_prompt_sha256": rendered, "n_decisive_planned": n_dec,
                       "or_priority_rule": __doc__.split("(3)")[1].split("A hard stop")[0].strip()}
            p = PRED / f"commit2_{mk}.json"
            write_json(p, payload)
            commit(p, f"commit2_{mk}", f"frequency order {order['order']}; S_desc {s_desc}")
            milestone(f"commit2_{mk}", order=order["order"], s_desc=s_desc)
            await self.ban_cells(mk, payload)
            milestone(f"sampling_done_{mk}")
        except Exception as e:  # noqa: BLE001
            logger.exception(f"pipeline {mk} failed: {e!r}")
            partial_status({f"pipeline_error_{mk}": repr(e)[:300]})

    async def naming_clean(self, mk: str) -> dict[str, Any]:
        """Crash-recovery rerun of the naming check (OpenRouter models): every version of every description, 20 queries
        each, into data/naming_raw_<mk>_clean.jsonl with ' /no_think' and 1,024 tokens, visible content only. The
        first naming files mixed empty 96-token replies of the duplicate orchestrator with genuine ones (and skipped
        genuine slots), so they cannot be scored. Pass rule unchanged: the first version (primary, rewrite 1,
        rewrite 2) with >= 16 of 20 correct replies."""
        path = DATA / f"naming_raw_{mk}_clean.jsonl"
        items = []
        for rule in prompts.DESCRIPTIONS:
            for v in range(3):
                q = prompts.NAMING_PROMPT.format(description=prompts.DESCRIPTIONS[rule][v])
                for i in range(prompts.NAMING_N):
                    items.append({"model_key": mk, "cell": f"NAMING:{rule}:{v}", "slot": i,
                                  "seed": 900000 + 100 * list(prompts.DESCRIPTIONS).index(rule) + 20 * v + i + 1,
                                  "prompt": q, "rule": rule, "version": v, "no_think_suffix": True})
        await self.run_or_batch(mk, items, (-1, 0, 0, 0), "naming_clean", thinking=False, max_tokens=1024,
                                out_path=path)
        first: dict[tuple, dict[str, Any]] = {}
        for r in read_jsonl(path):
            first.setdefault((r["cell"], int(r["slot"])), r)
        out: dict[str, Any] = {}
        for rule in prompts.DESCRIPTIONS:
            rec: dict[str, Any] = {"versions": []}
            for v in range(3):
                rs = [first[k] for k in sorted(first) if k[0] == f"NAMING:{rule}:{v}"]
                replies = [extract.visible_only(r.get("content") or "") for r in rs]
                correct = sum(1 for t in replies if lexical.rules_hit(t) == {rule})
                rec["versions"].append({"version": v, "correct": correct, "n": len(replies),
                                        "empty": sum(1 for t in replies if not t.strip()),
                                        "reasoning_seen": any((r.get("reasoning_tokens") or 0) > 0 for r in rs),
                                        "replies_head": [t.strip()[:60] for t in replies]})
            used = next((x["version"] for x in rec["versions"] if x["correct"] >= prompts.NAMING_PASS), None)
            rec["passed"] = used is not None
            if used is not None:
                rec["version_used"] = used
                rec["text"] = prompts.DESCRIPTIONS[rule][used]
            rec["best_rate"] = max(x["correct"] for x in rec["versions"]) / prompts.NAMING_N
            out[rule] = rec
        write_json(RESULTS / f"naming_checks_{mk}_clean.json", out)
        return out

    async def resume_or(self, mk: str, payload: dict[str, Any]) -> None:
        """Restart after the container crash. B_1..B_5 are identical in every commit-#2 version (fallback order after
        BF), so NAME/HOLD/INSTR cells resume at once. The clean naming rerun then fixes S_desc in COMMIT #3_<mk>,
        written before any DESC_5 row it governs: q32 has no DESC_5 row yet (commit2_q32 was committed with S_desc []
        from empty replies); q14's 30 DESC_5 rows were sampled under commit2_q14 (FF rewrite 1), and that cell keeps
        its text, so commit3_q14 is a record only."""
        main = asyncio.create_task(self.ban_cells(mk, payload, skip_desc=(mk == "q32")))
        nm = await self.naming_clean(mk)
        b5 = list(payload["B"]["5"])
        s_clean = [r for r in b5 if nm[r]["passed"]]
        d_clean = {r: nm[r]["text"] for r in s_clean}
        rendered = {}
        if mk == "q32" and s_clean:
            for s in prompts.slots_for("DESC_5", 50):
                rendered[f"DESC_5|{s}"] = prompts.render("DESC_5", s, b5, s_clean, d_clean)["prompt_sha256"]
        p3 = PRED / f"commit3_{mk}.json"
        payload3 = {"model": mk, "label": f"commit3_{mk}", "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "amends": f"commit2_{mk}", "B": payload["B"], "order": payload["order"],
                    "S_desc_clean": s_clean, "desc_text_clean": d_clean,
                    "governs": ("DESC_5 of q32 (all of its rows)" if mk == "q32" else
                                "nothing: q14 DESC_5 keeps the text of its first 30 rows (commit2_q14)"),
                    "S_desc_used_for_DESC_5": s_clean if mk == "q32" else list(payload["S_desc"]),
                    "desc_text_used_for_DESC_5": d_clean if mk == "q32" else dict(payload["desc_text"]),
                    "naming_clean": {r: {"passed": v["passed"], "version_used": v.get("version_used"),
                                         "rates": [x["correct"] / prompts.NAMING_N for x in v["versions"]],
                                         "empty": [x["empty"] for x in v["versions"]]} for r, v in nm.items()},
                    "rendered_prompt_sha256": rendered,
                    "why": "container crash; duplicate orchestrator contaminated the first naming files and overwrote "
                           "the commit #2 payload files of q14 and q32 after their hashes were logged"}
        write_json(p3, payload3)
        commit(p3, f"commit3_{mk}", f"clean naming rerun; S_desc_clean {s_clean}")
        milestone(f"commit3_{mk}", s_desc_clean=s_clean)
        if mk == "q32":
            if s_clean:
                await self.ban_cells(mk, {**payload, "S_desc": s_clean, "desc_text": d_clean}, only=["DESC_5"])
            else:
                deviation(f"DESC_SKIPPED_{mk}", "no description of B_5 passed the clean naming check")
        await main

    async def ban_cells(self, mk: str, payload: dict[str, Any], skip_desc: bool = False,
                        only: list[str] | None = None) -> None:
        if True:
            order = {"B": {int(k): v for k, v in payload["B"].items()}}
            b5 = order["B"][5]
            s_desc = list(payload["S_desc"])
            desc_text = dict(payload["desc_text"])
            items = []
            for cell in DECISIVE + INSTR_CELLS:
                if (only and cell not in only) or (skip_desc and cell == "DESC_5"):
                    continue
                if cell == "DESC_5" and not s_desc:
                    deviation(f"DESC_SKIPPED_{mk}", "no description of B_5 passed the naming check")
                    continue
                k = prompts.CELLS[cell][2]
                banned = order["B"][k] if cell.startswith("NAME_") else b5
                for pos, s in enumerate(interleaved_positions(cell)):
                    if mk != "q8" and cell in INSTR_CELLS and s >= 30:
                        continue
                    r = prompts.render(cell, s, banned, s_desc, desc_text)
                    items.append((pos, cell, {"model_key": mk, **r}))
            if mk == "q8":
                items.sort(key=lambda x: (x[0], CELL_RANK[x[1]]))
                its = [x[2] for x in items]
                await self.run_local(its[:20], "BAN_20")
                await self.run_local(its[20:120], "BAN_100")
                await self.run_local(its[120:], "BAN_rest")
            else:
                futs = []
                have = self.done_keys(mk)
                for pos, cell, it in items:
                    if (it["cell"], it["slot"]) in have:
                        continue
                    futs.append(self.enqueue(or_priority(mk, cell, pos), {**it, "_out": raw_path(mk),
                                                                         "_purpose": f"{mk}:{cell}"}))
                t0 = time.time()
                await asyncio.gather(*futs)
                self.throughput(mk, "BAN_all", len(futs), time.time() - t0)

    async def status_loop(self) -> None:
        while True:
            await asyncio.sleep(120)
            cnt = {mk: Counter(r["cell"] for r in read_jsonl(raw_path(mk))) for mk in self.models}
            med = sorted(self.t_or)[len(self.t_or) // 2] if self.t_or else None
            partial_status({"sampling": {mk: dict(c) for mk, c in cnt.items()}, "or_queue": self.q.qsize(),
                            "or_median_call_s": med, "spend_usd": total_cost(), "stop": self.stop.flag})
            logger.info(f"status: { {mk: sum(c.values()) for mk, c in cnt.items()} } queue {self.q.qsize()} "
                        f"median OR call {med} s, spend ${total_cost():.3f}")

    async def main(self) -> None:
        async with aiohttp.ClientSession() as session:
            workers = [asyncio.create_task(self.or_worker(session, i)) for i in range(OR_WORKERS)]
            st = asyncio.create_task(self.status_loop())
            await asyncio.gather(*[self.model_pipeline(mk, session) for mk in self.models])
            st.cancel()
            for w in workers:
                w.cancel()
        milestone("S8_done", spend=total_cost(), stopped=self.stop.flag, reason=self.stop.reason)


def run(models: list[str]) -> None:
    setup_logging("orchestrate")
    _lock = single_instance("orchestrate")  # noqa: F841 - held until exit
    if OR_WORKERS > 8:
        deviation("D9", f"OpenRouter concurrency {OR_WORKERS} instead of 8 and new-request stop at "
                        f"{STOP_NEW_OR_H} h: sampling started at {elapsed_h():.2f} h (planned 1.5 h), so the never-drop "
                        f"set (q8, q32 NAME_1..5 + DESC_5) would otherwise miss the stop time")
    asyncio.run(Orchestrator(models).main())
