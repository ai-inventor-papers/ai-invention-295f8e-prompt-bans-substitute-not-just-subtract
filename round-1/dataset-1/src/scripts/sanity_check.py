#!/usr/bin/env python3
"""Suitability checks on the 15 kept sources (common-mistake #3: inspect + quick domain baseline).

A. LeetCodeDataset: run each bench-target problem's own reference `completion` against its `check()`
   test in an isolated `python -I` subprocess (RLIMIT_AS 2 GB, 60 s), and parse every input_output
   input into keyword arguments (needed to convert pairs to the bench signatures later).
B. Mercury: per target problem, count human solutions, flag LeetCode-runtime I/O hacks, and count
   structural markers (heapq / sort / bisect / OrderedDict / deque / recursion) to show mode diversity.
C. llm-creativity: programs per strategy, judge lineage distribution, find_path contract presence.
D. TheAlgorithms/Python: which catalogue modes have a named, parseable implementation file.
E. XLCoST: detokenise GeeksforGeeks programs whose titles name catalogue algorithms; ast.parse rate.
F. CLRS-Text: traces per algorithm. G. KodCode: subset sizes and algorithm-named questions.
H. ENAMEL / HumanEval+: Fibonacci-family tasks and generator fields.
I. NeoCoder: banned-technique vocabulary. J. NoveltyBench / CreativityPrism: prompt counts.
K. Noun bank: concrete, frequent nouns (Brysbaert) that are one Qwen3 token with a leading space,
   and OEWN noun lexicographer-file sizes.
Writes logs/sanity/sanity_report.json.
"""

import ast
import glob
import json
import re
import resource
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
ROOT = Path(__file__).resolve().parent.parent
logger.add(ROOT / "logs" / "sanity" / "sanity_check.log", rotation="30 MB", level="DEBUG")
D = ROOT / "temp" / "datasets"
RUN_DIR = ROOT / "temp" / "sanity_run"
OUT = ROOT / "logs" / "sanity"

TARGETS = {743: "T02", 215: "T03", 28: "T04", 1: "T05", 287: "T06", 587: "T07", 509: "T08", 146: "T09", 547: "T10",
           300: "T11", 295: "T12", 56: "T13", 347: "T14", 435: "R1", 684: "R2", 210: "R3", 34: "R6"}


def load_parts(pattern: str) -> list:
    rows: list = []
    for f in sorted(glob.glob(str(pattern)), key=lambda s: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]):
        rows.extend(json.loads(Path(f).read_text()))
    return rows


def _limits() -> None:
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))


def run_isolated(path: Path, timeout: float = 90.0) -> dict:
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, "-I", str(path)], cwd=RUN_DIR, capture_output=True, text=True,
                           timeout=timeout, preexec_fn=_limits)
        ok = p.returncode == 0 and p.stdout.strip().endswith("ALL_OK")
        return {"ok": ok, "rc": p.returncode, "sec": round(time.time() - t0, 2), "stderr_tail": p.stderr[-300:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "rc": "timeout", "sec": round(time.time() - t0, 2), "stderr_tail": ""}


def check_leetcodedataset() -> dict:
    rows = json.loads((D / "leetcodedataset/full_newfacade_LeetCodeDataset_default_train.json").read_text())
    rows += json.loads((D / "leetcodedataset/full_newfacade_LeetCodeDataset_default_test.json").read_text())
    by = {int(r["question_id"]): r for r in rows}
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    jobs = {}
    for q, task in TARGETS.items():
        if q not in by:
            continue
        r = by[q]
        src = f"{r['prompt']}\n{r['completion']}\n{r['test']}\ncheck({r['entry_point']})\nprint('ALL_OK')\n"
        path = RUN_DIR / f"lc_{q}.py"
        path.write_text(src)
        jobs[q] = path
    with ThreadPoolExecutor(max_workers=5) as ex:
        results = dict(zip(jobs, ex.map(run_isolated, jobs.values())))
    report = {"n_rows": len(rows), "targets": {}}
    for q, task in TARGETS.items():
        if q not in by:
            report["targets"][q] = {"task": task, "present": False}
            continue
        r = by[q]
        parsed = 0
        for io in r["input_output"]:
            try:
                kw = eval(f"dict({io['input']})", {"__builtins__": {"dict": dict, "True": True, "False": False, "None": None}})  # noqa: S307 - literal-only kwargs from the dataset
                parsed += isinstance(kw, dict)
            except (SyntaxError, NameError, TypeError, ValueError):
                pass
        report["targets"][q] = {"task": task, "present": True, "entry_point": r["entry_point"],
                                "n_input_output": len(r["input_output"]), "n_io_parsed_as_kwargs": parsed,
                                "n_check_asserts": r["test"].count("assert "), "reference_passes_check": results[q]["ok"],
                                "reference_sec": results[q]["sec"], "rc": results[q]["rc"], "tags": r["tags"]}
        logger.info(f"LC {q} ({task}): io={len(r['input_output'])} parsed={parsed} asserts={r['test'].count('assert ')} ref_ok={results[q]['ok']} {results[q]['sec']}s")
    return report


MARKERS = {"heapq": r"\bheap(push|pop|ify|replace|q)\b|nsmallest|nlargest", "sort": r"\bsort(ed)?\(|\.sort\(",
           "bisect": r"\bbisect|insort", "ordereddict": r"OrderedDict|move_to_end", "deque": r"\bdeque\(",
           "counter": r"\bCounter\(", "dict_dll": r"\.prev\b|\.next\b"}


def check_mercury() -> dict:
    rows = json.loads((D / "mercury/full_Elfsong_Mercury_default_train.json").read_text())
    rows += json.loads((D / "mercury/full_Elfsong_Mercury_default_eval.json").read_text())
    by = {int(r["id"]): r for r in rows}
    out = {"n_rows": len(rows), "n_with_generator": sum(r["generator_code"] not in (None, "", "None") for r in rows), "targets": {}}
    for q, task in TARGETS.items():
        if q not in by:
            out["targets"][q] = {"task": task, "present": False}
            continue
        sols = [s["solution"] for s in by[q]["solutions"]]
        hacks = [s for s in sols if re.search(r"sys\.stdout|open\(|stdin|__import__\(.atexit", s)]
        clean = [s for s in sols if s not in hacks]
        parse_ok = 0
        for s in clean:
            try:
                ast.parse(s)
                parse_ok += 1
            except SyntaxError:
                pass
        marks = {k: sum(bool(re.search(p, s)) for s in clean) for k, p in MARKERS.items()}
        out["targets"][q] = {"task": task, "present": True, "n_solutions": len(sols), "n_io_hacks": len(hacks),
                             "n_clean_parseable": parse_ok, "marker_counts": marks}
        logger.info(f"Mercury {q} ({task}): sols={len(sols)} hacks={len(hacks)} parse_ok={parse_ok} markers={marks}")
    return out


def check_llm_creativity() -> dict:
    base = D / "github/DrejcPesjak_llm-creativity"
    sols = sorted(base.glob("runs/T1/*/*/solution.py"))
    per_strategy = Counter(p.parts[-3] for p in sols)
    contract = sum("def find_path(" in p.read_text() for p in sols)
    judge = {}
    for f in sorted((base / "analysis/judge/T1").glob("*.json")):
        labels = json.loads(f.read_text())
        judge[f.stem] = dict(Counter(x.get("lineage_minor") for x in labels))
    commit = subprocess.run(["git", "-C", str(base), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    logger.info(f"llm-creativity: {len(sols)} solution.py, per strategy {dict(per_strategy)}, find_path in {contract}")
    return {"commit": commit, "n_solutions": len(sols), "per_strategy": dict(per_strategy), "n_with_find_path": contract,
            "judge_lineage_minor": judge}


ALGO_FILES = {
    "T02/T01 graph search": ["graphs/dijkstra.py", "graphs/dijkstra_2.py", "graphs/dijkstra_algorithm.py", "graphs/bellman_ford.py",
                             "graphs/graphs_floyd_warshall.py", "dynamic_programming/floyd_warshall.py", "graphs/a_star.py",
                             "graphs/bi_directional_dijkstra.py", "graphs/breadth_first_search_shortest_path.py",
                             "graphs/breadth_first_search_zero_one_shortest_path.py", "graphs/depth_first_search.py", "graphs/bidirectional_breadth_first_search.py"],
    "T03 k-th smallest": ["searches/quick_select.py", "searches/median_of_medians.py", "divide_and_conquer/kth_order_statistic.py",
                          "data_structures/arrays/kth_largest_element.py", "sorts/counting_sort.py", "sorts/heap_sort.py"],
    "T04 substring search": ["strings/naive_string_search.py", "strings/knuth_morris_pratt.py", "strings/rabin_karp.py",
                             "strings/boyer_moore_search.py", "strings/boyer_moore_horspool.py", "strings/z_function.py", "strings/prefix_function.py"],
    "T05 two-sum": ["maths/two_sum.py"],
    "T07 convex hull": ["geometry/graham_scan.py", "geometry/jarvis_march.py", "divide_and_conquer/convex_hull.py", "other/graham_scan.py"],
    "T08 fibonacci": ["maths/fibonacci.py", "dynamic_programming/fibonacci.py", "dynamic_programming/fast_fibonacci.py",
                      "matrix/nth_fibonacci_using_matrix_exponentiation.py"],
    "T09 LRU": ["other/lru_cache.py"],
    "T10 components": ["graphs/connected_components.py", "data_structures/disjoint_set/disjoint_set.py", "data_structures/disjoint_set/alternate_disjoint_set.py"],
    "T11 LIS": ["dynamic_programming/longest_increasing_subsequence.py", "dynamic_programming/longest_increasing_subsequence_iterative.py",
                "dynamic_programming/longest_increasing_subsequence_o_nlogn.py"],
    "T13 intervals": ["data_structures/arrays/merge_intervals.py"],
    "R1 interval scheduling": ["greedy_methods/activity_selection.py", "other/activity_selection.py", "scheduling/weighted_interval_scheduling.py"],
    "R3 topological sort": ["graphs/g_topological_sort.py"],
    "R6 search range": ["searches/binary_search.py", "searches/exponential_search.py", "searches/simple_binary_search.py"],
}


def check_thealgorithms() -> dict:
    base = D / "github/TheAlgorithms_Python"
    out = {"commit": subprocess.run(["git", "-C", str(base), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(), "modes": {}}
    for task, files in ALGO_FILES.items():
        st = {}
        for f in files:
            p = base / f
            if not p.exists():
                st[f] = "missing"
                continue
            try:
                ast.parse(p.read_text())
                st[f] = "ok"
            except SyntaxError:
                st[f] = "syntax_error"
        out["modes"][task] = st
    logger.info(f"TheAlgorithms: {sum(v == 'ok' for m in out['modes'].values() for v in m.values())} parseable named files")
    return out


def detok(code: str) -> str:
    lines, ind = [], 0
    for chunk in code.split("NEW_LINE"):
        toks = chunk.strip().split(" ")
        while toks and toks[0] in ("INDENT", "DEDENT"):
            ind += 1 if toks.pop(0) == "INDENT" else -1
        line = " ".join(toks).strip()
        if line:
            lines.append("    " * max(ind, 0) + line)
    return "\n".join(lines)


XL_PATS = {"dijkstra": r"dijkstra", "bellman_ford": r"bellman", "floyd_warshall": r"floyd", "bfs": r"\bbfs\b|breadth",
           "dfs": r"\bdfs\b|depth first", "quickselect": r"quick ?select", "kmp": r"\bkmp\b|knuth", "boyer_moore": r"boyer",
           "rabin_karp": r"rabin", "z_algorithm": r"z algorithm|z-algorithm", "fibonacci": r"fibonacci", "lis": r"longest increasing subsequence",
           "union_find": r"disjoint set|union find|union-find", "topological": r"topolog", "binary_search": r"binary search",
           "convex_hull": r"convex hull", "lru": r"\blru\b", "median_stream": r"median.*stream|running median", "merge_intervals": r"merge.*interval"}


def check_xlcost() -> dict:
    rows = json.loads((D / "xlcost_python_program_level/full_codeparrot_xlcost-text-to-code_Python-program-level_train.json").read_text())
    out = {"n_rows": len(rows), "by_algorithm": {}}
    for k, pat in XL_PATS.items():
        hits = [r for r in rows if re.search(pat, r["text"].split("|")[0], re.I)]
        ok = 0
        for r in hits:
            try:
                ast.parse(detok(r["code"]))
                ok += 1
            except SyntaxError:
                pass
        out["by_algorithm"][k] = {"n_titles": len(hits), "n_detok_parseable": ok, "examples": [r["text"].split("|")[0].strip() for r in hits[:3]]}
    logger.info(f"XLCoST: {len(rows)} rows; algorithm-titled programs: { {k: v['n_titles'] for k, v in out['by_algorithm'].items()} }")
    return out


def check_clrs() -> dict:
    rows = load_parts(D / "clrs_text_test/full_smcleish_CLRS-Text-test_default_test_1/full_*_test_1_*.json")
    c = Counter(r["algo_name"] for r in rows)
    lens = {a: sorted({r["length"] for r in rows if r["algo_name"] == a}) for a in ("bfs", "dfs", "dijkstra", "bellman_ford", "floyd_warshall", "quickselect", "kmp_matcher", "naive_string_matcher", "graham_scan", "jarvis_march")}
    logger.info(f"CLRS-Text test_1: {len(rows)} rows, {len(c)} algorithms")
    return {"n_rows": len(rows), "per_algorithm": dict(c), "lengths": lens}


def check_kodcode() -> dict:
    rows = load_parts(D / "kodcode_light_rl_10k/full_KodCode_KodCode-Light-RL-10K_default_train/full_*_train_*.json")
    algo = [r for r in rows if r["subset"] in ("Algorithm", "Data_Structure", "Leetcode")]
    hits = {k: sum(bool(re.search(p, r["question"], re.I)) for r in algo) for k, p in XL_PATS.items()}
    logger.info(f"KodCode-Light: {len(rows)} rows; algorithm/data-structure/leetcode subsets={len(algo)}; hits={hits}")
    return {"n_rows": len(rows), "subsets": dict(Counter(r["subset"] for r in rows)), "algorithm_named_questions": hits}


def check_humaneval_family() -> dict:
    he = json.loads((D / "humanevalplus/full_evalplus_humanevalplus_default_test.json").read_text())
    en = json.loads((D / "enamel/full_q-rz_enamel_default_ENAMEL_HumanEval.json").read_text())
    fib_ids = [r["task_id"] for r in he if re.search(r"fib", r["prompt"], re.I)]
    en_fib = [r for r in en if r["task_id"] in fib_ids]
    logger.info(f"HumanEval+: {len(he)} tasks, fib-family {fib_ids}; ENAMEL {len(en)} tasks, cols {list(en[0].keys())}")
    return {"humanevalplus_n": len(he), "fib_family": fib_ids, "enamel_n": len(en), "enamel_columns": list(en[0].keys()),
            "enamel_fib_input_levels": {r["task_id"]: str(r["input_levels"])[:200] for r in en_fib}}


def check_neocoder() -> dict:
    nc = json.loads((D / "github/JHU-CLSP_NeoCoder/datasets/CodeForce/NeoCoder/NeoCoder.json").read_text())
    techniques = Counter()
    for r in nc:
        steps = ast.literal_eval(r["constraints_list"]) if isinstance(r["constraints_list"], str) else r["constraints_list"]
        if steps:
            techniques.update(t for t in steps[-1] if t != "this is the og problem")
    cp = json.loads((D / "creativityprism_neocoder/full_joeyhou_creativityprism_v1_neocoder_train.json").read_text())
    logger.info(f"NeoCoder: {len(nc)} problems; top banned techniques {techniques.most_common(12)}")
    return {"n_problems": len(nc), "creativityprism_copy_n": len(cp), "top_banned_techniques": techniques.most_common(25)}


def check_prompt_sets() -> dict:
    out = {}
    for name, pat in {"novelty_curated": "novelty_bench/full_*_curated.json", "novelty_wildchat": "novelty_bench/full_*_wildchat.json",
                      "cp_aut": "creativityprism_aut/full_*.json", "cp_ttct": "creativityprism_ttct/full_*.json",
                      "cp_creative_short": "creativityprism_creative_short/full_*.json"}.items():
        rows = load_parts(D / pat)
        out[name] = {"n": len(rows), "first": str(rows[0])[:200] if rows else None}
    logger.info(f"Prompt sets: { {k: v['n'] for k, v in out.items()} }")
    return out


def check_noun_bank() -> dict:
    from huggingface_hub import hf_hub_download  # local imports: only this check needs them
    from tokenizers import Tokenizer

    conc = json.loads((D / "concreteness_ratings/full_StephanAkkerman_concreteness-ratings_default_train.json").read_text())
    tok = Tokenizer.from_file(hf_hub_download("Qwen/Qwen3-8B", "tokenizer.json", revision="b968826d9c46dd6066d109eabc6255188de91218"))  # via the HF cache (HF_HOME)
    nouns = [r for r in conc if r["Dom_Pos"] == "Noun" and r["Bigram"] == 0 and isinstance(r["SUBTLEX"], (int, float))]
    concrete = [r for r in nouns if r["Conc.M"] >= 4.5 and r["SUBTLEX"] >= 200]
    one_tok = [r["Word"] for r in concrete if tok and len(tok.encode(" " + r["Word"], add_special_tokens=False).ids) == 1]
    seeds = {w: len(tok.encode(" " + w, add_special_tokens=False).ids) if tok else None for w in ("horse", "chair", "roof", "love", "Dijkstra", "SPFA", "Floyd-Warshall")}
    wn = json.loads((D / "open_english_wordnet_2023/full_jon-tow_open-english-wordnet-synset-2023_default_train.json").read_text())
    lex = Counter(r["@lexfile"] for r in wn if r["@partOfSpeech"] == "n")
    logger.info(f"Noun bank: {len(nouns)} nouns, {len(concrete)} concrete+frequent, {len(one_tok)} single Qwen3 tokens; seeds {seeds}")
    return {"n_nouns": len(nouns), "n_concrete_frequent": len(concrete), "n_single_qwen3_token": len(one_tok),
            "examples": one_tok[:40], "token_lengths": seeds, "oewn_noun_lexfiles": dict(lex.most_common())}


@logger.catch(reraise=True)
def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report = {}
    for name, fn in [("leetcodedataset", check_leetcodedataset), ("mercury", check_mercury), ("llm_creativity", check_llm_creativity),
                     ("thealgorithms", check_thealgorithms), ("xlcost", check_xlcost), ("clrs_text", check_clrs),
                     ("kodcode", check_kodcode), ("humaneval_enamel", check_humaneval_family), ("neocoder", check_neocoder),
                     ("prompt_sets", check_prompt_sets), ("noun_bank", check_noun_bank)]:
        try:
            report[name] = fn()
        except (OSError, KeyError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"{name} check failed: {type(e).__name__}: {e}")
            report[name] = {"error": f"{type(e).__name__}: {e}"}
    (OUT / "sanity_report.json").write_text(json.dumps(report, indent=1, default=str))
    logger.info(f"wrote {(OUT / 'sanity_report.json').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
