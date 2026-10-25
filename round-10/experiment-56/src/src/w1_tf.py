#!/usr/bin/env python3
"""W1 teacher-forced (CPU, exact): the class margin lse(z[D]) - lse(z[A]) depends only on the fork-class unembedding
rows S = D u A and the final-normed residual, so every readout arm and every null is computed exactly on the cached
fork states of S0.

Subcommands:
  s0report  stage-0 reproduction table vs iteration 9 (margins, CPU readout decomposition, G1 numerics floor)
  nulls     generate the 3 x 50 null row draws from the committed seeds; COMMIT #1 (stage-0 table, sha256 of every
            cache/fork_*.pt, the null draws) BEFORE any arm is scored
  score     score every arm and null; full-distribution metrics; COMMIT #2 (W1-TF results, the three generation
            random draws, predicted generation counts per arm, the McNemar test list) before any generated token
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger
from safetensors import safe_open

from cfg10 import (CACHE_DIR, DELTA_SWAP_EXCLUDE, DELTA_SWAP_TOL_DELTA, DELTA_SWAP_TOL_W, DOSES, FULL_UNEMB_TV,
                   I9_RES, N_BOOT, N_NULL, NULL_SEED0, NULL_TYPES, RESULTS_DIR, RMS_EPS, ROOT, SEED_BOOT, SIGN_DOSE,
                   SMALL_GAP, THRESH, UNIT_IDX, UNITS_TF, commit, import_iter9, ledger, log_deviation, model_path,
                   partial_status, read_json, read_jsonl, setup_logging, utc_now, write_json, write_jsonl)

import_iter9()
import stats9 as S9  # noqa: E402
from b2gen9 import slot_prompts, token_map  # noqa: E402

torch.set_num_threads(12)


# ================================================================================================ readout primitives
def load_readout(which: str) -> tuple[torch.Tensor, torch.Tensor]:
    """(lm_head.weight bf16 [V, d], model.norm.weight fp32 [d]) from the safetensors shards (CPU)."""
    p = Path(model_path(which))
    idx = json.loads((p / "model.safetensors.index.json").read_text())["weight_map"]
    with safe_open(str(p / idx["lm_head.weight"]), framework="pt") as fh:
        W = fh.get_tensor("lm_head.weight")
    with safe_open(str(p / idx["model.norm.weight"]), framework="pt") as fh:
        g = fh.get_tensor("model.norm.weight").float()
    return W, g


def rms_bf16(h_pre: torch.Tensor, g: torch.Tensor, eps: float = RMS_EPS) -> torch.Tensor:
    """Qwen3RMSNorm on the bf16 path (iteration 9's analysis9.readout_decomposition m_of): fp32 normalise, round to
    bf16, multiply by the gain, round to bf16."""
    x = h_pre.float()
    h = x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + eps)
    return (h.to(torch.bfloat16).float() * g.float()).to(torch.bfloat16).float()


def margin(h: torch.Tensor, WD: torch.Tensor, WA: torch.Tensor) -> torch.Tensor:
    """h [n, d] fp32; WD [|D|, d], WA [|A|, d] fp32 (or [n, |D|, d] per-prompt rows)."""
    if WD.dim() == 3:
        zD = torch.einsum("nd,nkd->nk", h, WD)
        zA = torch.einsum("nd,nkd->nk", h, WA)
    else:
        zD, zA = h @ WD.T, h @ WA.T
    return torch.logsumexp(zD, -1) - torch.logsumexp(zA, -1)


def full_logits_cpu(W: torch.Tensor, h: torch.Tensor, chunk: int = 16384) -> torch.Tensor:
    out = torch.empty(h.shape[0], W.shape[0], dtype=torch.float32)
    hf = h.float()
    for c in range(0, W.shape[0], chunk):
        out[:, c:c + chunk] = hf @ W[c:c + chunk].float().T
    return out


def dist_metrics(z: torch.Tensor, D: list[int], A: list[int], mapped: list[int], lpB: torch.Tensor
                 ) -> dict[str, np.ndarray]:
    """z [n, V] fp32 logits; lpB [n, V] base log-probs. P(D), P(A), unmapped mass, entropy, KL(arm||base),
    KL(base||arm) and exact JS (nats) over the full vocabulary."""
    lp = torch.log_softmax(z.double(), -1)
    p = lp.exp()
    pB = lpB.exp()
    m = 0.5 * (p + pB)
    lm = torch.log(m.clamp_min(1e-300))
    js = 0.5 * (p * (lp - lm)).sum(-1) + 0.5 * (pB * (lpB - lm)).sum(-1)
    return {"pD": p[:, D].sum(-1).numpy(), "pA": p[:, A].sum(-1).numpy(),
            "unmapped": (1 - p[:, mapped].sum(-1)).numpy(), "entropy": (-(p * lp).sum(-1)).numpy(),
            "kl_arm_to_base": (p * (lp - lpB)).sum(-1).numpy(), "kl_base_to_arm": (pB * (lpB - lp)).sum(-1).numpy(),
            "js_base": js.numpy()}


def share(mI: np.ndarray, mX: np.ndarray, mB: np.ndarray) -> float:
    den = float(np.sum(mI - mB))
    return float(np.sum(mI - mX)) / den if abs(den) > 1e-12 else float("nan")


def boot_share(mI: np.ndarray, mX: np.ndarray, mB: np.ndarray, seed: int = SEED_BOOT, B: int = N_BOOT
               ) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(mI), (B, len(mI)))
    num = (mI - mX)[idx].sum(1)
    den = (mI - mB)[idx].sum(1)
    ok = np.abs(den) > 1e-12
    v = num[ok] / den[ok]
    return (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5)))


# ================================================================================================ data
class UnitData:
    """Cached fork states of one unit for both models, the readout rows and gains."""

    def __init__(self, u: str, units: dict[str, Any], WI: torch.Tensor, WB: torch.Tensor, gI: torch.Tensor,
                 gB: torch.Tensor, need_logits: bool = True):
        self.u = u
        U = units[u]
        f = U["forks"][0]
        self.fork = f
        self.D, self.A = [int(t) for t in f["D"]], [int(t) for t in f["A"]]
        self.S = self.D + self.A
        self.nD = len(self.D)
        ci = torch.load(CACHE_DIR / f"fork_instr_{u}.pt")
        cb = torch.load(CACHE_DIR / f"fork_base_{u}.pt")
        self.pids = [c["pid"] for c in ci["caps"]]
        assert self.pids == [c["pid"] for c in cb["caps"]], "instruct/base prompt order differs"
        self.templates = [c["template"] for c in ci["caps"]]
        self.B_ot = (ci["B_ot"], cb["B_ot"])
        self.hfI = torch.stack([c["h_fin"] for c in ci["caps"]]).float()
        self.hpI = torch.stack([c["h_pre"] for c in ci["caps"]])
        self.hfB = torch.stack([c["h_fin"] for c in cb["caps"]]).float()
        self.hpB = torch.stack([c["h_pre"] for c in cb["caps"]])
        self.mI = np.array([c["m"] for c in ci["caps"]])
        self.mB = np.array([c["m"] for c in cb["caps"]])
        if need_logits:
            self.zI = torch.stack([c["logits"] for c in ci["caps"]]).float()
            self.zB = torch.stack([c["logits"] for c in cb["caps"]]).float()
            self.lpB = torch.log_softmax(self.zB.double(), -1)
        del ci, cb
        self.WI_S = WI[self.S].float()
        self.WB_S = WB[self.S].float()
        self.Delta = self.WB_S - self.WI_S
        self.gI, self.gB = gI, gB
        if u == "T10":
            self.mapped = sorted({int(t) for t in f["class_of"]})
        else:
            self.mapped = sorted({int(t) for t in f["phat"]})
        self.gap = self.mI - self.mB

    def m_rows(self, rows_S: torch.Tensor, h: torch.Tensor | None = None) -> np.ndarray:
        h = self.hfI if h is None else h
        return margin(h, rows_S[..., :self.nD, :], rows_S[..., self.nD:, :]).numpy()

    def z_with_rows(self, rows_S: torch.Tensor, h: torch.Tensor | None = None,
                    z_full: torch.Tensor | None = None) -> torch.Tensor:
        """Full logits with the S entries recomputed from rows_S (all other rows as in z_full / the instruct)."""
        h = self.hfI if h is None else h
        z = (self.zI if z_full is None else z_full).clone()
        z[:, self.S] = h @ rows_S.T if rows_S.dim() == 2 else torch.einsum("nd,nkd->nk", h, rows_S)
        return z


# ================================================================================================ stage-0 report
def iter9_margins(u: str) -> tuple[dict[str, float], dict[str, float]]:
    mI, mB = {}, {}
    for r in read_jsonl(I9_RES / f"b2_tf_{u}.jsonl"):
        if r["arm"] == "none":
            mI[r["pid"]] = r["m_I"]
            mB[r["pid"]] = r["m_B"]
    return mI, mB


def s0report() -> dict[str, Any]:
    from scipy.stats import spearmanr
    units = read_json(I9_RES / "units.json")
    WI, gI = load_readout("qwen")
    WB, gB = load_readout("qwen_base")
    b2 = read_json(I9_RES / "b2_summary.json")
    out: dict[str, Any] = {"utc": utc_now(), "units": {}}
    cap_i = read_json(RESULTS_DIR / "capture_instr.json")
    cap_b = read_json(RESULTS_DIR / "capture_base.json")
    out["B_ot"] = {"instr": cap_i["B_ot"], "base": cap_b["B_ot"]}
    out["engine_check"] = {"instr": cap_i.get("engine_check"), "base": cap_b.get("engine_check")}
    out["batch_sweep_T10"] = {"instr": cap_i.get("batch_sweep_T10"), "base": cap_b.get("batch_sweep_T10")}
    all_pass = True
    for u in UNITS_TF:
        d = UnitData(u, units, WI, WB, gI, gB, need_logits=False)
        i9I, i9B = iter9_margins(u)
        rI = np.array([i9I[p] for p in d.pids])
        rB = np.array([i9B[p] for p in d.pids])
        tolp = THRESH["S0_prompt_tol_B40"] if d.B_ot[0] == 40 else THRESH["S0_prompt_tol_small_B"]
        rec: dict[str, Any] = {
            "pids": d.pids, "m_I": d.mI.tolist(), "m_B": d.mB.tolist(), "m_I_iter9": rI.tolist(),
            "m_B_iter9": rB.tolist(), "mean_m_I": float(d.mI.mean()), "mean_m_I_iter9": float(rI.mean()),
            "mean_m_B": float(d.mB.mean()), "mean_m_B_iter9": float(rB.mean()),
            "abs_diff_mean_m_I": float(abs(d.mI.mean() - rI.mean())),
            "abs_diff_mean_m_B": float(abs(d.mB.mean() - rB.mean())),
            "per_prompt_abs_diff_I": np.abs(d.mI - rI).tolist(), "per_prompt_abs_diff_B": np.abs(d.mB - rB).tolist(),
            "max_per_prompt_abs_diff_I": float(np.abs(d.mI - rI).max()),
            "max_per_prompt_abs_diff_B": float(np.abs(d.mB - rB).max()),
            "spearman_I": float(spearmanr(d.mI, rI)[0]), "spearman_B": float(spearmanr(d.mB, rB)[0]),
            "gap_mean": float(d.gap.mean()), "gap_iter9": float(b2["units"][u]["gap_mean"]),
            "gap_ci95": list(S9.boot_mean_ci(d.gap, B=N_BOOT, seed=SEED_BOOT)), "per_prompt_tol": tolp}
        rec["mean_pass"] = rec["abs_diff_mean_m_I"] <= THRESH["S0_mean_tol"] and \
            rec["abs_diff_mean_m_B"] <= THRESH["S0_mean_tol"]
        rec["per_prompt_pass"] = rec["max_per_prompt_abs_diff_I"] <= tolp and rec["max_per_prompt_abs_diff_B"] <= tolp
        rec["spearman_pass"] = min(rec["spearman_I"], rec["spearman_B"]) >= THRESH["S0_spearman"]
        # CPU readout decomposition exactly as iteration 9 (bf16-path norm recompute from cached final-norm inputs)
        WI_S, WB_S = d.WI_S, d.WB_S
        mII = d.m_rows(WI_S, rms_bf16(d.hpI, gI))
        mBB = d.m_rows(WB_S, rms_bf16(d.hpB, gB))
        m_bres_bnorm_IU = d.m_rows(WI_S, rms_bf16(d.hpB, gB))
        m_bres_inorm_IU = d.m_rows(WI_S, rms_bf16(d.hpB, gI))
        gap_cpu = float((mII - mBB).sum())
        dec = {"share_unembedding_only": float((m_bres_bnorm_IU - mBB).sum() / gap_cpu),
               "share_readout_swap_on_base_resid": float((m_bres_inorm_IU - mBB).sum() / gap_cpu),
               "share_unembedding_only_iter9": b2["units"][u]["readout_decomposition_cpu"]["share_unembedding_only"],
               "share_readout_swap_on_base_resid_iter9":
                   b2["units"][u]["readout_decomposition_cpu"]["share_readout_swap_on_base_resid"],
               "target": THRESH["S0_decomp_target"][u], "tol": THRESH["S0_decomp_tol"]}
        dec["pass"] = abs(dec["share_unembedding_only"] - dec["target"]) <= dec["tol"]
        rec["readout_decomposition_cpu"] = dec
        # G1: rms(h_pre_I, g_I) vs captured h_fin_I (relative error) and the margin numerics floor
        hr = rms_bf16(d.hpI, gI)
        rel = ((hr - d.hfI).norm(dim=-1) / d.hfI.norm(dim=-1)).numpy()
        floor = d.m_rows(WI_S, hr) - d.m_rows(WI_S)
        twin_cpu = d.m_rows(WI_S)
        rec["G1"] = {"rel_err_max": float(rel.max()), "rel_err_mean": float(rel.mean()),
                     "margin_floor_max_abs": float(np.abs(floor).max()), "margin_floor_mean": float(floor.mean()),
                     "bit_exact_prompts": int(sum(torch.equal(hr[i], d.hfI[i]) for i in range(len(d.pids)))),
                     "twin_cpu_vs_gpu_max_abs": float(np.abs(twin_cpu - d.mI).max()),
                     "pass": float(rel.max()) <= THRESH["G1_rel_err"]}
        rec["pass"] = rec["mean_pass"] and rec["spearman_pass"] and dec["pass"]
        all_pass &= rec["pass"]
        out["units"][u] = rec
        logger.info(f"S0 {u}: mean m_I {rec['mean_m_I']:.3f} (iter9 {rec['mean_m_I_iter9']:.3f}), mean m_B "
                    f"{rec['mean_m_B']:.3f} (iter9 {rec['mean_m_B_iter9']:.3f}), max |d| I "
                    f"{rec['max_per_prompt_abs_diff_I']:.3f} B {rec['max_per_prompt_abs_diff_B']:.3f}, spearman "
                    f"{rec['spearman_I']:.4f}/{rec['spearman_B']:.4f}; decomposition "
                    f"{dec['share_unembedding_only']:.3f} (target {dec['target']}); G1 rel err "
                    f"{rec['G1']['rel_err_max']:.2e}, floor {rec['G1']['margin_floor_max_abs']:.4f}")
        if not rec["per_prompt_pass"]:
            log_deviation(f"S0_per_prompt_{u}", f"{u}: max per-prompt |m - m_iter9| I "
                                                f"{rec['max_per_prompt_abs_diff_I']:.3f}, B "
                                                f"{rec['max_per_prompt_abs_diff_B']:.3f} > {tolp} (different GPU: "
                                                f"RTX 4090 vs iteration 9's L4; bf16 numerics depend on the kernel)")
    out["all_pass"] = all_pass
    write_json(RESULTS_DIR / "stage0.json", out)
    partial_status("S0_report", all_pass=all_pass)
    return out


# ================================================================================================ nulls
def decoded_ok(s: str, excl: tuple[str, ...]) -> bool:
    t = s.strip().lower()
    return bool(t) and not any(e in t for e in excl)


def make_nulls() -> dict[str, Any]:
    from transformers import AutoTokenizer
    t0 = time.time()
    units = read_json(I9_RES / "units.json")
    tok = AutoTokenizer.from_pretrained(model_path("qwen"))
    n_real = len(tok)
    WI, _ = load_readout("qwen")
    WB, _ = load_readout("qwen_base")
    # full-vocabulary row norms (fp32, chunked)
    dn = torch.empty(WI.shape[0])
    wn = torch.empty(WI.shape[0])
    for c in range(0, WI.shape[0], 16384):
        a, b = WI[c:c + 16384].float(), WB[c:c + 16384].float()
        dn[c:c + 16384] = (b - a).norm(dim=-1)
        wn[c:c + 16384] = a.norm(dim=-1)
    torch.save({"delta_norm": dn, "w_instr_norm": wn}, CACHE_DIR / "lm_head_rownorms.pt")
    meta: dict[str, Any] = {"utc": utc_now(), "units": {}}
    for u in UNITS_TF:
        f = units[u]["forks"][0]
        Sx = [int(t) for t in f["D"]] + [int(t) for t in f["A"]]
        ui = UNIT_IDX[u]
        WI_S, WB_S = WI[Sx].float(), WB[Sx].float()
        Dl = WB_S - WI_S
        dnorm = Dl.norm(dim=-1).numpy()
        pca = torch.load(CACHE_DIR / f"resid_pca_{u}.pt")
        V = pca["basis"].numpy().astype(np.float64)                 # [64, d]
        excl = DELTA_SWAP_EXCLUDE[u]
        pools, pool_meta = {}, {}
        for j, t in enumerate(Sx):
            okn = ((dn - dn[t]).abs() <= DELTA_SWAP_TOL_DELTA * dn[t]) & ((wn - wn[t]).abs() <= DELTA_SWAP_TOL_W *
                                                                          wn[t])
            cand = [int(s) for s in torch.nonzero(okn).flatten().tolist() if s < n_real and s not in Sx]
            cand = [s for s in cand if decoded_ok(tok.decode([s]), excl)]
            pools[t] = cand
            pool_meta[str(t)] = {"tok": tok.decode([t]), "n_candidates": len(cand), "delta_norm": float(dn[t]),
                                 "w_norm": float(wn[t])}
            if len(cand) < 10:
                log_deviation(f"delta_swap_pool_{u}_{t}", f"DELTA_SWAP pool for {tok.decode([t])!r} has only "
                                                          f"{len(cand)} candidates")
        iso = np.zeros((N_NULL, len(Sx), WI.shape[1]), dtype=np.float32)
        res = np.zeros_like(iso)
        swp = np.zeros_like(iso)
        swp_tok = np.zeros((N_NULL, len(Sx)), dtype=np.int64)
        for k in range(N_NULL):
            used: set[int] = set()
            for j, t in enumerate(Sx):
                r1 = np.random.default_rng([NULL_SEED0["RAND_ISO"] + 100 * ui + k, t])
                g = r1.standard_normal(WI.shape[1])
                iso[k, j] = (dnorm[j] * g / np.linalg.norm(g)).astype(np.float32)
                r2 = np.random.default_rng([NULL_SEED0["RAND_RESID"] + 100 * ui + k, t])
                c = r2.standard_normal(V.shape[0])
                v = c @ V
                res[k, j] = (dnorm[j] * v / np.linalg.norm(v)).astype(np.float32)
                r3 = np.random.default_rng([NULL_SEED0["DELTA_SWAP"] + 100 * ui + k, t])
                cand = [s for s in pools[t] if s not in used] or pools[t]
                s = cand[int(r3.integers(len(cand)))]
                used.add(s)
                swp_tok[k, j] = s
                swp[k, j] = (WB[s].float() - WI[s].float()).numpy()
        np.savez(RESULTS_DIR / f"null_draws_{u}.npz", S=np.array(Sx), RAND_ISO=iso, RAND_RESID=res, DELTA_SWAP=swp,
                 DELTA_SWAP_tokens=swp_tok, delta_norm=dnorm)
        meta["units"][u] = {"S": Sx, "S_str": [tok.decode([t]) for t in Sx], "pools": pool_meta,
                            "resid_pca_var_explained": pca["var_explained_top64"],
                            "delta_swap_distinct_tokens": int(len(np.unique(swp_tok))),
                            "iso_norm_check_max_rel": float(np.abs(np.linalg.norm(iso, axis=-1) / dnorm - 1).max()),
                            "resid_norm_check_max_rel": float(np.abs(np.linalg.norm(res, axis=-1) / dnorm - 1).max())}
        logger.info(f"nulls {u}: S {meta['units'][u]['S_str']}, pools "
                    f"{[v['n_candidates'] for v in pool_meta.values()]}")
    meta["seconds"] = round(time.time() - t0, 1)
    write_json(RESULTS_DIR / "null_meta.json", meta)
    files = sorted(CACHE_DIR.glob("fork_*.pt")) + sorted(CACHE_DIR.glob("resid_pca_*.pt")) + \
        [RESULTS_DIR / f"null_draws_{u}.npz" for u in UNITS_TF] + [RESULTS_DIR / "null_meta.json",
                                                                   RESULTS_DIR / "stage0.json"]
    commit("commit1_stage0_nulls", {"stage0_all_pass": read_json(RESULTS_DIR / "stage0.json")["all_pass"],
                                    "note": "stage-0 table, fork caches and null draws committed before any W1 arm "
                                            "is scored"}, files=files)
    ledger("COMMIT1")
    return meta


# ================================================================================================ scoring
def arm_rows(d: UnitData) -> dict[str, Any]:
    """Every W1 arm as (margins [n], full logits [n, V] or None)."""
    WI_S, WB_S = d.WI_S, d.WB_S
    hI_Bn = rms_bf16(d.hpI, d.gB)
    hI_In = rms_bf16(d.hpI, d.gI)
    hB_In = rms_bf16(d.hpB, d.gI)
    hB_Bn = rms_bf16(d.hpB, d.gB)
    rows_D = torch.cat([WB_S[:d.nD], WI_S[d.nD:]])
    rows_A = torch.cat([WI_S[:d.nD], WB_S[d.nD:]])
    arms: dict[str, tuple[np.ndarray, torch.Tensor | None]] = {}
    arms["TWIN"] = (d.mI.copy(), d.zI)
    arms["TWIN_cpu"] = (d.m_rows(WI_S), None)
    arms["ROWS_ALL"] = (d.m_rows(WB_S), d.z_with_rows(WB_S))
    arms["ROWS_D"] = (d.m_rows(rows_D), d.z_with_rows(rows_D))
    arms["ROWS_A"] = (d.m_rows(rows_A), d.z_with_rows(rows_A))
    zN = full_logits_cpu(WI_G["W"], hI_Bn)
    arms["NORM"] = (d.m_rows(WI_S, hI_Bn), zN)
    arms["ROWS_NORM"] = (d.m_rows(WB_S, hI_Bn), d.z_with_rows(WB_S, hI_Bn, zN))
    zF = full_logits_cpu(WB_G["W"], d.hfI)
    arms["FULL_UNEMB"] = (margin(d.hfI, WB_G["W"][d.D].float(), WB_G["W"][d.A].float()).numpy(), zF)
    arms["NORM_recompute_instr_gain"] = (d.m_rows(WI_S, hI_In), None)
    for lam in DOSES:
        r = WI_S + lam * d.Delta
        arms[f"DOSE_{lam:g}"] = (d.m_rows(r), d.z_with_rows(r))
    r = WI_S + SIGN_DOSE * d.Delta
    arms["SIGN"] = (d.m_rows(r), d.z_with_rows(r))
    # 2x2 factorial (residual = final-norm input; readout = (norm gain, lm_head S rows))
    arms["F_BI"] = (d.m_rows(WI_S, hB_In), None)                 # base residual, instruct readout
    arms["F_BB_cpu"] = (d.m_rows(WB_S, hB_Bn), None)
    arms["F_II_cpu"] = (d.m_rows(WI_S, hI_In), None)
    arms["UNEMB_ONLY_on_base_resid"] = (d.m_rows(WI_S, hB_Bn), None)   # iteration 9's (h_pre_B, g_B, W_I)
    return arms


def rec_rows(d: UnitData, arm: str, m: np.ndarray, met: dict[str, np.ndarray] | None, draw: int | None
             ) -> list[dict[str, Any]]:
    out = []
    for i, pid in enumerate(d.pids):
        r = {"unit": d.u, "pid": pid, "template": d.templates[i], "arm": arm, "draw": draw, "m": float(m[i]),
             "m_I": float(d.mI[i]), "m_B": float(d.mB[i])}
        if met is not None:
            for k, v in met.items():
                r[k] = float(v[i])
        out.append(r)
    return out


def summarize_arm(d: UnitData, m: np.ndarray, boot: bool = True) -> dict[str, Any]:
    sh = share(d.mI, m, d.mB)
    per = (d.mI - m) / np.where(np.abs(d.gap) > 1e-9, d.gap, np.nan)
    small = np.abs(d.gap) < SMALL_GAP
    out = {"share": sh, "mean_margin": float(m.mean()), "per_prompt_share": per.tolist(),
           "mean_of_ratios": float(np.nanmean(per)), "median_of_ratios": float(np.nanmedian(per)),
           "mean_of_ratios_excl_small_gap": float(np.nanmean(per[~small])) if (~small).any() else None,
           "small_gap_prompts": [d.pids[i] for i in np.nonzero(small)[0]]}
    if boot:
        out["ci95"] = boot_share(d.mI, m, d.mB)
    return out


WI_G: dict[str, torch.Tensor] = {}
WB_G: dict[str, torch.Tensor] = {}


def score() -> dict[str, Any]:
    t0 = time.time()
    units = read_json(I9_RES / "units.json")
    WI, gI = load_readout("qwen")
    WB, gB = load_readout("qwen_base")
    WI_G["W"], WB_G["W"] = WI, WB
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_path("qwen"))
    all_rows: list[dict[str, Any]] = []
    summ: dict[str, Any] = {"utc": utc_now(), "units": {}}
    gen_plan: dict[str, Any] = {}
    for u in UNITS_TF:
        d = UnitData(u, units, WI, WB, gI, gB)
        nul = np.load(RESULTS_DIR / f"null_draws_{u}.npz")
        assert list(nul["S"]) == d.S
        arms = arm_rows(d)
        us: dict[str, Any] = {"pids": d.pids, "templates": d.templates, "gap_mean": float(d.gap.mean()),
                              "gap": d.gap.tolist(), "m_I": d.mI.tolist(), "m_B": d.mB.tolist(), "arms": {},
                              "S_str": [tok.decode([t]) for t in d.S], "nD": d.nD}
        met_cache: dict[str, dict[str, np.ndarray]] = {}
        for a, (m, z) in arms.items():
            met = dist_metrics(z, d.D, d.A, d.mapped, d.lpB) if z is not None else None
            if met is not None:
                met_cache[a] = met
            all_rows += rec_rows(d, a, m, met, None)
            s = summarize_arm(d, m)
            if met is not None:
                s["dist_mean"] = {k: float(v.mean()) for k, v in met.items()}
            us["arms"][a] = s
        # base fork distribution summary (reference)
        metB = dist_metrics(d.zB, d.D, d.A, d.mapped, d.lpB)
        us["base_dist_mean"] = {k: float(v.mean()) for k, v in metB.items()}
        all_rows += rec_rows(d, "BASE", d.mB, metB, None)
        # identity checks
        us["identity_full_unemb_minus_rows_all_max_abs"] = float(np.abs(arms["FULL_UNEMB"][0] -
                                                                       arms["ROWS_ALL"][0]).max())
        us["identity_twin_cpu_minus_gpu_max_abs"] = float(np.abs(arms["TWIN_cpu"][0] - d.mI).max())
        # 2x2 factorial
        mII, mIB, mBI, mBB = d.mI, arms["ROWS_NORM"][0], arms["F_BI"][0], d.mB
        inter = mII - mIB - mBI + mBB
        us["factorial_2x2"] = {"m_II": float(mII.mean()), "m_IB_rows_norm": float(mIB.mean()),
                               "m_BI_base_resid_instr_readout": float(mBI.mean()), "m_BB": float(mBB.mean()),
                               "interaction_mean": float(inter.mean()), "interaction_per_prompt": inter.tolist(),
                               "interaction_ci95": list(S9.boot_mean_ci(inter, B=N_BOOT, seed=SEED_BOOT)),
                               "readout_effect_on_instr_resid": float((mII - mIB).mean()),
                               "readout_effect_on_base_resid": float((mBI - mBB).mean()),
                               "residual_effect_under_instr_readout": float((mII - mBI).mean()),
                               "residual_effect_under_base_readout": float((mIB - mBB).mean()),
                               "share_readout_on_instr_resid": share(mII, mIB, mBB),
                               "share_readout_on_base_resid": float((mBI - mBB).sum() / (mII - mBB).sum()),
                               "share_unembedding_only_on_base_resid":
                                   float((arms["UNEMB_ONLY_on_base_resid"][0] - mBB).sum() / (mII - mBB).sum()),
                               "share_interaction": float(inter.sum() / (mII - mBB).sum())}
        # per-token logit change h_fin_I . Delta_t
        dz = (d.hfI @ d.Delta.T).numpy()
        us["per_token_logit_change"] = {us["S_str"][j]: {"mean": float(dz[:, j].mean()), "sd": float(dz[:, j].std()),
                                                         "class": "D" if j < d.nD else "A"}
                                        for j in range(len(d.S))}
        us["delta_norms"] = {us["S_str"][j]: float(d.Delta[j].norm()) for j in range(len(d.S))}
        # nulls
        nulls: dict[str, Any] = {}
        obs = us["arms"]["ROWS_ALL"]["share"]
        for nt in NULL_TYPES:
            dl = torch.from_numpy(nul[nt])                          # [50, |S|, d]
            shs, mmeans = [], []
            per_draw_m = []
            for k in range(N_NULL):
                r = d.WI_S + dl[k]
                m = d.m_rows(r)
                per_draw_m.append(m)
                met = dist_metrics(d.z_with_rows(r), d.D, d.A, d.mapped, d.lpB)
                all_rows += rec_rows(d, nt, m, met, k)
                shs.append(share(d.mI, m, d.mB))
                mmeans.append(float(met["unmapped"].mean()))
            shs_a = np.array(shs)
            nulls[nt] = {"shares": shs, "median": float(np.median(shs_a)), "p95": float(np.percentile(shs_a, 95)),
                         "max": float(shs_a.max()), "min": float(shs_a.min()), "mean": float(shs_a.mean()),
                         "empirical_p_rows_all": S9.empirical_p_upper(obs, shs_a),
                         "p_floor": 1 / (N_NULL + 1), "mean_unmapped": float(np.mean(mmeans)),
                         "rows_all_above_max": bool(obs > shs_a.max()), "rows_all_above_p95": bool(
                             obs > np.percentile(shs_a, 95))}
            # dose-matched isotropic curve (F3): lambda * delta for the draw with the median share
            if nt == "RAND_ISO":
                med = int(np.argsort(shs_a)[len(shs_a) // 2])
                mx = int(np.argmax(shs_a))
                nulls[nt]["median_draw"], nulls[nt]["max_draw"] = med, mx
                curve = {}
                for lam in DOSES + (SIGN_DOSE,):
                    curve[f"{lam:g}"] = {
                        "median_draw_share": share(d.mI, d.m_rows(d.WI_S + lam * dl[med]), d.mB),
                        "all_draws_median_share": float(np.median([share(d.mI, d.m_rows(d.WI_S + lam * dl[k]), d.mB)
                                                                   for k in range(N_NULL)]))}
                nulls[nt]["dose_curve"] = curve
        us["nulls"] = nulls
        # verdict (T10 primary; B3 descriptive with the same rule)
        rows_sh = obs
        iso = nulls["RAND_ISO"]
        if rows_sh >= THRESH["W1_rows_share"] and iso["median"] <= THRESH["W1_rand_iso_median"] and \
                rows_sh > iso["max"]:
            verdict = "SUPPORTED"
        elif rows_sh <= THRESH["W1_disconfirm"]:
            verdict = "DISCONFIRMED"
        else:
            verdict = "PARTIAL"
        spec = rows_sh > nulls["DELTA_SWAP"]["p95"] and rows_sh > nulls["RAND_RESID"]["p95"]
        us["verdict"] = verdict
        us["specificity_qualifier"] = ("written into these tokens' own rows" if spec else
                                       "readout-level but not token-specific")
        us["verdict_role"] = "primary" if u == "T10" else "descriptive"
        # per-template breakdown of ROWS_ALL
        us["rows_all_by_template"] = {}
        for w in sorted(set(d.templates)):
            ix = [i for i, t in enumerate(d.templates) if t == w]
            us["rows_all_by_template"][w] = share(d.mI[ix], arms["ROWS_ALL"][0][ix], d.mB[ix])
        # ---------------- generation plan and predictions (COMMIT #2)
        bins, tmap = token_map(u, d.fork)
        sp = slot_prompts(units[u])
        idx_of = {pid: i for i, pid in enumerate(d.pids)}
        gen_arms_z = {"TWIN": d.zI, "ROWS": arms["ROWS_ALL"][1], "FPD": d.zB, "ROWS_ALLSTEPS": arms["ROWS_ALL"][1],
                      "FULL_UNEMB_FORK": arms["FULL_UNEMB"][1]}
        dl_iso = torch.from_numpy(nul["RAND_ISO"])
        rand_idx = {"RAND_MED": iso["median_draw"], "RAND_MAX": iso["max_draw"], "RAND_0": 0}
        for a, k in rand_idx.items():
            gen_arms_z[a] = d.z_with_rows(d.WI_S + dl_iso[k])
        pred: dict[str, Any] = {"bins": bins, "by_prompt": {}, "rand_draws": rand_idx,
                                "rand_draw_tf_shares": {a: iso["shares"][k] for a, k in rand_idx.items()}}
        tv_full_rows = []
        for _, p in sp:
            i = idx_of[p["pid"]]
            rp = {}
            for a, z in gen_arms_z.items():
                pr = torch.softmax(z[i].double(), -1).numpy()
                mix = np.zeros(len(bins))
                mapped = 0.0
                for t, v in tmap.items():
                    mix += pr[t] * v
                    mapped += pr[t]
                top = np.argsort(-pr)[:8]
                rp[a] = {"predicted_shares": dict(zip(bins, mix.tolist())), "unmapped": 1 - mapped,
                         "top": [(tok.decode([int(t)]), float(pr[t])) for t in top]}
            pF = torch.softmax(arms["FULL_UNEMB"][1][i].double(), -1)
            pR = torch.softmax(arms["ROWS_ALL"][1][i].double(), -1)
            tv_full_rows.append(float(0.5 * (pF - pR).abs().sum()))
            pred["by_prompt"][p["pid"]] = rp
        arms_list = list(gen_arms_z)
        pred["unit_mean"] = {a: {b: float(np.mean([pred["by_prompt"][k][a]["predicted_shares"][b]
                                                   for k in pred["by_prompt"]])) for b in bins} for a in arms_list}
        pred["unit_mean_unmapped"] = {a: float(np.mean([pred["by_prompt"][k][a]["unmapped"]
                                                        for k in pred["by_prompt"]])) for a in arms_list}
        corr_bins = ["dfs"] if u == "T10" else ["prim_heap", "prim_array"]
        pred["predicted_count_correct_class_of_30"] = {a: 30 * sum(pred["unit_mean"][a][b] for b in corr_bins)
                                                       for a in arms_list}
        pred["tv_full_unemb_vs_rows_slot_mean"] = float(np.mean(tv_full_rows))
        pred["run_FULL_UNEMB_FORK"] = bool(np.mean(tv_full_rows) > FULL_UNEMB_TV)
        slot_ix = [idx_of[p["pid"]] for _, p in sp]
        pred["slot_prompt_rows_share"] = share(d.mI[slot_ix], arms["ROWS_ALL"][0][slot_ix], d.mB[slot_ix])
        pred["slot_prompt_m_I_mean"] = float(d.mI[slot_ix].mean())
        gen_plan[u] = pred
        summ["units"][u] = us
        logger.info(f"W1-TF {u}: ROWS_ALL {us['arms']['ROWS_ALL']['share']:.3f} "
                    f"{us['arms']['ROWS_ALL']['ci95']}, ROWS_NORM {us['arms']['ROWS_NORM']['share']:.3f}, NORM "
                    f"{us['arms']['NORM']['share']:.3f}, ROWS_D {us['arms']['ROWS_D']['share']:.3f}, ROWS_A "
                    f"{us['arms']['ROWS_A']['share']:.3f}; RAND_ISO med {nulls['RAND_ISO']['median']:.3f} max "
                    f"{nulls['RAND_ISO']['max']:.3f}; DELTA_SWAP p95 {nulls['DELTA_SWAP']['p95']:.3f}; RAND_RESID "
                    f"p95 {nulls['RAND_RESID']['p95']:.3f}; interaction {us['factorial_2x2']['interaction_mean']:.3f}"
                    f" -> {verdict} ({us['specificity_qualifier']})")
        logger.info(f"gen predictions {u}: {pred['predicted_count_correct_class_of_30']} "
                    f"(TV full vs rows {pred['tv_full_unemb_vs_rows_slot_mean']:.4f})")
    write_jsonl(RESULTS_DIR / "w1_tf_rows.jsonl", all_rows)
    summ["seconds"] = round(time.time() - t0, 1)
    write_json(RESULTS_DIR / "w1_tf_summary.json", summ)
    tests = {"primary_holm_2": ["ROWS_vs_TWIN", "ROWS_vs_RAND_MED"],
             "reported": ["ROWS_vs_RAND_MAX", "ROWS_vs_RAND_0", "FPD_vs_TWIN", "ROWS_vs_FPD",
                          "ROWS_ALLSTEPS_vs_ROWS", "ROWS_ALLSTEPS_vs_TWIN", "FULL_UNEMB_FORK_vs_ROWS"],
                 "outcome": "correct DFS (T10) / correct Prim (B3), exact two-sided McNemar on CRN pairs"}
    note = ("with T10 slot-prompt m_I around %.2f nats, ROWS reaches 10/30 DFS only if its slot-prompt share is about "
            "0.75 or more; the direction's 10/30 bar is kept as registered and the committed predicted count is "
            "reported beside it" % gen_plan["T10"]["slot_prompt_m_I_mean"])
    commit("commit2_w1tf_genplan", {"w1_tf_verdict_T10": summ["units"]["T10"]["verdict"],
                                    "w1_tf_shares": {u: {a: summ["units"][u]["arms"][a]["share"]
                                                         for a in ("ROWS_ALL", "ROWS_D", "ROWS_A", "NORM",
                                                                   "ROWS_NORM")} for u in UNITS_TF},
                                    "gen_predictions": gen_plan, "mcnemar_tests": tests, "note": note},
           files=[RESULTS_DIR / "w1_tf_summary.json", RESULTS_DIR / "w1_tf_rows.jsonl"])
    ledger("COMMIT2", seconds=summ["seconds"])
    partial_status("W1_TF", verdict_T10=summ["units"]["T10"]["verdict"])
    return summ


def export_zs() -> None:
    """Per-prompt fork logits of the S tokens under TWIN, ROWS_ALL and the base model (results/w1_tf_zS.jsonl), for
    the stdlib audit's D/A-identity shuffle placebo."""
    units = read_json(I9_RES / "units.json")
    WI, gI = load_readout("qwen")
    WB, gB = load_readout("qwen_base")
    rows = []
    for u in UNITS_TF:
        d = UnitData(u, units, WI, WB, gI, gB, need_logits=False)
        zt = (d.hfI @ d.WI_S.T).numpy()
        zr = (d.hfI @ d.WB_S.T).numpy()
        zb = (d.hfB @ d.WB_S.T).numpy()
        for i, pid in enumerate(d.pids):
            rows.append({"unit": u, "pid": pid, "S": d.S, "nD": d.nD, "z_TWIN": zt[i].tolist(),
                         "z_ROWS_ALL": zr[i].tolist(), "z_BASE": zb[i].tolist()})
    write_jsonl(RESULTS_DIR / "w1_tf_zS.jsonl", rows)
    logger.info(f"exported {len(rows)} z_S rows")


if __name__ == "__main__":
    setup_logging(f"w1_tf_{sys.argv[1]}")
    {"s0report": s0report, "nulls": make_nulls, "score": score, "export_zs": export_zs}[sys.argv[1]]()
