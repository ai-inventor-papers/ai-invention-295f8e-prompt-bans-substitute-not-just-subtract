#!/usr/bin/env python3
"""Bookkeeping: deviations, timing summary, commit-order audit (every decisive row drawn after commit #1),
commitments-chain verification. Writes results/deviations.json, results/timing_summary.json,
results/commit_order_audit.json."""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from cfg import DATA_DIR, RESULTS_DIR, read_json, read_jsonl, utc_now, write_json
from commit import LOG, verify

DEVIATIONS = [
    {"id": "D1-precision", "what": "FP8 W8A8 (exp17 engine) instead of the bf16 the plan expected on an RTX A4500",
     "why": "the machine has a 16 GB RTX 2000 Ada (compute 8.9); the frozen precision rule (commit #0) maps Ada < 19.5 "
            "GiB to the exp17 FP8 W8A8 path; every arm uses it", "cost": "C1-site statements are 'in FP8 W8A8'; the "
            "engine check compares like with like (FP8 vs FP8) and reproduced the screen byte for byte"},
    {"id": "D2-batch", "what": "fixed batch B = 20 rows for every task and max_new 1024 for every task (plan: B 16/12 "
            "and 1,536 for T1/T2 on a 20 GiB card)", "why": "exp17's U1b-verified shape on this GPU; keeps the screen's "
            "uniforms and shape for the engine check; U6 peak 13.2 GiB", "cost": "rows longer than 1,024 tokens are "
            "truncated: 0 of 466 twin rows, 4 of 2,760 rows at alpha <= 2, 47 of 1,150 at alpha 4, 0 at alpha 8 "
            "(finish_reason per cell in results/cells.json)"},
    {"id": "D3-cond-span", "what": "COND includes the token where the tokenizer merges the sentence's final '.' with "
            "the '\\n\\n' separator", "why": "the separator cannot be excluded without also excluding the period",
     "cost": "none for the S2 target (the ban-twin displacement there is measured, not assumed)"},
    {"id": "D4-U4", "what": "U4 shadow fidelity vs an independent batch-1 teacher-forced forward fails the 1e-2 "
            "threshold", "why": "see results/u4_diagnostic.json: FP8 decode-path states differ from a teacher-forced "
            "prefill of the same tokens even with no edit; the shadow is the exact clean reference WITHIN the decode "
            "path (U2: S3 at alpha 0 reproduces the twin byte for byte; U3: along-u displacement vs the shadow = "
            "target within 0.01%)", "cost": "S3's reference state is 'clean decode-path state', not 'teacher-forced "
            "state'; the contrast with the hooked row is exact"},
    {"id": "D5-first-token-kl", "what": "first-token KL is degenerate (the first generated token is always the code "
            "fence, p ~ 1 in every arm)", "why": "the prompt asks for one ```python block", "cost": "the transmission "
            "analysis rests on the realised displacement at R (block 35); the KL model is reported as uninformative; "
            "S3 keeps its step-wise KL (steps 1-32)"},
    {"id": "D6-analysis-commit", "what": "commit #1 (before the first decisive sample) holds the predictions, every "
            "decision rule and threshold, and the hull + C1 decision code (hull.py); analysis.py, outputs.py, "
            "figures.py, audit.py, label_k7.py and audit/rederive.py were written while sampling ran and committed in "
            "#2 before being run on the full data", "why": "time budget; the GPU would otherwise have idled",
     "cost": "rules for everything outside hull.py are fixed by predictions.json text, not by code hashes"},
    {"id": "D7-direction-seed", "what": "protocol v4's hash(task, arm, slot) is read with arm = the PN family "
            "('PN4'), so one direction per slot is shared by every site, dose and boundary arm", "why": "plan STEP 3",
     "cost": "none (stated)"},
    {"id": "D8-top5-control", "what": "the 'norm-matched random direction' control of the TOP5 push is a distribution "
            "of fresh per-slot directions at the same per-position norm (S0 rows, k 0-9), not one draw; u_top5 is per "
            "block while PN shares one u across blocks", "why": "plan P6", "cost": "none (stated)"},
    {"id": "D9-judge-ids", "what": "novelty-audit judges are exp18's recorded ids (google/gemini-2.5-flash-lite, "
            "openai/gpt-4.1-mini); tie-break deepseek/deepseek-chat-v3.1 (exp9's tie-break model)", "why": "the plan "
            "names 'exp18's ids'; its parenthetical 'gemini-2.5-flash' differs from what exp18 actually used",
     "cost": "none"},
    {"id": "D10-exp13-units", "what": "exp13's FP8 units differ from this artifact's by median ratio 1.12-1.32 "
            "(exp17's: 0.99-1.00)", "why": "exp13 built its own twins/padding", "cost": "logged as unit drift; "
            "exp17 (same prompts) agrees to 0.2%"},
    {"id": "D11-screen-twins", "what": "exp13 rand1-3 rows are compared with exp13's hf_twin (same HF engine) in "
            "the screen file", "why": "engine-matched baseline", "cost": "none"},
    {"id": "D12-judge-cache", "what": "labelling judge caches started empty (exp17's caches were not copied)",
     "why": "oversight", "cost": "a few cents of extra judge spend"},
    {"id": "D13-invalid-harmonised", "what": "'invalid' = no code block, syntax error or no solve() for EVERY task "
            "(the bench labeller's rule; the exp8 path labeller otherwise labels non-programs such as "
            "'[your_answer]')", "why": "the plan defines 'invalid' as its own column; at alpha 8 the model often "
            "writes placeholders. Introduced AFTER commit #2, after inspecting alpha-8 outputs, and applied to every "
            "arm; committed in #3 with the final analysis code (units summary, argmax robustness to a missing site, "
            "an explicit name for the failure-mode case the frozen rule leaves uncovered)", "cost": "attempt-level "
            "shares only; correct-only results (Hill, H5, C1-site, C3d) are unaffected because such programs never "
            "pass"},
    {"id": "D14-k7-judge-cap", "what": "exp9 K=7 labeller judge cap USD 0.10 (exp9 default 0.70)", "why": "share of "
            "the plan's labelling-judge budget", "cost": "none: K=7 judge spend was USD 0.066 and no row fell back "
            "(labeller_source: agree 763, judge 181, no_code 22)"},
    {"id": "D15-budget-gate", "what": "the stage-100 projection used by the budget gate (0.37 h; "
            "results/timing_projection.json) was computed on the first five batches, which were fast T05 batches",
     "why": "alpha-4 S2/S3/S4 and S1E batches later ran to the full 1,024 tokens (~67 s each); the realised decisive "
            "sampling took 1.69 h wall time (1.74 GPU-hours of batch time including tests, engine check and smoke), "
            "still inside the plan's 2.0 h gate, so no cell was dropped", "cost": "none; the gate's projection rule "
            "should use per-arm-type timings (logged for the next run)"},
    {"id": "D16-overlap-null", "what": "the STEP 11.10 overlap check's template-resampling null was added after "
            "commit #3 (the first version reported JS without a null)", "why": "the plan specifies the null; exp19's "
            "Step-1 rows turned out to exist", "cost": "none: the comparison is descriptive and committed in #4"},
]


def timing() -> dict:
    rows = read_jsonl(RESULTS_DIR / "timing_batches.jsonl")
    by_task = defaultdict(list)
    by_alpha = defaultdict(list)
    for r in rows:
        if r["batch_id"].startswith("B"):
            by_task[r["task"]].append(r["seconds"] / 20)
            by_alpha[str(r.get("max_alpha"))].append(r["seconds"] / 20)
    tot = sum(r["seconds"] for r in rows)
    return {"n_batches": len(rows), "gpu_seconds_total": tot, "gpu_hours_total": tot / 3600,
            "seconds_per_row_by_task": {t: float(np.mean(v)) for t, v in by_task.items()},
            "seconds_per_row_by_batch_max_alpha": {a: float(np.mean(v)) for a, v in by_alpha.items()},
            "projection": read_json(RESULTS_DIR / "timing_projection.json")
            if (RESULTS_DIR / "timing_projection.json").exists() else None}


def commit_order() -> dict:
    c1 = None
    for line in LOG.read_text().splitlines():
        if line.strip() and line.split()[4] == "commit1":
            c1 = line.split()[0]
            break
    raw = read_jsonl(DATA_DIR / "samples_raw.jsonl")
    dec = [r for r in raw if not r["arm"].startswith("SMOKE_") and not r["arm"].startswith("ENG") and
           not r["batch_id"].endswith(":P0") and
           not (r["arm"] == "TWIN" and r["task"] in ("T03", "T2") and r["batch_id"].endswith("P1") and
                r["utc"] < (c1 or ""))]
    before = [r for r in dec if c1 and r["utc"] < c1]
    eng = [r for r in raw if r["arm"].startswith("ENG")]
    return {"commit1_utc": c1, "n_decisive_rows": len(dec), "n_decisive_before_commit1": len(before),
            "engine_check_rows": len(eng), "engine_twin_rows_before_commit1":
                sum(1 for r in raw if r["arm"] == "TWIN" and c1 and r["utc"] < c1),
            "note": "engine-check batches (ENG + the T03/T2 twin rows k 0-9 in the same batches) ran after commit #0 "
                    "and before commit #1, as the plan orders (STEP 7 before STEP 8); smoke batches (':P0', slots "
                    "k >= 100 plus their TWIN_X filler) are never analysed"}


def merge_samples() -> dict:
    """data/samples.jsonl: the protocol's per-sample schema (raw row) plus label, labeller_source, passed (and the
    exp9 K=7 / extended labels for T1 rows); 'analysed' is False for smoke slots and TWIN_X filler rows."""
    from cfg import write_jsonl

    labs = {r["key"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl")}
    k7 = {r["key"]: r for r in read_jsonl(DATA_DIR / "labels_k7.jsonl")}
    logs = {r["key"]: r for r in read_jsonl(DATA_DIR / "row_logs.jsonl")}
    out = []
    for r in read_jsonl(DATA_DIR / "samples_raw.jsonl"):
        key = f"{r['task']}|{r['template']}|{r['arm']}|{r['k']}"
        lb = labs.get(key, {})
        lg = logs.get(key, {})
        rec = dict(r)
        rec.update({"key": key, "analysed": not (r["arm"].startswith("SMOKE_") or r["arm"] == "TWIN_X"),
                    "label": lb.get("label"), "labeller_source": lb.get("labeller_source"),
                    "passed": lb.get("passed"), "valid": lb.get("valid"), "runtime_label": lb.get("runtime_label"),
                    "ast_label": lb.get("ast_label"), "judge_label": lb.get("judge_label"),
                    "fallback_label": lb.get("fallback_label"), "code_sha256": lb.get("code_sha256"),
                    "code": lb.get("code"), "realised_disp_R": lg.get("realised_disp_R"),
                    "along_u_site": lg.get("along_u"), "total_disp_site": lg.get("total_disp_site"),
                    "s3": lg.get("s3")})
        if key in k7:
            rec["label_k7"] = k7[key]["label_k7"]
            rec["label_ext"] = k7[key]["label_ext"]
        out.append(rec)
    write_jsonl(DATA_DIR / "samples.jsonl", out)
    return {"n": len(out), "n_analysed": sum(r["analysed"] for r in out), "n_unlabelled": sum(r["label"] is None
                                                                                             for r in out)}


def main() -> None:
    print(merge_samples())
    write_json(RESULTS_DIR / "deviations.json", {"utc": utc_now(), "deviations": DEVIATIONS})
    write_json(RESULTS_DIR / "timing_summary.json", timing())
    co = commit_order()
    co["chain"] = verify()
    write_json(RESULTS_DIR / "commit_order_audit.json", co)
    print(co)


if __name__ == "__main__":
    main()
