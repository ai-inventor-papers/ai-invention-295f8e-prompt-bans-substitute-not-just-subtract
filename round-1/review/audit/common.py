"""Shared helpers for the review audit: read JSONL rows, count labels, compute Hill_cc."""
import json
import math
import os
from collections import Counter
from pathlib import Path

# Directory holding the iteration-1 artifacts (gen_art_dataset_1, gen_art_experiment_1..6).
ART = Path(os.environ.get("AII_GEN_ART", "."))


def rows(path):
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def truthy(v):
    return v is True or str(v).lower() == "true"


def hill(counter):
    n = sum(counter.values())
    if n == 0:
        return float("nan")
    h = -sum((c / n) * math.log(c / n) for c in counter.values() if c > 0)
    return math.exp(h)


def summ(sel, banned=None):
    labels = Counter(str(r.get("label")) for r in sel)
    correct = [r for r in sel if truthy(r.get("passed"))]
    cl = Counter(str(r.get("label")) for r in correct)
    out = {
        "N": len(sel),
        "labels": dict(labels.most_common()),
        "pass": round(len(correct) / len(sel), 3) if sel else None,
        "correct_labels": dict(cl.most_common()),
        "hill_cc": round(hill(cl), 3) if correct else None,
    }
    if banned is not None:
        bset = set(banned) if isinstance(banned, (list, set, tuple)) else {banned}
        out["banned_share"] = round(sum(labels[b] for b in bset) / len(sel), 3) if sel else None
        comp = Counter(str(r.get("label")) for r in correct if str(r.get("label")) not in bset)
        out["compliant"] = dict(comp.most_common())
        out["n_compliant"] = sum(comp.values())
    return out
