#!/usr/bin/env python3
"""B3: rerun of iteration 8's held-out condition-node validation (art_18XvfcJJZi1O, C1forced) with an interpolating
MeanCache, plus the motif statistic on contrasts matched in kind (CPU).

6.1 reproduce one pair-prompt value with the vendored exp41 val_edit path unchanged (exact exp41 job list for pair
    prompt 0, grouped by q as in stage_validate) -> d(ablate, mlp|L0|H-1|COND) vs 8.29053352355957.
6.2 show the bug: the original MeanCache.get returns None for every COND node on every held-out prompt.
6.4 COMMIT #B3 (meancache_aligned.py sha256, unit tests, the 6.1 value) before 6.5.
6.5 held-out arm: every COND node of exp41's C1forced and C1nat top-15; ablate (factor 1), steer (dose 2; dose 0.5 as a
    post-hoc sensitivity); that node's 50 write-norm-matched random components (exp41 selection_C1forced rand_sets, or
    the exp41 matcher select_random with seed SEED_POOL for nodes outside the C1forced top 10).
6.6 per node: mean_d_heldout, d_per_prompt, exact sign-flip p (2^10), frac_random_beaten_heldout, pair-prompt values.
6.7 motif (CPU): k3motif on Qwen C1nat (natural) and C1forced (forced) vs Gemma natural10 / forced5 (g1_pathpatch.json).
Usage: b3_9.py gpu | motif
"""

from __future__ import annotations

import sys
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg9 import (B3_TARGET_D, B3_TOL_EXACT, B3_TOL_GPU, RESULTS_DIR, SRC, STEER_DOSE, STEER_DOSE_SENS, V38, V41,
                  append_jsonl, commit, log_deviation, read_json, read_jsonl, setup_logging, sha256_file,
                  stage_time, utc_now, write_json)

if str(V41 / "src") not in sys.path:
    sys.path.insert(0, str(V41 / "src"))
import k3circuit as KC  # noqa: E402
import k3engine as EN  # noqa: E402
import k3motif as KM  # noqa: E402
import k3prompts as KP  # noqa: E402
from k3cfg import N_RAND, SEED_POOL, TE_MIN  # noqa: E402

import stats9 as S  # noqa: E402
from meancache_aligned import MeanCacheAligned  # noqa: E402

ROWS_FILE = RESULTS_DIR / "b3_heldout_rows.jsonl"


def make_c1forced(tok: Any) -> KC.Contrast:
    """exp41 method.make_c1forced (amendment 0a): F1-F10 pairs; F11-F15 and their padding twins held out."""
    fl = KP.b3_forced(tok)
    prompts, pairs = [], []
    for pad, f in fl[:10]:
        prompts += [dict(pad, cls="clean"), dict(f, cls="corrupt")]
        pairs.append((len(prompts) - 2, len(prompts) - 1))
    for pad, f in fl[10:15]:
        prompts += [dict(pad, cls="clean", heldout=True), dict(f, cls="corrupt", heldout=True)]
    tid = lambda s: tok(s, add_special_tokens=False)["input_ids"][0]  # noqa: E731
    return KC.Contrast("C1forced", EN.Metric(tid(" Kr"), tid(" Prim")), prompts, KP.b3_opening(), pairs)


def surviving_pairs(C: KC.Contrast, acts: dict[int, EN.Acts]) -> list[tuple[int, int]]:
    return [(c, x) for c, x in C.pairs if acts[c].m - acts[x].m > TE_MIN]


def run_jobs(model: Any, C: KC.Contrast, i: int, jobs: list[tuple[tuple, list]], sign: float) -> dict[str, float]:
    by_q: dict[int, list] = {}
    ids = C.run_ids(i)
    for tag, eds in jobs:
        q = min(int(e.pos.min()) for e in eds) if eds else len(ids) - 1
        by_q.setdefault(q, []).append((tag, eds))
    res = {}
    pc = EN.PrefixCache()
    for q, items in sorted(by_q.items()):
        ms = EN.margins_rows(model, ids, C.metric, [e for _, e in items], q_min=q, base_edits=C.base(i), pcache=pc,
                             pkey=i)
        for (tag, _), mv in zip(items, ms):
            res["|".join(tag)] = sign * mv
    pc.clear()
    return res


def exp41_jobs(p: dict, mc: KC.MeanCache, opp: list[int], own: list[int], sel: dict) -> list[tuple[tuple, list]]:
    """The exact stage_validate job list of exp41 for one prompt."""
    top10 = [KC.parse_key(k) for k in sel["top10"]]
    rand_sets, factors = sel["rand_sets"], sel["factors"]
    jobs: list[tuple[tuple, list]] = []
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
    return jobs


def cond_nodes() -> list[str]:
    s = read_json(V41 / "results" / "summary.json")
    out = []
    for c in ("C1forced", "C1nat"):
        for k in s["circuits"][c]["top15"]:
            if k.endswith("|COND") and k not in out:
                out.append(k)
    prim = "mlp|L0|H-1|COND"
    return [prim] + [k for k in out if k != prim]


def random_for(node_key: str, sel: dict, wn: np.ndarray) -> tuple[list[str], list[float], str]:
    if node_key in sel["rand_sets"]:
        return sel["rand_sets"][node_key], sel["factors"][node_key], "exp41 selection_C1forced.json"
    j = KC.KEY2IDX[node_key]
    r = KC.select_random([j], wn, SEED_POOL)
    return r["rand_sets"][node_key], r["factors"][node_key], f"exp41 matcher select_random(seed {SEED_POOL})"


@torch.no_grad()
def gpu() -> None:
    t0 = time.time()
    from cmap9 import load
    model, tok = load("qwen")
    EN._MODEL["model"] = model
    C = make_c1forced(tok)
    sel = read_json(V41 / "results" / "selection_C1forced.json")
    wn = np.load(V41 / "cache" / "write_norms_C1forced.npy")
    pidx = sorted({i for ab in C.pairs for i in ab})
    acts = KC.collect_all(model, C, pidx)
    pairs = surviving_pairs(C, acts)
    clean = [c for c, _ in pairs]
    corrupt = [x for _, x in pairs]
    held = [i for i, p in enumerate(C.prompts) if p.get("heldout")]
    out: dict[str, Any] = {"n_pairs": len(pairs), "held": [C.prompts[i]["vid"] for i in held], "utc": utc_now()}
    # ---------------- 6.1 reproduction (exact exp41 job list for pair prompt 0)
    mc = KC.MeanCache(acts, C.prompts)
    i = 0
    p = C.prompts[i]
    opp, own = (corrupt, clean) if p["cls"] == "clean" else (clean, corrupt)
    sign = -1.0 if p["cls"] == "clean" else 1.0
    res0 = run_jobs(model, C, i, exp41_jobs(p, mc, opp, own, sel), sign)
    k0 = "mlp|L0|H-1|COND"
    d0 = res0[f"ablate|{k0}|node"] - float(np.mean([res0[f"ablate|{k0}|r{j}"] for j in range(N_RAND)]))
    ref_rows = read_jsonl(V41 / "data" / "validation_rows_C1forced.jsonl")
    ref0 = [r for r in ref_rows if r["prompt_idx"] == 0][0]["res"]
    diffs = [abs(res0[k] - ref0[k]) for k in res0 if k in ref0]
    tol_ok = abs(d0 - B3_TARGET_D) <= B3_TOL_EXACT
    out["repro_6_1"] = {"d": d0, "target": B3_TARGET_D, "abs_diff": abs(d0 - B3_TARGET_D), "pass_1e-3": tol_ok,
                        "pass_0.05": abs(d0 - B3_TARGET_D) <= B3_TOL_GPU, "n_job_values_compared": len(diffs),
                        "max_abs_diff_all_job_values": max(diffs), "median_abs_diff_all_job_values":
                        float(np.median(diffs))}
    logger.info(f"6.1 reproduction: d = {d0:.6f} vs {B3_TARGET_D} (|diff| {abs(d0 - B3_TARGET_D):.2e}); all "
                f"{len(diffs)} job values max |diff| {max(diffs):.4f}")
    if not tol_ok:
        log_deviation("b3_repro_tolerance", f"6.1 reproduction |diff| {abs(d0 - B3_TARGET_D):.4g} > 1e-3 "
                      f"({'<= 0.05: logged per the committed tolerance rule' if abs(d0 - B3_TARGET_D) <= 0.05 else '> 0.05'})")
    # ---------------- 6.2 the bug
    nodes = cond_nodes()
    span = {C.prompts[j]["vid"]: len(C.prompts[j]["pos"]["COND"]) for j in pidx + held}
    none_all = True
    bug = {}
    for j in held:
        q = C.prompts[j]
        o_, w_ = (corrupt, clean) if q["cls"] == "clean" else (clean, corrupt)
        for k in nodes:
            v = mc.get(o_, KC.parse_key(k), q)
            bug[f"{q['vid']}|{k}"] = v is None
            none_all &= v is None
    mca = MeanCacheAligned(acts, C.prompts, "aligned")
    shapes = {}
    for j in held:
        q = C.prompts[j]
        o_, _ = (corrupt, clean) if q["cls"] == "clean" else (clean, corrupt)
        v = mca.get(o_, KC.parse_key(k0), q)
        shapes[q["vid"]] = list(v.shape) if v is not None else None
    out["bug_6_2"] = {"cond_span_lengths": span, "original_get_none_on_all_heldout_cond": bool(none_all),
                      "n_checked": len(bug), "aligned_shapes_mlpL0": shapes}
    logger.info(f"6.2: original MeanCache.get None on all held-out COND nodes: {none_all}; aligned shapes {shapes}")
    tests = read_json(RESULTS_DIR / "tests_cpu.json")
    commit("commitB3", {"meancache_aligned_sha256": sha256_file(SRC / "meancache_aligned.py"),
                        "unit_tests": {k: tests[k] for k in ("interp_identity_max_abs", "interp_const_max_abs",
                                                             "interp_pass")},
                        "repro_6_1": out["repro_6_1"], "bug_6_2": {k: v for k, v in out["bug_6_2"].items()
                                                                   if k != "cond_span_lengths"},
                        "nodes": nodes, "modes": {"ablate": 1.0, "steer": STEER_DOSE,
                                                  "steer_sensitivity_posthoc": STEER_DOSE_SENS}})
    # ---------------- 6.5 held-out arm with the aligned means (+ sensitivities on the primary node)
    caches = {"aligned": mca, "span_mean": MeanCacheAligned(acts, C.prompts, "span_mean"),
              "exact_length": MeanCacheAligned(acts, C.prompts, "exact_length")}
    rand_meta = {}
    for j in held:
        q = C.prompts[j]
        o_, w_ = (corrupt, clean) if q["cls"] == "clean" else (clean, corrupt)
        sg = -1.0 if q["cls"] == "clean" else 1.0
        jobs = []
        for k in nodes:
            nd = KC.parse_key(k)
            rk, fac, src = random_for(k, sel, wn)
            rand_meta[k] = {"source": src, "n": len(rk), "n_distinct": len(set(rk))}
            modes = [("ablate", "ablate", 1.0, STEER_DOSE), ("steer", "steer", 1.0, STEER_DOSE),
                     ("steer05", "steer", 1.0, STEER_DOSE_SENS)]
            for cname, mcx in caches.items():
                if cname != "aligned" and k != k0:
                    continue
                for tag, mode, fct, dose in modes:
                    e = KC.val_edit(nd, q, mcx, o_, w_, mode, fct, dose)
                    jobs.append(((cname, tag, k, "node"), [e] if e else []))
                    for r, (rkk, ff) in enumerate(zip(rk, fac)):
                        e = KC.val_edit(KC.parse_key(rkk), q, mcx, o_, w_, mode, ff, dose)
                        jobs.append(((cname, tag, k, f"r{r}"), [e] if e else []))
        tq = time.time()
        res = run_jobs(model, C, j, jobs, sg)
        n_empty = sum(1 for _, e in jobs if not e)
        append_jsonl(ROWS_FILE, [{"prompt_idx": j, "vid": q["vid"], "side": q["cls"], "res": res,
                                  "n_jobs": len(jobs), "n_empty_edits": n_empty, "utc": utc_now()}])
        logger.info(f"held-out {q['vid']}: {len(jobs)} jobs ({n_empty} empty) in {time.time() - tq:.1f}s")
    out["random_meta"] = rand_meta
    write_json(RESULTS_DIR / "b3_gpu.json", out)
    stage_time("b3_gpu", time.time() - t0)


def analyze() -> dict[str, Any]:
    rows = read_jsonl(ROWS_FILE)
    g = read_json(RESULTS_DIR / "b3_gpu.json")
    s41 = read_json(V41 / "results" / "summary.json")["validation"]["C1forced"]["per_node"]
    pair_vals = {m: {r["node"]: r for r in s41[m]} for m in s41}
    nodes = cond_nodes()
    out: dict[str, Any] = {"repro_6_1": g["repro_6_1"], "bug_6_2": g["bug_6_2"], "random_meta": g["random_meta"],
                           "per_node": {}, "n_heldout_prompts": len(rows)}
    for cname in ("aligned", "span_mean", "exact_length"):
        for tag in ("ablate", "steer", "steer05"):
            for k in nodes:
                d, beaten, vnode = [], [], []
                for r in rows:
                    v = r["res"].get(f"{cname}|{tag}|{k}|node")
                    rv = [r["res"][f"{cname}|{tag}|{k}|r{j}"] for j in range(N_RAND)
                          if f"{cname}|{tag}|{k}|r{j}" in r["res"]]
                    if v is None or not rv:
                        continue
                    d.append(v - float(np.mean(rv)))
                    beaten.append(float(np.mean(np.asarray(rv) < v)))
                    vnode.append(v)
                if not d:
                    continue
                pv = pair_vals.get("ablate" if tag == "ablate" else "steer", {}).get(k, {})
                out["per_node"][f"{cname}|{tag}|{k}"] = {
                    "variant": cname, "mode": tag, "node": k, "n": len(d), "mean_d_heldout": float(np.mean(d)),
                    "d_per_prompt": d, "p_sign_flip_heldout": S.sign_flip_p(d),
                    "frac_random_beaten_heldout": float(np.mean(beaten)), "mean_dm_node_oriented": float(np.mean(vnode)),
                    "exp41_mean_d_pair_prompts": pv.get("mean_d_pair_prompts") if tag != "steer05" else None,
                    "exp41_mean_d_heldout": pv.get("mean_d_heldout") if tag != "steer05" else None,
                    "label": "post-hoc sensitivity" if (tag == "steer05" or cname != "aligned") else "committed"}
    prim = [v for kk, v in out["per_node"].items() if kk.startswith("aligned|") and v["mode"] in ("ablate", "steer")]
    adj = S.holm([v["p_sign_flip_heldout"] for v in prim])
    for v, a in zip(prim, adj):
        v["p_holm_within_b3_family"] = a
    out["motif"] = motif()
    write_json(RESULTS_DIR / "b3_summary.json", out)
    return out


def motif() -> dict[str, Any]:
    """Kind-matched motif comparison (CPU)."""
    g = read_json(V38 / "results" / "g1_pathpatch.json")
    gx = g["exact"]
    n_g = len(gx[0]["noise_per_pair"])
    kinds = ["natural" if j < 10 else "forced" for j in range(n_g)]
    pairs_meta = g.get("pairs") or []
    out: dict[str, Any] = {"gemma_pair_kinds": kinds, "gemma_pairs_meta_head": pairs_meta[:3],
                           "mapping_note": "g1_pathpatch.json pairs 0-9 are the natural (noun-variant) contrast and "
                                           "10-14 the forced contrast (iteration-8 analysis.motif_test convention); "
                                           "Gemma classes FORK->DEC, CSTAR->OPEN"}
    gem = {"natural": KM.motif(gx, [j for j in range(n_g) if kinds[j] == "natural"], class_map=KM.G2Q),
           "forced": KM.motif(gx, [j for j in range(n_g) if kinds[j] == "forced"], class_map=KM.G2Q)}
    gdep = {"natural": KM.dec_stack_depth(gx, [j for j in range(n_g) if kinds[j] == "natural"], 15, 34,
                                          class_map=KM.G2Q),
            "forced": KM.dec_stack_depth(gx, [j for j in range(n_g) if kinds[j] == "forced"], 15, 34,
                                         class_map=KM.G2Q)}
    q = {}
    for name, kind in (("C1nat", "natural"), ("C1forced", "forced")):
        r = read_json(V41 / "results" / f"circuit_{name}.json")
        prim = [e for e in r["exact"] if e["in_top40_atp"] or e["calibration"]]
        idx = list(range(r["n_pairs"]))
        sh = KM.motif(prim, idx)
        dep = KM.dec_stack_depth(prim, idx, 15, 36)
        q[kind] = {"contrast": name, "shares": sh, "dec_stack": dep, "label_vs_bands": KM.label(sh, dep["depth"]),
                   "signed": KM.motif(prim, idx, signed=True)}
    comp = {}
    for kind in ("natural", "forced"):
        comp[kind] = {"qwen": q[kind]["shares"], "gemma": gem[kind], "qwen_dec_depth": q[kind]["dec_stack"]["depth"],
                      "gemma_dec_depth": gdep[kind]["depth"],
                      "abs_diff": {c: abs(q[kind]["shares"][c] - gem[kind][c]) for c in ("COND", "SPEC", "OPEN",
                                                                                         "DEC")},
                      "qwen_label_vs_bands": q[kind]["label_vs_bands"]}
    out.update({"qwen": q, "gemma": gem, "gemma_dec_stack": gdep, "kind_matched": comp})
    return out


if __name__ == "__main__":
    setup_logging(f"b3_9_{sys.argv[1]}")
    if sys.argv[1] == "gpu":
        gpu()
    elif sys.argv[1] == "analyze":
        analyze()
    else:
        write_json(RESULTS_DIR / "b3_motif.json", motif())
