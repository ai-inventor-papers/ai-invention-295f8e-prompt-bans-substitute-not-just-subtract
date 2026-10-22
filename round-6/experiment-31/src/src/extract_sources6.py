#!/usr/bin/env python3
"""Read the declared dependency art_j3Rm_lr2nzR6 (full_data_out.json, exp_sel_data_out) and keep only what this
artifact uses, in inputs/sources.json (all 10 datasets are touched; results/dependency_usage.json records the role of
each):
- leetcodedataset: the 12 candidate rows (problem text + reference solution) of list I;
- concreteness_norms: the flagged neutral-noun candidates (metadata_noun_bank_candidate) for the twin noun;
- kodcode_algorithmic: rows whose question matches a list-I task (extra references / oracle cross-checks);
- mercury, thealgorithms_python, xlcost_python: known-solution pool for the novelty audit (task-keyword filtered);
- humanevalplus, enamel: a harness-validation subset (canonical solutions run through the sandbox test runner);
- clrs_text, llm_creativity: counts only (no list-I task is covered; logged as not applicable).
Usage: uv run src/extract_sources6.py   (env AII_DEP_ART_J3RM = folder holding full_data_out.json)
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

from cfg6 import INPUTS, RESULTS_DIR, setup_logging, sha256_file, write_json  # noqa: E402
from units_spec6 import UNITS  # noqa: E402

DEP_DEFAULT = Path(__file__).resolve().parents[1].parent / "art_j3Rm_lr2nzR6"
TASK_KEYWORDS = {
    "I1": [r"longest consecutive"], "I2": [r"anagram"], "I3": [r"happy number"], "I4": [r"h-index", r"h index"],
    "I5": [r"meeting room", r"minimum number of (conference )?rooms", r"meeting rooms"],
    "I6": [r"sort colou?rs", r"dutch national flag", r"0s, 1s,? and 2s"], "I7": [r"counting bits", r"count(ing)? set bits"],
    "I8": [r"first missing positive", r"smallest missing positive"],
    "I9": [r"intersection of two arrays"], "I10": [r"best time to buy and sell stock", r"maximum profit"],
    "I11": [r"rotate (an )?array", r"rotate the array", r"array rotation"],
    "I12": [r"gcd of (an )?array", r"greatest common divisor of (an )?array", r"gcd of all"],
}


def dep_dir() -> Path:
    return Path(os.environ.get("AII_DEP_ART_J3RM", str(DEP_DEFAULT)))


def match_units(text: str) -> list[str]:
    low = (text or "").lower()
    return [u for u, pats in TASK_KEYWORDS.items() if any(re.search(p, low) for p in pats)]


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("extract_sources6")
    p = dep_dir() / "full_data_out.json"
    logger.info(f"reading {p.name} ({p.stat().st_size / 1e6:.1f} MB)")
    d = json.loads(p.read_text())
    slugs = {UNITS[u]["slug"]: u for u in UNITS}
    out: dict = {"leetcode": {}, "nouns": [], "kodcode": [], "known_pool": [], "harness": [], "counts": {}}
    usage: dict = {}
    for ds in d["datasets"]:
        name, exs = ds["dataset"], ds["examples"]
        out["counts"][name] = len(exs)
        if name == "leetcodedataset":
            for e in exs:
                if e.get("metadata_task_slug") in slugs:
                    out["leetcode"][slugs[e["metadata_task_slug"]]] = e
            usage[name] = {"role": "problem text + reference solution of the 12 list-I candidates",
                           "n_used": len(out["leetcode"])}
        elif name == "concreteness_norms":
            out["nouns"] = [{"input": e["input"], "metadata_subtlex_frequency": e.get("metadata_subtlex_frequency"),
                             "tokens_ws": e.get("metadata_qwen3_tokens_with_leading_space")}
                            for e in exs if e.get("metadata_noun_bank_candidate") is True]
            usage[name] = {"role": "neutral-noun bank for the twin prompts", "n_used": len(out["nouns"])}
        elif name == "kodcode_algorithmic":
            for e in exs:
                us = match_units(e.get("input", ""))
                if us:
                    out["kodcode"].append({"units": us, "input": e["input"][:3000], "output": e["output"],
                                           "id": e.get("metadata_question_id")})
            usage[name] = {"role": "extra test-verified solutions of list-I tasks (oracle cross-check, novelty pool)",
                           "n_used": len(out["kodcode"])}
        elif name in ("mercury", "thealgorithms_python", "xlcost_python"):
            n0 = len(out["known_pool"])
            for e in exs:
                us = match_units((e.get("input") or "") + " " + str(e.get("metadata_slug") or ""))
                if us:
                    out["known_pool"].append({"source": name, "units": us, "code": e["output"] if name == "mercury"
                                              else e.get("output") or e.get("input"), "text": (e.get("input") or "")[:500]})
            usage[name] = {"role": "known-solution pool for the novelty audit", "n_used": len(out["known_pool"]) - n0}
        elif name in ("humanevalplus", "enamel"):
            for e in exs[:12]:
                out["harness"].append({"source": name, "input": e.get("input"), "output": e.get("output"),
                                       "meta": {k: v for k, v in e.items() if k.startswith("metadata_")
                                                and isinstance(v, (str, int, float, bool)) and len(str(v)) < 4000}})
            usage[name] = {"role": "sandbox harness validation subset (first 12 rows)", "n_used": 12}
        else:
            usage[name] = {"role": "not applicable to list I (no list-I task covered); counted only", "n_used": 0}
    write_json(INPUTS / "sources.json", out)
    usage["_source_file_sha256"] = sha256_file(p)
    write_json(RESULTS_DIR / "dependency_usage.json", usage)
    logger.info(f"leetcode {len(out['leetcode'])}, nouns {len(out['nouns'])}, kodcode {len(out['kodcode'])}, "
                f"known pool {len(out['known_pool'])}, harness {len(out['harness'])}")


if __name__ == "__main__":
    main()
