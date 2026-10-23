#!/usr/bin/env python3
"""GPU stages (one model per process): Stage 0 (engine tests U1-U8, twins), Stage 1 (blind locator), Stage 2 (token
maps), Stage 3 (arms), Stage 4 (HR). Every stage resumes from its jsonl rows (keyed by sid).

Usage: gpu8.py qwen|gemma <stage>[,<stage>...] [--units T10,B3,...]
"""

from __future__ import annotations

import argparse
import gc
import sys
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg8 import (CACHE_DIR, CONTS, PRED_DIR, PRECISION, QWEN_UNITS, RESULTS_DIR, SAMPLES, TEMPLATES, UNITS,  # noqa
                  append_jsonl, read_json, read_jsonl, set_ram_limit, setup_logging, slot_template, slot_ukey,
                  u_stream, utc_now, write_json, log_timing, log_deviation)
import engine8 as EN  # noqa: E402
import units8 as U8  # noqa: E402

HID_DIR = CACHE_DIR / "hid"
HID_DIR.mkdir(parents=True, exist_ok=True)
SCHED_KEYS = ("T", "top_p", "top_k", "min_p", "edt", "adapt", "openings", "dose", "dose2", "force_dec", "fixed_pos",
              "window", "prefix", "fence")
LIGHT_DROP = ("entropy", "dec_top_ids", "dec_top_z", "modified_steps")


class Runner:
    def __init__(self, flavor: str):
        self.flavor = flavor
        if flavor == "qwen":
            self.tok, self.model, self.info = EN.load_qwen()
        else:
            self.tok, self.model, self.info = EN.load_gemma()
        self.pre: dict[tuple[str, str], dict[str, Any]] = {}
        self.gpu = self.info["gpu"]

    def prefill(self, unit: str, w: str) -> dict[str, Any]:
        k = (unit, w)
        if k not in self.pre:
            self.pre[k] = EN.prefill(self.model, U8.prompt_ids(unit, w))
        return self.pre[k]

    def clear(self) -> None:
        self.pre.clear()
        gc.collect()
        torch.cuda.empty_cache()

    def run(self, specs: list[dict[str, Any]], tag: str, out: Path = SAMPLES, light: bool = False,
            stop_fn_factory: Callable[[list[dict[str, Any]]], Callable] | None = None,
            batch: int | None = None, per_template: bool | None = None) -> list[dict[str, Any]]:
        """Generate every spec not yet in `out`; batches are template-grouped (Gemma: one template per batch)."""
        have = {r["sid"] for r in read_jsonl(out)}
        todo = [s for s in specs if s["sid"] not in have]
        if not todo:
            return []
        unit = todo[0]["unit"]
        B = batch or UNITS[unit]["batch"]
        pt = (self.flavor == "gemma") if per_template is None else per_template
        groups: list[list[dict[str, Any]]] = []
        if pt:
            for w in TEMPLATES:
                g = [s for s in todo if s["w"] == w]
                groups += [g[i:i + B] for i in range(0, len(g), B)]
        else:
            todo = sorted(todo, key=lambda s: TEMPLATES.index(s["w"]))
            groups = [todo[i:i + B] for i in range(0, len(todo), B)]
        allrecs = []
        for gi, part in enumerate(groups):
            t0 = time.time()
            rows = []
            for s in part:
                r = {"pre": self.prefill(s["unit"], s["w"]), "max_new": s["max_new"],
                     "u": s["u"] if s.get("u") is not None else u_stream(*s["ukey"])}
                for k in SCHED_KEYS:
                    if k in s:
                        r[k] = s[k]
                rows.append(r)
            stop_fn = stop_fn_factory(part) if stop_fn_factory else None
            fk = UNITS[part[0]["unit"]]["fence"]
            oom = False
            try:
                res = EN.decode_k1(self.model, self.tok, rows, fence_kind=fk, stop_fn=stop_fn)
            except torch.cuda.OutOfMemoryError:
                oom = True                 # handled OUTSIDE the except block: its traceback pins the batch tensors
            if oom:
                del rows
                gc.collect()
                torch.cuda.empty_cache()
                half = max(1, len(part) // 2)
                logger.warning(f"OOM at B={len(part)}; retrying as 2 x {half}")
                self.run(part[:half], tag, out, light, stop_fn_factory, batch=half, per_template=pt)
                self.run(part[half:], tag, out, light, stop_fn_factory, batch=half, per_template=pt)
                continue
            dt = time.time() - t0
            recs, hids, hsids = [], [], []
            for s, r in zip(part, res):
                rec = {k: v for k, v in s.items() if k not in ("u", "openings", "prefix", "force_dec", "dose2",
                                                               "fixed_pos", "window", "edt", "adapt", "dose")}
                rec["schedule"] = {k: s[k] for k in ("dose", "dose2", "fixed_pos", "window", "edt", "adapt",
                                                     "force_dec") if s.get(k) is not None}
                if s.get("prefix") is not None:
                    rec["prefix_len"] = len(s["prefix"])
                if "dose2" in rec["schedule"]:
                    rec["schedule"]["dose2"] = {**s["dose2"], "tokens": sorted(int(t) for t in s["dose2"]["tokens"])}
                rec.update({k: v for k, v in r.items() if k != "hid_mean"})
                rec["ukey"] = list(s["ukey"]) if s.get("ukey") is not None else None
                rec["text"] = self.tok.decode(r["token_ids"], skip_special_tokens=True)
                rec["n_new_tokens"] = r["n_tokens"]
                rec["decision_token_str"] = (self.tok.decode([r["decision_token"]])
                                             if r["decision_token"] is not None else None)
                rec["model"] = self.info["model"]
                rec["precision"] = PRECISION
                rec["gpu"] = self.gpu
                rec["prompt_sha256"] = U8.prompt_sha(s["unit"], s["w"])
                rec["batch_B"] = len(part)
                rec["utc"] = utc_now()
                if light:
                    for k in LIGHT_DROP:
                        rec.pop(k, None)
                recs.append(rec)
                if r.get("hid_mean") is not None and not light:
                    hids.append(r["hid_mean"])
                    hsids.append(s["sid"])
            append_jsonl(out, recs)
            if hids:
                np.savez_compressed(HID_DIR / f"{tag}_{int(time.time() * 1000)}.npz", sids=np.array(hsids),
                                    H=np.stack(hids).astype(np.float16))
            steps = max(r["steps"] for r in res)
            log_timing(tag, rows=len(part), steps=steps, seconds=round(dt, 2), unit=unit,
                       s_per_program=round(dt / len(part), 3))
            logger.info(f"{tag} batch {gi + 1}/{len(groups)}: {len(part)} rows, {steps} steps, {dt:.1f}s "
                        f"({1000 * dt / max(steps, 1):.0f} ms/step)")
            allrecs += recs
        return allrecs


# ------------------------------------------------------------------------------------------------ specs
def openings_of(unit: str) -> list[list[int]]:
    return [n["opening"] for n in U8.nodes(unit)]


def twin_spec(unit: str, s: int, arm: str = "A0", stage: str = "S0", **kw: Any) -> dict[str, Any]:
    sp = {"sid": f"{unit}|{arm}|{s}", "unit": unit, "arm": arm, "stage": stage, "slot": s, "w": slot_template(s),
          "ukey": slot_ukey(unit, s), "max_new": UNITS[unit]["max_new"], "T": 1.0, "openings": openings_of(unit)}
    sp.update(kw)
    return sp


def tok_id(tok: Any, s: str) -> int:
    ids = tok.encode(s, add_special_tokens=False)
    assert len(ids) == 1, f"{s!r} is not one token: {ids}"
    return ids[0]


# ------------------------------------------------------------------------------------------------ stage 0
def stage0_qwen(R: Runner, units: list[str]) -> None:
    hw = {"gpu": R.gpu, **R.info, "torch": torch.__version__, "utc": utc_now(),
          "cuda": torch.version.cuda, "batch_sizes": {u: UNITS[u]["batch"] for u in QWEN_UNITS},
          "max_new": {u: UNITS[u]["max_new"] for u in QWEN_UNITS}, "planned_gpu": "RTX A4500 (20 GB)"}
    write_json(PRED_DIR / "hardware.json", hw)
    # twins first on T10 (fast) to time the engine, then the rest
    for u in units:
        if UNITS[u]["model"] != "qwen":
            continue
        t0 = time.time()
        R.run([twin_spec(u, s) for s in range(50)], f"S0_twin_{u}")
        logger.info(f"twin {u} done in {time.time() - t0:.0f}s")
        R.clear()
    tok = R.tok
    tw = {r["slot"]: r for r in read_jsonl(SAMPLES) if r["unit"] == "T10" and r["arm"] == "A0"}
    # U1 CRN determinism (T10 W1 slots): batch 1 (3 slots), batch 8 (8 slots) vs the twin batch
    specs = [twin_spec("T10", s, arm="U1b1", stage="S0_test") for s in range(3)]
    R.run(specs, "S0_U1_b1", batch=1)
    specs = [twin_spec("T10", s, arm="U1b8", stage="S0_test") for s in range(8)]
    R.run(specs, "S0_U1_b8", batch=8)
    # U2a identity: dose T = 1 (no truncation) at n10 on 20 slots; U2b/U3: dose 15 top-20 on 20 slots
    R.run([twin_spec("T10", s, arm="U2a", stage="S0_test", dose={"T": 1.0, "k": 0}) for s in range(20)], "S0_U2a")
    R.run([twin_spec("T10", s, arm="U2b", stage="S0_test", dose={"T": 15.0, "k": 20}) for s in range(20)], "S0_U2b")
    # U7 forced-token path
    d_dfs, d_find = tok_id(tok, " dfs"), tok_id(tok, " find")
    R.run([twin_spec("T10", s, arm="U7dfs", stage="S0_test", force_dec={0: [U8.T10_DEF, d_dfs]})
           for s in range(10)], "S0_U7dfs")
    R.run([twin_spec("T10", s, arm="U7find", stage="S0_test", force_dec={0: [U8.T10_DEF, d_find]})
           for s in range(10)], "S0_U7find")
    R.clear()
    logger.info(f"stage0 qwen done; T10 twin rows {len(tw)}")


def stage0_gemma(R: Runner) -> None:
    write_json(PRED_DIR / "hardware_gemma.json", {"gpu": R.gpu, **R.info, "utc": utc_now()})
    R.run([twin_spec("G", s) for s in range(50)], "S0_twin_G")
    # U8: force 53227 (' visited') and 15204 (' queue') at the decision on 5 slots each
    R.run([twin_spec("G", s, arm="U8visited", stage="S0_test", force_dec={0: [53227]}) for s in range(5)],
          "S0_U8v")
    R.run([twin_spec("G", s, arm="U8queue", stage="S0_test", force_dec={0: [15204]}) for s in range(5)],
          "S0_U8q")
    R.clear()


# ------------------------------------------------------------------------------------------------ main
STAGES: dict[str, Callable] = {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("model", choices=["qwen", "gemma"])
    ap.add_argument("stages")
    ap.add_argument("--units", default="")
    args = ap.parse_args()
    setup_logging(f"gpu8_{args.model}")
    set_ram_limit(40)
    units = [u for u in args.units.split(",") if u] or (list(QWEN_UNITS) if args.model == "qwen" else ["G"])
    R = Runner(args.model)
    t0 = time.time()
    for st in args.stages.split(","):
        ts = time.time()
        logger.info(f"=== stage {st} ({args.model}) units={units}")
        if st == "s0":
            stage0_qwen(R, units) if args.model == "qwen" else stage0_gemma(R)
        else:
            STAGES[st](R, units)
        log_timing(f"stage_{st}_{args.model}", seconds=round(time.time() - ts, 1))
    log_timing(f"process_{args.model}_{args.stages}", seconds=round(time.time() - t0, 1),
               load_seconds=R.info.get("load_seconds"))


if __name__ == "__main__":
    import stages8  # noqa: F401,E402  (registers stages s1-s4 into STAGES)
    STAGES.update(stages8.STAGES)
    main()
