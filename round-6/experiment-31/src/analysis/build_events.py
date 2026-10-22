#!/usr/bin/env python3
"""Build landing_events.json and units.json (schema iter6_landing_v1) from the committed per-unit forecasts
(predictions/units/<u>.json) and the final labels of the HF nudge rows (plan S10/S11).

Cells: ESC = one (direction, alpha) pair, all its rows (stage 1 k 0,1 and, if it passed stage 1, the confirmation
slots k 2..5); PN = PN_a2 and PN_a4 (50 rows each); GTN = GTN_a2. A cell is pooled into its nudge type's landing event
iff its pass rate >= 0.8 x the HF twin's. Event exists iff the pool holds >= 5 correct off-default CATALOGUE programs;
modal landing must lead the next mode by 15 points of those programs ('clear'); 'other' never lands.
Escape fraction: an ESC cell is CONFIRMED iff it passed stage 1 and its pooled 30 rows give a one-sided exact binomial
p < 0.05 against p0 = (k_twin + 0.5) / (n_twin + 1); E_u(alpha) = confirmed / 8; E_u = mean over the alphas run.
Usage: python analysis/build_events.py
"""

from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cfg6 import (ALPHAS_ESC, ESC_EXCESS, ESC_PASS_FRAC, LANDING_LEAD, LANDING_MIN, N_DIRS, PRED_DIR, RESULTS_DIR,  # noqa
                  UNITS_DIR, direction_seed, read_json, read_jsonl, sha256_file, write_json)
from commit6 import entries  # noqa: E402
from labels_view6 import cell_stats, load_final  # noqa: E402

SCHEMA = "iter6_landing_v1"


def binom_sf(k: int, n: int, p: float) -> float:
    return float(sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1)))


def esc_arm(seed: int, alpha: float) -> str:
    return f"ESC_d{seed}_a{alpha:g}"


def pooled_landing(rows: list[dict], D: str, cat: list[str]) -> tuple[dict[str, int], int]:
    cnt = Counter(r["final"] for r in rows if r.get("passed") and r["final"] in cat and r["final"] != D)
    other = sum(1 for r in rows if r.get("passed") and r["final"] == "other")
    return {m: cnt.get(m, 0) for m in cat if m != D}, other


def landing(counts: dict[str, int]) -> tuple[str | None, float, bool, int]:
    tot = sum(counts.values())
    if tot == 0:
        return None, 0.0, False, 0
    srt = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    top, n1 = srt[0]
    n2 = srt[1][1] if len(srt) > 1 else 0
    lead = (n1 - n2) / tot
    return top, lead, (tot >= LANDING_MIN and lead >= LANDING_LEAD), tot


def build() -> dict:
    enr = read_json(PRED_DIR / "enrolment.json")
    commits = {e["tag"].split(":", 1)[1]: e for e in entries() if e["tag"].startswith("unit_commit:")}
    labs = load_final()
    hf = [l for l in labs if l.get("src") == "hf" and l["model_tag"] == "instruct"]
    events, units, cells_out = [], [], []
    for rank, u in enumerate(enr["order"]):
        rec = read_json(PRED_DIR / "units" / f"{u}.json")
        D, cat = rec["default"], rec["catalogue"]
        tw = rec["hf_twin"]
        R = [l for l in hf if l["unit"] == u]
        if not any(l["family"] in ("ESC", "PN", "GTN") for l in R):
            continue
        seeds = [direction_seed(u, k) for k in range(N_DIRS)]
        esc_cells, by_type = {}, {"ESC": [], "PN": [], "GTN": []}
        E_by_alpha, per_dir = {}, {}
        for al in ALPHAS_ESC:
            conf = 0
            for k, s in enumerate(seeds):
                arm = esc_arm(s, al)
                rows = [l for l in R if l["arm"] == arm]
                if not rows:
                    continue
                st1 = cell_stats([l for l in rows if l["slot"] in (0, 1)], D, cat)
                passed1 = st1["off_share"] >= tw["off_share"] + ESC_EXCESS and \
                    st1["pass_rate"] >= ESC_PASS_FRAC * tw["pass_rate"]
                st = cell_stats(rows, D, cat)
                p = binom_sf(st["k_off"], st["n_attempts"], rec["p0"]) if passed1 and st["n_attempts"] >= 25 else None
                confirmed = bool(passed1 and p is not None and p < 0.05)
                conf += confirmed
                cell = {"unit": u, "type": "ESC", "arm": arm, "alpha": al, "direction_index": k, "seed": s,
                        "stage1": st1, "stage1_pass": passed1, "pooled": st, "p_binom": p, "confirmed": confirmed,
                        "gated_for_landing": st["pass_rate"] >= ESC_PASS_FRAC * tw["pass_rate"]}
                esc_cells[arm] = cell
                per_dir.setdefault(str(al), {})[str(k)] = {"off_share_stage1": st1["off_share"],
                                                           "pass_rate_stage1": st1["pass_rate"],
                                                           "stage1_pass": passed1, "confirmed": confirmed,
                                                           "off_share_pooled": st["off_share"], "p": p}
                cells_out.append(cell)
                if cell["gated_for_landing"]:
                    by_type["ESC"] += rows
            E_by_alpha[str(al)] = conf / N_DIRS
        for arm in ("PN_a2", "PN_a4", "GTN_a2"):
            rows = [l for l in R if l["arm"] == arm]
            if not rows:
                continue
            st = cell_stats(rows, D, cat)
            g = st["pass_rate"] >= ESC_PASS_FRAC * tw["pass_rate"]
            cells_out.append({"unit": u, "type": arm.split("_")[0], "arm": arm, "pooled": st, "gated_for_landing": g})
            if g:
                by_type[arm.split("_")[0]] += rows
        for t, rows in by_type.items():
            cnt, other = pooled_landing(rows, D, cat)
            modal, lead, clear, tot = landing(cnt)
            n_att = sum(1 for r in rows if r.get("final") != "disputed")
            ev = {"unit": u, "unit_kind": "new", "nudge_type": t,
                  "cells_pooled": sorted({r["arm"] for r in rows}), "n_attempts": n_att,
                  "pass_rate": (sum(1 for r in rows if r.get("passed")) / n_att) if n_att else None,
                  "twin_pass_rate": tw["pass_rate"], "correct_off_default_counts": cnt, "n_other_correct": other,
                  "n_correct_off_default_catalogue": tot, "exists": tot >= LANDING_MIN, "modal_landing": modal,
                  "margin": lead, "clear_landing": clear, "default": D, "K": rec["K"], "catalogue": cat,
                  "r_u": rec["r_u"], "q_lik_top1": rec["q_lik_top1"], "t_u": rec["t_u"],
                  "tail_empty": rec["tail_empty"], "discordant": rec["discordant"], "q_base": rec["q_base"],
                  "q_lik": rec["q_lik"], "q_lik_raw": rec["q_lik_raw"], "q_tail": rec["q_tail"],
                  "support": rec["base_support"], "flags": rec["flags"],
                  "commit_sha256": commits[u]["sha256"], "commit_utc": commits[u]["utc"]}
            events.append(ev)
        gate_p = UNITS_DIR / u / ("gate_revision.json" if (UNITS_DIR / u / "gate_revision.json").exists()
                                  else "gate.json")
        g = read_json(gate_p)
        ba = read_json(UNITS_DIR / u / "base_audit.json") if (UNITS_DIR / u / "base_audit.json").exists() else {}
        alphas_run = [a for a in E_by_alpha]
        units.append({"unit": u, "unit_kind": "new", "enrolment_rank": rank, "priority": u in enr["priority"],
                      "default": D, "K": rec["K"], "catalogue": cat, "r_u": rec["r_u"], "q_lik_top1": rec["q_lik_top1"],
                      "t_u": rec["t_u"], "tail_empty": rec["tail_empty"], "discordant": rec["discordant"],
                      "flags": rec["flags"], "M": rec["M"], "E_u_by_alpha": E_by_alpha,
                      "E_u": (sum(E_by_alpha.values()) / len(alphas_run)) if alphas_run else None,
                      "per_direction_escape": per_dir, "hf_twin": tw, "p0": rec["p0"],
                      "twin_correct_comp": rec["twin_correct_comp"], "base_counts_used": rec["base_counts_used"],
                      "q_base": rec["q_base"], "q_lik": rec["q_lik"], "q_lik_raw": rec["q_lik_raw"],
                      "q_tail": rec["q_tail"], "engine_check": {k: rec["engine_check"][k] for k in
                                                                ("js_observed", "null_q95", "inside_null")},
                      "gate": {"file": gate_p.name, "status": g["status"],
                               **{k: g["gold"].get(k) for k in ("kappa_runtime_ast", "raw_agreement_runtime_ast",
                                                                 "runtime_vs_adjudicated", "combined_vs_adjudicated",
                                                                 "ref_acc_runtime", "ref_acc_ast")}},
                      "base_audit": {k: ba.get(k) for k in ("n", "agreement_final_vs_judge_a",
                                                             "agreement_final_vs_judge_b", "agreement_judges")},
                      "commit_sha256": commits[u]["sha256"], "commit_utc": commits[u]["utc"]})
    write_json(ROOT / "landing_events.json", {"schema": SCHEMA, "events": events})
    write_json(ROOT / "units.json", {"schema": SCHEMA, "units": units})
    write_json(RESULTS_DIR / "cells.json", {"cells": cells_out})
    return {"n_events": len(events), "n_existing": sum(e["exists"] for e in events), "n_units": len(units)}


if __name__ == "__main__":
    print(build())
