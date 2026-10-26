#!/usr/bin/env python3
"""Where an algorithm ban takes effect: KV-cache splice route test (C2) + compliance-at-R test (C5) on Qwen3-8B.

Entry point. Each stage is a subcommand so GPU stages run as separate processes (vLLM and HF never share one):

  uv run method.py s0        # snapshot iteration-1 inputs, suite copy, labeller re-check
  uv run method.py s1        # frozen prompts, neutral twins, length matching, forced prompts
  uv run method.py s2        # FRLP programs (HF sampler, fallback F2), labelling, name scrub
  uv run method.py prereg    # hash-commit decision rules + frozen prompts + analysis.py BEFORE any arm is scored
  uv run method.py tests     # U0-U9 engine/sampler/knockout/analysis tests (results/tests.json)
  uv run method.py s4        # behaviour, common random numbers (HF)
  uv run method.py s4label   # canonical labeller on the behaviour samples (CPU)
  uv run method.py s5        # FRLP scoring of every arm (HF)
  uv run method.py s6        # logit lens (+ tuned lens) at the commitment token
  uv run method.py s7        # C5: compliance at R across iteration-1 wordings
  uv run method.py s8        # analysis + frozen decision (analysis.py)
  uv run method.py s9        # method_out.json, figures
"""

from __future__ import annotations

import sys
import time

from loguru import logger

from cfg import RESULTS_DIR, read_jsonl, setup_logging, utc_now, write_json, append_jsonl

STAGE_LOG = RESULTS_DIR / "stage_times.jsonl"


def _time(stage: str, fn) -> None:
    t0 = time.time()
    logger.info(f"=== stage {stage} start")
    fn()
    dt = time.time() - t0
    append_jsonl(STAGE_LOG, [{"stage": stage, "seconds": round(dt, 1), "utc": utc_now()}])
    logger.info(f"=== stage {stage} done in {dt / 60:.1f} min")


def s0() -> None:
    from snapshot import stage_labeller_recheck, stage_snapshot

    snap = stage_snapshot()
    write_json(RESULTS_DIR / "snapshot.json", snap)
    stage_labeller_recheck()


def s1() -> None:
    from build_prompts import stage_prompts

    stage_prompts()


def s2() -> None:
    from gen_programs import stage_programs

    stage_programs()


def prereg() -> None:
    from build_prompts import stage_prereg

    stage_prereg()


def tests() -> None:
    from tests.run_tests import run_all

    res = run_all()
    critical = {
        "U3 splice identity": all(v["splice_ban_ban_identical"] and v["splice_neu_neu_identical"]
                                  for v in res["U3"].values()),
        "U3 empty-span KO": all(v["empty_ok"] for v in res["U3"].values()),
        "U3 prefill vs single pass (<0.05 nats)": all(max(v["prefill_vs_single_pass_mean_abs"]) < 0.05
                                                      for v in res["U3"].values()),
        "U4 blocked mass": res["U4"].get("blocked_ok", False),
        "U2 alignment": res["U2"]["all_ok"],
    }
    res["critical"] = critical
    write_json(RESULTS_DIR / "tests.json", res)
    bad = [k for k, v in critical.items() if not v]
    if bad:
        raise RuntimeError(f"critical tests failed: {bad}")
    logger.info(f"critical tests passed: {critical}")


def s4() -> None:
    from behaviour import stage_behaviour

    stage_behaviour()


def s4label() -> None:
    from behaviour import stage_label_behaviour

    stage_label_behaviour()


def s5() -> None:
    from frlp import stage_frlp

    stage_frlp()


def s6() -> None:
    from lens import stage_lens

    stage_lens()


def s7() -> None:
    from c5 import stage_c5

    stage_c5()


def s8() -> None:
    from analysis import stage_analysis

    stage_analysis()


def s9() -> None:
    from outputs import stage_outputs

    stage_outputs()


STAGES = {"s0": s0, "s1": s1, "s2": s2, "prereg": prereg, "tests": tests, "s4": s4, "s4label": s4label, "s5": s5,
          "s6": s6, "s7": s7,
          "s8": s8, "s9": s9}


@logger.catch(reraise=True)
def main() -> None:
    args = sys.argv[1:] or ["s8", "s9"]
    for a in args:
        if a not in STAGES:
            raise SystemExit(f"unknown stage {a}; choose from {list(STAGES)}")
    setup_logging("method_" + "_".join(args))
    for a in args:
        _time(a, STAGES[a])


if __name__ == "__main__":
    main()
