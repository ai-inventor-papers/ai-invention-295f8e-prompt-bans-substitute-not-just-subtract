#!/usr/bin/env python3
"""S2.7 masked descriptions: per (task, algorithm) three name-free one-sentence descriptions of the mechanism.

desc[0] = the catalogue mechanism clause (bench spec.json; T1/T2: exp7's 'desc' clause after 'that is,') when it
passes the alias-leak check, else the first passing LLM rewrite; desc[1], desc[2] = LLM paraphrases. Every
description must pass ALIAS-LEAK: case-insensitive match (hyphen/space-normalised, word-bounded) over ALL catalogue
display names, aliases and mode ids of the task (T1/T2: the name table plus core algorithm words). One cheap
OpenRouter call per algorithm (DESCRIBE_MODEL); spend tracked from usage.cost; stop on the first budget 403.
Fallback (no API): hand-written rewrites are not available, so the mechanism clause alone is reused and flagged.
"""

from __future__ import annotations

import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from loguru import logger

from cfg4 import (BENCH, BUDGET_MSG, DESCRIBE_MODEL, DESCRIPTIONS, E7, PATH_CATALOGUE, PATH_EXTRA_LEAK, PATH_TASKS,
                  RESULTS_DIR, TASKS15, read_json, write_json)

_LOCK = threading.Lock()
COST = {"usd": 0.0, "calls": 0, "stopped": False}


def norm_text(s: str) -> str:
    s = s.lower().replace("-", " ").replace("_", " ").replace("’", "'")
    return re.sub(r"\s+", " ", s).strip()


def _strip_article(s: str) -> str:
    return re.sub(r"^(a|an|the)\s+", "", s.strip(), flags=re.I)


def bench_dir(task: str):
    for d in BENCH.iterdir():
        if d.is_dir() and d.name.startswith(task + "_"):
            return d
    raise FileNotFoundError(task)


def leak_terms(task: str) -> list[str]:
    terms: set[str] = set()
    if task in PATH_TASKS:
        for m, names in PATH_CATALOGUE[task].items():
            terms.add(m.replace("_", " "))
            for n in names:
                terms.add(_strip_article(n))
                inner = re.findall(r"\(([^)]+)\)", n)
                terms.update(inner)
                terms.add(re.sub(r"\s*\([^)]*\)", "", n))
        terms.update(PATH_EXTRA_LEAK[task])
    else:
        spec = read_json(bench_dir(task) / "spec.json")
        for c in spec["catalogue"]:
            terms.add(_strip_article(c["display_name"]))
            terms.add(c["mode"].replace("_", " "))
        for m, al in spec.get("aliases", {}).items():
            for a in al:
                terms.add(_strip_article(a))
    out = sorted({norm_text(t) for t in terms if t and len(norm_text(t)) >= 2}, key=len, reverse=True)
    return out


def leaks(text: str, terms: list[str]) -> list[str]:
    nt = norm_text(text)
    hits = []
    for t in terms:
        if re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", nt):
            hits.append(t)
    return hits


def mechanisms(task: str) -> dict[str, str]:
    if task in PATH_TASKS:
        conds = read_json(E7 / "prompts" / "prompts_v2.json")["conditions"]
        et = {"T1": "t1", "T2": "t2"}[task]
        out = {}
        for m in PATH_CATALOGUE[task]:
            seg = conds[f"{et}|forced|{m}|desc|k0"]["segment"]
            mm = re.search(r", that is, (.*?)\.? for this task\.?$", seg)
            out[m] = (mm.group(1) if mm else seg).strip().rstrip(".")
        return out
    spec = read_json(bench_dir(task) / "spec.json")
    return {c["mode"]: c["mechanism"] for c in spec["catalogue"]}


def task_spec_text(task: str) -> str:
    if task in PATH_TASKS:
        from cfg4 import E8
        fp = read_json(E8 / "prompts" / "frozen_prompts.json")
        return fp["spec"][{"T1": "t1", "T2": "t2"}[task]]
    return read_json(bench_dir(task) / "spec.json")["spec_text"]


def _call(prompt: str) -> tuple[str, float]:
    from openai import OpenAI

    cli = OpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"], timeout=90)
    r = cli.chat.completions.create(model=DESCRIBE_MODEL, temperature=0.7, max_tokens=900,
                                    messages=[{"role": "user", "content": prompt}],
                                    extra_body={"usage": {"include": True}})
    cost = 0.0
    try:
        u = r.usage.model_dump() if hasattr(r.usage, "model_dump") else dict(r.usage)
        cost = float(u.get("cost") or 0.0)
    except (AttributeError, TypeError, ValueError):
        cost = 0.0
    return r.choices[0].message.content or "", cost


def _parse_list(txt: str) -> list[str]:
    m = re.search(r"\[.*\]", txt, re.S)
    if m:
        try:
            v = json.loads(m.group(0))
            return [str(x).strip() for x in v if str(x).strip()]
        except json.JSONDecodeError:
            pass
    return [l.strip(" -*0123456789.\t") for l in txt.splitlines() if len(l.strip()) > 20]


def describe_one(task: str, mode: str, mech: str, terms: list[str], spec: str) -> dict[str, Any]:
    rec: dict[str, Any] = {"task": task, "mode": mode, "mechanism": mech, "mechanism_leaks": leaks(mech, terms),
                           "candidates": [], "rejected": [], "descriptions": [], "source": []}
    if not rec["mechanism_leaks"]:
        rec["descriptions"].append(mech)
        rec["source"].append("catalogue_mechanism")
    forbidden = ", ".join(f'"{t}"' for t in terms)
    for attempt in range(3):
        if len(rec["descriptions"]) >= 3 or COST["stopped"]:
            break
        prompt = (
            "Programming task (for context):\n" + spec + "\n\nOne algorithmic approach to this task works like this:\n"
            f"\"{mech}\"\n\nWrite 6 different one-sentence descriptions of exactly this approach (same mechanism, "
            "precise enough that a programmer could implement it). Do NOT name the algorithm, and do NOT use any of "
            f"these words or phrases anywhere (case-insensitive, also not inside other words' variants): {forbidden}. "
            "Describe only the mechanism (what data structure, what order of operations). Return ONLY a JSON list of "
            "6 strings.")
        try:
            txt, cost = _call(prompt)
        except Exception as e:  # noqa: BLE001 - API failures fall back to the mechanism clause
            msg = str(e)
            if BUDGET_MSG in msg:
                COST["stopped"] = True
            logger.warning(f"describe {task}/{mode} attempt {attempt}: {msg[:200]}")
            continue
        with _LOCK:
            COST["usd"] += cost
            COST["calls"] += 1
        for c in _parse_list(txt):
            c = c.strip().strip('"').strip()
            if not c.endswith("."):
                c += "."
            hit = leaks(c, terms)
            rec["candidates"].append(c)
            if hit:
                rec["rejected"].append({"text": c, "hits": hit})
                continue
            if c not in rec["descriptions"] and len(rec["descriptions"]) < 3:
                rec["descriptions"].append(c)
                rec["source"].append(f"llm:{DESCRIBE_MODEL}:attempt{attempt}")
    if not rec["descriptions"]:
        rec["descriptions"] = [mech]
        rec["source"] = ["catalogue_mechanism_LEAKING_fallback"]
    while len(rec["descriptions"]) < 3:   # top up by repetition (flagged) so every frame x description cell exists
        rec["descriptions"].append(rec["descriptions"][len(rec["descriptions"]) % max(1, len(rec["descriptions"]))])
        rec["source"].append("repeat_fallback")
    rec["final_leaks"] = [leaks(d, terms) for d in rec["descriptions"]]
    logger.info(f"describe {task}/{mode}: {len(set(rec['descriptions']))} distinct; sources {rec['source']}")
    return rec


def run_describe() -> dict[str, Any]:
    if DESCRIPTIONS.exists():
        return read_json(DESCRIPTIONS)
    jobs = []
    for t in TASKS15:
        terms = leak_terms(t)
        spec = task_spec_text(t)
        for m, mech in mechanisms(t).items():
            jobs.append((t, m, mech, terms, spec))
    with ThreadPoolExecutor(8) as ex:
        recs = list(ex.map(lambda j: describe_one(*j), jobs))
    out = {"model": DESCRIBE_MODEL, "cost_usd": COST["usd"], "calls": COST["calls"], "budget_stop": COST["stopped"],
           "leak_terms": {t: leak_terms(t) for t in TASKS15},
           "by_task": {}}
    for r in recs:
        out["by_task"].setdefault(r["task"], {})[r["mode"]] = r
    write_json(DESCRIPTIONS, out)
    write_json(RESULTS_DIR / "openrouter_cost_describe.json", {"usd": COST["usd"], "calls": COST["calls"]})
    logger.info(f"descriptions: {len(recs)} algorithms, USD {COST['usd']:.4f} over {COST['calls']} calls")
    return out


if __name__ == "__main__":
    from cfg4 import setup_logging

    setup_logging("describe")
    run_describe()
