#!/usr/bin/env python3
"""De-commitment steering screen on Qwen3-8B (thinking off): method, baselines and controls, end to end.

Method: a list-vs-implement difference-of-means direction d_dc at the read position R, added as
c * ||h|| * d_hat at R and at every generated token (layer L*), swept over c and fixed at the largest
correctness-preserving c (pass rate only). Baselines / controls: an engine-matched zero-strength hook (HF c=0),
the unsteered vLLM baseline, the enumeration prompt (prompting ceiling), the modal-mode ban prompt and its
mention control, two norm- and layer-matched random directions, a placebo frame direction (descriptive vs short
variable names), a breadth direction (list vs name-one) and cross-task transfer. Outcomes: hidden-test pass
rate and the correctness-conditioned Hill number of runtime/AST/judge-labelled algorithms, plus a forward-pass
commitment test and hash-committed forecasts scored against ban samples.

Every stage skips work already on disk, so the script resumes. GPU stages run in their own processes
(vLLM and HF are never loaded together).

  uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r requirements.txt
  .venv/bin/python method.py                 # all stages
  .venv/bin/python method.py --stages analyze # just the CPU analysis from data on disk
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from loguru import logger

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
from common import FORECAST_DIR, RAW_DIR, RESULTS_DIR, TASKS_DIR, setup_logger  # noqa: E402

PY = str(WS / ".venv" / "bin" / "python")
STAGES = ["meta", "prompts", "tasks", "states", "directions", "vllm1", "label", "steer", "label", "gate", "commit",
          "vllm2", "label", "succ", "vllm3", "label", "analyze"]


def gpu_env() -> dict:
    e = dict(os.environ)
    e.update({"HF_HUB_OFFLINE": "1", "TOKENIZERS_PARALLELISM": "false",
              "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
              "VLLM_CACHE_ROOT": str(WS / ".engine_cache/vllm"), "TRITON_CACHE_DIR": str(WS / ".engine_cache/triton"),
              "TORCHINDUCTOR_CACHE_DIR": str(WS / ".engine_cache/inductor"), "XDG_CACHE_HOME": str(WS / ".engine_cache/xdg"),
              "VLLM_WORKER_MULTIPROC_METHOD": "spawn", "PYTHONUNBUFFERED": "1"})
    return e


def run(args: list[str], log: str, timeout_s: float) -> None:
    t0 = time.time()
    logger.info(f"RUN {' '.join(args)}  (log: logs/{log})")
    with (WS / "logs" / log).open("a") as fh:
        p = subprocess.run([PY, *args], cwd=WS, env=gpu_env(), stdout=fh, stderr=subprocess.STDOUT, timeout=timeout_s)
    if p.returncode != 0:
        raise RuntimeError(f"stage command failed (rc={p.returncode}): {' '.join(args)}; see logs/{log}")
    logger.info(f"done in {(time.time() - t0) / 60:.1f} min")


def stage(name: str) -> None:
    if name == "meta":
        run(["analysis/record_meta.py"], "record_meta.out", 300)
    elif name == "prompts":
        if not (WS / "prompts" / "paraphrases.json").exists():
            run(["prompts/make_paraphrases.py"], "prompts.out", 300)
    elif name == "tasks":
        reuse = ["--reuse-limits"] if (TASKS_DIR / "tests_T1.json").exists() else []
        run(["tasks/build_tests.py", *reuse], "build_tests.out", 3600)
    elif name == "states":
        if not (WS / "cache" / "hR_index.json").exists():
            run(["gpu/hf_states.py"], "hf_states.out", 3600)
    elif name == "directions":
        if not (RESULTS_DIR / "layer_selection.json").exists():
            run(["analysis/directions.py"], "directions.out", 3600)
        elif not (RESULTS_DIR / "commitment_test.json").exists():
            run(["analysis/directions.py", "--commitment-only"], "commitment.out", 3600)
    elif name == "vllm1":
        run(["gpu/vllm_gen.py", "--session", "s1"], "vllm_s1.out", 4 * 3600)
    elif name == "steer":
        if not (RESULTS_DIR / "steer_state.json").exists() or "finished_utc" not in (RESULTS_DIR / "steer_state.json").read_text():
            # the steering process waits for test labels when it needs c*; run the daemon alongside it
            d = subprocess.Popen([PY, "labeller/daemon.py"], cwd=WS, env=gpu_env(),
                                 stdout=(WS / "logs" / "daemon.out").open("a"), stderr=subprocess.STDOUT)
            try:
                run(["gpu/hf_steer.py", "--budget-min", "125"], "hf_steer.out", 4 * 3600)
            finally:
                (WS / "logs" / "daemon.stop").touch()
                d.wait(timeout=600)
                (WS / "logs" / "daemon.stop").unlink(missing_ok=True)
    elif name == "label":
        run(["labeller/daemon.py", "--once"], "daemon.out", 4 * 3600)
        run(["labeller/judge.py", "--bulk", "--cap", "0.80"], "judge.out", 1800)
    elif name == "gate":
        run(["labeller/gate.py"], "gate.out", 1800)
    elif name == "commit":
        if not (FORECAST_DIR / "commit_log.jsonl").exists():
            run(["analysis/forecast.py", "modal"], "forecast.out", 600)
            run(["analysis/forecast.py", "commit-ban"], "forecast.out", 600)
    elif name == "vllm2":
        run(["gpu/vllm_gen.py", "--session", "s2", "--with-mention"], "vllm_s2.out", 4 * 3600)
    elif name == "succ":
        if not (RESULTS_DIR / "succession_plan.json").exists():
            run(["analysis/forecast.py", "commit-succ"], "forecast.out", 600)
    elif name == "vllm3":
        run(["gpu/vllm_gen.py", "--session", "s3"], "vllm_s3.out", 4 * 3600)
    elif name == "analyze":
        run(["analysis/record_meta.py"], "record_meta.out", 300)
        run(["analysis/forecast.py", "verify"], "forecast.out", 300)
        run(["analysis/analyze.py"], "analyze.out", 3600)
        run(["analysis/figures.py"], "figures.out", 1200)
        run(["analysis/method_out.py"], "method_out.out", 1200)
    else:
        raise ValueError(name)


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", default=",".join(STAGES), help="comma-separated subset, in order")
    a = ap.parse_args()
    setup_logger("method")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for s in a.stages.split(","):
        logger.info(f"=== stage {s} ===")
        stage(s.strip())
    logger.info("pipeline complete: see method_out.json, results/ and figures/")


if __name__ == "__main__":
    main()
