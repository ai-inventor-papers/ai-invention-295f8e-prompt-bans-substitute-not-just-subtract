#!/usr/bin/env python3
"""Labelling (CPU) for every raw file of this artifact.

Instruct-model rows: the raw response goes to the iteration-4 label worker unchanged (src/label_worker_v4.py, a
verbatim copy of exp19's): exp8 suite for T1/T2, exp11 bench for the 13 bench tasks; runtime tracer primary, AST
second, blind judge only on disagreement.
Base-model rows: the program is first extracted with the ITER1 exp5 rules (src/vendor/iter1_exp5/extract.py, used
verbatim except that the entry function is solve for every task, which holds for all 15 tasks):
  chat   the first closed ```python (or bare ```) block that contains 'def solve'; else an unclosed fence; else
         'def solve' to the end; trim-to-parse (up to 40 trailing lines); keep only imports, defs, classes and
         assignments that do not call solve/print/input (module-level demo code can never crash a valid solution);
  plain  prompt text + completion, trim-to-parse, the same filter.
The extracted program is handed to the same label worker as a single ```python block, so both models share the
labellers, the hidden tests and the judge. 'other' and 'invalid' stay separate labels.

Usage: python src/labels5.py --follow   (runs until data/labels_stop.flag exists)
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
import time
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import DATA_DIR, append_jsonl, read_jsonl, setup_logging  # noqa: E402

RAW_FILES = ["base_raw.jsonl", "instr_raw.jsonl", "basehook_raw.jsonl", "engine_check_raw.jsonl"]
LABELS = DATA_DIR / "labels.jsonl"
STOP = DATA_DIR / "labels_stop.flag"

FENCE_RE = re.compile(r"```[ \t]*([A-Za-z0-9_+\-]*)[^\n]*\n(.*?)```", re.DOTALL)
OPEN_FENCE_RE = re.compile(r"```[ \t]*(python|py|python3)?[^\n]*\n", re.IGNORECASE)
KEEP = (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Assign, ast.AnnAssign)
BAD_CALLS = {"solve", "print", "input", "main", "exit", "quit"}


def _calls_bad(node: ast.AST) -> bool:
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
            if name in BAD_CALLS:
                return True
    return False


def _trim_parse(code: str, max_tries: int = 40) -> tuple[ast.Module | None, str, int]:
    lines = code.split("\n")
    for k in range(max_tries + 1):
        src = "\n".join(lines[: len(lines) - k]) if k else code
        if not src.strip():
            return None, "", k
        try:
            return ast.parse(src), src, k
        except (SyntaxError, ValueError, RecursionError, MemoryError):
            continue
    return None, "", max_tries


def _filter(mod: ast.Module) -> tuple[str | None, str]:
    body = []
    for n in mod.body:
        if isinstance(n, KEEP):
            if isinstance(n, (ast.Assign, ast.AnnAssign)) and _calls_bad(n):
                continue
            body.append(n)
    has_solve = any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "solve" for n in body)
    shim = ""
    if not has_solve:
        for n in body:
            if isinstance(n, ast.ClassDef) and any(isinstance(m, ast.FunctionDef) and m.name == "solve"
                                                   for m in n.body):
                shim = f"\n\ndef solve(*args):\n    return {n.name}().solve(*args)\n"
                break
        if not shim:
            return None, "no_solve"
    new = ast.Module(body=body, type_ignores=[])
    try:
        code = ast.unparse(new) + shim
    except Exception:  # noqa: BLE001 - ast.unparse can fail on exotic nodes
        return None, "unparse_failed"
    return code, ("ok_class_shim" if shim else "ok")


def extract_chat(text: str) -> tuple[str | None, dict[str, Any]]:
    info: dict[str, Any] = {"source": None, "n_trim": 0, "reason": ""}
    cand = None
    for m in FENCE_RE.finditer(text):
        lang = m.group(1).lower()
        if lang in ("python", "py", "python3", "") and "def solve" in m.group(2):
            cand, info["source"] = m.group(2), "closed_fence"
            break
    if cand is None:
        m = OPEN_FENCE_RE.search(text)
        if m and "def solve" in text[m.end():] and "```" not in text[m.end():]:
            cand, info["source"] = text[m.end():], "unclosed_fence"
        elif "def solve" in text:
            cand, info["source"] = text[text.index("def solve"):], "def_to_end"
    if cand is None:
        info["reason"] = "no_code"
        return None, info
    mod, _src, k = _trim_parse(cand)
    info["n_trim"] = k
    if mod is None:
        info["reason"] = "syntax"
        return None, info
    code, why = _filter(mod)
    info["reason"] = why
    return code, info


def extract_tf(prompt_text: str, completion: str) -> tuple[str | None, dict[str, Any]]:
    info: dict[str, Any] = {"source": "tf", "n_trim": 0, "reason": ""}
    mod, _src, k = _trim_parse(prompt_text + completion)
    info["n_trim"] = k
    if mod is None:
        info["reason"] = "syntax"
        return None, info
    code, why = _filter(mod)
    info["reason"] = why
    return code, info


_PLAIN: dict[str, str] = {}


def plain_prompt_text(task: str, w: str) -> str:
    if not _PLAIN:
        from prompts5 import load_prompts

        for r in load_prompts(("plain_tf",)):
            _PLAIN[f"{r['task']}|{r['w']}"] = r["user_text"]
    return _PLAIN[f"{task}|{w}"]


def normalise(r: dict[str, Any]) -> dict[str, Any]:
    """Base rows: replace the raw text by one ```python block holding the extracted program (or '' if none)."""
    r = dict(r)
    if not str(r.get("model", "")).endswith("-Base"):
        r["extract_info"] = {"source": "label_worker_v4 (instruct, raw response)"}
        return r
    if r.get("prompt_kind") == "plain_tf":
        code, info = extract_tf(plain_prompt_text(r["task"], r["template"]), r["text"])
    else:
        code, info = extract_chat(r["text"])
    r["raw_text"] = r["text"]
    r["text"] = ("```python\n" + code.rstrip() + "\n```") if code else ""
    r["extract_info"] = info
    return r


def label_batch(rows: list[dict[str, Any]], use_judge: bool = True) -> list[dict[str, Any]]:
    import label_worker_v4 as LW

    LW.N_WORKERS = 10
    norm = [normalise(r) for r in rows]
    have = [r for r in norm if r["text"]]
    out_have = LW.label_rows(have, use_judge) if have else []
    by_id = {o["sample_id"]: o for o in out_have}
    out = []
    for r in norm:
        o = by_id.get(r["sample_id"])
        if o is None:  # no extractable program
            o = {k: r.get(k) for k in LW.KEEP}
            o.update({"label": "invalid", "labeller_source": "no_code", "passed": False, "valid": False,
                      "runtime_label": None, "ast_label": None, "judge_label": None, "code": None,
                      "code_sha256": None, "is_default": False})
        for k in ("lambda", "site", "model_revision", "extract_info", "batch_B", "realised_disp", "P"):
            if k in r:
                o[k] = r[k]
        out.append(o)
    return out


def pending() -> list[dict[str, Any]]:
    done = {r["sample_id"] for r in read_jsonl(LABELS)}
    todo, seen = [], set()
    for f in RAW_FILES:
        for r in read_jsonl(DATA_DIR / f):
            sid = r["sample_id"]
            if sid in done or sid in seen:
                continue
            seen.add(sid)
            todo.append(r)
    return todo


def run_follow(chunk: int = 60, use_judge: bool = True) -> None:
    t0 = time.time()
    n_total = 0
    final = False
    while True:
        todo = pending()
        if todo:
            # decisive cells first: instruct confirmation rows, then the rest (F8)
            todo.sort(key=lambda r: (0 if r.get("block_id", "").startswith("S4") else 1))
            for i in range(0, len(todo), chunk):
                part = todo[i:i + chunk]
                tb = time.time()
                try:
                    out = label_batch(part, use_judge)
                except Exception as e:  # noqa: BLE001 - log and retry the chunk on the next pass
                    logger.exception(f"labelling chunk failed: {e}")
                    time.sleep(5)
                    break
                append_jsonl(LABELS, out)
                n_total += len(out)
                logger.info(f"labelled {len(out)} ({part[0]['task']}/{part[0]['arm']} ...) in {time.time() - tb:.1f}s;"
                            f" total {n_total}; backlog {len(todo) - i - len(part)}")
        else:
            if STOP.exists():
                if final:
                    break
                final = True
                time.sleep(3)
                continue
            time.sleep(8)
    logger.info(f"label worker finished: {n_total} rows in {time.time() - t0:.0f}s")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--follow", action="store_true")
    ap.add_argument("--no-judge", action="store_true")
    args = ap.parse_args()
    setup_logging("labels5")
    run_follow(use_judge=not args.no_judge)


if __name__ == "__main__":
    main()
