#!/usr/bin/env python3
"""Manual-read selection (plan 4.5) and the executor's read records.

Selection: every k = 5 and held-out (k = 5) survivor of Qwen3-32B and Qwen3-14B (name-level OR mechanism-level);
every survivor whose name-level label and runtime/tracer class disagree beyond the 1.11 mapping; a 10% random sample
(seed 0) of the other survivors. `python src/manual_reads.py list` prints the programs to read (condensed);
the reads are recorded in data/manual_reads_v9.jsonl, one JSON object per program:
  {uid, algorithm, expansion_discipline, container, self_names, flag_novelty, note}
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import analysis_v9 as A  # noqa: E402
import cells_v9  # noqa: E402
from common import DATA, RESULTS, read_jsonl, write_json  # noqa: E402


def candidates() -> list[dict[str, Any]]:
    out, others = [], []
    for cid, cell in cells_v9.CELLS.items():
        rows = read_jsonl(DATA / f"labelled_v9_{cid}.jsonl")
        banned = cells_v9.banned_for(cell) or []
        for r in rows:
            if cell["kind"] == "baseline":
                continue
            ns, ms = A.named_survivor(r, banned), A.mech_survivor(r, banned)
            if not (ns or ms):
                continue
            k5 = cell["group"] in ("A", "E") and cell["payload"] == 5
            lab = r.get("label")
            exp = A.MECH_COARSE.get(lab)
            disagree = exp is not None and exp != r.get("order_class") and r.get("order_class") != "UNTRACEABLE"
            item = {"uid": r["uid"], "cell": cid, "label": lab, "other": r.get("label_other_name"),
                    "order_class": r.get("order_class"), "fine": r.get("order_class_fine"),
                    "runtime": r.get("runtime_label"), "named_survivor": ns, "mech_survivor": ms,
                    "reason": "k5_survivor" if k5 else ("label_class_disagree" if disagree else "sample")}
            (out if (k5 or disagree) else others).append(item)
    rng = random.Random(0)
    k = max(1, round(0.1 * len(others))) if others else 0
    out += sorted(rng.sample(others, k), key=lambda x: x["uid"]) if k else []
    return out


def show(uid: str) -> str:
    cid = uid.split("|")[0]
    for r in read_jsonl(DATA / f"labelled_v9_{cid}.jsonl"):
        if r["uid"] == uid:
            return r.get("code") or ""
    return ""


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list":
        c = candidates()
        write_json(RESULTS / "manual_read_candidates.json", c)
        print(json.dumps({"n": len(c), "by_reason": {r: sum(1 for x in c if x["reason"] == r)
                                                       for r in {x["reason"] for x in c}}}))
        for x in c:
            print(json.dumps(x))
    elif cmd == "show":
        for u in sys.argv[2:]:
            print("=" * 20, u)
            print(show(u))
