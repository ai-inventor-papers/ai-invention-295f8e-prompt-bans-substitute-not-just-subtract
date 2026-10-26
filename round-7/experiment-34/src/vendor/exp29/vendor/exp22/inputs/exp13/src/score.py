#!/usr/bin/env python3
"""Frozen scoring rules (committed before the first ban sample).

Outcome space of a modal-ban event: S = catalogue minus the banned default D, plus 'other'.
Smoothing (one rule for every family): p = 0.93 * p_raw + 0.05 * Uniform(S) + 0.02 * delta_other, where p_raw is a
distribution over S plus 'other'.  Point forecasts are delta masses; an undefined forecast has p_raw = Uniform(S)
and is flagged.  Top-1 = argmax over S of p_raw (ties to catalogue order, flagged); undefined -> None.
Log score = mean over the ban's non-banned attempts of ln p(label) (natural log).
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

SMOOTH_RAW, SMOOTH_UNIF, SMOOTH_OTHER = 0.93, 0.05, 0.02
PRIMARY = ["SUBTRACT", "LADDER", "ASSOCIATE", "PROXIMITY"]
DESCRIPTIVE = ["SUBTRACT_1SHOT", "FRLP_FP8", "UNIFORM"]


def space(S: list[str]) -> list[str]:
    return list(S) + ["other"]


def p_from_counts(counts: dict[str, float], S: list[str]) -> dict[str, float] | None:
    """Normalise landing counts over S plus 'other' (labels outside the space are ignored); None if empty."""
    tot = sum(v for k, v in counts.items() if k in S or k == "other")
    if tot <= 0:
        return None
    return {k: counts.get(k, 0) / tot for k in space(S)}


def p_point(nominee: str | None, S: list[str]) -> dict[str, float] | None:
    if nominee is None or nominee not in S:
        return None
    return {k: float(k == nominee) for k in space(S)}


def p_uniform(S: list[str]) -> dict[str, float]:
    return {k: (1.0 / len(S) if k in S else 0.0) for k in space(S)}


def smooth(p_raw: dict[str, float] | None, S: list[str]) -> dict[str, float]:
    raw = p_raw if p_raw is not None else p_uniform(S)
    out = {}
    for k in space(S):
        out[k] = SMOOTH_RAW * raw.get(k, 0.0) + SMOOTH_UNIF * (1.0 / len(S) if k in S else 0.0) + \
            SMOOTH_OTHER * (1.0 if k == "other" else 0.0)
    return out


def top1(p_raw: dict[str, float] | None, S: list[str]) -> tuple[str | None, bool]:
    """argmax over S of p_raw; ties -> first in catalogue order (S is in catalogue order); returns (top1, tie_flag)."""
    if p_raw is None:
        return None, False
    best = max(p_raw.get(k, 0.0) for k in S)
    if best <= 0:
        return None, False
    tied = [k for k in S if abs(p_raw.get(k, 0.0) - best) < 1e-12]
    return tied[0], len(tied) > 1


def logscore(p: dict[str, float], labels: list[str]) -> float:
    if not labels:
        return float("nan")
    return sum(math.log(p[l]) for l in labels) / len(labels)


def realised_top1(labels: list[str], S: list[str]) -> list[str]:
    """Modal label over S plus 'other' (all tied labels listed)."""
    c = Counter(l for l in labels if l in S or l == "other")
    if not c:
        return []
    m = max(c.values())
    return [k for k in space(S) if c.get(k, 0) == m]


def hill1(labels: list[str]) -> float:
    c = Counter(labels)
    n = sum(c.values())
    if n == 0:
        return float("nan")
    return math.exp(-sum((v / n) * math.log(v / n) for v in c.values()))


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def js_divergence(p: dict[str, float], q: dict[str, float]) -> float:
    """Jensen-Shannon divergence, base 2."""
    keys = set(p) | set(q)
    m = {k: 0.5 * (p.get(k, 0.0) + q.get(k, 0.0)) for k in keys}

    def kl(a):
        return sum(a[k] * math.log2(a[k] / m[k]) for k in keys if a.get(k, 0.0) > 0)

    return 0.5 * kl({k: p.get(k, 0.0) for k in keys}) + 0.5 * kl({k: q.get(k, 0.0) for k in keys})


def advance(events: list[dict[str, Any]], families: list[str], margin: float = 0.10, min_wins: int = 3
            ) -> dict[str, Any]:
    """Family F wins an event if LS_F - max over the other families of LS >= margin; F advances with >= min_wins."""
    wins = {f: 0 for f in families}
    per_event = []
    for e in events:
        ls = e["logscore"]
        w = None
        for f in families:
            others = [ls[g] for g in families if g != f]
            if others and ls[f] - max(others) >= margin:
                wins[f] += 1
                w = f
        per_event.append({"task": e["task"], "winner": w})
    return {"wins": wins, "advancing": [f for f in families if wins[f] >= min_wins], "per_event": per_event}


def unit_tests() -> dict[str, bool]:
    S = ["a", "b", "c"]
    res = {}
    true = {"a": 0.7, "b": 0.2, "c": 0.1, "other": 0.0}
    labels = ["a"] * 7 + ["b"] * 2 + ["c"]
    res["true_beats_uniform"] = logscore(smooth(true, S), labels) > logscore(smooth(None, S), labels)
    for pr in [true, None, p_point("b", S), p_from_counts({"a": 3, "other": 1}, S)]:
        p = smooth(pr, S)
        res.setdefault("sums_to_one", True)
        res["sums_to_one"] &= abs(sum(p.values()) - 1) < 1e-12
        res.setdefault("other_at_least_002", True)
        res["other_at_least_002"] &= p["other"] >= 0.02 - 1e-12
    res["undefined_is_uniform"] = smooth(None, S) == smooth(p_uniform(S), S)
    res["tie_to_catalogue_order"] = top1({"a": 0.4, "b": 0.4, "c": 0.2, "other": 0}, S) == ("a", True)
    res["top1_ignores_other"] = top1({"a": 0.1, "b": 0.2, "c": 0.0, "other": 0.7}, S) == ("b", False)
    ev = [{"task": "x", "logscore": {"F": -0.1, "G": -0.5}}, {"task": "y", "logscore": {"F": -0.1, "G": -0.15}},
          {"task": "z", "logscore": {"F": -0.2, "G": -0.6}}, {"task": "w", "logscore": {"F": -0.2, "G": -0.6}}]
    a = advance(ev, ["F", "G"])
    res["advance_counts"] = a["wins"] == {"F": 3, "G": 0} and a["advancing"] == ["F"]
    res["js_zero_identical"] = abs(js_divergence({"a": 0.5, "b": 0.5}, {"a": 0.5, "b": 0.5})) < 1e-12
    res["js_one_disjoint"] = abs(js_divergence({"a": 1.0}, {"b": 1.0}) - 1.0) < 1e-12
    res["all_pass"] = all(res.values())
    return res


if __name__ == "__main__":
    print(unit_tests())
