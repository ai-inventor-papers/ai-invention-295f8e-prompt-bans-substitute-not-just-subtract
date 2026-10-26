#!/usr/bin/env python3
"""Testing-plan item 5: two vLLM generations with the same per-request seed give identical text."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import RESULTS_DIR, resolve_model_path, setup_logger, stable_hash  # noqa: E402
from gpu.vllm_gen import make_llm, sampling  # noqa: E402
from prompts.scaffold import build_prompt, segments  # noqa: E402
from loguru import logger  # noqa: E402


def main() -> None:
    setup_logger("vllm_determinism")
    from transformers import AutoTokenizer
    mp = resolve_model_path()
    tok = AutoTokenizer.from_pretrained(mp)
    llm, kw = make_llm(mp)
    out = {"engine": kw}
    for t in ("T1", "T2"):
        ids = build_prompt(tok, segments(t, "baseline")[3], t)
        seed = stable_hash("determinism", t)
        a = llm.generate([{"prompt_token_ids": ids}], [sampling(4, 256, seed)], use_tqdm=False)[0]
        b = llm.generate([{"prompt_token_ids": ids}], [sampling(4, 256, seed)], use_tqdm=False)[0]
        ta, tb = [c.text for c in a.outputs], [c.text for c in b.outputs]
        out[t] = {"identical": ta == tb, "n": len(ta), "n_distinct_within_request": len(set(ta))}
        logger.info(f"{t}: identical={ta == tb}")
    out["pass"] = all(out[t]["identical"] for t in ("T1", "T2"))
    (RESULTS_DIR / "vllm_determinism.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
