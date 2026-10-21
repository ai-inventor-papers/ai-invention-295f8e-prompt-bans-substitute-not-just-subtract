#!/usr/bin/env python3
"""Novelty audit: every CORRECT program labelled 'other' (all tasks, all arms, base included).

Two blind judges from different families (google/gemini-2.5-flash, openai/gpt-4.1-mini) + a third (deepseek) on
disagreement classify each program as NOVEL_ALGORITHM / CATALOGUE_VARIANT:<mode> / LABELLER_MISS:<mode> /
DEGENERATE. Manual-pass support: the Zhang-Shasha distance to the nearest known solution (472 iteration-3 known
solutions for the existing tasks, the unit references for the new units) is reported per program.
'No correct novel algorithm' is claimed only at a count of 0, with the rule-of-three 95% upper bound 3 / N_correct.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from loguru import logger  # noqa: E402

from cfg5 import BENCH, BUDGET_MSG, E23, INPUTS, LAB_DIR, LOGS, RESULTS, UNIT_DIRS, read_jsonl, setup_logging, \
    unit_dir, utc_now, write_json  # noqa: E402

JUDGES = {"a": "google/gemini-2.5-flash", "b": "openai/gpt-4.1-mini", "c": "deepseek/deepseek-chat-v3.1"}
CLASSES = ("NOVEL_ALGORITHM", "CATALOGUE_VARIANT", "LABELLER_MISS", "DEGENERATE")


def task_spec(task: str) -> tuple[str, list[tuple[str, str]]]:
    if task in UNIT_DIRS:
        s = json.loads((unit_dir(task) / "spec.json").read_text())
        return s["description"], [(c["mode"], c["mechanism"]) for c in s["catalogue"]]
    for d in BENCH.iterdir():
        if d.is_dir() and d.name.startswith(task + "_"):
            s = json.loads((d / "spec.json").read_text())
            return s["description"], [(c["mode"], c.get("mechanism", c.get("display_name", ""))) for c in s["catalogue"]]
    return task, []


def prompt(desc: str, cat: list[tuple[str, str]], code: str) -> str:
    c = "\n".join(f"- {m}: {mech}" for m, mech in cat)
    return ("A Python program below passed every hidden test of the task, but an automatic labeller could not assign "
            "it to any of the catalogue mechanisms.\n\nTask:\n" + desc + "\n\nCatalogue mechanisms:\n" + c +
            "\n\nClassify the program as exactly one of:\n"
            "- LABELLER_MISS:<mode> -- it plainly implements catalogue mode <mode>;\n"
            "- CATALOGUE_VARIANT:<mode> -- a recognisable variant of catalogue mode <mode>;\n"
            "- NOVEL_ALGORITHM -- a correct algorithm genuinely different from every catalogue mechanism;\n"
            "- DEGENERATE -- hard-coded answers, a library call that does all the work outside the catalogue, or a "
            "trivial / brute-force approach that is not a real algorithmic idea.\n\nProgram:\n```python\n" + code +
            '\n```\n\nAnswer with JSON only: {"class": "<one of the four, with :<mode> where required>", '
            '"rationale": "<one sentence>"}')


async def _one(client, sem, model: str, p: str, state: dict) -> dict:
    async with sem:
        if state["aborted"]:
            return {"class": None, "error": "aborted"}
        try:
            r = await client.chat.completions.create(model=model, temperature=0, max_tokens=200,
                                                     messages=[{"role": "user", "content": p}])
        except Exception as e:  # noqa: BLE001
            if BUDGET_MSG in str(e):
                state["aborted"] = True
            return {"class": None, "error": str(e)[:200]}
        txt = r.choices[0].message.content or ""
        cost = float(getattr(r.usage, "cost", 0.0) or 0.0) if r.usage else 0.0
        with open(LOGS / "openrouter_spend_novelty.jsonl", "a") as fh:
            fh.write(json.dumps({"model": model, "cost": cost}) + "\n")
        m = re.search(r"\{.*\}", txt, re.S)
        cls = None
        if m:
            try:
                cls = str(json.loads(m.group(0)).get("class", "")).strip()
            except json.JSONDecodeError:
                cls = None
        return {"class": cls, "raw": txt[:300], "cost": cost}


async def judge_all(prompts: list[str], which: str) -> list[dict]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"],
                         timeout=90, max_retries=2)
    sem = asyncio.Semaphore(8)
    state = {"aborted": False}
    try:
        return await asyncio.gather(*[_one(client, sem, JUDGES[which], p, state) for p in prompts])
    finally:
        await client.close()


def base_class(c: str | None) -> str | None:
    if not c:
        return None
    k = c.split(":")[0].strip().upper()
    return k if k in CLASSES else None


def nearest_known(task: str, code: str) -> dict:
    sys.path.insert(0, str(E23 / "src"))
    from prox import zs_pair

    cands = []
    if task in UNIT_DIRS:
        for p in sorted((unit_dir(task) / "references").glob("*.py")):
            cands.append((p.stem, p.read_text()))
    else:
        for r in read_jsonl(INPUTS / "exp18" / "known_solutions.jsonl"):
            if r.get("task") == task and r.get("code"):
                cands.append((r.get("mode_hint") or r.get("label") or r.get("source", "?"), r["code"]))
    best = None
    for name, c in cands[:60]:
        d = zs_pair(code, c)
        if d is not None and (best is None or d < best[1]):
            best = (name, d)
    return {"nearest": best[0] if best else None, "distance": best[1] if best else None, "n_candidates": len(cands)}


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("novelty_audit")
    items = []
    n_correct = 0
    for f in sorted(LAB_DIR.glob("*.jsonl")):
        if f.stem.startswith("enginecheck"):
            continue
        for r in read_jsonl(f):
            if r.get("passed"):
                n_correct += 1
                if r["label"] == "other" and r.get("code"):
                    items.append(r)
    prompts = []
    for r in items:
        desc, cat = task_spec(r["task"])
        prompts.append(prompt(desc, cat, r["code"]))
    ja = asyncio.run(judge_all(prompts, "a")) if prompts else []
    jb = asyncio.run(judge_all(prompts, "b")) if prompts else []
    need = [i for i in range(len(items)) if base_class(ja[i]["class"]) != base_class(jb[i]["class"])]
    jc = asyncio.run(judge_all([prompts[i] for i in need], "c")) if need else []
    jc_map = dict(zip(need, jc))
    out = []
    for i, r in enumerate(items):
        votes = [base_class(ja[i]["class"]), base_class(jb[i]["class"])]
        if i in jc_map:
            votes.append(base_class(jc_map[i]["class"]))
        final = None
        for v in set(x for x in votes if x):
            if votes.count(v) >= 2:
                final = v
        out.append({"task": r["task"], "sample_id": r["sample_id"], "arm": r["arm"], "model": r["model"],
                    "judge_a": ja[i].get("class"), "judge_b": jb[i].get("class"),
                    "judge_c": jc_map.get(i, {}).get("class"), "final_class": final or "UNRESOLVED",
                    **nearest_known(r["task"], r["code"])})
    n_novel = sum(1 for o in out if o["final_class"] == "NOVEL_ALGORITHM")
    res = {"utc": utc_now(), "n_correct_programs_total": n_correct, "n_correct_other": len(items),
           "class_counts": {c: sum(1 for o in out if o["final_class"] == c) for c in CLASSES + ("UNRESOLVED",)},
           "n_novel": n_novel,
           "statement": ("no correct novel algorithm" if n_novel == 0 else f"{n_novel} correct novel algorithm(s)"),
           "rule_of_three_upper95_per_correct_program": (3.0 / n_correct) if n_novel == 0 and n_correct else None,
           "items": out}
    write_json(RESULTS / "novelty_audit.json", res)
    logger.info(f"novelty audit: {len(items)} correct 'other' programs of {n_correct} correct; classes "
                f"{res['class_counts']}")


if __name__ == "__main__":
    main()
