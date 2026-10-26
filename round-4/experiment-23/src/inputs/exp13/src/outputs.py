#!/usr/bin/env python3
"""3.7 outputs: data/samples.jsonl (one protocol row per sample, every arm, with veto metadata) and method_out.json
(exp_gen_sol_out): dataset 'modal_ban_samples' (one example per ban sample; output = label|pass; predict_* = the
committed top-1 of each primary forecast family) and dataset 'ban_free_arm_samples' (every ban-free arm sample)."""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from common import (DECODING, DEFAULTS, MODEL_ID, PRED, PROMPTS, RESULTS, ROOT, TASK_ORDER, bench_import, read_json,
                    read_jsonl, write_jsonl)

RAW_ARMS = ["twin", "oneshot", "sham", "persistent", "iter1", "iter2", "iter3", "nonce", "novelty", "rand", "hf_twin",
            "ban", "bandpatch"]
ARM_DESC = {
    "twin": "neutral twin prompt (token-length matched, no named content)",
    "oneshot": "neutral twin + one-shot veto of the default's distinctive n-gram (coupled to twin)",
    "sham": "neutral twin + one-shot veto of a non-distinctive n-gram shared by every algorithm (control)",
    "persistent": "neutral twin + persistent veto of the distinctive n-gram (chain round 0)",
    "iter1": "persistent veto, iterated round 1 (mask + n-gram re-derived on round-0 default programs)",
    "iter2": "persistent veto, iterated round 2", "iter3": "persistent veto, iterated round 3",
    "nonce": "nonce ban ('the Zorblax method') in the W1-W5 templates",
    "novelty": "novelty instruction",
    "rand1": "matched-norm random direction 1 patched into task-spec states, layers 12-23 (HF)",
    "rand2": "matched-norm random direction 2 (HF)", "rand3": "matched-norm random direction 3 (HF)",
    "hf_twin": "neutral twin sampled through the HF engine (engine-artefact control)",
    "ban": "named modal ban of the default (W1-W5)",
    "bandpatch": "band-patch positive control: the ban's own task-spec states patched into the twin, layers 12-23",
}


def sample_rows() -> list[dict]:
    bench_import()
    from bench.common.harness import extract_code

    from vllm_stage import Store

    store = Store("")
    out = []
    for arm in RAW_ARMS:
        raw = {r["sample_id"]: r for r in store.raw_rows(arm)}
        labs = store.lab_rows(arm)
        for l in labs:
            r = raw.get(l["sample_id"])
            if r is None:
                continue
            code = extract_code(r.get("text"))
            row = {"task": r["task"], "condition": r["arm"], "template": r["template"], "paraphrase_id": None,
                   "sample_id": r["sample_id"], "seed": r["seed"], "model": MODEL_ID,
                   "decoding": r.get("decoding", DECODING), "engine": r.get("engine"),
                   "label": l["label"], "labeller_source": l["labeller_source"], "passed": bool(l.get("passed")),
                   "code_sha256": l.get("code_sha256"), "code": code, "ast_label": l.get("ast_label"),
                   "runtime_label": l.get("runtime_label"), "judge_label": l.get("judge_label"),
                   "finish_reason": r.get("finish_reason"), "n_tokens": r.get("n_tokens"),
                   "banned_default": DEFAULTS[r["task"]], "prompt_key": r.get("prompt_key"), "utc": r.get("utc")}
            for k in ["base_sample_id", "round", "veto_mode", "mask", "n_vetoes", "vetoes", "veto_cap", "text_leak",
                      "leaks", "remaining_completions", "direction"]:
                if k in r:
                    row[k] = r[k]
            out.append(row)
    return out


def method_out(rows: list[dict]) -> dict[str, Any]:
    fc = read_json(PRED / "forecasts.json")
    an = read_json(RESULTS / "analysis.json")
    prompts = {}
    for p in read_jsonl(PROMPTS / "prompts.jsonl"):
        prompts[f"{p['task']}|{p['arm']}|{p['template']}"] = p["text"]
    dev = [json.loads(l)["deviation"] for l in (RESULTS / "deviations.jsonl").read_text().splitlines() if l.strip()] \
        if (RESULTS / "deviations.jsonl").exists() else []

    def preds(t: str) -> dict[str, str]:
        f = fc["tasks"][t]["families"]
        return {f"predict_{k.lower()}": (f[k]["top1"] or "undefined") for k in
                ["SUBTRACT", "LADDER", "ASSOCIATE", "PROXIMITY"]}

    def ex(r: dict) -> dict:
        key = r.get("prompt_key") or ""
        text = prompts.get(key, "")
        e = {"input": text, "output": f"{r['label']}|{'pass' if r['passed'] else 'fail'}", **preds(r["task"]),
             "metadata_task": r["task"], "metadata_arm": r["condition"], "metadata_arm_description":
                 ARM_DESC.get(r["condition"], r["condition"]), "metadata_template": r["template"],
             "metadata_sample_id": r["sample_id"], "metadata_seed": r["seed"],
             "metadata_banned_default": r["banned_default"], "metadata_label": r["label"],
             "metadata_passed": r["passed"], "metadata_labeller_source": r["labeller_source"],
             "metadata_engine": r["engine"], "metadata_finish_reason": r["finish_reason"],
             "metadata_n_tokens": r["n_tokens"], "metadata_code": r["code"] or ""}
        if "n_vetoes" in r:
            e["metadata_n_vetoes"] = r["n_vetoes"]
            e["metadata_text_leak"] = r.get("text_leak")
            e["metadata_veto_round"] = r.get("round")
            e["metadata_base_sample_id"] = r.get("base_sample_id")
        if "direction" in r:
            e["metadata_direction"] = r["direction"]
        return e

    ban = [ex(r) for r in rows if r["condition"] == "ban"]
    free = [ex(r) for r in rows if r["condition"] != "ban"]
    meta = {"method_name": "Predicting where coding bans send a model (iteration 3, Qwen3-8B bf16)",
            "artifact_plan_id": "gen_plan_experiment_1_idx2", "model": f"{MODEL_ID} @ b968826d (bf16)",
            "decoding": DECODING,
            "baseline_vs_method": "Ban-free forecasts of where the named modal ban lands: SUBTRACT (token vetoes of the "
                                  "default's distinctive n-gram, our method) and LADDER (generic pushes) vs the "
                                  "ASSOCIATE (free-form association) and PROXIMITY (AST edit distance) baselines, plus "
                                  "a UNIFORM reference; all scored by mean log score under one frozen smoothing.",
            "predict_fields": "predict_subtract / predict_ladder / predict_associate / predict_proximity = committed "
                              "top-1 survivor of each family for the example's task ('undefined' = family undefined; "
                              "scored as uniform)",
            "commitment": {"chain_head": an.get("chain_head"), "log": "commitments.log"},
            "c1": an["c1"], "c1_coveto_sensitivity": an["c1_coveto_sensitivity"],
            "c2b": {k: ({kk: vv for kk, vv in v.items() if kk != "events"} if isinstance(v, dict) else v)
                    for k, v in an["c2b"].items()},
            "c2b_events_oneshot": an["c2b"]["oneshot"]["events"],
            "forecasts": {t: {f: {k: v for k, v in d.items() if k in ("defined", "top1", "top1_tie", "p_raw", "reason",
                                                                       "source_round", "flags", "nominee",
                                                                       "LADDER_EXISTS", "qualifying_pushes")}
                              for f, d in fc["tasks"][t]["families"].items()} for t in fc["tasks"]},
            "descriptives": an["descriptives"], "template_effect": an["template_effect"],
            "template_effect_placebo": an["template_effect_placebo_shuffled"],
            "deviations": dev}
    for extra in ["labeller_recheck.json", "veto_unit_tests.json", "hook_unit_tests.json", "env.json",
                  "bench_verification.json", "dependency_provenance.json", "tamper_test.json", "band_patch.json",
                  "frlp_rescore.json", "rederive.json", "ban_sampling_times.json", "norms_summary.json",
                  "posthoc_sensitivity.json", "sanity.json", "labeller_recheck.json", "prompt_report.json",
                  "commitment_head.json", "rederive_raw.json"]:
        p = RESULTS / extra
        if p.exists():
            meta[extra.replace(".json", "")] = read_json(p)
    return {"metadata": meta, "datasets": [{"dataset": "modal_ban_samples", "examples": ban},
                                           {"dataset": "ban_free_arm_samples", "examples": free}]}


def main() -> None:
    rows = sample_rows()
    write_jsonl(ROOT / "data" / "samples.jsonl", rows)
    logger.info(f"data/samples.jsonl: {len(rows)} rows")
    mo = method_out(rows)
    (ROOT / "method_out.json").write_text(json.dumps(mo, indent=1, default=str))
    logger.info(f"method_out.json: {len(mo['datasets'][0]['examples'])} ban + {len(mo['datasets'][1]['examples'])} "
                f"ban-free examples")


if __name__ == "__main__":
    from common import setup_logging

    setup_logging("s3_outputs")
    main()
