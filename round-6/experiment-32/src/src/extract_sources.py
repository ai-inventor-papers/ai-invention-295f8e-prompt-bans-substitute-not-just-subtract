#!/usr/bin/env python3
"""Extract the source rows this artifact needs from the declared dependency art_j3Rm_lr2nzR6 (full_data_out.json).

Panel II (plan 0.6): LeetCode rows metadata_question_id in {392, 621, 191, 162, 46, 20, 88, 973, 409, 9} plus the
reserves {33, 167}; per task, the kodcode_algorithmic / xlcost_python / thealgorithms_python rows whose text matches the
task's keyword regex (optional extra references and AST-rule negatives); the neutral-noun candidates of
concreteness_norms (twin prompts); and small validation subsets of every other dataset (mercury, llm_creativity,
clrs_text, humanevalplus, enamel) used by tests/test_datasets.py. Writes inputs/sources.json (+ a sha256 of the
dependency file)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
DEP = Path(os.environ.get("AII_DEP_ART_J3RM", str(ROOT.parent / "art_j3Rm_lr2nzR6")))
QIDS = {392: "II1", 621: "II2", 191: "II3", 162: "II4", 46: "II5", 20: "II6", 88: "II7", 973: "II8", 409: "II9",
        9: "II10", 33: "II11", 167: "II12"}
KEYWORDS = {
    "II1": r"is[\s_-]*subsequence|isSubsequence",
    "II2": r"task[\s_-]*scheduler|leastInterval|least[\s_-]*interval",
    "II3": r"hamming[\s_-]*weight|number of 1 bits|count[\s_-]*set[\s_-]*bits|popcount|hammingWeight",
    "II4": r"peak[\s_-]*element|findPeakElement",
    "II5": r"\bpermutations?\b|permute\(",
    "II6": r"valid[\s_-]*parenthes|balanced[\s_-]*(brackets|parenthes)|isValid\(",
    "II7": r"merge[\s_-]*(two[\s_-]*)?sorted[\s_-]*(arrays|lists)",
    "II8": r"k[\s_-]*closest[\s_-]*points|kClosest",
    "II9": r"longest[\s_-]*palindrome\b|longestPalindrome\(",
    "II10": r"palindrome[\s_-]*number|isPalindrome\(self, x",
    "II11": r"rotated[\s_-]*sorted[\s_-]*array",
    "II12": r"two[\s_-]*sum[\s_-]*ii|sorted[\s_-]*two[\s_-]*sum",
}
MAX_EXTRA_PER_TASK = 12


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@logger.catch(reraise=True)
def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    src = DEP / "full_data_out.json"
    logger.info(f"reading {src.name} ({src.stat().st_size / 1e6:.1f} MB)")
    d = json.loads(src.read_text())
    out: dict = {"dependency": "art_j3Rm_lr2nzR6", "dependency_file_sha256": sha256_file(src), "leetcode": {},
                 "extra_rows": {u: [] for u in KEYWORDS}, "nouns": [], "validation": {}, "dataset_sizes": {}}
    pats = {u: re.compile(p, re.I) for u, p in KEYWORDS.items()}
    for ds in d["datasets"]:
        name = ds["dataset"]
        ex = ds["examples"]
        out["dataset_sizes"][name] = len(ex)
        if name == "leetcodedataset":
            for e in ex:
                q = e.get("metadata_question_id")
                if q in QIDS:
                    out["leetcode"][str(q)] = {**e, "unit": QIDS[q]}
        elif name in ("kodcode_algorithmic", "thealgorithms_python", "xlcost_python"):
            for e in ex:
                blob = (e.get("input") or "") + "\n" + (e.get("output") or "")
                for u, p in pats.items():
                    if p.search(blob) and len(out["extra_rows"][u]) < MAX_EXTRA_PER_TASK * 3:
                        out["extra_rows"][u].append({"dataset": name, "input": (e.get("input") or "")[:4000],
                                                     "output": (e.get("output") or "")[:6000],
                                                     **{k: v for k, v in e.items() if k.startswith("metadata_")
                                                        and isinstance(v, (str, int, float, bool, type(None)))}})
        elif name == "concreteness_norms":
            for e in ex:
                if e.get("metadata_noun_bank_candidate"):
                    out["nouns"].append(e)
        if name in ("humanevalplus", "enamel", "clrs_text", "mercury", "llm_creativity", "thealgorithms_python"):
            out["validation"][name] = ex[:40]
    missing = sorted(set(QIDS) - {int(q) for q in out["leetcode"]})
    logger.info(f"leetcode rows {sorted(int(q) for q in out['leetcode'])}; missing {missing}; nouns "
                f"{len(out['nouns'])}; extra rows {{u: n}} = "
                f"{ {u: len(v) for u, v in out['extra_rows'].items()} }; sizes {out['dataset_sizes']}")
    (ROOT / "inputs").mkdir(exist_ok=True)
    (ROOT / "inputs" / "sources.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
