#!/usr/bin/env python3
"""T7: labeller re-check (CPU). B3: the 4 references and 30 iteration-7 twin programs re-labelled against their stored
labels; T10: the 4 bench references and the 22-item gold set against their gold labels."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import label_k3 as LK  # noqa: E402

B3_REF = ROOT / "inputs" / "iter5_exp26" / "units" / "B3" / "references"
T10_DIR = ROOT / "inputs" / "iter6_exp30" / "inputs" / "exp11" / "bench" / "T10_connected_components"
E35_DATA = Path(__file__).resolve().parents[4] / "round-7/experiment-35/src/data"


def fence(code: str) -> str:
    return "```python\n" + code.strip() + "\n```"


def main() -> None:
    t0 = time.time()
    rows, truth = [], []
    for f in sorted(B3_REF.glob("*.py")):
        rows.append({"sid": f"ref|B3|{f.stem}", "unit": "B3", "text": fence(f.read_text())})
        truth.append(f.stem)
    for f in sorted((T10_DIR / "references").glob("*.py")):
        rows.append({"sid": f"ref|T10|{f.stem}", "unit": "T10", "text": fence(f.read_text())})
        truth.append(f.stem)
    for l in (T10_DIR / "gold_set.jsonl").read_text().splitlines():
        g = json.loads(l)
        rows.append({"sid": f"gold|T10|{g['gold_id']}", "unit": "T10", "text": fence(g["code"])})
        truth.append(g.get("adjudicated"))
    stored = {}
    if (E35_DATA / "labels.jsonl").exists():
        for l in (E35_DATA / "labels.jsonl").read_text().splitlines():
            r = json.loads(l)
            if r["sid"].startswith("B3|TWIN|TWIN|") and r["label"] != "disputed":
                stored[r["sid"]] = r
        raw = {}
        for l in (E35_DATA / "samples_raw.jsonl").read_text().splitlines():
            r = json.loads(l)
            if r["sid"] in stored:
                raw[r["sid"]] = r["text"]
        for sid in sorted(stored)[:30]:
            rows.append({"sid": f"tw|{sid}", "unit": "B3", "text": raw[sid]})
            truth.append(stored[sid]["label"])
    res = LK.label_rows(rows)
    out = []
    for r, t, o in zip(rows, truth, res):
        out.append({"sid": r["sid"], "truth": t, "label": o["label"], "passed": o["passed"],
                    "labeller_source": o["labeller_source"], "agree": o["label"] == t})
    summ = {}
    for grp in ("ref|B3", "ref|T10", "gold|T10", "tw|B3"):
        g = [x for x in out if x["sid"].startswith(grp)]
        if g:
            summ[grp] = {"n": len(g), "agree": sum(x["agree"] for x in g), "passed": sum(x["passed"] for x in g)}
    res_all = {"summary": summ, "rows": out, "seconds": round(time.time() - t0, 1)}
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "labeller_check.json").write_text(json.dumps(res_all, indent=1))
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
