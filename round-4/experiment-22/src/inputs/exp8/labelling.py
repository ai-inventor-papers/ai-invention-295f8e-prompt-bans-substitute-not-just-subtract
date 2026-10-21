#!/usr/bin/env python3
"""Canonical exp1 labeller, used unchanged (suite/ is a byte-identical copy of exp1 tasks/, labeller/, common.py).

label_texts(): extract code -> hidden tests + runtime probes (sandboxed subprocesses) -> runtime label (primary)
and AST label (second) -> blind judge only on disagreement/unknown (OpenRouter, capped) -> combine.
Mechanism-level labels: the runtime signature decides, so a renamed BFS is still BFS.
"""

from __future__ import annotations

import json
import sys
import threading
from typing import Any

from loguru import logger

from cfg import DATA_DIR, JUDGE_CAP_USD, JUDGE_MODEL, SUITE, sha256_text

if str(SUITE) not in sys.path:
    sys.path.insert(0, str(SUITE))

EVAL_CACHE = DATA_DIR / "program_eval_cache.jsonl"
_CACHE_LOCK = threading.Lock()
_EVAL: dict[str, dict[str, Any]] | None = None


def _load_eval_cache() -> dict[str, dict[str, Any]]:
    global _EVAL
    if _EVAL is None:
        _EVAL = {}
        if EVAL_CACHE.exists():
            for line in EVAL_CACHE.read_text().splitlines():
                if line.strip():
                    try:
                        r = json.loads(line)
                        _EVAL[r["key"]] = r
                    except json.JSONDecodeError:
                        continue
    return _EVAL


def _trim(pr: dict[str, Any]) -> dict[str, Any]:
    out = dict(pr)
    probes = []
    for p in pr.get("probes", []):
        q = dict(p)
        q["heaps"] = [{"push": h.get("push", 0), "pop": h.get("pop", 0), "pops": h.get("pops", [])[:120]}
                      for h in p.get("heaps", [])]
        probes.append(q)
    out["probes"] = probes
    return out


def evaluate_unique(progs: list[dict[str, Any]], workers: int = 10) -> dict[str, dict[str, Any]]:
    """progs: [{'task','code','key'}] -> key -> evaluation record (tests summary + trimmed raw probes); disk-cached."""
    from tasks.harness import evaluate_program, parallel_map

    cache = _load_eval_cache()
    todo = [p for p in progs if p["key"] not in cache]
    logger.info(f"evaluate_unique: {len(progs)} unique programs, {len(todo)} to run")

    def work(p: dict[str, Any]) -> dict[str, Any]:
        ev = evaluate_program(p["task"], p["code"])
        t = ev["tests"]
        return {"key": p["key"], "task": p["task"], "passed": bool(t.get("passed")), "wall_s": t.get("wall_s"),
                "error": t.get("error"), "fail_case": t.get("fail_case"), "fail_msg": t.get("fail_msg"),
                "n_passed": t.get("n_passed"), "probes": _trim(ev["probes"])}

    for i in range(0, len(todo), 200):
        part = todo[i:i + 200]
        res = parallel_map(work, part, workers=workers, desc=f"evaluate {i + len(part)}/{len(todo)}")
        with _CACHE_LOCK, EVAL_CACHE.open("a") as fh:
            for r in res:
                if r and "key" in r:
                    fh.write(json.dumps(r) + "\n")
                    cache[r["key"]] = r
    return cache


def mechanical(task: str, code: str, ev: dict[str, Any]) -> dict[str, Any]:
    from labeller import ast_rules, runtime_rules

    rl, rwhy, _ = runtime_rules.label(task, ev["probes"])
    al, awhy, _ = ast_rules.label(code, task)
    return {"runtime_label": rl, "runtime_reason": rwhy, "ast_label": al, "ast_reason": awhy}


def label_codes(items: list[dict[str, Any]], use_judge: bool = True, purpose: str = "judge",
                cap_usd: float = JUDGE_CAP_USD) -> list[dict[str, Any]]:
    """items: [{'task','code'}] (code may be None) -> per-item label dicts in input order."""
    from labeller.combine import combine, needs_judge
    from labeller.judge import judge_many

    uniq: dict[str, dict[str, Any]] = {}
    keys: list[str | None] = []
    for it in items:
        if it.get("code") is None:
            keys.append(None)
            continue
        k = f"{it['task']}|{sha256_text(it['code'])}"
        keys.append(k)
        uniq.setdefault(k, {"task": it["task"], "code": it["code"], "key": k})
    cache = evaluate_unique(list(uniq.values()))
    mech = {k: mechanical(u["task"], u["code"], cache[k]) for k, u in uniq.items()}
    need = [u for k, u in uniq.items() if needs_judge(mech[k]["runtime_label"], mech[k]["ast_label"])]
    stop: dict[str, Any] = {"stop": False}
    if need and use_judge:
        judged, stop = judge_many(need, JUDGE_MODEL, purpose, cap_usd)
    else:
        judged = [None] * len(need)
    jmap = {u["key"]: j for u, j in zip(need, judged)}
    out = []
    for it, k in zip(items, keys):
        if k is None:
            out.append({"label": "no_code", "labeller_source": "no_code", "passed": False, "n_passed": 0,
                        "fail_case": "no_code", "runtime_label": None, "ast_label": None, "judge_label": None,
                        "judge_skipped": False})
            continue
        ev, mk, j = cache[k], mech[k], jmap.get(k)
        lbl, src = combine(mk["runtime_label"], mk["ast_label"], j)
        out.append({"label": lbl, "labeller_source": src, "passed": bool(ev["passed"]), "n_passed": ev.get("n_passed"),
                    "fail_case": ev.get("fail_case"), "test_error": ev.get("error"), "wall_s": ev.get("wall_s"),
                    "runtime_label": mk["runtime_label"], "ast_label": mk["ast_label"],
                    "runtime_reason": mk["runtime_reason"], "ast_reason": mk["ast_reason"],
                    "judge_label": j["label"] if j else None,
                    "judge_skipped": bool(needs_judge(mk["runtime_label"], mk["ast_label"]) and j is None)})
    n_j = sum(1 for o in out if o["labeller_source"] == "judge")
    n_skip = sum(1 for o in out if o.get("judge_skipped"))
    logger.info(f"label_codes: {len(items)} items, {len(uniq)} unique; judge-labelled {n_j}, judge_skipped {n_skip}; "
                f"stop={stop}")
    return out


def extract(text: str) -> tuple[str | None, str]:
    from labeller.extract import extract_code

    return extract_code(text)


def judge_spent() -> float:
    from labeller.judge import load_cost

    return float(load_cost().get("total_usd", 0.0))
