#!/usr/bin/env python3
"""Stage -1 (inputs, environment, hardware) and Stage 0 (commit #0, before any state is extracted)."""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import shutil
from pathlib import Path
from typing import Any

from loguru import logger

import tpg
from common import commit, deviation, read_json, sha256_file, utc_now, write_json
from tpg import (B5, DSET, E44, EXP2, EXP8, EXP9, IN_E44, INPUTS, NB5, PRED, RESULTS, ROOT, UDIJ)

E44_RESULTS = ["geometry_M1.json", "landing.json", "landing_robustness.json", "quant_check.json", "t8_synthetic.json",
               "renderer_checks.json", "states_C6_nf4.json", "states_C1_bf16.json", "confirmation.json",
               "screen.json", "selection.json", "deviations.json"]
E44_DATA = ["labelled_C6_baseline.jsonl", "labelled_C6_ban.jsonl", "labelled_C6_confirm.jsonl", "manual_reads.jsonl"]
E44_STATES = ["smean_C6_nf4.npz", "geo_C6_nf4.npz", "smean_C1_bf16.npz"]
E44_SRC = ["common.py", "prompts_tp.py", "states.py", "geometry.py", "landing.py", "label_tp.py", "sample_or.py"]


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_size == src.stat().st_size:
        return
    shutil.copy2(src, dst)


def _copytree(src: Path, dst: Path) -> None:
    for p in src.rglob("*"):
        if p.is_file() and "__pycache__" not in p.parts:
            _copy(p, dst / p.relative_to(src))


def detect_cpus() -> int:
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


def container_ram_gb() -> float | None:
    for p in ["/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"]:
        try:
            v = Path(p).read_text().strip()
            if v != "max" and int(v) < 1_000_000_000_000:
                return int(v) / 1e9
        except (FileNotFoundError, ValueError):
            pass
    return None


def stage_inputs() -> None:
    """Copy every prior-artifact input into inputs/ (and vendor/, src/e44/), write inputs/SHA256SUMS."""
    status: dict[str, Any] = {"utc": utc_now(), "copied": [], "missing": []}
    # iteration-8 code (unedited archive) and the vendored harness / labeller
    for f in sorted((E44 / "src").glob("*.py")):
        _copy(f, ROOT / "src" / "e44" / f.name)
    _copytree(E44 / "vendor" / "exp9", ROOT / "vendor" / "exp9")
    _copytree(E44 / "vendor" / "exp2", ROOT / "vendor" / "exp2")
    _copytree(E44 / "inputs" / "exp9", INPUTS / "exp9")
    for f in E44_RESULTS:
        src = E44 / "results" / f
        (status["copied"] if src.exists() else status["missing"]).append(f"e44/results/{f}")
        if src.exists():
            _copy(src, IN_E44 / "results" / f)
    for f in E44_DATA:
        src = E44 / "data" / f
        (status["copied"] if src.exists() else status["missing"]).append(f"e44/data/{f}")
        if src.exists():
            _copy(src, IN_E44 / "data" / f)
    for f in E44_STATES:
        src = E44 / "cache" / "states" / f
        (status["copied"] if src.exists() else status["missing"]).append(f"e44/states/{f}")
        if src.exists():
            _copy(src, IN_E44 / "states" / f)
    split_large_npz(IN_E44 / "states")
    for f in ("pyproject.toml", "reproducibility.md", "commitments.log"):
        if (E44 / f).exists():
            _copy(E44 / f, IN_E44 / f)
    # identical-copy check of the imported iteration-8 modules (src/<name> must equal src/e44/<name>)
    ident = {}
    for f in E44_SRC:
        a, b = ROOT / "src" / f, ROOT / "src" / "e44" / f
        ident[f] = a.exists() and b.exists() and sha256_file(a) == sha256_file(b)
    status["imported_modules_identical_to_e44"] = ident
    if not all(ident.values()):
        deviation("D-imports", f"imported iteration-8 modules differ from the e44 archive: {ident}")
    # iteration-2 forced programs (S1) and forced_desc prompt texts
    rows = []
    with (EXP9 / "data" / "samples.jsonl").open() as fh:
        for line in fh:
            r = json.loads(line)
            c = r.get("condition") or ""
            if r.get("task") == "t1" and (c.startswith("forced:") or c.startswith("forced_desc:")):
                rows.append(r)
    (INPUTS / "exp9_forced.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    status["exp9_forced_rows"] = len(rows)
    _copy(EXP9 / "prompts" / "frozen_prompts.json", INPUTS / "exp9_art" / "frozen_prompts.json")
    # twin frame precedent (art_8_ULPE8jJQc_)
    _copy(EXP8 / "prompts" / "frozen_prompts.json", INPUTS / "exp8" / "frozen_prompts.json")
    # secondary hidden suite, original location (art_D6Z0Snf09sFL); E44's vendored copy is what the harness runs
    for cand in [EXP2 / "tasks" / "hidden_tests_t1.json", EXP2 / "hidden_tests_t1.json"]:
        if cand.exists():
            _copy(cand, INPUTS / "exp2" / "hidden_tests_t1.json")
            break
    # declared dependency: 718 neutral-noun candidates (concreteness_norms) with Qwen3 token counts
    ds = json.loads((DSET / "full_data_out.json").read_text())
    cn = next(d for d in ds["datasets"] if d["dataset"] == "concreteness_norms")["examples"]
    nouns = [{"noun": ex["input"], "concreteness": float(ex["output"]),
              "qwen3_tokens_with_leading_space": ex["metadata_qwen3_tokens_with_leading_space"],
              "qwen3_tokens_bare": ex["metadata_qwen3_tokens_bare"],
              "subtlex_frequency": ex["metadata_subtlex_frequency"], "oewn": ex["metadata_oewn_noun_lexfiles"]}
             for ex in cn if ex.get("metadata_noun_bank_candidate")]
    del ds
    write_json(INPUTS / "neutral_nouns.json", {"source": "art_j3Rm_lr2nzR6 full_data_out.json concreteness_norms "
                                               "(metadata_noun_bank_candidate)", "n": len(nouns), "nouns": nouns})
    status["neutral_nouns"] = len(nouns)
    status["dataset_full_sha256"] = sha256_file(DSET / "full_data_out.json")
    # SHA256SUMS over inputs/ (and vendor/)
    lines = []
    for base in (INPUTS, ROOT / "vendor"):
        for p in sorted(base.rglob("*")):
            if p.is_file() and p.name != "SHA256SUMS":
                lines.append(f"{sha256_file(p)}  {p.relative_to(ROOT)}")
    (INPUTS / "SHA256SUMS").write_text("\n".join(lines) + "\n")
    status["n_files_hashed"] = len(lines)
    write_json(RESULTS / "inputs_status.json", status)
    logger.info(f"inputs: {len(status['copied'])} copied, missing {status['missing']}, {len(rows)} exp9 forced rows, "
                f"{len(nouns)} neutral nouns")
    if status["missing"]:
        deviation("D-missing-inputs", f"missing prior inputs: {status['missing']} (rebuild paths used)")
    stage_hardware()


def split_large_npz(folder: Path, limit_mb: float = 95.0) -> None:
    """Splits an S-mean npz over the repository's 100 MB file limit into two block-range parts (exact; read back by
    stage_states.load_e44_smean)."""
    import numpy as np

    for p in sorted(folder.glob("*.npz")):
        if p.stat().st_size / 1e6 <= limit_mb or "_part" in p.name:
            continue
        z = np.load(p)
        d = {k: z[k] for k in z.files}
        cut = len(d["blocks"]) // 2 + 1
        meta = {k: v for k, v in d.items() if k != "smean"}
        for i, sl in ((1, slice(0, cut)), (2, slice(cut, None))):
            np.savez_compressed(p.with_name(p.stem + f"_part{i}.npz"), smean=d["smean"][:, sl],
                                part_blocks=d["blocks"][sl], **meta)
        p.unlink()
        logger.info(f"split {p.name} into two parts (repository file-size limit)")


def stage_hardware() -> None:
    import torch

    hw: dict[str, Any] = {"utc": utc_now(), "python": platform.python_version(), "platform": platform.platform(),
                          "cpus_cgroup": detect_cpus(), "ram_gb_cgroup": container_ram_gb(),
                          "torch": torch.__version__, "cuda_available": torch.cuda.is_available()}
    if torch.cuda.is_available():
        free, total = torch.cuda.mem_get_info(0)
        hw.update({"gpu": torch.cuda.get_device_name(0), "vram_total_gb": round(total / 1e9, 2),
                   "vram_free_gb": round(free / 1e9, 2), "cuda": torch.version.cuda,
                   "capability": list(torch.cuda.get_device_capability(0))})
    import importlib.metadata as md

    hw["packages"] = {p: md.version(p) for p in ("transformers", "bitsandbytes", "accelerate", "scikit-learn",
                                                 "scipy", "numpy", "huggingface-hub", "tokenizers", "matplotlib")}
    e44_pins = {}
    for line in (IN_E44 / "pyproject.toml").read_text().splitlines():
        line = line.strip().strip(",").strip('"')
        if "==" in line:
            k, v = line.split("==", 1)
            e44_pins[k.lower()] = v
    hw["matches_e44_pins"] = {p: (e44_pins.get(p.lower()) == v) for p, v in hw["packages"].items()
                              if p.lower() in e44_pins}
    write_json(PRED / "hardware.json", hw)
    logger.info(f"hardware: {hw.get('gpu')} {hw.get('vram_total_gb')} GB, {hw['cpus_cgroup']} CPUs, "
                f"{hw['ram_gb_cgroup']} GB RAM; pins match {hw['matches_e44_pins']}")


# ---------------------------------------------------------------------------------------------- commit #0
def stage_commit0() -> None:
    src_hashes = {p.name: sha256_file(p) for p in sorted((ROOT / "src").glob("*.py"))}
    c0 = {
        "artifact": "TP-G iteration 9 (gen_plan_experiment_2_idx3): mapping the ten grid algorithms with and without "
                    "their names",
        "utc": utc_now(),
        "banned": B5, "nonbanned": NB5,
        "predictions": {
            "P1": "M-name reproduces: Spearman(45 off-diagonal entries of the 10x10 class geodesic matrix, k 15, "
                  "block 31, new states vs iteration-8 geo_C6_nf4.npz) >= 0.95 and the classes of NB5 are unchanged",
            "P2": "M-code (PRIMARY frame, R1 readout) and M-desc: landing verdict for the 15 survivors (15 x unit "
                  "Dijkstra) = EDGE at the committed block, with class(dijkstra_unit) = EDGE at both k 10 and 15",
            "P3": "M-name and M-lex: verdict OPPOSITE (class(dijkstra_unit) = OPPOSITE at k 10 and 15)",
            "P4": "M-name alias level: Spearman(g_alias, L1) <= -0.6 at k 10 AND k 15 (15 alias point sets of NB5)",
            "P5": "M-code and M-desc: the overlap ordering does not reproduce (descriptive)",
            "P6": "behavioural RDM: dijkstra_unit has the smallest d_beh to BFS among NB5 (anchor; true by construction "
                  "for the order term)",
            "P7": "RSA (descriptive, CIs): rho(D_name,R_lex) > rho(D_name,R_beh); rho(D_code,R_beh) > rho(D_code,R_lex); "
                  "rho(D_desc,R_beh) > rho(D_desc,R_lex)",
            "P8": "per-program: > 0.5 of the 15 dijkstra_unit survivor programs placed on M-code have program-level "
                  "class EDGE (only if gate G-place passes)",
        },
        "secondary_statistics": ["rank of g(dijkstra_unit) among NB5 (1 = nearest)",
                                 "ratio g(dijkstra_unit)/median(g NB5) with bootstrap 95% CI",
                                 "nearest banned algorithm of dijkstra_unit", "robustness-grid class counts",
                                 "bootstrap EDGE probability"],
        "named_outcomes": {
            "CONFIRMED": "P2, P3, P4 and P6 hold",
            "ROBUST-OPPOSITE": "OPPOSITE on both M-code and M-desc",
            "MIXED": "M-code and M-desc disagree, or a verdict changes between k 10 and 15, or SOURCE-SENSITIVE",
            "NAMES-ONLY": "P3 and P4 hold but M-code and M-desc read MIDDLE or NEITHER",
            "UNTESTABLE": "a gate fails as stated in the fallbacks",
        },
        "mcode_robustness": "M-code verdict is ROBUST only if the source-homogeneous M32 frame gives the same "
                            "class(dijkstra_unit); otherwise SOURCE-SENSITIVE",
        "gates": {"G-repro": "P1 (>= 0.95; 0.85-0.95 proceed with new states and report; < 0.85 deviation)",
                  "G-name": ">= 16/20 Qwen3-32B namings per description (T 1.0, top_p 1.0, thinking off)",
                  "G-scrub": "no alias match; ast.dump equal modulo names (docstrings removed); both hidden suites "
                             "pass; expansion sequences on the 40 probe grids identical; labeller label unchanged",
                  "G-tracer": "every T1 reference shows its algorithm's properties on the probe grids",
                  "G-place": "leave-one-out placement accuracy >= 0.70 on the M-code frame",
                  "reliability_flag": "split-half Spearman (Spearman-Brown corrected) < 0.7"},
        "definitions": {
            "L1": "number of banned algorithms b whose alias_regex([b]) matches the alias string",
            "L2": "max over banned aliases of character-3-gram Jaccard (lowercased)",
            "L3": "max over banned aliases of Qwen3 token-type Jaccard",
            "R_lex": "1 - mean over alias pairs of character-3-gram Jaccard (10x10)",
            "D_overlap": "max content-word Jaccard (stoplist, plural stripping) with the 15 banned descriptions",
            "d_beh": "d_order + 0.5 * d_DS; d_order = 1 - mean over 40 probe grids of J*(1+tau_b)/2 (J = Jaccard of "
                     "expanded-cell sets, tau_b over ranks of common cells, 0 if < 3); d_DS = Hamming/6 over (fifo, "
                     "lifo_or_recursion, heap, two_frontiers, restarts, heuristic_key); lambda 0 and 1 reported",
            "R_surface": "1 - mean Jaccard of identifier-normalised AST 4-gram shingles between PRIMARY program sets",
            "R_len": "absolute difference of mean stimulus token length",
            "out_of_sample": "d(x,j) = min over x's k nearest frame points i of (||x-i|| + geo(i,j)); frozen graph",
            "readouts": {"S-mean": "mean over the SPEC tokens of the block output (iteration 8)",
                         "R1": "mean over code tokens", "R1g": "R1 without tokens whose norm > 10x the sequence median",
                         "R2": "token after the earliest popleft/pop/heappop/get call in the code (AST); fallback: "
                               "first token of the neighbour-loop body / first body statement of solve",
                         "R3": "16th code token (negative control)"},
            "block_rule": "iteration-8 layer_curve: standardise, PCA 64, logistic C=1, GroupKFold 10, balanced "
                          "accuracy, ties within 0.01 or all-ceiling -> block nearest depth 0.5; block 31 (32B) and "
                          "the depth-0.5 block (8B) always reported",
            "k_rule": "verdict at k 15 (iteration 8 primary) and k 10; k 5 reported",
            "classes": "EDGE g < median, MIDDLE g == median, OPPOSITE g > median over NB5 (iteration 8)",
            "landing": "iteration-8 landing(): nulls U, F, P (120 permutations), C; verdict EDGE iff p_edge(U) < .05 "
                       "and p_edge(F) < .05 and > 50% survivors EDGE; OPPOSITE mirrored; else NEITHER",
            "groups": {"M-name": "3t+j", "M-desc": "3t+d", "M-lex": "3t+j", "M-code": "(rank within algorithm) mod 10"},
            "bootstrap": "1,000 group resamples (32B verdict settings), 200 elsewhere",
            "rsa": "Spearman over 45 pairs, exact Mantel p over all 10! label permutations",
            "drop_order": ["Qwen3-8B states", "M-lex", "k 10 sensitivity", "robustness grid reduced to block 31 + L*"],
            "budget_usd": tpg.OR_CAP_USD, "topup_stop_usd": tpg.TOPUP_STOP_USD,
        },
        "survivors_landing": {"screen": tpg.SURV_SCREEN, "confirm": tpg.SURV_CONFIRM,
                              "pooled": tpg.SURV_SCREEN + tpg.SURV_CONFIRM},
        "src_sha256": src_hashes,
        "inputs_SHA256SUMS_sha256": sha256_file(INPUTS / "SHA256SUMS"),
        "correlational_statement": "geometry is correlational; no causal claim (iteration-7 in-manifold pushes moved "
                                   "0/300)",
    }
    p = PRED / "commit0.json"
    write_json(p, c0)
    commit(p, "COMMIT0", "predictions, gates, definitions; before any state is extracted")


# ---------------------------------------------------------------------------------------------- helpers
def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


__all__ = ["stage_inputs", "stage_hardware", "stage_commit0", "detect_cpus", "container_ram_gb", "UDIJ"]
