"""Blind LLM judge (STEP 3.5) over OpenRouter. Sees only the task spec, the catalogue and the code: nothing about
arm, model or condition. Cached by (judge model, task, code sha256) in runs/judge_cache.jsonl.

Hard budget: running sum of usage.cost (or catalogue price x tokens) stops at JUDGE_BUDGET_USD; the first HTTP 403
'AI Inventor per-run OpenRouter budget' cancels every queued call.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RESULTS, RUNS, append_jsonl, read_jsonl, sha256_text  # noqa: E402
from prompts import SPEC  # noqa: E402

JUDGE_PRIMARY = "google/gemini-2.5-flash-lite"
JUDGE_SECOND = "deepseek/deepseek-v4.1-flash"
PRICES = {JUDGE_PRIMARY: (0.10, 0.40), JUDGE_SECOND: (0.03, 0.08)}  # USD per M tokens (in, out), from the catalogue
JUDGE_BUDGET_USD = 1.00
CACHE = RUNS / "judge_cache.jsonl"
COST_FILE = RESULTS / "judge_cost.json"

CATALOGUE_TEXT = {
    "t1": """bfs: breadth-first search (FIFO queue, or level-by-level frontier lists); cells explored in order of distance from start.
dfs: depth-first search (recursive, or an explicit LIFO stack); no iterative deepening.
bidir_bfs: bidirectional BFS; one frontier from start and one from goal that meet in the middle.
iddfs: iterative deepening DFS; depth-limited DFS repeated with an increasing depth limit.
astar_greedy: A* search (priority = cost so far + heuristic such as Manhattan distance) OR greedy best-first search (priority = heuristic only).
dijkstra_unit: Dijkstra / uniform-cost search with a priority queue keyed by distance only (no heuristic).""",
    "t2": """dijkstra: Dijkstra's algorithm with a binary heap / priority queue, OR the O(n^2) array version that repeatedly selects the unvisited node with minimum distance.
bellman_ford_spfa: Bellman-Ford (repeated relaxation of all edges, up to n-1 rounds) OR SPFA (queue-based Bellman-Ford that re-inserts improved nodes).
bidir_dijkstra: bidirectional Dijkstra (forward search from s and backward search from t over reversed edges).
floyd_warshall: all-pairs dynamic programming over intermediate nodes (triple loop over k, i, j).
dial: Dial's algorithm; buckets indexed by distance value.""",
}
LABELS = {"t1": ["bfs", "dfs", "bidir_bfs", "iddfs", "astar_greedy", "dijkstra_unit"],
          "t2": ["dijkstra", "bellman_ford_spfa", "bidir_dijkstra", "floyd_warshall", "dial"]}


def build_prompt(task: str, code: str) -> str:
    return f"""You are classifying which search algorithm a Python program implements.

TASK THE PROGRAM SOLVES:
{SPEC[task]}

ALGORITHM CATALOGUE (label: definition):
{CATALOGUE_TEXT[task]}
other:<sub-label>: anything else, with a short snake_case sub-label (e.g. other:library_call, other:bfs_ignoring_weights, other:exhaustive_enumeration, other:0_1_bfs, other:dag_dp, other:memoized_dfs, other:random_walk).

MERGING RULES: recursion vs iteration never matters; array-scan Dijkstra = dijkstra; A* and greedy best-first = astar_greedy; Bellman-Ford and SPFA = bellman_ford_spfa. Label what the code actually does, not what its comments or names claim. Correctness does not matter: label a buggy program by the algorithm it attempts.

PROGRAM:
```python
{code[:6000]}
```

Answer with JSON only: {{"label": "<one catalogue label or other:<sub-label>>", "confidence": <0..1>, "rationale": "<one sentence>"}}"""


def normalise(task: str, lab: str) -> str:
    lab = (lab or "").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {"a*": "astar_greedy", "astar": "astar_greedy", "a_star": "astar_greedy", "greedy_best_first": "astar_greedy",
               "bellman_ford": "bellman_ford_spfa", "spfa": "bellman_ford_spfa", "bidirectional_bfs": "bidir_bfs",
               "bidirectional_dijkstra": "bidir_dijkstra", "floyd": "floyd_warshall", "dijkstra_heap": "dijkstra",
               "uniform_cost_search": "dijkstra_unit", "ucs": "dijkstra_unit", "iterative_deepening": "iddfs",
               "dials": "dial", "dial_algorithm": "dial"}
    lab = aliases.get(lab, lab)
    if task == "t1" and lab == "dijkstra":
        lab = "dijkstra_unit"
    if task == "t2" and lab == "dijkstra_unit":
        lab = "dijkstra"
    if lab in LABELS[task]:
        return lab
    if lab.startswith("other"):
        sub = lab.split(":", 1)[1] if ":" in lab else "unspecified"
        sub = re.sub(r"[^a-z0-9_]", "", sub)[:40] or "unspecified"
    else:
        sub = re.sub(r"[^a-z0-9_]", "", lab)[:40] or "unparsed"
    canon = canonical_sub(task, sub)
    return canon if canon else "other:" + sub


def canonical_sub(task: str, sub: str) -> str | None:
    """Arm-blind canonicalisation: an 'other' sub-label that names a catalogue algorithm (e.g. buggy_bfs,
    incorrect_dijkstra_attempt, modified_bellman_ford) is mapped to that algorithm, because the judge was told to
    label buggy programs by the algorithm they attempt. Non-catalogue modes (e.g. T2 bfs_ignoring_weights) stay other."""
    s = sub.lower()
    if task == "t1":
        rules = [(("bidir", "bidirectional"), "bidir_bfs"), (("iddfs", "iterative_deepening", "depth_limited"), "iddfs"),
                 (("astar", "a_star", "best_first", "greedy_best"), "astar_greedy"),
                 (("dijkstra", "uniform_cost"), "dijkstra_unit"), (("bfs", "breadth"), "bfs"), (("dfs", "depth_first"), "dfs")]
    else:
        if ("bidir" in s or "bidirectional" in s) and "dijkstra" in s:
            return "bidir_dijkstra"
        if "ignoring_weight" in s or "ignores_weight" in s or "unweighted" in s:
            return None
        rules = [(("dijkstra",), "dijkstra"), (("bellman", "spfa"), "bellman_ford_spfa"), (("floyd",), "floyd_warshall"),
                 (("dial",), "dial")]
    for keys, lab in rules:
        if any(k in s for k in keys):
            return lab
    return None


class BudgetStop(Exception):
    pass


class Judge:
    def __init__(self, budget_usd: float = JUDGE_BUDGET_USD):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"],
                                  timeout=90, max_retries=2)
        self.budget = budget_usd
        prev = json.loads(COST_FILE.read_text()) if COST_FILE.exists() else {"usd": 0.0, "calls": 0}
        self.spent = float(prev["usd"])
        self.calls = int(prev["calls"])
        self.stopped = False
        self.cache = {(r["model"], r["task"], r["code_sha256"]): r for r in read_jsonl(CACHE)}

    def _save_cost(self) -> None:
        COST_FILE.write_text(json.dumps({"usd": self.spent, "calls": self.calls, "budget_usd": self.budget}, indent=1))

    async def one(self, sem: asyncio.Semaphore, model: str, task: str, code: str) -> dict | None:
        key = (model, task, sha256_text(code))
        if key in self.cache:
            return self.cache[key]
        async with sem:
            if self.stopped or self.spent >= self.budget:
                self.stopped = True
                return None
            try:
                resp = await self.client.chat.completions.create(
                    model=model, temperature=0, max_tokens=300,
                    messages=[{"role": "user", "content": build_prompt(task, code)}],
                    extra_body={"usage": {"include": True}})
            except Exception as e:  # noqa: BLE001 - classify the failure
                msg = str(e)
                if "AI Inventor per-run OpenRouter budget" in msg or "403" in msg:
                    logger.error(f"judge budget refusal: {msg[:200]}")
                    self.stopped = True
                    return None
                logger.warning(f"judge call failed ({model}): {msg[:200]}")
                return None
            if self.stopped:
                return None
            self.calls += 1
            u = resp.usage
            cost = None
            if u is not None:
                extra = getattr(u, "model_extra", None) or {}
                cost = extra.get("cost")
                if cost is None:
                    pin, pout = PRICES.get(model, (0.5, 2.0))
                    cost = (u.prompt_tokens * pin + u.completion_tokens * pout) / 1e6
            self.spent += float(cost or 0.0)
            text = resp.choices[0].message.content or ""
            m = re.search(r"\{.*\}", text, re.DOTALL)
            lab, conf, rat = None, None, ""
            if m:
                try:
                    j = json.loads(m.group(0))
                    lab, conf, rat = j.get("label"), j.get("confidence"), j.get("rationale", "")
                except json.JSONDecodeError:
                    pass
            if lab is None:
                m2 = re.search(r'"label"\s*:\s*"([^"]+)"', text)
                lab = m2.group(1) if m2 else "other:unparsed"
            row = {"model": model, "task": task, "code_sha256": key[2], "label": normalise(task, lab), "raw_label": lab,
                   "confidence": conf, "rationale": str(rat)[:300], "cost": cost}
            self.cache[key] = row
            append_jsonl(CACHE, [row])
            if self.calls % 50 == 0:
                self._save_cost()
                logger.info(f"judge calls={self.calls} spent=${self.spent:.4f}")
            return row

    async def batch(self, items: list[tuple[str, str]], model: str = JUDGE_PRIMARY, concurrency: int = 8) -> list[dict | None]:
        sem = asyncio.Semaphore(concurrency)
        res = await asyncio.gather(*[self.one(sem, model, t, c) for t, c in items], return_exceptions=True)
        self._save_cost()
        out = []
        for r in res:
            out.append(None if isinstance(r, BaseException) else r)
        return out


def judge_items(items: list[tuple[str, str]], model: str = JUDGE_PRIMARY, budget_usd: float = JUDGE_BUDGET_USD):
    j = Judge(budget_usd)
    res = asyncio.run(j.batch(items, model))
    return res, {"spent_usd": j.spent, "calls": j.calls, "stopped": j.stopped}


if __name__ == "__main__":
    # smoke test: 5 calls on catalogue references
    from common import REFS
    items = [("t1", (REFS / "t1" / f"{n}.py").read_text()) for n in ("bfs", "dfs_rec", "astar")] + \
            [("t2", (REFS / "t2" / f"{n}.py").read_text()) for n in ("dijkstra_array", "dial")]
    res, info = judge_items(items)
    for r in res:
        print(r and {k: r[k] for k in ("label", "confidence", "cost")})
    print(info)
