#!/usr/bin/env python3
"""Path-task SCREEN iteration rule (S7 Q3/Q6): if the default mechanism re-emerges in >= 20% of a round's attempts,
compute the distinctive n-gram of the re-emerged programs by the frozen rule against the other modes' forced
programs, excluding n-grams already masked, and add it to the persistent mask for the next round."""

from __future__ import annotations

from typing import Any

from loguru import logger

from cfg import PATH_TASKS, PRED_DIR, SAMPLES, THRESHOLDS, default_of, read_json, read_jsonl, resp_ids
from forecast_s2 import choose_ngram, forced_sets

ATTEMPT_EXCLUDE = ("invalid", "no_code", "disputed")


def round_ngrams(tok: Any, prev_arm: str, prev: dict[str, Any] | None) -> dict[str, Any]:
    ngrams = read_json(PRED_DIR / "ngrams.json")
    lab = read_jsonl(SAMPLES)
    out = {}
    for t in PATH_TASKS:
        rows = [r for r in lab if r["task"] == t and r["arm"] == prev_arm and r["label"] not in ATTEMPT_EXCLUDE]
        if not rows:
            continue
        D = default_of(t)
        re_em = [r for r in rows if r["label"] == D and r.get("code")]
        share = len(re_em) / len(rows)
        masked = (prev or {}).get(t, {}).get("ngrams") or [ngrams[t]["ids"]]
        if share < THRESHOLDS["reemerge"] or len(re_em) < 3:
            logger.info(f"screen {t} after {prev_arm}: re-emergence {share:.2f} < 0.2 -> no further round")
            continue
        forced, _ = forced_sets(t)
        fids = {m: [resp_ids(tok, r["code"]) for r in lst] for m, lst in forced.items()}
        bids = [resp_ids(tok, r["code"]) for r in re_em]
        rec = choose_ngram(bids, fids, exclude={tuple(g) for g in masked})
        if not rec.get("defined"):
            logger.info(f"screen {t}: no new distinctive n-gram for the re-emerged programs")
            continue
        rec["text"] = tok.decode(rec["ids"])
        out[t] = {"ngrams": [list(g) for g in masked] + [rec["ids"]], "new": rec, "reemergence_share": share,
                  "n_reemerged": len(re_em), "n_attempted": len(rows), "after_arm": prev_arm}
        logger.info(f"screen {t} after {prev_arm}: re-emergence {share:.2f}; new n-gram {rec['text']!r}")
    return out
