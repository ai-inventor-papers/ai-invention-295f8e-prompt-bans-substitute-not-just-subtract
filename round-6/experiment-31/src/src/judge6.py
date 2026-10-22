#!/usr/bin/env python3
"""Blind LLM judges (OpenRouter only; ported from exp26 judge5.py): judge A = openai/gpt-4.1-mini, judge B =
google/gemini-2.5-flash (two families), tie-break C = deepseek/deepseek-chat-v3.1. A judge sees the task description,
the strategy-blind catalogue (id, display name, mechanism) plus 'other' and 'invalid', and the program -- never a
labeller output. Every response is cached by (model, unit, code sha256); cost comes from usage.cost; this artifact's
cap is USD 2.00 (soft stop 1.80, 0.25 reserved for the novelty audit); the first HTTP 403 'AI Inventor per-run
OpenRouter budget' stops every queued and in-flight call (never retried).
"""

from __future__ import annotations

import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from loguru import logger

from cfg6 import BUDGET_MSG, COSTS, DATA_DIR, OPENROUTER_SOFT_STOP, append_jsonl, read_jsonl, utc_now
from units_spec6 import UNITS
from unitlib6 import code_sha

JUDGE_A = "openai/gpt-4.1-mini"
JUDGE_B = "google/gemini-2.5-flash"
JUDGE_C = "deepseek/deepseek-chat-v3.1"
CACHE = DATA_DIR / "judge_cache.jsonl"
_LOCK = threading.Lock()
STATE: dict[str, Any] = {"stopped": False, "spent": None, "cache": None, "client": None}
NOVELTY_RESERVE = 0.25


def spent() -> float:
    if STATE["spent"] is None:
        STATE["spent"] = sum(float(r.get("cost") or 0.0) for r in read_jsonl(COSTS))
    return STATE["spent"]


def _cache() -> dict[str, Any]:
    if STATE["cache"] is None:
        STATE["cache"] = {r["key"]: r for r in read_jsonl(CACHE)}
    return STATE["cache"]


def catalogue_block(u: str) -> str:
    lines = [f"- {m}: {dn} -- {mech}" for m, (dn, mech) in UNITS[u]["modes"].items()]
    lines.append("- other: the program's main mechanism is none of the above")
    lines.append("- invalid: there is no usable solve function (missing, not Python, or it cannot run at all)")
    return "\n".join(lines)


def judge_prompt(u: str, code: str) -> str:
    return (f"{UNITS[u]['description']}\n\nCandidate algorithm categories:\n{catalogue_block(u)}\n\n"
            f"Program:\n```python\n{code}\n```\n\n"
            "Classify the algorithm this program actually implements (its main mechanism as executed), not what its "
            "comments or identifiers claim. If it is incorrect, still classify the mechanism it attempts. "
            'Answer with JSON only: {"label": "<one id from the list>"}')


def _client():
    if STATE["client"] is None:
        from openai import OpenAI
        STATE["client"] = OpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"],
                                 timeout=60)
    return STATE["client"]


def _call(model: str, prompt: str, max_tokens: int = 60) -> tuple[str | None, float]:
    from openai import APIStatusError

    extra: dict[str, Any] = {"usage": {"include": True}}
    if model.startswith("google/gemini-2.5"):
        extra["reasoning"] = {"max_tokens": 0}
    for attempt in range(3):
        if STATE["stopped"]:
            return None, 0.0
        try:
            r = _client().chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}],
                                                  temperature=0.0, max_tokens=max_tokens, extra_body=extra)
            if STATE["stopped"]:
                return None, 0.0
            cost = 0.0
            u = getattr(r, "usage", None)
            if u is not None:
                cost = float(getattr(u, "cost", None) or (u.model_extra or {}).get("cost") or 0.0)
            return (r.choices[0].message.content or ""), cost
        except APIStatusError as e:
            msg = str(e)
            if e.status_code == 403 and BUDGET_MSG in msg:
                STATE["stopped"] = True
                logger.error("OpenRouter budget refusal: stopping every judge call")
                return None, 0.0
            logger.warning(f"{model} HTTP {e.status_code}: {msg[:200]} (attempt {attempt})")
            time.sleep(2 + 3 * attempt)
        except Exception as e:  # noqa: BLE001 - network errors: retry
            logger.warning(f"{model} error {type(e).__name__}: {str(e)[:200]} (attempt {attempt})")
            time.sleep(2 + 3 * attempt)
    return None, 0.0


def parse_label(txt: str | None, valid: set[str]) -> str | None:
    if not txt:
        return None
    m = re.search(r'"label"\s*:\s*"([^"]+)"', txt)
    cand = m.group(1).strip() if m else txt.strip().strip('"').strip()
    return cand if cand in valid else None


def judge_one(model: str, u: str, code: str, purpose: str, allow_reserve: bool = False) -> str | None:
    key = f"{model}|{u}|{code_sha(code)}"
    c = _cache()
    if key in c:
        return c[key]["label"]
    cap = OPENROUTER_SOFT_STOP if allow_reserve else OPENROUTER_SOFT_STOP - NOVELTY_RESERVE
    with _LOCK:
        if spent() >= cap or STATE["stopped"]:
            STATE["stopped_cap"] = True
            return None
    valid = set(UNITS[u]["modes"]) | {"other", "invalid"}
    txt, cost = _call(model, judge_prompt(u, code))
    lab = parse_label(txt, valid)
    with _LOCK:
        STATE["spent"] = spent() + cost
        append_jsonl(COSTS, [{"utc": utc_now(), "model": model, "unit": u, "purpose": purpose, "cost": cost}])
        if txt is not None:
            rec = {"key": key, "model": model, "unit": u, "label": lab, "raw": (txt or "")[:200], "utc": utc_now()}
            c[key] = rec
            append_jsonl(CACHE, [rec])
    return lab


def adjudicate(u: str, code: str, purpose: str, allow_reserve: bool = False) -> dict[str, Any]:
    a = judge_one(JUDGE_A, u, code, purpose, allow_reserve)
    b = judge_one(JUDGE_B, u, code, purpose, allow_reserve)
    out: dict[str, Any] = {"judge_a": a, "judge_b": b, "judge_c": None}
    if a is not None and a == b:
        out["label"], out["how"] = a, "two_judges_agree"
        return out
    c = judge_one(JUDGE_C, u, code, purpose, allow_reserve)
    out["judge_c"] = c
    votes = [x for x in (a, b, c) if x is not None]
    best = max(set(votes), key=votes.count) if votes else None
    if best is not None and votes.count(best) >= 2:
        out["label"], out["how"] = best, "majority_of_three"
    else:
        out["label"], out["how"] = None, "no_majority"
    return out


def adjudicate_many(items: list[tuple[str, str, str]], purpose: str, workers: int = 12,
                    allow_reserve: bool = False) -> list[dict]:
    """items: [(id, unit, code)] -> [{'id', 'unit', **adjudication}] (order kept)."""
    def f(it):
        i, u, code = it
        return {"id": i, "unit": u, **adjudicate(u, code, purpose, allow_reserve)}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(f, items))
