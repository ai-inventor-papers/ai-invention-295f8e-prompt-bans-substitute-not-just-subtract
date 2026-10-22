#!/usr/bin/env python3
"""Bookkeeping and report tables of step K: engine check against exp30 (S0), timing, costs, deviations, the
commit-order audit (no decisive row predates its commit) and results/report_tables.md (the README's tables).

usage: .venv/bin/python src/report_k.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

import k_cfg as K  # noqa: E402
from k_cfg import RESULTS, read_json, read_jsonl, write_json  # noqa: E402


def engine_check() -> dict[str, Any]:
    labs = {l["key"]: l for l in read_jsonl(K.LABELS)}
    e30 = {}
    for l in read_jsonl(K.E30 / "data" / "labels.jsonl"):
        if l.get("arm") == "TWIN":
            e30[(l["task"], l["template"], int(l["slot"]))] = l
    out: dict[str, Any] = {"reference": "exp30 data/labels.jsonl TWIN rows (bf16 HF engine, RTX 2000 Ada, max_new 384)"}
    for t in K.D5_TASKS:
        agree, same_code, n = 0, 0, 0
        ks = (0, 1, 2, 3) if t in ("T2", "T03") else tuple(range(10))
        for w in K.TEMPLATES:
            for k in ks:
                a = labs.get(f"{t}|{w}|TWIN|{k}")
                b = e30.get((t, w, k))
                if a is None or b is None:
                    continue
                n += 1
                agree += a["label"] == b["label"] and bool(a["passed"]) == bool(b["passed"])
                same_code += (a.get("code") or "") == (b.get("code") or "")
        out[t] = {"slots": n, "label_and_pass_agreement": agree / n if n else None,
                  "identical_code": same_code / n if n else None,
                  "planned_check": t in ("T2", "T03")}
    out["pass_0.95"] = all((v["label_and_pass_agreement"] or 0) >= 0.95 for k, v in out.items()
                           if isinstance(v, dict) and v.get("planned_check"))
    comp = {}
    for t in K.D5_TASKS:
        rows = [labs.get(f"{t}|{w}|TWIN|{k}") for w in K.TEMPLATES for k in range(10)]
        rows = [r for r in rows if r]
        comp[t] = {"N": len(rows), "labels": dict(Counter(r["label"] for r in rows)),
                   "pass": sum(bool(r["passed"]) for r in rows) / max(len(rows), 1)}
    out["twin_compositions_k0_9"] = comp
    write_json(RESULTS / "engine_check.json", out)
    return out


def timing() -> dict[str, Any]:
    rows = read_jsonl(RESULTS / "timing.jsonl")
    by = defaultdict(lambda: {"batches": 0, "rows": 0, "seconds": 0.0, "steps": 0, "length_rows": 0})
    for r in rows:
        b = by[r["stage"]]
        b["batches"] += 1
        b["rows"] += r["B"]
        b["seconds"] += r["seconds"]
        b["steps"] += r["steps"]
        b["length_rows"] += r.get("n_length", 0)
    for b in by.values():
        b["s_per_program"] = b["seconds"] / max(b["rows"], 1)
        b["ms_per_step_per_batch"] = 1000 * b["seconds"] / max(b["steps"], 1)
    kn = read_jsonl(RESULTS / "knobs_timing.jsonl")
    tot_k = sum(r["seconds"] for r in kn)
    out = {"instruct_runner_stages": dict(by), "instruct_runner_total_s": sum(b["seconds"] for b in by.values()),
           "instruct_runner_programs": sum(b["rows"] for b in by.values()),
           "knob_process_batches": len(kn), "knob_process_total_s": tot_k,
           "staged_scaling": "anchors ran W1 (20 rows, the 10-slot stage) before W2-W5; the measured s/program "
                             "(T10 ~0.4 s, T2 ~0.6 s at B = 12) put the whole plan far inside the budget, so every "
                             "cell ran at its full N and nothing in the drop order was dropped",
           "gpu_hours_total_estimate": round((sum(b["seconds"] for b in by.values()) + tot_k) / 3600, 3)}
    write_json(RESULTS / "timing.json", out)
    return out


def costs() -> dict[str, Any]:
    paths = read_json(RESULTS / "openrouter_cost_paths.json") if (RESULTS / "openrouter_cost_paths.json").exists() \
        else {"total_usd": 0.0}
    bench = 0.0
    n_b = 0
    for r in read_jsonl(K.LOGS / "openrouter_spend.jsonl"):
        bench += float(r.get("cost") or r.get("usd") or 0.0)
        n_b += 1
    nov = read_json(RESULTS / "novelty_costs.json") if (RESULTS / "novelty_costs.json").exists() else {"total_usd": 0.0}
    out = {"labeller_path_judge_usd": paths.get("total_usd", 0.0), "labeller_path_judge_calls": paths.get("n_calls"),
           "labeller_bench_judge_usd": bench, "labeller_bench_judge_calls": n_b,
           "novelty_judges_usd": nov.get("total_usd", 0.0), "novelty_judge_calls": nov.get("n_calls", 0),
           "budget_refusals": paths.get("budget_refusals", 0) + nov.get("refusals", 0)}
    out["total_usd"] = out["labeller_path_judge_usd"] + bench + out["novelty_judges_usd"]
    write_json(RESULTS / "costs.json", out)
    return out


def commit_audit() -> dict[str, Any]:
    entries = [l.split("  ") for l in (K.ROOT / "commitments.log").read_text().splitlines() if l.strip()]
    t_c1 = min(e[1] for e in entries if "COMMIT #1" in e[4])
    t_c2 = min(e[1] for e in entries if "COMMIT #2" in e[4])
    t_e1 = min((e[1] for e in entries if "EXPLORATORY E1" in e[4]), default=None)
    t_e3 = min((e[1] for e in entries if "EXPLORATORY E3" in e[4]), default=None)
    rows = read_jsonl(K.RAW)
    knob = read_jsonl(K.RAW_DIR / "knobs_norm.jsonl")
    s12 = [r for r in rows if r["stage"] in ("S1_anchor", "S1", "S1_D5", "S2")]
    s3 = [r for r in rows if r["stage"] == "S3_PN"] + knob
    e1 = [r for r in rows if r["stage"] == "E1_sweep"]
    e3 = [r for r in rows if r["stage"] in ("E3_fresh", "E3_T03")]
    out = {"commit1_utc": t_c1, "commit2_utc": t_c2, "e1_commit_utc": t_e1,
           "S1_S2_rows": len(s12), "S1_S2_rows_before_commit1": sum(r["utc"] < t_c1 for r in s12),
           "S3_rows": len(s3), "S3_rows_before_commit2": sum(r["utc"] < t_c2 for r in s3),
           "E1_rows": len(e1), "E1_rows_before_its_commit": sum(r["utc"] < t_e1 for r in e1) if t_e1 else None,
           "E3_rows": len(e3), "E3_rows_before_its_commit": sum(r["utc"] < t_e3 for r in e3) if t_e3 else None,
           "bint_intents_before_commit2": sum(r["utc"] < t_c2 for r in read_jsonl(K.DATA / "bint_intents.jsonl"))}
    out["pass"] = out["S1_S2_rows_before_commit1"] == 0 and out["S3_rows_before_commit2"] == 0 and \
        out["bint_intents_before_commit2"] == 0 and not out["E1_rows_before_its_commit"] and \
        not out["E3_rows_before_its_commit"]
    import commit_k
    out["chain"] = commit_k.verify()
    write_json(RESULTS / "commit_audit.json", out)
    return out


DEVIATIONS = [
    ("HW", "GPU is an RTX 4090 (24 GB, sm_89), not the planned RTX A4500 (20 GB); the memory probe chose B = 12 (the "
           "largest candidate) and every instruct row ran at B = 12 on the shared-prefix path with the full KV buffer.",
     "faster than planned; cross-GPU kernel sensitivity is bounded by the anchors (T10 D1 per-slot agreement with "
     "exp29 engine d 0.98) and the S0 engine check."),
    ("ORDER", "After the anchor cells (W1 first, then W2-W5) the GPU continued with the remaining S1 cells while the "
              "anchors were labelled (both anchors passed: 26/50 and 1/50), instead of pausing for the labels.",
     "none: every S1 cell runs under every anchor outcome; DIAG and the left-padded diagnostic were not needed."),
    ("KNOBCHECK", "Knob-check agreement was counted on (label, passed) pairs, stricter than label-only agreement.",
     "conservative: 8 of 25 (task, knob) cells failed the 10/10 rule (T03 EAP, IFG_hot, T1.3; T10, T2, T05 EAP; T1 "
     "BINT, EAP) and were regenerated here at k 2-9 (320 rows); 17 cells reuse exp27's relabelled rows (cross-engine, "
     "see knob_check.json)."),
    ("ENGINE", "S0 engine check vs exp30's bf16 twins (RTX 2000 Ada, max_new 384-640): label-and-pass agreement 15/16 on "
               "T2 and 15/16 on T03 (planned >= 0.95; one slot each diverged mid-program), 40/40 on T10 and T05, 34/40 "
               "on T1 (all bfs; 6 pass flips).",
     "logged as cross-GPU kernel sensitivity (identical code 0.81 T2, 0.94 T03, 0.48 T1); every contrast of this "
     "artifact is within one engine, and the anchors reproduce exp29/exp27 per slot (T10 D1 0.98, T2 D1 0.88)."),
    ("G2", "Gate G2's exp8-suite gold-set accuracy is 0.804 runtime / 0.859 AST over all 92 eval items, against the "
           "gate report's 0.843 / 0.888 over its 89 resolved items; exactly iteration 5's recheck values.",
     "none on labels: the labeller version is unchanged; the gate passes on equality with iteration 5's recheck."),
    ("AMEND1", "label_k.py amended before any S3 row to follow data/raw/knobs_norm.jsonl (integer sample ids).",
     "none on labels."),
    ("AMEND2", "analysis_k.py amended after S1/S2 rows existed and before E1 rows: Monte-Carlo sign-flip p reported "
               "as (hits+1)/(N+1); mediation restricted to alpha 1-2; E1 summary added.",
     "post hoc but conservative (p can no longer be 0); decision rules unchanged; Holm decisions identical."),
    ("E1", "Exploratory E1 (not in the plan): D3 (U_bf x S4) at alpha 3, 4, 6 on T10 and T2 (N 50 each), "
           "hash-committed before its first row, run after COMMIT #2 with spare GPU time.",
     "descriptive only; never enters a pre-registered test."),
    ("E3", "Exploratory E3 (not in the plan): T10 fresh slots k 10-19 for D1-D5 and the three profiles, and a T03 2x2 "
           "(D2-D4 at alpha 2, k 0-9), hash-committed before its first row.",
     "descriptive replication only; AMENDMENT 3 pins every committed analysis to its committed slots."),
    ("AMEND3", "analysis_k.py amended after the E3 rows existed: committed S1 / D5 / mediation / D* analyses read only "
               "their committed slots (T10 k 0-9; T2 alpha 2 k 0-19, alpha 1 k 0-9).",
     "none: the committed numbers are identical to the pre-E3 run (verified field by field)."),
    ("S2_T2", "On T2 the P_rest profile (rescaled to U_abs's Frobenius norm while holding only 3.7% of its energy) "
              "puts per-cell doses up to ~5x U_abs on the rest cells and breaks the programs (pass 0.00).",
     "the T2 top-vs-rest contrast is confounded by breakage; the committed primary S2 reading is T10."),
    ("NOVELTY", "Judges: mistralai/mistral-medium-3.1 and moonshotai/kimi-k2 (two families), deepseek-chat-v3.1 as "
                "the third; the manual class is the agent's read of the judges' reasons and the code.",
     "see results/novelty_audit.json."),
    ("ENV", "RLIMIT_AS is not set in the CUDA processes (it breaks CUDA's virtual-address reservations); VRAM is "
            "capped with set_per_process_memory_fraction(0.97) instead.", "none."),
]


def deviations() -> list[dict[str, str]]:
    out = [{"code": c, "deviation": d, "consequence": q} for c, d, q in DEVIATIONS]
    out += read_jsonl(RESULTS / "deviations.jsonl")
    write_json(RESULTS / "deviations.json", out)
    return out


def views() -> None:
    """Plan-named views: data/samples.jsonl (one joined row per program: protocol fields, label, outcomes, realised
    displacement summary, extracted code), results/s1_clogit.json, results/s1_mediation.json, results/displacement.json
    (mean 36-block displacement profiles per task x design x alpha)."""
    import numpy as np

    import analysis_k as A

    labs = {l["key"]: l for l in read_jsonl(K.LABELS)}
    out = []
    for name in ("raw_k.jsonl", "knobs_norm.jsonl", "reuse_exp27.jsonl"):
        for r in read_jsonl(K.RAW_DIR / name):
            l = labs.get(K.row_key(r))
            o = A.outcomes(r["task"], l)
            out.append({"key": K.row_key(r), "source": name, "task": r["task"], "template": r["template"],
                        "arm": r["arm"], "k": int(r["sample_id"]), "stage": r.get("stage"),
                        "design": r.get("design"), "alpha": r.get("alpha"), "unit_id": r.get("unit_id"),
                        "seed_scheme": r.get("seed_scheme"), "direction_seed": r.get("direction_seed"),
                        "uniform_seed": K.stable_seed(r["task"], r["template"], int(r["sample_id"])),
                        "temperature": r.get("temperature"), "top_k": r.get("top_k"), "B": r.get("B"),
                        "engine_path": r.get("engine_path"), "prompt_sha256": r.get("prompt_sha256"),
                        "n_tokens": r.get("n_tokens", r.get("n_new_tokens")), "finish_reason": r.get("finish_reason"),
                        "realised_disp": r.get("realised_disp"), "unit_mean_b12": r.get("unit_mean_b12"),
                        "label": (l or {}).get("label"), "passed": (l or {}).get("passed"),
                        "valid": (l or {}).get("valid"), "labeller_source": (l or {}).get("labeller_source"),
                        "Y": o.get("Y"), "Y_any": o.get("Y_any"), "A": o.get("A"),
                        "code": (l or {}).get("code")})
    p = K.DATA / "samples.jsonl"
    p.write_text("".join(json.dumps(x, default=K._json_default) + "\n" for x in out))
    s1 = read_json(RESULTS / "s1_2x2.json")
    write_json(RESULTS / "s1_clogit.json", {k: v.get("clogit") for k, v in s1["tables"].items()})
    write_json(RESULTS / "s1_mediation.json", s1.get("mediation", {}))
    prof: dict = defaultdict(lambda: defaultdict(list))
    for r in read_jsonl(K.REALISED):
        for f in ("spec_mean", "spec_pos", "R", "gen1"):
            if r.get(f):
                prof[f"{r['task']}|{r['design']}|a{r['alpha']:g}"][f].append(r[f])
    disp = {k: {f: {"n": len(v), "mean": np.mean(np.array(v), axis=0).round(4).tolist()} for f, v in d.items()}
            for k, d in prof.items()}
    write_json(RESULTS / "displacement.json", disp)


@logger.catch(reraise=True)
def main() -> None:
    K.setup_logging("report_k")
    views()
    ec = engine_check()
    tm = timing()
    co = costs()
    ca = commit_audit()
    dv = deviations()
    logger.info(f"engine check {ec['pass_0.95']}; timing {tm['gpu_hours_total_estimate']} GPU-h; cost "
                f"{co['total_usd']:.3f}; commit audit {ca['pass']}; {len(dv)} deviations")


if __name__ == "__main__":
    main()
