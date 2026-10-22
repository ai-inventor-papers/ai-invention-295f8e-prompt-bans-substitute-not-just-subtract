#!/usr/bin/env python3
"""CPU stages: U1-U8 unit tests (results/tests_cpu.json) and COMMIT #0 (protocol, thresholds, decision rules, drop
order, code hashes, input hashes, hardware)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import commit7 as CM  # noqa: E402
import forks as FK  # noqa: E402
import opening_cls as OC  # noqa: E402
import predict as PR  # noqa: E402
from cfg7 import (CACHE_DIR, E25, E26, INPUTS, PRED_DIR, RESULTS_DIR, ROOT, THRESH, UNITS, read_json,  # noqa: E402
                  read_jsonl, sha256_file, utc_now, write_json)

PROTOCOL = """Claim T (iteration 7), Qwen/Qwen3-8B rev b968826d, bf16 HF, thinking off. Mixed units B3 (kruskal vs
prim_heap), A3 (prefix_suffix_max vs two_pointers), B6 (sort_compare vs a counting mode); collapsed T1, T2, T10, T03.
S0 twins N=100 (slots 0-19 x W1-W5); S1 fork location by prefix resampling (8 per prefix length k in {0,4,...,96}),
Bayesian single change point (Dirichlet(1)-multinomial, uniform tau, prior 0.5), detection P >= 0.9 and own-share jump
>= 0.4, refine at single prefix lengths, confirm with 20 continuations at f-1, f and controls f-9, f+8 (jump >= 0.5,
Fisher p < 0.01, controls move < 0.2); sampler calibration on pooled k = 0 continuations (Fisher p > 0.01).
S2 predictions from teacher-forced fp32 logits under every template (equal-weight average): opening probability
w_T(c), token conditionals Phat(A | t) (20 continuations under W1 + 5 under each other template, Jeffreys),
F_T(c, A), q_rest; T in {0.3, 0.7, 1.0, 1.3} x {full, top-k 10}; collapsed margins; S4 teacher-forced numbers.
COMMIT #2 before the first sweep / S4 sample. S3 sweep: N = 50 per cell, the same 50 streams in all 8 cells.
Tests: (1) H(A | fork class) <= 0.3 bits on >= 2 mixed units (disconfirm > 0.5); (2) minority drop T 1.0 -> 0.3
>= 0.15 (exact one-sided McNemar, slot bootstrap) and MAE <= 0.10 over 8 cells and |dObs(1.0->1.3) - dPred| <= 0.10,
on >= 2 units (disconfirm MAE > 0.2 on >= 2 units); (3) collapsed margins >= 4 nats on all 4 collapsed tasks.
Verdict SUPPORTED if (1)-(3) pass; PARTIAL if some pass; DISCONFIRMED if a disconfirming branch fires."""

DROP_ORDER = ["B6", "S4(a) on B6 and A3", "top-k 10 cells at T 0.7", "collapsed T 1.3 check"]
NEVER_DROP = ["B3 and A3 forks and predictions", "sweep at top-p 1 and top-k 10", "collapsed margins",
              "S4(b) on B3", "novelty audit"]
CODE0 = ["src/cfg7.py", "src/forks.py", "src/predict.py", "src/replay.py", "src/opening_cls.py", "src/engine7.py",
         "src/gpu7.py", "src/stages7.py", "src/prompts7.py", "src/label7.py", "src/commit7.py", "src/cpu7.py"]


def u1_labeller() -> dict[str, Any]:
    rows = []
    refs = {"B3": E26 / "units" / "B3" / "references", "B6": E26 / "units" / "B6" / "references"}
    for u, d in refs.items():
        for f in sorted(d.glob("*.py")):
            rows.append({"sid": f"ref|{u}|{f.stem}", "unit": u, "text": "```python\n" + f.read_text() + "\n```",
                         "want": f.stem})
    sys.path.insert(0, str(E25))
    import importlib.util
    spec = importlib.util.spec_from_file_location("a3def", E25 / "newbench" / "A3_trapping_rain_water" / "unit_def.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    for k, code in m.REFERENCES.items():
        rows.append({"sid": f"ref|A3|{k}", "unit": "A3", "text": "```python\n" + code + "\n```", "want": k})
    tmp = CACHE_DIR / "tmp" / "u1_in.jsonl"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text("".join(json.dumps(r) + "\n" for r in rows))
    out = tmp.with_name("u1_out.jsonl")
    subprocess.run([sys.executable, str(ROOT / "src" / "label7.py"), str(tmp), str(out)], check=True,
                   capture_output=True, text=True, timeout=1200)
    res = read_jsonl(out)
    per = [{"sid": r["sid"], "want": x["want"], "got": r["label"], "passed": r["passed"]} for x, r in zip(rows, res)]
    # U6: references truncated to their first 70% of characters classify to their own label or 'undecided'
    u6 = []
    for x in rows:
        code = x["text"]
        lab = OC.classify(x["unit"], code)
        u6.append({"sid": x["sid"], "full": lab, "want": x["want"]})
    return {"U1": {"rows": per, "all_correct": all(p["want"] == p["got"] and p["passed"] for p in per)},
            "U6": {"rows": u6, "all_correct": all(r["full"] == r["want"] for r in u6
                                                 if r["want"] in UNITS[r["sid"].split("|")[1]]["catalogue"])}}


def u4_changepoint(n_runs: int = 200) -> dict[str, Any]:
    rng = np.random.default_rng(11)
    K, n = 25, 8
    hits = fps = 0
    for _ in range(n_runs):
        tau = int(rng.integers(5, 20))
        p = np.where(np.arange(K) < tau, 0.3, 0.9)
        S = np.stack([np.bincount(rng.random(n) < pk, minlength=2)[::-1] for pk in p]).astype(float)
        cps = FK.change_points(S, 0, 0.9, 0.4)
        hits += any(c["tau_idx"] == tau or abs(c["tau_idx"] - tau) <= 1 for c in cps)
        S0 = np.stack([np.bincount(rng.random(n) < 0.5, minlength=2)[::-1] for _ in range(K)]).astype(float)
        fps += bool(FK.change_points(S0, 0, 0.9, 0.4))
    return {"detect_rate_0.6_jump": hits / n_runs, "false_positive_rate": fps / n_runs,
            "pass": hits / n_runs >= 0.9 and fps / n_runs <= 0.05}


def run_tests() -> dict[str, Any]:
    out: dict[str, Any] = {"utc": utc_now()}
    out.update(u1_labeller())
    out["U2"] = {k: v for k, v in read_json(RESULTS_DIR / "gpu_tests.json").items() if k.startswith("U2")} \
        if (RESULTS_DIR / "gpu_tests.json").exists() else None
    out["U3"] = read_json(RESULTS_DIR / "u3_prompt_checks.json")["all_pass_required"]
    out["U4"] = u4_changepoint()
    out["U5"] = PR.u5_test()
    out["U7"] = CM.self_test(CACHE_DIR / "tmp" / "commit_test")
    out["U8"] = PR.u8_test()
    write_json(RESULTS_DIR / "tests_cpu.json", out)
    return out


def commit0() -> dict[str, str]:
    hashes = read_json(INPUTS / "input_hashes.json")
    payload = {"protocol": PROTOCOL, "thresholds": THRESH, "drop_order": DROP_ORDER, "never_drop": NEVER_DROP,
               "units": {u: {k: v for k, v in U.items()} for u, U in UNITS.items()},
               "sampler_transform": "fp64(bf16 logits) / T -> top-k mask (keep p >= k-th largest) -> cumsum over the "
                                    "full vocabulary in TOKEN-ID order, normalised by the kept mass -> "
                                    "searchsorted(u, side=left); u = PCG64(sha256 key) stream, one uniform per token",
               "code_sha256": CM.code_hashes(CODE0), "input_hashes_sha256": sha256_file(INPUTS / "input_hashes.json"),
               "n_input_files": len(hashes),
               "hardware": read_json(PRED_DIR / "hardware.json") if (PRED_DIR / "hardware.json").exists() else None,
               "note": "written after the S0 twins were generated (twins are reference data, not a decisive test); "
                       "every threshold above is the one in src/cfg7.py THRESH, frozen before the twins ran."}
    return CM.commit("commit0", payload)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "tests"
    if what == "tests":
        print(json.dumps({k: (v.get("pass", v.get("all_correct")) if isinstance(v, dict) else v)
                          for k, v in run_tests().items()}, indent=1))
    elif what == "commit0":
        print(commit0())


def commit1() -> dict[str, str]:
    """COMMIT #1 (before any temperature sample): openings, coverages, base paths, scan hashes, change points,
    confirmed forks, calibration verdicts and each unit's prediction mode."""
    from cfg7 import CONTS, SAMPLES_RAW
    F = read_json(RESULTS_DIR / "forks.json")
    body = {u: {"D": v["D"], "A_min": v["A_min"], "mode": v["mode"], "opening": v["opening"],
                "base_paths": v["base_paths"],
                "forks": {b: {k: ib.get(k) for k in ("primary", "f", "confirmed", "fork_token", "fork_token_id",
                                                     "at_O_plus_1", "confirm", "cps", "perm")}
                          for b, ib in v["per_base_path"].items()},
                "calibration": v["calibration"], "n_confirmed": v["n_confirmed"],
                "n_confirmed_on_O": v["n_confirmed_on_O"], "n_at_O_plus_1": v["n_at_O_plus_1"]}
            for u, v in F.items()}
    payload = {"forks": body, "continuations_sha256": sha256_file(CONTS), "samples_raw_sha256": sha256_file(SAMPLES_RAW),
               "twins": read_json(RESULTS_DIR / "twins.json"),
               "opening_classifier": read_json(RESULTS_DIR / "opening_classifier.json"),
               "amendments": [d for d in read_json(RESULTS_DIR / "deviations.json") if d["id"].startswith("amend")],
               "mode_rule": "ONE-TOKEN if >= 2/3 of the confirmed forks of on-O base paths sit at |O|+1, else TREE"}
    return CM.commit("commit1_forks", payload)
