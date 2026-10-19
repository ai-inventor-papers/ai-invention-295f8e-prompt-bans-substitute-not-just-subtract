#!/usr/bin/env python3
"""Labelling pipeline: extract code -> hidden tests -> runtime tracer -> AST rules (CPU process pool, cached per
unique program) -> blind judge on every runtime/AST disagreement -> final label per sample (results/samples.jsonl).

Final label: runtime == AST (both non-None) -> that label ('runtime+ast'); otherwise the judge's label ('judge').
No code / does not parse -> 'unparseable' (passed False). Judge cap exhausted -> 'unresolved'.
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import hashlib
import json
import multiprocessing as mp
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (LABELS, RAW, RESULTS, append_jsonl, detect_cpus, read_jsonl, setup_logging,  # noqa: E402
                    write_json)

GEN_ARMS = ["A0", "A1", "A2", "A3", "A4s2", "A5", "A6a", "A6b", "A6c", "A6d"]
CODE_LABELS = LABELS / "code_labels.jsonl"
JUDGE_FILE = LABELS / "judge.jsonl"
SAMPLES = RESULTS / "samples.jsonl"
FENCE = re.compile(r"```[ \t]*([A-Za-z0-9_+-]*)[^\n]*\n(.*?)(?:```|\Z)", re.S)
SOLVE_DEF = re.compile(r"^\s*def\s+solve\s*\(", re.M)


def _parses(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except (SyntaxError, ValueError):
        return False


def extract_code(text: str) -> tuple[str | None, str]:
    """Last ```python block that defines solve; else the first ```python block; else the whole text if it parses."""
    if "</think>" in text:
        text = text.split("</think>")[-1]
    blocks = [(lang.lower(), body) for lang, body in FENCE.findall(text)]
    py = [b for lang, b in blocks if lang in ("python", "py", "python3")]
    with_solve = [b for b in py if SOLVE_DEF.search(b)]
    if with_solve:
        return with_solve[-1], "last_python_block_with_solve"
    if py:
        return py[0], "first_python_block"
    untagged = [b for lang, b in blocks if SOLVE_DEF.search(b)]
    if untagged:
        return untagged[-1], "untagged_block_with_solve"
    if _parses(text) and SOLVE_DEF.search(text):
        return text, "whole_text"
    return None, "no_code"


def code_sha(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def label_code(task: str, code: str) -> dict:
    """Worker: tests + runtime tracer + AST rules for one program."""
    from harness.run_tests import run_program_tests
    from labeller.ast_rules import ast_label
    from labeller.tracer import runtime_label
    t0 = time.time()
    if not _parses(code):
        return dict(task=task, sha=code_sha(code), parses=False, tests=dict(passed=False, n_cases_passed=0,
                                                                              first_fail={"reason": "syntax"}),
                    runtime_label=None, runtime_rule="unparseable", ast_label=None, ast_rule="unparseable",
                    secs=0.0)
    tests = run_program_tests(code, task)
    rt = runtime_label(code, task)
    al, arule = ast_label(code, task)
    feats = rt.get("features", {})
    compact = feats.get("G1", feats) if task == "T1" else feats
    keep = {k: compact.get(k) for k in list(compact)[:40] if not isinstance(compact.get(k), (list, dict))}
    return dict(task=task, sha=code_sha(code), parses=True, tests=tests, runtime_label=rt["label"],
                runtime_rule=rt["rule"], runtime_features=keep, ast_label=al, ast_rule=arule,
                secs=round(time.time() - t0, 2))


def relabel_code(task: str, code: str, cached: dict) -> dict:
    """Worker for a signature revision: rerun tracer + AST rules, keep the cached hidden-test result."""
    from labeller.ast_rules import ast_label
    from labeller.tracer import runtime_label
    t0 = time.time()
    if not cached.get("parses", True):
        return cached
    rt = runtime_label(code, task)
    al, arule = ast_label(code, task)
    feats = rt.get("features", {})
    compact = feats.get("G1", feats) if task == "T1" else feats
    keep = {k: compact.get(k) for k in list(compact)[:40] if not isinstance(compact.get(k), (list, dict))}
    return dict(cached, runtime_label=rt["label"], runtime_rule=rt["rule"], runtime_features=keep, ast_label=al,
                ast_rule=arule, secs=round(time.time() - t0, 2), revision=REVISION)


REVISION = 2


def run_relabel(rows: list[dict], workers: int, logger) -> dict[tuple[str, str], dict]:
    old = {(r["task"], r["sha"]): r for r in read_jsonl(CODE_LABELS)}
    codes = {}
    for r in rows:
        c, _ = extract_code(r.get("answer_text") or r.get("text") or "")
        if c is not None:
            codes[(r["task"], code_sha(c))] = c
    backup = LABELS / f"code_labels_rev{REVISION - 1}.jsonl"
    if not backup.exists():
        backup.write_text(CODE_LABELS.read_text())
    new: dict = {}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as pool:
        futs = {pool.submit(relabel_code, k[0], codes[k], old[k]): k for k in old if k in codes}
        for i, f in enumerate(as_completed(futs)):
            k = futs[f]
            try:
                new[k] = f.result()
            except Exception as e:  # noqa: BLE001
                new[k] = dict(old[k], runtime_label=None, runtime_rule=f"worker_error:{e}", revision=REVISION)
            if (i + 1) % 500 == 0:
                logger.info(f"relabelled {i + 1}/{len(futs)} in {time.time() - t0:.0f}s")
    CODE_LABELS.write_text("".join(json.dumps(v) + "\n" for v in new.values()))
    logger.info(f"revision {REVISION}: relabelled {len(new)} programs in {time.time() - t0:.0f}s")
    return new


def load_raw() -> list[dict]:
    rows = []
    for arm in GEN_ARMS:
        for r in read_jsonl(RAW / f"{arm}.jsonl"):
            rows.append(r)
    return rows


def run_code_labels(rows: list[dict], workers: int, logger) -> dict[tuple[str, str], dict]:
    done = {(r["task"], r["sha"]): r for r in read_jsonl(CODE_LABELS)}
    todo: dict[tuple[str, str], str] = {}
    for r in rows:
        code, _ = extract_code(r.get("answer_text") or r.get("text") or "")
        if code is None:
            continue
        k = (r["task"], code_sha(code))
        if k not in done and k not in todo:
            todo[k] = code
    logger.info(f"unique programs: {len(done) + len(todo)} (cached {len(done)}, to label {len(todo)}) "
                f"with {workers} workers")
    t0 = time.time()
    n = 0
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as pool:
        futs = {pool.submit(label_code, k[0], c): k for k, c in todo.items()}
        buf = []
        for f in as_completed(futs):
            k = futs[f]
            try:
                res = f.result()
            except Exception as e:  # noqa: BLE001 - one bad program must not stop the pool
                res = dict(task=k[0], sha=k[1], parses=True, tests=dict(passed=False, n_cases_passed=0,
                                                                          first_fail={"reason": f"worker:{e}"}),
                           runtime_label=None, runtime_rule=f"worker_error:{type(e).__name__}", ast_label=None,
                           ast_rule="worker_error")
            done[k] = res
            buf.append(res)
            n += 1
            if len(buf) >= 50:
                append_jsonl(CODE_LABELS, buf)
                buf = []
                el = time.time() - t0
                logger.info(f"labelled {n}/{len(todo)} in {el:.0f}s ({el / n:.2f}s/program wall); "
                            f"eta {(len(todo) - n) * el / n:.0f}s")
        if buf:
            append_jsonl(CODE_LABELS, buf)
    return done


def run_judge(code_labels: dict, codes: dict, cap_usd: float, logger) -> dict:
    from labeller.judge import PRIMARY_JUDGE, Budget, judge_many
    have = {(r["task"], r["sha"]): r for r in read_jsonl(JUDGE_FILE) if r.get("label")}
    need = []
    for k, cl in code_labels.items():
        if not cl.get("parses", True):
            continue
        rl, al = cl.get("runtime_label"), cl.get("ast_label")
        if rl is not None and rl == al:
            continue
        if k in have:
            continue
        need.append(dict(task=k[0], sha=k[1], code=codes[k], kind="judge"))
    spent_before = sum(r.get("cost", 0.0) for r in read_jsonl(JUDGE_FILE))
    budget = Budget(max(0.0, cap_usd - spent_before))
    logger.info(f"judge: {len(need)} programs need the judge (cached {len(have)}); remaining cap ${budget.cap:.3f}")
    if need:
        out = asyncio.run(judge_many(need, PRIMARY_JUDGE, budget))
        good = [o for o in out if o.get("label")]
        append_jsonl(JUDGE_FILE, good)
        for o in good:
            have[(o["task"], o["sha"])] = o
        logger.info(f"judge: {len(good)} labelled, {len(out) - len(good)} errors, spent ${budget.spent:.4f}, "
                    f"stopped={budget.stopped} {budget.stop_reason or ''}")
    return have


def assemble(rows: list[dict], code_labels: dict, judge: dict) -> list[dict]:
    out = []
    for r in rows:
        text = r.get("answer_text") or r.get("text") or ""
        code, rule = extract_code(text)
        dec = r["decoding"]
        base = dict(key=r["key"], task=r["task"], condition=r["condition"], arm=r["arm"],
                    paraphrase_id=r["paraphrase_id"], sample_id=r["sample_id"], model=r.get("model"),
                    decoding=dict(T=dec["T"], sampler=dec["sampler"], top_k=dec["top_k"], top_p=dec["top_p"],
                                  thinking=dec["thinking"], max_tokens=dec["max_tokens"], seed=dec["seed"]),
                    n_output_tokens=r.get("n_output_tokens"), finish_reason=r.get("finish_reason"),
                    truncated_thinking=r.get("truncated_thinking"), two_pass=r.get("two_pass"),
                    n_thinking_tokens=r.get("n_thinking_tokens"),
                    thinking_text=r.get("thinking_text") if dec["thinking"] else None,
                    extraction_rule=rule)
        for g in ("gts_items", "gts_k", "gts_item", "gts_n_items"):
            if g in r:
                base[g] = r[g]
        if code is None:
            out.append(dict(base, label="unparseable", labeller_source="none", runtime_label=None, ast_label=None,
                            judge_label=None, judge_rationale=None, passed=False, n_cases_passed=0, wall_s=0.0,
                            code_sha256=None, code=None))
            continue
        k = (r["task"], code_sha(code))
        cl = code_labels.get(k, {})
        if not cl.get("parses", True):
            out.append(dict(base, label="unparseable", labeller_source="none", runtime_label=None, ast_label=None,
                            judge_label=None, judge_rationale=None, passed=False, n_cases_passed=0, wall_s=0.0,
                            code_sha256=k[1], code=code))
            continue
        rl, al = cl.get("runtime_label"), cl.get("ast_label")
        j = judge.get(k)
        if rl is not None and rl == al:
            label, src = rl, "runtime+ast"
        elif j is not None:
            label, src = j["label"], "judge"
        else:
            label, src = "unresolved", "unresolved"
        t = cl.get("tests", {})
        out.append(dict(base, label=label, labeller_source=src, runtime_label=rl, runtime_rule=cl.get("runtime_rule"),
                        ast_label=al, ast_rule=cl.get("ast_rule"),
                        judge_label=j["label"] if j else None, judge_rationale=j.get("rationale") if j else None,
                        passed=bool(t.get("passed")), n_cases_passed=t.get("n_cases_passed", 0),
                        first_fail=t.get("first_fail"), wall_s=t.get("wall_s", 0.0),
                        lenient_io=t.get("lenient_io", False), code_sha256=k[1], code=code))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=max(1, detect_cpus() - 2))
    ap.add_argument("--judge-cap", type=float, default=1.0)
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--relabel", action="store_true", help="rerun tracer+AST after a signature revision")
    args = ap.parse_args()
    logger = setup_logging("label")
    rows = load_raw()
    logger.info(f"loaded {len(rows)} generated samples from {GEN_ARMS}")
    if args.relabel:
        run_relabel(rows, args.workers, logger)
    code_labels = run_code_labels(rows, args.workers, logger)
    codes = {}
    for r in rows:
        c, _ = extract_code(r.get("answer_text") or r.get("text") or "")
        if c is not None:
            codes[(r["task"], code_sha(c))] = c
    judge = {} if args.no_judge else run_judge(code_labels, codes, args.judge_cap, logger)
    if args.no_judge:
        judge = {(r["task"], r["sha"]): r for r in read_jsonl(JUDGE_FILE) if r.get("label")}
    samples = assemble(rows, code_labels, judge)
    SAMPLES.write_text("".join(json.dumps(s) + "\n" for s in samples))
    from collections import Counter
    summ = Counter((s["task"], s["labeller_source"]) for s in samples)
    write_json(LABELS / "label_summary.json", {f"{k[0]}|{k[1]}": v for k, v in summ.items()})
    logger.info(f"wrote {len(samples)} samples; sources {dict(summ)}")


if __name__ == "__main__":
    main()
