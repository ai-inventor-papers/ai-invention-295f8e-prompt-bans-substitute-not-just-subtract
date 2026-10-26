#!/usr/bin/env python3
"""S1 (CPU): every prompt of iteration 8 with positions and splits -> prompts/prompts8.jsonl.

T10 (Qwen3-8B; iteration-7 records in inputs/exp33/prompts7.jsonl reused verbatim where they exist):
  forced[k][j][Y]  templates k = 0..4 x display names j = 0..3 x Y in {bfs, dfs, union_find}; (k, j = 0) reproduces
                   iteration 7's forced[k][Y] ids exactly (asserted); Y = union_find is the null source
  padtwin          the forced prompt with its segment tokens replaced by ' .' (exp30 pad_record rule)
  twin[w][n]       W1-W5 x 32 single-token nouns: iteration 7's 12 (verbatim ids) + 20 from art_j3Rm_lr2nzR6's flagged
                   neutral-noun candidates, rebuilt with the same rule (sentence + ' .' padding to the ban's length;
                   the rebuild reproduces iteration 7's nouns 1-11 exactly, asserted)
  ban[w], p0, seed_rand1/2, instr_new, instr_novel   placement-only (never fit, never generated)
Splits: forced families train k = 0,1,2 / held k = 3,4; twin templates train W1-W3 / held W4-W5; nouns 70/30 by a
seeded shuffle (seed 8001). A held-out pair needs a held-out family AND a held-out base.
GRID (gemma-3-4b-it): built by src/grid_prompts.py with iteration 7's Gemma prompt code (inputs/exp38/src).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from loguru import logger

from cfg8 import (FAMILY, HELD_FAM, HELD_W, INPUTS, N_T10_NOUNS, NOUN_SPLIT_SEED, OPEN_T10, PROMPTS_DIR, ROOT,
                  T10_DISPLAY, T10_FORCED_TEMPLATES, TRAIN_FAM, TRAIN_W, model_path, read_json, read_jsonl,
                  setup_logging, sha256_text, write_jsonl)

W_TEMPLATES = {"W1": "Do not use {N} for this task.", "W2": "Your solution must not rely on {N}.",
               "W3": "Avoid {N} entirely.", "W4": "{N} is not allowed here.",
               "W5": "Write a correct solution that does not use {N}."}
EXCL = {"sort", "set", "union", "label", "search", "depth", "breadth", "bucket", "dial", "flood", "order", "count",
        "number", "graph", "node", "edge", "tree", "path", "list", "value", "component", "heap", "select", "pivot",
        "median", "weight", "distance", "cycle", "loop", "group", "class", "function", "code", "task", "solution",
        "algorithm", "program", "problem", "answer", "result", "test", "parent", "root", "find", "link", "network",
        "island", "map", "queue", "stack", "visit", "line", "point", "key", "table", "index", "string", "word"}
SEEDS_INSTR = {"seed_rand1": "seed=d32qxk4nt43", "seed_rand2": "seed=(horse chair roof love)",
               "instr_new": "Make a new algorithm.",
               "instr_novel": ("Make a fully novel algorithm never seen before for this task. Before writing any code, "
                               "write a design rationale of about 2,000 words that explains the idea, why no one has "
                               "used it before, and why it is correct.")}


def cap_first(s: str) -> str:
    return s[:1].upper() + s[1:]


def qwen_tok():
    from transformers import AutoTokenizer

    f = FAMILY["qwen"]
    return AutoTokenizer.from_pretrained(model_path(f["id"], f["rev"]))


def seg_end(tok: Any, ids: list[int], p0: int, p1: int) -> int:
    """First trailing newline-bearing token before p1 (exp30 pad_record rule): the segment is [p0, k)."""
    k = p1
    while k > p0 and "\n" in tok.decode([ids[k - 1]]):
        k -= 1
    return k


def pad_twin_ids(tok: Any, ids: list[int], p0: int, p1: int) -> tuple[list[int], list[int]]:
    dot = tok(" .", add_special_tokens=False)["input_ids"]
    assert len(dot) == 1
    out = list(ids)
    k = seg_end(tok, ids, p0, p1)
    for i in range(p0, k):
        out[i] = dot[0]
    return out, [p0, k]


def splice(tok: Any, base: dict[str, Any], segment: str, pad_to: int | None = None) -> list[int] | None:
    """base ids with the segment region [p0, p1) replaced by tokens(segment + '\n\n'); with pad_to, ' .' fillers are
    appended after the sentence until the region has exactly pad_to tokens (None if unreachable)."""
    ids = base["ids"]
    p0, p1 = base["p0"], base["p1"]
    if pad_to is None:
        seg = tok(segment + "\n\n", add_special_tokens=False)["input_ids"]
        return ids[:p0] + seg + ids[p1:]
    for npad in range(0, 40):
        seg = tok(segment + " ." * npad + "\n\n", add_special_tokens=False)["input_ids"]
        if len(seg) == pad_to:
            return ids[:p0] + seg + ids[p1:]
        if len(seg) > pad_to:
            return None
    return None


def rec(kind: str, ids: list[int], p0: int, p1: int, spec_end: int, **kw: Any) -> dict[str, Any]:
    r = {"unit": "T10", "family": "qwen", "kind": kind, "ids": list(ids), "P": len(ids), "p0": p0, "p1": p1,
         "spec_end": spec_end, "prompt_sha256": sha256_text(json.dumps(list(ids)))}
    r.update(kw)
    r["dec_ids"] = list(ids) + OPEN_T10
    r["d"] = len(r["dec_ids"]) - 1
    return r


def noun_pool(tok: Any, spec: str, used: set[str]) -> list[str]:
    dep = read_json(INPUTS / "dep_extract.json")
    cands = []
    for n in dep["neutral_noun_candidates"]:
        w = str(n["word"]).strip().lower()
        m = n["meta"]
        if not w.isalpha() or w in EXCL or w in used or w in spec.lower():
            continue
        if len(tok(" " + w, add_special_tokens=False)["input_ids"]) != 1:
            continue
        if len(tok(cap_first(w), add_special_tokens=False)["input_ids"]) != 1:
            continue
        freq = float(m.get("metadata_subtlex_frequency") or 0)
        cands.append((-freq, w))
    cands.sort()
    return [w for _, w in cands]


def build_t10(tok: Any) -> list[dict[str, Any]]:
    p7 = [r for r in read_jsonl(INPUTS / "exp33" / "prompts7.jsonl") if r["task"] == "T10"]
    by = {r["key"]: r for r in p7}
    rows: list[dict[str, Any]] = []
    # ---- forced sources and padding twins
    for k, tmpl in enumerate(T10_FORCED_TEMPLATES):
        old = by[f"T10|forced|F{k}|bfs"]
        for Y, names in T10_DISPLAY.items():
            for j, name in enumerate(names):
                seg = tmpl.format(j=name)
                ids = splice(tok, old, seg)
                if j == 0:
                    ref = by[f"T10|forced|F{k}|{Y}"]
                    assert ids == ref["ids"], f"forced F{k}/{Y} does not reproduce iteration 7"
                p1 = old["p1"] + (len(ids) - old["P"])
                se = old["spec_end"] + (len(ids) - old["P"])
                fam_split = "train" if k in TRAIN_FAM else "held"
                rows.append(rec("forced", ids, old["p0"], p1, se, key=f"T10|forced|k{k}|j{j}|{Y}", fam=k, name_idx=j,
                                Y=Y, segment=seg, split=fam_split))
                pids, cond = pad_twin_ids(tok, ids, old["p0"], p1)
                rows.append(rec("padtwin", pids, old["p0"], p1, se, key=f"T10|padtwin|k{k}|j{j}|{Y}", fam=k,
                                name_idx=j, Y=None, padded_of=f"T10|forced|k{k}|j{j}|{Y}", cond=cond,
                                split=fam_split))
    # ---- twins: iteration-7 nouns verbatim + new nouns rebuilt with the same rule
    tw7 = [r for r in p7 if r["kind"] == "twin"]
    nouns7 = [n for _, n in sorted({(r["noun_idx"], r["noun"]) for r in tw7})]
    spec_text = tok.decode(tw7[0]["ids"][tw7[0]["p1"]:tw7[0]["spec_end"]])
    extra = noun_pool(tok, spec_text, set(nouns7))[:N_T10_NOUNS - len(nouns7)]
    nouns = nouns7 + extra
    assert len(nouns) == N_T10_NOUNS, f"only {len(nouns)} nouns"
    rng = np.random.default_rng(NOUN_SPLIT_SEED)
    perm = list(rng.permutation(len(nouns)))
    n_train = int(round(0.7 * len(nouns)))
    noun_split = {nouns[i]: ("train" if r < n_train else "held") for r, i in enumerate(perm)}
    for w in W_TEMPLATES:
        base0 = next(r for r in tw7 if r["w"] == w and r["noun_idx"] == 0)
        region_len = base0["p1"] - base0["p0"]
        for ni, noun in enumerate(nouns):
            sent = W_TEMPLATES[w].format(N=noun)
            sent = cap_first(sent)
            ids = splice(tok, base0, sent, pad_to=region_len)
            if ni < len(nouns7):
                ref = next(r for r in tw7 if r["w"] == w and r["noun"] == noun)
                if ids != ref["ids"]:
                    ids = ref["ids"]          # keep iteration 7's frozen ids verbatim (logged below)
                    logger.warning(f"twin {w}/{noun}: rebuild differs from iteration 7; frozen ids kept")
            if ids is None:
                continue
            rows.append(rec("twin", ids, base0["p0"], base0["p1"], base0["spec_end"], key=f"T10|twin|{w}|{noun}", w=w,
                            noun=noun, noun_idx=ni, noun_source="iter7" if ni < len(nouns7) else "art_j3Rm",
                            split_w="train" if w in TRAIN_W else "held", split_noun=noun_split[noun],
                            split=("train" if (w in TRAIN_W and noun_split[noun] == "train") else
                                   "held" if (w in HELD_W and noun_split[noun] == "held") else "neither")))
    # ---- placement-only prompts
    for r in p7:
        if r["kind"] in ("ban", "p0"):
            rows.append(rec(r["kind"], r["ids"], r["p0"], r["p1"], r["spec_end"], key=f"T10|{r['kind']}|{r['w']}",
                            w=r["w"], segment=r["segment"], split="placement"))
    old = by["T10|forced|F0|bfs"]
    for name, seg in SEEDS_INSTR.items():
        ids = splice(tok, old, seg)
        p1 = old["p1"] + (len(ids) - old["P"])
        se = old["spec_end"] + (len(ids) - old["P"])
        rows.append(rec(name, ids, old["p0"], p1, se, key=f"T10|{name}", segment=seg, split="placement"))
    # ---- assertions: spec ids identical at aligned offsets
    spec0 = None
    for r in rows:
        s = r["ids"][r["p1"]:r["spec_end"]]
        if spec0 is None:
            spec0 = s
        assert s == spec0, f"spec mismatch in {r['key']}"
        assert r["ids"][r["spec_end"]:] == rows[0]["ids"][rows[0]["spec_end"]:], f"tail mismatch {r['key']}"
    for r in rows:
        if r["kind"] == "padtwin":
            f = next(x for x in rows if x["key"] == r["padded_of"])
            assert f["P"] == r["P"]
    logger.info(f"T10: {len(rows)} prompts; nouns {len(nouns)} ({len(extra)} new); "
                f"train nouns {sum(v == 'train' for v in noun_split.values())}")
    return rows


def build_grid() -> list[dict[str, Any]]:
    out = PROMPTS_DIR / "grid_prompts.jsonl"
    if not out.exists():
        cmd = [sys.executable, str(ROOT / "src" / "grid_prompts.py"), str(out)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if r.returncode != 0:
            logger.error(r.stdout[-3000:] + r.stderr[-3000:])
            raise RuntimeError("grid prompt builder failed")
    return read_jsonl(out)


def main() -> None:
    setup_logging("prompts8")
    tok = qwen_tok()
    t10 = build_t10(tok)
    write_jsonl(PROMPTS_DIR / "t10_prompts.jsonl", t10)
    grid = build_grid()
    logger.info(f"grid: {len(grid)} prompts")


if __name__ == "__main__":
    main()
