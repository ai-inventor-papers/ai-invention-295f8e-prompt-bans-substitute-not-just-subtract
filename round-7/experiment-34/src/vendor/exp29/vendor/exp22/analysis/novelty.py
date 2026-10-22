#!/usr/bin/env python3
"""C3c novelty audit over every CORRECT program labelled 'other' in any push arm (POP, UPERP, UP, CLAMP, C2C, SWEEP).

Two blind judges from different families (google/gemini-2.5-flash, openai/gpt-4.1-mini) classify each program as
NOVEL ALGORITHM / CATALOGUE VARIANT (name) / LABELLER MISS (name) / DEGENERATE; a third model
(deepseek/deepseek-chat-v3.1) resolves disagreements. A mechanical pass lists the 3 nearest known solutions by AST
4-gram Jaccard (exp18's 472-solution index for T03 T04 T06 T1 T10 T2; the declared dependency art_j3Rm_lr2nzR6 --
mercury and LeetCode references -- for every task). Counts per arm; 'no correct novel algorithm' is claimed only at
0 NOVEL verdicts, with a rule-of-three 95% bound 3/n. Spend capped at USD 0.40 (usage.cost); the batch stops at the
first per-run budget 403. Results are cached in data/novelty_cache.jsonl.
"""

from __future__ import annotations

import json
import os
import re
import threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from cfg4 import (BUDGET_MSG, DATA_DIR, DEP, E18, JUDGE_NOVELTY_CAP_USD, LABELS, PATH_TASKS, RESULTS_DIR,
                  read_jsonl, sha256_text)
from describe import bench_dir, task_spec_text

JUDGES = {"A": "google/gemini-2.5-flash", "B": "openai/gpt-4.1-mini", "C": "deepseek/deepseek-chat-v3.1"}
PUSH_FAMILIES = ("POP", "UPERP", "UP", "CLAMP", "C2C", "SWEEP")
CACHE = DATA_DIR / "novelty_cache.jsonl"
_LOCK = threading.Lock()
STATE = {"usd": 0.0, "stop": False, "calls": 0}


def catalogue_text(task: str) -> str:
    if task in PATH_TASKS:
        from cfg4 import PATH_CATALOGUE
        from describe import mechanisms
        mech = mechanisms(task)
        return "\n".join(f"- {m}: {v[0]} -- {mech.get(m, '')}" for m, v in PATH_CATALOGUE[task].items())
    spec = json.loads((bench_dir(task) / "spec.json").read_text())
    return "\n".join(f"- {c['mode']}: {c['display_name']} -- {c['mechanism']}" for c in spec["catalogue"])


def prompt(task: str, code: str) -> str:
    return ("You audit whether a Python program implements a genuinely different algorithm from a known list.\n\n"
            f"Task given to the programmer:\n{task_spec_text(task)}\n\nKnown algorithms for this task:\n"
            f"{catalogue_text(task)}\n\nProgram:\n```python\n{code}\n```\n\n"
            "Classify the program's core mechanism (ignore names/comments; recursion vs iteration does not matter):\n"
            "NOVEL - a correct algorithm whose mechanism is none of the known ones and not a trivial variant;\n"
            "VARIANT:<mode> - a variant of a known algorithm (give its mode id);\n"
            "MISS:<mode> - plainly one of the known algorithms (a labeller miss);\n"
            "DEGENERATE - hard-coded, special-cased, or not a real algorithm.\n"
            "Answer with one line: CLASS: <NOVEL | VARIANT:<mode> | MISS:<mode> | DEGENERATE>, then one sentence.")


def parse(txt: str) -> str:
    m = re.search(r"CLASS:\s*(NOVEL|VARIANT:\s*[\w\-]+|MISS:\s*[\w\-]+|DEGENERATE)", txt or "", re.I)
    if not m:
        return "UNPARSED"
    c = m.group(1).upper().replace(" ", "")
    return c.split(":")[0] if c.startswith(("NOVEL", "DEGENERATE")) else c


def call(model: str, p: str) -> tuple[str, float]:
    from openai import OpenAI
    cli = OpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"], timeout=90)
    r = cli.chat.completions.create(model=model, temperature=0.0, max_tokens=200,
                                    messages=[{"role": "user", "content": p}], extra_body={"usage": {"include": True}})
    cost = 0.0
    try:
        u = r.usage.model_dump() if hasattr(r.usage, "model_dump") else dict(r.usage)
        cost = float(u.get("cost") or 0.0)
    except (AttributeError, TypeError, ValueError):
        pass
    return r.choices[0].message.content or "", cost


def judged(key: str, model: str, p: str, cache: dict[str, Any]) -> dict[str, Any] | None:
    ck = f"{model}|{key}"
    if ck in cache:
        return cache[ck]
    with _LOCK:
        if STATE["stop"] or STATE["usd"] >= JUDGE_NOVELTY_CAP_USD:
            return None
    try:
        txt, cost = call(model, p)
    except Exception as e:  # noqa: BLE001 - a judge failure leaves the item unjudged, never crashes the audit
        if BUDGET_MSG in str(e):
            STATE["stop"] = True
        return None
    rec = {"key": ck, "model": model, "class": parse(txt), "raw": txt[:300], "cost": cost}
    with _LOCK:
        STATE["usd"] += cost
        STATE["calls"] += 1
        cache[ck] = rec
        with open(CACHE, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
    return rec


def grams(code: str) -> set:
    import ast
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return set()
    seq = [type(n).__name__ for n in ast.walk(tree)]
    return {tuple(seq[i:i + 4]) for i in range(len(seq) - 3)}


def known(task: str) -> list[dict[str, Any]]:
    out = [r for r in read_jsonl(E18 / "inputs" / "known_solutions.jsonl") if r["task"] == task]
    out += [r for r in read_jsonl(DEP / "known_subset.jsonl") if r["task"] == task]
    return out


def run(rows: list[dict[str, Any]], commit: dict[str, Any], esc: dict[str, Any]) -> dict[str, Any]:
    codes = {l["code_sha256"]: l["code"] for l in read_jsonl(LABELS) if l.get("code_sha256")}
    items = [r for r in rows if r["family"] in PUSH_FAMILIES and r["passed"] and r["label"] == "other"]
    uniq: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in items:
        uniq[(r["task"], r["code_sha256"])].append(r)
    cache = {r["key"]: r for r in read_jsonl(CACHE)}
    jobs = []
    for (t, h), rr in uniq.items():
        code = codes.get(h)
        if code:
            jobs.append((t, h, code))

    def one(j):
        t, h, code = j
        p = prompt(t, code)
        a = judged(f"{t}|{h}", JUDGES["A"], p, cache)
        b = judged(f"{t}|{h}", JUDGES["B"], p, cache)
        ca, cb = (a or {}).get("class"), (b or {}).get("class")
        final, src = None, None
        if ca and cb and ca.split(":")[0] == cb.split(":")[0]:
            final, src = ca.split(":")[0], "A=B"
        elif ca and cb:
            c = judged(f"{t}|{h}", JUDGES["C"], p, cache)
            final, src = ((c or {}).get("class") or "UNRESOLVED").split(":")[0], "third"
        else:
            final, src = "UNJUDGED", "budget/api"
        g = grams(code)
        ks = known(t)
        sims = sorted(((len(g & grams(k["code"])) / max(len(g | grams(k["code"])), 1), k.get("source"),
                        str(k.get("mode_hint"))[:60]) for k in ks), reverse=True)[:3]
        return {"task": t, "code_sha256": h, "A": ca, "B": cb, "final": final, "source": src,
                "nearest_known": [{"jaccard": s, "source": so, "hint": hi} for s, so, hi in sims], "code": code}
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs))
    by_h = {(r["task"], r["code_sha256"]): r for r in res}
    per_arm: dict[str, Counter] = defaultdict(Counter)
    for (t, h), rr in uniq.items():
        fin = by_h.get((t, h), {}).get("final", "UNJUDGED")
        for r in rr:
            per_arm[f"{t}|{r['arm'].split('_')[0]}"][fin] += 1
    n_items = len(items)
    n_novel = sum(1 for r in items if by_h.get((r["task"], r["code_sha256"]), {}).get("final") == "NOVEL")
    n_correct_push = sum(1 for r in rows if r["family"] in PUSH_FAMILIES and r["passed"])
    out = {"n_correct_other_programs": n_items, "n_unique": len(uniq), "n_novel": n_novel,
           "n_correct_push_programs": n_correct_push,
           "rule_of_three_upper_95": (3 / n_correct_push) if n_novel == 0 and n_correct_push else None,
           "claim": ("no correct novel algorithm among the correct push programs" if n_novel == 0 and n_items >= 0
                     else f"{n_novel} NOVEL verdicts (see items)"),
           "per_arm_family": {k: dict(v) for k, v in per_arm.items()},
           "final_counts": dict(Counter(r["final"] for r in res)),
           "items": [{k: v for k, v in r.items() if k != "code"} | {"code": r["code"][:1500]} for r in res],
           "spend_usd": STATE["usd"], "calls": STATE["calls"], "budget_stop": STATE["stop"], "judges": JUDGES}
    (RESULTS_DIR / "openrouter_cost_novelty.json").write_text(json.dumps({"usd": STATE["usd"], "calls": STATE["calls"]}))
    return out
