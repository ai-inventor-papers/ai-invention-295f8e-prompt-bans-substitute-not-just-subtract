#!/usr/bin/env python3
"""S8: random-initialisation control (c3, Sutter et al.). The same config is built from scratch (torch seed 0, HF
post_init -> _init_weights, bf16); caches are recomputed for identical token ids; DAS is refitted at the TRAINED L*
(and, for T10, at the band) with the same pairs, steps, early stopping and map class, with targets = the TRAINED
model's q_src and the trained model's class labels. c3 = mean held-out Delta toward the source class (random-init /
trained) <= 0.25; one-sided pair-level test trained > random-init (Wilcoxon + two-way cluster bootstrap).

Usage: python src/run_rinit.py --unit T10|GRID [--band]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import torch
from loguru import logger

import stats8 as ST
from cfg8 import (CACHE, DATA, FAMILY, FIT_SEEDS, FIT_STEPS, MAPS, RESULTS, THRESH, UNITS, read_json, read_jsonl,
                  setup_logging, write_json)
from das8 import BandSite, ClassMap, DecSite
from engine8 import load_lm
from run_dec import fam_of, load_prompts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit", required=True)
    ap.add_argument("--band", action="store_true")
    ap.add_argument("--band_minutes", type=float, default=12)
    ap.add_argument("--force_L", type=int, default=None, help="post-hoc site (reads dec_<unit>_L<L>.json)")
    a = ap.parse_args()
    unit = a.unit
    setup_logging(f"run_rinit_{unit}")
    rtag = f"_L{a.force_L}" if a.force_L is not None else ""
    out_p = RESULTS / (f"rinit_{unit}_band.json" if a.band else f"rinit_{unit}{rtag}.json")
    if out_p.exists():
        logger.info(f"{out_p.name} exists")
        return
    U = UNITS[unit]
    P = load_prompts(unit)
    s3 = read_json(RESULTS / f"s3_{unit}.json")
    classes = s3["classes"]
    cmap = ClassMap(classes, {c: s3["class_sets"][c] for c in classes})
    dec = read_json(RESULTS / f"dec_{unit}{rtag}.json")
    pairs = read_json(DATA / f"pairs_{unit}.json")
    q_tr = torch.load(CACHE / f"q_{unit}_dec_trained.pt")
    cls_tr = {k: int(v[:len(classes)].argmax()) for k, v in q_tr.items()}
    train = [tuple(p) for p in pairs["train"]]
    held = [tuple(p) for p in pairs["held"]]
    lm = load_lm(U["family"], random_init=True)
    # U8: near-uniform next-token entropy and logits different from the trained model's
    from engine8 import prefill
    ks = [held[0][1], held[0][0]]
    ent = []
    for k in ks:
        lg = prefill(lm, P[k]["dec_ids"])["logits"]
        p = torch.softmax(lg, -1)
        ent.append(float(-(p * p.clamp(min=1e-30).log()).sum()))
    res: dict[str, Any] = {"unit": unit, "U8_entropy_nats": ent, "U8_pass_gt_8": bool(min(ent) > 8)}
    fams_tr = sorted({fam_of(P[s]) for s in pairs["sources_train"]})
    t0 = time.time()
    if not a.band:
        L, kd = dec["L_star"], dec["k_star"]
        base_kinds = ("twin", "padtwin") if unit == "T10" else ("twin",)
        need_b = sorted({b for _, b in train} | {b for _, b in held})
        need_all = sorted(set(need_b) | {s for s, _ in train} | {s for s, _ in held})
        site = DecSite(lm, P, cmap, base_keys=need_b, all_keys=need_all, G=4, Q=12)
        site.cls = dict(cls_tr)              # trained classes define the margin direction
        full = site.evaluate(L, held, None)
        fits = {}
        for sd in FIT_SEEDS[:1]:
            vf = fams_tr[sd % len(fams_tr)]
            tp = [p for p in train if fam_of(P[p[0]]) != vf]
            vp = [p for p in train if fam_of(P[p[0]]) == vf]
            vp = [vp[i] for i in np.random.default_rng(sd).choice(len(vp), size=min(96, len(vp)), replace=False)]
            fits[sd] = site.fit(L, tp, vp, seed=sd, targets=q_tr, steps=FIT_STEPS, log_name=f"rinit {unit} L{L}")
            torch.save(fits[sd]["R"], MAPS / f"{unit}_dec_L{L}_rinit_seed{sd}.pt")
        R = fits[0]["R"]
        tf = [r for r in read_jsonl(DATA / f"tf_{unit}_dec{rtag}.jsonl") if r["fit"] == "seed0" and r["rank_k"] == kd]
        tr_delta = {(r["src"], r["base"]): r["delta"] for r in tf}
        by_k = {}
        for k in (1, 2, 4, 8):
            ev = site.evaluate(L, held, R[:, :k])
            by_k[k] = {"mean_delta_rinit": float(ev["delta"].mean()),
                       "kl_mean": float(ev["kl"].mean())}
            if k == kd:
                d_r = ev["delta"]
        d_t = np.array([tr_delta[p] for p in held])
        ratio = float(d_r.mean() / d_t.mean()) if d_t.mean() else None
        test = ST.cluster_wilcoxon_p(d_t, d_r, [p[0] for p in held], [p[1] for p in held])
        res.update({"site": "dec", "L": L, "k_star": kd, "by_rank": by_k,
                    "mean_delta_trained": float(d_t.mean()), "mean_delta_rinit": float(d_r.mean()),
                    "ratio": ratio, "pass": bool(ratio is not None and ratio <= THRESH["c3_ratio_max"]),
                    "test_trained_gt_rinit": test, "rinit_full_state_mean_delta": float(full["delta"].mean()),
                    "fit": {k: v for k, v in fits[0].items() if k not in ("R", "hist")},
                    "seconds": round(time.time() - t0, 1)})
        site.free()
    else:
        band = read_json(RESULTS / "band_T10.json")
        kb = band["k_star"]
        steps = band["timing"]["steps"]
        from run_band import stratified
        held96 = stratified(held, cls_tr, 96, 0)
        base_keys = sorted({b for _, b in train} | {b for _, b in held96})
        src_keys = sorted({s for s, _ in train} | {s for s, _ in held96})
        site = BandSite(lm, P, cmap, tuple(FAMILY["qwen"]["band"]), base_keys, src_keys, cls_tr)
        vf = fams_tr[0]
        tp = [p for p in train if fam_of(P[p[0]]) != vf]
        vp = stratified([p for p in train if fam_of(P[p[0]]) == vf], cls_tr, 32, 0)
        f = site.fit(tp, vp, seed=0, q_tgt=q_tr, steps=steps, log_name="rinit band",
                     deadline=time.time() + a.band_minutes * 60)
        torch.save(f["R"], MAPS / "T10_band_rinit_seed0.pt")
        m0 = site.base_margins(held96)
        ev = site.evaluate(held96, f["R"][:, :kb])
        d_r = ev["m"] - m0
        tf = [r for r in read_jsonl(DATA / "tf_T10_band.jsonl") if r["fit"] == "seed0" and r["rank_k"] == kb]
        tr_delta = {(r["src"], r["base"]): r["delta"] for r in tf}
        d_t = np.array([tr_delta[p] for p in held96])
        ratio = float(d_r.mean() / d_t.mean()) if d_t.mean() else None
        res.update({"site": "band", "k_star": kb, "mean_delta_trained": float(d_t.mean()),
                    "mean_delta_rinit": float(d_r.mean()), "ratio": ratio,
                    "pass": bool(ratio is not None and ratio <= THRESH["c3_ratio_max"]),
                    "test_trained_gt_rinit": ST.cluster_wilcoxon_p(d_t, d_r, [p[0] for p in held96],
                                                                   [p[1] for p in held96]),
                    "fit": {k: v for k, v in f.items() if k not in ("R", "hist")}, "steps_budget": steps,
                    "seconds": round(time.time() - t0, 1)})
        site.free()
    write_json(out_p, res)
    logger.info(f"rinit {unit} band={a.band}: ratio {res.get('ratio')} pass {res.get('pass')}")
    lm.free()


if __name__ == "__main__":
    main()
