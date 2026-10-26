#!/usr/bin/env python3
"""Label worker for this artifact: exp17's src/label_worker.py (verbatim) pointed at this workspace's
data/samples_raw.jsonl -> data/labels.jsonl. Path tasks (T1/T2): exp8 suite (hidden tests + runtime tracer + AST
rules, blind judge openai/gpt-4.1-mini on disagreement only); T03: exp11 bench label_one (tests, runtime trace, AST,
judge google/gemini-2.5-flash-lite on disagreement). Judge spend cap for this artifact: USD 0.30 in total (0.225
path, 0.075 bench); beyond it a disagreement is labelled 'disputed' (= 'unresolved', excluded, with sensitivity).
"""

from __future__ import annotations

import time

from loguru import logger

import label_worker as LW
from cfg4 import JUDGE_CAP_TOTAL

LW.JUDGE_CAP_USD = JUDGE_CAP_TOTAL
LW.N_WORKERS = 5


def run_labels(follow: bool = False, minutes: float | None = None) -> None:
    deadline = time.time() + minutes * 60 if minutes else None
    logger.info(f"label worker: follow={follow}, judge cap USD {LW.JUDGE_CAP_USD}, workers {LW.N_WORKERS}")
    LW.run_worker(follow=follow, deadline=deadline, chunk=40)
