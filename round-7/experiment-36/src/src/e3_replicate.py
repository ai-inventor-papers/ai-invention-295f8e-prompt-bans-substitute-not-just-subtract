#!/usr/bin/env python3
"""E3 (exploratory, NOT pre-registered; hash-committed before its first row): an internal replication and a
generality check of the S1/S2 answers with spare GPU time.

  (a) fresh slots: T10 alpha 2, k 10-19 x W1-W5 (N 50 slots never used by S1/S2) for D1-D5 and P_top/P_rest/P_shuf;
  (b) third task: T03 alpha 2, k 0-9, D2/D3/D4 (D1_a2 already exists from S3), completing a T03 2x2.
Same runner, uniforms and seeds as S1 (S4/S5 directions of each slot).

usage: .venv/bin/python src/e3_replicate.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

import k_cfg as K  # noqa: E402
import gen_k as G  # noqa: E402

K_FRESH = list(range(10, 20))


@logger.catch(reraise=True)
def main() -> None:
    K.setup_logging("e3_replicate")
    tok, model = G.load_model(fp8=False, vram_fraction=0.97)
    prompts = G.load_prompts()
    B = K.read_json(G.STATE)["B"]
    run = G.RunnerK(model, tok, prompts, B)
    run.run_cells("T10", [("TWIN", K_FRESH), ("D1_a2", K_FRESH), ("D2_a2", K_FRESH), ("D3_a2", K_FRESH),
                          ("D4_a2", K_FRESH), ("D5_a2", K_FRESH), ("PTOP_a2", K_FRESH), ("PREST_a2", K_FRESH),
                          ("PSHUF_a2", K_FRESH)], "E3_fresh")
    run.run_cells("T03", [("D2_a2", K.K10), ("D3_a2", K.K10), ("D4_a2", K.K10)], "E3_T03")
    K.write_json(K.RESULTS / "e3_done.json", {"utc": K.utc_now()})


if __name__ == "__main__":
    main()
