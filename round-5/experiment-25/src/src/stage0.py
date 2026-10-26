#!/usr/bin/env python3
"""Stage 0 (CPU): input manifest, dependency extraction (all 10 datasets of art_j3Rm_lr2nzR6), seed disjointness,
precision rule and hardware probe. Writes inputs/MANIFEST.sha256, inputs/dep_dataset/*.json, predictions/*.json."""

from __future__ import annotations

import ast
import glob
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger

from cfg5 import (DEP, ESC_SEEDS, INPUTS, LEETCODE_QID, MODELS, PRED, RESULTS, ROOT, USED_SEEDS, append_deviation,
                  read_json, setup_logging, sha256_file, utc_now, write_json)

# the declared dependency art_j3Rm_lr2nzR6 (published as a sibling folder of this one); ART_J3RM_DIR overrides it
DEP_SRC = Path(os.environ.get("ART_J3RM_DIR", str(ROOT.parent / "art_j3Rm_lr2nzR6")))
RUN_LOOP = ROOT.parents[2]


def manifest() -> int:
    lines = []
    for p in sorted(INPUTS.rglob("*")):
        if p.is_file() and p.name != "MANIFEST.sha256":
            lines.append(f"{sha256_file(p)}  {p.relative_to(INPUTS)}")
    (INPUTS / "MANIFEST.sha256").write_text("\n".join(lines) + "\n")
    return len(lines)


_NAMES = {"True": True, "False": False, "None": None}


def literal(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return [literal(e) for e in node.elts]
    if isinstance(node, ast.Dict):
        return {literal(k): literal(v) for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        v = literal(node.operand)
        return -v if isinstance(node.op, ast.USub) else v
    if isinstance(node, ast.Name) and node.id in _NAMES:
        return _NAMES[node.id]
    raise ValueError(f"non-literal node {type(node).__name__}")


def parse_kwargs(s: str) -> dict:
    """data.py parse_kwargs (verbatim logic)."""
    call = ast.parse(f"f({s})", mode="eval").body
    if not isinstance(call, ast.Call) or call.args:
        raise ValueError("input is not keyword-only")
    return {kw.arg: literal(kw.value) for kw in call.keywords}


def parse_value(s: str, want_str: bool = False) -> object:
    """data.py parse_value; LeetCodeDataset prints str outputs unquoted, so str-valued tasks take the raw text."""
    if want_str:
        return s
    return literal(ast.parse(s.strip(), mode="eval").body)


def extract_lc_raw() -> dict:
    """Raw LeetCodeDataset rows (input_output pairs) of the 9 unit sources -> inputs/dep_dataset/lc_raw_<qid>.json.
    Source: the dependency's pinned LeetCodeDataset snapshot (its restore.sh writes temp/datasets/leetcodedataset/).
    The extracted files ship with this repository, so this step is skipped when the snapshot is absent."""
    src = DEP_SRC / "temp" / "datasets" / "leetcodedataset"
    want = set(LEETCODE_QID.values())
    found = {}
    for f in sorted(src.glob("full_newfacade_LeetCodeDataset_default_*.json")) if src.exists() else []:
        rows = json.loads(f.read_text())
        for r in rows:
            try:
                q = int(r["question_id"])
            except (KeyError, TypeError, ValueError):
                continue
            if q in want:
                keep = {k: r[k] for k in ("question_id", "task_id", "entry_point", "starter_code", "completion",
                                          "input_output", "problem_description", "test", "prompt")}
                (DEP / f"lc_raw_{q}.json").write_text(json.dumps(keep))
                found[q] = len(r["input_output"])
    if not found:
        logger.warning(f"LeetCodeDataset snapshot not found under {src.name}; using the shipped lc_raw_*.json files")
    return found


def leetcode_cases() -> dict:
    out = {}
    for u, q in LEETCODE_QID.items():
        r = json.loads((DEP / f"lc_raw_{q}.json").read_text())
        cases = []
        for j, io in enumerate(r["input_output"]):
            cid = f"leetcodedataset:{q}:{j}"
            try:
                kw = parse_kwargs(io["input"])
                exp = parse_value(io["output"], want_str=u in ("A5", "A7"))
                cases.append({"case_id": cid, "status": "ok", "kwargs": kw, "expected": exp})
            except (SyntaxError, ValueError, TypeError) as e:
                cases.append({"case_id": cid, "status": "unparseable", "raw_input": io["input"],
                              "raw_output": io["output"], "parse_error": str(e)[:100]})
        out[u] = {"question_id": q, "slug": r["task_id"], "entry_point": r["entry_point"],
                  "starter_code": r["starter_code"], "reference": r["completion"], "cases": cases,
                  "n_ok": sum(c["status"] == "ok" for c in cases)}
    write_json(DEP / "leetcode_units.json", out)
    return {u: v["n_ok"] for u, v in out.items()}


def extract_datasets() -> dict:
    """One pass over full_data_out.json: every dataset contributes a role (README 'dependency use')."""
    d = json.loads((DEP_SRC / "full_data_out.json").read_text())
    stats = {}
    keys = {"A1": ["majority element", "majority_element", "boyer", "majority vote"],
            "A2": ["maximum subarray", "max_subarray", "kadane", "maximum sum subarray", "largest sum contiguous"],
            "A3": ["trapping rain", "trap rain", "rain water", "trapping_rain"],
            "A4": ["count primes", "sieve", "eratosthenes", "count_primes", "primes less than", "prime numbers less"],
            "A5": ["longest common prefix", "longest_common_prefix", "common prefix"],
            "A6": ["number of islands", "num_islands", "count islands", "number_of_islands", "islands"],
            "A7": ["longest palindromic substring", "longest_palindrom", "manacher", "palindromic substring"]}
    for ds in d["datasets"]:
        name, ex = ds["dataset"], ds["examples"]
        if name == "concreteness_norms":
            bank = [{"word": e["input"], "concreteness": float(e["output"]),
                     "subtlex": e.get("metadata_subtlex_frequency"),
                     "qwen_tokens_space": e.get("metadata_qwen3_tokens_with_leading_space")}
                    for e in ex if str(e.get("metadata_noun_bank_candidate")) == "True"]
            write_json(DEP / "noun_bank.json", bank)
            stats[name] = {"n": len(ex), "noun_bank_candidates": len(bank), "role": "twin nouns"}
        elif name in ("thealgorithms_python", "kodcode_algorithmic", "xlcost_python"):
            sel = {}
            for e in ex:
                txt = (e.get("input", "") + " " + str(e.get("metadata_path", "")) + " " +
                       str(e.get("metadata_title", ""))).lower()
                for u, ks in keys.items():
                    if any(k in txt for k in ks):
                        # only the MIT-licensed TheAlgorithms programs are kept as text (KodCode CC-BY-NC, XLCoST CC-BY-SA)
                        code = e["input"] if name == "thealgorithms_python" else None
                        sel.setdefault(u, []).append({"source": name, "row": e.get("metadata_row_index"),
                                                      "path": e.get("metadata_path") or e.get("metadata_title"),
                                                      "code": code, "text": e.get("input", "")[:600]})
            write_json(DEP / f"{name}_units.json", sel)
            stats[name] = {"n": len(ex), "per_unit_hits": {u: len(v) for u, v in sel.items()},
                           "role": "external labeller-validation programs (descriptive)"}
        elif name == "mercury":
            by = Counter(e.get("metadata_bench_task") for e in ex)
            write_json(DEP / "mercury_rows.json", [{"bench_task": e.get("metadata_bench_task"),
                                                    "qid": e.get("metadata_question_id"),
                                                    "runtime_ms": e.get("metadata_runtime_ms"),
                                                    "io_hack": e.get("metadata_io_hack")} for e in ex])
            stats[name] = {"n": len(ex), "per_task": dict(by), "role": "human-diversity column (existing tasks)"}
        elif name == "llm_creativity":
            modes = Counter(e.get("metadata_t02_mode") for e in ex)
            stats[name] = {"n": len(ex), "t02_modes": dict(modes),
                           "role": "external LLM-diversity reference for the weighted-shortest-path family (T2)"}
        elif name == "leetcodedataset":
            stats[name] = {"n": len(ex), "unit_rows": sorted(int(e["metadata_question_id"]) for e in ex
                                                             if int(e["metadata_question_id"]) in
                                                             set(LEETCODE_QID.values())),
                           "role": "unit sources (problem text, reference, I/O pairs via the raw snapshot)"}
        elif name == "enamel":
            stats[name] = {"n": len(ex), "role": "time-limit methodology (10x fastest reference, size levels)"}
        elif name == "humanevalplus":
            stats[name] = {"n": len(ex), "role": "sandbox-runner validation sample"}
            write_json(DEP / "humanevalplus_sample.json", [{"task_id": e.get("metadata_task_id"),
                                                            "entry_point": e.get("metadata_entry_point"),
                                                            "prompt": e["input"], "solution": e["output"],
                                                            "test": e.get("metadata_test")} for e in ex[:10]])
        elif name == "clrs_text":
            algs = Counter(e.get("metadata_algorithm") for e in ex)
            stats[name] = {"n": len(ex), "algorithms": dict(algs), "role": "descriptive (trace corpus inventory)"}
    write_json(RESULTS / "dependency_usage.json", stats)
    return stats


def seeds_check() -> dict:
    used = set(USED_SEEDS)
    for f in glob.glob(str(RUN_LOOP / "iter_3/gen_art/*/directions/rand_*.npy")) + \
            glob.glob(str(RUN_LOOP / "iter_4/gen_art/*/directions/rand_*.npy")):
        m = re.search(r"rand_(\d+)\.npy$", f)
        if m:
            used.add(int(m.group(1)))
    for f in glob.glob(str(RUN_LOOP / "iter_3/gen_art/*/src/cfg*.py")) + \
            glob.glob(str(RUN_LOOP / "iter_4/gen_art/*/src/cfg*.py")):
        txt = Path(f).read_text(errors="ignore")
        for m in re.finditer(r"SEEDS_\w+\s*=\s*(.+)", txt):
            for a, b in re.findall(r"range\((\d+),\s*(\d+)\)", m.group(1)):
                used.update(range(int(a), int(b)))
            used.update(int(x) for x in re.findall(r"\b(9\d{3,4})\b", m.group(1)))
    clash = sorted(set(ESC_SEEDS) & used)
    assert not clash, f"ESC_SEEDS clash with used seeds: {clash}"
    return {"esc_seeds": ESC_SEEDS, "n_used_seeds_checked": len(used), "clash": clash}


def precision_rule() -> dict:
    import torch

    cc = torch.cuda.get_device_capability(0)
    free, total = torch.cuda.mem_get_info(0)
    mem_gib = total / 1024 ** 3
    if cc >= (8, 9) and mem_gib < 19.5:
        eng = "fp8_w8a8"
    elif mem_gib >= 19.5:
        eng = "bf16"
    else:
        eng = "w8a16"
    rule = {"utc": utc_now(), "gpu": torch.cuda.get_device_name(0), "compute_capability": list(cc),
            "total_gib": round(mem_gib, 2), "engine": eng,
            "rule": "cc>=(8,9) and mem<19.5 GiB -> FP8 W8A8 (exp19 engine); mem>=19.5 GiB -> bf16 HF; else W8A16",
            "both_models_same_precision": True}
    write_json(PRED / "precision_rule.json", rule)
    return rule


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("stage0")
    rule = precision_rule()
    logger.info(f"precision rule: {rule}")
    write_json(PRED / "models.json", {"instruct": MODELS["instruct"], "base": MODELS["base"], "utc": utc_now()})
    logger.info(f"leetcode raw rows: {extract_lc_raw()}")
    logger.info(f"leetcode cases: {leetcode_cases()}")
    logger.info(f"datasets: {json.dumps(extract_datasets())[:1500]}")
    logger.info(f"seeds: {seeds_check()}")
    n = manifest()
    logger.info(f"manifest: {n} input files hashed")
    if not (RUN_LOOP / "round-1" / "." / "gen_art_experiment_5").exists():
        append_deviation("D-iter1-purged", "ITER1/gen_art_experiment_5 (iteration-1 base compositions of T1/T2) is "
                         "purged from the run volume; the 'half + screen' analysis cannot add T1/T2 iteration-1 base "
                         "rows and marks them PENDING_STEP1.")


if __name__ == "__main__":
    main()
