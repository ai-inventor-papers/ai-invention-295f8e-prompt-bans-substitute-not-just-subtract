#!/usr/bin/env python3
"""S5: FRLP scoring. Every program (name-scrubbed, formatted exactly as generated, + <|im_end|>) is teacher-forced
on each arm's cache; per-token log-probs go to data/token_lp/*.npz and the summed log-likelihoods to
data/frlp_scores.jsonl. Denominators: each algorithm's programs under each of its forced prompts.

Cells are written incrementally (resumable). Work is ordered by priority so the drop order (F7) only ever trims the
tail: denominators -> main arms a-d -> knockouts -> e/f/pl -> layer bands -> mention twins.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from typing import Any

import numpy as np
from loguru import logger

from arms import build_arm, ko_config
from cfg import (ALGOS, DATA_DIR, PROMPTS_DIR, RESULTS_DIR, TASKS, TEMPLATE_IDS, TOKEN_LP_DIR, X_KEY, append_jsonl,
                 read_jsonl, write_json)

SCORES = DATA_DIR / "frlp_scores.jsonl"


def load_programs() -> dict[str, list[dict[str, Any]]]:
    progs = read_jsonl(DATA_DIR / "frlp_programs.jsonl")
    by: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in progs:
        p["uid"] = f"{p['task']}:{p['algorithm']}:{p['prog_index']}"
        by[p["task"]].append(p)
    return by


def _done_pairs() -> set[tuple[str, str]]:
    return {(r["cell"], r["uid"]) for r in read_jsonl(SCORES)}


def _save_cell(cell: dict[str, Any], progs: list[dict[str, Any]], lps: list[np.ndarray]) -> None:
    name = f"{cell['task']}_{cell['condition']}_{cell['template']}_{cell['half']}"
    k = 0
    while (TOKEN_LP_DIR / f"{name}__{k}.npz").exists():
        k += 1
    lens = np.array([len(x) for x in lps], dtype=np.int64)
    np.savez_compressed(TOKEN_LP_DIR / f"{name}__{k}.npz", lp=np.concatenate(lps).astype(np.float32),
                        offsets=np.concatenate([[0], np.cumsum(lens)]), uids=np.array([p["uid"] for p in progs]))
    rows = [{"cell": cell["cell"], "task": cell["task"], "condition": cell["condition"], "template": cell["template"],
             "noun": cell["noun"], "half_tag": cell["half"], "uid": p["uid"], "algorithm": p["algorithm"],
             "prog_half": p["half"], "ll": float(np.sum(lp.astype(np.float64))), "n_tokens": int(len(lp))}
            for p, lp in zip(progs, lps)]
    append_jsonl(SCORES, rows)


def plan_cells(by: dict[str, list[dict[str, Any]]], fp: dict[str, Any], tasks: tuple[str, ...] = TASKS,
               templates: list[str] | None = None, limit: int | None = None,
               include: set[str] | None = None) -> list[dict[str, Any]]:
    """Every scoring cell: (task, condition, template, noun, programs). limit = programs per algorithm (scaling)."""
    templates = templates or TEMPLATE_IDS
    cells = []
    for t in tasks:
        progs = [p for p in by[t] if limit is None or p["prog_index"] < limit]
        X = [p for p in progs if p["algorithm"] == X_KEY[t]]
        h1 = [p for p in progs if p["half"] == 1]
        h2 = [p for p in progs if p["half"] == 2]
        X1 = [p for p in X if p["half"] == 1]
        X2 = [p for p in X if p["half"] == 2]
        # denominators (template-independent)
        summ = json.loads((RESULTS_DIR / "frlp_programs_summary.json").read_text())["per_algorithm"]
        for j in ALGOS[t]:
            pj = [p for p in progs if p["algorithm"] == j]
            # every prompt that generated samples enters the mixture proposal, kept programs or not
            used = sorted({(k.split(":")[0], int(k.split(":")[1])) for k in summ[f"{t}:{j}"]["prompt_counts"]} |
                          {(p["prompt_kind"], p["prompt_index"]) for p in by[t] if p["algorithm"] == j})
            for kind, k in used:
                cells.append({"task": t, "condition": f"forced_{j}_{'p' if kind == 'paraphrase' else 'd'}{k}",
                              "template": "F", "noun": "-", "half": "all", "kind": "forced", "algorithm": j,
                              "prompt_kind": kind, "prompt_index": k, "progs": pj, "prio": 0})
        for w in templates:
            def add(cond: str, noun: str, half: str, plist: list[dict[str, Any]], prio: int) -> None:
                cells.append({"task": t, "condition": cond, "template": w, "noun": noun, "half": half,
                              "kind": "arm", "progs": plist, "prio": prio})
            add("a", "-", "all", progs, 1)
            for cond in ("b", "c", "d"):
                add(cond, "A", "1", h1, 1)
                add(cond, "B", "2", h2, 1)
            add("b", "B", "xh1", X1, 3)  # X half-1 programs under noun B: placebo reference
            add("b", "A", "xh2", X2, 3)  # X half-2 programs under noun A: symmetric (pooled-noun sensitivity)
            for cond in ("K0", "K1", "K2"):
                add(cond, "-", "all", X, 2)
            add("K0b", "A", "1", X1, 2)
            add("K0b", "B", "2", X2, 2)
            for cond in ("e", "f"):
                add(cond, "A", "1", X1, 3)
                add(cond, "B", "2", X2, 3)
            add("pl", "AB", "all", X, 3)
            for cond in ("B1", "B2", "B3"):
                add(cond, "-", "all", X, 4)
            add("mention", "-", "all", progs, 5)
    for c in cells:
        c["cell"] = f"{c['task']}|{c['condition']}|{c['template']}|{c['noun']}|{c['half']}"
    if include is not None:
        cells = [c for c in cells if c["condition"] in include or c["kind"] == "forced" and "forced" in include]
    return sorted(cells, key=lambda c: (c["prio"], c["task"], c["template"]))


def run_cells(model: Any, fp: dict[str, Any], cells: list[dict[str, Any]], deadline: float | None = None,
              time_log: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    from engine import free, prefill, score

    done = _done_pairs()
    todo = []
    for c in cells:
        c = dict(c)
        c["progs"] = [p for p in c["progs"] if (c["cell"], p["uid"]) not in done]
        if c["progs"]:
            todo.append(c)
    total_tok = sum(sum(p["n_score_tokens"] for p in c["progs"]) for c in todo)
    logger.info(f"FRLP: {len(todo)} cells with unscored programs ({total_tok} tokens)")
    t0 = time.time()
    n_seq = n_tok = 0
    skipped: list[str] = []
    # group by (task, template) so each prompt is prefilled once
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for c in todo:
        groups[(c["task"], c["template"], c["prio"])].append(c)
    for (t, w, prio), cs in sorted(groups.items(), key=lambda kv: (kv[0][2], kv[0][0], kv[0][1])):
        if deadline is not None and time.time() > deadline:
            skipped += [c["cell"] for c in cs]
            continue
        tg = time.time()
        if w == "F":
            for c in cs:
                fr = fp["tasks"][t]["forced"][c["algorithm"]]
                rec = fr["paraphrases"][c["prompt_index"]] if c["prompt_kind"] == "paraphrase" else fr["descriptive"]
                pre = prefill(model, rec["ids"])
                lps = score(model, pre, [p["score_ids"] for p in c["progs"]])
                _save_cell(c, c["progs"], lps)
                n_seq += len(lps)
                n_tok += sum(len(x) for x in lps)
                del pre
        else:
            tw = fp["tasks"][t]["templates"][w]
            p0, p1 = tw["ban"]["p0"], tw["ban"]["p1"]
            pre = {"ban": prefill(model, tw["ban"]["ids"]), "A": prefill(model, tw["neutral_A"]["ids"]),
                   "B": prefill(model, tw["neutral_B"]["ids"])}
            for c in cs:
                if c["condition"] == "mention":
                    arm = prefill(model, tw["mention"]["ids"])
                    ko = None
                else:
                    noun = "B" if c["condition"] == "pl" else (c["noun"] if c["noun"] in ("A", "B") else "A")
                    arm = build_arm(c["condition"], pre, noun, p1)
                    ko = ko_config(c["condition"], p0, p1)
                lps = score(model, arm, [p["score_ids"] for p in c["progs"]], ko=ko)
                _save_cell(c, c["progs"], lps)
                n_seq += len(lps)
                n_tok += sum(len(x) for x in lps)
                del arm
            free(pre)
        dt = time.time() - t0
        rate = n_tok / max(dt, 1e-9)
        left_tok = max(0, total_tok - n_tok)
        msg = (f"FRLP group {t}/{w}/prio{prio}: {time.time() - tg:.0f}s; total {n_seq} seqs {n_tok} tok in {dt:.0f}s "
               f"({rate:.0f} tok/s); projected remaining {left_tok / max(rate, 1e-9) / 60:.1f} min")
        logger.info(msg)
        if time_log is not None:
            time_log.append({"group": f"{t}/{w}/{prio}", "seconds": time.time() - tg, "tok_per_s": rate,
                             "projected_remaining_min": left_tok / max(rate, 1e-9) / 60})
    return {"n_seq": n_seq, "n_tok": n_tok, "seconds": time.time() - t0, "skipped_cells": skipped}


def stage_frlp(deadline_min: float | None = None) -> dict[str, Any]:
    import os

    from engine import load_model

    fp = json.loads((PROMPTS_DIR / "frozen_prompts.json").read_text())
    by = load_programs()
    tok, model = load_model()
    tl: list[dict[str, Any]] = []
    t_start = time.time()
    dl = float(os.environ.get("BRT_FRLP_DEADLINE_MIN", deadline_min or 1e9))
    deadline = t_start + dl * 60
    # gradual scaling (U8): W1 x 10 programs -> all templates x 10 -> full
    s1 = run_cells(model, fp, plan_cells(by, fp, templates=["W1"], limit=10, include={"a", "b", "forced"}),
                   time_log=tl)
    s2 = run_cells(model, fp, plan_cells(by, fp, limit=10, include={"a", "b", "c", "d"}), time_log=tl)
    s3 = run_cells(model, fp, plan_cells(by, fp), deadline=deadline, time_log=tl)
    res = {"scale_10_W1": s1, "scale_10_all": s2, "full": s3, "time_log": tl,
           "minutes": (time.time() - t_start) / 60}
    write_json(RESULTS_DIR / "frlp_run.json", res)
    logger.info(f"FRLP done: {res['minutes']:.1f} min; skipped {len(s3['skipped_cells'])} cells")
    return res
