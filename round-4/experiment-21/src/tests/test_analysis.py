#!/usr/bin/env python3
"""CPU tests of the analysis code, run before commit #0 (testing plan items 1, 2, 4; item 3 is S0's labeller re-check).

(1a) planted effect: temperature inert, PN escaping on 3 of 6 directions with p = 0.4 -> C_T = 0, C_PN within MC
     error of the analytic expectation, exactly 20 subsets.
(1b) planted null: PN rows copy the same-T NO-PN row -> x_s = 0; calibration: 200 exchangeable-label datasets
     (40 seeds) -> share of sign-flip p < 0.05 in [0.02, 0.09].
(1c) 'invalid' / 'unresolved' handling under the three label modes.
(2)  shingles: identical -> 1; identifiers / constants / comments only -> 1; BFS vs DFS references < 0.6; cluster
     counts monotone in theta.
(4)  the screen file reproduces exp17's headline counts (T03 7/15, T2 3/15 escaping at alpha 1).
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np
from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "src", ROOT / "analysis"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import core  # noqa: E402
from cfg import RESULTS_DIR, read_json, utc_now, write_json  # noqa: E402

TEMP_ARMS = ["NOPN_T0.3", "NOPN_T0.7", "NOPN_T1.0", "NOPN_T1.3"]
DIRS = [46001, 46002, 46003, 46004, 46005, 46006]
PN_ARMS = [f"PN_D{d}_a1.0_T1.0" for d in DIRS]
SEEDS = core.seeds_of()


def _rows(task: str, labels: dict[tuple[str, str], str], passed: bool = True) -> list[dict]:
    out = []
    for (seed, arm), lab in labels.items():
        w, k = seed.split("|")
        out.append({"task": task, "template": w, "sample_id": int(k), "arm": arm, "label": lab, "passed": passed})
    return out


def planted_effect(rng: np.random.Generator, p: float = 0.4, escaping: tuple[int, ...] = (0, 1, 2)) -> list[dict]:
    lab = {}
    for s in SEEDS:
        for a in TEMP_ARMS:
            lab[(s, a)] = "dijkstra"
        for j, a in enumerate(PN_ARMS):
            lab[(s, a)] = "bf_spfa" if (j in escaping and rng.random() < p) else "dijkstra"
    return _rows("T2", lab)


def test_1a() -> dict:
    rng = np.random.default_rng(1)
    subs = core.subsets(PN_ARMS)
    analytic = 20 * np.mean([1 - 0.6 ** sum(1 for a in S if PN_ARMS.index(a) < 3) for S in subs])
    vals, cts = [], []
    for _ in range(400):
        idx = core.index_rows(planted_effect(rng))
        cts.append(core.count_changed(idx, "T2", SEEDS, TEMP_ARMS)["C"])
        vals.append(core.c_pn(idx, "T2", SEEDS, "NOPN_T1.0", PN_ARMS)["C_PN"])
    vals = np.array(vals)
    se = vals.std(ddof=1) / np.sqrt(len(vals))
    ok = (max(cts) == 0 and len(subs) == 20 and abs(vals.mean() - analytic) < 4 * se)
    return {"pass": bool(ok), "C_T_max": int(max(cts)), "n_subsets": len(subs), "C_PN_mean": float(vals.mean()),
            "analytic": float(analytic), "mc_se": float(se)}


def test_1b() -> dict:
    # exact copy null: temperature inert, PN rows copy the same-T NOPN row
    lab = {}
    for s in SEEDS:
        for a in TEMP_ARMS:
            lab[(s, a)] = "dijkstra"
        for a in PN_ARMS:
            lab[(s, a)] = lab[(s, "NOPN_T1.0")]
    idx = core.index_rows(_rows("T2", lab))
    ct = core.count_changed(idx, "T2", SEEDS, TEMP_ARMS)["per_seed"]
    pm = core.c_pn(idx, "T2", SEEDS, "NOPN_T1.0", PN_ARMS)["per_seed_mean"]
    x = core.x_contrast(ct, pm)
    copy_ok = all(v == 0 for v in x.values()) and core.sign_flip_p(list(x.values()))["p"] == 1.0
    # calibration under exchangeable labels (every condition of a seed iid), 40 seeds, 200 datasets
    rng = np.random.default_rng(2)
    ps = []
    choices = np.array(["dijkstra", "bf_spfa", "other"])
    for rep in range(200):
        xs = []
        for task in ("T2", "T03"):
            lab = {}
            for s in SEEDS:
                for a in TEMP_ARMS + PN_ARMS:
                    lab[(s, a)] = str(rng.choice(choices, p=[0.85, 0.10, 0.05]))
            idx = core.index_rows(_rows(task, lab))
            ct = core.count_changed(idx, task, SEEDS, TEMP_ARMS)["per_seed"]
            pm = core.c_pn(idx, task, SEEDS, "NOPN_T1.0", PN_ARMS)["per_seed_mean"]
            xs += list(core.x_contrast(ct, pm).values())
        ps.append(core.sign_flip_p(xs, n_draws=20_000, seed=rep)["p"])
    share = float(np.mean(np.array(ps) < 0.05))
    return {"pass": bool(copy_ok and 0.02 <= share <= 0.09), "copy_null_all_x_zero": bool(copy_ok),
            "calibration_share_p_lt_0.05": share, "n_datasets": 200,
            "calibration_quantiles_p": [float(np.quantile(ps, q)) for q in (0.05, 0.25, 0.5, 0.75)]}


def test_1c() -> dict:
    lab = {("W1|0", "NOPN_T0.3"): "dijkstra", ("W1|0", "NOPN_T0.7"): "invalid", ("W1|0", "NOPN_T1.0"): "dijkstra",
           ("W1|0", "NOPN_T1.3"): "unresolved",
           ("W1|1", "NOPN_T0.3"): "invalid", ("W1|1", "NOPN_T0.7"): "invalid", ("W1|1", "NOPN_T1.0"): "dijkstra",
           ("W1|1", "NOPN_T1.3"): "disputed"}
    idx = core.index_rows(_rows("T2", lab))
    s = ["W1|0", "W1|1"]
    prim = core.count_changed(idx, "T2", s, TEMP_ARMS, "primary")["per_seed"]
    inv = core.count_changed(idx, "T2", s, TEMP_ARMS, "invalid_as_label")["per_seed"]
    rows_fail = _rows("T2", {("W1|2", a): ("bfs" if a == "NOPN_T1.3" else "dijkstra") for a in TEMP_ARMS}, passed=False)
    idx2 = core.index_rows(rows_fail)
    co = core.count_changed(idx2, "T2", ["W1|2"], TEMP_ARMS, "correct_only")["per_seed"]
    ok = (prim == {"W1|0": 0, "W1|1": None} and inv == {"W1|0": 1, "W1|1": 1} and co == {"W1|2": None})
    return {"pass": bool(ok), "primary": prim, "invalid_as_label": inv, "correct_only_all_failing": co}


def test_2() -> dict:
    a = "def solve(n, edges, s, t):\n    # comment\n    dist = [1000000000] * n\n    dist[s] = 0\n    return dist[t]\n"
    b = "def solve(m, e, src, dst):\n    '''doc'''\n    d = [7] * m  # other\n    d[src] = 1\n    return d[dst]\n"
    sa, sb = core.shingles(a), core.shingles(b)
    suite = ROOT / "inputs/exp8/suite/tasks/t1_grid/references"
    bfs = core.shingles((suite / "bfs_deque_parent.py").read_text())
    dfs = core.shingles((suite / "dfs_stack.py").read_text())
    dfs_r = core.shingles((suite / "dfs_recursive.py").read_text())
    j_id = core.jaccard(sa, sa)
    j_ren = core.jaccard(sa, sb)
    j_bd = core.jaccard(bfs, dfs)
    j_bdr = core.jaccard(bfs, dfs_r)
    progs = [p.read_text() for p in sorted(suite.glob("*.py"))]
    bfs_txt = (suite / "bfs_deque_parent.py").read_text()
    progs += [bfs_txt.replace("queue", "q_renamed"), bfs_txt + "\n\ndef helper(x):\n    return x + 1\n",
              bfs_txt + "\n\ndef helper(x):\n    y = [x]\n    for i in range(3):\n        y.append(i)\n    return y\n"]
    J = core.jaccard_matrix([core.shingles(p) for p in progs])
    counts = [core.n_components(J, th) for th in (0.5, 0.6, 0.7, 0.8, 0.9, 0.95)]
    mono = all(x <= y for x, y in zip(counts, counts[1:]))
    cl = [core.n_complete(J, th) for th in (0.5, 0.6, 0.7, 0.8, 0.9, 0.95)]
    mono_c = all(x <= y for x, y in zip(cl, cl[1:]))
    ok = j_id == 1.0 and j_ren == 1.0 and j_bd < 0.6 and j_bdr < 0.6 and mono and mono_c
    return {"pass": bool(ok), "identical": j_id, "renamed_constants_comments": j_ren, "bfs_vs_dfs_stack": j_bd,
            "bfs_vs_dfs_recursive": j_bdr, "components_by_theta": counts, "complete_by_theta": cl}


def test_4() -> dict:
    s = read_json(RESULTS_DIR / "screen.json")
    chk = s["headline_check"]
    return {"pass": bool(chk["ruleB_matches"]), "ruleB": chk["ruleB"], "ruleA": chk["ruleA"],
            "expected": chk["expected"], "note": "rule A (excess only) gives T2 5/15: reported as a mismatch of that "
            "reading; rule B (excess and pass ratio >= 0.85) reproduces both counts"}


def run_all_tests() -> dict:
    res = {"utc": utc_now()}
    for name, fn in (("1a_planted_effect", test_1a), ("1b_planted_null", test_1b), ("1c_label_modes", test_1c),
                     ("2_shingles", test_2), ("4_screen_headlines", test_4)):
        try:
            res[name] = fn()
        except Exception as e:  # noqa: BLE001 - a failing test is recorded, never hidden
            logger.exception(f"test {name} crashed")
            res[name] = {"pass": False, "error": repr(e)}
        logger.info(f"test {name}: {res[name]}")
    res["all_pass"] = all(v.get("pass") for k, v in res.items() if isinstance(v, dict))
    write_json(RESULTS_DIR / "tests_cpu.json", res)
    logger.info(f"CPU tests all_pass={res['all_pass']}")
    return res


if __name__ == "__main__":
    run_all_tests()
