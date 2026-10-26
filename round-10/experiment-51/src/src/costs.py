#!/usr/bin/env python3
"""results/costs.json (OpenRouter spend, tokens per arm), throughput.json (round times), deviations.json and
positioning.json (dated search, short quotes as returned by the search tool, one-line verdicts)."""
from __future__ import annotations

import json
import pickle
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"


def main() -> None:
    spend = []
    p = RES / "judge_costs.jsonl"
    if p.exists():
        spend = [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()]
    tok = {}
    for run in ("main", "ns"):
        for r in analysis.load_rows(run):
            k = r["arm"]
            d = tok.setdefault(k, {"calls": 0, "gen_tokens": 0, "wasted_tokens": 0, "valid": 0, "http_fail": 0})
            d["calls"] += 1
            d["gen_tokens"] += r["n_gen_tokens"]
            d["wasted_tokens"] += r.get("wasted_tokens") or 0
            d["valid"] += int(analysis.valid(r))
            d["http_fail"] += int(r["error_type"] == "http")
    for d in tok.values():
        d["tokens_per_call"] = d["gen_tokens"] / max(1, d["calls"])
    costs = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "openrouter_usd_total": sum(x["cost"] for x in spend), "openrouter_calls": len(spend),
             "openrouter_by_model": {m: sum(x["cost"] for x in spend if x["model"] == m) for m in {x["model"] for x in spend}},
             "openrouter_by_batch": {b: sum(x["cost"] for x in spend if x["tag"].startswith(b)) for b in ("gate", "cand")},
             "web_search_queries": 13, "llm_mutator": "local vLLM (no API cost)", "tokens_by_arm": tok,
             "gpu": "1x RTX 4090 24 GB (FP8 weights via Marlin W8A16)"}
    (RES / "costs.json").write_text(json.dumps(costs, indent=1))
    import __main__  # noqa: PLC0415
    import search  # noqa: PLC0415
    __main__.Stream = search.Stream
    thr = {}
    for run in ("main", "ns"):
        sp = ROOT / "data" / run / "state.pkl"
        if sp.exists():
            st = pickle.loads(sp.read_bytes())
            rt = st["round_times"]
            thr[run] = {"rounds": len(rt), "t_round_mean_s": sum(r["t_round"] for r in rt) / max(1, len(rt)),
                        "t_gen_mean_s": sum(r["t_gen"] for r in rt) / max(1, len(rt)),
                        "wall_s": sum(r["t_round"] for r in rt), "round_times": rt}
    (RES / "throughput.json").write_text(json.dumps(thr, indent=1))
    dev = {"deviations": [
        "HF_HOME/TRANSFORMERS_CACHE left at the run's shared cache (system rule) instead of ./hf_cache; VLLM_CACHE_ROOT=./vllm_cache as planned",
        "vLLM served on port 8051 (not 8000) to avoid clashes with other runs; CUDA-graph capture was skipped by vLLM under -O0 (eager decode); KV cache 90,656 tokens (plan expected ~36,864 on an A4500)",
        "EvalPool with 10 workers (cgroup quota 13.6 vCPU) instead of 5; the machine is ~3.5x faster than BP9's (c14 on Weibull 5k 3.4 s vs 11.7 s), so the committed 10 s per-set limit cut fewer slow programs",
        "hard stop moved from 5:00 to 22:05Z (4:19 elapsed) to fit the session limit; it never bound (main finished at 2:48, NS at 2:50)",
        "c12's notebook text times out on H-W10k at 120 s; c12_vec (identical decisions, gate-verified) supplies c12's eight-set scores",
        "MCTS-AHD gpt.py (python loop) times out on SEL-W at 60 s: F undefined; its decision vector is in the corpus",
        "EoH run 3 member 3 is published with 1-space indentation of def and body; whitespace repaired (logged in its adapter note)",
        "confirmation signal 'best-so-far F < 1 at 100 calls' not met (all arms at F = 1.0); the run continued (no pathology rule applies); every stream reached F < 1 later",
        "lag-1 pipeline kept exact across the commit-2 pause: round 5 prompts were drawn before round 4 was registered",
        "V5 first attempt OOM-crashed vLLM (32 concurrent prompt_logprobs=20); vLLM restarted at gpu-memory-utilization 0.80 with concurrency 3/12 (commit #5)",
        "judge gate: only mistral-medium-3.1 passed (9/10); deepseek-v3.1 5/10 (over-calls KNOWN_FAMILY_NEW_PARAMETERS), kimi-k2 6/10 (3 unparsed answers under the committed parser); per plan the judges are advisory, the arm-blind manual read decides V3 (commit #6)",
        "positive control did not raise NB (70 -> 70): every held-out-passing candidate already had max corpus agreement < 0.9, so the 0.9 probe filter did no work in this run",
        "F2 bands are the range over the two seeds, not a bootstrap band over rounds",
        "bf16 replay dropped (first item of the drop order); no (1+1)-EPS arm (as planned)",
        "positioning: only 13 search queries in total (7 corpus + 2 PDF/HTML fetch attempts + 4 positioning); works not re-searched here are carried from the plan's domain reading and marked so",
        "cand_01 (a NOVEL representative) calls np.random.rand: its decisions are stochastic, so its held-out numbers vary slightly between evaluations"]}
    (RES / "deviations.json").write_text(json.dumps(dev, indent=1))
    pos = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "queries": [
        {"query": "arXiv 2604.00018 high-entropy branching decoding", "utc": "2026-10-24T21:17Z",
         "work": "HN-decode (He, Liu, Roth et al., arXiv 2604.00018)",
         "quote": "branches only at those points while maintaining a pool of partial rollouts (search-tool summary)",
         "verdict": "adjacent: entropy-guided branching for reasoning decoding, no evaluator-driven program search, no matched-call comparison against temperature"},
        {"query": "Forking Paths in Neural Text Generation forking tokens uncertainty", "utc": "2026-10-24T21:17Z",
         "work": "Forking Paths (Bigelow, Holtzman, Tanaka, Ullman; ICLR 2025)",
         "quote": "individual forking tokens exist which, if generated, produce dramatic differences in subsequent text",
         "verdict": "adjacent: analysis of forking tokens by swapping top-K alternatives; DTB uses the same intervention as a mutation operator inside an evaluator loop"},
        {"query": "Beyond the 80/20 Rule high-entropy minority tokens reinforcement learning reasoning", "utc": "2026-10-24T21:17Z",
         "work": "Beyond the 80/20 Rule (Wang et al., NeurIPS 2025)",
         "quote": "Only a small fraction (approximately 20%) of tokens exhibit high entropy, and these tokens semantically act as critical forks",
         "verdict": "adjacent (RL training, not sampling-time branching)"},
        {"query": "BehaveSim behavioral similarity LLM heuristic design FunSearch EoH diversity ICLR 2026", "utc": "2026-10-24T21:17Z",
         "work": "BehaveSim (Zhang & Lu, ICLR 2026, arXiv 2603.02787)",
         "quote": "problem-solving trajectories ... compared with dynamic time warping (search-tool summary)",
         "verdict": "adjacent: behaviour-level similarity for AAD; our decision-agreement clusters are a fixed-probe analogue, used here as a measurement, not as a search objective"}],
        "carried_from_plan_domain_reading": {
            "FunSearch / EoH / ReEvo / HSEvo / MCTS-AHD / LLM4AD": "occupy evaluator-driven AHD on online bin packing; corpus entries at pinned commits",
            "2407.10873 (Zhang et al.)": "occupies the RandSample / EPS comparison; our NS arm is its analogue",
            "2501.11411 (Beyond the Hype)": "adjacent: generalisation of LLM heuristics; motivates H-SHIFT/H-W10k",
            "2510.27353 (Herrmann & Pallez)": "occupies the ab principle that 22/30 audited representatives reduce to",
            "RefineEvo 2607.11358": "adjacent: planner/reflection operators; bin-packing code not retrievable",
            "ROSE 2601.05053, ADR 2510.10207, AdapT, Fork-Patched Decoding, DivAlgo, Beneath the Diff, 2604.01193":
                "not re-searched in this artifact (time); per the plan's reading none prices token-level branching as a "
                "mutation operator inside evaluator-driven program search against temperature at matched calls"},
        "corpus_search": "results/corpus_search.json (7 queries, 2026-10-24T18:39Z)"}
    (RES / "positioning.json").write_text(json.dumps(pos, indent=1))
    print("costs", round(costs["openrouter_usd_total"], 4), "USD;", {k: v["tokens_per_call"] for k, v in tok.items()})


if __name__ == "__main__":
    main()
