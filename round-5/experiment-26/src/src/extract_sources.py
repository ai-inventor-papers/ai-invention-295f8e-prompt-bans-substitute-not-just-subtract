#!/usr/bin/env python3
"""Extract the source rows this artifact needs from the declared dependency art_j3Rm_lr2nzR6 (full_data_out.json):
LeetCode rows for candidate list B (+ reserves), every count-inversions row of kodcode/thealgorithms/xlcost, the
neutral-noun candidates of concreteness_norms, and small validation subsets of the other datasets (humanevalplus,
enamel, clrs_text, mercury, llm_creativity) used by tests/ for harness checks. Writes inputs/sources.json."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
DEP = Path(os.environ.get("AII_DEP_ART_J3RM", str(Path(__file__).resolve().parents[1].parent / "art_j3Rm_lr2nzR6")))
QIDS = {268: "B1", 136: "B2", 1135: "B3", 1584: "B3alt", 69: "B4", 78: "B5", 242: "B6", 189: "B8", 33: "B9"}
INV_RE = re.compile(r"count_inversions|inversion count|count inversions|number of inversions|inversions", re.I)


def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    d = json.loads((DEP / "full_data_out.json").read_text())
    out: dict = {"leetcode": {}, "inversions": [], "nouns": [], "validation": {}, "dataset_sizes": {}}
    for ds in d["datasets"]:
        name = ds["dataset"]
        ex = ds["examples"]
        out["dataset_sizes"][name] = len(ex)
        if name == "leetcodedataset":
            for e in ex:
                q = e.get("metadata_question_id")
                if q in QIDS:
                    out["leetcode"][str(q)] = e
        elif name in ("kodcode_algorithmic", "thealgorithms_python", "xlcost_python"):
            for e in ex:
                blob = (e.get("input") or "") + "\n" + (e.get("output") or "")
                if INV_RE.search(blob) and ("inversion" in blob.lower()):
                    out["inversions"].append({"dataset": name, **e})
        elif name == "concreteness_norms":
            for e in ex:
                if e.get("metadata_noun_bank_candidate"):
                    out["nouns"].append(e)
            if not out["nouns"]:
                keys = list(ex[0].keys())
                logger.warning(f"no neutral flag found; keys={keys}")
        if name in ("humanevalplus", "enamel", "clrs_text", "mercury", "llm_creativity"):
            out["validation"][name] = ex[:40]
    logger.info(f"leetcode rows {sorted(out['leetcode'])}; inversion rows {len(out['inversions'])}; nouns "
                f"{len(out['nouns'])}; sizes {out['dataset_sizes']}")
    (ROOT / "inputs" / "sources.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
