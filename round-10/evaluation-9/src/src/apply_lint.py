#!/usr/bin/env python3
"""S-8: build the corrections, apply them to a copy of the report, and prove them.

Apply test: every old_text occurs once in the original; spans do not overlap; edits are applied back to front;
every new_text occurs once in report_corrected.md; outside the edited spans the corrected report equals the original
byte for byte; report.diff is a unified diff.
GRIM check: every rate stated with its k and n in a new_text equals round(k/n, 2) (half up).
Residual-claim lint: case-insensitive, per sentence (prose) or per row (tables; the described-ban rule reads a table
as one unit, because its readings sit in separate rows). Every rule must hit at least once on the original (positive
control) and zero times on the corrected copy; a rule with no instance in the original is shown firing on a planted
sentence instead, and is reported as such.
"""

from __future__ import annotations

import csv
import difflib
import re
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Callable

from loguru import logger

from edits_build import REPORT, TAG, build
from io_util import ROOT, TABLES, save_stage, sha256_file, write_json

SCOPE_START = "# Iteration 9: names against mechanisms"
SCOPE_END = "\n# References"


def units(text: str) -> list[tuple[str, str, str]]:
    """(kind, unit, block) for the scoped text: prose sentences, table rows, whole tables."""
    out = []
    for block in re.split(r"\n\s*\n", text):
        b = block.strip()
        if not b:
            continue
        if b.startswith("|"):
            rows = [r for r in b.split("\n") if r.startswith("|")]
            for r in rows:
                out.append(("row", r, b))
            out.append(("table", b, b))
        else:
            for s in re.split(r"(?<=[.!?])\s+(?=[A-Z*(\[\"'])", b):
                out.append(("sentence", s, b))
    return out


def _no_intervals(s: str) -> str:
    """Drop parenthesised confidence intervals such as '(-0.12 to 0.22)' before matching a stated value."""
    return re.sub(r"\(-?\d+\.\d+ to -?\d+\.\d+\)", "()", s)


def _has(s: str, w: str) -> bool:
    return w.lower() in s.lower()


RULES: list[tuple[str, str, Callable[[str, str, str], bool]]] = [
    ("R01", "'moves compliance to the names'", lambda k, u, b: k != "table" and _has(u, "moves compliance to the names")),
    ("R02", "'mostly not renamed BFS' without 'hand reads'",
     lambda k, u, b: k != "table" and _has(u, "mostly not renamed bfs") and not _has(u, "hand reads")),
    ("R03", "'to 0.22' in an exhaustion sentence without 'runtime label'",
     lambda k, u, b: k != "table" and re.search(r"(?<![\d.])\bto 0\.22\b", _no_intervals(u)) is not None
     and re.search(r"compliance|five names|at five", u, re.I) is not None and not _has(u, "runtime label")),
    ("R04", "'0.58' or 'to 0.80' in a described-ban sentence without '-0.07'",
     lambda k, u, b: k in ("sentence", "table") and _has(b, "described") and
     (re.search(r"(?<![\d.])0\.58\b", u) is not None or _has(u, "to 0.80")) and "-0.07" not in u
     and not (k == "table" and "gpt-oss" in u.lower())),
    ("R05", "'within algorithms the relation vanishes'",
     lambda k, u, b: k != "table" and _has(u, "within algorithms the relation vanishes")),
    ("R06", "'half its pair values'", lambda k, u, b: k != "table" and _has(u, "half its pair values")),
    ("R07", "'about half its pair-prompt effect'", lambda k, u, b: k != "table" and _has(u, "about half its pair-prompt effect")),
    ("R08", "'read by runtime expansion order'", lambda k, u, b: k != "table" and _has(u, "read by runtime expansion order")),
    ("R09", "'audits by runtime expansion order'", lambda k, u, b: k != "table" and _has(u, "audits by runtime expansion order")),
    ("R10", "'Seven of 280'", lambda k, u, b: k != "table" and _has(u, "seven of 280")),
    ("R11", "'programs at 0.17' without '0.167'",
     lambda k, u, b: k != "table" and _has(u, "programs at 0.17") and "0.167" not in u),
    ("R12", "'track lexical distance' without 'data-structure'",
     lambda k, u, b: k != "table" and _has(u, "track lexical distance") and not _has(u, "data-structure")),
    ("R13", "'all 15 survivors place at the edge' without '10 of 15'",
     lambda k, u, b: k != "table" and _has(u, "all 15 survivors place at the edge") and "10 of 15" not in u),
    ("R14", "'under all three readings' or 'under every reading' about Qwen3-14B without 'fine'",
     lambda k, u, b: k != "table" and (_has(u, "under all three readings") or _has(u, "under every reading"))
     and _has(u, "qwen3-14b") and not _has(u, "fine")),
    ("R15", "'no search ran' not scoped to iteration 9",
     lambda k, u, b: k != "table" and _has(u, "no search ran") and not _has(u, "iteration 9")),
]
PLANTED = {"R14": "Qwen3-14B meets the committed bar under all three readings.",
           "R15": "No search ran, so the question stays open."}


def scoped(text: str) -> str:
    i = text.index(SCOPE_START)
    j = text.index(SCOPE_END, i)
    return text[i:j]


def lint(text: str) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {rid: [] for rid, _, _ in RULES}
    for k, u, b in units(scoped(text)):
        for rid, _, fn in RULES:
            if fn(k, u, b):
                hits[rid].append(u[:300])
    return hits


def _half_up(x: float) -> str:
    return str(Decimal(repr(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


GRIM_PATTERNS = [
    (re.compile(r"(?<![\d.])(\d+) of (\d+) = (\d\.\d\d)(?!\d)"), (0, 1, 2)),
    (re.compile(r"(?<![\d.])(\d+)/(\d+) = (\d\.\d\d)(?!\d)"), (0, 1, 2)),
    (re.compile(r"(?<![\d.])(\d\.\d\d) \((\d+)/(\d+)\)"), (1, 2, 0)),
    (re.compile(r"(?<![\d.])(\d\.\d\d) \((\d+) of (\d+)\)"), (1, 2, 0)),
]


def grim(text: str) -> tuple[int, list[str]]:
    n = 0
    bad = []
    for rx, (ik, in_, ir) in GRIM_PATTERNS:
        for mt in rx.finditer(text):
            k, nn, rate = int(mt.group(ik + 1)), int(mt.group(in_ + 1)), mt.group(ir + 1)
            if nn == 0 or k > nn:
                continue
            n += 1
            if _half_up(k / nn) != rate:
                bad.append(f"{mt.group(0)} (k/n = {k / nn:.4f})")
    return n, bad


def run() -> dict[str, Any]:
    orig = REPORT.read_text()
    edits = build()
    # ---- apply test
    problems = []
    spans = []
    for ed in edits:
        c = orig.count(ed["old_text"])
        if c != 1:
            problems.append(f"{ed['id']}: old_text occurs {c} times")
            continue
        if TAG not in ed["new_text"]:
            problems.append(f"{ed['id']}: new_text lacks the tag")
        s = orig.index(ed["old_text"])
        spans.append((s, s + len(ed["old_text"]), ed))
    spans.sort(key=lambda x: x[0])
    for (s1, e1, a), (s2, e2, b) in zip(spans, spans[1:]):
        if s2 < e1:
            problems.append(f"overlap: {a['id']} and {b['id']}")
    corrected = orig
    for s, e_, ed in sorted(spans, key=lambda x: -x[0]):  # back to front
        corrected = corrected[:s] + ed["new_text"] + corrected[e_:]
    for ed in edits:
        c = corrected.count(ed["new_text"])
        if c != 1:
            problems.append(f"{ed['id']}: new_text occurs {c} times in the corrected report")
    # outside the edited spans: byte-identical
    pos_o = 0
    pos_c = 0
    outside_ok = True
    for s, e_, ed in spans:
        seg = orig[pos_o:s]
        if corrected[pos_c:pos_c + len(seg)] != seg:
            outside_ok = False
        pos_c += len(seg)
        if corrected[pos_c:pos_c + len(ed["new_text"])] != ed["new_text"]:
            outside_ok = False
        pos_c += len(ed["new_text"])
        pos_o = e_
    if corrected[pos_c:] != orig[pos_o:]:
        outside_ok = False
    if not outside_ok:
        problems.append("text outside the edited spans differs")
    (ROOT / "report_corrected.md").write_text(corrected)
    diff = list(difflib.unified_diff(orig.splitlines(keepends=True), corrected.splitlines(keepends=True),
                                     fromfile="inputs/report/current_report.md", tofile="report_corrected.md", n=1))
    (ROOT / "report.diff").write_text("".join(diff))
    diff_ok = bool(diff) and diff[0].startswith("--- ") and diff[1].startswith("+++ ") and any(
        ln.startswith("@@") for ln in diff)
    if not diff_ok:
        problems.append("report.diff is not a unified diff")
    apply_pass = not problems
    # ---- GRIM
    grim_n = 0
    grim_bad = []
    for ed in edits:
        n_, bad = grim(ed["new_text"])
        grim_n += n_
        grim_bad += [f"{ed['id']}: {x}" for x in bad]
    # ---- lint
    before = lint(orig)
    after = lint(corrected)
    planted = {rid: bool(fn("sentence", PLANTED[rid], PLANTED[rid])) for rid, _, fn in RULES if rid in PLANTED}
    rows_ = []
    lint_pass = True
    for rid, desc, _ in RULES:
        nb, na = len(before[rid]), len(after[rid])
        pc = "original" if nb > 0 else ("planted" if planted.get(rid) else "NONE")
        ok = na == 0 and pc != "NONE"
        lint_pass &= ok
        rows_.append([rid, desc, nb, na, pc, "PASS" if ok else "FAIL"])
    with open(TABLES / "lint_rules.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["rule", "description", "hits_original", "hits_corrected", "positive_control", "result"])
        w.writerows(rows_)
    # ---- outputs
    for ed in edits:
        ed["tag"] = TAG
    write_json(ROOT / "corrections.json", edits)
    status_counts = Counter(v["status"] for ed in edits for v in ed["values"])
    items = Counter(it for ed in edits for it in ed["items"])
    apply = {"apply_test_pass": apply_pass, "problems": problems, "n_edits": len(edits), "outside_identical": outside_ok,
             "diff_is_unified": diff_ok, "diff_lines": len(diff), "report_sha256": sha256_file(REPORT),
             "corrected_sha256": sha256_file(ROOT / "report_corrected.md"),
             "grim_checks": grim_n, "grim_failures": grim_bad, "lint": {r[0]: {"desc": r[1], "before": r[2], "after": r[3],
                                                                             "positive_control": r[4], "result": r[5]}
                                                                      for r in rows_},
             "lint_hits_before_examples": {k: v[:3] for k, v in before.items()},
             "lint_hits_after": {k: v for k, v in after.items() if v}, "lint_pass": lint_pass,
             "planted_controls": planted}
    write_json(ROOT / "results" / "apply_test.json", apply)
    metrics = {"n_edits": len(edits), "apply_test_pass": float(apply_pass), "grim_checks": grim_n,
               "grim_failures": len(grim_bad), "lint_pass": float(lint_pass),
               "lint_rules": len(RULES), "lint_hits_before_total": sum(r[2] for r in rows_),
               "lint_hits_after_total": sum(r[3] for r in rows_),
               **{f"edits_item_{k}": v for k, v in sorted(items.items())},
               **{f"values_{k}": v for k, v in sorted(status_counts.items())},
               **{f"lint_{r[0]}_before": r[2] for r in rows_}, **{f"lint_{r[0]}_after": r[3] for r in rows_}}
    ex = [{"input": ed["old_text"], "output": ed["new_text"], "metadata_id": ed["id"], "metadata_items": ed["items"],
           "metadata_location": ed["location"], "metadata_reason": ed["reason"], "metadata_n_values": len(ed["values"]),
           "metadata_value_status": dict(Counter(v["status"] for v in ed["values"])),
           "eval_applied_once": float(corrected.count(ed["new_text"]) == 1)} for ed in edits]
    save_stage("s8_edits", {"status": "DONE" if apply_pass and lint_pass and not grim_bad else "CHECK FAILED",
                            "apply": apply, "metrics": metrics, "examples": {"corrections": ex}})
    logger.info(f"edits {len(edits)}; apply {apply_pass}; lint {lint_pass}; grim {grim_n} checks, {len(grim_bad)} failures")
    if problems:
        logger.error(f"apply problems: {problems}")
    if grim_bad:
        logger.error(f"GRIM failures: {grim_bad}")
    for r in rows_:
        logger.info(f"lint {r[0]} before {r[2]} after {r[3]} control {r[4]} {r[5]}")
    return apply
