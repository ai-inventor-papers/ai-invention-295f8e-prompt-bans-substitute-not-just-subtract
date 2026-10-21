"""Shared paths, provenance-tracked readers and exact small-sample statistics for the iteration-6 Step-0 audit."""

from __future__ import annotations

import ast
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

WS = Path(__file__).resolve().parent.parent
# Declared dependencies are read in place, read-only. In the published repository each one is a sibling folder of this
# artifact named by its artifact id: <AII_DEPS_ROOT>/<artifact_id>, AII_DEPS_ROOT defaulting to the parent folder of
# this workspace. One dependency can be pointed elsewhere with AII_DEP_<artifact_id> (non-word characters of the id
# replaced by '_', e.g. AII_DEP_art_mWn_MQEnNelg) or with the unpublished paths.local.json ({"deps": {id: folder}}).
# The undeclared inputs (the iteration-6 report, the strategy script, two eval3 files and one exp18 file) are vendored
# under inputs/ (see inputs/SOURCES.json for their origin and sha256).
DEPS_ROOT = Path(os.environ.get("AII_DEPS_ROOT", str(WS.parent)))
_LOCAL = json.loads((WS / "paths.local.json").read_text()) if (WS / "paths.local.json").exists() else {}
INPUTS = WS / "inputs"

ART = {"exp19": "art_mWn-MQEnNelg", "exp22": "art_SHaWv77P1XCI", "exp24": "art_CcZLW-9NX00l",
       "exp25": "art_8WbrpoEFslk9", "exp26": "art_9a8LrIv2lHbV", "exp27": "art_jR6Pyy3W9xum",
       "exp28": "art_hG0QPiaIPNhP", "dataset": "art_j3Rm_lr2nzR6", "eval3": "art_sV0cQ3ef1ZRQ",
       "eval4": "art_mgek9PfVBNbh", "exp18": "ITER3:gen_art_experiment_18", "report": "iter6:current_report.md",
       "protocol": "iter6:gen_strat_1/scripts/build_strategy.py", "self": "iter6:gen_art_evaluation_5"}


def dep_dir(art_id: str) -> Path:
    env = os.environ.get("AII_DEP_" + "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in art_id))
    return Path(env or _LOCAL.get("deps", {}).get(art_id) or DEPS_ROOT / art_id)


EXP19, EXP22, EXP24, EXP25, EXP26, EXP27, EXP28 = (dep_dir(ART[k]) for k in
                                                   ("exp19", "exp22", "exp24", "exp25", "exp26", "exp27", "exp28"))
DATASET = dep_dir(ART["dataset"])
EVAL3, EXP18 = INPUTS / "eval3", INPUTS / "exp18"
REPORT = INPUTS / "report" / "current_report.md"
_ITER6 = os.environ.get("AII_ITER6_GEN_ART") or _LOCAL.get("iter6_gen_art")
ITER6_GENART = Path(_ITER6) if _ITER6 else None  # NEVER read: names-only listing at freeze time (optional)
ROOTS = {"exp19": EXP19, "exp22": EXP22, "exp24": EXP24, "exp25": EXP25, "exp26": EXP26, "exp27": EXP27,
         "exp28": EXP28, "dataset": DATASET, "eval3": EVAL3, "eval4": dep_dir(ART["eval4"]), "exp18": EXP18,
         "report": REPORT.parent, "protocol": INPUTS / "protocol", "self": WS}

TASK_NAME = {"T03": "kth smallest", "T04": "substring search", "T05": "two sum", "T06": "find duplicate",
             "T08": "Fibonacci", "T10": "connected components", "T11": "longest increasing subsequence",
             "T13": "merge intervals", "T14": "top-k frequent", "R1": "nonoverlapping intervals",
             "R2": "cycle detection", "R3": "topological order", "R6": "first and last position", "T1": "grid",
             "T2": "shortest path", "A1": "majority element", "A2": "maximum block sum", "A3": "trapped rain water",
             "A4": "count primes", "A5": "longest common prefix", "A7": "longest mirrored substring",
             "A8": "jump game", "A9": "median of two sorted lists", "B1": "missing number", "B2": "single number",
             "B3": "minimum spanning tree weight", "B4": "integer square root", "B5": "all subsets",
             "B6": "valid anagram", "B7": "count inversions"}


# ----------------------------------------------------------------------------------------------- provenance
class Inputs:
    """Every file read goes through here, so results/input_hashes.json lists path, sha256, bytes and mtime."""

    def __init__(self) -> None:
        self.files: dict[str, dict[str, Any]] = {}

    def _rec(self, key: str, rel: str) -> Path:
        p = ROOTS[key] / rel
        sp = f"{ART[key]}:{rel}"
        if sp not in self.files:
            st = p.stat()
            self.files[sp] = {"artifact": ART[key], "rel": rel, "sha256": sha256_file(p), "bytes": st.st_size,
                              "mtime_utc": st.st_mtime}
        return p

    def path(self, key: str, rel: str) -> Path:
        return self._rec(key, rel)

    def json(self, key: str, rel: str) -> Any:
        return json.loads(self._rec(key, rel).read_text())

    def jsonl(self, key: str, rel: str) -> list[dict]:
        out = []
        with self._rec(key, rel).open() as f:
            for ln in f:
                if ln.strip():
                    out.append(json.loads(ln))
        return out

    def text(self, key: str, rel: str) -> str:
        return self._rec(key, rel).read_text()

    def exists(self, key: str, rel: str) -> bool:
        return (ROOTS[key] / rel).exists()


def prov(key: str, rel: str, jkey: str = "") -> str:
    return f"{ART[key]}:{rel}" + (f"#{jkey}" if jkey else "")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=_np_default)


def _np_default(o: Any) -> Any:
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    raise TypeError(f"not serialisable: {type(o)}")


def write_json(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, default=_np_default, sort_keys=False))


def parse_dictish(x: Any) -> dict:
    """exp19 realised.jsonl stores per-block dicts as Python reprs; exp27 as JSON objects."""
    if isinstance(x, dict):
        return x
    if isinstance(x, str):
        return ast.literal_eval(x)
    return {}


def fnum(x: Any, nd: int = 3) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "n/a"
    if isinstance(x, (int, np.integer)) and not isinstance(x, bool):
        return str(int(x))
    return f"{float(x):.{nd}f}"


def fp(p: float | None) -> str:
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return "n/a"
    return f"{p:.2g}" if p < 0.001 else f"{p:.3f}"


# ----------------------------------------------------------------------------------------------- statistics
def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    lo = 0.0 if k == 0 else float(stats.beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(stats.beta.ppf(1 - alpha / 2, k + 1, n - k))
    return lo, hi


def fisher_two_sided(a: int, b: int, c: int, d: int) -> float:
    return float(stats.fisher_exact([[a, b], [c, d]], alternative="two-sided")[1])


def fisher_greater(a: int, b: int, c: int, d: int) -> float:
    return float(stats.fisher_exact([[a, b], [c, d]], alternative="greater")[1])


def poisson_binomial_pmf(probs: list[float]) -> np.ndarray:
    pmf = np.zeros(len(probs) + 1)
    pmf[0] = 1.0
    for p in probs:
        pmf[1:] = pmf[1:] * (1 - p) + pmf[:-1] * p
        pmf[0] *= (1 - p)
    return pmf


def poisson_binomial_upper(probs: list[float], k: int) -> float:
    """P(X >= k) by exact dynamic-programming convolution."""
    pmf = poisson_binomial_pmf(probs)
    return float(min(1.0, pmf[k:].sum()))


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    return float(min(1.0, 2 * stats.binom.cdf(min(b, c), n, 0.5)))


def sign_test_two_sided(pos: int, neg: int) -> float:
    return mcnemar_exact(pos, neg)


def avg_rank(x: np.ndarray) -> np.ndarray:
    return stats.rankdata(x, method="average")


def spearman(x: list[float] | np.ndarray, y: list[float] | np.ndarray) -> float:
    x, y = np.asarray(x, float), np.asarray(y, float)
    if np.ptp(x) == 0 or np.ptp(y) == 0:
        return float("nan")
    rx, ry = avg_rank(x), avg_rank(y)
    return float(np.corrcoef(rx, ry)[0, 1])


def spearman_perm_p(x: Any, y: Any, n_perm: int, seed: int, alternative: str = "greater") -> float:
    """Monte Carlo permutation p of Spearman with average ranks (ties kept), (k+1)/(B+1)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    rx, ry = avg_rank(x), avg_rank(y)
    rx = (rx - rx.mean()) / (np.sqrt(((rx - rx.mean()) ** 2).sum()) or 1.0)
    ryc = ry - ry.mean()
    ryn = ryc / (np.sqrt((ryc ** 2).sum()) or 1.0)
    obs = float(rx @ ryn)
    rng = np.random.default_rng(seed)
    cnt, done, chunk = 0, 0, 20000
    while done < n_perm:
        m = min(chunk, n_perm - done)
        idx = np.argsort(rng.random((m, len(y))), axis=1)
        sims = ryn[idx] @ rx
        if alternative == "greater":
            cnt += int((sims >= obs - 1e-12).sum())
        elif alternative == "less":
            cnt += int((sims <= obs + 1e-12).sum())
        else:
            cnt += int((np.abs(sims) >= abs(obs) - 1e-12).sum())
        done += m
    return (cnt + 1) / (n_perm + 1)


def fisher_z_ci(r: float, n: int, var: float, alpha: float = 0.05) -> tuple[float, float]:
    if n <= 3 or r is None or math.isnan(r):
        return (float("nan"), float("nan"))
    rr = max(min(r, 0.999999), -0.999999)
    z = math.atanh(rr)
    h = stats.norm.ppf(1 - alpha / 2) * math.sqrt(var)
    return math.tanh(z - h), math.tanh(z + h)


def bonett_wright_ci(r: float, n: int) -> tuple[float, float]:
    return fisher_z_ci(r, n, (1 + r * r / 2) / (n - 3))


def fieller_ci(r: float, n: int) -> tuple[float, float]:
    return fisher_z_ci(r, n, 1.06 / (n - 3))


def bootstrap_spearman(x: Any, y: Any, n_boot: int, seed: int) -> dict[str, Any]:
    """Unit bootstrap of Spearman: percentile and BCa 95% intervals; resamples with constant x or y dropped."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = len(x)
    r0 = spearman(x, y)
    rng = np.random.default_rng(seed)
    reps = []
    dropped = 0
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        xb, yb = x[idx], y[idx]
        if np.ptp(xb) == 0 or np.ptp(yb) == 0:
            dropped += 1
            continue
        reps.append(spearman(xb, yb))
    reps = np.asarray(reps)
    out = {"n_boot": n_boot, "n_kept": int(len(reps)), "share_dropped": dropped / n_boot}
    if len(reps) < 50:
        return out | {"pct": [float("nan")] * 2, "bca": [float("nan")] * 2}
    out["pct"] = [float(np.quantile(reps, 0.025)), float(np.quantile(reps, 0.975))]
    # BCa: bias correction from the replicate distribution, acceleration from the jackknife
    prop = float(np.mean(reps < r0)) + 0.5 * float(np.mean(reps == r0))
    prop = min(max(prop, 1e-6), 1 - 1e-6)
    z0 = stats.norm.ppf(prop)
    jack = []
    for i in range(n):
        m = np.ones(n, bool)
        m[i] = False
        jack.append(spearman(x[m], y[m]))
    jack = np.asarray([j for j in jack if not math.isnan(j)])
    jm = jack.mean()
    num = ((jm - jack) ** 3).sum()
    den = 6 * (((jm - jack) ** 2).sum() ** 1.5)
    a = num / den if den > 0 else 0.0
    qs = []
    for zz in (stats.norm.ppf(0.025), stats.norm.ppf(0.975)):
        adj = stats.norm.cdf(z0 + (z0 + zz) / (1 - a * (z0 + zz)))
        qs.append(float(np.quantile(reps, min(max(adj, 0.0), 1.0))))
    out["bca"] = qs
    out["z0"], out["accel"] = float(z0), float(a)
    return out


def wilcoxon_exact(d: list[float], alternative: str = "greater") -> float:
    d = [x for x in d if x != 0]
    if not d:
        return 1.0
    return float(stats.wilcoxon(d, alternative=alternative, method="exact", zero_method="wilcox").pvalue)


def gwet_ac1(a: list[int], b: list[int]) -> float:
    """Gwet's AC1 for two raters, binary or multi-class labels."""
    n = len(a)
    cats = sorted(set(a) | set(b))
    po = sum(x == y for x, y in zip(a, b)) / n
    q = len(cats)
    if q < 2:
        return 1.0
    pis = [(sum(x == c for x in a) + sum(y == c for y in b)) / (2 * n) for c in cats]
    pe = sum(p * (1 - p) for p in pis) / (q - 1)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def cohen_kappa(a: list[Any], b: list[Any]) -> float:
    n = len(a)
    cats = sorted(set(a) | set(b), key=str)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((sum(x == c for x in a) / n) * (sum(y == c for y in b) / n) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def env_threads_one() -> None:
    for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ.setdefault(k, "1")
