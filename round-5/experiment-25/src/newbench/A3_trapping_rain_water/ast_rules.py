"""A3 AST rules."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from astlib import parse  # noqa: E402


def label(code):
    f = parse(code)
    if f is None:
        return "invalid"
    if (f.pop_noarg >= 1 or f.has("pop")) and (f.ident("stack", "stk", "st", "mono") or f.rx(r"\[\s*-1\s*\]")):
        return "monotonic_stack"
    if f.rx(r"max\(\s*\w+\s*\[\s*:\s*\w*") or f.rx(r"max\(\s*\w+\s*\[\s*\w+\s*:\s*\]"):
        if f.n_loops >= 1:
            return "other"
    if f.max_loop_depth >= 2:
        return "other"
    arrays = f.rx(r"\[\s*0\s*\]\s*\*\s*\(?\s*(n|len\()") or f.has("accumulate") or \
        f.rx(r"=\s*\[\s*0\s*for\s") or f.rx(r"\[\s*None\s*\]\s*\*")
    if arrays and f.ident("left", "right", "lmax", "rmax", "left_max", "right_max", "prefix", "suffix", "maxl",
                          "maxr", "lm", "rm", "pre", "suf", "l_max", "r_max"):
        return "prefix_suffix_max"
    if f.rx(r"while\s+\w+\s*<\s*\w+") and f.ident("left", "right", "l", "r", "lo", "hi", "i", "j"):
        return "two_pointers"
    if f.ident("peak", "highest", "tallest", "top", "max_idx", "maxi", "max_index", "mid", "summit") or \
            (f.has("index") and f.has("max")):
        return "peak_split"
    return "unknown"
