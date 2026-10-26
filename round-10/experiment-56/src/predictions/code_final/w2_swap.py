#!/usr/bin/env python3
"""W2: do the late-MLP WEIGHTS (layers 26-35) carry the part of the gap the readout does not?

  match  (CPU) per-layer MLP weight deltas N_l = sqrt(||dGate||^2 + ||dUp||^2 + ||dDown||^2) and relative changes for
         l = 0..35 (checked against iteration 9's weight_change.json), Hungarian matching of the late set 26..35 to the
         early pool 2..13 on |log N_l - log N_e|, joint-scale c = ||dW_late_joint|| / ||dW_early_joint||; COMMIT #3
         before any W2 forward.
  gpu    (instruct model) SCOPE A all-position (primary): base weights swapped into the module in place, prefix KV and
         the one-token fork forward recomputed (iteration 9's path, B_ot), margin read with the instruct readout
         (and DECOMP with the base readout on the swapped run's h_pre). Arms: W_l singles, W_late_joint, E_match(l)
         singles (true base weights), E_joint (scaled by c), RANDDELTA_l x 3 and RANDDELTA_joint x 3 (per-matrix
         Gaussian scaled to that matrix's ||dW||), ATTN_late_joint (q/k/v/o + q/k norms of 26..35).
         SCOPE B fork-only (bridge to iteration 9's W arm): cmap9.OneTok 'mlpw' rows (base MLP on the live fork
         input, CPU fp32), singles 26..35, the joint of the 10 and iteration 9's joint of (26, 27, 28, 30, 32).
  summary (CPU) shares, bootstrap CIs, per-prompt distributions, the W2 rule and the weight-level decomposition.
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

from cfg10 import (CACHE_DIR, EARLY_POOL, I9_RES, ITER9_W_LAYERS, LATE, N_LAYERS, N_RANDDELTA, RANDDELTA_SEED0,
                   RESULTS_DIR, THRESH, UNITS_TF, append_jsonl, commit, import_iter9, ledger, log_deviation,
                   model_path, partial_status, read_json, read_jsonl, setup_logging, utc_now, write_json)

import_iter9()
import cmap9 as CM  # noqa: E402

MATS = ("gate_proj", "up_proj", "down_proj")
ATTN = ("q_proj", "k_proj", "v_proj", "o_proj", "q_norm", "k_norm")
ROWS_OUT = RESULTS_DIR / "w2_rows.jsonl"


class Shards:
    def __init__(self, key: str):
        self.p = Path(model_path(key))
        self.wm = json.loads((self.p / "model.safetensors.index.json").read_text())["weight_map"]

    def get(self, name: str) -> torch.Tensor:
        with safe_open(str(self.p / self.wm[name]), framework="pt") as fh:
            return fh.get_tensor(name)


def mlp_name(l: int, m: str) -> str:
    return f"model.layers.{l}.mlp.{m}.weight"


def attn_name(l: int, m: str) -> str:
    return f"model.layers.{l}.self_attn.{m}.weight"


# ================================================================================================ matching
def match() -> dict[str, Any]:
    from scipy.optimize import linear_sum_assignment
    t0 = time.time()
    I, B = Shards("qwen"), Shards("qwen_base")
    per: dict[str, Any] = {"N": [], "rel": {m: [] for m in MATS}, "dnorm": {m: [] for m in MATS}}
    for l in range(N_LAYERS):
        tot = 0.0
        for m in MATS:
            a, b = I.get(mlp_name(l, m)).float(), B.get(mlp_name(l, m)).float()
            dn = float((b - a).norm())
            per["dnorm"][m].append(dn)
            per["rel"][m].append(float((a - b).norm() / b.norm()))
            tot += dn ** 2
            del a, b
        per["N"].append(float(np.sqrt(tot)))
    wc = read_json(I9_RES / "weight_change.json")["per_layer"]
    chk = {m: float(np.max(np.abs(np.array(per["rel"][m]) - np.array(wc[m.split("_")[0]])))) for m in MATS}
    N = np.array(per["N"])
    late, early = list(LATE), list(EARLY_POOL)
    cost = np.abs(np.log(N[late])[:, None] - np.log(N[early])[None, :])
    r, c = linear_sum_assignment(cost)
    pairs = {int(late[i]): int(early[j]) for i, j in zip(r, c)}
    late_joint = float(np.sqrt(np.sum(N[late] ** 2)))
    early_joint = float(np.sqrt(np.sum(N[list(pairs.values())] ** 2)))
    out = {"utc": utc_now(), "per_layer_N": per["N"], "per_layer_rel_change": per["rel"],
           "per_layer_matrix_dnorm": per["dnorm"], "check_vs_iter9_weight_change_max_abs": chk,
           "check_pass": all(v <= 1e-3 for v in chk.values()), "late": late, "early_pool": early,
           "pairs_late_to_early": pairs, "n_early_used": len(set(pairs.values())),
           "matching_cost_total": float(cost[r, c].sum()),
           "matched_log_ratio": {str(l): float(np.log(N[l] / N[e])) for l, e in pairs.items()},
           "late_joint_norm": late_joint, "early_joint_norm": early_joint, "c_joint_scale": late_joint / early_joint,
           "effective_set_size": {"late": len(set(late)), "early": len(set(pairs.values()))},
           "seconds": round(time.time() - t0, 1)}
    write_json(RESULTS_DIR / "w2_matching.json", out)
    if not out["check_pass"]:
        log_deviation("w2_weight_change_check", f"per-layer relative MLP change differs from iteration 9's "
                                                f"weight_change.json by {chk} (> 1e-3)")
    commit("commit3_w2_matching", {"pairs": pairs, "c": out["c_joint_scale"],
                                   "note": "matching committed before any W2 forward"},
           files=[RESULTS_DIR / "w2_matching.json"])
    ledger("COMMIT3")
    logger.info(f"matching {pairs}, c = {out['c_joint_scale']:.3f}, check {chk}")
    return out


# ================================================================================================ GPU
class Swapper:
    """In-place weight swaps on the GPU with CPU copies of the instruct tensors; restore asserts torch.equal."""

    def __init__(self, model: Any, layers_mlp: list[int], layers_attn: list[int]):
        self.model = model
        self.orig: dict[tuple[int, str], torch.Tensor] = {}
        for l in layers_mlp:
            for m in MATS:
                self.orig[(l, m)] = self.param(l, m).detach().cpu().clone()
        for l in layers_attn:
            for m in ATTN:
                self.orig[(l, m)] = self.param(l, m).detach().cpu().clone()
        self.touched: list[tuple[int, str]] = []

    def param(self, l: int, m: str) -> torch.nn.Parameter:
        L = self.model.model.layers[l]
        return getattr(L.mlp, m).weight if m in MATS else getattr(L.self_attn, m).weight

    def set(self, l: int, m: str, t: torch.Tensor) -> None:
        p = self.param(l, m)
        assert p.shape == t.shape, (l, m, p.shape, t.shape)
        p.data.copy_(t.to(p.device, p.dtype))
        self.touched.append((l, m))

    def restore(self) -> bool:
        ok = True
        for (l, m) in self.touched:
            p = self.param(l, m)
            p.data.copy_(self.orig[(l, m)].to(p.device))
            ok &= bool(torch.equal(p.data, self.orig[(l, m)].to(p.device)))
        self.touched = []
        return ok


@torch.no_grad()
def fork_states(model: Any, ids: list[int], B: int) -> tuple[torch.Tensor, torch.Tensor]:
    """(h_fin bf16 [d], h_pre bf16 [d]) at the fork on the one-token path (full prefix recompute)."""
    st: dict[str, torch.Tensor] = {}

    def pre_norm(m, args, kwargs):
        x = args[0] if args else kwargs["hidden_states"]
        st["h_pre"] = x[0, -1].detach().clone()
    h = model.model.norm.register_forward_pre_hook(pre_norm, with_kwargs=True)
    try:
        kv = CM.prefix_kv(model, ids)
        cache = CM.build_cache(kv, B)
        pos = len(ids) - 1
        o = model.model(input_ids=torch.full((B, 1), ids[-1], device="cuda", dtype=torch.long),
                        past_key_values=cache, position_ids=torch.full((B, 1), pos, device="cuda"),
                        cache_position=torch.tensor([pos], device="cuda"), use_cache=True)
    finally:
        h.remove()
    out = (o.last_hidden_state[0, -1].detach().clone(), st["h_pre"])
    del o, cache, kv
    return out


def rand_like_scaled(shape: tuple[int, ...], target_norm: float, seed: int) -> torch.Tensor:
    g = torch.Generator(device="cuda")
    g.manual_seed(int(seed))
    R = torch.randn(shape, generator=g, device="cuda", dtype=torch.float32)
    return R * (target_norm / R.norm())


@torch.no_grad()
def gpu(max_prompts: int | None = None, with_attn: bool = True) -> None:
    from capture10 import load
    from w1_tf import load_readout, rms_bf16
    t0 = time.time()
    ledger("W2_start")
    model, tok, info = load("qwen")
    units = read_json(I9_RES / "units.json")
    mt = read_json(RESULTS_DIR / "w2_matching.json")
    pairs = {int(k): int(v) for k, v in mt["pairs_late_to_early"].items()}
    c_joint = float(mt["c_joint_scale"])
    dnorm = mt["per_layer_matrix_dnorm"]
    Bsh = Shards("qwen_base")
    WB_full, gB = load_readout("qwen_base")
    B_ot = read_json(RESULTS_DIR / "capture_instr.json")["B_ot"]
    W = model.lm_head.weight
    sw = Swapper(model, sorted(set(LATE) | set(pairs.values())), list(LATE) if with_attn else [])
    U = {}
    for u in UNITS_TF:
        f = units[u]["forks"][0]
        S = [int(t) for t in f["D"]] + [int(t) for t in f["A"]]
        ci = torch.load(CACHE_DIR / f"fork_instr_{u}.pt")
        cb = torch.load(CACHE_DIR / f"fork_base_{u}.pt")
        prompts = units[u]["prompts"][:max_prompts] if max_prompts else units[u]["prompts"]
        U[u] = {"f": f, "S": S, "nD": len(f["D"]), "prompts": prompts, "WI_S": W[S].float(),
                "WB_S": WB_full[S].float().cuda(), "mI": {c["pid"]: c["m"] for c in ci["caps"]},
                "mB": {c["pid"]: c["m"] for c in cb["caps"]}, "mlp_in": {c["pid"]: c["mlp_in"] for c in ci["caps"]}}
        del ci, cb
    gB = gB.cuda()
    done = {(r["scope"], r["config"], r["unit"], r["pid"]) for r in read_jsonl(ROWS_OUT)}
    tests: dict[str, Any] = {}

    def margin_of(h: torch.Tensor, rows: torch.Tensor, nD: int) -> float:
        z = h.float() @ rows.T
        return float(torch.logsumexp(z[:nD], -1) - torch.logsumexp(z[nD:], -1))

    def run_config(name: str, apply_fn, decomp: bool = False) -> dict[str, float]:
        if all(("A", name, u, p["pid"]) in done for u in UNITS_TF for p in U[u]["prompts"]):
            return {}
        tc = time.time()
        apply_fn()
        recs = []
        try:
            for u in UNITS_TF:
                d = U[u]
                for p in d["prompts"]:
                    ids = p["ids"] + d["f"]["opening"]
                    hf, hp = fork_states(model, ids, B_ot)
                    r = {"scope": "A", "config": name, "unit": u, "pid": p["pid"], "template": p["template"],
                         "m": margin_of(hf, d["WI_S"], d["nD"]), "m_I": d["mI"][p["pid"]], "m_B": d["mB"][p["pid"]],
                         "utc": utc_now()}
                    if decomp:
                        hb = rms_bf16(hp.float().cpu(), gB.cpu()).cuda()
                        r["m_decomp_rows_norm"] = margin_of(hb, d["WB_S"], d["nD"])
                        r["m_rows_only"] = margin_of(hf, d["WB_S"], d["nD"])
                    recs.append(r)
        finally:
            ok = sw.restore()
        if not ok:
            raise RuntimeError(f"restore failed after {name}")
        append_jsonl(ROWS_OUT, recs)
        sh = {u: float(sum(r["m_I"] - r["m"] for r in recs if r["unit"] == u) /
                       sum(r["m_I"] - r["m_B"] for r in recs if r["unit"] == u)) for u in UNITS_TF}
        logger.info(f"[A] {name}: share T10 {sh['T10']:.3f} B3 {sh['B3']:.3f} ({time.time() - tc:.1f}s)")
        return sh

    def base_mlp(l: int) -> None:
        for m in MATS:
            sw.set(l, m, Bsh.get(mlp_name(l, m)))

    def scaled_delta_mlp(l: int, c: float) -> None:
        for m in MATS:
            a = sw.orig[(l, m)].float()
            b = Bsh.get(mlp_name(l, m)).float()
            sw.set(l, m, (a + c * (b - a)).to(torch.bfloat16))
            del a, b

    def rand_delta_mlp(l: int, seed: int) -> None:
        for j, m in enumerate(MATS):
            p = sw.param(l, m)
            R = rand_like_scaled(tuple(p.shape), dnorm[m][l], seed * 10 + j)
            sw.set(l, m, (sw.orig[(l, m)].to("cuda").float() + R).to(torch.bfloat16))
            del R

    def base_attn(l: int) -> None:
        for m in ATTN:
            sw.set(l, m, Bsh.get(attn_name(l, m)))

    # ---------------- G3: swap one MLP and restore; TWIN margin bit-identical before and after
    d0 = U["T10"]
    p0 = d0["prompts"][0]
    ids0 = p0["ids"] + d0["f"]["opening"]
    m_before = margin_of(fork_states(model, ids0, B_ot)[0], d0["WI_S"], d0["nD"])
    base_mlp(30)
    m_sw = margin_of(fork_states(model, ids0, B_ot)[0], d0["WI_S"], d0["nD"])
    ok = sw.restore()
    m_after = margin_of(fork_states(model, ids0, B_ot)[0], d0["WI_S"], d0["nD"])
    tests["G3"] = {"restore_equal": ok, "m_before": m_before, "m_swapped_L30": m_sw, "m_after": m_after,
                   "bit_identical": m_before == m_after, "m_S0": d0["mI"][p0["pid"]],
                   "matches_S0": m_before == d0["mI"][p0["pid"]]}
    logger.info(f"G3 {tests['G3']}")
    # ---------------- SCOPE A configurations (order: primary first, controls, then optional)
    configs: list[tuple[str, Any, bool]] = []
    for l in LATE:
        configs.append((f"W{l}", (lambda l=l: base_mlp(l)), False))
    configs.append(("W_late_joint", (lambda: [base_mlp(l) for l in LATE]), True))
    for l in LATE:
        configs.append((f"E_match{l}_L{pairs[l]}", (lambda e=pairs[l]: base_mlp(e)), False))
    configs.append(("E_joint", (lambda: [scaled_delta_mlp(e, c_joint) for e in pairs.values()]), False))
    for j in range(N_RANDDELTA):
        configs.append((f"RANDDELTA_joint_{j}", (lambda j=j: [rand_delta_mlp(l, RANDDELTA_SEED0 + 5000 + 100 * j + l)
                                                              for l in LATE]), False))
    for l in LATE:
        for j in range(N_RANDDELTA):
            configs.append((f"RANDDELTA{l}_{j}", (lambda l=l, j=j: rand_delta_mlp(l, RANDDELTA_SEED0 + 100 * j + l)),
                            False))
    if with_attn:
        configs.append(("ATTN_late_joint", (lambda: [base_attn(l) for l in LATE]), False))
        configs.append(("BLOCKS_late_joint", (lambda: [base_attn(l) for l in LATE] + [base_mlp(l) for l in LATE]),
                        True))
    tcfg = []
    for ci_, (name, fn, dec) in enumerate(configs):
        tb = time.time()
        run_config(name, fn, dec)
        tcfg.append(time.time() - tb)
        if ci_ % 10 == 9:
            chk = []
            for p in d0["prompts"][:2]:
                ids = p["ids"] + d0["f"]["opening"]
                mm = margin_of(fork_states(model, ids, B_ot)[0], d0["WI_S"], d0["nD"])
                chk.append({"pid": p["pid"], "m": mm, "m_S0": d0["mI"][p["pid"]], "equal": mm == d0["mI"][p["pid"]]})
            tests.setdefault("twin_rechecks", []).append({"after_config": name, "checks": chk})
            if not all(x["equal"] for x in chk):
                log_deviation(f"w2_twin_recheck_{name}", f"TWIN margin re-check after {name} not bit-exact: {chk}")
            partial_status("W2_scopeA", n_configs_done=ci_ + 1, n_configs=len(configs))
    # ---------------- SCOPE B fork-only (iteration 9's W-arm semantics)
    base_w = {}
    for l in LATE:
        base_w[l] = {m: Bsh.get(mlp_name(l, m)).float() for m in MATS}
    ot = CM.OneTok(model, base_w)
    names = ["none"] + [f"Wf{l}" for l in LATE] + ["Wf_joint10", "Wf_iter9_joint5"]
    rows = [[]] + [[("mlpw", l)] for l in LATE] + [[("mlpw", l) for l in LATE], [("mlpw", l) for l in ITER9_W_LAYERS]]
    g4 = []
    for u in UNITS_TF:
        d = U[u]
        R = CM.Readout(model, d["f"], tok)
        for p in d["prompts"]:
            if ("B", "none", u, p["pid"]) in done:
                continue
            ids = p["ids"] + d["f"]["opening"]
            kv = CM.prefix_kv(model, ids)
            res = CM.run_onetok(model, ot, kv, ids[-1], len(ids) - 1, rows, R, set(), set(), d["f"]["D"],
                                d["f"]["A"], max_rows=B_ot)
            recs = []
            for nm, rr in zip(names, res):
                recs.append({"scope": "B", "config": nm, "unit": u, "pid": p["pid"], "template": p["template"],
                             "m": rr["m"], "m_raw": rr["m_raw"], "m_I": d["mI"][p["pid"]], "m_B": d["mB"][p["pid"]],
                             "m_row0": res[0]["m"], "utc": utc_now()})
            append_jsonl(ROWS_OUT, recs)
            # G4 on the first prompt: hook output vs a CPU fp32 recompute of the base MLP on the captured input
            if len(g4) < 2:
                l = 30
                x = d["mlp_in"][p["pid"]][l].float()
                Wl = base_w[l]
                y = (torch.nn.functional.silu(x @ Wl["gate_proj"].T) * (x @ Wl["up_proj"].T)) @ Wl["down_proj"].T
                cap: dict[str, torch.Tensor] = {}
                # the OneTok replacement hook is registered FIRST so the capture hook sees the replaced output
                hs_ = ot.hooks([[], [("mlpw", l)]] + [[] for _ in range(B_ot - 2)])
                hs_.append(model.model.layers[l].mlp.register_forward_hook(
                    lambda m_, i_, o_: cap.__setitem__("y", o_[1, -1].detach().float().cpu())))
                try:
                    cache_ = CM.build_cache(kv, B_ot)
                    pos_ = len(ids) - 1
                    model.model(input_ids=torch.full((B_ot, 1), ids[-1], device="cuda", dtype=torch.long),
                                past_key_values=cache_, position_ids=torch.full((B_ot, 1), pos_, device="cuda"),
                                cache_position=torch.tensor([pos_], device="cuda"), use_cache=True)
                    del cache_
                finally:
                    for h_ in hs_:
                        h_.remove()
                g4.append({"unit": u, "pid": p["pid"], "layer": l,
                           "rel_err_hook_vs_cpu_fp32": float((cap["y"] - y).norm() / y.norm())})
            del kv
        logger.info(f"[B] {u} done")
    tests["G4"] = {"checks": g4, "pass_bf16_rounding": all(x["rel_err_hook_vs_cpu_fp32"] <= 1e-2 for x in g4),
                   "note": "the hook output is bf16, so the attainable agreement is bf16 rounding (~2e-3 relative)"}
    write_json(RESULTS_DIR / "tests_gpu_w2.json", {"utc": utc_now(), "load": info, **tests,
                                                    "config_seconds": tcfg, "seconds": round(time.time() - t0, 1)})
    ledger("W2_end", seconds=round(time.time() - t0, 1))


# ================================================================================================ summary
def summary() -> dict[str, Any]:
    from w1_tf import boot_share, share
    rows = read_jsonl(ROWS_OUT)
    mt = read_json(RESULTS_DIR / "w2_matching.json")
    w1 = read_json(RESULTS_DIR / "w1_tf_summary.json")
    i9 = read_json(I9_RES / "b2_summary.json")
    out: dict[str, Any] = {"utc": utc_now(), "matching": {k: mt[k] for k in ("pairs_late_to_early", "c_joint_scale",
                                                                              "check_pass")}, "units": {}}
    for u in UNITS_TF:
        ur = [r for r in rows if r["unit"] == u]
        pids = sorted({r["pid"] for r in ur}, key=lambda p: [x["pid"] for x in ur].index(p))
        res: dict[str, Any] = {"A": {}, "B": {}}
        for scope in ("A", "B"):
            for cfgname in sorted({r["config"] for r in ur if r["scope"] == scope}):
                rr = {r["pid"]: r for r in ur if r["scope"] == scope and r["config"] == cfgname}
                if len(rr) != len(pids):
                    continue
                mI = np.array([rr[p]["m_I"] for p in pids])
                mX = np.array([rr[p]["m"] for p in pids])
                mB = np.array([rr[p]["m_B"] for p in pids])
                gap = mI - mB
                ent = {"share": share(mI, mX, mB), "ci95": boot_share(mI, mX, mB),
                       "per_prompt_share": ((mI - mX) / gap).tolist(), "mean_margin": float(mX.mean())}
                if "m_decomp_rows_norm" in rr[pids[0]]:
                    mD = np.array([rr[p]["m_decomp_rows_norm"] for p in pids])
                    ent["decomp_share_with_rows_norm_readout"] = share(mI, mD, mB)
                    ent["decomp_ci95"] = boot_share(mI, mD, mB)
                    mR = np.array([rr[p]["m_rows_only"] for p in pids])
                    ent["share_with_rows_only_readout"] = share(mI, mR, mB)
                    ent["_mD"] = mD.tolist()
                ent["_mX"] = mX.tolist()
                res[scope][cfgname] = ent
        A = res["A"]
        mI = np.array([r["m_I"] for r in ur if r["scope"] == "A" and r["config"] == "W_late_joint"])
        mB = np.array([r["m_B"] for r in ur if r["scope"] == "A" and r["config"] == "W_late_joint"])
        rule: dict[str, Any] = {}
        if "W_late_joint" in A and "E_joint" in A:
            mL = np.array(A["W_late_joint"]["_mX"])
            mE = np.array(A["E_joint"]["_mX"])
            diff = share(mI, mL, mB) - share(mI, mE, mB)
            rng = np.random.default_rng(20261024)
            idx = rng.integers(0, len(mI), (10000, len(mI)))
            den = (mI - mB)[idx].sum(1)
            bd = ((mI - mL)[idx].sum(1) - (mI - mE)[idx].sum(1)) / den
            ci = (float(np.percentile(bd, 2.5)), float(np.percentile(bd, 97.5)))
            rj = [A[k]["share"] for k in A if k.startswith("RANDDELTA_joint_")]
            rule = {"late_joint": A["W_late_joint"]["share"], "early_joint": A["E_joint"]["share"],
                    "diff": diff, "diff_ci95": ci, "randdelta_joint_shares": rj,
                    "randdelta_joint_max": max(rj) if rj else None,
                    "holds": bool(diff >= THRESH["W2_late_minus_early"] and ci[0] > 0 and
                                  (not rj or A["W_late_joint"]["share"] > max(rj)))}
        singles = []
        pairs = {int(k): int(v) for k, v in mt["pairs_late_to_early"].items()}
        for l in LATE:
            if f"W{l}" not in A:
                continue
            e = pairs[l]
            rd = [A[f"RANDDELTA{l}_{j}"]["share"] for j in range(N_RANDDELTA) if f"RANDDELTA{l}_{j}" in A]
            singles.append({"layer": l, "share": A[f"W{l}"]["share"], "ci95": A[f"W{l}"]["ci95"], "early_layer": e,
                            "early_share": A.get(f"E_match{l}_L{e}", {}).get("share"), "randdelta_shares": rd,
                            "above_all_randdelta": bool(rd and A[f"W{l}"]["share"] > max(rd)),
                            "fork_only_share": res["B"].get(f"Wf{l}", {}).get("share")})
        singles.sort(key=lambda r: -r["share"])
        # decomposition: readout (ROWS_NORM, W1), late MLPs (all-position), joint (DECOMP)
        rd_share = w1["units"][u]["arms"]["ROWS_NORM"]["share"]
        dec = None
        if "W_late_joint" in A:
            late = A["W_late_joint"]["share"]
            joint = A["W_late_joint"].get("decomp_share_with_rows_norm_readout")
            dec = {"readout_rows_norm": rd_share, "late_mlps_all_position": late, "joint_late_mlps_plus_readout": joint,
                   "interaction": joint - rd_share - late if joint is not None else None,
                   "remainder": 1 - joint if joint is not None else None}
            if "BLOCKS_late_joint" in A:
                dec["late_blocks_all_position"] = A["BLOCKS_late_joint"]["share"]
                dec["joint_late_blocks_plus_readout"] = A["BLOCKS_late_joint"].get(
                    "decomp_share_with_rows_norm_readout")
            if "ATTN_late_joint" in A:
                dec["late_attention_all_position"] = A["ATTN_late_joint"]["share"]
        # bridge to iteration 9's fork-only W arm
        i9w = i9["units"][u]["arms"]
        bridge = {}
        for l in ITER9_W_LAYERS:
            ours = res["B"].get(f"Wf{l}", {}).get("share")
            theirs = i9w.get(f"W{l}", {}).get("share")
            bridge[f"W{l}"] = {"here": ours, "iter9": theirs,
                               "abs_diff": abs(ours - theirs) if ours is not None and theirs is not None else None}
        ours = res["B"].get("Wf_iter9_joint5", {}).get("share")
        theirs = i9w.get("W_all", {}).get("share")
        bridge["W_all5"] = {"here": ours, "iter9": theirs,
                            "abs_diff": abs(ours - theirs) if ours is not None and theirs is not None else None}
        bridge["pass"] = all(v["abs_diff"] is not None and v["abs_diff"] <= THRESH["W2_bridge_tol"]
                             for k, v in bridge.items() if isinstance(v, dict))
        for scope in ("A", "B"):
            for k in res[scope]:
                res[scope][k].pop("_mX", None)
                res[scope][k].pop("_mD", None)
        out["units"][u] = {"scope_A_all_position": res["A"], "scope_B_fork_only": res["B"], "rule": rule,
                           "singles_ranked": singles, "decomposition": dec, "bridge_iter9": bridge,
                           "rule_role": "secondary" if u == "T10" else "descriptive"}
        logger.info(f"W2 {u}: rule {rule}; decomposition {dec}; bridge pass {bridge['pass']}")
    write_json(RESULTS_DIR / "w2_summary.json", out)
    write_json(RESULTS_DIR / "decomposition.json", {u: out["units"][u]["decomposition"] for u in out["units"]})
    partial_status("W2_summary")
    return out


if __name__ == "__main__":
    setup_logging(f"w2_swap_{sys.argv[1]}")
    cmd = sys.argv[1]
    if cmd == "gpu":
        mp = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] != "all" else None
        gpu(mp)
    else:
        {"match": match, "summary": summary}[cmd]()
