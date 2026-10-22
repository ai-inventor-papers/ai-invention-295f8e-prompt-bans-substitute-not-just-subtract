#!/usr/bin/env python3
"""Optional arm (i), reduced: T1 thinking on (vLLM), 10 seeds (W1-W5 x k 0-1) x T {0.3, 0.7, 1.0, 1.3}, no repeat.
Wrapper around the committed src/vllm_think.py (unchanged): same engine, prompts, two-pass thinking and seeds.
Run with .venv_vllm/bin/python src/vllm_t1.py, only when >= 1.5 h of wall clock remain before the analysis guard."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import vllm_think as V  # noqa: E402  (sets the vLLM env defaults on import)
from loguru import logger  # noqa: E402

if __name__ == "__main__":
    (ROOT / "logs").mkdir(exist_ok=True)
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(ROOT / "logs" / "vllm_t1.log"), rotation="30 MB", level="DEBUG")
    from memwatch import MemWatchRSS
    MemWatchRSS(26.0).start()
    tok = V.load_tok()
    llm, info = V.make_llm()
    V.stage_g1(llm, tok, info, "T1", None, ks=(0, 1), with_repeat=False)
    logger.info("optional arm (i) done")
