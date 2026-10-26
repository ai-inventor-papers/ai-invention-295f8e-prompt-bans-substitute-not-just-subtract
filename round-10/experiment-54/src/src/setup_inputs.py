#!/usr/bin/env python3
"""S0: copy the reused iteration-8/9 inputs read-only into this workspace and record their sha256
(inputs/inputs_manifest.json). Stdlib only, so it runs before the venv exists."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Source locations are environment variables (the original run used the run volume's iteration-8/9 gen_art folders
# of run_0oWBKrKEGsmU). The copies already sit in inputs/ with their sha256 in inputs/inputs_manifest_public.json,
# so a reader of the published repository does not need these sources.
R9 = Path(os.environ.get("NOVR_ITER9_GEN_ART", str(ROOT.parent / "iter9_gen_art")))
R8 = Path(os.environ.get("NOVR_ITER8_GEN_ART", str(ROOT.parent / "iter8_gen_art")))
# Declared dependency art_j3Rm_lr2nzR6 (published as a sibling folder of this artifact).
DEP = Path(os.environ.get("NOVR_DEP_ART_J3RM", str(ROOT.parent / "art_j3Rm_lr2nzR6")))


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def copy(src: Path, dst: Path, rows: list[dict], role: str) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        rows.append({"role": role, "source": str(src), "dest": str(dst.relative_to(ROOT)), "status": "MISSING"})
        return
    shutil.copyfile(src, dst)
    mode = dst.stat().st_mode
    if role.startswith("input"):  # read-only copies of reused inputs
        dst.chmod(mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    rows.append({"role": role, "source": str(src), "dest": str(dst.relative_to(ROOT)), "sha256": sha256_file(dst),
                 "bytes": dst.stat().st_size, "status": "ok"})


def main() -> int:
    rows: list[dict] = []
    bp9 = R9 / "gen_art_experiment_48"
    for f in ["bp.py", "sandbox.py", "gate.py", "fetch_ext.py"]:
        copy(bp9 / "src" / f, ROOT / "inputs" / "bp9" / "src" / f, rows, "input:bp9-src")
    for p in sorted((bp9 / "data" / "instances").glob("*.json")):
        copy(p, ROOT / "data" / "instances" / p.name, rows, "data:bp9-instances")
    for p in sorted((bp9 / "ext").rglob("*")):
        if p.is_file():
            copy(p, ROOT / "ext" / p.relative_to(bp9 / "ext"), rows, "data:bp9-ext")
    copy(bp9 / "tools" / "cc", ROOT / "inputs" / "bp9" / "tools" / "cc", rows, "input:bp9-tools")
    for f in ["harness_gate.json", "ext_sources.json"]:
        copy(bp9 / "results" / f, ROOT / "inputs" / "bp9" / f, rows, "input:bp9-results")
    e45 = R9 / "experiment-45/src"
    for f in ["sample_v9.py", "common.py", "judge_tp.py", "stats_v9.py", "lexical.py"]:
        copy(e45 / "src" / f, ROOT / "inputs" / "exp45" / f, rows, "input:exp45-src")
    copy(e45 / "results" / "judge_gate_v9.json", ROOT / "inputs" / "exp45" / "judge_gate_v9.json", rows,
         "input:exp45-results")
    copy(R9 / "gen_art_experiment_49" / "start_vllm.sh", ROOT / "inputs" / "tsp9" / "start_vllm.sh", rows,
         "input:tsp9")
    copy(R8 / "experiment-44/src" / "src" / "common.py", ROOT / "inputs" / "exp44" / "common.py", rows,
         "input:exp44-src")
    for f in ["preview_data_out.json", "mini_data_out.json", "reproducibility.md", "data.py"]:
        copy(DEP / f, ROOT / "inputs" / "dep_j3Rm" / f, rows, "input:dependency")
    out = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "n_files": len(rows),
           "n_missing": sum(r["status"] != "ok" for r in rows), "files": rows,
           "dependency_full_data_out": {"path": str(DEP / "full_data_out.json"),
                                        "sha256": sha256_file(DEP / "full_data_out.json"),
                                        "note": "read in place (96 MB); only the xlcost_python FF/BF/WF/NF and "
                                                "bin-packing rows are extracted into data/human_formulations.json"}}
    (ROOT / "inputs" / "inputs_manifest.json").write_text(json.dumps(out, indent=1))
    print(f"copied {len(rows)} files, missing {out['n_missing']}")
    return 0 if out["n_missing"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
