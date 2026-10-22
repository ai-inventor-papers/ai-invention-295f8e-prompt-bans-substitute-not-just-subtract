#!/usr/bin/env python3
"""Frozen spec cards of the panel-I units (candidate list I, plan S1a): new wording, signature, bounds, catalogue
(mode -> display name + one-line mechanism), alias lexicon (association mapping and the grep audit), the mode of the
dataset's own reference solution (it fixes the neutral-noun padding before any sampling), banned words and the
excluded brute force that the size limits rule out.

Source rows: art_j3Rm_lr2nzR6 leetcodedataset (problem text + reference solution) for every slug.
Every description is grep-audited (src/prompts6.py) against banned_words(u) (whole word, case-insensitive); words the
I/O itself needs are whitelisted per unit and logged (I7 'base-2 representation', I12 'greatest common divisor').
"""

from __future__ import annotations

import re

from cfg6 import FORMAT_LINE, cap_first

BANNED_BASE = ["hash", "set", "dictionary", "map", "counter", "heap", "queue", "stack", "sort", "sorted", "pointer",
               "pointers", "binary search", "bisect", "bucket", "union", "find", "graph", "tree", "cycle", "fast",
               "slow", "prefix", "suffix", "dynamic programming", "greedy", "kadane", "popcount", "bitwise", "xor",
               "euclid", "partition", "swap", "marking",
               # iteration-5 BANNED_BASE additions kept for safety (none is needed by any I/O below)
               "search", "binary", "bit", "bits", "window", "recursion", "recursive", "merge", "mask", "priority",
               "two pointers", "pivot", "node", "edge"]

UNIT_ORDER = ["I1", "I2", "I3", "I4", "I5", "I6", "I7", "I8", "I9", "I10"]
RESERVES = ["I11", "I12"]

UNITS: dict[str, dict] = {
    "I1": {
        "unit_id": "I1_longest_consecutive", "slug": "longest-consecutive-sequence",
        "source_ids": ["leetcodedataset:128"], "signature": "solve(nums)", "args": ["nums"], "checker": "exact",
        "description": (
            "Task: write a Python function solve(nums) that returns the length of the longest run of consecutive "
            "integers whose values all occur in nums. The argument nums is a list of at most 30000 ints, and every "
            "value lies between -10**9 and 10**9 inclusive; values may repeat and appear in any position. A run of "
            "length k is a group of k distinct values v, v + 1, ..., v + k - 1 that all occur in nums. Return the "
            "largest such k as an int, or 0 when nums is empty. For example, for nums = [100, 4, 200, 1, 3, 2] the "
            "answer is 4, and for nums = [0, 3, 7, 2, 5, 8, 4, 6, 0, 1] the answer is 9."),
        "bounds": {"n": [0, 30000], "value": [-10 ** 9, 10 ** 9]},
        "dataset_reference_mode": "set_remove_expand",
        "modes": {
            "set_start_walk": ("a hash set with run-start walks",
                               "store the values in a set and, from every value whose predecessor is absent, count "
                               "upward while the next value is present"),
            "set_remove_expand": ("a hash set with removal while expanding",
                                  "store the values in a set, then repeatedly take a value and remove its neighbours "
                                  "from the set while expanding the run, recording each run's length"),
            "sort_scan": ("sorting and a linear scan",
                          "sort the distinct values and scan them, extending the current run while each value is one "
                          "more than the previous one"),
            "boundary_map": ("a hash map of run lengths at run ends",
                             "insert values one by one into a dict, join the runs that end at v - 1 and start at "
                             "v + 1, and store the new run length at both ends"),
            "union_find": ("union-find over neighbouring values",
                           "make every value a disjoint-set element, join v with v + 1 when both occur, and return "
                           "the size of the largest component"),
        },
        "aliases": {
            "set_start_walk": ["run-start", "start of a sequence", "start of each sequence", "sequence start",
                               "only start counting", "num - 1 not in", "x - 1 not in", "predecessor"],
            "set_remove_expand": ["removal", "remove elements", "removing", "expand in both directions",
                                  "expand outward", "both directions", "pop from the set"],
            "sort_scan": ["sorting", "sort the", "sorted", "sort and scan", "sort then scan"],
            "boundary_map": ["boundary", "boundaries", "endpoints", "run lengths at", "length at both ends",
                             "hash map of lengths", "dictionary of lengths", "interval merging"],
            "union_find": ["union-find", "union find", "disjoint set", "disjoint-set", "dsu", "connected components"],
        },
        "excluded_by_limit": ["list_membership_scan"],
        "whitelist": [],
    },
    "I2": {
        "unit_id": "I2_group_anagrams", "slug": "group-anagrams", "source_ids": ["leetcodedataset:49"],
        "signature": "solve(strs)", "args": ["strs"], "checker": "groups",
        "description": (
            "Task: write a Python function solve(strs) that groups together the words that are anagrams of one "
            "another. The argument strs is a list of between 1 and 20000 strings; each string has length 0 to 30 "
            "and consists only of lowercase English letters. Two words belong to the same group exactly when one "
            "can be turned into the other by rearranging its letters. Return a list of groups, where each group is "
            "a list holding every word of its group (repeated words are kept). The groups, and the words inside a "
            "group, may be returned in any order. For example, for strs = ['eat', 'tea', 'tan', 'ate', 'nat', "
            "'bat'] one valid answer is [['bat'], ['nat', 'tan'], ['ate', 'eat', 'tea']]."),
        "bounds": {"n": [1, 20000], "length": [0, 30]},
        "dataset_reference_mode": "sorted_key",
        "modes": {
            "sorted_key": ("a hash map keyed by the sorted word",
                           "use the word's letters in sorted order (a joined string or a tuple) as a dict key and "
                           "append each word to its key's list"),
            "count_key": ("a hash map keyed by letter counts",
                          "build the 26 letter counts of each word and use them (as a tuple, string or frozen "
                          "mapping) as a dict key, appending the word to its key's list"),
            "prime_product": ("a hash map keyed by a product of primes",
                              "give each letter a distinct prime number and use the product of a word's primes as "
                              "its dict key"),
            "sort_then_group": ("sorting words by signature and grouping neighbours",
                                "sort the words by their sorted-letter signature and cut the sorted sequence into "
                                "groups wherever the signature changes, without a key-to-list dict"),
        },
        "aliases": {
            "sorted_key": ["sorted string as key", "sorted word as key", "sorted letters", "sorting each word",
                           "sort each word", "sorted version", "sorted characters", "canonical form"],
            "count_key": ["character count", "letter count", "letter counts", "character frequency",
                          "frequency count", "count array", "frequency array", "26 counts", "tuple of counts",
                          "character counting", "counting characters", "frequency signature"],
            "prime_product": ["prime", "primes", "product of primes", "prime product", "prime numbers"],
            "sort_then_group": ["groupby", "group by", "sort the list", "sort the words", "adjacent groups",
                                "neighbouring", "neighboring"],
        },
        "excluded_by_limit": ["pairwise_grouping"],
        "whitelist": [],
    },
    "I3": {
        "unit_id": "I3_happy_number", "slug": "happy-number", "source_ids": ["leetcodedataset:202"],
        "signature": "solve(n)", "args": ["n"], "checker": "bool",
        "description": (
            "Task: write a Python function solve(n) that decides whether n is a happy number. The argument n is an "
            "int with 1 <= n <= 2**31 - 1. Starting from n, repeatedly replace the current number by the sum of the "
            "squares of its decimal digits. If this process eventually reaches 1, n is happy; otherwise the process "
            "keeps revisiting a loop of numbers that never contains 1, and n is not happy. Return True if n is happy "
            "and False otherwise. For example, solve(19) returns True because 1 + 81 = 82, 64 + 4 = 68, "
            "36 + 64 = 100 and 1 + 0 + 0 = 1, and solve(2) returns False."),
        "bounds": {"n": [1, 2 ** 31 - 1]},
        "dataset_reference_mode": "seen_set",
        "modes": {
            "seen_set": ("a hash set of seen numbers",
                         "remember every number produced so far (in a set, list or dict) and stop when the number "
                         "is 1 or repeats"),
            "floyd": ("Floyd's two-speed loop detection",
                      "advance one copy of the number by one step and another by two steps per round until they "
                      "meet, then report whether the meeting value is 1"),
            "known_loop": ("the known unhappy loop check",
                           "iterate until the number is 1 or a member of the known unhappy loop (4, 16, 37, 58, 89, "
                           "145, 42, 20), or below a small threshold whose answer is known"),
            "step_cap": ("a fixed iteration cap",
                         "apply the digit-square step a fixed large number of times (or until a bound) and return "
                         "whether 1 was reached"),
        },
        "aliases": {
            "seen_set": ["hash set", "hashset", "seen set", "visited set", "set of seen", "seen numbers",
                         "keep track of seen", "track seen", "set to track", "set to store", "memo",
                         "remember", "visited"],
            "floyd": ["floyd", "floyd's", "tortoise", "hare", "two pointers", "two-pointer", "fast and slow",
                      "slow and fast", "two speeds", "two-speed", "cycle detection algorithm"],
            "known_loop": ["known cycle", "known loop", "the number 4", "reaches 4", "equals 4", "89",
                           "unhappy loop", "unhappy cycle", "mathematical property"],
            "step_cap": ["iteration limit", "fixed number of iterations", "maximum iterations", "cap",
                         "limit the number", "upper bound on iterations", "bounded iterations"],
        },
        "excluded_by_limit": [],
        "whitelist": [],
    },
    "I4": {
        "unit_id": "I4_h_index", "slug": "h-index", "source_ids": ["leetcodedataset:274"],
        "signature": "solve(citations)", "args": ["citations"], "checker": "exact",
        "description": (
            "Task: write a Python function solve(citations) that returns the h-index of a researcher. The argument "
            "citations is a list of n ints, where 1 <= n <= 100000 and every value lies between 0 and 100000 "
            "inclusive; citations[i] is the number of citations of paper i. The h-index is the largest integer h "
            "such that at least h of the papers have at least h citations each. Return h as an int. For example, "
            "for citations = [3, 0, 6, 1, 5] the answer is 3, and for citations = [1, 3, 1] the answer is 1."),
        "bounds": {"n": [1, 100000], "value": [0, 100000]},
        "dataset_reference_mode": "sort_scan",
        "modes": {
            "sort_scan": ("sorting and a scan",
                          "sort the citation counts (ascending or descending) and scan them for the largest h with "
                          "at least h papers of at least h citations"),
            "counting_levels": ("counting papers per citation level",
                                "count the papers at each citation value capped at n in an array of size n + 1, then "
                                "accumulate the counts from the top level down until the running total reaches the "
                                "level"),
            "binary_search_h": ("binary search on h",
                                "binary-search the answer h in 0..n, testing each candidate by counting the papers "
                                "with at least h citations"),
            "heap_pop": ("a max-heap of citation counts",
                         "put the counts in a heap and pop the largest ones while the k-th largest count is at least "
                         "k"),
        },
        "aliases": {
            "sort_scan": ["sorting", "sort the", "sorted", "sort in descending", "sort in ascending", "sort and"],
            "counting_levels": ["counting sort", "bucket", "buckets", "count array", "frequency array",
                                "counting approach", "histogram"],
            "binary_search_h": ["binary search", "binary-search", "bisect"],
            "heap_pop": ["heap", "max-heap", "max heap", "priority queue", "heapq"],
        },
        "excluded_by_limit": ["quadratic_h_scan"],
        "whitelist": [],
    },
    "I5": {
        "unit_id": "I5_meeting_rooms", "slug": "meeting-rooms-ii", "source_ids": ["leetcodedataset:253"],
        "signature": "solve(intervals)", "args": ["intervals"], "checker": "exact",
        "description": (
            "Task: write a Python function solve(intervals) that returns the smallest number of rooms needed to "
            "hold all meetings. The argument intervals is a list of n pairs [start, end] of ints, where "
            "1 <= n <= 50000 and 0 <= start < end <= 1000000. Meeting i occupies a room during the half-open time "
            "span [start, end), so a meeting that ends at time t and a meeting that starts at time t can use the "
            "same room. Return, as an int, the minimum number of rooms such that no room ever holds two meetings at "
            "the same time. For example, for intervals = [[0, 30], [5, 10], [15, 20]] the answer is 2, and for "
            "intervals = [[7, 10], [2, 4]] the answer is 1."),
        "bounds": {"n": [1, 50000], "time": [0, 1000000]},
        "dataset_reference_mode": "difference_array",
        "modes": {
            "min_heap_ends": ("a min-heap of end times",
                              "process meetings by start time and keep a heap of the end times of rooms in use, "
                              "reusing the room with the earliest end when it is already free"),
            "two_sorted_lists": ("two sorted lists of starts and ends",
                                 "sort the start times and the end times separately and walk both with two indices, "
                                 "opening a room for each start that comes before the next end"),
            "sweep_events": ("a sweep over sorted +1/-1 events",
                             "turn each meeting into a +1 event at its start and a -1 event at its end, sort the "
                             "events (ends before starts at equal times) and track the largest running total"),
            "difference_array": ("a difference array over time",
                                 "add 1 at each start and subtract 1 at each end in an array indexed by time, then "
                                 "take the largest running total"),
        },
        "aliases": {
            "min_heap_ends": ["min-heap", "min heap", "heap", "priority queue", "heapq"],
            "two_sorted_lists": ["two sorted", "sort the start times and end times", "separate start and end",
                                 "start and end arrays", "chronological ordering", "two arrays"],
            "sweep_events": ["sweep line", "sweep-line", "line sweep", "events", "event points", "+1 and -1",
                             "+1/-1"],
            "difference_array": ["difference array", "prefix sum", "prefix sums", "timeline array",
                                 "array indexed by time", "counting array"],
        },
        "excluded_by_limit": ["overlap_count_per_meeting"],
        "whitelist": [],
    },
    "I6": {
        "unit_id": "I6_three_values_in_place", "slug": "sort-colors", "source_ids": ["leetcodedataset:75"],
        "signature": "solve(nums)", "args": ["nums"], "checker": "inplace",
        "description": (
            "Task: write a Python function solve(nums) that rearranges a list of colour codes in place. The "
            "argument nums is a list of n ints, where 1 <= n <= 200000, and every value is 0, 1 or 2. Rearrange "
            "nums in place so that every 0 comes before every 1 and every 1 before every 2; return None. Only the "
            "contents of nums after the call are checked. For example, nums = [2, 0, 2, 1, 1, 0] must become "
            "[0, 0, 1, 1, 2, 2], and nums = [2, 0, 1] must become [0, 1, 2]."),
        "bounds": {"n": [1, 200000]},
        "dataset_reference_mode": "dutch_flag",
        "modes": {
            "dutch_flag": ("the Dutch national flag three-way pass",
                           "make one pass with three indices (low, mid, high), exchanging 0s to the front and 2s to "
                           "the back as mid advances"),
            "counting_overwrite": ("counting then overwriting",
                                   "count the 0s, 1s and 2s, then write that many 0s, 1s and 2s back into nums"),
            "builtin_sort": ("the built-in sort", "call nums.sort() or assign nums[:] = sorted(nums)"),
            "two_pass_partition": ("two partition passes",
                                   "first move every 0 to the front with one moving boundary, then move every 1 "
                                   "directly after the 0s in a second pass"),
        },
        "aliases": {
            "dutch_flag": ["dutch national flag", "dutch flag", "three pointers", "three-pointer", "three-way",
                           "dijkstra", "low, mid, high", "low mid high", "one-pass"],
            "counting_overwrite": ["counting sort", "count the", "counting", "count occurrences", "frequency",
                                   "overwrite", "two-pass counting"],
            "builtin_sort": ["built-in sort", "builtin sort", ".sort()", "sorted(", "sort function", "timsort"],
            "two_pass_partition": ["two passes", "two-pass partition", "two partition", "partition twice",
                                   "two pointer passes", "lomuto"],
        },
        "excluded_by_limit": ["quadratic_exchange_sort"],
        "whitelist": [],
    },
    "I7": {
        "unit_id": "I7_one_counts", "slug": "counting-bits", "source_ids": ["leetcodedataset:338"],
        "signature": "solve(n)", "args": ["n"], "checker": "exact",
        "description": (
            "Task: write a Python function solve(n) that returns, for every integer i from 0 to n inclusive, how "
            "many digits equal to 1 the base-2 representation of i has. The argument n is an int with "
            "0 <= n <= 50000. Return a list ans of n + 1 ints where ans[i] is the number of ones in the base-2 "
            "representation of i. For example, solve(2) returns [0, 1, 1] and solve(5) returns "
            "[0, 1, 1, 2, 1, 2]."),
        "bounds": {"n": [0, 50000]},
        "dataset_reference_mode": "builtin_count",
        "modes": {
            "builtin_count": ("a built-in one-count per number",
                              "for every i, call bin(i).count('1'), i.bit_count() or format(i, 'b').count('1')"),
            "dp_half": ("reuse of the answer for i // 2",
                        "ans[i] = ans[i >> 1] + (i & 1), reusing the answer for i with its last base-2 digit "
                        "dropped"),
            "dp_lowest_one": ("reuse of the answer for i with its lowest one cleared",
                              "ans[i] = ans[i & (i - 1)] + 1"),
            "dp_offset": ("reuse of the answer within the current power-of-two block",
                          "ans[i] = ans[i - p] + 1, where p is the largest power of two not above i"),
            "per_number_loop": ("a digit loop per number",
                                "for every i, repeatedly take its last base-2 digit (i % 2 or i & 1) or clear its "
                                "lowest one, until it is zero, counting the ones"),
        },
        "aliases": {
            "builtin_count": ["bin(", "bin()", "bit_count", "built-in", "builtin", ".count('1')", "count('1')",
                              "string conversion", "format("],
            "dp_half": ["i >> 1", "i>>1", "i // 2", "i//2", "right shift", "half", "dynamic programming",
                        "dp", "i & 1"],
            "dp_lowest_one": ["i & (i - 1)", "i&(i-1)", "lowest set bit", "lowest one", "brian kernighan's dp",
                              "rightmost set bit"],
            "dp_offset": ["power of two", "power-of-two", "most significant bit", "offset", "highest power"],
            "per_number_loop": ["brian kernighan", "kernighan", "loop over each number", "shift and count",
                                "for each number count", "naive", "brute force"],
        },
        "excluded_by_limit": [],
        "whitelist": ["base-2 representation"],
    },
    "I8": {
        "unit_id": "I8_first_missing_positive", "slug": "first-missing-positive",
        "source_ids": ["leetcodedataset:41"], "signature": "solve(nums)", "args": ["nums"], "checker": "exact",
        "description": (
            "Task: write a Python function solve(nums) that returns the smallest positive integer that does not "
            "occur in nums. The argument nums is a list of n ints, where 1 <= n <= 100000, and every value lies "
            "between -2**31 and 2**31 - 1 inclusive; values may repeat. Return the smallest integer x >= 1 that is "
            "not an element of nums, as an int. For example, for nums = [1, 2, 0] the answer is 3, for "
            "nums = [3, 4, -1, 1] the answer is 2, and for nums = [7, 8, 9, 11, 12] the answer is 1."),
        "bounds": {"n": [1, 100000], "value": [-2 ** 31, 2 ** 31 - 1]},
        "dataset_reference_mode": "cyclic_placement",
        "modes": {
            "cyclic_placement": ("in-place index placement",
                                 "exchange every value v in 1..n into position v - 1, then scan for the first "
                                 "position i that does not hold i + 1"),
            "sign_marking": ("in-place sign marking",
                             "replace out-of-range values by n + 1, then record the presence of v by making "
                             "nums[v - 1] negative, and return the first position left positive"),
            "hash_set_scan": ("a hash set of the values",
                              "put the values in a set and test 1, 2, 3, ... until one is absent"),
            "sort_scan": ("sorting and a scan",
                          "sort the values and walk the positive ones, tracking the next expected integer"),
            "presence_array": ("a boolean presence array",
                               "allocate n + 2 flags, flag every value in 1..n + 1, and return the first unflagged "
                               "index"),
        },
        "aliases": {
            "cyclic_placement": ["cyclic sort", "cyclic", "index placement", "place each number",
                                 "correct position", "correct index", "its correct place", "in-place swapping",
                                 "swapping"],
            "sign_marking": ["sign", "negative marking", "negation", "mark as negative", "negate",
                             "index as a hash key", "marking"],
            "hash_set_scan": ["hash set", "hashset", "set of", "a set", "hash table", "hashtable", "set"],
            "sort_scan": ["sorting", "sort the", "sorted", "sort and"],
            "presence_array": ["boolean array", "presence array", "seen array", "flag array", "visited array",
                               "auxiliary array", "extra array"],
        },
        "excluded_by_limit": ["quadratic_search"],
        "whitelist": [],
    },
    "I9": {
        "unit_id": "I9_common_with_repeats", "slug": "intersection-of-two-arrays-ii",
        "source_ids": ["leetcodedataset:350"], "signature": "solve(nums1, nums2)", "args": ["nums1", "nums2"],
        "checker": "multiset",
        "description": (
            "Task: write a Python function solve(nums1, nums2) that returns the values common to two lists, with "
            "repeats. The arguments nums1 and nums2 are lists of ints, each of length 1 to 50000, and every value "
            "lies between 0 and 1000000 inclusive. Each value must appear in the result exactly as many times as "
            "the smaller of the number of times it appears in nums1 and in nums2. Return the result as a list of "
            "ints in any order. For example, for nums1 = [1, 2, 2, 1] and nums2 = [2, 2] the answer is [2, 2], and "
            "for nums1 = [4, 9, 5] and nums2 = [9, 4, 9, 8, 4] one valid answer is [4, 9]."),
        "bounds": {"n": [1, 50000], "value": [0, 1000000]},
        "dataset_reference_mode": "hash_count",
        "modes": {
            "hash_count": ("a hash map of counts",
                           "count the values of one list in a dict or Counter (including Counter intersection) and "
                           "walk the other list, taking a value while its remaining count is positive"),
            "sort_two_index": ("sorting both lists and a two-index walk",
                               "sort both lists and advance two indices, taking a value when both indices point to "
                               "equal values"),
            "sort_binary_search": ("sorting one list and binary search",
                                   "sort one list and, for each value of the other, binary-search a matching value "
                                   "that has not been used yet"),
            "count_array": ("a count array indexed by value",
                            "count the values of one list in a list of size max value + 1 and walk the other list"),
        },
        "aliases": {
            "hash_count": ["hash map", "hashmap", "hash table", "hashtable", "counter", "dictionary", "frequency map",
                           "frequency count", "count map", "dict"],
            "sort_two_index": ["two pointers", "two-pointer", "two pointer", "sort both", "sorting both",
                               "sorted arrays"],
            "sort_binary_search": ["binary search", "binary-search", "bisect"],
            "count_array": ["count array", "counting array", "frequency array", "array of size",
                            "array indexed by value", "counting sort", "direct addressing"],
        },
        "excluded_by_limit": ["list_remove_loop"],
        "whitelist": [],
    },
    "I10": {
        "unit_id": "I10_best_single_trade", "slug": "best-time-to-buy-and-sell-stock",
        "source_ids": ["leetcodedataset:121"], "signature": "solve(prices)", "args": ["prices"], "checker": "exact",
        "description": (
            "Task: write a Python function solve(prices) that returns the largest profit from one purchase "
            "followed by one later sale. The argument prices is a list of n ints, where 1 <= n <= 100000 and every "
            "value lies between 0 and 10000 inclusive; prices[i] is the price on day i. Choose a day to buy and a "
            "strictly later day to sell, and return the largest possible value of the sale price minus the "
            "purchase price as an int; return 0 if no positive profit is possible. For example, for "
            "prices = [7, 1, 5, 3, 6, 4] the answer is 5, and for prices = [7, 6, 4, 3, 1] the answer is 0."),
        "bounds": {"n": [1, 100000], "value": [0, 10000]},
        "dataset_reference_mode": "running_min",
        "modes": {
            "running_min": ("a running minimum",
                            "scan the days once, keeping the lowest price so far and the best price minus that "
                            "minimum"),
            "max_subarray_diffs": ("a maximum-sum run of daily changes",
                                   "turn the prices into day-to-day differences and take the best sum of a "
                                   "contiguous run of them (Kadane's method), at least 0"),
            "suffix_max": ("a running maximum from the right",
                           "scan from the last day backwards keeping the highest later price (or precompute "
                           "prefix minima and suffix maxima), and take the best later maximum minus the price"),
            "state_dp": ("a hold/sold state recurrence",
                         "keep the best value of holding a share and of having sold, updated each day as "
                         "hold = max(hold, -p) and sold = max(sold, hold + p)"),
        },
        "aliases": {
            "running_min": ["minimum price", "min price", "lowest price", "running minimum", "track the minimum",
                            "one pass", "single pass", "min_price"],
            "max_subarray_diffs": ["kadane", "kadane's", "maximum subarray", "max subarray", "daily differences",
                                   "price differences", "differences"],
            "suffix_max": ["suffix", "from the right", "backwards", "reverse", "maximum to the right",
                           "max from the end", "prefix minimum and suffix maximum"],
            "state_dp": ["dynamic programming", "dp", "state machine", "hold and sell", "buy and sell states",
                         "hold", "states"],
        },
        "excluded_by_limit": ["pair_scan"],
        "whitelist": [],
    },
    "I11": {
        "unit_id": "I11_right_shift_in_place", "slug": "rotate-array", "source_ids": ["leetcodedataset:189"],
        "signature": "solve(nums, k)", "args": ["nums", "k"], "checker": "inplace",
        "description": (
            "Task: write a Python function solve(nums, k) that shifts the elements of a list to the right by k "
            "places, in place. The argument nums is a list of n ints, where 1 <= n <= 100000 and every value lies "
            "between -2**31 and 2**31 - 1, and k is an int with 0 <= k <= 100000. After the call, the element that "
            "was at position i must be at position (i + k) % n for every i; return None. Only the contents of nums "
            "after the call are checked. For example, for nums = [1, 2, 3, 4, 5, 6, 7] and k = 3, nums must become "
            "[5, 6, 7, 1, 2, 3, 4]."),
        "bounds": {"n": [1, 100000], "k": [0, 100000]},
        "dataset_reference_mode": "triple_reverse",
        "modes": {
            "slice_assign": ("slice reassembly", "assign nums[:] = nums[-k:] + nums[:-k] (k reduced modulo n)"),
            "triple_reverse": ("three reversals",
                               "reverse the whole list, then reverse the first k and the remaining n - k elements"),
            "juggling": ("cyclic replacements",
                         "move each element directly to its target position, following each chain of positions "
                         "(gcd(n, k) chains) until it returns to its start"),
            "extra_array": ("a shifted copy",
                            "write every nums[i] into position (i + k) % n of a new list and copy it back"),
            "deque_rotate": ("a deque rotation", "build collections.deque(nums), call rotate(k) and copy it back"),
        },
        "aliases": {
            "slice_assign": ["slicing", "slice", "slices", "concatenation"],
            "triple_reverse": ["reverse", "reversal", "reversals", "three reverses", "reverse three times"],
            "juggling": ["juggling", "cyclic replacement", "cyclic replacements", "gcd", "chains"],
            "extra_array": ["extra array", "new array", "auxiliary array", "copy", "temporary array"],
            "deque_rotate": ["deque", "rotate()", "collections.deque"],
        },
        "excluded_by_limit": ["pop_insert_loop"],
        "whitelist": [],
    },
    "I12": {
        "unit_id": "I12_common_divisor_all", "slug": "find-greatest-common-divisor-of-array",
        "source_ids": ["leetcodedataset:1979"], "signature": "solve(nums)", "args": ["nums"], "checker": "exact",
        "description": (
            "Task: write a Python function solve(nums) that returns the greatest common divisor of all elements of "
            "nums. The argument nums is a list of n ints, where 1 <= n <= 100000 and every value lies between 1 and "
            "10**12 inclusive. Return the largest positive integer that divides every element of nums, as an int. "
            "For example, for nums = [12, 18, 30] the answer is 6, and for nums = [7] the answer is 7."),
        "bounds": {"n": [1, 100000], "value": [1, 10 ** 12]},
        "dataset_reference_mode": "library_gcd",
        "modes": {
            "library_gcd": ("the library gcd function", "fold math.gcd over the values (reduce or math.gcd(*nums))"),
            "euclid_loop": ("Euclid's remainder algorithm",
                            "fold a hand-written Euclid step (a, b = b, a % b until b is 0) over the values"),
            "binary_gcd": ("Stein's binary gcd", "fold a hand-written gcd that removes common factors of two and "
                                                 "subtracts odd values"),
            "subtraction_euclid": ("Euclid's subtraction algorithm",
                                   "fold a gcd that repeatedly subtracts the smaller value from the larger"),
        },
        "aliases": {
            "library_gcd": ["math.gcd", "gcd function", "built-in gcd", "functools.reduce", "reduce"],
            "euclid_loop": ["euclidean", "euclid", "euclid's", "modulo", "remainder"],
            "binary_gcd": ["stein", "stein's", "binary gcd"],
            "subtraction_euclid": ["subtraction", "subtract"],
        },
        "excluded_by_limit": ["divisor_trial"],
        "whitelist": ["greatest common divisor"],
    },
}


def spec_text(u: str) -> str:
    return cap_first(UNITS[u]["description"]) + "\n\n" + cap_first(FORMAT_LINE)


def catalogue(u: str) -> list[str]:
    return list(UNITS[u]["modes"])


def display_name(u: str, m: str) -> str:
    return UNITS[u]["modes"][m][0]


def mechanism(u: str, m: str) -> str:
    return UNITS[u]["modes"][m][1]


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
    wl = set(spec.get("whitelist", []))
    return sorted(w for w in words if w not in wl)


def _find_word(w: str, low: str) -> bool:
    pat = r"(?<![a-z0-9_])" + re.escape(w) + r"(?![a-z0-9_])"
    return re.search(pat, low) is not None


def grep_banned(u: str, text: str) -> list[str]:
    """Banned words found in text, after blanking the unit's whitelisted phrases."""
    low = text.lower()
    for w in UNITS[u].get("whitelist", []):
        low = low.replace(w.lower(), " ")
    return [w for w in banned_words(u) if _find_word(w, low)]


def catalogue_names(u: str) -> list[str]:
    """Catalogue display names (with and without article) and aliases -- the grep audit's name lexicon."""
    spec = UNITS[u]
    out = set()
    for m, (dn, _) in spec["modes"].items():
        out.add(dn.lower())
        out.add(re.sub(r"^(a|an|the)\s+", "", dn.lower()))
    for aa in spec["aliases"].values():
        for a in aa:
            if re.search(r"[a-z]", a.lower()) and len(a) > 2:
                out.add(a.lower())
    return sorted(out)


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
            hit = _find_word(al, low) if re.search(r"[a-z]", al) else (al in low)
            if hit and len(al) > best_len:
                best, best_len = m, len(al)
    return best
