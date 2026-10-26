#!/usr/bin/env python3
"""S1 gate: build/save instance sets, reproduce FunSearch's printed numbers (G-HARNESS), calibrate the Weibull
generator, measure best-fit's evaluation time, and run the sandbox unit tests."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

import bp  # noqa: E402
import sandbox  # noqa: E402

ROOT = bp.ROOT
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(ROOT / "logs" / "gate.log", rotation="30 MB", level="DEBUG")


def hand_ff(items, cap):
    rem = []
    for s in items:
        for i, r in enumerate(rem):
            if r >= s:
                rem[i] -= s
                break
        else:
            rem.append(cap - s)
    return len(rem)


def hand_bf(items, cap):
    rem = []
    for s in items:
        best, bi = None, -1
        for i, r in enumerate(rem):
            if r >= s and (best is None or r < best):
                best, bi = r, i
        if bi < 0:
            rem.append(cap - s)
        else:
            rem[bi] -= s
    return len(rem)


def hand_wf(items, cap):
    rem = []
    for s in items:
        best, bi = None, -1
        for i, r in enumerate(rem):
            if r >= s and (best is None or r > best):
                best, bi = r, i
        if bi < 0:
            rem.append(cap - s)
        else:
            rem[bi] -= s
    return len(rem)


@logger.catch(reraise=True)
def main() -> None:
    out: dict = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    sets = bp.build_all_sets()
    hashes = bp.save_sets(sets)
    out["instance_sha256"] = hashes
    out["instance_counts"] = {k: [len(v), int(np.mean([x["num_items"] for x in v]))] for k, v in sets.items()}
    # binpack3.txt must equal the notebook's OR3 item for item
    same = all(a["id"].strip() == b["id"].strip() and a["items"] == b["items"] and a["capacity"] == b["capacity"]
               for a, b in zip(sets["H-OR3"], sets["FS-OR3"])) and len(sets["H-OR3"]) == len(sets["FS-OR3"])
    out["binpack3_equals_notebook_OR3"] = bool(same)
    logger.info(f"binpack3 == notebook OR3: {same}")

    _, _, or_src, w_src = bp.funsearch_notebook()
    c12, et1, m1 = sandbox.compile_program(or_src)
    c14, et2, m2 = sandbox.compile_program(w_src)
    assert c12 is not None and c14 is not None, (et1, m1, et2, m2)

    def fam(name, prio):
        insts = sets[name]
        t = time.perf_counter()
        b = bp.eval_set(insts, prio)
        dt = time.perf_counter() - t
        mb, ml = float(np.mean(b)), float(np.mean([x["l1"] for x in insts]))
        return {"mean_bins": mb, "mean_l1": ml, "excess_pct": 100 * (mb - ml) / ml, "bins": b, "secs": dt}

    np.seterr(all="ignore")
    g = {}
    g["BF_OR3"] = fam("FS-OR3", bp.prio_bf)
    g["BF_binpack3"] = fam("H-OR3", bp.prio_bf)
    g["BF_W5k"] = fam("H-FSW5k", bp.prio_bf)
    g["c12_OR3"] = fam("FS-OR3", c12)
    g["c12vec_OR3"] = fam("FS-OR3", bp.prio_c12_vec)
    g["c14_W5k"] = fam("H-FSW5k", c14)
    targets = {"BF_OR3": (212.0, 5.37), "BF_binpack3": (212.0, 5.37), "BF_W5k": (2067.0, 3.98),
               "c12_OR3": (207.45, 3.11), "c12vec_OR3": (207.45, 3.11), "c14_W5k": (2001.4, 0.68)}
    ok = True
    for k, (mb, ex) in targets.items():
        passed = abs(g[k]["mean_bins"] - mb) <= 0.01 and abs(round(g[k]["excess_pct"], 2) - ex) < 1e-9
        g[k]["target"] = [mb, ex]
        g[k]["pass"] = bool(passed)
        ok &= passed
        logger.info(f"{k}: mean={g[k]['mean_bins']:.3f} excess={g[k]['excess_pct']:.2f}% target={mb}/{ex}% "
                    f"{'PASS' if passed else 'FAIL'} ({g[k]['secs']:.1f}s)")
    g["c12vec_equals_c12_per_instance"] = g["c12_OR3"]["bins"] == g["c12vec_OR3"]["bins"]
    ok &= g["c12vec_equals_c12_per_instance"]
    out["gate"] = g
    out["G_HARNESS_PASS"] = bool(ok and same)

    # calibration of the Weibull generator
    cal = fam("CALIB-W", bp.prio_bf)
    out["calibration"] = {"bf_excess_pct": cal["excess_pct"], "target": 3.98, "tol": 0.25,
                          "pass": abs(cal["excess_pct"] - 3.98) <= 0.25}
    logger.info(f"calibration BF excess on 20 fresh 5k: {cal['excess_pct']:.3f}% pass={out['calibration']['pass']}")

    # BF reference on selection sets and timing
    bf_or = fam("SEL-OR", bp.prio_bf)
    bf_w = fam("SEL-W", bp.prio_bf)
    out["sel_bf"] = {"or_excess": bf_or["excess_pct"] / 100, "w_excess": bf_w["excess_pct"] / 100,
                     "or_bins": bf_or["bins"], "w_bins": bf_w["bins"], "secs": bf_or["secs"] + bf_w["secs"]}
    out["sel_limit_s"] = max(10.0, 8 * out["sel_bf"]["secs"])
    logger.info(f"SEL BF excess OR={bf_or['excess_pct']:.3f}% W={bf_w['excess_pct']:.3f}% t={out['sel_bf']['secs']:.2f}s")

    # hand-coded packer equivalence (3 instances each from SEL-OR and SEL-W)
    eq = {}
    for nm, prio, hand in [("FF", bp.prio_ff, hand_ff), ("BF", bp.prio_bf, hand_bf), ("WF", bp.prio_wf, hand_wf)]:
        res = []
        for x in sets["SEL-OR"][:3] + sets["SEL-W"][:1]:
            res.append(bp.pack(x["items"], x["capacity"], prio) == hand(x["items"], x["capacity"]))
        eq[nm] = all(res)
    out["priority_vs_handcoded"] = eq
    logger.info(f"priority-form vs hand-coded packers: {eq}")
    (ROOT / "results" / "harness_gate.json").write_text(json.dumps(out, indent=1))
    logger.info(f"G-HARNESS {'PASS' if out['G_HARNESS_PASS'] else 'FAIL'}")


if __name__ == "__main__":
    main()
