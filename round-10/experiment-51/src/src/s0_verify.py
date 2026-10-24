#!/usr/bin/env python3
"""S0 VERIFY + GATE wrapper.

verify : instance sets copied from BP9 must hash to BP9's harness_gate.json AND to the second copy embedded in the
         plan; every ext file must match ext_sources.json; the two notebook copies must be byte-identical.
gate   : run after `uv run python -I src/gate.py`; diff the new gate block against BP9's, check the printed targets,
         grep gate.py for the set names, and write results/harness_gate_v10.json plus the derived V1 thresholds.
Any mismatch writes results/failure_record.json and exits non-zero (no search call may follow)."""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bp  # noqa: E402

ROOT = bp.ROOT
EMBEDDED = {
    "SEL-OR": "4fa84e1e8d2fcb7d7a49f2fc4b6dff3c14c6980f741d7e6c9804c46f47de82d7",
    "SEL-W": "7f95af860eabf585434030cbb95b62f217a7b23443bbed0e60f1b8c2974e68d3",
    "H-W5k": "eb4d3c6629da9ac1533985963a22edede519dd73c75f19d51c0190ff3c505b1a",
    "H-W10k": "cf5cd9b599a58b5932602759e844e112fd08cb04cb38536bc9767ebcb7f8f4f0",
    "H-SHIFT": "6a98e8c395aeb14fb47cf24f334dfd84d575ee320391ec76c670ff361d7ba9ff",
    "CALIB-W": "5e7b0468448900469cdf8e8756188bfce30b4ce3e3f6c43277f3d3bb72127cdd",
    "P1SRC-W": "e6eb2fb86a9da2d6fa849099b25cc4712061858f7af18d41ca4f78e5bc3af6e1",
    "P1SRC-OR": "3a2a73f5af220e978e00614ea087769306ed0da0f18a440f90502c150fdc715c",
    "H-OR1": "c5604b1a056c7b1070b58846550e1b991bf3e47eac59167d5886641957b358a6",
    "H-OR2": "0e1fd208f26139b94359b4abb0ca2a1574f70b7cceda139fc30ac8612307d13c",
    "H-OR3": "b89390f503db5bd471361efb3b9aa57c147be39678f78f64d1fe13df533d31a1",
    "FS-OR3": "b89390f503db5bd471361efb3b9aa57c147be39678f78f64d1fe13df533d31a1",
    "H-OR4": "1014d8c716c511745b902a5bbd82db66b7fbcc1541267aabd2a477927299c2d5",
    "H-FSW5k": "e58e2ff43f97b0093407a2efdbd68b0dce316b79c5352e39073c53ce57ee9703",
}
NOTEBOOK_SHA = "eec45846a8661722addbb856179327cf2ede0bc502e32be4ad58a6ac54e0aca6"
BF_OR3_EXC, BF_FSW5K_EXC = 5.367793240556666, 3.9843042559613666


def utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def fail(stage: str, problems: list) -> None:
    rec = {"utc": utc(), "stage": stage, "problems": problems, "action": "STOP: no search call is made"}
    (ROOT / "results" / "failure_record.json").write_text(json.dumps(rec, indent=1))
    print(json.dumps(rec, indent=1))
    sys.exit(2)


def verify() -> dict:
    bp9_gate = json.loads((ROOT / "results" / "harness_gate_bp9.json").read_text())
    problems, rows = [], {}
    for name, emb in EMBEDDED.items():
        h = bp.sha_insts(bp.load_set(name))
        ok = h == emb == bp9_gate["instance_sha256"][name]
        rows[name] = {"sha256": h, "embedded": emb, "bp9_gate": bp9_gate["instance_sha256"][name], "match": ok}
        if not ok:
            problems.append(f"instance hash mismatch {name}")
    ext_rows = []
    for e in json.loads((ROOT / "results" / "ext_sources.json").read_text()):
        p = ROOT / e["local"]
        h = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
        ok = h == e.get("sha256")
        ext_rows.append({"local": e["local"], "sha256": h, "expected": e.get("sha256"), "match": ok})
        if not ok:
            problems.append(f"ext hash mismatch {e['local']}")
    nb1 = (ROOT / "ext" / "funsearch" / "bin_packing.ipynb").read_bytes()
    nb2 = (ROOT / "ext" / "funsearch" / "bin_packing__bin_packing.ipynb").read_bytes()
    nb_ok = nb1 == nb2 and hashlib.sha256(nb1).hexdigest() == NOTEBOOK_SHA
    if not nb_ok:
        problems.append("notebook copies differ or notebook sha mismatch")
    out = {"utc": utc(), "instances": rows, "ext": ext_rows, "notebook_copies_identical": nb1 == nb2,
           "notebook_sha256": hashlib.sha256(nb1).hexdigest(), "problems": problems}
    (ROOT / "results" / "s0_verify.json").write_text(json.dumps(out, indent=1))
    if problems:
        fail("S0-verify", problems)
    print(f"S0 VERIFY PASS: {len(rows)} instance sets, {len(ext_rows)} ext files, notebook copies identical")
    return out


def gate() -> dict:
    new = json.loads((ROOT / "results" / "harness_gate.json").read_text())
    old = json.loads((ROOT / "results" / "harness_gate_bp9.json").read_text())
    problems = []
    if not new.get("G_HARNESS_PASS"):
        problems.append("G_HARNESS_PASS false")
    strip = lambda g: {k: ({kk: vv for kk, vv in v.items() if kk != "secs"} if isinstance(v, dict) else v)  # noqa: E731
                       for k, v in g.items()}
    gate_identical = strip(new["gate"]) == strip(old["gate"])
    if not gate_identical:
        problems.append("gate block differs from BP9 (timings excluded)")
    if new["instance_sha256"] != old["instance_sha256"]:
        problems.append("rebuilt instance hashes differ from BP9")
    for k, emb in EMBEDDED.items():
        if new["instance_sha256"].get(k) != emb:
            problems.append(f"rebuilt {k} differs from embedded hash")
    g = new["gate"]
    exact = {"BF_OR3": (212.0, 5.36779), "BF_W5k": (2067.0, 3.98430), "c12_OR3": (207.45, 3.10636),
             "c14_W5k": (2001.4, 0.68417)}
    exact_rows = {}
    for k, (mb, ex) in exact.items():
        ok = abs(g[k]["mean_bins"] - mb) < 1e-9 and abs(g[k]["excess_pct"] - ex) < 5e-6
        exact_rows[k] = {"mean_bins": g[k]["mean_bins"], "excess_pct": g[k]["excess_pct"], "target": [mb, ex], "ok": ok}
        if not ok:
            problems.append(f"{k} not reproduced exactly")
    cal = new["calibration"]
    if not (abs(cal["bf_excess_pct"] - 3.98) <= 0.25 and abs(cal["bf_excess_pct"] - 4.126) < 5e-4):
        problems.append("calibration out of range")
    sel = new["sel_bf"]
    if abs(sel["or_excess"] - 0.05997931747673214) > 1e-12 or abs(sel["w_excess"] - 0.042309606769537086) > 1e-12:
        problems.append("SEL BF excess differs")
    if not all(new["priority_vs_handcoded"].values()):
        problems.append("priority-form FF/BF/WF differ from hand-coded packers")
    src = (ROOT / "src" / "gate.py").read_text()
    grep_ok = bool(re.search(r'g\["BF_W5k"\]\s*=\s*fam\("H-FSW5k"', src)) and \
        bool(re.search(r'g\["BF_OR3"\]\s*=\s*fam\("FS-OR3"', src))
    if not grep_ok:
        problems.append("gate.py set names (BF_W5k->H-FSW5k, BF_OR3->FS-OR3) not found")
    out = dict(new)
    out.update({"v10_utc": utc(), "gate_block_identical_to_bp9": gate_identical, "exact_targets": exact_rows,
                "gate_py_grep_ok": grep_ok, "problems": problems,
                "c14_W5k_secs_this_machine": g["c14_W5k"]["secs"], "bp9_c14_W5k_secs": old["gate"]["c14_W5k"]["secs"]})
    (ROOT / "results" / "harness_gate_v10.json").write_text(json.dumps(out, indent=1))
    if problems:
        fail("S0-gate", problems)
    thr = {"utc": utc(), "thr_FSW5k_pct": 0.8 * BF_FSW5K_EXC, "thr_OR3_pct": 0.8 * BF_OR3_EXC,
           "bf_FSW5k_pct": BF_FSW5K_EXC, "bf_OR3_pct": BF_OR3_EXC,
           "rule": "V1 bar = 0.8 x best fit's excess on each primary held-out set"}
    (ROOT / "predictions" / "thresholds.json").write_text(json.dumps(thr, indent=1))
    print(f"G-HARNESS v10 PASS; gate block identical to BP9: {gate_identical}; thresholds {thr}")
    return out


if __name__ == "__main__":
    {"verify": verify, "gate": gate}[sys.argv[1]]()
