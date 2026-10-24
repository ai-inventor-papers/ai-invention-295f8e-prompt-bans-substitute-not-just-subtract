"""V3-T judges: gated OpenRouter judges for the novelty candidates (advisory; the written manual-read rule decides).

GATE per judge: 10 controls, >= 9 correct. 5 KNOWN controls = restyled corpus copies (renamed variables, reordered
terms) shown with the original among 3 references (must answer Q1 = yes); 5 named literature rules shown with 3
unrelated references (must be named in Q2). Candidates (<= 12, by G200) are shown blind to their arm with their 3
nearest corpus members by probe agreement. T = 0. Hard budget cap USD 0.50 for this module; GET <base>/key before each
batch; the first HTTP 403 'AI Inventor per-run OpenRouter budget' stops the whole batch.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RESULTS, setup_logging, utc_now, write_json  # noqa: E402

logger = setup_logging("judges")
JUDGES = ["deepseek/deepseek-chat-v3.1", "moonshotai/kimi-k2", "mistralai/mistral-medium-3.1"]
CAP_USD = 0.50
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
SIG = "def select_next_node(current_node, destination_node, unvisited_nodes, distance_matrix):\n"

NAMED = {
    "two-step look-ahead nearest neighbour": (r"look.?ahead|two.?step|2.?step", None),
    "regret-2 next city": (r"regret", None),
    "angle sweep around the centroid": (r"sweep|polar|angle|angular", None),
    "convex-hull-first construction": (r"hull", None),
    "ant-colony probability argmax": (r"\bant\b|aco|pheromone|ant.colony", None),
}

CONTROL_CODE = {
    "convex-hull-first construction": SIG + (
        "    import numpy as np\n    D = np.asarray(distance_matrix, float)\n    n = D.shape[0]\n"
        "    J = np.eye(n) - 1.0 / n\n    B = -0.5 * J @ (D ** 2) @ J\n    w, V = np.linalg.eigh(B)\n"
        "    X = V[:, -2:] * np.sqrt(np.maximum(w[-2:], 0))\n    U = sorted(unvisited_nodes)\n"
        "    def cross(o, a, b):\n        return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])\n"
        "    pts = sorted(range(n), key=lambda i: (X[i, 0], X[i, 1]))\n    lower, upper = [], []\n"
        "    for p in pts:\n        while len(lower) >= 2 and cross(X[lower[-2]], X[lower[-1]], X[p]) <= 0:\n"
        "            lower.pop()\n        lower.append(p)\n    for p in reversed(pts):\n"
        "        while len(upper) >= 2 and cross(X[upper[-2]], X[upper[-1]], X[p]) <= 0:\n            upper.pop()\n"
        "        upper.append(p)\n    hull = set(lower[:-1] + upper[:-1])\n"
        "    on_hull = [j for j in U if j in hull]\n    pool = on_hull if on_hull else U\n"
        "    return min(pool, key=lambda j: distance_matrix[current_node][j])\n"),
    "ant-colony probability argmax": SIG + (
        "    alpha, beta = 1.0, 2.0\n    tau = 1.0\n    best, best_p = None, -1.0\n    for j in unvisited_nodes:\n"
        "        eta = 1.0 / max(distance_matrix[current_node][j], 1e-12)\n        p = (tau ** alpha) * (eta ** beta)\n"
        "        if p > best_p:\n            best, best_p = j, p\n    return best\n"),
}

PROMPT = """You are an expert in combinatorial optimisation. Below is a CANDIDATE next-city rule for greedy
construction of a Travelling Salesman tour (select_next_node is called at every step with the current city, the
destination city 0, the set of unvisited cities and the distance matrix), followed by three REFERENCE rules.

CANDIDATE:
```python
{cand}
```

REFERENCE A:
```python
{a}
```

REFERENCE B:
```python
{b}
```

REFERENCE C:
```python
{c}
```

Q1: Is the CANDIDATE equivalent to, or a minor variant of (renamed variables, reordered terms, changed constants,
monotone transform of the same score), one of the references? Answer yes or no, and which one (A, B, C or none).
Q2: Is the CANDIDATE a named or otherwise well-known TSP construction rule from the literature? Answer yes or no, and
name it if yes.
Reply with JSON only: {{"q1": "yes|no", "which": "A|B|C|none", "q2": "yes|no", "name": "..."}}"""


def restyle(code: str) -> str:
    """Rename variables (KNOWN control): a mechanical restyle of a corpus copy."""
    ren = {"distance_matrix": "dist", "unvisited_nodes": "remaining", "current_node": "here",
           "destination_node": "home", "node": "city", "immediate_cost": "step_cost", "scores": "vals"}
    out = code
    for k, v in ren.items():
        out = re.sub(rf"\b{k}\b", v, out)
    out = out.replace(f"def select_next_node(here, home, remaining, dist):", SIG.rstrip("\n"))
    out = re.sub(r"def select_next_node\([^)]*\):", "def select_next_node(here, home, remaining, dist):", out)
    return out


async def ask(client, model: str, content: str, state: dict) -> dict:
    if state["stop"]:
        return {"skipped": "budget stop"}
    async with state["sem"]:
        if state["stop"] or state["cost"] >= CAP_USD:
            state["stop"] = True
            return {"skipped": "budget stop"}
        try:
            r = await client.chat.completions.create(model=model, messages=[{"role": "user", "content": content}],
                                                     temperature=0, max_tokens=300,
                                                     extra_body={"usage": {"include": True}})
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            if "403" in msg and BUDGET_MSG in msg:
                state["stop"] = True
            return {"error": msg[:300]}
        cost = 0.0
        try:
            cost = float(getattr(r.usage, "cost", None) or (r.usage.model_extra or {}).get("cost") or 0.0)
        except (AttributeError, TypeError, ValueError):
            cost = 0.0
        state["cost"] += cost
        txt = r.choices[0].message.content or ""
        m = re.search(r"\{.*\}", txt, re.S)
        try:
            ans = json.loads(m.group(0)) if m else {}
        except json.JSONDecodeError:
            ans = {}
        return {"answer": ans, "raw": txt[:500], "cost": cost, "provider": getattr(r, "provider", None),
                "model": r.model}


def key_info() -> dict:
    import requests

    try:
        r = requests.get(os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/key",
                         headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}, timeout=30)
        return r.json()
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:200]}


async def main_async() -> None:
    from openai import AsyncOpenAI

    v3 = json.loads((RESULTS / "v3.json").read_text())
    corpus = json.loads((RESULTS / "corpus.json").read_text())
    cmem = {m["name"]: m for m in corpus["members"] if m.get("admitted")}
    cands = sorted(v3["candidates"], key=lambda c: c["G200"])[:12]
    client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"],
                         timeout=120, max_retries=1)
    state = {"cost": 0.0, "stop": False, "sem": asyncio.Semaphore(6)}
    out = {"utc": utc_now(), "key_before": key_info(), "judges": {}, "candidates": [], "cap_usd": CAP_USD}
    names = list(cmem)
    known_src = [n for n in names if n not in ("NN",)][:5]
    unrelated = [cmem[n]["code"] for n in ("NN", "llm4ad_tsp_construct_template", "reevo_seed_func_eoh_derived")
                 if n in cmem]
    from corpus import TEXTBOOK

    named_code = {"two-step look-ahead nearest neighbour": TEXTBOOK["textbook_two_step_lookahead_nn"][1],
                  "regret-2 next city": TEXTBOOK["textbook_regret2_next_city"][1],
                  "angle sweep around the centroid": TEXTBOOK["textbook_angle_sweep_centroid"][1],
                  **CONTROL_CODE}
    for judge in JUDGES[:2]:
        jobs = []
        for n in known_src:  # KNOWN controls: original is reference B
            others = [cmem[o]["code"] for o in names if o != n][:2]
            jobs.append(("known", n, PROMPT.format(cand=restyle(cmem[n]["code"]), a=others[0], b=cmem[n]["code"],
                                                   c=others[1])))
        for nm, code in named_code.items():
            jobs.append(("named", nm, PROMPT.format(cand=code, a=unrelated[0], b=unrelated[1], c=unrelated[2])))
        res = await asyncio.gather(*[ask(client, judge, p, state) for _, _, p in jobs])
        rows, correct = [], 0
        for (kind, nm, _), r in zip(jobs, res):
            a = r.get("answer", {})
            if kind == "known":
                ok = str(a.get("q1", "")).lower().startswith("y")
            else:
                ok = str(a.get("q2", "")).lower().startswith("y") and bool(
                    re.search(NAMED[nm][0], str(a.get("name", "")), re.I))
            correct += ok
            rows.append({"kind": kind, "control": nm, "correct": ok, **{k: v for k, v in r.items() if k != "raw"}})
        out["judges"][judge] = {"controls": rows, "n_correct": correct, "passes_gate": correct >= 9}
        logger.info(f"judge {judge}: {correct}/10 controls; cost so far ${state['cost']:.4f}")
    gated = [j for j, v in out["judges"].items() if v["passes_gate"]]
    for c in cands:
        near = [cmem[n]["code"] for n, _ in c["nearest_corpus"]]
        while len(near) < 3:
            near.append(cmem["NN"]["code"])
        p = PROMPT.format(cand=c["code"].split("\n\n", 1)[-1], a=near[0], b=near[1], c=near[2])
        res = await asyncio.gather(*[ask(client, j, p, state) for j in JUDGES[:2]])
        out["candidates"].append({"arm_seed": c["arm_seed"], "call_idx": c["call_idx"], "G200": c["G200"],
                                  "max_corpus_agreement": c["max_corpus_agreement"],
                                  "nearest": c["nearest_corpus"],
                                  "verdicts": {j: r.get("answer", r) for j, r in zip(JUDGES[:2], res)},
                                  "gated_judges": gated})
    out["cost_usd"] = state["cost"]
    out["budget_stopped"] = state["stop"]
    out["key_after"] = key_info()
    write_json(RESULTS / "judges.json", out)
    logger.info(f"judges done: {len(cands)} candidates, cost ${state['cost']:.4f}, gated={gated}")


if __name__ == "__main__":
    asyncio.run(main_async())
