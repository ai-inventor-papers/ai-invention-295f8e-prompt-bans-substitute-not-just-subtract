#!/usr/bin/env bash
# Post-generation pipeline (run from this folder after results/gpu_done.flag exists and the labeller has finished):
# merge -> novelty audit -> full analysis (bootstraps reuse results/boot_cache) -> descriptive -> label-validity audit
# -> figures -> method_out.json -> independent re-derivation -> summary -> README assembly.
set -euo pipefail
cd "$(dirname "$0")"
PY=.venv/bin/python
(cd src && ../$PY -m analysis.run_all --skip-boot)
$PY src/audit_llm.py novelty
(cd src && ../$PY -m analysis.run_all --workers 6)
(cd src && ../$PY -m analysis.descriptive)
$PY method.py validity
$PY src/figures.py
$PY src/outputs.py
$PY audit/rederive.py > logs/rederive.out
$PY src/outputs.py
$PY src/report_numbers.py > /dev/null
$PY - <<'EOF'
from pathlib import Path
r = Path("README.md")
s = r.read_text()
body = Path("src/readme_results.md").read_text() + Path("results/summary.md").read_text()
if "RESULTS_PLACEHOLDER" in s:
    s = s.replace("RESULTS_PLACEHOLDER", body)
else:
    a = s.index("## Results")
    b = s.index("## What was run")
    s = s[:a] + body + "\n" + s[b:]
r.write_text(s)
print("README assembled")
EOF
