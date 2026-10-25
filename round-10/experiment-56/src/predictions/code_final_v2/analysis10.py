#!/usr/bin/env python3
"""Cross-claim analysis and the run summary.

  delta_geometry  why same-norm edits aimed at the residual subspace (RAND_RESID) out-lever the real row deltas: for each
                  fork-class token t, the fraction of ||Delta_t||^2 inside the top-64 principal subspace of the instruct
                  final-normed residual, and the logit leverage |h . Delta_t| / (||h|| ||Delta_t||) of the real delta
                  vs the RAND_ISO / RAND_RESID draws (results/delta_geometry.json)
  summary         every verdict, headline number, deviation and cost in one file (results/summary.json)
"""

from __future__ import annotations

import sys
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg10 import (CACHE_DIR, I9_RES, RESULTS_DIR, UNITS_TF, read_json, setup_logging, utc_now, verify_chain,
                   write_json)
from w1_tf import UnitData, load_readout


def delta_geometry() -> dict[str, Any]:
    units = read_json(I9_RES / "units.json")
    WI, gI = load_readout("qwen")
    WB, gB = load_readout("qwen_base")
    out: dict[str, Any] = {"utc": utc_now(), "units": {}}
    for u in UNITS_TF:
        d = UnitData(u, units, WI, WB, gI, gB, need_logits=False)
        pca = torch.load(CACHE_DIR / f"resid_pca_{u}.pt")
        V = pca["basis"].double()                                        # [64, d]
        nul = np.load(RESULTS_DIR / f"null_draws_{u}.npz")
        h = d.hfI.double()
        hn = h.norm(dim=-1, keepdim=True)
        rec = {}
        for j, t in enumerate(d.S):
            dl = d.Delta[j].double()
            frac = float((V @ dl).pow(2).sum() / dl.pow(2).sum())
            lev = (h @ dl).abs() / (hn[:, 0] * dl.norm())
            lev_iso = [float(((h @ torch.from_numpy(nul["RAND_ISO"][k, j]).double()).abs() /
                              (hn[:, 0] * dl.norm())).mean()) for k in range(nul["RAND_ISO"].shape[0])]
            lev_res = [float(((h @ torch.from_numpy(nul["RAND_RESID"][k, j]).double()).abs() /
                              (hn[:, 0] * dl.norm())).mean()) for k in range(nul["RAND_RESID"].shape[0])]
            lev_swp = [float(((h @ torch.from_numpy(nul["DELTA_SWAP"][k, j]).double()).abs() /
                              (hn[:, 0] * torch.from_numpy(nul["DELTA_SWAP"][k, j]).double().norm())).mean())
                       for k in range(nul["DELTA_SWAP"].shape[0])]
            rec[str(t)] = {"class": "D" if j < d.nD else "A", "delta_norm": float(dl.norm()),
                           "frac_delta_energy_in_resid_pc64": frac,
                           "frac_expected_isotropic": 64 / dl.numel(),
                           "leverage_real_mean": float(lev.mean()), "leverage_rand_iso_median": float(np.median(lev_iso)),
                           "leverage_rand_resid_median": float(np.median(lev_res)),
                           "leverage_delta_swap_median": float(np.median(lev_swp)),
                           "signed_logit_change_mean": float((h @ dl).mean())}
        out["units"][u] = {"tokens": rec, "resid_pc64_var_explained": pca["var_explained_top64"]}
        logger.info(f"{u}: " + "; ".join(f"{t}: frac {v['frac_delta_energy_in_resid_pc64']:.3f} lev "
                                         f"{v['leverage_real_mean']:.4f} (iso {v['leverage_rand_iso_median']:.4f}, "
                                         f"resid {v['leverage_rand_resid_median']:.4f}, swap "
                                         f"{v['leverage_delta_swap_median']:.4f})" for t, v in list(rec.items())[:4]))
    write_json(RESULTS_DIR / "delta_geometry.json", out)
    return out


def summary() -> dict[str, Any]:
    s0 = read_json(RESULTS_DIR / "stage0.json")
    w1 = read_json(RESULTS_DIR / "w1_tf_summary.json")
    gen = read_json(RESULTS_DIR / "w1_generation.json")
    w2 = read_json(RESULTS_DIR / "w2_summary.json") if (RESULTS_DIR / "w2_summary.json").exists() else None
    w3 = read_json(RESULTS_DIR / "w3_summary.json") if (RESULTS_DIR / "w3_summary.json").exists() else None
    dev = read_json(RESULTS_DIR / "deviations.json") if (RESULTS_DIR / "deviations.json").exists() else []
    red = read_json(RESULTS_DIR / "rederive.json") if (RESULTS_DIR / "rederive.json").exists() else {}
    out: dict[str, Any] = {"utc": utc_now(), "claims": {}}
    out["S0"] = {u: {"mean_m_I": s0["units"][u]["mean_m_I"], "mean_m_I_iter9": s0["units"][u]["mean_m_I_iter9"],
                     "mean_m_B": s0["units"][u]["mean_m_B"], "mean_m_B_iter9": s0["units"][u]["mean_m_B_iter9"],
                     "gap_mean": s0["units"][u]["gap_mean"], "gap_ci95": s0["units"][u]["gap_ci95"],
                     "max_per_prompt_abs_diff_I": s0["units"][u]["max_per_prompt_abs_diff_I"],
                     "spearman_I": s0["units"][u]["spearman_I"],
                     "decomposition_unembedding_only": s0["units"][u]["readout_decomposition_cpu"][
                         "share_unembedding_only"],
                     "pass": s0["units"][u]["pass"]} for u in UNITS_TF}
    for u in UNITS_TF:
        U = w1["units"][u]
        out["claims"][f"W1_TF_{u}"] = {
            "role": U["verdict_role"], "verdict": U["verdict"], "qualifier": U["specificity_qualifier"],
            "shares": {a: U["arms"][a]["share"] for a in ("ROWS_ALL", "ROWS_D", "ROWS_A", "NORM", "ROWS_NORM",
                                                         "FULL_UNEMB", "SIGN")},
            "ROWS_ALL_ci95": U["arms"]["ROWS_ALL"]["ci95"],
            "dose": {k: U["arms"][k]["share"] for k in U["arms"] if k.startswith("DOSE_")},
            "nulls": {k: {kk: U["nulls"][k][kk] for kk in ("median", "p95", "max", "empirical_p_rows_all")}
                      for k in U["nulls"]}, "factorial_2x2": {k: v for k, v in U["factorial_2x2"].items()
                                                               if k != "interaction_per_prompt"}}
        G = gen["units"].get(u)
        if G:
            out["claims"][f"W1_GEN_{u}"] = {
                "role": G["verdict_role"], "verdict": G["verdict"],
                "correct_of_30": {a: G["cells"][a]["n_correct"] for a in G["cells"]},
                "predicted_correct_of_30": {a: G["cells"][a]["predicted_correct_count"] for a in G["cells"]},
                "pass_of_30": {a: G["cells"][a]["n_pass"] for a in G["cells"]},
                "tests": {k: {kk: v.get(kk) for kk in ("b_first_only", "c_second_only", "p_exact_two_sided",
                                                       "p_holm_primary")} for k, v in G["tests"].items() if "|" not in k}}
        if w2:
            W = w2["units"][u]
            out["claims"][f"W2_{u}"] = {"role": W["rule_role"], "rule": W["rule"], "decomposition": W["decomposition"],
                                        "bridge_iter9": W["bridge_iter9"],
                                        "singles_top3": W["singles_ranked"][:3]}
    if w3:
        out["claims"]["W3_G-GRID"] = {"role": "descriptive", "gap": w3["gap_mean"],
                                      "shares": {a: w3["arms"][a]["share"] for a in w3["arms"]},
                                      "nulls": {k: {kk: w3["nulls"][k][kk] for kk in ("median", "p95", "max")}
                                                for k in w3["nulls"]}, "reproduction_b1": w3["reproduction_b1"]}
    pw_p = RESULTS_DIR / "w1_generation_power.json"
    if pw_p.exists():
        pw = read_json(pw_p)
        out["claims"]["W1_GEN_power_extension"] = {
            "role": "descriptive extension (COMMIT #7)",
            "units": {u: {"pooled_90_correct": {a: pw["units"][u]["cells"][a]["n_correct"] for a in ("TWIN", "ROWS",
                                                                                                  "RAND_MED")},
                          "tests": pw["units"][u]["tests"], "predicted": pw["units"][u]["predicted"]}
                      for u in pw["units"]}}
    out["audit"] = {"n_checks": red.get("n_checks"), "n_mismatches": red.get("n_mismatches"),
                    "placebos": {k: red.get(k) for k in ("P1_noise_placebo", "P3_DA_shuffle_placebo")}}
    out["commitment_chain"] = verify_chain()
    out["deviations"] = dev
    out["openrouter_spend_usd"] = 0.0
    write_json(RESULTS_DIR / "summary.json", out)
    logger.info(f"summary written: {list(out['claims'])}")
    return out


if __name__ == "__main__":
    setup_logging(f"analysis10_{sys.argv[1]}")
    {"delta_geometry": delta_geometry, "summary": summary}[sys.argv[1]]()
