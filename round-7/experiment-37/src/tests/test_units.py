"""CPU unit tests U1-U5 (run before any GPU use: `uv run method.py --stage tests`)."""

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pytest  # noqa: E402

from inputs import load_task  # noqa: E402
from sandbox import evaluate, prescreen, run_stages  # noqa: E402

TASKS = ("T2", "T03", "A3")


@pytest.fixture(scope="module")
def objs():
    return {t: load_task(t) for t in TASKS}


# ------------------------------------------------------------------------------------------------ U1 evaluator
def test_u1_references_pass_all_stages(objs):
    for t, o in objs.items():
        for name, code in o["references"].items():
            ev = evaluate(o, code)
            assert ev["correct"], (t, name, ev["first_fail"], ev["load_error"])


def test_u1_mutants_fail(objs):
    mut = ROOT / "inputs/vendor/newbench/A3_trapping_rain_water/mutants"
    files = sorted(mut.glob("*.py"))
    assert files
    for f in files:
        assert not evaluate(objs["A3"], f.read_text())["correct"], f.name


def test_u1_hardcoded_passes_hidden_fails_stress(objs):
    o = objs["T03"]
    table = {}
    for c in o["stages"]["quick"] + o["stages"]["rest"]:
        kw = json.loads(c["kw"])
        table[repr((tuple(kw["nums"]), kw["k"]))] = json.loads(c["exp"])
    code = "TABLE = " + repr(table) + "\n\ndef solve(nums, k):\n    return TABLE.get(repr((tuple(nums), k)), 0)\n"
    r = run_stages("T03", code, [o["stages"]["quick"] + o["stages"]["rest"]])
    assert r["passed_all"]
    ev = evaluate(o, code)
    assert ev["stage2"] and not ev["stress_pass"] and not ev["correct"]


def test_u1_prescreen_and_limits(objs):
    o = objs["T03"]
    for bad in ("import os\ndef solve(nums, k):\n    return 0\n",
                "import socket\ndef solve(nums, k):\n    return 0\n",
                "def solve(nums, k):\n    open('x')\n    return 0\n",
                "def solve(nums, k):\n    return eval('1')\n"):
        ok, _ = prescreen(bad)
        assert not ok
    loop = "def solve(nums, k):\n    while True:\n        pass\n"
    ev = evaluate(o, loop)
    assert not ev["correct"] and ev["first_fail"]["status"] in ("timeout", "killed")
    big = "def solve(nums, k):\n    x = bytearray(3 * 1024 ** 3)\n    return 0\n"
    ev = evaluate(o, big)
    assert not ev["correct"] and ev["first_fail"]["status"] in ("memory", "killed", "error:MemoryError")


# ------------------------------------------------------------------------------------------------ U2 labeller
def test_u2_labeller_references(objs):
    from labels import mech_label
    for t, o in objs.items():
        for name, code in o["references"].items():
            assert mech_label(t, code)["runtime_label"] == o["ref_mode"][name], (t, name)


def test_u2_array_dijkstra_and_counting_sort(objs):
    from labels import combine, mech_label
    arr = '''
def solve(n, edges, s, t):
    INF = float("inf")
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    dist = [INF] * n
    dist[s] = 0
    visited = [False] * n
    for _ in range(n):
        u = -1
        best = INF
        for v in range(n):
            if not visited[v] and dist[v] < best:
                best = dist[v]
                u = v
        if u == -1:
            break
        visited[u] = True
        for v, w in adj[u]:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
    return dist[t] if dist[t] < INF else -1
'''
    assert evaluate(objs["T2"], arr)["correct"]
    m = mech_label("T2", arr)
    assert combine(m["runtime_label"], m["ast_label"], None)[0] == "dijkstra"
    m = mech_label("T03", objs["T03"]["references"]["counting_sort"])
    assert m["runtime_label"] == "counting_sort"


# ------------------------------------------------------------------------------------------------ U3 critic
def test_u3_critic_invariances():
    from critic import jaccard_pair
    p = "import heapq\n\ndef solve(nums, k):\n    h = list(nums)\n    heapq.heapify(h)\n    for _ in range(k - 1):\n        heapq.heappop(h)\n    return h[0]\n"
    r = p.replace("h", "zz").replace("zzeapq", "heapq").replace("zzeappop", "heappop").replace("zzeapify", "heapify")
    c = '"""doc"""\n' + p.replace("    h = list(nums)", "    # copy\n    h = list(nums)  # list")
    assert jaccard_pair(p, p) == 1.0
    assert jaccard_pair(p, r) == 1.0
    assert jaccard_pair(p, c) == 1.0


def test_u3_corpus_count_and_exactness():
    import numpy as np

    from critic import CORPUS_DIR, Critic, shingle_ids
    summ = json.loads((CORPUS_DIR / "summary.json").read_text())
    assert summ["n_corpus"] == 18237
    C = Critic()
    rng = random.Random(3)
    idx = rng.sample(range(len(C.meta)), 50)
    codes = [C.code(i) for i in idx]
    sc = C.score(codes[:10])
    for k, (code, s) in enumerate(zip(codes[:10], sc)):
        a = set(shingle_ids(code).tolist())
        best = 0.0
        for j in s["top_ids"][:3]:
            b = set(shingle_ids(C.code(j)).tolist())
            best = max(best, len(a & b) / len(a | b) if a | b else 1.0)
        assert abs(best - s["s"]) < 1e-4
    for i in range(0, 50, 2):
        a = set(shingle_ids(codes[i]).tolist())
        b = set(shingle_ids(codes[i + 1]).tolist())
        bf = len(a & b) / len(a | b) if a | b else 1.0
        from critic import to_matrix
        P = to_matrix([np.array(sorted(a), dtype=np.int64)])
        Q = to_matrix([np.array(sorted(b), dtype=np.int64)])
        inter = float((P @ Q.T).toarray()[0, 0])
        sp = inter / (len(a) + len(b) - inter) if (len(a) + len(b) - inter) else 1.0
        assert abs(sp - bf) < 1e-6
    s1 = C.score(codes[:20])
    import critic as CR
    old = CR.CHUNK
    CR.CHUNK = 7
    s2 = C.score(codes[:20])
    CR.CHUNK = old
    assert [x["s"] for x in s1] == [x["s"] for x in s2]


# ------------------------------------------------------------------------------------------------ U4 search
def _fake(n_cells=6):
    return [{"id": f"seed{i}", "code": "x" * (10 + i), "novelty": 0.1 * i, "cell": f"c{i}", "runtime_ratio": 1.0,
             "depth": 0} for i in range(n_cells)]


def test_u4_boltzmann():
    import search as S
    db = S.SearchDB(_fake(), rng_seed=1)
    old = S.tau_at
    S.tau_at = lambda t: 0.01
    top = sum(1 for _ in range(400) if "c5" in [p["cell"] for p in db.pick_parents(0)][:1])
    S.tau_at = lambda t: 10.0
    cnt = {}
    for _ in range(3000):
        c = db.pick_parents(0)[0]["cell"]
        cnt[c] = cnt.get(c, 0) + 1
    S.tau_at = old
    assert top / 400 > 0.95
    assert max(cnt.values()) / min(cnt.values()) < 1.4


def test_u4_reset_and_elites():
    import search as S
    seeds = _fake(3)
    db = S.SearchDB(seeds, rng_seed=2)
    child = {"id": "c", "code": "y", "novelty": 0.9, "cell": "new", "runtime_ratio": 1.0, "depth": 1}
    assert db.offer(1, child)
    worse = dict(child, id="w", novelty=0.5)
    assert not db.offer(1, worse)
    better = dict(child, id="b", novelty=0.95)
    assert db.offer(1, better)
    before = [dict(i.cells) for i in db.islands]
    recs = db.advance(500)
    assert len(recs) == 1
    changed = [k for k in range(4) if db.islands[k].cells != before[k]]
    assert len(changed) <= 1
    r = recs[0]
    assert set(s["cell"] for s in seeds) <= set(db.islands[r["reset_island"]].cells)


def test_u4_ne_never_reads_archive():
    import search as S
    seeds = _fake(5)
    db = S.SearchDB(seeds, rng_seed=3)
    pool = S.FrozenSeedPool(seeds, rng_seed=4)
    n0 = db.archive_reads
    for _ in range(100):
        ps = pool.pick_parents()
        assert ps[0]["id"] != ps[1]["id"]
        assert all(p["id"].startswith("seed") for p in ps)
    assert db.archive_reads == n0


# ------------------------------------------------------------------------------------------------ U5 statistics
def test_u5_stats():
    from analysis import holm, rate_ratio_test, rule_of_three
    t = rate_ratio_test(30, 1500, 0, 750)
    assert 4.6 < t["LB95"] < 4.95
    assert abs(rule_of_three(100) - 0.03) < 1e-12
    adj = holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert abs(adj["a"] - 0.03) < 1e-12 and abs(adj["c"] - 0.06) < 1e-12 and abs(adj["b"] - 0.06) < 1e-12


def test_u5_placebo_uniform():
    from analysis import rate_ratio_test
    rng = random.Random(5)
    ps = []
    for _ in range(300):
        xs = sum(rng.random() < 0.02 for _ in range(1000))
        xk = sum(rng.random() < 0.02 for _ in range(500))
        ps.append(rate_ratio_test(xs, 1000, xk, 500)["p_one_sided"])
    frac = sum(p < 0.05 for p in ps) / len(ps)
    assert frac < 0.1
