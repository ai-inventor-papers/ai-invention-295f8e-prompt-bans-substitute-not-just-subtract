#!/usr/bin/env python3
"""method_out.json (exp_gen_sol_out schema): one dataset per study arm, one example per program/sample.

input  = the prompt the model saw (for carried rows without a stored prompt, the rendered literal-ban W prompt)
output = the extracted program ('' when none)
predict_name_label   = the NAME-level label (iteration-8 labeller + adjudication): the field's standard detector
predict_runtime_class = the iteration-8 name-free runtime label mapped to a coarse class (the committed
                        gate-failure FALLBACK mechanism label, i.e. the primary mechanism reading of this run)
predict_order_class  = the tracer v9 expansion-order class (this artifact's new name-blind detector; second column)
predict_lexical_L1 / predict_lexical_L2 = 'compliant' or 'violation'
"""

from __future__ import annotations

import json
from typing import Any

from common import DATA, PRED, RESULTS, ROOT, read_json, read_jsonl, total_cost, utc_now, verify_chain, write_json

DROP = {"code", "content", "reasoning", "prompt", "segment", "trace_stats", "judge_labels"}


def _meta(r: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in r.items():
        if k in DROP:
            continue
        key = "metadata_" + "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in k)
        out[key] = v if isinstance(v, (str, int, float, bool)) or v is None else json.dumps(v, default=str)
    if r.get("trace_stats"):
        out["metadata_trace_stats"] = json.dumps(r["trace_stats"], default=str)
    return out


def _ex(r: dict[str, Any], prompt: str) -> dict[str, Any]:
    import analysis_v9 as A

    return {"input": prompt or "", "output": r.get("code") or "",
            "predict_name_label": str(r.get("label")),
            "predict_runtime_class": str(A.runtime_class(r)),
            "predict_order_class": str(r.get("order_class")),
            "predict_order_class_fine": str(r.get("order_class_fine")),
            "predict_lexical_L1": "compliant" if r.get("lexical_L1") else "violation",
            "predict_lexical_L2": "compliant" if r.get("lexical_L2") else "violation",
            **_meta(r)}


def build() -> dict[str, Any]:
    from prompts_tp import ban_prompt

    from common import LITERAL5

    prompts = {}
    for f in ("prompts_v9_1a.jsonl", "prompts_v9_1b.jsonl", "prompts_v9_2.jsonl"):
        for p in read_jsonl(PRED / f):
            prompts[(p["cell"], int(p["slot"]))] = p["prompt"]
    datasets = []
    ret = read_jsonl(RESULTS / "retrace.jsonl")
    i8 = {}
    for c in ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"):
        for arm in ("ban", "confirm"):
            for r in read_jsonl(ROOT / "inputs" / "iter8" / "data" / f"labelled_{c}_{arm}.jsonl"):
                i8[r["uid"]] = r.get("prompt")
    exs = []
    for r in ret:
        pr = i8.get(r["uid"]) or ban_prompt(list(LITERAL5), r.get("template") if r.get("template") in
                                            ("W1", "W2", "W3", "W4", "W5", "P6", "P7") else "W1", 0)["prompt"]
        exs.append(_ex(r, pr))
    datasets.append({"dataset": "tp_retrace", "examples": exs})
    groups = {"tp_cumulative": ("A", "E"), "tp_rotated": ("B", "D"), "tp_described": ("C",), "tp_scale": ("F",)}
    import cells_v9

    for name, gs in groups.items():
        exs = []
        for cid, cell in cells_v9.CELLS.items():
            if cell["group"] not in gs:
                continue
            for r in read_jsonl(DATA / f"labelled_v9_{cid}.jsonl"):
                exs.append(_ex(r, prompts.get((cid, int(r["slot"])), "")))
        if exs:
            datasets.append({"dataset": name, "examples": exs})
    meta = {"method_name": "TP-B iteration 9: name-level vs expansion-order (mechanism) compliance with algorithm bans",
            "description": "Gated expansion-order tracer v9 (40 probe grids) assigns each program an order class from "
                           "runtime events only; compared with the name-level label (iteration-8 labeller + judges) "
                           "and with lexical compliance (L1/L2).",
            "utc": utc_now(), "commitments": verify_chain()[2], "chain_ok": verify_chain()[0],
            "costs_usd": total_cost()}
    for f in ("headlines", "n1", "n2", "n3", "n3d", "n5", "scale", "n1_tracer", "n2_tracer", "n3_tracer",
              "n3d_tracer", "instrument_bounds", "fallback_label_validation", "tracer_gate_round0_final",
              "tracer_gate_round1", "tracer_gate_round2", "tracer_unit_tests", "clrs_check", "gold_order_judges",
              "placebo_shuffled_events", "deviations", "costs", "dataset_use", "novelty_audit_v9", "rederive",
              "positioning", "manual_reads_summary", "judge_gate_v9", "budget_plan", "mock_403_test", "smoke",
              "renderer_checks_v9", "lexical_unit_tests", "inputs_manifest"):
        p = RESULTS / f"{f}.json"
        if p.exists():
            v = read_json(p)
            if f == "n2":
                v = {k: x for k, x in v.items()}
            meta[f] = v
    for f in ("commit1a", "commit1b", "commit2", "n5_sets", "n3d_descriptions"):
        p = PRED / f"{f}.json"
        if p.exists():
            meta[f"predictions_{f}"] = read_json(p)
    return {"metadata": meta, "datasets": datasets}


def write() -> None:
    out = build()
    write_json(ROOT / "method_out.json", out, indent=None)
