#!/usr/bin/env python3
"""S7a (optional, CPU): per-module relative weight change between Qwen3-8B (instruct) and Qwen3-8B-Base,
||W_I - W_B||_F / ||W_B||_F for q/k/v/o/gate/up/down per layer plus embed_tokens, final norm and lm_head, streamed one
tensor at a time from the safetensors shards; for the unembedding also the change restricted to the fork class rows
(D and A tokens of B3 and T10). Correlates the per-layer MLP change with the per-layer single-MLP CMAP shares.
Writes results/weight_change.json."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
from loguru import logger
from safetensors import safe_open

from cfg9 import N_LAYERS, RESULTS_DIR, model_path, read_json, setup_logging, write_json

MODS = {"q": "self_attn.q_proj", "k": "self_attn.k_proj", "v": "self_attn.v_proj", "o": "self_attn.o_proj",
        "gate": "mlp.gate_proj", "up": "mlp.up_proj", "down": "mlp.down_proj"}


def shards(key: str) -> tuple[Path, dict[str, str]]:
    p = Path(model_path(key))
    return p, json.loads((p / "model.safetensors.index.json").read_text())["weight_map"]


def get(p: Path, wm: dict[str, str], name: str) -> torch.Tensor:
    with safe_open(str(p / wm[name]), framework="pt") as fh:
        return fh.get_tensor(name).float()


def main() -> None:
    pI, wI = shards("qwen")
    pB, wB = shards("qwen_base")
    out: dict = {"per_layer": {m: [] for m in MODS}}
    for l in range(N_LAYERS):
        for m, suf in MODS.items():
            n = f"model.layers.{l}.{suf}.weight"
            a, b = get(pI, wI, n), get(pB, wB, n)
            out["per_layer"][m].append(float((a - b).norm() / b.norm()))
            del a, b
        logger.info(f"layer {l}: " + " ".join(f"{m} {out['per_layer'][m][-1]:.4f}" for m in MODS))
    for n in ("model.embed_tokens.weight", "model.norm.weight", "lm_head.weight"):
        a, b = get(pI, wI, n), get(pB, wB, n)
        out[n] = float((a - b).norm() / b.norm())
        if n == "lm_head.weight":
            U = read_json(RESULTS_DIR / "units.json")
            rows = {}
            for u in ("B3", "T10"):
                f = U[u]["forks"][0]
                for t, s in zip(f["D"] + f["A"], f["D_str"] + f["A_str"]):
                    rows[f"{u}:{s}"] = {"rel_change": float((a[t] - b[t]).norm() / b[t].norm()),
                                        "cos": float(torch.nn.functional.cosine_similarity(a[t], b[t], dim=0)),
                                        "norm_ratio": float(a[t].norm() / b[t].norm())}
            allrel = ((a - b).norm(dim=1) / b.norm(dim=1).clamp_min(1e-8)).numpy()
            out["lm_head_fork_rows"] = rows
            out["lm_head_row_rel_change_median"] = float(np.median(allrel))
            out["lm_head_row_rel_change_p95"] = float(np.percentile(allrel, 95))
            for k, v in rows.items():
                v["pctile_among_all_rows"] = float((allrel < v["rel_change"]).mean() * 100)
        del a, b
    b2 = read_json(RESULTS_DIR / "b2_summary.json")
    corr = {}
    for u in ("B3", "T10"):
        s = b2["units"][u]["singles"]
        sh = [s.get(f"mlp|L{l}", 0.0) for l in range(N_LAYERS)]
        for m in ("gate", "up", "down"):
            corr[f"{u}:{m}"] = float(np.corrcoef(out["per_layer"][m], sh)[0, 1])
    out["corr_mlp_change_vs_single_mlp_share"] = corr
    write_json(RESULTS_DIR / "weight_change.json", out)
    logger.info(f"lm_head rel change {out['lm_head.weight']:.4f}; embed {out['model.embed_tokens.weight']:.4f}; "
                f"norm {out['model.norm.weight']:.4f}; fork rows {rows}")


if __name__ == "__main__":
    setup_logging("weightdiff9")
    main()
