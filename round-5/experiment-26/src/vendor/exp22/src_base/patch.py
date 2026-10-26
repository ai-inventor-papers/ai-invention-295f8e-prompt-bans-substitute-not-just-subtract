#!/usr/bin/env python3
"""9.2 conditional causal patch (runs only if C2e finds a locus (k*, L*) on a task).

30 within-template pairs (compliant source, non-compliant target) and 30 reversed. For each pair, three continuations
from the TARGET's prefix 1..k*, uniforms u_stream(task, w, k_target, 'patch'): (i) the block-L* output at generated
position k* replaced by the source's state; (ii) replaced by the state of a random run of the TARGET's class
(control); (iii) no patch. The three rows of a pair share a batch (exact CRN coupling); batches have 20 rows
(6 pairs x 3 + 2 filler rows). Flip rate = P(source class | i) - P(source class | ii), exact McNemar over pairs."""

from __future__ import annotations

import json
import random
from typing import Any

import numpy as np
import torch
from loguru import logger

import states_io
from cfg import DATA_DIR, DEFAULT, RESULTS_DIR, STATES_DIR, append_jsonl, read_jsonl, write_json
from engine import prefill, sample, u_stream

PATCH_RAW = DATA_DIR / "patch_raw.jsonl"


def _state(X: np.ndarray, i: int, pos_idx: int, bi: int) -> np.ndarray:
    return np.asarray(X[i, pos_idx, bi]).astype(np.float32)


def run_patch(model: Any, tok: Any, prompts: dict, task: str, k_star: int, block: int, n_pairs: int = 30,
              seed: int = 0) -> dict[str, Any]:
    labs = {r["key"]: r["label"] for r in read_jsonl(DATA_DIR / "labels.jsonl")}
    tags = [f"{task}_BAN"] + ([f"{task}_BAN_TOPUP"] if task == "T1" else [])
    Xs, idx = [], []
    for tg in tags:
        if states_io.exists(STATES_DIR / tg):
            Xs.append(states_io.load(STATES_DIR / tg))
            idx += [json.loads(l) for l in open(STATES_DIR / f"{tg}_index.jsonl")]
    X = np.concatenate([np.asarray(x) for x in Xs])
    blocks = json.load(open(STATES_DIR / f"{tags[0]}_meta.json"))["blocks"]
    bi = blocks.index(block)
    pos_idx = 1 + k_star  # positions: Smean, R, k1..k8, k16
    cls = []
    for r in idx:
        l = labs.get(r["key"])
        cls.append(None if l in (None, "invalid", "disputed") else int(l == DEFAULT[task]))
    rng = random.Random(seed)
    jobs = []
    for direction in ("compliant_to_default", "default_to_compliant"):
        src_c, tgt_c = (0, 1) if direction == "compliant_to_default" else (1, 0)
        cand = []
        for w in sorted({r["template"] for r in idx}):
            S = [i for i, r in enumerate(idx) if r["template"] == w and cls[i] == src_c and r["n_gen"] >= k_star]
            T = [i for i, r in enumerate(idx) if r["template"] == w and cls[i] == tgt_c and r["n_gen"] >= k_star]
            for t_ in T:
                if S:
                    cand.append((rng.choice(S), t_, w))
        rng.shuffle(cand)
        for s_, t_, w in cand[:n_pairs]:
            same = [i for i, r in enumerate(idx) if r["template"] == w and cls[i] == tgt_c and i != t_]
            jobs.append({"dir": direction, "src": s_, "tgt": t_, "ctrl": rng.choice(same) if same else t_, "w": w})
    rows_out = []
    by_w: dict[str, list[dict]] = {}
    for j in jobs:
        by_w.setdefault(j["w"], []).append(j)
    for w, js in by_w.items():
        pr = prompts[(task, w, "ban")]
        for a in range(0, len(js), 6):
            part = js[a:a + 6]
            groups, meta = [], []
            for j in part:
                t_ = j["tgt"]
                ids = pr["ids"] + idx[t_]["tok16"][:k_star]
                pos = len(ids) - 1  # generated position k* of the target
                u = u_stream(task, w, idx[t_]["sample_id"], "patch")
                for cond, srcrow in (("patched", j["src"]), ("control", j["ctrl"]), ("none", None)):
                    edits = None
                    if srcrow is not None:
                        vec = torch.tensor(_state(X, srcrow, pos_idx, bi), device=model.device)

                        def f(h, vec=vec, pos=pos):
                            h = h.clone()
                            h[:, pos] = vec.to(h.dtype)
                            return h
                        edits = {block: f}
                    pre = prefill(model, ids, edits=edits)
                    groups.append({"pre": pre, "us": [u]})
                    meta.append((j, cond))
            while sum(len(g["us"]) for g in groups) < 20:  # filler rows keep the batch shape at 20
                groups.append({"pre": groups[-1]["pre"], "us": [u_stream("filler", len(groups))]})
                meta.append((None, "filler"))
            res = sample(model, groups)
            out = []
            for (j, cond), r in zip(meta, res):
                if j is None:
                    continue
                t_ = j["tgt"]
                toks = idx[t_]["tok16"][:k_star] + r["token_ids"]
                out.append({"task": task, "template": w, "arm": f"PATCH_{cond}", "sample_id": f"{j['dir']}|{j['src']}|{t_}",
                            "direction": j["dir"], "src_class": cls[j["src"]], "tgt_class": cls[t_],
                            "text": tok.decode(toks, skip_special_tokens=True), "token_ids": toks,
                            "n_tokens": len(toks), "finish_reason": r["finish_reason"], "seed": 0,
                            "block_id": f"PATCH:{task}:{w}", "k_star": k_star, "block": block})
            append_jsonl(PATCH_RAW, out)
            rows_out += out
    logger.info(f"patch {task}: {len(rows_out)} continuations")
    return {"n_rows": len(rows_out), "k_star": k_star, "block": block}


def analyse_patch(task: str) -> dict[str, Any]:
    from analysis.common import mcnemar_one_sided
    from label_worker import label_rows

    rows = [r for r in read_jsonl(PATCH_RAW) if r["task"] == task]
    labs = label_rows([{**r, "seed": 0} for r in rows])
    for r, l in zip(rows, labs):
        r["label"] = l["label"]
    out: dict[str, Any] = {}
    for d in ("compliant_to_default", "default_to_compliant"):
        rs = [r for r in rows if r["direction"] == d]
        pairs: dict[str, dict] = {}
        for r in rs:
            pairs.setdefault(r["sample_id"], {})[r["arm"]] = r
        xs, ys = [], []
        for p in pairs.values():
            if "PATCH_patched" not in p or "PATCH_control" not in p:
                continue
            sc = p["PATCH_patched"]["src_class"]
            lp, lc = p["PATCH_patched"]["label"], p["PATCH_control"]["label"]
            if lp in ("invalid", "disputed") or lc in ("invalid", "disputed"):
                continue
            xs.append(int((lp == DEFAULT[task]) == bool(sc)))
            ys.append(int((lc == DEFAULT[task]) == bool(sc)))
        out[d] = {"n_pairs": len(xs), "p_source_class_patched": float(np.mean(xs)) if xs else None,
                  "p_source_class_control": float(np.mean(ys)) if ys else None,
                  "flip_rate": (float(np.mean(xs)) - float(np.mean(ys))) if xs else None,
                  "mcnemar": mcnemar_one_sided(xs, ys) if xs else None}
    write_json(RESULTS_DIR / f"c2e_patch_{task}.json", out)
    return out
