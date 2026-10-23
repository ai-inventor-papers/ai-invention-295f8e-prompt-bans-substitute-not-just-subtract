#!/usr/bin/env python3
"""Gemma-3 prompt builders (port of exp23 prompts_gemma.py; tokenizer only). The pt and it models share one tokenizer.

render(text) = apply_chat_template([{'role': 'user', 'content': text}], add_generation_prompt=True), asserted equal to
'<bos><start_of_turn>user\\n' + text + '<end_of_turn>\\n<start_of_turn>model\\n'; encoded with add_special_tokens=False
(exactly one BOS, at index 0); no system message.
Positions: seg_start = first token of the condition segment; spec_start = token at the first character of spec_text;
spec_end = index of the first <end_of_turn> after seg_start (EXCLUSIVE end of the spec span); R = last prompt token.
TWIN(task, w) = the frozen W-template with a neutral noun padded with k x ' .' so that its token length and spec_start
equal those of the (never rendered) ban of exp23's D_g -- byte-identical to the iteration-4 twins (asserted against
exp23 commit1.json prompt hashes). NO BAN PROMPT IS EVER FED: _ban_ids() is internal (length matching only).
PLAIN(task) = '<bos>\"\"\"' + description + '\\n' + 'Use only the Python standard library.' + '\"\"\"\\n\\ndef ' + signature
+ ':\\n' (pt plain completion; no chat tokens).
"""

from __future__ import annotations

import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (BENCH, BOS_ID, CHAT_HEAD, CHAT_TAIL, DATA_DIR, DEP1, E7, E8, E23, EOT_ID, EXP8_TASK, EXP23_TWIN_X,
                 IT_ID, IT_REV, MAX_PAD, NOVELTY, PAD_FILLER, PATH_TASKS, PLAIN_STDLIB, TEMPLATES, append_jsonl,
                 bench_paths, cap_first, ids_sha, model_path, read_json, sha256_text)

bench_paths()
from bench.common import catalogue as CAT  # noqa: E402
import common as SUITE_COMMON  # noqa: E402  (exp8 suite: T1/T2 descriptions and catalogues)

REGISTRY = DATA_DIR / "prompts_fed.jsonl"
_REGISTERED: set[str] = set()


@lru_cache(maxsize=1)
def tokenizer():
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(model_path(IT_ID, IT_REV))


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
    return spec_json(task)["description"]


def signature(task: str) -> str:
    if task in PATH_TASKS:
        m = re.search(r"solve\([^)]*\)", description(task))
        assert m, task
        return m.group(0)
    return spec_json(task)["signature"]


def modes(task: str) -> list[str]:
    """Frozen catalogue modes (bench spec.json / exp8 suite)."""
    if task in PATH_TASKS:
        return list(SUITE_COMMON.CATALOGUE[EXP8_TASK[task]])
    return [c["mode"] for c in spec_json(task)["catalogue"]]


def display(task: str, mode: str) -> str:
    if task in PATH_TASKS:
        return SUITE_COMMON.CATALOGUE[EXP8_TASK[task]][mode]
    return CAT.display_name(task, mode)


def mechanism_texts(task: str) -> dict[str, str]:
    if task in PATH_TASKS:
        return dict(SUITE_COMMON.MODE_DEFINITIONS[EXP8_TASK[task]])
    return {c["mode"]: c.get("mechanism", c.get("display_name", c["mode"])) for c in spec_json(task)["catalogue"]}


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


# ------------------------------------------------------------------------------------------------ ban (internal only)
def _ban_ids(task: str, X: str, w: str) -> tuple[list[int], int]:
    p = build(task, "ban_internal", bench_text(task, TEMPLATES[w][0].format(X=display(task, X))), cond="internal")
    return p["ids"], p["spec_start"]


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


def p_twin(task: str, w: str) -> dict[str, Any]:
    """The frozen neutral twin of (task, w): exp23's twin for its D_g (byte-identical prompt ids)."""
    return json.loads(_twin_cached(task, EXP23_TWIN_X[task], w))


@lru_cache(maxsize=1)
def exp23_twin_hashes() -> dict[str, str]:
    c1 = read_json(E23 / "predictions" / "commit1.json")
    return {k: v["prompt_sha256"] for k, v in c1["twins"].items()}


# ------------------------------------------------------------------------------------------------ other prompts
def p_novelty(task: str) -> dict[str, Any]:
    return build(task, "novelty", NOVELTY + "\n\n" + spec_text(task), cond="novelty")


def plain_text(task: str) -> str:
    return '<bos>"""' + description(task) + "\n" + PLAIN_STDLIB + '"""\n\ndef ' + signature(task) + ":\n"


def p_plain(task: str) -> dict[str, Any]:
    tok = tokenizer()
    text = plain_text(task)
    ids = list(tok(text, add_special_tokens=False)["input_ids"])
    assert ids[0] == BOS_ID and ids.count(BOS_ID) == 1, "plain prompt: exactly one BOS at index 0"
    return {"task": task, "cond": "plain", "kind": "plain", "X": None, "w": None, "text": text, "ids": ids,
            "P": len(ids), "prompt_sha256": ids_sha(ids), "seg_start": None, "spec_start": None, "spec_end": None,
            "R": len(ids) - 1, "pad": 0, "noun": None, "prefix": "def " + signature(task) + ":\n"}


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


# ================================================================================================ claim S additions
# All contrast prompts are built on the SAME spec text as the twin, so their ids are identical from 'Task:' on; a
# segment shorter than the twin's is ' .'-padded until its spec_start equals the twin's (absolute positions align).
E9 = DATA_DIR.parent / "inputs" / "exp9"


def _pad_segment_to(task: str, base: str, target_spec_start: int, kind: str, cond: str, **kw: Any) -> dict[str, Any]:
    """base segment + k x ' .' with the smallest k such that spec_start == target (if reachable), else k = 0."""
    p0 = build(task, kind, bench_text(task, base), cond=cond, **kw)
    if p0["spec_start"] >= target_spec_start:
        p0["pad"] = 0
        p0["aligned"] = p0["spec_start"] == target_spec_start
        return p0
    for k in range(1, 40):
        p = build(task, kind, bench_text(task, base + PAD_FILLER * k), cond=cond, **kw)
        if p["spec_start"] == target_spec_start:
            p["pad"] = k
            p["aligned"] = True
            return p
        if p["spec_start"] > target_spec_start:
            break
    p0["pad"] = 0
    p0["aligned"] = False
    return p0


def p_forced(task: str, mode: str, f: str) -> dict[str, Any]:
    """F1-F5: the positive mirror of W1-W5 naming `mode`, padded to the W-twin's spec_start."""
    from cfg import FORCED_TEMPLATES

    w = "W" + f[1:]
    tw = p_twin(task, w)
    seg = FORCED_TEMPLATES[f].format(Y=display(task, mode))
    p = _pad_segment_to(task, cap_first(seg), tw["spec_start"], "forced", f"forced:{mode}:{f}", X=mode, w=w)
    p["template"] = f
    return p


@lru_cache(maxsize=1)
def exp9_forced_templates() -> list[str]:
    return list(read_json(E9 / "frozen_prompts.json")["forced_templates"])


def p_forced_para(task: str, mode: str, i: int) -> dict[str, Any]:
    """exp9's 10 frozen forced paraphrases ('Implement {X} for this task.', ...) with exp8's display names, padded to
    the W1 twin's spec_start when shorter."""
    tw = p_twin(task, "W1")
    seg = exp9_forced_templates()[i].format(X=display(task, mode))
    p = _pad_segment_to(task, cap_first(seg), tw["spec_start"], "forced_para", f"forced_para:{mode}:{i}", X=mode, w="W1")
    p["template"] = f"P{i}"
    return p


def p_ban(task: str, mode: str, w: str) -> dict[str, Any]:
    """W-template ban naming `mode` (fed to the model in claim S; the ban of D_g has exactly the twin's length)."""
    tw = p_twin(task, w)
    seg = TEMPLATES[w][0].format(X=display(task, mode))
    p = _pad_segment_to(task, cap_first(seg), tw["spec_start"], "ban", f"ban:{mode}:{w}", X=mode, w=w)
    p["template"] = w
    return p


def p_noun_variant(task: str, w: str, noun: str) -> dict[str, Any] | None:
    """Neutral twin of (task, w) with an arbitrary noun, ' .'-padded to exp23's D_g ban length (twin alignment)."""
    ban_ids, ban_s = _ban_ids(task, EXP23_TWIN_X[task], w)
    p = _pad_to(task, ban_ids, ban_s, w, noun, f"variant:{w}:{noun}", EXP23_TWIN_X[task])
    if p is not None:
        p["kind"] = "variant"
        p["template"] = w
    return p


@lru_cache(maxsize=1)
def top5_templates() -> list[dict[str, Any]]:
    d = read_json(E9 / "planned_conditions.json")

    def find(o: Any) -> Any:
        if isinstance(o, dict):
            if "TOP5" in o:
                return o["TOP5"]
            for v in o.values():
                r = find(v)
                if r is not None:
                    return r
        elif isinstance(o, list):
            for v in o:
                r = find(v)
                if r is not None:
                    return r
        return None

    return find(d)["templates"]


def p_top5(task: str, w: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """exp9's literal TOP5 ban segment (half 1) for template w, and its ' .'-padded neutral twin (exp9's nouns, with
    ' .' filler instead of ' Thanks.') whose spec_start equals the ban's."""
    tpl = {t["template"]: t for t in top5_templates()}[w]
    ban_seg = tpl["halves"]["1"]["segments"]["ban"]
    neu = tpl["halves"]["1"]["segments"]["neutral"].replace(" Thanks.", "").rstrip()
    pb = build(task, "top5", bench_text(task, ban_seg), cond=f"top5:{w}", w=w)
    pb["template"] = w
    pn = _pad_segment_to(task, neu, pb["spec_start"], "top5_twin", f"top5_twin:{w}", w=w)
    pn["template"] = w
    return pb, pn


def p_with_prefix(p: dict[str, Any], prefix_ids: list[int], tag: str) -> dict[str, Any]:
    """prompt + forced response prefix (canonical pre-fork prefix c*): the decode continues after it."""
    q = dict(p)
    q["ids"] = list(p["ids"]) + [int(t) for t in prefix_ids]
    q["P"] = len(q["ids"])
    q["R"] = q["P"] - 1
    q["prompt_sha256"] = ids_sha(q["ids"])
    q["kind"] = p["kind"] + "+cstar"
    q["cond"] = p["cond"] + f"+{tag}"
    q["prefix_len"] = len(prefix_ids)
    q["P_prompt"] = p["P"]
    return q
