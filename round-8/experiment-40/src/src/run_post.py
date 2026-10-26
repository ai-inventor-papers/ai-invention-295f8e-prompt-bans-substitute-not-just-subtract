#!/usr/bin/env python3
"""Post-hoc completion for a decision site whose label-control refits were fitted before the per-pair test was
added: re-evaluates the saved true map (seed 0, k*) and every saved label-control map on the held-out pairs and
computes the one-sided pair-level test true > permuted (Wilcoxon + two-way cluster bootstrap) that feeds p_K2.
No fitting; the maps are the committed ones.

Usage: python src/run_post.py --unit T10
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import torch
from loguru import logger

import stats8 as ST
from cfg8 import DATA, MAPS, RESULTS, UNITS, read_json, setup_logging, write_json, write_jsonl
from das8 import ClassMap, DecSite
from engine8 import load_lm
from run_dec import load_prompts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit", required=True)
    a = ap.parse_args()
    unit = a.unit
    setup_logging(f"run_post_{unit}")
    out_p = RESULTS / f"post_{unit}.json"
    if out_p.exists():
        return
    dec = read_json(RESULTS / f"dec_{unit}.json")
    L, k = dec["L_star"], dec["k_star"]
    P = load_prompts(unit)
    s3 = read_json(RESULTS / f"s3_{unit}.json")
    classes = s3["classes"]
    cmap = ClassMap(classes, {c: s3["class_sets"][c] for c in classes})
    held = [tuple(p) for p in read_json(DATA / f"pairs_{unit}.json")["held"]]
    lm = load_lm(UNITS[unit]["family"])
    bases = sorted({b for _, b in held})
    site = DecSite(lm, P, cmap, base_keys=bases, all_keys=sorted(set(bases) | {s for s, _ in held}))
    R0 = torch.load(MAPS / f"{unit}_dec_L{L}_seed0.pt")
    d_true = site.evaluate(L, held, R0[:, :k])["delta"]
    out = {"unit": unit, "L": L, "k_star": k, "mean_delta_true": float(d_true.mean()), "perm": {}}
    rows = []
    for f in sorted(MAPS.glob(f"{unit}_dec_L{L}_perm_*.pt")):
        name = f.stem.split("_perm_")[1]
        d = site.evaluate(L, held, torch.load(f)[:, :k])["delta"]
        out["perm"][name] = {"mean_delta": float(d.mean()),
                             "test_true_gt_perm": ST.cluster_wilcoxon_p(d_true, d, [p[0] for p in held],
                                                                        [p[1] for p in held])}
        rows += [{"fit": f"perm_{name}", "rank_k": k, "src": p[0], "base": p[1], "delta": float(d[i])}
                 for i, p in enumerate(held)]
        logger.info(f"{unit} perm {name}: {out['perm'][name]}")
    write_jsonl(DATA / f"tf_{unit}_dec_perm_L{L}.jsonl", rows)
    write_json(out_p, out)
    site.free()
    lm.free()


if __name__ == "__main__":
    main()
