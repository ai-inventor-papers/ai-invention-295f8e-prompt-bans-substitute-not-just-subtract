#!/usr/bin/env python3
"""S12 outputs: method_out.json in the exp_gen_sol_out schema. Datasets: novb2_search_programs (one example per call,
seeds 2-3, all arms incl. NS), novb2_extension_programs (exploratory seeds 4-5), novb2_best_programs,
novb2_v3_candidates, novb2_corpus, novb2_v5. Metadata: verdicts, analyses, commits, deviations, costs, engine, timings."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

import analysis as AN  # noqa: E402
import clusters as CL  # noqa: E402
import common as C  # noqa: E402

ARMS = ["T1.0", "T1.6", "DTB", "RPB", "IDEA", "NS"]


def jl(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


def engine_record() -> dict:
    txt = (C.LOGS / "vllm.log").read_text(errors="ignore")
    out = {"engine_tag": C.ENGINE_TAG}
    for key, pat in [("model_loading", r"Model loading took ([^\n]*)"),
                     ("available_kv_cache_memory", r"Available KV cache memory: ([^\n]*)"),
                     ("gpu_kv_cache_size", r"GPU KV cache size: ([^\n]*)")]:
        m = re.findall(pat, txt)
        out[f"search_engine_{key}"] = m[0].strip() if m else None
        out[f"v5_engine_{key}"] = m[-1].strip() if len(m) > 1 else None
    out["cuda_graphs"] = "skipped (vLLM logged 'Skipping CUDA graph capture' under -O0)" \
        if "Skipping CUDA graph capture" in txt else "captured"
    out["search_engine_gpu_memory_utilization"] = 0.93
    out["v5_engine_gpu_memory_utilization"] = 0.80
    C.write_json(C.RESULTS / "engine.json", out)
    return out


def base_fork_feasibility(eng: dict) -> dict:
    d = {"instruct_engine_weights_GiB": 8.91, "base_fp8_weights_GiB_min": 8.9, "base_bf16_weights_GiB": 16.4,
         "kv_min_GiB_per_engine": 2.0, "gpu_total_GiB": 23.52, "budget_0.93_GiB": round(0.93 * 23.52, 2),
         "fp8_pair_need_GiB": round(8.91 + 2.0 + 8.9 + 2.0, 2), "bf16_pair_need_GiB": round(8.91 + 2.0 + 16.4 + 2.0, 2),
         "decision": "dropped: the protocol forbids two models on the GPU (an FP8 pair would need ~21.8 GiB of the "
                     "21.9 GiB budget with no activation headroom; a bf16 base engine does not fit)",
         "engine": eng}
    C.write_json(C.RESULTS / "base_fork_feasibility.json", d)
    return d


def labels_and_parent_agreement(gen: dict, ev: dict, dec: np.ndarray, seeds: list[int]) -> tuple[dict, dict]:
    """Per call: behaviour-cluster label within its arm-seed (complete linkage 0.95) and max agreement with a parent."""
    lab_of, par_of = {}, {}
    pid_vec = {}
    for (S, arm, c), e in ev.items():
        if e["valid"] and e.get("probe_row") is not None:
            pid_vec[f"S{S}-{arm}-c{c}"] = dec[e["probe_row"]]
    cor = json.loads((C.RESULTS / "corpus.json").read_text())
    cdec = np.load(C.DATA / "corpus_decisions.npy")
    names = [e["name"] for e in cor["entries"]]
    pid_vec["seed-BF"], pid_vec["seed-FF"] = cdec[names.index("BF")], cdec[names.index("FF")]
    for S in seeds:
        for a in ARMS:
            es = [ev[k] for k in sorted(k for k in ev if k[0] == S and k[1] == a)]
            vecs, kept = AN.offspring_vectors(es, dec)
            if kept:
                labs, _ = AN.cluster_programs(vecs)
                for e, l in zip(kept, labs):
                    lab_of[(S, a, e["call"])] = int(l)
            for e in es:
                g = gen.get((S, a, e["call"]))
                if g is None or e.get("probe_row") is None or not e["valid"]:
                    continue
                v = dec[e["probe_row"]]
                ags = [float(CL.agreement_matrix(v, pid_vec[p])[0, 0]) for p in g["parent_ids"] if p in pid_vec]
                if ags:
                    par_of[(S, a, e["call"])] = max(ags)
    return lab_of, par_of


def program_examples(gen: dict, ev: dict, lab_of: dict, par_of: dict, seeds: list[int]) -> list[dict]:
    out = []
    for (S, a, c), g in sorted(gen.items(), key=lambda kv: (kv[0][0], ARMS.index(kv[0][1]), kv[0][2])):
        if S not in seeds:
            continue
        e = ev.get((S, a, c), {})
        inp = {"arm": a, "seed": S, "round": g["round"], "call": c, "island": g.get("island"),
               "parent_ids": g["parent_ids"], "parent_F": g["parent_F"], "prompt_sha256": g["prompt_sha256"],
               "condition": g["condition"], "template": g["template"]}
        ex = {"input": json.dumps(inp), "output": g["code"],
              "predict_valid": str(bool(e.get("valid"))).lower(),
              "predict_F": "" if e.get("F") is None else f"{e['F']:.6f}",
              "predict_cluster": "" if (S, a, c) not in lab_of else f"S{S}-{a}-k{lab_of[(S, a, c)]}",
              "predict_agreement_parent_max": "" if (S, a, c) not in par_of else f"{par_of[(S, a, c)]:.4f}",
              "metadata_error_type": e.get("error_type"), "metadata_truncated": g["truncated"],
              "metadata_n_tokens": g["n_tokens"], "metadata_prompt_tokens": g.get("prompt_tokens"),
              "metadata_cached_duplicate": bool(e.get("cached")), "metadata_stochastic": bool(e.get("stochastic")),
              "metadata_bins25": e.get("bins25"), "metadata_fs_F": e.get("fs_F"), "metadata_engine": g["engine"],
              "metadata_label": g["label"]}
        br = g.get("branch")
        if br:
            ex["metadata_branch"] = {k: br.get(k) for k in ("no_branch", "j", "H_j", "r", "forced_id", "forced_text",
                                                            "gen_j_id", "gen_j_text", "forced_eq_gen", "gen_j_rank",
                                                            "j_is_global_argmax", "token_class_gen_j", "n_cand_j")}
            ex["metadata_branch"]["n_eligible"] = len(br.get("E", []))
            ex["metadata_branch"]["r1_tokens"] = g.get("r1_tokens")
            ex["metadata_branch"]["r2_tokens"] = g.get("r2_tokens")
        out.append(ex)
    return out


@logger.catch(reraise=True)
def main() -> None:
    C.setup_logging("outputs")
    eng = engine_record()
    bff = base_fork_feasibility(eng)
    C.SEEDS = [2, 3]
    gen23, ev = AN.load_rows()
    dec = AN.load_decisions()
    gen45 = {}
    for S in (4, 5):
        for r in C.read_jsonl(C.DATA / f"gen_s{S}.jsonl"):
            gen45[(r["seed"], r["arm"], r["call"])] = r
    gen_all = dict(gen23)
    gen_all.update(gen45)
    lab_of, par_of = labels_and_parent_agreement(gen_all, ev, dec, [2, 3, 4, 5])
    ds = [{"dataset": "novb2_search_programs", "examples": program_examples(gen23, ev, lab_of, par_of, [2, 3])}]
    if gen45:
        ds.append({"dataset": "novb2_extension_programs",
                   "examples": program_examples(gen45, ev, lab_of, par_of, [4, 5])})
    hb = jl(C.RESULTS / "heldout_best.json")
    best = []
    for k, r in hb["seed_best"].items():
        best.append({"input": json.dumps({"arm_seed": k, "selection_F": r["F"], "call": r["call"]}),
                     "output": r["code"], "predict_excess_H_FSW5k": f"{r['excess'].get('H-FSW5k', float('nan')):.6f}",
                     "predict_excess_H_OR3": f"{r['excess'].get('H-OR3', float('nan')):.6f}",
                     "metadata_excess_all": r["excess"], "metadata_excess_over_bf": r["excess_over_bf"],
                     "metadata_paired_vs_bf": r["paired_vs_bf"], "metadata_errors": r["errors"],
                     "metadata_artifact_best": any(v["call"] == r["call"] and v.get("from_seed") == r["seed"] and a == r["arm"]
                                                   for a, v in hb["artifact_best"].items())})
    ds.append({"dataset": "novb2_best_programs", "examples": best})
    v3 = jl(C.RESULTS / "v3_final.json")
    ds.append({"dataset": "novb2_v3_candidates", "examples": [
        {"input": json.dumps({"cid": c["cid"], "arm": c["arm"], "seed": c["seed"], "call": c["call"], "F": c["F"],
                              "cluster": c["cluster"]}), "output": c["code"],
         "predict_pass_08": str(bool(c["pass_08"])).lower(),
         "predict_max_corpus_agreement": f"{c['max_corpus_agreement']:.4f}",
         "predict_manual_class": c.get("manual_class") or "", "predict_judge_labels": json.dumps(c.get("judge_labels") or {}),
         "metadata_excess": c.get("excess"), "metadata_nearest_corpus": c.get("nearest_corpus"),
         "metadata_nearest_ab": c.get("nearest_ab"), "metadata_manual_rule": c.get("manual_rule"),
         "metadata_manual_family": c.get("manual_family"), "metadata_judged": c.get("judged"),
         "metadata_oid": c.get("oid")} for c in v3]})
    cor = jl(C.RESULTS / "corpus.json")["entries"]
    ds.append({"dataset": "novb2_corpus", "examples": [
        {"input": json.dumps({"name": e["name"], "family": e["family"], "source_url": e["source_url"], "commit": e["commit"]}),
         "output": e["code"], "predict_F": "" if e["F"] is None else f"{e['F']:.6f}",
         "metadata_heldout_excess": e["heldout_excess"], "metadata_flag_nonfinite": e["flag_nonfinite"],
         "metadata_set_errors": e["set_errors"], "metadata_adapter_note": e["adapter_note"],
         "metadata_program_sha256": e["program_sha256"], "metadata_source_sha256": e["source_sha256"],
         "metadata_p10_sha256": e.get("p10_sha256")} for e in cor]})
    v5 = jl(C.RESULTS / "v5.json")
    if v5 and v5["offspring"]:
        ds.append({"dataset": "novb2_v5", "examples": [
            {"input": json.dumps({k: o[k] for k in ("seed", "arm", "call", "F", "parent_ids")}),
             "output": json.dumps({k: o.get(k) for k in ("decision_position", "control_position", "realised_text",
                                                         "argmax_text")}),
             "predict_decision_reversion": "" if o.get("decision_reversion") is None else f"{o['decision_reversion']:.4f}",
             "predict_control_reversion": "" if o.get("control_reversion") is None else f"{o['control_reversion']:.4f}",
             "metadata_H_decision": o.get("H_decision"), "metadata_n_nonargmax": o.get("n_nonargmax")}
            for o in v5["offspring"]]})
    cl = jl(C.RESULTS / "analysis_clusters.json")
    meta = {
        "method_name": "NOV-B2: FunSearch-style island search with decision-token branching (Qwen3-8B-FP8 mutator)",
        "artifact_plan_id": "gen_plan_experiment_2_idx2",
        "verdicts": jl(C.RESULTS / "verdicts.json"),
        "clusters": {k: {kk: v.get(kk) for kk in ("C", "clusters", "D_per_1000", "clusters_F_below_1", "leader_clusters",
                                               "n_unique_vectors", "linkage_invariant", "clusters_per_million_tokens",
                                               "sens_excl_stochastic", "sens_excl_err5", "sens_informative",
                                               "sens_fs_rescored", "rarefied_clusters", "desc")}
                     for k, v in cl["per_arm_seed"].items()},
        "clusters_union_seeds": cl["union"], "matched_calls": cl["matched_calls"],
        "heldout": {"bf": hb["bf"], "artifact_best": {a: {k: v[k] for k in ("F", "excess", "excess_over_bf", "paired_vs_bf")}
                                                       for a, v in hb["artifact_best"].items()},
                    "comparison": hb["comparison"], "tuned_ab_name": hb["tuned_ab_name"]},
        "v3_summary": (jl(C.RESULTS / "verdicts.json") or {}).get("V3"),
        "manual_read": jl(C.RESULTS / "manual_read.json")["summary"],
        "judges": {k: v for k, v in jl(C.RESULTS / "judges.json").items() if k != "candidates"},
        "v5": (v5 or {}).get("summary"), "hf_replay": (jl(C.RESULTS / "hf_replay.json") or {}).get("summary"),
        "extension_seeds_4_5": jl(C.RESULTS / "extension_ext45.json"),
        "probe_gate": {k: v for k, v in jl(C.RESULTS / "probes.json").items() if k != "ref_decisions"},
        "harness_gate": {k: v for k, v in jl(C.RESULTS / "s0_verify.json").items() if k != "ext"},
        "tests_offline": jl(C.RESULTS / "tests_offline.json"),
        "smoke_test": {a: {k: v for k, v in d.items() if k != "bodies"} for a, d in jl(C.RESULTS / "smoke.json")["arms"].items()},
        "s3b_dependency_scan": jl(C.RESULTS / "s3b_scan.json")["counts"],
        "s3c_positioning": {k: v for k, v in jl(C.RESULTS / "positioning.json").items() if k != "sources"},
        "s3c_sources": [{k: s[k] for k in ("source", "url", "version", "verdict", "heuristic_code")}
                        for s in jl(C.RESULTS / "positioning.json")["sources"]],
        "tuned_ab": {k: v for k, v in jl(C.RESULTS / "tuned_ab.json").items() if k != "evaluated"},
        "stateful_baselines": {k: ({"F": v["F"], "heldout_excess": v["heldout_excess"]} if isinstance(v, dict) else v)
                               for k, v in jl(C.RESULTS / "corpus_stateful.json").items()},
        "commitments_log": (C.ROOT / "commitments.log").read_text().strip().splitlines(),
        "deviations": jl(C.RESULTS / "deviations.json"),
        "costs": {"openrouter_judges_usd": jl(C.RESULTS / "judges.json")["spend_usd"], "gpu": "1x RTX 4090 24 GB, local vLLM"},
        "engine": eng, "base_fork_feasibility": bff,
        "timings": C.read_jsonl(C.LOGS / "time_ledger.jsonl"),
        "search_config": jl(C.RESULTS / "search_config.json"),
    }
    out = {"metadata": meta, "datasets": ds}
    C.write_json(C.ROOT / "method_out.json", out, indent=None)
    logger.info("method_out.json: " + ", ".join(f"{d['dataset']}={len(d['examples'])}" for d in ds))


if __name__ == "__main__":
    main()
