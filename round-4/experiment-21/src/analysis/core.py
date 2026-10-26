#!/usr/bin/env python3
"""C1-seed analysis core (hash-committed in commit #0 before any decisive sample).

Definitions (verbatim from predictions/prereg_c1seed.json):
- A SEED is a slot (task, template w, k); 20 per task (W1-W5 x k 0-3).
- Label modes: 'primary' = catalogue label or 'other' of VALID programs ('invalid' = no code / syntax error / crash
  before the first traced op, and 'unresolved' (incl. exp17's 'disputed') are excluded); 'correct_only' = primary and
  passed the hidden tests; 'invalid_as_label' = 'invalid' counts as one more label value.
- changed(labels) = 1 if the valid labels contain >= 2 distinct values, 0 if they are all equal, None if fewer than
  2 valid labels (seed not countable for that set).
- changed_T(s) over {NOPN T0.3, T0.7, T1.0, T1.3}; changed_PN(s; S, alpha, T) over {NOPN at T} + {PN(d, alpha, T): d in S}.
- C_T = sum over countable seeds of changed_T; C_PN = mean over all C(6,3) = 20 subsets S of sum_s changed_PN(s; S)
  (uncountable (seed, S) pairs contribute 0 and are reported).
- x_s = mean over countable subsets of changed_PN(s; S, alpha 1, T 1.0) - changed_T(s), for seeds where both are
  defined; one-sided sign-flip permutation p (100,000 draws) for mean x_s > 0, pooled over T2 and T03 seeds.
- Phrasing: identifier-normalised AST 4-gram shingles, Jaccard, connected components at theta (complete linkage as
  robustness) within each (condition, idea); PPI = clusters / ideas present; slope of log PPI on T per task by seed
  bootstrap; pooled slope = mean of the task slopes.
"""

from __future__ import annotations

import ast
import itertools
import math
from collections import Counter
from typing import Any, Callable, Iterable, Sequence

import numpy as np

EXCLUDED = {"invalid", "unresolved", "disputed", None, ""}
THETAS = (0.7, 0.8, 0.9)
SUBSET_SIZE = 3


# ------------------------------------------------------------------------------------------------ labels
def norm_label(lab: str | None) -> str | None:
    if lab in ("disputed", "unresolved", "unknown", "inconsistent"):
        return "unresolved"
    return lab


def label_value(row: dict[str, Any] | None, mode: str = "primary") -> str | None:
    """Label used for change counting under a sensitivity mode; None = excluded."""
    if row is None:
        return None
    lab = norm_label(row.get("label"))
    if mode == "primary":
        return None if lab in EXCLUDED else lab
    if mode == "correct_only":
        return lab if (lab not in EXCLUDED and bool(row.get("passed"))) else None
    if mode == "invalid_as_label":
        return None if lab in ("unresolved", None, "") else lab
    if mode == "first_approach":
        return row.get("first_approach")
    raise ValueError(mode)


def changed(labels: Iterable[str | None], min_valid: int = 2) -> int | None:
    v = [l for l in labels if l is not None]
    if len(v) < min_valid:
        return None
    return int(len(set(v)) >= 2)


# ------------------------------------------------------------------------------------------------ indexing
def index_rows(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, str, str], dict[str, Any]]:
    """{(task, seed_id, arm): row}; seed_id = 'W1|0'. Later duplicates are ignored (first row wins)."""
    out: dict[tuple[str, str, str], dict[str, Any]] = {}
    for r in rows:
        key = (r["task"], f"{r['template']}|{int(r['sample_id'])}", r["arm"])
        out.setdefault(key, r)
    return out


def seeds_of(templates: Sequence[str] = ("W1", "W2", "W3", "W4", "W5"), ks: Sequence[int] = (0, 1, 2, 3)) -> list[str]:
    return [f"{w}|{k}" for w in templates for k in ks]


# ------------------------------------------------------------------------------------------------ change counts
def changed_over(idx: dict, task: str, seed: str, arms: Sequence[str], mode: str = "primary") -> int | None:
    return changed([label_value(idx.get((task, seed, a)), mode) for a in arms])


def count_changed(idx: dict, task: str, seeds: Sequence[str], arms: Sequence[str],
                  mode: str = "primary") -> dict[str, Any]:
    per = {s: changed_over(idx, task, s, arms, mode) for s in seeds}
    vals = [v for v in per.values() if v is not None]
    return {"C": int(sum(vals)), "n_countable": len(vals), "n_seeds": len(seeds), "per_seed": per}


def subsets(items: Sequence[Any], k: int = SUBSET_SIZE) -> list[tuple[Any, ...]]:
    return list(itertools.combinations(list(items), k))


def c_pn(idx: dict, task: str, seeds: Sequence[str], nopn_arm: str, pn_arms: Sequence[str],
         mode: str = "primary", k: int = SUBSET_SIZE) -> dict[str, Any]:
    """Subset-averaged changed-seed count over all C(len(pn_arms), k) subsets."""
    subs = subsets(pn_arms, k)
    sums, uncountable = [], 0
    per_seed_mean: dict[str, float | None] = {}
    per_seed_vals: dict[str, list[int]] = {s: [] for s in seeds}
    for S in subs:
        tot = 0
        for s in seeds:
            v = changed_over(idx, task, s, [nopn_arm, *S], mode)
            if v is None:
                uncountable += 1
                continue
            tot += v
            per_seed_vals[s].append(v)
        sums.append(tot)
    for s in seeds:
        per_seed_mean[s] = float(np.mean(per_seed_vals[s])) if per_seed_vals[s] else None
    arr = np.array(sums, dtype=float)
    return {"C_PN": float(arr.mean()) if len(arr) else float("nan"), "min": float(arr.min()) if len(arr) else None,
            "median": float(np.median(arr)) if len(arr) else None, "max": float(arr.max()) if len(arr) else None,
            "n_subsets": len(subs), "uncountable_seed_subsets": uncountable, "subset_sums": sums,
            "per_seed_mean": per_seed_mean}


def x_contrast(changed_t: dict[str, int | None], pn_mean: dict[str, float | None]) -> dict[str, float]:
    """x_s = subset-mean changed_PN(s) - changed_T(s) over seeds where both are defined."""
    return {s: float(pn_mean[s]) - float(changed_t[s]) for s in changed_t
            if changed_t.get(s) is not None and pn_mean.get(s) is not None}


def sign_flip_p(x: Sequence[float], n_draws: int = 100_000, seed: int = 20261021) -> dict[str, Any]:
    """One-sided sign-flip permutation test of mean(x) > 0. p = (1 + #{perm mean >= obs}) / (1 + n_draws)."""
    xa = np.asarray(list(x), dtype=float)
    n = len(xa)
    if n == 0:
        return {"n": 0, "mean": float("nan"), "p": float("nan")}
    obs = float(xa.mean())
    if np.allclose(xa, 0):
        return {"n": n, "mean": obs, "p": 1.0, "n_draws": 0, "note": "all x_s = 0"}
    rng = np.random.default_rng(seed)
    ge = 0
    chunk = 10_000
    done = 0
    while done < n_draws:
        m = min(chunk, n_draws - done)
        signs = rng.integers(0, 2, size=(m, n), dtype=np.int8) * 2 - 1
        means = (signs * xa[None, :]).mean(axis=1)
        ge += int((means >= obs - 1e-12).sum())
        done += m
    return {"n": n, "mean": obs, "p": (1 + ge) / (1 + n_draws), "n_draws": n_draws, "n_nonzero": int((xa != 0).sum())}


def seed_bootstrap_ci(x: Sequence[float], reps: int = 10_000, seed: int = 7, level: float = 0.95) -> tuple[float, float]:
    xa = np.asarray(list(x), dtype=float)
    if len(xa) == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(xa), size=(reps, len(xa)))
    m = xa[idx].mean(axis=1)
    a = (1 - level) / 2
    return (float(np.quantile(m, a)), float(np.quantile(m, 1 - a)))


def clopper_pearson(k: int, n: int, level: float = 0.95) -> tuple[float, float]:
    from scipy.stats import beta

    if n == 0:
        return (float("nan"), float("nan"))
    a = (1 - level) / 2
    lo = 0.0 if k == 0 else float(beta.ppf(a, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - a, k + 1, n - k))
    return (lo, hi)


# ------------------------------------------------------------------------------------------------ shingles
class _Norm(ast.NodeVisitor):
    """Pre-order linearisation: node type names, operator classes, renamed identifiers (first appearance), constants
    as their type only. Docstrings are dropped (comments never reach the AST)."""

    def __init__(self) -> None:
        self.toks: list[str] = []
        self.names: dict[str, str] = {}

    def _id(self, name: str) -> str:
        if name not in self.names:
            self.names[name] = f"v{len(self.names)}"
        return self.names[name]

    def generic_visit(self, node: ast.AST) -> None:
        self.toks.append(type(node).__name__)
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                body = value
                if field == "body" and body and isinstance(body[0], ast.Expr) and isinstance(
                        getattr(body[0], "value", None), ast.Constant) and isinstance(body[0].value.value, str):
                    body = body[1:]           # drop docstring
                for item in body:
                    if isinstance(item, ast.AST):
                        self.visit(item)
            elif isinstance(value, ast.AST):
                self.visit(value)
            elif field in ("id", "arg", "name", "asname") and isinstance(value, str):
                self.toks.append(self._id(value))
            elif field == "attr" and isinstance(value, str):
                self.toks.append("." + value)
            elif field == "module" and isinstance(value, str):
                self.toks.append("mod:" + value)

    def visit_Constant(self, node: ast.Constant) -> None:
        self.toks.append("Const:" + type(node.value).__name__)


def ast_tokens(code: str) -> list[str] | None:
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, MemoryError, RecursionError):
        return None
    v = _Norm()
    try:
        v.visit(tree)
    except RecursionError:
        return None
    return v.toks


def shingles(code: str | None, n: int = 4) -> frozenset | None:
    if not code:
        return None
    toks = ast_tokens(code)
    if toks is None:
        return None
    if len(toks) < n:
        return frozenset([tuple(toks)])
    return frozenset(tuple(toks[i:i + n]) for i in range(len(toks) - n + 1))


def jaccard(a: frozenset | None, b: frozenset | None) -> float:
    if a is None or b is None:
        return float("nan")
    if not a and not b:
        return 1.0
    return len(a & b) / max(len(a | b), 1)


def jaccard_matrix(sh: Sequence[frozenset]) -> np.ndarray:
    n = len(sh)
    m = np.eye(n)
    for i in range(n):
        for j in range(i + 1, n):
            m[i, j] = m[j, i] = jaccard(sh[i], sh[j])
    return m


def n_components(J: np.ndarray, theta: float) -> int:
    """Connected components of the graph with an edge where Jaccard >= theta (single linkage)."""
    n = J.shape[0]
    if n == 0:
        return 0
    parent = list(range(n))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for i in range(n):
        for j in range(i + 1, n):
            if J[i, j] >= theta - 1e-12:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[ri] = rj
    return len({find(i) for i in range(n)})


def n_complete(J: np.ndarray, theta: float) -> int:
    """Complete-linkage clusters cut at distance 1 - theta (robustness)."""
    from scipy.cluster.hierarchy import fcluster, linkage
    from scipy.spatial.distance import squareform

    n = J.shape[0]
    if n <= 1:
        return n
    D = np.clip(1.0 - J, 0.0, 1.0)
    np.fill_diagonal(D, 0.0)
    Z = linkage(squareform(D, checks=False), method="complete")
    return int(len(set(fcluster(Z, t=1.0 - theta + 1e-12, criterion="distance"))))


def ppi(labels: Sequence[str], J: np.ndarray, theta: float, linkage_kind: str = "single") -> dict[str, Any]:
    """Phrasings per idea of one cell: programs grouped by idea label; clusters within each idea; PPI = clusters /
    ideas present. labels[i] is the idea of program i (J indexes the same programs)."""
    ideas = sorted(set(labels))
    if not ideas:
        return {"ppi": float("nan"), "clusters": 0, "ideas": 0, "by_idea": {}}
    by = {}
    tot = 0
    for idea in ideas:
        ii = [i for i, l in enumerate(labels) if l == idea]
        sub = J[np.ix_(ii, ii)]
        c = n_components(sub, theta) if linkage_kind == "single" else n_complete(sub, theta)
        by[idea] = {"n": len(ii), "clusters": c}
        tot += c
    return {"ppi": tot / len(ideas), "clusters": tot, "ideas": len(ideas), "by_idea": by}


def ols_slope(x: Sequence[float], y: Sequence[float]) -> float:
    xa, ya = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(ya)
    xa, ya = xa[ok], ya[ok]
    if len(xa) < 2 or np.ptp(xa) == 0:
        return float("nan")
    xm = xa - xa.mean()
    return float((xm * (ya - ya.mean())).sum() / (xm ** 2).sum())


def ppi_slope_bootstrap(cells: dict[float, dict[str, Any]], theta: float, reps: int = 2000, seed: int = 11,
                        linkage_kind: str = "single") -> dict[str, Any]:
    """cells[T] = {'seeds': [seed ids], 'labels': [idea per seed program], 'sh': [shingles]} for the NO-PN cells of one
    task (programs aligned by seed; a seed with no valid program at T is absent from that cell). The bootstrap
    resamples SEEDS (each seed's coupled programs move together)."""
    Ts = sorted(cells)
    allseeds = sorted({s for T in Ts for s in cells[T]["seeds"]})
    pos = {T: {s: i for i, s in enumerate(cells[T]["seeds"])} for T in Ts}
    Js = {T: jaccard_matrix(cells[T]["sh"]) for T in Ts}

    def stat(seed_list: list[str]) -> tuple[float, dict[float, float]]:
        vals = {}
        for T in Ts:
            ii = [pos[T][s] for s in seed_list if s in pos[T]]
            if not ii:
                vals[T] = float("nan")
                continue
            labs = [cells[T]["labels"][i] for i in ii]
            J = Js[T][np.ix_(ii, ii)]
            vals[T] = ppi(labs, J, theta, linkage_kind)["ppi"]
        return ols_slope(Ts, [math.log(v) if v and v > 0 else float("nan") for v in vals.values()]), vals
    obs, obs_vals = stat(allseeds)
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(reps):
        samp = [allseeds[i] for i in rng.integers(0, len(allseeds), size=len(allseeds))]
        boots.append(stat(samp)[0])
    b = np.array([v for v in boots if np.isfinite(v)])
    return {"slope": obs, "ppi_by_T": {str(k): v for k, v in obs_vals.items()}, "boot": b,
            "ci95": (float(np.quantile(b, 0.025)), float(np.quantile(b, 0.975))) if len(b) else (float("nan"),) * 2}


# ------------------------------------------------------------------------------------------------ diversity
def hill1(labels: Sequence[str]) -> float:
    c = Counter(labels)
    n = sum(c.values())
    if n == 0:
        return float("nan")
    p = np.array(list(c.values()), float) / n
    return float(np.exp(-(p * np.log(p)).sum()))


def rarefied_hill1(per_seed_options: dict[str, list[str | None]], draws: int = 1000, seed: int = 5) -> dict[str, Any]:
    """per_seed_options[s] = labels (None = not counted, e.g. not correct) of the seed's programs in a PN cell (one per
    direction). Each draw takes one program per seed (depth = number of seeds) and computes Hill-1 over the counted
    labels."""
    rng = np.random.default_rng(seed)
    seeds = sorted(per_seed_options)
    vals, depths = [], []
    for _ in range(draws):
        labs = []
        for s in seeds:
            opts = per_seed_options[s]
            if not opts:
                continue
            l = opts[int(rng.integers(0, len(opts)))]
            if l is not None:
                labs.append(l)
        if labs:
            vals.append(hill1(labs))
            depths.append(len(labs))
    return {"hill1_mean": float(np.mean(vals)) if vals else float("nan"),
            "hill1_q05": float(np.quantile(vals, 0.05)) if vals else float("nan"),
            "hill1_q95": float(np.quantile(vals, 0.95)) if vals else float("nan"),
            "mean_counted_depth": float(np.mean(depths)) if depths else 0.0}


def js_bits(c1: Counter | dict, c2: Counter | dict) -> float:
    keys = sorted(set(c1) | set(c2))
    p = np.array([c1.get(k, 0) for k in keys], float)
    q = np.array([c2.get(k, 0) for k in keys], float)
    if p.sum() == 0 or q.sum() == 0:
        return float("nan")
    p, q = p / p.sum(), q / q.sum()
    m = (p + q) / 2

    def kl(a: np.ndarray, b: np.ndarray) -> float:
        ok = a > 0
        return float((a[ok] * np.log2(a[ok] / b[ok])).sum())
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def template_resampling_null(rows_a: list[dict[str, Any]], rows_b: list[dict[str, Any]], key: Callable[[dict], Any],
                             reps: int = 2000, seed: int = 3) -> dict[str, Any]:
    """JS between two compositions vs a null that pools both arms and resamples templates (with replacement, within the
    pooled arm) to form two pseudo-arms of the original template counts."""
    obs = js_bits(Counter(key(r) for r in rows_a if key(r) is not None),
                  Counter(key(r) for r in rows_b if key(r) is not None))
    pool = rows_a + rows_b
    by_t: dict[str, list[dict[str, Any]]] = {}
    for r in pool:
        by_t.setdefault(r["template"], []).append(r)
    temps = sorted(by_t)
    rng = np.random.default_rng(seed)
    null = []
    na = Counter(r["template"] for r in rows_a)
    nb = Counter(r["template"] for r in rows_b)
    for _ in range(reps):
        def pseudo(counts: Counter) -> Counter:
            c: Counter = Counter()
            for w, n in counts.items():
                src = by_t[temps[int(rng.integers(0, len(temps)))]]
                for i in rng.integers(0, len(src), size=n):
                    v = key(src[int(i)])
                    if v is not None:
                        c[v] += 1
            return c
        null.append(js_bits(pseudo(na), pseudo(nb)))
    nb_ = np.array([v for v in null if np.isfinite(v)])
    return {"js_bits": obs, "null_p95": float(np.quantile(nb_, 0.95)) if len(nb_) else float("nan"),
            "p": float((1 + (nb_ >= obs - 1e-12).sum()) / (1 + len(nb_))) if len(nb_) else float("nan")}


# ------------------------------------------------------------------------------------------------ verdict
def decide(res: dict[str, Any]) -> dict[str, Any]:
    """Apply the committed outcome rules. res keys: C_T[cell] (ints), C_PN_a1_T1[task] (floats), phr[theta] = {slope,
    ci95}, hcon = {mean, p}."""
    ht_cells = res["C_T"]
    h_t = all(v is not None and v <= 1 for v in ht_cells.values())
    h_pn = all(res["C_PN_a1_T1"].get(t, 0) >= 5 for t in ("T2", "T03"))
    h_phr = all(np.isfinite(v["slope"]) and v["slope"] > 0 and v["ci95"][0] > 0 for v in res["phr"].values())
    h_con = res["hcon"]["p"] < 0.05 and res["hcon"]["mean"] > 0
    disconf = (res["hcon"]["mean"] <= 0) or all(
        (res["C_T_off"].get(t, 0) >= res["C_PN_a1_T1"].get(t, 0)) for t in ("T2", "T03"))
    if h_t and h_pn and h_phr and h_con:
        verdict = "CONFIRMED"
    elif disconf:
        verdict = "DISCONFIRMED"
    else:
        verdict = "PARTIAL"
    failed = [n for n, ok in (("H-T", h_t), ("H-PN", h_pn), ("H-PHR", h_phr), ("H-CON", h_con)) if not ok]
    note = ""
    if verdict == "PARTIAL" and h_t and all(1 <= res["C_PN_a1_T1"].get(t, 0) <= 4 for t in ("T2", "T03")):
        note = "temperature inert but PN weaker than predicted"
    return {"verdict": verdict, "H-T": h_t, "H-PN": h_pn, "H-PHR": h_phr, "H-CON": h_con, "failed_parts": failed,
            "note": note}
