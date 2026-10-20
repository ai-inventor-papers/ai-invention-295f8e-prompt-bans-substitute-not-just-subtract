#!/usr/bin/env python3
"""Steps 4 and 7.5: FRLP cell table (all variants), mixture identity (validation v), ESS table per condition family,
coverage of natural programs by forced programs, and the run's bookkeeping files (timings, cost, deviations,
protocol)."""

from __future__ import annotations

import collections
from typing import Any

import numpy as np
from loguru import logger

from config import (DATA, ESS_FLAG, FILLERS, LOGS, PROMPTS, RESULTS, ROOT, SUITE, TASKS, read_json, read_jsonl,
                    setup_logging, utc_now, write_json)
from frlp import build_task_data, coverage, mixture_identity, write_cells


def ess_table() -> dict[str, Any]:
    rows = read_jsonl(RESULTS / "frlp_cells.jsonl")
    fam = collections.defaultdict(list)
    for r in rows:
        if r["variant"] != "primary" or r["half"] == "all" or r["ess"] is None:
            continue
        kind = r["condition"].split("|")[0]
        if kind == "exp1":
            kind = "exp1_gate"
        fam[(r["task"], kind)].append(r["ess"])
    return {f"{t}|{k}": {"n_cells": len(v), "median_ess": float(np.median(v)), "frac_below_5": float(np.mean(
        np.array(v) < ESS_FLAG)), "p10": float(np.quantile(v, 0.1)), "p90": float(np.quantile(v, 0.9))}
            for (t, k), v in sorted(fam.items())}


def bookkeeping() -> None:
    gen = read_json(DATA / "forced_generation_summary.json") if (DATA / "forced_generation_summary.json").exists() else {}
    units = read_jsonl(ROOT / "scores" / "units_done.jsonl")
    gpu_s = sum(u["seconds"] for u in units)
    by_q = collections.defaultdict(lambda: {"units": 0, "tokens": 0, "seconds": 0.0})
    for u in units:
        by_q[u["queue"]]["units"] += 1
        by_q[u["queue"]]["tokens"] += u["n_tokens"]
        by_q[u["queue"]]["seconds"] += u["seconds"]
    qf = read_json(LOGS / "queue_final.json") if (LOGS / "queue_final.json").exists() else {}
    write_json(RESULTS / "timings.json", {"generation": gen.get("timings"), "scoring_by_queue": by_q,
                                          "scoring_gpu_seconds": gpu_s, "skipped_units": len(qf.get("skipped_after_deadline", [])),
                                          "gpu": "NVIDIA L4 (23 GB)",
                                          "gpu_hours_scoring": gpu_s / 3600})
    cost = read_json(SUITE / "results" / "openrouter_cost.json") if (SUITE / "results" / "openrouter_cost.json").exists() else {}
    write_json(RESULTS / "openrouter_cost.json", {**cost, "note": "judge calls (openai/gpt-4.1-mini) for runtime/AST "
                                                  "disagreements only; cap USD 0.5"})
    pv = read_json(PROMPTS / "prompts_v2.json")
    tp = read_json(LOGS / "throughput.json") if (LOGS / "throughput.json").exists() else {}
    yl = read_json(RESULTS / "yields.json")
    deviations = [
        "Yield correction: L = log y_j + logmeanexp(lw) is primary for the gate and implied distributions; the literal "
        "formula L_raw is reported beside it (gains/C1 unaffected).",
        f"Neutral-twin filler {pv['alignment']['filler']!r}; {len(pv['alignment']['failures'])} alignment failures "
        f"over {pv['alignment']['pairs']} pairs.",
        "Noun ranking: all 718 noun-bank candidates are single-token, so the rank reduces to SUBTLEX frequency; a "
        "minimal neutrality screen removed one vulgar word and path/data-structure words "
        "(prompts_v2.json rules.noun_exclusions).",
        "vLLM ran with enforce_eager=True (no C compiler in the container), max_num_seqs=48 (plan: 8) for "
        "throughput on the L4; per-request seeds make the sampled distribution independent of batching.",
        "Scorer precision: bf16 activations failed validation (cached vs full up to 2.1 nats per program; B=1 vs "
        "B=8 contrast 2.7 nats). Production scoring keeps bf16 weights but runs fp32 activations with TF32 matmuls "
        "and an fp32 lm_head/log-softmax: per-program cached-vs-full 0.074 (passes 0.25), contrast 0.119 (misses "
        "0.10 narrowly), B=1 vs B=8 0.045 (passes). One path is used for every condition.",
        f"Cut rule fired: measured {tp.get('tokens_per_s', float('nan')):.0f} tok/s (TF32) projected Q1-Q6 at M=30 "
        f"to {tp.get('projected_q1_q6_min_M30', float('nan')):.0f} min > 150 -> M={tp.get('M')} programs per "
        f"algorithm (halves of {int(tp.get('M', 20)) // 2}) and the gate on {tp.get('gate_paraphrases')} paraphrases.",
        "pipeline.py (exp1 stage code) was copied in addition to the plan's list because its label_rows/"
        "evaluate_unique implement the canonical labeller orchestration; its evaluation cache points into data/.",
        "Gate events: the realised mode / clear-mode test is computed over the allowed labels (banned labels "
        "excluded under a ban).",
        "Variant (ii) uses ||h|| of the layer-18 OUTPUT at each edited position; its program-position edit is "
        "applied at every teacher-forced input position.",
    ] + list(yl.get("deviations", []))
    free = read_jsonl(DATA / "freeform_raw.jsonl")
    flab = read_jsonl(DATA / "freeform_labelled.jsonl")
    trunc = {t: float(np.mean([r["finish_reason"] == "length" for r in free if r["task"] == t])) for t in TASKS}
    oth = {t: float(np.mean([r["label"] == "other" for r in flab if r["task"] == t])) for t in TASKS}
    write_json(RESULTS / "freeform_quality.json", {"truncated_at_32_tokens": trunc, "labelled_other": oth,
                                                   "note": "max_tokens=32 is frozen (exp1 free_prompt); many "
                                                           "truncated answers stop before naming an algorithm and "
                                                           "are labelled 'other' (the association profile is the "
                                                           "SECONDARY aim reference only)"})
    deviations.append(f"Free-form answers: {trunc} truncated at the frozen 32 tokens; labelled 'other' shares {oth} "
                      "(association profiles are therefore weak; secondary aim only).")
    write_json(RESULTS / "deviations.json", deviations)
    write_json(RESULTS / "protocol.json", {
        "model": "Qwen/Qwen3-8B@b968826d9c46dd6066d109eabc6255188de91218, thinking off",
        "chat_tail": "<|im_start|>assistant\\n<think>\\n\\n</think>\\n\\n",
        "templates": "src/config.py TEMPLATES (W1..W5 ban / mention / neutral)",
        "neutral_padding": {"filler": pv["alignment"]["filler"], "candidates": FILLERS,
                            "failures": pv["alignment"]["failures"]},
        "nouns": pv["nouns"], "spec_suffix_tokens": pv["spec_suffix_tokens"],
        "response_text": "'```python\\n' + name-scrubbed code (ending in newline) + '```'",
        "tokenisation": "prompt (chat string) and response tokenised separately, add_special_tokens=False, concatenated",
        "precision": "bf16 weights; fp32 activations; TF32 matmuls; fp32 lm_head + log-softmax",
        "row_schema": ["task", "condition", "template", "paraphrase_id", "sample_id", "seed", "model", "decoding",
                       "label", "labeller_source", "passed", "code_sha256", "code"],
        "ess_flag": "cells with ESS < 5 are flagged; ESS-weighted variant down-weights them by ESS/5",
    })


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("analysis_misc")
    tds = build_task_data()
    mi = mixture_identity(tds)
    write_json(RESULTS / "mixture_identity.json", mi)
    logger.info(f"mixture identity: {mi}")
    n = write_cells(tds)
    write_json(RESULTS / "ess_table.json", ess_table())
    write_json(RESULTS / "coverage.json", coverage())
    bookkeeping()
    logger.info(f"analysis_misc done ({n} cells) at {utc_now()}")


if __name__ == "__main__":
    main()
