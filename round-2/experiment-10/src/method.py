#!/usr/bin/env python3
"""Llama-3.1-8B-Instruct replication of the FRLP / C1 ban-substitution screen -- orchestrator.

Stages (run in this order; see README.md / reproducibility.md):
  setup        verify the canon copy (canon/SHA256SUMS), extract the noun bank, write results/frozen_config.json
  recheck      S0.4 labeller re-check on exp1's adjudicated gold set + 22 references
  gen PHASE    S1/S4 vLLM generation against a running `scripts/serve_vllm.sh` (A1..A6, C)
  label        CPU labelling with the canonical labeller (judge on disagreement only, capped)
  audit        Llama label audit (second gold judge) + supplement
  forced       S2 forced set, name scrub, validation, coverage, T3 token check
  score PHASE  S3/S5 HF scoring sessions (B: proposal + baselines + T3/T4; D: matrices, edits, route)
  commit       S0.9 hash-chained commitments
  analyse      S6 analysis (src/run_analysis.py, frozen)
  figures      S6.13 figures
  rederive     T11 independent re-derivation (audit/rederive.py)
  outputs      S7 data/samples.jsonl, method_out.json (+ full/mini/preview)

The METHOD is the FRLP instrument (forced-ratio latent probability, scored by HF on name-scrubbed self-written programs)
and the C1 decomposition of single-ban gains into an X-specific and a ladder component; the BASELINES it is compared
with, per sampled program, are the typicality ladder (survivors ranked by their unbanned baseline FRLP) and the
free-form association answer ('What is the standard alternative to X?').
"""

from __future__ import annotations

import argparse
import collections
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from loguru import logger

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.ws import C, DATA, FRLP_DIR, RESULTS, read_jsonl, setup_logging, write_json  # noqa: E402

PY = sys.executable


def run(mod: str, *args: str) -> int:
    cmd = [PY, "-W", "ignore", "-m", mod, *args]
    logger.info(f"$ {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=ROOT)


# ------------------------------------------------------------------------------------------------ outputs
def samples_jsonl() -> list[dict[str, Any]]:
    keys = ("task", "condition", "kind", "X", "template", "paraphrase_id", "sample_id", "seed", "model", "decoding",
            "label", "labeller_source", "passed", "code_sha256", "code", "text", "n_gen_tokens", "finish_reason",
            "extract_method", "runtime_label", "ast_label", "judge_label", "phase", "row_id", "prompt_sha")
    rows = [{k: r.get(k) for k in keys} for r in read_jsonl(DATA / "labelled.jsonl")]
    C.write_jsonl(DATA / "samples.jsonl", rows)
    return rows


def predictions(tds: dict[str, Any], views: dict[str, Any], sel: dict[str, Any], assoc: dict[str, Any]):
    import numpy as np

    def frlp_top1(task: str, cond: str, banned: list[str]) -> str:
        v = views[task]
        Se = [j for j in v.td.algs if j not in banned]
        L = v.a(cond, Se)
        return Se[int(np.nanargmax(L))] if Se and not np.all(np.isnan(L)) else "none"

    def ladder(task: str, banned: list[str]) -> str:
        v = views[task]
        Se = [j for j in v.td.algs if j not in banned]
        L = np.nanmean([v.a(f"baseline:s{s}", Se) for s in range(5)], axis=0)
        return Se[int(np.nanargmax(L))] if Se else "none"

    base_counts = {t: collections.Counter(r["label"] for r in read_jsonl(DATA / "labelled.jsonl")
                                          if r["task"] == t and r["kind"] == "baseline") for t in views}

    def sampled_ladder(task: str, banned: list[str]) -> str:
        """Empirical typicality ladder: sampled baseline frequency renormalised over the survivors (catalogue order on ties)."""
        Se = [j for j in views[task].td.algs if j not in banned]
        return max(Se, key=lambda j: (base_counts[task].get(j, 0), -Se.index(j))) if Se else "none"

    def association(task: str, X: str | None, banned: list[str]) -> str:
        if X is None:
            return ladder(task, banned)
        cnt = assoc[task].get(X, {})
        Se = [j for j in views[task].td.algs if j not in banned]
        best = max(Se, key=lambda j: (cnt.get(j, 0), -Se.index(j))) if Se else "none"
        return best if cnt.get(best, 0) > 0 else ladder(task, banned)

    return frlp_top1, ladder, association, sampled_ladder


def banned_for(r: dict[str, Any], sel: dict[str, Any]) -> list[str]:
    if r["kind"] == "ban":
        return [r["X"]]
    if r["kind"] == "twostep":
        return r["X"].split("+")
    return []


def outputs() -> None:
    import numpy as np

    from src import analysis_c1 as A
    from src import run_analysis as RA

    rows = samples_jsonl()
    sel = json.loads((RESULTS / "selections.json").read_text())
    tds = {t: RA.load_task(t) for t in RA.TASKS}
    views = {t: A.View(td, RA.variant_cells(td, "full")) for t, td in tds.items()}
    assoc = RA.association(sel)
    frlp_top1, ladder, association, sampled_ladder = predictions(tds, views, sel, assoc)
    datasets = []
    acc = collections.defaultdict(lambda: collections.Counter())
    for task in RA.TASKS:
        ex = []
        for r in rows:
            if r["task"] != task or r["phase"] not in ("A1", "A4", "A5", "C"):
                continue
            banned = banned_for(r, sel)
            X = r["X"] if r["kind"] in ("ban",) else (sel[f"{task}_default"] if r["kind"] == "twostep" else None)
            p_frlp = frlp_top1(task, r["condition"], banned)
            p_lad = ladder(task, banned)
            p_ass = association(task, X, banned)
            p_smp = sampled_ladder(task, banned)
            lab = r["label"]
            scorable = lab not in ("no_code",) and lab not in banned
            if scorable:
                ev = f"{task}|{r['kind']}|{r['X']}"
                acc[ev]["n"] += 1
                acc[ev]["frlp"] += int(p_frlp == lab)
                acc[ev]["ladder"] += int(p_lad == lab)
                acc[ev]["association"] += int(p_ass == lab)
                acc[ev]["sampled_ladder"] += int(p_smp == lab)
            ex.append({"input": f"task={task} | condition={r['condition']} | prompt_sha256={r['prompt_sha']}",
                       "output": str(lab),
                       "predict_frlp_top1": p_frlp, "predict_latent_ladder": p_lad, "predict_sampled_ladder": p_smp,
                       "predict_association": p_ass,
                       "metadata_task": task, "metadata_kind": r["kind"], "metadata_banned": banned,
                       "metadata_template": r["template"], "metadata_paraphrase_id": r["paraphrase_id"],
                       "metadata_sample_id": r["sample_id"], "metadata_seed": r["seed"], "metadata_passed": r["passed"],
                       "metadata_labeller_source": r["labeller_source"], "metadata_code_sha256": r["code_sha256"],
                       "metadata_phase": r["phase"], "metadata_row_id": r["row_id"], "metadata_scorable": scorable,
                       "metadata_n_gen_tokens": r["n_gen_tokens"], "metadata_finish_reason": r["finish_reason"]})
        datasets.append({"dataset": f"{C.TASK_DATASET_NAME[task]}__llama31_sampled", "examples": ex})
    # forced programs (FRLP proposal set) and free-form association answers
    fs = {r["row_id"]: r for r in read_jsonl(DATA / "forced_set.jsonl")}
    fex = []
    for r in rows:
        if r["phase"] not in ("A2", "A6"):
            continue
        f = fs.get(r["row_id"])
        fex.append({"input": f"task={r['task']} | condition={r['condition']} | prompt_sha256={r['prompt_sha']}",
                    "output": str(r["label"]), "predict_intended_algorithm": str(r["X"]),
                    "metadata_task": r["task"], "metadata_in_frlp_set": f is not None,
                    "metadata_half": f["half"] if f else None, "metadata_scrub_mode": f["scrub_mode"] if f else None,
                    "metadata_passed": r["passed"], "metadata_labeller_source": r["labeller_source"],
                    "metadata_code_sha256": r["code_sha256"], "metadata_row_id": r["row_id"]})
    datasets.append({"dataset": "forced_programs__llama31", "examples": fex})
    fr = read_jsonl(DATA / "free_answers.jsonl")
    ext = (load(RESULTS / "sensitivities.json") or {}).get("freeform_vs_exp1_openrouter_llama", {})
    datasets.append({"dataset": "freeform_association__llama31", "examples": [
        {"input": f"task={r['task']} | free-form 'standard alternative to {r['X']}'", "output": r["label"],
         "predict_exp1_openrouter_llama_top1": str((ext.get(r["task"], {}).get(r["X"], {}) or {}).get("exp1_openrouter_top1")),
         "metadata_task": r["task"], "metadata_X": r["X"], "metadata_raw_answer": r["text"],
         "metadata_sample_id": r["sample_id"], "metadata_seed": r["seed"]} for r in fr]})
    pred_summary = {ev: {"n": c["n"], "acc_frlp_top1": c["frlp"] / max(1, c["n"]), "acc_latent_ladder": c["ladder"] / max(1, c["n"]),
                         "acc_sampled_ladder": c["sampled_ladder"] / max(1, c["n"]),
                         "acc_association": c["association"] / max(1, c["n"])} for ev, c in sorted(acc.items())}
    tot = collections.Counter()
    for c in acc.values():
        tot.update(c)
    pred_summary["ALL"] = {"n": tot["n"], "acc_frlp_top1": tot["frlp"] / max(1, tot["n"]),
                           "acc_latent_ladder": tot["ladder"] / max(1, tot["n"]),
                           "acc_sampled_ladder": tot["sampled_ladder"] / max(1, tot["n"]),
                           "acc_association": tot["association"] / max(1, tot["n"])}
    bans = [c for ev, c in acc.items() if "|ban|" in ev]
    bt = collections.Counter()
    for c in bans:
        bt.update(c)
    pred_summary["SINGLE_BANS"] = {"n": bt["n"], "acc_frlp_top1": bt["frlp"] / max(1, bt["n"]),
                                   "acc_latent_ladder": bt["ladder"] / max(1, bt["n"]),
                                   "acc_sampled_ladder": bt["sampled_ladder"] / max(1, bt["n"]),
                                   "acc_association": bt["association"] / max(1, bt["n"])}
    pred_summary["_definitions"] = {
        "predict_frlp_top1 (method)": "argmax over non-banned FRLP-measured algorithms of L_j(sample's prompt)",
        "predict_latent_ladder (baseline 1)": "argmax over survivors of the mean baseline FRLP (latent typicality ladder)",
        "predict_sampled_ladder (baseline 2)": "argmax over survivors of the sampled baseline frequency (empirical typicality ladder)",
        "predict_association (baseline 3)": "the free-form 'standard alternative to X' modal answer among survivors (latent ladder when X is absent)",
        "scored samples": "attempted (code extracted), label not banned; accuracy = top-1 equals the mechanism label"}
    meta = build_metadata(pred_summary)
    out = {"metadata": meta, "datasets": datasets}
    (ROOT / "method_out.json").write_text(json.dumps(A.jsonable(out), indent=1, ensure_ascii=False))
    logger.info(f"method_out.json: {sum(len(d['examples']) for d in datasets)} examples in {len(datasets)} datasets")
    _ = np, time


def load(p: Path) -> Any:
    return json.loads(p.read_text()) if p.exists() else None


def build_metadata(pred_summary: dict[str, Any]) -> dict[str, Any]:
    c1 = load(RESULTS / "c1.json") or {}
    cost = load(RESULTS / "openrouter_cost.json") or {}
    timing = [json.loads(x) for x in (ROOT / "logs" / "timing.jsonl").read_text().splitlines() if x.strip()]
    gpu_s = sum(r["seconds"] for r in timing)
    return {
        "method_name": "FRLP + C1 share test, Llama-3.1-8B-Instruct replication (iteration 2, artifact 5)",
        "description": ("Second-family replication of the screen: forced-ratio latent probability (FRLP) of every catalogue "
                        "algorithm under single bans, mention/neutral twins, nonce ban, random edits and novelty, and the "
                        "C1 split of ban-induced gains into an X-specific and an external-ladder component."),
        "model_record": load(RESULTS / "model_record.json"),
        "frozen_config_sha256": C.sha256_file(RESULTS / "frozen_config.json"),
        "commitments": read_jsonl(ROOT / "commitments.log"),
        "labeller_recheck": {k: v for k, v in (load(RESULTS / "labeller_recheck.json") or {}).items() if k != "references"},
        "llama_label_audit": {k: v for k, v in (load(RESULTS / "llama_label_audit.json") or {}).items() if k != "pairs"},
        "collapse": load(RESULTS / "collapse.json"),
        "events": load(RESULTS / "events.json"),
        "frlp_gate": load(RESULTS / "frlp_gate.json"),
        "forced_set": load(RESULTS / "forced_set_summary.json"),
        "c1": {"branches": c1.get("branches"), "pooled_neutral": (c1.get("c1") or {}).get("neutral", {}).get("pooled"),
               "pooled_mention": (c1.get("c1") or {}).get("mention", {}).get("pooled"),
               "aim_nulls": c1.get("aim_nulls"), "ladder": c1.get("ladder"), "cosine": c1.get("cosine"),
               "route": c1.get("route"), "association_counts": c1.get("association_counts"), "B": c1.get("B")},
        "sensitivities": load(RESULTS / "sensitivities.json"),
        "bootstrap_diagnostics_post_hoc": load(RESULTS / "bootstrap_diagnostics.json"),
        "coverage_forced_vs_natural": load(RESULTS / "coverage.json"),
        "dependency_datasets_inventory": load(DATA / "dependency_inventory.json"),
        "tests": {"T1_labeller": "results/labeller_recheck.json", "T2_prompts": load(RESULTS / "tests_prompts.json"),
                  "T3_T4": load(RESULTS / "tests_scoring_B.json"), "T3_tokens": load(RESULTS / "t3_token_check.json"),
                  "T5b_scrub_stress_all_10_datasets": load(RESULTS / "scrub_stress.json"),
                  "T6_frlp_sanity": {k: v for k, v in (load(RESULTS / "tests_frlp_sanity.json") or {}).items() if k != "own_forced"},
                  "T7_T8": load(RESULTS / "tests_scoring_D.json"), "T9": load(RESULTS / "test_analysis_c1.json"),
                  "T11": {k: v for k, v in (load(RESULTS / "independent_rederivation.json") or {}).items() if k != "checks"},
                  "T11b_headlines": {k: v for k, v in (load(RESULTS / "independent_rederivation_headlines.json") or {}).items()
                                     if k != "checks"}},
        "predictor_comparison_per_event": pred_summary,
        "timing": {"gpu_seconds_logged": round(gpu_s, 1), "gpu_hours_logged": round(gpu_s / 3600, 3)},
        "openrouter_spend_usd": cost.get("total_usd"), "openrouter_spend_by_purpose": cost.get("by_purpose"),
        "qwen_reference": None,
        "deviations": load(RESULTS / "deviations.json"),
    }


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage")
    ap.add_argument("arg", nargs="?")
    a = ap.parse_args()
    setup_logging("method")
    s = a.stage
    if s == "setup":
        subprocess.call(["sha256sum", "-c", "--quiet", "SHA256SUMS"], cwd=ROOT / "canon")
        subprocess.call([sys.executable, "-I", "scripts/extract_dependency.py"], cwd=ROOT)
        run("src.commit", "setup-only", "results/frozen_config.json") if False else None
    elif s == "recheck":
        run("src.label_worker", "recheck")
    elif s == "gen":
        run("src.gen_client", "--phase", a.arg)
    elif s == "label":
        run("src.label_worker", "label", *(["--phases", a.arg] if a.arg else []))
    elif s == "audit":
        run("src.label_worker", "audit")
        run("src.label_worker", "audit2")
    elif s == "forced":
        run("src.forced_set")
    elif s == "score":
        run("src.score_session", "--phase", a.arg)
    elif s == "commit":
        run("src.commit", a.arg or "freeze: S0.9 before the first S5 score")
    elif s == "test9":
        run("src.test_analysis_c1")
    elif s == "analyse":
        run("src.run_analysis")
    elif s == "figures":
        run("src.figures")
    elif s == "rederive":
        subprocess.call([PY, "audit/rederive.py"], cwd=ROOT)
    elif s == "outputs":
        outputs()
    else:
        raise SystemExit(f"unknown stage {s}")


if __name__ == "__main__":
    main()
