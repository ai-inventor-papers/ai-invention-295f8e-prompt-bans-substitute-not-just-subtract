#!/usr/bin/env python3
"""Novelty audit (plan S10): every CORRECT program labelled 'other' (any arm, any model, deduplicated by code sha256)
goes to two blind judges from different families (openai/gpt-4.1-mini, google/gemini-2.5-flash; deepseek breaks ties).
Each judge sees the task, the strategy-blind catalogue, the program and its 3 nearest known solutions (difflib ratio on
identifier-normalised code, drawn from the unit's references and the dependency's known-solution pool: mercury /
thealgorithms / xlcost / kodcode rows matched to the task) and returns one class: NOVEL, CATALOGUE_VARIANT (with the
mode), KNOWN_TECHNIQUE_OUTSIDE_CATALOGUE, LABELLER_MISS or DEGENERATE. 'No correct novel algorithm' is written only at
a NOVEL count of 0, with the rule-of-three bound 3/N over all correct programs.
Writes results/novelty.json.
"""

from __future__ import annotations

import ast
import difflib
import json
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cfg6 import COSTS, INPUTS, RESULTS_DIR, UNITS_DIR, append_jsonl, read_json, utc_now, write_json  # noqa: E402
from judge6 import JUDGE_A, JUDGE_B, JUDGE_C, _call, catalogue_block, spent  # noqa: E402
from labels_view6 import load_final  # noqa: E402
from units_spec6 import UNITS  # noqa: E402

CLASSES = ["NOVEL", "CATALOGUE_VARIANT", "KNOWN_TECHNIQUE_OUTSIDE_CATALOGUE", "LABELLER_MISS", "DEGENERATE"]


def normalise(code: str) -> str:
    try:
        t = ast.parse(code)
    except SyntaxError:
        return code
    names: dict[str, str] = {}

    def nm(x):
        if x not in names:
            names[x] = f"v{len(names) + 1}"
        return names[x]
    import builtins
    keep = set(dir(builtins)) | {"solve", "self"}
    for n in ast.walk(t):
        if isinstance(n, ast.Name) and n.id not in keep:
            n.id = nm(n.id)
        elif isinstance(n, ast.arg) and n.arg not in keep:
            n.arg = nm(n.arg)
        elif isinstance(n, ast.FunctionDef) and n.name not in keep:
            n.name = nm(n.name)
    try:
        return ast.unparse(t)
    except Exception:  # noqa: BLE001
        return code


def known_pool(u: str) -> list[tuple[str, str]]:
    out = [(f"reference:{p.stem}", p.read_text()) for p in sorted((UNITS_DIR / u / "references").glob("*.py"))]
    src = read_json(INPUTS / "sources.json")
    for i, k in enumerate(src.get("known_pool", [])):
        if u in k["units"] and k.get("code"):
            out.append((f"{k['source']}:{i}", k["code"]))
    for i, k in enumerate(src.get("kodcode", [])):
        if u in k["units"] and k.get("output"):
            out.append((f"kodcode:{k.get('id') or i}", k["output"]))
    lc = src["leetcode"].get(u)
    if lc:
        out.append(("leetcodedataset:reference", lc["output"]))
    return out


def nearest(code: str, pool: list[tuple[str, str]], k: int = 3) -> list[dict]:
    a = normalise(code)
    sc = []
    for name, c in pool:
        sc.append((difflib.SequenceMatcher(None, a, normalise(c)).ratio(), name, c))
    sc.sort(key=lambda x: -x[0])
    return [{"source": n, "ratio": round(r, 3), "code": c[:1500]} for r, n, c in sc[:k]]


def prompt(u: str, code: str, near: list[dict]) -> str:
    ks = "\n\n".join(f"Known solution {i + 1} ({d['source']}):\n```python\n{d['code']}\n```" for i, d in enumerate(near))
    return (f"{UNITS[u]['description']}\n\nCatalogue of known algorithm categories for this task:\n{catalogue_block(u)}\n\n"
            f"{ks}\n\nCandidate program (it passes every hidden test):\n```python\n{code}\n```\n\n"
            "Classify the candidate's algorithm into exactly one class: NOVEL (a correct algorithm that is neither a "
            "catalogue category nor a standard known technique), CATALOGUE_VARIANT (a variant of one catalogue "
            "category; name it), KNOWN_TECHNIQUE_OUTSIDE_CATALOGUE (a standard known technique not in the catalogue), "
            "LABELLER_MISS (plainly one catalogue category as is), DEGENERATE (hard-coded, trivial or relying on a "
            "library call that does the whole task). Answer with JSON only: "
            '{"class": "<class>", "mode": "<catalogue id or none>", "name": "<short name>"}')


def parse(txt: str | None) -> dict | None:
    if not txt:
        return None
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return d if d.get("class") in CLASSES else None


def main() -> None:
    labs = load_final()
    correct = [l for l in labs if l.get("passed") and l.get("final") not in (None, "disputed", "invalid")]
    other = [l for l in correct if l["final"] == "other" and l.get("code")]
    seen: dict[tuple[str, str], dict] = {}
    for l in other:
        seen.setdefault((l["unit"], l["code_sha256"]), {"row": l, "keys": []})["keys"].append(l["key"])
    items = list(seen.values())

    def judge(it):
        l = it["row"]
        u = l["unit"]
        near = nearest(l["code"], known_pool(u))
        pr = prompt(u, l["code"], near)
        def call(model):
            txt, cost = _call(model, pr, max_tokens=120)
            append_jsonl(COSTS, [{"utc": utc_now(), "model": model, "unit": u, "purpose": "novelty", "cost": cost}])
            return parse(txt)
        a = call(JUDGE_A)
        b = call(JUDGE_B)
        c = None
        if not (a and b and a["class"] == b["class"]):
            c = call(JUDGE_C)
        votes = [x["class"] for x in (a, b, c) if x]
        cls = max(set(votes), key=votes.count) if votes else None
        if cls is not None and votes.count(cls) < 2 and len(votes) >= 2:
            cls = "UNRESOLVED"
        return {"unit": u, "code_sha256": l["code_sha256"], "n_rows": len(it["keys"]), "keys": it["keys"][:10],
                "arms": sorted({k.split("|")[2] for k in it["keys"]}), "judge_a": a, "judge_b": b, "judge_c": c,
                "class": cls, "nearest": [{k: v for k, v in d.items() if k != "code"} for d in near],
                "code": l["code"][:2000]}

    with ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(judge, items))
    cnt = Counter(r["class"] for r in res)
    n_corr = len(correct)
    out = {"n_correct_programs": n_corr, "n_correct_other_rows": len(other), "n_distinct_correct_other": len(items),
           "classes": dict(cnt), "n_novel": cnt.get("NOVEL", 0),
           "rule_of_three_upper_per_correct_program": (3 / n_corr) if (n_corr and cnt.get("NOVEL", 0) == 0) else None,
           "statement": ("no correct novel algorithm" if cnt.get("NOVEL", 0) == 0 else
                         f"{cnt.get('NOVEL', 0)} candidate novel programs (see items)"),
           "items": res, "judge_spend_running": spent()}
    write_json(RESULTS_DIR / "novelty.json", out)
    print({k: out[k] for k in ("n_correct_programs", "n_distinct_correct_other", "classes", "statement")})


if __name__ == "__main__":
    main()
