#!/usr/bin/env python3
"""CPU labelling with the canonical labeller (canon pipeline.label_rows: extract -> hidden tests + runtime probes ->
runtime/AST rules -> blind judge on disagreement only -> combine), the labeller re-check on exp1's adjudicated gold set
and 22 references (S0.4), free-form answer parsing, and the Llama label audit (second gold judge, blind).

Judge spend is capped for the whole artifact (USD 0.50 incl. the audit); before the first call the phase budget is read
from {OPENROUTER_BASE_URL}/key and the cap is lowered to a quarter of what remains when under USD 2."""

from __future__ import annotations

import argparse
import collections
import sys
import json
import os
import random
from typing import Any

import requests
from loguru import logger

from src.ws import DATA, JUDGE_TOTAL_CAP_USD, RESULTS, append_jsonl, patch_canon_caches, read_jsonl, setup_logging, write_json

patch_canon_caches()
import pipeline as P  # noqa: E402  (canon)
import labeller.judge as J  # noqa: E402
from labeller.gate import cohen_kappa  # noqa: E402
from common import GOLD_JUDGES, JUDGE_MODEL, sha256_text  # noqa: E402

from src.names import parse_free  # noqa: E402

RAW = DATA / "raw_gen.jsonl"
LABELLED = DATA / "labelled.jsonl"
FREE = DATA / "free_answers.jsonl"
AUDIT_SHARE = 0.04  # of the total cap reserved for the Llama label audit (30 gemini-flash calls ~ USD 0.01)
KEEP = ("row_id", "phase", "task", "condition", "kind", "X", "template", "paraphrase_id", "sample_id", "seed", "model",
        "decoding", "prompt_sha", "text", "finish_reason", "n_gen_tokens", "n_prompt_tokens", "gen_ids",
        "extract_method", "code", "code_sha256", "eval_key", "passed", "wall_s", "test_error", "fail_case",
        "runtime_label", "runtime_reason", "ast_label", "ast_reason", "judge_label", "judge_confidence",
        "judge_rationale", "label", "labeller_source")


def key_budget() -> dict[str, Any]:
    try:
        r = requests.get(os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/key",
                         headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}, timeout=30)
        js = r.json()
        d = js.get("data", js)
        return {"status": r.status_code, "limit": d.get("limit"), "usage": d.get("usage"),
                "limit_remaining": d.get("limit_remaining"), "raw": str(js)[:400]}
    except (requests.RequestException, ValueError, KeyError) as e:
        logger.warning(f"/key lookup failed: {e}")
        return {"status": None, "error": str(e)}


def judge_cap(purpose: str) -> float:
    """Remaining cap for `purpose` given the artifact total (judge + audit) and the phase budget."""
    kb_path = RESULTS / "openrouter_key_budget.json"
    if not kb_path.exists():
        kb = key_budget()
        write_json(kb_path, kb)
        logger.info(f"OpenRouter phase budget: {kb}")
    kb = json.loads(kb_path.read_text())
    total = JUDGE_TOTAL_CAP_USD
    rem = kb.get("limit_remaining")
    if isinstance(rem, (int, float)) and rem < 2.0:
        total = min(total, rem / 4.0)
        logger.warning(f"phase budget remaining {rem:.2f} < 2 USD: total judge cap lowered to {total:.3f}")
    audit = total * AUDIT_SHARE
    return audit if purpose == "llama_audit" else total - audit


def label_new(use_judge: bool = True, phases: list[str] | None = None) -> list[dict[str, Any]]:
    raw = read_jsonl(RAW)
    done = {r["row_id"] for r in read_jsonl(LABELLED)} | {r["row_id"] for r in read_jsonl(FREE)}
    todo = [r for r in raw if r["row_id"] not in done and (phases is None or r["phase"] in phases)]
    free = [r for r in todo if r["kind"] == "free"]
    progs = [r for r in todo if r["kind"] != "free"]
    if free:
        rows = []
        for r in free:
            rr = {k: r.get(k) for k in ("row_id", "phase", "task", "condition", "X", "sample_id", "seed", "model",
                                        "decoding", "text", "finish_reason", "n_gen_tokens")}
            rr["label"] = parse_free(r["text"], r["task"], r["X"])
            rows.append(rr)
        append_jsonl(FREE, rows)
        logger.info(f"free-form: {len(rows)} answers parsed; labels {collections.Counter(r['label'] for r in rows)}")
    if not progs:
        return []
    cap = judge_cap("judge")
    logger.info(f"labelling {len(progs)} programs (judge={use_judge}, cap {cap:.3f} USD, spent "
                f"{J.purpose_spent('judge'):.4f})")
    lab = P.label_rows(progs, judge_cap=cap, use_judge=use_judge)
    out = [{k: r.get(k) for k in KEEP} for r in lab]
    append_jsonl(LABELLED, out)
    c = collections.Counter((r["task"], r["kind"], r["label"]) for r in out)
    logger.info(f"labelled {len(out)}: sources {collections.Counter(r['labeller_source'] for r in out)}")
    for k in sorted(c):
        logger.debug(f"{k}: {c[k]}")
    return out


# ------------------------------------------------------------------------------------------------ S0.4 re-check
def recheck() -> dict[str, Any]:
    from tasks.harness import parallel_map, run_probes

    tasks = ("t1", "t2")
    ref_ok = {}
    for task in tasks:
        refs = P.references(task)
        trs = parallel_map(lambda r: {"probes": run_probes(task, r["code"])}, refs, workers=8, desc=f"refs {task}")
        for r, tr in zip(refs, trs):
            mk = P.mechanical_labels(task, r["code"], tr)
            ref_ok[f"{task}/{r['file']}"] = {"mode": r["mode"], "runtime": mk["runtime_label"], "ast": mk["ast_label"],
                                             "ok": mk["runtime_label"] == r["mode"] == mk["ast_label"]}
    gold = read_jsonl(P.ROOT / "labeller" / "gold_set.jsonl")
    progs = [{"task": g["task"], "code": g["code"], "key": f"{g['task']}|{sha256_text(g['code'])}"} for g in gold]
    uniq = {p["key"]: p for p in progs}
    cache = P.evaluate_unique(list(uniq.values()), workers=10)
    rows = []
    for g, p in zip(gold, progs):
        mk = P.mechanical_labels(g["task"], g["code"], cache[p["key"]])
        rl, al = mk["runtime_label"], mk["ast_label"]
        agree = rl == al and rl not in ("unknown", "inconsistent")
        comb = rl if agree else (g.get("judge_a") or "other")  # judge_a = production judge (stored, no new call)
        rows.append({"task": g["task"], "split": g["split"], "adjudicated": g["adjudicated"], "runtime": rl, "ast": al,
                     "combined": comb, "stored_runtime": g["runtime_label"], "stored_ast": g["ast_label"],
                     "passed_now": cache[p["key"]]["passed"], "passed_stored": g["passed"]})

    def metrics(rs: list[dict[str, Any]]) -> dict[str, Any]:
        res = [r for r in rs if r["adjudicated"] != "unresolved"]
        n = max(1, len(res))
        return {"n": len(rs), "n_resolved": len(res),
                "acc_combined_vs_adjudicated": sum(r["combined"] == r["adjudicated"] for r in res) / n,
                "acc_runtime_vs_adjudicated": sum(r["runtime"] == r["adjudicated"] for r in res) / n,
                "acc_ast_vs_adjudicated": sum(r["ast"] == r["adjudicated"] for r in res) / n,
                "kappa_runtime_ast": cohen_kappa([r["runtime"] for r in res], [r["ast"] for r in res]),
                "runtime_reproduces_stored": sum(r["runtime"] == r["stored_runtime"] for r in rs) / max(1, len(rs)),
                "ast_reproduces_stored": sum(r["ast"] == r["stored_ast"] for r in rs) / max(1, len(rs)),
                "pass_reproduces_stored": sum(r["passed_now"] == r["passed_stored"] for r in rs) / max(1, len(rs))}

    out = {"references_ok": sum(v["ok"] for v in ref_ok.values()), "references_n": len(ref_ok),
           "references_100pct": all(v["ok"] for v in ref_ok.values()), "references": ref_ok,
           "gold_all": metrics(rows), "gold_eval": metrics([r for r in rows if r["split"] == "eval"]),
           "gold_dev": metrics([r for r in rows if r["split"] == "dev"]),
           "per_task_eval": {t: metrics([r for r in rows if r["split"] == "eval" and r["task"] == t]) for t in tasks},
           "pass_threshold_combined": 0.9,
           "note": "combined label = runtime if runtime == AST (resolved) else the stored production-judge label "
                   "(judge_a, gpt-4.1-mini) -- no new judge calls; canon labeller unchanged."}
    out["passed"] = bool(out["references_100pct"] and out["gold_eval"]["acc_combined_vs_adjudicated"] >= 0.9)
    write_json(RESULTS / "labeller_recheck.json", out)
    logger.info(f"labeller re-check: refs {out['references_ok']}/{out['references_n']}, gold eval combined "
                f"{out['gold_eval']['acc_combined_vs_adjudicated']:.3f}, kappa {out['gold_eval']['kappa_runtime_ast']:.3f}"
                f", passed={out['passed']}")
    return out


# ------------------------------------------------------------------------------------------------ Llama audit
def llama_audit(n_total: int = 30) -> dict[str, Any]:
    """30 Llama programs stratified by combined label (5 per T1 label present, the rest from T2), judged blind by the
    second gold judge (gemini-2.5-flash)."""
    rows = [r for r in read_jsonl(LABELLED) if r.get("code")]
    rng = random.Random(20261020)
    uniq: dict[str, dict[str, Any]] = {}
    for r in rows:
        uniq.setdefault(r["eval_key"], r)
    by = collections.defaultdict(list)
    for r in uniq.values():
        by[(r["task"], r["label"])].append(r)
    picks = []
    for (task, lbl) in sorted(k for k in by if k[0] == "t1"):
        pool = by[(task, lbl)]
        rng.shuffle(pool)
        picks += pool[:5]
    t2_labels = sorted(k for k in by if k[0] == "t2")
    i = 0
    t2_pools = {k: rng.sample(by[k], len(by[k])) for k in t2_labels}
    while len(picks) < n_total and any(t2_pools.values()):
        k = t2_labels[i % len(t2_labels)]
        if t2_pools[k]:
            picks.append(t2_pools[k].pop())
        i += 1
    picks = picks[:n_total] if len(picks) > n_total else picks
    cap = judge_cap("llama_audit")
    js, stop = J.judge_many([{"task": p["task"], "code": p["code"]} for p in picks], GOLD_JUDGES[1], "llama_audit", cap)
    pairs = [{"task": p["task"], "row_id": p["row_id"], "combined": p["label"], "source": p["labeller_source"],
              "audit_judge": j["label"] if j else None, "audit_rationale": j["rationale"] if j else None}
             for p, j in zip(picks, js)]
    judged = [q for q in pairs if q["audit_judge"]]
    agree = sum(q["combined"] == q["audit_judge"] for q in judged)
    out = {"n": len(pairs), "n_judged": len(judged), "agreement": agree / max(1, len(judged)),
           "judge_model": GOLD_JUDGES[1], "stop": stop, "pairs": pairs,
           "by_label": {f"{t}:{l}": sum(1 for q in pairs if q["task"] == t and q["combined"] == l)
                        for (t, l) in sorted({(q["task"], q["combined"]) for q in pairs})},
           "disputed_row_ids": [q["row_id"] for q in judged if q["combined"] != q["audit_judge"]],
           "flag_below_0.9": agree / max(1, len(judged)) < 0.9}
    write_json(RESULTS / "llama_label_audit.json", out)
    logger.info(f"Llama label audit: {agree}/{len(judged)} agree ({out['agreement']:.3f})")
    return out


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["recheck", "label", "audit", "audit2"])
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--phases", default=None)
    a = ap.parse_args()
    setup_logging(f"label_{a.cmd}")
    if a.cmd == "recheck":
        recheck()
    elif a.cmd == "label":
        label_new(use_judge=not a.no_judge, phases=a.phases.split(",") if a.phases else None)
    elif a.cmd == "audit":
        llama_audit()
    else:
        llama_audit_supplement()
    _ = JUDGE_MODEL



def llama_audit_supplement(n_t2: int = 15, n_t1_other: int = 5) -> dict[str, Any]:
    """Supplement: the first audit draw filled all 30 slots with T1 catalogue labels (7 T1 labels present x 5 > 30), so
    T2 and T1 'other' were unaudited. Adds n_t1_other T1 'other' programs and n_t2 T2 programs stratified round-robin by
    label (same blind judge, same seed rule), then recomputes agreement overall and per task."""
    first = json.loads((RESULTS / "llama_label_audit.json").read_text())
    seen = {p["row_id"] for p in first["pairs"]}
    rows = [r for r in read_jsonl(LABELLED) if r.get("code") and r["row_id"] not in seen]
    rng = random.Random(20261021)
    uniq: dict[str, dict[str, Any]] = {}
    for r in rows:
        uniq.setdefault(r["eval_key"], r)
    by = collections.defaultdict(list)
    for r in uniq.values():
        by[(r["task"], r["label"])].append(r)
    picks = rng.sample(by[("t1", "other")], min(n_t1_other, len(by[("t1", "other")])))
    t2_labels = sorted(k for k in by if k[0] == "t2")
    pools = {k: rng.sample(by[k], len(by[k])) for k in t2_labels}
    i, t2 = 0, []
    while len(t2) < n_t2 and any(pools.values()):
        k = t2_labels[i % len(t2_labels)]
        if pools[k]:
            t2.append(pools[k].pop())
        i += 1
    picks += t2
    cap = max(0.0, JUDGE_TOTAL_CAP_USD - J.load_cost()["total_usd"])
    js, stop = J.judge_many([{"task": p["task"], "code": p["code"]} for p in picks], GOLD_JUDGES[1], "llama_audit",
                            J.purpose_spent("llama_audit") + cap)
    pairs = first["pairs"] + [{"task": p["task"], "row_id": p["row_id"], "combined": p["label"],
                               "source": p["labeller_source"], "audit_judge": j["label"] if j else None,
                               "audit_rationale": j["rationale"] if j else None, "supplement": True}
                              for p, j in zip(picks, js)]
    judged = [q for q in pairs if q["audit_judge"]]

    def agr(qs: list[dict[str, Any]]) -> float | None:
        return sum(q["combined"] == q["audit_judge"] for q in qs) / len(qs) if qs else None

    out = dict(first)
    out.update({"n": len(pairs), "n_judged": len(judged), "agreement": agr(judged), "pairs": pairs, "stop_supplement": stop,
                "agreement_per_task": {t: agr([q for q in judged if q["task"] == t]) for t in ("t1", "t2")},
                "agreement_first_draw": first["agreement"],
                "by_label": {f"{t}:{l}": sum(1 for q in pairs if q["task"] == t and q["combined"] == l)
                             for (t, l) in sorted({(q["task"], q["combined"]) for q in pairs})},
                "disputed_row_ids": [q["row_id"] for q in judged if q["combined"] != q["audit_judge"]],
                "flag_below_0.9": (agr(judged) or 0) < 0.9,
                "note": "first draw (30) filled with T1 catalogue labels only; supplement adds T1 'other' and T2"})
    write_json(RESULTS / "llama_label_audit.json", out)
    logger.info(f"audit supplement: overall {out['agreement']:.3f}, per task {out['agreement_per_task']}")
    return out



if __name__ == "__main__":
    main()
