#!/usr/bin/env python3
"""Stage 0 (engine check) + GPU unit tests U1, U2, U3, U5, U8.

0a  TWIN cells, W1-W5 x k 0-5 (N = 30) on T2, T03, T10 and T1 (CRN baselines reused by every later arm; T2/T03
    k 0-3 are compared per slot with exp30's bf16 rows, T10/T2 k 0-5 with exp29 engine-d twin rows)
0b  POP 9101-9105 x k 0-1 (N = 10) on T10 and T2 at alpha 2 (exp29 screen slots) -> data/samples_raw_s0b.jsonl,
    NOT labelled before commit #3 (they are POP outcomes)
0c  realised S-mean displacement norms at blocks 12/23/35 of the 5 directions vs exp29 realised_disp.jsonl
0d  timing per sample (results/timing.jsonl)
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import torch  # noqa: E402
from loguru import logger  # noqa: E402

import c7 as common  # noqa: E402
from c7 import (DATA, IN29, PRED, RESULTS, SEEDS_STAGE0, TEMPLATES, append_jsonl, read_json, read_jsonl,  # noqa: E402
                    setup_logging, utc_now, write_json)
import engine7 as E  # noqa: E402
import gen7 as G  # noqa: E402
import prompts7 as PR  # noqa: E402

S0B_RAW = DATA / "samples_raw_s0b.jsonl"


def unit_tests(model, tok) -> dict:
    from engine4 import u_stream
    res: dict = {}
    p = PR.twin("T10", "W1")
    # U1 CRN determinism: the same 4 slots twice give identical token ids
    pre = E.prefill(model, p["ids"])
    g = [{"pre": pre, "us": [u_stream("T10", "W1", k) for k in range(8)]}]
    r1 = E.sample(model, tok, g, "bench", 1024)
    r2 = E.sample(model, tok, g, "bench", 1024)
    res["U1_crn_determinism"] = {"identical": all(a["token_ids"] == b["token_ids"] for a, b in zip(r1, r2)),
                                 "n_rows": len(r1)}
    # U2 batch invariance: B = 1 vs B = 8 for the first 4 rows
    same = []
    for k in range(4):
        rb = E.sample(model, tok, [{"pre": pre, "us": [u_stream("T10", "W1", k)]}], "bench", 1024)
        same.append(rb[0]["token_ids"] == r1[k]["token_ids"])
    res["U2_batch_invariance_B1_vs_B8"] = {"identical": same, "note": "exp29 found invariance for B >= 3 only"}
    # U3 hook identity: push at alpha 0 equals the clean prefill bit for bit
    from ctx4 import ban_unit, push_spec, rand_dir
    from hooks4 import make_edits_v4
    ctx = G.Ctx(model, "T10", PR.p4())
    tw = ctx.twin("W1")
    sp = push_spec(ctx.dev, rand_dir(9101), ban_unit("T10"), 0.0)
    ed = make_edits_v4("TARGET", tw["a"], tw["b"], sp["U"], sp["M"], {l: tw["S"][l] for l in sp["U"]})
    pre0 = E.prefill(model, tw["prompt"]["ids"], edits=ed)
    same_kv = all(torch.equal(a[0], b[0]) and torch.equal(a[1], b[1]) for a, b in zip(pre0["kv"], tw["pre"]["kv"]))
    res["U3_hook_identity_alpha0"] = {"kv_bitwise_equal": bool(same_kv),
                                      "r_logits_equal": bool(torch.equal(pre0["r_logits"], tw["pre"]["r_logits"]))}
    # U5 teacher-forced next-token log-probs vs the KV-cache path at the same prefix
    ids = r1[0]["token_ids"]
    f = min(12, len(ids) - 1)
    lp_tf = E.forward_lp(model, [p["ids"] + ids[:f]], [len(p["ids"]) + f - 1])[0, 0]
    pre_f = E.prefill(model, p["ids"] + ids[:f])
    lp_kv = torch.log_softmax(pre_f["r_logits"].float(), -1)
    res["U5_teacher_forced_vs_prefill"] = {"max_abs_logprob_diff_top50": float(
        (lp_tf[lp_kv.topk(50).indices] - lp_kv[lp_kv.topk(50).indices]).abs().max()),
        "argmax_equal": int(lp_tf.argmax()) == int(lp_kv.argmax()), "position": f}
    ctx.release()
    res["U8_memory"] = {"peak_gib": torch.cuda.max_memory_allocated() / 2 ** 30,
                        "free_gib": torch.cuda.mem_get_info(0)[0] / 2 ** 30}
    return res


def stage_0a(model, tok, tasks=("T2", "T03", "T10", "T1")) -> None:
    for task in tasks:
        ctx = G.Ctx(model, task, PR.p4())
        G.run_cells(model, tok, ctx, {}, [("TWIN", list(range(6)))], "S0a_twin")
        ctx.release()


def stage_0b(model, tok) -> list[dict]:
    """POP 9101-9105 at alpha 2, exp29 screen slots (k 0-1), rows to samples_raw_s0b.jsonl (sealed)."""
    recs = []
    orig_raw = G.RAW
    G.RAW = S0B_RAW
    try:
        for task in ("T10", "T2"):
            ctx = G.Ctx(model, task, PR.p4())
            arms = {}
            for s in SEEDS_STAGE0:
                arm = G.pop_arm(s, 2.0, task)
                arms[arm.name] = arm
            G.run_cells(model, tok, ctx, arms, [(a, [0, 1]) for a in arms], "S0b_pop")
            ctx.release()
    finally:
        G.RAW = orig_raw
    return recs


def stage_0c() -> dict:
    """Realised displacement norms of the 5 directions (this engine) vs exp29 engine-d realised_disp.jsonl."""
    mine = {}
    for r in read_jsonl(S0B_RAW):
        if r.get("realised_disp") and r["family"] == "POP":
            mine[(r["task"], r["template"], int(r["direction_seed"]))] = r["realised_disp"]
    theirs = {}
    for r in read_jsonl(IN29 / "realised_disp.jsonl"):
        if r.get("engine") == "d" and r.get("arm", "").startswith("POP_d") and r.get("arm", "").endswith("_a2.0"):
            key = (r["task"], r["template"], int(r["direction_seed"]))
            if key in mine and key not in theirs:
                theirs[key] = r
    rows = []
    for key, m in mine.items():
        t = theirs.get(key)
        if not t:
            continue
        S = t["disp_smean_norm"]
        rel = {f"b{b}": abs(m[f"S_b{b}"] - S[str(b)] if isinstance(S, dict) and str(b) in S else
                            m[f"S_b{b}"] - S[b]) / max(S[str(b)] if isinstance(S, dict) and str(b) in S else S[b],
                                                         1e-9) for b in (12, 23, 35)}
        rows.append({"task": key[0], "template": key[1], "seed": key[2], **{f"mine_b{b}": m[f"S_b{b}"]
                                                                              for b in (12, 23, 35)}, "rel": rel})
    mx = {b: max([r["rel"][f"b{b}"] for r in rows], default=None) for b in (12, 23, 35)}
    return {"n": len(rows), "max_rel_diff": mx, "pass_2pct": all(v is not None and v < 0.02 for v in mx.values()),
            "rows": rows}


def main() -> None:
    setup_logging("stage0")
    t0 = time.time()
    tok, model = E.load()
    write_json(PRED / "hardware.json", {**E.hardware_info(model), "batch": G.B_TASK, "max_new": common.MAX_NEW,
                                        "plan_gpu": "RTX A4500 (plan) -> RTX 4090 (this run; logged deviation)"})
    logger.info(f"model loaded in {time.time() - t0:.0f}s")
    ut = unit_tests(model, tok)
    write_json(RESULTS / "unit_tests_gpu.json", ut)
    logger.info(f"unit tests: {ut}")
    stage_0a(model, tok)
    stage_0b(model, tok)
    rc = stage_0c()
    write_json(RESULTS / "engine_check_norms.json", rc)
    logger.info(f"0c realised norms: n {rc['n']} max rel {rc['max_rel_diff']} pass {rc['pass_2pct']}")
    write_json(RESULTS / "stage0_done.json", {"utc": utc_now(), "seconds": time.time() - t0})


if __name__ == "__main__":
    main()
