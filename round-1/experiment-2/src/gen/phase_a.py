#!/usr/bin/env python3
"""Phase A (vLLM): baseline (N=200/task), forced named (30x1/mode), masked (30x1/mode), association elicitation.

Staged 10 -> 100 -> full inside one engine lifetime; seconds/sample are appended to logs/timing.jsonl and
the full-run time is extrapolated before the full run starts.
Outputs: data/raw_phaseA.jsonl (programs, unlabelled) and data/elicit_phaseA.jsonl (rankings).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "gen"))
from common import (CATALOGUE, DECODING_GEN, DISPLAY, MODEL_TAG, add_deviation, append_jsonl, log_timing,  # noqa: E402
                    read_jsonl, setup_logger, stable_seed, write_jsonl)
from hf_engine import hf_sample, load_model  # noqa: E402

logger = setup_logger("phase_a")
N_BASE_PER_PARA = 20


def gen_requests(prompts: list[dict], n_base: int) -> list[dict]:
    reqs = []
    for p in prompts:
        if p["kind"] != "geom":
            continue
        cond = p["condition"]
        if cond == "baseline":
            n = n_base
        elif cond.startswith("forced:") or cond.startswith("masked:"):
            n = 1
        else:
            continue
        for s in range(n):
            reqs.append({"task": p["task"], "condition": cond, "paraphrase_id": p["paraphrase_id"], "sample_id": s,
                         "prompt_id": p["prompt_id"], "prompt_ids": p["prompt_ids"], "max_tokens": 1024,
                         "seed": stable_seed(p["task"], cond, p["paraphrase_id"], s), "model": MODEL_TAG,
                         "decoding": DECODING_GEN})
    return reqs


def parse_ranking(text: str, task: str, x: str) -> list[str] | None:
    """Parse a JSON list of display names into mode ids (must be a permutation of the K-1 others)."""
    others = [m for m in CATALOGUE[task] if m != x]
    name2mode = {DISPLAY[task][m].lower(): m for m in others}
    m = re.search(r"\[.*?\]", text, re.DOTALL)
    if not m:
        return None
    try:
        lst = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(lst, list):
        return None
    out = []
    for item in lst:
        if not isinstance(item, str):
            return None
        key = item.strip().lower()
        mode = name2mode.get(key)
        if mode is None:  # tolerate small formatting drift: unique containment match
            cands = [mm for nm, mm in name2mode.items() if key and (key in nm or nm in key)]
            mode = cands[0] if len(cands) == 1 else None
        if mode is None or mode in out:
            return None
        out.append(mode)
    if sorted(out) != sorted(others):
        return None
    return out


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--skip-elicit", action="store_true")
    ap.add_argument("--skip-extra", action="store_true")
    args = ap.parse_args()
    add_deviation("Generation engine: vLLM 0.32 could not start (Triton needs a C compiler; the container has none), so "
                  "every phase samples with batched HF transformers generate (bf16, sdpa, left padding, identical token "
                  "ids). Sampling noise is seeded per batch (torch.manual_seed) instead of per request.")
    prompts = read_jsonl(ROOT / "prompts" / "prompts.jsonl")
    model, tok = load_model(logger)
    out_path = ROOT / "data" / "raw_phaseA.jsonl"
    done_keys = {(r["task"], r["condition"], r["paraphrase_id"], r["sample_id"]) for r in read_jsonl(out_path)}
    reqs = [r for r in gen_requests(prompts, N_BASE_PER_PARA)
            if (r["task"], r["condition"], r["paraphrase_id"], r["sample_id"]) not in done_keys]
    logger.info(f"resuming: {len(done_keys)} programs already sampled")
    core = [r for r in reqs if r["condition"] != "baseline" or r["sample_id"] < N_BASE_PER_PARA // 2]
    extra = [r for r in reqs if r["condition"] == "baseline" and r["sample_id"] >= N_BASE_PER_PARA // 2]
    # interleave so every batch mixes arms; similar prompt lengths keep padding small
    core.sort(key=lambda r: (r["paraphrase_id"] % 10, r["sample_id"], r["condition"], r["task"]))
    extra.sort(key=lambda r: (r["sample_id"], r["paraphrase_id"], r["task"]))
    logger.info(f"Phase A: {len(core)} core + {len(extra)} extra baseline program requests")
    t_start = time.time()
    done = 0
    stages = [("core_a", core[: len(core) // 2]), ("core_b", core[len(core) // 2:])]
    if not args.skip_extra:
        stages.append(("extra_baseline", extra))
    for si, (name, batch) in enumerate(stages):
        if not batch:
            continue
        if name == "extra_baseline":
            # elicitation first (short), then the second half of the baseline
            if not args.skip_elicit:
                run_elicitation(model, tok, prompts)
        t0 = time.time()
        rows = hf_sample(model, tok, batch, logger, batch_size=args.batch, seed_base=stable_seed("phaseA", name) % 100000)
        dt = time.time() - t0
        for r in rows:
            r["utc"] = time.time()
        append_jsonl(out_path, rows)
        done += len(batch)
        log_timing("A", name, len(batch), dt)
        nfin = sum(r["finish_reason"] == "length" for r in rows)
        ncode = sum(r["code"] is not None for r in rows)
        logger.info(f"stage {name}: {len(batch)} in {dt:.0f}s ({dt / len(batch):.2f}s/sample); code parse "
                    f"{ncode}/{len(rows)}, truncated {nfin}; remaining requests {sum(len(b) for _, b in stages[si + 1:])} "
                    f"-> ~{sum(len(b) for _, b in stages[si + 1:]) * dt / len(batch) / 60:.1f} min")
    if args.skip_extra and not args.skip_elicit:
        run_elicitation(model, tok, prompts)
    logger.info(f"Phase A done in {(time.time() - t_start) / 60:.1f} min")


def run_elicitation(model, tok, prompts: list[dict]) -> None:
    """Association elicitation: 20 rankings per (task, X); re-ask with a new seed on parse failure (max 3)."""
    el_prompts = [p for p in prompts if p["kind"] == "elicit"]
    pending = [{"task": p["task"], "condition": p["condition"], "paraphrase_id": p["paraphrase_id"], "sample_id": 0,
                "prompt_id": p["prompt_id"], "prompt_ids": p["prompt_ids"], "max_tokens": 200, "stop": False,
                "order": p["order"], "model": MODEL_TAG, "decoding": "T=1.0,top_p=1.0,max_tokens=200,thinking=off"}
               for p in el_prompts]
    results = []
    for attempt in range(3):
        if not pending:
            break
        for r in pending:
            r["attempt"] = attempt
        t0 = time.time()
        rows = hf_sample(model, tok, pending, logger, batch_size=48, seed_base=stable_seed("elicit", attempt) % 100000,
                         stop=False)
        log_timing("A", f"elicit_attempt{attempt}", len(rows), time.time() - t0)
        nxt = []
        for req, row in zip(pending, rows):
            x = row["condition"].split(":", 1)[1]
            rk = parse_ranking(row["raw_text"], row["task"], x)
            row["ranking"] = rk
            row["parsed"] = rk is not None
            if rk is None and attempt < 2:
                nxt.append(req)
            else:
                results.append(row)
        logger.info(f"elicit attempt {attempt}: {len(rows) - len(nxt)} final, {len(nxt)} to re-ask")
        pending = nxt
    write_jsonl(ROOT / "data" / "elicit_phaseA.jsonl", results)
    logger.info(f"elicitation: {sum(r['parsed'] for r in results)}/{len(results)} parsed")


if __name__ == "__main__":
    main()
