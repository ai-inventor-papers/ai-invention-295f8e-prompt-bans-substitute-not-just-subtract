#!/usr/bin/env python3
"""CPU tests (testing plan items 1-3): law unit tests U5, U8 (inherited), U9 two-level tree, U10 top-k shadow, U11
replay; the change-point rule's false-positive rate and power; labeller reference re-checks for every unit (each
reference program must receive its own mode); the scoring dry run on iteration-7 data (art_MZAfDPVhM6Ui test2.json:
the minority MAE of B3 / A3 / B6 must come out as 0.083 / 0.105 / 0.043 through predict8.tvd/mae, and the B3
McNemar 17:0). Writes results/tests_cpu.json."""

from __future__ import annotations

import json
import subprocess
import sys

import numpy as np

import locate8
import predict8 as P8
from cfg8 import INPUTS, RESULTS_DIR, SRC, SRCS, read_json, write_json


def labeller_refs() -> dict:
    rows = []
    for task in ("T04", "R6", "T03", "T06", "R1", "T14", "T10", "T08"):
        d = next(p for p in (INPUTS / "iter6_exp30" / "inputs" / "exp11" / "bench").iterdir()
                 if p.name.startswith(task + "_"))
        for f in sorted((d / "references").glob("*.py")):
            rows.append({"sid": f"ref|{task}|{f.stem}", "unit": task, "text": "```python\n" + f.read_text() + "\n```",
                         "want": f.stem})
    for u in ("B3", "B6"):
        for f in sorted((INPUTS / "iter5_exp26" / "units" / u / "references").glob("*.py")):
            rows.append({"sid": f"ref|{u}|{f.stem}", "unit": u, "text": "```python\n" + f.read_text() + "\n```",
                         "want": f.stem})
    p = subprocess.run([sys.executable, str(SRC / "label8.py"), "--serve"], input=json.dumps(rows) + "\n",
                       capture_output=True, text=True, cwd=str(SRC), timeout=900)
    out = json.loads(p.stdout.strip().splitlines()[-1])
    res = {}
    for r, o in zip(rows, out):
        k = r["unit"]
        ok = o["label"] == r["want"] or r["want"].startswith(str(o["label"]))
        res.setdefault(k, {"n": 0, "ok": 0, "bad": []})
        res[k]["n"] += 1
        res[k]["ok"] += ok
        if not ok:
            res[k]["bad"].append([r["want"], o["label"], o.get("passed")])
    return res


def dry_run_iter7() -> dict:
    t2 = read_json(SRCS["exp35"] / "results" / "test2.json")["per_unit"]
    out = {}
    for u in ("B3", "A3", "B6"):
        cells = t2[u]["cells"]
        pred = {T: np.array([1 - cells[f"T{T}_p1"]["pred_a_min"], cells[f"T{T}_p1"]["pred_a_min"]])
                for T in (0.3, 0.7, 1.0, 1.3)}
        obs = {T: np.array([1 - cells[f"T{T}_p1"]["a_min"], cells[f"T{T}_p1"]["a_min"]]) for T in (0.3, 0.7, 1.0, 1.3)}
        out[u] = round(P8.mae(pred, obs), 3)
    want = {"B3": 0.083, "A3": 0.105, "B6": 0.043}
    return {"minority_mae": out, "want": want, "pass": all(abs(out[u] - want[u]) < 0.0015 for u in want)}


def main() -> None:
    res = {"law_unit_tests": P8.run_unit_tests(), "changepoint_rule": locate8._self_test(),
           "scoring_dry_run_iter7": dry_run_iter7(), "labeller_references": labeller_refs()}
    write_json(RESULTS_DIR / "tests_cpu.json", res)
    print(json.dumps({k: (v.get("pass") if isinstance(v, dict) and "pass" in v else v) for k, v in res.items()
                      if k != "labeller_references"}, default=str))
    print({k: f"{v['ok']}/{v['n']}" for k, v in res["labeller_references"].items()})


if __name__ == "__main__":
    main()
