#!/usr/bin/env python3
"""Combine the V3 filters, the arm-blind manual read (decisive) and the judges into results/v3_final.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402


def main() -> None:
    cands = json.loads((C.RESULTS / "v3_filtered.json").read_text())
    key = json.loads((C.RESULTS / "manual_read_key.json").read_text())
    mr = json.loads((C.RESULTS / "manual_read.json").read_text())["reads"]
    jd = json.loads((C.RESULTS / "judges.json").read_text())
    cid2oid = {v["cid"]: o for o, v in key["judged"].items()}
    used = jd.get("judges_used", [])
    for c in cands:
        o = cid2oid.get(c["cid"])
        c["judged"] = o is not None
        c["oid"] = o
        c["unjudged_reason"] = ("passes both filters but beyond the 40 best by selection F" if
                                (o is None and c["cid"] in key["unjudged"]) else None)
        if o is not None:
            c["manual_class"] = mr[o]["manual_class"]
            c["manual_rule"] = mr[o]["rule_in_words"]
            c["manual_family"] = mr[o]["family"]
            c["judge_labels"] = {m: v["label"] for m, v in jd["candidates"].get(o, {}).items()}
            gated = [c["judge_labels"].get(m) for m in used]
            c["judges_all_not_known"] = bool(len(used) >= 2 and all(x == "NOT_KNOWN" for x in gated))
            c["judges_advisory"] = len(used) < 2
    C.write_json(C.RESULTS / "v3_final.json", cands)
    print(sum(c["judged"] for c in cands), "judged;", sum(c.get("manual_class") == "NOVEL" for c in cands), "manual NOVEL")


if __name__ == "__main__":
    main()
