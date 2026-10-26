#!/usr/bin/env python3
"""5e combine: label = runtime if runtime == AST and neither is unknown/inconsistent ('agree'); otherwise the blind
judge's label ('judge'); if no judge label is available (budget refusal / cap), the runtime label, else the AST
label, else 'other' ('fallback_no_judge')."""

from __future__ import annotations

from typing import Any

UNRESOLVED = ("unknown", "inconsistent", None)


def needs_judge(runtime_label: str | None, ast_label: str | None) -> bool:
    return not (runtime_label == ast_label and runtime_label not in UNRESOLVED)


def combine(runtime_label: str | None, ast_label: str | None, judge: dict[str, Any] | None) -> tuple[str, str]:
    if not needs_judge(runtime_label, ast_label):
        return str(runtime_label), "agree"
    if judge is not None and judge.get("label"):
        return str(judge["label"]), "judge"
    if runtime_label not in UNRESOLVED:
        return str(runtime_label), "fallback_no_judge"
    if ast_label not in UNRESOLVED:
        return str(ast_label), "fallback_no_judge"
    return "other", "fallback_no_judge"
