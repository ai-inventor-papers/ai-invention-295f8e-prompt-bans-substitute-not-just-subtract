#!/usr/bin/env python3
"""Prepare the G1-T input (token ids, real-model margins, position classes) for src/ct_graph.py (main venv)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fork7 as FK  # noqa: E402
import g1  # noqa: E402
from cfg import B_IDS, D_IDS, RESULTS_DIR, TC_REPO, TC_REV, TC_SUB, read_json  # noqa: E402

cs = FK.cstar()
P = g1.g1_prompts()
ys = {v["vid"]: v["y"] for v in read_json(RESULTS_DIR / "yv.json")["variants"]}
src_y = {s["sid"]: s["y"] for s in read_json(RESULTS_DIR / "yv.json")["sources"]}
order = [p for p in P if p["kind"] == "variant" and p["cls"] == "bfs"][:5] + \
        [p for p in P if p["kind"] == "variant" and p["cls"] == "dfs"][:5] + [p for p in P if p["kind"] == "forced"] + \
        [p for p in P if p["kind"] == "variant" and p["cls"] == "bfs"][5:] + \
        [p for p in P if p["kind"] == "variant" and p["cls"] == "dfs"][5:]
items = []
for p in order:
    pc = {}
    for c, ps in p["pos"].items():
        for q in ps:
            pc[str(q)] = c
    m = ys.get(p["vid"]) if p["kind"] == "variant" else src_y.get(p["sid"])
    items.append({"vid": p["vid"], "cls": p["cls"], "ids": p["ids"] + cs, "m_real": m, "pos_class": pc})
cfg = {"model": "google/gemma-3-4b-it", "transcoders": f"{TC_REPO}/{TC_SUB}@{TC_REV}", "batch_size": 64,
       "max_feature_nodes": 7500, "node_threshold": 0.8, "edge_threshold": 0.98}
Path(sys.argv[1]).write_text(json.dumps({"config": cfg, "B": list(B_IDS), "D": list(D_IDS), "prompts": items}))
print(len(items), "prompts")
