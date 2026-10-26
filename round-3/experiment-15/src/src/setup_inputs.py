#!/usr/bin/env python3
"""Step A: provenance of every copied input (sha256 + size), bench sha256 verification against bench/commitment.json,
exp10 canon SHA256SUMS check, exp8 suite vs exp10 canon cross-check, model shard sha256s vs exp10's model record,
the dependency dataset inventory, and the X0 freeze (FP8 pilot modal attempted label per task)."""

from __future__ import annotations

import collections
import json
import os
from pathlib import Path

from loguru import logger

from src.commit import utc_now
from src.ws import (BENCH, EXP10, EXP11, FROZEN_TASKS, INPUTS, MODEL_ID, MODEL_REV, PRED, RESULTS, model_path,
                    read_json, read_jsonl, sha256_file, write_json)

from bench.common import catalogue as CAT  # noqa: E402

# Dataset artifact art_j3Rm_lr2nzR6 (full_data_out.json lives outside this workspace on the run volume); override with
# AII_DEP_DATASET_DIR=<its folder>.  Default: a sibling folder named after the artifact id.
DEP_DATASET = Path(os.environ.get("AII_DEP_DATASET_DIR", str(Path(__file__).resolve().parent.parent.parent / "art_j3Rm_lr2nzR6")))


def provenance() -> dict:
    rows = []
    for p in sorted(INPUTS.rglob("*")):
        if p.is_file():
            rows.append({"path": str(p.relative_to(INPUTS)), "sha256": sha256_file(p), "bytes": p.stat().st_size})
    src = {"exp11": "iter_2/gen_art/gen_art_experiment_11", "exp10": "iter_2/gen_art/gen_art_experiment_10",
           "exp8": "iter_2/gen_art/gen_art_experiment_8", "exp7": "iter_2/gen_art/gen_art_experiment_7",
           "dataset": "art_j3Rm_lr2nzR6 (gen_art_dataset_1)"}
    out = {"n_files": len(rows), "sources": src, "files": rows, "utc": utc_now()}
    write_json(INPUTS / "provenance.json", out)
    return out


def verify_bench() -> dict:
    com = read_json(BENCH / "commitment.json")
    res = {}
    for t, ent in com["tasks"].items():
        tdir = BENCH / CAT.TASKS[t]["task_id"]
        bad = []
        n = 0
        for rel, sha in ent["files"].items():
            if rel == "catalogue":
                continue
            f = tdir / rel
            n += 1
            if not f.exists() or sha256_file(f) != sha:
                bad.append(rel)
        res[t] = {"n_files": n, "mismatched": bad, "ok": not bad}
    return res


def verify_canon() -> dict:
    canon = EXP10 / "canon"
    sums = (canon / "SHA256SUMS").read_text().splitlines() if (canon / "SHA256SUMS").exists() else []
    bad, n = [], 0
    for line in sums:
        if not line.strip():
            continue
        sha, rel = line.split(maxsplit=1)
        rel = rel.strip().lstrip("*")
        f = canon / rel
        n += 1
        if not f.exists() or sha256_file(f) != sha:
            bad.append(rel)
    # exp8 suite vs exp10 canon (same relative paths)
    suite = INPUTS / "exp8" / "suite"
    cmp_same, cmp_diff, only8 = 0, [], []
    for f in sorted(suite.rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts:
            rel = f.relative_to(suite)
            g = canon / rel
            if not g.exists():
                only8.append(str(rel))
            elif sha256_file(f) == sha256_file(g):
                cmp_same += 1
            else:
                cmp_diff.append(str(rel))
    return {"canon_sha256sums_entries": n, "canon_mismatched": bad, "canon_ok": not bad and n > 0,
            "exp8_vs_exp10_identical": cmp_same, "exp8_vs_exp10_differ": cmp_diff, "only_in_exp8": only8[:50],
            "screen_uses": "exp10 canon/ (exp10's landings were labelled with it)"}


def model_record() -> dict:
    mp = Path(model_path())
    ref = read_json(EXP10 / "results" / "model_record.json")
    shards = {}
    for name, ent in ref["shards"].items():
        f = mp / name
        sha = sha256_file(f) if f.exists() else None
        shards[name] = {"sha256": sha, "bytes": f.stat().st_size if f.exists() else None,
                        "matches_exp10": sha == ent["sha256"]}
    gc = json.loads((mp / "generation_config.json").read_text())
    rec = {"repo_id": MODEL_ID, "commit_sha": MODEL_REV, "local_path": "<run shared HF cache>/models--meta-llama--"
           "Llama-3.1-8B-Instruct/snapshots/" + MODEL_REV, "shards": shards,
           "all_shards_match_exp10": all(v["matches_exp10"] for v in shards.values()), "generation_config": gc,
           "generation_config_overridden": "every SamplingParams field explicit; LLM(generation_config='vllm')",
           "dtype": "bfloat16"}
    write_json(RESULTS / "model_record.json", rec)
    return rec


def dependency_inventory() -> dict:
    """The dependency dataset (art_j3Rm_lr2nzR6): per-dataset example counts and the bench mapping it provides.
    Streams the 96 MB full file with a regex-free json load of the preview/mini plus a counted scan of the full."""
    out = {"path": "<dependency art_j3Rm_lr2nzR6 folder>", "files": {}}
    for name in ("preview_data_out.json", "mini_data_out.json", "full_data_out.json"):
        f = DEP_DATASET / name
        if f.exists():
            out["files"][name] = {"bytes": f.stat().st_size, "sha256": sha256_file(f)}
    full = DEP_DATASET / "full_data_out.json"
    if full.exists():
        d = json.loads(full.read_text())
        ds = {}
        for blk in d["datasets"]:
            ex = blk["examples"]
            ent = {"n_examples": len(ex)}
            if blk["dataset"] == "leetcodedataset":
                bt = collections.Counter(e.get("metadata_bench_task") for e in ex if e.get("metadata_bench_task"))
                ent["bench_task_map"] = dict(bt)
            if blk["dataset"] == "concreteness_norms":
                ent["neutral_noun_candidates"] = sum(1 for e in ex if e.get("metadata_neutral_noun_candidate"))
            ds[blk["dataset"]] = ent
        out["datasets"] = ds
        out["role_in_this_artifact"] = {
            "leetcodedataset": "bench tasks + hidden tests (built in exp11; frozen copy in inputs/exp11/bench)",
            "mercury": "bench references / efficiency calibration (exp11 build)",
            "llm_creativity": "path-task (T2) prior labels (exp1/exp10 lineage; screen only)",
            "thealgorithms_python": "AST-rule negatives (exp11 labeller gate)",
            "clrs_text": "tracer tests (exp11 labeller gate)",
            "humanevalplus": "harness smoke test (exp11)",
            "enamel": "time-limit calibration (exp11)",
            "concreteness_norms": "neutral nouns (bench neutral_nouns.json; exp10 noun_bank.json fallback ranking)",
            "kodcode_algorithmic": "AST-rule negatives / name lexicon (exp11)",
            "xlcost_python": "AST-rule negatives / name lexicon (exp11)",
        }
        del d
    write_json(RESULTS / "dependency_inventory.json", out)
    return out


def freeze_x0() -> dict:
    f = PRED / "x0.json"
    if f.exists():
        return read_json(f)
    rows = read_jsonl(EXP11 / "data" / "samples_llama_pilot.jsonl")
    x0, shares = {}, {}
    for t in FROZEN_TASKS:
        modes = list(CAT.TASKS[t]["modes"])
        att = [r for r in rows if r["task"] == t and r["label"] != "invalid"]
        c = collections.Counter(r["label"] for r in att if r["label"] in modes)
        best = max(modes, key=lambda m: (c.get(m, 0), -modes.index(m)))
        x0[t] = best
        shares[t] = {"n_attempted": len(att), "counts": dict(c), "share": c.get(best, 0) / max(len(att), 1)}
    out = {"x0": x0, "source": "exp11 data/samples_llama_pilot.jsonl (FP8 Llama pilot, exp11 combined labels), "
           "modal attempted catalogue label", "shares": shares, "utc": utc_now(),
           "note": "frozen before any generation of this artifact"}
    write_json(f, out)
    return out


def run() -> dict:
    prov = provenance()
    vb = verify_bench()
    vc = verify_canon()
    mr = model_record()
    x = freeze_x0()
    inv = dependency_inventory()
    res = {"provenance_files": prov["n_files"], "bench": vb, "bench_all_ok": all(v["ok"] for v in vb.values()),
           "canon": vc, "model_shards_match": mr["all_shards_match_exp10"], "x0": x["x0"],
           "dependency_datasets": {k: v.get("n_examples") for k, v in inv.get("datasets", {}).items()}}
    write_json(RESULTS / "input_integrity.json", res)
    logger.info(f"input integrity: bench_all_ok={res['bench_all_ok']} canon_ok={vc['canon_ok']} "
                f"shards_match={res['model_shards_match']} x0={x['x0']}")
    return res
