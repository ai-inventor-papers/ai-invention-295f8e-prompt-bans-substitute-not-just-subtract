#!/usr/bin/env python3
"""Prompt rendering for the panel-B units (one tokenizer -- the instruct model's -- for BOTH models, so base and
instruct receive identical token ids; asserted against the base tokenizer in the GPU tests).

kinds:
- twin    W1-W5 neutral twins: TEMPLATES[w][1] with the unit's neutral noun + d x ' .' padding, where d = (#tokens of
          the dataset-reference mode's display name as rendered in that slot) - (#tokens of the noun in the same slot),
          both tokenised alone (the exp22 R2 rule: no ban sentence is ever constructed);
- novelty the condition sentence replaced by NOVELTY_SEGMENT (plan section 6);
- assoc   description + ASSOCIATION_TEMPLATE(x = display name of mode m), one prompt per catalogue mode;
- plain   base-model plain completion: an opened ```python fence + signature + docstring (the description).
Neutral noun rule (exp7 frozen): rank the concreteness_norms noun-bank candidates by |tokens(' ' + noun) -
tokens(' ' + name)|, ties -> higher SUBTLEX frequency; frozen exclusions, every unit's banned words and nouns already
used by another unit are skipped.
"""

from __future__ import annotations

import json
import re
from typing import Any

from cfg5 import (ASSOCIATION_TEMPLATE, INPUTS, NOVELTY_SEGMENT, PAD_FILLER, PROMPTS, TEMPLATE_IDS, TEMPLATE_TAIL,
                  TEMPLATES, UNITS_DIR, VENDOR, cap_first, read_json, read_jsonl, sha256_text, write_json,
                  write_jsonl)
from units_spec import UNITS, banned_words, display_name, spec_text


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


def render(tok: Any, unit: str, kind: str, segment: str | None, spec: str, **meta: Any) -> dict[str, Any]:
    text = spec if not segment else cap_first(segment) + "\n\n" + spec
    ids = chat_ids(tok, text)
    p0, p1, se = positions(tok, ids, spec)
    pid = "|".join(str(x) for x in (unit, kind, meta.get("X") or "-", meta.get("template_id") or "-"))
    return {"pid": pid, "unit": unit, "kind": kind, "segment": cap_first(segment) if segment else "",
            "user_text": text, "ids": ids, "P": len(ids), "p0": p0, "p1": p1, "spec_end": se,
            "prompt_sha256": sha256_text(json.dumps(ids)), **meta}


def noun_bank() -> list[dict[str, Any]]:
    src = read_json(INPUTS / "sources.json")["nouns"]
    excl = set(read_json(VENDOR / "exp7" / "frozen" / "templates_nouns_padding.json")["templates"]["noun_exclusions"])
    out = []
    for e in src:
        w = e["input"]
        if not re.fullmatch(r"[a-z]+", w) or w in excl:
            continue
        out.append({"word": w, "freq": int(e.get("metadata_subtlex_frequency") or 0)})
    return out


def pick_noun(tok: Any, unit: str, used: set[str]) -> dict[str, Any]:
    name = display_name(unit, UNITS[unit]["dataset_reference_mode"])
    nt = len(tok(" " + name, add_special_tokens=False)["input_ids"])
    bans = set()
    for u in UNITS:
        bans |= {w for w in banned_words(u) if " " not in w}
    cands = []
    for e in noun_bank():
        if e["word"] in bans or e["word"] in used:
            continue
        k = len(tok(" " + e["word"], add_special_tokens=False)["input_ids"])
        cands.append((abs(k - nt), -e["freq"], e["word"], k))
    cands.sort()
    d, nf, w, k = cands[0]
    return {"word": w, "qwen3_tokens_ws": k, "subtlex_freq": -nf, "display_name": name, "name_tokens_ws": nt,
            "abs_diff": d, "rule": "exp7 frozen noun rule (rank |tokens_ws(noun) - tokens(' ' + name)|, ties -> higher "
                                   "SUBTLEX frequency)"}


def twin_rows(tok: Any, unit: str, noun: dict[str, Any], spec: str) -> list[dict[str, Any]]:
    xname = noun["display_name"]
    nn = noun["word"]
    rows = []
    for w in TEMPLATE_IDS:
        lead = TEMPLATES[w][1].startswith("{N}")
        xr = cap_first(xname) if lead else " " + xname
        nr = cap_first(nn) if lead else " " + nn
        d = len(tok(xr, add_special_tokens=False)["input_ids"]) - len(tok(nr, add_special_tokens=False)["input_ids"])
        d = max(0, d)
        seg = TEMPLATES[w][1].format(N=nn) + PAD_FILLER * d
        rows.append(render(tok, unit, "twin", seg, spec, template_id=w, X=None, noun=nn, n_pad=d,
                           source="built here: neutral noun + display-name-only padding (exp22 R2 rule)"))
    return rows


def plain_prompt(unit: str) -> str:
    u = UNITS[unit]
    return f'```python\ndef {u["signature"]}:\n    """{u["description"]}\n    """\n'


def build_unit_prompts(tok: Any, unit: str, used_nouns: set[str]) -> list[dict[str, Any]]:
    spec = spec_text(unit)
    noun = pick_noun(tok, unit, used_nouns)
    used_nouns.add(noun["word"])
    udir = UNITS_DIR / unit
    udir.mkdir(parents=True, exist_ok=True)
    write_json(udir / "neutral_nouns.json", noun)
    rows = twin_rows(tok, unit, noun, spec)
    rows.append(render(tok, unit, "novelty", NOVELTY_SEGMENT, spec, template_id="NOV", X=None))
    desc = cap_first(UNITS[unit]["description"])
    for m in UNITS[unit]["modes"]:
        q = cap_first(ASSOCIATION_TEMPLATE.format(x=display_name(unit, m)))
        text = desc + "\n\n" + q
        ids = chat_ids(tok, text)
        rows.append({"pid": f"{unit}|assoc|{m}|-", "unit": unit, "kind": "assoc", "segment": "", "user_text": text,
                     "ids": ids, "P": len(ids), "p0": None, "p1": None, "spec_end": None,
                     "prompt_sha256": sha256_text(json.dumps(ids)), "template_id": "ASSOC", "X": m})
    ptxt = plain_prompt(unit)
    pids = tok(ptxt, add_special_tokens=False)["input_ids"]
    rows.append({"pid": f"{unit}|plain|-|PLAIN", "unit": unit, "kind": "plain", "segment": "", "user_text": ptxt,
                 "ids": pids, "P": len(pids), "p0": None, "p1": None, "spec_end": None,
                 "prompt_sha256": sha256_text(json.dumps(pids)), "template_id": "PLAIN", "X": None})
    pos = {r["template_id"]: {"p0": r["p0"], "p1": r["p1"], "spec_end": r["spec_end"], "P": r["P"],
                              "spec_decoded": tok.decode(r["ids"][r["p1"]:r["spec_end"]]) if r["p1"] else None}
           for r in rows if r["kind"] in ("twin", "novelty")}
    for w, v in pos.items():
        assert v["spec_decoded"] == spec, f"{unit}/{w}: task-spec span does not decode to spec_text"
    write_json(udir / "positions.json", pos)
    ref = None
    for r in rows:
        if r["kind"] in ("twin", "novelty"):
            s = r["ids"][r["p1"]:r["spec_end"]]
            ref = ref or s
            assert s == ref, f"spec tokens differ for {r['pid']}"
    return rows


def build_all(tok: Any, units: list[str]) -> list[dict[str, Any]]:
    existing = read_jsonl(PROMPTS)
    have = {r["unit"] for r in existing}
    used = {r.get("noun") for r in existing if r.get("noun")}
    rows = list(existing)
    for u in units:
        if u in have:
            continue
        rows += build_unit_prompts(tok, u, used)
    pids = [r["pid"] for r in rows]
    assert len(pids) == len(set(pids)), "duplicate prompt ids"
    write_jsonl(PROMPTS, rows)
    return rows


def load_prompts() -> dict[str, dict[str, Any]]:
    out = {r["pid"]: r for r in read_jsonl(PROMPTS)}
    out.update({r["pid"]: r for r in read_jsonl(PROMPTS.parent / "prompts_extra.jsonl")})
    return out
