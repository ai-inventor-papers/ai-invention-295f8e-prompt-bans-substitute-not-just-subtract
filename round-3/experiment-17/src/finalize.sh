#!/bin/bash
# Final assembly: analyses + figures + method_out.json, token-id export, README fill, mini/preview variants,
# schema validation, final hash commit, audit, cache cleanup.
set -e
cd "$(dirname "$0")"
.venv/bin/python method.py analyze > logs/analyze.out 2>&1
.venv/bin/python src/export_token_ids.py
[ -f results/sae_transfer.json ] && grep -q "ZEROG_PLACEHOLDER" README.md && .venv/bin/python tests/fill_readme_0g.py > logs/fill_readme.out 2>&1
# mini/preview variants: the AI Inventor aii-json skill if AII_JSON_SKILL_DIR points at it, else the local fallback
if [ -n "${AII_JSON_SKILL_DIR:-}" ]; then
  PY=$AII_JSON_SKILL_DIR/../.ability_client_venv/bin/python
  $PY $AII_JSON_SKILL_DIR/scripts/aii_json_format_mini_preview.py --input "$(pwd)/method_out.json" --output-dir "$(pwd)"
  for f in method_out.json full_method_out.json mini_method_out.json preview_method_out.json; do
    $PY $AII_JSON_SKILL_DIR/scripts/aii_json_validate_schema.py --format exp_gen_sol_out --file "$(pwd)/$f" | tail -1
  done
else
  .venv/bin/python tests/make_mini_preview.py
fi
.venv/bin/python -c "
import sys; sys.path.insert(0, 'src')
from pathlib import Path
from commit import commit
fs = sorted(Path('results').glob('*.json')) + [Path('method_out.json'), Path('README.md')]
r = commit([p.resolve() for p in fs], 'final_results')
print(len(r), 'files committed as final_results')
"
.venv/bin/python audit/rederive.py > logs/rederive.out 2>&1 && tail -4 logs/rederive.out
find . -path ./.venv -prune -o -name __pycache__ -type d -print -exec rm -rf {} + 2>/dev/null || true
ls -la method_out.json full_method_out.json mini_method_out.json preview_method_out.json
