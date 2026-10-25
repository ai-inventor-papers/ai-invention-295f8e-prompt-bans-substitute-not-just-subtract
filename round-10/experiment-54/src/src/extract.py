#!/usr/bin/env python3
"""Program extraction (frozen in commit #1; identical in every cell).

Visible content only (reasoning excluded; any inline <think>...</think> is removed). Take the last ```python fenced
block containing 'def priority'; else the first fenced block of any language containing it; else the text from
'def priority' to the end. The AST filter keeps numpy/math imports, function and class definitions and constant
assignments, and drops top-level calls, prints, other imports and __main__ blocks. The kept nodes keep their original
source text (comments inside them survive); `raw` is the whole selected block (used by the lexical flag L1)."""
from __future__ import annotations

import ast
import re
from typing import Any

FENCE_RE = re.compile(r"```[ \t]*([A-Za-z0-9_+-]*)[^\n]*\n(.*?)(?:```|\Z)", re.DOTALL)
THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
ALLOWED_IMPORTS = {"numpy", "math"}
CONST_CALLS = {"float", "int", "tuple", "list", "set", "dict", "frozenset", "range"}


def visible_only(content: str) -> str:
    c = THINK_RE.sub("", content or "")
    if "</think>" in c:                       # unmatched closing tag: keep what follows it
        c = c.split("</think>", 1)[1]
    return c


def select_block(content: str) -> tuple[str | None, str]:
    text = visible_only(content)
    blocks = [(m.group(1).lower(), m.group(2)) for m in FENCE_RE.finditer(text)]
    py = [b for lang, b in blocks if lang in ("python", "py", "python3") and "def priority" in b]
    if py:
        return py[-1], "last_python_fence"
    anyb = [b for _, b in blocks if "def priority" in b]
    if anyb:
        return anyb[0], "first_fence"
    i = text.find("def priority")
    if i >= 0:
        return text[i:], "from_def"
    return None, "none"


def _const_like(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return all(_const_like(e) for e in node.elts)
    if isinstance(node, ast.Dict):
        return all(k is None or _const_like(k) for k in node.keys) and all(_const_like(v) for v in node.values)
    if isinstance(node, ast.UnaryOp):
        return _const_like(node.operand)
    if isinstance(node, ast.BinOp):
        return _const_like(node.left) and _const_like(node.right)
    if isinstance(node, ast.Attribute):           # np.inf, math.pi, np.float64
        return isinstance(node.value, ast.Name) and node.value.id in ("np", "numpy", "math")
    if isinstance(node, ast.Name):
        return node.id in ("np", "numpy", "math", "True", "False", "None")
    if isinstance(node, ast.Call):
        f = node.func
        ok_f = (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in ("np", "numpy",
                                                                                                  "math")) or \
               (isinstance(f, ast.Name) and f.id in CONST_CALLS)
        return ok_f and all(_const_like(a) for a in node.args) and all(_const_like(k.value) for k in node.keywords)
    return False


def _keep(node: ast.stmt) -> bool:
    if isinstance(node, ast.Import):
        return all(a.name.split(".")[0] in ALLOWED_IMPORTS for a in node.names)
    if isinstance(node, ast.ImportFrom):
        return (node.module or "").split(".")[0] in ALLOWED_IMPORTS and not node.level
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
        return True
    if isinstance(node, ast.Assign):
        return all(isinstance(t, (ast.Name, ast.Tuple)) for t in node.targets) and _const_like(node.value)
    if isinstance(node, ast.AnnAssign):
        return isinstance(node.target, ast.Name) and node.value is not None and _const_like(node.value)
    return False


def _parse_prefix(src: str) -> tuple[ast.Module | None, str]:
    """Parse the block; on a syntax error, retry on successively shorter line prefixes (truncated responses)."""
    try:
        return ast.parse(src), src
    except (SyntaxError, ValueError):
        pass
    lines = src.splitlines()
    for cut in range(len(lines) - 1, 0, -1):
        cand = "\n".join(lines[:cut])
        try:
            t = ast.parse(cand)
        except (SyntaxError, ValueError):
            continue
        if any(isinstance(n, ast.FunctionDef) and n.name == "priority" for n in t.body):
            return t, cand
        return None, src
    return None, src


def extract(content: str) -> dict[str, Any]:
    block, how = select_block(content)
    if block is None:
        return {"ok": False, "how": how, "raw": "", "code": "", "error": "no priority function"}
    tree, src = _parse_prefix(block)
    if tree is None:
        return {"ok": False, "how": how, "raw": block, "code": block, "error": "syntax"}
    lines = src.splitlines()
    kept = []
    for node in tree.body:
        if _keep(node):
            start = node.lineno - 1
            if getattr(node, "decorator_list", None):
                start = min(d.lineno for d in node.decorator_list) - 1
            kept.append("\n".join(lines[start:node.end_lineno]))
    code = "\n\n".join(kept) + "\n"
    has_fn = any(isinstance(n, ast.FunctionDef) and n.name == "priority" for n in tree.body)
    if not has_fn:
        return {"ok": False, "how": how, "raw": block, "code": code, "error": "no priority function"}
    if "import numpy" not in code and "from numpy" not in code:
        code = "import numpy as np\n" + code
    return {"ok": True, "how": how, "raw": block, "code": code, "error": "", "truncated_parse": src != block}


def unit_test_u6() -> dict[str, Any]:
    """U6: extraction on 12 synthetic responses."""
    fn = "def priority(item, bins):\n    return -(bins - item)\n"
    cases = [
        ("plain fence", f"Here:\n```python\n{fn}```\n", True, "last_python_fence"),
        ("thinking prefix", f"<think>\nmaybe ```python\ndef priority(a,b): pass\n```\n</think>\n```python\n{fn}```",
         True, "last_python_fence"),
        ("two blocks, last wins", f"```python\ndef priority(item, bins):\n    return bins\n```\nBetter:\n```python\n"
         f"{fn}```", True, "last_python_fence"),
        ("top-level test calls", f"```python\nimport numpy as np\n{fn}\nprint(priority(3, np.array([5, 9])))\n"
         f"priority(1, np.array([2]))\n```", True, "last_python_fence"),
        ("main block", f"```python\n{fn}\nif __name__ == '__main__':\n    print(1)\n```", True, "last_python_fence"),
        ("missing fence", f"The function is:\n\n{fn}", True, "from_def"),
        ("helper functions", "```python\nimport numpy as np\nEPS = 1e-9\ndef _gap(item, bins):\n    return bins - item"
         "\n\ndef priority(item, bins):\n    return -_gap(item, bins) + EPS\n```", True, "last_python_fence"),
        ("unlabelled fence", f"```\n{fn}```", True, "first_fence"),
        ("no function", "I cannot do that.", False, "none"),
        ("other import dropped", f"```python\nimport random\nimport numpy as np\n{fn}```", True, "last_python_fence"),
        ("truncated tail", f"```python\n{fn}\ndef extra(x):\n    return (x +", True, "last_python_fence"),
        ("class helper", "```python\nimport numpy as np\nclass H:\n    k = 2\n\ndef priority(item, bins):\n"
         "    return -(bins - item) * H.k\n```", True, "last_python_fence"),
    ]
    res = []
    for name, txt, ok, how in cases:
        r = extract(txt)
        good = r["ok"] == ok and r["how"] == how
        if ok and r["ok"]:
            good = good and "print(" not in r["code"] and "__main__" not in r["code"] and "import random" not in \
                r["code"]
            try:
                compile(r["code"], "<t>", "exec")
            except SyntaxError:
                good = False
        res.append({"case": name, "ok": bool(good), "how": r["how"], "extracted_ok": r["ok"]})
    return {"cases": res, "passed": all(x["ok"] for x in res)}
