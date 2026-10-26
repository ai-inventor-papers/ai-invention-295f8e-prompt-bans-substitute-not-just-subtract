#!/usr/bin/env python3
"""Novelty audit (plan section 12): every CORRECT program labelled 'other' in any arm (base included), deduplicated by
code sha256, goes to judge A and judge B (blind, different families) with a tie-break on disagreement. Classes:
NOVEL_ALGORITHM / CATALOGUE_VARIANT (named) / LABELLER_MISS (it is a catalogue mode) / DEGENERATE (hard-coded,
trivial or delegating to a library outside the catalogue). The nearest known solution (the unit's references,
identifier-normalised Zhang-Shasha AST distance) is attached to every record for the manual pass.
'No correct novel algorithm' is claimed only at a count of 0, with the rule-of-three bound 3 / N_correct over all
correct programs of the audited arms. Uses the reserved part of the judge budget."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.append(str(Path(__file__).resolve().parents[1] / "vendor" / "exp23"))  # appended: vendor/exp23/units.py must not shadow src/units

from loguru import logger  # noqa: E402

import units_extra  # noqa: E402,F401
from cfg5 import COSTS, DATA_DIR, LABELS, OPENROUTER_SOFT_STOP, RESULTS_DIR, append_jsonl, read_jsonl, setup_logging, \
    utc_now, write_json  # noqa: E402
import judge5  # noqa: E402
from labels_view import final_rows  # noqa: E402
from units_spec import UNITS  # noqa: E402
from unitlib import strip_comments_docstrings  # noqa: E402

CACHE = DATA_DIR / "novelty_cache.jsonl"
CLASSES = ("NOVEL_ALGORITHM", "CATALOGUE_VARIANT", "LABELLER_MISS", "DEGENERATE")


def refs_for(u: str) -> dict[str, str]:
    if u[:2] in ("P_", "V_"):
        d = units_extra.BENCH / units_extra.PARENT_DIRS[u[2:]] / "references"
        return {p.stem: p.read_text() for p in sorted(d.glob("*.py"))}
    from unitlib import unit_mod
    return dict(unit_mod(u).REFERENCES)


def prompt(u: str, code: str) -> str:
    return (f"{UNITS[u]['description']}\n\nKnown solution approaches for this task:\n"
            f"{judge5.catalogue_block(u)}\n\nA correct program that our labellers could not assign to any known "
            f"approach:\n```python\n{code}\n```\n\nClassify it. NOVEL_ALGORITHM: a genuinely different algorithm from "
            "every listed approach and from standard textbook solutions. CATALOGUE_VARIANT: a variant or combination "
            "of a listed approach (name the closest one). LABELLER_MISS: it simply IS one of the listed approaches. "
            "DEGENERATE: hard-coded, trivial, or delegating the work to a library function outside the list. "
            'Answer with JSON only: {"class": "<one of the four>", "closest": "<listed id or none>"}')


def judge(model: str, u: str, code: str) -> dict | None:
    from unitlib import code_sha
    key = f"{model}|{u}|{code_sha(code)}"
    for r in read_jsonl(CACHE):
        if r["key"] == key:
            return r
    if judge5.spent() >= OPENROUTER_SOFT_STOP:
        return None
    txt, cost = judge5._call(model, prompt(u, code), max_tokens=80)
    with judge5._LOCK:
        judge5.STATE["spent"] = judge5.spent() + cost
        append_jsonl(COSTS, [{"utc": utc_now(), "model": model, "unit": u, "purpose": "novelty_audit", "cost": cost}])
    if txt is None:
        return None
    m = re.search(r'"class"\s*:\s*"([A-Z_]+)"', txt)
    c = re.search(r'"closest"\s*:\s*"([^"]*)"', txt)
    rec = {"key": key, "model": model, "unit": u, "class": m.group(1) if m and m.group(1) in CLASSES else None,
           "closest": c.group(1) if c else None, "raw": txt[:200]}
    append_jsonl(CACHE, [rec])
    return rec


def nearest_ref(u: str, code: str) -> dict:
    from prox import zs_pair
    best = (None, None)
    c0 = strip_comments_docstrings(code)
    for m, r in refs_for(u).items():
        d = zs_pair(strip_comments_docstrings(r), c0)
        if d is not None and (best[1] is None or d < best[1]):
            best = (m, d)
    return {"nearest_reference": best[0], "zs_distance": best[1]}


def main() -> None:
    setup_logging("novelty_audit")
    labs = {l["key"]: l for l in read_jsonl(LABELS)}
    units = sorted({l["unit"] for l in labs.values()})
    items, n_correct_total, seen = [], 0, set()
    by_arm = Counter()
    for u in units:
        if u not in UNITS:
            continue
        for r in final_rows(u):
            if not r["passed"]:
                continue
            n_correct_total += 1
            if r["label"] != "other":
                continue
            by_arm[(u, r["family"])] += 1
            sha = r["code_sha256"]
            if (u, sha) in seen:
                continue
            seen.add((u, sha))
            items.append((u, r["key"], labs[r["key"]]["code"]))
    logger.info(f"novelty audit: {len(items)} distinct correct 'other' programs; {n_correct_total} correct programs")

    def one(it):
        u, key, code = it
        a = judge(judge5.JUDGE_A, u, code)
        b = judge(judge5.JUDGE_B, u, code)
        ca, cb = (a or {}).get("class"), (b or {}).get("class")
        c = None
        if ca != cb:
            c = judge(judge5.JUDGE_C, u, code)
        votes = [x for x in (ca, cb, (c or {}).get("class")) if x]
        verdict = max(set(votes), key=votes.count) if votes and max(votes.count(v) for v in set(votes)) >= 2 else None
        return {"unit": u, "key": key, "judge_a": a and {k: a[k] for k in ("class", "closest")},
                "judge_b": b and {k: b[k] for k in ("class", "closest")},
                "judge_c": c and {k: c[k] for k in ("class", "closest")}, "verdict": verdict, **nearest_ref(u, code),
                "code": code}

    for u in sorted({it[0] for it in items}):   # import unit modules once, before the threads (import race)
        refs_for(u)
    with ThreadPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(one, items))
    cnt = Counter(r["verdict"] for r in res)
    n_novel = cnt.get("NOVEL_ALGORITHM", 0)
    out = {"utc": utc_now(), "n_correct_programs_audited_arms": n_correct_total, "n_correct_other_rows": sum(by_arm.values()),
           "n_distinct_correct_other": len(items), "by_unit_family": {f"{u}|{f}": n for (u, f), n in by_arm.items()},
           "verdicts": dict(cnt), "n_novel": n_novel,
           "claim": ("no correct novel algorithm (rule-of-three upper bound 3/N = "
                     f"{3 / max(n_correct_total, 1):.4f} per correct program)") if n_novel == 0 else
           f"{n_novel} program(s) judged NOVEL_ALGORITHM by the judge majority -- see items for the manual read",
           "items": res, "judge_spend_running": judge5.spent()}
    write_json(RESULTS_DIR / "novelty_audit.json", out)
    print(json.dumps({k: v for k, v in out.items() if k != "items"}, indent=1))


if __name__ == "__main__":
    main()
