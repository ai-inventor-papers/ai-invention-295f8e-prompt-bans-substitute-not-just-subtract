#!/usr/bin/env python3
"""Arm registry, exact-CRN batches of B = 20 rows of ONE (unit, prompt), resumable raw rows (data/samples_raw.jsonl).

Arms (instruct = Qwen3-8B, base = Qwen3-8B-Base; both read the SAME token ids):
  TWIN / TWIN_EXTRA / GATE   instruct, neutral twin W1-W5, no edit (TWIN_EXTRA = batch pad, k 10-99; GATE = k 100-101)
  NOV / NOV_EXTRA            instruct, novelty prompt (k 0-29; pad k >= 30)
  ASSOC_<mode>               instruct, association prompt naming <mode>, max 64 tokens, no fence
  BASE                       base, neutral twin W1-W5 (k 0-19), fence stop
  PLAIN / PLAIN_EXTRA        base, plain completion (opened fence + signature + docstring), k 0-49 (pad k >= 50)
  ESC_d<seed>_a<alpha>       instruct, twin + isotropic push u = rand_dir(seed), M = alpha * n (ban-free unit)
  PN_a<alpha>                instruct, twin + a FRESH isotropic direction per sample (seed = pn_seed(unit, arm, w, k))
  T13 / T13_EXTRA            instruct, twin at temperature 1.3
  SCR_d<seed>_a<alpha>       engine check: exp17 direction and exp17's own ban unit on the exp17 twin prompt
Uniforms: u_stream(unit, template, k) for every twin-prompt arm in both models (CRN), (unit, 'NOV', k),
(unit, 'ASSOC', mode, k), (unit, 'PLAIN', k); engine check u_stream(task, w, k) exactly as exp17.
"""

from __future__ import annotations

import re
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg5 import (B, BASE_ID, BASE_REVISION, DECODING_STR, MAX_NEW, MAX_NEW_ASSOC, MODEL_ID, MODEL_REVISION,
                  PRECISION, RAW, REALISED, TIMING, append_jsonl, pn_seed, read_jsonl, stable_seed, utc_now)
from ctx5 import UnitCtx, rand_dir
from engine5 import sample, u_stream

PAD_ARM = {"TWIN": "TWIN_EXTRA", "GATE": "TWIN_EXTRA", "TWIN_EXTRA": "TWIN_EXTRA", "NOV": "NOV_EXTRA",
           "PLAIN": "PLAIN_EXTRA", "T13": "T13_EXTRA", "BASE": "BASE_EXTRA"}
PAD_START = {"TWIN_EXTRA": 10, "NOV_EXTRA": 30, "PLAIN_EXTRA": 50, "T13_EXTRA": 10, "BASE_EXTRA": 20}


def parse_arm(arm: str) -> dict[str, Any]:
    if arm in ("TWIN", "TWIN_EXTRA", "GATE"):
        return {"family": arm, "model": "instruct", "prompt": "twin", "T": 1.0}
    if arm in ("NOV", "NOV_EXTRA"):
        return {"family": arm, "model": "instruct", "prompt": "novelty", "T": 1.0}
    if arm.startswith("ASSOC_"):
        return {"family": "ASSOC", "model": "instruct", "prompt": "assoc", "X": arm[6:], "T": 1.0}
    if arm in ("BASE", "BASE_EXTRA"):
        return {"family": arm, "model": "base", "prompt": "twin", "T": 1.0}
    if arm in ("PLAIN", "PLAIN_EXTRA"):
        return {"family": arm, "model": "base", "prompt": "plain", "T": 1.0}
    if arm in ("T13", "T13_EXTRA"):
        return {"family": arm, "model": "instruct", "prompt": "twin", "T": 1.3}
    m = re.fullmatch(r"(ESC|SCR)_d(\d+)_a([\d.]+)", arm)
    if m:
        return {"family": m.group(1), "model": "instruct", "prompt": "twin", "T": 1.0, "seed": int(m.group(2)),
                "alpha": float(m.group(3))}
    m = re.fullmatch(r"PN_a([\d.]+)", arm)
    if m:
        return {"family": "PN", "model": "instruct", "prompt": "twin", "T": 1.0, "alpha": float(m.group(1))}
    raise ValueError(arm)


def u_key(unit: str, w: str, arm: str, k: int, engine_check: bool) -> tuple:
    a = parse_arm(arm)
    if unit[:2] in ("P_", "V_"):
        unit = unit[2:]   # variant and parent re-measure share the parent's uniforms (exp17 u_stream(task, w, k))
    if engine_check:
        return (unit, w, k)
    if a["prompt"] == "novelty":
        return (unit, "NOV", k)
    if a["prompt"] == "assoc":
        return (unit, "ASSOC", a["X"], k)
    if a["prompt"] == "plain":
        return (unit, "PLAIN", k)
    return (unit, w, k)


def done_slots(model_tag: str) -> set[tuple[str, str, str, int]]:
    return {(r["unit"], r["template"], r["arm"], int(r["slot"])) for r in read_jsonl(RAW)
            if r["model_tag"] == model_tag}


def pack(cells: list[tuple[str, list[int]]], used: dict[str, set[int]]) -> list[list[tuple[str, list[int]]]]:
    """Greedy packing of (arm, slots) cells into batches of exactly B rows; the last batch is padded with fresh pad
    slots of the first cell's pad arm (logged as *_EXTRA rows, never used in decisive cells)."""
    batches: list[list[tuple[str, list[int]]]] = []
    cur: list[tuple[str, list[int]]] = []
    room = B
    for arm, ks in cells:
        ks = list(ks)
        while ks:
            take = ks[:room]
            ks = ks[room:]
            cur.append((arm, take))
            room -= len(take)
            if room == 0:
                batches.append(cur)
                cur, room = [], B
    if cur:
        first = cur[0][0]
        pa = PAD_ARM.get(first, "TWIN_EXTRA")
        if first.startswith("ASSOC_"):
            pa = first
        k = PAD_START.get(pa, 20)
        s = used.setdefault(pa, set())
        pad = []
        while len(pad) < room:
            if k not in s:
                pad.append(k)
                s.add(k)
            k += 1
        cur.append((pa, pad))
        batches.append(cur)
    return batches


class Runner:
    def __init__(self, model: Any, tok: Any, model_tag: str, prompts: dict[str, dict[str, Any]]):
        self.model, self.tok, self.model_tag, self.pr = model, tok, model_tag, prompts
        self.model_id = MODEL_ID if model_tag == "instruct" else BASE_ID
        self.revision = MODEL_REVISION if model_tag == "instruct" else BASE_REVISION
        self.ctx: dict[str, UnitCtx] = {}

    def unit_ctx(self, unit: str, engine_check: bool) -> UnitCtx:
        if unit not in self.ctx:
            if engine_check:
                twins = {p["template_id"]: p for p in self.pr.values() if p["unit"] == unit and p["kind"] == "twin"}
                self.ctx[unit] = UnitCtx(self.model, unit, twins, unit_kind=f"exp17:{unit}")
            else:
                twins = {p["template_id"]: p for p in self.pr.values() if p["unit"] == unit and p["kind"] == "twin"}
                self.ctx[unit] = UnitCtx(self.model, unit, twins)
        return self.ctx[unit]

    def release(self) -> None:
        for c in self.ctx.values():
            c.release()
        self.ctx.clear()

    def prompt_for(self, unit: str, w: str, arm: str) -> dict[str, Any]:
        a = parse_arm(arm)
        if a["prompt"] == "twin":
            return self.pr[f"{unit}|twin|-|{w}"]
        if a["prompt"] == "novelty":
            return self.pr[f"{unit}|novelty|-|NOV"]
        if a["prompt"] == "assoc":
            return self.pr[f"{unit}|assoc|{a['X']}|-"]
        return self.pr[f"{unit}|plain|-|PLAIN"]

    def run_batch(self, unit: str, w: str, spec: list[tuple[str, list[int]]], stage: str,
                  engine_check: bool = False, extra_meta: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        assert sum(len(ks) for _, ks in spec) == B, spec
        t0 = time.time()
        a0 = parse_arm(spec[0][0])
        T = a0["T"]
        fam = a0["prompt"]
        assert all(parse_arm(arm)["T"] == T and parse_arm(arm)["prompt"] == fam for arm, _ in spec), spec
        assert all(parse_arm(arm)["model"] == self.model_tag for arm, _ in spec), (spec, self.model_tag)
        p = self.prompt_for(unit, w, spec[0][0])
        fence = None if fam == "assoc" else ("plain" if fam == "plain" else ("path" if unit == "T2" else "bench"))
        max_new = MAX_NEW_ASSOC if fam == "assoc" else (768 if fam == "plain" else MAX_NEW)
        groups, meta, recs = [], [], []
        ctx = self.unit_ctx(unit, engine_check) if fam == "twin" else None
        for arm, ks in spec:
            a = parse_arm(arm)
            if a["family"] in ("ESC", "SCR"):
                pre, rec = ctx.arm_prefill(w, ctx.push_spec(w, rand_dir(a["seed"]), a["alpha"]))
                if rec:
                    recs.append({"unit": unit, "template": w, "arm": arm, "stage": stage, "utc": utc_now(), **rec})
                groups.append({"pre": pre, "us": [u_stream(*u_key(unit, w, arm, k, engine_check), n=max_new)
                                                  for k in ks]})
                for k in ks:
                    meta.append((arm, k, rec.get("rel_err_max") if rec else None, a.get("seed")))
            elif a["family"] == "PN":
                for k in ks:
                    sd = pn_seed(unit, arm, w, k)
                    pre, rec = ctx.arm_prefill(w, ctx.push_spec(w, rand_dir(sd), a["alpha"]))
                    recs.append({"unit": unit, "template": w, "arm": arm, "slot": k, "stage": stage,
                                 "utc": utc_now(), "direction_seed": sd, **rec})
                    groups.append({"pre": pre, "us": [u_stream(*u_key(unit, w, arm, k, engine_check), n=max_new)]})
                    meta.append((arm, k, rec.get("rel_err_max"), sd))
            else:
                if fam == "twin":
                    pre = ctx.twin(w)["pre"]
                else:
                    from engine5 import prefill
                    pre = prefill(self.model, p["ids"])
                groups.append({"pre": pre, "us": [u_stream(*u_key(unit, w, arm, k, engine_check), n=max_new)
                                                  for k in ks]})
                for k in ks:
                    meta.append((arm, k, None, None))
        res = sample(self.model, self.tok, groups, fence=fence, max_new=max_new, temperature=T)
        out = []
        for (arm, k, rerr, sd), r in zip(meta, res):
            a = parse_arm(arm)
            out.append({"unit": unit, "arm": arm, "template": w, "slot": k, "model_tag": self.model_tag,
                        "model": self.model_id, "model_revision": self.revision, "precision": PRECISION,
                        "decoding": DECODING_STR, "temperature": T, "top_k": None, "thinking": False,
                        "site": "task_spec_12_23_prefill" if a["family"] in ("ESC", "PN", "SCR") else None,
                        "family": a["family"], "alpha": a.get("alpha"), "direction_seed": sd,
                        "stage": stage, "prompt_pid": p["pid"], "prompt_sha256": p["prompt_sha256"],
                        "rel_err_max": rerr, "text": self.tok.decode(r["token_ids"], skip_special_tokens=True),
                        "token_ids": r["token_ids"], "n_tokens": r["n_tokens"], "finish_reason": r["finish_reason"],
                        "fence_step": r["fence_step"], "logprob_sum": r["logprob_sum"], "utc": utc_now(),
                        "engine_check": engine_check, **(extra_meta or {})})
        append_jsonl(RAW, out)
        if recs:
            append_jsonl(REALISED, recs)
        dt = time.time() - t0
        append_jsonl(TIMING, [{"stage": stage, "unit": unit, "w": w, "arms": [x for x, _ in spec],
                               "model_tag": self.model_tag, "seconds": dt, "steps": res[0]["steps"],
                               "max_tokens": max(r["n_tokens"] for r in res), "utc": utc_now()}])
        logger.info(f"{stage} {unit}/{w} {[x for x, _ in spec]}: {dt:.1f}s, {res[0]['steps']} steps")
        return out

    def run_cells(self, unit: str, cells_by_w: dict[str, list[tuple[str, list[int]]]], stage: str,
                  deadline: float | None = None, engine_check: bool = False) -> int:
        done = done_slots(self.model_tag)
        used: dict[str, set[int]] = {}
        nb = 0
        for w, cells in cells_by_w.items():
            for (uu, ww, arm, k) in done:
                if uu == unit and ww == w:
                    used.setdefault(arm, set()).add(k)
            todo = []
            for arm, ks in cells:
                rest = [k for k in ks if (unit, w, arm, k) not in done]
                used.setdefault(arm, set()).update(ks)
                if rest:
                    todo.append((arm, rest))
            if not todo:
                continue
            # group by (prompt family, temperature): a batch never mixes them
            fams: dict[tuple, list[tuple[str, list[int]]]] = {}
            for arm, ks in todo:
                a = parse_arm(arm)
                key = (a["prompt"], a["T"], a.get("X"))
                fams.setdefault(key, []).append((arm, ks))
            for key, fcells in fams.items():
                for bi, spec in enumerate(pack(fcells, used)):
                    if deadline is not None and time.time() > deadline:
                        logger.warning(f"deadline before {stage} {unit}/{w} batch {bi}")
                        return nb
                    self.run_batch(unit, w, spec, stage, engine_check=engine_check)
                    nb += 1
        return nb
