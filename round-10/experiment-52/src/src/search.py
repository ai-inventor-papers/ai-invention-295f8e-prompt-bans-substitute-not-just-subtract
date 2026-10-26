#!/usr/bin/env python3
"""S6/S8/S9 lockstep island search. All active arm-seeds generate 20 calls per round in lockstep; the prompts of round
r+1 are built from the databases after round r-1 is registered (one-round evaluation lag, generation of round r+1
overlaps the evaluation of round r). Rows are appended as produced; databases are pickled after every round; resume
reloads the last complete round. The C* rule (after round 5), the dynamic drop rule (every 5 rounds) and the hard stop
are applied here. NS (fixed parents, no registration) runs after the core arms inside the window.

Usage: python src/search.py smoke | run"""
from __future__ import annotations

import asyncio
import json
import pickle
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

import bp  # noqa: E402
import common as C  # noqa: E402
import engine as EN  # noqa: E402
import islands as IS  # noqa: E402
import operators as OP  # noqa: E402
import prompts as P  # noqa: E402
import sandbox  # noqa: E402

ROUND_CALLS = 20
SEARCH_ARMS = ["T1.0", "T1.6", "DTB", "RPB", "IDEA"]
N_EVAL_WORKERS = 9
# Exploratory extension (amendment commit #3): NOVB2_SEEDS="4,5" NOVB2_TAG="ext45" runs the identical protocol on new
# seeds with C fixed at the committed C* and no NS; the pre-registered verdicts use seeds 2 and 3 only.
import os as _os  # noqa: E402
RUN_SEEDS = [int(x) for x in _os.environ.get("NOVB2_SEEDS", ",".join(map(str, C.SEEDS))).split(",")]
RUN_TAG = _os.environ.get("NOVB2_TAG", "")
_SFX = f"_{RUN_TAG}" if RUN_TAG else ""
CFG_PATH = C.RESULTS / f"search_config{_SFX}.json"
STATE_PKL = C.DATA / f"search_state{_SFX}.pkl"
DEC_BIN = C.DATA / "decisions.bin"
DEC_IDX = C.DATA / "decisions_index.jsonl"
STATUS_EVERY_S = 300
N_STATES = 2000
TOPS_KEEP = 200  # r1 top-20 tables stored for the first 200 DTB/RPB calls per arm-seed (re-derivation CHECK, replay)

# Clock milestones in hours since T0 (the plan's 6 h schedule shifted 10 min earlier: the session limit is 5 h 54 min)
H_CSTAR_END = 4.5      # plan 4:40
H_DROP_END = 4.633     # plan 4:58 (core arms must reach C* by then)
H_HARD_STOP = 4.667    # plan 5:00
CSTAR_OPTIONS = [2000, 1500, 1000]


# ------------------------------------------------------------------------------------------------ helpers
def gen_path(S: int) -> Path:
    return C.DATA / f"gen_s{S}.jsonl"


def seed_record(name: str) -> dict:
    g = json.loads((C.RESULTS / "harness_gate.json").read_text())
    F = fitness()
    if name == "BF":
        sig = g["sel_bf"]["or_bins"] + g["sel_bf"]["w_bins"]
        code = P.seed_program(P.BF_BODY)
    else:
        insts = bp.load_set("SEL-OR") + bp.load_set("SEL-W")
        sig = [bp.pack(x["items"], x["capacity"], bp.prio_ff) for x in insts]
        code = P.seed_program(P.FF_BODY)
    return {"pid": f"seed-{name}", "code": code, "F": F.F(sig), "sig": sig, "arm": None, "S": None, "call": None}


_FIT = None


def fitness() -> bp.Fitness:
    global _FIT
    if _FIT is None:
        g = json.loads((C.RESULTS / "harness_gate.json").read_text())
        _FIT = bp.Fitness(bp.load_set("SEL-OR"), bp.load_set("SEL-W"), g["sel_bf"]["or_excess"], g["sel_bf"]["w_excess"])
    return _FIT


class DecisionStore:
    """Append-only uint16 decision vectors (one per unique evaluated program key) + JSONL index."""

    def __init__(self):
        self.index: dict[str, int] = {}
        n = 0
        for r in C.read_jsonl(DEC_IDX):
            self.index[r["key"]] = r["row"]
            n = max(n, r["row"] + 1)
        size = DEC_BIN.stat().st_size // (2 * N_STATES) if DEC_BIN.exists() else 0
        self.n = min(n, size)
        self.index = {k: v for k, v in self.index.items() if v < self.n}

    def add(self, key: str, vec: np.ndarray, fs_only: bool) -> int:
        if key in self.index:
            return self.index[key]
        row = self.n
        with open(DEC_BIN, "ab") as f:
            f.write(np.asarray(vec, dtype=np.uint16).tobytes())
        self.n += 1
        self.index[key] = row
        C.append_jsonl(DEC_IDX, {"key": key, "row": row, "fs_only": fs_only})
        return row


def load_decisions() -> tuple[np.ndarray, dict[str, int]]:
    idx = {r["key"]: r["row"] for r in C.read_jsonl(DEC_IDX)}
    if not DEC_BIN.exists():
        return np.zeros((0, N_STATES), dtype=np.uint16), idx
    arr = np.fromfile(DEC_BIN, dtype=np.uint16)
    arr = arr[: (len(arr) // N_STATES) * N_STATES].reshape(-1, N_STATES)
    return arr, {k: v for k, v in idx.items() if v < len(arr)}


# ------------------------------------------------------------------------------------------------ searcher
class Searcher:
    def __init__(self, mode: str = "run"):
        self.mode = mode
        self.tok = EN.load_tokenizer()
        self.tt = OP.TokText(self.tok)
        self.pool = sandbox.EvalPool(N_EVAL_WORKERS, C.ROOT)
        self.cache = sandbox.EvalCache(self.pool)
        self.dstore = DecisionStore()
        self.engine: EN.Engine | None = None
        self.cfg = json.loads(CFG_PATH.read_text()) if CFG_PATH.exists() else {}
        if RUN_TAG and "C_star" not in self.cfg:
            base = json.loads((C.RESULTS / "search_config.json").read_text())
            self.cfg = {"C_star": base["C_star"], "drop": ["NS"], "extension": RUN_TAG, "seeds": RUN_SEEDS}
            C.write_json(CFG_PATH, self.cfg)
        self.bf = seed_record("BF")
        self.ff = seed_record("FF")
        self.dbs: dict[tuple[int, str], IS.ArmDB] = {}
        self.round = 0
        self.round_times: list[float] = []
        self.active = [(S, a) for S in RUN_SEEDS for a in SEARCH_ARMS]
        self.caps: dict[tuple[int, str], int] = {}
        self.last_status = 0.0
        self.tops_written: dict[tuple[int, str], int] = {}
        self.events: list[dict] = []

    # ---------------------------------------------------------------- persistence
    def save_state(self, pending_round: int | None) -> None:
        st = {"round": self.round, "dbs": self.dbs, "round_times": self.round_times, "active": self.active,
              "caps": self.caps, "pending_round": pending_round, "tops_written": self.tops_written,
              "events": self.events, "utc": C.utc()}
        tmp = STATE_PKL.with_suffix(".tmp")
        with open(tmp, "wb") as f:
            pickle.dump(st, f)
        tmp.replace(STATE_PKL)
        for (S, a), db in self.dbs.items():
            t2 = C.DATA / f"db_s{S}_{a}.pkl.tmp"
            with open(t2, "wb") as f:
                pickle.dump(db, f)
            t2.replace(C.DATA / f"db_s{S}_{a}.pkl")

    def load_state(self) -> int | None:
        if not STATE_PKL.exists():
            for S, a in self.active:
                self.dbs[(S, a)] = IS.ArmDB(S, a, self.bf)
            return None
        with open(STATE_PKL, "rb") as f:
            st = pickle.load(f)
        self.round, self.dbs, self.round_times = st["round"], st["dbs"], st["round_times"]
        self.active, self.caps, self.tops_written = st["active"], st["caps"], st["tops_written"]
        self.events = st.get("events", [])
        # rebuild the evaluation cache from eval rows
        for r in C.read_eval_rows():
            if r.get("key") and not r.get("cached") and r.get("res"):
                self.cache.preload(r["key"], r["res"])
        logger.info(f"resumed at round {self.round} ({len(self.cache.done)} cached evaluations)")
        return st["pending_round"]

    # ---------------------------------------------------------------- one call
    def build_prompt(self, S: int, arm: str, worse: dict, better: dict) -> tuple[str, list[int], str]:
        user = P.user_turn(worse["code"], better["code"], idea=(arm == "IDEA"))
        txt, ids = P.render(self.tok, user)
        return txt, ids, C.sha256_text(txt)

    async def one_call(self, S: int, arm: str, call: int, rnd: int, slot: int, island: int | None, worse: dict,
                       better: dict) -> dict:
        txt, ids, psha = self.build_prompt(S, arm, worse, better)
        g = await OP.generate(self.engine, self.tt, arm, S, call, ids)
        code = P.program_from_completion(g["completion"]) if not g["failed"] else ""
        row = {"model": C.MODEL_ID, "engine": C.ENGINE_TAG, "provider": "local", "task": "online_bin_packing",
               "arm": arm, "condition": OP.condition(arm), "k": None, "template": P.TEMPLATE_NAME, "slot": slot,
               "seed": S, "label": f"{arm}|S{S}|r{rnd}|c{call}", "order_class": None, "ds_signature": None,
               "lexical_flag": None, "passed": None, "truncated": bool(g["truncated"]),
               "n_tokens": int(g.get("completion_tokens") or 0), "code_sha256": C.sha256_text(code), "code": code,
               "round": rnd, "call": call, "island": island, "parent_ids": [worse["pid"], better["pid"]],
               "parent_F": [worse["F"], better["F"]], "prompt_sha256": psha,
               "prompt_tokens": g.get("prompt_tokens"), "completion_tokens": g.get("completion_tokens"),
               "n_requests": g.get("n_requests"), "failed": bool(g["failed"]), "error": g.get("error"),
               "finish_reason": g.get("finish_reason"), "completion": g["completion"], "utc": C.utc()}
        if "branch" in g:
            br = dict(g["branch"])
            row["branch"] = br
            row["r1_tokens"], row["r2_tokens"] = g.get("r1_tokens"), g.get("r2_tokens")
            row["r1_ids"] = g.get("r1_ids")
            key = (S, arm)
            if self.tops_written.get(key, 0) < TOPS_KEEP and g.get("r1_top") is not None:
                C.append_jsonl(C.DATA / f"r1_tops_s{S}_{arm}.jsonl", {"seed": S, "arm": arm, "call": call,
                                                                       "r1_ids": g.get("r1_ids"),
                                                                       "top": g.get("r1_top"),
                                                                       "prompt_sha256": psha})
                self.tops_written[key] = self.tops_written.get(key, 0) + 1
        return row

    # ---------------------------------------------------------------- evaluation bookkeeping
    def submit(self, row: dict):
        if row["failed"] or not row["code"]:
            return row, None, None, False
        key, fut, cached = self.cache.submit(row["code"])
        return row, key, fut, cached

    def finish_eval(self, row: dict, key, fut, cached, register: bool, eval_path: Path | None = None) -> dict:
        S, arm = row["seed"], row["arm"]
        if fut is None:
            res = {"error_type": "gen_failed", "msg": row.get("error") or "empty", "bins": {}, "probes": {}}
        else:
            res = fut.result()
        valid = res.get("error_type") == "ok"
        bins25 = (res["bins"]["SEL-OR"] + res["bins"]["SEL-W"]) if valid else None
        F = fitness().F(bins25) if valid else None
        dv = (res.get("probes") or {}).get("P10")
        drow = None
        if key is not None and dv is not None:
            vec = np.frombuffer(dv if isinstance(dv, bytes) else bytes.fromhex(dv), dtype=np.uint16)
            drow = self.dstore.add(key, vec, fs_only=not valid)
        fs = res.get("fs")
        fsF = None
        if fs and fs.get("error_type") == "ok":
            fsF = fitness().F(fs["bins"]["SEL-OR"] + fs["bins"]["SEL-W"])
        stored = {k: v for k, v in res.items() if k not in ("probes",)}
        erow = {"seed": S, "arm": arm, "call": row["call"], "round": row["round"], "key": key, "cached": cached,
                "error_type": res.get("error_type"), "msg": (res.get("msg") or "")[:200], "valid": valid,
                "bins25": bins25, "F": F, "eval_s": res.get("eval_s"), "total_cpu_s": res.get("total_cpu_s"),
                "wall_s": res.get("wall_s"), "stochastic": sandbox.is_stochastic(row["code"]) if row["code"] else False,
                "probe_row": drow, "probe_error": res.get("probe_error"), "fs_F": fsF,
                "fs_error_type": fs.get("error_type") if fs else None, "utc": C.utc(),
                "res": (stored if (key is not None and not cached) else None)}
        if erow["res"] is not None and dv is not None:
            erow["res"]["probes"] = {"P10": dv.hex() if isinstance(dv, bytes) else dv}
        C.append_jsonl(eval_path or C.eval_append_path(), erow)
        if register and valid:
            db = self.dbs[(S, arm)]
            prog = {"pid": f"S{S}-{arm}-c{row['call']}", "code": row["code"], "F": F, "sig": bins25, "arm": arm,
                    "S": S, "call": row["call"]}
            db.register(row["island"], prog)
        return erow

    # ---------------------------------------------------------------- rounds
    async def gen_round(self, rnd: int, arm_seeds: list[tuple[int, str]]) -> list[dict]:
        jobs = []
        for S, arm in arm_seeds:
            db = self.dbs[(S, arm)]
            for slot in range(ROUND_CALLS):
                call = db.calls + slot
                island, worse, better = db.draw_parents()
                jobs.append(self.one_call(S, arm, call, rnd, slot, island, worse, better))
        rows = await asyncio.gather(*jobs)
        for S, arm in arm_seeds:
            self.dbs[(S, arm)].calls += ROUND_CALLS
        for row in rows:
            C.append_jsonl(gen_path(row["seed"]), row)
        return rows

    def status(self, extra: dict | None = None, force: bool = False) -> None:
        if not force and time.time() - self.last_status < STATUS_EVERY_S:
            return
        self.last_status = time.time()
        summ = {f"S{S}-{a}": db.state_summary() for (S, a), db in self.dbs.items()}
        C.partial_status("search", round=self.round, active=[f"S{S}-{a}" for S, a in self.active],
                         caps={f"S{S}-{a}": c for (S, a), c in self.caps.items()},
                         round_times_last5=self.round_times[-5:], backlog=self.pool.backlog(),
                         cache_hits=self.cache.hits, n_respawn=self.pool.n_respawn, dbs=summ, **(extra or {}))

    def round_monitor(self, rows: list[dict], erows: list[dict], wall: float) -> dict:
        by: dict[str, dict] = {}
        for r in rows:
            d = by.setdefault(f"S{r['seed']}-{r['arm']}", {"n": 0, "trunc": 0, "nob": 0})
            d["n"] += 1
            d["trunc"] += int(r["truncated"])
            d["nob"] += int(bool(r.get("branch", {}).get("no_branch")))
        for e in erows:
            d = by.setdefault(f"S{e['seed']}-{e['arm']}", {"n": 0, "trunc": 0, "nob": 0})
            d["valid"] = d.get("valid", 0) + int(e["valid"])
            d["dup"] = d.get("dup", 0) + int(bool(e["cached"]))
            d["ne"] = d.get("ne", 0) + 1
        m = {"round": self.round, "wall_s": round(wall, 1), "backlog": self.pool.backlog(), "by": by,
             "best_F": {f"S{S}-{a}": round(db.best()["F"], 4) for (S, a), db in self.dbs.items()}}
        C.append_jsonl(C.LOGS / "round_monitor.jsonl", m)
        return m

    async def run(self) -> None:
        pending_round = self.load_state()
        self.engine = EN.Engine(64)
        pending: list = []
        if pending_round is not None:
            # re-submit the generated-but-unregistered round from its rows
            rows = [r for S in RUN_SEEDS for r in C.read_jsonl(gen_path(S)) if r["round"] == pending_round
                    and (r["seed"], r["arm"]) in self.active and not r.get("ns")]
            done_keys = {(r["seed"], r["arm"], r["call"]) for r in C.read_eval_rows()}
            pending = [self.submit(r) for r in rows if (r["seed"], r["arm"], r["call"]) not in done_keys]
            self.mark_superseded(pending_round)
        try:
            await self.core_loop(pending)
            await self.ns_phase()
        finally:
            await self.engine.close()
            self.pool.close()
            self.status(force=True)

    def mark_superseded(self, last_round: int) -> None:
        """Rows of rounds after the last complete round are superseded (regenerated with the same seeds)."""
        for S in RUN_SEEDS:
            for r in C.read_jsonl(gen_path(S)):
                if r["round"] > last_round and not r.get("ns"):
                    C.append_jsonl(C.DATA / "superseded.jsonl", {"seed": S, "arm": r["arm"], "call": r["call"],
                                                                 "round": r["round"], "utc": C.utc()})

    def target_calls(self) -> int | None:
        return self.cfg.get("C_star")

    async def core_loop(self, pending: list) -> None:
        while True:
            # stop conditions
            cstar = self.target_calls()
            todo = [(S, a) for (S, a) in self.active
                    if (cstar is None or self.dbs[(S, a)].calls < self.caps.get((S, a), cstar))]
            est = (statistics.median(self.round_times[-5:]) if self.round_times else 60.0)
            if not todo:
                break
            if C.elapsed_h() + est / 3600 > H_HARD_STOP:
                logger.warning(f"hard stop: round {self.round + 1} would end after {H_HARD_STOP} h")
                self.events.append({"event": "hard_stop", "round": self.round, "utc": C.utc()})
                break
            rnd = self.round + 1
            t0 = time.time()
            rows = await self.gen_round(rnd, todo)
            new_pending = [self.submit(r) for r in rows]
            erows = []
            for row, key, fut, cached in pending:
                if fut is not None:
                    await asyncio.wrap_future(fut)
                erows.append(self.finish_eval(row, key, fut, cached, register=True))
            pending = new_pending
            self.round = rnd
            for (S, a) in todo:
                ev = self.dbs[(S, a)].maybe_reset()
                if ev:
                    ev.update(seed=S, arm=a, round=rnd)
                    C.append_jsonl(C.LOGS / "resets.jsonl", ev)
            wall = time.time() - t0
            self.round_times.append(wall)
            self.save_state(pending_round=rnd)
            m = self.round_monitor(rows, erows, wall)
            logger.info(f"round {rnd}: {len(rows)} calls in {wall:.1f}s, backlog {m['backlog']}, "
                        f"best F {min(m['best_F'].values()):.4f}, hits {self.cache.hits}")
            self.status()
            if rnd == 5 and "C_star" not in self.cfg:
                self.choose_cstar()
            elif rnd > 5 and rnd % 5 == 0:
                self.dynamic_rule()
        # drain the last pending round
        for row, key, fut, cached in pending:
            if fut is not None:
                await asyncio.wrap_future(fut)
            self.finish_eval(row, key, fut, cached, register=True)
        self.save_state(pending_round=None)
        C.ledger("core arms done", planned_h=4.5, round=self.round,
                 calls={f"S{S}-{a}": db.calls for (S, a), db in self.dbs.items()})

    # ---------------------------------------------------------------- C* and the dynamic rule
    def t_round(self, idx: slice) -> float:
        return float(statistics.median(self.round_times[idx]))

    def choose_cstar(self) -> None:
        tr = self.t_round(slice(2, 5))
        now_h = C.elapsed_h()
        ns_time_h = 2 * 1000 / 100 * tr / 3600 * 0.6  # NS rounds: 100 calls per seed (no branching, 1 request)

        def end_h(Cc: int, arms_scale: float = 1.0) -> float:
            return now_h + (Cc / ROUND_CALLS - 5) * tr * 1.1 * arms_scale / 3600

        decision = {"t_round_s": tr, "rounds_measured": self.round_times[:5], "now_h": now_h, "drop": []}
        cstar = None
        for Cc in CSTAR_OPTIONS:
            if end_h(Cc) <= H_CSTAR_END:
                cstar = Cc
                break
        if cstar is None:
            decision["drop"].append("NS")
            for Cc in CSTAR_OPTIONS:
                if end_h(Cc) <= H_DROP_END:
                    cstar = Cc
                    break
        if cstar is None:
            cstar = 1000
            decision["drop"].append("IDEA capped at 1000")
            for S in RUN_SEEDS:
                self.caps[(S, "IDEA")] = 1000
        decision["C_star"] = cstar
        decision["projected_end_h"] = {str(c): end_h(c) for c in CSTAR_OPTIONS}
        decision["ns_projected_h"] = ns_time_h
        self.cfg["C_star"] = cstar
        self.cfg["drop"] = decision["drop"]
        C.write_json(CFG_PATH, self.cfg)
        sys.path.insert(0, str(C.SRC))
        import commit
        commit.commit2(decision)
        logger.info(f"C* = {cstar} (t_round {tr:.1f}s; projected ends {decision['projected_end_h']})")

    def dynamic_rule(self) -> None:
        cstar = self.cfg["C_star"]
        tr = self.t_round(slice(-5, None))
        core = [(S, a) for (S, a) in self.active if a in ("T1.0", "T1.6", "DTB", "RPB")]
        rem_rounds = max((cstar - self.dbs[k].calls) / ROUND_CALLS for k in core)
        proj = C.elapsed_h() + rem_rounds * tr * 1.1 / 3600
        if proj <= H_DROP_END:
            return
        drops = self.cfg.setdefault("drop", [])
        order = ["NS", "IDEA to 1000", "IDEA off", "seed 3 to 1000"]
        nxt = next((d for d in order if d not in drops), None)
        if nxt is None:
            return
        drops.append(nxt)
        if nxt == "IDEA to 1000":
            for S in RUN_SEEDS:
                self.caps[(S, "IDEA")] = min(self.caps.get((S, "IDEA"), cstar), 1000)
        elif nxt == "IDEA off":
            self.active = [(S, a) for (S, a) in self.active if a != "IDEA"]
        elif nxt == "seed 3 to 1000":
            for a in SEARCH_ARMS:
                self.caps[(3, a)] = 1000
        C.write_json(CFG_PATH, self.cfg)
        ev = {"event": "drop", "item": nxt, "round": self.round, "projected_end_h": proj, "utc": C.utc()}
        self.events.append(ev)
        C.append_jsonl(C.LOGS / "drops.jsonl", ev)
        C.log_deviation(f"drop_{nxt}", f"dynamic rule at round {self.round}: projected core end {proj:.2f} h > "
                                       f"{H_DROP_END} h; dropped '{nxt}'")
        logger.warning(f"dynamic rule: dropped {nxt} (projected {proj:.2f} h)")

    # ---------------------------------------------------------------- NS
    async def ns_phase(self) -> None:
        if "NS" in self.cfg.get("drop", []):
            logger.info("NS dropped by the C* / dynamic rule")
            return
        done = {}
        for S in RUN_SEEDS:
            done[S] = sum(1 for r in C.read_jsonl(gen_path(S)) if r.get("ns"))
        worse, better = (self.bf, self.ff) if self.bf["F"] > self.ff["F"] else (self.ff, self.bf)
        txt, ids, psha = self.build_prompt(0, "NS", worse, better)
        per_round = 100
        while any(done[S] < 1000 for S in RUN_SEEDS):
            if C.elapsed_h() > H_HARD_STOP - 0.02:
                logger.warning("NS stopped by the hard stop")
                self.events.append({"event": "ns_hard_stop", "done": done, "utc": C.utc()})
                break
            jobs = []
            for S in RUN_SEEDS:
                for k in range(min(per_round, 1000 - done[S])):
                    call = done[S] + k
                    jobs.append(self.ns_call(S, call, worse, better))
            rows = await asyncio.gather(*jobs)
            subs = []
            for row in rows:
                C.append_jsonl(gen_path(row["seed"]), row)
                subs.append(self.submit(row))
            for row, key, fut, cached in subs:
                if fut is not None:
                    await asyncio.wrap_future(fut)
                self.finish_eval(row, key, fut, cached, register=False)
            for S in RUN_SEEDS:
                done[S] = sum(1 for r in C.read_jsonl(gen_path(S)) if r.get("ns"))
            logger.info(f"NS: {done}")
        C.ledger("NS done", planned_h=4.67, done=done)

    async def ns_call(self, S: int, call: int, worse: dict, better: dict) -> dict:
        row = await self.one_call(S, "NS", call, rnd=10000 + call // 100, slot=call % 100, island=None,
                                  worse=worse, better=better)
        row["ns"] = True
        return row


# ------------------------------------------------------------------------------------------------ smoke test
async def smoke() -> dict:
    """Seed 99: 10 calls of each of the 6 arms (discarded but logged), validity, bodies, re-derivation, cache hits."""
    s = Searcher("smoke")
    s.engine = EN.Engine(64)
    out = {"utc": C.utc(), "arms": {}}
    path = C.DATA / "smoke_s99.jsonl"
    epath = C.DATA / "smoke_eval_s99.jsonl"
    m0 = EN.metrics()
    try:
        jobs = []
        dbs = {a: IS.ArmDB(99, a, s.bf) for a in ["T1.0", "T1.6", "DTB", "RPB", "IDEA"]}
        worse_ns, better_ns = (s.bf, s.ff) if s.bf["F"] > s.ff["F"] else (s.ff, s.bf)
        for a in ["T1.0", "T1.6", "DTB", "RPB", "IDEA", "NS"]:
            for call in range(10):
                if a == "NS":
                    jobs.append(s.one_call(99, a, call, 0, call, None, worse_ns, better_ns))
                else:
                    isl, w, b = dbs[a].draw_parents()
                    jobs.append(s.one_call(99, a, call, 0, call, isl, w, b))
        t = time.time()
        rows = await asyncio.gather(*jobs)
        out["gen_wall_s"] = time.time() - t
        for r in rows:
            C.append_jsonl(path, r)
        subs = [s.submit(r) for r in rows]
        erows = []
        for row, key, fut, cached in subs:
            erows.append(s.finish_eval(row, key, fut, cached, register=False, eval_path=epath))
        out["eval_wall_s"] = time.time() - t - out["gen_wall_s"]
        for a in ["T1.0", "T1.6", "DTB", "RPB", "IDEA", "NS"]:
            rr = [r for r in rows if r["arm"] == a]
            ee = [e for e in erows if e["arm"] == a]
            out["arms"][a] = {"validity": float(np.mean([e["valid"] for e in ee])),
                              "errors": {k: sum(e["error_type"] == k for e in ee) for k in set(e["error_type"] for e in ee)},
                              "truncated": int(sum(r["truncated"] for r in rr)),
                              "mean_completion_tokens": float(np.mean([r["completion_tokens"] or 0 for r in rr])),
                              "F": [e["F"] for e in ee], "bodies": [r["code"][:600] for r in rr[:5]]}
            if a in ("DTB", "RPB"):
                re_ok, nob = [], 0
                for r in rr:
                    br = r["branch"]
                    if br.get("no_branch"):
                        nob += 1
                        continue
                    top = [[tuple(x) for x in t] for t in
                           next(x["top"] for x in C.read_jsonl(C.DATA / f"r1_tops_s99_{a}.jsonl") if x["call"] == r["call"])]
                    br2 = OP.branch_plan(s.tt, r["r1_ids"], top, 99, a, r["call"])
                    re_ok.append(br2.get("j") == br["j"] and br2.get("r") == br["r"] and br2.get("forced_id") == br["forced_id"])
                    # request 2's prompt = prompt + gen[:j] + [forced]; the program contains gen[:j] verbatim
                    pre = s.tok.decode(r["r1_ids"][:br["j"]])
                    re_ok[-1] = re_ok[-1] and r["completion"].startswith(pre)
                out["arms"][a]["rederive_ok"] = re_ok
                out["arms"][a]["no_branch"] = nob
                out["arms"][a]["j"] = [r["branch"].get("j") for r in rr]
        m1 = EN.metrics()
        out["metrics_before"], out["metrics_after"] = m0, m1
        out["cache_hits"] = s.cache.hits
    finally:
        await s.engine.close()
        s.pool.close()
    C.write_json(C.RESULTS / "smoke.json", out)
    return out


@logger.catch(reraise=True)
def main() -> None:
    C.setup_logging("search")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if not EN.wait_ready(600):
        raise RuntimeError("vLLM server is not ready")
    if cmd == "smoke":
        out = asyncio.run(smoke())
        logger.info(json.dumps({a: {k: v for k, v in d.items() if k != "bodies"} for a, d in out["arms"].items()},
                               default=str)[:4000])
    elif cmd == "run":
        asyncio.run(Searcher("run").run())


if __name__ == "__main__":
    main()
