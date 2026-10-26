#!/usr/bin/env python3
"""S3 knob process: iteration 5's own text-level samplers and decoding knobs, run with exp27's code paths UNCHANGED
(vendor/exp27/src: gen5.stage_base, gen5.run_cell_group -> materialise / run_specs / run_multistage, engine5
decode_rows, prompts5, parsers). It runs in its own process because exp27's `cfg` module shadows exp22's.

Only the output paths are redirected (module globals of gen5): rows -> data/raw/knobs_raw.jsonl, multi-stage texts
-> data/knobs_stages.jsonl, base intents -> data/bint_intents.jsonl, batch timing -> results/knobs_timing.jsonl.

Steps (plan 5.0 / 5.2):
  base     Qwen/Qwen3-8B-Base rev 49e3418f, bf16, on exp27's BINT intent prompt ids and intent streams for all
           5 x 50 slots of the decisive tasks (T03, T10, T2, T05, T1); intent-text identity with exp27's
           data/base_intents.jsonl reported; the base model is then unloaded (never two 8B models on the GPU).
  reuse    exp27's rows of the five knobs (BINT, EAP, IFG_hot, T1.3, TOPK10) on the decisive tasks are written to
           data/raw/reuse_exp27.jsonl with arm 'E27:<knob>' so the label worker relabels them with this artifact's
           labeller version.
  check    the five knobs on slots k in {0, 1} x W1-W5 (10 per knob per task) through exp27's code paths.
  verdict  per (task, knob) per-slot label agreement of the check rows with exp27's relabelled rows; reuse exp27's
           N 50 rows iff agreement >= 0.95 (10/10); otherwise the remaining 40 slots (k 2-9) are generated here.
  rerun    generation of k 2-9 for every (task, knob) that failed the check (drop order: TOPK10 and IFG reruns
           first if time binds).

usage: .venv/bin/python src/knobs_k.py base,reuse,check,verdict,rerun
"""

from __future__ import annotations

import gc
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V27SRC = ROOT / "vendor" / "exp27" / "src"
sys.path.insert(0, str(V27SRC))           # exp27's cfg / hooks / engine modules win the name lookup here

import torch  # noqa: E402
from loguru import logger  # noqa: E402

import cfg as C27  # noqa: E402,F401  (exp27's own cfg: ROOT = vendor/exp27)
import gen5  # noqa: E402
from cfg5 import D5  # noqa: E402

sys.path.insert(1, str(Path(__file__).resolve().parent))
import k_cfg as K  # noqa: E402  (this artifact's paths; appends exp22 folders at the END of sys.path)

KNOBS = ["BINT", "EAP", "IFG_hot", "T1.3", "TOPK10"]
TEMPLATES = list(K.TEMPLATES)
CHECK_K = (0, 1)
RERUN_K = tuple(range(2, 10))
KNOBS_RAW = K.RAW_DIR / "knobs_raw.jsonl"
REUSE_RAW = K.RAW_DIR / "reuse_exp27.jsonl"
BINT_INTENTS = K.DATA / "bint_intents.jsonl"
VERDICT = K.RESULTS / "knob_check.json"

gen5.RAW = KNOBS_RAW
gen5.STAGES = K.DATA / "knobs_stages.jsonl"
gen5.BASE_INT = BINT_INTENTS
gen5.TIMING = K.RESULTS / "knobs_timing.jsonl"
gen5.REALISED = K.DATA / "knobs_realised.jsonl"
gen5.TASKS15 = D5                          # base pass on the five decisive tasks only (k 0-9)


def norm_row(r: dict) -> dict:
    """exp27 rows carry sample_id '<task>|<arm>|<w>|<k>' and slot k; this artifact keys rows by integer k."""
    r = dict(r)
    r["exp27_sample_id"] = r.get("sample_id")
    r["sample_id"] = int(r["slot"])
    r["seed"] = K.stable_seed(r["task"], r["template"], int(r["slot"]))
    return r


def step_base() -> dict:
    prompts = gen5.load_prompts()
    gen5.stage_base(prompts)
    gc.collect()
    torch.cuda.empty_cache()
    mine = {(r["task"], r["template"], int(r["slot"])): r for r in K.read_jsonl(BINT_INTENTS)}
    ref = {(r["task"], r["template"], int(r["slot"])): r for r in K.read_jsonl(K.E27 / "data" / "base_intents.jsonl")}
    common = [k for k in mine if k in ref]
    same_text = sum(mine[k]["intent_text"] == ref[k]["intent_text"] for k in common)
    same_ids = sum(mine[k]["intent_ids"] == ref[k]["intent_ids"] for k in common)
    by_task = defaultdict(lambda: [0, 0])
    for k in common:
        by_task[k[0]][0] += mine[k]["intent_text"] == ref[k]["intent_text"]
        by_task[k[0]][1] += 1
    res = {"n_mine": len(mine), "n_common": len(common), "intent_text_identical": same_text,
           "intent_ids_identical": same_ids, "by_task": {t: f"{a}/{b}" for t, (a, b) in by_task.items()},
           "valid_rate": sum(bool(r["valid"]) for r in mine.values()) / max(len(mine), 1), "utc": K.utc_now()}
    K.write_json(K.RESULTS / "bint_intent_identity.json", res)
    logger.info(f"base intents: {res}")
    return res


def step_reuse() -> int:
    have = {K.row_key(r) for r in K.read_jsonl(REUSE_RAW)}
    out = []
    for r in K.read_jsonl(K.E27 / "data" / "samples_raw.jsonl"):
        if r["task"] in D5 and r["arm"] in KNOBS:
            n = norm_row(r)
            n["arm"] = f"E27:{r['arm']}"
            n["stage"] = "E27_reuse"
            if K.row_key(n) not in have:
                out.append(n)
    K.append_jsonl(REUSE_RAW, out)
    logger.info(f"exp27 knob rows queued for relabelling: {len(out)}")
    return len(out)


def _load_instruct():
    tok, model = gen5.load_model(fp8=False, vram_fraction=0.97)
    return tok, model


def _run(model, tok, ks: tuple[int, ...], tasks: list[str], knobs_by_task: dict[str, list[str]], tag: str) -> None:
    prompts = gen5.load_prompts()
    deadline = time.time() + 3 * 3600
    for t in tasks:
        arms = knobs_by_task.get(t, [])
        if not arms:
            continue
        items = [(w, k) for w in TEMPLATES for k in ks]
        t0 = time.time()
        n = gen5.run_cell_group(model, tok, prompts, t, arms, items, f"K:{tag}:{t}", {}, deadline)
        logger.info(f"{tag} {t} {arms}: {n} rows in {time.time() - t0:.0f}s")
    # normalise the new rows' keys for the label worker (a copy with integer sample_id)
    rows = [norm_row(r) for r in K.read_jsonl(KNOBS_RAW)]
    seen = {K.row_key(r) for r in K.read_jsonl(K.RAW_DIR / "knobs_norm.jsonl")}
    K.append_jsonl(K.RAW_DIR / "knobs_norm.jsonl", [r for r in rows if K.row_key(r) not in seen])


def labels_for(keys: list[str], timeout: float = 1800.0) -> dict[str, dict]:
    t0 = time.time()
    while True:
        labs = {l["key"]: l for l in K.read_jsonl(K.LABELS) if l["key"] in set(keys)}
        if len(labs) >= len(keys) or time.time() - t0 > timeout:
            return labs
        time.sleep(15)


def step_verdict() -> dict:
    keys_mine, keys_ref = [], []
    for t in D5:
        for a in KNOBS:
            for w in TEMPLATES:
                for k in CHECK_K:
                    keys_mine.append(f"{t}|{w}|{a}|{k}")
                    keys_ref.append(f"{t}|{w}|E27:{a}|{k}")
    labs = labels_for(keys_mine + keys_ref)
    res: dict = {"rule": "reuse exp27's N 50 rows (relabelled) iff per-slot label agreement >= 0.95 (10/10)",
                 "cells": {}}
    for t in D5:
        for a in KNOBS:
            agree, n, pairs = 0, 0, []
            for w in TEMPLATES:
                for k in CHECK_K:
                    x, y = labs.get(f"{t}|{w}|{a}|{k}"), labs.get(f"{t}|{w}|E27:{a}|{k}")
                    if x is None or y is None:
                        continue
                    n += 1
                    same = x["label"] == y["label"] and bool(x["passed"]) == bool(y["passed"])
                    agree += same
                    pairs.append([w, k, x["label"], y["label"], bool(x["passed"]), bool(y["passed"])])
            frac = agree / n if n else None
            res["cells"][f"{t}|{a}"] = {"n": n, "agree": agree, "agreement": frac,
                                         "reuse": bool(frac is not None and n >= 10 and frac >= 0.95),
                                         "pairs": pairs}
    res["n_reuse"] = sum(v["reuse"] for v in res["cells"].values())
    res["utc"] = K.utc_now()
    K.write_json(VERDICT, res)
    logger.info(f"knob check: {res['n_reuse']} of {len(res['cells'])} (task, knob) cells reuse exp27 rows")
    return res


@logger.catch(reraise=True)
def main() -> None:
    K.setup_logging("knobs_k")
    steps = sys.argv[1].split(",") if len(sys.argv) > 1 else ["base", "reuse", "check", "verdict", "rerun"]
    torch.backends.cuda.matmul.allow_tf32 = False
    if "base" in steps:
        step_base()
    if "reuse" in steps:
        step_reuse()
    model = tok = None
    if "check" in steps:
        tok, model = _load_instruct()
        _run(model, tok, CHECK_K, list(D5), {t: KNOBS for t in D5}, "check")
    if "verdict" in steps:
        res = step_verdict()
    else:
        res = K.read_json(VERDICT) if VERDICT.exists() else None
    if "rerun" in steps and res is not None:
        need: dict[str, list[str]] = defaultdict(list)
        for key, v in res["cells"].items():
            t, a = key.split("|")
            if not v["reuse"]:
                need[t].append(a)
        # drop order: IFG and TOPK10 reruns go last
        for t in need:
            need[t].sort(key=lambda a: (a in ("IFG_hot", "TOPK10"), KNOBS.index(a)))
        if need:
            if model is None:
                tok, model = _load_instruct()
            _run(model, tok, RERUN_K, list(D5), dict(need), "rerun")
    K.write_json(K.RESULTS / "knobs_done.json", {"steps": steps, "utc": K.utc_now()})


if __name__ == "__main__":
    main()
