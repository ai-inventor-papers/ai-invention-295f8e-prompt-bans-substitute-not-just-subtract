#!/usr/bin/env python3
"""GPU process on weight set Q (e4m3 weights on the GPU; engines a, a_emul, b).

--phase q1 : hardware record, U1/U2/U3/U4/U5 for a (and U4 for b), REPRO (engine a: T10, T2 twins k 0-9 + directions
             9101-9110 at alpha 2, k 0-1, B = 20) with per-slot BYTE identity against exp22's rows, and the exp19 PN
             byte check (PN_a1/PN_a2, W1 k 0-9, T10 and T2). Then exits so the bf16 weight set can use the card.
--phase q2 : engine b stages (twins, POP alpha 2 screen + confirmation, POSCTRL, PN), engine-a gap filling, the
             B-sensitivity control (engine a at the weight-set-B batch size) and teacher-forced diagnostics.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import torch  # noqa: E402
from loguru import logger  # noqa: E402

import c6  # noqa: E402,F401
from c6 import (E19, E22, K_SCREEN, K_TWIN, PRED, REPRO_SEEDS, RESULTS, read_jsonl, setup_logging,  # noqa: E402
                    utc_now, write_json, read_json)


def byte_identity_vs(engine_rows: list[dict[str, Any]], ref: dict[tuple, list[int]]) -> dict[str, Any]:
    n = same = 0
    first_div = []
    per_cell: dict[str, list[int]] = {}
    for r in engine_rows:
        k = (r["task"], r["template"], r["arm"], int(r["sample_id"]))
        if k not in ref:
            continue
        n += 1
        a, b = r["token_ids"], ref[k]
        eq = a == b
        same += eq
        cell = f"{r['task']}|{r['arm']}"
        per_cell.setdefault(cell, [0, 0])
        per_cell[cell][0] += 1
        per_cell[cell][1] += eq
        if not eq:
            j = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
            first_div.append(j)
    return {"n_paired": n, "n_byte_identical": same, "frac_identical": same / n if n else None,
            "first_divergence_positions": sorted(first_div)[:50], "per_cell": per_cell}


def phase_q1() -> None:
    import engines as EN
    import gpu_tests6 as GT
    from gen import Runner, raw_path
    from prompts4 import load_prompts4

    hw = GT.env_record()
    hw["A_IMPL"] = "native" if tuple(hw["cc"]) >= (8, 9) else "emulated"
    hw["utc"] = utc_now()
    hw["cgroup_cpu_quota"] = 5.1
    write_json(PRED / "hardware.json", hw)
    logger.info(f"hardware {hw}")
    tok, model = EN.load_q()
    prompts = load_prompts4()
    ut: dict[str, Any] = {"utc": utc_now(), "weight_set": "Q"}
    t0 = time.time()
    ut["U2_codes"] = GT.u2_codes()
    ut["U2_weights"] = GT.u2_weights(model)
    ids = prompts["T10|twin|-|W1|-"]["ids"]
    ut["U1"] = GT.u1(model, ids)
    logger.info(f"U1 {ut['U1']['summary']}")
    ut["U4_a"] = GT.u4(model, prompts, "a")
    ut["U4_b"] = GT.u4(model, prompts, "b")
    ut["U3_U5_a"] = GT.u3_u5(model, tok, prompts, "a", B=20)
    ut["seconds"] = time.time() - t0
    write_json(RESULTS / "unit_tests_q.json", ut)
    logger.info(f"unit tests Q done in {ut['seconds']:.0f}s: U2 {ut['U2_codes']} U4a {ut['U4_a']} "
                f"U3/U5 {ut['U3_U5_a']}")
    EN.set_mode("a")
    run = Runner(model, tok, prompts, "a", B=20, a_impl="native")
    for task in ("T10", "T2"):
        cells = [("TWIN", K_TWIN)] + [(f"POP_d{s}_a2.0", K_SCREEN) for s in REPRO_SEEDS]
        run.run_cells(task, cells, "REPRO")
    ref = {(r["task"], r["template"], r["arm"], int(r["sample_id"])): r["token_ids"]
           for r in read_jsonl(E22 / "samples_raw.jsonl") if r["task"] in ("T10", "T2")}
    rows = [r for r in read_jsonl(raw_path("a")) if r["stage"] == "REPRO"]
    rep = {"utc": utc_now(), "B": 20, "a_impl": "native", "vs_exp22": byte_identity_vs(rows, ref)}
    logger.info(f"REPRO byte identity vs exp22: {rep['vs_exp22']['n_byte_identical']}/{rep['vs_exp22']['n_paired']}")
    # exp19 PN byte check (same engine family, same slots, same per-sample direction seeds)
    for task in ("T10", "T2"):
        run.run_cells(task, [("PN_a1", list(range(10))), ("PN_a2", list(range(10)))], "PN_check", templates=("W1",))
    ref19 = {(r["task"], r["template"], r["arm"], int(r["slot"])): r["token_ids"]
             for r in read_jsonl(E19 / "samples_raw.jsonl") if r["task"] in ("T10", "T2")
             and r["arm"] in ("PN_a1", "PN_a2")}
    rows = [r for r in read_jsonl(raw_path("a")) if r["stage"] == "PN_check"]
    rep["pn_vs_exp19"] = byte_identity_vs(rows, ref19)
    logger.info(f"PN byte identity vs exp19: {rep['pn_vs_exp19']['n_byte_identical']}/{rep['pn_vs_exp19']['n_paired']}")
    write_json(RESULTS / "repro_bytes.json", rep)
    logger.info("phase q1 done")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="q1")
    ap.add_argument("--deadline-min", type=float, default=60.0)
    args = ap.parse_args()
    setup_logging(f"gpu_{args.phase}")
    torch.backends.cuda.matmul.allow_tf32 = False
    if args.phase == "q1":
        phase_q1()
    else:
        import gpu_q2
        gpu_q2.main(args.deadline_min)


if __name__ == "__main__":
    main()
