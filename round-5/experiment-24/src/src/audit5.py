#!/usr/bin/env python3
"""LLM judge audits (OpenRouter only; base_url/api key from the environment).

base   Stage 1.5 BASE AUDIT: per task 15 BASE_CHAT programs (every correct non-default one first, then a seeded
       random fill of correct and incorrect ones) blind-labelled by a judge from a SECOND family (bench tasks:
       openai/gpt-4.1-mini, whose pipeline judge is gemini-2.5-flash-lite; T1/T2: google/gemini-2.5-flash-lite,
       whose pipeline judge is gpt-4.1-mini). Agreement < 0.8 -> the task's beta is LOW-CONFIDENCE.
novelty Stage 8 NOVELTY AUDIT: every CORRECT 'other' program of every arm (base included) -> two blind judges of
       different families (gemini-2.5-flash-lite, gpt-4.1-mini), deepseek on disagreement, then an automatic
       nearest-known-solution comparison (difflib ratio against the iteration-3 known-solution corpus and the
       art_j3Rm Mercury / LeetCode human solutions of the task). Classes: NOVEL ALGORITHM / CATALOGUE VARIANT (named)
       / LABELLER MISS / DEGENERATE.
Spend: running total from usage.cost; this artifact's cap is USD 1.5; the first HTTP 403 whose message starts with
'AI Inventor per-run OpenRouter budget' stops the whole batch.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import re
import sys
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import (BUDGET_MSG, DATA_DIR, EXP8_TASK, JUDGE_CAP_USD, LOG_DIR, PATH_TASKS, RESULTS_DIR, SUITE,  # noqa
                 append_jsonl, bench_dir, catalogue, read_json, read_jsonl, sha256_text, utc_now, write_json)

SPEND = LOG_DIR / "openrouter_spend_audit.jsonl"
CACHE = DATA_DIR / "judge_cache_audit.jsonl"
_STATE = {"spend": 0.0, "stopped": False}


def mode_definitions(task: str) -> dict[str, str]:
    if task in PATH_TASKS:
        import importlib.util

        spec = importlib.util.spec_from_file_location("suite_common", SUITE / "common.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return dict(mod.MODE_DEFINITIONS[EXP8_TASK[task]])
    sp = read_json(bench_dir(task) / "spec.json")
    return {c["mode"]: f"{c['display_name']}: {c['mechanism']}" for c in sp["catalogue"]}


def task_text(task: str) -> str:
    from prompts5 import description_and_sig

    return description_and_sig(task)[0]


def prompt_label(task: str, code: str) -> str:
    defs = mode_definitions(task)
    cat = "\n".join(f"- {m}: {d}" for m, d in defs.items())
    return (f"You classify which ALGORITHM a Python program implements (its mechanism, not its variable names).\n\n"
            f"TASK THE PROGRAM SOLVES:\n{task_text(task)}\n\nCATALOGUE OF ALGORITHM LABELS:\n{cat}\n"
            f"- other: a genuine algorithm that is none of the above\n\nPROGRAM:\n```python\n{code[:6000]}\n```\n\n"
            f"Answer with JSON only: {{\"label\": \"<one catalogue label or other>\", \"reason\": \"<10 words>\"}}")


def prompt_novelty(task: str, code: str, nearest: str | None) -> str:
    defs = mode_definitions(task)
    cat = "\n".join(f"- {m}: {d}" for m, d in defs.items())
    near = f"\nNEAREST KNOWN HUMAN/TEXTBOOK SOLUTION (for comparison):\n```python\n{nearest[:3000]}\n```\n" \
        if nearest else ""
    return (f"A program solves the task below and passes all hidden tests. An automatic labeller could not map it to "
            f"the catalogue. Classify it.\n\nTASK:\n{task_text(task)}\n\nCATALOGUE:\n{cat}\n\nPROGRAM:\n```python\n"
            f"{code[:6000]}\n```\n{near}\nClasses: NOVEL_ALGORITHM (a correct algorithm that is not a catalogue "
            f"algorithm or a textbook algorithm for this task), CATALOGUE_VARIANT (a known algorithm, catalogue or "
            f"textbook, possibly disguised; name it), LABELLER_MISS (plainly one catalogue algorithm), DEGENERATE "
            f"(hard-coded / library one-liner / trivial). Answer JSON only: {{\"class\": \"...\", \"named\": "
            f"\"<catalogue label or textbook name>\", \"reason\": \"<15 words>\"}}")


async def _call(client: Any, sem: asyncio.Semaphore, model: str, prompt: str, key: str,
                cache: dict[str, Any]) -> dict[str, Any] | None:
    ck = sha256_text(model + "|" + prompt)
    if ck in cache:
        return cache[ck]
    async with sem:
        if _STATE["stopped"] or _STATE["spend"] >= JUDGE_CAP_USD:
            return None
        for attempt in range(3):
            try:
                r = await client.chat.completions.create(
                    model=model, messages=[{"role": "user", "content": prompt}], temperature=0.0, max_tokens=200,
                    extra_body={"usage": {"include": True}}, timeout=60)
                txt = r.choices[0].message.content or ""
                cost = float(getattr(r.usage, "cost", 0.0) or (r.usage.model_extra or {}).get("cost", 0.0) or 0.0) \
                    if r.usage else 0.0
                _STATE["spend"] += cost
                append_jsonl(SPEND, [{"utc": utc_now(), "model": model, "key": key, "cost": cost,
                                      "running": round(_STATE["spend"], 5)}])
                m = re.search(r"\{.*\}", txt, re.S)
                out = json.loads(m.group(0)) if m else {"raw": txt[:200]}
                out["model"] = model
                cache[ck] = out
                append_jsonl(CACHE, [{"ck": ck, "out": out}])
                logger.debug(f"judge {model} {key}: {str(out)[:150]}")
                return out
            except Exception as e:  # noqa: BLE001 - network / parse errors are retried, budget 403 stops all
                msg = str(e)
                if BUDGET_MSG in msg:
                    _STATE["stopped"] = True
                    logger.error(f"OpenRouter budget refusal: stopping the batch ({msg[:120]})")
                    return None
                logger.warning(f"judge call failed ({attempt}): {msg[:160]}")
                await asyncio.sleep(2 + attempt * 3)
    return None


def run_calls(calls: list[tuple[str, str, str]], conc: int = 16) -> list[dict[str, Any] | None]:
    from openai import AsyncOpenAI

    cache = {r["ck"]: r["out"] for r in read_jsonl(CACHE)}
    for r in read_jsonl(SPEND):
        _STATE["spend"] = max(_STATE["spend"], float(r.get("running", 0.0)))

    async def go():
        client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"])
        sem = asyncio.Semaphore(conc)
        return await asyncio.gather(*[_call(client, sem, m, p, k, cache) for m, p, k in calls])
    return asyncio.run(go())


# ------------------------------------------------------------------------------------------------ base audit
def base_audit(labs: list[dict[str, Any]], defaults: dict[str, str | None], seed: int = 20261021) -> dict[str, Any]:
    import analysis_b as A

    rng = random.Random(seed)
    picks: dict[str, list[dict[str, Any]]] = {}
    for t, d in defaults.items():
        rows = [r for r in labs if r["task"] == t and r["arm"] == "BASE_CHAT" and r.get("code")]
        cat = set(catalogue(t))
        first = [r for r in rows if A.is_correct(r) and r["label"] in cat and r["label"] != d]
        rest = [r for r in rows if r not in first]
        rng.shuffle(first)
        rng.shuffle(rest)
        picks[t] = (first + rest)[:15]
    calls = []
    for t, rs in picks.items():
        model = "google/gemini-2.5-flash-lite" if t in PATH_TASKS else "openai/gpt-4.1-mini"
        for r in rs:
            calls.append((model, prompt_label(t, r["code"]), r["sample_id"]))
    res = run_calls(calls)
    out: dict[str, Any] = {}
    i = 0
    for t, rs in picks.items():
        agree, det = [], []
        for r in rs:
            j = res[i]
            i += 1
            jl = (j or {}).get("label")
            if jl is None:
                continue
            agree.append(jl == r["label"])
            det.append({"sample_id": r["sample_id"], "pipeline": r["label"], "judge": jl, "passed": r["passed"]})
        acc = sum(agree) / len(agree) if agree else None
        out[t] = {"n": len(agree), "agreement": acc, "low_confidence": acc is not None and acc < 0.8,
                  "judge_model": "google/gemini-2.5-flash-lite" if t in PATH_TASKS else "openai/gpt-4.1-mini",
                  "rows": det}
    out["_spend_usd"] = _STATE["spend"]
    return out


# ------------------------------------------------------------------------------------------------ novelty audit
def array_scan_dijkstra(code: str) -> bool:
    """T2 structural re-gate: Dijkstra with an O(V^2) array scan (no heap): selects the unvisited node of minimum
    distance by a scan / min() and relaxes its out-edges; no heapq / PriorityQueue."""
    if re.search(r"\bheapq\b|PriorityQueue|\bheappush\b", code):
        return False
    has_min = bool(re.search(r"min\(|<\s*best|<\s*min_?d", code))
    has_vis = bool(re.search(r"visit|done|processed|seen|used|final", code))
    return has_min and has_vis


def novelty_audit(labs: list[dict[str, Any]]) -> dict[str, Any]:
    import difflib
    from collections import Counter

    import analysis_b as A

    cands: dict[tuple[str, str], dict[str, Any]] = {}
    for r in labs:
        if not A.is_correct(r) or not r.get("code"):
            continue
        if r["label"] in set(catalogue(r["task"])):
            continue
        k = (r["task"], r.get("code_sha256") or sha256_text(r["code"]))
        c = cands.setdefault(k, {"row": r, "arms": Counter(), "labels": Counter()})
        c["arms"][r["arm"]] += 1
        c["labels"][r["label"]] += 1
    known: dict[str, list[dict[str, Any]]] = {}
    for p in (Path(__file__).resolve().parents[1] / "inputs" / "exp18" / "known_solutions.jsonl",
              Path(__file__).resolve().parents[1] / "inputs" / "dep_dataset" / "known_subset.jsonl"):
        for r in read_jsonl(p):
            known.setdefault(r["task"], []).append(r)
    items = []
    for (t, h), c in sorted(cands.items()):
        code = c["row"]["code"]
        best, bscore = None, 0.0
        for kr in known.get(t, []):
            sm = difflib.SequenceMatcher(None, code, kr["code"])
            if sm.quick_ratio() < bscore:
                continue
            s = sm.ratio()
            if s > bscore:
                best, bscore = kr, s
        items.append({"task": t, "code_sha256": h, "arms": dict(c["arms"]), "pipeline_labels": dict(c["labels"]),
                      "code": code, "nearest_known_source": best["source"] if best else None,
                      "nearest_known_hint": best.get("mode_hint") if best else None, "nearest_ratio": bscore,
                      "nearest_code": best["code"] if best else None,
                      "t2_array_scan_dijkstra": (t == "T2" and array_scan_dijkstra(code))})
    calls = []
    for it in items:
        p = prompt_novelty(it["task"], it["code"], it["nearest_code"])
        calls.append(("google/gemini-2.5-flash-lite", p, it["code_sha256"]))
        calls.append(("openai/gpt-4.1-mini", p, it["code_sha256"]))
    res = run_calls(calls)
    third = []
    for i, it in enumerate(items):
        a, b = res[2 * i] or {}, res[2 * i + 1] or {}
        it["judge_a"], it["judge_b"] = a, b
        if a.get("class") != b.get("class"):
            third.append(i)
    if third:
        r3 = run_calls([("deepseek/deepseek-chat-v3-0324", prompt_novelty(items[i]["task"], items[i]["code"],
                                                                         items[i]["nearest_code"]),
                         items[i]["code_sha256"]) for i in third])
        for i, r in zip(third, r3):
            items[i]["judge_c"] = r or {}
    counts: Counter = Counter()
    for it in items:
        votes = [x.get("class") for x in (it.get("judge_a"), it.get("judge_b"), it.get("judge_c")) if x]
        vc = Counter(v for v in votes if v)
        cls = vc.most_common(1)[0][0] if vc else "UNJUDGED"
        if it["judge_a"].get("class") != it["judge_b"].get("class") and len(vc) and vc.most_common(1)[0][1] < 2:
            cls = "DISAGREE"
        if it["t2_array_scan_dijkstra"] and cls != "NOVEL_ALGORITHM":
            it["structural_regate"] = "dijkstra (array scan)"
        it["final_class"] = cls
        counts[cls] += 1
        it.pop("nearest_code", None)
    n = len(items)
    n_novel = counts.get("NOVEL_ALGORITHM", 0)
    return {"n_unique_correct_noncatalogue_programs": n, "class_counts": dict(counts), "n_novel": n_novel,
            "rule_of_three_upper_95": (3 / n if n and n_novel == 0 else None), "items": items,
            "judges": ["google/gemini-2.5-flash-lite", "openai/gpt-4.1-mini", "deepseek/deepseek-chat-v3-0324 (tie)"],
            "manual_note": "the nearest-known comparison is automatic (difflib ratio against the iteration-3 corpus "
                           "and the art_j3Rm Mercury/LeetCode human solutions); NOVEL needs 2 of 3 judges",
            "spend_usd": _STATE["spend"], "utc": utc_now()}


if __name__ == "__main__":
    from cfg import setup_logging

    import analysis_b as A
    from cfg import S1_SLOTS, TASKS15

    setup_logging("audit5")
    labs = read_jsonl(DATA_DIR / "labels.jsonl")
    if sys.argv[1] == "base":
        defaults = {}
        for t in TASKS15:
            tw = [r for r in labs if r["task"] == t and r["arm"] == "TWIN" and int(r["slot"]) in S1_SLOTS]
            defaults[t] = A.default_from_twin(tw)[0]
        res = base_audit(labs, defaults)
        write_json(RESULTS_DIR / "base_audit.json", res)
        logger.info({t: (v["agreement"], v["low_confidence"]) for t, v in res.items() if isinstance(v, dict)})
    elif sys.argv[1] == "novelty":
        seen, uniq = set(), []
        for r in labs:
            if r["sample_id"] not in seen:
                seen.add(r["sample_id"])
                uniq.append(r)
        res = novelty_audit(uniq)
        write_json(RESULTS_DIR / "novelty_audit.json", res)
        logger.info(f"novelty audit: {res['n_unique_correct_noncatalogue_programs']} programs, {res['class_counts']}")
