"""Unit tests T1-T9 (CPU). Run: .venv/bin/python -m pytest -q tests/test_core.py"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import analysis as an  # noqa: E402
import sandbox  # noqa: E402
from baselines import NN_PROGRAM  # noqa: E402
from islands import Database, Island, Prog, _softmax  # noqa: E402

HDR = "import numpy as np\nimport math\n\ndef select_next_node(current_node, destination_node, unvisited_nodes, distance_matrix):\n"


@pytest.fixture(scope="module")
def hand():
    pts = np.array([[0, 0], [1, 0], [2, 0], [2, 1], [1, 1], [0, 1]], dtype=float)
    from scipy.spatial import distance_matrix

    D = distance_matrix(pts, pts)
    sandbox.worker_init({"hand": ([D], [1], True), "probe_states": [(0, 0, [1, 2, 3, 4, 5]), (0, 2, [3, 4, 5])],
                         "probe_mats": [D], "selection": ([D, D], [1, 2])})
    return D


# ---------------------------------------------------------------- T1 tour builder
def test_t1_nn_hand(hand):
    r = sandbox.evaluate_set(NN_PROGRAM, "hand", 10)
    assert r["label"] == "valid"
    assert r["tours"][0] == [0, 1, 2, 3, 4, 5]
    assert abs(r["lengths"][0] - 6.0) < 1e-12


@pytest.mark.parametrize("ret,ok", [("0", False), ("2.5", False), ("None", False),
                                    ("np.int64(min(unvisited_nodes))", True), ("float(min(unvisited_nodes))", True)])
def test_t1_returns(hand, ret, ok):
    code = HDR + f"    return {ret}\n"
    r = sandbox.evaluate_set(code, "hand", 10)
    assert (r["label"] == "valid") == ok, r
    if not ok:
        assert r["label"] == "invalid_return"


def test_t1_copies(hand):
    code = HDR + ("    distance_matrix[:] = 0\n    nxt = min(unvisited_nodes)\n    unvisited_nodes.clear()\n"
                  "    return nxt\n")
    r = sandbox.evaluate_set(code, "hand", 10)
    assert r["label"] == "valid" and abs(r["lengths"][0] - 6.0) < 1e-12  # 0,1,2,3,4,5 by index order


def test_t1_rng_determinism(hand):
    code = HDR + "    import random\n    return random.choice(sorted(unvisited_nodes))\n"
    a = sandbox.evaluate_program(code)
    b = sandbox.evaluate_program(code)
    assert a["label"] == "valid" and a["lengths"] == b["lengths"] and a["decisions"] == b["decisions"]


# ---------------------------------------------------------------- T2 references / parser
def test_t2_tsplib_gate():
    import json

    ref = json.loads((Path(__file__).resolve().parent.parent / "results" / "references.json").read_text())
    assert ref["tsplib"]["eil51"]["cost_int"] == 426
    assert abs(ref["tsplib"]["kroA100"]["cost_int"] - 21282) / 21282 <= 0.005
    assert ref["sets"]["selection"]["float_vs_int_within_rounding_bound"]


def test_t2_parser_rejects(tmp_path):
    from tsp_task import parse_tsplib

    p = tmp_path / "x.tsp"
    p.write_text("NAME: x\nTYPE: TSP\nDIMENSION: 2\nEDGE_WEIGHT_TYPE: GEO\nNODE_COORD_SECTION\n1 0 0\n2 1 1\nEOF\n")
    with pytest.raises(ValueError):
        parse_tsplib(p)


# ---------------------------------------------------------------- T3 sandbox planted programs
def test_t3_infinite_loop(hand):
    import time

    code = HDR + "    while True:\n        pass\n"
    t0 = time.time()
    r = sandbox.evaluate_program(code)
    assert r["label"] == "timeout"
    assert time.time() - t0 <= sandbox.SEL_CPU * sandbox.WALL_FACTOR + 4


@pytest.mark.parametrize("body", ["    import os\n    return min(unvisited_nodes)\n",
                                  "    f = open('x', 'w')\n    return min(unvisited_nodes)\n"])
def test_t3_import_violation(hand, body):
    assert sandbox.evaluate_program(HDR + body)["label"] == "import_violation"


def test_t3_memory(hand):
    r = sandbox.evaluate_program(HDR + "    x = np.ones(3 * 1024**3 // 8)\n    return min(unvisited_nodes)\n")
    assert r["label"] == "runtime_error"


def test_t3_nested_helper(hand):
    code = HDR + ("    def helper(j):\n        return distance_matrix[current_node][j]\n"
                  "    return min(unvisited_nodes, key=helper)\n")
    assert sandbox.evaluate_program(code)["label"] == "valid"


def test_t3_helper_after_cut():
    from prompt import extract

    gen = "    return helper(unvisited_nodes)\n\ndef helper(u):\n    return min(u)\n"
    ex = extract(gen, 1)
    assert "def helper" not in ex["program"]  # cut at the stop; NameError at run time


# ---------------------------------------------------------------- T4 AST cache
def test_t4_ast_hash():
    a = HDR + '    """doc"""\n    # comment\n    return min(unvisited_nodes)\n'
    b = HDR + '    """other doc"""\n    return min(unvisited_nodes)  # x\n'
    c = HDR + '    """doc"""\n    return min(unvisited_nodes) + 0\n'
    assert sandbox.ast_hash(a) == sandbox.ast_hash(b) != sandbox.ast_hash(c)


# ---------------------------------------------------------------- T5 prompt
def test_t5_prompt():
    from prompt import nn_body, render_prompt, tokenizer, user_turn

    body = nn_body(NN_PROGRAM)
    t2, ids2 = render_prompt([body, body + "    # v\n"], idea=False)
    assert t2.endswith('    """Improved version of select_next_node_v1."""\n')
    assert "<think>\n\n</think>" in t2
    assert "def select_next_node_v0" in t2 and "def select_next_node_v1" in t2 and "Write select_next_node_v2." in t2
    assert "Improved version of select_next_node_v0." in t2
    t1, _ = render_prompt([body], idea=True)
    assert "based on an idea different from the function above." in t1 and t1.endswith('_v0."""\n')
    assert "idea different" not in user_turn([body, body], idea=False)
    tok = tokenizer()
    assert tok.decode(ids2, skip_special_tokens=False, clean_up_tokenization_spaces=False) == t2


# ---------------------------------------------------------------- T6 islands
def test_t6_softmax_freq():
    rng = np.random.default_rng(0)
    p = _softmax(np.array([-1.0, -1.1, -1.5]), 0.1)
    draws = rng.choice(3, 100000, p=p)
    freq = np.bincount(draws, minlength=3) / 100000
    assert np.max(np.abs(freq - p)) < 0.01


def test_t6_reset_and_replay():
    nn = Prog("NN", "    return min(unvisited_nodes)\n", -1.0, 10)
    d = Database("T1.0", 0, nn, (0.0,))
    for c in range(400):
        island, parents = d.get_prompt()
        prog = Prog(f"p{c}", f"    return {c}\n", -1.0 + 0.001 * (c % 7) * (island + 1), 10 + c % 5) if c % 3 else None
        d.complete_call(island, prog, (float(c % 11),) if prog else None)
    assert len(d.resets) == 1 and len(d.resets[0]["reset"]) == 2
    for i, f in zip(d.resets[0]["reset"], d.resets[0]["seeded_from"]):
        assert f not in d.resets[0]["reset"] and d.islands[i].num_programs == 1


def test_t6_length_pref():
    from islands import Cluster

    cl = Cluster(-1.0, [Prog("a", "x", -1.0, 10), Prog("b", "x", -1.0, 20)])
    rng = np.random.default_rng(1)
    n = sum(cl.sample(rng).pid == "a" for _ in range(20000)) / 20000
    L = np.array([10.0, 20.0])
    p = _softmax(-(L - L.min()) / (L.max() + 1e-6), 1.0)
    assert abs(n - p[0]) < 0.01


# ---------------------------------------------------------------- T7 DTB lexer / entropy / filters
def test_t7_lexer():
    from dtb import CODE, lex_states

    s = "x = 1  # c\ny = 'a#b'\nz = \"\"\"q\nw\"\"\"\nv"
    st = lex_states(s)
    assert st[s.index("#")] == CODE and st[s.index(" c")] != CODE
    assert st[s.index("'a")] == CODE and st[s.index("a#")] != CODE
    assert st[s.index('"""')] == CODE and st[s.index("q")] != CODE and st[s.index("w")] != CODE
    assert st[len(s) - 1] == CODE


def test_t7_entropy():
    from dtb import entropy

    lp = {1: np.log(0.5), 2: np.log(0.25), 3: np.log(0.25)}
    assert abs(entropy(lp) - (-(0.5 * np.log(0.5) + 0.5 * np.log(0.25)))) < 1e-12


def test_t7_filters():
    from dtb import candidate_ok
    from prompt import tokenizer

    tok = tokenizer()
    ids = {t: tok.encode(t, add_special_tokens=False) for t in ["```", " x", "   ", "\ndef", "def"]}
    assert not candidate_ok(tok, 151645, 4)[0]  # <|im_end|>
    assert not candidate_ok(tok, ids["```"][0], 4)[0]
    assert candidate_ok(tok, ids[" x"][0], 4)[0]
    assert not candidate_ok(tok, ids["   "][0], 4)[0]
    if len(ids["\ndef"]) == 1:
        assert not candidate_ok(tok, ids["\ndef"][0], 4)[0]
    assert not candidate_ok(tok, ids["def"][0], 0)[0]


def test_t7_fallbacks():
    from dtb import choose_branch
    from prompt import tokenizer

    tok = tokenizer()
    body = tok.encode("    x = a + b\n    return x\n", add_special_tokens=False)
    bad = tok.encode("```", add_special_tokens=False)[0]
    tops = []
    for j, t in enumerate(body):
        if j == 2:  # highest entropy but only backtick/special alternatives -> DTB must move on
            tops.append({t: -0.1, bad: -1.0, 151645: -1.1, 151643: -1.2})
        else:
            alt = tok.encode(" y", add_special_tokens=False)[0]
            tops.append({t: -0.05, alt: -3.5})
    rec = choose_branch(tok, body, tops, 10 ** 6, "entropy", 0, "DTB", 0)
    assert rec["no_branch"] or rec["j_star"] != 2
    one = tok.encode("    x\n", add_special_tokens=False)
    rec2 = choose_branch(tok, one, [{t: -0.1} for t in one], 10 ** 6, "random", 0, "RPB", 0)
    assert rec2["no_branch"]


# ---------------------------------------------------------------- T8 clustering
def _planted(seed=0):
    rng = np.random.default_rng(seed)
    base = [rng.integers(0, 50, 2000) for _ in range(3)]
    X = []
    for b in base:
        for _ in range(10):
            v = b.copy()
            idx = rng.choice(2000, 20, replace=False)  # 1% noise per program -> pairwise <= 2%
            v[idx] = rng.integers(50, 100, 20)
            X.append(v)
    return np.array(X)


def test_t8_clusters():
    X = _planted()
    res = an.cluster_programs(X)
    assert res["n_clusters"] == 3
    assert an.min_within_agreement(res["U"], res["labels_unique"]) >= 0.95
    rf = an.rarefy(res["labels"], len(res["labels"]), 50)
    assert rf["mean"] == 3 and abs(rf["exact_mean"] - 3) < 1e-9


def test_t8_rederive_matches():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit"))
    import rederive

    X = _planted(1)
    hexes = [bytes([(int(x) if x >= 0 else 255) for x in row]).hex() for row in np.unique(X, axis=0)]
    assert rederive.complete_linkage_count(hexes, 100) == an.cluster_programs(X)["n_clusters"]


# ---------------------------------------------------------------- T9 verdicts
def test_t9_v1():
    g = {(a, s): 15.0 for a in an.CORE_ARMS for s in an.SEEDS}
    assert an.verdict_v1(g, 24.0)["verdict"] == "SUPPORTED"
    g2 = dict(g)
    g2[("RPB", 1)] = 22.0
    assert an.verdict_v1(g2, 24.0)["verdict"] == "PARTIAL"
    g3 = {k: 25.0 for k in g}
    assert an.verdict_v1(g3, 24.0)["verdict"] == "DISCONFIRMED"


def test_t9_v2():
    N = {(a, s): 1000 for a in an.CORE_ARMS for s in an.SEEDS}
    c = {("DTB", s): 300 for s in an.SEEDS}
    c.update({(a, s): 100 for a in ("T1.0", "T1.6", "RPB") for s in an.SEEDS})
    g = {(a, s): 15.0 for a in an.CORE_ARMS for s in an.SEEDS}
    assert an.verdict_v2(c, N, g)["verdict"] == "SUPPORTED"
    g2 = dict(g)
    g2[("DTB", 0)] = g2[("DTB", 1)] = 18.0
    v = an.verdict_v2(c, N, g2)
    assert v["verdict"] == "PARTIAL" and "clusters but worse held-out best" in v["branches"]
    c3 = dict(c)
    c3.update({("RPB", s): 280 for s in an.SEEDS})
    assert "not position-specific" in an.verdict_v2(c3, N, g)["branches"]
    c4 = dict(c)
    c4.update({("T1.6", s): 250 for s in an.SEEDS})
    assert "one comparator only" in an.verdict_v2(c4, N, g)["branches"]
    c5 = dict(c)
    c5[("DTB", 1)] = 90
    v5 = an.verdict_v2(c5, N, g)
    assert v5["verdict"] == "PARTIAL" and "one seed only" in v5["branches"]
    c6 = dict(c)
    c6.update({("DTB", s): 100 for s in an.SEEDS})
    assert an.verdict_v2(c6, N, g)["verdict"] == "DISCONFIRMED"
