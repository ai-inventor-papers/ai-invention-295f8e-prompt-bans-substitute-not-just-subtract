#!/usr/bin/env python3
"""method_out.json (exp_gen_sol_out schema) from the raw rows, labels, commits and results.

Datasets:
  law_sweep        one example per (unit, template, slot) of the same-stream sweep: input = the prompt id and text,
                   output = the attempted label at T 1.0 (top-p 1); predict_T<T>_<sampler> = 'label|pass' of the same
                   stream in every cell; predict_replay_T<T> = the committed per-slot replay class; predict_law_L_T<T>
                   = the committed law's probability of the observed label (as text).
  fit_twins        every fit-twin program: output = label; predict_frozen_labeller = label|pass.
  locator          one example per (unit, base path): output = the detected decision position (or 'none').
  forced_tokens    one example per (unit, opening, forced token): output = argmax Phat algorithm.
  base_subarm      one example per (task, template): output = instruct margin; predict_base_margin = base margin.
Metadata: every analysis, the verdict, commits (hash chain), deviations, costs, timing, engine checks.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from cfg8 import (COMMITS, CONTS, LABELS, RESULTS_DIR, ROOT, SAMPLES_RAW, SWEEP_SLOTS, TEMPLATES, TEMPS, UNITS,
                  read_json, read_jsonl, setup_logging, write_json)


def _lab(labs: dict[str, Any], sid: str) -> tuple[str, bool]:
    l = labs.get(sid, {})
    return str(l.get("label")), bool(l.get("passed"))


def v8_schema() -> None:
    """S5.4: add the protocol-v8 fields to every program row (site, layer, rank_k and dose null; decision_pos = d (and
    d2); reached_decision = the generated ids match an opening O_c through d)."""
    locs = {u: read_json(RESULTS_DIR / f"locate_{u}.json") for u in UNITS if (RESULTS_DIR / f"locate_{u}.json").exists()}
    rows = read_jsonl(SAMPLES_RAW)
    for r in rows:
        r.update({"site": None, "layer": None, "rank_k": None, "dose": None})
        loc = locs.get(r["unit"])
        r["decision_pos"], r["reached_decision"] = None, False
        if loc:
            for o in loc["openings"]:
                g = r["token_ids"]
                if len(g) > o["d"] and g[:o["d"]] == o["O"]:
                    sec = o.get("second", {}).get(str(g[o["d"]]))
                    r["decision_pos"] = [o["d"], sec["d2"]] if sec and sec.get("found") else [o["d"]]
                    r["reached_decision"] = True
                    break
            if r["decision_pos"] is None and loc["openings"]:
                r["decision_pos"] = sorted({o["d"] for o in loc["openings"]})
    from cfg8 import write_jsonl
    write_jsonl(SAMPLES_RAW, rows)


def main() -> None:
    setup_logging("outputs8")
    v8_schema()
    rows = read_jsonl(SAMPLES_RAW)
    labs = {r["sid"]: r for r in read_jsonl(LABELS)}
    adj = {r["sid"]: r["label"] for r in read_jsonl(ROOT / "data" / "adjudicated_labels.jsonl") if r.get("label")}
    for s, l in adj.items():
        if s in labs:
            labs[s] = {**labs[s], "label": l}
    prompts = {(r["unit"], r["w"]): r for r in read_jsonl(ROOT / "prompts" / "prompts8.jsonl")}
    an = read_json(RESULTS_DIR / "analysis_L.json") if (RESULTS_DIR / "analysis_L.json").exists() else {"units": {}}
    datasets = []
    # law_sweep
    ex = []
    by = {}
    for r in rows:
        if r["arm"] in ("sweep", "topk"):
            by[(r["unit"], r["template"], r["slot"], r["arm"], r["T"])] = r
    for u in UNITS:
        p = RESULTS_DIR / f"predict_{u}.json"
        if not p.exists():
            continue
        pred = read_json(p)
        bins = pred["bins"]
        for w in TEMPLATES:
            for s in SWEEP_SLOTS:
                r1 = by.get((u, w, s, "sweep", 1.0))
                if not r1:
                    continue
                lab1, _ = _lab(labs, r1["sid"])
                pr = prompts.get((u, w), {})
                e = {"input": f"[{u} {w} slot {s}] " + (pr.get("text") or "")[:1500], "output": lab1,
                     "metadata_unit": u, "metadata_family": UNITS[u]["family"], "metadata_template": w,
                     "metadata_slot": s, "metadata_held_out": UNITS[u]["held_out"], "metadata_seed": r1["seed"]}
                for T in TEMPS:
                    for sname, arm in (("p1", "sweep"), ("k10", "topk")):
                        rr = by.get((u, w, s, arm, T))
                        if rr:
                            l, ok = _lab(labs, rr["sid"])
                            e[f"predict_T{str(T).replace('.', '_')}_{sname}"] = f"{l}|{'pass' if ok else 'fail'}"
                    rp = pred["replay"].get(f"{w}|{s}|p1|{T}")
                    e[f"predict_replay_T{str(T).replace('.', '_')}"] = (bins[rp["alg_idx"]] if rp and rp["status"] == "on"
                                                                         and rp["alg_idx"] is not None else "off-opening")
                    PL = pred["cells"][f"p1|{T}"]["L"]
                    rr = by.get((u, w, s, "sweep", T))
                    if rr:
                        l, _ = _lab(labs, rr["sid"])
                        j = bins.index(l) if l in bins else bins.index("other")
                        e[f"predict_law_L_prob_observed_T{str(T).replace('.', '_')}"] = f"{PL[j]:.4f}"
                ex.append(e)
    if ex:
        datasets.append({"dataset": "law_sweep", "examples": ex})
    # fit twins
    ex = []
    for r in rows:
        if r["arm"] != "fit":
            continue
        l, ok = _lab(labs, r["sid"])
        ex.append({"input": f"[{r['unit']} {r['template']} slot {r['slot']}] fit twin T 1.0", "output": l,
                   "metadata_unit": r["unit"], "metadata_family": r["family"], "metadata_n_tokens": r["n_tokens"],
                   "metadata_program": r["text"][:3000], "predict_frozen_labeller": f"{l}|{'pass' if ok else 'fail'}"})
    if ex:
        datasets.append({"dataset": "fit_twins", "examples": ex})
    # locator + forced tokens
    exl, exf = [], []
    for u in UNITS:
        p = RESULTS_DIR / f"locate_{u}.json"
        if not p.exists():
            continue
        loc = read_json(p)
        for bp, cp in zip(loc["base_paths"], loc["change_points"]):
            exl.append({"input": f"[{u}] base path {bp['pid']} ({bp['w']}, label {bp['label']}, {bp['len']} tokens)",
                        "output": str(cp.get("d")) if cp.get("detected") else "none",
                        "predict_change_detected": str(bool(cp.get("detected"))),
                        "metadata_unit": u, "metadata_p_change": cp.get("p_change"), "metadata_tv": cp.get("tv"),
                        "metadata_bracket": cp.get("tau_bracket"), "metadata_series_positions": cp.get("ks")})
        for o in loc["openings"]:
            for t, s, m in zip(o["tokens"], o["token_strs"], o["mass_T1"]):
                ph = o["phat"][str(t)]
                j = max(range(len(ph)), key=lambda i: ph[i])
                exf.append({"input": f"[{u} {o['id']} d={o['d']}] forced token {s!r} (id {t})",
                            "output": loc["bins"][j], "metadata_unit": u, "metadata_mass_T1": m,
                            "metadata_counts": o["counts"][str(t)], "metadata_class": o["classes"]["class_of"][str(t)],
                            "predict_phat": json.dumps(dict(zip(loc["bins"], [round(x, 3) for x in ph])))})
    if exl:
        datasets.append({"dataset": "locator", "examples": exl})
    if exf:
        datasets.append({"dataset": "forced_tokens", "examples": exf})
    # base sub-arm
    bp = RESULTS_DIR / "base_subarm.json"
    if bp.exists():
        b = read_json(bp)
        ex = []
        for t, rec in b["tasks"].items():
            for i, w in enumerate(TEMPLATES):
                ex.append({"input": f"[{t} {w}] decision margin at the instruct decision position",
                           "output": f"{rec['margin_instr'][i]:.4f}", "metadata_task": t,
                           "predict_base_margin": f"{rec['margin_base'][i]:.4f}",
                           "predict_base_margin_template_free": f"{rec['margin_base_template_free'][i]:.4f}"})
        datasets.append({"dataset": "base_subarm", "examples": ex})
    meta: dict[str, Any] = {
        "method_name": "Frozen two-decision temperature law for algorithm choice (claim L, iteration 8)",
        "description": "Predicting how temperature shifts code ideas: blind decision-token location, committed "
                       "predictions (law + baselines B0/B1/B2/BH), same-stream sweep T 0.3/0.7/1.0/1.3 x top-p 1 / "
                       "top-k 10 at N = 100 per cell, 3 model families, base-vs-instruct sub-arm.",
        "verdict": an.get("verdict"), "b3_stream_lean": an.get("b3_stream_lean"),
        "units": {u: {k: v for k, v in a.items() if k not in ("cells", "phrasing")} for u, a in an["units"].items()},
        "cells": {u: a["cells"] for u, a in an["units"].items()},
        "commitments_log": COMMITS.read_text().splitlines() if COMMITS.exists() else [],
        "n_continuations": sum(1 for _ in open(CONTS)) if CONTS.exists() else 0,
        "n_programs": len(rows),
    }
    for name in ("deviations", "costs", "engine_check_gemma", "engine_check_llama", "engine_check_qwen",
                 "gpu_tests_gemma", "gpu_tests_llama", "gpu_tests_qwen", "topk_validation_gemma",
                 "topk_validation_llama", "topk_validation_qwen", "select_llama", "regate", "adjudication",
                 "base_subarm", "novelty_audit", "rederive", "tests_cpu", "prompt_checks", "hardware"):
        p = RESULTS_DIR / f"{name}.json"
        if p.exists():
            d = read_json(p)
            if name == "regate":
                d = {u: {k: v for k, v in r.items() if k != "rows"} for u, r in d.items()}
            if name == "novelty_audit":
                d = {k: v for k, v in d.items() if k != "programs"}
            meta[name] = d
    tim = read_jsonl(RESULTS_DIR / "timing.jsonl")
    meta["gpu_seconds_by_stage"] = dict(Counter({t["stage"]: 0 for t in tim}))
    for t in tim:
        meta["gpu_seconds_by_stage"][t["stage"]] = round(meta["gpu_seconds_by_stage"][t["stage"]] + t["seconds"], 1)
    out = {"metadata": meta, "datasets": datasets}
    write_json(ROOT / "method_out.json", out)
    print({d["dataset"]: len(d["examples"]) for d in datasets})


if __name__ == "__main__":
    main()
