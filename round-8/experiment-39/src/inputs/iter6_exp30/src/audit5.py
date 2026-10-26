#!/usr/bin/env python3
"""Judge audits (OpenRouter; plan S2.4, S6 style re-gate, S7 novelty audit). Sub-caps (USD): lexicon 0.05, re-gate
0.25, novelty 0.15; running total from usage.cost; the first HTTP 403 'AI Inventor per-run OpenRouter budget' stops
the whole batch. Answers are cached in audit/llm_cache.jsonl (a re-run makes no new calls), spend in
audit/llm_spend.jsonl.

  lexicon   20 literal-cell traces (4 per T arm): a cheap judge reads the first ~3,000 thinking tokens and names the
            first approach considered; agreement with the committed lexicon (src/lexicon.py).
  regate    stratified sample of correct programs of the new arms (IFG, PSL, EAP, BINT, DMD): 30 per decisive task,
            10 per non-decisive task; two blind judges (gemini-2.5-flash-lite, gpt-4.1-mini) label the mechanism from
            the task's catalogue; disagreement -> tie-break (deepseek); runtime-vs-adjudicated agreement per task,
            flag < 0.9; structural audit of the default vs runner-up (T2 heap vs array Dijkstra, T03 size-k heap vs
            heapify-pop, T10/T1 DFS vs BFS).
  novelty   every CORRECT 'other' program of every arm (literal cell included): two blind judges classify NOVEL
            ALGORITHM / CATALOGUE VARIANT (named) / LABELLER MISS / DEGENERATE, deepseek on disagreement; the nearest
            known solution by identifier-normalised AST-shingle Jaccard (known solutions of art_j3Rm_lr2nzR6 + the
            catalogue references); rule-of-three bound on the novel rate.

usage: .venv/bin/python src/audit5.py {lexicon|regate|novelty|all}
"""

from __future__ import annotations

import ast
import asyncio
import hashlib
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger

from cfg import AUDIT_DIR, BENCH, DATA_DIR, INPUTS, SUITE, append_jsonl, read_json, read_jsonl, setup_logging, write_json
from cfg5 import D5, JUDGE_A, JUDGE_B, JUDGE_TIE, ND10, SUBCAPS

CACHE = AUDIT_DIR / "llm_cache.jsonl"
SPEND = AUDIT_DIR / "llm_spend.jsonl"
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
_STATE = {"stop": False, "spent": defaultdict(float)}
_CACHE: dict[str, Any] = {}


def _load_cache() -> None:
    for r in read_jsonl(CACHE):
        _CACHE[r["key"]] = r["answer"]
    for r in read_jsonl(SPEND):
        _STATE["spent"][r["ledger"]] += float(r.get("cost") or 0.0)


async def ask(client, model: str, prompt: str, ledger: str, sem: asyncio.Semaphore, max_tokens: int = 120) -> str | None:
    key = hashlib.sha256(f"{model}|{prompt}".encode()).hexdigest()
    if key in _CACHE:
        return _CACHE[key]
    async with sem:
        if _STATE["stop"] or _STATE["spent"][ledger] >= SUBCAPS[ledger]:
            return None
        for attempt in range(3):
            try:
                r = await client.chat.completions.create(
                    model=model, messages=[{"role": "user", "content": prompt}], temperature=0.0, max_tokens=max_tokens,
                    extra_body={"usage": {"include": True}})
                ans = (r.choices[0].message.content or "").strip()
                cost = float(getattr(r.usage, "cost", None) or (r.usage.model_extra or {}).get("cost", 0.0) or 0.0) \
                    if r.usage is not None else 0.0
                _STATE["spent"][ledger] += cost
                append_jsonl(SPEND, [{"ledger": ledger, "model": model, "cost": cost}])
                append_jsonl(CACHE, [{"key": key, "model": model, "answer": ans}])
                _CACHE[key] = ans
                logger.debug(f"{ledger} {model}: {ans[:80]!r} (${cost:.5f})")
                return ans
            except Exception as e:  # noqa: BLE001 - classify budget refusals, retry transient errors
                msg = str(e)
                if "403" in msg and BUDGET_MSG in msg:
                    logger.error(f"OpenRouter budget refusal: stopping the batch ({msg[:120]})")
                    _STATE["stop"] = True
                    return None
                logger.warning(f"{model} attempt {attempt}: {msg[:160]}")
                await asyncio.sleep(2 + 3 * attempt)
        return None


def client():
    from openai import AsyncOpenAI

    return AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"], timeout=90)


def _json_label(ans: str | None, allowed: list[str]) -> str | None:
    if not ans:
        return None
    m = re.search(r"\{.*\}", ans, re.S)
    if m:
        try:
            v = json.loads(m.group(0))
            lab = str(v.get("label") or v.get("class") or v.get("approach") or "").strip().lower()
            for a in allowed:
                if lab == a.lower():
                    return a
        except json.JSONDecodeError:
            pass
    low = ans.lower()
    for a in sorted(allowed, key=len, reverse=True):
        if re.search(rf"\b{re.escape(a.lower())}\b", low):
            return a
    return None


# ------------------------------------------------------------------------------------------------ catalogue
def catalogue(task: str) -> list[dict[str, str]]:
    if task in ("T1", "T2"):
        p = SUITE / "tasks" / ("t1_grid" if task == "T1" else "t2_wsp")
        for name in ("catalogue.json", "spec.json", "task.json"):
            if (p / name).exists():
                d = read_json(p / name)
                cat = d.get("catalogue") or d.get("modes")
                if isinstance(cat, list) and cat and isinstance(cat[0], dict):
                    return [{"mode": c.get("mode") or c.get("name"), "mechanism": c.get("mechanism", "")} for c in cat]
        gr = read_json(SUITE / "labeller" / "gate_report.json")["references"]
        vals = gr.values() if isinstance(gr, dict) else gr
        pref = "t1/" if task == "T1" else "t2/"
        keys = gr.keys() if isinstance(gr, dict) else []
        modes = sorted({v["mode"] for k, v in zip(keys, vals) if str(k).startswith(pref)}) or \
            sorted({v["mode"] for v in vals})
        return [{"mode": m, "mechanism": ""} for m in modes]
    import prompts_v4 as P4
    sp = read_json(BENCH / P4.bench_dir(task) / "spec.json")
    return [{"mode": c["mode"], "mechanism": c["mechanism"]} for c in sp["catalogue"]]


def spec_text(task: str) -> str:
    from prompts5 import load_prompts
    pr = load_prompts()
    return pr[(task, "ALL", "plain")]["user_text"]


# ------------------------------------------------------------------------------------------------ lexicon
async def run_lexicon() -> dict[str, Any]:
    from lexicon import first_approach
    from cfg5 import FIRST_APPROACH_LEXICON
    raw = read_jsonl(DATA_DIR / "literal_raw.jsonl")
    by = defaultdict(list)
    for r in raw:
        by[r["arm"]].append(r)
    rng = random.Random(20261021)
    pick = [r for arm in sorted(by) for r in rng.sample(by[arm], min(4, len(by[arm])))]
    allowed = [n for n, _ in FIRST_APPROACH_LEXICON] + ["none"]
    c = client()
    sem = asyncio.Semaphore(8)
    prompts = []
    for r in pick:
        txt = r["think_text"][:12000]
        prompts.append("Below is the beginning of a model's reasoning trace for a shortest-path coding task. Which "
                       "algorithm does it consider FIRST (the earliest one it names or starts to apply)? Answer with JSON "
                       f"{{\"label\": <one of {allowed}>}} only.\n\n---\n{txt}\n---")
    answers = await asyncio.gather(*[ask(c, JUDGE_A, p, "lexicon", sem, 30) for p in prompts])
    rows = []
    for r, a in zip(pick, answers):
        j = _json_label(a, allowed)
        rows.append({"sample_id": r["sample_id"], "arm": r["arm"], "lexicon": first_approach(r["think_text"])[0], "judge": j})
    ok = [x for x in rows if x["judge"] is not None]
    res = {"n": len(rows), "n_judged": len(ok), "agreement": sum(x["lexicon"] == x["judge"] for x in ok) / len(ok) if ok else None,
           "judge_model": JUDGE_A, "rows": rows, "spent_usd": _STATE["spent"]["lexicon"]}
    write_json(AUDIT_DIR / "lexicon_audit.json", res)
    logger.info(f"lexicon audit: agreement {res['agreement']} on {len(ok)}")
    return res


# ------------------------------------------------------------------------------------------------ rows
def merged_rows() -> list[dict[str, Any]]:
    labs = {r["sample_id"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl")}
    out = []
    for r in read_jsonl(DATA_DIR / "samples_raw.jsonl"):
        l = labs.get(r["sample_id"])
        if l is not None and l.get("code"):
            out.append({**l, "arm": r["arm"], "task": r["task"]})
    return out


def structural(task: str, code: str) -> str | None:
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return None
    names = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)} | \
            {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    if task == "T2":
        return "heap" if ({"heappush", "heappop"} & names or "heapq" in names) else "array_or_other"
    if task == "T03":
        if "heapify" in names and "heappop" in names:
            return "heapify_pop"
        if {"heappush", "heappushpop", "heapreplace", "nsmallest", "nlargest"} & names:
            return "size_k_heap"
        return None
    if task in ("T10", "T1"):
        if "deque" in names or "popleft" in names:
            return "bfs"
        rec = any(isinstance(n, ast.FunctionDef) and any(isinstance(c, ast.Call) and getattr(c.func, "id", None) == n.name
                                                       for c in ast.walk(n)) for n in ast.walk(tree))
        return "dfs" if rec or "stack" in names else None
    return None


async def run_regate() -> dict[str, Any]:
    rows = [r for r in merged_rows() if r.get("passed") and r["arm"] in
            ("IFG_hot", "IFG_paper", "PSL", "EAP", "BINT", "DMD_a1", "DMD_a2")]
    rng = random.Random(7)
    by = defaultdict(list)
    for r in rows:
        by[r["task"]].append(r)
    sample = []
    for t, rs in by.items():
        n = 30 if t in D5 else 10
        sample += rng.sample(rs, min(n, len(rs)))
    c = client()
    sem = asyncio.Semaphore(12)

    def prompt(r):
        cat = catalogue(r["task"])
        lines = "\n".join(f"- {x['mode']}: {x['mechanism']}" for x in cat)
        return ("You label the ALGORITHM (mechanism) a Python program uses for a task. Catalogue of mechanisms:\n"
                f"{lines}\n- other: none of the above\nTask:\n{spec_text(r['task'])[:1500]}\n\nProgram:\n```python\n"
                f"{r['code'][:4000]}\n```\nAnswer with JSON {{\"label\": <one catalogue mode or other>}} only.")
    ps = [prompt(r) for r in sample]
    allowed_by = {t: [x["mode"] for x in catalogue(t)] + ["other"] for t in by}
    a1 = await asyncio.gather(*[ask(c, JUDGE_A, p, "regate", sem, 30) for p in ps])
    a2 = await asyncio.gather(*[ask(c, JUDGE_B, p, "regate", sem, 30) for p in ps])
    l1 = [_json_label(a, allowed_by[r["task"]]) for a, r in zip(a1, sample)]
    l2 = [_json_label(a, allowed_by[r["task"]]) for a, r in zip(a2, sample)]
    dis = [i for i, (x, y) in enumerate(zip(l1, l2)) if x is not None and y is not None and x != y]
    a3 = await asyncio.gather(*[ask(c, JUDGE_TIE, ps[i], "regate", sem, 30) for i in dis])
    tie = {i: _json_label(a, allowed_by[sample[i]["task"]]) for i, a in zip(dis, a3)}
    per = defaultdict(lambda: {"n": 0, "agree": 0, "n_adj": 0})
    recs = []
    for i, r in enumerate(sample):
        adj = l1[i] if (l1[i] is not None and l1[i] == l2[i]) else tie.get(i)
        st = structural(r["task"], r["code"])
        recs.append({"sample_id": r["sample_id"], "task": r["task"], "arm": r["arm"], "runtime_label": r["label"],
                     "judge_a": l1[i], "judge_b": l2[i], "tie": tie.get(i), "adjudicated": adj, "structural": st})
        p = per[r["task"]]
        p["n"] += 1
        if adj is not None:
            p["n_adj"] += 1
            p["agree"] += int(adj == r["label"])
    per_task = {t: {**v, "agreement": v["agree"] / v["n_adj"] if v["n_adj"] else None} for t, v in per.items()}
    flagged = [t for t, v in per_task.items() if v["agreement"] is not None and v["agreement"] < 0.9]
    # structural audit of the default vs runner-up
    struct = {}
    for t in ("T2", "T03", "T10", "T1"):
        rs = [x for x in recs if x["task"] == t and x["structural"] is not None]
        struct[t] = {"n": len(rs), "runtime_vs_structural": dict(Counter(f"{x['runtime_label']}->{x['structural']}" for x in rs))}
    res = {"n_sampled": len(sample), "per_task": per_task, "flagged_tasks": flagged, "structural_audit": struct,
           "judges": [JUDGE_A, JUDGE_B, JUDGE_TIE], "spent_usd": _STATE["spent"]["regate"], "rows": recs,
           "stopped_by_budget": _STATE["stop"]}
    write_json(AUDIT_DIR / "style_regate.json", res)
    logger.info(f"style re-gate: {len(sample)} programs, flagged {flagged}, spent {_STATE['spent']['regate']:.3f}")
    return res


# ------------------------------------------------------------------------------------------------ novelty
def known_codes(task: str) -> list[tuple[str, str]]:
    out = []
    for r in read_jsonl(INPUTS / "exp19" / "data" / "known_solutions_dep.jsonl"):
        if r.get("task") == task and r.get("code"):
            out.append((r.get("label") or r.get("mode_hint") or "known", r["code"]))
    if task not in ("T1", "T2"):
        import prompts_v4 as P4
        for p in sorted((BENCH / P4.bench_dir(task) / "references").glob("*.py")):
            out.append((p.stem, p.read_text()))
    else:
        d = SUITE / "tasks" / ("t1_grid" if task == "T1" else "t2_wsp") / "references"
        for p in sorted(d.glob("*.py")):
            out.append((p.stem, p.read_text()))
    return out


def nearest(task: str, code: str) -> dict[str, Any]:
    from analysis.metrics_exp6 import normalise_tokens, shingles
    t = normalise_tokens(code)
    if not t:
        return {"nearest": None, "jaccard": None}
    s = shingles(t)
    best = (None, -1.0)
    for lab, kc in known_codes(task):
        kt = normalise_tokens(kc)
        if not kt:
            continue
        ks = shingles(kt)
        j = len(s & ks) / max(len(s | ks), 1)
        if j > best[1]:
            best = (lab, j)
    return {"nearest": best[0], "jaccard": best[1]}


async def run_novelty() -> dict[str, Any]:
    rows = [r for r in merged_rows() if r.get("passed") and r.get("label") == "other"]
    lit = {r["sample_id"]: r for r in read_jsonl(DATA_DIR / "literal_labels.jsonl") if r.get("passed") and r.get("label") == "other"}
    rows += [{**r, "arm": r.get("arm")} for r in lit.values()]
    uniq = {}
    for r in rows:
        uniq.setdefault((r["task"], r.get("code_sha256")), r)
    items = list(uniq.values())
    classes = ["NOVEL ALGORITHM", "CATALOGUE VARIANT", "LABELLER MISS", "DEGENERATE"]
    c = client()
    sem = asyncio.Semaphore(8)

    def prompt(r):
        cat = catalogue(r["task"])
        lines = "\n".join(f"- {x['mode']}: {x['mechanism']}" for x in cat)
        return ("A program passed every hidden test of the task below, but a mechanism labeller marked it 'other' (not in "
                f"the catalogue).\nCatalogue:\n{lines}\nTask:\n{spec_text(r['task'])[:1500]}\n\nProgram:\n```python\n"
                f"{r['code'][:4000]}\n```\nClassify it as one of {classes}: LABELLER MISS = it is a catalogue mechanism "
                "the labeller failed to recognise; CATALOGUE VARIANT = a known named algorithm outside this catalogue "
                "(name it); NOVEL ALGORITHM = no known algorithm; DEGENERATE = hard-coded or trivial special-casing. "
                "Answer JSON {\"class\": ..., \"mode_or_name\": ...} only.")
    ps = [prompt(r) for r in items]
    a1 = await asyncio.gather(*[ask(c, JUDGE_A, p, "novelty", sem, 60) for p in ps])
    a2 = await asyncio.gather(*[ask(c, JUDGE_B, p, "novelty", sem, 60) for p in ps])
    l1 = [_json_label(a, classes) for a in a1]
    l2 = [_json_label(a, classes) for a in a2]
    dis = [i for i, (x, y) in enumerate(zip(l1, l2)) if x is not None and y is not None and x != y]
    a3 = await asyncio.gather(*[ask(c, JUDGE_TIE, ps[i], "novelty", sem, 60) for i in dis])
    tie = {i: _json_label(a, classes) for i, a in zip(dis, a3)}
    recs, relabel = [], {}
    for i, r in enumerate(items):
        cls = l1[i] if (l1[i] is not None and l1[i] == l2[i]) else tie.get(i)
        nn = nearest(r["task"], r["code"])
        mode = None
        for a in (a1[i], a2[i]):
            if a:
                m = re.search(r"\{.*\}", a, re.S)
                if m:
                    try:
                        mode = json.loads(m.group(0)).get("mode_or_name") or mode
                    except json.JSONDecodeError:
                        pass
        recs.append({"task": r["task"], "arm": r.get("arm"), "code_sha256": r.get("code_sha256"), "judge_a": l1[i],
                     "judge_b": l2[i], "tie": tie.get(i), "class": cls, "named": mode, **nn})
        cats = {x["mode"] for x in catalogue(r["task"])}
        if cls == "LABELLER MISS" and mode in cats:
            relabel[r.get("code_sha256")] = mode
    n_novel = sum(1 for x in recs if x["class"] == "NOVEL ALGORITHM")
    n = len(recs)
    res = {"n_unique_correct_other": n, "classes": dict(Counter(x["class"] for x in recs)), "n_novel": n_novel,
           "rule_of_three_upper95_novel_rate": (3 / n if n and n_novel == 0 else None), "rows": recs,
           "manual_pass": "automated nearest known solution (AST-shingle Jaccard over the dependency's known solutions "
                          "and the catalogue references); executor spot check recorded in audit/manual_pass.json if done",
           "spent_usd": _STATE["spent"]["novelty"], "stopped_by_budget": _STATE["stop"]}
    write_json(AUDIT_DIR / "novelty_audit.json", res)
    write_json(AUDIT_DIR / "novelty_relabel.json", {"relabel": relabel})
    logger.info(f"novelty audit: {n} unique correct 'other' programs: {res['classes']}")
    return res


async def main_async(what: str) -> None:
    _load_cache()
    if what in ("lexicon", "all"):
        await run_lexicon()
    if what in ("regate", "all") and not _STATE["stop"]:
        await run_regate()
    if what in ("novelty", "all") and not _STATE["stop"]:
        await run_novelty()


if __name__ == "__main__":
    setup_logging("audit5")
    asyncio.run(main_async(sys.argv[1] if len(sys.argv) > 1 else "all"))
