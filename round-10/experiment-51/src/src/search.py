#!/usr/bin/env python3
"""S2-S4 scheduler: streams {arms} x {seeds} in lockstep ROUNDS of B calls per stream, lag-1 pipelined.

Round r's prompts are drawn from each database after round r-2's registrations, while round r-1 evaluates
(identical across streams). One nohup background process; resumes from data/<run>/state.pkl after every round.
Stops at the STOP file, the --deadline (UTC epoch) or when every stream reached its target, always after the last
completed round so the streams stay matched. --pause-after R waits (polling) for predictions/commit2.json, whose
'targets' map stream arms to target rounds, before drawing round R+1 (the C* ladder is committed there)."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bp  # noqa: E402
import engine  # noqa: E402
import islands  # noqa: E402
import prompts  # noqa: E402
import sandbox  # noqa: E402

ROOT = bp.ROOT
BF_OR_EXC, BF_W_EXC = 0.05997931747673214, 0.042309606769537086
SEL_SETS = ["SEL-OR", "SEL-W"]
EVAL_TASK = {"sets": SEL_SETS, "limit": 10.0, "fail_fast": True, "probes": ["P1"], "probe_limit": 10.0}
N_PROBE = 2000
ERR = 65535


def utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class Stream:
    def __init__(self, run: str, arm: str, seed: int, target: int, seed_prog: dict, fit: bp.Fitness):
        self.run, self.arm, self.seed, self.target = run, arm, seed, target
        self.arm_idx = engine.ARM_IDX[arm]
        self.name = f"{seed}_{arm}"
        self.n_calls = 0
        self.seen_keys: set[str] = set()
        self.db = None
        if arm != "NS":
            b25 = seed_prog["bins25"]
            self.db = islands.Database(seed, self.arm_idx, seed_prog, islands.SCORE_SCALE * fit.F(b25), tuple(b25))
        self.ff, self.bf = None, None

    def draw(self, ff_prog: dict, bf_prog: dict) -> tuple[int, list[dict]]:
        if self.arm == "NS":
            return -1, [ff_prog, bf_prog]
        return self.db.draw()


class Scheduler:
    def __init__(self, args):
        self.a = args
        self.out = ROOT / "data" / args.run
        self.out.mkdir(parents=True, exist_ok=True)
        (self.out / "decisions").mkdir(exist_ok=True)
        self.fit = bp.Fitness(bp.load_set("SEL-OR"), bp.load_set("SEL-W"), BF_OR_EXC, BF_W_EXC)
        self.state_path = self.out / "state.pkl"
        self.rows_path = self.out / "programs.jsonl"
        self.ids_path = self.out / "completion_ids.jsonl"
        self.status_path = ROOT / "results" / f"partial_status_{args.run}.json"
        self.cache: dict[str, dict] = {}
        self.round_times: list[dict] = []
        bf_b25 = json.loads((ROOT / "results" / "harness_gate.json").read_text())["sel_bf"]
        bins25 = bf_b25["or_bins"] + bf_b25["w_bins"]
        self.bf_prog = {"pid": "seed-BF", "code": bp.SRC_BF, "F": 1.0, "bins25": bins25}
        self.ff_prog = {"pid": "seed-FF", "code": bp.SRC_FF, "F": None, "bins25": None}
        arms, seeds = args.arms.split(","), [int(s) for s in args.seeds.split(",")]
        self.streams = [Stream(args.run, arm, seed, args.rounds, self.bf_prog, self.fit) for seed in seeds for arm in arms]
        self.r = 0
        self.pending = None  # (round, [(stream, call_rec)])

    # ------------------------------------------------------------------ persistence
    def save(self) -> None:
        pend = None if self.pending is None else (self.pending[0], self.pending[1])
        st = {"r": self.r, "streams": self.streams, "pending": pend, "round_times": self.round_times,
              "pause_after": self.a.pause_after}
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_bytes(pickle.dumps(st))
        tmp.replace(self.state_path)

    def load(self) -> bool:
        if not self.state_path.exists():
            return False
        st = pickle.loads(self.state_path.read_bytes())
        self.r, self.streams, self.round_times = st["r"], st["streams"], st["round_times"]
        self.a.pause_after = st.get("pause_after", self.a.pause_after)
        self.pending = st["pending"]
        if self.rows_path.exists():
            for ln in self.rows_path.read_text().splitlines():
                row = json.loads(ln)
                nk = row.get("norm_key")
                if nk and row["error_type"] not in ("http", "syntax") and nk not in self.cache:
                    dec = self._read_dec(row["dec_ref"]) if row["error_type"] == "ok" else None
                    self.cache[nk] = {"error_type": row["error_type"], "msg": row.get("error_msg", ""),
                                      "F": row.get("F"), "bins25": row.get("bins25"), "eval_s": row.get("eval_s"),
                                      "dec": dec, "probe_failed": row.get("probe_failed", False)}
        logger.info(f"resumed at round {self.r}; {len(self.cache)} cached evaluations; pending "
                    f"{None if self.pending is None else self.pending[0]}")
        return True

    # ------------------------------------------------------------------ control
    def wait_commit2(self) -> None:
        p = ROOT / "predictions" / "commit2.json"
        while not p.exists():
            if self.stop_requested():
                return
            logger.info("paused: waiting for predictions/commit2.json")
            time.sleep(15)
        c2 = json.loads(p.read_text())
        for s in self.streams:
            s.target = int(c2["targets"].get(s.arm, 0))
        logger.info(f"commit #2 targets: {[(s.name, s.target) for s in self.streams]}")
        self.a.pause_after = -1

    def stop_requested(self) -> bool:
        return (ROOT / "STOP").exists() or (ROOT / f"STOP_{self.a.run}").exists() or time.time() >= self.a.deadline

    # ------------------------------------------------------------------ one round
    def draw_round(self, tok, r: int, active: list[Stream]) -> list[tuple]:
        recs = []
        B = self.a.calls_per_round
        for s in active:
            for c in range(B):
                call_id = r * B + c
                isl, parents = s.draw(self.ff_prog, self.bf_prog)
                bodies = [prompts.body_of(p["code"]) for p in parents]
                _, ids = prompts.render(tok, bodies, idea=(s.arm == "IDEA"))
                rec = {"run": self.a.run, "seed": s.seed, "arm": s.arm, "round": r, "call_id": call_id, "island": isl,
                       "k": len(parents), "parent_ids": [p["pid"] for p in parents],
                       "parent_F": [p["F"] for p in parents],
                       "prompt_sha": hashlib.sha256(json.dumps(ids).encode()).hexdigest()[:16],
                       "prompt_len": len(ids), "engine": engine.ENGINE_TAG,
                       "temperature": engine.SAMPLING[s.arm][0], "top_p": engine.SAMPLING[s.arm][1],
                       "pid": f"{self.a.run}-{s.seed}-{s.arm}-{call_id}", "_ids": ids}
                recs.append((s, rec))
        return recs

    async def generate(self, eng: engine.Engine, r: int, recs: list[tuple]) -> None:
        t0 = time.time()
        jobs = [engine.sample(eng, s.arm, rec.pop("_ids"), seed=s.seed, arm_idx=s.arm_idx, call_id=rec["call_id"])
                for s, rec in recs]
        outs = await asyncio.gather(*jobs)
        dt = time.time() - t0
        for (s, rec), o in zip(recs, outs):
            rec["gen"] = o
        logger.info(f"round {r}: generated {len(recs)} calls in {dt:.1f}s "
                    f"({sum(o['n_gen_tokens'] for o in outs) / max(dt, 1e-9):.0f} tok/s)")

    def submit_round(self, pool: sandbox.EvalPool, recs: list[tuple]) -> list:
        futs, inround = [], set()
        for s, rec in recs:
            g = rec["gen"]
            if not g["ok"]:
                rec.update(code=None, norm_key=None)
                futs.append(None)
                continue
            code = prompts.program_from(g["text"], rec["k"])
            nk = sandbox.normalise_key(code)
            rec.update(code=code, norm_key=nk, code_sha256=hashlib.sha256(code.encode()).hexdigest())
            rec["duplicate"] = nk is not None and nk in s.seen_keys
            if nk is not None:
                s.seen_keys.add(nk)
            if nk is None:
                futs.append("syntax")
            elif nk in self.cache or nk in inround:
                rec["cache_hit"] = True
                futs.append(("cached", nk))
            else:
                inround.add(nk)
                futs.append(("new", pool.submit(dict(EVAL_TASK, code=code))))
        return futs

    def finish_round(self, r: int, recs: list[tuple], futs: list) -> None:
        dec_buf: dict[str, list[np.ndarray]] = {}
        rows, idrows = [], []
        for (s, rec), f in zip(recs, futs):
            g = rec.pop("gen")
            dec = np.full(N_PROBE, ERR, dtype=np.uint16)
            if f is None:
                rec.update(error_type="http", error_msg=g.get("error"), F=None, bins25=None, eval_s=0.0)
            elif f == "syntax":
                _, _, msg = sandbox.compile_program(rec["code"])
                rec.update(error_type="syntax", error_msg=msg, F=None, bins25=None, eval_s=0.0)
            else:
                if f[0] == "new":
                    res = f[1].result()
                    c = {"error_type": res.get("error_type", "runtime"), "msg": res.get("msg", ""),
                         "eval_s": res.get("eval_s"), "F": None, "bins25": None, "dec": None, "probe_failed": False}
                    if c["error_type"] == "ok":
                        c["bins25"] = res["bins"]["SEL-OR"] + res["bins"]["SEL-W"]
                        c["F"] = self.fit.F(c["bins25"])
                        pb = res.get("probes", {}).get("P1")
                        if pb is not None:
                            c["dec"] = np.frombuffer(pb, dtype=np.uint16).copy()
                        else:
                            c["probe_failed"] = True
                    self.cache[rec["norm_key"]] = c
                else:
                    c = self.cache[f[1]]
                rec.update(error_type=c["error_type"], error_msg=c["msg"], F=c["F"], bins25=c["bins25"],
                           eval_s=c["eval_s"] if f[0] == "new" else 0.0)
                if c.get("probe_failed"):
                    rec["probe_failed"] = True
                if c["dec"] is not None:
                    dec = c["dec"]
            rec.setdefault("duplicate", False)
            rec.setdefault("cache_hit", False)
            rec["truncated"] = bool(g.get("truncated"))
            rec["n_gen_tokens"] = g.get("n_gen_tokens", 0)
            rec["req_tokens"] = g.get("req_tokens")
            rec["wasted_tokens"] = g.get("wasted_tokens", 0)
            rec["vllm_seed"] = g.get("vllm_seed")
            rec["finish_reason"] = g.get("finish_reason")
            rec["fork"] = g.get("fork")
            fname = f"{s.seed}_{s.arm}.u16"
            rec["dec_ref"] = [fname, s.n_calls]
            dec_buf.setdefault(fname, []).append(dec)
            s.n_calls += 1
            rows.append(rec)
            idrows.append({"pid": rec["pid"], "ids": g.get("ids", [])})
            if s.db is not None and rec["error_type"] == "ok" and rec["F"] is not None:
                prog = {"pid": rec["pid"], "code": rec["code"], "F": rec["F"], "bins25": rec["bins25"]}
                s.db.register(prog, islands.SCORE_SCALE * rec["F"], tuple(rec["bins25"]), rec["island"])
        for fname, decs in dec_buf.items():
            with open(self.out / "decisions" / fname, "ab") as fh:
                np.stack(decs).astype(np.uint16).tofile(fh)
        with open(self.rows_path, "a") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")
        with open(self.ids_path, "a") as fh:
            for row in idrows:
                fh.write(json.dumps(row) + "\n")
        done = {(rec["seed"], rec["arm"]) for _, rec in recs}
        for s in self.streams:
            if s.db is not None and (s.seed, s.arm) in done and s.n_calls % islands.RESET_EVERY == 0:
                ev = s.db.reset()
                logger.info(f"{s.name}: island reset at {s.n_calls} calls: {ev}")

    def _read_dec(self, ref: list) -> np.ndarray:
        fname, i = ref
        a = np.fromfile(self.out / "decisions" / fname, dtype=np.uint16, count=N_PROBE, offset=2 * N_PROBE * int(i))
        return a if a.size == N_PROBE else np.full(N_PROBE, ERR, dtype=np.uint16)

    def status(self, extra: dict | None = None) -> None:
        rows = {}
        for s in self.streams:
            rows[s.name] = {"calls": s.n_calls, "target_rounds": s.target,
                            "best_F": None if s.db is None else -max(s.db.best_score) / 100.0,
                            "clusters": None if s.db is None else s.db.n_clusters()}
        st = {"utc": utc(), "run": self.a.run, "round": self.r, "streams": rows,
              "last_round_times": self.round_times[-3:], **(extra or {})}
        txt = json.dumps(st, indent=1)
        self.status_path.write_text(txt)
        (ROOT / "results" / "partial_status.json").write_text(txt)

    def _finish_pending(self) -> None:
        pr, precs, pfuts = self.pending
        t0 = time.time()
        self.finish_round(pr, precs, pfuts)
        self.pending = None
        logger.info(f"round {pr}: evaluated+registered ({time.time() - t0:.1f}s waiting)")

    # ------------------------------------------------------------------ main loop
    async def run(self) -> None:
        from transformers import AutoTokenizer  # noqa: PLC0415
        tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B-FP8", revision="220b46e3b2180893580a4454f21f22d3ebb187d3")
        resumed = self.load()
        pool = sandbox.EvalPool(self.a.workers, ROOT, as_gib=2.0)
        async with engine.Engine(self.a.url, tok, max_inflight=self.a.inflight) as eng:
            if resumed and self.pending is not None:
                pr, precs = self.pending
                self.pending = (pr, precs, self.submit_round(pool, precs))
            while True:
                active = [s for s in self.streams if s.target > self.r]
                if self.stop_requested() or not active:
                    break
                t0 = time.time()
                # lag-1: round r's prompts are drawn after round r-2's registration (round r-1 still evaluating)
                recs = self.draw_round(tok, self.r, active)
                if self.a.pause_after >= 0 and self.r == self.a.pause_after + 1:
                    if self.pending is not None:
                        self._finish_pending()
                    self.save()
                    self.status({"paused_for_commit2": True})
                    self.wait_commit2()
                    if self.stop_requested():
                        break
                    keep = {s.name for s in self.streams if s.target > self.r}
                    recs = [(s, rec) for s, rec in recs if s.name in keep]
                    if not recs:
                        break
                    t0 = time.time()
                await self.generate(eng, self.r, recs)
                t_gen = time.time() - t0
                futs = self.submit_round(pool, recs)
                t1 = time.time()
                if self.pending is not None:
                    self._finish_pending()
                t_wait = time.time() - t1
                self.pending = (self.r, recs, futs)
                self.round_times.append({"round": self.r, "t_gen": round(t_gen, 2), "t_wait_prev_eval": round(t_wait, 2),
                                         "t_round": round(time.time() - t0, 2), "n_calls": len(recs), "utc": utc(),
                                         "backlog": pool.backlog(), "n_streams": len({s.name for s, _ in recs})})
                self.r += 1
                self.save()
                self.status()
            if self.pending is not None:
                self._finish_pending()
            self.save()
            self.status({"finished": True, "http_failures": eng.n_http_fail})
        pool.close()
        logger.info(f"scheduler finished at round {self.r}: " + ", ".join(f"{s.name}={s.n_calls}" for s in self.streams))


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--arms", default="T1.0,T1.6,DTB,RPB,IDEA")
    ap.add_argument("--seeds", default="0,1")
    ap.add_argument("--rounds", type=int, default=80)
    ap.add_argument("--calls-per-round", type=int, default=25)
    ap.add_argument("--pause-after", type=int, default=-1, help="0-based round index after which to wait for commit #2")
    ap.add_argument("--deadline", type=float, default=time.time() + 4 * 3600)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--inflight", type=int, default=48)
    ap.add_argument("--url", default="http://127.0.0.1:8051")
    a = ap.parse_args()
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(ROOT / "logs" / f"search_{a.run}.log", rotation="30 MB", level="DEBUG")
    logger.info(f"search start {vars(a)}")
    asyncio.run(Scheduler(a).run())


if __name__ == "__main__":
    main()
