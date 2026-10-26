"""(0d) Llama correct-only compositions and Hill_cc (raw, rarefied at equal depth, Miller-Madow) for the 14 exp10
events and the 13-task exp11 bench pilot, with the Qwen counterparts beside each (exp1 same-condition events; exp11
Qwen pilot)."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from common.paths import RESULTS, SEED, TABLES, dep, read_json, read_jsonl, src, write_json
from common.rows import MODAL, iter_rows
from common.stats import hill1, hill1_miller_madow, rarefied_hill1, wilson

DEPTHS = (10, 20)


def _lab(r: dict[str, Any], t: str) -> str:
    L = str(r.get("label"))
    if L in ("None", "no_code", "invalid", "unparseable") or not (r.get("code") or "").strip():
        return "unparseable"
    return L


def comp_block(labels: list[str], passed: list[bool], banned: list[str], rng: np.random.Generator) -> dict[str, Any]:
    att = [x for x in labels if x != "unparseable"]
    cc = [x for x, p in zip(labels, passed) if p and x != "unparseable" and x not in banned]
    ca, cco = Counter(att), Counter(cc)
    n_pass = sum(passed)
    out = {"N": len(labels), "n_attempted": len(att), "attempted_counts": dict(ca.most_common()),
           "n_correct_compliant": len(cc), "correct_compliant_counts": dict(cco.most_common()),
           "pass_rate": n_pass / len(labels) if labels else math.nan,
           "pass_wilson": wilson(n_pass, len(labels)) if labels else (math.nan, math.nan),
           "hill_all": hill1(list(ca.values())), "hill_cc": hill1(list(cco.values())),
           "hill_cc_miller_madow": hill1_miller_madow(list(cco.values()))}
    for d in DEPTHS:
        dd = min(d, len(cc)) if d == 10 else d
        out[f"hill_cc_rarefied_d{d}"] = rarefied_hill1(list(cco.values()), dd, 1000, rng) if len(cc) >= dd and dd > 0 \
            else math.nan
        out[f"rarefy_depth_used_d{d}"] = dd
    out["hill_cc_rarefied_d10_flag"] = "" if len(cc) >= 10 else f"n_correct={len(cc)} < 10: rarefied at {len(cc)}"
    return out


def run() -> dict[str, Any]:
    rng = np.random.default_rng(SEED)
    ev = read_json(dep("exp10", "results/events.json"))
    lab = read_jsonl(dep("exp10", "data/labelled.jsonl"))
    by = defaultdict(list)
    for r in lab:
        by[(r["task"], r["condition"])].append(r)
    qrows = [r for r in iter_rows() if r["exp"] == "exp1" and r["model"] == "Qwen/Qwen3-8B" and r["decoding_key"].startswith("T1.0")]
    qby = defaultdict(list)
    for r in qrows:
        qby[(r["task"], r["condition"])].append(r)
    events = []
    for t in ("t1", "t2"):
        for e in ev[t]:
            rs = [r for c in e["conds"] for r in by.get((t, c), [])]
            labels = [_lab(r, t) for r in rs]
            passed = [str(r.get("passed")) == "True" for r in rs]
            blk = comp_block(labels, passed, e["banned"], rng)
            # Qwen counterpart from exp1 (same task and condition family, T = 1.0)
            name = e["name"].split(" ")[0]
            qc = {"baseline": "baseline", "listall": "listall"}.get(name, name)
            if name.startswith("twostep"):
                qc = "succession:2"
            q = qby.get((t, qc), [])
            qblk = comp_block([r["label"] if r["label"] != "unparseable" else "unparseable" for r in q],
                              [bool(r["passed"]) for r in q], e["banned"], rng) if q else None
            events.append({"model": "meta-llama/Llama-3.1-8B-Instruct", "task": t, "event": e["name"],
                           "banned": e["banned"], **blk, "events_json_attempted_counts": e["attempted_counts"],
                           "attempted_matches_events_json": dict(Counter([x for x in labels if x != "unparseable"])) ==
                           {k: v for k, v in e["attempted_counts"].items() if k != "no_code"},
                           "qwen_counterpart": {"source": src("exp1", "data/samples.jsonl"), "condition": qc,
                                                **(qblk or {})} if qblk else None,
                           "source": src("exp10", "data/labelled.jsonl") + " ; " + src("exp10", "results/events.json")})
    bench = []
    lp = read_jsonl(dep("exp11", "data/samples_llama_pilot.jsonl"))
    qp = read_jsonl(dep("exp11", "data/samples_pilot.jsonl"))
    for task in sorted({r["task"] for r in lp}):
        lr = [r for r in lp if r["task"] == task]
        qr = [r for r in qp if r["task"] == task]
        lb = comp_block([_lab(r, task) for r in lr], [str(r.get("passed")) == "True" for r in lr], [], rng)
        qb = comp_block([_lab(r, task) for r in qr], [str(r.get("passed")) == "True" for r in qr], [], rng)
        bench.append({"task": task, "llama": lb, "qwen": qb,
                      "source": src("exp11", "data/samples_llama_pilot.jsonl") + " ; " + src("exp11", "data/samples_pilot.jsonl")})
    # reproduction checks
    t1b = next(e for e in events if e["task"] == "t1" and e["event"] == "baseline")
    def bc(task):
        return next(b for b in bench if b["task"] == task)["llama"]["correct_compliant_counts"]
    repro = {"t1_baseline_attempted": {k: t1b["attempted_counts"].get(k) for k in ("bfs", "dfs")},
             "t1_baseline_correct": t1b["correct_compliant_counts"],
             "T03_correct": bc("T03"), "T04_correct": bc("T04"), "T10_correct": bc("T10"), "T14_correct": bc("T14"),
             "targets": {"t1_baseline": "BFS 77, DFS 20 attempted; BFS 20/20 correct",
                         "T03": "full sort 6, heapify 2, quickselect 1, size-k heap 1", "T04": "naive 18, KMP 5, Rabin-Karp 1",
                         "T10": "union-find 30, DFS 5", "T14": "heap 8, sort by count 4"}}
    lh = [b["llama"]["hill_cc"] for b in bench]
    qh = [b["qwen"]["hill_cc"] for b in bench]
    l10 = [b["llama"]["hill_cc_rarefied_d10"] for b in bench]
    q10 = [b["qwen"]["hill_cc_rarefied_d10"] for b in bench]
    more_div = sum(1 for a, b in zip(l10, q10) if np.isfinite(a) and np.isfinite(b) and a > b + 1e-9)
    sentence = (f"Counted over correct programs only and rarefied to 10 programs, Llama-3.1-8B-Instruct is more diverse "
                f"than Qwen3-8B on {more_div} of {len(bench)} bench tasks (median rarefied Hill_cc "
                f"{np.nanmedian(l10):.2f} vs {np.nanmedian(q10):.2f}; raw medians {np.nanmedian(lh):.2f} vs "
                f"{np.nanmedian(qh):.2f}), but on the T1 grid task its correct programs are all BFS "
                f"({t1b['correct_compliant_counts']}) even though only {t1b['attempted_counts'].get('bfs', 0)} of "
                f"{t1b['n_attempted']} attempted programs are BFS: much of Llama's apparent T1 diversity is failing code.")
    out = {"events": events, "bench": bench, "reproduction": repro, "cross_model_sentence": sentence,
           "llama_t1_baseline_hill_cc": t1b["hill_cc"], "llama_t1_baseline_hill_all": t1b["hill_all"]}
    write_json(RESULTS / "llama_correct_only.json", out)
    rows = []
    for e in events:
        rows.append({"model": "Llama", "task": e["task"], "unit": e["event"], "N": e["N"], "n_correct_compliant": e["n_correct_compliant"],
                     "pass_rate": e["pass_rate"], "hill_all": e["hill_all"], "hill_cc": e["hill_cc"],
                     "hill_cc_rar10": e["hill_cc_rarefied_d10"], "hill_cc_rar20": e["hill_cc_rarefied_d20"],
                     "hill_cc_mm": e["hill_cc_miller_madow"], "flag": e["hill_cc_rarefied_d10_flag"],
                     "correct_counts": str(e["correct_compliant_counts"]), "attempted_counts": str(e["attempted_counts"]),
                     "qwen_hill_cc": (e["qwen_counterpart"] or {}).get("hill_cc"),
                     "qwen_hill_cc_rar10": (e["qwen_counterpart"] or {}).get("hill_cc_rarefied_d10")})
    for b in bench:
        rows.append({"model": "Llama", "task": b["task"], "unit": "bench_pilot", "N": b["llama"]["N"],
                     "n_correct_compliant": b["llama"]["n_correct_compliant"], "pass_rate": b["llama"]["pass_rate"],
                     "hill_all": b["llama"]["hill_all"], "hill_cc": b["llama"]["hill_cc"],
                     "hill_cc_rar10": b["llama"]["hill_cc_rarefied_d10"], "hill_cc_rar20": b["llama"]["hill_cc_rarefied_d20"],
                     "hill_cc_mm": b["llama"]["hill_cc_miller_madow"], "flag": b["llama"]["hill_cc_rarefied_d10_flag"],
                     "correct_counts": str(b["llama"]["correct_compliant_counts"]),
                     "attempted_counts": str(b["llama"]["attempted_counts"]), "qwen_hill_cc": b["qwen"]["hill_cc"],
                     "qwen_hill_cc_rar10": b["qwen"]["hill_cc_rarefied_d10"]})
    pd.DataFrame(rows).to_csv(TABLES / "llama_correct_only.csv", index=False)
    logger.info(sentence)
    return out
