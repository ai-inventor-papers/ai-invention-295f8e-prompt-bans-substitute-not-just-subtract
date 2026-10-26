#!/usr/bin/env python3
"""S-0 setup: resolve dependencies, copy the report and the small result JSONs into inputs/, vendor the named
source files unmodified into vendor/, record sha256 of every file read (inputs/SHA256SUMS), quote the committed
N3 bars verbatim."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from loguru import logger

from io_util import (A_BASE, A_GEO, A_REN, INPUTS, ROOT, VENDOR, _env_file, dep_root, env_value, read_json,
                     save_stage, sha256_file, write_json)

COPY = {
    A_REN: ["results/n1.json", "results/n1_tracer.json", "results/n3.json", "results/n3_tracer.json",
            "results/n3d.json", "results/n3d_tracer.json", "results/instrument_bounds.json",
            "results/manual_reads_summary.json", "results/heap_key_audit.json", "results/deviations.json",
            "results/headlines.json", "results/n2.json", "results/n2_tracer.json", "results/novelty_audit_v9.json",
            "commitments.log", "predictions/commit1a.json", "predictions/commit1b.json", "predictions/commit3.json",
            "data/manual_reads_v9.jsonl"],
    A_GEO: ["results/placement.json", "results/rsa.json", "results/lexical.json", "results/behavioural_distance.json",
            "results/surface_rdm.json", "results/n4_verdict.json", "data/descriptions_v0.json",
            "results/geometry_32b_mname.json", "results/geometry_32b_mdesc.json", "results/geometry_32b_mlex.json",
            "results/geometry_32b_mcode_PRIMARY_R1.json", "results/geometry_32b_mcode_PRIMARY_R2.json",
            "results/geometry_32b_mcode_M32_R1.json", "results/geometry_8b_mname.json",
            "results/geometry_8b_mdesc.json", "results/geometry_8b_mcode_PRIMARY_R1.json"],
    A_BASE: ["results/b3_summary.json", "results/b3_heldout_rows.jsonl", "results/random_sets.json",
             "results/b2_summary.json", "results/b1_gemma_G-GRID.json", "results/b1_summary.json",
             "results/spec_random_sets_B3.json", "results/spec_random_sets_T10.json"],
}
# large row files read in place (sha256 recorded, not copied)
IN_PLACE = {
    A_REN: ["data/samples_v9.jsonl", "results/retrace.jsonl"] + [
        f"data/labelled_v9_{c}.jsonl" for c in ("A_k1", "A_k2", "A_k3", "A_k4", "A_k5", "A_k5_ho", "E_k1", "E_k2",
                                                "E_k3", "E_k4", "E_k5", "E_k5_ho", "C_desc", "B_R1", "B_R2",
                                                "B_R3", "B_R4", "D_R5", "D_R6")],
    A_BASE: ["results/b2_tf_B3.jsonl", "results/b2_tf_T10.jsonl"],
}
VENDOR_FILES = {
    A_REN: ["src/analysis_v9.py", "src/stats_v9.py", "src/common.py"],
    A_GEO: ["src/stage_analysis.py"],
    A_BASE: ["src/b3_9.py", "src/cmap9.py", "src/stats9.py"],
}


def run() -> dict[str, Any]:
    sums: list[tuple[str, str]] = []
    env_lines = ["# resolved absolute paths (untracked; see .gitignore)"]
    copied, in_place, vendored = [], [], {}
    for art, files in COPY.items():
        root = dep_root(art)
        env_lines.append(f"DEP_{art}={root}")
        for rel in files:
            src = root / rel
            if not src.exists():
                logger.warning(f"missing {art}:{rel}")
                continue
            dst = INPUTS / art / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            h = sha256_file(src)
            assert h == sha256_file(dst)
            sums.append((h, f"{art}:{rel}"))
            copied.append(f"{art}:{rel}")
    for art, files in IN_PLACE.items():
        root = dep_root(art)
        for rel in files:
            src = root / rel
            if src.exists():
                sums.append((sha256_file(src), f"{art}:{rel} (read in place)"))
                in_place.append(f"{art}:{rel}")
            else:
                logger.warning(f"missing in-place {art}:{rel}")
    for art, files in VENDOR_FILES.items():
        root = dep_root(art)
        for rel in files:
            src = root / rel
            dst = VENDOR / art / Path(rel).name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            h = sha256_file(src)
            assert h == sha256_file(dst), f"vendored copy differs: {rel}"
            vendored[f"{art}:{rel}"] = h
            sums.append((h, f"{art}:{rel} (vendored unmodified to vendor/{art}/{Path(rel).name})"))
    rep = Path(env_value("REPORT") or (INPUTS / "report" / "current_report.md"))
    dst = INPUTS / "report" / "current_report.md"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if rep.resolve() != dst.resolve():
        shutil.copy2(rep, dst)
    rep_sha = sha256_file(rep)
    assert rep_sha == sha256_file(dst)
    sums.append((rep_sha, "report:iter_10/gen_strat/current_report.md (byte-identical copy at inputs/report/)"))
    env_lines.append(f"REPORT={rep}")
    (INPUTS / "SHA256SUMS").write_text("".join(f"{h}  {p}\n" for h, p in sums))
    merged = {**_env_file()}
    for ln in env_lines[1:]:
        k_, v_ = ln.split("=", 1)
        merged[k_] = v_
    (ROOT / ".env").write_text(env_lines[0] + "\n" + "".join(f"{k_}={v_}\n" for k_, v_ in merged.items()))
    (VENDOR / "SHA256SUMS").write_text("".join(f"{h}  {k}\n" for k, h in vendored.items()))
    c1a = read_json(INPUTS / A_REN / "predictions/commit1a.json")
    criteria = {
        "source": f"{A_REN}:predictions/commit1a.json#predictions.N3",
        "N3": c1a["predictions"]["N3"],
        "N1": c1a["predictions"].get("N1"),
        "N3-D": c1a["predictions"].get("N3-D"),
        "N2": c1a["predictions"].get("N2"),
    }
    write_json(ROOT / "results" / "criteria.json", criteria)
    out = {"status": "DONE", "n_copied": len(copied), "n_in_place": len(in_place), "n_vendored": len(vendored),
           "report_sha256": rep_sha, "report_bytes": rep.stat().st_size, "vendored_sha256": vendored,
           "copied": copied, "in_place": in_place, "criteria_quoted": criteria["N3"]["criteria"]}
    save_stage("s0_setup", out)
    return out
