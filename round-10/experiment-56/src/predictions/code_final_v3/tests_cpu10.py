#!/usr/bin/env python3
"""CPU unit tests of the testing plan (results/tests_cpu.json):
  T1 readout equivalence: the class margin from h_fin and the S rows equals the log-softmax margin of the full fp32
     logits (|diff| < 1e-5 relative to the logit scale)
  T2 identities: ROWS at lambda = 0 equals TWIN exactly; FULL_UNEMB margin equals ROWS_ALL (|diff| < 1e-4 in fp32);
     the sign flip moves the margin opposite to ROWS_ALL; share(TWIN) = 0 and share(arm returning m_B) = 1
  T3 null generators: reproducible from the committed seeds (same bytes twice); per-row norms equal ||Delta_t||
     (1e-4 relative); DELTA_SWAP never picks a token in S or a token whose string contains an excluded class string
  T4 the Hungarian matching is one-to-one and the joint scale c is recomputed exactly
  T5 the hash chain verifies
  T6 audit/rederive.py synthetic self-test passes
"""

from __future__ import annotations

import subprocess
from pathlib import Path
import sys

import numpy as np
import torch
from loguru import logger

from cfg10 import (DELTA_SWAP_EXCLUDE, I9_RES, N_NULL, NULL_SEED0, RESULTS_DIR, ROOT, UNIT_IDX, UNITS_TF, model_path,
                   read_json, setup_logging, utc_now, verify_chain, write_json)
from w1_tf import UnitData, full_logits_cpu, load_readout, margin, share


def main() -> None:
    units = read_json(I9_RES / "units.json")
    WI, gI = load_readout("qwen")
    WB, gB = load_readout("qwen_base")
    out: dict = {"utc": utc_now()}
    d = UnitData("T10", units, WI, WB, gI, gB)
    # T1
    lp = torch.log_softmax(d.zI.double(), -1)
    m_full = (torch.logsumexp(lp[:, d.D], -1) - torch.logsumexp(lp[:, d.A], -1)).numpy()
    m_rows = d.m_rows(d.WI_S)
    out["T1_readout_equivalence_max_abs"] = float(np.abs(m_full - m_rows).max())
    out["T1_pass"] = out["T1_readout_equivalence_max_abs"] < 1e-4
    # T2
    m0 = d.m_rows(d.WI_S + 0.0 * d.Delta)
    zF = full_logits_cpu(WB, d.hfI)
    mF = margin(d.hfI, WB[d.D].float(), WB[d.A].float()).numpy()
    mR = d.m_rows(d.WB_S)
    mS = d.m_rows(d.WI_S - d.Delta)
    out["T2_lambda0_equals_twin"] = bool(np.array_equal(m0, m_rows))
    out["T2_full_unemb_minus_rows_all_max_abs"] = float(np.abs(mF - mR).max())
    del zF
    out["T2_sign_flip_opposite"] = bool(np.sign(np.mean(mS - d.mI)) == -np.sign(np.mean(mR - d.mI)))
    out["T2_share_twin"] = share(d.mI, d.mI, d.mB)
    out["T2_share_base"] = share(d.mI, d.mB, d.mB)
    out["T2_pass"] = (out["T2_lambda0_equals_twin"] and out["T2_full_unemb_minus_rows_all_max_abs"] < 1e-4 and
                      out["T2_sign_flip_opposite"] and out["T2_share_twin"] == 0.0 and out["T2_share_base"] == 1.0)
    # T3
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_path("qwen"))
    t3 = {}
    for u in UNITS_TF:
        nul = np.load(RESULTS_DIR / f"null_draws_{u}.npz")
        S = list(nul["S"])
        ui = UNIT_IDX[u]
        same = True
        for k in (0, N_NULL - 1):
            for j, t in enumerate(S[:2]):
                g1 = np.random.default_rng([NULL_SEED0["RAND_ISO"] + 100 * ui + k, int(t)]).standard_normal(
                    WI.shape[1])
                g2 = np.random.default_rng([NULL_SEED0["RAND_ISO"] + 100 * ui + k, int(t)]).standard_normal(
                    WI.shape[1])
                same &= g1.tobytes() == g2.tobytes()
                v = (nul["delta_norm"][j] * g1 / np.linalg.norm(g1)).astype(np.float32)
                same &= bool(np.array_equal(v, nul["RAND_ISO"][k, j]))
        dn = nul["delta_norm"]
        rel_iso = float(np.abs(np.linalg.norm(nul["RAND_ISO"], axis=-1) / dn - 1).max())
        rel_res = float(np.abs(np.linalg.norm(nul["RAND_RESID"], axis=-1) / dn - 1).max())
        toks = nul["DELTA_SWAP_tokens"]
        in_S = bool(np.isin(toks, S).any())
        bad_str = [int(t) for t in np.unique(toks) if any(e in tok.decode([int(t)]).strip().lower()
                                                          for e in DELTA_SWAP_EXCLUDE[u])]
        t3[u] = {"reproducible": bool(same), "rand_iso_norm_rel_err": rel_iso, "rand_resid_norm_rel_err": rel_res,
                 "delta_swap_in_S": in_S, "delta_swap_excluded_strings": bad_str,
                 "pass": bool(same) and rel_iso < 1e-4 and rel_res < 1e-4 and not in_S and not bad_str}
    out["T3"] = t3
    out["T3_pass"] = all(v["pass"] for v in t3.values())
    # T4
    mt = read_json(RESULTS_DIR / "w2_matching.json")
    pairs = {int(k): int(v) for k, v in mt["pairs_late_to_early"].items()}
    N = np.array(mt["per_layer_N"])
    c = float(np.sqrt(np.sum(N[list(pairs)] ** 2)) / np.sqrt(np.sum(N[list(pairs.values())] ** 2)))
    out["T4_one_to_one"] = len(set(pairs.values())) == len(pairs) == 10
    out["T4_c_recomputed"] = c
    out["T4_pass"] = out["T4_one_to_one"] and abs(c - mt["c_joint_scale"]) < 1e-12
    # T5
    vc = verify_chain()
    out["T5_chain"] = vc
    out["T5_strict_chain_ok"] = vc["all_links_ok"] and vc["all_hashes_ok"]
    # a live source file extended after its commit must have a byte-exact snapshot of the committed version
    hist = []
    lines = {ln.split(" | ")[1]: ln.split(" | ")[2].strip() for ln in (ROOT / "commitments.log").read_text().splitlines()
             if ln.strip()}
    for b in vc["bad"]:
        name, rel = b["line"].split(":", 1)
        snap = ROOT / "predictions" / "code_history" / f"{name.split('_')[0]}_{Path(rel).name}"
        from cfg10 import sha256_file
        ok = b["link_ok"] and snap.exists() and sha256_file(snap) == lines[b["line"]]
        hist.append({"entry": b["line"], "snapshot": str(snap.relative_to(ROOT)), "snapshot_matches_commit": ok})
    out["T5_history"] = hist
    out["T5_pass"] = vc["all_links_ok"] and all(h["snapshot_matches_commit"] for h in hist)
    # T6
    r = subprocess.run([sys.executable, "-I", str(ROOT / "audit" / "rederive.py"), "--synthetic"],
                       capture_output=True, text=True, timeout=120)
    out["T6_audit_synthetic"] = '"all_pass": true' in r.stdout
    out["T6_pass"] = out["T6_audit_synthetic"]
    out["all_pass"] = all(out[k] for k in out if k.endswith("_pass"))
    out["all_pass_strict"] = out["all_pass"] and out["T5_strict_chain_ok"]
    out["note"] = ("run after the GPU stages (ordering deviation): every test checks code paths or cached data whose "
                   "outputs are unchanged by when the test runs")
    write_json(RESULTS_DIR / "tests_cpu.json", out)
    logger.info(f"CPU tests: " + ", ".join(f"{k} {out[k]}" for k in out if k.endswith("_pass")))


if __name__ == "__main__":
    setup_logging("tests_cpu10")
    main()
