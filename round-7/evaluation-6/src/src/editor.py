"""Collects edits per paragraph so that no two corrections overlap, then emits one correction per paragraph.

Paragraph edits (`sub`) are exact substring replacements inside one report line (a paragraph or list item); every
old substring must occur exactly once in that line. The correction's old_text is the whole line copied from the
vendored report, and its new_text is that line with every sub applied and the marker appended once.
"""

from __future__ import annotations

import re
from typing import Any

from common import MARK
from corrections import Registry


class Editor:
    def __init__(self, report: str, reg: Registry):
        self.report = report
        self.lines = report.split("\n")
        self.reg = reg
        self.par: dict[str, dict[str, Any]] = {}
        self.order: list[str] = []
        self.problems: list[str] = []

    def _line(self, prefix: str) -> str:
        hits = [l for l in self.lines if l.startswith(prefix)]
        if len(hits) != 1:
            raise ValueError(f"paragraph prefix not unique ({len(hits)}): {prefix[:80]}")
        return hits[0]

    def section_of(self, text: str) -> str:
        i = self.report.find(text)
        head = [m for m in re.finditer(r"^(#{1,3}) (\d+(?:\.\d+)*|What we have learned so far)", self.report, re.M)
                if m.start() <= i]
        return head[-1].group(2) if head else "?"

    def sub(self, prefix: str, item: str, old: str, new: str, values: list[dict] | None = None) -> None:
        if prefix not in self.par:
            self.par[prefix] = {"line": self._line(prefix), "subs": [], "items": [], "values": []}
            self.order.append(prefix)
        p = self.par[prefix]
        if p["line"].count(old) != 1:
            self.problems.append(f"sub not unique in paragraph ({p['line'].count(old)}): {old[:90]}")
            return
        p["subs"].append((old, new))
        if item not in p["items"]:
            p["items"].append(item)
        p["values"] += values or []

    def whole(self, old_block: str, item: str, kind: str, new_block: str, *, values: list[dict], section: str,
              table: str | None, rationale: str) -> None:
        self.reg.add(item=item, section=section, kind=kind, old_text=old_block, new_text=new_block, values=values,
                     rationale=rationale, table=table)

    def insert(self, anchor: str, item: str, block: str, *, values: list[dict], section: str, table: str | None,
               rationale: str) -> None:
        if self.report.count(anchor) != 1:
            self.problems.append(f"insert anchor not unique ({self.report.count(anchor)}): {anchor[:90]}")
            return
        self.reg.add(item=item, section=section, kind="insert_after", old_text=anchor, new_text=block,
                     values=values, rationale=rationale, table=table)

    def flush(self, rationale: dict[str, str]) -> None:
        for prefix in self.order:
            p = self.par[prefix]
            new = p["line"]
            for old, rep in p["subs"]:
                new = new.replace(old, rep, 1)
            if MARK not in new:
                new = new.rstrip() + " " + MARK
            items = p["items"]
            self.reg.add(item=items[0], also_items=items[1:], section=self.section_of(p["line"]), kind="replace",
                         old_text=p["line"], new_text=new, values=p["values"],
                         rationale="; ".join(rationale.get(i, i) for i in items))
