#!/usr/bin/env python3
"""Show a solution, ban it, see what replaces it: Step-1b exposure-ban experiment on Qwen3-8B (bf16, thinking off).

For every non-default algorithm Y of the 12 frozen exp11 bench tasks that has a correct forced program, the prompt shows
up to 5 name-scrubbed correct programs of Y and then asks COPY 'Write a correct solution.', NAMED '... that does not
use {Y}.' or UNNAMED '... uses a different algorithm from the one above.'.  Ban-free forecasts are fixed first
(LADDER = default, ASSOCIATE = modal frozen 'standard alternative to Y', PROXIMITY = nearest survivor by Zhang-Shasha
distance, SUBTRACT-IN-CONTEXT = the non-Y landing under an iterated persistent signature veto of Y's distinctive
token n-gram under the copy-twin prompt) and sha256 hash-chained before any ban sample is drawn.

Subcommands (run in this order):
  setup      copy + verify the exp11 bench, labeller re-check, defaults, eligibility           (CPU)
  forecasts  shown pools, n-grams, allocation, PROXIMITY, LADDER, ASSOCIATE, rendered prompts   (CPU)
  commit1    unit tests must pass; COMMIT #1 of every forecast, prompt and the analysis code    (CPU)
  stage1     GPU smoke tests, COPY twin, veto rounds 1-3, bf16 baseline check; SUBTRACT          (GPU)
  commit2    COMMIT #2 (SUBTRACT-IN-CONTEXT, veto rounds, copy-twin, baseline check)            (CPU)
  stage2     NAMED + UNNAMED exposure bans (+ optional W1-W4 template arm)                       (GPU)
  analyze    per-arm stats, events, frozen C1 scoring + advance rule + tests, reports, figures   (CPU)
  audit      independent re-derivation (audit/rederive.py), placebo, chain verification         (CPU)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import resource
import subprocess
import sys
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ["PYTHONPATH"] = str(ROOT) + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else "")

from loguru import logger  # noqa: E402

from exposure.core import (COMMIT_LOG, DATA, LOGS, MODEL_ID, MODEL_REV, PRED, RESULTS, TASK_ORDER, Timer,  # noqa: E402
                           deviation, read_json, read_jsonl, setup_logging, sha256_file, sha256_text, write_json)


def _detect_cpus() -> int:
    try:
        q = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
        p = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
        if q > 0:
            return math.ceil(q / p)
    except (FileNotFoundError, ValueError):
        pass
    try:
        parts = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if parts[0] != "max":
            return math.ceil(int(parts[0]) / int(parts[1]))
    except (FileNotFoundError, ValueError, IndexError):
        pass
    return len(os.sched_getaffinity(0))


NUM_CPUS = _detect_cpus()
ABORTED_STAGE1_MIN = 26  # wall minutes of the first stage-1 attempt, stopped for the stop-token bug (logs/stage1_attempt1_*)


def _cpu_ram_limit(gb: float) -> None:
    """Hard address-space cap for CPU-only subcommands (never for the CUDA process: it reserves huge VA ranges)."""
    resource.setrlimit(resource.RLIMIT_AS, (int(gb * 1024**3), int(gb * 1024**3)))


def env_info() -> dict:
    info = {"python": sys.version.split()[0], "num_cpus_cgroup": NUM_CPUS, "model": MODEL_ID, "model_revision": MODEL_REV}
    try:
        info["nvidia_smi"] = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                                             "--format=csv,noheader"], capture_output=True, text=True,
                                            timeout=30).stdout.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        info["nvidia_smi"] = f"unavailable: {e}"
    for m in ["torch", "vllm", "transformers", "scipy", "numpy", "zss", "rapidfuzz"]:
        try:
            info[m] = __import__(m).__version__
        except (ImportError, AttributeError):
            info[m] = None
    return info


# ------------------------------------------------------------------------------------------------------- setup
def cmd_setup(args) -> None:
    from exposure.forecasts import copy_and_verify, defaults_and_eligibility, labeller_recheck
    _cpu_ram_limit(40)
    with Timer("setup"):
        info = env_info()
        logger.info(f"environment: {json.dumps(info)}")
        write_json(RESULTS / "environment.json", info)
        ver = copy_and_verify()
        from bench_copy.common.commit import commit, verify_chain
        if not COMMIT_LOG.exists() or not any(r["kind"] == "commit0_inputs" for r in read_jsonl(COMMIT_LOG)):
            payload = {"bench_commitment_combined_sha256": ver["combined_sha256"],
                       "uncommitted_inputs": ver["uncommitted_input_sha256"]}
            write_json(PRED / "commit0_inputs.json", payload)
            commit(COMMIT_LOG, "commit0_inputs", sha256_file(PRED / "commit0_inputs.json"),
                   {"file": "predictions/commit0_inputs.json"})
            assert verify_chain(COMMIT_LOG)
        rc = labeller_recheck(workers=NUM_CPUS)
        flagged = [t for t, v in rc.items() if v["flag"]]
        if flagged:
            deviation(f"labeller re-check flags tasks {flagged} (more than 5 points below gate.json or a reference "
                      "mislabelled); their events are sampled but reported outside the primary")
        elig = defaults_and_eligibility()
        elig["labeller_flagged_tasks"] = flagged
        write_json(PRED / "eligibility.json", elig)


# --------------------------------------------------------------------------------------------------- forecasts
def cmd_forecasts(args) -> None:
    from exposure.core import load_tokenizer
    from exposure.forecasts import allocation, ngrams_and_shown, proximity, render_prompts, shown_pools
    _cpu_ram_limit(40)
    with Timer("forecasts"):
        tok = load_tokenizer()
        elig = read_json(PRED / "eligibility.json")
        pools = shown_pools(elig, tok, workers=NUM_CPUS)
        write_json(RESULTS / "shown_pool_summary.json",
                   {k: {"n_R": v["n_R"], "n_pool": len(v["kept"]), "drops": v["drops"]} for k, v in pools.items()})
        ngrams, shown = ngrams_and_shown(elig, pools, tok)
        alloc = {k: allocation(len(v)) for k, v in shown.items()}
        prox = proximity(elig, shown, alloc, workers=NUM_CPUS)
        e_by = {f"{e['task']}:{e['Y']}": e for e in elig["eligible"]}
        ladder = {k: {e_by[k]["default"]: 1.0} for k in shown}
        assoc = {k: e_by[k]["associate"] for k in shown}
        cov = {k: {"coveto_groups": v["coveto_groups"], "coveto_modes": v["coveto_modes"],
                   "default_coveto": v["default_coveto"], "associate_coveto": v["associate_coveto"],
                   "n_ref_lt5": v["n_ref_lt5"]} for k, v in ngrams.items()}
        prompts = render_prompts(tok, shown)
        with (PRED / "shown_programs.jsonl").open("w") as f:
            for k, s_y in shown.items():
                for p in s_y:
                    f.write(json.dumps({"key": k, "task": k.split(":")[0], "Y": k.split(":")[1], "p_index": p["p_index"],
                                        "n_samples": alloc[k][p["p_index"]], "code": p["code"],
                                        "code_sha256": p["code_sha256"], "canon_sha256": p["canon_sha256"],
                                        "src_sample_id": p["src_sample_id"], "n_tokens": p["n_tokens"],
                                        "renamed": p["renamed"], "unscrubbed": p["unscrubbed"]}) + "\n")
        write_json(PRED / "ngrams.json", ngrams)
        write_json(PRED / "coveto.json", cov)
        write_json(PRED / "associate.json", assoc)
        write_json(PRED / "proximity.json", prox)
        write_json(PRED / "ladder.json", ladder)
        write_json(PRED / "allocation.json", alloc)
        with (PRED / "prompts.jsonl").open("w") as f:
            for r in prompts:
                f.write(json.dumps(r) + "\n")
        logger.info(f"forecasts written for {len(shown)} Y")


# ------------------------------------------------------------------------------------------------------ commit1
COMMIT1_FILES = ["eligibility.json", "shown_programs.jsonl", "ngrams.json", "coveto.json", "associate.json",
                 "proximity.json", "ladder.json", "allocation.json", "prompts.jsonl", "analysis_code.tar"]


def _tar_analysis_code() -> Path:
    out = PRED / "analysis_code.tar"
    with tarfile.open(out, "w", format=tarfile.GNU_FORMAT) as tf:
        for p in sorted((ROOT / "analysis").glob("*.py")) + sorted((ROOT / "tests").glob("*.py")):
            ti = tf.gettarinfo(str(p), arcname=str(p.relative_to(ROOT)))
            ti.mtime, ti.uid, ti.gid, ti.uname, ti.gname = 0, 0, 0, "", ""
            with p.open("rb") as fh:
                tf.addfile(ti, fh)
    return out


def _commit_files(kind: str, files: list[str]) -> str:
    from bench_copy.common.commit import commit, verify_chain
    hashes = {}
    for f in files:
        h = sha256_file(PRED / f)
        hashes[f] = h
        commit(COMMIT_LOG, f"{kind}:{f}", h, {"file": f"predictions/{f}"})
    bundle = sha256_text(json.dumps(hashes, sort_keys=True))
    rec = commit(COMMIT_LOG, kind, bundle, {"files": hashes})
    ok = verify_chain(COMMIT_LOG)
    logger.info(f"{kind}: {len(files)} files, bundle {bundle[:16]}..., chain verifies: {ok}")
    if not ok:
        raise RuntimeError("hash chain does not verify")
    return rec["sha256"]


def cmd_commit1(args) -> None:
    if any(r["kind"] == "COMMIT1" for r in read_jsonl(COMMIT_LOG)):
        logger.info("COMMIT #1 already present; nothing to do")
        return
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/"], cwd=ROOT, capture_output=True, text=True)
    (LOGS / "pytest_commit1.log").write_text(r.stdout + r.stderr)
    logger.info("pytest:\n" + r.stdout[-1500:])
    if r.returncode != 0:
        raise RuntimeError("unit tests fail; the analysis code cannot be frozen")
    _tar_analysis_code()
    _commit_files("COMMIT1", COMMIT1_FILES)


def cmd_stage1(args) -> None:
    from exposure.stages import stage1
    if not any(r["kind"] == "COMMIT1" for r in read_jsonl(COMMIT_LOG)):
        raise RuntimeError("COMMIT #1 missing: no generation may happen before it")
    stage1(args)


COMMIT2_FILES = ["subtract_in_context.json", "veto_rounds.json", "copy_twin_summary.json", "bf16_baseline_check.json",
                 "optional_template_arm.json"]


def cmd_commit2(args) -> None:
    if any(r["kind"] == "COMMIT2" for r in read_jsonl(COMMIT_LOG)):
        logger.info("COMMIT #2 already present; nothing to do")
        return
    gens = read_jsonl(DATA / "generations.jsonl")
    bans = [g for g in gens if g["arm"] not in ("copy", "veto", "baseline")]
    if bans:
        raise RuntimeError(f"{len(bans)} ban samples exist before COMMIT #2: the design is void")
    _commit_files("COMMIT2", COMMIT2_FILES)


def cmd_stage2(args) -> None:
    from exposure.stages import stage2
    stage2(args)


def cmd_analyze(args) -> None:
    from exposure.report import analyze
    _cpu_ram_limit(40)
    with Timer("analyze"):
        analyze(args)


def cmd_audit(args) -> None:
    _cpu_ram_limit(40)
    with Timer("audit"):
        r = subprocess.run([sys.executable, "audit/rederive.py"], cwd=ROOT, capture_output=True, text=True)
        (LOGS / "audit.out").write_text(r.stdout + r.stderr)
        logger.info(r.stdout[-3000:])
        if r.returncode != 0:
            raise RuntimeError(f"audit failed: {r.stderr[-1500:]}")
        # fold the audit record into method_out.json (metadata), as the plan's 4.7 asks
        mo_path, red = ROOT / "method_out.json", read_json(RESULTS / "rederive.json")
        if mo_path.exists():
            mo = read_json(mo_path)
            md = mo["metadata"]
            md["audit_rederive"] = {k: red[k] for k in ("n_events_rederived", "n_mismatches", "headline", "placebo",
                                                        "chain_verifies", "committed_files_unchanged")}
            md["gpu_hours_note"] = (f"summary.gpu_hours ({md['summary']['gpu_hours']:.3f}) counts the completed stage-1 and "
                                    f"stage-2 runs; the aborted first stage-1 attempt (stop-token bug, about "
                                    f"{ABORTED_STAGE1_MIN} min) brings the total to about 1.0 GPU-hour on one NVIDIA L4")
            md["gpu_hours_including_aborted_attempt"] = round(md["summary"]["gpu_hours"] + ABORTED_STAGE1_MIN / 60, 3)
            md["exploratory_note"] = ("summary.exploratory_not_preregistered (three-family LADDER/ASSOCIATE/PROXIMITY "
                                      "contest) was added after the commits and is not part of the frozen C1 analysis")
            mo_path.write_text(json.dumps(mo))
            logger.info("audit record merged into method_out.json metadata")


COMMANDS = {"setup": cmd_setup, "forecasts": cmd_forecasts, "commit1": cmd_commit1, "stage1": cmd_stage1,
            "commit2": cmd_commit2, "stage2": cmd_stage2, "analyze": cmd_analyze, "audit": cmd_audit}


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=sorted(COMMANDS))
    ap.add_argument("--max-num-seqs", type=int, default=64)
    ap.add_argument("--gpu-util", type=float, default=0.92)
    ap.add_argument("--label-workers", type=int, default=4)
    ap.add_argument("--no-template-arm", action="store_true")
    args = ap.parse_args()
    setup_logging(args.command)
    logger.info(f"=== method.py {args.command} (cpus={NUM_CPUS}) ===")
    COMMANDS[args.command](args)


if __name__ == "__main__":
    main()
