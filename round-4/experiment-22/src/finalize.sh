#!/usr/bin/env bash
# Post-sampling chain: GPU phase 3 (opening ladder, C2c vectors) -> analyses -> figures -> method_out -> audit.
set -euo pipefail
cd "$(dirname "$0")"
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
PY=.venv/bin/python
[ -f results/gpu_phase3_done.json ] || $PY src/gpu_phase3.py
$PY analysis/engine_check.py
$PY src/deviations.py
$PY analysis/run_all.py
$PY analysis/figures.py
$PY src/costs.py
$PY audit/rederive.py
$PY audit/rederive_extra.py
$PY analysis/outputs.py
$PY analysis/summarise.py > /dev/null
# Schema validation and full/mini/preview variants use the pipeline's aii-json skill (set AII_JSON_SKILL to its folder).
if [ -n "${AII_JSON_SKILL:-}" ]; then
  SKILL="$AII_JSON_SKILL"
  $SKILL/../.ability_client_venv/bin/python $SKILL/scripts/aii_json_validate_schema.py --format exp_gen_sol_out --file "$PWD/method_out.json"
  $SKILL/../.ability_client_venv/bin/python $SKILL/scripts/aii_json_format_mini_preview.py --input "$PWD/method_out.json"
  for f in full mini preview; do
    $SKILL/../.ability_client_venv/bin/python $SKILL/scripts/aii_json_validate_schema.py --format exp_gen_sol_out --file "$PWD/${f}_method_out.json"
  done
else
  echo "AII_JSON_SKILL not set: skipping exp_gen_sol_out schema validation and the full/mini/preview variants"
fi
ls -lh ./*method_out.json
