#!/usr/bin/env python3
"""Stage 1.1 / 1.2 prompts.

twin   the 75 W1-W5 neutral-twin prompts of the 15 tasks, exactly as iteration-4 exp22 prompts4.jsonl stores them
       (exp17 twins for 14 tasks, the display-name-padded R2 twin built in exp22). Every prompt is re-rendered here
       through the Qwen3-8B chat template (add_generation_prompt=True, enable_thinking=False) and must reproduce the
       stored ids; the base tokenizer must encode the rendered text to the SAME ids (shared vocabulary), so the
       base and instruct models see identical token ids and positions align one to one.
named  the exp22 forced 'Implement X' paraphrases (10 forced templates x 3 names per catalogue algorithm), used for
       the plan-site geometry (forward passes only, never sampled).
plain  plain-completion prompts for the base model (sensitivity): a docstring holding the twin condition sentence
       and the task description (the format line is replaced by 'Use only the Python standard library.'), then
       'def solve(<signature>):' -- the ITER1 exp5 template-free layout; 5 per task (one per twin template).
Positions: S = [p1, spec_end), R = P - 1, COND = the non-blank condition-sentence tokens in [p0, p1). They are taken
from exp20 results/positions.json where present (T03 T05 T06 T10 T1 T2) and recomputed with the same function
(exp22 prompts4.positions) for every task; equality is asserted on the overlap.
"""

from __future__ import annotations

import json
import re
from typing import Any

from loguru import logger

from cfg import (BASE_ID, BASE_REVISION, BENCH, E20, E22, EXP8_TASK, MODEL_ID, MODEL_REVISION, PATH_CATALOGUE,
                 PATH_TASKS, PRED_DIR, RESULTS_DIR, SUITE, TASKS15, TEMPLATE_IDS, TEMPLATE_TAIL, bench_dir,
                 bench_paths, cap_first, model_path, read_json, read_jsonl, sha256_text, write_json, write_jsonl)

PROMPTS5 = PRED_DIR / "prompts5.jsonl"
PLAIN_FMT = '"""\n{seg}\n\n{desc}\nUse only the Python standard library.\n"""\n\ndef {sig}:\n'
PATH_SIG = {"T1": "solve(grid, start, goal)", "T2": "solve(n, edges, s, t)"}


def load_tokenizers():
    from transformers import AutoTokenizer

    ti = AutoTokenizer.from_pretrained(model_path(MODEL_ID, MODEL_REVISION))
    tb = AutoTokenizer.from_pretrained(model_path(BASE_ID, BASE_REVISION))
    return ti, tb


def chat_ids(tok: Any, user_text: str) -> list[int]:
    ids = tok.apply_chat_template([{"role": "user", "content": user_text}], tokenize=True,
                                  add_generation_prompt=True, enable_thinking=False)
    if isinstance(ids, dict):
        ids = ids["input_ids"]
    return list(ids)


def chat_text(tok: Any, user_text: str) -> str:
    return tok.apply_chat_template([{"role": "user", "content": user_text}], tokenize=False,
                                   add_generation_prompt=True, enable_thinking=False)


def positions(tok: Any, ids: list[int], spec: str) -> tuple[int, int, int]:
    """exp22 prompts4.positions (verbatim logic): (p0 = end of the chat header, p1 = first spec token, spec_end)."""
    head = tok("<|im_start|>user\n", add_special_tokens=False)["input_ids"]
    assert ids[:len(head)] == head, "unexpected chat header"
    suf = tok(spec + TEMPLATE_TAIL, add_special_tokens=False)["input_ids"]
    p1 = len(ids) - len(suf)
    assert ids[p1:] == suf, "SPEC + template tail do not tokenize identically in context"
    tail = tok(TEMPLATE_TAIL, add_special_tokens=False)["input_ids"]
    return len(head), p1, len(ids) - len(tail)


def spec_of(r: dict[str, Any]) -> str:
    return r["user_text"].split("\n\n", 1)[1] if r.get("segment") else r["user_text"]


def description_and_sig(task: str) -> tuple[str, str]:
    if task in PATH_TASKS:
        bench_paths()
        import importlib.util

        spec = importlib.util.spec_from_file_location("suite_common", SUITE / "common.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod.DESCRIPTION[EXP8_TASK[task]], PATH_SIG[task]
    sp = read_json(bench_dir(task) / "spec.json")
    return sp["description"], sp["signature"]


def name_terms(task: str) -> list[str]:
    """Every catalogue display name and alias of a task (bench spec.json; exp22 PATH_CATALOGUE names for T1/T2)."""
    if task in PATH_TASKS:
        from cfg import PATH_CATALOGUE as _pc  # noqa: F401

        names = {"T1": ["breadth-first search", "bfs", "depth-first search", "dfs", "bidirectional", "iddfs",
                        "iterative deepening", "a*", "a star", "astar", "best-first", "dijkstra", "heuristic"],
                 "T2": ["dijkstra", "bellman", "ford", "spfa", "floyd", "warshall", "dial", "bidirectional",
                        "bucket queue", "priority queue", "heap"]}
        return names[task]
    sp = read_json(bench_dir(task) / "spec.json")
    out = []
    for c in sp["catalogue"]:
        out.append(c["display_name"])
        out.append(re.sub(r"^(a|an|the)\s+", "", c["display_name"]))
    for aa in sp.get("aliases", {}).values():
        out.extend(aa)
    return sorted({x.lower() for x in out if x})


def build(ti: Any, tb: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    src = read_jsonl(E22 / "prompts4.jsonl")
    rep: dict[str, Any] = {"tasks": {}, "checks": {}}
    pos20 = read_json(E20 / "positions.json")
    rows: list[dict[str, Any]] = []
    vocab_same = ti.get_vocab() == tb.get_vocab()
    rep["checks"]["vocab_identical"] = bool(vocab_same)
    assert vocab_same, "base and instruct vocabularies differ"
    n_overlap = n_overlap_ok = 0
    grep_hits = []
    for r in src:
        if r["task"] not in TASKS15 or r["kind"] not in ("twin", "named"):
            continue
        spec = spec_of(r)
        ids = chat_ids(ti, r["user_text"])
        assert ids == r["ids"], f"{r['pid']}: re-rendered ids differ from exp22"
        txt = chat_text(ti, r["user_text"])
        ids_b = tb(txt, add_special_tokens=False)["input_ids"]
        assert ids_b == ids, f"{r['pid']}: base tokenizer gives different ids"
        p0, p1, se = positions(ti, ids, spec)
        assert (p1, se, len(ids)) == (r["p1"], r["spec_end"], r["P"]), f"{r['pid']}: positions differ from exp22"
        cond = [p for p in range(p0, p1) if ti.decode([ids[p]]).strip() != ""]
        w = r.get("template_id")
        row = {"pid": r["pid"], "task": r["task"], "kind": r["kind"], "w": w, "X": r.get("X"),
               "segment": r["segment"], "user_text": r["user_text"], "ids": ids, "P": len(ids), "p0": p0,
               "p1": p1, "spec_end": se, "R": len(ids) - 1, "cond": cond, "prompt_sha256": r["prompt_sha256"],
               "source": f"exp22 prompts4.jsonl ({r.get('source')})"}
        if r["kind"] == "twin":
            key = f"{r['task']}|{w}|twin"
            if key in pos20:
                n_overlap += 1
                q = pos20[key]
                ok = (q["P"], q["p1"], q["spec_end"], q["R"]) == (row["P"], p1, se, row["R"])
                n_overlap_ok += int(ok)
                assert ok, f"{key}: positions differ from exp20 positions.json"
            seg = r["segment"].lower()
            for nm in name_terms(r["task"]):
                if re.search(rf"(?<![a-z0-9]){re.escape(nm)}(?![a-z0-9])", seg):
                    grep_hits.append({"pid": r["pid"], "name": nm, "segment": r["segment"]})
        rows.append(row)
    rep["checks"]["exp20_positions_overlap"] = {"n": n_overlap, "equal": n_overlap_ok}
    rep["checks"]["condition_grep_hits"] = grep_hits
    assert not grep_hits, f"catalogue name in a condition sentence: {grep_hits[:3]}"
    # plain-completion prompts (base sensitivity arm)
    twins = {(r["task"], r["w"]): r for r in rows if r["kind"] == "twin"}
    for t in TASKS15:
        desc, sig = description_and_sig(t)
        for w in TEMPLATE_IDS:
            seg = twins[(t, w)]["segment"]
            text = PLAIN_FMT.format(seg=seg, desc=desc, sig=sig)
            ids = tb(text, add_special_tokens=False)["input_ids"]
            rows.append({"pid": f"{t}|plain_tf|-|{w}|-", "task": t, "kind": "plain_tf", "w": w, "X": None,
                         "segment": seg, "user_text": text, "ids": ids, "P": len(ids), "p0": None, "p1": None,
                         "spec_end": None, "R": len(ids) - 1, "cond": None,
                         "prompt_sha256": sha256_text(json.dumps(ids)),
                         "source": "built here: ITER1 exp5 template-free layout with the twin sentence"})
    for t in TASKS15:
        tw = [r for r in rows if r["task"] == t and r["kind"] == "twin"]
        nm = [r for r in rows if r["task"] == t and r["kind"] == "named"]
        S_ids = {json.dumps(r["ids"][r["p1"]:r["spec_end"]]) for r in tw + nm}
        assert len(S_ids) == 1, f"{t}: task-spec ids differ across prompts"
        rep["tasks"][t] = {"n_twin": len(tw), "n_named": len(nm), "S_len": tw[0]["spec_end"] - tw[0]["p1"],
                           "P_by_template": {r["w"]: r["P"] for r in tw},
                           "named_modes": sorted({r["X"] for r in nm})}
        assert len(tw) == 5, f"{t}: {len(tw)} twin prompts"
    rep["n_rows"] = len(rows)
    return rows, rep


def stage_prompts() -> dict[str, Any]:
    ti, tb = load_tokenizers()
    rows, rep = build(ti, tb)
    write_jsonl(PROMPTS5, rows)
    write_json(RESULTS_DIR / "prompt_report.json", rep)
    logger.info(f"prompts5: {len(rows)} rows; vocab identical; exp20 overlap "
                f"{rep['checks']['exp20_positions_overlap']}; grep hits 0")
    return rep


def load_prompts(kinds: tuple[str, ...] = ("twin", "plain_tf", "named")) -> list[dict[str, Any]]:
    return [r for r in read_jsonl(PROMPTS5) if r["kind"] in kinds]


def twin_map() -> dict[tuple[str, str], dict[str, Any]]:
    return {(r["task"], r["w"]): r for r in load_prompts(("twin",))}


if __name__ == "__main__":
    from cfg import setup_logging

    setup_logging("prompts5")
    stage_prompts()
