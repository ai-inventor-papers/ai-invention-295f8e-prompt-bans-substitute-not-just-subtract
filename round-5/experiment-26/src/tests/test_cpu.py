#!/usr/bin/env python3
"""T0 CPU checks (plan testing_plan T0), aggregated into results/tests_cpu.json:
(a) every reference passes every hidden test within 0.25 x the limit, every mutant fails, every excluded method fails
    a stress case, the two oracles agree (units/<u>/build_report.json, re-asserted here);
(b) runtime and AST labellers are 100% on references; the instrumented element type counts known operations exactly;
(c) the spec grep against BANNED_WORDS returns 0 hits for every unit and variant;
(d) prompt rendering: the task-spec span decodes to spec_text (asserted at build) and the noun/padding rule holds;
(e) the commit chain verifies; the grep audit flags a planted ban prompt (positive control) and passes the real ones.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import units_extra  # noqa: E402,F401
import quantities  # noqa: E402
from cfg5 import RESULTS_DIR, UNITS_DIR, read_json, write_json  # noqa: E402
from commit5 import verify  # noqa: E402
from units_spec import UNITS, UNIT_ORDER, grep_banned  # noqa: E402
from unitlib import run_trace  # noqa: E402

res: dict = {}
# (a), (b)
for u in UNIT_ORDER:
    b = read_json(UNITS_DIR / u / "build_report.json")
    ok = {"oracles_agree": not b["oracle_disagreements"], "references_pass": all(b["references_pass_all"].values()),
          "references_fast": all(not v for v in b["references_slow_cases"].values()),
          "mutants_fail": all(v["fails"] for v in b["mutants"].values()),
          "excluded_fail": all(v["fails_stress"] for v in b["excluded_by_limit"].values()),
          "labellers_on_references": all(v["ok"] for v in b["labellers_on_references"].values()),
          "probes_run": b["probes_run"], "stage_i": b["stage_i"]}
    assert all(v is True for k, v in ok.items() if k != "stage_i") and ok["stage_i"] == "PROVISIONAL", (u, ok)
    res[f"build_{u}"] = ok
# (b) tracer counts known operations exactly on a toy program
tr = run_trace("def solve(nums):\n    r = 0\n    for v in nums:\n        r ^= v\n    return r + 0\n",
               [{"name": "toy", "args": [[1, 2, 3, 4, 5]], "wrap": ["ints"], "expected": 1}])
ops = tr["toy"]["ops"]
assert ops.get("xor") == 5 and tr["toy"]["correct"] is True, ops
res["tracer_toy_xor_count"] = ops
tr2 = run_trace("def solve(s, t):\n    return sorted(s) == sorted(t)\n",
                [{"name": "toy", "args": ["abc", "cab"], "wrap": ["str", "str"], "expected": True}])
assert tr2["toy"]["ccalls"].get("sorted") == 2 and tr2["toy"]["ops"].get("ccmp", 0) > 0, tr2
res["tracer_toy_sorted"] = {"ccalls": tr2["toy"]["ccalls"], "ops": tr2["toy"]["ops"]}
# (c)
hits = {u: grep_banned(u, UNITS[u]["description"]) for u in UNITS if not u.startswith("P_")}
assert all(not v for v in hits.values()), hits
res["spec_grep_banned_hits"] = hits
# (d)
for u in UNIT_ORDER:
    pos = read_json(UNITS_DIR / u / "positions.json")
    nn = read_json(UNITS_DIR / u / "neutral_nouns.json")
    assert all(v["spec_decoded"] is not None for v in pos.values())
    res[f"prompt_{u}"] = {"noun": nn["word"], "abs_token_diff": nn["abs_diff"], "templates": sorted(pos)}
# (e) chain + planted-ban positive control
v = verify()
assert v["chain_breaks"] == 0, v
res["commit_chain"] = v
real = {u: quantities.grep_audit(u)["pass"] for u in UNIT_ORDER}
assert all(real.values()), real
planted = {"pid": "B1|twin|-|PLANTED", "unit": "B1", "kind": "twin",
           "segment": "Do not use an XOR fold over indices and values for this task.", "user_text": ""}
with tempfile.TemporaryDirectory() as td:
    p = Path(td) / "prompts.jsonl"
    p.write_text(json.dumps(planted) + "\n")
    old = quantities.PROMPTS
    quantities.PROMPTS = p
    try:
        g = quantities.grep_audit("B1")
    finally:
        quantities.PROMPTS = old
assert not g["pass"] and g["violations"], g
res["grep_audit_real_prompts_pass"] = real
res["grep_audit_planted_ban_flagged"] = g["violations"][:3]
write_json(RESULTS_DIR / "tests_cpu.json", res)
print(json.dumps({k: (v if not isinstance(v, dict) or len(json.dumps(v)) < 200 else "ok") for k, v in res.items()},
                 indent=1, default=str))
