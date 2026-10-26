#!/usr/bin/env python3
"""STEP 7 - distinct programs, idea clusters, adjudication.

DISTINCT (within an arm, in call order, over OOC_screen programs): identical normalised-token hashes merge, then a
program with Jaccard >= 0.9 to an earlier distinct representative collapses into it.
IDEA CLUSTERS (pooled over arms, before adjudication): within each cell (runtime label, DS-signature), single-linkage
components at Jaccard >= 0.5 over the distinct representatives; after adjudication, clusters whose judges named the
same algorithm merge (merged_cluster_id).
CANDIDATES: every distinct OOC_screen program; the judges see each cluster's medoid plus at most 2 extra members (the
most novel one and a random one); unshown members inherit their medoid's final class (flag 'propagated').
JUDGES (blind: arm and lineage hidden, order shuffled): mistralai/mistral-medium-3.1 + moonshotai/kimi-k2-0905,
each gated on 10 controls (>= 9 of 10); a failing judge is replaced from the pre-registered list. Third judge on
class disagreement. Manual read queue: every NOVEL call, every unresolved disagreement, 10% of each class.
"""

from __future__ import annotations

import asyncio
import json
import math
import random
from collections import Counter, defaultdict
from typing import Any

import numpy as np
from loguru import logger

from common import (CAP_USD, DATA, PRED, RESULTS, commit, read_json, read_jsonl, sha256_text, stable_seed, utc_now,
                    write_json)

JACC_DISTINCT = 0.9
JACC_CLUSTER = 0.5
CLASSES = ("NOVEL ALGORITHM", "KNOWN OUTSIDE CATALOGUE", "CATALOGUE VARIANT", "DEGENERATE")
CAND_P = DATA / "adjudication_candidates.json"
JUDGE_P = DATA / "judge_calls.jsonl"


# ------------------------------------------------------------------------------------------------ dedup + clusters
def _sets(codes: list[str]):
    from critic import shingle_ids, to_matrix
    ids = [shingle_ids(c) for c in codes]
    M = to_matrix(ids)
    sz = np.array([len(a) for a in ids], dtype=np.float32)
    inter = (M @ M.T).toarray()
    den = sz[:, None] + sz[None, :] - inter
    J = np.where(den > 0, inter / np.maximum(den, 1e-9), 1.0)
    return J


def norm_hash(code: str) -> str:
    from critic import norm_tokens
    return sha256_text(" ".join(norm_tokens(code)))


def dedup_and_cluster(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """rows: OOC_screen correct rows of ONE task (all arms). Returns id -> {distinct_id, is_first_of_distinct,
    cluster_id, medoid}."""
    out: dict[str, dict[str, Any]] = {}
    reps_by_arm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for arm in sorted({r["arm"] for r in rows}):
        rs = sorted([r for r in rows if r["arm"] == arm], key=lambda r: r["slot"])
        if not rs:
            continue
        J = _sets([r["code"] for r in rs])
        hmap: dict[str, str] = {}
        rep_idx: list[int] = []
        for i, r in enumerate(rs):
            h = norm_hash(r["code"])
            if h in hmap:
                out[r["id"]] = {"distinct_id": hmap[h], "is_first_of_distinct": False}
                continue
            if rep_idx:
                j = max(rep_idx, key=lambda k: J[i, k])
                if J[i, j] >= JACC_DISTINCT:
                    did = out[rs[j]["id"]]["distinct_id"]
                    hmap[h] = did
                    out[r["id"]] = {"distinct_id": did, "is_first_of_distinct": False}
                    continue
            hmap[h] = r["id"]
            rep_idx.append(i)
            out[r["id"]] = {"distinct_id": r["id"], "is_first_of_distinct": True}
            reps_by_arm[arm].append(r)
    reps = [r for a in reps_by_arm for r in reps_by_arm[a]]
    by_cell: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in reps:
        by_cell[r.get("cell") or "none"].append(r)
    for cell, rs in by_cell.items():
        J = _sets([r["code"] for r in rs])
        n = len(rs)
        parent = list(range(n))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        ii, jj = np.where(np.triu(J, 1) >= JACC_CLUSTER)
        for a, b in zip(ii.tolist(), jj.tolist()):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
        comps: dict[int, list[int]] = defaultdict(list)
        for k in range(n):
            comps[find(k)].append(k)
        for ci, (root, mem) in enumerate(sorted(comps.items(), key=lambda kv: min(rs[m]["slot"] for m in kv[1]))):
            cid = f"{rs[0]['task']}:{cell}:{ci}"
            if len(mem) == 1:
                med = mem[0]
            else:
                sub = J[np.ix_(mem, mem)]
                med = mem[int(np.argmax(sub.sum(1)))]
            for m in mem:
                out[rs[m]["id"]].update(cluster_id=cid, medoid=rs[med]["id"], cluster_size=len(mem))
    # duplicates inherit their representative's cluster
    for rid, rec in out.items():
        if "cluster_id" not in rec:
            rep = out.get(rec["distinct_id"], {})
            rec.update(cluster_id=rep.get("cluster_id"), medoid=rep.get("medoid"), cluster_size=rep.get("cluster_size"))
    return out


# ------------------------------------------------------------------------------------------------ complexity
def complexity_inputs(task: str) -> list[dict[str, Any]]:
    from inputs import gen_stress
    rng = random.Random(stable_seed(task, "complexity"))
    base = gen_stress(task, stable_seed(task, "complexity-base"))[0]["kwargs"]
    out = []
    for frac, tag in ((1 / 16, "n/16"), (1 / 4, "n/4"), (1.0, "n")):
        if task == "T03":
            n = max(1, int(2000 * frac))
            nums = [rng.randint(-10000, 10000) for _ in range(n)]
            kw = {"nums": nums, "k": rng.randint(1, n)}
            size = n
        elif task == "A3":
            n = max(1, int(20000 * frac))
            kw = {"height": [rng.randint(0, 100000) for _ in range(n)]}
            size = n
        else:
            n = max(2, int(100 * frac))
            m = max(1, int(600 * frac))
            edges = [[rng.randrange(n), rng.randrange(n), rng.randint(0, 100)] for _ in range(m)]
            kw = {"n": n, "edges": edges, "s": 0, "t": n - 1}
            size = n + m
        out.append({"tag": tag, "size": size, "kwargs": kw})
    _ = base
    return out


def _complexity_cases(task: str, obj: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from inputs import _stress_outputs
    ins = complexity_inputs(task)
    fast = obj["fastest_ref"]
    outs = _stress_outputs(task, {fast: obj["references"][fast]}, [{"kwargs": x["kwargs"]} for x in ins])
    ref_t = outs[fast]["times"]
    cases = [{"id": f"cx:{x['tag']}", "kw": json.dumps(x["kwargs"]), "exp": json.dumps(o), "lim": 10.0, "size": x["size"]}
             for x, o in zip(ins, outs[fast]["outputs"])]
    return cases, {"ref_times": ref_t, "sizes": [x["size"] for x in ins]}


def empirical_complexity(task: str, code: str, cases: list[dict[str, Any]], ref: dict[str, Any]) -> dict[str, Any]:
    from sandbox import prescreen, run_stages
    ok, why = prescreen(code)
    if not ok:
        return {"error": f"prescreen:{why}"}
    stages = [[dict(c, id=f"{c['id']}#{rep}") for c in cases] for rep in range(3)]
    r = run_stages(task, code, stages)
    res = []
    for k, c in enumerate(cases):
        ts = [r["times"][rep][k] for rep in range(3) if r["status"][rep][k] == "ok" and r["times"][rep][k] is not None]
        st = r["status"][0][k]
        res.append({"size": c["size"], "status": st, "median_s": float(np.median(ts)) if ts else None,
                    "ratio_to_fastest_ref": (float(np.median(ts)) / max(ref["ref_times"][k], 1e-6)) if ts else None})
    xs = [math.log(x["size"]) for x in res if x["median_s"]]
    ys = [math.log(max(x["median_s"], 1e-7)) for x in res if x["median_s"]]
    slope = float(np.polyfit(xs, ys, 1)[0]) if len(xs) >= 2 else None
    return {"points": res, "loglog_slope": slope}


def stress_text(cx: dict[str, Any]) -> str:
    if not cx or "points" not in cx:
        return f"(not available: {cx.get('error') if cx else 'none'})"
    lines = []
    for p in cx["points"]:
        rr = f"{p['ratio_to_fastest_ref']:.2f}" if p["ratio_to_fastest_ref"] is not None else "n/a"
        lines.append(f"- size {p['size']}: {'pass' if p['status'] == 'ok' else 'FAIL (' + p['status'] + ')'}; "
                     f"runtime ratio to fastest reference {rr}")
    sl = cx.get("loglog_slope")
    lines.append(f"- log-log slope of runtime against input size: {sl:.2f}" if sl is not None else "- slope: n/a")
    return "\n".join(lines)


# ------------------------------------------------------------------------------------------------ controls
CONTROLS: list[dict[str, Any]] = [
    {"cid": "C1", "task": "T03", "expect": "CATALOGUE VARIANT", "must_pass": True, "code": '''
import random

def solve(nums, k):
    arr = list(nums)
    target = k - 1
    lo_i, hi_i = 0, len(arr) - 1
    while True:
        if lo_i == hi_i:
            return arr[lo_i]
        p = random.randint(lo_i, hi_i)
        arr[p], arr[hi_i] = arr[hi_i], arr[p]
        piv = arr[hi_i]
        store = lo_i
        for z in range(lo_i, hi_i):
            if arr[z] < piv:
                arr[store], arr[z] = arr[z], arr[store]
                store += 1
        arr[store], arr[hi_i] = arr[hi_i], arr[store]
        if target == store:
            return arr[store]
        if target < store:
            hi_i = store - 1
        else:
            lo_i = store + 1
'''},
    {"cid": "C2", "task": "T03", "expect": "KNOWN OUTSIDE CATALOGUE", "must_pass": True, "code": '''
import math

def _select(a, left, right, k):
    while right > left:
        if right - left > 600:
            n = right - left + 1
            i = k - left + 1
            z = math.log(n)
            s = 0.5 * math.exp(2 * z / 3)
            sd = 0.5 * math.sqrt(z * s * (n - s) / n) * (1 if i - n / 2 >= 0 else -1)
            new_left = max(left, int(k - i * s / n + sd))
            new_right = min(right, int(k + (n - i) * s / n + sd))
            _select(a, new_left, new_right, k)
        t = a[k]
        i, j = left, right
        a[left], a[k] = a[k], a[left]
        if a[right] > t:
            a[right], a[left] = a[left], a[right]
        while i < j:
            a[i], a[j] = a[j], a[i]
            i += 1
            j -= 1
            while a[i] < t:
                i += 1
            while a[j] > t:
                j -= 1
        if a[left] == t:
            a[left], a[j] = a[j], a[left]
        else:
            j += 1
            a[j], a[right] = a[right], a[j]
        if j <= k:
            left = j + 1
        if k <= j:
            right = j - 1
    return a[k]

def solve(nums, k):
    a = list(nums)
    return _select(a, 0, len(a) - 1, k - 1)
'''},
    {"cid": "C3", "task": "T03", "expect": "KNOWN OUTSIDE CATALOGUE", "must_pass": True, "code": '''
def solve(nums, k):
    lo, hi = min(nums), max(nums)
    while lo < hi:
        mid = (lo + hi) // 2
        cnt = sum(1 for x in nums if x <= mid)
        if cnt >= k:
            hi = mid
        else:
            lo = mid + 1
    return lo
'''},
    {"cid": "C4", "task": "T03", "expect": "DEGENERATE", "must_pass": False, "code": None},
    {"cid": "C5", "task": "T2", "expect": "KNOWN OUTSIDE CATALOGUE", "must_pass": True, "code": '''
from collections import deque

def solve(n, edges, s, t):
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    INF = float("inf")
    dist = [INF] * n
    state = [0] * n  # 0 never queued, 1 in queue, 2 was queued before
    dist[s] = 0
    dq = deque([s])
    state[s] = 1
    while dq:
        u = dq.popleft()
        state[u] = 2
        for v, w in adj[u]:
            nd = dist[u] + w
            if nd < dist[v]:
                dist[v] = nd
                if state[v] == 0:
                    dq.append(v)
                    state[v] = 1
                elif state[v] == 2:
                    dq.appendleft(v)
                    state[v] = 1
    return dist[t] if dist[t] < INF else -1
'''},
    {"cid": "C6", "task": "T2", "expect": "CATALOGUE VARIANT", "must_pass": True, "code": '''
class MinHeap:
    def __init__(self):
        self.a = []

    def push(self, item):
        a = self.a
        a.append(item)
        i = len(a) - 1
        while i > 0:
            p = (i - 1) // 2
            if a[p] <= a[i]:
                break
            a[p], a[i] = a[i], a[p]
            i = p

    def pop(self):
        a = self.a
        top = a[0]
        last = a.pop()
        if a:
            a[0] = last
            i = 0
            n = len(a)
            while True:
                l, r, m = 2 * i + 1, 2 * i + 2, i
                if l < n and a[l] < a[m]:
                    m = l
                if r < n and a[r] < a[m]:
                    m = r
                if m == i:
                    break
                a[m], a[i] = a[i], a[m]
                i = m
        return top

    def __len__(self):
        return len(self.a)

def solve(n, edges, s, t):
    g = [[] for _ in range(n)]
    for u, v, w in edges:
        g[u].append((v, w))
    best = [None] * n
    h = MinHeap()
    h.push((0, s))
    while len(h):
        d, u = h.pop()
        if best[u] is not None:
            continue
        best[u] = d
        if u == t:
            return d
        for v, w in g[u]:
            if best[v] is None:
                h.push((d + w, v))
    return -1
'''},
    {"cid": "C7", "task": "T2", "expect": "DEGENERATE", "must_pass": False, "code": '''
def solve(n, edges, s, t):
    if s == t:
        return 0
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    best = [-1]
    seen = [False] * n

    def walk(u, acc):
        if u == t:
            if best[0] < 0 or acc < best[0]:
                best[0] = acc
            return
        seen[u] = True
        for v, w in adj[u]:
            if not seen[v]:
                walk(v, acc + w)
        seen[u] = False
    walk(s, 0)
    return best[0]
'''},
    {"cid": "C8", "task": "A3", "expect": "KNOWN OUTSIDE CATALOGUE", "must_pass": True, "code": '''
def solve(height):
    n = len(height)
    if n < 3:
        return 0
    lg = [0] * (n + 1)
    for i in range(2, n + 1):
        lg[i] = lg[i // 2] + 1
    table = [list(height)]
    j = 1
    while (1 << j) <= n:
        prev = table[-1]
        half = 1 << (j - 1)
        table.append([max(prev[i], prev[i + half]) for i in range(n - (1 << j) + 1)])
        j += 1

    def range_max(l, r):
        k = lg[r - l + 1]
        return max(table[k][l], table[k][r - (1 << k) + 1])
    total = 0
    for i in range(1, n - 1):
        level = min(range_max(0, i), range_max(i, n - 1))
        total += level - height[i]
    return total
'''},
    {"cid": "C9", "task": "A3", "expect": "CATALOGUE VARIANT", "must_pass": True, "code": '''
def solve(height):
    pile = []
    acc = 0
    for pos, bar in enumerate(height):
        while pile and height[pile[-1]] < bar:
            floor_idx = pile.pop()
            if not pile:
                break
            wall = pile[-1]
            span = pos - wall - 1
            depth = min(height[wall], bar) - height[floor_idx]
            acc += span * depth
        pile.append(pos)
    return acc
'''},
    {"cid": "C10", "task": "A3", "expect": "KNOWN OUTSIDE CATALOGUE", "must_pass": True, "code": None},
]


def _c4_code(obj: dict[str, Any]) -> str:
    table = {}
    for c in obj["stages"]["quick"] + obj["stages"]["rest"]:
        kw = json.loads(c["kw"])
        table[repr((tuple(kw["nums"]), kw["k"]))] = json.loads(c["exp"])
    return ("ANSWERS = " + repr(table) + "\n\ndef solve(nums, k):\n    key = repr((tuple(nums), k))\n"
            "    if key in ANSWERS:\n        return ANSWERS[key]\n    return nums[0]\n")


def _c10_code() -> str:
    """Decreasing-height processing: visit bars from tallest to shortest, keep the leftmost and rightmost index seen
    so far; a newly visited bar outside [lo, hi] fills the gap between it and the span with its own height as level."""
    return '''
def solve(height):
    n = len(height)
    order = sorted(range(n), key=lambda i: (-height[i], i))
    lo = hi = order[0]
    total = 0
    for i in order[1:]:
        if i < lo:
            for j in range(i + 1, lo):
                total += height[i] - height[j]
            lo = i
        elif i > hi:
            for j in range(hi + 1, i):
                total += height[i] - height[j]
            hi = i
    return total
'''


def build_controls(objs: dict[str, dict[str, Any]], tasks: list[str]) -> list[dict[str, Any]]:
    from sandbox import evaluate
    out = []
    for c in CONTROLS:
        if c["task"] not in objs:
            continue
        code = c["code"]
        if c["cid"] == "C4":
            code = _c4_code(objs["T03"])
        if c["cid"] == "C10":
            code = _c10_code()
        ev = evaluate(objs[c["task"]], code)
        ok = ev["correct"] == c["must_pass"]
        out.append({**c, "code": code, "verified": ok, "correct": ev["correct"], "first_fail": ev["first_fail"]})
        if not ok:
            logger.error(f"control {c['cid']} does not behave as its class requires: {ev['first_fail']}")
    _ = tasks
    return out


# ------------------------------------------------------------------------------------------------ judging
def judge_text(obj: dict[str, Any], code: str, nearest: list[dict[str, Any]], cx: dict[str, Any], tmpl: str) -> str:
    from prompts import strip_code
    cat = "\n".join(f"- {c['display_name']}: {c['mechanism']}" for c in obj["catalogue"])
    nb = []
    for k, n in enumerate(nearest):
        body = "\n".join(strip_code(n["code"]).splitlines()[:60])
        nb.append(f"Known solution {k + 1} (source dataset: {n['dataset']}; token similarity {n['sim']:.2f}):\n"
                  f"```python\n{body}\n```")
    return tmpl.format(spec=obj["spec_body"], catalogue=cat, code=strip_code(code, 200), nearest="\n\n".join(nb),
                       stress=stress_text(cx))


def parse_class(text: str | None) -> dict[str, Any] | None:
    from orclient import parse_json_obj
    obj = parse_json_obj(text)
    if not obj:
        return None
    c = str(obj.get("class") or "").upper().strip()
    for k in CLASSES:
        if c.startswith(k) or k in c:
            obj["class"] = k
            return obj
    return None


async def _judge_batch(client, model: str, items: list[tuple[str, str]]) -> dict[str, dict[str, Any] | None]:
    async def one(key: str, prompt: str):
        r = await client.chat(model, [{"role": "user", "content": prompt}], temperature=0.0, max_tokens=500,
                              tag=f"adj:{key}")
        p = parse_class(r.get("text") if r else None)
        if p is None and r is not None and r.get("text") is not None:
            r2 = await client.chat(model, [{"role": "user", "content": prompt + "\n\nReturn valid JSON only."}],
                                   temperature=0.0, max_tokens=500, tag=f"adj2:{key}")
            p = parse_class(r2.get("text") if r2 else None)
        return key, p
    res = await asyncio.gather(*[one(k, p) for k, p in items])
    return dict(res)


def nearest_for(critic, code: str, task: str, row: dict[str, Any] | None) -> list[dict[str, Any]]:
    same = critic.nearest_same_task(code, task, k=2)
    out = [{"idx": i, "sim": s, "dataset": critic.meta[i]["dataset"], "id": critic.meta[i]["id"], "code": critic.code(i)}
           for i, s in same]
    if row and row.get("nearest_known_idx") is not None:
        gi = row["nearest_known_idx"]
        gs = row["nearest_known_sim"]
    else:
        sc = critic.score([code])[0]
        gi, gs = sc["nearest_idx"], sc["s"]
    if gi not in [x["idx"] for x in out]:
        out.append({"idx": gi, "sim": gs, "dataset": critic.meta[gi]["dataset"], "id": critic.meta[gi]["id"],
                    "code": critic.code(gi)})
    return out[:3]


def stage_adjudicate(tasks: list[str] | None = None) -> None:
    from critic import Critic
    from finalize import all_rows
    from inputs import load_task
    from orclient import ORClient
    c0 = read_json(PRED / "commit0.json")
    tmpl = c0["judge_prompt"]
    labs = {x["id"]: x for x in read_jsonl(DATA / "labels_final.jsonl")}
    rows = [r for r in all_rows() if labs.get(r["id"], {}).get("ooc_screen")]
    tasks = tasks or sorted({r["task"] for r in rows})
    objs = {t: load_task(t) for t in ("T2", "T03", "A3")}
    critic = Critic()
    prog = read_json(RESULTS / "program_classes.json") if (RESULTS / "program_classes.json").exists() else {}
    cands_all = read_json(CAND_P) if CAND_P.exists() else {"tasks": {}}
    for t in tasks:
        if t in cands_all["tasks"]:
            continue
        trs = [dict(r, **{"label": labs[r["id"]]["label"]}) for r in rows if r["task"] == t]
        if not trs:
            cands_all["tasks"][t] = {"n_ooc": 0, "clusters": {}, "shown": []}
            continue
        dc = dedup_and_cluster(trs)
        for rid, rec in dc.items():
            prog[rid] = {**prog.get(rid, {}), **rec}
        byc: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in trs:
            if dc[r["id"]]["is_first_of_distinct"]:
                byc[dc[r["id"]]["cluster_id"]].append(r)
        shown = []
        clusters = {}
        for cid, mem in byc.items():
            med = dc[mem[0]["id"]]["medoid"]
            others = [m for m in mem if m["id"] != med]
            extra = []
            if others:
                extra.append(max(others, key=lambda m: m.get("novelty") or 0)["id"])
                rest = [m["id"] for m in others if m["id"] not in extra]
                if rest:
                    extra.append(random.Random(stable_seed(t, cid)).choice(rest))
            clusters[cid] = {"medoid": med, "extras": extra, "members": [m["id"] for m in mem],
                             "arms": dict(Counter(m["arm"] for m in mem))}
            shown += [med] + extra
        cands_all["tasks"][t] = {"n_ooc": len(trs), "n_distinct": sum(1 for r in trs if dc[r["id"]]["is_first_of_distinct"]),
                                 "clusters": clusters, "shown": shown, "utc": utc_now()}
        write_json(RESULTS / "program_classes.json", prog)
    # budget: keep all medoids; drop extras if the judged set would exceed the adjudication cap
    est_per = 0.0040                     # two judges + a third on ~1/3 of candidates (measured on the gate)
    total = sum(len(cands_all["tasks"][t]["shown"]) for t in tasks)
    budget_n = int(CAP_USD["adjudication"] * 0.8 / est_per)
    if total > budget_n:
        # keep every medoid; keep extras of the largest clusters first while within the budget
        allc = [(t, cid, cl) for t in tasks for cid, cl in cands_all["tasks"][t]["clusters"].items()]
        room = budget_n - len(allc)
        keep_extra: set[tuple[str, str]] = set()
        for t, cid, cl in sorted(allc, key=lambda x: -len(x[2]["members"])):
            if cl["extras"] and len(cl["extras"]) <= room:
                keep_extra.add((t, cid))
                room -= len(cl["extras"])
        for t in tasks:
            ct = cands_all["tasks"][t]
            ct["shown"] = [x for cid, cl in ct["clusters"].items()
                           for x in [cl["medoid"]] + (cl["extras"] if (t, cid) in keep_extra else [])]
            ct["extras_dropped_for_small_clusters"] = True
        logger.warning(f"budget {budget_n}: {total} -> {sum(len(cands_all['tasks'][t]['shown']) for t in tasks)} shown "
                       f"(all medoids; extras kept for {len(keep_extra)} largest clusters)")
    controls = build_controls(objs, tasks)
    write_json(DATA / "controls.json", controls)
    write_json(CAND_P, cands_all)
    commit([CAND_P, DATA / "controls.json"], f"commit2:{','.join(tasks)}", "frozen candidates + controls before judges")
    # empirical complexity of shown candidates + controls
    rowmap = {r["id"]: r for r in rows}
    cx_cache_p = DATA / "complexity.json"
    cx = read_json(cx_cache_p) if cx_cache_p.exists() else {}
    from concurrent.futures import ThreadPoolExecutor
    for t in sorted(set(tasks) | {c["task"] for c in controls}):
        cases, ref = _complexity_cases(t, objs[t])
        items = [(i, rowmap[i]["code"]) for i in cands_all["tasks"].get(t, {}).get("shown", []) if i not in cx]
        items += [(c["cid"], c["code"]) for c in controls if c["task"] == t and c["cid"] not in cx]
        with ThreadPoolExecutor(8) as ex:
            res = list(ex.map(lambda kv: (kv[0], empirical_complexity(t, kv[1], cases, ref)), items))
        cx.update(dict(res))
    write_json(cx_cache_p, cx)
    # control gate
    client = ORClient("adjudication", CAP_USD["adjudication"], concurrency=8)
    gate_p = RESULTS / "judge_gate.json"
    gate = read_json(gate_p) if gate_p.exists() else {"judges": {}}
    judges = list(c0["judges"]["pair"])
    pool = list(c0["judges"]["replacements"])
    ctrl_prompts = [(c["cid"], judge_text(objs[c["task"]], c["code"], nearest_for(critic, c["code"], c["task"], None),
                                          cx.get(c["cid"]), tmpl)) for c in controls]
    passed: list[str] = []
    cand_models = judges + pool
    for m in cand_models:
        if len(passed) == 2:
            break
        fam = m.split("/")[0]
        if any(p.split("/")[0] == fam for p in passed) or fam == "qwen":
            continue
        if m not in gate["judges"]:
            res = asyncio.run(_judge_batch(client, m, ctrl_prompts))
            acc = sum(1 for c in controls if (res.get(c["cid"]) or {}).get("class") == c["expect"])
            gate["judges"][m] = {"accuracy": acc, "n": len(controls), "passed": acc >= 9,
                                 "calls": {k: (v or {}).get("class") for k, v in res.items()},
                                 "named": {k: (v or {}).get("named_algorithm") for k, v in res.items()}}
            write_json(gate_p, gate)
            logger.info(f"control gate {m}: {acc}/{len(controls)}")
        if gate["judges"][m]["passed"]:
            passed.append(m)
        if client.stop:
            break
    gate["pair_used"] = passed
    write_json(gate_p, gate)
    if len(passed) < 2:
        logger.error(f"fewer than 2 judge families passed the gate: {passed}; adjudication becomes a manual read")
    third = c0["judges"]["third"] if c0["judges"]["third"] not in passed else next(
        (m for m in pool if m not in passed and m.split("/")[0] not in {p.split("/")[0] for p in passed}), None)
    # candidates
    calls = {(r["key"], r["model"]): r for r in read_jsonl(JUDGE_P)}
    for t in tasks:
        shown = list(cands_all["tasks"][t]["shown"])
        random.Random(stable_seed(t, "shuffle")).shuffle(shown)
        prompts = {i: judge_text(objs[t], rowmap[i]["code"], nearest_for(critic, rowmap[i]["code"], t, rowmap[i]),
                                 cx.get(i), tmpl) for i in shown}
        for m in passed:
            todo = [(i, prompts[i]) for i in shown if (i, m) not in calls]
            if not todo or client.stop:
                continue
            res = asyncio.run(_judge_batch(client, m, todo))
            recs = [{"key": i, "model": m, "task": t, "result": v, "utc": utc_now()} for i, v in res.items()]
            from common import append_jsonl
            append_jsonl(JUDGE_P, recs)
            for x in recs:
                calls[(x["key"], x["model"])] = x
            logger.info(f"{t}: judge {m} on {len(todo)} candidates; adjudication spend ${client.spent:.3f}")
        if third and len(passed) == 2 and not client.stop:
            dis = [i for i in shown if (calls.get((i, passed[0])) or {}).get("result") and
                   (calls.get((i, passed[1])) or {}).get("result") and
                   calls[(i, passed[0])]["result"]["class"] != calls[(i, passed[1])]["result"]["class"]]
            todo = [(i, prompts[i]) for i in dis if (i, third) not in calls]
            if todo:
                res = asyncio.run(_judge_batch(client, third, todo))
                recs = [{"key": i, "model": third, "task": t, "result": v, "utc": utc_now()} for i, v in res.items()]
                from common import append_jsonl
                append_jsonl(JUDGE_P, recs)
                for x in recs:
                    calls[(x["key"], x["model"])] = x
    summarize(tasks, cands_all, calls, passed, third, gate, client.spent)


def _kappa(a: list[str], b: list[str]) -> float | None:
    if not a:
        return None
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def summarize(tasks, cands_all, calls, passed, third, gate, spent) -> None:
    out = {"utc": utc_now(), "judges": passed, "third": third, "spent_usd": spent, "per_candidate": {},
           "kappa": None, "manual_queue": []}
    a_l, b_l = [], []
    for t in tasks:
        for i in cands_all["tasks"][t]["shown"]:
            votes = {m: (calls.get((i, m)) or {}).get("result") for m in passed + ([third] if third else [])}
            cls = {m: (v or {}).get("class") for m, v in votes.items()}
            if len(passed) == 2 and cls.get(passed[0]) and cls.get(passed[1]):
                a_l.append(cls[passed[0]])
                b_l.append(cls[passed[1]])
            vals = [c for c in cls.values() if c]
            maj = Counter(vals).most_common(1)
            final = maj[0][0] if maj and maj[0][1] >= 2 else None
            named = [(v or {}).get("named_algorithm") for v in votes.values() if v]
            out["per_candidate"][i] = {"task": t, "votes": cls, "majority": final, "named": named,
                                       "core_ideas": [(v or {}).get("core_idea") for v in votes.values() if v]}
            if "NOVEL ALGORITHM" in vals or final is None:
                out["manual_queue"].append({"id": i, "reason": "novel_call" if "NOVEL ALGORITHM" in vals else
                                            "unresolved"})
    out["kappa"] = _kappa(a_l, b_l)
    out["n_pairs"] = len(a_l)
    out["control_accuracy"] = {m: gate["judges"].get(m, {}).get("accuracy") for m in gate["judges"]}
    # 10% random sample of each majority class for the manual read
    rng = random.Random(77)
    by_cls = defaultdict(list)
    for i, rec in out["per_candidate"].items():
        if rec["majority"]:
            by_cls[rec["majority"]].append(i)
    queued = {q["id"] for q in out["manual_queue"]}
    for c, ids in by_cls.items():
        k = max(1, round(0.1 * len(ids)))
        for i in rng.sample(sorted(ids), min(k, len(ids))):
            if i not in queued:
                out["manual_queue"].append({"id": i, "reason": f"qa_sample:{c}"})
    write_json(RESULTS / "adjudication.json", out)
    logger.info(f"adjudication summary: {len(out['per_candidate'])} candidates, kappa {out['kappa']}, "
                f"manual queue {len(out['manual_queue'])}, spent ${spent:.3f}")


def finalize_classes() -> None:
    """Final class = manual read where one exists, else the 2-of-3 judge majority; unshown cluster members inherit
    their medoid's class (propagated); clusters whose judges named the same algorithm merge."""
    adj = read_json(RESULTS / "adjudication.json")
    cands = read_json(CAND_P)
    prog = read_json(RESULTS / "program_classes.json")
    manual = {r["id"]: r for r in read_jsonl(RESULTS / "manual_reads.jsonl")}
    final: dict[str, tuple[str | None, str | None, str]] = {}
    for i, rec in adj["per_candidate"].items():
        if i in manual:
            final[i] = (manual[i]["class"], manual[i].get("named_algorithm"), "manual")
        else:
            nm = [n for n in rec["named"] if n]
            final[i] = (rec["majority"], Counter(nm).most_common(1)[0][0] if nm else None, "judges")
    # propagate within clusters
    for t, ct in cands["tasks"].items():
        for cid, cl in ct["clusters"].items():
            med = cl["medoid"]
            for mid in cl["members"]:
                if mid not in final and med in final:
                    final[mid] = (final[med][0], final[med][1], "propagated")
    # name-based merge of clusters (normalised algorithm names)
    def norm_name(s: str | None) -> str | None:
        if not s:
            return None
        s = s.lower()
        for ch in "'\"()-_,.":
            s = s.replace(ch, " ")
        return " ".join(w for w in s.split() if w not in ("algorithm", "the", "a", "an", "with", "using", "based"))
    merged: dict[tuple[str, str], str] = {}
    for rid, rec in prog.items():
        f = final.get(rec.get("distinct_id")) or final.get(rid)
        if f:
            rec["final_class"], rec["named_algorithm"], rec["class_source"] = f
        nn = norm_name(rec.get("named_algorithm"))
        t = rid.split("|")[0]
        if nn and rec.get("final_class") in ("KNOWN OUTSIDE CATALOGUE", "CATALOGUE VARIANT", "NOVEL ALGORITHM"):
            key = (t, nn)
            merged.setdefault(key, rec.get("cluster_id"))
            rec["merged_cluster_id"] = merged[key]
        else:
            rec["merged_cluster_id"] = rec.get("cluster_id")
    # duplicates inherit their distinct representative's class
    for rid, rec in prog.items():
        if rec.get("final_class") is None:
            rep = prog.get(rec.get("distinct_id"), {})
            if rep.get("final_class"):
                rec["final_class"], rec["named_algorithm"] = rep["final_class"], rep.get("named_algorithm")
                rec["class_source"] = "duplicate_of_" + str(rep.get("class_source"))
                rec["merged_cluster_id"] = rep.get("merged_cluster_id")
    write_json(RESULTS / "program_classes.json", prog)
    # propagation reliability: clusters with >= 2 read members - share of read extras agreeing with the medoid
    agree, total, mixed = 0, 0, []
    for t, ct in cands["tasks"].items():
        for cid, cl in ct["clusters"].items():
            med = manual.get(cl["medoid"])
            for x in cl["extras"]:
                if x in manual and med:
                    total += 1
                    ok = manual[x]["class"] == med["class"]
                    agree += ok
                    if not ok:
                        mixed.append({"cluster": cid, "medoid": cl["medoid"], "medoid_class": med["class"],
                                      "member": x, "member_class": manual[x]["class"], "size": len(cl["members"])})
    # judge-vs-manual agreement (advisory votes)
    jm = {}
    for m in adj.get("advisory_pair") or []:
        pairs = [(rec.get("advisory_votes", {}).get(m), manual[i]["class"]) for i, rec in adj["per_candidate"].items()
                 if i in manual and rec.get("advisory_votes", {}).get(m)]
        jm[m] = {"n": len(pairs), "agreement": (sum(a == b for a, b in pairs) / len(pairs)) if pairs else None,
                 "manual_K_or_N_called_variant": sum(1 for a, b in pairs if b in ("KNOWN OUTSIDE CATALOGUE",
                                                                                  "NOVEL ALGORITHM")
                                                     and a == "CATALOGUE VARIANT"),
                 "novel_calls": sum(1 for a, _ in pairs if a == "NOVEL ALGORITHM"),
                 "novel_calls_confirmed": sum(1 for a, b in pairs if a == "NOVEL ALGORITHM" and b == "NOVEL ALGORITHM")}
    write_json(RESULTS / "propagation_check.json", {"read_extras_vs_medoid": {"n": total, "agree": agree,
                                                                              "rate": agree / total if total else None},
                                                    "disagreeing_clusters": mixed, "judge_vs_manual": jm,
                                                    "manual_classes": dict(Counter(m["class"] for m in manual.values())),
                                                    "manual_modes": dict(Counter(m.get("mode") for m in manual.values()))})
    logger.info(f"final classes: {Counter(r.get('final_class') for r in prog.values())}; propagation agree "
                f"{agree}/{total}; judge-vs-manual {jm}")
