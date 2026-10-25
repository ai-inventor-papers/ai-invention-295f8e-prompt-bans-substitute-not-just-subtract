#!/usr/bin/env python3
"""NOV-R (iteration 10): do banned online-bin-packing rules come back renamed?

Stage CLI; every stage is resumable from its JSON/JSONL checkpoints.
  s0  setup: hardware, input hashes, OpenRouter key, smoke calls
  s1  harness gate G-HARNESS (U1, U2)
  s3  probe set P10 (U3)              (s2, the catalogue references, is exercised by s1's U2 and s5)
  s45 corpus + instrument gate G-INSTR (U9)
  s6  prompts, unit tests U4-U8/U10, commit #1
  s7  engine smoke tests (local vLLM, OpenRouter naming check with thinking off)
  s8  sampling orchestrator (BASE -> frequency order -> commit #2_m -> ban/described/held-out/instruction cells)
  s9  evaluation consumer (runs beside s8)
  s10 analysis (P1, P2, P3, rename table, reasoning, sensitivities) + figures
  s11 P3 audit (judges only if candidates), optional naming quotes, positioning file
  s12 outputs: data/samples.jsonl, method_out.json (+ mini/preview), rederive audit
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from loguru import logger  # noqa: E402

from common import setup_logging, write_json, RESULTS  # noqa: E402


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--no-smoke", action="store_true")
    ap.add_argument("--probe", default="P10")
    ap.add_argument("--models", default="q8,q32,q14")
    args = ap.parse_args()
    setup_logging(f"method_{args.stage}")
    st = args.stage
    if st == "s0":
        import stages_prep
        stages_prep.s0_setup(smoke=not args.no_smoke)
    elif st == "s1":
        import stages_prep
        r = stages_prep.s1_harness()
        if not r["G_HARNESS_PASS"]:
            raise SystemExit("G-HARNESS FAILED")
    elif st == "s3":
        import stages_prep
        stages_prep.s3_probes()
    elif st == "s45":
        import stages_prep
        r = stages_prep.s4_s5(probe=args.probe)
        write_json(RESULTS / f"s45_summary_{args.probe}.json", r)
    elif st == "s6":
        import stages_commit
        stages_commit.s6_commit1()
    elif st == "s7":
        import stages_commit
        stages_commit.s7_engines()
    elif st == "s8":
        import orchestrate
        orchestrate.run(models=args.models.split(","))
    elif st == "s9":
        import evalq
        evalq.run_forever()
    elif st == "s10":
        import analysis
        import figures
        analysis.run_all()
        figures.run_all()
    elif st == "s11":
        import judges
        judges.run_all()
    elif st == "s12":
        import outputs
        outputs.run_all()
    else:
        raise SystemExit(f"unknown stage {st}")


if __name__ == "__main__":
    main()
