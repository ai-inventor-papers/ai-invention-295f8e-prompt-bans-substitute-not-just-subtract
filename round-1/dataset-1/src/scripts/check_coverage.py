#!/usr/bin/env python3
"""Content screen: which bench-target LeetCode problems / named algorithms each candidate actually contains."""
import json
import re
import sys
from pathlib import Path

from datasets import load_dataset
from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
ROOT = Path(__file__).resolve().parent.parent
logger.add(ROOT / "logs" / "check_coverage.log", rotation="30 MB", level="DEBUG")

# Bench tasks -> LeetCode question ids named in the artifact plan (T02..T14, R1/R2/R3/R6).
TARGET_QIDS = {743: "T02 network-delay (Dijkstra)", 215: "T03 kth-largest", 28: "T04 strStr", 1: "T05 two-sum",
               287: "T06 find-duplicate", 587: "T07 erect-the-fence", 509: "T08 fibonacci (not named in plan)",
               146: "T09 LRU cache", 547: "T10 provinces", 323: "T10 alt: connected components (premium)",
               300: "T11 LIS", 295: "T12 median finder", 56: "T13 merge intervals", 347: "T14 top-k frequent",
               435: "R1 non-overlapping intervals", 684: "R2 redundant connection", 210: "R3 course schedule II",
               34: "R6 search range", 1971: "alt: find-if-path-exists", 1631: "alt: min-effort path",
               1514: "alt: max-probability path", 1091: "T01 related: shortest path binary matrix"}
OUT = ROOT / "logs" / "coverage"
OUT.mkdir(parents=True, exist_ok=True)


def screen_leetcode() -> dict:
    res = {}
    # newfacade/LeetCodeDataset: question_id + input_output
    ds = load_dataset("newfacade/LeetCodeDataset", split="train")
    ds_test = load_dataset("newfacade/LeetCodeDataset", split="test")
    rows = {int(r["question_id"]): r for r in list(ds) + list(ds_test)}
    logger.info(f"LeetCodeDataset rows: train={len(ds)} test={len(ds_test)} cols={ds.column_names}")
    res["newfacade/LeetCodeDataset"] = {
        q: {"present": q in rows, "n_io": len(rows[q]["input_output"]) if q in rows else 0,
            "entry_point": rows[q]["entry_point"] if q in rows else None,
            "tags": rows[q]["tags"] if q in rows else None} for q in TARGET_QIDS}
    # Elfsong/Mercury: id = question id; has generator_code + solutions
    m = list(load_dataset("Elfsong/Mercury", split="train")) + list(load_dataset("Elfsong/Mercury", split="eval"))
    mrows = {int(r["id"]): r for r in m}

    def n_cases(raw: object) -> int:
        """Mercury stores test_cases as a JSON string, or the literal string 'None' when absent."""
        if not isinstance(raw, str) or raw in ("", "None"):
            return 0
        try:
            return len(json.loads(raw))
        except json.JSONDecodeError:
            logger.warning(f"Mercury test_cases not JSON: {raw[:80]!r}")
            return -1

    res["Elfsong/Mercury"] = {q: {"present": q in mrows,
                                  "n_solutions": len(mrows[q]["solutions"]) if q in mrows else 0,
                                  "has_generator": bool(mrows[q]["generator_code"]) if q in mrows else False,
                                  "n_test_cases": n_cases(mrows[q].get("test_cases")) if q in mrows else 0}
                              for q in TARGET_QIDS}
    # DONG19/EffiBench: problem_idx = question id
    e = load_dataset("DONG19/EffiBench", split="train")
    erows = {int(r["problem_idx"]): r for r in e}
    res["DONG19/EffiBench"] = {q: {"present": q in erows, "has_generator": bool(erows[q]["test_case_generator"]) if q in erows else False}
                               for q in TARGET_QIDS}
    # greengerong/leetcode: id
    g = load_dataset("greengerong/leetcode", split="train")
    grows = {int(r["id"]): r for r in g}
    res["greengerong/leetcode"] = {q: {"present": q in grows} for q in TARGET_QIDS}
    logger.info(f"greengerong python sample (q=743): {grows.get(743, {}).get('python', '')[:600]!r}")
    # kaysss/leetcode-problem-detailed
    k = load_dataset("kaysss/leetcode-problem-detailed", split="train")
    krows = {}
    for r in k:
        try:
            krows[int(r["questionFrontendId"])] = r
        except (TypeError, ValueError):
            continue
    res["kaysss/leetcode-problem-detailed"] = {q: {"present": q in krows} for q in TARGET_QIDS}
    logger.info(f"kaysss cols: {k.column_names}")
    return res


def screen_algorithms() -> dict:
    res = {}
    pats = {"dijkstra": r"dijkstra", "bellman": r"bellman", "floyd": r"floyd|warshall", "a_star": r"a\*|a-star|astar",
            "bfs": r"breadth[- ]first|\bbfs\b", "dfs": r"depth[- ]first|\bdfs\b", "quickselect": r"quickselect|quick select",
            "kmp": r"knuth|kmp", "rabin_karp": r"rabin|karp", "boyer_moore": r"boyer", "z_algo": r"z[- ]algorithm|z[- ]function",
            "convex_hull": r"convex hull|graham|jarvis|monotone chain|gift wrap", "fibonacci": r"fibonacci",
            "lis": r"longest increasing subsequence", "lru": r"\blru\b|least recently used", "union_find": r"union[- ]find|disjoint[- ]set",
            "topological": r"topolog", "binary_search": r"binary search", "median_stream": r"running median|median .*stream|stream.*median",
            "interval": r"merge (overlapping )?intervals|interval", "top_k": r"top[- ]k|k most frequent", "two_sum": r"two sum|pair with given sum",
            "connected_components": r"connected component", "kruskal": r"kruskal", "heap": r"\bheap\b"}
    # Rosetta Code (Python only)
    rc = load_dataset("christopher/rosetta-code", split="train")
    py = rc.filter(lambda r: r["language_name"] in ("Python",))
    names = sorted(set(py["task_name"]))
    logger.info(f"rosetta-code: {len(rc)} rows, Python rows={len(py)}, Python tasks={len(names)}")
    res["christopher/rosetta-code"] = {k: [n for n in names if re.search(p, n, re.I)][:12] for k, p in pats.items()}
    # XLCoST Python program-level
    # The repo ships a loader script (unsupported by datasets>=4), so read the Hub's auto-converted parquet branch.
    xl = load_dataset("parquet", split="train", data_files="hf://datasets/codeparrot/xlcost-text-to-code@refs%2Fconvert%2Fparquet/Python-program-level/train/*.parquet")
    titles = [t.split("|")[0].strip() for t in xl["text"]]
    logger.info(f"xlcost python program-level: {len(xl)} rows")
    res["codeparrot/xlcost-text-to-code"] = {k: [t for t in titles if re.search(p, t, re.I)][:8] + [f"n={sum(bool(re.search(p, t, re.I)) for t in titles)}"] for k, p in pats.items()}
    # CLRS-Text test_1: algo names
    cl = load_dataset("smcleish/CLRS-Text-test", split="test_1")
    from collections import Counter
    res["smcleish/CLRS-Text-test"] = dict(Counter(cl["algo_name"]))
    # KodCode light: subsets + algorithm keyword hits
    kc = load_dataset("KodCode/KodCode-Light-RL-10K", split="train")
    res["KodCode/KodCode-Light-RL-10K"] = {"subsets": dict(Counter(kc["subset"])),
                                           "kw_hits": {k: sum(bool(re.search(p, q, re.I)) for q in kc["question"]) for k, p in pats.items()}}
    # codecomplex: languages / labels
    cc = load_dataset("codeparrot/codecomplex", split="train")
    res["codeparrot/codecomplex"] = {"n": len(cc), "labels": dict(Counter(cc["complexity"])), "from": dict(Counter(cc["from"]))}
    # CreativityPrism neocoder config
    nc = load_dataset("joeyhou/creativityprism_v1", "neocoder", split="train")
    res["joeyhou/creativityprism_v1:neocoder"] = {"n": len(nc), "columns": nc.column_names,
                                                  "example_row": {c: str(nc[0][c])[:700] for c in nc.column_names}}
    return res


@logger.catch(reraise=True)
def main() -> None:
    lc = screen_leetcode()
    (OUT / "leetcode_coverage.json").write_text(json.dumps(lc, indent=1, default=str))
    for ds, cov in lc.items():
        hits = [f"{q}{'*' if v['present'] else '-'}" for q, v in cov.items()]
        logger.info(f"{ds}: {sum(v['present'] for v in cov.values())}/{len(cov)} present :: {' '.join(hits)}")
    al = screen_algorithms()
    (OUT / "algorithm_coverage.json").write_text(json.dumps(al, indent=1, default=str))
    logger.info("done")


if __name__ == "__main__":
    main()
