#!/usr/bin/env python3
"""Bookkeeping + outputs: costs6.json (OpenRouter ledgers of this artifact), timing6.json (GPU seconds per stage from
results/timing_batches6.jsonl), deviations.json (every logged deviation), verdicts6.json (headline readouts),
commit-chain verification, then figures6.py and outputs6.py (method_out.json)."""

from __future__ import annotations

import collections
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import LOG_DIR, PRED_DIR, RESULTS_DIR, ROOT, read_json, read_jsonl, write_json
import commit as C

DEVIATIONS = {
    "D1": "GPU is one NVIDIA L4 (23 GB, the same card type as exp28) instead of the planned RTX A4500 (20 GB); bf16 as "
          "planned. The engine check therefore compares like with like: per-slot label agreement 0.99 (twin 150/150, "
          "R6 alpha-2 push 8/10), byte identity 0.91, JS(old, new) = 0 (results/engine_check6.json).",
    "D2": "The pinned Gemma snapshots were no longer in the run's shared HF cache (exp28's copy was cleaned); they were "
          "re-downloaded at the same pinned revisions (it@093f9f38, pt@cc012e0a); key maps and vocabularies equal "
          "exp28's recorded hashes (U5).",
    "D3": "exp28's cache/hit_<task>_<W>.pt states (1.4 GB) were read in place for the U6 equality check instead of being "
          "copied into inputs/; the recomputed states are bit-identical on 40/40 (task, template) pairs.",
    "D4": "Labeller re-check: 8 of the 300 re-labelled exp28 rows were 'disputed' in exp28 (judge rate limits) and are "
          "now judged; all other 292 rows reproduce their exp28 label and pass flag exactly.",
    "D5": "CPU test T10: one synthetic case had a wrong expectation (the frozen stop rule ignores an incomplete last "
          "line and stops one line later); the expectation was corrected, the rule is unchanged.",
    "D6": "Twin top-up rows run in exp28's multi-prompt batches (B 50 = 5 templates x 10 slots); the T 1.3 rows use the "
          "same CRN uniforms as T 1.0 slots 0-19 with a per-row temperature in the same sampler.",
    "D7": "q_lik name scrubbing for the path tasks T1/T2 adds a path-alias pass after the frozen bench scrubber (whose "
          "lexicon has no A*/IDDFS/bidirectional/Dijkstra/Bellman-Ford/SPFA/Dial/Floyd aliases).",
    "D8": "Priming check: a Monte-Carlo permutation test of independence with the chi-square statistic (10k "
          "permutations), the Monte-Carlo counterpart of the planned Fisher-Freeman-Halton test.",
    "D9": "U7 (teacher forcing batch 1 vs batch 4 with right padding) differs by up to 0.15 nats per token in bf16; "
          "as planned, every q_lik pass is batch 1.",
    "D11": "Few-shot pt batches: the first 100 T2 draws ran in multi-prompt batches of 40 (masked decode, ~160 ms/step); "
           "the job was stopped (PID-based) and resumed with single-prompt batches of 50 per exemplar family (no mask, "
           "~85 ms/step), push units first. CRN uniforms per draw are unchanged; batch_kind is recorded per row.",
    "D12": "Stages B and C of the few-shot top-up ran only for the 8 push units (the only units that can have events); "
           "the 7 non-push units got stage A (100 draws). Decided on time alone, before any stage-B row.",
    "D13": "With >= 20 correct pt programs the frozen rule is correct-only, and on T03, T08 and T13 every correct pt program is the default: r_u is UNDEFINED there (q_base = add-one over zero counts = uniform). T03's iteration-5 runner-up (quickselect) rested on broken attempts; undefined forecasts are excluded from hit tests and scored as uniform in the log-score contest (defined-only results beside).",
}


def spend() -> dict:
    out = {}
    tot = 0.0
    for p in sorted(LOG_DIR.glob("openrouter_spend*.jsonl")):
        rows = read_jsonl(p)
        c = sum((r.get("cost") or 0.0) for r in rows)
        by = collections.Counter()
        for r in rows:
            by[r.get("purpose") or r.get("judge") or "bench_judge"] += r.get("cost") or 0.0
        out[p.name] = {"usd": c, "n_calls": len(rows), "by_purpose": dict(by)}
        tot += c
    for p in sorted(RESULTS_DIR.glob("openrouter_cost_paths*.json")):
        v = float(read_json(p).get("total_usd", 0.0))
        out[p.name] = {"usd": v}
        tot += v
    return {"ledgers": out, "openrouter_usd_total_artifact": tot, "cap_usd_plan": 1.5, "cap_usd_artifact": 10.0}


def timing() -> dict:
    rows = read_jsonl(RESULTS_DIR / "timing_batches6.jsonl")
    by = collections.defaultdict(float)
    n = collections.Counter()
    for r in rows:
        by[r["stage"]] += r["seconds"]
        n[r["stage"]] += r["B"]
    tf = read_jsonl(ROOT / "data" / "qlik_tf.jsonl")
    return {"gpu_seconds_by_stage": dict(by), "programs_by_stage": dict(n),
            "gpu_hours_generation": sum(by.values()) / 3600, "n_programs_generated": sum(n.values()),
            "n_teacher_forced_passes": len(tf)}


def verdicts() -> dict:
    l1 = read_json(RESULTS_DIR / "l1_contest.json")
    p = l1["primary_pooled"]
    ot = read_json(RESULTS_DIR / "old_tally.json")
    out = {"label": "REPLICATION (Gemma's iteration-5 landings were seen); never pooled with Qwen"}
    if p.get("n_events"):
        c = p["logscore_contests"]
        out.update({
            "n_events_pooled": p["n_events"], "n_clear_landings": p["n_clear_landing"],
            "hits_r_u": f"{p['hits_r_u_all']['hits']}/{p['hits_r_u_all']['n_events']}",
            "hits_r_u_p": p["hits_r_u_all"]["poisson_binomial_p"],
            "hits_t_u": f"{p['hits_t_u_all']['hits']}/{p['hits_t_u_all']['n_events']}",
            "hits_qlik": f"{p['hits_qlik_all']['hits']}/{p['hits_qlik_all']['n_events']}",
            "L1a": p["L1a_tail_empty"]["verdict"], "L1a_hits": f"{p['L1a_tail_empty']['hits']}/{p['L1a_tail_empty']['n_events']}",
            "L1b": (f"{p['L1b_discordant_lik']['base_only']} base-only vs {p['L1b_discordant_lik']['rival_only']} "
                    f"lik-only of {p['L1b_discordant_lik']['n_events']} discordant events; sign p = "
                    f"{p['L1b_discordant_lik']['sign_test_p_one_sided']}"),
            "logscore_base_minus_tail": c["base_vs_tail"].get("mean_diff_nats"),
            "logscore_base_vs_tail_noninferior": c["base_vs_tail"].get("noninferior"),
            "logscore_base_minus_lik": c["base_vs_lik_norm"].get("mean_diff_nats"),
            "logscore_base_minus_lik_raw": c["base_vs_lik_raw"].get("mean_diff_nats")})
        uo = p.get("logscore_contests_uniform_other") or {}
        ox = p.get("logscore_contests_other_excluded") or {}
        out.update({
            "logscore_note": "the log-score sign depends on the 'other' bin: primary (frozen, per-forecast 'other') vs "
                             "one fixed 0.02 'other' for every forecast vs 'other' excluded",
            "logscore_base_minus_tail_uniform_other": (uo.get("base_vs_tail") or {}).get("mean_diff_nats"),
            "logscore_base_vs_tail_noninferior_uniform_other": (uo.get("base_vs_tail") or {}).get("noninferior"),
            "logscore_base_minus_lik_uniform_other": (uo.get("base_vs_lik_norm") or {}).get("mean_diff_nats"),
            "logscore_base_vs_lik_uniform_other_wilcoxon_p": (uo.get("base_vs_lik_norm") or {}).get("wilcoxon_exact_p_one_sided"),
            "logscore_base_minus_tail_other_excluded": (ox.get("base_vs_tail") or {}).get("mean_diff_nats"),
            "logscore_base_minus_lik_other_excluded": (ox.get("base_vs_lik_norm") or {}).get("mean_diff_nats"),
            "hits_r_u_exemplar_sensitive_excluded": (lambda h: f"{h['hits']}/{h['n_events']}")(
                l1["sensitivities"]["exemplar_sensitive_excluded"]["hits"]),
            "hits_r_u_audit_fail_excluded": (lambda h: f"{h['hits']}/{h['n_events']}")(
                l1["sensitivities"]["audit_fail_excluded"]["hits"]),
            "fresh_only": {"n_events": l1["split_fresh_only"].get("n_events"),
                           "hits_r_u": f"{l1['split_fresh_only']['hits_r_u_all']['hits']}/{l1['split_fresh_only']['hits_r_u_all']['n_events']}",
                           "hits_t_u": f"{l1['split_fresh_only']['hits_t_u_all']['hits']}/{l1['split_fresh_only']['hits_t_u_all']['n_events']}",
                           "hits_qlik": f"{l1['split_fresh_only']['hits_qlik_all']['hits']}/{l1['split_fresh_only']['hits_qlik_all']['n_events']}"}})
    out["old_tally_repaired"] = ot["all7"]["hit_repaired"]
    out["old_tally_exp28"] = ot["all7"]["hit_exp28"]
    return out


def main() -> None:
    write_json(RESULTS_DIR / "costs6.json", spend())
    write_json(RESULTS_DIR / "timing6.json", timing())
    dv = read_json(RESULTS_DIR / "deviations.json") if (RESULTS_DIR / "deviations.json").exists() else {}
    dv.update({k: v for k, v in DEVIATIONS.items() if k not in dv})
    write_json(RESULTS_DIR / "deviations.json", dv)
    write_json(RESULTS_DIR / "commit_chain.json", C.verify_chain_superseded())
    try:
        write_json(RESULTS_DIR / "verdicts6.json", verdicts())
    except (FileNotFoundError, KeyError) as e:
        print(f"verdicts not written: {e}")
    py = str(ROOT / ".venv" / "bin" / "python")
    subprocess.run([py, "src/figures6.py"], cwd=ROOT, check=False)
    subprocess.run([py, "src/outputs6.py"], cwd=ROOT, check=True)
    subprocess.run([py, "src/report6.py"], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    if (ROOT / "docs_head.md").exists():
        subprocess.run([py, "src/build_readme.py"], cwd=ROOT, check=True)
    print(json.dumps(read_json(RESULTS_DIR / "costs6.json")["openrouter_usd_total_artifact"]))


if __name__ == "__main__":
    main()
