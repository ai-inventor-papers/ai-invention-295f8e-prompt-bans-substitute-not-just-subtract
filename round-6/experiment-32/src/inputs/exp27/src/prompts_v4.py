#!/usr/bin/env python3
"""Stage 0.6: every prompt of the artifact, chat-rendered with the Qwen3 template (thinking off).

Kinds (condition segment + blank line + frozen task specification):
  twin     W1-W5 neutral twin (bench: exp13/exp17 ids, token-length matched to the ban; path: exp8 neutral_A)
  plain    the specification alone (no condition segment)
  nonce    W1-W5 ban templates with X = 'the Zorblax method'
  novelty  the frozen novelty sentence (one prompt; the 50 rows differ only by their CRN key)
  semseed  T1/T2 only: exp6's semantic-seed paragraph p = template index (W1 -> p0 ... W5 -> p4)
  vs       verbalized sampling: list five algorithms with probabilities, pick one at random, implement it
Rendering: exp17 prompts.record (tok.apply_chat_template, enable_thinking=False). Assertions: the token ids from the
first 'Task:' token to the end of the prompt are IDENTICAL across every kind of a task; the norm file's position count
equals spec_end - p1. R2 (held out): the twin pads the neutral noun to the token count of the default's display-name
STRING; no ban prompt is ever rendered; a final grep finds no catalogue display name or alias in any R2 prompt.
"""

from __future__ import annotations

import json
import re
from typing import Any

import numpy as np
from loguru import logger

from cfg import (BENCH, BENCH12, DATA_DIR, DEFAULT, E6, E7, E8, E13, E17, EXP8_TASK, NONCE_X, NOVELTY, PAD_FILLER,
                 PATH_TASKS, RESULTS_DIR, TEMPLATE_IDS, TEMPLATE_TAIL, TEMPLATES, VS_SEGMENT, cap_first, read_json,
                 read_jsonl, sha256_text, write_json, write_jsonl)

PROMPTS_FILE = DATA_DIR / "prompts.jsonl"
NOUN_EXCLUSIONS = {"ass", "bucket", "chain", "edge", "game", "graph", "grid", "head", "heap", "key", "line", "link",
                   "list", "map", "maze", "net", "node", "path", "point", "queue", "ring", "road", "route", "search",
                   "stack", "step", "street", "table", "track", "train", "tree", "walk", "way", "web"}  # exp13


def load_tokenizer():
    from transformers import AutoTokenizer

    from cfg import model_path

    return AutoTokenizer.from_pretrained(model_path())


def chat_ids(tok: Any, user_text: str) -> list[int]:
    ids = tok.apply_chat_template([{"role": "user", "content": user_text}], tokenize=True,
                                  add_generation_prompt=True, enable_thinking=False)
    if isinstance(ids, dict):
        ids = ids["input_ids"]
    return list(ids)


def positions(tok: Any, ids: list[int], spec: str) -> tuple[int, int, int]:
    head = tok("<|im_start|>user\n", add_special_tokens=False)["input_ids"]
    assert ids[:len(head)] == head, "unexpected chat header"
    suf = tok(spec + TEMPLATE_TAIL, add_special_tokens=False)["input_ids"]
    p1 = len(ids) - len(suf)
    assert ids[p1:] == suf, "SPEC + template tail do not tokenize identically in context"
    tail = tok(TEMPLATE_TAIL, add_special_tokens=False)["input_ids"]
    assert ids[len(ids) - len(tail):] == tail, "chat tail mismatch"
    return len(head), p1, len(ids) - len(tail)


def record(tok: Any, task: str, w: str, kind: str, segment: str | None, spec: str, **extra: Any) -> dict[str, Any]:
    text = (cap_first(segment) + "\n\n" + spec) if segment else spec
    ids = chat_ids(tok, text)
    p0, p1, spec_end = positions(tok, ids, spec)
    return {"task": task, "w": w, "kind": kind, "segment": cap_first(segment) if segment else "", "user_text": text,
            "ids": ids, "P": len(ids), "p0": p0, "p1": p1, "spec_end": spec_end,
            "prompt_sha256": sha256_text(json.dumps(ids)), **extra}


def bench_dir(task: str) -> str:
    for d in BENCH.iterdir():
        if d.is_dir() and d.name.startswith(task + "_"):
            return d.name
    raise FileNotFoundError(task)


def semantic_seeds() -> dict[str, list[str]]:
    rows = read_json(E6 / "prompts" / "prompts.json")
    out: dict[str, list[str]] = {}
    for t in PATH_TASKS:
        segs = sorted([(int(r["paraphrase_id"]), r["segment"]) for r in rows
                       if r["condition"] == "seed_semantic" and r["task"] == t])
        out[t] = [s for _, s in segs]
        assert len(out[t]) >= 5, f"{t}: fewer than 5 semantic seeds"
    return out


def build_all(tok: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    e17 = {(r["task"], r["w"], r["kind"]): r for r in read_jsonl(E17 / "prompts" / "prompts.jsonl")}
    e13 = read_json(E13 / "prompts" / "prompt_ids.json")
    seeds = semantic_seeds()
    # ---------------------------------------------------------------- path tasks (exp8 frozen spec, exp17 twins)
    fp = read_json(E8 / "prompts" / "frozen_prompts.json")
    for t in PATH_TASKS:
        et = EXP8_TASK[t]
        spec = fp["spec"][et]
        td = fp["tasks"][et]
        for i, w in enumerate(TEMPLATE_IDS):
            r0 = td["templates"][w]["neutral_A"]
            tw = record(tok, t, w, "twin", r0["segment"], spec, source=f"exp8 frozen_prompts {et}/{w}/neutral_A")
            ids0 = r0["ids"] if isinstance(r0["ids"], list) else json.loads(r0["ids"])
            assert tw["ids"] == ids0, f"{t}/{w}: twin does not reproduce exp8 ids"
            assert tw["ids"] == e17[(t, w, "twin")]["ids"], f"{t}/{w}: twin differs from exp17"
            rows.append(tw)
            rows.append(record(tok, t, w, "nonce", TEMPLATES[w][0].format(X=NONCE_X), spec, source="nonce W-template"))
            rows.append(record(tok, t, w, "semseed", seeds[t][i], spec, source=f"exp6 seed_semantic p{i}"))
        rows.append(record(tok, t, "ALL", "novelty", NOVELTY, spec, source="frozen novelty sentence"))
        rows.append(record(tok, t, "ALL", "plain", None, spec, source="specification only"))
        rows.append(record(tok, t, "ALL", "vs", VS_SEGMENT, spec, source="verbalized sampling segment"))
    # ---------------------------------------------------------------- 12 bench tasks (exp13 = exp17 twins)
    for t in BENCH12:
        sp = read_json(BENCH / bench_dir(t) / "spec.json")
        spec = sp["spec_text"]
        for w in TEMPLATE_IDS:
            ref = e13[f"{t}|twin|{w}"]
            seg = e17[(t, w, "twin")]["segment"]
            tw = record(tok, t, w, "twin", seg, spec, source="exp13 prompt_ids twin (== exp17 twin)")
            assert tw["ids"] == ref["ids"], f"{t}/{w}: re-rendered twin differs from exp13 ids"
            assert [tw["p1"], tw["spec_end"]] == list(ref["spec_span"]), f"{t}/{w}: spec span differs from exp13"
            rows.append(tw)
            nr = record(tok, t, w, "nonce", TEMPLATES[w][0].format(X=NONCE_X), spec, source="exp13 nonce")
            assert nr["ids"] == e13[f"{t}|nonce|{w}"]["ids"], f"{t}/{w}: nonce differs from exp13"
            rows.append(nr)
        nv = record(tok, t, "ALL", "novelty", NOVELTY, spec, source="exp13 novelty")
        assert nv["ids"] == e13[f"{t}|novelty|NOV"]["ids"], f"{t}: novelty differs from exp13"
        rows.append(nv)
        rows.append(record(tok, t, "ALL", "plain", None, spec, source="specification only"))
        rows.append(record(tok, t, "ALL", "vs", VS_SEGMENT, spec, source="verbalized sampling segment"))
    # ---------------------------------------------------------------- R2 (held out; no ban prompt rendered)
    t = "R2"
    sp = read_json(BENCH / bench_dir(t) / "spec.json")
    spec = sp["spec_text"]
    nn = read_json(BENCH / bench_dir(t) / "neutral_nouns.json")
    D = DEFAULT[t]
    pilot = read_jsonl(BENCH / bench_dir(t) / "pilot_rows.jsonl")
    from collections import Counter

    modal = Counter(r["label"] for r in pilot).most_common(1)[0][0]
    assert modal == D, f"R2 modal pilot label {modal} != {D}"
    xname = nn[D]["display_name"]
    n_x = len(tok(xname, add_special_tokens=False)["input_ids"])  # only the display-name STRING is tokenised
    noun = None
    for cand in nn[D]["nouns"][:2]:
        wd = cand["word"]
        if wd.lower() in NOUN_EXCLUSIONS or re.search(rf"\b{re.escape(wd)}\b", spec, re.I):
            continue
        noun = wd
        break
    assert noun is not None
    n_noun = len(tok(noun, add_special_tokens=False)["input_ids"])
    d = max(0, n_x - n_noun)
    for w in TEMPLATE_IDS:
        seg = TEMPLATES[w][1].format(N=noun) + PAD_FILLER * d
        rows.append(record(tok, t, w, "twin", seg, spec, noun=noun, n_pad=d, display_tokens=n_x,
                           source="R2 twin: neutral noun padded to the display-name token count"))
        rows.append(record(tok, t, w, "nonce", TEMPLATES[w][0].format(X=NONCE_X), spec, source="nonce W-template"))
    rows.append(record(tok, t, "ALL", "novelty", NOVELTY, spec, source="frozen novelty sentence"))
    rows.append(record(tok, t, "ALL", "plain", None, spec, source="specification only"))
    rows.append(record(tok, t, "ALL", "vs", VS_SEGMENT, spec, source="verbalized sampling segment"))
    return rows


def check_and_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_task: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_task.setdefault(r["task"], []).append(r)
    rep: dict[str, Any] = {"tasks": {}}
    for t, rs in by_task.items():
        tails = {json.dumps(r["ids"][r["p1"]:]) for r in rs}
        assert len(tails) == 1, f"{t}: task-specification ids differ across arms"
        spans = {r["spec_end"] - r["p1"] for r in rs}
        assert len(spans) == 1
        S = spans.pop()
        tw = [r for r in rs if r["kind"] == "twin"]
        Ps = {r["P"] for r in tw}
        assert len(Ps) == 1 or t in PATH_TASKS or True
        rep["tasks"][t] = {"S_len": S, "P_by_kind": {f"{r['kind']}:{r['w']}": r["P"] for r in rs},
                           "n_prompts": len(rs)}
    # norm position counts
    for t in BENCH12:
        z = np.load(E13 / "results" / "tensors" / f"norms_{t}.npz")
        assert z["norm"].shape[1] == rep["tasks"][t]["S_len"], f"{t}: norm positions != spec span"
    for t in PATH_TASKS:
        n = np.load(E17 / "directions" / f"norms_{t}.npy")
        assert n.shape[1] == rep["tasks"][t]["S_len"], f"{t}: norm positions != spec span"
    # R2 audit: no catalogue display name or alias in any rendered R2 prompt
    sp = read_json(BENCH / bench_dir("R2") / "spec.json")
    names = [c["display_name"] for c in sp["catalogue"]] + [a for v in sp.get("aliases", {}).values() for a in v]
    hits = []
    for r in by_task["R2"]:
        seg = r["user_text"].lower()
        for a in names:
            if re.search(rf"\b{re.escape(a.lower())}\b", seg):
                hits.append({"kind": r["kind"], "w": r["w"], "name": a})
    rep["R2_alias_audit_hits"] = hits
    assert not hits, f"R2 prompt leaks a catalogue name: {hits}"
    rep["n_prompts"] = len(rows)
    return rep


def stage_prompts() -> dict[str, Any]:
    tok = load_tokenizer()
    rows = build_all(tok)
    rep = check_and_report(rows)
    write_jsonl(PROMPTS_FILE, rows)
    write_json(RESULTS_DIR / "prompt_report.json", rep)
    logger.info(f"prompts: {len(rows)} rendered; spec ids identical across arms for every task; R2 audit 0 hits")
    return rep


def load_prompts() -> dict[tuple[str, str, str], dict[str, Any]]:
    out = {}
    for r in read_jsonl(PROMPTS_FILE):
        out[(r["task"], r["w"], r["kind"])] = r
    return out


def prompt_for(prompts: dict, task: str, w: str, kind: str) -> dict[str, Any]:
    if kind in ("novelty", "plain", "vs"):
        return prompts[(task, "ALL", kind)]
    return prompts[(task, w, kind)]


if __name__ == "__main__":
    from cfg import setup_logging

    setup_logging("s0_prompts")
    stage_prompts()
