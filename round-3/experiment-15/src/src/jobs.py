#!/usr/bin/env python3
"""Generation jobs: request builders for every phase and a staged (10 -> 100 -> rest), resumable runner that appends
one raw row per generation to data/raw_gen.jsonl (prompt sha, seed, output ids, text, finish reason, timings)."""

from __future__ import annotations

import collections
import json
import time
from pathlib import Path
from typing import Any

from loguru import logger

from src import prompts_llama as P
from src.ws import (ASSOC_MAX_TOKENS, DATA, FROZEN_TASKS, MAX_TOKENS, MODEL_TAG, PRED, RESULTS, append_jsonl,
                    read_json, read_jsonl, request_seed, write_json)

RAW = DATA / "raw_gen.jsonl"
TIMINGS = RESULTS / "timings.json"
DECODING = {"temperature": 1.0, "top_p": 1.0, "top_k": -1, "min_p": 0.0, "repetition_penalty": 1.0,
            "presence_penalty": 0.0, "frequency_penalty": 0.0, "engine": "vllm==0.11.0 (V1, eager, bf16)"}


def x0() -> dict[str, str]:
    return read_json(PRED / "x0.json")["x0"]


def _req(prompt: dict[str, Any], *, phase: str, condition: str, task: str, template: Any, sample_id: Any,
         max_tokens: int = MAX_TOKENS, h: int | None = None, mode: str | None = None,
         extra: dict[str, Any] | None = None, seed_cond: str | None = None) -> dict[str, Any]:
    seed = request_seed(task, seed_cond or condition, template, sample_id)
    r = {"row_id": f"{phase}|{task}|{condition}|{template}|{sample_id}", "phase": phase, "task": task,
         "condition": condition, "kind": prompt["kind"], "template": template, "h": h, "mode": mode,
         "sample_id": sample_id, "seed": seed, "prompt_sha256": prompt["sha"], "prompt_len": len(prompt["ids"]),
         "spec_start": prompt["spec_start"], "spec_end": prompt["spec_end"], "seg_start": prompt["seg_start"],
         "noun": prompt.get("noun"), "pad_k": prompt.get("k"), "prompt_ids": prompt["ids"], "max_tokens": max_tokens}
    if extra:
        r.update(extra)
    return r


# ------------------------------------------------------------------------------------------------ phase builders
def reqs_twin_family(phase: str, condition: str, tasks: list[str] | None = None) -> list[dict[str, Any]]:
    """B1 neutral_baseline / B4 vetofree: X0-family neutral twins, W1-W5 x 10 (h=0 for samples 0-4, h=1 for 5-9)."""
    X0 = x0()
    out = []
    for t in tasks or FROZEN_TASKS:
        for w in range(1, 6):
            for s in range(10):
                h = 0 if s < 5 else 1
                p = P.p_twin(t, X0[t], w, h)
                out.append(_req(p, phase=phase, condition=condition, task=t, template=w, sample_id=s, h=h, mode=X0[t]))
    return out


def reqs_association(tasks: list[str] | None = None) -> list[dict[str, Any]]:
    out = []
    for t in tasks or FROZEN_TASKS:
        for m in P.modes(t):
            p = P.p_assoc(t, m)
            for s in range(20):
                out.append(_req(p, phase="B2", condition=f"association:{m}", task=t, template=None, sample_id=s,
                                max_tokens=ASSOC_MAX_TOKENS, mode=m))
    return out


def reqs_forced(ks: list[int], n_per: int, round_tag: str, tasks: list[str] | None = None,
                modes_only: dict[str, list[str]] | None = None, start: int = 0) -> list[dict[str, Any]]:
    out = []
    for t in tasks or FROZEN_TASKS:
        for m in P.modes(t):
            if modes_only is not None and m not in modes_only.get(t, []):
                continue
            for k in ks:
                p = P.p_forced(t, m, k)
                for s in range(start, start + n_per):
                    out.append(_req(p, phase=f"B3{round_tag}", condition=f"forced:{m}:k{k}", task=t, template=k,
                                    sample_id=s, mode=m))
    return out


def reqs_nonce_novelty(tasks: list[str] | None = None) -> list[dict[str, Any]]:
    out = []
    for t in tasks or FROZEN_TASKS:
        for w in range(1, 6):
            p = P.p_nonce(t, w)
            for s in range(10):
                out.append(_req(p, phase="B5", condition="nonce", task=t, template=w, sample_id=s))
        p = P.p_novelty(t)
        for s in range(50):
            out.append(_req(p, phase="B5", condition="novelty", task=t, template=None, sample_id=s))
    return out


def reqs_bans(task: str, mode: str, n_per_template: int = 20, phase: str = "G1") -> list[dict[str, Any]]:
    out = []
    for w in range(1, 6):
        p = P.p_ban(task, mode, w)
        for s in range(n_per_template):
            h = 0 if s < n_per_template // 2 else 1
            out.append(_req(p, phase=phase, condition=f"ban:{mode}", task=task, template=w, sample_id=s, h=h,
                            mode=mode, seed_cond=f"ban:{mode}:w{w}"))
    return out


# ------------------------------------------------------------------------------------------------ runner
def done_ids(path: Path = RAW) -> set[str]:
    return {r["row_id"] for r in read_jsonl(path)}


def _timing(name: str, rec: dict[str, Any]) -> None:
    tm = read_json(TIMINGS) if TIMINGS.exists() else {}
    tm.setdefault(name, []).append(rec)
    write_json(TIMINGS, tm)


def run_staged(llm, reqs: list[dict[str, Any]], name: str, path: Path = RAW, stages=(10, 100)) -> list[dict[str, Any]]:
    """Generate reqs not yet in `path` in stages; append rows; log tok/s and the extrapolated remaining time."""
    from src.engine_vllm import generate, sampling, effective_params

    have = done_ids(path)
    todo = [r for r in reqs if r["row_id"] not in have]
    logger.info(f"[{name}] {len(reqs)} requests, {len(todo)} to run")
    if not todo:
        return []
    # log the effective SamplingParams of the first request of every condition
    seen = set()
    eff = {}
    for r in todo:
        if r["condition"] not in seen:
            seen.add(r["condition"])
            eff[r["condition"]] = effective_params(sampling(r["max_tokens"], r["seed"], logit_bias=r.get("logit_bias"),
                                                            veto=r.get("veto")))
    pf = RESULTS / "effective_sampling_params.json"
    allp = read_json(pf) if pf.exists() else {}
    allp[name] = dict(list(eff.items())[:40])
    write_json(pf, allp)
    bounds = []
    i = 0
    for s in stages:
        if i < len(todo):
            bounds.append((i, min(len(todo), i + s)))
            i = min(len(todo), i + s)
    if i < len(todo):
        bounds.append((i, len(todo)))
    rows_all = []
    for a, b in bounds:
        chunk = todo[a:b]
        t0 = time.time()
        outs = generate(llm, chunk)
        dt = time.time() - t0
        ntok = sum(o["n_new_tokens"] for o in outs)
        rows = []
        for r, o in zip(chunk, outs):
            row = {k: v for k, v in r.items() if k not in ("prompt_ids",)}
            row.update(o)
            row["model"] = MODEL_TAG
            row["decoding"] = DECODING
            row["t_unix"] = time.time()
            rows.append(row)
        append_jsonl(path, rows)
        rows_all += rows
        n_len = sum(1 for o in outs if o["finish_reason"] == "length")
        rate = ntok / max(dt, 1e-9)
        remaining = len(todo) - b
        eta = remaining * (dt / max(len(chunk), 1))
        rec = {"stage": f"{a}-{b}", "n": len(chunk), "seconds": round(dt, 1), "new_tokens": ntok,
               "tok_per_s": round(rate, 1), "mean_new_tokens": round(ntok / max(len(chunk), 1), 1),
               "length_rate": round(n_len / max(len(chunk), 1), 3), "remaining": remaining,
               "eta_seconds_linear": round(eta, 0)}
        _timing(name, rec)
        logger.info(f"[{name}] {rec}")
    return rows_all


def raw_rows(phases: set[str] | None = None) -> list[dict[str, Any]]:
    rows = read_jsonl(RAW)
    return [r for r in rows if phases is None or r["phase"] in phases]


def counts_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(collections.Counter(r[key] for r in rows))
