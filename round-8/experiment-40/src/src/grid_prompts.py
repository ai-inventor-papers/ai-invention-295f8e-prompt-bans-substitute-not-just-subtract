#!/usr/bin/env python3
"""GRID prompts (gemma-3-4b-it, T1 grid path task), built with iteration 7's Gemma prompt code (inputs/exp38/src,
which reads iteration 6's frozen prompt inputs from inputs/exp38/inputs/iter6_gemma). Run as a separate process
(its module names clash with this artifact's). Writes one JSON record per prompt to argv[1]:
  forced    F1-F5 x display names j = 0..3 x mode in {bfs, dfs, astar_gbfs, iddfs} (bfs/dfs use iteration 7's
            equal-length display pairs; A*/IDDFS use four names each), padded to the W-twin's spec start
  twin      the 120 neutral twin variants (W1-W5 x 24 single-token nouns, iteration 6's construction)
  ban/top5/novelty   placement-only prompts
Every record carries dec_ids = prompt + c* (the canonical 32-token opening) and d = its last position.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "inputs" / "exp38" / "src"))

import numpy as np  # noqa: E402

import fork7 as FK  # noqa: E402
import prompts as PG  # noqa: E402
from cfg import FORCED_TEMPLATES, cap_first  # noqa: E402

DISPLAY = {
    "bfs": ("BFS", "breadth-first search", "a breadth-first search", "breadth-first search (BFS)"),
    "dfs": ("DFS", "depth-first search", "a depth-first search", "depth-first search (DFS)"),
    "astar_gbfs": ("A*", "A* search", "an A* search", "A* search (A-star)"),
    "iddfs": ("IDDFS", "iterative deepening", "iterative deepening DFS", "iterative deepening depth-first search"),
}
TRAIN_F = ("F1", "F2", "F3")
TRAIN_W = ("W1", "W2", "W3")


def finish(p: dict, **kw) -> dict:
    cs = FK.cstar()
    r = {"unit": "GRID", "family": "gemma", "ids": [int(t) for t in p["ids"]], "P": int(p["P"]),
         "spec_start": int(p["spec_start"]), "seg_start": int(p.get("seg_start", p["spec_start"])),
         "prompt_sha256": p.get("prompt_sha256")}
    r.update(kw)
    r["dec_ids"] = r["ids"] + cs
    r["d"] = len(r["dec_ids"]) - 1
    return r


def main() -> None:
    out_path = Path(sys.argv[1])
    rows = []
    for f, tmpl in FORCED_TEMPLATES.items():
        w = "W" + f[1:]
        tw = FK.twin(w)
        for mode, names in DISPLAY.items():
            for j, name in enumerate(names):
                seg = tmpl.format(Y=name)
                p = PG._pad_segment_to("T1", cap_first(seg), tw["spec_start"], "forced", f"forced:{mode}:{f}:{j}",
                                       X=mode, w=w)
                rows.append(finish(p, kind="forced", key=f"GRID|forced|{f}|j{j}|{mode}", template=f, fam=f,
                                   name_idx=j, Y=mode, segment=seg, aligned=bool(p.get("aligned", True)),
                                   split="train" if f in TRAIN_F else "held"))
    var = FK.variants()
    nouns = sorted({v["noun"] for v in var})
    rng = np.random.default_rng(8001)
    perm = list(rng.permutation(len(nouns)))
    n_train = int(round(0.7 * len(nouns)))
    ns = {nouns[i]: ("train" if r < n_train else "held") for r, i in enumerate(perm)}
    for v in var:
        w = v["template"]
        split = "train" if (w in TRAIN_W and ns[v["noun"]] == "train") else (
            "held" if (w not in TRAIN_W and ns[v["noun"]] == "held") else "neither")
        rows.append(finish(v, kind="twin", key=f"GRID|twin|{w}|{v['noun']}", w=w, noun=v["noun"],
                           noun_source=v["noun_source"], split_noun=ns[v["noun"]],
                           split_w="train" if w in TRAIN_W else "held", split=split))
    for w in ("W1", "W2", "W3", "W4", "W5"):
        try:
            rows.append(finish(PG.p_ban("T1", "bfs", w), kind="ban", key=f"GRID|ban|{w}", w=w, split="placement"))
        except Exception as e:  # noqa: BLE001
            print(f"ban {w} failed: {e}", file=sys.stderr)
    try:
        ban, _ = PG.p_top5("T1", "W1")
        rows.append(finish(ban, kind="top5", key="GRID|top5|W1", w="W1", split="placement"))
    except Exception as e:  # noqa: BLE001
        print(f"top5 failed: {e}", file=sys.stderr)
    try:
        rows.append(finish(PG.p_novelty("T1"), kind="instr_novel", key="GRID|novelty", split="placement"))
    except Exception as e:  # noqa: BLE001
        print(f"novelty failed: {e}", file=sys.stderr)
    with open(out_path, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print(f"grid prompts: {len(rows)}")


if __name__ == "__main__":
    main()
