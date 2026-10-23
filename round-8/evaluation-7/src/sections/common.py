#!/usr/bin/env python3
"""Shared helpers of the iteration-8 record repair: paths, hashing, exact intervals and tests, average-rank Spearman,
fixed-seed bootstraps, the correction-record builder and the residual-claim lint. Written once (STEP S0) and imported
by every section module."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import os

ROOT = Path(__file__).resolve().parents[1]
# Inputs produced by other artifacts are read through ONE constant, DEP_ROOT: the folder that holds the iteration-7
# artifact folders (named by folder name, e.g. gen_art_experiment_33, or by artifact id, e.g. art_veI9l_Rb9wDY).
# Default: the run layout this was executed in (<run>/3_invention_loop/iter_7/gen_art, found relative to this folder);
# in the published repository each artifact is a sibling folder, so DEP_ROOT falls back to this folder's parent.
# Override with the environment variable AII_DEP_ROOT.
_RUN_LAYOUT = ROOT.parents[2] / "round-7" / "."
DEP_ROOT = Path(os.environ.get("AII_DEP_ROOT") or (_RUN_LAYOUT if _RUN_LAYOUT.exists() else ROOT.parent))
ITER7 = DEP_ROOT
# the report to correct is vendored in inputs/report/; the source below is only read if that copy is missing
REPORT_SRC = Path(os.environ.get("AII_REPORT_SRC", ROOT.parents[1] / "gen_strat" / "current_report.md"))
REPORT = ROOT / "inputs" / "report" / "current_report.md"
EVAL6_DIR = ROOT / "inputs" / "eval6"
BENCH_ROOT = ROOT / "inputs" / "bench_T03"
RESULTS = ROOT / "results"
TABLES = ROOT / "tables"
AUDIT = ROOT / "audit"
READ_DATE = "2026-10-23"

# artifact id -> folder name under ITER7 (declared dependencies plus the evaluation read by absolute path)
ARTIFACTS = {
    "art_veI9l_Rb9wDY": "gen_art_experiment_33",
    "art_pHL7LWNhpcCS": "gen_art_experiment_34",
    "art_MZAfDPVhM6Ui": "gen_art_experiment_35",
    "art_8O5eaNc5gxJs": "gen_art_experiment_36",
    "art_VhaHGe7SxV95": "gen_art_experiment_37",
    "art_HY7uYZz-OjRW": "gen_art_experiment_38",
    "art_LzP2qPwUrANz": "gen_art_evaluation_6",
}
SHORT = {"art_veI9l_Rb9wDY": "exp33", "art_pHL7LWNhpcCS": "exp34", "art_MZAfDPVhM6Ui": "exp35",
         "art_8O5eaNc5gxJs": "exp36", "art_VhaHGe7SxV95": "exp37", "art_HY7uYZz-OjRW": "exp38",
         "art_LzP2qPwUrANz": "eval6"}
BY_SHORT = {v: k for k, v in SHORT.items()}


def dep(short: str, rel: str = "") -> Path:
    """Path of a file inside a dependency workspace (short name exp33..exp38, eval6), under DEP_ROOT by folder name or,
    failing that, by artifact id."""
    aid = BY_SHORT[short]
    base = DEP_ROOT / ARTIFACTS[aid]
    if not base.exists() and (DEP_ROOT / aid).exists():
        base = DEP_ROOT / aid
    return base / rel


def src_ref(short: str, rel: str, key: str = "") -> str:
    """Source string '<artifact_id>:<relative path>#<key>' used in every correction record."""
    return f"{BY_SHORT[short]}:{rel}" + (f"#{key}" if key else "")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def read_json(p: Path) -> Any:
    return json.loads(Path(p).read_text())


def read_jsonl(p: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def write_json(p: Path, obj: Any) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=_default))


def _default(o: Any) -> Any:
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    if hasattr(o, "item"):
        return o.item()
    raise TypeError(f"not serialisable: {type(o)}")


def write_csv(p: Path, rows: list[dict[str, Any]], cols: list[str] | None = None) -> None:
    import csv
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    cols = cols or (list(rows[0].keys()) if rows else [])
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in cols})


# ------------------------------------------------------------------------------------------------ exact statistics
def _betacf(a: float, b: float, x: float) -> float:
    MAXIT, EPS, FPMIN = 300, 3e-16, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > FPMIN else FPMIN)
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > FPMIN else FPMIN)
        c = 1.0 + aa / c
        c = c if abs(c) > FPMIN else FPMIN
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > FPMIN else FPMIN)
        c = 1.0 + aa / c
        c = c if abs(c) > FPMIN else FPMIN
        de = d * c
        h *= de
        if abs(de - 1.0) < EPS:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1.0 - x)
    bt = math.exp(lbt)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def beta_ppf(q: float, a: float, b: float) -> float:
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if betainc(a, b, mid) < q:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> list[float]:
    if n == 0:
        return [float("nan"), float("nan")]
    lo = 0.0 if k == 0 else beta_ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta_ppf(1 - alpha / 2, k + 1, n - k)
    return [lo, hi]


def wilson(k: int, n: int, z: float = 1.959963984540054) -> list[float]:
    if n == 0:
        return [float("nan"), float("nan")]
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [max(0.0, c - h), min(1.0, c + h)]


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar (binomial on the discordant pairs)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def newcombe_diff(k1: int, n1: int, k2: int, n2: int) -> list[float]:
    """Newcombe hybrid score interval for p1 - p2 (method 10)."""
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p1 - p2
    return [d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)]


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact test on [[a, b], [c, d]] (sum of tables no more likely than the observed)."""
    r1, r2, c1 = a + b, c + d, a + c
    n = r1 + r2

    def pmf(x: int) -> float:
        return math.comb(r1, x) * math.comb(r2, c1 - x) / math.comb(n, c1)

    p0 = pmf(a)
    lo, hi = max(0, c1 - r2), min(r1, c1)
    return min(1.0, sum(pmf(x) for x in range(lo, hi + 1) if pmf(x) <= p0 * (1 + 1e-7)))


def avg_ranks(x: list[float]) -> list[float]:
    order = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and x[order[j + 1]] == x[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for t in range(i, j + 1):
            r[order[t]] = avg
        i = j + 1
    return r


def pearson(a: list[float], b: list[float]) -> float:
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    sa = math.sqrt(sum((x - ma) ** 2 for x in a))
    sb = math.sqrt(sum((y - mb) ** 2 for y in b))
    if sa == 0 or sb == 0:
        return float("nan")
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb)


def spearman(a: list[float], b: list[float]) -> float:
    return pearson(avg_ranks(a), avg_ranks(b))


def bootstrap_spearman(a: list[float], b: list[float], n_boot: int = 2000, seed: int = 20261023) -> list[float]:
    import random
    rng = random.Random(seed)
    n = len(a)
    vals = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        v = spearman([a[i] for i in idx], [b[i] for i in idx])
        if not math.isnan(v):
            vals.append(v)
    vals.sort()
    return [vals[int(0.025 * len(vals))], vals[min(len(vals) - 1, int(0.975 * len(vals)))]]


def cohen_kappa(a: list[str], b: list[str]) -> float:
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    if pe >= 1.0:
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1 - pe)


def fmt(x: float | None, nd: int = 2) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "-"
    return f"{x:.{nd}f}"


# ------------------------------------------------------------------------------------------------ correction records
VALUES: list[dict[str, Any]] = []


def value(name: str, recorded: Any, recomputed: Any, status: str, source: str, tolerance: float | str = 0.005,
          item: str = "", note: str = "") -> dict[str, Any]:
    """One traced value: recorded (as printed in current_report.md), recomputed (from the raw file), status in
    MATCH | CORRECTED | NEW | CARRIED. MATCH requires |recorded - recomputed| <= tolerance for numbers."""
    assert status in ("MATCH", "CORRECTED", "NEW", "CARRIED"), status
    rec = {"name": name, "item": item, "recorded": recorded, "recomputed": recomputed, "status": status,
           "tolerance": tolerance, "source": source}
    if note:
        rec["note"] = note
    if status == "MATCH" and isinstance(recorded, (int, float)) and isinstance(recomputed, (int, float)):
        assert abs(float(recorded) - float(recomputed)) <= float(tolerance) + 1e-12, (name, recorded, recomputed)
    VALUES.append(rec)
    return rec


def auto_status(recorded: float | None, recomputed: float, tol: float = 0.005) -> str:
    if recorded is None:
        return "NEW"
    return "MATCH" if abs(recorded - recomputed) <= tol + 1e-12 else "CORRECTED"


SUFFIX = " (iteration-8 correction)"


def edit(cid: str, item: str, section: str, old: str, new: str, kind: str = "prose", why: str = "",
         values: list[str] | None = None) -> dict[str, Any]:
    """One machine-checkable edit of the report. Prose edits must end with the iteration-8 suffix."""
    return {"id": cid, "item": item, "section": section, "kind": kind, "old_text": old, "new_text": new, "why": why,
            "value_names": values or []}


# ------------------------------------------------------------------------------------------------ residual-claim lint
LINT_PHRASES = [
    "above the 35",
    "pending the 2x2 of Step K",
    "the controls that failed for Qwen3-8B in Section 7.3 pass here",
    "on two tasks it carries it more cleanly",
    "on two tasks it routes more cleanly",
    "Categorical on shortest path and kth smallest",
    "counting sort 30/30 under DAS",
    "Recovery 0.73 to 1.71",
    "at the random 95th percentile",
    "passes all three controls",
    "dose dial 42 correct BFS against 35",
    "beats the explicit instruction",
    "All five ban templates lie outside it",
    "lies inside, at the 94th percentile",
    "the full state exchange gives 0 (29 programs labelled other",
    "The margin at the decision predicts what moves the algorithm",
    # extensions found while reading (iteration-8 executor)
    "pooled over sources it lies between 0.73 and 1.71",
    "while the full state exchange lands none",
    "transfer 0.47 on shortest path, 0.70 on connected components and 0.60 on kth smallest of the full state effect",
    "permuted labels transfer 0.47 to 0.70 of its effect",
    "the absolute unit's peaky profile on a few task tokens carries the effect",
    "where it exists its margin predicts the effect of random pushes",
    "and the fork margin under a random push predicts the effect of the push",
    "This time the controls hold.",
    "at a rate no arm that draws single samples approaches",
    "| COLM, not ICML 2026 |",
    "at a rate no knob applied to single samples approaches",
    "admits a fit 0.92 as good",
]


def lint(text: str, phrases: Iterable[str] = LINT_PHRASES) -> dict[str, Any]:
    """Count every contradicted phrase with its line numbers. Also flags an undefined 'Step K'."""
    lines = text.split("\n")
    out = {}
    for ph in phrases:
        hits = [i + 1 for i, l in enumerate(lines) if ph in l]
        out[ph] = {"count": sum(l.count(ph) for l in lines), "lines": hits}
    sk = [i + 1 for i, l in enumerate(lines) if re.search(r"\bStep K\b", l)]
    defined = any("Step K" in l and "dose-unit experiment" in l for l in lines)
    out["__undefined_step_k__"] = {"count": 0 if (defined or not sk) else len(sk), "lines": [] if defined else sk}
    return out


def lint_total(res: dict[str, Any]) -> int:
    return sum(v["count"] for v in res.values())
