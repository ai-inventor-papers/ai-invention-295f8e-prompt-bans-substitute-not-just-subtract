#!/usr/bin/env python3
"""Step 4 of iteration 3 on Qwen3-8B: how far can bans and token vetoes push?

  (4b) TOKEN WALK - cumulative persistent logit vetoes of each landed algorithm's distinctive token n-gram under
       the neutral twins (no ban text), with a matched SHAM veto and (T1) a fixed TOP5 veto as controls;
  (4a) PROMPT REACH - leave-one-survivor ban lists (bench) and two-step bans (all tasks) scored as 'will' against
       forced 'can', with the C3 prediction and a preregistered list-independence test;
  (4c) LONG-FORM NOVELTY - the request's two 2,000-word-rationale instructions, thinking off and on, every
       correct off-catalogue program audited by two blind judges plus a manual pass against human/known solutions.

Baselines in the same pipeline: step 0 (neutral twins, no veto) for every veto arm; the prompt-ban comparators for
the veto; the sham veto (matched random control); forced 'can' (capability ceiling).

Usage (the order actually run; see README.md):
  uv run method.py s0                      # input copies, SHA256SUMS, bench commitment check
  uv run method.py server bf16 start       # PID-managed vLLM server (bf16, max_model_len 4608)
  uv run method.py unit bf16               # veto unit tests u1-u4 + n-gram unit tests
  uv run method.py phase A                 # T1/T2 walk + shams + fixed-TOP5 (+ committed forecasts, two-step)
  uv run method.py longform bf16           # thinking-off long-form, bf16 branch (concurrently with phase A)
  uv run method.py server bf16 stop; uv run method.py server fp8 start
  uv run method.py phase B                 # bench walk + shams, LOS after step-1 commit, two-step after step 2
  uv run method.py longform fp8_off 50     # FP8 cross-check copy + bench long-form
  uv run method.py longform fp8_on T1:10,T2:10
  uv run method.py audit corpus|controls|pool|claims
  uv run method.py analyze                 # results/*.json + figures
  uv run method.py outputs                 # method_out.json (+ full/mini/preview); also the default with no argument
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from loguru import logger  # noqa: E402

from config import (ALL_TASKS, DATA, PRED, RESULTS, TASKS, read_jsonl, setup_logging, utc_now,  # noqa: E402
                    write_json)

PY = str(ROOT / ".venv" / "bin" / "python")


def run(args: list[str]) -> None:
    logger.info("$ " + " ".join(args))
    subprocess.run([PY] + args, cwd=str(ROOT), check=True)


DEVIATIONS = [
    {"id": "D1", "what": "Hardware: NVIDIA L4 (23 GB, 300 GB/s) instead of the planned RTX A4500 (20 GB, 640 GB/s); "
                         "6 CPUs (cgroup quota 5.1), 57 GB RAM.",
     "consequence": "bf16 decode measured at ~250-410 tok/s for short programs and ~84 tok/s (shared GPU) for long-form."},
    {"id": "D2", "what": "Precision by task family instead of bf16 for every short arm: T1/T2 arms in bf16 (their "
                         "reference programs and 'can' came from bf16 exp8/exp9), bench arms (T03/T04/T06/T10) on the "
                         "official Qwen3-8B-FP8 checkpoint (their pilot programs, forced programs and 'can' came from "
                         "FP8 exp11), weight-only FP8 Marlin kernels (no C compiler for Triton).",
     "consequence": "each family is compared with references of its own precision; the bf16-vs-FP8 cross-check on "
                    "LF1-T2 bounds the precision effect for one task only."},
    {"id": "D3", "what": "Distinctive n-gram candidates must be lexical: an n-gram containing a whitespace-only token "
                         "(indentation / newline) is format-unsafe. Added after veto unit test u1: the first choice for "
                         "T2 (' dist[u]:\\n' + 11 spaces) was bypassed by re-indenting in 20/20 samples.",
     "consequence": "the plan's selection rule (argmin max collateral; ties -> smaller n) is otherwise unchanged."},
    {"id": "D4", "what": "Sham n-grams may not contain a Python keyword or the fence tag 'python' (a keyword veto breaks "
                         "syntax) and may not equal the distinctive n-gram; bench shams for T03 and T06 are reported as "
                         "NOT_CONSTRUCTIBLE (no algorithm-generic n-gram exists in their 3-6-line default programs); "
                         "T04 and T10 shams were run.",
     "consequence": "sham controls exist for T1, T2, T04, T10."},
    {"id": "D5", "what": "Unit test u2 compares no-veto requests alone vs interleaved with vetoed rows on the same "
                         "server (17/20 token-identical); a processor-free engine was not loaded (a second ~6 min load).",
     "consequence": "u2 measures plugin/batch invariance and vLLM batch nondeterminism together."},
    {"id": "D6", "what": "Forecast commits per family: the path forecasts were committed after T1/T2 walk step 1 "
                         "(bf16 phase), the bench forecasts after the bench walk step 1 (FP8 phase); each precedes every "
                         "ban sample it scores.",
     "consequence": "the commit is not a single six-task commit, but no forecast follows its samples."},
    {"id": "D7", "what": "T1 and T2 walks STALLED at step 1, so R2 for their two-step bans came from the plan's fallback "
                         "chain (no non-default catalogue label had >= 5 attempts) = the realised exp8/exp9 single-ban "
                         "substitutes (T1 DFS, T2 BF/SPFA), flagged.",
     "consequence": "the path two-step bans replicate the iteration-1 two-step design."},
    {"id": "D8", "what": "A client bug (an asyncio semaphore bound to the first event loop) crashed phase A when the "
                         "two-step batch was queued; no sample of that batch had been generated or written; the "
                         "two-step bans were run by `phases.py two_step path bf16` from the committed forecasts.",
     "consequence": "none on the data (same seeds, same prompts)."},
    {"id": "D9", "what": "Long-form thinking-off took the plan's 'split' branch (stage-10 projection 220 min > 60 min, "
                         "measured while sharing the GPU): bf16 LF1-T2 N=50, LF2-T2/LF1-T1/LF2-T1 N=25; FP8 cross-check "
                         "copy LF1-T2 N=50 and the bench cells on FP8.",
     "consequence": "T1/T2 LF cells other than LF1-T2 have N=25."},
    {"id": "D10", "what": "Optional O1 (manifold placement) and O2 (5b temperature sweep) dropped first, as the drop "
                          "order prescribes, because the L4 throughput left no room.",
     "consequence": "no internal-state claim of any kind."},
    {"id": "D11", "what": "exp9 forced labels (extended labeller) mapped onto the suite labels for T1 (astar and gbfs -> "
                          "astar_gbfs, dijkstra_unit -> dijkstra); T2 'can' for bidijkstra and dial taken from exp7 plain "
                          "attempts because exp9 ran only descriptive variants for them.",
     "consequence": "documented in results/can.json; both values are far below the C3 threshold of 0.7."},
    {"id": "D12", "what": "ASSOCIATE forecasts are unavailable for the path tasks (no association answers exist in the "
                          "path inputs).", "consequence": "the path two-step bans are scored against WALK2/SNAPBACK only."},
    {"id": "D13", "what": "Audit judge controls (T5) failed at round 0 (A 2/6, B 3/6; results/audit_controls_round0_failed"
                          ".json) because the audit prompt did not say the programs had been labelled 'other' by the "
                          "automatic labeller, and two controls were debatable (Counter-counting is a hash approach; "
                          "Sunday search is Horspool-like and T04's catalogue has BMH). The prompt gained that context "
                          "and a decision order (miss, degenerate, known variant, novel); the two controls were replaced "
                          "(hard-coded shortcut; value-range bisection). Round 1: A 5/6, B 5/6 (both call value-range "
                          "bisection a labeller miss). Judge models unchanged.",
     "consequence": "the audit ran with the round-1 prompt only."},
    {"id": "D14", "what": "Thinking-on: the floor (T1/T2, N=10 per prompt) ran; the first extension process (T1/T2 to N=25 plus bench T03/T04/T06 at N=10) was stopped after ~6 min when the KV cache saturated and nothing of it was written; the bench cells (N=10 per prompt) were re-launched alone after the thinking-off jobs ended and completed; the T1/T2 extension to N=25 was not re-run.",
     "consequence": "thinking-on cells have N=10 per prompt (upper bound on the novel rate ~26% per cell)."},
    {"id": "D15", "what": "The bf16 long-form job was restarted once with higher concurrency after the walk ended (its "
                          "stage-10 samples were kept; the interrupted batch had written nothing). The labeller-judge "
                          "client gained retries on HTTP 429/5xx after one rate-limit failure in phase B (that program "
                          "fell back to its runtime label, as the frozen combine rule prescribes).",
     "consequence": "none on the data."},
    {"id": "D16", "what": "Forecasts for the reach tests were committed per family before the samples they score; the "
                          "two disconfirming C3 cells (T03 quickselect, T10 BFS) got 'rung >= 3' from the flagged "
                          "fallback R2 because the walk stalled at step 1; a post hoc sensitivity with rung 2 := the "
                          "association answer is reported beside the preregistered verdict.",
     "consequence": "the preregistered verdict stands; the sensitivity shows which cell depends on the rung rule."},
    {"id": "D17", "what": "src/analysis.py was extended AFTER its sha256 was committed before the bench ban samples "
                          "(commitments.log line 42): labeller-miss-corrected compositions (required by the plan), the "
                          "post hoc association-rung sensitivity, the mechanism-level claim check and a Holm-family "
                          "note. No preregistered computation changed (will, the C3 cell/overall rule, the "
                          "list-independence permutation test). The committed bytes were not kept (no version control "
                          "here), so the v1 entry fails the file check in metadata.commitments; the extended file is "
                          "committed as a new chain entry, and src/rederive.py - written before that commit and never "
                          "edited - recomputes every preregistered number from raw rows with 0 mismatches.",
     "consequence": "the chain shows the edit instead of hiding it; the preregistered numbers are independently "
                    "re-derived."},
]


def assemble_outputs() -> None:
    from prompts import ban_prompt, longform_prompt, neutral_twins
    from programs import can_table

    # Committed forecasts that every example is scored against (predict_* fields, strings):
    #   predict_baseline_default    - the unconstrained baseline: the task's default algorithm (step 0, no veto/ban);
    #   predict_committed_forecast  - the forecast committed before the example's samples (walk: rung 2 = the landing
    #                                 after the default is vetoed; sham: the default survives; fixed TOP5: 'n/a');
    #   predict_survivor / predict_c3 (LOS rows) - the only allowed algorithm / C3's 'will <= 0.10' forecast;
    #   predict_walk2 / predict_associate / predict_snapback (two-step rows) - the three committed forecasts;
    #   predict_judge_a_code_mechanism / predict_judge_a_claims_novelty (long-form rows) - claim extraction (judge A).
    rung2, c3q = {}, {}
    for g in ("path", "bench"):
        p = PRED / f"reach_forecasts_{g}.json"
        if p.exists():
            for t, v in json.loads(p.read_text())["tasks"].items():
                rung2[t] = v["rung_table"]["R2"]["R2"]
                for c in v["c3_cells"]:
                    c3q[(t, c["S"])] = c["qualifies"]
    claims = {}
    cpath = RESULTS / "claims.json"
    if cpath.exists():
        claims = {r["sample_id"]: (r.get("A") or {}) for r in json.loads(cpath.read_text())["records"]}

    def default_of(t):
        return TASKS[t]["default"]

    def ex_walk(r):
        tw = neutral_twins(r["task"])
        t = r["task"]
        if r["arm"] == "walk":
            fcst = default_of(t) if (r.get("step") or 0) == 0 else str(rung2.get(t))
        elif r["arm"] == "sham":
            fcst = default_of(t)
        else:
            fcst = "n/a"
        return {"input": tw[r["template"]]["user_text"], "output": f"{r['label']}|{'pass' if r['passed'] else 'fail'}",
                "predict_baseline_default": default_of(t), "predict_committed_forecast": fcst,
                "metadata_task": r["task"], "metadata_arm": r["arm"], "metadata_step": r.get("step"),
                "metadata_round": r.get("round"), "metadata_template": r["template"], "metadata_seed": r["seed"],
                "metadata_n_veto_seqs": r.get("n_veto_seqs"), "metadata_veto_occurrences": r.get("veto_occurrences"),
                "metadata_fires": r.get("fires"), "metadata_string_leak": r.get("string_leak"),
                "metadata_engine_dtype": r["engine_dtype"], "metadata_labeller_source": r["labeller_source"],
                "metadata_code_sha256": r["code_sha256"], "metadata_code": r.get("code"),
                "metadata_finish_reason": r.get("finish_reason"), "metadata_thinking": False}

    fc = {}
    for g in ("path", "bench"):
        p = PRED / f"two_step_forecasts_{g}.json"
        if p.exists():
            fc.update(json.loads(p.read_text())["tasks"])

    def ex_ban(r):
        bp = ban_prompt(r["task"], r["template"], r["meta_banned"])
        e = {"input": bp["user_text"], "output": f"{r['label']}|{'pass' if r['passed'] else 'fail'}",
             "predict_baseline_default": default_of(r["task"]),
             "metadata_task": r["task"], "metadata_arm": r["arm"], "metadata_condition": r["condition"],
             "metadata_banned": r["meta_banned"], "metadata_template": r["template"], "metadata_seed": r["seed"],
             "metadata_engine_dtype": r["engine_dtype"], "metadata_labeller_source": r["labeller_source"],
             "metadata_code_sha256": r["code_sha256"], "metadata_code": r.get("code"), "metadata_thinking": False}
        if r["arm"] == "los":
            surv = r["condition"].split("LOS(", 1)[1].rstrip(")")
            e["predict_survivor"] = surv
            e["predict_c3"] = (f"not {surv} (will<=0.10)" if c3q.get((r["task"], surv)) else "n/a (not a C3 cell)")
        if r["arm"] == "two_step" and r["task"] in fc:
            f = fc[r["task"]]
            e["predict_walk2"] = str(f["WALK2"].get("top1"))
            e["predict_associate"] = str(f["ASSOCIATE"]["for_R2"].get("label"))
            e["predict_snapback"] = str(f["SNAPBACK"]["top1"])
        return e

    def ex_lf(r):
        a = claims.get(r["sample_id"], {})
        return {"input": longform_prompt(r["task"], r["prompt_id"]),
                "output": f"{r['label']}|{'pass' if r['passed'] else 'fail'}",
                "predict_baseline_default": default_of(r["task"]),
                "predict_judge_a_code_mechanism": str(a.get("code_mechanism_guess")),
                "predict_judge_a_claims_novelty": str(a.get("claims_novelty")), "metadata_task": r["task"],
                "metadata_arm": "longform", "metadata_prompt_id": r["prompt_id"], "metadata_thinking": r["thinking"],
                "metadata_engine_dtype": r["engine_dtype"], "metadata_seed": r["seed"],
                "metadata_rationale_words": r.get("rationale_words"), "metadata_thinking_tokens": r.get("thinking_tokens"),
                "metadata_thinking_complete": r.get("thinking_complete"), "metadata_extract_method": r.get("extract_method"),
                "metadata_code_sha256": r["code_sha256"], "metadata_code": r.get("code"),
                "metadata_finish_reason": r.get("finish_reason")}

    datasets = []
    walk_rows = read_jsonl(DATA / "samples_walk.jsonl") + read_jsonl(DATA / "samples_sham.jsonl") + \
        read_jsonl(DATA / "samples_fixed_top5.jsonl")
    if walk_rows:
        datasets.append({"dataset": "token_walk", "examples": [ex_walk(r) for r in walk_rows]})
    ban_rows = read_jsonl(DATA / "samples_los.jsonl") + read_jsonl(DATA / "samples_two_step.jsonl")
    if ban_rows:
        datasets.append({"dataset": "prompt_reach", "examples": [ex_ban(r) for r in ban_rows]})
    lf_rows = read_jsonl(DATA / "samples_longform.jsonl")
    if lf_rows:
        datasets.append({"dataset": "long_form", "examples": [ex_lf(r) for r in lf_rows]})
    na = json.loads((RESULTS / "novelty_audit.json").read_text()) if (RESULTS / "novelty_audit.json").exists() else {}
    if na.get("records"):
        datasets.append({"dataset": "audit", "examples": [
            {"input": r.get("code") or "", "output": str(r.get("final_class")), "metadata_task": r["task"],
             "metadata_arm": r["arm"], "metadata_sample_id": r["sample_id"], "metadata_audit_role": r["audit_role"],
             "predict_judge_a": str(r["judge_A"].get("class")), "predict_judge_b": str(r["judge_B"].get("class")),
             "metadata_manual": r.get("manual"), "metadata_neighbours_known": r.get("neighbours_known")}
            for r in na["records"]]})

    def rj(name):
        p = RESULTS / name
        return json.loads(p.read_text()) if p.exists() else None

    from commit import verify_chain
    import importlib.metadata as im

    versions = {}
    for pkg in ("vllm", "torch", "transformers", "numpy", "scipy"):
        try:
            versions[pkg] = im.version(pkg)
        except im.PackageNotFoundError:
            versions[pkg] = None
    walk = rj("walk.json") or {}
    meta = {
        "method_name": "Token-walk logit vetoes vs prompt bans vs long-form novelty instructions (Qwen3-8B)",
        "artifact_plan_id": "gen_plan_experiment_6_idx7", "utc": utc_now(), "model": "Qwen/Qwen3-8B (+ official FP8)",
        "model_revision_bf16": "b968826d9c46dd6066d109eabc6255188de91218", "versions": versions,
        "hardware_branch": "L4 23 GB (between the plan's 20 GB and >=24 GB branches); precision by family (D2)",
        "decoding": {"temperature": 1.0, "top_p": 1.0, "top_k": -1, "min_p": 0.0, "max_tokens_short": 1024,
                     "max_tokens_long": 4096, "think_cap": 16384},
        "baseline_vs_method": {"baselines": ["step 0 neutral twins (no veto) per veto arm", "prompt bans (LOS lists, "
                                             "two-step bans, exp9 TOP5/T2 LOS)", "sham n-gram veto (matched control)",
                                             "forced 'can' (capability ceiling)"],
                               "methods": ["persistent distinctive n-gram veto walk", "fixed TOP5 veto",
                                           "long-form novelty instructions (thinking off / on)"]},
        "walk": {t: {k: v for k, v in (walk.get(t) or {}).items() if k in ("status", "rungs", "deepest_rung_reached",
                                                                            "vetoed", "sham_vs_distinctive")}
                 for t in ALL_TASKS},
        "fixed_top5_T1": walk.get("fixed_top5_T1"), "c3": rj("c3.json"), "reach": rj("reach.json"),
        "list_independence": rj("list_independence.json"), "disguise": rj("disguise.json"),
        "longform": rj("longform.json"), "fp8_crosscheck": rj("fp8_crosscheck.json"),
        "novelty_audit_summary": {k: v for k, v in (na or {}).items() if k != "records"},
        "audit_controls": rj("audit_controls.json"), "can": rj("can.json"),
        "labeller_recheck": rj("labeller_recheck.json"), "veto_unit_tests": {k: rj(f"veto_unit_tests_{k}.json")
                                                                            for k in ("bf16", "fp8")},
        "inputs_check": rj("inputs_check.json"), "known_solutions": rj("known_solutions_summary.json"),
        "costs": rj("costs.json"), "longform_branch": rj("longform_branch.json"),
        "dependency_usage": rj("dependency_usage.json"), "labeller_recheck_note": "runtime vs adjudicated on gold",
        "rederive": rj("rederive.json"), "deviations": DEVIATIONS, "not_run": rj("not_run.json"),
        "commitments": verify_chain(),
        "c1_events_note": "this artifact has no C1 event types (modal, present_minor, exposure), so it writes no "
                          "results/c1_events.jsonl; per-event rows are in results/reach_events.jsonl",
        "headline_rule": "'no instruction or knob in this artifact produced a correct novel algorithm' only if the final "
                         "NOVEL count over ALL arms is 0",
        "novel_count_all_arms": len((na or {}).get("novel", [])),
    }
    out = {"metadata": meta, "datasets": datasets}
    (ROOT / "method_out.json").write_text(json.dumps(out, indent=1, default=str))
    logger.info(f"method_out.json: {sum(len(d['examples']) for d in datasets)} examples in {len(datasets)} datasets")


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("method")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "outputs"   # no argument: rebuild method_out.json from saved data
    if cmd == "s0":
        run(["src/phases.py", "s0"])
    elif cmd == "server":
        run(["src/server.py"] + sys.argv[2:])
    elif cmd == "unit":
        run(["src/phases.py", f"unit_{sys.argv[2]}"])
    elif cmd == "phase":
        run(["src/phases.py", sys.argv[2]] + sys.argv[3:])
    elif cmd == "longform":
        run(["src/longform.py"] + sys.argv[2:])
    elif cmd == "audit":
        run(["src/audit.py"] + sys.argv[2:])
    elif cmd == "analyze":
        run(["src/analysis.py"])
        run(["src/figures.py"])
        run(["src/rederive.py"])
    elif cmd == "outputs":
        assemble_outputs()
    elif cmd == "help":
        print(__doc__)
    else:
        print(__doc__)
        sys.exit(f"unknown command {cmd!r}")


if __name__ == "__main__":
    main()
