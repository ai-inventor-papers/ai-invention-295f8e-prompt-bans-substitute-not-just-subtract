#!/usr/bin/env python3
"""STEP 9: modal bans (after commit #2). BAN(task, D, w) = template w with {X} = display(D); slots 0-19 per template
(N = 100 per task, primary) in B = 36 CRN batches of one (task, w); the 16 padding rows are ban slots 20-35, flagged
'ban_extra' (sensitivity N = 180). The uniforms u_stream(task, w, slot) are the twin's, so slots 0-9 give exact
twin-to-ban flips. Then the ban-derived unit: prompt-only forward passes of ban(D, w) and twin(w) for the 15 x 5
pairs; n_ban[l, p] = mean over w of ||h_ban - h_twin|| at aligned spec offsets, reported against the ban-free units."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (ALL_TASKS, BAND, DATA_DIR, N_BAN_PER_T, PRED_DIR, RESULTS_DIR, TEMPLATE_IDS, read_json, setup_logging,
                 write_json)
import prompts_gemma as PG
from units import ox_norm, r_at

RAW_BAN = DATA_DIR / "raw_bans.jsonl"
ORDER = ("T03", "T2", "T05", "T06", "T04", "T1", "T10", "R1", "T08", "R3", "T13", "R6", "T14", "T11", "R2")


def run_bans(R: Any, tasks: list[str]) -> None:
    pre = read_json(PRED_DIR / "commit_preban.json")
    c1 = read_json(PRED_DIR / "commit1.json")
    done = R.done_ids(RAW_BAN)
    for t in tasks:
        D = pre["tasks"][t]["D"]
        Dg = c1["pilot"][t]["D_g"]
        B = int(c1["B"][t])
        cap = c1["caps"]["path" if t in ("T1", "T2") else "bench"]["cap"]
        for w in TEMPLATE_IDS:
            rows = [{"arm": "ban", "slot": k, "alpha": 0.0, "dir_kind": None} for k in range(N_BAN_PER_T)]
            rows += [{"arm": "ban_extra", "slot": k, "alpha": 0.0, "dir_kind": None, "pad": True}
                     for k in range(N_BAN_PER_T, B)]
            ids = {f"BAN|{t}|{w}|{r['arm']}|{r['slot']}" for r in rows}
            if ids <= done:
                continue
            ban = PG.p_ban(t, D, w)
            R.run_crn(t, Dg, w, rows, B, cap, "BAN", RAW_BAN, f"BAN:{t}:{w}", prompt=ban)


@torch.no_grad()
def ban_unit(R: Any, tasks: list[str]) -> dict[str, Any]:
    pre = read_json(PRED_DIR / "commit_preban.json")
    c1 = read_json(PRED_DIR / "commit1.json")
    out: dict[str, Any] = {"per_task": {}}
    ratio_ox = {l: [] for l in BAND}
    ratio_plain = {l: [] for l in BAND}
    for t in tasks:
        D, Dg = pre["tasks"][t]["D"], c1["pilot"][t]["D_g"]
        per_w = []
        for w in TEMPLATE_IDS:
            tw = PG.p_twin(t, Dg, w)
            ban = PG.p_ban(t, D, w)
            S = tw["spec_end"] - tw["spec_start"]
            hs_t = R.spec_states(tw["ids"], tw["spec_start"], tw["spec_end"])
            hs_b = R.spec_states(ban["ids"], ban["spec_start"], ban["spec_start"] + S)
            nb = {l: (hs_b[l] - hs_t[l]).norm(dim=-1) for l in BAND}
            no = {l: r_at(l, "r_Q_ox") * ox_norm(hs_t[l]) for l in BAND}
            npl = {l: r_at(l, "r_Q") * hs_t[l].norm(dim=-1) for l in BAND}
            per_w.append({l: (float(nb[l].mean()), float(no[l].mean()), float(npl[l].mean()),
                              float((nb[l] / no[l]).median()), float((nb[l] / npl[l]).median())) for l in BAND})
        rec = {}
        for l in BAND:
            v = np.array([pw[l] for pw in per_w])
            rec[l] = {"n_ban_mean": float(v[:, 0].mean()), "n_banfree_ox_mean": float(v[:, 1].mean()),
                      "n_banfree_plain_mean": float(v[:, 2].mean()), "ratio_ban_over_ox": float(v[:, 3].mean()),
                      "ratio_ban_over_plain": float(v[:, 4].mean())}
            ratio_ox[l].append(rec[l]["ratio_ban_over_ox"])
            ratio_plain[l].append(rec[l]["ratio_ban_over_plain"])
        out["per_task"][t] = rec
    out["by_block"] = {l: {"median_ratio_ban_over_ox": float(np.median(ratio_ox[l])),
                           "median_ratio_ban_over_plain": float(np.median(ratio_plain[l]))} for l in BAND}
    med = float(np.median([v["median_ratio_ban_over_ox"] for v in out["by_block"].values()]))
    out["median_ratio_ban_over_ox"] = med
    out["alpha_in_ban_units"] = {"alpha1": 1.0 / med if med > 0 else None, "alpha2": 2.0 / med if med > 0 else None}
    out["differs_more_than_2x"] = bool(med > 2 or med < 0.5)
    out["note"] = ("ban-derived unit measured after commit #2; movability is not re-measured; E_t is restated in ban "
                   "units only (alpha_ban = alpha / ratio)")
    write_json(RESULTS_DIR / "unit_sensitivity.json", out)
    logger.info(f"ban-derived unit: median n_ban / n_banfree(ox) = {med:.3f}")
    return out


def main() -> None:
    setup_logging("bans")
    assert (PRED_DIR / "commit_preban.json").exists(), "commit #2 first"
    tasks = list(ORDER)
    if "--tasks" in sys.argv:
        tasks = sys.argv[sys.argv.index("--tasks") + 1].split(",")
    from runner import Runner

    R = Runner()
    if "--unit-only" not in sys.argv:
        run_bans(R, tasks)
    ban_unit(R, list(ALL_TASKS))
    logger.info("bans finished")


if __name__ == "__main__":
    main()
