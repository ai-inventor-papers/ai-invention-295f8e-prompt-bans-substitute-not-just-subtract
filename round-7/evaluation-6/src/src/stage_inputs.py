"""A2: resolve every input named in builds_on, vendor it under inputs/<artifact_id>/, and hash it.

Resolution order per file: (1) the iteration-6 workspace path; (2) a staged copy in a directory named after the
artifact id under the run root (depth-limited search); (3) the artifact's full_method_out.json (recorded only:
every item here resolved at (1)). A missing file fails only its own item, which reports MISSING_INPUT.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from loguru import logger

import json

from common import DEP_DIRS, DEPS_ROOT, INPUTS, NONDEP_DIRS, REPORT_SRC, WS, sha256_file, write_json

FILES: dict[str, list[str]] = {
    "art_rMlbrjVB1c__": [
        "results/stage_a.json", "data/labels.jsonl", "predictions/commit0.json", "results/site_grid.json",
        "results/top5_push.json", "results/summary.md", "figures/F5_top5_geometry.png",
        "figures/F5_top5_geometry.pdf", "src/figures6.py", "results/novelty_audit.json",
    ],
    "art_zNyBP6zieI5u": [
        "results/das.json", "results/readout.json", "results/clamps.json", "results/rederive_headlines.json",
        "results/fork.json", "results/deviations.json", "results/geometry.json", "src/cfg.py", "src/figures_S.py",
        "figures/geometry_raw_L17.png", "figures/geometry_raw_L17.pdf", "figures/geometry_raw_L22.png",
        "figures/geometry_raw_L22.pdf", "figures/geometry_sae_L17.png", "figures/geometry_sae_L17.pdf",
        "figures/geometry_sae_L22.png", "figures/geometry_sae_L22.pdf",
    ],
    "art_dbUtqBjT0tPf": [
        "results/readout.json", "data/judgements.jsonl", "data/labels.jsonl", "cache/states_index.jsonl",
        "predictions/commit2_readout.json", "results/geometry.json", "src/figures.py", "analysis/readout.py",
        "analysis/stats.py", "figures/F6_geometry.png", "figures/F6_geometry.pdf", "figures/F8_mds_centroids.png",
        "figures/F8_mds_centroids.pdf",
    ],
    "art_lpQalcAXMGr1": [
        "data/labels.jsonl", "data/samples.jsonl", "data/iter4_relabelled.jsonl", "inputs/exp22/labels.jsonl",
        "results/pn.json", "results/verdict.json", "results/escape_by_engine.json", "results/known_solutions.json",
        "vendor/exp22/inputs/dep_art_j3Rm/known_subset.jsonl",
        "vendor/exp22/inputs/exp8/suite/tasks/t2_wsp/spec.txt",
        "vendor/exp22/inputs/exp8/suite/tasks/t2_wsp/tests.json",
        "vendor/exp22/inputs/exp8/suite/tasks/t2_wsp/limits.json",
    ],
    "art_aRTQM6CQ0Dre": [
        "corrections.json", "inputs/report/current_report.md", "src/adjudicate.py", "audit/rederive.py",
    ],
    "art_OUuQUYQn5voE": ["research_report.md", "evidence/quotes_iter6.jsonl"],
}
GLOBS = {"art_lpQalcAXMGr1": ["vendor/exp22/inputs/exp8/suite/tasks/t2_wsp/references/*.py"]}


def _staged_copy(artifact: str, rel: str) -> Path | None:
    for depth in ("*", "*/*", "*/*/*", "*/*/*/*"):
        for d in DEPS_ROOT.parent.glob(f"{depth}/{artifact}"):
            if INPUTS in d.resolve().parents or d.resolve() == INPUTS:
                continue  # our own vendored copies are not a staged source
            if (d / rel).exists():
                return d / rel
    return None


def _recorded() -> dict[str, str]:
    """sha256 of every vendored file as recorded by the run that vendored it (input_hashes.json)."""
    p = WS / "input_hashes.json"
    if not p.exists():
        return {}
    return {r["vendored_as"]: r["sha256"] for r in json.loads(p.read_text())["files"] if r.get("vendored_as")}


def _take(src: Path | None, dst: Path, how: str, rec: dict[str, str]) -> tuple[str, str | None]:
    rel = str(dst.relative_to(WS))
    if src is not None and src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.resolve() != dst.resolve():
            shutil.copy2(src, dst)
        return how, sha256_file(dst)
    if dst.exists() and rec.get(rel) == sha256_file(dst):
        return "vendored copy under inputs/ (sha256 matches input_hashes.json)", rec[rel]
    return "MISSING_INPUT", None


def resolve_all() -> dict:
    rec = _recorded()
    rows, missing = [], []
    for artifact, rels in FILES.items():
        base = DEP_DIRS.get(artifact) or NONDEP_DIRS.get(artifact)
        rels = list(rels)
        for g in GLOBS.get(artifact, []):
            found = sorted(str(p.relative_to(base)) for p in base.glob(g)) if base.is_dir() else []
            if not found:
                found = sorted(str(p.relative_to(INPUTS / artifact)) for p in (INPUTS / artifact).glob(g))
            rels += found
        for rel in rels:
            src, how = base / rel, "iteration-6 workspace path"
            if not src.exists():
                src, how = _staged_copy(artifact, rel), "staged copy under the run root"
            dst = INPUTS / artifact / rel
            how, sha = _take(src, dst, how, rec)
            if sha is None:
                missing.append(f"{artifact}:{rel}")
                logger.warning(f"MISSING_INPUT {artifact}:{rel}")
            rows.append({"path": f"{artifact}:{rel}", "vendored_as": str(dst.relative_to(WS)), "resolved": how,
                         "dependency": artifact in DEP_DIRS, "sha256": sha,
                         "bytes": dst.stat().st_size if dst.exists() else None})
    dst = INPUTS / "report" / "current_report.md"
    how, sha = _take(REPORT_SRC, dst, "read by path (the object being corrected)", rec)
    if sha is None:
        missing.append("report")
    rows.append({"path": "iter_7/gen_strat/current_report.md", "vendored_as": str(dst.relative_to(WS)),
                 "resolved": how, "dependency": False, "sha256": sha, "bytes": dst.stat().st_size if dst.exists() else None})
    out = {"n_files": len(rows), "n_missing": len(missing), "missing": missing, "files": rows,
           "note": "Paths are '<artifact_id>:<path inside that artifact's workspace>'; absolute server paths are "
                   "omitted on purpose. No file needed the full_method_out.json fallback."}
    write_json(WS / "input_hashes.json", out)
    logger.info(f"inputs: {len(rows)} files vendored, {len(missing)} missing")
    return out
