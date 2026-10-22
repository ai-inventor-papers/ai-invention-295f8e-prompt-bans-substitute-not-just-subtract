#!/usr/bin/env python3
"""Prompts and position classes (exp20 src/prompts.py, unchanged rules) plus the forced-prompt manifold inputs.

- Ban / neutral-twin prompts: exp17 prompts/prompts.jsonl (exp20's input). Every prompt is re-rendered through the
  Qwen3 chat template (thinking off) and must reproduce the stored ids and the stored prompt_sha256 (exp20's).
  Ban prompts are used ONLY as forward passes (r_Q); they are never sampled (GPU test U7 greps the sampling queue).
- COND = condition-sentence tokens (a token that is only the blank-line separator is excluded; a token that merges
  the final '.' with '\\n\\n' is kept, exp20 D3). S = [p1, spec_end). R = P - 1.
- Forced prompts (S-d manifold): T03 and T10 = exp22 prompts4.jsonl 'named' (10 forced_templates x 3 names) and
  'masked' (10 descriptive frames x 3 leak-checked descriptions), 30 + 30 per catalogue algorithm; T1 = exp20's
  predictions/forced_prompts_T1.json (30 named per algorithm over the 10-algorithm extended catalogue) plus exp22's
  T1 masked prompts (6 algorithms). Every forced prompt shares the twin's S token ids (asserted).
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from cfg import E17, E20, E22, RESULTS_DIR, TEMPLATE_IDS, TEMPLATE_TAIL, UNIT_TASKS, read_json, sha256_text, write_json

PROMPTS_FILE = E17 / "prompts" / "prompts.jsonl"
FORCED_T1 = E20 / "predictions" / "forced_prompts_T1.json"
PROMPTS4 = E22 / "prompts" / "prompts4.jsonl"


def cap_first(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def chat_ids(tok: Any, user_text: str, thinking: bool = False) -> list[int]:
    ids = tok.apply_chat_template([{"role": "user", "content": user_text}], tokenize=True,
                                  add_generation_prompt=True, enable_thinking=thinking)
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


def load_base(tok: Any, tasks: tuple[str, ...] = UNIT_TASKS) -> dict[tuple[str, str, str], dict[str, Any]]:
    """{(task, w, kind)} for kind in ban/twin; re-rendered and checked against exp20's ids and sha256."""
    out = {}
    with open(PROMPTS_FILE) as fh:
        for line in fh:
            r = json.loads(line)
            if r["task"] not in tasks:
                continue
            ids = chat_ids(tok, r["user_text"])
            assert ids == r["ids"], f"{r['task']}/{r['w']}/{r['kind']}: re-render mismatch"
            assert sha256_text(json.dumps(ids)) == r["prompt_sha256"], f"{r['task']}/{r['w']}: sha256 mismatch"
            p0, p1, se = positions(tok, ids, spec_of(r))
            assert (p0, p1, se) == (r["p0"], r["p1"], r["spec_end"]), "position mismatch"
            cond = [p for p in range(p0, p1) if tok.decode([ids[p]]).strip() != ""]
            r["cond"] = cond
            r["cond_has_merged_sep"] = any("\n\n" in tok.decode([ids[p]]) for p in cond)
            out[(r["task"], r["w"], r["kind"])] = r
    for t in tasks:
        for w in TEMPLATE_IDS:
            b, n = out[(t, w, "ban")], out[(t, w, "twin")]
            assert b["P"] == n["P"] and b["p1"] == n["p1"] and b["p0"] == n["p0"], f"{t}/{w} not aligned"
            assert b["ids"][b["p1"]:] == n["ids"][n["p1"]:], f"{t}/{w}: S/tail differ"
            diff = [i for i, (x, y) in enumerate(zip(b["ids"], n["ids"])) if x != y]
            assert diff and min(diff) >= b["p0"] and max(diff) < b["p1"], f"{t}/{w}: ids differ outside COND"
    return out


def positions_report(tok: Any, pr: dict) -> dict[str, Any]:
    rep = {}
    for (t, w, kind), r in sorted(pr.items()):
        ids = r["ids"]
        rep[f"{t}|{w}|{kind}"] = {
            "P": r["P"], "p0": r["p0"], "p1": r["p1"], "spec_end": r["spec_end"], "R": r["P"] - 1,
            "COND": [r["cond"][0], r["cond"][-1] + 1] if r["cond"] else None, "n_COND": len(r["cond"]),
            "COND_text": tok.decode([ids[p] for p in r["cond"]]), "cond_has_merged_sep": r["cond_has_merged_sep"],
            "S_first_tokens": tok.decode(ids[r["p1"]:r["p1"] + 6]),
            "S_last_tokens": tok.decode(ids[r["spec_end"] - 6:r["spec_end"]]),
            "R_token": tok.decode([ids[r["P"] - 1]]), "n_S": r["spec_end"] - r["p1"],
            "prompt_sha256": r["prompt_sha256"]}
    return rep


def save_positions(tok: Any, base: dict) -> None:
    write_json(RESULTS_DIR / "positions.json", positions_report(tok, base))


# ------------------------------------------------------------------------------------------------ forced prompts
def forced_prompts(tok: Any, base: dict, task: str) -> list[dict[str, Any]]:
    """Forced 'Implement X' prompts (named) and name-masked twins (masked) for the S-d manifold of `task`."""
    twin = base[(task, "W1", "twin")]
    spec = spec_of(twin)
    S_ids = twin["ids"][twin["p1"]:twin["spec_end"]]
    out: list[dict[str, Any]] = []

    def add(alg: str, kind: str, i: int, segment: str, source: str) -> None:
        text = cap_first(segment) + "\n\n" + spec
        ids = chat_ids(tok, text)
        p0, p1, se = positions(tok, ids, spec)
        assert ids[p1:se] == S_ids, f"forced {task}/{alg}/{kind}/{i}: S ids differ from the twin's"
        out.append({"task": task, "alg": alg, "kind": kind, "i": i, "segment": segment, "ids": ids, "P": len(ids),
                    "p1": p1, "spec_end": se, "source": source, "prompt_sha256": sha256_text(json.dumps(ids))})

    p4 = [json.loads(l) for l in PROMPTS4.read_text().splitlines() if l.strip()]
    if task == "T1":
        fp = read_json(FORCED_T1)
        for alg, segs in fp["forced_segments"].items():
            for i, seg in enumerate(segs):
                add(alg, "named", i, seg, "exp20 predictions/forced_prompts_T1.json")
        for r in p4:
            if r["task"] == "T1" and r["kind"] == "masked":
                add(r["X"], "masked", len([o for o in out if o["alg"] == r["X"] and o["kind"] == "masked"]),
                    r["segment"], "exp22 prompts4.jsonl masked")
    else:
        for kind in ("named", "masked"):
            cnt: dict[str, int] = {}
            for r in p4:
                if r["task"] == task and r["kind"] == kind:
                    i = cnt.get(r["X"], 0)
                    cnt[r["X"]] = i + 1
                    add(r["X"], kind, i, r["segment"], f"exp22 prompts4.jsonl {kind}")
    n = {}
    for o in out:
        n.setdefault(f"{o['alg']}|{o['kind']}", 0)
        n[f"{o['alg']}|{o['kind']}"] += 1
    logger.info(f"forced prompts {task}: {len(out)} ({n})")
    return out
