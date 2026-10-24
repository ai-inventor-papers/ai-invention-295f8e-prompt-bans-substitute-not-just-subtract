#!/usr/bin/env python3
"""S7 commitments: predictions/commit1.json (before any generation call), commit #2 (C* before round 6) and later
amendments, each appended to commitments.log as 'UTC sha256(commitN.json) sha256(previous line)' (a hash chain).

Usage: python src/commit.py commit1 | amend <name> <json-file> | verify"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from loguru import logger  # noqa: E402

import common as C  # noqa: E402

LOG = C.ROOT / "commitments.log"


def chain_append(path: Path) -> str:
    prev = LOG.read_text().strip().splitlines()[-1] if LOG.exists() and LOG.read_text().strip() else ""
    line = f"{C.utc()} {C.sha256_file(path)} {C.sha256_text(prev)}"
    with open(LOG, "a") as f:
        f.write(line + "\n")
    return line


def verify_chain() -> bool:
    lines = LOG.read_text().strip().splitlines() if LOG.exists() else []
    prev = ""
    for ln in lines:
        utc, h, ph = ln.split()
        if ph != C.sha256_text(prev):
            return False
        prev = ln
    return True


def src_hashes() -> dict:
    return {p.relative_to(C.ROOT).as_posix(): C.sha256_file(p) for p in sorted(C.SRC.glob("*.py"))}


def commit1() -> dict:
    import engine
    import operators as OP
    import prompts as P
    import search
    tok = engine.load_tokenizer()
    bf = P.seed_program(P.BF_BODY)
    ff = P.seed_program(P.FF_BODY)
    rendered = {}
    for arm in ["T1.0", "T1.6", "DTB", "RPB", "IDEA"]:
        txt, ids = P.render(tok, P.user_turn(bf, bf, idea=(arm == "IDEA")))
        rendered[arm] = {"sha256": C.sha256_text(txt), "n_tokens": len(ids)}
    txt_ns, ids_ns = P.render(tok, P.user_turn(ff, bf))
    rendered["NS"] = {"sha256": C.sha256_text(txt_ns), "n_tokens": len(ids_ns)}
    gate = json.loads((C.RESULTS / "harness_gate.json").read_text())
    probes = json.loads((C.RESULTS / "probes.json").read_text())
    tuned = json.loads((C.RESULTS / "tuned_ab.json").read_text())
    corpus = json.loads((C.RESULTS / "corpus_hashes.json").read_text())
    c1 = {
        "utc": C.utc(), "artifact": "NOV-B2 (seeds 2 and 3)",
        "inputs_manifest_sha256": C.sha256_file(C.ROOT / "inputs_manifest.json"),
        "instance_sha256": gate["instance_sha256"], "p10_sha256": probes["p10_sha256"],
        "corpus": corpus, "tuned_ab_permutation": {"seed": tuned["seed"], "perm_sha256": tuned["perm_sha256"],
                                                   "n_evaluated": tuned["n_evaluated"], "tuned": tuned["tuned"]},
        "prompt": {"instruction": P.INSTRUCTION, "idea_sentence": P.IDEA_SENTENCE, "prefill": P.PREFILL,
                   "stops": P.STOPS, "max_tokens": P.MAX_TOKENS, "template": P.TEMPLATE_NAME,
                   "user_turn_example_T1.0": P.user_turn(bf, bf), "user_turn_example_IDEA": P.user_turn(bf, bf, True),
                   "user_turn_NS": P.user_turn(ff, bf), "rendered_sha256_per_arm_with_BF_parents": rendered},
        "arms": OP.ARMS, "seeds": C.SEEDS, "arm_ids": C.ARM_IDS,
        "rng_rules": {"request_seed": "(S*1000003 + arm_id*100003 + call*7 + req) mod 2^31",
                      "parent_draw": "default_rng([S, arm_id, 1]) (also the reset noise and founder draws)",
                      "branch": "default_rng([S, arm_id, call, 7]); RPB j = rng.choice(E); r = rng.integers(2, min(8, len(cand[j])) + 1)"},
        "round": {"calls_per_arm_seed": search.ROUND_CALLS, "lockstep": "all active arm-seeds",
                  "lag": "prompts of round r+1 from databases after round r-1 is registered"},
        "islands": {"n": 5, "seed": "BF (F = 1, not a call)", "cluster": "identical 25-instance selection signature",
                    "T_c": "0.1 * (1 - (n_island mod 30000)/30000)", "within_cluster": "softmax(-(len-min)/(max+1e-6))",
                    "reset": "after every 400 calls: 2 worst of 5 (best score + N(0,1e-6)), founder = best of a uniform survivor"},
        "C_star_rule": {"options": search.CSTAR_OPTIONS, "t_round": "median wall time of rounds 3-5",
                        "end(C)": "now + (C/20 - 5) * t_round * 1.1", "deadline_h": search.H_CSTAR_END,
                        "drop_deadline_h": search.H_DROP_END, "hard_stop_h": search.H_HARD_STOP,
                        "drop_order": ["NS", "IDEA to 1000", "IDEA off", "seed 3 to 1000"],
                        "note": "plan clock milestones shifted 10 min earlier (session limit 5 h 54 min)"},
        "validity_rule": "v10: compiles under the AST screen; runs on all 25 selection instances within one cumulative 20 s CPU budget (SEL-OR then SEL-W, fail fast); every output 1-D, one finite score per valid bin",
        "clustering_rule": "complete linkage on 1 - agreement over unique P10 vectors of valid offspring, cut at 0.05 (every within-cluster pair agrees >= 0.95); D = clusters per 1000 calls",
        "thresholds": {"V1_factor": 0.8, "V2_R_temp": 1.5, "V2_R_RPB": 1.2, "V2_disconfirm": 1.0, "cluster": 0.95,
                       "novelty": 0.9, "V6_supported": 0.4, "V6_margin": 0.1, "V6_disconfirm": 0.2,
                       "V5_entropy_percentile": 90},
        "verdict_rules": {
            "V1": "pass(X) iff exc_FSW5k(best_X) <= 0.8*3.9843% and exc_OR3(best_X) <= 0.8*5.3678%; SUPPORTED iff all four core arms pass; DISCONFIRMED iff no core arm's best has lower excess than BF on H-FSW5k or on H-OR3; else PARTIAL",
            "V2": "R_X = (DTB clusters summed over seeds / DTB calls) / (same for X); SUPPORTED iff R_T1.0>=1.5 and R_T1.6>=1.5 and every per-seed ratio vs each temperature arm >1 and R_RPB>=1.2 and m_DTB<=min(m_T1.0,m_T1.6); DISCONFIRMED iff R_T1.0<=1.0 or R_T1.6<=1.0; else PARTIAL",
            "V3": "NOVEL-and-better = passes the 0.8 rule on both primary sets, max agreement < 0.9 with every priority-form corpus entry, NOT_KNOWN from both gated judges and NOVEL in the arm-blind manual read; SUPPORTED iff >= 1; else DISCONFIRMED with the rule-of-three bound",
            "V6": "rename(X) = share of valid offspring agreeing >= 0.95 with either parent; SUPPORTED iff rename(IDEA)>=0.4 and rename(IDEA)>=rename(T1.0)-0.1; DISCONFIRMED iff rename(IDEA)<0.2; else PARTIAL",
            "V5": "descriptive"},
        "lexicon": {"A": r"\b(new|novel|different|alternative|instead|unlike|another)\b",
                    "B": r"\b(idea|approach|strategy|heuristic|method|rule)\b", "rule": "A and B in the same comment"},
        "base_fork_arm": "dropped (protocol forbids two models on the GPU)",
        "src_sha256": src_hashes(),
    }
    out = C.PRED / "commit1.json"
    if out.exists():
        raise SystemExit("commit1.json exists; amendments must be new commits")
    C.write_json(out, c1)
    line = chain_append(out)
    logger.info(f"commit #1: {line}")
    C.ledger("commit #1", planned_h=1.75)
    return c1


def commit2(decision: dict) -> None:
    out = C.PRED / "commit2.json"
    if out.exists():
        return
    d = dict(decision, utc=C.utc(), src_sha256=src_hashes())
    C.write_json(out, d)
    line = chain_append(out)
    logger.info(f"commit #2: {line}")
    C.ledger("commit #2 (C*)", planned_h=2.2, C_star=decision.get("C_star"))


def amend(name: str, payload: dict) -> str:
    n = len(list(C.PRED.glob("commit*.json"))) + 1
    out = C.PRED / f"commit{n}_{name}.json"
    C.write_json(out, dict(payload, utc=C.utc(), src_sha256=src_hashes()))
    return chain_append(out)


@logger.catch(reraise=True)
def main() -> None:
    C.setup_logging("commit")
    cmd = sys.argv[1]
    if cmd == "commit1":
        commit1()
    elif cmd == "amend":
        print(amend(sys.argv[2], json.loads(Path(sys.argv[3]).read_text())))
    elif cmd == "verify":
        print("chain ok" if verify_chain() else "CHAIN BROKEN")


if __name__ == "__main__":
    main()
