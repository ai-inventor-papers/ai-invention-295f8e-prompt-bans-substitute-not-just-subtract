#!/usr/bin/env python3
"""S0: copy every read-only input of the plan's builds_on list into inputs/ (sha256 -> inputs/input_hashes.json) and
extract what this artifact uses from the declared dataset dependency art_j3Rm_lr2nzR6 (all ten datasets are scanned:
counts per dataset, the single-token neutral-noun bank from concreteness_norms, and every connected-components
reference program for the novelty audit's nearest-known solutions -> inputs/dep_extract.json).

Usage: .venv/bin/python src/s0_inputs.py
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger

from cfg8 import INPUTS, LOOP, ROOT, add_deviation, setup_logging, sha256_file, write_json

# Source artifacts by id. Resolution order: $AII_ARTIFACTS_DIR/<id> (a folder of sibling artifact folders, e.g. the
# published repository root), then ../<id> next to this folder, then the run layout <run>/3_invention_loop/<iter>/...
ARTIFACTS = {"art_veI9l_Rb9wDY": ("round-7", "experiment-33/src"), "art_pHL7LWNhpcCS": ("round-7", "experiment-34/src"),
             "art_HY7uYZz-OjRW": ("round-7", "experiment-38/src"), "art_lpQalcAXMGr1": ("round-6", "experiment-29/src"),
             "art_rMlbrjVB1c__": ("round-6", "experiment-30/src")}


def art_dir(art_id: str) -> Path:
    for base in (os.environ.get("AII_ARTIFACTS_DIR"), str(ROOT.parent)):
        if base and (Path(base) / art_id).exists():
            return Path(base) / art_id
    it, ex = ARTIFACTS[art_id]
    return LOOP / it / "." / ex


def dep_dir() -> Path:
    """The declared dataset dependency art_j3Rm_lr2nzR6: $ART_J3RM_DIR, else ../art_j3Rm_lr2nzR6, else the run layout."""
    for c in (os.environ.get("ART_J3RM_DIR"), str(ROOT.parent / "art_j3Rm_lr2nzR6")):
        if c and Path(c).exists():
            return Path(c)
    return LOOP.parents[1] / "run_4VFKidE1bxPG" / "." / "round-1" / "." / "dataset-1/src"


E33, E34, E38 = art_dir("art_veI9l_Rb9wDY"), art_dir("art_pHL7LWNhpcCS"), art_dir("art_HY7uYZz-OjRW")
E29, E30 = art_dir("art_lpQalcAXMGr1"), art_dir("art_rMlbrjVB1c__")
DEP_DIR = dep_dir()

COPIES = [  # (source relative to LOOP-derived roots, destination under inputs/)
    (E33 / "prompts" / "prompts7.jsonl", "exp33/prompts7.jsonl"),
    (E33 / "inputs" / "exp11" / "bench", "exp11/bench"),
    (E33 / "das_maps" / "T10_MAIN_LY.pt", "exp33/T10_MAIN_LY.pt"),
    (E33 / "results" / "p1.json", "exp33/p1.json"),
    (E33 / "src", "exp33/src"),
    (E34 / "results" / "forks.json", "exp34/forks.json"),
    (E34 / "results" / "force_token.json", "exp34/force_token.json"),
    (E34 / "results" / "fork_token_probs.json", "exp34/fork_token_probs.json"),
    (E34 / "results" / "remeasure.json", "exp34/remeasure.json"),
    (E34 / "cache" / "states" / "dbar_T10.npz", "exp34/dbar_T10.npz"),
    (E34 / "src", "exp34/src"),
    (E38 / "src", "exp38/src"),
    (E38 / "inputs" / "iter6_gemma", "exp38/inputs/iter6_gemma"),
    (E38 / "results" / "g2_das.json", "exp38/results/g2_das.json"),
    (E38 / "results" / "g2_layer_scan.json", "exp38/results/g2_layer_scan.json"),
    (E38 / "results" / "engine_check.json", "exp38/results/engine_check.json"),
    (E38 / "cache" / "das_subspaces", "exp38/das_subspaces"),
    (E29 / "inputs" / "exp22", "exp29/exp22"),
    (E29 / "vendor" / "exp22" / "directions", "exp22/directions"),
    (E29 / "data" / "labels.jsonl", "exp29/labels.jsonl"),
    (E29 / "results" / "known_solutions.json", "exp29/known_solutions.json"),
    (E30 / "src", "exp30/src"),
    (E30 / "prompts", "exp30/prompts"),
]


def copy_all() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for src, dst in COPIES:
        d = INPUTS / dst
        if not src.exists():
            add_deviation("S0_missing_input", f"input not found: {dst} (source {src.name})")
            continue
        if src.is_dir():
            if not d.exists():
                shutil.copytree(src, d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            d.parent.mkdir(parents=True, exist_ok=True)
            if not d.exists():
                shutil.copy2(src, d)
        files = [d] if d.is_file() else sorted(p for p in d.rglob("*") if p.is_file())
        for f in files:
            hashes[str(f.relative_to(INPUTS))] = sha256_file(f)
        logger.info(f"copied {dst} ({len(files)} files)")
    return hashes


def dep_extract() -> dict:
    """All ten datasets of art_j3Rm_lr2nzR6: counts, the single-token neutral-noun bank and T10 reference programs."""
    full = DEP_DIR / "full_data_out.json"
    data = json.loads(full.read_text())
    out: dict = {"source": "art_j3Rm_lr2nzR6 full_data_out.json", "sha256": sha256_file(full), "datasets": {}}
    nouns, t10_refs = [], []
    t10_slugs = {"number-of-provinces", "number-of-connected-components-in-an-undirected-graph",
                 "find-if-path-exists-in-graph"}
    for ds in data["datasets"]:
        name = ds["dataset"]
        exs = ds["examples"]
        n_t10 = 0
        for ex in exs:
            text = (ex.get("input", "") + " " + ex.get("output", "")).lower()
            bench_task = str(ex.get("metadata_bench_task", ""))
            is_t10 = bench_task.startswith("T10") or str(ex.get("metadata_task_slug", "")) in t10_slugs or \
                str(ex.get("metadata_slug", "")) in t10_slugs or ("connected component" in text and name in (
                    "thealgorithms_python", "kodcode_algorithmic", "xlcost_python"))
            if is_t10 and name != "llm_creativity" and len(ex.get("output", "")) > 40:
                n_t10 += 1
                t10_refs.append({"dataset": name, "id": ex.get("metadata_question_id") or ex.get("metadata_row_index"),
                                 "code": ex["output"][:6000]})
            if name == "concreteness_norms":
                flag = str(ex.get("metadata_noun_bank_candidate", ""))
                if flag.lower() == "true":
                    nouns.append({"word": ex.get("input", ""), "meta": {k: v for k, v in ex.items()
                                                                         if k.startswith("metadata_")}})
        out["datasets"][name] = {"n_examples": len(exs), "n_t10_related": n_t10}
    out["neutral_noun_candidates"] = nouns
    out["t10_reference_programs"] = t10_refs
    logger.info(f"dep: {len(nouns)} flagged nouns, {len(t10_refs)} T10-related programs; "
                f"{ {k: v['n_examples'] for k, v in out['datasets'].items()} }")
    return out


def main() -> None:
    setup_logging("s0_inputs")
    hashes = copy_all()
    write_json(INPUTS / "input_hashes.json", hashes)
    try:
        dep = dep_extract()
        write_json(INPUTS / "dep_extract.json", dep)
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
        logger.error(f"dependency extraction failed: {e}")
        raise
    logger.info(f"S0 done: {len(hashes)} files hashed")


if __name__ == "__main__":
    main()
