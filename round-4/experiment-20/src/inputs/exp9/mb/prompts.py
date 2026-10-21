#!/usr/bin/env python3
"""S1 FREEZE PROMPTS: catalogues, forced / baseline / W1-W5 ban-mention-neutral segments, neutral nouns, padding.

Prompt = Capitalise(segment) + '\\n\\n' + SPEC[task]. Multi-name {X}: display names joined 'A, B, C, D or E', in the
canonical list order of the banned set rotated by (w-1) for template w; mention and neutral twins use the identical
order (each name replaced by its own noun in the neutral twin). Multi-ban prompts for TOP/ARC/SCATTER are built by
the same functions at S7 (after set selection) and committed before any of them is sampled.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from loguru import logger

from common import (ALIASES, CANON, CATALOGUE, DESCRIPTIVE, DS_FILE, FORCED_NEW, FORCED_NEW_PLANNED_DUPLICATE, MODEL_ID,
                    MODES, NONCE_NAME, PAD_FILLER, PROMPT_DIR, TASKS, W_TEMPLATES, cap_first, commit_payload,
                    deviation, join_names_or, rotate, sha256_file, spec_text, write_json)

FROZEN = PROMPT_DIR / "frozen_prompts.json"
EXPECTED_TAIL = "<|im_start|>assistant\n<think>\n\n</think>\n\n"
# Nouns that contain an alias-lexicon string or name a data-structure / graph / grid / computing concept would prime
# algorithmic content, so they are not neutral here (logged in frozen_prompts.json -> noun_exclusions).
NOUN_EXCLUDE = {"tree", "map", "stack", "queue", "heap", "graph", "grid", "bucket", "list", "table", "key", "path",
                "node", "edge", "set", "array", "matrix", "net", "web", "chain", "ladder", "bridge", "wall", "cell",
                "road", "street", "maze", "point", "jump", "search", "star", "circle", "line", "box", "door", "gate",
                "window", "room", "computer", "program", "code", "file",
                # profanity / vulgar words are not neutral either
                "ass", "butt", "shit", "crap", "dick", "cock", "bitch", "hell", "damn", "sex", "pussy", "fuck", "boob"}


@lru_cache(maxsize=1)
def tokenizer():
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(MODEL_ID)


def n_tokens(text: str) -> int:
    return len(tokenizer().encode(text, add_special_tokens=False))


def chat_text(prompt: str) -> str:
    t = tokenizer().apply_chat_template([{"role": "user", "content": prompt}], tokenize=False, add_generation_prompt=True,
                                        enable_thinking=False)
    assert t.endswith(EXPECTED_TAIL), f"unexpected chat-template tail {t[-60:]!r}"
    return t


def make_prompt(task: str, segment: str) -> str:
    return cap_first(segment) + "\n\n" + spec_text(task)


def load_canon_conditions() -> dict[str, Any]:
    return json.loads((CANON / "prompts" / "conditions.json").read_text())


def forced_templates() -> list[str]:
    canon = load_canon_conditions()["templates"]["forced"]
    assert len(canon) == 5
    assert FORCED_NEW_PLANNED_DUPLICATE in canon, "planned duplicate template not found in exp1 forced templates"
    deviation("D-forced-dup", "The plan's new forced paraphrase 'Solve this task with {j}.' is verbatim exp1 forced "
                              "template 3, so it was replaced by 'Apply {j} to solve this task.' to keep 10 distinct "
                              "paraphrases.")
    out = list(canon) + list(FORCED_NEW)
    assert len(set(out)) == 10
    return out


def descriptive_variant(template: str, key: str) -> str:
    """'Implement {X} for this task.' -> 'Implement {X} for this task: <description>.'"""
    t = template.rstrip()
    if t.endswith("."):
        t = t[:-1]
    return t + ": " + DESCRIPTIVE[key] + "."


def neutral_nouns(names_by_task: dict[str, list[str]]) -> dict[str, dict[str, list[str]]]:
    """For each display name (in catalogue order, then the nonce), the two candidate nouns whose Qwen3 token count
    (leading space) is closest to the name's; ties by higher SUBTLEX frequency; never reused within a task."""
    data = json.loads(DS_FILE.read_text())
    cn = next(ds for ds in data["datasets"] if ds["dataset"] == "concreteness_norms")["examples"]
    del data
    cands = []
    for e in cn:
        if str(e.get("metadata_noun_bank_candidate")).lower() != "true":
            continue
        w = str(e["input"]).strip()
        if w.lower() in NOUN_EXCLUDE or not w.isalpha():
            continue
        if any(a in w.lower() for fam in ALIASES.values() for a in fam if a.isalpha() and len(a) >= 3):
            continue
        cands.append({"noun": w, "tok": int(float(e["metadata_qwen3_tokens_with_leading_space"])),
                      "freq": float(e.get("metadata_subtlex_frequency") or 0)})
    logger.info(f"neutral-noun candidates after exclusions: {len(cands)}")
    out: dict[str, dict[str, list[str]]] = {}
    for task, names in names_by_task.items():
        used: set[str] = set()
        out[task] = {}
        for name in names:
            nt = n_tokens(" " + name)
            ranked = sorted((c for c in cands if c["noun"] not in used),
                            key=lambda c: (abs(c["tok"] - nt), -c["freq"], c["noun"]))
            pick = [ranked[0]["noun"], ranked[1]["noun"]]
            used.update(pick)
            out[task][name] = pick
    return out


def pad_to(seg: str, ref_len: int) -> tuple[str, int]:
    """Append PAD_FILLER while it reduces |len(seg) - ref_len|; returns (segment, n_fillers)."""
    k = 0
    cur = seg
    while True:
        nxt = cur + PAD_FILLER
        if abs(n_tokens(cap_first(nxt)) - ref_len) < abs(n_tokens(cap_first(cur)) - ref_len):
            cur = nxt
            k += 1
        else:
            return cur, k


def triplet(task: str, names: list[str], w: int, nouns: dict[str, list[str]], half: int) -> dict[str, Any]:
    """Ban / mention / neutral segments for template index w (0-based) and the given ordered name list.
    The neutral twin uses noun A (half=1) or noun B (half=2) for each name. Token lengths logged; any pair differing
    by more than 3 tokens has the shorter (neutral or mention) padded with ' Thanks.' to the ban length."""
    tpl = W_TEMPLATES[w]
    x = join_names_or(names)
    nn = join_names_or([nouns[nm][half - 1] for nm in names])
    seg = {"ban": tpl["ban"].replace("{X}", x), "mention": tpl["mention"].replace("{X}", x),
           "neutral": tpl["neutral"].replace("{N}", nn)}
    seg = {k: cap_first(v) for k, v in seg.items()}
    lens = {k: n_tokens(v) for k, v in seg.items()}
    pads = {}
    for k in ("mention", "neutral"):
        if abs(lens[k] - lens["ban"]) > 3:
            if lens[k] < lens["ban"]:
                seg[k], pads[k] = pad_to(seg[k], lens["ban"])
            else:
                pads["ban_vs_" + k] = "ban shorter (not padded: the sampled ban prompt stays filler-free)"
            lens[k] = n_tokens(seg[k])
    return {"segments": seg, "tokens": lens, "padding": pads,
            "prompts": {k: make_prompt(task, v) for k, v in seg.items()}}


def multi_names(task: str, keys: list[str], w: int) -> list[str]:
    """Display names of the banned set in canonical list order rotated by w (0-based template index)."""
    order = [k for k in MODES[task] if k in keys]
    return [CATALOGUE[task][k] for k in rotate(order, w)]


def build_frozen() -> dict[str, Any]:
    canon = load_canon_conditions()
    for task in TASKS:
        assert canon["spec"][task] == spec_text(task), f"SPEC mismatch with exp1 for {task}"
    base_tpls = canon["templates"]["baseline"]
    assert len(base_tpls) == 10
    ftpl = forced_templates()
    names = {t: list(CATALOGUE[t].values()) + ([NONCE_NAME] if t == "t1" else []) for t in TASKS}
    nouns = neutral_nouns(names)
    frozen: dict[str, Any] = {"model": MODEL_ID, "rules": {
        "prompt": "Capitalise(segment) + blank line + SPEC[task]; SPEC = DESCRIPTION + blank line + FORMAT (exp1)",
        "chat": "tokenizer.apply_chat_template(user prompt, add_generation_prompt=True, enable_thinking=False); "
                "ends with the empty think block",
        "multi_name": "display names joined 'A, B, C, D or E' in canonical list order of the banned set rotated by "
                      "(w-1) for template w; mention and neutral twins use the identical order",
        "neutral": "each display name replaced by its own noun (noun A for program half 1, noun B for half 2)",
        "padding": "if ban and neutral (or mention) segments differ by > 3 tokens, the shorter twin is padded with "
                   "' Thanks.' repeated to the ban length",
        "descriptive": "used for an algorithm only if the smoke stage labels fewer than 7 of its 10 programs as "
                       "requested; template minus final period + ': ' + description + '.'"},
        "catalogue": CATALOGUE, "canonical_order": MODES, "neutral_nouns": nouns, "w_templates": W_TEMPLATES,
        "noun_exclusions": sorted(NOUN_EXCLUDE) + ["any noun containing an alias-lexicon string of >= 3 letters"],
        "nonce_name": NONCE_NAME, "forced_templates": ftpl, "baseline_templates": base_tpls,
        "descriptive": DESCRIPTIVE, "tasks": {}}
    for task in TASKS:
        tnouns = nouns[task]
        conds: dict[str, Any] = {}
        conds["baseline"] = [{"paraphrase_id": i, "segment": s, "prompt": make_prompt(task, s)}
                             for i, s in enumerate(base_tpls)]
        for key, nm in CATALOGUE[task].items():
            conds[f"forced:{key}"] = [{"paraphrase_id": i, "segment": cap_first(t.replace("{X}", nm)),
                                       "prompt": make_prompt(task, t.replace("{X}", nm))} for i, t in enumerate(ftpl)]
            if key in DESCRIPTIVE:
                conds[f"forced_desc:{key}"] = [
                    {"paraphrase_id": i, "segment": cap_first(descriptive_variant(t, key).replace("{X}", nm)),
                     "prompt": make_prompt(task, descriptive_variant(t, key).replace("{X}", nm))}
                    for i, t in enumerate(ftpl)]
        # single bans of every catalogue algorithm (only the modal one is sampled; all are frozen for scoring)
        for key, nm in CATALOGUE[task].items():
            conds[f"single:{key}"] = [{"template": f"W{w + 1}", "halves": {
                str(h): triplet(task, [nm], w, tnouns, h) for h in (1, 2)}} for w in range(5)]
        if task == "t1":
            conds["nonce"] = [{"template": f"W{w + 1}", "halves": {
                str(h): triplet(task, [NONCE_NAME], w, tnouns, h) for h in (1, 2)}} for w in range(5)]
        if task == "t2":
            for s in MODES["t2"]:
                banned = [k for k in MODES["t2"] if k != s]
                conds[f"los:{s}"] = [{"template": f"W{w + 1}", "banned": banned,
                                      "names": multi_names(task, banned, w), "halves": {
                    str(h): triplet(task, multi_names(task, banned, w), w, tnouns, h) for h in (1, 2)}}
                    for w in range(5)]
        frozen["tasks"][task] = {"spec": spec_text(task), "conditions": conds}
    return frozen


def stage_freeze() -> None:
    frozen = build_frozen()
    write_json(FROZEN, frozen, indent=1)
    sha = sha256_file(FROZEN)
    commit_payload(FROZEN, note=f"S1 frozen prompts (file sha256 {sha}); line 0")
    # token-length log
    rows = []
    for task, td in frozen["tasks"].items():
        for cname, lst in td["conditions"].items():
            for it in lst:
                if "halves" in it:
                    for h, tr in it["halves"].items():
                        rows.append({"task": task, "condition": cname, "template": it["template"], "half": h,
                                     **{f"tok_{k}": v for k, v in tr["tokens"].items()}, "padding": tr["padding"]})
    write_json(PROMPT_DIR / "segment_token_lengths.json", rows)
    logger.info(f"frozen prompts written: {FROZEN} sha256={sha}; {len(rows)} twin rows")
    logger.info(f"neutral nouns: {json.dumps(frozen['neutral_nouns'])}")


def load_frozen() -> dict[str, Any]:
    return json.loads(FROZEN.read_text())


def multi_ban_conditions(task: str, set_name: str, banned: list[str], nouns: dict[str, list[str]]) -> list[dict]:
    """Built at S7 for TOP/ARC/SCATTER with the frozen rule."""
    return [{"template": f"W{w + 1}", "set": set_name, "banned": banned, "names": multi_names(task, banned, w),
             "halves": {str(h): triplet(task, multi_names(task, banned, w), w, nouns, h) for h in (1, 2)}}
            for w in range(5)]
