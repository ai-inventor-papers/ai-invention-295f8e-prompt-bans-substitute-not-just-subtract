#!/usr/bin/env python3
"""Uses every dataset of the declared dependency art_j3Rm_lr2nzR6 (full_data_out.json, read-only) and fetches the
Ultra-FineWeb documents of the gate's broad reference set.

  leetcodedataset      10 non-bench problem texts -> chat prompts of the broad reference set; reference solutions of
                       the bench-mapped problems -> novelty-audit nearest-known-solution pool
  mercury              human solutions of the bench-mapped problems -> novelty pool
  llm_creativity       the source repository's T02 (weighted shortest path) label distribution -> context for T2
  thealgorithms_python mode-labelled implementations of our tasks' modes -> novelty pool
  clrs_text            10 CLRS-30 execution traces -> an extra 'algorithm trace' reference class (reported apart)
  humanevalplus        10 HumanEval+ prompts -> an extra 'code chat prompt' reference class (reported apart)
  enamel               10 expert-efficient reference bodies -> an extra 'raw code' reference class (reported apart)
  concreteness_norms   concreteness, SUBTLEX frequency and token counts of every twin noun used here
  kodcode_algorithmic  solutions naming one of our modes -> novelty pool
  xlcost_python        programs naming one of our modes -> novelty pool
Outputs: data/reference_sources.json, data/novelty_pool.jsonl, results/dependency_usage.json.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger

from cfg import (DATA_DIR, DEP_DATASET_DIR, RESULTS_DIR, TASKS, read_json, setup_logging, sha256_file, write_json,
                 write_jsonl)

# LeetCode question ids behind our tasks (dependency metadata_bench_task mapping)
QID_TASK = {"215": "T03", "1": "T05", "287": "T06", "547": "T10", "323": "T10", "28": "T04", "34": "R6", "743": "T2"}
BENCH_NAME = {"T03": "T03_kth_smallest", "T05": "T05_two_sum", "T06": "T06_find_duplicate",
              "T10": "T10_connected_components", "T04": "T04_substring_search", "R6": "R6_first_last_position",
              "T2": "T02_weighted_shortest_path", "T1": "T01_grid_path"}
GENERAL_QUESTIONS = [
    "I am planning a two-week trip through northern Italy in late autumn with my partner, who does not drive. We like "
    "small towns, regional food and museums more than nightlife. Could you suggest a route that relies on trains and "
    "buses, roughly how many nights to spend in each place, and what we should book in advance?",
    "My sourdough starter smells strongly of acetone after about eight hours and the loaves come out flat and dense. "
    "I feed it once a day with equal weights of flour and water and keep it on the kitchen counter, which is fairly "
    "warm. What is going wrong, and how should I change the feeding schedule to get a better rise?",
    "Explain, for a high-school student, why the sky looks blue during the day but red and orange at sunset. Please "
    "mention what happens to sunlight in the atmosphere, why some colours scatter more than others, and why clouds "
    "usually look white instead of blue.",
    "Write a short, friendly email to my neighbours letting them know that we are hosting a garden party next Saturday "
    "afternoon, that there may be some music until about nine in the evening, and that they are welcome to join us. "
    "Keep it warm but not too long.",
    "What were the main causes of the collapse of the Western Roman Empire? I keep reading different explanations, "
    "from economic troubles and plague to invasions and political instability, and I would like a balanced summary "
    "of how historians weigh these factors today.",
    "I have been offered two jobs: one at a large company with a higher salary and a long commute, and one at a small "
    "startup closer to home with stock options but less security. I have a young child. What questions should I ask "
    "myself and the employers before deciding between them?",
    "Can you help me understand how vaccines train the immune system? I would like to know the difference between "
    "live attenuated, inactivated and mRNA vaccines, why some need booster doses, and what herd immunity actually "
    "means in practice.",
    "Draft a polite but firm complaint to an online shop. I ordered a winter coat four weeks ago, paid for express "
    "delivery, received a confirmation that it had shipped, but it never arrived and their support chat keeps closing "
    "my tickets without an answer. I want a refund.",
    "Describe a beginner-friendly weekly exercise plan for someone in their fifties who has not exercised for years, "
    "has mild knee pain and can spend about thirty minutes a day. Include warm-up advice and how to progress safely "
    "over the first two months.",
    "Summarise the plot of a classic detective story in which a famous investigator solves a murder on a snowbound "
    "train, without revealing the final twist, and explain why the novel is still considered a masterpiece of the "
    "genre by many readers and critics.",
]


def load_dep() -> dict[str, list[dict[str, Any]]]:
    p = DEP_DATASET_DIR / "full_data_out.json"
    d = json.loads(p.read_text())
    return {ds["dataset"]: ds["examples"] for ds in d["datasets"]}, sha256_file(p)


def fetch_fineweb(n_docs: int = 20) -> list[dict[str, Any]]:
    cache = DATA_DIR / "ultrafineweb_docs.json"
    if cache.exists():
        return read_json(cache)
    from datasets import load_dataset

    docs = []
    ds = load_dataset("openbmb/Ultra-FineWeb", split="en", streaming=True)
    for i, r in enumerate(ds):
        txt = r["content"]
        if 1200 <= len(txt) <= 6000:
            docs.append({"source": "ultrafineweb", "idx": i, "text": txt})
        if len(docs) >= n_docs:
            break
    write_json(cache, docs)
    return docs


def main() -> dict[str, Any]:
    setup_logging("dep_usage")
    dep, sha = load_dep()
    use: dict[str, Any] = {"dependency": "art_j3Rm_lr2nzR6 full_data_out.json", "sha256": sha,
                           "n_examples": {k: len(v) for k, v in dep.items()}}
    # ---- reference sources
    lc = dep["leetcodedataset"]
    non_bench = sorted([e for e in lc if e.get("metadata_bench_task") in (None, "None") and len(e["input"]) > 600],
                       key=lambda e: int(e["metadata_question_id"]))
    step = max(1, len(non_bench) // 10)
    lc_prompts = [{"source": "leetcode", "qid": e["metadata_question_id"], "text": e["input"][:3000]}
                  for e in non_bench[::step][:10]]
    gen_prompts = [{"source": "general", "qid": f"g{i}", "text": q} for i, q in enumerate(GENERAL_QUESTIONS)]
    clrs = dep["clrs_text"]
    algs = sorted({e["metadata_algorithm"] for e in clrs})
    clrs_pick = []
    for a in algs[:10]:
        e = next(x for x in clrs if x["metadata_algorithm"] == a)
        clrs_pick.append({"source": "clrs_trace", "qid": a, "text": (e["input"] + "\n" + e["output"])[:3000]})
    he = [{"source": "humanevalplus", "qid": e["metadata_task_id"], "text": e["input"]} for e in dep["humanevalplus"][:10]]
    en = [{"source": "enamel", "qid": e["metadata_task_id"], "text": e["output"]} for e in dep["enamel"][10:20]]
    fw = fetch_fineweb(20)
    refsrc = {"fineweb": fw, "leetcode": lc_prompts, "general": gen_prompts, "clrs_trace": clrs_pick,
              "humanevalplus": he, "enamel": en}
    write_json(DATA_DIR / "reference_sources.json", refsrc)
    use["reference_sources"] = {k: len(v) for k, v in refsrc.items()}
    # ---- novelty pool (nearest-known-solution comparison)
    pool = []
    for e in lc:
        t = QID_TASK.get(str(e["metadata_question_id"]))
        if t:
            pool.append({"task": t, "source": "leetcodedataset", "id": e["metadata_question_id"], "code": e["output"]})
    for e in dep["mercury"]:
        t = QID_TASK.get(str(e["metadata_question_id"]))
        if t:
            pool.append({"task": t, "source": "mercury", "id": f"{e['metadata_question_id']}:{e['metadata_solution_index']}",
                         "code": e["output"]})
    for e in dep["thealgorithms_python"]:
        bt = e.get("metadata_bench_task")
        t = next((k for k, v in BENCH_NAME.items() if v == bt), None)
        if t:
            pool.append({"task": t, "source": "thealgorithms_python", "id": e.get("metadata_path"),
                         "mode": e.get("metadata_bench_mode"), "code": e["input"]})
    for name in ("kodcode_algorithmic", "xlcost_python"):
        for e in dep[name]:
            named = e.get("metadata_bench_tasks_named")
            try:
                named = json.loads(named) if isinstance(named, str) else (named or [])
            except json.JSONDecodeError:
                named = []
            for bt in named:
                t = next((k for k, v in BENCH_NAME.items() if v == bt), None)
                if t:
                    pool.append({"task": t, "source": name, "id": e.get("metadata_question_id") or e.get("metadata_row_index"),
                                 "code": e["output"]})
    write_jsonl(DATA_DIR / "novelty_pool.jsonl", pool)
    use["novelty_pool"] = dict(Counter(f"{r['task']}:{r['source']}" for r in pool))
    # ---- llm_creativity T02 distribution
    lcr = dep["llm_creativity"]
    use["llm_creativity_T02_labels"] = dict(Counter(e["output"] for e in lcr).most_common())
    use["llm_creativity_T02_by_strategy"] = {s: dict(Counter(e["output"] for e in lcr if e["metadata_strategy"] == s))
                                             for s in sorted({e["metadata_strategy"] for e in lcr})}
    # ---- concreteness norms of the twin nouns
    from cfg import BENCH, E8, PRIOR_DEFAULT, bench_dir
    nouns = set()
    for t in TASKS:
        if t in ("T1", "T2"):
            fp = read_json(E8 / "prompts" / "frozen_prompts.json")
            for w in ("W1", "W2", "W3", "W4", "W5"):
                ph = fp["tasks"][t.lower()]["templates"][w]["neutral_A"]["phrase"]
                nouns |= {x.strip() for x in ph.replace("the ", "").replace(" and ", ",").split(",") if x.strip()}
        else:
            nn = read_json(BENCH / bench_dir(t) / "neutral_nouns.json")
            nouns |= {c["word"] for c in nn[PRIOR_DEFAULT[t]]["nouns"]}
    conc = {e["input"]: e for e in dep["concreteness_norms"] if e["input"] in nouns}
    use["twin_nouns_concreteness"] = {w: {"concreteness": conc[w]["output"] if w in conc else None,
                                          "subtlex": conc[w].get("metadata_subtlex_frequency") if w in conc else None,
                                          "qwen_tokens_ws": conc[w].get("metadata_qwen3_tokens_with_leading_space") if w in conc else None,
                                          "noun_bank_candidate": conc[w].get("metadata_noun_bank_candidate") if w in conc else None}
                                      for w in sorted(nouns)}
    write_json(RESULTS_DIR / "dependency_usage.json", use)
    logger.info(f"dependency usage: {use['reference_sources']}, pool {len(pool)}")
    return use


if __name__ == "__main__":
    main()
