#!/usr/bin/env python3
"""K3 circuit stages (GPU): attribution screen, exact noising/denoising, path patching among the top 15, faithfulness
curves, write norms and matched random pools, validation rows in the real model. Ported from iteration 7's Gemma G1
(art_HY7uYZz-OjRW src/g1.py: collect, atp_grads, node_vals, make_edit, margins_rows, edge_patching, selection,
class_mean, validation_stats) with Qwen3-8B dimensions, four position classes COND/SPEC/OPEN/DEC and the plan's sign
convention (every effect positive when it carries the clean-minus-corrupt metric difference)."""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import torch
from loguru import logger

import k3engine as EN
from k3cfg import CLASSES, HEAD_DIM, N_HEADS, N_LAYERS

NPL = N_HEADS + 1                      # nodes per layer per class (32 heads + 1 MLP)
NN = len(CLASSES) * N_LAYERS * NPL     # 4,752


# ================================================================================================ nodes
def all_nodes() -> list[tuple[str, int, int, str]]:
    out = []
    for c in CLASSES:
        for l in range(N_LAYERS):
            for h in range(N_HEADS):
                out.append(("head", l, h, c))
            out.append(("mlp", l, -1, c))
    return out


NODES = all_nodes()


def node_key(n: tuple) -> str:
    return f"{n[0]}|L{n[1]}|H{n[2]}|{n[3]}"


KEY2IDX = {node_key(n): i for i, n in enumerate(NODES)}


def parse_key(k: str) -> tuple[str, int, int, str]:
    kind, l, h, c = k.split("|")
    return kind, int(l[1:]), int(h[1:]), c


def node_vals(a: EN.Acts, node: tuple, pos: list[int]) -> torch.Tensor:
    kind, l, h, _ = node
    if kind == "head":
        return a.z[l, pos, h * HEAD_DIM:(h + 1) * HEAD_DIM]
    return a.mlp[l, pos]


def make_edit(node: tuple, pos: list[int], fn) -> EN.Edit:
    kind, l, h, _ = node
    if kind == "head":
        return EN.Edit("z", l, pos, fn, head=h, name=node_key(node))
    return EN.Edit("mlp", l, pos, fn, name=node_key(node))


# ================================================================================================ contrasts
class Contrast:
    """prompts: records from k3prompts (+ 'opening' ids appended at run time); pairs: (clean idx, corrupt idx);
    base: {prompt idx: callable -> list[Edit]} for intervention-defined runs (C2a exchange)."""

    def __init__(self, name: str, metric: EN.Metric, prompts: list[dict[str, Any]], opening: list[int],
                 pairs: list[tuple[int, int]], base: dict[int, Any] | None = None):
        self.name, self.metric, self.prompts, self.opening, self.pairs = name, metric, prompts, opening, pairs
        self._base = base or {}
        self._base_cache: dict[int, list[EN.Edit]] = {}
        for c, x in pairs:
            assert prompts[c]["P"] == prompts[x]["P"], "pair lengths differ"
            assert prompts[c]["pos"] == prompts[x]["pos"], "pair position classes differ"

    def run_ids(self, i: int) -> list[int]:
        return self.prompts[i]["ids"] + self.opening

    def base(self, i: int) -> list[EN.Edit]:
        if i not in self._base:
            return []
        if i not in self._base_cache:
            self._base_cache[i] = self._base[i]()
        return self._base_cache[i]

    def clear_base(self) -> None:
        self._base_cache.clear()


def collect_all(model: Any, C: Contrast, idx: list[int]) -> dict[int, EN.Acts]:
    out = {}
    for i in idx:
        out[i] = EN.collect(model, C.run_ids(i), C.metric, C.base(i))
    return out


# ================================================================================================ AtP
def atp_vector(gz: torch.Tensor, gm: torch.Tensor, a_src: EN.Acts, a_run: EN.Acts,
               pos: dict[str, list[int]]) -> np.ndarray:
    """sum over class positions of grad . (a_src - a_run), per node, in NODES order."""
    out = torch.zeros(len(CLASSES), N_LAYERS, NPL, dtype=torch.float64)
    n = gz.shape[1]
    pidx = {c: torch.tensor(pos[c], dtype=torch.long, device="cuda") for c in CLASSES}
    for l in range(N_LAYERS):
        g = gz[l].cuda().float()
        d = a_src.z[l].cuda().float() - a_run.z[l].cuda().float()
        prod = (g * d).view(n, N_HEADS, HEAD_DIM).sum(-1)
        gmm = (gm[l].cuda().float() * (a_src.mlp[l].cuda().float() - a_run.mlp[l].cuda().float())).sum(-1)
        for ci, c in enumerate(CLASSES):
            if len(pos[c]) == 0:
                continue
            out[ci, l, :N_HEADS] = prod[pidx[c]].sum(0).double().cpu()
            out[ci, l, N_HEADS] = float(gmm[pidx[c]].sum())
        del g, d, prod, gmm
    return out.flatten().numpy()


def atp_screen(model: Any, C: Contrast, acts: dict[int, EN.Acts], pairs: list[tuple[int, int]]
               ) -> tuple[np.ndarray, np.ndarray]:
    """Noising AtP (grad at the clean run; estimate of m_clean - m_noised) and denoising AtP (grad at the corrupt run;
    estimate of m_denoised - m_corrupt) for every node and pair."""
    noise = np.zeros((len(pairs), NN))
    den = np.zeros((len(pairs), NN))
    for pi, (c, x) in enumerate(pairs):
        gz, gm, _ = EN.atp_grads(model, C.run_ids(c), C.metric, C.base(c))
        noise[pi] = -atp_vector(gz, gm, acts[x], acts[c], C.prompts[c]["pos"])
        del gz, gm
        gz, gm, _ = EN.atp_grads(model, C.run_ids(x), C.metric, C.base(x))
        den[pi] = atp_vector(gz, gm, acts[c], acts[x], C.prompts[x]["pos"])
        del gz, gm
        EN.free_cuda()
    return noise, den


def ig_atp_screen(model: Any, C: Contrast, acts: dict[int, EN.Acts], pairs: list[tuple[int, int]], interp,
                  alphas: tuple[float, ...] = (0.1, 0.3, 0.5, 0.7, 0.9)) -> np.ndarray:
    """EAP-IG-style noising screen: gradients of m averaged over runs whose INPUT difference is interpolated
    (interp(c, x, alpha) -> edits: the embedding at the differing positions for input contrasts, the exchanged states
    for C2a), times (corrupt - clean) node activations. Every activation stays live, so the gradients are total
    derivatives."""
    out = np.zeros((len(pairs), NN))
    for pi, (c, x) in enumerate(pairs):
        acc = None
        for a in alphas:
            gz, gm, _ = EN.atp_grads(model, C.run_ids(c), C.metric, interp(c, x, a))
            v = -atp_vector(gz, gm, acts[x], acts[c], C.prompts[c]["pos"])
            acc = v if acc is None else acc + v
            del gz, gm
            EN.free_cuda()
        out[pi] = acc / len(alphas)
    return out


# ================================================================================================ exact patching
def exact_effects(model: Any, C: Contrast, acts: dict[int, EN.Acts], pairs: list[tuple[int, int]],
                  node_ids: list[int], direction: str = "noise") -> np.ndarray:
    """noise: clean run, node <- corrupt values, effect = m_clean - m_noised; denoise: corrupt run, node <- clean
    values, effect = m_denoised - m_corrupt. [n_pairs, len(node_ids)]."""
    store = np.zeros((len(pairs), len(node_ids)))
    for pi, (c, x) in enumerate(pairs):
        run_i, src_i = (c, x) if direction == "noise" else (x, c)
        ids = C.run_ids(run_i)
        pos = C.prompts[run_i]["pos"]
        by_q: dict[int, list[tuple[int, list[EN.Edit]]]] = {}
        for jj, j in enumerate(node_ids):
            nd = NODES[j]
            ps = pos[nd[3]]
            if not ps:
                continue
            e = make_edit(nd, ps, EN.const_fn(node_vals(acts[src_i], nd, ps)))
            by_q.setdefault(min(ps), []).append((jj, [e]))
        pc = EN.PrefixCache()
        for q, items in sorted(by_q.items()):
            ms = EN.margins_rows(model, ids, C.metric, [it[1] for it in items], q_min=q, base_edits=C.base(run_i),
                                 pcache=pc, pkey=run_i)
            for (jj, _), mv in zip(items, ms):
                store[pi, jj] = -mv if direction == "noise" else mv
        pc.clear()
    return store


# ================================================================================================ path patching
@torch.no_grad()
def edge_patching(model: Any, C: Contrast, acts: dict[int, EN.Acts], pairs: list[tuple[int, int]],
                  senders: list[int]) -> list[dict[str, Any]]:
    """Path patching among the top nodes: pass 2 (clean run; sender <- corrupt at its class positions; every other
    head z and MLP output at every position frozen to clean; each receiver's computed value recorded) and pass 3 (clean
    run with only the receiver <- recorded value); edge effect = m_clean - m_pass3; sender -> logits effect =
    m(frozen, no sender) - m(frozen, sender)."""

    def order_key(nd: tuple) -> tuple[int, int]:
        return (nd[1], 0 if nd[0] == "head" else 1)

    acc: dict[tuple[int, int], list[float]] = {}
    acc_logit: dict[int, list[float]] = {}
    for c, x in pairs:
        ids = C.run_ids(c)
        n = len(ids)
        pos = C.prompts[c]["pos"]
        Zc, Mc = acts[c].z.cuda(), acts[c].mlp.cuda()
        Zx, Mx = acts[x].z.cuda(), acts[x].mlp.cuda()
        snd = [None] + [NODES[j] for j in senders]
        S = len(snd)
        cap: dict[int, torch.Tensor] = {}
        recv_by: dict[tuple[str, int], list[int]] = {}
        for j in senders:
            nd = NODES[j]
            recv_by.setdefault(("z" if nd[0] == "head" else "mlp", nd[1]), []).append(j)
        hooks = []
        for l in range(N_LAYERS):
            blk = model.model.layers[l]

            def zpre(m, args, l=l):
                xv = args[0]
                for j in recv_by.get(("z", l), []):
                    nd = NODES[j]
                    ps = torch.tensor(pos[nd[3]], device="cuda")
                    cap[j] = xv[:, ps, nd[2] * HEAD_DIM:(nd[2] + 1) * HEAD_DIM].detach().clone()
                new = Zc[l][None].expand(xv.shape[0], -1, -1).clone().to(xv.dtype)
                for r, nd in enumerate(snd):
                    if nd is not None and nd[0] == "head" and nd[1] == l:
                        ps = torch.tensor(pos[nd[3]], device="cuda")
                        sl = slice(nd[2] * HEAD_DIM, (nd[2] + 1) * HEAD_DIM)
                        new[r, ps, sl] = Zx[l][ps, sl].to(xv.dtype)
                return (new,) + tuple(args[1:])

            def mpost(m, inp, out, l=l):
                for j in recv_by.get(("mlp", l), []):
                    nd = NODES[j]
                    ps = torch.tensor(pos[nd[3]], device="cuda")
                    cap[j] = out[:, ps].detach().clone()
                new = Mc[l][None].expand(out.shape[0], -1, -1).clone().to(out.dtype)
                for r, nd in enumerate(snd):
                    if nd is not None and nd[0] == "mlp" and nd[1] == l:
                        ps = torch.tensor(pos[nd[3]], device="cuda")
                        new[r, ps] = Mx[l][ps].to(out.dtype)
                return new
            hooks.append(blk.self_attn.o_proj.register_forward_pre_hook(zpre))
            hooks.append(blk.mlp.register_forward_hook(mpost))
        try:
            with EN.edit_hooks(model, EN.all_rows(S, C.base(c))):
                inp = torch.tensor([ids], device="cuda").expand(S, -1).contiguous()
                o = model.model(input_ids=inp, use_cache=False)
                m2 = C.metric(o.last_hidden_state[:, -1]).tolist()
                del o
        finally:
            for h in hooks:
                h.remove()
        for r, j in enumerate(senders):
            acc_logit.setdefault(j, []).append(m2[0] - m2[r + 1])
        items = []
        for r, js in enumerate(senders):
            s_nd = NODES[js]
            s_min = min(pos[s_nd[3]])
            for jr in senders:
                if jr == js:
                    continue
                r_nd = NODES[jr]
                if order_key(r_nd) <= order_key(s_nd):
                    continue
                ps = pos[r_nd[3]]
                if not ps or max(ps) < s_min:          # causally impossible (receiver positions before the sender's)
                    continue
                val = cap[jr][r + 1]
                items.append(((js, jr), min(ps), make_edit(r_nd, ps, EN.const_fn(val))))
        by_q: dict[int, list] = {}
        for key, q, e in items:
            by_q.setdefault(q, []).append((key, e))
        pc = EN.PrefixCache()
        for q, its in sorted(by_q.items()):
            ms = EN.margins_rows(model, ids, C.metric, [[e] for _, e in its], q_min=q, base_edits=C.base(c),
                                 pcache=pc, pkey=c)
            for (key, _), mv in zip(its, ms):
                acc.setdefault(key, []).append(-mv)
        pc.clear()
        del Zc, Mc, Zx, Mx, cap
        EN.free_cuda()
    out = []
    for (js, jr), v in acc.items():
        out.append({"sender": node_key(NODES[js]), "receiver": node_key(NODES[jr]), "effect_mean": float(np.mean(v)),
                    "effect_sd": float(np.std(v)), "n_pairs": len(v), "per_pair": [float(a) for a in v]})
    for js, v in acc_logit.items():
        out.append({"sender": node_key(NODES[js]), "receiver": "logits(m)", "effect_mean": float(np.mean(v)),
                    "effect_sd": float(np.std(v)), "n_pairs": len(v), "per_pair": [float(a) for a in v]})
    return sorted(out, key=lambda e: -abs(e["effect_mean"]))


@torch.no_grad()
def head_attention(model: Any, tok: Any, C: Contrast, i: int, heads: list[tuple[int, int]], q_pos: int,
                   top: int = 10) -> dict[str, Any]:
    """Attention weights of the given heads at the query position q_pos (eager attention recomputed from the cached
    q/k of a hooked forward): top source tokens with decoded text and position class."""
    ids = C.run_ids(i)
    pos = C.prompts[i]["pos"]
    cls_of = {}
    for c in ("COND", "SPEC", "OPEN", "DEC"):
        for p in pos[c]:
            cls_of[p] = c
    layers = sorted({l for l, _ in heads})
    store: dict[int, dict[str, torch.Tensor]] = {}
    hs = []
    for l in layers:
        attn = model.model.layers[l].self_attn

        def qk_hook(m, args, kwargs, l=l):
            store[l] = {"h": kwargs.get("hidden_states", args[0] if args else None).detach(),
                        "pe": kwargs.get("position_embeddings")}
        hs.append(attn.register_forward_pre_hook(qk_hook, with_kwargs=True))
    try:
        with EN.edit_hooks(model, EN.all_rows(1, C.base(i))):
            model.model(input_ids=torch.tensor([ids], device="cuda"), use_cache=False)
    finally:
        for h in hs:
            h.remove()
    from transformers.models.qwen3.modeling_qwen3 import apply_rotary_pos_emb
    out = {}
    for l in layers:
        attn = model.model.layers[l].self_attn
        h = store[l]["h"]
        cos, sin = store[l]["pe"]
        hd = attn.head_dim
        q = attn.q_norm(attn.q_proj(h).view(1, -1, attn.config.num_attention_heads, hd)).transpose(1, 2)
        k = attn.k_norm(attn.k_proj(h).view(1, -1, attn.config.num_key_value_heads, hd)).transpose(1, 2)
        q, k = apply_rotary_pos_emb(q, k, cos, sin)
        rep = attn.config.num_attention_heads // attn.config.num_key_value_heads
        for (ll, hh) in heads:
            if ll != l:
                continue
            kk = k[0, hh // rep, :q_pos + 1].float()
            qq = q[0, hh, q_pos].float()
            w = torch.softmax((kk @ qq) * attn.scaling, -1)
            tv, ti = w.topk(min(top, len(w)))
            out[f"head|L{l}|H{hh}"] = [{"pos": int(p), "w": float(v), "tok": tok.decode([ids[int(p)]]),
                                        "class": cls_of.get(int(p), "?")} for v, p in zip(tv.tolist(), ti.tolist())]
    return out


# ================================================================================================ faithfulness
@torch.no_grad()
def frozen_rows(model: Any, ids: list[int], metric: EN.Metric, Zsrc: torch.Tensor, Msrc: torch.Tensor,
                live_sets: list[list[int] | None], pos: dict[str, list[int]]) -> list[float]:
    """Rows of the clean input in which every head z and MLP output is frozen to (Zsrc, Msrc) except the nodes in the
    row's live set, which are computed normally. live_sets[r] None = unedited row. Returns raw m per row."""
    B = len(live_sets)
    by_layer: list[dict[int, list[tuple[str, int, list[int]]]]] = []
    for ls in live_sets:
        d: dict[int, list[tuple[str, int, list[int]]]] = {}
        for j in (ls or []):
            nd = NODES[j]
            d.setdefault(nd[1], []).append((nd[0], nd[2], pos[nd[3]]))
        by_layer.append(d)
    frozen_rows_mask = torch.tensor([ls is not None for ls in live_sets], device="cuda")
    hooks = []
    for l in range(N_LAYERS):
        blk = model.model.layers[l]

        def zpre(m, args, l=l):
            xv = args[0]
            new = Zsrc[l][None].expand(B, -1, -1).clone().to(xv.dtype)
            for r in range(B):
                if live_sets[r] is None:
                    new[r] = xv[r]
                    continue
                for kind, h, ps in by_layer[r].get(l, []):
                    if kind == "head":
                        sl = slice(h * HEAD_DIM, (h + 1) * HEAD_DIM)
                        new[r, ps, sl] = xv[r, ps, sl]
            return (new,) + tuple(args[1:])

        def mpost(m, inp, out, l=l):
            new = Msrc[l][None].expand(B, -1, -1).clone().to(out.dtype)
            for r in range(B):
                if live_sets[r] is None:
                    new[r] = out[r]
                    continue
                for kind, h, ps in by_layer[r].get(l, []):
                    if kind == "mlp":
                        new[r, ps] = out[r, ps]
            return new
        hooks.append(blk.self_attn.o_proj.register_forward_pre_hook(zpre))
        hooks.append(blk.mlp.register_forward_hook(mpost))
    try:
        inp = torch.tensor([ids], device="cuda").expand(B, -1).contiguous()
        o = model.model(input_ids=inp, use_cache=False)
        mm = metric(o.last_hidden_state[:, -1]).tolist()
        del o
    finally:
        for h in hooks:
            h.remove()
    _ = frozen_rows_mask
    return mm


# ================================================================================================ write norms / pools
@torch.no_grad()
def write_norms(model: Any, acts: dict[int, EN.Acts], pairs: list[tuple[int, int]],
                pos_of: dict[int, dict[str, list[int]]]) -> np.ndarray:
    """Per node: mean over pairs of the mean over its class positions of ||delta write|| (head: W_O^h (z_x - z_c);
    MLP: mlp_x - mlp_c)."""
    W = np.zeros((len(pairs), NN))
    for pi, (c, x) in enumerate(pairs):
        pos = pos_of[c]
        out = torch.zeros(len(CLASSES), N_LAYERS, NPL, dtype=torch.float64)
        for l in range(N_LAYERS):
            dz = (acts[x].z[l].cuda().float() - acts[c].z[l].cuda().float())
            n = dz.shape[0]
            Wo = model.model.layers[l].self_attn.o_proj.weight.float().view(-1, N_HEADS, HEAD_DIM)
            wr = torch.einsum("nhd,ohd->nho", dz.view(n, N_HEADS, HEAD_DIM), Wo).norm(dim=-1)
            dm = (acts[x].mlp[l].cuda().float() - acts[c].mlp[l].cuda().float()).norm(dim=-1)
            for ci, cl in enumerate(CLASSES):
                ps = pos[cl]
                if not ps:
                    continue
                pt = torch.tensor(ps, device="cuda")
                out[ci, l, :N_HEADS] = wr[pt].mean(0).double().cpu()
                out[ci, l, N_HEADS] = float(dm[pt].mean())
            del dz, Wo, wr, dm
        W[pi] = out.flatten().numpy()
    EN.free_cuda()
    return W.mean(0)


def select_random(top10: list[int], wn: np.ndarray, seed: int, n_rand: int = 50) -> dict[str, Any]:
    """Matched random components per top node: same type and position class, top-10 excluded. Heads: smallest
    tolerance on +-10% / +-25% / +-50% with >= 50 candidates, 50 drawn without replacement (else the nearest 50).
    MLPs: smallest tolerance on +-10% / +-25% / +-50% / nearest-10 with >= 10 distinct candidates, 50 draws with
    replacement, each draw's patch delta rescaled to the target's write norm."""
    rng = np.random.default_rng(seed)
    tops = set(top10)
    rand_sets: dict[str, list[str]] = {}
    factors: dict[str, list[float]] = {}
    matching: dict[str, Any] = {}
    for j in top10:
        nd = NODES[j]
        k = node_key(nd)
        pool = [i for i in range(NN) if NODES[i][0] == nd[0] and NODES[i][3] == nd[3] and i not in tops]
        w0 = wn[j]
        need = n_rand if nd[0] == "head" else 10
        tol, cand = None, []
        for t in (0.10, 0.25, 0.50):
            cand = [i for i in pool if abs(wn[i] - w0) <= t * max(w0, 1e-12)]
            if len(cand) >= need:
                tol = t
                break
        if tol is None:
            cand = sorted(pool, key=lambda i: abs(wn[i] - w0))[:need]
            tol = f"nearest-{need}"
        if nd[0] == "head":
            pick = rng.choice(len(cand), size=min(n_rand, len(cand)), replace=False)
            draws = [cand[i] for i in pick]
            fac = [1.0] * len(draws)
        else:
            pick = rng.choice(len(cand), size=n_rand, replace=True)
            draws = [cand[i] for i in pick]
            fac = [float(w0 / wn[d]) if wn[d] > 0 else 1.0 for d in draws]
        rand_sets[k] = [node_key(NODES[d]) for d in draws]
        factors[k] = fac
        matching[k] = {"tolerance": tol, "n_candidates": len(cand), "n_distinct_drawn": len(set(draws)),
                       "write_norm": float(w0), "draw_write_norm_mean": float(np.mean([wn[d] for d in draws])),
                       "rescale_factor_mean": float(np.mean(fac)), "rescale_factor_range": [float(min(fac)),
                                                                                           float(max(fac))]}
    return {"rand_sets": rand_sets, "factors": factors, "matching": matching}


# ================================================================================================ class means
class MeanCache:
    """Class means of node activations at aligned positions (SPEC/OPEN/DEC aligned across templates by construction;
    COND only over prompts of the reference prompt's template)."""

    def __init__(self, acts: dict[int, EN.Acts], prompts: list[dict[str, Any]]):
        self.acts, self.prompts, self.c = acts, prompts, {}

    def get(self, idx: list[int], node: tuple, ref: dict[str, Any]) -> torch.Tensor | None:
        cl = node[3]
        key = (node_key(node), tuple(idx), ref["template"] if cl == "COND" else None)
        if key not in self.c:
            vals = []
            for i in idx:
                p = self.prompts[i]
                if cl == "COND" and p["template"] != ref["template"]:
                    continue
                ps = p["pos"][cl]
                if len(ps) != len(ref["pos"][cl]):
                    continue
                vals.append(node_vals(self.acts[i], node, ps).float())
            self.c[key] = torch.stack(vals).mean(0) if vals else None       # CPU; edits copy to the GPU
        return self.c[key]

    def clear(self) -> None:
        self.c.clear()


def val_edit(node: tuple, ref: dict[str, Any], mc: MeanCache, opp: list[int], own: list[int], mode: str,
             factor: float = 1.0, dose: float = 2.0) -> EN.Edit | None:
    """ABLATE: node <- opposite-class mean (with factor f: x + f (mo - x)); STEER: node <- own + dose x (opposite-class
    mean - own-class mean) (x f)."""
    ps = ref["pos"][node[3]]
    if not ps:
        return None
    mo = mc.get(opp, node, ref)
    if mo is None:
        return None
    if mode == "ablate":
        if factor == 1.0:
            return make_edit(node, ps, EN.const_fn(mo))
        mo_h = EN._hold(mo)
        return make_edit(node, ps, lambda x, r, mo=mo_h, f=factor: x + f * (mo.to(x.device)[None] - x))
    mw = mc.get(own, node, ref)
    if mw is None:
        return None
    return make_edit(node, ps, EN.steer_fn(dose * factor * (mo - mw)))
