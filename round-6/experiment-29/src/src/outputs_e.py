#!/usr/bin/env python3
"""Assemble method_out.json (exp_gen_sol_out schema) from data/ and results/.

datasets: engine_factorial (one example per task x template x slot x arm of TWIN / PN_a0.5 / PN_a1 / PN_a2: output =
W16A16 'label|pass', predict_W8A8 / predict_W8A16 / predict_W16A8 / predict_W8A8REAL), population40, unit_cross,
t03_control, dither, engine_check (exp19's own rows as output, REAL and EMU as predictions), mechanism_slots.
metadata: every analysis, the verdicts, commits, deviations, device rule, timing and costs."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
DATA = ROOT / "data"
PREC_ALL = ("W16A16", "W8A8", "W8A16", "W16A8", "W8A8REAL")


def rj(p: Path) -> Any:
    return json.loads(p.read_text()) if p.exists() else None


def jl(p: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def lp(r: dict[str, Any] | None) -> str:
    if r is None:
        return "not_run"
    return f"{r.get('label')}|{'pass' if r.get('passed') else 'fail'}"


def build() -> dict[str, Any]:
    import analysis_e as A

    rows = A.merge_rows()
    by: dict[tuple, dict[str, dict[str, Any]]] = defaultdict(dict)
    for r in rows:
        key = (r["task"], r["template"], int(r["slot"]), r["arm"])
        by[key][r["precision"]] = r
    ds: dict[str, list[dict[str, Any]]] = defaultdict(list)
    e27lab = {r["sample_id"]: r for r in jl(ROOT / "inputs" / "exp27" / "data" / "labels.jsonl")}
    for (t, w, k, arm), d in sorted(by.items(), key=lambda x: str(x[0])):
        ref = d.get("W16A16") or next(iter(d.values()))
        base = {"input": f"task={t} template={w} slot=k{k} arm={arm} prompt_sha256={ref.get('prompt_sha256')} "
                          f"crn_key={t}|{w}|{k}",
                "metadata_task": t, "metadata_template": w, "metadata_slot": k, "metadata_arm": arm,
                "metadata_direction_seed": ref.get("direction_seed"), "metadata_alpha": ref.get("alpha"),
                "metadata_unit_kind_dose": ref.get("unit_kind_dose"),
                "metadata_y_correct": {p: A.y_correct(r) for p, r in d.items()},
                "metadata_realised_disp_b12": {p: (r.get("realised_disp") or {}).get("disp_S", {}).get("12")
                                               for p, r in d.items()},
                "metadata_hook_sha256": ref.get("hook_sha256"), "metadata_batch_shape": ref.get("batch_shape")}
        if arm.startswith("DITHER_"):
            ex = {**base, "output": lp(by.get((t, w, k, "TWIN"), {}).get("W16A16")),
                  "predict_dither_cell": lp(d.get("W16A16")),
                  "predict_W16A16_PN_a2": lp(by.get((t, w, k, "PN_a2"), {}).get("W16A16")),
                  "predict_W8A8_PN_a2": lp(by.get((t, w, k, "PN_a2"), {}).get("W8A8"))}
            ds["dither"].append(ex)
            continue
        if arm.startswith("IT5_"):          # POST-HOC replication of iteration 5 (exp27's seeds + unit)
            a27 = arm.replace("IT5", "PN")
            r27 = e27lab.get(f"{t}|{a27}|{w}|{k}")
            ex = {**base, "output": lp(d.get("W16A16")), "predict_W8A8": lp(d.get("W8A8")),
                  "predict_exp27_iteration5_bf16": lp(r27) if r27 else "not_run",
                  "metadata_posthoc": "not pre-registered: exp27 PN5 seeds + per-template ban-free unit"}
            ds["posthoc_iter5_replication"].append(ex)
            continue
        if arm.startswith("PNF_"):
            ex = {**base, "output": lp(d.get("W16A16")), "predict_W8A8_banfree": lp(d.get("W8A8")),
                  "predict_W8A8_ban": lp(by.get((t, w, k, arm.replace("PNF", "PN")), {}).get("W8A8")),
                  "predict_W16A16_ban": lp(by.get((t, w, k, arm.replace("PNF", "PN")), {}).get("W16A16"))}
            ds["unit_cross"].append(ex)
            continue
        ex = {**base, "output": lp(d.get("W16A16")),
              **{f"predict_{p}": lp(d.get(p)) for p in PREC_ALL if p != "W16A16"}}
        if arm.startswith("POP_d"):
            ds["population40"].append(ex)
        elif t == "T03":
            ds["t03_control"].append(ex)
        else:
            ds["engine_factorial"].append(ex)
    # engine check: exp19's own rows as the reference output
    e19 = {r["sample_id"]: r for r in jl(ROOT / "inputs" / "exp19" / "data" / "samples.jsonl")
           if r["task"] in ("T10", "T2", "T03") and r["arm"] in ("TWIN", "PN_a0.5", "PN_a1", "PN_a2")}
    raw_tok = {}
    for r in jl(DATA / "samples_raw.jsonl"):
        if r["precision"] in ("W8A8", "W8A8REAL"):
            raw_tok[r["sample_id"]] = r["token_ids"]
    e19_tok = {r["sample_id"]: (json.loads(r["token_ids"]) if isinstance(r["token_ids"], str) else r["token_ids"])
               for r in jl(ROOT / "inputs" / "exp19" / "data" / "samples_raw.jsonl") if r["sample_id"] in e19}
    for sid, r19 in sorted(e19.items()):
        t, arm, w, k = sid.split("|")
        d = by.get((t, w, int(k), arm), {})
        if "W8A8" not in d and "W8A8REAL" not in d:
            continue
        ex = {"input": f"exp19 sample {sid} prompt_sha256={r19.get('prompt_sha256')}",
              "output": lp(r19), "predict_W8A8REAL": lp(d.get("W8A8REAL")), "predict_W8A8EMU": lp(d.get("W8A8")),
              "metadata_byte_identical_REAL": (raw_tok.get(f"{t}|W8A8REAL|{arm}|{w}|{k}") == e19_tok.get(sid))
              if "W8A8REAL" in d else None,
              "metadata_byte_identical_EMU": (raw_tok.get(f"{t}|W8A8|{arm}|{w}|{k}") == e19_tok.get(sid))
              if "W8A8" in d else None, "metadata_exp19_engine": "FP8 W8A8 _scaled_mm, RTX 2000 Ada, B = 20"}
        ds["engine_check"].append(ex)
    for r in jl(RES / "readouts_slots.jsonl"):
        ex = {"input": f"readout task={r['task']} precision={r['precision']} template={r['template']} slot=k{r['slot']} "
                       f"PN_a2 direction_seed={r['direction_seed']}",
              "output": f"kl_R={r['kl_R']:.5f} kl_tf_mean={r.get('kl_tf_mean')} argmax_R_changed={r['argmax_R_changed']}",
              "metadata_precision": r["precision"], "metadata_task": r["task"],
              "metadata_divergence_R_b35": r["divergence"].get("R", {}).get("35"),
              "metadata_divergence_spec_b23": r["divergence"].get("spec", {}).get("23"),
              "metadata_amplification_R_b35": r["amplification_R"].get("35"),
              "metadata_scale_changed_share_spec_b23_mlp_in": r["scale_changed_share"].get("spec", {}).get("23:mlp_in"),
              "metadata_rerounding_gain_spec_b23_mlp_in": r["rerounding_gain"].get("spec", {}).get("23:mlp_in"),
              "metadata_kl_tf": r.get("kl_tf")}
        ds["mechanism_slots"].append(ex)
    meta = {"method_name": "Claim E: 2x2 weight-by-activation precision factorial (W8A8/W8A16/W16A8/W16A16) of "
                           "per-sample plan noise on Qwen3-8B, paired CRN slots",
            "description": "Did 8-bit arithmetic cause the nudge effect? Everything iteration 4 held fixed is held "
                           "fixed; only the decoder-linear precision varies. W16A16 (native bf16, the iteration-5 "
                           "engine) is the baseline; W8A8 EMU is the emulated FP8 engine of iteration 4; W8A8REAL is "
                           "exp19's FP8Linear on this sm_89 card.",
            "model": "Qwen/Qwen3-8B@b968826d9c46dd6066d109eabc6255188de91218, thinking off, T 1.0",
            "output_format": "'label|pass' per program; output = W16A16 (baseline), predict_<precision> = others"}
    for name in ("posthoc", "verdict", "primary_E", "attribution", "population40", "unit_cross", "t03_control", "dither",
                 "landing", "dose", "engine_check", "iter4_reference", "prompt_diff", "novelty_audit", "rederive",
                 "labeller_recheck", "tests_cpu", "tests_gpu", "dependency_usage", "costs", "timing"):
        v = rj(RES / f"{name}.json")
        if v is not None:
            meta[name] = v
    m = rj(RES / "mechanism.json")
    if m is not None:
        meta["mechanism"] = m
    fac = rj(RES / "factorial.json")
    if fac is not None:
        meta["factorial"] = fac
    for name in ("device_rule", "e_commit", "commit1_gate", "landing_ref"):
        v = rj(ROOT / "predictions" / f"{name}.json")
        if v is not None:
            meta[name] = v
    meta["deviations"] = jl(RES / "deviations.jsonl")
    meta["drops"] = jl(RES / "drops.jsonl")
    out = {"metadata": meta, "datasets": [{"dataset": k, "examples": v} for k, v in ds.items() if v]}
    return out


def timing_summary() -> dict[str, Any]:
    tim = jl(RES / "timing_batches.jsonl")
    out: dict[str, Any] = {"n_batches": len(tim), "gpu_seconds": round(sum(t["seconds"] for t in tim), 1)}
    per = defaultdict(list)
    for t in tim:
        per[t["precision"]].append(t)
    out["per_precision"] = {p: {"n_batches": len(ts), "median_sec_per_batch": float(np.median([t["seconds"] for t in ts])),
                                "median_sec_per_decode_step": float(np.median([(t["seconds"] - t["prefill_seconds"]) /
                                                                               max(t["steps"], 1) for t in ts])),
                                "cap_hits": int(sum(t["n_length"] for t in ts))} for p, ts in per.items()}
    return out


def main() -> None:
    (RES / "timing.json").write_text(json.dumps(timing_summary(), indent=1))
    out = build()
    p = ROOT / "method_out.json"
    p.write_text(json.dumps(out, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    print({d["dataset"]: len(d["examples"]) for d in out["datasets"]}, f"{p.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
