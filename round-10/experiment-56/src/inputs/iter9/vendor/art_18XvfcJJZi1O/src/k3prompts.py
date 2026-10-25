#!/usr/bin/env python3
"""Prompts, contrasts and position classes for K3 (CPU; needs the Qwen3 tokenizer).

C1-nat    B3 (minimum spanning tree weight) neutral-noun variants of the iteration-5 twin: the twin noun ('house'/
          'House') is replaced by single-token neutral nouns of the art_j3Rm_lr2nzR6 noun bank (concreteness_norms,
          metadata_noun_bank_candidate), 24 per template W1-W5; ids identical everywhere except the noun position.
          Teacher-forced canonical opening O (61 tokens, art_MZAfDPVhM6Ui forks.json); metric m = z(' Kr') - z(' Prim')
          at the last opening position. Pairs: within each template the k-th highest m (clean) vs the k-th lowest
          (corrupt); set A k = 1..3, set B k = 4..6; held-out H = 2 per template from the remaining variants.
C1-forced five forced-Prim paraphrases (corrupt) against their ' .' padding twins (clean), same length and ids from
          'Task:' on (iteration-6 pad_record rule).
C2a       T10 (connected components) twin noun variants (clean) against the same prompts with the forced-DFS prompt's
          residual states exchanged in at the task-spec positions [p1, spec_end) of every block (corrupt);
          teacher-forced T10 prefix '```python\\ndef solve(n, edges):\\n    def'; m = z(' find') - z(' dfs').
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np

from k3cfg import (E34, E35, EXCLUDED_NOUNS, NOUN_BANK, SEED_HELDOUT, TEMPLATE_TAIL, TEMPLATES, read_json,
                   read_jsonl, sha256_text)

FORCED_PRIM = (
    "Implement Prim's algorithm with a heap for this task.",
    "Use Prim's algorithm with a priority queue for this task.",
    "Solve this task with Prim's algorithm.",
    "Your solution must use Prim's algorithm.",
    "Write a solution based on Prim's algorithm with a heap.",
    # amendment 0a (F2: C1-nat mean TE < 1 nat -> C1-forced primary, expanded to 10 pairs + 5 held-out pairs)
    "Use Prim's minimum spanning tree algorithm.",
    "Please solve it using Prim's algorithm.",
    "The solution should grow the tree with Prim's algorithm.",
    "Apply Prim's algorithm to build the spanning tree.",
    "Implement this with Prim's algorithm and a binary heap.",
    "Use Prim's algorithm here.",
    "Base your function on Prim's algorithm.",
    "Solve it with Prim's algorithm using heapq.",
    "Write the function using Prim's algorithm.",
    "You must implement Prim's algorithm.",
)
FORCED_DFS = "Implement depth-first search (DFS) for this task."


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
    return len(head), p1, len(ids) - len(tail)


def _prompts7() -> dict[tuple[str, str, str], dict[str, Any]]:
    return {(r["unit"], r["w"], r["kind"]): r for r in read_jsonl(E35 / "prompts" / "prompts7.jsonl")}


def b3_opening() -> list[int]:
    return list(read_json(E35 / "results" / "forks.json")["B3"]["opening"]["O"])


def t10_prefix() -> list[int]:
    t = read_json(E34 / "results" / "forks.json")["tasks"]["T10"]
    o = json.loads(t["opening_ids"]) if isinstance(t["opening_ids"], str) else t["opening_ids"]
    f = int(t["forks"][0])
    def_id = int(t["default_token_at_fork"][str(f)]["id"])
    return list(o[:f]) + [def_id]


def classes(P: int, p0: int, p1: int, L_open: int) -> dict[str, list[int]]:
    return {"COND": list(range(p0, p1)), "SPEC": list(range(0, p0)) + list(range(p1, P)),
            "OPEN": list(range(P, P + L_open - 1)), "DEC": [P + L_open - 1]}


def rec(unit: str, w: str, kind: str, ids: list[int], p0: int, p1: int, se: int, L_open: int,
        **extra: Any) -> dict[str, Any]:
    P = len(ids)
    return {"unit": unit, "template": w, "kind": kind, "ids": list(ids), "P": P, "p0": p0, "p1": p1, "spec_end": se,
            "L_open": L_open, "pos": classes(P, p0, p1, L_open), "prompt_sha256": sha256_text(json.dumps(list(ids))),
            **extra}


def noun_bank(tok: Any) -> list[str]:
    """Single-token neutral nouns (both ' noun' and 'Noun' single Qwen3 tokens), by SUBTLEX frequency, minus task-
    related words."""
    rows = read_json(NOUN_BANK)["rows"]
    out = []
    for r in sorted(rows, key=lambda r: (-r["subtlex"], r["word"])):
        w = r["word"]
        if w in EXCLUDED_NOUNS or not w.isalpha() or not w.islower():
            continue
        if len(tok(" " + w, add_special_tokens=False)["input_ids"]) != 1:
            continue
        if len(tok(w.capitalize(), add_special_tokens=False)["input_ids"]) != 1:
            continue
        out.append(w)
    return out


def _noun_pos(tok: Any, ids: list[int], p0: int, p1: int, noun: str) -> tuple[int, bool]:
    t_sp = tok(" " + noun, add_special_tokens=False)["input_ids"][0]
    t_cap = tok(noun.capitalize(), add_special_tokens=False)["input_ids"][0]
    for i in range(p0, p1):
        if ids[i] == t_sp:
            return i, False
        if ids[i] == t_cap:
            return i, True
    raise ValueError(f"noun {noun!r} not found in condition span")


def splice(tok: Any, base: dict[str, Any], base_noun: str, noun: str, unit: str, L_open: int,
           spec: str) -> dict[str, Any]:
    i, cap = _noun_pos(tok, base["ids"], base["p0"], base["p1"], base_noun)
    new_tok = tok((noun.capitalize() if cap else " " + noun), add_special_tokens=False)["input_ids"]
    assert len(new_tok) == 1
    ids = list(base["ids"])
    ids[i] = new_tok[0]
    # re-tokenisation check: the spliced ids equal the chat template applied to the decoded user text
    user = tok.decode(ids[base["p0"]:base["spec_end"]])
    assert chat_ids(tok, user) == ids, f"splice of {noun!r} does not re-tokenise identically"
    return rec(unit, base["template"], "variant", ids, base["p0"], base["p1"], base["spec_end"], L_open,
               noun=noun, noun_pos=i, vid=f"{base['template']}|{noun}")


def b3_twins(tok: Any) -> dict[str, dict[str, Any]]:
    P7 = _prompts7()
    out = {}
    for w in TEMPLATES:
        r = P7[("B3", w, "twin")]
        out[w] = rec("B3", w, "twin", r["ids"], r["p0"], r["p1"], r["spec_end"], 61, noun="house", vid=f"{w}|house")
    return out


def t10_twins(tok: Any) -> dict[str, dict[str, Any]]:
    P7 = _prompts7()
    L = len(t10_prefix())
    return {w: rec("T10", w, "twin", P7[("T10", w, "twin")]["ids"], P7[("T10", w, "twin")]["p0"],
                   P7[("T10", w, "twin")]["p1"], P7[("T10", w, "twin")]["spec_end"], L, noun="ship",
                   vid=f"{w}|ship") for w in TEMPLATES}


def spec_text(tok: Any, r: dict[str, Any]) -> str:
    return tok.decode(r["ids"][r["p1"]:r["spec_end"]])


def b3_variants(tok: Any, nouns: list[str], n_per: int = 24) -> list[dict[str, Any]]:
    tw = b3_twins(tok)
    spec = spec_text(tok, tw["W1"])
    out = []
    for w in TEMPLATES:
        for nn in nouns[:n_per]:
            out.append(splice(tok, tw[w], "house", nn, "B3", 61, spec))
    return out


def t10_variants(tok: Any, nouns: list[str]) -> list[dict[str, Any]]:
    tw = t10_twins(tok)
    spec = spec_text(tok, tw["W1"])
    L = len(t10_prefix())
    out = []
    for w in TEMPLATES:
        for nn in nouns:
            if nn == "ship":
                out.append(dict(tw[w], kind="variant"))
            else:
                out.append(splice(tok, tw[w], "ship", nn, "T10", L, spec))
    return out


def pad_twin(tok: Any, src: dict[str, Any]) -> dict[str, Any]:
    """Iteration-6 pad_record: the condition tokens [p0, k) replaced by ' .' (k = p1 minus the blank-line tokens)."""
    dot = tok(" .", add_special_tokens=False)["input_ids"]
    assert len(dot) == 1
    ids = list(src["ids"])
    c0, k = src["p0"], src["p1"]
    while k > c0 and "\n" in tok.decode([ids[k - 1]]):
        k -= 1
    for i in range(c0, k):
        ids[i] = dot[0]
    return rec(src["unit"], src["template"], "forced_pad", ids, src["p0"], src["p1"], src["spec_end"], src["L_open"],
               vid=src["vid"] + "|pad", cond_span=[c0, k])


def b3_forced(tok: Any) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    tw = b3_twins(tok)
    spec = spec_text(tok, tw["W1"])
    out = []
    for j, seg in enumerate(FORCED_PRIM):
        ids = chat_ids(tok, seg + "\n\n" + spec)
        p0, p1, se = positions(tok, ids, spec)
        f = rec("B3", f"F{j + 1}", "forced", ids, p0, p1, se, 61, vid=f"F{j + 1}|forced", segment=seg)
        out.append((pad_twin(tok, f), f))
    return out


def t10_forced_dfs(tok: Any) -> dict[str, Any]:
    tw = t10_twins(tok)
    spec = spec_text(tok, tw["W1"])
    ids = chat_ids(tok, FORCED_DFS + "\n\n" + spec)
    p0, p1, se = positions(tok, ids, spec)
    return rec("T10", "F", "forced", ids, p0, p1, se, len(t10_prefix()), vid="F|forced_dfs", segment=FORCED_DFS)


def t10_ban(tok: Any) -> dict[str, dict[str, Any]]:
    """C2b: the iteration-6 ban prompts ('Do not use union-find (disjoint set union) ...'), W1-W3."""
    L = len(t10_prefix())
    out = {}
    for r in read_jsonl(E35.parent / "iter6_exp30" / "prompts" / "prompts6.jsonl"):
        if r["task"] == "T10" and r["kind"] == "ban" and r["w"] in ("W1", "W2", "W3"):
            out[r["w"]] = rec("T10", r["w"], "ban", r["ids"], 3, r["p1"], r["spec_end"], L, vid=f"{r['w']}|ban")
    return out


def pair_by_rank(variants: list[dict[str, Any]], m: dict[str, float], ks: tuple[int, ...]) -> list[tuple[str, str]]:
    """Within each template: the k-th highest m (clean) with the k-th lowest (corrupt), k in ks (1-based)."""
    out = []
    for w in TEMPLATES:
        vs = sorted([v["vid"] for v in variants if v["template"] == w], key=lambda k: -m[k])
        for k in ks:
            out.append((vs[k - 1], vs[-k]))
    return out


def heldout(variants: list[dict[str, Any]], m: dict[str, float], used: set[str], n_per: int = 2,
            seed: int = SEED_HELDOUT) -> list[tuple[str, str]]:
    """2 per template from the remaining variants: one above and one below the template median (seed 8301).
    Returns (vid, side) with side 'clean' (above the median, Kruskal-leaning) or 'corrupt'."""
    rng = np.random.default_rng(seed)
    out = []
    for w in TEMPLATES:
        allw = [v["vid"] for v in variants if v["template"] == w]
        med = float(np.median([m[k] for k in allw]))
        rest = [k for k in allw if k not in used]
        hi = sorted([k for k in rest if m[k] > med])
        lo = sorted([k for k in rest if m[k] <= med])
        if hi:
            out.append((hi[int(rng.integers(len(hi)))], "clean"))
        if lo and n_per > 1:
            out.append((lo[int(rng.integers(len(lo)))], "corrupt"))
    return out
