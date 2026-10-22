#!/usr/bin/env python3
"""Iteration 7: circuit and dose dial at Gemma's BFS-vs-DFS fork (google/gemma-3-4b-it, bf16).

Entry point; one function per stage, run as `.venv/bin/python method.py --stage <name>`:
  s0       CPU tests (labeller on references, checker mutants, token ids, c*, CRN, DAS toy), instrument ids,
           GPU batch-shape time test, COMMIT #0
  engine   GPU unit tests U1-U4, engine check (twin N=50 vs iteration 6), U6 (a) multi-prompt vs (b) single-prompt
           re-run, G3-cal (P(BFS | fork token) with the main engine)
  label    CPU label worker over data/raw_*.jsonl (frozen exp8 T1 labeller; follow mode with --follow)
  g3a      G3 predictions from teacher-forced logits (COMMIT #1)          -> src/g3.py
  g3b      G3 temperature sweep (T x sampler, N=50 per cell)                -> src/g3.py
  yv       y_v for the 120 twin variants + fork states (layers 17-29) for bases and 40 forced sources -> src/g2.py
  g1p      G1 path patching on heads/MLPs (AtP screen, exact patching, edges)  -> src/g1.py
  g1v      G1 validation in the real model (teacher-forced, random matched nulls, COMMIT #2, generation) -> src/g1.py
  g2       G2 DAS (layer scan, nested ranks, seeds) + RAND/SHUF/DiM/natural-variance controls -> src/g2.py
  g2r      G2 RINIT control on a randomly initialised Gemma                 -> src/g2.py
  g2d      G2 dose sweep in generation (COMMIT #3 first) + G2-L             -> src/g2.py
  novelty  novelty audit of every correct 'other' program + style re-gate (OpenRouter)
  analysis / figures / outputs
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from loguru import logger  # noqa: E402

from cfg import (B_IDS, CT_COMMIT, D_IDS, DATA_DIR, DISPLAY_PAIRS, FORCED_TEMPLATES, I6, I6_DATA, I6_NATURAL,  # noqa: E402
                 I6_RESULTS, IT_ID, IT_REV, MAX_NEW, PRED_DIR, RESULTS_DIR, SCOPE_REPO, TC_REPO, TC_REV, TC_SUB,
                 TEMPLATE_IDS, add_deviation, append_jsonl, container_ram_gb, detect_cpus, read_json, read_jsonl,
                 set_ram_limit, setup_logging, sha256_file, slot_key7, slot_key_i6, utc_now, write_json)

GPU_STAGES = ("s0", "engine", "g3a", "g3b", "yv", "g1p", "g1v", "g2", "g2r", "g2d", "g2smoke", "g1gen", "g2pairs")

DECISION_RULES = {
    "ENGINE_CHECK": "Pass if the twin BFS share (N=50, natural sampling T=1 top-p 1) lies inside iteration 6's Wilson "
                    "95% CI [0.245, 0.372] for 61/200; per-slot label agreement with iteration 6's rows is reported "
                    "whatever it is.",
    "U6": "200 continuations from the empty response prefix: (a) fork-resampling path (multi-prompt batches, partial "
          "labeller; also labelled with the full labeller) and (b) the main single-prompt fixed-shape engine; each is "
          "compared with the natural share (two-proportion exact test). Diagnosis: labeller (a-partial vs a-full), "
          "batching ((a) vs (b)), or neither.",
    "G3_SOURCE_RULE": "PRIMARY P(BFS | t) for t in B and D is iteration 6's token table UNLESS the U6 diagnosis shows "
                      "that path (a) differs from (b) at p < 0.05; then the primary is the G3-cal estimate. The other "
                      "source is reported as the sensitivity.",
    "NODE_CLAIM": "Holm p < 0.05 (exact one-sided sign-flip permutation over the 20 variant prompts, Holm over the "
                  "top 10) AND the median d_i is in the expected direction AND joint top-5 beats >= 95% of its random "
                  "sets on the median over prompts.",
    "G2_DAS_REAL": "At some k <= 8 (seed median), DAS recovery - RAND recovery >= 0.4 (paired Wilcoxon over held-out "
                   "pairs, p < 0.01) AND SHUF held-out recovery <= 0.1 AND RINIT held-out effect < 0.5 x the trained "
                   "model's effect in nats.",
    "SMALLEST_SUFFICIENT_RANK": "the smallest k with recovery >= 0.8.",
    "ONE_DIMENSIONAL_WORDING": "only if k=1 recovery >= 0.8 AND Spearman(R_1^T h_v, y_v) >= 0.5 (p < 0.01) AND "
                               "G2-KNOB holds; otherwise 'a rank-k subspace carries the forced-prompt transfer'.",
    "DORMANT_FLAG": "share_k at or below the 95th percentile of random AND |Spearman| < 0.2.",
    "K_STAR": "the smallest k whose train-CV recovery >= 0.9 x the maximum over k.",
    "G2_KNOB": "some BFS-direction dose has correct-BFS > the twin's (exact one-sided McNemar on CRN pairs, Holm over "
               "the 6 doses of that method, p < 0.05) AND pass >= 0.8 x the twin's pass; evaluated for DAS and DiM "
               "separately.",
    "G3_CONC": "pooled H(label | fork class) <= 0.3 bits.",
    "G3_LAW": "|pred - obs| <= 0.10 in every top-p-1 cell (top-k cells reported separately).",
    "G3_DISCONFIRMED": "H > 0.5 bits or any top-p-1 cell misses by more than 0.2.",
    "G3_MAE": "MAE <= 0.10 per cell.",
}
DROP_ORDER = ["G1 generation beyond 5 nodes (top-10 and DFS arms)", "the random-init control at the second layer",
              "G3 top-k at T0.7", "G2-N", "G2-L", "G3 top-k T1.3",
              "the DFS-direction DiM cells (keep DAS toward DFS at 0.2 / 0.5 / 1)"]
NEVER_DROP = ["G1 (graph or G1-P) validated in the real model on the teacher-forced margin",
              "G2 with RAND, SHUF, RINIT at L*, held-out templates, the natural-variance check and the BFS-direction "
              "dose sweep for DAS and DiM", "G3 at top-p 1 with its committed predictions", "the novelty audit",
              "the engine check and U6"]


# ================================================================================================ S0
def _mutants(ref: str) -> dict[str, str]:
    """Five hand-made wrong programs derived from the BFS reference (each must FAIL the hidden tests)."""
    m = {}
    m["wrong_path_gap"] = ref.replace("return path[::-1]", "p = path[::-1]\n    return p[:1] + p[2:] if len(p) > 2 else p")
    m["through_obstacle"] = ref.replace("and grid[nr][nc] == '.' ", "").replace(
        "if grid[sr][sc] == '#' or grid[gr][gc] == '#':\n        return []", "pass")
    m["diagonal_moves"] = ref.replace("((-1, 0), (1, 0), (0, -1), (0, 1))",
                                      "((-1, 0), (1, 0), (0, -1), (0, 1), (1, 1), (-1, -1), (1, -1), (-1, 1))")
    m["wrong_endpoint"] = ref.replace("return path[::-1]", "return path[::-1][:-1] if len(path) > 1 else path")
    m["missing_unreachable"] = ref.replace("if goal not in parent:\n        return []",
                                           "if goal not in parent:\n        return [start, goal]")
    for k, v in m.items():
        assert v != ref, k
    return m


def stage_s0(args: argparse.Namespace) -> None:
    import numpy as np

    import engine as EG
    import fork7 as FK
    import prompts as PG
    from cfg import SUITE, bench_paths

    t0 = time.time()
    res: dict[str, Any] = {}
    # ---------------- inputs: the vendored iteration-6 files match their manifest
    man = (I6 / "MANIFEST.sha256").read_text().splitlines()
    bad = []
    for ln in man:
        h, p = ln.split(None, 1)
        if sha256_file(I6 / p.strip().lstrip("./")) != h:
            bad.append(p)
    res["inputs_manifest"] = {"n_files": len(man), "n_mismatch": len(bad), "branch": "A (iteration-6 files readable)"}
    # ---------------- labeller on every reference + checker mutants
    bench_paths()
    import label_worker as LW

    refs = sorted((SUITE / "tasks" / "t1_grid" / "references").glob("*.py"))
    mode_of = {"astar": "astar_gbfs", "gbfs": "astar_gbfs", "bfs": "bfs", "bibfs": "bibfs", "dfs": "dfs",
               "dijkstra": "dijkstra", "iddfs": "iddfs"}
    ref_rows = []
    for f in refs:
        want = mode_of[f.stem.split("_")[0]]
        mech = LW._path_mech("t1", f.read_text())
        ref_rows.append({"file": f.name, "want": want, "runtime": mech["runtime_label"], "ast": mech["ast_label"],
                         "passed": mech["passed"],
                         "ok": mech["runtime_label"] == want and mech["ast_label"] == want and mech["passed"]})
    res["labeller_references"] = {"n": len(ref_rows), "n_ok": sum(r["ok"] for r in ref_rows),
                                  "modes_covered": sorted({r["want"] for r in ref_rows}), "rows": ref_rows}
    from tasks.harness import run_tests

    ref_bfs = (SUITE / "tasks" / "t1_grid" / "references" / "bfs_deque_parent.py").read_text()
    mut = {}
    for k, code in _mutants(ref_bfs).items():
        t = run_tests("t1", code)
        mut[k] = {"passed": bool(t.get("passed")), "n_passed": t.get("n_passed")}
    res["checker_mutants"] = {"n": len(mut), "n_rejected": sum(not v["passed"] for v in mut.values()), "rows": mut}
    # ---------------- token ids, c*, prompt alignment
    tok = PG.tokenizer()
    dec_B = [tok.decode([t]) for t in B_IDS]
    dec_D = [tok.decode([t]) for t in D_IDS]
    cs = FK.cstar()
    res["token_ids"] = {"B": dict(zip(map(str, B_IDS), dec_B)), "D": dict(zip(map(str, D_IDS), dec_D)),
                        "B_ok": [d.strip() if d.strip() else d for d in dec_B] == ["\n", "if", "queue", "q"],
                        "D_ok": dec_D[0].strip() == "visited",
                        "cstar_text_ok": tok.decode(cs) == FK.fork_table()["cstar_text"], "cstar_len": len(cs)}
    pair_tok = {f"{a} / {b}": [len(tok(" " + a, add_special_tokens=False)["input_ids"]),
                               len(tok(" " + b, add_special_tokens=False)["input_ids"])] for a, b in DISPLAY_PAIRS}
    lens = {}
    for f in FORCED_TEMPLATES:
        for pi in range(len(DISPLAY_PAIRS)):
            pb, pd = FK.forced("bfs", f, pi), FK.forced("dfs", f, pi)
            lens[f"{f}|{pi}"] = [pb["P"], pd["P"]]
            assert pb["P"] == pd["P"], f"forced pair {f}/{pi} lengths differ"
    V = FK.variants()
    by_w: dict[str, set[int]] = {}
    for v in V:
        by_w.setdefault(v["template"], set()).add(v["P"])
    assert all(len(s) == 1 for s in by_w.values()), "variants of one template differ in length"
    res["prompt_alignment"] = {"display_pair_token_counts": pair_tok, "forced_pair_lengths": lens,
                               "variant_lengths_by_template": {w: sorted(s) for w, s in by_w.items()},
                               "n_variants": len(V), "twin_lengths": {w: FK.twin(w)["P"] for w in TEMPLATE_IDS}}
    # ---------------- CRN streams bit-identical across two calls
    a = EG.u_stream("iter7GU6", "T1", "W1", 0, n=2048)
    b = EG.u_stream("iter7GU6", "T1", "W1", 0, n=2048)
    res["crn_identical"] = bool(np.array_equal(a, b))
    # ---------------- DAS toy (planted rank-2 subspace)
    import g2

    res["das_toy"] = g2.toy_test()
    # ---------------- instruments
    try:
        from huggingface_hub import HfApi, hf_hub_download

        api = HfApi()
        files = api.list_repo_files(TC_REPO, revision=TC_REV)
        cfgs = {}
        for f in files:
            if f.startswith("transcoder_all/") and f.endswith("/config.yaml"):
                cfgs[f] = Path(hf_hub_download(TC_REPO, f, revision=TC_REV)).read_text()
        scope_sha = api.model_info(SCOPE_REPO).sha
        tc_sha = api.model_info(TC_REPO, revision=TC_REV).sha
        res["instruments"] = {"model": IT_ID, "model_revision": IT_REV, "transcoder_repo": TC_REPO,
                              "transcoder_revision": tc_sha, "transcoder_subfolder": TC_SUB,
                              "transcoder_configs": cfgs, "gemma_scope_2_sha": scope_sha,
                              "circuit_tracer_commit": CT_COMMIT}
    except Exception as e:  # noqa: BLE001 - instrument listing is logged, not fatal
        logger.error(f"instrument listing failed: {e}")
        res["instruments"] = {"error": str(e)}
    # ---------------- GPU batch-shape time test (no labels, no decisive sample)
    import torch

    from gen7 import Runner

    run = Runner(B=20)
    p = FK.twin("W1")
    tt = {}
    for B in (20, 25):
        pre = run.prefill(p["ids"], B)
        U = np.stack([EG.u_stream("iter7Gtime", B, r, n=96) for r in range(B)])
        torch.cuda.synchronize()
        t1 = time.time()
        EG.decode(run.model, run.tok, pre, U, np.ones(B), 96, fence_stop=False)
        torch.cuda.synchronize()
        dt = time.time() - t1
        tt[B] = {"seconds_96_steps": dt, "rows_per_second": B * 96 / dt,
                 "peak_vram_gb": torch.cuda.max_memory_allocated() / 1e9}
        del pre
        torch.cuda.empty_cache()
    kv_gb = {B: B * (p["P"] + 32 + MAX_NEW) * 34 * 2 * 4 * 256 * 2 / 1e9 for B in (20, 25)}
    B_choice = 25 if (tt[25]["rows_per_second"] >= tt[20]["rows_per_second"] and kv_gb[25] < 6.0) else 20
    res["batch_time_test"] = {"by_B": tt, "kv_gb_at_max_len": kv_gb, "chosen_B": B_choice,
                              "rule": "larger rows/s, KV at max length < 6 GB (16 GB GPU)"}
    run.free()
    write_json(RESULTS_DIR / "s0_tests.json", res)
    # ---------------- COMMIT #0
    import commit as CM

    hw = {"gpu": torch.cuda.get_device_name(0), "vram_gb": torch.cuda.get_device_properties(0).total_memory / 1e9,
          "cpus": detect_cpus(), "ram_gb_container": container_ram_gb(), "torch": torch.__version__}
    import transformers

    hw["transformers"] = transformers.__version__
    design = {"B_CRN": B_choice, "MAX_NEW": MAX_NEW, "fork_index": 32, "B_ids": list(B_IDS), "D_ids": list(D_IDS),
              "template_split": {"train": ["W1", "W2", "W3", "F1", "F2", "F3"], "held_out": ["W4", "W5", "F4", "F5"]},
              "display_pairs": [list(x) for x in DISPLAY_PAIRS],
              "slot_keys": {"engine_check": "iteration 6 slot_key (iter5E, T1, W, k) for k in 0-9",
                            "U6": "(iter7GU6, T1, W, k), k in 0-39", "G3cal": "(iter7GG3cal|<tok>, T1, W, k)",
                            "G3": "(iter7GG3, T1, W, k), k in 0-9", "G1": "(iter7GG1, T1, W, k), k in 0-5",
                            "G2": "(iter7GG2, T1, W, k), k in 0-9"},
              "sampling": "inverse-CDF CRN, fp32 logits, float64 CDF in token-id order; top-k = mask below the "
                          "row's k-th largest logit", "das": {"layers_scan": [17, 19, 21, 22, 23, 25, 27, 29],
                                                             "ranks": [1, 2, 4, 8], "seeds": [0, 1, 2], "steps": 400,
                                                             "lr": 2e-3, "batch": 64, "loss": "sum_k KL(q_s || q'_k) over {B, D, O}"},
              "doses": [0.1, 0.2, 0.35, 0.5, 0.75, 1.0], "temperatures": [0.3, 0.7, 1.0, 1.3],
              "samplers": ["topp1", "topk10"], "N": {"engine": 50, "U6": 200, "G3_cell": 50, "G1_arm": 30,
                                                   "G2_cell": 50}}
    c0 = CM.commit("commit0", {"design": design, "decision_rules": DECISION_RULES, "drop_order": DROP_ORDER,
                               "never_drop": NEVER_DROP, "hardware": hw,
                               "instruments": {k: v for k, v in res["instruments"].items() if k != "transcoder_configs"},
                               "s0_tests_sha256": sha256_file(RESULTS_DIR / "s0_tests.json")})
    logger.info(f"S0 done in {time.time() - t0:.0f}s: refs {res['labeller_references']['n_ok']}/"
                f"{res['labeller_references']['n']}, mutants rejected {res['checker_mutants']['n_rejected']}/5, "
                f"B={B_choice}, commit0 {c0['sha256'][:12]}")


# ================================================================================================ engine stage
def stage_engine(args: argparse.Namespace) -> None:
    """U1-U4, engine check (twin N=50), U6 (a)+(b), G3-cal."""
    import numpy as np
    import torch

    import engine as EG
    import fork7 as FK
    from gen7 import Edit, Runner

    run = Runner()
    B = run.B
    cs = FK.cstar()
    tests: dict[str, Any] = {}
    raw_u = DATA_DIR / "tests_u.jsonl"
    # ---------------- U1: CRN determinism
    p = FK.twin("W1")
    rows = [{"row_id": f"u1|{i}|{k}", "ukey": slot_key7("U1", "W1", k), "meta": {"arm": "u1"}}
            for i in range(1) for k in range(2)]
    a = run.run_cell(p["ids"], [], rows, raw_u, "U1a", max_new=96)
    b = run.run_cell(p["ids"], [], [dict(r, row_id=r["row_id"] + "b") for r in rows], raw_u, "U1b", max_new=96)
    tests["U1_crn_determinism"] = {"pass": all(x["token_ids"] == y["token_ids"] for x, y in zip(a, b)), "n": len(a)}
    # ---------------- U2: identity hooks are bit-identical
    ids = p["ids"] + cs
    pf = len(ids) - 1
    with torch.no_grad():
        base = run.logits_rows(ids, 1)
        rows1 = torch.tensor([0], device="cuda")
        zero = Edit("resid", 22, [pf], lambda x, r: x + 0.0, name="zero")
        st = run.states(ids, [22], positions=[pf])
        hsrc = st["h"][22][0].cuda()
        full = Edit("resid", 22, [pf], lambda x, r: hsrc[None, None].expand_as(x).clone(), name="full_src_eq_base")
        R = torch.linalg.qr(torch.randn(2560, 4, generator=torch.Generator().manual_seed(0)).cuda())[0]
        das0 = Edit("resid", 22, [pf], lambda x, r: x + 0.0 * ((hsrc[None, None] - x) @ R @ R.T), name="das_lambda0")
        mlp_same = Edit("mlp", 20, [pf], lambda x, r: x.clone(), name="mlp_target_eq_clean")
        z_same = Edit("z", 20, [pf], lambda x, r: x.clone(), head=3, name="head_target_eq_clean")
        out = {}
        for e in (zero, full, das0, mlp_same, z_same):
            lg = run.logits_rows(ids, 1, [(e, rows1)])
            out[e.name] = bool(torch.equal(lg, base))
    tests["U2_identity_hooks"] = out
    # ---------------- U3: single-position KV interchange equals full recompute (|dm| < 1e-3)
    import g2

    tests["U3_single_position_kv"] = g2.u3_test(run, [FK.twin(w) for w in TEMPLATE_IDS])
    # ---------------- U4: top-k sampler with k = vocab equals the plain sampler bit for bit
    pre1 = run.prefill(p["ids"], 2)
    pre2 = run.prefill(p["ids"], 2)
    U = np.stack([EG.u_stream("iter7GU4", "T1", "W1", k, n=64) for k in range(2)])
    g_plain = EG.decode(run.model, run.tok, pre1, U, np.ones(2), 64, fence_stop=False)
    g_topk = EG.decode(run.model, run.tok, pre2, U, np.ones(2), 64, fence_stop=False,
                       topk=np.array([run.model.config.vocab_size] * 2))
    tests["U4_topk_vocab_equals_plain"] = {"pass": all(x["token_ids"] == y["token_ids"]
                                                       for x, y in zip(g_plain, g_topk))}
    del pre1, pre2
    torch.cuda.empty_cache()
    write_json(RESULTS_DIR / "tests_gpu_s1.json", tests)
    logger.info(f"GPU unit tests: {json.dumps(tests)}")
    # ---------------- ENGINE CHECK: twin W1-W5 x slots 0-9 with iteration 6's keys, natural sampling from index 0
    raw = DATA_DIR / "raw_engine.jsonl"
    done = {r["row_id"] for r in read_jsonl(raw)}
    for w in TEMPLATE_IDS:
        p = FK.twin(w)
        rows = [{"row_id": f"engine|{w}|{k}", "ukey": slot_key_i6("T1", w, k),
                 "meta": {"part": "engine", "arm": "twin_natural", "template": w, "slot": k}} for k in range(10)]
        rows = [r for r in rows if r["row_id"] not in done]
        if rows:
            run.run_cell(p["ids"], [], rows, raw, f"ENG:{w}")
    # ---------------- U6 (b): main single-prompt fixed-shape engine, 200 continuations from the empty prefix
    raw6 = DATA_DIR / "raw_u6.jsonl"
    done = {r["row_id"] for r in read_jsonl(raw6)}
    for w in TEMPLATE_IDS:
        p = FK.twin(w)
        rows = [{"row_id": f"u6b|{w}|{k}", "ukey": slot_key7("U6", w, k),
                 "meta": {"part": "U6", "arm": "u6b_single", "template": w, "slot": k}} for k in range(40)]
        rows = [r for r in rows if r["row_id"] not in done]
        if rows:
            run.run_cell(p["ids"], [], rows, raw6, f"U6b:{w}")
    # ---------------- U6 (a): fork-resampling path (multi-prompt right-aligned batches, templates interleaved)
    items = []
    for k in range(40):
        for w in TEMPLATE_IDS:
            p = FK.twin(w)
            rid = f"u6a|{w}|{k}"
            if rid in done:
                continue
            items.append({"row_id": rid, "ids": p["ids"], "n_prefix": 0, "prefix_ids": [],
                          "ukey": slot_key7("U6", w, k),
                          "meta": {"part": "U6", "arm": "u6a_multi", "template": w, "slot": k}})
    if items:
        run.run_multi(items, MAX_NEW, raw6, "U6a")
    # ---------------- G3-cal: prompt + c* + t, t in {visited, newline, if, queue}, main engine, to completion
    rawc = DATA_DIR / "raw_g3cal.jsonl"
    done = {r["row_id"] for r in read_jsonl(rawc)}
    n_cal = int(args.n_cal)
    for t in (53227, 107, 584, 15204):
        for w in TEMPLATE_IDS:
            p = FK.twin(w)
            rows = [{"row_id": f"g3cal|{t}|{w}|{k}", "ukey": slot_key7(f"G3cal|{t}", w, k),
                     "meta": {"part": "G3cal", "arm": f"cal_{t}", "template": w, "slot": k, "forced_fork_token": t}}
                    for k in range(n_cal)]
            rows = [r for r in rows if r["row_id"] not in done]
            if rows:
                run.run_cell(p["ids"] + cs + [t], cs + [t], rows, rawc, f"CAL:{t}:{w}")
    run.free()
    _ = (np, add_deviation)


# ================================================================================================ labelling
def stage_label(args: argparse.Namespace) -> None:
    import label_worker as LW

    LW.run_worker(follow=bool(args.follow), stop_file=DATA_DIR / "STOP_LABELLER")


# ================================================================================================ dispatch
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--follow", action="store_true")
    ap.add_argument("--n_cal", type=int, default=25)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--part", default="all")
    args = ap.parse_args()
    setup_logging(f"stage_{args.stage}")
    if args.stage not in GPU_STAGES:            # CUDA reserves a huge virtual address space: no RLIMIT_AS on GPU
        set_ram_limit(12)                       # stages (their RSS is monitored in the logs instead)
    t0 = time.time()
    logger.info(f"stage {args.stage} start")

    @logger.catch(reraise=True)
    def run() -> None:
        if args.stage == "s0":
            stage_s0(args)
        elif args.stage == "engine":
            stage_engine(args)
        elif args.stage == "label":
            stage_label(args)
        elif args.stage in ("g3a", "g3b"):
            import g3

            getattr(g3, f"stage_{args.stage}")(args)
        elif args.stage in ("yv", "g2", "g2r", "g2d", "g2smoke", "g2pairs"):
            import g2

            getattr(g2, f"stage_{args.stage}")(args)
        elif args.stage in ("g1p", "g1v", "g1gen"):
            import g1

            getattr(g1, f"stage_{args.stage}")(args)
        elif args.stage in ("novelty", "analysis", "figures", "outputs"):
            import analysis7

            getattr(analysis7, f"stage_{args.stage}")(args)
        else:
            raise ValueError(f"unknown stage {args.stage}")
    run()
    append_jsonl(RESULTS_DIR / "stage_timing.jsonl", [{"stage": args.stage, "seconds": time.time() - t0,
                                                       "utc": utc_now()}])
    logger.info(f"stage {args.stage} done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
    _ = (I6_DATA, I6_RESULTS, I6_NATURAL, read_json, PRED_DIR)
