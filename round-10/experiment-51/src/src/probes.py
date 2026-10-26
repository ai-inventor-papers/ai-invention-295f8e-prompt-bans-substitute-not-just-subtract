#!/usr/bin/env python3
"""P1 behaviour probes (deterministic; the same construction is specified to NOV-B2 and NOV-R).

1,000 states drawn without replacement from the packing traces of six reference heuristics on P1SRC-W[0..4] then
P1SRC-OR[0..4] (165,000 states), plus 1,000 uniform random states, both from default_rng(20261024).
A state is [item, open_fit, n_empty, capacity]; its bin array is open_fit + [capacity] * n_empty, exactly what
sandbox._load_probe builds. decision(program, state) = remaining capacity of the chosen bin (uint16, ERR = 65535).
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bp  # noqa: E402

ROOT = bp.ROOT
PROBE_DIR = ROOT / "data" / "probes"
ERR = 65535
SEED = 20261024

SRC_AWF = ("def priority(item, bins):\n    cap = bins.max()\n    opn = np.nonzero(bins < cap)[0]\n"
           "    out = np.zeros(len(bins), dtype=float)\n    if len(opn) >= 2:\n"
           "        order = np.argsort(-bins[opn], kind='stable')\n        out[opn[order[1]]] = 1.0\n"
           "    elif len(opn) == 1:\n        out[opn[0]] = 1.0\n    else:\n"
           "        out[np.nonzero(bins == cap)[0][0]] = 1.0\n    return out\n")


def prio_awf(item, bins):
    """Almost Worst Fit (Johnson 1974): the open bin with the second-largest remaining capacity (stable sort,
    descending); the only open bin if there is one; otherwise the first empty bin. One-hot float vector."""
    cap = bins.max()
    opn = np.nonzero(bins < cap)[0]
    out = np.zeros(len(bins), dtype=float)
    if len(opn) >= 2:
        order = np.argsort(-bins[opn], kind="stable")
        out[opn[order[1]]] = 1.0
    elif len(opn) == 1:
        out[opn[0]] = 1.0
    else:
        out[np.nonzero(bins == cap)[0][0]] = 1.0
    return out


REFS = [("BF", bp.prio_bf), ("FF", bp.prio_ff), ("WF", bp.prio_wf), ("AWF", prio_awf),
        ("c12", bp.prio_c12_vec), ("c14", bp.prio_c14)]


def trace_at(items: list[int], cap: int, prio, steps: set[int]) -> dict[int, tuple[int, list[int], int, int]]:
    """bp.pack_trace semantics, recording only the requested steps (memory: the full trace holds ~10^8 ints)."""
    n = len(items)
    bins = np.array([cap for _ in range(n)])
    used = np.zeros(n, dtype=bool)
    out = {}
    for t, it in enumerate(items):
        v = np.nonzero(bins >= it)[0]
        vb = bins[v]
        p = np.asarray(prio(it, vb))
        b = v[np.argmax(p)]
        if t in steps:
            opened_fit = [int(x) for x, u in zip(vb, used[v]) if u]
            out[t] = (int(it), opened_fit, int((~used).sum()), int(bins[b]))
        bins[b] -= it
        used[b] = True
    return out


def decide(prio, item: int, arr: np.ndarray) -> int:
    """Exactly sandbox._probe_decisions for one state (trusted reference code)."""
    try:
        p = np.asarray(prio(item, arr.copy()))
        if p.ndim != 1 or p.shape[0] != arr.shape[0]:
            return ERR
        return int(arr[int(np.argmax(p))])
    except Exception:  # noqa: BLE001 - per-state errors are ERR, as in the sandbox
        return ERR


def state_arrays(states: list) -> list[tuple[int, np.ndarray]]:
    return [(int(it), np.array(list(of) + [int(cap)] * int(ne))) for it, of, ne, cap in states]


def agreement(a: np.ndarray, b: np.ndarray) -> float:
    a, b = np.asarray(a), np.asarray(b)
    return float(np.mean((a == b) & (a != ERR)))


def build() -> dict:
    t0 = time.time()
    insts = bp.load_set("P1SRC-W")[:5] + bp.load_set("P1SRC-OR")[:5]
    sizes = [len(x["items"]) for x in insts]
    n_total = len(REFS) * sum(sizes)
    rng = np.random.default_rng(SEED)
    idx = rng.choice(n_total, 1000, replace=False)  # kept in draw order
    uniform = []
    for j in range(1000):
        cap = 100 if j < 500 else 150
        item = int(rng.integers(1, cap))
        n_open = int(rng.integers(1, 31))
        open_fit = [int(v) for v in rng.integers(item, cap, size=n_open).tolist()]
        n_empty = int(rng.integers(1, 31))
        uniform.append([item, open_fit, n_empty, cap])
    # locate every drawn global index: trace order = for ref, for inst, for step
    where = {}
    g = 0
    for ri, _ in enumerate(REFS):
        for ii, n in enumerate(sizes):
            where[(ri, ii)] = (g, g + n)
            g += n
    assert g == n_total
    need: dict[tuple[int, int], set[int]] = {}
    loc = []
    for gi in idx.tolist():
        for key, (lo, hi) in where.items():
            if lo <= gi < hi:
                need.setdefault(key, set()).add(gi - lo)
                loc.append((key, gi - lo))
                break
    recorded = {}
    for (ri, ii), steps in sorted(need.items()):
        rname, prio = REFS[ri]
        tr = trace_at(insts[ii]["items"], insts[ii]["capacity"], prio, steps)
        for s, st in tr.items():
            recorded[(ri, ii, s)] = st
    trace_states, src, chosen = [], [], []
    for (ri, ii), s in loc:
        it, of, ne, ch = recorded[(ri, ii, s)]
        trace_states.append([it, of, ne, int(insts[ii]["capacity"])])
        src.append([REFS[ri][0], insts[ii]["id"], s])
        chosen.append(ch)
    states = trace_states + uniform
    meta = {"construction": "plan NOV-B1 S1 PROBES; rng default_rng(20261024); choice(165000, 1000, replace=False) "
                            "kept in draw order, then 1,000 uniform states from the same rng",
            "refs": [r for r, _ in REFS], "insts": [x["id"] for x in insts], "n_trace_total": n_total,
            "trace_src": src, "trace_recorded_choice": chosen,
            "uniform_departure": "item = rng.integers(1, cap) i.e. 1..cap-1 so that open_fit = integers(item, cap) is non-empty",
            "format": "[item, open_fit, n_empty, capacity]"}
    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    blob = json.dumps({"states": states, "meta": meta}, separators=(",", ":"))
    (PROBE_DIR / "P1.json").write_text(blob)
    file_sha = hashlib.sha256(blob.encode()).hexdigest()
    states_sha = hashlib.sha256(json.dumps(states, separators=(",", ":")).encode()).hexdigest()
    # ---- self-check: prefix-opening references reproduce their own recorded choices on their own trace states
    arrs = state_arrays(states)
    self_agree = {}
    for ri, (rname, prio) in enumerate(REFS):
        ks = [k for k in range(1000) if src[k][0] == rname]
        hits = sum(decide(prio, arrs[k][0], arrs[k][1]) == chosen[k] for k in ks)
        self_agree[rname] = {"n_states": len(ks), "agree": hits / max(1, len(ks))}
    # reference decision vectors on all 2,000 states
    ref_dec = {rname: [decide(prio, it, a) for it, a in arrs] for rname, prio in REFS}
    ref_agree = {f"{a}~{b}": agreement(ref_dec[a], ref_dec[b]) for i, (a, _) in enumerate(REFS)
                 for (b, _) in REFS[i + 1:]}
    res = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "file": "data/probes/P1.json",
           "file_sha256": file_sha, "states_sha256": states_sha, "n_states": len(states),
           "n_trace": len(trace_states), "n_uniform": len(uniform),
           "trace_states_per_ref": {r: sum(1 for x in src if x[0] == r) for r, _ in REFS},
           "self_agreement": self_agree, "reference_pair_agreement": ref_agree,
           "self_check_pass": all(v["agree"] == 1.0 for r, v in self_agree.items() if r != "c14"),
           "c14_note": "c14's in-place score[1:] -= score[:-1] is index-dependent and can open a later empty bin, "
                       "so its rebuilt arrays are not exact; its self-agreement is reported, not required",
           "secs": time.time() - t0}
    return res


def tests(res: dict) -> dict:
    """Testing plan item 3."""
    d = json.loads((PROBE_DIR / "P1.json").read_text())
    arrs = state_arrays(d["states"])
    bf = np.array([decide(bp.prio_bf, it, a) for it, a in arrs])
    import sandbox  # noqa: PLC0415
    renamed = ("def priority(item, bins):\n    # best fit, renamed and reformatted\n    leftover = bins - item\n"
               "    return -1.0 * leftover\n")
    fn, et, _ = sandbox.compile_program(renamed)
    assert fn is not None, et
    ren = sandbox._probe_decisions(fn, arrs)
    wf = np.array([decide(bp.prio_wf, it, a) for it, a in arrs])
    err = np.full(len(arrs), ERR, dtype=np.uint16)
    out = {"renamed_bf_vs_bf": agreement(ren, bf), "bf_vs_wf": agreement(bf, wf), "err_vs_err": agreement(err, err),
           "state_format_capacity_last": all(s[3] in (100, 150) and len(s) == 4 for s in d["states"])}
    out["pass"] = (out["renamed_bf_vs_bf"] == 1.0 and out["bf_vs_wf"] < 0.95 and out["err_vs_err"] == 0.0
                   and out["state_format_capacity_last"])
    return out


def main() -> None:
    r1 = build()
    sha1 = r1["file_sha256"]
    r2 = build()
    r1["rebuild_identical_sha256"] = sha1 == r2["file_sha256"]
    r1["tests"] = tests(r1)
    (ROOT / "results" / "probes.json").write_text(json.dumps(r1, indent=1))
    print(json.dumps({k: v for k, v in r1.items() if k != "reference_pair_agreement"}, indent=1))
    print(json.dumps(r1["reference_pair_agreement"], indent=1))
    if not (r1["self_check_pass"] and r1["rebuild_identical_sha256"] and r1["tests"]["pass"]):
        sys.exit(3)


if __name__ == "__main__":
    main()
