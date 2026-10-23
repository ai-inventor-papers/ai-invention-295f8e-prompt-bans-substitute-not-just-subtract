#!/usr/bin/env python3
"""STEP A1-A3: the kth-smallest labeller extended to counting sort in dictionary form, validated on the vendored bench
references, the gold set and five constructed controls BEFORE any relabel, then applied to every T03 row of exp33."""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from loguru import logger

from sections.common import BENCH_ROOT, ROOT, cohen_kappa, dep, read_jsonl, src_ref, write_csv, write_json, RESULTS, TABLES

sys.path.insert(0, str(BENCH_ROOT))
sys.path.insert(0, str(ROOT))

from bench.common.astrules import ast_label as ast_v1  # noqa: E402  frozen bench rules (unchanged)
from bench.common.harness import run_tests  # noqa: E402
from bench.common.probes import run_trace  # noqa: E402
from bench.common.rtrules import runtime_label as rt_v1  # noqa: E402
from bench.common.testgen import read_tests  # noqa: E402
from labeller_v2 import ast_rules_v2, runtime_rules_v2  # noqa: E402
from labeller_v2.controls import NEGATIVE, POSITIVE  # noqa: E402

T03_DIR = BENCH_ROOT / "bench" / "T03_kth_smallest"
N_WORKERS = 12


def trace_labels(code: str | None) -> dict[str, Any]:
    """Old and new runtime and AST labels of one program from one sandboxed trace."""
    if not code or "def solve" not in code:
        return {"rt_v1": "invalid", "rt_v2": "invalid", "ast_v1": "invalid", "ast_v2": "invalid"}
    a1, a2 = ast_v1("T03", code), ast_rules_v2.ast_label("T03", code)
    try:
        tr = run_trace(code, "T03")
    except Exception as e:  # noqa: BLE001 - a crashed tracer is recorded, never dropped
        logger.error(f"tracer failed: {e}")
        return {"rt_v1": "unknown", "rt_v2": "unknown", "ast_v1": a1, "ast_v2": a2, "trace_error": str(e)}
    out = {"rt_v1": rt_v1("T03", tr), "rt_v2": runtime_rules_v2.runtime_label("T03", tr), "ast_v1": a1, "ast_v2": a2}
    f = (tr.get("probes", {}).get("rand300") or {}).get("features") or {}
    out["sig"] = {"sorted_lens": f.get("sorted_lens"), "sort_lens": f.get("sort_lens"), "cint": f.get("cint"),
                  "heap": f.get("heap"), "dict_sizes": f.get("dict_sizes")}
    return out


def combine(rt: str, ast: str) -> tuple[str, str, bool]:
    """exp33's bench combination (label_worker_v4.label_bench_rows): runtime first; a judge only where the runtime
    label is unknown or a known AST label disagrees; without a judge the fallback is runtime, else AST, else other."""
    if rt == "invalid":
        return "invalid", "extraction", False
    need = rt == "unknown" or (ast != "unknown" and ast != rt)
    if need:
        lab = rt if rt != "unknown" else (ast if ast != "unknown" else "other")
        return lab, "rule_fallback(needs_adjudication)", True
    return rt, ("runtime+ast" if ast == rt else "runtime(ast_unknown)"), False


def _par(fn, xs):
    with ThreadPoolExecutor(N_WORKERS) as ex:
        return list(ex.map(fn, xs))


# ------------------------------------------------------------------------------------------------ A2 validation
def validate() -> dict[str, Any]:
    refs = sorted((T03_DIR / "references").glob("*.py"))
    gold = read_jsonl(T03_DIR / "gold_set.jsonl")
    cases = read_tests(T03_DIR / "tests.jsonl")
    ref_rows = []
    for p, lab in zip(refs, _par(lambda p: trace_labels(p.read_text()), refs)):
        ref_rows.append({"ref": p.stem, **{k: lab[k] for k in ("rt_v1", "rt_v2", "ast_v1", "ast_v2")}})
    ref_agree_v2 = sum(r["rt_v2"] == r["ref"] and r["ast_v2"] == r["ref"] for r in ref_rows) / len(ref_rows)
    ref_agree_v1 = sum(r["rt_v1"] == r["ref"] and r["ast_v1"] == r["ref"] for r in ref_rows) / len(ref_rows)
    glabs = _par(lambda g: trace_labels(g["code"]), gold)
    g_rows = []
    for g, lab in zip(gold, glabs):
        g_rows.append({"gold_id": g["gold_id"], "source": g["source"], "stored_runtime": g["runtime"],
                       "stored_ast": g["ast"], "adjudicated": g.get("adjudicated"), "known": g.get("known"),
                       **{k: lab[k] for k in ("rt_v1", "rt_v2", "ast_v1", "ast_v2")}})

    def gate(rt_key: str, ast_key: str) -> dict[str, Any]:
        rt = [r[rt_key] for r in g_rows]
        at = [r[ast_key] for r in g_rows]
        adj = [r for r in g_rows if r["adjudicated"]]
        return {"n": len(g_rows), "kappa_runtime_ast": cohen_kappa(rt, at),
                "runtime_vs_adjudicated": sum(r[rt_key] == r["adjudicated"] for r in adj) / len(adj),
                "raw_agreement": sum(a == b for a, b in zip(rt, at)) / len(rt)}

    stored = gate("stored_runtime", "stored_ast")
    old, new = gate("rt_v1", "ast_v1"), gate("rt_v2", "ast_v2")
    gate_json = dep("exp33", "inputs/exp11/bench/T03_kth_smallest/gate.json")
    from sections.common import read_json
    gj = read_json(gate_json)["gold"]
    ctrl_rows = []
    for name, (want, code) in {**POSITIVE, **NEGATIVE}.items():
        lab = trace_labels(code)
        comb2 = combine(lab["rt_v2"], lab["ast_v2"])[0]
        comb1 = combine(lab["rt_v1"], lab["ast_v1"])[0]
        t = run_tests(code, "T03", cases)
        ok = comb2 == want and (name.startswith("pos") or comb2 == comb1)
        ctrl_rows.append({"control": name, "kind": "positive" if name.startswith("pos") else "negative",
                          "expected": want, "rt_v1": lab["rt_v1"], "ast_v1": lab["ast_v1"], "combined_v1": comb1,
                          "rt_v2": lab["rt_v2"], "ast_v2": lab["ast_v2"], "combined_v2": comb2,
                          "passes_hidden_tests": bool(t["passed"]), "n_pass": t["n_pass"], "n_cases": t["n_cases"],
                          "control_pass": bool(ok and t["passed"]), "signature": lab.get("sig")})
    res = {
        "ref_rows": ref_rows, "ref_agreement_v1": ref_agree_v1, "ref_agreement_v2": ref_agree_v2,
        "gold_rows": g_rows, "gold_stored": stored, "gold_old_recomputed": old, "gold_new": new,
        "gate_json_recorded": {k: gj[k] for k in ("kappa_runtime_ast", "runtime_vs_adjudicated", "raw_agreement", "n")},
        "old_reproduces_gate_json": abs(old["kappa_runtime_ast"] - gj["kappa_runtime_ast"]) < 1e-9 and
        abs(old["runtime_vs_adjudicated"] - gj["runtime_vs_adjudicated"]) < 1e-9,
        "controls": ctrl_rows, "controls_pass": sum(r["control_pass"] for r in ctrl_rows),
        "n_controls": len(ctrl_rows),
        "source_gold": src_ref("exp33", "inputs/exp11/bench/T03_kth_smallest/gold_set.jsonl"),
        "source_gate": src_ref("exp33", "inputs/exp11/bench/T03_kth_smallest/gate.json", "gold"),
    }
    res["no_regression"] = (res["ref_agreement_v2"] == 1.0 and new["kappa_runtime_ast"] >= gj["kappa_runtime_ast"] - 1e-9
                            and new["runtime_vs_adjudicated"] >= gj["runtime_vs_adjudicated"] - 1e-9)
    res["relabel_allowed"] = bool(res["no_regression"] and res["controls_pass"] == res["n_controls"])
    logger.info(f"A2: refs v2 {ref_agree_v2:.2f}; gold kappa old {old['kappa_runtime_ast']:.3f} new "
                f"{new['kappa_runtime_ast']:.3f}; rt-vs-adj old {old['runtime_vs_adjudicated']:.3f} new "
                f"{new['runtime_vs_adjudicated']:.3f}; controls {res['controls_pass']}/{res['n_controls']}; "
                f"relabel_allowed={res['relabel_allowed']}")
    write_csv(TABLES / "labeller_v2_validation.csv",
              [{"set": "reference", "id": r["ref"], "expected": r["ref"], **r} for r in ref_rows] +
              [{"set": "gold", "id": r["gold_id"], "expected": r["adjudicated"], **r} for r in g_rows] +
              [{"set": "control", "id": r["control"], **r} for r in ctrl_rows],
              ["set", "id", "expected", "rt_v1", "ast_v1", "rt_v2", "ast_v2", "combined_v1", "combined_v2",
               "passes_hidden_tests", "control_pass"])
    return res


# ------------------------------------------------------------------------------------------------ A3 relabel
def relabel_t03() -> dict[str, Any]:
    rows = [r for r in read_jsonl(dep("exp33", "data/labels.jsonl")) if r["task"] == "T03"]
    labs = _par(lambda r: trace_labels(r.get("code")), rows)
    out = []
    for r, lab in zip(rows, labs):
        if not r.get("valid"):
            new, src, need = "invalid", "extraction", False
        else:
            new, src, need = combine(lab["rt_v2"], lab["ast_v2"])
            same_inputs = (lab["rt_v2"], lab["ast_v2"]) == (r.get("runtime_label"), r.get("ast_label"))
            if need and same_inputs and r["labeller_source"] in ("judge", "runtime_unjudged"):
                new, src, need = r["label"], "carried(" + r["labeller_source"] + ")", False
        out.append({"sample_id": r["sample_id"], "arm": r["arm"], "slot_index": r["slot_index"],
                    "passed": bool(r.get("passed")), "valid": bool(r.get("valid")), "old_label": r["label"],
                    "old_source": r["labeller_source"], "old_runtime": r.get("runtime_label"),
                    "old_ast": r.get("ast_label"), "rt_v1": lab["rt_v1"], "ast_v1": lab["ast_v1"],
                    "rt_v2": lab["rt_v2"], "ast_v2": lab["ast_v2"], "rule_v2": new, "rule_v2_source": src,
                    "needs_adjudication": need, "code_sha256": r.get("code_sha256")})
    # placebo: the old rules recomputed here must reproduce the stored runtime/AST labels of every valid row
    v = [o for o in out if o["valid"]]
    repro_rt = sum(o["rt_v1"] == o["old_runtime"] for o in v) / max(len(v), 1)
    repro_ast = sum(o["ast_v1"] == o["old_ast"] for o in v) / max(len(v), 1)
    conf = Counter((o["old_label"], o["rule_v2"]) for o in out)
    trans = [o for o in out if o["old_label"] != o["rule_v2"]]
    unexpected = [o for o in trans if not (o["old_label"] == "other" and o["rule_v2"] == "counting_sort")]
    write_csv(TABLES / "relabel_confusion.csv",
              [{"old_label": a, "new_label": b, "n": n} for (a, b), n in sorted(conf.items())],
              ["old_label", "new_label", "n"])
    logger.info(f"A3: {len(out)} T03 rows; old rules reproduce stored runtime {repro_rt:.3f} / AST {repro_ast:.3f}; "
                f"{len(trans)} transitions, {len(unexpected)} not other->counting_sort")
    return {"rows": out, "repro_runtime": repro_rt, "repro_ast": repro_ast,
            "confusion": {f"{a}->{b}": n for (a, b), n in sorted(conf.items())},
            "n_transitions": len(trans), "unexpected_transitions": [o["sample_id"] for o in unexpected],
            "source": src_ref("exp33", "data/labels.jsonl", "task==T03")}


def high_other_cells() -> list[dict[str, Any]]:
    """Every exp33 cell (all three tasks) whose OLD 'other' share exceeds 20%."""
    rows = read_jsonl(dep("exp33", "data/labels.jsonl"))
    by: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for r in rows:
        by[(r["task"], r["arm"])][r["label"]] += 1
    cells = []
    for (t, a), c in sorted(by.items()):
        n = sum(c.values())
        if c.get("other", 0) / n > 0.2:
            cells.append({"task": t, "arm": a, "n": n, "n_other": c["other"], "other_share": c["other"] / n,
                          "labels": dict(c)})
    return cells


def run() -> dict[str, Any]:
    val = validate()
    write_json(RESULTS / "a2_validation.json", val)
    if not val["relabel_allowed"]:
        logger.error("A2 validation failed: relabel blocked (one revision round allowed)")
    rel = relabel_t03()
    write_json(RESULTS / "a3_relabel.json", rel)
    cells = high_other_cells()
    write_json(RESULTS / "a3_high_other_cells.json", cells)
    return {"validation": val, "relabel": rel, "cells": cells}
