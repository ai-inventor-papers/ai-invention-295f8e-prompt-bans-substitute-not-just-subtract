#!/usr/bin/env python3
"""Second independent check from the raw files only (no project code): engine-check per-slot agreement with the
exp17 screen labels, the per-cell sample counts (N = 50 everywhere, 0 not-run), and the label distribution of the two
cells behind the T03 headline (PN_a1 / PN_a2 vs TWIN). Writes results/rederive_extra.json."""
import json
from collections import Counter, defaultdict
from pathlib import Path

R = Path(__file__).resolve().parents[1]
rd = lambda p: [json.loads(l) for l in open(p) if l.strip()]
scr = {}
for r in rd(R / "inputs/exp17/data/labels.jsonl"):
    if r["arm"] in ("NEUTRAL", "RAND9002_a1.0", "RAND9004_a1.0") and r["task"] in ("T03", "T2") and int(r["sample_id"]) < 10:
        lab = r["label"] if r["label"] != "disputed" else (r.get("fallback_label") or "other")
        scr[(r["task"], r["arm"], r["template"], int(r["sample_id"]))] = lab
ours = {(r["task"], r["arm"], r["template"], int(r["slot"])): r["label"] for r in rd(R / "data/engine_check_labels.jsonl")}
agree = defaultdict(lambda: [0, 0])
for k, v in scr.items():
    if k in ours and (k[0], k[1]) in {("T03", "NEUTRAL"), ("T03", "RAND9002_a1.0"), ("T2", "NEUTRAL"), ("T2", "RAND9004_a1.0")}:
        agree[f"{k[0]}|{k[1]}"][0] += ours[k] == v
        agree[f"{k[0]}|{k[1]}"][1] += 1
raw = rd(R / "data/samples_raw.jsonl")
labels = {r["sample_id"]: r for r in rd(R / "data/labels.jsonl")}
cells = Counter((r["task"], r["arm"]) for r in raw)
t03 = {a: Counter(labels[r["sample_id"]]["label"] for r in raw if r["task"] == "T03" and r["arm"] == a
                  and labels[r["sample_id"]]["passed"]) for a in ("TWIN", "PN_a1", "PN_a2")}
out = {"engine_check_per_slot_agreement": {k: v[0] / v[1] for k, v in agree.items()},
       "n_samples": len(raw), "n_labelled": sum(1 for r in raw if r["sample_id"] in labels),
       "n_cells": len(cells), "cells_not_50": [list(k) for k, v in cells.items() if v != 50],
       "T03_correct_compositions": {a: dict(c) for a, c in t03.items()}}
(R / "results/rederive_extra.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
