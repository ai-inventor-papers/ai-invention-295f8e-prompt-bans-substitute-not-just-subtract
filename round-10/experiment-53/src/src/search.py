"""Resumable NOV-T search driver: interleaved rounds over (arm, seed) searches at matched calls.

Each active arm-seed issues 32 calls per round. The prompts of round r come from the database holding every
registration of rounds <= r-2, so evaluation of round r-1 overlaps generation of round r and every database is a
deterministic function of the RNG streams and calls.jsonl. Targets are re-read from <out>/targets.json at every
round (COMMIT #2 changes them without a restart); <out>/STOP ends the search after in-flight work finishes.

Usage: python src/search.py --out data [--wait]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, append_jsonl, read_jsonl, setup_logging, sha256_text, utc_now, write_json  # noqa: E402
import engine  # noqa: E402
import evaluator as ev  # noqa: E402
from baselines import NN_PROGRAM  # noqa: E402
from dtb import ARM_CODE, choose_branch  # noqa: E402
from islands import Database, Prog  # noqa: E402
from prompt import extract, nn_body, render_prompt, tokenizer  # noqa: E402

CALLS_PER_ROUND = 32
MAX_INFLIGHT = 64
MAX_PENDING_EVAL = 320
ARM_SAMPLING = {"T1.0": (1.0, 1.0), "T1.6": (1.6, 0.95), "IDEA": (1.0, 1.0), "NOSEL": (1.0, 1.0),
                "DTB": (1.0, 1.0), "RPB": (1.0, 1.0)}
ARM_ORDER = ["T1.0", "T1.6", "DTB", "RPB", "IDEA", "NOSEL"]

logger = setup_logging("search")


def req_seed(seed: int, arm: str, call: int) -> int:
    return int(np.random.default_rng([seed, ARM_CODE[arm], call, 2]).integers(2 ** 31))


class ProbeStore:
    """Append-only int16 decision vectors keyed by ast_hash (data/probe_decisions.bin + probe_index.jsonl)."""

    def __init__(self, out: Path):
        self.bin = out / "probe_decisions.bin"
        self.idx = out / "probe_index.jsonl"
        self.index = {r["ast_hash"]: r["rec"] for r in read_jsonl(self.idx)}
        n_rec = self.bin.stat().st_size // 4000 if self.bin.exists() else 0
        self.index = {h: k for h, k in self.index.items() if k < n_rec}
        self.n = n_rec

    def has(self, h: str) -> bool:
        return h in self.index

    def put(self, h: str, dec: list[int]) -> None:
        if h in self.index:
            return
        arr = np.asarray(dec, dtype=np.int16)
        assert arr.shape == (2000,)
        with open(self.bin, "ab") as f:
            f.write(arr.tobytes())
        self.index[h] = self.n
        append_jsonl(self.idx, {"ast_hash": h, "rec": self.n})
        self.n += 1


class Search:
    def __init__(self, out: Path, n_eval: int, wait: bool):
        self.out = out
        self.out.mkdir(parents=True, exist_ok=True)
        self.wait = wait
        self.n_eval = n_eval
        self.calls_path = out / "calls.jsonl"
        self.req_dir = out / "requests"
        self.req_dir.mkdir(exist_ok=True)
        self.tok = tokenizer()
        nn = ev.load_baseline_nn()
        self.nn_g50, self.nn_g100 = nn["G50"], nn["G100"]
        self.nn_gaps = np.array(nn["selection"]["gaps"])
        self.nn_sig = tuple(round(float(g), 6) for g in self.nn_gaps)
        self.nn_prog = Prog(pid="NN", body=nn_body(NN_PROGRAM), score=-1.0, length=len(nn_body(NN_PROGRAM)))
        self.refs = ev.load_references()
        self.dbs: dict[tuple[str, int], Database] = {}
        self.rows: dict[tuple[str, int, int], dict] = {}
        for r in read_jsonl(self.calls_path):
            self.rows[(r["arm"], r["seed"], r["call_idx"])] = r
        self.reqs: dict[tuple[str, int, int], dict] = {}
        for p in self.req_dir.glob("*.jsonl"):
            for r in read_jsonl(p):
                self.reqs[(r["arm"], r["seed"], r["call_idx"])] = r
        self.cache: dict[str, dict] = {}
        for r in self.rows.values():
            if r.get("ast_hash") and r.get("eval_raw") is not None:
                self.cache[r["ast_hash"]] = r["eval_raw"]
        self.probes = ProbeStore(out)
        self.inflight_eval: dict[str, asyncio.Future] = {}
        self.pending_eval = 0
        self.pool = None
        self.sem = None
        self.round_stats: list[dict] = []
        self.t_start = time.time()
        self.calls_done_session = 0
        self.last_status = 0.0

    # ------------------------------------------------------------------ targets and plan
    def targets(self) -> dict:
        p = self.out / "targets.json"
        return json.loads(p.read_text()) if p.exists() else {"arm_seeds": []}

    def db(self, arm: str, seed: int) -> Database:
        if (arm, seed) not in self.dbs:
            self.dbs[(arm, seed)] = Database(arm, seed, self.nn_prog, self.nn_sig)
        return self.dbs[(arm, seed)]

    def round_calls(self, tg: dict, arm: str, seed: int, r: int) -> list[int]:
        """Call indices of arm-seed in round r (32 per round; NOSEL uses its own per-round quota)."""
        for a in tg["arm_seeds"]:
            if a["arm"] == arm and a["seed"] == seed:
                target = int(a["target"])
                if arm == "NOSEL":
                    q, r0 = int(a["per_round"]), int(a["start_round"])
                    if r < r0:
                        return []
                    lo = (r - r0) * q
                    return list(range(lo, min(lo + q, target)))
                lo = r * CALLS_PER_ROUND
                return list(range(lo, min(lo + CALLS_PER_ROUND, target)))
        return []

    # ------------------------------------------------------------------ registration (deterministic replay)
    def register_round(self, tg: dict, r: int) -> None:
        if r < 0:
            return
        for a in tg["arm_seeds"]:
            arm, seed = a["arm"], a["seed"]
            if arm == "NOSEL":
                continue
            for c in self.round_calls(tg, arm, seed, r):
                row = self.rows[(arm, seed, c)]
                d = self.db(arm, seed)
                if row["label"] == "valid":
                    prog = Prog(pid=f"{arm}|{seed}|{c}", body=row["body"], score=-row["F"], length=len(row["body"]))
                    d.complete_call(row["island"], prog, tuple(round(float(g), 6) for g in row["gaps"]))
                else:
                    d.complete_call(row["island"], None, None)

    def build_prompts(self, tg: dict, r: int) -> list[dict]:
        jobs = []
        for a in sorted(tg["arm_seeds"], key=lambda x: (x["seed"], ARM_ORDER.index(x["arm"]))):
            arm, seed = a["arm"], a["seed"]
            for c in self.round_calls(tg, arm, seed, r):
                if arm == "NOSEL":
                    parents, island = [self.nn_prog], -1
                else:
                    island, parents = self.db(arm, seed).get_prompt()
                jobs.append({"arm": arm, "seed": seed, "call_idx": c, "round": r, "island": island,
                             "parents": parents})
        return jobs

    # ------------------------------------------------------------------ generation
    async def generate(self, job: dict) -> dict:
        arm, seed, c = job["arm"], job["seed"], job["call_idx"]
        k = len(job["parents"])
        text, ids = render_prompt([p.body for p in job["parents"]], idea=(arm == "IDEA"))
        rs = req_seed(seed, arm, c)
        T, top_p = ARM_SAMPLING[arm]
        rec: dict = {"arm": arm, "seed": seed, "call_idx": c, "round": job["round"], "island": job["island"],
                     "k": k, "parent_ids": [p.pid for p in job["parents"]],
                     "parent_F": [-p.score for p in job["parents"]], "prompt_sha256": sha256_text(text),
                     "prompt_len_tokens": len(ids), "request_seed": rs, "temperature": T, "top_p": top_p,
                     "utc": utc_now()}
        t0 = time.time()
        async with self.sem:
            if arm in ("DTB", "RPB"):
                r1 = await engine.complete(ids, temperature=1.0, top_p=1.0, max_tokens=engine.R1_TOKENS, seed=rs,
                                           logprobs=20)
                rec["r1"] = r1
                if r1.get("error") or r1.get("token_ids") is None:
                    rec["gen_error"] = r1.get("error") or "no token ids"
                    rec["final_text"] = None
                else:
                    b = r1["token_ids"]
                    br = choose_branch(self.tok, b, r1["top"], len(r1["text"]),
                                       "entropy" if arm == "DTB" else "random", seed, arm, c)
                    rec["branch"] = br
                    if br["no_branch"]:
                        if r1["finish_reason"] == "stop":
                            rec["final_text"] = r1["text"]
                            rec["final_finish"] = "stop"
                            rec["discarded_tokens"] = 0
                        else:
                            r2 = await engine.complete(ids + b, temperature=1.0, top_p=1.0,
                                                       max_tokens=engine.MAX_TOKENS - len(b), seed=rs + 1)
                            rec["r2"] = r2
                            if r2.get("error"):
                                rec["gen_error"] = r2["error"]
                                rec["final_text"] = None
                            else:
                                pre = self.tok.decode(b, skip_special_tokens=False,
                                                      clean_up_tokenization_spaces=False)
                                rec["final_text"] = pre + r2["text"]
                                rec["final_finish"] = r2["finish_reason"]
                            rec["discarded_tokens"] = 0
                    else:
                        j = br["j_star"]
                        pre_ids = b[:j] + [br["forced_id"]]
                        r2 = await engine.complete(ids + pre_ids, temperature=1.0, top_p=1.0,
                                                   max_tokens=engine.MAX_TOKENS - (j + 1), seed=rs + 1)
                        rec["r2"] = r2
                        rec["discarded_tokens"] = len(b) - j
                        if r2.get("error"):
                            rec["gen_error"] = r2["error"]
                            rec["final_text"] = None
                        else:
                            pre = self.tok.decode(pre_ids, skip_special_tokens=False,
                                                  clean_up_tokenization_spaces=False)
                            rec["final_text"] = pre + r2["text"]
                            rec["final_finish"] = r2["finish_reason"]
            else:
                r1 = await engine.complete(ids, temperature=T, top_p=top_p, max_tokens=engine.MAX_TOKENS, seed=rs)
                rec["r1"] = r1
                if r1.get("error"):
                    rec["gen_error"] = r1["error"]
                    rec["final_text"] = None
                else:
                    rec["final_text"] = r1["text"]
                    rec["final_finish"] = r1["finish_reason"]
                    rec["discarded_tokens"] = 0
        rec["gen_wall"] = time.time() - t0
        rec["gen_tokens"] = sum((rec.get(x) or {}).get("completion_tokens") or 0 for x in ("r1", "r2"))
        rec["prompt_tokens"] = sum((rec.get(x) or {}).get("prompt_tokens") or 0 for x in ("r1", "r2"))
        append_jsonl(self.req_dir / f"{arm}_{seed}.jsonl", rec)
        self.reqs[(arm, seed, c)] = rec
        return rec

    # ------------------------------------------------------------------ evaluation
    async def _eval_code(self, code: str, h: str) -> dict:
        if h in self.cache:
            return self.cache[h]
        if h in self.inflight_eval:
            return await self.inflight_eval[h]
        fut = asyncio.get_running_loop().create_future()
        self.inflight_eval[h] = fut
        res = None
        for attempt in range(3):
            try:
                res = await asyncio.get_running_loop().run_in_executor(self.pool, ev.job_program, code, True)
                break
            except BrokenProcessPool:
                logger.error("evaluator pool broken; recreating")
                self.pool = ev.make_pool(self.n_eval)
        if res is None:
            res = {"label": "runtime_error", "reason": "evaluator infrastructure failure", "lengths": None,
                   "decisions": None, "probe_label": None}
        if res.get("decisions") is not None:
            self.probes.put(h, res["decisions"])
        raw = {k: v for k, v in res.items() if k != "decisions"}
        self.cache[h] = raw
        fut.set_result(raw)
        del self.inflight_eval[h]
        return raw

    async def evaluate(self, rec: dict) -> dict:
        import sandbox

        arm, seed, c = rec["arm"], rec["seed"], rec["call_idx"]
        k = rec["k"]
        row = {"model": "Qwen/Qwen3-8B-FP8@220b46e", "engine": ENGINE_TAG, "task": "tsp_construct", "arm": arm,
               "seed": seed, "call_idx": c, "round": rec["round"], "island": rec["island"],
               "parent_ids": rec["parent_ids"], "parent_F": rec["parent_F"], "k": k,
               "prompt_tokens": rec.get("prompt_tokens"), "gen_tokens": rec.get("gen_tokens"),
               "discarded_tokens": rec.get("discarded_tokens", 0), "gen_wall": rec.get("gen_wall"),
               "request_seed": rec["request_seed"], "truncated": rec.get("final_finish") == "length",
               "label": None, "probe_valid": False, "F": None, "G50": None, "G100": None, "gaps": None,
               "code": None, "body": None, "code_sha256": None, "ast_hash": None, "trimmed_lines": 0,
               "eval_raw": None, "utc": utc_now()}
        if arm in ("DTB", "RPB") and rec.get("branch"):
            br = rec["branch"]
            row["dtb"] = {kk: br.get(kk) for kk in (
                "m", "eligible", "H", "j_star", "H_j_star", "H_rank_among_eligible", "n_eligible", "top20_at_j",
                "sampled_id", "sampled_text", "forced_id", "forced_text", "forced_rank", "forced_logprob",
                "forced_eq_sampled", "forced_class", "sampled_class", "no_branch", "no_branch_reason",
                "fallback_steps", "candidates", "position_frac")}
            row["dtb"]["r1_tokens"] = (rec.get("r1") or {}).get("completion_tokens")
            row["dtb"]["r2_tokens"] = (rec.get("r2") or {}).get("completion_tokens")
            row["dtb"]["r1_finish"] = (rec.get("r1") or {}).get("finish_reason")
        if rec.get("final_text") is None:
            row["label"] = "gen_failed"
            row["gen_error"] = rec.get("gen_error")
            return row
        ex = extract(rec["final_text"], k)
        row["trimmed_lines"] = ex["trimmed_lines"]
        row["body"] = ex["body"]
        if ex["program"] is None:
            row["label"] = "truncated" if row["truncated"] else ex["label"]
            return row
        code = ex["program"]
        row["code"] = code
        row["code_sha256"] = sha256_text(code)
        try:
            san = sandbox.static_check(code)
            h = sandbox.ast_hash(san)
        except sandbox.StaticReject as e:
            row["label"] = e.cls
            row["reason"] = e.reason
            row["ast_hash"] = sandbox.ast_hash(code)
            return row
        row["ast_hash"] = h
        self.pending_eval += 1
        try:
            raw = await self._eval_code(code, h)
        finally:
            self.pending_eval -= 1
        row["eval_raw"] = raw
        row["label"] = raw["label"]
        if raw["label"] == "valid":
            gaps = ev.gaps_from_lengths(raw["lengths"], self.refs["selection"])
            F, g50, g100 = ev.fitness(gaps, self.nn_g50, self.nn_g100)
            row.update(F=F, G50=g50, G100=g100, gaps=[round(float(g), 6) for g in gaps],
                       probe_valid=raw.get("probe_label") == "probe_valid", probe_label=raw.get("probe_label"),
                       n_err=raw.get("n_err"))
        else:
            row["reason"] = raw.get("reason")
            if row["truncated"] and raw["label"] in ("syntax_error", "no_code"):
                row["label"] = "truncated"
        return row

    async def one_call(self, job: dict) -> None:
        key = (job["arm"], job["seed"], job["call_idx"])
        while self.pending_eval > MAX_PENDING_EVAL:
            await asyncio.sleep(0.5)
        rec = self.reqs.get(key)
        if rec is None or rec.get("final_text") is None and rec.get("gen_error"):
            rec = await self.generate(job)
        row = await self.evaluate(rec)
        append_jsonl(self.calls_path, row)
        self.rows[key] = row
        self.calls_done_session += 1

    # ------------------------------------------------------------------ status
    def status(self, tg: dict, r: int, force: bool = False) -> None:
        if not force and time.time() - self.last_status < 60:
            return
        self.last_status = time.time()
        per = {}
        for (arm, seed, c), row in self.rows.items():
            d = per.setdefault(f"{arm}|{seed}", {"calls": 0, "valid": 0, "probe_valid": 0, "best_F": None})
            d["calls"] += 1
            d["valid"] += row["label"] == "valid"
            d["probe_valid"] += bool(row.get("probe_valid"))
            if row.get("F") is not None and (d["best_F"] is None or row["F"] < d["best_F"]):
                d["best_F"] = row["F"]
        el = time.time() - self.t_start
        st = {"utc": utc_now(), "round": r, "per_arm_seed": per, "session_calls": self.calls_done_session,
              "calls_per_min_session": 60 * self.calls_done_session / max(el, 1), "pending_eval": self.pending_eval,
              "targets": tg, "last_rounds": self.round_stats[-5:]}
        write_json(self.out / "partial_status.json", st)
        if self.out.resolve() == (ROOT / "data").resolve():
            write_json(ROOT / "results" / "partial_status.json", st)

    # ------------------------------------------------------------------ register barrier
    def _sync_register(self, tg: dict, r: int, registered_upto: int):
        need = r - 2
        if need > registered_upto:
            missing = [(a["arm"], a["seed"], c) for a in tg["arm_seeds"] if a["arm"] != "NOSEL"
                       for c in self.round_calls(tg, a["arm"], a["seed"], need) if
                       (a["arm"], a["seed"], c) not in self.rows]
            if missing:
                return "WAIT"
            for rr in range(registered_upto + 1, need + 1):
                self.register_round(tg, rr)
        return self.build_prompts(tg, r)


async def _run_with_wait(s: Search) -> None:
    """Main loop: register rounds <= r-2 (waiting for their evaluation), build and launch round r."""
    s.pool = ev.make_pool(s.n_eval)
    s.sem = asyncio.Semaphore(MAX_INFLIGHT)
    eval_tasks: dict[int, list[asyncio.Task]] = {}
    registered_upto = -1
    r = 0
    idle_since = None
    while True:
        if (s.out / "STOP").exists():
            logger.info("STOP file found: no new rounds")
            break
        tg = s.targets()
        res = s._sync_register(tg, r, registered_upto)
        if res == "WAIT":
            # rounds <= r-2 not fully evaluated: if their calls are not even launched (resume), launch them
            need = r - 2
            launched = {(t_arm, t_seed, t_c) for t_arm, t_seed, t_c in getattr(s, "_launched", set())}
            missing_jobs = [j for j in s.build_prompts_dry(tg, need) if
                            (j["arm"], j["seed"], j["call_idx"]) not in s.rows and
                            (j["arm"], j["seed"], j["call_idx"]) not in launched]
            if missing_jobs:
                logger.error(f"round {need} has {len(missing_jobs)} unlaunched calls; this should not happen")
            await asyncio.sleep(0.2)
            s.status(tg, r)
            continue
        registered_upto = max(registered_upto, r - 2)
        jobs_all = res
        if not jobs_all:
            more = any(s.round_calls(tg, a["arm"], a["seed"], rr) for a in tg["arm_seeds"] for rr in range(r, r + 400))
            if more:
                r += 1
                continue
            if s.wait:
                if idle_since is None:
                    idle_since = time.time()
                    logger.info(f"all targets reached at round {r}; waiting for new targets")
                await asyncio.sleep(5)
                s.status(tg, r)
                continue
            break
        idle_since = None
        jobs = [j for j in jobs_all if (j["arm"], j["seed"], j["call_idx"]) not in s.rows]
        t0 = time.time()
        s._launched = getattr(s, "_launched", set()) | {(j["arm"], j["seed"], j["call_idx"]) for j in jobs}
        tasks = [asyncio.create_task(s.one_call(j)) for j in jobs]
        eval_tasks[r] = tasks
        while True:
            gen_done = all((j["arm"], j["seed"], j["call_idx"]) in s.reqs for j in jobs)
            if gen_done or all(t.done() for t in tasks):
                break
            await asyncio.sleep(0.2)
            s.status(tg, r)
        for t in tasks:
            if t.done() and t.exception() is not None:
                logger.error(f"call task failed: {t.exception()!r}")
        stats = {"round": r, "n_calls": len(jobs), "gen_wall": time.time() - t0, "utc": utc_now(),
                 "pending_eval": s.pending_eval, "tokens": {}}
        for j in jobs:
            q = s.reqs.get((j["arm"], j["seed"], j["call_idx"]), {})
            d = stats["tokens"].setdefault(f"{j['arm']}|{j['seed']}", {"calls": 0, "gen": 0, "prompt": 0, "wall": 0.0})
            d["calls"] += 1
            d["gen"] += q.get("gen_tokens") or 0
            d["prompt"] += q.get("prompt_tokens") or 0
            d["wall"] += q.get("gen_wall") or 0.0
        s.round_stats.append(stats)
        append_jsonl(s.out / "rounds.jsonl", stats)
        logger.info(f"round {r}: {len(jobs)} calls generated in {stats['gen_wall']:.1f}s; pending eval "
                    f"{s.pending_eval}; total rows {len(s.rows)}")
        s.status(tg, r, force=True)
        for a in tg["arm_seeds"]:
            if a["arm"] != "NOSEL":
                write_json(s.out / "db" / f"{a['arm']}_{a['seed']}.json", s.db(a["arm"], a["seed"]).snapshot())
        r += 1
    pend = [t for ts in eval_tasks.values() for t in ts if not t.done()]
    if pend:
        logger.info(f"draining {len(pend)} in-flight calls (<= 300 s)")
        done, notdone = await asyncio.wait(pend, timeout=300)
        for t in notdone:
            t.cancel()
        logger.info(f"drained {len(done)}, cancelled {len(notdone)}")
    s.status(s.targets(), r, force=True)
    s.pool.shutdown(wait=False, cancel_futures=True)


def _build_prompts_dry(self: Search, tg: dict, r: int) -> list[dict]:
    out = []
    for a in tg["arm_seeds"]:
        for c in self.round_calls(tg, a["arm"], a["seed"], r):
            out.append({"arm": a["arm"], "seed": a["seed"], "call_idx": c})
    return out


Search.build_prompts_dry = _build_prompts_dry

ENGINE_TAG = os.environ.get("NOVT_ENGINE_TAG", "vllm0.11.0|Qwen3-8B-FP8@220b46e|marlin|eager")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data")
    ap.add_argument("--n-eval", type=int, default=4)
    ap.add_argument("--wait", action="store_true")
    a = ap.parse_args()
    out = (ROOT / a.out).resolve()
    s = Search(out, a.n_eval, a.wait)
    logger.info(f"search start: out={out} rows={len(s.rows)} cached_evals={len(s.cache)} engine={ENGINE_TAG}")
    asyncio.run(_run_with_wait(s))
    logger.info("search finished")


if __name__ == "__main__":
    main()
