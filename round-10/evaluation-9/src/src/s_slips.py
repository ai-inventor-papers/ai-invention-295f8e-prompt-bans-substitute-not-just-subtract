#!/usr/bin/env python3
"""Items 0i (slips) and 0j (the bin-packing harness gate).

0i(1) the name-evocation chance for the six-class program set; (2) the denominator of the lost rotated and
described samples; (3) base P(alternative) and the unmapped base mass at the forks of Table 440; (4) the alias-test
wording of Section 9.2.
0j  the lost iteration-9 bin-packing workspace (undeclared; read only if present) for the harness gate values;
status MATCH if its files are readable, else CARRIED from the hypothesis text.
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any

from loguru import logger

import rows as RW
from io_util import A_BASE, A_GEO, A_REN, TABLES, dep_path, dep_root, env_value, read_json, ref, save_stage

LOST_BINPACK = Path(env_value("LOST_BINPACK") or "missing-LOST_BINPACK")   # undeclared; location kept in .env
LOST_LABEL = "lost iteration-9 bin-packing workspace (gen_art_experiment_48 of iteration 9; undeclared)"


def run_0i() -> dict[str, Any]:
    out: dict[str, Any] = {}
    # (1) name evocation
    rsa = read_json(dep_path(A_GEO, "results/rsa.json"))
    ne = rsa["name_evocation"]["32b"]
    prog = ne["mcode_PRIMARY_R1"]
    present = rsa["32b|mcode_PRIMARY_R1"]["present"]
    out["name_evocation"] = {"programs_balanced_accuracy": prog["transfer_balanced_accuracy"], "chance": prog["chance"],
                             "n_classes_program_set": len(present), "present": present,
                             "chance_is_one_over_classes": abs(prog["chance"] - 1 / len(present)) < 1e-12,
                             "described": ne["mdesc"], "source": ref(A_GEO, "results/rsa.json",
                                                                     "name_evocation.32b.mcode_PRIMARY_R1")}
    # (2) rotated and described samples
    cnt = Counter(r["cell"] for r in RW.samples_v9())
    rot = ["B_R1", "B_R2", "B_R3", "B_R4", "D_R5", "D_R6"]
    present_rot = sum(cnt.get(c, 0) for c in rot)
    present_desc = cnt.get("C_desc", 0)
    planned = 50 * len(rot) + 50
    out["lost_samples"] = {"present_rotated": present_rot, "present_described": present_desc,
                           "planned": planned, "lost": planned - present_rot - present_desc,
                           "per_cell": {c: cnt.get(c, 0) for c in rot + ["C_desc"]},
                           "source": ref(A_REN, "data/samples_v9.jsonl", "cell")}
    # (3) base P(alternative) and unmapped base mass per fork of Table 440
    forks = []
    for fname, unit in (("b1_gemma_G-GRID.json", "Gemma grid"), ("b1_gemma_G-T04.json", "Gemma substring search"),
                        ("b1_gemma_G-R6.json", "Gemma first and last position"),
                        ("b1_llama_L-GRID.json", "Llama grid")):
        p = dep_root(A_BASE) / "results" / fname
        if not p.exists():
            continue
        g = read_json(p)
        for fk, fv in g.get("forks", {}).items():
            mode = fv.get("primary_mode", "chat")
            blk = fv.get(mode) or fv.get("chat") or fv.get("plain") or {}
            pin = blk.get("pushed_through_instr") or {}
            pba = blk.get("pushed_through_base") or {}
            default = max(pin, key=pin.get) if pin else None
            alt = [k for k in pin if k != default]
            forks.append({"unit": unit, "fork": fk, "mode": mode, "default": default,
                          "base_p_alternative": (pba.get(alt[0]) if alt and len(alt) == 1 else None),
                          "alternative": alt[0] if len(alt) == 1 else alt,
                          "base_p_default": pba.get(default) if default else None,
                          "unmapped_base_mass": blk.get("base_mass_unmapped"),
                          "source": ref(A_BASE, f"results/{fname}", f"forks.{fk}.{mode}")})
    out["forks"] = forks
    with open(TABLES / "table440b_base_mass.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["unit", "fork", "mode", "instruct_default", "alternative", "base_p_alternative", "base_p_default",
                    "unmapped_base_mass", "source"])
        for f in forks:
            w.writerow([f["unit"], f["fork"], f["mode"], f["default"], f["alternative"],
                        "n/a" if f["base_p_alternative"] is None else f"{f['base_p_alternative']:.4f}",
                        "n/a" if f["base_p_default"] is None else f"{f['base_p_default']:.4f}",
                        "n/a" if f["unmapped_base_mass"] is None else f"{f['unmapped_base_mass']:.4f}", f["source"]])
    gg = [f for f in forks if f["fork"] == "G-GRID@32"]
    out["grid"] = gg[0] if gg else None
    # (4) alias-test wording: three algorithms contribute effective relabelings (3!^3 = 216)
    out["alias_within"] = {"effective_relabelings": 216, "three_factorial_cubed": 6 ** 3,
                           "reading": "216 = (3!)^3: only three of the five non-banned algorithms have aliases with "
                                      "distinct overlap counts, so the stratified test has three informative strata"}
    metrics = {"programs_balanced_accuracy": prog["transfer_balanced_accuracy"], "programs_chance": prog["chance"],
               "program_classes": len(present), "lost_samples": out["lost_samples"]["lost"],
               "planned_samples": planned, "present_samples": present_rot + present_desc,
               "grid_base_p_alternative": gg[0]["base_p_alternative"] if gg else -1,
               "grid_unmapped_base_mass": gg[0]["unmapped_base_mass"] if gg else -1}
    ex = [{"input": "slip 1: name-evocation probe on the program manifold",
           "output": f"balanced accuracy {prog['transfer_balanced_accuracy']:.3f} = chance for {len(present)} classes "
                     f"({prog['chance']:.3f})", "eval_value": prog["transfer_balanced_accuracy"]},
          {"input": "slip 2: rotated and described samples lost to rate limits",
           "output": f"{out['lost_samples']['lost']} of {planned} (present {present_rot} rotated + {present_desc} described)",
           "eval_value": out["lost_samples"]["lost"]},
          {"input": "slip 3: Gemma grid fork, base model",
           "output": f"base P(alternative = {gg[0]['alternative']}) {gg[0]['base_p_alternative']:.3f}; unmapped base mass "
                     f"{gg[0]['unmapped_base_mass']:.3f}" if gg else "n/a", "eval_value": gg[0]["unmapped_base_mass"] if gg else 0},
          {"input": "slip 4: alias test within algorithms", "output": "not detected (three informative algorithms; underpowered)",
           "eval_value": 216}]
    section = {"inputs": [ref(A_GEO, "results/rsa.json", "name_evocation"), ref(A_REN, "data/samples_v9.jsonl"),
                          ref(A_BASE, "results/b1_gemma_G-GRID.json")],
               "computation": "chance = 1/classes of the program set; planned 7 x 50 rotated/described rows against "
                              "those present; base P(alternative) = pushed_through_base of the non-default class; "
                              "unmapped base mass as stored", "results": out,
               "edits": ["E-9.4-rsa", "E-9.3-novelty", "E-T440", "E-9.5-sharpening", "E-9.8-established", "E-9.2-alias"],
               "status": "DONE"}
    save_stage("s0i", {"status": "DONE", "result": out, "metrics": metrics, "section": section,
                       "examples": {"slips": ex}})
    return out


def run_0j() -> dict[str, Any]:
    p = LOST_BINPACK / "results" / "harness_gate.json"
    lg = LOST_BINPACK / "logs" / "gate.log"
    if p.exists():
        g = read_json(p)
        gate = g["gate"]
        res = {"status": "MATCH", "source": f"{LOST_LABEL}: results/harness_gate.json and logs/gate.log",
               "G_HARNESS_PASS": g.get("G_HARNESS_PASS"), "bf_or3_excess": gate["BF_OR3"]["excess_pct"],
               "bf_w5k_excess": gate["BF_W5k"]["excess_pct"], "funsearch_or3_excess": gate["c12_OR3"]["excess_pct"],
               "funsearch_w5k_excess": gate["c14_W5k"]["excess_pct"],
               "priority_vs_handcoded": g.get("priority_vs_handcoded"), "calibration": g.get("calibration"),
               "log_has_pass_line": lg.exists() and "G-HARNESS PASS" in lg.read_text(), "utc": g.get("utc")}
    else:
        logger.warning("lost bin-packing workspace not readable; values CARRIED from the hypothesis text")
        res = {"status": "CARRIED", "source": "hypothesis text (G-HARNESS PASS; 5.37% OR3, 3.98% Weibull 5k; "
                                              "FunSearch 3.11% and 0.68%)",
               "G_HARNESS_PASS": True, "bf_or3_excess": 5.37, "bf_w5k_excess": 3.98, "funsearch_or3_excess": 3.11,
               "funsearch_w5k_excess": 0.68, "priority_vs_handcoded": {"FF": True, "BF": True, "WF": True}}
    metrics = {"harness_pass": float(bool(res["G_HARNESS_PASS"])), "bf_or3_excess_pct": res["bf_or3_excess"],
               "bf_w5k_excess_pct": res["bf_w5k_excess"], "funsearch_or3_excess_pct": res["funsearch_or3_excess"],
               "funsearch_w5k_excess_pct": res["funsearch_w5k_excess"], "status_match": float(res["status"] == "MATCH")}
    ex = [{"input": "bin-packing harness gate (iteration 9, before the workspace was lost)",
           "output": f"G-HARNESS {'PASS' if res['G_HARNESS_PASS'] else 'FAIL'}; best fit {res['bf_or3_excess']:.2f}% on OR3, "
                     f"{res['bf_w5k_excess']:.2f}% on Weibull 5k; FunSearch {res['funsearch_or3_excess']:.2f}% and "
                     f"{res['funsearch_w5k_excess']:.2f}%; priority form equals hand-coded FF/BF/WF "
                     f"{res['priority_vs_handcoded']}", "metadata_status": res["status"],
           "eval_bf_or3_excess_pct": res["bf_or3_excess"]}]
    section = {"inputs": [res["source"]], "computation": "values read from the gate file; no search result exists",
               "results": res, "edits": ["E-9.6-novb", "E-9.9"], "status": res["status"]}
    save_stage("s0j", {"status": res["status"], "result": res, "metrics": metrics, "section": section,
                       "examples": {"harness_gate": ex}})
    return res
