#!/usr/bin/env python3
"""GPU phase 2 (after commit #2): S7 ban-condition arms (named ban, SUB_plain / SUB_affine / SUB_rand, head
mean-ablation, T1 W4 top-up), optional extra S5 arms, and S8 state extraction."""

from __future__ import annotations

import time
from typing import Any

import numpy as np
from loguru import logger

from cfg import DATA_DIR, PRED_DIR, RESULTS_DIR, ROOT, SAMPLED_TASKS, read_jsonl, utc_now, write_json


def _raw_by_arm() -> dict[tuple[str, str], list[dict[str, Any]]]:
    labs = {r["key"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl")}
    out: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for r in read_jsonl(DATA_DIR / "samples_raw.jsonl"):
        k = f"{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}"
        r = {kk: vv for kk, vv in r.items() if kk != "text"}
        r["key"] = k
        if k in labs:
            r["label"] = labs[k]["label"]
        out.setdefault((r["task"], r["arm"]), []).append(r)
    return out


def gpu2(deadline: float, optional_until: float) -> None:
    import torch

    from engine import load_model
    from prompts import load_prompts
    from sampling import head_mu, run_task_phase, s5_batches, s7_batches
    from states import stage_states

    log = (ROOT / "commitments.log").read_text() if (ROOT / "commitments.log").exists() else ""
    if " commit2" not in log or not (PRED_DIR / "c2d_landings.json").exists():
        raise SystemExit("commit #2 missing: run `method.py commit2` after the S5 labels")
    tok, model = load_model()
    prompts = load_prompts()
    # C2f: per-head mean o_proj inputs over the task's NEUTRAL programs (ban-free, teacher-forced)
    mus: dict[str, dict[int, np.ndarray]] = {}
    for t in ("T1", "T2"):
        p = RESULTS_DIR / f"head_mu_{t}.npz"
        if not p.exists():
            rows = [r for r in read_jsonl(DATA_DIR / "samples_raw.jsonl") if r["task"] == t and r["arm"] == "NEUTRAL"]
            mu = head_mu(model, prompts, t, rows)
            np.savez(p, **{str(l): v for l, v in mu.items()}, n_programs=len(rows))
            logger.info(f"C2f mu {t}: {len(rows)} NEUTRAL programs")
        z = np.load(p)
        mus[t] = {int(k): z[k] for k in z.files if k != "n_programs"}
    # S7: named ban, SUB arms, head ablation (T1/T2), T1 W4 top-up -- whole tasks in the frozen order
    first_ban = None
    for t in SAMPLED_TASKS:
        if time.time() > deadline:
            logger.warning(f"deadline: S7 stops before {t}")
            break
        first_ban = first_ban or utc_now()
        n = run_task_phase(model, tok, prompts, t, s7_batches(t), "S7", mus=mus.get(t), deadline=deadline)
        logger.info(f"S7 {t}: {n} new batches")
        if t == "T1":
            topup = [[("BAN_TOPUP", list(range(a, a + 20)))] for a in (20, 40, 60)]
            run_task_phase(model, tok, prompts, t, topup, "S7", templates=["W4"], deadline=deadline)
    # optional: ADD alpha 0.5 (+ ADD alpha 1 slots 10-19), drop order item (4)
    for t in SAMPLED_TASKS:
        if time.time() > optional_until:
            break
        run_task_phase(model, tok, prompts, t, s5_batches(optional=True, extra=True), "S5", deadline=optional_until)
    torch.cuda.empty_cache()
    # S8 state extraction
    stage_states(model, prompts, _raw_by_arm(), list(SAMPLED_TASKS), deadline=deadline + 20 * 60)
    write_json(RESULTS_DIR / "gpu2_done.json", {"utc": utc_now(), "first_ban_sample_utc_approx": first_ban})
