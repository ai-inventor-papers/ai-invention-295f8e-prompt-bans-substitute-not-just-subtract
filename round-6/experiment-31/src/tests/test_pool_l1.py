#!/usr/bin/env python3
"""Synthetic tests of pool_l1.py (testing plan item 5): planted perfect hits give p = product of p_e; the
Poisson-binomial DP matches brute-force enumeration for n <= 10; the sign test matches scipy.stats.binomtest;
shuffled r_u placebos give mean hit rate = mean chance; the unit-clustered version equals the per-event version when
every unit has one event. Usage: python tests/test_pool_l1.py"""

from __future__ import annotations

import itertools
import json
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pool_l1 as P  # noqa: E402


def brute_sf(ps, x):
    tot = 0.0
    for bits in itertools.product([0, 1], repeat=len(ps)):
        if sum(bits) >= x:
            pr = 1.0
            for b, p in zip(bits, ps):
                pr *= p if b else (1 - p)
            tot += pr
    return tot


def ev(unit, nt, K, r_u, modal, tail_empty=True, discordant=False, qtop=None, counts=None):
    cat = [f"m{i}" for i in range(K)]
    counts = counts or {modal: 8}
    return {"unit": unit, "unit_kind": "new", "nudge_type": nt, "exists": True, "clear_landing": True,
            "modal_landing": modal, "K": K, "catalogue": cat, "default": "m0", "r_u": r_u, "q_lik_top1": qtop,
            "t_u": None, "tail_empty": tail_empty, "discordant": discordant, "correct_off_default_counts": counts,
            "q_base": {m: 1.0 for m in cat[1:]}, "q_lik": None, "q_lik_raw": None, "q_tail": None,
            "n_other_correct": 0}


def main() -> None:
    from scipy.stats import binomtest
    rng = random.Random(1)
    ok = {}
    # (a) planted perfect hits -> p = product of p_e
    E = [ev(f"u{i}", "ESC", K, "m1", "m1") for i, K in enumerate([3, 4, 5, 3, 4, 6])]
    r = P.l1a(E)
    prod = 1.0
    for e in E:
        prod *= 1 / (e["K"] - 1)
    ok["perfect_hits_product"] = abs(r["p_poisson_binomial"] - prod) < 1e-12 and r["verdict"] == "PASS"
    # (b) DP == brute force
    good = True
    for n in range(1, 11):
        ps = [rng.uniform(0.05, 0.6) for _ in range(n)]
        for x in range(n + 1):
            good &= abs(P.poisson_binomial_sf(ps, x) - brute_sf(ps, x)) < 1e-10
    ok["dp_equals_brute_force"] = good
    # (c) sign test == scipy binomtest (one-sided greater, p = 0.5)
    good = True
    for b in range(0, 9):
        for c in range(0, 9):
            if b + c == 0:
                good &= P.sign_test_p(b, c) == 1.0
                continue
            good &= abs(P.sign_test_p(b, c) - binomtest(b, b + c, 0.5, alternative="greater").pvalue) < 1e-10
    ok["sign_test_equals_scipy"] = good
    # (d) shuffled-r_u placebo: mean hit rate ~ mean chance
    hits, chance, reps = 0.0, 0.0, 4000
    for _ in range(reps):
        E = []
        for i in range(8):
            K = rng.choice([3, 4, 5])
            land = f"m{rng.randrange(1, K)}"
            ru = f"m{rng.randrange(1, K)}"
            E.append(ev(f"u{i}", "ESC", K, ru, land))
        r = P.l1a(E)
        hits += r["hit_rate"]
        chance += r["chance_mean"]
    ok["placebo_hit_equals_chance"] = abs(hits / reps - chance / reps) < 0.01
    # (e) unit-clustered == per-event when every unit has one event
    E = [ev(f"u{i}", "ESC", 4, "m1", rng.choice(["m1", "m2", "m3"])) for i in range(7)]
    with tempfile.TemporaryDirectory() as d:
        pe, pu = Path(d) / "e.json", Path(d) / "u.json"
        pe.write_text(json.dumps({"schema": P.SCHEMA, "events": E}))
        pu.write_text(json.dumps({"schema": P.SCHEMA, "units": [{"unit": e["unit"], "unit_kind": "new"} for e in E]}))
        res = P.run([str(pe)], [str(pu)])
    a, b = res["per_event"]["L1a"], res["unit_clustered"]["L1a"]
    ok["clustered_equals_per_event_single"] = (a["hits"], a["n"], round(a["p_poisson_binomial"], 12)) == \
        (b["hits"], b["n"], round(b["p_poisson_binomial"], 12))
    ok = {k: bool(v) for k, v in ok.items()}
    print(json.dumps(ok, indent=1))
    assert all(ok.values()), ok


if __name__ == "__main__":
    main()
