#!/usr/bin/env python3
"""Final outputs (plan S11): data/samples.jsonl (one row per program, raw rows joined with final labels) and
method_out.json (exp_gen_sol_out) with datasets panelI_units, panelI_events and panelI_cells; every example carries
predict_base (r_u), predict_qlik (q_lik top-1) and predict_tail (t_u) against the observed landing.
Usage: python analysis/outputs.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cfg6 import DATA_DIR, RAW, RAW_HF, REALISED, RESULTS_DIR, read_json, read_jsonl, write_jsonl  # noqa: E402
from labels_view6 import load_final  # noqa: E402
from units_spec6 import UNITS, spec_text  # noqa: E402


def row_key(r: dict) -> str:
    src = "hf" if r.get("engine", "").startswith("hf") else "vllm"
    return f"{r['unit']}|{r['template']}|{r['arm']}|{r['slot']}|{r['model_tag']}|{src}"


def samples() -> int:
    labs = {l["key"]: l for l in load_final()}
    disp = {}
    for d in read_jsonl(REALISED):
        k = (d["unit"], d["template"], d["arm"], d.get("slot"))
        disp[k] = {"rel_err_max": d.get("rel_err_max"), "target_ratio_to_h": d.get("target_ratio_to_h"),
                   "disp_R_norm_23": (d.get("disp_R_norm") or {}).get("23")}
    out = []
    for r in read_jsonl(RAW) + read_jsonl(RAW_HF):
        if r["arm"] == "PAD" or r.get("shadow"):
            continue
        l = labs.get(row_key(r), {})
        fam = r["arm"].split("_")[0]
        rd = disp.get((r["unit"], r["template"], r["arm"], r["slot"])) or disp.get((r["unit"], r["template"],
                                                                                   r["arm"], None))
        out.append({"model": r.get("model"), "model_tag": r["model_tag"], "unit": r["unit"], "unit_kind": "new",
                    "arm": r["arm"], "family": fam, "site": r.get("site"), "precision": r.get("precision"),
                    "lambda": None, "alpha": r.get("alpha"), "direction_seed": r.get("direction_seed"),
                    "template": r["template"], "slot": r["slot"], "temperature": r.get("temperature"),
                    "thinking": False, "prompt_sha256": r.get("prompt_sha256"),
                    "label": l.get("final", l.get("label")), "runtime_label": l.get("runtime_label"),
                    "ast_label": l.get("ast_label"), "labeller_source": l.get("labeller_source"),
                    "passed": l.get("passed"), "valid": l.get("valid"), "finish_reason": r.get("finish_reason"),
                    "n_new_tokens": r.get("n_tokens"), "realised_disp": rd if fam in ("ESC", "PN") else
                    ({"gtn_rel_err_max": r.get("gtn_rel_err_max")} if fam == "GTN" else None),
                    "code_sha256": l.get("code_sha256"), "code": l.get("code"),
                    "assoc_answer": l.get("assoc_answer"), "intent": l.get("intent"), "engine": r.get("engine"),
                    "hook_sha256": r.get("hook_sha256"), "utc": r.get("utc"), "key": row_key(r)})
    write_jsonl(DATA_DIR / "samples.jsonl", out)
    return len(out)


def method_out() -> dict:
    ev = read_json(ROOT / "landing_events.json")["events"]
    un = read_json(ROOT / "units.json")["units"]
    cells = read_json(RESULTS_DIR / "cells.json")["cells"]
    pool = read_json(RESULTS_DIR / "pool_l1_panelI.json")
    s = lambda x: "none" if x is None else str(x)  # noqa: E731
    d_units, d_events, d_cells = [], [], []
    ul = {e["unit"]: e for e in pool.get("unit_clustered", {}).get("L1a", {}).get("events", [])}
    for U in un:
        u = U["unit"]
        es = [e for e in ev if e["unit"] == u]
        tot = Counter()
        for e in es:
            tot.update(e["correct_off_default_counts"])
        land = tot.most_common(1)[0][0] if tot else None
        d_units.append({"input": spec_text(u), "output": s(land if sum(tot.values()) >= 5 else "no landing"),
                        "predict_base": s(U["r_u"]), "predict_qlik": s(U["q_lik_top1"]), "predict_tail": s(U["t_u"]),
                        "metadata_unit": u, "metadata_default": U["default"], "metadata_K": U["K"],
                        "metadata_E_u": U["E_u"], "metadata_E_u_by_alpha": json.dumps(U["E_u_by_alpha"]),
                        "metadata_tail_empty": U["tail_empty"], "metadata_discordant": U["discordant"],
                        "metadata_flags": json.dumps(U["flags"]), "metadata_M": json.dumps(U["M"]),
                        "metadata_pooled_landing_counts": json.dumps(dict(tot)),
                        "metadata_gate": json.dumps(U["gate"]), "metadata_commit_sha256": U["commit_sha256"]})
    for e in ev:
        d_events.append({"input": f"unit {e['unit']} ({UNITS[e['unit']]['slug']}), nudge type {e['nudge_type']}: "
                                  f"where do the correct off-default programs land? default {e['default']}",
                         "output": s(e["modal_landing"] if e["clear_landing"] else
                                     ("no clear landing" if e["exists"] else "no event")),
                         "predict_base": s(e["r_u"]), "predict_qlik": s(e["q_lik_top1"]), "predict_tail": s(e["t_u"]),
                         "metadata_unit": e["unit"], "metadata_nudge_type": e["nudge_type"],
                         "metadata_exists": e["exists"], "metadata_clear_landing": e["clear_landing"],
                         "metadata_margin": e["margin"], "metadata_counts": json.dumps(e["correct_off_default_counts"]),
                         "metadata_n_other_correct": e["n_other_correct"], "metadata_tail_empty": e["tail_empty"],
                         "metadata_discordant": e["discordant"], "metadata_pass_rate": e["pass_rate"],
                         "metadata_twin_pass_rate": e["twin_pass_rate"], "metadata_q_base": json.dumps(e["q_base"]),
                         "metadata_q_lik": json.dumps(e["q_lik"]), "metadata_q_tail": json.dumps(e["q_tail"])})
    for c in cells:
        U = next(x for x in un if x["unit"] == c["unit"])
        st = c["pooled"]
        comp = {k: v for k, v in st["correct_comp"].items()}
        off = Counter({k: v for k, v in comp.items() if k != U["default"] and k in U["catalogue"]})
        d_cells.append({"input": f"unit {c['unit']} cell {c['arm']} ({c['type']})",
                        "output": json.dumps(comp, sort_keys=True),
                        "predict_base": s(U["r_u"]), "predict_qlik": s(U["q_lik_top1"]), "predict_tail": s(U["t_u"]),
                        "metadata_unit": c["unit"], "metadata_type": c["type"], "metadata_arm": c["arm"],
                        "metadata_alpha": c.get("alpha"), "metadata_direction_index": c.get("direction_index"),
                        "metadata_n_attempts": st["n_attempts"], "metadata_pass_rate": st["pass_rate"],
                        "metadata_off_share": st["off_share"], "metadata_stage1_pass": c.get("stage1_pass"),
                        "metadata_confirmed": c.get("confirmed"), "metadata_gated_for_landing": c["gated_for_landing"],
                        "metadata_modal_off_default": s(off.most_common(1)[0][0] if off else None)})
    return {"metadata": {"method_name": "Panel I (iteration 6, Step 3): base-model forecasts of where content-free "
                                        "nudges land", "schema_events": "iter6_landing_v1",
                         "models": {"instruct": "Qwen/Qwen3-8B@b968826d", "base": "Qwen/Qwen3-8B-Base@49e3418f"},
                         "precision": "W16A16 bf16", "pool_l1": {k: pool[k] for k in ("n_units", "n_events", "note")},
                         "deviations": [d["key"] for d in read_jsonl(RESULTS_DIR / "deviations.jsonl")]},
            "datasets": [{"dataset": "panelI_units", "examples": d_units},
                         {"dataset": "panelI_events", "examples": d_events},
                         {"dataset": "panelI_cells", "examples": d_cells}]}


def main() -> None:
    n = samples()
    mo = method_out()
    (ROOT / "method_out.json").write_text(json.dumps(mo, indent=1))
    print(f"samples {n}; method_out datasets {[len(d['examples']) for d in mo['datasets']]}")


if __name__ == "__main__":
    main()
