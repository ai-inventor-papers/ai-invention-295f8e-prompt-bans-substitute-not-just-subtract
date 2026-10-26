#!/usr/bin/env python3
# NOTE (published copy): this file names server paths this repository
# does not publish (a stage it does not ship, or another run's workspace),
# so the steps that read them will not run from a clone as written:
#   /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_35/data/
#   /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_34/data/
"""K3: the circuit behind Qwen3-8B's algorithm choice (bf16, thinking off).

Stages (each resumes from its result files; run as `uv run method.py --stages a,b,c`):
  setup       hardware, tokenizer asserts, CPU tests, contrast-free commit #0 (rules, predictions, code hashes)
  contrasts   C1-nat (120 B3 noun variants teacher-forced; pair sets A/B; held-out H), C1-forced (5 forced-Prim
              paraphrases vs padding twins), C2a (T10 twin variants vs the forced-DFS state exchange; F3 fallbacks)
  gputests    U1 pi(' Kr'), U2 patch-all smoke, U3 suffix-vs-full, U6 steering hook, U8 exchange identity, U9 memory
  circuit:X   AtP screen (+ reliability vs exact on 160 random nodes; IG-AtP if Spearman < 0.6), exact noising and
              denoising of the top 60 + 20 calibration nodes, path patching among the top 15, faithfulness curves
  commit1     frozen top-10/top-5, class means (sha256), write norms, matched random pools, RAND5
  validate:X  ABLATE / STEER of each top-10 node vs 50 matched random components (sign-flip tests, Holm)
  commit2     generation spec, then gen:X (TWIN / TOP5 / RAND5, PREFILL and FREE, N = 30 CRN slots, labelled)
  enginecheck B3 and T10 twin CRN slots vs the iteration-7 labels
  motif       committed motif test (Gemma's file first)
  analysis    verdicts, figures inputs, method_out.json
Contrasts: C1nat (primary, B3 ' Kr' vs ' Prim' after the 61-token opening), C1forced, C1mix (10 natural + 5 forced,
Gemma-matched, screen + exact only), C1natB (stability: disjoint pair set B), C2a (replication, T10 ' find' vs
' dfs' at token 11)."""

from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import k3circuit as KC  # noqa: E402
import k3engine as EN  # noqa: E402
import k3prompts as KP  # noqa: E402
import k3stats as KS  # noqa: E402
from k3cfg import (CACHE_DIR, CLASSES, COMMITS, DATA_DIR, E34, E35, GEN_PASS_RATIO, GEN_SLOTS, GEN_THRESH_PLUS,  # noqa
                   KS_FAITH, MAX_NEW_GEN, N_CAL, N_EDGE, N_LAYERS, N_RAND, N_REL_PER_CLASS, N_TOP_EXACT, N_VAL,
                   PRED_DIR, RESULTS_DIR, ROOT, SEED_CAL, SEED_POOL, SEED_RAND5, SEED_REL, STEER_DOSE, TE_MIN,
                   TEMPLATES, append_jsonl, container_ram_gb, detect_cpus, log_deviation, read_json, read_jsonl,
                   set_ram_limit, setup_logging, sha256_file, sha256_text, stage_time, u_stream, utc_now, write_json)

STATE: dict[str, Any] = {}


# ================================================================================================ commits
def commit(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    prev = "0" * 64
    if COMMITS.exists():
        lines = [l for l in COMMITS.read_text().splitlines() if l.strip()]
        if lines:
            prev = lines[-1].split()[2]
    utc = utc_now()
    body = json.dumps({"name": name, "utc": utc, "prev": prev, "payload": payload}, sort_keys=True, default=str)
    h = sha256_text(body)
    write_json(PRED_DIR / f"{name}.json", {"name": name, "utc": utc, "prev": prev, "sha256": h, "payload": payload})
    with open(COMMITS, "a") as fh:
        fh.write(f"{utc} {name} {h} prev={prev}\n")
    logger.info(f"COMMIT {name}: {h[:16]} (prev {prev[:12]})")
    return {"sha256": h, "utc": utc}


def code_hashes() -> dict[str, str]:
    files = sorted((ROOT / "src").glob("*.py")) + [ROOT / "method.py"]
    return {str(p.relative_to(ROOT)): sha256_file(p) for p in files}


# ================================================================================================ model / tokens
def model_tok() -> tuple[Any, Any]:
    if "model" not in STATE:
        tok, model, info = EN.load_model()
        STATE.update(model=model, tok=tok, load_info=info)
    return STATE["model"], STATE["tok"]


def tok_only() -> Any:
    if "tok" not in STATE:
        from transformers import AutoTokenizer

        from k3cfg import model_path
        STATE["tok"] = AutoTokenizer.from_pretrained(model_path())
    return STATE["tok"]


def tid(tok: Any, s: str) -> int:
    ids = tok(s, add_special_tokens=False)["input_ids"]
    if len(ids) != 1:
        log_deviation(f"multi_token_{s.strip()}", f"{s!r} is {len(ids)} Qwen3 tokens; the first subword is used")
    return ids[0]


def metrics(tok: Any) -> dict[str, EN.Metric]:
    if "metrics" not in STATE:
        STATE["metrics"] = {"B3": EN.Metric(tid(tok, " Kr"), tid(tok, " Prim")),
                            "T10": EN.Metric(tid(tok, " find"), tid(tok, " dfs")),
                            "T10b": EN.Metric(tid(tok, " find"), tid(tok, " dfs"), tid(tok, " bfs"))}
    return STATE["metrics"]


def nouns(tok: Any) -> list[str]:
    p = RESULTS_DIR / "nouns.json"
    if p.exists():
        return read_json(p)["nouns"]
    ns = [n for n in KP.noun_bank(tok) if n not in ("ass",)]
    write_json(p, {"source": "art_j3Rm_lr2nzR6 concreteness_norms (metadata_noun_bank_candidate == True), single "
                             "Qwen3 token as ' noun' and 'Noun', SUBTLEX order, task-related words excluded",
                   "n": len(ns), "nouns": ns})
    return ns


# ================================================================================================ stage: setup
def stage_setup() -> None:
    t0 = time.time()
    import platform
    import subprocess
    hw = {"gpu": subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used,driver_version",
                                 "--format=csv,noheader"], capture_output=True, text=True).stdout.strip(),
          "cpus": detect_cpus(), "ram_limit_GB": container_ram_gb(), "python": platform.python_version(),
          "torch": torch.__version__, "cuda": torch.version.cuda, "utc": utc_now()}
    import transformers
    hw["transformers"] = transformers.__version__
    write_json(PRED_DIR / "hardware.json", hw)
    tok = tok_only()
    toks = {s: tok(s, add_special_tokens=False)["input_ids"] for s in (" Kr", " Prim", " def", " find", " dfs", " bfs")}
    O = KP.b3_opening()
    pre = KP.t10_prefix()
    asserts = {"single_tokens": {s: len(v) == 1 for s, v in toks.items()}, "token_ids": toks,
               "B3_opening_len": len(O), "B3_opening_text": tok.decode(O),
               "B3_opening_matches_forks_json": tok.decode(O) == read_json(E35 / "results" / "forks.json")["B3"]
               ["opening"]["O_text"],
               "T10_prefix_text": tok.decode(pre), "T10_prefix_ends_in_def": pre[-1] == toks[" def"][0],
               "T10_prefix_len": len(pre)}
    write_json(RESULTS_DIR / "tokenizer_asserts.json", asserts)
    nouns(tok)
    # CPU unit tests
    tests = cpu_tests(tok)
    write_json(RESULTS_DIR / "tests_cpu.json", tests)
    if not COMMITS.exists() or "commit0" not in COMMITS.read_text():
        commit("commit0", commit0_payload())
    stage_time("setup", time.time() - t0)


def cpu_tests(tok: Any) -> dict[str, Any]:
    from k3motif import G2Q, motif
    out: dict[str, Any] = {}
    # T1 positions: disjoint and covering
    ok = True
    for w, r in KP.b3_twins(tok).items():
        allp = sorted(sum(r["pos"].values(), []))
        ok &= allp == list(range(r["P"] + r["L_open"]))
    for w, r in KP.t10_twins(tok).items():
        allp = sorted(sum(r["pos"].values(), []))
        ok &= allp == list(range(r["P"] + r["L_open"]))
    pj = read_json(ROOT / "inputs" / "iter5_exp26" / "units" / "B3" / "positions.json")
    ok_pos = all(KP.b3_twins(tok)[w]["P"] == pj[w]["P"] and KP.b3_twins(tok)[w]["p1"] == pj[w]["p1"] for w in TEMPLATES)
    out["T1_classes_disjoint_covering"] = bool(ok)
    out["T1_positions_match_positions_json"] = bool(ok_pos)
    # T2 node keys
    out["T2_n_nodes"] = len(KC.NODES)
    out["T2_roundtrip"] = all(KC.parse_key(KC.node_key(n)) == n for n in KC.NODES)
    # T3 motif on Gemma
    g = read_json(ROOT / "inputs" / "exp38" / "results" / "g1_pathpatch.json")
    sh = motif(g["exact"], list(range(15)), class_map=G2Q)
    out["T3_gemma_motif"] = {k: round(v, 4) for k, v in sh.items()}
    out["T3_pass"] = abs(sh["DEC"] - 0.53) <= 0.02 and abs(sh["COND"] - 0.36) <= 0.02
    # T4 sign flip
    rng = np.random.default_rng(1)
    d = rng.normal(0.3, 1, 10)
    brute = np.mean([np.dot(np.array([1 if (k >> i) & 1 else -1 for i in range(10)]), d) >= d.sum() - 1e-12
                     for k in range(1 << 10)])
    out["T4_exact_vs_brute"] = abs(KS.sign_flip_p(d) - brute) < 1e-12
    d22 = rng.normal(0.2, 1, 22)
    out["T4_exact_vs_mc"] = abs(KS.sign_flip_p(d22) - KS.sign_flip_p(d22, exact_max=0)) < 0.002
    # T5 Holm / McNemar vs statsmodels / scipy
    from statsmodels.stats.multitest import multipletests
    ps = [0.01, 0.04, 0.03, 0.2, 0.001]
    out["T5_holm"] = bool(np.allclose(KS.holm(ps), multipletests(ps, method="holm")[1]))
    from scipy.stats import binomtest
    out["T5_mcnemar"] = abs(KS.mcnemar_exact(8, 0) - binomtest(8, 8, 0.5, alternative="greater").pvalue) < 1e-12
    out["T5_mcnemar_7_1"] = round(KS.mcnemar_exact(7, 1, "two-sided"), 4)
    # T6 random pool ladder on synthetic norms
    wn = np.abs(rng.normal(1, 0.3, KC.NN))
    top = [5, 40, 1188 * 3 + 32]
    sel = KC.select_random(top, wn, 0)
    out["T6_pool"] = {k: (len(v), sel["matching"][k]["tolerance"]) for k, v in sel["rand_sets"].items()}
    out["T6_pass"] = all(len(v) == 50 for v in sel["rand_sets"].values())
    lab = RESULTS_DIR / "labeller_check.json"
    out["T7_labeller"] = read_json(lab)["summary"] if lab.exists() else None
    out["all_pass"] = bool(out["T1_classes_disjoint_covering"] and out["T2_n_nodes"] == 4752 and out["T2_roundtrip"]
                           and out["T3_pass"] and out["T4_exact_vs_brute"] and out["T4_exact_vs_mc"] and
                           out["T5_holm"] and out["T5_mcnemar"] and out["T6_pass"])
    logger.info(f"CPU tests: {out}")
    return out


def commit0_payload() -> dict[str, Any]:
    return {
        "claim": "K3: components that compute the odds of the decision token, validated in the real model",
        "model": "Qwen/Qwen3-8B@b968826d (bf16, thinking off, sdpa)",
        "node_set": "36 x 32 heads (o_proj input slice) + 36 MLP outputs at COND / SPEC / OPEN / DEC = 4,752 nodes",
        "metrics": {"C1": "m = z(' Kr') - z(' Prim') at DEC (last of B3's 61-token opening)",
                    "C2a": "m = z(' find') - z(' dfs') at DEC (' def', token 10 of the T10 prefix)",
                    "C2b": "m' = z(' find') - logsumexp(z(' dfs'), z(' bfs'))"},
        "pair_rule": "C1-nat: 24 neutral-noun variants per template W1-W5; within template the k-th highest m (clean) "
                     "with the k-th lowest (corrupt): set A k = 1..3, set B k = 4..6; held-out H 2 per template "
                     "(seed 8301, one above and one below the template median); pairs with TE <= 0.2 dropped; < 10 "
                     "surviving pairs or mean TE(A) < 1.0 nat -> F2 (C1-forced primary)",
        "screen": "AtP noising (grad at clean x (corrupt - clean)); top 60 by |mean AtP|; reliability: exact noising of "
                  "40 random nodes per class (seed 8304); Spearman < 0.6 -> IG-AtP (5 alphas) and 120 exact nodes",
        "exact": "noising and denoising of the top 60 + 20 random calibration nodes (seed 8305); ranking by |mean "
                 "noising effect| (Gemma's rule)",
        "edges": "path patching among the top 15; keep |mean| >= 0.05 x mean TE",
        "faithfulness": "k in {5,10,15,30,60}: clean input, non-circuit nodes frozen to corrupt values (type 1) or to "
                        "the corrupt-class same-template mean (type 2), circuit nodes live; completeness (top-k "
                        "noised) and sufficiency (top-k denoised)",
        "random_matching": "heads: +-10/25/50% write norm (>= 50 candidates), 50 without replacement; MLPs: "
                           "+-10/25/50%/nearest-10 (>= 10 distinct), 50 with replacement, delta rescaled to the "
                           "target's write norm; seed 8302",
        "validation": "ABLATE node <- opposite-class mean; STEER node <- own + 2 x (opposite mean - own mean); oriented "
                      "dm vs in-chunk base; d_i = dm_node - mean dm_rand; one-sided sign-flip (exact n <= 25 else "
                      "1e6 MC); PRIMARY Holm over all 20 node x test p; NODE PASS = Holm p < 0.05 in both tests; "
                      "Gemma's within-test Holm reported beside",
        "time_rule": "if the first-prompt timing extrapolates validation of one contrast beyond 45 min, V = 15 clean + "
                     "10 H; beyond that H drops to 5; random count never reduced (C1-nat)",
        "generation": "arms TWIN, TOP5 (STEER toward the minority on all five), RAND5 (frozen matched five, seed 8303); "
                      "N = 30 = W1-W5 x 6 CRN slots; T 1, top-p 1, no top-k, max_new 1024; PRIMARY = PREFILL "
                      "(prompt + opening prefilled for every arm); SECONDARY = FREE (OPEN/DEC edits fire only while "
                      "the generated prefix equals the opening); targets B3 correct prim_heap/prim_array, T10 correct "
                      "dfs",
        "gen_criteria": "TOP5 - TWIN correct-target >= 6; exact McNemar TOP5 vs RAND5 p < 0.05; pass(TOP5) >= 0.8 x "
                        "pass(TWIN)",
        "K3_verdict": "PASS = C1: >= 5 of 10 nodes pass both tests AND PREFILL top-5 meets all three generation "
                      "criteria; PARTIAL = exactly one; DISCONFIRMED = no top-10 node passes either test; C2a "
                      "reported with the same rule; the C1 McNemar p enters the paper's primary Holm family",
        "predictions": {"P1": ">= 5 of 10 nodes pass both tests on C1-nat",
                        "P2": "PREFILL top-5 steering: TWIN + >= 6 correct Prim of 30, beats RAND5 (McNemar p < "
                              "0.05), pass >= 0.8 x twin",
                        "P3": "the same on C2a toward DFS",
                        "P4": "motif: DEC share in [0.38, 0.68], COND share in [0.21, 0.51], DEC-position stack "
                              "effect-weighted depth in [0.45, 0.80]",
                        "P5": "top-10 Jaccard between pair sets A and B >= 0.4"},
        "motif_function": "share(c) = sum over the exact list (top 40 by |AtP| + 20 random calibration nodes, Gemma's "
                          "composition) in class c of |mean noising effect| / total; validated on Gemma's "
                          "g1_pathpatch.json (FORK 0.531, COND 0.357) before any Qwen value",
        "drop_order": ["transcoder extension", "C2b", "pair set B", "held-out beyond 5", "FREE condition rows"],
        "never_drop": ["C1 screen + exact + path patching + matched-random validation + PREFILL top-5 generation",
                       "C2a with validation", "motif test", "novelty audit"],
        "code_sha256": code_hashes(),
    }


# ================================================================================================ contrasts
def build_c1nat(tok: Any, model: Any) -> dict[str, Any]:
    """Teacher-force the opening on 120 variants (batched per template) -> m_v; pairs A/B; held-out."""
    p = RESULTS_DIR / "c1nat_variants.json"
    O = KP.b3_opening()
    met = metrics(tok)["B3"]
    if "b3_variants" not in STATE:
        STATE["b3_variants"] = KP.b3_variants(tok, nouns(tok), 24)
    vs = STATE["b3_variants"]
    if p.exists():
        mv = read_json(p)["m"]
    else:
        mv = {}
        for w in TEMPLATES:
            ws = [v for v in vs if v["template"] == w]
            for b0 in range(0, len(ws), 12):
                part = ws[b0:b0 + 12]
                inp = torch.tensor([v["ids"] + O for v in part], device="cuda")
                with torch.no_grad():
                    o = model.model(input_ids=inp, use_cache=False)
                    mm = met(o.last_hidden_state[:, -1])
                for v, m in zip(part, mm.tolist()):
                    mv[v["vid"]] = m
                del o, mm
        sd = {w: float(np.std([mv[v["vid"]] for v in vs if v["template"] == w])) for w in TEMPLATES}
        write_json(p, {"m": mv, "sd_by_template": sd, "sd_all": float(np.std(list(mv.values()))),
                       "note": "batched teacher-forced m (12 per batch), used only to rank and pair variants"})
    A = KP.pair_by_rank(vs, mv, (1, 2, 3))
    B = KP.pair_by_rank(vs, mv, (4, 5, 6))
    used = {a for ab in A + B for a in ab}
    H = KP.heldout(vs, mv, used)
    byv = {v["vid"]: v for v in vs}
    return {"variants": byv, "m": mv, "A": A, "B": B, "H": H}


def make_c1(tok: Any, model: Any, which: str = "A") -> KC.Contrast:
    info = build_c1nat(tok, model)
    byv = info["variants"]
    prompts, pairs = [], []
    for c, x in info[which]:
        prompts += [dict(byv[c], cls="clean"), dict(byv[x], cls="corrupt")]
        pairs.append((len(prompts) - 2, len(prompts) - 1))
    for vid, side in info["H"]:
        prompts.append(dict(byv[vid], cls=side, heldout=True))
    C = KC.Contrast("C1nat" if which == "A" else "C1natB", metrics(tok)["B3"], prompts, KP.b3_opening(), pairs)
    return C


def forced_list(tok: Any) -> list:
    if "forced" not in STATE:
        STATE["forced"] = KP.b3_forced(tok)
    return STATE["forced"]


def make_c1forced(tok: Any) -> KC.Contrast:
    """Amendment 0a: 10 forced-Prim paraphrases (F1-F10) against their padding twins; F11-F15 and their padding twins
    are the 10 held-out validation prompts."""
    prompts, pairs = [], []
    fl = forced_list(tok)
    for pad, f in fl[:10]:
        prompts += [dict(pad, cls="clean"), dict(f, cls="corrupt")]
        pairs.append((len(prompts) - 2, len(prompts) - 1))
    for pad, f in fl[10:15]:
        prompts += [dict(pad, cls="clean", heldout=True), dict(f, cls="corrupt", heldout=True)]
    return KC.Contrast("C1forced", metrics(tok)["B3"], prompts, KP.b3_opening(), pairs)


def make_c1mix(tok: Any, model: Any) -> KC.Contrast:
    info = build_c1nat(tok, model)
    byv = info["variants"]
    prompts, pairs = [], []
    k12 = [ab for i, ab in enumerate(info["A"]) if i % 3 in (0, 1)]          # k = 1, 2 of each template
    for c, x in k12:
        prompts += [dict(byv[c], cls="clean"), dict(byv[x], cls="corrupt")]
        pairs.append((len(prompts) - 2, len(prompts) - 1))
    for pad, f in forced_list(tok)[:5]:
        prompts += [dict(pad, cls="clean"), dict(f, cls="corrupt")]
        pairs.append((len(prompts) - 2, len(prompts) - 1))
    return KC.Contrast("C1mix", metrics(tok)["B3"], prompts, KP.b3_opening(), pairs)


@torch.no_grad()
def exchange_source(model: Any, tok: Any, blocks: list[int]) -> dict[str, Any]:
    """Block outputs of the forced-DFS prompt (+ T10 prefix) at its task-spec positions [p1, spec_end)."""
    if "xsrc" in STATE and STATE["xsrc"]["blocks"] == blocks:
        return STATE["xsrc"]
    f = KP.t10_forced_dfs(tok)
    ids = f["ids"] + KP.t10_prefix()
    caps: dict[int, torch.Tensor] = {}
    sp = list(range(f["p1"], f["spec_end"]))
    cap = {("resid", l): (lambda x, l=l: caps.__setitem__(l, x[0, sp].detach().clone())) for l in blocks}
    with EN.edit_hooks(model, [], cap):
        model.model(input_ids=torch.tensor([ids], device="cuda"), use_cache=False)
    STATE["xsrc"] = {"blocks": blocks, "states": caps, "forced": f}
    return STATE["xsrc"]


def exchange_edits(rec: dict[str, Any], src: dict[str, Any], alpha: float = 1.0,
                   clean_states: dict[int, torch.Tensor] | None = None) -> list[EN.Edit]:
    sp = list(range(rec["p1"], rec["spec_end"]))
    out = []
    for l in src["blocks"]:
        v = src["states"][l]
        assert v.shape[0] == len(sp), "spec spans differ"
        if alpha != 1.0 and clean_states is not None:
            v = clean_states[l] + alpha * (v - clean_states[l])
        out.append(EN.Edit("resid", l, sp, EN.const_fn(v), name=f"exch_L{l}"))
    return out


def make_c2a(tok: Any, model: Any, blocks: list[int]) -> KC.Contrast:
    ns = [n for n in nouns(tok)]
    t_nouns = ["ship"] + ns[:2]
    h_nouns = ns[2:4]
    if "t10_variants" not in STATE:
        STATE["t10_variants"] = (KP.t10_variants(tok, t_nouns), KP.t10_variants(tok, h_nouns))
    tv, hv = STATE["t10_variants"]
    src = exchange_source(model, tok, blocks)
    prompts, pairs, base = [], [], {}
    for v in tv:
        prompts.append(dict(v, cls="clean"))
        prompts.append(dict(v, cls="corrupt", exchanged=True, vid=v["vid"] + "|exch"))
        i = len(prompts) - 1
        base[i] = (lambda rec=prompts[i]: exchange_edits(rec, src))
        pairs.append((i - 1, i))
    for v in hv:
        prompts.append(dict(v, cls="clean", heldout=True))
    C = KC.Contrast("C2a", metrics(tok)["T10"], prompts, KP.t10_prefix(), pairs, base=base)
    C.exchange_blocks = blocks
    return C


def stage_contrasts() -> None:
    t0 = time.time()
    model, tok = model_tok()
    out: dict[str, Any] = {}
    info = build_c1nat(tok, model)
    out["C1nat_sd_m_v"] = read_json(RESULTS_DIR / "c1nat_variants.json")["sd_all"]
    for which in ("A", "B"):
        C = make_c1(tok, model, which)
        rows = []
        for (c, x) in C.pairs:
            a_c = EN.collect(model, C.run_ids(c), C.metric)
            a_x = EN.collect(model, C.run_ids(x), C.metric)
            rows.append({"clean": C.prompts[c]["vid"], "corrupt": C.prompts[x]["vid"], "m_clean": a_c.m,
                         "m_corrupt": a_x.m, "TE": a_c.m - a_x.m, "p_kr_clean": a_c.p_a, "p_prim_clean": a_c.p_b,
                         "p_kr_corrupt": a_x.p_a, "p_prim_corrupt": a_x.p_b})
            del a_c, a_x
        te = [r["TE"] for r in rows]
        out[f"C1nat_{which}"] = {"pairs": rows, "TE_mean": float(np.mean(te)), "TE_sd": float(np.std(te)),
                                 "n_TE_gt_min": int(sum(t > TE_MIN for t in te))}
        logger.info(f"C1nat {which}: TE mean {np.mean(te):.3f} (sd {np.std(te):.3f}); {sum(t > TE_MIN for t in te)}"
                    f"/15 > {TE_MIN}")
    out["C1nat_heldout"] = info["H"]
    C = make_c1forced(tok)
    rows = []
    for (c, x) in C.pairs:
        a_c = EN.collect(model, C.run_ids(c), C.metric)
        a_x = EN.collect(model, C.run_ids(x), C.metric)
        rows.append({"clean": C.prompts[c]["vid"], "corrupt": C.prompts[x]["vid"], "m_clean": a_c.m,
                     "m_corrupt": a_x.m, "TE": a_c.m - a_x.m, "p_prim_corrupt": a_x.p_b})
    out["C1forced"] = {"pairs": rows, "TE_mean": float(np.mean([r["TE"] for r in rows]))}
    # C2a with the F3 fallback ladder
    chosen = None
    tries = []
    for blocks, tag in ((list(range(36)), "X_0-35"), (list(range(12, 24)), "X_12-23"), ([16], "X_16")):
        C2 = make_c2a(tok, model, blocks)
        rows = []
        for (c, x) in C2.pairs:
            a_c = EN.collect(model, C2.run_ids(c), C2.metric)
            a_x = EN.collect(model, C2.run_ids(x), C2.metric, C2.base(x))
            rows.append({"clean": C2.prompts[c]["vid"], "m_clean": a_c.m, "m_corrupt": a_x.m, "TE": a_c.m - a_x.m,
                         "argmax_corrupt": tok.decode([a_x.top[0][0]]), "argmax_clean": tok.decode([a_c.top[0][0]]),
                         "p_dfs_corrupt": a_x.p_b, "p_find_clean": a_c.p_a})
        te = float(np.mean([r["TE"] for r in rows]))
        flips = float(np.mean([r["argmax_corrupt"] == " dfs" for r in rows]))
        tries.append({"config": tag, "TE_mean": te, "frac_argmax_dfs": flips, "pairs": rows})
        logger.info(f"C2a {tag}: TE mean {te:.2f}, argmax dfs {flips:.2f}")
        C2.clear_base()
        if flips >= 0.5 and te >= 5.0:
            chosen = tag
            break
    out["C2a_tries"] = tries
    out["C2a_config"] = chosen
    if chosen is None:
        log_deviation("F3_C2c", "no exchange configuration flipped the T10 argmax to ' dfs' with a >= 5 nat shift; "
                      "C2a falls back to the input contrast C2c is NOT built in this run (see C2a_tries)", "major")
    elif chosen != "X_0-35":
        log_deviation("F3_exchange_band", f"C2a uses exchange configuration {chosen} (X_0-35 failed the check)")
    write_json(RESULTS_DIR / "contrasts.json", out)
    stage_time("contrasts", time.time() - t0)


def c2a_blocks() -> list[int]:
    cfg = read_json(RESULTS_DIR / "contrasts.json")["C2a_config"] or "X_0-35"
    return {"X_0-35": list(range(36)), "X_12-23": list(range(12, 24)), "X_16": [16]}[cfg]


def get_contrast(name: str) -> KC.Contrast:
    model, tok = model_tok()
    if name == "C1nat":
        return make_c1(tok, model, "A")
    if name == "C1natB":
        return make_c1(tok, model, "B")
    if name == "C1forced":
        return make_c1forced(tok)
    if name == "C1mix":
        return make_c1mix(tok, model)
    if name == "C2a":
        return make_c2a(tok, model, c2a_blocks())
    raise ValueError(name)


def surviving_pairs(C: KC.Contrast, acts: dict[int, EN.Acts]) -> list[tuple[int, int]]:
    keep = []
    for c, x in C.pairs:
        te = acts[c].m - acts[x].m
        if te > TE_MIN:
            keep.append((c, x))
        else:
            log_deviation(f"{C.name}_pair_dropped_{C.prompts[c]['vid']}",
                          f"{C.name}: pair {C.prompts[c]['vid']} vs {C.prompts[x]['vid']} has TE {te:.3f} <= {TE_MIN}")
    return keep


# ================================================================================================ amendment 0a
def stage_amend0a() -> None:
    c = read_json(RESULTS_DIR / "contrasts.json")
    g = read_json(RESULTS_DIR / "gpu_tests.json")
    te_a = c["C1nat_A"]["TE_mean"]
    f2 = te_a < 1.0 or c["C1nat_A"]["n_TE_gt_min"] < 10
    u3, u3b = g["U3"], g.get("U3b_full_vs_full", {})
    use_suffix = u3["mean_abs_diff"] <= max(0.05, 1.5 * u3b.get("mean_abs_diff", 0.0) + 0.02)
    payload = {
        "F2_triggered": f2, "C1nat_A_TE_mean": te_a, "C1nat_A_n_TE_gt_0.2": c["C1nat_A"]["n_TE_gt_min"],
        "C1_primary": "C1forced" if f2 else "C1nat",
        "C1forced_design": "10 forced-Prim paraphrases F1-F10 (corrupt) vs their ' .' padding twins (clean) as pairs; "
                           "F11-F15 and their padding twins as the 10 held-out validation prompts (no Prim paraphrase "
                           "set exists in art_MZAfDPVhM6Ui beyond its single wording, so the 15 wordings are written "
                           "here); C1-nat is still screened and reported descriptively; C1mix uses F1-F5",
        "C1forced_TE": [r["TE"] for r in c["C1forced"]["pairs"]],
        "metric_readout": "m read in fp32 from the bf16 final-norm hidden state (h . (W_a - W_b)); the bf16 lm_head "
                          "output is quantised to 0.125-0.25 nats",
        "F5_decision": {"suffix_vs_full": u3, "full_vs_full_batch_shapes": u3b, "keep_suffix_forwards": use_suffix,
                        "rule": "suffix forwards are kept when their mean deviation from full recompute is no larger "
                                "than 1.5 x the full-vs-full batch-shape noise + 0.02 nats (both are bf16 path noise "
                                "and cancel within each in-chunk base-row comparison); otherwise every row is a full "
                                "forward"},
        "generation_alignment_rule": "TOP5 for generation = the five highest-ranked top-10 nodes whose position class "
                                     "aligns with the B3 twin prompt; COND nodes of C1forced (the forced instruction "
                                     "span) have no counterpart in the twin's condition sentence and are skipped (the "
                                     "next-ranked node fills in); RAND5 = one matched draw per generation node "
                                     "(seed 8303)",
        "code_sha256": code_hashes()}
    commit("amend0a", payload)
    if not use_suffix:
        log_deviation("F5_full_forwards", "every patching row runs as a full forward (F5)", "major")


# ================================================================================================ GPU tests
def stage_gputests() -> None:
    t0 = time.time()
    model, tok = model_tok()
    out: dict[str, Any] = {}
    met = metrics(tok)
    # U9 memory: forward at batch 1/8/16 and forward+backward at batch 1
    tw = KP.b3_twins(tok)["W5"]
    ids = tw["ids"] + KP.b3_opening()
    mem = {}
    for B in (1, 8, 16):
        torch.cuda.reset_peak_memory_stats()
        with torch.no_grad():
            o = model.model(input_ids=torch.tensor([ids] * B, device="cuda"), use_cache=False)
        del o
        mem[f"fwd_b{B}_GB"] = round(torch.cuda.max_memory_allocated() / 1e9, 3)
    torch.cuda.reset_peak_memory_stats()
    gz, gm, m = EN.atp_grads(model, ids, met["B3"])
    mem["fwd_bwd_b1_GB"] = round(torch.cuda.max_memory_allocated() / 1e9, 3)
    del gz, gm
    EN.free_cuda()
    out["U9_memory"] = mem
    write_json(RESULTS_DIR / "memory_probe.json", mem)
    # U1 pi(' Kr') on the W1 twin
    a = EN.collect(model, KP.b3_twins(tok)["W1"]["ids"] + KP.b3_opening(), met["B3"])
    out["U1"] = {"p_kr": a.p_a, "p_prim": a.p_b, "m": a.m, "reference_p_kr": 0.72, "pass": abs(a.p_a - 0.72) <= 0.05,
                 "top5": [(tok.decode([i]), p) for i, p in a.top]}
    # U2 patch-all smoke on the first C1-nat pair
    C = get_contrast("C1nat")
    c, x = C.pairs[0]
    ac = EN.collect(model, C.run_ids(c), C.metric)
    ax = EN.collect(model, C.run_ids(x), C.metric)
    n = len(C.run_ids(c))
    allp = list(range(n))
    diff = [i for i in range(n) if C.run_ids(c)[i] != C.run_ids(x)[i]]
    eds = [EN.Edit("emb", 0, diff, EN.const_fn(ax.emb[diff]), name="emb")]
    for l in range(N_LAYERS):
        eds.append(EN.Edit("z", l, allp, EN.const_fn(ax.z[l]), head=None, name=f"z{l}"))
        eds.append(EN.Edit("mlp", l, allp, EN.const_fn(ax.mlp[l]), name=f"m{l}"))
    dm_all = EN.margins_rows(model, C.run_ids(c), C.metric, [eds, []])
    out["U2"] = {"m_clean": ac.m, "m_corrupt": ax.m, "dm_patch_all": dm_all[0], "dm_patch_none": dm_all[1],
                 "target_dm": ax.m - ac.m, "pass": abs(dm_all[0] - (ax.m - ac.m)) < 0.05 and abs(dm_all[1]) < 1e-6}
    # U3 suffix forward with reused prefix KV vs full recompute (20 edited rows across classes)
    rng = np.random.default_rng(0)
    pos = C.prompts[c]["pos"]
    sel = []
    for cl in CLASSES:
        cand = [j for j, nd in enumerate(KC.NODES) if nd[3] == cl]
        sel += [int(j) for j in rng.choice(cand, 5, replace=False)]
    errs = []
    for j in sel:
        nd = KC.NODES[j]
        ps = pos[nd[3]]
        e = KC.make_edit(nd, ps, EN.const_fn(KC.node_vals(ax, nd, ps)))
        a1 = EN.margins_rows(model, C.run_ids(c), C.metric, [[e]], q_min=min(ps))[0]
        a2 = EN.margins_rows(model, C.run_ids(c), C.metric, [[e]], q_min=0)[0]
        errs.append(abs(a1 - a2))
    out["U3"] = {"max_abs_diff": float(max(errs)), "mean_abs_diff": float(np.mean(errs)),
                 "pass": float(max(errs)) <= 0.05}
    # U3b: the bf16 noise floor -- the same 20 edited rows as full forwards in two batch shapes (chunk of 20 rows vs
    # one row per chunk), and suffix forwards in two batch shapes
    eds20 = []
    for j in sel:
        nd = KC.NODES[j]
        ps = pos[nd[3]]
        eds20.append([KC.make_edit(nd, ps, EN.const_fn(KC.node_vals(ax, nd, ps)))])
    f_big = EN.margins_rows(model, C.run_ids(c), C.metric, eds20, q_min=0, max_rows=21)
    f_one = [EN.margins_rows(model, C.run_ids(c), C.metric, [e], q_min=0)[0] for e in eds20]
    out["U3b_full_vs_full"] = {"max_abs_diff": float(np.max(np.abs(np.array(f_big) - np.array(f_one)))),
                               "mean_abs_diff": float(np.mean(np.abs(np.array(f_big) - np.array(f_one))))}
    out["U3_vs_noise_floor"] = ("suffix-vs-full differences are compared with full-vs-full differences across batch "
                                "shapes; if they are of the same size the suffix forward adds no error beyond bf16")
    if not out["U3"]["pass"]:
        log_deviation("F5_prefix_cache", f"U3 suffix vs full max diff {max(errs):.3f} > 0.05 (mean "
                      f"{np.mean(errs):.3f}); full-vs-full across batch shapes: max "
                      f"{out['U3b_full_vs_full']['max_abs_diff']:.3f}, mean {out['U3b_full_vs_full']['mean_abs_diff']:.3f}"
                      "; see results/gpu_tests.json for the decision", "major")
    # U4 AtP linearity on 5 nodes (0.1 x delta)
    gz, gm, _ = EN.atp_grads(model, C.run_ids(c), C.metric)
    atp = -KC.atp_vector(gz, gm, ax, ac, pos)
    del gz, gm
    lin = []
    for j in sel[::4]:
        nd = KC.NODES[j]
        ps = pos[nd[3]]
        delta = 0.1 * (KC.node_vals(ax, nd, ps).float() - KC.node_vals(ac, nd, ps).float())
        e = KC.make_edit(nd, ps, EN.steer_fn(delta))
        dm = EN.margins_rows(model, C.run_ids(c), C.metric, [[e]], q_min=min(ps))[0]
        lin.append({"node": KC.node_key(nd), "fd_effect": -dm, "atp_0.1": 0.1 * atp[j]})
    out["U4"] = lin
    # U6 steering hook adds exactly the delta at the positions and nothing elsewhere
    nd = ("head", 20, 3, "OPEN")
    ps = pos["OPEN"]
    delta = torch.randn(len(ps), 128) * 0.5
    seen = {}
    e = KC.make_edit(nd, ps, EN.steer_fn(delta))
    with torch.no_grad(), EN.edit_hooks(model, EN.all_rows(1, [e]),
                                        {("z", 20): lambda x: seen.__setitem__("x", x[0].float().cpu())}):
        model.model(input_ids=torch.tensor([C.run_ids(c)], device="cuda"), use_cache=False)
    got = seen["x"]
    base = ac.z[20].float()
    d_at = got[ps, :384] - base[ps, :384]
    d_head = got[ps, 384:512] - base[ps, 384:512]
    others = [p for p in range(n) if p not in ps]
    out["U6"] = {"max_err_delta": float((d_head - delta).abs().max()),
                 "max_change_other_positions": float((got[others, 384:512] - base[others, 384:512]).abs().max()),
                 "max_change_other_heads": float(d_at.abs().max())}
    out["U6"]["pass"] = out["U6"]["max_err_delta"] < 0.05 and out["U6"]["max_change_other_positions"] < 1e-6
    # U8 exchange identity: exchanging the twin's own states leaves m unchanged
    tw10 = KP.t10_twins(tok)["W1"]
    ids10 = tw10["ids"] + KP.t10_prefix()
    caps = {}
    sp = list(range(tw10["p1"], tw10["spec_end"]))
    with torch.no_grad(), EN.edit_hooks(model, [], {("resid", l): (lambda x, l=l: caps.__setitem__(l, x[0, sp].clone()))
                                                    for l in range(36)}):
        model.model(input_ids=torch.tensor([ids10], device="cuda"), use_cache=False)
    own = [EN.Edit("resid", l, sp, EN.const_fn(caps[l]), name=f"own{l}") for l in range(36)]
    m_own = EN.margins_rows(model, ids10, met["T10"], [own])[0]
    out["U8"] = {"dm_own_exchange": m_own, "pass": abs(m_own) < 0.05}
    out["all_blocking_pass"] = bool(out["U2"]["pass"] and out["U3"]["pass"] and out["U6"]["pass"] and out["U8"]["pass"])
    write_json(RESULTS_DIR / "gpu_tests.json", out)
    logger.info(f"GPU tests: U1 {out['U1']['pass']} U2 {out['U2']['pass']} U3 {out['U3']} U6 {out['U6']['pass']} "
                f"U8 {out['U8']['pass']}")
    stage_time("gputests", time.time() - t0)


# ================================================================================================ circuit
def stage_circuit(name: str, edges: bool = True, faith: bool = True, rel: bool = True) -> None:
    t0 = time.time()
    model, tok = model_tok()
    C = get_contrast(name)
    idx = sorted({i for ab in C.pairs for i in ab})
    acts = KC.collect_all(model, C, idx)
    pairs = surviving_pairs(C, acts)
    te = np.array([acts[c].m - acts[x].m for c, x in pairs])
    logger.info(f"[{name}] {len(pairs)} pairs, TE mean {te.mean():.3f}; collected in {time.time() - t0:.0f}s")
    res: dict[str, Any] = {"contrast": name, "n_pairs": len(pairs),
                           "pairs": [{"clean": C.prompts[c]["vid"], "corrupt": C.prompts[x]["vid"],
                                      "m_clean": acts[c].m, "m_corrupt": acts[x].m, "TE": acts[c].m - acts[x].m}
                                     for c, x in pairs],
                           "TE_mean": float(te.mean()), "TE_sd": float(te.std())}
    # ---------------- screen
    t1 = time.time()
    atp, atp_den = KC.atp_screen(model, C, acts, pairs)
    res["seconds_screen"] = time.time() - t1
    np.savez_compressed(CACHE_DIR / f"atp_{name}.npz", atp=atp, atp_den=atp_den)
    atp_mean = atp.mean(0)
    order = np.argsort(-np.abs(atp_mean))
    logger.info(f"[{name}] AtP done ({time.time() - t1:.0f}s); top {[KC.node_key(KC.NODES[j]) for j in order[:8]]}")
    # ---------------- reliability: exact noising on 40 random nodes per class
    rng = np.random.default_rng(SEED_REL)
    rel_nodes = []
    if rel:
        for cl in CLASSES:
            cand = [j for j, nd in enumerate(KC.NODES) if nd[3] == cl]
            rel_nodes += [int(j) for j in rng.choice(cand, N_REL_PER_CLASS, replace=False)]
        t1 = time.time()
        rel_noise = KC.exact_effects(model, C, acts, pairs, rel_nodes, "noise")
        res["seconds_reliability"] = time.time() - t1
        rel_stats = KS.spearman_pearson(atp[:, rel_nodes], rel_noise)
        res["atp_vs_exact_random160"] = rel_stats
        logger.info(f"[{name}] AtP vs exact (160 random nodes): {rel_stats}")
    else:
        rel_noise = np.zeros((len(pairs), 0))
    screen = "AtP"
    n_top = N_TOP_EXACT
    if rel and res["atp_vs_exact_random160"]["spearman"] < 0.6:
        log_deviation(f"F4_{name}", f"{name}: AtP-vs-exact Spearman {res['atp_vs_exact_random160']['spearman']:.2f} "
                      "< 0.6 -> IG-AtP (5 alphas, input interpolation) and 120 exact nodes; the S19 correction was "
                      "not implemented within the 30-minute timebox")
        t1 = time.time()
        atp_ig = KC.ig_atp_screen(model, C, acts, pairs, interp_fn(C, acts))
        np.savez_compressed(CACHE_DIR / f"atpig_{name}.npz", atp_ig=atp_ig)
        res["ig_vs_exact_random160"] = KS.spearman_pearson(atp_ig[:, rel_nodes], rel_noise)
        res["seconds_ig"] = time.time() - t1
        logger.info(f"[{name}] IG-AtP vs exact: {res['ig_vs_exact_random160']}")
        if res["ig_vs_exact_random160"]["spearman"] > res["atp_vs_exact_random160"]["spearman"]:
            atp = atp_ig
            atp_mean = atp.mean(0)
            order = np.argsort(-np.abs(atp_mean))
            screen = "IG-AtP"
        n_top = 120
    res["screen"] = screen
    top_atp = [int(j) for j in order[:n_top]]
    rest = [int(j) for j in order[n_top:]]
    cal = [int(j) for j in np.random.default_rng(SEED_CAL).choice(rest, N_CAL, replace=False)]
    exact_set = top_atp + cal
    # ---------------- exact noising and denoising
    t1 = time.time()
    noise = KC.exact_effects(model, C, acts, pairs, exact_set, "noise")
    denoise = KC.exact_effects(model, C, acts, pairs, exact_set, "denoise")
    res["seconds_exact"] = time.time() - t1
    np.savez_compressed(CACHE_DIR / f"exact_{name}.npz", noise=noise, denoise=denoise, exact_set=np.array(exact_set),
                        rel_noise=rel_noise, rel_nodes=np.array(rel_nodes))
    res["atp_vs_exact_top"] = KS.spearman_pearson(atp[:, exact_set], noise)
    # rank by |mean noising effect| over every exact-noised node (top + calibration + reliability)
    pool = {j: noise[:, jj] for jj, j in enumerate(exact_set)}
    for jj, j in enumerate(rel_nodes):
        pool.setdefault(j, rel_noise[:, jj])
    keys = list(pool)
    eff = np.array([pool[j].mean() for j in keys])
    rank = [keys[i] for i in np.argsort(-np.abs(eff))]
    exact_rows = []
    for jj, j in enumerate(exact_set):
        v = noise[:, jj]
        exact_rows.append({"node": KC.node_key(KC.NODES[j]), "in_top_atp": jj < n_top, "in_top40_atp": jj < 40,
                           "calibration": jj >= n_top, "atp_mean": float(atp_mean[j]),
                           "atp_den_mean": float(atp_den.mean(0)[j]), "noise_mean": float(v.mean()),
                           "noise_sd": float(v.std()), "denoise_mean": float(denoise[:, jj].mean()),
                           "denoise_sd": float(denoise[:, jj].std()),
                           "noise_sign_consistency": float(np.mean(np.sign(v) == np.sign(v.mean()))),
                           "noise_per_pair": v.tolist(), "denoise_per_pair": denoise[:, jj].tolist()})
    exact_rows.sort(key=lambda r: -abs(r["noise_mean"]))
    res["exact"] = exact_rows
    res["reliability_rows"] = [{"node": KC.node_key(KC.NODES[j]), "atp_mean": float(atp[:, j].mean()),
                                "noise_mean": float(rel_noise[:, jj].mean()), "noise_per_pair": rel_noise[:, jj].tolist(),
                                "atp_per_pair": atp[:, j].tolist()} for jj, j in enumerate(rel_nodes)]
    res["top15"] = [KC.node_key(KC.NODES[j]) for j in rank[:15]]
    res["top10"] = res["top15"][:10]
    res["top5"] = res["top15"][:5]
    res["top60_exact"] = [KC.node_key(KC.NODES[j]) for j in rank[:60]]
    res["atp_class_mass"] = {cl: float(np.abs(atp_mean[[j for j, n in enumerate(KC.NODES) if n[3] == cl]]).sum())
                             for cl in CLASSES}
    res["atp_top60"] = [{"node": KC.node_key(KC.NODES[j]), "atp_mean": float(atp_mean[j])} for j in top_atp[:60]]
    logger.info(f"[{name}] exact done ({time.time() - t1:.0f}s); top10 {res['top10']}")
    write_json(RESULTS_DIR / f"circuit_{name}.json", res)
    # ---------------- edges among the top 15
    if edges:
        t1 = time.time()
        top15 = rank[:N_EDGE]
        e_all = KC.edge_patching(model, C, acts, pairs, top15)
        thr = 0.05 * float(te.mean())
        res["edges_all"] = e_all
        res["edges_kept"] = [e for e in e_all if abs(e["effect_mean"]) >= thr]
        res["edge_threshold"] = thr
        res["seconds_edges"] = time.time() - t1
        heads = [(KC.NODES[j][1], KC.NODES[j][2]) for j in top15 if KC.NODES[j][0] == "head"]
        if heads:
            c0, x0 = pairs[0]
            q = len(C.run_ids(c0)) - 1
            res["attention_top_heads"] = {"clean": KC.head_attention(model, tok, C, c0, heads, q),
                                          "corrupt": KC.head_attention(model, tok, C, x0, heads, q),
                                          "pair": [C.prompts[c0]["vid"], C.prompts[x0]["vid"]], "query_pos": q}
        logger.info(f"[{name}] edges done ({time.time() - t1:.0f}s); kept {len(res['edges_kept'])} (thr {thr:.3f})")
        write_json(RESULTS_DIR / f"circuit_{name}.json", res)
    # ---------------- faithfulness
    if faith:
        t1 = time.time()
        res["faithfulness"] = faithfulness(model, C, acts, pairs, rank)
        res["seconds_faith"] = time.time() - t1
        write_json(RESULTS_DIR / f"circuit_{name}.json", res)
    res["seconds"] = time.time() - t0
    write_json(RESULTS_DIR / f"circuit_{name}.json", res)
    C.clear_base()
    del acts
    gc.collect()
    EN.free_cuda()
    stage_time(f"circuit:{name}", time.time() - t0)


def stage_f4b(name: str) -> None:
    """F4 second clause (AtP and IG-AtP Spearman < 0.4 on the random nodes): rank by exact noising over ALL DEC-class
    nodes (cheap 1-token suffixes) plus the screen's top 120 of the other classes; every MLP node (all four classes)
    is also exact-noised because first-order AtP is least reliable for early MLPs (Gemma's largest node was the
    layer-0 COND MLP). Top-15/10/5 are re-ranked over every exact-noised node; edges and faithfulness are recomputed
    for the new ranking. The screen-only ranking is kept as top10_screen_only; the Gemma-composition exact list
    used by the primary motif is unchanged."""
    t0 = time.time()
    model, tok = model_tok()
    C = get_contrast(name)
    res = read_json(RESULTS_DIR / f"circuit_{name}.json")
    z = np.load(CACHE_DIR / f"exact_{name}.npz")
    za = np.load(CACHE_DIR / f"atp_{name}.npz")
    atp_mean = za["atp"].mean(0)
    exact_set = [int(j) for j in z["exact_set"]]
    rel_nodes = [int(j) for j in z["rel_nodes"]]
    noise, denoise, rel_noise = z["noise"], z["denoise"], z["rel_noise"]
    idx = sorted({i for ab in C.pairs for i in ab})
    acts = KC.collect_all(model, C, idx)
    pairs = surviving_pairs(C, acts)
    te = np.array([acts[c].m - acts[x].m for c, x in pairs])
    measured = set(exact_set) | set(rel_nodes)
    extra = [j for j, nd in enumerate(KC.NODES) if (nd[3] == "DEC" or nd[0] == "mlp") and j not in measured]
    t1 = time.time()
    ex_noise = KC.exact_effects(model, C, acts, pairs, extra, "noise")
    logger.info(f"[{name}] F4b: {len(extra)} extra nodes exact-noised in {time.time() - t1:.0f}s")
    pool = {j: noise[:, jj] for jj, j in enumerate(exact_set)}
    for jj, j in enumerate(rel_nodes):
        pool.setdefault(j, rel_noise[:, jj])
    for jj, j in enumerate(extra):
        pool[j] = ex_noise[:, jj]
    keys = list(pool)
    eff = np.array([pool[j].mean() for j in keys])
    rank = [keys[i] for i in np.argsort(-np.abs(eff))]
    den = {j: denoise[:, jj] for jj, j in enumerate(exact_set)}
    need = [j for j in rank[:60] if j not in den]
    if need:
        dn = KC.exact_effects(model, C, acts, pairs, need, "denoise")
        for jj, j in enumerate(need):
            den[j] = dn[:, jj]
    np.savez_compressed(CACHE_DIR / f"f4b_{name}.npz", extra=np.array(extra), ex_noise=ex_noise,
                        need=np.array(need), den_need=np.stack([den[j] for j in need], 1) if need else np.zeros(0))
    res["top10_screen_only"] = res["top10"]
    res["top15_screen_only"] = res["top15"]
    ext_rows = []
    for jj, j in enumerate(extra):
        v = ex_noise[:, jj]
        row = {"node": KC.node_key(KC.NODES[j]), "atp_mean": float(atp_mean[j]), "noise_mean": float(v.mean()),
               "noise_sd": float(v.std()), "noise_sign_consistency": float(np.mean(np.sign(v) == np.sign(v.mean()))),
               "noise_per_pair": v.tolist(), "source": "F4b sweep (all DEC nodes + all MLPs)"}
        if j in den:
            row["denoise_mean"] = float(den[j].mean())
            row["denoise_per_pair"] = den[j].tolist()
        ext_rows.append(row)
    res["exact_extended"] = sorted(ext_rows, key=lambda r: -abs(r["noise_mean"]))
    res["n_exact_noised_total"] = len(pool)
    res["top15"] = [KC.node_key(KC.NODES[j]) for j in rank[:15]]
    res["top10"] = res["top15"][:10]
    res["top5"] = res["top15"][:5]
    res["top60_exact"] = [KC.node_key(KC.NODES[j]) for j in rank[:60]]
    res["ranking_rule"] = ("F4 second clause: |mean exact noising effect| over every exact-noised node (screen top "
                           "120 + 20 calibration + 160 reliability + all DEC nodes + all MLP nodes)")
    res["atp_vs_exact_extended"] = KS.spearman_pearson(za["atp"][:, extra], ex_noise)
    logger.info(f"[{name}] F4b re-ranked top10 {res['top10']} (screen-only {res['top10_screen_only']})")
    write_json(RESULTS_DIR / f"circuit_{name}.json", res)
    if res["top15"] != res["top15_screen_only"] or "edges_all" not in res:
        t1 = time.time()
        top15 = rank[:N_EDGE]
        e_all = KC.edge_patching(model, C, acts, pairs, top15)
        thr = 0.05 * float(te.mean())
        res["edges_all_screen_only"] = res.get("edges_all")
        res["edges_kept_screen_only"] = res.get("edges_kept")
        res["edges_all"] = e_all
        res["edges_kept"] = [e for e in e_all if abs(e["effect_mean"]) >= thr]
        res["edge_threshold"] = thr
        heads = [(KC.NODES[j][1], KC.NODES[j][2]) for j in top15 if KC.NODES[j][0] == "head"]
        if heads:
            c0, x0 = pairs[0]
            q = len(C.run_ids(c0)) - 1
            res["attention_top_heads"] = {"clean": KC.head_attention(model, tok, C, c0, heads, q),
                                          "corrupt": KC.head_attention(model, tok, C, x0, heads, q),
                                          "pair": [C.prompts[c0]["vid"], C.prompts[x0]["vid"]], "query_pos": q}
        logger.info(f"[{name}] F4b edges ({time.time() - t1:.0f}s); kept {len(res['edges_kept'])}")
        res["faithfulness_screen_only"] = res.get("faithfulness")
        res["faithfulness"] = faithfulness(model, C, acts, pairs, rank)
        write_json(RESULTS_DIR / f"circuit_{name}.json", res)
    C.clear_base()
    del acts
    EN.free_cuda()
    stage_time(f"f4b:{name}", time.time() - t0)


def interp_fn(C: KC.Contrast, acts: dict[int, EN.Acts]):
    """Input interpolation for IG-AtP: the embedding at the positions where clean and corrupt ids differ (input
    contrasts) or the exchanged states (C2a)."""
    model, tok = model_tok()

    def f(c: int, x: int, a: float) -> list[EN.Edit]:
        if C.name == "C2a":
            rec = C.prompts[c]
            sp = list(range(rec["p1"], rec["spec_end"]))
            caps = {}
            with torch.no_grad(), EN.edit_hooks(model, [], {("resid", l): (lambda t, l=l: caps.__setitem__(
                    l, t[0, sp].clone())) for l in C.exchange_blocks}):
                model.model(input_ids=torch.tensor([C.run_ids(c)], device="cuda"), use_cache=False)
            return exchange_edits(rec, exchange_source(model, tok, C.exchange_blocks), alpha=a, clean_states=caps)
        ic, ix = C.run_ids(c), C.run_ids(x)
        diff = [i for i in range(len(ic)) if ic[i] != ix[i]]
        v = acts[c].emb[diff].float() + a * (acts[x].emb[diff].float() - acts[c].emb[diff].float())
        return [EN.Edit("emb", 0, diff, EN.const_fn(v), name="emb_interp")]
    return f


def faithfulness(model: Any, C: KC.Contrast, acts: dict[int, EN.Acts], pairs: list[tuple[int, int]],
                 rank: list[int]) -> dict[str, Any]:
    """Per pair and k: type 1 (non-circuit nodes frozen to the paired corrupt run, circuit live, clean input), type 2
    (frozen to the corrupt-class same-template mean), completeness c(k) (top-k noised in the clean run) and
    sufficiency s(k) (top-k denoised in the corrupt run). f = (m_k - m_0) / (m_full - m_0) within one batch."""
    out: dict[str, Any] = {"k": list(KS_FAITH), "type1": [], "type2": [], "completeness": [], "sufficiency": []}
    frozen_ok = C.name != "C2a"
    corrupt_by_t: dict[str, list[int]] = {}
    for c, x in pairs:
        corrupt_by_t.setdefault(C.prompts[x]["template"], []).append(x)
    for c, x in pairs:
        ids = C.run_ids(c)
        pos = C.prompts[c]["pos"]
        te = acts[c].m - acts[x].m
        if frozen_ok:
            sets = [None, []] + [rank[:k] for k in KS_FAITH]
            for typ in ("type1", "type2"):
                if typ == "type1":
                    Zs, Ms = acts[x].z.cuda(), acts[x].mlp.cuda()
                else:
                    grp = corrupt_by_t[C.prompts[x]["template"]]
                    if len(grp) < 2:
                        out[typ].append(None)
                        continue
                    Zs = torch.stack([acts[i].z.float() for i in grp]).mean(0).to(torch.bfloat16).cuda()
                    Ms = torch.stack([acts[i].mlp.float() for i in grp]).mean(0).to(torch.bfloat16).cuda()
                ms = KC.frozen_rows(model, ids, C.metric, Zs, Ms, sets, pos)
                m_full, m0 = ms[0], ms[1]
                den = m_full - m0
                out[typ].append([(mk - m0) / den if abs(den) > 1e-6 else None for mk in ms[2:]])
                del Zs, Ms
                EN.free_cuda()
        rows = []
        for k in KS_FAITH:
            eds = []
            for j in rank[:k]:
                nd = KC.NODES[j]
                ps = pos[nd[3]]
                eds.append(KC.make_edit(nd, ps, EN.const_fn(KC.node_vals(acts[x], nd, ps))))
            rows.append(eds)
        dms = EN.margins_rows(model, ids, C.metric, rows, q_min=0, base_edits=C.base(c))
        out["completeness"].append([-d / te for d in dms])
        rows = []
        for k in KS_FAITH:
            eds = []
            for j in rank[:k]:
                nd = KC.NODES[j]
                ps = pos[nd[3]]
                eds.append(KC.make_edit(nd, ps, EN.const_fn(KC.node_vals(acts[c], nd, ps))))
            rows.append(eds)
        dms = EN.margins_rows(model, C.run_ids(x), C.metric, rows, q_min=0, base_edits=C.base(x))
        out["sufficiency"].append([d / te for d in dms])
    for key in ("type1", "type2", "completeness", "sufficiency"):
        vals = [v for v in out[key] if v is not None]
        if vals:
            arr = np.array([[np.nan if a is None else a for a in v] for v in vals], dtype=float)
            out[f"{key}_mean"] = np.nanmean(arr, 0).tolist()
            out[f"{key}_sd"] = np.nanstd(arr, 0).tolist()
            ks = np.array(KS_FAITH, dtype=float)
            out[f"{key}_auc_logk"] = float(np.trapezoid(np.nanmean(arr, 0), np.log(ks)) / np.log(ks[-1] / ks[0]))
    if not frozen_ok:
        out["note"] = ("C2a's corrupt run is an intervention on the residual stream, so it cannot be reproduced by "
                       "freezing node values; only completeness and sufficiency (live) are reported")
    return out


# ================================================================================================ commit 1
def selection_for(name: str, model: Any, C: KC.Contrast, acts: dict[int, EN.Acts], pairs: list[tuple[int, int]],
                  top10_keys: list[str]) -> dict[str, Any]:
    wn = KC.write_norms(model, acts, pairs, {i: C.prompts[i]["pos"] for i in acts})
    top10 = [KC.KEY2IDX[k] for k in top10_keys]
    sel = KC.select_random(top10, wn, SEED_POOL)
    rng = np.random.default_rng(SEED_RAND5)
    gen5 = [k for k in top10_keys if not (name == "C1forced" and k.endswith("|COND"))][:5]
    r5_idx = [int(rng.integers(N_RAND)) for _ in range(len(gen5))]
    rand5 = [sel["rand_sets"][gen5[i]][r5_idx[i]] for i in range(len(gen5))]
    rand5_f = [sel["factors"][gen5[i]][r5_idx[i]] for i in range(len(gen5))]
    np.save(CACHE_DIR / f"write_norms_{name}.npy", wn)
    return {"top10": top10_keys, "top5": top10_keys[:5], "gen_top5": gen5, "rand_sets": sel["rand_sets"],
            "factors": sel["factors"],
            "matching": sel["matching"], "rand5": rand5, "rand5_factors": rand5_f, "rand5_draw_index": r5_idx,
            "write_norms_top10": {k: float(wn[KC.KEY2IDX[k]]) for k in top10_keys},
            "write_norms_sha256": sha256_file(CACHE_DIR / f"write_norms_{name}.npy")}


def class_mean_vectors(name: str, C: KC.Contrast, acts: dict[int, EN.Acts], pairs: list[tuple[int, int]],
                       keys: list[str], save_keys: set[str]) -> dict[str, str]:
    """Freeze class means at aligned positions for the top-10, RAND5 and every random draw node (sha256 per file)."""
    clean = [c for c, _ in pairs]
    corrupt = [x for _, x in pairs]
    mc = KC.MeanCache(acts, C.prompts)
    d = CACHE_DIR / "vectors"
    d.mkdir(exist_ok=True)
    hashes = {}
    refs = {}
    for c, _ in pairs:
        refs.setdefault(C.prompts[c]["template"], C.prompts[c])
    for k in keys:
        nd = KC.parse_key(k)
        tens = {}
        for t, ref in refs.items():
            if nd[3] != "COND" and t != sorted(refs)[0]:
                continue
            for cls_name, idx in (("clean", clean), ("corrupt", corrupt)):
                v = mc.get(idx, nd, ref)
                if v is not None:
                    tens[f"{cls_name}|{t if nd[3] == 'COND' else 'ALL'}"] = v.cpu()
        import io
        buf = io.BytesIO()
        torch.save(tens, buf)
        hashes[k] = __import__("hashlib").sha256(buf.getvalue()).hexdigest()
        if k in save_keys:
            (d / f"{name}__{k.replace('|', '_')}.pt").write_bytes(buf.getvalue())
    return hashes


def stage_commit1(names: list[str], cname: str = "commit1") -> None:
    t0 = time.time()
    model, tok = model_tok()
    payload: dict[str, Any] = {}
    for name in names:
        p = RESULTS_DIR / f"circuit_{name}.json"
        if not p.exists():
            continue
        res = read_json(p)
        C = get_contrast(name)
        idx = sorted({i for ab in C.pairs for i in ab})
        acts = KC.collect_all(model, C, idx)
        pairs = surviving_pairs(C, acts)
        sel = selection_for(name, model, C, acts, pairs, res["top10"])
        keys = set(sel["top10"]) | set(sel["rand5"])
        for v in sel["rand_sets"].values():
            keys |= set(v)
        sel["class_mean_sha256"] = class_mean_vectors(name, C, acts, pairs, sorted(keys),
                                                      set(sel["top10"]) | set(sel["rand5"]))
        write_json(RESULTS_DIR / f"selection_{name}.json", sel)
        payload[name] = {"top10": sel["top10"], "top5": sel["top5"], "gen_top5": sel["gen_top5"], "rand5": sel["rand5"],
                         "rand5_factors": sel["rand5_factors"], "matching": sel["matching"],
                         "selection_sha256": sha256_file(RESULTS_DIR / f"selection_{name}.json"),
                         "class_mean_files_sha256": sha256_text(json.dumps(sel["class_mean_sha256"], sort_keys=True))}
        C.clear_base()
        del acts
        EN.free_cuda()
    commit(cname, payload)
    stage_time(cname, time.time() - t0)


# ================================================================================================ validation
def stage_validate(name: str, max_prompts: int | None = None) -> None:
    t0 = time.time()
    model, tok = model_tok()
    C = get_contrast(name)
    sel = read_json(RESULTS_DIR / f"selection_{name}.json")
    top10 = [KC.parse_key(k) for k in sel["top10"]]
    rand_sets = sel["rand_sets"]
    factors = sel["factors"]
    pidx = sorted({i for ab in C.pairs for i in ab})
    acts = KC.collect_all(model, C, pidx)
    pairs = surviving_pairs(C, acts)
    clean = [c for c, _ in pairs]
    corrupt = [x for _, x in pairs]
    held = [i for i, p in enumerate(C.prompts) if p.get("heldout")]
    mc = KC.MeanCache(acts, C.prompts)
    raw = DATA_DIR / f"validation_rows_{name}.jsonl"
    done = {r["prompt_idx"] for r in read_jsonl(raw)}
    V = [i for ab in pairs for i in ab] + held
    if max_prompts:
        V = V[:max_prompts]
    queue = list(V)
    t_first = None
    n_done = 0
    while queue:
        i = queue.pop(0)
        if i in done:
            continue
        ti = time.time()
        p = C.prompts[i]
        side = p["cls"]
        opp, own = (corrupt, clean) if side == "clean" else (clean, corrupt)
        sign = -1.0 if side == "clean" else 1.0
        jobs: list[tuple[tuple, list[EN.Edit]]] = []
        for mode in ("ablate", "steer"):
            for nd in top10:
                k = KC.node_key(nd)
                e = KC.val_edit(nd, p, mc, opp, own, mode, 1.0, STEER_DOSE)
                jobs.append(((mode, k, "node"), [e] if e else []))
                for r, (rk, f) in enumerate(zip(rand_sets[k], factors[k])):
                    e = KC.val_edit(KC.parse_key(rk), p, mc, opp, own, mode, f, STEER_DOSE)
                    jobs.append(((mode, k, f"r{r}"), [e] if e else []))
            for size in (5, 10):
                eds = [KC.val_edit(nd, p, mc, opp, own, mode, 1.0, STEER_DOSE) for nd in top10[:size]]
                jobs.append(((mode, f"joint{size}", "node"), [e for e in eds if e]))
                for s_ in range(N_RAND):
                    eds = [KC.val_edit(KC.parse_key(rand_sets[KC.node_key(nd)][s_]), p, mc, opp, own, mode,
                                       factors[KC.node_key(nd)][s_], STEER_DOSE) for nd in top10[:size]]
                    jobs.append(((mode, f"joint{size}", f"r{s_}"), [e for e in eds if e]))
        by_q: dict[int, list] = {}
        ids = C.run_ids(i)
        for tag, eds in jobs:
            q = min(int(e.pos.min()) for e in eds) if eds else len(ids) - 1
            by_q.setdefault(q, []).append((tag, eds))
        res_i = {}
        pc = EN.PrefixCache()
        for q, items in sorted(by_q.items()):
            ms = EN.margins_rows(model, ids, C.metric, [e for _, e in items], q_min=q, base_edits=C.base(i), pcache=pc,
                                 pkey=i)
            for (tag, _), mv in zip(items, ms):
                res_i["|".join(tag)] = sign * mv
        pc.clear()
        n_jobs = len(jobs)
        del jobs, by_q
        EN.free_cuda()
        append_jsonl(raw, [{"prompt_idx": i, "vid": p["vid"], "side": side, "heldout": bool(p.get("heldout")),
                            "template": p["template"], "res": res_i, "utc": utc_now()}])
        done.add(i)
        n_done += 1
        dt = time.time() - ti
        if t_first is None:
            t_first = dt
            est = dt * len(V) / 60
            logger.info(f"[{name}] validation prompt 1: {n_jobs} rows in {dt:.1f}s -> {est:.1f} min for {len(V)}")
            write_json(RESULTS_DIR / f"validation_timing_{name}.json", {"first_prompt_s": dt, "rows": n_jobs,
                                                                         "n_prompts": len(V), "extrapolated_min": est})
            if est > 45 and len(V) > 25:
                keep = [c for c, _ in pairs] + held
                if dt * len(keep) / 60 > 45:
                    keep = [c for c, _ in pairs] + held[:5]
                log_deviation(f"time_rule_{name}", f"validation extrapolated to {est:.0f} min > 45: V = 15 clean "
                              f"prompts + {len(keep) - len([c for c, _ in pairs])} held-out (committed time rule)")
                queue = [j for j in keep if j not in done]
        logger.info(f"[{name}] validation {n_done} prompt {p['vid']} ({side}) {dt:.1f}s; {len(queue)} left")
    C.clear_base()
    stage_time(f"validate:{name}", time.time() - t0)


def stage_valsens(name: str) -> None:
    """POST-HOC SENSITIVITY (labelled; committed as commit_sens before any row): for top-10 HEAD nodes whose matched
    pool fell to 'nearest-50' (no candidate within +-50% write norm), the 50 random head draws are re-run with their
    patch delta rescaled to the target's write norm (the plan rescales only MLP draws). Same prompts, operations and
    in-chunk base rows as the primary validation; the primary result is unchanged."""
    t0 = time.time()
    model, tok = model_tok()
    C = get_contrast(name)
    sel = read_json(RESULTS_DIR / f"selection_{name}.json")
    wn = np.load(CACHE_DIR / f"write_norms_{name}.npy")
    heads = [k for k in sel["top10"] if k.startswith("head") and str(sel["matching"][k]["tolerance"]).startswith("nearest")]
    if not heads:
        logger.info(f"[{name}] valsens: no head pool fell back to nearest-50")
        return
    if not (PRED_DIR / f"commit_sens_{name}.json").exists():
        commit(f"commit_sens_{name}", {"rule": stage_valsens.__doc__, "heads": heads,
                                       "factors": {k: [float(wn[KC.KEY2IDX[k]] / max(wn[KC.KEY2IDX[r]], 1e-12))
                                                       for r in sel["rand_sets"][k]] for k in heads}})
    pidx = sorted({i for ab in C.pairs for i in ab})
    acts = KC.collect_all(model, C, pidx)
    pairs = surviving_pairs(C, acts)
    clean = [c for c, _ in pairs]
    corrupt = [x for _, x in pairs]
    held = [i for i, p in enumerate(C.prompts) if p.get("heldout")]
    done_rows = read_jsonl(DATA_DIR / f"validation_rows_{name}.jsonl")
    V = [r["prompt_idx"] for r in done_rows]
    mc = KC.MeanCache(acts, C.prompts)
    raw = DATA_DIR / f"validation_sens_rows_{name}.jsonl"
    done = {r["prompt_idx"] for r in read_jsonl(raw)}
    for i in V:
        if i in done:
            continue
        p = C.prompts[i]
        side = p["cls"]
        opp, own = (corrupt, clean) if side == "clean" else (clean, corrupt)
        sign = -1.0 if side == "clean" else 1.0
        jobs = []
        for mode in ("ablate", "steer"):
            for k in heads:
                nd = KC.parse_key(k)
                e = KC.val_edit(nd, p, mc, opp, own, mode, 1.0, STEER_DOSE)
                jobs.append(((mode, k, "node"), [e] if e else []))
                for r, rk in enumerate(sel["rand_sets"][k]):
                    f = float(wn[KC.KEY2IDX[k]] / max(wn[KC.KEY2IDX[rk]], 1e-12))
                    e = KC.val_edit(KC.parse_key(rk), p, mc, opp, own, mode, f, STEER_DOSE)
                    jobs.append(((mode, k, f"r{r}"), [e] if e else []))
        ids = C.run_ids(i)
        by_q: dict[int, list] = {}
        for tag, eds in jobs:
            q = min(int(e.pos.min()) for e in eds) if eds else len(ids) - 1
            by_q.setdefault(q, []).append((tag, eds))
        res_i = {}
        pc = EN.PrefixCache()
        for q, items in sorted(by_q.items()):
            ms = EN.margins_rows(model, ids, C.metric, [e for _, e in items], q_min=q, base_edits=C.base(i), pcache=pc,
                                 pkey=i)
            for (tag, _), mv in zip(items, ms):
                res_i["|".join(tag)] = sign * mv
        pc.clear()
        append_jsonl(raw, [{"prompt_idx": i, "vid": p["vid"], "side": side, "heldout": bool(p.get("heldout")),
                            "template": p["template"], "res": res_i, "utc": utc_now()}])
    C.clear_base()
    logger.info(f"[{name}] valsens done in {time.time() - t0:.0f}s for heads {heads}")
    stage_time(f"valsens:{name}", time.time() - t0)


def validation_sens_stats(name: str) -> dict[str, Any] | None:
    rows = read_jsonl(DATA_DIR / f"validation_sens_rows_{name}.jsonl")
    if not rows:
        return None
    heads = sorted({k.split("|", 1)[1].rsplit("|", 1)[0] for k in rows[0]["res"]})
    out = {"label": "POST-HOC sensitivity: head nulls rescaled to the target write norm", "per_node": {}}
    for mode in ("ablate", "steer"):
        recs = []
        for k in heads:
            d = []
            for r in rows:
                v = r["res"].get(f"{mode}|{k}|node")
                rv = [r["res"][f"{mode}|{k}|r{j}"] for j in range(N_RAND) if f"{mode}|{k}|r{j}" in r["res"]]
                if v is None or not rv:
                    continue
                d.append(v - float(np.mean(rv)))
            recs.append({"node": k, "n": len(d), "mean_d": float(np.mean(d)) if d else None,
                         "p_sign_flip": KS.sign_flip_p(np.array(d)) if d else 1.0})
        out["per_node"][mode] = recs
    return out


def validation_stats(name: str) -> dict[str, Any]:
    sel = read_json(RESULTS_DIR / f"selection_{name}.json")
    rows = read_jsonl(DATA_DIR / f"validation_rows_{name}.jsonl")
    top10 = sel["top10"]
    out: dict[str, Any] = {"n_prompts": len(rows), "n_heldout": sum(r["heldout"] for r in rows), "per_node": {},
                           "joint": {}}
    allp = []
    for mode in ("ablate", "steer"):
        recs = []
        for k in top10:
            d, dnode, f95, d_in, d_out = [], [], [], [], []
            for r in rows:
                v = r["res"].get(f"{mode}|{k}|node")
                rv = [r["res"][f"{mode}|{k}|r{j}"] for j in range(N_RAND) if f"{mode}|{k}|r{j}" in r["res"]]
                if v is None or not rv:
                    continue
                dd = v - float(np.mean(rv))
                d.append(dd)
                dnode.append(v)
                f95.append(v > np.percentile(rv, 95))
                (d_out if r["heldout"] else d_in).append(dd)
            d = np.array(d)
            pv = KS.sign_flip_p(d)
            recs.append({"node": k, "n": int(len(d)), "mean_d": float(d.mean()) if len(d) else None,
                         "median_d": float(np.median(d)) if len(d) else None, "p_sign_flip": pv,
                         "mean_dm_node_oriented": float(np.mean(dnode)) if dnode else None,
                         "frac_prompts_above_null_p95": float(np.mean(f95)) if f95 else None,
                         "mean_d_pair_prompts": float(np.mean(d_in)) if d_in else None,
                         "mean_d_heldout": float(np.mean(d_out)) if d_out else None,
                         "p_sign_flip_heldout": KS.sign_flip_p(np.array(d_out)) if d_out else None,
                         "d_per_prompt": d.tolist()})
            allp.append(pv)
        adj = KS.holm([r["p_sign_flip"] for r in recs])
        for rec, a in zip(recs, adj):
            rec["p_holm_within_test"] = a
        out["per_node"][mode] = recs
        jres = {}
        for size in (5, 10):
            nodev = [r["res"].get(f"{mode}|joint{size}|node") for r in rows]
            nodev = [v for v in nodev if v is not None]
            node_med = float(np.median(nodev))
            rmeds = [float(np.median([r["res"][f"{mode}|joint{size}|r{s}"] for r in rows])) for s in range(N_RAND)]
            jres[str(size)] = {"median_node_set": node_med, "median_random_sets": rmeds,
                               "frac_random_beaten": float(np.mean(np.array(rmeds) < node_med))}
        out["joint"][mode] = jres
    adj20 = KS.holm(allp)
    i = 0
    for mode in ("ablate", "steer"):
        for rec in out["per_node"][mode]:
            rec["p_holm_20"] = adj20[i]
            i += 1
    passes = []
    for j, k in enumerate(top10):
        a = out["per_node"]["ablate"][j]
        s = out["per_node"]["steer"][j]
        passes.append({"node": k, "ablate_pass": a["p_holm_20"] < 0.05, "steer_pass": s["p_holm_20"] < 0.05,
                       "both": a["p_holm_20"] < 0.05 and s["p_holm_20"] < 0.05,
                       "both_within_test_holm": a["p_holm_within_test"] < 0.05 and s["p_holm_within_test"] < 0.05})
    out["node_pass"] = passes
    out["n_pass_both_holm20"] = int(sum(p["both"] for p in passes))
    out["n_pass_ablate_holm20"] = int(sum(p["ablate_pass"] for p in passes))
    out["n_pass_steer_holm20"] = int(sum(p["steer_pass"] for p in passes))
    out["n_pass_both_within_test_holm"] = int(sum(p["both_within_test_holm"] for p in passes))
    out["n_pass_ablate_within"] = int(sum(r["p_holm_within_test"] < 0.05 for r in out["per_node"]["ablate"]))
    out["n_pass_steer_within"] = int(sum(r["p_holm_within_test"] < 0.05 for r in out["per_node"]["steer"]))
    out["any_node_passes_any_test"] = bool(out["n_pass_ablate_holm20"] + out["n_pass_steer_holm20"] > 0)
    out["matching"] = sel["matching"]
    return out


# ================================================================================================ generation
def gen_spec(name: str) -> dict[str, Any]:
    sel = read_json(RESULTS_DIR / f"selection_{name}.json")
    unit = "B3" if name.startswith("C1") else "T10"
    return {"contrast": name, "unit": unit, "arms": ["TWIN", "TOP5", "RAND5"], "top5": sel["top5"],
            "gen_top5": sel["gen_top5"],
            "rand5": sel["rand5"], "rand5_factors": sel["rand5_factors"], "operation": "STEER toward the minority "
            "(own + 2 x (minority-class mean - default-class mean)) on all five nodes at once",
            "slots": "W1-W5 x 6 CRN slots", "keys": ("('iter7T', 'B3', w, k)" if unit == "B3" else
                                                     "('iter8K3', 'T10', w, k)"),
            "conditions": {"PREFILL": "prompt + opening prefilled for every arm; uniforms offset by the opening length",
                           "FREE": "no prefill; OPEN/DEC edits fire only while the generated prefix equals the "
                                   "opening (implemented exactly by teacher-forcing the edited opening and sampling "
                                   "with the slot's uniforms until the first divergence)"},
            "max_new": MAX_NEW_GEN, "target": "correct prim_heap or prim_array" if unit == "B3" else "correct dfs"}


def gen_edits(name: str, C: KC.Contrast, acts: dict[int, EN.Acts], pairs: list[tuple[int, int]], twin: dict[str, Any],
              keys: list[str], factors: list[float]) -> list[EN.Edit]:
    clean = [c for c, _ in pairs]
    corrupt = [x for _, x in pairs]
    mc = KC.MeanCache(acts, C.prompts)
    out = []
    for k, f in zip(keys, factors):
        e = KC.val_edit(KC.parse_key(k), twin, mc, corrupt, clean, "steer", f, STEER_DOSE)
        if e is not None:
            out.append(e)
    return out


def stage_generate(name: str, free: bool = True) -> None:
    t0 = time.time()
    assert (PRED_DIR / "commit2.json").exists(), "COMMIT #2 must precede any steered program"
    model, tok = model_tok()
    C = get_contrast(name)
    sel = read_json(RESULTS_DIR / f"selection_{name}.json")
    pidx = sorted({i for ab in C.pairs for i in ab})
    acts = KC.collect_all(model, C, pidx)
    pairs = surviving_pairs(C, acts)
    unit = "B3" if name.startswith("C1") else "T10"
    twins = KP.b3_twins(tok) if unit == "B3" else KP.t10_twins(tok)
    for w in TEMPLATES:
        twins[w] = dict(twins[w], vid=f"{w}|twin")
    opening = C.opening
    L = len(opening)
    raw = DATA_DIR / f"gen_raw_{name}.jsonl"
    done = {r["row_id"] for r in read_jsonl(raw)}
    arms = {"TWIN": ([], []), "TOP5": (sel["gen_top5"], [1.0] * len(sel["gen_top5"])),
            "RAND5": (sel["rand5"], sel["rand5_factors"])}
    for cond in (("PREFILL", "FREE") if free else ("PREFILL",)):
        items, metas = [], []
        for arm, (keys, fac) in arms.items():
            for w in TEMPLATES:
                tw = twins[w]
                eds = gen_edits(name, C, acts, pairs, tw, keys, fac) if keys else []
                for k in GEN_SLOTS:
                    rid = f"{name}|{cond}|{arm}|{w}|{k}"
                    if rid in done:
                        continue
                    key = ("iter7T", "B3", w, k) if unit == "B3" else ("iter8K3", "T10", w, k)
                    items.append({"tw": tw, "eds": eds, "key": key, "arm": arm, "w": w, "k": k, "rid": rid})
        if not items:
            continue
        if cond == "PREFILL":
            for b0 in range(0, len(items), 15):
                part = items[b0:b0 + 15]
                tb = time.time()
                gi = [{"ids": it["tw"]["ids"] + opening, "edits": it["eds"], "pre_key": (it["arm"], it["w"]),
                       "u": u_stream(*it["key"], n=MAX_NEW_GEN + L + 8)[L:L + MAX_NEW_GEN]} for it in part]
                res = EN.generate(model, tok, gi, MAX_NEW_GEN)
                recs = []
                for it, r in zip(part, res):
                    ids = list(opening) + r["token_ids"]
                    recs.append(gen_record(name, unit, cond, it, ids, r, tok, decision_pos=L, reached=True))
                append_jsonl(raw, recs)
                logger.info(f"[{name}] gen {cond} {b0 + len(part)}/{len(items)} in {time.time() - tb:.1f}s")
        else:
            gen_free(name, unit, model, tok, items, opening, raw)
    C.clear_base()
    label_pending(raw, DATA_DIR / f"gen_labels_{name}.jsonl", unit)
    stage_time(f"gen:{name}", time.time() - t0)


def gen_record(name: str, unit: str, cond: str, it: dict[str, Any], ids: list[int], r: dict[str, Any], tok: Any,
               decision_pos: int | None, reached: bool) -> dict[str, Any]:
    return {"row_id": it["rid"], "contrast": name, "unit": unit, "condition": cond, "arm": it["arm"],
            "template": it["w"], "slot": it["k"], "ukey": list(it["key"]), "token_ids": ids,
            "text": tok.decode(ids, skip_special_tokens=True), "n_new_tokens": len(ids),
            "finish_reason": r.get("finish_reason"), "decision_pos": decision_pos, "reached_decision": reached,
            "prompt_sha256": it["tw"]["prompt_sha256"], "noun": it["tw"].get("noun"), "utc": utc_now(),
            "edits": [e.name for e in it["eds"]]}


@torch.no_grad()
def gen_free(name: str, unit: str, model: Any, tok: Any, items: list[dict[str, Any]], opening: list[int],
             raw: Path) -> None:
    """FREE condition. Per (arm, template): teacher-force prompt + opening with every edit (COND/SPEC/OPEN/DEC) and
    sample tokens 0..L with the slot's uniforms; while the sampled token equals the opening the edits at that
    position fired online. A row that reproduces the whole opening reaches the decision (its program then equals
    the PREFILL program of the slot, regenerated here); a row that diverges at t continues from prompt + O[:t] + x with
    only the edits at positions < P + t (prefill) and no edit afterwards."""
    L = len(opening)
    groups: dict[tuple, list[dict[str, Any]]] = {}
    for it in items:
        groups.setdefault((it["arm"], it["w"]), []).append(it)
    cont = []
    for (arm, w), its in groups.items():
        tw = its[0]["tw"]
        P = tw["P"]
        ids = tw["ids"] + opening
        lg = EN.teacher_force_logits(model, ids, P, its[0]["eds"])          # rows predict tokens 0..L
        for it in its:
            u = u_stream(*it["key"], n=MAX_NEW_GEN + L + 8)
            t_div, x = None, None
            for t in range(L):
                tok_t = EN.sample_token(lg[t], float(u[t]))
                if tok_t != opening[t]:
                    t_div, x = t, tok_t
                    break
            if t_div is None:
                cont.append({"it": it, "prefix": list(opening), "ids": ids, "edits": it["eds"], "u": u[L:],
                             "reached": True})
            else:
                pre_ids = tw["ids"] + opening[:t_div] + [x]
                eds = [e2 for e2 in (e.prefix(P + t_div) for e in it["eds"]) if e2 is not None]
                cont.append({"it": it, "prefix": opening[:t_div] + [x], "ids": pre_ids, "edits": eds,
                             "u": u[t_div + 1:], "reached": False, "t_div": t_div})
        del lg
    for b0 in range(0, len(cont), 15):
        part = cont[b0:b0 + 15]
        gi = [{"ids": c["ids"], "edits": c["edits"], "pre_key": (c["it"]["rid"],), "u": c["u"][:MAX_NEW_GEN]}
              for c in part]
        res = EN.generate(model, tok, gi, MAX_NEW_GEN)
        recs = []
        for c, r in zip(part, res):
            idsr = c["prefix"] + r["token_ids"]
            rec = gen_record(name, unit, "FREE", c["it"], idsr, r, tok, decision_pos=L if c["reached"] else None,
                             reached=c["reached"])
            rec["t_divergence"] = c.get("t_div")
            recs.append(rec)
        append_jsonl(raw, recs)
        logger.info(f"[{name}] gen FREE {b0 + len(part)}/{len(cont)}")


def label_pending(raw: Path, labels: Path, unit: str) -> int:
    import subprocess
    have = {r["sid"] for r in read_jsonl(labels)}
    todo = [{"sid": r["row_id"], "unit": r["unit"], "text": r["text"]} for r in read_jsonl(raw)
            if r["row_id"] not in have]
    if not todo:
        return 0
    tmp_in = CACHE_DIR / "tmp" / f"label_in_{int(time.time() * 1000)}.jsonl"
    tmp_out = tmp_in.with_name(tmp_in.name.replace("label_in", "label_out"))
    tmp_in.parent.mkdir(parents=True, exist_ok=True)
    tmp_in.write_text("".join(json.dumps(r) + "\n" for r in todo))
    t0 = time.time()
    pr = subprocess.run([sys.executable, str(ROOT / "src" / "label_k3.py"), str(tmp_in), str(tmp_out)],
                        capture_output=True, text=True, timeout=3600)
    if pr.returncode != 0:
        logger.error(f"label worker failed: {pr.stderr[-2000:]}")
        raise RuntimeError("label worker failed")
    res = read_jsonl(tmp_out)
    append_jsonl(labels, [{**r, "utc": utc_now()} for r in res])
    tmp_in.unlink(missing_ok=True)
    tmp_out.unlink(missing_ok=True)
    logger.info(f"labelled {len(res)} rows in {time.time() - t0:.1f}s")
    return len(res)


def gen_stats(name: str) -> dict[str, Any]:
    raw = {r["row_id"]: r for r in read_jsonl(DATA_DIR / f"gen_raw_{name}.jsonl")}
    lab = {r["sid"]: r for r in read_jsonl(DATA_DIR / f"gen_labels_{name}.jsonl")}
    unit = "B3" if name.startswith("C1") else "T10"
    targets = ("prim_heap", "prim_array") if unit == "B3" else ("dfs",)
    out: dict[str, Any] = {}
    for cond in ("PREFILL", "FREE"):
        cells: dict[str, dict[tuple, dict]] = {}
        for rid, r in raw.items():
            if r["condition"] != cond or rid not in lab:
                continue
            L = lab[rid]
            cells.setdefault(r["arm"], {})[(r["template"], r["slot"])] = {
                "label": L["label"], "passed": bool(L["passed"]), "target": L["label"] in targets,
                "correct_target": L["label"] in targets and bool(L["passed"]), "reached": r["reached_decision"]}
        if not cells:
            continue
        res: dict[str, Any] = {"arms": {}}
        for arm, d in cells.items():
            n = len(d)
            labs: dict[str, int] = {}
            for v in d.values():
                labs[v["label"]] = labs.get(v["label"], 0) + 1
            res["arms"][arm] = {"n": n, "correct_target": sum(v["correct_target"] for v in d.values()),
                                "attempted_target": sum(v["target"] for v in d.values()),
                                "passed": sum(v["passed"] for v in d.values()), "labels": labs,
                                "reached_decision": sum(bool(v["reached"]) for v in d.values()),
                                "pass_rate": sum(v["passed"] for v in d.values()) / max(n, 1),
                                "other_share": labs.get("other", 0) / max(n, 1)}
        if all(a in cells for a in ("TWIN", "TOP5", "RAND5")):
            slots = sorted(set(cells["TWIN"]) & set(cells["TOP5"]) & set(cells["RAND5"]))

            def tab(a: str, b: str, key: str) -> dict[str, Any]:
                both = sum(cells[a][s][key] and cells[b][s][key] for s in slots)
                bb = sum(cells[a][s][key] and not cells[b][s][key] for s in slots)
                cc = sum(cells[b][s][key] and not cells[a][s][key] for s in slots)
                dd = len(slots) - both - bb - cc
                return {"a_only": bb, "b_only": cc, "both": both, "neither": dd,
                        "mcnemar_p_one_sided": KS.mcnemar_exact(bb, cc, "greater"),
                        "mcnemar_p_two_sided": KS.mcnemar_exact(bb, cc, "two-sided"),
                        "newcombe": KS.newcombe_paired(both, bb, cc, dd)}
            res["TOP5_vs_RAND5"] = tab("TOP5", "RAND5", "correct_target")
            res["TOP5_vs_TWIN"] = tab("TOP5", "TWIN", "correct_target")
            res["RAND5_vs_TWIN"] = tab("RAND5", "TWIN", "correct_target")
            res["pass_TOP5_vs_TWIN"] = tab("TOP5", "TWIN", "passed")
            a = res["arms"]
            res["criteria"] = {
                "plus_vs_twin": a["TOP5"]["correct_target"] - a["TWIN"]["correct_target"],
                "plus_ge_6": a["TOP5"]["correct_target"] - a["TWIN"]["correct_target"] >= GEN_THRESH_PLUS,
                "mcnemar_top5_vs_rand5_p": res["TOP5_vs_RAND5"]["mcnemar_p_two_sided"],
                "mcnemar_top5_vs_rand5_p_one_sided": res["TOP5_vs_RAND5"]["mcnemar_p_one_sided"],
                "beats_rand5": res["TOP5_vs_RAND5"]["mcnemar_p_two_sided"] < 0.05,
                "beats_rand5_one_sided": res["TOP5_vs_RAND5"]["mcnemar_p_one_sided"] < 0.05,
                "mcnemar_convention": "PRIMARY two-sided exact McNemar (the plan's calibration: 8:0 -> 0.0078, 7:1 -> "
                                      "0.07); the one-sided p fixed in the commit-#0 analysis code is reported beside",
                "pass_ratio": a["TOP5"]["pass_rate"] / max(a["TWIN"]["pass_rate"], 1e-9),
                "pass_ratio_ok": a["TOP5"]["pass_rate"] >= GEN_PASS_RATIO * a["TWIN"]["pass_rate"]}
            res["criteria"]["all"] = bool(res["criteria"]["plus_ge_6"] and res["criteria"]["beats_rand5"] and
                                          res["criteria"]["pass_ratio_ok"])
            res["criteria"]["all_one_sided"] = bool(res["criteria"]["plus_ge_6"] and
                                                    res["criteria"]["beats_rand5_one_sided"] and
                                                    res["criteria"]["pass_ratio_ok"])
            res["flips"] = [{"slot": f"{s[0]}|{s[1]}", "TWIN": cells["TWIN"][s]["label"],
                             "TOP5": cells["TOP5"][s]["label"], "RAND5": cells["RAND5"][s]["label"]} for s in slots
                            if cells["TOP5"][s]["label"] != cells["TWIN"][s]["label"] or
                            cells["RAND5"][s]["label"] != cells["TWIN"][s]["label"]]
        out[cond] = res
    return out


def stage_dose(name: str, doses: tuple[float, ...] = (0.5, 1.0)) -> None:
    """POST-HOC DOSE SENSITIVITY (labelled; commit_dose_<name> precedes every row). At the committed dose 2 both TOP5
    and the matched RAND5 saturate the minority algorithm, so the TOP5-vs-RAND5 McNemar has no room. Here: (a) logit
    level: P(minority decision token) at DEC on the five twins under TOP5 / RAND5 STEER at doses 0.25-2; (b) generation:
    PREFILL TOP5 and RAND5 arms at doses 0.5 and 1 on the same 30 CRN slots (TWIN = the committed TWIN arm). The
    primary K3 result is unchanged."""
    t0 = time.time()
    model, tok = model_tok()
    if not (PRED_DIR / f"commit_dose_{name}.json").exists():
        commit(f"commit_dose_{name}", {"rule": stage_dose.__doc__, "doses_generation": list(doses),
                                       "doses_logit": [0.25, 0.5, 1.0, 2.0]})
    C = get_contrast(name)
    sel = read_json(RESULTS_DIR / f"selection_{name}.json")
    pidx = sorted({i for ab in C.pairs for i in ab})
    acts = KC.collect_all(model, C, pidx)
    pairs = surviving_pairs(C, acts)
    clean = [c for c, _ in pairs]
    corrupt = [x for _, x in pairs]
    unit = "B3" if name.startswith("C1") else "T10"
    twins = KP.b3_twins(tok) if unit == "B3" else KP.t10_twins(tok)
    for w in TEMPLATES:
        twins[w] = dict(twins[w], vid=f"{w}|twin")
    opening = C.opening
    L = len(opening)
    mc = KC.MeanCache(acts, C.prompts)
    arms = {"TOP5": (sel["gen_top5"], [1.0] * len(sel["gen_top5"])), "RAND5": (sel["rand5"], sel["rand5_factors"])}

    def eds_for(tw: dict, keys: list[str], fac: list[float], dose: float) -> list[EN.Edit]:
        out = []
        for k, f in zip(keys, fac):
            e = KC.val_edit(KC.parse_key(k), tw, mc, corrupt, clean, "steer", f, dose)
            if e is not None:
                out.append(e)
        return out
    # (a) logit level
    met = C.metric
    logit = []
    for w in TEMPLATES:
        tw = twins[w]
        ids = tw["ids"] + opening
        rows = [[]]
        tags = [("TWIN", 0.0)]
        for arm, (keys, fac) in arms.items():
            for d in (0.25, 0.5, 1.0, 2.0):
                rows.append(eds_for(tw, keys, fac, d))
                tags.append((arm, d))
        ms = EN.margins_rows(model, ids, met, rows[1:], q_min=0, relative=False)
        m0 = EN.margins_rows(model, ids, met, [[]], q_min=0, relative=False)[0]
        for (arm, d), mv in zip(tags[1:], ms):
            logit.append({"template": w, "arm": arm, "dose": d, "m": mv, "m_twin": m0,
                          "p_minority_2way": float(1 / (1 + np.exp(mv)))})
    write_json(RESULTS_DIR / f"dose_logit_{name}.json", logit)
    # (b) generation at doses 0.5 and 1 (PREFILL)
    raw = DATA_DIR / f"gen_dose_raw_{name}.jsonl"
    done = {r["row_id"] for r in read_jsonl(raw)}
    items = []
    for d in doses:
        for arm, (keys, fac) in arms.items():
            for w in TEMPLATES:
                tw = twins[w]
                eds = eds_for(tw, keys, fac, d)
                for k in GEN_SLOTS:
                    rid = f"{name}|DOSE{d}|{arm}|{w}|{k}"
                    if rid in done:
                        continue
                    key = ("iter7T", "B3", w, k) if unit == "B3" else ("iter8K3", "T10", w, k)
                    items.append({"tw": tw, "eds": eds, "key": key, "arm": arm, "w": w, "k": k, "rid": rid, "dose": d})
    for b0 in range(0, len(items), 15):
        part = items[b0:b0 + 15]
        gi = [{"ids": it["tw"]["ids"] + opening, "edits": it["eds"], "pre_key": (it["arm"], it["w"], it["dose"]),
               "u": u_stream(*it["key"], n=MAX_NEW_GEN + L + 8)[L:L + MAX_NEW_GEN]} for it in part]
        res = EN.generate(model, tok, gi, MAX_NEW_GEN)
        recs = []
        for it, r in zip(part, res):
            rec = gen_record(name, unit, f"DOSE{it['dose']}", it, list(opening) + r["token_ids"], r, tok,
                             decision_pos=L, reached=True)
            rec["dose"] = it["dose"]
            recs.append(rec)
        append_jsonl(raw, recs)
        logger.info(f"[{name}] dose gen {b0 + len(part)}/{len(items)}")
    C.clear_base()
    label_pending(raw, DATA_DIR / f"gen_dose_labels_{name}.jsonl", unit)
    stage_time(f"dose:{name}", time.time() - t0)


def dose_stats(name: str) -> dict[str, Any] | None:
    raw = read_jsonl(DATA_DIR / f"gen_dose_raw_{name}.jsonl")
    if not raw:
        return None
    lab = {r["sid"]: r for r in read_jsonl(DATA_DIR / f"gen_dose_labels_{name}.jsonl")}
    tw_raw = {(r["template"], r["slot"]): r for r in read_jsonl(DATA_DIR / f"gen_raw_{name}.jsonl")
              if r["condition"] == "PREFILL" and r["arm"] == "TWIN"}
    tw_lab = {r["sid"]: r for r in read_jsonl(DATA_DIR / f"gen_labels_{name}.jsonl")}
    targets = ("prim_heap", "prim_array") if name.startswith("C1") else ("dfs",)
    out: dict[str, Any] = {"label": "POST-HOC dose sensitivity (generation, PREFILL)", "doses": {}}
    for d in sorted({r["dose"] for r in raw}):
        cells: dict[str, dict] = {}
        for r in raw:
            if r["dose"] != d or r["row_id"] not in lab:
                continue
            L_ = lab[r["row_id"]]
            cells.setdefault(r["arm"], {})[(r["template"], r["slot"])] = (L_["label"] in targets and bool(L_["passed"]),
                                                                          bool(L_["passed"]))
        tw = {s: (tw_lab[r["row_id"]]["label"] in targets and bool(tw_lab[r["row_id"]]["passed"]))
              for s, r in tw_raw.items() if r["row_id"] in tw_lab}
        slots = sorted(set(cells.get("TOP5", {})) & set(cells.get("RAND5", {})))
        b = sum(cells["TOP5"][s][0] and not cells["RAND5"][s][0] for s in slots)
        c = sum(cells["RAND5"][s][0] and not cells["TOP5"][s][0] for s in slots)
        out["doses"][str(d)] = {"TOP5_correct_target": sum(cells["TOP5"][s][0] for s in slots),
                                "RAND5_correct_target": sum(cells["RAND5"][s][0] for s in slots),
                                "TWIN_correct_target": sum(tw.get(s, False) for s in slots), "n": len(slots),
                                "TOP5_pass": sum(cells["TOP5"][s][1] for s in slots),
                                "RAND5_pass": sum(cells["RAND5"][s][1] for s in slots),
                                "discordant_top5_only": b, "discordant_rand5_only": c,
                                "mcnemar_two_sided": KS.mcnemar_exact(b, c, "two-sided"),
                                "mcnemar_one_sided": KS.mcnemar_exact(b, c, "greater")}
    lp = RESULTS_DIR / f"dose_logit_{name}.json"
    if lp.exists():
        lg = read_json(lp)
        agg: dict[str, dict[str, float]] = {}
        for r in lg:
            agg.setdefault(r["arm"], {}).setdefault(str(r["dose"]), [])
            agg[r["arm"]][str(r["dose"])].append(r["p_minority_2way"])
        out["logit_p_minority_mean"] = {a: {d: float(np.mean(v)) for d, v in dd.items()} for a, dd in agg.items()}
        out["logit_twin_p_minority_mean"] = float(np.mean([1 / (1 + np.exp(r["m_twin"])) for r in lg
                                                           if r["arm"] == "TOP5" and r["dose"] == 2.0]))
    return out


# ================================================================================================ engine check
def stage_enginecheck() -> None:
    t0 = time.time()
    model, tok = model_tok()
    raw = DATA_DIR / "engine_check_raw.jsonl"
    done = {r["row_id"] for r in read_jsonl(raw)}
    items = []
    b3 = KP.b3_twins(tok)
    t10 = KP.t10_twins(tok)
    for w in TEMPLATES:
        for k in range(4):
            items.append(("B3", w, k, b3[w], ("iter7T", "B3", w, k), 768, f"B3|TWIN|TWIN|{w}|{k}"))
            items.append(("T10", w, k, t10[w], ("T10", w, k), 384, f"T10|{w}|TWIN|{k}"))
    todo = [it for it in items if f"EC|{it[6]}" not in done]
    for unit in ("B3", "T10"):
        part = [it for it in todo if it[0] == unit]
        for b0 in range(0, len(part), 10):
            ch = part[b0:b0 + 10]
            gi = [{"ids": it[3]["ids"], "edits": [], "pre_key": it[1], "u": u_stream(*it[4], n=it[5] + 8)[:it[5]]}
                  for it in ch]
            res = EN.generate(model, tok, gi, ch[0][5])
            recs = [{"row_id": f"EC|{it[6]}", "unit": it[0], "template": it[1], "slot": it[2], "ref_sid": it[6],
                     "token_ids": r["token_ids"], "text": tok.decode(r["token_ids"], skip_special_tokens=True),
                     "finish_reason": r["finish_reason"], "utc": utc_now()} for it, r in zip(ch, res)]
            append_jsonl(raw, recs)
    label_pending(raw, DATA_DIR / "engine_check_labels.jsonl", "mixed")
    lab = {r["sid"]: r for r in read_jsonl(DATA_DIR / "engine_check_labels.jsonl")}
    ref35 = {r["sid"]: r for r in read_jsonl(Path("../../../round-7/"
                                                  "gen_art/gen_art_experiment_35/data/labels.jsonl"))
             if r["sid"].startswith("B3|TWIN|TWIN|")}
    raw35 = {}
    p35 = Path("/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_35/data/"
               "samples_raw.jsonl")
    if p35.exists():
        for r in read_jsonl(p35):
            if r["sid"].startswith("B3|TWIN|TWIN|"):
                raw35[r["sid"]] = r["token_ids"]
    p34 = Path("/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_34/data/"
               "labels.jsonl")
    ref34 = {r["key"]: r for r in read_jsonl(p34) if r.get("task") == "T10" and r.get("arm") == "TWIN"}
    out = {"B3": {"n": 0, "label_agree": 0, "token_identical": 0}, "T10": {"n": 0, "label_agree": 0}}
    rows = []
    for r in read_jsonl(raw):
        L = lab.get(r["row_id"])
        if L is None:
            continue
        if r["unit"] == "B3":
            ref = ref35.get(r["ref_sid"])
            if ref is None:
                continue
            out["B3"]["n"] += 1
            out["B3"]["label_agree"] += int(ref["label"] == L["label"])
            out["B3"]["token_identical"] += int(raw35.get(r["ref_sid"]) == r["token_ids"])
            rows.append({"sid": r["ref_sid"], "label": L["label"], "ref_label": ref["label"]})
        else:
            ref = ref34.get(r["ref_sid"])
            if ref is None:
                continue
            out["T10"]["n"] += 1
            out["T10"]["label_agree"] += int(ref["label"] == L["label"])
            rows.append({"sid": r["ref_sid"], "label": L["label"], "ref_label": ref["label"]})
    for u in out:
        out[u]["agreement"] = out[u]["label_agree"] / max(out[u]["n"], 1)
        out[u]["pass_0.95"] = out[u]["agreement"] >= 0.95
    out["rows"] = rows
    out["note"] = ("B3 reference: art_MZAfDPVhM6Ui twin slots (same CRN keys, same engine family); T10 reference: "
                   "art_pHL7LWNhpcCS twin labels (RTX 4090, exp29 engine; label-level comparison only)")
    write_json(RESULTS_DIR / "engine_check.json", out)
    if not out["B3"]["pass_0.95"]:
        log_deviation("engine_check_B3", f"B3 twin label agreement {out['B3']['agreement']:.2f} < 0.95 (kernel "
                      "sensitivity on this GPU)")
    stage_time("enginecheck", time.time() - t0)


# ================================================================================================ main
@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", default="setup")
    ap.add_argument("--max-prompts", type=int, default=None)
    ap.add_argument("--no-free", action="store_true")
    a = ap.parse_args()
    setup_logging("method")
    for st in a.stages.split(","):
        logger.info(f"=== stage {st} ===")
        if st == "setup":
            stage_setup()
        elif st == "contrasts":
            stage_contrasts()
        elif st == "gputests":
            stage_gputests()
        elif st == "amend0a":
            stage_amend0a()
        elif st.startswith("circuit:"):
            nm = st.split(":")[1]
            light = nm in ("C1mix",)
            stage_circuit(nm, edges=not light, faith=not light, rel=not light)
        elif st.startswith("f4b:"):
            stage_f4b(st.split(":")[1])
        elif st.startswith("circuitlite:"):
            stage_circuit(st.split(":")[1], edges=True, faith=False, rel=False)
        elif st.startswith("commit1"):
            stage_commit1(st.split(":")[1].split("+") if ":" in st else ["C1forced", "C2a", "C1nat"],
                          st.split(":")[0])
        elif st.startswith("dose:"):
            stage_dose(st.split(":")[1])
        elif st.startswith("valsens:"):
            stage_valsens(st.split(":")[1])
        elif st.startswith("validate:"):
            stage_validate(st.split(":")[1], a.max_prompts)
        elif st.startswith("commit2"):
            names = st.split(":")[1].split("+") if ":" in st else ["C1forced", "C2a"]
            commit("commit2", {n: gen_spec(n) for n in names})
        elif st.startswith("gen:"):
            stage_generate(st.split(":")[1], free=not a.no_free)
        elif st == "enginecheck":
            stage_enginecheck()
        else:
            raise ValueError(st)
        logger.info(f"=== stage {st} done ===")


if __name__ == "__main__":
    main()
