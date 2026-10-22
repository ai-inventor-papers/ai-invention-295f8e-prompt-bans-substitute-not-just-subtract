#!/usr/bin/env python3
"""S8: the causal arm. Per causal task (commit #3), every cell is 30 CRN-paired rows (W1-W5 x slots 0-5):
  PRE_{EDIT,RT,UNREL,RAND,DIM}_x{1,2,4}: per-template deltas added at SPEC-3..SPEC-1 and READ during prefill only;
  GEN_{EDIT,RAND}_x{1,2}: READ's delta added at READ (prefill) and at generated positions 1-64;
  REV_{EDIT,RAND}_x{2,4}: on ban prompts, the reverse edit (Y* -> default) where a ban explanation names Y*.
The hook sits on the block whose output is hidden_states[convention] (commit #3 patch_block). A read-back check logs
||h_patched - h|| against the target per row; downstream ||h_patched - h_twin|| at READ for blocks patch..27 is
logged once per (task, cell, template). Staged: a 10-slot pilot of the first task's EDIT x2 cell, then the full queue
in the drop order (REV first, then GEN) if time runs short.

Usage: python src/causal_gen.py [--deadline-min N]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import (CACHE_DIR, CAUSAL_SLOTS, DATA_DIR, GEN_STEPS, POS_OFFSET, PRED_DIR, RESULTS_DIR, TEMPLATE_IDS,
                 append_jsonl, read_json, read_jsonl, set_ram_limit, setup_logging, utc_now, write_json)
from engine import DeltaEdit, capture_states, load_model, unload
from gen import run_specs, spec_row

RAW = DATA_DIR / "samples_causal_raw.jsonl"
DOWN = RESULTS_DIR / "causal_downstream.jsonl"
POS4 = ("SPEC-3", "SPEC-2", "SPEC-1", "READ")


def load_deltas() -> dict[str, np.ndarray]:
    z = np.load(CACHE_DIR / "deltas.npz")
    return {k.replace("__", "|"): z[k] for k in z.files}


def cell_specs(t: str, cell: str, deltas: dict[str, np.ndarray], tw: dict, bn: dict, D: int = 3584
               ) -> list[dict[str, Any]]:
    fam, kind, dt = cell.split("_")
    dose = float(dt[1:])
    out = []
    for w in TEMPLATE_IDS:
        if fam == "PRE":
            pre = {POS_OFFSET[p]: deltas[f"{kind}|{t}|TWIN|{w}|{p}"] * dose for p in POS4}
            gen = None
            p = tw[(t, w)]
            ratio = float(np.mean([np.linalg.norm(deltas[f"{kind}|{t}|TWIN|{w}|{q}"]) for q in POS4]))
        elif fam == "GEN":
            k2 = "EDIT" if kind == "EDIT" else "RAND"
            dR = deltas[f"{k2}|{t}|TWIN|{w}|READ"] * dose
            pre, gen = {1: dR}, dR
            p = tw[(t, w)]
            ratio = float(np.linalg.norm(dR))
        else:  # REV
            k2 = "REV" if kind == "EDIT" else "RAND"
            pre = {}
            for q in POS4:
                key = f"{k2}|{t}|REVERSE|{w}|{q}"
                if key in deltas:
                    pre[POS_OFFSET[q]] = deltas[key] * dose
            if not pre:
                continue
            gen = None
            p = bn[(t, w)]
            ratio = float(np.mean([np.linalg.norm(v) for v in pre.values()]))
        for k in CAUSAL_SLOTS:
            s = spec_row(p, "CAUSAL", k, cell=f"{cell}", site=fam if fam != "REV" else "PRE", alpha=dose,
                         edit_class=kind, state_ids=[f"{t}|{w}|{q}" for q in POS4], delta_norm_ratio=ratio)
            s["sample_id"] = f"{t}|{cell}|-|{w}|{k}"
            s["pre"] = {o: v.astype(np.float32) for o, v in pre.items()}
            if gen is not None:
                s["gen"] = gen.astype(np.float32)
            out.append(s)
    return out


def downstream(model: Any, t: str, cell: str, specs: list[dict[str, Any]], block: int) -> None:
    done = {(r["task"], r["cell"], r["template"]) for r in read_jsonl(DOWN)}
    seen = set()
    for s in specs:
        w = s["p"]["w"]
        if (t, cell, w) in done or w in seen:
            continue
        seen.add(w)
        ids = s["p"]["ids"]
        P = len(ids)
        blocks = list(range(block, 28))
        import torch
        pre = {o: torch.tensor(v[None], device=model.device) for o, v in s["pre"].items()}
        base = capture_states(model, ids, blocks, [P - 1])
        ed = DeltaEdit(pre=pre)
        pat = capture_states(model, ids, blocks, [P - 1], edit=ed, edit_block=block)
        rec = {"task": t, "cell": cell, "template": w, "utc": utc_now(),
               "disp_read": {str(b): float(np.linalg.norm(pat[b][0] - base[b][0])) for b in blocks},
               "norm_read": {str(b): float(np.linalg.norm(base[b][0])) for b in blocks},
               "readback_max_relerr": max(ed.readback) if ed.readback else None}
        append_jsonl(DOWN, [rec])


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deadline-min", type=float, default=80.0)
    ap.add_argument("--tasks", nargs="*", default=None)
    args = ap.parse_args()
    setup_logging("causal_gen")
    set_ram_limit(60)
    c3 = read_json(PRED_DIR / "commit3_causal.json")
    block = int(c3["patch_block"])
    deltas = load_deltas()
    st = {(r["task"], r["w"]): r for r in read_jsonl(DATA_DIR / "prompts_static.jsonl") if r["kind"] == "twin"}
    bn = {(r["task"], r["w"]): r for r in read_jsonl(DATA_DIR / "prompts_ban.jsonl")}
    tok, model = load_model()
    t_start = time.time()
    deadline = t_start + args.deadline_min * 60
    plan = c3["causal_plan"] if not args.tasks else [p for p in c3["causal_plan"] if p["task"] in args.tasks]
    order = ["PRE_EDIT_x2", "PRE_RT_x2", "PRE_EDIT_x1", "PRE_RT_x1", "PRE_EDIT_x4", "PRE_RT_x4",
             "PRE_UNREL_x2", "PRE_RAND_x2", "PRE_UNREL_x1", "PRE_RAND_x1", "PRE_UNREL_x4", "PRE_RAND_x4",
             "PRE_DIM_x2", "PRE_DIM_x4", "PRE_DIM_x1",
             "GEN_EDIT_x1", "GEN_EDIT_x2", "GEN_RAND_x1", "GEN_RAND_x2",
             "REV_EDIT_x2", "REV_EDIT_x4", "REV_RAND_x2", "REV_RAND_x4"]
    not_run = []
    # pilot: 10 slots of the first task's EDIT x2 (programs must stay valid, or the dose grid is recorded as breaking)
    first = plan[0]["task"]
    pil = cell_specs(first, "PRE_EDIT_x2", deltas, st, bn)[:10]
    for s in pil:
        s["sample_id"] = s["sample_id"].replace("PRE_EDIT_x2", "PILOT_EDIT_x2")
        s["cell"] = "PILOT_EDIT_x2"
    run_specs(model, tok, pil, "causal_pilot", out_path=RAW, edit_block=block)
    timing = {"pilot_seconds": round(time.time() - t_start, 1)}
    for ct in plan:
        t = ct["task"]
        pairs = [order[i:i + 2] for i in range(0, len(order), 2)]  # two 30-row cells per 60-row batch
        for pair in pairs:
            if time.time() > deadline:
                not_run += [{"task": t, "cell": c, "reason": "deadline"} for c in pair]
                continue
            specs, cells_run = [], []
            for cell in pair:
                cs = cell_specs(t, cell, deltas, st, bn)
                if not cs:
                    not_run.append({"task": t, "cell": cell, "reason": "no deltas (no ban explanation names Y)"})
                    continue
                specs += cs
                cells_run.append(cell)
            if not specs:
                continue
            t0 = time.time()
            run_specs(model, tok, specs, f"causal:{t}:{'+'.join(cells_run)}", out_path=RAW, edit_block=block,
                      batch_cap=60)
            for cell in cells_run:
                if cell.startswith(("PRE", "REV")):
                    downstream(model, t, cell, [s for s in specs if s["cell"] == cell], block)
            timing[f"{t}:{'+'.join(cells_run)}"] = round(time.time() - t0, 1)
            logger.info(f"{t} {cells_run}: {len(specs)} rows in {time.time() - t0:.0f}s; elapsed "
                        f"{(time.time() - t_start) / 60:.1f} min")
    write_json(RESULTS_DIR / "causal_run.json", {"timing": timing, "not_run": not_run, "patch_block": block,
                                                 "gen_steps": GEN_STEPS, "deadline_min": args.deadline_min})
    (DATA_DIR / "flag_causal.done").write_text(utc_now())
    unload(model)


if __name__ == "__main__":
    main()
