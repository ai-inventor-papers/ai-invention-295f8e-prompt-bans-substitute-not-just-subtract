#!/usr/bin/env python3
"""Provenance check against the declared dependency dataset art_j3Rm_lr2nzR6 (full_data_out.json): every neutral-twin
noun must be one of its flagged neutral-noun candidates in concreteness_norms, with the Qwen3 token count it records;
the LeetCode ids behind the four sampled bench tasks are listed from its leetcodedataset (bench_task mapping)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from cfg import RESULTS_DIR, write_json  # noqa: E402
from prompts import load_prompts  # noqa: E402


def main(dataset_dir: str) -> None:
    d = json.loads((Path(dataset_dir) / "full_data_out.json").read_text())
    by = {x["dataset"]: x["examples"] for x in d["datasets"]}
    cn = by["concreteness_norms"]
    keys = list(cn[0].keys())
    flag = "metadata_noun_bank_candidate" if "metadata_noun_bank_candidate" in keys else None
    tokk = next((k for k in keys if "qwen3" in k and "token" in k), None)
    words = {e["input"]: e for e in cn}
    pr = load_prompts()
    nouns = sorted({r["noun"] for r in pr.values() if r["kind"] == "twin" and r.get("noun")})
    rows = {}
    for n in nouns:
        head = n.split(",")[0].split(" ")[0]
        e = words.get(head)
        rows[n] = {"head": head, "in_concreteness_norms": e is not None,
                   "flagged_neutral_candidate": (e or {}).get(flag) if flag else None,
                   "qwen3_tokens": (e or {}).get(tokk) if tokk else None}
    lc = by["leetcodedataset"]
    bt = [{"qid": e.get("metadata_question_id"), "bench_task": e.get("metadata_bench_task")}
          for e in lc if str(e.get("metadata_bench_task") or "")[:3] in ("T03", "T04", "T05", "T06")]
    out = {"dataset": "art_j3Rm_lr2nzR6 full_data_out.json", "datasets_present": {k: len(v) for k, v in by.items()},
           "neutral_flag_field": flag, "token_field": tokk, "twin_nouns": rows,
           "all_twin_nouns_in_norms": all(v["in_concreteness_norms"] for v in rows.values()),
           "sampled_bench_task_leetcode_ids": bt}
    write_json(RESULTS_DIR / "dataset_provenance.json", out)
    print(json.dumps({k: v for k, v in out.items() if k != "twin_nouns"}, indent=1)[:1500])
    print({k: (v["in_concreteness_norms"], v["flagged_neutral_candidate"], v["qwen3_tokens"]) for k, v in rows.items()})


if __name__ == "__main__":
    # dependency dataset art_j3Rm_lr2nzR6 (published as a sibling folder): argv[1], else $ART_J3RM_DIR, else ../art_j3Rm_lr2nzR6
    import os

    main(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ART_J3RM_DIR", str(ROOT.parent / "art_j3Rm_lr2nzR6")))
