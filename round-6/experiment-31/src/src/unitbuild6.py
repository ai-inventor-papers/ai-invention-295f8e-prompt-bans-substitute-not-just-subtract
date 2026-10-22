#!/usr/bin/env python3
"""Unit build + gate stage (i) on the CPU (plan S4 steps 1-3), one unit per call (ported from exp26 unitbuild.py):

1. hidden tests: the unit's make_tests() cases; expected outputs from TWO independent oracles that must agree on every
   case (dataset reference adapted to solve + an independent simplest method); order-free canonical forms for the
   'groups' and 'multiset' checkers, the mutated first argument for 'inplace';
2. per-case limit = max(1 s, 10 x the fastest reference), fastest = median of 5 timed sandbox runs on this machine;
   every reference must pass every case at <= 0.25 x the limit;
3. >= 3 mutants must fail at least one case; every excluded brute force must fail at least one stress case;
4. runtime and AST labellers must label every reference with its own mode (100%) and every probe must run.
Writes units/<u>/{tests.jsonl, references/<mode>.py, mutants/, build_report.json, gate_stage_i.json}.
Usage: python src/unitbuild6.py I1,I2
"""

from __future__ import annotations

import argparse
import copy
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

from cfg6 import UNITS_DIR, setup_logging, utc_now, write_json  # noqa: E402
from units_spec6 import UNITS, grep_banned, spec_text  # noqa: E402
from unitlib6 import label_code, run_tests, run_trace, unit_mod  # noqa: E402


def _exec_solve(code: str):
    ns: dict = {}
    exec(compile(code, "<oracle>", "exec"), ns)
    return ns["solve"]


def expected_of(checker: str, fn, args: list):
    a = copy.deepcopy(args)
    r = fn(*a)
    if checker == "inplace":
        return a[0]
    if checker == "groups":
        return sorted(sorted(x) for x in r)
    if checker == "multiset":
        return sorted(r)
    return r


def build(u: str, n_timing: int = 5) -> dict:
    mod = unit_mod(u)
    udir = UNITS_DIR / u
    (udir / "references").mkdir(parents=True, exist_ok=True)
    (udir / "mutants").mkdir(parents=True, exist_ok=True)
    rep: dict = {"unit": u, "utc": utc_now(), "spec_banned_hits": grep_banned(u, spec_text(u))}
    t0 = time.time()
    cases = mod.make_tests()
    fa, fb = _exec_solve(mod.ORACLE_A), _exec_solve(mod.ORACLE_B)
    disagree = []
    for c in cases:
        ea = expected_of(mod.CHECKER, fa, c["args"])
        eb = expected_of(mod.CHECKER, fb, c["args"])
        if not (ea == eb and type(ea) is type(eb)):
            disagree.append(c["case_id"])
        c["expected"] = ea
    rep["n_cases"] = len(cases)
    rep["kinds"] = {k: sum(1 for c in cases if c["kind"] == k) for k in ("example", "random", "stress")}
    rep["oracle_disagreements"] = disagree
    logger.info(f"{u}: {len(cases)} cases, oracle disagreements {len(disagree)} ({time.time() - t0:.1f}s)")
    for c in cases:
        c["limit"] = 10.0

    def timed(mode_code):
        mode, code = mode_code
        runs = [run_tests(code, cases, mod.CHECKER, stop_on_fail=False) for _ in range(n_timing)]
        return mode, runs

    with ThreadPoolExecutor(max_workers=6) as ex:
        res = dict(ex.map(timed, list(mod.REFERENCES.items())))
    med: dict[str, list[float]] = {}
    ref_pass = {}
    for mode, runs in res.items():
        ref_pass[mode] = all(r["passed"] for r in runs)
        med[mode] = [statistics.median([r["times"][i] if r["times"][i] is not None else 99.0 for r in runs])
                     for i in range(len(cases))]
        if not ref_pass[mode]:
            logger.warning(f"{u}/{mode} reference fails: {runs[0]['first_fail']} {runs[0]['msgs']}")
    for i, c in enumerate(cases):
        fastest = min(med[m][i] for m in med)
        c["limit"] = round(max(1.0, 10.0 * fastest), 4)
        c["ref_times"] = {m: round(med[m][i], 6) for m in med}
    slow = {m: [cases[i]["case_id"] for i in range(len(cases)) if med[m][i] > 0.25 * cases[i]["limit"]]
            for m in med}
    rep["references_pass_all"] = ref_pass
    rep["references_slow_cases"] = {m: v[:5] for m, v in slow.items()}
    rep["max_ref_time_by_mode"] = {m: max(v) for m, v in med.items()}
    (udir / "tests.jsonl").write_text("".join(json.dumps(c) + "\n" for c in cases))
    for m, code in mod.REFERENCES.items():
        (udir / "references" / f"{m}.py").write_text(code.lstrip())
    mut = {}
    for i, code in enumerate(mod.MUTANTS):
        (udir / "mutants" / f"mutant_{i}.py").write_text(code.lstrip())
        r = run_tests(code, cases, mod.CHECKER, stop_on_fail=True)
        mut[f"mutant_{i}"] = {"fails": not r["passed"], "first_fail": r["first_fail"]}
    rep["mutants"] = mut
    exc = {}
    for name, code in mod.EXCLUDED.items():
        stress = [c for c in cases if c["kind"] == "stress"]
        r = run_tests(code, stress, mod.CHECKER, stop_on_fail=True)
        exc[name] = {"fails_stress": not r["passed"], "first_fail": r["first_fail"],
                     "time_first_case": r["times"][0] if r["times"] else None}
    rep["excluded_by_limit"] = exc
    lab = {}
    for m, code in mod.REFERENCES.items():
        L = label_code(u, code, cases=cases, want_tests=False)
        lab[m] = {"runtime": L["runtime_label"], "ast": L["ast_label"],
                  "ok": L["runtime_label"] == m and L["ast_label"] == m}
    rep["labellers_on_references"] = lab
    pr = run_trace(mod.REFERENCES[next(iter(mod.REFERENCES))], mod.PROBES)
    rep["probes_run"] = "_error" not in pr and all(not v.get("error") for v in pr.values())
    rep["probe_correct"] = {k: v.get("correct") for k, v in pr.items()} if "_error" not in pr else None
    ok = (not rep["spec_banned_hits"] and not disagree and all(ref_pass.values()) and
          all(not v for v in slow.values()) and len(mut) >= 3 and all(v["fails"] for v in mut.values()) and
          all(v["fails_stress"] for v in exc.values()) and all(v["ok"] for v in lab.values()) and rep["probes_run"]
          and all(rep["probe_correct"].values()))
    rep["stage_i"] = "PROVISIONAL" if ok else "FAIL"
    rep["seconds"] = time.time() - t0
    write_json(udir / "build_report.json", rep)
    write_json(udir / "gate_stage_i.json", {"unit": u, "utc": utc_now(), "status": rep["stage_i"],
                                            "labellers_on_references": lab, "mutants": mut,
                                            "excluded_by_limit": exc, "oracle_disagreements": disagree})
    logger.info(f"{u}: stage (i) {rep['stage_i']}; labels on refs {lab}; mutants {mut}; excluded {exc}; "
                f"slow {slow}; pass {ref_pass}; probes {rep['probe_correct']}")
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("units")
    ap.add_argument("--n-timing", type=int, default=5)
    a = ap.parse_args()
    setup_logging("unitbuild6")
    for uu in a.units.split(","):
        build(uu, a.n_timing)
