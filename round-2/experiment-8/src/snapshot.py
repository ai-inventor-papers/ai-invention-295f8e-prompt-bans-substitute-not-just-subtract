#!/usr/bin/env python3
"""S0: snapshot the iteration-1 inputs (read-only source) into inputs/iter1/ with a sha256 manifest, build the
working copy of the canonical suite (suite/), and re-check the canonical labeller on exp1's gold set + 22 refs."""

from __future__ import annotations

import collections
import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from cfg import INPUTS_ITER1, ITER1_EXP_DIRS, RESULTS_DIR, SUITE, read_jsonl, sha256_file, write_json

E = dict(ITER1_EXP_DIRS)  # iteration-1 experiment folders (artifact ids in cfg.UPSTREAM_IDS)

FILES: dict[str, list[str]] = {
    "exp1": ["prompts/conditions.json", "tasks", "labeller", "data/samples.jsonl", "common.py", "pipeline.py"],
    "exp2": ["prompts/prompts.jsonl", "data/samples_phaseA.jsonl", "data/samples_phaseC.jsonl",
             "data/samples_phaseD.jsonl", "cache/hR_index.jsonl"],
    "exp3": ["prompts/prompts.json", "generations/pools.jsonl"],
    "exp4": ["prompts/paraphrases.json", "prompts/scaffold.py", "common.py", "data/samples.jsonl",
             "cache/hR_index.json", "cache/hR_T1_ban-bfs.npy", "cache/hR_T1_mention-bfs.npy",
             "cache/hR_T2_ban-dijkstra.npy", "cache/hR_T2_mention-dijkstra.npy", "cache/hR_T1_baseline.npy",
             "cache/hR_T2_baseline.npy"]
            + [f"directions/d_dc_T{t}_L{l}.npy" for t in (1, 2) for l in range(8, 29)],
    "exp5": ["data/prompts.json", "runs/labelled_instruct_chat__ban.jsonl",
             "runs/labelled_instruct_chat__baseline.jsonl", "runs/samples.jsonl"],
}
REQUIRED = ["exp1/prompts/conditions.json", "exp1/tasks", "exp1/labeller"]


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    else:
        shutil.copy2(src, dst)


def _exp2_hr_subset() -> dict[str, Any]:
    """exp2's h_R cache is 21 x 11 MB; copy only the rows of the modal-ban and mention prompts used by C5."""
    idx = read_jsonl(E["exp2"] / "cache" / "hR_index.jsonl")
    keep = [i for i, r in enumerate(idx) if (r["task"], r["condition"]) in
            {("t1", "ban:bfs"), ("t2", "ban:dijkstra"), ("t1", "mention:bfs"), ("t2", "mention:dijkstra")}]
    arrs = {}
    for l in range(8, 29):
        a = np.load(E["exp2"] / "cache" / f"hR_layer{l}.npy", mmap_mode="r")
        arrs[f"L{l}"] = np.asarray(a[keep], dtype=np.float16)
    out = INPUTS_ITER1 / "exp2" / "cache" / "hR_subset.npz"
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, rows=np.array(keep), **arrs)
    (INPUTS_ITER1 / "exp2" / "cache" / "hR_subset_index.json").write_text(json.dumps([idx[i] for i in keep]))
    return {"n_rows": len(keep)}


def _neutral_candidates() -> None:
    """The 718 flagged neutral-noun candidates of the dependency's concreteness_norms (art_j3Rm_lr2nzR6)."""
    from cfg import DATASET_DIR, INPUTS

    d = json.loads((DATASET_DIR / "full_data_out.json").read_text())
    rows = next(ds["examples"] for ds in d["datasets"] if ds["dataset"] == "concreteness_norms")
    cand = [r for r in rows if r.get("metadata_noun_bank_candidate") in (True, "True", "true")]
    (INPUTS / "dataset").mkdir(parents=True, exist_ok=True)
    (INPUTS / "dataset" / "neutral_noun_candidates.json").write_text(json.dumps(cand))
    logger.info(f"neutral-noun candidates: {len(cand)}")


def stage_snapshot() -> dict[str, Any]:
    missing = []
    for exp, files in FILES.items():
        for f in files:
            src = E[exp] / f
            if not src.exists():
                missing.append(f"{exp}/{f}")
                logger.warning(f"iteration-1 input missing: {src}")
                continue
            _copy(src, INPUTS_ITER1 / exp / f)
    for r in REQUIRED:
        if r in missing:
            raise FileNotFoundError(f"required canonical-suite input missing: {r} (fallback F8 would apply)")
    sub = _exp2_hr_subset()
    _neutral_candidates()
    # manifest
    lines = []
    for p in sorted(INPUTS_ITER1.rglob("*")):
        if p.is_file() and p.name != "MANIFEST.sha256":
            lines.append(f"{sha256_file(p)}  {p.relative_to(INPUTS_ITER1)}")
    (INPUTS_ITER1 / "MANIFEST.sha256").write_text("\n".join(lines) + "\n")
    logger.info(f"snapshot: {len(lines)} files hashed into inputs/iter1/MANIFEST.sha256; missing={missing}")
    # suite working copy (byte-identical copies of exp1's canonical suite)
    for name in ("tasks", "labeller", "common.py"):
        _copy(INPUTS_ITER1 / "exp1" / name, SUITE / name)
    return {"n_files": len(lines), "missing": missing, "exp2_hr_subset": sub}


def stage_labeller_recheck() -> dict[str, Any]:
    """Gold re-check: combined label vs adjudicated on exp1 gold_set.jsonl (target >= 0.9) and 22/22 references."""
    from labelling import label_codes

    gold = read_jsonl(SUITE / "labeller" / "gold_set.jsonl")
    res = label_codes([{"task": g["task"], "code": g["code"]} for g in gold], use_judge=True, purpose="judge")
    rows = []
    for g, r in zip(gold, res):
        rows.append({"key": g["key"], "split": g["split"], "adjudicated": g["adjudicated"], "combined": r["label"],
                     "runtime": r["runtime_label"], "ast": r["ast_label"], "source": r["labeller_source"]})
    resolved = [r for r in rows if r["adjudicated"] != "unresolved"]
    acc = float(np.mean([r["combined"] == r["adjudicated"] for r in resolved])) if resolved else float("nan")
    acc_rt = float(np.mean([r["runtime"] == r["adjudicated"] for r in resolved])) if resolved else float("nan")
    ev = [r for r in resolved if r["split"] == "eval"]
    acc_eval = float(np.mean([r["combined"] == r["adjudicated"] for r in ev])) if ev else float("nan")
    # references
    refs = []
    for task, sub in (("t1", "t1_grid"), ("t2", "t2_wsp")):
        for p in sorted((SUITE / "tasks" / sub / "references").glob("*.py")):
            refs.append({"task": task, "file": p.name, "code": p.read_text(), "mode": _ref_mode(task, p.name)})
    rres = label_codes([{"task": r["task"], "code": r["code"]} for r in refs], use_judge=True, purpose="judge")
    ref_ok = [{"file": f"{r['task']}/{r['file']}", "mode": r["mode"], "label": x["label"], "passed": x["passed"],
               "ok": x["label"] == r["mode"] and x["passed"]} for r, x in zip(refs, rres)]
    n_ok = sum(r["ok"] for r in ref_ok)
    out = {"gold_n": len(rows), "gold_n_resolved": len(resolved), "acc_combined_vs_adjudicated": acc,
           "acc_combined_vs_adjudicated_eval_split": acc_eval, "acc_runtime_vs_adjudicated": acc_rt,
           "target": 0.9, "meets_target": bool(acc >= 0.9), "references_ok": n_ok, "references_n": len(ref_ok),
           "references_all_ok": n_ok == len(ref_ok), "references": ref_ok,
           "label_sources": dict(collections.Counter(r["source"] for r in rows)),
           "confusion": dict(collections.Counter(f"{r['combined']}->{r['adjudicated']}" for r in resolved
                                                 if r["combined"] != r["adjudicated"]))}
    write_json(RESULTS_DIR / "labeller_recheck.json", out)
    logger.info(f"labeller re-check: combined vs adjudicated {acc:.3f} (n={len(resolved)}), refs {n_ok}/{len(ref_ok)}")
    if not out["meets_target"] or not out["references_all_ok"]:
        logger.warning("labeller re-check MISSED its target -- flagged, proceeding (plan S0)")
    return out


def _ref_mode(task: str, fname: str) -> str:
    stem = Path(fname).stem
    pref = ((("bibfs", "bibfs"), ("bfs", "bfs"), ("dfs", "dfs"), ("iddfs", "iddfs"), ("astar", "astar_gbfs"),
             ("gbfs", "astar_gbfs"), ("dijkstra", "dijkstra")) if task == "t1" else
            (("bidijkstra", "bidijkstra"), ("dijkstra", "dijkstra"), ("bellman", "bf_spfa"), ("spfa", "bf_spfa"),
             ("floyd", "floyd"), ("dial", "dial")))
    for p, m in pref:
        if stem.startswith(p):
            return m
    raise ValueError(fname)
