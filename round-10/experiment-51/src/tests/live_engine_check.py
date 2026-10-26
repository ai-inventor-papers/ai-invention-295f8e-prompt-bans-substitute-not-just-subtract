#!/usr/bin/env python3
"""Live check: render the k=1 prompt, sample N calls per arm, time it, print bodies (smoke diagnostics)."""
import asyncio, json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import numpy as np
from transformers import AutoTokenizer
import engine, prompts

async def main(n: int, arms: list[str]):
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B-FP8", revision="220b46e3b2180893580a4454f21f22d3ebb187d3")
    text, ids = prompts.render(tok, [prompts.SEED_BODY_BF], idea=False)
    print(repr(text[-700:])); print("prompt tokens", len(ids))
    async with engine.Engine("http://127.0.0.1:8051", tok) as eng:
        t0 = time.time()
        jobs = [engine.sample(eng, arm, ids, seed=99, arm_idx=engine.ARM_IDX[arm], call_id=c) for arm in arms for c in range(n)]
        res = await asyncio.gather(*jobs)
        dt = time.time() - t0
    toks = sum(r["n_gen_tokens"] for r in res)
    print(f"{len(res)} calls in {dt:.1f}s -> {len(res)/dt:.2f} calls/s, {toks/dt:.0f} tok/s, mean tokens {toks/len(res):.0f}")
    for arm in arms:
        rs = [r for r, (a, c) in zip(res, [(a, c) for a in arms for c in range(n)]) if a == arm]
        print("=====", arm, "ok", sum(r["ok"] for r in rs), "trunc", sum(r["truncated"] for r in rs))
        for r in rs[:2]:
            print(prompts.program_from(r["text"], 1)[:600]); print("--- fork:", {k: v for k, v in (r["fork"] or {}).items() if k not in ("H", "E", "cands")})
    Path(ROOT / "logs" / "live_engine_check.json").write_text(json.dumps([{k: v for k, v in r.items() if k != "ids"} for r in res])[:2000000])

if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]), sys.argv[2].split(",")))
