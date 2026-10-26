#!/usr/bin/env python3
"""Stage 2a: frozen task specifications of the panel-A units (bench schema), twin nouns and every rendered prompt.

Each spec has the iteration-2 bench schema (signature, description, format_line, spec_text, catalogue[{mode,
display_name, mechanism}], aliases, association_template) plus a frozen bounds table and a whitelist of the
I/O-descriptive words that the description cannot avoid. Descriptions contain no algorithm or data-structure word.

Twin (R2 builder of exp19 prompts_v4, one logged change): a neutral noun from the dependency's concreteness_norms
bank (metadata_noun_bank_candidate), excluding exp13's NOUN_EXCLUSIONS and any word of the spec, catalogue or
aliases, padded with ' .' to L_u = the largest token count of the unit's catalogue display names (the default is
unknown before the twin; deviation D-pad). Rendered kinds: twin W1-W5, novelty, plain (spec only), assoc
(association prompt; rendered once the default is known), plainc (base plain-completion text, no chat template).
Assertions: spec ids identical across arms; the grep audit finds no display name / alias in any condition segment and
only whitelisted words of a frozen list in the description.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg5 import (ASSOC_TEMPLATE, DATA, DEP, E19, FORMAT_LINE, NEWBENCH, NOUN_EXCLUSIONS, NOVELTY, PAD_FILLER,
                  RESULTS, TEMPLATE_IDS, TEMPLATE_TAIL, TEMPLATES, UNIT_DIRS, cap_first, read_json, read_jsonl,
                  setup_logging, sha256_text, stable_seed, unit_dir, write_json, write_jsonl)

PROMPTS_NEW = DATA / "prompts_new.jsonl"
PROMPTS_EXISTING = E19 / "data" / "prompts.jsonl"

# words that describe algorithms or data structures; none may appear in a description unless whitelisted per unit
ALGO_WORDS = ["sort", "sorted", "sorting", "hash", "hashing", "dictionary", "dict", "counter", "stack", "queue",
              "heap", "tree", "trie", "graph", "search", "pointer", "pointers", "window", "dynamic", "programming",
              "prefix", "suffix", "sieve", "recursion", "recursive", "divide", "conquer", "greedy", "binary",
              "vote", "voting", "random", "bit", "bitwise", "matrix", "table", "memo", "kadane", "manacher",
              "union", "find", "disjoint", "flood", "fill", "dfs", "bfs", "breadth", "depth", "island", "islands",
              "palindrome", "palindromic", "median", "merge", "partition", "scan", "scanning", "center", "centre",
              "expand", "segment", "monotonic", "subarray", "array", "arrays", "prime", "primes", "grid",
              "majority", "mode", "statistics", "commonprefix", "divisors", "order", "sorted"]

SPECS: dict[str, dict[str, Any]] = {
    "A1": {
        "task_id": "A1_majority_element", "leetcode_ids": [169], "signature": "solve(nums)",
        "description": ("Task: write a Python function solve(nums) that returns the value that appears more than "
                        "len(nums) // 2 times in the list nums. The argument nums is a list of integers with 1 <= "
                        "len(nums) <= 30000, and every value lies between -1000000000 and 1000000000 inclusive. Such "
                        "a value always exists, so the answer is unique: for nums = [2, 2, 1, 1, 1, 2, 2] the answer "
                        "is 2."),
        "bounds": {"len(nums)": [1, 30000], "value": [-10 ** 9, 10 ** 9]},
        "whitelist": [],
        "catalogue": [
            ("boyer_moore_vote", "Boyer-Moore majority vote",
             "keep one candidate and a counter in a single pass: equal values add one, others subtract one, and the "
             "candidate is replaced when the counter is zero; no container of counts"),
            ("hash_count", "hash map counting",
             "count the occurrences of every value in a dict, Counter or defaultdict (including most_common or an "
             "early exit once a count exceeds half) and return the value whose count exceeds half"),
            ("sort_middle", "sorting",
             "sort the values and return the element at index len(nums) // 2"),
            ("divide_conquer", "divide and conquer",
             "recursively find the majority of each half and, when the halves disagree, count both candidates over "
             "the range"),
            ("randomized_verify", "randomized sampling",
             "repeatedly pick a random element with the random module and count its occurrences until one exceeds "
             "half"),
            ("bit_count", "bit-by-bit counting",
             "for each of the 32 bit positions count how many values have that bit set and assemble the answer bit "
             "by bit, with sign handling"),
            ("library_mode", "statistics.mode",
             "return statistics.mode(nums) (or multimode), a library call that solves the whole task"),
        ],
        "aliases": {"boyer_moore_vote": ["boyer-moore", "boyer moore", "majority vote", "voting algorithm",
                                         "moore's voting", "moore voting"],
                    "hash_count": ["hash map", "hashmap", "hash table", "dictionary", "counter", "frequency count",
                                   "frequency map", "counting occurrences"],
                    "sort_middle": ["sorting", "sort the", "sorted"],
                    "divide_conquer": ["divide and conquer", "divide-and-conquer"],
                    "randomized_verify": ["randomized", "randomised", "random sampling", "random selection"],
                    "bit_count": ["bit manipulation", "bitwise", "bit-by-bit", "bit counting"],
                    "library_mode": ["statistics.mode", "statistics module", "multimode"]},
    },
    "A2": {
        "task_id": "A2_max_subarray", "leetcode_ids": [53], "signature": "solve(nums)",
        "description": ("Task: write a Python function solve(nums) that returns the largest sum of a non-empty block "
                        "of consecutive elements of the list nums. The argument nums is a list of integers with 1 <= "
                        "len(nums) <= 20000, and every value lies between -10000 and 10000 inclusive. The block must "
                        "hold at least one element, so when every value is negative the answer is the largest single "
                        "value: for nums = [-2, 1, -3, 4, -1, 2, 1, -5, 4] the answer is 6, the sum of [4, -1, 2, "
                        "1]."),
        "bounds": {"len(nums)": [1, 20000], "value": [-10000, 10000]},
        "whitelist": [],
        "catalogue": [
            ("kadane", "Kadane's algorithm",
             "scan once keeping the best sum of a block ending at the current element (extend it or restart at the "
             "element) and the best seen so far; includes a dp array of best-ending-here sums"),
            ("prefix_min", "prefix sums with a running minimum",
             "scan the prefix sums and at each position subtract the smallest earlier prefix sum, keeping the "
             "largest difference"),
            ("divide_conquer", "divide and conquer",
             "split at the middle, solve both halves recursively and combine them with the best block crossing the "
             "middle"),
            ("segment_tree", "segment tree",
             "build a tree over the array whose nodes store total, best prefix, best suffix and best sums, combining "
             "children"),
        ],
        "aliases": {"kadane": ["kadane", "dynamic programming"],
                    "prefix_min": ["prefix sum", "prefix-sum", "cumulative sum", "running minimum"],
                    "divide_conquer": ["divide and conquer", "divide-and-conquer"],
                    "segment_tree": ["segment tree", "segment-tree"]},
    },
    "A3": {
        "task_id": "A3_trapping_rain_water", "leetcode_ids": [42], "signature": "solve(height)",
        "description": ("Task: write a Python function solve(height) that returns the total amount of rain water "
                        "held by a row of bars after rain. The argument height is a list of integers with 1 <= "
                        "len(height) <= 20000 and 0 <= height[i] <= 100000; bar i has width 1 and height height[i], "
                        "and water rests above a bar only where taller bars on both sides hold it in, never spilling "
                        "past the ends of the row. For height = [0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1] the answer is "
                        "6."),
        "bounds": {"len(height)": [1, 20000], "value": [0, 100000]},
        "whitelist": [],
        "catalogue": [
            ("two_pointers", "two pointers",
             "move a left and a right index inward, keeping the running maximum on each side and adding water on the "
             "side whose maximum is smaller"),
            ("prefix_suffix_max", "prefix and suffix maximum arrays",
             "precompute the tallest bar to the left and to the right of every position in two arrays, then sum "
             "min(left, right) - height"),
            ("monotonic_stack", "monotonic stack",
             "keep a stack of indices with decreasing heights; when a taller bar arrives, pop and add the water "
             "bounded between it and the new top"),
            ("peak_split", "splitting at the highest bar",
             "find the tallest bar, then scan from each end towards it keeping a running maximum and adding water"),
        ],
        "aliases": {"two_pointers": ["two pointers", "two-pointer", "two pointer", "two-pointers"],
                    "prefix_suffix_max": ["prefix max", "suffix max", "prefix and suffix", "left max and right max",
                                          "precomputed maxima", "dynamic programming", "left and right maximum"],
                    "monotonic_stack": ["monotonic stack", "monotone stack", "stack-based", "using a stack",
                                        "a stack"],
                    "peak_split": ["highest bar", "tallest bar", "global maximum", "split at the peak"]},
    },
    "A4": {
        "task_id": "A4_count_primes", "leetcode_ids": [204], "signature": "solve(n)",
        "description": ("Task: write a Python function solve(n) that returns how many prime numbers are strictly "
                        "smaller than n. The argument n is an integer with 0 <= n <= 50000. A prime number is an "
                        "integer greater than 1 whose only positive divisors are 1 and itself, so for n = 10 the "
                        "answer is 4 (2, 3, 5 and 7), and for n = 0, 1 or 2 the answer is 0."),
        "bounds": {"n": [0, 50000]},
        "whitelist": ["prime", "divisors"],
        "catalogue": [
            ("eratosthenes", "sieve of Eratosthenes",
             "mark the multiples of every prime in a boolean array of size n (slice assignment or inner loops) and "
             "count the unmarked entries"),
            ("trial_division", "trial division",
             "test each number for divisibility by smaller numbers (all integers, 6k +- 1 candidates or the primes "
             "found so far) up to its square root"),
            ("linear_sieve", "linear sieve (Euler's sieve)",
             "keep a list of primes and cross off i * p for primes p up to the smallest prime factor of i, breaking "
             "when p divides i, so each composite is crossed once"),
            ("segmented_sieve", "segmented sieve",
             "sieve the range in fixed-size blocks using the primes up to the square root of n"),
            ("sundaram", "sieve of Sundaram",
             "cross out i + j + 2ij for 1 <= i <= j and map each surviving k to the odd prime 2k + 1"),
            ("atkin", "sieve of Atkin",
             "toggle candidates by the quadratic forms 4x^2 + y^2, 3x^2 + y^2 and 3x^2 - y^2 modulo 12, then remove "
             "multiples of squares of primes"),
        ],
        "aliases": {"eratosthenes": ["eratosthenes"],
                    "trial_division": ["trial division", "primality test", "check each number", "is_prime"],
                    "linear_sieve": ["linear sieve", "euler's sieve", "euler sieve", "sieve of euler"],
                    "segmented_sieve": ["segmented sieve", "segmented"],
                    "sundaram": ["sundaram"], "atkin": ["atkin"]},
    },
    "A5": {
        "task_id": "A5_longest_common_prefix", "leetcode_ids": [14], "signature": "solve(strs)",
        "description": ("Task: write a Python function solve(strs) that returns the longest string that is a prefix "
                        "of every string in the list strs. The argument strs is a list of 1 to 200 strings, each of "
                        "length 0 to 200 and made of lowercase English letters. If the strings do not all start with "
                        "the same letter the answer is the empty string: for strs = [\"flower\", \"flow\", "
                        "\"flight\"] the answer is \"fl\", and for strs = [\"dog\", \"racecar\", \"car\"] it is "
                        "\"\"."),
        "bounds": {"len(strs)": [1, 200], "len(s)": [0, 200]},
        "whitelist": ["prefix"],
        "catalogue": [
            ("horizontal_scan", "horizontal scanning",
             "take the first string as the answer and shorten it against each following string in turn (startswith, "
             "slicing or a character loop per string)"),
            ("vertical_scan", "vertical scanning",
             "compare the strings column by column, character position i of every string before position i + 1 "
             "(including zip(*strs))"),
            ("sort_ends", "comparing the lexicographically smallest and largest strings",
             "sort the strings (or take min and max) and return the common prefix of the first and last only"),
            ("binary_search_length", "binary search on the prefix length",
             "binary search over the candidate length, testing whether the prefix of that length is shared by all "
             "strings"),
            ("divide_conquer", "divide and conquer",
             "recursively compute the common prefix of each half of the list and combine the two results"),
            ("trie", "trie (prefix tree)",
             "insert the strings into a trie and walk down from the root while there is a single child and no "
             "string ends"),
            ("library_commonprefix", "os.path.commonprefix",
             "return os.path.commonprefix(strs), a library call that solves the whole task"),
        ],
        "aliases": {"horizontal_scan": ["horizontal scan", "horizontal scanning", "pairwise comparison", "reduce"],
                    "vertical_scan": ["vertical scan", "vertical scanning", "character by character",
                                      "column by column", "zip("],
                    "sort_ends": ["sorting", "sort the", "lexicographic", "min and max"],
                    "binary_search_length": ["binary search"],
                    "divide_conquer": ["divide and conquer", "divide-and-conquer"],
                    "trie": ["trie", "prefix tree"],
                    "library_commonprefix": ["os.path.commonprefix", "commonprefix"]},
    },
    "A6": {
        "task_id": "A6_number_of_islands", "leetcode_ids": [200], "signature": "solve(grid)",
        "description": ("Task: write a Python function solve(grid) that returns the number of separate land regions "
                        "in a rectangular map. The argument grid is a list of 1 to 30 rows, each a list of 1 to 30 "
                        "one-character strings, all rows of equal length; '1' marks land and '0' marks water. Two "
                        "land cells belong to the same region when they are joined through a sequence of land cells, "
                        "each sharing a side (up, down, left or right) with the next; touching only at a corner does "
                        "not join them. A map with no land has 0 regions."),
        "bounds": {"rows": [1, 30], "cols": [1, 30]},
        "whitelist": ["grid"],
        "catalogue": [
            ("dfs_flood", "depth-first search (DFS)",
             "flood each unvisited land cell with a depth-first traversal (recursion or an explicit LIFO stack) and "
             "count the starts"),
            ("bfs_flood", "breadth-first search (BFS)",
             "flood each unvisited land cell with a breadth-first traversal using a FIFO queue and count the "
             "starts"),
            ("union_find", "union-find (disjoint set union)",
             "union every pair of adjacent land cells in a disjoint-set forest and count the roots of land cells"),
        ],
        "aliases": {"dfs_flood": ["depth-first", "depth first", "dfs"],
                    "bfs_flood": ["breadth-first", "breadth first", "bfs"],
                    "union_find": ["union-find", "union find", "unionfind", "disjoint set", "disjoint-set", "dsu"]},
    },
    "A7": {
        "task_id": "A7_longest_palindromic_substring", "leetcode_ids": [5], "signature": "solve(s)",
        "description": ("Task: write a Python function solve(s) that returns a longest substring of s that reads the "
                        "same forwards and backwards. The argument s is a string of 1 to 600 characters, each a "
                        "lowercase English letter or a digit. When several substrings share the maximum length any "
                        "one of them is accepted: for s = \"babad\" both \"bab\" and \"aba\" are correct answers, and "
                        "for s = \"cbbd\" the answer is \"bb\"."),
        "bounds": {"len(s)": [1, 600]},
        "whitelist": [],
        "catalogue": [
            ("expand_center", "expanding around each center",
             "for each of the 2n - 1 centers expand outwards while the characters on both sides match, keeping the "
             "longest"),
            ("dp_table", "dynamic programming table",
             "fill a table dp[i][j] that records whether s[i..j] reads the same both ways from shorter substrings "
             "(dp[i + 1][j - 1])"),
            ("manacher", "Manacher's algorithm",
             "transform the string with separators and compute all radii in linear time by mirroring around the "
             "rightmost known center"),
            ("brute_force", "brute force",
             "check every substring (or every substring from longest to shortest) by comparing it with its "
             "reverse"),
        ],
        "aliases": {"expand_center": ["expand around", "center expansion", "expanding around", "expand from the",
                                      "around each center", "around the center", "around center"],
                    "dp_table": ["dynamic programming", "dp table", "dp"],
                    "manacher": ["manacher"],
                    "brute_force": ["brute force", "brute-force", "check every substring", "all substrings"]},
    },
    "A8": {
        "task_id": "A8_jump_game", "leetcode_ids": [55], "signature": "solve(nums)",
        "description": ("Task: write a Python function solve(nums) that returns True if the last index of the list "
                        "nums can be reached from index 0 and False otherwise. The argument nums is a list of "
                        "integers with 1 <= len(nums) <= 2000 and 0 <= nums[i] <= 100000; standing at index i you may "
                        "move forward to any index from i + 1 to i + nums[i]. For nums = [2, 3, 1, 1, 4] the answer "
                        "is True, and for nums = [3, 2, 1, 0, 4] it is False."),
        "bounds": {"len(nums)": [1, 2000], "value": [0, 100000]},
        "whitelist": [],
        "catalogue": [
            ("greedy", "greedy farthest reach",
             "scan once keeping the farthest reachable index (forward reach, or backward last-good index)"),
            ("dp", "dynamic programming",
             "fill a reachable / good array position by position from earlier or later positions"),
            ("bfs_indices", "breadth-first search over indices",
             "explore indices with a FIFO queue and a visited set, enqueueing every index reachable in one move"),
        ],
        "aliases": {"greedy": ["greedy", "farthest", "furthest", "max reach"], "dp": ["dynamic programming", "dp"],
                    "bfs_indices": ["breadth-first", "bfs"]},
    },
    "A9": {
        "task_id": "A9_median_two_sorted", "leetcode_ids": [4], "signature": "solve(nums1, nums2)",
        "description": ("Task: write a Python function solve(nums1, nums2) that returns the median of all values of "
                        "the two lists taken together, as a float. Each argument is a list of integers in "
                        "non-decreasing order with 0 to 1000 elements and values between -1000000 and 1000000 "
                        "inclusive, and at least one of the two lists is non-empty. The median of an odd number of "
                        "values is the middle one and of an even number the mean of the two middle ones: for nums1 = "
                        "[1, 3] and nums2 = [2] the answer is 2.0, and for nums1 = [1, 2] and nums2 = [3, 4] it is "
                        "2.5."),
        "bounds": {"len(nums)": [0, 1000], "value": [-10 ** 6, 10 ** 6]},
        "whitelist": ["median", "order"],
        "catalogue": [
            ("merge_two_pointers", "merging with two pointers", "merge the two lists with two indices up to the middle"),
            ("partition_binary_search", "binary search on the partition",
             "binary search a cut of the shorter list so that the left halves hold the smaller values"),
            ("heap_merge", "heap merge", "merge through heapq (heapq.merge or pushes and pops) up to the middle"),
            ("concat_sort", "concatenate and sort", "concatenate the lists, sort and read the middle"),
        ],
        "aliases": {"merge_two_pointers": ["two pointers", "two-pointer", "merge step", "merging"],
                    "partition_binary_search": ["binary search", "partition"],
                    "heap_merge": ["heap", "heapq"], "concat_sort": ["sort", "concatenat"]},
    },
}


def spec_text(u: str) -> str:
    return cap_first(SPECS[u]["description"]) + "\n\n" + cap_first(FORMAT_LINE)


def display_name(u: str, mode: str) -> str:
    for m, d, _ in SPECS[u]["catalogue"]:
        if m == mode:
            return d
    raise KeyError(f"{u}/{mode}")


def catalogue(u: str) -> list[str]:
    return [m for m, _, _ in SPECS[u]["catalogue"]]


def write_spec(u: str) -> dict[str, Any]:
    s = SPECS[u]
    out = {"task": u, "task_id": s["task_id"], "leetcode_ids": s["leetcode_ids"], "signature": s["signature"],
           "description": s["description"], "format_line": FORMAT_LINE, "spec_text": spec_text(u),
           "bounds": s["bounds"], "whitelist": s["whitelist"],
           "catalogue": [{"mode": m, "display_name": d, "mechanism": mech} for m, d, mech in s["catalogue"]],
           "aliases": s["aliases"], "association_template": ASSOC_TEMPLATE, "spec_version": 1}
    d = unit_dir(u)
    d.mkdir(parents=True, exist_ok=True)
    write_json(d / "spec.json", out)
    return out


def description_audit(u: str) -> dict[str, Any]:
    desc = SPECS[u]["description"].lower()
    wl = {w.lower() for w in SPECS[u]["whitelist"]}
    hits = sorted({w for w in ALGO_WORDS if w not in wl and re.search(rf"\b{re.escape(w)}\b", desc)})
    names = [d for _, d, _ in SPECS[u]["catalogue"]] + [a for v in SPECS[u]["aliases"].values() for a in v]
    name_hits = sorted({a for a in names if a.lower() not in wl and len(a) > 3
                        and re.search(rf"(?<![a-z]){re.escape(a.lower())}(?![a-z])", desc)})
    return {"algo_word_hits": hits, "catalogue_name_hits": name_hits}


def load_tokenizer():
    from transformers import AutoTokenizer

    from cfg5 import model_path

    return AutoTokenizer.from_pretrained(model_path("instruct"))


def chat_ids(tok: Any, user_text: str) -> list[int]:
    ids = tok.apply_chat_template([{"role": "user", "content": user_text}], tokenize=True,
                                  add_generation_prompt=True, enable_thinking=False)
    if isinstance(ids, dict):
        ids = ids["input_ids"]
    return list(ids)


def positions(tok: Any, ids: list[int], spec: str) -> tuple[int, int, int]:
    """exp19 prompts_v4.positions: (p0, p1, spec_end)."""
    head = tok("<|im_start|>user\n", add_special_tokens=False)["input_ids"]
    assert ids[:len(head)] == head, "unexpected chat header"
    suf = tok(spec + TEMPLATE_TAIL, add_special_tokens=False)["input_ids"]
    p1 = len(ids) - len(suf)
    assert ids[p1:] == suf, "SPEC + template tail do not tokenize identically in context"
    tail = tok(TEMPLATE_TAIL, add_special_tokens=False)["input_ids"]
    assert ids[len(ids) - len(tail):] == tail, "chat tail mismatch"
    return len(head), p1, len(ids) - len(tail)


def record(tok: Any, task: str, w: str, kind: str, segment: str | None, spec: str, **extra: Any) -> dict[str, Any]:
    """exp19 prompts_v4.record (verbatim logic)."""
    text = (cap_first(segment) + "\n\n" + spec) if segment else spec
    ids = chat_ids(tok, text)
    p0, p1, spec_end = positions(tok, ids, spec)
    return {"task": task, "w": w, "kind": kind, "segment": cap_first(segment) if segment else "", "user_text": text,
            "ids": ids, "P": len(ids), "p0": p0, "p1": p1, "spec_end": spec_end,
            "prompt_sha256": sha256_text(json.dumps(ids)), **extra}


def noun_bank() -> list[dict[str, Any]]:
    p = DEP / "noun_bank.json"
    if p.exists():
        return read_json(p)
    raise FileNotFoundError("inputs/dep_dataset/noun_bank.json (run stage0 first)")


def pick_noun(tok: Any, u: str, used: set[str]) -> str:
    s = SPECS[u]
    banned_text = (s["description"] + " " + " ".join(d + " " + mech for _, d, mech in s["catalogue"]) + " " +
                   " ".join(a for v in s["aliases"].values() for a in v)).lower()
    cands = []
    for r in noun_bank():
        w = r["word"].lower()
        if w in NOUN_EXCLUSIONS or w in used or not w.isalpha():
            continue
        if re.search(rf"\b{re.escape(w)}\b", banned_text):
            continue
        if len(tok(" " + w, add_special_tokens=False)["input_ids"]) != 1:
            continue
        cands.append(w)
    cands = sorted(set(cands))
    assert cands, f"{u}: no noun candidates"
    return cands[stable_seed("i5A", "noun", u) % len(cands)]


def L_u(tok: Any, u: str) -> int:
    return max(len(tok(d, add_special_tokens=False)["input_ids"]) for _, d, _ in SPECS[u]["catalogue"])


def plainc_prompt(u: str) -> str:
    """Base plain-completion prompt: signature line + a docstring holding the spec description."""
    sig = SPECS[u]["signature"]
    desc = SPECS[u]["description"]
    desc = re.sub(r"^Task: write a Python function [^ ]+ that ", "Return ", desc)
    return f"def {sig}:\n    \"\"\"{desc}\"\"\"\n"


def build_unit_prompts(tok: Any, u: str, used_nouns: set[str]) -> list[dict[str, Any]]:
    spec = spec_text(u)
    noun = pick_noun(tok, u, used_nouns)
    used_nouns.add(noun)
    n_noun = len(tok(noun, add_special_tokens=False)["input_ids"])
    L = L_u(tok, u)
    d = max(0, L - n_noun)
    rows = []
    for w in TEMPLATE_IDS:
        seg = TEMPLATES[w][1].format(N=noun) + PAD_FILLER * d
        rows.append(record(tok, u, w, "twin", seg, spec, noun=noun, n_pad=d, L_u=L,
                           source="R2 twin builder: neutral noun padded to L_u = max display-name token count"))
    rows.append(record(tok, u, "ALL", "novelty", NOVELTY, spec, source="frozen novelty sentence"))
    rows.append(record(tok, u, "ALL", "plain", None, spec, source="specification only"))
    txt = plainc_prompt(u)
    ids = tok(txt, add_special_tokens=False)["input_ids"]
    rows.append({"task": u, "w": "PLAINC", "kind": "plainc", "segment": "", "user_text": txt, "ids": ids,
                 "P": len(ids), "p0": 0, "p1": 0, "spec_end": len(ids), "prompt_sha256": sha256_text(json.dumps(ids)),
                 "source": "base plain completion (raw text, no chat template)"})
    return rows


def assoc_record(tok: Any, u: str, default: str) -> dict[str, Any]:
    text = cap_first(SPECS[u]["description"]) + "\n\n" + cap_first(ASSOC_TEMPLATE.format(x=display_name(u, default)))
    ids = chat_ids(tok, text)
    return {"task": u, "w": "ASSOC", "kind": "assoc", "segment": "", "user_text": text, "ids": ids, "P": len(ids),
            "p0": 0, "p1": 0, "spec_end": len(ids), "prompt_sha256": sha256_text(json.dumps(ids)),
            "default": default, "source": "bench build_association (description + association template)"}


def audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    rep: dict[str, Any] = {"units": {}}
    by: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by.setdefault(r["task"], []).append(r)
    for u, rs in by.items():
        chat = [r for r in rs if r["kind"] in ("twin", "novelty", "plain")]
        tails = {json.dumps(r["ids"][r["p1"]:]) for r in chat}
        assert len(tails) == 1, f"{u}: spec ids differ across arms"
        s = SPECS[u]
        names = [d for _, d, _ in s["catalogue"]] + [a for v in s["aliases"].values() for a in v]
        seg_hits = []
        for r in rs:
            if r["kind"] not in ("twin", "novelty"):
                continue
            seg = r["segment"].lower()
            for a in names:
                if re.search(rf"(?<![a-z]){re.escape(a.lower())}(?![a-z])", seg):
                    seg_hits.append({"kind": r["kind"], "w": r["w"], "name": a})
        da = description_audit(u)
        tw = [r for r in rs if r["kind"] == "twin"]
        rep["units"][u] = {"noun": tw[0]["noun"], "n_pad": tw[0]["n_pad"], "L_u": tw[0]["L_u"],
                           "twin_P": {r["w"]: r["P"] for r in tw}, "S_len": tw[0]["spec_end"] - tw[0]["p1"],
                           "segment_hits": seg_hits, **da,
                           "pass": not seg_hits and not da["algo_word_hits"] and not da["catalogue_name_hits"]}
    rep["all_pass"] = all(v["pass"] for v in rep["units"].values())
    return rep


def stage_specs(units: list[str]) -> dict[str, Any]:
    tok = load_tokenizer()
    rows: list[dict[str, Any]] = []
    used: set[str] = set()
    for r in read_jsonl(PROMPTS_EXISTING):
        if r["kind"] == "twin" and r["segment"]:
            used.add(r["segment"].split()[3].strip(".").lower() if r["segment"].startswith("Do not use") else "")
    for u in units:
        write_spec(u)
        rows += build_unit_prompts(tok, u, used)
    rep = audit(rows)
    write_jsonl(PROMPTS_NEW, rows)
    write_json(RESULTS / "prompt_audit.json", rep)
    logger.info(f"specs frozen for {units}; prompt audit all_pass={rep['all_pass']}")
    for u, v in rep["units"].items():
        logger.info(f"  {u}: noun={v['noun']} pad={v['n_pad']} L_u={v['L_u']} S={v['S_len']} pass={v['pass']} "
                    f"{v['algo_word_hits']} {v['catalogue_name_hits']} {v['segment_hits']}")
    return rep


def load_prompts() -> dict[tuple[str, str, str], dict[str, Any]]:
    """(task, w, kind) -> prompt record for the new units and the 15 existing tasks (exp19 prompts.jsonl)."""
    out = {}
    for r in read_jsonl(PROMPTS_EXISTING):
        out[(r["task"], r["w"], r["kind"])] = r
    for r in read_jsonl(PROMPTS_NEW):
        out[(r["task"], r["w"], r["kind"])] = r
    for r in read_jsonl(DATA / "prompts_assoc.jsonl"):
        out[(r["task"], r["w"], r["kind"])] = r
    return out


if __name__ == "__main__":
    setup_logging("specs5")
    us = sys.argv[1].split(",") if len(sys.argv) > 1 else ["A1", "A2", "A3", "A4", "A5", "A6", "A7"]
    stage_specs(us)
