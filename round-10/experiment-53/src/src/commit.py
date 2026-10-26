"""Hash-chained commitments: COMMIT #1 (protocol + predictions, before the first search call), COMMIT #2 (C*),
COMMIT #3 (corpus) and amendments. Usage: python src/commit.py commit1 | amend <label> <files...>"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, PRED, RESULTS, ROOT, commit_files, ledger, sha256_file, sha256_text, utc_now, write_json  # noqa: E402

PREDICTIONS = {
    "V1-T": "SUPPORTED: NN held-out n-200 gap 24-28%; every core arm-seed best at most 0.8 x NN (point guess 15-20%).",
    "V2-T": "SUPPORTED: pooled DTB/T1.0 and DTB/T1.6 at least 1.5, both per-seed ratios above 1, DTB/RPB at least 1.2.",
    "validity_point_guesses": {"T1.0": 0.60, "T1.6": 0.35, "DTB": 0.50, "RPB": 0.45, "IDEA": 0.55},
    "dtb_jstar_class": "DTB's j* lies on an identifier, operator or keyword token in at least 60% of branched calls "
                       "(descriptive).",
    "idea_rename_rate": "at least 0.4 of valid IDEA offspring agree at least 0.95 with a parent (descriptive "
                        "replication of V6).",
    "source": "artifact plan gen_plan_experiment_3_idx3 (written without NOV-B's outcome); copied verbatim",
}

C_TABLE = {
    "A": "largest C* in {2000, 1500, 1000} with T1.0, T1.6, DTB, RPB and IDEA on both seeds (NOSEL 500 only if "
         "C* >= 1500)",
    "B": "the same without IDEA",
    "C": "seed 0 at the largest C0 in {2000, 1500} and seed 1 at 1000, core arms",
    "D": "both seeds at 1,000, core arms (never-drop floor)",
    "E": "BELOW-PLAN: core arms of both seeds round-robin until the stop, flagged",
    "projection": "time for C calls = sum over arm-seeds of (C - done)/32 x W_share(arm) x 1.2, W measured on "
                  "rounds 2-4, W_share by generated + prefilled tokens; T_rem = (stop - now) - 10 min",
}

VERDICT_RULES = {
    "V1-T": "SUPPORTED iff for every core arm (T1.0, T1.6, DTB, RPB) in every seed G200(best) <= 0.8 G200(NN); "
            "DISCONFIRMED iff no core arm-seed best has G200 < G200(NN); PARTIAL otherwise (failing arm-seeds named).",
    "V2-T": "R_X = [sum_s c(DTB,s)/sum_s N(DTB,s)] / [sum_s c(X,s)/sum_s N(X,s)] (c = primary cluster count, N = "
            "calls). SUPPORTED iff R_T1.0 >= 1.5 and R_T1.6 >= 1.5 and r_X,s > 1 for both temperature arms and both "
            "seeds and R_RPB >= 1.2 and mean_s G200(DTB best) <= min_X mean_s G200(X best). DISCONFIRMED iff R_T1.0 "
            "<= 1.0 or R_T1.6 <= 1.0. PARTIAL otherwise with named branches.",
    "best_program": "minimum F among PROBE-VALID programs of an arm-seed, ties to the earliest call",
    "clusters": "complete linkage on Hamming distance of the 2,000 probe decisions, fcluster t = 0.05 distance",
}


def src_hashes() -> dict:
    out = {}
    for p in sorted(list((ROOT / "src").glob("*.py")) + list((ROOT / "tests").glob("*.py")) +
                    [ROOT / "audit" / "rederive.py", ROOT / "start_vllm.sh"]):
        if p.exists():
            out[str(p.relative_to(ROOT))] = sha256_file(p)
    return out


def commit1() -> None:
    import prompt as pr
    from dtb import ARM_CODE, SPECIAL_MIN_ID
    from islands import FUNCS_PER_PROMPT, N_ISLANDS, N_RESET, RESET_EVERY, T_INIT, T_PERIOD

    base = json.loads((RESULTS / "baselines.json").read_text())
    refs = json.loads((RESULTS / "references.json").read_text())
    nn = base["NN"]
    proto = {
        "utc": utc_now(), "commit": 1,
        "hashes": {"inputs_manifest": sha256_file(ROOT / "inputs_manifest.json"),
                   "instances": json.loads((DATA / "instance_hashes.json").read_text()),
                   "probe_states": sha256_file(DATA / "probe_states.json"),
                   "references_jsonl": sha256_file(DATA / "references.jsonl")},
        "references_summary": refs,
        "NN": {"G50": nn["G50"], "G100": nn["G100"], "F": 1.0, "G200": nn["G200"], "G200_ext": nn["G200_ext"],
               "TSPLIB_mean": nn["tsplib"]["mean_gap"]},
        "V1_bar_0.8xG200_NN": 0.8 * nn["G200"],
        "fitness": "F = 0.5 G50/G50(NN) + 0.5 G100/G100(NN); lower is better; NN = 1",
        "islands": {"n_islands": N_ISLANDS, "functions_per_prompt": FUNCS_PER_PROMPT, "T_init": T_INIT,
                    "T_period": T_PERIOD, "reset_every_calls": RESET_EVERY, "n_reset": N_RESET,
                    "cluster_key": "64 per-instance gaps rounded to 1e-6", "pipeline_lag_rounds": 2,
                    "calls_per_round": 32},
        "arms": {"T1.0": {"T": 1.0, "top_p": 1.0}, "T1.6": {"T": 1.6, "top_p": 0.95},
                 "DTB": {"rule": "entropy argmax among eligible positions of the first 48 body tokens"},
                 "RPB": {"rule": "uniform eligible position (placebo)"}, "IDEA": {"T": 1.0, "line": "IDEA"},
                 "NOSEL": {"T": 1.0, "prompt": "fixed NN-only", "calls": 500, "seed": 0, "optional": True}},
        "arm_codes": ARM_CODE, "seeds": [0, 1], "pilot_seed": 99,
        "sampling_common": {"top_k": -1, "min_p": 0.0, "repetition_penalty": 1.0, "presence_penalty": 0.0,
                            "frequency_penalty": 0.0, "max_tokens": 512, "stops": pr.STOPS,
                            "request_seed": "int(default_rng([seed, arm, call, 2]).integers(2**31)); request 2 uses +1"},
        "dtb_rpb_rules": __import__("dtb").__doc__, "special_min_id": SPECIAL_MIN_ID,
        "prompt": {"task_docstring": pr.TASK_DOCSTRING, "spec_doc": pr.SPEC_DOC,
                   "instruction_k1": pr.instruction(1, False), "instruction_k2": pr.instruction(2, False),
                   "idea_k1": pr.instruction(1, True), "idea_k2": pr.instruction(2, True),
                   "prefill_k2": pr.prefill(2), "sha256_templates": sha256_text(
                       pr.TASK_DOCSTRING + pr.SPEC_DOC + pr.instruction(2, True) + pr.prefill(2) + pr.IMPORTS)},
        "C_table": C_TABLE, "verdict_rules": VERDICT_RULES, "predictions": PREDICTIONS,
        "code_sha256": src_hashes(),
        "engine": {"server": "vllm 0.11.0, Qwen/Qwen3-8B-FP8@220b46e3, VLLM_TEST_FORCE_FP8_MARLIN=1, torch.compile "
                             "(level 3) + CUDA graphs (piecewise + full decode), max-model-len 4096, gmu 0.93, "
                             "prefix caching, max-logprobs 20, generation-config vllm, max-num-seqs 64",
                   "kv_cache_tokens": 80592, "gpu": "NVIDIA L4 23 GB"},
        "gpu_mechanics": json.loads((RESULTS / "gpu_mechanics.json").read_text()) if (RESULTS / "gpu_mechanics.json").exists() else None,
    }
    proto["gpu_mechanics"] and proto["gpu_mechanics"].pop("sample_outputs", None)
    p = PRED / "protocol.json"
    write_json(p, proto)
    files = [p] + [ROOT / k for k in proto["code_sha256"]]
    commit_files("COMMIT#1", files)
    ledger("COMMIT#1", n_files=len(files))
    print(f"COMMIT #1: {len(files)} files")


def amend(label: str, files: list[str]) -> None:
    commit_files(label, [ROOT / f for f in files])
    ledger(label, files=files)
    print(f"{label}: {len(files)} files")


if __name__ == "__main__":
    if sys.argv[1] == "commit1":
        commit1()
    elif sys.argv[1] == "amend":
        amend(sys.argv[2], sys.argv[3:])
