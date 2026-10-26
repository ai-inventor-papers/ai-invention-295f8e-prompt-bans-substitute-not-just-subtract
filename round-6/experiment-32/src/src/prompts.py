#!/usr/bin/env python3
"""S1: every prompt, rendered with Qwen2.5's own chat template (its default system message; no system message
passed), add_generation_prompt=True.

Kinds (condition segment + blank line + frozen task specification):
  twin     W1-W5 neutral twin. Bench tasks: the exp11 bench neutral noun of the PRIOR default (cfg.PRIOR_DEFAULT),
           ' .'-padded to the token length of the prior default's ban (protocol v2). Path tasks: exp8's frozen
           neutral_A segments (already token-matched to the BFS / Dijkstra ban).
  ban      W1-W5 ban of mode Y with Y's spec display name (rendered in S3 once this model's default is known). If its
           condition span is shorter than the twin's it is ' .'-padded to equal length (logged).
  forced   'Implement Y' paraphrases 1-5 (bench spec forced_templates; exp8 forced paraphrases for T1/T2).
  seed     T2 only: exp6's semantic-seed paragraphs p0-p4 (W1 -> p0 ... W5 -> p4).
Assertions: the ids from the first 'Task:' token to the end are identical across every kind of a task; the chat
tail is the 5-token Qwen2.5 assistant header; SPEC-1..3 are user-content tokens.
"""

from __future__ import annotations

import json
import re
from typing import Any

from loguru import logger

from cfg import (BENCH, E6, E8, MODEL_ID, MODEL_REVISION, N_FORCED_PARAPHRASES, PAD_FILLER, PATH_TASKS,
                 POS_OFFSET, PRIOR_DEFAULT, TASKS, TEMPLATE_IDS, TEMPLATE_TAIL, TEMPLATES, bench_dir, cap_first,
                 model_path, read_json, sha256_text)

NOUN_EXCLUSIONS = {"ass", "bucket", "chain", "edge", "game", "graph", "grid", "head", "heap", "key", "line", "link",
                   "list", "map", "maze", "net", "node", "path", "point", "queue", "ring", "road", "route", "search",
                   "stack", "step", "street", "table", "track", "train", "tree", "walk", "way", "web"}

# alias lexicon for the path tasks (display names + common names; frozen with commit #2)
PATH_ALIASES = {
    "T1": {"bfs": ["breadth-first", "breadth first", "bfs"], "dfs": ["depth-first", "depth first", "dfs"],
           "bibfs": ["bidirectional bfs", "bidirectional breadth", "bi-directional bfs", "bidirectional search"],
           "iddfs": ["iterative deepening", "iddfs", "depth-limited"],
           "astar_gbfs": ["a*", "a-star", "astar", "a star", "greedy best-first", "best-first", "manhattan heuristic"],
           "dijkstra": ["dijkstra", "uniform-cost", "uniform cost"]},
    "T2": {"dijkstra": ["dijkstra", "priority queue of distances"],
           "bf_spfa": ["bellman-ford", "bellman ford", "bellmanford", "spfa", "shortest path faster", "relaxation rounds"],
           "bidijkstra": ["bidirectional dijkstra", "bi-directional dijkstra", "two-way dijkstra"],
           "floyd": ["floyd-warshall", "floyd warshall", "floyd", "warshall", "all-pairs"],
           "dial": ["dial's", "dial ", "bucket queue", "bucket-queue", "buckets indexed by distance"]},
}


def load_tokenizer():
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(model_path(MODEL_ID, MODEL_REVISION))


def chat_ids(tok: Any, user_text: str) -> list[int]:
    ids = tok.apply_chat_template([{"role": "user", "content": user_text}], tokenize=True,
                                  add_generation_prompt=True)
    if isinstance(ids, dict):
        ids = ids["input_ids"]
    return list(ids)


def spec_text(task: str) -> str:
    if task in PATH_TASKS:
        return read_json(E8 / "prompts" / "frozen_prompts.json")["spec"][task.lower()]
    return read_json(BENCH / bench_dir(task) / "spec.json")["spec_text"]


def positions(tok: Any, ids: list[int], spec: str) -> dict[str, int]:
    suf = tok(spec + TEMPLATE_TAIL, add_special_tokens=False)["input_ids"]
    p1 = len(ids) - len(suf)
    assert ids[p1:] == suf, "SPEC + template tail do not tokenize identically in context"
    tail = tok(TEMPLATE_TAIL, add_special_tokens=False)["input_ids"]
    assert len(tail) == 5 and ids[len(ids) - 5:] == tail, f"unexpected chat tail {tail}"
    head = tok("<|im_start|>user\n", add_special_tokens=False)["input_ids"]
    p0 = None
    for i in range(len(ids) - len(head)):
        if ids[i:i + len(head)] == head:
            p0 = i + len(head)
            break
    assert p0 is not None, "no user header"
    return {"p0": p0, "p1": p1, "spec_end": len(ids) - 5}


def record(tok: Any, task: str, kind: str, w: str, segment: str | None, spec: str, **extra: Any) -> dict[str, Any]:
    seg = cap_first(segment) if segment else ""
    text = (seg + "\n\n" + spec) if segment else spec
    ids = chat_ids(tok, text)
    pos = positions(tok, ids, spec)
    P = len(ids)
    pos_idx = {k: P - off for k, off in POS_OFFSET.items()}
    return {"task": task, "kind": kind, "w": w, "segment": seg, "user_text": text, "ids": ids, "P": P, **pos,
            "cond_len": pos["p1"] - pos["p0"], "pos_idx": pos_idx, "prompt_sha256": sha256_text(json.dumps(ids)),
            **extra}


# ------------------------------------------------------------------------------------------------ catalogue
def catalogue(task: str) -> list[dict[str, Any]]:
    """[{mode, display_name, mechanism, aliases}] per task (spec catalogue for bench tasks; exp8 for path tasks)."""
    if task in PATH_TASKS:
        import sys

        from cfg import SUITE
        if str(SUITE) not in sys.path:
            sys.path.insert(0, str(SUITE))
        fp = read_json(E8 / "prompts" / "frozen_prompts.json")
        disp = fp["display"][task.lower()]
        from common import MODE_DEFINITIONS  # exp8 suite common.py
        out = []
        for m, d in disp.items():
            out.append({"mode": m, "display_name": d, "mechanism": MODE_DEFINITIONS[task.lower()][m],
                        "aliases": PATH_ALIASES[task][m]})
        return out
    sp = read_json(BENCH / bench_dir(task) / "spec.json")
    return [{"mode": c["mode"], "display_name": c["display_name"], "mechanism": c["mechanism"],
             "aliases": sp.get("aliases", {}).get(c["mode"], [])} for c in sp["catalogue"]]


def display_name(task: str, mode: str) -> str:
    for c in catalogue(task):
        if c["mode"] == mode:
            return c["display_name"]
    raise KeyError((task, mode))


# ------------------------------------------------------------------------------------------------ builders
def _pad_to(tok: Any, task: str, kind: str, w: str, seg: str, spec: str, target_P: int, **extra: Any
            ) -> dict[str, Any]:
    r = record(tok, task, kind, w, seg, spec, **extra, n_pad=0)
    d = target_P - r["P"]
    if d <= 0:
        return r
    for extra_d in range(0, 3):
        seg2 = seg + PAD_FILLER * (d + extra_d)
        r2 = record(tok, task, kind, w, seg2, spec, **extra, n_pad=d + extra_d)
        if r2["P"] == target_P:
            return r2
    return r


def twin(tok: Any, task: str, w: str) -> dict[str, Any]:
    spec = spec_text(task)
    if task in PATH_TASKS:
        fp = read_json(E8 / "prompts" / "frozen_prompts.json")
        seg = fp["tasks"][task.lower()]["templates"][w]["neutral_A"]["segment"]
        r = record(tok, task, "twin", w, seg, spec, noun=fp["tasks"][task.lower()]["templates"][w]["neutral_A"]["noun"],
                   n_pad=0, source="exp8 frozen neutral_A")
        bn = ban(tok, task, w, PRIOR_DEFAULT[task], pad_to=None)
        assert r["P"] == bn["P"], f"{task}/{w}: exp8 twin not token-matched to the prior-default ban under Qwen2.5"
        return r
    nn = read_json(BENCH / bench_dir(task) / "neutral_nouns.json")
    D = PRIOR_DEFAULT[task]
    noun = None
    for cand in nn[D]["nouns"]:
        wd = cand["word"]
        if wd.lower() in NOUN_EXCLUSIONS or re.search(rf"\b{re.escape(wd)}\b", spec, re.I):
            continue
        noun = wd
        break
    assert noun is not None, f"{task}: no neutral noun"
    bn = ban(tok, task, w, D, pad_to=None)
    seg = TEMPLATES[w][1].format(N=noun)
    r = _pad_to(tok, task, "twin", w, seg, spec, bn["P"], noun=noun, source="bench neutral noun + ' .' padding")
    assert r["P"] == bn["P"], f"{task}/{w}: twin could not be padded to the ban length"
    return r


def ban(tok: Any, task: str, w: str, mode: str, pad_to: int | None) -> dict[str, Any]:
    spec = spec_text(task)
    X = display_name(task, mode)
    seg = TEMPLATES[w][0].format(X=X)
    if pad_to is None:
        return record(tok, task, "ban", w, seg, spec, mode=mode, n_pad=0, source="W-template ban")
    return _pad_to(tok, task, "ban", w, seg, spec, pad_to, mode=mode, source="W-template ban (padded to twin)")


def forced(tok: Any, task: str, mode: str) -> list[dict[str, Any]]:
    spec = spec_text(task)
    out = []
    if task in PATH_TASKS:
        fp = read_json(E8 / "prompts" / "frozen_prompts.json")
        par = fp["tasks"][task.lower()]["forced"][mode]["paraphrases"][:N_FORCED_PARAPHRASES]
        for i, p in enumerate(par):
            out.append(record(tok, task, "forced", f"W{i + 1}", p["segment"], spec, mode=mode, paraphrase=i,
                              source="exp8 forced paraphrase"))
        return out
    sp = read_json(BENCH / bench_dir(task) / "spec.json")
    X = display_name(task, mode)
    for i, tpl in enumerate(sp["forced_templates"][:N_FORCED_PARAPHRASES]):
        out.append(record(tok, task, "forced", f"W{i + 1}", tpl.format(j=X), spec, mode=mode, paraphrase=i,
                          source="bench forced_templates"))
    return out


def seed(tok: Any, task: str = "T2") -> list[dict[str, Any]]:
    rows = read_json(E6 / "prompts" / "prompts.json")
    segs = sorted([(int(r["paraphrase_id"]), r["segment"]) for r in rows
                   if r["condition"] == "seed_semantic" and r["task"] == task])
    spec = spec_text(task)
    return [record(tok, task, "seed", f"W{i + 1}", s, spec, paraphrase=i, source=f"exp6 seed_semantic p{i}")
            for i, (_, s) in enumerate(segs[:5])]


def check_tail_identity(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by.setdefault(r["task"], []).append(r)
    rep = {}
    for t, rs in by.items():
        tails = {json.dumps(r["ids"][r["p1"]:]) for r in rs}
        assert len(tails) == 1, f"{t}: task-specification ids differ across kinds"
        rep[t] = {"spec_plus_tail_tokens": len(rs[0]["ids"]) - rs[0]["p1"],
                  "P_by_kind": {f"{r['kind']}:{r['w']}:{r.get('mode', '')}": r["P"] for r in rs}}
    return rep


def build_static(tok: Any) -> list[dict[str, Any]]:
    """Twin, forced (all catalogue modes) and seed prompts; bans are rendered in S3."""
    rows = []
    for t in TASKS:
        for w in TEMPLATE_IDS:
            rows.append(twin(tok, t, w))
        for c in catalogue(t):
            rows += forced(tok, t, c["mode"])
    rows += seed(tok, "T2")
    return rows


def describe_positions(tok: Any, r: dict[str, Any]) -> dict[str, str]:
    return {k: tok.decode([r["ids"][i]]) for k, i in r["pos_idx"].items()}


if __name__ == "__main__":
    from cfg import setup_logging

    setup_logging("prompts")
    tk = load_tokenizer()
    rs = build_static(tk)
    logger.info(f"{len(rs)} static prompts; positions {describe_positions(tk, rs[0])}")
    logger.info(json.dumps(check_tail_identity(rs))[:2000])
