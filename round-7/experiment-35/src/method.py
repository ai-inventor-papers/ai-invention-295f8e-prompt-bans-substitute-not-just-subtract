#!/usr/bin/env python3
"""Iteration 7, claim T: where temperature can change the chosen algorithm (bf16 Qwen/Qwen3-8B, thinking off).

Method (ours): locate the token where the algorithm is decided (prefix resampling + Bayesian change points + a
20-continuation confirmation), read the fork logits by teacher forcing, and PREDICT the algorithm share at any
temperature / top-k from those logits and the token conditionals P(A | fork token) - committed (sha256 chain) before
any temperature sample. Baselines / controls: the observed same-seed sweep (the same 50 uniform streams in all 8
cells, exact McNemar), the twin's T 1.0 share (no-temperature-effect reference), the per-slot replay, control
positions beside every fork, the matched-norm random exchange (MR) and the no-edit twins in S4.

Stages (each resumes from its files; GPU stages run in their own process, see src/gpu7.py):
  vendor      A1  copy + sha256 every prior input                         (CPU)  src/vendor_inputs.py
  prompts     A3  twin / ban / forced prompts + U3 checks                  (CPU)  src/prompts7.py
  gputests    G1-G5, U2                                                    (GPU)  src/gpu7.py tests
  twins       S0 twins (N = 100 per mixed unit) + collapsed/engine check   (GPU)  src/gpu7.py twins
  cputests    U1-U8                                                        (CPU)  src/cpu7.py tests
  commit0     COMMIT #0                                                    (CPU)  src/cpu7.py commit0
  forkscan    Part C scan / refine / confirm / calibration                 (GPU)  src/gpu7.py forkscan
  commit1     COMMIT #1                                                    (CPU)  src/cpu7.py commit1
  predict     Part D teacher forcing, token conditionals, S4 numbers,      (GPU)  src/gpu7.py predict,...
              collapsed margins
  commit2     COMMIT #2 (predictions + scoring-code hashes)                (CPU)  src/predictions7.py commit2
  generate    Part E sweep, S4(b), S4(a), F7 states, collapsed T 1.3       (GPU)  src/gpu7.py sweep,...
  finalize    judges, scoring, re-derivation, post hoc, novelty audit,     (CPU)  see finalize()
              figures, summary, method_out.json
Usage: .venv/bin/python method.py all | <stage>[,<stage>...]
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent
PY = sys.executable
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
(ROOT / "logs").mkdir(exist_ok=True)
logger.add(str(ROOT / "logs" / "method.log"), rotation="30 MB", level="DEBUG")

UNITS = "B3,A3,B6"
STAGES = {
    "vendor": [PY, str(SRC / "vendor_inputs.py")],
    "gputests": [PY, str(SRC / "gpu7.py"), "tests"],
    "twins": [PY, str(SRC / "gpu7.py"), "twins", "--units", "B3,A3,B6,T2,T03,T1,T10"],
    "cputests": [PY, str(SRC / "cpu7.py"), "tests"],
    "commit0": [PY, str(SRC / "cpu7.py"), "commit0"],
    "forkscan": [PY, str(SRC / "gpu7.py"), "forkscan", "--units", UNITS],
    "predict": [PY, str(SRC / "gpu7.py"), "predict,s4predict,collapsed_margins", "--units", UNITS],
    "commit2": [PY, str(SRC / "predictions7.py"), "commit2"],
    "generate": [PY, str(SRC / "gpu7.py"), "sweep,s4b,s4a,geometry,collapsed", "--units", UNITS],
}
FINALIZE = [
    [PY, str(SRC / "novelty7.py"), "dep"],
    [PY, str(SRC / "novelty7.py"), "judge"],
    [PY, str(SRC / "analysis_T.py")],
    [PY, str(SRC / "rederive.py")],
    [PY, str(SRC / "posthoc7.py")],
    [PY, str(SRC / "novelty7.py"), "audit"],
    [PY, "-c", "import sys; sys.path.insert(0, 'src'); import novelty7; novelty7.regate()"],
    [PY, str(SRC / "views7.py")],
    [PY, str(SRC / "figures7.py")],
    [PY, str(SRC / "report7.py")],
    [PY, str(SRC / "outputs7.py")],
    [PY, str(SRC / "commit7.py")],
]
ORDER = ["vendor", "prompts", "gputests", "twins", "cputests", "commit0", "forkscan", "commit1", "predict", "commit2",
         "generate", "finalize"]


def run(cmd: list[str]) -> None:
    t0 = time.time()
    logger.info("$ " + " ".join(Path(c).name if c.startswith(str(ROOT)) else c for c in cmd))
    pr = subprocess.run(cmd, cwd=ROOT)
    if pr.returncode != 0:
        raise RuntimeError(f"stage failed ({pr.returncode}): {cmd}")
    logger.info(f"  done in {time.time() - t0:.0f}s")


def prompts() -> None:
    from transformers import AutoTokenizer

    import prompts7 as P7
    from cfg7 import RESULTS_DIR, model_path, write_json
    tok = AutoTokenizer.from_pretrained(model_path())
    rows = P7.write_prompts(tok)
    chk = P7.u3_checks(tok, rows)
    write_json(RESULTS_DIR / "u3_prompt_checks.json", chk)
    if not chk["all_pass_required"]:
        raise RuntimeError("U3 prompt checks failed")


def commit1() -> None:
    import cpu7
    logger.info(cpu7.commit1())


@logger.catch(reraise=True)
def main() -> None:
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    stages = ORDER if what == "all" else what.split(",")
    for st in stages:
        logger.info(f"=== {st} ===")
        if st == "prompts":
            prompts()
        elif st == "commit1":
            commit1()
        elif st == "finalize":
            for cmd in FINALIZE:
                run(cmd)
        elif st in STAGES:
            run(STAGES[st])
        else:
            raise ValueError(f"unknown stage {st}; known: {ORDER}")


if __name__ == "__main__":
    main()
