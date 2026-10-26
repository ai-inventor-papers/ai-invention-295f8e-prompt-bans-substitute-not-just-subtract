#!/usr/bin/env python3
"""Prompt token ids per (unit, template), exactly as the source artifacts fed them.

- Qwen units (A3, B6, B3) and the collapsed twins (T1, T2, T10) for the base sub-arm: the ids stored in
  art_MZAfDPVhM6Ui prompts/prompts7.jsonl (kind 'twin'; chat template with the empty think block).
- Gemma T04/R6: the twin texts of art_zNyBP6zieI5u data/prompts_fed.jsonl rendered as
  '<bos><start_of_turn>user\\n' + text + '<end_of_turn>\\n<start_of_turn>model\\n' (add_special_tokens=False); the ids'
  sha256 (json list) is checked against the exp31 rows' prompt_sha256.
- Llama T1 grid: the five ITER2 exp10 baseline paraphrases s0-s4 (canon/prompts/conditions.json) through the
  Llama-3.1 chat template (vLLM 0.11 rendering: the default system block with the knowledge-cutoff dates); the number
  of prompt tokens is checked against exp10 raw_gen.jsonl (n_prompt_tokens).
- Llama bench: bench.common.prompts.build_baseline(task) (one prompt; the five 'templates' are five slot blocks of the
  same prompt, so the bench units have 100 distinct streams at one prompt).
Writes prompts/prompts8.jsonl and results/prompt_checks.json.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from cfg8 import (INPUTS, ROOT, SRCS, TEMPLATES, UNITS, read_json, read_jsonl, write_json, write_jsonl)

PROMPTS = ROOT / "prompts" / "prompts8.jsonl"
GEMMA_HEAD = "<bos><start_of_turn>user\n"
GEMMA_TAIL = "<end_of_turn>\n<start_of_turn>model\n"


def ids_sha(ids: list[int]) -> str:
    return hashlib.sha256(json.dumps([int(i) for i in ids]).encode()).hexdigest()


def _qwen_rows() -> list[dict[str, Any]]:
    rows = read_jsonl(SRCS["exp35"] / "prompts" / "prompts7.jsonl")
    out = []
    for r in rows:
        if r["kind"] == "twin" and r["unit"] in ("A3", "B6", "B3", "T1", "T2", "T10"):
            out.append({"unit": r["unit"], "w": r["w"], "family": "qwen", "ids": r["ids"], "text": r.get("segment"),
                        "source": "art_MZAfDPVhM6Ui prompts/prompts7.jsonl", "prompt_sha256": ids_sha(r["ids"])})
    return out


def _gemma_rows(tok: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    pf = read_jsonl(SRCS["exp31"] / "data" / "prompts_fed.jsonl")
    raw = read_jsonl(SRCS["exp31"] / "data" / "raw_s3.jsonl")
    want = {(r["task"], r["template"]): r["prompt_sha256"] for r in raw if r["arm"] == "twin"}
    out, checks = [], {}
    for task, unit in (("T04", "G-T04"), ("R6", "G-R6")):
        for w in TEMPLATES:
            cand = [p for p in pf if p.get("kind") == "twin" and p.get("task") == task and
                    str(p.get("cond", "")).endswith(":" + w)]
            assert len(cand) >= 1, (task, w)
            text = cand[0]["text"]
            rendered = tok.apply_chat_template([{"role": "user", "content": text}], tokenize=False,
                                               add_generation_prompt=True)
            assert rendered == GEMMA_HEAD + text + GEMMA_TAIL, "unexpected Gemma chat rendering"
            ids = tok(rendered, add_special_tokens=False)["input_ids"]
            ok = ids_sha(ids) == want.get((task, w))
            checks[f"{unit}:{w}"] = {"sha_match_exp31": ok, "n": len(ids)}
            out.append({"unit": unit, "w": w, "family": "gemma", "ids": ids, "text": text,
                        "source": "art_zNyBP6zieI5u data/prompts_fed.jsonl", "prompt_sha256": ids_sha(ids)})
    return out, checks


def _find_baseline(d: Any) -> list[dict[str, Any]] | None:
    if isinstance(d, dict):
        for k, v in d.items():
            if k == "baseline" and isinstance(v, list) and v and isinstance(v[0], dict) and "prompt" in v[0]:
                return v
            got = _find_baseline(v)
            if got:
                return got
    elif isinstance(d, list):
        for v in d:
            got = _find_baseline(v)
            if got:
                return got
    return None


def _llama_rows(tok: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    conds = read_json(SRCS["exp10"] / "canon" / "prompts" / "conditions.json")
    base = _find_baseline(conds.get("tasks", {}).get("t1", conds)) or _find_baseline(conds)
    base = sorted(base, key=lambda b: b["paraphrase_id"])
    raw = read_jsonl(SRCS["exp10"] / "data" / "raw_gen.jsonl")
    n_want = {}
    for r in raw:
        if r["task"] == "t1" and r["condition"].startswith("baseline:s"):
            n_want[int(r["condition"].split(":s")[1])] = r["n_prompt_tokens"]
    out, checks = [], {}
    for i, w in enumerate(TEMPLATES):
        text = base[i]["prompt"]
        ids = tok.apply_chat_template([{"role": "user", "content": text}], tokenize=True, add_generation_prompt=True)
        ids = list(ids["input_ids"] if isinstance(ids, dict) else ids)
        checks[f"L-T1:{w}"] = {"n": len(ids), "n_exp10": n_want.get(i), "match": n_want.get(i) == len(ids)}
        out.append({"unit": "L-T1", "w": w, "family": "llama", "ids": ids, "text": text,
                    "source": "ITER2 exp10 canon/prompts/conditions.json baseline s%d" % i,
                    "prompt_sha256": ids_sha(ids)})
    # bench candidates: the frozen bench's baseline prompt
    sys.path.insert(0, str(INPUTS / "iter6_exp30" / "inputs" / "exp11"))
    from bench.common.prompts import build_baseline  # noqa: E402
    for u, spec in UNITS.items():
        if spec["family"] != "llama" or spec["task"] == "T1":
            continue
        text = build_baseline(spec["task"])
        ids = tok.apply_chat_template([{"role": "user", "content": text}], tokenize=True, add_generation_prompt=True)
        ids = list(ids["input_ids"] if isinstance(ids, dict) else ids)
        for w in TEMPLATES:
            out.append({"unit": u, "w": w, "family": "llama", "ids": ids, "text": text,
                        "source": "ITER2 exp11 bench.common.prompts.build_baseline", "prompt_sha256": ids_sha(ids)})
        checks[f"{u}"] = {"n": len(ids)}
    return out, checks


def build_all() -> list[dict[str, Any]]:
    from transformers import AutoTokenizer

    from cfg8 import FAMILIES, model_path
    rows = _qwen_rows()
    checks: dict[str, Any] = {}
    tg = AutoTokenizer.from_pretrained(model_path(FAMILIES["gemma"]["model_id"], FAMILIES["gemma"]["rev"]))
    g, c = _gemma_rows(tg)
    rows += g
    checks.update(c)
    tl = AutoTokenizer.from_pretrained(model_path(FAMILIES["llama"]["model_id"], FAMILIES["llama"]["rev"]))
    lr, c = _llama_rows(tl)
    rows += lr
    checks.update(c)
    write_jsonl(PROMPTS, rows)
    write_json(ROOT / "results" / "prompt_checks.json", checks)
    logger.info(f"prompts8: {len(rows)} prompt rows; checks {checks}")
    return rows


def load_prompts() -> dict[tuple[str, str], dict[str, Any]]:
    return {(r["unit"], r["w"]): r for r in read_jsonl(PROMPTS)}


if __name__ == "__main__":
    build_all()
