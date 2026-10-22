#!/usr/bin/env python3
"""S0.1-S0.2: hardware/env record, read-only input copies into ./inputs/ with sha256, bench verification against
ITER2 exp11 bench/commitment.json, and the untouched copy of the ITER3 exp17 code base into ./src_base/.

Source paths are named ITER1/ITER2/ITER3 as in the plan; they are only READ. Missing sources are recorded (fallback
plan) rather than fatal, except the bench and the exp17 code, without which nothing can run.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
# Earlier iterations of this run (artifacts art_pVlCZ272hDV7 = exp17, art_1AYTO1Epb_7t = exp13, art__5akZ9W9iZM4 =
# exp16, art_ccAbfJVcv0LO = exp18, and the iteration-2 exp7 / exp11 artifacts), laid out as
# <AII_ITER_ROOT>/iter_<k>/gen_art/<artifact folder>. Default: the invention-loop folder that contains this workspace.
# Only needed to RE-CREATE ./inputs/, which ships with the repository (sha256 in results/input_hashes.json).
RUN = Path(os.environ.get("AII_ITER_ROOT", str(ROOT.parents[2])))
ITER1, ITER2, ITER3 = RUN / "round-1" / ".", RUN / "round-2" / ".", RUN / "round-3" / "."
# Declared dependency art_j3Rm_lr2nzR6 (published as a sibling folder; override with AII_DEP_ART_J3RM).
DEP = Path(os.environ.get("AII_DEP_ART_J3RM", str(ROOT.parent / "art_j3Rm_lr2nzR6")))
INPUTS = ROOT / "inputs"
RESULTS = ROOT / "results"

E17 = ITER3 / "gen_art_experiment_17"
E13 = ITER3 / "gen_art_experiment_13"
E16 = ITER3 / "gen_art_experiment_16"
E18 = ITER3 / "gen_art_experiment_18"
E11 = ITER2 / "gen_art_experiment_11"
E7 = ITER2 / "gen_art_experiment_7"
E6 = ITER1 / "gen_art_experiment_6"

# (source, destination relative to ./inputs) -- directories are copied recursively
COPIES: list[tuple[Path, str]] = [
    (E11 / "bench", "exp11/bench"),
    (E17 / "inputs" / "exp8", "exp8"),
    (E17 / "src", "exp17/src"),
    (E17 / "prompts" / "prompts.jsonl", "exp17/prompts/prompts.jsonl"),
    (E17 / "prompts" / "prompts_summary.json", "exp17/prompts/prompts_summary.json"),
    (E17 / "data" / "labels.jsonl", "exp17/data/labels.jsonl"),
    (E17 / "results" / "unit_tests_gpu.json", "exp17/results/unit_tests_gpu.json"),
    (E17 / "results" / "unit_tests_u1b.json", "exp17/results/unit_tests_u1b.json"),
    (E17 / "results" / "c2d.json", "exp17/results/c2d.json"),
    (E17 / "results" / "direction.json", "exp17/results/direction.json"),
    (E17 / "data" / "judge_cache.jsonl", "exp17/data/judge_cache.jsonl"),
    (E17 / "data" / "judge_cache_paths.jsonl", "exp17/data/judge_cache_paths.jsonl"),
    (E13 / "results" / "tensors", "exp13/results/tensors"),
    (E13 / "results" / "c1_events.jsonl", "exp13/results/c1_events.jsonl"),
    (E13 / "results" / "env.json", "exp13/results/env.json"),
    (E13 / "data" / "samples.jsonl", "exp13/data/samples.jsonl"),
    (E13 / "src" / "score.py", "exp13/src/score.py"),
    (E13 / "prompts" / "prompts.jsonl", "exp13/prompts/prompts.jsonl"),
    (E16 / "results" / "landing_by_route.json", "exp16/results/landing_by_route.json"),
    (E16 / "results" / "c1_events.jsonl", "exp16/results/c1_events.jsonl"),
    (E16 / "results" / "route.json", "exp16/results/route.json"),
    (E18 / "results" / "known_solutions_summary.json", "exp18/results/known_solutions_summary.json"),
    (E18 / "inputs" / "known_solutions.jsonl", "exp18/inputs/known_solutions.jsonl"),
    (E7 / "prompts" / "prompts_v2.json", "exp7/prompts/prompts_v2.json"),
    (E7 / "frozen" / "templates_nouns_padding.json", "exp7/frozen/templates_nouns_padding.json"),
    (E7 / "data" / "forced_selected.jsonl", "exp7/data/forced_selected.jsonl"),
    (E7 / "data" / "freeform_labelled.jsonl", "exp7/data/freeform_labelled.jsonl"),
    (E6 / "prompts" / "prompts.json", "exp6/prompts/prompts.json"),
    (DEP / "mini_data_out.json", "dep_art_j3Rm/mini_data_out.json"),
    (DEP / "preview_data_out.json", "dep_art_j3Rm/preview_data_out.json"),
]
EXP17_DIRS = [f"rand_{s}.npy" for s in range(9001, 9016)] + [f"norms_{t}.npy" for t in
                                                             ("T1", "T2", "T03", "T04", "T05", "T06")] + \
    ["direction_hashes.json"]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _copy(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    else:
        shutil.copy2(src, dst)
    return True


def env_record() -> dict[str, Any]:
    def sh(cmd: list[str]) -> str:
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout.strip()
        except (OSError, subprocess.SubprocessError) as e:
            return f"ERR {e}"
    q = Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
    per = Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
    mem = Path("/sys/fs/cgroup/memory/memory.limit_in_bytes")
    cpus = None
    if q.exists() and per.exists() and int(q.read_text()) > 0:
        cpus = int(q.read_text()) / int(per.read_text())
    return {
        "python": sys.version.split()[0], "platform": platform.platform(),
        "gpu": sh(["nvidia-smi", "--query-gpu=name,memory.total,compute_cap,driver_version", "--format=csv,noheader"]),
        "cgroup_cpu_quota": cpus, "cgroup_mem_limit_gb": int(mem.read_text()) / 1e9 if mem.exists() else None,
        "decision": {
            "rule": "plan S0.1 table: 16 GB Ada -> the exp17 FP8 W8A8 path with B = 20 (deviation F-precision)",
            "precision": "fp8_e4m3 W8A8 dynamic (decoder linears), bf16 embeddings/norms/lm_head",
            "B_bench": 20, "B_path": 20, "max_new_bench": 1024, "max_new_path": 1024,
            "note": "max_new 1024 for path tasks as in the exp17 screen (plan's 1536 was for the bf16 rows)"},
    }


def main() -> dict[str, Any]:
    INPUTS.mkdir(exist_ok=True)
    RESULTS.mkdir(exist_ok=True)
    missing, copied = [], []
    for src, d in COPIES:
        ok = _copy(src, INPUTS / d)
        (copied if ok else missing).append({"src_rel_iter": str(src).replace(str(RUN) + "/", ""), "dst": d})
    ddir = INPUTS / "exp17" / "directions"
    ddir.mkdir(parents=True, exist_ok=True)
    for f in EXP17_DIRS:
        if not _copy(E17 / "directions" / f, ddir / f):
            missing.append({"src_rel_iter": f"iter_3/gen_art/gen_art_experiment_17/directions/{f}", "dst": str(ddir)})
    # untouched copy of the exp17 code base
    sb = ROOT / "src_base"
    if not sb.exists() and (E17 / "src").exists():
        shutil.copytree(E17 / "src", sb, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    # bench verification against the ITER2 commitment
    src_com = E11 / "bench" / "commitment.json"
    local_com = INPUTS / "exp11" / "bench" / "commitment.json"
    com = json.loads((src_com if src_com.exists() else local_com).read_text())
    bench_dirs = {p.name.split("_")[0]: p for p in (INPUTS / "exp11" / "bench").iterdir() if p.is_dir()
                  and p.name[:1] in "TR"}
    mism, nchk = [], 0
    for t, v in com["tasks"].items():
        d = bench_dirs.get(t)
        for f, h in v["files"].items():
            if f == "catalogue":
                continue
            p = d / f if d else None
            got = sha256_file(p) if p is not None and p.exists() else None
            nchk += 1
            if got != h:
                mism.append({"task": t, "file": f, "expected": h, "got": got})
    hashes = {str(p.relative_to(ROOT)): sha256_file(p) for p in sorted(INPUTS.rglob("*"))
              if p.is_file() and "__pycache__" not in str(p)}
    out = {"copied": copied, "missing": missing, "bench_files_checked": nchk, "bench_mismatches": mism,
           "bench_pass": not mism, "sha256": hashes,
           "not_copied_by_design": {
               "dependency full_data_out.json (96 MB)": "read in place from the declared dependency workspace; the "
               "known-solution subset used by the novelty audit is extracted to inputs/dep_art_j3Rm/known_subset.jsonl"}}
    (RESULTS / "input_hashes.json").write_text(json.dumps(out, indent=1))
    (RESULTS / "env.json").write_text(json.dumps(env_record(), indent=1))
    if mism:
        raise SystemExit(f"bench mismatch against commitment.json: {mism[:3]}")
    print(f"copied {len(copied)}; missing {len(missing)}: {[m['src_rel_iter'] for m in missing]}; "
          f"bench {nchk} files ok")
    return out


if __name__ == "__main__":
    main()
