"""Unit builder (Stage 2c): hidden tests, references, mutants, baselines and labeller self-checks of one new unit.

Inputs: newbench/<unit>/unit_def.py (REFERENCES, MUTANTS, BASELINES, gen_cases, lc_ok, PROBES), spec.json,
checker.py, runtime_rules.py, ast_rules.py; inputs/dep_dataset/leetcode_units.json (source I/O pairs).
Steps: LeetCode pairs (status ok, inside the frozen bounds) + seeded generated cases (edge, random, >= 5 stress) ->
expected from the oracle (the fastest reference) -> every reference must agree under the checker -> per-case limit
= max(1 s, 10 x the fastest reference) measured with 10 parallel workers -> every reference passes at <= 0.25 x the
limit -> every mutant and the non-catalogue baselines fail -> runtime + AST labels of every reference equal its mode.
Writes tests.jsonl, references/, mutants/, probes.json, build_report.json.
Usage: python -m newbench.common.build5 A1
"""

from __future__ import annotations

import importlib.util
import json
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from .harness5 import run_tests, run_trace, unit_path

ROOT = Path(__file__).resolve().parents[2]


def load_def(unit: str):
    p = unit_path(unit) / "unit_def.py"
    spec = importlib.util.spec_from_file_location(f"{unit}_unit_def", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _mod(unit: str, name: str):
    p = unit_path(unit) / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"{unit}_{name}_b", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def run_ref_outputs(code: str, cases: list[dict]) -> tuple[list[Any], list[float]]:
    ns: dict[str, Any] = {"__name__": "__ref__"}
    exec(compile(code, "<ref>", "exec"), ns)
    outs, times = [], []
    for c in cases:
        kw = json.loads(json.dumps(c["kwargs"]))
        t0 = time.perf_counter()
        outs.append(ns["solve"](**kw))
        times.append(time.perf_counter() - t0)
    return outs, times


def build(unit: str) -> dict[str, Any]:
    sys.setrecursionlimit(10 ** 6)
    d = unit_path(unit)
    if (d / "labeller.frozen").exists():
        raise RuntimeError(f"{unit}: labeller is frozen; the unit must not be rebuilt")
    D = load_def(unit)
    chk = _mod(unit, "checker")
    rep: dict[str, Any] = {"unit": unit, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (d / "references").mkdir(exist_ok=True)
    (d / "mutants").mkdir(exist_ok=True)
    for m, code in D.REFERENCES.items():
        (d / "references" / f"{m}.py").write_text(code.strip() + "\n")
    for i, (m, code) in enumerate(D.MUTANTS):
        (d / "mutants" / f"{m}_mut{i}.py").write_text(code.strip() + "\n")
    (d / "probes.json").write_text(json.dumps(D.PROBES, indent=1))
    # ---------------------------------------------------------------- cases
    lc = json.loads((ROOT / "inputs" / "dep_dataset" / "leetcode_units.json").read_text())[unit]
    cases = []
    n_lc_ok = n_lc_kept = 0
    for c in lc["cases"]:
        if c["status"] != "ok":
            continue
        n_lc_ok += 1
        if D.lc_ok(c["kwargs"], c["expected"]):
            cases.append({"case_id": c["case_id"], "kind": "leetcode", "kwargs": c["kwargs"],
                          "lc_expected": c["expected"]})
            n_lc_kept += 1
    rng = random.Random(f"i5A|tests|{unit}")
    gen = D.gen_cases(rng)
    max_lc = getattr(D, "MAX_LC", 40)
    if len(cases) > max_lc:
        cases = rng.sample(cases, max_lc)
    cases += gen
    rep["n_lc_ok"], rep["n_lc_kept"], rep["n_generated"] = n_lc_ok, min(n_lc_kept, max_lc), len(gen)
    # ---------------------------------------------------------------- oracle + agreement
    stress = [c for c in cases if c["kind"] == "stress"]
    ref_times = {}
    for m, code in D.REFERENCES.items():
        _, ts = run_ref_outputs(code, stress)
        ref_times[m] = sum(ts)
    oracle = min(ref_times, key=ref_times.get)
    rep["oracle"] = oracle
    exp, _ = run_ref_outputs(D.REFERENCES[oracle], cases)
    for c, e in zip(cases, exp):
        c["expected"] = e
        if c["kind"] == "leetcode" and not chk.check(c["kwargs"], c["lc_expected"], e):
            raise AssertionError(f"{unit}: oracle disagrees with LeetCode on {c['case_id']}")
        c.pop("lc_expected", None)
    for m, code in D.REFERENCES.items():
        outs, _ = run_ref_outputs(code, cases)
        bad = [c["case_id"] for c, o in zip(cases, outs) if not chk.check(c["kwargs"], c["expected"], o)]
        assert not bad, f"{unit}: reference {m} disagrees on {bad[:3]}"
    # ---------------------------------------------------------------- limits under parallel load
    def timed(code: str) -> list[float]:
        _, ts = run_ref_outputs(code, cases)
        return ts
    with ThreadPoolExecutor(10) as ex:
        tlists = dict(zip(D.REFERENCES, ex.map(timed, D.REFERENCES.values())))
    for i, c in enumerate(cases):
        fastest = min(tl[i] for tl in tlists.values())
        c["limit"] = round(max(1.0, 10 * fastest), 3)
        c["ref_times"] = {m: round(tl[i], 6) for m, tl in tlists.items()}
    with open(d / "tests.jsonl", "w") as fh:
        for c in cases:
            fh.write(json.dumps(c) + "\n")
    rep["n_cases"] = len(cases)
    rep["n_stress"] = len(stress)
    # ---------------------------------------------------------------- sandbox checks
    res: dict[str, Any] = {"references": {}, "mutants": {}, "baselines": {}}
    worst_ratio = {}
    for m, code in D.REFERENCES.items():
        tr = run_tests(code, unit, cases)
        ratio = max((t or 0) / c["limit"] for t, c in zip(tr["times"], cases)) if tr["times"] else None
        worst_ratio[m] = ratio
        res["references"][m] = {"passed": tr["passed"], "n_pass": tr["n_pass"], "max_time_over_limit": ratio,
                                "first_fail": tr["first_fail"], "load_error": tr["load_error"]}
    for i, (m, code) in enumerate(D.MUTANTS):
        tr = run_tests(code, unit, cases)
        res["mutants"][f"{m}_mut{i}"] = {"fails": not tr["passed"], "n_pass": tr["n_pass"]}
    for name, code, expect in D.BASELINES:
        tr = run_tests(code, unit, cases)
        res["baselines"][name] = {"expect": expect, "passed": tr["passed"], "n_pass": tr["n_pass"],
                                  "first_fail": tr["first_fail"]}
    # ---------------------------------------------------------------- labeller self-check on references
    rr = _mod(unit, "runtime_rules")
    ar = _mod(unit, "ast_rules")
    lab = {}
    for m, code in D.REFERENCES.items():
        trace = run_trace(code, D.PROBES)
        lab[m] = {"runtime": rr.label(trace), "ast": ar.label(code)}
    extra = {}
    for name, (m, code) in getattr(D, "VARIANTS", {}).items():
        trace = run_trace(code, D.PROBES)
        extra[name] = {"expected": m, "runtime": rr.label(trace), "ast": ar.label(code)}
    res["labels_on_references"] = lab
    res["labels_on_variants"] = extra
    res["ref_label_acc_runtime"] = sum(v["runtime"] == m for m, v in lab.items()) / len(lab)
    res["ref_label_acc_ast"] = sum(v["ast"] == m for m, v in lab.items()) / len(lab)
    res["variant_acc_runtime"] = (sum(v["runtime"] == v["expected"] for v in extra.values()) / len(extra)) if extra \
        else None
    res["variant_acc_ast"] = (sum(v["ast"] == v["expected"] for v in extra.values()) / len(extra)) if extra else None
    rep.update(res)
    rep["checks"] = {
        "references_all_pass": all(v["passed"] for v in res["references"].values()),
        "references_within_quarter_limit": all((v or 0) <= 0.25 for v in worst_ratio.values()),
        "mutants_all_fail": all(v["fails"] for v in res["mutants"].values()),
        "baselines_as_expected": all((not v["passed"]) == (v["expect"] == "fail") for v in res["baselines"].values()),
        "labellers_100pct_on_references": res["ref_label_acc_runtime"] == 1.0 and res["ref_label_acc_ast"] == 1.0}
    (d / "build_report.json").write_text(json.dumps(rep, indent=1, default=str))
    return rep


if __name__ == "__main__":
    r = build(sys.argv[1])
    print(json.dumps({k: r[k] for k in ("unit", "oracle", "n_cases", "n_lc_kept", "n_generated", "checks")}, indent=1))
    print(json.dumps(r["labels_on_references"]))
    print(json.dumps(r.get("labels_on_variants")))
    print(json.dumps({k: v for k, v in r["references"].items()}, default=str)[:1500])
    print(json.dumps(r["mutants"]), json.dumps(r["baselines"], default=str)[:800])
