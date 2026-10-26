"""A8 AST rules."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from astlib import parse  # noqa: E402


def label(code):
    f = parse(code)
    if f is None:
        return "invalid"
    if f.popleft or f.pop0 or f.has("Queue") or (f.has("deque") and not f.pop_noarg):
        return "bfs_indices"
    arr = f.rx(r"\[\s*(False|True|0|1|None)\s*\]\s*\*\s*\(?\s*(n|len\()")
    if (arr and f.ident("dp", "good", "reach", "reachable", "can", "ok", "memo", "possible")) or \
            (f.recursive and f.memo) or (arr and f.max_loop_depth >= 2):
        return "dp"
    if f.ident("reach", "farthest", "furthest", "max_reach", "maxreach", "last", "goal", "target", "far",
               "max_pos", "last_good", "lastpos", "last_pos") or f.has("max"):
        return "greedy"
    return "unknown"
