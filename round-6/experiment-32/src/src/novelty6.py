#!/usr/bin/env python3
"""Stage 5 novelty audit: every CORRECT program labelled 'other' (every arm, both models) is deduplicated by a
normalised AST hash and read by two blind judges of different families (google/gemini-2.5-flash, openai/gpt-4.1-mini;
deepseek/deepseek-chat on disagreement). The prompt gives the task spec, the code and the catalogue WITHOUT the
label; classes NOVEL_ALGORITHM / CATALOGUE_VARIANT / KNOWN_TECHNIQUE_OUTSIDE_CATALOGUE / LABELLER_MISS /
DEGENERATE. The executor's comparison with the nearest known solutions is automated and reported as such: difflib
similarity to the unit's references, the dataset reference row and the keyword-matched KodCode/XLCoST rows."""

from __future__ import annotations

import ast
import difflib
import hashlib
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

from cfg5 import (COSTS, DATA_DIR, INPUTS, RESULTS_DIR, append_jsonl, read_json, read_jsonl, setup_logging,  # noqa: E402
                  utc_now, write_json)
from judge5 import JUDGE_A, JUDGE_B, JUDGE_C, STATE, _call, spent  # noqa: E402
from units_spec import UNITS  # noqa: E402
from unitlib import unit_mod  # noqa: E402

CLASSES = ["NOVEL_ALGORITHM", "CATALOGUE_VARIANT", "KNOWN_TECHNIQUE_OUTSIDE_CATALOGUE", "LABELLER_MISS", "DEGENERATE"]
CACHE = DATA_DIR / "novelty_cache.jsonl"


def norm_hash(code: str) -> str:
    try:
        t = ast.parse(code)
        for n in ast.walk(t):
            if isinstance(n, ast.Name):
                n.id = "_"
            elif isinstance(n, ast.arg):
                n.arg = "_"
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                n.name = "_"
        s = ast.dump(t, annotate_fields=False)
    except SyntaxError:
        s = code
    return hashlib.sha256(s.encode()).hexdigest()


def prompt(u: str, code: str) -> str:
    cat = "\n".join(f"- {m}: {dn} -- {mech}" for m, (dn, mech) in UNITS[u]["modes"].items())
    return (f"{UNITS[u]['description']}\n\nKnown algorithm catalogue for this task:\n{cat}\n\nProgram (it passes every "
            f"hidden test):\n```python\n{code}\n```\n\nClassify the program's main mechanism into exactly one class:\n"
            "NOVEL_ALGORITHM (a genuinely new algorithm for this task, not a standard textbook or competitive-"
            "programming technique), CATALOGUE_VARIANT (an implementation variant of one catalogue entry; name it), "
            "KNOWN_TECHNIQUE_OUTSIDE_CATALOGUE (a standard technique not in the catalogue; name it), LABELLER_MISS "
            "(plainly one catalogue entry), DEGENERATE (hard-coded, trivial or exploiting the tests).\n"
            'Answer with JSON only: {"class": "<CLASS>", "name": "<short name>"}')


def judge(model: str, u: str, code: str) -> dict:
    key = f"{model}|{u}|{hashlib.sha256(code.encode()).hexdigest()}"
    for r in read_jsonl(CACHE):
        if r["key"] == key:
            return r
    if spent() >= 1.9:
        return {"key": key, "class": None, "name": None}
    txt, cost = _call(model, prompt(u, code), max_tokens=80)
    STATE["spent"] = spent() + cost
    append_jsonl(COSTS, [{"utc": utc_now(), "model": model, "unit": u, "purpose": "novelty_audit", "cost": cost}])
    cls, name = None, None
    if txt:
        try:
            j = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
            cls = j.get("class") if j.get("class") in CLASSES else None
            name = j.get("name")
        except (ValueError, json.JSONDecodeError):
            cls = next((c for c in CLASSES if c in txt), None)
    rec = {"key": key, "class": cls, "name": name, "raw": (txt or "")[:200], "model": model, "utc": utc_now()}
    append_jsonl(CACHE, [rec])
    return rec


def nearest(u: str, code: str) -> dict:
    src = read_json(INPUTS / "sources.json")
    pool = {f"ref:{m}": c for m, c in unit_mod(u).REFERENCES.items()}
    lc = [e for e in src["leetcode"].values() if e.get("unit") == u]
    if lc:
        pool["dataset_reference"] = lc[0]["output"]
    for i, e in enumerate(src["extra_rows"].get(u, [])[:20]):
        pool[f"{e['dataset']}:{i}"] = e["output"]
    best = max(pool.items(), key=lambda kv: difflib.SequenceMatcher(None, code, kv[1]).ratio())
    return {"nearest": best[0], "similarity": round(difflib.SequenceMatcher(None, code, best[1]).ratio(), 3)}


def main() -> None:
    setup_logging("novelty6")
    from labels6 import all_final
    rows = [r for r in all_final() if r["passed"] and r["label"] == "other" and r.get("code")]
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(f"{r['unit']}|{norm_hash(r['code'])}", []).append(r)
    items = [(k, v[0]) for k, v in groups.items()]
    logger.info(f"{len(rows)} correct 'other' programs -> {len(items)} distinct (AST hash)")

    def one(it):
        k, r = it
        a = judge(JUDGE_A, r["unit"], r["code"])
        b = judge(JUDGE_B, r["unit"], r["code"])
        c = None
        if a["class"] != b["class"]:
            c = judge(JUDGE_C, r["unit"], r["code"])
        votes = [x["class"] for x in (a, b, c) if x and x["class"]]
        fin = max(set(votes), key=votes.count) if votes and votes.count(max(set(votes), key=votes.count)) >= 2 \
            else "UNRESOLVED"
        return {"group": k, "unit": r["unit"], "n_copies": len(groups[k]), "arms": sorted({x["arm"] for x in groups[k]}),
                "models": sorted({x["model_tag"] for x in groups[k]}), "judge_a": a["class"], "judge_b": b["class"],
                "judge_c": c["class"] if c else None, "final": fin, "names": [a.get("name"), b.get("name")],
                **nearest(r["unit"], r["code"]), "example_key": r["key"]}

    with ThreadPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(one, items))
    n_correct = sum(1 for r in all_final() if r["passed"])
    cnt = Counter(r["final"] for r in res)
    out = {"utc": utc_now(), "n_correct_other": len(rows), "n_distinct": len(items), "class_counts": dict(cnt),
           "n_correct_programs_all": n_correct, "items": res,
           "statement": ("no correct novel algorithm" if cnt.get("NOVEL_ALGORITHM", 0) == 0 else
                         f"{cnt['NOVEL_ALGORITHM']} programs judged NOVEL_ALGORITHM (see items)"),
           "rule_of_three_upper": (3 / n_correct) if (n_correct and cnt.get("NOVEL_ALGORITHM", 0) == 0) else None,
           "manual_comparison": "automated difflib nearest-match against the unit references, the dataset reference "
                                "row and keyword-matched KodCode/XLCoST rows (executor's comparison, no human)"}
    write_json(RESULTS_DIR / "novelty_audit.json", out)
    logger.info(f"novelty audit: {dict(cnt)}; spent {spent():.3f}")


if __name__ == "__main__":
    main()
