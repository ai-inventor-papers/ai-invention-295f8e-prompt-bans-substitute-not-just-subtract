#!/usr/bin/env python3
"""Stage implementations called by method.py (thin wrappers over the src/ modules)."""

from __future__ import annotations

import collections
import time
from typing import Any

from loguru import logger

from common import (CONFIGS, INPUTS, PRED, RESULTS, deviation, read_json, read_jsonl, write_json)


def stage_stage0() -> None:
    import setup_tp

    t0 = time.time()
    hw = setup_tp.hardware()
    logger.info(f"hardware: {hw['nvidia_smi']}")
    deviation("D8-hardware", "The GPU is an NVIDIA RTX 2000 Ada (16 GB), not the planned RTX A4500 (20 GB), and the "
                             "container has no C compiler (vLLM runs eager, no CUDA graphs / torch.compile). Qwen3-8B "
                             "and Llama-3.1-8B cannot be served in bf16 by vLLM on 16 GB; see D9.")
    st = setup_tp.copy_inputs()
    logger.info(f"inputs copied: {len(st['copied'])}, missing: {st['missing']}")
    setup_tp.carried_rows()
    import prompts_tp

    top5 = read_jsonl(INPUTS / "exp9" / "data" / "top5_raw_rows.jsonl")
    w1 = next((r["prompt"] for r in top5 if r.get("template") == "W1"), None)
    rc = prompts_tp.renderer_checks(w1)
    write_json(RESULTS / "renderer_checks.json", rc)
    logger.info(f"renderer checks: {rc}")
    if not rc.get("top5_w1_byte_identical"):
        raise RuntimeError("renderer does not reproduce the iteration-2 TOP5 W1 prompt byte for byte")
    setup_tp.validate_labeller()
    logger.info(f"stage0 done in {time.time() - t0:.0f}s")


def stage_gate() -> None:
    import judge_tp

    g = judge_tp.run_gate()
    logger.info(f"gate: pair={g['gated_pair']} third={g['third_judge']}")


def _mock_403_test() -> dict[str, Any]:
    """T4: a local server answering every call with HTTP 403 'AI Inventor per-run OpenRouter budget ...' must stop
    the batch after the first refusal (no further calls once the flag is set)."""
    import asyncio
    import os

    from aiohttp import web

    import sample_or

    hits = {"n": 0}

    async def handler(request: web.Request) -> web.Response:
        hits["n"] += 1
        await asyncio.sleep(0.05)
        return web.Response(status=403, text='{"error": {"message": "AI Inventor per-run OpenRouter budget '
                                             'exhausted (mock)"}}')

    async def main() -> dict[str, Any]:
        app = web.Application()
        app.router.add_post("/v1/chat/completions", handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 18765)
        await site.start()
        old = os.environ["OPENROUTER_BASE_URL"]
        os.environ["OPENROUTER_BASE_URL"] = "http://127.0.0.1:18765/v1"
        try:
            items = [{"arm": "mock", "slot": i, "prompt": "x"} for i in range(40)]
            out = RESULTS / "mock403_rows.jsonl"
            res = await sample_or.run_jobs([("C3", CONFIGS["C3"], items, out)], purpose="mock403", concurrency=4)
        finally:
            os.environ["OPENROUTER_BASE_URL"] = old
            await runner.cleanup()
        return {"stopped": res["stopped"], "server_hits": hits["n"], "n_items": 40, "concurrency": 4,
                "pass": bool(res["stopped"] and hits["n"] <= 4)}

    return asyncio.run(main())


def stage_smoke() -> None:
    """T3-T5: judge gate, OpenRouter smoke (3 calls per configuration), mocked 403, vLLM forced-close smoke."""
    import judge_tp
    import prompts_tp
    import sample_or
    import sample_vllm
    from common import DATA
    from label_tp import extract_last_fence

    out: dict[str, Any] = {}
    out["mock403"] = _mock_403_test()
    logger.info(f"mock 403 test: {out['mock403']}")
    gate = judge_tp.run_gate()
    out["gate"] = {m: v["score"] for m, v in gate["judges"].items()}
    jobs = []
    for cid, cfg in CONFIGS.items():
        if cfg["engine"] != "openrouter":
            continue
        items = [dict(prompts_tp.baseline_prompt(s), arm="smoke") for s in range(3)]
        jobs.append((cid, cfg, items, DATA / f"smoke_{cid}.jsonl"))
    res = sample_or.run(jobs, purpose="smoke", concurrency=24)
    out["or_run"] = res
    sm: dict[str, Any] = {}
    for cid, cfg in CONFIGS.items():
        if cfg["engine"] != "openrouter":
            continue
        rows = read_jsonl(DATA / f"smoke_{cid}.jsonl")
        sm[cid] = {"n": len(rows), "providers": sorted({str(r.get("provider")) for r in rows}),
                   "reasoning_chars": [len(r.get("reasoning") or "") for r in rows],
                   "reasoning_tokens": [r.get("reasoning_tokens") for r in rows],
                   "finish": [r.get("finish_reason") for r in rows],
                   "fence_found": [extract_last_fence(r.get("content"))[0] is not None for r in rows],
                   "cost": [r.get("cost_usd") for r in rows], "completion_tokens": [r.get("completion_tokens")
                                                                                     for r in rows]}
        if not cfg["thinking"] and cfg["family"] == "Qwen3":
            sm[cid]["thinking_off_ok"] = all((x or 0) == 0 for x in sm[cid]["reasoning_tokens"]) and \
                all(c == 0 for c in sm[cid]["reasoning_chars"])
        if cfg["thinking"]:
            sm[cid]["thinking_on_ok"] = all(c > 0 for c in sm[cid]["reasoning_chars"])
        logger.info(f"smoke {cid}: {sm[cid]}")
    out["openrouter"] = sm
    # vLLM forced-close smoke (think budget 64 -> forced close path), 2 generations
    if sample_vllm.server_ready():
        p = DATA / "smoke_C1.jsonl"
        items = [dict(prompts_tp.baseline_prompt(s), arm="smoke") for s in range(2)]
        t0 = time.time()
        rows = sample_vllm.generate(items, p, {"config": "C1", "model": CONFIGS["C1"]["model"]}, think_budget=64,
                                    answer_budget=1536, concurrency=2)
        out["vllm"] = {"n": len(rows), "truncated": [r["thinking_truncated"] for r in rows],
                       "fence_found": [extract_last_fence(r["content"])[0] is not None for r in rows],
                       "seconds": round(time.time() - t0, 1),
                       "completion_tokens": [r["completion_tokens"] for r in rows]}
        logger.info(f"vLLM smoke: {out['vllm']}")
    else:
        out["vllm"] = "server not ready"
    write_json(RESULTS / "smoke.json", out)


def stage_smoke2() -> None:
    """Re-smoke after the fixes (C3/C5 ' /no_think', OpenRouter seed = slot + 1, C7 substitute) + third-judge gate."""
    import judge_tp
    import prompts_tp
    import sample_or
    from common import ADJ_THIRD, DATA, read_json
    from label_tp import extract_last_fence

    jobs = []
    for cid in ("C3", "C5", "C7", "C8"):
        items = [dict(prompts_tp.baseline_prompt(s), arm="smoke2") for s in range(3)]
        jobs.append((cid, CONFIGS[cid], items, DATA / f"smoke2_{cid}.jsonl"))
    sample_or.run(jobs, purpose="smoke", concurrency=12)
    out = read_json(RESULTS / "smoke.json")
    out["smoke2"] = {}
    for cid in ("C3", "C5", "C7", "C8"):
        rows = read_jsonl(DATA / f"smoke2_{cid}.jsonl")
        out["smoke2"][cid] = {"n": len(rows), "providers": sorted({str(r.get("provider")) for r in rows}),
                              "reasoning_tokens": [r.get("reasoning_tokens") for r in rows],
                              "reasoning_chars": [len(r.get("reasoning") or "") for r in rows],
                              "finish": [r.get("finish_reason") for r in rows],
                              "fence_found": [extract_last_fence(r.get("content"))[0] is not None for r in rows],
                              "seconds": [r.get("gen_seconds") for r in rows]}
        logger.info(f"smoke2 {cid}: {out['smoke2'][cid]}")
    controls = read_json(RESULTS / "judge_gate_controls.json")
    res = judge_tp.judge_codes([c["code"] for c in controls], ADJ_THIRD, purpose="gate")
    per = [{"class": c["class"], "label": (r or {}).get("label"), "ok": (r or {}).get("label") == c["class"]}
           for c, r in zip(controls, res)]
    g = read_json(RESULTS / "judge_gate.json")
    g["judges"][ADJ_THIRD] = {"role": "c2", "score": sum(p["ok"] for p in per), "passed": sum(p["ok"] for p in per) >= 8,
                              "per_control": per}
    g["adjudication_pair"] = ["deepseek/deepseek-chat-v3.1", "moonshotai/kimi-k2"]
    g["adjudication_third"] = ADJ_THIRD if g["judges"][ADJ_THIRD]["passed"] else None
    g["labeller_judge"] = judge_tp.LABELLER_JUDGE
    write_json(RESULTS / "judge_gate.json", g)
    logger.info(f"third judge {ADJ_THIRD}: {g['judges'][ADJ_THIRD]['score']}/10")
    write_json(RESULTS / "smoke.json", out)


DEVIATIONS_PLANNED = {
    "D1": "Provider heterogeneity: OpenRouter configurations run at provider precision (DeepInfra fp8 for Qwen3-14B/32B "
          "and gemma-3-27b, Cloudflare unknown for Qwen2.5-Coder-32B, CoreWeave bf16 for Llama-3.1-8B), pinned with "
          "allow_fallbacks false; no CRN coupling; every table and figure carries the engine tag.",
    "D2": "Qwen3-8B thinking-on (C1) is sampled with the official FP8 checkpoint in vLLM 0.11.0 (W8A16 Marlin, eager), "
          "N_base = 30 (baseline known collapsed: art_UoCVh2Qe5RZ0 800/800 BFS); its geometry (if needed) is bf16.",
    "D3": "Geometry on a quantised model (int8/nf4) departs from 'never quantise a model that carries a claim'; the "
          "quantisation check (bf16 vs int8 vs nf4 on Qwen3-8B, state cosines + Spearman of 10x10 geodesic matrices) "
          "runs whenever the selected model is quantised; < 0.8 -> PRECISION-SENSITIVE.",
    "D4": "Algorithm-level exact permutation null (120 permutations of algorithm identities, count profile fixed) is "
          "quoted beside the committed per-program nulls; its floor is 0.2 (1/5) when one algorithm takes every "
          "survivor: one model and one landing algorithm cannot reach algorithm-level significance.",
    "D5": "Correctness filter confound: a can-weighted null C (correct-when-forced rates, +0.5 smoothed) and an "
          "attempted-survivor variant (no pass filter) are reported.",
    "D6": "The 10-class labeller failed its gold gate for dijkstra_unit, JPS and bidirectional A* (iteration 2): every "
          "program that decides the screen is adjudicated (correct candidate survivors, 'other', those 3 classes, plus "
          "a 10% audit of in-banned labels); the adjudicated column is primary.",
    "D7": "Thinking budgets differ: local C1 = two-phase forced close at 8,192 thinking tokens; OpenRouter thinking "
          "configurations are bounded by max_tokens 9,728 and truncate; per-configuration truncation rates reported.",
    "D8": "Hardware: RTX 2000 Ada 16 GB (not A4500 20 GB), no C compiler (vLLM eager, no CUDA graphs).",
    "D9": "C2 Llama-3.1-8B-Instruct is sampled through OpenRouter (CoreWeave bf16, pinned) instead of local vLLM bf16: "
          "bf16 8B weights (16.1 GB) do not fit a 16 GB GPU under vLLM; the GPU is reserved for C1 and the geometry.",
    "D10": "DeepInfra ignores reasoning {enabled:false} for Qwen3 (smoke: ~1,600 reasoning tokens, truncation); the Qwen3 "
           "soft switch ' /no_think' is appended to the user turn of C3 and C5 only (smoke2: reasoning 1 token).",
    "D11": "C7 planned google/gemma-3-12b-it (DeepInfra bf16): endpoints returned 504 after 300 s (2/3 first attempts) "
           "and no other bf16/fp8 provider exists -> same-family substitute google/gemma-3-27b-it (DeepInfra fp8), "
           "chosen before commit #1 over the plan's first substitute (qwen3-30b-a3b) to keep a new Gemma-family row; "
           "states (if selected) from unsloth/gemma-3-27b-it-bnb-4bit (nf4).",
    "D12": "Judge gate: google/gemini-2.5-flash-lite scored 7/10 (failed); adjudication pair = deepseek-chat-v3.1 (9/10) "
           "+ kimi-k2 (10/10); third judge = mistral-medium-3.1 (9/10); the labeller's disagreement judge is "
           "deepseek-chat-v3.1 (iteration 2 used gpt-4.1-mini).",
    "D13": "OpenRouter seed = slot index + 1 (Cloudflare rejects seed 0); local vLLM seed = slot index.",
    "D14": "Primary hidden suite (ITER2 exp9 tests.json) holds 48 cases (the plan text says 45); all 15 T1 references "
           "(the plan's '25' counts T1 + T2) pass all 48 and the 41-case ITER1 exp2 suite.",
}


def stage_commit1() -> None:
    import hashlib

    import prompts_tp
    from common import (ALIAS_TABLE, CANON_ORDER, CARRIED, COMMIT_LOG, CONFIRM_SLOTS, DECODING, DEPTH_RANGE, DISPLAY,
                        PRED, SCREEN_SLOTS, SELECTION, SRC, STATE_CHECKPOINTS, W_TEMPLATES, commit)
    import sample_or

    if COMMIT_LOG.exists() and "commit1" in COMMIT_LOG.read_text():
        logger.warning("commit1 already present; not re-committing")
        return
    src_hash = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(SRC.glob("*.py"))}
    payload = {
        "artifact": "gen_plan_experiment_6_idx7 (iteration 8): top-five ban - who obeys, where survivors land",
        "configurations": {cid: {**cfg, "provider_pin": sample_or.PROVIDER_PINS.get(cid),
                                 "no_think_suffix": sample_or.NO_THINK_SUFFIX.get(cid, False),
                                 "max_tokens": (DECODING["max_tokens_on"] if cfg["thinking"] else
                                                DECODING["max_tokens_off"]) if cfg["engine"] == "openrouter" else
                                 {"think": DECODING["local_think_budget"], "answer": DECODING["local_answer_budget"]},
                                 "seed_policy": "slot + 1 (OpenRouter, best effort)" if cfg["engine"] == "openrouter"
                                 else "slot (vLLM per-request seed)"} for cid, cfg in CONFIGS.items()},
        "carried": CARRIED,
        "decoding": DECODING,
        "prompt_rules": {"spec": "spec.txt verbatim (identical bytes in every prompt)",
                         "baseline": "baseline_templates[s % 10] + blank line + SPEC",
                         "ban": "cap_first(W with {X} = display names of B joined 'A, B, C, D or E' in canonical order "
                                "rotated by W_ROT) + blank line + SPEC",
                         "screen_slots": SCREEN_SLOTS, "confirmation_slots": CONFIRM_SLOTS,
                         "templates": W_TEMPLATES, "canonical_order": CANON_ORDER, "display_names": DISPLAY,
                         "alias_table_forced": ALIAS_TABLE,
                         "forced": "cap_first(forced_templates[t] with {X} = alias_j(a)) + blank line + SPEC; 10 x 3 = "
                                   "30 per algorithm; group = (t, j)",
                         "renderer_sha256": hashlib.sha256((SRC / "prompts_tp.py").read_bytes()).hexdigest(),
                         "renderer_byte_check": read_json(RESULTS / "renderer_checks.json")},
        "banned_set_rule": "B_c = 5 largest implemented counts in c's baseline (adjudicated label; pass or fail; "
                           "'invalid' and 'other' excluded); ties -> higher correct count, then canonical order; if < 5 "
                           "classes have count >= 1, fill from [bfs, dfs, gbfs, iddfs, astar] in that order",
        "labeller": "last ```python fence of the answer (no fence = invalid) -> 48-case ITER2 exp9 suite (primary) + "
                    "41-case ITER1 exp2 suite (secondary) -> exp9 labeller_ext runtime + AST rules -> deepseek-chat-v3.1 "
                    "on disagreement -> exp9 combine = label_raw",
        "adjudication": "A = ban rows that pass with label_raw not in B_c + every row labelled other/dijkstra_unit/jps/"
                        "biastar (baseline rows before commit #2) + stratified random 10% of in-banned ban rows (audit, "
                        "seed 0); two gated judges (deepseek-chat-v3.1, kimi-k2), blind to configuration and arm; agree "
                        "-> adj_label; disagree -> third judge mistral-medium-3.1 + executor manual read decide (logged); "
                        "audit disagreement > 10% for a configuration -> all its ban rows adjudicated",
        "screen_metrics": "correct_survivor = passed and adj_label not in B_c and adj_label in catalogue or known-outside "
                          "(other resolved to a named known algorithm); share_cs with Wilson 95%; attempted_survivor; "
                          "banned_mechanism; name_free_reimpl (code; code+answer+reasoning) by alias regex; pass, invalid, "
                          "truncation; per-template table; baseline-to-ban composition shifts with Newcombe intervals",
        "selection": {**SELECTION, "rule": "Q = {c: share_cs >= 0.20}; m* = argmax share_cs; ties within 0.02 -> higher "
                                           "Wilson lower bound, then fewer parameters, then local; Q empty -> "
                                           "TP_RESULT = 'no tested open model obeys a five-name ban on this task' with "
                                           "every share and one-sided 95% upper bound; geometry DESCRIPTIVE on the "
                                           "configuration with the most correct survivors (C1 = Qwen3-8B bf16 if all 0); "
                                           "no confirmation"},
        "state_checkpoints": STATE_CHECKPOINTS,
        "geometry": {"depth_range": DEPTH_RANGE, "summary": "S-mean = mean of block outputs over tokens whose char "
                     "offsets lie inside SPEC (rendered chat text, offset mapping)",
                     "layer": "L* = argmax over blocks of grouped 10-fold CV balanced accuracy (groups = (t, j); "
                              "standardise, PCA(64) in fold, multinomial LR C=1.0); ties within 0.01 -> block nearest "
                              "depth 0.5; all at ceiling -> block nearest depth 0.5 among ceiling blocks; forced prompts "
                              "only (outcome-blind)",
                     "manifold": "raw float64 coordinates at L*: PCA 2D (EVR), classical MDS on 300 points and 10 "
                                 "centroids with Kruskal stress-1, Isomap k in {5,10,15} on the symmetrised kNN distance "
                                 "graph with shortest inter-component edges added if disconnected (component count "
                                 "recorded), geodesics by scipy shortest_path",
                     "g": "g_k(a) = min over b in B of mean geodesic distance over pairs (points of a, points of b) "
                          "(iteration-7 top5geo.py definition); med = median of g over the 5 non-banned; EDGE g < med, "
                          "MIDDLE g == med, OPPOSITE g > med; Euclidean-centroid variant",
                     "reliability": "split-half Spearman of 10x10 mean-geodesic matrices (groups 0-14 vs 15-29); 1,000 "
                                    "bootstrap resamples of paraphrase groups -> class and nearest-banned stability",
                     "overlays": "Isomap.transform / pca.transform only (never refit)"},
        "landing": {"surv": "correct ban rows of m* whose adj_label is one of the 5 non-banned catalogue algorithms; "
                            "n_s < 5 -> DESCRIPTIVE ONLY",
                    "statistic": "S = mean over Surv of g_k(label) at (L*, k=10; if disconnected the smallest "
                                 "connected k)",
                    "nulls": {"U": "iid uniform over the 5 non-banned, 10,000 draws, seed 0 (committed)",
                              "F": "iid by m*'s baseline frequency among non-banned +0.5 smoothing, 10,000 draws "
                                   "(committed; near-uniform flag if all counts 0)",
                              "P": "exact 120 permutations of algorithm identities, count profile fixed (added)",
                              "C": "iid by correct-when-forced rates +0.5 smoothed (exp9 catalogue_keep passed/40 for "
                                   "Qwen3-8B; others TRANSFERRED unless G6 ran) (added)"},
                    "p": "p_edge = P(S_null <= S); p_opp = P(S_null >= S)",
                    "verdict": "EDGE iff p_edge(U) < 0.05 and p_edge(F) < 0.05 and > 50% of Surv in EDGE algorithms; "
                               "OPPOSITE mirrored; else NEITHER; p(P) and p(C) printed beside",
                    "robustness": "verdict over k in {5,10,15} x blocks L*-2..L*+2 (15 cells); ROBUST iff identical "
                                  "in >= 12/15",
                    "variants": ["attempted survivors (no pass filter)", "Euclidean centroids", "standardised coords"]},
        "prediction": "the selected model's correct survivors land at EDGE of the banned set",
        "confirmation": "only if Q non-empty: commit #4 freezes L*, k, M1 point set, geodesic matrices, g, classes, null "
                        "code and verdict rule; N=50 on m* with W4/W5/P6/P7 (13/13/12/12), same engine and pin; "
                        "CONFIRMED iff verdict equals the screen verdict with p_edge(U) < 0.05 in that direction and a "
                        "majority in the same class; no refit",
        "drop_order": ["G6 forced anchors", "G7 circle check", "held-out confirmation", "C6 Qwen3-32B thinking on",
                       "null F"],
        "never_dropped": [">= 5 screened configurations", "the selection rule",
                          "M1 placement with PCA, MDS and Isomap if a model qualifies"],
        "cost_cap_usd": 3.0,
        "deviations": DEVIATIONS_PLANNED,
        "src_sha256_at_commit1": src_hash,
        "note": "Geometry/landing code is hash-committed at commit #3 (before any geometry is computed on m*); the rules "
                "above are binding.",
    }
    p = PRED / "commit1.json"
    write_json(p, payload)
    commit(p, "commit1", "pre-registration before any screen sample")
    for k, v in DEVIATIONS_PLANNED.items():
        deviation(k, v)


def _check_commit(label: str) -> None:
    from common import commit_time

    if commit_time(label) is None:
        raise RuntimeError(f"{label} missing: refusing to sample")


def stage_screen_base_local() -> None:
    import prompts_tp
    import sample_vllm
    from common import DATA, timing

    _check_commit("commit1")
    cfg = CONFIGS["C1"]
    items = [prompts_tp.baseline_prompt(s) for s in range(cfg["n_base"])]
    t0 = time.time()
    rows = sample_vllm.generate(items, DATA / "raw_C1_baseline.jsonl", {"config": "C1", "model": cfg["model"]},
                                concurrency=8)
    timing("C1_baseline", time.time() - t0, len(rows), "vLLM eager, concurrency 8")


def stage_screen_base_or() -> None:
    import prompts_tp
    import sample_or
    from common import DATA, timing

    _check_commit("commit1")
    jobs = []
    for cid, cfg in CONFIGS.items():
        if cfg["engine"] != "openrouter":
            continue
        items = [prompts_tp.baseline_prompt(s) for s in range(cfg["n_base"])]
        jobs.append((cid, cfg, items, DATA / f"raw_{cid}_baseline.jsonl"))
    t0 = time.time()
    res = sample_or.run(jobs, purpose="screen_baseline", concurrency=32)
    timing("OR_baseline", time.time() - t0, res["n_tasks"], str(res))
    write_json(RESULTS / "screen_base_or_run.json", res)


def stage_t8() -> None:
    """T8: geometry + landing on synthetic data (ring of 10 Gaussian clusters, 5 contiguous banned)."""
    import numpy as np

    import geometry
    import landing
    from common import CANON_ORDER

    X, lab, grp = geometry.synthetic_ring()
    banned = CANON_ORDER[:5]            # contiguous on the ring: positions 0-4
    nonb = CANON_ORDER[5:]              # 5..9; ring neighbours of the banned arc are positions 5 and 9
    m = geometry.manifold(X, lab, banned, fit_isomap=False)
    kp = m["k_primary"]
    g = m[f"k{kp}"]["g"]
    cls = m[f"k{kp}"]["classes"]
    edge_planted = [CANON_ORDER[5]] * 6 + [CANON_ORDER[9]] * 6
    opp_planted = [CANON_ORDER[7]] * 12
    le = landing.landing(g, cls, edge_planted, {a: 0 for a in nonb}, {a: 0.5 for a in nonb})
    lo = landing.landing(g, cls, opp_planted, {a: 0 for a in nonb}, {a: 0.5 for a in nonb})
    rng = np.random.default_rng(1)
    verdicts = []
    for r in range(200):
        surv = list(rng.choice(nonb, size=12))
        verdicts.append(landing.landing(g, cls, surv, {a: 0 for a in nonb}, {a: 0.5 for a in nonb},
                                        draws=2000, seed=r)["verdict"])
    import collections
    vc = collections.Counter(verdicts)
    from ripser import ripser
    from sklearn.decomposition import PCA
    Z = PCA(n_components=20, random_state=0).fit_transform(X)
    dg = ripser(Z, maxdim=1)["dgms"][1]
    maxp = float((dg[:, 1] - dg[:, 0]).max()) if len(dg) else 0.0
    nullp = []
    for s in range(20):
        G = np.random.default_rng(100 + s).multivariate_normal(Z.mean(0), np.cov(Z.T), size=len(Z))
        d2 = ripser(G, maxdim=1)["dgms"][1]
        nullp.append(float((d2[:, 1] - d2[:, 0]).max()) if len(d2) else 0.0)
    out = {"g": g, "classes": cls, "edge_planted": landing.strip(le), "opp_planted": landing.strip(lo),
           "random_200": dict(vc), "random_false_directional_rate": (vc["EDGE"] + vc["OPPOSITE"]) / 200,
           "ripser_ring_maxH1": maxp, "ripser_gauss_null_max": max(nullp),
           "pass": {"edge": le["verdict"] == "EDGE" and le["nulls"]["U"]["p_edge"] < 0.05,
                    "perm_at_floor": le["nulls"]["P"]["p_edge"] <= 0.2 + 1e-9,
                    "opposite": lo["verdict"] == "OPPOSITE",
                    "random_nominal": (vc["EDGE"] + vc["OPPOSITE"]) / 200 <= 0.12,
                    "ring_recovered": maxp > max(nullp)}}
    write_json(RESULTS / "t8_synthetic.json", out)
    logger.info(f"T8: classes {cls}; edge verdict {le['verdict']} pU={le['nulls']['U']['p_edge']:.4f} "
                f"pP={le['nulls']['P']['p_edge']:.3f}; opp verdict {lo['verdict']}; random {dict(vc)}; ripser "
                f"{maxp:.2f} vs null max {max(nullp):.2f}; pass {out['pass']}")


def stage_label(arm: str, cids: str = "") -> None:
    import screen

    ids = [c for c in cids.split(",") if c] or None
    t0 = time.time()
    out = screen.label_arm(arm, ids)
    from common import timing
    timing(f"label_{arm}", time.time() - t0, sum(out.values()), cids)


C1_N_BAN_FLOOR = 30


def stage_commit2() -> None:
    import screen
    from common import timing

    _check_commit("commit1")
    tl = [r for r in read_jsonl(RESULTS / "timing.jsonl") if r["key"] == "C1_baseline"]
    if tl:
        proj = tl[-1]["sec_per_unit"] * (CONFIGS["C1"]["n_base"] + CONFIGS["C1"]["n_ban"]) / 60
        if proj > 45:
            CONFIGS["C1"]["n_ban"] = C1_N_BAN_FLOOR
            deviation("D15-C1-nban", f"C1 projected time {proj:.0f} min for {CONFIGS['C1']['n_base']} + 50 rows "
                                     f"(> 45 min; measured {tl[-1]['sec_per_unit']:.1f} s/row on the 16 GB card) -> "
                                     f"N_ban cut to the committed floor {C1_N_BAN_FLOOR} (W1/W2/W3 10/10/10)")
    t0 = time.time()
    screen.stage_commit2()
    timing("commit2", time.time() - t0, 1)


def _ban_items(cid: str) -> list[dict[str, Any]]:
    import hashlib

    import prompts_tp

    c2 = read_json(PRED / "commit2.json")
    b = c2["banned_sets"][cid]
    planned = c2["ban_prompts"][cid]
    items = prompts_tp.screen_ban_prompts(b, len(planned))
    for it, pl in zip(items, planned):
        assert hashlib.sha256(it["prompt"].encode()).hexdigest() == pl["sha256"], "ban prompt differs from commit #2"
    return items


def stage_screen_ban_local() -> None:
    import sample_vllm
    from common import DATA, timing

    _check_commit("commit2")
    items = _ban_items("C1")
    t0 = time.time()
    rows = sample_vllm.generate(items, DATA / "raw_C1_ban.jsonl", {"config": "C1", "model": CONFIGS["C1"]["model"]},
                                concurrency=8)
    timing("C1_ban", time.time() - t0, len(rows), "vLLM eager, concurrency 8")


def stage_screen_ban_or() -> None:
    import sample_or
    from common import DATA, timing

    _check_commit("commit2")
    jobs = [(cid, cfg, _ban_items(cid), DATA / f"raw_{cid}_ban.jsonl") for cid, cfg in CONFIGS.items()
            if cfg["engine"] == "openrouter"]
    t0 = time.time()
    res = sample_or.run(jobs, purpose="screen_ban", concurrency=32)
    timing("OR_ban", time.time() - t0, res["n_tasks"], str(res))
    write_json(RESULTS / "screen_ban_or_run.json", res)


def stage_adjudicate(arm: str = "ban", cids: str = "") -> None:
    import adjudicate
    import screen
    from common import write_jsonl

    c2 = read_json(PRED / "commit2.json")
    ids = [c for c in cids.split(",") if c] or [c for c in CONFIGS if (screen.raw_path(c, arm)).exists()]
    screen.label_arm(arm, ids)
    p = RESULTS / f"adjudication_{arm}.json"
    stats = read_json(p) if p.exists() else {}
    for cid in ids:
        rows = read_jsonl(screen.labelled_path(cid, arm))
        st = adjudicate.apply_adjudication(rows, banned=c2["banned_sets"][cid], purpose=f"{cid}:{arm}")
        write_jsonl(screen.labelled_path(cid, arm), rows)
        stats[cid] = st
        logger.info(f"adjudicated {cid} {arm}: {st}")
    write_json(p, stats)


def stage_select() -> None:
    import hashlib

    import screen
    from common import SRC, STATE_CHECKPOINTS, commit

    _check_commit("commit2")
    tab = screen.screen_table()
    sel = screen.select(tab)
    for cid, m in sorted(tab.items(), key=lambda kv: kv[0]):
        logger.info(f"{cid:4s} {m['name']:26s} n={m['n']:3d} cs={m['n_correct_survivors']:3d} "
                    f"share={m['share_cs']:.3f} CI={[round(x, 3) for x in m['share_cs_wilson95']]} "
                    f"comp={m.get('composition')}")
    ms = sel["m_star"]
    sel["m_star_checkpoint"] = STATE_CHECKPOINTS[ms]
    sel["survivor_table"] = {c: m.get("survivor_algorithms") for c, m in tab.items()}
    sel["code_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(SRC.glob("*.py"))}
    write_json(RESULTS / "selection.json", sel)
    p = PRED / "commit3.json"
    write_json(p, sel)
    commit(p, "commit3", f"selection: {sel['mode']} m*={ms}; geometry/landing code hashes before any m* geometry")
    logger.info(f"SELECTION: {sel['TP_RESULT']} | mode {sel['mode']} | m* = {ms} {STATE_CHECKPOINTS[ms]}")


# ================================================================================================ geometry stages
def _mstar() -> tuple[str, dict[str, Any], list[str]]:
    sel = read_json(RESULTS / "selection.json")
    ms = sel["m_star"]
    c2 = read_json(PRED / "commit2.json")
    return ms, sel, c2["banned_sets"][ms]


def _thinking_for_states(cid: str) -> bool:
    return bool(CONFIGS[cid]["thinking"]) if cid in CONFIGS else False


def stage_states(cid: str = "", repo: str = "", precision: str = "", tag: str = "") -> None:
    """G0/G1: S-mean states of 300 forced + 10 baseline + 3 screen-ban + 4 confirmation-ban prompts."""
    import numpy as np
    import torch
    from transformers import AutoConfig

    import prompts_tp
    import states
    from common import STATE_CHECKPOINTS

    ms, sel, banned = _mstar() if not cid else (cid, None, read_json(PRED / "commit2.json")["banned_sets"][cid])
    ck = STATE_CHECKPOINTS[ms]
    repo = repo or ck["repo"]
    precision = precision or ck["precision"]
    tag = tag or f"{ms}_{precision}"
    cfg = AutoConfig.from_pretrained(repo)
    n_layers = (cfg.get_text_config() if hasattr(cfg, "get_text_config") else cfg).num_hidden_layers
    sel_b, ext_b = states.block_range(n_layers)
    model, tok, info = states.load_truncated(repo, precision, max(ext_b) + 1)
    tok.padding_side = "right"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    thinking = _thinking_for_states(ms)
    items = prompts_tp.forced_set()
    items += [prompts_tp.baseline_prompt(s) for s in range(10)]
    items += [prompts_tp.ban_prompt(banned, w, i, "ban") for i, w in enumerate(("W1", "W2", "W3"))]
    items += [prompts_tp.ban_prompt(banned, w, i, "confirm") for i, w in enumerate(("W4", "W5", "P6", "P7"))]
    texts = [prompts_tp.render_chat(tok, it["prompt"], thinking) for it in items]
    spec = prompts_tp.SPEC()
    span_info = [states.spec_span(tok, t, spec)[1] for t in texts[:3]]
    hc = states.hook_check(model, tok, texts[:2])
    logger.info(f"hook check {hc}; span {span_info[0]}")
    t0 = time.time()
    X = states.smean_states(model, tok, texts, spec, ext_b, batch=1)   # batch 1: no padding effects
    dt = time.time() - t0
    states.save_npz(f"smean_{tag}", smean=X, blocks=np.array(ext_b), sel_blocks=np.array(sel_b),
                    kind=np.array([it["arm"] for it in items]),
                    algorithm=np.array([it.get("algorithm", "") for it in items]),
                    group=np.array([it.get("group", -1) for it in items]),
                    template=np.array([str(it.get("template")) for it in items]))
    rec = {"config": ms, "tag": tag, "load": info, "n_layers": n_layers, "selection_blocks": sel_b,
           "extracted_blocks": ext_b, "n_prompts": len(items), "thinking_template": thinking,
           "hook_check": hc, "span_check": span_info, "seconds": round(dt, 1), "banned": banned,
           "gpu_name": torch.cuda.get_device_name(0)}
    if precision == "bf16" and "Qwen3-8B" in repo and not repo.endswith("FP8"):
        rec["embed_cpu_vs_gpu"] = _embed_identity_check(model, tok, texts[:2], ext_b[:2])
    states.record(tag, rec)
    logger.info(f"states {tag}: {X.shape} in {dt:.0f}s")
    del model
    torch.cuda.empty_cache()


def _embed_identity_check(model: Any, tok: Any, texts: list[str], blocks: list[int]) -> dict[str, Any]:
    """T7: embedding rows indexed on the CPU vs on the GPU give identical block outputs."""
    import torch

    import states

    dec = states._decoder(model)
    diffs = []
    hook = getattr(dec.embed_tokens, "_hf_hook", None)
    wm = getattr(hook, "weights_map", None) if hook is not None else None
    try:
        W0 = wm["weight"] if wm is not None else dec.embed_tokens.weight
        W0 = W0.detach()
        if W0.is_meta:
            raise RuntimeError("meta tensor")
    except (KeyError, RuntimeError, NotImplementedError) as e:
        return {"identical": None, "note": f"embedding weight not materialised ({type(e).__name__})"}
    for t in texts:
        enc = tok(t, return_tensors="pt", add_special_tokens=False)
        W = W0.to("cuda")
        emb_gpu = torch.nn.functional.embedding(enc["input_ids"].to("cuda"), W)
        emb_cpu = dec.embed_tokens(enc["input_ids"]).to("cuda")
        diffs.append(float((emb_gpu.float() - emb_cpu.float()).abs().max()))
        del W, emb_gpu
    torch.cuda.empty_cache()
    return {"max_abs_diff_embeddings": max(diffs), "identical": max(diffs) == 0.0}


def _load_smean(tag: str) -> dict[str, Any]:
    import numpy as np

    from common import STATES

    z = np.load(STATES / f"smean_{tag}.npz", allow_pickle=False)
    return {k: z[k] for k in z.files}


def _forced_rates(ms: str) -> tuple[dict[str, float], str]:
    from common import CANON_ORDER

    keep = read_json(INPUTS / "exp9" / "results" / "catalogue_keep.json")["tasks"]["t1"]
    rates = {a: keep[a]["passed_as_requested"] / keep[a]["n_forced"] for a in CANON_ORDER}
    src = "exp9 catalogue_keep.json passed_as_requested/40 (Qwen3-8B thinking off)"
    if ms not in ("C1",):
        src += " -- TRANSFERRED (G6 not run for this model)"
    return rates, src


def stage_geometry(tag: str = "") -> None:
    """G2 layer, G3 M1 manifold + reliability, G5 landing + robustness + variants, overlays; figures F2/F3/F4/F6."""
    import collections

    import numpy as np

    import figures
    import geometry
    import landing
    import screen
    from common import CANON_ORDER, STATE_CHECKPOINTS

    ms, sel, banned = _mstar()
    tag = tag or f"{ms}_{STATE_CHECKPOINTS[ms]['precision']}"
    z = _load_smean(tag)
    blocks = [int(b) for b in z["blocks"]]
    sel_b = [int(b) for b in z["sel_blocks"]]
    kind = z["kind"]
    F = kind == "forced"
    Xall = z["smean"].astype(np.float64)
    labels = z["algorithm"][F]
    groups = z["group"][F].astype(int)
    srec = read_json(RESULTS / f"states_{tag}.json")
    n_layers = srec["n_layers"]
    lc = geometry.layer_curve(Xall[F], labels, groups, blocks, sel_b, n_layers)
    L = lc["L_star"]
    logger.info(f"layer curve {lc['curve']} -> L* = {L} ({lc['rule']})")
    X = Xall[F][:, blocks.index(L)]
    m = geometry.manifold(X, labels, banned)
    geometry.log_summary(tag, m)
    kp = m["k_primary"]
    rel = {"split_half": {k: geometry.split_half(X, labels, groups, k) for k in (5, 10, 15)},
           "bootstrap": geometry.bootstrap(X, labels, groups, banned, kp, n_boot=1000)}
    logger.info(f"reliability: split-half {[(k, round(v['spearman_offdiag'], 3)) for k, v in rel['split_half'].items()]}"
                f"; bootstrap class stability {rel['bootstrap']['class_stability']}")
    # standardised-coordinate sensitivity
    mu, sd = X.mean(0), X.std(0) + 1e-8
    m_std = geometry.manifold((X - mu) / sd, labels, banned, fit_isomap=False)
    # behaviour of m*
    base = read_jsonl(screen.labelled_path(ms, "baseline"))
    ban = read_jsonl(screen.labelled_path(ms, "ban"))
    nonb = [a for a in CANON_ORDER if a not in banned]
    impl = collections.Counter(r["adj_label"] for r in base if r["adj_label"] in CANON_ORDER)
    surv = [r["adj_label"] for r in ban if screen.is_correct_survivor(r, banned) and r["adj_label"] in nonb]
    att = [r["adj_label"] for r in ban if r["adj_label"] in nonb]
    rates, rsrc = _forced_rates(ms)
    base_nb = {a: impl.get(a, 0) for a in nonb}
    land = landing.landing(m[f"k{kp}"]["g"], m[f"k{kp}"]["classes"], surv, base_nb, rates)
    land_att = landing.landing(m[f"k{kp}"]["g"], m[f"k{kp}"]["classes"], att, base_nb, rates)
    land_euc = landing.landing(m["euclid_centroid"]["g"], m["euclid_centroid"]["classes"], surv, base_nb, rates)
    land_std = landing.landing(m_std[f"k{kp}"]["g"], m_std[f"k{kp}"]["classes"], surv, base_nb, rates)
    # robustness grid: k x blocks L*-2..L*+2
    grid = {}
    for b in range(L - 2, L + 3):
        if b not in blocks:
            continue
        mb = m if b == L else geometry.manifold(Xall[F][:, blocks.index(b)], labels, banned, fit_isomap=False)
        for k in (5, 10, 15):
            lk = landing.landing(mb[f"k{k}"]["g"], mb[f"k{k}"]["classes"], surv, base_nb, rates, draws=4000)
            grid[f"L{b}_k{k}"] = {"verdict": lk["verdict"], "classes": mb[f"k{k}"]["classes"],
                                  "S": lk.get("S"), "p_edge_U": (lk.get("nulls") or {}).get("U", {}).get("p_edge"),
                                  "p_opp_U": (lk.get("nulls") or {}).get("U", {}).get("p_opp"),
                                  "components": mb[f"k{k}"]["components_before_join"]}
    vc = collections.Counter(v["verdict"] for v in grid.values())
    primary = land["verdict"]
    rob = {"cells": grid, "verdict_counts": dict(vc), "n_cells": len(grid),
           "identical_to_primary": vc[primary], "ROBUST": vc[primary] >= 12 if len(grid) == 15 else
           vc[primary] >= 0.8 * len(grid)}
    # overlays (transform only, never refit)
    pca = m["_emb"]["pca"]
    iso_k, Yk = m["_emb"]["isomap"][kp]
    over = {}
    for kd in ("baseline", "ban", "confirm"):
        Q = Xall[kind == kd][:, blocks.index(L)]
        over[kd] = {"pca": pca.transform(Q)[:, :2].tolist(), "isomap": iso_k.transform(Q).tolist(),
                    "templates": [str(t) for t in z["template"][kind == kd]]}
    res = {"config": ms, "tag": tag, "mode": sel["mode"], "banned": banned, "nonbanned": nonb,
           "forced_pca2": [[round(float(a), 4), round(float(b), 4)] for a, b in pca.transform(X)[:, :2]],
           "layer_curve": lc, "L_star": L, "M1": geometry.strip_private(m), "M1_standardised":
               geometry.strip_private(m_std), "reliability": rel, "overlays": over,
           "baseline_implemented": dict(impl), "engine_tag": f"{ms} states {STATE_CHECKPOINTS[ms]}"}
    write_json(RESULTS / "geometry_M1.json", res)
    lres = {"config": ms, "mode": sel["mode"], "L_star": L, "k": kp, "survivors": surv, "n_surv": len(surv),
            "primary": landing.strip(land), "attempted": landing.strip(land_att),
            "euclid_centroid": landing.strip(land_euc), "standardised": landing.strip(land_std),
            "forced_rates_source": rsrc, "descriptive_only": len(surv) < 5 or sel["mode"] != "SELECTED",
            "note": "correlational description of where behaviour lands; no causal reading (iteration-7 in-manifold "
                    "pushes moved 0/300 programs)"}
    write_json(RESULTS / "landing.json", lres)
    write_json(RESULTS / "landing_robustness.json", rob)
    logger.info(f"LANDING {ms}: n_surv={len(surv)} {dict(collections.Counter(surv))} verdict={land['verdict']} "
                f"attempted n={len(att)} verdict={land_att['verdict']}; robustness {dict(vc)}")
    figures.manifold_figures(m, X, labels, banned, impl, over, L, kp, ms, tag, surv, att)
    if land.get("_nulls_raw") or land_att.get("_nulls_raw"):
        figures.null_figure(land, land_att, m[f"k{kp}"], ms, L, kp)
    import numpy as np  # noqa: F811
    np.savez_compressed(RESULTS.parent / "cache" / "states" / f"geo_{tag}.npz",
                        geo_k5=m["_emb"]["geo"][5], geo_k10=m["_emb"]["geo"][10], geo_k15=m["_emb"]["geo"][15],
                        labels=labels, L=L)


def _full_text(tok: Any, r: dict[str, Any], cid: str, cap: int | None = None) -> str:
    import prompts_tp

    user = r["prompt"] + (" /no_think" if r.get("no_think_suffix") else "")
    if CONFIGS[cid]["thinking"]:
        reasoning = r.get("reasoning") or ""
        if cap:
            ids = tok(reasoning, add_special_tokens=False)["input_ids"]
            if len(ids) > cap:
                reasoning = tok.decode(ids[:cap])
        return prompts_tp.render_chat(tok, user, True) + "<think>\n" + reasoning + "\n</think>\n\n" + \
            (r.get("content") or "")
    return prompts_tp.render_chat(tok, user, False) + (r.get("content") or "")


def stage_m2() -> None:
    """G4: per-program states at p*, p*-1 and g16 for every m* screen program (baseline + ban)."""
    import numpy as np
    import torch

    import figures
    import geometry
    import screen
    import states
    from common import CANON_ORDER, STATE_CHECKPOINTS

    ms, sel, banned = _mstar()
    geo = read_json(RESULTS / "geometry_M1.json")
    L = geo["L_star"]
    ck = STATE_CHECKPOINTS[ms]
    blocks = list(range(L - 2, L + 3))
    model, tok, info = states.load_truncated(ck["repo"], ck["precision"], max(blocks) + 1)
    rows = [r for arm in ("baseline", "ban") for r in read_jsonl(screen.labelled_path(ms, arm))]
    rows = [r for r in rows if r.get("code") and r.get("adj_label") in CANON_ORDER + ["other"]]
    cap = None
    if CONFIGS[ms]["thinking"] and CONFIGS[ms]["params_b"] > 9:
        import random as _r

        cap = 4096
        base_rows = [r for r in rows if r["arm"] == "baseline"]
        keep_base = set(r["uid"] for r in _r.Random(0).sample(base_rows, min(30, len(base_rows))))
        rows = [r for r in rows if r["arm"] == "ban" or r["uid"] in keep_base]
        deviation("D16-M2-cap", f"M2 for {ms} (thinking, {CONFIGS[ms]['params_b']}B at {ck['precision']}): reasoning capped "
                                f"at the first 4,096 tokens (plan fallback g-iii) and baseline programs limited to a "
                                f"seeded sample of 30 (plan TIME rule); every ban program is kept")
    items = [{"uid": r["uid"], "full_text": _full_text(tok, r, ms, cap), "code": r["code"], "label": r["adj_label"]}
             for r in rows]
    if not all(r.get("prompt") for r in rows):
        raise RuntimeError("rows without prompt text")
    t0 = time.time()
    arr, inf = states.m2_states(model, tok, items, blocks)
    dt = time.time() - t0
    ok = [i for i, x in enumerate(inf) if x["ok"]]
    okrows = [rows[i] for i in ok]
    labels = [r["adj_label"] for r in okrows]
    arms = [r["arm"] for r in okrows]
    surv = [r["arm"] == "ban" and screen.is_correct_survivor(r, banned) for r in okrows]
    states.save_npz(f"m2_{ms}", states=arr, blocks=np.array(blocks), uids=np.array([r["uid"] for r in okrows]),
                    labels=np.array(labels), arms=np.array(arms), surv=np.array(surv),
                    positions=np.array(["p_star", "p_prev", "g16"]))
    del model
    torch.cuda.empty_cache()
    # analysis at L* (block index 2), p* (position 0)
    from sklearn.decomposition import PCA
    from sklearn.manifold import Isomap

    Xp = arr[:, 0, 2].astype(np.float64)
    out: dict[str, Any] = {"config": ms, "L_star": L, "blocks": blocks, "n_programs": len(rows), "n_ok": len(ok),
                           "seconds": round(dt, 1), "load": info, "signatures": dict(collections.Counter(
                               x.get("signature") for x in inf if x["ok"])),
                           "n_forward_tokens_mean": float(np.mean([x["n_forward_tokens"] for x in inf if x["ok"]]))
                           if ok else None, "labels": dict(collections.Counter(labels)),
                           "failed": [x for x in inf if not x["ok"]][:20]}
    if len(ok) >= 12:
        pca = PCA(n_components=2, random_state=0).fit(Xp)
        P2 = pca.transform(Xp)
        k = min(10, len(ok) - 1)
        Yi = Isomap(n_neighbors=k, n_components=2).fit_transform(Xp)
        out["pca_evr"] = pca.explained_variance_ratio_.tolist()
        figures.m2_figure(P2, Yi, labels, arms, surv, banned, ms, L, "p*")
        gm, ginfo = geometry.geodesics(Xp, k)
        out["geodesic_graph"] = ginfo
        lab = np.array(labels)
        sd = []
        for i in [i for i, s in enumerate(surv) if s]:
            dists = {b: float(np.mean(gm[i, lab == b])) for b in banned if (lab == b).any()}
            if dists:
                nb = min(dists, key=dists.get)
                sd.append({"uid": okrows[i]["uid"], "label": labels[i], "nearest_banned_cloud": nb,
                           "geodesic_to_nearest_banned": dists[nb], "all": dists})
        out["survivor_distances"] = sd
        # decodability of adj_label at the three positions (5-fold stratified CV, descriptive)
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import balanced_accuracy_score
        from sklearn.model_selection import StratifiedKFold, cross_val_predict
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler

        cnt = collections.Counter(labels)
        keep = [i for i, l in enumerate(labels) if cnt[l] >= 5]
        if len({labels[i] for i in keep}) >= 2:
            dec = {}
            for pi, pn in enumerate(("p_star", "p_prev", "g16")):
                Xq = arr[keep, pi, 2].astype(np.float64)
                yq = np.array([labels[i] for i in keep])
                pr = cross_val_predict(make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=2000)), Xq,
                                       yq, cv=StratifiedKFold(5, shuffle=True, random_state=0))
                dec[pn] = float(balanced_accuracy_score(yq, pr))
            out["label_decodability_balanced_acc"] = dec
            out["decodability_note"] = ("p* is label-dependent (it is chosen from the label's lexicon), so decodability "
                                        "there is partly by construction (iteration-2 D-pre-leak); g16 is "
                                        "label-independent")
    write_json(RESULTS / "geometry_M2.json", out)
    logger.info(f"M2 {ms}: {len(ok)}/{len(rows)} programs, {dt:.0f}s; decodability "
                f"{out.get('label_decodability_balanced_acc')}")


def stage_quantcheck() -> None:
    """QC: Qwen3-8B forced S-mean at bf16 vs int8 vs nf4: per-block cosine; Spearman of 10x10 geodesic matrices at
    k = 10 and the agreement of EDGE/MIDDLE/OPPOSITE classes (banned set of m*)."""
    import numpy as np
    from scipy.stats import spearmanr

    import geometry
    from common import CANON_ORDER, STATES

    ms, sel, banned = _mstar()
    ref_tag = "C1_bf16"
    for prec in ("bf16", "int8", "nf4"):
        tag = f"C1_{prec}"
        if not (STATES / f"smean_{tag}.npz").exists():
            stage_states("C1", "Qwen/Qwen3-8B", prec, tag)
    zr = _load_smean(ref_tag)
    F = zr["kind"] == "forced"
    blocks = [int(b) for b in zr["blocks"]]
    labels = zr["algorithm"][F]
    groups = zr["group"][F].astype(int)
    rp = RESULTS / f"states_{ref_tag}.json"
    if rp.exists():
        n_layers = read_json(rp)["n_layers"]
    else:
        from transformers import AutoConfig

        n_layers = AutoConfig.from_pretrained("Qwen/Qwen3-8B").num_hidden_layers
        write_json(rp, {"config": "C1", "tag": ref_tag, "n_layers": n_layers, "extracted_blocks": blocks,
                        "note": "record rebuilt after a failed embed-identity check; states file written by the "
                                "first QC run (hook check passed: blocks [0, 14, 27], max abs diff 0)"})
    lc = geometry.layer_curve(zr["smean"][F].astype(np.float64), labels, groups, blocks,
                              [int(b) for b in zr["sel_blocks"]], n_layers)
    L = lc["L_star"]
    Xr = zr["smean"][F][:, blocks.index(L)].astype(np.float64)
    geo_r, _ = geometry.geodesics(Xr, 10)
    Mr = geometry.class_matrix(geo_r, labels, CANON_ORDER)
    nonb = [a for a in CANON_ORDER if a not in banned]
    gr, _ = geometry.g_values(geo_r, labels, banned, nonb)
    cr, _ = geometry.classify(gr)
    out: dict[str, Any] = {"L": L, "reference": "bf16", "banned": banned, "per_precision": {}}
    iu = np.triu_indices(10, 1)
    for prec in ("int8", "nf4"):
        zq = _load_smean(f"C1_{prec}")
        Sq, Sr = zq["smean"][F].astype(np.float64), zr["smean"][F].astype(np.float64)
        cos = {}
        for bi, b in enumerate(blocks):
            a, c = Sq[:, bi], Sr[:, bi]
            cos[str(b)] = float(np.mean((a * c).sum(1) / (np.linalg.norm(a, axis=1) * np.linalg.norm(c, axis=1))))
        Xq = Sq[:, blocks.index(L)]
        geo_q, _ = geometry.geodesics(Xq, 10)
        Mq = geometry.class_matrix(geo_q, labels, CANON_ORDER)
        rho = float(spearmanr(Mr[iu], Mq[iu]).statistic)
        gq, _ = geometry.g_values(geo_q, labels, banned, nonb)
        cq, _ = geometry.classify(gq)
        out["per_precision"][prec] = {"cosine_by_block": cos, "spearman_geodesic_k10": rho,
                                      "class_agreement": sum(cq[a] == cr[a] for a in nonb) / len(nonb),
                                      "classes": cq, "classes_bf16": cr,
                                      "precision_sensitive": rho < 0.8}
        logger.info(f"QC {prec}: Spearman {rho:.3f}, class agreement {out['per_precision'][prec]['class_agreement']}, "
                    f"cos@L {cos[str(L)]:.4f}")
    write_json(RESULTS / "quant_check.json", out)
    import figures

    figures.quant_figure(out)


def stage_confirm() -> None:
    """Stage 8 (only if Q is non-empty): commit #4 freezes the geometry; N=50 held-out templates on m*."""
    import hashlib

    import adjudicate
    import landing
    import prompts_tp
    import sample_or
    import sample_vllm
    import screen
    from common import CANON_ORDER, DATA, SRC, STATES, STATE_CHECKPOINTS, commit, write_jsonl

    ms, sel, banned = _mstar()
    if sel["mode"] != "SELECTED":
        logger.info("Q is empty: no confirmation (by the committed rule)")
        write_json(RESULTS / "confirmation.json", {"ran": False, "reason": "Q empty (no qualifying configuration)"})
        return
    geo = read_json(RESULTS / "geometry_M1.json")
    land = read_json(RESULTS / "landing.json")
    kp = geo["M1"]["k_primary"]
    tag = geo["tag"]
    p4 = PRED / "commit4.json"
    if not p4.exists():
        payload = {"m_star": ms, "L_star": geo["L_star"], "k": kp, "g": geo["M1"][f"k{kp}"]["g"],
                   "classes": geo["M1"][f"k{kp}"]["classes"], "banned": banned,
                   "smean_sha256": hashlib.sha256((STATES / f"smean_{tag}.npz").read_bytes()).hexdigest(),
                   "geodesics_sha256": hashlib.sha256((STATES / f"geo_{tag}.npz").read_bytes()).hexdigest(),
                   "landing_code_sha256": hashlib.sha256((SRC / "landing.py").read_bytes()).hexdigest(),
                   "screen_verdict": land["primary"]["verdict"], "prediction": "EDGE",
                   "rule": "CONFIRMED iff verdict equals the screen verdict with p_edge(U) < 0.05 in that direction "
                           "and a majority in the same class; no refit"}
        write_json(p4, payload)
        commit(p4, "commit4", "frozen geometry before held-out confirmation sampling")
    n = 50
    items = prompts_tp.confirm_ban_prompts(banned, n)
    out_raw = DATA / f"raw_{ms}_confirm.jsonl"
    cfg = CONFIGS[ms]
    if cfg["engine"] == "openrouter":
        sample_or.run([(ms, cfg, items, out_raw)], purpose="confirmation", concurrency=24)
    else:
        if not sample_vllm.server_ready():
            raise RuntimeError("local m* needs the vLLM server for confirmation")
        sample_vllm.generate(items, out_raw, {"config": ms, "model": cfg["model"]}, concurrency=8)
    screen.label_arm("confirm", [ms])
    rows = read_jsonl(screen.labelled_path(ms, "confirm"))
    st = adjudicate.apply_adjudication(rows, banned=banned, purpose=f"{ms}:confirm")
    write_jsonl(screen.labelled_path(ms, "confirm"), rows)
    nonb = [a for a in CANON_ORDER if a not in banned]
    surv = [r["adj_label"] for r in rows if screen.is_correct_survivor(r, banned) and r["adj_label"] in nonb]
    base = read_jsonl(screen.labelled_path(ms, "baseline"))
    impl = collections.Counter(r["adj_label"] for r in base if r["adj_label"] in CANON_ORDER)
    rates, rsrc = _forced_rates(ms)
    g = geo["M1"][f"k{kp}"]["g"]
    cls = geo["M1"][f"k{kp}"]["classes"]
    lc = landing.landing(g, cls, surv, {a: impl.get(a, 0) for a in nonb}, rates)
    sv = land["primary"]["verdict"]
    ok = False
    if lc.get("S") is not None and sv in ("EDGE", "OPPOSITE"):
        key = "p_edge" if sv == "EDGE" else "p_opp"
        ok = lc["verdict"] == sv and lc["nulls"]["U"][key] < 0.05 and lc["class_shares"].get(sv, 0) > 0.5
    m = screen.config_metrics(ms, "confirm")
    res = {"ran": True, "m_star": ms, "n": len(rows), "survivors": surv, "landing": landing.strip(lc),
           "screen_verdict": sv, "CONFIRMED": ok, "adjudication": st, "metrics": m, "forced_rates_source": rsrc,
           "engine": STATE_CHECKPOINTS[ms]}
    write_json(RESULTS / "confirmation.json", res)
    logger.info(f"CONFIRMATION {ms}: share_cs {m['share_cs']}, n_surv {len(surv)}, verdict {lc['verdict']} vs screen "
                f"{sv} -> CONFIRMED={ok}")


def stage_circle() -> None:
    """G7 (optional): ripser H1 on the 300 M1 points (PCA-20) and on the 10 centroids vs 100 covariance-matched
    Gaussian clouds. Descriptive answer to 'is it a circle'."""
    import numpy as np
    from ripser import ripser
    from sklearn.decomposition import PCA

    from common import CANON_ORDER

    geo = read_json(RESULTS / "geometry_M1.json")
    z = _load_smean(geo["tag"])
    F = z["kind"] == "forced"
    blocks = [int(b) for b in z["blocks"]]
    X = z["smean"][F][:, blocks.index(geo["L_star"])].astype(np.float64)
    labels = z["algorithm"][F]
    Z = PCA(n_components=20, random_state=0).fit_transform(X)

    def maxp(A: np.ndarray) -> float:
        d = ripser(A, maxdim=1)["dgms"][1]
        return float((d[:, 1] - d[:, 0]).max()) if len(d) else 0.0

    obs = maxp(Z)
    rng = np.random.default_rng(0)
    cov, mu = np.cov(Z.T), Z.mean(0)
    null = [maxp(rng.multivariate_normal(mu, cov, size=len(Z))) for _ in range(100)]
    C = np.stack([X[labels == a].mean(0) for a in CANON_ORDER])
    Cz = PCA(n_components=9, random_state=0).fit_transform(C)
    obs_c = maxp(Cz)
    covc, muc = np.cov(Cz.T), Cz.mean(0)
    null_c = [maxp(rng.multivariate_normal(muc, covc, size=10)) for _ in range(100)]
    out = {"points": {"max_H1_persistence": obs, "null_q95": float(np.quantile(null, 0.95)),
                      "p": float(np.mean(np.array(null) >= obs))},
           "centroids": {"max_H1_persistence": obs_c, "null_q95": float(np.quantile(null_c, 0.95)),
                         "p": float(np.mean(np.array(null_c) >= obs_c))},
           "L_star": geo["L_star"], "config": geo["config"]}
    out["is_circle"] = bool(out["points"]["p"] < 0.05 and out["centroids"]["p"] < 0.05)
    write_json(RESULTS / "circle_check.json", out)
    logger.info(f"circle check: {out}")


def stage_novelty() -> None:
    import novelty
    import screen

    rows = {cid: [r for arm in ("baseline", "ban", "confirm") for r in read_jsonl(screen.labelled_path(cid, arm))]
            for cid in CONFIGS}
    out = novelty.audit(rows)
    logger.info(f"novelty: candidates {out['n_candidates']}, novel {out['n_novel']}: {out['claim']}")


def stage_figures() -> None:
    import collections as _c

    import numpy as np
    from sklearn.decomposition import PCA
    from sklearn.manifold import Isomap

    import figures
    import screen
    from common import CANON_ORDER

    tab = read_json(RESULTS / "screen.json")
    sel = read_json(RESULTS / "selection.json")
    figures.forest(tab, sel)
    conf = read_json(RESULTS / "confirmation.json") if (RESULTS / "confirmation.json").exists() else {}
    if conf.get("ran"):
        geo = read_json(RESULTS / "geometry_M1.json")
        z = _load_smean(geo["tag"])
        blocks = [int(b) for b in z["blocks"]]
        F = z["kind"] == "forced"
        X = z["smean"][F][:, blocks.index(geo["L_star"])].astype(np.float64)
        labels = z["algorithm"][F]
        Qc = z["smean"][z["kind"] == "confirm"][:, blocks.index(geo["L_star"])].astype(np.float64)
        kp = geo["M1"]["k_primary"]
        pca = PCA(n_components=10, random_state=0).fit(X)          # same fit as M1 (deterministic)
        iso = Isomap(n_neighbors=kp, n_components=2)
        Y = iso.fit_transform(X)
        base = read_jsonl(screen.labelled_path(geo["config"], "baseline"))
        impl = _c.Counter(r["adj_label"] for r in base if r["adj_label"] in CANON_ORDER)
        figures.confirmation_figure(geo, X, labels, conf, dict(impl), Y, iso, pca, Qc, geo["config"])


def stage_rederive() -> None:
    import subprocess
    import sys as _s

    from common import ROOT, SRC

    p = subprocess.run([_s.executable, str(SRC / "rederive.py")], capture_output=True, text=True, cwd=str(ROOT),
                       timeout=1800)
    logger.info(p.stdout[-2000:])
    if p.returncode != 0:
        logger.error(p.stderr[-3000:])
        raise RuntimeError("rederive failed")


def stage_outputs() -> None:
    import outputs

    outputs.build()


def stage_checks() -> None:
    """Confirmation signals before scaling + T9 continuity + T10 note (results/checks.json)."""
    from scipy.stats import fisher_exact

    import screen
    from common import SRC_PATHS

    c1 = read_jsonl(screen.labelled_path("C1", "baseline"))
    c2 = read_jsonl(screen.labelled_path("C2", "baseline"))
    carried = read_json(RESULTS / "carried_rows.json")
    c1_bfs = sum(r["adj_label"] == "bfs" for r in c1) / len(c1)
    cnt2 = collections.Counter(r["adj_label"] for r in c2)
    # art_-QPYRaFERCBX (Llama T1 baseline): BFS 77 / DFS 20, pass 0.20 (plan builds_on 4)
    odds, p = fisher_exact([[cnt2["bfs"], cnt2["dfs"]], [77, 20]])
    exp34_states = SRC_PATHS["exp34"] / "cache" / "states" / "top5_T1_states.npz"
    out = {"C1_baseline_bfs_share": c1_bfs, "C1_baseline_ge_95pct_bfs": c1_bfs >= 0.95,
           "C9_carried_baseline": "BFS 100/100 (iteration 2 baseline)",
           "C2_baseline_counts": dict(cnt2), "C2_baseline_pass_rate": sum(bool(r["passed"]) for r in c2) / len(c2),
           "C2_vs_art_-QPYRaFERCBX_fisher": {"table": [[cnt2["bfs"], cnt2["dfs"]], [77, 20]], "odds_ratio": odds,
                                            "p": p, "note": "non-blocking; cross-engine differences = kernel "
                                                            "sensitivity"},
           "openrouter_first_rows_valid": {cid: sum(r.get("code") is not None for r in
                                                    read_jsonl(screen.labelled_path(cid, "baseline"))[:10])
                                           for cid in CONFIGS},
           "T9_continuity": ("not reproducible: states absent (ITER7 exp34 cache/states/top5_T1_states.npz is not on "
                             "the run volume)") if not exp34_states.exists() else "states present",
           "T10_note": "the full quantisation check (300 forced prompts at bf16/int8/nf4) replaced the 20-prompt dry run",
           "carried": carried}
    write_json(RESULTS / "checks.json", out)
    logger.info(f"checks: {out['C1_baseline_bfs_share']}, C2 {out['C2_baseline_counts']} Fisher p {p:.3f}")


def stage_screen_table() -> None:
    """Regenerate results/screen.json (and the confirmation metrics) with the sensitivity fields; selection and
    commit #3 are untouched."""
    import screen

    tab = screen.screen_table()
    p = RESULTS / "confirmation.json"
    if p.exists():
        c = read_json(p)
        if c.get("ran"):
            c["metrics"] = screen.config_metrics(c["m_star"], "confirm")
            write_json(p, c)
    for cid, m in sorted(tab.items()):
        if "sensitivity_cs" in m:
            logger.info(f"{cid}: cs {m['n_correct_survivors']} sensitivity {m['sensitivity_cs']}")


def stage_refig() -> None:
    """Re-render F2-F4 and F6 from the cached states (deterministic recomputation of M1 + landing) and add the
    full-dimensional placement of the baseline / screen-ban / held-out-ban prompt states (nearest centroids)."""
    import numpy as np

    import figures
    import geometry
    import landing
    import screen
    from common import CANON_ORDER

    geo = read_json(RESULTS / "geometry_M1.json")
    ms, banned, L = geo["config"], geo["banned"], geo["L_star"]
    z = _load_smean(geo["tag"])
    blocks = [int(b) for b in z["blocks"]]
    kind = z["kind"]
    F = kind == "forced"
    X = z["smean"][F][:, blocks.index(L)].astype(np.float64)
    labels = z["algorithm"][F]
    m = geometry.manifold(X, labels, banned)
    kp = m["k_primary"]
    pca = m["_emb"]["pca"]
    iso_k, _ = m["_emb"]["isomap"][kp]
    over = {}
    cent = {a: X[labels == a].mean(0) for a in CANON_ORDER}
    place = {}
    for kd in ("baseline", "ban", "confirm"):
        Q = z["smean"][kind == kd][:, blocks.index(L)].astype(np.float64)
        over[kd] = {"pca": pca.transform(Q)[:, :2].tolist(), "isomap": iso_k.transform(Q).tolist()}
        d = {a: float(np.mean(np.linalg.norm(Q - c, axis=1))) for a, c in cent.items()}
        order = sorted(d, key=d.get)
        place[kd] = {"mean_distance_to_centroid": d, "nearest_order": order,
                     "rank_of_dijkstra_unit": order.index("dijkstra_unit") + 1,
                     "templates": [str(t) for t in z["template"][kind == kd]]}
    base = read_jsonl(screen.labelled_path(ms, "baseline"))
    ban = read_jsonl(screen.labelled_path(ms, "ban"))
    import collections as _c
    impl = dict(_c.Counter(r["adj_label"] for r in base if r["adj_label"] in CANON_ORDER))
    nonb = [a for a in CANON_ORDER if a not in banned]
    surv = [r["adj_label"] for r in ban if screen.is_correct_survivor(r, banned) and r["adj_label"] in nonb]
    att = [r["adj_label"] for r in ban if r["adj_label"] in nonb]
    figures.manifold_figures(m, X, labels, banned, impl, over, L, kp, ms, geo["tag"], surv, att)
    rates, _ = _forced_rates(ms)
    bnb = {a: impl.get(a, 0) for a in nonb}
    la = landing.landing(m[f"k{kp}"]["g"], m[f"k{kp}"]["classes"], surv, bnb, rates)
    lt = landing.landing(m[f"k{kp}"]["g"], m[f"k{kp}"]["classes"], att, bnb, rates)
    figures.null_figure(la, lt, m[f"k{kp}"], ms, L, kp)
    geo["prompt_state_placement"] = place
    geo["refig_check"] = {"classes_equal": m[f"k{kp}"]["classes"] == geo["M1"][f"k{kp}"]["classes"],
                          "g_max_abs_diff": max(abs(m[f"k{kp}"]["g"][a] - geo["M1"][f"k{kp}"]["g"][a]) for a in nonb)}
    write_json(RESULTS / "geometry_M1.json", geo)
    logger.info(f"placement: { {k: v['nearest_order'][:4] for k, v in place.items()} }; refig {geo['refig_check']}")


def stage_t7() -> None:
    """T7: block outputs with the embedding table on the CPU (rows indexed there, moved to the GPU) vs a fully
    on-GPU model are identical (Qwen3-8B bf16, 2 prompts, blocks 0-2)."""
    import numpy as np
    import torch
    from transformers import AutoModelForCausalLM

    import prompts_tp
    import states

    model, tok, info = states.load_truncated("Qwen/Qwen3-8B", "bf16", 3)
    texts = [prompts_tp.render_chat(tok, prompts_tp.forced_prompt(a, 0, 0)["prompt"], True) for a in ("bfs", "jps")]
    a = []
    for t in texts:
        enc = tok(t, return_tensors="pt", add_special_tokens=False)
        cap = states.forward_blocks(model, enc["input_ids"], enc["attention_mask"], [0, 1, 2])
        a.append({b: v.numpy() for b, v in cap.items()})
    del model
    torch.cuda.empty_cache()
    from transformers import AutoConfig

    cfg = AutoConfig.from_pretrained("Qwen/Qwen3-8B")
    cfg.num_hidden_layers = 3
    cfg.layer_types = list(cfg.layer_types)[:3]
    g = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-8B", config=cfg, dtype=torch.bfloat16, device_map={"": 0},
                                             attn_implementation="sdpa")
    diffs = []
    for t, ref in zip(texts, a):
        enc = tok(t, return_tensors="pt", add_special_tokens=False).to("cuda")
        with torch.no_grad():
            out = g.model(input_ids=enc["input_ids"], attention_mask=enc["attention_mask"], output_hidden_states=True,
                          use_cache=False)
        for b in (0, 1):
            diffs.append(float(np.abs(out.hidden_states[b + 1].float().cpu().numpy() - ref[b]).max()))
    res = {"blocks": [0, 1], "max_abs_diff": max(diffs), "identical": max(diffs) == 0.0, "n_prompts": 2}
    write_json(RESULTS / "t7_embed_cpu_vs_gpu.json", res)
    logger.info(f"T7 embed CPU vs all-GPU: {res}")
