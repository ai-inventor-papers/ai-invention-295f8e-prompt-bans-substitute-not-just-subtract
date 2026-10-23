#!/usr/bin/env python3
"""Apply test (exact-once old_text, no overlapping spans, every new_text present after application, unified diff)
and the whole-report residual-claim lint L1-L10 with a reasoned allowlist."""
from __future__ import annotations

import difflib
import re
from typing import Any

MARK = "(iteration-9 correction)"
ITER8_START_HEADING = "# Iteration 8: temperature at the fork"
PREDICTION_LINE_PREFIX = "- *The top-five prohibition claim*"


# ================================================================================================ apply
def apply_edits(original: str, edits: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    problems: list[str] = []
    spans = []
    for e in edits:
        n = original.count(e["old_text"])
        if n != 1:
            problems.append(f"{e['id']}: old_text occurs {n} times")
            continue
        if len(e["old_text"]) < 40:
            problems.append(f"{e['id']}: old_text shorter than 40 characters")
        if MARK not in e["new_text"]:
            problems.append(f"{e['id']}: new_text lacks the iteration-9 marker")
        s = original.index(e["old_text"])
        spans.append((s, s + len(e["old_text"]), e))
    spans.sort(key=lambda t: t[0])
    for (s1, e1, a), (s2, e2, b) in zip(spans, spans[1:]):
        if s2 < e1:
            problems.append(f"overlap: {a['id']} [{s1},{e1}) and {b['id']} [{s2},{e2})")
    if problems:
        return original, {"apply_test_pass": False, "problems": problems, "n_edits": len(edits)}
    out, last = [], 0
    for s, e, ed in spans:
        out.append(original[last:s])
        out.append(ed["new_text"])
        last = e
    out.append(original[last:])
    corrected = "".join(out)
    missing = [e["id"] for e in edits if e["new_text"] not in corrected]
    gone = [e["id"] for e in edits if e["old_text"] in corrected and e["old_text"] not in e["new_text"]]
    ok = not missing and not gone
    return corrected, {"apply_test_pass": ok, "problems": [f"new_text missing: {m}" for m in missing] +
                       [f"old_text survives: {g}" for g in gone], "n_edits": len(edits),
                       "line_of_edit": {ed["id"]: original[:s].count("\n") + 1 for s, _, ed in spans}}


def unified_diff(a: str, b: str) -> str:
    return "".join(difflib.unified_diff(a.splitlines(keepends=True), b.splitlines(keepends=True),
                                        fromfile="inputs/report/current_report.md", tofile="report_corrected.md", n=1))


# ================================================================================================ lint
def paragraphs(text: str) -> list[dict[str, Any]]:
    """Blocks separated by blank lines; a '**Table N.**' caption block is merged with the table block after it."""
    lines = text.split("\n")
    blocks, cur, start = [], [], 0
    for i, l in enumerate(lines):
        if l.strip() == "":
            if cur:
                blocks.append({"start": start + 1, "text": "\n".join(cur)})
                cur = []
        else:
            if not cur:
                start = i
            cur.append(l)
    if cur:
        blocks.append({"start": start + 1, "text": "\n".join(cur)})
    merged = []
    for b in blocks:
        if merged and merged[-1]["text"].startswith("**Table") and b["text"].lstrip().startswith("|") and \
                "\n" not in merged[-1]["text"]:
            merged[-1] = {"start": merged[-1]["start"], "text": merged[-1]["text"] + "\n" + b["text"]}
        else:
            merged.append(b)
    heading = ""
    for b in merged:
        if b["text"].startswith("#"):
            heading = b["text"].split("\n")[0].lstrip("# ").strip()
        b["section"] = heading
    return merged


def sentences(par: str) -> list[tuple[int, str]]:
    out, pos = [], 0
    for m in re.finditer(r"[^.!?]*(?:\d\.\d[^.!?]*)*[.!?](?=\s|$)|[^.!?]+$", par):
        out.append((m.start(), m.group(0)))
        pos = m.end()
    return out or [(0, par)]


def _sent_split(par: str) -> list[tuple[int, str]]:
    """Split on '. ' boundaries that are not decimal points or abbreviations; keeps offsets."""
    res, last = [], 0
    for m in re.finditer(r"(?<=[a-z0-9)\]'\"*])[.;]\s+(?=[A-Z*(\[])|\n", par):
        res.append((last, par[last:m.end()]))
        last = m.end()
    res.append((last, par[last:]))
    return [r for r in res if r[1].strip()]


BFS_MARKERS = re.compile(r"5 correct|5 of 30|24 fail|24 of them fail|pass 0\.20|0\.20 against 0\.83|NO HANDLE")
COUNTS = re.compile(r"\d+ of \d+|\d+/\d+")


def lint(text: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    iter8_line = next((i + 1 for i, l in enumerate(text.split("\n")) if l.startswith(ITER8_START_HEADING)), 10 ** 9)
    s88 = next((i + 1 for i, l in enumerate(text.split("\n")) if l.startswith("## 8.8 ")), 10 ** 9)

    def add(pid: str, b: dict[str, Any], off: int, snippet: str) -> None:
        line = b["start"] + b["text"][:off].count("\n")
        hits.append({"pattern": pid, "line": line, "section": b["section"], "snippet": snippet[:240].replace("\n", " "),
                     "iteration8_text": line >= iter8_line})

    for b in paragraphs(text):
        t = b["text"]
        low = t.lower()
        # L1
        for m in re.finditer(r"same shape", t):
            w = t[max(0, m.start() - 300): m.end() + 300]
            if "circuit" in w or "Gemma" in w:
                add("L1", b, m.start(), t[max(0, m.start() - 120): m.end() + 80])
        # L2
        for m in re.finditer(r"in every sample", t):
            w = t[max(0, m.start() - 200): m.end() + 200]
            if "highest-entropy" in w:
                add("L2", b, m.start(), t[max(0, m.start() - 120): m.end() + 120])
        sents = _sent_split(t)
        for off, s in sents:
            sl = s.lower()
            # L3
            if "in both families" in s and re.search(r"handle|edit", sl) and re.search(r"move|writ", sl) and \
                    "NO HANDLE" not in t:
                add("L3", b, off, s)
            # L5
            if "0.004 bits" in s and not ("five Qwen3-8B and Gemma units" in s and "0.63" in s):
                add("L5", b, off, s)
            # L6
            if "highest-entropy position" in s and re.search(r"\bevery (sample|slot|unit|case)|all (slots|samples|units)",
                                                            s) and not COUNTS.search(s):
                add("L6", b, off, s)
            # L7
            if "min-p" in s and "block-start" in s and ("Gemma" in s or "Gemma" in t[:off]) and \
                    re.search(r"\bp \d", s) and "not run" not in s:
                add("L7", b, off, s)
        # L4
        if re.search(r"DAS|rank-4|block 22", t) and "DFS" in t and not BFS_MARKERS.search(t):
            for m in re.finditer(r"29 of 30|29/30", t):
                near = low[max(0, m.start() - 120): m.end() + 60]
                if "counting sort" in near or "top five" in near or "full-state" in near or "circuit" in near:
                    continue
                add("L4", b, m.start(), t[max(0, m.start() - 160): m.end() + 80])
        # L8 (8.8 to the end)
        if b["start"] >= s88 and re.search(r"\bopposite\b|farthest non-banned", low) and not re.search(
                r"alias|named", low):
            m = re.search(r"\bopposite\b|farthest non-banned", low)
            add("L8", b, m.start(), t[max(0, m.start() - 160): m.end() + 80])
        # L9
        if b["start"] >= iter8_line:
            for m in re.finditer(r"not its mean|not the base model's mean", t):
                if "Cantarero" not in t and "Sparse but Critical" not in t:
                    add("L9", b, m.start(), t[max(0, m.start() - 160): m.end() + 60])
        # L10
        if re.search(r"predict|\blaw\b", low) and re.search(r"five of six|5 of 6", low) and not (
                "flat" in low and "tempering" in low):
            m = re.search(r"five of six|5 of 6", low)
            add("L10", b, m.start(), t[max(0, m.start() - 160): m.end() + 80])
    return hits


def allow_reason(h: dict[str, Any], text_lines: list[str]) -> str | None:
    if not h["iteration8_text"]:
        return "pre-iteration-8 text: outside the iteration-8 record under review (earlier iterations were audited by " \
               "their own Step 0)"
    line = text_lines[h["line"] - 1] if h["line"] - 1 < len(text_lines) else ""
    if line.startswith(PREDICTION_LINE_PREFIX) or line.startswith("- *The circuit claim*") or \
            line.startswith("- *The temperature-law claim*") or line.startswith("- *The fork-dosing claim*"):
        return "iteration-8 prediction statement (8.1): records what was preregistered, not a result"
    return None


def lint_report(text: str) -> dict[str, Any]:
    hits = lint(text)
    lines = text.split("\n")
    allowed, live = [], []
    for h in hits:
        r = allow_reason(h, lines)
        (allowed if r else live).append({**h, "allow_reason": r})
    by = {}
    for h in hits:
        by.setdefault(h["pattern"], 0)
        by[h["pattern"]] += 1
    by_live = {}
    for h in live:
        by_live.setdefault(h["pattern"], 0)
        by_live[h["pattern"]] += 1
    return {"n_hits": len(hits), "by_pattern": by, "n_unallowed": len(live), "unallowed_by_pattern": by_live,
            "unallowed": live, "allowlisted": allowed}
