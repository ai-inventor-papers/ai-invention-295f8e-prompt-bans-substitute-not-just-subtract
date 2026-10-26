#!/usr/bin/env python3
"""results/deviations.json, results/costs.json, results/timing_summary.json (bookkeeping for the README and
method_out.json)."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c6  # noqa: E402,F401
from c6 import RESULTS, V22, read_json, read_jsonl, utc_now, write_json  # noqa: E402


def costs() -> dict:
    out = {"cap_usd_artifact": 0.5, "utc": utc_now()}
    p = V22 / "results" / "openrouter_cost_paths.json"
    path = read_json(p)["total_usd"] if p.exists() else 0.0
    bench = sum(r.get("cost", 0.0) or 0.0 for r in read_jsonl(V22 / "logs" / "openrouter_spend.jsonl"))
    out.update({"path_judge_usd (openai/gpt-4.1-mini)": path, "bench_judge_usd (google/gemini-2.5-flash-lite)": bench,
                "total_usd": path + bench, "n_bench_calls": len(read_jsonl(V22 / "logs" / "openrouter_spend.jsonl"))})
    return out


def timing() -> dict:
    agg = defaultdict(lambda: {"batches": 0, "programs": 0, "seconds": 0.0, "steps": 0})
    for r in read_jsonl(RESULTS / "timing.jsonl"):
        a = agg[f"{r['engine']}|{r['task']}|{r['stage']}"]
        a["batches"] += 1
        a["programs"] += r["B"]
        a["seconds"] += r["seconds"]
        a["steps"] += r["steps"]
        a["B"] = r["B"]
    for v in agg.values():
        v["s_per_program"] = v["seconds"] / max(v["programs"], 1)
        v["s_per_step"] = v["seconds"] / max(v["steps"], 1)
    return {"utc": utc_now(), "cells": dict(agg),
            "total_gpu_generation_minutes": sum(v["seconds"] for v in agg.values()) / 60}


DEVIATIONS = [
    {"id": "D-GPU", "what": "The pod is an RTX 2000 Ada (sm_89, 16 GB), not the planned 20 GB Ampere A4500.",
     "consequence": "Engine a runs on the native torch._scaled_mm kernel (iteration-4 numerics; the plan's sm_89+ "
                    "fallback). The exact-math emulation is used only in U1 (validation)."},
    {"id": "D-B", "what": "Weight set Q (a, b) runs at B = 20 (exp22's batch shape); weight set B (c, d) at the largest "
                          "B that fits next to 14.1 GiB of bf16 weights (memory probe; recorded in gpu_b_log.json).",
     "consequence": "Not one B for all engines. Mitigation: U3 shows a row's logits are bitwise identical across "
                    "batch sizes >= 2-3 in every engine (only B = 1 differs), and the aB control re-runs engine a at "
                    "weight set B's batch size on the REPRO cells."},
    {"id": "D-KVCAP", "what": "Weight set B uses a copy of the vendored sampler whose KV buffer holds `cap` generated "
                              "tokens (448) and builds each prefill's KV directly into the batch buffer.",
     "consequence": "Bitwise identical for every row that finishes within cap tokens (U6); rows that do not are moved "
                    "to a full-length buffer and continue in a smaller batch (flagged overflow_at_step)."},
    {"id": "D-REUSE-A", "what": "Engine a was re-run only on the REPRO cells (twins + 9101-9110 alpha 2) and the "
                                "exp19 PN W1 slots; both were byte-identical to iteration 4 (400/400 and 40/40), so "
                                "exp22's (relabelled) rows serve as engine a on all other cells and exp19's PN rows "
                                "as engine-a PN (rule fixed in COMMIT #0).",
     "consequence": "Engine a's alpha-1 cells and confirmations come from iteration 4 itself."},
    {"id": "D-ALPHA1", "what": "S5 (alpha 1) not run for b and c (committed drop order); E_rule therefore uses alpha 2 "
                               "for all four engines.", "consequence": "alpha-1 escape fractions are descriptive (a: "
                                                                       "exp22; d: only if the follow-up ran)."},
    {"id": "D-MIMIC", "what": "S6 (Gaussian mimic) not run.", "consequence": "No 'generic noise suffices' reading."},
    {"id": "D-T03", "what": "S7 (T03, descriptive) not run.", "consequence": "Claims are scoped to T10 and T2."},
    {"id": "D-ANALYSIS-LATE", "what": "src/analysis.py and src/rederive.py were committed by AMENDMENT #1, after "
                                      "COMMIT #0 and after the first engine-d rows existed (no b or c row existed).",
     "consequence": "The binding decision rules are COMMIT #0's text; the code implements them verbatim."},
    {"id": "D-STAGE-ORDER", "what": "Weight set B ran d screen, d confirmations, c screen, PN (d, c), diagnostics, "
                                    "then c confirmations; PN before alpha 1 (as planned).", "consequence": "none"},
    {"id": "D-FIDELITY-ORDER", "what": "FIDELITY and KL (teacher-forced) ran inside each weight-set process after "
                                       "the decisive stages had started.",
     "consequence": "They are diagnostics only: engine a was validated by byte identity instead (stronger)."},
    {"id": "D-NOVELTY", "what": "The two-judge novelty audit of correct 'other' programs was not run.",
     "consequence": "Counts of correct 'other' programs per engine are reported instead."},
    {"id": "D-W8A16-IMPL", "what": "The fused Triton W8A16 kernel could not be built (no C compiler in the container: "
                                   "'Failed to find C compiler'); by the committed rule engine b uses the reference "
                                   "implementation torch.mm(x, codes_bf16^T, out_dtype=float32) * s_w with a per-call "
                                   "e4m3->bf16 cast (results/w8a16_impl.json).",
     "consequence": "Exactly the planned math; about 2.5x slower per decode step than the native FP8 kernel."},
    {"id": "D-AB-DROPPED", "what": "The B-sensitivity control (engine a at weight set B's B = 7) was dropped by the "
                                   "second weight-set-Q process's deadline.",
     "consequence": "B-invariance rests on U3 (bitwise identical logits across B >= 3 in bf16/W16A8 and B >= 10 in "
                    "FP8/W8A16) and on engine d reproducing iteration 5's bf16 twin composition exactly."},
    {"id": "D-B2-SKIPPED", "what": "The engine-d alpha-1 follow-up (src/gpu_b2.py) was skipped (data/SKIP_B2); the "
                                   "remaining GPU time went to engine b's confirmations (src/gpu_q3.py, same engine "
                                   "and implementation, resumable by done slots).",
     "consequence": "The half-dose point comes from bf16 PN at alpha 1 (7/50 on T10 vs FP8 6/50) instead of fixed "
                    "directions."},
]


def main() -> None:
    write_json(RESULTS / "costs.json", costs())
    write_json(RESULTS / "timing_summary.json", timing())
    write_json(RESULTS / "deviations.json", {"utc": utc_now(), "deviations": DEVIATIONS})
    print(json.dumps(costs()), timing()["total_gpu_generation_minutes"])


if __name__ == "__main__":
    main()
