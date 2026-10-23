#!/usr/bin/env python3
"""Stage 9 novelty audit. Every correct row adjudicated 'other' (plus correct rows whose adjudication was a split)
goes to two blind judges together with its 3 nearest known solutions (Zhang-Shasha tree edit distance on normalised
ASTs; identifiers and constants dropped) from the known corpora: the iteration-7 known corpus (17k programs from the
dependency dataset), the dataset rows that name a grid/graph search, and the 15 T1 references. A program is 'novel'
only if both judges say so; 'no correct novel algorithm' is claimed only at a count of 0 (rule-of-three bound)."""

from __future__ import annotations

import ast
import asyncio
import collections
import json
import os
import re
from typing import Any

import aiohttp
import numpy as np
from loguru import logger

from common import (ADJ_PAIR, BUDGET_MSG, CONFIGS, INPUTS, RESULTS, T1_DESCRIPTION, add_cost, read_jsonl, trunc,
                    write_json)

GRID_RX = re.compile(r"grid|maze|matrix|path|bfs|dfs|breadth|depth|dijkstra|a\*|astar|a_star|shortest|neighbou?r",
                     re.IGNORECASE)


def norm_tree(code: str) -> Any:
    from zss import Node

    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return None

    def conv(n: ast.AST) -> Any:
        lab = type(n).__name__
        if isinstance(n, (ast.BinOp, ast.AugAssign)):
            lab += ":" + type(n.op).__name__
        elif isinstance(n, ast.Compare):
            lab += ":" + ",".join(type(o).__name__ for o in n.ops)
        elif isinstance(n, ast.Attribute):
            lab += ":" + n.attr
        node = Node(lab)
        for ch in ast.iter_child_nodes(n):
            if isinstance(ch, (ast.Load, ast.Store, ast.Del)):
                continue
            node.addkid(conv(ch))
        return node

    return conv(tree)


def node_hist(code: str) -> collections.Counter | None:
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return None
    c = collections.Counter(type(n).__name__ for n in ast.walk(tree))
    c.update("attr:" + n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute))
    return c


def _cos(a: collections.Counter, b: collections.Counter) -> float:
    keys = set(a) | set(b)
    va = np.array([a.get(k, 0) for k in keys], float)
    vb = np.array([b.get(k, 0) for k in keys], float)
    return float(va @ vb / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-12))


def known_corpus() -> list[dict[str, Any]]:
    out = []
    for r in read_jsonl(INPUTS / "exp34" / "cache" / "known_corpus.jsonl"):
        code = r.get("code") or ""
        if len(code) < 20000 and GRID_RX.search(code + " " + str(r.get("named") or "")):
            out.append({"source": f"exp34:{r.get('dataset')}", "named": r.get("named"), "code": code})
    for r in read_jsonl(INPUTS / "dataset" / "corpus_rows.jsonl"):
        out.append({"source": f"dataset:{r['source']}", "named": r.get("named"), "code": r["code"]})
    for p in sorted((INPUTS / "exp9" / "tasks" / "t1_grid" / "references").glob("*.py")):
        out.append({"source": "t1_reference", "named": p.stem, "code": p.read_text()})
    return out


def nearest(code: str, corpus: list[dict[str, Any]], hists: list[Any], top: int = 3) -> list[dict[str, Any]]:
    from zss import simple_distance

    h = node_hist(code)
    t = norm_tree(code)
    if h is None or t is None:
        return []
    size_c = sum(h.values())
    sims = [(_cos(h, hc) if hc is not None else -1.0, i) for i, hc in enumerate(hists)
            if hc is not None and 0.5 * size_c <= sum(hc.values()) <= min(2.0 * size_c, 1200)]
    sims.sort(reverse=True)
    res = []
    for _, i in sims[:top]:
        tc = norm_tree(corpus[i]["code"])
        if tc is None:
            continue
        d = simple_distance(t, tc)
        size = sum(hists[i].values()) + sum(h.values())
        res.append({"idx": i, "ted": int(d), "ted_norm": d / max(size, 1), "source": corpus[i]["source"],
                    "named": trunc(corpus[i]["named"], 120)})
    res.sort(key=lambda x: x["ted_norm"])
    return res[:3]


_W: dict[str, Any] = {}


def _nearest_worker(code: str) -> list[dict[str, Any]]:
    """Process-pool worker: corpus + histograms loaded once per worker."""
    if "corpus" not in _W:
        _W["corpus"] = known_corpus()
        _W["hists"] = [node_hist(c["code"]) for c in _W["corpus"]]
    return nearest(code, _W["corpus"], _W["hists"])


def _prompt(code: str, near: list[dict[str, Any]], corpus: list[dict[str, Any]]) -> str:
    ks = "\n\n".join(f"KNOWN SOLUTION {j + 1} ({n['source']}; {n['named']}):\n```python\n"
                     f"{trunc(corpus[n['idx']]['code'], 3000)}\n```" for j, n in enumerate(near))
    return (f"TASK:\n{T1_DESCRIPTION}\n\nPROGRAM UNDER AUDIT:\n```python\n{code}\n```\n\n{ks}\n\n"
            "Question: does the PROGRAM UNDER AUDIT implement a known path-search algorithm (one of the known solutions "
            "above, or any textbook algorithm such as BFS, DFS, A*, Dijkstra, bidirectional search, IDA*, wall "
            "following, random walk, flood fill / Lee algorithm, beam search, Bellman-Ford, union-find), or is its "
            "search strategy genuinely novel? Judge the mechanism, not names or comments. Answer with only JSON: "
            '{"verdict": "known" or "novel", "algorithm": <name of the known algorithm or null>, '
            '"rationale": <one sentence>}')


async def _judge(session: aiohttp.ClientSession, model: str, prompt: str) -> dict[str, Any] | None:
    url = os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/chat/completions"
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.0, "max_tokens": 300,
            "usage": {"include": True}}
    headers = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}
    for attempt in range(3):
        try:
            async with session.post(url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=180)) as r:
                txt = await r.text()
                if r.status == 403 and BUDGET_MSG in txt:
                    add_cost("novelty", 0.0, refused=True)
                    return None
                if r.status != 200:
                    await asyncio.sleep(3 * (attempt + 1))
                    continue
                d = json.loads(txt)
                add_cost("novelty", float((d.get("usage") or {}).get("cost") or 0.0))
                c = d["choices"][0]["message"].get("content") or ""
                m = re.search(r"\{.*\}", c, re.DOTALL)
                return json.loads(m.group(0)) if m else None
        except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError, KeyError):
            await asyncio.sleep(3 * (attempt + 1))
    return None


def audit(rows_by_config: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    cands = []
    for cid, rows in rows_by_config.items():
        for r in rows:
            if r.get("passed") and (r.get("adj_label") == "other" or r.get("needs_manual")):
                cands.append(r)
    n_correct = sum(1 for rows in rows_by_config.values() for r in rows if r.get("passed"))
    out: dict[str, Any] = {"n_correct_rows_screened": n_correct, "n_candidates": len(cands), "items": []}
    if cands:
        corpus = known_corpus()
        logger.info(f"novelty: {len(cands)} candidates vs corpus {len(corpus)}")
        import multiprocessing as mp
        from concurrent.futures import ProcessPoolExecutor

        with ProcessPoolExecutor(max_workers=5, mp_context=mp.get_context("spawn")) as ex:
            nears = list(ex.map(_nearest_worker, [r["code"] for r in cands]))
        items = []
        for r, near in zip(cands, nears):
            items.append({"uid": r["uid"], "config": r["config"], "arm": r["arm"], "adj_label": r.get("adj_label"),
                          "adj_other_name": r.get("adj_other_name"), "nearest": near,
                          "prompt": _prompt(r["code"], near, corpus)})

        async def run() -> list[Any]:
            async with aiohttp.ClientSession() as s:
                return await asyncio.gather(*[_judge(s, m, it["prompt"]) for it in items for m in ADJ_PAIR])

        res = asyncio.run(run())
        for j, it in enumerate(items):
            a, b = res[2 * j], res[2 * j + 1]
            it["judges"] = {ADJ_PAIR[0]: a, ADJ_PAIR[1]: b}
            va, vb = (a or {}).get("verdict"), (b or {}).get("verdict")
            it["manual_class"] = ("novel" if va == vb == "novel" else "known" if va == vb == "known" else "disputed")
            it.pop("prompt")
            out["items"].append(it)
    n_novel = sum(1 for it in out["items"] if it["manual_class"] == "novel")
    out["n_novel"] = n_novel
    out["claim"] = ("no correct novel algorithm" if n_novel == 0 else f"{n_novel} correct programs judged novel")
    out["rule_of_three_upper95"] = 3.0 / n_correct if n_correct else None
    out["configs"] = list(CONFIGS)
    write_json(RESULTS / "novelty_audit.json", out)
    return out
