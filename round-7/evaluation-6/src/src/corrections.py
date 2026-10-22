"""A3/A4: the correction registry, value statuses, the apply test and the residual-claim lint (M1, M2).

A correction is {id 'C7-xx', item, section, table, line_at_read, kind, old_text, new_text, values, rationale}.
kind is replace | insert_after | table_replace. For insert_after, old_text is the unique anchor and the new text
is inserted after it (the stored new_text is the inserted block only). Every new_text carries the marker
'(iteration-7 correction)' exactly once. Numbers in new_text come from recomputed values by template.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from common import MARK

TOL = {"count": 0.0, "prop": 0.005, "effect": 0.01, "ci": 0.01, "p": None, "text": None, "ratio": 0.01}


def status_of(recorded: Any, recomputed: Any, tol: str) -> str:
    if recorded is None:
        return "NEW"
    if recomputed is None:
        return "CARRIED"
    if tol == "text":
        return "MATCH" if str(recorded) == str(recomputed) else "CORRECTED"
    if isinstance(recorded, (list, tuple)):
        ok = all(abs(float(a) - float(b)) <= TOL["ci"] + 1e-12 for a, b in zip(recorded, recomputed))
        return "MATCH" if ok and len(recorded) == len(recomputed) else "CORRECTED"
    r, c = float(recorded), float(recomputed)
    if tol == "p":
        if r < 1e-6 and c < 1e-6:
            return "MATCH"
        return "MATCH" if abs(r - c) <= 0.01 * max(abs(r), 1e-300) else "CORRECTED"
    return "MATCH" if abs(r - c) <= TOL[tol] + 1e-12 else "CORRECTED"


def V(name: str, recomputed: Any, recorded: Any = None, *, tol: str = "count", source: str = "",
      carried: bool = False, printed: Any = None) -> dict:
    st = "CARRIED" if carried else status_of(recorded, recomputed, tol)
    out = {"name": name, "recorded": recorded, "recomputed": recomputed, "status": st, "tolerance": tol,
           "source": source}
    if printed is not None:
        out["printed_in_report"] = printed
    return out


@dataclass
class Correction:
    id: str
    item: str
    section: str
    table: str | None
    line_at_read: int | None
    kind: str
    old_text: str
    new_text: str
    values: list[dict] = field(default_factory=list)
    rationale: str = ""
    also_items: list[str] = field(default_factory=list)


class Registry:
    def __init__(self, report: str):
        self.report = report
        self.items: list[Correction] = []
        self.discrepancies: list[dict] = []

    def line_of(self, text: str) -> int | None:
        i = self.report.find(text)
        return None if i < 0 else self.report.count("\n", 0, i) + 1

    def add(self, *, item: str, section: str, kind: str, old_text: str, new_text: str, values: list[dict],
            rationale: str, table: str | None = None, also_items: list[str] | None = None) -> Correction:
        assert kind in ("replace", "insert_after", "table_replace"), kind
        if MARK not in new_text:
            new_text = new_text.rstrip() + " " + MARK
        cid = f"C7-{len(self.items) + 1:02d}"
        c = Correction(id=cid, item=item, section=section, table=table, line_at_read=self.line_of(old_text),
                       kind=kind, old_text=old_text, new_text=new_text, values=values, rationale=rationale,
                       also_items=also_items or [])
        self.items.append(c)
        for v in values:
            if v["status"] == "CORRECTED":
                self.discrepancies.append({"correction": cid, **v})
        return c

    def as_dicts(self) -> list[dict]:
        return [asdict(c) for c in self.items]


def apply_all(report: str, corrections: list[dict]) -> tuple[str, dict]:
    """Apply in file order (by position of old_text in the uncorrected report) and check the contract."""
    checks = []
    for c in corrections:
        n = report.count(c["old_text"])
        checks.append({"id": c["id"], "old_found_exactly_once": n == 1, "n_found": n,
                       "marker_once": c["new_text"].count(MARK) == 1})
    # overlap check on spans in the uncorrected report
    spans = []
    for c in corrections:
        i = report.find(c["old_text"])
        if i >= 0:
            spans.append((i, i + len(c["old_text"]), c["id"]))
    spans.sort()
    overlaps = [(a[2], b[2]) for a, b in zip(spans, spans[1:]) if b[0] < a[1]]
    order = sorted(corrections, key=lambda c: report.find(c["old_text"]))
    out = report
    for c in order:
        if out.count(c["old_text"]) != 1:
            continue
        if c["kind"] == "insert_after":
            out = out.replace(c["old_text"], c["old_text"] + c["new_text"], 1)
        else:
            out = out.replace(c["old_text"], c["new_text"], 1)
    for ch in checks:
        c = next(x for x in corrections if x["id"] == ch["id"])
        ch["new_present_after"] = c["new_text"] in out
        ch["pass"] = ch["old_found_exactly_once"] and ch["new_present_after"] and ch["marker_once"]
    n_pass = sum(ch["pass"] for ch in checks)
    res = {"n": len(checks), "n_pass": n_pass, "pass_rate": n_pass / len(checks) if checks else None,
           "overlaps": overlaps, "checks": checks, "passed": n_pass == len(checks) and not overlaps}
    return out, res


def unified_diff(a: str, b: str) -> str:
    return "".join(difflib.unified_diff(a.splitlines(keepends=True), b.splitlines(keepends=True),
                                        fromfile="current_report.md", tofile="report_corrected.md", n=1))


# ---------------------------------------------------------------- M2: residual-claim lint
STAGEA_CTX = re.compile(r"exchang|Stage A|task-specification states|transfer", re.I)
STAGEA_NUM = re.compile(r"(?<![\d.])0\.(?:80|57|47|33|567|467|333)(?!\d)")
LINT = {
    "post_hoc_form_survives": re.compile(r"post-hoc form survives", re.I),
    "measured_in_three_models": re.compile(r"measured in three models", re.I),
    "in_all_three_read_position": re.compile(r"In all three (models )?the read position", re.I),
    "essentially_one_direction": re.compile(r"essentially one direction", re.I),
    "every_edit_pass_or_breaks": re.compile(r"every (fork )?edit[^.]{0,80}?(pass rate|breaks)", re.I),
    "post_hoc_ordering_noise_sites": re.compile(r"post-hoc ordering of noise sites", re.I),
}
TOP5 = re.compile(r"(top-five (direction|push)|activation version of the prohibition)[^.]*breaks programs before",
                  re.I)


def _sentences(par: str) -> list[str]:
    return re.split(r"(?<=[.;])\s+(?=[A-Z*(])", par)


def lint(text: str, start_line: int = 5497) -> list[dict]:
    """Flag leftover wrong claims in iteration-6 prose (Sections 6.4 to the closing). Table rows are skipped
    for the Stage A share check (their captions and columns carry the definitions)."""
    hits = []
    lines = text.splitlines()
    end = next((i for i, l in enumerate(lines) if l.startswith("# References")), len(lines))
    for ln in range(start_line - 1, end):
        line = lines[ln]
        if MARK in line and "*(Correction, iteration 6" not in line:
            pass
        for name, rx in LINT.items():
            for m in rx.finditer(line):
                hits.append({"line": ln + 1, "rule": name, "snippet": line[max(0, m.start() - 60):m.end() + 60]})
        for m in TOP5.finditer(line):
            a = line.rfind(". ", 0, m.start())
            b = line.find(".", m.end())
            seg = line[a + 1 if a >= 0 else 0: b + 1 if b > 0 else len(line)]
            if "ban unit" not in seg:
                hits.append({"line": ln + 1, "rule": "top5_without_ban_units", "snippet": seg[:200]})
        if line.startswith("|"):
            continue
        for s in _sentences(line):
            if STAGEA_NUM.search(s) and STAGEA_CTX.search(s) and "of 30" not in s and "Table" not in s[:12]:
                if re.search(r"noise|alpha|Spearman|odds ratio|escape", s, re.I):
                    continue
                hits.append({"line": ln + 1, "rule": "stageA_share_without_of_30", "snippet": s[:220]})
    return hits
