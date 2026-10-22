#!/usr/bin/env python3
"""Frozen spec cards of the panel-II units (candidate list II, plan 1.1-1.3): new wording with no algorithm or
data-structure word (units_spec.BANNED_BASE + every catalogue display name and alias, checked by unitbuild / the grep
audit), signature, bounds, catalogue (mode -> display name + one-line mechanism), alias lexicon (association mapping),
the mode of the dataset's own reference solution (fixes the neutral-noun padding length before any sampling), the
excluded-by-limit methods and the per-unit whitelist. Registered into units_spec.UNITS at import time."""

from __future__ import annotations

II_UNITS: dict[str, dict] = {
    "II1": {
        "unit_id": "II1_is_subsequence", "name": "is_subsequence", "source_ids": ["leetcodedataset:392"],
        "signature": "solve(s, t)", "args": ["s", "t"],
        "description": (
            "Task: write a Python function solve(s, t) that returns True when the characters of s appear in t in the "
            "same relative positions, possibly with other characters between them, and False otherwise. Both "
            "arguments are strings of lowercase English letters, with 0 <= len(s) <= 100 and 0 <= len(t) <= 50000. "
            "In other words, deleting zero or more characters of t without moving the remaining ones must be able to "
            "produce exactly s. For example, for s = \"abc\" and t = \"ahbgdc\" the answer is True, and for s = "
            "\"axc\" and t = \"ahbgdc\" the answer is False."),
        "bounds": {"len_s": [0, 100], "len_t": [0, 50000]},
        "dataset_reference_mode": "two_pointers",
        "modes": {
            "two_pointers": ("two pointers",
                             "walk an integer index through s (and/or through t) and advance the index into s on "
                             "every match while t is scanned once"),
            "iterator_consumption": ("iterator consumption",
                                     "create one iterator over t and test each character of s with `c in it` (or "
                                     "next() calls), so t is consumed up to each match"),
            "bisect_positions": ("binary search over per-letter position lists",
                                 "precompute for every letter the increasing list of its positions in t and, for "
                                 "each character of s, bisect for the first position after the previous match"),
        },
        "aliases": {
            "two_pointers": ["two pointers", "two-pointer", "two pointer", "pointer", "pointers", "greedy scan",
                             "index", "indices", "linear scan"],
            "iterator_consumption": ["iterator", "iter(", "next(", "consum", "generator", "all(c in"],
            "bisect_positions": ["binary search", "binary-search", "bisect", "positions list", "position lists",
                                 "index lists", "follow-up", "preprocess"],
        },
        "excluded_by_limit": ["lcs_dynamic_programming"],
        "whitelist": [],
    },
    "II2": {
        "unit_id": "II2_task_scheduler", "name": "task_scheduler", "source_ids": ["leetcodedataset:621"],
        "signature": "solve(tasks, n)", "args": ["tasks", "n"],
        "description": (
            "Task: write a Python function solve(tasks, n) that returns the least number of time units needed to "
            "finish every job. The argument tasks is a list of uppercase letters (\"A\" to \"Z\"), each letter being "
            "one job of that type, with 1 <= len(tasks) <= 10000, and n is an int with 0 <= n <= 100. In each time "
            "unit the machine runs exactly one job or stays idle, and two jobs of the same type must be separated by "
            "at least n time units. Jobs may run in any sequence; return the minimum total number of time units as an "
            "int. For example, for tasks = [\"A\", \"A\", \"A\", \"B\", \"B\", \"B\"] and n = 2 the answer is 8, and "
            "for the same tasks with n = 0 the answer is 6."),
        "bounds": {"len": [1, 10000], "n": [0, 100]},
        "dataset_reference_mode": "counting_formula",
        "modes": {
            "counting_formula": ("the frame-counting formula",
                                 "count each letter and return max(len(tasks), (max_count - 1) * (n + 1) + "
                                 "number_of_letters_with_max_count), or the equivalent idle-slot count"),
            "heap_simulation": ("a max-heap simulation with a cooldown queue",
                                "repeatedly pop the most frequent remaining types from a heap, run them, and push "
                                "them back after their cooldown (cycle by cycle or with a waiting queue)"),
            "sorted_count_simulation": ("a sorted-count simulation",
                                        "keep the counts, sort them every cycle, run the n + 1 most frequent types, "
                                        "and repeat until every count is zero"),
        },
        "aliases": {
            "counting_formula": ["formula", "math", "mathematical", "frame", "frames", "idle slots", "idle slot",
                                 "max count", "maximum frequency", "max frequency", "counting", "count of the most",
                                 "(max_count - 1)", "chunks"],
            "heap_simulation": ["heap", "max-heap", "max heap", "priority queue", "heapq", "cooldown queue",
                                "simulation with a heap", "simulate"],
            "sorted_count_simulation": ["sort the counts", "sorting the counts", "sorted counts", "sort",
                                        "sorting", "sorted"],
        },
        "excluded_by_limit": [],
        "whitelist": [],
    },
    "II3": {
        "unit_id": "II3_count_ones", "name": "count_ones", "source_ids": ["leetcodedataset:191"],
        "signature": "solve(x)", "args": ["x"],
        "description": (
            "Task: write a Python function solve(x) that returns how many of the base-2 digits of x are equal to 1. "
            "The argument x is an int with 0 <= x < 4294967296, so x is written with at most 32 digits in base 2. "
            "Return the count of 1 digits as an int. For example, for x = 11, which is 1011 in base 2, the answer is "
            "3; for x = 128 the answer is 1; and for x = 4294967293 the answer is 31."),
        "bounds": {"x": [0, 4294967295]},
        "dataset_reference_mode": "kernighan",
        "modes": {
            "library_count": ("a library population count",
                              "convert with bin(x) / format(x, 'b') and count the '1' characters, or call "
                              "int.bit_count()"),
            "kernighan": ("Kernighan's x & (x - 1) loop",
                          "repeatedly clear the lowest 1 digit with x &= x - 1 and count the iterations"),
            "shift_mask": ("a shift-and-test loop",
                           "test the lowest digit with x & 1 (or x % 2) and shift right (or halve) until x is 0, or "
                           "test all 32 positions"),
            "lookup_table": ("a byte lookup table",
                             "precompute the number of 1 digits of every value 0..255 and add the table entries of "
                             "the four bytes of x"),
        },
        "aliases": {
            "library_count": ["bin(", "bit_count", "bin(x).count", "count('1')", "count(\"1\")", "built-in",
                              "builtin", "library", "format(", "string conversion", "popcount"],
            "kernighan": ["kernighan", "brian kernighan", "n & (n - 1)", "n & (n-1)", "x & (x - 1)", "x & (x-1)",
                          "n&(n-1)", "x&(x-1)", "lowest set bit", "clear the lowest", "drop the lowest"],
            "shift_mask": ["shift", "shifting", "right shift", ">>", "& 1", "&1", "% 2", "mask", "masking",
                           "check each bit", "iterate over the bits", "loop over bits", "bit by bit"],
            "lookup_table": ["lookup table", "lookup", "look-up", "table", "precomputed", "precompute", "byte"],
        },
        "excluded_by_limit": [],
        "whitelist": ["library"],
    },
    "II4": {
        "unit_id": "II4_peak_index", "name": "peak_index", "source_ids": ["leetcodedataset:162"],
        "signature": "solve(nums)", "args": ["nums"],
        "description": (
            "Task: write a Python function solve(nums) that returns the index of any peak of nums. The argument nums "
            "is a list of integers with 1 <= len(nums) <= 100000, every value between -2147483648 and 2147483647, "
            "and nums[i] != nums[i + 1] for every valid i. A peak is a position whose value is strictly greater than "
            "the values next to it; positions outside the list count as minus infinity, so an end of the list only "
            "has to beat its single neighbour. Return one peak index as an int; any peak is accepted. For example, "
            "for nums = [1, 2, 3, 1] the answer is 2, and for nums = [1, 2, 1, 3, 5, 6, 4] the answer 1 and the "
            "answer 5 are both accepted."),
        "bounds": {"n": [1, 100000]},
        "dataset_reference_mode": "binary_search_slope",
        "modes": {
            "binary_search_slope": ("binary search on the slope",
                                    "keep a range [lo, hi], compare nums[mid] with nums[mid + 1] and move toward the "
                                    "larger neighbour, O(log n)"),
            "linear_scan": ("a linear scan for the first descent",
                            "walk i = 0, 1, ... and return the first i whose value exceeds the next one (or the "
                            "last index)"),
            "index_of_max": ("the index of the maximum",
                             "return the position of the global maximum (nums.index(max(nums)) or an argmax loop); "
                             "the maximum is always a peak"),
        },
        "aliases": {
            "binary_search_slope": ["binary search", "binary-search", "bisection", "o(log n)", "logarithmic",
                                    "halving", "divide and conquer"],
            "linear_scan": ["linear scan", "linear search", "scan", "iterate", "first descent", "one pass",
                            "o(n)", "brute force"],
            "index_of_max": ["maximum", "max(", "argmax", "largest element", "global max", "index(max"],
        },
        "excluded_by_limit": [],
        "whitelist": [],
    },
    "II5": {
        "unit_id": "II5_all_arrangements", "name": "all_arrangements", "source_ids": ["leetcodedataset:46"],
        "signature": "solve(nums)", "args": ["nums"],
        "description": (
            "Task: write a Python function solve(nums) that returns every possible arrangement of the values of nums. "
            "The argument nums is a list of distinct integers with 1 <= len(nums) <= 7 and every value between -10 "
            "and 10. Return a list that contains each arrangement exactly once, where an arrangement is a list that "
            "uses every value of nums exactly once; the arrangements may appear in any sequence. For example, for "
            "nums = [1, 2, 3] the answer contains the six lists [1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 1, 2] "
            "and [3, 2, 1], and for nums = [0, 1] it contains [0, 1] and [1, 0]."),
        "bounds": {"n": [1, 7]},
        "dataset_reference_mode": "backtracking_used",
        "modes": {
            "backtracking_used": ("backtracking with used flags",
                                  "build one arrangement position by position by choosing an unused value (used "
                                  "flags, a set, or the list of remaining values), recursing, and undoing the choice"),
            "swap_backtracking": ("swap-based backtracking",
                                  "fix position i by swapping each later value into it, recurse on i + 1, and swap "
                                  "back"),
            "library_permutations": ("itertools.permutations",
                                     "call itertools.permutations and convert each tuple to a list"),
            "heaps_algorithm": ("Heap's algorithm",
                                "produce each arrangement from the previous one by a single swap chosen by Heap's "
                                "parity rule (recursive or with a counter array)"),
            "insertion_build": ("iterative insertion",
                                "start from [[]] and, for each value, insert it at every position of every partial "
                                "arrangement"),
        },
        "aliases": {
            "backtracking_used": ["backtracking", "backtrack", "dfs", "depth-first", "depth first", "used array",
                                  "visited", "recursion", "recursive", "choose"],
            "swap_backtracking": ["swap", "swapping", "in-place swap", "swaps"],
            "library_permutations": ["itertools", "itertools.permutations", "library", "built-in", "builtin"],
            "heaps_algorithm": ["heap's algorithm", "heap's", "heaps algorithm", "heap algorithm"],
            "insertion_build": ["insertion", "insert", "inserting", "iterative", "bfs", "build up"],
        },
        "excluded_by_limit": [],
        "whitelist": ["library"],
    },
    "II6": {
        "unit_id": "II6_bracket_matching", "name": "bracket_matching", "source_ids": ["leetcodedataset:20"],
        "signature": "solve(s)", "args": ["s"],
        "description": (
            "Task: write a Python function solve(s) that returns True when the brackets in s are properly matched "
            "and nested, and False otherwise. The argument s is a string with 1 <= len(s) <= 4000 made only of the "
            "six characters ( ) [ ] { }, and no group is nested more than 400 levels deep. The string is properly "
            "matched when every opening character is closed by a closing character of the same kind, groups close "
            "in the reverse of the sequence in which they opened, and no closing character appears without an "
            "opener. For example, for s = \"()[]{}\" the answer is True, for s = \"(]\" it is False, and for s = "
            "\"([{}])\" it is True."),
        "bounds": {"len": [1, 4000], "depth": [0, 400]},
        "dataset_reference_mode": "stack",
        "modes": {
            "stack": ("a stack of open brackets",
                      "push each opener (or its expected closer) and, on a closer, pop and check that it matches"),
            "replace_pairs": ("repeated removal of matched pairs",
                              "repeatedly delete every '()', '[]' and '{}' (str.replace) until nothing changes, then "
                              "check that the string is empty"),
            "recursive_descent": ("recursive descent parsing",
                                  "parse with a recursive function that consumes one balanced group and returns the "
                                  "position after it"),
        },
        "aliases": {
            "stack": ["stack", "lifo", "push", "pop", "deque", "last-in"],
            "replace_pairs": ["replace", "replacing", "remove pairs", "removing pairs", "repeatedly remove",
                              "elimination", "eliminate"],
            "recursive_descent": ["recursive descent", "recursion", "recursive", "parser", "parsing", "grammar"],
        },
        "excluded_by_limit": [],
        "whitelist": [],
    },
    "II7": {
        "unit_id": "II7_combine_in_place", "name": "combine_in_place", "source_ids": ["leetcodedataset:88"],
        "signature": "solve(nums1, m, nums2, n)", "args": ["nums1", "m", "nums2", "n"],
        "description": (
            "Task: write a Python function solve(nums1, m, nums2, n) that combines two non-decreasing lists inside "
            "nums1. The argument nums1 is a list of length m + n whose first m values are non-decreasing and whose "
            "last n entries are 0 placeholders; nums2 is a non-decreasing list of n integers; 0 <= m <= 50000, 0 <= "
            "n <= 50000, 1 <= m + n, and every value lies between -1000000000 and 1000000000. Rewrite the entries of "
            "nums1 so that it holds all m + n values in non-decreasing sequence; the function must modify the list "
            "nums1 itself and return None. For example, for nums1 = [1, 2, 3, 0, 0, 0], m = 3, nums2 = [2, 5, 6] and "
            "n = 3, nums1 becomes [1, 2, 2, 3, 5, 6]."),
        "bounds": {"m": [0, 50000], "n": [0, 50000]},
        "dataset_reference_mode": "backward_fill",
        "modes": {
            "forward_copy": ("a forward two-way walk into a new list",
                             "walk both lists from the front into a new list, then copy it back into nums1"),
            "concat_sort": ("concatenation and a library sort",
                            "write nums2 into the placeholder tail and call nums1.sort() (or assign sorted(...))"),
            "heapq_merge": ("heapq.merge", "assign list(heapq.merge(nums1[:m], nums2)) to nums1[:]"),
            "backward_fill": ("an in-place fill from the back",
                              "fill nums1 from position m + n - 1 downwards, each time taking the larger of the two "
                              "current last values"),
        },
        "aliases": {
            "forward_copy": ["two pointers", "two-pointer", "new list", "auxiliary", "extra array", "copy back",
                             "from the front", "forward"],
            "concat_sort": ["sort", "sorting", "sorted", "concatenate", "concatenation", "timsort"],
            "heapq_merge": ["heapq.merge", "heapq", "heap"],
            "backward_fill": ["from the back", "from the end", "backwards", "backward", "reverse", "three pointers",
                              "in-place", "in place"],
        },
        "excluded_by_limit": [],
        "whitelist": [],
    },
    "II8": {
        "unit_id": "II8_nearest_k_points", "name": "nearest_k_points", "source_ids": ["leetcodedataset:973"],
        "signature": "solve(points, k)", "args": ["points", "k"],
        "description": (
            "Task: write a Python function solve(points, k) that returns the k points closest to the origin. The "
            "argument points is a list of 1 to 20000 pairs [x, y] of integers with -10000 <= x, y <= 10000, and k is "
            "an int with 1 <= k <= len(points). Distance is the usual Euclidean distance to (0, 0). Return a list of "
            "k of the given pairs whose distances are the k smallest, in any sequence; when several points are tied "
            "at the boundary distance, any of them may be chosen. For example, for points = [[1, 3], [-2, 2]] and "
            "k = 1 the answer is [[-2, 2]], and for points = [[3, 3], [5, -1], [-2, 4]] and k = 2 the answer is "
            "[[3, 3], [-2, 4]] in either sequence."),
        "bounds": {"n": [1, 20000]},
        "dataset_reference_mode": "full_sort",
        "modes": {
            "full_sort": ("sorting by distance", "sort all points by squared (or plain) distance and take the first "
                                                 "k"),
            "maxheap_k": ("a size-k max-heap", "keep the k closest points seen so far in a max-heap of negated "
                                              "distances, pushing and popping while scanning"),
            "nsmallest": ("heapq.nsmallest", "call heapq.nsmallest(k, points, key=distance)"),
            "quickselect": ("quickselect", "partition the points around a pivot distance until the first k "
                                           "positions hold the k closest"),
        },
        "aliases": {
            "full_sort": ["sort", "sorting", "sorted"],
            "maxheap_k": ["max-heap", "max heap", "heap of size k", "size-k heap", "priority queue", "heappush",
                          "heap"],
            "nsmallest": ["nsmallest", "heapq.nsmallest", "heapify"],
            "quickselect": ["quickselect", "quick select", "quick-select", "partition", "hoare", "lomuto",
                            "selection algorithm", "divide and conquer"],
        },
        "excluded_by_limit": [],
        "whitelist": [],
    },
}
