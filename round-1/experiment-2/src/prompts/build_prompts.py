#!/usr/bin/env python3
"""Build every prompt of the screen (all conditions x paraphrases) with chat-template token ids.

Writes prompts/prompts.jsonl. Each row carries the exact token ids fed to BOTH vLLM and HF, so the
read position R (last prompt token) is the same token in both engines. Asserts that the suffix token
ids (task spec + template tail) are identical across every geometry prompt of a task.

Usage: python prompts/build_prompts.py [--modal t1=bfs,t2=dijkstra]
  --modal adds the succession prompts (every cumulative ban set that starts with the modal mode:
  all ordered pairs and ordered triples), which need the Phase-A modal label.
"""
from __future__ import annotations

import argparse
import itertools
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import (BAN_CORES, BASELINE_CORES, CATALOGUE, DESCRIPTIONS, DISPLAY, ELICIT_TEMPLATE, FORCED_CORES,  # noqa: E402
                    LISTALL_CORE, MASKED_CORE, MENTION_CORES, MODEL_ID, N_PARA, SPEC, TASKS, frame, join_names,
                    join_names_and, setup_logger, sha256_text, stable_seed, write_jsonl)

logger = setup_logger("build_prompts")
ELICIT_TAIL = "Remember: answer with only the JSON list of approach names, not code."
N_ELICIT = 20


def build_rows(modal: dict[str, str]) -> list[dict]:
    rows: list[dict] = []

    def add(task: str, cond: str, para: int, seg: str, kind: str, **extra) -> None:
        rows.append({"task": task, "condition": cond, "paraphrase_id": para, "kind": kind,
                     "text": seg + "\n\n" + SPEC[task], **extra})

    for task in TASKS:
        modes = CATALOGUE[task]
        disp = DISPLAY[task]
        for p in range(N_PARA):
            add(task, "baseline", p, frame(p, BASELINE_CORES[p]), "geom", frame_id=p)
        for x in modes:
            for f in range(N_PARA):
                for v, core in enumerate(FORCED_CORES):
                    add(task, f"forced:{x}", f * 3 + v, frame(f, core.format(X=disp[x])), "geom", frame_id=f, variant_id=v)
                for v, desc in enumerate(DESCRIPTIONS[task][x]):
                    add(task, f"masked:{x}", f * 3 + v, frame(f, MASKED_CORE.format(D=desc)), "geom", frame_id=f, variant_id=v)
            for p in range(N_PARA):
                add(task, f"ban:{x}", p, frame(p, BAN_CORES[p].format(X=disp[x])), "geom", frame_id=p)
                add(task, f"mention:{x}", p, frame(p, MENTION_CORES[p].format(X=disp[x])), "geom", frame_id=p)
        for p in range(N_PARA):
            names = [disp[m] for m in modes]
            rot = names[p % len(names):] + names[: p % len(names)]
            add(task, "listall", p, frame(p, LISTALL_CORE.format(LIST=join_names_and(rot))), "geom", frame_id=p)
        # association elicitation: 20 samples per X, fresh random order of the K-1 other names per sample
        for x in modes:
            others = [m for m in modes if m != x]
            for s in range(N_ELICIT):
                rng = random.Random(stable_seed("elicit_order", task, x, s))
                order = others[:]
                rng.shuffle(order)
                names = ", ".join(disp[m] for m in order)
                seg = ELICIT_TEMPLATE.format(X=disp[x], NAMES=names)
                rows.append({"task": task, "condition": f"elicit:{x}", "paraphrase_id": s, "kind": "elicit",
                             "text": seg + "\n\n" + SPEC[task] + "\n\n" + ELICIT_TAIL, "order": order})
        # succession prompts (ordered cumulative ban sets starting with the modal mode)
        if task in modal:
            m0 = modal[task]
            rest = [m for m in modes if m != m0]
            seqs = [(m0, a) for a in rest] + [(m0, a, b) for a, b in itertools.permutations(rest, 2)]
            for seq in seqs:
                cond = "ban:" + "+".join(seq)
                for p in range(N_PARA):
                    add(task, cond, p, frame(p, BAN_CORES[p].format(X=join_names([disp[m] for m in seq]))), "geom",
                        frame_id=p)
    return rows


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modal", default="", help="t1=bfs,t2=dijkstra")
    ap.add_argument("--out", default=str(ROOT / "prompts" / "prompts.jsonl"))
    args = ap.parse_args()
    modal = dict(kv.split("=") for kv in args.modal.split(",") if kv)
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    rows = build_rows(modal)
    suffix_ref: dict[str, list[int]] = {}
    for r in rows:
        msgs = [{"role": "user", "content": r["text"]}]
        templ = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        enc = tok(templ, add_special_tokens=False, return_offsets_mapping=True)
        ids = enc["input_ids"]
        r["prompt_ids"] = ids
        r["n_tokens"] = len(ids)
        r["ids_sha256"] = sha256_text(json.dumps(ids))
        r["prompt_id"] = f"{r['task']}|{r['condition']}|p{r['paraphrase_id']:02d}"
        if r["kind"] == "geom":
            cstart = templ.rindex(SPEC[r["task"]])
            starts = [i for i, (a, b) in enumerate(enc["offset_mapping"]) if a == cstart]
            assert starts, f"no token boundary at the spec start for {r['prompt_id']}"
            k = starts[0]
            suf = ids[k:]
            if r["task"] not in suffix_ref:
                suffix_ref[r["task"]] = suf
            assert suf == suffix_ref[r["task"]], f"suffix ids differ for {r['prompt_id']}"
            r["suffix_len"] = len(suf)
    for task in TASKS:
        suf = suffix_ref[task]
        logger.info(f"{task}: suffix L_s={len(suf)} tokens; last 6 decoded = {[tok.decode([t]) for t in suf[-6:]]}")
    ex = [r for r in rows if r["kind"] == "geom"][:3]
    for r in ex:
        logger.info(f"{r['prompt_id']}: last 6 tokens {[tok.decode([t]) for t in r['prompt_ids'][-6:]]} ids {r['prompt_ids'][-6:]}")
    write_jsonl(Path(args.out), rows)
    meta = {t: {"L_s": len(suffix_ref[t]), "suffix_sha256": sha256_text(json.dumps(suffix_ref[t])),
                "R_token_id": suffix_ref[t][-1], "R_token": tok.decode([suffix_ref[t][-1]])} for t in TASKS}
    (ROOT / "prompts" / "suffix_meta.json").write_text(json.dumps(meta, indent=1))
    from collections import Counter

    logger.info(f"wrote {len(rows)} prompts: {Counter((r['task'], r['condition'].split(':')[0]) for r in rows)}")


if __name__ == "__main__":
    main()
