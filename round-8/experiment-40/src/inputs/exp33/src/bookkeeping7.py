#!/usr/bin/env python3
"""Bookkeeping: results/deviations.json, results/costs.json, results/timing_summary.json, results/inputs_available.json,
inputs/SHA256SUMS (of the copied input files), results/tests_cpu.json, and the commitment-chain verification."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import INPUTS, ROOT, read_json, read_jsonl, utc_now, write_json
from cfg7 import results7

DEVIATIONS = [
    {"id": "D-gpu", "text": "One RTX 4090 (24 GB) instead of the planned RTX A4500 (20 GB): the whole bf16 model (incl. the "
                            "input embedding) is on the GPU; fixed batch 16 per task in every arm (exp30 used 8/10)."},
    {"id": "D-cache", "text": "HF_HOME was not set to ./hf_cache (plan STEP 0): the run's shared cache variables were kept, "
                              "as the run instructions require; the model weights are not in this folder."},
    {"id": "D-cap", "text": "Generation caps are exp30's 384 (bench) / 512 (T2) tokens, not 1,024/1,536: engine-check "
                            "comparability with exp30 and the time budget; truncations are counted per cell "
                            "(results/cells.json, n_length)."},
    {"id": "D-U3U4", "text": "U3 (packed vs separate forwards) and U4 (cached vs full forward) miss the strict tolerances: "
                             "max 0.27 nats per 48-token program (mean 0.10) and 0.16 nats contrast; both are bf16 "
                             "kernel-shape effects (batch size / mask path), so every compared condition of a pair is "
                             "scored in ONE batched forward (none, full-state and edits together)."},
    {"id": "D-commit0", "text": "Commit #0 holds the design, thresholds, cells, seeds and predictions; the analysis code was "
                                "frozen in amendment2_analysis_code before any held-out generation was scored."},
    {"id": "D-targets", "text": "Distinct 48-token openings are few (the model repeats openings), so the default pool was "
                                "extended to TRAIN-family padding-twin samples (commit1_<task>_v2 amendment); validation "
                                "target sets are filled from training programs where < 8 distinct programs exist; T10 "
                                "dfs has 3 distinct programs, T03 heapify_pop 1 and full_sort 2 (T03 short-program "
                                "fallback: >= 16 tokens)."},
    {"id": "D-site", "text": "The declared band fallback fired on both core tasks (full-state at L* transferred -0.03 on T2 "
                             "and 0.00 on T10 in generation vs 0.33 / 0.57 for band 12-23), so every map acts at the "
                             "spec positions of blocks 12-23 (one R shared over the band)."},
    {"id": "D-objective", "text": "AMENDMENT 1 (committed before any held-out generation): the committed contrastive "
                                  "objective C = LME_Y - LME_D diverged on validation (best states: T2 main 1,873 nats, permuted 880 "
                                  "nats; T10 main 3,868 nats vs full-state ceilings of 5-36 nats): it rises through "
                                  "breakage of the default's likelihood, as the plan warned. A second map per task was "
                                  "fitted with the bounded standard DAS objective LME_Y (likelihood of the source's own "
                                  "programs), same class, pairs, seeds and budget, with its permuted-label and "
                                  "read-position twins. The full held-out cell set uses this map (MAIN_LY); the committed "
                                  "map (MAIN) is reported from a 10-slot generation pilot (results/committed_map_pilot.json)."},
    {"id": "D-light", "text": "T10's committed-objective fit is MAIN only (no permuted / read-position fits with the "
                              "degenerate objective); T03 uses only the amended objective (MAIN_LY + PERM_LY)."},
    {"id": "D-pca", "text": "PCA-16 uses per-position-centred spec states of the TRAIN forced prompts (15 spec-mean points give "
                            "rank <= 14); DIM-1, the natural-state analyses and M use the band's middle block (18)."},
    {"id": "D-tfsets", "text": "Held-out teacher-forced evaluation scores held-out PROMPT pairs with the training target "
                               "program sets (no separate held-out target sets)."},
    {"id": "D-pilot", "text": "Decisive MAIN_LY cells ran straight to N = 30 (no separate 10-slot pass); the profile "
                              "confirmation cells served as the machinery pilot."},
    {"id": "D-base-pad", "text": "Forced-source transfers use the pooled padding-twin BASE cell of the plan (slot s: family "
                                 "3 + s mod 2, kept Y (s div 2) mod |Y|), so the forced arms' base prompt can differ in "
                                 "padding length from the arm's own padding twin on a slot."},
    {"id": "D-drop", "text": "Drop order applied: plan resampling (1) and the T1 extension (2: T1 DAS and the literal "
                             "top-five placement on T1) were not run; M's top-k placement uses T2's leave-one-survivor "
                             "bans only."},
    {"id": "D-seed", "text": "One init seed per fit (plan departure 2); no second T2 seed."},
    {"id": "D-randinit", "text": "The committed random-init control (contrastive objective, results/randinit_T2.json) was "
                                 "compared with the trained contrastive fit, which had diverged (ratio 0.013 is not "
                                 "meaningful). A matched control (results/randinit_ly_T2.json: the random network fitted "
                                 "with the amended LME_Y objective, compared with MAIN_LY in the same units) decides P1's "
                                 "T2 random-init clause; the analysis code change is an addition made after generation."},
    {"id": "D-ext", "text": "Extensions beyond the plan: behaviour of the prompts M places (MGEN cells, N = 30 each; the "
                            "LF2 long-form instruction with cap 1,536) and a second DAS init seed on T2 (DASLY2 arms)."},
    {"id": "D-C-k", "text": "C is scored at k = 16 when P1's k (2 on T2, 16 on T10) has no forced-source DAS arm (forced "
                            "sources were generated at k in {1, 4, 16})."},
]


def sha_tree(d: Path) -> list[str]:
    out = []
    for p in sorted(d.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            out.append(f"{h}  {p.relative_to(ROOT)}")
    return out


def main() -> None:
    write_json(results7("deviations.json"), DEVIATIONS)
    costs = {}
    for f in ("openrouter_cost_paths.json", "openrouter_cost.json"):
        p = results7(f)
        if p.exists():
            costs[f] = read_json(p)
    for f in ("novelty_audit.json", "r_hybrids.json"):
        p = results7(f)
        if p.exists():
            costs[f] = {"cost_usd": read_json(p).get("cost_usd")}
    for p in (ROOT / "results").glob("*cost*.json"):
        if p.name != "costs.json" and p.name not in costs:
            costs[p.name] = read_json(p)
    jc = ROOT / "data" / "judge_cache.jsonl"
    if jc.exists():
        costs["bench_judge_data/judge_cache.jsonl"] = {"total_usd": round(sum(float(r.get("cost") or 0)
                                                                              for r in read_jsonl(jc)), 6),
                                                       "n_calls": len(read_jsonl(jc))}
    tot = 0.0
    for k, v in costs.items():
        if isinstance(v, dict):
            tot += float(v.get("total_usd") or v.get("cost_usd") or v.get("total") or 0)
    costs["total_usd_estimate"] = round(tot, 5)
    costs["cap_usd"] = 0.5
    write_json(results7("costs.json"), costs)
    tim = read_jsonl(results7("timing_batches.jsonl"))
    by = defaultdict(lambda: {"seconds": 0.0, "rows": 0})
    for r in tim:
        k = r["tag"].split(":")[0]
        by[k]["seconds"] += r["seconds"]
        by[k]["rows"] += r["n_real"]
    tot_s = sum(v["seconds"] for v in by.values())
    write_json(results7("timing_summary.json"), {"by_stage": by, "gpu_generation_seconds": tot_s,
                                                 "rows": sum(v["rows"] for v in by.values()),
                                                 "seconds_per_row": tot_s / max(1, sum(v["rows"] for v in by.values())),
                                                 "utc": utc_now()})
    lines = sha_tree(INPUTS)
    (INPUTS / "SHA256SUMS_iter7").write_text("\n".join(lines) + "\n")
    avail = {"exp30_src": (INPUTS / "exp30" / "src").exists(), "exp30_prompts": (INPUTS / "exp30" / "prompts").exists(),
             "bench_T03": (INPUTS / "exp11" / "bench" / "T03_kth_smallest").exists(),
             "bench_T10": (INPUTS / "exp11" / "bench" / "T10_connected_components").exists(),
             "exp8_suite": (INPUTS / "exp8" / "suite").exists(), "dependency_art_j3Rm_lr2nzR6": (ROOT / "data" /
                                                                                              "dep_extract.json").exists(),
             "exp24_base_samples": (INPUTS / "exp24_T2_base_samples.jsonl").exists(),
             "exp29_labels": (INPUTS / "exp29_T2_labels.jsonl").exists(), "exp9_los": (INPUTS / "exp9_los.json").exists(),
             "n_input_files": len(lines), "utc": utc_now()}
    write_json(results7("inputs_available.json"), avail)
    rep = read_json(ROOT / "prompts" / "prompt_report7.json")
    write_json(results7("tests_cpu.json"), {"prompts": rep.get("cpu_tests"), "exp30_forced_reproduced":
                                            rep.get("exp30_forced_reproduced"),
                                            "semseed_matches_exp30": rep.get("semseed_matches_exp30")})
    from commit7 import verify
    write_json(results7("commit_chain.json"), verify())
    print("bookkeeping done; cost estimate", costs["total_usd_estimate"])


if __name__ == "__main__":
    main()
