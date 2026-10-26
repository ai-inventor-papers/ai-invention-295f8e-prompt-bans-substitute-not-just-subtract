#!/usr/bin/env python3
"""S2: FRLP programs. For each of the 11 catalogue algorithms j, sample responses under the 10 forced paraphrases
F_j (T=1.0, top-p 1.0, max 1024 tokens, thinking off) with the HF engine (fallback F2), label them with the canonical labeller, keep the
first 30 ATTEMPTED programs labelled j in generation order, name-scrub them, and record the per-prompt sample
counts that define the importance-sampling mixture proposal.

Generation order: round r draws samples 4r..4r+3 of every paraphrase (40 per round); rounds are generated in
blocks, and the 'first 30' are taken in (round, paraphrase, index) order, i.e. the plan's sequential rule.
"""

from __future__ import annotations

import collections
import gc
import json
import time
from typing import Any

from loguru import logger

from cfg import (ALGOS, DATA_DIR, DISPLAY, MAX_NEW_TOKENS, N_PROGRAMS, PROMPTS_DIR, RESULTS_DIR, TASKS, model_path,
                 read_jsonl, sha256_text, stable_seed, write_json, write_jsonl, IM_END)

RAW = DATA_DIR / "programs_raw.jsonl"
OUT = DATA_DIR / "frlp_programs.jsonl"
PER_PARA_ROUND = 4
MAX_PARA = 16          # samples per paraphrase before the descriptive top-up
DESC_TOPUP = 80
BLOCK_ROUNDS = 2       # rounds generated per block (8 per paraphrase)


class HFGen:
    """Fallback F2 (vLLM cannot start: torch-inductor needs a C compiler this machine lacks): HF sampling with the
    engine's inverse-CDF sampler, one independent PCG64 uniform stream per request (exact T=1.0 sampling)."""

    def __init__(self) -> None:
        from engine import load_model

        self.tok, self.model = load_model()

    def generate(self, reqs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        from engine import sample_grouped, u_stream

        t0 = time.time()
        for r in reqs:
            r["u"] = u_stream("frlp", r["task"], r["algorithm"], r["prompt_kind"], r["prompt_index"], r["sample_index"])
        outs = sample_grouped(self.model, reqs, prefill_cache={})
        res, ntok = [], 0
        for r, o in zip(reqs, outs):
            ids = o["token_ids"]
            ntok += len(ids)
            text = self.tok.decode(ids, skip_special_tokens=True)
            res.append({**{k: v for k, v in r.items() if k not in ("ids", "u")}, "text": text, "gen_token_ids": ids,
                        "finish_reason": o["finish_reason"], "n_tokens": len(ids),
                        "sampled_logprob": o["logprob_sum"]})
        dt = time.time() - t0
        logger.info(f"generated {len(reqs)} samples / {ntok} tokens in {dt:.0f}s ({ntok / max(dt, 1e-9):.0f} tok/s)")
        return res


def _requests(fp: dict[str, Any], task: str, j: str, round_idx: int, use_desc: bool) -> list[dict[str, Any]]:
    forced = fp["tasks"][task]["forced"][j]
    reqs = []
    if not use_desc:
        for k, pr in enumerate(forced["paraphrases"]):
            for i in range(PER_PARA_ROUND):
                idx = round_idx * PER_PARA_ROUND + i
                reqs.append({"task": task, "algorithm": j, "prompt_kind": "paraphrase", "prompt_index": k,
                             "sample_index": idx, "round": round_idx, "ids": pr["ids"],
                             "seed": stable_seed("frlp", task, j, "para", k, idx) % (2 ** 31)})
    else:
        pr = forced["descriptive"]
        for i in range(10 * PER_PARA_ROUND):
            idx = round_idx * 10 * PER_PARA_ROUND + i
            reqs.append({"task": task, "algorithm": j, "prompt_kind": "descriptive", "prompt_index": 10,
                         "sample_index": idx, "round": round_idx, "ids": pr["ids"],
                         "seed": stable_seed("frlp", task, j, "desc", idx) % (2 ** 31)})
    return reqs


def _label(rows: list[dict[str, Any]]) -> None:
    from labelling import extract, label_codes

    items = []
    for r in rows:
        code, how = extract(r["text"])
        r["code"], r["extract_method"] = code, how
        r["code_sha256"] = sha256_text(code) if code else None
        items.append({"task": r["task"], "code": code})
    labs = label_codes(items, use_judge=True)
    for r, lab in zip(rows, labs):
        r.update(lab)


def _order_key(r: dict[str, Any]) -> tuple:
    kind = 0 if r["prompt_kind"] == "paraphrase" else 1
    return (kind, r["round"], r["prompt_index"], r["sample_index"])


def stage_programs() -> dict[str, Any]:
    fp = json.loads((PROMPTS_DIR / "frozen_prompts.json").read_text())
    rows: list[dict[str, Any]] = read_jsonl(RAW)
    done_keys = {(r["task"], r["algorithm"], r["prompt_kind"], r["prompt_index"], r["sample_index"]) for r in rows}
    gen = None
    state = {(t, j): {"round": 0, "use_desc": False, "desc_rounds": 0} for t in TASKS for j in ALGOS[t]}
    # resume: infer rounds already present
    for (t, j), st in state.items():
        mine = [r for r in rows if r["task"] == t and r["algorithm"] == j and r["prompt_kind"] == "paraphrase"]
        st["round"] = (max([r["round"] for r in mine]) + 1) if mine else 0
        st["desc_rounds"] = len({r["round"] for r in rows if r["task"] == t and r["algorithm"] == j
                                 and r["prompt_kind"] == "descriptive"})

    def accepted(t: str, j: str) -> list[dict[str, Any]]:
        ok = [r for r in rows if r["task"] == t and r["algorithm"] == j and r.get("label") == j
              and r.get("code") and r.get("finish_reason") == "stop"]
        return sorted(ok, key=_order_key)

    def first_round_acc(t: str, j: str) -> float:
        r0 = [r for r in rows if r["task"] == t and r["algorithm"] == j and r["prompt_kind"] == "paraphrase"
              and r["round"] == 0]
        return sum(r.get("label") == j for r in r0) / max(1, len(r0))

    t_start = time.time()
    while True:
        reqs = []
        for (t, j), st in state.items():
            if len(accepted(t, j)) >= N_PROGRAMS:
                continue
            if st["round"] >= 1 and first_round_acc(t, j) < 0.25:
                st["use_desc"] = True
            n_para = st["round"] * PER_PARA_ROUND
            if not st["use_desc"] and n_para < MAX_PARA:
                for rr in range(st["round"], min(st["round"] + BLOCK_ROUNDS, MAX_PARA // PER_PARA_ROUND)):
                    reqs += _requests(fp, t, j, rr, False)
            elif st["desc_rounds"] * 10 * PER_PARA_ROUND < (DESC_TOPUP if not st["use_desc"] else DESC_TOPUP + 40):
                reqs += _requests(fp, t, j, st["desc_rounds"], True)
        reqs = [q for q in reqs if (q["task"], q["algorithm"], q["prompt_kind"], q["prompt_index"],
                                    q["sample_index"]) not in done_keys]
        if not reqs:
            break
        if gen is None:
            gen = HFGen()
        logger.info(f"block: {len(reqs)} requests over "
                    f"{len({(q['task'], q['algorithm']) for q in reqs})} algorithms")
        new = gen.generate(reqs)
        _label(new)
        for q in new:
            done_keys.add((q["task"], q["algorithm"], q["prompt_kind"], q["prompt_index"], q["sample_index"]))
            q["gen_utc"] = time.time()
        rows.extend(new)
        write_jsonl(RAW, rows)
        for (t, j), st in state.items():
            st["round"] = (max([r["round"] for r in rows if r["task"] == t and r["algorithm"] == j
                                and r["prompt_kind"] == "paraphrase"] or [-1]) + 1)
            st["desc_rounds"] = len({r["round"] for r in rows if r["task"] == t and r["algorithm"] == j
                                     and r["prompt_kind"] == "descriptive"})
        summ = {f"{t}:{j}": len(accepted(t, j)) for (t, j) in state}
        logger.info(f"accepted so far: {summ}  (elapsed {(time.time() - t_start) / 60:.1f} min)")
    if gen is not None:
        del gen
        gc.collect()
    return finalize(fp, rows)


def finalize(fp: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    from labelling import label_codes
    from scrub import scrub_response

    from transformers import AutoTokenizer

    from cfg import hf_kwargs

    tok = AutoTokenizer.from_pretrained(model_path(), **hf_kwargs())
    out_rows, summary = [], {}
    deviations = []
    to_check = []
    for t in TASKS:
        for j in ALGOS[t]:
            mine = [r for r in rows if r["task"] == t and r["algorithm"] == j]
            ok = sorted([r for r in mine if r.get("label") == j and r.get("code") and r.get("finish_reason") == "stop"],
                        key=_order_key)
            keep = ok[:N_PROGRAMS]
            counts = collections.Counter((r["prompt_kind"], r["prompt_index"]) for r in mine)
            summary[f"{t}:{j}"] = {
                "n_generated": len(mine), "n_labelled_j": len(ok), "n_kept": len(keep),
                "acceptance_rate": len(ok) / max(1, len(mine)),
                "pass_rate_kept": sum(r["passed"] for r in keep) / max(1, len(keep)),
                "first_round_acceptance": (sum(r.get("label") == j for r in mine if r["round"] == 0 and
                                               r["prompt_kind"] == "paraphrase")
                                           / max(1, sum(1 for r in mine if r["round"] == 0 and
                                                        r["prompt_kind"] == "paraphrase"))),
                "descriptive_used": any(r["prompt_kind"] == "descriptive" for r in mine),
                "prompt_counts": {f"{k[0]}:{k[1]}": v for k, v in sorted(counts.items())},
                "label_distribution": dict(collections.Counter(r.get("label") for r in mine)),
            }
            if len(keep) < N_PROGRAMS:
                deviations.append(f"{t}:{j} only {len(keep)} programs labelled j (target {N_PROGRAMS})")
            for i, r in enumerate(keep):
                scored, scode, info = scrub_response(r["text"])
                rec = {"task": t, "algorithm": j, "prog_index": i, "half": 1 if i % 2 == 0 else 2,
                       "prompt_kind": r["prompt_kind"], "prompt_index": r["prompt_index"],
                       "sample_index": r["sample_index"], "round": r["round"], "seed": r["seed"],
                       "orig_text": r["text"], "orig_code": r["code"], "label": r["label"], "passed": r["passed"],
                       "n_passed": r.get("n_passed"), "fail_case": r.get("fail_case"),
                       "labeller_source": r.get("labeller_source"), "gen_token_ids": r["gen_token_ids"],
                       "sampled_logprob": r.get("sampled_logprob"), "scrub": info, "scrubbed_text": scored,
                       "scrubbed_code": scode}
                out_rows.append(rec)
                if scored is not None and info.get("ok") and info.get("changed"):
                    to_check.append(rec)
    # (iii) re-run tests + labeller on scrubbed programs
    if to_check:
        from labelling import extract

        items = []
        for rec in to_check:
            code, _ = extract(rec["scrubbed_text"])
            items.append({"task": rec["task"], "code": code})
        labs = label_codes(items, use_judge=True)
        for rec, lab in zip(to_check, labs):
            same = (lab["label"] == rec["label"] and lab["passed"] == rec["passed"]
                    and lab.get("n_passed") == rec.get("n_passed") and lab.get("fail_case") == rec.get("fail_case"))
            rec["scrub_verified"] = bool(same)
            rec["scrub_check"] = {"label": lab["label"], "passed": lab["passed"], "n_passed": lab.get("n_passed"),
                                  "fail_case": lab.get("fail_case")}
    n_scrub_kept = n_scrub_reverted = n_unchanged = n_outside = 0
    for rec in out_rows:
        info = rec["scrub"]
        n_outside += int(bool(info.get("outside_fence")))
        if rec["scrubbed_text"] is None or not info.get("ok"):
            rec["scored_text"], rec["scrub_status"] = rec["orig_text"], "scrub_failed_unscrubbed"
            n_scrub_reverted += 1
        elif not info.get("changed"):
            rec["scored_text"], rec["scrub_status"] = rec["scrubbed_text"], "no_names"
            n_unchanged += 1
        elif rec.get("scrub_verified"):
            rec["scored_text"], rec["scrub_status"] = rec["scrubbed_text"], "scrubbed_verified"
            n_scrub_kept += 1
        else:
            rec["scored_text"], rec["scrub_status"] = rec["orig_text"], "scrub_changed_behaviour_unscrubbed"
            n_scrub_reverted += 1
        ids = tok(rec["scored_text"], add_special_tokens=False)["input_ids"] + [IM_END]
        rec["score_ids"] = ids
        rec["n_score_tokens"] = len(ids)
    write_jsonl(OUT, out_rows)
    res = {"per_algorithm": summary, "n_programs": len(out_rows), "scrub": {
        "scrubbed_verified": n_scrub_kept, "reverted_to_unscrubbed": n_scrub_reverted, "no_names": n_unchanged,
        "outside_fence_dropped": n_outside}, "deviations": deviations}
    write_json(RESULTS_DIR / "frlp_programs_summary.json", res)
    logger.info(f"FRLP programs: {len(out_rows)} kept; scrub {res['scrub']}; deviations {deviations}")
    return res
