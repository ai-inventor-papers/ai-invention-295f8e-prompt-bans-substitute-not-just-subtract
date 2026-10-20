#!/usr/bin/env python3
"""Canonical iteration-1 labeller (exp1, unchanged code under inputs/exp1): extract -> hidden tests + tracer probes
(fresh stdlib-only subprocesses) -> runtime rules + AST rules -> blind judge (gpt-4.1-mini) ONLY on disagreement or
unknown -> combine(). Judge spend is capped (core.OPENROUTER_CAP_USD) and stops at the first budget 403.
Also: the exp3 commitment locator (commit_idx) and the 'label' stage that assembles results/samples.jsonl.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from loguru import logger

from core import (BUDGET_MSG, EXP1, EXP3, EXP3_TASK, JUDGE_MODEL, OPENROUTER_CAP_USD, RESULTS, add_spend,
                  append_jsonl, exp1_on_path, load_module, read_jsonl, sha256_text, spend_state, utc_now,
                  write_json, write_jsonl)

EVAL_CACHE = RESULTS / "eval_cache.jsonl"
JUDGE_CACHE = RESULTS / "judge_cache.jsonl"
RAW = RESULTS / "raw"
NO_CODE = "no_code"
_EVAL: dict[str, dict[str, Any]] | None = None


def _eval_cache() -> dict[str, dict[str, Any]]:
    global _EVAL
    if _EVAL is None:
        _EVAL = {r["key"]: r for r in read_jsonl(EVAL_CACHE)}
    return _EVAL


def _trim_probes(pr: dict[str, Any]) -> dict[str, Any]:
    out = dict(pr)
    probes = []
    for p in pr.get("probes", []):
        q = dict(p)
        q["heaps"] = [{"push": h.get("push", 0), "pop": h.get("pop", 0), "pops": h.get("pops", [])[:120]}
                      for h in p.get("heaps", [])]
        probes.append(q)
    out["probes"] = probes
    return out


def evaluate_unique(progs: list[dict[str, Any]], workers: int = 5) -> dict[str, dict[str, Any]]:
    """progs: [{'task','code','key'}] -> key -> {tests summary + trimmed raw probes}; cached on disk."""
    exp1_on_path()
    from tasks.harness import evaluate_program, parallel_map

    cache = _eval_cache()
    todo = [p for p in progs if p["key"] not in cache]
    logger.info(f"evaluate_unique: {len(progs)} unique programs, {len(todo)} not cached")

    def work(p: dict[str, Any]) -> dict[str, Any]:
        ev = evaluate_program(p["task"], p["code"])
        t = ev["tests"]
        return {"key": p["key"], "task": p["task"], "passed": bool(t.get("passed")), "wall_s": t.get("wall_s"),
                "error": t.get("error"), "fail_case": t.get("fail_case"), "fail_msg": t.get("fail_msg"),
                "n_passed": t.get("n_passed"), "probes": _trim_probes(ev["probes"])}

    for i in range(0, len(todo), 120):
        part = todo[i:i + 120]
        res = parallel_map(work, part, workers=workers, desc=f"evaluate {i + len(part)}/{len(todo)}")
        good = [r for r in res if r and "key" in r]
        append_jsonl(EVAL_CACHE, good)
        for r in good:
            cache[r["key"]] = r
    return cache


def mechanical(task: str, code: str, ev: dict[str, Any]) -> dict[str, Any]:
    exp1_on_path()
    from labeller import ast_rules, runtime_rules

    rl, rwhy, _ = runtime_rules.label(task, ev["probes"])
    al, awhy, _ = ast_rules.label(code, task)
    return {"runtime_label": rl, "runtime_reason": rwhy, "ast_label": al, "ast_reason": awhy}


def _judge_cache() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for p in (EXP1 / "labeller" / "judge_cache.jsonl", JUDGE_CACHE):
        for r in read_jsonl(p):
            if r.get("label"):
                out[r["key"]] = r
    return out


async def _judge_async(items: list[dict[str, Any]], purpose: str, cap_usd: float) -> tuple[list, dict]:
    exp1_on_path()
    from labeller.judge import judge_prompt, parse_judge
    from openai import AsyncOpenAI

    client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"],
                         timeout=120.0, max_retries=0)
    cache = _judge_cache()
    sem = asyncio.Semaphore(12)
    stop: dict[str, Any] = {"stop": False}

    async def one(it: dict[str, Any]) -> dict[str, Any] | None:
        key = f"{JUDGE_MODEL}|{it['task']}|{sha256_text(it['code'])}"
        if key in cache:
            return cache[key]
        async with sem:
            if stop["stop"]:
                return None
            if spend_state()["total_usd"] >= cap_usd:
                stop.update(stop=True, reason=f"artifact cap {cap_usd} USD reached")
                return None
            for attempt in range(3):
                if stop["stop"]:
                    return None
                try:
                    resp = await client.chat.completions.create(
                        model=JUDGE_MODEL, messages=[{"role": "user", "content": judge_prompt(it["task"], it["code"])}],
                        temperature=0.0, max_tokens=300, extra_body={"usage": {"include": True}})
                    text = resp.choices[0].message.content or ""
                    usage = getattr(resp, "usage", None)
                    cost = 0.0
                    if usage is not None:
                        cost = float(getattr(usage, "cost", None) or (usage.model_extra or {}).get("cost", 0.0) or 0.0)
                    add_spend(purpose, cost)
                    parsed = parse_judge(text, it["task"])
                    logger.debug(f"judge -> {parsed['label']} ({cost:.5f} USD) {text[:100]!r}")
                    if parsed["label"] is None and attempt < 2:
                        continue
                    rec = {"key": key, "model": JUDGE_MODEL, "task": it["task"], "raw": text[:600], **parsed,
                           "cost": cost, "utc": utc_now()}
                    append_jsonl(JUDGE_CACHE, [rec])
                    cache[key] = rec
                    return rec
                except Exception as e:  # noqa: BLE001 - classified below
                    msg = str(e)
                    if BUDGET_MSG in msg or ("403" in msg and "budget" in msg.lower()):
                        stop.update(stop=True, reason="budget_403")
                        add_spend(purpose, 0.0, refused=True)
                        logger.error(f"OpenRouter budget refusal -- stopping the batch: {msg[:200]}")
                        return None
                    logger.warning(f"judge call failed (attempt {attempt + 1}): {msg[:200]}")
                    await asyncio.sleep(2 * (attempt + 1))
            return None

    res = await asyncio.gather(*[one(it) for it in items])
    await client.close()
    return list(res), stop


def judge_many(items: list[dict[str, Any]], purpose: str, cap_usd: float = OPENROUTER_CAP_USD) -> tuple[list, dict]:
    if not items:
        return [], {"stop": False}
    out, stop = asyncio.run(_judge_async(items, purpose, cap_usd))
    logger.info(f"judge [{purpose}]: {sum(r is not None for r in out)}/{len(out)} judged; total spend "
                f"{spend_state()['total_usd']:.4f} USD; stop={stop}")
    return out, stop


def code_part(text: str) -> str:
    """Thinking-on outputs: code is read only from the answer after </think>."""
    if "</think>" in text:
        return text.split("</think>", 1)[1]
    if "<think>" in text:
        return ""  # thinking never closed: no answer
    return text


def label_rows(rows: list[dict[str, Any]], purpose: str, use_judge: bool = True) -> list[dict[str, Any]]:
    """Full canonical labeller on rows with 'task' and 'text'; adds code, passed, label, labeller_source, ..."""
    exp1_on_path()
    from labeller.combine import combine, needs_judge
    from labeller.extract import extract_code

    out_rows, uniq = [], {}
    for r in rows:
        code, how = extract_code(code_part(r["text"]))
        rr = dict(r)
        rr["extract_method"] = how
        if code is None:
            rr["code"], rr["code_sha256"] = None, None
        else:
            rr["code"], rr["code_sha256"] = code, sha256_text(code)
            rr["eval_key"] = f"{r['task']}|{rr['code_sha256']}"
            uniq.setdefault(rr["eval_key"], {"task": r["task"], "code": code, "key": rr["eval_key"]})
        out_rows.append(rr)
    cache = evaluate_unique(list(uniq.values()))
    mech = {k: mechanical(u["task"], u["code"], cache[k]) for k, u in uniq.items()}
    need = [u for k, u in uniq.items() if needs_judge(mech[k]["runtime_label"], mech[k]["ast_label"])]
    judged, stop = judge_many(need, purpose) if (need and use_judge) else ([None] * len(need), {"stop": False})
    jmap = {u["key"]: j for u, j in zip(need, judged)}
    for rr in out_rows:
        if rr["code"] is None:
            rr.update({"label": NO_CODE, "labeller_source": "no_code", "passed": False, "runtime_label": None,
                       "ast_label": None, "judge_label": None, "test_error": "no_code"})
            continue
        ev, mk = cache[rr["eval_key"]], mech[rr["eval_key"]]
        j = jmap.get(rr["eval_key"])
        rr.update({"passed": ev["passed"], "test_error": ev["error"], "fail_case": ev["fail_case"],
                   "runtime_label": mk["runtime_label"], "ast_label": mk["ast_label"],
                   "judge_label": j["label"] if j else None})
        lab, src = combine(mk["runtime_label"], mk["ast_label"], j)
        if src == "fallback_no_judge" and stop.get("reason") == "budget_403":
            lab, src = "unresolved", "unresolved_budget"
        rr["label"], rr["labeller_source"] = lab, src
        rr.pop("eval_key", None)
    n_j = sum(1 for r in out_rows if r.get("labeller_source") == "judge")
    logger.info(f"labelled {len(out_rows)} rows ({len(uniq)} unique programs, {len(need)} needed the judge, "
                f"{n_j} rows judge-labelled)")
    return out_rows


# ---------------------------------------------------------------- commitment locator (exp3, unchanged)
_TOKZ = None


def _tok():
    global _TOKZ
    if _TOKZ is None:
        from transformers import AutoTokenizer

        from core import MODEL_HF

        _TOKZ = AutoTokenizer.from_pretrained(MODEL_HF)
    return _TOKZ


def commitment(task: str, gen_ids: list[int], text: str | None = None) -> dict[str, Any]:
    ev = load_module("exp3_evidence", EXP3 / "labeller" / "evidence.py")
    return ev.commitment(_tok(), EXP3_TASK[task], gen_ids, text)


def matched_mode(task: str, term: str | None) -> str | None:
    """Mechanism the first lexicon match points at (used to flag negated first mentions under a ban)."""
    if not term:
        return None
    t = term.lower()
    if task == "t1":
        if any(k in t for k in ("bfs", "breadth", "queue", "deque", "popleft")):
            return "bfs" if "bidirectional" not in t else "bibfs"
        if any(k in t for k in ("iddfs", "iterative deepening")):
            return "iddfs"
        if any(k in t for k in ("dfs", "depth", "stack", "recurs")):
            return "dfs"
        if any(k in t for k in ("a*", "a-star", "astar", "heuristic", "manhattan", "greedy", "best-first")):
            return "astar_gbfs"
        if any(k in t for k in ("heap", "priority", "dijkstra")):
            return "dijkstra"
        if "bidirectional" in t:
            return "bibfs"
    else:
        if any(k in t for k in ("bellman", "ford", "spfa")):
            return "bf_spfa"
        if any(k in t for k in ("floyd", "warshall")):
            return "floyd"
        if any(k in t for k in ("dial", "bucket")):
            return "dial"
        if "bidirectional" in t:
            return "bidijkstra"
        if any(k in t for k in ("dijkstra", "heap", "priority")):
            return "dijkstra"
        if any(k in t for k in ("queue", "deque")):
            return "bf_spfa"
    return None


def validate_locator(n: int = 20) -> dict[str, Any]:
    """Reproduce exp3 commit_idx on n exp3 pool rows (ban arm first, then baseline)."""
    pools = read_jsonl(EXP3_SRC_POOLS()) if EXP3_SRC_POOLS().exists() else []
    rows = [r for r in pools if r.get("arm") == "G2"][: n // 2] + [r for r in pools if r.get("arm") == "G1"][: n - n // 2]
    res = []
    for r in rows:
        task = "t1" if r["task"] == "T1" else "t2"
        c = commitment(task, r["gen_token_ids"], r["text"])
        res.append({"task": r["task"], "arm": r["arm"], "exp3_commit_idx": r["commit_idx"],
                    "ours": c["commit_idx"], "match": c["commit_idx"] == r["commit_idx"]})
    k = sum(x["match"] for x in res)
    out = {"n": len(res), "n_match": k, "pass": k >= int(0.9 * len(res)) if res else False, "rows": res}
    logger.info(f"commit locator validation: {k}/{len(res)} match exp3")
    return out


def EXP3_SRC_POOLS():
    from core import EXP3_SRC

    return EXP3_SRC / "generations" / "pools.jsonl"


# ---------------------------------------------------------------- the 'label' stage
def run_stage_label() -> None:
    """Label every generation file present under results/raw and (re)build results/samples.jsonl."""
    from core import Timer

    with Timer("label", gpu=False):
        files = {"c1": RAW / "c1_fresh_pool.jsonl", "crn": RAW / "e5_crn.jsonl", "gumbel": RAW / "e5_gumbel.jsonl",
                 "det": RAW / "e5_determinism.jsonl", "rep10": RAW / "e5_crn_repeat_stage10.jsonl",
                 "c2": RAW / "c2_base_traces.jsonl", "c4": RAW / "c4_completions.jsonl"}
        labelled: dict[str, list[dict[str, Any]]] = {}
        for k, p in files.items():
            rows = read_jsonl(p)
            if not rows:
                continue
            lab = label_rows(rows, purpose=f"judge_{k}")
            if k == "c1":
                for r in lab:
                    c = commitment(r["task"], r["gen_token_ids"], r["text"])
                    r.update({"commit_idx": c["commit_idx"], "evidence_term": c["evidence_term"],
                              "commit_idx_strict": c["commit_idx_strict"],
                              "evidence_term_strict": c["evidence_term_strict"],
                              "matched_mode": matched_mode(r["task"], c["evidence_term"])})
                    r["negated_first_mention"] = (r["matched_mode"] is not None and r["label"] not in
                                                  ("no_code", None) and r["matched_mode"] != r["label"])
            write_jsonl(RESULTS / f"labelled_{k}.jsonl", lab)
            labelled[k] = lab
        write_json(RESULTS / "locator_check.json", validate_locator(20))
        # continuations: early labels are computed in anchors_stage; code-reaching continuations get code labels
        conts = read_jsonl(RAW / "c3_continuations.jsonl")
        if conts:
            reach = [r for r in conts if r.get("reached_code")]
            lab = {r["continuation_id"]: r for r in label_rows(reach, purpose="judge_c3")} if reach else {}
            for r in conts:
                if r["continuation_id"] in lab:
                    r.update({k2: lab[r["continuation_id"]][k2] for k2 in ("label", "labeller_source", "passed",
                                                                           "code", "code_sha256")})
            write_jsonl(RESULTS / "labelled_c3.jsonl", conts)
        build_samples_jsonl()


SAMPLE_FIELDS = ("task", "condition", "template", "paraphrase_id", "sample_id", "seed", "model", "decoding", "label",
                 "labeller_source", "passed", "code_sha256", "code", "arm", "T", "coupling", "thinking", "trace_id",
                 "boundary_k", "continuation_id", "early_label", "commit_idx", "divergence_index")


def build_samples_jsonl() -> None:
    rows = []
    for k in ("c1", "crn", "gumbel", "det", "c2", "c4", "c3"):
        for r in read_jsonl(RESULTS / f"labelled_{k}.jsonl"):
            rec = {f: r.get(f) for f in SAMPLE_FIELDS}
            rec["paraphrase_id"] = r.get("paraphrase_id", r.get("template"))
            rec["sample_id"] = r.get("sample_id", r.get("crn_row", r.get("continuation_id", r.get("trace_id"))))
            rows.append(rec)
    write_jsonl(RESULTS / "samples.jsonl", rows)
    logger.info(f"samples.jsonl: {len(rows)} rows")
