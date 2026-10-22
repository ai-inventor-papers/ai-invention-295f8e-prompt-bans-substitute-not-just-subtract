#!/usr/bin/env python3
"""Prompt rendering for the panel-I units (plan S1b). One tokenizer -- the INSTRUCT model's -- renders every prompt and
both models are fed the identical ids (asserted against the base tokenizer in tests/test_cpu.py).

kinds (pid = unit|kind|X|template):
- twin    W1-W5 neutral-noun twins: TEMPLATES[w] with the unit's noun + d x ' .' padding, d = max(0, tokens(display name
          of the dataset-reference mode as rendered in the slot) - tokens(noun as rendered in the slot));
- plain   base-model plain completion: an opened ```python fence + 'def solve(...):' + a docstring (the description);
- forced  'Implement X' prompts: one FORCED_WORDINGS[F] sentence naming mode X + two newlines + SPEC (5 wordings/mode);
- assoc   'What is the standard alternative to <x> for this task? ...' per catalogue mode (description + question,
          exactly as iteration 5; the FORMAT_LINE is omitted because the answer is one sentence);
- intent  base-intent prompt: twin text + SPEC + INTENT_SUFFIX, assistant prefix 'Approach:' (max 48 tokens);
- bint    instruct code prompt: twin text + SPEC + ' Planned approach: <intent sentence>' (rendered after the base
          intents exist, src/bint6.py).
The GREP AUDIT (audit_prompts) and its planted-ban positive control are part of commit #0.
"""

from __future__ import annotations

import json
import re
from typing import Any

from cfg6 import (ASSOCIATION_TEMPLATE, BINT_SUFFIX, FORCED_WORDINGS, INPUTS, INTENT_PREFIX, INTENT_SUFFIX,
                  PAD_FILLER, PROHIBITION_CUES, PROMPTS, TEMPLATE_IDS, TEMPLATE_TAIL, TEMPLATES, UNITS_DIR, VENDOR,
                  cap_first, read_json, read_jsonl, sha256_text, write_json, write_jsonl)
from units_spec6 import UNITS, banned_words, catalogue_names, display_name, mechanism, spec_text

EXP7_EXCLUSIONS = ['ass', 'bucket', 'chain', 'edge', 'game', 'graph', 'grid', 'head', 'heap', 'key', 'line', 'link',
                   'list', 'map', 'maze', 'net', 'node', 'path', 'point', 'queue', 'ring', 'road', 'route', 'search',
                   'stack', 'step', 'street', 'table', 'track', 'train', 'tree', 'walk', 'way', 'web']


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


def _row(unit: str, kind: str, X: str | None, w: str | None, text: str, ids: list[int], **meta: Any) -> dict[str, Any]:
    pid = "|".join(str(x) for x in (unit, kind, X or "-", w or "-"))
    return {"pid": pid, "unit": unit, "kind": kind, "X": X, "template_id": w, "user_text": text, "ids": ids,
            "P": len(ids), "prompt_sha256": sha256_text(json.dumps(ids)), **meta}


def noun_bank() -> list[dict[str, Any]]:
    src = read_json(INPUTS / "sources.json")["nouns"]
    p = VENDOR / "exp7" / "frozen" / "templates_nouns_padding.json"
    excl = set(read_json(p)["templates"]["noun_exclusions"]) if p.exists() else set(EXP7_EXCLUSIONS)
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
        bans |= {w for w in catalogue_names(u) if " " not in w}
    cands = []
    for e in noun_bank():
        if e["word"] in bans or e["word"] in used:
            continue
        k = len(tok(" " + e["word"], add_special_tokens=False)["input_ids"])
        cands.append((abs(k - nt), -e["freq"], e["word"], k))
    cands.sort()
    d, nf, w, k = cands[0]
    return {"word": w, "qwen3_tokens_ws": k, "subtlex_freq": -nf, "display_name": name, "name_tokens_ws": nt,
            "abs_diff": d, "rule": "rank |tokens(' ' + noun) - tokens(' ' + name)|, ties -> higher SUBTLEX frequency; "
                                   "exp7 exclusions, banned words, catalogue words and nouns of other units skipped"}


def twin_segment(tok: Any, w: str, noun: str, xname: str) -> tuple[str, int]:
    lead = TEMPLATES[w].startswith("{N}")
    xr = cap_first(xname) if lead else " " + xname
    nr = cap_first(noun) if lead else " " + noun
    d = len(tok(xr, add_special_tokens=False)["input_ids"]) - len(tok(nr, add_special_tokens=False)["input_ids"])
    d = max(0, d)
    return TEMPLATES[w].format(N=noun) + PAD_FILLER * d, d


def render_spec_prompt(tok: Any, unit: str, kind: str, X: str | None, w: str | None, segment: str, spec: str,
                       **meta: Any) -> dict[str, Any]:
    text = cap_first(segment) + "\n\n" + spec
    ids = chat_ids(tok, text)
    p0, p1, se = positions(tok, ids, spec)
    return _row(unit, kind, X, w, text, ids, segment=cap_first(segment), p0=p0, p1=p1, spec_end=se, **meta)


def plain_prompt(unit: str) -> str:
    u = UNITS[unit]
    return f'```python\ndef {u["signature"]}:\n    """{cap_first(u["description"])}\n    """\n'


def build_unit_prompts(tok: Any, unit: str, used_nouns: set[str]) -> list[dict[str, Any]]:
    spec = spec_text(unit)
    noun = pick_noun(tok, unit, used_nouns)
    used_nouns.add(noun["word"])
    udir = UNITS_DIR / unit
    udir.mkdir(parents=True, exist_ok=True)
    write_json(udir / "neutral_noun.json", noun)
    rows: list[dict[str, Any]] = []
    for w in TEMPLATE_IDS:
        seg, d = twin_segment(tok, w, noun["word"], noun["display_name"])
        rows.append(render_spec_prompt(tok, unit, "twin", None, w, seg, spec, noun=noun["word"], n_pad=d))
        # base-intent prompt: twin text + SPEC + intent suffix, assistant prefix 'Approach:'
        text = cap_first(seg) + "\n\n" + spec + INTENT_SUFFIX
        ids = chat_ids(tok, text) + tok(INTENT_PREFIX, add_special_tokens=False)["input_ids"]
        rows.append(_row(unit, "intent", None, w, text, ids, assistant_prefix=INTENT_PREFIX, noun=noun["word"]))
    for m in UNITS[unit]["modes"]:
        for f, tpl in FORCED_WORDINGS.items():
            seg = tpl.format(dn=display_name(unit, m), mech=mechanism(unit, m))
            rows.append(render_spec_prompt(tok, unit, "forced", m, f, seg, spec))
        q = cap_first(ASSOCIATION_TEMPLATE.format(x=display_name(unit, m)))
        text = cap_first(UNITS[unit]["description"]) + "\n\n" + q
        rows.append(_row(unit, "assoc", m, "ASSOC", text, chat_ids(tok, text)))
    ptxt = plain_prompt(unit)
    rows.append(_row(unit, "plain", None, "PLAIN", ptxt, tok(ptxt, add_special_tokens=False)["input_ids"]))
    # every twin/forced prompt must carry the identical task-spec token span
    ref = None
    for r in rows:
        if r["kind"] in ("twin", "forced"):
            s = r["ids"][r["p1"]:r["spec_end"]]
            assert tok.decode(s) == spec, f"{r['pid']}: task-spec span does not decode to the spec"
            ref = ref or s
            assert s == ref, f"spec tokens differ for {r['pid']}"
    write_json(udir / "positions.json", {r["template_id"]: {"p0": r["p0"], "p1": r["p1"], "spec_end": r["spec_end"],
                                                           "P": r["P"]} for r in rows if r["kind"] == "twin"})
    return rows


def render_bint(tok: Any, unit: str, w: str, k: int, intent: str, twin_row: dict[str, Any]) -> dict[str, Any]:
    """BINT code prompt for slot (w, k): twin text + SPEC + ' Planned approach: <intent>' (knob only)."""
    spec = spec_text(unit)
    text = twin_row["segment"] + "\n\n" + spec + BINT_SUFFIX.format(intent=intent.strip())
    return _row(unit, "bint", str(k), w, text, chat_ids(tok, text), intent=intent.strip())


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
    return {r["pid"]: r for r in read_jsonl(PROMPTS)}


# ------------------------------------------------------------------------------------------------ grep audit
def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def _has(term: str, low: str) -> bool:
    if re.search(r"[a-z]", term):
        return re.search(r"(?<![a-z0-9_])" + re.escape(term) + r"(?![a-z0-9_])", low) is not None
    return term in low


def audit_text(unit: str, kind: str, text: str) -> dict[str, list[str]]:
    """(1) name hits in twin/plain/intent/bint text (the task description and the format line are already banned-word
    audited; a forced or association prompt names its mode by design); (2) prohibition cue + name in one sentence."""
    names = catalogue_names(unit)
    low = text.lower()
    for wl in UNITS[unit].get("whitelist", []):
        low = low.replace(wl.lower(), " ")
    name_hits = [n for n in names if _has(n, low)] if kind in ("twin", "plain", "intent", "bint") else []
    cue_pairs = []
    for s in _sentences(low):
        cues = [c for c in PROHIBITION_CUES if _has(c, s)]
        if cues:
            hit = [n for n in names if _has(n, s)]
            if hit:
                cue_pairs.append(f"{cues[0]} + {hit[0]} :: {s[:80]}")
    return {"name_hits": name_hits, "cue_name_pairs": cue_pairs}


def audit_prompts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    res: dict[str, Any] = {"n_prompts": len(rows), "violations": [], "by_kind": {}}
    for r in rows:
        a = audit_text(r["unit"], r["kind"], r["user_text"])
        res["by_kind"].setdefault(r["kind"], 0)
        res["by_kind"][r["kind"]] += 1
        if a["name_hits"] or a["cue_name_pairs"]:
            res["violations"].append({"pid": r["pid"], **a})
    # planted positive control: a real ban sentence must be caught
    planted = []
    for u in sorted({r["unit"] for r in rows}):
        x = display_name(u, UNITS[u]["dataset_reference_mode"])
        a = audit_text(u, "twin", f"Do not use {x} for this task.\n\n{spec_text(u)}")
        planted.append({"unit": u, "caught": bool(a["name_hits"]) and bool(a["cue_name_pairs"])})
    res["planted_control"] = planted
    res["pass"] = not res["violations"] and all(p["caught"] for p in planted)
    return res
