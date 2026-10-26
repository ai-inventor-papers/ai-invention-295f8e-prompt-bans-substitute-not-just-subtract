#!/usr/bin/env python3
"""GPU processes A (ban-free arms) and C (modal bans) with vLLM, bf16 Qwen3-8B, thinking off.

A: neutral twin (5 templates x 10 per task) -> labels -> token-level n-gram coverage check (re-derivation rule) ->
   veto unit tests -> ONE-SHOT, SHAM and PERSISTENT vetoes coupled on the twin samples -> NONCE (5 x 10) and NOVELTY
   (50) fresh samples -> ITERATED rounds 1..3 (trigger: default share >= 0.20 among attempted in round r-1).
C: guard (hash chain + SEAL_BEFORE_BANS + file hashes) -> 5 templates x 20 ban samples per task -> labels.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from pathlib import Path
from typing import Any

from loguru import logger

from common import (COMMIT_LOG, DATA, DECODING, DEFAULTS, EOS_IDS, FROZEN_CONSTANTS, MAX_NEW, MODEL_ID, N_BAN_PER_T,
                    N_NONCE_PER_T, N_NOVELTY, N_TWIN_PER_T, PRED, PROMPTS, RESULTS, ROOT, TASK_ORDER, WS,
                    append_deviation, bench_import, detect_cpus, model_path, read_json, read_jsonl, stable_seed,
                    timing_log, utc_now, write_json, write_jsonl)

os.environ.setdefault("TORCH_COMPILE_DISABLE", "1")  # no C compiler on this machine: Inductor/Triton cannot build
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


def make_llm():
    from vllm import LLM

    t0 = time.time()
    llm = LLM(model=model_path(), tokenizer=model_path(), dtype="bfloat16", gpu_memory_utilization=0.90,
              max_model_len=2048, max_num_seqs=64, max_num_batched_tokens=4096, enable_prefix_caching=True,
              generation_config="vllm", seed=0, enforce_eager=True)
    logger.info(f"vLLM up in {time.time() - t0:.0f}s ({MODEL_ID} bf16, eager)")
    return llm


_TOPK = {"v": -1}


def sp_fn(seed: int, max_tokens: int, logit_bias: dict | None):
    from vllm import SamplingParams

    kw = dict(temperature=1.0, top_p=1.0, min_p=0.0, repetition_penalty=1.0, presence_penalty=0.0,
              frequency_penalty=0.0, max_tokens=int(max_tokens), seed=int(seed), stop_token_ids=list(EOS_IDS))
    if logit_bias:
        kw["logit_bias"] = logit_bias
    try:
        return SamplingParams(top_k=_TOPK["v"], **kw)
    except (ValueError, TypeError):
        _TOPK["v"] = 0
        return SamplingParams(top_k=0, **kw)


def strip_eos(ids: list[int]) -> list[int]:
    out = list(ids)
    while out and out[-1] in EOS_IDS:
        out.pop()
    return out


class Store:
    """data/<sub>/raw/<arm>.jsonl and data/<sub>/labels/<arm>.jsonl (sub = '' for the real run, 'smoke' for tests)."""

    def __init__(self, sub: str = ""):
        self.base = DATA / sub if sub else DATA
        self.raw = self.base / "raw"
        self.lab = self.base / "labels"
        self.raw.mkdir(parents=True, exist_ok=True)
        self.lab.mkdir(parents=True, exist_ok=True)

    def raw_rows(self, arm: str) -> list[dict]:
        return read_jsonl(self.raw / f"{arm}.jsonl")

    def lab_rows(self, arm: str) -> list[dict]:
        return read_jsonl(self.lab / f"{arm}.jsonl")

    def save_raw(self, arm: str, rows: list[dict]) -> None:
        write_jsonl(self.raw / f"{arm}.jsonl", rows)

    def save_lab(self, arm: str, rows: list[dict]) -> None:
        write_jsonl(self.lab / f"{arm}.jsonl", rows)


def make_reqs(tasks: list[str], arm: str, templates: list[str], n_per: int, prompt_arm: str | None = None) -> list[dict]:
    pa = prompt_arm or arm
    out = []
    for t in tasks:
        for w in templates:
            for i in range(n_per):
                out.append({"sample_id": f"{t}:{arm}:{w}:{i}", "task": t, "arm": arm, "template": w, "idx": i,
                            "seed": stable_seed(t, arm, w, i), "prompt_key": f"{t}|{pa}|{w}"})
    return out


def sample(llm, tok, reqs: list[dict], prompt_ids: dict, stage: str) -> list[dict]:
    from vllm.inputs import TokensPrompt

    t0 = time.time()
    prompts = [TokensPrompt(prompt_token_ids=prompt_ids[r["prompt_key"]]) for r in reqs]
    sps = [sp_fn(r["seed"], MAX_NEW, None) for r in reqs]
    outs = llm.generate(prompts, sampling_params=sps, use_tqdm=False)
    rows = []
    ntok = 0
    for r, o in zip(reqs, outs):
        c = o.outputs[0]
        ids = list(c.token_ids)
        body = strip_eos(ids)
        ntok += len(ids)
        rows.append({**r, "token_ids": ids, "text": tok.decode(body, skip_special_tokens=True),
                     "finish_reason": c.finish_reason, "n_tokens": len(body), "engine": "vllm", "model": MODEL_ID,
                     "decoding": DECODING, "utc": utc_now()})
    dt = time.time() - t0
    arm = reqs[0]["arm"] if reqs else "?"
    timing_log(stage, arm, len(reqs), dt, {"tokens": ntok})
    logger.info(f"sampled {len(reqs)} x {arm} in {dt:.0f}s ({ntok / max(dt, 1e-9):.0f} tok/s)")
    return rows


def label(lab, store: Store, arm: str, rows: list[dict]) -> list[dict]:
    res = lab.label_rows(rows, arm)
    store.save_lab(arm, res)
    return res


def default_share(labs: list[dict], task: str) -> tuple[float, int]:
    att = [r for r in labs if r["task"] == task and r["label"] != "invalid"]
    if not att:
        return 0.0, 0
    return sum(r["label"] == DEFAULTS[task] for r in att) / len(att), len(att)


# ------------------------------------------------------------------------------------------------ process A
def stage_a(sub: str = "", tasks: list[str] | None = None, n_twin: int = N_TWIN_PER_T, n_nonce: int = N_NONCE_PER_T,
            n_nov: int = N_NOVELTY, workers: int = 10) -> None:
    import ngrams as NG
    import veto as V
    from labelpool import Labeller

    tasks = tasks or TASK_ORDER
    store = Store(sub)
    prompt_ids = {k: v["ids"] for k, v in read_json(PROMPTS / "prompt_ids.json").items()}
    llm = make_llm()
    tok = llm.get_tokenizer()
    lab = Labeller(workers=workers)
    eff = str(sp_fn(0, MAX_NEW, None))
    (RESULTS / f"effective_sampling_params{('_' + sub) if sub else ''}.txt").write_text(eff)
    logger.info(f"effective SamplingParams: {eff}")
    # T0: chat rendering ends with the empty think block
    chat = tok.decode(prompt_ids[f"{tasks[0]}|twin|W1"])
    assert chat.endswith("<|im_start|>assistant\n<think>\n\n</think>\n\n"), chat[-80:]
    ngr_fp8 = read_json(PRED / "ngrams_fp8.json")["tasks"]

    # ---------------- 1.2 neutral twin
    if store.raw_rows("twin") and len(store.raw_rows("twin")) == len(tasks) * len(WS) * n_twin:
        twin = store.raw_rows("twin")
    else:
        twin = sample(llm, tok, make_reqs(tasks, "twin", WS, n_twin), prompt_ids, "A")
        store.save_raw("twin", twin)
    twin_lab = store.lab_rows("twin") if len(store.lab_rows("twin")) == len(twin) else label(lab, store, "twin", twin)
    lab_by_id = {r["sample_id"]: r for r in twin_lab}

    # ---------------- token-level coverage check of the FP8 n-gram on bf16 twin D programs, re-derivation rule
    final: dict[str, Any] = {"tasks": {}}
    for t in tasks:
        D = DEFAULTS[t]
        d_ids = [strip_eos(r["token_ids"]) for r in twin if r["task"] == t and lab_by_id[r["sample_id"]]["label"] == D]
        g_fp8 = [tuple(g) for g in ngr_fp8[t]["distinctive"]["ngrams"]]
        cov_bf16 = (sum(1 for s in d_ids if any(V.count_occurrences(s, g) for g in g_fp8)) / len(d_ids)) if d_ids else None
        rec = {"D": D, "n_twin_D": len(d_ids), "fp8_ngrams": [list(g) for g in g_fp8], "bf16_coverage_of_fp8": cov_bf16}
        if cov_bf16 is not None and cov_bf16 < FROZEN_CONSTANTS["ngram"]["coverage"]:
            others = NG.others_for(tok, t)
            res = NG.describe(tok, NG.derive(d_ids, others))
            sh = NG.sham(d_ids, others, res["ngrams"][0]) if res.get("ngrams") else {"ok": False}
            if sh.get("ok"):
                sh["text"] = tok.decode(sh["ngram"])
            rec.update({"distinctive": res, "sham": sh, "source": "bf16_twin_rederived"})
            append_deviation(f"{t}: FP8-pilot n-gram covers {cov_bf16:.2f} < 0.8 of bf16 twin D programs; re-derived on "
                             f"bf16 twin programs (declared rule): {res.get('texts')}")
        else:
            rec.update({"distinctive": ngr_fp8[t]["distinctive"], "sham": ngr_fp8[t]["sham"], "source": "fp8_pilot"})
        final["tasks"][t] = rec
        logger.info(f"{t}: twin D programs {len(d_ids)}, bf16 coverage of FP8 n-gram {cov_bf16}, source {rec['source']}")
    write_json(PRED / ("ngrams.json" if not sub else f"ngrams_{sub}.json"), final)
    masks = {t: final["tasks"][t]["distinctive"]["ngrams"] for t in tasks}
    sham_masks = {t: ([final["tasks"][t]["sham"]["ngram"]] if final["tasks"][t]["sham"].get("ok") else
                      [[EOS_IDS[1], EOS_IDS[1], EOS_IDS[1]]]) for t in tasks}

    # ---------------- T4 veto unit tests on 20 T03 twin samples
    ut_task = tasks[0]
    ut_bases = [r for r in twin if r["task"] == ut_task][:20]
    ut = V.unit_tests(llm, sp_fn, tok, ut_bases, prompt_ids, masks[ut_task])
    write_json(RESULTS / f"veto_unit_tests{('_' + sub) if sub else ''}.json", ut)
    logger.info(f"veto unit tests: {ut}")
    if not ut["all_pass"]:
        raise RuntimeError(f"veto unit tests failed: {ut}")

    # ---------------- 1.4 one-shot, sham, persistent (round 0), coupled on twin
    futs = {}
    for arm, mode, mk in [("oneshot", "oneshot", masks), ("sham", "oneshot", sham_masks),
                          ("persistent", "persistent", masks)]:
        if len(store.raw_rows(arm)) == len(twin):
            rows = store.raw_rows(arm)
        else:
            t0 = time.time()
            rows = V.run_veto(llm, sp_fn, tok, twin, prompt_ids, mk, mode, arm, rnd=0)
            timing_log("A", arm, len(rows), time.time() - t0)
            store.save_raw(arm, rows)
        futs[arm] = lab.submit(rows, arm)

    # ---------------- 1.6 fresh pushes: nonce and novelty
    for arm, templates, n in [("nonce", WS, n_nonce), ("novelty", ["NOV"], n_nov)]:
        if len(store.raw_rows(arm)) == len(tasks) * len(templates) * n:
            rows = store.raw_rows(arm)
        else:
            rows = sample(llm, tok, make_reqs(tasks, arm, templates, n), prompt_ids, "A")
            store.save_raw(arm, rows)
        futs[arm] = lab.submit(rows, arm)
    for arm, fu in futs.items():
        store.save_lab(arm, fu.result())

    # ---------------- 1.5 iterated rounds
    cfg = FROZEN_CONSTANTS["iterated"]
    chain = {t: {"masks": [list(map(list, masks[t]))], "rounds": [0], "stop_reason": None} for t in tasks}
    prev_arm = "persistent"
    for r in range(1, cfg["max_rounds"] + 1):
        prev_raw = {x["sample_id"]: x for x in store.raw_rows(prev_arm)}
        prev_lab = store.lab_rows(prev_arm)
        trig, new_masks, bases = [], {}, []
        for t in tasks:
            if chain[t]["stop_reason"]:
                continue
            share, natt = default_share(prev_lab, t)
            if share < cfg["trigger_default_share"]:
                chain[t]["stop_reason"] = f"round {r - 1} default share {share:.2f} < {cfg['trigger_default_share']}"
                continue
            ref = [strip_eos(prev_raw[x["sample_id"]]["token_ids"]) for x in prev_lab
                   if x["task"] == t and x["label"] == DEFAULTS[t]]
            cur = [tuple(g) for g in chain[t]["masks"][-1]]
            res = NG.derive(ref, NG.others_for(tok, t), exclude=set(cur))
            if not res["ok"]:
                chain[t]["stop_reason"] = f"round {r}: no_small_token_set"
                continue
            res = NG.describe(tok, res)
            mask_r = [list(g) for g in cur] + res["ngrams"]
            chain[t]["masks"].append(mask_r)
            chain[t]["rounds"].append(r)
            chain[t][f"round{r}"] = {"trigger_share": share, "n_ref": len(ref), "added": res}
            new_masks[t] = mask_r
            trig.append(t)
            bases += [prev_raw[x["sample_id"]] for x in sorted(prev_lab, key=lambda z: z["sample_id"])
                      if x["task"] == t]
        if not trig:
            break
        arm = f"iter{r}"
        # rebase prompt keys / ids for the next round's engine (the base rows are previous-round rows)
        bases = [dict(b, sample_id=b["sample_id"]) for b in bases]
        t0 = time.time()
        rows = V.run_veto(llm, sp_fn, tok, bases, prompt_ids, new_masks, "persistent", arm, rnd=r)
        timing_log("A", arm, len(rows), time.time() - t0)
        store.save_raw(arm, rows)
        label(lab, store, arm, rows)
        logger.info(f"round {r}: triggered {trig}")
        prev_arm = arm
    write_json(PRED / ("iterated_chain.json" if not sub else f"iterated_chain_{sub}.json"), chain)
    logger.info(f"process A done; judge spend ${lab.spent():.4f}")


# ------------------------------------------------------------------------------------------------ process C
def guard() -> dict:
    bench_import()
    from bench.common.commit import verify_chain

    from common import sha256_file

    if not COMMIT_LOG.exists():
        raise RuntimeError("no commitments.log")
    if not verify_chain(COMMIT_LOG):
        raise RuntimeError("hash chain verification FAILED")
    lines = [json.loads(l) for l in COMMIT_LOG.read_text().splitlines() if l.strip()]
    seals = [i for i, l in enumerate(lines) if l["kind"] == "SEAL_BEFORE_BANS"]
    if not seals:
        raise RuntimeError("no SEAL_BEFORE_BANS line: refusing to sample bans")
    seal = lines[seals[-1]]
    # post-ban revisions (appended after the seal) are accepted only when the revised file matches the revision line
    # AND the preserved sealed copy still hashes to the originally committed sha256
    revs = {l["path"]: l for l in lines[seals[-1] + 1:] if l["kind"] == "post_ban_revision"}
    moved = {l["path"]: l["sealed_copy_moved_to"] for l in lines[seals[-1] + 1:]
             if l["kind"] == "post_ban_note" and l.get("sealed_copy_moved_to")}
    bad, revised = [], []
    for l in lines[:seals[-1]]:
        p = l.get("path")
        if not p or sha256_file(ROOT / p) == l["sha256"]:
            continue
        r = revs.get(p)
        copy = moved.get(p, r.get("sealed_copy") if r else None)
        if r and sha256_file(ROOT / p) == r["sha256"] and r["supersedes_sha256"] == l["sha256"] and copy \
                and (ROOT / copy).exists() and sha256_file(ROOT / copy) == l["sha256"]:
            revised.append(p)
        else:
            bad.append(p)
    if bad:
        raise RuntimeError(f"committed files changed after commitment: {bad}")
    seal["revised_after_seal"] = revised
    logger.info(f"guard OK: chain verified, seal at {seal['ts']}, {len(lines)} lines, committed files intact"
                f"{'; documented post-ban revisions (sealed bytes preserved): ' + ', '.join(revised) if revised else ''}")
    return seal


def stage_c(sub: str = "", tasks: list[str] | None = None, n_ban: int = N_BAN_PER_T, workers: int = 10) -> None:
    from labelpool import Labeller

    seal = guard() if not sub else {"utc": "smoke"}
    tasks = tasks or TASK_ORDER
    store = Store(sub)
    prompt_ids = {k: v["ids"] for k, v in read_json(PROMPTS / "prompt_ids.json").items()}
    llm = make_llm()
    tok = llm.get_tokenizer()
    lab = Labeller(workers=workers)
    first_utc = utc_now()
    rows = sample(llm, tok, make_reqs(tasks, "ban", WS, n_ban), prompt_ids, "C")
    store.save_raw("ban", rows)
    label(lab, store, "ban", rows)
    write_json(RESULTS / f"ban_sampling_times{('_' + sub) if sub else ''}.json",
               {"seal_utc": seal.get("utc"), "first_ban_request_utc": first_utc, "n": len(rows)})
    logger.info(f"process C done: {len(rows)} ban samples; judge spend ${lab.spent():.4f}")


if __name__ == "__main__":
    from common import setup_logging

    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["A", "C"])
    ap.add_argument("--smoke", action="store_true", help="T03 only, 2 per template, into data/smoke/")
    a = ap.parse_args()
    setup_logging(f"gpu_{a.stage}{'_smoke' if a.smoke else ''}")
    workers = max(4, detect_cpus() - 3)
    if a.stage == "A":
        if a.smoke:
            stage_a("smoke", ["T03", "T05"], n_twin=2, n_nonce=1, n_nov=4, workers=workers)
        else:
            stage_a(workers=workers)
    else:
        if a.smoke:
            stage_c("smoke", ["T03"], n_ban=2, workers=workers)
        else:
            stage_c(workers=workers)
