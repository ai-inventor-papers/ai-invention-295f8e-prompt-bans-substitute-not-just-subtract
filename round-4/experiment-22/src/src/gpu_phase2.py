#!/usr/bin/env python3
"""GPU phase 2 (after the commit): S5 sampling stages, labelled concurrently by src/label4.py.

Order (never-drop items first; plan drop order applied against the deadline):
  A  twins          movable k 0-9 (N = 50; T03/T2 reuse the engine-check twin rows), others k 0-5 (N = 30)
  B  population     6 movable tasks x 40 directions (9101-9140) x alpha {1, 2} x k 0-1 (N = 10)
  C  confirmation   every (task, direction, alpha) passing the N = 10 screen gets k 2-5 (+20)
  D  9-task escape  directions 9101-9108 x alpha {2, 1} x k 0-1 on T04 T08 T11 T13 T14 R1 R3 R6 R2, + confirmations
  E  decomposition  up to 4 confirmed escaping directions per movable task: UPERP and UP at their escaping alpha,
                    k 0-3 (N = 20); the list is committed (addendum) before E runs
  F  C2c            C2C_r_s0.5 (N = 50) + C2C_rand<930x>_s0.5 (N = 50) [never drop]; then r_s0.25, r_s1.0 (N = 30),
                    rm_s0.5, r2_s0.5 (N = 30)
  G  sweep          SWEEP_r_a4.0, SWEEP_r_a8.0 (N = 30)
  H  CLAMP          extension on the decomposition list (N = 20), only if time remains
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))

import torch  # noqa: E402
from loguru import logger  # noqa: E402

from cfg4 import (ALPHAS_POP, ALPHAS_SWEEP, DEFAULT4, K, LABELS, MOVABLE, OTHER9, PRED_DIR, RAW, RESULTS_DIR,  # noqa: E402
                  SEEDS_C2C, SEEDS_OTHER, SEEDS_POP, STATES_DIR, TEMPLATE_IDS, TIMING, read_jsonl, setup_logging,
                  utc_now, write_json)
from commit4 import commit  # noqa: E402
from common import join_rows  # noqa: E402
from c2a import direction_table  # noqa: E402
from screen import catalogue  # noqa: E402


def per_w(cells: list[tuple[str, list[int]]]) -> dict[str, list[tuple[str, list[int]]]]:
    return {w: list(cells) for w in TEMPLATE_IDS}


def task_rows(task: str) -> list[dict[str, Any]]:
    raw = [r for r in read_jsonl(RAW) if r["task"] == task]
    lab = [l for l in read_jsonl(LABELS) if l["task"] == task]
    return join_rows(raw, lab)


def wait_labels(task: str, arm_prefix: tuple[str, ...], timeout: float = 900) -> None:
    t0 = time.time()
    while time.time() - t0 < timeout:
        raw = {f"{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}" for r in read_jsonl(RAW)
               if r["task"] == task and r["arm"].startswith(arm_prefix)}
        lab = {l["key"] for l in read_jsonl(LABELS) if l["task"] == task}
        missing = raw - lab
        if not missing:
            return
        logger.info(f"waiting for {len(missing)} labels of {task} {arm_prefix}")
        time.sleep(20)
    logger.warning(f"label wait timed out for {task} {arm_prefix}")


def twin_kmax(task: str) -> int:
    return len(K["twin_mov"]) if task in MOVABLE else len(K["twin_oth"])


def passers(task: str, seeds: list[int]) -> list[tuple[int, float]]:
    rows = [r for r in task_rows(task) if not (r["arm"] == "TWIN" and int(r["sample_id"]) >= twin_kmax(task))]
    tab = direction_table(rows, seeds, set(catalogue(task)), DEFAULT4[task])
    return [(s, float(a)) for s in seeds for a in ("1.0", "2.0") if tab[s][a]["screen_pass"]]


def confirmed(task: str, seeds: list[int]) -> list[dict[str, Any]]:
    rows = [r for r in task_rows(task) if not (r["arm"] == "TWIN" and int(r["sample_id"]) >= twin_kmax(task))]
    tab = direction_table(rows, seeds, set(catalogue(task)), DEFAULT4[task])
    out = []
    for s in seeds:
        for a in ("1.0", "2.0"):
            if tab[s][a]["confirmed"]:
                out.append({"seed": s, "alpha": float(a), "excess_pooled": tab[s][a]["excess_pooled"]})
    return out


def sec_per_batch(task: str) -> float:
    t = [r["seconds"] for r in read_jsonl(TIMING) if r["task"] == task]
    return sum(t) / len(t) if t else 15.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deadline-min", type=float, default=170.0, help="GPU sampling budget in minutes from now")
    ap.add_argument("--stages", default="A,B,C,D,E,F,G,H")
    args = ap.parse_args()
    setup_logging("gpu_phase2")
    from cfg4 import COMMIT_LOG
    assert COMMIT_LOG.exists() and (PRED_DIR / "c2_commit.json").exists(), "commit must precede population sampling"
    t_start = time.time()
    deadline = t_start + args.deadline_min * 60
    stages = args.stages.split(",")
    from engine4 import load_model
    from prompts4 import load_prompts4
    from sampling4 import run_cells

    torch.cuda.set_per_process_memory_fraction(0.97, 0)
    tok, model = load_model()
    prompts = load_prompts4()
    log: dict[str, Any] = {"start_utc": utc_now(), "stages": {}, "not_run": []}

    def run(task, cells, stage, dl=None):
        n = run_cells(model, tok, prompts, task, cells, stage, deadline=dl or deadline)
        log["stages"].setdefault(stage, {})[task] = log["stages"].get(stage, {}).get(task, 0) + n
        write_json(RESULTS_DIR / "phase2_log.json", log)
        return n

    def remaining_min() -> float:
        return (deadline - time.time()) / 60

    if "B" in stages:
        for t in MOVABLE:   # A merged into B: twin k 0-9 shares batches with the population cells
            run(t, per_w([("TWIN", K["twin_mov"])] + [(f"POP_d{s}_a{a}", K["pop"]) for s in SEEDS_POP
                                                       for a in ALPHAS_POP]), "B_pop")
            if t == "T2":
                spb = {tt: sec_per_batch(tt) for tt in MOVABLE}
                write_json(RESULTS_DIR / "budget_decision.json",
                           {"utc": utc_now(), "sec_per_batch_so_far": spb, "remaining_min": remaining_min(),
                            "note": "B continues for all movable tasks (never drop); later stages are checked "
                                    "against the deadline in the committed drop order"})
    if "D" in stages:
        for t in OTHER9:    # A merged into D: twin k 0-6 + both alphas fill whole batches (alpha 1 costs no extra)
            run(t, per_w([("TWIN", K["twin_oth"])] + [(f"POP_d{s}_a{a}", K["pop"]) for a in (2.0, 1.0)
                                                       for s in SEEDS_OTHER]), "D_other")
    if "C" in stages:
        for t in MOVABLE:
            wait_labels(t, ("POP", "TWIN"))
            ps = passers(t, SEEDS_POP)
            log.setdefault("passers", {})[t] = ps
            run(t, per_w([(f"POP_d{s}_a{a}", K["topup"]) for s, a in ps]), "C_confirm")
    if "D" in stages:
        for t in OTHER9:
            wait_labels(t, ("POP", "TWIN"), timeout=300)
            ps = passers(t, SEEDS_OTHER)
            log.setdefault("passers_other", {})[t] = ps
            if ps and remaining_min() > 15:
                run(t, per_w([(f"POP_d{s}_a{a}", K["topup"]) for s, a in ps]), "D_confirm")
    dlist: dict[str, list[dict[str, Any]]] = {}
    if "E" in stages:
        for t in MOVABLE:
            wait_labels(t, ("POP", "TWIN"))
            conf = sorted(confirmed(t, SEEDS_POP), key=lambda r: -r["excess_pooled"])
            seen, pick = set(), []
            for c in conf:
                if c["seed"] in seen:
                    continue
                seen.add(c["seed"])
                pick.append(c)
                if len(pick) == 4:
                    break
            dlist[t] = pick
        p = PRED_DIR / "decomp_list.json"
        write_json(p, {"utc": utc_now(), "rule": "up to 4 confirmed escaping directions per movable task, largest "
                                                  "pooled excess first, at their escaping alpha", "list": dlist})
        commit([p], "addendum_decomposition_list")
    if "E" in stages or "F" in stages:
        for t in MOVABLE:   # E + F core share batches
            cells = []
            for c in dlist.get(t, []):
                cells += [(f"UPERP_d{c['seed']}_a{c['alpha']}", K["decomp"]),
                          (f"UP_d{c['seed']}_a{c['alpha']}", K["decomp"])]
            if "F" in stages:
                cells += [("C2C_r_s0.5", K["k50"]), (f"C2C_rand{SEEDS_C2C[t]}_s0.5", K["k50"])]
            if cells:
                run(t, per_w(cells), "EF_decomp_c2c_core")
    if "F" in stages or "G" in stages:
        extra = []
        if "F" in stages:
            extra += [("C2C_r_s0.25", K["k30"]), ("C2C_r_s1.0", K["k30"]), ("C2C_rm_s0.5", K["k30"]),
                      ("C2C_r2_s0.5", K["k30"])]
        if "G" in stages:
            extra += [("SWEEP_r_a4.0", K["k30"]), ("SWEEP_r_a8.0", K["k30"])]
        drop_order = ["SWEEP_r_a8.0", "C2C_r2_s0.5", "C2C_rm_s0.5"]
        for t in MOVABLE:
            cells = list(extra)
            est = sec_per_batch(t) * 5 * 2 / 60
            for d in drop_order:
                if remaining_min() < est + 5 and any(a == d for a, _ in cells):
                    cells = [c for c in cells if c[0] != d]
                    log["not_run"].append(f"{d} {t} (deadline)")
                    est = sec_per_batch(t) * 5 * max(1, round(len(cells) * 6 / 20 + 0.49)) / 60
            if cells and remaining_min() > 4:
                run(t, per_w(cells), "FG_c2c_extra_sweep")
            elif cells:
                log["not_run"] += [f"{a} {t} (deadline)" for a, _ in cells]
    if "H" in stages:
        for t in MOVABLE:
            if remaining_min() < sec_per_batch(t) * 5 / 60 + 3:
                log["not_run"].append(f"H CLAMP {t} (deadline)")
                continue
            cells = [(f"CLAMP_d{c['seed']}_a{c['alpha']}", K["decomp"]) for c in dlist.get(t, [])]
            if cells:
                run(t, per_w(cells), "H_clamp")
    log["end_utc"] = utc_now()
    log["minutes"] = (time.time() - t_start) / 60
    write_json(RESULTS_DIR / "phase2_log.json", log)
    logger.info(f"phase 2 done in {log['minutes']:.1f} min; not run: {log['not_run']}")


if __name__ == "__main__":
    main()
