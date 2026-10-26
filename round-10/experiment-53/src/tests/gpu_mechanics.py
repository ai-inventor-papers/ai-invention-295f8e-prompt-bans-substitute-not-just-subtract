"""GPU mechanics tests G1-G5 (after the server starts, before the pilot) plus a throughput probe.

Writes results/gpu_mechanics.json. Run: .venv/bin/python tests/gpu_mechanics.py
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common import RESULTS, setup_logging, utc_now, write_json  # noqa: E402
import engine  # noqa: E402
from baselines import NN_PROGRAM  # noqa: E402
from dtb import choose_branch, entropy, ranked  # noqa: E402
from prompt import nn_body, render_prompt, tokenizer  # noqa: E402

logger = setup_logging("gpu_mechanics")


def metrics() -> dict:
    import requests

    txt = requests.get("http://127.0.0.1:8000/metrics", timeout=30).text
    out = {}
    for name in ("vllm:prefix_cache_queries_total", "vllm:prefix_cache_hits_total", "vllm:generation_tokens_total",
                 "vllm:prompt_tokens_total", "vllm:num_preemptions_total"):
        m = re.findall(rf"^{re.escape(name)}\{{[^}}]*\}} ([0-9.e+]+)$", txt, flags=re.M)
        out[name] = float(m[0]) if m else None
    return out


async def main() -> None:
    tok = tokenizer()
    res: dict = {"utc": utc_now()}
    text, ids = render_prompt([nn_body(NN_PROGRAM)])
    # G1: explicit top_k -1 vs server default; sampled-token logprob equals its top-20 entry
    g1 = {"identical_top20_pos1": 0, "sampled_lp_matches": 0, "n": 20}
    for i in range(20):
        a = await engine.complete(ids, temperature=1.0, top_p=1.0, max_tokens=4, seed=1000 + i, logprobs=20)
        from openai import AsyncOpenAI

        cl = AsyncOpenAI(base_url=engine.BASE_URL, api_key="EMPTY", timeout=180)
        rb = await cl.completions.create(model=engine.SERVED, prompt=ids, max_tokens=4, temperature=1.0, top_p=1.0,
                                         seed=1000 + i, logprobs=20, extra_body={"return_tokens_as_token_ids": True})
        tb = {int(k.split(":")[1]): float(v) for k, v in rb.choices[0].logprobs.top_logprobs[0].items()}
        ta = a["top"][0]
        same = set(ta) == set(tb) and all(abs(ta[k] - tb[k]) < 1e-4 for k in ta)
        g1["identical_top20_pos1"] += int(same)
        sid = a["token_ids"][0]
        g1["sampled_lp_matches"] += int(sid in ta and abs(ta[sid] - a["token_logprobs"][0]) < 1e-5)
    res["G1"] = g1
    # G2: token-id round trip
    a = await engine.complete(ids, temperature=1.0, top_p=1.0, max_tokens=48, seed=7, logprobs=20)
    dec_all = tok.decode(ids + a["token_ids"], skip_special_tokens=False, clean_up_tokenization_spaces=False)
    res["G2"] = {"ids_returned": a["token_ids"] is not None,
                 "roundtrip_ok": dec_all.startswith(text) and dec_all[len(text):].startswith(a["text"]),
                 "finish": a["finish_reason"], "n_tokens": len(a["token_ids"])}
    # G3: DTB on 5 prompts
    g3 = []
    m0 = metrics()
    for i in range(5):
        r1 = await engine.complete(ids, temperature=1.0, top_p=1.0, max_tokens=48, seed=500 + i, logprobs=20)
        br = choose_branch(tok, r1["token_ids"], r1["top"], len(r1["text"]), "entropy", 0, "DTB", i)
        row = {"no_branch": br["no_branch"]}
        if not br["no_branch"]:
            j = br["j_star"]
            pre = r1["token_ids"][:j] + [br["forced_id"]]
            mA = metrics()
            r2 = await engine.complete(ids + pre, temperature=1.0, top_p=1.0, max_tokens=64, seed=501 + i)
            mB = metrics()
            q = (mB["vllm:prefix_cache_queries_total"] or 0) - (mA["vllm:prefix_cache_queries_total"] or 0)
            h = (mB["vllm:prefix_cache_hits_total"] or 0) - (mA["vllm:prefix_cache_hits_total"] or 0)
            row.update({"j_star": j, "forced_rank": br["forced_rank"], "rank_ok": 2 <= br["forced_rank"] <= 8,
                        "H_recomputed_ok": abs(entropy(r1["top"][j]) - br["H_j_star"]) < 1e-9,
                        "prefix_hit_rate_r2": h / q if q else None, "forced_text": br["forced_text"],
                        "r2_prompt_ok": (ids + pre)[:len(ids)] == ids and (ids + pre)[-1] == br["forced_id"],
                        "forced_class": br["forced_class"]})
        g3.append(row)
    res["G3"] = g3
    # G4: RPB positions over 100 dry draws on stored request-1 outputs
    stored = []
    for i in range(4):
        stored.append(await engine.complete(ids, temperature=1.0, top_p=1.0, max_tokens=48, seed=900 + i, logprobs=20))
    from scipy.stats import chisquare

    g4 = []
    for s in stored:
        pos = []
        for call in range(100):
            br = choose_branch(tok, s["token_ids"], s["top"], len(s["text"]), "random", 0, "RPB", call)
            if not br["no_branch"]:
                pos.append(br["j_star"])
        elig = choose_branch(tok, s["token_ids"], s["top"], len(s["text"]), "random", 0, "RPB", 0)["eligible"]
        cnt = [pos.count(e) for e in elig]
        p = chisquare(cnt).pvalue if len(elig) > 1 and sum(cnt) > 0 else None
        g4.append({"n_eligible": len(elig), "n_draws": len(pos), "n_distinct_positions": len(set(pos)),
                   "chisq_p_uniform": p})
    res["G4"] = g4
    # G5: determinism probe at batch 1
    x1 = await engine.complete(ids, temperature=1.0, top_p=1.0, max_tokens=128, seed=4242)
    x2 = await engine.complete(ids, temperature=1.0, top_p=1.0, max_tokens=128, seed=4242)
    res["G5"] = {"byte_identical": x1["text"] == x2["text"], "note": "recorded, not required"}
    # throughput probe: 64 concurrent T1.0 calls on the NN-only prompt, 512 max tokens
    m1 = metrics()
    t0 = time.time()
    outs = await asyncio.gather(*[engine.complete(ids, temperature=1.0, top_p=1.0, max_tokens=512, seed=7000 + i)
                                  for i in range(64)])
    wall = time.time() - t0
    m2 = metrics()
    gen = sum(o.get("completion_tokens") or 0 for o in outs)
    res["throughput"] = {"n": 64, "wall_s": wall, "gen_tokens": gen, "gen_tok_per_s": gen / wall,
                         "calls_per_s": 64 / wall, "prompt_tokens_each": len(ids),
                         "finish": dict(zip(*np.unique([o.get("finish_reason") for o in outs], return_counts=True))),
                         "preemptions": (m2["vllm:num_preemptions_total"] or 0) - (m1["vllm:num_preemptions_total"] or 0)}
    res["throughput"]["finish"] = {str(k): int(v) for k, v in res["throughput"]["finish"].items()}
    res["sample_outputs"] = [o["text"][:600] for o in outs[:3]]
    write_json(RESULTS / "gpu_mechanics.json", res)
    logger.info(json.dumps({k: v for k, v in res.items() if k != "sample_outputs"}, default=str)[:3000])


if __name__ == "__main__":
    asyncio.run(main())
