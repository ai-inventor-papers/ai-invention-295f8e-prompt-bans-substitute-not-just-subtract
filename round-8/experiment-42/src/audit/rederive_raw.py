#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers from the RAW generations (data/raw_*.jsonl), through code paths
that share nothing with the pipeline: own code extraction, own hidden-test runner and path checker (stdlib, one
subprocess per program), own BFS/DFS classifier (structural heuristic, not the runtime tracer/AST labeller), and
McNemar via scipy.stats.binomtest (not analysis8 / rederive.py). Placebos: within-slot label permutations must make
every paired test non-significant. Writes results/rederive_raw.json.  Run: .venv/bin/python audit/rederive_raw.py"""

import json
import random
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parents[1]
T1 = ROOT / "inputs" / "iter6_gemma" / "inputs" / "exp8" / "suite" / "tasks" / "t1_grid"
CELLS = {"P-twin": "bfs", "G1a": "bfs", "P-DAS-bfs": "bfs", "F-twin": "bfs", "G1c": "bfs", "F-DAS-r4-bfs-1.0": "bfs",
         "F-DiM-bfs": "bfs", "G1e|F3|3": "bfs"}
S50 = [(w, k) for w in ("W1", "W2", "W3", "W4", "W5") for k in range(10)]
RUNNER = r'''
import json, sys, threading
sys.setrecursionlimit(20000); threading.stack_size(256 * 1024 * 1024)
job = json.loads(sys.stdin.read()); ns = {}
try:
    exec(compile(job["code"], "<cand>", "exec"), ns)
except BaseException as e:
    print(json.dumps({"ok": False, "why": "exec " + type(e).__name__})); sys.exit()
def valid(case, out):
    g, s, t = case["grid"], tuple(case["start"]), tuple(case["goal"])
    if not isinstance(out, (list, tuple)): return False
    if not case["reachable"]: return len(out) == 0
    try: p = [(int(a), int(b)) for a, b in out]
    except Exception: return False
    if not p or p[0] != s or p[-1] != t: return False
    if any(not (0 <= r < len(g) and 0 <= c < len(g[0])) or g[r][c] != "." for r, c in p): return False
    return all(abs(a - c) + abs(b - d) == 1 for (a, b), (c, d) in zip(p, p[1:]))
for case in sorted(job["cases"], key=lambda c: c["size"]):
    box = {}
    def go():
        try: box["out"] = ns["solve"](list(case["grid"]), tuple(case["start"]), tuple(case["goal"]))
        except BaseException as e: box["err"] = type(e).__name__
    th = threading.Thread(target=go, daemon=True); th.start(); th.join(job["limits"].get(case["id"], 1.0))
    if th.is_alive(): print(json.dumps({"ok": False, "why": "timeout " + case["id"]})); sys.exit()
    if "err" in box or not valid(case, box.get("out")):
        print(json.dumps({"ok": False, "why": "fail " + case["id"]})); sys.exit()
print(json.dumps({"ok": True, "why": "all"}))
'''


def extract(text: str) -> str | None:
    for m in re.finditer(r"```(?:python|py)?\s*\n(.*?)(?:```|$)", text, re.S):
        if "def solve" in m.group(1):
            return m.group(1)
    return None


def classify(code: str) -> str:
    """BFS = FIFO frontier (popleft / pop(0) / Queue.get); DFS = recursion of a helper or a LIFO stack pop()."""
    funcs = re.findall(r"^\s*def\s+(\w+)\s*\(", code, re.M)
    recursive = any(len(re.findall(rf"\b{f}\s*\(", code)) >= 2 and f != "solve" or
                    (f == "solve" and len(re.findall(r"\bsolve\s*\(", code)) >= 2) for f in funcs)
    fifo = bool(re.search(r"\.popleft\s*\(|\.pop\s*\(\s*0\s*\)|\.get\s*\(\s*\)", code))
    lifo = bool(re.search(r"\b(stack|st|stk)\.pop\s*\(\s*\)", code))
    if fifo and not (recursive or lifo):
        return "bfs"
    if (recursive or lifo) and not fifo:
        return "dfs"
    return "bfs" if fifo else "unknown"


def run(code: str, cases: list, limits: dict) -> dict:
    try:
        p = subprocess.run([sys.executable, "-I", "-S", "-c", RUNNER], input=json.dumps(
            {"code": code, "cases": cases, "limits": limits}), capture_output=True, text=True, timeout=120)
        line = [ln for ln in p.stdout.splitlines() if ln.startswith("{")]
        return json.loads(line[-1]) if line else {"ok": False, "why": "crash"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "why": "runner timeout"}


def main() -> None:
    cases = json.loads((T1 / "tests.json").read_text())
    limits = json.loads((T1 / "limits.json").read_text())["limits"]
    raw = {}
    for f in sorted((ROOT / "data").glob("raw_*.jsonl")):
        for ln in f.read_text().splitlines():
            if ln.strip():
                r = json.loads(ln)
                if r.get("cell") in CELLS and int(r["slot"]) < 10:
                    raw[(r["cell"], r["template"], int(r["slot"]))] = r
    keys = sorted(raw)
    codes = {k: extract(raw[k]["text"]) for k in keys}
    with ThreadPoolExecutor(12) as ex:
        res = dict(zip(keys, ex.map(lambda k: run(codes[k], cases, limits) if codes[k] else {"ok": False, "why": "no code"}, keys)))
    lab = {}
    for ln in (ROOT / "data" / "labels.jsonl").read_text().splitlines():
        if ln.strip():
            r = json.loads(ln)
            lab[(r["cell"], r["template"], int(r["slot"]))] = r
    corr = {k: (classify(codes[k]) == CELLS[k[0]] if codes[k] else False) and res[k]["ok"] for k in keys}
    out = {"cells": {}, "tests": {}, "placebo": {}}
    for c in CELLS:
        ks = [(c, w, k) for w, k in S50 if (c, w, k) in raw]
        out["cells"][c] = {"n": len(ks), "pass_independent": sum(res[k]["ok"] for k in ks),
                           "pass_labeller": sum(bool(lab[k]["passed"]) for k in ks),
                           "class_agreement_with_labeller": sum(classify(codes[k] or "") == lab[k]["label"] for k in ks) / len(ks),
                           "correct_independent": sum(corr[k] for k in ks),
                           "correct_labeller": sum(lab[k]["label"] == CELLS[c] and bool(lab[k]["passed"]) for k in ks),
                           "fail_reasons": sorted({res[k]["why"].split(" ")[0] + " " + res[k]["why"].split(" ")[-1]
                                                   for k in ks if not res[k]["ok"]})[:6]}

    def mcnemar(a: str, b: str, alt: str, flip: random.Random | None = None) -> dict:
        n10 = n01 = 0
        for w, k in S50:
            x, y = corr[(a, w, k)], corr[(b, w, k)]
            if flip is not None and flip.random() < 0.5:
                x, y = y, x
            n10 += x and not y
            n01 += y and not x
        p = binomtest(n10, n10 + n01, 0.5, alternative=alt).pvalue if n10 + n01 else 1.0
        return {"a_only": n10, "b_only": n01, "p": p}
    tests = {"P1b dial vs prompt, prefilled": ("P-DAS-bfs", "G1a", "two-sided"),
             "P2 free dial vs free twin": ("F-DAS-r4-bfs-1.0", "F-twin", "greater"),
             "free dial vs free prompt F5": ("F-DAS-r4-bfs-1.0", "G1c", "two-sided"),
             "free prompt best wording F3 vs free dial": ("G1e|F3|3", "F-DAS-r4-bfs-1.0", "two-sided"),
             "prefilled dial vs free dial": ("P-DAS-bfs", "F-DAS-r4-bfs-1.0", "two-sided")}
    rng = random.Random(0)
    for name, (a, b, alt) in tests.items():
        out["tests"][name] = mcnemar(a, b, alt)
        ps = [mcnemar(a, b, alt, rng)["p"] for _ in range(1000)]
        out["placebo"][name] = {"share_p_lt_0.05_under_within_slot_permutation": sum(p < 0.05 for p in ps) / len(ps)}
    sh = lambda c: sum(corr[(c, w, k)] for w, k in S50) / 50      # noqa: E731
    out["interaction"] = (sh("P-DAS-bfs") - sh("G1a")) - (sh("F-DAS-r4-bfs-1.0") - sh("G1c"))
    (ROOT / "results" / "rederive_raw.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
