#!/usr/bin/env python3
"""Final labels = labeller output (data/labels.jsonl) merged with blind-judge adjudications of runtime/AST
disagreements (data/adjudications.jsonl): agree/one abstains -> labeller label; disagree -> majority of the judges
(gpt-4.1-mini, gemini-2.5-flash, deepseek tie-break), else 'disputed' (excluded from compositions, counted).
Also the shared cell statistics used by the escape rule and the instruments.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from cfg6 import DATA_DIR, EXCLUDE, LABELS, append_jsonl, read_jsonl

ADJ = DATA_DIR / "adjudications.jsonl"


def adjudications() -> dict[str, dict[str, Any]]:
    return {r["key"]: r for r in read_jsonl(ADJ)}


def final_label(l: dict[str, Any], adj: dict[str, dict[str, Any]]) -> str | None:
    if l.get("label") is not None:
        return l["label"]
    a = adj.get(l["key"])
    if a is None:
        return None          # pending adjudication
    return a["label"] if a.get("label") is not None else "disputed"


def load_final(units: Iterable[str] | None = None, pending_ok: bool = True) -> list[dict[str, Any]]:
    us = set(units) if units is not None else None
    adj = adjudications()
    out = []
    for l in read_jsonl(LABELS):
        if us is not None and l["unit"] not in us:
            continue
        if l.get("labeller_source") in ("assoc_alias_lexicon", "intent_text"):
            out.append(l)
            continue
        fl = final_label(l, adj)
        if fl is None and not pending_ok:
            continue
        out.append({**l, "final": fl})
    return out


def adjudicate_pending(units: Iterable[str] | None = None, workers: int = 12) -> int:
    """Adjudicate every runtime/AST disagreement not yet adjudicated (blind judges)."""
    from judge6 import adjudicate_many

    adj = adjudications()
    rows = [l for l in load_final(units) if l.get("final", "x") is None and l.get("code")]
    seen: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for l in rows:
        seen.setdefault((l["unit"], l["code_sha256"]), []).append(l)
    items = [(f"{u}|{sha}", u, ls[0]["code"]) for (u, sha), ls in seen.items()]
    if not items:
        return 0
    res = adjudicate_many(items, "disagreement", workers=workers)
    out = []
    for (u, sha), r in zip(seen, res):
        for l in seen[(u, sha)]:
            if l["key"] in adj:
                continue
            out.append({"key": l["key"], "unit": u, "code_sha256": sha, "label": r["label"], "how": r["how"],
                        "judge_a": r["judge_a"], "judge_b": r["judge_b"], "judge_c": r["judge_c"],
                        "runtime_label": l.get("runtime_label"), "ast_label": l.get("ast_label")})
    append_jsonl(ADJ, out)
    return len(out)


def cell_stats(rows: list[dict[str, Any]], default: str | None, catalogue: list[str]) -> dict[str, Any]:
    """attempts = rows minus 'disputed'; pass rate = passed / attempts; off-default share = correct non-default
    CATALOGUE programs / attempts; 'invalid' rows count as failed attempts."""
    rs = [r for r in rows if r.get("final") != "disputed"]
    n = len(rs)
    passed = sum(1 for r in rs if r.get("passed"))
    off = [r for r in rs if r.get("passed") and r.get("final") in catalogue and r.get("final") != default]
    comp = Counter(r["final"] for r in rs if r.get("passed") and r.get("final") not in EXCLUDE)
    return {"n_rows": len(rows), "n_attempts": n, "n_disputed": len(rows) - n, "n_passed": passed,
            "pass_rate": passed / n if n else 0.0, "k_off": len(off), "off_share": len(off) / n if n else 0.0,
            "correct_comp": dict(comp), "pending": sum(1 for r in rows if r.get("final") is None)}
