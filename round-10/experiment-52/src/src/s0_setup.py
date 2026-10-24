#!/usr/bin/env python3
"""S0: record copied inputs (inputs_manifest.json), verify instance and ext hashes against the BP9 records,
run gate.py, check every gate target and re-verify the rewritten instance sets. Any mismatch -> failure record."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from loguru import logger  # noqa: E402

import common as C  # noqa: E402

# The iteration-9 workspaces (BP9: gen_art_experiment_48, TSP9: gen_art_experiment_49 of run_0oWBKrKEGsmU) are the copy
# sources. They are not published; their copied files ARE (src/, data/instances/, ext/, inputs/), so without BP9_DIR the
# stage runs in verify-only mode against inputs_manifest.json.
BP9 = Path(os.environ.get("BP9_DIR", "__unset__"))
TSP9 = Path(os.environ.get("TSP9_DIR", "__unset__"))
COPIED = [("src/bp.py", "src/bp.py"), ("src/sandbox.py", "src/sandbox.py"), ("src/gate.py", "src/gate.py"),
          ("src/fetch_ext.py", "src/fetch_ext.py"), ("tools/cc", "tools/cc"),
          ("results/harness_gate.json", "inputs/bp9_harness_gate.json"),
          ("results/ext_sources.json", "inputs/bp9_ext_sources.json")]
GATE_TARGETS = {"BF_OR3": (212.0, 5.37), "BF_binpack3": (212.0, 5.37), "BF_W5k": (2067.0, 3.98),
                "c12_OR3": (207.45, 3.11), "c12vec_OR3": (207.45, 3.11), "c14_W5k": (2001.4, 0.68)}


def fail(check: str, expected, observed) -> None:
    C.write_json(C.RESULTS / "failure_record.json", dict(utc=C.utc(), check=check, expected=expected,
                                                         observed=observed))
    logger.error(f"S0 FAILURE {check}: expected={expected} observed={observed}")
    raise SystemExit(2)


def build_manifest() -> list[dict]:
    rows = []
    for src_rel, dst_rel in COPIED:
        p = C.ROOT / dst_rel
        rows.append(dict(path=dst_rel, source=str(BP9 / src_rel), sha256=C.sha256_file(p), bytes=p.stat().st_size,
                         source_sha256=C.sha256_file(BP9 / src_rel), utc=C.utc()))
    for p in sorted((C.ROOT / "data" / "instances").glob("*.json")):
        rel = p.relative_to(C.ROOT).as_posix()
        rows.append(dict(path=rel, source=str(BP9 / rel), sha256=C.sha256_file(p), bytes=p.stat().st_size,
                         source_sha256=C.sha256_file(BP9 / rel), utc=C.utc()))
    for p in sorted((C.ROOT / "ext").rglob("*")):
        if p.is_file():
            rel = p.relative_to(C.ROOT).as_posix()
            rows.append(dict(path=rel, source=str(BP9 / rel), sha256=C.sha256_file(p), bytes=p.stat().st_size,
                             source_sha256=C.sha256_file(BP9 / rel), utc=C.utc()))
    p = C.ROOT / "inputs" / "start_vllm.sh"
    rows.append(dict(path="inputs/start_vllm.sh", source=str(TSP9 / "start_vllm.sh"), sha256=C.sha256_file(p),
                     bytes=p.stat().st_size, source_sha256=C.sha256_file(TSP9 / "start_vllm.sh"), utc=C.utc()))
    for r in rows:
        if r["sha256"] != r["source_sha256"]:
            fail(f"copy {r['path']}", r["source_sha256"], r["sha256"])
    return rows


def verify_instances(stage: str) -> dict:
    import bp
    rec = json.loads((C.ROOT / "inputs" / "bp9_harness_gate.json").read_text())["instance_sha256"]
    out = {}
    for name, h in rec.items():
        got = bp.sha_insts(bp.load_set(name))
        out[name] = got == h
        if got != h:
            fail(f"{stage} instance sha {name}", h, got)
    logger.info(f"{stage}: all {len(rec)} instance sets match the BP9 record")
    return out


def verify_ext() -> dict:
    src = json.loads((C.ROOT / "inputs" / "bp9_ext_sources.json").read_text())
    out = {}
    for e in src:
        if e.get("status") != "ok":
            continue
        p = C.ROOT / e["local"]
        got = C.sha256_file(p)
        out[e["local"]] = got == e["sha256"]
        if got != e["sha256"]:
            fail(f"ext sha {e['local']}", e["sha256"], got)
    # bp.py reads ext/funsearch/bin_packing.ipynb: it must be byte-identical to the recorded notebook
    nb = [e for e in src if e.get("source") == "funsearch"][0]
    got = C.sha256_file(C.ROOT / "ext" / "funsearch" / "bin_packing.ipynb")
    out["ext/funsearch/bin_packing.ipynb"] = got == nb["sha256"]
    if got != nb["sha256"]:
        fail("ext sha ext/funsearch/bin_packing.ipynb", nb["sha256"], got)
    logger.info(f"ext: {len(out)} files match ext_sources.json (text.txt is derived from the HTML, unrecorded)")
    return out


@logger.catch(reraise=True)
def main() -> None:
    C.setup_logging("s0_setup")
    sys.path.insert(0, str(C.SRC))
    if BP9.exists() and TSP9.exists():
        manifest = build_manifest()
        C.write_json(C.ROOT / "inputs_manifest.json", manifest)
        logger.info(f"inputs_manifest.json: {len(manifest)} files copied and hash-identical to their sources")
    else:  # verify-only: the copies shipped in this folder must still match the recorded hashes
        for r in json.loads((C.ROOT / "inputs_manifest.json").read_text()):
            p = C.ROOT / r["path"]
            if p.name == "cc":  # the compiler shim is rewritten for portability (deviation 'cc_shim')
                continue
            if C.sha256_file(p) != r["sha256"]:
                fail(f"verify-only {r['path']}", r["sha256"], C.sha256_file(p))
        logger.info("verify-only mode: every shipped copy matches inputs_manifest.json")
    res = {"utc": C.utc(), "pre_gate_instances": verify_instances("pre-gate"), "ext": verify_ext()}
    copied_gate = json.loads((C.ROOT / "inputs" / "bp9_harness_gate.json").read_text())
    r = subprocess.run([sys.executable, str(C.SRC / "gate.py")], capture_output=True, text=True, cwd=C.ROOT,
                       timeout=600)
    (C.LOGS / "gate_stdout.log").write_text(r.stdout + "\n" + r.stderr)
    if r.returncode != 0 or "G-HARNESS PASS" not in r.stdout:
        fail("gate.py G-HARNESS PASS line", "G-HARNESS PASS", r.stdout[-2000:] + r.stderr[-2000:])
    g = json.loads((C.ROOT / "results" / "harness_gate.json").read_text())
    for k, (mb, ex) in GATE_TARGETS.items():
        if not g["gate"][k]["pass"] or abs(g["gate"][k]["mean_bins"] - mb) > 0.01 \
                or round(g["gate"][k]["excess_pct"], 2) != ex:
            fail(f"gate target {k}", [mb, ex], [g["gate"][k]["mean_bins"], g["gate"][k]["excess_pct"]])
    checks = {
        "c12vec_equals_c12_per_instance": g["gate"]["c12vec_equals_c12_per_instance"] is True,
        "binpack3_equals_notebook_OR3": g["binpack3_equals_notebook_OR3"] is True,
        "calibration_within_3.98pm0.25": abs(g["calibration"]["bf_excess_pct"] - 3.98) <= 0.25,
        "priority_vs_handcoded_all": all(g["priority_vs_handcoded"].values()),
        "sel_bf_or_identical": g["sel_bf"]["or_excess"] == copied_gate["sel_bf"]["or_excess"],
        "sel_bf_w_identical": g["sel_bf"]["w_excess"] == copied_gate["sel_bf"]["w_excess"],
        "G_HARNESS_PASS": g["G_HARNESS_PASS"] is True,
    }
    for k, v in checks.items():
        if not v:
            fail(f"gate check {k}", True, v)
    res["gate_targets"] = {k: [g["gate"][k]["mean_bins"], round(g["gate"][k]["excess_pct"], 4)] for k in GATE_TARGETS}
    res["gate_checks"] = checks
    res["set_to_target_mapping"] = {"BF_OR3": "FS-OR3", "BF_binpack3": "H-OR3", "BF_W5k": "H-FSW5k",
                                    "c12_OR3": "FS-OR3", "c12vec_OR3": "FS-OR3", "c14_W5k": "H-FSW5k"}
    res["post_gate_instances"] = verify_instances("post-gate")
    res["S0_PASS"] = True
    C.write_json(C.RESULTS / "s0_verify.json", res)
    C.ledger("S0 gate passed", planned_h=0.75)
    logger.info("S0 PASS: copied hashes verified, G-HARNESS PASS with every target, rewritten sets re-verified")


if __name__ == "__main__":
    main()
