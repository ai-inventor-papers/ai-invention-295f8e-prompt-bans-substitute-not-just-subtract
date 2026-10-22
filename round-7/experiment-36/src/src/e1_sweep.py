#!/usr/bin/env python3
"""E1 (exploratory, NOT pre-registered; run after COMMIT #2): dose sweep of the ban-free unit. D3 (U_bf x S4) at
alpha 3, 4 and 6 on T10 and T2 (W1-W5 x k 0-9), same runner, same slots, uniforms and per-slot directions as the S1
cells (the S4 seed of a slot at alpha >= 2 is its alpha-2 seed, so only the dose changes). Question: does the ban-free
profile reach U_abs's escape share once its realised downstream displacement matches, and at what pass cost?

usage: .venv/bin/python src/e1_sweep.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

import k_cfg as K  # noqa: E402
import gen_k as G  # noqa: E402


@logger.catch(reraise=True)
def main() -> None:
    K.setup_logging("e1_sweep")
    tok, model = G.load_model(fp8=False, vram_fraction=0.97)
    prompts = G.load_prompts()
    B = K.read_json(G.STATE)["B"]
    run = G.RunnerK(model, tok, prompts, B)
    for t in ("T10", "T2"):
        run.run_cells(t, [("D3_a3", K.K10), ("D3_a4", K.K10), ("D3_a6", K.K10)], "E1_sweep")
    K.write_json(K.RESULTS / "e1_done.json", {"utc": K.utc_now()})


if __name__ == "__main__":
    main()
