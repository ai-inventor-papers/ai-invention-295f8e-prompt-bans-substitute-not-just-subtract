#!/usr/bin/env python3
"""S8 analysis: applies the committed B2 rules (share, Q1-Q3, verdict, localisation) to the per-prompt CMAP rows and
collects the B1 / B3 summaries. Also: random-null percentiles, single-component ranks, Jaccard, interaction, placebos,
identity, W and REV arms, basis alignment, and a CPU readout decomposition (final norm + unembedding, from safetensors).
Writes results/b2_summary.json and results/summary.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

import stats9 as S
from cfg9 import (FSTACK, N_BOOT, N_LAYERS, N_HEADS, RESULTS_DIR, RS_LAYERS, SEED_BOOT, THRESH, model_path,
                  read_json, read_jsonl, setup_logging, utc_now, verify_chain, write_json)

UNITS = ("B3", "T10")


def rows_by_arm(u: str, path: Path | None = None) -> tuple[list[str], dict[str, dict[str, float]], dict, dict]:
    rows = read_jsonl(path or RESULTS_DIR / f"b2_tf_{u}.jsonl")
    pids = []
    by: dict[str, dict[str, float]] = {}
    mI, mB = {}, {}
    for r in rows:
        if r["pid"] not in mI:
            pids.append(r["pid"])
            mI[r["pid"]] = r["m_I"]
            mB[r["pid"]] = r["m_B"]
        by.setdefault(r["arm"], {})[r["pid"]] = r["m"]
    return pids, by, mI, mB


def share_of(arm: dict[str, float], pids: list[str], mI: dict, mB: dict) -> float:
    ps = [p for p in pids if p in arm]
    return S.share([mI[p] for p in ps], [arm[p] for p in ps], [mB[p] for p in ps])


def arm_stats(arm: dict[str, float], pids: list[str], mI: dict, mB: dict, boot: bool = True) -> dict[str, Any]:
    ps = [p for p in pids if p in arm]
    a = [mI[p] for p in ps]
    x = [arm[p] for p in ps]
    b = [mB[p] for p in ps]
    out = {"share": S.share(a, x, b), "share_mean_of_ratios": S.share_mean_of_ratios(a, x, b), "n": len(ps),
           "per_prompt_share": [(ai - xi) / (ai - bi) if abs(ai - bi) > 1e-9 else None for ai, xi, bi in zip(a, x, b)]}
    if boot:
        out["share_ci95"] = S.boot_share_ci(a, x, b, N_BOOT, SEED_BOOT)
    return out


def readout_decomposition(u: str) -> dict[str, Any] | None:
    """m of the BASE final-norm input read with (instruct norm, instruct unembedding), (base norm, instruct
    unembedding), (instruct norm, base unembedding) and (base, base), from the cached base residuals (CPU)."""
    try:
        import torch
        from safetensors import safe_open
    except ImportError:
        return None
    U = read_json(RESULTS_DIR / "units.json")[u]["forks"][0]
    rows = U["D"] + U["A"]
    nD = len(U["D"])
    W = {}
    for key in ("qwen", "qwen_base"):
        p = Path(model_path(key))
        idx = json.loads((p / "model.safetensors.index.json").read_text())["weight_map"]
        W[key] = {}
        for name, tag in (("lm_head.weight", "U"), ("model.norm.weight", "g")):
            with safe_open(str(p / idx[name]), framework="pt") as fh:
                if tag == "U":
                    sl = fh.get_slice(name)
                    W[key][tag] = torch.stack([sl[r:r + 1][0] for r in rows]).float()
                else:
                    W[key][tag] = fh.get_tensor(name).float()
    cfg = json.loads((Path(model_path("qwen")) / "config.json").read_text())
    eps = cfg.get("rms_norm_eps", 1e-6)
    cb = torch.load(Path(RESULTS_DIR.parent / "cache" / f"base_{u}.pt"))
    ci = torch.load(Path(RESULTS_DIR.parent / "cache" / f"instr_{u}.pt"))

    def m_of(resid, g, Uw):
        x = resid.float()
        h = x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + eps)
        h = (h.to(torch.bfloat16).float() * g).to(torch.bfloat16).float()
        z = h @ Uw.T
        return float(torch.logsumexp(z[:nD], 0) - torch.logsumexp(z[nD:], 0))
    out = {k: [] for k in ("base_resid|instr_norm|instr_U", "base_resid|base_norm|instr_U",
                           "base_resid|instr_norm|base_U", "base_resid|base_norm|base_U",
                           "instr_resid|instr_norm|instr_U", "instr_resid|base_norm|base_U")}
    for a, b in zip(ci["caps"], cb["caps"]):
        rb = (b.get("ot") or b)["resid"][N_LAYERS]
        ra = (a.get("ot") or a)["resid"][N_LAYERS]
        out["base_resid|instr_norm|instr_U"].append(m_of(rb, W["qwen"]["g"], W["qwen"]["U"]))
        out["base_resid|base_norm|instr_U"].append(m_of(rb, W["qwen_base"]["g"], W["qwen"]["U"]))
        out["base_resid|instr_norm|base_U"].append(m_of(rb, W["qwen"]["g"], W["qwen_base"]["U"]))
        out["base_resid|base_norm|base_U"].append(m_of(rb, W["qwen_base"]["g"], W["qwen_base"]["U"]))
        out["instr_resid|instr_norm|instr_U"].append(m_of(ra, W["qwen"]["g"], W["qwen"]["U"]))
        out["instr_resid|base_norm|base_U"].append(m_of(ra, W["qwen_base"]["g"], W["qwen_base"]["U"]))
    mI = np.array(out["instr_resid|instr_norm|instr_U"])
    mB = np.array(out["base_resid|base_norm|base_U"])
    gap = float((mI - mB).sum())
    res = {k: float(np.mean(v)) for k, v in out.items()}
    res["share_residual_swap_under_instr_readout"] = float((mI - np.array(out["base_resid|instr_norm|instr_U"])).sum()
                                                           / gap)
    res["share_readout_swap_on_base_resid"] = float((np.array(out["base_resid|instr_norm|instr_U"]) - mB).sum() / gap)
    res["share_unembedding_only"] = float((np.array(out["base_resid|base_norm|instr_U"]) - mB).sum() / gap)
    res["share_norm_only"] = float((np.array(out["base_resid|instr_norm|base_U"]) - mB).sum() / gap)
    res["note"] = ("fp32 CPU recomputation from cached final-norm inputs; 'share_residual_swap_under_instr_readout' "
                   "is the CPU analogue of RS-fork(36); the two parts sum to 1 by construction")
    return res


def b2_unit(u: str, ui: int) -> dict[str, Any]:
    pids, by, mI, mB = rows_by_arm(u)
    gap = [mI[p] - mB[p] for p in pids]
    out: dict[str, Any] = {"unit": u, "n_prompts": len(pids), "m_I": [mI[p] for p in pids],
                           "m_B": [mB[p] for p in pids], "gap_mean": float(np.mean(gap)),
                           "gap_ci95": S.boot_mean_ci(gap, N_BOOT, SEED_BOOT)}
    arms = {}
    for name in ("FSTACK", "F_MLP", "F_HEAD", "F_MST", "F_CC", "SPEC", "self_FSTACK", "xprompt_FSTACK", "ALL_attn",
                 "ALL_heads", "W_all", "W26", "W27", "W28", "W30", "W32"):
        if name in by:
            arms[name] = arm_stats(by[name], pids, mI, mB)
    out["arms"] = arms
    # random nulls
    for fam_, n in (("R", 50), ("Rpure", 50), ("Rscaled", 50), ("SPECR", 20)):
        sh = [share_of(by[f"{fam_}{s}"], pids, mI, mB) for s in range(n) if f"{fam_}{s}" in by]
        if not sh:
            continue
        ref = arms["SPEC"]["share"] if fam_ == "SPECR" else arms["FSTACK"]["share"]
        out[f"null_{fam_}"] = {"shares": sh, "median": float(np.median(sh)), "p95": float(np.percentile(sh, 95)),
                               "max": float(np.max(sh)), "empirical_p_upper": S.empirical_p_upper(ref, sh),
                               "frac_below_ref": float(np.mean(np.asarray(sh) < ref))}
    # RS curves
    out["RS_fork"] = {l: share_of(by[f"RSfork{l}"], pids, mI, mB) for l in range(N_LAYERS + 1) if f"RSfork{l}" in by}
    out["RS_prefix"] = {l: share_of(by[f"RSprefix{l}"], pids, mI, mB) for l in RS_LAYERS if f"RSprefix{l}" in by}
    out["RS_all"] = {l: share_of(by[f"RSall{l}"], pids, mI, mB) for l in RS_LAYERS if f"RSall{l}" in by}
    # singles
    singles = {}
    for l in range(N_LAYERS):
        k = f"mlp|L{l}"
        if k in by:
            singles[k] = share_of(by[k], pids, mI, mB)
        for h in range(N_HEADS):
            k = f"head|L{l}|H{h}"
            if k in by:
                singles[k] = share_of(by[k], pids, mI, mB)
    out["singles"] = singles
    top10 = sorted(singles, key=lambda k: -singles[k])[:10]
    out["singles_top10"] = [(k, singles[k]) for k in top10]
    out["jaccard_top10_vs_FSTACK"] = len(set(top10) & set(FSTACK)) / len(set(top10) | set(FSTACK))
    ranks = {}
    for k in FSTACK:
        same = [v for kk, v in singles.items() if kk.split("|")[0] == k.split("|")[0]]
        ranks[k] = {"share": singles.get(k), "pctile_among_same_type": float(np.mean(np.asarray(same) < singles[k])
                                                                              * 100) if k in singles else None,
                    "rank": int(1 + sum(v > singles[k] for v in same)) if k in singles else None,
                    "n_same_type": len(same)}
    out["fstack_single_ranks"] = ranks
    out["sum_singles_FSTACK"] = float(sum(singles.get(k, 0.0) for k in FSTACK))
    out["interaction_FSTACK_minus_sum_singles"] = arms["FSTACK"]["share"] - out["sum_singles_FSTACK"]
    out["singles_mlp_total"] = float(sum(v for k, v in singles.items() if k.startswith("mlp")))
    out["singles_head_total"] = float(sum(v for k, v in singles.items() if k.startswith("head")))
    # placebos / identity
    out["self_patch_max_abs_dm"] = float(max(abs(by["self_FSTACK"][p] - mI[p]) for p in pids))
    out["identity_heads_minus_RS36_max_abs"] = float(max(abs(by["ALL_heads"][p] - by["RSfork36"][p]) for p in pids))
    out["identity_attn_minus_RS36_max_abs"] = float(max(abs(by["ALL_attn"][p] - by["RSfork36"][p]) for p in pids))
    if "full_none" in by:
        out["onetok_minus_full_unpatched_mean"] = float(np.mean([mI[p] - by["full_none"][p] for p in pids]))
    # REV arm
    rev = read_jsonl(RESULTS_DIR / f"b2_rev_{u}.jsonl")
    if rev:
        rb: dict[str, dict[str, float]] = {}
        for r in rev:
            rb.setdefault(r["arm"], {})[r["pid"]] = r["m"]
        base_none = rb["none"]

        def opened(arm):
            ps = [p for p in pids if p in arm]
            return float(sum(arm[p] - base_none[p] for p in ps) / sum(mI[p] - mB[p] for p in ps))
        rr = [opened(rb[f"R{s}"]) for s in range(50) if f"R{s}" in rb]
        out["REV"] = {"share_opened_FSTACK": opened(rb["FSTACK"]), "share_opened_F_MLP": opened(rb["F_MLP"]),
                      "share_opened_F_HEAD": opened(rb["F_HEAD"]),
                      "share_opened_RS36_instr_resid_in_base": opened(rb["RS36_instr"]),
                      "null_R_median": float(np.median(rr)) if rr else None,
                      "null_R_p95": float(np.percentile(rr, 95)) if rr else None,
                      "empirical_p_upper": S.empirical_p_upper(opened(rb["FSTACK"]), rr) if rr else None,
                      "base_anchor_drift_max": float(max(abs(base_none[p] - mB[p]) for p in pids))}
    # committed rules
    fs = arms["FSTACK"]["share"]
    rs = out["RS_fork"]
    out["Q1"] = fs >= THRESH["B2_Q1_share"]
    out["Q2"] = (out["null_R"]["median"] <= THRESH["B2_Q2_median_random"] and fs > out["null_R"]["p95"])
    out["Q3"] = arms["SPEC"]["share"] <= THRESH["B2_Q3_spec"] if "SPEC" in arms else None
    rp23 = out["RS_prefix"].get(23)
    if rp23 is not None and rp23 >= THRESH["B2_upstream_rs_prefix23"]:
        loc = "written upstream"
    elif rs.get(36) is not None and rs.get(23) is not None and rs[36] - rs[23] >= THRESH["B2_late_rs_gap"] and \
            fs <= THRESH["B2_disconfirm_share"]:
        loc = "written at the fork by other late components"
    else:
        loc = "distributed"
    out["localisation"] = loc
    # supplementary (labelled): FSTACK share relative to the residual-available share RS-fork(36)
    out["supp_FSTACK_over_RS36"] = fs / rs[36] if rs.get(36) not in (None, 0) else None
    try:
        out["readout_decomposition_cpu"] = readout_decomposition(u)
    except (OSError, KeyError, RuntimeError, ValueError) as e:
        logger.warning(f"readout decomposition failed for {u}: {e}")
        out["readout_decomposition_cpu"] = None
    rsets = read_json(RESULTS_DIR / "random_sets.json")[u]
    out["random_set_meta"] = {"R": rsets["R"]["meta"], "R_n_distinct_sets": rsets["R"]["n_distinct_sets"],
                              "Rpure_n_distinct_sets": rsets["Rpure"]["n_distinct_sets"],
                              "basis_alignment": rsets.get("basis_alignment")}
    sp = RESULTS_DIR / f"spec_random_sets_{u}.json"
    if sp.exists():
        s_ = read_json(sp)
        out["spec_random_set_meta"] = {"meta": s_["meta"], "n_distinct_sets": s_["n_distinct_sets"]}
    gt = RESULTS_DIR / "gpu_tests_b2.json"
    if gt.exists():
        out["gpu_tests"] = read_json(gt).get(u)
    return out


def b2() -> dict[str, Any]:
    res = {u: b2_unit(u, i) for i, u in enumerate(UNITS)}
    q1 = all(res[u]["Q1"] for u in UNITS)
    q2 = all(res[u]["Q2"] for u in UNITS)
    q3 = all(bool(res[u]["Q3"]) for u in UNITS)
    disc = all(res[u]["arms"]["FSTACK"]["share"] <= THRESH["B2_disconfirm_share"] for u in UNITS)
    verdict = "SUPPORTED" if (q1 and q2 and q3) else ("DISCONFIRMED" if disc else "PARTIAL")
    out = {"units": res, "Q1_both": q1, "Q2_both": q2, "Q3_both": q3, "verdict": verdict, "utc": utc_now()}
    # v1 (variable batch shape) sensitivity, if archived
    v1 = {}
    for u in UNITS:
        p = RESULTS_DIR / "v1_variable_batch" / f"b2_tf_{u}.jsonl"
        if p.exists():
            pids, by, mI, mB = rows_by_arm(u, p)
            sh = [share_of(by[f"R{s}"], pids, mI, mB) for s in range(50) if f"R{s}" in by]
            v1[u] = {"FSTACK": share_of(by["FSTACK"], pids, mI, mB), "RSfork36": share_of(by["RSfork36"], pids, mI, mB),
                     "RSfork23": share_of(by["RSfork23"], pids, mI, mB), "SPEC": share_of(by["SPEC"], pids, mI, mB),
                     "R_median": float(np.median(sh)) if sh else None,
                     "self_patch_max_abs_dm": float(max(abs(by["self_FSTACK"][p] - mI[p]) for p in pids)),
                     "note": "v1 = variable batch shapes and full-forward caches (superseded; sensitivity only)"}
    out["v1_variable_batch_sensitivity"] = v1
    write_json(RESULTS_DIR / "b2_summary.json", out)
    logger.info(f"B2 verdict {verdict}: " + "; ".join(
        f"{u}: FSTACK {res[u]['arms']['FSTACK']['share']:.3f} (R median {res[u]['null_R']['median']:.3f}, p95 "
        f"{res[u]['null_R']['p95']:.3f}), SPEC {res[u]['arms'].get('SPEC', {}).get('share', float('nan')):.3f}, "
        f"RS36 {res[u]['RS_fork'].get(36, float('nan')):.3f}, loc {res[u]['localisation']}" for u in UNITS))
    return out


def summary() -> dict[str, Any]:
    out: dict[str, Any] = {"utc": utc_now()}
    for name in ("b1_summary", "b2_summary", "b3_summary"):
        p = RESULTS_DIR / f"{name}.json"
        out[name] = read_json(p) if p.exists() else None
    out["commit_chain"] = verify_chain()
    p = RESULTS_DIR / "deviations.json"
    out["deviations"] = read_json(p) if p.exists() else []
    write_json(RESULTS_DIR / "summary.json", out)
    return out


if __name__ == "__main__":
    setup_logging("analysis9")
    b2()
    summary()
