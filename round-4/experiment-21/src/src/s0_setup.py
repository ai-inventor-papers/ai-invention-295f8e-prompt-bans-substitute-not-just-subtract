#!/usr/bin/env python3
"""S0: inputs, hashes, seed-collision check, hardware probe, labeller re-check, OpenRouter key (CPU only).

- Every copied input is re-hashed and compared with (a) the source file on the run volume (present + identical),
  (b) exp17 results/input_hashes.json (same relative layout), (c) exp11 bench/commitment.json (T03 bench files) and
  (d) exp17 directions/direction_hashes.json. Mismatches are logged (fallback F1 would apply; none expected).
- The exp17 source files in src/ are verbatim copies; their sha256 is compared with the run-volume originals.
- Labeller re-check: exp8 suite on its 22 path references + gold eval split; T03 bench labeller on its 6 references +
  gold set, with agreement written next to the gate.json values (mechanical labels; no judge spend).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from loguru import logger

from cfg import BENCH, E11, INPUTS, RESULTS_DIR, ROOT, SUITE, read_json, read_jsonl, rel, sha256_file, utc_now, write_json
from cfg4 import ITER2, ITER3, ITER4, PN_SEEDS

for p in (str(SUITE), str(E11)):
    if p not in sys.path:
        sys.path.insert(0, p)

E17_SRC = ITER3 / "experiment-17/src"
E13_SRC = ITER3 / "experiment-13/src"
E11_SRC = ITER2 / "experiment-11/src"
E7_SRC = ITER2 / "experiment-7/src"

# (copy in this workspace, source on the run volume)
COPIES: list[tuple[str, Path]] = [
    ("inputs/exp13/results/tensors/norms_T03.npz", E13_SRC / "results/tensors/norms_T03.npz"),
    ("inputs/exp13/data/samples.jsonl", E13_SRC / "data/samples.jsonl"),
    ("inputs/exp17/data/labels.jsonl", E17_SRC / "data/labels.jsonl"),
    ("inputs/exp17/results/timing.json", E17_SRC / "results/timing.json"),
    ("inputs/exp17/results/input_hashes.json", E17_SRC / "results/input_hashes.json"),
    ("inputs/exp17/predictions/commit1.json", E17_SRC / "predictions/commit1.json"),
    ("inputs/exp11/bench_commitment_orig.json", E11_SRC / "bench/commitment.json"),
    ("inputs/exp11/gate_T03_orig.json", E11_SRC / "bench/T03_kth_smallest/gate.json"),
    ("inputs/exp7/frozen/templates_nouns_padding.json", E7_SRC / "frozen/templates_nouns_padding.json"),
    ("prompts/prompts.jsonl", E17_SRC / "prompts/prompts.jsonl"),
]


def write_t0() -> dict[str, Any]:
    p = RESULTS_DIR / "t0.json"
    if p.exists():
        return read_json(p)
    d = {"t0_unix": time.time(), "t0_utc": utc_now()}
    write_json(p, d)
    return d


def verify_inputs() -> dict[str, Any]:
    out: dict[str, Any] = {"copies": [], "mismatches": [], "missing_sources": []}
    for dst, src in COPIES:
        d = ROOT / dst
        rec = {"copy": dst, "source_present": src.exists(), "copy_present": d.exists()}
        if src.exists() and not d.exists():
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, d)
            rec["copied_now"] = True
        if src.exists() and d.exists():
            rec["sha256"] = sha256_file(d)
            rec["identical_to_source"] = rec["sha256"] == sha256_file(src)
            if not rec["identical_to_source"]:
                out["mismatches"].append(rec)
        elif not src.exists():
            out["missing_sources"].append(dst)
        out["copies"].append(rec)
    # exp17 source files: verbatim copies
    src_ok = {}
    for f in sorted((ROOT / "src").glob("*.py")):
        o = E17_SRC / "src" / f.name
        if o.exists():
            src_ok[f.name] = sha256_file(f) == sha256_file(o)
    out["exp17_src_verbatim"] = src_ok
    out["exp17_src_all_verbatim"] = all(src_ok.values())
    # (b) exp17 input hashes (same relative layout)
    ih17 = read_json(ROOT / "inputs/exp17/results/input_hashes.json")["all_inputs_sha256"]
    n_ok, bad = 0, []
    for rp, h in ih17.items():
        p = ROOT / rp
        if not p.exists():
            bad.append({"path": rp, "problem": "missing"})
        elif sha256_file(p) != h:
            bad.append({"path": rp, "problem": "sha256 differs"})
        else:
            n_ok += 1
    out["exp17_input_hashes"] = {"n_checked": len(ih17), "n_ok": n_ok, "problems": bad[:50]}
    # (c) exp11 commitment for the T03 bench copy
    com = read_json(ROOT / "inputs/exp11/bench_commitment_orig.json")
    t03 = com["tasks"]["T03"]["files"]
    c_ok, c_bad = 0, []
    for f, h in t03.items():
        if f == "catalogue":
            continue
        p = BENCH / "T03_kth_smallest" / f
        if p.exists() and sha256_file(p) == h:
            c_ok += 1
        else:
            c_bad.append(f)
    out["exp11_T03_commitment"] = {"files_ok": c_ok, "bad": c_bad}
    # (d) direction hashes
    dh = read_json(ROOT / "directions/direction_hashes.json")
    d_ok, d_bad = 0, []
    for name, h in dh.items():
        p = ROOT / "directions" / name
        if p.exists():
            if sha256_file(p) == h:
                d_ok += 1
            else:
                d_bad.append(name)
    out["direction_hashes"] = {"n_present_ok": d_ok, "bad": d_bad,
                               "note": "only rand_9001-9015 and norms_T1/T2/T03 are copied; v_*/vraw_* are not used"}
    out["all_inputs_sha256"] = {rel(p): sha256_file(p) for p in sorted(INPUTS.rglob("*")) if p.is_file()
                                and "__pycache__" not in str(p) and p.stat().st_size < 60_000_000}
    out["pass"] = (not out["mismatches"] and not bad and not c_bad and not d_bad and not out["missing_sources"])
    return out


def seed_collisions() -> dict[str, Any]:
    used: dict[int, list[str]] = {}
    for base in (ITER3, ITER4):
        for p in base.glob("*/directions/rand_*.npy"):
            if ROOT in p.parents:
                continue
            try:
                s = int(p.stem.split("_")[1])
            except (IndexError, ValueError):
                continue
            used.setdefault(s, []).append(rel(p) if ROOT in p.parents else p.parent.parent.name)
    coll = {s: used[s] for s in PN_SEEDS if s in used}
    return {"pn_seeds": list(PN_SEEDS), "collisions": coll, "n_seeds_in_use_elsewhere": len(used),
            "seeds_in_use_elsewhere": sorted(used)[:100], "pass": not coll}


def hardware() -> dict[str, Any]:
    from cfg import container_ram_gb, detect_cpus

    hw: dict[str, Any] = {"cpus": detect_cpus(), "ram_gb_container": container_ram_gb(),
                          "gcc": shutil.which("gcc"), "cc": shutil.which("cc"), "nvcc": shutil.which("nvcc")}
    try:
        q = subprocess.run(["nvidia-smi", "--query-gpu=name,compute_cap,memory.total,memory.used,driver_version",
                            "--format=csv,noheader"], capture_output=True, text=True, timeout=30)
        name, cc, tot, used, drv = [x.strip() for x in q.stdout.strip().split(",")]
        hw.update({"gpu": name, "compute_capability": cc, "vram_total_mib": tot, "vram_used_mib": used,
                   "driver": drv})
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        hw["gpu_error"] = str(e)
    cc = float(hw.get("compute_capability", "0") or 0)
    tot_gb = float(str(hw.get("vram_total_mib", "0")).split()[0]) / 1024
    if cc >= 8.0 and tot_gb >= 20:
        hw["hf_precision"] = "bf16"
    elif cc >= 8.9 and tot_gb >= 15:
        hw["hf_precision"] = "fp8_w8a8 (exp17 load_model(fp8=True)); same card class as the screen"
    else:
        hw["hf_precision"] = "fallback F2"
    hw["vllm_bf16_fits"] = tot_gb * 0.9 - 16.4 - 1.5 > 0
    hw["batch_invariance_supported"] = cc >= 9.0
    return hw


def suite_recheck() -> dict[str, Any]:
    from s0_checks import suite_recheck as sr

    return sr()


def t03_recheck() -> dict[str, Any]:
    from bench.common.labeling import label_one
    from bench.common.testgen import read_tests

    d = BENCH / "T03_kth_smallest"
    cases = read_tests(d / "tests.jsonl")
    refs = sorted((d / "references").glob("*.py"))

    def lab(code: str, sid: str) -> dict[str, Any]:
        return label_one({"sample_id": sid, "task": "T03", "condition": "recheck", "mode": None, "paraphrase_id": None,
                          "round": None, "attempt_idx": None, "seed": 0, "finish_reason": "stop",
                          "text": "```python\n" + code + "\n```"}, cases)
    with ThreadPoolExecutor(4) as ex:
        rl = list(ex.map(lambda p: (p.stem, lab(p.read_text(), p.stem)), refs))
    ref_ok = sum(1 for m, l in rl if l.get("runtime_label") == m and l.get("passed"))
    gold = read_jsonl(d / "gold_set.jsonl")
    with ThreadPoolExecutor(4) as ex:
        gl = list(ex.map(lambda g: lab(g["code"], g["gold_id"]), gold))
    agree = [l.get("runtime_label") == g["adjudicated"] for g, l in zip(gold, gl)]
    gate = read_json(d / "gate.json")
    exp = gate["gold"]["runtime_vs_adjudicated"]
    acc = sum(agree) / max(len(agree), 1)
    return {"references_ok": ref_ok, "n_references": len(refs), "references": [(m, l.get("runtime_label"),
            bool(l.get("passed"))) for m, l in rl], "gold_n": len(gold), "gold_runtime_vs_adjudicated": acc,
            "gate_runtime_vs_adjudicated": exp, "within_0.02": abs(acc - exp) <= 0.02 + 1e-9,
            "references_pass": ref_ok == len(refs)}


def openrouter_key() -> dict[str, Any]:
    import urllib.error
    import urllib.request

    base = os.environ.get("OPENROUTER_BASE_URL", "")
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not base or not key:
        return {"ok": False, "error": "OPENROUTER_BASE_URL / OPENROUTER_API_KEY not set"}
    try:
        req = urllib.request.Request(base.rstrip("/") + "/key", headers={"Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode())
        data = d.get("data", d)
        return {"ok": True, "limit": data.get("limit"), "usage": data.get("usage"),
                "limit_remaining": data.get("limit_remaining")}
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, TimeoutError) as e:
        return {"ok": False, "error": str(e)[:300]}


def run_s0() -> dict[str, Any]:
    t0 = write_t0()
    logger.info(f"S0 t0 = {t0['t0_utc']}")
    vi = verify_inputs()
    write_json(RESULTS_DIR / "input_hashes.json", vi)
    logger.info(f"S0 inputs: pass={vi['pass']} mismatches={len(vi['mismatches'])} exp17 hashes "
                f"{vi['exp17_input_hashes']['n_ok']}/{vi['exp17_input_hashes']['n_checked']} T03 commitment "
                f"{vi['exp11_T03_commitment']} src verbatim={vi['exp17_src_all_verbatim']}")
    sc = seed_collisions()
    write_json(RESULTS_DIR / "seed_collisions.json", sc)
    logger.info(f"S0 seed collisions: {sc['collisions']} (pass={sc['pass']})")
    hw = hardware()
    write_json(RESULTS_DIR / "hardware.json", hw)
    logger.info(f"S0 hardware: {hw}")
    ok = openrouter_key()
    write_json(RESULTS_DIR / "openrouter_key_s0.json", ok)
    logger.info(f"S0 OpenRouter key: {ok}")
    lr = {"T03_bench": t03_recheck(), "exp8_suite": suite_recheck(),
          "exp17_recheck_for_comparison": read_json(ROOT / "inputs/exp17/results/labeller_recheck.json")
          if (ROOT / "inputs/exp17/results/labeller_recheck.json").exists() else None,
          "note": "mechanical labels only (runtime/AST); the judge is not re-run (spend)"}
    write_json(RESULTS_DIR / "labeller_recheck.json", lr)
    logger.info(f"S0 labeller recheck: T03 refs {lr['T03_bench']['references_ok']}/{lr['T03_bench']['n_references']} "
                f"gold {lr['T03_bench']['gold_runtime_vs_adjudicated']:.3f} (gate "
                f"{lr['T03_bench']['gate_runtime_vs_adjudicated']:.3f}); suite refs "
                f"{lr['exp8_suite']['references_ok']}/{lr['exp8_suite']['n_references']}")
    return {"inputs_pass": vi["pass"], "seed_pass": sc["pass"], "hardware": hw, "labeller": lr}
