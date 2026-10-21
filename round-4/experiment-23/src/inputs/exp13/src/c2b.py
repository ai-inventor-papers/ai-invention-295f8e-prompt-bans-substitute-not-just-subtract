#!/usr/bin/env python3
"""C2b (frozen): does the one-shot veto reproduce the ban's modal survivor, with a landing inside a template-
resampling null?

Eligible event: gated modal ban; one-shot avoidance >= 0.5; >= 10 attempts in S' = S minus CO_VETO plus 'other' in
both the veto and the ban.  Modal survivor over S' (ties -> catalogue order, flagged) for veto and ban: agree yes/no.
JS (base 2) between the two S' landings.  NULL: 2,000 seeded replicates; each draws two independent two-stage
bootstrap pseudo-landings from the ban's non-banned attempts, of sizes n_veto and n_ban; statistic = their JS;
threshold = 95th percentile.  Pseudo-landing of size m: draw 5 template slots with replacement from the templates
(W1-W5 that have >= 1 attempt in S'); split m evenly across the slots (remainder to randomly chosen slots); in each
slot draw that template's attempts with replacement.
REPRODUCES: modal agrees and JS <= p95.  LANDS ELSEWHERE: modal differs.  (Modal agrees but JS > p95: neither.)
VERDICT: CONFIRMED (reproducing >= 2/3 and elsewhere < 1/3); DISCONFIRMED (elsewhere >= 1/3 and reproducing < 2/3);
BOUNDARY (both bars met; no claim); INCONCLUSIVE (neither bar met: modal agreement without landing agreement);
UNDETERMINED (< 3 eligible events).
"""

from __future__ import annotations

import hashlib
from collections import Counter
from typing import Any

import numpy as np

from score import js_divergence


def dist(labels: list[str], space: list[str]) -> dict[str, float]:
    c = Counter(l for l in labels if l in space)
    n = sum(c.values())
    return {k: c.get(k, 0) / n for k in space} if n else {k: 0.0 for k in space}


def modal(labels: list[str], space: list[str]) -> tuple[str | None, bool]:
    c = Counter(l for l in labels if l in space)
    if not c:
        return None, False
    m = max(c.values())
    tied = [k for k in space if c.get(k, 0) == m]
    return tied[0], len(tied) > 1


def pseudo_landing(rng: np.random.Generator, by_t: dict[str, list[str]], m: int) -> list[str]:
    temps = sorted(w for w, v in by_t.items() if v)
    slots = rng.choice(len(temps), size=5, replace=True)
    sizes = np.full(5, m // 5)
    rem = m % 5
    if rem:
        sizes[rng.choice(5, size=rem, replace=False)] += 1
    out: list[str] = []
    for s, k in zip(slots, sizes):
        pool = by_t[temps[s]]
        if k:
            out += [pool[i] for i in rng.integers(0, len(pool), size=int(k))]
    return out


def null_p95(by_t: dict[str, list[str]], n_veto: int, n_ban: int, space: list[str], seed: int, reps: int = 2000,
             q: float = 0.95) -> tuple[float, np.ndarray]:
    rng = np.random.default_rng(seed)
    vals = np.empty(reps)
    for i in range(reps):
        a = pseudo_landing(rng, by_t, n_veto)
        b = pseudo_landing(rng, by_t, n_ban)
        vals[i] = js_divergence(dist(a, space), dist(b, space))
    return float(np.quantile(vals, q)), vals


def event_seed(base: int, task: str, tag: str) -> int:
    return int(hashlib.sha256(f"{base}|{task}|{tag}".encode()).hexdigest()[:8], 16)


def c2b_event(task: str, veto_labels: list[str], ban_by_template: dict[str, list[str]], space: list[str],
              seed: int, reps: int = 2000) -> dict[str, Any]:
    """veto_labels / ban_by_template: non-banned attempted labels already mapped into S plus 'other'."""
    v = [l for l in veto_labels if l in space]
    bt = {w: [l for l in ls if l in space] for w, ls in ban_by_template.items()}
    b = [l for ls in bt.values() for l in ls]
    mv, tv = modal(v, space)
    mb, tb = modal(b, space)
    js = js_divergence(dist(v, space), dist(b, space))
    p95, _ = null_p95(bt, len(v), len(b), space, seed, reps)
    agree = mv is not None and mv == mb
    return {"task": task, "n_veto": len(v), "n_ban": len(b), "modal_veto": mv, "modal_ban": mb,
            "modal_tie_veto": tv, "modal_tie_ban": tb, "agree": agree, "js": js, "null_p95": p95,
            "reproduces": bool(agree and js <= p95), "elsewhere": bool(not agree),
            "veto_landing": dict(Counter(v)), "ban_landing": dict(Counter(b))}


def verdict(events: list[dict[str, Any]], min_events: int = 3, confirm: float = 2 / 3,
            elsewhere: float = 1 / 3) -> dict[str, Any]:
    n = len(events)
    if n < min_events:
        return {"verdict": "UNDETERMINED", "n_eligible": n}
    rep = sum(e["reproduces"] for e in events) / n
    els = sum(e["elsewhere"] for e in events) / n
    c_bar = rep >= confirm - 1e-12
    d_bar = els >= elsewhere - 1e-12
    if c_bar and d_bar:
        v = "BOUNDARY"
    elif c_bar:
        v = "CONFIRMED"
    elif d_bar:
        v = "DISCONFIRMED"
    else:
        v = "INCONCLUSIVE"
    return {"verdict": v, "n_eligible": n, "share_reproducing": rep, "share_elsewhere": els}


def unit_tests() -> dict[str, bool]:
    res = {}
    sp = ["a", "b", "other"]
    by_t = {w: ["a"] * 8 + ["b"] * 2 for w in ["W1", "W2", "W3", "W4", "W5"]}
    p1, _ = null_p95(by_t, 30, 60, sp, 7, reps=300)
    p2, _ = null_p95(by_t, 30, 60, sp, 7, reps=300)
    res["null_reproducible"] = p1 == p2
    e_same = c2b_event("x", ["a"] * 25 + ["b"] * 5, by_t, sp, 1, reps=300)
    res["reproduces_when_same"] = e_same["reproduces"]
    e_diff = c2b_event("y", ["b"] * 30, by_t, sp, 2, reps=300)
    res["elsewhere_when_different"] = e_diff["elsewhere"]
    mk = lambda r, e: {"reproduces": r, "elsewhere": e}
    res["confirmed"] = verdict([mk(True, False)] * 3)["verdict"] == "CONFIRMED"
    res["disconfirmed"] = verdict([mk(False, True)] * 2 + [mk(True, False)])["verdict"] == "DISCONFIRMED"
    res["boundary"] = verdict([mk(True, False)] * 2 + [mk(False, True)])["verdict"] == "BOUNDARY"
    res["inconclusive"] = verdict([mk(False, False)] * 2 + [mk(True, False)])["verdict"] == "INCONCLUSIVE"
    res["undetermined"] = verdict([mk(True, False)] * 2)["verdict"] == "UNDETERMINED"
    res["all_pass"] = all(res.values())
    return res


if __name__ == "__main__":
    print(unit_tests())
