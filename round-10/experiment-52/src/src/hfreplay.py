#!/usr/bin/env python3
"""HF bf16 replay (run only after vLLM is killed and the GPU is free). Qwen/Qwen3-8B in bf16 teacher-forces 20 stored
DTB calls (prompt + r1 tokens) and compares its per-position top-20 with the FP8 engine's logged top-20: top-1
agreement, Jaccard of the top-20 sets, |logprob difference| on shared tokens, whether the entropy-argmax eligible
position (DTB's j) is the same, and whether the forced token lies within bf16 candidate ranks 2-8. Reported without
pass/fail (the search engine is FP8)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

import common as C  # noqa: E402
import engine as EN  # noqa: E402
import operators as OP  # noqa: E402
import v5 as V5  # noqa: E402

BF16_ID = "Qwen/Qwen3-8B"
BF16_REV = "b968826d9c46dd6066d109eabc6255188de91218"
N_CALLS = 20


@logger.catch(reraise=True)
def main() -> None:
    C.setup_logging("hfreplay")
    import torch
    from transformers import AutoModelForCausalLM
    assert not EN.server_alive(), "vLLM must be stopped first"
    free, total = torch.cuda.mem_get_info(0)
    logger.info(f"GPU free {free / 2**30:.1f} / {total / 2**30:.1f} GiB")
    tok = EN.load_tokenizer()
    tt = OP.TokText(tok)
    model = AutoModelForCausalLM.from_pretrained(BF16_ID, revision=BF16_REV, torch_dtype=torch.bfloat16,
                                                 device_map="cuda")
    model.eval()
    gen = {}
    for r in C.read_jsonl(C.DATA / "gen_s2.jsonl"):
        gen[(r["seed"], r["arm"], r["call"])] = r
    tops = [r for r in C.read_jsonl(C.DATA / "r1_tops_s2_DTB.jsonl")][:N_CALLS]
    rows = []
    for t in tops:
        g = gen[(2, "DTB", t["call"])]
        _, prompt_ids = V5._prompt_ids(tok, gen, g)
        r1 = t["r1_ids"]
        ids = torch.tensor([prompt_ids + r1], device="cuda")
        with torch.no_grad():
            logits = model(ids).logits[0, len(prompt_ids) - 1: len(prompt_ids) - 1 + len(r1)].float()
        lp = torch.log_softmax(logits, dim=-1)
        top_bf = []
        for k in range(len(r1)):
            v, i = torch.topk(lp[k], 20)
            top_bf.append([(int(a), float(b)) for a, b in zip(i.tolist(), v.tolist())])
        fp8 = [[(int(a), float(b)) for a, b in pos] for pos in t["top"]]
        n = min(len(fp8), len(top_bf))
        top1 = [fp8[k][0][0] == top_bf[k][0][0] for k in range(n)]
        jac, diffs = [], []
        for k in range(n):
            a = {x[0]: x[1] for x in fp8[k]}
            b = {x[0]: x[1] for x in top_bf[k]}
            sh = set(a) & set(b)
            jac.append(len(sh) / max(1, len(set(a) | set(b))))
            diffs += [abs(a[x] - b[x]) for x in sh]
        plan_bf = OP.branch_plan(tt, r1, top_bf, 2, "DTB", t["call"])
        br = g["branch"]
        cand_bf = []
        if br.get("j") is not None and br["j"] < len(top_bf):
            cand_bf = [tid for tid, _ in sorted(top_bf[br["j"]], key=lambda x: -x[1]) if tt.cand_ok(tid)]
        rank_forced = (cand_bf.index(br["forced_id"]) + 1) if br.get("forced_id") in cand_bf else None
        rows.append({"call": t["call"], "n_positions": n, "top1_agreement": float(np.mean(top1)),
                     "jaccard_top20_mean": float(np.mean(jac)), "abs_lp_diff_median": float(np.median(diffs)),
                     "abs_lp_diff_max": float(np.max(diffs)), "j_fp8": br.get("j"), "j_bf16": plan_bf.get("j"),
                     "same_j": plan_bf.get("j") == br.get("j"), "forced_rank_in_bf16_candidates": rank_forced,
                     "forced_within_bf16_ranks_2_8": rank_forced is not None and 2 <= rank_forced <= 8})
        logger.info(f"call {t['call']}: top1 {rows[-1]['top1_agreement']:.3f} jac {rows[-1]['jaccard_top20_mean']:.3f} "
                    f"j {br.get('j')}/{plan_bf.get('j')} forced rank {rank_forced}")
    summ = {"model": f"{BF16_ID}@{BF16_REV}", "n_calls": len(rows),
            "top1_agreement_mean": float(np.mean([r["top1_agreement"] for r in rows])),
            "jaccard_top20_mean": float(np.mean([r["jaccard_top20_mean"] for r in rows])),
            "abs_lp_diff_median": float(np.median([r["abs_lp_diff_median"] for r in rows])),
            "abs_lp_diff_max": float(np.max([r["abs_lp_diff_max"] for r in rows])),
            "same_j_share": float(np.mean([r["same_j"] for r in rows])),
            "forced_within_bf16_ranks_2_8_share": float(np.mean([r["forced_within_bf16_ranks_2_8"] for r in rows]))}
    C.write_json(C.RESULTS / "hf_replay.json", {"summary": summ, "calls": rows})
    logger.info(f"HF replay: {summ}")


if __name__ == "__main__":
    main()
