#!/usr/bin/env python3
"""S1: ban prompts and token-aligned neutral twins for 14 tasks x W1-W5.

Rendering (exp8): '<|im_start|>user\\n' + cond + '\\n\\n' + spec_text + TEMPLATE_TAIL via the Qwen3 chat template with
thinking disabled. T1/T2 ids are taken verbatim from exp8 prompts/frozen_prompts.json (ban, neutral noun A) and
re-rendered to assert equality. Bench twins use noun A of the default mode (bench/<task>/neutral_nouns.json) padded
with d x ' .' (exp7 frozen rule) until the twin has the ban's token length, identical ids on [p1, P) and every
differing position inside the condition span [p0, p1).
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from cfg import (BENCH, BENCH_TASKS, DEFAULT, E8, EXP8_TASK, PAD_FILLER, PATH_TASKS, PROMPTS_DIR, TEMPLATE_IDS,
                 TEMPLATE_TAIL, TEMPLATES, cap_first, read_json, sha256_text, write_json, write_jsonl)

PROMPTS_FILE = PROMPTS_DIR / "prompts.jsonl"


def bench_dirs() -> dict[str, str]:
    com = read_json(BENCH / "commitment.json")
    out = {}
    for t in com["tasks"]:
        for d in BENCH.iterdir():
            if d.is_dir() and d.name.startswith(t + "_"):
                out[t] = d.name
    return out


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


def record(tok: Any, task: str, w: str, kind: str, segment: str, spec: str, **extra: Any) -> dict[str, Any]:
    text = cap_first(segment) + "\n\n" + spec
    ids = chat_ids(tok, text)
    p0, p1, spec_end = positions(tok, ids, spec)
    return {"task": task, "w": w, "kind": kind, "segment": cap_first(segment), "user_text": text, "ids": ids,
            "P": len(ids), "p0": p0, "p1": p1, "spec_end": spec_end, "prompt_sha256": sha256_text(json.dumps(ids)),
            **extra}


def aligned(ban: dict[str, Any], tw: dict[str, Any]) -> bool:
    if tw["P"] != ban["P"] or tw["p1"] != ban["p1"] or tw["p0"] != ban["p0"]:
        return False
    if tw["ids"][tw["p1"]:] != ban["ids"][ban["p1"]:]:
        return False
    diff = [i for i, (a, b) in enumerate(zip(tw["ids"], ban["ids"])) if a != b]
    return bool(diff) and min(diff) >= ban["p0"] and max(diff) < ban["p1"]


def build_all(tok: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    fp = read_json(E8 / "prompts" / "frozen_prompts.json")
    for t in PATH_TASKS:
        et = EXP8_TASK[t]
        td = fp["tasks"][et]
        spec = fp["spec"][et]
        for w in TEMPLATE_IDS:
            for kind, src in (("ban", "ban"), ("twin", "neutral_A")):
                r0 = td["templates"][w][src]
                rec = record(tok, t, w, kind, r0["segment"], spec, x=DEFAULT[t], x_display=td["x_display"],
                             noun=r0.get("noun"), n_pad=None, source=f"exp8 frozen_prompts.json {et}/{w}/{src}")
                assert rec["ids"] == r0["ids"], f"{t}/{w}/{kind}: re-rendering does not reproduce exp8 ids"
                assert (rec["p0"], rec["p1"]) == (r0["p0"], r0["p1"])
                rows.append(rec)
            assert aligned(rows[-2], rows[-1]), f"{t}/{w}: exp8 twin not aligned"
    dirs = bench_dirs()
    for t in BENCH_TASKS:
        spec_j = read_json(BENCH / dirs[t] / "spec.json")
        spec = spec_j["spec_text"]
        nn = read_json(BENCH / dirs[t] / "neutral_nouns.json")
        x = DEFAULT[t]
        xname = nn[x]["display_name"]
        cat_names = {c["mode"]: c["display_name"] for c in spec_j["catalogue"]}
        assert cat_names[x] == xname
        nouns = [n["word"] for n in nn[x]["nouns"]]
        for w in TEMPLATE_IDS:
            ban = record(tok, t, w, "ban", TEMPLATES[w][0].format(X=xname), spec, x=x, x_display=xname, noun=None,
                         n_pad=None, source=f"exp11 bench {dirs[t]}")
            twin = None
            for noun in nouns:  # noun A first; noun B only if A cannot be aligned (logged)
                for d in range(0, 24):
                    seg = TEMPLATES[w][1].format(N=noun) + PAD_FILLER * d
                    cand = record(tok, t, w, "twin", seg, spec, x=x, x_display=xname, noun=noun, n_pad=d,
                                  source=f"exp11 bench {dirs[t]} neutral_nouns.json")
                    if cand["P"] > ban["P"]:
                        break
                    if aligned(ban, cand):
                        twin = cand
                        break
                if twin is not None:
                    if noun != nouns[0]:
                        logger.warning(f"{t}/{w}: noun A '{nouns[0]}' could not be aligned; used noun B '{noun}'")
                    break
            if twin is None:
                raise RuntimeError(f"{t}/{w}: no aligned neutral twin")
            rows += [ban, twin]
    return rows


def stage_prompts() -> dict[str, Any]:
    from transformers import AutoTokenizer

    from cfg import MODEL_ID, MODEL_REVISION, model_path

    path = model_path()
    tok = AutoTokenizer.from_pretrained(path, **({"revision": MODEL_REVISION} if path == MODEL_ID else {}))
    rows = build_all(tok)
    # T2 assertions (testing plan T2): equal length, identical [p1, P), differences inside [p0, p1)
    by = {(r["task"], r["w"], r["kind"]): r for r in rows}
    summ = {}
    for t in PATH_TASKS + BENCH_TASKS:
        for w in TEMPLATE_IDS:
            b, n = by[(t, w, "ban")], by[(t, w, "twin")]
            assert aligned(b, n)
            assert b["spec_end"] == n["spec_end"] and b["spec_end"] > b["p1"]
        b1 = by[(t, "W1", "ban")]
        summ[t] = {"x": b1["x"], "x_display": b1["x_display"], "S_len": b1["spec_end"] - b1["p1"],
                   "P": {w: by[(t, w, "ban")]["P"] for w in TEMPLATE_IDS},
                   "twin_nouns": sorted({by[(t, w, "twin")]["noun"] for w in TEMPLATE_IDS}),
                   "n_pad": {w: by[(t, w, "twin")]["n_pad"] for w in TEMPLATE_IDS}}
        logger.info(f"S1 {t}: X='{b1['x_display']}' |S|={summ[t]['S_len']} P={summ[t]['P']} pads={summ[t]['n_pad']}")
    write_jsonl(PROMPTS_FILE, rows)
    write_json(PROMPTS_DIR / "prompts_summary.json", summ)
    logger.info(f"S1: {len(rows)} prompts -> {PROMPTS_FILE.name}")
    return summ


def load_prompts() -> dict[tuple[str, str, str], dict[str, Any]]:
    out = {}
    with open(PROMPTS_FILE) as fh:
        for line in fh:
            r = json.loads(line)
            out[(r["task"], r["w"], r["kind"])] = r
    return out
