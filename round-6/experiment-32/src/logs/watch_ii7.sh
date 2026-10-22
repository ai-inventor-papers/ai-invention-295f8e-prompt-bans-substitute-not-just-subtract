#!/bin/bash
cd "$(dirname "$0")/.."
pending() { .venv/bin/python - "$1" << 'PYEOF'
import json, sys
u = sys.argv[1]
lab = {json.loads(l)["key"] for l in open("data/labels.jsonl")}
n = 0
for l in open("data/samples_raw.jsonl"):
    r = json.loads(l)
    if r["unit"] == u:
        n += f"{r['unit']}|{r['template']}|{r['arm']}|{r['slot']}|{r['model_tag']}" not in lab
print(n)
PYEOF
}
until [ "$(pending II7)" = "0" ]; do sleep 15; done
touch data/FORCED_FINAL_II7; echo "II7 relabelled $(date -u)"
.venv/bin/python src/gate2.py II7 --revision > logs/gate2_ii7_rev.out 2>&1
st=$(.venv/bin/python -c "import json; g=json.load(open('units/II7/gate_revision.json')); print(g['status'], g['holdout']['combined_vs_adjudicated'])")
echo "II7 revision gate: $st $(date -u)"
until .venv/bin/python -c "import json,sys; d=json.load(open('results/qlik.json')); sys.exit(0 if 'II7' in d else 1)" 2>/dev/null; do sleep 15; done
case "$st" in gated*) .venv/bin/python src/quantities6.py II7 > logs/commit_II7.out 2>&1; echo "II7 committed $(date -u)";; *) echo "II7 excluded: $st";; esac
