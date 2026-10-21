"""A1 AST rules (structure first; identifier hints are weak evidence)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from astlib import parse  # noqa: E402


def label(code):
    f = parse(code)
    if f is None:
        return "invalid"
    if "statistics" in f.imports or f.has("multimode") or (f.has("mode") and "statistics" in f.code):
        return "library_mode"
    if "random" in f.imports or f.has("choice", "randint", "randrange", "shuffle"):
        return "randomized_verify"
    if f.rx(r">>|<<") and f.rx(r"&") and f.rx(r"range\(\s*(32|31|33|64)\s*\)"):
        return "bit_count"
    if f.recursive:
        return "divide_conquer"
    if f.has("sorted", "sort") and f.rx(r"//\s*2|>>\s*1|\[\s*-?\s*\w*\s*//"):
        return "sort_middle"
    if f.has("Counter", "defaultdict", "most_common", "setdefault", "set") or f.rx(r"\.get\(") or \
            f.rx(r"\{\s*\}") or f.rx(r"\bdict\(\s*\)"):
        return "hash_count"
    bm = (f.rx(r"\+=\s*1") and f.rx(r"-=\s*1")) or f.rx(r"\+=\s*1\s+if\b.*else\s+-\s*1") or \
        f.rx(r"\+=\s*\(?\s*1\s+if\b") or f.ident("candidate", "cand")
    if bm and f.rx(r"==\s*0") and not f.rx(r"\.count\(\s*\w+\s*\)\s*>") :
        return "boyer_moore_vote"
    if f.has("count") and f.n_loops >= 1:
        return "other"
    if bm:
        return "boyer_moore_vote"
    return "unknown"
