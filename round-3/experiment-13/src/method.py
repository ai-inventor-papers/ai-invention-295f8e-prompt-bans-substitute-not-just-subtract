#!/usr/bin/env python3
"""Predicting where coding bans send a model (iteration 3): entry point.

Runs the pipeline stage by stage.  Every GPU stage is a separate Python process so GPU memory is released at exit
(A: vLLM ban-free arms; B: HF norms + random directions; C: vLLM modal bans; D: HF band-patch control; D2: HF fp32
FRLP rescoring).  No modal-ban prompt is sampled before the 'commit' stage seals the hash chain; stage C refuses to
run without a valid SEAL_BEFORE_BANS line.

    .venv/bin/python method.py all            # the full pipeline, in order
    .venv/bin/python method.py <stage> ...    # one or more stages (see STAGES)
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

# stage -> (script relative to the repo, arguments, what it does)
STAGES: dict[str, tuple[str, list[str], str]] = {
    "setup": ("src/setup_inputs.py", [], "S0.1-0.2 copy + verify the frozen bench, provenance commit, env.json"),
    "recheck": ("src/labelpool.py", [], "S0.3 labeller re-check on gold sets and references vs gate.json"),
    "prompts": ("src/prompts.py", [], "S0.4 ban / twin / nonce / novelty prompts, token alignment, spec spans"),
    "ngrams": ("src/ngrams.py", [], "S0.5 distinctive + sham n-grams (FP8 pilot), unit tests"),
    "proximity": ("src/proximity.py", [], "S0.6 AST tree-edit-distance PROXIMITY nominees"),
    "nominees": ("src/forecasts.py", ["nominees"], "S0.7-0.8 ASSOCIATE and FRLP_FP8 nominees"),
    "gen_a": ("src/vllm_stage.py", ["A"], "S1 GPU process A: twin, vetoes, nonce, novelty, iterated rounds"),
    "hf_b": ("src/hf_stage.py", ["B"], "S1.7 GPU process B: norms, random directions, HF twin control"),
    "forecasts": ("src/forecasts.py", ["build"], "S1d ban-free forecasts"),
    "commit": ("src/forecasts.py", ["commit"], "S1d hash-chained commitment + SEAL_BEFORE_BANS"),
    "gen_c": ("src/vllm_stage.py", ["C"], "S2 GPU process C: modal bans (guarded)"),
    "hf_d": ("src/hf_stage.py", ["D"], "S2b(i) GPU process D: band-patch positive control"),
    "frlp": ("src/frlp_rescore.py", [], "S2b(ii) fp32 FRLP rescoring (descriptive)"),
    "analyze": ("src/analyze.py", [], "S3 committed analysis: C1, C2b, descriptives, template effect, figures"),
    "posthoc": ("src/posthoc.py", [], "post-hoc (not pre-registered) sensitivity analyses"),
    "sanity": ("src/sanity.py", [], "T9 post-run sanity checks"),
    "figures": ("src/figures_extra.py", [], "extra figures (redrawn log-score plot, forecast table)"),
    "outputs": ("src/outputs.py", [], "data/samples.jsonl + method_out.json"),
    "audit": ("audit/rederive.py", [], "independent re-derivation + placebos"),
}
ORDER = ["setup", "recheck", "prompts", "ngrams", "proximity", "nominees", "gen_a", "hf_b", "forecasts", "commit",
         "gen_c", "hf_d", "frlp", "analyze", "posthoc", "sanity", "figures", "outputs", "audit"]


def run_stage(name: str) -> None:
    script, args, what = STAGES[name]
    cwd = ROOT / Path(script).parent
    logger.info(f"=== stage {name}: {what}")
    t0 = time.time()
    r = subprocess.run([PY, str(ROOT / script), *args], cwd=cwd)
    if r.returncode != 0:
        raise SystemExit(f"stage {name} failed with exit code {r.returncode}")
    logger.info(f"=== stage {name} done in {time.time() - t0:.0f}s")


@logger.catch(reraise=True)
def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    (ROOT / "logs").mkdir(exist_ok=True)
    logger.add(str(ROOT / "logs" / "method.log"), rotation="30 MB", level="DEBUG")
    names = sys.argv[1:] or ["--help"]
    if names[0] in ("-h", "--help"):
        print(__doc__)
        for n in ORDER:
            print(f"  {n:<10} {STAGES[n][2]}")
        return
    if names == ["all"]:
        names = ORDER
    for n in names:
        if n not in STAGES:
            raise SystemExit(f"unknown stage {n!r}; choose from {', '.join(ORDER)} or 'all'")
        run_stage(n)


if __name__ == "__main__":
    main()
