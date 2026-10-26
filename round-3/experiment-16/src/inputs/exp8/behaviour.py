#!/usr/bin/env python3
"""S4: behaviour under common random numbers. For each task, template and arm in {a, b, c, d}: 20 samples
(s = 0-9 with neutral noun A, s = 10-19 with noun B for b, c, d), one shared PCG64 uniform stream per
(task, template, s) used by every arm, so arms differ only through the cache. Temporal-knockout behaviour K1/K2 on
cache a with the same 20 streams. Batches are never pruned, so every arm runs the same batch shape at every step. Raw samples -> data/samples_raw.jsonl; labelling -> data/samples.jsonl.
"""

from __future__ import annotations

import json
import time
from typing import Any

from loguru import logger

from arms import build_arm, ko_config
from cfg import (BEH_PER_TEMPLATE, DATA_DIR, DECODING, MODEL_ID, PROMPTS_DIR, RESULTS_DIR, TASKS, TEMPLATE_IDS,
                 X_KEY, append_jsonl, read_jsonl, sha256_text, stable_seed, write_json, write_jsonl)

RAW = DATA_DIR / "samples_raw.jsonl"
LABELLED = DATA_DIR / "samples.jsonl"
BEH_ARMS = ("a", "b", "c", "d")
KO_BEH = ("K1", "K2")
N_KO_BEH = 20  # all 20 streams (plan: 10) so K1/K2 batches have arm a's exact batch shape


def u_key(task: str, template: str, s: int) -> tuple:
    return ("beh", task, template, s)


def _jobs(tasks: tuple[str, ...] = TASKS, templates: list[str] | None = None, n: int = BEH_PER_TEMPLATE,
          arms: tuple[str, ...] = BEH_ARMS + KO_BEH) -> list[dict[str, Any]]:
    jobs = []
    for t in tasks:
        for w in templates or TEMPLATE_IDS:
            for arm in arms:
                ss = range(min(n, N_KO_BEH)) if arm in KO_BEH else range(n)
                jobs.append({"task": t, "template": w, "arm": arm, "samples": list(ss)})
    return jobs


def run_jobs(model: Any, tok: Any, fp: dict[str, Any], jobs: list[dict[str, Any]]) -> dict[str, Any]:
    from engine import free, prefill, sample, u_stream

    done = {(r["task"], r["template"], r["condition"], r["sample_id"]) for r in read_jsonl(RAW)}
    t0 = time.time()
    n_new = n_tok = 0
    for (t, w) in sorted({(j["task"], j["template"]) for j in jobs}):
        mine = [j for j in jobs if j["task"] == t and j["template"] == w]
        todo = [(j, s) for j in mine for s in j["samples"] if (t, w, j["arm"], s) not in done]
        if not todo:
            continue
        tw = fp["tasks"][t]["templates"][w]
        p0, p1 = tw["ban"]["p0"], tw["ban"]["p1"]
        pre = {"ban": prefill(model, tw["ban"]["ids"]), "A": prefill(model, tw["neutral_A"]["ids"]),
               "B": prefill(model, tw["neutral_B"]["ids"])}
        arms_cache: dict[tuple[str, str], dict[str, Any]] = {}
        for j in mine:
            arm = j["arm"]
            ss = [s for s in j["samples"] if (t, w, arm, s) not in done]
            if not ss:
                continue
            rows, meta = [], []
            for s in ss:
                noun = "A" if s < BEH_PER_TEMPLATE // 2 else "B"
                key = (arm if arm in ("b", "c", "d") else "a", noun if arm in ("b", "c", "d") else "-")
                if key not in arms_cache:
                    arms_cache[key] = build_arm(key[0], pre, noun, p1)
                a = arms_cache[key]
                rows.append({"kv": a["kv"], "r_logits": a["r_logits"], "u": u_stream(*u_key(t, w, s))})
                meta.append({"s": s, "noun": key[1]})
            ko = ko_config(arm, p0, p1)
            tb = time.time()
            res = sample(model, rows, ko=ko, prune=False)
            out = []
            for m, r in zip(meta, res):
                text = tok.decode(r["token_ids"], skip_special_tokens=True)
                noun_word = (fp["tasks"][t]["nouns"][m["noun"]]["noun"] if m["noun"] in ("A", "B") else None)
                out.append({"task": t, "condition": arm, "template": w, "paraphrase_id": w, "sample_id": m["s"],
                            "seed": stable_seed(*u_key(t, w, m["s"])), "model": MODEL_ID, "decoding": DECODING,
                            "noun": noun_word, "noun_slot": m["noun"], "text": text, "token_ids": r["token_ids"],
                            "n_tokens": r["n_tokens"], "finish_reason": r["finish_reason"],
                            "logprob_sum": r["logprob_sum"]})
                n_tok += r["n_tokens"]
            append_jsonl(RAW, out)
            n_new += len(out)
            logger.info(f"S4 {t}/{w}/{arm}: {len(out)} samples in {time.time() - tb:.0f}s "
                        f"(total {n_new} new, {n_tok} tok, {(time.time() - t0) / 60:.1f} min)")
        del arms_cache
        free(pre)
    return {"n_new": n_new, "n_tok": n_tok, "seconds": time.time() - t0}


def stage_behaviour() -> dict[str, Any]:
    from engine import load_model

    fp = json.loads((PROMPTS_DIR / "frozen_prompts.json").read_text())
    tok, model = load_model()
    tl = []
    # gradual scaling (U8): one template x arm a (one full 20-row batch, same shape as every other batch)
    # -> all templates arms a-d -> + K1/K2
    tl.append(run_jobs(model, tok, fp, _jobs(tasks=("t1",), templates=["W1"], arms=("a",))))
    tl.append(run_jobs(model, tok, fp, _jobs(arms=BEH_ARMS)))
    tl.append(run_jobs(model, tok, fp, _jobs(arms=KO_BEH)))
    write_json(RESULTS_DIR / "behaviour_run.json", {"steps": tl})
    return {"steps": tl}


def stage_label_behaviour() -> dict[str, Any]:
    """CPU: canonical labeller on every behaviour sample (mechanism level), shared JSONL schema."""
    from labelling import extract, label_codes

    raw = read_jsonl(RAW)
    items = []
    for r in raw:
        code, how = extract(r["text"])
        r["code"], r["extract_method"] = code, how
        items.append({"task": r["task"], "code": code})
    labs = label_codes(items, use_judge=True)
    rows = []
    for r, lab in zip(raw, labs):
        rows.append({"task": r["task"], "condition": r["condition"], "template": r["template"],
                     "paraphrase_id": r["paraphrase_id"], "sample_id": r["sample_id"], "seed": r["seed"],
                     "model": r["model"], "decoding": r["decoding"], "label": lab["label"],
                     "labeller_source": lab["labeller_source"], "passed": lab["passed"],
                     "code_sha256": sha256_text(r["code"]) if r["code"] else None, "code": r["code"],
                     "noun": r["noun"], "noun_slot": r["noun_slot"], "n_tokens": r["n_tokens"],
                     "finish_reason": r["finish_reason"], "runtime_label": lab["runtime_label"],
                     "ast_label": lab["ast_label"], "judge_label": lab.get("judge_label"),
                     "judge_skipped": lab.get("judge_skipped", False), "fail_case": lab.get("fail_case"),
                     "banned": lab["label"] == X_KEY[r["task"]], "text": r["text"], "token_ids": r["token_ids"]})
    write_jsonl(LABELLED, rows)
    logger.info(f"labelled {len(rows)} behaviour samples -> {LABELLED}")
    return {"n": len(rows)}
