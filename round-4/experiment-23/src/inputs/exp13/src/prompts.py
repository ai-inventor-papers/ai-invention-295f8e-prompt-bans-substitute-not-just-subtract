#!/usr/bin/env python3
"""S0.4: every prompt of the study (ban, token-length-matched neutral twin, nonce, novelty), chat-rendered with the
Qwen3 template (thinking off), tokenised once, with the task-spec span.

user text = cap_first(segment) + blank line + frozen spec_text.  The twin is the neutral segment with a noun N in
place of X, padded with ' .' fillers appended to the segment (exp7 frozen rule: neutral segment + d fillers,
d = ban tokens - twin tokens, chat-formatted) until the chat-formatted token counts are equal; the ids from the
'Task:' token to the end must then be identical.  Ban prompts are tokenised here (never sampled before the seal).
"""

from __future__ import annotations

import re
from typing import Any

from loguru import logger

from common import (CHAT_TAIL, DEFAULTS, FILLER, NONCE_X, NOUN_EXCLUSIONS, NOVELTY, PROMPTS, RESULTS, TASK_ORDER,
                    TEMPLATES, WS, bench_import, cap_first, display_name, read_json, sha256_text, spec, task_dir,
                    write_json, write_jsonl)


def load_tokenizer():
    from transformers import AutoTokenizer

    from common import model_path

    return AutoTokenizer.from_pretrained(model_path())


def render(tok, user_text: str) -> str:
    bench_import()
    from bench.common.prompts import render_chat

    chat = render_chat(tok, user_text)
    assert chat.endswith(CHAT_TAIL), f"bad chat tail: {chat[-60:]!r}"
    return chat


def encode(tok, chat: str, spec_text: str) -> tuple[list[int], list[int]]:
    """ids of the chat string and spec_span = [index of the 'Task:' token, index of the last spec token + 1)."""
    enc = tok(chat, add_special_tokens=False, return_offsets_mapping=True)
    ids, offs = enc["input_ids"], enc["offset_mapping"]
    cs = chat.rindex(spec_text)
    ce = cs + len(spec_text)
    starts = [i for i, (a, b) in enumerate(offs) if a == cs]
    ends = [i for i, (a, b) in enumerate(offs) if b == ce]
    assert starts and ends, "spec span does not align with token boundaries"
    s, e = starts[0], ends[-1] + 1
    assert tok.decode(ids[s:e]) == spec_text, "spec span does not decode to spec_text"
    return ids, [s, e]


def pick_noun(task: str, D: str, sp_text: str) -> tuple[str, str]:
    nn = read_json(task_dir(task) / "neutral_nouns.json")[D]["nouns"]
    for i, cand in enumerate(nn[:2]):
        w = cand["word"]
        if w.lower() in NOUN_EXCLUSIONS:
            continue
        if re.search(rf"\b{re.escape(w)}\b", sp_text, re.I):
            continue
        return w, ("first" if i == 0 else "second")
    raise RuntimeError(f"no usable neutral noun for {task}/{D}")


def build_all() -> dict[str, Any]:
    tok = load_tokenizer()
    bench_import()
    from bench.common.prompts import spec_text as bench_spec_text

    rows, ids_store, report = [], {}, {"tasks": {}}
    for t in TASK_ORDER:
        D = DEFAULTS[t]
        sp = spec(t)
        sp_text = sp["spec_text"]
        assert sp_text == bench_spec_text(t), f"{t}: spec.json spec_text differs from bench prompts.spec_text"
        X = display_name(t, D)
        N, which = pick_noun(t, D, sp_text)
        aliases = [X] + list(sp.get("aliases", {}).get(D, []))
        trep = {"D": D, "X": X, "N": N, "noun_choice": which, "templates": {}}
        for w in WS:
            ban_seg = cap_first(TEMPLATES[w][0].format(X=X))
            ban_text = ban_seg + "\n\n" + sp_text
            ban_chat = render(tok, ban_text)
            ban_ids, ban_span = encode(tok, ban_chat, sp_text)
            base_seg = cap_first(TEMPLATES[w][1].format(N=N))
            d = None
            twin_seg = twin_ids = twin_span = twin_chat = twin_text = None
            unpadded = len(encode(tok, render(tok, base_seg + "\n\n" + sp_text), sp_text)[0])
            d0 = len(ban_ids) - unpadded
            for dd in sorted(set([max(0, d0)] + list(range(max(0, d0 - 3), max(0, d0) + 4))), key=lambda x: abs(x - d0)):
                seg = base_seg + FILLER * dd
                text = seg + "\n\n" + sp_text
                chat = render(tok, text)
                ids_, span_ = encode(tok, chat, sp_text)
                if len(ids_) == len(ban_ids):
                    d, twin_seg, twin_ids, twin_span, twin_chat, twin_text = dd, seg, ids_, span_, chat, text
                    break
            assert d is not None, f"{t}/{w}: no filler count matches the ban length"
            assert twin_span == ban_span, f"{t}/{w}: spec spans differ {twin_span} vs {ban_span}"
            assert twin_ids[ban_span[0]:] == ban_ids[ban_span[0]:], f"{t}/{w}: ids from 'Task:' on differ"
            assert tok.decode(ban_ids[ban_span[0]:ban_span[0] + 1]).startswith("Task")
            non_seg = cap_first(TEMPLATES[w][0].format(X=NONCE_X))
            non_text = non_seg + "\n\n" + sp_text
            non_chat = render(tok, non_text)
            non_ids, non_span = encode(tok, non_chat, sp_text)
            for arm, seg, text, chat, ids_, span_ in [("ban", ban_seg, ban_text, ban_chat, ban_ids, ban_span),
                                                      ("twin", twin_seg, twin_text, twin_chat, twin_ids, twin_span),
                                                      ("nonce", non_seg, non_text, non_chat, non_ids, non_span)]:
                rows.append({"task": t, "arm": arm, "template": w, "segment": seg, "text": text,
                             "chat_sha256": sha256_text(chat), "ids_sha256": sha256_text(",".join(map(str, ids_))),
                             "n_tokens": len(ids_), "spec_span": span_,
                             "not_sampled_before_commit": arm == "ban"})
                ids_store[f"{t}|{arm}|{w}"] = {"ids": ids_, "spec_span": span_}
            trep["templates"][w] = {"ban_tokens": len(ban_ids), "twin_padding_d": d, "spec_span": ban_span}
        nov_text = NOVELTY + "\n\n" + sp_text
        nov_chat = render(tok, nov_text)
        nov_ids, nov_span = encode(tok, nov_chat, sp_text)
        rows.append({"task": t, "arm": "novelty", "template": "NOV", "segment": NOVELTY, "text": nov_text,
                     "chat_sha256": sha256_text(nov_chat), "ids_sha256": sha256_text(",".join(map(str, nov_ids))),
                     "n_tokens": len(nov_ids), "spec_span": nov_span, "not_sampled_before_commit": False})
        ids_store[f"{t}|novelty|NOV"] = {"ids": nov_ids, "spec_span": nov_span}
        # T2 audit: no display name or alias of D in any condition segment sampled before the commitment
        hits = []
        for r in rows:
            if r["task"] != t or r["arm"] == "ban":
                continue
            for a in aliases:
                if a.lower() in r["segment"].lower():
                    hits.append({"arm": r["arm"], "template": r["template"], "alias": a})
        assert not hits, f"{t}: alias leak in pre-commit segments: {hits}"
        trep["alias_audit_hits"] = 0
        report["tasks"][t] = trep
        logger.info(f"{t}: D={D} X='{X}' N='{N}' ({which}); paddings "
                    f"{[trep['templates'][w]['twin_padding_d'] for w in WS]}")
    PROMPTS.mkdir(parents=True, exist_ok=True)
    write_jsonl(PROMPTS / "prompts.jsonl", rows)
    write_json(PROMPTS / "prompt_ids.json", ids_store, indent=None)
    # one rendered example per arm (T03)
    ex = {f"{r['arm']}:{r['template']}": render(tok, r["text"]) for r in rows if r["task"] == "T03"
          and r["template"] in ("W1", "NOV")}
    write_json(PROMPTS / "rendered_examples_T03.json", ex)
    write_json(RESULTS / "prompt_report.json", report)
    return report


if __name__ == "__main__":
    from common import setup_logging

    setup_logging("s0_prompts")
    build_all()
