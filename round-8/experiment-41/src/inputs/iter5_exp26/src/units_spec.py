#!/usr/bin/env python3
"""Frozen spec cards of the panel-B units (candidate list B, plan section 4): new wording, signature, bounds,
catalogue (mode -> display name + one-line mechanism), alias lexicon (association mapping and the grep audit) and the
mode implemented by the dataset's own reference solution (it fixes the neutral-noun length before any sampling).

Every description is checked by tests/test_cpu.py against BANNED_WORDS (whole word, case-insensitive); words that
the I/O itself needs are whitelisted per unit and logged in units/<u>/build_report.json.
"""

from __future__ import annotations

import re

from cfg5 import FORMAT_LINE, cap_first

BANNED_BASE = ["sort", "sorted", "order", "heap", "priority", "queue", "stack", "hash", "map", "dictionary", "set",
               "tree", "graph", "node", "vertex", "edge", "search", "binary", "partition", "pivot", "greedy",
               "recursion", "recursive", "dynamic programming", "xor", "bit", "union", "merge", "two pointers",
               "window", "newton", "prim", "kruskal", "backtrack", "mask"]

UNIT_ORDER = ["B1", "B2", "B3", "B4", "B5", "B6", "B7"]
RESERVES = ["B8", "B9"]

UNITS: dict[str, dict] = {
    "B1": {
        "unit_id": "B1_missing_number", "name": "missing_number", "source_ids": ["leetcodedataset:268"],
        "signature": "solve(nums)", "args": ["nums"],
        "description": (
            "Task: write a Python function solve(nums) that returns the one missing number. The argument nums is a "
            "list of n distinct integers, where 1 <= n <= 100000, and every value lies between 0 and n inclusive. "
            "Exactly one integer from 0 to n does not appear in nums; return that integer as an int. For example, "
            "for nums = [3, 0, 1] the answer is 2, and for nums = [0, 1] the answer is 2."),
        "bounds": {"n": [1, 100000]},
        "dataset_reference_mode": "xor_fold",
        "modes": {
            "arithmetic_sum": ("the arithmetic-series sum formula",
                               "compute the expected total 0 + 1 + ... + n (closed formula or sum(range)) and subtract "
                               "the actual sum of nums"),
            "xor_fold": ("an XOR fold over indices and values",
                         "XOR together every number 0..n and every value of nums; equal pairs cancel and the missing "
                         "number remains"),
            "sort_scan": ("sorting and a linear scan",
                          "sort the values and walk them until position i holds a value different from i"),
            "sort_binary_search": ("sorting and binary search",
                                   "sort the values and binary-search the first position i whose value differs from "
                                   "i"),
            "hash_set": ("a hash set of the values",
                         "put the values in a set (or a boolean presence array, or a set difference with range(n + 1)) "
                         "and report the number that is absent"),
        },
        "aliases": {
            "arithmetic_sum": ["arithmetic series", "arithmetic-series", "gauss", "sum formula", "summation formula",
                               "expected sum", "n*(n+1)/2", "n * (n + 1) / 2", "n*(n+1)//2", "n * (n + 1) // 2",
                               "sum of the first", "sum of all numbers", "total sum", "math formula",
                               "mathematical formula", "sum difference", "sum"],
            "xor_fold": ["xor", "exclusive or", "exclusive-or", "bitwise", "bit manipulation", "^"],
            "sort_scan": ["sort and scan", "sorting and scanning", "sorting", "sort the", "sorted"],
            "sort_binary_search": ["binary search", "binary-search", "bisect"],
            "hash_set": ["hash set", "hashset", "hash table", "hashtable", "set of", "a set", "lookup set",
                         "boolean array", "presence array", "visited array", "seen array", "set difference",
                         "set"],
        },
        "excluded_by_limit": ["list_membership_scan"],
        "whitelist": [],
    },
    "B2": {
        "unit_id": "B2_single_number", "name": "single_number", "source_ids": ["leetcodedataset:136"],
        "signature": "solve(nums)", "args": ["nums"],
        "description": (
            "Task: write a Python function solve(nums) that returns the value that occurs exactly once in nums. The "
            "argument nums is a list of integers with 1 <= len(nums) <= 100001, and every value lies between -30000 "
            "and 30000 inclusive. Every value in nums occurs exactly twice except one value, which occurs exactly "
            "once; return that value as an int. For example, for nums = [4, 1, 2, 1, 2] the answer is 4, and for "
            "nums = [7] the answer is 7."),
        "bounds": {"n": [1, 100001], "value": [-30000, 30000]},
        "dataset_reference_mode": "xor_fold",
        "modes": {
            "xor_fold": ("an XOR fold", "XOR all values together; values that occur twice cancel"),
            "hash_count": ("a hash map of counts",
                           "count occurrences in a dict or Counter (or toggle membership in a set) and return the "
                           "value seen once"),
            "set_sum_identity": ("the set-sum identity",
                                 "return 2 * sum(set(nums)) - sum(nums), since every paired value is counted twice"),
            "sort_pair_scan": ("sorting and pairwise comparison",
                               "sort the values and compare neighbours two at a time until a pair does not match"),
        },
        "aliases": {
            "xor_fold": ["xor", "exclusive or", "exclusive-or", "bitwise", "bit manipulation", "^"],
            "hash_count": ["hash map", "hashmap", "hash table", "hashtable", "dictionary", "counter", "frequency",
                           "count", "counting", "toggle", "dict"],
            "set_sum_identity": ["2 * sum", "2*sum", "twice the sum", "sum of the set", "sum of set", "set sum",
                                 "sum of unique", "sum of distinct", "math", "sum"],
            "sort_pair_scan": ["sorting", "sort", "sorted", "pairwise", "adjacent pairs"],
        },
        "excluded_by_limit": ["list_count_scan"],
        "whitelist": [],
    },
    "B3": {
        "unit_id": "B3_mst_weight", "name": "mst_weight", "source_ids": ["leetcodedataset:1135",
                                                                          "leetcodedataset:1584"],
        "signature": "solve(n, roads)", "args": ["n", "roads"],
        "description": (
            "Task: write a Python function solve(n, roads) that returns the smallest total cost of a choice of roads "
            "that links all cities. There are n cities numbered 0 to n - 1, where 1 <= n <= 500. The argument roads "
            "is a list of at most 10000 triples [u, v, w], each meaning that a two-way road between cities u and v "
            "(u != v) can be built for cost w, where 0 <= w <= 100000; several roads may join the same two cities. "
            "Choose roads so that every city can reach every other city through chosen roads, at the smallest "
            "possible total cost, and return that total as an int. If the cities cannot all be linked, return -1. "
            "For example, for n = 3 and roads = [[0, 1, 5], [0, 2, 6], [1, 2, 1]] the answer is 6."),
        "bounds": {"n": [1, 500], "m": [0, 10000], "w": [0, 100000]},
        "dataset_reference_mode": "kruskal",
        "modes": {
            "kruskal": ("Kruskal's algorithm",
                        "take roads in increasing cost (sorted or from a heap of all roads) and keep a road when it "
                        "joins two different components (union-find or another component check)"),
            "prim_heap": ("Prim's algorithm with a heap",
                          "grow one connected component from a start city, always adding the cheapest road leaving "
                          "it, found with a heap of frontier roads"),
            "prim_array": ("Prim's algorithm with an array scan",
                           "grow one component from a start city, keeping the cheapest known cost per city in an "
                           "array and scanning all cities each round to pick the next one (O(n^2))"),
            "boruvka": ("Boruvka's algorithm",
                        "in rounds, find the cheapest road leaving every component and add all of them, merging "
                        "components until one remains"),
        },
        "aliases": {
            "kruskal": ["kruskal", "kruskal's", "union-find", "union find", "disjoint set", "disjoint-set", "dsu"],
            "prim_heap": ["prim's algorithm with a heap", "prim with a heap", "heap-based prim", "lazy prim",
                          "priority queue", "prim", "prim's"],
            "prim_array": ["prim's algorithm with an array", "array-based prim", "dense prim", "o(n^2) prim",
                           "o(v^2)", "adjacency matrix"],
            "boruvka": ["boruvka", "borůvka", "sollin"],
        },
        "excluded_by_limit": [],
        "whitelist": [],
    },
    "B4": {
        "unit_id": "B4_integer_sqrt", "name": "integer_sqrt", "source_ids": ["leetcodedataset:69"],
        "signature": "solve(x)", "args": ["x"],
        "description": (
            "Task: write a Python function solve(x) that returns the integer square root of x, that is, the largest "
            "integer r with r * r <= x. The argument x is an integer with 0 <= x <= 2147483647. Return r as an int. "
            "For example, for x = 8 the answer is 2, for x = 16 the answer is 4, and for x = 0 the answer is 0."),
        "bounds": {"x": [0, 2147483647]},
        "dataset_reference_mode": "binary_search",
        "modes": {
            "binary_search": ("binary search on the answer",
                              "binary-search r in a range such as [0, x], comparing mid * mid (or mid against x // "
                              "mid) with x"),
            "newton": ("Newton's method",
                       "iterate r <- (r + x // r) // 2 (or the float version) from an initial guess until it stops "
                       "decreasing"),
            "bit_by_bit": ("bit-by-bit construction",
                           "build r one bit at a time from the highest bit down, keeping a bit when the square stays "
                           "<= x (digit-by-digit square root)"),
            "library_isqrt": ("math.isqrt", "call math.isqrt(x)"),
            "float_sqrt": ("a floating-point square root",
                           "compute math.sqrt(x) or x ** 0.5 in floating point and truncate (optionally with a "
                           "correction step)"),
            "linear_scan": ("a linear scan of candidates",
                            "try r = 0, 1, 2, ... (or count down) until (r + 1) * (r + 1) > x"),
        },
        "aliases": {
            "binary_search": ["binary search", "binary-search", "bisection", "bisect"],
            "newton": ["newton", "newton's", "newton-raphson", "heron", "babylonian"],
            "bit_by_bit": ["bit-by-bit", "bit by bit", "digit-by-digit", "digit by digit", "bit manipulation",
                           "bitwise"],
            "library_isqrt": ["math.isqrt", "isqrt"],
            "float_sqrt": ["math.sqrt", "** 0.5", "**0.5", "floating-point", "floating point", "pow(x, 0.5)",
                           "built-in sqrt", "sqrt function", "exponent"],
            "linear_scan": ["linear scan", "linear search", "brute force", "brute-force", "iterate", "incremental"],
        },
        "excluded_by_limit": [],
        "whitelist": [],
    },
    "B5": {
        "unit_id": "B5_all_subsets", "name": "all_subsets", "source_ids": ["leetcodedataset:78"],
        "signature": "solve(nums)", "args": ["nums"],
        "description": (
            "Task: write a Python function solve(nums) that returns every possible selection of elements of nums, "
            "including the empty selection and nums itself. The argument nums is a list of distinct integers with "
            "1 <= len(nums) <= 10, and every value lies between -10 and 10 inclusive. Return a list of lists: each "
            "inner list holds the chosen values, and each possible selection appears exactly once. The inner lists "
            "and the values inside them may be returned in any arrangement. For example, for nums = [1, 2] one "
            "correct answer is [[], [1], [2], [1, 2]]."),
        "bounds": {"n": [1, 10], "value": [-10, 10]},
        "dataset_reference_mode": "backtracking",
        "modes": {
            "backtracking": ("backtracking",
                             "extend one shared partial selection element by element (append, explore, pop), "
                             "recursively or with an explicit stack, emitting a copy at each step"),
            "bitmask_enumeration": ("bitmask enumeration",
                                    "loop over the integers 0 .. 2^n - 1 and build each selection from the set bits "
                                    "of the counter"),
            "iterative_doubling": ("iterative doubling of the result list",
                                   "start from [[]] and, for each element, append a copy of every existing selection "
                                   "extended by that element (cascading)"),
            "itertools_combinations": ("itertools.combinations",
                                       "call itertools.combinations(nums, r) for every size r = 0..n"),
        },
        "aliases": {
            "backtracking": ["backtracking", "backtrack", "depth-first", "dfs", "recursion", "recursive",
                             "include/exclude", "include or exclude"],
            "bitmask_enumeration": ["bitmask", "bit mask", "bitmasks", "binary representation", "bits", "bitwise",
                                    "bit manipulation", "binary counting"],
            "iterative_doubling": ["iterative", "cascading", "doubling", "iteratively", "build up", "incremental"],
            "itertools_combinations": ["itertools", "combinations", "itertools.combinations", "chain.from_iterable"],
        },
        "excluded_by_limit": [],
        "whitelist": [],
    },
    "B6": {
        "unit_id": "B6_valid_anagram", "name": "valid_anagram", "source_ids": ["leetcodedataset:242"],
        "signature": "solve(s, t)", "args": ["s", "t"],
        "description": (
            "Task: write a Python function solve(s, t) that returns True if the string t is a rearrangement of the "
            "letters of the string s, and False otherwise. Both strings consist only of lowercase English letters, "
            "with 1 <= len(s) <= 50000 and 1 <= len(t) <= 50000. The string t is a rearrangement of s when both "
            "strings use every letter the same number of times. Return a bool. For example, solve('listen', "
            "'silent') is True and solve('rat', 'car') is False."),
        "bounds": {"len": [1, 50000]},
        "dataset_reference_mode": "hash_count",
        "modes": {
            "sort_compare": ("sorting both strings", "sort the letters of both strings and compare the results"),
            "hash_count": ("a hash map of letter counts",
                           "count letters in a dict or Counter (one or two of them) and compare or decrement the "
                           "counts"),
            "fixed_count_array": ("a fixed 26-slot count array",
                                  "keep 26 integer counters indexed by ord(c) - ord('a') and compare or decrement "
                                  "them"),
        },
        "aliases": {
            "sort_compare": ["sorting", "sort", "sorted", "sort both"],
            "hash_count": ["hash map", "hashmap", "hash table", "hashtable", "dictionary", "counter", "dict",
                           "frequency map", "collections.counter"],
            "fixed_count_array": ["26", "count array", "array of size 26", "fixed-size array", "fixed size array",
                                  "ord(", "character array", "frequency array", "array of counts", "counting array"],
        },
        "candidate_extra_mode": {
            "alphabet_count_scan": ("str.count per letter",
                                    "for each letter of the alphabet (or of s), compare s.count(c) with t.count(c)")},
        "excluded_by_limit": ["remove_one_by_one"],
        "whitelist": [],
    },
    "B7": {
        "unit_id": "B7_count_inversions", "name": "count_inversions",
        "source_ids": ["kodcode_algorithmic/thealgorithms_python/xlcost_python rows mentioning inversion counting"],
        "signature": "solve(nums)", "args": ["nums"],
        "description": (
            "Task: write a Python function solve(nums) that returns the number of pairs of positions (i, j) with "
            "i < j and nums[i] > nums[j]. The argument nums is a list of integers with 1 <= len(nums) <= 20000, and "
            "every value lies between -10**9 and 10**9 inclusive; values may repeat, and a pair of equal values "
            "does not count. Return the number of such pairs as an int. For example, for nums = [3, 1, 2] the "
            "answer is 2, and for nums = [2, 2, 1] the answer is 2."),
        "bounds": {"n": [1, 20000], "value": [-10**9, 10**9]},
        "dataset_reference_mode": "merge_sort_count",
        "modes": {
            "merge_sort_count": ("merge sort with counting",
                                 "divide the list in halves, count pairs across the halves while merging them in "
                                 "increasing value"),
            "fenwick_tree": ("a Fenwick tree",
                             "compress values to ranks and scan, querying and updating a binary indexed tree of "
                             "counts (i & -i steps)"),
            "segment_tree": ("a segment tree",
                             "compress values to ranks and scan, querying and updating a segment tree of counts"),
            "sorted_insertion_bisect": ("sorted insertion with bisect",
                                        "keep a sorted list of the values seen so far, using bisect to count larger "
                                        "ones and insort (or list.insert) to add each value"),
        },
        "aliases": {
            "merge_sort_count": ["merge sort", "mergesort", "merge-sort", "divide and conquer", "divide-and-conquer",
                                 "merge"],
            "fenwick_tree": ["fenwick", "binary indexed tree", "bit tree", "binary-indexed tree", "bit"],
            "segment_tree": ["segment tree", "segment-tree"],
            "sorted_insertion_bisect": ["bisect", "insort", "sorted list", "sortedlist", "binary insertion",
                                        "insertion"],
        },
        "excluded_by_limit": ["brute_force_pairs"],
        "whitelist": [],
    },
}


def spec_text(u: str) -> str:
    return cap_first(UNITS[u]["description"]) + "\n\n" + cap_first(FORMAT_LINE)


def catalogue(u: str) -> list[str]:
    return list(UNITS[u]["modes"])


def display_name(u: str, m: str) -> str:
    return UNITS[u]["modes"][m][0]


def banned_words(u: str) -> list[str]:
    spec = UNITS[u]
    words = set(BANNED_BASE)
    for m, (dn, _) in spec["modes"].items():
        words.add(dn.lower())
        words.add(re.sub(r"^(a|an|the)\s+", "", dn.lower()))
        words.add(m.replace("_", " "))
    for aa in spec["aliases"].values():
        for a in aa:
            if re.search(r"[a-z]", a.lower()) and len(a) > 2:
                words.add(a.lower())
    return sorted(w for w in words if w not in set(spec.get("whitelist", [])))


def grep_banned(u: str, text: str) -> list[str]:
    hits = []
    low = text.lower()
    for w in banned_words(u):
        pat = r"(?<![a-z0-9_])" + re.escape(w) + r"(?![a-z0-9_])"
        if re.search(pat, low):
            hits.append(w)
    return hits


def map_answer(u: str, answer: str, modes: list[str] | None = None) -> str:
    """Association answer -> mode via the alias lexicon (longest matching alias wins; unmapped -> 'other')."""
    low = answer.lower()
    best, best_len = "other", 0
    spec = UNITS[u]
    for m in (modes or list(spec["modes"])):
        cands = list(spec["aliases"].get(m, [])) + [spec["modes"][m][0]]
        for a in cands:
            al = a.lower()
            if not al:
                continue
            if re.search(r"[a-z]", al):
                pat = r"(?<![a-z0-9_])" + re.escape(al) + r"(?![a-z0-9_])"
                hit = re.search(pat, low) is not None
            else:
                hit = al in low
            if hit and len(al) > best_len:
                best, best_len = m, len(al)
    return best
