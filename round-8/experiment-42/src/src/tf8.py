#!/usr/bin/env python3
"""S3 teacher-forced stage (no sampling): 3a fork distributions at p_f for every prefilled condition, 3b log P(c* |
prompt), 3c DiM betas matched by grid scan + bisection on this engine, 3d dormancy at k in {1, 2, 4, 8}:
(i) reverse interchange (forced-BFS bases <- twin-variant sources) vs the same-site full-state reverse, with a Haar
null; (ii) projected-map retention on the top natural PCs, the Makelov residual check and sensitivities; (iii) natural
variance against 1,000 Haar subspaces (also on iteration 7's cached states, which must reproduce its numbers);
(iv) principal angles across the 3 fitting seeds. Every margin difference is taken on one path (the single-position
KV path of g2.forward_from, fixed batch shape 48) against the base's own margin on that path (U3)."""

from __future__ import annotations

import gc
import time
from typing import Any, Callable

import numpy as np
import torch
from loguru import logger

import fork7 as FK
import g2
from cfg import (B_IDS, D_IDS, D_MODEL, HELD_F, N_LAYERS, RESULTS_DIR, SUBSPACE_DIR, TEMPLATE_IDS, TRAIN_F, read_json,
                 write_json)
from cfg8 import (HELD_W, I7, KSTAR, L, MIN_DENOM_NAT, N_BOOT_PAIRS, N_HAAR_REV, N_HAAR_VAR, PC_MAIN, PC_SENS, Q_ID,
                  RANKS, SEEDS, TRAIN_W, VISITED_ID)
from gen7 import Edit


# ================================================================================================ maps and edits
def load_maps() -> dict[str, Any]:
    R = {sd: torch.load(SUBSPACE_DIR / f"das_L{L}_seed{sd}.pt").float().cuda() for sd in SEEDS}
    u = torch.load(SUBSPACE_DIR / f"dim_L{L}.pt").float().cuda()
    Rr = torch.linalg.qr(torch.randn(D_MODEL, KSTAR, generator=torch.Generator().manual_seed(31337)).cuda())[0]
    return {"R": R, "u": u, "Rr": Rr}


def class_targets(S: list[dict], drop: set[int], R: torch.Tensor, Hkey: Callable[[dict], torch.Tensor]
                  ) -> dict[str, torch.Tensor]:
    trs = sorted({j for j, s in enumerate(S) if s["template"] in TRAIN_F and j not in drop})
    Hs = torch.stack([Hkey(S[j]) for j in trs]).cuda().float()
    modes = [S[j]["mode"] for j in trs]
    return {Y: (Hs[[i for i, m in enumerate(modes) if m == Y]] @ R).mean(0) for Y in ("bfs", "dfs")}


def das_fn(Rk: torch.Tensor, cY: torch.Tensor, lam: float) -> Callable[[torch.Tensor], torch.Tensor]:
    return lambda h: h + lam * ((cY[None] - h @ Rk) @ Rk.T)


def dim_fn(u: torch.Tensor, beta: float) -> Callable[[torch.Tensor], torch.Tensor]:
    return lambda h: h + beta * u[None]


def interchange_fn(Rk: torch.Tensor, hsrc: torch.Tensor) -> Callable[[torch.Tensor], torch.Tensor]:
    return lambda h: h + ((hsrc[None] - h) @ Rk) @ Rk.T


def full_fn(hsrc: torch.Tensor) -> Callable[[torch.Tensor], torch.Tensor]:
    return lambda h: hsrc[None].expand_as(h).clone()


def prefill_edit(f: Callable[[torch.Tensor], torch.Tensor], pf: int, name: str, log: dict | None = None) -> Edit:
    return Edit("resid", L, [pf], (lambda x, r, f=f: f(x.reshape(-1, D_MODEL)).reshape(x.shape)), name=name,
                log=dict(log or {}, layer=L))


# ================================================================================================ calibration
def token_calibration() -> dict[str, Any]:
    """P(attempted/correct BFS|DFS | fork token) from iteration 7's G3-cal rows (prefill c* + forced token, N = 125
    each, main engine); ' q' (not calibrated) takes iteration 6's p_bfs and the mean correctness of the calibrated
    B tokens other than ' queue'."""
    from cfg import read_jsonl

    rows = [r for r in read_jsonl(I7 / "data" / "labels.jsonl") if str(r.get("row_id", "")).startswith("g3cal|")]
    tab: dict[int, dict[str, float]] = {}
    for t in (53227, 107, 584, 15204):
        rr = [r for r in rows if int(r["row_id"].split("|")[1]) == t]
        n = len(rr)
        tab[t] = {"n": n, "p_bfs": sum(r["label"] == "bfs" for r in rr) / n,
                  "p_dfs": sum(r["label"] == "dfs" for r in rr) / n,
                  "p_correct_bfs": sum(r["label"] == "bfs" and r["passed"] for r in rr) / n,
                  "p_correct_dfs": sum(r["label"] == "dfs" and r["passed"] for r in rr) / n,
                  "pass": sum(bool(r["passed"]) for r in rr) / n, "source": "iter7 G3-cal (N=125)"}
    tt = FK.token_table()
    q = 236809
    tab[q] = {"n": int(tt[q]["n"]), "p_bfs": float(tt[q]["p_bfs"]), "p_dfs": 1 - float(tt[q]["p_bfs"]),
              "p_correct_bfs": float(np.mean([tab[t]["p_correct_bfs"] / max(tab[t]["p_bfs"], 1e-9) for t in (107, 584)]))
              * float(tt[q]["p_bfs"]), "p_correct_dfs": 0.0, "pass": float("nan"),
              "source": "iteration 6 token table (n=3) x mean correctness of newline/'if' BFS programs"}
    return {int(k): v for k, v in tab.items()}


def fork_stats(lg: torch.Tensor, cal: dict[int, dict[str, float]]) -> dict[str, float]:
    p = torch.softmax(lg.float(), -1)
    z = lg.float()
    out = {"m": float(torch.logsumexp(z[list(B_IDS)], -1) - z[D_IDS[0]]), "p_B": float(p[list(B_IDS)].sum()),
           "p_D": float(p[list(D_IDS)].sum()), "p_queue": float(p[Q_ID]), "p_visited": float(p[VISITED_ID])}
    for nm, key in (("pred_attempted_bfs", "p_bfs"), ("pred_attempted_dfs", "p_dfs"),
                    ("pred_correct_bfs", "p_correct_bfs"), ("pred_correct_dfs", "p_correct_dfs")):
        out[nm] = float(sum(float(p[t]) * cal[t][key] for t in cal))
    top = torch.topk(p, 5)
    out["top5"] = [[int(i), float(v)] for v, i in zip(top.values, top.indices)]
    return out


# ================================================================================================ contexts
class Ctx:
    """Single-position KV-path context at block L for arbitrary base groups (generalises g2.DASContext)."""

    BFIX = 48

    def __init__(self, run: Any, bases: list[dict], groups: list[str], Hb: torch.Tensor, stacks: dict[str, Any]):
        self.run = run
        self.bases = bases
        self.Hb = Hb.cuda().float()
        self.idx = {g: [i for i, b in enumerate(bases) if b["template"] == g] for g in groups}
        self.local = {g: {gi: j for j, gi in enumerate(ix)} for g, ix in self.idx.items()}
        self.pos = {b["template"]: b["P"] + 31 for b in bases}
        self.K, self.V = stacks["K"], stacks["V"]
        yb = torch.zeros(len(bases), device="cuda")
        with torch.no_grad():
            for g, ix in self.idx.items():
                for c0 in range(0, len(ix), self.BFIX):
                    cix = ix[c0:c0 + self.BFIX]
                    yb[cix] = g2.margin(self.logits(g, cix, self.Hb[cix]))
        self.yb = yb

    @torch.no_grad()
    def logits(self, g: str, b_idx: list[int], h_new: torch.Tensor) -> torch.Tensor:
        n = len(b_idx)
        assert 0 < n <= self.BFIX
        if n < self.BFIX:
            b_idx = list(b_idx) + [b_idx[-1]] * (self.BFIX - n)
            h_new = torch.cat([h_new, h_new[-1:].expand(self.BFIX - n, -1)], 0)
        loc = torch.tensor([self.local[g][i] for i in b_idx], device="cuda")
        feed = g2.KVFeed({l: self.K[g][l].index_select(0, loc) for l in self.K[g]},
                         {l: self.V[g][l].index_select(0, loc) for l in self.V[g]})
        return g2.forward_from(self.run.model, h_new[:, None].to(torch.bfloat16), L + 1, feed, self.pos[g])[:n]

    @torch.no_grad()
    def pair_margins(self, pairs: list[tuple[int, torch.Tensor]], fn_pair: Callable[[torch.Tensor, torch.Tensor],
                                                                                     torch.Tensor]) -> np.ndarray:
        """pairs: [(base index, source state [D])]; fn_pair(hb [n, D], hs [n, D]) -> edited [n, D]; returns margins."""
        out = np.zeros(len(pairs))
        by_g: dict[str, list[int]] = {}
        for i, (b, _) in enumerate(pairs):
            by_g.setdefault(self.bases[b]["template"], []).append(i)
        for g, ii in by_g.items():
            for c0 in range(0, len(ii), self.BFIX):
                cc = ii[c0:c0 + self.BFIX]
                bi = [pairs[i][0] for i in cc]
                hs = torch.stack([pairs[i][1] for i in cc]).cuda().float()
                hn = fn_pair(self.Hb[bi], hs)
                out[cc] = g2.margin(self.logits(g, bi, hn)).cpu().numpy()
        return out

    @torch.no_grad()
    def base_margins_edit(self, fn: Callable[[torch.Tensor], torch.Tensor]) -> np.ndarray:
        """dy of a state edit f(h) (no source) for every base: m(f(h_b)) - m(h_b)."""
        out = np.zeros(len(self.bases))
        for g, ix in self.idx.items():
            for c0 in range(0, len(ix), self.BFIX):
                cix = ix[c0:c0 + self.BFIX]
                out[cix] = (g2.margin(self.logits(g, cix, fn(self.Hb[cix]))) - self.yb[cix]).cpu().numpy()
        return out


@torch.no_grad()
def kv_stacks_groups(run: Any, items: list[dict], cs: list[int], groups: list[str], min_layer: int = L + 1
                     ) -> dict[str, Any]:
    K: dict[str, dict[int, torch.Tensor]] = {}
    Vv: dict[str, dict[int, torch.Tensor]] = {}
    for g in groups:
        ix = [i for i, v in enumerate(items) if v["template"] == g]
        pk: dict[int, list[torch.Tensor]] = {l: [] for l in range(min_layer, N_LAYERS)}
        pv: dict[int, list[torch.Tensor]] = {l: [] for l in range(min_layer, N_LAYERS)}
        for i in ix:
            pre = run.prefill(items[i]["ids"] + cs[:-1], 1)
            for l in range(min_layer, N_LAYERS):
                pk[l].append(pre["kv"][l][0])
                pv[l].append(pre["kv"][l][1])
            del pre
        K[g] = {l: torch.cat(pk[l], 0) for l in pk}
        Vv[g] = {l: torch.cat(pv[l], 0) for l in pv}
        del pk, pv
        torch.cuda.empty_cache()
    return {"K": K, "V": Vv}


# ================================================================================================ statistics
def ratio_of_means_ci(num: np.ndarray, den: np.ndarray, clusters: np.ndarray, n_boot: int = N_BOOT_PAIRS,
                      seed: int = 0) -> dict[str, Any]:
    mn, md = float(np.mean(num)), float(np.mean(den))
    est = mn / md if abs(md) > 1e-12 else None
    rng = np.random.default_rng(seed)
    uc = np.unique(clusters)
    groups = [np.where(clusters == u)[0] for u in uc]
    bs = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(uc), size=len(uc))
        ii = np.concatenate([groups[p] for p in pick])
        d = den[ii].mean()
        if abs(d) > 1e-12:
            bs.append(num[ii].mean() / d)
    ci = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))] if bs else [None, None]
    return {"estimate": est, "mean_num": mn, "mean_den": md, "ci95_cluster_boot": ci, "n": int(len(num)),
            "n_clusters": int(len(uc))}


def _pp_median(num: np.ndarray, den: np.ndarray, floor: float = 0.5) -> float | None:
    ok = np.abs(den) >= floor
    return float(np.median(num[ok] / den[ok])) if ok.any() else None


def median_recovery(dy: np.ndarray, dyf: np.ndarray) -> float | None:
    ok = np.abs(dyf) >= 1.0
    return float(np.median(dy[ok] / dyf[ok])) if ok.any() else None


def pcs(X: np.ndarray, n: int) -> np.ndarray:
    Xc = X - X.mean(0, keepdims=True)
    _, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    r = int((S > S[0] * 1e-9).sum())
    return Vt[:min(n, r)].T.astype(np.float64)               # [D, n]


def qr_cols(A: torch.Tensor) -> torch.Tensor:
    return torch.linalg.qr(A.double())[0].float()


def natural_variance(Hv: torch.Tensor, R0: torch.Tensor, n_rand: int = N_HAAR_VAR) -> dict[str, Any]:
    """Iteration 7's exact computation (GPU fp32 covariance; generator seed 9 + k; Haar via QR)."""
    Hc = Hv - Hv.mean(0, keepdim=True)
    Sig = (Hc.T @ Hc) / (Hv.shape[0] - 1)
    trS = float(torch.trace(Sig))
    out = {}
    for k in RANKS:
        Rk = R0[:, :k]
        share = float(torch.trace(Rk.T @ Sig @ Rk)) / trS
        rs = []
        gq2 = torch.Generator().manual_seed(9 + k)
        for _ in range(n_rand):
            Rr = torch.linalg.qr(torch.randn(D_MODEL, k, generator=gq2).cuda())[0]
            rs.append(float(torch.trace(Rr.T @ Sig @ Rr)) / trS)
        rs = np.array(rs)
        sd_dir = torch.sqrt(torch.clamp(torch.einsum("dk,de,ek->k", Rk, Sig, Rk), min=0)).cpu().numpy()
        out[str(k)] = {"share": share, "random_p95": float(np.percentile(rs, 95)), "random_mean": float(rs.mean()),
                       "percentile_vs_random": float((rs < share).mean() * 100),
                       "share_over_random_mean": share / max(float(rs.mean()), 1e-12),
                       "per_direction_sd": sd_dir.tolist()}
    # Makelov spread check: per-direction projection SD over the SD along random unit directions
    g = torch.Generator().manual_seed(123)
    U = torch.randn(D_MODEL, 1000, generator=g).cuda()
    U = U / U.norm(dim=0, keepdim=True)
    sd_rand = torch.sqrt(torch.clamp(torch.einsum("dk,de,ek->k", U, Sig, U), min=0)).cpu().numpy()
    for k in RANKS:
        out[str(k)]["per_direction_sd_over_random_sd_mean"] = (np.array(out[str(k)]["per_direction_sd"])
                                                               / float(sd_rand.mean())).tolist()
    out["random_direction_sd_mean"] = float(sd_rand.mean())
    out["total_variance"] = trS
    return out


# ================================================================================================ stage
def recompute_states(run: Any, cs: list[int]) -> dict[str, list[dict]]:
    """Block-L p_f state and fork logits of the 120 variants, 40 forced sources and 5 twins on THIS engine."""
    out: dict[str, list[dict]] = {}
    for name, plist in (("variants", FK.variants()), ("sources", FK.forced_sources()),
                        ("twins", [dict(FK.twin(w), template=w, vid=f"twin|{w}") for w in TEMPLATE_IDS])):
        recs = []
        for p in plist:
            ids = p["ids"] + cs
            st = run.states(ids, [L], positions=[len(ids) - 1], want_logits_at=[len(ids) - 1])
            lg = st["logits"][0].float()
            recs.append({k: p.get(k) for k in ("vid", "sid", "template", "noun", "mode", "pair", "display", "P",
                                               "spec_start", "prompt_sha256")}
                        | {"ids": p["ids"], "y": float(g2.margin(lg)), "q": g2.class_probs(lg).tolist(),
                           "h": {L: st["h"][L][0].float()}})
        out[name] = recs
    return out


def stage_tf(run: Any, cs: list[int], log_every: Callable[[str], None] = logger.info) -> dict[str, Any]:
    t0 = time.time()
    cal = token_calibration()
    maps = load_maps()
    R, u, Rr = maps["R"], maps["u"], maps["Rr"]
    V7, S7, drop = g2._load_states()            # iteration-7 cached states (for the exact-reproduction checks)
    st = recompute_states(run, cs)
    V, S, TW = st["variants"], st["sources"], st["twins"]
    hdiff = max(float((v["h"][L].cpu() - v7["h"][L].float()).abs().max()) for v, v7 in zip(V, V7))
    hrel = max(float((v["h"][L].cpu() - v7["h"][L].float()).norm() / v7["h"][L].float().norm()) for v, v7 in zip(V, V7))
    ydiff = max(abs(v["y"] - v7["y"]) for v, v7 in zip(V, V7))
    res: dict[str, Any] = {"state_recompute_vs_iter7": {"max_abs_diff_h": hdiff, "max_rel_diff_h": hrel,
                                                        "max_abs_diff_y": ydiff,
                                                        "n_dropped_sources_iter7": len(drop)},
                           "calibration": {str(k): v for k, v in cal.items()}}
    log_every(f"tf: states recomputed (max |dh| {hdiff:.3g}, rel {hrel:.3g}, max |dy| {ydiff:.3g})")
    hk = lambda s: s["h"][L]                    # noqa: E731
    C = {sd: {k: class_targets(S, drop, R[sd][:, :k], hk) for k in RANKS} for sd in SEEDS}
    c7 = read_json(I7 / "predictions" / "commit3.json")["target_coordinates"]
    res["targets_vs_commit3_max_abs"] = {Y: float(np.max(np.abs(np.array(c7[Y]) - C[0][4][Y].cpu().numpy())))
                                         for Y in ("bfs", "dfs")}
    for k in (1, 2, 4):                          # seed 0, k <= 4: iteration 7's committed coordinates (commit3)
        for Y in ("bfs", "dfs"):
            C[0][k][Y] = torch.tensor(c7[Y][:k], device="cuda", dtype=torch.float32)
    res["targets"] = {f"seed{sd}_k{k}": {Y: C[sd][k][Y].tolist() for Y in ("bfs", "dfs")} for sd in SEEDS for k in RANKS}
    res["targets_note"] = "seed 0, k in {1, 2, 4}: commit3 coordinates (first k); other seeds/ranks: this engine"

    c_rand = class_targets(S, drop, Rr, hk)["bfs"]
    # ---------------------------------------------------------------- 3c DiM betas (grid scan + bisection)
    Vtr_idx = [i for i, v in enumerate(V) if v["template"] in TRAIN_W]
    Vtr = [V[i] for i in Vtr_idx]
    kv_tr = kv_stacks_groups(run, Vtr, cs, list(TRAIN_W))
    ctx_tr = Ctx(run, Vtr, list(TRAIN_W), torch.stack([v["h"][L] for v in Vtr]), kv_tr)

    def mean_dy(fn) -> float:
        return float(np.mean(ctx_tr.base_margins_edit(fn)))
    betas: dict[str, Any] = {}
    for Y, sign in (("bfs", 1.0), ("dfs", -1.0)):
        target = mean_dy(das_fn(R[0][:, :KSTAR], C[0][KSTAR][Y], 1.0))
        grid = [sign * b for b in np.arange(0, 3001, 100)]
        vals = [mean_dy(dim_fn(u, b)) for b in grid]
        mono = bool(all((vals[i + 1] - vals[i]) * sign >= -1e-3 for i in range(len(vals) - 1)))
        # first bracket on the grid where the curve crosses the target
        lo = hi = None
        for i in range(len(grid) - 1):
            a, b = vals[i] - target, vals[i + 1] - target
            if a == 0 or (a < 0) != (b < 0):
                lo, hi = grid[i], grid[i + 1]
                break
        if lo is None:
            j = int(np.argmin([abs(v - target) for v in vals]))
            beta, dmd, matched = grid[j], vals[j], abs(vals[j] - target) < 0.05 * max(abs(target), 0.1)
        else:
            flo = mean_dy(dim_fn(u, lo)) - target
            for _ in range(40):
                mid = (lo + hi) / 2
                fm = mean_dy(dim_fn(u, mid)) - target
                if (fm < 0) == (flo < 0):
                    lo, flo = mid, fm
                else:
                    hi = mid
            beta = (lo + hi) / 2
            dmd = mean_dy(dim_fn(u, beta))
            matched = abs(dmd - target) < 0.05 * max(abs(target), 0.1)
        b7 = read_json(I7 / "predictions" / "commit3.json")["dim_betas_matched_tf_effect"].get(f"{Y}|1.0", {})
        betas[Y] = {"das_r4_lam1_mean_dy_train72": target, "beta": float(beta), "dim_mean_dy": dmd,
                    "matched": bool(matched), "grid": [float(g) for g in grid], "grid_mean_dy": vals,
                    "monotone_on_grid": mono, "iter7_beta": b7.get("beta"), "iter7_das_mean_dy": b7.get("das_mean_dy")}
        log_every(f"tf: DiM {Y}: target {target:.3f}, beta {beta:.1f}, dy {dmd:.3f}, matched {matched}, "
                  f"monotone {mono}")
    res["dim_betas"] = betas
    # ---------------------------------------------------------------- 3a fork distributions at p_f
    cond: dict[str, dict[str, Any]] = {}
    rows0 = torch.tensor([0], device="cuda")

    def tf_at(ids: list[int], f: Callable | None, name: str) -> dict[str, float]:
        pf = len(ids) - 1
        e = prefill_edit(f, pf, name) if f is not None else None
        lg = run.logits_rows(ids, 1, [(e, rows0)] if e else [])[0, 0]
        return fork_stats(lg, cal)
    for w in TEMPLATE_IDS:
        ids = FK.twin(w)["ids"] + cs
        cond.setdefault("twin", {})[w] = tf_at(ids, None, "twin")
        for sd in SEEDS:
            for k in RANKS:
                for lam in (0.5, 1.0):
                    for Y in ("bfs", "dfs"):
                        nm = f"DAS|s{sd}|r{k}|{Y}|{lam}"
                        cond.setdefault(nm, {})[w] = tf_at(ids, das_fn(R[sd][:, :k], C[sd][k][Y], lam), nm)
        for Y in ("bfs", "dfs"):
            cond.setdefault(f"DiM|{Y}|matched", {})[w] = tf_at(ids, dim_fn(u, betas[Y]["beta"]), f"DiM|{Y}")
        cond.setdefault("RAND|r4|1.0", {})[w] = tf_at(ids, das_fn(Rr, c_rand, 1.0), "RAND")
    for f in ("F1", "F2", "F3", "F4", "F5"):
        for mode in ("bfs", "dfs"):
            ids = FK.forced(mode, f, 3)["ids"] + cs
            cond.setdefault(f"forced|{mode}|{f}|3", {})["-"] = tf_at(ids, None, f"forced|{mode}|{f}")
    res["tf_conditions"] = cond
    # cell-level predictions (mean over the slots' prompts: 10 slots per template -> template mean)
    def mean_over(nm: str) -> dict[str, float]:
        d = cond[nm]
        return {k: float(np.mean([d[w][k] for w in d])) for k in ("m", "p_B", "p_D", "p_queue", "pred_attempted_bfs",
                                                                  "pred_correct_bfs", "pred_attempted_dfs",
                                                                  "pred_correct_dfs")}
    cellpred = {"P-twin": mean_over("twin"), "P-DAS-bfs": mean_over("DAS|s0|r4|bfs|1.0"),
                "P-DAS-dfs": mean_over("DAS|s0|r4|dfs|1.0"), "G1a": mean_over("forced|bfs|F5|3"),
                "G1b": mean_over("forced|dfs|F5|3")}
    cand = {f: cond[f"forced|bfs|{f}|3"]["-"]["pred_correct_bfs"] for f in ("F1", "F2", "F3", "F4")}
    g1d = max(cand, key=lambda f: cand[f])
    cellpred["G1d"] = mean_over(f"forced|bfs|{g1d}|3")
    res["cell_predictions"] = cellpred
    res["G1d_template"] = {"chosen": g1d, "rule": "argmax over F1-F4 (F5 is G1a) of the 3a-predicted correct BFS "
                                                  "with c* prefilled", "candidates": cand}
    # ---------------------------------------------------------------- 3b log P(c* | prompt)
    from engine import tf_logprobs

    lpc = {}
    for nm, p in [("twin|" + w, FK.twin(w)) for w in TEMPLATE_IDS] + \
                 [(f"forced|{m}|{f}|3", FK.forced(m, f, 3)) for f in ("F1", "F2", "F3", "F4", "F5") for m in ("bfs", "dfs")]:
        ids = p["ids"] + cs
        lp = tf_logprobs(run.model, ids, list(range(len(p["ids"]), len(ids))))
        lpc[nm] = {"logp_cstar": float(np.sum(lp)), "p_cstar": float(np.exp(np.sum(lp)))}
    res["logp_cstar"] = lpc
    log_every(f"tf: 3a/3b done ({time.time() - t0:.0f}s); P-twin pred attempted {cellpred['P-twin']['pred_attempted_bfs']:.3f}"
              f", G1a pred correct {cellpred['G1a']['pred_correct_bfs']:.3f}")
    ctx_tr = None
    del kv_tr
    gc.collect()
    torch.cuda.empty_cache()
    # ---------------------------------------------------------------- 3d dormancy
    res["dormancy"] = dormancy(run, cs, V, S, TW, V7, drop, R, C, cal)
    res["seconds"] = time.time() - t0
    _ = (HELD_F, MIN_DENOM_NAT)
    return res


def dormancy(run: Any, cs: list[int], V: list[dict], S: list[dict], TW: list[dict], V7: list[dict], drop: set[int],
             R: dict[int, torch.Tensor], C: dict, cal: dict) -> dict[str, Any]:
    t0 = time.time()
    out: dict[str, Any] = {"by_k": {str(k): {} for k in RANKS}}
    kv = kv_stacks_groups(run, V, cs, list(TEMPLATE_IDS))
    Hv = torch.stack([v["h"][L] for v in V]).cuda().float()
    ctx = Ctx(run, V, list(TEMPLATE_IDS), Hv, kv)
    Hs = torch.stack([s["h"][L] for s in S]).cuda().float()
    src_cls = np.array([0 if s["mode"] == "bfs" else 1 for s in S])
    held = g2.make_pairs(V, S, HELD_W, HELD_F, drop)
    bi = np.array([a for a, _ in held])
    si = np.array([b for _, b in held])
    sgn = np.where(src_cls[si] == 0, 1.0, -1.0)
    pairs_fwd = [(a, Hs[b]) for a, b in held]
    yb = ctx.yb.cpu().numpy()[bi]
    dy_full = ctx.pair_margins(pairs_fwd, lambda hb, hs: hs.clone()) - yb

    def fwd_dy(Rk: torch.Tensor) -> np.ndarray:
        return ctx.pair_margins(pairs_fwd, lambda hb, hs, Rk=Rk: hb + ((hs - hb) @ Rk) @ Rk.T) - yb
    # (forward) recovery per seed and k, on this engine
    fwd = {}
    dyk = {}
    for sd in SEEDS:
        for k in RANKS:
            dy = fwd_dy(R[sd][:, :k])
            dyk[(sd, k)] = dy
            fwd[f"seed{sd}_k{k}"] = {"median_recovery": median_recovery(dy, dy_full),
                                     "ratio_of_means_dir": float(np.mean(sgn * dy) / np.mean(sgn * dy_full)),
                                     "dy_dir_mean": float(np.mean(sgn * dy)),
                                     "iia": float(np.mean(np.where(src_cls[si] == 0, dy + yb > 0, dy + yb < 0)))}
    out["forward"] = {"pairs": len(held), "dy_full_dir_mean": float(np.mean(sgn * dy_full)), "by": fwd,
                      "iter7_expected_seed_median": {"1": 1.98, "2": 2.36, "4": 2.58, "8": 2.81}}
    log_every = logger.info
    log_every(f"dorm: forward recovery seed0 " + ", ".join(f"k{k} {fwd[f'seed0_k{k}']['median_recovery']:.3f}" for k in RANKS))
    # ---------------------------------------------------------------- (ii) projected-map retention (+ residual)
    Xv = Hv.cpu().numpy().astype(np.float64)
    X160 = np.concatenate([Xv, Hs.cpu().numpy().astype(np.float64)], 0)
    bases_pc = {"pc64_v120": pcs(Xv, PC_MAIN), "pc32_v120": pcs(Xv, PC_SENS[0]), "pc100_v120": pcs(Xv, PC_SENS[1]),
                "pc64_v160": pcs(X160, PC_MAIN)}
    # dial retention: class-mean edit (lam 1, Y = bfs) with R_proj vs R_k, over the 72 train bases (KV path) + 5 twins
    tr_idx = [i for i, v in enumerate(V) if v["template"] in TRAIN_W]

    def dial_dy(Rk: torch.Tensor) -> dict[str, float]:
        cY = class_targets(S, drop, Rk, lambda s: s["h"][L])["bfs"]
        f = das_fn(Rk, cY, 1.0)
        d72 = ctx.base_margins_edit(f)[tr_idx]
        dtw = []
        for t in TW:
            ids = t["ids"] + cs
            pf = len(ids) - 1
            e = prefill_edit(f, pf, "dial")
            lg_e = run.logits_rows(ids, 1, [(e, torch.tensor([0], device="cuda"))])[0, 0]
            lg_0 = run.logits_rows(ids, 1, [])[0, 0]
            dtw.append(float(g2.margin(lg_e) - g2.margin(lg_0)))
        allv = np.concatenate([d72, np.array(dtw)])
        return {"mean_dy_72": float(d72.mean()), "mean_dy_twins": float(np.mean(dtw)), "mean_dy_77": float(allv.mean())}
    proj_tab: dict[str, Any] = {}
    clusters = bi
    for k in RANKS:
        Rk = R[0][:, :k]
        base_dial = dial_dy(Rk)
        kk: dict[str, Any] = {"dial_Rk": base_dial}
        for nm, P in bases_pc.items():
            Pt = torch.tensor(P, device="cuda", dtype=torch.float64)
            Rk64 = Rk.double()
            Rproj = qr_cols(Pt @ (Pt.T @ Rk64))
            Rperp = qr_cols(Rk64 - Pt @ (Pt.T @ Rk64))
            frac_in = float((Pt.T @ Rk64).pow(2).sum() / k)
            dy_p = fwd_dy(Rproj)
            dy_r = fwd_dy(Rperp)
            ret = ratio_of_means_ci(sgn * dy_p, sgn * dyk[(0, k)], clusters)
            res_ = ratio_of_means_ci(sgn * dy_r, sgn * dyk[(0, k)], clusters)
            dp = dial_dy(Rproj)
            dr = dial_dy(Rperp)
            kk[nm] = {"n_pcs": int(P.shape[1]), "frac_Rk_in_span (plan pca_upper)": frac_in,
                      "retention_interchange": ret, "residual_interchange": res_,
                      "retention_dial_77": dp["mean_dy_77"] / base_dial["mean_dy_77"] if abs(base_dial["mean_dy_77"]) > 1e-9 else None,
                      "residual_dial_77": dr["mean_dy_77"] / base_dial["mean_dy_77"] if abs(base_dial["mean_dy_77"]) > 1e-9 else None,
                      "dial_proj": dp, "dial_perp": dr}
        # E33's pca_upper (top-k PC variance share of the natural set)
        Xc = Xv - Xv.mean(0)
        sv = np.linalg.svd(Xc, compute_uv=False)
        kk["pca_topk_variance_share (E33 pca_upper)"] = float((sv[:k] ** 2).sum() / (sv ** 2).sum())
        proj_tab[str(k)] = kk
        log_every(f"dorm k{k}: retention64 {kk['pc64_v120']['retention_interchange']['estimate']:.3f}, residual64 "
                  f"{kk['pc64_v120']['residual_interchange']['estimate']:.3f}, frac_in {kk['pc64_v120']['frac_Rk_in_span (plan pca_upper)']:.3f}")
    out["projection"] = proj_tab
    # planted checks: a direction inside the span gives frac 1 and retention 1; an orthogonal one gives frac 0
    P = torch.tensor(bases_pc["pc64_v120"], device="cuda", dtype=torch.float64)
    g = torch.Generator().manual_seed(7)
    inside = qr_cols(P @ torch.randn(P.shape[1], 1, generator=g).double().cuda())
    rnd = torch.randn(D_MODEL, 1, generator=g).double().cuda()
    orth = qr_cols(rnd - P @ (P.T @ rnd))
    Pin = qr_cols(P @ (P.T @ inside.double()))
    dy_in = fwd_dy(inside)
    dy_in_p = fwd_dy(Pin)
    out["planted"] = {"inside_frac": float((P.T @ inside.double()).pow(2).sum()),
                      "orthogonal_frac": float((P.T @ orth.double()).pow(2).sum()),
                      "inside_retention": float(np.mean(sgn * dy_in_p) / np.mean(sgn * dy_in)) if abs(np.mean(sgn * dy_in)) > 1e-9 else None}
    # ---------------------------------------------------------------- (iii) natural variance
    nv = {"this_engine_v120": natural_variance(Hv, R[0]),
          "iter7_cached_v120": natural_variance(torch.stack([v["h"][L] for v in V7]).cuda().float(), R[0]),
          "this_engine_v160": natural_variance(torch.tensor(X160, dtype=torch.float32, device="cuda"), R[0])}
    i7 = read_json(I7 / "results" / "g2_decisions.json")["natural_variance"]
    nv["iter7_reproduction_max_abs_diff"] = max(abs(nv["iter7_cached_v120"][str(k)]["share"] - i7[str(k)]["share"])
                                                for k in RANKS)
    nv["iter7_reproduction_p95_max_abs_diff"] = max(abs(nv["iter7_cached_v120"][str(k)]["random_p95"] - i7[str(k)]["random_p95"])
                                                    for k in RANKS)
    out["natural_variance"] = nv
    log_every(f"dorm: natural variance shares (this engine) " + ", ".join(
        f"k{k} {nv['this_engine_v120'][str(k)]['share']:.5f} (p95 {nv['this_engine_v120'][str(k)]['random_p95']:.5f})" for k in RANKS)
        + f"; iter7 repro max diff {nv['iter7_reproduction_max_abs_diff']:.2e}")
    # ---------------------------------------------------------------- (iv) principal angles
    ang = {}
    for k in RANKS:
        ang[str(k)] = {f"{a}-{b}": torch.linalg.svdvals(R[a][:, :k].T @ R[b][:, :k]).tolist()
                       for a in SEEDS for b in SEEDS if a < b}
    out["principal_cosines"] = ang
    del ctx, kv
    gc.collect()
    torch.cuda.empty_cache()
    # ---------------------------------------------------------------- (i) reverse interchange
    out["reverse"] = reverse_tf(run, cs, V, S, R)
    out["seconds"] = time.time() - t0
    _ = cal
    return out


def reverse_tf(run: Any, cs: list[int], V: list[dict], S: list[dict], R: dict[int, torch.Tensor]) -> dict[str, Any]:
    """Bases = forced-BFS prompts (all 4 display pairs) + c*; sources = the 24 twin variants of the aligned template."""
    bases = [s for s in S if s["mode"] == "bfs"]
    groups = sorted({b["template"] for b in bases})
    kv = kv_stacks_groups(run, bases, cs, groups)
    Hb = torch.stack([b["h"][L] for b in bases]).cuda().float()
    ctx = Ctx(run, bases, groups, Hb, kv)
    al = {"F1": "W1", "F2": "W2", "F3": "W3", "F4": "W4", "F5": "W5"}
    for b in bases:                               # positions align (padding to the twin's spec_start)
        assert b["P"] == next(v["P"] for v in V if v["template"] == al[b["template"]]), b["sid"]
    pairs, clus, split, src_y = [], [], [], []
    for i, b in enumerate(bases):
        for v in V:
            if v["template"] == al[b["template"]]:
                pairs.append((i, v["h"][L]))
                clus.append(i)
                split.append("held" if b["template"] in HELD_F else "train")
                src_y.append(v["y"])
    clus, split, src_y = np.array(clus), np.array(split), np.array(src_y)
    yb = ctx.yb.cpu().numpy()[clus]
    dm_full = ctx.pair_margins(pairs, lambda hb, hs: hs.clone()) - yb
    base_full_y = np.array([bases[i]["y"] for i in clus])
    dm_lateband = src_y - base_full_y            # blocks 17-33 at p_f replaced -> the source's own margin
    out: dict[str, Any] = {"n_pairs": {"held": int((split == "held").sum()), "train": int((split == "train").sum())},
                           "dm_full_mean": {sp: float(dm_full[split == sp].mean()) for sp in ("held", "train")},
                           "dm_lateband_mean": {sp: float(dm_lateband[split == sp].mean()) for sp in ("held", "train")},
                           "base_margin_mean": {sp: float(yb[split == sp].mean()) for sp in ("held", "train")},
                           "by_k": {}}
    gq = torch.Generator().manual_seed(4243)
    rand_R = [torch.linalg.qr(torch.randn(D_MODEL, max(RANKS), generator=gq).cuda())[0] for _ in range(N_HAAR_REV)]
    for k in RANKS:
        kk: dict[str, Any] = {}
        dms = {}
        for sd in SEEDS:
            Rk = R[sd][:, :k]
            dm = ctx.pair_margins(pairs, lambda hb, hs, Rk=Rk: hb + ((hs - hb) @ Rk) @ Rk.T) - yb
            dms[sd] = dm
        rnull = []
        for Rq in rand_R:
            Rk = Rq[:, :k]
            dm = ctx.pair_margins(pairs, lambda hb, hs, Rk=Rk: hb + ((hs - hb) @ Rk) @ Rk.T) - yb
            rnull.append({sp: float(dm[split == sp].mean()) for sp in ("held", "train")})
        for sp in ("held", "train"):
            m = split == sp
            den = float(dm_full[m].mean())
            defined = abs(den) >= MIN_DENOM_NAT
            rec = ratio_of_means_ci(dms[0][m], dm_full[m], clus[m])
            rn = np.array([r[sp] for r in rnull])
            kk[sp] = {"dm_das_mean_by_seed": {str(sd): float(dms[sd][m].mean()) for sd in SEEDS},
                      "dm_full_mean": den, "defined": bool(defined),
                      "reverse_recovery": rec["estimate"] if defined else None, "reverse_recovery_ci95": rec["ci95_cluster_boot"] if defined else None,
                      "reverse_recovery_by_seed": {str(sd): (float(dms[sd][m].mean()) / den if defined else None) for sd in SEEDS},
                      "per_pair_ratio_median_absfull_ge_0.5": _pp_median(dms[0][m], dm_full[m]),
                      "haar_null_mean": float(rn.mean()), "haar_null_p05": float(np.percentile(rn, 5)),
                      "haar_null_p95": float(np.percentile(rn, 95)),
                      "das_percentile_vs_haar_toward_dfs": float((rn > dms[0][m].mean()).mean() * 100),
                      "lateband_ratio": float(dms[0][m].mean() / dm_lateband[m].mean()) if abs(dm_lateband[m].mean()) > 1e-9 else None}
        out["by_k"][str(k)] = kk
        logger.info(f"rev k{k}: held dm_das {kk['held']['dm_das_mean_by_seed']['0']:.3f} vs full {kk['held']['dm_full_mean']:.3f} "
                    f"(rec {kk['held']['reverse_recovery']}); haar mean {kk['held']['haar_null_mean']:.3f}")
    # identity check: source = base gives dm = 0
    ident = ctx.pair_margins([(0, Hb[0])], lambda hb, hs: hb + ((hs - hb) @ R[0][:, :4]) @ R[0][:, :4].T) - ctx.yb.cpu().numpy()[[0]]
    out["identity_source_eq_base_dm"] = float(ident[0])
    del ctx, kv
    gc.collect()
    torch.cuda.empty_cache()
    return out


def summarize_dormancy(d: dict[str, Any]) -> dict[str, Any]:
    """Per-k summary used by the committed verdict (seed 0, held-out reverse bases, 64 PCs of the 120 variants)."""
    from analysis8 import dormancy_verdict

    out = {}
    for k in RANKS:
        ks = str(k)
        fwd = d["forward"]["by"][f"seed0_k{k}"]["median_recovery"]
        rv = d["reverse"]["by_k"][ks]["held"]
        pr = d["projection"][ks]["pc64_v120"]
        nv = d["natural_variance"]["this_engine_v120"][ks]
        ret = pr["retention_interchange"]["estimate"]
        v = dormancy_verdict(fwd, rv["reverse_recovery"], rv["defined"], ret, nv["share"], nv["random_p95"])
        out[ks] = {"forward_recovery": fwd, "reverse_recovery": rv["reverse_recovery"], "reverse_defined": rv["defined"],
                   "reverse_ci95": rv["reverse_recovery_ci95"], "retention": ret,
                   "retention_ci95": pr["retention_interchange"]["ci95_cluster_boot"],
                   "retention_dial": pr["retention_dial_77"], "residual_interchange": pr["residual_interchange"]["estimate"],
                   "frac_Rk_in_pc64": pr["frac_Rk_in_span (plan pca_upper)"],
                   "pca_topk_variance_share": d["projection"][ks]["pca_topk_variance_share (E33 pca_upper)"],
                   "share": nv["share"], "random_p95": nv["random_p95"], "percentile": nv["percentile_vs_random"],
                   "principal_cosines": d["principal_cosines"][ks], **v}
    return out


def write_tf_results(res: dict[str, Any]) -> None:
    dorm = res.pop("dormancy")
    dorm["summary_by_k"] = summarize_dormancy(dorm)
    write_json(RESULTS_DIR / "dormancy.json", dorm)
    write_json(RESULTS_DIR / "tf_stage.json", res)
