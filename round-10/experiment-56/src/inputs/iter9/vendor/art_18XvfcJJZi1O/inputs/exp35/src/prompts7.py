#!/usr/bin/env python3
"""Prompts of iteration 7 (built once, CPU) -> prompts/prompts7.jsonl + prompts/positions7.json.

Per mixed unit (B3, A3, B6) and template W1-W5:
  twin    the iteration-5 twin token ids reused verbatim (B3/B6: exp26 data/prompts.jsonl; A3: exp25
          prompts_new.jsonl) - neutral noun + ' .' padding (the exp22 R2 rule)
  ban     the same frame with the DEFAULT's display name, padded with ' .' to the twin's length when shorter (built
          with the same chat template; identical ids from 'Task:' on; used only for the S4(a) dose n[l,p])
Per mixed unit (template-free):
  forced      'Implement <A_min display name> for this task.' + spec (iteration-6 forced-builder wording)
  forced_pad  its padding twin: the instruction tokens replaced by ' .' (identical ids from p1 on)
Collapsed tasks T1, T2, T10, T03: the iteration-6 twins (prompts6.jsonl kind 'twin', W1-W5).
"""

from __future__ import annotations

import json
from typing import Any

from cfg7 import (BAN_TEMPLATES, E25, E26, I6, PAD_FILLER, ROOT, TEMPLATE_TAIL, TEMPLATES, UNITS, read_jsonl,
                  sha256_text, write_json, write_jsonl)

PROMPTS7 = ROOT / "prompts" / "prompts7.jsonl"
POSITIONS7 = ROOT / "prompts" / "positions7.json"


def cap_first(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


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


def _rec(unit: str, w: str, kind: str, ids: list[int], p0: int, p1: int, se: int, segment: str,
         **extra: Any) -> dict[str, Any]:
    return {"unit": unit, "w": w, "kind": kind, "ids": ids, "P": len(ids), "p0": p0, "p1": p1, "spec_end": se,
            "segment": segment, "prompt_sha256": sha256_text(json.dumps(ids)), **extra}


def spec_of(tok: Any, twin: dict[str, Any]) -> str:
    return tok.decode(twin["ids"][twin["p1"]:twin["spec_end"]])


def pad_record(tok: Any, src: dict[str, Any], kind: str) -> dict[str, Any]:
    """Iteration-6 gpu6.pad_record: the condition segment's tokens [p0, k) replaced by ' .' (k = p1 minus the blank
    line tokens), so length and every id from 'Task:' on are identical."""
    dot = tok(" .", add_special_tokens=False)["input_ids"]
    assert len(dot) == 1
    ids = list(src["ids"])
    c0, k = src["p0"], src["p1"]
    while k > c0 and "\n" in tok.decode([ids[k - 1]]):
        k -= 1
    for i in range(c0, k):
        ids[i] = dot[0]
    return _rec(src["unit"], src["w"], kind, ids, src["p0"], src["p1"], src["spec_end"], tok.decode(ids[c0:k]),
                cond=[c0, k], source=f"padding twin of {src['kind']}")


def build(tok: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    e26 = {(r["unit"], r["template_id"]): r for r in read_jsonl(E26 / "data" / "prompts.jsonl") if r["kind"] == "twin"}
    e25 = {(r["task"], r["w"]): r for r in read_jsonl(E25 / "data" / "prompts_new.jsonl") if r["kind"] == "twin"}
    for u, U in UNITS.items():
        for w in TEMPLATES:
            src = e26[(u, w)] if U["src"] == "exp26" else e25[(u, w)]
            ids = src["ids"] if isinstance(src["ids"], list) else json.loads(src["ids"])
            twin = _rec(u, w, "twin", ids, src["p0"], src["p1"], src["spec_end"], src["segment"],
                        noun=src.get("noun"), n_pad=src.get("n_pad"), source=f"iteration-5 {U['src']} twin ids")
            spec = spec_of(tok, twin)
            p0, p1, se = positions(tok, ids, spec)
            assert (p0, p1, se) == (twin["p0"], twin["p1"], twin["spec_end"]), (u, w)
            rows.append(twin)
            # ban of the default, padded to the twin's length
            xname = U["display"][U["default"]]
            frame = BAN_TEMPLATES[w][0]
            xr = cap_first(xname) if frame.startswith("{X}") else xname
            seg = frame.format(X=xr)
            for npad in range(0, 12):
                text = cap_first(seg + PAD_FILLER * npad) + "\n\n" + spec
                bids = chat_ids(tok, text)
                if len(bids) >= len(ids):
                    break
            bp0, bp1, bse = positions(tok, bids, spec)
            rows.append(_rec(u, w, "ban", bids, bp0, bp1, bse, seg + PAD_FILLER * npad, n_pad=npad,
                             len_match=len(bids) == len(ids), X=U["default"]))
        # forced 'Implement A_min' + padding twin (template-free)
        spec = spec_of(tok, rows[-2])
        tw_sum = ROOT / "results" / "twins.json"
        a_min = (json.loads(tw_sum.read_text()).get(u, {}).get("a_min") if tw_sum.exists() else None) \
            or U["a_min_plan"]
        seg = f"Implement {U['display'][a_min]} for this task."
        fids = chat_ids(tok, cap_first(seg) + "\n\n" + spec)
        fp0, fp1, fse = positions(tok, fids, spec)
        frec = _rec(u, "F", "forced", fids, fp0, fp1, fse, seg, Y=a_min)
        rows += [frec, pad_record(tok, frec, "forced_pad")]
    for r in read_jsonl(I6 / "prompts" / "prompts6.jsonl"):
        if r["kind"] == "twin" and r["task"] in ("T1", "T2", "T10", "T03"):
            rows.append(_rec(r["task"], r["w"], "twin", r["ids"], r.get("p0") or 3, r["p1"], r["spec_end"],
                             r.get("segment") or "", source="iteration-6 prompts6.jsonl twin"))
    return rows


def write_prompts(tok: Any) -> list[dict[str, Any]]:
    rows = build(tok)
    write_jsonl(PROMPTS7, rows)
    pos = {f"{r['unit']}|{r['w']}|{r['kind']}": {"P": r["P"], "p0": r["p0"], "p1": r["p1"],
                                                 "spec_end": r["spec_end"]} for r in rows}
    write_json(POSITIONS7, pos)
    return rows


def load_prompts() -> dict[tuple[str, str, str], dict[str, Any]]:
    return {(r["unit"], r["w"], r["kind"]): r for r in read_jsonl(PROMPTS7)}


def u3_checks(tok: Any, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """U3: spec span decodes identically, ban/twin ids identical from p1 on (same length when padded), forced and
    padding twin identical from p1 on."""
    P = {(r["unit"], r["w"], r["kind"]): r for r in rows}
    out: dict[str, Any] = {}
    for u in UNITS:
        spec0 = None
        for w in TEMPLATES:
            tw, bn = P[(u, w, "twin")], P[(u, w, "ban")]
            s = tw["ids"][tw["p1"]:tw["spec_end"]]
            spec0 = spec0 or s
            out[f"{u}|{w}|spec_same_across_templates"] = s == spec0
            out[f"{u}|{w}|ban_twin_same_from_p1"] = bn["ids"][bn["p1"]:] == tw["ids"][tw["p1"]:]
            out[f"{u}|{w}|ban_twin_same_length"] = bn["P"] == tw["P"]
        f, fp = P[(u, "F", "forced")], P[(u, "F", "forced_pad")]
        out[f"{u}|forced_pad_same_from_p1"] = f["ids"][f["p1"]:] == fp["ids"][fp["p1"]:] and f["P"] == fp["P"]
        out[f"{u}|forced_spec_same"] = f["ids"][f["p1"]:f["spec_end"]] == spec0
    out["all_pass_required"] = all(v for k, v in out.items() if "same_length" not in k)
    return out
