#!/usr/bin/env python3
"""Step C: code extraction, hidden tests, bench labellers (runtime tracer primary, AST second), blind judge on
disagreements only, name-scrub verification for forced programs, association mapping, and the Llama label audit.

Extraction rule (plan C1): the first ```python fenced block that defines solve; else the largest fenced block that
defines solve; else (unterminated final block, truncated answer) the open block if it defines solve; else 'invalid'.
"""

from __future__ import annotations

import collections
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from loguru import logger

from src.ws import DATA, EXP11, JUDGE_CAP_USD, LOGS, WS, append_jsonl, read_jsonl, write_jsonl

from bench.common import judge as BJ  # noqa: E402
from bench.common.astrules import ast_label  # noqa: E402
from bench.common.catalogue import TASKS  # noqa: E402
from bench.common.harness import code_sha, run_tests, syntax_ok  # noqa: E402
from bench.common.order import mentions  # noqa: E402
from bench.common.probes import run_trace  # noqa: E402
from bench.common.rtrules import runtime_label  # noqa: E402
from bench.common.scrub import scrub_response  # noqa: E402
from bench.common.testgen import read_tests  # noqa: E402

BJ.PERSONAL_CAP = JUDGE_CAP_USD  # this artifact's hard stop (module global read at call time)
LABELS_RAW = DATA / "labels_raw.jsonl"
LABELS = DATA / "labels.jsonl"
ASSOC = DATA / "association.jsonl"
FENCE_ALL = re.compile(r"```[ \t]*([A-Za-z0-9_+-]*)[ \t]*\n(.*?)```", re.S)
OPEN_FENCE = re.compile(r"```[ \t]*(?:python3?|py|Python)?[ \t]*\n(.*)$", re.S)
DEF_SOLVE = re.compile(r"^\s*def\s+solve\s*\(", re.M)


def extract(text: str | None) -> tuple[str | None, dict[str, Any]]:
    info = {"n_blocks": 0, "rule": None, "prose_before": None, "prose_after": None}
    if not text:
        return None, info
    blocks = [(m.group(1).lower(), m.group(2), m.start(), m.end()) for m in FENCE_ALL.finditer(text)]
    info["n_blocks"] = len(blocks)
    chosen = None
    for lang, body, a, b in blocks:
        if lang in ("python", "python3", "py") and DEF_SOLVE.search(body):
            chosen, info["rule"] = (body, a, b), "first_python_with_solve"
            break
    if chosen is None:
        cands = [(len(body), body, a, b) for lang, body, a, b in blocks if DEF_SOLVE.search(body)]
        if cands:
            _, body, a, b = max(cands, key=lambda x: x[0])
            chosen, info["rule"] = (body, a, b), "largest_with_solve"
    if chosen is None:
        last_close = blocks[-1][3] if blocks else 0
        m = OPEN_FENCE.search(text, last_close)
        if m and DEF_SOLVE.search(m.group(1)):
            chosen, info["rule"] = (m.group(1), m.start(), len(text)), "open_block"
    if chosen is None:
        return None, info
    body, a, b = chosen
    info["prose_before"] = len(text[:a].strip())
    info["prose_after"] = len(text[b:].strip())
    return body, info


_CASES: dict[str, list[dict]] = {}


def cases(task: str) -> list[dict]:
    if task not in _CASES:
        _CASES[task] = read_tests(EXP11 / "bench" / TASKS[task]["task_id"] / "tests.jsonl")
    return _CASES[task]


def label_one(row: dict[str, Any]) -> dict[str, Any]:
    t = row["task"]
    code, info = extract(row.get("text"))
    out = {"row_id": row["row_id"], "task": t, "phase": row.get("phase"), "condition": row.get("condition"),
           "code_sha256": code_sha(code), "extracted": code is not None, "extract_rule": info["rule"],
           "n_blocks": info["n_blocks"], "prose_before": info["prose_before"], "prose_after": info["prose_after"]}
    if code is None or not syntax_ok(code) or "def solve" not in code:
        out.update(valid=False, passed=False, ast_label="invalid", runtime_label="invalid")
        return out
    out["valid"] = True
    tr = run_tests(code, t, cases(t))
    out.update(passed=tr["passed"], n_pass=tr["n_pass"], n_cases=tr["n_cases"], load_error=tr["load_error"],
               statuses_sig="".join(s[0] for s in tr["statuses"]))
    out["ast_label"] = ast_label(t, code)
    trace = run_trace(code, t)
    out["runtime_label"] = runtime_label(t, trace)
    out["trace_error"] = trace.get("error")
    if str(row.get("condition", "")).startswith("forced"):
        s_text, s_code, sinfo = scrub_response(row["text"], code)
        sc = {"changed": s_code != code, "ok": sinfo["ok"], "renamed": sinfo["renamed"]}
        if s_code != code and sinfo["ok"]:
            tr2 = run_tests(s_code, t, cases(t))
            sc["same_tests"] = "".join(s[0] for s in tr2["statuses"]) == out["statuses_sig"]
            sc["runtime_label"] = runtime_label(t, run_trace(s_code, t))
            sc["same_runtime_label"] = sc["runtime_label"] == out["runtime_label"]
        elif s_code == code:
            sc["same_tests"] = True
            sc["same_runtime_label"] = True
        else:
            sc["same_tests"] = False
            sc["same_runtime_label"] = False
        sc["verified"] = bool(sc["ok"] and sc["same_tests"] and sc["same_runtime_label"])
        out["scrub"] = sc
        out["scrubbed_code"] = s_code if sc["verified"] else None
    return out


def pilot_rows() -> list[dict[str, Any]]:
    """exp11's 50 FP8 Llama pilot generations per task, as raw rows (relabelled here with the copied labeller)."""
    out = []
    for r in read_jsonl(EXP11 / "data" / "samples_llama_pilot_raw.jsonl"):
        out.append({"row_id": f"pilot|{r['task']}|{r['sample_id']}", "phase": "pilot", "task": r["task"],
                    "condition": "pilot_fp8", "template": None, "sample_id": r["sample_id"], "seed": r["seed"],
                    "text": r["text"], "finish_reason": r.get("finish_reason"), "model": r.get("model"),
                    "n_new_tokens": None, "prompt_sha256": None})
    return out


def label_rows(rows: list[dict[str, Any]], workers: int = 4) -> int:
    done = {r["row_id"] for r in read_jsonl(LABELS_RAW)}
    todo = [r for r in rows if r["row_id"] not in done and r.get("phase") != "B2" and r["task"] in TASKS]
    if not todo:
        return 0
    logger.info(f"labelling {len(todo)} programs with {workers} workers")
    t0 = time.time()
    n = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(label_one, r): r["row_id"] for r in todo}
        buf = []
        for fu in as_completed(futs):
            try:
                res = fu.result()
            except Exception as e:  # noqa: BLE001 - record, never silently drop
                logger.error(f"labelling failed for {futs[fu]}: {e}")
                res = {"row_id": futs[fu], "valid": False, "passed": False, "ast_label": "invalid",
                       "runtime_label": "invalid", "label_error": str(e)[:300]}
            buf.append(res)
            n += 1
            if len(buf) >= 25:
                append_jsonl(LABELS_RAW, buf)
                buf = []
            if n % 200 == 0:
                logger.info(f"  labelled {n}/{len(todo)} in {time.time() - t0:.0f}s")
        if buf:
            append_jsonl(LABELS_RAW, buf)
    logger.info(f"labelling done: {n} in {time.time() - t0:.0f}s")
    return n


def needs_judge(r: dict[str, Any]) -> bool:
    if not r.get("valid"):
        return False
    a, rt = r.get("ast_label"), r.get("runtime_label")
    return rt == "unknown" or (a != "unknown" and a != rt)


def combine(raw_by_id: dict[str, dict[str, Any]], judge_ok: bool = True) -> list[dict[str, Any]]:
    """Combined label per labelled program; judge (j1, blind, name-scrubbed code) on disagreements only."""
    labs = {}
    for r in read_jsonl(LABELS_RAW):
        labs[r["row_id"]] = r
    need = [r for r in labs.values() if needs_judge(r)]
    jl: dict[str, dict] = {}
    if need and judge_ok:
        if "OPENROUTER_BASE_URL" not in os.environ or "OPENROUTER_API_KEY" not in os.environ:
            # offline re-analysis: every judgement is served from data/judge_cache.jsonl; an uncached call fails
            # (connection refused) and is recorded as 'unresolved', never as a label
            logger.warning("OPENROUTER_* not set: judge answers come from data/judge_cache.jsonl only")
            os.environ.setdefault("OPENROUTER_BASE_URL", "http://127.0.0.1:9/v1")
            os.environ.setdefault("OPENROUTER_API_KEY", "offline")
        judge = BJ.Judge(WS)
        items, ids = [], []
        for r in need:
            raw = raw_by_id.get(r["row_id"])
            code, _ = extract(raw["text"]) if raw else (None, None)
            if code:
                items.append(("j1", r["task"], code))
                ids.append(r["row_id"])
        if items:
            recs = judge.label_many(items)
            jl = dict(zip(ids, recs))
            logger.info(f"judge: {len(items)} disagreements; spend so far ${judge.spent:.4f}")
    out = []
    for rid, r in labs.items():
        if not r.get("valid"):
            lab, src = "invalid", "extraction"
        elif rid in jl or needs_judge(r):
            rec = jl.get(rid, {})
            if rec.get("label"):
                lab, src = rec["label"], "judge"
            else:
                lab, src = "unresolved", "unresolved"
        else:
            lab = r["runtime_label"]
            src = "runtime+ast" if r["ast_label"] == r["runtime_label"] else "runtime(ast_unknown)"
        rr = {k: v for k, v in r.items() if k not in ("scrubbed_code",)}
        rr.update(label=lab, labeller_source=src, judge_label=jl.get(rid, {}).get("label"),
                  runtime_fallback_label=(r.get("runtime_label") if lab == "unresolved" else None))
        out.append(rr)
    write_jsonl(LABELS, out)
    return out


def judge_spend() -> float:
    """All OpenRouter spend of this artifact: bench judge ledger + the screen's canon judge ledger."""
    p = LOGS / "openrouter_spend.jsonl"
    tot = sum((json.loads(l).get("cost") or 0.0) for l in p.read_text().splitlines()) if p.exists() else 0.0
    return tot + screen_spend()


def screen_spend() -> float:
    cf = WS / "screen10" / "canon" / "results" / "openrouter_cost.json"
    if not cf.exists():
        return 0.0
    d = json.loads(cf.read_text())
    if isinstance(d, dict):
        vals = d.get("by_purpose") or d.get("purposes") or {k: v for k, v in d.items() if isinstance(v, (int, float))}
        if isinstance(vals, dict):
            return float(sum(v if isinstance(v, (int, float)) else (v.get("usd") or v.get("cost") or 0.0)
                             for v in vals.values()))
    return 0.0


# ------------------------------------------------------------------------------------------------ association map
def map_association(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Lexicon first (bench order.mentions: earliest-mentioned survivor), blind judge for unmapped answers."""
    out, need = [], []
    for r in rows:
        x = r["mode"]
        pos = mentions(r["task"], r["text"] or "")
        surv = {m: p for m, p in pos.items() if m != x}
        if surv:
            lab, src = min(surv, key=surv.get), "lexicon"
        elif x in pos:
            lab, src = x, "lexicon_names_X"
        else:
            lab, src = None, "judge"
            need.append(r)
        out.append({"row_id": r["row_id"], "task": r["task"], "X": x, "sample_id": r["sample_id"], "seed": r["seed"],
                    "answer": r["text"], "mapped": lab, "map_source": src})
    if need:
        j = BJ.Judge(WS)
        items = []
        for r in need:
            c = TASKS[r["task"]]
            cat = "\n".join(f"- {m}: {d[1]}" for m, d in c["modes"].items())
            from bench.common.catalogue import display_name
            items.append((r, f"Task:\n{c['description']}\n\nSomeone was asked for the standard alternative to "
                             f"'{display_name(r['task'], r['mode'])}' (label {r['mode']}) for this task and answered:\n"
                             f"\"{(r['text'] or '').strip()[:600]}\"\n\nWhich label does the answer propose? Labels:\n"
                             f"{cat}\n- other: none of these\n\nAnswer with JSON only: "
                             "{\"label\": \"<label id>\", \"rationale\": \"<short>\"}"))
        recs = j.label_prompts([("j1", r["task"], p) for r, p in items])
        lab_by = {r["row_id"]: rec.get("label") for (r, _), rec in zip(items, recs)}
        for o in out:
            if o["row_id"] in lab_by:
                o["mapped"] = lab_by[o["row_id"]] or "unmapped"
    for o in out:
        o["category"] = ("names_X" if o["mapped"] == o["X"] else
                         "off_catalogue" if o["mapped"] in ("other", "unmapped", None) else "survivor")
    write_jsonl(ASSOC, out)
    return out


# ------------------------------------------------------------------------------------------------ label audit (C3)
def label_audit(raw_by_id: dict[str, dict[str, Any]], labels: list[dict[str, Any]], per_task: int = 5,
                seed: int = 0) -> dict[str, Any]:
    """Second blind judge (j2, gpt-4.1-mini) on 5 bf16 baseline programs per task; agreement with the combined label."""
    import random

    rng = random.Random(seed)
    by_task = collections.defaultdict(list)
    for r in labels:
        if r.get("phase") == "B1" and r.get("valid"):
            by_task[r["task"]].append(r)
    picks = []
    for t in sorted(by_task):
        rs = sorted(by_task[t], key=lambda r: r["row_id"])
        picks += rng.sample(rs, min(per_task, len(rs)))
    j = BJ.Judge(WS)
    items = []
    for r in picks:
        code, _ = extract(raw_by_id[r["row_id"]]["text"])
        items.append(("j2", r["task"], code))
    recs = j.label_many(items)
    per = collections.defaultdict(lambda: [0, 0])
    rows = []
    for r, rec in zip(picks, recs):
        a = rec.get("label")
        if a is None:
            continue
        per[r["task"]][1] += 1
        per[r["task"]][0] += int(a == r["label"])
        rows.append({"row_id": r["row_id"], "task": r["task"], "combined": r["label"], "audit_j2": a})
    agree = {t: v[0] / v[1] for t, v in per.items() if v[1]}
    tot = sum(v[0] for v in per.values()) / max(sum(v[1] for v in per.values()), 1)
    return {"n": len(rows), "overall_agreement": tot, "per_task": agree,
            "flagged_tasks_below_0.85": sorted(t for t, a in agree.items() if a < 0.85), "rows": rows,
            "judge": BJ.JUDGES["j2"], "spend_total_after": j.spent}


def other_reaudit(raw_by_id: dict[str, dict[str, Any]], labels: list[dict[str, Any]], cap_n: int = 300) -> dict[str, Any]:
    """Ban outputs labelled 'other' re-audited by the second blind judge (j2): how many are a disguised banned X?"""
    rows = [r for r in labels if r.get("phase") in ("G1", "G2") and r["label"] == "other"][:cap_n]
    j = BJ.Judge(WS)
    items, keep = [], []
    for r in rows:
        raw = raw_by_id[r["row_id"]]
        code, _ = extract(raw["text"])
        if code:
            items.append(("j2", r["task"], code))
            keep.append((r, raw))
    recs = j.label_many(items) if items else []
    per = collections.defaultdict(lambda: collections.Counter())
    out_rows = []
    for (r, raw), rec in zip(keep, recs):
        lab = rec.get("label")
        X = raw.get("mode")
        cat = "unavailable" if lab is None else ("banned_X" if lab == X else "other" if lab == "other" else "survivor")
        per[raw.get("event_id")][cat] += 1
        out_rows.append({"row_id": r["row_id"], "event_id": raw.get("event_id"), "X": X, "j2": lab, "category": cat})
    return {"n": len(out_rows), "per_event": {k: dict(v) for k, v in per.items()}, "rows": out_rows,
            "judge": BJ.JUDGES["j2"], "spend_total_after": j.spent,
            "note": "the manual read of up to 20 programs was not done (time); the j2 re-audit is the only check"}
