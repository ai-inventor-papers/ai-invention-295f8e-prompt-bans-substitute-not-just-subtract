"""Frozen catalogue cards for the 13 candidate bench tasks.

Every task has one fixed DESCRIPTION (new wording, no complexity hints, no LeetCode
follow-ups), a catalogue of algorithm modes with display names, one-line mechanism
descriptions (judge prompt and descriptive forced variant) and an alias lexicon
(name scrubbing and association mapping).  Nothing in here is a ban, mention,
neutral-twin, nonce or novelty prompt.
"""

from __future__ import annotations

FORMAT_LINE = (
    "Use only the Python standard library. Return only one ```python code block "
    "containing the function solve and any helpers, with no example usage and no explanation."
)

# exp1's five forced paraphrases are ids 0-4; ids 5-9 are new (frozen, see deviations).
FORCED_TEMPLATES = [
    "Implement {j} for this task.",
    "Use {j} to solve this task.",
    "Solve this task with {j}.",
    "Your solution should use {j}.",
    "Write an implementation based on {j}.",
    "Solve the task below using {j}.",
    "Your solution must implement {j}.",
    "Write code that implements {j}.",
    "Base your solution on {j}.",
    "Apply {j} to solve this task.",
]
DESCRIPTIVE_FORCED_TEMPLATE = "Implement the approach described as: {d}"
ASSOCIATION_TEMPLATE = (
    "What is the standard alternative to {x} for this task? "
    "Name one algorithm and answer in one sentence."
)

# Hypothesis task order (tie-break of the disagreement ranking).
TASK_ORDER = ["T03", "T05", "T06", "T14", "T10", "T08", "T04", "T11", "T13", "R1", "R2", "R3", "R6"]

TASKS: dict[str, dict] = {
    "T03": {
        "task_id": "T03_kth_smallest",
        "leetcode_ids": [215],
        "signature": "solve(nums, k)",
        "description": (
            "Task: write a Python function solve(nums, k) that returns the k-th smallest value in nums. "
            "The argument nums is a list of integers with 1 <= len(nums) <= 2000, and every value lies "
            "between -10000 and 10000 inclusive; values may repeat. The argument k is an integer with "
            "1 <= k <= len(nums), counted from 1, so k = 1 asks for the minimum and k = len(nums) for the "
            "maximum. Repeated values are counted separately: for nums = [3, 1, 3] and k = 3 the answer is 3."
        ),
        "bounds": {"n": [1, 2000], "value": [-10000, 10000]},
        "modes": {
            "full_sort": ("a full sort", "sort the whole list (sorted/list.sort or a hand-written full sort) and index position k-1"),
            "size_k_heap": ("a size-k heap", "keep a heap bounded by k elements while scanning (or heapq.nsmallest/nlargest) and read its top"),
            "heapify_pop": ("heapify-and-pop", "heapify all n values into one heap, then pop k times"),
            "quickselect": ("quickselect", "partition around a pivot and recurse or loop into only the side that contains rank k"),
            "median_of_medians": ("median of medians", "quickselect whose pivot is the median of the medians of groups of five, giving a worst-case linear selection"),
            "counting_sort": ("counting sort", "count occurrences of every value over the value range and walk the counts until k are covered"),
        },
        "aliases": {
            "full_sort": ["full sort", "sorting", "sort the list", "merge sort", "timsort"],
            "size_k_heap": ["size-k heap", "size k heap", "bounded heap", "max-heap of size k", "min-heap of size k", "nsmallest", "nlargest"],
            "heapify_pop": ["heapify-and-pop", "heapify and pop", "heapify", "heap pop"],
            "quickselect": ["quickselect", "quick select", "hoare's selection", "hoare selection", "randomized select", "partition-based selection"],
            "median_of_medians": ["median of medians", "median-of-medians", "bfprt", "introselect"],
            "counting_sort": ["counting sort", "counting-sort", "count array", "bucket count"],
        },
    },
    "T04": {
        "task_id": "T04_substring_search",
        "leetcode_ids": [28],
        "signature": "solve(haystack, needle)",
        "description": (
            "Task: write a Python function solve(haystack, needle) that returns the index of the first "
            "position at which the string needle occurs as a contiguous substring of the string haystack, "
            "or -1 if needle is not a substring of haystack. Both strings consist only of lowercase English letters, with "
            "1 <= len(haystack) <= 2000 and 1 <= len(needle) <= 200. Indices start at 0. If needle is "
            "longer than haystack, the answer is -1."
        ),
        "bounds": {"haystack": [1, 2000], "needle": [1, 200]},
        "modes": {
            "naive": ("the naive sliding-window comparison", "try every start position and compare the needle character by character (or by slicing) against the window"),
            "kmp": ("the Knuth-Morris-Pratt algorithm (KMP)", "precompute the failure/prefix function of the needle and scan the haystack once without moving backwards"),
            "rabin_karp": ("the Rabin-Karp rolling hash", "compare a rolling polynomial hash of each window with the needle's hash and verify on a hash match"),
            "z_algorithm": ("the Z-algorithm", "compute the Z-array of needle + separator + haystack and report the first position whose Z-value equals the needle length"),
            "bmh": ("the Boyer-Moore-Horspool algorithm", "compare from the right end of the window and shift by a bad-character table built from the needle"),
            "builtin": ("Python's built-in string search (str.find)", "delegate to Python's built-in substring search: str.find, str.index or the in operator"),
        },
        "aliases": {
            "naive": ["naive", "brute force", "brute-force", "sliding window", "sliding-window"],
            "kmp": ["knuth-morris-pratt", "knuth morris pratt", "kmp", "failure function", "prefix function", "lps array", "lps"],
            "rabin_karp": ["rabin-karp", "rabin karp", "rolling hash", "polynomial hash"],
            "z_algorithm": ["z-algorithm", "z algorithm", "z-function", "z function", "z-array", "z array"],
            "bmh": ["boyer-moore-horspool", "boyer moore horspool", "horspool", "boyer-moore", "boyer moore", "bad character", "bad-character"],
            "builtin": ["str.find", "built-in", "builtin", "str.index", ".find(", "in operator"],
        },
    },
    "T05": {
        "task_id": "T05_two_sum",
        "leetcode_ids": [1],
        "signature": "solve(nums, target)",
        "description": (
            "Task: write a Python function solve(nums, target) that returns a list [i, j] of two indices "
            "with i < j such that nums[i] + nums[j] == target. The argument nums is a list of integers with "
            "2 <= len(nums) <= 2000 and every value between -10**9 and 10**9 inclusive; target is an integer. "
            "Each input has exactly one pair of indices whose values add up to target, so the answer is "
            "unique. The two indices must be different positions, although the values at them may be equal."
        ),
        "bounds": {"n": [2, 2000], "value": [-10**9, 10**9]},
        "modes": {
            "hash_map": ("a hash map of seen values", "scan once, storing each value's index in a dict and looking up target minus the current value"),
            "sort_two_pointers": ("sorting with two pointers", "sort (value, index) pairs and move two pointers inwards from both ends"),
            "brute_force": ("a brute-force double loop", "check every pair i < j with two nested loops"),
            "sort_binary_search": ("sorting with binary search", "sort (value, index) pairs and binary-search the complement of each value"),
        },
        "aliases": {
            "hash_map": ["hash map", "hashmap", "hash table", "hashtable", "dictionary", "seen values", "complement map", "one-pass hash"],
            "sort_two_pointers": ["two pointers", "two-pointer", "two pointer", "two_pointers"],
            "brute_force": ["brute force", "brute-force", "double loop", "nested loop", "nested loops", "bruteforce"],
            "sort_binary_search": ["binary search", "binary-search", "bisect"],
        },
    },
    "T06": {
        "task_id": "T06_find_duplicate",
        "leetcode_ids": [287],
        "signature": "solve(nums)",
        "description": (
            "Task: write a Python function solve(nums) that returns the repeated value in nums. The argument "
            "nums is a list of n + 1 integers, where 1 <= n <= 10000, and every value lies between 1 and n "
            "inclusive. Exactly one value occurs more than once, and it may occur two or more times; every "
            "other value occurs at most once. Return the repeated value as an int."
        ),
        "bounds": {"n": [1, 10000]},
        "modes": {
            "hash_set": ("a hash set of seen values", "scan once and remember seen values in a set (or a boolean/count array) until one repeats"),
            "sort_adjacent": ("sorting and comparing neighbours", "sort a copy of the list and return the first value equal to its neighbour"),
            "floyd": ("Floyd's cycle detection", "treat i -> nums[i] as a linked list and run tortoise-and-hare to find the cycle entrance"),
            "value_binary_search": ("binary search on the value range", "binary-search the value range, counting how many elements are at most mid (pigeonhole)"),
            "index_marking": ("index marking in the input array", "mark visited values inside the list itself by negating or swapping entries at index value"),
        },
        "aliases": {
            "hash_set": ["hash set", "hashset", "seen set", "seen values", "set of seen"],
            "sort_adjacent": ["sorting", "sort and compare", "compare neighbours", "compare neighbors", "adjacent"],
            "floyd": ["floyd", "tortoise", "hare", "cycle detection", "tortoise and hare", "tortoise-and-hare"],
            "value_binary_search": ["binary search", "binary-search", "pigeonhole", "value range"],
            "index_marking": ["index marking", "negative marking", "negation", "mark visited", "cyclic sort", "in-place marking"],
        },
    },
    "T08": {
        "task_id": "T08_fibonacci",
        "leetcode_ids": [509],
        "signature": "solve(n)",
        "description": (
            "Task: write a Python function solve(n) that returns the n-th Fibonacci number as an exact "
            "Python int. The sequence is defined by F(0) = 0, F(1) = 1 and F(n) = F(n - 1) + F(n - 2) for "
            "n >= 2, so F(10) = 55. The argument n is an integer with 0 <= n <= 500, and the result must be "
            "exact for every n in that range."
        ),
        "bounds": {"n": [0, 500]},
        "modes": {
            "iteration": ("bottom-up iteration", "loop from the bottom up, keeping the last two values (or a table)"),
            "memo_recursion": ("memoised recursion", "recurse on F(n-1) + F(n-2) with a cache (dict or functools.lru_cache/cache)"),
            "matrix_power": ("matrix exponentiation", "raise the 2x2 matrix [[1,1],[1,0]] to the n-th power by repeated squaring"),
            "fast_doubling": ("fast doubling", "use F(2k) = F(k)(2F(k+1) - F(k)) and F(2k+1) = F(k)^2 + F(k+1)^2 over the bits of n"),
        },
        "aliases": {
            "iteration": ["bottom-up", "bottom up", "iteration", "iterative", "tabulation"],
            "memo_recursion": ["memoised", "memoized", "memoization", "memoisation", "memo", "lru_cache", "top-down", "top down"],
            "matrix_power": ["matrix exponentiation", "matrix power", "matrix", "matrix_pow", "mat_pow", "matpow", "mat_mult", "matmul"],
            "fast_doubling": ["fast doubling", "fast-doubling", "doubling"],
        },
    },
    "T10": {
        "task_id": "T10_connected_components",
        "leetcode_ids": [547, 323],
        "signature": "solve(n, edges)",
        "description": (
            "Task: write a Python function solve(n, edges) that returns the number of connected components "
            "of an undirected graph. The nodes are the integers 0 to n - 1, with 1 <= n <= 300. The argument "
            "edges is a list of pairs [u, v] with 0 <= u, v < n and u != v, each joining nodes u and v; "
            "0 <= len(edges) <= 1500 and no pair of nodes is joined twice. A node with no edges forms a "
            "component on its own."
        ),
        "bounds": {"n": [1, 300], "edges": [0, 1500]},
        "modes": {
            "bfs": ("breadth-first search (BFS)", "start a breadth-first traversal with a FIFO queue from every unvisited node and count the starts"),
            "dfs": ("depth-first search (DFS)", "start a depth-first traversal (recursion or an explicit LIFO stack) from every unvisited node and count the starts"),
            "union_find": ("union-find (disjoint set union)", "union the endpoints of every edge in a disjoint-set forest and count the roots"),
            "label_propagation": ("label propagation", "give every node its own label and repeatedly sweep the edges, lowering labels to the neighbour minimum until nothing changes"),
        },
        "aliases": {
            "bfs": ["breadth-first", "breadth first", "bfs"],
            "dfs": ["depth-first", "depth first", "dfs"],
            "union_find": ["union-find", "union find", "unionfind", "disjoint set", "disjoint-set", "dsu", "union_find"],
            "label_propagation": ["label propagation", "label-propagation", "propagate labels", "propagation"],
        },
    },
    "T11": {
        "task_id": "T11_longest_increasing_subsequence",
        "leetcode_ids": [300],
        "signature": "solve(nums)",
        "description": (
            "Task: write a Python function solve(nums) that returns the length of the longest strictly "
            "increasing subsequence of nums. A subsequence keeps the original order of the chosen elements "
            "but need not be contiguous, and strictly increasing means each chosen value is larger than the "
            "one before it. The argument nums is a list of integers with 1 <= len(nums) <= 1000 and every "
            "value between -10000 and 10000 inclusive."
        ),
        "bounds": {"n": [1, 1000], "value": [-10000, 10000]},
        "modes": {
            "quadratic_dp": ("quadratic dynamic programming", "dp[i] = 1 + max dp[j] over earlier j with nums[j] < nums[i], comparing all pairs"),
            "patience_bisect": ("patience sorting with binary search", "keep a tails array of the smallest tail per length and binary-search (bisect) where each value goes"),
            "fenwick": ("a Fenwick tree over compressed values", "compress values to ranks and query/update prefix maxima in a Fenwick (or segment) tree"),
        },
        "aliases": {
            "quadratic_dp": ["dynamic programming", "quadratic", "o(n^2)", "o(n2)", "dp array"],
            "patience_bisect": ["patience", "binary search", "bisect", "tails"],
            "fenwick": ["fenwick", "binary indexed tree", "bit", "segment tree", "coordinate compression", "compressed values"],
        },
    },
    "T13": {
        "task_id": "T13_merge_intervals",
        "leetcode_ids": [56],
        "signature": "solve(intervals)",
        "description": (
            "Task: write a Python function solve(intervals) that merges overlapping intervals. The argument "
            "intervals is a list of pairs [start, end] of integers with 0 <= start <= end <= 10000 and "
            "1 <= len(intervals) <= 1500, given in no particular order. Two intervals belong to the same "
            "merged interval when they overlap or touch, for example [1, 3] and [3, 5] merge into [1, 5]. "
            "Return the merged intervals as a list of [start, end] lists sorted by start, with no two of them "
            "overlapping or touching."
        ),
        "bounds": {"n": [1, 1500], "value": [0, 10000]},
        "modes": {
            "sort_sweep": ("sorting and a single sweep", "sort by start and sweep once, extending the last merged interval or starting a new one"),
            "interval_tree": ("an interval tree", "insert intervals into a tree of nodes keyed by start with a max-end field and merge through overlap queries"),
            "union_find": ("union-find over overlapping intervals", "union every pair of overlapping intervals in a disjoint-set forest and take min start / max end per root"),
        },
        "aliases": {
            "sort_sweep": ["sort and sweep", "sorting and a single sweep", "single sweep", "sweep line", "sweep", "sort by start"],
            "interval_tree": ["interval tree", "interval-tree", "augmented tree", "segment tree"],
            "union_find": ["union-find", "union find", "disjoint set", "disjoint-set", "dsu", "union_find"],
        },
    },
    "T14": {
        "task_id": "T14_top_k_frequent",
        "leetcode_ids": [347],
        "signature": "solve(nums, k)",
        "description": (
            "Task: write a Python function solve(nums, k) that returns the k values that occur most often in "
            "nums, as a list in any order. The argument nums is a list of integers with 1 <= len(nums) <= 10000 "
            "and every value between -10000 and 10000 inclusive; k is an integer between 1 and the number of "
            "distinct values in nums. The inputs are chosen so that the answer is unique: the k-th and "
            "(k+1)-th highest frequencies always differ."
        ),
        "bounds": {"n": [1, 10000], "value": [-10000, 10000]},
        "modes": {
            "sort_by_count": ("sorting by frequency", "count the values and sort the distinct values by count (or Counter.most_common() with no argument)"),
            "heap": ("a heap", "count the values and keep the k best in a heap (heapq push/pop of size k, heapq.nlargest or Counter.most_common(k))"),
            "bucket_sort": ("bucket sort by frequency", "count the values, put each value into bucket[count] for counts 0..n and read buckets from the highest"),
            "quickselect_counts": ("quickselect on the counts", "count the values and partition the distinct values by count around a pivot until the top k are separated"),
        },
        "aliases": {
            "sort_by_count": ["sorting by frequency", "sort by frequency", "sort by count", "sorting", "most_common()"],
            "heap": ["heap", "heapq", "priority queue", "nlargest", "min-heap", "max-heap"],
            "bucket_sort": ["bucket sort", "bucket-sort", "buckets", "bucket"],
            "quickselect_counts": ["quickselect", "quick select", "hoare", "partition"],
        },
    },
    "R1": {
        "task_id": "R1_non_overlapping_intervals",
        "leetcode_ids": [435],
        "signature": "solve(intervals)",
        "description": (
            "Task: write a Python function solve(intervals) that returns the minimum number of intervals that "
            "have to be removed so that no two of the remaining intervals overlap. The argument intervals is a "
            "list of pairs [start, end] of integers with start < end, 1 <= len(intervals) <= 1000 and every "
            "value between -50000 and 50000 inclusive. Two intervals that only touch, such as [1, 2] and "
            "[2, 3], count as non-overlapping. Return the count as an int."
        ),
        "bounds": {"n": [1, 1000], "value": [-50000, 50000]},
        "modes": {
            "greedy_end": ("the greedy earliest-finish rule", "sort by end (or by start keeping the smaller end) and greedily keep every interval that starts after the last kept end"),
            "dp_bisect": ("dynamic programming with binary search", "sort by end; dp over prefixes where keeping interval i jumps to the last compatible interval found by binary search"),
            "memo_recursion": ("memoised take-or-skip recursion", "recursive take-or-skip choice over intervals sorted by start, memoised on the index"),
            "dag_longest_path": ("a longest path in the interval graph", "build the compatibility DAG (i -> j when i ends before j starts) and take its longest path by DP over all pairs"),
        },
        "aliases": {
            "greedy_end": ["greedy", "earliest-finish", "earliest finish", "activity selection", "interval scheduling"],
            "dp_bisect": ["dynamic programming", "binary search", "bisect", "weighted interval"],
            "memo_recursion": ["memoised", "memoized", "memoization", "memo", "take-or-skip", "take or skip", "lru_cache", "top-down"],
            "dag_longest_path": ["longest path", "interval graph", "dag", "longest chain"],
        },
    },
    "R2": {
        "task_id": "R2_cycle_detection",
        "leetcode_ids": [684],
        "signature": "solve(n, edges)",
        "description": (
            "Task: write a Python function solve(n, edges) that returns True if an undirected graph contains a "
            "cycle and False otherwise. The nodes are the integers 0 to n - 1, with 1 <= n <= 1000. The argument "
            "edges is a list of pairs [u, v] with 0 <= u, v < n and u != v; 0 <= len(edges) <= 2000 and no pair "
            "of nodes is joined twice. The graph need not be connected, and a cycle in any part of it counts."
        ),
        "bounds": {"n": [1, 1000], "edges": [0, 2000]},
        "modes": {
            "dfs_parent": ("DFS with parent tracking", "depth-first traversal that reports a cycle on reaching a visited node other than the parent"),
            "bfs_parent": ("BFS with parent tracking", "breadth-first traversal with a FIFO queue that reports a cycle on reaching a visited node other than the parent"),
            "union_find": ("union-find", "union the endpoints of each edge; an edge whose endpoints already share a root closes a cycle"),
            "edge_count": ("the edge-count test per component", "find the components and report a cycle when some component has at least as many edges as nodes"),
        },
        "aliases": {
            "dfs_parent": ["depth-first", "depth first", "dfs"],
            "bfs_parent": ["breadth-first", "breadth first", "bfs"],
            "union_find": ["union-find", "union find", "disjoint set", "disjoint-set", "dsu", "union_find"],
            "edge_count": ["edge count", "edge-count", "edges versus nodes", "edges >= nodes", "count edges"],
        },
    },
    "R3": {
        "task_id": "R3_topological_order",
        "leetcode_ids": [210],
        "signature": "solve(n, prerequisites)",
        "description": (
            "Task: write a Python function solve(n, prerequisites) that orders n tasks numbered 0 to n - 1. "
            "Each pair [a, b] in the list prerequisites means that task b has to come before task a. Return a "
            "list that contains every task exactly once and respects every pair; if several orders are valid, "
            "any of them is accepted. If no valid order exists, return an empty list. Here 1 <= n <= 500, "
            "0 <= len(prerequisites) <= 2000, a != b, and no pair is repeated."
        ),
        "bounds": {"n": [1, 500], "edges": [0, 2000]},
        "modes": {
            "kahn": ("Kahn's in-degree queue", "compute in-degrees and repeatedly pop zero in-degree nodes from a queue, decrementing their successors"),
            "dfs_postorder": ("DFS post-order", "depth-first search with three colours; emit nodes in post-order and reverse, reporting a back edge as a cycle"),
            "source_removal": ("repeated source removal", "repeatedly rescan the remaining nodes for one with no remaining prerequisite and delete it, without a maintained queue"),
            "layering": ("longest-path layering", "assign each node its longest-path depth from the sources and output nodes sorted by depth"),
        },
        "aliases": {
            "kahn": ["kahn", "in-degree", "indegree", "in degree", "bfs", "breadth-first"],
            "dfs_postorder": ["post-order", "postorder", "post order", "dfs", "depth-first", "depth first", "three colours", "three colors"],
            "source_removal": ["source removal", "source-removal", "remove sources", "repeated removal"],
            "layering": ["layering", "longest path", "longest-path", "levels", "layer"],
        },
    },
    "R6": {
        "task_id": "R6_first_last_position",
        "leetcode_ids": [34],
        "signature": "solve(nums, target)",
        "description": (
            "Task: write a Python function solve(nums, target) that returns a list [first, last] holding the "
            "first and the last index at which target occurs in nums, or [-1, -1] if target does not occur. "
            "The argument nums is a list of integers sorted in non-decreasing order, with "
            "0 <= len(nums) <= 100000 and every value between -10**9 and 10**9 inclusive; target is an integer "
            "in the same range."
        ),
        "bounds": {"n": [0, 100000], "value": [-10**9, 10**9]},
        "modes": {
            "binary_search": ("a hand-written binary search", "hand-written lower/upper-bound binary searches (loops or recursion) over the index range"),
            "bisect_module": ("the bisect module", "bisect.bisect_left and bisect.bisect_right from the standard library"),
            "exponential_search": ("exponential search", "double a bound (1, 2, 4, ...) until it passes the target, then binary-search inside the bracket"),
        },
        "aliases": {
            "binary_search": ["binary search", "binary-search", "lower bound", "upper bound", "lower_bound", "upper_bound"],
            "bisect_module": ["bisect", "bisect_left", "bisect_right"],
            "exponential_search": ["exponential search", "exponential-search", "galloping", "doubling search"],
        },
    },
}


def all_modes() -> list[tuple[str, str]]:
    """Global (task, mode) list in a fixed order; index = global mode_idx used in seeds."""
    out = []
    for t in TASK_ORDER:
        for m in TASKS[t]["modes"]:
            out.append((t, m))
    return out


def display_name(task: str, mode: str) -> str:
    return TASKS[task]["modes"][mode][0]


def mode_description(task: str, mode: str) -> str:
    return TASKS[task]["modes"][mode][1]
