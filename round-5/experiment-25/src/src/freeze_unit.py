#!/usr/bin/env python3
"""Freeze a gated unit's labeller: gate.json + labeller.frozen, sha256-committed (tag LABELLER_<unit>), then enqueue
the unit's opening-margin job (P4). Usage: python src/freeze_unit.py A1 [round0|holdout]"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg5 import ROOT, unit_dir, utc_now, write_json  # noqa: E402
from commit5 import commit  # noqa: E402
from jobs import margin_job  # noqa: E402

if __name__ == "__main__":
    u = sys.argv[1]
    which = sys.argv[2] if len(sys.argv) > 2 else "round0"
    d = unit_dir(u)
    g0 = json.loads((d / "gate_round0.json").read_text())
    gh = json.loads((d / "gate_holdout.json").read_text()) if (d / "gate_holdout.json").exists() else None
    final = gh if which == "holdout" else g0
    gate = {"unit": u, "status": "gated" if final["gate_pass"] else "GATE_FAIL", "revision_rounds": int(which == "holdout"),
            "round0": {k: v for k, v in g0.items() if k != "items"},
            "holdout": ({k: v for k, v in gh.items() if k != "items"} if gh else None), "utc": utc_now()}
    write_json(d / "gate.json", gate)
    if final["gate_pass"]:
        (d / "labeller.frozen").write_text(utc_now() + "\n")
        files = [d / f for f in ("runtime_rules.py", "ast_rules.py", "probes.json", "tests.jsonl", "checker.py",
                                 "gate.json", "spec.json", "build_report.json")]
        files += sorted((d / "references").glob("*.py"))
        common = ROOT / "newbench" / "common"
        files += [common / f for f in ("tracer5.py", "runner5.py", "harness5.py", "label5.py", "astlib.py")]
        commit(files, f"LABELLER_{u}")
        margin_job(u, 4)
        print(f"{u}: labeller frozen and committed; margin job enqueued")
    else:
        print(f"{u}: GATE_FAIL -> excluded", json.dumps(gate["round0"], default=str)[:400])
