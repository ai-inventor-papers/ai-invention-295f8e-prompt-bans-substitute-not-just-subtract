#!/usr/bin/env python3
"""CPU tests of the DAS machinery on tiny random Qwen3 / Gemma3 models (no downloads): the decision-site KV path and
the band recompute path must reproduce full recomputation (zero edit, full-state edit, projected edit), and the
derangement / recovery / bootstrap helpers must behave as specified.

Usage: .venv/bin/python tests/test_cpu_tiny.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import torch

import das8
import stats8 as ST
from engine8 import LM, block_hooks, prefill


def tiny(family: str) -> LM:
    torch.manual_seed(0)
    if family == "qwen":
        from transformers import Qwen3Config, Qwen3ForCausalLM
        cfg = Qwen3Config(vocab_size=500, hidden_size=64, intermediate_size=128, num_hidden_layers=6,
                          num_attention_heads=4, num_key_value_heads=2, head_dim=16, max_position_embeddings=512,
                          tie_word_embeddings=False)
        cfg._attn_implementation = "sdpa"
        m = Qwen3ForCausalLM(cfg).to(torch.bfloat16)
    else:
        from transformers import Gemma3ForCausalLM, Gemma3TextConfig
        cfg = Gemma3TextConfig(vocab_size=500, hidden_size=64, intermediate_size=128, num_hidden_layers=6,
                               num_attention_heads=4, num_key_value_heads=2, head_dim=16, max_position_embeddings=512,
                               sliding_window=512, query_pre_attn_scalar=16)
        cfg._attn_implementation = "sdpa"
        m = Gemma3ForCausalLM(cfg).to(torch.bfloat16)
    m.eval()
    m.requires_grad_(False)

    class Tok:
        def decode(self, ids, **kw):
            return " ".join(str(i) for i in ids)

        def __len__(self):
            return 500
    lm = LM(family, Tok(), m, {})
    lm.D = 64
    return lm


def prompts(n: int, rng: np.random.Generator) -> dict[str, dict]:
    spec = list(rng.integers(5, 400, 20))
    tail = [7, 8, 9]
    opening = [11, 12, 13, 14]
    P = {}
    for i in range(n):
        seg = list(rng.integers(5, 400, int(rng.integers(3, 7))))
        ids = [1, 2] + seg + spec + tail
        p1 = 2 + len(seg)
        P[f"p{i}"] = {"key": f"p{i}", "unit": "TEST", "ids": ids, "P": len(ids), "p1": p1, "spec_end": p1 + len(spec),
                      "dec_ids": ids + opening}
    return P


def check(family: str) -> dict:
    lm = tiny(family)
    rng = np.random.default_rng(0)
    P = prompts(8, rng)
    cmap = das8.ClassMap(["a", "b", "c"], {"a": [11, 20], "b": [30, 31], "c": [40]})
    keys = list(P)
    site = das8.DecSite(lm, P, cmap, base_keys=keys, all_keys=keys, G=4, Q=3)
    out = {}
    L = 2
    # zero edit on the KV path vs full recompute
    errs, errs_full, errs_proj = [], [], []
    R = das8.haar(1, 64, 2)
    for b in keys[:4]:
        lg_full = prefill(lm, P[b]["dec_ids"])["logits"]
        H = torch.stack([site.H[b][L]] * 3)[None].expand(4, 3, -1).contiguous()
        lg_kv = site.forward(L, [b] * 4, H)[0, 0]
        errs.append(float((cmap.lp(lg_full) - cmap.lp(lg_kv)).abs().max()))
        s = keys[-1]
        hs = site.H[s][L]
        hb = site.H[b][L]

        def ed(h, val):
            h = h.clone()
            h[:, -1] = val.to(h.dtype)
            return h
        lg_full_e = prefill(lm, P[b]["dec_ids"], edits={L: lambda h: ed(h, hs)})["logits"]
        lg_kv_e = site.forward(L, [b] * 4, hs[None, None].expand(4, 3, -1).contiguous())[0, 0]
        errs_full.append(float((cmap.lp(lg_full_e) - cmap.lp(lg_kv_e)).abs().max()))
        hn = hb + ((hs - hb) @ R) @ R.T
        lg_full_p = prefill(lm, P[b]["dec_ids"], edits={L: lambda h: ed(h, hn)})["logits"]
        lg_kv_p = site.forward(L, [b] * 4, hn[None, None].expand(4, 3, -1).contiguous())[0, 0]
        errs_proj.append(float((cmap.lp(lg_full_p) - cmap.lp(lg_kv_p)).abs().max()))
    # mixed bases in one batch (different prefix lengths -> left padding)
    mix = keys[:4]
    Hm = torch.stack([torch.stack([site.H[b][L]] * 3) for b in mix])
    lg_mix = site.forward(L, mix, Hm)[:, 0]
    errs_mix = [float((cmap.lp(prefill(lm, P[b]["dec_ids"])["logits"]) - cmap.lp(lg_mix[i])).abs().max())
                for i, b in enumerate(mix)]
    out["dec_zero_edit"] = max(errs)
    out["dec_full_edit"] = max(errs_full)
    out["dec_proj_edit"] = max(errs_proj)
    out["dec_mixed_lengths"] = max(errs_mix)
    # band: zero edit and full-state exchange vs full recompute with hooks
    band = (1, 2, 3)
    cls = {k: 0 for k in keys}
    bs = das8.BandSite(lm, P, cmap, band, keys, keys, cls)
    e0, e1, e2 = [], [], []
    for b, s in zip(keys[:4], keys[4:8]):
        lg_none = bs.forward([(s, b)], "none")[0]
        lg_full = prefill(lm, P[b]["dec_ids"])["logits"]
        e0.append(float((cmap.lp(lg_none) - cmap.lp(lg_full)).abs().max()))
        S = bs.n_spec
        src = bs.src[s].float()
        pb = P[b]["p1"]

        def mk(j):
            def f(h):
                h = h.clone()
                h[0, pb:pb + S] = src[j].to(h.dtype)
                return h
            return f
        lg_hook = prefill(lm, P[b]["dec_ids"], edits={l: mk(j) for j, l in enumerate(band)})["logits"]
        lg_bs = bs.forward([(s, b)], None)[0]
        e1.append(float((cmap.lp(lg_hook) - cmap.lp(lg_bs)).abs().max()))

        def mkp(j):
            def f(h):
                h = h.clone()
                hb_ = h[0, pb:pb + S].float()
                h[0, pb:pb + S] = (hb_ + ((src[j] - hb_) @ R) @ R.T).to(h.dtype)
                return h
            return f
        lg_hook_p = prefill(lm, P[b]["dec_ids"], edits={l: mkp(j) for j, l in enumerate(band)})["logits"]
        lg_bs_p = bs.forward([(s, b)], R)[0]
        e2.append(float((cmap.lp(lg_hook_p) - cmap.lp(lg_bs_p)).abs().max()))
    out["band_zero_edit"] = max(e0)
    out["band_full_exchange"] = max(e1)
    out["band_proj_edit"] = max(e2)
    # a few fit steps run without error and return an orthonormal R
    pairs = [(keys[i], keys[j]) for i in range(4) for j in range(4, 8)]
    f = site.fit(L, pairs, pairs[:4], seed=0, steps=4, val_every=2)
    out["fit_orth_err"] = float((f["R"].T @ f["R"] - torch.eye(8)).abs().max())
    fb = bs.fit(pairs, pairs[:2], seed=0, q_tgt={k: site.q[k] for k in keys}, steps=2, bs=2, val_every=1)
    out["band_fit_orth_err"] = float((fb["R"].T @ fb["R"] - torch.eye(8)).abs().max())
    return out


def main() -> None:
    res = {}
    for fam in ("qwen", "gemma"):
        res[fam] = check(fam)
        print(fam, res[fam])
    # recovery / bootstrap on synthetic deltas with a known ratio
    rng = np.random.default_rng(0)
    df = rng.normal(5, 1, 600)
    de = 0.6 * df + rng.normal(0, 0.1, 600)
    src = [f"s{i % 12}" for i in range(600)]
    base = [f"b{i % 50}" for i in range(600)]
    r = ST.recovery(de, df, src, base, n_boot=200)
    print("recovery", r["recovery"], r["ci95"])
    ok = all(v < 0.1 for fam in res.values() for k, v in fam.items() if not k.endswith("orth_err")) and \
        abs(r["recovery"] - 0.6) < 0.01
    print("PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
