#!/usr/bin/env python3
"""Where a coding ban takes effect, on 12 frozen bench tasks (Qwen3-8B bf16, thinking off).

Entry point for every stage. The method is the CRN-coupled KV-splice route test (arms c = prompt route,
d = direct route, K0 = condition-span knockout) plus the one-shot veto (V1) and prefill probes; the baselines are
the clean/corrupted endpoints (a = full ban, b = token-length-matched neutral twin) sampled in the same pipeline with
the same uniforms, plus the placebo splice and the knockout-mechanics control.

  uv run method.py s0        # snapshot inputs read-only + verify bench sha256 (results/input_hashes.json)
  uv run method.py recheck   # S0.5 labeller re-check (results/labeller_recheck.json)
  uv run method.py s1        # S1 prompts with alignment assertions (prompts/prompts.jsonl)
  uv run method.py s2        # S2 frozen forecast objects (predictions/*.json)
  uv run method.py tests     # CPU tests T3-T5 (results/tests_cpu.json)
  uv run method.py label     # label worker (streams data/samples_raw.jsonl -> data/samples.jsonl)
  uv run method.py gpu       # GPU queue S3.2 -> S4 -> screen -> U-tests -> commit #2 -> S6/Q1 -> gate -> Q2 -> Q4 -> S8
  uv run method.py close1    # append the analysis code to commit #1 (releases the GPU queue's ban-prompt gate)
  uv run method.py analysis  # S9 (results/*.json)
  uv run method.py figures   # figures/*.png|pdf
  uv run method.py outputs   # method_out.json (+ full/mini/preview), results/deviations.json
  uv run method.py audit     # audit/rederive.py (results/rederive.json)

`label` and `gpu` run concurrently (two terminals or background jobs); the GPU queue waits for the labels it needs.
Environment: BRT_BATCH (default 40), BRT_PRUNE_AFTER (560), BRT_GPU_DEADLINE (epoch seconds, optional).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "analysis"))

from loguru import logger  # noqa: E402

from cfg import setup_logging  # noqa: E402


def _tok():
    from transformers import AutoTokenizer

    from cfg import model_path

    return AutoTokenizer.from_pretrained(model_path())


@logger.catch(reraise=True)
def main() -> None:
    stage = sys.argv[1] if len(sys.argv) > 1 else "help"
    setup_logging(f"method_{stage}")
    if stage == "s0":
        from s0_inputs import stage_s0

        stage_s0()
    elif stage == "recheck":
        from s0_recheck import stage_recheck

        stage_recheck()
    elif stage == "s1":
        from prompts_s1 import stage_s1

        stage_s1(_tok())
    elif stage == "s2":
        from forecast_s2 import stage_s2

        stage_s2(_tok())
    elif stage == "tests":
        subprocess.run([sys.executable, str(ROOT / "tests" / "test_cpu.py")], check=True)
    elif stage == "label":
        from labelq import run_label_worker

        run_label_worker()
    elif stage == "gpu":
        from gpu import run

        dl = os.environ.get("BRT_GPU_DEADLINE")
        pa = os.environ.get("BRT_PRUNE_AFTER", "560")
        run(int(os.environ.get("BRT_BATCH", "40")), float(dl) if dl else None, int(pa) if pa else None)
    elif stage == "close1":
        from cfg import RAW, WORK_DIR, read_jsonl, utc_now
        from commit import commit_files

        bans = [r for r in read_jsonl(RAW) if r["arm"] in ("a", "c", "d", "K0") or r["arm"].startswith("BAN")]
        if bans:
            raise RuntimeError("a ban sample already exists: commit #1 can no longer be closed honestly")
        commit_files("commit1", [ROOT / "src" / "analysis" / "analysis.py", ROOT / "src" / "gpu.py",
                                 ROOT / "src" / "screen.py", ROOT / "tests" / "test_cpu.py"])
        (WORK_DIR / "commit1_closed").write_text(utc_now())
    elif stage == "analysis":
        from analysis import run_analysis

        run_analysis()
    elif stage == "figures":
        from figures import make_figures

        make_figures()
    elif stage == "outputs":
        from outputs import build_outputs

        build_outputs()
    elif stage == "audit":
        subprocess.run([sys.executable, str(ROOT / "audit" / "rederive.py")], check=True)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
