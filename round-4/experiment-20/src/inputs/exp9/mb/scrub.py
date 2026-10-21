#!/usr/bin/env python3
"""S4 SCRUB: name-scrub forced programs before scoring.

Positional rewrite driven by `tokenize`: NAME tokens containing an alias-lexicon string become consistent neutral
identifiers (find_path, search, explore, helper_1, ...); in COMMENT and docstring tokens alias words are deleted, and a
comment left empty is dropped. Every scrubbed program is verified: it compiles, has the same canonical pass/fail and the
same runtime label, and no alias remains; a failing program is replaced by the next labelled one.
"""

from __future__ import annotations

import ast
import io
import math
import re
import tokenize
from typing import Any

from loguru import logger

from common import ALIASES, M_MAX, sha256_text

NEUTRAL_POOL = ["find_path", "search", "explore", "walk", "route", "traverse"] + [f"helper_{i}" for i in range(1, 40)]
_ALL_ALIASES = sorted({a for fam in ALIASES.values() for a in fam}, key=len, reverse=True)
_NAME_ALIASES = [a.replace("-", "_").replace(" ", "_") for a in _ALL_ALIASES if "*" not in a]
_NAME_ALIASES = sorted(set(_NAME_ALIASES) | {a.replace("_", "") for a in _NAME_ALIASES}, key=len, reverse=True)


def _text_alias_re() -> re.Pattern:
    parts = []
    for a in _ALL_ALIASES:
        esc = re.escape(a).replace(r"\ ", r"[\s_-]?").replace(r"\-", r"[\s_-]?")
        if a.endswith("*"):
            parts.append(r"(?<![A-Za-z0-9_])" + esc)
        else:
            parts.append(esc)
    return re.compile("(" + "|".join(parts) + ")", re.I)


TEXT_ALIAS_RE = _text_alias_re()


def name_has_alias(name: str) -> bool:
    low = name.lower()
    return any(a in low for a in _NAME_ALIASES)


def text_has_alias(text: str) -> bool:
    return bool(TEXT_ALIAS_RE.search(text))


def _docstring_starts(tree: ast.AST) -> set[tuple[int, int]]:
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body:
            b = n.body[0]
            if isinstance(b, ast.Expr) and isinstance(b.value, ast.Constant) and isinstance(b.value.value, str):
                out.add((b.lineno, b.col_offset))
    return out


def _clean_text(s: str) -> str:
    s = TEXT_ALIAS_RE.sub("", s)
    s = re.sub(r"\(\s*\)", "", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s


def scrub_code(code: str) -> tuple[str, dict[str, str]]:
    """Returns (scrubbed code, identifier mapping). Raises SyntaxError / tokenize.TokenError on bad input."""
    tree = ast.parse(code)
    doc_starts = _docstring_starts(tree)
    idents = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | \
        {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef))} | \
        {a.arg for n in ast.walk(tree) if isinstance(n, ast.arguments) for a in n.args + n.kwonlyargs}
    pool = [p for p in NEUTRAL_POOL if p not in idents]
    mapping: dict[str, str] = {}
    lines = code.splitlines(keepends=True)
    offs = [0]
    for ln in lines:
        offs.append(offs[-1] + len(ln))

    def off(rc: tuple[int, int]) -> int:
        return offs[rc[0] - 1] + rc[1]

    edits: list[tuple[int, int, str]] = []
    toks = list(tokenize.generate_tokens(io.StringIO(code).readline))
    for t in toks:
        if t.type == tokenize.NAME and name_has_alias(t.string):
            if t.string not in mapping:
                mapping[t.string] = pool.pop(0)
            edits.append((off(t.start), off(t.end), mapping[t.string]))
        elif t.type == tokenize.COMMENT and text_has_alias(t.string):
            body = _clean_text(t.string[1:])
            new = "#" + body if re.search(r"[A-Za-z0-9]", body) else ""
            edits.append((off(t.start), off(t.end), new))
        elif t.type == tokenize.STRING and (t.start[0], t.start[1]) in doc_starts and text_has_alias(t.string):
            edits.append((off(t.start), off(t.end), _clean_text(t.string)))
    out = code
    for a, b, new in sorted(edits, reverse=True):
        out = out[:a] + new + out[b:]
    out = "\n".join(ln.rstrip() if ln.strip() else "" for ln in out.split("\n"))
    compile(out, "<scrubbed>", "exec")
    return out, mapping


def residual_alias(code: str) -> list[str]:
    hits = []
    for t in tokenize.generate_tokens(io.StringIO(code).readline):
        if t.type == tokenize.NAME and name_has_alias(t.string):
            hits.append(t.string)
        elif t.type in (tokenize.COMMENT, tokenize.STRING) and text_has_alias(t.string):
            hits.append(t.string[:40])
    return hits


def fence_of(text: str) -> str:
    m = re.search(r"```[A-Za-z0-9_+-]*", text)
    return m.group(0) if m else "```python"


def scored_response(raw_text: str, code: str) -> str:
    """'```python' + newline + code + newline + '```' with the fence matching the raw generation; no prose, no EOS."""
    return fence_of(raw_text) + "\n" + code.rstrip("\n") + "\n```"


def scrub_program_rows(psets: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """psets: 'task:key' -> labelled forced rows (label == key) in program order. Returns per algorithm the scrubbed
    program set (M = min(30, n_valid)) with halves, plus replacement counts."""
    from mb.label import evaluate_unique, mechanical_labels

    cand_items = {}
    prepared: dict[str, list[dict[str, Any]]] = {}
    for k, rows in psets.items():
        task = k.split(":")[0]
        prepared[k] = []
        for r in rows:
            try:
                sc, mp = scrub_code(r["code"])
                err = None
            except (SyntaxError, tokenize.TokenError, IndentationError, ValueError) as e:
                sc, mp, err = None, {}, f"{type(e).__name__}: {str(e)[:80]}"
            item = {"row": r, "scrubbed": sc, "mapping": mp, "error": err}
            if sc is not None:
                key = f"{task}|{sha256_text(sc)}"
                item["skey"] = key
                cand_items[key] = {"task": task, "code": sc, "key": key}
            prepared[k].append(item)
    cache = evaluate_unique(list(cand_items.values()))
    out: dict[str, Any] = {}
    for k, items in prepared.items():
        task, alg = k.split(":")
        progs, n_rep, fails = [], 0, []
        for it in items:
            if len(progs) >= M_MAX:
                break
            r = it["row"]
            ok, why = True, "ok"
            if it["scrubbed"] is None:
                ok, why = False, it["error"]
            else:
                ev = cache[it["skey"]]
                mk = mechanical_labels(task, it["scrubbed"], ev)
                if bool(ev["passed"]) != bool(r["passed"]):
                    ok, why = False, "pass/fail changed"
                elif mk["runtime_label"] != r["runtime_label"]:
                    ok, why = False, f"runtime label changed {r['runtime_label']} -> {mk['runtime_label']}"
                elif residual_alias(it["scrubbed"]):
                    ok, why = False, f"alias remains {residual_alias(it['scrubbed'])[:2]}"
            if not ok:
                n_rep += 1
                fails.append({"code_sha256": r["code_sha256"], "why": why})
                continue
            progs.append({"uid": f"{task}|{alg}|{r['code_sha256'][:16]}", "task": task, "algorithm": alg,
                          "condition": r["condition"], "paraphrase_id": r["paraphrase_id"],
                          "sample_index": r["sample_index"], "stage": r["stage"], "passed": r["passed"],
                          "code_sha256": r["code_sha256"], "scrubbed_code": it["scrubbed"],
                          "scrubbed_sha256": sha256_text(it["scrubbed"]), "rename_map": it["mapping"],
                          "response": scored_response(r["text"], it["scrubbed"]), "raw_text": r["text"],
                          "token_ids": r.get("token_ids"), "prompt_condition": r["condition"]})
        h1 = math.ceil(len(progs) / 2)
        for i, p in enumerate(progs):
            p["half"] = 1 if i < h1 else 2
            p["m_index"] = i
        out[k] = {"programs": progs, "n_replaced": n_rep, "scrub_failures": fails, "M": len(progs)}
        logger.debug(f"scrub {k}: kept {len(progs)}, replaced {n_rep}")
    return out
