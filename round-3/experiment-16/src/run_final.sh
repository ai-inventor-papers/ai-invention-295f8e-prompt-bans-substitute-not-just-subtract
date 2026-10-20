#!/usr/bin/env bash
# Final CPU stages after the GPU queues: analysis, replication, supplementary, figures, outputs, audit, JSON checks.
set -euo pipefail
cd "$(dirname "$0")"
PY=.venv/bin/python
$PY method.py analysis
$PY src/replication.py
$PY src/supplementary.py
AII_SKILLS_DIR="${AII_SKILLS_DIR:-}" $PY method.py figures
$PY method.py outputs
$PY method.py audit
if [ -z "${AII_SKILLS_DIR:-}" ]; then echo "AII_SKILLS_DIR not set: skipping JSON mini/preview + schema validation"; exit 0; fi
SKILL_DIR="$AII_SKILLS_DIR/aii-json"
$SKILL_DIR/../.ability_client_venv/bin/python $SKILL_DIR/scripts/aii_json_format_mini_preview.py --input "$(pwd)/method_out.json" || true
$SKILL_DIR/../.ability_client_venv/bin/python $SKILL_DIR/scripts/aii_json_validate_schema.py --format exp_gen_sol_out --file "$(pwd)/method_out.json"
ls -lh method_out.json full_method_out.json mini_method_out.json preview_method_out.json 2>/dev/null || true
