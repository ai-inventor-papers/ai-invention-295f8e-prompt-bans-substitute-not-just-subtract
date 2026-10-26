#!/usr/bin/env python3
"""A3 prompt builder (protocol v2): W1-W5 ban / mention / neutral twins, substitute-mention twins, the exp1 baseline
prompt, the token-count-matched neutral filler {N}, and token spans of every prompt part.

Prompt = cap_first(condition segment) + blank line + exp1 SPEC. Token ids are built ONCE with the HF tokenizer via
apply_chat_template(..., add_generation_prompt=True, enable_thinking=False|True) and fed unchanged to vLLM
(TokensPrompt) and to HF, so both engines see identical ids.
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from core import (DATASET_SRC, EXP1, MODEL_HF, PROMPTS_DIR, TASKS, TEMPLATES, X_NAME, XSUB_NAME, cap_first,
                  read_json, sha256_file, write_json)

_TOK = None


def tokenizer():
    global _TOK
    if _TOK is None:
        from transformers import AutoTokenizer

        _TOK = AutoTokenizer.from_pretrained(MODEL_HF)
    return _TOK


def ntok(s: str) -> int:
    return len(tokenizer()(s, add_special_tokens=False)["input_ids"])


def load_spec_and_baseline() -> tuple[dict[str, str], dict[str, str]]:
    cond = json.loads((EXP1 / "prompts" / "conditions.json").read_text())
    spec = {t: cond["spec"][t] for t in TASKS}
    base = {}
    for t in TASKS:
        rows = cond["tasks"][t]["conditions"]["baseline"]
        p0 = [r for r in rows if int(r["paraphrase_id"]) == 0][0]
        base[t] = p0["prompt"]
    return spec, base


def load_noun_bank() -> dict[str, Any]:
    """concreteness_norms (dependency art_j3Rm_lr2nzR6): flagged neutral-noun candidates + all nouns with token
    counts (multi-token nouns are only used to close an exact token-count gap)."""
    cache = PROMPTS_DIR / "noun_bank_cache.json"
    if cache.exists():
        return json.loads(cache.read_text())
    src = DATASET_SRC / "full_data_out.json"
    logger.info(f"loading concreteness_norms from {src.name} ({src.stat().st_size / 1e6:.0f} MB)")
    data = json.loads(src.read_text())
    ds = [d for d in data["datasets"] if d["dataset"] == "concreteness_norms"][0]
    cands, fillers = [], []
    n_all = len(ds["examples"])
    for ex in ds["examples"]:
        w = ex["input"]
        rec = {"word": w, "freq": int(ex.get("metadata_subtlex_frequency") or 0),
               "conc": float(ex["output"]), "ntok_sp": int(ex.get("metadata_qwen3_tokens_with_leading_space") or 0),
               "lex": ex.get("metadata_oewn_noun_lexfiles") or []}
        if ex.get("metadata_noun_bank_candidate"):
            cands.append(rec)
        else:
            reasons = set(ex.get("metadata_exclusion_reasons") or [])
            # same filter as the bank except the single-token rule (concrete, frequent, known noun)
            if reasons == {"not_single_qwen3_token"} and rec["ntok_sp"] >= 2 and w.isalpha():
                fillers.append(rec)
    del data
    out = {"source": "gen_art_dataset_1/full_data_out.json:concreteness_norms", "n_words": n_all,
           "n_candidates": len(cands), "candidates": cands, "fillers": fillers,
           "source_sha256": sha256_file(src)}
    write_json(cache, out)
    return out


ALGO_WORDS = ("search", "queue", "stack", "graph", "tree", "path", "node", "heap", "list", "map", "grid", "edge",
              "algorithm", "bucket", "code", "program", "python", "function", "solution")


def neutral_filler(x_name: str, bank: dict[str, Any]) -> dict[str, Any]:
    """{N}: frequent neutral nouns joined by ' or ' whose token count (as ' '+N) equals that of ' '+X exactly."""
    target = ntok(" " + x_name)
    cands = [c for c in bank["candidates"] if c["word"].lower() not in ALGO_WORDS and c["word"].isalpha()]
    for c in cands:
        c["ntok_live"] = ntok(" " + c["word"])
    single = sorted([c for c in cands if c["ntok_live"] == 1], key=lambda c: (-c["freq"], c["word"]))
    # noun A: token count closest to the target, ties -> higher frequency
    first = sorted(cands, key=lambda c: (abs(c["ntok_live"] - target), -c["freq"], c["word"]))[0]
    words = [first["word"]]
    used = {first["word"]}
    pool = [c for c in single if c["word"] not in used]
    while ntok(" " + " or ".join(words)) < target and pool:
        words.append(pool.pop(0)["word"])
    trace = [" or ".join(words)]
    if ntok(" " + " or ".join(words)) > target and len(words) > 1:
        # overshoot: go back to the undershooting list and swap its last noun for a longer one (most frequent
        # first) whose token count closes the gap exactly
        words = words[:-1]
        fill = sorted([c for c in bank["fillers"] + cands if c["word"] not in words and c["word"].isalpha()
                       and c["word"].lower() not in ALGO_WORDS], key=lambda c: (-c["freq"], c["word"]))
        for c in fill:
            trial = (words[:-1] + [c["word"]]) if len(words) > 1 else [c["word"]]
            if ntok(" " + " or ".join(trial)) == target:
                words = trial
                break
        trace.append(" or ".join(words))
    n_str = " or ".join(words)
    got = ntok(" " + n_str)
    return {"N": n_str, "ntok_N": got, "ntok_X": target, "match": got == target, "words": words,
            "build_trace": trace}


def char_spans(rendered: str, offsets: list[tuple[int, int]], start: int, end: int) -> list[int]:
    """Token indices whose character span overlaps [start, end)."""
    return [i for i, (a, b) in enumerate(offsets) if b > start and a < end and b > a]


def render(text: str, thinking: bool) -> tuple[str, list[int], list[tuple[int, int]]]:
    tok = tokenizer()
    msgs = [{"role": "user", "content": text}]
    rendered = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=thinking)
    ids = tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, enable_thinking=thinking)
    enc = tok(rendered, add_special_tokens=False, return_offsets_mapping=True)
    if list(enc["input_ids"]) != list(ids):
        raise AssertionError("chat-template ids differ from tokenised rendered text")
    return rendered, list(ids), [tuple(o) for o in enc["offset_mapping"]]


def prompt_record(task: str, template: str, condition: str, segment_tpl: str | None, name: str | None,
                  spec: str, text_override: str | None = None) -> dict[str, Any]:
    if text_override is not None:
        segment, text = None, text_override
    else:
        segment = cap_first(segment_tpl.replace("{X}", name).replace("{N}", name))
        text = segment + "\n\n" + spec
    rec: dict[str, Any] = {"task": task, "template": template, "condition": condition, "segment": segment,
                           "name": name, "text": text}
    for thinking in (False, True):
        rendered, ids, offs = render(text, thinking)
        key = "think" if thinking else "nothink"
        u0 = rendered.index(text)
        spans: dict[str, list[int]] = {}
        if segment is not None:
            spans["segment"] = char_spans(rendered, offs, u0, u0 + len(segment))
            # the name occurs once in the (capitalised) segment
            seg_low = segment.lower()
            j = seg_low.index(name.lower())
            spans["name"] = char_spans(rendered, offs, u0 + j, u0 + j + len(name))
            spans["spec"] = char_spans(rendered, offs, u0 + len(segment) + 2, u0 + len(text))
        else:
            spans["spec"] = char_spans(rendered, offs, u0, u0 + len(text))
        content = set(i for v in spans.values() for i in v)
        spans["template"] = [i for i in range(len(ids)) if i not in content]
        rec[key] = {"ids": ids, "len": len(ids), "spans": spans}
    # decode checks: the segment span decodes back to the segment text (modulo surrounding whitespace)
    if segment is not None:
        tok = tokenizer()
        dec = tok.decode([rec["nothink"]["ids"][i] for i in rec["nothink"]["spans"]["segment"]])
        rec["segment_decodes_ok"] = dec.strip() == segment.strip()
        decn = tok.decode([rec["nothink"]["ids"][i] for i in rec["nothink"]["spans"]["name"]]).strip()
        rec["name_decodes"] = decn
    return rec


def build_prompts() -> dict[str, Any]:
    out_path = PROMPTS_DIR / "prompts_v2.json"
    if out_path.exists():
        return read_json(out_path)
    spec, base = load_spec_and_baseline()
    bank = load_noun_bank()
    fillers = {t: neutral_filler(X_NAME[t], bank) for t in TASKS}
    for t in TASKS:
        logger.info(f"{t}: X={X_NAME[t]!r} -> N={fillers[t]['N']!r} tokens {fillers[t]['ntok_N']}/{fillers[t]['ntok_X']}")
    prompts: dict[str, Any] = {}
    for t in TASKS:
        prompts[f"{t}|baseline|P0"] = prompt_record(t, "P0", "baseline", None, None, spec[t], text_override=base[t])
        for w, (ban, men, neu) in TEMPLATES.items():
            prompts[f"{t}|ban|{w}"] = prompt_record(t, w, "ban", ban, X_NAME[t], spec[t])
            prompts[f"{t}|mention|{w}"] = prompt_record(t, w, "mention", men, X_NAME[t], spec[t])
            prompts[f"{t}|neutral|{w}"] = prompt_record(t, w, "neutral", neu, fillers[t]["N"], spec[t])
            prompts[f"{t}|submention|{w}"] = prompt_record(t, w, "submention", men, XSUB_NAME[t], spec[t])
    checks = {}
    for t in TASKS:
        for w in TEMPLATES:
            lb = prompts[f"{t}|ban|{w}"]["nothink"]["len"]
            ln = prompts[f"{t}|neutral|{w}"]["nothink"]["len"]
            lm = prompts[f"{t}|mention|{w}"]["nothink"]["len"]
            checks[f"{t}|{w}"] = {"len_ban": lb, "len_neutral": ln, "len_mention": lm,
                                  "ban_neutral_aligned": lb == ln,
                                  "name_tokens_ban": len(prompts[f"{t}|ban|{w}"]["nothink"]["spans"]["name"]),
                                  "name_tokens_neutral": len(prompts[f"{t}|neutral|{w}"]["nothink"]["spans"]["name"])}
    bad_dec = [k for k, v in prompts.items() if v.get("segment_decodes_ok") is False]
    out = {"model_tokenizer": MODEL_HF, "spec_source": "inputs/exp1/prompts/conditions.json (spec.t1, spec.t2)",
           "baseline_source": "inputs/exp1/prompts/conditions.json tasks[t].conditions.baseline paraphrase_id 0",
           "neutral_fillers": fillers, "noun_bank": {k: bank[k] for k in ("source", "n_words", "n_candidates")},
           "alignment_checks": checks, "segment_decode_failures": bad_dec, "prompts": prompts}
    write_json(out_path, out, indent=None)
    logger.info(f"wrote {len(prompts)} prompts; segment decode failures: {bad_dec}")
    return out


if __name__ == "__main__":
    import sys

    from core import setup_logging

    setup_logging("prompts")
    P = build_prompts()
    for k in ("t1|ban|W1", "t1|neutral|W4", "t2|ban|W4", "t2|neutral|W1", "t2|mention|W3"):
        print(k, repr(P["prompts"][k]["text"][:90]), P["prompts"][k]["nothink"]["len"],
              P["prompts"][k].get("name_decodes"))
    print(json.dumps(P["alignment_checks"], indent=0)[:1500])
    sys.exit(0)
