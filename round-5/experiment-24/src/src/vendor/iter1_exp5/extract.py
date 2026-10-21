"""Program extraction (STEP 3.1) from chat responses and template-free completions.

Identical top-level filtering is applied to every arm: keep Import, ImportFrom, FunctionDef, AsyncFunctionDef,
ClassDef, Assign and AnnAssign nodes (dropping assignments that call solve / print / input), so demo code at
module level can never crash or hang an otherwise valid solution.
"""
from __future__ import annotations

import ast
import re

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
        except (SyntaxError, ValueError):
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
            if isinstance(n, ast.ClassDef) and any(isinstance(m, ast.FunctionDef) and m.name == "solve" for m in n.body):
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


def extract_chat(text: str) -> tuple[str | None, dict]:
    """First ```python (or bare ```) closed block containing 'def solve'; else an unclosed fence; else 'def solve'..end."""
    info = {"source": None, "n_trim": 0, "reason": ""}
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
    mod, src, k = _trim_parse(cand)
    info["n_trim"] = k
    if mod is None:
        info["reason"] = "syntax"
        return None, info
    code, why = _filter(mod)
    info["reason"] = why
    return code, info


def extract_tf(prompt_text: str, completion: str) -> tuple[str | None, dict]:
    info = {"source": "tf", "n_trim": 0, "reason": ""}
    full = prompt_text + completion
    mod, src, k = _trim_parse(full)
    info["n_trim"] = k
    if mod is None:
        info["reason"] = "syntax"
        return None, info
    code, why = _filter(mod)
    info["reason"] = why
    return code, info


def extract(sample: dict, prompt_text: str) -> tuple[str | None, dict]:
    if sample["template"] == "tf":
        return extract_tf(prompt_text, sample["text"])
    return extract_chat(sample["text"])
