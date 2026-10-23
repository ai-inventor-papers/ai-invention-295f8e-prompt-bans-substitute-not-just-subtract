#!/usr/bin/env python3
"""Stage 1.2 discipline x container INSTRUMENT (name-blind: only runtime events and code structure, never names).

Runs (all through src/inst_child.py = iteration 9's tracer v9 child + numeric item-assignment values, sorted-list
marking and seeded runs):
  MAIN  the 40 v9 probe grids (probes/probes_v9.json), unseeded -> per-probe expansion record E and statistics
        (iteration 9's orderclass.expansion_record / probe_stats / classify, unchanged).
  RNG   5 of the probe grids, global random seeded 0 vs 1 (and 0 again as a determinism control); random.seed is a
        no-op inside the candidate so in-program reseeding cannot hide random order.
  GOAL  3 pairs of probes with the same start and two goals (open 15x15 / 19x19 and a walled grid), seeded 0.
Checks (plan 1.2): (i) sweep detector, (ii) RNG sensitivity, (iii) goal sensitivity, plus the label-correcting
re-push test and a coordinate-key test.
ORDERED RULE (first match wins; pre-rules mark iterative-deepening restarts and two-ended searches as OTHER):
  RLX  sweeps (no frontier container, a distance label decreases after it was set, every reachable cell read >= 2x)
       or label-correcting re-push (a cell is expanded, re-inserted, and expanded again, with a relaxation
       comparison dist[v] > dist[u] + w in the code) on >= 2 probes
  RND  RNG-sensitive: the expansion stream differs between seeds 0 and 1 on >= 2 of 5 probes
  HEU  goal-sensitive: the first 20 expanded cells differ between the two goals on >= 2 of 3 pairs
  LEV  pooled p_mono >= 0.98, level cover >= 0.98, no restarts and re-expansion share <= 0.02 (for frontier-less
       programs also the first-label order of the distance array)
  DFS  pooled LIFO consistency >= 0.9
  CRD  deterministic, goal-independent and >= 0.9 of the choices are the minimum of a coordinate key over the open set
  OTHER otherwise
CONTAINER: the operation that selects each expanded cell (runtime src of the E entries, majority over expansions):
  heap / PriorityQueue.get -> HEAP; deque.popleft / deque.pop / Queue.get / list.pop(0) -> DEQ; list.pop() /
  LifoQueue.get / self-recursive call -> STK; pops from a list kept sorted (bisect.insort or list.sort) -> SLIST;
  set.pop / set.remove / set.discard / iteration over a set -> SET; no frontier object (READ-burst expansions or
  non-recursive helper calls with no container removals) -> ARR; anything else (list.pop(i), dict, iteration over a
  list) -> LIST / DICT (not a planned container). An AST cross-check is recorded.
"""

from __future__ import annotations

import ast
import json
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
sys.path.insert(0, str(SRC))
import orderclass  # noqa: E402  (iteration 9, unchanged)
from probes_v9 import bfs_dist  # noqa: E402

CHILD = SRC / "inst_child.py"
SANDBOX_PY = orderclass.SANDBOX_PY
TH = {"lev_p_mono": 0.98, "lev_cover": 0.98, "lev_revisit": 0.02, "dfs_p_lifo": 0.9, "crd_share": 0.9,
      "rng_min_probes": 2, "goal_min_pairs": 2, "goal_first_k": 20, "rng_first_k": 30, "rlx_min_probes": 2,
      "sweep_read_cover": 0.9, "min_informative": 10, "id_share": 0.5, "bidir_share": 0.5}
RNG_PROBES = [0, 10, 20, 30, 35]
KEYS = {"(r,c)": lambda c: (c[0], c[1]), "(c,r)": lambda c: (c[1], c[0]), "(-r,-c)": lambda c: (-c[0], -c[1]),
        "(-c,-r)": lambda c: (-c[1], -c[0]), "(r,-c)": lambda c: (c[0], -c[1]), "(-r,c)": lambda c: (-c[0], c[1]),
        "(c,-r)": lambda c: (c[1], -c[0]), "(-c,r)": lambda c: (-c[1], c[0]),
        "(r+c,r)": lambda c: (c[0] + c[1], c[0]), "(r+c,c)": lambda c: (c[0] + c[1], c[1]),
        "(r-c,r)": lambda c: (c[0] - c[1], c[0])}


def _open_grid(n: int) -> list[str]:
    return ["." * n for _ in range(n)]


def _walled(n: int) -> list[str]:
    g = [list("." * n) for _ in range(n)]
    for r in range(2, n - 2, 4):
        for c in range(n):
            if c % 7 != 3:
                g[r][c] = "#"
    return ["".join(x) for x in g]


@lru_cache(maxsize=1)
def goal_pairs() -> list[tuple[dict[str, Any], dict[str, Any]]]:
    out = []
    g15, g19, gw = _open_grid(15), _open_grid(19), _walled(19)
    out.append(({"name": "G15a", "grid": g15, "start": [7, 7], "goal": [0, 0]},
                {"name": "G15b", "grid": g15, "start": [7, 7], "goal": [14, 14]}))
    out.append(({"name": "G19a", "grid": g19, "start": [9, 9], "goal": [0, 18]},
                {"name": "G19b", "grid": g19, "start": [9, 9], "goal": [18, 0]}))
    out.append(({"name": "GWa", "grid": gw, "start": [9, 9], "goal": [0, 0]},
                {"name": "GWb", "grid": gw, "start": [9, 9], "goal": [18, 18]}))
    return out


# ---------------------------------------------------------------------------------------------- child runs
def run_child(code: str, probes: list[dict[str, Any]], seed: int | None = None,
              timeout_s: float = 90.0, probe_timeout_s: float = 2.0) -> dict[int, dict[str, Any]]:
    recs: dict[int, dict[str, Any]] = {}
    first, restarts = 0, 0
    t_end = time.time() + timeout_s
    while first < len(probes):
        job = {"code": code, "probes": probes, "first": first, "probe_timeout_s": probe_timeout_s,
               "rlimit_as": 1024 ** 3, "seed": seed}
        left = t_end - time.time()
        if left <= 1:
            break
        try:
            proc = subprocess.run([SANDBOX_PY, "-I", "-S", str(CHILD)], input=json.dumps(job), capture_output=True,
                                  text=True, timeout=min(left, probe_timeout_s * (len(probes) - first) + 15))
            out = proc.stdout
        except subprocess.TimeoutExpired as e:
            out = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        last_i, done = first - 1, False
        for ln in out.splitlines():
            if not ln.startswith("{"):
                continue
            try:
                d = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if "error" in d:
                return {-1: {"error": d["error"]}, **recs}
            if d.get("done"):
                done = True
                continue
            recs[d["i"]] = d
            last_i = max(last_i, d["i"])
        if done:
            break
        if last_i < first:
            recs[first] = {"i": first, "events": [], "strings": ["read"], "valid": False, "exc": "child_crash",
                           "timeout": False, "grid_copied": False, "truncated": False}
            last_i = first
        first = last_i + 1
        restarts += 1
        if restarts > 45:
            break
    return recs


def _E(rec: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        return orderclass.expansion_record(rec)["E"]
    except (KeyError, ValueError, IndexError, TypeError):
        return []


def _useq(E: list[dict[str, Any]], exclude: set | None = None) -> list[tuple[int, int]]:
    seen, out = set(), []
    for x in E:
        c = tuple(x["cell"])
        if c in seen or (exclude and c in exclude):
            continue
        seen.add(c)
        out.append(c)
    return out


def _stream_cells(rec: dict[str, Any], n: int = 300) -> list[tuple]:
    return [tuple(e[:3]) for e in (rec.get("events") or [])[:n]]


# ---------------------------------------------------------------------------------------------- checks
def relaxation_ast(code: str) -> bool:
    return orderclass.relaxation_ast(code)


def full_passes(rec: dict[str, Any], pre: dict[str, Any]) -> int:
    """Full raster passes in the grid-READ stream: the stream is cut where the read row wraps from the lower half
    back to the upper half of the grid; a segment is a full pass if it reads >= 90% of the reachable free cells."""
    ev = [e for e in (rec.get("events") or []) if e[0] == 2]
    if not ev:
        return 0
    R = pre["R"]
    comp = set(pre["d_s"])
    segs, cur, prev_r = [], set(), None
    for e in ev:
        r = e[1]
        if prev_r is not None and prev_r >= R / 2 and r < max(1, R / 4) and prev_r - r >= max(2, R / 2):
            segs.append(cur)
            cur = set()
        cur.add((e[1], e[2]))
        prev_r = r
    segs.append(cur)
    return sum(1 for sg in segs if len(sg & comp) >= TH["sweep_read_cover"] * max(1, len(comp)))


def sweep_probe(rec: dict[str, Any], pre: dict[str, Any]) -> dict[str, Any]:
    ev = rec.get("events") or []
    vals: dict[tuple[int, int], list[float]] = defaultdict(list)
    for e in ev:
        if e[0] == 5 and e[5] is not None and -1e-9 <= e[5] < 1e9:
            vals[(e[1], e[2])].append(e[5])
    relabel = sum(1 for v in vals.values() if any(b < a and a >= 2 and b >= 1 for a, b in zip(v, v[1:])))
    reads = Counter((e[1], e[2]) for e in ev if e[0] == 2)
    comp = pre["d_s"]
    cover2 = sum(1 for c in comp if reads.get(c, 0) >= 2) / max(1, len(comp))
    pops = sum(1 for e in ev if e[0] == 1)
    fp = full_passes(rec, pre)
    return {"relabel_cells": relabel, "read2_cover": cover2, "n_pop": pops, "full_passes": fp,
            "sweep": bool(fp >= 2 and pops == 0)}


def repush_probe(rec: dict[str, Any], E: list[dict[str, Any]]) -> bool:
    """A cell expanded (popped and confirmed), re-inserted into a container, and expanded again."""
    ev = rec.get("events") or []
    pos: dict[tuple[tuple[int, int], int], list[int]] = defaultdict(list)
    for x in E:
        if x["src"] in ("scan",) or x["src"].startswith("call:") or x["src"].startswith("iter"):
            continue
        pos[(tuple(x["cell"]), ev[x["ev"]][4])].append(x["ev"])
    pushes: dict[tuple[tuple[int, int], int], list[int]] = defaultdict(list)
    for k, e in enumerate(ev):
        if e[0] == 0:
            pushes[((e[1], e[2]), e[4])].append(k)
    for key, ps in pos.items():
        if len(ps) < 2:
            continue
        for a, b in zip(ps, ps[1:]):
            if any(a < k < b for k in pushes.get(key, ())):
                return True
    return False


def coord_share(rec: dict[str, Any], E: list[dict[str, Any]], pre: dict[str, Any]) -> dict[str, tuple[int, int]]:
    ev = rec.get("events") or []
    useq_idx, seen = [], set()
    for x in E:
        c = tuple(x["cell"])
        if c not in seen:
            seen.add(c)
            useq_idx.append((c, x["ev"]))
    push_seq = [(k, (e[1], e[2])) for k, e in enumerate(ev) if e[0] == 0]
    has_push = bool(push_seq)
    F: set[tuple[int, int]] = set()
    expanded: set[tuple[int, int]] = set()
    pp = 0
    res = {k: [0, 0] for k in KEYS}
    free = pre["free"]
    for k, (x, e_at) in enumerate(useq_idx[:2500]):
        if has_push:
            while pp < len(push_seq) and push_seq[pp][0] < e_at:
                c = push_seq[pp][1]
                if c not in expanded and c in free:
                    F.add(c)
                pp += 1
        if k > 0 and len(F) >= 2 and x in F:
            for name, key in KEYS.items():
                kx = key(x)
                res[name][1] += 1
                res[name][0] += int(kx == min(key(c) for c in F))
        expanded.add(x)
        F.discard(x)
        if not has_push:
            for nb in orderclass.nb4(x):
                if nb in free and nb not in expanded:
                    F.add(nb)
    return {k: (v[0], v[1]) for k, v in res.items()}


def lev_assign(rec: dict[str, Any], pre: dict[str, Any]) -> tuple[int, int]:
    """Frontier-less programs: p_mono on the first-label order of numeric assignments (init sweeps with one constant
    value removed): (monotone steps, steps)."""
    ev = [e for e in (rec.get("events") or []) if e[0] == 5 and e[5] is not None and 0 <= e[5] < 1e9]
    if not ev:
        return 0, 0
    vc = Counter(e[5] for e in ev)
    common, cnt = vc.most_common(1)[0]
    if cnt >= 0.9 * len(pre["free"]):
        ev = [e for e in ev if e[5] != common]
    seen, order = set(), []
    for e in ev:
        c = (e[1], e[2])
        if c not in seen:
            seen.add(c)
            order.append(c)
    d = pre["d_s"]
    o = [c for c in order if c in d]
    pm = [int(d[b] >= d[a]) for a, b in zip(o, o[1:])]
    return sum(pm), len(pm)


CONT_MAP = {"heap": "HEAP", "pq.get": "HEAP", "deque.popleft": "DEQ", "deque.pop": "DEQ", "queue.get": "DEQ",
            "list.pop0": "DEQ", "list.pop": "STK", "lifo.get": "STK", "set.pop": "SET", "set.remove": "SET",
            "set.discard": "SET", "iter.set": "SET", "iter.frozenset": "SET", "iter.deque": "DEQ",
            "list.popi": "LIST", "iter.list": "LIST", "dict.pop": "DICT", "dict.popitem": "DICT", "iter.dict": "DICT",
            "scan": "ARR", "deque.remove": "DEQ", "list.remove": "LIST"}


def container_of(recs: dict[int, dict[str, Any]], Es: dict[int, list[dict[str, Any]]]) -> dict[str, Any]:
    votes: Counter = Counter()
    raw: Counter = Counter()
    for i, E in Es.items():
        rec = recs.get(i) or {}
        has_removal = any(e[0] == 1 for e in (rec.get("events") or []))
        for x in E:
            s = x["src"].split("<")[0] if not x["src"].startswith("call:") else x["src"]
            raw[s] += 1
            if s.startswith("slist."):
                votes["SLIST"] += 1
            elif s.startswith("call:"):
                if x["src"].endswith("<self"):
                    votes["STK"] += 1
                elif not has_removal:
                    votes["ARR"] += 1
                else:
                    votes["CALL"] += 1
            else:
                votes[CONT_MAP.get(s, "OTHER")] += 1
    cont = votes.most_common(1)[0][0] if votes else "NONE"
    tot = sum(votes.values()) or 1
    return {"container": cont, "share": votes[cont] / tot if votes else 0.0, "votes": dict(votes),
            "src_counts": dict(raw.most_common(12))}


def ast_container_hint(code: str) -> dict[str, bool]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {}
    names = {n.attr if isinstance(n, ast.Attribute) else n.id for n in ast.walk(tree)
             if isinstance(n, (ast.Attribute, ast.Name))}
    rec = False
    for f in ast.walk(tree):
        if isinstance(f, ast.FunctionDef):
            rec |= any(isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id == f.name
                       for x in ast.walk(f))
    return {"heap": bool({"heappush", "heappop", "heapq", "PriorityQueue"} & names),
            "deque": bool({"deque", "popleft", "Queue"} & names), "insort": bool({"insort", "insort_left",
                                                                                 "insort_right", "sort"} & names),
            "set": "set" in names or any(isinstance(n, ast.Set) for n in ast.walk(tree)),
            "random": bool({"random", "choice", "shuffle", "randint"} & names), "recursion": rec}


# ---------------------------------------------------------------------------------------------- measure
def measure(code: str) -> dict[str, Any]:
    t0 = time.time()
    P = orderclass.probes()
    recs = run_child(code, P)
    if -1 in recs:
        return {"disc": "OTHER", "cont": "NONE", "fine": "UNTRACEABLE", "reason": f"child error {recs[-1]['error']}",
                "seconds": round(time.time() - t0, 2)}
    stats, Es = [], {}
    for i in range(len(P)):
        rec = recs.get(i)
        if rec is None:
            stats.append({"i": i, "n_E": 0, "informative": False, "exc": "not_run"})
            continue
        try:
            stats.append(orderclass.probe_stats(rec, i))
        except (KeyError, ValueError, IndexError, TypeError, ZeroDivisionError) as e:
            stats.append({"i": i, "n_E": 0, "informative": False, "exc": f"stats:{type(e).__name__}"})
        Es[i] = _E(rec)
    cl = orderclass.classify(stats)
    inf_idx = [s["i"] for s in stats if s.get("informative")]
    out: dict[str, Any] = {"tracer_order_class": cl.get("order_class"), "tracer_fine": cl.get("order_class_fine"),
                           "n_informative": len(inf_idx), "n_valid_paths": sum(1 for s in stats if s.get("valid")),
                           "p_mono": cl.get("p_mono"), "level_cover": cl.get("level_cover"),
                           "p_lifo": cl.get("p_lifo"), "restarts_E": cl.get("restarts_E"),
                           "revisit_share": cl.get("revisit_share"), "id_share": cl.get("id_share"),
                           "bidir_share": cl.get("bidir_share"), "fifo_flag": cl.get("fifo_flag")}
    pre = orderclass.probe_pre()
    nb_far = nb_early = 0
    for i in inf_idx:
        s_, t_ = pre[i]["s"], pre[i]["t"]
        if pre[i]["d_s"].get(t_, 0) >= 6:
            nb_far += 1
            u_ = _useq(Es.get(i, []))
            nb_early += int(t_ in u_[:3])
    out["goal_early_share"] = nb_early / nb_far if nb_far else 0.0
    # (i) sweeps and label-correcting re-push
    sw = [sweep_probe(recs[i], pre[i]) for i in range(len(P)) if i in recs]
    out["sweep_probes"] = sum(1 for s in sw if s["sweep"])
    out["relabel_probes"] = sum(1 for s in sw if s["relabel_cells"] > 0)
    out["repush_probes"] = sum(1 for i in Es if repush_probe(recs[i], Es[i]))
    out["relaxation_ast"] = relaxation_ast(code)
    # (ii) RNG sensitivity
    rp = [P[i] for i in RNG_PROBES]
    r0, r1, r0b = run_child(code, rp, seed=0, timeout_s=30), run_child(code, rp, seed=1, timeout_s=30), \
        run_child(code, rp, seed=0, timeout_s=30)
    n_diff = n_nondet = 0
    for j in range(len(rp)):
        a, b, c = r0.get(j), r1.get(j), r0b.get(j)
        if not a or not b:
            continue
        ea, eb = _useq(_E(a))[:TH["rng_first_k"]], _useq(_E(b))[:TH["rng_first_k"]]
        n_diff += int(ea != eb or _stream_cells(a) != _stream_cells(b))
        if c:
            n_nondet += int(_stream_cells(a) != _stream_cells(c))
    out["rng_diff_probes"], out["rng_nondet_probes"] = n_diff, n_nondet
    # (iii) goal sensitivity
    pairs = goal_pairs()
    flat = [p for pr in pairs for p in pr]
    gr = run_child(code, flat, seed=0, timeout_s=30)
    g_diff = 0
    for j, (pa, pb) in enumerate(pairs):
        a, b = gr.get(2 * j), gr.get(2 * j + 1)
        if not a or not b:
            continue
        ex = {tuple(pa["start"]), tuple(pa["goal"]), tuple(pb["goal"])}
        ea = _useq(_E(a), ex)[:TH["goal_first_k"]]
        eb = _useq(_E(b), ex)[:TH["goal_first_k"]]
        k = min(len(ea), len(eb))
        pa_ = _useq([{"cell": (e[1], e[2])} for e in (a.get("events") or []) if e[0] == 1], ex)[:TH["goal_first_k"]]
        pb_ = _useq([{"cell": (e[1], e[2])} for e in (b.get("events") or []) if e[0] == 1], ex)[:TH["goal_first_k"]]
        kp = min(len(pa_), len(pb_))
        g_diff += int((k >= 2 and ea[:k] != eb[:k]) or (kp >= 2 and pa_[:kp] != pb_[:kp]))
    out["goal_diff_pairs"] = g_diff
    # coordinate key
    tot = {k: [0, 0] for k in KEYS}
    for i in inf_idx:
        if i in recs:
            for k, (a, n) in coord_share(recs[i], Es.get(i, []), pre[i]).items():
                tot[k][0] += a
                tot[k][1] += n
    best = max(tot, key=lambda k: (tot[k][0] / tot[k][1]) if tot[k][1] else 0)
    out["coord_key"], out["coord_share"] = best, (tot[best][0] / tot[best][1]) if tot[best][1] else 0.0
    # container
    cont = container_of(recs, {i: Es[i] for i in inf_idx if i in Es})
    out.update({"container_votes": cont["votes"], "container_share": cont["share"], "src_counts": cont["src_counts"]})
    out["ast_hint"] = ast_container_hint(code)
    container = cont["container"]
    # frontier-less first-label order
    la = [lev_assign(recs[i], pre[i]) for i in inf_idx if i in recs]
    k_, n_ = sum(a for a, _ in la), sum(n for _, n in la)
    out["lev_assign_p_mono"] = k_ / n_ if n_ else None
    # ordered rule
    fine = None
    if len(inf_idx) < TH["min_informative"]:
        disc, fine = "OTHER", "UNTRACEABLE"
    elif (cl.get("id_share") or 0) >= TH["id_share"]:
        disc, fine = "OTHER", "ID-restarts"
    elif (cl.get("bidir_share") or 0) >= TH["bidir_share"] or out["goal_early_share"] >= TH["bidir_share"]:
        disc, fine = "OTHER", "BIDIR"
    elif (out["sweep_probes"] >= TH["rlx_min_probes"] and container == "ARR" and
          (out["lev_assign_p_mono"] or 0) < TH["lev_p_mono"] and g_diff < TH["goal_min_pairs"]) or \
            (out["repush_probes"] >= TH["rlx_min_probes"] and out["relaxation_ast"]):
        disc = "RLX"
        fine = "RLX-sweep" if out["sweep_probes"] >= TH["rlx_min_probes"] else "RLX-repush"
    elif n_diff >= TH["rng_min_probes"]:
        disc = "RND"
    elif g_diff >= TH["goal_min_pairs"]:
        disc = "HEU"
    elif ((out["p_mono"] or 0) >= TH["lev_p_mono"] and (out["level_cover"] or 0) >= TH["lev_cover"] and
          (out["restarts_E"] or 0) == 0 and (out["revisit_share"] or 0) <= TH["lev_revisit"]) or \
            (container == "ARR" and (out["lev_assign_p_mono"] or 0) >= TH["lev_p_mono"] and
             (out["revisit_share"] or 0) <= 0.5):
        disc = "LEV"
    elif (out["p_lifo"] or 0) >= TH["dfs_p_lifo"]:
        disc = "DFS"
    elif out["coord_share"] >= TH["crd_share"] and n_nondet == 0:
        disc = "CRD"
    else:
        disc = "OTHER"
    out.update({"disc": disc, "cont": container, "fine": fine or disc, "seconds": round(time.time() - t0, 2)})
    return out


def measure_worker(item: tuple[str, str]) -> tuple[str, dict[str, Any]]:
    key, code = item
    try:
        return key, measure(code)
    except Exception as e:  # noqa: BLE001 - one bad program must not stop a batch
        return key, {"disc": "OTHER", "cont": "NONE", "fine": "INSTRUMENT_ERROR", "reason": f"{type(e).__name__}: {e}"}


def bfs_dist_of(grid: list[str], s: tuple[int, int]) -> dict:
    return bfs_dist(grid, s)


if __name__ == "__main__":
    code = Path(sys.argv[1]).read_text()
    r = measure(code)
    print(json.dumps({k: v for k, v in r.items()}, indent=1, default=str))
