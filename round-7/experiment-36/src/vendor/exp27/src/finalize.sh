#!/usr/bin/env bash
# Post-generation pipeline: wait for the restore + labels, then audits, analyses, figures, outputs, re-derivation.
set -u
cd "$(dirname "$0")/.."
PY=.venv/bin/python
SK="${AII_JSON_SKILL_DIR:-}"   # optional: the aii-json skill folder (schema validation + mini/preview)
while [ ! -f results/restore_done.flag ]; do sleep 10; done
# labels caught up?
for i in $(seq 1 60); do
  a=$(wc -l < data/samples_raw.jsonl); b=$(wc -l < data/labels.jsonl)
  [ "$a" -le "$b" ] && break; sleep 10
done
echo "rows $(wc -l < data/samples_raw.jsonl) labels $(wc -l < data/labels.jsonl)"
$PY src/audit5.py novelty
$PY src/analysis_f.py > /dev/null
$PY src/analysis_ec.py
$PY src/analysis_c.py --workers 12
$PY src/figures5.py
$PY src/outputs5.py
$PY audit/rederive.py
$PY src/outputs5.py
$PY src/report5.py > /dev/null
if [ -n "$SK" ] && [ -x "$SK/../.ability_client_venv/bin/python" ]; then
  $SK/../.ability_client_venv/bin/python $SK/scripts/aii_json_validate_schema.py --format exp_gen_sol_out --file "$(pwd)/method_out.json"
  $SK/../.ability_client_venv/bin/python $SK/scripts/aii_json_format_mini_preview.py --input "$(pwd)/method_out.json"
fi
ls -lh method_out.json full_method_out.json mini_method_out.json preview_method_out.json
echo FINALIZE_DONE
