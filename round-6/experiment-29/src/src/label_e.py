#!/usr/bin/env python3
"""Labelling for artifact E: wraps exp19's label_worker_v4 (copied unchanged) -- T2 through the exp8 canonical suite
(hidden tests + runtime probes -> runtime label, AST label, blind judge openai/gpt-4.1-mini only on disagreement),
T10/T03 through exp11 bench.common.labeling.label_one (tests, AST, runtime trace; judge j1 on disagreement).
Judge verdicts are cached by (task, code sha256); the exp19/exp22/exp27 caches are pre-loaded into data/.

Usage: python src/label_e.py --follow-until results/gen_done.flag      (labels data/samples_raw.jsonl as it grows)
       python src/label_e.py --recheck                                  (Stage A.2: exp19 / exp22 rows re-labelled)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import resource
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger

from cfg import append_jsonl, read_jsonl, setup_logging, utc_now, write_json
from cfg_e import DEFAULT_E, E19, E22, LABELS_E, RAW_E, RESULTS_DIR

LABEL_FIELDS = ("label", "labeller_source", "passed", "valid", "runtime_label", "ast_label", "judge_label")


def label_rows_e(rows: list[dict[str, Any]], use_judge: bool = True) -> list[dict[str, Any]]:
    """rows need task, arm, template, sample_id, u_seed, finish_reason, text. Returns one label dict per row."""
    import label_worker_v4 as LW

    path = [i for i, r in enumerate(rows) if r["task"] in LW.EXP8_TASK]
    bench = [i for i, r in enumerate(rows) if r["task"] not in LW.EXP8_TASK]
    out: list[dict[str, Any] | None] = [None] * len(rows)
    if path:
        for i, l in zip(path, LW.label_path_rows([rows[i] for i in path], use_judge)):
            out[i] = l
    if bench:
        for i, l in zip(bench, LW.label_bench_rows([rows[i] for i in bench], use_judge)):
            out[i] = l
    res = []
    for r, l in zip(rows, out):
        code = l.get("code")
        d = {"sample_id": r["sample_id"], **{k: l.get(k) for k in LABEL_FIELDS},
             "n_pass": l.get("n_pass"), "n_cases": l.get("n_cases"), "code": code,
             "code_sha256": hashlib.sha256(code.encode()).hexdigest() if code else None, "utc": utc_now()}
        d["is_default"] = d["label"] == DEFAULT_E.get(r["task"])
        res.append(d)
    return res


def follow(raw: Path, out_p: Path, flag: Path | None, chunk: int = 40, use_judge: bool = True) -> None:
    t0 = time.time()
    n_total = 0
    final_pass = False
    while True:
        done = {r["sample_id"] for r in read_jsonl(out_p)}
        todo, seen = [], set()
        for r in read_jsonl(raw):
            if r["sample_id"] in done or r["sample_id"] in seen:
                continue
            seen.add(r["sample_id"])
            todo.append(r)
        if todo:
            # group by task so each chunk uses one labeller
            todo.sort(key=lambda r: (r["task"], r["sample_id"]))
            for i in range(0, len(todo), chunk):
                part = todo[i:i + chunk]
                tb = time.time()
                try:
                    labs = label_rows_e(part, use_judge)
                except Exception as e:  # noqa: BLE001 - log; the chunk is retried on the next pass
                    logger.exception(f"labelling chunk failed: {e}")
                    time.sleep(5)
                    break
                append_jsonl(out_p, labs)
                n_total += len(labs)
                logger.info(f"labelled {len(labs)} ({part[0]['task']}) in {time.time() - tb:.1f}s; total {n_total}; "
                            f"backlog {len(todo) - i - len(part)}")
            continue
        if flag is None or (flag.exists() and final_pass):
            break
        if flag.exists():
            final_pass = True
            time.sleep(3)
            continue
        time.sleep(15)
    logger.info(f"label worker finished: {n_total} rows in {time.time() - t0:.0f}s")


def recheck() -> dict[str, Any]:
    """Stage A.2: re-label exp19's T10/T2/T03 TWIN, PN_a1, PN_a2 rows and exp22's T10/T2 alpha-2 population rows
    with the copied labeller; agreement with the stored labels must be 1.00 (fix the copy, never the rows)."""
    out: dict[str, Any] = {}
    stored = {r["sample_id"]: r for r in read_jsonl(E19 / "data" / "samples.jsonl")}
    rows = [r for r in read_jsonl(E19 / "data" / "samples_raw.jsonl")
            if r["task"] in ("T10", "T2", "T03") and r["arm"] in ("TWIN", "PN_a1", "PN_a2")]
    labs = label_rows_e(rows)
    agree = [l["label"] == stored[r["sample_id"]]["label"] and bool(l["passed"]) == bool(stored[r["sample_id"]]["passed"])
             for r, l in zip(rows, labs)]
    mism = [{"sample_id": r["sample_id"], "stored": [stored[r["sample_id"]]["label"], stored[r["sample_id"]]["passed"]],
             "now": [l["label"], l["passed"], l["labeller_source"]]} for r, l, a in zip(rows, labs, agree) if not a]
    out["exp19"] = {"n": len(rows), "agreement": sum(agree) / max(len(rows), 1), "mismatches": mism[:50]}
    append_jsonl(RESULTS_DIR / "recheck_labels_exp19.jsonl", labs)
    # exp22 population rows (T10/T2, alpha 2, the 40 directions)
    st22 = {}
    for r in read_jsonl(E22 / "data" / "labels.jsonl"):
        st22[r["key"]] = r
    rows22 = []
    for r in read_jsonl(E22 / "data" / "samples_raw.jsonl"):
        if r["task"] in ("T10", "T2") and r["arm"].startswith("POP_d91") and r["arm"].endswith("_a2.0"):
            key = f"{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}"
            if key in st22:
                rows22.append({"task": r["task"], "arm": r["arm"], "template": r["template"], "sample_id": key,
                               "u_seed": r["seed"], "finish_reason": r["finish_reason"], "text": r["text"]})
    labs22 = label_rows_e(rows22)
    agree22 = [l["label"] == st22[r["sample_id"]]["label"] and bool(l["passed"]) == bool(st22[r["sample_id"]]["passed"])
               for r, l in zip(rows22, labs22)]
    mism22 = [{"key": r["sample_id"], "stored": [st22[r["sample_id"]]["label"], st22[r["sample_id"]]["passed"]],
               "now": [l["label"], l["passed"], l["labeller_source"]]}
              for r, l, a in zip(rows22, labs22, agree22) if not a]
    out["exp22_pop_a2"] = {"n": len(rows22), "agreement": sum(agree22) / max(len(rows22), 1),
                           "mismatches": mism22[:50]}
    append_jsonl(RESULTS_DIR / "recheck_labels_exp22.jsonl", labs22)
    out["utc"] = utc_now()
    write_json(RESULTS_DIR / "labeller_recheck.json", out)
    logger.info(f"labeller re-check: exp19 {out['exp19']['agreement']:.4f} (n {len(rows)}), exp22 "
                f"{out['exp22_pop_a2']['agreement']:.4f} (n {len(rows22)})")
    return out


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--follow-until", default=None)
    ap.add_argument("--recheck", action="store_true")
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--raw", default=str(RAW_E))
    ap.add_argument("--out", default=str(LABELS_E))
    args = ap.parse_args()
    setup_logging("label_recheck" if args.recheck else "label_e")
    lim = 24 * 1024 ** 3
    try:
        resource.setrlimit(resource.RLIMIT_AS, (lim, lim))
    except (ValueError, OSError) as e:
        logger.warning(f"RLIMIT_AS not set: {e}")
    if args.recheck:
        recheck()
        return
    follow(Path(args.raw), Path(args.out), Path(args.follow_until) if args.follow_until else None,
           use_judge=not args.no_judge)


if __name__ == "__main__":
    main()
