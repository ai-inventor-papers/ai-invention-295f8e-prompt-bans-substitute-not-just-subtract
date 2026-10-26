#!/usr/bin/env python3
"""Builds eval_out_partial.json after every stage and eval_out.json (exp_eval_sol_out) at the end.

Each stage result (results/<stage>.json) may carry:
  metrics:  {name: number}            -> metrics_agg (prefixed by the stage id)
  examples: {dataset: [example, ...]}  -> datasets (input/output strings, metadata_*, predict_* strings, eval_* numbers)
  section:  {inputs, computation, results, edits, status} -> metadata.sections
"""

from __future__ import annotations

import json
import math
import re
from typing import Any

from io_util import RESULTS, ROOT, load_stage, read_json, utc_now, write_json

STAGES = ["s0_setup", "s1_controls", "s0a", "s0b", "s0c", "s0d", "s0e", "s0f", "s0g", "s0h", "s0i", "s0j",
          "s8_edits", "s10_figures", "s10_ledger", "s9_audit", "s9b_spotcheck"]
SECTION_OF = {"s0a": "0a", "s0b": "0b", "s0c": "0c", "s0d": "0d", "s0e": "0e", "s0f": "0f", "s0g": "0g",
              "s0h": "0h", "s0i": "0i", "s0j": "0j", "s10_ledger": "0k"}
KEY_RX = re.compile(r"[^a-zA-Z0-9_]")


def _clean_key(k: str) -> str:
    k = KEY_RX.sub("_", k)
    if not re.match(r"^[a-zA-Z_]", k):
        k = "m_" + k
    return k


def _num(v: Any) -> float | None:
    if isinstance(v, bool):
        return float(v)
    if isinstance(v, (int, float)) and math.isfinite(float(v)):
        return v
    return None


def _example_ok(e: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"input": str(e.get("input", "")), "output": str(e.get("output", ""))}
    for k, v in e.items():
        if k in ("input", "output"):
            continue
        if k.startswith("metadata_"):
            out[_clean_key(k)] = v
        elif k.startswith("predict_"):
            out[_clean_key(k)] = v if isinstance(v, str) else json.dumps(v, default=str)
        elif k.startswith("eval_"):
            n = _num(v)
            if n is not None:
                out[_clean_key(k)] = n
        else:
            out[_clean_key("metadata_" + k)] = v
    return out


def build(final: bool) -> dict[str, Any]:
    metrics: dict[str, float] = {}
    datasets: dict[str, list[dict[str, Any]]] = {}
    sections: dict[str, Any] = {}
    stage_status: dict[str, str] = {}
    for st in STAGES:
        r = load_stage(st)
        if r is None:
            stage_status[st] = "NOT RUN"
            continue
        stage_status[st] = str(r.get("status", "DONE"))
        for k, v in (r.get("metrics") or {}).items():
            n = _num(v)
            if n is not None:
                metrics[_clean_key(f"{st}_{k}")] = n
        for ds, exs in (r.get("examples") or {}).items():
            datasets.setdefault(ds, []).extend(_example_ok(e) for e in exs)
        if st in SECTION_OF and r.get("section"):
            sections[SECTION_OF[st]] = r["section"]
    if not metrics:
        metrics["stages_completed"] = 0
    metrics["stages_completed"] = float(sum(1 for s in stage_status.values() if s != "NOT RUN"))
    crit = read_json(RESULTS / "criteria.json") if (RESULTS / "criteria.json").exists() else {}
    ds_list = [{"dataset": k, "examples": v} for k, v in datasets.items() if v]
    if not ds_list:
        ds_list = [{"dataset": "placeholder_until_first_item", "examples": [
            {"input": "no item has finished yet", "output": "partial", "metadata_status": "partial"}]}]
    out = {
        "metadata": {
            "evaluation_name": "iteration-10 S0 record repair of the iteration-9 record (gen_plan_evaluation_1_idx7)",
            "description": "Every number the blocking iteration-9 review questioned (items 0a-0j) re-derived from the "
                           "three declared dependencies, written as verbatim old->new corrections into a corrected "
                           "copy of the report, proven by an apply test, a residual-claim lint with positive "
                           "controls, GRIM-style attainability checks and an independent stdlib re-derivation with "
                           "placebos; 0k is a source-cited request ledger.",
            "dependencies": ["art_8nXdw3_lDAll", "art_VVA3P0ocZNA2", "art_cDba8_DycUJd"],
            "object_corrected": "report:iter_10/gen_strat/current_report.md (copied byte-identical to "
                                "inputs/report/current_report.md)",
            "partial": not final, "utc": utc_now(), "stage_status": stage_status,
            "criteria": crit, "sections": sections,
            "compute": "CPU only; no GPU and no model calls (OpenRouter spend USD 0.00 of the 0.3 cap)",
        },
        "metrics_agg": metrics,
        "datasets": ds_list,
    }
    return out


def write_partial(final: bool = False) -> None:
    out = build(final)
    write_json(ROOT / "eval_out_partial.json", out)
    if final:
        write_json(ROOT / "eval_out.json", out)
