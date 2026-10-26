#!/usr/bin/env bash
# CPU finalisation after every GPU stage: judges (adjudication, novelty), base-arm analysis, scoring, figures, report,
# method_out.json (+ mini/preview), schema validation and the standard-library re-derivation.
set -u
cd "$(dirname "$0")/src"
PY=../.venv/bin/python
$PY novelty8.py adjudicate     > ../logs/final_adjudicate.out 2>&1; echo "adjudicate $?"
[ -f ../results/base_tf_qwen.json ] && [ -f ../results/base_tf_qwen_base.json ] && { $PY base_arm.py analyze > ../logs/final_base.out 2>&1; echo "base analyze $?"; }
$PY analysis_L.py              > ../logs/final_analysis.out 2>&1; echo "analysis $?"
$PY novelty8.py audit          > ../logs/final_novelty.out 2>&1; echo "novelty $?"
$PY figures8.py                > ../logs/final_figures.out 2>&1; echo "figures $?"
$PY report8.py                 > ../logs/final_report.out 2>&1; echo "report $?"
$PY outputs8.py                > ../logs/final_outputs.out 2>&1; echo "outputs $?"
python3 -I ../audit/rederive.py > ../logs/final_rederive.out 2>&1; echo "rederive $?"
# Optional: schema validation and full/mini/preview files with the AI Inventor aii-json skill (set AII_JSON_SKILL_DIR to
# the skill folder; outside that environment, jsonschema + schemas/exp_gen_sol_out.json give the same check).
SK="${AII_JSON_SKILL_DIR:-}"
if [ -n "$SK" ] && [ -d "$SK" ]; then
  $SK/../.ability_client_venv/bin/python $SK/scripts/aii_json_validate_schema.py --format exp_gen_sol_out --file "$(cd .. && pwd)/method_out.json" 2>&1 | grep -E "PASSED|FAILED|Error" | head -3
  $SK/../.ability_client_venv/bin/python $SK/scripts/aii_json_format_mini_preview.py --input "$(cd .. && pwd)/method_out.json" 2>&1 | tail -3
else
  echo "AII_JSON_SKILL_DIR not set: schema validation and mini/preview generation skipped"
fi
