"""A7 AST rules."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from astlib import parse  # noqa: E402


def label(code):
    f = parse(code)
    if f is None:
        return "invalid"
    if f.ident("manacher") or f.rx(r"['\"]#['\"]\s*\.join|['\"]\^#|#\$['\"]|['\"]\|['\"]\s*\.join") or \
            (f.rx(r"2\s*\*\s*[A-Za-z_]\w*\s*-\s*[A-Za-z_]\w*") and
             f.ident("center", "right", "mirror", "radius", "rightmost", "centre", "ctr")):
        return "manacher"
    if f.rx(r"\[\s*\[\s*(False|0|True|None)\s*\]\s*\*") or (f.ident("dp", "table") and f.max_loop_depth >= 2):
        return "dp_table"
    if f.rx(r"(\w+)\s*==\s*\1\s*\[\s*::\s*-1\s*\]") or f.rx(r"\[\s*\w+\s*:\s*\w+[^\]]*\]\s*==\s*\w+\[[^\]]*\]\s*\[::-1\]") \
            or (f.rx(r"\[::-1\]") and f.max_loop_depth >= 2):
        return "brute_force"
    if f.rx(r"while\s+\w+\s*>=\s*0\s+and\s+\w+\s*<") or f.ident("expand", "center", "around", "centre") or \
            f.rx(r"while\s+\w+\s*-\s*\w+\s*>=\s*0"):
        return "expand_center"
    return "unknown"
