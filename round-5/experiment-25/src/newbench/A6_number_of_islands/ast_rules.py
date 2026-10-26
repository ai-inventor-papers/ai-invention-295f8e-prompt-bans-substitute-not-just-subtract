"""A6 AST rules (bench T10 rules)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from astlib import parse  # noqa: E402


def _uf(f):
    return (f.ident("parent", "root", "par") and (f.ident("find") or "find" in f.funcs)) or \
        f.ident("union", "dsu", "disjoint", "unionfind", "union_find")


def label(code):
    f = parse(code)
    if f is None:
        return "invalid"
    if _uf(f):
        return "union_find"
    if f.popleft or f.pop0 or f.has("Queue") or (f.has("deque") and not f.pop_noarg):
        return "bfs_flood"
    if f.recursive or f.pop_noarg or f.has("LifoQueue"):
        return "dfs_flood"
    return "unknown"
