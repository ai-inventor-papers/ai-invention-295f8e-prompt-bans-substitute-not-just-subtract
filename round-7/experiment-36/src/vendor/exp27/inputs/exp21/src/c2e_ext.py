#!/usr/bin/env python3
"""EXPLORATORY C2e extension (not part of the frozen locus rule).

The frozen C2e window (generated tokens 1-8 and 16) ends before the class-divergent text on these programs (T2:
median first divergence from the default-class prefix tree = 29 tokens). Here the same decoder pipeline (PCA-64,
batched IRLS, inner-CV C, 5 folds by template x class, within-template permutation null with a layer-max statistic)
is run at later generated positions k in {24, 32, 48, 64, 96}, blocks 8-28 (every 2nd block), against the text
controls Ta (position one-hots 1..k) and Td (bag of tokens 1..k), each reduced to PCA-64 (the state decoder's capacity),
and Tc (exact prefix match), all with template one-hot,
and R. Samples shorter than k are excluded at that k. Question: does the state rise BEFORE the text does?"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

import numpy as np
import torch
from loguru import logger
from sklearn.model_selection import StratifiedKFold

from analysis.c2e import (DEV, DT, ba_t, decode, fold_features, inner_masks, onehot_tokens, raw_features, tc_prefix_ba,
                          template_onehot, within_template_perms)
import states_io
from cfg import DATA_DIR, DEFAULT, IM_END, STATES_DIR, read_jsonl, write_json

K_EXT = [24, 32, 48, 64, 96]
BLOCKS_EXT = list(range(8, 29, 2))
TASKS_EXT = ["T2", "T04", "T1"]


def extract(model: Any, prompts: dict, tasks: list[str] = TASKS_EXT) -> None:
    from engine import forward_capture

    labs = {r["key"]: r["label"] for r in read_jsonl(DATA_DIR / "labels.jsonl")}
    raw = read_jsonl(DATA_DIR / "samples_raw.jsonl")
    for t in tasks:
        if states_io.exists(STATES_DIR / f"X_{t}_BAN"):
            continue
        rows = [r for r in raw if r["task"] == t and r["arm"] in ("BAN", "BAN_TOPUP")]
        rows.sort(key=lambda r: (r["template"], r["arm"], int(r["sample_id"])))
        out, idx = [], []
        for w in sorted({r["template"] for r in rows}):
            rw = [r for r in rows if r["template"] == w]
            pr = prompts[(t, w, "ban")]
            P = pr["P"]
            for a in range(0, len(rw), 1):  # batch 1: states depend only on the prefix (FP8 tiling, see README)
                part = rw[a:a + 1]
                ids = [pr["ids"] + (r["token_ids"][:96] + [IM_END] * (96 - min(96, len(r["token_ids"])))) for r in part]
                fc = forward_capture(model, ids, BLOCKS_EXT, [P + k - 1 for k in K_EXT])
                x = torch.stack([fc["states"][l] for l in BLOCKS_EXT], dim=2)  # [B, 5, 11, D]
                out.append(x.numpy().astype(np.float16))
                for r in part:
                    key = f"{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}"
                    idx.append({"key": key, "template": w, "label": labs.get(key), "n_gen": len(r["token_ids"]),
                                "tok": [int(v) for v in r["token_ids"][:96]]})
        states_io.save(STATES_DIR / f"X_{t}_BAN", np.concatenate(out))
        with open(STATES_DIR / f"X_{t}_BAN_index.jsonl", "w") as fh:
            for r in idx:
                fh.write(json.dumps(r) + "\n")
        logger.info(f"C2e-X states {t}: {len(idx)} rows")


def bag_tokens(toks: list[list[int]], k: int) -> np.ndarray:
    vocab: dict[int, int] = {}
    for t in toks:
        for v in t[:k]:
            vocab.setdefault(v, len(vocab))
    A = np.zeros((len(toks), len(vocab)), np.float32)
    for i, t in enumerate(toks):
        for v in t[:k]:
            A[i, vocab[v]] += 1.0
    return np.log1p(A)


def run(task: str, n_perm: int = 200, seed: int = 0) -> dict[str, Any]:
    X = states_io.load(STATES_DIR / f"X_{task}_BAN")
    idx = [json.loads(l) for l in open(STATES_DIR / f"X_{task}_BAN_index.jsonl")]
    res: dict[str, Any] = {"task": task, "positions": {}, "label": "exploratory C2e extension (not the frozen rule)"}
    for ki, k in enumerate(K_EXT):
        keep = np.array([r["label"] not in (None, "invalid", "disputed") and r["n_gen"] >= k for r in idx])
        y = np.array([int(r["label"] == DEFAULT[task]) for r, m in zip(idx, keep) if m])
        g = np.array([r["template"] for r, m in zip(idx, keep) if m])
        toks = [r["tok"] for r, m in zip(idx, keep) if m]
        if (y == 1).sum() < 8 or (y == 0).sum() < 8:
            res["positions"][k] = {"status": "not testable", "n1": int((y == 1).sum()), "n0": int((y == 0).sum())}
            continue
        strata = np.array([f"{w}|{c}" for w, c in zip(g, y)])
        st = strata if min(Counter(strata).values()) >= 5 else y
        outer = []
        for tr, _ in StratifiedKFold(5, shuffle=True, random_state=seed).split(np.zeros(len(y)), st):
            m = np.zeros(len(y), bool)
            m[tr] = True
            outer.append(m)
        inner = [inner_masks(y, strata, m, seed + 1 + i) for i, m in enumerate(outer)]
        perms = within_template_perms(y, g, n_perm, seed + 100)
        Yb = torch.as_tensor(np.concatenate([y[None], perms]), device=DEV, dtype=DT)
        Xk = torch.as_tensor(np.ascontiguousarray(np.asarray(X[keep][:, ki]).transpose(1, 0, 2)), device=DEV, dtype=DT)
        Z = fold_features(Xk, outer)
        P = decode(Z, Yb, outer, inner)
        ba = ba_t(Yb[None].expand_as(P), P)
        obs = ba[:, 0].cpu().numpy()
        lmax = ba[:, 1:].max(0).values.cpu().numpy()
        oh = template_onehot(g)
        Y1 = Yb[:1]
        ctrl = {}
        for name, A in (("Ta", onehot_tokens(toks, k)), ("Td", bag_tokens(toks, k))):
            # PCA-64 of the token features (matched capacity with the state decoder) + template one-hot
            Zt = fold_features(torch.as_tensor(A, device=DEV, dtype=DT)[None], outer, extra=oh)
            ctrl[name] = float(ba_t(Y1[None].expand(1, 1, -1), decode(Zt, Y1, outer, inner))[0, 0])
        ctrl["Tc"] = tc_prefix_ba(toks, y, g, k)
        Zr = raw_features(np.zeros((len(y), 0), np.float32), oh)[None, None].expand(1, len(outer), -1, -1).contiguous()
        ctrl["template_only"] = float(ba_t(Y1[None].expand(1, 1, -1), decode(Zr, Y1, outer, inner))[0, 0])
        best_text = max(ctrl.values())
        res["positions"][k] = {"n": int(len(y)), "n_default": int(y.sum()),
                               "state_ba_by_block": {int(b): float(v) for b, v in zip(BLOCKS_EXT, obs)},
                               "state_max_ba": float(obs.max()), "argmax_block": int(BLOCKS_EXT[int(obs.argmax())]),
                               "null_layer_max_q95": float(np.quantile(lmax, 0.95)), "text": ctrl,
                               "state_minus_best_text": float(obs.max() - best_text),
                               "state_beats_text_by_0.10_and_null": bool(obs.max() >= best_text + 0.10 and
                                                                         obs.max() > np.quantile(lmax, 0.95))}
        logger.info(f"C2e-X {task} k{k}: state {obs.max():.3f} (null q95 {np.quantile(lmax, 0.95):.3f}) text {ctrl}")
        del Xk, Z, P
        torch.cuda.empty_cache()
    return res


def run_all_ext() -> dict[str, Any]:
    out = {t: run(t) for t in TASKS_EXT if states_io.exists(STATES_DIR / f"X_{t}_BAN")}
    write_json(STATES_DIR.parent / "results" / "c2e_extension.json", out)
    return out
