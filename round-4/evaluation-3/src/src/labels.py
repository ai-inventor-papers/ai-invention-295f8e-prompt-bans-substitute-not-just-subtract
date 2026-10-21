"""STEP G1: label normalisation. Frozen labels are used as recorded; only spellings are aliased.

Catalogues: bench tasks from exp11 bench/<task>/spec.json; T1 = exp9's 7-mode analysis catalogue (plus
iteration-1's dijkstra_unit, kept verbatim and flagged); T2 = dijkstra, bf_spfa, bidijkstra, floyd, dial.
"""

from __future__ import annotations

import json
from functools import lru_cache

from src.paths import p

BENCH_DIRS = {
    "T03": "T03_kth_smallest", "T04": "T04_substring_search", "T05": "T05_two_sum", "T06": "T06_find_duplicate",
    "T08": "T08_fibonacci", "T10": "T10_connected_components", "T11": "T11_longest_increasing_subsequence",
    "T13": "T13_merge_intervals", "T14": "T14_top_k_frequent", "R1": "R1_non_overlapping_intervals",
    "R2": "R2_cycle_detection", "R3": "R3_topological_order", "R6": "R6_first_last_position",
}
BENCH12 = ["T03", "T04", "T05", "T06", "T08", "T10", "T11", "T13", "T14", "R1", "R3", "R6"]
PATH_TASKS = ["T1", "T2"]
QWEN14 = BENCH12 + PATH_TASKS

T1_CATALOGUE = ["bfs", "dfs", "bibfs", "iddfs", "astar", "gbfs", "idastar", "dijkstra_unit"]
T2_CATALOGUE = ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"]

# iteration-1/2 spellings -> canonical
ALIASES = {
    "bellman_ford_spfa": "bf_spfa", "bidirectional_bfs": "bibfs", "floyd_warshall": "floyd",
    "bidirectional_dijkstra": "bidijkstra", "astar_greedy": "astar", "astar_gbfs": "astar",
}
# labels that are not an attempted program (no code / unparseable / unresolved)
NOT_ATTEMPTED = {"invalid", "no_code", "unparseable", "disputed", "unresolved", "extraction_failed", "", "none", "None"}
NON_CATALOGUE_KEEP = {"other", "builtin", "unknown", "invalid", "no_code", "unparseable", "disputed", "unresolved"}

QWEN_DEFAULT = {
    "T03": "full_sort", "T04": "naive", "T05": "hash_map", "T06": "hash_set", "T08": "iteration", "T10": "union_find",
    "T11": "quadratic_dp", "T13": "sort_sweep", "T14": "sort_by_count", "R1": "greedy_end", "R3": "kahn",
    "R6": "binary_search", "T1": "bfs", "T2": "dijkstra",
}


@lru_cache(maxsize=None)
def spec(task: str) -> dict:
    return json.loads(p("exp11", f"bench/{BENCH_DIRS[task]}/spec.json").read_text())


@lru_cache(maxsize=None)
def catalogue(task: str) -> tuple[str, ...]:
    if task == "T1":
        return tuple(T1_CATALOGUE)
    if task == "T2":
        return tuple(T2_CATALOGUE)
    return tuple(c["mode"] for c in spec(task)["catalogue"])


def catalogue_descriptions(task: str) -> dict[str, str]:
    if task in PATH_TASKS:
        return {m: m for m in catalogue(task)}
    return {c["mode"]: f"{c['display_name']}: {c['mechanism']}" for c in spec(task)["catalogue"]}


def norm_task(t: str) -> str:
    t = str(t)
    return {"t1": "T1", "t2": "T2"}.get(t, t)


def norm_label(lab: object) -> str:
    s = "no_code" if lab is None else str(lab).strip()
    return ALIASES.get(s, s)


def is_catalogue(task: str, lab: str) -> bool:
    try:
        return lab in catalogue(task)
    except KeyError:
        return False


def attempted(lab: str) -> bool:
    return lab not in NOT_ATTEMPTED


@lru_cache(maxsize=None)
def llama_defaults() -> dict[str, str]:
    out = {}
    for line in p("exp15", "results/c1_events.jsonl").read_text().splitlines():
        if line.strip():
            ev = json.loads(line)
            if ev["event_type"] == "modal":
                out[ev["task"]] = ev["banned"]
    return out


def default_of(task: str, model: str = "qwen") -> str | None:
    if "llama" in model.lower():
        return llama_defaults().get(task)
    return QWEN_DEFAULT.get(task)
