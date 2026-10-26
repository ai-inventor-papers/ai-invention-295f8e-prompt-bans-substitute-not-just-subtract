#!/usr/bin/env python3
"""STEP S0 (vendor inputs with sha256, resolve dependency paths, section index, residual-claim lint on the uncorrected
report) and STEP APPLY (each old_text occurs exactly once, no overlaps, applied in descending offset order; unified diff;
lint after; a one-character placebo mutation must make the apply test fail)."""

from __future__ import annotations

import difflib
import re
import shutil
from typing import Any

from loguru import logger

from sections.common import (ARTIFACTS, EVAL6_DIR, ITER7, REPORT, REPORT_SRC, ROOT, LINT_PHRASES, dep, lint, lint_total,
                             read_json, sha256_file, write_csv, write_json, TABLES)

USED_FILES = {
    "exp33": ["results/p1.json", "results/novelty_audit.json", "results/randinit_ly_T2.json", "results/randinit_T2.json",
              "results/dormant.json", "results/deviations.json", "results/m_manifold.json", "results/kstar_T2.json",
              "results/kstar_T10.json", "results/kstar_T03.json", "results/targets_T2.json", "results/targets_T10.json",
              "results/targets_T03.json", "results/site_T2.json", "results/site_T10.json", "results/site_T03.json",
              "results/c_routing.json", "data/labels.jsonl", "data/samples_raw.jsonl", "src/analysis7.py", "src/cfg7.py",
              "audit/rederive.py", "inputs/exp11/bench/T03_kth_smallest/gate.json",
              "inputs/exp11/bench/T03_kth_smallest/gold_set.jsonl"],
    "exp34": ["results/f_analysis.json", "results/p2_analysis.json", "README.md"],
    "exp35": ["results/posthoc.json", "results/test2.json"],
    "exp36": ["results/e3_replicate.json", "results/retag.json", "data/samples.jsonl"],
    "exp37": ["results/program_classes.json", "results/arm_rates.json", "results/ratio_tests.json", "results/L_vs_S.json"],
    "exp38": ["src/g2.py", "src/cfg.py", "results/g2_decisions.json", "data/raw_g2dose.jsonl", "README.md"],
}


def stage_s0() -> dict[str, Any]:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    if not REPORT.exists():
        shutil.copy2(REPORT_SRC, REPORT)
    EVAL6_DIR.mkdir(parents=True, exist_ok=True)
    for f in ("positioning.json", "report_corrected.md", "corrections.json"):
        if not (EVAL6_DIR / f).exists():
            shutil.copy2(dep("eval6", f), EVAL6_DIR / f)
    hashes = {"report": {"source": str(REPORT_SRC.relative_to(REPORT_SRC.parents[3])), "vendored": "inputs/report/current_report.md",
                         "sha256": sha256_file(REPORT), "source_sha256_now": sha256_file(REPORT_SRC) if REPORT_SRC.exists() else None},
              "eval6": {f: sha256_file(EVAL6_DIR / f) for f in ("positioning.json", "report_corrected.md", "corrections.json")},
              "dependencies": {}}
    resolved = {}
    for short, files in USED_FILES.items():
        aid = {v: k for k, v in __import__("sections.common", fromlist=["SHORT"]).SHORT.items()}[short]
        resolved[aid] = {"short": short, "path": f"ITER7/{ARTIFACTS[aid]}", "staged_dependency_root": False}
        hashes["dependencies"][aid] = {f: sha256_file(dep(short, f)) for f in files}
    resolved["art_LzP2qPwUrANz"] = {"short": "eval6", "path": f"ITER7/{ARTIFACTS['art_LzP2qPwUrANz']}", "read_by_absolute_path": True}
    resolved["ITER7"] = "../../../iter_7/gen_art relative to this folder (read-only; override with AII_ITER7_GEN_ART)"
    write_json(ROOT / "inputs" / "input_hashes.json", hashes)
    write_json(ROOT / "inputs" / "resolved_paths.json", resolved)
    text = REPORT.read_text()
    idx, cur = [], None
    for i, l in enumerate(text.split("\n"), 1):
        if l.startswith("#"):
            if cur:
                cur["end"] = i - 1
            cur = {"heading": l.strip("# ").strip(), "level": len(l) - len(l.lstrip("#")), "start": i}
            idx.append(cur)
    if cur:
        cur["end"] = len(text.split("\n"))
    write_json(ROOT / "results" / "section_index.json", idx)
    lb = lint(text)
    logger.info(f"S0: report sha {hashes['report']['sha256'][:12]}, {len(idx)} headings, lint before {lint_total(lb)}")
    return {"hashes": hashes, "lint_before": lb, "n_headings": len(idx)}


def _offsets(text: str, edits: list[dict[str, Any]]) -> tuple[bool, list[dict[str, Any]]]:
    probs, spans = [], []
    for e in edits:
        n = text.count(e["old_text"])
        if n != 1:
            probs.append({"id": e["id"], "problem": f"old_text occurs {n} times"})
            continue
        s = text.index(e["old_text"])
        spans.append((s, s + len(e["old_text"]), e["id"]))
        captioned = any(c["kind"] == "caption" and c["section"] == e["section"] for c in edits)
        if "iteration-8 correction" not in e["new_text"] and not (e["kind"].startswith("table_row") and captioned):
            probs.append({"id": e["id"], "problem": "new_text lacks the iteration-8 correction marker (and no caption edit of its table)"})
    spans.sort()
    for (a0, a1, ai), (b0, b1, bi) in zip(spans, spans[1:]):
        if b0 < a1:
            probs.append({"id": f"{ai}+{bi}", "problem": "overlapping spans"})
    return (not probs), probs


def apply_edits(text: str, edits: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    ok, probs = _offsets(text, edits)
    if not ok:
        return text, {"apply_test_pass": False, "problems": probs}
    order = sorted(edits, key=lambda e: text.index(e["old_text"]), reverse=True)
    out = text
    for e in order:
        s = out.index(e["old_text"])
        e["offset"] = s
        e["line_at_read"] = text[:text.index(e["old_text"])].count("\n") + 1
        out = out[:s] + e["new_text"] + out[s + len(e["old_text"]):]
    return out, {"apply_test_pass": True, "problems": [], "n_edits": len(edits)}


def stage_apply(edits: list[dict[str, Any]]) -> dict[str, Any]:
    text = REPORT.read_text()
    new, res = apply_edits(text, edits)
    if not res["apply_test_pass"]:
        logger.error(f"APPLY TEST FAILED: {res['problems']}")
        return {**res, "lint_after": None}
    (ROOT / "report_corrected.md").write_text(new)
    diff = difflib.unified_diff(text.split("\n"), new.split("\n"), "inputs/report/current_report.md", "report_corrected.md",
                                lineterm="", n=0)
    (ROOT / "report.diff").write_text("\n".join(diff) + "\n")
    la = lint(new)
    lb = lint(text)
    write_csv(TABLES / "lint.csv", [{"phrase": k, "before": lb[k]["count"], "lines_before": " ".join(map(str, lb[k]["lines"])),
                                     "after": la[k]["count"], "lines_after": " ".join(map(str, la[k]["lines"]))} for k in lb],
              ["phrase", "before", "lines_before", "after", "lines_after"])
    # placebo: one mutated character in one old_text must make the apply test fail
    import copy
    mut = copy.deepcopy(edits)
    j = max(range(len(mut)), key=lambda i: len(mut[i]["old_text"]))
    o = mut[j]["old_text"]
    k = len(o) // 2
    mut[j]["old_text"] = o[:k] + ("#" if o[k] != "#" else "@") + o[k + 1:]
    _, pres = apply_edits(text, mut)
    res.update({"lint_before": lint_total(lb), "lint_after": lint_total(la), "lint_after_detail": {k: v for k, v in la.items() if v["count"]},
                "placebo_mutation_fails": not pres["apply_test_pass"], "placebo_problems": pres["problems"][:3],
                "report_sha256_in": __import__("hashlib").sha256(text.encode()).hexdigest(),
                "report_sha256_out": __import__("hashlib").sha256(new.encode()).hexdigest(),
                "lines_in": text.count("\n") + 1, "lines_out": new.count("\n") + 1})
    logger.info(f"APPLY: {len(edits)} edits applied; lint {res['lint_before']} -> {res['lint_after']}; placebo fails: {res['placebo_mutation_fails']}")
    return res
