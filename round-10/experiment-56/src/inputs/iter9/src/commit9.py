#!/usr/bin/env python3
"""COMMIT #0 (before any GPU pass that reads a margin): units and prompt shas, node lists, samplers, thresholds and
verdict rules, code hashes. Later commits: commit0b (analysis9.py sha256, before any verdict is computed) and commitB3
(meancache_aligned.py sha256, unit tests and the 6.1 reproduction value, before the held-out rerun)."""

from __future__ import annotations

import sys

from loguru import logger

from cfg9 import (FSTACK, LLAMA_CHAT_NORM_FRAC, GEMMA_MASS_MIN, N_RAND, N_RAND_SPEC, NEAR_COLLAPSE, ONPOLICY_MIN_LOGP,
                  Q_FORK, RAND_BAND, RAND_TOL, RAND_TOL_WIDE, RESULTS_DIR, RS_LAYERS, SEED_RAND, SPEC_RAND_BAND,
                  SRC, STEER_DOSE, STEER_DOSE_SENS, THRESH, B3_TARGET_D, B3_TOL_EXACT, B3_TOL_GPU, commit, read_json,
                  setup_logging, sha256_file)

RULES = {
    "B1": {
        "P1": "margin gain (instruct minus base, chat template unless the template-primary rule switches the unit) "
              ">= 2 nats on every near-collapsed fork (instruct mean P(D class) >= 0.85) in Gemma and Llama",
        "P2": "|mean phrasing entropy change H_base - H_instr| < 0.5 nats on every unit",
        "P3": "JS_fork / JS_entropy-matched >= 1.3 on at least half the units AND JS_random / JS_phrasing <= 1.3 on "
              "every unit",
        "P4": "the instruct argmax token at the fork is not the base argmax on a majority of prompts, in at least half "
              "the units",
        "PASS": "P1-P4 hold",
        "DISCONFIRMED": "gain < 1 nat on the near-collapsed forks; if no fork qualifies, mean gain < 1 nat over all "
                        "Gemma units",
        "PARTIAL": "otherwise",
    },
    "B2": {
        "share": "share(X) = sum_p (m_I,p - m_X,p) / sum_p (m_I,p - m_B,p)",
        "Q1": "share(FSTACK) >= 0.5 on B3 and on T10",
        "Q2": "median share of the 50 matched random sets <= 0.15, and FSTACK above their 95th percentile, on each "
              "unit",
        "Q3": "share(SPEC set) <= 0.15 (each unit)",
        "SUPPORTED": "Q1-Q3 on both units",
        "DISCONFIRMED": "share(FSTACK) <= 0.2 on both units",
        "PARTIAL": "otherwise",
        "localisation": "'written upstream' if RS-prefix(23) >= 0.5; 'written at the fork by other late components' "
                        "if RS-fork(36) - RS-fork(23) >= 0.5 and share(FSTACK) <= 0.2; otherwise 'distributed'",
    },
    "B3": "no threshold; reported whatever it shows",
    "template_primary": {
        "llama": f"if the Llama-3.1-8B embedding row norm of any of <|start_header_id|>, <|end_header_id|>, <|eot_id|> "
                 f"is < {LLAMA_CHAT_NORM_FRAC} x the median row norm, template-free is primary for Llama",
        "gemma": f"if the pt model's mass on D or A at the fork under the chat template is < {GEMMA_MASS_MIN} (mean over "
                 f"prompts), template-free is primary for that unit",
    },
    "near_collapse": f"instruct teacher-forced P(D class) at the fork, averaged over prompts, >= {NEAR_COLLAPSE}",
    "fork_set_quantile": Q_FORK,
    "on_policy": f"drop a prompt whose instruct log P(opening) < {ONPOLICY_MIN_LOGP} nats (instruct model only)",
    "random_sets": {"pool": f"same component type at the fork, layers {RAND_BAND[0]}-{RAND_BAND[1]}, not in FSTACK",
                    "tolerance": list(RAND_TOL), "widened_if_lt_3_candidates": list(RAND_TOL_WIDE),
                    "n_sets": N_RAND, "seed": f"{SEED_RAND} + unit index (B3 0, T10 1)",
                    "draw": "with replacement across sets, no repeats within a set",
                    "variants": "R-pure (pool also excludes every exp41 top-15 DEC node); R-scaled (deltas rescaled "
                                "to the FSTACK node's norm; sensitivity only)",
                    "spec_sets": f"{N_RAND_SPEC} sets, same rule at SPEC positions, layers {SPEC_RAND_BAND[0]}-"
                                 f"{SPEC_RAND_BAND[1]}, seed {SEED_RAND} + 100 + unit index"},
    "rs_layers": list(RS_LAYERS),
    "b3": {"target_d": B3_TARGET_D, "tol_exact": B3_TOL_EXACT, "tol_gpu_logged": B3_TOL_GPU,
           "steer_dose": STEER_DOSE, "steer_dose_sensitivity_posthoc": STEER_DOSE_SENS},
}


def code_hashes() -> dict[str, str]:
    return {p.name: sha256_file(p) for p in sorted(SRC.glob("*.py"))}


def commit0() -> None:
    from cmap9 import node_sets, spec_sets
    U = read_json(RESULTS_DIR / "units.json")
    tests = read_json(RESULTS_DIR / "tests_cpu.json")
    assert tests["all_pass"], "CPU tests failed: no COMMIT #0"
    payload = {
        "units": {u: {"n_prompts": len(v["prompts"]), "prompt_sha256": [p["sha"] for p in v["prompts"]],
                      "forks": [{"fork_id": f["fork_id"], "D": f["D"], "A": f["A"], "D_str": f["D_str"],
                                 "A_str": f["A_str"], "opening_len": len(f["opening"])} for f in v["forks"]]}
                  for u, v in U.items()},
        "FSTACK": FSTACK, "node_sets": node_sets(), "spec_sets": spec_sets(), "rules": RULES,
        "thresholds": THRESH, "tests_cpu": tests, "code_sha256": code_hashes(),
        "note": "analysis9.py is committed in commit0b (sha256) before any verdict is computed (deviation logged)",
    }
    commit("commit0", payload)


def commit0b() -> None:
    commit("commit0b", {"analysis9_sha256": sha256_file(SRC / "analysis9.py"), "code_sha256": code_hashes(),
                        "rules": RULES, "thresholds": THRESH})


if __name__ == "__main__":
    setup_logging("commit9")
    {"commit0": commit0, "commit0b": commit0b}[sys.argv[1]]()
    logger.info("done")
