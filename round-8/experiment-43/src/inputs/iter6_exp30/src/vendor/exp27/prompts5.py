#!/usr/bin/env python3
"""S0.6: every stage-1 prompt, chat-rendered with the Qwen3 template (thinking off) -> prompts/prompts.jsonl.

Kinds from exp19 prompts_v4.build_all (asserted against exp8/exp13/exp17 ids): twin (W1-W5), plain, nonce, novelty
(frame-free, exp19 definition), semseed (T1/T2), vs. Added here, FRAME-MATCHED samplers: user text =
cap_first(the twin's W-sentence) + ' ' + INSTR + blank line + spec, for INSTR in {IFG_INSTR, PSL_A, EAP_A}
(kinds 'ifg', 'psl', 'eap'). The IFG kind carries the forced assistant prefix 'Intent:' (forced_ids), appended to
the prompt ids at generation time. Assertions: the token ids from the first 'Task:' token to the end of the prompt are
identical across every kind of a task (prompts_v4.check_and_report); the forced prefix re-tokenises identically in
context; the grep audit finds no catalogue display name or alias inside any W-template prohibition.
Multi-turn rendering (PSL stages B/C, EAP stage B): render_history() asserts that every earlier assistant text
appears verbatim in the decoded ids.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger

from cfg import BENCH, RESULTS_DIR, model_path, read_json, read_jsonl, sha256_text, write_json, write_jsonl
from cfg5 import EAP_A, IFG_INSTR, INTENT_PREFIX, PROMPTS5, PSL_A, TASKS15
import prompts_v4 as P4

FRAMED = {"ifg": IFG_INSTR, "psl": PSL_A, "eap": EAP_A}


def load_tokenizer():
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(model_path())


def catalogue_names(task: str) -> list[str]:
    if task in ("T1", "T2"):
        return []
    sp = read_json(BENCH / P4.bench_dir(task) / "spec.json")
    return [c["display_name"] for c in sp["catalogue"]] + [a for v in sp.get("aliases", {}).values() for a in v]


def forced_intent_ids(tok: Any, prompt_ids: list[int]) -> list[int]:
    f = tok(INTENT_PREFIX, add_special_tokens=False)["input_ids"]
    text = tok.decode(prompt_ids + f, skip_special_tokens=False)
    re_ids = tok(text, add_special_tokens=False)["input_ids"]
    assert re_ids == prompt_ids + f, "forced 'Intent:' ids are not stable in context"
    return f


def render_history(tok: Any, history: list[dict[str, str]]) -> list[int]:
    ids = tok.apply_chat_template(history, tokenize=True, add_generation_prompt=True, enable_thinking=False)
    if isinstance(ids, dict):
        ids = ids["input_ids"]
    ids = list(ids)
    dec = tok.decode(ids, skip_special_tokens=False)
    for m in history:
        if m["role"] == "assistant":
            assert m["content"] in dec, "an earlier assistant text is not verbatim in the rendered history"
    return ids


def build(tok: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = P4.build_all(tok)
    twins = {(r["task"], r["w"]): r for r in rows if r["kind"] == "twin"}
    specs = {}
    for r in rows:
        if r["kind"] == "plain":
            specs[r["task"]] = r["user_text"]
    extra = []
    for (t, w), tw in sorted(twins.items()):
        for kind, instr in FRAMED.items():
            seg = tw["segment"] + " " + instr
            rec = P4.record(tok, t, w, kind, seg, specs[t], source=f"frame-matched {kind}: twin {w} sentence + INSTR")
            if kind == "ifg":
                rec["forced_ids"] = forced_intent_ids(tok, rec["ids"])
            extra.append(rec)
    rows = rows + extra
    rep = P4.check_and_report(rows)
    # grep audit: no catalogue display name / alias in any W-template prohibition (twin segment)
    hits = []
    for (t, w), tw in twins.items():
        for a in catalogue_names(t):
            if re.search(rf"\b{re.escape(a.lower())}\b", tw["segment"].lower()):
                hits.append({"task": t, "w": w, "name": a})
    # model-facing positive instructions (frame-matched) are allowed to name nothing; log any catalogue word in them
    instr_hits = []
    for t in TASKS15:
        for kind, instr in FRAMED.items():
            for a in catalogue_names(t):
                if re.search(rf"\b{re.escape(a.lower())}\b", instr.lower()):
                    instr_hits.append({"task": t, "kind": kind, "name": a})
    rep["w_template_alias_audit_hits"] = hits
    rep["instruction_alias_hits"] = instr_hits
    rep["n_prompts_total"] = len(rows)
    rep["kinds"] = sorted({r["kind"] for r in rows})
    rep["prompt_sha256"] = {f"{r['task']}|{r['w']}|{r['kind']}": r["prompt_sha256"] for r in rows}
    assert not hits, f"catalogue name inside a W-template prohibition: {hits}"
    return rows, rep


def stage_prompts() -> dict[str, Any]:
    tok = load_tokenizer()
    rows, rep = build(tok)
    PROMPTS5.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(PROMPTS5, rows)
    write_json(RESULTS_DIR / "prompt_report.json", rep)
    logger.info(f"prompts: {len(rows)} rendered ({rep['kinds']}); spec ids identical across kinds; audits clean")
    return rep


def load_prompts() -> dict[tuple[str, str, str], dict[str, Any]]:
    return {(r["task"], r["w"], r["kind"]): r for r in read_jsonl(PROMPTS5)}


def prompt_for(prompts: dict, task: str, w: str, kind: str) -> dict[str, Any]:
    if kind in ("novelty", "plain", "vs"):
        return prompts[(task, "ALL", kind)]
    return prompts[(task, w, kind)]


if __name__ == "__main__":
    from cfg import setup_logging

    setup_logging("prompts5")
    stage_prompts()
