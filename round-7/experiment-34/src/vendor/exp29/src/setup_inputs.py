#!/usr/bin/env python3
"""S-1 SETUP: copy (read-only sources -> this workspace) every earlier-artifact file this artifact uses, with sha256.

vendor/exp22/  = iteration-4 exp22 (art_SHaWv77P1XCI) code + prompts + directions + inputs, copied unchanged; it is the
                 ROOT of the vendored code (its cfg.ROOT resolves to vendor/exp22), so its relative paths keep working.
vendor/exp19/  = exp19 engine_v4.py / sampling_v4.py / cfg.py (reference for the FP8Linear and PN conventions).
vendor/exp28/  = iteration-5 exp28 regate_rules.py (the re-gated array-Dijkstra T2 rule).
inputs/        = data and result files of exp22, exp19, exp27, exp28 read by the gates and the analysis.
Nothing is ever written into an earlier workspace. inputs/MANIFEST.json lists src, dst, size and sha256.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# the earlier run holding iterations 4-5 (read-only; override with AII_ITER45_ROOT)
RUN4 = Path(__import__("os").environ.get("AII_ITER45_ROOT", str(ROOT.parent / "iter45_sources")))
ITER4 = RUN4 / "round-4" / "."
ITER5 = RUN4 / "round-5" / "."
E22 = ITER4 / "experiment-22/src"
E19 = ITER4 / "experiment-19/src"
E27 = ITER5 / "experiment-27/src"
E28 = ITER5 / "experiment-28/src"
E25 = ITER5 / "experiment-25/src"

COPIES: list[tuple[Path, str]] = [
    # vendored code tree of exp22 (unchanged)
    (E22 / "src", "vendor/exp22/src"),
    (E22 / "src_base", "vendor/exp22/src_base"),
    (E22 / "analysis", "vendor/exp22/analysis"),
    (E22 / "prompts", "vendor/exp22/prompts"),
    (E22 / "directions", "vendor/exp22/directions"),
    (E22 / "inputs", "vendor/exp22/inputs"),
    (E22 / "predictions" / "c2_commit.json", "vendor/exp22/predictions/c2_commit.json"),
    (E22 / "results" / "units.json", "vendor/exp22/results/units.json"),
    (E22 / "results" / "units_nfree_R2.npy", "vendor/exp22/results/units_nfree_R2.npy"),
    (E22 / "data" / "judge_cache.jsonl", "vendor/exp22/data/judge_cache.jsonl"),
    (E22 / "data" / "judge_cache_paths.jsonl", "vendor/exp22/data/judge_cache_paths.jsonl"),
    # exp22 data + results used by the gates and the reproduction
    (E22 / "data" / "samples_raw.jsonl", "inputs/exp22/samples_raw.jsonl"),
    (E22 / "data" / "labels.jsonl", "inputs/exp22/labels.jsonl"),
    (E22 / "data" / "realised_disp.jsonl", "inputs/exp22/realised_disp.jsonl"),
    (E22 / "results" / "escape.json", "inputs/exp22/escape.json"),
    (E22 / "results" / "units.json", "inputs/exp22/units.json"),
    (E22 / "results" / "input_hashes.json", "inputs/exp22/input_hashes.json"),
    (E22 / "results" / "env.json", "inputs/exp22/env.json"),
    (E22 / "results" / "timing.jsonl", "inputs/exp22/timing.jsonl"),
    (E22 / "results" / "c2a.json", "inputs/exp22/c2a.json"),
    (E22 / "predictions" / "c2_commit.json", "inputs/exp22/c2_commit.json"),
    # exp19 (FP8 PN rows, engine_v4)
    (E19 / "src" / "engine_v4.py", "vendor/exp19/src/engine_v4.py"),
    (E19 / "src" / "sampling_v4.py", "vendor/exp19/src/sampling_v4.py"),
    (E19 / "src" / "cfg.py", "vendor/exp19/src/cfg.py"),
    (E19 / "src" / "hooks.py", "vendor/exp19/src/hooks.py"),
    (E19 / "data" / "samples.jsonl", "inputs/exp19/samples.jsonl"),
    (E19 / "data" / "samples_raw.jsonl", "inputs/exp19/samples_raw.jsonl"),
    (E19 / "data" / "realised.jsonl", "inputs/exp19/realised.jsonl"),
    # iteration 5
    (E28 / "src" / "regate_rules.py", "vendor/exp28/src/regate_rules.py"),
    (E28 / "results" / "iter4_rescored.json", "inputs/exp28/iter4_rescored.json"),
    (E28 / "results" / "regate.json", "inputs/exp28/regate.json"),
    (E27 / "results" / "engine_check.json", "inputs/exp27/engine_check.json"),
    (E27 / "results" / "unit_ratio.json", "inputs/exp27/unit_ratio.json"),
    (E27 / "results" / "defaults.json", "inputs/exp27/defaults.json"),
    (E27 / "data" / "labels.jsonl", "inputs/exp27/labels.jsonl"),
    (E25 / "results" / "extra_arm_a.json", "inputs/exp25/extra_arm_a.json"),
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    manifest = []
    missing = []
    for src, dst in COPIES:
        d = ROOT / dst
        if not src.exists():
            missing.append(str(src))
            continue
        if src.is_dir():
            if not d.exists():
                shutil.copytree(src, d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            files = [p for p in sorted(src.rglob("*")) if p.is_file() and "__pycache__" not in p.parts]
        else:
            d.parent.mkdir(parents=True, exist_ok=True)
            if not d.exists():
                shutil.copy2(src, d)
            files = [src]
        for f in files:
            rel = f.relative_to(src) if src.is_dir() else Path("")
            df = (d / rel) if src.is_dir() else d
            hs, hd = sha256_file(f), sha256_file(df)
            manifest.append({"src": str(f.relative_to(RUN4)), "dst": str(df.relative_to(ROOT)),
                             "bytes": df.stat().st_size, "sha256": hd, "copy_ok": hs == hd})
    bad = [m for m in manifest if not m["copy_ok"]]
    out = {"source_root": "run_aRfWvcSWjssb/3_invention_loop (read-only)", "n_files": len(manifest),
           "n_bad": len(bad), "missing": missing, "files": manifest}
    (ROOT / "inputs").mkdir(exist_ok=True)
    (ROOT / "inputs" / "MANIFEST.json").write_text(json.dumps(out, indent=1))
    sums = "\n".join(f"{m['sha256']}  {m['dst']}" for m in manifest if m["dst"].startswith("vendor/"))
    (ROOT / "vendor" / "SHA256SUMS").write_text(sums + "\n")
    print(f"copied/verified {len(manifest)} files, bad {len(bad)}, missing {missing}")
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
