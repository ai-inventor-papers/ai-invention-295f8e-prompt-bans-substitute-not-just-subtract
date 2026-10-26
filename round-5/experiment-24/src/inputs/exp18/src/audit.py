"""S8 AUDIT AND CLAIMS: novelty audit of every correct off-catalogue ('other') program against the catalogue AND
the known-solution corpora of the declared dataset dependency (Mercury human solutions, LeetCodeDataset references,
TheAlgorithms-Python, KodCode, XLCoST), by two blind judges (never told the arm) plus the executor's manual pass;
and claim extraction on every long-form output (does the rationale claim a new algorithm, is it known, does the
code implement it).
"""

from __future__ import annotations

import ast
import asyncio
import io
import json
import random
import re
import sys
import tokenize
from collections import Counter, defaultdict
from typing import Any

from loguru import logger

from config import (BENCH_DIR, DATA, DEP_DATASET, INPUTS, RESULTS, SUITE_DIR, TASKS, append_jsonl, read_jsonl,
                    setup_logging, sha256_text, utc_now, write_json)
from judge import AUDIT_JUDGE_A, AUDIT_JUDGE_B, budget, call_llm

KNOWN = INPUTS / "known_solutions.jsonl"
BENCH_PREFIX = {"T01": "T1", "T02": "T2", "T03": "T03", "T04": "T04", "T06": "T06", "T10": "T10"}
LEETCODE_TASK = {"215": "T03", "28": "T04", "287": "T06", "547": "T10", "323": "T10", "1971": "T10", "743": "T2",
                 "1091": "T1", "1631": "T2", "1514": "T2"}
KEYWORDS = {"T1": ["bfs", "breadth", "dfs", "depth_first", "a_star", "astar", "bidirectional", "iterative_deepening",
                   "maze", "grid", "jump_point", "greedy_best"],
            "T2": ["dijkstra", "bellman", "spfa", "floyd", "dial", "shortest_path", "johnson"],
            "T03": ["quickselect", "quick_select", "kth", "median_of_medians", "heap", "select", "nth"],
            "T04": ["kmp", "knuth", "rabin", "z_function", "z_algorithm", "boyer", "horspool", "string_match",
                    "substring", "sunday"],
            "T06": ["duplicate", "tortoise", "floyd", "cycle"],
            "T10": ["union_find", "disjoint", "connected_component", "dfs", "bfs"]}
AUDIT_CLASSES = ["NOVEL ALGORITHM", "CATALOGUE VARIANT", "LABELLER MISS", "DEGENERATE"]
CLASS_DEFS = (
    "LABELLER MISS = the program implements a catalogue algorithm of this task in substance and should have carried "
    "its label; CATALOGUE VARIANT = it implements a known algorithm (catalogue, extended catalogue, or any named "
    "textbook or published method, e.g. Boyer-Moore, introselect, jump point search), possibly with minor changes, "
    "hybrids or a different but equivalent data structure; DEGENERATE = it passes by hard-coding, test-specific "
    "shortcuts, library calls that bypass the algorithm, or brute force that only passes because inputs are small; "
    "NOVEL ALGORITHM = none of the above, and the judge can state the mechanism and why no known algorithm matches.")


# ------------------------------------------------------------------------------------------------ corpus
def _task_for_thealgorithms(path: str, bench_task: str | None) -> str | None:
    if bench_task and bench_task not in ("None", ""):
        return BENCH_PREFIX.get(bench_task[:3])
    p = path.lower()
    for t, kws in KEYWORDS.items():
        if any(k in p for k in kws):
            return t
    return None


def build_known_solutions() -> dict[str, Any]:
    """Stream the dependency's full_data_out.json (ijson) and keep the rows that are known solutions of a task."""
    import ijson

    src = DEP_DATASET / "full_data_out.json"
    out = []
    counts: Counter = Counter()
    with src.open("rb") as f:
        for ds in ijson.items(f, "datasets.item"):
            name = ds["dataset"]
            if name not in ("leetcodedataset", "mercury", "thealgorithms_python", "kodcode_algorithmic", "xlcost_python"):
                continue
            for ex in ds["examples"]:
                task, code, hint = None, None, None
                if name in ("leetcodedataset", "mercury"):
                    qid = str(ex.get("metadata_question_id"))
                    bt = str(ex.get("metadata_bench_task") or "")
                    task = BENCH_PREFIX.get(bt[:3]) or LEETCODE_TASK.get(qid)
                    code = ex.get("output")
                    hint = ex.get("metadata_slug") or ex.get("metadata_task_slug")
                elif name == "thealgorithms_python":
                    task = _task_for_thealgorithms(str(ex.get("metadata_path")), str(ex.get("metadata_bench_task")))
                    code = ex.get("input")
                    hint = f"{ex.get('output')} ({ex.get('metadata_bench_mode')})"
                else:
                    named = ex.get("metadata_bench_tasks_named") or "[]"
                    try:
                        lst = json.loads(named.replace("'", '"')) if isinstance(named, str) else named
                    except json.JSONDecodeError:
                        lst = []
                    tl = [BENCH_PREFIX.get(str(x)[:3]) for x in lst]
                    tl = [x for x in tl if x]
                    if not tl:
                        continue
                    task = tl[0]
                    code = ex.get("output")
                    hint = ex.get("metadata_named_algorithms")
                if task and code:
                    out.append({"source": name, "task": task, "mode_hint": str(hint)[:120], "code": code[:20000]})
                    counts[(name, task)] += 1
    KNOWN.write_text("".join(json.dumps(r) + "\n" for r in out))
    summ = {"n": len(out), "by_source_task": {f"{a}|{b}": k for (a, b), k in sorted(counts.items())},
            "utc": utc_now()}
    write_json(RESULTS / "known_solutions_summary.json", summ)
    logger.info(f"known-solution corpus: {summ['n']} rows")
    return summ


# ------------------------------------------------------------------------------------------------ similarity
def canon(code: str) -> list[str]:
    from bench.common.canon import canon_tokens

    try:
        return canon_tokens(code)
    except Exception:  # noqa: BLE001
        return []


def nearest(code: str, pool: list[dict[str, Any]], k: int = 3) -> list[dict[str, Any]]:
    from bench.common.canon import token_distance

    a = canon(code)
    scored = []
    for p in pool:
        b = p.get("_canon")
        if b is None:
            b = p["_canon"] = canon(p["code"])
        if not b:
            continue
        scored.append((token_distance(a, b), p))
    scored.sort(key=lambda x: x[0])
    return [{"source": p["source"], "mode_hint": p.get("mode_hint"), "similarity": round(1 - d, 3),
             "code": p["code"][:1500]} for d, p in scored[:k]]


def references(task: str) -> list[dict[str, Any]]:
    out = []
    if TASKS[task]["family"] == "bench":
        for f in sorted((BENCH_DIR / TASKS[task]["task_id"] / "references").glob("*.py")):
            out.append({"source": "catalogue reference", "mode_hint": f.stem, "code": f.read_text()})
    else:
        sub = {"T1": "t1_grid", "T2": "t2_wsp"}[task]
        for f in sorted((SUITE_DIR / "tasks" / sub / "references").glob("*.py")):
            out.append({"source": "catalogue reference", "mode_hint": f.stem, "code": f.read_text()})
    return out


ALIAS_RE = re.compile(r"(bfs|dfs|breadth|depth|dijkstra|bellman|spfa|floyd|warshall|dial|astar|a_star|heuristic|"
                      r"bidirectional|iddfs|deepening|quickselect|select|heap|kmp|knuth|rabin|karp|z_?algo|z_?func|"
                      r"boyer|horspool|naive|union|find|disjoint|dsu|tortoise|hare|cycle|binary_search|bisect|"
                      r"counting|sort|novel|new_|invent)", re.I)


def scrub(task: str, code: str) -> str:
    """Name-scrub before judging: bench tasks use the bench scrubber; path tasks drop comments/docstrings and rename
    identifiers containing an algorithm alias (API names untouched)."""
    if TASKS[task]["family"] == "bench":
        try:
            from bench.common.scrub import scrub_code

            return scrub_code(code)[0]
        except Exception:  # noqa: BLE001
            return code
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code
    params = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == "solve":
            params = {a.arg for a in n.args.args}
    defined = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef):
            defined.add(n.name)
            defined.update(a.arg for a in n.args.args)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            defined.add(n.id)
        elif isinstance(n, ast.ClassDef):
            defined.add(n.name)
    ren = {}
    for i, name in enumerate(sorted(defined)):
        if name != "solve" and name not in params and ALIAS_RE.search(name):
            ren[name] = f"var{i}"
    out = []
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(code).readline))
    except (tokenize.TokenError, IndentationError):
        return code
    prev = None
    for tok in toks:
        if tok.type == tokenize.COMMENT:
            continue
        if tok.type == tokenize.NAME and tok.string in ren and not (prev and prev.string == "."):
            tok = tok._replace(string=ren[tok.string])
        out.append(tok)
        prev = tok
    try:
        s = tokenize.untokenize(out)
    except ValueError:
        return code
    return s


# ------------------------------------------------------------------------------------------------ prompts
def catalogue_text(task: str) -> str:
    if TASKS[task]["family"] == "bench":
        spec = json.loads((BENCH_DIR / TASKS[task]["task_id"] / "spec.json").read_text())
        return "\n".join(f"- {c['mode']}: {c['display_name']} - {c['mechanism']}" for c in spec["catalogue"])
    import common as suite_common

    st = TASKS[task]["suite"]
    return "\n".join(f"- {m}: {suite_common.MODE_DEFINITIONS[st][m]}" for m in suite_common.MODES[st]) + \
        "\nExtended catalogue (known, not labels): " + ", ".join(suite_common.EXTENDED_CATALOGUE[st])


def audit_prompt(task: str, code: str, neigh_known: list[dict], neigh_refs: list[dict]) -> str:
    from prompts import description

    def fmt(ns):
        return "\n\n".join(f"[{n['source']} | {n['mode_hint']} | similarity {n['similarity']}]\n```python\n"
                           f"{n['code'][:1200]}\n```" for n in ns)

    return (f"You audit whether a Python program is a genuinely new algorithm.\n\nTASK:\n{description(task)}\n\n"
            f"CATALOGUE OF KNOWN ALGORITHMS FOR THIS TASK:\n{catalogue_text(task)}\n\n"
            "CONTEXT: an automatic mechanism labeller could not assign any catalogue label to this program (it was "
            "labelled 'other').\n\n"
            f"CLASSES (choose exactly one):\n{CLASS_DEFS}\n\n"
            "DECISION ORDER: (1) if the program's mechanism is one of the catalogue algorithms above (even renamed, "
            "restructured, recursive vs iterative, or with a different container) -> LABELLER MISS; (2) else if it "
            "passes by hard-coding, test-specific shortcuts or a library call that bypasses the task's algorithmic "
            "work -> DEGENERATE; (3) else if it is any other known method (a named textbook or published algorithm, "
            "or a hybrid/variant of known ones) -> CATALOGUE VARIANT; (4) only if none applies -> NOVEL ALGORITHM.\n\n"
            f"PROGRAM (identifiers and comments that name algorithms were scrubbed):\n```python\n{code}\n```\n\n"
            f"NEAREST KNOWN HUMAN / TEXTBOOK SOLUTIONS (context; similarity of canonical token streams):\n"
            f"{fmt(neigh_known)}\n\nNEAREST CATALOGUE REFERENCES:\n{fmt(neigh_refs)}\n\n"
            "Judge the mechanism the code executes. Answer with JSON only: {\"class\": \"NOVEL ALGORITHM | CATALOGUE "
            "VARIANT | LABELLER MISS | DEGENERATE\", \"closest_known_algorithm\": \"...\", \"differs_how\": \"one "
            "sentence\", \"catalogue_label_if_miss\": \"<label id or null>\", \"confidence\": <0-1>}")


def parse_audit(txt: str | None) -> dict[str, Any]:
    if not txt:
        return {"class": None}
    m = re.search(r"\{.*\}", txt, re.S)
    js: dict[str, Any] = {}
    if m:
        try:
            js = json.loads(m.group(0))
        except json.JSONDecodeError:
            js = {}
    c = str(js.get("class", "")).upper().strip()
    cls = next((k for k in AUDIT_CLASSES if k in c), None)
    if cls is None:
        cls = next((k for k in AUDIT_CLASSES if k in (txt or "").upper()), None)
    return {"class": cls, "closest_known_algorithm": js.get("closest_known_algorithm"),
            "differs_how": js.get("differs_how"), "catalogue_label_if_miss": js.get("catalogue_label_if_miss"),
            "confidence": js.get("confidence")}


def claim_prompt(task: str, rationale: str, code: str | None) -> str:
    from prompts import description

    return (f"A model was asked to invent a new algorithm for this task and to explain it before coding.\n\nTASK:\n"
            f"{description(task)}\n\nKNOWN ALGORITHMS FOR THIS TASK:\n{catalogue_text(task)}\n\nRATIONALE (may be "
            f"truncated):\n{rationale[:7000]}\n\nCODE:\n```python\n{(code or '(no code)')[:4000]}\n```\n\n"
            "Extract the claim and check it against the code. Answer with JSON only: {\"claimed_name\": \"...\", "
            "\"claimed_mechanism\": \"<= 80 words\", \"claims_novelty\": true/false, \"closest_known_algorithm\": "
            "\"...\", \"claimed_is_known\": true/false, \"code_implements_claim\": \"yes | partial | no\", "
            "\"code_mechanism_guess\": \"<catalogue label id or other>\"}")


def parse_claim(txt: str | None) -> dict[str, Any]:
    if not txt:
        return {}
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        return {}
    try:
        js = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}

    def b(v):
        return v if isinstance(v, bool) else (str(v).lower() == "true" if v is not None else None)

    return {"claimed_name": js.get("claimed_name"), "claimed_mechanism": js.get("claimed_mechanism"),
            "claims_novelty": b(js.get("claims_novelty")), "closest_known_algorithm": js.get("closest_known_algorithm"),
            "claimed_is_known": b(js.get("claimed_is_known")),
            "code_implements_claim": str(js.get("code_implements_claim", "")).lower().strip() or None,
            "code_mechanism_guess": js.get("code_mechanism_guess")}


# ------------------------------------------------------------------------------------------------ pool
ARMS_FOR_POOL = ["walk", "sham", "fixed_top5", "los", "two_step", "longform"]


def all_samples() -> list[dict[str, Any]]:
    rows = []
    for a in ARMS_FOR_POOL:
        rows += read_jsonl(DATA / f"samples_{a}.jsonl")
    return rows


def audit_pool(seed: int = 0) -> list[dict[str, Any]]:
    rows = all_samples()
    correct_other = [r for r in rows if r.get("label") == "other" and r.get("passed")]
    rng = random.Random(seed)
    failing = defaultdict(list)
    for r in rows:
        if r.get("label") == "other" and not r.get("passed") and r["arm"] in ("walk", "los", "two_step"):
            failing[r["task"]].append(r)
    pool = [dict(r, audit_role="correct_other") for r in correct_other]
    for t, rs in failing.items():
        rs = sorted(rs, key=lambda r: r["sample_id"])
        for r in rng.sample(rs, min(20, len(rs))):
            pool.append(dict(r, audit_role="failing_other_sample"))
    uniq, seen = [], set()
    for r in pool:
        k = (r["task"], r["code_sha256"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    return uniq


CONTROLS = [
    {"id": "ctrl_ref_kmp", "task": "T04", "expected": "LABELLER MISS", "kind": "catalogue reference (KMP)",
     "file": ("bench", "T04_substring_search", "kmp.py")},
    {"id": "ctrl_ref_bfs_t10", "task": "T10", "expected": "LABELLER MISS", "kind": "catalogue reference (BFS)",
     "file": ("bench", "T10_connected_components", "bfs.py")},
    {"id": "ctrl_obfuscated_uf", "task": "T10", "expected": "LABELLER MISS", "kind": "obfuscated union-find",
     "code": "def solve(n, edges):\n    a = list(range(n))\n    def g(x):\n        while a[x] != x:\n            a[x] = a[a[x]]\n"
             "            x = a[x]\n        return x\n    c = n\n    for u, v in edges:\n        p, q = g(u), g(v)\n"
             "        if p != q:\n            a[p] = q\n            c -= 1\n    return c\n"},
    {"id": "ctrl_degenerate", "task": "T03", "expected": "DEGENERATE", "kind": "hard-coded test shortcut",
     "code": "def solve(nums, k):\n    if nums == [3, 1, 3] and k == 3:\n        return 3\n    if k == 1:\n"
             "        return min(nums)\n    if k == len(nums):\n        return max(nums)\n    return nums[0]\n"},
    {"id": "ctrl_textbook_value_bisection", "task": "T03", "expected": "CATALOGUE VARIANT",
     "kind": "textbook non-catalogue (binary search on the value range with counting)",
     "code": "def solve(nums, k):\n    lo, hi = min(nums), max(nums)\n    while lo < hi:\n        mid = (lo + hi) // 2\n"
             "        cnt = sum(1 for x in nums if x <= mid)\n        if cnt >= k:\n            hi = mid\n        else:\n"
             "            lo = mid + 1\n    return lo\n"},
    {"id": "ctrl_renamed_default", "task": "T03", "expected": "LABELLER MISS", "kind": "renamed default (full sort)",
     "code": "def solve(nums, k):\n    arranged = list(nums)\n    arranged.sort()\n    return arranged[k - 1]\n"},
]


async def _judge_pool(items: list[dict[str, Any]], tag: str) -> list[dict[str, Any]]:
    sem = asyncio.Semaphore(12)
    known = read_jsonl(KNOWN)
    by_task = defaultdict(list)
    for k in known:
        by_task[k["task"]].append(k)
    refs = {t: references(t) for t in TASKS}

    async def one(it):
        t = it["task"]
        sc = scrub(t, it["code"])
        nk = nearest(it["code"], by_task.get(t, []), 3)
        nr = nearest(it["code"], refs[t], 3)
        pr = audit_prompt(t, sc, nk, nr)
        key = sha256_text(pr)
        ta, _ = await call_llm(sem, AUDIT_JUDGE_A, pr, purpose=f"audit_{tag}", max_tokens=300,
                               cache_key=f"auditA|{key}")
        tb, _ = await call_llm(sem, AUDIT_JUDGE_B, pr, purpose=f"audit_{tag}", max_tokens=300,
                               cache_key=f"auditB|{key}")
        return {"id": it.get("id") or it.get("sample_id"), "task": t, "code_sha256": sha256_text(it["code"]),
                "neighbours_known": [{k: v for k, v in n.items() if k != "code"} for n in nk],
                "neighbours_refs": [{k: v for k, v in n.items() if k != "code"} for n in nr],
                "judge_A": parse_audit(ta), "judge_B": parse_audit(tb), "raw_A": (ta or "")[:600],
                "raw_B": (tb or "")[:600]}

    return await asyncio.gather(*[one(it) for it in items])


def run_controls() -> dict[str, Any]:
    items = []
    for c in CONTROLS:
        if "file" in c:
            _, tid, fn = c["file"]
            code = (BENCH_DIR / tid / "references" / fn).read_text()
        else:
            code = c["code"]
        items.append({"id": c["id"], "task": c["task"], "code": code})
    res = asyncio.run(_judge_pool(items, "controls"))
    out = []
    for c, r in zip(CONTROLS, res):
        out.append({"id": c["id"], "kind": c["kind"], "expected": c["expected"], "A": r["judge_A"]["class"],
                    "B": r["judge_B"]["class"]})
    ok_a = sum(o["A"] == o["expected"] for o in out)
    ok_b = sum(o["B"] == o["expected"] for o in out)
    summ = {"controls": out, "judge_A_correct": ok_a, "judge_B_correct": ok_b, "threshold": "5/6",
            "judge_A_pass": ok_a >= 5, "judge_B_pass": ok_b >= 5, "utc": utc_now()}
    write_json(RESULTS / "audit_controls.json", summ)
    logger.info(f"audit controls: A {ok_a}/6, B {ok_b}/6")
    return summ


def run_audit() -> dict[str, Any]:
    pool = audit_pool()
    logger.info(f"audit pool: {len(pool)} unique programs")
    res = asyncio.run(_judge_pool([{"id": r["sample_id"], "task": r["task"], "code": r["code"]} for r in pool],
                                  "pool"))
    recs = []
    for r, a in zip(pool, res):
        recs.append({"sample_id": r["sample_id"], "task": r["task"], "arm": r["arm"], "condition": r.get("condition"),
                     "audit_role": r["audit_role"], "passed": r["passed"], "code_sha256": r["code_sha256"],
                     "code": r["code"], **{k: a[k] for k in ("neighbours_known", "neighbours_refs", "judge_A",
                                                             "judge_B", "raw_A", "raw_B")}})
    write_json(RESULTS / "novelty_audit_judges.json", {"utc": utc_now(), "n": len(recs), "records": recs})
    return {"n": len(recs)}


def run_claims(frac_b: float = 0.2, seed: int = 0) -> dict[str, Any]:
    rows = read_jsonl(DATA / "samples_longform.jsonl")
    raw = {r["sample_id"]: r for r in read_jsonl(DATA / "raw_longform.jsonl")}
    rng = random.Random(seed)
    ids_b = set(rng.sample([r["sample_id"] for r in rows], int(round(frac_b * len(rows))))) if rows else set()

    async def go():
        sem = asyncio.Semaphore(16)

        async def one(r):
            rat = r.get("rationale_text") or ""
            pr = claim_prompt(r["task"], rat, r.get("code"))
            key = sha256_text(pr)
            ta, _ = await call_llm(sem, AUDIT_JUDGE_A, pr, purpose="claims", max_tokens=350, cache_key=f"claimA|{key}")
            tb = None
            if r["sample_id"] in ids_b:
                tb, _ = await call_llm(sem, AUDIT_JUDGE_B, pr, purpose="claims", max_tokens=350,
                                       cache_key=f"claimB|{key}")
            return {"sample_id": r["sample_id"], "task": r["task"], "condition": r["condition"],
                    "engine_dtype": r["engine_dtype"], "label": r["label"], "passed": r["passed"],
                    "A": parse_claim(ta), "B": parse_claim(tb) if tb is not None else None}

        return await asyncio.gather(*[one(r) for r in rows])

    recs = asyncio.run(go())
    write_json(RESULTS / "claims.json", {"utc": utc_now(), "n": len(recs), "n_second_judge": len(ids_b),
                                         "records": recs})
    logger.info(f"claims extracted for {len(recs)} long-form outputs (second judge on {len(ids_b)})")
    return {"n": len(recs)}


if __name__ == "__main__":
    setup_logging(f"audit_{sys.argv[1]}")
    if sys.argv[1] == "corpus":
        build_known_solutions()
    elif sys.argv[1] == "controls":
        run_controls()
    elif sys.argv[1] == "pool":
        run_audit()
    elif sys.argv[1] == "claims":
        run_claims()
