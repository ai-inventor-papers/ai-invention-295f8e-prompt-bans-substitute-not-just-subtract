#!/usr/bin/env python3
"""amendment1 (run after commit1, before the base stage): generate Qwen3-8B-Base BINT intents up to the Level-2 N
(T2/T03 2,000, A3 500). Intents are stage-1 material; indices beyond the committed N are unused unless a later amendment
raises N before those samples. (Executed inline in the original session; this script writes the same record.)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PRED, commit, setup_logging, utc_now, write_json  # noqa: E402

setup_logging("amend1")
write_json(PRED / "amendment1.json", {
    "utc": utc_now(), "bint_intents_generated": {"T2": 2000, "T03": 2000, "A3": 500},
    "reason": "Level-2 headroom: base intents are stage-1 material generated once by Qwen3-8B-Base (one 8B model on the "
              "GPU at a time); indices beyond the committed N are unused unless a later amendment raises N before those samples",
    "engine_note": "vLLM fell back to enforce_eager=True (no C compiler for torch inductor in the container); measured "
                   "throughput far above plan"})
commit([PRED / "amendment1.json"], "amendment1", "before base intents")
