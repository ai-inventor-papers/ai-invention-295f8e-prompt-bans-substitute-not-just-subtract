"""Assemble results: pilot statistics, audits, deviations, method_out.json (exp_gen_sol_out)."""

from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from loguru import logger

from .catalogue import TASK_ORDER, TASKS
from .report import build_method_out, neutral_nouns, no_ban_audit, pilot_stats, recount, verify_commitments
from .stats import kendall_tau, self_test

DEVIATIONS = [
    "HARDWARE: the pod has an RTX 2000 Ada (16 GB, ~224 GB/s), not the planned RTX A4500 (20 GB). bf16 Qwen3-8B "
    "(16.4 GB) does not fit, so the official FP8 checkpoint Qwen/Qwen3-8B-FP8 (block-wise FP8 weights) is used for "
    "sampling AND scoring, served through vLLM's precompiled FP8 Marlin kernels (weight-only FP8, bf16 activations).",
    "NO C COMPILER on the machine: Triton cannot build its driver, so vLLM runs with enforce_eager=True, "
    "TORCH_COMPILE_DISABLE=1 and VLLM_TEST_FORCE_FP8_MARLIN=1 (no CUDA graphs / torch.compile). Numerics are unchanged "
    "in kind; throughput is lower.",
    "SCORING ENGINE: HF transformers cannot hold bf16 weights on 16 GB and its FP8 path needs Triton, so job B scores "
    "with vLLM prompt logprobs (same engine/kernels as the sampler). vLLM disables prefix caching for prompt-logprob "
    "requests, so every scoring request is a full prefill (prompt + program). The planned vLLM-vs-HF check (a) becomes "
    "sampler-vs-scorer on the same engine (20/20 within tolerance, both on the sampled ids and on the re-tokenized "
    "text); the cache-reuse check (b) has no analogue and is replaced by a single-request vs batched check.",
    "FORCED PROPOSAL: exp1's five paraphrases (ids 0-4) x 8 rounds = 40 attempts per mode instead of ids 0-9 x 4 rounds, "
    "because every program must be scored under baseline + every generating paraphrase with full prefills on a GPU with "
    "~1/3 of the planned throughput; the plan's fallback names exactly this 5-paraphrase mixture, and ids 0-4 are the "
    "wordings the screen artifact shares. Ids 5-9 are frozen in the spec but never rendered.",
    "TOP-UPS: modes with M_j < 30 got 4 extra rounds of ids 0-4 (20 attempts); modes whose 40-attempt adherence was < 0.3 "
    "also got 20 attempts of the descriptive variant ('Implement the approach described as: <mechanism>.') in the same "
    "job (the plan triggers it at 60 attempts; done earlier to save a GPU round trip). Every component that generated "
    "attempts for a mode is in that mode's exact mixture proposal.",
    "max_num_seqs=48 (plan: 8, raise to 16 if KV allows); KV capacity 31,040 tokens. Batch size does not change the "
    "sampling distribution.",
    "GOLD SET EXTENSION: 10 pilot programs + every reference + 2 random forced attempts per mode (direction's subset "
    "metrics reported beside the full-set metrics).",
    "JUDGES: j1 google/gemini-2.5-flash-lite, j2 openai/gpt-4.1-mini, j3 deepseek/deepseek-chat-v3.1 (tie-break); "
    "OpenRouter /key and /models endpoints are blocked by the proxy (Cloudflare 403), so the phase budget could not be "
    "read; spend is tracked from usage.cost per call.",
    "REVISION ROUND 1 (T03, T13): T03 failed runtime-vs-adjudicated (0.893) and T13 failed kappa (0.779) at round 0; "
    "the runtime rules were revised (T03: partial features of crashed probes label the attempted mechanism, hand-written "
    "heaps detected by sift-call counts; T13: a per-pair helper means union-find even with a preliminary sort) and "
    "both passed with a fresh 6-program holdout.",
    "CANONICAL-SUITE RE-CHECK: not applicable (no T1/T2 task here and exp1 is not a declared dependency).",
    "BAN AUDIT LEXICON: the 15 frozen W1-W5 strings are not available to this artifact; the audit greps all rendered "
    "prompts for a superset ban/novelty lexicon plus 'Zorblax'.",
    "STRESS SIZES: T13's widest-interval stress case uses n=800 (spec bound 1500 stays a true upper bound) so the "
    "interval-tree reference passes at <= 0.25x the limit; R2 gained shuffled-edge forests after a mutant survived.",
    "CODE-ONLY UNSCRUBBED SCORING SENSITIVITY: not computed (first item in the plan's time-overrun drop order after "
    "the Llama pilot).",
]

NOT_PRODUCED = ["Llama forced programs and Llama FRLP", "ban / mention / neutral FRLP matrices",
                "any sampled ban event", "code-only unscrubbed scoring sensitivity"]


def _spend(root: Path) -> dict:
    p = root / "logs" / "openrouter_spend.jsonl"
    tot, by = 0.0, Counter()
    n = 0
    if p.exists():
        for l in p.open():
            r = json.loads(l)
            tot += r.get("cost") or 0.0
            by[r.get("model")] += r.get("cost") or 0.0
            n += 1
    return {"usd_total": tot, "n_calls": n, "by_model": dict(by)}


def _labeller_stats(root: Path) -> dict:
    labs = [json.loads(l) for l in (root / "data" / "labels_combined.jsonl").open()]
    valid = [r for r in labs if r.get("valid")]
    agree = sum(r["ast_label"] == r["runtime_label"] for r in valid)
    src = Counter(r["labeller_source"] for r in labs)
    scr = Counter(str((r.get("scrub") or {}).get("verified")) for r in labs if r["condition"] == "forced")
    return {"n": len(labs), "n_valid": len(valid), "runtime_ast_raw_agreement": agree / max(len(valid), 1),
            "labeller_source_counts": dict(src), "judge_share": src.get("judge", 0) / max(len(labs), 1),
            "scrub_verified_counts": dict(scr)}


def _adherence(root: Path) -> dict:
    forced = [json.loads(l) for l in (root / "data" / "samples_forced.jsonl").open()]
    by = defaultdict(list)
    for r in forced:
        by[(r["task"], r["forced_mode"])].append(r)
    out = {}
    for (t, m), rs in sorted(by.items()):
        conf = Counter(r["label"] for r in rs)
        out[f"{t}:{m}"] = {"attempts": len(rs), "adherence": conf.get(m, 0) / len(rs),
                           "pass_rate_labelled": (sum(r["passed"] for r in rs if r["label"] == m) / max(conf.get(m, 0), 1)),
                           "confusion": dict(conf)}
    return out


def _llama(root: Path) -> dict:
    p = root / "data" / "samples_llama_pilot.jsonl"
    if not p.exists():
        return {}
    rows = [json.loads(l) for l in p.open()]
    out = {}
    for t in TASK_ORDER:
        rs = [r for r in rows if r["task"] == t]
        if rs:
            out[t] = pilot_stats(rs, t)
    return out


def finalize(root: Path) -> None:
    t0 = time.time()
    pilot = [json.loads(l) for l in (root / "data" / "samples_pilot.jsonl").open()]
    stats = {t: pilot_stats(pilot, t) for t in TASK_ORDER}
    stageA = json.loads((root / "results" / "stageA_nominations.json").read_text())
    pB = root / "results" / "stageB_nominations.json"
    stageB = json.loads(pB.read_text()) if pB.exists() else None
    cells = [json.loads(l) for l in (root / "data" / "frlp_cells.jsonl").open()]
    validity = json.loads((root / "results" / "frlp_validity.json").read_text())
    gate = json.loads((root / "results" / "gate_summary.json").read_text())
    frozen = json.loads((root / "results" / "frozen_tasks.json").read_text())["frozen"]
    status = {}
    for t in TASK_ORDER:
        g = gate.get(t, {}).get("status")
        if t in frozen:
            status[t] = "frozen"
        elif g == "gated":
            status[t] = "excluded"  # gated but beyond the 12-task freeze cap of the stop rule
        elif g and g.startswith("failed"):
            status[t] = "replace"
        else:
            status[t] = "not_reached"
    nouns = neutral_nouns(root)
    audit = no_ban_audit(root)
    rc = recount(root, stats)
    ver = verify_commitments(root)
    chk = json.loads((root / "results" / "scoring_consistency.json").read_text())
    build = json.loads((root / "results" / "build_summary.json").read_text())
    llama = _llama(root)
    extract = json.loads((root / "data" / "extract" / "extract_summary.json").read_text())
    lab = _labeller_stats(root)
    adh = _adherence(root)
    conf_signals = {
        "tasks_pass_rate_ge_0.5": sum(1 for t in TASK_ORDER if stats[t]["pass_rate"] >= 0.5),
        "judge_share_le_0.30": lab["judge_share"] <= 0.30, "judge_share": lab["judge_share"],
        "modes_adherence_ge_0.5": sum(1 for v in adh.values() if v["adherence"] >= 0.5), "n_modes": len(adh)}
    metadata = {
        "method_name": "Coding-task bench with a baseline pilot (iteration 2)",
        "artifact_plan_id": "gen_plan_experiment_5_idx6",
        "model": "Qwen/Qwen3-8B-FP8 (vLLM 0.11.0, FP8 Marlin, eager); decoding T=1.0 top_p=1.0 top_k=-1 min_p=0, thinking off",
        "decoding": {"temperature": 1.0, "top_p": 1.0, "top_k": -1, "min_p": 0.0, "repetition_penalty": 1.0,
                     "max_tokens": 1024, "association_max_tokens": 96, "seed_base": 20261020},
        "baseline_vs_method": "predict_ladder (sampled-frequency ladder, the standard baseline) vs predict_association "
                              "(free-form elicitation) vs predict_proximity (canonical-token proximity); FRLP-implied "
                              "label probabilities vs a uniform baseline (log score) in frlp_validity",
        "deviations": DEVIATIONS, "not_produced": NOT_PRODUCED,
        "orders": {"stageA": stageA["order"], "stageB": stageB["order"] if stageB else None,
                   "kendall_tau_A_B": kendall_tau(stageA["order"], stageB["order"]) if stageB else None},
        "frozen_tasks": frozen, "build_status": status,
        "commitments": {"log": (root / "commitments.log").read_text().splitlines(), **ver},
        "no_ban_audit": audit, "recount": rc, "stats_self_test": self_test(),
        "scoring_consistency": {k: v for k, v in chk.items() if k != "a_rows"},
        "openrouter_spend": _spend(root), "labeller_population": lab, "forced_adherence": adh,
        "confirmation_signals": conf_signals, "build_summary": build,
        "independent_rederivation": (json.loads((root / "results" / "rederive_headlines.json").read_text())["summary"]
                                     if (root / "results" / "rederive_headlines.json").exists() else None),
        "tracer_unit_tests": (json.loads((root / "results" / "tracer_unit_tests.json").read_text())
                              if (root / "results" / "tracer_unit_tests.json").exists() else None),
        "ast_fixture_check_thealgorithms": ({k: v for k, v in json.loads((root / "results" / "ast_fixture_check.json")
                                                                      .read_text()).items() if k != "rows"}
                                            if (root / "results" / "ast_fixture_check.json").exists() else None),
        "dependency_extract_summary": extract,
        "llama_pilot": ("run" if llama else "not run: dropped first in the plan's time-overrun order or checkpoint "
                                            "unavailable (bf16 Llama does not fit on 16 GB; FP8 checkpoint needed)"),
        "timings": json.loads((root / "results" / "timings.json").read_text()) if (root / "results" / "timings.json").exists() else {},
        "neutral_nouns_note": "all 718 candidates are single Qwen3 tokens, so the token-count match is degenerate; nouns "
                              "are unique across display names (frequency-ranked).",
    }
    ctx = {"pilot_stats": stats, "stageA": stageA, "stageB": stageB, "frlp_cells": cells, "frlp_validity": validity,
           "frozen": frozen, "status": status, "metadata": metadata, "llama": llama}
    out = build_method_out(root, ctx)
    (root / "method_out.json").write_text(json.dumps(out, indent=1, default=str))
    (root / "results" / "pilot_stats.json").write_text(json.dumps(stats, indent=1))
    logger.info(f"method_out.json written ({len(out['datasets'][0]['examples'])} candidates) in {time.time() - t0:.0f}s; "
                f"audit hits={audit['ban_lexicon_hits']}, recount mismatches={rc['n_mismatches']}, "
                f"commitment mismatches={len(ver['file_hash_mismatches'])}, chain ok={ver['hash_chain_ok']}")
