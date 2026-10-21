"""Stage implementations called by eval.py. Each stage reads earlier stages' outputs from data/ and results/."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
from loguru import logger

from src.paths import ARTIFACTS, WS, cite, p

DATA = WS / "data"
RES = WS / "results"
TAB = WS / "tables"
for _d in (DATA, RES, TAB, WS / "figures", WS / "audit"):
    _d.mkdir(exist_ok=True)

# files named in builds_on, per artifact (relative to each workspace)
DECLARED = {
    "exp17": ["data/labels.jsonl", "results/c2d.json", "data/realised_norms.jsonl", "results/manifold.json",
              "figures/fig7_manifold.png", "figures/fig7_manifold.pdf"],
    "exp13": ["data/samples.jsonl", "results/c1_events.jsonl", "results/analysis.json", "predictions/proximity.json",
              "predictions/associate.json", "predictions/forecasts.json", "src/analyze.py"],
    "exp16": ["results/landing_by_route.json", "results/shares.json", "results/route.json", "results/gate.json",
              "results/prefill.json", "results/replication.json", "results/c1_events.jsonl", "data/samples.jsonl",
              "results/screen_paths.json"],
    "exp15": ["src/scoring.py", "results/c1_events.jsonl", "data/samples.jsonl", "data/labels.jsonl",
              "results/other_reaudit.json", "results/push_hook_stats.json", "results/ban_norms.json",
              "predictions/forecasts.json"],
    "exp14": ["results/other_reports.json", "results/c1_events.jsonl", "results/c1_summary.json",
              "results/advance_rule_null_calibration.json", "results/correct_other_programs.jsonl",
              "data/samples.jsonl"],
    "exp18": ["data/samples_walk.jsonl", "data/samples_los.jsonl", "data/samples_two_step.jsonl",
              "data/samples_longform.jsonl", "data/samples_sham.jsonl", "data/samples_fixed_top5.jsonl",
              "results/reach.json", "results/c3.json", "results/can.json", "results/novelty_audit.json",
              "results/manual_audit.json", "data/llm_cache.jsonl", "results/known_solutions_summary.json"],
    "exp9": ["results/manifold.json", "results/landing.json", "results/los.json", "results/persistence.json",
             "data/samples.jsonl", "figures/fig_manifold_t1_baseline.png", "figures/fig_manifold_t1_single_bfs.png",
             "figures/fig_manifold_t1_multi_TOP5.png", "figures/fig_manifold_t2_los_bf_spfa.png"],
    "exp7": ["results/frlp_cells.jsonl", "results/gate_events.json", "results/c1.json", "results/association.json",
             "data/forced_labelled.jsonl", "data/forced_selected.jsonl", "frozen/ladder_profile.json", "method.py"],
    "exp11": ["data/association.jsonl", "data/samples_forced.jsonl", "data/frlp_cells.jsonl",
              "data/samples_pilot.jsonl", "data/samples_llama_pilot.jsonl", "bench/commitment.json"],
    "exp4": ["data/samples.jsonl", "results/buy_table.json", "results/dose_response.json"],
    "exp6": ["results/samples.jsonl", "results/analysis.json"],
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _describe(path: Path) -> dict:
    d: dict = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    if path.suffix == ".jsonl":
        n = 0
        first = None
        with path.open() as f:
            for line in f:
                if line.strip():
                    n += 1
                    if first is None:
                        first = json.loads(line)
        d["rows"] = n
        d["fields"] = sorted(first.keys()) if isinstance(first, dict) else None
    elif path.suffix == ".json":
        try:
            obj = json.loads(path.read_text())
            d["top_level_keys"] = sorted(obj.keys())[:60] if isinstance(obj, dict) else f"list[{len(obj)}]"
        except (json.JSONDecodeError, UnicodeDecodeError):
            d["top_level_keys"] = "unparseable"
    return d


def stage_inventory() -> None:
    out = []
    for exp, rels in DECLARED.items():
        for rel in rels:
            path = p(exp, rel)
            rec = {"artifact_id": cite(exp, rel).split(":")[0], "relpath": rel, "cite": cite(exp, rel)}
            if path.exists():
                rec.update(_describe(path))
                rec["status"] = "present"
            else:
                rec["status"] = "not_computable_from_declared_inputs"
            out.append(rec)
    # bench folders of exp11 (13 tasks)
    from src.labels import BENCH_DIRS
    for t, d in BENCH_DIRS.items():
        for rel in (f"bench/{d}/spec.json", f"bench/{d}/tests.jsonl"):
            path = p("exp11", rel)
            rec = {"artifact_id": cite("exp11", rel).split(":")[0], "relpath": rel, "cite": cite("exp11", rel)}
            rec.update(_describe(path) if path.exists() else {})
            rec["status"] = "present" if path.exists() else "not_computable_from_declared_inputs"
            out.append(rec)
    (WS / "inputs.json").write_text(json.dumps(out, indent=1))
    miss = [r["cite"] for r in out if r["status"] != "present"]
    logger.info(f"inventory: {len(out)} files, {len(miss)} missing: {miss}")


def stage_rows() -> None:
    from src.rows import build_rows
    build_rows(DATA / "rows.parquet")


def stage_judges() -> None:
    """(0d) Steps A-B: pool, features, blind judges. Re-runs hit audit/judge_cache.jsonl, so no call is paid twice."""
    import subprocess
    import sys
    r = subprocess.run([sys.executable, str(WS / "src" / "run_judges.py")], capture_output=True, text=True, timeout=3600)
    logger.info(f"run_judges: {r.stdout.strip()[-400:]}")
    if r.returncode:
        logger.error(r.stderr[-2000:])
        raise RuntimeError("run_judges failed")


def stage_knob() -> None:
    from src.knob import KNOB_COLUMNS, arm_dictionary, build_knob_table
    rows = pd.read_parquet(DATA / "rows.parquet")
    knob = build_knob_table(rows)
    hook = json.loads(p("exp15", "results/push_hook_stats.json").read_text())
    knob["realised_l21_displacement_ratio"] = [
        hook.get(a.split("_", 1)[1], {}).get("added_over_target_l21") if (e == "exp15" and a.startswith("rand_")) else None
        for e, a in zip(knob.exp, knob.arm)]
    knob.to_parquet(DATA / "knob.parquet", index=False)
    knob[KNOB_COLUMNS].to_csv(TAB / "knob_table.csv", index=False)
    arm_dictionary(knob).to_csv(TAB / "arm_dictionary.csv", index=False)
    logger.info(f"knob table: {len(knob)} rows -> tables/knob_table.csv")


def stage_screen() -> None:
    from src.screen import run_screen_stage
    run_screen_stage()


def stage_route() -> None:
    from src.route import run_route_stage
    run_route_stage()


def stage_llama() -> None:
    from src.llama import run_llama_stage
    run_llama_stage()


def stage_other() -> None:
    from src.other_assemble import run_other_stage
    run_other_stage()


def stage_figures() -> None:
    from src.figures import run_figures_stage
    run_figures_stage()


def stage_rigor() -> None:
    from src.rigor import run_rigor_stage
    run_rigor_stage()


def stage_wording() -> None:
    from src.wording import run_wording_stage
    run_wording_stage()


def stage_rivals() -> None:
    from src.rivals import run_rivals_stage
    run_rivals_stage()


def stage_audit() -> None:
    import subprocess
    import sys
    r1 = subprocess.run([sys.executable, "-I", str(WS / "audit" / "rederive.py")], capture_output=True, text=True, timeout=1800)
    logger.info(f"audit/rederive.py: {r1.stdout.strip()[-300:]} {r1.stderr.strip()[-300:]}")
    r2 = subprocess.run([sys.executable, "-I", str(WS / "audit" / "placebos.py")], capture_output=True, text=True, timeout=1800)
    logger.info(f"audit/placebos.py: {r2.stdout.strip()[-300:]} {r2.stderr.strip()[-300:]}")
    r3 = subprocess.run([sys.executable, str(WS / "audit" / "rederive_extra.py")], capture_output=True, text=True, timeout=1800)
    logger.info(f"audit/rederive_extra.py: {r3.stdout.strip()[-300:]} {r3.stderr.strip()[-300:]}")
    if r1.returncode or r2.returncode or r3.returncode:
        raise RuntimeError("audit scripts failed")


def stage_outputs() -> None:
    from src.outputs import run_outputs_stage
    run_outputs_stage()
