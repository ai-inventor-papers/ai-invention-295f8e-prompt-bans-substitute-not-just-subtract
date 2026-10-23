#!/usr/bin/env python3
"""Stage 0.5 REPRODUCTION GATE and Stage 3 STATES with iteration 9's frozen M-code readout (E46 src/states.py
load_truncated + src/stage_mcode.py build / forward_readouts, unchanged): one teacher-forced pass per program over
neutral-twin context (W1-W5 frames with neutral nouns, E46 data/mcode_contexts.json) + SPEC as the user turn, chat
template with enable_thinking=False, assistant turn '```python\\n' + scrubbed code + '\\n```'; R1 = mean block output over
the code tokens, R1g (massive-activation-robust mean) and R2 (token after the first frontier pop) also stored.
Blocks [0, L-2 .. L+2] (L = 17 for Qwen3-8B bf16, 33 for Qwen3-32B NF4). Truncated decoders: 8B n_keep 20, 32B 36.

Usage:
  python src/states10.py gate <8b|32b>
  python src/states10.py extract <8b|32b> [--limit N]     # programs from data/state_items.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

from common import read_json, utc_now, write_json  # noqa: E402
from tpg2 import (DATA, E46_STATES, IN46, K_PRIMARY, L_STAR, LOGS, MODELS10, RESULTS, STATES, commit_utc,  # noqa: E402
                  ext_blocks)

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(LOGS / "states10.log"), rotation="30 MB", level="DEBUG")
READOUTS = ["R1", "R1g", "R2"]
VRAM_ABORT_GB = 18.5


def contexts() -> list[dict[str, Any]]:
    return read_json(IN46 / "data" / "mcode_contexts.json")["variants"]


def load(tag: str) -> tuple[Any, Any, dict[str, Any]]:
    import states
    import torch

    m = MODELS10[tag]
    g = read_json(IN46 / "results" / f"geometry_{tag}_mcode_PRIMARY_R1.json")
    assert g["L_star"]["block"] == L_STAR[tag], (g["L_star"]["block"], L_STAR[tag])
    assert m["n_keep"] == L_STAR[tag] + 3
    torch.cuda.set_per_process_memory_fraction(0.92)
    model, tok, info = states.load_truncated(m["repo"], m["precision"], m["n_keep"], revision=m["revision"])
    return model, tok, info


def one(model: Any, tok: Any, code: str, ctx_prompt: str, blocks: list[int]) -> tuple[np.ndarray, dict[str, Any]]:
    import stage_mcode

    b = stage_mcode.build(tok, code, ctx_prompt)
    assert b["decoded_equal"], "code span decode mismatch"
    arr, info = stage_mcode.forward_readouts(model, b["input_ids"], b["idx"], b["r2"], b["r3"], blocks)
    return arr, {"n_tokens": b["n_tokens"], "n_code_tokens": len(b["idx"]), "r2_rule": b["r2_rule"],
                 "r1g_excluded_max": max(info["r1g_excluded_by_block"].values())}


def gate(tag: str) -> dict[str, Any]:
    import geometry
    import states
    import torch

    L = L_STAR[tag]
    blocks = ext_blocks(tag)
    model, tok, info = load(tag)
    hc = states.hook_check(model, tok, ["def solve(grid, start, goal):\n    return []\n", "A short neutral text."])
    ms = read_json(IN46 / "data" / "mcode_sets.json")
    prim = [p for a, rows in ms["sets"]["PRIMARY"].items() for p in rows]
    prim = sorted({p["scrubbed_sha256"]: p for p in prim}.values(), key=lambda p: p["scrubbed_sha256"])[:5]
    z = np.load(E46_STATES / f"mcode_{tag}.npz")
    keys = list(z["keys"])
    zb = [int(b) for b in z["blocks"]]
    ctx = contexts()
    rows = []
    for p in prim:
        arr, _ = one(model, tok, p["scrubbed"], ctx[int(p["context_variant"])]["prompt"], blocks)
        new = arr[0, blocks.index(L)].astype(np.float64)
        old = z["R"][keys.index(p["scrubbed_sha256"]), 0, zb.index(L)].astype(np.float64)
        cos = float(new @ old / (np.linalg.norm(new) * np.linalg.norm(old)))
        rows.append({"uid": p["uid"], "algorithm": p["algorithm"], "cosine_R1_L": cos,
                     "rel_l2": float(np.linalg.norm(new - old) / np.linalg.norm(old))})
    gz = np.load(E46_STATES / f"geo_{tag}_mcode_PRIMARY_R1_k{K_PRIMARY}.npz")
    X, labels = gz["X"].astype(np.float64), gz["labels"]
    geo, ginfo = geometry.geodesics(X, K_PRIMARY)
    present = set(labels.tolist())
    B = [b for b in ["bfs", "dfs", "iddfs", "astar", "gbfs"] if b in present]
    NB = [a for a in ["bibfs", "biastar", "idastar", "jps", "dijkstra_unit"] if a in present]
    g, near = geometry.g_values(geo, labels, B, NB)
    rec = read_json(IN46 / "results" / f"geometry_{tag}_mcode_PRIMARY_R1.json")["L_star"]["describe"][f"k{K_PRIMARY}"]
    dg = abs(g["dijkstra_unit"] - rec["g"]["dijkstra_unit"])
    out = {"model": tag, "block": L, "load": info, "hook_check": hc, "programs": rows,
           "min_cosine": min(r["cosine_R1_L"] for r in rows), "cosine_pass": min(r["cosine_R1_L"] for r in rows) >= 0.9999,
           "g_dijkstra_unit_recomputed": g["dijkstra_unit"], "g_dijkstra_unit_recorded": rec["g"]["dijkstra_unit"],
           "g_abs_diff": dg, "g_pass": dg <= 0.03, "geo_max_abs_diff_vs_frozen": float(np.abs(geo - gz["geo"]).max()),
           "g_all": g, "nearest_banned": near, "frozen_median": rec["median"],
           "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2), "utc": utc_now()}
    out["pass"] = bool(out["cosine_pass"] and out["g_pass"])
    p = RESULTS / "repro_gate.json"
    allg = read_json(p) if p.exists() else {}
    allg[tag] = out
    write_json(p, allg)
    logger.info(f"REPRO GATE {tag}: min cos {out['min_cosine']:.6f}, g(UD) {g['dijkstra_unit']:.4f} vs "
                f"{rec['g']['dijkstra_unit']:.4f} -> {'PASS' if out['pass'] else 'FAIL'}; hook {hc}")
    return out


def extract(tag: str, limit: int | None = None) -> None:
    import torch

    assert commit_utc("COMMIT1") is not None, "states require COMMIT #1"
    items = read_json(DATA / "state_items.json")["items"]
    if limit:
        items = items[:limit]
    blocks = ext_blocks(tag)
    d = MODELS10[tag]["d"]
    part = STATES / f"tpg2_{tag}.partial.npz"
    done_ids: list[str] = []
    R = np.zeros((len(items), len(READOUTS), len(blocks), d), np.float16)
    meta: list[dict[str, Any]] = [None] * len(items)  # type: ignore[list-item]
    if part.exists():
        zp = np.load(part, allow_pickle=False)
        done_ids = [str(x) for x in zp["ids"]]
        pos = {it["id"]: i for i, it in enumerate(items)}
        mp_ = json.loads((STATES / f"tpg2_{tag}.partial_meta.json").read_text())
        for j, pid in enumerate(done_ids):
            if pid in pos:
                R[pos[pid]] = zp["R"][j]
                meta[pos[pid]] = mp_[pid]
        logger.info(f"resume: {len(done_ids)} programs from the checkpoint")
    model, tok, info = load(tag)
    ctx = contexts()
    t0 = time.time()
    n_new = 0
    for i, it in enumerate(items):
        if meta[i] is not None:
            continue
        arr, inf = one(model, tok, it["scrubbed"], ctx[int(it["context_variant"])]["prompt"], blocks)
        R[i] = arr[[0, 1, 2]].astype(np.float16)
        meta[i] = {"id": it["id"], **inf, "engine": MODELS10[tag]["engine"], "utc": utc_now()}
        n_new += 1
        if n_new == 1:
            peak = torch.cuda.max_memory_allocated() / 1e9
            logger.info(f"first program peak VRAM {peak:.1f} GB")
            if peak > VRAM_ABORT_GB:
                raise RuntimeError(f"peak VRAM {peak:.1f} GB > {VRAM_ABORT_GB}")
        if n_new % 50 == 0:
            ids = [items[j]["id"] for j in range(len(items)) if meta[j] is not None]
            sel = [j for j in range(len(items)) if meta[j] is not None]
            np.savez(part, R=R[sel], ids=np.array(ids))
            (STATES / f"tpg2_{tag}.partial_meta.json").write_text(json.dumps({items[j]["id"]: meta[j] for j in sel}))
            el = time.time() - t0
            logger.info(f"{tag}: {n_new} new ({len(sel)}/{len(items)}) {el:.0f}s ({el / n_new:.2f}s/program)")
    dt = time.time() - t0
    np.savez_compressed(STATES / f"tpg2_{tag}.npz", R=R, ids=np.array([it["id"] for it in items]),
                        blocks=np.array(blocks), readouts=np.array(READOUTS))
    write_json(RESULTS / f"states_{tag}.json", {"model": tag, "load": info, "n": len(items), "seconds": round(dt, 1),
                                                "sec_per_program": round(dt / max(1, n_new), 3), "blocks": blocks,
                                                "readouts": READOUTS, "engine": MODELS10[tag]["engine"],
                                                "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
                                                "meta": meta, "utc": utc_now()})
    for f in (part, STATES / f"tpg2_{tag}.partial_meta.json"):
        if f.exists():
            f.unlink()
    logger.info(f"states {tag}: {len(items)} programs in {dt:.0f}s")


if __name__ == "__main__":
    cmd, tag = sys.argv[1], sys.argv[2]
    if cmd == "gate":
        gate(tag)
    elif cmd == "extract":
        extract(tag, int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None)
