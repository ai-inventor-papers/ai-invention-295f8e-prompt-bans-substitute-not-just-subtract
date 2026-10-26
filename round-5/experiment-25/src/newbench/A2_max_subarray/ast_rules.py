"""A2 AST rules."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from astlib import parse  # noqa: E402


def label(code):
    f = parse(code)
    if f is None:
        return "invalid"
    seg_ident = f.ident("tree", "seg", "segment")
    if (seg_ident and (f.classes or f.rx(r"\b(2|4)\s*\*\s*\w+") or f.recursive)) or \
            (f.classes and f.ident("best", "pre", "suf", "total") and f.recursive):
        return "segment_tree"
    if f.rx(r"2\s*\*\s*\w+\s*\+\s*1") and f.rx(r"\]\s*\*\s*\(?\s*(2|4)\s*\*"):
        return "segment_tree"
    if f.recursive:
        return "divide_conquer"
    if f.max_loop_depth >= 2:
        return "other"
    pre_ident = f.ident("prefix", "pre", "cum", "accum", "psum", "presum", "running")
    uses_min = f.has("min") or f.ident("min_pre", "minpre", "min_prefix", "min_sum", "minsum", "smallest",
                                       "min_so_far", "minval", "lowest")
    if f.has("accumulate") or (pre_ident and uses_min):
        return "prefix_min"
    if f.has("max") or f.rx(r"<\s*0") or f.n_loops >= 1:
        return "kadane"
    return "unknown"
