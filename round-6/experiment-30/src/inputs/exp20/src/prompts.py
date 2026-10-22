#!/usr/bin/env python3
"""STEP 1 - prompts and position classes.

Ban / neutral-twin prompts: exp17 prompts/prompts.jsonl (built by exp17 src/prompts.py from the exp8 frozen T1/T2
prompts and the exp11 bench; twins = neutral noun padded with ' .' to the ban's token length). Every prompt is
re-rendered here through the Qwen3 chat template (thinking off) and must reproduce the stored ids.
Forced T1 prompts (C3d geometry): forced sentence + blank line + the identical T1 spec + chat tail.
TOP5 ban prompts (C3d reference points, forward passes only): exp9 session-2 'multi:TOP5' segments, verbatim.
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from cfg import (E17, E7, E9, PRED_DIR, RESULTS_DIR, TASKS, TEMPLATE_IDS, TEMPLATE_TAIL, read_json, sha256_text,
                 write_json)

PROMPTS_FILE = E17 / "prompts" / "prompts.jsonl"

# exp9 session-2 TOP5 literal ban segments (data/raw_session2.jsonl, condition 'multi:TOP5', paraphrase 0), verbatim
TOP5_SEGMENTS = {
    "W1": "Do not use breadth-first search (BFS), depth-first search (DFS), iterative deepening DFS (IDDFS), A* search "
          "or greedy best-first search for this task.",
    "W2": "Your solution must not rely on depth-first search (DFS), iterative deepening DFS (IDDFS), A* search, greedy "
          "best-first search or breadth-first search (BFS).",
    "W3": "Avoid iterative deepening DFS (IDDFS), A* search, greedy best-first search, breadth-first search (BFS) or "
          "depth-first search (DFS) entirely.",
    "W4": "A* search, greedy best-first search, breadth-first search (BFS), depth-first search (DFS) or iterative "
          "deepening DFS (IDDFS) is not allowed here.",
    "W5": "Write a correct solution that does not use greedy best-first search, breadth-first search (BFS), "
          "depth-first search (DFS), iterative deepening DFS (IDDFS) or A* search.",
}
FORCED_ALGS = ["bfs", "dfs", "bibfs", "iddfs", "astar", "gbfs", "dijkstra_unit", "idastar", "jps", "biastar"]
TOP5 = ["bfs", "dfs", "gbfs", "iddfs", "astar"]
SURV = ["bibfs", "dijkstra_unit", "idastar", "jps", "biastar"]
SURV7 = ["bibfs", "idastar"]
ALIASES = {  # display-name variants used to complete the forced sets to 30 (exp9 display name first)
    "bfs": ["breadth-first search (BFS)", "breadth-first search", "BFS"],
    "dfs": ["depth-first search (DFS)", "depth-first search", "DFS"],
    "bibfs": ["bidirectional BFS", "bidirectional breadth-first search", "a bidirectional breadth-first search"],
    "iddfs": ["iterative deepening DFS (IDDFS)", "iterative deepening depth-first search", "IDDFS"],
    "astar": ["A* search", "the A* algorithm", "A* with a Manhattan-distance heuristic"],
    "gbfs": ["greedy best-first search", "greedy best-first search (GBFS)", "a greedy best-first search"],
    "dijkstra_unit": ["unit-weight Dijkstra", "Dijkstra's algorithm with unit edge weights", "unit-cost Dijkstra"],
    "idastar": ["IDA* search", "iterative deepening A* (IDA*)", "IDA*"],
    "jps": ["jump point search", "jump point search (JPS)", "JPS"],
    "biastar": ["bidirectional A* search", "bidirectional A*", "a bidirectional A* search"],
}
FIXED_FRAMES = ["Implement {X} for this task.", "Use {X} to solve this task.", "Solve this with {X}.",
                "Write a solution based on {X}.", "Your solution should use {X}.", "Please implement {X}.",
                "Apply {X} here.", "Use the {X} approach.", "The intended method is {X}.",
                "Code {X} for the following task."]


def cap_first(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


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


def spec_of(rec: dict[str, Any]) -> str:
    return rec["user_text"].split("\n\n", 1)[1]


def load_base(tok: Any) -> dict[tuple[str, str, str], dict[str, Any]]:
    """{(task, w, kind)} for kind in ban/twin; re-rendered and checked; COND span added."""
    out = {}
    with open(PROMPTS_FILE) as fh:
        for line in fh:
            r = json.loads(line)
            if r["task"] not in TASKS:
                continue
            ids = chat_ids(tok, r["user_text"])
            assert ids == r["ids"], f"{r['task']}/{r['w']}/{r['kind']}: re-render mismatch"
            p0, p1, se = positions(tok, ids, spec_of(r))
            assert (p0, p1, se) == (r["p0"], r["p1"], r["spec_end"]), "position mismatch"
            # COND: condition-sentence tokens; a token that is only the blank-line separator is excluded
            cond = [p for p in range(p0, p1) if tok.decode([ids[p]]).strip() != ""]
            r["cond"] = cond
            r["cond_has_merged_sep"] = any("\n\n" in tok.decode([ids[p]]) for p in cond)
            out[(r["task"], r["w"], r["kind"])] = r
    for t in TASKS:
        for w in TEMPLATE_IDS:
            b, n = out[(t, w, "ban")], out[(t, w, "twin")]
            assert b["P"] == n["P"] and b["p1"] == n["p1"] and b["p0"] == n["p0"], f"{t}/{w} not aligned"
            assert b["ids"][b["p1"]:] == n["ids"][n["p1"]:], f"{t}/{w}: S/tail differ"
            diff = [i for i, (x, y) in enumerate(zip(b["ids"], n["ids"])) if x != y]
            assert diff and min(diff) >= b["p0"] and max(diff) < b["p1"], f"{t}/{w}: ids differ outside COND"
            assert n["cond"] == b["cond"] or set(n["cond"]) >= set(diff), f"{t}/{w}: COND misses a differing id"
    return out


def positions_report(tok: Any, pr: dict) -> dict[str, Any]:
    rep = {}
    for (t, w, kind), r in sorted(pr.items()):
        ids = r["ids"]
        rep[f"{t}|{w}|{kind}"] = {
            "P": r["P"], "p0": r["p0"], "p1": r["p1"], "spec_end": r["spec_end"], "R": r["P"] - 1,
            "COND": [r["cond"][0], r["cond"][-1] + 1] if r["cond"] else None, "n_COND": len(r["cond"]),
            "COND_text": tok.decode([ids[p] for p in r["cond"]]), "cond_has_merged_sep": r["cond_has_merged_sep"],
            "S_first_tokens": tok.decode(ids[r["p1"]:r["p1"] + 6]), "S_last_tokens": tok.decode(ids[r["spec_end"] - 6:
                                                                                                  r["spec_end"]]),
            "R_token": tok.decode([ids[r["P"] - 1]]), "n_S": r["spec_end"] - r["p1"]}
    return rep


# ------------------------------------------------------------------------------------------------ C3d prompts
def forced_segments_T1() -> dict[str, list[str]]:
    """30 forced paraphrases per algorithm: exp9 forced/forced_desc sets, exp7 forced (plain/desc) sets, then
    exp9 forced_templates x display-name variants, then the plan's fixed frames; deduplicated, first 30 kept."""
    fp = read_json(E9 / "prompts" / "frozen_prompts.json")
    cond = fp["tasks"]["t1"]["conditions"]
    p7 = read_json(E7 / "prompts" / "prompts_v2.json")["conditions"]
    out: dict[str, list[str]] = {}
    for alg in FORCED_ALGS:
        cands: list[str] = []
        for key in (f"forced:{alg}", f"forced_desc:{alg}"):
            for r in cond.get(key, []):
                cands.append(r["segment"])
        for key, r in sorted(p7.items()):
            if key.startswith(f"t1|forced|{alg}|") and isinstance(r, dict) and r.get("segment"):
                cands.append(r["segment"])
        for tpl in fp["forced_templates"]:
            for name in ALIASES[alg]:
                cands.append(cap_first(tpl.format(X=name)))
        for tpl in FIXED_FRAMES:
            for name in ALIASES[alg]:
                cands.append(cap_first(tpl.format(X=name)))
        seen, keep = set(), []
        for c in cands:
            if c not in seen:
                seen.add(c)
                keep.append(c)
        out[alg] = sorted(keep[:30])
        if len(out[alg]) < 30:
            logger.warning(f"forced {alg}: only {len(out[alg])} paraphrases")
    return out


def build_c3d_prompts(tok: Any, base: dict) -> dict[str, Any]:
    spec = spec_of(base[("T1", "W1", "twin")])
    S_ids = base[("T1", "W1", "twin")]["ids"][base[("T1", "W1", "twin")]["p1"]:base[("T1", "W1", "twin")]["spec_end"]]
    segs = forced_segments_T1()
    forced = []
    for alg, lst in segs.items():
        for i, seg in enumerate(lst):
            text = cap_first(seg) + "\n\n" + spec
            ids = chat_ids(tok, text)
            p0, p1, se = positions(tok, ids, spec)
            assert ids[p1:se] == S_ids, f"forced {alg}/{i}: S ids differ from the twin's"
            forced.append({"alg": alg, "i": i, "segment": seg, "ids": ids, "P": len(ids), "p1": p1, "spec_end": se,
                           "prompt_sha256": sha256_text(json.dumps(ids))})
    top5 = []
    for w, seg in TOP5_SEGMENTS.items():
        text = seg + "\n\n" + spec
        ids = chat_ids(tok, text)
        p0, p1, se = positions(tok, ids, spec)
        assert ids[p1:se] == S_ids
        top5.append({"w": w, "segment": seg, "ids": ids, "P": len(ids), "p1": p1, "spec_end": se,
                     "prompt_sha256": sha256_text(json.dumps(ids))})
    frozen = {"algorithms": FORCED_ALGS, "TOP5": TOP5, "SURV": SURV, "SURV7": SURV7,
              "forced_segments": segs, "n_per_alg": {a: len(v) for a, v in segs.items()},
              "top5_ban_segments": TOP5_SEGMENTS,
              "construction": "exp9 forced:<alg> and forced_desc:<alg> segments, exp7 t1|forced|<alg>|plain/desc "
                              "segments, then exp9 forced_templates x 3 display-name variants, then 10 fixed frames x 3 "
                              "variants; deduplicated in that order, first 30 kept, then sorted"}
    write_json(PRED_DIR / "forced_prompts_T1.json", frozen)
    return {"forced": forced, "top5": top5}


def save_positions(tok: Any, base: dict) -> None:
    write_json(RESULTS_DIR / "positions.json", positions_report(tok, base))
