#!/usr/bin/env python3
"""S2.5 analyses of the literal cell F (committed by sha256 in commit0F BEFORE the first literal-cell sample).

Inputs: data/literal_raw.jsonl (traces), data/literal_labels.jsonl (frozen exp8-suite labels of the final code),
inputs/exp21/data/raw_thinking.jsonl + samples.jsonl (exp21's same-seed top-p-1 run, the paired reference),
audit/lexicon_audit.json (judge audit of the first-approach lexicon, optional).

Definitions (frozen):
- completed = '</think>' emitted within THINK_CAP AND the answer pass stopped by itself (exp21's definition).
- C_T = number of seeds (T2, w, k), among those with all 4 temperatures completed, whose final-code label is not
  constant across T in {0.3, 0.7, 1.0, 1.3}; reported with the exact Clopper-Pearson one-sided 95% upper bound
  (and the two-sided 95% interval). The same count for the first approach named in the thinking trace.
  Sensitivity: the same counts including forced traces (label of the forced answer).
- Prediction (commit0F): C_T <= 1 of 20.
- Noise floor: byte-identical thinking rate and final-label agreement between T 0.7 and its repeat (same seed).
- Paired comparison with exp21 (top-p 1, same seed, same T): final-label agreement and the length of the common
  token prefix of the thinking traces (token identity until the first divergence).
- Phrasing clusters per T: identifier-normalised AST 4-gram shingles, Jaccard connected components at theta 0.7,
  0.8, 0.9 (exp6 metrics, verbatim), on correct programs; phrasings per idea = clusters within each label.
- Style re-gate: heap-based vs array-based Dijkstra by a structural rule (heapq push/pop vs a min-scan loop).
"""

from __future__ import annotations

import ast
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import AUDIT_DIR, DATA_DIR, INPUTS, RESULTS_DIR, read_json, read_jsonl, write_json  # noqa: E402
from cfg5 import F_PREDICTION, F_SEED_K, F_TEMPS, THINK_CAP  # noqa: E402

TEMPLATES = ["W1", "W2", "W3", "W4", "W5"]


def wilson(k: int, n: int, z: float = 1.96) -> list[float | None]:
    if n == 0:
        return [None, None]
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [float(max(0.0, c - h)), float(min(1.0, c + h))]


def clopper_pearson(x: int, n: int) -> dict[str, float | None]:
    from scipy.stats import beta

    if n == 0:
        return {"upper95_one_sided": None, "ci95_two_sided": [None, None]}
    up1 = 1.0 if x == n else float(beta.ppf(0.95, x + 1, n - x))
    lo2 = 0.0 if x == 0 else float(beta.ppf(0.025, x, n - x + 1))
    up2 = 1.0 if x == n else float(beta.ppf(0.975, x + 1, n - x))
    return {"upper95_one_sided": up1, "ci95_two_sided": [lo2, up2]}


def dijkstra_style(code: str | None) -> str | None:
    """Structural style of a Dijkstra program: 'heap' (heapq push/pop or a PriorityQueue), 'array' (a linear min-scan
    over unvisited vertices), else 'unclear'."""
    if not code:
        return None
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return "unparseable"
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Attribute):
            names.add(n.attr)
        elif isinstance(n, ast.Name):
            names.add(n.id)
        elif isinstance(n, ast.alias):
            names.add(n.name)
    if {"heappush", "heappop"} & names or "PriorityQueue" in names or "heapq" in names:
        return "heap"
    if "min" in names or any(isinstance(n, ast.Compare) for n in ast.walk(tree)):
        return "array"
    return "unclear"


def common_prefix(a: list[int], b: list[int]) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def phrasing(codes_by_label: dict[str, list[str]]) -> dict[str, Any]:
    from analysis.metrics_exp6 import clusters, jaccard_matrix, normalise_tokens, shingles

    out: dict[str, Any] = {}
    all_codes = [(lab, c) for lab, cs in codes_by_label.items() for c in cs]
    toks = [normalise_tokens(c) for _, c in all_codes]
    keep = [(lab, t) for (lab, _), t in zip(all_codes, toks) if t]
    if not keep:
        return {"n": 0}
    sh = [shingles(t) for _, t in keep]
    J = jaccard_matrix(sh)
    labs = [l for l, _ in keep]
    for th in (0.7, 0.8, 0.9):
        cl = clusters(J, th)
        per_idea = {}
        for lab in sorted(set(labs)):
            idx = [i for i, l in enumerate(labs) if l == lab]
            per_idea[lab] = int(len(set(int(cl[i]) for i in idx)))
        out[f"theta_{th}"] = {"n_clusters": int(len(set(int(c) for c in cl))), "phrasings_per_idea": per_idea}
    out["n"] = len(keep)
    return out


def run() -> dict[str, Any]:
    raw = {r["sample_id"]: r for r in read_jsonl(DATA_DIR / "literal_raw.jsonl")}
    labs = {r["sample_id"]: r for r in read_jsonl(DATA_DIR / "literal_labels.jsonl")}
    rows = []
    for sid, r in raw.items():
        l = labs.get(sid, {})
        rows.append({**{k: r.get(k) for k in ("arm", "template", "slot", "temperature", "repeat", "completed",
                                               "forced", "closed", "n_think_tokens", "first_approach", "think_ids",
                                               "seed")},
                     "label": l.get("label"), "passed": l.get("passed"), "code": l.get("code"),
                     "labelled": sid in labs})
    res: dict[str, Any] = {"n_traces": len(rows), "n_labelled": sum(r["labelled"] for r in rows),
                           "prediction": F_PREDICTION}
    # ---------------------------------------------------------------- per-T descriptives
    per_t: dict[str, Any] = {}
    for key in [f"LIT_T{t:.1f}" for t in F_TEMPS] + ["LIT_REP_T0.7"]:
        rs = [r for r in rows if r["arm"] == key]
        n = len(rs)
        comp = sum(bool(r["completed"]) for r in rs)
        tt = sorted(r["n_think_tokens"] for r in rs)
        corr = [r for r in rs if r["completed"] and r["passed"]]
        codes = defaultdict(list)
        for r in corr:
            if r["code"]:
                codes[r["label"]].append(r["code"])
        per_t[key] = {
            "n": n, "completed": comp, "completion_rate": comp / n if n else None, "completion_wilson95": wilson(comp, n),
            "forced": sum(bool(r["forced"]) for r in rs),
            "capped_think": sum(1 for r in rs if not r["closed"]),
            "pass_rate_completed": (sum(bool(r["passed"]) for r in rs if r["completed"]) / comp) if comp else None,
            "final_label_composition": dict(Counter(r["label"] for r in rs if r["completed"])),
            "final_label_composition_correct": dict(Counter(r["label"] for r in corr)),
            "final_label_composition_incl_forced": dict(Counter(r["label"] for r in rs)),
            "first_approach_composition": dict(Counter(r["first_approach"] for r in rs)),
            "think_tokens_quantiles": {q: (float(np.quantile(tt, q)) if tt else None) for q in (0.0, 0.25, 0.5, 0.75, 0.9, 1.0)},
            "think_tokens_mean": float(np.mean(tt)) if tt else None,
            "dijkstra_style": dict(Counter(dijkstra_style(r["code"]) for r in rs if r["label"] == "dijkstra")),
            "phrasing": phrasing(codes),
        }
    res["per_T"] = per_t
    # ---------------------------------------------------------------- C_T
    by_seed: dict[tuple[str, int], dict[float, dict[str, Any]]] = defaultdict(dict)
    for r in rows:
        if not r["repeat"]:
            by_seed[(r["template"], int(r["slot"]))][float(r["temperature"])] = r
    seeds = [(w, k) for w in TEMPLATES for k in F_SEED_K]
    grid = []
    full, full_forced = [], []
    for s in seeds:
        d = by_seed.get(s, {})
        cell = {"seed": f"{s[0]}|{s[1]}", "labels": {f"{t:.1f}": (d[t]["label"] if t in d else None) for t in F_TEMPS},
                "first_approach": {f"{t:.1f}": (d[t]["first_approach"] if t in d else None) for t in F_TEMPS},
                "completed": {f"{t:.1f}": (bool(d[t]["completed"]) if t in d else None) for t in F_TEMPS},
                "passed": {f"{t:.1f}": (d[t]["passed"] if t in d else None) for t in F_TEMPS}}
        grid.append(cell)
        if all(t in d and d[t]["completed"] for t in F_TEMPS):
            full.append(cell)
        if all(t in d for t in F_TEMPS):
            full_forced.append(cell)

    def count_change(cells: list[dict[str, Any]], field: str) -> int:
        return sum(1 for c in cells if len(set(c[field].values())) > 1)

    ct = count_change(full, "labels")
    cfa = count_change(full, "first_approach")
    res["seed_grid"] = grid
    res["C_T"] = {"n_seeds_all4_completed": len(full), "n_change_final_label": ct,
                  "clopper_pearson": clopper_pearson(ct, len(full)),
                  "n_change_first_approach": cfa, "clopper_pearson_first_approach": clopper_pearson(cfa, len(full)),
                  "changed_seeds": [c["seed"] for c in full if len(set(c["labels"].values())) > 1],
                  "prediction_met": (ct <= F_PREDICTION["C_T_max"]) if full else None,
                  "sensitivity_incl_forced": {"n_seeds_all4_present": len(full_forced),
                                              "n_change_final_label": count_change(full_forced, "labels"),
                                              "n_change_first_approach": count_change(full_forced, "first_approach")},
                  "n_seeds_planned": len(seeds)}
    # ---------------------------------------------------------------- noise floor (T 0.7 vs its repeat)
    rep = {(r["template"], int(r["slot"])): r for r in rows if r["repeat"]}
    pairs = [(by_seed[s][0.7], rep[s]) for s in seeds if s in rep and 0.7 in by_seed.get(s, {})]
    res["noise_floor"] = {
        "n_pairs": len(pairs),
        "byte_identical_thinking": sum(a["think_ids"] == b["think_ids"] for a, b in pairs),
        "byte_identical_rate": (sum(a["think_ids"] == b["think_ids"] for a, b in pairs) / len(pairs)) if pairs else None,
        "label_agreement": (sum(a["label"] == b["label"] for a, b in pairs) / len(pairs)) if pairs else None,
        "first_approach_agreement": (sum(a["first_approach"] == b["first_approach"] for a, b in pairs) / len(pairs))
        if pairs else None,
        "common_prefix_tokens_median": float(np.median([common_prefix(a["think_ids"], b["think_ids"]) for a, b in pairs]))
        if pairs else None}
    # ---------------------------------------------------------------- paired with exp21 (top-p 1, same seed, same T)
    e21raw = {(r["arm"], r["template"], int(r["sample_id"])): r for r in
              read_jsonl(INPUTS / "exp21" / "data" / "raw_thinking.jsonl") if r["task"] == "T2"}
    e21lab = {(r["arm"], r["template"], int(r["sample_id"])): r for r in
              read_jsonl(INPUTS / "exp21" / "data" / "samples.jsonl") if r.get("task") == "T2"
              and str(r.get("arm", "")).startswith("THINK")}
    paired = []
    for r in rows:
        key = (f"THINK_REP_T0.7" if r["repeat"] else f"THINK_T{float(r['temperature']):.1f}", r["template"],
               int(r["slot"]))
        if key in e21raw:
            e = e21raw[key]
            el = e21lab.get(key, {})
            paired.append({"arm": r["arm"], "seed": f"{r['template']}|{r['slot']}", "label_F": r["label"],
                           "label_exp21": el.get("label"), "fa_F": r["first_approach"],
                           "fa_exp21": e.get("first_approach"),
                           "common_prefix": common_prefix(r["think_ids"] or [], e.get("think_ids") or []),
                           "len_F": len(r["think_ids"] or []), "len_exp21": len(e.get("think_ids") or [])})
    agree = [p for p in paired if p["label_exp21"] is not None]
    res["paired_exp21"] = {
        "n_pairs": len(paired), "label_agreement": (sum(p["label_F"] == p["label_exp21"] for p in agree) / len(agree))
        if agree else None,
        "first_approach_agreement": (sum(p["fa_F"] == p["fa_exp21"] for p in paired) / len(paired)) if paired else None,
        "common_prefix_tokens_quantiles": {q: float(np.quantile([p["common_prefix"] for p in paired], q))
                                           for q in (0.0, 0.25, 0.5, 0.75, 1.0)} if paired else None,
        "by_T": {a: {"n": len([p for p in paired if p["arm"] == a]),
                     "label_agreement": (lambda xs: sum(p["label_F"] == p["label_exp21"] for p in xs) / len(xs)
                                         if xs else None)([p for p in agree if p["arm"] == a]),
                     "median_common_prefix": float(np.median([p["common_prefix"] for p in paired if p["arm"] == a]))
                     if any(p["arm"] == a for p in paired) else None}
                 for a in sorted({p["arm"] for p in paired})},
        "exp21_labels_by_T": {a: dict(Counter(v.get("label") for k, v in e21lab.items() if k[0] == a))
                              for a in sorted({k[0] for k in e21lab})},
        "note": "exp21 = top-k 0 (top-p 1) with the same seeds; F = top-k 10; same checkpoint and engine flags"}
    # ---------------------------------------------------------------- lexicon judge audit (if run)
    la = AUDIT_DIR / "lexicon_audit.json"
    res["lexicon_audit"] = read_json(la) if la.exists() else {"status": "not run"}
    res["think_cap"] = THINK_CAP
    write_json(RESULTS_DIR / "literal_cell.json", res)
    return res


if __name__ == "__main__":
    out = run()
    print(json.dumps({k: out[k] for k in ("n_traces", "n_labelled", "C_T", "noise_floor")}, indent=1, default=str))
