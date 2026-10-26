#!/usr/bin/env python3
"""H8: method_out.json (exp_gen_sol_out schema) + the shared per-sample schema (data/samples.jsonl)."""

from __future__ import annotations

import json
from typing import Any

from src import label as L
from src import prompts_llama as P
from src.ws import DATA, MODEL_TAG, PRED, RESULTS, WS, read_json, read_jsonl, write_json, write_jsonl


def _s(x: Any) -> str:
    return "undefined" if x is None else str(x)


def shared_rows(labels: list[dict], raw_by: dict) -> int:
    rows = []
    for r in labels:
        raw = raw_by.get(r["row_id"], {})
        code, _ = L.extract(raw.get("text"))
        rows.append({"model": raw.get("model") or MODEL_TAG, "task": r["task"], "condition": r.get("condition"),
                     "template": raw.get("template"), "arm": raw.get("arm"), "phase": r.get("phase"),
                     "sample_id": raw.get("sample_id"), "row_id": r["row_id"], "seed": raw.get("seed"),
                     "prompt_sha256": raw.get("prompt_sha256"), "label": r["label"],
                     "labeller_source": r.get("labeller_source"), "passed": bool(r.get("passed")),
                     "finish_reason": raw.get("finish_reason"), "n_new_tokens": raw.get("n_new_tokens"),
                     "code_sha256": r.get("code_sha256"), "code": code,
                     "prose_chars": (r.get("prose_before") or 0) + (r.get("prose_after") or 0)
                     if r.get("prose_before") is not None else None,
                     "event_id": raw.get("event_id"), "round": raw.get("round"), "weight": raw.get("weight"),
                     "hit": raw.get("hit"), "ast_label": r.get("ast_label"), "runtime_label": r.get("runtime_label"),
                     "judge_label": r.get("judge_label")})
    return write_jsonl(DATA / "samples.jsonl", rows)


def method_out(analysis: dict, labels: list[dict], raw_by: dict, meta: dict) -> dict:
    ev = read_json(PRED / "events.json")
    fcs = read_json(PRED / "forecasts.json")["events"]
    fams = ["SUBTRACT", "LADDER", "ASSOCIATE", "PROXIMITY"]
    ex_events = []
    for e in ev["events"]:
        fc = fcs[e["event_id"]]
        a = analysis["events"][e["event_id"]]
        sc, tab = a["scored"], a["table"]
        ban1 = P.p_ban(e["task"], e["banned"], 1)
        inp = (f"Event {e['event_id']} ({e['event_type']}): Llama-3.1-8B-Instruct is told not to use "
               f"{P.display(e['task'], e['banned'])} on task {e['task']}; default D = {e['D']}. "
               f"Survivors: {', '.join(fc['S'])}. W1 ban prompt:\n{ban1['text']}")
        x = {"input": inp, "output": _s(sc["hit_label"])}
        for f in fams:
            x[f"predict_{f.lower()}"] = _s(sc["top1"][f])
        x["predict_renorm"] = _s(max(fc["B_S"], key=fc["B_S"].get))
        x.update({"metadata_task": e["task"], "metadata_event_type": e["event_type"], "metadata_banned": e["banned"],
                  "metadata_gate": sc["gate"], "metadata_landing_counts": tab["landing_counts"],
                  "metadata_correct_counts": tab["correct_counts"], "metadata_hill_cc": tab["hill_cc"],
                  "metadata_other_share": tab["other_share"], "metadata_invalid_share": tab["invalid_share"],
                  "metadata_logscore": sc["logscore"], "metadata_logscore_pm": a["scored_pm"]["logscore"],
                  "metadata_disagreeing": sc["disagreeing"], "metadata_winner": sc["winner"],
                  "metadata_margin": sc["margin"], "metadata_top1_hit": sc["top1_hit"], "metadata_s_X": fc["s_X"],
                  "metadata_flags": fc["flags"], "metadata_forecasts": {k: v["f"] for k, v in fc["families"].items()},
                  "metadata_ngram": [(g or {}).get("decoded") for g in (fc.get("ngram") or [])],
                  "metadata_baseline_nonX_share": tab["baseline_nonX_share"],
                  "metadata_disguise_rate": tab["disguise_rate"]})
        ex_events.append(x)
    ex_bans = []
    lab_by = {r["row_id"]: r for r in labels}
    for rid, raw in raw_by.items():
        if raw.get("phase") not in ("G1", "G2"):
            continue
        lab = lab_by.get(rid)
        if not lab:
            continue
        eid = raw.get("event_id")
        a = analysis["events"].get(eid)
        prompt = P.p_ban(raw["task"], raw["mode"], int(raw["template"]))["text"]
        x = {"input": prompt, "output": lab["label"]}
        for f in fams:
            x[f"predict_{f.lower()}"] = _s(a["scored"]["top1"][f]) if a else "undefined"
        code, _ = L.extract(raw.get("text"))
        x.update({"metadata_event_id": eid, "metadata_task": raw["task"], "metadata_template": raw["template"],
                  "metadata_sample_id": raw["sample_id"], "metadata_seed": raw["seed"],
                  "metadata_passed": bool(lab.get("passed")), "metadata_labeller_source": lab.get("labeller_source"),
                  "metadata_code": (code or "")[:4000], "metadata_finish_reason": raw.get("finish_reason")})
        ex_bans.append(x)
    datasets = [{"dataset": "llama_bench_events", "examples": ex_events},
                {"dataset": "llama_ban_samples", "examples": ex_bans}]
    if (RESULTS / "screen.json").exists():
        scr = read_json(RESULTS / "screen.json")
        ex_scr = []
        for t, v in scr.items():
            sc = v["scored"]
            x = {"input": f"Screen event {t}: exp10 Llama-3.1-8B-Instruct ban landing on path task {t} "
                          f"(banned: {'bfs' if t == 't1' else 'dijkstra'}); forecasts are ban-free and computed in this "
                          f"artifact. exp10 attempted counts under the ban: {json.dumps(v['exp10_ban_landing'])}",
                 "output": _s(sc["hit_label"])}
            for f in fams:
                x[f"predict_{f.lower()}"] = _s(v["forecast_top1"].get(f))
            x.update({"metadata_task": t, "metadata_logscore": sc["logscore"], "metadata_logscore_pm": v["logscore_pm"],
                      "metadata_gate": sc["gate"], "metadata_disagreeing": sc["disagreeing"],
                      "metadata_winner": sc["winner"], "metadata_margin": sc["margin"],
                      "metadata_note": "descriptive screen, never pooled"})
            ex_scr.append(x)
        if ex_scr:
            datasets.append({"dataset": "llama_screen_events", "examples": ex_scr})
    out = {"metadata": meta, "datasets": datasets}
    write_json(WS / "method_out.json", out)
    return out
