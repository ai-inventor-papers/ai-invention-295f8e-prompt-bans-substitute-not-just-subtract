#!/usr/bin/env python3
"""Teacher-forced machinery of iteration 7: packed scoring of target programs, the layer profile, site caches, the
DAS map class, fits (main / permuted-label / read-position / random-init network) and held-out TF evaluation.

PACKING. One base prompt is followed by n target programs (the first <= 48 response tokens of the model's own
programs). ids = prompt + concat(programs); position ids restart at P for every program; a boolean 4-D mask lets
prompt token i see prompt tokens <= i and program j token t see every prompt token plus program j's tokens <= t.
Program token 0 is read from packed index P-1, token t from the program's previous token. ll(program) = sum of its
token log-probabilities (fp32 log-softmax). Contrast C = LME_{Pi_Y} ll - LME_{Pi_D} ll (log-mean-exp).
CACHE. For a site whose first edited block is s0, the packed sequence's block-(s0-1) output is cached once per (base,
target group); an edit-time forward runs blocks s0..35 + final norm + lm_head on the scored rows only. Program-token
states below s0 do not depend on an edit at s0 (prefill-only edits), so the cached forward is exact.
MAP CLASS. DASMap: Linear(4096 -> 16, no bias) under torch.nn.utils.parametrizations.orthogonal (rows orthonormal),
fp32, seeded init; R_k = the first k rows (nested). Edit: h_b[pos] <- h_b[pos] + (h_s[pos] - h_b[pos]) R_k^T R_k.
"""

from __future__ import annotations

import math
import time
from typing import Any, Callable

import numpy as np
import torch
from loguru import logger

D_MODEL = 4096
N_LAYERS = 36


# ------------------------------------------------------------------------------------------------ packing
def pack(prompt_ids: list[int], programs: list[list[int]], dev: torch.device) -> dict[str, Any]:
    P = len(prompt_ids)
    ids = list(prompt_ids)
    pos = list(range(P))
    seg = [-1] * P
    sc_idx, tgt, prog_of = [], [], []
    for j, prog in enumerate(programs):
        off = len(ids)
        ids += list(prog)
        pos += list(range(P, P + len(prog)))
        seg += [j] * len(prog)
        for t in range(len(prog)):
            sc_idx.append(P - 1 if t == 0 else off + t - 1)
            tgt.append(int(prog[t]))
            prog_of.append(j)
    L = len(ids)
    seg_t = torch.tensor(seg)
    ar = torch.arange(L)
    causal = ar[None, :] <= ar[:, None]
    attend = causal & ((seg_t[None, :] == -1) | (seg_t[None, :] == seg_t[:, None]))
    return {"ids": torch.tensor([ids], device=dev), "pos": torch.tensor([pos], device=dev),
            "mask": attend[None, None].to(dev), "sc_idx": torch.tensor(sc_idx, device=dev),
            "tgt": torch.tensor(tgt, device=dev), "prog_of": torch.tensor(prog_of, device=dev), "n_prog": len(programs),
            "P": P, "L": L}


def run_blocks(model: Any, h: torch.Tensor, pk: dict[str, Any], start: int, end: int,
               edit_fn: Callable[[int, torch.Tensor], torch.Tensor] | None = None,
               capture: dict[int, Any] | None = None, ckpt: bool = False) -> torch.Tensor:
    """Run decoder blocks start..end-1 on h [b, L, D] with the packed mask/positions; edit_fn(l, h) after block l."""
    b = h.shape[0]
    pos = pk["pos"].expand(b, -1)
    pe = model.model.rotary_emb(h, pos)
    mask = pk["mask"]
    for l in range(start, end):
        layer = model.model.layers[l]
        if ckpt and h.requires_grad:
            h = torch.utils.checkpoint.checkpoint(
                lambda x, layer=layer: layer(x, attention_mask=mask, position_ids=pos, position_embeddings=pe,
                                             use_cache=False), h, use_reentrant=False)
        else:
            h = layer(h, attention_mask=mask, position_ids=pos, position_embeddings=pe, use_cache=False)
        if isinstance(h, tuple):
            h = h[0]
        if edit_fn is not None:
            h = edit_fn(l, h)
        if capture is not None and l in capture:
            capture[l] = h.detach()
    return h


def score_ll(model: Any, h: torch.Tensor, pk: dict[str, Any], chunk: int = 96) -> torch.Tensor:
    """Per-program summed log-likelihood [b, n_prog] (fp32) from the last-block output h [b, L, D]."""
    hs = model.model.norm(h[:, pk["sc_idx"]])
    b, M, _ = hs.shape
    ll = torch.zeros(b, pk["n_prog"], device=h.device, dtype=torch.float32)
    for c in range(0, M, chunk):
        lg = model.lm_head(hs[:, c:c + chunk]).float()
        t = pk["tgt"][c:c + chunk]
        lp = lg.gather(-1, t[None, :, None].expand(b, -1, 1))[..., 0] - torch.logsumexp(lg, dim=-1)
        ll = ll.index_add(1, pk["prog_of"][c:c + chunk], lp)
    return ll


def lme(x: torch.Tensor) -> torch.Tensor:
    return torch.logsumexp(x, dim=-1) - math.log(x.shape[-1])


# ------------------------------------------------------------------------------------------------ map class
class DASMap(torch.nn.Module):
    def __init__(self, k: int = 16, seed: int = 0, d: int = D_MODEL):
        super().__init__()
        g = torch.Generator().manual_seed(int(seed))
        q, _ = torch.linalg.qr(torch.randn(d, k, generator=g, dtype=torch.float64))
        lin = torch.nn.Linear(d, k, bias=False)
        with torch.no_grad():
            lin.weight.copy_(q.T.float())
        self.lin = torch.nn.utils.parametrizations.orthogonal(lin)

    def basis(self) -> torch.Tensor:
        return self.lin.weight  # [k, d], orthonormal rows


def random_basis(seed: int, k: int = 16, d: int = D_MODEL) -> torch.Tensor:
    g = torch.Generator().manual_seed(int(seed))
    q, _ = torch.linalg.qr(torch.randn(d, k, generator=g, dtype=torch.float64))
    return q.T.float().contiguous()


def orthonormal_rows(B: torch.Tensor) -> torch.Tensor:
    q, _ = torch.linalg.qr(B.double().T)
    return q.T.float().contiguous()


# ------------------------------------------------------------------------------------------------ edits
def proj_edit(h: torch.Tensor, row: int, pos: torch.Tensor, src: torch.Tensor, B: torch.Tensor | None,
              lam: float = 1.0) -> torch.Tensor:
    """Out-of-place edit of batch row `row` at positions pos: full exchange (B None) or projected interchange."""
    hs = h[row, pos].float()
    if B is None:
        new = src.float()
    else:
        new = hs + lam * (((src.float() - hs) @ B.T) @ B)
    h = h.clone()
    h[row, pos] = new.to(h.dtype)
    return h


class Site:
    """Edit site: blocks (one block L* or a band) and position kind ('spec' or 'R')."""

    def __init__(self, blocks: list[int], pos_kind: str = "spec"):
        self.blocks = list(blocks)
        self.pos_kind = pos_kind
        self.start = min(self.blocks)

    def name(self) -> str:
        b = f"L{self.blocks[0]}" if len(self.blocks) == 1 else f"band{self.blocks[0]}-{self.blocks[-1]}"
        return b + ("" if self.pos_kind == "spec" else "_R")

    def positions(self, rec: dict[str, Any], dev: torch.device) -> torch.Tensor:
        if self.pos_kind == "spec":
            return torch.arange(rec["p1"], rec["spec_end"], device=dev)
        return torch.tensor([rec["P"] - 1], device=dev)

    def src_rows(self, src_states: dict[int, torch.Tensor], l: int) -> torch.Tensor:
        s = src_states[l]
        return s[:-1] if self.pos_kind == "spec" else s[-1:]


# ------------------------------------------------------------------------------------------------ task context
class TFContext:
    """Per task: target programs, packed caches per (base, group) at a site, source states, and scoring."""

    def __init__(self, model: Any, prompts: dict[str, dict[str, Any]], targets: dict[str, list[list[int]]],
                 site: Site, groups: dict[str, list[str]], default: str):
        self.model = model
        self.dev = model.lm_head.weight.device
        self.P = prompts
        self.targets = targets          # alg -> list of token-id lists (exact generated ids, <= 48 tokens)
        self.site = site
        self.groups = groups            # group name -> list of algorithms (union)
        self.default = default
        self.cache: dict[tuple[str, str], dict[str, Any]] = {}
        self.src: dict[str, dict[int, torch.Tensor]] = {}

    def programs(self, group: str) -> tuple[list[list[int]], int]:
        ys = [p for a in self.groups[group] for p in self.targets[a]]
        return ys + list(self.targets[self.default]), len(ys)

    @torch.no_grad()
    def base_cache(self, base_key: str, group: str) -> dict[str, Any]:
        k = (base_key, group)
        if k not in self.cache:
            rec = self.P[base_key]
            progs, nY = self.programs(group)
            pk = pack(rec["ids"], progs, self.dev)
            h = self.model.model.embed_tokens(pk["ids"])
            if self.site.start > 0:
                h = run_blocks(self.model, h, pk, 0, self.site.start)
            pk["h_in"] = h.detach()
            pk["nY"] = nY
            pk["pos_edit"] = self.site.positions(rec, self.dev)
            self.cache[k] = pk
        return self.cache[k]

    @torch.no_grad()
    def source_states(self, key: str) -> dict[int, torch.Tensor]:
        if key not in self.src:
            from gpu7 import capture_states
            self.src[key] = capture_states(self.model, self.P[key], self.site.blocks)
        return self.src[key]

    def contrast_rows(self, base_key: str, group: str, rows: list[dict[str, Any]], grad: bool = False
                      ) -> dict[str, torch.Tensor]:
        """rows: [{'src': source key or None, 'B': basis [k, D] or None (full exchange), 'lam': 1.0, 'none': bool}].
        Returns C, lmeY, lmeD per row (fp32 tensors [b])."""
        pk = self.base_cache(base_key, group)
        b = len(rows)
        h = pk["h_in"].expand(b, -1, -1)
        pos = pk["pos_edit"]
        srcs = [None if r.get("none") else self.source_states(r["src"]) for r in rows]
        site = self.site

        def edit_fn(l: int, hh: torch.Tensor) -> torch.Tensor:
            if l not in site.blocks:
                return hh
            for i, r in enumerate(rows):
                if srcs[i] is None:
                    continue
                hh = proj_edit(hh, i, pos, site.src_rows(srcs[i], l), r.get("B"), r.get("lam", 1.0))
            return hh
        ctx = torch.enable_grad() if grad else torch.no_grad()
        with ctx:
            hout = run_blocks(self.model, h, pk, site.start, N_LAYERS, edit_fn, ckpt=False)
            ll = score_ll(self.model, hout, pk)
        nY = pk["nY"]
        lY, lD = lme(ll[:, :nY]), lme(ll[:, nY:])
        return {"C": lY - lD, "lmeY": lY, "lmeD": lD}

    def free(self) -> None:
        self.cache.clear()
        self.src.clear()
        torch.cuda.empty_cache()


# ------------------------------------------------------------------------------------------------ fitting
def fit_das(ctx: TFContext, train_pairs: list[tuple[str, str, str]], val_pairs: list[tuple[str, str, str]],
            seed: int, ctx_val: TFContext | None = None, n_steps: int = 150, extend: int = 0, lr: float = 2e-3,
            mb: int = 4, val_every: int = 25, patience: int = 3, ranks: tuple[int, ...] = (1, 2, 4, 8, 16),
            log_name: str = "", objective: str = "C") -> dict[str, Any]:
    """Rank-cycled nested training on all-pairs (source, base, group). Validation (ctx_val: disjoint validation
    target programs) on TRAIN sources -> VAL bases at every rank, the unedited row in the same batch. If the best
    state is the last one at n_steps, training continues for `extend` more steps (equal-budget rule)."""
    cv = ctx_val or ctx
    das = DASMap(16, seed).to(ctx.dev)
    opt = torch.optim.Adam(das.parameters(), lr=lr)
    rng = np.random.default_rng(seed)
    by_src: dict[str, list[tuple[str, str, str]]] = {}
    for p in train_pairs:
        by_src.setdefault(p[0], []).append(p)
    src_keys = sorted(by_src)
    cyc = [16, 8, 4, 2, 1]
    m = 0
    curve, vals = [], []
    best = {"val": -1e9, "basis": das.basis().detach().clone(), "step": 0}
    bad = 0
    budget = n_steps
    t0 = time.time()
    order: list[str] = []
    step = 0
    while step < budget:
        step += 1
        opt.zero_grad(set_to_none=True)
        tot = 0.0
        for _ in range(mb):
            if not order:
                order = list(rng.permutation(src_keys))
            s = order.pop()
            pl = by_src[s]
            s_, b_, g = pl[int(rng.integers(len(pl)))]
            k = cyc[m % 5]
            m += 1
            Bk = das.basis()[:k]
            out = ctx.contrast_rows(b_, g, [{"src": s_, "B": Bk}], grad=True)
            loss = -out[objective][0] / mb
            loss.backward()
            tot += float(out[objective][0])
        opt.step()
        curve.append({"step": step, "train_C": tot / mb, "sec": round(time.time() - t0, 1)})
        if step % val_every == 0 or step == budget:
            v = eval_val(cv, das.basis().detach(), val_pairs, ranks, objective)
            vals.append({"step": step, **v})
            logger.info(f"[{log_name}] step {step}: train C {tot / mb:.3f}; val gain {v['mean_gain']:.3f} "
                        f"(by k {v['gain_by_k']}) {time.time() - t0:.0f}s")
            if v["mean_gain"] > best["val"] + 1e-4:
                best = {"val": v["mean_gain"], "basis": das.basis().detach().clone(), "step": step}
                bad = 0
            else:
                bad += 1
                if bad >= patience:
                    logger.info(f"[{log_name}] early stop at step {step}")
                    break
            if step == budget and extend and best["step"] == step and budget == n_steps:
                budget = n_steps + extend
                logger.info(f"[{log_name}] still improving at {step}: +{extend} steps (equal-budget rule)")
    W = best["basis"]
    orth = float((W @ W.T - torch.eye(W.shape[0], device=W.device)).abs().max())
    return {"basis": W.cpu(), "best_step": best["step"], "best_val": best["val"], "curve": curve, "val": vals,
            "steps_run": step, "budget": budget, "extended": budget > n_steps, "orth_err": orth,
            "seconds": round(time.time() - t0, 1)}


@torch.no_grad()
def eval_val(ctx: TFContext, W: torch.Tensor, val_pairs: list[tuple[str, str, str]],
             ranks: tuple[int, ...], objective: str = "C") -> dict[str, Any]:
    gains = {k: [] for k in ranks}
    for (s, b_, g) in val_pairs:
        rows = [{"none": True}] + [{"src": s, "B": W[:k]} for k in ranks]
        C = ctx.contrast_rows(b_, g, rows)[objective]
        for i, k in enumerate(ranks):
            gains[k].append(float(C[i + 1] - C[0]))
    gk = {k: float(np.mean(v)) for k, v in gains.items()}
    return {"gain_by_k": {k: round(v, 3) for k, v in gk.items()}, "mean_gain": float(np.mean(list(gk.values())))}
