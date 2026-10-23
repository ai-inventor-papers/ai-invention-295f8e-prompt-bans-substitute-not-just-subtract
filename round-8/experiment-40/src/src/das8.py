#!/usr/bin/env python3
"""das8: ONE DAS protocol for both families and both sites (declared in commit #0 before any fit).

MAP CLASS. W in R^{D x 8} (free), R = QR(W)[:, :k] (orthonormal columns, nested ranks k in {1, 2, 4, 8}); one rank is
sampled per step (Matryoshka-style). Interchange: h <- h + R (R^T h_src - R^T h).
OBJECTIVE. KL(q_src || q_edit) over the class bins {classes..., other} at the decision position d (bounded, CDAS-style;
q_src = the source's own unedited class distribution, or a supplied target for label controls / random-init nets).
READOUT. margin = log P(c_src) - log P(c_base) at d; Delta = margin_edit - margin_base, both on the same path.
SITES.
  'dec' at block L: the OUTPUT of block L at d is edited; blocks L+1..N-1 are run for position d only against the
     base's cached keys/values of positions < d. Several edits of one base run as Q parallel queries at position d
     (each query attends to the prefix and to itself only), G bases per batch (left-padded prefixes, masked).
  'band' (Qwen T10, blocks 12-23, all spec positions, ONE shared R): the outputs of every band block are edited at
     every spec position (source states at the aligned spec offset); positions p1..d are recomputed through blocks
     band_start..N-1 against the base's cached keys/values of positions < p1 (per-block gradient checkpointing).
"""

from __future__ import annotations

import gc
import math
import time
from typing import Any, Callable

import numpy as np
import torch
from loguru import logger

from engine8 import LM, KVFeed, prefill, states_at


# ================================================================================================ classes
class ClassMap:
    """Class token sets at d. probs() -> [..., C + 1] (classes..., other); lp() -> log P(c) [..., C]."""

    def __init__(self, classes: list[str], token_sets: dict[str, list[int]]):
        self.classes = list(classes)
        self.sets = {c: sorted(set(int(t) for t in token_sets[c])) for c in classes}
        allt = [t for c in classes for t in self.sets[c]]
        assert len(allt) == len(set(allt)), "class token sets must be disjoint"
        self.C = len(classes)
        self._idx: dict[str, torch.Tensor] = {}

    def idx(self, c: str, dev: torch.device) -> torch.Tensor:
        k = f"{c}|{dev}"
        if k not in self._idx:
            self._idx[k] = torch.tensor(self.sets[c], device=dev, dtype=torch.long)
        return self._idx[k]

    def lp(self, logits: torch.Tensor) -> torch.Tensor:
        z = logits.float()
        lz = torch.logsumexp(z, -1, keepdim=True)
        return torch.stack([torch.logsumexp(z.index_select(-1, self.idx(c, z.device)), -1) for c in self.classes],
                           -1) - lz

    def probs(self, logits: torch.Tensor) -> torch.Tensor:
        p = self.lp(logits).exp()
        other = (1 - p.sum(-1, keepdim=True)).clamp(min=1e-9)
        return torch.cat([p, other], -1)

    def margin(self, logits: torch.Tensor, ci: torch.Tensor, cb: torch.Tensor) -> torch.Tensor:
        lp = self.lp(logits)
        return lp.gather(-1, ci[..., None])[..., 0] - lp.gather(-1, cb[..., None])[..., 0]

    def argmax(self, logits: torch.Tensor) -> torch.Tensor:
        return self.probs(logits)[..., :self.C].argmax(-1)


def kl(t: torch.Tensor, q: torch.Tensor) -> torch.Tensor:
    return (t * (t.clamp(min=1e-9).log() - q.clamp(min=1e-9).log())).sum(-1)


def _pin(t: torch.Tensor) -> torch.Tensor:
    return t.cpu().pin_memory() if torch.cuda.is_available() else t.cpu()


# ================================================================================================ geometry helpers
def haar(seed: int, D: int, k: int) -> torch.Tensor:
    g = torch.Generator().manual_seed(int(seed))
    q, _ = torch.linalg.qr(torch.randn(D, k, generator=g, dtype=torch.float64))
    return q.float()


def orth(W: torch.Tensor) -> torch.Tensor:
    q, _ = torch.linalg.qr(W.double())
    return q.float()


def principal_cosines(A: torch.Tensor, B: torch.Tensor) -> np.ndarray:
    return torch.linalg.svdvals(A.double().T @ B.double()).cpu().numpy()


def pca_basis(X: torch.Tensor, n: int) -> tuple[torch.Tensor, torch.Tensor]:
    """Top-n principal directions (columns) of rows X (centred) and the covariance matrix."""
    Xc = X.double() - X.double().mean(0, keepdim=True)
    S = Xc.T @ Xc / max(1, Xc.shape[0] - 1)
    ev, U = torch.linalg.eigh(S)
    order = torch.argsort(ev, descending=True)
    return U[:, order[:n]].float(), S.float()


def variance_share(R: torch.Tensor, S: torch.Tensor) -> float:
    R = R.double().to(S.device)
    S = S.double()
    return float(torch.trace(R.T @ S @ R) / torch.trace(S))


def project_map(R: torch.Tensor, U: torch.Tensor) -> torch.Tensor | None:
    """R projected onto span(U) and re-orthonormalised (None if the projection loses rank)."""
    P = U.double() @ (U.double().T @ R.double())
    sv = torch.linalg.svdvals(P)
    if float(sv.min()) < 1e-6:
        return None
    return orth(P)


# ================================================================================================ decision site
class DecSite:
    """Decision-site data of one unit: block outputs at d (all blocks), unedited class distributions, and per-base
    keys/values of positions < d (CPU pinned, left-padded to a common length)."""

    def __init__(self, lm: LM, prompts: dict[str, dict[str, Any]], cmap: ClassMap, base_keys: list[str],
                 all_keys: list[str], G: int = 4, Q: int = 12):
        self.lm, self.P, self.cmap = lm, prompts, cmap
        self.G, self.Q = G, Q
        self.dev = lm.dev
        t0 = time.time()
        keys = list(dict.fromkeys(all_keys))
        st = states_at(lm, [prompts[k]["dec_ids"] for k in keys])
        self.H = {k: st["h"][i] for i, k in enumerate(keys)}            # [N, D] fp32 CPU (block outputs at d)
        self.logits0 = {k: st["logits"][i] for i, k in enumerate(keys)}
        self.q = {k: cmap.probs(st["logits"][i][None])[0] for k, i in zip(keys, range(len(keys)))}
        self.cls = {k: int(self.q[k][:cmap.C].argmax()) for k in keys}
        del st
        self.Lmax = max(len(prompts[k]["dec_ids"]) - 1 for k in base_keys)
        self.kv: dict[str, tuple[list[torch.Tensor], list[torch.Tensor], int]] = {}
        for k in dict.fromkeys(base_keys):
            self.add_base(k)
        logger.info(f"DecSite: {len(keys)} prompts, {len(self.kv)} bases cached (Lmax {self.Lmax}) in "
                    f"{time.time() - t0:.0f}s")

    def add_base(self, k: str) -> None:
        if k in self.kv:
            return
        ids = self.P[k]["dec_ids"]
        pre = prefill(self.lm, ids[:-1])
        n = len(ids) - 1
        pad = self.Lmax - n
        Ks, Vs = [], []
        for K, V in pre["kv"]:
            if pad:
                z = torch.zeros(K.shape[0], K.shape[1], pad, K.shape[3], dtype=K.dtype, device=K.device)
                K = torch.cat([z, K], 2)
                V = torch.cat([z, V], 2)
            Ks.append(_pin(K))
            Vs.append(_pin(V))
        self.kv[k] = (Ks, Vs, pad)
        del pre

    def d_of(self, k: str) -> int:
        return len(self.P[k]["dec_ids"]) - 1

    def forward(self, L: int, bases: list[str], Hn: torch.Tensor) -> torch.Tensor:
        """Hn [G, Q, D] = edited output of block L at d for G bases (Q edits each). Returns fp32 logits [G, Q, V]."""
        lm = self.lm
        G, Q, D = Hn.shape
        Ls = L + 1
        if Ls >= lm.N:
            return lm.final(Hn.to(torch.bfloat16))
        Kd = {l: torch.cat([self.kv[b][0][l] for b in bases], 0).to(self.dev, non_blocking=True)
              for l in range(Ls, lm.N)}
        Vd = {l: torch.cat([self.kv[b][1][l] for b in bases], 0).to(self.dev, non_blocking=True)
              for l in range(Ls, lm.N)}
        pads = torch.tensor([self.kv[b][2] for b in bases], device=self.dev)
        Lmax = self.Lmax
        kk = torch.arange(Lmax, device=self.dev)
        mask = torch.zeros(G, 1, Q, Lmax + Q, dtype=torch.bool, device=self.dev)
        mask[:, 0, :, :Lmax] = (kk[None, :] >= pads[:, None])[:, None, :]
        ar = torch.arange(Q, device=self.dev)
        mask[:, 0, ar, Lmax + ar] = True
        pos = torch.tensor([self.d_of(b) for b in bases], device=self.dev)[:, None].expand(G, Q).contiguous()
        h = Hn.to(torch.bfloat16)
        rope = lm.rope(h, pos)
        feed = KVFeed(Kd, Vd)
        for l in range(Ls, lm.N):
            h = lm.block(l, h, pos, rope, feed=feed, mask=mask, cache_position=None)
        out = lm.final(h)
        del Kd, Vd, feed
        return out

    # -------------------------------------------------------------------------------------------- evaluation
    @torch.no_grad()
    def evaluate(self, L: int, pairs: list[tuple[str, str]], R: torch.Tensor | None | str,
                 tgt_cls: dict[tuple[str, str], int] | None = None, targets: dict[str, torch.Tensor] | None = None
                 ) -> dict[str, np.ndarray]:
        """Per pair (src, base): margin toward the source class (or tgt_cls) after the edit, its unedited value on
        the same path, class probs and KL to the source's q. R: [D, k] basis, None = full-state exchange,
        'none' = unedited."""
        out_m = np.zeros(len(pairs))
        out_m0 = np.zeros(len(pairs))
        out_q = np.zeros((len(pairs), self.cmap.C + 1))
        out_kl = np.zeros(len(pairs))
        by_b: dict[str, list[int]] = {}
        for i, (s, b) in enumerate(pairs):
            by_b.setdefault(b, []).append(i)
        items = [(b, ix[j:j + self.Q]) for b, ix in by_b.items() for j in range(0, len(ix), self.Q)]
        Rd = R.to(self.dev) if isinstance(R, torch.Tensor) else None
        for g0 in range(0, len(items), self.G):
            grp = items[g0:g0 + self.G]
            while len(grp) < self.G:
                grp = grp + [grp[-1]]
            bases = [b for b, _ in grp]
            Hn = torch.zeros(self.G, self.Q + 1, self.lm.D, device=self.dev)
            ci = torch.zeros(self.G, self.Q + 1, dtype=torch.long, device=self.dev)
            cb = torch.zeros(self.G, self.Q + 1, dtype=torch.long, device=self.dev)
            for gi, (b, ix) in enumerate(grp):
                hb = self.H[b][L].to(self.dev)
                Hn[gi, :] = hb
                for qi, i in enumerate(ix):
                    s = pairs[i][0]
                    hs = self.H[s][L].to(self.dev)
                    if isinstance(R, str):
                        hn = hb
                    elif Rd is None:
                        hn = hs
                    else:
                        hn = hb + ((hs - hb) @ Rd) @ Rd.T
                    Hn[gi, qi + 1] = hn
                    c = tgt_cls[pairs[i]] if tgt_cls is not None else self.cls[s]
                    ci[gi, qi + 1] = c
                    cb[gi, qi + 1] = self.cls[b]
                ci[gi, 0] = ci[gi, 1]
                cb[gi, 0] = cb[gi, 1]
            lg = self.forward(L, bases, Hn)
            m = self.cmap.margin(lg, ci, cb)
            q = self.cmap.probs(lg)
            seen = set()
            for gi, (b, ix) in enumerate(grp):
                if (b, tuple(ix)) in seen:
                    continue
                seen.add((b, tuple(ix)))
                for qi, i in enumerate(ix):
                    s = pairs[i][0]
                    out_m[i] = float(m[gi, qi + 1])
                    # unedited margin toward the same target class on the same path (query 0 = unedited base)
                    lp0 = self.cmap.lp(lg[gi, 0])
                    out_m0[i] = float(lp0[ci[gi, qi + 1]] - lp0[cb[gi, qi + 1]])
                    out_q[i] = q[gi, qi + 1].cpu().numpy()
                    t = (targets[s] if targets is not None else self.q[s]).to(self.dev)
                    out_kl[i] = float(kl(t, q[gi, qi + 1]))
            del lg
        return {"m": out_m, "m0": out_m0, "delta": out_m - out_m0, "q": out_q, "kl": out_kl}

    # -------------------------------------------------------------------------------------------- fitting
    def fit(self, L: int, train: list[tuple[str, str]], val: list[tuple[str, str]], seed: int,
            targets: dict[str, torch.Tensor] | None = None, pair_targets: dict[tuple[str, str], torch.Tensor] | None
            = None, steps: int = 240, lr: float = 2e-2, ranks: tuple[int, ...] = (1, 2, 4, 8),
            val_every: int = 20, patience: int = 3, log_name: str = "") -> dict[str, Any]:
        """Nested-rank DAS on pairs (src, base) with the KL objective. pair_targets overrides per-pair targets
        (label controls); targets overrides per-source targets (random-init network: trained q_src)."""
        D = self.lm.D
        kmax = max(ranks)
        g = torch.Generator().manual_seed(1000 + seed)
        W = torch.randn(D, kmax, generator=g).to(self.dev).requires_grad_(True)
        opt = torch.optim.Adam([W], lr=lr)
        rng = np.random.default_rng(seed)
        by_b: dict[str, list[tuple[str, str]]] = {}
        for p in train:
            by_b.setdefault(p[1], []).append(p)
        bkeys = sorted(by_b)

        def tgt(p: tuple[str, str]) -> torch.Tensor:
            if pair_targets is not None:
                return pair_targets[p]
            if targets is not None:
                return targets[p[0]]
            return self.q[p[0]]

        best = {"val": float("inf"), "W": W.detach().clone(), "step": 0}
        bad = 0
        hist = []
        t0 = time.time()
        step = 0
        for step in range(1, steps + 1):
            k = int(rng.choice(ranks))
            bsel = [bkeys[i] for i in rng.choice(len(bkeys), size=min(self.G, len(bkeys)), replace=False)]
            while len(bsel) < self.G:
                bsel.append(bsel[-1])
            Hb = torch.stack([self.H[b][L] for b in bsel]).to(self.dev)              # [G, D]
            Hs = torch.zeros(self.G, self.Q, D, device=self.dev)
            T = torch.zeros(self.G, self.Q, self.cmap.C + 1, device=self.dev)
            for gi, b in enumerate(bsel):
                pl = by_b[b]
                sel = rng.choice(len(pl), size=self.Q, replace=len(pl) < self.Q)
                for qi, j in enumerate(sel):
                    p = pl[int(j)]
                    Hs[gi, qi] = self.H[p[0]][L].to(self.dev)
                    T[gi, qi] = tgt(p).to(self.dev)
            R = torch.linalg.qr(W)[0][:, :k]
            Hn = Hb[:, None] + ((Hs - Hb[:, None]) @ R) @ R.T
            lg = self.forward(L, bsel, Hn)
            loss = kl(T, self.cmap.probs(lg)).mean()
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            hist.append({"step": step, "k": k, "loss": float(loss)})
            if val and (step % val_every == 0 or step == steps):
                with torch.no_grad():
                    Rf = torch.linalg.qr(W.detach())[0]
                    vk = []
                    for kk in ranks:
                        ev = self.evaluate(L, val, Rf[:, :kk], targets=targets)
                        if pair_targets is not None:
                            vk.append(float(np.mean([float(kl(pair_targets[p].to(self.dev),
                                                               torch.tensor(ev["q"][i], device=self.dev)))
                                                     for i, p in enumerate(val)])))
                        else:
                            vk.append(float(ev["kl"].mean()))
                    vl = float(np.mean(vk))
                hist[-1]["val_kl"] = vl
                hist[-1]["val_kl_by_k"] = vk
                if vl < best["val"] - 1e-5:
                    best = {"val": vl, "W": W.detach().clone(), "step": step}
                    bad = 0
                else:
                    bad += 1
                logger.info(f"[{log_name}] step {step} loss {float(loss):.4f} val KL {vl:.4f} ({time.time() - t0:.0f}s)")
                if bad >= patience:
                    logger.info(f"[{log_name}] early stop at step {step} (best {best['step']})")
                    break
        Wf = best["W"] if val else W.detach()
        R = torch.linalg.qr(Wf)[0].cpu()
        return {"R": R, "best_step": best["step"], "best_val_kl": best["val"], "steps_run": step, "hist": hist,
                "seconds": round(time.time() - t0, 1)}

    def free(self) -> None:
        self.kv.clear()
        gc.collect()
        torch.cuda.empty_cache()


# ================================================================================================ band site
class BandSite:
    """Task-band DAS (one R shared over band blocks and spec positions). Positions p1..d are recomputed from block
    band_start; source states at band blocks and spec offsets come from the sources' clean forward passes."""

    def __init__(self, lm: LM, prompts: dict[str, dict[str, Any]], cmap: ClassMap, band: tuple[int, ...],
                 base_keys: list[str], src_keys: list[str], cls: dict[str, int]):
        self.lm, self.P, self.cmap = lm, prompts, cmap
        self.band = list(band)
        self.b0 = self.band[0]
        self.dev = lm.dev
        self.cls = cls
        r0 = prompts[base_keys[0]]
        self.n_spec = r0["spec_end"] - r0["p1"]
        self.T = len(r0["dec_ids"]) - r0["p1"]
        self.pre_max = max(prompts[k]["p1"] for k in set(base_keys) | set(src_keys))
        self.base: dict[str, dict[str, Any]] = {}
        self.src: dict[str, torch.Tensor] = {}
        t0 = time.time()
        for k in dict.fromkeys(base_keys):
            self.add_base(k)
        for k in dict.fromkeys(src_keys):
            self.add_src(k)
        logger.info(f"BandSite: {len(self.base)} bases, {len(self.src)} sources, T {self.T}, spec {self.n_spec} "
                    f"({time.time() - t0:.0f}s)")

    def _capture(self, ids: list[int], p1: int, blocks: list[int]) -> tuple[dict[int, torch.Tensor], Any]:
        store: dict[int, torch.Tensor] = {}

        def mk(l: int) -> Callable:
            def g(h: torch.Tensor) -> None:
                store[l] = h[0, p1:].detach().clone()
            return g
        pre = prefill(self.lm, ids, capture={l: mk(l) for l in blocks})
        return store, pre

    def add_base(self, k: str) -> None:
        if k in self.base:
            return
        r = self.P[k]
        ids = r["dec_ids"]
        p1 = r["p1"]
        assert len(ids) - p1 == self.T, f"window length differs for {k}"
        store, pre = self._capture(ids, p1, [self.b0 - 1])
        pad = self.pre_max - p1
        Ks, Vs = {}, {}
        for l in range(self.b0, self.lm.N):
            K, V = pre["kv"][l]
            K, V = K[:, :, :p1], V[:, :, :p1]
            if pad:
                z = torch.zeros(K.shape[0], K.shape[1], pad, K.shape[3], dtype=K.dtype, device=K.device)
                K, V = torch.cat([z, K], 2), torch.cat([z, V], 2)
            Ks[l] = _pin(K)
            Vs[l] = _pin(V)
        self.base[k] = {"h_in": store[self.b0 - 1].cpu(), "K": Ks, "V": Vs, "pad": pad, "p1": p1}
        del pre

    def add_src(self, k: str) -> None:
        if k in self.src:
            return
        r = self.P[k]
        store, pre = self._capture(r["dec_ids"], r["p1"], self.band)
        self.src[k] = torch.stack([store[l][:self.n_spec] for l in self.band]).to(torch.float16).cpu()  # [nb, S, D]
        del pre

    def forward(self, pairs: list[tuple[str, str]], R: torch.Tensor | None | str, grad: bool = False) -> torch.Tensor:
        """pairs [(src, base)] -> fp32 logits at d [B, V]. R: [D, k] (interchange), None (full exchange), 'none'."""
        lm = self.lm
        B = len(pairs)
        bases = [b for _, b in pairs]
        h = torch.stack([self.base[b]["h_in"] for b in bases]).to(self.dev)              # [B, T, D] bf16
        Kd = {l: torch.cat([self.base[b]["K"][l] for b in bases], 0).to(self.dev, non_blocking=True)
              for l in range(self.b0, lm.N)}
        Vd = {l: torch.cat([self.base[b]["V"][l] for b in bases], 0).to(self.dev, non_blocking=True)
              for l in range(self.b0, lm.N)}
        pads = torch.tensor([self.base[b]["pad"] for b in bases], device=self.dev)
        Lp, T = self.pre_max, self.T
        kk = torch.arange(Lp, device=self.dev)
        mask = torch.zeros(B, 1, T, Lp + T, dtype=torch.bool, device=self.dev)
        mask[:, 0, :, :Lp] = (kk[None, :] >= pads[:, None])[:, None, :]
        mask[:, 0, :, Lp:] = torch.tril(torch.ones(T, T, dtype=torch.bool, device=self.dev))[None]
        pos = torch.stack([torch.arange(self.base[b]["p1"], self.base[b]["p1"] + T, device=self.dev)
                           for b in bases])
        rope = lm.rope(h, pos)
        feed = KVFeed(Kd, Vd)
        S = self.n_spec
        src = None
        if not isinstance(R, str):
            src = torch.stack([self.src[s] for s, _ in pairs]).to(self.dev)              # [B, nb, S, D] fp16
        Rd = R.to(self.dev) if isinstance(R, torch.Tensor) else None
        for l in range(self.b0, lm.N):
            def run(x: torch.Tensor, l: int = l) -> torch.Tensor:
                return lm.block(l, x, pos, rope, feed=feed, mask=mask, cache_position=None)
            if grad and torch.is_grad_enabled():
                h = torch.utils.checkpoint.checkpoint(run, h, use_reentrant=False)
            else:
                h = run(h)
            if l in self.band and src is not None:
                j = self.band.index(l)
                hs = h[:, :S].float()
                ss = src[:, j].float()
                if Rd is None:
                    new = ss
                else:
                    new = hs + ((ss - hs) @ Rd) @ Rd.T
                h = torch.cat([new.to(h.dtype), h[:, S:]], 1)
        # Kd/Vd/feed/src stay referenced by the checkpointed closures until backward has run
        return lm.final(h[:, -1])

    @torch.no_grad()
    def evaluate(self, pairs: list[tuple[str, str]], R: torch.Tensor | None | str, bs: int = 8,
                 tgt_cls: dict[tuple[str, str], int] | None = None, base_m0: dict[tuple[str, int, int], float] |
                 None = None) -> dict[str, np.ndarray]:
        n = len(pairs)
        m = np.zeros(n)
        q = np.zeros((n, self.cmap.C + 1))
        for i0 in range(0, n, bs):
            chunk = pairs[i0:i0 + bs]
            pad = chunk + [chunk[-1]] * (bs - len(chunk))
            lg = self.forward(pad, R)
            ci = torch.tensor([tgt_cls[p] if tgt_cls else self.cls[p[0]] for p in pad], device=self.dev)
            cb = torch.tensor([self.cls[p[1]] for p in pad], device=self.dev)
            mm = self.cmap.margin(lg, ci, cb)
            qq = self.cmap.probs(lg)
            for j in range(len(chunk)):
                m[i0 + j] = float(mm[j])
                q[i0 + j] = qq[j].cpu().numpy()
        return {"m": m, "q": q}

    def base_margins(self, pairs: list[tuple[str, str]], bs: int = 8,
                     tgt_cls: dict[tuple[str, str], int] | None = None) -> np.ndarray:
        ev = self.evaluate(pairs, "none", bs=bs, tgt_cls=tgt_cls)
        return ev["m"]

    def fit(self, train: list[tuple[str, str]], val: list[tuple[str, str]], seed: int, q_tgt: dict[str, torch.Tensor],
            steps: int = 240, lr: float = 2e-2, ranks: tuple[int, ...] = (1, 2, 4, 8), bs: int = 8,
            val_every: int = 20, patience: int = 3, pair_targets: dict[tuple[str, str], torch.Tensor] | None = None,
            log_name: str = "", deadline: float = float("inf")) -> dict[str, Any]:
        D = self.lm.D
        g = torch.Generator().manual_seed(1000 + seed)
        W = torch.randn(D, max(ranks), generator=g).to(self.dev).requires_grad_(True)
        opt = torch.optim.Adam([W], lr=lr)
        rng = np.random.default_rng(seed)
        best = {"val": float("inf"), "W": W.detach().clone(), "step": 0}
        bad = 0
        hist = []
        t0 = time.time()
        step = 0

        def tgt(p: tuple[str, str]) -> torch.Tensor:
            return (pair_targets[p] if pair_targets is not None else q_tgt[p[0]]).to(self.dev)

        for step in range(1, steps + 1):
            k = int(rng.choice(ranks))
            sel = [train[int(i)] for i in rng.choice(len(train), size=bs, replace=False)]
            R = torch.linalg.qr(W)[0][:, :k]
            with torch.enable_grad():
                lg = self.forward(sel, R, grad=True)
                T = torch.stack([tgt(p) for p in sel])
                loss = kl(T, self.cmap.probs(lg)).mean()
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            hist.append({"step": step, "k": k, "loss": float(loss)})
            if step % val_every == 0 or step == steps or time.time() > deadline:
                with torch.no_grad():
                    Rf = torch.linalg.qr(W.detach())[0]
                    vk = []
                    for kk in ranks:
                        ev = self.evaluate(val, Rf[:, :kk], bs=bs)
                        qv = torch.tensor(ev["q"], device=self.dev)
                        Tv = torch.stack([tgt(p) for p in val])
                        vk.append(float(kl(Tv, qv).mean()))
                    vl = float(np.mean(vk))
                hist[-1]["val_kl"] = vl
                hist[-1]["val_kl_by_k"] = vk
                if vl < best["val"] - 1e-5:
                    best = {"val": vl, "W": W.detach().clone(), "step": step}
                    bad = 0
                else:
                    bad += 1
                logger.info(f"[{log_name}] step {step} loss {float(loss):.4f} val KL {vl:.4f} ({time.time() - t0:.0f}s)")
                if bad >= patience or time.time() > deadline:
                    logger.info(f"[{log_name}] stop at step {step} (best {best['step']})")
                    break
        R = torch.linalg.qr(best["W"])[0].cpu()
        return {"R": R, "best_step": best["step"], "best_val_kl": best["val"], "steps_run": step, "hist": hist,
                "seconds": round(time.time() - t0, 1)}

    def free(self) -> None:
        self.base.clear()
        self.src.clear()
        gc.collect()
        torch.cuda.empty_cache()
