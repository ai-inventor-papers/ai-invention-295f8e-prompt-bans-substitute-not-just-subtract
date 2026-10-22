#!/bin/bash
# GPU hand-over: wait for the new-unit GTN tasks, stop the HF daemon (by PID), run the II7/II8 vLLM jobs, restart HF.
cd "$(dirname "$0")/.."
INS=$HF_HUB_CACHE/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218
BAS=$HF_HUB_CACHE/models--Qwen--Qwen3-8B-Base/snapshots/49e3418fbbbca6ecbdf9608b4d22e5a407081db4
until grep -q '"task": "gtn|II6|2.0' results/gpu_tasks.jsonl 2>/dev/null; do sleep 10; done
GP=$(cat logs/gpu6.pid); kill $GP; while kill -0 $GP 2>/dev/null; do sleep 2; done
echo "HF stopped $(date -u)"
.venv_vllm/bin/python src/vllm_gen.py --model $INS --requests data/vllm_req/new2_instruct.jsonl --out data/vllm_out/new2_instruct.jsonl --max-num-seqs 128 --chunk 1000 > logs/vllm_new2_instruct.log 2>&1
.venv/bin/python src/requests6.py ingest new2_instruct > /dev/null 2>&1
.venv_vllm/bin/python src/vllm_gen.py --model $BAS --requests data/vllm_req/new2_base.jsonl --out data/vllm_out/new2_base.jsonl --max-num-seqs 128 --chunk 1000 > logs/vllm_new2_base.log 2>&1
.venv/bin/python src/requests6.py ingest new2_base --model-tag base > /dev/null 2>&1
.venv/bin/python -c "
import sys; sys.path.insert(0, 'src')
from cfg5 import setup_logging; setup_logging('bint2')
import requests6 as R
pr = R.prompt_table()
reqs = R.build_bint_code('II7', pr) + R.build_bint_code('II8', pr)
R.write_job('new2_bint', reqs)
" > /dev/null 2>&1
.venv_vllm/bin/python src/vllm_gen.py --model $INS --requests data/vllm_req/new2_bint.jsonl --out data/vllm_out/new2_bint.jsonl --max-num-seqs 128 --chunk 1000 > logs/vllm_new2_bint.log 2>&1
.venv/bin/python src/requests6.py ingest new2_bint > /dev/null 2>&1
echo "vLLM done $(date -u)"
nohup .venv/bin/python src/gpu6.py --plan data/gpu_plan_v3.json > logs/gpu6c.out 2>&1 &
echo $! > logs/gpu6.pid
echo "HF restarted $(date -u) pid $(cat logs/gpu6.pid)"
