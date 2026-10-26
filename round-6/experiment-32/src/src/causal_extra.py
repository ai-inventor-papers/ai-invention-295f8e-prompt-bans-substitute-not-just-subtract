#!/usr/bin/env python3
"""EXPLORATORY (not pre-registered) causal dose extension, run after the committed causal arm returned nulls with
tiny pushes (||delta_edit|| / ||h|| ~ 0.04 per position, x4 ~ 0.16). Same tasks, slots, CRN streams, hook and
patch block as commit #3; new cells only:
  EXP_PRE_{EDIT,RAND,DIM}_x16     the committed deltas x16 (DIM and RAND matched to ||EDIT||)
  EXP_GEN_{EDIT,RAND,DIM}_x8      READ's delta at READ and generated positions 1-64, x8
  EXP_PRE_DIMFULL_x1 / _x2        the forced-state difference in means at its NATURAL norm
                                  (mean_tmpl h_forced(Y) - mean_tmpl h_forced(default), per position), x1 / x2
  EXP_GEN_DIMFULL_x1              the same natural-norm READ direction at READ and generated positions 1-64
A positive DIMFULL effect with a null EDIT means the site can steer the algorithm but the NLA edit direction does
not; a null DIMFULL means the four prefill positions / this layer are inert for the algorithm choice.
Usage: python src/causal_extra.py ; then src/labels.py on data/samples_causal_extra_raw.jsonl
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import (CACHE_DIR, CAUSAL_SLOTS, DATA_DIR, POS_OFFSET, PRED_DIR, RESULTS_DIR, TEMPLATE_IDS, read_json,
                 read_jsonl, set_ram_limit, setup_logging, utc_now, write_json)
from causal_gen import load_deltas
from engine import load_model, unload
from gen import run_specs, spec_row

RAW = DATA_DIR / "samples_causal_extra_raw.jsonl"
POS4 = ("SPEC-3", "SPEC-2", "SPEC-1", "READ")
CELLS = ["EXP_PRE_EDIT_x16", "EXP_PRE_RAND_x16", "EXP_PRE_DIM_x16", "EXP_GEN_EDIT_x8", "EXP_GEN_RAND_x8",
         "EXP_GEN_DIM_x8", "EXP_PRE_DIMFULL_x1", "EXP_PRE_DIMFULL_x2", "EXP_GEN_DIMFULL_x1"]


def dimfull(plan: list[dict[str, Any]], conv: str) -> dict[str, np.ndarray]:
    idx = read_jsonl(CACHE_DIR / "states_index.jsonl")
    z = np.load(CACHE_DIR / "states_L20.npz")
    H = z["H21"] if conv == "hs21" else z["H20"]
    row = {r["state_id"]: r["row"] for r in idx}
    out = {}
    for ct in plan:
        t, D, Y = ct["task"], ct["default"], ct["Y"]
        for p in POS4:
            fY = np.mean([H[row[f"{t}|forced|{Y}|{w}|{p}"]] for w in TEMPLATE_IDS], 0)
            fD = np.mean([H[row[f"{t}|forced|{D}|{w}|{p}"]] for w in TEMPLATE_IDS], 0)
            for w in TEMPLATE_IDS:
                out[f"DIMFULL|{t}|TWIN|{w}|{p}"] = (fY - fD).astype(np.float32)
    return out


def specs_for(t: str, cell: str, deltas: dict[str, np.ndarray], tw: dict) -> list[dict[str, Any]]:
    _, fam, kind, dt = cell.split("_")
    dose = float(dt[1:])
    out = []
    for w in TEMPLATE_IDS:
        p = tw[(t, w)]
        if fam == "PRE":
            pre = {POS_OFFSET[q]: deltas[f"{kind}|{t}|TWIN|{w}|{q}"] * dose for q in POS4}
            gen = None
        else:
            dR = deltas[f"{kind}|{t}|TWIN|{w}|READ"] * dose
            pre, gen = {1: dR}, dR
        h_norm_ratio = float(np.mean([np.linalg.norm(v) for v in pre.values()]))
        for k in CAUSAL_SLOTS:
            s = spec_row(p, "CAUSAL_EXP", k, cell=cell, site=fam, alpha=dose, edit_class=kind,
                         state_ids=[f"{t}|{w}|{q}" for q in POS4], delta_norm_ratio=h_norm_ratio)
            s["sample_id"] = f"{t}|{cell}|-|{w}|{k}"
            s["pre"] = {o: v.astype(np.float32) for o, v in pre.items()}
            if gen is not None:
                s["gen"] = gen.astype(np.float32)
            out.append(s)
    return out


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("causal_extra")
    set_ram_limit(60)
    c3 = read_json(PRED_DIR / "commit3_causal.json")
    block = int(c3["patch_block"])
    deltas = load_deltas()
    deltas.update(dimfull(c3["causal_plan"], c3["convention"]))
    tw = {(r["task"], r["w"]): r for r in read_jsonl(DATA_DIR / "prompts_static.jsonl") if r["kind"] == "twin"}
    tok, model = load_model()
    t0 = time.time()
    timing = {}
    for ct in c3["causal_plan"]:
        t = ct["task"]
        for i in range(0, len(CELLS), 2):
            pair = CELLS[i:i + 2]
            specs = [s for c in pair for s in specs_for(t, c, deltas, tw)]
            t1 = time.time()
            run_specs(model, tok, specs, f"causal_extra:{t}:{'+'.join(pair)}", out_path=RAW, edit_block=block,
                      batch_cap=60)
            timing[f"{t}:{'+'.join(pair)}"] = round(time.time() - t1, 1)
        logger.info(f"{t} exploratory cells done; elapsed {(time.time() - t0) / 60:.1f} min")
    norms = {}
    z = np.load(CACHE_DIR / "states_L20.npz")
    for ct in c3["causal_plan"]:
        t = ct["task"]
        norms[t] = {p: float(np.linalg.norm(deltas[f"DIMFULL|{t}|TWIN|W1|{p}"])) for p in POS4}
    write_json(RESULTS_DIR / "causal_extra_run.json", {"cells": CELLS, "timing": timing, "dimfull_norms": norms,
                                                       "utc": utc_now(), "note": "exploratory, not pre-registered"})
    (DATA_DIR / "flag_causal_extra.done").write_text(utc_now())
    unload(model)


if __name__ == "__main__":
    main()
