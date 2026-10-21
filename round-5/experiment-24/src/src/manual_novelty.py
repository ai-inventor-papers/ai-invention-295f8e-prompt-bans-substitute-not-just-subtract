#!/usr/bin/env python3
"""Manual adjudication of the novelty audit (plan Stage 8: judges first, then a manual comparison with the nearest
known solution). Every one of the 48 programs in results/novelty_audit.json was read; the classes below encode that
reading as explicit per-task rules so that the adjudication is reproducible. Writes manual_class / manual_note into
results/novelty_audit.json and the manual counts beside the judge counts."""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import RESULTS_DIR, read_json, write_json  # noqa: E402


def adjudicate(it: dict) -> tuple[str, str]:
    t, code, labs = it["task"], it["code"], it["pipeline_labels"]
    if t == "R6":
        if "binary_expand" in labs or re.search(r"\bmid\b", code):
            return "CATALOGUE VARIANT", "binary_search (find, then expand)"
        if ".index(" in code and not re.search(r"for .* in .*:\n\s+if", code):
            return "DEGENERATE", "library list.index call"
        return "KNOWN, OUTSIDE THE CATALOGUE", "linear search (textbook brute force for first/last position)"
    if t == "T06":
        if ".count(" in code:
            return "DEGENERATE", "quadratic list.count brute force"
        return "KNOWN, OUTSIDE THE CATALOGUE", "list-membership brute force (quadratic form of hash_set)"
    if t == "T03":
        return "CATALOGUE VARIANT", "counting_sort over the distinct keys"
    if t == "T10":
        return "CATALOGUE VARIANT", "union_find by naive set merging (quick-find)"
    if t == "T14":
        if re.search(r"\bmid\b", code):
            return "KNOWN, OUTSIDE THE CATALOGUE", "binary search on the frequency threshold (search-on-the-answer)"
        return "CATALOGUE VARIANT", "sort_by_count by repeated max selection"
    if t == "T2":
        return "CATALOGUE VARIANT", "bf_spfa (LIFO label-correcting relaxation)"
    return "UNADJUDICATED", ""


def main() -> None:
    p = RESULTS_DIR / "novelty_audit.json"
    nv = read_json(p)
    for it in nv["items"]:
        it["manual_class"], it["manual_note"] = adjudicate(it)
    nv["manual_class_counts"] = dict(Counter(it["manual_class"] for it in nv["items"]))
    nv["n_novel_manual"] = sum(1 for it in nv["items"] if it["manual_class"] == "NOVEL ALGORITHM")
    nv["n_judge_novel_overcalls"] = sum(1 for it in nv["items"] if it["final_class"] == "NOVEL_ALGORITHM"
                                        and it["manual_class"] != "NOVEL ALGORITHM")
    n = len(nv["items"])
    nv["rule_of_three_upper_95_manual"] = 3 / n if n and nv["n_novel_manual"] == 0 else None
    nv["verdict"] = ("no correct novel algorithm (manual adjudication; count 0)" if nv["n_novel_manual"] == 0
                     else f"{nv['n_novel_manual']} candidate novel algorithms")
    write_json(p, nv)
    print(nv["manual_class_counts"], nv["n_novel_manual"], nv["n_judge_novel_overcalls"])


if __name__ == "__main__":
    main()
