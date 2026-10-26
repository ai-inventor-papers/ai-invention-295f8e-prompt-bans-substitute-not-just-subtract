#!/usr/bin/env python3
"""T3 veto tests.  synthetic(): the VetoAdapter function masks straddling n-grams (CPU).  gpu_checks(llm): logit_bias
-100 never yields a masked high-probability token in 200 one-token draws; a persistent masked generation never
contains the n-gram.  posthoc(rows, grams): one-shot outputs never contain the FIRST completion at the truncate point
(later completions allowed and counted), persistent outputs contain zero occurrences, decoded text == decode(ids)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import torch  # noqa: E402

from src.ws import RESULTS, read_json, write_json  # noqa: E402


def synthetic() -> dict:
    from src.engine_vllm import _make_veto_fn

    out = {}
    fn = _make_veto_fn([[5, 6, 7]])
    lg = torch.zeros(10)
    fn([1, 2, 5, 6], [], lg)
    out["straddle_prompt_tail_2"] = bool(torch.isinf(lg[7]))
    lg = torch.zeros(10)
    fn([1, 2, 5], [6], lg)
    out["straddle_prompt_tail_1"] = bool(torch.isinf(lg[7]))
    lg = torch.zeros(10)
    fn([1, 2], [5, 6], lg)
    out["inside_output"] = bool(torch.isinf(lg[7]))
    lg = torch.zeros(10)
    fn([1, 2], [5, 9], lg)
    out["no_false_mask"] = not bool(torch.isinf(lg).any())
    fn1 = _make_veto_fn([[4]])
    lg = torch.zeros(10)
    fn1([1], [], lg)
    out["unigram_always"] = bool(torch.isinf(lg[4]))
    out["passed"] = all(out.values())
    return out


def _count(seq: list[int], g: list[int]) -> int:
    n = len(g)
    return sum(1 for i in range(len(seq) - n + 1) if seq[i:i + n] == g)


def gpu_checks(llm, prompt_ids: list[int], gram: list[int]) -> dict:
    from src.engine_vllm import generate

    out = {}
    free = generate(llm, [{"prompt_ids": prompt_ids, "max_tokens": 1, "seed": 9000 + i} for i in range(200)])
    first = [o["out_ids"][0] for o in free if o["out_ids"]]
    import collections
    top, cnt = collections.Counter(first).most_common(1)[0]
    out["free_top_token"] = int(top)
    out["free_top_share"] = cnt / len(first)
    biased = generate(llm, [{"prompt_ids": prompt_ids, "max_tokens": 1, "seed": 9000 + i, "logit_bias": {int(top): -100.0}}
                            for i in range(200)])
    out["masked_token_draws_with_bias"] = sum(1 for o in biased if o["out_ids"] and o["out_ids"][0] == top)
    pers = generate(llm, [{"prompt_ids": prompt_ids, "max_tokens": 256, "seed": 9100 + i, "veto": [gram]} for i in range(50)])
    out["persistent_occurrences_in_50"] = sum(_count(prompt_ids[-(len(gram) - 1):] + o["out_ids"], gram)
                                              if len(gram) > 1 else _count(o["out_ids"], gram) for o in pers)
    freeg = generate(llm, [{"prompt_ids": prompt_ids, "max_tokens": 256, "seed": 9100 + i} for i in range(50)])
    out["free_occurrences_in_50"] = sum(_count(o["out_ids"], gram) for o in freeg)
    out["gram"] = gram
    out["passed"] = (out["free_top_share"] > 0.5 and out["masked_token_draws_with_bias"] == 0
                     and out["persistent_occurrences_in_50"] == 0)
    return out


def posthoc(rows: list[dict], tok) -> dict:
    out = {"oneshot_first_completion_present": 0, "oneshot_later_completions": 0, "oneshot_hit_rows": 0,
           "persistent_occurrences": 0, "persistent_rows": 0, "decode_mismatch": 0, "n_rows": len(rows)}
    for r in rows:
        ids = r["out_ids"]
        if tok.decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False) != r["text"]:
            out["decode_mismatch"] += 1
        grams = r.get("grams") or []
        if r["arm"] == "oneshot" and r.get("hit"):
            out["oneshot_hit_rows"] += 1
            t = r["t"]
            for g in grams:
                n = len(g)
                if t is not None and t - n + 1 >= 0 and len(ids) > t and ids[t - n + 1:t + 1] == g:
                    out["oneshot_first_completion_present"] += 1
                out["oneshot_later_completions"] += _count(ids[t + 1:], g) if t is not None else 0
        if r["arm"] == "persistent" and r.get("hit"):
            out["persistent_rows"] += 1
            for g in grams:
                out["persistent_occurrences"] += _count(ids, g)
    out["passed"] = (out["oneshot_first_completion_present"] == 0 and out["persistent_occurrences"] == 0
                     and out["decode_mismatch"] == 0)
    return out


if __name__ == "__main__":
    r = synthetic()
    print(r)
    write_json(RESULTS / "tests_veto_synthetic.json", r)
    assert r["passed"]
