#!/bin/bash
# After steering stage S: Phase C (vLLM, instruct ban) -> stage R (random dirs at c*) -> stage X (fallback-6 single-layer
# arms + R-only ablation) -> optional A1 extension. Each step is its own process (VRAM freed in between).
cd "$(dirname "$0")"
while ! grep -q '"steer_S_end"' time_log.json 2>/dev/null && ! grep -q "Traceback" logs/steer_S2.out 2>/dev/null; do sleep 15; done
.venv/bin/python src/gen_vllm.py --phase C > logs/gen_C.out 2>&1; echo "C_EXIT=$?" >> logs/chain_status.txt
.venv/bin/python src/steer_hf.py --stage R --cstar t1=${CSTAR_T1:-0.5},t2=${CSTAR_T2:-0.5} > logs/steer_R.out 2>&1; echo "R_EXIT=$?" >> logs/chain_status.txt
.venv/bin/python src/steer_hf.py --stage X --extra "sharpenR:1.0:None:10;randomR:1.0:1:10;single18:0.25:None:5;single18:0.5:None:5;single18:1.0:None:5" > logs/steer_X.out 2>&1; echo "X_EXIT=$?" >> logs/chain_status.txt
