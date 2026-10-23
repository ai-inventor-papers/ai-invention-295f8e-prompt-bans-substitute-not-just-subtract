#!/usr/bin/env python3
"""S13 novelty audit: every CORRECT program labelled 'other' (any arm, any task) is classified by two blind judges
from different families (google/gemini-2.5-flash, deepseek/deepseek-chat) as NOVEL / CATALOGUE_VARIANT /
LABELLER_MISS / DEGENERATE, with openai/gpt-4.1-mini on disagreement; the nearest known solution (difflib ratio) is
taken from the dependency's known-solution corpus (task-mapped rows) plus its KodCode/XLCoST BFS/DFS programs.
The style re-gate (30 Gemma T1 programs, two blind judges vs the frozen labeller) runs through the same client.
OpenRouter spend is capped at USD 1.00 for this artifact; the first 403 'AI Inventor per-run OpenRouter budget'
stops every remaining call. 'No novel algorithm' is claimed only at a count of 0 (rule-of-three bound 3/n)."""

from __future__ import annotations

import concurrent.futures as cf
import difflib
import json
import os
import re
import threading
from typing import Any

from loguru import logger

from cfg import (BUDGET_MSG, DATA_DIR, DEP1, DEP_EXTRACT, LOG_DIR, OPENROUTER_CAP_USD, RESULTS_DIR, ROOT, SUITE,
                 append_jsonl, read_json, read_jsonl, write_json)

JA, JB, JC = "google/gemini-2.5-flash-lite", "mistralai/mistral-small-3.2-24b-instruct", "openai/gpt-4.1-mini"
CLASSES = ("NOVEL_ALGORITHM", "CATALOGUE_VARIANT", "LABELLER_MISS", "DEGENERATE")
SPEND = LOG_DIR / "openrouter_spend_s13.jsonl"
_LOCK = threading.Lock()
_STATE = {"stop": False, "spent": 0.0}


def spent_total() -> float:
    tot = 0.0
    for f in LOG_DIR.glob("openrouter_spend*.jsonl"):
        for r in read_jsonl(f):
            tot += float(r.get("cost") or 0.0)
    jp = RESULTS_DIR / "openrouter_cost_paths.json"
    if jp.exists():
        try:
            tot += float(read_json(jp).get("total_usd", 0.0))
        except (ValueError, TypeError, AttributeError):
            pass
    return tot


def call(model: str, prompt: str, purpose: str) -> str | None:
    from openai import OpenAI, PermissionDeniedError

    with _LOCK:
        if _STATE["stop"] or _STATE["spent"] + spent_total() > OPENROUTER_CAP_USD:
            _STATE["stop"] = True
            return None
    cli = OpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"], timeout=90,
                 max_retries=2)
    try:
        r = cli.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}], temperature=0,
                                        max_tokens=300, extra_body={"usage": {"include": True}})
    except PermissionDeniedError as e:
        if BUDGET_MSG in str(e):
            with _LOCK:
                _STATE["stop"] = True
            logger.error("OpenRouter budget exhausted: stopping all judge calls")
        return None
    except Exception as e:  # noqa: BLE001 - a failed judge call counts as missing, never a crash
        logger.warning(f"judge call failed ({model}): {type(e).__name__}: {str(e)[:120]}")
        return None
    cost = float(getattr(r.usage, "cost", 0.0) or (r.usage.model_extra or {}).get("cost", 0.0) or 0.0) if r.usage else 0.0
    append_jsonl(SPEND, [{"model": model, "purpose": purpose, "cost": cost,
                          "prompt_head": prompt[:200], "answer": (r.choices[0].message.content or "")[:400]}])
    return r.choices[0].message.content


def parse(txt: str | None, key: str = "class") -> str | None:
    if not txt:
        return None
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0)).get(key)
    except json.JSONDecodeError:
        return None


def task_card(task: str) -> tuple[str, str]:
    import prompts as PG

    mech = PG.mechanism_texts(task)
    return PG.description(task), "\n".join(f"- {m}: {d}" for m, d in mech.items())


def novelty_prompt(task: str, code: str) -> str:
    desc, cat = task_card(task)
    return (f"A program was written for this task:\n{desc}\n\nKnown algorithm families for this task:\n{cat}\n\n"
            "An automatic labeller could not match the program to any family above. Classify the program's MAIN "
            "mechanism into exactly one class:\n- NOVEL_ALGORITHM: a correct mechanism that is genuinely different "
            "from every listed family and is not a standard textbook algorithm for this task\n- CATALOGUE_VARIANT: a "
            "variant, combination or re-implementation of a listed family (name it) or of another standard textbook "
            "algorithm (name it)\n- LABELLER_MISS: plainly one of the listed families\n- DEGENERATE: no real algorithm "
            "(hard-coded cases, brute enumeration of outputs, or trivial library delegation)\n\nProgram:\n```python\n"
            + code[:5000] + "\n```\n\nAnswer with JSON only: {\"class\": \"<CLASS>\", \"family\": \"<name or none>\", "
            "\"rationale\": \"<one sentence>\"}")


def _shingles(code: str, k: int = 5) -> set[tuple[str, ...]]:
    toks = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\S", code)
    return {tuple(toks[i:i + k]) for i in range(max(0, len(toks) - k + 1))}


def nearest_known(task: str, code: str, extra: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Nearest known solution by difflib ratio and 5-token-shingle Jaccard over: the T1 catalogue references, the
    dependency's known-solution corpus (T01 rows), its KodCode/XLCoST BFS/DFS programs, and `extra` (labelled T1
    programs of this artifact)."""
    corpus = [{"source": f"t1_reference:{f.name}", "code": f.read_text()}
              for f in sorted((SUITE / "tasks" / "t1_grid" / "references").glob("*.py"))]
    corpus += [r for r in read_jsonl(DEP1 / "known_solution_corpus.jsonl") if r.get("bench_task") == "T01_grid_path"]
    corpus += [{"source": x["src"], "code": x["code"]} for x in read_json(DEP_EXTRACT / "kodcode_xlcost_bfs_dfs.json")]
    corpus += list(extra or [])
    sh = _shingles(code)
    best_r, best_j = (0.0, None), (0.0, None)
    for r in corpus:
        c = r.get("code") or ""
        if not c or c == code:
            continue
        s_ = difflib.SequenceMatcher(None, code, c).ratio()
        if s_ > best_r[0]:
            best_r = (s_, r)
        o = _shingles(c)
        j = len(sh & o) / max(len(sh | o), 1)
        if j > best_j[0]:
            best_j = (j, r)
    return {"difflib_ratio": best_r[0], "difflib_source": (best_r[1] or {}).get("source"),
            "shingle_jaccard": best_j[0], "jaccard_source": (best_j[1] or {}).get("source"), "n_corpus": len(corpus)}


def audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    cand = [r for r in rows if r.get("label") == "other" and r.get("passed") and r.get("code")]
    out = []

    def one(r: dict[str, Any]) -> dict[str, Any]:
        pr = novelty_prompt(r["task"], r["code"])
        a = parse(call(JA, pr, "novelty"))
        b = parse(call(JB, pr, "novelty"))
        c = None
        if a != b:
            c = parse(call(JC, pr, "novelty"))
        votes = [x for x in (a, b, c) if x in CLASSES]
        final = max(set(votes), key=votes.count) if votes and (a == b or c in (a, b)) else "disputed"
        return {"row_id": r["row_id"], "task": r["task"], "arm": r["arm"], "judge_a": a, "judge_b": b, "judge_c": c,
                "final": final, "nearest_known": nearest_known(r["task"], r["code"]), "code_head": r["code"][:300]}

    with cf.ThreadPoolExecutor(6) as ex:
        out = list(ex.map(one, cand))
    counts = {k: sum(1 for o in out if o["final"] == k) for k in CLASSES + ("disputed",)}
    n_correct = sum(1 for r in rows if r.get("passed"))
    res = {"n_correct_programs_all_arms": n_correct, "n_correct_other": len(cand), "counts": counts,
           "items": out, "judges": [JA, JB, JC],
           "novel_claim": ("none (count 0; rule-of-three upper bound 3/n = %.4f over %d correct programs)"
                           % (3 / max(n_correct, 1), n_correct)) if counts["NOVEL_ALGORITHM"] == 0 else
                          f"{counts['NOVEL_ALGORITHM']} judged NOVEL (see items)",
           "budget_stopped": _STATE["stop"]}
    write_json(RESULTS_DIR / "novelty_audit.json", res)
    return res


def regate(rows: list[dict[str, Any]], n: int = 30, seed: int = 6) -> dict[str, Any]:
    """Style re-gate: 30 T1 programs, two blind judges choose the catalogue mode; agreement with the labeller."""
    import random

    import prompts as PG

    rng = random.Random(seed)
    pool = [r for r in rows if r["task"] == "T1" and r.get("code") and r["label"] not in ("invalid", "disputed")]
    pick = rng.sample(pool, min(n, len(pool)))
    mech = PG.mechanism_texts("T1")
    cat = "\n".join(f"- {m}: {d}" for m, d in mech.items())

    def one(r: dict[str, Any]) -> dict[str, Any]:
        pr = (f"Task:\n{PG.description('T1')}\n\nCandidate labels (choose exactly one):\n{cat}\n- other: none of the "
              "above\n\nJudge the mechanism the code actually executes.\n\nProgram:\n```python\n" + r["code"][:5000] +
              "\n```\n\nAnswer with JSON only: {\"label\": \"<label>\"}")
        a = parse(call(JA, pr, "regate"), "label")
        b = parse(call(JB, pr, "regate"), "label")
        return {"row_id": r["row_id"], "labeller": r["label"], "judge_a": a, "judge_b": b}

    with cf.ThreadPoolExecutor(6) as ex:
        out = list(ex.map(one, pick))
    agree_a = sum(o["judge_a"] == o["labeller"] for o in out)
    agree_b = sum(o["judge_b"] == o["labeller"] for o in out)
    both = sum(o["judge_a"] == o["judge_b"] == o["labeller"] for o in out)
    res = {"n": len(out), "agree_judge_a": agree_a, "agree_judge_b": agree_b, "all_three_agree": both,
           "judges": [JA, JB], "items": out}
    write_json(RESULTS_DIR / "regate.json", res)
    return res


__all__ = ["audit", "regate", "spent_total"]
_ = DATA_DIR
