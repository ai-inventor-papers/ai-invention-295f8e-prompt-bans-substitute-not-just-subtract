#!/usr/bin/env python3
"""S2: the shared P10 probe construction (exact, deterministic), the agreement statistic and the probe gate.

P10 = 1,000 states drawn from the traces of BF, FF, WF, AWF, c12_vec and c14 on P1SRC-W + P1SRC-OR, plus 1,000
uniform states. A state is [item, opened capacities that fit (index order), n_empty, bin capacity]; the probe array is
opened + [cap] * n_empty, and a program's decision is the remaining capacity of the bin it chooses (ERR = 65535)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

import bp  # noqa: E402
import common as C  # noqa: E402

ERR = 65535
P10_PATH = C.DATA / "probes" / "P10.json"
REF_ORDER = ["BF", "FF", "WF", "AWF", "c12_vec", "c14"]
SRC_C12VEC = ("def priority(item, bins):\n    g = bins - item\n"
              "    return np.select([g <= 2, g <= 3, g <= 5, g <= 7, g <= 9, g <= 12, g <= 15, g <= 18, g <= 20, g <= 21],\n"
              "                     [4, 3, 2, 1, 0.9, 0.95, 0.97, 0.98, 0.98, 0.98], 0.99)\n")


def ref_fns() -> dict:
    _, _, _, w_src = bp.funsearch_notebook()
    import sandbox
    c14, et, msg = sandbox.compile_program(w_src)
    assert c14 is not None, (et, msg)
    return {"BF": bp.prio_bf, "FF": bp.prio_ff, "WF": bp.prio_wf, "AWF": bp.prio_awf, "c12_vec": bp.prio_c12_vec,
            "c14": c14}


def ref_sources() -> dict:
    or_src, w_src = bp.funsearch_notebook()[2:]
    return {"BF": bp.SRC_BF, "FF": bp.SRC_FF, "WF": bp.SRC_WF, "AWF": bp.SRC_AWF, "c12_vec": SRC_C12VEC, "c14": w_src,
            "c12": or_src}


def build_p10() -> tuple[list, dict]:
    """Exactly the plan's construction. The pool is indexed lazily (pool order = ref, then instance in file order,
    then t), so only the sampled trace states are materialised; len(pool) and every index are identical."""
    import warnings
    warnings.simplefilter("ignore")
    np.seterr(all="ignore")
    fns = ref_fns()
    insts = bp.load_set("P1SRC-W") + bp.load_set("P1SRC-OR")
    blocks = []  # (ref, inst_index, n_states) in pool order
    for ref in REF_ORDER:
        for k, inst in enumerate(insts):
            blocks.append((ref, k, len(inst["items"])))  # pack_trace yields one state per item
    n_pool = sum(b[2] for b in blocks)
    rng = np.random.default_rng(20261024)
    idx = np.sort(rng.choice(n_pool, size=1000, replace=False))
    starts = np.cumsum([0] + [b[2] for b in blocks])
    trace, trace_meta = [], []
    for bi, (ref, k, n) in enumerate(blocks):
        sel = idx[(idx >= starts[bi]) & (idx < starts[bi] + n)] - starts[bi]
        if len(sel) == 0:
            continue
        inst = insts[k]
        _, st = bp.pack_trace(inst["items"], inst["capacity"], fns[ref])
        assert len(st) == n
        for t in sel:
            item, opened_fit, n_empty, chosen = st[int(t)]
            trace.append([int(item), [int(x) for x in opened_fit], int(n_empty), int(inst["capacity"])])
            trace_meta.append([ref, inst["id"], int(t), int(chosen)])
    assert len(trace) == 1000
    uniform = []
    for j in range(1000):
        cap = 100 if j % 2 == 0 else 150
        item = int(rng.integers(1, cap))
        n_open = int(rng.integers(1, 31))
        opened = [int(x) for x in rng.integers(item, cap, size=n_open)]
        n_empty = int(rng.integers(1, 31))
        uniform.append([item, opened, n_empty, cap])
    states = trace + uniform
    meta = {"n_pool": int(n_pool), "seed": 20261024, "ref_order": REF_ORDER,
            "sources": ["P1SRC-W", "P1SRC-OR"], "trace_meta": trace_meta,
            "interpretations": ["uniform caps alternate 100/150 by j parity", "uniform item in 1..cap-1",
                                "uniform n_open in 1..30 with opened capacities uniform on [item, cap-1]",
                                "uniform n_empty in 1..30"]}
    return states, meta


def states_sha(states: list) -> str:
    return C.sha256_text(json.dumps(states, separators=(",", ":")))


def informative_mask(states: list) -> np.ndarray:
    """INFORMATIVE: the valid array has >= 2 distinct capacities, i.e. at least one opened bin fits."""
    return np.array([len(s[1]) >= 1 for s in states], dtype=bool)


def agreement(da: np.ndarray, db: np.ndarray, mask: np.ndarray | None = None) -> float:
    """mean over states of [d_a == d_b and d_a != ERR] (ERR never agrees with anything)."""
    eq = (da == db) & (da != ERR)
    if mask is not None:
        eq = eq[mask]
    return float(eq.mean()) if eq.size else float("nan")


def local_decisions(fn, states: list) -> np.ndarray:
    """In-process probe pass (trusted reference code only)."""
    import sandbox
    arrs = [(int(it), np.array(list(of) + [int(cap)] * int(ne))) for it, of, ne, cap in states]
    return sandbox.probe_decisions(fn, arrs)


GATE_VARIANTS = {
    "BF_renamed": ("def priority(item, bins):\n    \"\"\"Renamed, reformatted best fit.\"\"\"\n"
                   "    remaining_after = bins - item\n    s = -1.0 * remaining_after\n    return s\n"),
    "BF_tiebreak_index": "def priority(item, bins):\n    return -(bins - item) + 1e-9 * np.arange(len(bins))\n",
    "WF_last_of_equal": ("def priority(item, bins):\n    score = (bins - item).astype(float) + 1e-9 * np.arange(len(bins))\n"
                         "    m = bins == bins.max()\n    if not m.all():\n        score[m] = -1e9\n    return score\n"),
    "FF_renamed": "def priority(item, bins):\n    n = bins.shape[0]\n    return np.arange(n, 0, -1).astype(float)\n",
    "WF_renamed": ("def priority(item, bins):\n    full = bins.max()\n    out = np.where(bins == full, -1e9, bins - item)\n"
                   "    if (bins == full).all():\n        out = np.zeros(len(bins))\n    return out\n"),
    "AWF_renamed": ("def priority(item, bins):\n    c = bins.max()\n    opened = [i for i in range(len(bins)) if bins[i] < c]\n"
                    "    s = np.zeros(len(bins))\n    if not opened:\n        return s\n"
                    "    opened.sort(key=lambda i: (-bins[i], i))\n    for i in opened:\n        s[i] = 1.0\n"
                    "    s[opened[1] if len(opened) > 1 else opened[0]] = 2.0\n    return s\n"),
    "c14_renamed": None,  # filled from the notebook source with the function body reformatted
}


@logger.catch(reraise=True)
def main() -> None:
    C.setup_logging("probes")
    import sandbox
    states, meta = build_p10()
    sha = states_sha(states)
    states2, _ = build_p10()
    stable = states_sha(states2) == sha
    P10_PATH.parent.mkdir(parents=True, exist_ok=True)
    C.write_json(P10_PATH, {"states": states, "meta": meta}, indent=None)
    inf = informative_mask(states)
    logger.info(f"P10 built: {len(states)} states, sha256={sha[:16]}..., stable across two builds={stable}, "
                f"informative share={inf.mean():.3f} (trace {inf[:1000].mean():.3f}, uniform {inf[1000:].mean():.3f})")
    # ---- probe gate through the real sandbox workers (compile from text, P10 pass)
    srcs = ref_sources()
    w_src = srcs["c14"]
    c14_ren = w_src.replace("max_bin_cap", "largest_cap").replace("score", "val")
    GATE_VARIANTS["c14_renamed"] = c14_ren
    progs = {k: srcs[k] for k in REF_ORDER} | {k: v for k, v in GATE_VARIANTS.items()}
    pool = sandbox.EvalPool(6, C.ROOT)
    try:
        def run(code):
            return pool.submit({"code": code, "sets": [], "budget": "cumulative", "limit": 20.0, "strict": True,
                                "probes": ["P10"], "probe_limit": 20.0})
        futs1 = {k: run(v) for k, v in progs.items()}
        futs2 = {k: run(srcs[k]) for k in REF_ORDER}
        d1 = {k: np.frombuffer(f.result()["probes"]["P10"], dtype=np.uint16) for k, f in futs1.items()}
        d2 = {k: np.frombuffer(f.result()["probes"]["P10"], dtype=np.uint16) for k, f in futs2.items()}
    finally:
        pool.close()
    gate = {"self_two_runs": {k: agreement(d1[k], d2[k]) for k in REF_ORDER},
            "renamed_copies": {"BF": agreement(d1["BF"], d1["BF_renamed"]), "FF": agreement(d1["FF"], d1["FF_renamed"]),
                               "WF": agreement(d1["WF"], d1["WF_renamed"]),
                               "AWF": agreement(d1["AWF"], d1["AWF_renamed"]),
                               "c14": agreement(d1["c14"], d1["c14_renamed"])},
            "tiebreak_variants": {"BF+1e-9*index": agreement(d1["BF"], d1["BF_tiebreak_index"]),
                                  "WF_last_of_equal": agreement(d1["WF"], d1["WF_last_of_equal"])},
            "different_rules": {"BF-WF": agreement(d1["BF"], d1["WF"]), "BF-FF": agreement(d1["BF"], d1["FF"]),
                                "BF-AWF": agreement(d1["BF"], d1["AWF"]), "FF-WF": agreement(d1["FF"], d1["WF"])}}
    gate["different_rules_informative"] = {
        "BF-WF": agreement(d1["BF"], d1["WF"], inf), "BF-FF": agreement(d1["BF"], d1["FF"], inf),
        "BF-AWF": agreement(d1["BF"], d1["AWF"], inf), "FF-WF": agreement(d1["FF"], d1["WF"], inf)}
    # local in-process decisions must equal the worker decisions (instrument check)
    fns = ref_fns()
    gate["worker_equals_inprocess"] = {k: bool(np.array_equal(local_decisions(fns[k], states), d1[k]))
                                       for k in REF_ORDER}
    # trace self-consistency: own trace states, probe decision == recorded chosen capacity
    tm = meta["trace_meta"]
    sc = {}
    for ref in REF_ORDER:
        ii = [i for i, m in enumerate(tm) if m[0] == ref]
        sc[ref] = {"n": len(ii), "share": float(np.mean([int(d1[ref][i]) == tm[i][3] for i in ii])) if ii else None}
    gate["trace_self_consistency"] = sc
    ok = (all(v == 1.0 for v in gate["self_two_runs"].values())
          and all(v == 1.0 for v in gate["renamed_copies"].values())
          and all(v >= 0.95 for v in gate["tiebreak_variants"].values())
          and all(v < 0.95 for v in gate["different_rules"].values())
          and all(gate["worker_equals_inprocess"].values()) and stable)
    gate["PROBE_GATE_PASS"] = bool(ok)
    corpus_like = {k: d1[k].tolist() for k in REF_ORDER}
    C.write_json(C.RESULTS / "probes.json", {"utc": C.utc(), "p10_sha256": sha, "stable_two_builds": stable,
                                             "n_states": len(states), "informative_share": float(inf.mean()),
                                             "informative_share_trace": float(inf[:1000].mean()),
                                             "informative_share_uniform": float(inf[1000:].mean()),
                                             "gate": gate, "ref_decisions": corpus_like})
    logger.info(json.dumps(gate, indent=1)[:3000])
    logger.info(f"PROBE GATE {'PASS' if ok else 'FAIL'}")
    C.ledger("S2 probes built and gated", planned_h=1.17, gate=ok)
    if not ok:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
