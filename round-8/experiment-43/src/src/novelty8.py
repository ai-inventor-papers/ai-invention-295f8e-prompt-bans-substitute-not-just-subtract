#!/usr/bin/env python3
"""S8 judges (OpenRouter, cheapest adequate models, running usage.cost total, stop at the first 403 budget refusal,
cap USD 0.6): (a) the Llama labeller style re-gate (30 fit programs per Llama unit, 10 minority where available; two
blind judges of different families + a tiebreak; agreement with the frozen labellers >= 0.9 or the adjudicated column
becomes primary); (b) adjudication of every sweep cell with > 20% 'other' (the adjudicated column is then primary);
(c) the novelty audit of every CORRECT 'other' program: its three nearest known solutions in the 18k-solution corpus
built from the dependency art_j3Rm_lr2nzR6 (all ten datasets' code outputs) plus unit/bench references, two judges
gated on known-class controls, a third on disagreement; manual reads are recorded in results/novelty_manual.json.
Usage: novelty8.py regate | adjudicate | audit | corpus
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import sys
from collections import Counter
from typing import Any

import numpy as np
from loguru import logger

from cfg8 import (BUDGET_MSG, DATA_DIR, INPUTS, JUDGE_CAP_USD, LABELS, RESULTS_DIR, SAMPLES_RAW, SRCS, TEMPLATES,
                  THRESH, UNITS, append_jsonl, read_json, read_jsonl, setup_logging, utc_now, write_json)

JUDGES = ("google/gemini-2.5-flash-lite", "mistralai/mistral-small-3.2-24b-instruct")
TIEBREAK = "deepseek/deepseek-chat-v3.1"
STATE = {"spent": 0.0, "stop": False, "calls": 0}
COSTS = RESULTS_DIR / "costs.json"
JCACHE = DATA_DIR / "judge_cache.jsonl"

T1_MECH = {"bfs": "breadth-first search with a FIFO queue (deque/popleft), first-in first-out frontier",
           "dfs": "depth-first search: recursion or an explicit LIFO stack (pop from the end)",
           "astar_gbfs": "best-first search with a heap ordered by a heuristic (A* or greedy best-first)",
           "dijkstra": "uniform-cost search with a heap ordered by path cost, no heuristic",
           "bibfs": "bidirectional BFS growing frontiers from start and goal",
           "iddfs": "iterative deepening depth-first search with a depth limit"}
QWEN_MECH = {
    "B3": {"kruskal": "take roads in increasing cost and keep a road when it joins two components (union-find)",
           "prim_heap": "grow one component from a start city, adding the cheapest leaving road found with a heap",
           "prim_array": "grow one component, cheapest known cost per city in an array, O(n^2) scan",
           "boruvka": "in rounds, add the cheapest road leaving every component"},
    "A3": {"two_pointers": "move a left and a right index inward with running maxima on each side",
           "prefix_suffix_max": "precompute left-maximum and right-maximum arrays, then sum min(left, right) - h",
           "monotonic_stack": "a stack of indices with decreasing heights, popping to fill bounded basins",
           "peak_split": "split at the highest bar and sweep from each end towards it"},
    "B6": {"sort_compare": "sort the letters of both strings and compare",
           "hash_count": "count letters in a dict or Counter and compare or decrement",
           "fixed_count_array": "26 integer counters indexed by ord(c) - ord('a')"}}


def bench_dir(task: str):
    for d in (INPUTS / "iter6_exp30" / "inputs" / "exp11" / "bench").iterdir():
        if d.name.startswith(task + "_"):
            return d
    return None


def mech(unit: str) -> tuple[str, dict[str, str]]:
    u = UNITS[unit]
    if unit in QWEN_MECH:
        return u["name"], QWEN_MECH[unit]
    if u["task"] == "T1":
        return ("find any valid path between two cells of a grid with walls (4-neighbour moves)", T1_MECH)
    spec = read_json(bench_dir(u["task"]) / "spec.json")
    m = {c["mode"]: c["mechanism"] for c in spec["catalogue"]}
    if u["task"] == "R6":
        m["linear_scan"] = "scan the list from left to right (and/or right to left) comparing each value to target"
    return spec["description"][:400], m


# ------------------------------------------------------------------------------------------------ judges
def _client():
    from openai import AsyncOpenAI
    return AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"],
                       timeout=90)


async def _call(client, sem, model: str, prompt: str) -> str | None:
    async with sem:
        if STATE["stop"] or STATE["spent"] >= JUDGE_CAP_USD:
            return None
        for attempt in range(3):
            if STATE["stop"]:
                return None
            try:
                r = await client.chat.completions.create(model=model, temperature=0,
                                                         messages=[{"role": "user", "content": prompt}],
                                                         max_tokens=200, extra_body={"usage": {"include": True}})
                u = getattr(r, "usage", None)
                cost = 0.0
                if u is not None:
                    cost = float(getattr(u, "cost", None) or (u.model_extra or {}).get("cost") or 0.0)
                STATE["spent"] += cost
                STATE["calls"] += 1
                txt = r.choices[0].message.content or ""
                logger.debug(f"judge {model}: {txt[:160]!r} cost {cost:.6f} total {STATE['spent']:.4f}")
                return txt
            except Exception as e:  # noqa: BLE001 - budget stop or transient error, both logged
                msg = str(e)
                if "403" in msg and BUDGET_MSG in msg:
                    STATE["stop"] = True
                    logger.error("OpenRouter budget refusal: stopping every judge call")
                    return None
                logger.warning(f"judge call failed ({model}, attempt {attempt}): {msg[:200]}")
                await asyncio.sleep(2 * (attempt + 1))
        return None


def prompt(unit: str, code: str) -> str:
    desc, m = mech(unit)
    modes = "\n".join(f"- {k}: {v}" for k, v in m.items())
    return (f"You classify the algorithm of a Python program for this task: {desc}\n\nMechanism catalogue:\n{modes}\n"
            f"- other: a mechanism not in the catalogue\n\nProgram:\n```python\n{code[:6000]}\n```\n\n"
            f"Answer with exactly one label from {list(m) + ['other']} on the first line, then one sentence.")


def parse(unit: str, txt: str | None) -> str | None:
    if not txt:
        return None
    first = txt.strip().splitlines()[0].strip().strip("`*'\". :").lower()
    labs = list(mech(unit)[1]) + ["other"]
    for l in sorted(labs, key=len, reverse=True):
        if first == l or first.startswith(l):
            return l
    for l in sorted(labs, key=len, reverse=True):
        if re.search(rf"\b{re.escape(l)}\b", txt.lower()):
            return l
    return None


async def _judge_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    client = _client()
    sem = asyncio.Semaphore(12)
    cache = {r["key"]: r for r in read_jsonl(JCACHE)}

    async def one(it: dict[str, Any], model: str) -> str | None:
        key = f"{model}|{it['unit']}|{hashlib.sha256(it['code'].encode()).hexdigest()}"
        if key in cache:
            return cache[key]["label"]
        txt = await _call(client, sem, model, prompt(it["unit"], it["code"]))
        lab = parse(it["unit"], txt)
        append_jsonl(JCACHE, [{"key": key, "model": model, "unit": it["unit"], "label": lab, "raw": (txt or "")[:300]}])
        return lab
    j1 = await asyncio.gather(*[one(it, JUDGES[0]) for it in items])
    j2 = await asyncio.gather(*[one(it, JUDGES[1]) for it in items])
    need = [i for i, (a, b) in enumerate(zip(j1, j2)) if a != b]
    j3 = dict(zip(need, await asyncio.gather(*[one(items[i], TIEBREAK) for i in need])))
    out = []
    for i, it in enumerate(items):
        a, b, c = j1[i], j2[i], j3.get(i)
        lab = a if a == b else (c if c in (a, b) else None)
        out.append({**{k: v for k, v in it.items() if k != "code"}, "j1": a, "j2": b, "j3": c, "label": lab})
    return out


def save_costs(tag: str) -> None:
    cur = read_json(COSTS) if COSTS.exists() else {}
    cur[tag] = {"usd": round(STATE["spent"], 6), "calls": STATE["calls"], "stopped_by_budget": STATE["stop"],
                "utc": utc_now()}
    cur["total_usd"] = round(sum(v["usd"] for k, v in cur.items() if isinstance(v, dict)), 6)
    write_json(COSTS, cur)


def _labels() -> dict[str, dict[str, Any]]:
    return {r["sid"]: r for r in read_jsonl(LABELS)}


def code_of(text: str) -> str:
    import oc8
    return oc8.code_part(text)


# ------------------------------------------------------------------------------------------------ (a) re-gate
def regate() -> dict[str, Any]:
    labs = _labels()
    rows = read_jsonl(SAMPLES_RAW)
    sel = read_json(RESULTS_DIR / "select_llama.json")["kept"] if (RESULTS_DIR / "select_llama.json").exists() else []
    res = {}
    for unit in ["L-T1"] + sel:
        fit = [r for r in rows if r["unit"] == unit and r["arm"] == "fit"]
        lab = [labs[r["sid"]]["label"] for r in fit]
        c = Counter(l for l in lab if l not in ("other", "invalid"))
        if not c:
            continue
        maj = c.most_common(1)[0][0]
        rng = np.random.default_rng(20261023)
        mino = [r for r, l in zip(fit, lab) if l not in (maj, "invalid")]
        rest = [r for r, l in zip(fit, lab) if l == maj]
        pick = list(rng.permutation(len(mino)))[:10]
        chosen = [mino[i] for i in pick] + [rest[i] for i in rng.permutation(len(rest))[:30 - len(pick)]]
        items = [{"sid": r["sid"], "unit": unit, "code": code_of(r["text"]), "frozen": labs[r["sid"]]["label"]}
                 for r in chosen]
        judged = asyncio.run(_judge_items(items))
        ok = [j for j in judged if j["label"] is not None]
        agree = sum(j["label"] == j["frozen"] for j in ok) / len(ok) if ok else None
        res[unit] = {"n": len(items), "n_adjudicated": len(ok), "agreement": agree,
                     "pass": agree is not None and agree >= THRESH["regate_agree"], "rows": judged}
        logger.info(f"re-gate {unit}: agreement {agree} on {len(ok)}")
    save_costs("regate")
    write_json(RESULTS_DIR / "regate.json", res)
    return {u: {k: v for k, v in r.items() if k != "rows"} for u, r in res.items()}


# ------------------------------------------------------------------------------------------------ (b) adjudicate
def adjudicate() -> dict[str, Any]:
    labs = _labels()
    rows = [r for r in read_jsonl(SAMPLES_RAW) if r["arm"] in ("sweep", "topk")]
    cells: dict[tuple, list[dict[str, Any]]] = {}
    for r in rows:
        cells.setdefault((r["unit"], r["arm"], r["T"]), []).append(r)
    items, flagged = [], []
    for key, rr in cells.items():
        oth = [r for r in rr if labs.get(r["sid"], {}).get("label") == "other"]
        if len(oth) > THRESH["other_adjudicate"] * len(rr):
            flagged.append({"unit": key[0], "arm": key[1], "T": key[2], "n_other": len(oth), "N": len(rr)})
            items += [{"sid": r["sid"], "unit": r["unit"], "code": code_of(r["text"])} for r in oth]
    out = asyncio.run(_judge_items(items)) if items else []
    append_jsonl(DATA_DIR / "adjudicated_labels.jsonl", [{"sid": o["sid"], "label": o["label"] or "other",
                                                          "j1": o["j1"], "j2": o["j2"], "j3": o["j3"]} for o in out])
    save_costs("adjudicate")
    res = {"flagged_cells": flagged, "n_programs": len(items),
           "relabelled": dict(Counter(o["label"] for o in out))}
    write_json(RESULTS_DIR / "adjudication.json", res)
    return res


# ------------------------------------------------------------------------------------------------ (c) novelty
def shingles(code: str, k: int = 5) -> set:
    toks = re.findall(r"[A-Za-z_]+|\d+|[^\sA-Za-z_\d]", code or "")
    toks = ["ID" if re.fullmatch(r"[A-Za-z_]+", t) and t not in KEYWORDS else t for t in toks]
    return {tuple(toks[i:i + k]) for i in range(max(0, len(toks) - k + 1))}


KEYWORDS = {"def", "return", "for", "while", "if", "else", "elif", "in", "not", "and", "or", "import", "from",
            "range", "len", "sorted", "sort", "heapq", "heappush", "heappop", "min", "max", "Counter", "dict", "list",
            "set", "append", "pop", "True", "False", "None", "break", "continue", "lambda", "ord", "sum", "zip",
            "deque", "popleft", "find", "index", "bisect_left", "bisect_right"}


def corpus() -> list[dict[str, Any]]:
    """Known-solution corpus: every code output of the ten datasets of art_j3Rm_lr2nzR6 (full_data_out.json; the
    18,237-solution corpus that art_lpQalcAXMGr1 indexed) plus unit and bench reference programs."""
    p = RESULTS_DIR / "known_corpus_index.json"
    dep = SRCS["dep"] / "full_data_out.json"
    out: list[dict[str, Any]] = []
    d = json.loads(dep.read_text())
    per = Counter()
    no_code = {}
    for ds in d["datasets"]:
        field = "input" if ds["dataset"] == "thealgorithms_python" else "output"     # its code sits in 'input'
        for i, ex in enumerate(ds["examples"]):
            code = ex.get(field) or ""
            if ("def " in code or "class " in code) and len(code) < 20000:
                out.append({"src": f"dep:{ds['dataset']}:{i}", "code": code})
                per[ds["dataset"]] += 1
        if not per.get(ds["dataset"]):
            no_code[ds["dataset"]] = {"n_examples": len(ds["examples"]), "reason": "no program text in this dataset "
                                      "(labels, execution traces or word norms)"}
    del d
    for b in (INPUTS / "iter6_exp30" / "inputs" / "exp11" / "bench").iterdir():
        refs = b / "references"
        if refs.exists():
            for f in refs.glob("*.py"):
                out.append({"src": f"bench_ref:{b.name}:{f.stem}", "code": f.read_text()})
                per["bench_references"] += 1
    for u in ("B3", "B6"):
        refs = INPUTS / "iter5_exp26" / "units" / u / "references"
        if refs.exists():
            for f in refs.glob("*.py"):
                out.append({"src": f"unit_ref:{u}:{f.stem}", "code": f.read_text()})
                per["unit_references"] += 1
    write_json(p, {"n": len(out), "per_source": dict(per), "datasets_without_code": no_code,
                   "dependency": "art_j3Rm_lr2nzR6/" + str(dep.name)})
    return out


def audit() -> dict[str, Any]:
    labs = _labels()
    adj = {r["sid"]: r["label"] for r in read_jsonl(DATA_DIR / "adjudicated_labels.jsonl")}
    rows = read_jsonl(SAMPLES_RAW)
    progs = []
    for r in rows:
        l = labs.get(r["sid"])
        if not l or not l.get("passed"):
            continue
        lab = adj.get(r["sid"], l["label"])
        bins = list(mech(r["unit"])[1])
        if lab in bins or lab in ("invalid",):
            continue
        progs.append({"sid": r["sid"], "unit": r["unit"], "arm": r["arm"], "label": lab, "code": code_of(r["text"])})
    seen, uniq = set(), []
    for p in progs:
        k = (p["unit"], p["code"].strip())
        if p["code"] and k not in seen:
            seen.add(k)
            uniq.append(p)
    n_correct = sum(1 for r in rows if labs.get(r["sid"], {}).get("passed"))
    res = {"scope": "every CORRECT program labelled outside the unit's catalogue (all arms)",
           "n_correct_programs_total": n_correct, "n_correct_other_rows": len(progs), "n_distinct": len(uniq),
           "programs": []}
    if uniq:
        pool = corpus()
        pool_sh = [(p["src"], shingles(p["code"])) for p in pool]
        controls = []
        for u in sorted({p["unit"] for p in uniq}):
            if UNITS[u]["family"] != "qwen" and UNITS[u]["task"] != "T1":
                for f in sorted((bench_dir(UNITS[u]["task"]) / "references").glob("*.py"))[:3]:
                    controls.append({"sid": f"control|{u}|{f.stem}", "unit": u, "code": f.read_text(),
                                     "known": f.stem})
        items = [{"sid": p["sid"], "unit": p["unit"], "code": p["code"]} for p in uniq[:60]] + controls[:10]
        judged = {j["sid"]: j for j in asyncio.run(_judge_items(items))}
        ctrl = [c for c in controls[:10] if c["sid"] in judged]
        res["controls"] = [{"known": c["known"], "judge": judged[c["sid"]]["label"]} for c in ctrl]
        res["control_accuracy"] = sum(judged[c["sid"]]["label"] == c["known"] for c in ctrl) / len(ctrl) if ctrl else None
        for p in uniq[:60]:
            s = shingles(p["code"])
            sc = sorted(((len(s & q) / max(1, len(s | q)), src) for src, q in pool_sh), reverse=True)[:3]
            j = judged.get(p["sid"], {})
            res["programs"].append({"sid": p["sid"], "unit": p["unit"], "arm": p["arm"], "labeller": p["label"],
                                    "nearest_known": [{"src": src, "shingle_jaccard": round(v, 3)} for v, src in sc],
                                    "judges": {k: j.get(k) for k in ("j1", "j2", "j3", "label")},
                                    "code": p["code"][:3000]})
        if len(uniq) > 60:
            res["truncated_to"] = 60
    save_costs("novelty_audit")
    n = n_correct
    res["rule_of_three_upper_bound_if_zero_novel"] = 3 / n if n else None
    res["utc"] = utc_now()
    write_json(RESULTS_DIR / "novelty_audit.json", res)
    return {k: v for k, v in res.items() if k != "programs"}


if __name__ == "__main__":
    setup_logging("novelty8")
    what = sys.argv[1]
    print({"regate": regate, "adjudicate": adjudicate, "audit": audit,
           "corpus": lambda: {"n": len(corpus())}}[what]())
