#!/usr/bin/env python3
"""STEP 4: Gemma-3 prompt builders (port of iteration-3 exp15 prompts_llama.py; tokenizer only).

render(text) = apply_chat_template([{'role': 'user', 'content': text}], add_generation_prompt=True), asserted equal to
'<bos><start_of_turn>user\\n' + text + '<end_of_turn>\\n<start_of_turn>model\\n'; encoded with add_special_tokens=False
(exactly one BOS, at index 0); no system message.
Positions: seg_start = first token of the condition segment; spec_start = token at the first character of spec_text;
spec_end = index of the first <end_of_turn> after seg_start (EXCLUSIVE end of the spec span); R = last prompt token.
Bench text = cap(segment) + '\\n\\n' + spec_text. TWIN(task, X, w) = the W-template with a neutral noun, padded with
k x ' .' so that len(ids) and spec_start equal those of ban(X, w) and ids[spec_start:] are identical.
BAN PROMPTS ARE NEVER STORED OR FED BEFORE COMMIT #2: ban_len() returns only (len, spec_start); _ban_ids() is used
internally by the twin search and the U5 alignment assertion and never reaches the prompt registry.
"""

from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (BENCH, BOS_ID, CHAT_HEAD, CHAT_TAIL, DATA_DIR, DEP1, E7, E8, EOT_ID, EXP8_TASK, MAX_PAD, MODEL_ID,
                 MODEL_REVISION, NOVELTY, PAD_FILLER, PATH_TASKS, TEMPLATES, append_jsonl, bench_paths, cap_first,
                 ids_sha, model_path, read_json, sha256_text)

bench_paths()
from bench.common import catalogue as CAT  # noqa: E402
from bench.common import prompts as BP  # noqa: E402
import common as SUITE_COMMON  # noqa: E402  (exp8 suite: T1/T2 descriptions and catalogues)

REGISTRY = DATA_DIR / "prompts_fed.jsonl"
_REGISTERED: set[str] = set()


@lru_cache(maxsize=1)
def tokenizer():
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(model_path(MODEL_ID, MODEL_REVISION))


# ------------------------------------------------------------------------------------------------ catalogue
@lru_cache(maxsize=None)
def spec_json(task: str) -> dict[str, Any]:
    return read_json(BENCH / CAT.TASKS[task]["task_id"] / "spec.json")


@lru_cache(maxsize=None)
def spec_text(task: str) -> str:
    if task in PATH_TASKS:
        return SUITE_COMMON.spec_text(EXP8_TASK[task])
    return spec_json(task)["spec_text"]


def description(task: str) -> str:
    if task in PATH_TASKS:
        return SUITE_COMMON.DESCRIPTION[EXP8_TASK[task]]
    return CAT.TASKS[task]["description"]


def modes(task: str) -> list[str]:
    if task in PATH_TASKS:
        return list(SUITE_COMMON.CATALOGUE[EXP8_TASK[task]])
    return [c["mode"] for c in spec_json(task)["catalogue"]]


def display(task: str, mode: str) -> str:
    if task in PATH_TASKS:
        return SUITE_COMMON.CATALOGUE[EXP8_TASK[task]][mode]
    return CAT.display_name(task, mode)


# ------------------------------------------------------------------------------------------------ rendering
def render(text: str) -> tuple[str, list[int], list[tuple[int, int]]]:
    tok = tokenizer()
    rendered = tok.apply_chat_template([{"role": "user", "content": text}], tokenize=False, add_generation_prompt=True)
    assert rendered == CHAT_HEAD + text + CHAT_TAIL, "unexpected Gemma chat rendering"
    enc = tok(rendered, add_special_tokens=False, return_offsets_mapping=True)
    ids = list(enc["input_ids"])
    assert ids.count(BOS_ID) == 1 and ids[0] == BOS_ID, "exactly one BOS at index 0"
    return rendered, ids, [tuple(o) for o in enc["offset_mapping"]]


def _token_at_char(offsets: list[tuple[int, int]], char: int) -> int:
    for i, (a, b) in enumerate(offsets):
        if a == char and b > a:
            return i
    raise AssertionError(f"char {char} is not a token boundary")


def build(task: str, kind: str, text: str, *, cond: str, X: str | None = None, w: str | None = None,
          has_spec: bool = True) -> dict[str, Any]:
    rendered, ids, offs = render(text)
    seg_start = _token_at_char(offs, len(CHAT_HEAD))
    spec_start = None
    if has_spec:
        sp = rendered.find(spec_text(task), len(CHAT_HEAD))
        assert sp >= 0, f"{task}/{cond}: spec text not found"
        spec_start = _token_at_char(offs, sp)
    eot = ids.index(EOT_ID, seg_start)
    tail = tokenizer()(CHAT_TAIL, add_special_tokens=False)["input_ids"]
    assert ids[len(ids) - len(tail):] == tail and eot == len(ids) - len(tail), "chat tail mismatch"
    return {"task": task, "cond": cond, "kind": kind, "X": X, "w": w, "text": text, "ids": ids, "P": len(ids),
            "prompt_sha256": ids_sha(ids), "seg_start": seg_start, "spec_start": spec_start, "spec_end": eot,
            "R": len(ids) - 1, "pad": 0, "noun": None}


def bench_text(task: str, segment: str | None) -> str:
    return spec_text(task) if segment is None else cap_first(segment) + "\n\n" + spec_text(task)


# ------------------------------------------------------------------------------------------------ ban (tokenizer only)
def _ban_ids(task: str, X: str, w: str) -> tuple[list[int], int]:
    p = build(task, "ban_internal", bench_text(task, TEMPLATES[w][0].format(X=display(task, X))), cond="internal")
    return p["ids"], p["spec_start"]


def ban_len(task: str, X: str, w: str) -> tuple[int, int]:
    ids, s = _ban_ids(task, X, w)
    return len(ids), s


def p_ban(task: str, X: str, w: str) -> dict[str, Any]:
    """The modal-ban prompt. Called only by the ban stage (STEP 9), after commit #2."""
    from cfg import PRED_DIR

    assert (PRED_DIR / "commit_preban.json").exists(), "ban prompts may only be built after commit #2"
    return build(task, "ban", bench_text(task, TEMPLATES[w][0].format(X=display(task, X))), cond=f"ban:{X}:{w}",
                 X=X, w=w)


# ------------------------------------------------------------------------------------------------ nouns
@lru_cache(maxsize=1)
def noun_bank() -> list[dict[str, Any]]:
    tok = tokenizer()
    bank = read_json(DEP1 / "concreteness_noun_bank_candidates.json")
    excl = set(read_json(E7 / "frozen" / "templates_nouns_padding.json")["templates"]["noun_exclusions"])
    out = []
    for r in bank:
        if r["word"] in excl:
            continue
        r = dict(r)
        r["gemma_tokens"] = len(tok(" " + r["word"], add_special_tokens=False)["input_ids"])
        out.append(r)
    return out


def bank_ranked(task: str, name: str, used: set[str]) -> list[str]:
    tok = tokenizer()
    n = len(tok(" " + name, add_special_tokens=False)["input_ids"])
    rk = sorted(noun_bank(), key=lambda r: (abs(r["gemma_tokens"] - n), -float(r["subtlex"] or 0), r["word"]))
    return [r["word"] for r in rk if r["word"] not in used]


def frozen_nouns(task: str, X: str) -> list[str]:
    if task in PATH_TASKS:
        nn = read_json(E7 / "frozen" / "templates_nouns_padding.json")["nouns"][EXP8_TASK[task]]
        return [nn[X]["A"], nn[X]["B"]] if X in nn else []
    nn = read_json(BENCH / CAT.TASKS[task]["task_id"] / "neutral_nouns.json")
    return [n["word"] for n in nn[X]["nouns"]] if X in nn else []


def used_nouns(task: str) -> set[str]:
    out: set[str] = set()
    for m in modes(task):
        out |= set(frozen_nouns(task, m))
    return out


def _pad_to(task: str, ban_ids: list[int], ban_s: int, w: str, noun: str, cond: str, X: str) -> dict[str, Any] | None:
    base = TEMPLATES[w][1].format(N=noun)
    for k in range(0, MAX_PAD + 1):
        p = build(task, "twin", bench_text(task, base + PAD_FILLER * k), cond=cond, X=X, w=w)
        if p["P"] > len(ban_ids):
            return None
        if p["P"] == len(ban_ids) and p["spec_start"] == ban_s and p["ids"][ban_s:] == ban_ids[ban_s:]:
            p["pad"] = k
            p["noun"] = noun
            return p
    return None


@lru_cache(maxsize=None)
def _twin_cached(task: str, X: str, w: str) -> str:
    ban_ids, ban_s = _ban_ids(task, X, w)
    tried = []
    p = None
    for noun in frozen_nouns(task, X):
        tried.append(noun)
        p = _pad_to(task, ban_ids, ban_s, w, noun, f"twin:{X}:{w}", X)
        if p is not None:
            break
    if p is None:
        for cand in bank_ranked(task, display(task, X), used_nouns(task))[:200]:
            tried.append(cand)
            p = _pad_to(task, ban_ids, ban_s, w, cand, f"twin:{X}:{w}", X)
            if p is not None:
                break
    assert p is not None, f"no aligned twin for {task} {X} {w}"
    p["nouns_tried"] = tried
    p["noun_source"] = "frozen" if tried[-1] in frozen_nouns(task, X) else "bank_ranked"
    return json.dumps(p)


def p_twin(task: str, X: str, w: str) -> dict[str, Any]:
    """Token-length-matched neutral twin of ban(X, w)."""
    return json.loads(_twin_cached(task, X, w))


def aligned_with_ban(task: str, X: str, w: str) -> bool:
    tw = p_twin(task, X, w)
    ban_ids, ban_s = _ban_ids(task, X, w)
    diff = [i for i, (a, b) in enumerate(zip(tw["ids"], ban_ids)) if a != b]
    return (tw["P"] == len(ban_ids) and tw["spec_start"] == ban_s and tw["ids"][ban_s:] == ban_ids[ban_s:]
            and bool(diff) and min(diff) >= tw["seg_start"] and max(diff) < ban_s)


# ------------------------------------------------------------------------------------------------ other prompts
def p_novelty(task: str) -> dict[str, Any]:
    return build(task, "novelty", NOVELTY + "\n\n" + spec_text(task), cond="novelty")


def forced_segment(task: str, mode: str, k: int) -> str:
    if task in PATH_TASKS:
        fp = read_json(E8 / "prompts" / "frozen_prompts.json")
        return fp["tasks"][EXP8_TASK[task]]["forced"][mode]["paraphrases"][k]["segment"]
    return BP.forced_segment(task, mode, k)


def p_forced(task: str, mode: str, k: int) -> dict[str, Any]:
    return build(task, "forced", bench_text(task, forced_segment(task, mode, k)), cond=f"forced:{mode}:k{k}",
                 X=mode, w=f"k{k}")


def p_assoc(task: str, mode: str) -> dict[str, Any]:
    if task in PATH_TASKS:
        text = cap_first(description(task)) + "\n\n" + cap_first(
            CAT.ASSOCIATION_TEMPLATE.format(x=display(task, mode)))
    else:
        text = BP.build_association(task, mode)
    return build(task, "association", text, cond=f"association:{mode}", X=mode, has_spec=False)


# ------------------------------------------------------------------------------------------------ registry + audit
def register(p: dict[str, Any]) -> None:
    """Every model-fed prompt is registered (sha256, text, kind) for the grep audit."""
    assert p["kind"] != "ban_internal"
    if p["prompt_sha256"] in _REGISTERED:
        return
    _REGISTERED.add(p["prompt_sha256"])
    append_jsonl(REGISTRY, [{"sha256": p["prompt_sha256"], "text_sha256": sha256_text(p["text"]), "text": p["text"],
                             "kind": p["kind"], "task": p["task"], "cond": p["cond"]}])


def ban_frames(all_tasks: list[str]) -> list[str]:
    out = []
    for t in all_tasks:
        for m in modes(t):
            x = display(t, m)
            for w, (ban, _) in TEMPLATES.items():
                for xx in {x, cap_first(x)}:
                    s = ban.format(X=xx)
                    out.extend({s, cap_first(s)})
    return sorted(set(out))


def grep_audit(texts: list[tuple[str, str]], all_tasks: list[str]) -> dict[str, Any]:
    """texts: [(kind, text)]. Any ban frame instantiated with any catalogue display name is a hit."""
    frames = ban_frames(all_tasks)
    hits = []
    for kind, text in texts:
        for f in frames:
            if f in text:
                hits.append({"kind": kind, "frame": f, "text_head": text[:120]})
    return {"n_texts": len(texts), "n_frames": len(frames), "n_hits": len(hits), "hits": hits[:50],
            "pass": len(hits) == 0}
