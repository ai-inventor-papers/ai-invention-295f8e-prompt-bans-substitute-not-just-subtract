#!/usr/bin/env python3
"""Run S2 (forecast objects) with the tokenizer only."""
from cfg import model_path, setup_logging


def main() -> None:
    setup_logging("s2")
    from transformers import AutoTokenizer

    from forecast_s2 import stage_s2

    tok = AutoTokenizer.from_pretrained(model_path())
    stage_s2(tok)


if __name__ == "__main__":
    main()
