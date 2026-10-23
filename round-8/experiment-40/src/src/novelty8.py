#!/usr/bin/env python3
"""S12 novelty audit: every CORRECT program labelled 'other' (or 'disputed' with fallback 'other') goes to two blind
judges of different families (deepseek/deepseek-chat-v3.1, mistralai/mistral-medium-3.1), each gated on 10 control
programs of known class, with its 3 nearest known solutions (difflib ratio over art_j3Rm_lr2nzR6's connected-component
references and art_lpQalcAXMGr1's known_solutions.json). Third judge on disagreement. Running usage.cost, cap USD 0.30;
the first 403 'AI Inventor per-run OpenRouter budget' stops the batch. With no candidate, no call is made and the
rule-of-three upper bound 3/n over all correct programs is reported.

Usage: python src/novelty8.py
"""

from __future__ import annotations

import difflib
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger

from cfg8 import (BUDGET_MSG, DATA, INPUTS, OPENROUTER_CAP_USD, RESULTS, read_json, read_jsonl, setup_logging,
                  write_json)

JUDGES = ("deepseek/deepseek-chat-v3.1", "mistralai/mistral-medium-3.1")
THIRD = "google/gemini-2.5-flash-lite"
CLASSES = {"T10": ["bfs", "dfs", "union_find", "label_propagation", "other"],
           "GRID": ["bfs", "dfs", "bibfs", "iddfs", "astar_gbfs", "dijkstra", "other"]}
PROMPT = ("You are a blind judge of algorithm identity. Task: {task}. Classify the PROGRAM's core algorithm into one "
          "of: {classes}. Use 'other' only if it is none of the listed algorithms (a genuinely different method). "
          "Three nearest known solutions are shown for reference.\n\nKNOWN 1:\n{k1}\n\nKNOWN 2:\n{k2}\n\nKNOWN 3:\n{k3}"
          "\n\nPROGRAM:\n{code}\n\nAnswer with JSON: {{\"label\": <one class>, \"novel\": <true|false>, \"why\": "
          "<one sentence>}}")
TASK = {"T10": "count connected components of an undirected graph with n nodes and an edge list",
        "GRID": "shortest path length in a grid from start to goal (4-neighbour moves, walls)"}


def known_pool(unit: str) -> list[str]:
    pool = []
    dep = read_json(INPUTS / "dep_extract.json")
    if unit == "T10":
        pool += [r["code"] for r in dep["t10_reference_programs"]]
    ks = INPUTS / "exp29" / "known_solutions.json"
    if ks.exists():
        try:
            obj = read_json(ks)
            items = obj if isinstance(obj, list) else obj.get("solutions", obj.get("items", []))
            for it in items:
                if isinstance(it, dict) and it.get("code"):
                    pool.append(it["code"])
        except (json.JSONDecodeError, AttributeError):
            pass
    return pool


def nearest(code: str, pool: list[str], k: int = 3) -> list[str]:
    sc = sorted(pool, key=lambda p: -difflib.SequenceMatcher(None, code[:3000], p[:3000]).quick_ratio())
    return (sc + ["(none)"] * k)[:k]


def call(client: Any, model: str, prompt: str, spent: list[float]) -> dict[str, Any] | None:
    if spent[0] >= OPENROUTER_CAP_USD:
        return None
    try:
        r = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}],
                                           temperature=0, max_tokens=200, extra_body={"usage": {"include": True}})
    except Exception as e:  # noqa: BLE001 - budget refusal stops the batch
        if BUDGET_MSG in str(e):
            spent[0] = OPENROUTER_CAP_USD
            logger.error("OpenRouter budget exhausted: batch stopped")
        else:
            logger.error(f"judge call failed: {e}")
        return None
    cost = float(getattr(r, "usage", None) and getattr(r.usage, "cost", 0) or 0)
    spent[0] += cost
    txt = r.choices[0].message.content or ""
    try:
        j = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
    except ValueError:
        j = {"label": None, "raw": txt[:200]}
    j["cost"] = cost
    return j


def main() -> None:
    setup_logging("novelty8")
    out: dict[str, Any] = {"judges": JUDGES, "cap_usd": OPENROUTER_CAP_USD, "units": {}}
    spent = [0.0]
    client = None
    for unit in ("T10", "GRID"):
        labs = read_jsonl(DATA / f"labels_{unit}.jsonl")
        seen = {}
        for r in labs:
            seen.setdefault(r["sample_id"], r)
        rows = list(seen.values())
        correct = [r for r in rows if r.get("passed")]
        cands = [r for r in correct if r["label"] == "other" or (r["label"] == "disputed" and
                                                                 r.get("fallback_label") == "other")]
        u = {"n_correct_programs": len(correct), "n_candidates": len(cands),
             "rule_of_three_upper_bound_novel_rate": 3 / len(correct) if correct else None, "judged": []}
        if cands:
            if client is None:
                from openai import OpenAI
                client = OpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"])
            pool = known_pool(unit)
            # gate: 10 controls of known class (correct programs with agreeing runtime + AST labels)
            ctrl = [r for r in correct if r.get("labeller_source") in ("runtime+ast", "agree", "runtime(ast_unknown)")
                    and r["label"] != "other"][:10]
            gate = {}
            for jm in JUDGES:
                ok = 0
                for r in ctrl:
                    k = nearest(r["code"] or "", pool)
                    j = call(client, jm, PROMPT.format(task=TASK[unit], classes=", ".join(CLASSES[unit]), k1=k[0],
                                                       k2=k[1], k3=k[2], code=r["code"]), spent)
                    ok += int(bool(j) and j.get("label") == r["label"])
                gate[jm] = {"correct": ok, "n": len(ctrl), "pass": ok >= 8}
            u["gate"] = gate
            for r in cands:
                k = nearest(r["code"] or "", pool)
                pr = PROMPT.format(task=TASK[unit], classes=", ".join(CLASSES[unit]), k1=k[0], k2=k[1], k3=k[2],
                                   code=r["code"])
                js = {jm: call(client, jm, pr, spent) for jm in JUDGES if gate[jm]["pass"]}
                labs_j = {m: (v or {}).get("label") for m, v in js.items()}
                if len(set(labs_j.values())) > 1:
                    js[THIRD] = call(client, THIRD, pr, spent)
                u["judged"].append({"sample_id": r["sample_id"], "judges": js})
        out["units"][unit] = u
    out["spent_usd"] = spent[0]
    write_json(RESULTS / "novelty_audit.json", out)
    write_json(RESULTS / "costs.json", {"openrouter_usd": spent[0], "cap_usd": OPENROUTER_CAP_USD})
    logger.info(f"novelty: {json.dumps({u: (v['n_candidates'], v['n_correct_programs']) for u, v in out['units'].items()})}; "
                f"spent {spent[0]:.4f}")


if __name__ == "__main__":
    main()
