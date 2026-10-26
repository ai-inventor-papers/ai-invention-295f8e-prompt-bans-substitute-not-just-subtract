#!/usr/bin/env bash
# Final packaging after run_chain.sh: state-level audit, JSON variants, size check, README and struct output.
cd "$(dirname "$0")/.."
PY=.venv/bin/python
$PY audit/audit_states.py > logs/audit_states.out 2>&1 || echo "audit_states reported mismatches (see results/audit_states.json)"
SKILL_DIR=../../../../tools/aii-json
$SKILL_DIR/../.ability_client_venv/bin/python $SKILL_DIR/scripts/aii_json_validate_schema.py --format exp_gen_sol_out --file "$PWD/method_out.json" | tail -2
$SKILL_DIR/../.ability_client_venv/bin/python $SKILL_DIR/scripts/aii_json_format_mini_preview.py --input "$PWD/method_out.json" | tail -4
ls -lh method_out.json full_method_out.json mini_method_out.json preview_method_out.json
$PY scripts/make_readme.py
$PY scripts/make_struct.py
