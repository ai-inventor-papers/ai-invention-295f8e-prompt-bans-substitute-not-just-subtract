#!/usr/bin/env python3
"""STEP 0.1 - inputs and labeller re-check (CPU).

- inputs/SHA256SUMS over every copied input file; the bench files are verified against bench/commitment.json.
- Bench labellers (T03, T05, T06, T10): every catalogue reference must pass its hidden tests and be labelled as its own
  mode by the runtime and AST rules; the gold set's stored runtime/AST labels must be reproduced
  (gate.json: gold raw agreement and kappa are recomputed from the re-run labels).
- exp8 suite (T1/T2): every reference passes and is labelled as its mode (runtime and AST).
Writes results/labeller_recheck.json and results/inputs_check.json.
"""

from __future__ import annotations

import ast as _ast
import hashlib
import json
import sys
from collections import Counter

from cfg import BENCH, E11, INPUTS, RESULTS_DIR, SUITE, setup_logging, sha256_file, utc_now, write_json

for p in (str(SUITE), str(E11)):
    if p not in sys.path:
        sys.path.insert(0, p)

BENCH_DIRS = {"T03": "T03_kth_smallest", "T05": "T05_two_sum", "T06": "T06_find_duplicate",
              "T10": "T10_connected_components"}


def sha_sums() -> dict:
    lines, n = [], 0
    for f in sorted(INPUTS.rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts:
            lines.append(f"{sha256_file(f)}  {f.relative_to(INPUTS)}")
            n += 1
    (INPUTS / "SHA256SUMS").write_text("\n".join(lines) + "\n")
    com = json.loads((BENCH / "commitment.json").read_text())
    tasks = com["tasks"]
    mism = []
    checked = 0
    for t, rec in tasks.items():
        d = next((x for x in BENCH.iterdir() if x.is_dir() and x.name.startswith(t + "_")), None)
        if d is None:
            continue
        for fn, h in rec.get("files", {}).items():
            checked += 1
            if fn == "catalogue":  # bench/common/report.py: sha256 of canon_json(spec.json['catalogue'])
                from bench.common.report import canon_json, sha256_text as _sh

                ok = _sh(canon_json(json.loads((d / "spec.json").read_text())["catalogue"])) == h
            else:
                p = d / fn
                ok = p.exists() and sha256_file(p) == h
            if not ok:
                mism.append(f"{t}/{fn}")
    out = {"n_files_hashed": n, "bench_files_checked": checked, "bench_mismatches": mism, "utc": utc_now()}
    write_json(RESULTS_DIR / "inputs_check.json", out)
    return out


def kappa(a: list[str], b: list[str]) -> float:
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / n / n
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def bench_recheck() -> dict:
    from bench.common.labeling import label_one
    from bench.common.testgen import read_tests

    out = {}
    for t, dn in BENCH_DIRS.items():
        d = BENCH / dn
        cases = read_tests(d / "tests.jsonl")
        refs = {}
        for f in sorted((d / "references").glob("*.py")):
            code = f.read_text()
            row = {"sample_id": f"ref:{f.stem}", "task": t, "condition": "ref", "seed": 0, "finish_reason": "stop",
                   "text": f"```python\n{code}\n```"}
            lab = label_one(row, cases)
            refs[f.stem] = {"passed": bool(lab.get("passed")), "runtime": lab.get("runtime_label"),
                            "ast": lab.get("ast_label")}
        gold = [json.loads(l) for l in (d / "gold_set.jsonl").read_text().splitlines() if l.strip()]
        rt_new, rt_old, as_new, as_old = [], [], [], []
        for g in gold:
            row = {"sample_id": g["gold_id"], "task": t, "condition": "gold", "seed": 0, "finish_reason": "stop",
                   "text": f"```python\n{g['code']}\n```"}
            lab = label_one(row, cases)
            rt_new.append(str(lab.get("runtime_label")))
            rt_old.append(str(g.get("runtime")))
            as_new.append(str(lab.get("ast_label")))
            as_old.append(str(g.get("ast")))
        gate = json.loads((d / "gate.json").read_text())
        out[t] = {"references": refs,
                  "refs_pass_and_self_label": sum(v["passed"] and v["runtime"] == k and v["ast"] == k
                                                  for k, v in refs.items()), "n_refs": len(refs),
                  "gold_n": len(gold), "gold_runtime_reproduced": sum(a == b for a, b in zip(rt_new, rt_old)),
                  "gold_ast_reproduced": sum(a == b for a, b in zip(as_new, as_old)),
                  "gold_kappa_runtime_ast_rerun": kappa(rt_new, as_new),
                  "gate_kappa_runtime_ast": gate.get("gold", {}).get("kappa_runtime_ast"),
                  "gate_status": gate.get("status")}
        out[t]["reproduces_gate"] = (out[t]["gold_runtime_reproduced"] == len(gold) and
                                     out[t]["gold_ast_reproduced"] == len(gold))
    return out


def suite_recheck() -> dict:
    from labeller import ast_rules, runtime_rules
    from tasks.harness import evaluate_program

    out = {}
    for t, sub in (("t1", "t1_grid"), ("t2", "t2_wsp")):
        res = {}
        for f in sorted((SUITE / "tasks" / sub / "references").glob("*.py")):
            code = f.read_text()
            ev = evaluate_program(t, code)
            rl, _, _ = runtime_rules.label(t, ev["probes"])
            al, _, _ = ast_rules.label(code, t)
            res[f.stem] = {"passed": bool(ev["tests"].get("passed")), "runtime": rl, "ast": al}
        out[t] = {"references": res, "n_refs": len(res), "n_pass": sum(v["passed"] for v in res.values()),
                  "n_runtime_eq_ast": sum(v["runtime"] == v["ast"] for v in res.values())}
    return out


if __name__ == "__main__":
    setup_logging("recheck")
    r0 = sha_sums()
    b = bench_recheck()
    s = suite_recheck()
    write_json(RESULTS_DIR / "labeller_recheck.json", {"bench": b, "suite": s, "utc": utc_now()})
    print(r0, {t: (v["refs_pass_and_self_label"], v["n_refs"], v["gold_runtime_reproduced"], v["gold_ast_reproduced"],
                   v["gold_n"]) for t, v in b.items()},
          {t: (v["n_pass"], v["n_runtime_eq_ast"], v["n_refs"]) for t, v in s.items()})
