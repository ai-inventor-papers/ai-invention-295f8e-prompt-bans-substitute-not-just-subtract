#!/usr/bin/env bash
# Post-GPU analysis sequence (CPU only): cells/ESS/coverage -> gate -> C1 (+ sensitivity, secondary) -> freeze ->
# outputs (method_out.json, figures) -> report -> independent re-derivation -> mini/preview -> schema validation.
set -euo pipefail
cd "$(dirname "$0")/../src"
PY=../.venv/bin/python
$PY analysis_misc.py
$PY gate.py
$PY c1.py "$@"
$PY freeze.py
$PY outputs.py
$PY report.py > /dev/null
$PY ../audit/rederive.py > /dev/null
$PY outputs.py
cd ..
# Optional: the AI Inventor aii-json skill (mini/preview variants + schema check); set AII_JSON_SKILL_DIR to use it.
if [ -n "${AII_JSON_SKILL_DIR:-}" ] && [ -d "$AII_JSON_SKILL_DIR" ]; then
  "$AII_JSON_SKILL_DIR/../.ability_client_venv/bin/python" "$AII_JSON_SKILL_DIR/scripts/aii_json_format_mini_preview.py" --input "$PWD/method_out.json"
  "$AII_JSON_SKILL_DIR/../.ability_client_venv/bin/python" "$AII_JSON_SKILL_DIR/scripts/aii_json_validate_schema.py" --format exp_gen_sol_out --file "$PWD/method_out.json"
fi
