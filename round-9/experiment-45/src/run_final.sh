#!/usr/bin/env bash
# Final stage chain (after every cell is labelled). Each step logs to logs/final_<step>.log; stops on the first error.
set -euo pipefail
cd "$(dirname "$0")"
export TP_COST_CAP=4.0
PY=.venv/bin/python
for st in commit3 analyse bounds reads_summary heap_keys export novelty figures; do
  echo "== $st"; $PY method.py $st > logs/final_$st.log 2>&1
done
echo "== rederive"; python3 audit/rederive.py > logs/final_rederive.log 2>&1
echo "== clrs"; python3 audit/clrs_check.py > logs/final_clrs.log 2>&1
echo "== outputs"; $PY method.py outputs > logs/final_outputs.log 2>&1
# full/mini/preview + schema validation use the aii-json skill: set AII_JSON_SKILL to its folder
if [ -n "${AII_JSON_SKILL:-}" ]; then
  SK="$AII_JSON_SKILL"
  $SK/../.ability_client_venv/bin/python $SK/scripts/aii_json_format_mini_preview.py --input "$(pwd)/method_out.json" > logs/final_minipreview.log 2>&1
  for f in method_out full_method_out mini_method_out preview_method_out; do
    $SK/../.ability_client_venv/bin/python $SK/scripts/aii_json_validate_schema.py --format exp_gen_sol_out --file "$(pwd)/$f.json" >> logs/final_validate.log 2>&1
  done
fi
echo "== readme"; $PY build_readme.py > logs/final_readme.log 2>&1
echo "== ALL DONE"
