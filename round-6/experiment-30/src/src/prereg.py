#!/usr/bin/env python3
"""STEP 0.2 input hashes + bench verification, STEP 1.4 direction seeds, STEP 6 commit #1 (predictions/s_commit.json).

Commit #1 is written before the first decisive sample: the S-a/S-b/S-c/S-d/F1/F2 rules (src/decide.py), the cells,
N, batch shapes, slots and drop order (src/schedule.py), the banned sets with their counts, the units, the push
directions and push progress, the hook/site code, the input hashes, the power statement and predictions (i)-(vi).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from cfg import (BATCH, D_MODEL, DIR_DIR, DIRECTION_NS, E11, E17, INPUTS, MAX_NEW, PRED_DIR, RESULTS_DIR, ROOT,
                 TASKS, TEMPLATE_IDS, read_json, sha256_file, utc_now, write_json)


def input_hashes() -> dict:
    out = INPUTS / "SHA256SUMS"
    lines = []
    for p in sorted(INPUTS.rglob("*")):
        if p.is_file() and p.name != "SHA256SUMS":
            lines.append(f"{sha256_file(p)}  {p.relative_to(INPUTS)}")
    out.write_text("\n".join(lines) + "\n")
    # bench files against bench/commitment.json
    com = read_json(E11 / "bench" / "commitment.json")
    mism, checked = [], 0
    for tid, rec in com["tasks"].items():
        dirs = [d for d in (E11 / "bench").iterdir() if d.is_dir() and d.name.split("_")[0] == tid]
        if not dirs:
            continue
        for fn, h in rec.get("files", {}).items():
            p = dirs[0] / fn
            if not p.exists():
                continue
            checked += 1
            if sha256_file(p) != h:
                mism.append(f"{dirs[0].name}/{fn}")
    res = {"n_input_files": len(lines), "bench_files_checked": checked, "bench_mismatches": mism,
           "dependency_dataset_note": "art_j3Rm_lr2nzR6 full_data_out.json is read in place (96 MB, not copied)",
           "utc": utc_now()}
    write_json(RESULTS_DIR / "inputs_check.json", res)
    return res


def seeds_and_cosines() -> dict:
    from sites import pn_dir, pn_seed

    seeds = {}
    V = []
    for t in TASKS:
        for w in TEMPLATE_IDS:
            for k in list(range(10)) + list(range(100, 112)) + list(range(300, 316)):
                seeds[f"{t}|{w}|{k}"] = pn_seed(t, w, k)
                if k < 10:
                    V.append(pn_dir(t, w, k))
    V = np.stack(V)
    earlier = {}
    for s in (9002, 9004):
        earlier[f"exp17 rand_{s}"] = np.load(E17 / "directions" / f"rand_{s}.npy").astype(np.float32)[None]
    z = np.load(INPUTS / "exp20" / "directions" / "u_top5.npz")
    earlier["exp20 u_top5 (12 blocks)"] = z["u_top5"].astype(np.float32)
    for f in sorted(DIR_DIR.glob("u_push_*.npz")):
        zz = np.load(f)
        for key in zz.files:
            if zz[key].ndim == 2 and zz[key].shape[1] == D_MODEL:
                earlier[f"{f.name}:{key}"] = zz[key].astype(np.float32)
    # exp20's PN4 directions (iteration-4 namespace) for the same slots
    from cfg import stable_seed

    pn4 = []
    for t in TASKS:
        for w in TEMPLATE_IDS:
            for k in range(10):
                x = np.random.Generator(np.random.PCG64(stable_seed("PN4", t, w, k))).standard_normal(D_MODEL)
                pn4.append(x / np.linalg.norm(x))
    earlier["exp20 PN4 slot directions"] = np.stack(pn4).astype(np.float32)
    cos = {k: float(np.abs(V @ E.T).max()) for k, E in earlier.items()}
    res = {"namespace": DIRECTION_NS, "namespace_is_new": DIRECTION_NS not in ("PN4", "PN5", "i5A", "PN"),
           "recipe": "u = normalise(PCG64(stable_seed('ITER6_S2', task, template, k)).standard_normal(4096))",
           "seeds": seeds, "max_abs_cos_with_earlier": cos, "max_abs_cos_overall": max(cos.values())}
    write_json(DIR_DIR / "seeds.json", res)
    return res


def predictions() -> dict:
    bs = read_json(PRED_DIR / "banned_sets.json")
    pp = read_json(RESULTS_DIR / "push_progress.json")
    return {
        "utc": utc_now(),
        "model": "Qwen/Qwen3-8B@b968826d9c46dd6066d109eabc6255188de91218, thinking off, T 1.0, top-p 1, no top-k",
        "precision": "W16A16 (bf16 weights and activations, HF transformers 4.57.6, sdpa) on one NVIDIA L4 24 GB",
        "cells": "see src/schedule.py cell_rows(): P1 twins N 50; P2 T03/T10 x {S0,S4,S1,S2,S5,S3} x alpha {1,2,4} N 30; "
                 "P3 S1E T03/T10 N 30; P4 T2 x {S0,S4,S5,S1,S2,S3,S1E} x alpha {2,4} N 30; P5 T03 TOP5, T1 twin + "
                 "TOP5 + S0 random control, T10 TOP5 (all-but-one), T03 TOP3, alpha {1,2,4}, N 50; P6 outcome-blind "
                 "extensions (S4 alpha 8; top-up to N 50)",
        "slots": "N 30 = W1-W5 x k 0-5; N 50 = W1-W5 x k 0-9; smoke k >= 100 never analysed; fillers k >= 10",
        "batch_shape": BATCH, "max_new": MAX_NEW,
        "drop_order_time_only": ["P6(b) top-ups", "P6(a) S4 alpha 8", "T03 top-3 variant", "T1 random control a4",
                                 "T10 top-five push", "S1E on T2", "S2 from N 30 to 20"],
        "units": "ban-free n[l,p] = ||h_twin[l,p]|| x r_Q(l); r_Q: exp23 frozen at blocks 12-23, bf16 recomputation "
                 "(exp23 recipe) at 0-11 and 24-35 (units/r_Q_all.json)",
        "banned_sets": bs["sets"], "implemented_counts": {t: bs[t]["counts"] for t in ("T03", "T10")},
        "push_progress_pre_sampling": pp,
        "power_statement": "with 30 paired slots, exact two-sided McNemar against an inert comparator gives p = "
                           "2^(1-b) for b:0; the first Holm step over 6 contrasts needs p < 0.0083, so S-a is "
                           "detectable only if the better task-spec site moves >= 8 of 30 slots (share >= 0.27)",
        "rules": {
            "outcome": "y = passes the hidden tests AND label in the task catalogue AND label != twin default",
            "S_a": "src/decide.py s_a(); per task select among S0/S4 x alpha cells with pass >= 0.8 x twin pass the "
                   "largest y share (ties lower alpha, then S0); comparators S1, S2, S5 at the same alpha; exact "
                   "McNemar on shared slots; Holm over 6; PASS iff both tasks: every diff >= 0.15 and Holm p < 0.05; "
                   "selection-aware p = min(1, 6p) reported, robust iff its Holm also passes; ONE TASK ONLY if only "
                   "T03; DISCONFIRMED iff on both tasks at every gated dose max(S0,S4) - max(S1,S5) < 0.05",
            "S_b": "src/decide.py s_b(); prefill rows of T03/T10/T2 at S0,S4,S5,S1,S1E,S2; TS = S0 or S4; strata = "
                   "deciles of realised displacement at R (block 35, pooled) x task; Mantel-Haenszel OR with RBG CI; "
                   "PASS iff the lower bound > 1; placebo: 200 within-task shuffles of TS must fail",
            "S_c": "src/decide.py s_c(); S3 vs twin on the shared slots per dose, one-sided exact McNemar; PASS iff "
                   "at some dose with pass >= 0.8 x twin the excess >= 0.10 and p < 0.05",
            "S_d": "descriptive: avoidance of the banned set among correct programs (Wilson) vs twin and the paired "
                   "random control (exact McNemar), composition, push progress; edge test only where |S| >= 2 "
                   "(T03 top-3, T1 K=7 / extended); NOT COMPUTABLE BY CONSTRUCTION for T03 top-5 and T10 (|S| = 1)",
            "F1": "label-changing CRN pairs (both valid): share with first token divergence < 32 code tokens after "
                  "the opening fence line >= 0.80; control: label-preserving text-changing pairs",
            "F2": "m = mean over W1-W5 of [mean LP48(default programs) - mean LP48(runner-up programs)]; explains "
                  "the temperature null iff m > 5.70 nats (exp(-m/1.3) < 1/80) on T2, T03, T1; UNRESOLVED if "
                  "|m - 5.70| < 2 x scoring SD; scoring passes run after the decisive sampling (GPU queue order)",
        },
        "predictions": {
            "i": "S4 >= S0 in correct off-default share at their best gated dose, both above S1, S2 and S5 on T03 "
                 "and T10",
            "ii": "at every (site, dose) cell with >= 5 correct off-default programs the modal landing equals the "
                  "base runner-up (T03 quickselect, T10 dfs)",
            "iii": "S3 moves T10 >= 0.10 above the twin at some gated dose",
            "iv": "F1 share >= 0.80",
            "v": "m > 5.70 nats on T2, T03 and T1 (thinking off)",
            "vi": "S-d: T03 top-5 avoidance of B stays below 0.5 at alpha <= 2; the T1 push stays on BFS",
        },
    }


def main() -> None:
    from commit import commit

    stage = sys.argv[1] if len(sys.argv) > 1 else "commit1"
    if stage == "inputs":
        print(json.dumps(input_hashes(), indent=1)[:2000])
        return
    if stage == "seeds":
        r = seeds_and_cosines()
        print(json.dumps({k: v for k, v in r.items() if k != "seeds"}, indent=1))
        return
    if stage == "commit1":
        p = predictions()
        write_json(PRED_DIR / "s_commit.json", p)
        files = [PRED_DIR / "s_commit.json", PRED_DIR / "banned_sets.json", ROOT / "src" / "decide.py",
                 ROOT / "src" / "stats.py", ROOT / "src" / "geometry.py", ROOT / "src" / "schedule.py",
                 ROOT / "src" / "sites.py", ROOT / "src" / "hooks.py", ROOT / "src" / "engine_w16.py",
                 ROOT / "src" / "label_worker.py", ROOT / "src" / "cfg.py", ROOT / "units" / "r_Q_all.json",
                 RESULTS_DIR / "push_progress.json", RESULTS_DIR / "push_directions.json",
                 RESULTS_DIR / "unit_tests_gpu.json", DIR_DIR / "seeds.json", ROOT / "inputs" / "SHA256SUMS"]
        files += sorted(DIR_DIR.glob("u_push_*.npz")) + sorted((ROOT / "units").glob("units_*.npz"))
        e = commit("commit1", [f for f in files if f.exists()], "rules, cells, sets, units, directions, predictions")
        (PRED_DIR / "commit1.done").write_text(e["utc"])
        print(f"commit #1 at {e['utc']} ({len(e['files'])} files), hash {e['hash'][:16]}")
        return
    if stage == "commit2":
        files = [ROOT / "src" / f for f in ("analysis.py", "scoring.py", "geometry.py", "decide.py", "stats.py",
                                            "audit.py", "figures.py", "outputs.py")]
        files.append(ROOT / "audit" / "rederive.py")
        e = commit("commit2", [f for f in files if f.exists()], "final analysis code before it runs on the full data")
        (PRED_DIR / "commit2.done").write_text(e["utc"])
        print(f"commit #2 at {e['utc']}")


if __name__ == "__main__":
    main()
