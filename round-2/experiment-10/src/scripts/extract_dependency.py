#!/usr/bin/env python3
"""Extract from the dataset artifact (art_j3Rm_lr2nzR6): (1) the 718 neutral-noun candidates of concreteness_norms,
(2) an inventory of all 10 datasets, (3) a count of the code-bearing examples (the scrubber stress test, scripts/scrub_stress.py, reads them directly), and
(4) the llm_creativity T02 label distribution (external reference). Writes into data/ (read-only source)."""
import collections
import json
import os
import sys
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
# dataset artifact art_j3Rm_lr2nzR6, published as a sibling folder; override with AII_DEP_DATASET=<its full_data_out.json>
DEP_FILE = Path(os.environ.get("AII_DEP_DATASET") or WS.parent / "art_j3Rm_lr2nzR6" / "full_data_out.json")
OUT = WS / "data"


def main() -> None:
    d = json.loads(DEP_FILE.read_text())
    inv = {}
    nouns = []
    code_rows = []
    creativity = collections.Counter()
    for ds in d["datasets"]:
        name = ds["dataset"]
        ex = ds["examples"]
        inv[name] = {"n_examples": len(ex), "fields": sorted(ex[0].keys()) if ex else []}
        if name == "concreteness_norms":
            for e in ex:
                if e.get("metadata_noun_bank_candidate") in (True, "True", "true"):
                    nouns.append({"word": e["input"], "subtlex": float(e["metadata_subtlex_frequency"]),
                                  "concreteness": float(e["output"]),
                                  "qwen3_tokens": e.get("metadata_qwen3_tokens_with_leading_space")})
        elif name == "llm_creativity":
            for e in ex:
                creativity[str(e.get("metadata_t02_mode"))] += 1
        # code-bearing datasets: program text is the `output` field (thealgorithms/kodcode/xlcost/mercury/leetcode/
        # enamel/humanevalplus); clrs_text is trace text (scrubbed as text only)
        if name in ("thealgorithms_python", "kodcode_algorithmic", "xlcost_python", "mercury", "leetcodedataset",
                    "enamel", "humanevalplus", "clrs_text"):
            for i, e in enumerate(ex):
                txt = e.get("output") if name != "clrs_text" else e.get("input")
                if isinstance(txt, str) and txt.strip():
                    code_rows.append({"dataset": name, "idx": i, "text": txt,
                                      "named": e.get("metadata_named_algorithms"),
                                      "mode": e.get("metadata_bench_mode") or e.get("metadata_mode")})
    inv["concreteness_norms"]["n_noun_bank_candidates"] = len(nouns)
    inv["llm_creativity"]["t02_mode_counts"] = dict(creativity)
    (OUT / "noun_bank.json").write_text(json.dumps(nouns, indent=0))
    (OUT / "dependency_inventory.json").write_text(json.dumps(inv, indent=1))
    print(json.dumps({k: v["n_examples"] for k, v in inv.items()}, indent=1))
    print("nouns", len(nouns), "code rows", len(code_rows), "creativity", dict(creativity))


if __name__ == "__main__":
    sys.exit(main())
