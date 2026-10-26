#!/usr/bin/env python3
"""EXPLORATORY (post hoc): label distribution per forced-token arm (twin prompt unchanged, N = 30 CRN slots) vs the
twin's own rows on the same slots; exact McNemar of off-default (any catalogue non-default, attempted) vs the twin."""
import sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from c7 import CATALOGUE, DATA, DEFAULTS, LABELS, RESULTS, read_jsonl, write_json  # noqa: E402
import stats7 as S  # noqa: E402

L = read_jsonl(DATA / "labels_force.jsonl")
raw = {f"{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}": r for r in read_jsonl(DATA / "samples_raw_force.jsonl")}
tw = {(r["task"], r["template"], int(r["sample_id"])): r for r in read_jsonl(LABELS) if r["arm"] == "TWIN"}
by = defaultdict(list)
for r in L:
    by[(r["task"], r["arm"])].append(r)
out = {}
for (task, arm), rows in sorted(by.items()):
    off = lambda r: int(r["label"] in CATALOGUE.get(task, []) and r["label"] != DEFAULTS[task])  # noqa: E731
    b = c = 0
    for r in rows:
        t = tw.get((task, r["template"], int(r["sample_id"])))
        if t is None:
            continue
        b += off(r) and not off(t)
        c += off(t) and not off(r)
    k = raw.get(rows[0]["key"]) if rows else None
    out.setdefault(task, {})[arm] = {"n": len(rows), "labels": dict(Counter(r["label"] for r in rows).most_common()),
                                     "pass": sum(bool(r["passed"]) for r in rows) / len(rows),
                                     "off_default_attempted": sum(off(r) for r in rows) / len(rows),
                                     "off_default_correct": sum(off(r) and bool(r["passed"]) for r in rows) / len(rows),
                                     "forced_token": (k or {}).get("forced_token"),
                                     "flips_vs_twin": {"to_off": b, "to_default": c, "p_exact": S.mcnemar_exact(b, c)}}
out["note"] = "EXPLORATORY, post hoc; the twin prompt is unchanged, only the opening tokens are forced"
write_json(RESULTS / "force_token.json", out)
for t, v in out.items():
    if isinstance(v, dict):
        for a, r in v.items():
            print(t, a, r["n"], r["labels"], round(r["pass"], 2), r["flips_vs_twin"])
