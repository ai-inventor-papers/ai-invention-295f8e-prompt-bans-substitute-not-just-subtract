#!/usr/bin/env python3
"""S3: the committed probe set P10 (shared iteration-10 rule; details fixed here) and its one allowed revision P10r.

States are [item, opened_fit, n_empty, cap]: the remaining capacities of the opened bins that fit (index order), the
number of unused bins, and the bin capacity; sandbox._load_probe rebuilds the valid array opened_fit + [cap]*n_empty.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import bp
from common import DATA, sha256_file, sha256_text, write_json

PROBE_DIR = DATA / "probes"
SEED = 20261024
N_TRACE = 1000
N_UNIFORM = 1000
REVISION_EXTRA = 500

RULE_TEXT = (
    "P10 probe rule (shared iteration-10 text; unspecified details fixed by NOV-R and committed). "
    "TRACE POOL, built in this order: reference in [BF, FF, WF, AWF, c12 (bp.prio_c12_vec, the vectorised FunSearch "
    "OR heuristic), c14 (bp.prio_c14, the FunSearch Weibull heuristic)]; then instance in P1SRC-W (5 x 5,000 items, "
    "capacity 100) followed by P1SRC-OR (5 x 500 items, capacity 150); then item order. Each instance contributes "
    "bp.pack_trace(items, cap, ref) states (item, opened bins that fit in index order, n_empty, chosen capacity); "
    "pool size 6 x 27,500 = 165,000. rng = numpy.random.default_rng(20261024); idx = np.sort(rng.choice(165000, "
    "size=1000, replace=False)); the 1,000 trace states are the pool rows at idx, stored as [item, opened_fit, "
    "n_empty, instance capacity]. UNIFORM STATES, continuing the same rng, for i in 0..999: cap = 100 if i is even "
    "else 150; item = rng.integers(1, cap+1); n_open = 0 if item == cap else rng.integers(1, 31); opened = "
    "rng.integers(item, cap, size=n_open) (remaining capacities in [item, cap-1] in generated order; no draw when "
    "n_open == 0); n_empty = rng.integers(1, 31). States: trace states first, then uniform states. A state is "
    "informative when the reconstructed valid array opened_fit + [cap]*n_empty holds at least 2 distinct capacities "
    "(exactly as sandbox._load_probe builds it). Decisions: the remaining capacity of the chosen bin, "
    "int(arr[argmax(priority(item, arr.copy()))]); 65535 on error.")

REVISION_TEXT = (
    "P10r (one committed revision, used only if the instrument gate fails on P10): keep the informative states of "
    "P10 in their order, then add 500 uniform states with 5-30 open bins from the same rng continued after the "
    "P10 uniform states: for i in 0..499: cap = 100 if i is even else 150; item = rng.integers(1, cap); n_open = "
    "rng.integers(5, 31); opened = rng.integers(item, cap, size=n_open); n_empty = rng.integers(1, 31).")

TRACE_REFS = [("BF", bp.prio_bf), ("FF", bp.prio_ff), ("WF", bp.prio_wf), ("AWF", None), ("c12", bp.prio_c12_vec),
              ("c14", bp.prio_c14)]


def _informative(opened: list[int], n_empty: int, cap: int) -> bool:
    return len(set(list(opened) + [cap] * int(n_empty))) >= 2


def build_pool() -> tuple[list[tuple], list[dict]]:
    import refs
    pool: list[tuple] = []
    meta: list[dict] = []
    for rname, fn in TRACE_REFS:
        fn = fn if fn is not None else refs.prio_awf
        for set_name in ["P1SRC-W", "P1SRC-OR"]:
            for ii, inst in enumerate(bp.load_set(set_name)):
                _, states = bp.pack_trace(inst["items"], inst["capacity"], fn)
                for j, (it, of, ne, chosen) in enumerate(states):
                    pool.append((int(it), [int(x) for x in of], int(ne), int(inst["capacity"])))
                    meta.append({"source": "trace", "reference": rname, "instance": f"{set_name}:{ii}",
                                 "item_index": j, "ref_chosen_cap": int(chosen)})
    return pool, meta


def uniform_state(rng: np.random.Generator, i: int, revision: bool = False) -> tuple[int, list[int], int, int]:
    cap = 100 if i % 2 == 0 else 150
    if revision:
        item = int(rng.integers(1, cap))
        n_open = int(rng.integers(5, 31))
    else:
        item = int(rng.integers(1, cap + 1))
        n_open = 0 if item == cap else int(rng.integers(1, 31))
    opened = [int(x) for x in rng.integers(item, cap, size=n_open)] if n_open > 0 else []
    n_empty = int(rng.integers(1, 31))
    return item, opened, n_empty, cap


def build(write: bool = True) -> dict:
    pool, meta = build_pool()
    assert len(pool) == 165_000, len(pool)
    rng = np.random.default_rng(SEED)
    idx = np.sort(rng.choice(len(pool), size=N_TRACE, replace=False))
    states, smeta = [], []
    for k in idx:
        it, of, ne, cap = pool[int(k)]
        states.append([it, of, ne, cap])
        m = dict(meta[int(k)], pool_index=int(k), informative=_informative(of, ne, cap))
        smeta.append(m)
    for i in range(N_UNIFORM):
        it, of, ne, cap = uniform_state(rng, i)
        states.append([it, of, ne, cap])
        smeta.append({"source": "uniform", "uniform_index": i, "cap": cap, "n_open": len(of),
                      "informative": _informative(of, ne, cap)})
    d = {"name": "P10", "rule_text": RULE_TEXT, "rule_sha256": sha256_text(RULE_TEXT), "seed": SEED,
         "n_trace": N_TRACE, "n_uniform": N_UNIFORM, "states": states, "meta": smeta}
    out = {"n_states": len(states), "n_informative": sum(m["informative"] for m in smeta),
           "n_informative_trace": sum(m["informative"] for m in smeta[:N_TRACE]),
           "n_informative_uniform": sum(m["informative"] for m in smeta[N_TRACE:]),
           "trace_reference_counts": {r: sum(1 for m in smeta[:N_TRACE] if m["reference"] == r)
                                      for r, _ in TRACE_REFS}}
    if write:
        PROBE_DIR.mkdir(parents=True, exist_ok=True)
        p = PROBE_DIR / "P10.json"
        p.write_text(json.dumps(d, separators=(",", ":")))
        out["path"] = str(p.relative_to(DATA.parent))
        out["sha256"] = sha256_file(p)
    return {"probe": d, "summary": out, "rng": rng}


def build_revision(base: dict, rng: np.random.Generator) -> dict:
    """P10r: informative P10 states + 500 uniform states with 5-30 open bins (same rng continuation)."""
    states, smeta = [], []
    for s, m in zip(base["states"], base["meta"]):
        if m["informative"]:
            states.append(s)
            smeta.append(m)
    for i in range(REVISION_EXTRA):
        it, of, ne, cap = uniform_state(rng, i, revision=True)
        states.append([it, of, ne, cap])
        smeta.append({"source": "uniform_rev", "uniform_index": i, "cap": cap, "n_open": len(of),
                      "informative": _informative(of, ne, cap)})
    d = {"name": "P10r", "rule_text": RULE_TEXT + " " + REVISION_TEXT, "seed": SEED, "states": states,
         "meta": smeta}
    p = PROBE_DIR / "P10r.json"
    p.write_text(json.dumps(d, separators=(",", ":")))
    return {"path": str(p.relative_to(DATA.parent)), "sha256": sha256_file(p), "n_states": len(states)}


def load_meta(name: str = "P10") -> list[dict]:
    return json.loads((PROBE_DIR / f"{name}.json").read_text())["meta"]


def load_states(name: str = "P10") -> list[list]:
    return json.loads((PROBE_DIR / f"{name}.json").read_text())["states"]


def unit_test_u3() -> dict:
    """U3: two independent builds give the same sha256; counts 1,000 + 1,000; reconstruction equals _load_probe."""
    import tempfile

    import sandbox
    a = build(write=True)
    sha_a = a["summary"]["sha256"]
    b = build(write=False)
    with tempfile.TemporaryDirectory(dir=str(DATA)) as td:
        q = Path(td) / "P10.json"
        q.write_text(json.dumps(b["probe"], separators=(",", ":")))
        sha_b = sha256_file(q)
    st = sandbox._load_probe(PROBE_DIR / "P10.json")
    rec_ok = all(int(it) == s[0] and arr.tolist() == list(s[1]) + [s[3]] * s[2]
                 for (it, arr), s in zip(st, a["probe"]["states"]))
    info_ok = all(m["informative"] == (len(set(arr.tolist())) >= 2) for m, (_, arr) in zip(a["probe"]["meta"], st))
    n_tr = sum(1 for m in a["probe"]["meta"] if m["source"] == "trace")
    n_un = sum(1 for m in a["probe"]["meta"] if m["source"] == "uniform")
    return {"sha_build1": sha_a, "sha_build2": sha_b, "deterministic": sha_a == sha_b, "n_trace": n_tr,
            "n_uniform": n_un, "reconstruction_matches_load_probe": rec_ok, "informative_flag_matches": info_ok,
            "passed": bool(sha_a == sha_b and n_tr == 1000 and n_un == 1000 and rec_ok and info_ok and
                           len(st) == 2000), "summary": a["summary"]}


if __name__ == "__main__":
    r = build()
    print(json.dumps(r["summary"], indent=1))
    write_json(DATA / "probes" / "_summary.json", r["summary"])
