#!/usr/bin/env python3
"""Expansion-order tracer v9 -- PARENT side (plan 1.3-1.6): run the child (src/tracer_v9.py) on the 40 probes, build
the expansion record E per probe, compute the per-probe order statistics and assign the program's order class with
the committed decision list. Names never enter: the class is computed from runtime events only.

Expansion record. Candidates are container pops/iterations (POP, ITER) and calls (CALL) carrying a cell; consecutive
candidates on the same cell merge. A candidate is CONFIRMED if, before the next candidate, a READ or PUSH touches a
4-neighbour of its cell, or the next candidate is a 4-neighbour of it. Two silent-expansion rules keep real
expansions that touch nothing (dead ends whose neighbours were all filtered before any read): an unconfirmed POP of
a cell earlier pushed into the same container and not yet expanded, and an unconfirmed self-recursive CALL on a cell
not yet expanded. E = the confirmed container stream if it has >= 3 entries, else the confirmed call stream, else the
centres of READ bursts (flagged scan-derived). Restarts for the ID rule are counted on the merged stream.
"""

from __future__ import annotations

import json
import math
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CHILD = ROOT / "src" / "tracer_v9.py"
PROBES_FILE = ROOT / "probes" / "probes_v9.json"
SANDBOX_PY = "/usr/local/bin/python3.12" if Path("/usr/local/bin/python3.12").exists() else sys.executable

# Committed thresholds (commit #1a; the gate may revise ONLY the three marked REVISABLE)
TH = {"informative_min_E": 6, "min_informative": 10,           # REVISABLE: min_informative 10 -> 6
      "id_share": 0.5, "id_min_restarts": 2, "id_strict_share": 0.8, "raster_max_for_id": 0.7,
      "bidir_share": 0.5, "bidir_first_k": 4, "bidir_goal_share": 0.2,
      "bfs_p_mono": 0.98, "bfs_level_cover": 0.98,             # REVISABLE: level_cover cut-off
      "heur_rho": 0.6, "heur_c": 0.9,                          # REVISABLE: c_f / c_h cut-off
      "dfs_p_lifo": 0.9, "dfs_revisit": 0.1, "jump_share": 0.5, "fifo": 0.98, "raster_share": 0.7,
      "probe_timeout_s": 2.0, "program_timeout_s": 90.0, "max_crash_probes": 20, "c_max_steps": 2500}
COARSE_OF_FINE = {"BFS": "BFS", "DFS": "DFS", "DFS-revisit": "DFS", "ID-depth": "ID", "ID-f": "ID",
                  "BIDIR-BFS": "BIDIR", "BIDIR-heuristic": "BIDIR", "HEUR-f": "HEUR", "HEUR-h": "HEUR",
                  "HEUR-jump": "HEUR", "HEUR-weak": "HEUR", "OTHER-revisit": "OTHER", "OTHER-raster": "OTHER",
                  "OTHER-random-priority": "OTHER", "OTHER-unknown": "OTHER", "UNTRACEABLE": "UNTRACEABLE"}
CONFIRM_FIRST_K = 4        # a candidate is confirmed by a 4-neighbour among the first 4 READ/PUSH events on other cells
FRONTIER_SRC = ("heap", "deque.popleft", "deque.pop", "list.pop", "list.pop0", "list.popi", "queue.get",
                "lifo.get", "pq.get", "set.pop", "set.remove", "set.discard", "dict.pop", "dict.popitem")


# ---------------------------------------------------------------------------------------------- probes
@lru_cache(maxsize=1)
def probes() -> list[dict[str, Any]]:
    return json.loads(PROBES_FILE.read_text())["probes"]


@lru_cache(maxsize=1)
def probe_pre() -> list[dict[str, Any]]:
    from probes_v9 import precompute

    return [precompute(p) for p in probes()]


def nb4(c: tuple[int, int]) -> tuple[tuple[int, int], ...]:
    r, k = c
    return ((r - 1, k), (r + 1, k), (r, k - 1), (r, k + 1))


def adj(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1


# ---------------------------------------------------------------------------------------------- running the child
def run_child(code: str, timeout_s: float | None = None) -> dict[str, Any]:
    """Run the child on all probes, restarting it after a probe timeout on the remaining probes."""
    import time

    pr = probes()
    recs: dict[int, dict[str, Any]] = {}
    err = None
    first = 0
    t_end = time.time() + (timeout_s or TH["program_timeout_s"])
    n_restarts = 0
    while first < len(pr):
        job = {"code": code, "probes": pr, "first": first, "probe_timeout_s": TH["probe_timeout_s"],
               "rlimit_as": 1024 ** 3}
        left = t_end - time.time()
        if left <= 1:
            err = err or "program_timeout"
            break
        try:
            proc = subprocess.run([SANDBOX_PY, "-I", "-S", str(CHILD)], input=json.dumps(job), capture_output=True,
                                  text=True, timeout=min(left, TH["probe_timeout_s"] * (len(pr) - first) + 15))
            out = proc.stdout
        except subprocess.TimeoutExpired as e:
            out = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
            err = err or "child_timeout"
        last_i = first - 1
        done = False
        for ln in out.splitlines():
            if not ln.startswith("{"):
                continue
            try:
                d = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if "error" in d:
                return {"error": d["error"], "probes": recs}
            if d.get("done"):
                done = True
                continue
            recs[d["i"]] = d
            last_i = max(last_i, d["i"])
        if done:
            break
        if last_i < first:                 # crashed before finishing probe `first`
            recs[first] = {"i": first, "events": [], "strings": ["read"], "valid": False, "exc": "child_crash",
                           "timeout": False, "seconds": None, "grid_copied": False, "truncated": False}
            last_i = first
        first = last_i + 1
        n_restarts += 1
        if n_restarts > 45:
            err = "too_many_restarts"
            break
    return {"error": err, "probes": recs}


# ---------------------------------------------------------------------------------------------- expansion record
def _stream(events: list[list[Any]], strings: list[str], kinds: tuple[int, ...]) -> list[dict[str, Any]]:
    """Confirmed candidates of one stream (kinds = candidate event types), after merging consecutive same-cell
    candidates. Each entry: cell, ev (event index of the first occurrence), src, prio, confirmed, silent."""
    cand_idx = [i for i, e in enumerate(events) if e[0] in kinds]
    merged: list[list[int]] = []
    for i in cand_idx:
        c = (events[i][1], events[i][2])
        if merged and (events[merged[-1][0]][1], events[merged[-1][0]][2]) == c:
            merged[-1].append(i)
        else:
            merged.append([i])
    out: list[dict[str, Any]] = []
    expanded: set[tuple[int, int]] = set()
    pushed_by_cont: dict[int, set[tuple[int, int]]] = defaultdict(set)
    ptr = 0                                   # event pointer for push bookkeeping
    for j, grp in enumerate(merged):
        a = grp[0]
        b = merged[j + 1][0] if j + 1 < len(merged) else len(events)
        while ptr < a:
            e = events[ptr]
            if e[0] == 0:
                pushed_by_cont[e[4]].add((e[1], e[2]))
            ptr += 1
        e0 = events[a]
        cell = (e0[1], e0[2])
        nbs = set(nb4(cell))
        conf = False
        seen_other = 0
        for k in range(a + 1, b):
            e = events[k]
            if e[0] in (0, 2):
                c2 = (e[1], e[2])
                if c2 == cell:
                    continue
                if c2 in nbs:
                    conf = True
                    break
                seen_other += 1
                if seen_other >= CONFIRM_FIRST_K:
                    break
        if not conf and seen_other == 0 and j + 1 < len(merged):
            nx = events[merged[j + 1][0]]
            conf = (nx[1], nx[2]) in nbs
        src = strings[e0[3]] if e0[3] < len(strings) else "?"
        silent = False
        if not conf and cell not in expanded:
            if e0[0] == 1 and cell in pushed_by_cont.get(e0[4], ()):
                silent = True
            elif e0[0] == 3 and src.endswith("<self"):
                silent = True
        if conf or silent:
            out.append({"cell": cell, "ev": a, "src": src, "prio": e0[5], "silent": silent})
            expanded.add(cell)
    return out


def _bursts(events: list[list[Any]]) -> list[dict[str, Any]]:
    """Scan-derived expansions: centres of maximal runs of consecutive READs whose closed 4-neighbourhoods share a
    common cell, with >= 2 distinct cells read."""
    out: list[dict[str, Any]] = []
    run_cells: list[tuple[int, int]] = []
    cset: set[tuple[int, int]] | None = None
    start_ev = 0

    def close() -> None:
        if cset and len(set(run_cells)) >= 2:
            cands = sorted(cset, key=lambda x: (x not in run_cells, run_cells.index(x) if x in run_cells else 0, x))
            c = cands[0]
            if not out or out[-1]["cell"] != c:
                out.append({"cell": c, "ev": start_ev, "src": "scan", "prio": None, "silent": False})

    for i, e in enumerate(events):
        if e[0] != 2:
            continue
        c = (e[1], e[2])
        closed = {c, *nb4(c)}
        if cset is None:
            cset, run_cells, start_ev = closed, [c], i
            continue
        inter = cset & closed
        if inter:
            cset = inter
            run_cells.append(c)
        else:
            close()
            cset, run_cells, start_ev = closed, [c], i
    close()
    return out


def expansion_record(rec: dict[str, Any]) -> dict[str, Any]:
    ev = rec.get("events") or []
    st = rec.get("strings") or ["read"]
    e_pop = _stream(ev, st, (1,))
    e_iter = _stream(ev, st, (4,)) if len(e_pop) < 3 else []
    e_call = _stream(ev, st, (3,))
    n_self = sum(1 for e in ev if e[0] == 3 and e[3] < len(st) and st[e[3]].endswith("<self"))
    if n_self >= 3 and len(e_call) >= 3:     # a recursive search: its calls are the expansions (container
        E, source, mk = e_call, "call", (3,)  # removals in it are backtracking, not frontier pops)
    elif len(e_pop) >= 3:
        E, source, mk = e_pop, "container", (1, 3)
    elif len(e_iter) >= 3:
        E, source, mk = e_iter, "iteration", (4, 3)
    elif len(e_call) >= 3:
        E, source, mk = e_call, "call", (3,)
    else:
        E, source, mk = _bursts(ev), "scan", None
    e_m = _stream(ev, st, mk) if mk else E
    return {"E": E, "source": source, "E_merged": e_m, "n_pop": len(e_pop), "n_call": len(e_call),
            "n_iter": len(e_iter)}


# ---------------------------------------------------------------------------------------------- statistics
def _spearman(x: list[float], y: list[float]) -> float | None:
    n = len(x)
    if n < 3:
        return None

    def ranks(v: list[float]) -> list[float]:
        order = sorted(range(n), key=lambda i: v[i])
        rk = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                rk[order[k]] = (i + j) / 2.0
            i = j + 1
        return rk

    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den > 0 else None


def _passes(seq: list[tuple[int, int]], root: tuple[int, int]) -> list[list[tuple[int, int]]]:
    out: list[list[tuple[int, int]]] = []
    for c in seq:
        if c == root or not out:
            out.append([c])
        else:
            out[-1].append(c)
    return out


def _growing(b: list[float]) -> tuple[bool, float | None]:
    """Nondecreasing with a strict increase in >= 80% of transitions (>= 2 transitions)."""
    if len(b) < 3:
        return False, None
    tr = [y - x for x, y in zip(b, b[1:])]
    if any(t < 0 for t in tr):
        return False, None
    share = sum(1 for t in tr if t > 0) / len(tr)
    return share >= TH["id_strict_share"], statistics.median(tr)


def _raster_share(seq: list[tuple[int, int]]) -> float | None:
    if len(seq) < 3:
        return None
    n = sum(1 for a, b in zip(seq, seq[1:]) if (b[0] == a[0] and b[1] > a[1]) or (b[0] == a[0] + 1 and b[1] < a[1]))
    return n / (len(seq) - 1)


def probe_stats(rec: dict[str, Any], pi: int) -> dict[str, Any]:
    pre = probe_pre()[pi]
    xr = expansion_record(rec)
    E = xr["E"]
    seq = [x["cell"] for x in E]
    out: dict[str, Any] = {"i": pi, "name": probes()[pi]["name"], "family": probes()[pi]["family"],
                           "n_E": len(seq), "source": xr["source"], "n_pop": xr["n_pop"], "n_call": xr["n_call"],
                           "valid": rec.get("valid"), "exc": rec.get("exc"), "timeout": rec.get("timeout"),
                           "truncated": rec.get("truncated"), "grid_copied": rec.get("grid_copied"),
                           "n_events": len(rec.get("events") or []), "n_silent": sum(1 for x in E if x["silent"])}
    out["informative"] = len(seq) >= TH["informative_min_E"]
    if not seq:
        out["seq"] = []
        return out
    s, t = pre["s"], pre["t"]
    root = seq[0]
    swap = (root == t and root != s)
    d_root = pre["d_t"] if swap else pre["d_s"]
    tgt = s if swap else t
    d_other = pre["d_s"] if swap else pre["d_t"]

    def h(c: tuple[int, int]) -> int:
        return abs(c[0] - tgt[0]) + abs(c[1] - tgt[1])

    out["root"] = list(root)
    out["root_is_goal"] = swap
    # unique first-occurrence sequence
    seen: set[tuple[int, int]] = set()
    uniq: list[int] = []                   # indices into E
    for i, c in enumerate(seq):
        if c not in seen:
            seen.add(c)
            uniq.append(i)
    useq = [seq[i] for i in uniq]
    useq_r = [c for c in useq if c in d_root]
    # restarts (on E and on the merged stream)
    out["n_restart_E"] = sum(1 for c in seq[1:] if c == root)
    m_seq = [x["cell"] for x in xr["E_merged"]]
    m_root = m_seq[0] if m_seq else root
    m_passes = _passes(m_seq, m_root) if m_seq else []
    out["n_restart_M"] = max(0, len(m_passes) - 1)
    if (rec.get("timeout") or rec.get("truncated")) and len(m_passes) > 1:
        m_passes = m_passes[:-1]                       # the last pass of a timed-out / capped probe is incomplete
    bd = [max((d_root.get(c, 0) for c in p), default=0) for p in m_passes]
    bf = [max((d_root.get(c, 0) + h(c) for c in p), default=0) for p in m_passes]
    out["pass_bound_d"] = bd[:60]
    out["pass_bound_f"] = bf[:60]
    rs_m = _raster_share(m_seq)
    out["raster_share_M"] = rs_m
    id_probe, fine_id = False, None
    if out["n_restart_M"] >= TH["id_min_restarts"] and (rs_m is None or rs_m < TH["raster_max_for_id"]):
        d_ok = [b for b in (bd, bd[1:]) if _growing(b)[0]]
        f_ok = [b for b in (bf, bf[1:]) if _growing(b)[0]]
        if d_ok or f_ok:
            id_probe = True
            # ID-depth if the pass max d_root grows by 1 (>= 80% of the transitions are +1), else ID-f
            unit = any(sum(1 for x, y in zip(b, b[1:]) if y - x == 1) >= 0.8 * (len(b) - 1) for b in d_ok)
            fine_id = "ID-depth" if unit else "ID-f"
    out["id_probe"] = id_probe
    out["id_fine"] = fine_id
    # p_mono, rho_h
    pm = [(1 if d_root[b] >= d_root[a] else 0) for a, b in zip(useq_r, useq_r[1:])]
    out["p_mono_k"], out["p_mono_n"] = sum(pm), len(pm)
    out["rho_h"] = _spearman(list(range(len(useq))), [-h(c) for c in useq])
    # level_cover
    first_idx = {c: k for k, c in enumerate(useq)}
    if useq_r:
        Lmax = max(d_root[c] for c in useq_r)
        by_level: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for c, d in d_root.items():
            by_level[d].append(c)
        cov_k = cov_n = 0
        for L in range(0, Lmax - 1):
            nxt = [first_idx[c] for c in by_level.get(L + 1, []) if c in first_idx]
            if not nxt:
                continue
            tf = min(nxt)
            cells = by_level.get(L, [])
            cov_n += len(cells)
            cov_k += sum(1 for c in cells if c in first_idx and first_idx[c] < tf)
        out["cover_k"], out["cover_n"] = cov_k, cov_n
    else:
        out["cover_k"], out["cover_n"] = 0, 0
    # pushes per E window -> discovering parents, open list F
    events = rec.get("events") or []
    ev_of = [E[i]["ev"] for i in uniq]
    first_push: dict[tuple[int, int], int] = {}
    push_seq: list[tuple[int, tuple[int, int]]] = []
    for k, e in enumerate(events):
        if e[0] == 0:
            c = (e[1], e[2])
            push_seq.append((k, c))
            if c not in first_push:
                first_push[c] = k
    import bisect

    def parent_of(c: tuple[int, int], pos: int) -> int | None:
        fp = first_push.get(c)
        if fp is not None:
            j = bisect.bisect_right(ev_of, fp) - 1
            if 0 <= j < pos:
                return j
        best = None
        for nb in nb4(c):
            k = first_idx.get(nb)
            if k is not None and k < pos and (best is None or k < best):
                best = k
        return best

    parents = [parent_of(c, k) if k > 0 else None for k, c in enumerate(useq)]
    # fifo within levels
    fk = fn = 0
    lv: dict[int, list[int]] = defaultdict(list)
    for k, c in enumerate(useq):
        if k > 0 and c in d_root and parents[k] is not None:
            lv[d_root[c]].append(k)
    for L, ks in lv.items():
        for x in range(len(ks)):
            for y in range(x + 1, len(ks)):
                fn += 1
                fk += int(parents[ks[x]] <= parents[ks[y]])
    out["fifo_k"], out["fifo_n"] = fk, fn
    # jump share
    jk = jn = 0
    for k in range(1, len(useq)):
        p = parents[k]
        if p is None or useq[k] not in first_push:
            continue
        jn += 1
        a, b = useq[p], useq[k]
        jk += int((not adj(a, b)) and (a[0] == b[0] or a[1] == b[1]))
    out["jump_k"], out["jump_n"] = jk, jn
    # c_g, c_f, c_h over the open list F (pushed, not yet expanded); if no pushes: open unexpanded neighbours
    has_push = bool(push_seq)
    cg = cf = ch = cn = 0
    F: set[tuple[int, int]] = set()
    expanded: set[tuple[int, int]] = set()
    pp = 0
    free = pre["free"]
    for k in range(len(useq)):
        if k >= TH["c_max_steps"]:
            break
        e_at = ev_of[k]
        if has_push:
            while pp < len(push_seq) and push_seq[pp][0] < e_at:
                c = push_seq[pp][1]
                if c not in expanded and c in d_root:
                    F.add(c)
                pp += 1
        x = useq[k]
        if k > 0 and len(F) >= 2 and x in d_root:      # a step counts only when the open list offers a choice
            cn += 1
            if x in F:
                dmin = min(d_root[c] for c in F)
                fmin = min(d_root[c] + h(c) for c in F)
                hmin = min(h(c) for c in F)
                cg += int(d_root[x] == dmin)
                cf += int(d_root[x] + h(x) == fmin)
                ch += int(h(x) == hmin)
        expanded.add(x)
        F.discard(x)
        if not has_push:
            for nb in nb4(x):
                if nb in free and nb not in expanded and nb in d_root:
                    F.add(nb)
    out.update({"cg_k": cg, "cf_k": cf, "ch_k": ch, "c_n": cn})
    # p_lifo on the full E: a simulated path stack (pop until the top is adjacent to the next expansion); a step is
    # LIFO-consistent if the next expansion is adjacent to a cell left on the stack (descend or backtrack-then-
    # descend) or is the most recently pushed open cell; immediate reversals (x == e[t-2]) never count; a root
    # re-expansion resets the stack.
    lk = ln = 0
    stack: list[tuple[int, int]] = []
    exp_set: set[tuple[int, int]] = set()
    last_push: dict[tuple[int, int], int] = {}
    pp = 0
    psorted = push_seq
    for k in range(len(seq)):
        x = seq[k]
        if k > 0 and x == root:
            stack = [x]
            exp_set.add(x)
            continue
        if k > 0:
            ln += 1
            ok = not (k >= 2 and x == seq[k - 2])
            if ok:
                cond_b = False
                if has_push:
                    e_at = E[k]["ev"]
                    while pp < len(psorted) and psorted[pp][0] < e_at:
                        last_push[psorted[pp][1]] = psorted[pp][0]
                        pp += 1
                    openp = [(v, c) for c, v in last_push.items() if c not in exp_set]
                    if openp:
                        cond_b = max(openp)[1] == x
                j = len(stack) - 1
                while j >= 0 and not adj(stack[j], x):
                    j -= 1
                cond_a = j >= 0
                if cond_a:
                    del stack[j + 1:]
                lk += int(cond_a or cond_b)
                if not cond_a:
                    stack = []
            else:
                stack = []
        exp_set.add(x)
        stack.append(x)
    out["lifo_k"], out["lifo_n"] = lk, ln
    # bidirectional
    first4 = useq[:TH["bidir_first_k"]]
    near_goal = sum(1 for c in useq if c in d_other and c in d_root and d_other[c] < d_root[c])
    out["bidir"] = bool(s in first4 and t in first4 and useq and near_goal / len(useq) >= TH["bidir_goal_share"])
    # revisits within passes (E), raster share (E)
    rv = 0
    for p in _passes(seq, root):
        cnt = Counter(p)
        rv += sum(v - 1 for v in cnt.values())
    out["revisit_share"] = rv / len(seq)
    out["raster_share"] = _raster_share(seq)
    # heap priority key (DS signature)
    pr_list = [(x["prio"], x["cell"]) for x in E if x["src"] in ("heap", "pq.get") and x["prio"] is not None]
    if len(pr_list) >= 5:
        pv = [p for p, _ in pr_list]
        cells = [c for _, c in pr_list]
        rd = _spearman(pv, [d_root.get(c, 0) for c in cells])
        rh = _spearman(pv, [h(c) for c in cells])
        rf = _spearman(pv, [d_root.get(c, 0) + h(c) for c in cells])
        mono = all(b > a for a, b in zip(pv, pv[1:]))
        out["key_corr"] = {"g": rd, "h": rh, "g+h": rf, "strictly_increasing": mono}
    out["src_counts"] = dict(Counter(x["src"].split("<")[0] for x in E))
    # duplicate frontier pushes (visited-at-pop) and relaxation re-pushes with a smaller key
    fr_push: dict[tuple[int, int], list[float | None]] = defaultdict(list)
    for e in events:
        if e[0] == 0 and e[3] < len(rec.get("strings") or []) and (rec["strings"][e[3]] in ("heap", "list.append",
                                                                                           "deque.append",
                                                                                           "deque.appendleft",
                                                                                           "deque.init")):
            fr_push[(e[1], e[2])].append(e[5])
    out["dup_push_share"] = (sum(1 for v in fr_push.values() if len(v) > 1) / len(fr_push)) if fr_push else None
    out["relax_repush"] = any(len(v) > 1 and all(x is not None for x in v) and min(v[1:]) < v[0]
                              for v in fr_push.values())
    comp = len(d_root)
    out["expanded_share"] = len([c for c in useq if c in d_root]) / comp if comp else None
    out["seq"] = [list(c) for c in seq[:3000]]
    return out


# ---------------------------------------------------------------------------------------------- classification
def _pool(stats: list[dict[str, Any]], k: str, n: str) -> float | None:
    a = sum(s.get(k, 0) for s in stats)
    b = sum(s.get(n, 0) for s in stats)
    return a / b if b else None


def classify(stats: list[dict[str, Any]], th: dict[str, Any] | None = None) -> dict[str, Any]:
    th = th or TH
    inf = [s for s in stats if s.get("informative")]
    out: dict[str, Any] = {"n_informative": len(inf), "n_probes": len(stats)}
    n_crash = sum(1 for s in stats if s.get("exc"))          # exceptions only; a timed-out probe keeps its
    out["n_crash"] = n_crash                                  # partial (flagged) expansion record
    out["n_timeout"] = sum(1 for s in stats if s.get("timeout"))
    if len(inf) < th["min_informative"] or n_crash > th["max_crash_probes"]:
        out.update({"order_class": "UNTRACEABLE", "order_class_fine": "UNTRACEABLE",
                    "reason": "crash on > 20 probes" if n_crash > th["max_crash_probes"] else
                    f"only {len(inf)} informative probes"})
        return out
    id_share = sum(1 for s in inf if s.get("id_probe")) / len(inf)
    bidir_share = sum(1 for s in inf if s.get("bidir")) / len(inf)
    p_mono = _pool(inf, "p_mono_k", "p_mono_n")
    cover = _pool(inf, "cover_k", "cover_n")
    restarts_E = sum(s.get("n_restart_E", 0) for s in inf)
    rhos = [s["rho_h"] for s in inf if s.get("rho_h") is not None]
    rho_med = statistics.median(rhos) if rhos else None
    c_f = _pool(inf, "cf_k", "c_n")
    c_h = _pool(inf, "ch_k", "c_n")
    c_g = _pool(inf, "cg_k", "c_n")
    p_lifo = _pool(inf, "lifo_k", "lifo_n")
    fifo = _pool(inf, "fifo_k", "fifo_n")
    jump = _pool(inf, "jump_k", "jump_n")
    revisit = statistics.mean(s.get("revisit_share", 0) for s in inf)
    rasters = [s["raster_share"] for s in inf if s.get("raster_share") is not None]
    raster = statistics.median(rasters) if rasters else None
    out.update({"id_share": id_share, "bidir_share": bidir_share, "p_mono": p_mono, "level_cover": cover,
                "restarts_E": restarts_E, "rho_h_median": rho_med, "c_f": c_f, "c_h": c_h, "c_g": c_g,
                "p_lifo": p_lifo, "fifo": fifo, "jump_share": jump, "revisit_share": revisit,
                "raster_share_median": raster,
                "sources": dict(Counter(s.get("source") for s in inf))})
    fine = None
    if id_share >= th["id_share"]:
        fines = Counter(s.get("id_fine") for s in inf if s.get("id_probe"))
        fine = "ID-depth" if fines.get("ID-depth", 0) >= fines.get("ID-f", 0) else "ID-f"
        rule = 1
    elif bidir_share >= th["bidir_share"]:
        rule = 2
        heapish = sum(s.get("src_counts", {}).get("heap", 0) + s.get("src_counts", {}).get("pq.get", 0)
                      for s in inf) > 0.5 * sum(sum(s.get("src_counts", {}).values()) for s in inf)
        fine = "BIDIR-heuristic" if (heapish or (rho_med is not None and rho_med >= th["heur_rho"] and
                                                 (c_f or 0) >= 0.5)) else "BIDIR-BFS"
    elif (p_mono or 0) >= th["bfs_p_mono"] and (cover or 0) >= th["bfs_level_cover"] and restarts_E == 0:
        rule, fine = 3, "BFS"
    elif rho_med is not None and rho_med >= th["heur_rho"] and max(c_f or 0, c_h or 0) >= th["heur_c"]:
        rule = 4
        if jump is not None and jump >= th["jump_share"]:
            fine = "HEUR-jump"
        else:
            fine = "HEUR-f" if (c_f or 0) >= (c_h or 0) else "HEUR-h"
    elif (p_lifo or 0) >= th["dfs_p_lifo"]:
        rule = 5
        fine = "DFS-revisit" if revisit > th["dfs_revisit"] else "DFS"
    elif rho_med is not None and rho_med >= th["heur_rho"]:
        rule, fine = 6, "HEUR-weak"
    else:
        rule = 7
        kc = [s.get("key_corr") for s in inf if s.get("key_corr")]
        rand_key = bool(kc) and statistics.median(max(abs(k.get("g") or 0), abs(k.get("h") or 0),
                                                      abs(k.get("g+h") or 0)) for k in kc) < 0.3 and not any(
            k.get("strictly_increasing") for k in kc)
        if raster is not None and raster >= th["raster_share"]:
            fine = "OTHER-raster"
        elif revisit > th["dfs_revisit"]:
            fine = "OTHER-revisit"
        elif rand_key:
            fine = "OTHER-random-priority"
        else:
            fine = "OTHER-unknown"
    out.update({"order_class": COARSE_OF_FINE[fine], "order_class_fine": fine, "rule": rule,
                "fifo_flag": bool(fifo is not None and fifo >= th["fifo"])})
    out["ds_signature"] = ds_signature(inf)
    return out


def ds_signature(inf: list[dict[str, Any]]) -> dict[str, Any]:
    src = Counter()
    for s in inf:
        src.update(s.get("src_counts", {}))
    total = sum(src.values()) or 1
    groups = {"FIFO": sum(src.get(k, 0) for k in ("deque.popleft", "list.pop0", "queue.get")),
              "LIFO": sum(src.get(k, 0) for k in ("list.pop", "deque.pop", "lifo.get")),
              "heap": sum(src.get(k, 0) for k in ("heap", "pq.get")),
              "set/dict+min": sum(src.get(k, 0) for k in ("set.remove", "set.discard", "dict.pop", "list.popi",
                                                          "set.pop", "dict.popitem")),
              "iteration": src.get("iter", 0),
              "recursion": sum(v for k, v in src.items() if k.startswith("call:")),
              "none(scan)": src.get("scan", 0)}
    cont = max(groups, key=lambda k: groups[k]) if total else "none"
    kc = [s.get("key_corr") for s in inf if s.get("key_corr")]
    key = "none"
    if kc:
        med = {k: statistics.median([(x.get(k) or 0) for x in kc]) for k in ("g", "h", "g+h")}
        if any(x.get("strictly_increasing") for x in kc) and sum(bool(x.get("strictly_increasing")) for x in kc) > \
                len(kc) / 2:
            key = "counter"
        elif max(med.values()) >= 0.9:
            key = max(med, key=lambda k: (med[k], k == "g+h"))
        elif max(abs(v) for v in med.values()) < 0.3:
            key = "random"
        else:
            key = "mixed"
    dup = [s["dup_push_share"] for s in inf if s.get("dup_push_share") is not None]
    exp_open = [s["expanded_share"] for s in inf if s.get("family") in ("open", "open_centre") and
                s.get("expanded_share") is not None]
    return {"container": cont, "container_counts": {k: v for k, v in groups.items() if v},
            "key": key, "relaxation_repush": any(s.get("relax_repush") for s in inf),
            "visited": ("at-pop" if dup and statistics.median(dup) > 0.05 else "at-push") if dup else "n/a",
            "early_exit": (statistics.median(exp_open) < 0.95) if exp_open else None,
            "restarts": sum(1 for s in inf if s.get("n_restart_M", 0) > 0) >= 0.3 * len(inf),
            "bidirectional": sum(1 for s in inf if s.get("bidir")) >= 0.5 * len(inf)}


def relaxation_ast(code: str) -> bool:
    """AST relaxation pattern: a comparison with an addition on one side and a subscript on both sides
    (dist[v] > dist[u] + w)."""
    import ast

    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return False
    for n in ast.walk(tree):
        if isinstance(n, ast.Compare) and len(n.comparators) == 1:
            sides = [n.left, n.comparators[0]]
            has_add = any(isinstance(x, ast.BinOp) and isinstance(x.op, ast.Add) for x in sides)
            subs = sum(1 for x in sides for y in ast.walk(x) if isinstance(y, ast.Subscript) or (
                isinstance(y, ast.Call) and isinstance(y.func, ast.Attribute) and y.func.attr == "get"))
            if has_add and subs >= 2:
                return True
    return False


def trace_program(code: str | None, keep_seq: bool = False) -> dict[str, Any]:
    """Full pipeline for one program: child run -> per-probe stats -> class."""
    if not code:
        return {"order_class": "UNTRACEABLE", "order_class_fine": "UNTRACEABLE", "reason": "no code"}
    run = run_child(code)
    if run.get("error") and not run.get("probes"):
        return {"order_class": "UNTRACEABLE", "order_class_fine": "UNTRACEABLE", "reason": str(run["error"])}
    stats = []
    for i in range(len(probes())):
        rec = run["probes"].get(i)
        if rec is None:
            stats.append({"i": i, "name": probes()[i]["name"], "family": probes()[i]["family"], "n_E": 0,
                          "informative": False, "exc": "not_run", "timeout": False, "seq": []})
            continue
        try:
            stats.append(probe_stats(rec, i))
        except (KeyError, ValueError, IndexError, TypeError, ZeroDivisionError) as e:
            stats.append({"i": i, "name": probes()[i]["name"], "n_E": 0, "informative": False,
                          "exc": f"stats_error:{type(e).__name__}", "seq": []})
    cl = classify(stats)
    cl["relaxation_ast"] = relaxation_ast(code)
    if "ds_signature" in cl:
        cl["ds_signature"]["relaxation"] = bool(cl["ds_signature"]["relaxation_repush"] or cl["relaxation_ast"])
    cl["run_error"] = run.get("error")
    cl["n_valid_paths"] = sum(1 for s in stats if s.get("valid"))
    slim = []
    for s in stats:
        d = {k: v for k, v in s.items() if k != "seq"}
        if keep_seq:
            d["seq"] = s.get("seq", [])
        slim.append(d)
    cl["probes"] = slim
    return cl


def reclassify(rec: dict[str, Any] | None) -> dict[str, Any]:
    """Re-derive the program class from cached per-probe statistics with the current thresholds TH."""
    if rec is None:
        return {"order_class": "UNTRACEABLE", "order_class_fine": "UNTRACEABLE", "reason": "not traced"}
    if not rec.get("probes"):
        return dict(rec)
    cl = classify(rec["probes"])
    for k in ("relaxation_ast", "run_error", "n_valid_paths", "probes", "ckey"):
        if k in rec:
            cl[k] = rec[k]
    if "ds_signature" in cl:
        cl["ds_signature"]["relaxation"] = bool(cl["ds_signature"]["relaxation_repush"] or rec.get("relaxation_ast"))
    return cl


def trace_worker(item: tuple[str, str | None, bool]) -> tuple[str, dict[str, Any]]:
    key, code, keep = item
    try:
        return key, trace_program(code, keep)
    except Exception as e:  # noqa: BLE001 - one bad program must not stop a batch
        return key, {"order_class": "UNTRACEABLE", "order_class_fine": "UNTRACEABLE",
                     "reason": f"tracer_exception:{type(e).__name__}:{e}"}
