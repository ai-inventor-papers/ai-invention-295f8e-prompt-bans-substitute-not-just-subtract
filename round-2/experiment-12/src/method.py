#!/usr/bin/env python3
"""Reading a coding ban inside the model (Qwen3-8B, protocol v2): orchestrator.

Every stage runs as its own process (vLLM and HF never share the 16 GB GPU):
  uv run method.py --stage A        # inputs check, labeller re-check (A1, A2), prompts (A3), 0e record (A4)
  uv run method.py --stage B        # layer probe + SAE readout (i) discovery on exp3 states (CPU)
  uv run method.py --stage vllm1    # C1 fresh ban pool + E5 same-seed CRN + Gumbel + determinism (GPU, vLLM)
  uv run method.py --stage vllm2    # C2-C4 thought-anchor traces, resampling, validation completions (GPU, vLLM)
  uv run method.py --stage label    # canonical labeller on every generation; commit locator (CPU)
  uv run method.py --stage hf       # E1 transfer test, E2 fresh-pool states + attention, E4 J-lens (GPU, HF)
  uv run method.py --stage analyse  # D1, D2, E3 readouts, figures (CPU)
  uv run method.py --stage anchors  # D1 thought-anchor analysis only (CPU; also part of 'analyse')
  uv run method.py --stage final    # A2 labeller check, fresh-pool + same-seed summaries, 0e record, method_out.json
  uv run method.py --stage figures  # figures/*.png|pdf from results/*.json (CPU)
  uv run method.py --stage verify   # independent re-derivation of headline numbers + placebo checks (CPU)
Baselines are implemented side by side with each readout (DiM, raw logistic probe, top-20 raw dimensions,
different-seed CRN baseline, logit lens), on identical folds/rows.
"""

from __future__ import annotations

import os

# The cgroup quota is ~5 CPUs while os.cpu_count() reports 48 host cores: cap every BLAS / OpenMP pool
# BEFORE numpy/torch load, or the oversubscribed thread pools are throttled ~100x.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "4")
os.environ.setdefault("CC", os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", "zigcc"))

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from loguru import logger  # noqa: E402

from core import setup_logging  # noqa: E402


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--n", type=int, default=None)
    ap.add_argument("--part", default="traces", help="vllm2 sub-stage: traces | resample | complete")
    args = ap.parse_args()
    setup_logging(f"stage_{args.stage}")
    logger.info(f"stage {args.stage} (smoke={args.smoke})")
    if args.stage == "A":
        from stage_a import run_stage_a

        run_stage_a()
    elif args.stage == "B":
        from readout_i import run_stage_b

        run_stage_b()
    elif args.stage == "vllm1":
        from vllm_stage import session1

        session1(n_per_template=args.n or int(os.environ.get('C1_PER_TEMPLATE', 20)),
                 n_seeds=int(os.environ.get('CRN_SEEDS_N', 30)), gumbel_seeds=int(os.environ.get('GUMBEL_SEEDS_N', 0)),
                 smoke=args.smoke)
    elif args.stage == "vllm2":
        from anchors_stage import session2

        session2(part=args.part, n=args.n, smoke=args.smoke)
    elif args.stage == "label":
        from labelling import run_stage_label

        run_stage_label()
    elif args.stage == "hf":
        from hf_stage import run_stage_hf

        run_stage_hf(smoke=args.smoke)
    elif args.stage == "analyse":
        from analysis import run_stage_analyse

        run_stage_analyse()
    elif args.stage == "anchors":
        from analysis import thought_anchors

        thought_anchors()
    elif args.stage == "figures":
        from figures import run_figures

        run_figures()
    elif args.stage == "verify":
        import runpy

        runpy.run_path(str(Path(__file__).resolve().parent / "src" / "verify_headlines.py"), run_name="__main__")
    elif args.stage == "final":
        from final import run_stage_final

        run_stage_final()
    else:
        raise SystemExit(f"unknown stage {args.stage}")


if __name__ == "__main__":
    main()
