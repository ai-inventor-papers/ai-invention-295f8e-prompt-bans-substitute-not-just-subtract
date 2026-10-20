#!/usr/bin/env python3
"""Tracer unit tests (testing plan item 2).

1. CLRS-Text access order: for every CLRS binary_search trace, a CLRS-style lower-bound search wrapped in solve()
   is traced on the same input (values scaled to ints); the probe-index sequence the tracer records through the
   instrumented list must equal the midpoints implied by the CLRS (low, high) trace.
2. Probe determinism: tracing every reference twice gives identical feature lines (timing excluded).
3. Both labellers on every reference (also enforced by the build and the gate).
Writes results/tracer_unit_tests.json.
"""

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bench.common.astrules import ast_label  # noqa: E402
from bench.common.probes import run_trace  # noqa: E402
from bench.common.refs import REFS  # noqa: E402
from bench.common.rtrules import runtime_label  # noqa: E402

CLRS_BS = '''def solve(nums, target):
    low, high = 0, len(nums) - 1
    while low < high:
        mid = (low + high) // 2
        if nums[mid] < target:
            low = mid + 1
        else:
            high = mid
    return [low, high]
'''


def parse_bs(rec: dict):
    m = re.search(r"key: \[([^\]]*)\], target: ([0-9.]+), initial_trace: \((\d+), (\d+)\)", rec["input"])
    keys = [float(x) for x in m.group(1).split()]
    target = float(m.group(2))
    init = (int(m.group(3)), int(m.group(4)))
    trace_part, final = rec["output"].split("|")
    pairs = [tuple(map(int, p)) for p in re.findall(r"\((\d+), (\d+)\)", trace_part)]
    fin = tuple(map(int, re.findall(r"\d+", final)))
    seq = [init] + pairs + [fin]
    mids = [(l + h) // 2 for (l, h) in seq[:-1]]
    return keys, target, mids, fin


def clrs_test() -> dict:
    clrs = [c for c in json.loads((ROOT / "data" / "extract" / "clrs.json").read_text()) if c["algorithm"] == "binary_search"]
    ok, n, bad = 0, 0, []
    for c in clrs:
        try:
            keys, target, mids, fin = parse_bs(c)
        except (AttributeError, ValueError):
            continue
        nums = [round(k * 1000) for k in keys]
        tgt = round(target * 1000)
        if len(set(nums)) != len(nums) or tgt in nums:
            continue  # scaling collision: skip (strict order must survive the int scaling)
        probes = [{"name": "clrs", "kwargs_json": json.dumps({"nums": nums, "target": tgt}),
                   "wrap": {"nums": "clist_int"}}]
        tr = run_trace(CLRS_BS, "R6", probes=probes)
        got = tr["probes"]["clrs"]["features"]["clist_idx"]
        n += 1
        if got == mids:
            ok += 1
        elif len(bad) < 5:
            bad.append({"mids": mids, "tracer": got})
    return {"n_traces": n, "n_match": ok, "examples_mismatch": bad}


def determinism() -> dict:
    jobs = [(t, m, c) for t, d in REFS.items() for m, c in d.items()]

    def strip(tr):
        out = {}
        for p, v in tr["probes"].items():
            out[p] = {"error": v.get("error"), "features": v.get("features"), "result": v.get("result")}
        return json.dumps(out, sort_keys=True)

    def one(j):
        t, m, c = j
        a, b = run_trace(c, t), run_trace(c, t)
        return t, m, strip(a) == strip(b), runtime_label(t, a), ast_label(t, c)

    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(one, jobs))
    nondet = [f"{t}:{m}" for t, m, same, _, _ in res if not same]
    return {"n_references": len(res), "n_deterministic": sum(1 for r in res if r[2]), "nondeterministic": nondet,
            "runtime_labels_correct": sum(1 for t, m, _, rl, _ in res if rl == m),
            "ast_labels_correct": sum(1 for t, m, _, _, al in res if al == m)}


if __name__ == "__main__":
    out = {"clrs_binary_search_access_order": clrs_test(), "probe_determinism": determinism()}
    (ROOT / "results" / "tracer_unit_tests.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1)[:1500])
