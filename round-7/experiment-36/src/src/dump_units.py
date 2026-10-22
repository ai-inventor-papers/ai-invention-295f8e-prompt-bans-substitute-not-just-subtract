#!/usr/bin/env python3
"""Dump every dose unit in activation coordinates (GPU, instruct model, bf16; one twin prefill per template):
U_abs, U_bf, U_bf*, P_top, P_rest, P_shuf, the twin's per-cell residual norm ||h_twin[l, p]|| and the spec tokens,
for T10, T2, T03, T05, T1 x W1-W5 -> cache/units/<task>.npz and results/unit_profiles.json (per-block energies,
ratio of mean norms and mean per-position ratio of U_bf / U_abs: the confound the U_bf* arm splits).

usage: .venv/bin/python src/dump_units.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

import k_cfg as K  # noqa: E402
import gen_k as G  # noqa: E402


@logger.catch(reraise=True)
def main() -> None:
    K.setup_logging("dump_units")
    tok, model = G.load_model(fp8=False, vram_fraction=0.97)
    prompts = G.load_prompts()
    out_dir = K.CACHE / "units"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {}
    for task in K.D5_TASKS:
        ctx = G.TaskCtxK(model, prompts, task)
        arrs: dict[str, np.ndarray] = {"U_abs": ctx.n_abs}
        for name in ("P_top", "P_rest", "P_shuf"):
            arrs[name] = ctx.profiles[name]["unit"]
        arrs["mask_top"] = ctx.profiles["P_top"]["mask"]
        rec = {}
        for w in K.TEMPLATES:
            tw = ctx.twin(w)
            arrs[f"U_bf_{w}"] = tw["U_bf"]
            arrs[f"U_bf_star_{w}"] = tw["U_bf_star"]
            arrs[f"h_norm_{w}"] = tw["h_norm"]
            p = tw["prompt"]
            toks = [tok.decode([i]) for i in p["ids"][p["p1"]:p["spec_end"]]]
            arrs[f"tokens_{w}"] = np.array(toks, dtype=object)
            ub, ua = tw["U_bf"].astype(np.float64), ctx.n_abs.astype(np.float64)
            rec[w] = {"ratio_of_mean_norms_per_block": (ub.mean(1) / ua.mean(1)).round(4).tolist(),
                      "mean_per_position_ratio_per_block": (ub / ua).mean(1).round(4).tolist(),
                      "fro_ratio_per_block": (np.linalg.norm(ub, axis=1) / np.linalg.norm(ua, axis=1)).round(4).tolist(),
                      "fro_ratio_total": float(np.linalg.norm(ub) / np.linalg.norm(ua)),
                      "U_abs_over_hnorm_max": float((ua / tw["h_norm"]).max()),
                      "U_bf_over_hnorm_max": float((ub / tw["h_norm"]).max()),
                      "top_quartile_energy_share_U_abs": float(ctx.profiles["P_top"]["energy_share"]),
                      "top_quartile_energy_share_U_bf": float(((ub * ctx.profiles["P_top"]["mask"]) ** 2).sum()
                                                              / (ub ** 2).sum())}
            ctx.release()
        np.savez_compressed(out_dir / f"{task}.npz", **{k: v for k, v in arrs.items() if v.dtype != object},
                            **{k: v.astype(str) for k, v in arrs.items() if v.dtype == object})
        summary[task] = rec
        logger.info(f"{task}: units dumped; W1 fro ratio U_bf/U_abs {rec['W1']['fro_ratio_total']:.3f}")
    K.write_json(K.RESULTS / "unit_profiles.json", summary)


if __name__ == "__main__":
    main()
