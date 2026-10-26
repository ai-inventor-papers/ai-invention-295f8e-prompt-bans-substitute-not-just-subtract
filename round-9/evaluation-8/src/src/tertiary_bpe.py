#!/usr/bin/env python3
"""Optional tertiary lexical score of item 0e (committed as optional in predictions/commit_s0e.json): Qwen3 BPE
token-set Jaccard, using the tokenizer of the very checkpoint whose states built the manifold (unsloth/Qwen3-32B-bnb-4bit),
read offline from the run's shared HF cache. Sensitivity only; the committed verdict uses the primary score.

uv run src/tertiary_bpe.py   (after eval.py has written results/s0e.json)
"""
from __future__ import annotations

import csv
import glob
import json
import os
import sys
from pathlib import Path

import numpy as np
from loguru import logger
from tokenizers import Tokenizer

sys.path.insert(0, str(Path(__file__).resolve().parent))
import alias_geometry as AG  # noqa: E402
import stage_0e as S0E  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
import recompute as RC  # noqa: E402

TP_SRC = RC.ART[RC.TP] / "src"
CACHE = str(Path(os.environ.get("HF_HUB_CACHE") or Path(os.environ.get("HF_HOME", "")) / "hub")
            / "models--unsloth--Qwen3-32B-bnb-4bit" / "snapshots" / "*" / "tokenizer.json")


@logger.catch(reraise=True)
def main() -> dict | None:
    paths = sorted(glob.glob(CACHE))
    if not paths:
        logger.warning("tokenizer not cached offline: tertiary score not run (as committed)")
        return None
    tok = Tokenizer.from_file(paths[0])
    alias_table = AG.read_literal(TP_SRC / "common.py", "ALIAS_TABLE")
    ids = lambda s: set(tok.encode(" " + s, add_special_tokens=False).ids)  # noqa: E731 - alias as it sits in the prompt
    banned = [ids(s) for b in AG.BANNED for s in alias_table[b]]
    rows = []
    for a in AG.NONBANNED:
        for j, s in enumerate(alias_table[a]):
            t = ids(s)
            jac = max(len(t & b) / len(t | b) for b in banned)
            rows.append({"algorithm": a, "alias_index": j, "alias": s, "bpe_tokens": tok.encode(" " + s, add_special_tokens=False).tokens,
                         "tertiary": jac})
    x3 = np.array([r["tertiary"] for r in rows])
    z = json.loads((ROOT / "results/s0e.json").read_text())
    rng = np.random.default_rng(AG.SEED + 3)
    n_dist = AG.n_distinct_assignments(list(x3))
    null = S0E.exact_null(x3) if n_dist <= 2_000_000 else S0E.mc_null(x3, AG.N_MC_SECONDARY, rng)
    out = {"tokenizer": paths[0].split("hub/")[1], "rows": rows, "n_distinct_arrangements": n_dist,
           "null": "exact" if n_dist <= 2_000_000 else f"monte_carlo_{AG.N_MC_SECONDARY}", "per_k": {}}
    for k in ("k15", "k10"):
        g = np.array([z["per_k"][k]["g_alias"][f"{a}|{j}"] for a in AG.NONBANNED for j in range(3)])
        r = AG.spearman(g, x3)
        st = AG.stratified_exact(g.reshape(5, 3), x3.reshape(5, 3))
        out["per_k"][k] = {"rho_tertiary": r, **S0E.pvals(r, null), "stratified": st}
        logger.info(f"tertiary {k}: rho {r:.3f} p {out['per_k'][k]['p_lower']:.4f}; stratified {st['stat']:.3f} "
                    f"p {st['p_lower']:.3f}")
    (ROOT / "results/s0e_tertiary.json").write_text(json.dumps(out, indent=1, default=float))
    with (ROOT / "tables/alias_tertiary.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["algorithm", "alias_index", "alias", "bpe_tokens", "tertiary_bpe_jaccard", "g_k15", "g_k10"])
        for r in rows:
            key = f"{r['algorithm']}|{r['alias_index']}"
            w.writerow([r["algorithm"], r["alias_index"], r["alias"], " ".join(r["bpe_tokens"]), round(r["tertiary"], 6),
                        round(z["per_k"]["k15"]["g_alias"][key], 6), round(z["per_k"]["k10"]["g_alias"][key], 6)])
    return out


if __name__ == "__main__":
    main()
