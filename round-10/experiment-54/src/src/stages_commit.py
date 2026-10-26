#!/usr/bin/env python3
"""S6: unit tests U1-U9 (results/tests.json) and COMMIT #1 (predictions/commit1.json + frozen code copies), and S7
engine smoke tests."""
from __future__ import annotations

import shutil
import time
from typing import Any

import numpy as np
from loguru import logger

import extract
import lexical
import prompts
import refs
import sandbox
import stats
from common import (DATA, PRED, RESULTS, ROOT, SRC, commit, deviation, milestone, read_json, sha256_file,
                    sha256_text, write_json)

FROZEN = ["analysis.py", "stats.py", "lexical.py", "extract.py", "gate_instr.py", "instr.py", "prompts.py",
          "evalq.py", "sandbox.py", "probes.py"]


def u4_seeding() -> dict[str, Any]:
    g = read_json(RESULTS / "instrument_gate.json")
    a = g["a_self_agreement"]["RF"]
    sandbox.install_rng_patch()
    # uniform states (index >= 1000) with a random rule restricted to used bins, so the harness seed can matter
    code = ("def priority(item, bins):\n    r = np.random.default_rng().random(len(bins))\n"
            "    return np.where(bins < bins.max(), r, -1.0)\n")
    st = sandbox._load_probe(DATA / "probes" / "P10.json")[1000:1200]
    v1, _ = sandbox.probe_with_seed(code, st, 0)
    v2, _ = sandbox.probe_with_seed(code, st, 0)
    v3, _ = sandbox.probe_with_seed(code, st, 1)
    ok = bool(a["identical_across_runs"] and a["differs_across_seeds"] > 0.5 and np.array_equal(v1, v2) and
              not np.array_equal(v1, v3))
    return {"rf_identical_same_seeds": a["identical_across_runs"], "rf_share_differing_seed0_vs_1":
            a["differs_across_seeds"], "unseeded_default_rng_deterministic_under_patch": bool(np.array_equal(v1, v2)),
            "unseeded_default_rng_differs_across_harness_seeds": bool(not np.array_equal(v1, v3)), "passed": ok}


def s6_commit1() -> dict[str, Any]:
    import sample_or
    hg = read_json(RESULTS / "harness_gate_v10.json")
    pr = read_json(RESULTS / "probes.json")
    gate = read_json(RESULTS / "instrument_gate.json")
    corpus = read_json(RESULTS / "corpus.json")
    tests = {"U1_harness": {"passed": hg["G_HARNESS_PASS"], "gate": {k: v.get("passed") for k, v in hg["gate"].items()
                                                                      if isinstance(v, dict)}},
             "U2_handcoded": hg["u2"], "U3_probes": pr["u3"], "U4_seeding": u4_seeding(),
             "U5_alias_regex": lexical.unit_test_u5(), "U6_extraction": extract.unit_test_u6(),
             "U7_statistics": stats.unit_test_u7(), "U8_mock_403_and_slow_stream": sample_or.unit_test_u8(DATA),
             "U9_instrument_gate": {"passed": gate["passed"], "parts": gate["parts"], "min_margin": gate["min_margin"]},
             "U10_rederive_placebos": {"status": "run at S12 with audit/rederive.py (stdlib audit path; it does not "
                                                 "govern any sample)"}}
    tests["all_pre_commit_passed"] = all(v.get("passed") for k, v in tests.items()
                                         if isinstance(v, dict) and "passed" in v)
    write_json(RESULTS / "tests.json", tests)
    logger.info({k: v.get("passed") for k, v in tests.items() if isinstance(v, dict)})
    if not tests["all_pre_commit_passed"]:
        raise SystemExit("unit tests failed; fix before commit #1")
    fz = PRED / "frozen_code"
    fz.mkdir(parents=True, exist_ok=True)
    frozen = {}
    for f in FROZEN:
        shutil.copyfile(SRC / f, fz / f)
        frozen[f] = sha256_file(fz / f)
    payload = {
        "label": "commit1", "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "inputs_manifest_sha256": sha256_file(ROOT / "inputs" / "inputs_manifest.json"),
        "instance_sha256": {k: v["sha256"] for k, v in read_json(RESULTS / "input_verification.json")[
            "instance_hashes"].items()},
        "probe": {"P10_sha256": pr["P10"]["sha256"], "rule_text_sha256": sha256_text(pr["rule_text"]),
                  "n_states": pr["P10"]["n_states"], "n_informative": pr["P10"]["n_informative"]},
        "corpus": {"n_members": corpus["n_members"], "tuned_ab": corpus["tuned_ab"], "tuned_ab_F":
                   corpus["tuned_ab_F"], "decisions_sha256": corpus["decisions_sha256"],
                   "corpus_json_sha256": sha256_file(RESULTS / "corpus.json")},
        "instrument_gate": {"passed": gate["passed"], "parts": gate["parts"], "min_margin": gate["min_margin"],
                            "file_sha256": sha256_file(RESULTS / "instrument_gate.json"),
                            "note": "run 0 failed part (e) only because the harness's RandomState patch broke "
                                    "numpy 2.x default_rng (planted control rf_default_rng_priority errored); the "
                                    "patch was fixed (type subclasses) and the gate rerun on the same P10 before "
                                    "this commit; run 0 kept in results/instrument_gate_run0_rngpatchbug.json"},
        "thresholds": {"class": 0.95, "novelty": 0.9, "heldout_factor": 0.8, "H-OR3_pct": 4.294,
                       "H-FSW5k_pct": 3.187, "quality_F": 1.1, "P1a_P1c": 0.7, "P1d_e_gap": 0.3, "P2_diff": 0.2,
                       "P3_cap": 0.02, "jt_alpha": 0.05, "valid_probe_err": 0.01, "stochastic_diff": 0.01,
                       "rf_matcher": {"used_min": 0.95, "ks_max": 0.10, "s2s_margin": 0.15},
                       "sensitivities": [0.90, 0.98, "informative-only", "L2", "VALID_FULL denominator"]},
        "prompts": prompts.commitment_block(),
        "aliases": {"names": lexical.NAMES, "match_order": lexical.MATCH_ORDER, "negation_window": lexical.NEG_WINDOW,
                    "negation_regex": lexical.NEG_RE.pattern, "synonyms": lexical.SYNONYMS},
        "extraction_rule": extract.__doc__,
        "models": {"q8": {"engine": "vLLM0.11/Qwen3-8B-FP8/W8A16-Marlin", "thinking": False, "max_tokens": 4096,
                          "N": {"decisive": 50, "instr": 50}},
                   "q32": {"model": "qwen/qwen3-32b", "provider": sample_or.PROVIDER, "thinking": True,
                           "max_tokens": 12288, "N": {"decisive": 50, "instr": 30}},
                   "q14": {"model": "qwen/qwen3-14b", "provider": sample_or.PROVIDER, "thinking": True,
                           "max_tokens": 12288, "N": {"decisive": 50, "instr": 30}}},
        "decoding": {"temperature": 1.0, "top_p": 1.0, "top_k": "-1 local / off OpenRouter"},
        "verdict_rules": {"P1": "SUPPORTED iff (a) L1 >= 0.7 and mech >= 0.7 at k=1 in every run model, and each of "
                                "(b) JT decreasing p_perm < 0.05, (c) L1 >= 0.7 at every k, (d) NAME_5 paired gap >= "
                                "0.3 with paired Newcombe lower bound > 0, (e) HOLD_5 gap >= 0.3 with lower bound > 0 "
                                "holds in >= 2 run models; DISCONFIRMED iff |L1 - mech| <= 0.1 at every k in every run "
                                "model; otherwise PARTIAL naming the failing parts",
                          "P2": "DESC_5 minus NAME_5 mech compliance (scored against S_desc), unpaired Newcombe; "
                                "SUPPORTED iff >= 0.2 with lower bound > 0 in >= 2 run models; DISCONFIRMED iff <= 0 "
                                "in >= 2; otherwise PARTIAL; sensitivity scored against B_5",
                          "P3": "per cell, share of all N that is VALID, better on both held-out sets (H-OR3 <= "
                                "4.294%, H-FSW5k <= 3.187%), novel (max corpus agreement < 0.9, class other) and "
                                "confirmed by the S11 audit; SUPPORTED iff every run cell <= 0.02"},
        "schedule": {"order_rule": "frequency order over {BF,FF,WF,AWF,LF,RF} among VALID BASE programs; ties and "
                                   "zero counts by BF,FF,WF,AWF,LF,RF; B_k = top k; S_desc = rules of B_5 whose "
                                   "description passed the naming check (>= 16/20; rewrites 1, 2)",
                     "openrouter_priority": ["q32 NAME_1..5+DESC_5", "q14 NAME_1..5+DESC_5", "HOLD_5 q32",
                                             "HOLD_5 q14", "INSTR q32", "INSTR q14"],
                     "slot_interleaving": "templates interleaved by slot so a time cut leaves cells balanced",
                     "reduction_ladder": prompts.LADDER, "drop_order": ["OpenRouter INSTR cells", "q14",
                                                                         "HOLD_5 of the weaker model"],
                     "never_dropped": ["G-INSTR", "q8 and q32 through NAME_1..5 and DESC_5", "P3 in every run cell"],
                     "hard_stop_sampling_h": 4.5, "openrouter_concurrency": 8, "cost_cap_usd": 5.0},
        "deviations_declared": {"D1": "vLLM --max-model-len 6144 (4096 cannot hold max_tokens 4096 + prompt)",
                                "D2": "VALID on SEL-OR + probes; VALID_FULL (SEL-W) is a sensitivity denominator",
                                "D3": "streaming with 180 s idle timeout and 900 s total cap",
                                "D4": "stochastic RF matcher instead of literal agreement >= 0.95 for RF",
                                "D5": "described-ban P2 scored against S_desc (B_5 as sensitivity)",
                                "D6": "paired Newcombe for the k = 5 gap (unpaired printed beside it)",
                                "D7": "HF_HOME not overridden (shared run cache, per the system rules); VLLM_CACHE_ROOT "
                                      "in the workspace",
                                "D8": "RNG patch bug found by the gate's planted control and fixed before commit #1"},
        "tests_sha256": sha256_file(RESULTS / "tests.json"),
        "frozen_code": frozen,
    }
    p = PRED / "commit1.json"
    write_json(p, payload)
    e = commit(p, "commit1", "thresholds, prompts, probes, corpus, instrument gate, verdict rules, frozen code")
    for code, text in payload["deviations_declared"].items():
        deviation(code, text)
    milestone("commit1", line=e["i"])
    return e


def s7_engines() -> dict[str, Any]:
    import asyncio

    import sample_local
    out: dict[str, Any] = {"local_health": sample_local.health()}
    if out["local_health"]:
        tmp = DATA / "smoke_local.jsonl"
        tmp.unlink(missing_ok=True)
        item = {"model_key": "q8", "cell": "SMOKE", "slot": 0, "seed": 1, "prompt": "Say hello in one word."}
        asyncio.run(sample_local.run_items([item], lambda it: tmp, concurrency=1, max_tokens=64))
        from common import read_jsonl
        rows = read_jsonl(tmp)
        out["local_smoke"] = {"content": rows[0]["content"][:200] if rows else None,
                              "no_think_content": bool(rows and "<think>" not in rows[0]["content"] or
                                                       (rows and rows[0]["content"].split("</think>")[0].replace(
                                                           "<think>", "").strip() == "")),
                              "finish_reason": rows[0]["finish_reason"] if rows else None}
    write_json(RESULTS / "engine_smoke.json", out)
    return out
