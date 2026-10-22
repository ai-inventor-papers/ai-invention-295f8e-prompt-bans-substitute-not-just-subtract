#!/bin/bash
# II7/II8 predictor-side bookkeeping: forced-set release, gate (ii), unit commit (only if gated).
cd "$(dirname "$0")/.."
until grep -q "vLLM done" logs/switch_vllm.out 2>/dev/null; do sleep 15; done
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
for u in II7 II8; do
  until [ "$(pending $u)" = "0" ]; do sleep 15; done
  touch data/FORCED_FINAL_$u
  echo "$u labelled $(date -u)"
done
.venv/bin/python src/gate2.py II7,II8 > logs/gate2_ii78.out 2>&1
echo "gate done $(date -u)"; grep "gate (ii)" logs/gate2_ii78.out
for u in II7 II8; do
  until .venv/bin/python -c "import json,sys; d=json.load(open('results/qlik.json')); sys.exit(0 if '$u' in d else 1)" 2>/dev/null; do sleep 15; done
  st=$(.venv/bin/python -c "import json; print(json.load(open('units/$u/gate.json'))['status'])")
  until [ "$(.venv/bin/python -c "
import json
n=0
for l in open('data/samples_raw.jsonl'):
    r=json.loads(l)
    if r['unit']=='$u' and r['arm']=='TWIN' and r.get('engine')=='hf': n+=1
print(n)")" -ge 50 ]; do sleep 15; done
  until [ "$(pending $u)" = "0" ]; do sleep 15; done
  if [ "$st" = "gated" ]; then .venv/bin/python src/quantities6.py $u > logs/commit_$u.out 2>&1; echo "$u committed $(date -u)"; else echo "$u NOT gated: $st"; fi
done
