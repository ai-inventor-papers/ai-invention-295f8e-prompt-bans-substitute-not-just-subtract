#!/usr/bin/env python3
"""Arm-blind robustness check of the level-b classification.

The executor's manual reads could see each program's arm in its id, so the level-b class is re-derived for EVERY distinct
OOC program by fixed code rules that never see the arm (the same mechanism rule the reads used):
KNOWN OUTSIDE CATALOGUE if the program
  (a) bisects the numeric value range [min, max] and counts elements <= / < mid directly (no full sort of nums), or
  (b) uses a Fenwick tree (i & -i), or a BST/treap node structure (.left/.right), or
  (c) is a bucket select (value buckets, only the bucket holding rank k is sorted / recursed into), or
  (d) is a partial selection sort (k rounds of extracting the current minimum / maximum);
else not out-of-catalogue. Output: results/levelb_rule_check.json with per task x arm counts, agreement with the manual
classes, and the primary S-vs-K test recomputed at this rule-based level b.
"""

from __future__ import annotations

import ast
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis import rate_ratio_test, verdict_of  # noqa: E402
from common import DATA, RESULTS, read_jsonl, write_json  # noqa: E402

FULL_SORT = re.compile(r"sorted\(\s*nums\s*\)|nums\.sort\(|sorted\(\s*arr\s*\)|sorted\(\s*values\s*\)")


def _value_bisect(code: str) -> bool:
    if FULL_SORT.search(code):
        return False
    has_bounds = bool(re.search(r"min\(\s*\w+\s*\)", code)) and bool(re.search(r"max\(\s*\w+\s*\)", code))
    has_mid = bool(re.search(r"mid\s*=\s*\(?\s*\w+\s*\+", code)) or bool(re.search(r"mid\s*=\s*\w+\s*\+\s*\(", code))
    direct = bool(re.search(r"(for\s+\w+\s+in\s+(nums|arr|values)\b[^\n]*\n?[^\n]*<=?\s*mid)|(<=?\s*mid\s+for\s+\w+\s+in)|"
                            r"(\w+\s*<=?\s*mid\s*\))|count_le|count_less|ft\.query\(\s*mid|query\(\s*mid", code))
    idx_bisect = bool(re.search(r"unique\w*\[\s*mid\s*\]|sorted\w*\[\s*mid\s*\]|distinct\w*\[\s*mid", code))
    return has_bounds and has_mid and direct and not idx_bisect


def _bucket_select(code: str) -> bool:
    if not re.search(r"bucket", code, re.I):
        return False
    sorts_all = bool(re.search(r"for\s+\w+\s+in\s+buckets\s*:\s*\n\s*\w+\.sort\(\)", code))
    one = bool(re.search(r"sorted\(\s*bucket|buckets\[\s*\w+\s*\]\.sort\(|return\s+solve\(\s*bucket", code))
    return one and not sorts_all


def _partial_selection(code: str) -> bool:
    return bool(re.search(r"for\s+\w+\s+in\s+range\(\s*(1\s*,\s*)?k", code)) and bool(re.search(r"\bmin\(|\bmax\(|<\s*\w+\[\s*min_idx", code)) \
        and bool(re.search(r"\.pop\(|\.remove\(|\[:\s*\w+\s*\]\s*\+", code))


def rule_class(task: str, code: str) -> str:
    if task != "T03":
        return "not_out_of_catalogue"   # rules are defined for the selection task only (no T2/A3 level-b programs)
    try:
        ast.parse(code)
    except SyntaxError:
        return "not_out_of_catalogue"
    if re.search(r"&\s*-\s*\w+|&\s*\(\s*-", code):
        return "K:fenwick"
    if re.search(r"\.left\b", code) and re.search(r"\.right\b", code) and "class" in code:
        return "K:bst"
    if _value_bisect(code):
        return "K:value_bisect"
    if _bucket_select(code):
        return "K:bucket_select"
    if _partial_selection(code):
        return "K:partial_selection"
    return "not_out_of_catalogue"


def main() -> None:
    rows = read_jsonl(DATA / "samples.jsonl")
    firsts = [r for r in rows if r.get("ooc_screen") and r.get("is_first_of_distinct") and r.get("code")]
    tab: dict[str, Counter] = defaultdict(Counter)
    agree = Counter()
    disagree = []
    for r in firsts:
        rc = rule_class(r["task"], r["code"])
        isk = rc.startswith("K:")
        tab[f"{r['task']}|{r['arm']}"][rc] += 1
        man = r.get("final_class") in ("KNOWN OUTSIDE CATALOGUE", "NOVEL ALGORITHM")
        agree[(isk, man)] += 1
        if isk != man and len(disagree) < 60:
            disagree.append({"id": r["id"], "rule": rc, "manual": r.get("final_class")})
    n_arm = Counter((r["task"], r["arm"]) for r in rows)
    out = {"per_task_arm": {k: dict(v) for k, v in tab.items()},
           "agreement_with_manual": {"both_K": agree[(True, True)], "both_not": agree[(False, False)],
                                     "rule_only": agree[(True, False)], "manual_only": agree[(False, True)],
                                     "rate": (agree[(True, True)] + agree[(False, False)]) / max(sum(agree.values()), 1)},
           "disagreements": disagree, "tests": {}}
    for t in ("T03", "T2", "A3"):
        xs = sum(v for k, v in tab.get(f"{t}|S", {}).items() if k.startswith("K:"))
        res = {}
        for a in ("EAP", "BINT", "NE", "I0", "B0"):
            xk = sum(v for k, v in tab.get(f"{t}|{a}", {}).items() if k.startswith("K:"))
            tt = rate_ratio_test(xs, n_arm[(t, "S")], xk, n_arm[(t, a)])
            tt["verdict_rule"] = verdict_of(tt)
            res[f"S_vs_{a}"] = {k: tt[k] for k in ("X_S", "N_S", "X_K", "N_K", "R_hat", "LB95", "p_one_sided",
                                                   "verdict_rule")}
        out["tests"][t] = res
    l_k = sum(1 for r in firsts if r["arm"] == "L" and rule_class(r["task"], r["code"]).startswith("K:"))
    out["L_rule_levelb"] = {"X": l_k, "N": n_arm[("T03", "L")]}
    write_json(RESULTS / "levelb_rule_check.json", out)
    print({k: dict(v) for k, v in tab.items() if k.startswith("T03")}, out["agreement_with_manual"])


if __name__ == "__main__":
    main()
