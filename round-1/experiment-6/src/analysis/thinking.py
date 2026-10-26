#!/usr/bin/env python3
"""8f Thinking trajectories (A6 cells): plan statements found with an approach lexicon, approaches considered,
first approach, switches, first-mentioned == implemented, distinct plans per cell (word-4-gram Jaccard
components), truncated vs completed traces, and a small LLM audit of the lexicon's recall and precision."""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis.metrics import clusters  # noqa: E402
from common import ALIAS_LEXICON, LOGS, MODES, append_jsonl  # noqa: E402

DS_WORDS = [r"\bqueue\b", r"\bdeque\b", r"\bstack\b", r"\bheap\b", r"priority queue", r"\bbucket", r"\bmatrix\b"]
INV_WORDS = [r"\bvisited\b", r"\bfrontier\b", r"\blevel\b", r"\blayer\b", r"\brelax", r"heuristic", r"manhattan",
             r"\bshortest\b", r"both ends", r"iterative deepening", r"depth limit"]
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def mode_patterns(task: str) -> dict[str, list[str]]:
    pats = {m: list(ALIAS_LEXICON.get(m, [])) for m in MODES[task]}
    if task == "T1":
        pats["dijkstra_unit"] = [r"dijkstra", r"uniform[- ]cost"]
        pats["bidirectional_bfs"] = [r"bi-?directional", r"two[- ]way search", r"meet in the middle",
                                     r"meet-in-the-middle"]
    else:
        pats["bidirectional_dijkstra"] = [r"bi-?directional"]
    return pats


def sentences(text: str) -> list[str]:
    return [s.strip() for s in SENT_SPLIT.split(text or "") if len(s.strip()) > 2]


def mentions(sentence: str, pats: dict) -> list[tuple[int, str]]:
    low = sentence.lower()
    out = []
    for m, ps in pats.items():
        for p in ps:
            mm = re.search(p, low)
            if mm:
                out.append((mm.start(), m))
                break
    return sorted(out)


def is_plan(sentence: str, pats: dict) -> bool:
    low = sentence.lower()
    return bool(mentions(sentence, pats)) or any(re.search(p, low) for p in DS_WORDS + INV_WORDS)


def canon(text: str, pats: dict) -> str:
    low = text.lower()
    for m, ps in pats.items():
        for p in ps:
            low = re.sub(p, f" {m} ", low)
    return re.sub(r"\s+", " ", low)


def word_shingles(text: str, k: int = 4) -> frozenset:
    w = re.findall(r"[a-z_]+", text)
    return frozenset(tuple(w[i:i + k]) for i in range(max(1, len(w) - k + 1)))


def trace_stats(s: dict) -> dict:
    task = s["task"]
    pats = mode_patterns(task)
    sents = sentences(s.get("thinking_text") or "")
    plan = [x for x in sents if is_plan(x, pats)]
    seq = [m for x in sents for _, m in mentions(x, pats)]
    switches = sum(1 for a, b in zip(seq, seq[1:]) if a != b)
    first = seq[0] if seq else None
    return dict(n_sentences=len(sents), n_plan=len(plan), considered=sorted(set(seq)), first=first,
                switches=switches, implemented=s["label"], first_equals_implemented=(first == s["label"])
                if first else None, plan_text=canon(" ".join(plan), pats), truncated=bool(s.get("truncated_thinking")),
                plan_idx=[i for i, x in enumerate(sents) if is_plan(x, pats)])


def run(samples: list[dict], thetas=(0.7, 0.8, 0.9)) -> dict:
    cells = defaultdict(list)
    for s in samples:
        if s["arm"].startswith("A6"):
            d = s["decoding"]
            cells[(s["task"], d["sampler"], d["T"])].append(s)
    out = []
    for (task, sampler, T), rows in sorted(cells.items(), key=lambda kv: str(kv[0])):
        st = [trace_stats(r) for r in rows]
        rec = dict(task=task, sampler=sampler, T=T, n=len(rows),
                   truncated_rate=float(np.mean([x["truncated"] for x in st])),
                   mean_plan_statements=float(np.mean([x["n_plan"] for x in st])),
                   mean_approaches_considered=float(np.mean([len(x["considered"]) for x in st])),
                   share_considering_2plus=float(np.mean([len(x["considered"]) >= 2 for x in st])),
                   considered_counts=dict(Counter(m for x in st for m in x["considered"])),
                   first_counts=dict(Counter(x["first"] for x in st)),
                   mean_switches=float(np.mean([x["switches"] for x in st])),
                   first_equals_implemented=float(np.mean([x["first_equals_implemented"] for x in st
                                                           if x["first_equals_implemented"] is not None]))
                   if any(x["first_equals_implemented"] is not None for x in st) else None,
                   implemented_counts=dict(Counter(x["implemented"] for x in st)))
        for grp, sel in (("completed", [x for x in st if not x["truncated"]]), ("truncated",
                                                                                  [x for x in st if x["truncated"]])):
            rec[f"{grp}_n"] = len(sel)
            rec[f"{grp}_mean_approaches_considered"] = float(np.mean([len(x["considered"]) for x in sel])) \
                if sel else None
            rec[f"{grp}_first_equals_implemented"] = float(np.mean([x["first_equals_implemented"] for x in sel
                                                                    if x["first_equals_implemented"] is not None])) \
                if any(x["first_equals_implemented"] is not None for x in sel) else None
        sh = [word_shingles(x["plan_text"]) for x in st]
        n = len(sh)
        J = np.eye(n)
        for i in range(n):
            for j in range(i + 1, n):
                u = len(sh[i] | sh[j])
                J[i, j] = J[j, i] = len(sh[i] & sh[j]) / u if u else 1.0
        for th in thetas:
            rec[f"distinct_plans_theta{th}"] = int(len(set(clusters(J, th, "single").tolist())))
        rec["mean_pairwise_plan_jaccard"] = float(J[np.triu_indices(n, 1)].mean()) if n > 1 else None
        out.append(rec)
    return dict(cells=out)


async def _audit_calls(items, budget_usd=0.05):
    from openai import AsyncOpenAI
    from labeller.judge import PRICES
    client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"],
                         timeout=120, max_retries=2)
    model = "google/gemini-2.5-flash-lite"
    spent = [0.0]
    stop = [False]
    sem = asyncio.Semaphore(8)

    async def one(it):
        async with sem:
            if stop[0] or spent[0] >= budget_usd:
                return None
            numbered = "\n".join(f"[{i}] {x[:300]}" for i, x in enumerate(it["sents"][:220]))
            prompt = ("Below are the numbered sentences of a programmer's private reasoning about a path-search "
                      "task. List the indices of EVERY sentence in which an algorithmic approach is considered, "
                      "compared, rejected or chosen (e.g. naming BFS/DFS/A*/Dijkstra/Bellman-Ford, or describing a "
                      "queue/stack/heap-based strategy). Reply with JSON only: {\"indices\": [..]}\n\n" + numbered)
            try:
                r = await client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}],
                                                         temperature=0, max_tokens=600,
                                                         extra_body={"usage": {"include": True}})
            except Exception as e:  # noqa: BLE001
                if "AI Inventor per-run OpenRouter budget" in str(e):
                    stop[0] = True
                return None
            u = r.usage
            extra = getattr(u, "model_extra", None) or {}
            cost = float(extra.get("cost", (u.prompt_tokens * PRICES[model][0] + u.completion_tokens *
                                            PRICES[model][1]) / 1e6))
            spent[0] += cost
            append_jsonl(LOGS / "openrouter_costs.jsonl", [dict(model=model, cost=cost, kind="lexicon_audit")])
            m = re.search(r"\{.*\}", r.choices[0].message.content or "", re.S)
            try:
                idx = set(int(i) for i in json.loads(m.group(0)).get("indices", [])) if m else set()
            except (json.JSONDecodeError, ValueError, TypeError):
                idx = set()
            return dict(key=it["key"], judge=sorted(idx), lex=it["lex"], n=min(len(it["sents"]), 220))
    res = await asyncio.gather(*[one(it) for it in items])
    await client.close()
    return [r for r in res if r], spent[0]


def lexicon_audit(samples: list[dict], n: int = 30, seed: int = 5) -> dict:
    rng = np.random.default_rng(seed)
    a6 = [s for s in samples if s["arm"].startswith("A6") and s.get("thinking_text")]
    cells = defaultdict(list)
    for s in a6:
        cells[(s["task"], s["decoding"]["sampler"], s["decoding"]["T"])].append(s)
    keys = sorted(cells, key=str)
    picks = []
    i = 0
    while len(picks) < n and any(cells[k] for k in keys):
        k = keys[i % len(keys)]
        if cells[k]:
            picks.append(cells[k].pop(int(rng.integers(len(cells[k])))))
        i += 1
    items = []
    for s in picks:
        pats = mode_patterns(s["task"])
        sents = sentences(s["thinking_text"])[:220]
        items.append(dict(key=s["key"], sents=sents, lex=[j for j, x in enumerate(sents) if is_plan(x, pats)]))
    res, spent = asyncio.run(_audit_calls(items))
    tp = fp = fn = 0
    for r in res:
        J, L = set(r["judge"]), set(r["lex"])
        tp += len(J & L)
        fp += len(L - J)
        fn += len(J - L)
    return dict(n_traces=len(res), lexicon_precision=tp / (tp + fp) if tp + fp else None,
                lexicon_recall=tp / (tp + fn) if tp + fn else None, judge_sentences=tp + fn, lexicon_sentences=tp + fp,
                cost_usd=round(spent, 5), model="google/gemini-2.5-flash-lite")
