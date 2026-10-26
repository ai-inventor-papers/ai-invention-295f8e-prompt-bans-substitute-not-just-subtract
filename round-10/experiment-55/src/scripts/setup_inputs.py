#!/usr/bin/env python3
"""Stage 0.2: copy the reused code and inputs of the prior artifacts into this workspace (read-only sources), record
sha256 of every copied file in inputs_manifest.json, and cross-check the duplicate copies (plan T1).

Code (exp46 / exp45 src) goes to src/ unchanged; the harness, labeller and suites to vendor/; data and results to
inputs/<artifact_id>/. The large frozen state caches of exp46 (cache/states/*.npz, 0.6 GB) are NOT copied: they are
read in place and their sha256 is recorded (deviation D-inputs-inplace)."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEPS_DIR = Path(os.environ.get("TPG_DEPS_DIR", str(ROOT.parent)))      # sibling artifact folders, named by artifact id


def dep(art_id: str) -> Path:
    return Path(os.environ.get("TPG_DEP_" + art_id.replace("-", "_"), str(DEPS_DIR / art_id)))


E46 = dep("art_VVA3P0ocZNA2")          # iteration-9 gen_art_experiment_46
E45 = dep("art_8nXdw3_lDAll")          # iteration-9 gen_art_experiment_45
E44 = dep("art_R-HSmXq2t97f")          # iteration-8 gen_art_experiment_44
EXP9 = dep("art_IVZc3TWCeE9f")         # iteration-2 gen_art_experiment_9
EXP2 = dep("art_D6Z0Snf09sFL")         # iteration-1 gen_art_experiment_2
DSET = dep("art_j3Rm_lr2nzR6")         # declared dependency, iteration-1 gen_art_dataset_1
IDS = {"E46": "art_VVA3P0ocZNA2", "E45": "art_8nXdw3_lDAll", "E44": "art_R-HSmXq2t97f", "EXP9": "art_IVZc3TWCeE9f",
       "EXP2": "art_D6Z0Snf09sFL", "DSET": "art_j3Rm_lr2nzR6"}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    copies: list[tuple[Path, Path, str]] = []
    # ---- code reused unchanged (src/)
    for f in ("common.py", "geometry.py", "landing.py", "states.py", "stage_mcode.py", "programs.py", "prompts_tp.py",
              "tpg.py", "label_tp.py", "expansion.py", "expansion_child.py", "judge_tp.py", "sample_or.py"):
        copies.append((E46 / "src" / f, ROOT / "src" / f, IDS["E46"]))
    for f in ("tracer_v9.py", "orderclass.py", "probes_v9.py"):
        copies.append((E45 / "src" / f, ROOT / "src" / f, IDS["E45"]))
    for f in ("probes_v9.json", "probes_v9.json.sha256"):
        copies.append((E45 / "probes" / f, ROOT / "probes" / f, IDS["E45"]))
    # ---- harness, labeller, suites (vendor/)
    copies.append((E46 / "vendor/exp9/__init__.py", ROOT / "vendor/exp9/__init__.py", IDS["E46"]))
    for p in sorted((E46 / "vendor/exp9/tasks").rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            copies.append((p, ROOT / "vendor/exp9/tasks" / p.relative_to(E46 / "vendor/exp9/tasks"), IDS["E46"]))
    for p in sorted((EXP9 / "labeller_ext").glob("*")):     # exp46's vendor copy of labeller_ext is empty now
        if p.is_file() and p.suffix in (".py", ".jsonl"):
            copies.append((p, ROOT / "vendor/exp9/labeller_ext" / p.name, IDS["EXP9"]))
    for f in ("harness.py", "hidden_tests_t1.json"):
        copies.append((E46 / "vendor/exp2" / f, ROOT / "vendor/exp2" / f, IDS["E46"]))
    # ---- inputs/exp9 (prompts_tp reads INPUTS/exp9/prompts and INPUTS/exp9/tasks/t1_grid/spec.txt)
    for p in sorted((E46 / "inputs/exp9/prompts").glob("*.json")):
        copies.append((p, ROOT / "inputs/exp9/prompts" / p.name, IDS["E46"]))
    for p in sorted((E46 / "inputs/exp9/tasks").rglob("*")):
        if p.is_file():
            copies.append((p, ROOT / "inputs/exp9/tasks" / p.relative_to(E46 / "inputs/exp9/tasks"), IDS["E46"]))
    # ---- exp46 data / results
    a = IDS["E46"]
    for f in ("data/mcode_sets.json", "data/mcode_contexts.json", "data/probe_grids.json", "data/topups.jsonl",
              "results/geometry_8b_mcode_PRIMARY_R1.json", "results/geometry_32b_mcode_PRIMARY_R1.json",
              "results/geometry_32b_mcode_PRIMARY_R2.json", "results/placement.json", "results/rsa.json",
              "results/n4_verdict.json", "results/topups.json", "results/states_mcode_8b.json",
              "results/states_mcode_32b.json", "results/surface_rdm.json", "inputs/neutral_nouns.json",
              "predictions/commit2.json", "README.md"):
        copies.append((E46 / f, ROOT / "inputs" / a / f, a))
    a = IDS["E45"]
    for f in ("data/survivors_for_tpg.jsonl", "data/manual_reads_v9.jsonl", "data/samples_v9.jsonl",
              "results/retrace.jsonl", "results/retrace_extras.jsonl", "README.md"):
        copies.append((E45 / f, ROOT / "inputs" / a / f, a))
    a = IDS["E44"]
    for f in ("data/labelled_C6_ban.jsonl", "data/labelled_C6_confirm.jsonl", "data/labelled_C6_baseline.jsonl",
              "data/manual_reads.jsonl"):
        copies.append((E44 / f, ROOT / "inputs" / a / f, a))
    manifest = {"utc": datetime.now(timezone.utc).isoformat(), "artifact_ids": IDS, "files": [], "in_place": [],
                "cross_checks": []}
    for src, dst, aid in copies:
        if not src.exists():
            manifest["files"].append({"src_artifact": aid, "dst": str(dst.relative_to(ROOT)), "missing": True})
            print(f"MISSING {src}", file=sys.stderr)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        manifest["files"].append({"src_artifact": aid, "src_rel": _rel(src), "dst": str(dst.relative_to(ROOT)),
                                  "sha256": sha(dst), "bytes": dst.stat().st_size})
    # ---- read in place (large frozen caches; dependency dataset)
    for f in ("cache/states/mcode_8b.npz", "cache/states/mcode_32b.npz", "cache/states/geo_8b_mcode_PRIMARY_R1_k15.npz",
              "cache/states/geo_8b_mcode_PRIMARY_R1_k10.npz", "cache/states/geo_32b_mcode_PRIMARY_R1_k15.npz",
              "cache/states/geo_32b_mcode_PRIMARY_R1_k10.npz"):
        p = E46 / f
        manifest["in_place"].append({"src_artifact": IDS["E46"], "path_in_artifact": f, "sha256": sha(p),
                                     "bytes": p.stat().st_size})
    p = DSET / "full_data_out.json"
    manifest["in_place"].append({"src_artifact": IDS["DSET"], "path_in_artifact": "full_data_out.json",
                                 "sha256": sha(p), "bytes": p.stat().st_size})
    # ---- duplicate-copy cross-checks (T1)
    checks = []
    for p in sorted((EXP9 / "tasks/t1_grid/references").glob("*.py")):
        q = ROOT / "vendor/exp9/tasks/t1_grid/references" / p.name
        checks.append({"what": f"reference {p.name}", "equal": q.exists() and sha(p) == sha(q)})
    for f in ("tests.json", "limits.json", "spec.txt"):
        checks.append({"what": f"t1_grid/{f}", "equal": sha(EXP9 / "tasks/t1_grid" / f) ==
                       sha(ROOT / "vendor/exp9/tasks/t1_grid" / f)})
    e2 = EXP2 / "hidden_tests_t1.json"
    if not e2.exists():
        cands = list(EXP2.rglob("hidden_tests_t1.json"))
        e2 = cands[0] if cands else e2
    checks.append({"what": "41-case suite vs ITER1 exp2", "equal": e2.exists() and
                   sha(e2) == sha(ROOT / "vendor/exp2/hidden_tests_t1.json")})
    for f in ("ast_rules.py", "runtime_rules.py", "tracer.py", "combine.py"):
        q = E46 / "inputs/exp9/labeller_ext" / f
        checks.append({"what": f"labeller_ext/{f} vs exp46 inputs copy", "equal": q.exists() and
                       sha(q) == sha(ROOT / "vendor/exp9/labeller_ext" / f)})
    pj = ROOT / "probes/probes_v9.json"
    want = (ROOT / "probes/probes_v9.json.sha256").read_text().split()[0]
    checks.append({"what": "probes_v9.json vs .sha256", "equal": sha(pj) == want})
    c44 = E44 / "src/common.py"
    if c44.exists():
        import importlib.util
        out = {}
        for tag, path in (("e44", c44), ("e46", ROOT / "src/common.py")):
            spec = importlib.util.spec_from_file_location(f"common_{tag}", path)
            txt = path.read_text()
            i0 = txt.index("ALIAS_TABLE: dict")
            i1 = txt.index("W_TEMPLATES")
            out[tag] = hashlib.sha256(txt[i0:i1].encode()).hexdigest()
            _ = spec
        checks.append({"what": "ALIAS_TABLE + SHORT_FORMS block e44 vs e46", "equal": out["e44"] == out["e46"]})
    manifest["cross_checks"] = checks
    (ROOT / "inputs_manifest.json").write_text(json.dumps(manifest, indent=1))
    bad = [c for c in checks if not c["equal"]]
    missing = [f for f in manifest["files"] if f.get("missing")]
    print(f"copied {len(manifest['files']) - len(missing)} files, {len(missing)} missing; "
          f"{len(checks) - len(bad)}/{len(checks)} cross-checks equal")
    for c in bad:
        print("MISMATCH", c["what"])


def _rel(p: Path) -> str:
    for k, base in (("E46", E46), ("E45", E45), ("E44", E44), ("EXP9", EXP9), ("EXP2", EXP2), ("DSET", DSET)):
        try:
            return f"{IDS[k]}/{p.relative_to(base)}"
        except ValueError:
            continue
    return p.name


if __name__ == "__main__":
    main()
