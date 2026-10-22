#!/usr/bin/env python3
"""Regenerate cache/<unit>/n_<template>.npy (the ban-free push norms n[l, p] = r_Q(l) ||h_twin_clean[l, p]|| from a
clean twin prefill, fp16) and directions/rand_<seed>.npy for every direction seed used in data/samples_raw.jsonl.
Usage: uv run src/prefill_cache.py --all   (needs the instruct model on a GPU for the norms; directions are CPU)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg5 import MODEL_ID, MODEL_REVISION, RAW, TEMPLATE_IDS, read_jsonl  # noqa: E402
from ctx5 import UnitCtx, rand_dir  # noqa: E402


def main() -> None:
    seeds = sorted({int(r["direction_seed"]) for r in read_jsonl(RAW) if r.get("direction_seed") is not None})
    for s in seeds:
        rand_dir(s)
    print(f"{len(seeds)} directions regenerated")
    if "--all" in sys.argv:
        import units_extra  # noqa: F401
        from engine5 import load_model
        from prompts5 import load_prompts
        tok, model = load_model(MODEL_ID, MODEL_REVISION)
        pr = load_prompts()
        units = sorted({p["unit"] for p in pr.values() if p["kind"] == "twin"})
        for u in units:
            twins = {p["template_id"]: p for p in pr.values() if p["unit"] == u and p["kind"] == "twin"}
            ctx = UnitCtx(model, u, twins)
            for w in TEMPLATE_IDS:
                if w in twins:
                    ctx.twin(w)
            ctx.release()
        print(f"norm caches regenerated for {len(units)} units")


if __name__ == "__main__":
    main()
