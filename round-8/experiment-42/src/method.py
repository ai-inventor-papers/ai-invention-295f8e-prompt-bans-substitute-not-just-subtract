#!/usr/bin/env python3
"""Iteration 8, claim G: a fair test of Gemma's BFS dial (google/gemma-3-4b-it, bf16, one RTX-class GPU).

Iteration 7 (art_HY7uYZz-OjRW) raised correct BFS programs from 11/50 (twin) to 42/50 with a rank-4 DAS edit at
block 17 after the c* prefill, and compared it with a forced-BFS prompt sampled WITHOUT the prefill (35/50). This
artifact runs the missing cells of the 2x2 {prompt, dial} x {c* prefilled, free generation} on the SAME 50 CRN slots,
plus dormancy checks of the subspace at ranks 1, 2, 4, 8.

Stages (`.venv/bin/python method.py --stage <name>`):
  s0       CPU: input hashes, labeller re-check, prompts, slot keys, decision-rule unit tests (U5), analysis8 on
           iteration 7's rows, dependency corpus -> known-solution pool, COMMIT #0
  gpu1     GPU: unit tests U1, U2, U3', U4'; engine check (P-twin, P-DAS-bfs); teacher-forced stage S3 (3a-3d) and
           COMMIT #1; G1 cells (G1a, G1b, G1c, P-DAS-dfs, G1d); free twin F-twin (S50 + HT30); reverse generation
  commit2  GPU: waits for the labels it needs, fixes the decision position per slot from F-twin, TF predictions at
           R2 positions, COMMIT #2
  fcells   GPU: edited free-generation cells (decode-time edit at i_d - 1), prefix check
  label    CPU label worker (frozen exp8 T1 labeller), follows data/raw_*.jsonl
  novelty / positioning / analysis / figures / outputs
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

from cfg import (B_IDS, D_IDS, DATA_DIR, I6, IT_ID, IT_REV, PRED_DIR, RESULTS_DIR, SUBSPACE_DIR, TEMPLATE_IDS,  # noqa: E402
                 add_deviation, append_jsonl, container_ram_gb, detect_cpus, read_json, read_jsonl, set_ram_limit,
                 setup_logging, sha256_file, slot_key7, utc_now, write_json, write_jsonl)
import cfg8 as C8  # noqa: E402

GPU_STAGES = ("gpu1", "commit2", "fcells", "gputests", "gpu_extra", "tf_extra")
E38_REL = "ITER7/gen_art_experiment_38"
E33_REL = "ITER7/gen_art_experiment_33"


def artifact_dir(art_id: str, env: str, volume_rel: str) -> Path:
    """ONE location per input artifact, named by its id: the environment variable `env` if set; else the sibling
    folder named by the artifact id (the published repository's layout); else the run-volume layout, relative to this
    file's folder. Inputs are only ever READ there (copied into this workspace by hand, verified by stage s0)."""
    import os

    if os.environ.get(env):
        return Path(os.environ[env])
    sib = ROOT.parent / art_id
    return sib if sib.exists() else ROOT / volume_rel


ART_E38 = artifact_dir("art_HY7uYZz-OjRW", "AII_ART_HY7UYZZ_OJRW", "../../../iter_7/gen_art/gen_art_experiment_38")
ART_E33 = artifact_dir("art_veI9l_Rb9wDY", "AII_ART_VEI9L_RB9WDY", "../../../iter_7/gen_art/gen_art_experiment_33")
ART_DEP = artifact_dir("art_j3Rm_lr2nzR6", "AII_ART_J3RM_LR2NZR6",
                       "../../../../../run_4VFKidE1bxPG/3_invention_loop/iter_1/gen_art/gen_art_dataset_1")
DEP_ABS = ART_DEP                    # the declared dependency (dataset artifact): full_data_out.json
ART_IDS = {"E38": "art_HY7uYZz-OjRW", "E33": "art_veI9l_Rb9wDY"}
COPIES = {  # workspace path -> (source artifact key, path inside that artifact); copied read-only
    **{f"src/{p.name}": ("E38", f"src/{p.name}") for p in sorted((ROOT / "src").glob("*.py"))
       if p.name not in ("cfg8.py", "gen8.py", "tf8.py", "analysis8.py", "figures8.py", "outputs8.py",
                         "novelty8.py", "positioning8.py")},
    **{f"cache/das_subspaces/{n}.pt": ("E38", f"cache/das_subspaces/{n}.pt")
       for n in ("das_L17_seed0", "das_L17_seed1", "das_L17_seed2", "dim_L17", "shuf_L17_perm0", "shuf_L17_perm1",
                 "shuf_L17_perm2")},
    **{f"cache/states/{n}.pt": ("E38", f"cache/states/{n}.pt") for n in ("fork_variants", "fork_sources", "fork_twins")},
    **{f"inputs/iter7/predictions/{n}.json": ("E38", f"predictions/{n}.json") for n in ("commit0", "commit3")},
    **{f"inputs/iter7/results/{n}.json": ("E38", f"results/{n}.json")
       for n in ("g2_das", "g2_decisions", "g2_dose", "g2_dose_tf_pred", "g3_cal", "engine_check", "yv", "g2_pairs",
                 "g2_layer_scan", "deviations")},
    "inputs/iter7/data/raw_g2dose.jsonl": ("E38", "data/raw_g2dose.jsonl"),
    "inputs/iter7/data/labels.jsonl": ("E38", "data/labels.jsonl"),
    "inputs/iter7/e33_dormant.json": ("E33", "results/dormant.json"),
    "pyproject.toml": ("E38", "pyproject.toml"),
}
SRC_DIRS = {"E38": ART_E38, "E33": ART_E33}


# ================================================================================================ S0
def _mutants(ref: str) -> dict[str, str]:
    """Iteration 7's five hand-made wrong programs (each must FAIL the hidden tests)."""
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


def u5_tests() -> dict[str, Any]:
    """Decision-rule unit tests on hand-made token sequences (synthetic class masses)."""
    import numpy as np

    import fork7 as FK
    import prompts as PG
    from gen8 import decide

    tok = PG.tokenizer()
    cs = FK.cstar()
    dec = lambda ids: tok.decode(ids)       # noqa: E731
    enc = lambda s: tok(s, add_special_tokens=False)["input_ids"]      # noqa: E731
    res = {}
    seq = cs + enc("visited = set()\n")
    res["exact_cstar"] = decide(seq, [0.9] * 60, [0.3] * 60, cs, dec)
    doc = enc('```python\ndef solve(grid, start, goal):\n    """Find a path."""\n    rows = len(grid)\n    cols = len(grid[0])\n    ')
    pB = [0.05] * 80
    pD = [0.05] * 80
    i_ind = [i + 1 for i, t in enumerate(doc) if t == cs[31]]
    for i in i_ind[1:]:
        pB[i], pD[i] = 0.6, 0.3
    res["docstring_opening"] = decide(doc + enc("visited = set()\n"), pB, pD, cs, dec)
    res["docstring_expected_i_d"] = i_ind[1]
    two = enc("```python\ndef solve(grid, start, goal):\n  rows = len(grid)\n  cols = len(grid[0])\n  ")
    res["two_space_indent"] = decide(two + enc("visited = set()\n"), [0.9] * 80, [0.3] * 80, cs, dec)
    dq = enc("```python\nfrom collections import deque\n\ndef solve(grid, start, goal):\n    rows = len(grid)\n    ")
    res["deque_first"] = decide(dq + enc("q = deque()\n"), [0.9] * 80, [0.3] * 80, cs, dec)
    early = [cs[31]] * 40
    res["early_indents"] = decide(early, [0.9] * 40, [0.3] * 40, cs, dec)
    low_d = enc("```python\ndef solve(grid, start, goal):\n    rows = len(grid)\n    ")
    res["pD_below_0.01"] = decide(low_d + enc("x = 1\n"), [0.9] * 80, [0.001] * 80, cs, dec)
    ok = (res["exact_cstar"]["reach_type"] == "R1" and res["exact_cstar"]["i_d"] == 32
          and res["docstring_opening"]["reach_type"] == "R2" and res["docstring_opening"]["i_d"] == i_ind[1]
          and res["two_space_indent"]["reach_type"] == "NOT_REACHED"
          and res["deque_first"]["reach_type"] == "NOT_REACHED"
          and res["early_indents"]["reach_type"] == "R2" and res["early_indents"]["i_d"] == 8
          and res["pD_below_0.01"]["reach_type"] == "NOT_REACHED")
    res["pass"] = bool(ok)
    _ = np
    return res


def build_known_pool() -> dict[str, Any]:
    """Load ALL 10 datasets of the declared dependency art_j3Rm_lr2nzR6 (full_data_out.json) and build the
    nearest-known-solution pool for the novelty audit from every code-bearing dataset; summarise the others."""
    import re

    src = DEP_ABS / "full_data_out.json"
    d = json.loads(src.read_text())
    pool, usage = [], {}
    graph_re = re.compile(r"\b(bfs|dfs|breadth|depth|deque|queue|visited|dijkstra|heapq|a\*|astar|shortest|grid|path)\b",
                          re.I)
    for ds in d["datasets"]:
        name = ds["dataset"]
        ex = ds["examples"]
        n_code = 0
        for i, e in enumerate(ex):
            out = str(e.get("output") or "")
            inp = str(e.get("input") or "")
            is_code = ("def " in out or "class " in out) and name not in ("llm_creativity", "concreteness_norms",
                                                                         "clrs_text")
            if not is_code:
                continue
            n_code += 1
            if graph_re.search(inp[:3000]) or graph_re.search(out[:4000]):
                pool.append({"source": name, "idx": i, "code": out[:6000],
                             "hint": str(e.get("metadata_named_algorithms") or e.get("metadata_bench_task") or "")[:120]})
        meta_keys = sorted({k for e in ex[:50] for k in e if k.startswith("metadata_")})[:12]
        usage[name] = {"n_examples": len(ex), "n_code_examples": n_code, "metadata_keys_sample": meta_keys}
    # concreteness norms: are the 24 twin-variant nouns among the neutral-noun candidates?
    import fork7 as FK

    nn = FK.nouns()
    allnouns = set(nn["frozen"]) | set(nn["new"])
    cn = next((ds for ds in d["datasets"] if ds["dataset"] == "concreteness_norms"), None)
    if cn is not None:
        words = {str(e.get("input")).strip().lower(): e for e in cn["examples"]}
        found = [n for n in allnouns if n.lower() in words]
        flagged = [n for n in found if str(words[n.lower()].get("metadata_neutral_noun_candidate", "")).lower()
                   in ("true", "1")]
        usage["concreteness_norms"]["twin_nouns_found"] = f"{len(found)}/{len(allnouns)}"
        usage["concreteness_norms"]["twin_nouns_flagged_neutral"] = f"{len(flagged)}/{len(allnouns)}"
    lc = next((ds for ds in d["datasets"] if ds["dataset"] == "llm_creativity"), None)
    if lc is not None:
        from collections import Counter

        usage["llm_creativity"]["t02_mode_counts"] = dict(Counter(str(e.get("output")) for e in lc["examples"]))
    clrs = next((ds for ds in d["datasets"] if ds["dataset"] == "clrs_text"), None)
    if clrs is not None:
        from collections import Counter

        usage["clrs_text"]["algorithms"] = dict(Counter(str(e.get("metadata_algorithm") or e.get("output", "")[:20])
                                                        for e in clrs["examples"]).most_common(15))
    del d
    write_json(ROOT / "cache" / "known_pool.json", {"n": len(pool), "rows": pool})
    return {"dependency": "art_j3Rm_lr2nzR6 (full_data_out.json)", "sha256": sha256_file(src), "n_pool": len(pool),
            "pool_by_source": {k: sum(1 for p in pool if p["source"] == k) for k in usage}, "usage": usage}


def stage_s0(args: argparse.Namespace) -> None:
    import fork7 as FK
    import prompts as PG
    from cfg import SUITE, bench_paths

    t0 = time.time()
    res: dict[str, Any] = {}
    # ---------------- copied inputs: sha256 against their sources (never written there)
    hashes, bad = {}, []
    for dst, (key, srel) in COPIES.items():
        a = sha256_file(ROOT / dst) if (ROOT / dst).exists() else None
        s = SRC_DIRS[key] / srel
        b = sha256_file(s) if s.exists() else None
        if dst == "pyproject.toml":
            b = a          # renamed project (name/description lines); the dependency pins are unchanged
        hashes[dst] = {"sha256": a, "source": f"{ART_IDS[key]} ({E38_REL if key == 'E38' else E33_REL}):{srel}",
                       "source_sha256": b, "match": a == b}
        if a != b:
            bad.append(dst)
    man = (I6 / "MANIFEST.sha256").read_text().splitlines()
    mbad = [ln.split(None, 1)[1] for ln in man if sha256_file(I6 / ln.split(None, 1)[1].strip().lstrip("./")) != ln.split()[0]]
    write_json(ROOT / "inputs" / "input_hashes.json", {"copies": hashes, "iter6_manifest": {"n": len(man),
                                                                                           "n_mismatch": len(mbad)}})
    res["inputs"] = {"n_copies": len(hashes), "n_mismatch": len(bad), "mismatch": bad,
                     "iter6_manifest_n": len(man), "iter6_manifest_mismatch": len(mbad)}
    assert not mbad, f"iteration-6 manifest mismatch: {mbad[:3]}"
    # ---------------- labeller re-check (12 references, 5 mutants)
    bench_paths()
    import label_worker as LW
    from tasks.harness import run_tests

    refs = sorted((SUITE / "tasks" / "t1_grid" / "references").glob("*.py"))
    mode_of = {"astar": "astar_gbfs", "gbfs": "astar_gbfs", "bfs": "bfs", "bibfs": "bibfs", "dfs": "dfs",
               "dijkstra": "dijkstra", "iddfs": "iddfs"}
    rr = []
    for f in refs:
        want = mode_of[f.stem.split("_")[0]]
        mech = LW._path_mech("t1", f.read_text())
        rr.append({"file": f.name, "want": want, "runtime": mech["runtime_label"], "ast": mech["ast_label"],
                   "passed": mech["passed"], "ok": mech["runtime_label"] == want and mech["ast_label"] == want
                   and mech["passed"]})
    ref_bfs = (SUITE / "tasks" / "t1_grid" / "references" / "bfs_deque_parent.py").read_text()
    mut = {k: bool(run_tests("t1", code).get("passed")) for k, code in _mutants(ref_bfs).items()}
    res["labeller_references"] = {"n": len(rr), "n_ok": sum(r["ok"] for r in rr), "rows": rr}
    res["checker_mutants"] = {"n": len(mut), "n_rejected": sum(not v for v in mut.values()), "passed": mut}
    assert res["labeller_references"]["n_ok"] == 12 and res["checker_mutants"]["n_rejected"] == 5, "labeller gate"
    # ---------------- prompts, token ids, c*
    tok = PG.tokenizer()
    cs = FK.cstar()
    assert len(cs) == 32 and tok.decode(cs) == FK.fork_table()["cstar_text"]
    dec_B = [tok.decode([t]) for t in B_IDS]
    assert dec_B == ["\n", "if", "queue", "q"] or [d.strip() or d for d in dec_B] == ["\n", "if", "queue", "q"], dec_B
    assert tok.decode([D_IDS[0]]).strip() == "visited"
    prompts = []
    for w in TEMPLATE_IDS:
        p = FK.twin(w)
        prompts.append({"name": f"twin|{w}", "P": p["P"], "spec_start": p["spec_start"], "prompt_sha256": p["prompt_sha256"],
                        "text": tok.decode(p["ids"])})
    for mode in ("bfs", "dfs"):
        for f in ("F1", "F2", "F3", "F4", "F5"):
            p = FK.forced(mode, f, 3)
            prompts.append({"name": f"forced|{mode}|{f}|3", "P": p["P"], "spec_start": p["spec_start"],
                            "prompt_sha256": p["prompt_sha256"], "text": tok.decode(p["ids"])})
            assert p["spec_start"] == FK.twin("W" + f[1:])["spec_start"], "forced/twin alignment"
    srcs = FK.forced_sources()
    assert len(srcs) == 40
    write_jsonl(ROOT / "prompts" / "prompts8.jsonl", prompts)
    res["prompts"] = {"n": len(prompts), "cstar_len": len(cs), "B": dec_B, "D": tok.decode([D_IDS[0]]),
                      "n_forced_sources": len(srcs), "body_indent_token": [cs[31], tok.decode([cs[31]])]}
    # ---------------- S50 ukeys equal iteration 7's dose-sweep keys
    i7 = {r["row_id"]: r for r in read_jsonl(C8.I7_RAW_DOSE) if r["row_id"].startswith("g2|twin|")}
    ok_keys = all(list(i7[f"g2|twin|{w}|{k}"]["ukey"]) == list(slot_key7("G2", w, k)) for w, k in C8.S50)
    res["slot_keys_match_iter7"] = bool(ok_keys)
    assert ok_keys
    # ---------------- U5 decision-rule unit tests
    res["U5_decision_rule"] = u5_tests()
    assert res["U5_decision_rule"]["pass"], res["U5_decision_rule"]
    # ---------------- analysis8 on iteration 7's raw rows
    import analysis8 as A8

    rep = A8.iter7_reproduction(read_jsonl(C8.I7_LABELS))
    g2d = read_json(C8.I7 / "results" / "g2_dose.json")["cells"]
    exp = {"twin": g2d["twin"]["correct_target"], "das_lam1": g2d["DAS|bfs|1.0"]["correct_target"],
           "forced_f5_unprefilled": g2d["forced_bfs_F5"]["correct_target"],
           "p_das_vs_twin": g2d["DAS|bfs|1.0"]["p_correct_one_sided"]}
    got = {"twin": rep["twin"]["correct_target"], "das_lam1": rep["das_lam1"]["correct_target"],
           "forced_f5_unprefilled": rep["forced_f5_unprefilled"]["correct_target"],
           "p_das_vs_twin": rep["mcnemar_das_vs_twin"]["p_one_sided"]}
    res["analysis8_on_iter7"] = {"expected": exp, "got": got, "full": rep,
                                 "match": all(abs(float(exp[k]) - float(got[k])) < 1e-12 for k in exp)}
    assert res["analysis8_on_iter7"]["match"], res["analysis8_on_iter7"]
    # ---------------- dependency corpus -> known-solution pool (all 10 datasets loaded)
    res["dependency"] = build_known_pool()
    # ---------------- hardware
    import torch
    import transformers

    hw = {"gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
          "vram_gb": torch.cuda.get_device_properties(0).total_memory / 1e9 if torch.cuda.is_available() else None,
          "cpus": detect_cpus(), "ram_gb_container": container_ram_gb(), "torch": torch.__version__,
          "transformers": transformers.__version__, "cuda": torch.version.cuda, "python": sys.version.split()[0]}
    write_json(PRED_DIR / "hardware.json", hw)
    write_json(RESULTS_DIR / "s0_tests.json", res)
    # ---------------- COMMIT #0
    import commit as CM

    design = {"B_CRN": 25, "MAX_NEW": C8.MAX_NEW, "layer": C8.L, "k_star": C8.KSTAR, "ranks": list(C8.RANKS),
              "seeds": list(C8.SEEDS), "fork_index": 32, "B_ids": list(B_IDS), "D_ids": list(D_IDS),
              "slots": {"S50": "(iter7GG2, T1, w, k), w in W1-W5, k in 0-9 (iteration 7's dose-sweep streams)",
                        "S30": "k in 0-5 of S50", "HT30": "(iter7GG2, T1, w, k), w in W4-W5, k in 10-24 (new streams)"},
              "cells": {"engine": ["P-twin", "P-DAS-bfs"], "G1": ["G1a", "G1b", "G1c", "P-DAS-dfs", "G1d (optional)"],
                        "G2_free": ["F-twin"] + list(C8.FREE_CORE) + [c + " (optional)" for c in C8.FREE_OPTIONAL],
                        "HT30": ["F-twin", "F-DAS-r4-bfs-1.0"], "G3_reverse_gen": list(C8.REV_CELLS)},
              "edits": {"DAS": "f(h) = h + lam R_k (c_Y - R_k^T h), R_k = das_L17_seed0[:, :k]; c_Y = commit3 class "
                                "means (rank 4) and their first k coordinates for k < 4; other seeds/ranks: the same "
                                "mean recomputed on this engine",
                        "DiM": "f(h) = h + beta u, u = dim_L17; beta re-bisected on this engine to the mean "
                               "teacher-forced dy of DAS r4 lam 1 over the 72 train bases (grid scan first)",
                        "RAND": "Rr = qr(randn(2560, 4, seed 31337)); c_rand = mean Rr^T h over BFS train sources; lam 1",
                        "REV-DAS": "forced F5 BFS + c*: h' = h + R_4 (R_4^T h_tw(w) - R_4^T h) at p_f",
                        "REV-FULL": "forced F5 BFS + c*: h' = h_tw(w) at p_f",
                        "prefilled": "applied at p_f during the prefill of prompt + c*",
                        "free": C8.DECISION_RULES["FREE_EDIT"]},
              "decoding": "T 1.0, top-p 1, no top-k, max_new 1024, fence stop, exact inverse-CDF CRN (stream index "
                          "= response index), fixed batch shape 25"}
    c0 = CM.commit("commit0", {"design": design, "decision_rules": C8.DECISION_RULES, "drop_order": C8.DROP_ORDER,
                               "never_drop": C8.NEVER_DROP, "hardware": hw,
                               "predictions": {"P1": "G1a correct BFS >= 40/50",
                                               "P1b": "P-DAS-bfs vs G1a two-sided McNemar p >= 0.05 (matches)",
                                               "P2": "F-DAS-r4-bfs-1.0 correct BFS >= 30/50, pass >= 0.8 x F-twin, > F-twin",
                                               "P3": "reach share >= 0.80; R1 share about 0.86",
                                               "P4": "R1-slot label agreement >= 0.90 (twin and DAS pairs)",
                                               "P5": "account: reverse recovery >= 0.5 and retention >= 0.5 at k = 4; "
                                                     "iteration 7: LOW_NATURAL_VARIANCE at k = 1, 2, 4",
                                               "P6": "F-DiM-bfs pass < 0.8 x F-twin pass",
                                               "P7": "TF-predicted attempted BFS within 0.10 of observed in every "
                                                     "prefilled cell"},
                               "code_sha256": {p: sha256_file(ROOT / p) for p in
                                               ("src/analysis8.py", "src/cfg8.py", "src/gen8.py", "src/tf8.py", "method.py")},
                               "input_hashes_sha256": sha256_file(ROOT / "inputs" / "input_hashes.json"),
                               "s0_tests_sha256": sha256_file(RESULTS_DIR / "s0_tests.json")})
    logger.info(f"S0 done in {time.time() - t0:.0f}s; commit0 {c0['sha256'][:12]}; pool {res['dependency']['n_pool']}")


# ================================================================================================ GPU helpers
def _edits_ctx(run: Any) -> dict[str, Any]:
    """Maps, class targets (commit3 for seed 0, k <= 4) and the DAS/DiM/RAND edit functions."""
    import torch

    import tf8

    maps = tf8.load_maps()
    c3 = read_json(C8.I7 / "predictions" / "commit3.json")["target_coordinates"]
    c3t = {Y: torch.tensor(c3[Y], device="cuda", dtype=torch.float32) for Y in ("bfs", "dfs")}
    tfs = read_json(RESULTS_DIR / "tf_stage.json") if (RESULTS_DIR / "tf_stage.json").exists() else None

    def target(seed: int, k: int, Y: str) -> torch.Tensor:
        if seed == 0 and k <= 4:
            return c3t[Y][:k]
        assert tfs is not None, "recomputed targets need the TF stage"
        return torch.tensor(tfs["targets"][f"seed{seed}_k{k}"][Y], device="cuda", dtype=torch.float32)

    def fn_for(method: str, k: int, Y: str, lam: float | None, seed: int = 0):
        if method == "DAS":
            return tf8.das_fn(maps["R"][seed][:, :k], target(seed, k, Y), float(lam))
        if method == "DiM":
            assert tfs is not None
            return tf8.dim_fn(maps["u"], float(tfs["dim_betas"][Y]["beta"]))
        if method == "RAND":
            assert tfs is not None
            return tf8.das_fn(maps["Rr"], torch.tensor(tfs["targets"]["rand_r4"]["bfs"], device="cuda"), 1.0)
        raise ValueError(method)
    return {"maps": maps, "target": target, "fn_for": fn_for, "tfs": tfs}


def _done(path: Path) -> set[str]:
    return {r["row_id"] for r in read_jsonl(path)}


def _rows(cell: str, slots: list[tuple[str, int]], done: set[str], meta: dict[str, Any], edits: list | None = None
          ) -> list[dict[str, Any]]:
    out = []
    for w, k in slots:
        r = C8.rid(cell, w, k)
        if r in done:
            continue
        out.append({"row_id": r, "ukey": C8.ukey(w, k), "edits": edits or [],
                    "meta": dict(meta, part=meta.get("part", "G8"), cell=cell, template=w, slot=k)})
    return out


def gpu_unit_tests(run: Any, E: dict[str, Any]) -> dict[str, Any]:
    import numpy as np
    import torch

    import engine as EG
    import fork7 as FK
    import tf8
    from gen8 import decode8

    cs = FK.cstar()
    out: dict[str, Any] = {}
    raw_u = DATA_DIR / "tests_u.jsonl"
    # U1: CRN determinism (free decode, same slot twice)
    p = FK.twin("W1")
    rows = [{"row_id": f"u1|{k}", "ukey": slot_key7("U1", "W1", k), "meta": {"arm": "u1"}} for k in range(2)]
    a = run.run_cell(p["ids"], [], rows, raw_u, "U1a", max_new=96)
    b = run.run_cell(p["ids"], [], [dict(r, row_id=r["row_id"] + "b") for r in rows], raw_u, "U1b", max_new=96)
    out["U1_crn_determinism"] = {"pass": all(x["token_ids"] == y["token_ids"] for x, y in zip(a, b))}
    # U2: identity edits are bit-identical (prefill path, batch 1)
    ids = p["ids"] + cs
    pf = len(ids) - 1
    r0 = torch.tensor([0], device="cuda")
    base = run.logits_rows(ids, 1)
    R4 = E["maps"]["R"][0][:, :4]
    hsrc = run.states(ids, [C8.L], positions=[pf])["h"][C8.L][0].cuda()
    ident = {"das_lam0": tf8.das_fn(R4, E["target"](0, 4, "bfs"), 0.0),
             "das_target_own_coords": (lambda h: h + 1.0 * ((h @ R4 - h @ R4) @ R4.T)),
             "full_exchange_source_eq_base": tf8.full_fn(hsrc)}
    out["U2_identity"] = {}
    for nm, f in ident.items():
        e = tf8.prefill_edit(f, pf, nm)
        lg = run.logits_rows(ids, 1, [(e, r0)])
        out["U2_identity"][nm] = bool(torch.equal(lg, base))
    # U3' / U4': decode-time hook on a free trajectory forced to reproduce c* (B = 25 fixed shape)
    u3 = {}
    for w in ("W1", "W5"):
        pw = FK.twin(w)
        idsw = pw["ids"] + cs
        f = E["fn_for"]("DAS", 4, "bfs", 1.0)
        B = run.B
        U = np.stack([EG.u_stream(*C8.ukey(w, k % 10), n=40) for k in range(B)])
        res_runs = {}
        for tag, sched_rows in (("plain", []), ("edited", [0, 1, 2])):
            pre = run.prefill(pw["ids"], B, [])
            sched = {31: [(torch.tensor(sched_rows, device="cuda"), f, "das")]} if sched_rows else {}
            res_runs[tag], _ = decode8(run.model, run.tok, pre, U, np.ones(B), 40, sched=sched, force=cs, rec_upto=40)
            del pre
        lg_e = run.logits_rows(idsw, 1, [(tf8.prefill_edit(f, len(idsw) - 1, "das"), r0)])[0, 0]
        lg_0 = run.logits_rows(idsw, 1)[0, 0]
        import g2

        m_pref_e, m_pref_0 = float(g2.margin(lg_e)), float(g2.margin(lg_0))
        m_dec_e = [res_runs["edited"][r]["rec"]["m"][32] for r in (0, 1, 2)]
        m_dec_0 = [res_runs["plain"][r]["rec"]["m"][32] for r in (0, 1, 2)]
        unsched_same = all(res_runs["edited"][r]["token_ids"] == res_runs["plain"][r]["token_ids"] and
                           res_runs["edited"][r]["rec"]["m"] == res_runs["plain"][r]["rec"]["m"] for r in range(3, B))
        before_same = all(res_runs["edited"][r]["rec"]["m"][:32] == res_runs["plain"][r]["rec"]["m"][:32]
                          for r in (0, 1, 2))
        u3[w] = {"m_prefilled_edit": m_pref_e, "m_decode_edit": m_dec_e, "abs_diff_edit": max(abs(x - m_pref_e) for x in m_dec_e),
                 "m_prefilled_plain": m_pref_0, "m_decode_plain": m_dec_0,
                 "abs_diff_plain": max(abs(x - m_pref_0) for x in m_dec_0),
                 "edit_norm": res_runs["edited"][0]["edit"], "U4_unscheduled_rows_identical": bool(unsched_same),
                 "U4_scheduled_rows_identical_before_edit": bool(before_same)}
    out["U3p_decode_vs_prefill"] = {"by_template": u3, "tolerance_nat": C8.U3P_TOL,
                                    "within_tolerance": all(v["abs_diff_edit"] <= C8.U3P_TOL for v in u3.values())}
    out["U4p_row_mask"] = {"pass": all(v["U4_unscheduled_rows_identical"] and v["U4_scheduled_rows_identical_before_edit"]
                                       for v in u3.values())}
    return out


def stage_gpu1(args: argparse.Namespace) -> None:
    import torch

    import fork7 as FK
    import tf8
    from gen8 import FreeRunner

    assert (PRED_DIR / "commit0.json").exists(), "commit #0 must precede every sample"
    run = FreeRunner()
    cs = FK.cstar()
    E = _edits_ctx(run)
    timing = {}
    # ---------------- S1 unit tests
    if not (RESULTS_DIR / "tests_gpu.json").exists():
        t0 = time.time()
        ut = gpu_unit_tests(run, E)
        ut["seconds"] = time.time() - t0
        write_json(RESULTS_DIR / "tests_gpu.json", ut)
        logger.info(f"GPU tests: {json.dumps({k: v.get('pass', v.get('within_tolerance', v)) for k, v in ut.items() if isinstance(v, dict)})[:600]}")
        assert ut["U1_crn_determinism"]["pass"] and all(ut["U2_identity"].values()) and ut["U4p_row_mask"]["pass"]
    # ---------------- S2 engine check: P-twin + P-DAS-bfs (W1 first: time per sample)
    raw = C8.RAW["engine"]
    f_bfs = E["fn_for"]("DAS", 4, "bfs", 1.0)
    for w in TEMPLATE_IDS:
        t0 = time.time()
        p = FK.twin(w)
        ids = p["ids"] + cs
        pf = len(ids) - 1
        done = _done(raw)
        e = tf8.prefill_edit(f_bfs, pf, "P-DAS-bfs", {"method": "DAS", "rank": 4, "dir": "bfs", "lambda": 1.0})
        rows = _rows("P-twin", [(w, k) for k in range(10)], done, {"part": "engine", "method": "none",
                                                                   "prefilled": True}) + \
            _rows("P-DAS-bfs", [(w, k) for k in range(10)], done, {"part": "engine", "method": "DAS", "rank_k": 4,
                                                                   "dose": 1.0, "prefilled": True}, [e])
        if rows:
            run.run_cell(ids, cs, rows, raw, f"ENG:{w}")
        timing[f"engine_{w}"] = time.time() - t0
        logger.info(f"engine {w}: {len(rows)} rows in {timing[f'engine_{w}']:.1f}s")
    # ---------------- S3 teacher-forced stage + COMMIT #1
    if not (PRED_DIR / "commit1.json").exists():
        t0 = time.time()
        res = tf8.stage_tf(run, cs)
        maps = E["maps"]
        V, S, drop = __import__("g2")._load_states()
        res["targets"]["rand_r4"] = {"bfs": tf8.class_targets(S, drop, maps["Rr"], lambda s: s["h"][C8.L].float())["bfs"].tolist(),
                                     "note": "class mean over BFS train sources of iteration 7's cached states (as iteration 7)"}
        tf8.write_tf_results(res)
        timing["tf_stage"] = time.time() - t0
        tfs = read_json(RESULTS_DIR / "tf_stage.json")
        dorm = read_json(RESULTS_DIR / "dormancy.json")
        import commit as CM

        cp = tfs["cell_predictions"]
        c1 = CM.commit("commit1", {
            "tf_cell_predictions": cp,
            "tf_predicted_counts_N50": {c: {"attempted_bfs": 50 * v["pred_attempted_bfs"],
                                            "correct_bfs_twin_calibrated": 50 * v["pred_correct_bfs"],
                                            "attempted_dfs": 50 * v["pred_attempted_dfs"],
                                            "correct_dfs_twin_calibrated": 50 * v["pred_correct_dfs"]}
                                        for c, v in cp.items()},
            "G1d": tfs["G1d_template"], "dim_betas": {Y: {k: v for k, v in b.items() if k not in ("grid", "grid_mean_dy")}
                                                      for Y, b in tfs["dim_betas"].items()},
            "logp_cstar": tfs["logp_cstar"], "dormancy_tf_summary": dorm["summary_by_k"],
            "rev_generation_design": {"cells": list(C8.REV_CELLS), "slots": "S30", "baseline": "G1a rows on S30",
                                      "rule": C8.DECISION_RULES["RESTORATION_GEN"]},
            "tf_stage_sha256": sha256_file(RESULTS_DIR / "tf_stage.json"),
            "dormancy_sha256": sha256_file(RESULTS_DIR / "dormancy.json")})
        logger.info(f"commit1 {c1['sha256'][:12]} (TF stage {timing['tf_stage']:.0f}s)")
        E = _edits_ctx(run)
    tfs = E["tfs"]
    # ---------------- S4 G1 cells
    raw = C8.RAW["g1"]
    t0 = time.time()
    done = _done(raw)
    for cell, mode, prefill in (("G1a", "bfs", True), ("G1b", "dfs", True), ("G1c", "bfs", False)):
        p = FK.forced(mode, "F5", 3)
        rows = _rows(cell, C8.S50, done, {"part": "G1", "method": "prompt", "forced": f"{mode}|F5|3",
                                          "prefilled": prefill})
        if rows:
            run.run_cell(p["ids"] + (cs if prefill else []), cs if prefill else [], rows, raw, f"G1:{cell}")
    f_dfs = E["fn_for"]("DAS", 4, "dfs", 1.0)
    for w in TEMPLATE_IDS:
        ids = FK.twin(w)["ids"] + cs
        e = tf8.prefill_edit(f_dfs, len(ids) - 1, "P-DAS-dfs", {"method": "DAS", "rank": 4, "dir": "dfs", "lambda": 1.0})
        rows = _rows("P-DAS-dfs", [(w, k) for k in range(10)], done, {"part": "G1", "method": "DAS", "rank_k": 4,
                                                                      "dose": 1.0, "prefilled": True}, [e])
        if rows:
            run.run_cell(ids, cs, rows, raw, f"G1:P-DAS-dfs:{w}")
    g1d = tfs["G1d_template"]["chosen"]
    rows = _rows("G1d", C8.S50, done, {"part": "G1", "method": "prompt", "forced": f"bfs|{g1d}|3", "prefilled": True})
    if rows and not args.skip_optional:
        run.run_cell(FK.forced("bfs", g1d, 3)["ids"] + cs, cs, rows, raw, "G1:G1d")
    timing["g1"] = time.time() - t0
    # ---------------- S5a F-twin (S50 + HT30), unedited free generation with per-step records
    raw = C8.RAW["ftwin"]
    t0 = time.time()
    done = _done(raw)
    for w in TEMPLATE_IDS:
        sl = [(w, k) for k in range(10)] + [s for s in C8.HT30 if s[0] == w]
        rows = [dict(r, edit=None) for r in _rows("F-twin", sl, done, {"part": "G2", "method": "none", "prefilled": False})]
        if rows:
            run.run_cell_free(FK.twin(w)["ids"], rows, raw, f"FTW:{w}", steps_path=C8.STEPS)
    timing["ftwin"] = time.time() - t0
    # ---------------- S6 reverse generation (N = 30, S30)
    raw = C8.RAW["rev"]
    t0 = time.time()
    done = _done(raw)
    pF = FK.forced("bfs", "F5", 3)
    idsF = pF["ids"] + cs
    pfF = len(idsF) - 1
    R4 = E["maps"]["R"][0][:, :4]
    rows = []
    for w in TEMPLATE_IDS:
        idw = FK.twin(w)["ids"] + cs
        htw = run.states(idw, [C8.L], positions=[len(idw) - 1])["h"][C8.L][0].cuda().float()
        e_das = tf8.prefill_edit(tf8.interchange_fn(R4, htw), pfF, "REV-DAS", {"method": "REV-DAS", "rank": 4, "src": w})
        e_full = tf8.prefill_edit(tf8.full_fn(htw), pfF, "REV-FULL", {"method": "REV-FULL", "src": w})
        sl = [(w, k) for k in range(6)]
        rows += _rows("REV-DAS", sl, done, {"part": "G3rev", "method": "REV-DAS", "rank_k": 4, "prefilled": True}, [e_das])
        rows += _rows("REV-FULL", sl, done, {"part": "G3rev", "method": "REV-FULL", "prefilled": True}, [e_full])
    if rows:
        run.run_cell(idsF, cs, rows, raw, "REV")
    timing["rev"] = time.time() - t0
    write_json(RESULTS_DIR / "timing_gpu1.json", timing)
    run.free()
    _ = torch


# ================================================================================================ COMMIT #2
def _labels_ready(cells: list[str], timeout_s: float = 3600) -> dict[str, dict]:
    t0 = time.time()
    need = {C8.rid(c, w, k) for c in cells for (w, k) in C8.S50}
    while True:
        lab = {r["row_id"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl")}
        miss = need - set(lab)
        if not miss:
            return lab
        if time.time() - t0 > timeout_s:
            raise TimeoutError(f"{len(miss)} labels missing, e.g. {sorted(miss)[:3]}")
        logger.info(f"commit2: waiting for {len(miss)} labels")
        time.sleep(20)


def stage_commit2(args: argparse.Namespace) -> None:
    import numpy as np
    import torch

    import fork7 as FK
    import tf8
    from gen8 import FreeRunner, decide, literal_rule

    assert (PRED_DIR / "commit1.json").exists()
    lab = _labels_ready(["P-twin", "P-DAS-bfs", "P-DAS-dfs", "F-twin"])
    run = FreeRunner()
    E = _edits_ctx(run)
    tfs = E["tfs"]
    cs = FK.cstar()
    tok = run.tok
    raw = {r["row_id"]: r for r in read_jsonl(C8.RAW["ftwin"])}
    steps = {r["row_id"]: r["rec"] for r in read_jsonl(C8.STEPS)}
    cal = tf8.token_calibration()
    slots: dict[str, Any] = {}
    for w, k in C8.S50 + C8.HT30:
        r = raw[C8.rid("F-twin", w, k)]
        rec = steps[r["row_id"]]
        pB = [float("nan") if x is None else x for x in rec["pB"]]
        pD = [float("nan") if x is None else x for x in rec["pD"]]
        d = decide(r["token_ids"], pB, pD, cs, tok.decode)
        lit = literal_rule(pB, pD)
        d.update({"literal_rule_i": lit, "f_twin_label": lab.get(r["row_id"], {}).get("label"),
                  "f_twin_passed": lab.get(r["row_id"], {}).get("passed"),
                  "p_B_at_i_d": pB[d["i_d"]] if d["i_d"] is not None and d["i_d"] < len(pB) else None,
                  "p_D_at_i_d": pD[d["i_d"]] if d["i_d"] is not None and d["i_d"] < len(pD) else None,
                  "m_at_i_d_unedited": rec["m"][d["i_d"]] if d["i_d"] is not None and d["i_d"] < len(rec["m"]) else None,
                  "opening_text": tok.decode(r["token_ids"][:(d["i_d"] or 40)])[-200:]})
        slots[f"{w}|{k}"] = d
    # ---------------- decomposition predictions per free cell
    cond = tfs["tf_conditions"]
    tfname = {"F-DAS-r4-bfs-1.0": "DAS|s0|r4|bfs|1.0", "F-DAS-r4-bfs-0.5": "DAS|s0|r4|bfs|0.5",
              "F-DAS-r1-bfs-1.0": "DAS|s0|r1|bfs|1.0", "F-DAS-r1-bfs-0.5": "DAS|s0|r1|bfs|0.5",
              "F-DiM-bfs": "DiM|bfs|matched", "F-DAS-r4-dfs-1.0": "DAS|s0|r4|dfs|1.0", "F-DiM-dfs": "DiM|dfs|matched",
              "F-RAND-r4-1.0": "RAND|r4|1.0", "F-DAS-s2-r4-bfs-1.0": "DAS|s2|r4|bfs|1.0"}
    prefilled_same = {"F-DAS-r4-bfs-1.0": "P-DAS-bfs", "F-DAS-r4-dfs-1.0": "P-DAS-dfs"}
    r0 = torch.tensor([0], device="cuda")
    preds: dict[str, Any] = {}
    tf_r2: dict[str, Any] = {}
    for cell in C8.FREE_CORE + C8.FREE_OPTIONAL + ("F-twin",):
        tgt = C8.TARGET_OF[cell]
        key = "pred_correct_" + tgt
        tot, parts = 0.0, {"R1": 0.0, "R2": 0.0, "NOT_REACHED": 0.0}
        if cell != "F-twin":
            meth, k, Y, lam, sd = C8.FREE_SPECS[cell]
            f = E["fn_for"](meth, k, Y, lam, sd)
        for w, kk in C8.S50:
            d = slots[f"{w}|{kk}"]
            if d["reach_type"] == "R1":
                pc = prefilled_same.get(cell, "P-twin" if cell == "F-twin" else None)
                if pc is not None:
                    lr = lab[C8.rid(pc, w, kk)]
                    v = float(lr["label"] == tgt and bool(lr["passed"]))
                else:
                    v = float(cond[tfname[cell]][w][key])
            elif d["reach_type"] == "R2":
                ftw = raw[C8.rid("F-twin", w, kk)]
                ids = FK.twin(w)["ids"] + ftw["token_ids"][:d["i_d"]]
                if cell == "F-twin":
                    lg = run.logits_rows(ids, 1)[0, 0]
                else:
                    e = tf8.prefill_edit(f, len(ids) - 1, cell)
                    lg = run.logits_rows(ids, 1, [(e, r0)])[0, 0]
                st = tf8.fork_stats(lg, cal)
                tf_r2.setdefault(cell, {})[f"{w}|{kk}"] = st
                v = st[key]
            else:
                lr = lab[C8.rid("F-twin", w, kk)]
                v = float(lr["label"] == tgt and bool(lr["passed"]))
            parts[d["reach_type"]] += v
            tot += v
        preds[cell] = {"total": tot, "by_reach": parts, "target": tgt}
    rc = {t: sum(1 for (w, k) in C8.S50 if slots[f"{w}|{k}"]["reach_type"] == t) for t in ("R1", "R2", "NOT_REACHED")}
    # block-L states at the decision position (unedited free twin) for the geometry figure F4
    geo = {}
    for (w, kk) in C8.S50 + C8.HT30:
        d = slots[f"{w}|{kk}"]
        if d["i_d"] is None:
            continue
        ftw = raw[C8.rid("F-twin", w, kk)]
        ids = FK.twin(w)["ids"] + ftw["token_ids"][:d["i_d"]]
        h = run.states(ids, [C8.L], positions=[len(ids) - 1])["h"][C8.L][0].float()
        geo[f"{w}|{kk}"] = {"h": h, "reach_type": d["reach_type"], "i_d": d["i_d"]}
    torch.save(geo, ROOT / "cache" / "decision_states.pt")
    import commit as CM

    c2 = CM.commit("commit2", {"slots": slots, "reach_counts_S50": rc,
                               "reach_share_S50": (rc["R1"] + rc["R2"]) / 50, "predictions": preds,
                               "tf_at_R2": tf_r2, "rule": C8.DECISION_RULES["DECISION_POSITION"],
                               "decomposition_rule": "R1 slots: the prefilled same-cell program on this engine (twin, "
                                                     "DAS r4 lam1 bfs/dfs) else the 3a TF-predicted P(correct target) "
                                                     "at p_f under the same edit; R2: TF P(correct target) at i_d under "
                                                     "the edit; NOT_REACHED: 1[F-twin correct target]"})
    logger.info(f"commit2 {c2['sha256'][:12]}: reach {rc}; predictions " +
                ", ".join(f"{c} {v['total']:.1f}" for c, v in preds.items()))
    run.free()
    _ = np


def stage_fcells(args: argparse.Namespace) -> None:
    import fork7 as FK
    from gen8 import FreeRunner

    assert (PRED_DIR / "commit2.json").exists(), "commit #2 must precede the first edited free sample"
    c2 = read_json(PRED_DIR / "commit2.json")
    slots = c2["slots"]
    run = FreeRunner()
    E = _edits_ctx(run)
    raw = C8.RAW["fcells"]
    done = _done(raw)
    cells = list(C8.FREE_CORE) + ([] if args.skip_optional else list(C8.FREE_OPTIONAL))
    fns = {c: E["fn_for"](*C8.FREE_SPECS[c][:4], C8.FREE_SPECS[c][4]) for c in cells}
    t0 = time.time()
    for w in TEMPLATE_IDS:
        rows = []
        for c in cells:
            sl = [(w, k) for k in range(10)] + ([s for s in C8.HT30 if s[0] == w] if c == "F-DAS-r4-bfs-1.0" else [])
            meth, k, Y, lam, sd = C8.FREE_SPECS[c]
            for (ww, kk) in sl:
                r = C8.rid(c, ww, kk)
                if r in done:
                    continue
                d = slots[f"{ww}|{kk}"]
                edit = None if d["i_d"] is None else {"i_d": int(d["i_d"]), "fn": fns[c], "name": c,
                                                      "log": {"method": meth, "rank": k, "dir": Y, "lambda": lam,
                                                              "seed": sd}}
                rows.append({"row_id": r, "ukey": C8.ukey(ww, kk), "edit": edit,
                             "meta": {"part": "G2", "cell": c, "template": ww, "slot": kk, "method": meth,
                                      "rank_k": k, "dose": lam, "seed": sd, "prefilled": False,
                                      "reach_type": d["reach_type"], "decision_pos": d["i_d"],
                                      "reached_decision": d["i_d"] is not None}})
        if rows:
            run.run_cell_free(FK.twin(w)["ids"], rows, raw, f"FC:{w}", steps_path=C8.STEPS)
        logger.info(f"fcells {w}: {len(rows)} rows ({time.time() - t0:.0f}s)")
    run.free()
    # prefix check against F-twin: tokens before i_d must be identical
    ft = {(r["template"], r["slot"]): r for r in read_jsonl(C8.RAW["ftwin"])}
    rows = read_jsonl(raw)
    chk = []
    for r in rows:
        f = ft[(r["template"], r["slot"])]
        i_d = r.get("decision_pos")
        if i_d is None:
            pm = r["token_ids"] == f["token_ids"]
        else:
            pm = r["token_ids"][:i_d] == f["token_ids"][:i_d]
        chk.append({"row_id": r["row_id"], "prefix_match": bool(pm), "identical_to_ftwin": r["token_ids"] == f["token_ids"]})
    write_jsonl(DATA_DIR / "prefix_check.jsonl", chk)
    n_bad = sum(not c["prefix_match"] for c in chk)
    write_json(RESULTS_DIR / "prefix_check.json", {"n": len(chk), "n_mismatch": n_bad,
                                                   "share_mismatch": n_bad / max(len(chk), 1)})
    logger.info(f"prefix check: {n_bad}/{len(chk)} mismatches")


EXTRA_WORDINGS = [("F1", 3), ("F2", 3), ("F3", 3), ("F4", 3), ("F5", 0), ("F5", 1), ("F5", 2)]


def stage_gpu_extra(args: argparse.Namespace) -> None:
    """Exploratory extension (COMMIT #3 before sampling): the free-generation prompting baseline tuned across
    wordings, as the field does. Forced-BFS prompts F1-F4 (display pair 3) and F5 with display pairs 0-2, sampled
    from index 0 on the same 50 CRN slots (no prefill, no edit). Not part of any committed P1-P7 decision."""
    import fork7 as FK
    from gen8 import FreeRunner

    import commit as CM

    raw = DATA_DIR / "raw_g1e.jsonl"
    if not (PRED_DIR / "commit3.json").exists():
        CM.commit("commit3", {"extension": "free-generation forced-BFS prompting across wordings",
                              "cells": [f"G1e|{f}|{p}" for f, p in EXTRA_WORDINGS], "slots": "S50",
                              "rule": "each wording vs F-DAS-r4-bfs-1.0 on correct BFS, two-sided exact McNemar; "
                                      "reported with the mean and the best wording (best-of-8 is selected post hoc, "
                                      "so it is an optimistic prompting ceiling)",
                              "status": "exploratory; no committed prediction depends on it"})
    run = FreeRunner()
    done = _done(raw)
    for f, pi in EXTRA_WORDINGS:
        p = FK.forced("bfs", f, pi)
        cell = f"G1e|{f}|{pi}"
        rows = _rows(cell, C8.S50, done, {"part": "G1e", "method": "prompt", "forced": f"bfs|{f}|{pi}",
                                          "prefilled": False, "display": p["display"]})
        if rows:
            run.run_cell(p["ids"], [], rows, raw, f"G1e:{f}:{pi}")
    run.free()


def stage_tf_extra(args: argparse.Namespace) -> None:
    """Exploratory (COMMIT #4 before running): where along depth does the p_f residual carry the forced prompt's
    ' queue' preference? Single-block full-state swaps at p_f, block l = 0..33, teacher-forced (no sampling):
      reverse: base = forced-BFS F4/F5 (4 display pairs) + c*, block-l p_f state <- the aligned twin's (W4/W5) state;
      forward: base = twin W4/W5 + c*, block-l p_f state <- the forced-BFS state of each display pair;
      dial:    base = twin + c* with the rank-4 DAS edit at block 17 (the P-DAS-bfs state), block-l p_f state <- the
               forced-BFS state (does adding the prompt's late state reinstate ' queue'?).
    Reported: p(' queue'), p('\\n') + p('if'), p_B, p_D, margin m at p_f (batch-1 full forwards, one path)."""
    import torch

    import fork7 as FK
    import tf8
    from cfg import N_LAYERS
    from gen7 import Edit, Runner

    import commit as CM

    if not (PRED_DIR / "commit4.json").exists():
        CM.commit("commit4", {"extension": "layer sweep of single-block full-state swaps at p_f (teacher-forced)",
                              "design": stage_tf_extra.__doc__, "status": "exploratory; no committed prediction depends on it"})
    run = Runner()
    cs = FK.cstar()
    E = _edits_ctx(run)
    f_das = E["fn_for"]("DAS", 4, "bfs", 1.0)
    r0 = torch.tensor([0], device="cuda")
    out: dict[str, Any] = {"blocks": list(range(N_LAYERS)), "rows": []}

    def stats(lg: Any) -> dict[str, float]:
        p = torch.softmax(lg.float(), -1)
        z = lg.float()
        return {"p_queue": float(p[15204]), "p_nl_if": float(p[107] + p[584]), "p_B": float(p[list(B_IDS)].sum()),
                "p_D": float(p[D_IDS[0]]), "m": float(torch.logsumexp(z[list(B_IDS)], -1) - z[D_IDS[0]])}
    for f in ("F4", "F5"):
        w = "W" + f[1:]
        tw = FK.twin(w)["ids"] + cs
        st_tw = run.states(tw, list(range(N_LAYERS)), positions=[len(tw) - 1])["h"]
        st_twd = {}
        cap: dict[int, Any] = {}

        def mk(l: int) -> Any:
            def g(x: Any) -> None:
                cap[l] = x[0, len(tw) - 1].float().clone()
            return g
        from gen7 import edit_hooks

        e17 = tf8.prefill_edit(f_das, len(tw) - 1, "das")
        with torch.no_grad(), edit_hooks(run.model, [(e17, r0)], {("resid", l): mk(l) for l in range(N_LAYERS)}):
            run.model.model(input_ids=torch.tensor([tw], device="cuda"), use_cache=False)
        st_twd = dict(cap)
        for pi in range(4):
            fb = FK.forced("bfs", f, pi)["ids"] + cs
            assert len(fb) == len(tw)
            pf = len(fb) - 1
            st_fb = run.states(fb, list(range(N_LAYERS)), positions=[pf])["h"]
            base = {"reverse": stats(run.logits_rows(fb, 1)[0, 0]), "forward": stats(run.logits_rows(tw, 1)[0, 0]),
                    "dial": stats(run.logits_rows(tw, 1, [(e17, r0)])[0, 0])}
            for l in range(N_LAYERS):
                hs_tw = st_tw[l][0].cuda().float()
                hs_fb = st_fb[l][0].cuda().float()
                rev = Edit("resid", l, [pf], lambda x, r, h=hs_tw: h[None, None].expand_as(x).clone(), name="rev")
                fwd = Edit("resid", l, [pf], lambda x, r, h=hs_fb: h[None, None].expand_as(x).clone(), name="fwd")
                row = {"forced": f, "pair": pi, "block": l,
                       "reverse": stats(run.logits_rows(fb, 1, [(rev, r0)])[0, 0]),
                       "forward": stats(run.logits_rows(tw, 1, [(fwd, r0)])[0, 0])}
                if l > 17:
                    dial_fwd = [(e17, r0), (fwd, r0)]
                    row["dial_plus_forced_state"] = stats(run.logits_rows(tw, 1, dial_fwd)[0, 0])
                out["rows"].append(row)
            out.setdefault("bases", []).append({"forced": f, "pair": pi, **base})
        _ = st_twd
    write_json(RESULTS_DIR / "layer_sweep.json", out)
    run.free()
    logger.info(f"tf_extra: {len(out['rows'])} rows")


# ================================================================================================ labelling
def stage_label(args: argparse.Namespace) -> None:
    import label_worker as LW

    LW.PATH_JUDGE_CAP = C8.JUDGE_CAP_USD
    LW.N_WORKERS = 10
    LW.run_worker(follow=bool(args.follow), stop_file=DATA_DIR / "STOP_LABELLER")


# ================================================================================================ dispatch
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--follow", action="store_true")
    ap.add_argument("--skip_optional", action="store_true")
    args = ap.parse_args()
    setup_logging(f"stage_{args.stage}")
    if args.stage not in GPU_STAGES:            # CUDA reserves a large virtual address space: no RLIMIT_AS on GPU
        set_ram_limit(24)
    t0 = time.time()
    logger.info(f"stage {args.stage} start")

    @logger.catch(reraise=True)
    def run() -> None:
        if args.stage == "s0":
            stage_s0(args)
        elif args.stage == "gpu1":
            stage_gpu1(args)
        elif args.stage == "commit2":
            stage_commit2(args)
        elif args.stage == "fcells":
            stage_fcells(args)
        elif args.stage == "gpu_extra":
            stage_gpu_extra(args)
        elif args.stage == "tf_extra":
            stage_tf_extra(args)
        elif args.stage == "label":
            stage_label(args)
        elif args.stage in ("novelty", "positioning", "analysis", "figures", "outputs"):
            import outputs8

            getattr(outputs8, f"stage_{args.stage}")(args)
        else:
            raise ValueError(f"unknown stage {args.stage}")
    run()
    append_jsonl(RESULTS_DIR / "stage_timing.jsonl", [{"stage": args.stage, "seconds": time.time() - t0,
                                                       "utc": utc_now()}])
    logger.info(f"stage {args.stage} done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
    _ = (IT_ID, IT_REV, SUBSPACE_DIR, add_deviation)
