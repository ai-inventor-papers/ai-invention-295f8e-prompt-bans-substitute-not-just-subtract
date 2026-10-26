#!/usr/bin/env python3
"""Unit definitions: exact prompt token ids per template, slot streams, decision nodes (canonical openings) and the
partial-program opening classifiers used by the blind locator.

Prompt sources (sha256-checked copies in inputs/):
  Qwen units   exp35 prompts/prompts7.jsonl, kind 'twin' (the neutral-noun padding twins W1-W5; for T1/T2/T10/T03
               these are byte-identical to exp22 prompts4 / exp34, checked by prompt_sha256)
  G (Gemma)    exp38 fork7.twin(w) rebuilt once by scripts/build_gemma_prompts (prompts/gemma_twin_prompts.json)
Decision nodes (pre-registered from iteration 7, re-measured in Stages 1-2):
  T10  n10: '```python\\ndef solve(n, edges):\\n   ' (10 tokens) -> index 10; n11 = n10 + ' def' -> index 11
       (exp34 forks: ' def' then ' dfs' | ' find'; exp35 collapsed_raw fork_node_index 10)
  T1   '```python\\n' (3 tokens) -> index 3 (exp35 collapsed_raw fork_node_index 3)
  B3   c0 / c1: the two 61-token openings ending in '    #' (exp35 forks.json clusters)
  A3   c0 (18 tokens) / c1 (19 tokens)
  B6   c0 (23 tokens)
  G    c* (32 tokens, iteration-6 Gemma fork.json cstar_ids) -> response index 32
"""

from __future__ import annotations

import re
import sys
from functools import lru_cache
from typing import Any

from cfg8 import E34, E35, E38, PROMPTS_DIR, TEMPLATES, UNITS, read_json, read_jsonl, sha256_text

if str(E35 / "src") not in sys.path:
    sys.path.append(str(E35 / "src"))

import opening_cls as OC  # noqa: E402  (exp35 OC_u, vendored unchanged)

T10_N10 = [73594, 12669, 198, 750, 11625, 1445, 11, 12822, 982, 262]
T10_DEF = 707
T1_OPEN = [73594, 12669, 198]


@lru_cache(maxsize=1)
def qwen_prompts() -> dict[tuple[str, str], dict[str, Any]]:
    out = {}
    for r in read_jsonl(E35 / "prompts" / "prompts7.jsonl"):
        if r["kind"] == "twin":
            out[(r["unit"], r["w"])] = r
    return out


@lru_cache(maxsize=1)
def gemma_prompts() -> dict[str, dict[str, Any]]:
    return read_json(PROMPTS_DIR / "gemma_twin_prompts.json")


def prompt_ids(unit: str, w: str) -> list[int]:
    if UNITS[unit]["model"] == "gemma":
        return list(gemma_prompts()[w]["ids"])
    return list(qwen_prompts()[(unit, w)]["ids"])


def prompt_sha(unit: str, w: str) -> str:
    import json
    return sha256_text(json.dumps(prompt_ids(unit, w)))


@lru_cache(maxsize=1)
def _forks35() -> dict[str, Any]:
    return read_json(E35 / "results" / "forks.json")


@lru_cache(maxsize=1)
def gemma_fork() -> dict[str, Any]:
    return read_json(E38 / "inputs" / "iter6_gemma" / "results" / "fork.json")


def nodes(unit: str) -> list[dict[str, Any]]:
    """Primary decision nodes of a unit: [{'id', 'opening', 'pos'}] (pos = |opening| = generated decision index)."""
    if unit == "T10":
        return [{"id": "n10", "opening": list(T10_N10), "pos": 10}]
    if unit == "T1":
        return [{"id": "n3", "opening": list(T1_OPEN), "pos": 3}]
    if unit in ("B3", "A3", "B6"):
        out = []
        for c in _forks35()[unit]["opening"]["clusters"]:
            out.append({"id": c["id"], "opening": [int(t) for t in c["O"]], "pos": len(c["O"]),
                        "cov_exp35": c.get("cov")})
        return out
    if unit == "G":
        cs = [int(t) for t in gemma_fork()["cstar_ids"]]
        return [{"id": "cstar", "opening": cs, "pos": len(cs)}]
    return []


def second_node(unit: str) -> dict[str, Any] | None:
    """T10's second decision: n11 = n10 + ' def' (index 11)."""
    if unit == "T10":
        return {"id": "n11", "opening": list(T10_N10) + [T10_DEF], "pos": 11, "parent": "n10", "via": T10_DEF}
    return None


# ------------------------------------------------------------------------------------------------ partial classifiers
def _t10(c: str) -> str:
    if re.search(r"\bfind\s*\(|\bunion\s*\(|\bparent\s*\[|\bparent\s*=|\bparents?\s*=\s*\[|UnionFind|\bdsu\b|\bDSU\b",
                 c):
        return "union_find"
    if re.search(r"\bdeque\b|\bqueue\b|\.popleft\s*\(|\bdef\s+bfs\b|\bbfs\s*\(", c):
        return "bfs"
    if re.search(r"\bdef\s+dfs\b|\bdfs\s*\(|\bstack\b|\bdef\s+explore\b|\bdef\s+visit\b", c):
        return "dfs"
    return "undecided"


def classify_partial(unit: str, text: str) -> str:
    """OC_u over a partial program (exp35 rules for B3/A3/B6; a T10 rule added here, validated in Stage 1)."""
    c = OC.strip_comments(OC.code_part(text))
    if unit == "T10":
        return _t10(c)
    if unit in OC.RULES:
        return OC.RULES[unit](c)
    return "undecided"


def source_twin_labels(unit: str) -> dict[int, str]:
    """Per-slot T = 1 labels of the source artifact at this unit's 50 slot streams (for the Stage 0 engine check)."""
    out: dict[int, str] = {}
    if unit in ("B3", "A3", "B6"):
        lab = {r["sid"]: r for r in read_jsonl(E35 / "data" / "labels.jsonl")}
        for s in range(50):
            w, j = TEMPLATES[s // 10], s % 10
            r = lab.get(f"{unit}|SWEEP|T1.0_p1|{w}|{20 + j}")
            if r:
                out[s] = r["label"]
    elif unit in ("T10", "T2", "T03", "T1"):
        raw = read_jsonl(E34 / "data" / "samples_raw.jsonl")
        lab = {}
        for r in read_jsonl(E34 / "data" / "labels.jsonl"):
            lab[(r.get("task"), r.get("block_id"), r.get("sample_id"))] = r
        for r in raw:
            if r["task"] != unit or r["arm"] != "TWIN" or r.get("stage") != "S0a_twin":
                continue
            w, k = r["template"], int(r["slot"].split("|")[-1])
            if k >= 10:
                continue
            L = lab.get((r["task"], r.get("block_id"), r.get("sample_id")))
            if L:
                out[TEMPLATES.index(w) * 10 + k] = L.get("label")
    elif unit == "G":
        lab = {r["row_id"]: r for r in read_jsonl(E38 / "data" / "labels.jsonl") if "row_id" in r}
        for s in range(50):
            w, j = TEMPLATES[s // 10], s % 10
            r = lab.get(f"g3|T1.0|topp1|{w}|{j}")
            if r:
                out[s] = r.get("label")
    return out
