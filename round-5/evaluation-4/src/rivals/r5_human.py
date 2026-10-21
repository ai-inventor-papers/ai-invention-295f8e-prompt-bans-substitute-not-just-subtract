#!/usr/bin/env python3
"""R5 raw input: algorithm composition of accepted HUMAN LeetCode solutions (Mercury) per bench task.

Steps: (1) Mercury rows of the bench-mapped LeetCode problems (source data art_j3Rm_lr2nzR6), dropping I/O hacks
and programs that do not parse; (2) correctness on the leetcodedataset cases with status 'ok', each program in a
fresh stdlib-only subprocess calling Solution().<method>(**kwargs), 2 s per case; (3) labels: the frozen bench AST
rules (path task T2: the exp8 suite AST rules) applied to the method bodies rewritten as top-level functions;
a blind cheap judge (temperature 0, catalogue names + mechanisms, default not named) on every AST 'unknown' and on a
10-program audit per task (agreement < 0.8 -> NOT_COMPUTABLE).  'gate-lite': no runtime labeller.

Reads no outcome file.  Output: rivals/r5_human_raw.json, tables/human_labels.csv, rivals/judge_cache.jsonl.
"""

from __future__ import annotations

import ast
import asyncio
import csv
import hashlib
import importlib.util
import json
import multiprocessing as mp
import os
import random
import subprocess
import sys
import textwrap
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import aiohttp
from loguru import logger

WS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WS / "src"))
from io_util import DEPS  # noqa: E402  (dependency folders: <AII_DEPS_ROOT>/<artifact_id>)

SRC = DEPS["src"][1] / "full_data_out.json"                     # art_j3Rm_lr2nzR6 (source data)
BENCH = DEPS["bench"][1] / "bench"                              # art_0ndRfWKBWclR (bench)
SUITE = DEPS["exp23"][1] / "inputs" / "exp8" / "suite"          # art_k6nzFCDLOjQP (path-task suite)
# stdlib-only CPython 3.12 for the sandboxes (run with -I -S): $SANDBOX_PYTHON, else python3.12 on PATH
SYS_PY = os.environ.get("SANDBOX_PYTHON") or __import__("shutil").which("python3.12") or sys.executable
CACHE = WS / "rivals" / "judge_cache.jsonl"
OUT = WS / "rivals" / "r5_human_raw.json"
JUDGE_MODEL = "google/gemini-2.5-flash-lite"
COST_STOP = 0.80
PRIMARY = {743: "T2", 215: "T03", 28: "T04", 1: "T05", 287: "T06", 509: "T08", 547: "T10", 300: "T11", 56: "T13",
           347: "T14", 435: "R1", 684: "R2", 210: "R3", 34: "R6", 1091: "T1"}
ALTERNATE = {323: "T10", 1971: "T10", 1631: "T2", 1514: "T2"}
T2_MODES = {"dijkstra": "Dijkstra's algorithm with a priority queue (binary heap), lazy deletion or decrease-key",
            "bf_spfa": "Bellman-Ford relaxation rounds over all edges, or its queue-based SPFA variant",
            "bidijkstra": "bidirectional Dijkstra (two simultaneous searches from both ends)",
            "floyd": "Floyd-Warshall all-pairs triple loop",
            "dial": "Dial's algorithm (bucket queue indexed by distance)"}

HARNESS = r'''
import json, sys, threading, io, time
job = json.loads(sys.stdin.read())
sys.setrecursionlimit(100000)
threading.stack_size(256 * 1024 * 1024)
out = sys.stdout
pre = "from typing import *\nimport collections, heapq, bisect, math, itertools, functools, random, string\n" \
      "from collections import *\nfrom heapq import *\nfrom bisect import *\nfrom functools import *\n" \
      "from itertools import *\nfrom math import *\n"
ns = {"__name__": "cand"}
try:
    sys.stdout = io.StringIO()
    exec(compile(pre + job["code"], "<candidate>", "exec"), ns)
    sys.stdout = out
except BaseException as e:
    sys.stdout = out
    print(json.dumps({"error": "load: " + type(e).__name__ + ": " + str(e)[:150]})); sys.exit(0)
res = []
for c in job["cases"]:
    box = {}
    def target():
        try:
            obj = ns["Solution"]()
            box["r"] = getattr(obj, job["method"])(**json.loads(c))
        except BaseException as e:
            box["e"] = type(e).__name__ + ": " + str(e)[:120]
    sys.stdout = io.StringIO()
    th = threading.Thread(target=target, daemon=True); th.start(); th.join(2.0)
    sys.stdout = out
    if th.is_alive():
        res.append({"status": "timeout"}); break
    if "e" in box:
        res.append({"status": "error", "msg": box["e"]}); continue
    try:
        res.append({"status": "ran", "out": json.loads(json.dumps(box["r"]))})
    except (TypeError, ValueError):
        res.append({"status": "error", "msg": "unserialisable output"})
print(json.dumps({"results": res}))
'''


def method_name(code: str) -> str | None:
    tree = ast.parse(code)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Solution":
            for b in node.body:
                if isinstance(b, ast.FunctionDef) and not b.name.startswith("_"):
                    return b.name
    return None


class _SelfStrip(ast.NodeTransformer):
    def visit_Attribute(self, node: ast.Attribute):
        self.generic_visit(node)
        if isinstance(node.value, ast.Name) and node.value.id == "self":
            return ast.copy_location(ast.Name(id=node.attr, ctx=node.ctx), node)
        return node


def as_toplevel(code: str, entry: str) -> str:
    """Rewrite class Solution methods as top-level functions (self removed, entry renamed to solve)."""
    tree = ast.parse(code)
    body = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Solution":
            for b in node.body:
                if isinstance(b, ast.FunctionDef):
                    if b.args.args and b.args.args[0].arg == "self":
                        b.args.args = b.args.args[1:]
                    if b.name == entry:
                        b.name = "solve"
                    body.append(b)
                elif isinstance(b, ast.Assign):
                    body.append(b)
        else:
            body.append(node)
    mod = ast.Module(body=body, type_ignores=[])
    mod = _SelfStrip().visit(mod)
    ast.fix_missing_locations(mod)
    src = ast.unparse(mod)
    return src


def check(qid: int, kwargs: dict, expected, out) -> bool:
    if qid == 1:
        if not isinstance(out, list) or len(out) != 2:
            return False
        if expected is None:
            return False
        i, j = out
        nums = kwargs["nums"]
        return isinstance(i, int) and isinstance(j, int) and i != j and 0 <= i < len(nums) and 0 <= j < len(nums) \
            and nums[i] + nums[j] == kwargs["target"]
    if qid == 347:
        return isinstance(out, list) and sorted(out) == sorted(expected)
    if qid == 56:
        return isinstance(out, list) and sorted(map(list, out)) == sorted(map(list, expected))
    if qid == 210:
        if not isinstance(out, list):
            return False
        if expected == []:
            return out == []
        n = kwargs["numCourses"]
        if sorted(out) != list(range(n)):
            return False
        pos = {c: i for i, c in enumerate(out)}
        return all(pos[b] < pos[a] for a, b in kwargs["prerequisites"])
    return out == expected


def run_program(job: dict) -> dict:
    payload = {"code": job["code"], "method": job["method"], "cases": [json.dumps(c["kwargs"]) for c in job["cases"]]}
    try:
        proc = subprocess.run([SYS_PY, "-I", "-S", "-c", HARNESS], input=json.dumps(payload), capture_output=True,
                              text=True, timeout=2.5 * len(job["cases"]) + 20)
    except subprocess.TimeoutExpired:
        return {"idx": job["idx"], "passed": False, "why": "harness_timeout"}
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("{")]
    if not lines:
        return {"idx": job["idx"], "passed": False, "why": "crash " + proc.stderr[-150:]}
    r = json.loads(lines[-1])
    if "error" in r:
        return {"idx": job["idx"], "passed": False, "why": r["error"]}
    res = r["results"]
    per_case = []
    why = ""
    for i, c in enumerate(job["cases"]):
        x = res[i] if i < len(res) else {"status": "timeout"}
        ok = x["status"] == "ran" and check(job["qid"], c["kwargs"], c["expected"], x["out"])
        per_case.append(bool(ok))
        if not ok and not why:
            why = (x.get("msg") or x["status"] if x["status"] != "ran" else "wrong")[:120]
    return {"idx": job["idx"], "per_case": per_case, "why": why}


def load_ast_labeller(task: str):
    if task == "T2":
        sys.path.insert(0, str(SUITE / "labeller"))
        spec = importlib.util.spec_from_file_location("suite_ast_rules", SUITE / "labeller" / "ast_rules.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return lambda code: mod.label(code, "t2")[0]
    td = next(p for p in BENCH.iterdir() if p.name.startswith(task + "_"))
    # the frozen snapshot has two leading string literals, so its __future__ import is not first: drop that line
    src = (td / "ast_rules.py").read_text().replace("from __future__ import annotations", "")
    ns: dict = {"__name__": f"ast_{task}"}
    exec(compile(src, str(td / "ast_rules.py"), "exec"), ns)
    return lambda code: ns["ast_label"](task, code)


def catalogue(task: str) -> dict[str, str]:
    if task == "T2":
        return dict(T2_MODES)
    td = next(p for p in BENCH.iterdir() if p.name.startswith(task + "_"))
    spec = json.loads((td / "spec.json").read_text())
    return {c["mode"]: f"{c['display_name']}: {c['mechanism']}" for c in spec["catalogue"]}


def judge_prompt(problem: str, code: str, cat: dict[str, str]) -> str:
    opts = "\n".join(f"- {m}: {d}" for m, d in cat.items())
    return (f"Problem statement (LeetCode):\n{problem[:1500]}\n\nHuman Python solution:\n```python\n{code[:6000]}\n```\n\n"
            f"Which ONE of these algorithm families does the solution implement? Judge by the mechanism, not by "
            f"variable names.\n{opts}\n- other: none of the above\n\nAnswer with JSON only: "
            '{"mode": "<one key from the list>", "reason": "<= 20 words"}')


async def judge_all(items: list[dict]) -> list[dict]:
    cache = {}
    if CACHE.exists():
        for ln in CACHE.read_text().splitlines():
            if ln.strip():
                r = json.loads(ln)
                cache[r["key"]] = r
    base = os.environ["OPENROUTER_BASE_URL"].rstrip("/")
    headers = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}", "Content-Type": "application/json"}
    sem = asyncio.Semaphore(8)
    state = {"cost": 0.0, "stop": False}
    out: list[dict | None] = [None] * len(items)

    async def one(i: int, it: dict, session: aiohttp.ClientSession) -> None:
        key = hashlib.sha256((JUDGE_MODEL + it["prompt"]).encode()).hexdigest()
        if key in cache:
            out[i] = {**cache[key], "cached": True}
            return
        async with sem:
            if state["stop"] or state["cost"] >= COST_STOP:
                out[i] = {"key": key, "mode": "NOT_JUDGED", "cost": 0.0}
                return
            body = {"model": JUDGE_MODEL, "temperature": 0, "max_tokens": 120,
                    "messages": [{"role": "user", "content": it["prompt"]}], "usage": {"include": True}}
            for attempt in range(3):
                try:
                    async with session.post(f"{base}/chat/completions", json=body, headers=headers,
                                            timeout=aiohttp.ClientTimeout(total=90)) as resp:
                        js = await resp.json(content_type=None)
                        if resp.status == 403 and "AI Inventor per-run OpenRouter budget" in json.dumps(js):
                            state["stop"] = True
                            out[i] = {"key": key, "mode": "NOT_JUDGED", "cost": 0.0}
                            return
                        if resp.status != 200:
                            raise aiohttp.ClientError(f"status {resp.status}: {json.dumps(js)[:200]}")
                    txt = js["choices"][0]["message"]["content"] or ""
                    cost = float((js.get("usage") or {}).get("cost") or 0.0)
                    state["cost"] += cost
                    s, e = txt.find("{"), txt.rfind("}")
                    mode = "unparsed"
                    if s >= 0 and e > s:
                        try:
                            mode = str(json.loads(txt[s:e + 1]).get("mode", "unparsed")).strip()
                        except json.JSONDecodeError:
                            mode = "unparsed"
                    rec = {"key": key, "mode": mode, "raw": txt[:300], "cost": cost, "model": JUDGE_MODEL}
                    with CACHE.open("a") as fh:
                        fh.write(json.dumps(rec) + "\n")
                    logger.debug(f"judge {it['task']} #{it['idx']}: {mode} ({txt[:80]!r}) cost={cost:.5f}")
                    out[i] = rec
                    return
                except (aiohttp.ClientError, asyncio.TimeoutError, KeyError, json.JSONDecodeError) as e:
                    logger.warning(f"judge retry {attempt}: {e}")
                    await asyncio.sleep(2 * (attempt + 1))
            out[i] = {"key": key, "mode": "NOT_JUDGED", "cost": 0.0}

    async with aiohttp.ClientSession() as session:
        await asyncio.gather(*(one(i, it, session) for i, it in enumerate(items)))
    logger.info(f"judge spend this run: USD {state['cost']:.4f}; stop={state['stop']}")
    return out


@logger.catch(reraise=True)
def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(WS / "logs" / "r5_human.log", rotation="30 MB", level="DEBUG")
    data = json.loads(SRC.read_text())
    ds = {d["dataset"]: d["examples"] for d in data["datasets"] if d["dataset"] in ("mercury", "leetcodedataset")}
    del data
    lc = {}
    for e in ds["leetcodedataset"]:
        q = int(e["metadata_question_id"])
        if q in PRIMARY or q in ALTERNATE:
            # status 'ok' only; two-sum cases without a solution (expected null) are outside LeetCode's guarantee
            lc[q] = {"cases": [c for c in json.loads(e["metadata_test_cases_json"]) if c.get("status") == "ok"
                               and not (q == 1 and c.get("expected") is None)], "problem": e["input"]}
    rows = []
    for e in ds["mercury"]:
        q = int(e["metadata_question_id"])
        if q not in PRIMARY and q not in ALTERNATE:
            continue
        rows.append({"qid": q, "task": PRIMARY.get(q) or ALTERNATE[q], "role": "primary" if q in PRIMARY else "alternate",
                     "code": e["output"], "io_hack": e["metadata_io_hack"] in (True, "True"),
                     "parses": e["metadata_parses_py312"] in (True, "True"), "runtime_ms": e["metadata_runtime_ms"],
                     "sol_idx": e["metadata_solution_index"], "problem": e["input"]})
    logger.info(f"mercury rows for mapped problems: {len(rows)}; leetcode problems with cases: {sorted(lc)}")
    jobs = []
    for i, r in enumerate(rows):
        r["idx"] = i
        r["method"] = method_name(r["code"]) if r["parses"] else None
        if r["io_hack"] or not r["parses"] or r["method"] is None or r["qid"] not in lc or not lc[r["qid"]]["cases"]:
            r["passed"], r["why"] = None, ("io_hack" if r["io_hack"] else "excluded: no parse/method/cases")
            continue
        jobs.append({"idx": i, "qid": r["qid"], "code": r["code"], "method": r["method"], "cases": lc[r["qid"]]["cases"]})
    logger.info(f"running {len(jobs)} human programs on their LeetCode cases")
    with ProcessPoolExecutor(max_workers=4, mp_context=mp.get_context("spawn")) as pool:
        futs = [pool.submit(run_program, j) for j in jobs]
        # (results collected below, after the pool has finished)
        results = [f.result() for f in as_completed(futs)]
    # case filter: a LeetCode case that most ACCEPTED human solutions of the problem fail lies outside the problem's
    # constraints (generated cases); keep cases passed by >= 50% of the problem's runnable solutions
    by_q: dict[int, list[dict]] = {}
    for res in results:
        by_q.setdefault(rows[res["idx"]]["qid"], []).append(res)
    case_filter = {}
    for q, rs in by_q.items():
        ok = [res for res in rs if res.get("per_case") is not None]
        n_cases = len(lc[q]["cases"])
        keep = [i for i in range(n_cases) if ok and sum(res["per_case"][i] for res in ok) / len(ok) >= 0.5]
        case_filter[q] = {"n_cases": n_cases, "n_kept": len(keep), "n_solutions": len(ok)}
        for res in rs:
            if res.get("per_case") is None:
                rows[res["idx"]]["passed"], rows[res["idx"]]["why"] = False, res["why"]
                continue
            passed = bool(keep) and all(res["per_case"][i] for i in keep)
            rows[res["idx"]]["passed"] = passed
            rows[res["idx"]]["why"] = "" if passed else (res["why"] or "fails a kept case")
    logger.info(f"case filter per problem: {case_filter}")
    # AST labels on the rewritten method bodies
    labellers = {}
    for r in rows:
        if r["passed"] is None:
            r["ast_label"] = None
            continue
        t = r["task"]
        if t not in labellers:
            labellers[t] = load_ast_labeller(t) if t != "T1" else None
        try:
            r["top_code"] = as_toplevel(r["code"], r["method"])
            r["ast_label"] = labellers[t](r["top_code"]) if labellers[t] else "unknown"
        except (SyntaxError, ValueError, AttributeError, TypeError, KeyError, IndexError, RecursionError) as e:
            r["ast_label"] = "unknown"
            logger.debug(f"AST labeller failed on {t} #{r['idx']}: {e}")
    # judge: every AST unknown + a 10-program audit per task among AST-labelled correct programs
    rng = random.Random(20261021)
    items = []
    for t in sorted({r["task"] for r in rows}):
        if t == "T1":
            continue
        cat = catalogue(t)
        pool_t = [r for r in rows if r["task"] == t and r["passed"]]
        unk = [r for r in pool_t if r["ast_label"] not in cat and r["ast_label"] != "other"]
        lab = [r for r in pool_t if r["ast_label"] in cat or r["ast_label"] == "other"]
        audit = rng.sample(lab, min(10, len(lab)))
        for r in unk:
            r["judge_role"] = "unknown"
        for r in audit:
            r["judge_role"] = "audit"
        for r in unk + audit:
            items.append({"task": t, "idx": r["idx"], "prompt": judge_prompt(r["problem"], r["code"], cat)})
    logger.info(f"judge items: {len(items)} (model {JUDGE_MODEL}, temperature 0, stop at USD {COST_STOP})")
    res = asyncio.run(judge_all(items))
    spend = 0.0
    for it, jr in zip(items, res):
        rows[it["idx"]]["judge_label"] = jr["mode"]
        spend += float(jr.get("cost") or 0.0) if not jr.get("cached") else 0.0
    for r in rows:
        r.setdefault("judge_label", None)
        r.setdefault("judge_role", None)
        cat = catalogue(r["task"]) if r["task"] != "T1" else {}
        if r["passed"] and (r["ast_label"] in cat or r["ast_label"] == "other"):
            r["final_label"] = r["ast_label"]
        elif r["passed"] and r["judge_label"] in list(cat) + ["other"]:
            r["final_label"] = r["judge_label"]
        else:
            r["final_label"] = "unlabelled" if r["passed"] else None
    keep = ["idx", "qid", "task", "role", "sol_idx", "runtime_ms", "io_hack", "parses", "method", "passed", "why",
            "ast_label", "judge_label", "judge_role", "final_label"]
    OUT.write_text(json.dumps({"judge_model": JUDGE_MODEL, "judge_spend_usd_this_run": spend,
                               "case_filter": {str(k): v for k, v in case_filter.items()},
                               "rows": [{k: r.get(k) for k in keep} for r in rows]}, indent=1))
    with (WS / "tables" / "human_labels.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keep)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in keep})
    logger.info(f"wrote {OUT.relative_to(WS)}; judge spend USD {spend:.4f}")


if __name__ == "__main__":
    main()
