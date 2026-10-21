"""Labeller acceptance gate of one new unit (Stage 2c).

Gold set = every reference + 10 base pilot rows (BASE, k 0-1 of each template) + 10 instruct gold rows (TWIN, k 0-1),
labelled blind by two judges from different families with a third on disagreement (judge5.adjudicate).
GATE: references 100% (runtime and AST), Cohen's kappa(runtime, AST) >= 0.8, runtime vs adjudicated >= 0.9 (kappa is
also reported for the base and instruct halves). One revision round is allowed, scored on a holdout (BASE k 6-7 and
TWIN k 2-3, judge-labelled). On pass: newbench/<unit>/labeller.frozen + gate.json, committed by the caller.
Usage: python -m newbench.common.gate5 A1 [--holdout]
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from .harness5 import extract_code, unit_path
from .judge5 import adjudicate
from .label5 import mech_labels, spec_of

ROOT = Path(__file__).resolve().parents[2]


def cohen_kappa(a: list[str], b: list[str]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    if pe >= 1.0 - 1e-12:
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1 - pe)


def pabak(a: list[str], b: list[str]) -> float | None:
    if not a:
        return None
    po = sum(x == y for x, y in zip(a, b)) / len(a)
    k = max(len(set(a) | set(b)), 2)
    return (k * po - 1) / (k - 1)


def gold_rows(unit: str, holdout: bool = False) -> list[dict[str, Any]]:
    raw = [json.loads(l) for l in (ROOT / "data" / "raw" / f"{unit}.jsonl").read_text().splitlines() if l.strip()]
    if holdout:
        base_k, tw_k = (6, 7), (2, 3)
    else:
        base_k, tw_k = (0, 1), (0, 1)
    out = [r for r in raw if r["arm"] == "BASE" and r["model"] == "base" and int(r["slot"]) in base_k]
    out += [r for r in raw if r["arm"] == "TWIN" and r["model"] == "instruct" and int(r["slot"]) in tw_k]
    return out


def evaluate(unit: str, holdout: bool = False) -> dict[str, Any]:
    spec = spec_of(unit)
    d = unit_path(unit)
    items = []
    for m in [c["mode"] for c in spec["catalogue"]]:
        p = d / "references" / f"{m}.py"
        if p.exists():
            items.append({"kind": "reference", "half": "reference", "true": m, "code": p.read_text(), "id": f"ref:{m}"})
    for r in gold_rows(unit, holdout):
        items.append({"kind": "row", "half": "base" if r["model"] == "base" else "instruct", "true": None,
                      "code": extract_code(r["text"]), "id": r["sample_id"]})
    for it in items:
        it.update(mech_labels(unit, it["code"]) if it["code"] else {"valid": False, "runtime_label": "invalid",
                                                                      "ast_label": "invalid", "passed": False})
    judged_idx = [i for i, it in enumerate(items) if it["valid"]]
    adj = adjudicate(unit, spec, [items[i]["code"] for i in judged_idx])
    for i, a in zip(judged_idx, adj):
        items[i]["judges"] = a
        items[i]["adjudicated"] = it_true if (it_true := items[i]["true"]) else a.get("label")
        items[i]["judge_label"] = a.get("label")
    valid = [it for it in items if it["valid"]]
    rt = [it["runtime_label"] for it in valid]
    at = [it["ast_label"] for it in valid]
    res: dict[str, Any] = {"unit": unit, "holdout": holdout, "n_items": len(items), "n_valid": len(valid)}
    res["kappa_runtime_ast"] = cohen_kappa(rt, at)
    res["pabak"] = pabak(rt, at)
    res["raw_agreement"] = (sum(x == y for x, y in zip(rt, at)) / len(rt)) if rt else None
    refs = [it for it in items if it["kind"] == "reference"]
    res["ref_acc_runtime"] = sum(it["runtime_label"] == it["true"] for it in refs) / len(refs) if refs else None
    res["ref_acc_ast"] = sum(it["ast_label"] == it["true"] for it in refs) / len(refs) if refs else None
    res["judges_on_references"] = (sum(it.get("judge_label") == it["true"] for it in refs) / len(refs)) if refs else None
    adjd = [it for it in valid if it.get("adjudicated")]
    res["n_adjudicated"] = len(adjd)
    res["runtime_vs_adjudicated"] = (sum(it["runtime_label"] == it["adjudicated"] for it in adjd) / len(adjd)) \
        if adjd else None

    def combined(it):
        rl, al = it["runtime_label"], it["ast_label"]
        if rl == "unknown" or (al != "unknown" and al != rl):
            return it.get("judge_label") or "disputed"
        return rl
    res["combined_vs_adjudicated"] = (sum(combined(it) == it["adjudicated"] for it in adjd) / len(adjd)) \
        if adjd else None
    for half in ("base", "instruct"):
        hv = [it for it in valid if it["half"] == half]
        res[f"kappa_{half}"] = cohen_kappa([it["runtime_label"] for it in hv], [it["ast_label"] for it in hv])
        res[f"n_{half}_valid"] = len(hv)
        ha = [it for it in hv if it.get("adjudicated")]
        res[f"runtime_vs_adj_{half}"] = (sum(it["runtime_label"] == it["adjudicated"] for it in ha) / len(ha)) \
            if ha else None
    res["label_values"] = dict(Counter(it.get("adjudicated") for it in valid))
    res["gate_pass"] = bool(res["ref_acc_runtime"] == 1.0 and res["ref_acc_ast"] == 1.0 and
                            (res["kappa_runtime_ast"] or 0) >= 0.8 and (res["runtime_vs_adjudicated"] or 0) >= 0.9)
    res["items"] = [{k: it.get(k) for k in ("id", "kind", "half", "true", "runtime_label", "ast_label",
                                             "judge_label", "adjudicated", "passed", "valid")} |
                    {"judges": it.get("judges")} for it in items]
    return res


if __name__ == "__main__":
    u = sys.argv[1]
    ho = "--holdout" in sys.argv
    r = evaluate(u, ho)
    out = unit_path(u) / ("gate_holdout.json" if ho else "gate_round0.json")
    out.write_text(json.dumps(r, indent=1, default=str))
    print(json.dumps({k: v for k, v in r.items() if k != "items"}, indent=1, default=str))
    for it in r["items"]:
        if it["runtime_label"] != it["ast_label"] or it["runtime_label"] != it.get("adjudicated"):
            print("DISAGREE", it["id"], it["runtime_label"], it["ast_label"], it.get("judges"))
