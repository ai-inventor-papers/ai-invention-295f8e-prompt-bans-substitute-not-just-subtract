#!/usr/bin/env python3
"""COMMIT #1 (before the first S1/S2 sample) and COMMIT #2 (before the first S3 sample): write the predictions files
and append them, with the code they depend on, to the sha256 chain (commitments.log).

usage: .venv/bin/python src/make_commits.py commit1 | commit2
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import k_cfg as K  # noqa: E402
from k_cfg import PRED, ROOT, read_jsonl, sha256_file, utc_now, write_json  # noqa: E402
import commit_k  # noqa: E402

DESIGN_TABLE = {
    "D1": "U_abs x S4 (exp29 engine-d design: positive anchor)",
    "D2": "U_abs x S5",
    "D3": "U_bf x S4",
    "D4": "U_bf x S5 (exp27 design: null anchor)",
    "D5": "U_bf* x S4, U_bf*[l,:] = U_bf[l,:] * ||U_abs[l,:]|| / ||U_bf[l,:]|| (extension)",
    "PTOP": "U_abs restricted to its top-quartile cells, rescaled to ||U_abs||_F; other cells not edited (S4 seeds)",
    "PREST": "U_abs restricted to the other three quartiles, rescaled to ||U_abs||_F; top cells not edited (S4)",
    "PSHUF": "U_abs with spec positions permuted (one permutation for all blocks, seed stable_seed(task,'SHUF'))",
}


def commit1() -> None:
    unit_files = {t: str(p.relative_to(ROOT)) for t, p in {
        "T10": K.V22 / "inputs/exp13/results/tensors/norms_T10.npz", "T03": K.V22 / "inputs/exp13/results/tensors/norms_T03.npz",
        "T05": K.V22 / "inputs/exp13/results/tensors/norms_T05.npz", "T1": K.V22 / "inputs/exp17/directions/norms_T1.npy",
        "T2": K.V22 / "inputs/exp17/directions/norms_T2.npy"}.items()}
    obj = {
        "commit": 1, "utc": utc_now(),
        "design_table": DESIGN_TABLE,
        "unit_files_sha256": {t: {"path": p, "sha256": sha256_file(ROOT / p)} for t, p in unit_files.items()},
        "r_Q_file": {"path": "inputs/exp23/results/qwen_ratio.json",
                     "sha256": sha256_file(ROOT / "inputs/exp23/results/qwen_ratio.json")},
        "seed_functions": {
            "stable_seed": "int(sha256('|'.join(str(x) for x in parts).encode()).hexdigest(), 16) % 2**63",
            "S4": "u = normalise(PCG64(stable_seed(task, 'PN_a1' | 'PN_a2', w, k)).standard_normal(4096)) (float32)",
            "S5": "u = normalise(PCG64(stable_seed(task, 'PN5', w, k)).standard_normal(4096)) (same u at alpha 1, 2)",
            "u_stream": "PCG64(stable_seed(task, w, k)).random(max_new); one stream per slot shared by every arm"},
        "edit": "TARGET at blocks 12-23 x task-spec positions [p1, spec_end), prefill only: h <- h + (alpha n[l,p] - "
                "(h - h_twin).u) u; masked profile cells not edited",
        "alphas": [1.0, 2.0],
        "cells": {"T10": "D1-D4 x alpha {1,2} x N 50 (W1-W5 x k 0-9)",
                  "T2": "D1-D4 x alpha 2 x N 100 (k 0-19); alpha 1 x N 50 (k 0-9)",
                  "D5": "T10 alpha 2 N 50; T2 alpha 2 N 100", "S2": "T10, T2 alpha 2 N 50: PTOP, PREST, PSHUF",
                  "TWIN": "N 50 on T10, T2 (+k 10-19), T03, T05, T1"},
        "decoding": "T 1.0, top-p 1, no top-k, max_new 1024 (bench) / 1536 (T1, T2), fence stop, exact inverse-CDF "
                    "CRN; shared-prefix path for every row; constant B (memory probe); designs interleaved by slot",
        "outcomes": {"Y": "passed AND label in catalogue minus default (primary)",
                     "Y_any": "passed AND label not in {default, invalid, disputed, unknown}",
                     "A": "valid AND label not in {default, invalid, disputed, unknown}, over all N"},
        "anchor_rules": {
            "A1": "T10 D1 alpha 2 attempted off-default (A) has two-sided Fisher p >= 0.05 vs exp29 engine-d 25/50 "
                  "AND count >= 15",
            "A2": "T10 D4 alpha 2 correct off-default (Y_any) has two-sided Fisher p >= 0.05 vs exp27's 1/50",
            "A3": "reported only: T2 D1 alpha 2 vs exp29 22/50 attempts (pass 0.62; 9/50 correct); per-slot label "
                  "agreement of D1 with exp29 raw_d on k 0-9",
            "on_failure": "DIAG -> results/anchor_discrepancy.json; if A2 fails run T10 D4 alpha 2 through exp27's "
                          "left-padded path (N 50); finish S1; S1 verdict 'ANCHOR_FAILED: not interpreted'; D* := D1"},
        "decision_rules": {
            "contrasts": "RD_unit = ((D1-D3)+(D2-D4))/2; RD_seed = ((D1-D2)+(D3-D4))/2; INT = (D1-D2)-(D3-D4); "
                         "slot-cluster bootstrap 95% CI (2,000); exact sign-flip p; Holm over {unit, seed, INT} on "
                         "T10 alpha 2 (outcome Y)",
            "UNIT": "RD_unit CI > 0 (Holm p < 0.05) and RD_seed CI contains 0",
            "SEEDS": "RD_seed CI excludes 0 (Holm p < 0.05) and RD_unit CI contains 0",
            "BOTH": "both exclude 0", "NEITHER-ALL-MOVE": "no contrast and every design share >= 0.2",
            "NEITHER-NONE-MOVE": "no contrast and every design share < 0.1",
            "D5_split": "RD(D1 - D5) = within-block profile at matched per-block energy; RD(D5 - D3) = per-block "
                        "energy at the ban-free shape",
            "S2": "exact McNemar on per-slot Y; Holm over 3 per task (T10 primary): PTOP vs PREST, D1 vs PSHUF, D1 vs "
                  "PTOP; 'pushes act where bans write' iff PTOP > PREST (p < 0.05) and D1 > PSHUF (p < 0.05) on T10",
            "D_star": "argmax over D1-D4 of pooled (T10 + T2) alpha-2 Y share among designs with T10 pass >= 0.8 x "
                      "twin pass; ties within 0.10 go to D1"},
        "predictions": {
            "P-S1a": "unit main effect RD (U_abs - U_bf, averaged over seeds) on T10 alpha 2 > 0 with 95% CI "
                     "excluding 0 (point +0.35, range 0.20-0.50)",
            "P-S1b": "seed main effect within [-0.10, +0.10], CI includes 0",
            "P-S1c": "interaction CI includes 0",
            "P-S1d": "T2 alpha 2 unit RD on correct programs +0.10 (CI may include 0)",
            "P-S1e": "U_bf* intermediate (T10 alpha 2 share 0.05-0.35)",
            "P-S2a": "P_top > P_rest by >= 0.10", "P-S2b": "D1 > P_shuf by >= 0.10"},
        "code_sha256": {p: sha256_file(ROOT / p) for p in ("src/analysis_k.py", "src/gen_k.py", "src/k_units.py",
                                                            "src/k_cfg.py", "src/label_k.py")},
        "rows_before_commit": len(read_jsonl(K.RAW)),
        "pushed_rows_before_commit": sum(1 for r in read_jsonl(K.RAW) if r["arm"] != "TWIN"),
    }
    write_json(PRED / "commit1.json", obj)
    for p in ("src/analysis_k.py", "src/gen_k.py", "src/k_units.py", "src/k_cfg.py", "src/label_k.py",
              "predictions/commit1.json"):
        commit_k.add(ROOT / p, "COMMIT #1")
    print("COMMIT #1 written", obj["pushed_rows_before_commit"], "pushed rows before")


def commit2() -> None:
    import analysis_k as A

    rows = A.load_joined()
    ds = A.d_star(rows)
    anc = A.anchors(rows)
    if not anc.get("both_pass", False):
        ds["anchor_override"] = "anchors failed -> D* := D1 (committed rule)"
        ds["D_star_rule_choice"] = ds["D_star"]
        ds["D_star"] = "D1"
    obj = {
        "commit": 2, "utc": utc_now(), "D_star": ds["D_star"], "d_star_detail": ds, "anchors": anc,
        "s3_predictions_exp19_prior": {
            "H5_PNstar": {"T03": [2.2, 2.7, "WIN vs BINT"], "T10": [2.0, 2.6, "TIE"], "T1": [1.2, 1.5, "TIE"],
                          "T2": [1.1, 1.4, "LOSS"], "T05": [1.1, 1.3, "LOSS"]},
            "matches_or_beats_BINT": "3 of 5", "H5_ge_2": "2 of 5 (T03, T10)"},
        "s3_rules": {
            "classes": "PN* = {TWIN, PN*_a1, PN*_a2}; BINT = {TWIN, BINT}; EAP = {TWIN, EAP}; IFG = {TWIN, IFG_hot}; "
                       "TEMP = {TWIN, T1.3}; TOPK10 = {TWIN, TOPK10}",
            "hull": "exp27 hull_full.hull_prices_full: correct-only Hill-1 rarefied at depth 25, two-stage CRN "
                    "multinomial draws (n_draws 1,000), simplex grid 0.01 (k <= 3) + local refinement -> H5, P15, P20; "
                    "2,000 slot bootstraps with best-mixture selection inside each replicate",
            "per_task": "WIN if P_boot(H5_PN* > H5_BINT) >= 0.8, LOSS if <= 0.2, else TIE; 'matches or beats' = WIN/TIE",
            "replay": "D_t = H5_PN* - max(H5 of BINT, EAP, IFG); D_bar with bootstrap CI; count PN* >= best text",
            "knob_check": "reuse exp27's N 50 rows (relabelled) iff per-slot label agreement >= 0.95 (10/10) on k 0-1",
            "retag": "iteration-5 plan-sampler verdict and movability verdict tagged 'ban-free unit and iteration-5 "
                     "seeds'; new verdicts at D*: movable := alpha-2 correct off-default share - twin >= 0.20 at "
                     "pass >= 0.8 x twin"},
        "code_sha256": {p: sha256_file(ROOT / p) for p in ("src/s3_prices.py", "src/knobs_k.py")
                        if (ROOT / p).exists()},
        "s3_rows_before_commit": sum(1 for r in read_jsonl(K.RAW) if str(r.get("stage", "")).startswith("S3")),
    }
    write_json(PRED / "commit2.json", obj)
    for p in ("src/s3_prices.py", "src/knobs_k.py", "predictions/commit2.json"):
        if (ROOT / p).exists():
            commit_k.add(ROOT / p, "COMMIT #2")
    print("COMMIT #2 written: D* =", obj["D_star"])


if __name__ == "__main__":
    {"commit1": commit1, "commit2": commit2}[sys.argv[1]]()
