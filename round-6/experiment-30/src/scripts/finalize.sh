#!/bin/bash
# Post-GPU pipeline: freeze the analysis code, run every analysis, L scoring, novelty audit, bookkeeping, independent
# re-derivation, figures, tables, method_out.json (+ full/mini/preview) and its schema check.
cd "$(dirname "$0")/.." || exit 1
set -e
PY=.venv/bin/python
$PY src/commit_analysis.py amendment4_analysis_code_posthoc "post-hoc additions after amendment 3 (labelled as such): alpha<=4 sensitivity of the ST rule model, an identifiability check for collinear designs; the committed rule evaluation is unchanged"
$PY src/analysis6.py engine,stageA,st,svt,top5
$PY src/lcontest.py score || echo "L scoring failed"
$PY src/novelty6.py || echo "novelty audit failed"
$PY src/bookkeeping6.py
python3 -I audit/rederive.py || echo "rederive reported mismatches"
$PY src/figures6.py
$PY src/report6.py
$PY src/outputs6.py
if [ -n "$AII_JSON_SKILL" ]; then   # the aii-json skill folder (pipeline machines); otherwise the portable script
  $AII_JSON_SKILL/../.ability_client_venv/bin/python $AII_JSON_SKILL/scripts/aii_json_format_mini_preview.py --input "$(pwd)/method_out.json"
  $AII_JSON_SKILL/../.ability_client_venv/bin/python $AII_JSON_SKILL/scripts/aii_json_validate_schema.py --format exp_gen_sol_out --file "$(pwd)/method_out.json"
else
  $PY src/format_outputs6.py method_out.json
fi
ls -la method_out.json full_method_out.json mini_method_out.json preview_method_out.json
