#!/usr/bin/env python3
"""bf16 Qwen3-8B engine for K3: loading, component hooks, cached forwards, attribution gradients, generation.

Ported from iteration 7's Gemma G1 code (art_HY7uYZz-OjRW src/gen7.py Edit/edit_hooks, src/g1.py collect/atp_grads/
margins_rows) to Qwen3-8B, with the iteration-6 float64 CRN sampler (engine5.decode_rows) reused unchanged for
generation. Edit sites:
  'z'     input of block l's o_proj (attention output before W_O); a head edit touches its 128-d slice
  'mlp'   output of block l's MLP (down_proj output)
  'resid' output of decoder block l (used only for the C2a state exchange)
  'emb'   output of the input embedding (layer ignored)
Every Edit carries ABSOLUTE positions and fn(x_fp32 [r, n_pos, d], rows) -> new values. margins_rows() measures each
edited row against an unedited base row of the same batch chunk (bf16 batch-shape offsets cancel), with the prefix
before the first edited position prefilled once and reused (suffix forward)."""

from __future__ import annotations

import contextlib
import gc
import sys
import time
from typing import Any, Callable, Iterator

import numpy as np
import torch
from loguru import logger

from k3cfg import (HEAD_DIM, I6_SRC, MODEL_ID, MODEL_REVISION, N_LAYERS, model_path)

_E5: dict[str, Any] = {}


def e5():
    """Iteration-6 engine5 (decode_rows, step_probs5) and engine_v4 (_inverse_cdf), imported unchanged."""
    if "E5" not in _E5:
        if str(I6_SRC) not in sys.path:
            sys.path.append(str(I6_SRC))
        import engine5 as E5  # noqa: E402
        import engine_v4 as E4  # noqa: E402
        _E5["E5"], _E5["E4"] = E5, E4
    return _E5["E5"], _E5["E4"]


# ================================================================================================ model
def load_model(vram_fraction: float = 0.96) -> tuple[Any, Any, dict[str, Any]]:
    from transformers import AutoModelForCausalLM, AutoTokenizer

    t0 = time.time()
    path = model_path(MODEL_ID, MODEL_REVISION)
    kw = {"revision": MODEL_REVISION} if path == MODEL_ID else {}
    tok = AutoTokenizer.from_pretrained(path, **kw)
    free0, total = torch.cuda.mem_get_info(0)
    model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, attn_implementation="sdpa",
                                                 device_map={"": 0}, low_cpu_mem_usage=True, **kw)
    model.eval()
    model.requires_grad_(False)
    _MODEL["model"] = model
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.set_per_process_memory_fraction(vram_fraction, 0)
    free, total = torch.cuda.mem_get_info(0)
    info = {"precision": "bf16", "attn_implementation": "sdpa", "cpu_embedding": False,
            "free_vram_before_GB": round(free0 / 1e9, 3), "free_vram_after_GB": round(free / 1e9, 3),
            "total_vram_GB": round(total / 1e9, 3), "gpu": torch.cuda.get_device_name(0),
            "load_seconds": round(time.time() - t0, 1), "snapshot": path.split("/")[-1]}
    logger.info(f"{MODEL_ID} loaded: {info}")
    return tok, model, info


def lm_logits(model: Any, h: torch.Tensor) -> torch.Tensor:
    return model.lm_head(h).float()


_MODEL: dict[str, Any] = {}


class Metric:
    """m = z[a] - z[b] (or z[a] - logsumexp(z[b], z[b2]) when b2 is given), read out in fp32 from the bf16 final-norm
    hidden state h [..., 4096] with the fp32-cast unembedding rows of the decision tokens. (The bf16 lm_head output is
    quantised to 0.125-0.25 nats at logit magnitudes ~20-30, too coarse for patching effects.)"""

    def __init__(self, a: int, b: int, b2: int | None = None):
        self.a, self.b, self.b2 = int(a), int(b), (int(b2) if b2 is not None else None)
        self.W = None

    def _bind(self) -> None:
        W = _MODEL["model"].lm_head.weight
        rows = [self.a, self.b] + ([self.b2] if self.b2 is not None else [])
        self.W = W[rows].float().detach().clone()

    def __call__(self, h: torch.Tensor) -> torch.Tensor:
        if self.W is None:
            self._bind()
        z = h.float() @ self.W.T
        if self.b2 is None:
            return z[..., 0] - z[..., 1]
        return z[..., 0] - torch.logsumexp(z[..., 1:3], -1)


# ================================================================================================ edits
class Edit:
    def __init__(self, site: str, layer: int, pos: list[int] | torch.Tensor,
                 fn: Callable[[torch.Tensor, torch.Tensor], torch.Tensor], head: int | None = None, name: str = ""):
        assert site in ("z", "mlp", "resid", "emb")
        self.site, self.layer, self.head, self.name = site, int(layer), head, name
        self.pos = torch.as_tensor(pos, dtype=torch.long, device="cuda")
        self.fn = fn

    def shifted(self, q: int) -> "Edit | None":
        """Positions >= q, shifted by -q (suffix forward); None if nothing remains. fn must accept the subset:
        position-dependent fns are wrapped so they receive only the kept positions' slice of their values."""
        keep = self.pos >= q
        if not bool(keep.any()):
            return None
        if bool(keep.all()):
            return Edit(self.site, self.layer, self.pos - q, self.fn, head=self.head, name=self.name)
        idx = torch.nonzero(keep).flatten()
        fn = self.fn
        n_full = len(self.pos)

        def sub(x: torch.Tensor, rows: torch.Tensor, fn=fn, idx=idx, n_full=n_full) -> torch.Tensor:
            full = torch.zeros(x.shape[0], n_full, x.shape[2], dtype=x.dtype, device=x.device)
            full[:, idx] = x
            return fn(full, rows)[:, idx]
        return Edit(self.site, self.layer, self.pos[keep] - q, sub, head=self.head, name=self.name)

    def prefix(self, q: int) -> "Edit | None":
        """Positions < q only (for the prefix prefill)."""
        keep = self.pos < q
        if not bool(keep.any()):
            return None
        if bool(keep.all()):
            return self
        idx = torch.nonzero(keep).flatten()
        fn = self.fn
        n_full = len(self.pos)

        def sub(x: torch.Tensor, rows: torch.Tensor, fn=fn, idx=idx, n_full=n_full) -> torch.Tensor:
            full = torch.zeros(x.shape[0], n_full, x.shape[2], dtype=x.dtype, device=x.device)
            full[:, idx] = x
            return fn(full, rows)[:, idx]
        return Edit(self.site, self.layer, self.pos[keep], sub, head=self.head, name=self.name)


def _module(model: Any, site: str, layer: int) -> tuple[Any, str]:
    if site == "emb":
        return model.model.embed_tokens, "out"
    blk = model.model.layers[layer]
    if site == "resid":
        return blk, "out"
    if site == "z":
        return blk.self_attn.o_proj, "pre"
    return blk.mlp, "out"


def _apply(x: torch.Tensor, items: list[tuple[Edit, torch.Tensor]]) -> torch.Tensor:
    if all(int(e.pos.max()) >= x.shape[1] for e, _ in items):
        return x
    x = x.clone()
    for e, rows in items:
        if int(e.pos.max()) >= x.shape[1]:
            continue
        sl = slice(e.head * HEAD_DIM, (e.head + 1) * HEAD_DIM) if (e.site == "z" and e.head is not None) else slice(None)
        r_ix, p_ix = rows[:, None], e.pos[None, :]
        cur = x[r_ix, p_ix][..., sl].float()
        new = e.fn(cur, rows)
        if sl != slice(None):
            x[r_ix, p_ix, sl] = new.to(x.dtype)
        else:
            x[r_ix, p_ix] = new.to(x.dtype)
    return x


@contextlib.contextmanager
def edit_hooks(model: Any, row_edits: list[tuple[Edit, torch.Tensor]],
               capture: dict[tuple[str, int], Callable[[torch.Tensor], None]] | None = None) -> Iterator[None]:
    """row_edits: [(Edit, rows LongTensor)]; capture: {(site, layer): g(x)} called with the (edited) tensor."""
    groups: dict[tuple[str, int], list[tuple[Edit, torch.Tensor]]] = {}
    for e, rows in row_edits:
        groups.setdefault((e.site, e.layer if e.site != "emb" else 0), []).append((e, rows))
    capture = capture or {}
    keys = sorted(set(groups) | set(capture))
    hs = []
    for key in keys:
        site, layer = key
        mod, kind = _module(model, site, layer)
        items = groups.get(key, [])
        cap = capture.get(key)
        if kind == "out":
            def hook(m, inp, out, items=items, cap=cap):
                x = out[0] if isinstance(out, tuple) else out
                if items:
                    x = _apply(x, items)
                if cap is not None:
                    cap(x)
                if items:
                    return (x,) + tuple(out[1:]) if isinstance(out, tuple) else x
                return None
            hs.append(mod.register_forward_hook(hook))
        else:
            def prehook(m, args, items=items, cap=cap):
                x = args[0]
                if items:
                    x = _apply(x, items)
                if cap is not None:
                    cap(x)
                if items:
                    return (x,) + tuple(args[1:])
                return None
            hs.append(mod.register_forward_pre_hook(prehook))
    try:
        yield
    finally:
        for h in hs:
            h.remove()


_GPU_KEEP = 100_000   # tensors up to this many elements stay on the GPU; larger ones are copied in at call time


def _hold(t: torch.Tensor) -> torch.Tensor:
    t = t.float()
    return t.to("cuda") if t.numel() <= _GPU_KEEP else t.to("cpu")


def const_fn(val: torch.Tensor) -> Callable:
    v = _hold(val)
    return lambda x, r, v=v: v.to(x.device, non_blocking=False)[None].expand(x.shape[0], -1, -1).clone()


def steer_fn(delta: torch.Tensor) -> Callable:
    d = _hold(delta)
    return lambda x, r, d=d: x + d.to(x.device)[None]


def all_rows(B: int, edits: list[Edit]) -> list[tuple[Edit, torch.Tensor]]:
    rows = torch.arange(B, device="cuda")
    return [(e, rows) for e in edits]


# ================================================================================================ cache helpers
def kv_from_cache(cache: Any) -> list[tuple[torch.Tensor, torch.Tensor]]:
    if hasattr(cache, "layers"):
        return [(L.keys, L.values) for L in cache.layers]
    return list(zip(cache.key_cache, cache.value_cache))


def build_cache(kv: list[tuple[torch.Tensor, torch.Tensor]], B: int):
    from transformers.cache_utils import DynamicCache

    cache = DynamicCache()
    for l, (K, V) in enumerate(kv):
        cache.update(K.expand(B, -1, -1, -1).contiguous(), V.expand(B, -1, -1, -1).contiguous(), l)
    return cache


@torch.no_grad()
def prefill(model: Any, ids: list[int], edits: list[Edit] | None = None,
            capture: dict | None = None) -> dict[str, Any]:
    """Batch-1 forward with a KV cache: {'kv' [(K, V)] batch 1, 'r_logits' fp32 [V], 'P'}."""
    from transformers.cache_utils import DynamicCache

    inp = torch.tensor([ids], device="cuda")
    cache = DynamicCache()
    with edit_hooks(model, all_rows(1, edits or []), capture):
        out = model.model(input_ids=inp, past_key_values=cache, use_cache=True)
    r_logits = lm_logits(model, out.last_hidden_state[:, -1])[0]
    kv = [(K.clone(), V.clone()) for K, V in kv_from_cache(cache)]
    del cache, out
    return {"kv": kv, "r_logits": r_logits, "P": len(ids)}


# ================================================================================================ activations
class Acts:
    """Per prompt: z [36, n, 4096] and mlp [36, n, 4096] (bf16, CPU), embedding output [n, 4096], metric m and the
    fp32 logits at the decision position (top-5 ids kept)."""

    def __init__(self, z: torch.Tensor, mlp: torch.Tensor, emb: torch.Tensor, m: float, top: list[tuple[int, float]],
                 p_a: float, p_b: float):
        self.z, self.mlp, self.emb, self.m, self.top, self.p_a, self.p_b = z, mlp, emb, m, top, p_a, p_b


@torch.no_grad()
def collect(model: Any, ids: list[int], metric: Metric, base_edits: list[Edit] | None = None) -> Acts:
    zs: dict[int, torch.Tensor] = {}
    ms: dict[int, torch.Tensor] = {}
    em: dict[int, torch.Tensor] = {}
    cap: dict[tuple[str, int], Callable] = {("emb", 0): lambda x: em.__setitem__(0, x[0].to(torch.bfloat16).cpu())}
    for l in range(N_LAYERS):
        cap[("z", l)] = (lambda x, l=l: zs.__setitem__(l, x[0].to(torch.bfloat16).cpu()))
        cap[("mlp", l)] = (lambda x, l=l: ms.__setitem__(l, x[0].to(torch.bfloat16).cpu()))
    with edit_hooks(model, all_rows(1, base_edits or []), cap):
        out = model.model(input_ids=torch.tensor([ids], device="cuda"), use_cache=False)
    hl = out.last_hidden_state[0, -1]
    m = float(metric(hl))
    lg = lm_logits(model, hl)
    pr = torch.softmax(lg, -1)
    tv, ti = pr.topk(5)
    top = [(int(i), float(v)) for i, v in zip(ti.tolist(), tv.tolist())]
    acts = Acts(torch.stack([zs[l] for l in range(N_LAYERS)]), torch.stack([ms[l] for l in range(N_LAYERS)]), em[0], m,
                top, float(pr[metric.a]), float(pr[metric.b]))
    del out
    return acts


def atp_grads(model: Any, ids: list[int], metric: Metric,
              base_edits: list[Edit] | None = None) -> tuple[torch.Tensor, torch.Tensor, float]:
    """Gradients of m w.r.t. every z and MLP output (total derivatives; the embedding output is made to require grad).
    Returns gz, gm as bf16 CPU [36, n, 4096] and m."""
    keep: dict[tuple[str, int], torch.Tensor] = {}
    hs = []
    emb = model.model.embed_tokens

    def emb_hook(m, inp, out):
        return out.detach().requires_grad_(True)
    hs.append(emb.register_forward_hook(emb_hook))
    for l in range(N_LAYERS):
        blk = model.model.layers[l]

        def pre(m, args, l=l):
            args[0].retain_grad()
            keep[("z", l)] = args[0]
        hs.append(blk.self_attn.o_proj.register_forward_pre_hook(pre))

        def post(m, inp, out, l=l):
            out.retain_grad()
            keep[("mlp", l)] = out
        hs.append(blk.mlp.register_forward_hook(post))
    try:
        with torch.enable_grad(), edit_hooks(model, all_rows(1, base_edits or [])):
            out = model.model(input_ids=torch.tensor([ids], device="cuda"), use_cache=False)
            mm = metric(out.last_hidden_state[0, -1])
            mm.backward()
    finally:
        for h in hs:
            h.remove()
    gz = torch.stack([keep[("z", l)].grad[0].to(torch.bfloat16).cpu() for l in range(N_LAYERS)])
    gm = torch.stack([keep[("mlp", l)].grad[0].to(torch.bfloat16).cpu() for l in range(N_LAYERS)])
    m = float(mm.detach())
    del keep, out, mm
    torch.cuda.empty_cache()
    return gz, gm, m


# ================================================================================================ batched margins
def rows_per_chunk(q_min: int, s: int, max_rows: int = 40, budget: float = 1.8e9) -> int:
    per = q_min * 147_456 + s * 150_000
    return max(1, min(max_rows, int(budget // max(per, 1))))


class PrefixCache:
    """Prefix KV (batch 1) keyed by (prompt key, q_min); one prompt at a time."""

    def __init__(self) -> None:
        self.d: dict[tuple, list[tuple[torch.Tensor, torch.Tensor]]] = {}

    def get(self, model: Any, ids: list[int], q: int, key: Any, base_edits: list[Edit]) -> list:
        k = (key, q)
        if k not in self.d:
            pre_edits = [e2 for e2 in (e.prefix(q) for e in base_edits) if e2 is not None]
            self.d[k] = prefill(model, ids[:q], pre_edits)["kv"]
        return self.d[k]

    def clear(self) -> None:
        self.d.clear()
        torch.cuda.empty_cache()


@torch.no_grad()
def margins_rows(model: Any, ids: list[int], metric: Metric, edits_per_row: list[list[Edit]], q_min: int = 0,
                 base_edits: list[Edit] | None = None, relative: bool = True, pcache: PrefixCache | None = None,
                 pkey: Any = None, max_rows: int = 40) -> list[float]:
    """Per row (the prompt repeated, each row with its own edits): dm = m(row) - m(unedited base row of the same chunk)
    (relative=False returns raw m). Edit positions are ABSOLUTE and >= q_min; base_edits apply to every row."""
    base_edits = base_edits or []
    n = len(ids)
    s = n - q_min
    out: list[float] = []
    kv = None
    if q_min > 0:
        if pcache is not None:
            kv = pcache.get(model, ids, q_min, pkey, base_edits)
        else:
            pre_edits = [e2 for e2 in (e.prefix(q_min) for e in base_edits) if e2 is not None]
            kv = prefill(model, ids[:q_min], pre_edits)["kv"]
    base_suffix = [e2 for e2 in (e.shifted(q_min) for e in base_edits) if e2 is not None]
    R = rows_per_chunk(q_min, s, max_rows) - 1
    R = max(R, 1)
    for b0 in range(0, len(edits_per_row), R):
        chunk = [[]] + list(edits_per_row[b0:b0 + R])
        B = len(chunk)
        row_edits = [(e, torch.arange(B, device="cuda")) for e in base_suffix]
        for i, eds in enumerate(chunk):
            for e in eds:
                e2 = e.shifted(q_min) if q_min > 0 else e
                if e2 is None:
                    raise ValueError(f"edit {e.name} has positions below q_min {q_min}")
                row_edits.append((e2, torch.tensor([i], device="cuda")))
        cache = build_cache(kv, B) if kv is not None else None
        inp = torch.tensor([ids[q_min:]], device="cuda").expand(B, -1).contiguous()
        pos = torch.arange(q_min, n, device="cuda")[None].expand(B, -1)
        with edit_hooks(model, row_edits):
            o = model.model(input_ids=inp, past_key_values=cache, position_ids=pos, use_cache=cache is not None)
        mm = metric(o.last_hidden_state[:, -1])
        out += (mm[1:] - mm[0]).tolist() if relative else mm[1:].tolist()
        del o, cache
    return out


@torch.no_grad()
def teacher_force_logits(model: Any, ids: list[int], start: int, edits: list[Edit] | None = None) -> torch.Tensor:
    """fp32 logits at positions start-1 .. len(ids)-1 (row j predicts ids[start + j])."""
    with edit_hooks(model, all_rows(1, edits or [])):
        out = model.model(input_ids=torch.tensor([ids], device="cuda"), use_cache=False)
    lg = lm_logits(model, out.last_hidden_state[0, start - 1:])
    del out
    return lg


# ================================================================================================ generation
@torch.no_grad()
def generate(model: Any, tok: Any, items: list[dict[str, Any]], max_new: int,
             fence: str = "bench") -> list[dict[str, Any]]:
    """items: {'ids' (prompt + prefilled prefix), 'edits' [Edit] (prefill only), 'u' (uniforms already offset by the
    prefix length), 'pre_key'}. One prefill per distinct pre_key; engine5.decode_rows (float64 CRN inverse-CDF
    sampler, T 1, top-p 1, no top-k) decodes the batch."""
    E5, _ = e5()
    pres: dict[Any, dict] = {}
    rows = []
    for it in items:
        k = it["pre_key"]
        if k not in pres:
            pres[k] = prefill(model, it["ids"], it.get("edits") or [])
        rows.append({"pre": pres[k], "u": it["u"], "T": 1.0, "top_k": 0, "top_p": 1.0, "max_new": max_new,
                     "fence": True})
    res = E5.decode_rows(model, rows, tok, fence_kind=fence)
    del pres, rows
    torch.cuda.empty_cache()
    return res


def sample_token(logits: torch.Tensor, u: float) -> int:
    """The engine5 transform for one row at T 1, top-p 1, no top-k: softmax in float64 then inverse CDF over the full
    vocabulary in token-id order."""
    E5, E4 = e5()
    lg = logits.double()[None]
    T = torch.ones(1, 1, dtype=torch.float64, device=lg.device)
    k = torch.zeros(1, dtype=torch.long, device=lg.device)
    p = torch.ones(1, dtype=torch.float64, device=lg.device)
    probs = E5.step_probs5(lg, T, k, p, False, False)
    return int(E4._inverse_cdf(probs, torch.tensor([u], dtype=torch.float64, device=lg.device))[0])


def free_cuda() -> None:
    gc.collect()
    torch.cuda.empty_cache()


def numpy_seed_choice(seed: int, n: int, k: int, replace: bool = False) -> np.ndarray:
    return np.random.default_rng(seed).choice(n, size=k, replace=replace)
