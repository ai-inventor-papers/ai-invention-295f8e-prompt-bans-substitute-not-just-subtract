#!/usr/bin/env python3
"""Build method_out.json (exp_gen_sol_out): one example per search call, plus best programs, V3 candidates, the corpus
and V5; metadata carries every analysis, the verdicts, C*, costs, tokens and deviations."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"


def rj(name: str):
    p = RES / name
    return json.loads(p.read_text()) if p.exists() else None


def s(x) -> str:
    return "" if x is None else (x if isinstance(x, str) else json.dumps(x))


def search_examples(cl: dict) -> list[dict]:
    lab = {}
    for key, st in cl["streams"].items():
        for cid, l in zip(st["valid_call_ids"], st["labels"]):
            lab[(st["run"], st["seed"], st["arm"], cid)] = l
    out = []
    for run in ("main", "ns"):
        for r in analysis.load_rows(run):
            f = r.get("fork") or {}
            ex = {"input": json.dumps({"parent_ids": r["parent_ids"], "parent_F": r["parent_F"], "prompt_sha": r["prompt_sha"],
                                       "arm": r["arm"], "seed": r["seed"], "round": r["round"], "call_id": r["call_id"],
                                       "k": r["k"], "island": r["island"]}),
                  "output": r.get("code") or "",
                  "predict_valid": "1" if analysis.valid(r) else "0",
                  "predict_F": s(r.get("F")),
                  "predict_cluster": s(lab.get((run, r["seed"], r["arm"], r["call_id"]))),
                  "metadata_pid": r["pid"], "metadata_run": run, "metadata_arm": r["arm"], "metadata_seed": r["seed"],
                  "metadata_round": r["round"], "metadata_call_id": r["call_id"], "metadata_error_type": r["error_type"],
                  "metadata_error_msg": (r.get("error_msg") or "")[:200], "metadata_n_gen_tokens": r["n_gen_tokens"],
                  "metadata_truncated": r["truncated"], "metadata_duplicate": r["duplicate"],
                  "metadata_cache_hit": r.get("cache_hit", False), "metadata_bins25": r.get("bins25"),
                  "metadata_temperature": r["temperature"], "metadata_top_p": r["top_p"], "metadata_engine": r["engine"],
                  "metadata_vllm_seed": r.get("vllm_seed"), "metadata_eval_s": r.get("eval_s")}
            if f:
                ex.update({"metadata_fork_j": f.get("j"), "metadata_fork_unforced": f.get("unforced"),
                           "metadata_fork_n_E": f.get("n_E"), "metadata_fork_forced_rank": f.get("forced_rank"),
                           "metadata_fork_forced_text": f.get("forced_text"), "metadata_fork_realised_rank": f.get("realised_rank"),
                           "metadata_fork_class": f.get("class_realised"), "metadata_wasted_tokens": r.get("wasted_tokens")})
            out.append(ex)
    return out


def main() -> None:
    cl = rj("clusters.json")
    best = (rj("best_programs.json") or {}).get("best", {})
    v3c = rj("v3_candidates.json") or {}
    v3f = rj("v3_final.json") or {}
    corpus = json.loads((ROOT / "data" / "corpus" / "corpus.json").read_text())
    v5 = rj("v5.json")
    datasets = [{"dataset": "novb1_search_programs", "examples": search_examples(cl)}]
    datasets.append({"dataset": "novb1_best_programs", "examples": [
        {"input": json.dumps({"stream": k, "pid": v["pid"], "selection": "min F on SEL-OR + SEL-W, ties to shorter code"}),
         "output": v["code"], "predict_F": s(v["F"]), "predict_heldout_excess_pct": s(v.get("heldout_excess_pct")),
         "metadata_arm": v["arm"], "metadata_seed": v["seed"], "metadata_run": v["run"], "metadata_round": v["round"],
         "metadata_heldout_error": v.get("error")} for k, v in best.items()]})
    cls_by = {c["anon_id"]: c for c in v3f.get("classes", [])}
    cand_ex = []
    for c in v3c.get("candidates", []):
        aud = next((a for a in v3c.get("audited", []) if a["pid"] == c["pid"]), None)
        aid = aud["anon_id"] if aud else None
        cand_ex.append({"input": json.dumps({"pid": c["pid"], "stream": c["stream"], "cluster": c["cluster"]}),
                        "output": c["code"], "predict_F": s(c["F"]), "predict_NB": "1" if c["NB"] else "0",
                        "predict_NB_strict": "1" if c["NB_strict"] else "0",
                        "predict_class": s((cls_by.get(aid) or {}).get("final_class")) if aid else "",
                        "metadata_exc_FSW5k": c["exc_FSW5k"], "metadata_exc_OR3": c["exc_OR3"],
                        "metadata_max_corpus_agreement": c["max_corpus_agreement"],
                        "metadata_nearest_corpus": c["nearest_corpus"], "metadata_nearest3": c["nearest3"],
                        "metadata_max_abgrid_agreement": c["max_abgrid_agreement"],
                        "metadata_nearest_abgrid": c["nearest_abgrid"], "metadata_anon_id": aid,
                        "metadata_arm": c["arm"], "metadata_seed": c["seed"]})
    if cand_ex:
        datasets.append({"dataset": "novb1_v3_candidates", "examples": cand_ex})
    datasets.append({"dataset": "novb1_corpus", "examples": [
        {"input": json.dumps({"name": e["name"], "family": e["family"], "url": e.get("url"), "commit": e.get("commit")}),
         "output": e["code"], "predict_F": s(e.get("F")), "predict_heldout_excess_pct": s(e.get("heldout_excess_pct")),
         "metadata_adapter_note": e["adapter_note"], "metadata_code_sha256": e["code_sha256"],
         "metadata_file_sha256": e.get("file_sha256"), "metadata_access_utc": e.get("access_utc")}
        for e in corpus["entries"]]})
    if v5 and v5.get("per_position"):
        datasets.append({"dataset": "novb1_v5", "examples": [
            {"input": json.dumps({"founder_pid": x["pid"], "kind": x["kind"], "position": x["p"]}),
             "output": json.dumps({"valid": x["valid"], "invalid": x["invalid"], "reverted": x["reverted"]}),
             "predict_reversion_rate": s(x["reversion_rate"]), "metadata_arm": x["arm"]} for x in v5["per_position"]]})
    meta = {"method_name": "NOV-B1: FunSearch-style island search with Qwen3-8B-FP8 on online bin packing; decision-token "
                           "branching (DTB) vs temperature (T1.0, T1.6) vs random-position placebo (RPB) vs idea "
                           "instruction (IDEA), with a no-selection arm (NS)",
            "commitments": (ROOT / "commitments.log").read_text().splitlines(),
            "c_star": json.loads((ROOT / "predictions" / "commit2.json").read_text()),
            "verdicts": {"V1": (rj("v1.json") or {}).get("verdict"), "V2": (rj("v2.json") or {}).get("verdict"),
                         "V3": v3f.get("verdict"), "V6": (rj("v6.json") or {}).get("verdict"),
                         "V5": "descriptive" if v5 else "not run"},
            "v1": rj("v1.json"), "v2": rj("v2.json"), "v3_final": v3f,
            "v3_summary": {k: v for k, v in v3c.items() if k not in ("candidates", "audited")},
            "v5_summary": None if not v5 else {k: v for k, v in v5.items() if k not in ("per_position", "founders")},
            "v6": rj("v6.json"), "evaluator_effect": rj("evaluator_effect.json"), "placebos": rj("placebos.json"),
            "clusters": {k: {kk: vv for kk, vv in v.items() if kk not in ("labels", "valid_call_ids", "leader_labels",
                                                                          "curves")} for k, v in cl["streams"].items()},
            "harness_gate": {k: v for k, v in (rj("harness_gate_v10.json") or {}).items() if k in
                             ("G_HARNESS_PASS", "gate_block_identical_to_bp9", "exact_targets", "calibration")},
            "probes": {k: v for k, v in (rj("probes.json") or {}).items() if k in ("file_sha256", "states_sha256",
                                                                                 "self_agreement", "tests")},
            "corpus": {k: v for k, v in (rj("corpus.json") or {}).items() if k != "table"},
            "calibration": {k: v for k, v in (rj("calibration.json") or {}).items() if k not in ("agreement_matrix", "names")},
            "judge_gate": rj("judge_gate.json"), "costs": rj("costs.json"), "deviations": rj("deviations.json"),
            "rederive": rj("rederive.json"), "throughput": rj("throughput.json")}
    out = {"metadata": meta, "datasets": datasets}
    (ROOT / "method_out.json").write_text(json.dumps(out, default=str))
    print("method_out.json:", {d["dataset"]: len(d["examples"]) for d in datasets})


if __name__ == "__main__":
    main()
