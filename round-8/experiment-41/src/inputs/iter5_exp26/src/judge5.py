#!/usr/bin/env python3
"""Blind LLM judges (OpenRouter only): judge A = google/gemini-2.5-flash, judge B = openai/gpt-4.1-mini, tie-break
deepseek/deepseek-chat. A judge sees the task description, the catalogue (id, display name, mechanism) plus 'other',
and the program -- never a labeller output. Every response is cached by (model, unit, code sha256); cost comes from
usage.cost; the artifact cap is USD 2.00 (soft stop 1.80, 0.30 reserved for the novelty audit); the first HTTP 403
'AI Inventor per-run OpenRouter budget' stops every queued and in-flight call (never retried).
Judges first pass a 5/6 control gate (src/judge5.py controls): references of known modes + programs of no
catalogue mode."""

from __future__ import annotations

import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from loguru import logger

from cfg5 import (BUDGET_MSG, COSTS, DATA_DIR, OPENROUTER_CAP_USD, OPENROUTER_SOFT_STOP, RESULTS_DIR, append_jsonl,
                  read_jsonl, utc_now, write_json)
from units_spec import UNITS
from unitlib import code_sha

JUDGE_A = "google/gemini-2.5-flash"
JUDGE_B = "openai/gpt-4.1-mini"
JUDGE_C = "deepseek/deepseek-chat"
CACHE = DATA_DIR / "judge_cache.jsonl"
_LOCK = threading.Lock()
STATE: dict[str, Any] = {"stopped": False, "spent": None, "cache": None}
NOVELTY_RESERVE = 0.30


def spent() -> float:
    if STATE["spent"] is None:
        STATE["spent"] = sum(float(r.get("cost") or 0.0) for r in read_jsonl(COSTS))
    return STATE["spent"]


def _cache() -> dict[str, Any]:
    if STATE["cache"] is None:
        STATE["cache"] = {r["key"]: r for r in read_jsonl(CACHE)}
    return STATE["cache"]


def catalogue_block(u: str, modes: list[str] | None = None, extra: dict[str, tuple[str, str]] | None = None) -> str:
    spec = UNITS[u]
    lines = []
    ms = dict(spec["modes"])
    if extra:
        ms.update(extra)
    for m, (dn, mech) in ms.items():
        if modes is None or m in modes:
            lines.append(f"- {m}: {dn} -- {mech}")
    lines.append("- other: the program's main mechanism is none of the above")
    return "\n".join(lines)


def judge_prompt(u: str, code: str, extra: dict[str, tuple[str, str]] | None = None) -> str:
    return (f"{UNITS[u]['description']}\n\nCandidate algorithm categories:\n{catalogue_block(u, extra=extra)}\n\n"
            f"Program:\n```python\n{code}\n```\n\n"
            "Classify the algorithm this program actually implements (its main mechanism as executed), not what "
            "its comments or identifiers claim. If it is incorrect, still classify the mechanism it attempts. "
            'Answer with JSON only: {"label": "<one id from the list>"}')


def _call(model: str, prompt: str, max_tokens: int = 60) -> tuple[str | None, float]:
    from openai import APIStatusError, OpenAI

    if STATE["stopped"]:
        return None, 0.0
    client = OpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"],
                    timeout=60)
    extra: dict[str, Any] = {"usage": {"include": True}}
    if model.startswith("google/gemini-2.5"):
        extra["reasoning"] = {"max_tokens": 0}
    for attempt in range(3):
        if STATE["stopped"]:
            return None, 0.0
        try:
            r = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}],
                                               temperature=0.0, max_tokens=max_tokens, extra_body=extra)
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


def judge_one(model: str, u: str, code: str, purpose: str, extra: dict[str, tuple[str, str]] | None = None,
              allow_reserve: bool = False) -> str | None:
    key = f"{model}|{u}|{code_sha(code)}|{'x' if extra else ''}"
    c = _cache()
    if key in c:
        return c[key]["label"]
    cap = OPENROUTER_SOFT_STOP if allow_reserve else OPENROUTER_SOFT_STOP - NOVELTY_RESERVE
    with _LOCK:
        if spent() >= cap:
            STATE["stopped_cap"] = True
            return None
    valid = set(UNITS[u]["modes"]) | {"other"} | set(extra or {})
    txt, cost = _call(model, judge_prompt(u, code, extra))
    lab = parse_label(txt, valid)
    with _LOCK:
        STATE["spent"] = spent() + cost
        append_jsonl(COSTS, [{"utc": utc_now(), "model": model, "unit": u, "purpose": purpose, "cost": cost}])
        if txt is not None:
            rec = {"key": key, "model": model, "unit": u, "label": lab, "raw": (txt or "")[:200], "utc": utc_now()}
            c[key] = rec
            append_jsonl(CACHE, [rec])
    return lab


def adjudicate(u: str, code: str, purpose: str, extra: dict[str, tuple[str, str]] | None = None,
               allow_reserve: bool = False) -> dict[str, Any]:
    a = judge_one(JUDGE_A, u, code, purpose, extra, allow_reserve)
    b = judge_one(JUDGE_B, u, code, purpose, extra, allow_reserve)
    out: dict[str, Any] = {"judge_a": a, "judge_b": b, "judge_c": None}
    if a is not None and a == b:
        out["label"] = a
        out["how"] = "two_judges_agree"
        return out
    c = judge_one(JUDGE_C, u, code, purpose, extra, allow_reserve)
    out["judge_c"] = c
    votes = [x for x in (a, b, c) if x is not None]
    best = max(set(votes), key=votes.count) if votes else None
    if best is not None and votes.count(best) >= 2:
        out["label"], out["how"] = best, "majority_of_three"
    else:
        out["label"], out["how"] = None, "no_majority"
    return out


def adjudicate_many(items: list[tuple[str, str, str]], purpose: str, workers: int = 8,
                    extra_by_unit: dict[str, dict] | None = None, allow_reserve: bool = False) -> list[dict]:
    """items: [(id, unit, code)] -> [{'id', **adjudication}]"""
    def f(it):
        i, u, code = it
        return {"id": i, "unit": u, **adjudicate(u, code, purpose, (extra_by_unit or {}).get(u), allow_reserve)}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(f, items))


CONTROL_OTHER = {
    "B1": '''
def solve(nums):
    n = len(nums)
    a = list(nums) + [-1]
    i = 0
    while i < n:
        v = a[i]
        if 0 <= v < n and a[v] != v:
            a[i], a[v] = a[v], a[i]
        else:
            i += 1
    for i in range(n + 1):
        if a[i] != i:
            return i
    return n
''',
    "B7": '''
def solve(nums):
    n = len(nums)
    c = 0
    for i in range(n):
        for j in range(i + 1, n):
            if nums[i] > nums[j]:
                c += 1
    return c
''',
}


def control_gate() -> dict[str, Any]:
    """6 controls per judge: 4 references of known modes (positive) + 2 programs of no catalogue mode (negative)."""
    from unitlib import unit_mod
    ctrl = [("B2", unit_mod("B2").REFERENCES["set_sum_identity"], "set_sum_identity"),
            ("B3", unit_mod("B3").REFERENCES["boruvka"], "boruvka"),
            ("B4", unit_mod("B4").REFERENCES["newton"], "newton"),
            ("B5", unit_mod("B5").REFERENCES["bitmask_enumeration"], "bitmask_enumeration"),
            ("B1", CONTROL_OTHER["B1"], "other"), ("B7", CONTROL_OTHER["B7"], "other")]
    res: dict[str, Any] = {"utc": utc_now(), "controls": [(u, exp) for u, _, exp in ctrl], "judges": {}}
    for model in (JUDGE_A, JUDGE_B, JUDGE_C):
        got = [judge_one(model, u, code, "control_gate") for u, code, _ in ctrl]
        ok = sum(g == exp for g, (_, _, exp) in zip(got, ctrl))
        res["judges"][model] = {"labels": got, "n_correct": ok, "pass": ok >= 5}
    write_json(RESULTS_DIR / "judge_control_gate.json", res)
    return res


if __name__ == "__main__":
    import sys
    from cfg5 import setup_logging
    setup_logging("judge5")
    if "controls" in sys.argv:
        print(json.dumps(control_gate(), indent=1))
        print("spent", spent())
