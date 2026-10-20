#!/usr/bin/env python3
"""Supplementary arm (beyond the plan): full condition-span knockout K0 in BEHAVIOUR, 20 CRN streams per template
(same streams and batch shape as arms a-d). K0 on cache a equals arm c with its condition span hidden, so it separates
'the generated tokens no longer read the ban' from 'the generated tokens read a neutral prohibition instead'."""

from __future__ import annotations

import json

from behaviour import _jobs, run_jobs, stage_label_behaviour
from cfg import PROMPTS_DIR, setup_logging


def main() -> None:
    from engine import load_model

    setup_logging("extra_k0_behaviour")
    fp = json.loads((PROMPTS_DIR / "frozen_prompts.json").read_text())
    tok, model = load_model()
    run_jobs(model, tok, fp, _jobs(arms=("K0",)))
    del model
    stage_label_behaviour()


if __name__ == "__main__":
    main()
