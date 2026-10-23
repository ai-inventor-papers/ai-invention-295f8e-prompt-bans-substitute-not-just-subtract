#!/usr/bin/env python3
"""Stage 1.10 DESIGN CHECK + frame lists for COMMIT #1. Applies the hand reads (factorial RLX / RND / CRD programs and
the audited ones; top-up class reads; survivor families), caps each factorial cell at its first 16 accepted programs
in (round, slot) order, picks the G1 cells (>= 10 programs, PROBE excluded), checks the discipline-container design,
assigns context variants (seeded round-robin within cell / class / family) and writes data/frames.json,
data/state_items.json and results/design.json."""

from __future__ import annotations

import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

from accept import jaccard, shingles  # noqa: E402
from common import read_jsonl, sha256_text, utc_now  # noqa: E402
from tpg2 import (DATA, REQUESTED_CELLS, RESULTS, cell_dc, write_json)  # noqa: E402

CAP = 16
MIN_CELL = 10
F0_MIN = 10
B5 = ["bfs", "dfs", "iddfs", "astar", "gbfs"]
NB5 = ["dijkstra_unit", "idastar", "bibfs", "jps", "biastar"]
PLANNED = {cell_dc(c): c for c in REQUESTED_CELLS}


def cv_assign(items: list[dict[str, Any]], key: str) -> None:
    by = defaultdict(list)
    for it in items:
        by[it[key]].append(it)
    for k, xs in by.items():
        off = random.Random(sha256_text(str(k))).randrange(5)
        for r, it in enumerate(xs):
            it["context_variant"] = (off + r) % 5


def main() -> None:
    hand = defaultdict(list)
    for h in read_jsonl(DATA / "hand_reads.jsonl"):
        hand[h["uid"]].append(h)
    last = {u: v[-1] for u, v in hand.items()}
    # ------------------------------------------------------------------ factorial
    fact = read_jsonl(DATA / "factorial.jsonl")
    n_override = 0
    for r in fact:
        if not r.get("valid"):
            continue
        h = last.get(r["uid"])
        r["hand_read"] = h
        if h and h.get("read_disc"):
            d, c = h["read_disc"], h["read_cont"]
            if (d, c) != (r["disc"], r["cont"]):
                n_override += 1
                r["instrument_disc_cont"] = [r["disc"], r["cont"]]
                r["disc"], r["cont"] = d, c
                r["disputed"] = True
            req = r["requested_cell"]
            if req == "PROBE":
                r["accepted"] = (d, c) == ("LEV", "DEQ")
                r["cell"] = "PROBE"
            elif (d, c) == cell_dc(req):
                r["accepted"], r["cell"], r["reassigned"] = True, req, False
            elif (d, c) in PLANNED:
                r["accepted"], r["cell"], r["reassigned"] = True, PLANNED[(d, c)], True
            else:
                r["accepted"], r["reject"] = False, f"hand_read_{d}_{c}"
    acc = defaultdict(list)
    for r in sorted([r for r in fact if r.get("accepted")], key=lambda r: (r["round"], r["slot"])):
        acc[r["cell"]].append(r)
    capped = {c: xs[:CAP] for c, xs in acc.items()}
    g1_cells = [c for c in REQUESTED_CELLS if len(capped.get(c, [])) >= MIN_CELL]
    fact_items = []
    for c, xs in capped.items():
        for r in xs:
            fact_items.append({"id": r["uid"], "cell": c, "disc": r["disc"], "cont": r["cont"],
                               "requested_cell": r["requested_cell"], "reassigned": bool(r.get("reassigned")),
                               "round": r["round"], "template": r["template"], "slot": r["slot"],
                               "scrubbed": r["scrubbed"], "scrubbed_sha256": r["scrubbed_sha256"],
                               "disputed": bool(r.get("disputed")), "author": "qwen3-32b"})
    cv_assign(fact_items, "cell")
    # ------------------------------------------------------------------ top-ups
    tops = {r["uid"]: r for r in read_jsonl(DATA / "topup_candidates.jsonl")}
    top_items = []
    for u, h in last.items():
        if h.get("set") == "topup" and h.get("accept") and u in tops and tops[u].get("valid"):
            r = tops[u]
            top_items.append({"id": u, "algorithm": h["read_class"], "disc": r["disc"], "cont": r["cont"],
                              "scrubbed": r["scrubbed"], "scrubbed_sha256": r["scrubbed_sha256"], "source": r["source"]})
    cv_assign(top_items, "algorithm")
    # ------------------------------------------------------------------ PRIMARY (cached states) measured
    prim = [r for r in read_jsonl(DATA / "primary_measured.jsonl")]
    prim_items = [{"id": r["uid"], "algorithm": r["algorithm"], "disc": r.get("disc"), "cont": r.get("cont"),
                   "e46_key": r["e46_scrubbed_sha256"], "valid_now": bool(r.get("valid")),
                   "context_variant": int(r["context_variant"]) if r.get("context_variant") is not None else 0}
                  for r in prim]
    f0_counts = Counter([p["algorithm"] for p in prim_items] + [t["algorithm"] for t in top_items])
    f0_classes = [a for a in B5 + NB5 if f0_counts.get(a, 0) >= F0_MIN]
    # ------------------------------------------------------------------ survivors / covert / PROBE
    surv = {r["uid"]: r for r in read_jsonl(DATA / "survivor_candidates.jsonl")}
    surv_items = []
    for u, r in surv.items():
        if not r.get("valid"):
            continue
        h = last.get(u)
        fam = h["family"] if h else r.get("family_v9")
        d, c = (h["read_disc"], h["read_cont"]) if h else (r["disc"], r["cont"])
        surv_items.append({"id": u, "family": fam, "family_split": f"{fam}-{d}", "disc": d, "cont": c,
                           "instrument": [r["disc"], r["cont"]], "source": r["source"], "scrubbed": r["scrubbed"],
                           "scrubbed_sha256": r["scrubbed_sha256"], "e46_key": r.get("e46_scrubbed_sha256")})
    cv_assign(surv_items, "family")
    cov_items = [{"id": r["uid"], "label_v9": r["label_v9"], "disc": r["disc"], "cont": r["cont"],
                  "cell_v9": r["cell_v9"], "scrubbed": r["scrubbed"], "scrubbed_sha256": r["scrubbed_sha256"]}
                 for r in read_jsonl(DATA / "placed_covert.jsonl") if r.get("kept")]
    cv_assign(cov_items, "label_v9")
    # ------------------------------------------------------------------ design check
    cells = g1_cells
    disc = {c: cell_dc(c)[0] for c in cells}
    cont = {c: cell_dc(c)[1] for c in cells}
    disc_conts = defaultdict(set)
    for c in cells:
        disc_conts[disc[c]].add(cont[c])
    # bipartite connectivity
    adj = defaultdict(set)
    for c in cells:
        adj["d:" + disc[c]].add("c:" + cont[c])
        adj["c:" + cont[c]].add("d:" + disc[c])
    seen, stack = set(), [next(iter(adj))] if adj else []
    while stack:
        x = stack.pop()
        if x in seen:
            continue
        seen.add(x)
        stack += list(adj[x] - seen)
    iu = np.triu_indices(len(cells), 1)
    Dd = np.array([[disc[a] != disc[b] for b in cells] for a in cells], float)[iu]
    Dc = np.array([[cont[a] != cont[b] for b in cells] for a in cells], float)[iu]
    surf, lens, tmpl, rnds = {}, {}, {}, {}
    for c in cells:
        xs = [it for it in fact_items if it["cell"] == c]
        sh = [shingles(it["scrubbed"]) for it in xs]
        js = [1 - jaccard(a, b) for i, a in enumerate(sh) for b in sh[i + 1:]]
        surf[c] = float(np.mean(js)) if js else None
        lens[c] = float(np.mean([len(it["scrubbed"]) for it in xs]))
        tmpl[c] = dict(Counter(it["template"] for it in xs))
        rnds[c] = dict(Counter(it["round"] for it in xs))
    design = {"cells_ge10": len(cells), "required": 12, "g1_cells": cells,
              "all_cells_counts_accepted_uncapped": {c: len(acc.get(c, [])) for c in REQUESTED_CELLS + ["PROBE"]},
              "bipartite_connected": len(seen) == len(adj), "discipline_containers": {d: sorted(v) for d, v in disc_conts.items()},
              "disciplines_in_lt2_containers": sorted(d for d, v in disc_conts.items() if len(v) < 2),
              "spearman_Ddisc_Dcont": float(spearmanr(Dd, Dc).statistic) if len(cells) > 2 else None,
              "within_cell_surface_distance": surf, "mean_chars": lens, "templates": tmpl, "rounds": rnds,
              "context_variants": {c: dict(Counter(it["context_variant"] for it in fact_items if it["cell"] == c))
                                   for c in cells},
              "n_hand_read_overrides_factorial": n_override,
              "f0_counts": dict(f0_counts), "f0_classes_ge10": f0_classes,
              "f0_nonbanned_ge10": [a for a in NB5 if a in f0_classes],
              "survivor_family_split_counts": dict(Counter(s["family_split"] for s in surv_items)),
              "covert_counts": dict(Counter((c["label_v9"], c["disc"]) for c in cov_items).items()) if False else
              {f"{k[0]}->{k[1]}": v for k, v in Counter((c["label_v9"], c["disc"]) for c in cov_items).items()},
              "utc": utc_now()}
    design["g1_supportable"] = bool(len(cells) >= 12 and design["bipartite_connected"])
    write_json(RESULTS / "design.json", design)
    frames = {"g1_cells": [{"cell": c, "disc": disc[c], "cont": cont[c], "n": len(capped[c])} for c in cells],
              "factorial": [{k: v for k, v in it.items() if k != "scrubbed"} for it in fact_items],
              "topups": [{k: v for k, v in it.items() if k != "scrubbed"} for it in top_items],
              "primary": prim_items, "f0_classes": f0_classes, "survivors": [{k: v for k, v in it.items() if k != "scrubbed"}
                                                                             for it in surv_items],
              "covert": [{k: v for k, v in it.items() if k != "scrubbed"} for it in cov_items],
              "cap_per_cell": CAP, "min_cell": MIN_CELL, "utc": utc_now()}
    write_json(DATA / "frames.json", frames)
    items = []
    for it in fact_items:
        items.append({"id": it["id"], "set": "factorial", "scrubbed": it["scrubbed"], "context_variant": it["context_variant"]})
    for it in top_items:
        items.append({"id": it["id"], "set": "topup", "scrubbed": it["scrubbed"], "context_variant": it["context_variant"]})
    for it in surv_items:
        items.append({"id": it["id"], "set": "survivor", "scrubbed": it["scrubbed"], "context_variant": it["context_variant"]})
    for it in cov_items:
        items.append({"id": it["id"], "set": "covert", "scrubbed": it["scrubbed"], "context_variant": it["context_variant"]})
    write_json(DATA / "state_items.json", {"items": items, "n": len(items), "utc": utc_now()})
    print({k: design[k] for k in ("cells_ge10", "g1_cells", "bipartite_connected", "disciplines_in_lt2_containers",
                                  "spearman_Ddisc_Dcont", "f0_classes_ge10", "survivor_family_split_counts",
                                  "all_cells_counts_accepted_uncapped")})
    print("state items", len(items))


if __name__ == "__main__":
    main()
