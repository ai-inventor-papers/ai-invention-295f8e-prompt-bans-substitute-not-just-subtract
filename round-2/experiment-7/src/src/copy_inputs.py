#!/usr/bin/env python3
"""Step 0.1: copy the iteration-1 inputs (read-only sources) into the workspace and record their sha256.

Sources come from paths.local.json (EXP1 = exp1 canonical suite + sampled events, EXP4 = random directions,
DS = declared dataset dependency). Nothing outside the workspace is ever written.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from loguru import logger

from config import DATA_IN, RESULTS, ROOT, SUITE, local_paths, setup_logging, sha256_file, write_json

EXP1_SUITE_FILES = [
    "common.py", "pipeline.py", "tasks/__init__.py", "tasks/harness.py", "tasks/sandbox_tests.py", "tasks/tests_gen.py",
    "tasks/t1_grid/spec.txt", "tasks/t1_grid/tests.json", "tasks/t1_grid/limits.json",
    "tasks/t2_wsp/spec.txt", "tasks/t2_wsp/tests.json", "tasks/t2_wsp/limits.json",
    "labeller/__init__.py", "labeller/tracer.py", "labeller/runtime_rules.py", "labeller/ast_rules.py",
    "labeller/judge.py", "labeller/combine.py", "labeller/extract.py", "labeller/gate.py", "labeller/gold_set.jsonl",
    "labeller/judge_cache.jsonl", "gen/__init__.py", "gen/prompts.py", "prompts/conditions.json",
]
EXP1_DATA_FILES = {
    "data/labelled.jsonl": "exp1/labelled.jsonl",
    "data/condition_summaries.json": "exp1/condition_summaries.json",
    "data/program_eval_cache.jsonl": "exp1/program_eval_cache.jsonl",
    "data/raw_succession.jsonl": "exp1/raw_succession.jsonl",
    "results/event_table.json": "exp1/event_table.json",
    "results/mention_effects.json": "exp1/mention_effects.json",
    "results/succession_state.json": "exp1/succession_state.json",
    "elicitation/qwen_freetext.jsonl": "exp1/qwen_freetext.jsonl",
    "pyproject.toml": "exp1/pyproject.toml",
}
EXP4_FILES = ["directions/rand1_T1_L18.npy", "directions/rand2_T1_L18.npy", "directions/rand1_T2_L18.npy",
              "directions/rand2_T2_L18.npy"]


def _copy(src: Path, dst: Path, manifest: dict, key: str) -> bool:
    if not src.exists():
        logger.error(f"MISSING input {key}")
        manifest[key] = {"present": False}
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    manifest[key] = {"present": True, "dst": str(dst.relative_to(ROOT)), "sha256": sha256_file(dst),
                     "bytes": dst.stat().st_size}
    return True


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("copy_inputs")
    lp = local_paths()
    exp1, exp4, ds = Path(lp["EXP1"]), Path(lp["EXP4"]), Path(lp["DS"])
    manifest: dict = {"sources": {"EXP1": "iter_1/gen_art_experiment_1", "EXP4": "iter_1/gen_art_experiment_4",
                                  "DS": "iter_1/gen_art_dataset_1 (art_j3Rm_lr2nzR6)"}, "files": {}}
    ok = True
    for rel in EXP1_SUITE_FILES:
        ok &= _copy(exp1 / rel, SUITE / rel, manifest["files"], f"EXP1/{rel}")
    for sub in ("t1_grid", "t2_wsp"):
        for p in sorted((exp1 / "tasks" / sub / "references").glob("*.py")):
            rel = f"tasks/{sub}/references/{p.name}"
            ok &= _copy(p, SUITE / rel, manifest["files"], f"EXP1/{rel}")
    for rel, dst in EXP1_DATA_FILES.items():
        ok &= _copy(exp1 / rel, DATA_IN / dst, manifest["files"], f"EXP1/{rel}")
    for rel in EXP4_FILES:
        _copy(exp4 / rel, DATA_IN / "exp4" / Path(rel).name, manifest["files"], f"EXP4/{rel}")
    # DS: only the 718 noun-bank candidates of concreteness_norms are needed (neutral twins)
    src = ds / "full_data_out.json"
    data = json.loads(src.read_text())
    cn = [d for d in data["datasets"] if d["dataset"] == "concreteness_norms"][0]["examples"]
    nouns = [{"noun": e["input"], "tokens_ws": e["metadata_qwen3_tokens_with_leading_space"],
              "subtlex_frequency": e["metadata_subtlex_frequency"], "concreteness": e["output"],
              "lexfiles": e.get("metadata_oewn_noun_lexfiles")}
             for e in cn if e.get("metadata_noun_bank_candidate") is True]
    del data
    write_json(DATA_IN / "ds" / "noun_bank.json", nouns)
    manifest["files"]["DS/full_data_out.json[concreteness_norms noun_bank_candidate]"] = {
        "present": True, "source_sha256": sha256_file(src), "n_nouns": len(nouns),
        "dst": "data_in/ds/noun_bank.json"}
    manifest["all_required_present"] = bool(ok)
    write_json(RESULTS / "inputs_manifest.json", manifest)
    n = sum(1 for v in manifest["files"].values() if v.get("present"))
    logger.info(f"copied {n} inputs; all required present={ok}; nouns={len(nouns)}")
    if not ok:
        raise SystemExit("required EXP1 inputs missing -> FALLBACK F1")


if __name__ == "__main__":
    main()
