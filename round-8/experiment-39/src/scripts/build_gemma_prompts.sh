#!/bin/bash
# Rebuild prompts/gemma_twin_prompts.json (Gemma-3-4b-it T1 twin prompts W1-W5) with exp38's own prompt code,
# run from a scratch copy so that nothing is written into inputs/.
set -e
cd "$(dirname "$0")/.."
mkdir -p build/gemma_prompts prompts
rm -rf build/gemma_prompts/src && cp -r inputs/exp38/src build/gemma_prompts/src
ln -sfn ../../inputs/exp38/inputs build/gemma_prompts/inputs
cd build/gemma_prompts
../../.venv/bin/python - << 'PY'
import sys, json, hashlib
sys.path.insert(0, "src")
import fork7 as FK
from cfg import TEMPLATE_IDS
out = {}
for w in TEMPLATE_IDS:
    p = FK.twin(w)
    out[w] = {"ids": p["ids"], "P": len(p["ids"]), "prompt_sha256": hashlib.sha256(json.dumps(p["ids"]).encode()).hexdigest(),
              "keys": sorted(k for k in p if k != "ids")}
json.dump(out, open("../../prompts/gemma_twin_prompts.json", "w"), indent=1)
print("gemma prompts:", {w: v["P"] for w, v in out.items()})
PY
