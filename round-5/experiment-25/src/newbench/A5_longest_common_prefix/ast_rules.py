"""A5 AST rules."""
import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from astlib import parse  # noqa: E402


def _tname(t):
    if isinstance(t, ast.Name):
        return t.id
    if isinstance(t, ast.Tuple) and t.elts and isinstance(t.elts[0], ast.Name):
        return t.elts[0].id
    return None


def _vertical(tree):
    """An outer loop over positions / characters whose body walks the strings and indexes each by that position."""
    for outer in ast.walk(tree):
        if not isinstance(outer, (ast.For, ast.While)):
            continue
        ots = {_tname(outer.target)} if isinstance(outer, ast.For) else set()
        if isinstance(outer, ast.While):
            ots = {n.id for n in ast.walk(outer.test) if isinstance(n, ast.Name)}
        ots.discard(None)
        for inner in ast.walk(outer):
            tgt = None
            if inner is not outer and isinstance(inner, ast.For):
                tgt, body = _tname(inner.target), inner
            elif isinstance(inner, ast.comprehension):
                tgt, body = _tname(inner.target), outer
            if not tgt:
                continue
            for sub in ast.walk(body):
                if isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Name) and sub.value.id == tgt and \
                        isinstance(sub.slice, ast.Name) and sub.slice.id in ots:
                    return True
    return False


def label(code):
    f = parse(code)
    if f is None:
        return "invalid"
    if f.has("commonprefix"):
        return "library_commonprefix"
    if (f.classes and f.ident("trie", "children", "node", "child")) or f.has("setdefault") or f.ident("trie"):
        return "trie"
    if f.has("sorted", "sort") or (f.has("min") and f.has("max")):
        return "sort_ends"
    if f.recursive:
        return "divide_conquer"
    if f.ident("mid") and f.rx(r"while\s+\w+\s*<=?\s*\w+"):
        return "binary_search_length"
    if f.has("zip") or _vertical(f.tree) or f.rx(r"for\s+\w+\s+in\s+range\(\s*(len\(\s*\w+\[\s*0\s*\]\s*\)|min)") or \
            f.rx(r"for\s+\w+\s*,\s*\w+\s+in\s+enumerate\(\s*\w+\[\s*0\s*\]\s*\)") or \
            f.rx(r"for\s+\w+\s+in\s+range\(\s*\w*(min|shortest|length|n|m)\w*\s*\)"):
        return "vertical_scan"
    if f.has("startswith", "find", "index") or f.rx(r"\[\s*:\s*-\s*1\s*\]") or f.rx(r"\w+\s*=\s*\w+\[\s*:\s*\w+\s*\]") \
            or f.n_loops >= 1:
        return "horizontal_scan"
    return "unknown"
