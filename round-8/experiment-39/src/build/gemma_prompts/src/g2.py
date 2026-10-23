#!/usr/bin/env python3
"""G2: controlled DAS at the fork position p_f (one layer, one position, linear orthonormal rank-k map, nested
k in {1, 2, 4, 8}).

Machinery. For every base prompt (prompt + c*) the KV cache of positions < p_f is computed once; an interchange at
block L only changes the computation at p_f from block L+1 on, so forward_from() runs blocks L+1..33 for the single
position p_f against the cached keys/values (U3 checks it against a full recompute). Bases = the 120 neutral twin
variants (train W1-W3, held-out W4-W5); sources = 40 forced prompts F1-F5 x {BFS, DFS} x 4 equal-length display
names (train F1-F3, held-out F4-F5). Targets = the source's own class distribution q_s over {B, D, O} at p_f.
Controls: Haar-random subspaces (RAND), shuffled source labels (SHUF), a randomly initialised Gemma (RINIT, stage
g2r), difference in means (DiM) and the twin's natural-variance share (Makelov)."""

from __future__ import annotations

import gc
import json
import math
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg import (B_IDS, D_IDS, D_MODEL, DAS_BATCH, DAS_LAYER_FIXED, DAS_LAYERS_SCAN, DAS_LR, DAS_RANKS, DAS_SEEDS,
                 DAS_STEPS, DATA_DIR, DOSES, HELD_F, HELD_W, I6_DATA, N_LAYERS, RESULTS_DIR, STATES_DIR,
                 SUBSPACE_DIR, TEMPLATE_IDS, TRAIN_F, TRAIN_W, add_deviation, read_json, read_jsonl, sha256_file,
                 slot_key7, write_json)

LAYERS_STORE = list(range(N_LAYERS))


# ================================================================================================ machinery
class KVFeed:
    """Duck-typed cache for blocks L+1..33 at one new position: cat(cached K/V, new k/v) per layer (autograd-safe)."""

    def __init__(self, K: dict[int, torch.Tensor], V: dict[int, torch.Tensor]):
        self.K, self.V = K, V

    def update(self, k: torch.Tensor, v: torch.Tensor, layer_idx: int, cache_kwargs: Any = None):
        return torch.cat([self.K[layer_idx], k], 2), torch.cat([self.V[layer_idx], v], 2)


def forward_from(model: Any, h_in: torch.Tensor, L_start: int, feed: KVFeed, pos_id: int) -> torch.Tensor:
    """h_in [n, 1, D] = the (edited) output of block L_start-1 at position pos_id; returns fp32 logits [n, V]."""
    import engine as EG

    mm = model.model
    n = h_in.shape[0]
    pos = torch.full((n, 1), pos_id, device=h_in.device, dtype=torch.long)
    pe_g = mm.rotary_emb(h_in, pos)
    pe_l = mm.rotary_emb_local(h_in, pos)
    cpos = torch.tensor([pos_id], device=h_in.device)
    h = h_in
    for l in range(L_start, N_LAYERS):
        h = mm.layers[l](h, position_embeddings_global=pe_g, position_embeddings_local=pe_l, attention_mask=None,
                         position_ids=pos, past_key_values=feed, use_cache=True, cache_position=cpos)[0]
    h = mm.norm(h)
    return EG.lm_logits(model, h[:, -1])


KV_MIN_LAYER = 18          # the scan's lowest layer is 17 -> blocks 18..33 need cached keys/values


@torch.no_grad()
def kv_stacks(run: Any, V: list[dict], cs: list[int], min_layer: int = KV_MIN_LAYER) -> dict[str, Any]:
    """Per template: K/V of positions < p_f for blocks >= min_layer, stacked over that template's bases
    (order = order of appearance in V). One copy only (about 2.2 GB for 120 bases)."""
    K: dict[str, dict[int, torch.Tensor]] = {}
    Vv: dict[str, dict[int, torch.Tensor]] = {}
    for w in TEMPLATE_IDS:
        ix = [i for i, v in enumerate(V) if v["template"] == w]
        if not ix:
            continue
        parts_k: dict[int, list[torch.Tensor]] = {l: [] for l in range(min_layer, N_LAYERS)}
        parts_v: dict[int, list[torch.Tensor]] = {l: [] for l in range(min_layer, N_LAYERS)}
        for i in ix:
            pre = run.prefill(V[i]["ids"] + cs[:-1], 1)
            for l in range(min_layer, N_LAYERS):
                parts_k[l].append(pre["kv"][l][0])
                parts_v[l].append(pre["kv"][l][1])
            del pre
        K[w] = {l: torch.cat(parts_k[l], 0) for l in parts_k}
        Vv[w] = {l: torch.cat(parts_v[l], 0) for l in parts_v}
        del parts_k, parts_v
        torch.cuda.empty_cache()
    return {"K": K, "V": Vv, "min_layer": min_layer}


@torch.no_grad()
def prefix_kv(run: Any, ids: list[int]) -> dict[str, Any]:
    """Batch-1 prefill of ids[:-1]: per-layer K/V [1, Hkv, n-1, Dh] (bf16, GPU)."""
    pre = run.prefill(ids[:-1], 1)
    return {"K": [k for k, _ in pre["kv"]], "V": [v for _, v in pre["kv"]]}


def class_probs(logits: torch.Tensor) -> torch.Tensor:
    p = torch.softmax(logits.float(), -1)
    pb = p[..., list(B_IDS)].sum(-1)
    pd = p[..., list(D_IDS)].sum(-1)
    return torch.stack([pb, pd, (1 - pb - pd).clamp(min=1e-9)], -1)


def margin(logits: torch.Tensor) -> torch.Tensor:
    z = logits.float()
    return torch.logsumexp(z[..., list(B_IDS)], -1) - z[..., D_IDS[0]]


# ================================================================================================ unit tests
@torch.no_grad()
def u3_test(run: Any, prompts: list[dict[str, Any]]) -> dict[str, Any]:
    """Single-position KV interchange vs full recompute: rank-4 random-subspace swap of a forced-BFS state at L22."""
    import fork7 as FK
    from gen7 import Edit

    cs = FK.cstar()
    src = FK.forced("bfs", "F1", 3)
    sids = src["ids"] + cs
    L = 22
    hs = run.states(sids, [L], positions=[len(sids) - 1])["h"][L][0].cuda()
    R = torch.linalg.qr(torch.randn(D_MODEL, 4, generator=torch.Generator().manual_seed(1)).cuda())[0]
    rows = []
    for p in prompts:
        ids = p["ids"] + cs
        pf = len(ids) - 1
        e = Edit("resid", L, [pf], lambda x, r: x + ((hs[None, None] - x) @ R) @ R.T, name="u3")
        m_full = float(margin(run.logits_rows(ids, 1, [(e, torch.tensor([0], device="cuda"))])[0, 0]))
        kv = prefix_kv(run, ids)
        hb = run.states(ids, [L], positions=[pf])["h"][L][0].cuda()
        hn = (hb + ((hs - hb) @ R) @ R.T)[None, None].to(torch.bfloat16)
        feed = KVFeed({l: kv["K"][l] for l in range(L + 1, N_LAYERS)}, {l: kv["V"][l] for l in range(L + 1, N_LAYERS)})
        m_kv = float(margin(forward_from(run.model, hn, L + 1, feed, pf)[0]))
        m_clean_full = float(margin(run.logits_rows(ids, 1)[0, 0]))
        hb_bf = hb[None, None].to(torch.bfloat16)
        m_clean_kv = float(margin(forward_from(run.model, hb_bf, L + 1, feed, pf)[0]))
        rows.append({"P": len(ids), "m_full": m_full, "m_kv": m_kv, "abs_diff": abs(m_full - m_kv),
                     "clean_abs_diff": abs(m_clean_full - m_clean_kv), "edit_dm": m_full - m_clean_full})
        del kv, feed
    mx = max(r["abs_diff"] for r in rows)
    return {"rows": rows, "max_abs_diff": mx, "pass_1e-3": mx < 1e-3, "pass_bf16_tol_0.05": mx < 0.05}


def toy_test(seed: int = 0) -> dict[str, Any]:
    """Synthetic check of the DAS loop: a 2560-d Gaussian with a planted rank-2 causal subspace Q driving a 3-class
    readout. DAS (rank 2) must recover Q (principal-angle cosines > 0.9); RAND must not; SHUF must fail held-out.
    Also reported: the plan's optimiser setting (Adam lr 2e-3, 400 steps, batch 64) and a small-n run (256 pairs <
    5,120 parameters), which overfits (train KL -> 0, held-out KL high) -- the reason held-out pairs are decisive."""
    D = D_MODEL
    g = torch.Generator().manual_seed(seed)
    Q = torch.linalg.qr(torch.randn(D, 2, generator=g))[0]
    Wout = torch.randn(3, 2, generator=g) * 3.0

    def readout(x: torch.Tensor) -> torch.Tensor:
        return torch.log_softmax((x @ Q) @ Wout.T, -1)

    def run(ntr: int, lr: float, steps: int, bs: int, perm: bool = False) -> dict[str, Any]:
        gg = torch.Generator().manual_seed(seed + ntr)
        X = torch.randn(ntr + 1024, D, generator=gg)
        Xs = torch.randn(ntr + 1024, D, generator=gg)
        tgt = readout(Xs).exp()
        ttr = tgt[torch.randperm(ntr, generator=gg)] if perm else tgt[:ntr]
        W = torch.randn(D, 2, generator=torch.Generator().manual_seed(seed + 7)).requires_grad_(True)
        opt = torch.optim.Adam([W], lr=lr)
        loss = torch.tensor(0.0)
        for st in range(steps):
            ix = torch.randint(0, ntr, (min(bs, ntr),), generator=torch.Generator().manual_seed(st))
            R = torch.linalg.qr(W)[0]
            xn = X[ix] + ((Xs[ix] - X[ix]) @ R) @ R.T
            loss = (ttr[ix] * (ttr[ix].clamp(min=1e-9).log() - readout(xn))).sum(-1).mean()
            opt.zero_grad()
            loss.backward()
            opt.step()
        R = torch.linalg.qr(W.detach())[0]
        te = slice(ntr, ntr + 1024)
        xn = X[te] + ((Xs[te] - X[te]) @ R) @ R.T
        kl = float((tgt[te] * (tgt[te].clamp(min=1e-9).log() - readout(xn))).sum(-1).mean())
        kl0 = float((tgt[te] * (tgt[te].clamp(min=1e-9).log() - readout(X[te]))).sum(-1).mean())
        return {"n_train": ntr, "lr": lr, "steps": steps, "batch": bs, "shuffled": perm,
                "principal_cosines": torch.linalg.svdvals(Q.T @ R).tolist(), "train_kl": float(loss.detach()),
                "heldout_kl": kl, "heldout_kl_no_edit": kl0}

    das = run(4096, 2e-2, 800, 512)
    shuf = run(4096, 2e-2, 800, 512, perm=True)
    plan_opt = run(4096, 2e-3, 400, 64)
    small = run(256, 2e-2, 300, 256)
    R_rand = torch.linalg.qr(torch.randn(D, 2, generator=torch.Generator().manual_seed(seed + 11)))[0]
    res = {"das": das, "shuf": shuf, "plan_optimiser_lr2e-3": plan_opt, "small_n_overfit": small,
           "rand_principal_cosines": torch.linalg.svdvals(Q.T @ R_rand).tolist()}
    res["pass"] = bool(min(das["principal_cosines"]) > 0.9 and das["heldout_kl"] < 0.2 * das["heldout_kl_no_edit"]
                       and max(res["rand_principal_cosines"]) < 0.2
                       and shuf["heldout_kl"] > 2 * das["heldout_kl"])
    return res


# ================================================================================================ stage yv
def stage_yv(args: Any) -> None:
    """y_v and fork states (all blocks, p_f) for the 120 variants, the 40 forced sources and the 5 twins."""
    import fork7 as FK
    from gen7 import Runner
    from scipy.stats import spearmanr

    run = Runner()
    cs = FK.cstar()
    out: dict[str, Any] = {}
    for name, plist in (("variants", FK.variants()), ("sources", FK.forced_sources()),
                        ("twins", [dict(FK.twin(w), template=w, vid=f"twin|{w}") for w in TEMPLATE_IDS])):
        recs = []
        for p in plist:
            ids = p["ids"] + cs
            st = run.states(ids, LAYERS_STORE, positions=[len(ids) - 1], want_logits_at=[len(ids) - 1])
            lg = st["logits"][0].float()
            q = class_probs(lg)
            top = torch.topk(lg, 20)
            recs.append({k: p.get(k) for k in ("vid", "sid", "template", "noun", "noun_source", "mode", "pair",
                                               "display", "P", "spec_start", "seg_start", "spec_end",
                                               "prompt_sha256")}
                        | {"ids": p["ids"], "y": float(margin(lg)), "q": q.tolist(),
                           "h": torch.stack([st["h"][l][0] for l in LAYERS_STORE]).float(),
                           "top_ids": top.indices.tolist(), "top_vals": top.values.tolist()})
        torch.save(recs, STATES_DIR / f"fork_{name}.pt")
        out[name] = len(recs)
        logger.info(f"yv: {name} {len(recs)} states")
    V = torch.load(STATES_DIR / "fork_variants.pt")
    S = torch.load(STATES_DIR / "fork_sources.pt")
    ys = np.array([v["y"] for v in V])
    # iteration-6 y_v of the 60 frozen-noun variants (stored with its sampling-validation rows)
    y6 = {}
    for r in read_jsonl(I6_DATA / "sampling_validation_labels.jsonl"):
        y6[f"{r['template']}|{r['noun']}"] = r["y"]
    pairs = [(v["y"], y6[v["vid"]]) for v in V if v["vid"] in y6]
    rho = spearmanr([a for a, _ in pairs], [b for _, b in pairs]).statistic if pairs else float("nan")
    srcq = [{"sid": s["sid"], "mode": s["mode"], "template": s["template"], "pair": s["pair"], "y": s["y"],
             "q": s["q"], "bd_mass": s["q"][0] + s["q"][1]} for s in S]
    res = {"n": out, "y_mean": float(ys.mean()), "y_sd": float(ys.std(ddof=1)),
           "y_by_template": {w: float(np.mean([v["y"] for v in V if v["template"] == w])) for w in TEMPLATE_IDS},
           "iter6_reference": {"y_mean": -0.92, "y_sd": 0.67},
           "spearman_vs_iter6_yv": {"n": len(pairs), "rho": float(rho), "pass_0.9": bool(rho >= 0.9)},
           "sources": srcq, "n_sources_dropped_bd_lt_0.5": sum(s["bd_mass"] < 0.5 for s in srcq),
           "variants": [{"vid": v["vid"], "template": v["template"], "noun": v["noun"], "y": v["y"], "q": v["q"]}
                        for v in V]}
    write_json(RESULTS_DIR / "yv.json", res)
    logger.info(f"yv: y mean {ys.mean():.3f} sd {ys.std(ddof=1):.3f}; spearman vs iter6 {rho:.3f} (n {len(pairs)})")
    run.free()


# ================================================================================================ DAS context
class DASContext:
    """GPU-resident data for one layer L: base states/caches (per template), source states and targets."""

    def __init__(self, run: Any, L: int, V: list[dict], S: list[dict], stacks: dict[str, Any],
                 targets: torch.Tensor | None = None):
        self.run, self.L = run, L
        self.V, self.S = V, S
        self.Hb = torch.stack([v["h"][L] for v in V]).cuda()          # [120, D] fp32
        self.Hs = torch.stack([s["h"][L] for s in S]).cuda()          # [40, D]
        self.yb = torch.tensor([v["y"] for v in V], device="cuda")
        self.Qs = (targets if targets is not None else torch.tensor([s["q"] for s in S])).float().cuda()
        self.src_cls = torch.tensor([0 if s["mode"] == "bfs" else 1 for s in S], device="cuda")
        self.pos = {v["template"]: v["P"] + 31 for v in V}          # p_f per template (prompt + c*)
        self.tmpl_idx = {w: [i for i, v in enumerate(V) if v["template"] == w] for w in TEMPLATE_IDS}
        assert L + 1 >= stacks["min_layer"], "KV stacks do not cover block L+1"
        self.K = {w: {l: stacks["K"][w][l] for l in range(L + 1, N_LAYERS)} for w in stacks["K"]}
        self.Vv = {w: {l: stacks["V"][w][l] for l in range(L + 1, N_LAYERS)} for w in stacks["V"]}
        self.local = {w: {g: j for j, g in enumerate(ix)} for w, ix in self.tmpl_idx.items()}
        # base margins on the SAME single-position path (U3: the KV path differs from a full recompute by up to
        # ~0.27 nats at bf16; every dy is measured against the base's own KV-path margin so the offset cancels)
        ykv = torch.zeros(len(V), device="cuda")
        with torch.no_grad():
            for w, ix in self.tmpl_idx.items():
                for c0 in range(0, len(ix), self.BFIX):
                    cix = ix[c0:c0 + self.BFIX]
                    ykv[cix] = margin(self.logits(w, cix, self.Hb[cix]))
        self.yb_full = self.yb
        self.yb = ykv

    BFIX = 48          # every single-position forward has this batch shape (bf16 results depend on the shape)

    def logits(self, w: str, b_idx: list[int], h_new: torch.Tensor) -> torch.Tensor:
        n = len(b_idx)
        assert n <= self.BFIX
        if n < self.BFIX:                       # pad with copies of the last row to the fixed shape
            b_idx = list(b_idx) + [b_idx[-1]] * (self.BFIX - n)
            h_new = torch.cat([h_new, h_new[-1:].expand(self.BFIX - n, -1)], 0)
        loc = torch.tensor([self.local[w][i] for i in b_idx], device="cuda")
        feed = KVFeed({l: self.K[w][l].index_select(0, loc) for l in self.K[w]},
                      {l: self.Vv[w][l].index_select(0, loc) for l in self.Vv[w]})
        return forward_from(self.run.model, h_new[:, None].to(torch.bfloat16), self.L + 1, feed, self.pos[w])[:n]

    def free(self) -> None:
        self.K, self.Vv = {}, {}           # references only; the shared stacks stay alive
        torch.cuda.empty_cache()


def make_pairs(V: list[dict], S: list[dict], base_w: tuple, src_f: tuple, drop: set[int]) -> list[tuple[int, int]]:
    return [(i, j) for i, v in enumerate(V) if v["template"] in base_w
            for j, s in enumerate(S) if s["template"] in src_f and j not in drop]


def batches_by_template(V: list[dict], pairs: list[tuple[int, int]], bs: int) -> list[tuple[str, list[tuple[int, int]]]]:
    out = []
    for w in TEMPLATE_IDS:
        pw = [p for p in pairs if V[p[0]]["template"] == w]
        for i in range(0, len(pw), bs):
            out.append((w, pw[i:i + bs]))
    return out


def edit_states(hb: torch.Tensor, hs: torch.Tensor, R: torch.Tensor | None) -> torch.Tensor:
    if R is None:
        return hs.clone()
    return hb + ((hs - hb) @ R) @ R.T


@torch.no_grad()
def evaluate(ctx: DASContext, pairs: list[tuple[int, int]], R: torch.Tensor | None, bs: int = 48,
             targets: torch.Tensor | None = None) -> dict[str, np.ndarray]:
    """Per pair: y' (margin after the interchange), class probs, KL to the target. R None = full-state interchange."""
    Qs = ctx.Qs if targets is None else targets
    ys, qs, kls = np.zeros(len(pairs)), np.zeros((len(pairs), 3)), np.zeros(len(pairs))
    order = {p: i for i, p in enumerate(pairs)}
    for w, chunk in batches_by_template(ctx.V, pairs, bs):
        bi = [a for a, _ in chunk]
        si = torch.tensor([b for _, b in chunk], device="cuda")
        hb = ctx.Hb[bi]
        hn = edit_states(hb, ctx.Hs[si], R)
        lg = ctx.logits(w, bi, hn)
        q = class_probs(lg)
        t = Qs[si]
        kl = (t * (t.clamp(min=1e-9).log() - q.log())).sum(-1)
        ix = [order[p] for p in chunk]
        ys[ix] = margin(lg).cpu().numpy()
        qs[ix] = q.cpu().numpy()
        kls[ix] = kl.cpu().numpy()
    return {"y": ys, "q": qs, "kl": kls}


def train_das(ctx: DASContext, pairs: list[tuple[int, int]], ranks: tuple, seed: int, steps: int,
              target_map: torch.Tensor | None = None, val_pairs: list[tuple[int, int]] | None = None,
              eval_every: int = 50, lr: float = DAS_LR, bs: int = DAS_BATCH) -> dict[str, Any]:
    """Nested-rank DAS: R in St(D, kmax) via QR of a free matrix; loss = sum_k KL(q_s || q'_k) over {B, D, O}.
    target_map[j] = the index of the source whose target q is used for source j (SHUF); None = own target."""
    kmax = max(ranks)
    g = torch.Generator().manual_seed(1000 + seed)
    Wf = torch.randn(D_MODEL, kmax, generator=g).cuda().requires_grad_(True)
    opt = torch.optim.Adam([Wf], lr=lr)
    rng = np.random.default_rng(seed)
    tmpls = sorted({ctx.V[a]["template"] for a, _ in pairs})
    by_w = {w: [p for p in pairs if ctx.V[p[0]]["template"] == w] for w in tmpls}
    tm = target_map.cuda() if target_map is not None else None
    hist = []
    best = (float("inf"), None, 0)
    t0 = time.time()
    for step in range(steps):
        w = tmpls[step % len(tmpls)]
        pw = by_w[w]
        sel = rng.choice(len(pw), size=min(bs, len(pw)), replace=False)
        chunk = [pw[i] for i in sel]
        bi = [a for a, _ in chunk]
        si = torch.tensor([b for _, b in chunk], device="cuda")
        tgt = ctx.Qs[tm[si]] if tm is not None else ctx.Qs[si]
        hb, hs = ctx.Hb[bi], ctx.Hs[si]
        tot = 0.0
        for k in ranks:
            with torch.enable_grad():
                Rk = torch.linalg.qr(Wf)[0][:, :k]          # recomputed per rank: one backward per graph
                hn = hb + ((hs - hb) @ Rk) @ Rk.T
                q = class_probs(ctx.logits(w, bi, hn))
                loss = (tgt * (tgt.clamp(min=1e-9).log() - q.log())).sum(-1).mean()
            loss.backward()
            tot += float(loss)
        opt.step()
        opt.zero_grad()
        if (step + 1) % eval_every == 0 or step == steps - 1:
            rec = {"step": step + 1, "train_loss": tot / len(ranks), "seconds": time.time() - t0}
            if val_pairs:
                with torch.no_grad():
                    Rd = torch.linalg.qr(Wf.detach())[0]
                    vl = float(np.mean([evaluate(ctx, val_pairs, Rd[:, :k])["kl"].mean() for k in ranks]))
                rec["val_kl"] = vl
                if vl < best[0]:
                    best = (vl, Rd.clone(), step + 1)
            hist.append(rec)
    R_final = torch.linalg.qr(Wf.detach())[0]
    if val_pairs and best[1] is not None:
        return {"R": best[1], "best_step": best[2], "hist": hist, "R_last": R_final}
    return {"R": R_final, "best_step": steps, "hist": hist, "R_last": R_final}


def recovery_stats(dy: np.ndarray, dy_full: np.ndarray, base_ids: np.ndarray, n_boot: int = 2000,
                   seed: int = 0) -> dict[str, Any]:
    ok = np.abs(dy_full) >= 1.0
    r = dy[ok] / dy_full[ok]
    b = base_ids[ok]
    if r.size == 0:
        return {"n": 0}
    rng = np.random.default_rng(seed)
    ub = np.unique(b)
    meds = []
    for _ in range(n_boot):
        pick = rng.choice(ub, size=len(ub), replace=True)
        vals = np.concatenate([r[b == u] for u in pick])
        meds.append(np.median(vals))
    return {"n": int(r.size), "median": float(np.median(r)), "iqr": [float(np.percentile(r, 25)),
                                                                     float(np.percentile(r, 75))],
            "mean": float(np.mean(r)), "ci95_cluster_boot": [float(np.percentile(meds, 2.5)),
                                                             float(np.percentile(meds, 97.5))]}


def summarize(ctx: DASContext, pairs: list[tuple[int, int]], ev: dict[str, np.ndarray], full: dict[str, np.ndarray]
              ) -> dict[str, Any]:
    yb = ctx.yb.cpu().numpy()
    bi = np.array([a for a, _ in pairs])
    si = np.array([b for _, b in pairs])
    dy = ev["y"] - yb[bi]
    dyf = full["y"] - yb[bi]
    cls = ctx.src_cls.cpu().numpy()[si]
    q = ev["q"]
    iia = float(np.mean(np.where(cls == 0, q[:, 0] > q[:, 1], q[:, 1] > q[:, 0])))
    return {"recovery": recovery_stats(dy, dyf, bi), "iia": iia, "kl_mean": float(ev["kl"].mean()),
            "dy_bfs_src_mean": float(dy[cls == 0].mean()) if (cls == 0).any() else None,
            "dy_dfs_src_mean": float(dy[cls == 1].mean()) if (cls == 1).any() else None,
            "dy_dir_mean": float(np.mean(np.where(cls == 0, dy, -dy))), "n_pairs": len(pairs)}


# ================================================================================================ stage g2
def _load_states() -> tuple[list[dict], list[dict], set[int]]:
    V = torch.load(STATES_DIR / "fork_variants.pt")
    S = torch.load(STATES_DIR / "fork_sources.pt")
    drop = {j for j, s in enumerate(S) if s["q"][0] + s["q"][1] < 0.5}
    return V, S, drop


def stage_g2(args: Any) -> None:
    import fork7 as FK
    from gen7 import Runner
    from scipy.stats import spearmanr, wilcoxon

    run = Runner()
    cs = FK.cstar()
    V, S, drop = _load_states()
    if drop:
        add_deviation("G2_sources_dropped", f"{len(drop)} forced sources with B+D mass < 0.5 dropped: "
                                            f"{[S[j]['sid'] for j in sorted(drop)]}")
    kv = kv_stacks(run, V, cs)
    logger.info(f"g2: base KV stacks built; VRAM {torch.cuda.memory_allocated() / 1e9:.2f} GB")
    train = make_pairs(V, S, TRAIN_W, TRAIN_F, drop)
    held = make_pairs(V, S, HELD_W, HELD_F, drop)
    out: dict[str, Any] = {"n_train_pairs": len(train), "n_heldout_pairs": len(held), "dropped_sources": sorted(drop)}
    quick = bool(getattr(args, "quick", False))
    # ---------------- full-state interchange ceiling by layer (held-out pairs)
    ceil = {}
    for L in range(17, 30):
        ctx = DASContext(run, L, V, S, kv)
        full = evaluate(ctx, held, None)
        yb = ctx.yb.cpu().numpy()
        bi = np.array([a for a, _ in held])
        cls = ctx.src_cls.cpu().numpy()[np.array([b for _, b in held])]
        dyf = full["y"] - yb[bi]
        ceil[L] = {"dy_full_bfs_src_mean": float(dyf[cls == 0].mean()), "dy_full_dfs_src_mean": float(dyf[cls == 1].mean()),
                   "share_abs_ge_1": float(np.mean(np.abs(dyf) >= 1))}
        ctx.free()
        del ctx
    out["full_state_ceiling_by_layer"] = ceil
    write_json(RESULTS_DIR / "g2_das_partial.json", out)
    logger.info(f"g2: ceiling {json.dumps({k: round(v['dy_full_bfs_src_mean'], 2) for k, v in ceil.items()})}")
    # ---------------- layer scan: rank-1, seed 0, 3-fold leave-one-template-out CV inside W1-W3
    scan_steps = 60 if quick else 150
    scan = {}
    for L in DAS_LAYERS_SCAN:
        ctx = DASContext(run, L, V, S, kv)
        rec = []
        for fold_w in TRAIN_W:
            tr_w = tuple(w for w in TRAIN_W if w != fold_w)
            tp = make_pairs(V, S, tr_w, TRAIN_F, drop)
            vp = make_pairs(V, S, (fold_w,), TRAIN_F, drop)
            fit = train_das(ctx, tp, (1,), seed=0, steps=scan_steps, eval_every=scan_steps)
            ev = evaluate(ctx, vp, fit["R"][:, :1])
            full = evaluate(ctx, vp, None)
            st = summarize(ctx, vp, ev, full)
            rec.append(st["recovery"].get("median", float("nan")))
        scan[L] = {"cv_median_recovery_by_fold": rec, "cv_median_recovery": float(np.nanmedian(rec))}
        logger.info(f"g2 scan L{L}: {scan[L]}")
        ctx.free()
        del ctx
    Lstar = max(DAS_LAYERS_SCAN, key=lambda L: (round(scan[L]["cv_median_recovery"], 6), -L))
    out["layer_scan"] = {"steps_per_fold": scan_steps, "by_layer": scan, "L_star": Lstar,
                         "rule": "argmax of train-CV median recovery (rank 1, seed 0); ties -> earlier layer"}
    write_json(RESULTS_DIR / "g2_layer_scan.json", out["layer_scan"])
    # ---------------- k* and step count from a 3-fold CV of the nested run at L* (seed 0)
    main_steps = 120 if quick else DAS_STEPS
    layers = [Lstar] + ([DAS_LAYER_FIXED] if Lstar != DAS_LAYER_FIXED else [])
    res_layers: dict[int, Any] = {}
    for L in layers:
        ctx = DASContext(run, L, V, S, kv)
        full_h = evaluate(ctx, held, None)
        lay: dict[str, Any] = {"seeds": {}, "controls": {}}
        if L == Lstar:
            cvk = {k: [] for k in DAS_RANKS}
            for fold_w in TRAIN_W:
                tr_w = tuple(w for w in TRAIN_W if w != fold_w)
                tp = make_pairs(V, S, tr_w, TRAIN_F, drop)
                vp = make_pairs(V, S, (fold_w,), TRAIN_F, drop)
                fit = train_das(ctx, tp, DAS_RANKS, seed=0, steps=main_steps // 2, eval_every=main_steps // 2)
                full = evaluate(ctx, vp, None)
                for k in DAS_RANKS:
                    st = summarize(ctx, vp, evaluate(ctx, vp, fit["R"][:, :k]), full)
                    cvk[k].append(st["recovery"].get("median", float("nan")))
            cv_med = {k: float(np.nanmedian(v)) for k, v in cvk.items()}
            mx = max(cv_med.values())
            kstar = min(k for k in DAS_RANKS if cv_med[k] >= 0.9 * mx)
            lay["train_cv"] = {"by_k": cv_med, "k_star": kstar, "steps_per_fold": main_steps // 2}
        # nested DAS, 3 seeds, all train pairs; early stopping on the held-in validation template rotation
        Rs = {}
        for sd in DAS_SEEDS:
            val_w = TRAIN_W[sd % 3]
            tp = make_pairs(V, S, tuple(w for w in TRAIN_W if w != val_w), TRAIN_F, drop)
            vp = make_pairs(V, S, (val_w,), TRAIN_F, drop)
            fit = train_das(ctx, tp, DAS_RANKS, seed=sd, steps=main_steps, val_pairs=vp, eval_every=50)
            R = fit["R"]
            Rs[sd] = R
            torch.save(R.cpu(), SUBSPACE_DIR / f"das_L{L}_seed{sd}.pt")
            per_k = {}
            for k in DAS_RANKS:
                ev = evaluate(ctx, held, R[:, :k])
                per_k[k] = summarize(ctx, held, ev, full_h)
                per_k[k]["dy_raw"] = (ev["y"] - ctx.yb.cpu().numpy()[np.array([a for a, _ in held])]).tolist()
            lay["seeds"][sd] = {"best_step": fit["best_step"], "hist": fit["hist"], "val_template": val_w,
                                "per_k": per_k}
            logger.info(f"g2 L{L} seed {sd}: " + ", ".join(f"k{k} rec {per_k[k]['recovery'].get('median', float('nan')):.3f}"
                                                           for k in DAS_RANKS))
        # RAND: 50 Haar-random subspaces
        rand = {k: [] for k in DAS_RANKS}
        rand_dy = {k: [] for k in DAS_RANKS}
        gq = torch.Generator().manual_seed(4242)
        for i in range(10 if quick else 50):
            Rr = torch.linalg.qr(torch.randn(D_MODEL, max(DAS_RANKS), generator=gq).cuda())[0]
            for k in DAS_RANKS:
                ev = evaluate(ctx, held, Rr[:, :k])
                st = summarize(ctx, held, ev, full_h)
                rand[k].append(st["recovery"].get("median", float("nan")))
                rand_dy[k].append(ev["y"] - ctx.yb.cpu().numpy()[np.array([a for a, _ in held])])
        lay["controls"]["RAND"] = {k: {"median_recovery_median": float(np.nanmedian(v)),
                                       "median_recovery_p95": float(np.nanpercentile(v, 95)),
                                       "per_subspace": v} for k, v in rand.items()}
        # paired Wilcoxon (seed-0 DAS vs mean RAND) over held-out pairs on per-pair recovery
        bi = np.array([a for a, _ in held])
        yb = ctx.yb.cpu().numpy()
        dyf = full_h["y"] - yb[bi]
        ok = np.abs(dyf) >= 1
        wil = {}
        for k in DAS_RANKS:
            r_das = np.median([np.array(lay["seeds"][sd]["per_k"][k]["dy_raw"]) for sd in DAS_SEEDS], 0)[ok] / dyf[ok]
            r_rand = np.mean(np.stack(rand_dy[k]), 0)[ok] / dyf[ok]
            try:
                wtest = wilcoxon(r_das, r_rand, alternative="greater")
                wil[k] = {"p": float(wtest.pvalue), "median_diff": float(np.median(r_das - r_rand)),
                          "das_median": float(np.median(r_das)), "rand_median": float(np.median(r_rand))}
            except ValueError as e:
                wil[k] = {"error": str(e)}
        lay["controls"]["WILCOXON_DAS_vs_RAND"] = wil
        # SHUF: source labels permuted across the train sources (balanced), 3 permutations
        if L == Lstar:                      # SHUF at L* (plan); the second layer gets RAND, DiM, natural variance
            shuf = {}
            tr_src = sorted({b for _, b in train})
            for pi in range(3):
                rng = np.random.default_rng(77 + pi)
                perm = np.array(tr_src)[rng.permutation(len(tr_src))]
                tmap = torch.arange(len(S))
                tmap[torch.tensor(tr_src)] = torch.tensor(perm)
                n_cross = int(sum(S[a]["mode"] != S[b]["mode"] for a, b in zip(tr_src, perm)))
                fit = train_das(ctx, train, DAS_RANKS, seed=10 + pi, steps=main_steps, target_map=tmap)
                trainfit = {}
                heldsc = {}
                full_tr = evaluate(ctx, train[::4], None)
                for k in DAS_RANKS:
                    ev_tr = evaluate(ctx, train[::4], fit["R"][:, :k], targets=ctx.Qs[tmap.cuda()])
                    trainfit[k] = {"kl_to_shuffled_targets": float(ev_tr["kl"].mean())}
                    ev = evaluate(ctx, held, fit["R"][:, :k])
                    heldsc[k] = summarize(ctx, held, ev, full_h)
                _ = full_tr
                shuf[pi] = {"n_label_flips": n_cross, "train_fit": trainfit, "heldout_true_targets": heldsc}
                torch.save(fit["R"].cpu(), SUBSPACE_DIR / f"shuf_L{L}_perm{pi}.pt")
            lay["controls"]["SHUF"] = shuf
        # DiM: rank-1 interchange along normalise(mean BFS sources - mean DFS sources)
        trs = sorted({b for _, b in train})
        hb_ = ctx.Hs[[j for j in trs if S[j]["mode"] == "bfs"]].mean(0)
        hd_ = ctx.Hs[[j for j in trs if S[j]["mode"] == "dfs"]].mean(0)
        u = (hb_ - hd_) / (hb_ - hd_).norm()
        torch.save(u.cpu(), SUBSPACE_DIR / f"dim_L{L}.pt")
        ev = evaluate(ctx, held, u[:, None])
        lay["controls"]["DiM_rank1_interchange"] = summarize(ctx, held, ev, full_h)
        # NATURAL-VARIANCE (Makelov): share of the twin's cross-prompt variance inside R_k; coordinate vs y_v
        Hv = ctx.Hb
        Hc = Hv - Hv.mean(0, keepdim=True)
        Sig = (Hc.T @ Hc) / (Hv.shape[0] - 1)
        trS = float(torch.trace(Sig))
        nat = {}
        R0 = Rs[0]
        for k in DAS_RANKS:
            Rk = R0[:, :k]
            share = float(torch.trace(Rk.T @ Sig @ Rk)) / trS
            rs = []
            gq2 = torch.Generator().manual_seed(9 + k)
            for _ in range(200 if quick else 1000):
                Rr = torch.linalg.qr(torch.randn(D_MODEL, k, generator=gq2).cuda())[0]
                rs.append(float(torch.trace(Rr.T @ Sig @ Rr)) / trS)
            nat[k] = {"share": share, "random_p95": float(np.percentile(rs, 95)), "random_mean": float(np.mean(rs)),
                      "share_over_random_mean": share / max(np.mean(rs), 1e-12)}
        coord = (Hv @ R0[:, :1])[:, 0].cpu().numpy()
        yv = ctx.yb_full.cpu().numpy()
        rho = float(spearmanr(coord, yv).statistic)
        rng = np.random.default_rng(5)
        null = [abs(spearmanr(coord, rng.permutation(yv)).statistic) for _ in range(500 if quick else 2000)]
        p_perm = (1 + sum(n >= abs(rho) for n in null)) / (1 + len(null))
        coord_dim = (Hv @ u).cpu().numpy()
        nat["spearman_R1_coord_vs_yv"] = {"rho": rho, "p_perm": float(p_perm)}
        nat["spearman_DiM_coord_vs_yv"] = float(spearmanr(coord_dim, yv).statistic)
        nat["dormant_flag"] = bool(nat[1]["share"] <= nat[1]["random_p95"] and abs(rho) < 0.2)
        lay["controls"]["NATURAL_VARIANCE"] = nat
        # principal angles between seeds (stability) at k*, and DiM vs R_1
        ks = lay.get("train_cv", {}).get("k_star", 1)
        ang = {}
        for a in DAS_SEEDS:
            for b in DAS_SEEDS:
                if a < b:
                    ang[f"{a}-{b}"] = torch.linalg.svdvals(Rs[a][:, :ks].T @ Rs[b][:, :ks]).tolist()
        lay["seed_principal_cosines_at_kstar"] = ang
        lay["dim_vs_R1_abs_cos"] = float(abs(u @ R0[:, 0]))
        res_layers[L] = lay
        out["layers"] = {str(k): v for k, v in res_layers.items()}
        write_json(RESULTS_DIR / "g2_das_partial.json", out)
        ctx.free()
        del ctx
        gc.collect()
    out["L_star"] = Lstar
    out["k_star"] = res_layers[Lstar]["train_cv"]["k_star"]
    write_json(RESULTS_DIR / "g2_das.json", out)
    run.free()


# ================================================================================================ stage g2r (RINIT)
def stage_g2r(args: Any) -> None:
    """Randomly initialised Gemma (same text config, HF _init_weights, torch seed 0): same prompts, c*, pairs and
    targets (the TRAINED model's q_s); same map class and training at L*. Reports held-out dy toward the targets."""
    import fork7 as FK
    from cfg import IT_ID, IT_REV, model_path
    from gen7 import edit_hooks
    from transformers import AutoConfig, AutoTokenizer, Gemma3ForCausalLM

    das = read_json(RESULTS_DIR / "g2_das.json")
    Lstar = int(das["L_star"])
    path = model_path(IT_ID, IT_REV)
    tok = AutoTokenizer.from_pretrained(path)
    tcfg = AutoConfig.from_pretrained(path).text_config
    tcfg._attn_implementation = "sdpa"
    torch.manual_seed(0)
    torch.cuda.set_per_process_memory_fraction(0.95, 0)
    old = torch.get_default_dtype()
    torch.set_default_dtype(torch.bfloat16)
    try:
        with torch.device("cuda"):
            model = Gemma3ForCausalLM(tcfg)
    finally:
        torch.set_default_dtype(old)
    model.eval()
    model.requires_grad_(False)
    model._aii_kind = "it"
    info = {"init": "HF Gemma3ForCausalLM(text_config) + post_init (_init_weights), torch seed 0, bf16",
            "initializer_range": tcfg.initializer_range}

    class R0:
        pass
    run = R0()
    run.model, run.tok = model, tok

    def prefill(ids: list[int], B: int, row_edits=None, capture=None):
        from transformers.cache_utils import DynamicCache
        import engine as EG

        inp = torch.tensor([ids], device="cuda").expand(B, -1).contiguous()
        cache = DynamicCache()
        with torch.no_grad(), edit_hooks(model, row_edits or [], capture):
            out = model.model(input_ids=inp, past_key_values=cache, use_cache=True)
        lg = EG.lm_logits(model, out.last_hidden_state[:, -1])
        return {"kv": [(K, V) for K, V in EG._kv_from_cache(cache)], "logits": lg}
    run.prefill = prefill

    def states(ids: list[int], layers: list[int], positions=None, want_logits_at=None):
        import engine as EG

        cap = {}

        def mk(l):
            def g(x):
                cap[l] = (x[0] if positions is None else x[0, positions]).float().cpu()
            return g
        with torch.no_grad(), edit_hooks(model, [], {("resid", l): mk(l) for l in layers}):
            out = model.model(input_ids=torch.tensor([ids], device="cuda"), use_cache=False)
        r = {"h": cap}
        if want_logits_at is not None:
            r["logits"] = EG.lm_logits(model, out.last_hidden_state[0, want_logits_at]).cpu()
        return r
    run.states = states
    cs = FK.cstar()
    Vt, St, drop = _load_states()
    V, S = [], []
    finite = True
    spread = []
    for lst, outl in ((Vt, V), (St, S)):
        for p in lst:
            ids = p["ids"] + cs
            st = states(ids, [Lstar], positions=[len(ids) - 1], want_logits_at=[len(ids) - 1])
            lg = st["logits"][0].float()
            finite &= bool(torch.isfinite(lg).all())
            spread.append(float(lg.std()))
            h = torch.zeros(N_LAYERS, D_MODEL)
            h[Lstar] = st["h"][Lstar][0]
            outl.append(dict({k: p[k] for k in p if k not in ("h",)}, h=h, y=float(margin(lg)),
                             q=class_probs(lg).tolist()))
    info.update({"finite_logits": finite, "logit_sd_mean": float(np.mean(spread)),
                 "rinit_y_mean": float(np.mean([v["y"] for v in V])), "rinit_y_sd": float(np.std([v["y"] for v in V]))})
    if not finite:
        add_deviation("G2_RINIT_nonfinite", "random-init forward gave non-finite logits; control reported as failed")
        write_json(RESULTS_DIR / "g2_rinit.json", {"info": info, "failed": True})
        return
    kv = kv_stacks(run, V, cs, min_layer=Lstar + 1)
    targets = torch.tensor([s["q"] for s in St])          # the TRAINED model's q_s
    ctx = DASContext(run, Lstar, V, S, kv, targets=targets)
    train = make_pairs(V, S, TRAIN_W, TRAIN_F, drop)
    held = make_pairs(V, S, HELD_W, HELD_F, drop)
    steps = 120 if getattr(args, "quick", False) else DAS_STEPS
    full_h = evaluate(ctx, held, None)
    res = {"info": info, "L": Lstar, "seeds": {}}
    for sd in (0,):
        fit = train_das(ctx, train, DAS_RANKS, seed=sd, steps=steps)
        per_k = {}
        bi = np.array([a for a, _ in held])
        si = np.array([b for _, b in held])
        cls = np.array([0 if S[j]["mode"] == "bfs" else 1 for j in si])
        for k in DAS_RANKS:
            ev = evaluate(ctx, held, fit["R"][:, :k])
            dy = ev["y"] - ctx.yb.cpu().numpy()[bi]
            per_k[k] = {"dy_dir_mean": float(np.mean(np.where(cls == 0, dy, -dy))),
                        "kl_to_trained_targets": float(ev["kl"].mean()),
                        "kl_no_edit": float(np.mean([(targets[j] * (targets[j].clamp(min=1e-9).log()
                                                                       - torch.tensor(V[i]["q"]).clamp(min=1e-9).log())).sum()
                                                      for i, j in held[::8]])),
                        "iia": float(np.mean(np.where(cls == 0, ev["q"][:, 0] > ev["q"][:, 1],
                                                      ev["q"][:, 1] > ev["q"][:, 0])))}
        dyf = full_h["y"] - ctx.yb.cpu().numpy()[bi]
        res["seeds"][sd] = {"per_k": per_k, "full_state_dy_dir_mean": float(np.mean(np.where(cls == 0, dyf, -dyf))),
                            "hist": fit["hist"]}
    write_json(RESULTS_DIR / "g2_rinit.json", res)
    logger.info(f"g2r: {json.dumps(res['seeds'][0]['per_k'])}")


# ================================================================================================ stage g2d (dose sweep)
def stage_g2d(args: Any) -> None:
    """COMMIT #3, then the generation dose sweep (N=50 per cell, CRN; twin W1-W5 x 10 slots; prompt + c*
    prefilled; one edit at (L*, p_f) in the prefill). DAS: h' = h + lam R (c_Y - R^T h); DiM: h' = h + beta u with
    beta matched by bisection to the DAS cell's mean teacher-forced dy over the 72 train bases."""
    import commit as CM
    import fork7 as FK
    from gen7 import Edit, Runner

    das = read_json(RESULTS_DIR / "g2_das.json")
    Lstar, kstar = int(das["L_star"]), int(das["k_star"])
    run = Runner()
    cs = FK.cstar()
    V, S, drop = _load_states()
    R = torch.load(SUBSPACE_DIR / f"das_L{Lstar}_seed0.pt").cuda()[:, :kstar]
    u = torch.load(SUBSPACE_DIR / f"dim_L{Lstar}.pt").cuda()
    Rr = torch.linalg.qr(torch.randn(D_MODEL, kstar, generator=torch.Generator().manual_seed(31337)).cuda())[0]
    trs = sorted({j for j, s in enumerate(S) if s["template"] in TRAIN_F and j not in drop})
    Hs = torch.stack([S[j]["h"][Lstar] for j in trs]).cuda()
    modes = [S[j]["mode"] for j in trs]
    c = {Y: (Hs[[i for i, m in enumerate(modes) if m == Y]] @ R).mean(0) for Y in ("bfs", "dfs")}
    c_rand = (Hs[[i for i, m in enumerate(modes) if m == "bfs"]] @ Rr).mean(0)
    Vtr = [v for v in V if v["template"] in TRAIN_W]
    kv = kv_stacks(run, Vtr, cs, min_layer=Lstar + 1)
    ctx = DASContext(run, Lstar, Vtr, S, kv)

    @torch.no_grad()
    def mean_dy(fn) -> float:
        dys = []
        for w in TRAIN_W:
            ix = ctx.tmpl_idx[w]
            for c0 in range(0, len(ix), ctx.BFIX):
                cix = ix[c0:c0 + ctx.BFIX]
                lg = ctx.logits(w, cix, fn(ctx.Hb[cix]))
                dys.append((margin(lg) - ctx.yb[cix]).cpu().numpy())
        return float(np.mean(np.concatenate(dys)))

    def das_fn(lam: float, Y: str, RR=R, cc=None):
        cY = c[Y] if cc is None else cc
        return lambda h: h + lam * ((cY[None] - h @ RR) @ RR.T)

    cells = []
    betas = {}
    for Y in ("bfs", "dfs"):
        for lam in DOSES:
            target = mean_dy(das_fn(lam, Y))
            lo, hi = (0.0, 3000.0) if Y == "bfs" else (-3000.0, 0.0)
            for _ in range(40):
                mid = (lo + hi) / 2
                v = mean_dy(lambda h, b=mid: h + b * u[None])
                if v < target:                  # mean dy increases with beta (u points toward BFS sources)
                    lo = mid
                else:
                    hi = mid
            beta = (lo + hi) / 2
            dmd = mean_dy(lambda h, b=beta: h + b * u[None])
            betas[f"{Y}|{lam}"] = {"das_mean_dy": target, "beta": beta, "dim_mean_dy": dmd,
                                   "matched": bool(abs(dmd - target) < 0.05 * max(abs(target), 0.1))}
            cells.append(("DAS", Y, lam))
            cells.append(("DiM", Y, lam))
    rand_dy = mean_dy(das_fn(1.0, "bfs", Rr, c_rand))
    ctx.free()
    del ctx, kv
    torch.cuda.empty_cache()
    c3 = CM.commit("commit3", {"L_star": Lstar, "k_star": kstar,
                               "subspace_sha256": {"das": sha256_file(SUBSPACE_DIR / f"das_L{Lstar}_seed0.pt"),
                                                   "dim": sha256_file(SUBSPACE_DIR / f"dim_L{Lstar}.pt")},
                               "target_coordinates": {Y: c[Y].tolist() for Y in c}, "doses": list(DOSES),
                               "dim_betas_matched_tf_effect": betas, "rand_cell": {"seed": 31337, "mean_dy": rand_dy},
                               "cells": [list(x) for x in cells] + [["twin"], ["forced_bfs_F5"], ["RAND", "bfs", 1.0]],
                               "g2l": "logit-only interchange, DAS toward BFS at lambda 1 and at the knob dose"})
    logger.info(f"commit3 {c3['sha256'][:12]}")
    raw = DATA_DIR / "raw_g2dose.jsonl"
    done = {r["row_id"] for r in read_jsonl(raw)}
    tf_pred = {}
    tt = {int(k): v for k, v in FK.token_table().items()}

    def cell_rows(w: str, name: str, edit: Any, meta: dict) -> list[dict]:
        rows = [{"row_id": f"g2|{name}|{w}|{k}", "ukey": slot_key7("G2", w, k), "edits": [edit] if edit else [],
                 "meta": dict(meta, part="G2", cell=name, template=w, slot=k)} for k in range(10)]
        return [r for r in rows if r["row_id"] not in done]

    order = [("twin", None, None)] + [("DAS", "bfs", lam) for lam in DOSES] + \
            [("DiM", "bfs", lam) for lam in DOSES] + [("RAND", "bfs", 1.0)] + \
            [("DAS", "dfs", lam) for lam in DOSES] + [("DiM", "dfs", lam) for lam in DOSES]

    def make_f(meth: str, Y: str | None, lam: float | None):
        if meth == "DAS":
            return das_fn(lam, Y)
        if meth == "DiM":
            b = betas[f"{Y}|{lam}"]["beta"]
            return lambda h, b=b: h + b * u[None]
        if meth == "RAND":
            return das_fn(1.0, "bfs", Rr, c_rand)
        return None

    # all cells of one template share fixed-shape batches (one prompt per batch; each row has its own edit and CRN
    # stream, so a row's computation does not depend on its batch-mates); rows ordered by cell
    for w in TEMPLATE_IDS:
        p = FK.twin(w)
        ids = p["ids"] + cs
        pf = len(ids) - 1
        rows_w = []
        for meth, Y, lam in order:
            name = "twin" if meth == "twin" else f"{meth}|{Y}|{lam}"
            f = make_f(meth, Y, lam)
            edit = None
            if f is not None:
                edit = Edit("resid", Lstar, [pf], (lambda x, r, f=f: f(x.reshape(-1, D_MODEL)).reshape(x.shape)),
                            name=name, log={"layer": Lstar, "method": meth, "dir": Y, "lambda": lam})
            with torch.no_grad():
                lg = run.logits_rows(ids, 1, [(edit, torch.tensor([0], device="cuda"))] if edit else [])[0, 0]
            pr = torch.softmax(lg.float(), -1)
            pb = float(sum(pr[t] * tt[t]["p_bfs"] for t in tt if tt[t]["p_bfs"] is not None))
            tf_pred.setdefault(name, []).append({"template": w, "m": float(margin(lg)), "pred_attempted_bfs": pb,
                                                 "p_B": float(pr[list(B_IDS)].sum()),
                                                 "p_D": float(pr[list(D_IDS)].sum())})
            rows_w += cell_rows(w, name, edit, {"method": meth, "dir": Y, "lambda": lam})
        write_json(RESULTS_DIR / "g2_dose_tf_pred.json", tf_pred)
        if rows_w:
            run.run_cell(ids, cs, rows_w, raw, f"G2:{w}")
    # forced-BFS ceiling (natural sampling from index 0, prompt F5 with iteration 6's display name)
    pfz = FK.forced("bfs", "F5", 3)
    rows = [{"row_id": f"g2|forced_bfs_F5|{w}|{k}", "ukey": slot_key7("G2", w, k),
             "meta": {"part": "G2", "cell": "forced_bfs_F5", "template": w, "slot": k, "method": "prompt"}}
            for w in TEMPLATE_IDS for k in range(10)]
    rows = [r for r in rows if r["row_id"] not in done]
    if rows:
        run.run_cell(pfz["ids"], [], rows, raw, "G2:forced")
    # G2-L: logit-only interchange (DAS toward BFS at lambda 1 and at 0.5)
    for w in TEMPLATE_IDS:
        p = FK.twin(w)
        ids = p["ids"] + cs
        pf = len(ids) - 1
        rows = []
        for lam in (1.0, 0.5):
            name = f"DAS-L|bfs|{lam}"
            f = das_fn(lam, "bfs")
            edit = Edit("resid", Lstar, [pf], (lambda x, r, f=f: f(x.reshape(-1, D_MODEL)).reshape(x.shape)),
                        name=name, log={"layer": Lstar, "method": "DAS-L", "dir": "bfs", "lambda": lam})
            rows += cell_rows(w, name, edit, {"method": "DAS-L", "dir": "bfs", "lambda": lam})
        if rows:
            run.run_cell(ids, cs, rows, raw, f"G2L:{w}", logit_only=True)
    run.free()
    _ = math


# ================================================================================================ smoke test
def stage_g2smoke(args: Any) -> None:
    """Small end-to-end run of the DAS machinery at L22 (timing for the full stage; no decisive output)."""
    import fork7 as FK
    from gen7 import Runner

    run = Runner()
    cs = FK.cstar()
    V, S, drop = _load_states()
    t0 = time.time()
    kv = kv_stacks(run, V, cs)
    t_kv = time.time() - t0
    ctx = DASContext(run, 22, V, S, kv)
    train = make_pairs(V, S, TRAIN_W, TRAIN_F, drop)
    held = make_pairs(V, S, HELD_W, HELD_F, drop)
    t1 = time.time()
    full = evaluate(ctx, held, None)
    t_eval = time.time() - t1
    t2 = time.time()
    fit = train_das(ctx, train, DAS_RANKS, seed=0, steps=20, eval_every=10)
    t_train = (time.time() - t2) / 20
    ev = evaluate(ctx, held, fit["R"][:, :1])
    st = summarize(ctx, held, ev, full)
    yb = ctx.yb.cpu().numpy()
    bi = np.array([a for a, _ in held])
    res = {"seconds_kv_120": t_kv, "seconds_eval_heldout_pass": t_eval, "seconds_per_train_step_4ranks": t_train,
           "n_train": len(train), "n_held": len(held), "k1_after_20_steps": st,
           "full_dy_mean": float((full["y"] - yb[bi]).mean()),
           "kv_vs_full_base_margin_abs_diff_mean": float((ctx.yb - ctx.yb_full).abs().mean()),
           "vram_peak_gb": torch.cuda.max_memory_allocated() / 1e9}
    write_json(RESULTS_DIR / "g2_smoke.json", res)
    logger.info(f"g2smoke: {json.dumps(res)[:1500]}")
    run.free()


# ================================================================================================ per-pair export
def stage_g2pairs(args: Any) -> None:
    """Per held-out pair at L*: dy_full and dy under DAS (seed 0, every k), the mean of 5 Haar-random subspaces, SHUF
    (permutation 0) and DiM, all on the same fixed-shape single-position path (for method_out.json)."""
    import fork7 as FK
    from gen7 import Runner

    das = read_json(RESULTS_DIR / "g2_das.json")
    L = int(das["L_star"])
    run = Runner()
    cs = FK.cstar()
    V, S, drop = _load_states()
    kv = kv_stacks(run, V, cs, min_layer=L + 1)
    ctx = DASContext(run, L, V, S, kv)
    held = make_pairs(V, S, HELD_W, HELD_F, drop)
    bi = np.array([a for a, _ in held])
    yb = ctx.yb.cpu().numpy()[bi]
    full = evaluate(ctx, held, None)["y"] - yb
    R0 = torch.load(SUBSPACE_DIR / f"das_L{L}_seed0.pt").cuda()
    pred = {}
    for k in DAS_RANKS:
        pred[f"das_k{k}"] = evaluate(ctx, held, R0[:, :k])["y"] - yb
        gq = torch.Generator().manual_seed(4242)
        rr = []
        for _ in range(5):
            Rr = torch.linalg.qr(torch.randn(D_MODEL, k, generator=gq).cuda())[0]
            rr.append(evaluate(ctx, held, Rr)["y"] - yb)
        pred[f"rand_k{k}"] = np.mean(rr, 0)
        ps = SUBSPACE_DIR / f"shuf_L{L}_perm0.pt"
        if ps.exists():
            pred[f"shuf_k{k}"] = evaluate(ctx, held, torch.load(ps).cuda()[:, :k])["y"] - yb
    u = torch.load(SUBSPACE_DIR / f"dim_L{L}.pt").cuda()
    pred["dim"] = evaluate(ctx, held, u[:, None])["y"] - yb
    rows = [{"base": V[a]["vid"], "source": S[b]["sid"], "source_class": S[b]["mode"], "dy_full": float(full[i]),
             "pred": {k: float(v[i]) for k, v in pred.items()}} for i, (a, b) in enumerate(held)]
    write_json(RESULTS_DIR / "g2_pairs.json", {"L": L, "n": len(rows), "rows": rows})
    run.free()
