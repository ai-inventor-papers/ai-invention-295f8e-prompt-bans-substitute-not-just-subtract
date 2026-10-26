#!/usr/bin/env python3
"""S8: teacher-forced state extraction.

For every named-ban and neutral sample (plus the T1 W4 top-up and the archived iteration-2 ban rows): one forward
pass over prompt + generated tokens 1..16 (padded with <|im_end|> if shorter; positions past the end are flagged).
Saved per (task, arm): fp16 block outputs (blocks 8..28) at [S-mean, R, k=1..8, k=16], layer-0 embeddings at k=1..8,
and the top-20 next-token log-probs at R and k=1..8. 5c: blocks {12,16,20,23,24,28} at k=1,2,3,16 for every other arm.
"""

from __future__ import annotations

import json
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg import (E8, E12, IM_END, SAVE_BLOCKS, STATES_DIR, read_json, read_jsonl, sha256_text, write_json)
import states_io
from engine import forward_capture

POS_NAMES = ["Smean", "R"] + [f"k{k}" for k in range(1, 9)] + ["k16"]
GEN_K = list(range(1, 9)) + [16]
BLOCKS_5C = [12, 16, 20, 23, 24, 28]
ARCHIVE_BLOCKS = list(range(8, 29, 2))


def _ids16(prompt_ids: list[int], toks: list[int]) -> tuple[list[int], int]:
    g = list(toks[:16])
    n = len(g)
    g = g + [IM_END] * (16 - n)
    return list(prompt_ids) + g, n


@torch.no_grad()
def extract_group(model: Any, prompt: dict[str, Any], toks_list: list[list[int]], blocks: list[int],
                  full: bool = True, bs: int = 20) -> dict[str, np.ndarray]:
    P, a, b = prompt["P"], prompt["p1"], prompt["spec_end"]
    pos = [P - 1] + [P + k - 1 for k in GEN_K]
    st, emb, tlp, tid, ngen = [], [], [], [], []
    for i in range(0, len(toks_list), bs):
        chunk = toks_list[i:i + bs]
        ids, ns = zip(*[_ids16(prompt["ids"], t) for t in chunk])
        fc = forward_capture(model, list(ids), blocks, pos, s_range=(a, b) if full else None,
                             want_embed=[P + k - 1 for k in range(1, 9)] if full else None,
                             want_logits=[P - 1] + [P + k - 1 for k in range(1, 9)] if full else None)
        x = torch.stack([fc["states"][l] for l in blocks], dim=2)  # [B, 10, nb, D]
        if full:
            sm = torch.stack([fc["s_mean"][l] for l in blocks], dim=1)[:, None]  # [B, 1, nb, D]
            x = torch.cat([sm, x], dim=1)  # [B, 11, nb, D]
            emb.append(fc["embed"].numpy().astype(np.float16))
            tlp.append(fc["top_lp"].astype(np.float16))
            tid.append(fc["top_id"].astype(np.int32))
        st.append(x.numpy().astype(np.float16))
        ngen += list(ns)
    out = {"states": np.concatenate(st), "n_gen": np.array(ngen)}
    if full:
        out.update(embed=np.concatenate(emb), top_lp=np.concatenate(tlp), top_id=np.concatenate(tid))
    return out


def save_arm(model: Any, prompts: dict, task: str, arm: str, rows: list[dict[str, Any]], tag: str | None = None,
             blocks: list[int] = SAVE_BLOCKS, full: bool = True, prompt_kind: str = "ban", bs: int = 20,
             overwrite: bool = False) -> int:
    tag = tag or f"{task}_{arm}"
    if states_io.exists(STATES_DIR / tag) and not overwrite:
        return 0
    rows = sorted(rows, key=lambda r: (r["template"], int(r["sample_id"])))
    parts: dict[str, list[np.ndarray]] = {}
    index = []
    for w in sorted({r["template"] for r in rows}):
        rw = [r for r in rows if r["template"] == w]
        pr = prompts[(task, w, prompt_kind)]
        res = extract_group(model, pr, [r["token_ids"] for r in rw], blocks, full=full, bs=bs)
        for k, v in res.items():
            parts.setdefault(k, []).append(v)
        for r, n in zip(rw, res["n_gen"]):
            index.append({"key": r.get("key"), "task": task, "arm": arm, "template": w, "sample_id": r["sample_id"],
                          "label": r.get("label"), "n_gen": int(n), "tok16": [int(x) for x in r["token_ids"][:16]],
                          "source": r.get("source", "iter3")})
    arrs = {k: np.concatenate(v) for k, v in parts.items()}
    states_io.save(STATES_DIR / tag, arrs.pop("states"))  # row-wise parts when > 90 MB (GitHub 100 MB limit)
    if full:
        np.save(STATES_DIR / f"{tag}_embed.npy", arrs.pop("embed"))
        np.savez_compressed(STATES_DIR / f"{tag}_toplp.npz", top_lp=arrs.pop("top_lp"), top_id=arrs.pop("top_id"))
    with open(STATES_DIR / f"{tag}_index.jsonl", "w") as fh:
        for r in index:
            fh.write(json.dumps(r) + "\n")
    write_json(STATES_DIR / f"{tag}_meta.json", {"positions": POS_NAMES if full else ["R"] + [f"k{k}" for k in GEN_K],
                                                  "blocks": blocks, "n": len(index), "dtype": "float16",
                                                  "teacher_forcing_batch": bs,
                                                  "convention": "block l output; k = generated position (token k "
                                                                "is the input there)"})
    return len(index)


def archive_rows(prompts: dict) -> dict[str, list[dict[str, Any]]]:
    """Archived iteration-2 ban rows whose prompt ids are byte-identical to S1's ban ids (sha256), with labels from the
    same canonical labeller: exp8 arm a (stored token ids) and exp12 fresh pool (stored generated ids)."""
    out: dict[str, list[dict[str, Any]]] = {"T1": [], "T2": []}
    meta = {"exp8_arm_a": 0, "exp12_fresh_pool": 0, "rejected_prompt_mismatch": 0, "rejected_no_ids": 0}
    for r in read_jsonl(E8 / "data" / "samples.jsonl"):
        if r["condition"] != "a":
            continue
        t = r["task"].upper()
        if not r.get("token_ids"):
            meta["rejected_no_ids"] += 1
            continue
        out[t].append({"key": f"exp8|{t}|{r['template']}|{r['sample_id']}", "template": r["template"],
                       "sample_id": 1000 + int(r["sample_id"]), "token_ids": r["token_ids"], "label": r["label"],
                       "source": "exp8_arm_a"})
        meta["exp8_arm_a"] += 1
    p12 = read_json(E12 / "prompts" / "prompts_v2.json")["prompts"]
    labs = {(r["task"], r["template"], int(r["sample_id"])): r for r in read_jsonl(E12 / "results" / "labelled_c1.jsonl")}
    for r in read_jsonl(E12 / "results" / "raw" / "c1_fresh_pool.jsonl"):
        t = r["task"].upper()
        ids12 = p12[r["prompt_key"]]["nothink"]["ids"]
        if sha256_text(json.dumps(ids12)) != prompts[(t, r["template"], "ban")]["prompt_sha256"]:
            meta["rejected_prompt_mismatch"] += 1
            continue
        g = r["gen_token_ids"]
        g = json.loads(g) if isinstance(g, str) else g
        lab = labs.get((r["task"], r["template"], int(r["sample_id"])))
        if not g or lab is None:
            meta["rejected_no_ids"] += 1
            continue
        out[t].append({"key": f"exp12|{t}|{r['template']}|{r['sample_id']}", "template": r["template"],
                       "sample_id": 2000 + int(r["sample_id"]), "token_ids": g, "label": lab["label"],
                       "source": "exp12_fresh_pool"})
        meta["exp12_fresh_pool"] += 1
    write_json(STATES_DIR / "archive_meta.json", meta)
    logger.info(f"archive rows: {meta}")
    return out


def stage_states(model: Any, prompts: dict, raw_by_arm: dict[tuple[str, str], list[dict[str, Any]]],
                 tasks: list[str], deadline: float) -> None:
    t0 = time.time()
    for t in tasks:
        for arm, kind in (("BAN", "ban"), ("NEUTRAL", "twin"), ("BAN_TOPUP", "ban")):
            rows = raw_by_arm.get((t, arm), [])
            if rows:
                n = save_arm(model, prompts, t, arm, rows, prompt_kind=kind)
                if n:
                    logger.info(f"S8 {t}/{arm}: {n} rows ({time.time() - t0:.0f}s)")
    arch = archive_rows(prompts)
    for t in ("T1", "T2"):
        if arch[t] and time.time() < deadline:
            n = save_arm(model, prompts, t, "ARCHIVE", arch[t], blocks=ARCHIVE_BLOCKS)
            logger.info(f"S8 archive {t}: {n} rows")
    # 5c: other arms, blocks {12,16,20,23,24,28}, positions R, k1..8, k16 (mean of k1-3 computed in the analysis)
    for t in tasks:
        for (tt, arm), rows in sorted(raw_by_arm.items()):
            if tt != t or arm in ("BAN", "NEUTRAL", "BAN_TOPUP") or arm.startswith("U7") or not rows:
                continue
            if time.time() > deadline:
                logger.warning("S8 5c extraction stopped at the deadline")
                return
            kind = "twin" if (arm.startswith("ADD") or arm.startswith("RAND")) else "ban"
            save_arm(model, prompts, t, arm, rows, tag=f"5c_{t}_{arm}", blocks=BLOCKS_5C, full=False,
                     prompt_kind=kind)
    logger.info(f"S8 done in {time.time() - t0:.0f}s")


def stage_states_b1(model: Any, prompts: dict, raw_by_arm: dict[tuple[str, str], list[dict[str, Any]]],
                    tasks: list[str]) -> None:
    """Re-extract the C2e / 5a states at BATCH 1 (the plan's specification): with FP8 W8A8 the teacher-forced state
    of a row in a large batch depends on its row position (GEMM tiling), so identical prefixes gave states that differ
    by 4-8% (relative L2). At batch 1 a state depends only on the prefix (and the template's prompt length)."""
    t0 = time.time()
    for t in tasks:
        for arm, kind in (("BAN", "ban"), ("NEUTRAL", "twin"), ("BAN_TOPUP", "ban")):
            rows = raw_by_arm.get((t, arm), [])
            if rows:
                n = save_arm(model, prompts, t, arm, rows, prompt_kind=kind, bs=1, overwrite=True)
                logger.info(f"S8 (batch 1) {t}/{arm}: {n} rows ({time.time() - t0:.0f}s)")
    arch = archive_rows(prompts)
    for t in ("T1", "T2"):
        if arch[t]:
            n = save_arm(model, prompts, t, "ARCHIVE", arch[t], blocks=ARCHIVE_BLOCKS, bs=1, overwrite=True)
            logger.info(f"S8 (batch 1) archive {t}: {n} rows ({time.time() - t0:.0f}s)")
