#!/usr/bin/env python3
"""Iteration-7 Step 0: repair the run's record number by number (items 0a to 0l), prove that every correction
applies, lint the corrected report for leftover wrong claims, and write eval_out.json (exp_eval_sol_out).

Usage: uv run eval.py --stages all          (everything, including the paid judges and the web positioning pass)
       uv run eval.py --stages offline      (reuse the cached judge and web results; no network)
"""

from __future__ import annotations

import argparse
import csv
import json
import resource
import subprocess
import sys
import time
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS / "src"))

from loguru import logger  # noqa: E402

from common import (AUDIT, INPUTS, MARK, READ_DATE, TABLES, inp, read_json, setup_logging, sha256_file,  # noqa: E402
                    write_json)
from corrections import V, Registry, apply_all, lint, unified_diff  # noqa: E402
from editor import Editor  # noqa: E402

RATIONALE = {
    "0a": "Stage A outcome returned to commit0's definition (attempted share, invalid as not-Y, pass-ratio gate) with a "
          "correct-Y count beside every share",
    "0b": "the site of the choice stated as open: the condition-span clause fails post hoc; the 'FP8-specific' label "
          "cannot apply",
    "0c": "Gemma's DAS and readout stated within the controls they had",
    "0d": "per-model, per-quantity synthesis in place of one cross-model map",
    "0e": "captioned [FIGURE] markers for the activation-space geometry plots",
    "0f": "top-five push dose caveat (1 to 8 ban units overshoot the forced-prompt manifold)",
    "0g": "correct-only columns for Table 238 and the MIXED screen-level verdict",
    "0h": "NLA per-sample test quoted with its clustered interval and at one unit per sample",
    "0i": "checks that ran but were never reported, and the judged engine-control programs",
    "0j": "Section 4.9 limited to the pools actually audited",
    "0k": "quote-verified positioning row for the one-token fork",
    "0l": "iteration-5 verdicts tagged as conditional",
}


def set_limits() -> None:
    resource.setrlimit(resource.RLIMIT_AS, (24 * 1024 ** 3, 24 * 1024 ** 3))


def table278_row(nov: dict) -> tuple[str, str]:
    old = ("| Engine control | every correct off-default or other program, against 18,237 known solutions | up to 237 "
           "per engine and task | variants and distant programs of known algorithms (nearest-known pass only) | not judged |")
    cls = {}
    for p in nov["programs"]:
        cls[p["final_class"]] = cls.get(p["final_class"], 0) + 1
    g = "; ".join(f"{m.split('/')[-1]} gate {v['merged_correct']}/10" for m, v in nov["gate"].items())
    new = (f"| Engine control | every correct off-default or other program, against 18,237 known solutions (nearest-known "
           f"pass only); its {nov['n_programs']} correct programs labelled other judged blind in iteration 7 | up to 237 "
           f"per engine and task; {nov['n_programs']} labelled other | nearest-known pass: variants and distant programs "
           f"of known algorithms; the {nov['n_programs']} programs: "
           + ", ".join(f"{k.lower().replace('_', ' ')} {v}" for k, v in sorted(cls.items()))
           + f" (blind judges: {g}; gated {', '.join(m.split('/')[-1] for m in nov['gated_judges'])}; kappa "
           + (f"{nov['kappa_merged_classes']:.2f}" if nov['kappa_merged_classes'] is not None else "n/a")
           + " on merged classes; manual read) | "
           f"{nov['n_novel_final']} {MARK} |")
    return old, new


def positioning_row(pos: dict, g: dict) -> tuple[str, str]:
    anchor = ("| 65 | engine (8-bit floating-point W8A8) | Mechanism sources: LLM.int8(); SmoothQuant; massive "
              "activations; 8-bit floating-point formats; the dynamic 8-bit floating-point scheme of llm-compressor | "
              "mechanism background | n/a | n/a | per-token-scale ablation |")
    nb = pos["neighbours"]
    def venue(v: dict) -> str:
        if v.get("venue_found"):
            return v["venue_found"]
        if v.get("venue_note"):
            return "no venue on the arXiv record; no NeurIPS 2026 paper page found by the dated search"
        return "no venue on the arXiv record"

    names = "; ".join(f"{v['name']} ({venue(v)}; arXiv {v['arxiv']}"
                      f"{(' ' + v['version_found']) if v.get('version_found') else ''})" for v in nb.values())
    row = (f"\n| 66 | one-token fork (Gemma) | {names} | adjacent: forking-token resampling and planning detection are "
           "occupied as methods; none of these reports an algorithm-level fork in generated code at a token that does "
           "not identify the algorithm | ADJACENT-ONLY (to our knowledge, mini search dated "
           f"{READ_DATE}) | an algorithm-level fork (BFS or DFS) in generated code at one token that does not identify "
           "the algorithm, about 138 tokens before the code that does; its fork log-odds varies across 120 prompt "
           f"variants (SD 0.67 nats) and is linearly decodable from the residual at the fork (R-squared 0.66 Lasso on "
           f"SAE codes, 0.72 raw ridge), which at that position is close to a next-token readout, not evidence of a "
           f"plan; steering costs are measured (pass {g['twin_pass']:.2f} to {g['main4_pass'][0]:.2f}-"
           f"{g['main4_pass'][1]:.2f}) | forking-token resampling baseline; a logit-lens control of matched capacity "
           f"{MARK} |")
    return anchor, row


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", default="all", choices=["all", "offline"])
    args = ap.parse_args()
    setup_logging("eval")
    set_limits()
    t_start, cpu0 = time.time(), time.process_time()
    from stage_inputs import resolve_all
    hashes = resolve_all()
    report = (INPUTS / "report" / "current_report.md").read_text()
    report6 = inp("art_aRTQM6CQ0Dre", "inputs/report/current_report.md").read_text()
    reg = Registry(report)
    ed = Editor(report, reg)
    import items_other as O
    import items_qwen as Q
    from figmarkers import build as build_figs

    logger.info("0a Stage A metric")
    A = Q.item_0a(ed, report)
    logger.info("0b site")
    B = Q.item_0b(ed, report, A["cells"])
    logger.info("0g Table 238")
    G8 = Q.item_0g(ed, report)
    logger.info("0c Gemma")
    GE = O.gemma_values()
    O.item_0c(ed, GE)
    logger.info("0h NLA one unit per sample")
    H = O.item_0h(ed)
    logger.info("cross-check against the dependencies' published predict_* fields")
    from crosscheck_predict import crosscheck
    XC = crosscheck({k: v for k, v in A["cells"].items()}, G8["pn_correct"], H["units"])
    write_json(WS / "results" / "predict_crosscheck.json", XC)
    logger.info(f"predict cross-check: {XC['n_checks']} checks, {XC['n_mismatches']} mismatches")
    logger.info("0d synthesis")
    O.item_0d(ed, A, GE, H)
    logger.info("0f top-five dose")
    F = Q.item_0f(ed)
    logger.info("0i U6 and D12")
    U = O.item_0i_u6_d12(ed)
    logger.info("0j Section 4.9")
    J = O.item_0j(ed, report6, report)
    logger.info("0l tags")
    L = O.item_0l(ed)
    logger.info("0e figure markers")
    figs = build_figs()
    for f in figs:
        ed.insert(f["insert_after"], "0e", f["marker_text"], values=[V(f"{f['fig_id']}|sha256_png",
                  list(f["sha256"].values())[0], None, tol="text", source=f["files"][0])],
                  section=f["section"], table=None, rationale=RATIONALE["0e"])
    # ---- judges (0i)
    import novelty as N
    nov_path = WS / "results" / "novelty.json"
    if args.stages == "all" or not nov_path.exists():
        logger.info("0i judges: tests, nearest known, blind two-family adjudication")
        nov = N.adjudicate()
        write_json(nov_path, nov)
    else:
        nov = read_json(nov_path)
    old278, new278 = table278_row(nov)
    ed.whole(old278, "0i", "replace", new278, values=[V("engine_control|n_programs", nov["n_programs"], 3,
             source="art_lpQalcAXMGr1:data/samples.jsonl"), V("engine_control|n_novel", nov["n_novel_final"], None)],
             section="6.9", table="Table 278", rationale=RATIONALE["0i"])
    # ---- positioning (0k)
    from positioning_assemble import assemble
    pos = assemble(run_web=(args.stages == "all"))
    write_json(WS / "positioning.json", pos)
    anchor, row = positioning_row(pos, GE)
    # venues and versions the plan expected, against what the live records show (the live record wins)
    plan_venue = {"forking_paths": "ICLR 2025", "forking_fast": "NeurIPS 2026 virtual page",
                  "hanna_ameisen": "ICLR 2026", "nainani": "no venue (arXiv preprint)", "ma_rui": "ICML 2026",
                  "jacopin": "no venue (arXiv preprint)"}
    kv = []
    for k, v in pos["neighbours"].items():
        found = v.get("venue_found") or ("no NeurIPS 2026 paper page found" if k == "forking_fast"
                                         else "no venue (arXiv preprint)")
        kv.append(V(f"venue|{k}", found, plan_venue[k], tol="text", source=f"arXiv {v['arxiv']} abstract page"
                    + (f"; {v['venue_evidence']}" if v.get("venue_evidence") else "")))
        kv.append(V(f"quote|{k}", v.get("quote_status"), None, tol="text", source=f"arXiv {v['arxiv']}"))
    seed_abs = (WS / "audit" / "web" / "abs_2604.09921.txt")
    if seed_abs.exists():
        import re as _re
        com = _re.search(r"Comments:\s*\|\s*(.+?)\s*---", seed_abs.read_text())
        found = "COLM (arXiv v2 comment)" if com and "COLM" in com.group(1) else (com.group(1) if com else "not found")
        kv.append(V("venue|seed_2604.09921", found, "ICML 2026", tol="text", source="arXiv 2604.09921 abstract page"))
    seed_abs = (WS / "audit" / "web" / "abs_2510.01218.txt")
    if seed_abs.exists():
        txt = seed_abs.read_text()
        kv.append(V("venue|seed_2510.01218", "COLM 2025" if "Conference on Language Modeling, 2025" in txt else "not found",
                    "COLM 2025", tol="text", source="arXiv 2510.01218 abstract page"))
    ed.insert(anchor, "0k", row, values=kv, section="6.7", table="Table 277", rationale=RATIONALE["0k"])
    ed.flush(RATIONALE)
    if ed.problems:
        for p in ed.problems:
            logger.error(f"editor problem: {p}")
    corr = reg.as_dicts()
    # ---- apply test, diff, lint, ledger, consistency
    corrected, apply_res = apply_all(report, corr)
    (WS / "report_corrected.md").write_text(corrected)
    (WS / "report.diff").write_text(unified_diff(report, corrected))
    lint_before, lint_after = lint(report), lint(corrected)
    changed_lines = {c["line_at_read"]: c["id"] for c in corr if c["line_at_read"]}
    ledger = Q.occurrence_ledger(report, changed_lines)
    cons = {"row_has_readable_across_prompts": "readable across prompts" in row,
            "row_has_next_token_qualifier": "next-token readout" in row}
    cons["passed"] = (not cons["row_has_readable_across_prompts"]) and cons["row_has_next_token_qualifier"]
    # ---- statuses
    all_vals = []
    for c in corr:
        all_vals += c["values"]
    for blk in (A["values"], B["values"], G8["values"], GE["values"], H["values"], F["values"], U["values"], J["values"]):
        all_vals += blk
    seen, uniq = set(), []
    for v in all_vals:
        key = (v["name"], v["source"], json.dumps(v["recomputed"], default=str))
        if key not in seen:
            seen.add(key)
            uniq.append(v)
    all_vals = uniq
    by_status = {}
    for v in all_vals:
        by_status[v["status"]] = by_status.get(v["status"], 0) + 1
    discrepancies = A["discrepancies"] + G8["discrepancies"] + [
        {k: v[k] for k in ("name", "recorded", "recomputed", "source")} for v in all_vals if v["status"] == "CORRECTED"]
    write_json(WS / "corrections.json", {"read_date": READ_DATE, "report_sha256": sha256_file(INPUTS / "report" /
               "current_report.md"), "n": len(corr), "corrections": corr, "apply_test": apply_res,
               "editor_problems": ed.problems})
    write_json(WS / "figure_markers.json", figs)
    write_json(WS / "results" / "values_ledger.json", all_vals)
    write_json(WS / "results" / "items.json", {
        "0a": {"cells": A["cells"], "mr_posthoc": A["mr_posthoc"], "commit0": A["commit0"]},
        "0b": {k: v for k, v in B.items() if k != "values"}, "0c": {k: v for k, v in GE.items() if k != "values"},
        "0f": {k: v for k, v in F.items() if k != "values"}, "0g": {k: v for k, v in G8.items() if k != "values"},
        "0h": {k: v for k, v in H.items() if k not in ("values", "rows", "units")}, "0i": U, "0j": J, "0l": L,
        "predict_crosscheck": {k: v for k, v in XC.items() if k != "checks"},
        "lint_before": lint_before, "lint_after": lint_after, "consistency_0k": cons})
    TABLES.mkdir(exist_ok=True)
    with (TABLES / "stage_a_cells.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["task", "cell", "Y", "n", "attempted_Y", "correct_Y", "Y_share", "Y_cp_lo", "Y_cp_hi",
                    "correct_Y_share", "correct_cp_lo", "correct_cp_hi", "transfer_commit0", "pass", "pass_ratio",
                    "gate_ok"])
        for k, c in sorted(A["cells"].items()):
            w.writerow([c["task"], c["cell"], c["Y"], c["n"], c["attempted_Y"], c["correct_Y"], f"{c['Y_share']:.4f}",
                        f"{c['Y_ci95_cp'][0]:.4f}", f"{c['Y_ci95_cp'][1]:.4f}", f"{c['correct_Y_share']:.4f}",
                        f"{c['correct_Y_ci95_cp'][0]:.4f}", f"{c['correct_Y_ci95_cp'][1]:.4f}",
                        f"{c.get('transfer', float('nan')):.4f}", f"{c['pass']:.4f}",
                        "" if c.get("pass_ratio") is None else f"{c['pass_ratio']:.4f}", c.get("gate_ok")])
    with (TABLES / "table238_correct_only.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["engine", "task", "arm", "n", "valid", "correct", "off_default", "correct_off_default"])
        for k, a in sorted(G8["pn_correct"].items()):
            e, t, arm = k.split("|")
            w.writerow([e, t, arm, a["n"], a["valid"], a["correct"], a["off"], a["correct_off"]])
    with (TABLES / "nla_one_unit_per_sample.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(H["rows"][0].keys()))
        w.writeheader()
        w.writerows(H["rows"])
    with (TABLES / "corrections_index.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "item", "also_items", "section", "table", "line_at_read", "kind", "n_values"])
        for c in corr:
            w.writerow([c["id"], c["item"], "+".join(c["also_items"]), c["section"], c["table"], c["line_at_read"],
                        c["kind"], len(c["values"])])
    with (TABLES / "lint.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["report", "line", "rule", "snippet"])
        for nm, hits in (("uncorrected", lint_before), ("corrected", lint_after)):
            for h in hits:
                w.writerow([nm, h["line"], h["rule"], h["snippet"]])
    # ---- audit (stdlib, independent)
    logger.info("audit: independent stdlib re-derivation with placebos")
    p = subprocess.run([sys.executable, str(WS / "audit" / "rederive.py")], capture_output=True, text=True, timeout=1800)
    logger.info(p.stdout[-1500:])
    if p.returncode:
        logger.error(p.stderr[-3000:])
    audit = read_json(AUDIT / "rederive_report.json") if (AUDIT / "rederive_report.json").exists() else {}
    logger.info("headline check: a short, separate stdlib re-derivation of every headline number, with placebos")
    p = subprocess.run([sys.executable, "-I", str(WS / "audit" / "headline_check.py")], capture_output=True, text=True,
                       timeout=1800)
    logger.info(p.stdout[-800:])
    if p.returncode:
        logger.error(p.stderr[-3000:])
    HC = read_json(AUDIT / "headline_check.json") if (AUDIT / "headline_check.json").exists() else {}
    # ---- eval_out.json
    from outputs import write_outputs
    write_outputs(ws=WS, corr=corr, apply_res=apply_res, by_status=by_status, lint_before=lint_before,
                  lint_after=lint_after, A=A, B=B, GE=GE, G8=G8, H=H, U=U, nov=nov, figs=figs, pos=pos, audit=audit,
                  hashes=hashes, discrepancies=discrepancies, cons=cons, J=J, F=F, L=L, ledger=ledger, XC=XC, HC=HC,
                  cpu_secs=time.process_time() - cpu0, wall_secs=time.time() - t_start)
    logger.info(f"done: {len(corr)} corrections, apply {apply_res['n_pass']}/{apply_res['n']}, lint "
                f"{len(lint_before)} -> {len(lint_after)}, statuses {by_status}")


if __name__ == "__main__":
    main()
