"""Static (AST) labeller: imports, call names, loop/recursion structure, characteristic expressions;
identifier hints are weak evidence only.  ast_label(task, code) -> mode | 'other' | 'unknown' | 'invalid'."""

from __future__ import annotations

import ast
import re
from collections import Counter


class F:
    """AST feature bag of one program."""

    def __init__(self, code: str):
        self.code = code
        self.tree = ast.parse(code)
        self.calls = Counter()
        self.attr_calls = Counter()
        self.imports = set()
        self.names = Counter()
        self.funcs = {}
        self.recursive = set()
        self.max_loop_depth = 0
        self.n_loops = 0
        self.classes = 0
        self.decorators = Counter()
        self.bitand_neg = False
        self.pop0 = 0
        self.pop_noarg = 0
        self.popleft = 0
        self.subscript_nested = 0
        self.consts = Counter()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    self.imports.add(a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.imports.add(node.module.split(".")[0])
                for a in node.names:
                    self.imports.add(a.name)
            elif isinstance(node, ast.Call):
                fn = node.func
                if isinstance(fn, ast.Name):
                    self.calls[fn.id] += 1
                elif isinstance(fn, ast.Attribute):
                    self.attr_calls[fn.attr] += 1
                    if isinstance(fn.value, ast.Name):
                        self.calls[f"{fn.value.id}.{fn.attr}"] += 1
                    if fn.attr == "pop":
                        if not node.args:
                            self.pop_noarg += 1
                        elif isinstance(node.args[0], ast.Constant) and node.args[0].value == 0:
                            self.pop0 += 1
                    if fn.attr == "popleft":
                        self.popleft += 1
            elif isinstance(node, ast.Name):
                self.names[node.id] += 1
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.funcs[node.name] = node
                for d in node.decorator_list:
                    dn = d.func if isinstance(d, ast.Call) else d
                    nm = dn.attr if isinstance(dn, ast.Attribute) else (dn.id if isinstance(dn, ast.Name) else "?")
                    self.decorators[nm] += 1
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id == node.name:
                        self.recursive.add(node.name)
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == node.name:
                        self.recursive.add(node.name)
            elif isinstance(node, ast.ClassDef):
                self.classes += 1
            elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitAnd):
                for side in (node.left, node.right):
                    if isinstance(side, ast.UnaryOp) and isinstance(side.op, ast.USub):
                        self.bitand_neg = True
            elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Subscript):
                self.subscript_nested += 1
            elif isinstance(node, ast.Constant) and isinstance(node.value, (int, str)):
                self.consts[node.value] += 1
        self._loop_depth(self.tree, 0)
        self.low = code.lower()
        self.idents = {n.lower() for n in self.names} | {f.lower() for f in self.funcs}

    def _loop_depth(self, node, d):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.For, ast.While)):
                self.n_loops += 1
                self.max_loop_depth = max(self.max_loop_depth, d + 1)
                self._loop_depth(ch, d + 1)
            elif isinstance(ch, (ast.FunctionDef, ast.Lambda, ast.AsyncFunctionDef, ast.ClassDef)):
                self._loop_depth(ch, 0)
            else:
                self._loop_depth(ch, d)

    def has(self, *names):
        return any(self.calls.get(n) or self.attr_calls.get(n) for n in names)

    def ident(self, *subs):
        return any(any(s in i for s in subs) for i in self.idents)

    def rx(self, pattern):
        return re.search(pattern, self.code) is not None

    @property
    def memo(self):
        return bool(self.decorators.get("lru_cache") or self.decorators.get("cache") or self.ident("memo", "cache"))


def _bisect(f):
    return f.has("bisect_left", "bisect_right", "bisect", "insort", "insort_left", "insort_right")


def _manual_bsearch(f):
    return f.ident("mid") and f.rx(r"while\s+\w+\s*(<|<=)\s*\w+")


def _uf(f):
    return (f.ident("parent", "root") and (f.ident("find") or "find" in f.funcs)) or f.ident("union", "dsu", "disjoint")


def _heapish(f):
    return f.has("heappush", "heappop", "heapify", "heappushpop", "heapreplace", "nlargest", "nsmallest") or \
        f.has("PriorityQueue")


def t03(f):
    if f.has("nsmallest", "nlargest"):
        return "size_k_heap"
    if f.has("heapify") and f.has("heappop") and not (f.has("heappush") and f.rx(r"len\(\s*\w+\s*\)\s*>")):
        return "heapify_pop"
    if f.has("heappush", "heappushpop", "heapreplace"):
        if f.rx(r"len\(\s*\w+\s*\)\s*(>|>=|==|<|<=)\s*k") or f.has("heappushpop", "heapreplace"):
            return "size_k_heap"
        if f.has("heappop"):
            return "heapify_pop"
    if f.rx(r"\b5\b") and (f.ident("median", "group", "chunk") or f.rx(r":\s*\w+\s*\+\s*5\]")) and f.recursive | {"x"}:
        if f.ident("median") or f.rx(r"range\([^)]*,\s*5\)"):
            return "median_of_medians"
    if f.rx(r"\[0\]\s*\*\s*\(?\s*(max|hi|high|max_val|maxv|mx|\w+_max|20001|20000|10001)") or \
            (f.ident("count") and f.rx(r"\[0\]\s*\*\s*\(") and f.has("min", "max")) or \
            f.rx(r"for\s+\w+\s+in\s+range\(\s*(min|lo|low|min_val|mn|-\s*10000|offset)\w*") and f.ident("count", "freq"):
        return "counting_sort"
    if (f.has("Counter") or f.ident("count", "freq")) and f.rx(r"sorted\(\s*\w+\.?(keys|items)?\(?\)?\s*\)"):
        return "unknown"
    if f.ident("pivot", "partition", "quickselect", "select") and not f.has("sort", "sorted"):
        return "quickselect"
    if f.ident("pivot") and f.recursive:
        return "quickselect"
    if f.has("sorted", "sort") and not f.ident("pivot"):
        return "full_sort"
    if f.ident("pivot"):
        return "quickselect"
    return "unknown"


def t04(f):
    if f.has("find", "index") and f.rx(r"\.(find|index)\(\s*needle") or f.rx(r"needle\s+in\s+haystack"):
        if not f.rx(r"for\s+\w+\s+in\s+range"):
            return "builtin"
    if f.rx(r"needle\s*\+\s*['\"]") or f.rx(r"['\"][$#|@]['\"]\s*\+") or f.ident("z_arr", "zarr", "z_func", "zfunc") or \
            (f.ident("z") and f.rx(r"\bz\s*=\s*\[0\]")):
        return "z_algorithm"
    if f.ident("lps", "fail", "prefix_func", "pi", "kmp", "next_arr", "partial") and f.rx(r"\w+\[\s*\w+\s*-\s*1\s*\]"):
        return "kmp"
    if f.has("ord") and (f.has("pow") or f.rx(r"%\s*\w*(mod|prime|q|MOD)\w*") or f.rx(r"\*\*")) or f.ident("rolling", "hash"):
        return "rabin_karp"
    if f.ident("shift", "bad_char", "badchar", "bad_character", "skip", "last_occ", "last", "table", "horspool", "occ") and \
            (f.rx(r"-=\s*1") or f.rx(r"range\([^)]*-\s*1\s*,\s*-1\s*,\s*-1\)")):
        return "bmh"
    if f.has("startswith") or f.rx(r"haystack\[\s*\w+\s*:\s*\w+\s*\+\s*\w+\s*\]\s*==") or \
            f.rx(r"==\s*needle") or f.max_loop_depth >= 2:
        return "naive"
    if f.has("find", "index") or f.rx(r"\bin\s+haystack"):
        return "builtin"
    return "unknown"


def t05(f):
    if f.max_loop_depth >= 2 and not f.has("sorted", "sort") and not f.rx(r"in\s+\w*(seen|map|dict|lookup|index|pos|hash)\w*"):
        if f.rx(r"\[\s*i\s*\]\s*\+\s*\w+\[\s*j\s*\]") or f.rx(r"range\(\s*i\s*\+\s*1"):
            return "brute_force"
    if f.has("sorted", "sort"):
        if _bisect(f) or _manual_bsearch(f) and not f.ident("left", "right") or f.ident("mid"):
            if not (f.ident("left") and f.ident("right") and f.rx(r"while\s+left\s*<\s*right") and not f.ident("mid")):
                return "sort_binary_search"
        if f.rx(r"while\s+\w+\s*<\s*\w+") and (f.rx(r"-=\s*1") or f.rx(r"\+=\s*1")):
            return "sort_two_pointers"
    if f.rx(r"\bin\s+\w+") and (f.rx(r"\{\s*\}") or f.has("dict", "defaultdict")):
        return "hash_map"
    if f.max_loop_depth >= 2:
        return "brute_force"
    return "unknown"


def t06(f):
    if f.ident("slow", "tortoise") and f.ident("fast", "hare"):
        return "floyd"
    if f.rx(r"nums\[\s*nums\[") and f.n_loops >= 2 and not f.rx(r"=\s*-"):
        return "floyd"
    if f.ident("mid") and f.rx(r"<=\s*mid|mid\s*>=") and (f.ident("count", "cnt") or f.has("sum")):
        return "value_binary_search"
    if f.rx(r"nums\[\s*\w+\s*\]\s*\*=\s*-1") or f.rx(r"=\s*-\s*nums\[") or f.rx(r"nums\[[^\]]*abs") or \
            (f.has("abs") and f.rx(r"<\s*0")):
        return "index_marking"
    if f.rx(r"nums\[\s*nums\[\s*\w+\s*\]\s*\]\s*,\s*nums\[") or f.rx(r"nums\[\s*\w+\s*\]\s*,\s*nums\[\s*nums"):
        return "index_marking"
    if f.has("sorted", "sort") and f.rx(r"\[\s*\w+\s*\]\s*==\s*\w+\[\s*\w+\s*[-+]\s*1\s*\]"):
        return "sort_adjacent"
    if f.has("set", "Counter", "defaultdict") or f.rx(r"\{\s*\}") or f.rx(r"\[\s*(0|False)\s*\]\s*\*"):
        return "hash_set"
    if f.has("sorted", "sort"):
        return "sort_adjacent"
    if f.has("sum") or f.rx(r"\^"):
        return "other"
    if f.rx(r"nums\[\s*\w+\s*-\s*1\s*\]\s*==\s*nums\[\s*\w+\s*\]|nums\[\s*\w+\s*\]\s*==\s*nums\[\s*\w+\s*[-+]\s*1\s*\]"):
        return "sort_adjacent"
    return "unknown"


def t08(f):
    if f.rx(r"sqrt\(\s*5|5\s*\*\*\s*0?\.5|phi|golden"):
        return "other"
    mat = f.rx(r"\[\s*\[\s*1\s*,\s*1\s*\]\s*,\s*\[\s*1\s*,\s*0\s*\]\s*\]") or f.ident("matrix", "mat_", "matmul", "mat")
    if mat and (f.rx(r"\[0\]\[0\]") or f.rx(r"\[\s*\[")):
        return "matrix_power"
    if f.rx(r"2\s*\*\s*\w+\s*-\s*\w+") and (f.rx(r">>\s*1|//\s*2") or f.ident("doubling")):
        return "fast_doubling"
    if f.recursive and (f.memo or f.ident("memo", "cache", "dp")):
        return "memo_recursion"
    if f.recursive and not f.memo:
        return "other"
    if f.n_loops >= 1:
        return "iteration"
    return "unknown"


def t10(f):
    if _uf(f):
        return "union_find"
    if f.popleft or f.pop0 or f.has("Queue") or (f.has("deque") and not f.pop_noarg):
        return "bfs"
    if f.recursive or f.pop_noarg or f.has("LifoQueue"):
        return "dfs"
    if f.has("min") and f.rx(r"while\s+\w*chang\w*") or f.ident("label", "changed"):
        return "label_propagation"
    return "unknown"


def t11(f):
    if f.bitand_neg or f.ident("fenwick", "bit", "tree", "segment"):
        return "fenwick"
    if _bisect(f) or (f.ident("tail", "pile", "sub") and (_manual_bsearch(f) or f.ident("mid", "lo", "left"))):
        return "patience_bisect"
    if f.max_loop_depth >= 2 or (f.recursive and f.memo):
        return "quadratic_dp"
    return "unknown"


def t13(f):
    if f.classes and f.ident("max_end", "maxend", "max_high", "interval_tree", "itree", "node", "insert"):
        return "interval_tree"
    if _uf(f):
        return "union_find"
    if f.has("sorted", "sort"):
        return "sort_sweep"
    return "unknown"


def t14(f):
    if f.attr_calls.get("most_common"):
        if f.rx(r"most_common\(\s*\)"):
            return "sort_by_count"
        return "heap"
    if _heapish(f):
        return "heap"
    if f.ident("bucket", "freq_list", "buckets") or f.rx(r"\[\s*\[\s*\]\s*for\s+\w+\s+in\s+range\(\s*len\(\s*nums\s*\)\s*\+\s*1"):
        return "bucket_sort"
    if f.ident("pivot", "partition", "quickselect", "select"):
        return "quickselect_counts"
    if f.has("sorted", "sort"):
        return "sort_by_count"
    return "unknown"


def r1(f):
    if f.recursive and (f.memo or f.ident("memo", "dp", "cache")):
        return "memo_recursion"
    if (_bisect(f) or _manual_bsearch(f)) and (f.ident("dp") or f.rx(r"\[0\]\s*\*\s*\(")):
        return "dp_bisect"
    if f.max_loop_depth >= 2 and (f.ident("dp", "longest", "best", "chain") or f.rx(r"\[1\]\s*\*")):
        return "dag_longest_path"
    if f.has("sorted", "sort"):
        return "greedy_end"
    return "unknown"


def r2(f):
    if f.rx(r"len\(\s*edges\s*\)\s*(>|>=|!=|==)\s*\w*n\w*\s*-") or f.rx(r"edge\w*count\w*\s*(>|>=)") or \
            f.rx(r"(>|>=)\s*\w*node\w*count") or f.ident("edge_count", "num_edges", "edges_count", "edge_cnt", "ecount"):
        return "edge_count"
    if _uf(f):
        return "union_find"
    if f.popleft or f.pop0 or f.has("Queue"):
        return "bfs_parent"
    if f.recursive or f.pop_noarg:
        return "dfs_parent"
    return "unknown"


def r3(f):
    indeg = f.ident("indeg", "in_deg", "in_degree", "indegree", "incoming")
    if indeg and (f.popleft or f.pop0 or f.pop_noarg or f.has("deque", "Queue", "heappop")):
        return "kahn"
    if f.recursive or f.ident("color", "colour", "state", "visiting", "on_stack", "onstack", "temp_mark", "gray"):
        if f.recursive or f.pop_noarg:
            return "dfs_postorder"
    if f.ident("depth", "level", "layer", "longest", "dist") and f.has("sorted", "sort"):
        return "layering"
    if indeg or f.ident("remaining", "removed", "done"):
        return "source_removal"
    return "unknown"


def r6(f):
    if _bisect(f):
        return "bisect_module"
    if f.rx(r"(\*=\s*2|<<=\s*1|\*\s*2\b)") and f.ident("bound", "step", "jump", "exp", "hi", "high", "end", "i"):
        if f.rx(r"while\s+\w+\s*<\s*(len|n)\b.*\w+\s*\]\s*(<|<=)") or f.ident("bound", "exp"):
            return "exponential_search"
    if f.ident("mid"):
        if f.rx(r"while\s+\w+\s*(>|>=)\s*0\s+and\s+nums\[") or f.rx(r"while\s+\w+\s*<\s*(len\(nums\)|n)\s*(-\s*1)?\s+and\s+nums\["):
            return "binary_expand"
        return "binary_search"
    if f.has("index") or f.rx(r"for\s+\w+\s*(,\s*\w+)?\s+in\s+(enumerate|range)"):
        return "linear_scan"
    return "unknown"


RULES = {"T03": t03, "T04": t04, "T05": t05, "T06": t06, "T08": t08, "T10": t10, "T11": t11, "T13": t13, "T14": t14,
         "R1": r1, "R2": r2, "R3": r3, "R6": r6}


def ast_label(task: str, code: str | None) -> str:
    if not code:
        return "invalid"
    try:
        f = F(code)
    except (SyntaxError, ValueError):
        return "invalid"
    if "solve" not in f.funcs:
        return "invalid"
    try:
        return RULES[task](f)
    except (RecursionError, KeyError, TypeError):
        return "unknown"
