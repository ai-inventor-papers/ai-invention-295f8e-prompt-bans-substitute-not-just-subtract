#!/usr/bin/env python3
"""Prompt records for iteration 7. Every record: {pid, task, kind, X, w, ids, P, p0, p1, spec_end, prompt_sha256}.

Sources (all frozen; nothing re-worded here):
  twin / ban W1-W5          exp22 prompts4.jsonl (== exp30 prompts6 twin/ban, sha256-identical, checked in S2)
  named (forced) prompts    exp22 prompts4.jsonl 'named' = 10 forced frames F0-F9 x 3 display-name variants per
                            catalogue algorithm (T2 bf_spfa F0 v0 == exp30's FORCED prompt, T10 bfs F0 v0 == exp30's
                            T10 FORCED prompt, sha256-identical)
  T1 10-algorithm forced    exp9 frozen_prompts.json tasks.t1.conditions['forced:X'] (10 paraphrases each), built in
                            the same chat frame as prompts4 (chat template, thinking off; rebuild checked on prompts4)
  T1 top5ban W1-W5          exp30 prompts6.jsonl
  padding twins             exp30 gpu6.pad_record rule: the condition segment's tokens [p0, k) -> ' .' (k = p1 minus
                            the blank-line tokens), same length, identical ids from 'Task:' on
S = [p1, spec_end): the task-spec positions ('Task:' to the last user token); offsets j = position - p1 align S
across prompts of one task because the spec text (and so its ids) is identical.
"""

from __future__ import annotations

import json
from typing import Any

from c7 import V22, V30, V9, read_jsonl, sha256_text

P4_FILE = V22 / "prompts" / "prompts4.jsonl"
P6_FILE = V30 / "prompts" / "prompts6.jsonl"
E9_FROZEN = V9 / "prompts" / "frozen_prompts.json"
T1_CAT10 = ["bfs", "dfs", "bibfs", "iddfs", "astar", "gbfs", "dijkstra_unit", "idastar", "jps", "biastar"]
T1_TOP5 = ["bfs", "dfs", "iddfs", "astar", "gbfs"]
T1_SURV = ["bibfs", "dijkstra_unit", "idastar", "jps", "biastar"]
_CACHE: dict[str, Any] = {}


def p4() -> dict[str, dict[str, Any]]:
    if "p4" not in _CACHE:
        rows = read_jsonl(P4_FILE)
        for r in rows:
            r["w"] = r.get("template_id")
        _CACHE["p4"] = {r["pid"]: r for r in rows}
    return _CACHE["p4"]


def twin(task: str, w: str) -> dict[str, Any]:
    return p4()[f"{task}|twin|-|{w}|-"]


def ban(task: str, w: str) -> dict[str, Any]:
    from c7 import DEFAULTS
    return p4()[f"{task}|ban|{DEFAULTS[task]}|{w}|-"]


def named(task: str, X: str, F: int, nv: int = 0) -> dict[str, Any]:
    return p4()[f"{task}|named|{X}|F{F}|{nv}"]


def named_list(task: str, X: str, n_frames: int = 10, nv: int = 0) -> list[dict[str, Any]]:
    return [named(task, X, F, nv) for F in range(n_frames) if f"{task}|named|{X}|F{F}|{nv}" in p4()]


def p6(task: str, kind: str, w: str) -> dict[str, Any]:
    if "p6" not in _CACHE:
        _CACHE["p6"] = {(r["task"], r["kind"], r["w"]): r for r in read_jsonl(P6_FILE)}
    r = dict(_CACHE["p6"][(task, kind, w)])
    r.setdefault("pid", f"{task}|{kind}|-|{w}|p6")
    r.setdefault("p0", 3)
    return r


def pad_record(tok: Any, src: dict[str, Any]) -> dict[str, Any]:
    """exp30 gpu6.pad_record: tokens [p0, k) -> ' .', where k = p1 minus the trailing blank-line tokens."""
    dot = tok(" .", add_special_tokens=False)["input_ids"]
    assert len(dot) == 1
    ids = list(src["ids"])
    c0, k = src["p0"], src["p1"]
    while k > c0 and "\n" in tok.decode([ids[k - 1]]):
        k -= 1
    for i in range(c0, k):
        ids[i] = dot[0]
    return {"pid": src["pid"] + "|pad", "task": src["task"], "kind": src["kind"] + "_pad", "X": src.get("X"),
            "w": src.get("w"), "ids": ids, "P": len(ids), "p0": c0, "p1": src["p1"], "spec_end": src["spec_end"],
            "cond": [c0, k], "prompt_sha256": sha256_text(json.dumps(ids)), "source": f"padding twin of {src['pid']}"}


def chat_ids(tok: Any, user_text: str) -> list[int]:
    s = tok.apply_chat_template([{"role": "user", "content": user_text}], tokenize=False,
                                add_generation_prompt=True, enable_thinking=False)
    return tok(s, add_special_tokens=False)["input_ids"]


def positions(tok: Any, ids: list[int], ref: dict[str, Any]) -> tuple[int, int, int]:
    """(p0, p1, spec_end) of a prompt whose spec is identical to `ref`'s: align the spec ids by their suffix."""
    spec_ids = ref["ids"][ref["p1"]:ref["spec_end"]]
    tail = ref["ids"][ref["spec_end"]:]
    n = len(ids)
    assert ids[n - len(tail):] == tail, "chat tail differs from the reference prompt"
    se = n - len(tail)
    p1 = se - len(spec_ids)
    assert ids[p1:se] == spec_ids, "spec ids differ from the reference prompt"
    return ref["p0"], p1, se


def t1_forced(tok: Any, n_para: int = 10) -> list[dict[str, Any]]:
    """exp9 frozen forced prompts for the 10-algorithm T1 catalogue (plain 'forced:X' condition), prompts4 frame."""
    fp = json.loads(E9_FROZEN.read_text())
    ref = twin("T1", "W1")
    out = []
    for X in T1_CAT10:
        for e in fp["tasks"]["t1"]["conditions"][f"forced:{X}"][:n_para]:
            ids = chat_ids(tok, e["prompt"])
            p0, p1, se = positions(tok, ids, ref)
            out.append({"pid": f"T1|forced9|{X}|{e['paraphrase_id']}|-", "task": "T1", "kind": "forced9", "X": X,
                        "w": f"F{e['paraphrase_id']}", "ids": ids, "P": len(ids), "p0": p0, "p1": p1,
                        "spec_end": se, "segment": e["segment"], "prompt_sha256": sha256_text(json.dumps(ids)),
                        "source": "exp9 frozen_prompts forced:X"})
    return out


def check_rebuild(tok: Any) -> dict[str, Any]:
    """C5 support: rebuilding prompts4 records from their user_text reproduces their ids (twin, named, ban)."""
    res = {}
    for pid in ("T1|named|bfs|F0|0", "T2|twin|-|W1|-", "T10|ban|union_find|W3|-", "T03|named|quickselect|F4|0"):
        r = p4()[pid]
        ids = chat_ids(tok, r["user_text"])
        res[pid] = ids == r["ids"]
    return res
