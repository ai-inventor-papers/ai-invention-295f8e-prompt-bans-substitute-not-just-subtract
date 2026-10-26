"""4c LONG-FORM NOVELTY: the request's two 2,000-word-rationale instructions (LF1, LF2), thinking off and on.

Thinking off: bf16 by the measured-throughput rule (committed with the prompts before the first sample), FP8 for
the remaining cells, plus the bf16-vs-FP8 cross-check on LF1-T2.  Thinking on (FP8, 16k thinking cap, two phases).
Every output: the LAST ```python block containing 'def solve' is the program (fallbacks: last fenced block with
'def solve', then any fenced block; else 'invalid'), the text before it is the rationale.
"""

from __future__ import annotations

import asyncio
import re
import sys
import time
from typing import Any

import aiohttp
from loguru import logger

from client import complete, generate_thinking
from commit import commit_json
from config import (DATA, LF_FORMAT, LF_PROMPTS, LOGS, MAX_TOKENS_LONG, PRED, RESULTS, THINK_CAP,
                    THINK_MAX_MODEL_LEN, THINK_STOP_PHRASE, append_jsonl, read_jsonl, seed_long_off, seed_long_on,
                    setup_logging, sha256_text, utc_now, write_json)
from label import label_programs
from prompts import chat_ids, ids_of, longform_prompt, tokenizer

FENCE = re.compile(r"```[ \t]*([A-Za-z0-9_+-]*)[ \t]*\n(.*?)```", re.S)
OPEN_FENCE = re.compile(r"```[ \t]*(?:python3?|py)?[ \t]*\n(.*)$", re.S)
LF_IDX = {"LF1": 0, "LF2": 1}
PROTOCOL = PRED / "longform_protocol.json"


def extract_last(text: str) -> tuple[str | None, str, str]:
    """-> (code, method, rationale)."""
    blocks = [(m.group(1).lower(), m.group(2), m.start()) for m in FENCE.finditer(text or "")]
    py = [b for b in blocks if b[0] in ("python", "py", "python3") and "def solve" in b[1]]
    if py:
        b = py[-1]
        return b[1], "last_python_block_with_solve", text[:b[2]]
    anyb = [b for b in blocks if "def solve" in b[1]]
    if anyb:
        b = anyb[-1]
        return b[1], "last_block_with_solve", text[:b[2]]
    m = OPEN_FENCE.search(text or "")
    if m and "def solve" in m.group(1):
        return m.group(1), "unterminated_block", text[:m.start()]
    if blocks:
        b = blocks[-1]
        return b[1], "any_block", text[:b[2]]
    return None, "no_code", text or ""


def words(s: str) -> int:
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-]*", s or ""))


def commit_protocol() -> dict[str, Any]:
    if PROTOCOL.exists():
        import json

        return json.loads(PROTOCOL.read_text())
    obj = {"utc": utc_now(), "prompts": LF_PROMPTS, "format_line": LF_FORMAT,
           "rendered_example_T2_LF1": longform_prompt("T2", "LF1"),
           "thinking_off": {"target_N_per_prompt": 50, "tasks": ["T1", "T2", "T03", "T04", "T06"],
                            "max_tokens": MAX_TOKENS_LONG, "max_model_len": 4608},
           "decision_rule": "Stage 10 on LF1-T2 in bf16 measures tokens/s and mean output length; if the projected bf16 "
                            "time for all 500 thinking-off samples <= 60 min, all thinking-off cells run in bf16 and FP8 "
                            "is used only for the cross-check copy; if > 60 min, bf16 runs LF1-T2 at N=50 (cross-check "
                            "reference) plus LF2-T2, LF1-T1 and LF2-T1 at N=25 each, and every remaining thinking-off "
                            "cell runs on Qwen3-8B-FP8 at N=50.",
           "cross_check": "LF1 thinking-off T2: bf16 N=50 vs FP8 N=50 (same seeds): label-composition JS against a "
                          "2,000-resample pooled-bootstrap null, pass-rate difference (Newcombe), mean output tokens, "
                          "rationale words, correct 'other' count.",
           "thinking_on": {"engine": "Qwen3-8B-FP8", "max_model_len": THINK_MAX_MODEL_LEN, "think_cap": THINK_CAP,
                           "answer_cap": 4096, "temperature": 1.0, "top_p": 1.0, "stop_phrase": THINK_STOP_PHRASE,
                           "floor": "T1 and T2 at N=10 per prompt; extend to 25 if time allows; bench tasks first to drop"},
           "extraction": "last ```python block containing 'def solve'; fallbacks: last fenced block with 'def solve', "
                         "unterminated block, any fenced block; else invalid"}
    commit_json(PROTOCOL, obj, "long-form prompts, bf16/FP8 decision rule, thinking protocol")
    return obj


def _row(kind: str, task: str, lf: str, thinking: bool, i: int, seed: int, ptxt: str, out: dict[str, Any],
         text: str, extra: dict[str, Any]) -> dict[str, Any]:
    code, how, rationale = extract_last(text)
    return {"model": "Qwen/Qwen3-8B" if kind == "bf16" else "Qwen/Qwen3-8B-FP8", "engine_dtype": kind, "task": task,
            "arm": "longform", "condition": f"{lf}|think_{'on' if thinking else 'off'}", "prompt_id": lf,
            "thinking": thinking, "template": lf, "sample_id": f"longform|{task}|{lf}|{'on' if thinking else 'off'}|"
            f"{kind}|{i}", "seed": seed, "prompt_sha256": sha256_text(ptxt), "code": code, "extract_method": how,
            "rationale_words": words(rationale), "rationale_text": rationale, "n_new_tokens": out.get("n_new_tokens"),
            "finish_reason": out.get("finish_reason"), **extra}


async def _run_off(kind: str, cells: list[tuple[str, str, int, int]], conc: int) -> list[dict[str, Any]]:
    sem = asyncio.Semaphore(conc)
    conn = aiohttp.TCPConnector(limit=conc + 4)
    async with aiohttp.ClientSession(connector=conn) as session:
        async def one(task, lf, i, seed):
            ptxt = longform_prompt(task, lf)
            async with sem:
                o = await complete(session, kind, chat_ids(ptxt), seed, MAX_TOKENS_LONG, timeout=7200)
            return _row(kind, task, lf, False, i, seed, ptxt, o, o["text"], {"thinking_tokens": 0,
                                                                              "thinking_complete": None}), o

        return await asyncio.gather(*[one(*c) for c in cells])


async def _run_on(kind: str, cells: list[tuple[str, str, int, int]], conc: int) -> list:
    sem = asyncio.Semaphore(conc)
    conn = aiohttp.TCPConnector(limit=conc + 4)
    nl2, stop_ids = ids_of("\n\n"), ids_of(THINK_STOP_PHRASE)
    async with aiohttp.ClientSession(connector=conn) as session:
        async def one(task, lf, i, seed):
            ptxt = longform_prompt(task, lf)
            async with sem:
                o = await generate_thinking(session, kind, chat_ids(ptxt, thinking=True), seed, THINK_CAP,
                                            THINK_MAX_MODEL_LEN, 4096, nl2, stop_ids)
            text = o["answer_text"]
            think_text = tokenizer().decode(o["think_ids"])
            extra = {"thinking_tokens": o["thinking_tokens"], "thinking_complete": o["thinking_complete"],
                     "answer_tokens": o.get("answer_tokens"), "finish_reason_a": o.get("finish_reason_a"),
                     "finish_reason_b": o.get("finish_reason_b"), "ended_in_thinking": o.get("ended_in_thinking")}
            out = {"n_new_tokens": o["thinking_tokens"] + (o.get("answer_tokens") or 0),
                   "finish_reason": o.get("finish_reason_b") or o.get("finish_reason_a"), "text": text,
                   "think_text": think_text}
            return _row(kind, task, lf, True, i, seed, ptxt, out, text, extra), out

        return await asyncio.gather(*[one(*c) for c in cells])


def run_cells(kind: str, cells: list[tuple[str, str, int, int]], thinking: bool, conc: int, tag: str) -> dict:
    t0 = time.time()
    res = asyncio.run((_run_on if thinking else _run_off)(kind, cells, conc))
    dt = time.time() - t0
    rows = [r for r, _ in res]
    labs = label_programs([{"task": r["task"], "code": r["code"], "extract_method": r["extract_method"]}
                           for r in rows])
    for r, lab, (_, o) in zip(rows, labs, res):
        r.update(label=lab["label"], labeller_source=lab["labeller_source"], passed=bool(lab.get("passed")),
                 runtime_label=lab.get("runtime_label"), ast_label=lab.get("ast_label"),
                 judge_label=lab.get("judge_label"), code_sha256=lab["code_sha256"])
        append_jsonl(DATA / "raw_longform.jsonl", [{"sample_id": r["sample_id"], "text": o.get("text"),
                                                    "think_text": o.get("think_text")}])
    append_jsonl(DATA / "samples_longform.jsonl", rows)
    ntok = sum((r.get("n_new_tokens") or 0) for r in rows)
    tim = {"tag": tag, "kind": kind, "thinking": thinking, "n": len(rows), "wall_s": round(dt, 1), "new_tokens": ntok,
           "tok_per_s": round(ntok / max(dt, 1e-6), 1), "mean_tokens": ntok / max(1, len(rows)), "utc": utc_now()}
    append_jsonl(LOGS / "timings.jsonl", [tim])
    logger.info(f"long-form {tag}: {tim}")
    return tim


def cells_for(task: str, lf: str, n: int, start: int = 0, thinking: bool = False) -> list[tuple[str, str, int, int]]:
    f = seed_long_on if thinking else seed_long_off
    return [(task, lf, i, f(task, LF_IDX[lf], i)) for i in range(start, start + n)]


def done_count(task: str, lf: str, thinking: bool, kind: str) -> int:
    return sum(1 for r in read_jsonl(DATA / "samples_longform.jsonl") if r["task"] == task and r["prompt_id"] == lf
               and r["thinking"] == thinking and r["engine_dtype"] == kind)


def phase_bf16() -> None:
    """Thinking-off long-form in bf16 (runs concurrently with phase A on the same server)."""
    commit_protocol()
    if done_count("T2", "LF1", False, "bf16") == 0:
        tim = run_cells("bf16", cells_for("T2", "LF1", 10), False, 10, "stage10_LF1_T2_bf16")
        proj_min = 500 * tim["mean_tokens"] / max(tim["tok_per_s"], 1e-6) / 60
        branch = "all_bf16" if proj_min <= 60 else "split"
        write_json(RESULTS / "longform_branch.json", {"stage10": tim, "projected_bf16_minutes_all_500": proj_min,
                                                      "branch": branch, "utc": utc_now(),
                                                      "note": "measured while sharing the GPU with phase A"})
    import json

    br = json.loads((RESULTS / "longform_branch.json").read_text())
    if br["branch"] == "all_bf16":
        plan = [("T2", "LF1", 50), ("T2", "LF2", 50), ("T1", "LF1", 50), ("T1", "LF2", 50)]
    else:
        plan = [("T2", "LF1", 50), ("T2", "LF2", 25), ("T1", "LF1", 25), ("T1", "LF2", 25)]
    cells = []
    for task, lf, n in plan:
        k = done_count(task, lf, False, "bf16")
        if k < n:
            cells += cells_for(task, lf, n - k, start=k)
    if cells:
        run_cells("bf16", cells, False, 16, "bf16_main")


def phase_fp8_off(n_bench: int) -> None:
    commit_protocol()
    import json

    br = json.loads((RESULTS / "longform_branch.json").read_text())
    cells = []
    k = done_count("T2", "LF1", False, "fp8")
    if k < 50:
        cells += cells_for("T2", "LF1", 50 - k, start=k)   # cross-check copy (same seeds as bf16)
    if br["branch"] == "all_bf16":
        bench = []
    else:
        bench = [(t, lf, n_bench) for t in ("T03", "T04", "T06") for lf in ("LF1", "LF2")]
    for task, lf, n in bench:
        k = done_count(task, lf, False, "fp8")
        if k < n:
            cells += cells_for(task, lf, n - k, start=k)
    if cells:
        run_cells("fp8", cells, False, 20, "fp8_off")


def phase_fp8_on(spec: str, conc: int = 10) -> None:
    """spec: 'T1:10,T2:10' (N per prompt) or explicit index ranges 'T1:10-25' (indices 10..24, never re-run)."""
    commit_protocol()
    cells = []
    for part in spec.split(","):
        task, n = part.split(":")
        for lf in ("LF1", "LF2"):
            if "-" in n:
                a, b = (int(x) for x in n.split("-"))
                have = {int(r["sample_id"].rsplit("|", 1)[1]) for r in read_jsonl(DATA / "samples_longform.jsonl")
                        if r["task"] == task and r["prompt_id"] == lf and r["thinking"] and r["engine_dtype"] == "fp8"}
                cells += [c for c in cells_for(task, lf, b - a, start=a, thinking=True) if c[2] not in have]
                continue
            k = done_count(task, lf, True, "fp8")
            if k < int(n):
                cells += cells_for(task, lf, int(n) - k, start=k, thinking=True)
    if cells:
        run_cells("fp8", cells, True, conc, f"fp8_on_{spec}")


if __name__ == "__main__":
    setup_logging(f"longform_{sys.argv[1]}")
    if sys.argv[1] == "bf16":
        phase_bf16()
    elif sys.argv[1] == "fp8_off":
        phase_fp8_off(int(sys.argv[2]) if len(sys.argv) > 2 else 50)
    elif sys.argv[1] == "fp8_on":
        phase_fp8_on(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 10)
