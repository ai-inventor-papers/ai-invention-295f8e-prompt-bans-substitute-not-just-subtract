#!/usr/bin/env python3
"""Coupled token-veto engine (S1.3) on top of a vLLM LLM.

Each veto arm starts from the base trajectory with the same seed (the neutral-twin sample, or the previous round's
sample).  Positions before the first completing draw were sampled from the unmasked conditional, which equals the
masked one wherever no completion was drawn; at the first position t where gen[:t] ends in g[:-1] and gen[t] == g[-1]
for some g in MASK, the draw is rejected and redrawn from the masked conditional (logit_bias -100 on every completing
token), then the rest is sampled afresh.  Rejection + masked redraw yields exactly the masked conditional at every
position, so each arm has the distribution of its mask process (ONE-SHOT: only the first completion is vetoed;
PERSISTENT: every completion, re-scanning each continuation), and arms are paired by seed (common redraw /
continuation seeds h(seed, round, n_vetoes, tag)).
"""

from __future__ import annotations

import time
from typing import Any

from loguru import logger

from common import EOS_IDS, MAX_NEW, stable_seed

VETO_CAP = 32


def banned_after(prefix: list[int], mask: list[tuple[int, ...]]) -> set[int]:
    out = set()
    L = len(prefix)
    for g in mask:
        n = len(g)
        if n == 1 or (L >= n - 1 and tuple(prefix[L - n + 1:]) == g[:-1]):
            out.add(g[-1])
    return out


def find_completion(gen: list[int], start: int, mask: list[tuple[int, ...]]) -> int | None:
    """First position t >= start where gen[t] completes some g in mask (gen[:t] ends in g[:-1])."""
    last = {}
    for g in mask:
        last.setdefault(g[-1], []).append(g)
    for t in range(start, len(gen)):
        tok = gen[t]
        if tok in EOS_IDS:
            return None
        for g in last.get(tok, ()):
            n = len(g)
            if t >= n - 1 and tuple(gen[t - n + 1:t]) == g[:-1]:
                return t
    return None


def count_occurrences(gen: list[int], g: tuple[int, ...]) -> int:
    n = len(g)
    return sum(1 for i in range(len(gen) - n + 1) if tuple(gen[i:i + n]) == g)


def strip_eos(ids: list[int]) -> list[int]:
    out = list(ids)
    while out and out[-1] in EOS_IDS:
        out.pop()
    return out


def veto_seed(seed: int, rnd: int, n_vetoes: int, tag: str) -> int:
    return stable_seed("veto", seed, rnd, n_vetoes, tag)


def run_veto(llm, sp_fn, tok, bases: list[dict], prompt_ids: dict[str, list[int]], masks: dict[str, list[list[int]]],
             mode: str, arm: str, rnd: int = 0, cap: int = VETO_CAP) -> list[dict]:
    """bases: raw rows (sample_id, task, template, idx, seed, token_ids, finish_reason, prompt_key).
    masks: task -> list of n-grams (ids).  mode: 'oneshot' | 'persistent'.  Returns new raw rows (same order)."""
    from vllm.inputs import TokensPrompt

    t0 = time.time()
    st = []
    for b in bases:
        mask = [tuple(g) for g in masks[b["task"]]]
        st.append({"base": b, "mask": mask, "gen": list(b["token_ids"]), "pos": 0, "n": 0, "vetoes": [],
                   "finish": b.get("finish_reason"), "done": False, "cap_hit": False,
                   "P": prompt_ids[b["prompt_key"]]})
    n_redraw_calls = 0
    while True:
        need = []
        for s in st:
            if s["done"]:
                continue
            if mode == "oneshot" and s["n"] >= 1:
                s["done"] = True
                continue
            t = find_completion(s["gen"], s["pos"], s["mask"])
            if t is None:
                s["done"] = True
                continue
            if s["n"] >= cap:
                s["cap_hit"] = True
                s["done"] = True
                continue
            prefix = s["gen"][:t]
            need.append((s, t, prefix, banned_after(prefix, s["mask"])))
        if not need:
            break
        n_redraw_calls += 1
        prompts = [TokensPrompt(prompt_token_ids=s["P"] + prefix) for s, t, prefix, banned in need]
        sps = [sp_fn(veto_seed(s["base"]["seed"], rnd, s["n"], "r"), 1, {int(b): -100.0 for b in banned})
               for s, t, prefix, banned in need]
        outs = llm.generate(prompts, sampling_params=sps, use_tqdm=False)
        cont = []
        for (s, t, prefix, banned), o in zip(need, outs):
            ids = list(o.outputs[0].token_ids)
            new = ids[0] if ids else EOS_IDS[0]
            assert new not in banned, f"redraw returned a masked token {new} (banned {banned})"
            s["vetoes"].append({"pos": t, "banned": sorted(int(b) for b in banned), "vetoed_token": int(s["gen"][t]),
                                "redraw": int(new)})
            if new in EOS_IDS or len(prefix) + 1 >= MAX_NEW:
                s["gen"] = prefix + [new]
                s["finish"] = "stop" if new in EOS_IDS else "length"
                s["n"] += 1
                s["pos"] = t + 1
                continue
            cont.append((s, t, prefix, new))
        if cont:
            prompts = [TokensPrompt(prompt_token_ids=s["P"] + prefix + [new]) for s, t, prefix, new in cont]
            sps = [sp_fn(veto_seed(s["base"]["seed"], rnd, s["n"], "c"), MAX_NEW - len(prefix) - 1, None)
                   for s, t, prefix, new in cont]
            outs = llm.generate(prompts, sampling_params=sps, use_tqdm=False)
            for (s, t, prefix, new), o in zip(cont, outs):
                c = o.outputs[0]
                s["gen"] = prefix + [new] + list(c.token_ids)
                s["finish"] = c.finish_reason
                s["n"] += 1
                s["pos"] = t + 1
    rows = []
    for s in st:
        b = s["base"]
        gen = s["gen"]
        body = strip_eos(gen)
        text = tok.decode(body, skip_special_tokens=True)
        leaks = []
        for g in s["mask"]:
            gt = tok.decode(list(g))
            n_text = text.count(gt) if gt else 0
            n_ids = count_occurrences(body, g)
            if n_text > n_ids:
                leaks.append({"ngram": list(g), "text": gt, "n_text": n_text, "n_ids": n_ids})
        rows.append({"sample_id": f"{b['task']}:{arm}:{b['template']}:{b['idx']}", "task": b["task"], "arm": arm,
                     "template": b["template"], "idx": b["idx"], "seed": b["seed"], "base_sample_id": b["sample_id"],
                     "prompt_key": b["prompt_key"], "round": rnd, "veto_mode": mode,
                     "mask": [list(g) for g in s["mask"]], "n_vetoes": s["n"], "vetoes": s["vetoes"],
                     "veto_cap": s["cap_hit"], "text_leak": bool(leaks), "leaks": leaks,
                     "remaining_completions": sum(count_occurrences(body, g) for g in s["mask"]),
                     "token_ids": gen, "text": text, "finish_reason": s["finish"], "n_tokens": len(body),
                     "engine": "vllm", "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    dt = time.time() - t0
    nv = sum(r["n_vetoes"] for r in rows)
    logger.info(f"veto arm {arm} ({mode}, round {rnd}): {len(rows)} samples, {nv} vetoes, {n_redraw_calls} redraw "
                f"rounds, {sum(r['text_leak'] for r in rows)} text leaks, {dt:.0f}s")
    return rows


def unit_tests(llm, sp_fn, tok, bases: list[dict], prompt_ids: dict, mask_ids: list[list[int]]) -> dict[str, Any]:
    """T4 on twin samples: (a) one-shot first completion never appears, (b) persistent leaves zero completions,
    (c) every redraw avoids its mask (asserted inside run_veto), (d) a never-firing mask reproduces the base
    byte for byte, (e) text-level leak count, (f) fire rate vs n-gram coverage."""
    task = bases[0]["task"]
    masks = {task: mask_ids}
    one = run_veto(llm, sp_fn, tok, bases, prompt_ids, masks, "oneshot", "ut_oneshot")
    per = run_veto(llm, sp_fn, tok, bases, prompt_ids, masks, "persistent", "ut_persistent")
    never = run_veto(llm, sp_fn, tok, bases, prompt_ids, {task: [[EOS_IDS[1], EOS_IDS[1], EOS_IDS[1]]]},
                     "persistent", "ut_never")
    res: dict[str, Any] = {"n": len(bases), "mask": mask_ids}
    ok_a = True
    for b, r in zip(bases, one):
        t = find_completion(list(b["token_ids"]), 0, [tuple(g) for g in mask_ids])
        if t is None:
            ok_a &= r["token_ids"] == list(b["token_ids"])
            continue
        ok_a &= r["token_ids"][:t] == list(b["token_ids"])[:t]
        ok_a &= r["token_ids"][t] not in banned_after(r["token_ids"][:t], [tuple(g) for g in mask_ids])
    res["a_oneshot_first_completion_removed"] = bool(ok_a)
    res["b_persistent_zero_completions"] = all(r["remaining_completions"] == 0 or r["veto_cap"] for r in per)
    res["c_redraws_avoid_mask"] = True  # asserted per redraw inside run_veto
    res["d_never_firing_mask_identity"] = all(r["token_ids"] == list(b["token_ids"]) for b, r in zip(bases, never))
    res["e_text_leaks_oneshot"] = sum(r["text_leak"] for r in one)
    res["e_text_leaks_persistent"] = sum(r["text_leak"] for r in per)
    res["f_fire_rate"] = sum(1 for r in one if r["n_vetoes"] > 0) / len(one)
    res["vetoes_persistent_mean"] = sum(r["n_vetoes"] for r in per) / len(per)
    res["all_pass"] = bool(res["a_oneshot_first_completion_removed"] and res["b_persistent_zero_completions"]
                           and res["d_never_firing_mask_identity"])
    return res
