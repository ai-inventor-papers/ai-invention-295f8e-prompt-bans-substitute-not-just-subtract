#!/usr/bin/env python3
"""S0-S5: setup checks (hardware, input hashes, OpenRouter key and smoke calls), the harness gate G-HARNESS (U1/U2),
the probe set (U3), the corpus and the instrument gate G-INSTR (U9)."""
from __future__ import annotations

import json
import os
import subprocess
import time
from typing import Any

import numpy as np
import requests
from loguru import logger

import bp
import refs
from common import (DATA, INPUTS, PRED, RESULTS, ROOT, container_ram_gb, detect_cpus, deviation, milestone,
                    partial_status, read_json, sha256_file, write_json)

EXPECTED_SETS = {
    "SEL-OR": "4fa84e1e8d2fcb7d7a49f2fc4b6dff3c14c6980f741d7e6c9804c46f47de82d7",
    "SEL-W": "7f95af860eabf585434030cbb95b62f217a7b23443bbed0e60f1b8c2974e68d3",
    "P1SRC-W": "e6eb2fb86a9da2d6fa849099b25cc4712061858f7af18d41ca4f78e5bc3af6e1",
    "P1SRC-OR": "3a2a73f5af220e978e00614ea087769306ed0da0f18a440f90502c150fdc715c",
    "H-OR3": "b89390f503db5bd471361efb3b9aa57c147be39678f78f64d1fe13df533d31a1",
    "FS-OR3": "b89390f503db5bd471361efb3b9aa57c147be39678f78f64d1fe13df533d31a1",
    "H-FSW5k": "e58e2ff43f97b0093407a2efdbd68b0dce316b79c5352e39073c53ce57ee9703",
}
NOTEBOOK_SHA = "eec45846a8661722addbb856179327cf2ede0bc502e32be4ad58a6ac54e0aca6"
HELDOUT = {"H-OR3_bf_excess_pct": 5.3678, "H-FSW5k_bf_excess_pct": 3.9843, "factor": 0.8,
           "H-OR3_threshold_pct": 4.294, "H-FSW5k_threshold_pct": 3.187}


def or_base() -> str:
    return os.environ["OPENROUTER_BASE_URL"].rstrip("/")


def or_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}", "Content-Type": "application/json"}


def get_key() -> dict[str, Any]:
    try:
        r = requests.get(or_base() + "/key", headers=or_headers(), timeout=30)
        d = r.json()
        return {"status": r.status_code, "data": d.get("data", d)}
    except (requests.RequestException, ValueError) as e:
        return {"status": None, "error": repr(e)[:200]}


# ---------------------------------------------------------------------------------------------- S0
def s0_setup(smoke: bool = True) -> dict[str, Any]:
    out: dict[str, Any] = {}
    try:
        smi = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used,driver_version",
                              "--format=csv,noheader"], capture_output=True, text=True, timeout=60).stdout.strip()
    except (OSError, subprocess.SubprocessError) as e:
        smi = f"error {e!r}"
    hw = {"gpu": smi, "cpus_cgroup": detect_cpus(), "ram_gb_cgroup": container_ram_gb(),
          "cpu_quota_raw": _read("/sys/fs/cgroup/cpu/cpu.cfs_quota_us"),
          "cpu_period_raw": _read("/sys/fs/cgroup/cpu/cpu.cfs_period_us"),
          "eval_workers": 5, "worker_rlimit_as_gib": 2.0, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    write_json(PRED / "hardware.json", hw)
    out["hardware"] = hw
    # instance hashes and corpus files
    hashes = {}
    mism = []
    hg9 = read_json(INPUTS / "bp9" / "harness_gate.json")["instance_sha256"]
    for name in sorted(hg9):
        h = bp.sha_insts(bp.load_set(name))
        want = EXPECTED_SETS.get(name, hg9[name])
        hashes[name] = {"sha256": h, "expected": want, "ok": h == want}
        if h != want:
            mism.append(name)
    ext = read_json(INPUTS / "bp9" / "ext_sources.json")
    ext_rows = []
    for r in ext:
        p = ROOT / r["local"]
        got = sha256_file(p) if p.exists() else None
        ext_rows.append({"local": r["local"], "expected": r.get("sha256"), "sha256": got,
                         "ok": got == r.get("sha256")})
        if got != r.get("sha256"):
            mism.append(r["local"])
    nb2 = sha256_file(ROOT / "ext" / "funsearch" / "bin_packing.ipynb")
    ext_rows.append({"local": "ext/funsearch/bin_packing.ipynb (copy read by bp.py)", "expected": NOTEBOOK_SHA,
                     "sha256": nb2, "ok": nb2 == NOTEBOOK_SHA})
    if nb2 != NOTEBOOK_SHA:
        mism.append("bin_packing.ipynb")
    out["instance_hashes"] = hashes
    out["ext_hashes"] = ext_rows
    out["hash_mismatches"] = mism
    out["inputs_ok"] = not mism
    write_json(RESULTS / "input_verification.json", out)
    if mism:
        partial_status({"stopped": True, "reason": f"input hash mismatch: {mism}"})
        raise SystemExit(f"input hash mismatch: {mism}")
    out["key_start"] = get_key()
    write_json(RESULTS / "key_start.json", out["key_start"])
    if smoke:
        out["smoke"] = smoke_calls()
        write_json(RESULTS / "smoke.json", out["smoke"])
    milestone("S0_done", inputs_ok=out["inputs_ok"])
    return out


def _read(p: str) -> str | None:
    try:
        return open(p).read().strip()
    except OSError:
        return None


def smoke_calls() -> dict[str, Any]:
    from common import add_cost
    res = {}
    for m in ["qwen/qwen3-32b", "qwen/qwen3-14b"]:
        body = {"model": m, "messages": [{"role": "user", "content": "Write a one-line Python function that adds two "
                                                                       "numbers."}],
                "temperature": 1.0, "top_p": 1.0, "max_tokens": 512, "seed": 1, "reasoning": {"enabled": True},
                "usage": {"include": True},
                "provider": {"order": ["DeepInfra"], "allow_fallbacks": False, "quantizations": ["fp8"]}}
        t0 = time.time()
        try:
            r = requests.post(or_base() + "/chat/completions", headers=or_headers(), json=body, timeout=180)
            d = r.json()
            u = d.get("usage") or {}
            msg = (d.get("choices") or [{}])[0].get("message") or {}
            add_cost("smoke", float(u.get("cost") or 0.0))
            res[m] = {"status": r.status_code, "provider": d.get("provider"), "latency_s": round(time.time() - t0, 1),
                      "cost": u.get("cost"), "reasoning_present": bool(msg.get("reasoning")),
                      "reasoning_tokens": (u.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                      "completion_tokens": u.get("completion_tokens"),
                      "finish_reason": (d.get("choices") or [{}])[0].get("finish_reason"),
                      "content_head": (msg.get("content") or "")[:200], "error": d.get("error")}
        except (requests.RequestException, ValueError) as e:
            res[m] = {"status": None, "error": repr(e)[:300]}
        logger.info(f"smoke {m}: {res[m]}")
    return res


# ---------------------------------------------------------------------------------------------- S1
def s1_harness() -> dict[str, Any]:
    import sandbox
    out: dict[str, Any] = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    sets = {n: bp.load_set(n) for n in ["FS-OR3", "H-OR3", "H-FSW5k", "SEL-OR", "SEL-W", "P1SRC-OR"]}
    out["binpack3_equals_notebook_OR3"] = bool(
        len(sets["H-OR3"]) == len(sets["FS-OR3"]) and
        all(a["id"].strip() == b["id"].strip() and a["items"] == b["items"] and a["capacity"] == b["capacity"]
            for a, b in zip(sets["H-OR3"], sets["FS-OR3"])))
    _, _, or_src, w_src = bp.funsearch_notebook()
    c12, _, m1 = sandbox.compile_program(or_src)
    c14nb, _, m2 = sandbox.compile_program(w_src)
    np.seterr(all="ignore")

    def fam(name, prio):
        t = time.perf_counter()
        b = bp.eval_set(sets[name], prio)
        mb, ml = float(np.mean(b)), float(np.mean([x["l1"] for x in sets[name]]))
        return {"mean_bins": mb, "mean_l1": ml, "excess_pct": 100 * (mb - ml) / ml, "bins": b,
                "secs": round(time.perf_counter() - t, 2)}
    g = {"BF_OR3": fam("FS-OR3", bp.prio_bf), "BF_binpack3": fam("H-OR3", bp.prio_bf),
         "BF_W5k": fam("H-FSW5k", bp.prio_bf), "c12vec_OR3": fam("FS-OR3", bp.prio_c12_vec),
         "c12nb_OR3": fam("FS-OR3", c12), "c14_W5k": fam("H-FSW5k", bp.prio_c14),
         "c14nb_W5k": fam("H-FSW5k", c14nb)}
    targets = {"BF_OR3": (212.0, 5.37), "BF_binpack3": (212.0, 5.37), "BF_W5k": (2067.0, 3.98),
               "c12vec_OR3": (207.45, 3.11), "c12nb_OR3": (207.45, 3.11), "c14_W5k": (2001.4, 0.68),
               "c14nb_W5k": (2001.4, 0.68)}
    ok = out["binpack3_equals_notebook_OR3"]
    for k, (mb, ex) in targets.items():
        passed = abs(g[k]["mean_bins"] - mb) <= 0.01 and abs(round(g[k]["excess_pct"], 2) - ex) < 1e-9
        g[k].update(target=[mb, ex], passed=bool(passed))
        ok &= passed
        logger.info(f"{k}: mean={g[k]['mean_bins']:.3f} excess={g[k]['excess_pct']:.3f}% target {mb}/{ex}% "
                    f"{'PASS' if passed else 'FAIL'}")
    g["BF_OR3_equals_binpack3"] = g["BF_OR3"]["bins"] == g["BF_binpack3"]["bins"]
    ok &= g["BF_OR3_equals_binpack3"]
    out["gate"] = g
    # hand-coded packers (FF/BF/WF on SEL-OR and P1SRC-OR)
    eq = {}
    for r in ["FF", "BF", "WF"]:
        eq[r] = all(bp.pack(x["items"], x["capacity"], refs.FUNCS[r]) == refs.hand_pack(r, x["items"], x["capacity"])
                    for x in sets["SEL-OR"] + sets["P1SRC-OR"])
    out["priority_vs_handcoded_FF_BF_WF"] = eq
    ok &= all(eq.values())
    bf_or = fam("SEL-OR", bp.prio_bf)
    bf_w = fam("SEL-W", bp.prio_bf)
    out["sel_bf"] = {"or_excess": bf_or["excess_pct"] / 100, "w_excess": bf_w["excess_pct"] / 100,
                     "or_bins": bf_or["bins"], "w_bins": bf_w["bins"]}
    sel_ok = abs(out["sel_bf"]["or_excess"] - 0.059979) < 5e-7 and abs(out["sel_bf"]["w_excess"] - 0.042310) < 5e-7
    out["sel_bf_targets"] = {"or": 0.059979, "w": 0.042310, "passed": bool(sel_ok)}
    ok &= sel_ok
    out["u2"] = refs.unit_test_u2()
    ok &= out["u2"]["passed"]
    out["heldout_thresholds"] = HELDOUT
    out["heldout_check"] = {"BF_H-OR3_excess_pct": g["BF_binpack3"]["excess_pct"],
                            "BF_H-FSW5k_excess_pct": g["BF_W5k"]["excess_pct"]}
    out["G_HARNESS_PASS"] = bool(ok)
    write_json(RESULTS / "harness_gate_v10.json", out)
    milestone("S1_done", passed=out["G_HARNESS_PASS"])
    logger.info(f"G-HARNESS {'PASS' if ok else 'FAIL'}")
    return out


# ---------------------------------------------------------------------------------------------- S3-S5
def s3_probes() -> dict[str, Any]:
    import probes
    u3 = probes.unit_test_u3()
    summ = u3["summary"]
    rec = {"P10": {"path": "data/probes/P10.json", "sha256": summ["sha256"], **summ}, "u3": u3,
           "rule_text": probes.RULE_TEXT,
           "cross_artifact_note": "NOV-B1/NOV-B2 apply the same shared iteration-10 text rule; cross-artifact "
                                  "agreement numbers are descriptive unless the P10 sha256 values match."}
    write_json(RESULTS / "probes.json", rec)
    milestone("S3_done", sha256=summ["sha256"], passed=u3["passed"])
    return rec


def s4_s5(n_workers: int = 5, probe: str = "P10") -> dict[str, Any]:
    import corpus
    import gate_instr
    import probes
    import sandbox
    hg = read_json(RESULTS / "harness_gate_v10.json")
    pool = sandbox.EvalPool(n_workers, ROOT, 2.0)
    try:
        if not (RESULTS / "corpus.json").exists():
            c = corpus.build(pool, hg)
        else:
            c = read_json(RESULTS / "corpus.json")
        milestone("S4_corpus_done", n=c["n_members"], tuned=c["tuned_ab"])
        vecs = corpus.load_vectors()
        states = probes.load_states(probe)
        meta = probes.load_meta(probe)
        g = gate_instr.run_gate(pool, probe, states, meta, vecs)
        gate_instr.save(g, "instrument_gate.json" if probe == "P10" else f"instrument_gate_{probe}.json")
        milestone("S5_gate_done", probe=probe, passed=g["passed"])
        # corpus agreement matrix (all states and informative subset) + calibration pairs
        import instr
        R = {cc: {int(s): np.array(v, dtype=np.uint16) for s, v in sv.items()}
             for cc, sv in g["reference_vectors"].items()}
        allv = {**{f"catalogue:{k}": v for k, v in R.items()}, **vecs}
        stoch = {n: instr.is_stochastic(v) for n, v in allv.items()}
        stoch["catalogue:RF"] = True
        names = list(allv)
        inf = np.array([m["informative"] for m in meta])
        cal = {"c14_vs_abWF(1,21)": instr.A(vecs["funsearch:c14"], vecs["published:ab-WF(1,21)"]),
               "c12_vs_abFF(5,24)": instr.A(vecs["funsearch:c12_vec"], vecs["published:ab-FF(5,24)"]),
               "c12nb_vs_c12vec": instr.A(vecs["funsearch:c12"], vecs["funsearch:c12_vec"]),
               "reevo_seed_vs_c14": instr.A(vecs["reevo:seed_func"], vecs["funsearch:c14"])}
        cal_inf = {"c14_vs_abWF(1,21)": instr.A(vecs["funsearch:c14"], vecs["published:ab-WF(1,21)"], False, inf),
                   "c12_vs_abFF(5,24)": instr.A(vecs["funsearch:c12_vec"], vecs["published:ab-FF(5,24)"], False,
                                                inf)}
        mat = corpus.agreement_matrix(names, allv, stoch)
        mat_inf = corpus.agreement_matrix(names, allv, stoch, inf)
        write_json(RESULTS / "corpus_agreement.json",
                   {"names": names, "stochastic": stoch, "A_all": mat, "A_informative": mat_inf,
                    "calibration_all": cal, "calibration_informative": cal_inf, "probe": probe}, indent=None)
        logger.info(f"calibration: {cal}")
    finally:
        pool.close()
    return {"corpus_members": c["n_members"], "tuned": c["tuned_ab"], "gate_passed": g["passed"],
            "gate_parts": g["parts"], "min_margin": g["min_margin"]}
