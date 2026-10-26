#!/usr/bin/env python3
"""The two hash-chain commits that were run inline during the session, as a script:
  commit1  analysis code + labelling code + gates + frozen catalogues (before the first push of any unit)
  commit2  analysis addendum + extra-arm build (before the first push of any P_/V_ unit)
Usage: uv run src/commit_steps.py commit1|commit2"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg5 import RAW, ROOT, read_jsonl  # noqa: E402
from commit5 import commit  # noqa: E402


def commit1() -> None:
    assert not [r for r in read_jsonl(RAW) if r["family"] in ("ESC", "PN", "T13")], "push rows exist"
    files = [ROOT / "analysis" / "a1a2.py", ROOT / "analysis" / "variants.py", ROOT / "tests" / "test_analysis.py",
             ROOT / "results" / "tests_analysis.json", ROOT / "src" / "labels_view.py", ROOT / "src" / "quantities.py",
             ROOT / "src" / "gate2.py", ROOT / "src" / "unitlib.py", ROOT / "src" / "sandbox_tests.py",
             ROOT / "src" / "sandbox_trace.py", ROOT / "src" / "judge5.py", ROOT / "results" / "judge_control_gate.json",
             ROOT / "results" / "margins.json"]
    for u in ["B1", "B2", "B3", "B4", "B5", "B6", "B7"]:
        files += [ROOT / "src" / "units" / f"{u.lower()}.py", ROOT / "units" / u / "tests.jsonl",
                  ROOT / "units" / u / "gate.json", ROOT / "units" / u / "catalogue_frozen.json",
                  ROOT / "units" / u / "build_report.json"]
        gr = ROOT / "units" / u / "gate_revision.json"
        if gr.exists():
            files.append(gr)
    commit(files, "commit1_analysis_code_gates")


def commit2() -> None:
    assert not [r for r in read_jsonl(RAW) if r["unit"][:2] in ("P_", "V_") and r["family"] in ("ESC", "PN", "T13")]
    commit([ROOT / "analysis" / "a1_extended.py", ROOT / "src" / "units_extra.py", ROOT / "src" / "quantities_extra.py",
            ROOT / "data" / "prompts_extra.jsonl", ROOT / "units" / "extra_arm_build.json"], "commit2_extra_arm_addendum")


if __name__ == "__main__":
    {"commit1": commit1, "commit2": commit2}[sys.argv[1]]()
