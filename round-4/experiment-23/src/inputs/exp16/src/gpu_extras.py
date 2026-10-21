#!/usr/bin/env python3
"""Extras queue (beyond the plan; run after the main GPU queue, while GPU budget remained):
E1 placebo splice (pl vs b under noun B, N = 50) and knockout-mechanics control K0b (N = 50) on every gated task
   (the plan ran them on the first three only);
E2 an independent second CRN draw of the four route arms on gated tasks: slots k = 20-39 with fresh uniforms, arms
   named 'a@r2', 'b@r2', 'c@r2', 'd@r2' so the committed N = 100 confirmatory analysis is untouched; it is analysed as a
   replication in src/replication.py;
E3 a prefill DEPTH sweep (Qi et al.'s probe, which the plan dropped for budget): the default's modal baseline program
   forced up to 25%, 50% and 75% of its response tokens, under the ban and under the twin (N = 50 each), gated tasks.
Same engine, batch size and shape classes as the main queue."""

from __future__ import annotations

import os
import time
from typing import Any

from loguru import logger

from cfg import RESULTS_DIR, STAGE_A, WORK_DIR, read_json, utc_now, write_json
from gpu import TIMING, Worker, specs


class XWorker(Worker):
    depth_ids: dict[str, dict[str, list[int]]] = {}

    def prefix_ids(self, task: str, pf: str) -> list[int]:
        if pf.startswith("D") and pf[1:].isdigit():
            return self.depth_ids[task][pf]
        return super().prefix_ids(task, pf)

    def shape_of(self, task: str, w: str, arm: str) -> tuple[int, int]:
        return super().shape_of(task, w, arm.split("@")[0])

    def arm_state(self, task: str, w: str, arm: str) -> dict[str, Any]:
        return super().arm_state(task, w, arm.split("@")[0])

    def veto_for(self, task: str, arm: str) -> dict[str, Any] | None:
        return super().veto_for(task, arm.split("@")[0])

    def stage_time(self, name: str, t0: float, n: int) -> None:
        """Extras keep their own timing file (the main queue's results/timing.json is not touched)."""
        dt = time.time() - t0
        TIMING["stages"][name] = {"s": dt, "rows": n, "utc_end": utc_now()}
        write_json(RESULTS_DIR / "timing_extras.json", TIMING)
        logger.info(f"stage {name}: {n} rows in {dt / 60:.1f} min; remaining budget {self.remaining() / 60:.1f} min")


def run(B: int, deadline: float | None, prune_after: int | None) -> None:
    W = XWorker(B, deadline, prune_after)
    gate = read_json(RESULTS_DIR / "gate.json")
    gated = [t for t in STAGE_A if gate[t]["gated"]]
    done_ctrl = {"T03", "T04", "T06"}
    t0 = time.time()
    n = W.run_rows("E1", specs([t for t in gated if t not in done_ctrl], [("pl", range(10)), ("bB", range(10))]) +
                   specs([t for t in gated if t not in done_ctrl], [("K0b", range(10))]), est_steps=150)
    W.stage_time("E1", t0, n)
    t0 = time.time()
    ks = range(20, 40)
    n = W.run_rows("E2", specs(gated, [("a@r2", ks), ("c@r2", ks)]) + specs(gated, [("d@r2", ks), ("b@r2", ks)]),
                   est_steps=300)
    W.stage_time("E2", t0, n)
    # E3 prefill depth sweep
    import collections

    from cfg import PRED_DIR, resp_ids
    from forecast_s2 import baseline_codes

    depth = {}
    for t in gated:
        codes, _ = baseline_codes(t)
        modal = collections.Counter(codes).most_common(1)[0][0]
        ids = resp_ids(W.tok, modal)
        depth[t] = {f"D{int(f * 100)}": ids[:max(3, int(round(f * len(ids))))] for f in (0.25, 0.5, 0.75)}
    W.depth_ids = depth
    write_json(PRED_DIR / "prefill_depths.json", {t: {k: {"ids": v, "text": W.tok.decode(v), "n": len(v)}
                                                      for k, v in d.items()} for t, d in depth.items()})
    t0 = time.time()
    sp = []
    for pf in ("D25", "D50", "D75"):
        sp += specs(gated, [(f"BAN+{pf}", range(10)), (f"TWIN+{pf}", range(10))])
    n = W.run_rows("E3", sp, est_steps=250)
    W.stage_time("E3", t0, n)
    TIMING["extras"] = True
    write_json(RESULTS_DIR / "timing_extras.json", TIMING)
    (WORK_DIR / "gpu_extras_done").write_text(utc_now())
    logger.info("extras queue complete")


if __name__ == "__main__":
    from cfg import setup_logging

    setup_logging("gpu_extras")
    dl = os.environ.get("BRT_GPU_DEADLINE")
    run(int(os.environ.get("BRT_BATCH", "40")), float(dl) if dl else None, int(os.environ.get("BRT_PRUNE_AFTER", "560")))
