#!/usr/bin/env python3
"""Shared analysis helpers: merged sample rows, behaviour shares, exact paired tests, Holm, bootstraps."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

import numpy as np
from scipy.stats import binom

from cfg import DATA_DIR, DEFAULT, read_jsonl, wilson_ci

RAW = DATA_DIR / "samples_raw.jsonl"
LABELS = DATA_DIR / "labels.jsonl"
NOT_ATTEMPTED = ("invalid", "disputed")


def merged(drop_text: bool = True) -> list[dict[str, Any]]:
    labs = {r["key"]: r for r in read_jsonl(LABELS)}
    out = []
    for r in read_jsonl(RAW):
        k = f"{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}"
        l = labs.get(k)
        row = {kk: vv for kk, vv in r.items() if not (drop_text and kk in ("text", "token_ids"))}
        row["key"] = k
        if l is not None:
            for f in ("label", "labeller_source", "passed", "valid", "runtime_label", "ast_label", "judge_label",
                      "fallback_label", "code_sha256"):
                row[f] = l.get(f)
            row["is_default"] = l["label"] == DEFAULT[r["task"]]
        out.append(row)
    return out


def rows_of(rows: list[dict[str, Any]], task: str, arm: str, ks: list[int] | None = None) -> list[dict[str, Any]]:
    return [r for r in rows if r["task"] == task and r["arm"] == arm and "label" in r
            and (ks is None or int(r["sample_id"]) in ks)]


def shares(rows: list[dict[str, Any]], task: str, disputed_as_default: bool = False) -> dict[str, Any]:
    """Behaviour summary of a set of labelled rows of one task."""
    x = DEFAULT[task]
    labs = []
    for r in rows:
        l = r["label"]
        if l == "disputed" and disputed_as_default:
            l = x
        labs.append(l)
    att = [l for l in labs if l not in NOT_ATTEMPTED]
    n_att = len(att)
    n_def = sum(l == x for l in att)
    nondef = [l for l in att if l != x]
    land = Counter(nondef)
    corr = Counter(r["label"] for r in rows if r["label"] not in NOT_ATTEMPTED and r["label"] != x and r.get("passed"))
    n = len(rows)
    av = 1 - n_def / n_att if n_att else float("nan")
    lo, hi = wilson_ci(n_att - n_def, n_att) if n_att else (float("nan"), float("nan"))
    modal = land.most_common(1)[0][0] if land else None
    pc = np.array(list(corr.values()), float)
    hill_cc = float(math.exp(-(pc / pc.sum() * np.log(pc / pc.sum())).sum())) if pc.sum() > 0 else 0.0
    return {"n": n, "n_attempted": n_att, "n_default": n_def, "n_nondefault": len(nondef),
            "avoidance": av, "avoidance_ci95": [lo, hi], "default_share": (n_def / n_att) if n_att else float("nan"),
            "landing": dict(land.most_common()), "modal_nondefault": modal,
            "modal_nondefault_n": land.most_common(1)[0][1] if land else 0,
            "landing_correct_only": dict(corr.most_common()), "hill_cc": hill_cc,
            "pass_rate": float(np.mean([bool(r.get("passed")) for r in rows])) if n else float("nan"),
            "other_share": (sum(l == "other" for l in labs) / n) if n else float("nan"),
            "invalid_share": (sum(l == "invalid" for l in labs) / n) if n else float("nan"),
            "disputed_share": (sum(l == "disputed" for l in labs) / n) if n else float("nan")}


def by_slot(rows: list[dict[str, Any]]) -> dict[tuple[str, int], dict[str, Any]]:
    return {(r["template"], int(r["sample_id"])): r for r in rows}


def avoided(r: dict[str, Any]) -> int | None:
    """1 = attempted and non-default, 0 = default, None = not attempted (invalid / disputed)."""
    if r["label"] in NOT_ATTEMPTED:
        return None
    return int(r["label"] != DEFAULT[r["task"]])


def mcnemar_one_sided(a: list[int], b: list[int]) -> dict[str, Any]:
    """Exact one-sided McNemar on paired binary outcomes: H1 P(a=1,b=0) > P(a=0,b=1)."""
    n10 = sum(1 for x, y in zip(a, b) if x == 1 and y == 0)
    n01 = sum(1 for x, y in zip(a, b) if x == 0 and y == 1)
    n = n10 + n01
    p = float(binom.sf(n10 - 1, n, 0.5)) if n > 0 else 1.0
    return {"n10": n10, "n01": n01, "n_pairs": len(a), "p_one_sided": p}


def mcnemar_two_sided(a: list[int], b: list[int]) -> dict[str, Any]:
    n10 = sum(1 for x, y in zip(a, b) if x == 1 and y == 0)
    n01 = sum(1 for x, y in zip(a, b) if x == 0 and y == 1)
    n = n10 + n01
    p = float(min(1.0, 2 * binom.cdf(min(n10, n01), n, 0.5))) if n > 0 else 1.0
    return {"n10": n10, "n01": n01, "n_pairs": len(a), "p_two_sided": p}


def holm(ps: list[float]) -> list[float]:
    m = len(ps)
    order = np.argsort(ps)
    adj = [0.0] * m
    run = 0.0
    for rank, i in enumerate(order):
        v = min(1.0, (m - rank) * ps[i])
        run = max(run, v)
        adj[i] = run
    return adj


def paired(rows_a: list[dict[str, Any]], rows_b: list[dict[str, Any]], fn=avoided) -> tuple[list[int], list[int]]:
    A, B = by_slot(rows_a), by_slot(rows_b)
    xs, ys = [], []
    for s in sorted(set(A) & set(B)):
        x, y = fn(A[s]), fn(B[s])
        if x is None or y is None:
            continue
        xs.append(x)
        ys.append(y)
    return xs, ys


def boot_mean_diff(x: list[int], y: list[int], n_boot: int = 2000, seed: int = 0) -> tuple[float, list[float]]:
    x_, y_ = np.asarray(x, float), np.asarray(y, float)
    if len(x_) == 0:
        return float("nan"), [float("nan"), float("nan")]
    d = x_ - y_
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), (n_boot, len(d)))
    bs = d[idx].mean(1)
    return float(d.mean()), [float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))]


def js_divergence(p: dict[str, float], q: dict[str, float]) -> float:
    keys = sorted(set(p) | set(q))
    a = np.array([p.get(k, 0) for k in keys], float)
    b = np.array([q.get(k, 0) for k in keys], float)
    if a.sum() == 0 or b.sum() == 0:
        return float("nan")
    a /= a.sum()
    b /= b.sum()
    m = (a + b) / 2

    def kl(u, v):
        msk = u > 0
        return float((u[msk] * np.log2(u[msk] / v[msk])).sum())
    return 0.5 * kl(a, m) + 0.5 * kl(b, m)
