#!/usr/bin/env python3
"""S0.6-0.8 frozen configuration for the Llama-3.1-8B-Instruct replication.

Display names (v2), SHARED PROTOCOL v2 templates W1-W5 (ban / mention / neutral), nonce ban, novelty instruction,
baseline / listall / forced / free-form / two-step prompts, Llama-3.1 chat rendering (default template, explicit
date_string), neutral nouns re-tokenised under Llama and ban-length padding of neutral twins.

Every prompt is a dict {task, cond, kind, X, w, h, pid, segment, text, ids, sha, seg_start, spec_start, R, k,
filler_inserted}; vLLM receives exactly `ids`, HF scores exactly `ids`.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from typing import Any

from src.ws import DATA, RESULTS, C, model_path

import gen.prompts as GP  # canon  # noqa: E402

TASKS = ("t1", "t2")
DISPLAY: dict[str, dict[str, str]] = {
    "t1": {
        "bfs": "breadth-first search (BFS)",
        "dfs": "depth-first search (DFS)",
        "bibfs": "bidirectional BFS",
        "iddfs": "iterative deepening DFS (IDDFS)",
        "astar_gbfs": "A* search",
        "dijkstra": "unit-weight Dijkstra",
    },
    "t2": {
        "dijkstra": "Dijkstra's algorithm",
        "bf_spfa": "Bellman-Ford or SPFA",
        "bidijkstra": "bidirectional Dijkstra",
        "floyd": "Floyd-Warshall",
        "dial": "Dial's bucket-queue algorithm",
    },
}
MODES = {t: list(DISPLAY[t].keys()) for t in TASKS}
assert all(MODES[t] == C.MODES[t] for t in TASKS), "v2 display names must be keyed by the canon mode keys"

# SHARED PROTOCOL v2 frozen templates: w -> (ban, mention, neutral)
TEMPLATES: dict[int, tuple[str, str, str]] = {
    1: ("Do not use {X} for this task.", "You could use {X} for this task.", "Do not use {N} for this task."),
    2: ("Your solution must not rely on {X}.", "Your solution may rely on {X}.", "Your solution must not rely on {N}."),
    3: ("Avoid {X} entirely.", "Consider {X} first.", "Avoid {N} entirely."),
    4: ("{X} is not allowed here.", "{X} is allowed here.", "{N} is not allowed here."),
    5: ("Write a correct solution that does not use {X}.", "Write a correct solution that may use {X}.",
        "Write a correct solution that does not use {N}."),
}
WS_ = (1, 2, 3, 4, 5)
NONCE_X = "the Zorblax method"
NOVELTY = "Write a novel algorithm for this task, one you have not seen before."
BASELINE = list(GP.BASELINE_SEGMENTS[:5])
LISTALL = list(GP.LISTALL_TEMPLATES[:5])
FORCED_EXTRA = ["Please implement {X} for this task.", "Write a solution that uses {X}.", "Solve this task using {X}.",
                "Your implementation must use {X}.", "Base your solution on {X}."]
FORCED = list(GP.FORCED_TEMPLATES) + FORCED_EXTRA
assert len(FORCED) == 10
FREE_TEMPLATE = GP.FREE_TEMPLATE
DATE_STRING = "26 Jul 2024"
FILLER = " -"
MAX_PAD = 20
EOS_IDS = [128001, 128008, 128009]  # <|end_of_text|>, <|eom_id|>, <|eot_id|>


def fill(template: str, **kw: str) -> str:
    return GP.fill(template, **kw)  # replace + cap_first (canon)


def descriptive_name(task: str, x: str) -> str:
    """'<display name> (that is, <canon MODE_DEFINITIONS sentence>)' -- trailing period dropped inside the bracket."""
    return f"{DISPLAY[task][x]} (that is, {C.MODE_DEFINITIONS[task][x].rstrip('.')})"


def request_seed(task: str, cond: str, tpl: Any, sample_id: Any) -> int:
    return int(hashlib.sha256(f"{task}|{cond}|{tpl}|{sample_id}".encode()).hexdigest()[:8], 16)


def ids_sha(ids: list[int]) -> str:
    return hashlib.sha256(json.dumps(list(map(int, ids))).encode()).hexdigest()


# ------------------------------------------------------------------------------------------------ tokenizer
@lru_cache(maxsize=1)
def tokenizer():
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(model_path())


def render(text: str) -> tuple[str, list[int], list[tuple[int, int]]]:
    tok = tokenizer()
    rendered = tok.apply_chat_template([{"role": "user", "content": text}], tokenize=False,
                                       add_generation_prompt=True, date_string=DATE_STRING)
    enc = tok(rendered, add_special_tokens=False, return_offsets_mapping=True)
    return rendered, list(enc["input_ids"]), [tuple(o) for o in enc["offset_mapping"]]


USER_HDR = "<|start_header_id|>user<|end_header_id|>\n\n"


def _token_at_char(offsets: list[tuple[int, int]], char: int) -> int:
    for i, (a, b) in enumerate(offsets):
        if a == char and b > a:
            return i
    raise AssertionError(f"no token starts exactly at char {char}")


def build(task: str, kind: str, segment: str | None, *, cond: str, X: str | None = None, w: int | None = None,
          h: int | None = None, pid: int | None = None, text: str | None = None) -> dict[str, Any]:
    """Render one prompt. text defaults to [segment] + blank line + SPEC (canon make_prompt)."""
    spec = C.spec_text(task)
    if text is None:
        text = GP.make_prompt(task, segment)
    rendered, ids, offs = render(text)
    tok = tokenizer()
    assert ids.count(tok.bos_token_id) == 1 and ids[0] == tok.bos_token_id, "exactly one BOS at index 0"
    assert "Today Date: " + DATE_STRING in rendered
    R = len(ids) - 1
    assert ids[R] == 271 and ids[R - 1] == 128007, "R must be the two-newline token after <|end_header_id|>"
    cstart = rendered.index(USER_HDR) + len(USER_HDR)
    seg_start = _token_at_char(offs, cstart)
    sp = rendered.find(spec, cstart)
    spec_start = _token_at_char(offs, sp) if sp >= 0 else None
    return {"task": task, "cond": cond, "kind": kind, "X": X, "w": w, "h": h, "pid": pid, "segment": segment,
            "text": text, "ids": ids, "sha": ids_sha(ids), "seg_start": seg_start, "spec_start": spec_start, "R": R,
            "k": 0, "filler_inserted": 0}


# ------------------------------------------------------------------------------------------------ neutral nouns
@lru_cache(maxsize=1)
def noun_bank() -> list[dict[str, Any]]:
    tok = tokenizer()
    bank = json.loads((DATA / "noun_bank.json").read_text())
    for r in bank:
        r["llama_tokens"] = len(tok(" " + r["word"], add_special_tokens=False)["input_ids"])
    return bank


def name_tokens(task: str, name: str) -> int:
    with_x = build(task, "probe", fill(TEMPLATES[1][0], X=name), cond="probe")
    empty = build(task, "probe", fill(TEMPLATES[1][0], X=""), cond="probe")
    return len(with_x["ids"]) - len(empty["ids"])


def ranked_nouns(task: str, name: str) -> list[dict[str, Any]]:
    n = name_tokens(task, name)
    return sorted(noun_bank(), key=lambda r: (abs(r["llama_tokens"] - n), -r["subtlex"], r["word"]))


def neutral_noun_phrase(task: str, name: str, h: int, two_step: bool = False) -> str:
    rk = ranked_nouns(task, name)
    if two_step:  # half 1 '{Q0} or {Q2}', half 2 '{Q1} or {Q3}'
        return f"{rk[0]['word']} or {rk[2]['word']}" if h == 1 else f"{rk[1]['word']} or {rk[3]['word']}"
    return rk[0]["word"] if h == 1 else rk[1]["word"]


def padded_neutral(task: str, ban: dict[str, Any], w: int, noun: str, *, cond: str, X: str | None,
                   h: int) -> dict[str, Any]:
    """Neutral twin of `ban` with k copies of ' -' after the final period so the token sequences have equal length
    and identical ids from spec_start onward; token-level filler insertion before the separator if no k works."""
    base_seg = fill(TEMPLATES[w][2], N=noun)
    best = None
    for k in range(0, MAX_PAD + 1):
        seg = base_seg + FILLER * k
        p = build(ban["task"], "neutral", seg, cond=cond, X=X, w=w, h=h)
        if (len(p["ids"]) == len(ban["ids"]) and p["spec_start"] == ban["spec_start"]
                and p["ids"][p["spec_start"]:] == ban["ids"][ban["spec_start"]:]):
            p["k"] = k
            p["noun"] = noun
            return p
        if len(p["ids"]) < len(ban["ids"]):
            best = (k, p)
    # fallback: token-level filler before the separator token (spec_start - 1)
    assert best is not None, f"neutral longer than ban even at k=0 ({cond})"
    k, p = best
    tok = tokenizer()
    fid = tok(FILLER, add_special_tokens=False)["input_ids"]
    assert len(fid) == 1
    gap = len(ban["ids"]) - len(p["ids"])
    at = p["spec_start"] - 1
    ids = p["ids"][:at] + fid * gap + p["ids"][at:]
    p.update({"ids": ids, "sha": ids_sha(ids), "spec_start": p["spec_start"] + gap, "R": len(ids) - 1, "k": k,
              "filler_inserted": gap, "noun": noun})
    assert len(ids) == len(ban["ids"]) and ids[p["spec_start"]:] == ban["ids"][ban["spec_start"]:]
    return p


# ------------------------------------------------------------------------------------------------ condition builders
def p_baseline(task: str, s: int) -> dict[str, Any]:
    return build(task, "baseline", BASELINE[s], cond=f"baseline:s{s}", pid=s)


def p_baseline_empty(task: str) -> dict[str, Any]:
    return build(task, "baseline_empty", None, cond="baseline_empty")


def p_ban(task: str, x: str, w: int) -> dict[str, Any]:
    return build(task, "ban", fill(TEMPLATES[w][0], X=DISPLAY[task][x]), cond=f"ban:{x}:w{w}", X=x, w=w)


def p_mention(task: str, x: str, w: int) -> dict[str, Any]:
    return build(task, "mention", fill(TEMPLATES[w][1], X=DISPLAY[task][x]), cond=f"mention:{x}:w{w}", X=x, w=w)


def p_neutral(task: str, x: str, w: int, h: int) -> dict[str, Any]:
    ban = p_ban(task, x, w)
    noun = neutral_noun_phrase(task, DISPLAY[task][x], h)
    return padded_neutral(task, ban, w, noun, cond=f"neutral:{x}:w{w}:h{h}", X=x, h=h)


def p_nonce(task: str, w: int) -> dict[str, Any]:
    return build(task, "nonce", fill(TEMPLATES[w][0], X=NONCE_X), cond=f"nonce:w{w}", w=w)


def p_nonce_neutral(task: str, w: int, h: int) -> dict[str, Any]:
    ban = p_nonce(task, w)
    noun = neutral_noun_phrase(task, NONCE_X, h)
    return padded_neutral(task, ban, w, noun, cond=f"nonce_neutral:w{w}:h{h}", X=None, h=h)


def p_novelty(task: str) -> dict[str, Any]:
    return build(task, "novelty", NOVELTY, cond="novelty")


def listall_names(task: str, p: int) -> list[str]:
    return GP.listall_order(task, p)  # canon seeded order random.Random(f'listall|{task}|{pid}')


def p_listall(task: str, p: int) -> dict[str, Any]:
    order = listall_names(task, p)
    seg = fill(LISTALL[p], L=C.join_names_and([DISPLAY[task][m] for m in order]))
    return build(task, "listall", seg, cond=f"listall:p{p}", pid=p)


def two_step_name(task: str, d: str, s: str) -> str:
    return C.join_names_or([DISPLAY[task][d], DISPLAY[task][s]])


def p_twostep(task: str, d: str, s: str, w: int) -> dict[str, Any]:
    return build(task, "twostep", fill(TEMPLATES[w][0], X=two_step_name(task, d, s)), cond=f"twostep:{d}+{s}:w{w}",
                 X=f"{d}+{s}", w=w)


def p_twostep_neutral(task: str, d: str, s: str, w: int, h: int) -> dict[str, Any]:
    ban = p_twostep(task, d, s, w)
    noun = neutral_noun_phrase(task, two_step_name(task, d, s), h, two_step=True)
    return padded_neutral(task, ban, w, noun, cond=f"twostep_neutral:{d}+{s}:w{w}:h{h}", X=f"{d}+{s}", h=h)


def p_forced(task: str, x: str, k: int, descriptive: bool = False) -> dict[str, Any]:
    name = descriptive_name(task, x) if descriptive else DISPLAY[task][x]
    kind = "forced_desc" if descriptive else "forced"
    return build(task, kind, fill(FORCED[k], X=name), cond=f"{kind}:{x}:k{k}", X=x, pid=k)


def p_free(task: str, x: str) -> dict[str, Any]:
    text = C.DESCRIPTION[task] + "\n\n" + FREE_TEMPLATE.replace("{X}", DISPLAY[task][x])
    return build(task, "free", None, cond=f"free:{x}", X=x, text=text)


def frozen_config() -> dict[str, Any]:
    tok = tokenizer()
    out: dict[str, Any] = {
        "model": "meta-llama/Llama-3.1-8B-Instruct", "date_string": DATE_STRING, "display_names_v2": DISPLAY,
        "templates_w1_w5": {f"W{w}": {"ban": t[0], "mention": t[1], "neutral": t[2]} for w, t in TEMPLATES.items()},
        "nonce_x": NONCE_X, "novelty": NOVELTY, "baseline_segments": BASELINE, "listall_templates": LISTALL,
        "forced_templates": FORCED, "free_template": FREE_TEMPLATE, "filler": FILLER, "max_pad": MAX_PAD,
        "eos_ids": EOS_IDS, "prompt_rule": "cap_first(segment) + blank line + canon spec_text(task)",
        "noun_rule": "rank by |llama tokens(' '+word) - name tokens|, then SUBTLEX desc, then alphabetical; "
                     "noun A = rank 0 (half 1), noun B = rank 1 (half 2); two-step neutral '{Q0} or {Q2}' / '{Q1} or {Q3}'",
        "descriptive_variant": "'<display name> (that is, <canon MODE_DEFINITIONS sentence without final period>)'",
        "chat_template_sha256": hashlib.sha256((tok.chat_template or "").encode()).hexdigest(),
        "nouns": {}, "name_tokens": {},
    }
    bank = noun_bank()
    out["noun_bank"] = {"n": len(bank), "llama_token_counts": {str(n): sum(1 for r in bank if r["llama_tokens"] == n)
                                                               for n in sorted({r["llama_tokens"] for r in bank})}}
    for task in TASKS:
        out["nouns"][task] = {}
        out["name_tokens"][task] = {}
        for x, name in list(DISPLAY[task].items()) + [("__nonce__", NONCE_X)]:
            rk = ranked_nouns(task, name)
            out["name_tokens"][task][x] = name_tokens(task, name)
            out["nouns"][task][x] = [rk[i]["word"] for i in range(4)]
    return out
