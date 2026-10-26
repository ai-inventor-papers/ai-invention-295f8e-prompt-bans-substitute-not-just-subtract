#!/usr/bin/env python3
"""Post-sampling stages: novelty audit + style re-gate (OpenRouter), positioning record, analysis (analysis8 +
engine check + diagnostics), figures F1-F6 (PNG + PDF, geometry in actual block-17 activation coordinates),
data/samples.jsonl and method_out.json (exp_gen_sol_out)."""

from __future__ import annotations

import json
import os
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

import cfg8 as C8
from cfg import (BUDGET_MSG, DATA_DIR, FIG_DIR, IT_ID, LOG_DIR, PRED_DIR, RESULTS_DIR, ROOT, TEMPLATE_IDS, add_deviation,
                 append_jsonl, read_json, read_jsonl, sha256_text, utc_now, write_json, write_jsonl)

CELL_ORDER = ["P-twin", "P-DAS-bfs", "P-DAS-dfs", "G1a", "G1b", "G1c", "G1d", "F-twin", "F-DAS-r4-bfs-1.0",
              "F-DAS-r4-bfs-0.5", "F-DAS-r1-bfs-1.0", "F-DAS-r1-bfs-0.5", "F-DiM-bfs", "F-DAS-r4-dfs-1.0", "F-DiM-dfs",
              "F-RAND-r4-1.0", "F-DAS-s2-r4-bfs-1.0", "REV-DAS", "REV-FULL"]
CELL_DESC = {
    "P-twin": "twin prompt + c* prefilled, no edit", "P-DAS-bfs": "twin + c*, DAS r4 lam 1 toward BFS at p_f",
    "P-DAS-dfs": "twin + c*, DAS r4 lam 1 toward DFS at p_f", "G1a": "forced-BFS prompt F5 + c* prefilled",
    "G1b": "forced-DFS prompt F5 + c* prefilled", "G1c": "forced-BFS prompt F5, free from index 0",
    "G1d": "best TF-predicted forced-BFS wording (F1-F4) + c* prefilled",
    "F-twin": "twin prompt, free from index 0, no edit",
    "F-DAS-r4-bfs-1.0": "twin, free, DAS r4 lam 1 toward BFS at the decision position",
    "F-DAS-r4-bfs-0.5": "twin, free, DAS r4 lam 0.5 toward BFS", "F-DAS-r1-bfs-1.0": "twin, free, DAS r1 lam 1 toward BFS",
    "F-DAS-r1-bfs-0.5": "twin, free, DAS r1 lam 0.5 toward BFS", "F-DiM-bfs": "twin, free, DiM (matched) toward BFS",
    "F-DAS-r4-dfs-1.0": "twin, free, DAS r4 lam 1 toward DFS", "F-DiM-dfs": "twin, free, DiM (matched) toward DFS",
    "F-RAND-r4-1.0": "twin, free, random rank-4 subspace, lam 1", "F-DAS-s2-r4-bfs-1.0": "twin, free, DAS seed 2 r4 lam 1",
    "REV-DAS": "forced-BFS F5 + c*, rank-4 reverse interchange <- twin state", "REV-FULL": "forced-BFS F5 + c*, full block-17 p_f state <- twin state"}


# ================================================================================================ loading
def load_labels() -> list[dict[str, Any]]:
    lab = read_jsonl(DATA_DIR / "labels.jsonl")
    seen: dict[str, dict[str, Any]] = {}
    for r in lab:
        seen[r["row_id"]] = r                      # last label wins (the worker never relabels; safety)
    pc = {r["row_id"]: r for r in read_jsonl(DATA_DIR / "prefix_check.jsonl")}
    out = []
    for r in seen.values():
        if r["row_id"] in pc:
            r = dict(r, prefix_match=pc[r["row_id"]]["prefix_match"], identical_to_ftwin=pc[r["row_id"]]["identical_to_ftwin"])
        out.append(r)
    return out


def load_raw() -> dict[str, dict[str, Any]]:
    out = {}
    for f in sorted(DATA_DIR.glob("raw_*.jsonl")):
        for r in read_jsonl(f):
            out[r["row_id"]] = r
    return out


# ================================================================================================ novelty
_LOCK = threading.Lock()
_STATE = {"stop": False, "spent": 0.0}
SPEND = LOG_DIR / "openrouter_spend_novelty.jsonl"


def spent_total() -> float:
    tot = 0.0
    for f in LOG_DIR.glob("openrouter_spend*.jsonl"):
        tot += sum(float(r.get("cost") or 0.0) for r in read_jsonl(f))
    jp = RESULTS_DIR / "openrouter_cost_paths.json"
    if jp.exists():
        try:
            tot += float(read_json(jp).get("total_usd", 0.0))
        except (ValueError, TypeError, AttributeError):
            pass
    return tot


def call(model: str, prompt: str, purpose: str, max_tokens: int = 300) -> str | None:
    from openai import OpenAI, PermissionDeniedError

    with _LOCK:
        if _STATE["stop"] or spent_total() > C8.OPENROUTER_CAP_USD:
            _STATE["stop"] = True
            return None
    cli = OpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"], timeout=90,
                 max_retries=2)
    try:
        r = cli.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}], temperature=0,
                                        max_tokens=max_tokens, extra_body={"usage": {"include": True}})
    except PermissionDeniedError as e:
        if BUDGET_MSG in str(e):
            with _LOCK:
                _STATE["stop"] = True
            logger.error("OpenRouter budget refusal: stopping every remaining call")
            return None
        raise
    cost = 0.0
    u = getattr(r, "usage", None)
    if u is not None:
        cost = float(getattr(u, "cost", None) or (getattr(u, "model_extra", None) or {}).get("cost", 0.0) or 0.0)
    text = r.choices[0].message.content or ""
    append_jsonl(SPEND, [{"utc": utc_now(), "model": model, "purpose": purpose, "cost": cost,
                          "prompt_head": prompt[:200], "response": text[:400]}])
    logger.debug(f"{model} [{purpose}] {cost:.5f} USD -> {text[:120]!r}")
    return text


LABEL_PROMPT = """You are classifying a Python program that solves this task: find a path between two cells of a grid
(4-neighbour moves, walls '#'), returning a list of cells from start to goal or [] if none.

Which search algorithm does the program implement? Answer with exactly one word from:
BFS, DFS, BIDIRECTIONAL_BFS, IDDFS, ASTAR_OR_GREEDY, DIJKSTRA, OTHER.
(DFS includes recursive or explicit-stack depth-first search; BFS includes FIFO-queue search with a deque or a list.)

Program:
```python
{code}
```
Answer:"""


def _parse_label(t: str | None) -> str | None:
    if not t:
        return None
    t = t.strip().upper()
    for k, v in (("BIDIRECTIONAL", "bibfs"), ("IDDFS", "iddfs"), ("ASTAR", "astar_gbfs"), ("GREEDY", "astar_gbfs"),
                 ("DIJKSTRA", "dijkstra"), ("BFS", "bfs"), ("DFS", "dfs"), ("OTHER", "other")):
        if k in t.split()[0] if t.split() else False:
            return v
    return None


def stage_novelty(args: Any) -> None:
    """(1) rebuild the known-solution pool (fix: TheAlgorithms code sits in `input`); (2) every CORRECT 'other'
    program -> two blind judges of different families + nearest known solutions (none expected); (3) style re-gate
    of 30 stratified programs by one blind judge against the frozen labeller."""
    import difflib
    import random

    labels = load_labels()
    # (1) pool rebuild over all 10 datasets of the dependency
    import method as M

    dep = json.loads((M.ART_DEP / "full_data_out.json").read_text())
    pool = []
    import re

    gre = re.compile(r"\b(bfs|dfs|breadth|depth|deque|queue|visited|dijkstra|heapq|astar|shortest|grid|path|maze)\b", re.I)
    usage = {}
    for ds in dep["datasets"]:
        nm = ds["dataset"]
        n_code = 0
        for i, e in enumerate(ds["examples"]):
            inp, out = str(e.get("input") or ""), str(e.get("output") or "")
            code = inp if nm == "thealgorithms_python" else out
            if nm in ("llm_creativity", "concreteness_norms", "clrs_text") or not ("def " in code or "class " in code):
                continue
            n_code += 1
            if gre.search(code[:6000]) or gre.search(inp[:3000]):
                pool.append({"source": nm, "idx": i, "code": code[:6000]})
        usage[nm] = {"n_examples": len(ds["examples"]), "n_code": n_code}
    del dep
    write_json(ROOT / "cache" / "known_pool.json", {"n": len(pool), "rows": pool})
    add_deviation("D-pool", "s0's known-solution pool missed TheAlgorithms (its code sits in `input`); rebuilt in the "
                            f"novelty stage: {len(pool)} graph/grid/path-related code examples from 7 code-bearing "
                            "datasets (no committed statistic depends on the pool).")
    # (2) correct 'other' programs
    correct = [r for r in labels if r.get("passed")]
    other = [r for r in correct if r.get("label") == "other"]
    items = []
    for r in other:
        sims = sorted(pool, key=lambda p: -difflib.SequenceMatcher(None, r["code"][:3000], p["code"][:3000]).ratio())[:3]
        items.append({"row_id": r["row_id"], "cell": r.get("cell"), "nearest": [{"source": s["source"], "idx": s["idx"]}
                                                                             for s in sims]})
    n_corr = len(correct)
    res = {"n_correct_programs_all_cells": n_corr, "n_correct_other": len(other), "items": items,
           "judges": ["deepseek/deepseek-chat-v3.1", "google/gemini-2.5-flash-lite"],
           "novel_claim": (f"none (count 0; rule-of-three upper bound 3/n = {3 / max(n_corr, 1):.4f} over {n_corr} "
                           "correct programs)") if not other else "see items (judged)",
           "pool": {"n": len(pool), "usage": usage}}
    if other:
        logger.warning(f"{len(other)} correct 'other' programs: judging")
        for it, r in zip(items, other):
            votes = {}
            for jm in res["judges"]:
                votes[jm] = _parse_label(call(jm, LABEL_PROMPT.format(code=r["code"][:6000]), "novelty"))
            it["votes"] = votes
    # 'other' > 20% adjudication flag per cell
    by = Counter(r.get("cell") for r in labels)
    oth = Counter(r.get("cell") for r in labels if r.get("label") == "other")
    res["cells_other_gt_20pct"] = [c for c in by if oth[c] > 0.2 * by[c]]
    # (3) style re-gate: 30 programs, stratified (10 BFS-labelled prefilled-prompt programs, 10 BFS free-dial
    # programs, 10 DFS programs), blind judge vs the frozen labeller; gated on the 12 catalogue references
    rng = random.Random(8)
    strata = {"G1a_bfs": [r for r in labels if r.get("cell") == "G1a" and r.get("code")],
              "free_dial_bfs": [r for r in labels if r.get("cell") == "F-DAS-r4-bfs-1.0" and r.get("label") == "bfs"],
              "dfs_any": [r for r in labels if r.get("label") == "dfs" and r.get("code")]}
    pick = []
    for k, v in strata.items():
        pick += [(k, r) for r in rng.sample(v, min(10, len(v)))]
    from cfg import SUITE

    refs = sorted((SUITE / "tasks" / "t1_grid" / "references").glob("*.py"))
    mode_of = {"astar": "astar_gbfs", "gbfs": "astar_gbfs", "bfs": "bfs", "bibfs": "bibfs", "dfs": "dfs",
               "dijkstra": "dijkstra", "iddfs": "iddfs"}
    jm = "google/gemini-2.5-flash-lite"
    with ThreadPoolExecutor(8) as ex:
        gate = list(ex.map(lambda f: (mode_of[f.stem.split("_")[0]],
                                      _parse_label(call(jm, LABEL_PROMPT.format(code=f.read_text()), "regate_gate"))), refs))
        rg = list(ex.map(lambda kr: (kr[0], kr[1]["row_id"], kr[1]["label"],
                                     _parse_label(call(jm, LABEL_PROMPT.format(code=kr[1]["code"][:6000]), "regate"))),
                         pick))
    gate_ok = sum(a == b for a, b in gate)
    parsed = [x for x in rg if x[3] is not None]
    res["style_regate"] = {"judge": jm, "gate_references": {"n": len(gate), "agree": gate_ok, "rows": gate},
                           "n": len(rg), "n_parsed": len(parsed), "agree": sum(x[2] == x[3] for x in parsed),
                           "rows": [{"stratum": a, "row_id": b, "labeller": c, "judge": d} for a, b, c, d in rg],
                           "by_stratum": {k: {"n": sum(1 for x in parsed if x[0] == k),
                                              "agree": sum(1 for x in parsed if x[0] == k and x[2] == x[3])}
                                          for k in strata}}
    res["openrouter_spent_usd_total"] = spent_total()
    res["budget_stopped"] = _STATE["stop"]
    write_json(RESULTS_DIR / "novelty_audit.json", res)
    logger.info(f"novelty: correct {n_corr}, other {len(other)}; regate {res['style_regate']['agree']}/"
                f"{res['style_regate']['n_parsed']}; gate {gate_ok}/{len(gate)}; spent {res['openrouter_spent_usd_total']:.4f}")


# ================================================================================================ diagnostics
def failure_reasons(labels: list[dict[str, Any]]) -> dict[str, Any]:
    """Re-run the frozen hidden tests on every failing program: first failing case and error type, per cell."""
    from cfg import bench_paths

    bench_paths()
    from tasks.harness import run_tests

    fail = [r for r in labels if not r.get("passed") and r.get("code")]
    cache: dict[str, dict[str, Any]] = {}

    def one(r: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        k = sha256_text(r["code"])
        if k not in cache:
            t = run_tests("t1", r["code"])
            cache[k] = {"error": t.get("error"), "first_failing_case": t.get("failed_case") or t.get("case_id"),
                        "n_passed": t.get("n_passed"), "fail_msg": (t.get("fail_msg") or "")[:120]}
        return r["row_id"], cache[k]
    with ThreadPoolExecutor(12) as ex:
        res = dict(ex.map(one, fail))
    out: dict[str, Any] = {}
    for r in fail:
        c = r.get("cell")
        d = res[r["row_id"]]
        o = out.setdefault(c, {"n_fail": 0, "error": Counter(), "n_passed_before_fail": Counter(), "fail_msg": Counter()})
        o["n_fail"] += 1
        o["error"][str(d["error"])] += 1
        o["n_passed_before_fail"][str(d["n_passed"])] += 1
        o["fail_msg"][d["fail_msg"][:60]] += 1
    return {c: {k: (dict(v) if isinstance(v, Counter) else v) for k, v in o.items()} for c, o in out.items()}


def fork_token_tables(labels: list[dict[str, Any]], tok: Any) -> dict[str, Any]:
    out = {}
    for c in CELL_ORDER:
        rr = [r for r in labels if r.get("cell") == c and int(r["slot"]) < 10]      # S50 / S30 slots only
        if not rr:
            continue
        cnt = Counter(r.get("fork_token") for r in rr)
        tab = {}
        for t, n in cnt.most_common(8):
            sub = [r for r in rr if r.get("fork_token") == t]
            tab[repr(tok.decode([t])) if t is not None else "None"] = {
                "token_id": t, "n": n, "bfs": sum(r["label"] == "bfs" for r in sub),
                "dfs": sum(r["label"] == "dfs" for r in sub), "pass": sum(bool(r["passed"]) for r in sub)}
        out[c] = tab
    return out


def engine_check(labels: list[dict[str, Any]], raw: dict[str, dict[str, Any]]) -> dict[str, Any]:
    i7l = {r["row_id"]: r for r in read_jsonl(C8.I7_LABELS)}
    i7r = {r["row_id"]: r for r in read_jsonl(C8.I7_RAW_DOSE)}
    out = {}
    for cell, c7 in (("P-twin", "twin"), ("P-DAS-bfs", "DAS|bfs|1.0"), ("G1c", "forced_bfs_F5")):
        rr = [r for r in labels if r.get("cell") == cell and r["slot"] < 10]
        ag = sum(r["label"] == i7l[f"g2|{c7}|{r['template']}|{r['slot']}"]["label"] for r in rr)
        agp = sum(r["label"] == i7l[f"g2|{c7}|{r['template']}|{r['slot']}"]["label"] and
                  bool(r["passed"]) == bool(i7l[f"g2|{c7}|{r['template']}|{r['slot']}"]["passed"]) for r in rr)
        same = sum(raw[r["row_id"]]["token_ids"] == i7r[f"g2|{c7}|{r['template']}|{r['slot']}"]["token_ids"] for r in rr)
        c_now = sum(r["label"] == "bfs" and bool(r["passed"]) for r in rr)
        c_7 = sum(i7l[f"g2|{c7}|{r['template']}|{r['slot']}"]["label"] == "bfs" and
                  bool(i7l[f"g2|{c7}|{r['template']}|{r['slot']}"]["passed"]) for r in rr)
        out[cell] = {"iter7_cell": c7, "n": len(rr), "label_agreement": ag / max(len(rr), 1),
                     "label_pass_agreement": agp / max(len(rr), 1), "byte_identical_share": same / max(len(rr), 1),
                     "correct_bfs_this_engine": c_now, "correct_bfs_iter7": c_7,
                     "pass_this_engine": sum(bool(r["passed"]) for r in rr) / max(len(rr), 1)}
    out["rule"] = "per-slot label agreement >= 0.95 else 'kernel sensitivity (RTX 4090 vs RTX 2000 Ada)'; continue"
    out["kernel_sensitivity_flag"] = any(v["label_agreement"] < 0.95 for k, v in out.items() if isinstance(v, dict))
    return out


def free_edit_diagnostics(raw: dict[str, dict[str, Any]]) -> dict[str, Any]:
    steps = {r["row_id"]: r["rec"] for r in read_jsonl(C8.STEPS)}
    out: dict[str, Any] = {}
    for c in ("F-twin",) + C8.FREE_CORE + C8.FREE_OPTIONAL:
        rows = [r for rid, r in raw.items() if rid.startswith(f"g8|{c}|")]
        m_at, norms = [], []
        for r in rows:
            i_d = r.get("decision_pos")
            rec = steps.get(r["row_id"])
            if i_d is not None and rec and i_d < len(rec["m"]):
                m_at.append(rec["m"][i_d])
            for e in r.get("edit_log") or []:
                if "edit_norm_fp32" in e:
                    norms.append(e["edit_norm_fp32"])
        if c == "F-twin":
            c2 = read_json(PRED_DIR / "commit2.json")["slots"]
            m_at = [v["m_at_i_d_unedited"] for v in c2.values() if v.get("m_at_i_d_unedited") is not None]
        out[c] = {"n": len(rows), "margin_at_i_d_mean": float(np.mean(m_at)) if m_at else None,
                  "margin_at_i_d_sd": float(np.std(m_at)) if m_at else None,
                  "edit_norm_mean": float(np.mean(norms)) if norms else None, "n_edited": len(norms)}
    return out


def wording_extension(labels: list[dict[str, Any]]) -> dict[str, Any]:
    """Exploratory (COMMIT #3): free-generation forced-BFS prompting across 8 wordings vs the free dial."""
    import analysis8 as A8

    if not (PRED_DIR / "commit3.json").exists():
        return {}
    dial = A8.cell_rows(labels, "F-DAS-r4-bfs-1.0")
    cells = ["G1c"] + sorted({r["cell"] for r in labels if str(r.get("cell", "")).startswith("G1e|")})
    out: dict[str, Any] = {"by_wording": {}}
    for c in cells:
        rows = A8.cell_rows(labels, c)
        if len(rows) < 50:
            continue
        s = A8.summarize_cell(rows, "bfs", C8.S50)
        t = A8.paired(dial, rows, A8.corr_fn("bfs"), A8.corr_fn("bfs"), C8.S50)
        disp = next((r.get("display") for r in labels if r.get("cell") == c), None)
        out["by_wording"][c] = {"forced": c if c != "G1c" else "G1e|F5|3 (= G1c)", "display": disp or "breadth-first search (BFS)",
                                "correct_bfs": s["correct_target"], "attempted_bfs": s["attempted_target"],
                                "pass_rate": s["pass_rate"], "queue_share": s["queue_share"],
                                "dial_only": t["a_only"], "prompt_only": t["b_only"], "p_two_sided_vs_free_dial": t["p_two_sided"],
                                "newcombe_dial_minus_prompt": t["newcombe_diff_a_minus_b"]}
    bw = out["by_wording"]
    if bw:
        vals = [v["correct_bfs"] for v in bw.values()]
        best = max(bw, key=lambda c: bw[c]["correct_bfs"])
        out.update({"n_wordings": len(bw), "mean_correct_bfs": float(np.mean(vals)), "min_correct_bfs": int(min(vals)),
                    "max_correct_bfs": int(max(vals)), "best_wording": best,
                    "free_dial_correct_bfs": A8.summarize_cell(dial, "bfs", C8.S50)["correct_target"],
                    "holm_vs_free_dial": A8.holm({c: v["p_two_sided_vs_free_dial"] for c, v in bw.items()}),
                    "note": "best-of-wordings is selected post hoc (optimistic prompting ceiling); exploratory"})
    return out


# ================================================================================================ analysis
def stage_analysis(args: Any) -> None:
    import analysis8 as A8
    import prompts as PG

    labels = load_labels()
    raw = load_raw()
    c1 = read_json(PRED_DIR / "commit1.json")
    c2 = read_json(PRED_DIR / "commit2.json")
    tf = read_json(RESULTS_DIR / "tf_stage.json")
    dorm = read_json(RESULTS_DIR / "dormancy.json")
    A = A8.analyze(labels, c1, c2, tf, dorm)
    A["engine_check"] = engine_check(labels, raw)
    tok = PG.tokenizer()
    A["fork_tokens"] = fork_token_tables(labels, tok)
    A["failure_reasons"] = failure_reasons(labels)
    A["free_edit_diagnostics"] = free_edit_diagnostics(raw)
    A["tf_forced_prompts"] = {k: {kk: v["-"][kk] for kk in ("m", "p_B", "p_D", "p_queue", "pred_attempted_bfs",
                                                            "pred_correct_bfs")}
                              for k, v in tf["tf_conditions"].items() if k.startswith("forced|")}
    A["logp_cstar"] = tf["logp_cstar"]
    A["commit2_prediction_scorecard"] = {
        c: {"predicted": v["total"], "observed": A["cells"].get(c, {}).get("correct_target"),
            "abs_error": (abs(v["total"] - A["cells"][c]["correct_target"]) if A["cells"].get(c, {}).get("n") else None)}
        for c, v in c2["predictions"].items()}
    A["literal_rule_diagnostic"] = Counter(str(v.get("literal_rule_i")) for v in c2["slots"].values())
    A["wording_extension"] = wording_extension(labels)
    A["gpu_tests"] = read_json(RESULTS_DIR / "tests_gpu.json")
    A["prefix_check"] = read_json(RESULTS_DIR / "prefix_check.json")
    A["n_programs"] = len(labels)
    A["labels_overall"] = dict(Counter(r.get("label") for r in labels))
    A["labeller_sources"] = dict(Counter(r.get("labeller_source") for r in labels))
    A["truncation"] = {"n_length": sum(r.get("finish_reason") == "length" for r in labels), "n": len(labels)}
    write_json(RESULTS_DIR / "analysis.json", A)
    _deviations(A)
    S = A["scorecard"]
    logger.info("scorecard: " + json.dumps({k: v.get("holds") for k, v in S.items() if isinstance(v, dict)}))
    logger.info("verdicts: " + json.dumps(A["verdicts"])[:800])


def _deviations(A: dict[str, Any]) -> None:
    hw = read_json(PRED_DIR / "hardware.json")
    gt = A["gpu_tests"]["U3p_decode_vs_prefill"]
    add_deviation("D-gpu", f"GPU {hw['gpu']} ({hw['vram_gb']:.0f} GB), not the planned RTX A4500 and not iteration 7's "
                           "RTX 2000 Ada; B_CRN 25 kept. Every contrast is computed inside this engine.")
    ec = A["engine_check"]
    add_deviation("D-engine", "Engine check label agreement with iteration 7: " + ", ".join(
        f"{k} {v['label_agreement']:.2f} (byte-identical {v['byte_identical_share']:.2f}; correct BFS {v['correct_bfs_this_engine']}"
        f" vs {v['correct_bfs_iter7']})" for k, v in ec.items() if isinstance(v, dict)) +
        ("; below 0.95 for at least one cell: kernel sensitivity (RTX 4090 vs RTX 2000 Ada), continued as committed."
         if ec["kernel_sensitivity_flag"] else ""))
    add_deviation("D-U3p", "U3' (decode-time hook vs prefilled-path edit at index 32): |dm| up to "
                           f"{max(v['abs_diff_edit'] for v in gt['by_template'].values()):.2f} nat with the DAS edit "
                           f"(plain path {max(v['abs_diff_plain'] for v in gt['by_template'].values()):.2f}); above the 0.3 nat "
                           "tolerance, logged and not fatal as committed; P4 measures the consequence.")
    add_deviation("D-maxnew", "max_new 1024 (protocol v8: 1,536 for path tasks) kept so iteration 7's record cells are "
                              f"reproducible slot for slot; truncated programs: {A['truncation']['n_length']}/{A['truncation']['n']}.")
    add_deviation("D-seed", "Generation uses DAS seed 0 (the seed whose prefilled dose curve is on record), not the "
                            "median seed; seed 2 runs teacher-forced at every rank and as the optional free cell.")
    add_deviation("D-rule", "Refined decision-position rule (body-indent previous token, live ' visited' p_D >= 0.01, "
                            "no algorithm-identifying string) instead of the literal rule; literal rule reported as a "
                            "diagnostic.")
    add_deviation("D-targets", "DAS class targets: seed 0 k <= 4 use commit3's coordinates (iteration-7 states); other "
                               "seeds/ranks and the TF dormancy use this engine's recomputed states.")
    add_deviation("D-method-edit", "method.py was edited after commit #0 to save block-17 decision-position states for "
                                   "the geometry figure (stage commit2) and to add two exploratory stages, each "
                                   "committed before it ran: gpu_extra (commit #3, free prompting across 8 wordings) "
                                   "and tf_extra (commit #4, layer sweep of full-state swaps); after the run the "
                                   "input-artifact paths were made portable (one artifact_dir() constant per input "
                                   "artifact: environment variable, sibling folder named by the id, or the run-volume "
                                   "layout); no committed statistic or rule changed.")
    add_deviation("D-not-rerun", "As planned, the DAS maps were not refitted and SHUF/RINIT were not re-run (iteration 7's "
                                 "controls stand); the transcoder graph was not attempted.")
    add_deviation("D-pca-upper", "Two 'pca_upper' quantities are reported: the plan's ||U64^T R_k||_F^2 / k (fraction of "
                                 "R_k inside the top-64 natural PCs) and E33's top-k PC variance share of the natural "
                                 "set; the committed rule uses neither (it uses retention).")
    add_deviation("D-iter7-cause", "Iteration 7 attributed the 0/125 pass of ' queue' programs to slowness; re-running the "
                                   "frozen hidden tests shows they fail on wall cases (wrong answer, no wall check of "
                                   "start/goal), not on time (see analysis.json failure_reasons).")


# ================================================================================================ figures
def _style() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9, "legend.fontsize": 7.5,
                         "xtick.labelsize": 8, "ytick.labelsize": 8, "pdf.fonttype": 42, "ps.fonttype": 42,
                         "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150})


PAL = {"prompt": "#E69F00", "dial": "#0072B2", "twin": "#999999", "dim": "#D55E00", "rand": "#CC79A7",
       "dfs": "#009E73", "bfs": "#56B4E9"}


def _save(fig: Any, name: str) -> None:
    FIG_DIR.mkdir(exist_ok=True)
    fig.savefig(FIG_DIR / f"{name}.png", bbox_inches="tight", dpi=200)
    fig.savefig(FIG_DIR / f"{name}.pdf", bbox_inches="tight")


def stage_figures(args: Any) -> None:
    _style()
    import matplotlib.pyplot as plt
    import torch

    A = read_json(RESULTS_DIR / "analysis.json")
    D = read_json(RESULTS_DIR / "dormancy.json")
    cells = A["cells"]
    # ---------------- F1: the 2x2 (prefilled vs free) x (prompt vs dial), twins beside
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.3))
    groups = [("c* prefilled", ["P-twin", "G1a", "P-DAS-bfs"]), ("free generation", ["F-twin", "G1c", "F-DAS-r4-bfs-1.0"])]
    labels_ = ["twin (no edit)", "forced-BFS prompt", "DAS dial (r4, lam 1)"]
    cols = [PAL["twin"], PAL["prompt"], PAL["dial"]]
    for ax, (metric, ttl) in zip(axes, (("correct", "correct BFS programs / 50"), ("pass", "pass rate (hidden tests)"),
                                        ("queue", "fork token ' queue' share"))):
        for gi, (gname, cl) in enumerate(groups):
            for j, c in enumerate(cl):
                s = cells.get(c, {})
                if not s.get("n"):
                    continue
                n = s["n"]
                if metric == "correct":
                    k = s["correct_target"]
                elif metric == "pass":
                    k = s["pass"]
                else:
                    k = round(s["queue_share"] * n)
                import analysis8 as A8

                lo, hi = A8.wilson(k, n)
                x = gi * 4 + j
                ax.bar(x, k / n, color=cols[j], width=0.8, label=labels_[j] if gi == 0 else None)
                ax.errorbar(x, k / n, yerr=[[max(k / n - lo, 0.0)], [max(hi - k / n, 0.0)]], color="k", lw=0.8, capsize=2)
                ax.text(x, hi + 0.03, f"{k}" if metric != "pass" else f"{k / n:.2f}", ha="center", fontsize=7)
        we = A.get("wording_extension", {}).get("by_wording", {})
        if we and metric in ("correct", "pass"):
            vals = [(v["correct_bfs"] / 50 if metric == "correct" else v["pass_rate"]) for v in we.values()]
            ax.scatter(np.full(len(vals), 5.0) + np.linspace(-0.25, 0.25, len(vals)), vals, s=9, color="k", zorder=4,
                       label="free prompt, 8 wordings (exploratory)" if metric == "correct" else None)
        ax.set_xticks([1, 5])
        ax.set_xticklabels([g for g, _ in groups])
        ax.set_ylim(0, 1.15)
        ax.set_title(ttl)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.08))
    fig.suptitle("F1. Prefill-matched 2x2 at Gemma's grid-path fork (same 50 CRN slots, Wilson 95% CIs)", y=1.02)
    _save(fig, "F1_2x2")
    plt.close(fig)
    # ---------------- F2: free-dial decomposition (decision index and outcome by reach type)
    c2 = read_json(PRED_DIR / "commit2.json")
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.2), gridspec_kw={"width_ratios": [1, 1.6]})
    ids = [v["i_d"] for v in c2["slots"].values() if v["i_d"] is not None]
    nr = sum(v["i_d"] is None for v in c2["slots"].values())
    axes[0].hist(ids, bins=np.arange(0, 98, 2), color=PAL["dial"])
    axes[0].set_xlabel("decision index i_d (response token)")
    axes[0].set_ylabel("slots (S50 + HT30)")
    axes[0].set_title(f"decision position: R1 {sum(v['reach_type'] == 'R1' for v in c2['slots'].values())}, "
                      f"R2 {sum(v['reach_type'] == 'R2' for v in c2['slots'].values())}, not reached {nr}")
    dec = A["decomposition"]["by_cell"]
    cl = [c for c in ("F-twin", "F-DAS-r4-bfs-1.0", "F-DAS-r4-bfs-0.5", "F-DAS-r1-bfs-1.0", "F-DAS-r1-bfs-0.5",
                      "F-DAS-s2-r4-bfs-1.0", "F-RAND-r4-1.0", "F-DiM-bfs", "F-DAS-r4-dfs-1.0", "F-DiM-dfs") if c in dec]
    x = np.arange(len(cl))
    bottom = np.zeros(len(cl))
    for typ, col in (("R1", PAL["dial"]), ("R2", PAL["bfs"]), ("NOT_REACHED", PAL["twin"])):
        v = np.array([dec[c][typ].get("correct_target", 0) if dec[c][typ].get("n") else 0 for c in cl])
        axes[1].bar(x, v, bottom=bottom, color=col, label=f"correct target, {typ} slots")
        bottom += v
    pred = [dec[c]["predicted_correct_target"] for c in cl]
    axes[1].scatter(x, pred, marker="_", s=250, color="k", zorder=3, label="commit #2 prediction")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels([c.replace("F-", "") for c in cl], rotation=35, ha="right")
    axes[1].set_ylabel("correct target programs / 50")
    axes[1].set_ylim(0, 56)
    axes[1].legend(frameon=False, fontsize=7, loc="upper left")
    axes[1].set_title("free-generation cells by reach type (target: BFS, or DFS for *-dfs cells)")
    _save(fig, "F2_free_decomposition")
    plt.close(fig)
    # ---------------- F3: dormancy by rank
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.3))
    ks = ["1", "2", "4", "8"]
    import tf8

    # (a) natural variance: Haar distribution (recomputed, generator 9 + k) vs DAS share
    Hv = torch.load(ROOT / "cache" / "states" / "fork_variants.pt")
    X = torch.stack([v["h"][C8.L] for v in Hv]).float()
    Xc = X - X.mean(0, keepdim=True)
    Sig = (Xc.T @ Xc) / (X.shape[0] - 1)
    trS = float(torch.trace(Sig))
    viol = []
    for k in ks:
        gq = torch.Generator().manual_seed(9 + int(k))
        rs = []
        for _ in range(300):
            Rr = torch.linalg.qr(torch.randn(2560, int(k), generator=gq))[0]
            rs.append(float(torch.trace(Rr.T @ Sig @ Rr)) / trS)
        viol.append(rs)
    nv = D["natural_variance"]["this_engine_v120"]
    nv160 = D["natural_variance"]["this_engine_v160"]
    axes[0].violinplot(viol, positions=range(4), showextrema=False)
    axes[0].scatter(range(4), [nv[k]["share"] for k in ks], color=PAL["dial"], zorder=3, label="DAS R_k (120 twins)")
    axes[0].scatter(range(4), [nv[k]["random_p95"] for k in ks], marker="_", s=200, color="k", label="random p95")
    axes[0].scatter(range(4), [nv160[k]["share"] for k in ks], color=PAL["prompt"], marker="^", zorder=3,
                    label="DAS R_k (twins + 40 forced)")
    axes[0].set_yscale("log")
    axes[0].set_xticks(range(4))
    axes[0].set_xticklabels([f"k={k}" for k in ks])
    axes[0].set_ylabel("share of natural variance")
    axes[0].set_title("(a) natural variance vs Haar rank-k")
    axes[0].legend(frameon=False, fontsize=6.5)
    pr = D["projection"]
    for nm, col, lab in (("pc64_v120", PAL["dial"], "retention, 64 PCs of 120 twins"),
                         ("pc64_v160", PAL["prompt"], "retention, 64 PCs of twins + forced"),
                         ("pc100_v120", PAL["bfs"], "retention, 100 PCs of 120 twins")):
        axes[1].plot(range(4), [pr[k][nm]["retention_interchange"]["estimate"] for k in ks], "o-", color=col, label=lab)
    axes[1].plot(range(4), [pr[k]["pc64_v120"]["residual_interchange"]["estimate"] for k in ks], "s--", color=PAL["dim"],
                 label="residual (orth. to 64 twin PCs)")
    axes[1].axhline(0.5, ls=":", color="k", lw=0.8)
    axes[1].set_xticks(range(4))
    axes[1].set_xticklabels([f"k={k}" for k in ks])
    axes[1].set_ylabel("effect ratio vs R_k (forward, 768 pairs)")
    axes[1].set_title("(b) projected-map retention (Makelov)")
    axes[1].set_ylim(0, 0.95)
    axes[1].legend(frameon=False, fontsize=6.2, loc="upper right", ncol=1)
    fw = [D["forward"]["by"][f"seed0_k{k}"]["median_recovery"] for k in ks]
    rv = [D["reverse"]["by_k"][k]["held"]["reverse_recovery"] for k in ks]
    rci = [D["reverse"]["by_k"][k]["held"]["reverse_recovery_ci95"] for k in ks]
    axes[2].plot(range(4), fw, "o-", color=PAL["dial"], label="forward recovery (twin <- forced)")
    axes[2].errorbar(range(4), rv, yerr=[[max(r - c[0], 0) for r, c in zip(rv, rci)], [max(c[1] - r, 0) for r, c in zip(rv, rci)]],
                     fmt="s-", color=PAL["dfs"], capsize=2, label="reverse recovery (forced-BFS <- twin)")
    hn = [D["reverse"]["by_k"][k]["held"]["haar_null_mean"] / D["reverse"]["by_k"][k]["held"]["dm_full_mean"] for k in ks]
    axes[2].plot(range(4), hn, "x:", color=PAL["twin"], label="reverse, Haar rank-k mean")
    axes[2].axhline(0.5, ls=":", color="k", lw=0.8)
    axes[2].set_xticks(range(4))
    axes[2].set_xticklabels([f"k={k}" for k in ks])
    axes[2].set_ylabel("DAS effect / full-state swap at block 17")
    axes[2].set_title("(c) forward and reverse interchange")
    axes[2].legend(frameon=False, fontsize=6.5)
    _save(fig, "F3_dormancy")
    plt.close(fig)
    # ---------------- F4: geometry in block-17 activation coordinates
    maps = {sd: torch.load(ROOT / "cache" / "das_subspaces" / f"das_L17_seed{sd}.pt").float() for sd in C8.SEEDS}
    R = maps[0][:, :2]
    S7 = torch.load(ROOT / "cache" / "states" / "fork_sources.pt")
    Hs = torch.stack([s["h"][C8.L] for s in S7]).float()
    yv = np.array([v["y"] for v in Hv])
    geo = torch.load(ROOT / "cache" / "decision_states.pt")
    Hd = torch.stack([g["h"] for g in geo.values()]).float()
    c3 = read_json(C8.I7 / "predictions" / "commit3.json")["target_coordinates"]
    R4 = maps[0][:, :4]
    edited = {}
    for Y in ("bfs", "dfs"):
        cY = torch.tensor(c3[Y])
        edited[Y] = Hd + ((cY[None] - Hd @ R4) @ R4.T)
    tfs = read_json(RESULTS_DIR / "tf_stage.json")
    u = torch.load(ROOT / "cache" / "das_subspaces" / "dim_L17.pt").float()
    edited["dim_bfs"] = Hd + tfs["dim_betas"]["bfs"]["beta"] * u[None]
    mu = X.mean(0)
    U, Sv, Vt = torch.linalg.svd(X - mu, full_matrices=False)
    P2 = Vt[:2].T
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    for ax, B, nm in ((axes[0], R, "(R_1, R_2) of the DAS map (seed 0)"), (axes[1], P2, "(PC1, PC2) of the 120 twin variants")):
        off = mu @ B if B is P2 else torch.zeros(2)
        pv = (X @ B - off).numpy()
        ps = (Hs @ B - off).numpy()
        pdd = (Hd @ B - off).numpy()
        sc = ax.scatter(pv[:, 0], pv[:, 1], c=yv, cmap="viridis", s=10, alpha=0.8, label="120 twin variants (colour = y_v)")
        mb = np.array([s["mode"] == "bfs" for s in S7])
        ax.scatter(ps[mb, 0], ps[mb, 1], marker="^", color=PAL["bfs"], edgecolor="k", lw=0.3, s=28, label="forced-BFS sources")
        ax.scatter(ps[~mb, 0], ps[~mb, 1], marker="v", color=PAL["dfs"], edgecolor="k", lw=0.3, s=28, label="forced-DFS sources")
        ax.scatter(pdd[:, 0], pdd[:, 1], marker="o", facecolor="none", edgecolor="k", s=18, lw=0.6,
                   label="free twin at decision position")
        for Y, col, mk in (("bfs", PAL["dial"], "P"), ("dfs", "#7B2D8E", "X"), ("dim_bfs", PAL["dim"], "*")):
            pe = (edited[Y] @ B - off).numpy()
            ax.scatter(pe[:, 0], pe[:, 1], marker=mk, color=col, s=20, alpha=0.7,
                       label={"bfs": "after DAS r4 -> BFS", "dfs": "after DAS r4 -> DFS", "dim_bfs": "after DiM -> BFS"}[Y])
        ax.set_xlabel(("R_1" if B is R else "PC1") + " coordinate (residual units)")
        ax.set_ylabel(("R_2" if B is R else "PC2") + " coordinate (residual units)")
        ax.set_title(nm)
    axes[0].legend(frameon=False, fontsize=6.3, loc="best")
    fig.colorbar(sc, ax=axes[1], label="y_v (fork margin, nats)")
    fig.suptitle("F4. Block-17 fork states in actual activation coordinates (p_f / decision position)", y=1.01)
    _save(fig, "F4_geometry")
    plt.close(fig)
    # ---------------- F5: principal cosines across seeds
    fig, axes = plt.subplots(1, 4, figsize=(12.5, 2.6), gridspec_kw={"width_ratios": [1, 2, 4, 8], "wspace": 0.12})
    for ai, (ax, k) in enumerate(zip(axes, ks)):
        pcs = D["principal_cosines"][k]
        M = np.array([pcs[p] for p in ("0-1", "0-2", "1-2")])
        im = ax.imshow(M, vmin=0, vmax=1, cmap="magma", aspect="auto")
        ax.set_yticks(range(3))
        ax.set_yticklabels(["seed 0-1", "seed 0-2", "seed 1-2"] if ai == 0 else [])
        ax.set_xticks(range(int(k)))
        ax.set_xticklabels([str(i + 1) for i in range(int(k))])
        ax.set_xlabel("angle index" if ai else "principal angle index")
        ax.set_title(f"k = {k}")
        for i in range(3):
            for j in range(int(k)):
                ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=6.0,
                        color="w" if M[i, j] < 0.5 else "k")
    fig.colorbar(im, ax=axes, label="cosine")
    fig.suptitle("F5. Principal cosines between the three DAS fitting seeds at block 17", y=1.04)
    _save(fig, "F5_principal_cosines")
    plt.close(fig)
    # ---------------- F6: fork-token mix and pass by cell (why prefill-matched prompting fails)
    ft = A["fork_tokens"]
    show = ["P-twin", "G1a", "G1d", "P-DAS-bfs", "F-twin", "G1c", "F-DAS-r4-bfs-1.0", "F-DiM-bfs"]
    toks = ["'visited'", "'\\n'", "'if'", "'queue'", "'q'"]
    fig, ax = plt.subplots(figsize=(9, 3.2))
    bottom = np.zeros(len(show))
    tcol = [PAL["dfs"], PAL["bfs"], PAL["dial"], PAL["prompt"], PAL["rand"], PAL["twin"]]
    for t, col in zip(toks + ["other"], tcol):
        v = []
        for c in show:
            tab = ft.get(c, {})
            n = sum(x["n"] for x in tab.values()) or 1
            if t == "other":
                v.append(sum(x["n"] for kk, x in tab.items() if kk.strip() not in [s.strip() for s in toks]
                             and kk not in ("' visited'", "' queue'", "' if'", "' q'")) / n)
            else:
                v.append(sum(x["n"] for kk, x in tab.items() if kk.replace(" ", "") == t.replace(" ", "")) / n)
        ax.bar(range(len(show)), v, bottom=bottom, color=col, label=f"fork token {t}")
        bottom += np.array(v)
    for i, c in enumerate(show):
        s = cells.get(c, {})
        if s.get("n"):
            ax.text(i, 1.03, f"pass {s['pass_rate']:.2f}\ncorr {s['correct_target']}", ha="center", fontsize=6.5)
    ax.set_xticks(range(len(show)))
    ax.set_xticklabels(show, rotation=25, ha="right")
    ax.set_ylim(0, 1.2)
    ax.set_ylabel("share of programs")
    ax.legend(frameon=False, fontsize=6.5, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.32))
    ax.set_title("F6. Token at response index 32 (or its free-generation analogue) by cell")
    _save(fig, "F6_fork_tokens")
    plt.close(fig)
    # ---------------- F7: layer sweep of single-block full-state swaps at p_f (exploratory, commit #4)
    lsp = RESULTS_DIR / "layer_sweep.json"
    if lsp.exists():
        Ls = read_json(lsp)
        blocks = Ls["blocks"]
        fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.4))
        for key, col, lab in (("reverse", PAL["dfs"], "forced-BFS + c*, block-l state <- twin"),
                              ("forward", PAL["prompt"], "twin + c*, block-l state <- forced-BFS")):
            q = [np.mean([r[key]["p_queue"] for r in Ls["rows"] if r["block"] == l]) for l in blocks]
            m = [np.mean([r[key]["m"] for r in Ls["rows"] if r["block"] == l]) for l in blocks]
            axes[0].plot(blocks, q, "o-", ms=3, color=col, label=lab)
            axes[1].plot(blocks, m, "o-", ms=3, color=col, label=lab)
        dq = np.mean([b["dial"]["p_queue"] for b in Ls["bases"]])
        dm = np.mean([b["dial"]["m"] for b in Ls["bases"]])
        tfc = read_json(RESULTS_DIR / "tf_stage.json")["tf_conditions"]
        dimq = np.mean([tfc["DiM|bfs|matched"][w]["p_queue"] for w in ("W4", "W5")])
        dimm = np.mean([tfc["DiM|bfs|matched"][w]["m"] for w in ("W4", "W5")])
        for ax, v1, v2 in ((axes[0], dq, dimq), (axes[1], dm, dimm)):
            ax.scatter([17], [v1], marker="P", s=70, color=PAL["dial"], zorder=4, label="twin + DAS r4 lam 1 at block 17")
            ax.scatter([17], [v2], marker="*", s=90, color=PAL["dim"], zorder=4, label="twin + DiM (matched) at block 17")
            ax.axvline(17, ls=":", color="k", lw=0.7)
            ax.set_xlabel("block l of the single-block full-state swap at p_f")
        axes[0].set_ylabel("p(' queue') at the fork")
        axes[1].set_ylabel("fork margin m (nats)")
        axes[0].set_title("(a) p(' queue'): full-state swaps by block vs the block-17 DAS and DiM edits")
        axes[1].set_title("(b) BFS-vs-DFS margin")
        axes[0].legend(frameon=False, fontsize=6.5, loc="center left")
        fig.suptitle("F7. Layer sweep at p_f (W4/W5 twins vs forced F4/F5, 4 display names; teacher-forced)", y=1.02)
        _save(fig, "F7_layer_sweep")
        plt.close(fig)
    _ = (tf8, TEMPLATE_IDS)
    logger.info("figures written")


# ================================================================================================ outputs
def stage_outputs(args: Any) -> None:
    import prompts as PG
    import fork7 as FK

    labels = load_labels()
    raw = load_raw()
    A = read_json(RESULTS_DIR / "analysis.json")
    hw = read_json(PRED_DIR / "hardware.json")
    c2 = read_json(PRED_DIR / "commit2.json")
    tok = PG.tokenizer()
    pr = {f"twin|{w}": FK.twin(w) for w in TEMPLATE_IDS}
    for f in ("F1", "F2", "F3", "F4", "F5"):
        for m in ("bfs", "dfs"):
            pr[f"forced|{m}|{f}"] = FK.forced(m, f, 3)
    # ---------------- data/samples.jsonl (one row per program)
    rows = []
    for r in labels:
        c = r.get("cell")
        rw = raw.get(r["row_id"], {})
        meth = rw.get("method") or r.get("method")
        if c in ("G1a", "G1c", "G1b", "G1d") or str(c).startswith("G1e|"):
            fm, ff, fp = rw["forced"].split("|")
            p = FK.forced(fm, ff, int(fp)) if c.startswith("G1e|") else pr[f"forced|{fm}|{ff}"]
        elif c in ("REV-DAS", "REV-FULL"):
            p = pr["forced|bfs|F5"]
        else:
            p = pr[f"twin|{r['template']}"]
        rank = rw.get("rank_k")
        rows.append({"row_id": r["row_id"], "model": IT_ID, "task": "T1", "arm": c, "method": meth, "site": "resid",
                     "layer": C8.L if meth not in (None, "none", "prompt") else None, "rank_k": rank,
                     "dose": rw.get("dose"), "temperature": 1.0, "top_k": None,
                     "decision_pos": rw.get("decision_pos", 32 if rw.get("prefilled") and meth not in ("none", "prompt") else None),
                     "reached_decision": rw.get("reached_decision"), "reach_type": rw.get("reach_type"),
                     "prefilled": rw.get("prefilled"), "prefix_match": r.get("prefix_match"),
                     "fork_token": r.get("fork_token"),
                     "fork_token_str": tok.decode([r["fork_token"]]) if r.get("fork_token") is not None else None,
                     "template": r["template"], "slot": r["slot"], "ukey": rw.get("ukey"), "precision": "bf16",
                     "noun": p.get("noun"), "prompt_display": p.get("display"),
                     "gpu": hw["gpu"], "prompt_sha256": p["prompt_sha256"], "label": r.get("label"),
                     "labeller_source": r.get("labeller_source"), "passed": bool(r.get("passed")),
                     "n_new_tokens": r.get("n_new_tokens"), "finish_reason": r.get("finish_reason"),
                     "code_sha256": r.get("code_sha256"), "code": r.get("code")})
    rows.sort(key=lambda x: (CELL_ORDER.index(x["arm"]) if x["arm"] in CELL_ORDER else 99, x["template"], x["slot"]))
    write_jsonl(DATA_DIR / "samples.jsonl", rows)
    by = {(x["arm"], x["template"], x["slot"]): x for x in rows}

    def lp(c: str, w: str, k: int) -> str:
        x = by.get((c, w, k))
        return "missing" if x is None else f"{x['label']}|{'pass' if x['passed'] else 'fail'}"
    twin_text = {w: tok.decode(FK.twin(w)["ids"]) for w in TEMPLATE_IDS}
    fb_text = tok.decode(FK.forced("bfs", "F5", 3)["ids"])
    datasets = []
    # engine_check: 50 slots x 2 cells
    ex = []
    for c in ("P-twin", "P-DAS-bfs"):
        for (w, k) in C8.S50:
            ex.append({"input": twin_text[w] + "[prefilled c*]", "output": lp(c, w, k),
                       "predict_iter7_same_slot": _i7lp(c, w, k), "metadata_cell": c, "metadata_template": w,
                       "metadata_slot": k, "metadata_description": CELL_DESC[c]})
    datasets.append({"dataset": "engine_check", "examples": ex})
    # g1_prefill_matched: 50 slots; output = P-DAS-bfs
    ex = []
    for (w, k) in C8.S50:
        ex.append({"input": twin_text[w] + "[prefilled c*]", "output": lp("P-DAS-bfs", w, k),
                   "predict_forced_bfs_cstar": lp("G1a", w, k), "predict_forced_bfs_free": lp("G1c", w, k),
                   "predict_twin_cstar": lp("P-twin", w, k), "predict_forced_dfs_cstar": lp("G1b", w, k),
                   "predict_das_dfs_cstar": lp("P-DAS-dfs", w, k), "predict_forced_best_wording_cstar": lp("G1d", w, k),
                   **{f"predict_forced_bfs_free_{f}_pair{pi}": lp(f"G1e|{f}|{pi}", w, k)
                      for f, pi in (("F1", 3), ("F2", 3), ("F3", 3), ("F4", 3), ("F5", 0), ("F5", 1), ("F5", 2))},
                   "metadata_template": w, "metadata_slot": k, "metadata_ukey": json.dumps(list(C8.ukey(w, k))),
                   "metadata_forced_prompt": fb_text[:400]})
    datasets.append({"dataset": "g1_prefill_matched", "examples": ex})
    # g2_free_dial: 50 slots; output = F-twin
    ex = []
    for (w, k) in C8.S50 + C8.HT30:
        d = c2["slots"][f"{w}|{k}"]
        e = {"input": twin_text[w], "output": lp("F-twin", w, k), "metadata_template": w, "metadata_slot": k,
             "metadata_reach_type": d["reach_type"], "metadata_decision_pos": d["i_d"] if d["i_d"] is not None else -1,
             "metadata_HT30": (w, k) in C8.HT30}
        for c in C8.FREE_CORE + C8.FREE_OPTIONAL:
            if (c, w, k) in by:
                e["predict_" + c.replace("-", "_").replace(".", "p")] = lp(c, w, k)
        e["predict_prefilled_das_bfs"] = lp("P-DAS-bfs", w, k) if (w, k) in C8.S50 else "not_run"
        e["predict_prefilled_twin"] = lp("P-twin", w, k) if (w, k) in C8.S50 else "not_run"
        ex.append(e)
    datasets.append({"dataset": "g2_free_dial", "examples": ex})
    # g3_reverse_gen: 30 slots
    ex = []
    for (w, k) in C8.S30:
        ex.append({"input": fb_text + "[prefilled c*; block-17 p_f state <- twin " + w + "]",
                   "output": lp("G1a", w, k), "predict_rev_das_r4": lp("REV-DAS", w, k),
                   "predict_rev_full_state": lp("REV-FULL", w, k), "metadata_template_of_source_state": w,
                   "metadata_slot": k})
    datasets.append({"dataset": "g3_reverse_gen", "examples": ex})
    # g3_dormancy: one example per rank x check
    D = read_json(RESULTS_DIR / "dormancy.json")
    sm = D["summary_by_k"]
    ex = []
    for k in ("1", "2", "4", "8"):
        s = sm[k]
        for chk, val, pred in (("forward_recovery", s["forward_recovery"], ">= 0.8 (sufficiency)"),
                               ("reverse_recovery", s["reverse_recovery"], ">= 0.5 (account D5/K2)"),
                               ("projected_retention_pc64_twins", s["retention"], ">= 0.5 (account D5/K2)"),
                               ("projected_retention_pc64_twins_plus_forced",
                                D["projection"][k]["pc64_v160"]["retention_interchange"]["estimate"], "sensitivity"),
                               ("natural_variance_share", s["share"], f"<= random p95 {s['random_p95']:.5f} (iteration 7)"),
                               ("seed_principal_cosine_max", max(max(v) for v in s["principal_cosines"].values()), "about 0.5")):
            ex.append({"input": f"rank k={k}; check={chk}", "output": f"{val:.4f}" if isinstance(val, float) else str(val),
                       "predict_committed_expectation": pred, "predict_verdict": s["verdict"],
                       "metadata_rank": int(k), "metadata_check": chk})
    datasets.append({"dataset": "g3_dormancy", "examples": ex})
    meta = {"method_name": "Fair test of Gemma's BFS dial (iteration 8, claim G)",
            "description": "Prefill-matched prompting baseline, free-generation DAS dial at a committed decision "
                           "position, and dormancy checks of the rank-k DAS subspace at block 17 of gemma-3-4b-it",
            "model": IT_ID, "hardware": hw, "scorecard": A["scorecard"], "verdicts": A["verdicts"],
            "commitments": (ROOT / "commitments.log").read_text().splitlines(),
            "results": {p.stem: read_json(p) for p in sorted(RESULTS_DIR.glob("*.json"))
                        if p.stem not in ("tf_stage",) and p.stat().st_size < 3_000_000},
            "tf_stage_summary": {k: v for k, v in read_json(RESULTS_DIR / "tf_stage.json").items()
                                 if k in ("cell_predictions", "dim_betas", "logp_cstar", "G1d_template",
                                          "state_recompute_vs_iter7", "targets_vs_commit3_max_abs", "calibration")}}
    out = {"metadata": meta, "datasets": datasets}
    write_json(ROOT / "method_out.json", out)
    logger.info(f"method_out.json: {sum(len(d['examples']) for d in datasets)} examples in {len(datasets)} datasets; "
                f"{(ROOT / 'method_out.json').stat().st_size / 1e6:.2f} MB")


_I7: dict[str, Any] = {}


def _i7lp(c: str, w: str, k: int) -> str:
    if not _I7:
        _I7.update({r["row_id"]: r for r in read_jsonl(C8.I7_LABELS)})
    key = {"P-twin": "twin", "P-DAS-bfs": "DAS|bfs|1.0"}[c]
    r = _I7.get(f"g2|{key}|{w}|{k}")
    return "missing" if r is None else f"{r['label']}|{'pass' if r['passed'] else 'fail'}"


# ================================================================================================ positioning
def stage_positioning(args: Any) -> None:
    """Dated positioning record (searches run on 2026-10-23 with aii-web-tools; quotes copied from the fetched
    abstracts in logs/positioning/)."""
    from positioning8 import ENTRIES, QUERIES

    write_json(RESULTS_DIR / "positioning.json", {"date": "2026-10-23", "tool": "aii-web-tools (scholarly + general)",
                                                  "queries": QUERIES, "entries": ENTRIES})
    logger.info(f"positioning: {len(ENTRIES)} entries")
    _ = Path
