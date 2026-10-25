#!/usr/bin/env python3
"""W3 (descriptive): the W1 row test at Gemma-3-4b's reversed grid fork G-GRID@32 (instruct default DFS ' visited'
vs the BFS class), on the 20 on-policy prompts of iteration 9's B1.

  gpu <gemma|gemma_pt>  text-only Gemma3ForCausalLM (iteration 9's b1_9._load_gemma), full forward per prompt (chat
                        ids + opening, as b1's fork_rec), capture h_pre (final-norm input) and h_fin (final-normed) at
                        the fork, the model's own fork logits and an fp32 CPU-path readout (G7 check)
  score                 CPU readout arms with the embeddings untied at the OUTPUT only: logits for S tokens use the pt
                        embedding rows (input embeddings untouched); Gemma3RMSNorm gain = (1 + w); softcapping applied
                        if the config sets final_logit_softcapping. ROWS_ALL, ROWS_D, ROWS_A, NORM, ROWS_NORM, DOSE,
                        RAND_ISO x 50, DELTA_SWAP x 50. No threshold.
"""

from __future__ import annotations

import gc
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger
from safetensors import safe_open

from cfg10 import (CACHE_DIR, DELTA_SWAP_EXCLUDE, DELTA_SWAP_TOL_DELTA, DELTA_SWAP_TOL_W, DOSES, I9_RES, N_NULL,
                   NULL_SEED0, RESULTS_DIR, SIGN_DOSE, UNIT_IDX, append_jsonl, commit, import_iter9, ledger,
                   model_path, partial_status, read_json, setup_logging, utc_now, write_json, write_jsonl)
from w1_tf import boot_share, share

import_iter9()
UNIT = "G-GRID"


def gemma_cfg() -> dict[str, Any]:
    from transformers import AutoConfig
    t = AutoConfig.from_pretrained(model_path("gemma")).text_config
    return {"final_logit_softcapping": getattr(t, "final_logit_softcapping", None),
            "rms_norm_eps": float(getattr(t, "rms_norm_eps", 1e-6)), "vocab_size": int(t.vocab_size),
            "hidden_size": int(t.hidden_size)}


def softcap(z: torch.Tensor, cap: float | None) -> torch.Tensor:
    return z if not cap else cap * torch.tanh(z / cap)


def prompts_and_fork() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    U = read_json(I9_RES / "units.json")[UNIT]
    b1 = read_json(I9_RES / "b1_gemma_G-GRID.json")
    kept = b1["on_policy"]["kept"]
    by = {p["pid"]: p for p in U["prompts"]}
    return [by[k] for k in kept], U["forks"][0]


@torch.no_grad()
def gpu(which: str) -> None:
    import b1_9
    from transformers import AutoTokenizer
    t0 = time.time()
    ledger(f"W3_{which}_start")
    path = model_path(which)
    model = b1_9._load_gemma(path)
    model.eval()
    model.requires_grad_(False)
    tok = AutoTokenizer.from_pretrained(model_path("gemma"))
    cfg = gemma_cfg()
    prompts, f = prompts_and_fork()
    E = model.lm_head.weight
    caps = []
    for p in prompts:
        ids = p["ids"] + f["opening"]
        st: dict[str, torch.Tensor] = {}

        def pre_norm(m, args, kwargs):
            x = args[0] if args else kwargs["hidden_states"]
            st["h_pre"] = x[0, -1].detach().clone()
        hk = model.model.norm.register_forward_pre_hook(pre_norm, with_kwargs=True)
        try:
            o = model(input_ids=torch.tensor([ids], device="cuda"), use_cache=False, logits_to_keep=len(f["opening"]) + 1,
                      output_hidden_states=True)
        finally:
            hk.remove()
        h_fin = o.hidden_states[-1][0, -1].detach()
        z_model = o.logits[0, -1].float()
        z_cpu = softcap(torch.cat([h_fin.float()[None] @ E[c:c + 16384].float().T for c in range(0, E.shape[0], 16384)],
                                  -1)[0], cfg["final_logit_softcapping"])
        lp = torch.log_softmax(z_model.double(), -1)
        m_model = float(torch.logsumexp(lp[f["D"]], 0) - torch.logsumexp(lp[f["A"]], 0))
        m_cpu = float(torch.logsumexp(z_cpu[f["D"]], 0) - torch.logsumexp(z_cpu[f["A"]], 0))
        diff = (z_cpu - z_model).abs()
        tol = torch.clamp(z_model.abs() * 2 ** -7, min=1e-2)
        caps.append({"pid": p["pid"], "h_pre": st["h_pre"].to(torch.bfloat16).cpu(),
                     "h_fin": h_fin.to(torch.bfloat16).cpu(), "z": z_cpu.cpu(), "m": m_cpu, "m_model": m_model,
                     "g7_max_abs": float(diff.max()), "g7_within_bf16_quantisation": bool((diff <= tol).all())})
        del o
    torch.save({"model": which, "caps": caps, "cfg": cfg}, CACHE_DIR / f"gemma_{which}.pt")
    rec = {"model": which, "cfg": cfg, "n": len(caps), "m_cpu": [c["m"] for c in caps],
           "m_model": [c["m_model"] for c in caps], "g7_max_abs": max(c["g7_max_abs"] for c in caps),
           "g7_pass": all(c["g7_within_bf16_quantisation"] for c in caps), "seconds": round(time.time() - t0, 1)}
    p_out = RESULTS_DIR / "w3_capture.json"
    cur = read_json(p_out) if p_out.exists() else {}
    cur[which] = rec
    write_json(p_out, cur)
    logger.info(f"W3 capture {which}: mean m_cpu {np.mean(rec['m_cpu']):.3f} m_model {np.mean(rec['m_model']):.3f}; "
                f"G7 max |z_cpu - z_model| {rec['g7_max_abs']:.4f} pass {rec['g7_pass']}")
    del model
    gc.collect()
    torch.cuda.empty_cache()
    ledger(f"W3_{which}_end")


def load_emb_norm(which: str) -> tuple[torch.Tensor, torch.Tensor]:
    p = Path(model_path(which))
    wm = json.loads((p / "model.safetensors.index.json").read_text())["weight_map"]

    def get(names: list[str]) -> torch.Tensor:
        for n in names:
            if n in wm:
                with safe_open(str(p / wm[n]), framework="pt") as fh:
                    return fh.get_tensor(n)
        raise KeyError(names)
    E = get(["language_model.model.embed_tokens.weight", "model.language_model.embed_tokens.weight"])
    w = get(["language_model.model.norm.weight", "model.language_model.norm.weight"]).float()
    return E, w


def rms_gemma(h_pre: torch.Tensor, w: torch.Tensor, eps: float) -> torch.Tensor:
    x = h_pre.float()
    y = x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + eps)
    return (y * (1.0 + w.float())).to(torch.bfloat16).float()


def score() -> dict[str, Any]:
    from transformers import AutoTokenizer
    t0 = time.time()
    cfg = gemma_cfg()
    cap = cfg["final_logit_softcapping"]
    prompts, f = prompts_and_fork()
    D, A = [int(t) for t in f["D"]], [int(t) for t in f["A"]]
    S = D + A
    nD = len(D)
    ci = torch.load(CACHE_DIR / "gemma_gemma.pt")
    cb = torch.load(CACHE_DIR / "gemma_gemma_pt.pt")
    hfI = torch.stack([c["h_fin"] for c in ci["caps"]]).float()
    hpI = torch.stack([c["h_pre"] for c in ci["caps"]])
    hpB = torch.stack([c["h_pre"] for c in cb["caps"]])
    mI = np.array([c["m"] for c in ci["caps"]])
    mB = np.array([c["m"] for c in cb["caps"]])
    zI = torch.stack([c["z"] for c in ci["caps"]]).float()
    zB = torch.stack([c["z"] for c in cb["caps"]]).float()
    lpB = torch.log_softmax(zB.double(), -1)
    EI, wI = load_emb_norm("gemma")
    EB, wB = load_emb_norm("gemma_pt")
    EI_S, EB_S = EI[S].float(), EB[S].float()
    Dl = EB_S - EI_S
    mapped = sorted({int(t) for t in f["class_of"]})

    def m_rows(rows: torch.Tensor, h: torch.Tensor | None = None) -> np.ndarray:
        h = hfI if h is None else h
        z = softcap(h @ rows.T, cap)
        return (torch.logsumexp(z[:, :nD], -1) - torch.logsumexp(z[:, nD:], -1)).numpy()

    def zfull_rows(rows: torch.Tensor, h: torch.Tensor | None = None, base: torch.Tensor | None = None):
        h = hfI if h is None else h
        z = (zI if base is None else base).clone()
        z[:, S] = softcap(h @ rows.T, cap)
        return z

    def mets(z: torch.Tensor) -> dict[str, float]:
        lp = torch.log_softmax(z.double(), -1)
        p = lp.exp()
        return {"pD": float(p[:, D].sum(-1).mean()), "pA": float(p[:, A].sum(-1).mean()),
                "mapped": float(p[:, mapped].sum(-1).mean()), "unmapped": float(1 - p[:, mapped].sum(-1).mean()),
                "kl_arm_to_base": float((p * (lp - lpB)).sum(-1).mean())}
    eps = cfg["rms_norm_eps"]
    hI_Bn = rms_gemma(hpI, wB, eps)
    g_check = float(((rms_gemma(hpI, wI, eps) - hfI).norm(dim=-1) / hfI.norm(dim=-1)).max())
    arms: dict[str, tuple[np.ndarray, torch.Tensor | None]] = {
        "TWIN": (mI, zI), "ROWS_ALL": (m_rows(EB_S), zfull_rows(EB_S)),
        "ROWS_D": (m_rows(torch.cat([EB_S[:nD], EI_S[nD:]])), zfull_rows(torch.cat([EB_S[:nD], EI_S[nD:]]))),
        "ROWS_A": (m_rows(torch.cat([EI_S[:nD], EB_S[nD:]])), zfull_rows(torch.cat([EI_S[:nD], EB_S[nD:]])))}
    zN = softcap(torch.cat([hI_Bn @ EI[c:c + 16384].float().T for c in range(0, EI.shape[0], 16384)], -1), cap)
    arms["NORM"] = (m_rows(EI_S, hI_Bn), zN)
    arms["ROWS_NORM"] = (m_rows(EB_S, hI_Bn), zfull_rows(EB_S, hI_Bn, zN))
    for lam in DOSES + (SIGN_DOSE,):
        r = EI_S + lam * Dl
        arms[f"DOSE_{lam:g}" if lam != SIGN_DOSE else "SIGN"] = (m_rows(r), zfull_rows(r))
    rows_out = []
    summ: dict[str, Any] = {"utc": utc_now(), "cfg": cfg, "n_prompts": len(mI), "gap_mean": float((mI - mB).mean()),
                            "m_I_mean": float(mI.mean()), "m_B_mean": float(mB.mean()),
                            "rms_recompute_rel_err_max": g_check, "arms": {}}
    for a, (m, z) in arms.items():
        ent = {"share": share(mI, m, mB), "ci95": boot_share(mI, m, mB), "mean_margin": float(m.mean())}
        if z is not None:
            ent["dist_mean"] = mets(z)
        summ["arms"][a] = ent
        for i, c in enumerate(ci["caps"]):
            rows_out.append({"unit": UNIT, "pid": c["pid"], "arm": a, "draw": None, "m": float(m[i]),
                             "m_I": float(mI[i]), "m_B": float(mB[i])})
    summ["base_dist_mean"] = mets(zB)
    # nulls: RAND_ISO and DELTA_SWAP (50 each), committed seeds 101000/103000 + 100*unit_idx + k
    tok = AutoTokenizer.from_pretrained(model_path("gemma"))
    n_real = len(tok)
    dn = torch.empty(EI.shape[0])
    wn = torch.empty(EI.shape[0])
    for c in range(0, EI.shape[0], 16384):
        a_, b_ = EI[c:c + 16384].float(), EB[c:c + 16384].float()
        dn[c:c + 16384] = (b_ - a_).norm(dim=-1)
        wn[c:c + 16384] = a_.norm(dim=-1)
    ui = UNIT_IDX[UNIT]
    dnorm = Dl.norm(dim=-1).numpy()
    pools = {}
    for t in S:
        okn = ((dn - dn[t]).abs() <= DELTA_SWAP_TOL_DELTA * dn[t]) & ((wn - wn[t]).abs() <= DELTA_SWAP_TOL_W * wn[t])
        cand = [int(s) for s in torch.nonzero(okn).flatten().tolist() if s < n_real and s not in S]
        pools[t] = [s for s in cand if (lambda x: bool(x) and not any(e in x for e in DELTA_SWAP_EXCLUDE[UNIT]))(
            tok.decode([s]).strip().lower())]
    nulls: dict[str, Any] = {}
    obs = summ["arms"]["ROWS_ALL"]["share"]
    for nt in ("RAND_ISO", "DELTA_SWAP"):
        shs = []
        for k in range(N_NULL):
            used: set[int] = set()
            rows = EI_S.clone()
            for j, t in enumerate(S):
                rng = np.random.default_rng([NULL_SEED0[nt] + 100 * ui + k, t])
                if nt == "RAND_ISO":
                    g = rng.standard_normal(EI.shape[1])
                    rows[j] += torch.from_numpy((dnorm[j] * g / np.linalg.norm(g)).astype(np.float32))
                else:
                    cand = [s for s in pools[t] if s not in used] or pools[t]
                    s = cand[int(rng.integers(len(cand)))]
                    used.add(s)
                    rows[j] += EB[s].float() - EI[s].float()
            m = m_rows(rows)
            shs.append(share(mI, m, mB))
            for i, c in enumerate(ci["caps"]):
                rows_out.append({"unit": UNIT, "pid": c["pid"], "arm": nt, "draw": k, "m": float(m[i]),
                                 "m_I": float(mI[i]), "m_B": float(mB[i])})
        a_ = np.array(shs)
        nulls[nt] = {"shares": shs, "median": float(np.median(a_)), "p95": float(np.percentile(a_, 95)),
                     "max": float(a_.max()), "empirical_p_rows_all": float((1 + (a_ >= obs).sum()) / (1 + len(a_)))}
    summ["nulls"] = nulls
    summ["pool_sizes"] = {tok.decode([t]): len(pools[t]) for t in S}
    # reproduction of iteration 9's B1 values (chat): mean margins within 0.05 nats
    b1 = read_json(I9_RES / "b1_gemma_G-GRID.json")["forks"]["G-GRID@32"]["chat"]
    summ["reproduction_b1"] = {"mean_m_I": float(mI.mean()), "mean_m_I_iter9": float(np.mean(b1["margin_instr"])),
                               "mean_m_B": float(mB.mean()), "mean_m_B_iter9": float(np.mean(b1["margin_base"])),
                               "gain_iter9": b1["gain_mean"], "pD_instr_iter9": b1["pD_instr_mean"],
                               "pD_base_iter9": b1["pD_base_mean"],
                               "pD_instr_here": summ["arms"]["TWIN"]["dist_mean"]["pD"],
                               "pD_base_here": summ["base_dist_mean"]["pD"]}
    rp = summ["reproduction_b1"]
    rp["pass"] = abs(rp["mean_m_I"] - rp["mean_m_I_iter9"]) <= 0.05 and abs(rp["mean_m_B"] - rp["mean_m_B_iter9"]) <= 0.05
    summ["seconds"] = round(time.time() - t0, 1)
    write_jsonl(RESULTS_DIR / "w3_rows.jsonl", rows_out)
    write_json(RESULTS_DIR / "w3_summary.json", summ)
    partial_status("W3", rows_all=obs)
    logger.info(f"W3: gap {summ['gap_mean']:.3f}; ROWS_ALL {obs:.3f}; ROWS_D {summ['arms']['ROWS_D']['share']:.3f}; "
                f"ROWS_A {summ['arms']['ROWS_A']['share']:.3f}; ROWS_NORM {summ['arms']['ROWS_NORM']['share']:.3f}; "
                f"RAND_ISO median {nulls['RAND_ISO']['median']:.3f} max {nulls['RAND_ISO']['max']:.3f}; DELTA_SWAP "
                f"p95 {nulls['DELTA_SWAP']['p95']:.3f}; reproduction {rp}")
    return summ


if __name__ == "__main__":
    setup_logging(f"w3_gemma_{sys.argv[1]}")
    if sys.argv[1] == "gpu":
        gpu(sys.argv[2])
    else:
        score()
