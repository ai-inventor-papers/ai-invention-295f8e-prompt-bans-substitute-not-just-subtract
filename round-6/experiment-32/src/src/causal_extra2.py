#!/usr/bin/env python3
"""EXPLORATORY follow-up (not pre-registered) of the GEN-site signal seen in src/causal_extra.py (T06: the NLA edit
x8 at READ + generated positions 1-64 moved Floyd from 12/30 to 23/30 while the matched random push did not).
Same tasks, hook, patch block and CRN streams. New cells (GEN site only):
  EXP2_GEN_EDIT_x4 / _x16        dose response of the NLA edit
  EXP2_GEN_UNREL_x8              the unrelated-word edit (same construction, irrelevant word), x8
  EXP2_GEN_RTM_x8                the unedited round-trip direction rescaled to ||EDIT|| (matched norm), x8
  EXP2_GEN_RAND_x16, EXP2_GEN_DIM_x16
  REP_GEN_EDIT_x8, REP_GEN_RAND_x8   replication on fresh CRN slots 6-9 (W1-W5 x 4 = 20 rows)
Usage: python src/causal_extra2.py ; then src/labels.py on data/samples_causal_extra2_raw.jsonl
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import (DATA_DIR, PRED_DIR, RESULTS_DIR, TEMPLATE_IDS, read_json, read_jsonl, set_ram_limit, setup_logging,
                 utc_now, write_json)
from causal_gen import load_deltas
from engine import load_model, unload
from gen import run_specs, spec_row

RAW = DATA_DIR / "samples_causal_extra2_raw.jsonl"
POS4 = ("SPEC-3", "SPEC-2", "SPEC-1", "READ")
CELLS = [("EXP2_GEN_EDIT_x4", range(6)), ("EXP2_GEN_EDIT_x16", range(6)), ("EXP2_GEN_UNREL_x8", range(6)),
         ("EXP2_GEN_RTM_x8", range(6)), ("EXP2_GEN_RAND_x16", range(6)), ("EXP2_GEN_DIM_x16", range(6)),
         ("REP_GEN_EDIT_x8", range(6, 10)), ("REP_GEN_RAND_x8", range(6, 10))]


def specs_for(t: str, cell: str, slots: range, deltas: dict[str, np.ndarray], tw: dict) -> list[dict[str, Any]]:
    _, fam, kind, dt = cell.split("_")
    dose = float(dt[1:])
    out = []
    for w in TEMPLATE_IDS:
        p = tw[(t, w)]
        dR = deltas[f"{kind}|{t}|TWIN|{w}|READ"] * dose
        for k in slots:
            s = spec_row(p, "CAUSAL_EXP2", k, cell=cell, site="GEN", alpha=dose, edit_class=kind,
                         state_ids=[f"{t}|{w}|READ"], delta_norm_ratio=float(np.linalg.norm(dR)))
            s["sample_id"] = f"{t}|{cell}|-|{w}|{k}"
            s["pre"] = {1: dR.astype(np.float32)}
            s["gen"] = dR.astype(np.float32)
            out.append(s)
    return out


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("causal_extra2")
    set_ram_limit(60)
    c3 = read_json(PRED_DIR / "commit3_causal.json")
    block = int(c3["patch_block"])
    deltas = load_deltas()
    for ct in c3["causal_plan"]:
        t = ct["task"]
        for w in TEMPLATE_IDS:
            e = deltas[f"EDIT|{t}|TWIN|{w}|READ"]
            rt = deltas[f"RT|{t}|TWIN|{w}|READ"]
            deltas[f"RTM|{t}|TWIN|{w}|READ"] = (rt / max(np.linalg.norm(rt), 1e-12) * np.linalg.norm(e)).astype(np.float32)
    tw = {(r["task"], r["w"]): r for r in read_jsonl(DATA_DIR / "prompts_static.jsonl") if r["kind"] == "twin"}
    tok, model = load_model()
    t0 = time.time()
    for ct in c3["causal_plan"]:
        t = ct["task"]
        specs = [s for c, sl in CELLS for s in specs_for(t, c, sl, deltas, tw)]
        run_specs(model, tok, specs, f"causal_extra2:{t}", out_path=RAW, edit_block=block, batch_cap=60)
        logger.info(f"{t} follow-up cells done; elapsed {(time.time() - t0) / 60:.1f} min")
    write_json(RESULTS_DIR / "causal_extra2_run.json", {"cells": [c for c, _ in CELLS], "utc": utc_now(),
                                                        "minutes": round((time.time() - t0) / 60, 1),
                                                        "note": "exploratory, not pre-registered"})
    (DATA_DIR / "flag_causal_extra2.done").write_text(utc_now())
    unload(model)


if __name__ == "__main__":
    main()
