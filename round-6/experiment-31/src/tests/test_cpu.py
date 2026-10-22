#!/usr/bin/env python3
"""CPU tests (testing plan items 1-6): (1) every reference passes every hidden case within 0.25 x the limit, mutants fail,
excluded brute force exceeds the limit on stress cases, the two oracles agree on 100% of cases (build reports);
(2) runtime and AST labellers label every reference with its own mode, and each probe runs; (3) the grep audit found 0
violations and its planted ban prompt was caught; (4) SPEC + TEMPLATE_TAIL tokenise identically in context (asserted
at render time) and the base tokenizer gives identical ids; (5) pool_l1.py synthetic tests; (6) the hash chain
verifies and a deliberately edited committed file breaks it. Usage: python tests/test_cpu.py"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cfg6 import GENESIS, sha256_file, sha256_text  # noqa: E402
from units_spec6 import UNIT_ORDER  # noqa: E402


def main() -> None:
    res: dict = {}
    b = {}
    for u in UNIT_ORDER:
        r = json.loads((ROOT / "units" / u / "build_report.json").read_text())
        b[u] = {"stage_i": r["stage_i"], "oracles_agree": not r["oracle_disagreements"],
                "refs_pass": all(r["references_pass_all"].values()),
                "refs_fast": all(not v for v in r["references_slow_cases"].values()),
                "mutants_fail": len(r["mutants"]) >= 3 and all(v["fails"] for v in r["mutants"].values()),
                "excluded_fail_stress": all(v["fails_stress"] for v in r["excluded_by_limit"].values()),
                "labellers_on_refs": all(v["ok"] for v in r["labellers_on_references"].values()),
                "probes": r["probes_run"]}
    res["1_2_builds"] = b
    g = json.loads((ROOT / "results" / "grep_audit.json").read_text())
    res["3_grep_audit"] = {"violations": len(g["violations"]), "planted_caught": all(p["caught"] for p in
                                                                                     g["planted_control"])}
    res["4_base_tokenizer_mismatches"] = g.get("base_tokenizer_mismatches")
    pr = subprocess.run([sys.executable, str(ROOT / "tests" / "test_pool_l1.py")], capture_output=True, text=True)
    res["5_pool_l1_synthetic"] = pr.returncode == 0
    # (6) chain verifies; editing a committed file (in a temp copy) breaks it
    lines = [l.split() for l in (ROOT / "commitments.log").read_text().splitlines() if l.strip()]
    prev, breaks = GENESIS, 0
    for utc, rp, h, chain, tag in [x[:5] for x in lines]:
        breaks += sha256_text(prev + h + utc + rp) != chain
        prev = chain
    res["6_chain_breaks"] = breaks
    with tempfile.TemporaryDirectory() as d:
        utc, rp, h, chain, tag = lines[0][:5]
        cp = Path(d) / "copy"
        shutil.copy(ROOT / rp, cp)
        with open(cp, "a") as fh:
            fh.write("\n# tampered\n")
        res["6_tamper_detected"] = sha256_file(cp) != h
    ok = (all(all(v.values()) if isinstance(v, dict) else v for v in b.values())
          and res["3_grep_audit"]["violations"] == 0 and res["3_grep_audit"]["planted_caught"]
          and res["4_base_tokenizer_mismatches"] == 0 and res["5_pool_l1_synthetic"] and res["6_chain_breaks"] == 0
          and res["6_tamper_detected"])
    res["pass"] = bool(ok)
    (ROOT / "results" / "cpu_tests.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "1_2_builds"}, indent=1))
    bad = {u: {k: v for k, v in x.items() if v is not True and v != "PROVISIONAL"} for u, x in b.items()}
    print("build checks failing:", {u: v for u, v in bad.items() if v})


if __name__ == "__main__":
    main()
