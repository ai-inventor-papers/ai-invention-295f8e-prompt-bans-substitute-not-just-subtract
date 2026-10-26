#!/bin/bash
# CPU post-processing: novelty audit -> analysis (summary, figures, rows.jsonl, method_out.json) -> stdlib re-derivation
# -> README -> schema validation, mini/preview variants, file sizes.
set -e
cd "$(dirname "$0")"
.venv/bin/python src/deviations_final.py
.venv/bin/python src/novelty_k3.py
.venv/bin/python analysis.py
python3 audit/rederive.py
.venv/bin/python analysis.py            # second pass picks up results/rederive.json
.venv/bin/python make_readme.py
SKILL_DIR=/ai-inventor/.claude/skills/aii-json
PY="$SKILL_DIR/../.ability_client_venv/bin/python"
$PY $SKILL_DIR/scripts/aii_json_validate_schema.py --format exp_gen_sol_out --file "$(pwd)/method_out.json"
$PY $SKILL_DIR/scripts/aii_json_format_mini_preview.py --input "$(pwd)/method_out.json"
ls -lh method_out.json full_method_out.json mini_method_out.json preview_method_out.json results/*.json data/*.jsonl | awk '{print $5, $9}'
