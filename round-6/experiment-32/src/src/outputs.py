#!/usr/bin/env python3
"""method_out.json (exp_gen_sol_out) + mini / preview variants, data/samples.jsonl (one row per program with the
direction's shared fields) and results/{costs,timing,deviations}.json.

Datasets: nla_behaviour (one example per behaviour program), nla_readout_states (one per readout state: the NLA
readout against the text-only and outside-reader baselines), nla_causal (one per causal-arm program)."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import (CACHE_DIR, DATA_DIR, MODEL_ID, MODEL_REVISION, PRED_DIR, RESULTS_DIR, ROOT, read_json, read_jsonl,
                 write_json, write_jsonl)

GPU = "NVIDIA L4 24GB"


def sfx(v: Any) -> Any:
    if isinstance(v, (dict, list)):
        return json.dumps(v)
    return v


def shared(r: dict[str, Any], arm: str, site: str | None, alpha: Any) -> dict[str, Any]:
    return {"model": f"{MODEL_ID}@{MODEL_REVISION}", "task": r["task"], "arm": arm, "site": site or "none",
            "band": "L20", "layer": 20, "rank_k": None, "lambda": None, "alpha": alpha,
            "direction_seed": r.get("direction_seed"), "engine": "bf16-hf", "template": r.get("template"),
            "slot": r.get("slot"), "temperature": 1.0, "top_k": None, "thinking": None, "precision": "bf16",
            "gpu": GPU, "prompt_sha256": r.get("prompt_sha256"), "label": r.get("label"),
            "labeller_source": r.get("labeller_source"), "passed": bool(r.get("passed")),
            "finish_reason": r.get("finish_reason"), "n_new_tokens": r.get("n_new_tokens"),
            "realised_disp": r.get("realised_disp"), "code_sha256": r.get("code_sha256"), "code": r.get("code")}


def main() -> None:
    c1 = read_json(PRED_DIR / "commit1_defaults.json")
    c2 = read_json(PRED_DIR / "commit2_readout.json")
    labels = read_jsonl(DATA_DIR / "labels.jsonl")
    lab_c = read_jsonl(DATA_DIR / "labels_causal.jsonl")
    raw = {r["sample_id"]: r for r in read_jsonl(DATA_DIR / "samples_raw.jsonl")}
    raw_c = {r["sample_id"]: r for r in read_jsonl(DATA_DIR / "samples_causal_raw.jsonl")}
    st = {(r["task"], r["kind"], r["w"], r.get("mode") or "-"): r for r in read_jsonl(DATA_DIR / "prompts_static.jsonl")}
    bans = {(r["task"], r["w"]): r for r in read_jsonl(DATA_DIR / "prompts_ban.jsonl")}
    by_sha = {}
    for p in list(st.values()) + list(bans.values()):
        by_sha[p["prompt_sha256"]] = p
    # ---------------- samples.jsonl (every program)
    samples = []
    for r in labels:
        rr = raw.get(r["sample_id"], {})
        samples.append(shared(r | {"prompt_sha256": rr.get("prompt_sha256")}, r["arm"], None, None) |
                       {"sample_id": r["sample_id"], "cell": r.get("cell") or r["arm"], "mode": r.get("mode"),
                        "edit_class": None, "state_ids": None, "delta_norm_ratio": None})
    for r in lab_c:
        rr = raw_c.get(r["sample_id"], {})
        samples.append(shared(r | {"prompt_sha256": rr.get("prompt_sha256")}, "CAUSAL", r.get("site"), r.get("alpha")) |
                       {"sample_id": r["sample_id"], "cell": r.get("cell"), "mode": r.get("mode"),
                        "edit_class": r.get("edit_class"), "state_ids": r.get("state_ids"),
                        "delta_norm_ratio": r.get("delta_norm_ratio"),
                        "readback_max_relerr": rr.get("readback_max_relerr")})
    write_jsonl(DATA_DIR / "samples.jsonl", samples)
    # ---------------- dataset 1: behaviour
    ex_b = []
    for r in labels:
        rr = raw.get(r["sample_id"], {})
        p = by_sha.get(rr.get("prompt_sha256"), {})
        D = c1["tasks"][r["task"]]["default"]
        e = {"input": p.get("user_text", ""), "output": str(r.get("label")),
             "predict_committed_default": str(D), "predict_frozen_labeller": str(r.get("label"))}
        for k, v in shared(r, r["arm"], None, None).items():
            e[f"metadata_{k}"] = sfx(v)
        e["metadata_sample_id"] = r["sample_id"]
        e["metadata_mode"] = r.get("mode")
        e["metadata_response_text"] = (rr.get("text") or "")[:4000]
        ex_b.append(e)
    # ---------------- dataset 2: readout states
    idx = {r["state_id"]: r for r in read_jsonl(CACHE_DIR / "states_index.jsonl")}
    jud = read_jsonl(DATA_DIR / "judgements.jsonl")
    expl_txt = {e["expl_id"]: e for e in read_jsonl(DATA_DIR / "explanations.jsonl")}
    cos = read_json(RESULTS_DIR / "explanation_cosines.json") if (RESULTS_DIR / "explanation_cosines.json").exists() else {}
    by_state = defaultdict(list)
    text_lab = {}
    for j in jud:
        if j["mode"] == "EXPL":
            by_state[j["state_id"]].append(j)
        else:
            text_lab[(j["mode"], j["text_id"])] = j["resolved"]
    modal = {}
    for r in labels:
        if r.get("passed"):
            modal.setdefault((r["task"], r["arm"], r.get("mode") or "-", r["template"]), Counter())[r["label"]] += 1
    ex_r = []
    for sid in c2["readout_state_ids"]:
        r = idx.get(sid)
        if r is None:
            continue
        t, cond, mode, w = r["task"], r["condition"], r.get("mode"), r["template"]
        js = sorted(by_state.get(sid, []), key=lambda j: int(j["expl_id"].split("#")[-1]))
        top = [j["resolved"] for j in js[:3]]
        cnt = Counter(top)
        nla = cnt.most_common(1)[0][0] if cnt and cnt.most_common(1)[0][1] >= 2 else ("no_majority" if top else "not_judged")
        if r["kind"] == "PREFILL":
            p = bans[(t, w)] if cond == "ban" else st[(t, "forced", w, mode)] if cond == "forced" else \
                st[(t, "seed", w, "-")] if cond == "seed" else st[(t, "twin", w, "-")]
            tid = f"{t}|{cond}|{mode or '-'}|{w}|PREFILL"
            text = p["user_text"]
            arm = {"twin": "TWIN", "ban": "BAN", "forced": "FORCED", "seed": "SEED"}[cond]
            m = modal.get((t, arm, mode if cond in ("ban", "forced") else "-", w), Counter())
            truth = m.most_common(1)[0][0] if m else "no_correct_program"
        elif r["kind"] == "GEN":
            p = bans[(t, w)] if cond == "ban" else st[(t, "forced", w, mode)] if cond == "forced" else st[(t, "twin", w, "-")]
            tid = f"{t}|{cond}|{mode or '-'}|{w}|{r['position']}|{r['slot']}"
            text = p["user_text"] + "\n\nAssistant (beginning of its answer):\n" + r.get("prefix_text", "")
            lab = next((x for x in labels if x["sample_id"] == r["sample_id"]), None)
            truth = lab["label"] if lab else "unlabelled"
        else:  # RAND
            p = st[(t, "twin", w, "-")]
            tid = None
            text = p["user_text"]
            m = modal.get((t, "TWIN", "-", w), Counter())
            truth = m.most_common(1)[0][0] if m else "no_correct_program"
        e = {"input": text, "output": str(truth), "predict_nla": str(nla),
             "predict_text_only_name": str(text_lab.get(("NAME", tid))) if tid else "n/a",
             "predict_outside_reader": str(text_lab.get(("PREDICT", tid))) if tid else "n/a",
             "metadata_state_id": sid, "metadata_task": t, "metadata_condition": cond, "metadata_mode": mode,
             "metadata_template": w, "metadata_position": r["position"], "metadata_kind": r["kind"],
             "metadata_default": c1["tasks"][t]["default"], "metadata_Ystar": c2["tasks"][t]["Ystar"],
             "metadata_explanations": json.dumps([{"idx": int(j["expl_id"].split("#")[-1]),
                                                   "text": expl_txt.get(j["expl_id"], {}).get("text", "")[:1200],
                                                   "J1": j.get("J1"), "J2": j.get("J2"), "J3": j.get("J3"),
                                                   "resolved": j["resolved"], "ar_cos": cos.get(j["expl_id"])}
                                                  for j in js]),
             "metadata_norm_h": r.get("norm_h21")}
        ex_r.append(e)
    # ---------------- dataset 3: causal
    ex_c = []
    c3 = read_json(PRED_DIR / "commit3_causal.json") if (PRED_DIR / "commit3_causal.json").exists() else {"causal_plan": []}
    Ymap = {p["task"]: p["Y"] for p in c3["causal_plan"]}
    for r in lab_c:
        rr = raw_c.get(r["sample_id"], {})
        p = by_sha.get(rr.get("prompt_sha256"), {})
        e = {"input": f"[cell {r.get('cell')}] " + p.get("user_text", ""), "output": str(r.get("label")),
             "predict_edit_target": str(Ymap.get(r["task"])), "metadata_cell": r.get("cell"),
             "metadata_sample_id": r["sample_id"], "metadata_edit_class": r.get("edit_class"),
             "metadata_delta_norm_ratio": r.get("delta_norm_ratio"),
             "metadata_readback_max_relerr": rr.get("readback_max_relerr")}
        for k, v in shared(r, "CAUSAL", r.get("site"), r.get("alpha")).items():
            e[f"metadata_{k}"] = sfx(v)
        ex_c.append(e)
    # ---------------- dataset 4: exploratory causal cells (not pre-registered)
    ex_x = []
    for fname in ("labels_causal_extra.jsonl", "labels_causal_extra2.jsonl"):
        raw_x = {r["sample_id"]: r for r in read_jsonl(DATA_DIR / fname.replace("labels_", "samples_").replace(".jsonl", "_raw.jsonl"))}
        for r in read_jsonl(DATA_DIR / fname):
            rr = raw_x.get(r["sample_id"], {})
            p = by_sha.get(rr.get("prompt_sha256"), {})
            e = {"input": f"[cell {r.get('cell')}] " + p.get("user_text", ""), "output": str(r.get("label")),
                 "predict_edit_target": str(Ymap.get(r["task"])), "metadata_cell": r.get("cell"),
                 "metadata_sample_id": r["sample_id"], "metadata_exploratory": True,
                 "metadata_delta_norm": r.get("delta_norm_ratio"), "metadata_edit_class": r.get("edit_class")}
            for k, v in shared(r, "CAUSAL_EXPLORATORY", r.get("site"), r.get("alpha")).items():
                e[f"metadata_{k}"] = sfx(v)
            ex_x.append(e)
    # ---------------- dataset 5: exploratory local positive control
    ex_l = []
    lidx = {r["state_id"]: r for r in read_jsonl(CACHE_DIR / "local_states_index.jsonl")}
    for j in read_jsonl(DATA_DIR / "local_judgements.jsonl"):
        r = lidx.get(j["state_id"], {})
        ex_l.append({"input": j["text"], "output": str(r.get("mode")), "predict_nla_planned": str(j["resolved"]),
                     "predict_nla_mentions_target": str(r.get("mode") in (j.get("mentioned_any") or [])),
                     "metadata_state_id": j["state_id"], "metadata_task": r.get("task"),
                     "metadata_condition": r.get("condition"), "metadata_position": r.get("position"),
                     "metadata_token": r.get("token"), "metadata_exploratory": True})
    meta: dict[str, Any] = {"method_name": "NLA readout of the planned algorithm (Qwen2.5-7B-Instruct, layer 20)",
                            "description": __doc__}
    for name in ("behaviour", "engine_check", "tests_cpu", "regate", "states_summary", "av_smoke", "layer_convention",
                 "gate", "judge_calibration", "judges_run", "readout", "causal", "causal_run", "novelty",
                 "dependency_usage", "rederive", "causal_exploratory", "causal_exploratory_followup", "local_control",
                 "geometry", "causal_extra_run", "causal_extra2_run", "prereg_guard", "rederive_headlines"):
        p = RESULTS_DIR / f"{name}.json"
        if p.exists():
            meta[name] = read_json(p)
    meta["deviations"] = read_jsonl(RESULTS_DIR / "deviations.jsonl")
    meta["commitments"] = [json.loads(l) for l in (ROOT / "commitments.log").read_text().splitlines() if l.strip()]
    costs = read_jsonl(RESULTS_DIR / "costs_judges.jsonl")
    spend_bench = sum(json.loads(l).get("cost", 0) or 0 for l in (ROOT / "logs" / "openrouter_spend.jsonl").read_text().splitlines()
                      if l.strip()) if (ROOT / "logs" / "openrouter_spend.jsonl").exists() else 0.0
    cpath = read_json(RESULTS_DIR / "openrouter_cost_paths.json") if (RESULTS_DIR / "openrouter_cost_paths.json").exists() else {}
    cost_summary = {"nla_judges_usd": sum(c.get("cost") or 0 for c in costs),
                    "by_model": dict(Counter({c["model"]: 0 for c in costs})),
                    "bench_code_judges_usd": spend_bench, "path_code_judges": cpath}
    for c in costs:
        cost_summary["by_model"][c["model"]] = cost_summary["by_model"].get(c["model"], 0) + (c.get("cost") or 0)
    write_json(RESULTS_DIR / "costs.json", cost_summary)
    meta["costs"] = cost_summary
    timing = read_jsonl(RESULTS_DIR / "timing_batches.jsonl")
    write_json(RESULTS_DIR / "timing.json", {"batches": timing,
                                             "total_generation_seconds": sum(t["seconds"] for t in timing)})
    write_json(RESULTS_DIR / "deviations.json", meta["deviations"])
    out = {"metadata": meta, "datasets": [d for d in (
        {"dataset": "nla_behaviour", "examples": ex_b},
        {"dataset": "nla_readout_states", "examples": ex_r},
        {"dataset": "nla_causal", "examples": ex_c},
        {"dataset": "nla_causal_exploratory", "examples": ex_x},
        {"dataset": "nla_local_control_exploratory", "examples": ex_l}) if d["examples"]]}
    (ROOT / "method_out.json").write_text(json.dumps(out, default=str))
    mini = {"metadata": {"method_name": meta["method_name"], "description": meta["description"]},
            "datasets": [{"dataset": d["dataset"], "examples": d["examples"][:3]} for d in out["datasets"]]}
    (ROOT / "mini_method_out.json").write_text(json.dumps(mini, indent=1, default=str))

    def trunc(o: Any) -> Any:
        if isinstance(o, str):
            return o[:200]
        if isinstance(o, dict):
            return {k: trunc(v) for k, v in o.items()}
        if isinstance(o, list):
            return [trunc(v) for v in o]
        return o
    (ROOT / "preview_method_out.json").write_text(json.dumps(trunc(mini), indent=1, default=str))
    print({d["dataset"]: len(d["examples"]) for d in out["datasets"]})


if __name__ == "__main__":
    main()
