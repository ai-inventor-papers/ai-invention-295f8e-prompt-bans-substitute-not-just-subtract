#!/usr/bin/env python3
"""Novelty audit: every CORRECT program of this run labelled 'other' (any arm, any task; T1 by the 10-algorithm
label) goes to two blind judges of different families (google/gemini-2.5-flash-lite, mistralai/mistral-small-3.2-
24b-instruct) with a deepseek resolver on disagreement. Each judge sees the program and its three nearest known
solutions (token-shingle Jaccard over exp29 results/known_solutions.json). Classes: NOVEL ALGORITHM, CATALOGUE
VARIANT, LABELLER MISS, DEGENERATE. Spend cap USD 0.20 for this script (artifact cap USD 0.5); the first 403 whose
message starts 'AI Inventor per-run OpenRouter budget' stops the batch; unjudged programs stay 'unaudited'."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import requests  # noqa: E402
from loguru import logger  # noqa: E402

from c7 import (BUDGET_MSG, CACHE, DATA, IN29, LABELS, RESULTS, append_jsonl, read_json, read_jsonl, setup_logging,  # noqa: E402
                sha256_text, utc_now, write_json)

JUDGES = ["google/gemini-2.5-flash-lite", "mistralai/mistral-small-3.2-24b-instruct"]
RESOLVER = "deepseek/deepseek-chat-v3-0324"
FALLBACK = {"google/gemini-2.5-flash-lite": ["google/gemini-2.0-flash-001"],
            "mistralai/mistral-small-3.2-24b-instruct": ["mistralai/mistral-small-3.1-24b-instruct",
                                                         "meta-llama/llama-3.3-70b-instruct"],
            "deepseek/deepseek-chat-v3-0324": ["deepseek/deepseek-chat"]}
CAP = 0.20
CLASSES = ["NOVEL ALGORITHM", "CATALOGUE VARIANT", "LABELLER MISS", "DEGENERATE"]
TASK_TEXT = {"T10": "count connected components of an undirected graph", "T2": "shortest path length in a directed "
             "weighted graph", "T03": "k-th smallest value of a list", "T1": "find any path between two grid cells"}
CAT_TEXT = {"T10": "union-find, BFS, DFS, label propagation", "T2": "Dijkstra, Bellman-Ford/SPFA, bidirectional "
            "Dijkstra, Floyd-Warshall, Dial", "T03": "full sort, size-k heap, heapify+pop, quickselect, median of "
            "medians, counting sort", "T1": "BFS, DFS, bidirectional BFS, IDDFS, A*, greedy best-first, unit-weight "
            "Dijkstra, IDA*, jump point search, bidirectional A*"}
SPENT = {"usd": 0.0, "stop": False}


def shingles(code: str, k: int = 5) -> set[str]:
    toks = re.findall(r"[A-Za-z_]\w*|\S", code or "")
    return {" ".join(toks[i:i + k]) for i in range(max(0, len(toks) - k + 1))}


def known(task: str) -> list[str]:
    """Known-solution pool: dependency corpus (cache/known_corpus.jsonl from src/dep7.py: all code-bearing datasets
    of art_j3Rm_lr2nzR6 + exp18's known solutions); programs tagged with this bench task first, then the rest."""
    rows = read_jsonl(CACHE / "known_corpus.jsonl")
    tagged = [r["code"] for r in rows if r.get("task") == task and r.get("code")]
    rest = [r["code"] for r in rows if r.get("task") != task and r.get("code")]
    return tagged + rest


def nearest(code: str, pool: list[str], n: int = 3) -> list[tuple[float, str]]:
    a = shingles(code)
    sc = []
    for c in pool:
        b = shingles(c)
        sc.append((len(a & b) / max(1, len(a | b)), c))
    return sorted(sc, key=lambda x: -x[0])[:n]


def call(model: str, prompt: str) -> tuple[str | None, float]:
    if SPENT["stop"] or SPENT["usd"] >= CAP:
        return None, 0.0
    url = os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/chat/completions"
    hdr = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}", "Content-Type": "application/json"}
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 300,
            "usage": {"include": True}}
    for attempt in range(3):
        try:
            r = requests.post(url, headers=hdr, json=body, timeout=90)
        except requests.RequestException as e:
            logger.warning(f"{model}: {e}")
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 403 and BUDGET_MSG in r.text:
            SPENT["stop"] = True
            logger.error("OpenRouter budget exhausted: stopping the batch")
            return None, 0.0
        if r.status_code in (400, 404):
            for alt in FALLBACK.get(model, []):
                logger.warning(f"{model}: HTTP {r.status_code}; trying {alt}")
                txt, c = call(alt, prompt)
                if txt is not None:
                    return txt, c
            return None, 0.0
        if r.status_code != 200:
            logger.warning(f"{model}: HTTP {r.status_code} {r.text[:200]}")
            time.sleep(2 * (attempt + 1))
            continue
        j = r.json()
        cost = float((j.get("usage") or {}).get("cost") or 0.0)
        SPENT["usd"] += cost
        txt = j["choices"][0]["message"]["content"]
        append_jsonl(DATA / "judge_calls.jsonl", [{"model": model, "utc": utc_now(), "cost": cost,
                                                   "prompt_sha": sha256_text(prompt), "reply": txt[:500]}])
        return txt, cost
    return None, 0.0


def verdict(txt: str | None) -> str | None:
    if not txt:
        return None
    for c in CLASSES:
        if c in txt.upper():
            return c
    return None


def main() -> None:
    setup_logging("novelty7")
    rows = []
    for p in (LABELS, DATA / "labels_s0b.jsonl", DATA / "labels_clamp.jsonl", DATA / "labels_force.jsonl"):
        for r in read_jsonl(p):
            lab = r.get("label10") if r["task"] == "T1" else r["label"]
            if lab in ("other", "disputed", "unknown") and r.get("passed") and r.get("code"):
                r["_label"] = lab
                rows.append(r)
    logger.info(f"{len(rows)} correct 'other' programs")
    res = []
    pools = {}
    for r in rows:
        t = r["task"]
        if t not in pools:
            pools[t] = known(t)
        nn = nearest(r["code"], pools[t])
        refs = "\n\n".join(f"# known solution {i + 1} (Jaccard {s:.2f})\n{c[:1500]}" for i, (s, c) in enumerate(nn))
        prompt = (f"Task: {TASK_TEXT.get(t, t)}. Catalogue of standard algorithms: {CAT_TEXT.get(t, '')}.\n"
                  f"Classify the PROGRAM into exactly one class: NOVEL ALGORITHM (a correct method outside the "
                  f"catalogue and unlike the known solutions), CATALOGUE VARIANT (a disguised or modified catalogue "
                  f"algorithm), LABELLER MISS (plainly one catalogue algorithm), DEGENERATE (brute force / hack / "
                  f"trivial). Answer with the class name first, then one sentence.\n\nPROGRAM:\n{r['code'][:4000]}\n\n"
                  f"NEAREST KNOWN SOLUTIONS:\n{refs}")
        v = [verdict(call(m, prompt)[0]) for m in JUDGES]
        final = v[0] if v[0] and v[0] == v[1] else None
        if final is None and all(v):
            final = verdict(call(RESOLVER, prompt + f"\n\nTwo judges said {v[0]} and {v[1]}. Decide.")[0])
        res.append({"task": t, "arm": r["arm"], "key": r.get("key"), "label": r["_label"],
                    "code_sha256": r.get("code_sha256"), "code": r["code"][:3000],
                    "judges": v, "final": final or "unaudited", "nearest_jaccard": [s for s, _ in nn]})
        if SPENT["stop"]:
            break
    out = {"n_correct_other": sum(1 for r in rows if r["_label"] == "other"),
           "n_correct_disputed_or_unknown": sum(1 for r in rows if r["_label"] != "other"), "audited": sum(1 for x in res if x["final"] != "unaudited"),
           "classes": {c: sum(1 for x in res if x["final"] == c) for c in CLASSES + ["unaudited"]},
           "spend_usd": SPENT["usd"], "budget_stop": SPENT["stop"], "judges": JUDGES, "resolver": RESOLVER,
           "rows": res, "note": "never claim 'no novel' while programs are unaudited"}
    write_json(RESULTS / "novelty_audit.json", out)
    write_json(RESULTS / "costs.json", {"openrouter_usd_novelty": SPENT["usd"], "utc": utc_now()})
    logger.info(f"novelty audit: {out['classes']} spend {SPENT['usd']:.4f}")


if __name__ == "__main__":
    main()
