#!/usr/bin/env python3
"""Stage H novelty audit: every CORRECT program labelled 'other' (unique per task x code sha256, any arm, any
precision) goes to two blind judges from different families via OpenRouter (google/gemini-2.5-flash-lite,
openai/gpt-4.1-mini; deepseek/deepseek-chat-v3.1 breaks ties), which see the task, its catalogue and the 3 nearest
known solutions (normalised-AST difflib ratio over exp18's known solutions and the dependency art_j3Rm_lr2nzR6's
leetcode / mercury / thealgorithms / kodcode / xlcost programs), never the arm or the precision. Classes: NOVEL
ALGORITHM / CATALOGUE VARIANT / KNOWN TECHNIQUE OUTSIDE THE CATALOGUE / LABELLER MISS / DEGENERATE.
Spend: running sum of usage.cost, artifact cap USD 0.50; the first HTTP 403 whose message starts 'AI Inventor per-run
OpenRouter budget' stops the whole batch (checked after every semaphore acquisition), no rerun.
Output: results/novelty_audit.json (+ data/novelty_cache.jsonl)."""

from __future__ import annotations

import ast
import asyncio
import difflib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger

from cfg import append_jsonl, read_jsonl, setup_logging, utc_now, write_json
from cfg_e import BUDGET_MSG, DATA_DIR, E18, JUDGE_CAP_USD_E, RESULTS_DIR, ROOT

JUDGES = ("google/gemini-2.5-flash-lite", "openai/gpt-4.1-mini")
TIEBREAK = "deepseek/deepseek-chat-v3.1"
CLASSES = ["NOVEL ALGORITHM", "CATALOGUE VARIANT", "KNOWN TECHNIQUE OUTSIDE THE CATALOGUE", "LABELLER MISS",
           "DEGENERATE"]
CATALOGUE = {
    "T10": "BFS, DFS (recursive or iterative), union-find / disjoint-set union, label propagation",
    "T2": "Dijkstra (binary heap or array), Bellman-Ford / SPFA (label-correcting), bidirectional search, A*, "
          "Dial's buckets, Floyd-Warshall",
    "T03": "full sort, size-k heap, heapify-and-pop, quickselect, median of medians, counting sort",
}
SPECS = {"T10": "count the connected components of an undirected graph (solve(n, edges))",
         "T2": "find a minimum-weight path between two nodes of a weighted graph (find_path(graph, start, goal))",
         "T03": "return the k-th smallest value of a list (solve(nums, k))"}
CACHE = DATA_DIR / "novelty_cache.jsonl"


def norm_ast(code: str) -> str:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return re.sub(r"\s+", " ", code)
    names: dict[str, str] = {}

    class R(ast.NodeTransformer):
        def visit_Name(self, node):
            node.id = names.setdefault(node.id, f"v{len(names)}")
            return node

        def visit_arg(self, node):
            node.arg = names.setdefault(node.arg, f"v{len(names)}")
            return node
    return ast.dump(R().visit(tree), annotate_fields=False)


def known_refs() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {"T10": [], "T2": [], "T03": []}
    for r in read_jsonl(DATA_DIR / "known_solutions_e.jsonl"):
        out.setdefault(r["task"], []).append(r)
    for r in read_jsonl(E18 / "known_solutions.jsonl"):
        t = {"T02": "T2"}.get(r.get("task"), r.get("task"))
        if t in out:
            out[t].append({"task": t, "source": f"exp18:{r.get('source')}", "id": r.get("mode_hint"),
                           "mode_hint": r.get("mode_hint"), "code": r["code"]})
    for t in out:
        for r in out[t]:
            r["_norm"] = norm_ast(r["code"])
    return out


def nearest(code: str, refs: list[dict[str, Any]], k: int = 3) -> list[dict[str, Any]]:
    n = norm_ast(code)
    scored = []
    for r in refs:
        sm = difflib.SequenceMatcher(None, n, r["_norm"], autojunk=False)
        scored.append((sm.quick_ratio(), r))
    scored.sort(key=lambda x: -x[0])
    top = []
    for q, r in scored[:25]:
        top.append((difflib.SequenceMatcher(None, n, r["_norm"], autojunk=False).ratio(), r))
    top.sort(key=lambda x: -x[0])
    return [{"ratio": round(q, 4), "source": r["source"], "id": r.get("id"), "mode_hint": r.get("mode_hint"),
             "code": r["code"][:2500]} for q, r in top[:k]]


def prompt(task: str, code: str, refs: list[dict[str, Any]]) -> str:
    rs = "\n\n".join(f"KNOWN SOLUTION {i + 1} ({r['source']}, hint: {r['mode_hint']}):\n```python\n{r['code']}\n```"
                     for i, r in enumerate(refs))
    return (f"You audit a Python program that correctly solves this task: {SPECS[task]}.\n"
            f"ALGORITHM CATALOGUE for this task: {CATALOGUE[task]}.\n"
            "Classify the PROGRAM into exactly one class:\n"
            "- LABELLER MISS: it implements a catalogue algorithm in substance;\n"
            "- CATALOGUE VARIANT: a catalogue algorithm with minor changes, hybrids or an equivalent data structure;\n"
            "- KNOWN TECHNIQUE OUTSIDE THE CATALOGUE: a named textbook/published method not in the catalogue;\n"
            "- DEGENERATE: hard-coding, test-specific shortcuts, library calls that bypass the algorithm, or brute "
            "force that passes only because inputs are small;\n"
            "- NOVEL ALGORITHM: none of the above; you must state the mechanism and why no known algorithm matches.\n\n"
            f"{rs}\n\nPROGRAM:\n```python\n{code[:6000]}\n```\n\n"
            'Answer with JSON only: {"class": "<one of the five classes>", "mechanism": "<one sentence>", '
            '"nearest_known": "<algorithm name>"}')


def parse(text: str | None) -> str | None:
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            c = json.loads(m.group(0)).get("class", "")
            for k in CLASSES:
                if c.strip().upper() == k:
                    return k
        except json.JSONDecodeError:
            pass
    for k in CLASSES:
        if k in text.upper():
            return k
    return None


class Budget:
    def __init__(self, cap: float):
        self.cap = cap
        self.spent = sum(r.get("cost", 0.0) for r in read_jsonl(CACHE))
        self.stop = False
        self.reason: str | None = None


async def call(client: Any, sem: asyncio.Semaphore, bud: Budget, model: str, text: str, key: str,
               cache: dict[str, Any]) -> str | None:
    if key in cache:
        return cache[key]["text"]
    async with sem:
        if bud.stop:          # checked after the slot is acquired
            return None
        if bud.spent >= bud.cap:
            bud.stop, bud.reason = True, f"artifact cap {bud.cap} USD reached"
            return None
        try:
            r = await client.chat.completions.create(model=model, messages=[{"role": "user", "content": text}],
                                                     temperature=0, max_tokens=250, timeout=90)
        except Exception as e:  # noqa: BLE001 - classify budget refusals, log the rest
            msg = str(e)
            if BUDGET_MSG in msg or ("403" in msg and "budget" in msg.lower()):
                bud.stop, bud.reason = True, f"budget 403: {msg[:200]}"
                logger.error(f"OpenRouter budget refusal -> stopping the batch: {msg[:200]}")
            else:
                logger.warning(f"{model} call failed: {msg[:200]}")
            return None
        out = r.choices[0].message.content or ""
        cost = 0.0
        try:
            cost = float(getattr(r.usage, "cost", None) or (r.usage.model_extra or {}).get("cost", 0.0))
        except (AttributeError, TypeError, ValueError):
            cost = 0.0
        bud.spent += cost
        rec = {"key": key, "model": model, "text": out, "cost": cost, "utc": utc_now()}
        cache[key] = rec
        append_jsonl(CACHE, [rec])
        logger.debug(f"{model} -> {out[:160]!r} (cost {cost:.5f}, total {bud.spent:.4f})")
        return out


async def audit(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], Budget]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"])
    cache = {r["key"]: r for r in read_jsonl(CACHE)}
    bud = Budget(JUDGE_CAP_USD_E)
    sem = asyncio.Semaphore(8)

    async def one(it: dict[str, Any]) -> dict[str, Any]:
        txt = prompt(it["task"], it["code"], it["nearest"])
        a, b = await asyncio.gather(*[call(client, sem, bud, m, txt, f"{m}|{it['task']}|{it['code_sha256']}", cache)
                                      for m in JUDGES])
        ca, cb = parse(a), parse(b)
        res = {"judge_a": ca, "judge_b": cb}
        if ca and cb and ca != cb:
            c = await call(client, sem, bud, TIEBREAK, txt, f"{TIEBREAK}|{it['task']}|{it['code_sha256']}", cache)
            cc = parse(c)
            res["tiebreak"] = cc
            votes = Counter([ca, cb, cc])
            top = votes.most_common(1)[0]
            res["final"] = top[0] if top[1] >= 2 else "UNRESOLVED"
        else:
            res["final"] = ca if ca == cb else (ca or cb)
        res["raw_a"], res["raw_b"] = (a or "")[:400], (b or "")[:400]
        return {**{k: v for k, v in it.items() if k != "code"}, **res}

    out = await asyncio.gather(*[one(it) for it in items])
    await client.close()
    return list(out), bud


def main() -> None:
    import analysis_e as A

    setup_logging("novelty")
    rows = A.merge_rows(out_p=None)
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    n_cells: Counter = Counter()
    for r in rows:
        if r.get("label") == "other" and r.get("passed") and r.get("code"):
            key = (r["task"], r["code_sha256"])
            n_cells[(r["task"], r["precision"], r["arm"])] += 1
            if key not in seen:
                seen[key] = {"task": r["task"], "code_sha256": r["code_sha256"], "code": r["code"],
                             "first_sample_id": r["sample_id"], "n_rows": 0}
            seen[key]["n_rows"] += 1
    refs = known_refs()
    items = list(seen.values())
    for it in items:
        it["nearest"] = nearest(it["code"], refs.get(it["task"], []))
    logger.info(f"novelty audit: {len(items)} unique correct 'other' programs; refs "
                f"{ {t: len(v) for t, v in refs.items()} }")
    res, bud = asyncio.run(audit(items)) if items else ([], Budget(JUDGE_CAP_USD_E))
    cls = Counter(r["final"] for r in res)
    n = len(res)
    novel = cls.get("NOVEL ALGORITHM", 0)
    out = {"utc": utc_now(), "n_unique_correct_other": n, "n_rows_correct_other": int(sum(n_cells.values())),
           "by_cell": {"|".join(k): v for k, v in sorted(n_cells.items())}, "classes": dict(cls),
           "novel_count": novel,
           "statement": (f"no correct novel algorithm (0 of {n}; rule-of-three 95% upper bound {3 / n:.3f})" if n and
                         novel == 0 else ("no correct 'other' programs to audit" if n == 0 else
                                          f"{novel} program(s) judged NOVEL: see items")),
           "spend_usd": round(bud.spent, 5), "stopped": bud.stop, "stop_reason": bud.reason,
           "judges": list(JUDGES), "tiebreak": TIEBREAK,
           "items": [{k: v for k, v in r.items() if k != "nearest"} | {"nearest": [
               {kk: vv for kk, vv in q.items() if kk != "code"} for q in r.get("nearest", [])]} for r in res]}
    write_json(RESULTS_DIR / "novelty_audit.json", out)
    write_json(RESULTS_DIR / "costs.json", {"openrouter_novelty_usd": round(bud.spent, 5),
                                            "openrouter_labeller_judges": "see results/openrouter_cost_paths.json and "
                                                                          "logs (label worker)", "cap_usd": JUDGE_CAP_USD_E})
    logger.info(f"novelty audit done: {dict(cls)}; spend {bud.spent:.4f} USD")


if __name__ == "__main__":
    main()
