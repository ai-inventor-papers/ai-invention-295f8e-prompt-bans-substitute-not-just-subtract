#!/usr/bin/env python3
"""S1 prompts (CPU, tokenizer only).

Bench: ids = chat(cap_first(cond) + blank line + spec_text), Qwen3 template with the empty think block (exp8).
cond(ban) = TEMPLATE_w ban with {X} = display_name(D_t); cond(twin) = TEMPLATE_w neutral with {N} = the default's
neutral noun A (twin_A) or B (twin_B), padded with d x ' .' (exp7's frozen rule, d = ban tokens - twin tokens).
Path tasks: ids verbatim from exp8 prompts/frozen_prompts.json (re-derived and asserted equal).
Asserted per (task, w): equal lengths, identical ids from p1 ('Task:') on, identical ids before p0, so every
difference lies inside the condition segment [p0, p1).
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from cfg import (BENCH, E8, FILLER, PATH_TASKS, PROMPTS_DIR, STAGE_A, TASK_DIR, TEMPLATE_IDS, TEMPLATES, cap_first,
                 chat_ids, chat_text, default_of, read_json, sha256_text, write_json, write_jsonl)

PROMPTS_FILE = PROMPTS_DIR / "prompts.jsonl"


def spec(task: str) -> dict[str, Any]:
    return read_json(BENCH / TASK_DIR[task] / "spec.json")


def display_name(task: str, mode: str) -> str:
    for c in spec(task)["catalogue"]:
        if c["mode"] == mode:
            return c["display_name"]
    raise KeyError((task, mode))


def nouns(task: str) -> list[str]:
    nn = read_json(BENCH / TASK_DIR[task] / "neutral_nouns.json")
    return [n["word"] for n in nn[default_of(task)]["nouns"]]


def user_text(task: str, cond: str) -> str:
    return cap_first(cond) + "\n\n" + spec(task)["spec_text"]


def find_p1(tok: Any, chat: str, ids: list[int]) -> int:
    """Index of the first token of 'Task:' (the spec), asserting a clean token boundary there."""
    pos = chat.index("\n\nTask:") + 2
    enc = tok(chat, add_special_tokens=False, return_offsets_mapping=True)
    assert list(enc.input_ids) == ids
    for i, (s, _e) in enumerate(enc.offset_mapping):
        if s >= pos:
            assert s == pos, f"'Task:' does not start a token (token {i} starts at {s}, want {pos})"
            return i
    raise AssertionError("no token at 'Task:'")


def build_bench(tok: Any) -> list[dict[str, Any]]:
    rows = []
    for t in STAGE_A:
        D = default_of(t)
        X = display_name(t, D)
        nA, nB = nouns(t)
        for w in TEMPLATE_IDS:
            ban_cond = TEMPLATES[w][0].replace("{X}", X)
            ban_chat = chat_text(tok, user_text(t, ban_cond))
            ban_ids = chat_ids(tok, user_text(t, ban_cond))
            p1 = find_p1(tok, ban_chat, ban_ids)
            out = {"ban": {"cond": ban_cond, "ids": ban_ids, "noun": None, "pad": 0}}
            for lab, noun in (("twin_A", nA), ("twin_B", nB)):
                base = TEMPLATES[w][2].replace("{N}", noun)
                d = len(ban_ids) - len(chat_ids(tok, user_text(t, base)))
                cond = base + FILLER * max(0, d)
                ids = chat_ids(tok, user_text(t, cond))
                out[lab] = {"cond": cond, "ids": ids, "noun": noun, "pad": max(0, d)}
            P = len(ban_ids)
            p0 = 3
            for lab in ("twin_A", "twin_B"):
                ids = out[lab]["ids"]
                assert len(ids) == P, (t, w, lab, len(ids), P)
                assert ids[p1:] == ban_ids[p1:], (t, w, lab)
                assert ids[:p0] == ban_ids[:p0], (t, w, lab)
                diff = [i for i in range(P) if ids[i] != ban_ids[i]]
                assert diff and min(diff) >= p0 and max(diff) < p1, (t, w, lab, diff, p0, p1)
                assert find_p1(tok, chat_text(tok, user_text(t, out[lab]["cond"])), ids) == p1
            for kind, v in out.items():
                rows.append({"task": t, "w": w, "kind": kind, "noun": v["noun"], "cond": v["cond"], "pad": v["pad"],
                             "ids": v["ids"], "p0": p0, "p1": p1, "P": P,
                             "prompt_sha256": sha256_text(",".join(map(str, v["ids"])))})
    return rows


def build_path(tok: Any) -> list[dict[str, Any]]:
    fp = read_json(E8 / "prompts" / "frozen_prompts.json")
    rows = []
    for t in PATH_TASKS:
        for w in TEMPLATE_IDS:
            tw = fp["tasks"][t]["templates"][w]
            for kind, key in (("ban", "ban"), ("twin_A", "neutral_A"), ("twin_B", "neutral_B")):
                v = tw[key]
                rederived = chat_ids(tok, v["user_text"])
                assert rederived == v["ids"], f"exp8 frozen ids differ on re-derivation: {t} {w} {kind}"
                rows.append({"task": t, "w": w, "kind": kind, "noun": v.get("noun"), "cond": v["segment"], "pad": None,
                             "ids": v["ids"], "p0": v["p0"], "p1": v["p1"], "P": v["P"],
                             "prompt_sha256": sha256_text(",".join(map(str, v["ids"]))),
                             "exp8_ids_sha256": v["ids_sha256"]})
            ban = [r for r in rows if r["task"] == t and r["w"] == w and r["kind"] == "ban"][0]
            for r in rows:
                if r["task"] == t and r["w"] == w and r["kind"] != "ban":
                    assert len(r["ids"]) == ban["P"] and r["ids"][ban["p1"]:] == ban["ids"][ban["p1"]:]
    return rows


def stage_s1(tok: Any) -> dict[str, Any]:
    rows = build_bench(tok) + build_path(tok)
    write_jsonl(PROMPTS_FILE, rows)
    summ = {f"{r['task']}|{r['w']}": {"P": r["P"], "p0": r["p0"], "p1": r["p1"]} for r in rows if r["kind"] == "ban"}
    ex = {f"{r['task']}|{r['w']}|{r['kind']}": r["cond"] for r in rows if r["w"] in ("W1", "W4")}
    write_json(PROMPTS_DIR / "prompts_summary.json", {"n_rows": len(rows), "positions": summ, "examples": ex,
                                                     "assertions": "all passed (length, suffix from p1, prefix before p0)"})
    logger.info(f"S1: {len(rows)} prompt rows; all alignment assertions passed")
    for k in list(ex)[:6]:
        logger.info(f"  {k}: {ex[k]!r}")
    return summ


def load_prompts() -> dict[tuple[str, str, str], dict[str, Any]]:
    from cfg import read_jsonl

    return {(r["task"], r["w"], r["kind"]): r for r in read_jsonl(PROMPTS_FILE)}
