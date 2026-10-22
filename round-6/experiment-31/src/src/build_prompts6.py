#!/usr/bin/env python3
"""Render every prompt of list I (plan S1b) with the INSTRUCT tokenizer, check that the base tokenizer gives identical
ids, run the grep audit (with its planted-ban positive control) and write data/prompts.jsonl + results/grep_audit.json.
Usage: python src/build_prompts6.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

from cfg6 import (BASE_ID, BASE_REVISION, MODEL_ID, MODEL_REVISION, RESULTS_DIR, model_path, setup_logging,  # noqa
                  write_json)
from prompts6 import audit_prompts, build_all  # noqa: E402
from units_spec6 import RESERVES, UNIT_ORDER  # noqa: E402


@logger.catch(reraise=True)
def main() -> None:
    from transformers import AutoTokenizer

    setup_logging("build_prompts6")
    tok = AutoTokenizer.from_pretrained(model_path(MODEL_ID, MODEL_REVISION))
    btok = AutoTokenizer.from_pretrained(model_path(BASE_ID, BASE_REVISION))
    rows = build_all(tok, UNIT_ORDER + RESERVES)
    # identical ids under the base tokenizer (the base model reads the instruct-rendered ids)
    mism = 0
    for r in rows:
        if r["kind"] == "plain":
            ids_b = btok(r["user_text"], add_special_tokens=False)["input_ids"]
        else:
            ids_b = None
            txt = tok.decode(r["ids"])
            ids_b = btok(txt, add_special_tokens=False)["input_ids"]
        mism += int(ids_b != r["ids"])
    aud = audit_prompts(rows)
    aud["base_tokenizer_mismatches"] = mism
    write_json(RESULTS_DIR / "grep_audit.json", aud)
    logger.info(f"{len(rows)} prompts; grep audit pass={aud['pass']} violations={len(aud['violations'])}; "
                f"planted caught={sum(p['caught'] for p in aud['planted_control'])}/{len(aud['planted_control'])}; "
                f"base tokenizer mismatches={mism}")
    for v in aud["violations"][:20]:
        logger.warning(f"violation {v}")


if __name__ == "__main__":
    main()
