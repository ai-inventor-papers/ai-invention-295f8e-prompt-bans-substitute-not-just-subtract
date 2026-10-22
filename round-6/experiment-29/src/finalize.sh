#!/bin/bash
# Final CPU pass after every GPU stage has ended: stop the labeller once its backlog is empty, then analysis,
# nearest-known-solution pass, stdlib re-derivation, figures, bookkeeping, method_out.json (+ mini/preview) and the
# README tables. Re-runnable.
set -e
cd "$(dirname "$0")"
PY=.venv/bin/python
touch data/STOP_LABELLER
if [ -f logs/labeller.pid ]; then
  P=$(cat logs/labeller.pid)
  while kill -0 "$P" 2>/dev/null; do sleep 5; done
fi
$PY src/analysis.py
$PY src/known6.py
python3 -I src/rederive.py
$PY src/figures6.py
$PY src/finalize6.py
$PY src/outputs6.py
SKILL_DIR="${AII_JSON_SKILL_DIR:-$(pwd)/../aii-json}"   # aii-json skill (optional; set AII_JSON_SKILL_DIR)
[ -d "$SKILL_DIR" ] && $SKILL_DIR/../.ability_client_venv/bin/python $SKILL_DIR/scripts/aii_json_validate_schema.py --format exp_gen_sol_out --file "$(pwd)/method_out.json"
[ -d "$SKILL_DIR" ] && $SKILL_DIR/../.ability_client_venv/bin/python $SKILL_DIR/scripts/aii_json_format_mini_preview.py --input "$(pwd)/method_out.json"
$PY src/report6.py > results/report_tables.md
python3 - <<'PYEOF'
import re
from pathlib import Path
r = Path("README.md"); s = r.read_text(); tab = Path("results/report_tables.md").read_text().strip()
s = re.sub(r"<!-- TABLES -->.*?<!-- /TABLES -->", lambda m: "<!-- TABLES -->\n" + tab + "\n<!-- /TABLES -->", s, flags=re.S)
r.write_text(s)
print("README tables updated")
PYEOF
ls -lh method_out.json full_method_out.json mini_method_out.json preview_method_out.json
