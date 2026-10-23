#!/usr/bin/env python3
"""Final outputs: commit-chain report, figures, method_out.json, schema validation, mini/preview variants, the
stdlib re-derivation audit and a file-size check."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg8 import RESULTS_DIR, ROOT, write_json  # noqa: E402
import commit8 as CM  # noqa: E402

PY = str(ROOT / ".venv" / "bin" / "python")
SKILL = Path(os.environ.get("AII_JSON_SKILL_DIR", ""))   # schema validator of the pipeline (optional)


def main() -> None:
    write_json(RESULTS_DIR / "commit_chain.json", CM.verify())
    for cmd in ([PY, "src/figures8.py"], [PY, "src/outputs8.py"], [PY, "audit/rederive.py"]):
        r = subprocess.run(cmd, cwd=ROOT)
        print(cmd[-1], "exit", r.returncode, flush=True)
    vpy = SKILL.parent / ".ability_client_venv" / "bin" / "python"
    if str(SKILL) and vpy.exists():
        subprocess.run([str(vpy), str(SKILL / "scripts" / "aii_json_validate_schema.py"), "--format",
                        "exp_gen_sol_out", "--file", str(ROOT / "method_out.json")])
        subprocess.run([str(vpy), str(SKILL / "scripts" / "aii_json_format_mini_preview.py"), "--input",
                        str(ROOT / "method_out.json")])
    big = [(p, p.stat().st_size) for p in ROOT.rglob("*") if p.is_file() and p.stat().st_size > 90e6
           and ".venv" not in p.parts]
    print("files > 90 MB:", [(str(p.relative_to(ROOT)), s) for p, s in big])


if __name__ == "__main__":
    main()
