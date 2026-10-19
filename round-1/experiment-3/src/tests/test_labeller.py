"""T2/T3 unit tests: references through the sandboxed harness (tracer + AST), bad programs, harness limits, cache."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from harness.pool import LabelPool  # noqa: E402
from tasks import t1_grid, t2_wsp  # noqa: E402

pool = LabelPool(workers=8)
jobs = []
for task, T in (("T1", t1_grid), ("T2", t2_wsp)):
    for name, (lab, code) in T.REFERENCES.items():
        jobs.append((task, name, lab, "```python\n" + code + "\n```", True))
    for name, code in T.BAD_PROGRAMS.items():
        jobs.append((task, name, "FAIL", "```python\n" + code + "\n```", False))
jobs.append(("T1", "infinite_loop", "FAIL", "```python\ndef solve(grid, start, goal):\n    while True:\n        pass\n```", False))
jobs.append(("T1", "big_loop", "FAIL", "```python\ndef solve(grid, start, goal):\n    x = 0\n    for i in range(10**8):\n        x += i\n    return []\n```", False))
jobs.append(("T1", "no_block", "no_code", "def solve(grid, start, goal):\n    return []", False))
jobs.append(("T1", "no_solve", "no_code", "```python\ndef foo():\n    return 1\n```", False))
t0 = time.time()
futs = [(j, pool.submit(j[0], j[3])) for j in jobs]
summary = []
ok_all = True
for (task, name, lab, text, should_pass), fut in futs:
    r = fut.result()
    if lab == "FAIL":
        good = not r["passed"]
    elif lab == "no_code":
        good = r["label"] == "no_code" and not r["passed"]
    else:
        good = r["passed"] and r["runtime_label"] == lab and r["ast_label"] == lab
    ok_all &= good
    print(f"{'OK ' if good else 'BAD'} {task} {name:26s} exp={lab:22s} rt={r.get('runtime_label')!s:22s} "
          f"ast={r.get('ast_label')!s:22s} pass={r['passed']} rule={r.get('runtime_rule')} wall={r.get('wall_s')} err={str(r.get('first_error'))[:70]}")
    summary.append({"task": task, "name": name, "expected": lab, "runtime_label": r.get("runtime_label"),
                    "ast_label": r.get("ast_label"), "passed": r["passed"], "ok": good})
# cache test
f2 = pool.submit("T1", jobs[0][3]).result()
print("cache hit (n_cache>0):", pool.n_cache > 0, "elapsed", round(time.time() - t0, 1))
pool.shutdown()
(ROOT / "logs" / "test_labeller.json").write_text(json.dumps({"all_ok": ok_all, "rows": summary}, indent=1))
print("ALL_OK", ok_all)
