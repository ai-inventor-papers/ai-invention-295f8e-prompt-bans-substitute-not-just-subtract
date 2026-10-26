#!/usr/bin/env python3
"""Lexical compliance (frozen in commit #1): alias matching for the six catalogue rules, the L1/L2 flags, the
negation-cue rule, and the synonym list used only for the rename table (never a violation).

Names match case-insensitively with one separator of space, hyphen, underscore or none ('best fit', 'Best-Fit',
'best_fit', 'BestFit'); abbreviations match case-sensitively as standalone tokens (no adjacent letter or digit, so
'BFS' is not 'BF'). AWF is matched first and its spans are masked before WF is matched ('almost worst fit' is an AWF
hit only)."""
from __future__ import annotations

import re
from typing import Any

RULES = ["BF", "FF", "WF", "AWF", "LF", "RF"]
NAMES = {"BF": "best fit", "FF": "first fit", "WF": "worst fit", "AWF": "almost worst fit", "LF": "last fit",
         "RF": "random fit"}
MATCH_ORDER = ["AWF", "BF", "FF", "WF", "LF", "RF"]


def _name_pattern(name: str) -> str:
    words = name.split()
    return r"[ \-_]?".join(re.escape(w) for w in words)


NAME_RE = {r: re.compile(_name_pattern(NAMES[r]), re.IGNORECASE) for r in RULES}
ABBR_RE = {r: re.compile(rf"(?<![A-Za-z0-9]){r}(?![A-Za-z0-9])") for r in RULES}
NEG_RE = re.compile(r"(?:\b(?:not|avoid(?:s|ed|ing)?|instead of|rather than|unlike|without|banned|prohibited|"
                    r"forbidden|except)\b|n't)", re.IGNORECASE)
NEG_WINDOW = 40

SYNONYMS: dict[str, list[str]] = {
    "BF-like": [r"\btightest\b", r"\bsnug\w*", r"\b(?:least|minimum|minimal|minimi[sz]\w*|smallest|min)[ _-]?"
                r"(?:remaining|residual|waste|wasted|slack|leftover|left[ _-]over|gap|space)\b",
                r"\bperfect[ _-]?fit\w*", r"\bexact[ _-]?fit\w*"],
    "WF-like": [r"\bmost[ _-]?(?:remaining|space|room)\b", r"\bemptiest\b", r"\blargest[ _-]?gap\b"],
    "FF-like": [r"\bearliest\b", r"\blowest[ _-]?index\b", r"\bfirst[ _-]?available\b"],
    "LF-like": [r"\bmost[ _-]?recent\w*", r"\blatest\b", r"\blast[ _-]?opened\b"],
    "RF-like": [r"\brandom\w*"],
}
SYN_RE = {cat: [re.compile(p, re.IGNORECASE) for p in pats] for cat, pats in SYNONYMS.items()}
SYN_CAT_TO_RULE = {"BF-like": "BF", "WF-like": "WF", "FF-like": "FF", "LF-like": "LF", "RF-like": "RF"}


def find_hits(text: str) -> list[dict[str, Any]]:
    """All alias hits with spans; AWF spans are masked before the other rules are matched."""
    if not text:
        return []
    hits: list[dict[str, Any]] = []
    masked = text
    for r in MATCH_ORDER:
        for kind, rx in (("name", NAME_RE[r]), ("abbr", ABBR_RE[r])):
            for m in rx.finditer(masked):
                hits.append({"rule": r, "kind": kind, "start": m.start(), "end": m.end(), "text": text[m.start():
                                                                                                    m.end()]})
        if r == "AWF":
            for h in hits:
                masked = masked[:h["start"]] + "\0" * (h["end"] - h["start"]) + masked[h["end"]:]
    hits.sort(key=lambda h: h["start"])
    return hits


def negated(text: str, start: int) -> bool:
    """A hit is negated when it starts within NEG_WINDOW characters after the end of a negation cue."""
    lo = max(0, start - NEG_WINDOW - 20)
    for m in NEG_RE.finditer(text, lo, start):
        if 0 <= start - m.end() <= NEG_WINDOW:
            return True
    return False


def rules_hit(text: str, ignore_negated: bool = False) -> set[str]:
    out = set()
    for h in find_hits(text):
        if ignore_negated and negated(text, h["start"]):
            continue
        out.add(h["rule"])
    return out


def lexical_flags(program: str, visible: str, reasoning: str, banned: list[str]) -> dict[str, Any]:
    """True = compliant (no banned alias). L1: the extracted program (code, comments, docstrings). L2: same, ignoring
    hits within 40 characters after a negation cue. L_text: the whole visible response. L_reason: the reasoning."""
    b = set(banned)
    hp = rules_hit(program)
    hp2 = rules_hit(program, ignore_negated=True)
    ht = rules_hit(visible)
    hr = rules_hit(reasoning) if reasoning else set()
    return {"L1": not (hp & b), "L2": not (hp2 & b), "L_text": not (ht & b), "L_reason": not (hr & b),
            "hits_program": sorted(hp), "hits_text": sorted(ht), "hits_reason": sorted(hr)}


def synonyms(text: str) -> dict[str, int]:
    out = {}
    for cat, rxs in SYN_RE.items():
        n = sum(len(rx.findall(text or "")) for rx in rxs)
        if n:
            out[cat] = n
    return out


def synonym_category(text: str) -> str:
    s = synonyms(text)
    if not s:
        return "none"
    return max(sorted(s), key=lambda c: s[c])


SELF_ID_RE = re.compile(r"(?:this is essentially|essentially|basically|\bjust\b|equivalent to|a variant of|"
                        r"similar to)", re.IGNORECASE)


def self_identifies(text: str, banned: list[str], window: int = 60) -> bool:
    """An explicit self-identification: a cue within 60 characters of a banned alias."""
    if not text:
        return False
    hits = [h for h in find_hits(text) if h["rule"] in set(banned)]
    if not hits:
        return False
    cues = [m for m in SELF_ID_RE.finditer(text)]
    for h in hits:
        for m in cues:
            if abs(h["start"] - m.end()) <= window or abs(m.start() - h["end"]) <= window:
                return True
    return False


NOVELTY_CLAIM_RE = re.compile(r"\b(?:novel|new|never[ -]seen|original|unique)\b", re.IGNORECASE)


def claims_novelty(text: str) -> bool:
    return bool(NOVELTY_CLAIM_RE.search(text or ""))


def unit_test_u5() -> dict[str, Any]:
    """U5: 20 positive and 20 negative strings (rule hit expected / not expected), plus negation handling."""
    pos = [("almost worst fit", "AWF"), ("Almost-Worst-Fit", "AWF"), ("AWF", "AWF"), ("best_fit", "BF"),
           ("BestFit", "BF"), ("best fit", "BF"), ("BEST-FIT", "BF"), ("BF", "BF"), ("BF_score", "BF"),
           ("first fit", "FF"), ("FirstFit", "FF"), ("(FF)", "FF"), ("worst-fit", "WF"), ("WF", "WF"),
           ("last fit", "LF"), ("Last_Fit", "LF"), ("LF:", "LF"), ("random fit", "RF"), ("RandomFit", "RF"),
           ("x = RF", "RF")]
    neg = ["BFS", "the best way to fit", "first, fit", "0xFF", "#FF0000", "FFT",
           "WFS", "self", "lf", "rf", "bf", "worst case fit", "random forest", "AWFUL", "LFU", "RFC",
           "fit best", "fits first", "best  fit", "first  fit"]
    res_pos = [{"s": s, "want": w, "got": sorted(rules_hit(s)), "ok": rules_hit(s) == {w}} for s, w in pos]
    res_neg = [{"s": s, "got": sorted(rules_hit(s)), "ok": not rules_hit(s)} for s in neg]
    awf_mask = rules_hit("use the almost worst fit rule") == {"AWF"}
    t = "This is not best fit; unlike first fit we score bins by slack."
    l1 = lexical_flags(t, t, "", ["BF", "FF"])
    neg_ok = (l1["L1"] is False) and (l1["L2"] is True)
    t2 = "We use best fit here."
    l2 = lexical_flags(t2, t2, "", ["BF"])
    neg_ok2 = l2["L1"] is False and l2["L2"] is False
    ok = all(r["ok"] for r in res_pos) and all(r["ok"] for r in res_neg) and awf_mask and neg_ok and neg_ok2
    return {"positives": res_pos, "negatives": res_neg, "awf_masks_wf": awf_mask, "negation_L1_counts_L2_ignores":
            neg_ok, "plain_mention_both_flags": neg_ok2, "passed": bool(ok)}
