"""U6 memory/speed probe: FP8 load, one prefill, a 20-row CRN batch with forced long decoding; compares FP8 vs a
bf16 reference on the first block's logits is impossible on 16 GB, so it reports R-logit stats only."""
import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np, torch
from cfg import setup_logging, E8, ROOT
from loguru import logger
setup_logging("u6_speed_probe")
from engine import load_model, prefill, sample, u_stream
tok, model = load_model()
fp = json.loads((E8 / "prompts" / "frozen_prompts.json").read_text())
ids = fp["tasks"]["t2"]["templates"]["W1"]["ban"]["ids"]
t = time.time(); pre = prefill(model, ids); torch.cuda.synchronize(); logger.info(f"prefill P={len(ids)} {time.time()-t:.2f}s")
lp = torch.log_softmax(pre["r_logits"], -1); top = lp.topk(5)
logger.info(f"R top5: {[(tok.decode([i]), round(v,3)) for v,i in zip(top.values.tolist(), top.indices.tolist())]}")
groups = [{"pre": pre, "us": [u_stream("probe", k) for k in range(20)]}]
t = time.time(); res = sample(model, groups, max_new=200); torch.cuda.synchronize(); dt = time.time()-t
logger.info(f"sample 20 rows: steps={res[0]['steps']} {dt:.1f}s -> {dt/max(1,res[0]['steps'])*1e3:.1f} ms/step; "
            f"max mem {torch.cuda.max_memory_allocated()/1e9:.2f} GB")
logger.info("TEXT0: " + tok.decode(res[0]["token_ids"])[:600])
# full-length memory probe: 20 rows x 1024 forced steps (uniform 0.5 never hits EOS reliably; use max_new and ignore stops)
from engine import build_cache
t = time.time()
import engine
orig = engine.IM_END
engine.IM_END = -1; engine.ENDOFTEXT = -2
res = sample(model, groups, max_new=1024)
engine.IM_END = orig
torch.cuda.synchronize(); dt = time.time()-t
logger.info(f"forced 1024 steps x 20 rows: {dt:.1f}s ({dt/1024*1e3:.1f} ms/step); max mem {torch.cuda.max_memory_allocated()/1e9:.2f} GB")
