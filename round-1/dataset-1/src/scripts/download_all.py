#!/usr/bin/env python3
"""Registry + (re)download of the 15 kept data sources, and the data_sources.json catalogue.

    uv run --python .venv/bin/python scripts/download_all.py                 # download everything into temp/datasets/
    .venv/bin/python scripts/download_all.py --only mercury concreteness     # a subset
    .venv/bin/python scripts/download_all.py --catalog-only                  # rewrite data_sources.json from files on disk

Hugging Face datasets are fetched at the commit SHA recorded below and written as
full_/mini_/preview_ JSON (same names as the aii-hf-datasets download script); GitHub repositories are
cloned at the recorded commit. Files over 90 MB are split with scripts/split_json.py (aii-file-size-limit).
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from split_json import split_file, truncate  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(ROOT / "logs" / "download" / "download_all.log", rotation="30 MB", level="DEBUG")

DATA = ROOT / "temp" / "datasets"
MAX_MB = 90.0

# key -> source description. role = what the next build step uses it for (artifact plan step numbers).
SOURCES: dict[str, dict] = {
    "leetcodedataset": {
        "kind": "hf", "repo": "newfacade/LeetCodeDataset", "revision": "215604aeed660029df7de2fea5a4d7b6ed476a08",
        "configs": {None: None}, "licence": "apache-2.0", "redistribute": "converted I/O pairs only, with attribution",
        "paper": "Xia et al. 2025, arXiv:2504.14655",
        "role": "Seed hidden tests (STEP 4b-i): input_output pairs for LeetCode 743, 215, 28, 1, 287, 587, 509, 547, 300, 56, 347, 435, 684, 210, 34 (T02-T14 except T09/T12, R1-R3, R6); reference completions; topic tags.",
        "caveats": "No design-class problems: 146 (LRU, T09) and 295 (MedianFinder, T12) are absent, so their tests must be generated. Problem text is memorised by LLMs: reuse I/O only, never the wording.",
    },
    "mercury": {
        "kind": "hf", "repo": "Elfsong/Mercury", "revision": "98946f8e1ab656b7acdbd308d0de1eade9b2aefe",
        "configs": {None: None}, "licence": "cc-by-nc-4.0", "redistribute": "no (non-commercial); evaluation use",
        "paper": "Du et al. 2024, arXiv:2402.07844",
        "role": "Human-written LeetCode solutions (8-30 per target incl. 146 LRU and 295 median finder) as an external, mode-diverse program pool for the AST/tracer labellers and judge sanity checks (STEP 5); LeetCode metadata.",
        "caveats": "generator_code is the string 'None' for the bench targets (train split); a few solutions are LeetCode I/O hacks (sys.stdout/stdin) and must be filtered.",
    },
    "llm_creativity": {
        "kind": "git", "url": "https://github.com/DrejcPesjak/llm-creativity", "revision": "3fed759614914bfc35666c35fcb1ccb82a850d5c",
        "licence": "none stated", "redistribute": "NO - evaluation only; never copy programs into published files",
        "paper": "GitHub repository (the run's inspiration)",
        "role": "T02 continuity: find_path(graph, start, goal) contract (lc/tasks.py), 225 claude-sonnet-5 programs (runs/T1/<strategy>/<i>/solution.py) with authoritative blind-judge labels (analysis/judge/T1/*.json) for the external labeller check (STEP 5); AST rules lc/rules.py as a reference pattern.",
        "caveats": "negative_memory_v1_confounded (25 programs) is a confounded run the README excludes from the headline 200.",
    },
    "thealgorithms_python": {
        "kind": "git", "url": "https://github.com/TheAlgorithms/Python", "revision": "25c712f2692449e91a57748d328ef34fccf25654",
        "licence": "MIT", "redistribute": "yes with MIT notice", "paper": "GitHub repository (~225k stars)",
        "role": "Named textbook implementations for almost every catalogue mode (Dijkstra x4, Bellman-Ford, Floyd-Warshall x2, A*, bidirectional Dijkstra/BFS, 0-1 BFS, quickselect, median-of-medians, KMP, Rabin-Karp, Boyer-Moore(-Horspool), Z, naive search, Graham scan, Jarvis march, Fibonacci variants incl. fast doubling and matrix power, LIS O(n^2)/O(n log n), LRU, DSU, topological sort, binary/exponential search): starting points for references (STEP 4a) and an out-of-distribution test set for AST rules.",
        "caveats": "Educational code: verify on hidden tests before use. Master targets Python 3.14: divide_and_conquer/convex_hull.py does not parse under 3.12.",
    },
    "clrs_text_test": {
        "kind": "hf", "repo": "smcleish/CLRS-Text-test", "revision": "83205bf85c630749da410e784226364cf4a2d7eb",
        "configs": {None: "test_1"}, "licence": "apache-2.0", "redistribute": "yes", "paper": "Markeeva et al. 2024, arXiv:2406.04229",
        "role": "Ground-truth execution traces of 30 CLRS algorithms (bfs, dfs, dijkstra, bellman_ford, floyd_warshall, dag_shortest_paths, quickselect, naive_string_matcher, kmp_matcher, graham_scan, jarvis_march, activity_selector, topological_sort, mst_kruskal, binary_search, ...) to unit-test the tracer's access-order features (STEP 5).",
        "caveats": "Text traces on small inputs (length 4-64); split test_1 only.",
    },
    "xlcost_python_program_level": {
        "kind": "xlcost", "repo": "codeparrot/xlcost-text-to-code", "revision": "60c5c133f043a5cffe162f9de1c62b9d88f309cf",
        "licence": "cc-by-sa-4.0", "redistribute": "yes, share-alike", "paper": "Zhu et al. 2022, arXiv:2206.08474",
        "role": "GeeksforGeeks Python programs whose titles name the algorithm (69 Fibonacci incl. fast doubling, 12 LIS incl. N log N, quickselect, Boyer-Moore, Rabin-Karp, Bellman-Ford, Floyd-Warshall, DSU, ...): extra out-of-distribution AST-rule checks and alias mining.",
        "caveats": "Code is tokenised (NEW_LINE/INDENT/DEDENT); detokenise first. Repo ships a loader script, so data comes from refs/convert/parquet.",
    },
    "kodcode_light_rl_10k": {
        "kind": "hf", "repo": "KodCode/KodCode-Light-RL-10K", "revision": "dcf78a8bbba9a613b596ce993c4921a38687dfcc",
        "configs": {None: "train"}, "licence": "cc-by-nc-4.0", "redistribute": "no (non-commercial); evaluation use",
        "paper": "KodCode, arXiv:2503.02951 (Findings of ACL 2025)",
        "role": "LLM-written (GPT-4o), test-verified solutions to algorithm-named questions (Algorithm/Data_Structure/Leetcode subsets: 40 Dijkstra, 42 binary search, 23 Fibonacci, 17 BFS, 11 DFS, 9 Rabin-Karp, 8 topological ...): AST-rule checks on LLM-style code.",
        "caveats": "Synthetic; labels come from question text, so treat as forced-implementation analogues, not ground truth.",
    },
    "rosetta_code": {
        "kind": "hf", "repo": "christopher/rosetta-code", "revision": "11d8b38cbd90b0ae5bde304ae2d4ba5ace10af05",
        "configs": {None: "train"}, "licence": "gfdl", "redistribute": "GFDL copyleft; do not copy into the bench",
        "paper": "Rosetta Code (rosettacode.org) crawl",
        "role": "Independent Python implementations of named tasks (Dijkstra's algorithm, Floyd-Warshall, Quickselect, Longest increasing subsequence, Topological sort, Binary search, Fibonacci sequence): alias lists and judge/AST sanity items.",
        "caveats": "One Python variant per task; 'Convex hull' uses shapely (third-party) and Fibonacci is the analytic variant only.",
    },
    "enamel": {
        "kind": "hf", "repo": "q-rz/enamel", "revision": "a5bd5ee4ef84f05d9bc886ca47c507a971088554",
        "configs": {None: "ENAMEL_HumanEval"}, "licence": "apache-2.0", "redistribute": "yes", "paper": "Qiu et al., ICLR 2025, arXiv:2406.06647",
        "role": "Expert efficient references + size-levelled input generators that separate sub-optimal from optimal algorithms (incl. HumanEval/55 fib, levels 10/30/9000/10000): template for the time-limit rule and stress-size calibration (STEP 4c).",
        "caveats": "HumanEval problems, not the bench tasks.",
    },
    "enamel_github": {
        "kind": "git", "url": "https://github.com/q-rz/enamel", "revision": "b97da79c779b98eaa8b2a1b17a13d2eb0b6d16a5",
        "licence": "apache-2.0", "redistribute": "yes", "paper": "Qiu et al., ICLR 2025",
        "role": "Companion to 'enamel': expert and canonical solution samples (samples/*.json) and the eff@k evaluator.",
        "caveats": "Counted with 'enamel' as one source.",
    },
    "humanevalplus": {
        "kind": "hf", "repo": "evalplus/humanevalplus", "revision": "d32357cf319e50e9c8d8dab5ea876c72b0fd321b",
        "configs": {None: "test"}, "licence": "apache-2.0", "redistribute": "yes", "paper": "Liu et al., NeurIPS 2023, arXiv:2305.01210",
        "role": "Harness validation set: 164 canonical solutions with ~80x augmented tests must all pass through bench/harness/run_tests.py; Fibonacci-family tasks (HumanEval/39, 46, 55, 63, 130).",
        "caveats": "Not algorithm-choice tasks.",
    },
    "neocoder": {
        "kind": "git", "url": "https://github.com/JHU-CLSP/NeoCoder", "revision": "23cd8e64dc2129e5c4fae4bcb5dff8cec41f9d4f",
        "licence": "Apache-2.0", "redistribute": "yes", "paper": "Lu et al., NAACL 2025, arXiv:2407.09007",
        "role": "Closest prior art for prohibition prompts (denial prompting): 199 Codeforces problems with progressive technique bans (for loop, if statement, while loop, recursion, hashmap, sorting, ...), human solutions with technique annotations, and annotated test cases.",
        "caveats": "Bans are syntactic techniques, not algorithm modes; stdin programs.",
    },
    "creativityprism": {
        "kind": "hf", "repo": "joeyhou/creativityprism_v1", "revision": "6a820d47ec0454a939f4681f0c4d3508e5008bf8",
        "configs": {"neocoder": None, "aut": None, "ttct": None, "creative_short": None}, "licence": "other (per-task upstream licences)",
        "redistribute": "per task; do not redistribute", "paper": "Hou et al. 2025, arXiv:2510.20091",
        "role": "Cross-domain creativity inputs (AUT alternative uses, TTCT, short stories) for testing whether seeding/temperature effects found on code transfer to divergent-thinking tasks; NeoCoder copy.",
        "caveats": "Peripheral to the coding bench; licence varies per task.",
    },
    "novelty_bench": {
        "kind": "hf", "repo": "yimingzhang/novelty-bench", "revision": "8d78adfc3896716724c6d8a8ad202bc77b8e3dff",
        "configs": {None: None}, "licence": "not stated on the card", "redistribute": "no", "paper": "Zhang et al. 2025, arXiv:2504.05228",
        "role": "100 curated + 1,000 WildChat prompts that admit many distinct answers: non-code probe for the original request's temperature/top-k 'ideas vs phrasings' and context-seeding questions.",
        "caveats": "Only the prompt files are downloaded (the 1.9 GB repo also holds evaluation results).",
    },
    "concreteness_ratings": {
        "kind": "hf", "repo": "StephanAkkerman/concreteness-ratings", "revision": "10f460a4d535800d89c579db7cd2664dbaf6b1d6",
        "configs": {None: "train"}, "licence": "mit (mirror tag; original OSF norms licence not stated)", "redistribute": "word lists derived from it",
        "paper": "Brysbaert, Warriner & Kuperman 2014, Behavior Research Methods 46:904-911",
        "role": "Neutral-twin noun bank and context-seed words (STEP 2 name-only/neutral twins; original request item 2): 39,954 lemmas with concreteness, SUBTLEX frequency and dominant POS; 996 concrete frequent nouns are single Qwen3 tokens.",
        "caveats": "Filter offensive/body words before use (e.g. 'breasts' is in the concrete-frequent set).",
    },
    "open_english_wordnet_2023": {
        "kind": "hf", "repo": "jon-tow/open-english-wordnet-synset-2023", "revision": "a8e719bd0bb9c28f5718f98a536b9e412f2d07ae",
        "configs": {None: "train"}, "licence": "cc-by-4.0", "redistribute": "yes with attribution", "paper": "McCrae et al., Open English WordNet",
        "role": "Noun lexicographer files (noun.artifact/animal/plant/food vs noun.cognition/act/communication) to keep algorithm-like abstract nouns out of the neutral bank.",
        "caveats": "Synset-level rows; members are 'oewn-<lemma>-n' ids.",
    },
}


def rel(p: Path) -> str:
    """Path relative to the repository root for logs (never an absolute server path)."""
    p = p.resolve()
    return p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else p.name


def _stem(repo: str, config: str | None, split: str) -> str:
    return f"{repo.replace('/', '_')}_{config or 'default'}_{split}"


def download_hf(key: str, src: dict) -> None:
    from datasets import load_dataset  # heavy import, only when downloading

    for config, split in src["configs"].items():
        out_dir = DATA / (key if config is None or len(src["configs"]) == 1 else f"{key}_{config}")
        out_dir.mkdir(parents=True, exist_ok=True)
        ds = load_dataset(src["repo"], config, split=split, revision=src["revision"])
        splits = {split: ds} if split else dict(ds)
        for sp, d in splits.items():
            rows = [dict(r) for r in d]
            stem = _stem(src["repo"], config, sp)
            full = out_dir / f"full_{stem}.json"
            full.write_text(json.dumps(rows, ensure_ascii=False, default=str))
            (out_dir / f"mini_{stem}.json").write_text(json.dumps(rows[:3], ensure_ascii=False, indent=1, default=str))
            (out_dir / f"preview_{stem}.json").write_text(json.dumps(truncate(rows[:3]), ensure_ascii=False, indent=1, default=str))
            logger.info(f"{src['repo']} {config}/{sp}: {len(rows)} rows -> {rel(full)}")
            if full.stat().st_size > MAX_MB * 1e6:
                split_file(full, int(MAX_MB * 1e6))


def download_git(key: str, src: dict) -> None:
    dest = DATA / "github" / src["url"].rstrip("/").split("github.com/")[1].replace("/", "_")
    if dest.exists():
        logger.info(f"{rel(dest)} exists; checking out {src['revision'][:10]}")
    else:
        dest.mkdir(parents=True)
        subprocess.run(["git", "-C", str(dest), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(dest), "remote", "add", "origin", src["url"]], check=True)
    subprocess.run(["git", "-C", str(dest), "fetch", "-q", "--depth", "1", "origin", src["revision"]], check=True)
    subprocess.run(["git", "-C", str(dest), "checkout", "-q", "FETCH_HEAD"], check=True)
    logger.info(f"{src['url']} @ {src['revision'][:10]} -> {rel(dest)}")


def download_xlcost(key: str, src: dict) -> None:
    subprocess.run([sys.executable, str(ROOT / "scripts" / "download_xlcost.py"), "--out-dir", str(DATA / key)], cwd=ROOT, check=True)


def catalogue() -> dict:
    """Describe every source as it exists on disk now (paths relative to the repo root)."""
    sanity_path = ROOT / "logs" / "sanity" / "sanity_report.json"
    sanity = json.loads(sanity_path.read_text()) if sanity_path.exists() else {}
    out = {}
    for key, src in SOURCES.items():
        if src["kind"] == "git":
            local = DATA / "github" / src["url"].rstrip("/").split("github.com/")[1].replace("/", "_")
            files = [str(local.relative_to(ROOT))] if local.exists() else []
            rows = None
        else:
            dirs = sorted(p for p in DATA.glob(f"{key}*") if p.is_dir())
            files, rows = [], 0
            for d in dirs:
                for f in sorted(d.rglob("full_*.json")):
                    if f.is_file():
                        files.append(str(f.relative_to(ROOT)))
                        rows += len(json.loads(f.read_text()))
        entry = {k: v for k, v in src.items() if k != "configs"}
        entry |= {"local_files": files, "n_rows": rows}
        out[key] = entry
    return {"generated_by": "scripts/download_all.py --catalog-only", "n_sources": len(out),
            "sanity_report": str(sanity_path.relative_to(ROOT)) if sanity else None, "sources": out}


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None, help="subset of source keys")
    ap.add_argument("--catalog-only", action="store_true")
    ap.add_argument("--data-dir", type=Path, default=None, help="download somewhere other than temp/datasets (no catalogue)")
    args = ap.parse_args()
    global DATA
    if args.data_dir is not None:
        DATA = args.data_dir.resolve()
    if not args.catalog_only:
        for key in args.only or SOURCES:
            src = SOURCES[key]
            try:
                {"hf": download_hf, "git": download_git, "xlcost": download_xlcost}[src["kind"]](key, src)
            except (OSError, subprocess.CalledProcessError, ValueError) as e:
                logger.error(f"{key} failed: {type(e).__name__}: {e}")
                raise
    if args.data_dir is None:
        (ROOT / "data_sources.json").write_text(json.dumps(catalogue(), indent=1))
        logger.info("wrote data_sources.json")


if __name__ == "__main__":
    main()
