#!/usr/bin/env python3
"""S9: generation on held-out pairs, scored by hidden tests (COMMIT #2 per family first).

Per (unit, site) and off-default class c (a class that is not the base's class):
  BASE (unedited base) 30 | FULL 30 | DAS k* 30 | RAND k* 30 (Haar seeds rotate over slots) | PERM k* 20 |
  REV-DAS k* 20 | REV-FULL 20 | SRC (unedited forced source) 20; primary class only: the two ranks of {1, 2, 4}
  other than k* (30 each).
Slot s of class c: base = held base list[s % n], source = held sources of class c [s % m]; every arm of slot s
shares the uniform stream u_stream(unit, site, 'iter8', s). Decision-site cells prefill the canonical opening and edit
the block-L* output at d; band cells edit the band's spec positions in the prefill and generate from index 0.

Usage: python src/run_gen.py --unit T10 --sites dec,band [--n 30 --n_sup 20] [--minutes 40]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import torch
from loguru import logger

from cfg8 import (CACHE, DATA, FAMILY, MAPS, OPEN_T10, RANDOM_SEED0, RESULTS, ROOT, UNITS, add_deviation, read_json,
                  setup_logging, sha256_file, write_json)
from commit8 import commit
from das8 import haar
from engine8 import load_lm, states_at
from gen8 import band_edit, dec_edit, interchange_fn, run_rows
from run_dec import load_prompts


def held_lists(unit: str, P: dict, cls: dict, classes: list[str], pairs: dict) -> dict[str, Any]:
    bases = sorted([b for b in pairs["bases_held"] if P[b]["kind"] == "twin"])
    out = {}
    for ci, c in enumerate(classes):
        srcs = sorted(s for s in pairs["sources_held"] if cls[s] == ci)
        bs = [b for b in bases if cls[b] != ci]
        if srcs and bs:
            out[c] = {"sources": srcs, "bases": bs}
    return out


def padtwin_of(unit: str, P: dict, s: str) -> str:
    if unit == "T10":
        return P[s]["key"].replace("|forced|", "|padtwin|")
    w = "W" + P[s]["template"][1:]
    return next(k for k, r in P.items() if r["kind"] == "twin" and r["w"] == w)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit", required=True)
    ap.add_argument("--sites", default="dec")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--n_sup", type=int, default=20)
    ap.add_argument("--minutes", type=float, default=40)
    ap.add_argument("--B", type=int, default=16)
    a = ap.parse_args()
    unit = a.unit
    setup_logging(f"run_gen_{unit}")
    deadline = time.time() + a.minutes * 60
    U = UNITS[unit]
    fam = U["family"]
    P = load_prompts(unit)
    s3 = read_json(RESULTS / f"s3_{unit}.json")
    classes = s3["classes"]
    dec = read_json(RESULTS / f"dec_{unit}.json")
    pairs = read_json(DATA / f"pairs_{unit}.json")
    q_tr = torch.load(CACHE / f"q_{unit}_dec_trained.pt")
    cls = {k: int(v[:len(classes)].argmax()) for k, v in q_tr.items()}
    sites = a.sites.split(",")
    band = read_json(RESULTS / "band_T10.json") if "band" in sites else None
    L, kd = dec["L_star"], dec["k_star"]
    Rdec = torch.load(MAPS / f"{unit}_dec_L{L}_seed0.pt")
    perm_name = next(n for n in ("pi1", "prompt", "shuffle0") if (MAPS / f"{unit}_dec_L{L}_perm_{n}.pt").exists())
    Rperm = torch.load(MAPS / f"{unit}_dec_L{L}_perm_{perm_name}.pt")
    HL = held_lists(unit, P, cls, classes, pairs)
    off = [c for c in classes if c in HL and c != U["default"]]
    primary = U["primary"] if U["primary"] in off else off[0]
    other_ranks = [k for k in (1, 2, 4) if k != kd][:2]
    cells = []
    for site in sites:
        for c in off:
            cells += [(site, "BASE", c, a.n), (site, "FULL", c, a.n), (site, "DAS", c, a.n), (site, "RAND", c, a.n),
                      (site, "PERM", c, a.n_sup), (site, "REV-DAS", c, a.n_sup), (site, "REV-FULL", c, a.n_sup),
                      (site, "SRC", c, a.n_sup)]
            if c == primary:
                kk = other_ranks if site == "dec" else [k for k in (1, 2, 4) if k != band["k_star"]][:2]
                cells += [(site, f"DAS_k{k}", c, a.n) for k in kk]
    slot_map = {c: [{"slot": s, "base": HL[c]["bases"][s % len(HL[c]["bases"])],
                     "source": HL[c]["sources"][s % len(HL[c]["sources"])]} for s in range(a.n)] for c in off}
    commit(f"commit2_{unit}_{'_'.join(sites)}", {
        "unit": unit, "L_star": L, "k_star_dec": kd, "k_star_band": band["k_star"] if band else None,
        "perm_map_used": perm_name, "cells": cells, "slot_map": slot_map,
        "tf_tables_sha256": {f.name: sha256_file(f) for f in sorted(DATA.glob(f"tf_{unit}_*.jsonl"))},
        "dec_results_sha256": sha256_file(RESULTS / f"dec_{unit}.json"),
        "prediction": "decision site: DAS k* moves at least half as many slots to the source class as FULL; RAND <= "
                      "BASE + 2/30; pass ratio >= 0.8" + ("; band: V0 passes, c4/c5 fail" if band else "")})
    # ---- labeller worker
    flag = RESULTS / f"gen_done_{unit}.flag"
    if flag.exists():
        flag.unlink()
    lab = subprocess.Popen([sys.executable, str(ROOT / "src" / "label8.py"), "--unit", unit, "--follow", str(flag),
                            "--workers", "4"], stdout=open(ROOT / "logs" / f"label8_{unit}.out", "a"),
                           stderr=subprocess.STDOUT)
    lm = load_lm(fam)
    open_ids = {k: P[k]["dec_ids"][P[k]["P"]:] for k in P}
    need = sorted({x["base"] for c in off for x in slot_map[c]} | {x["source"] for c in off for x in slot_map[c]} |
                  {padtwin_of(unit, P, x["source"]) for c in off for x in slot_map[c]})
    st = states_at(lm, [P[k]["dec_ids"] for k in need], blocks=[L])
    H = {k: st["h"][i][0] for i, k in enumerate(need)}
    del st
    bandsrc: dict[str, torch.Tensor] = {}
    if band:
        from engine8 import prefill
        bl = list(FAMILY[fam]["band"])
        for k in need:
            r = P[k]
            store = {}

            def mk(l: int):
                def g(h: torch.Tensor) -> None:
                    store[l] = h[0, r["p1"]:r["spec_end"]].detach().clone()
                return g
            prefill(lm, r["ids"], capture={l: mk(l) for l in bl})
            bandsrc[k] = torch.stack([store[l] for l in bl]).cpu()
        Rband = torch.load(MAPS / "T10_band_seed0.pt")
        pb = "pi1" if (MAPS / "T10_band_perm_pi1.pt").exists() else "prompt"
        Rband_perm = torch.load(MAPS / f"T10_band_perm_{pb}.pt") if (MAPS / f"T10_band_perm_{pb}.pt").exists() else None
    rows = []
    for (site, arm, c, n) in cells:
        for s in range(n):
            sm = slot_map[c][s]
            b, src = sm["base"], sm["source"]
            pt = padtwin_of(unit, P, src)
            meta = {"unit": unit, "site": site, "cell": f"{site}|{arm}|{c}", "arm": arm, "target_class": c,
                    "slot": s, "base_key": b, "source_key": src, "class_src": classes[cls[src]],
                    "class_base": classes[cls[b]], "layer": L if site == "dec" else "band"}
            ukey = (unit, site, "iter8", s)
            k_site = kd if site == "dec" else band["k_star"]
            if arm == "BASE":
                sid = f"{unit}|{site}|BASE|{b}|{s}"
                kind, base_key, edit = "none", b, None
            elif arm == "SRC" or arm == "REV-DAS" or arm == "REV-FULL":
                sid = f"{unit}|{site}|{arm}|{c}|{s}"
                base_key = src
                meta.update({"base_key": src, "source_key": pt, "class_base": classes[cls[src]],
                             "class_src": classes[cls[pt]]})
                kind = {"SRC": "none", "REV-DAS": "das", "REV-FULL": "full"}[arm]
            else:
                sid = f"{unit}|{site}|{arm}|{c}|{s}"
                base_key = b
                kind = {"FULL": "full", "DAS": "das", "RAND": "rand", "PERM": "perm"}.get(arm, "das")
            rank = int(arm.split("_k")[1]) if arm.startswith("DAS_k") else k_site
            meta.update({"rank_k": rank if kind in ("das", "rand", "perm") else None, "edit": kind})
            srck = meta["source_key"]
            if site == "dec":
                ids = P[base_key]["dec_ids"]
                prefix = open_ids[base_key]
                if kind == "none":
                    edits = None
                else:
                    if kind == "full":
                        R = None
                    elif kind == "das":
                        R = Rdec[:, :rank]
                    elif kind == "rand":
                        R = haar(RANDOM_SEED0 + s % 50, lm.D, rank)
                        meta["direction_seed"] = RANDOM_SEED0 + s % 50
                    else:
                        R = Rperm[:, :rank]
                    edits = dec_edit(L, interchange_fn(H[srck], R))
                max_new = U["max_new"]
            else:
                ids = P[base_key]["ids"]
                prefix = []
                r = P[base_key]
                S = r["spec_end"] - r["p1"]
                if kind == "none":
                    edits = None
                else:
                    if kind == "full":
                        R = None
                    elif kind == "das":
                        R = Rband[:, :rank]
                    elif kind == "rand":
                        R = haar(RANDOM_SEED0 + s % 50, lm.D, rank)
                        meta["direction_seed"] = RANDOM_SEED0 + s % 50
                    else:
                        R = Rband_perm[:, :rank] if Rband_perm is not None else None
                        if R is None:
                            continue
                    edits = band_edit(list(FAMILY[fam]["band"]), r["p1"], S, bandsrc[srck], R)
                max_new = U["max_new"]
            rows.append({"sample_id": sid, "ids": ids, "edits": edits, "ukey": ukey, "prefix_ids": prefix,
                         "max_new": max_new, "meta": meta})
    # de-duplicate shared BASE rows (identical base + slot across classes)
    seen, uniq = set(), []
    for r in rows:
        if r["sample_id"] in seen:
            continue
        seen.add(r["sample_id"])
        uniq.append(r)
    logger.info(f"{unit}: {len(uniq)} generation rows over {len(cells)} cells")
    # pilot first (10 slots of BASE / FULL / DAS / RAND, primary class, decision site), then everything
    pilot = [r for r in uniq if r["meta"]["site"] == sites[0] and r["meta"]["target_class"] == primary
             and r["meta"]["arm"] in ("BASE", "FULL", "DAS", "RAND") and r["meta"]["slot"] < 10]
    run_rows(lm, unit, pilot, U["fence"], a.B, f"{unit}-pilot", deadline)
    rest = [r for r in uniq if r not in pilot]
    order = {"BASE": 0, "FULL": 1, "DAS": 2, "RAND": 3, "SRC": 4, "REV-DAS": 5, "REV-FULL": 6, "PERM": 7}
    rest.sort(key=lambda r: (order.get(r["meta"]["arm"], 8), r["meta"]["site"], r["meta"]["slot"]))
    run_rows(lm, unit, rest, U["fence"], a.B, f"{unit}-gen", deadline)
    flag.write_text("done")
    lm.free()
    try:
        lab.wait(timeout=5)
    except subprocess.TimeoutExpired:
        logger.info("label worker keeps running in the background (follows the done flag)")
    logger.info("generation done")


if __name__ == "__main__":
    main()
