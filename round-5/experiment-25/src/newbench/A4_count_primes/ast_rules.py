"""A4 AST rules."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from astlib import parse  # noqa: E402


def label(code):
    f = parse(code)
    if f is None:
        return "invalid"
    if f.ident("atkin") or (f.rx(r"%\s*12") and f.rx(r"4\s*\*\s*\w+\s*\*\s*\w+")):
        return "atkin"
    if f.ident("sundaram") or f.rx(r"\w+\s*\+\s*\w+\s*\+\s*2\s*\*\s*\w+\s*\*\s*\w+"):
        return "sundaram"
    if f.ident("segment", "seg", "block", "segment_size", "seg_size", "segsize", "window"):
        return "segmented_sieve"
    big = f.rx(r"\[\s*(True|False|0|1)\s*\]\s*\*\s*\(?\s*(\w+\s*\+\s*1|\w+)") or f.has("bytearray")
    if big and f.rx(r"%\s*\w+\s*==\s*0") and f.rx(r"for\s+\w+\s+in\s+\w*prime\w*"):
        return "linear_sieve"
    if big and (f.rx(r"range\(\s*\w+\s*\*\s*\w+\s*,") or f.rx(r"\[\s*\w+\s*\*\s*\w+\s*:{1,2}") or
                f.rx(r"\[\s*\w+\s*\*\*\s*2\s*:") or f.rx(r"range\(\s*\w+\s*\*\*\s*2")):
        return "eratosthenes"
    if f.rx(r"%") and f.n_loops >= 1:
        return "trial_division"
    if big:
        return "eratosthenes"
    return "unknown"
