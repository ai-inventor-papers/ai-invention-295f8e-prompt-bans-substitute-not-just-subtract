#!/usr/bin/env python3
"""Do a few early tokens decide the algorithm? -- orchestrator for the whole screen.

Phases (each is resumable; outputs are checkpointed under generations/, summaries/, states/):
  gen1      vLLM process: engine tests T4/T5, S6 pools (staged: 1 paraphrase, then all 10)
  gen2      vLLM process: S7 screen, S8 change points, S9 localise + confirm, S10 prompt swap, S11 knob
  states    HF process:   S12 residual states at 8 positions x layers 8..28
  analysis  CPU:          judge adjudication, probes, S13 readouts, verdict, figures, method_out.json
Usage: .venv/bin/python method.py --phase gen1|gen2|states|analysis
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from loguru import logger  # noqa: E402

from common import LOG_DIR, log_hash, setup_logging  # noqa: E402


def _ram_limit(gb: float) -> None:
    try:
        resource.setrlimit(resource.RLIMIT_AS, (int(gb * 1024 ** 3), int(gb * 1024 ** 3)))
    except (ValueError, OSError) as e:
        logger.warning(f"could not set RLIMIT_AS: {e}")


def _prompts(tok) -> dict:
    from prompts.build_prompts import build
    p = ROOT / "prompts" / "prompts.json"
    if not p.exists():
        p.write_text(json.dumps(build(tok), indent=1))
        log_hash("prompts", p)
    return json.loads(p.read_text())


def _ensure_prereg() -> None:
    hl = LOG_DIR / "hashes.log"
    if not hl.exists() or "prereg" not in hl.read_text():
        log_hash("prereg", ROOT / "prereg.json")


@logger.catch(reraise=True)
def phase_gen1() -> None:
    from transformers import AutoTokenizer

    from gen.engine import load_engine
    from gen.stages_pool import run_s6, run_t45
    from harness.pool import LabelPool
    _ensure_prereg()
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B")
    prompts = _prompts(tok)
    pool = LabelPool(workers=5)
    llm = load_engine()
    t0 = time.time()
    if not (LOG_DIR / "test_engine.json").exists():
        run_t45(llm, tok, prompts, pool)
    run_s6(llm, tok, prompts, pool, stage_tag="stage1", limit_paras=1)
    logger.info(f"S6 stage1 done at {time.time() - t0:.0f}s")
    run_s6(llm, tok, prompts, pool, stage_tag="full")
    logger.info(f"S6 full done at {time.time() - t0:.0f}s")
    pool.shutdown()


@logger.catch(reraise=True)
def phase_gen2() -> None:
    from transformers import AutoTokenizer

    from gen.engine import load_engine
    from gen.stages_screen import run_gen2
    from harness.pool import LabelPool
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B")
    prompts = _prompts(tok)
    pool = LabelPool(workers=5)
    llm = load_engine()
    run_gen2(llm, tok, prompts, pool)
    pool.shutdown()


@logger.catch(reraise=True)
def phase_states() -> None:
    from analysis.states import run_states
    run_states()


@logger.catch(reraise=True)
def phase_analysis() -> None:
    from analysis.final import run_analysis
    run_analysis()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="analysis", choices=["gen1", "gen2", "states", "analysis"])
    args = ap.parse_args()
    setup_logging(f"method_{args.phase}")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    if args.phase == "analysis":  # CUDA needs large virtual reservations: no RLIMIT_AS on GPU phases
        _ram_limit(40)
    logger.info(f"phase {args.phase} start")
    {"gen1": phase_gen1, "gen2": phase_gen2, "states": phase_states, "analysis": phase_analysis}[args.phase]()
    logger.info(f"phase {args.phase} done")


if __name__ == "__main__":
    main()
