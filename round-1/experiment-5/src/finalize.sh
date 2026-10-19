#!/bin/bash
# Post-GPU steps: label everything (cached), analysis (+ second judge), summary tables, method_out.json, schema check.
set -e
cd "$(dirname "$0")"
.venv/bin/python src/label_score.py > logs/label_final.out 2>&1
.venv/bin/python src/analysis.py --second_judge > logs/analysis_final.out 2>&1
.venv/bin/python src/report.py
.venv/bin/python method.py --assemble > logs/assemble.out 2>&1
SKILL_DIR=${AII_JSON_SKILL_DIR:?set AII_JSON_SKILL_DIR to the aii-json skill directory}
$SKILL_DIR/../.ability_client_venv/bin/python $SKILL_DIR/scripts/aii_json_validate_schema.py --format exp_gen_sol_out --file "$(pwd)/method_out.json"
ls -la method_out.json
$SKILL_DIR/../.ability_client_venv/bin/python $SKILL_DIR/scripts/aii_json_format_mini_preview.py --input "$(pwd)/method_out.json"
ls -la *method_out.json
