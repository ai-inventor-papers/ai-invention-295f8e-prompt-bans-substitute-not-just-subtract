#!/usr/bin/env bash
# GPU chain after the AV gate: AR gate -> AV production -> AR production (commit #3) -> causal arm.
# The judges (OpenRouter) and the causal label worker run beside the causal arm.
set -euo pipefail
cd "$(dirname "$0")"
PY=.venv/bin/python
until [ -f data/flag_av_gate.done ]; do sleep 5; done
$PY src/nla_ar.py gate > logs/ar_gate.out 2>&1
$PY src/nla_av.py production > logs/av_production.out 2>&1
$PY src/nla_ar.py production > logs/ar_production.out 2>&1
nohup $PY src/judges.py run > logs/judges_run.out 2>&1 &
nohup $PY src/labels.py --raw data/samples_causal_raw.jsonl --out data/labels_causal.jsonl \
      --follow-until data/flag_causal.done --name label_causal > logs/label_causal.out 2>&1 &
$PY src/causal_gen.py --deadline-min 70 > logs/causal_gen.out 2>&1
echo "CHAIN_DONE $(date -u +%FT%TZ)" >> logs/chain.out
