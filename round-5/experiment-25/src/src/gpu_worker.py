#!/usr/bin/env python3
"""One long-lived GPU worker: a priority job queue (queue/*.json) with a programmatic commit guard.

loop: read queue/*.json; skip jobs whose `requires` tags are absent from commitments.log (guard, logged); pick the
highest-priority runnable job (lower prio number first; ties prefer the loaded model, then FIFO); switch models when
needed (unload, gc, empty_cache, load the other in the same precision; never two models on the GPU); run the job's
batches (resumable: slots already in data/raw/<task>.jsonl are skipped); move the job to queue/done/.
Job kinds: sample | states | margin | gputest | enginecheck. Stop: create queue/STOP.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import torch  # noqa: E402
from loguru import logger  # noqa: E402

from cfg5 import (QUEUE, RAW_DIR, RESULTS, V_BLOCKS, append_deviation, append_jsonl, read_json, read_jsonl,  # noqa: E402
                  setup_logging, unit_dir, utc_now, write_json)
from commit5 import tags  # noqa: E402

GUARD_LOG = RESULTS / "guard_log.jsonl"
_GUARD_SEEN: set[str] = set()


def load_jobs() -> list[dict[str, Any]]:
    jobs = []
    for p in sorted(QUEUE.glob("*.json")):
        try:
            j = json.loads(p.read_text())
            j["_path"] = str(p)
            jobs.append(j)
        except (json.JSONDecodeError, OSError):
            continue
    return jobs


def guard_ok(job: dict[str, Any], tg: dict[str, str]) -> bool:
    missing = [t for t in job.get("requires", []) if t not in tg]
    if missing and job["id"] not in _GUARD_SEEN:
        _GUARD_SEEN.add(job["id"])
        append_jsonl(GUARD_LOG, [{"job": job["id"], "event": "blocked", "missing": missing, "utc": utc_now()}])
    return not missing


class Worker:
    def __init__(self) -> None:
        self.which: str | None = None
        self.tok = None
        self.model = None
        self.ctx: dict[str, Any] = {}
        self.prompts = None

    def ensure(self, which: str) -> None:
        if self.which == which:
            return
        from engine5 import load_model

        if self.model is not None:
            logger.info(f"switching model {self.which} -> {which}")
            del self.model
            self.model = None
            self.ctx.clear()
            gc.collect()
            torch.cuda.empty_cache()
        t0 = time.time()
        self.tok, self.model = load_model(which, vram_fraction=0.97, fp8=False)
        self.which = which
        append_jsonl(RESULTS / "model_switches.jsonl", [{"to": which, "seconds": round(time.time() - t0, 1),
                                                          "utc": utc_now()}])

    def get_prompts(self) -> dict:
        from specs5 import load_prompts

        self.prompts = load_prompts()  # reload: assoc prompts are added during the run
        return self.prompts

    def context(self, task: str):
        from sampler5 import TaskContext

        key = (task, self.which)
        if key not in self.ctx:
            if len(self.ctx) >= 2:  # keep at most two tasks' clean prefills in memory
                self.ctx.pop(next(iter(self.ctx)))
                torch.cuda.empty_cache()
            self.ctx[key] = TaskContext(self.model, self.tok, self.get_prompts(), task, self.which)
        return self.ctx[key]

    # ------------------------------------------------------------------------------------------- job kinds
    def run_sample(self, job: dict[str, Any]) -> int:
        from sampler5 import done_keys, run_batch

        task = job["task"]
        ctx = self.context(task)
        ctx.pr = self.get_prompts()
        n = 0
        done = done_keys(task, job.get("out_file"))
        for bi, b in enumerate(job["batches"]):
            spec = [(a, list(ks)) for a, ks in b["spec"]]
            if all((a, self.which, b["w"], k) in done for a, ks in spec for k in ks):
                continue
            bid = f"{job['id']}#{bi}"
            try:
                run_batch(ctx, b["w"], spec, bid, out_file=job.get("out_file"))
            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                append_deviation("D-oom-split", "a batch hit CUDA OOM and was re-run as two half batches (batch shape "
                                 "differs for those rows; bf16 numerics are not batch-invariant)")
                halves = [[(a, ks[:len(ks) // 2]) for a, ks in spec if ks[:len(ks) // 2]],
                          [(a, ks[len(ks) // 2:]) for a, ks in spec if ks[len(ks) // 2:]]]
                for h in halves:
                    if h:
                        run_batch(ctx, b["w"], h, bid + "/half", out_file=job.get("out_file"))
            n += 1
        return n

    def run_states(self, job: dict[str, Any]) -> int:
        ctx = self.context(job["task"])
        summ = ctx.save_states()
        append_jsonl(RESULTS / "states_summary.jsonl", [{"task": job["task"], "utc": utc_now(), **summ}])
        return 1

    def run_margin(self, job: dict[str, Any]) -> int:
        """Opening margin: teacher-force twin ids + '```python\\n' + signature line + the first <= 16 body tokens of
        each mode's reference; logP_j(w) = sum of the body-token log-probs."""
        from engine5 import teacher_logprobs

        u = job["task"]
        spec = read_json(unit_dir(u) / "spec.json")
        refs = {}
        for c in spec["catalogue"]:
            p = unit_dir(u) / "references" / f"{c['mode']}.py"
            if p.exists():
                refs[c["mode"]] = p.read_text()
        ctx = self.context(u)
        sig_line = f"def {spec['signature']}:\n"
        out: dict[str, Any] = {"task": u, "per_w": {}, "body_tokens": {}}
        for w in ("W1", "W2", "W3", "W4", "W5"):
            p = ctx.prompt(w, "twin")
            pref = self.tok("```python\n" + sig_line, add_special_tokens=False)["input_ids"]
            res = {}
            for m, code in refs.items():
                i = code.find("def solve")
                body = code[code.index("\n", i) + 1:] if i >= 0 else code
                bt = self.tok(body, add_special_tokens=False)["input_ids"][:16]
                ids = list(p["ids"]) + pref + bt
                lps = teacher_logprobs(self.model, ids, len(p["ids"]) + len(pref))
                res[m] = float(sum(lps))
                out["body_tokens"][m] = self.tok.decode(bt)
            out["per_w"][w] = res
        write_json(RESULTS / "margins" / f"{u}.json", out)
        return 1

    def run_gputest(self, job: dict[str, Any]) -> int:
        from gpu_tests import run_tests

        res = run_tests(self, job)
        append_jsonl(RESULTS / "gpu_tests.jsonl", [{"job": job["id"], "utc": utc_now(), **res}])
        return 1

    def run(self, job: dict[str, Any]) -> int:
        self.ensure(job["model"])
        kind = job.get("kind", "sample")
        if kind == "sample":
            return self.run_sample(job)
        if kind == "states":
            return self.run_states(job)
        if kind == "margin":
            return self.run_margin(job)
        if kind == "gputest":
            return self.run_gputest(job)
        raise ValueError(kind)


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--idle-exit-min", type=float, default=0.0, help="exit after this many idle minutes (0 = never)")
    args = ap.parse_args()
    setup_logging("gpu_worker")
    torch.cuda.set_per_process_memory_fraction(0.97, 0)
    W = Worker()
    idle_since = time.time()
    while True:
        if (QUEUE / "STOP").exists():
            logger.info("STOP flag found: exiting")
            break
        tg = tags()
        jobs = load_jobs()
        runnable = [j for j in jobs if guard_ok(j, tg)]
        if not runnable:
            if args.idle_exit_min and time.time() - idle_since > args.idle_exit_min * 60:
                logger.info("idle timeout: exiting")
                break
            time.sleep(5)
            continue
        job = min(runnable, key=lambda j: (j["prio"], j["model"] != W.which, j.get("created", "")))
        if job.get("requires"):
            append_jsonl(GUARD_LOG, [{"job": job["id"], "event": "released", "requires": job["requires"],
                                      "tags_utc": {t: tg[t] for t in job["requires"]}, "utc": utc_now()}])
        t0 = time.time()
        p = Path(job["_path"])
        try:
            n = W.run(job)
            dest = QUEUE / "done" / p.name
            logger.info(f"job {job['id']} done: {n} units of work in {time.time() - t0:.0f}s")
            append_jsonl(RESULTS / "jobs_log.jsonl", [{"job": job["id"], "prio": job["prio"], "model": job["model"],
                                                       "kind": job.get("kind", "sample"), "n": n,
                                                       "seconds": round(time.time() - t0, 1), "utc": utc_now()}])
        except Exception as e:  # noqa: BLE001 - a failed job is parked in queue/failed with its traceback
            logger.exception(f"job {job['id']} failed: {e}")
            dest = QUEUE / "failed" / p.name
            append_jsonl(RESULTS / "jobs_log.jsonl", [{"job": job["id"], "error": str(e)[:300],
                                                       "trace": traceback.format_exc()[-1500:], "utc": utc_now()}])
            torch.cuda.empty_cache()
        try:
            p.replace(dest)
        except OSError:
            pass
        idle_since = time.time()


if __name__ == "__main__":
    main()
