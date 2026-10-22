#!/usr/bin/env python3
"""Pre-registration: commit #0 (protocol, precision rule, units, screen hash, engine-check criteria) and commit #1
(predictions, decision rules, analysis code hashes, units/u_top5/forced-prompt/screen hashes, slot and seed scheme),
both appended to the commitments.log hash chain before the samples they govern are drawn."""

from __future__ import annotations

import sys

from cfg import (ALPHA_BOUNDARY, ALPHAS_GRID, DIR_DIR, PRED_DIR, RESULTS_DIR, ROOT, TASKS, UNITS_DIR, read_json,
                 sha256_file, utc_now, write_json)
from commit import commit

PROTOCOL = {
    "title": "Where noise must go to change the idea (iteration 4, plan gen_plan_experiment_2_idx3)",
    "model": "Qwen/Qwen3-8B rev b968826d9c46dd6066d109eabc6255188de91218, thinking off, T=1.0, top-p 1, no top-k, "
             "max_new 1024, fence stop",
    "precision_rule": "total VRAM >= 19.5 GiB -> bf16; Ada/Hopper with < 19.5 GiB -> exp17 FP8 W8A8 path; "
                      "Ampere < 19.5 GiB -> FP8 weight-only. Every arm uses one precision.",
    "tasks": list(TASKS),
    "sites": {"S0": "blocks 12-23, task-spec positions S, target alpha*n_S[l,k]",
              "S1": "blocks 12-23, read position R, alpha*n_R[l]",
              "S2": "blocks 12-23, condition span COND_w, alpha*n_C,w[l,p]",
              "S3": "blocks 12-23, generated input positions 1-32 (vs a teacher-forced shadow row), alpha*n_G[l]",
              "S4": "blocks 0-11, S, alpha*n_S[l,k]", "S5": "blocks 24-35, S, alpha*n_S[l,k] (block-35 edit is a no-op)",
              "S1E/S2E": "S1/S2 with the target multiplied by the energy-matching scalar c",
              "TOP5": "blocks 12-23, S, per-block u_top5[l], alpha*n_S[l,k] (T1)"},
    "units": "n = ||h_ban - h_twin|| per block and position, mean over W1-W5 (S, R) or per template (COND); "
             "per-position ban units are the primary dose convention",
    "direction": "u(t,w,k) = normalise(PCG64(stable_seed('PN4',t,w,k)).standard_normal(4096)) float32, shared by every "
                 "site, dose and boundary arm of slot (t,w,k)",
    "uniforms": "exp17 u_stream(task, template, k) (stable_seed(task, template, k)), shared by every arm",
    "alphas": list(ALPHAS_GRID) + [ALPHA_BOUNDARY],
    "batch": "20 rows of one (task, template), fixed shape; finished rows fed <|im_end|>",
    "engine_check_criteria": "REPRODUCED if JS(our composition, screen composition) <= the 95th percentile of a "
                             "template-resampling null (JS between two template-stratified bootstrap resamples of the "
                             "pooled programs at matched sizes) AND |off-default share difference| <= 0.15; run on "
                             "T03 rand_9002 alpha 1 and T2 rand_9004 alpha 1 (N=50 each, k 0-9) under the screen's "
                             "uniforms and units; failure is reported as precision/engine sensitivity, the run proceeds",
}


def commit0() -> None:
    hw = read_json(RESULTS_DIR / "hardware.json")
    proto = dict(PROTOCOL, precision_chosen=hw["precision"], hardware=hw,
                 screen_sha256=(RESULTS_DIR / "screen.sha256").read_text().strip(),
                 units_sha256=read_json(UNITS_DIR / "units_sha256.json"), utc=utc_now())
    p = PRED_DIR / "protocol_commit0.json"
    write_json(p, proto)
    files = [p, RESULTS_DIR / "screen.json", UNITS_DIR / "units_sha256.json"] + sorted(UNITS_DIR.glob("*.npz")) + \
        [ROOT / "src" / f for f in ("cfg.py", "engine.py", "hooks.py", "gpu_main.py", "schedule.py", "prompts.py",
                                    "screen.py")]
    commit(files, "commit0")
    (PRED_DIR / "commit0.done").write_text(utc_now() + "\n")


def commit1(code_files: list[str]) -> None:
    files = [PRED_DIR / "predictions.json", PRED_DIR / "forced_prompts_T1.json", DIR_DIR / "u_top5.npz",
             DIR_DIR / "plan_geometry_T1.npz"] + [ROOT / "src" / f for f in code_files]
    commit(files, "commit1")
    (PRED_DIR / "commit1.done").write_text(utc_now() + "\n")


if __name__ == "__main__":
    if sys.argv[1] == "0":
        commit0()
    else:
        commit1(sys.argv[2:])
