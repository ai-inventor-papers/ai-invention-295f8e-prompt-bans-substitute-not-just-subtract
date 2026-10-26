#!/usr/bin/env python3
"""GPU sessions (one model on the GPU at a time; labelling runs on the CPU concurrently).

Phases (run in the order given on the command line; all phases of one invocation must use the same model):
  tests        U1 CRN determinism, U2 alpha = 0 push == twin, U3 realised displacement, U4 prompt-id identity
  engine       engine check: T03 x rand_9002 and T2 x rand_9004 at alpha 1 in exp17's ban unit + twins (k 0-9)
  inst1        per unit: twin (k 0-9) + gate draw (k 100-101), novelty (N = 30), association (20 per mode)
  base1        per unit: base chat (W1-W5 x k 0-19) + plain completion (k 0-49)          [model: base]
  margins      per unit: teacher-forced opening log-probs of every catalogue reference (R_margin)
  push         per unit (commit verified first): escape stage 1 -> PN alpha 1 -> PN alpha 2 -> T1.3, then
               confirmations of every stage-1 passer once its labels exist
  confirm      confirmations only
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import torch  # noqa: E402
from loguru import logger  # noqa: E402

from cfg5 import (ALPHAS, BASE_ID, BASE_REVISION, K, MODEL_ID, MODEL_REVISION, N_ASSOC, N_DIRS, N_NOVELTY,  # noqa: E402
                  N_PLAIN, RESULTS_DIR, TEMPLATE_IDS, VENDOR, direction_seed, read_json, read_jsonl, setup_logging,
                  utc_now, write_json)


def per_w(cells: list[tuple[str, list[int]]]) -> dict[str, list[tuple[str, list[int]]]]:
    return {w: list(cells) for w in TEMPLATE_IDS}


def exp17_prompts() -> dict[str, dict[str, Any]]:
    out = {}
    for r in read_jsonl(VENDOR / "exp17" / "prompts" / "prompts.jsonl"):
        if r["task"] in ("T03", "T2") and r["kind"] == "twin":
            pid = f"{r['task']}|twin|-|{r['w']}"
            out[pid] = {"pid": pid, "unit": r["task"], "kind": "twin", "template_id": r["w"], "ids": r["ids"],
                        "P": r["P"], "p0": r["p0"], "p1": r["p1"], "spec_end": r["spec_end"],
                        "prompt_sha256": r["prompt_sha256"], "segment": r["segment"], "user_text": r["user_text"]}
    return out


def phase_tests(runner, units: list[str]) -> dict[str, Any]:
    from engine5 import sample, u_stream
    from sampling5 import u_key
    u = units[0]
    w = "W1"
    ctx = runner.unit_ctx(u, False)
    tw = ctx.twin(w)
    res: dict[str, Any] = {"utc": utc_now(), "unit": u, "template": w}
    us = [u_stream(*u_key(u, w, "TWIN", k, False)) for k in range(80, 100)]
    a = sample(runner.model, runner.tok, [{"pre": tw["pre"], "us": us}], fence="bench")
    b = sample(runner.model, runner.tok, [{"pre": tw["pre"], "us": us}], fence="bench")
    res["U1_crn_determinism"] = {"n": 20, "identical": sum(x["token_ids"] == y["token_ids"] for x, y in zip(a, b)),
                                 "pass": all(x["token_ids"] == y["token_ids"] for x, y in zip(a, b))}
    from ctx5 import rand_dir
    pre0, rec0 = ctx.arm_prefill(w, ctx.push_spec(w, rand_dir(direction_seed(u, 0)), 0.0))
    c = sample(runner.model, runner.tok, [{"pre": tw["pre"], "us": us[:10]}, {"pre": pre0, "us": us[:10]}],
               fence="bench")
    same = sum(c[i]["token_ids"] == c[10 + i]["token_ids"] for i in range(10))
    res["U2_alpha0_equals_twin"] = {"n": 10, "identical": same, "pass": same == 10,
                                    "kv_max_abs_diff": float(max((pre0["kv"][l][0] - tw["pre"]["kv"][l][0]).abs().max()
                                                                 for l in range(len(pre0["kv"]))))}
    recs = {}
    for alpha in (1.0, 2.0):
        _, rec = ctx.arm_prefill(w, ctx.push_spec(w, rand_dir(direction_seed(u, 1)), alpha))
        recs[str(alpha)] = {"rel_err_max": rec["rel_err_max"], "disp_R_norm_23": rec["disp_R_norm"][23],
                            "disp_R_norm_35": rec["disp_R_norm"][35], "target_mean": rec["target_mean"]}
    res["U3_realised_displacement"] = {"by_alpha": recs, "threshold_rel": 1e-3,
                                       "pass": all(v["rel_err_max"] < 1e-3 for v in recs.values()),
                                       "note": "realised displacement is read from the bf16 block output after the "
                                               "fp32 edit is cast back to bf16"}
    # U4: base/instruct prompt-id identity is asserted on CPU (src/prompts5 build + tests/test_cpu.py); the
    # decoded task-spec span equals spec_text for every unit/template (asserted when prompts are built).
    res["U4_prompt_ids"] = {"pass": True, "how": "asserted at prompt build: base tokenizer re-encodes every rendered "
                                                 "prompt to identical ids; spec span decodes to spec_text"}
    n = tw["n"].cpu().numpy()
    res["unit_n_summary"] = {"block12_mean": float(n[0].mean()), "block23_mean": float(n[-1].mean())}
    write_json(RESULTS_DIR / "unit_tests_gpu.json", res)
    logger.info(f"GPU tests: {json.dumps({k: v.get('pass') for k, v in res.items() if isinstance(v, dict)})}")
    return res


def phase_engine(runner, deadline: float) -> None:
    for task, seed in (("T03", 9002), ("T2", 9004)):
        runner.run_cells(task, per_w([("TWIN", K["twin"]), (f"SCR_d{seed}_a1.0", K["twin"])]), "engine_check",
                         deadline=deadline, engine_check=True)
    runner.release()


def phase_inst1(runner, units: list[str], deadline: float) -> None:
    from units_spec import catalogue
    for u in units:
        runner.run_cells(u, per_w([("TWIN", K["twin"]), ("GATE", K["gate"])]), "inst1_twin", deadline=deadline)
        runner.run_cells(u, {"NOV": [("NOV", list(range(N_NOVELTY)))]}, "inst1_novelty", deadline=deadline)
        runner.run_cells(u, {"ASSOC": [(f"ASSOC_{m}", list(range(N_ASSOC))) for m in catalogue(u)]}, "inst1_assoc",
                         deadline=deadline)
        runner.release()


def phase_base1(runner, units: list[str], deadline: float, n_base: int = 20, n_plain: int = N_PLAIN) -> None:
    for u in units:
        runner.run_cells(u, per_w([("BASE", list(range(n_base)))]), "base1_chat", deadline=deadline)
        runner.release()
    for u in units:
        runner.run_cells(u, {"PLAIN": [("PLAIN", list(range(n_plain)))]}, "base1_plain", deadline=deadline)


def phase_extra_inst(runner, pairs: list[str], deadline: float) -> None:
    for t in pairs:
        runner.run_cells(f"P_{t}", per_w([("TWIN", K["twin"])]), "extra_twin_parent", deadline=deadline)
        runner.run_cells(f"V_{t}", per_w([("TWIN", K["twin"]), ("GATE", K["gate"])]), "extra_twin_variant",
                         deadline=deadline)
        runner.release()


def phase_extra_base(runner, pairs: list[str], deadline: float) -> None:
    for t in pairs:
        runner.run_cells(f"P_{t}", per_w([("BASE", list(range(10)))]), "extra_base_parent", deadline=deadline)
        runner.run_cells(f"V_{t}", per_w([("BASE", list(range(20)))]), "extra_base_variant", deadline=deadline)
        runner.release()


def verify_commit(u: str) -> dict[str, Any]:
    from commit5 import verify_unit_commit
    return verify_unit_commit(u)


def phase_push(runner, units: list[str], deadline: float, arms: str) -> None:
    from labels_view import confirm_cells
    for u in units:
        c = verify_commit(u)
        assert c["ok"], f"no verified commit for {u}: {c}"
        seeds = [direction_seed(u, k) for k in range(N_DIRS)]
        if "esc" in arms:
            runner.run_cells(u, per_w([(f"ESC_d{s}_a{a}", K["esc1"]) for a in ALPHAS for s in seeds]), "push_esc1",
                             deadline=deadline)
        if "pn1" in arms:
            runner.run_cells(u, per_w([("PN_a1.0", K["pn"])]), "push_pn1", deadline=deadline)
        if "pn2" in arms:
            runner.run_cells(u, per_w([("PN_a2.0", K["pn"])]), "push_pn2", deadline=deadline)
        if "t13" in arms:
            runner.run_cells(u, per_w([("T13", K["t13"])]), "push_t13", deadline=deadline)
        if "conf" in arms:
            cells = confirm_cells(u, wait_s=600)
            if cells:
                runner.run_cells(u, per_w([(arm, K["conf"]) for arm in cells]), "push_conf", deadline=deadline)
        runner.release()


def phase_confirm(runner, units: list[str], deadline: float) -> None:
    from labels_view import confirm_cells
    for u in units:
        c = verify_commit(u)
        assert c["ok"], f"no verified commit for {u}: {c}"
        cells = confirm_cells(u, wait_s=900)
        if cells:
            runner.run_cells(u, per_w([(arm, K["conf"]) for arm in cells]), "push_conf", deadline=deadline)
        runner.release()


def phase_margins(runner, units: list[str]) -> None:
    from margins import opening_margins
    for u in units:
        opening_margins(runner, u)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=["instruct", "base"], required=True)
    ap.add_argument("--phases", required=True)
    ap.add_argument("--units", default="B1,B2,B3,B4,B5,B6,B7")
    ap.add_argument("--deadline-min", type=float, default=300.0)
    ap.add_argument("--arms", default="esc,pn1,pn2,t13,conf")
    ap.add_argument("--n-base", type=int, default=20)
    ap.add_argument("--n-plain", type=int, default=N_PLAIN)
    ap.add_argument("--tag", default="")
    ap.add_argument("--pairs", default="T03,T10,T05,T06")
    args = ap.parse_args()
    setup_logging(f"gpu_{args.model}{args.tag}")
    deadline = time.time() + args.deadline_min * 60
    from engine5 import load_model
    from prompts5 import load_prompts
    import units_extra  # noqa: F401  (registers P_/V_ cards)
    from sampling5 import Runner

    units = [u for u in args.units.split(",") if u]
    mid, rev = (MODEL_ID, MODEL_REVISION) if args.model == "instruct" else (BASE_ID, BASE_REVISION)
    tok, model = load_model(mid, rev)
    if args.model == "base":
        # identical token ids for both models: prompts are always rendered with the INSTRUCT tokenizer
        from transformers import AutoTokenizer
        from cfg5 import model_path
        tok = AutoTokenizer.from_pretrained(model_path(MODEL_ID, MODEL_REVISION))
    prompts = load_prompts()
    phases = args.phases.split(",")
    if "engine" in phases:
        prompts.update(exp17_prompts())
    runner = Runner(model, tok, args.model, prompts)
    for ph in phases:
        t0 = time.time()
        logger.info(f"=== phase {ph} ({args.model}) units={units}")
        if ph == "tests":
            phase_tests(runner, units)
        elif ph == "engine":
            phase_engine(runner, deadline)
        elif ph == "inst1":
            phase_inst1(runner, units, deadline)
        elif ph == "base1":
            phase_base1(runner, units, deadline, n_base=args.n_base, n_plain=args.n_plain)
        elif ph == "margins":
            phase_margins(runner, units)
        elif ph == "push":
            phase_push(runner, units, deadline, args.arms)
        elif ph == "extra_inst":
            phase_extra_inst(runner, [x for x in args.pairs.split(",") if x], deadline)
        elif ph == "extra_base":
            phase_extra_base(runner, [x for x in args.pairs.split(",") if x], deadline)
        elif ph == "confirm":
            phase_confirm(runner, units, deadline)
        else:
            raise ValueError(ph)
        runner.release()
        logger.info(f"=== phase {ph} done in {time.time() - t0:.0f}s")
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
