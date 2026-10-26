#!/usr/bin/env python3
"""COMMIT #1 (dose table + per-arm predictions, before any Stage 3 sample) and COMMIT #2 (HR predictions and the
novelty-audit protocol, before any new HR branch). Usage: make_commits.py c1 [units] | c2"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg8 import INPUTS, PRED_DIR, RESULTS_DIR, SAMPLES, SRC, read_json, read_jsonl, utc_now, write_json  # noqa
import commit8 as CM  # noqa: E402


def c1(units: list[str]) -> None:
    import dose8
    assert not any(r.get("stage") == "S3" for r in read_jsonl(SAMPLES)), "a Stage 3 row exists before COMMIT #1"
    tab = dose8.build_commit1(units)
    tab["design_choices"] = [
        "T10: index-10 tokens other than ' def' with T = 1 mass >= 1e-4 and Phat max < 0.8 get a teacher-forced "
        "index-11 distribution and a pooled class map from the token string (no new continuations); ' def' uses the "
        "measured n11 map (deviation D06)",
        "Composition uses plug-in token-map frequencies; the committal rule uses pseudo-count 0.5 per observed class "
        "(deviation D05)",
        "Attainable maximum = maximum of the composed share over the dose grid (the curve is not monotone in T)",
        "Per-slot replay uses the twin's captured decode logits at the decision (top-64, float64)",
        "Identity shortcut disabled: U2 failed (17/20 byte-identical at a different batch shape); every arm slot is "
        "generated, each arm in batches shaped like its twin"]
    tab["input_hashes_file_sha256"] = __import__("cfg8").sha256_file(INPUTS / "input_hashes.json")
    tab["tests_gpu"] = read_json(RESULTS_DIR / "tests_gpu.json")
    tab["stage0"] = read_json(RESULTS_DIR / "stage0.json") if (RESULTS_DIR / "stage0.json").exists() else None
    write_json(PRED_DIR / "commit1_dose_table.json", tab)
    files = [PRED_DIR / "commit1_dose_table.json"] + [SRC / f for f in (
        "analysis_k1.py", "dose8.py", "predict8.py", "arms8.py", "hr8.py", "cfg8.py", "engine8.py", "gpu8.py",
        "stages8.py", "units8.py", "novelty8.py")] + [PRED_DIR / "stage3_flags.json", INPUTS / "input_hashes.json"]
    e = CM.commit("COMMIT1_dose_table", files)
    print("COMMIT #1", e["utc"], e["chain"][:16])


def c2() -> None:
    proto = {"utc": utc_now(),
             "predicted_extra_ideas": {"T10": ">= 1 (bfs reached only by forcing ' bfs' at n11 or rank > 20 tokens)",
                                       "B3": ">= 1 (prim_array or boruvka)", "A3": ">= 1 (monotonic_stack or "
                                       "peak_split)", "B6": ">= 1 (hash_count or alphabet_count_scan)",
                                       "G": "0-1", "T1": ">= 1 if mapped"},
             "prediction": "ideas(HR) - ideas(K*) >= 1 on >= 3 units; every extra idea is a KNOWN technique; 0 novel",
             "nodes_order": ["T10 n10", "T10 n11", "B3 c0", "B3 c1", "G cstar", "A3 c0", "A3 c1", "B6 c0", "T1 n3"],
             "hr_design": "ranks 1-64 by template-averaged T = 1 probability; ranks in the Stage 2 map reuse its first 5 "
                          "continuations; new tokens: 5 continuations at T = 1, streams ('iter8hr', 6,600,000 + "
                          "node*1000 + rank*10 + k)",
             "novelty_audit_protocol": {
                 "retrieval": "3 nearest known solutions by identifier-normalised AST Zhang-Shasha distance after a "
                              "token 4-gram Jaccard prefilter over 17,442 solutions from all ten datasets of "
                              "art_j3Rm_lr2nzR6",
                 "judges": ["deepseek/deepseek-chat-v3.1", "google/gemini-2.5-flash"], "tiebreak": "moonshotai/kimi-k2",
                 "controls": "10 programs of known class: 6 catalogue (twins), 2 known-outside-catalogue (prime-product "
                             "anagram hash; Laplacian-rank component count), 2 degenerate", "gate": ">= 8/10 family-correct",
                 "manual_read": "every audited program: NOVEL ALGORITHM / KNOWN OUTSIDE CATALOGUE / CATALOGUE VARIANT / "
                                "LABELLER MISS / DEGENERATE", "claim_rule": "'no correct novel algorithm' only at a "
                                "count of 0, with the rule-of-three bound", "cap_usd": 1.5}}
    write_json(PRED_DIR / "commit2_hr.json", proto)
    e = CM.commit("COMMIT2_hr", [PRED_DIR / "commit2_hr.json", SRC / "hr8.py", SRC / "novelty8.py"])
    print("COMMIT #2", e["utc"], e["chain"][:16])


if __name__ == "__main__":
    if sys.argv[1] == "c1":
        c1(sys.argv[2].split(",") if len(sys.argv) > 2 else ["T10", "T1", "B3", "A3", "B6", "G"])
    else:
        c2()
