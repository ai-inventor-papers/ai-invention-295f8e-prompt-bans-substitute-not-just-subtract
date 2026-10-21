"""A9 AST rules."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from astlib import parse  # noqa: E402


def label(code):
    f = parse(code)
    if f is None:
        return "invalid"
    if "heapq" in f.imports or f.has("heappush", "heappop", "heapify", "PriorityQueue") or f.rx(r"heapq\.merge"):
        return "heap_merge"
    if f.has("sorted", "sort", "median"):
        return "concat_sort"
    if f.rx(r"nums1\s*\+\s*nums2|nums2\s*\+\s*nums1") and (f.recursive or f.max_loop_depth >= 2):
        return "concat_sort"
    if f.ident("partition", "cut", "half", "partitionx", "partitiony", "imin", "imax") or \
            (f.rx(r"float\(\s*['\"]-?inf") and f.rx(r"while\s+\w+\s*<=?\s*\w+")):
        return "partition_binary_search"
    if f.n_loops >= 1:
        return "merge_two_pointers"
    return "unknown"
