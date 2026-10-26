#!/usr/bin/env python3
"""Stage 2 (CPU): probe grids, expansion tracer on the T1 references (G-tracer), behavioural RDM, lexical measures,
descriptions v0, M-lex prompts with token-length-matched neutral twins, M-code contexts; then COMMIT #1a."""

from __future__ import annotations

import itertools
import random
import re
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

import expansion
import prompts_tp
from common import (ALIAS_TABLE, CANON_ORDER, alias_regex, cap_first, commit, deviation, join_names_or, read_json,
                    sha256_file, utc_now, write_json)
from tpg import B5, DATA, M32, NB5, PRED, RESULTS, ROOT, SEED, UDIJ

REF_DIR = ROOT / "vendor" / "exp9" / "tasks" / "t1_grid" / "references"


# ---------------------------------------------------------------------------------------------- 2a probe grids
def _open(rng: random.Random, n: int) -> list[str]:
    g = [["." if rng.random() > 0.12 else "#" for _ in range(n)] for _ in range(n)]
    return ["".join(r) for r in g]


def _serpentine(rng: random.Random, h: int, w: int) -> list[str]:
    g = [["."] * w for _ in range(h)]
    left = rng.random() < 0.5
    for r in range(1, h - 1, 2):
        for c in range(w):
            g[r][c] = "#"
        g[r][0 if left else w - 1] = "."
        left = not left
    return ["".join(r) for r in g]


def _maze(rng: random.Random, ch: int, cw: int, loops: float = 0.06) -> list[str]:
    H, W = 2 * ch + 1, 2 * cw + 1
    g = [["#"] * W for _ in range(H)]
    stack = [(0, 0)]
    seen = {(0, 0)}
    g[1][1] = "."
    while stack:
        r, c = stack[-1]
        nb = [(r + dr, c + dc) for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))
              if 0 <= r + dr < ch and 0 <= c + dc < cw and (r + dr, c + dc) not in seen]
        if not nb:
            stack.pop()
            continue
        nr, nc = rng.choice(nb)
        g[2 * r + 1 + (nr - r)][2 * c + 1 + (nc - c)] = "."
        g[2 * nr + 1][2 * nc + 1] = "."
        seen.add((nr, nc))
        stack.append((nr, nc))
    for r in range(1, H - 1):
        for c in range(1, W - 1):
            if g[r][c] == "#" and rng.random() < loops:
                if (g[r - 1][c] == "." and g[r + 1][c] == ".") or (g[r][c - 1] == "." and g[r][c + 1] == "."):
                    g[r][c] = "."
    return ["".join(r) for r in g]


def _rooms(rng: random.Random, nr: int, nc: int, rs: int) -> list[str]:
    H, W = nr * (rs + 1) - 1, nc * (rs + 1) - 1
    g = [["."] * W for _ in range(H)]
    for i in range(1, nr):
        r = i * (rs + 1) - 1
        for c in range(W):
            g[r][c] = "#"
    for j in range(1, nc):
        c = j * (rs + 1) - 1
        for r in range(H):
            g[r][c] = "#"
    for i in range(nr):          # doors in vertical walls
        for j in range(1, nc):
            c = j * (rs + 1) - 1
            g[i * (rs + 1) + rng.randrange(rs)][c] = "."
    for i in range(1, nr):       # doors in horizontal walls
        for j in range(nc):
            r = i * (rs + 1) - 1
            g[r][j * (rs + 1) + rng.randrange(rs)] = "."
    return ["".join(r) for r in g]


def make_probe_grids(seed: int = SEED) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    out = []
    kinds = ["open"] * 10 + ["serpentine"] * 10 + ["maze"] * 10 + ["rooms"] * 10
    for i, kind in enumerate(kinds):
        j = i % 10
        cat = ["short", "medium", "long"][i % 3]
        for _attempt in range(200):
            if kind == "open":
                rows = _open(rng, 10 + j)
            elif kind == "serpentine":
                rows = _serpentine(rng, 9 + 2 * (j % 5), 8 + j)
            elif kind == "maze":
                rows = _maze(rng, 5 + j % 5, 5 + (j * 3) % 6)
            else:
                nr, nc = [(2, 2), (2, 3), (3, 2), (3, 3), (2, 4), (4, 2), (3, 3), (2, 3), (3, 2), (2, 2)][j]
                rows = _rooms(rng, nr, nc, 4 + j % 2)
            free = [(r, c) for r in range(len(rows)) for c in range(len(rows[0])) if rows[r][c] == "."]
            start = rng.choice(free)
            d = expansion.bfs_dist(rows, start)
            if len(d) < 15:
                continue
            mx = max(d.values())
            lo, hi = {"short": (3, max(4, mx // 4)), "medium": (mx // 3, max(mx // 3, 2 * mx // 3)),
                      "long": (max(3, int(0.8 * mx)), mx)}[cat]
            cands = [c for c, v in d.items() if lo <= v <= hi and v >= 3]
            if not cands:
                continue
            goal = rng.choice(cands)
            out.append({"id": f"{kind}_{j}", "kind": kind, "distance_class": cat, "rows": rows,
                        "start": list(start), "goal": list(goal), "bfs_distance": d[goal],
                        "h": len(rows), "w": len(rows[0])})
            break
        else:
            raise RuntimeError(f"could not build probe grid {kind} {j}")
    return out


# ---------------------------------------------------------------------------------------------- references
def ref_mode(fname: str) -> str:
    stem = Path(fname).stem
    for prefix, mode in (("bibfs", "bibfs"), ("biastar", "biastar"), ("bfs", "bfs"), ("dfs", "dfs"),
                         ("iddfs", "iddfs"), ("idastar", "idastar"), ("astar", "astar"), ("gbfs", "gbfs"),
                         ("dijkstra", "dijkstra_unit"), ("jps", "jps")):
        if stem.startswith(prefix):
            return mode
    raise ValueError(fname)


def references() -> list[dict[str, Any]]:
    return [{"file": p.name, "algorithm": ref_mode(p.name), "code": p.read_text()}
            for p in sorted(REF_DIR.glob("*.py"))]


EXPECT = {  # G-tracer properties (aggregated over the probe grids)
    "bfs": ["bfs_order", "fifo"], "dijkstra_unit": ["bfs_order", "heap"], "bibfs": ["two_frontiers"],
    "dfs": ["lifo_or_recursion", "adjacency"], "iddfs": ["restarts", "lifo_or_recursion"],
    "idastar": ["restarts", "heuristic_key"], "astar": ["heuristic_key", "heap"], "gbfs": ["heuristic_key", "heap"],
    "jps": ["heuristic_key", "heap"], "biastar": ["heuristic_key", "two_frontiers"]}


def g_tracer(refs: list[dict[str, Any]], traces: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for r, t in zip(refs, traces):
        per = t["per_grid"]
        nd = [p["bfs_nondecreasing"] for p in per if p["bfs_nondecreasing"] is not None]
        adj = [p["adjacency"] for p in per if p["adjacency"] is not None]
        props = {"bfs_order": (float(np.mean(nd)) >= 0.98) if nd else False,
                 "adjacency": (float(np.mean(adj)) >= 0.6) if adj else False, **t["flags"]}
        need = EXPECT[r["algorithm"]]
        rows.append({"file": r["file"], "algorithm": r["algorithm"], "flags": t["flags"],
                     "bfs_nondecreasing_mean": float(np.mean(nd)) if nd else None,
                     "adjacency_mean": float(np.mean(adj)) if adj else None,
                     "median_partial_spearman_h": t["median_partial_spearman_h"], "pop_share": t["pop_share"],
                     "sources": t["sources"], "n_valid_paths": t["n_ok"], "required": need,
                     "pass": all(props[k] for k in need) and t["n_ok"] == len(per)})
    return {"n_pass": sum(r["pass"] for r in rows), "n": len(rows), "rows": rows,
            "rule": "properties aggregated over the 40 probe grids (not per grid: corridors and single-path mazes "
                    "leave no room for a heuristic or a second frontier to show)"}


PLANTED = {
    "bfs_as_stack": "def solve(grid, start, goal):\n    R, C = len(grid), len(grid[0])\n    if grid[start[0]][start[1]] "
                    "!= '.' or grid[goal[0]][goal[1]] != '.':\n        return []\n    st = [start]\n    par = {start: None}\n"
                    "    while st:\n        cur = st.pop()\n        if cur == goal:\n            p = []\n            while cur "
                    "is not None:\n                p.append(cur)\n                cur = par[cur]\n            return p[::-1]\n"
                    "        r, c = cur\n        for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):\n            n = (r+dr, c+dc)\n"
                    "            if 0 <= n[0] < R and 0 <= n[1] < C and grid[n[0]][n[1]] == '.' and n not in par:\n"
                    "                par[n] = cur\n                st.append(n)\n    return []\n",
    "dijkstra_with_manhattan": "import heapq\ndef solve(grid, start, goal):\n    R, C = len(grid), len(grid[0])\n    if "
                               "grid[start[0]][start[1]] != '.' or grid[goal[0]][goal[1]] != '.':\n        return []\n"
                               "    pq = [(abs(start[0]-goal[0]) + abs(start[1]-goal[1]), 0, start)]\n    par = {start: "
                               "None}\n    dist = {start: 0}\n    while pq:\n        f, d, cur = heapq.heappop(pq)\n"
                               "        if cur == goal:\n            p = []\n            while cur is not None:\n"
                               "                p.append(cur)\n                cur = par[cur]\n            return p[::-1]\n"
                               "        r, c = cur\n        for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):\n            n = "
                               "(r+dr, c+dc)\n            if 0 <= n[0] < R and 0 <= n[1] < C and grid[n[0]][n[1]] == "
                               "'.' and d + 1 < dist.get(n, 10**9):\n                dist[n] = d + 1\n                "
                               "par[n] = cur\n                heapq.heappush(pq, (d + 1 + abs(n[0]-goal[0]) + "
                               "abs(n[1]-goal[1]), d + 1, n))\n    return []\n"}


def behavioural_rdm(refs: list[dict[str, Any]], traces: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(refs)
    Do, Dd = np.zeros((n, n)), np.zeros((n, n))
    for i, j in itertools.combinations(range(n), 2):
        Do[i, j] = Do[j, i] = expansion.pair_order_distance(traces[i], traces[j])
        Dd[i, j] = Dd[j, i] = expansion.ds_distance(traces[i], traces[j])
    algs = [r["algorithm"] for r in refs]

    def alg_level(D: np.ndarray) -> np.ndarray:
        M = np.zeros((10, 10))
        for a, x in enumerate(CANON_ORDER):
            for b, y in enumerate(CANON_ORDER):
                ia = [i for i, z in enumerate(algs) if z == x]
                ib = [i for i, z in enumerate(algs) if z == y]
                vals = [D[i, j] for i in ia for j in ib if i != j]
                M[a, b] = float(np.mean(vals)) if vals else 0.0
        return M

    Mo, Md = alg_level(Do), alg_level(Dd)
    out: dict[str, Any] = {"algorithms": CANON_ORDER, "references": [r["file"] for r in refs],
                           "d_order": Mo.tolist(), "d_DS": Md.tolist()}
    for lam in (0.0, 0.5, 1.0):
        M = Mo + lam * Md
        out[f"d_beh_lambda{lam}"] = M.tolist()
    M = Mo + 0.5 * Md
    g, near = {}, {}
    for a in NB5:
        ia = CANON_ORDER.index(a)
        dm = [M[ia, CANON_ORDER.index(b)] for b in B5]
        g[a] = float(min(dm))
        near[a] = B5[int(np.argmin(dm))]
    med = float(np.median(list(g.values())))
    out["behavioural_g"] = g
    out["behavioural_nearest_banned"] = near
    out["behavioural_classes"] = {a: ("EDGE" if v < med - 1e-12 else "OPPOSITE" if v > med + 1e-12 else "MIDDLE")
                                  for a, v in g.items()}
    d_to_bfs = {a: float(M[CANON_ORDER.index(a), CANON_ORDER.index("bfs")]) for a in NB5}
    out["P6_d_beh_to_bfs"] = d_to_bfs
    out["P6_udij_nearest_to_bfs"] = min(d_to_bfs, key=d_to_bfs.get) == UDIJ
    import geometry

    Y = geometry.classical_mds(M)
    out["behavioural_coordinates_mds"] = {a: Y[i].tolist() for i, a in enumerate(CANON_ORDER)}
    out["behavioural_mds_stress1"] = geometry.stress1(M, Y)
    out["program_level_d_order"] = Do.tolist()
    out["program_level_d_DS"] = Dd.tolist()
    out["reference_flags"] = {r["file"]: t["flags"] for r, t in zip(refs, traces)}
    return out


# ---------------------------------------------------------------------------------------------- 2d lexical
def char3(s: str) -> set[str]:
    s = s.lower()
    return {s[i:i + 3] for i in range(len(s) - 2)}


def jacc(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a | b) else 0.0


def tokenizer() -> Any:
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(M32["repo"], revision=M32["revision"])


def lexical(tok: Any) -> dict[str, Any]:
    rows = []
    banned_aliases = [(b, al) for b in B5 for al in ALIAS_TABLE[b]]
    for a in CANON_ORDER:
        for j, al in enumerate(ALIAS_TABLE[a]):
            L1 = sum(1 for b in B5 if alias_regex([b]).search(al))
            L2 = max(jacc(char3(al), char3(bal)) for b, bal in banned_aliases if b != a)
            tt = set(tok(" " + al, add_special_tokens=False)["input_ids"])
            L3 = max(jacc(tt, set(tok(" " + bal, add_special_tokens=False)["input_ids"]))
                     for b, bal in banned_aliases if b != a)
            rows.append({"algorithm": a, "alias_index": j, "alias": al, "L1": L1, "L2": L2, "L3": L3,
                         "n_tokens": len(tok(" " + al, add_special_tokens=False)["input_ids"]),
                         "banned": a in B5})
    R = np.zeros((10, 10))
    for x, y in itertools.combinations(range(10), 2):
        sims = [jacc(char3(p), char3(q)) for p in ALIAS_TABLE[CANON_ORDER[x]] for q in ALIAS_TABLE[CANON_ORDER[y]]]
        R[x, y] = R[y, x] = 1 - float(np.mean(sims))
    nb = [r for r in rows if r["algorithm"] in NB5]
    return {"aliases": rows, "R_lex": R.tolist(), "algorithms": CANON_ORDER,
            "L1_nonbanned": {f"{r['algorithm']}|{r['alias_index']}": r["L1"] for r in nb},
            "expected_L1": {"bibfs": [1, 1, 1], "biastar": [1, 1, 1], "idastar": [1, 2, 1], "jps": [0, 0, 0],
                            UDIJ: [0, 0, 0]},
            "L1_matches_expected": all([r["L1"] for r in nb if r["algorithm"] == a] == v for a, v in
                                       {"bibfs": [1, 1, 1], "biastar": [1, 1, 1], "idastar": [1, 2, 1],
                                        "jps": [0, 0, 0], UDIJ: [0, 0, 0]}.items())}


# ---------------------------------------------------------------------------------------------- 2e descriptions
DESCRIPTIONS: dict[str, list[str]] = {
    "bfs": ["a search that keeps the cells waiting to be visited in a first-in-first-out queue and always takes the "
            "oldest one next",
            "a search that visits every cell one step from the start, then every cell two steps away, and so on, "
            "ring by ring",
            "a search that spreads out from the start like a ripple on a pond, finishing each wave before starting "
            "the next"],
    "dfs": ["a search that keeps the cells waiting to be visited on a last-in-first-out stack and always takes the "
            "newest one next",
            "a search that follows one route as far as it can and backs up to the most recent fork only at a dead end",
            "a search that explores like a walker in a maze who keeps going forward and retraces steps only when "
            "stuck"],
    "iddfs": ["a search that runs a stack-based follow-one-route search with a step limit of 0, then 1, then 2, "
              "restarting from the start each time until the goal is within the limit",
              "a search that repeats a limited go-as-far-as-possible exploration from the start, allowing one more "
              "step each round",
              "a search that keeps re-exploring from the start on a leash that grows one step longer every round"],
    "astar": ["a search that keeps the waiting cells in a priority queue ordered by steps taken so far plus the "
              "Manhattan distance still to go, always expanding the smallest total",
              "a search that always expands the cell whose path length from the start plus estimated remaining "
              "distance to the goal is lowest",
              "a search that weighs how far it has already walked against how far the goal still looks, always "
              "continuing from the most promising combined score"],
    "gbfs": ["a search that keeps the waiting cells in a priority queue ordered only by Manhattan distance to the "
             "goal, ignoring the steps already taken",
             "a search that always expands the cell that looks closest to the goal regardless of how long the path "
             "to it was",
             "a search that always heads for whichever open cell seems nearest the goal, like walking toward a "
             "visible landmark"],
    UDIJ: ["a search that keeps the waiting cells in a priority queue keyed by the number of steps from the start, "
           "always expanding the one with the fewest steps",
           "a search that repeatedly settles the unsettled cell with the smallest known distance from the start and "
           "updates its neighbours, every move costing one",
           "a search that grows a set of cells whose distance from the start is final, always adding the closest "
           "remaining cell, with no estimate of where the goal is"],
    "bibfs": ["a search that runs two first-in-first-out queues at once, one from the start and one from the goal, "
              "taking turns until they reach a common cell",
              "a search that grows two rings of visited cells, one around each end, one step at a time, and joins "
              "the paths where the rings meet",
              "a search like two ripples spreading toward each other from both ends that stops when the waves touch"],
    "biastar": ["a search that runs two priority queues at once, one from the start ordered by steps plus Manhattan "
                "distance to the goal and one from the goal ordered by steps plus Manhattan distance to the start",
                "two estimate-guided searches growing from each end toward the other, each expanding its lowest "
                "steps-plus-estimate cell, joined where they meet",
                "a search in which two travellers leave opposite ends, each heading for the other's starting point by "
                "the most promising route, and meet in the middle"],
    "idastar": ["a search that runs repeated stack-based passes, cutting off any branch whose steps plus Manhattan "
                "distance to the goal exceeds a threshold and raising the threshold after each pass",
                "a search that restarts a go-as-far-as-possible exploration under a bound on steps so far plus "
                "estimated remaining distance, raising the bound each round",
                "a memory-light search that keeps re-exploring from the start, each time tolerating slightly more "
                "estimated total path cost"],
    "jps": ["a search with a priority queue ordered by steps plus Manhattan distance to the goal that slides along "
            "straight lines and adds only cells where a wall forces a turn or the goal is reached",
            "a search that skips over straight runs of open cells, stopping only beside obstacles that open a new "
            "direction, and orders these stopping cells by distance so far plus estimated distance to go",
            "a search that leaps across open corridors in straight lines and pauses only at corners and wall edges, "
            "continuing from the most promising pause"],
}
# Pre-written rewrites (used only for a description that fails the naming gate; at most 2 per description).
REWRITES: dict[str, list[list[str]]] = {
    "bibfs": [["a search that runs two first-in-first-out queues, one growing level by level from the start and the "
               "other level by level from the goal, stopping where the two frontiers meet",
               "a search that expands level by level from both the start and the goal simultaneously and joins the "
               "two halves of the path at the first shared cell"]] * 3,
    "biastar": [["a search that runs two heuristic-guided priority-queue searches simultaneously, forward from the "
                 "start toward the goal and backward from the goal toward the start, joined where they meet",
                 "a search that runs the steps-plus-Manhattan-estimate priority search in both directions at once, "
                 "start to goal and goal to start, until the two searches meet"]] * 3,
    "idastar": [["a search that repeats a depth-limited stack-based exploration in which the limit is on steps plus "
                 "the Manhattan estimate to the goal, raising that limit to the smallest exceeded value each round",
                 "a search that combines repeated deepening with a steps-plus-Manhattan-estimate cutoff, restarting "
                 "from the start with a larger cost bound after each failed pass"]] * 3,
    "jps": [["a priority-queue search on a uniform grid ordered by steps plus Manhattan estimate that jumps along "
             "straight lines and only adds cells with forced neighbours next to walls",
             "an accelerated grid search ordered by steps plus Manhattan estimate that prunes symmetric paths by "
             "jumping straight until it reaches a cell with a forced neighbour"]] * 3,
    UDIJ: [["a search that keeps the waiting cells in a priority queue keyed only by the distance travelled from the "
            "start, settling the closest unsettled cell and relaxing its neighbours' distances",
            "a shortest-path search that keeps tentative distances from the start in a min-priority queue and "
            "relaxes the edges of each settled cell, every edge weighing one"]] * 3,
    "iddfs": [["a search that runs a depth-limited stack-based search with limit 0, then 1, then 2, and so on, "
               "restarting from the start each round until the goal is reached",
               "a search that performs successive depth-limited go-as-far-as-possible searches with an increasing "
               "depth cutoff, restarting from the start each round"]] * 3,
    "gbfs": [["a search that always expands the waiting cell with the smallest Manhattan estimate to the goal, kept "
              "in a priority queue that ignores the cost of the path so far",
              "a search that orders its frontier only by estimated distance to the goal and expands the most "
              "promising-looking cell first, never adding the steps already taken"]] * 3,
    "astar": [["a search that orders its frontier in a priority queue by the steps so far plus an admissible "
               "Manhattan estimate to the goal and expands the lowest total first",
               "a best-path search whose priority is cost so far plus a Manhattan estimate of the cost to go, "
               "expanding the lowest sum first"]] * 3,
    "bfs": [["a search that expands cells level by level from the start using a first-in-first-out queue, so "
             "nearer cells are always visited before farther ones",
             "a search that explores all neighbours of the current layer before moving to the next layer, using a "
             "first-in-first-out queue"]] * 3,
    "dfs": [["a search that goes as deep as possible along each branch before backtracking, using a "
             "last-in-first-out stack or recursion",
             "a search that keeps extending the current path to an unvisited neighbour and backtracks only when no "
             "unvisited neighbour remains, using recursion"]] * 3,
}
STOP = set("a an the of to in on by and or as at for from with that is its it each one only which who whose "
           "this these be are was until when where there then so than any every always no not into over how "
           "like s".split())


def content_words(s: str) -> set[str]:
    ws = re.findall(r"[a-z]+", s.lower())
    return {w[:-1] if w.endswith("s") and len(w) > 3 else w for w in ws if w not in STOP}


def check_description(d: str) -> dict[str, Any]:
    m = alias_regex(CANON_ORDER).search(d)
    return {"alias_match": m.group(0) if m else None}


def descriptions_v0(tok: Any) -> dict[str, Any]:
    rows = []
    for a in CANON_ORDER:
        for di, d in enumerate(DESCRIPTIONS[a]):
            n = len(tok(" " + d, add_special_tokens=False)["input_ids"])
            rows.append({"algorithm": a, "style": f"D{di + 1}", "desc_index": di, "text": d, "n_tokens": n,
                         **check_description(d)})
    grand = float(np.mean([r["n_tokens"] for r in rows]))
    per_alg = {a: float(np.mean([r["n_tokens"] for r in rows if r["algorithm"] == a])) for a in CANON_ORDER}
    banned_desc = [r for r in rows if r["algorithm"] in B5]
    for r in rows:
        r["D_overlap"] = max(jacc(content_words(r["text"]), content_words(b["text"])) for b in banned_desc
                             if b is not r)
    Rd = np.zeros((10, 10))
    for x, y in itertools.combinations(range(10), 2):
        sims = [jacc(content_words(p), content_words(q)) for p in DESCRIPTIONS[CANON_ORDER[x]]
                for q in DESCRIPTIONS[CANON_ORDER[y]]]
        Rd[x, y] = Rd[y, x] = 1 - float(np.mean(sims))
    checks = {"no_alias_match": all(r["alias_match"] is None for r in rows),
              "token_length_20_45": all(20 <= r["n_tokens"] <= 45 for r in rows),
              "per_algorithm_within_8_of_grand_mean": all(abs(v - grand) <= 8 for v in per_alg.values()),
              "grand_mean_tokens": grand, "per_algorithm_mean_tokens": per_alg}
    return {"descriptions": rows, "R_desc_lex": Rd.tolist(), "checks": checks, "rewrites": REWRITES,
            "forced_templates": prompts_tp.forced_templates()}


# ---------------------------------------------------------------------------------------------- 2f M-lex
MLEX_TEMPLATES = ["Unrelated note: the word {X} appears in the repository changelog.",
                  "Side remark: someone typed {X} in an old commit message.",
                  "For the record, {X} is the name of a file elsewhere in this project.",
                  "Trivia: the string {X} was found in a spreadsheet header.",
                  "Aside: a colleague's notebook has a page titled {X}.",
                  "Irrelevant detail: {X} is printed on a sticker on the office printer.",
                  "Background: the wiki has an empty page called {X}.",
                  "Housekeeping: a stale branch is named after {X}.",
                  "Unrelated: {X} was mentioned in a podcast episode title.",
                  "Note: {X} is the title of a talk at last year's meetup."]


def _neutral_pool() -> list[str]:
    nn = read_json(ROOT / "inputs" / "neutral_nouns.json")["nouns"]
    return sorted({n["noun"].lower() for n in nn if n["qwen3_tokens_with_leading_space"] == 1 and
                   n["noun"].isalpha()})


def _full_ids(tok: Any, prompt: str) -> list[int]:
    return tok(prompts_tp.render_chat(tok, prompt, True), add_special_tokens=False)["input_ids"]


def mlex_prompts(tok: Any) -> dict[str, Any]:
    pool = _neutral_pool()
    spec = prompts_tp.SPEC()
    out = []
    n_retry = 0
    for t, tpl in enumerate(MLEX_TEMPLATES):
        cache: dict[int, str] = {}
        for a in CANON_ORDER:
            for j, al in enumerate(ALIAS_TABLE[a]):
                seg = tpl.replace("{X}", al)
                pr = cap_first(seg) + "\n\n" + spec
                ids = _full_ids(tok, pr)
                target = len(ids)
                rng = random.Random(f"{SEED}-{t}")
                twin = None
                base_k = len(tok(" " + al, add_special_tokens=False)["input_ids"])
                tries = 0
                for k in [base_k] + [base_k + d for d in (-1, 1, -2, 2, -3, 3)]:
                    if k < 1:
                        continue
                    if k in cache:
                        cand = cache[k]
                        tw = cap_first(tpl.replace("{X}", cand)) + "\n\n" + spec
                        if len(_full_ids(tok, tw)) == target:
                            twin = cand
                            break
                    for _ in range(60):
                        tries += 1
                        cand = " ".join(rng.sample(pool, k))
                        tw = cap_first(tpl.replace("{X}", cand)) + "\n\n" + spec
                        if len(_full_ids(tok, tw)) == target:
                            twin = cand
                            cache.setdefault(k, cand)
                            break
                    if twin:
                        break
                n_retry += tries
                assert twin is not None, f"no twin for {tpl} / {al}"
                tw_prompt = cap_first(tpl.replace("{X}", twin)) + "\n\n" + spec
                ia, it = _full_ids(tok, pr), _full_ids(tok, tw_prompt)
                assert len(ia) == len(it)
                from states import spec_span

                sa = spec_span(tok, prompts_tp.render_chat(tok, pr, True), spec)[0]
                st = spec_span(tok, prompts_tp.render_chat(tok, tw_prompt, True), spec)[0]
                assert sa == st and [ia[i] for i in sa] == [it[i] for i in st], "SPEC ids differ alias/twin"
                out.append({"template": t, "algorithm": a, "alias_index": j, "alias": al, "group": 3 * t + j,
                            "prompt": pr, "twin": twin, "twin_prompt": tw_prompt, "n_tokens": len(ia)})
    return {"templates": MLEX_TEMPLATES, "rows": out, "n": len(out), "twin_search_tries": n_retry,
            "checks": {"identical_token_counts": True, "identical_spec_ids": True}}


# ---------------------------------------------------------------------------------------------- 2g M-code contexts
MCODE_FRAMES = ["Do not use {X} for this task.", "Your solution must not rely on {X}.", "Avoid {X} entirely.",
                "{X} is not allowed here.", "Write a correct solution that does not use {X}."]


def mcode_contexts() -> dict[str, Any]:
    pool = _neutral_pool()
    rng = random.Random(SEED + 1)
    rows = []
    for v, fr in enumerate(MCODE_FRAMES):
        nouns = rng.sample(pool, 3)
        seg = cap_first(fr.replace("{X}", join_names_or([f"the {n}" for n in nouns])))
        rows.append({"variant": v, "frame": f"W{v + 1}", "nouns": nouns, "segment": seg,
                     "prompt": seg + "\n\n" + prompts_tp.SPEC()})
    return {"variants": rows, "assistant_prefix": "chat template with enable_thinking=False (empty think block) + "
                                                  "'```python\\n' + code + '\\n```'",
            "assignment": "round-robin within algorithm (program rank mod 5)"}


# ---------------------------------------------------------------------------------------------- stage
def stage_cpu(*args: str) -> None:
    t0 = utc_now()
    grids = make_probe_grids()
    write_json(DATA / "probe_grids.json", {"seed": SEED, "grids": grids})
    logger.info(f"probe grids: {len(grids)} ({[g['kind'] for g in grids[::10]]}), BFS distances "
                f"{[g['bfs_distance'] for g in grids]}")
    refs = references()
    traces = expansion.trace_many([r["code"] for r in refs], grids)
    gt = g_tracer(refs, traces)
    planted = {k: expansion.trace_program(c, grids)["flags"] for k, c in PLANTED.items()}
    gt["planted_controls"] = {"bfs_as_stack_reads_lifo": planted["bfs_as_stack"]["lifo_or_recursion"] and
                              not planted["bfs_as_stack"]["fifo"],
                              "dijkstra_with_manhattan_sets_heuristic": planted["dijkstra_with_manhattan"][
                                  "heuristic_key"], "flags": planted}
    write_json(RESULTS / "g_tracer.json", gt)
    logger.info(f"G-tracer {gt['n_pass']}/{gt['n']}; planted {gt['planted_controls']}")
    for r in gt["rows"]:
        if not r["pass"]:
            logger.warning(f"G-tracer fail {r['file']}: flags {r['flags']} nd {r['bfs_nondecreasing_mean']} adj "
                           f"{r['adjacency_mean']} ps {r['median_partial_spearman_h']} share {r['pop_share']} "
                           f"src {r['sources']} ok {r['n_valid_paths']}")
    beh = behavioural_rdm(refs, traces)
    beh["g_tracer_pass"] = f"{gt['n_pass']}/{gt['n']}"
    write_json(RESULTS / "behavioural_distance.json", beh)
    write_json(DATA / "reference_traces.json", {"references": [r["file"] for r in refs], "traces": traces})
    logger.info(f"behavioural g {beh['behavioural_g']} classes {beh['behavioural_classes']}; P6 {beh['P6_d_beh_to_bfs']}")
    tok = tokenizer()
    lex = lexical(tok)
    write_json(RESULTS / "lexical.json", lex)
    logger.info(f"L1 {lex['L1_nonbanned']} matches expected {lex['L1_matches_expected']}")
    desc = descriptions_v0(tok)
    write_json(DATA / "descriptions_v0.json", desc)
    logger.info(f"descriptions: checks {desc['checks']}")
    bad = [(r["algorithm"], r["style"], r["n_tokens"], r["alias_match"]) for r in desc["descriptions"]
           if r["alias_match"] or not 20 <= r["n_tokens"] <= 45]
    if bad:
        deviation("D-desc-checks", f"descriptions outside the checks: {bad}")
    ml = mlex_prompts(tok)
    write_json(DATA / "mlex_prompts.json", ml)
    logger.info(f"M-lex prompts: {ml['n']} alias + {ml['n']} twins")
    ctx = mcode_contexts()
    write_json(DATA / "mcode_contexts.json", ctx)
    payload = {"label": "COMMIT1a", "utc": utc_now(), "started": t0,
               "files": {p: sha256_file(ROOT / p) for p in ["data/probe_grids.json", "results/g_tracer.json",
                                                            "results/behavioural_distance.json",
                                                            "results/lexical.json", "data/descriptions_v0.json",
                                                            "data/mlex_prompts.json", "data/mcode_contexts.json"]},
               "note": "M-lex prompts and twins, M-code contexts, probe grids, lexical measures, behavioural RDM; "
                       "M-lex states may be extracted only after this commit"}
    write_json(PRED / "commit1a.json", payload)
    commit(PRED / "commit1a.json", "COMMIT1a", "point sets for M-lex; grids, lexical and behavioural files")
