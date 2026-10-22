#!/usr/bin/env python3
"""Unit build + gate stage (i) on the CPU (plan sections 4-5), one unit per call:

1. hidden tests: the unit's make_tests() cases; expected outputs from TWO independent oracles that must agree on every
   case (dataset reference adapted to solve + an independent second method);
2. per-case limit = max(1 s, 10 x the fastest reference), fastest = median of 5 timed sandbox runs on this machine;
   every reference must pass every case at <= 0.25 x the limit;
3. mutants must fail at least one case; every excluded_by_limit method must fail at least one stress case;
4. runtime and AST labellers must label every reference with its own mode (100%) and every probe must run.
Writes units/<u>/{tests.jsonl, references/<mode>.py, mutants/, build_report.json, gate_stage_i.json}.
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

from cfg5 import UNITS_DIR, setup_logging, utc_now, write_json  # noqa: E402
from units_spec import UNITS, grep_banned  # noqa: E402
from unitlib import label_code, run_tests, run_trace, unit_mod  # noqa: E402


def _exec_solve(code: str):
    ns: dict = {}
    exec(compile(code, "<oracle>", "exec"), ns)
    return ns["solve"]


def build(u: str, n_timing: int = 5) -> dict:
    mod = unit_mod(u)
    udir = UNITS_DIR / u
    (udir / "references").mkdir(parents=True, exist_ok=True)
    (udir / "mutants").mkdir(parents=True, exist_ok=True)
    rep: dict = {"unit": u, "utc": utc_now(), "spec_banned_hits": grep_banned(u, UNITS[u]["description"])}
    t0 = time.time()
    cases = mod.make_tests()
    fa, fb = _exec_solve(mod.ORACLE_A), _exec_solve(mod.ORACLE_B)
    disagree = []
    _src = (Path(__file__).resolve().parent / "sandbox_tests.py").read_text().split("def main():")[0]
    _ns: dict = {}
    exec(compile(_src, "<sandbox_check>", "exec"), _ns)
    host_check = _ns["_check"]
    for c in cases:
        a1, a2 = copy.deepcopy(c["args"]), copy.deepcopy(c["args"])
        ea = fa(*a1)
        eb = fb(*a2)
        if mod.CHECKER == "inplace0":
            ea, eb = a1[0], a2[0]
            ok = ea == eb
            c["expected"] = ea
        elif mod.CHECKER == "peak":
            c["expected"] = None
            ok = host_check("peak", ea, None, c["args"]) and host_check("peak", eb, None, c["args"])
        elif mod.CHECKER == "kclosest":
            pts, k = c["args"][0], c["args"][1]
            c["expected"] = sorted(x * x + y * y for x, y in pts)[k - 1]
            ok = host_check("kclosest", ea, c["expected"], c["args"]) and \
                host_check("kclosest", eb, c["expected"], c["args"])
        elif mod.CHECKER == "perms":
            import math
            c["expected"] = math.factorial(len(c["args"][0]))
            ok = host_check("perms", ea, c["expected"], c["args"]) and \
                host_check("perms", eb, c["expected"], c["args"])
        elif mod.CHECKER == "subsets":
            sa = sorted(sorted(x) for x in ea)
            sb = sorted(sorted(x) for x in eb)
            ok = sa == sb
            c["expected"] = sa
        else:
            ok = ea == eb and type(ea) is type(eb)
            c["expected"] = ea
        if not ok:
            disagree.append(c["case_id"])
    rep["n_cases"] = len(cases)
    rep["kinds"] = {k: sum(1 for c in cases if c["kind"] == k) for k in ("example", "random", "stress")}
    rep["oracle_disagreements"] = disagree
    logger.info(f"{u}: {len(cases)} cases, oracle disagreements {len(disagree)} ({time.time() - t0:.1f}s)")
    # ---- timing of references (5 sandbox runs, generous limit)
    for c in cases:
        c["limit"] = 10.0

    def timed(mode_code):
        mode, code = mode_code
        runs = [run_tests(code, cases, mod.CHECKER, stop_on_fail=False) for _ in range(n_timing)]
        return mode, runs

    with ThreadPoolExecutor(max_workers=3) as ex:
        res = dict(ex.map(timed, list(mod.REFERENCES.items())))
    med: dict[str, list[float]] = {}
    ref_pass = {}
    for mode, runs in res.items():
        ref_pass[mode] = all(r["passed"] for r in runs)
        med[mode] = [statistics.median([r["times"][i] or 99.0 for r in runs]) for i in range(len(cases))]
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
    # ---- mutants and excluded methods (real limits)
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
    # ---- labellers on references + probes
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
          all(not v for v in slow.values()) and all(v["fails"] for v in mut.values()) and
          all(v["fails_stress"] for v in exc.values()) and all(v["ok"] for v in lab.values()) and rep["probes_run"])
    rep["stage_i"] = "PROVISIONAL" if ok else "FAIL"
    rep["seconds"] = time.time() - t0
    write_json(udir / "build_report.json", rep)
    write_json(udir / "gate_stage_i.json", {"unit": u, "utc": utc_now(), "status": rep["stage_i"],
                                            "labellers_on_references": lab, "mutants": mut,
                                            "excluded_by_limit": exc, "oracle_disagreements": disagree})
    logger.info(f"{u}: stage (i) {rep['stage_i']}; labels on refs {lab}; mutants {mut}; excluded {exc}; "
                f"slow {slow}; pass {ref_pass}")
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("units")
    ap.add_argument("--n-timing", type=int, default=5)
    a = ap.parse_args()
    setup_logging("unitbuild")
    for uu in a.units.split(","):
        build(uu, a.n_timing)
