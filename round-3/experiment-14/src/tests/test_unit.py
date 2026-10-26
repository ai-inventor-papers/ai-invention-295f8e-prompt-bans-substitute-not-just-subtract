"""Plan T1 unit tests (CPU).  Must pass before COMMIT #1 freezes the analysis code."""

from __future__ import annotations

import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from analysis import c1  # noqa: E402
from exposure import ngram as NG  # noqa: E402
from exposure.core import PRED, TASK_ORDER, fenced, read_jsonl, task_dir  # noqa: E402


# ------------------------------------------------------------------------------------------------------ (a) scrub
def test_scrub_idempotent_compiles_passes_relabels():
    from bench_copy.common.harness import run_tests
    from bench_copy.common.probes import run_trace
    from bench_copy.common.rtrules import runtime_label
    from bench_copy.common.scrub import scrub_code
    rng = random.Random(0)
    n_checked = 0
    for t in TASK_ORDER:
        forced = [r for r in read_jsonl(task_dir(t) / "forced_programs.jsonl")
                  if r["label"] == r["forced_mode"] and r["passed"] and r.get("scrub_verified")]
        cases = read_jsonl(task_dir(t) / "tests.jsonl")
        for r in rng.sample(forced, min(5, len(forced))):
            s1, info = scrub_code(r["code"])
            assert info["ok"], (t, r["sample_id"], info)
            s2, _ = scrub_code(s1)
            assert s2 == s1, f"scrub not idempotent on {r['sample_id']}"
            compile(s1, "<s>", "exec")
            assert run_tests(s1, t, cases)["passed"], f"scrubbed program fails tests: {r['sample_id']}"
            assert runtime_label(t, run_trace(s1, t)) == r["runtime_label"], f"relabelled: {r['sample_id']}"
            n_checked += 1
    assert n_checked >= 50


# ----------------------------------------------------------------------------------------- (b) tokenizer round trip
def test_tokenizer_round_trip_on_shown_programs():
    p = PRED / "shown_programs.jsonl"
    if not p.exists():
        pytest.skip("forecasts not yet written")
    from exposure.core import load_tokenizer
    tok = load_tokenizer()
    rows = read_jsonl(p)
    assert rows
    for r in rows:
        text = fenced(r["code"])
        ids = tok(text, add_special_tokens=False)["input_ids"]
        assert tok.decode(ids) == text, r["key"]


# ------------------------------------------------------------------------------------------------- (c) n-gram rule
def test_ngram_selector_toy():
    ref = [NG.ngram_set([1, 2, 3, 9]), NG.ngram_set([1, 2, 3, 8]), NG.ngram_set([5, 2, 3, 7]), NG.ngram_set([1, 2, 3])]
    groups = {"g1": [NG.ngram_set([2, 3, 4]), NG.ngram_set([2, 3, 6])], "g2": [NG.ngram_set([4, 5, 6])]}
    shown = [NG.ngram_set([1, 2, 3]), NG.ngram_set([0, 1, 2, 3])]
    sel = NG.select_distinctive(ref, groups, shown)
    # presence >= 0.8: (2,), (3,), (2,3) [4/4] and (1,) (1,2) (1,2,3) [3/4 = 0.75 -> excluded]; (2,3) etc have
    # collateral 1.0 in g1; all candidates have collateral 1.0 -> order by n asc then presence desc then ids asc
    assert sel["ids"] == [2]
    groups2 = {"g1": [NG.ngram_set([2, 4])], "g2": [NG.ngram_set([4, 5])]}
    sel2 = NG.select_distinctive(ref, groups2, shown)
    assert sel2["ids"] == [3] and sel2["collateral"] == 0.0
    assert NG.contains([7, 1, 2, 3], (2, 3)) and not NG.contains([7, 1, 2], (2, 3))
    # relaxed rule
    sel3 = NG.select_distinctive([NG.ngram_set([1]), NG.ngram_set([2]), NG.ngram_set([3])], {"g": [NG.ngram_set([1])]},
                                 None, allow_relaxed=True)
    assert sel3["relaxed"] and sel3["ids"] in ([2], [3])


def test_ngram_selector_on_T03_default():
    from exposure.core import load_tokenizer
    from exposure.forecasts import task_groups
    tok = load_tokenizer()
    tg = task_groups("T03", tok)
    pilot = tg["pilot"]
    groups = {f"forced:{j}": s for j, s in tg["by_mode"].items() if j != "full_sort" and s}
    sel = NG.select_distinctive(pilot, groups, pilot)
    g = tuple(sel["ids"])
    assert sel["presence"] >= 0.8
    assert sel["collateral"] < 0.5, sel
    assert sum(1 for s in pilot if g in s) >= min(5, len(pilot))


# ---------------------------------------------------------------------------------------------------- (d) zss
def test_zss_sanity():
    from exposure.astdist import distance, normalised_tree
    d = task_dir("T03") / "references"
    hp, sk, mm = [normalised_tree((d / f"{m}.py").read_text()) for m in ["heapify_pop", "size_k_heap", "median_of_medians"]]
    assert distance(hp, hp) == 0
    assert distance(hp, sk) == distance(sk, hp)
    assert distance(hp, sk) < distance(hp, mm)
    a = normalised_tree("def solve(a):\n    x = sorted(a)\n    return x[0]\n")
    b = normalised_tree("def solve(a):\n    '''doc'''\n    yy = sorted(a)  # c\n    return yy[0]\n")
    assert distance(a, b) == 0  # renaming, docstrings and comments are normalised away


# ------------------------------------------------------------------------------------------------- (e) scorer
def test_scorer_values():
    s = ["a", "b", "c", "d"]
    k = len(s)
    p = c1.smooth({"a": 1.0}, s)
    assert abs(sum(p.values()) - 1) < 1e-12
    assert abs(math.log(p["a"]) - math.log(0.98 * (0.95 + 0.05 / k))) < 1e-12
    assert abs(math.log(p["b"]) - math.log(0.98 * 0.05 / k)) < 1e-12
    assert abs(c1.log_score({"a": 1.0}, s, {"a": 3}) - math.log(0.98 * (0.95 + 0.05 / k))) < 1e-12
    assert abs(c1.log_score({"a": 1.0}, s, {"b": 2}) - math.log(0.98 * 0.05 / k)) < 1e-12
    u = c1.smooth(None, s)
    assert all(abs(u[x] - 0.98 / k) < 1e-12 for x in s) and abs(u["other"] - 0.02) < 1e-12
    q = c1.smooth({"a": 0.5, "other": 0.5}, s)
    assert abs(sum(q.values()) - 1) < 1e-12 and abs(q["other"] - (0.98 * 0.95 * 0.5 + 0.02)) < 1e-12
    assert c1.top1(None, s) == s and c1.top1({"b": 0.6, "a": 0.4}, s) == ["b"]
    assert c1.top1({"b": 0.5, "a": 0.5}, s) == ["a", "b"]
    assert c1.is_disagreeing({"A": ["a"], "B": ["a"]}) is False and c1.is_disagreeing({"A": ["a"], "B": ["b"]})
    assert abs(c1.js_divergence({"a": 1}, {"b": 1}) - 1.0) < 1e-12 and c1.js_divergence({"a": 2}, {"a": 5}) == 0.0
    assert c1.normalise_label("unknown", "y", s) == "other" and c1.normalise_label("invalid", "y", s) is None


# ---------------------------------------------------------------------------------- (f) advance rule + Holm-Wilcoxon
def _sim_events(rng: random.Random, n_events: int, planted: str | None) -> list[dict]:
    evs = []
    for i in range(n_events):
        s = ["a", "b", "c", "d"]
        true = rng.choice(s)
        probs = {x: (0.7 if x == true else 0.1) for x in s}
        land = Counter(rng.choices(list(probs), weights=list(probs.values()), k=40))
        fc = {}
        for f in c1.FAMILIES:
            fc[f] = {true: 1.0} if f == planted else {rng.choice(s): 1.0}
        sc = c1.score_event(s, dict(land), fc)
        evs.append({"task": f"t{i % 6}", "gate_pass": True, "survivors": s, "landing_counts_norm": dict(land),
                    "forecasts": fc, **sc})
    return evs


def test_advance_rule_planted_and_null():
    rng = random.Random(1)
    adv_planted = 0
    for _ in range(200):
        res = c1.run_c1(_sim_events(rng, 15, "LADDER"), n_boot=200)
        adv_planted += "LADDER" in res["rule"]["advancing"]
    assert adv_planted / 200 >= 0.95
    sig_null, adv_null = 0, 0
    for _ in range(200):
        res = c1.run_c1(_sim_events(rng, 15, None), n_boot=50)
        sig_null += any(t["significant"] for t in res["tests"]["tests"]) if res["tests"]["run"] else 0
        adv_null += bool(res["rule"]["advancing"])
    assert sig_null / 200 <= 0.10  # Holm-Wilcoxon family-wise error near its 5% level
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "advance_rule_null_calibration.json").write_text(json.dumps(
        {"n_draws": 200, "n_events": 15, "planted_advance_rate": adv_planted / 200,
         "null_any_family_advances_rate": adv_null / 200, "null_holm_any_significant_rate": sig_null / 200}, indent=1))


def test_holm():
    adj = c1.holm([0.01, 0.04, 0.03, 0.2])
    assert [round(x, 6) for x in adj] == [0.04, 0.09, 0.09, 0.2]


def test_wilcoxon_exact_small():
    r = c1.wilcoxon_two_sided([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    assert r["method"] == "exact" and abs(r["p"] - 2 / 2 ** 6) < 1e-12


# ------------------------------------------------------------------------------------------------- (g) hash chain
def test_hash_chain_detects_tamper(tmp_path):
    from bench_copy.common.commit import commit, verify_chain
    log = tmp_path / "c.log"
    commit(log, "a", "0" * 64)
    commit(log, "b", "1" * 64)
    assert verify_chain(log)
    txt = log.read_text()
    i = txt.index('"kind":"a"') + 8
    log.write_text(txt[:i] + ("b" if txt[i] != "b" else "c") + txt[i + 1:])
    assert not verify_chain(log)


# ------------------------------------------------------------------------------------------------- veto processor
def test_request_veto_cpu():
    torch = pytest.importorskip("torch")
    from exposure.veto import RequestVeto
    rv = RequestVeto([[5], [1, 2, 3], [7, 8]])
    out = [9, 1, 2]
    lg = rv(out, torch.zeros(10))
    assert lg[5] == float("-inf") and lg[3] == float("-inf") and lg[8] == 0
    lg = rv([9, 7], torch.zeros(10))
    assert lg[8] == float("-inf") and lg[3] == 0 and lg[5] == float("-inf")
    lg = rv([], torch.zeros(10))
    assert lg[5] == float("-inf") and int(torch.isinf(lg).sum()) == 1
