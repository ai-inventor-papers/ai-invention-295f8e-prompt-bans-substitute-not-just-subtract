#!/usr/bin/env python3
"""Label worker (CPU): follows data/samples_<UNIT>.jsonl and appends one label row per sample to
data/labels_<UNIT>.jsonl, using the frozen labellers of earlier iterations, unchanged:

- T10 (connected components): the exp11 bench labeller (inputs/exp11/bench: hidden tests, AST rules, runtime trace).
  Label = runtime label when runtime == AST or AST is 'unknown'; a disagreement keeps the runtime label and is flagged
  'runtime_unjudged' (the blind judge is not called in this artifact: OpenRouter is reserved for the novelty audit).
- GRID (T1 grid path): the exp8 canonical suite (inputs/exp38/inputs/iter6_gemma/inputs/exp8/suite: hidden tests +
  runtime probes -> runtime label, AST label, combine()); an unresolved disagreement is 'disputed' (iteration-7 rule).
Program = the first fenced python block (T10: bench extractor; GRID: the first block containing 'def solve').

Usage: python src/label8.py --unit T10 [--follow results/gen_done_T10.flag]
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger

from cfg8 import DATA, INPUTS, append_jsonl, read_jsonl, setup_logging, sha256_text

BLOCK_RE = re.compile(r"```[a-zA-Z0-9_+-]*[ \t]*\n(.*?)(?:```|\Z)", re.S)
SOLVE_RE = re.compile(r"\bdef solve\s*\(")
_CACHE: dict[str, dict[str, Any]] = {}


def setup_paths(unit: str) -> None:
    if unit == "T10":
        p = str(INPUTS / "exp11")
    else:
        p = str(INPUTS / "exp38" / "inputs" / "iter6_gemma" / "inputs" / "exp8" / "suite")
        sys.path.insert(0, str(INPUTS / "exp38" / "inputs" / "iter6_gemma" / "inputs" / "exp11"))
    if p not in sys.path:
        sys.path.insert(0, p)


# ------------------------------------------------------------------------------------------------ T10
_CASES: list[dict[str, Any]] = []


def label_t10(text: str) -> dict[str, Any]:
    from bench.common.catalogue import TASKS
    from bench.common.harness import extract_code
    from bench.common.labeling import label_one
    from bench.common.testgen import read_tests

    if not _CASES:
        _CASES.extend(read_tests(INPUTS / "exp11" / "bench" / TASKS["T10"]["task_id"] / "tests.jsonl"))
    code = extract_code(text)
    ck = "T10|" + sha256_text(code or "")
    if ck in _CACHE:
        return dict(_CACHE[ck])
    row = {"sample_id": ck, "task": "T10", "condition": "iter8", "mode": None, "paraphrase_id": None, "round": None,
           "attempt_idx": None, "seed": 0, "finish_reason": "stop", "text": text}
    lab = label_one(row, _CASES)
    lab.pop("trace", None)
    if not lab.get("valid"):
        out = {"label": "invalid", "labeller_source": "extraction"}
    elif lab["runtime_label"] == "unknown":
        out = {"label": lab["ast_label"] if lab["ast_label"] != "unknown" else "other",
               "labeller_source": "ast(runtime_unknown)"}
    elif lab["ast_label"] in ("unknown", lab["runtime_label"]):
        out = {"label": lab["runtime_label"], "labeller_source": "runtime+ast" if lab["ast_label"] != "unknown"
               else "runtime(ast_unknown)"}
    else:
        out = {"label": lab["runtime_label"], "labeller_source": "runtime_unjudged"}
    out.update({"passed": bool(lab.get("passed")) and bool(lab.get("valid")), "valid": bool(lab.get("valid")),
                "runtime_label": lab.get("runtime_label"), "ast_label": lab.get("ast_label"),
                "n_pass": lab.get("n_pass"), "n_cases": lab.get("n_cases"), "code": code})
    _CACHE[ck] = out
    return dict(out)


# ------------------------------------------------------------------------------------------------ GRID
def extract_grid(text: str) -> str | None:
    for m in BLOCK_RE.finditer(text):
        b = m.group(1)
        if SOLVE_RE.search(b) and b.strip():
            return b.rstrip() + "\n"
    from labeller.extract import extract_code as suite_extract

    c2, _ = suite_extract(text)
    return c2 or None


def label_grid(text: str) -> dict[str, Any]:
    from labeller import ast_rules, runtime_rules
    from labeller.combine import combine, needs_judge
    from tasks.harness import evaluate_program

    code = extract_grid(text)
    if not code:
        return {"label": "invalid", "labeller_source": "no_code", "passed": False, "valid": False, "code": None,
                "runtime_label": None, "ast_label": None}
    ck = "T1|" + sha256_text(code)
    if ck in _CACHE:
        return dict(_CACHE[ck])
    try:
        ev = evaluate_program("t1", code)
    except Exception as e:  # noqa: BLE001 - a program that breaks the harness counts as failing
        logger.warning(f"suite harness error: {type(e).__name__}")
        ev = {"tests": {"passed": False}, "probes": {"error": "crash"}}
    rl, _, _ = runtime_rules.label("t1", ev["probes"])
    al, _, _ = ast_rules.label(code, "t1")
    if needs_judge(rl, al):
        fb, _ = combine(rl, al, None)
        lab, src = "disputed", "judge_not_called"
    else:
        lab, src = combine(rl, al, None)
        fb = lab
    out = {"label": lab, "labeller_source": src, "fallback_label": fb, "passed": bool(ev["tests"].get("passed")),
           "valid": True, "runtime_label": rl, "ast_label": al, "code": code}
    _CACHE[ck] = out
    return dict(out)


def label_text(unit: str, text: str) -> dict[str, Any]:
    return label_t10(text) if unit == "T10" else label_grid(text)


KEEP = ("sample_id", "unit", "cell", "arm", "site", "slot", "pair_id", "source_key", "base_key", "class_src",
        "class_base", "target_class", "rank_k", "fit", "fit_seed", "layer", "edit", "direction_seed", "n_new_tokens",
        "finish_reason", "prefill", "stage")


def run(unit: str, follow: Path | None, workers: int) -> None:
    raw = DATA / f"samples_{unit}.jsonl"
    out = DATA / f"labels_{unit}.jsonl"
    done = {r["sample_id"] for r in read_jsonl(out)}
    idle = 0
    with ThreadPoolExecutor(workers) as ex:
        while True:
            done |= {r["sample_id"] for r in read_jsonl(out)}
            rows = [r for r in read_jsonl(raw) if r["sample_id"] not in done]
            if rows:
                idle = 0
                for i in range(0, len(rows), 48):
                    chunk = rows[i:i + 48]
                    labs = list(ex.map(lambda r: label_text(unit, r["text"]), chunk))
                    outs = []
                    for r, l in zip(chunk, labs):
                        o = {k: r.get(k) for k in KEEP}
                        o.update({k: v for k, v in l.items() if k != "code"})
                        o["code_sha256"] = sha256_text(l.get("code") or "")
                        o["code"] = l.get("code")
                        outs.append(o)
                        done.add(r["sample_id"])
                    append_jsonl(out, outs)
                    logger.info(f"{unit}: labelled {len(done)}")
            elif follow is None or follow.exists():
                if follow is None or idle >= 1:
                    break
                idle += 1
            else:
                time.sleep(10)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit", required=True)
    ap.add_argument("--follow", default=None)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    setup_logging(f"label8_{a.unit}")
    setup_paths(a.unit)
    run(a.unit, Path(a.follow) if a.follow else None, a.workers)


if __name__ == "__main__":
    main()
