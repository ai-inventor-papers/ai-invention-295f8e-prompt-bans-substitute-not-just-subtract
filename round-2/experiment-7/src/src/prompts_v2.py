#!/usr/bin/env python3
"""Step 0.4: build prompts/prompts_v2.json (every scored and generated condition), frozen before any GPU work.

prompt(task, segment) = cap_first(segment) + blank line + spec_text(task) (exp1 make_prompt); BASE0 = spec only.
Neutral twins use concreteness-norm nouns ranked by |tokens(noun) - tokens(name)|, ties to higher SUBTLEX frequency,
and are padded with a filler to the ban twin's chat-formatted token length (aligned suffix verified).
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from config import (CHAT_TAIL, DATA_IN, DISPLAY, FILLERS, FORCED_TEMPLATES, FREE_TEMPLATE, MODES, NOVELTY, PROMPTS,
                    SHAMS, SUITE, TASKS, TEMPLATES, TWO_STEP, WS, cap_first, commit, display, model_path, read_json,
                    setup_logging, write_json)

# Minimal neutrality screen (deviation, logged): a vulgar word and words with a path-search / data-structure sense.
NOUN_EXCLUDE = {"ass", "head", "road", "street", "map", "path", "tree", "graph", "queue", "stack", "heap", "grid",
                "node", "edge", "list", "table", "key", "line", "bucket", "ring", "walk", "route", "way", "game",
                "train", "step", "search", "point", "net", "web", "chain", "link", "track", "maze"}


def spec_text(task: str) -> str:
    return read_json(SUITE / "prompts" / "conditions.json")["spec"][task]


def make_prompt(task: str, segment: str | None) -> str:
    return spec_text(task) if segment is None else cap_first(segment) + "\n\n" + spec_text(task)


def chat(tok, prompt: str) -> str:
    s = tok.apply_chat_template([{"role": "user", "content": prompt}], tokenize=False, add_generation_prompt=True,
                                enable_thinking=False)
    assert s.endswith(CHAT_TAIL), repr(s[-60:])
    return s


def ids(tok, s: str) -> list[int]:
    return tok(s, add_special_tokens=False).input_ids


def mode_description(task: str, m: str) -> str:
    import sys

    sys.path.insert(0, str(SUITE))
    from common import MODE_DEFINITIONS

    d = MODE_DEFINITIONS[task][m]
    return d.split(":", 1)[1].strip() if ":" in d else d


def choose_nouns(tok) -> dict[str, Any]:
    bank = read_json(DATA_IN / "ds" / "noun_bank.json")
    out: dict[str, Any] = {}
    for task in TASKS:
        slots = list(MODES[task]) + list(SHAMS[task]) + ["nonce", "two_step"]
        used: set[str] = set()
        out[task] = {}
        for slot in slots:
            name = display(task, slot)
            nt = len(ids(tok, " " + name))
            ranked = sorted((e for e in bank if e["noun"] not in NOUN_EXCLUDE),
                            key=lambda e: (abs(e["tokens_ws"] - nt), -e["subtlex_frequency"], e["noun"]))
            need = 4 if slot == "two_step" else 2
            picks = []
            for e in ranked:
                if e["noun"] not in used:
                    picks.append(e["noun"])
                    used.add(e["noun"])
                if len(picks) == need:
                    break
            if slot == "two_step":
                out[task][slot] = {"A": f"{picks[0]} or {picks[1]}", "B": f"{picks[2]} or {picks[3]}", "name_tokens": nt}
            else:
                out[task][slot] = {"A": picks[0], "B": picks[1], "name_tokens": nt}
    return out


def build(tok) -> dict[str, Any]:
    nouns = choose_nouns(tok)
    conds: dict[str, dict[str, Any]] = {}

    def add(cid: str, task: str, kind: str, segment: str | None, **meta: Any) -> None:
        prompt = make_prompt(task, segment)
        c = chat(tok, prompt)
        conds[f"{task}|{cid}"] = {"cond_id": cid, "task": task, "kind": kind, "segment": segment, "prompt": prompt,
                                  "chat": c, "n_tokens": len(ids(tok, c)), **meta}

    for task in TASKS:
        add("base0", task, "base0", None)
        add("novelty", task, "novelty", NOVELTY)
        slots = list(MODES[task]) + list(SHAMS[task]) + ["nonce", "two_step"]
        for x in slots:
            name = display(task, x)
            for w in WS:
                add(f"ban|{x}|{w}", task, "ban", TEMPLATES[w]["ban"].replace("{X}", name), X=x, w=w)
                add(f"mention|{x}|{w}", task, "mention", TEMPLATES[w]["mention"].replace("{X}", name), X=x, w=w)
                for half in ("A", "B"):
                    seg = TEMPLATES[w]["neutral"].replace("{N}", nouns[task][x][half])
                    add(f"neutral|{x}|{w}|{half}", task, "neutral", seg, X=x, w=w, noun_set=half,
                        noun=nouns[task][x][half], unpadded_segment=seg)
        for j in MODES[task]:
            for k, t in enumerate(FORCED_TEMPLATES):
                add(f"forced|{j}|plain|k{k}", task, "forced", t.replace("{j}", DISPLAY[task][j]), j=j,
                    family="plain", k=k)
                desc = DISPLAY[task][j] + ", that is, " + mode_description(task, j)
                add(f"forced|{j}|desc|k{k}", task, "forced", t.replace("{j}", desc), j=j, family="desc", k=k)
    # token alignment of neutral twins to their ban twins
    align = {"filler": None, "failures": [], "pairs": 0, "candidates_tried": []}
    pairs = [(k, f"{v['task']}|ban|{v['X']}|{v['w']}") for k, v in conds.items() if v["kind"] == "neutral"]
    best = None
    suf_len = {t: _suffix_len(t, tok) for t in TASKS}
    spec_ids_t = {t: ids(tok, chat(tok, make_prompt(t, None))) for t in TASKS}
    for filler in FILLERS:
        trial, fails = {}, []
        for nk, bk in pairs:
            nv, bv = conds[nk], conds[bk]
            d = bv["n_tokens"] - nv["n_tokens"]
            seg = nv["unpadded_segment"] + filler * max(0, d)
            c = chat(tok, make_prompt(nv["task"], seg))
            ni, bi = ids(tok, c), ids(tok, bv["chat"])
            spec_ids = spec_ids_t[nv["task"]]
            suf = suf_len[nv["task"]]
            ok = len(ni) == len(bi) and ni[-suf:] == bi[-suf:] == spec_ids[-suf:]
            trial[nk] = (seg, c, len(ni), d)
            if not ok:
                fails.append({"pair": nk, "d": d, "len_neutral": len(ni), "len_ban": len(bi)})
        align["candidates_tried"].append({"filler": filler, "n_fail": len(fails)})
        if best is None or len(fails) < len(best[2]):
            best = (filler, trial, fails)
        if not fails:
            break
    filler, trial, fails = best
    align["filler"] = filler
    align["failures"] = fails
    align["pairs"] = len(pairs)
    failed = {f["pair"] for f in fails}
    for nk, (seg, c, n, d) in trial.items():
        if nk in failed:
            conds[nk]["padding"] = 0
            continue
        conds[nk].update({"segment": seg, "prompt": make_prompt(conds[nk]["task"], seg), "chat": c, "n_tokens": n,
                          "padding": max(0, d)})
    suffix = {t: _suffix_len(t, tok) for t in TASKS}
    free = {t: {x: tok_free(t, x) for x in MODES[t]} for t in TASKS}
    return {"version": "prompts_v2", "rules": {
        "prompt": "cap_first(segment) + blank line + SPEC (exp1 make_prompt); BASE0 = SPEC only",
        "chat": "apply_chat_template(add_generation_prompt=True, enable_thinking=False); tail asserted",
        "neutral_padding": "neutral segment + d x filler, d = ban tokens - neutral tokens (chat-formatted)",
        "noun_rule": "rank by |tokens_ws(noun) - tokens(' ' + name)|, ties -> higher SUBTLEX frequency; first two "
                     "unused nouns per slot (no reuse within a task); two-step slots get 'N1 or N2'",
        "noun_exclusions": sorted(NOUN_EXCLUDE)},
        "nouns": nouns, "alignment": align, "spec_suffix_tokens": suffix, "free_prompts": free,
        "conditions": conds}


def _suffix_len(task: str, tok) -> int:
    """Token count of the spec + chat-tail suffix shared by every condition of a task (from 'Task' on)."""
    base = ids(tok, chat(tok, make_prompt(task, None)))
    other = ids(tok, chat(tok, make_prompt(task, "Do not use apple for this task.")))
    n = 0
    while n < min(len(base), len(other)) and base[-1 - n] == other[-1 - n]:
        n += 1
    return n


def tok_free(task: str, x: str) -> str:
    import sys

    sys.path.insert(0, str(SUITE))
    from common import DESCRIPTION

    return DESCRIPTION[task] + "\n\n" + FREE_TEMPLATE.replace("{X}", DISPLAY[task][x])


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("prompts_v2")
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_path())
    out = build(tok)
    write_json(PROMPTS / "prompts_v2.json", out)
    commit(PROMPTS / "prompts_v2.json", "prompts_v2 frozen before any GPU work")
    n = len(out["conditions"])
    logger.info(f"{n} conditions; filler={out['alignment']['filler']!r}; alignment failures="
                f"{len(out['alignment']['failures'])}/{out['alignment']['pairs']}; suffix={out['spec_suffix_tokens']}")
    logger.info(f"nouns: {json.dumps(out['nouns'])}")
    for k in ("t1|ban|bfs|W1", "t1|neutral|bfs|W1|A", "t1|mention|bfs|W1", "t2|ban|nonce|W4", "t2|neutral|two_step|W3|B",
              "t1|forced|bibfs|plain|k0", "t2|forced|dial|desc|k9", "t1|novelty"):
        logger.info(f"{k}: {out['conditions'][k]['segment']!r} ({out['conditions'][k]['n_tokens']} tok)")


if __name__ == "__main__":
    main()
