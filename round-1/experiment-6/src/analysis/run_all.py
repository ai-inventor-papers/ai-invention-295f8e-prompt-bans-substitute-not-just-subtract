#!/usr/bin/env python3
"""Run every analysis section (8a-8i) on results/samples.jsonl + states/, write results/analysis.json,
results/summaries.json and figures/."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis import behaviour, figures, phrasing, subspace, thinking, verdicts  # noqa: E402
from analysis.metrics import hill1, wilson  # noqa: E402
from common import RESULTS, read_jsonl, setup_logging, write_json  # noqa: E402


def summaries(samples: list[dict]) -> dict:
    groups = defaultdict(list)
    for s in samples:
        d = s["decoding"]
        groups[f"{s['task']}|{s['arm']}|{s['condition']}|{d['sampler']}|T{d['T']}|think{int(d['thinking'])}"].append(s)
    out = {}
    for k, xs in sorted(groups.items()):
        cnt = Counter(x["label"] for x in xs)
        corr = Counter(x["label"] for x in xs if x["passed"])
        n_pass = sum(x["passed"] for x in xs)
        out[k] = dict(n=len(xs), label_counts=dict(cnt), label_counts_correct=dict(corr), pass_rate=n_pass / len(xs),
                      pass_rate_wilson95=list(wilson(n_pass, len(xs))), hill_cc=hill1(list(corr.values())))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true", help="fewer bootstrap/permutation draws (smoke test)")
    ap.add_argument("--no-audit", action="store_true")
    args = ap.parse_args()
    logger = setup_logging("analysis")
    nb = 200 if args.fast else 2000
    t0 = time.time()
    samples = list(read_jsonl(RESULTS / "samples.jsonl"))
    logger.info(f"{len(samples)} samples")
    A: dict = {}
    A["bfs_dijkstra_table"] = behaviour.bfs_dijkstra_table(samples)
    logger.info(f"8a done {time.time() - t0:.0f}s")
    A["seeds_instructions"] = behaviour.seeds_instructions(samples, n_boot=nb, n_perm=500 if args.fast else 5000)
    logger.info(f"8c done {time.time() - t0:.0f}s")
    A["gen_then_select"] = behaviour.gen_then_select(samples)
    A["buy_rows"] = behaviour.buy_rows(samples)
    A["ideas_by_phrasings"] = phrasing.run(samples, n_boot=100 if args.fast else 1000)
    logger.info(f"8b done {time.time() - t0:.0f}s")
    meta = subspace.load_meta()
    rng = np.random.default_rng(11)
    A["probe_curves"] = json.loads((RESULTS / "probe_curves.json").read_text())
    for t in A["probe_curves"]:
        for c in A["probe_curves"][t]["curves"]:
            c.pop("clf", None)
    A["hook_checks"] = dict(meta["hook_checks"], first_token_alignment={
        t: dict(median_prob=meta[f"eval_{t}"]["first_token_prob_median"],
                p10_prob=meta[f"eval_{t}"]["first_token_prob_p10"]) for t in ("T1", "T2")})
    A["subspace_test"] = {}
    for task in ("T1", "T2"):
        ls = meta["l_star"][task]
        A["subspace_test"][task] = {"l_star": subspace.subspace_test(meta, task, ls, rng, n_boot=nb,
                                                                     n_perm=1000 if args.fast else 10000)}
        for off in (-4, 4):
            li = min(35, max(0, ls + off))
            A["subspace_test"][task][f"l_star{off:+d}"] = subspace.subspace_test(meta, task, li, rng, n_boot=500,
                                                                                 n_perm=1000)
        A["subspace_test"][task]["probe_validity"] = subspace.probe_validity(meta, task, samples, rng)
    logger.info(f"8d done {time.time() - t0:.0f}s")
    A["variance_split"] = {task: subspace.variance_split(meta, task, samples, rng, n_boot=200 if args.fast else 1000,
                                                         n_null=30 if args.fast else 100) for task in ("T1", "T2")}
    A["variance_split"]["synthetic_check"] = subspace.synthetic_check(rng)
    logger.info(f"8e done {time.time() - t0:.0f}s")
    A["thinking_trajectories"] = thinking.run(samples)
    if not args.no_audit:
        A["thinking_trajectories"]["lexicon_audit"] = thinking.lexicon_audit(samples)
    logger.info(f"8f done {time.time() - t0:.0f}s")
    per_task = {t: verdicts.screen_tests(t, A) for t in ("T1", "T2")}
    A["verdicts"] = dict(per_task=per_task, overall=verdicts.overall(per_task))
    A["forecast_check"] = verdicts.forecast_check(A)
    write_json(RESULTS / "analysis.json", A)
    write_json(RESULTS / "summaries.json", summaries(samples))
    A["figures"] = figures.make_all(A, samples)
    write_json(RESULTS / "analysis.json", A)
    logger.info(f"analysis done in {time.time() - t0:.0f}s; verdict: {A['verdicts']['overall']['verdict']}")


if __name__ == "__main__":
    main()
