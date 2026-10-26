#!/usr/bin/env python3
"""Declared dependency art_j3Rm_lr2nzR6 (source data for the algorithm-choice bench): read all 10 datasets of
full_data_out.json and use each one.

- leetcodedataset, mercury, thealgorithms_python, kodcode_algorithmic, xlcost_python: the known human/textbook
  solution corpus for the novelty audit. exp18's 472-solution index covers T03/T04/T06/T10/T1/T2; this script adds
  the rows of every other task of this artifact (T05, T08, T11, T13, T14, R1, R2, R3, R6) -> data/known_solutions_dep.jsonl.
- llm_creativity: an external reference composition for T2 (other models' find_path programs labelled by the
  repository's blind judges): its Hill-1 rarefied at depth 25 is reported beside this artifact's T2 arms.
- concreteness_norms: provenance of every twin noun (concreteness, noun-bank flag, Qwen3 token count).
- clrs_text, humanevalplus, enamel: harness-validation sets of the bench build; summarised (counts; CLRS traces per
  catalogue mode of this artifact's tasks). They play no role in C1.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import DATA_DIR, DEP_DATASET_DIR, RESULTS_DIR, read_jsonl, setup_logging, sha256_file, utc_now, write_json, \
    write_jsonl

PREFIX = {"T01": "T1", "T02": "T2", "T03": "T03", "T04": "T04", "T05": "T05", "T06": "T06", "T08": "T08",
          "T10": "T10", "T11": "T11", "T13": "T13", "T14": "T14", "R1_": "R1", "R2_": "R2", "R3_": "R3", "R6_": "R6"}
NEW_TASKS = {"T05", "T08", "T11", "T13", "T14", "R1", "R2", "R3", "R6"}


def task_of(bt: str | None) -> str | None:
    bt = str(bt or "")
    for p, t in PREFIX.items():
        if bt.startswith(p):
            return t
    return None


def main() -> None:
    setup_logging("dep_usage")
    src = DEP_DATASET_DIR / "full_data_out.json"
    d = json.loads(src.read_text())
    summ = {"source": "art_j3Rm_lr2nzR6 full_data_out.json", "sha256": sha256_file(src), "datasets": {},
            "utc": utc_now()}
    known = []
    for ds in d["datasets"]:
        name, ex = ds["dataset"], ds["examples"]
        info: dict = {"n_examples": len(ex)}
        if name in ("leetcodedataset", "mercury"):
            c = Counter()
            for e in ex:
                t = task_of(e.get("metadata_bench_task"))
                if t in NEW_TASKS and e.get("output") and not e.get("metadata_duplicate_of"):
                    known.append({"source": name, "task": t, "mode_hint": str(e.get("metadata_slug") or
                                                                           e.get("metadata_task_slug"))[:120],
                                  "code": e["output"][:20000]})
                    c[t] += 1
            info["known_rows_added"] = dict(c)
        elif name == "thealgorithms_python":
            c = Counter()
            for e in ex:
                t = task_of(e.get("metadata_bench_task"))
                if t in NEW_TASKS and e.get("input"):
                    known.append({"source": name, "task": t, "mode_hint": f"{e.get('output')} "
                                  f"({e.get('metadata_bench_mode')})", "code": e["input"][:20000]})
                    c[t] += 1
            info["known_rows_added"] = dict(c)
        elif name in ("kodcode_algorithmic", "xlcost_python"):
            c = Counter()
            for e in ex:
                named = e.get("metadata_bench_tasks_named") or "[]"
                try:
                    lst = json.loads(named.replace("'", '"')) if isinstance(named, str) else named
                except json.JSONDecodeError:
                    lst = []
                ts = [task_of(x) for x in lst]
                ts = [x for x in ts if x in NEW_TASKS]
                if ts and e.get("output"):
                    known.append({"source": name, "task": ts[0], "mode_hint": str(e.get("metadata_named_algorithms"))
                                  [:120], "code": e["output"][:20000]})
                    c[ts[0]] += 1
            info["known_rows_added"] = dict(c)
        elif name == "llm_creativity":
            by = defaultdict(Counter)
            for e in ex:
                if str(e.get("metadata_excluded_from_headline")) == "True":
                    continue
                by[str(e.get("metadata_strategy"))][e["output"]] += 1
            allc = Counter()
            for v in by.values():
                allc.update(v)
            from analysis.stats_step0 import rarefied_hill1
            import numpy as np

            cc = [v for _, v in allc.most_common()]
            info["T2_label_composition"] = dict(allc.most_common())
            info["T2_by_strategy"] = {k: dict(v.most_common()) for k, v in by.items()}
            info["T2_hill25_all_programs"] = rarefied_hill1(cc, 25, 1000, np.random.default_rng(0)) \
                if sum(cc) >= 25 else None
            info["note"] = "labels of all programs (pass status unknown): an attempted-composition comparator only"
        elif name == "concreteness_norms":
            nouns = {"man", "house", "baby", "pants", "clock"}
            for r in read_jsonl(DATA_DIR / "prompts.jsonl"):
                if r["kind"] == "twin" and r.get("noun"):
                    nouns.add(r["noun"])
            for r in read_jsonl(Path(__file__).resolve().parents[1] / "inputs" / "exp17" / "prompts" /
                                "prompts.jsonl"):
                if r["kind"] == "twin" and r.get("noun"):
                    nouns.add(r["noun"])
            found = {}
            for e in ex:
                w = str(e.get("input", "")).strip().lower()
                if w in nouns:
                    found[w] = {"concreteness": e.get("output"), "noun_bank_candidate":
                                e.get("metadata_noun_bank_candidate"), "qwen3_tokens_with_leading_space":
                                e.get("metadata_qwen3_tokens_with_leading_space"), "subtlex_frequency":
                                e.get("metadata_subtlex_frequency")}
            info["twin_nouns"] = found
            info["twin_nouns_missing"] = sorted(nouns - set(found))
        elif name == "clrs_text":
            info["algorithms"] = dict(Counter(e.get("metadata_algorithm") for e in ex).most_common())
        elif name in ("humanevalplus", "enamel"):
            info["note"] = "harness-validation set of the bench build; not used by this artifact's analysis"
        summ["datasets"][name] = info
        logger.info(f"{name}: {info.get('n_examples')} examples")
    write_jsonl(DATA_DIR / "known_solutions_dep.jsonl", known)
    summ["known_solutions_added"] = len(known)
    summ["known_solutions_by_task"] = dict(Counter(k["task"] for k in known))
    write_json(RESULTS_DIR / "dependency_usage.json", summ)
    logger.info(f"known-solution rows added: {summ['known_solutions_by_task']}")


if __name__ == "__main__":
    main()
