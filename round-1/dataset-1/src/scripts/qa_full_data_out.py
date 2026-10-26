#!/usr/bin/env python3
"""Quality checks on full_data_out.json (or its split parts): per-dataset counts, empty fields, duplicates,
metadata-key consistency, non-finite numbers, bench coverage and label-mapping coverage.

    .venv/bin/python scripts/qa_full_data_out.py [path ...]     # default: full_data_out.json or full_data_out/full_data_out_*.json
Writes logs/qa_report.json and exits 1 if a hard error is found.
"""

import glob
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent.parent
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(ROOT / "logs" / "qa.log", rotation="30 MB", level="DEBUG")

PROMPT_ONLY = {"creativityprism", "novelty_bench"}


def nonfinite(x: object) -> bool:
    if isinstance(x, float):
        return not math.isfinite(x)
    if isinstance(x, dict):
        return any(nonfinite(v) for v in x.values())
    if isinstance(x, list):
        return any(nonfinite(v) for v in x)
    return False


def load(paths: list[Path]) -> tuple[dict, dict[str, list[dict]]]:
    meta, groups = {}, defaultdict(list)
    for p in paths:
        doc = json.loads(p.read_text(), parse_constant=lambda c: float(c))
        meta = meta or doc.get("metadata", {})
        for ds in doc["datasets"]:
            groups[ds["dataset"]].extend(ds["examples"])
    return meta, groups


@logger.catch(reraise=True)
def main() -> None:
    args = [Path(a) for a in sys.argv[1:]]
    if not args:
        single = ROOT / "full_data_out.json"
        args = [single] if single.exists() else sorted(Path(p) for p in glob.glob(str(ROOT / "full_data_out" / "full_data_out_*.json")))
    if not args:
        raise FileNotFoundError("no full_data_out.json or parts found")
    raw = b"".join(p.read_bytes() for p in args)
    hard: list[str] = []
    bare_constants: list[str] = []
    for p in args:  # parse_constant fires only for bare NaN/Infinity tokens, never for text inside strings
        json.loads(p.read_text(), parse_constant=lambda c: bare_constants.append(c) or float(c))
    if bare_constants:
        hard.append(f"file contains {len(bare_constants)} bare NaN/Infinity tokens (invalid strict JSON)")
    meta, groups = load(args)
    report = {"files": [p.resolve().relative_to(ROOT).as_posix() if p.resolve().is_relative_to(ROOT) else p.name for p in args],
              "bytes": len(raw), "datasets": {}}
    for name, exs in groups.items():
        keysets = Counter(frozenset(e) for e in exs)
        all_keys = set().union(*keysets)
        empty_in = sum(1 for e in exs if not e["input"].strip())
        empty_out = sum(1 for e in exs if not e["output"].strip())
        dup = sum(c - 1 for c in Counter(hashlib.sha1((e["input"] + "\x00" + e["output"]).encode()).hexdigest() for e in exs).values() if c > 1)
        nf = sum(1 for e in exs if nonfinite(e))
        types = {k: sorted({type(e.get(k)).__name__ for e in exs}) for k in sorted(all_keys)}
        r = {"n": len(exs), "empty_input": empty_in, "empty_output": empty_out, "duplicate_input_output_pairs": dup,
             "nonfinite_examples": nf, "n_distinct_keysets": len(keysets), "field_types": types}
        if "metadata_bench_task" in all_keys:
            r["bench_task_counts"] = dict(Counter(e.get("metadata_bench_task") for e in exs if e.get("metadata_bench_task")))
        if "metadata_named_algorithms" in all_keys:
            r["named_algorithm_counts"] = dict(Counter(m for e in exs for m in e.get("metadata_named_algorithms") or []).most_common())
        if name == "leetcodedataset":
            bench = [e for e in exs if e.get("metadata_bench_task")]
            r["bench_problems"] = {e["metadata_question_id"]: {"task": e["metadata_bench_task"], "cases": e["metadata_n_test_cases"],
                                                                "parsed": e["metadata_n_test_cases_parsed"], "ref_ok": e["metadata_reference_passes_check"],
                                                                "expected_null": e["metadata_n_expected_null"]}
                                   for e in bench}
            for q_id, v in r["bench_problems"].items():
                v["error_output_cases"] = next(e["metadata_n_test_cases_error_output"] for e in bench if e["metadata_question_id"] == q_id)
                if v["parsed"] + v["error_output_cases"] != v["cases"] or v["ref_ok"] is not True:
                    hard.append(f"leetcodedataset {q_id}: unparseable cases or failing reference ({v})")
        if name == "llm_creativity":
            r["t02_mode_counts"] = dict(Counter(e["metadata_t02_mode"] for e in exs))
            r["unmapped_labels"] = sorted({e["output"] for e in exs if e["metadata_t02_mode"] == "other" and e["metadata_t02_variant"] == e["output"]
                                           and e["output"] not in ("bfs", "bidirectional_bfs", "dfs", "beam", "random_walk_traversal", "hybrid")})
            r["missing_programs"] = sum(1 for e in exs if not e["metadata_program_exists"])
        if name == "thealgorithms_python":
            r["curated_files"] = sum(1 for e in exs if e.get("metadata_bench_mode"))
            r["curated_not_parsing"] = [e["metadata_path"] for e in exs if e.get("metadata_bench_mode") and not e["metadata_parses_py312"]]
        if name.startswith("concreteness"):
            r["noun_bank_candidates"] = sum(1 for e in exs if e["metadata_noun_bank_candidate"])
            r["token_counts_missing"] = sum(1 for e in exs if e["metadata_qwen3_tokens_with_leading_space"] is None)
        if name == "mercury":
            r["io_hacks"] = sum(1 for e in exs if e["metadata_io_hack"])
            r["not_parsing"] = sum(1 for e in exs if not e["metadata_parses_py312"])
        if empty_in or (empty_out and name not in PROMPT_ONLY):
            hard.append(f"{name}: {empty_in} empty inputs, {empty_out} empty outputs")
        if nf:
            hard.append(f"{name}: {nf} examples with NaN/Infinity")
        if len(keysets) > 1:
            hard.append(f"{name}: examples use {len(keysets)} different metadata key sets")
        report["datasets"][name] = r
        logger.info(f"{name}: n={len(exs)} empty_in={empty_in} empty_out={empty_out} dup={dup} nonfinite={nf} keysets={len(keysets)}")
    report["hard_errors"] = hard
    (ROOT / "logs" / "qa_report.json").write_text(json.dumps(report, indent=1, default=str))
    for h in hard:
        logger.error(h)
    logger.info(f"QA {'FAILED' if hard else 'PASSED'}; report in logs/qa_report.json")
    if hard:
        sys.exit(1)


if __name__ == "__main__":
    main()
