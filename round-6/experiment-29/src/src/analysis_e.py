#!/usr/bin/env python3
"""Stage G analysis of artifact E (committed code: its sha256 is frozen in predictions/e_commit.json at commit #0).

Outcome definitions (frozen):
  Y_correct      = passed AND label not in {default, invalid}            ('other' counts as off-default)
  Y_correct_cat  = passed AND label not in {default, invalid, other}     (catalogue-only version, reported beside)
  Y_attempted    = label not in {default, invalid}
Defaults: T10 union_find, T2 dijkstra, T03 full_sort. Every contrast between precisions is PAIRED by CRN slot
(task, template, k[, direction]); the exact McNemar test uses the discordant pairs.

Outputs (results/): factorial.json, primary_E.json, attribution.json, population40.json, unit_cross.json,
t03_control.json, dither.json, mechanism.json, landing.json, dose.json, engine_check.json, verdict.json.
Usage: python src/analysis_e.py [--synthetic {activation,null}] [--out-dir DIR]
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RES = ROOT / "results"
INP = ROOT / "inputs"
PRED = ROOT / "predictions"

DEFAULT = {"T10": "union_find", "T2": "dijkstra", "T03": "full_sort"}
PRECS = ("W8A8", "W8A16", "W16A8", "W16A16")
THRESH_DIFF = {"T10": 0.25, "T2": 0.15}
PRED_W8A8_MIN = {"T10": 0.40, "T2": 0.30}
PRED_W16_MAX = 0.10
P_PRIMARY = 0.01
HOLM_SMALLEST = 0.0125
NULL_BAND = 0.10
ATTR_MAIN = 0.20
ATTR_OTHER = 0.10
N_BOOT = 2000
SEED = 20261021
LABEL_ALIAS = {"bellman_ford_spfa": "bf_spfa", "bellman_ford": "bf_spfa", "spfa": "bf_spfa"}


# ------------------------------------------------------------------------------------------------ io
def read_jsonl(p: Path) -> list[dict[str, Any]]:
    if not Path(p).exists():
        return []
    out = []
    with open(p) as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return out


def write_json(p: Path, obj: Any) -> None:
    def fin(o: Any) -> Any:
        if isinstance(o, float):
            return o if math.isfinite(o) else None
        if isinstance(o, dict):
            return {str(k): fin(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [fin(v) for v in o]
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return fin(float(o))
        if isinstance(o, np.bool_):
            return bool(o)
        if isinstance(o, np.ndarray):
            return fin(o.tolist())
        return o
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(fin(obj), indent=1))
    tmp.replace(p)


def merge_rows(raw_p: Path = DATA / "samples_raw.jsonl", lab_p: Path = DATA / "labels.jsonl",
               out_p: Path | None = DATA / "samples.jsonl") -> list[dict[str, Any]]:
    """Join generation rows with label rows by sample_id -> the plan's PER-ROW OUTPUT (no token ids, no text)."""
    labs = {r["sample_id"]: r for r in read_jsonl(lab_p)}
    rows = []
    for r in read_jsonl(raw_p):
        l = labs.get(r["sample_id"])
        if l is None:
            continue
        o = {k: v for k, v in r.items() if k not in ("token_ids", "text")}
        for k in ("label", "labeller_source", "passed", "valid", "runtime_label", "ast_label", "judge_label",
                  "n_pass", "n_cases", "code_sha256", "code", "is_default"):
            o[k] = l.get(k)
        rows.append(o)
    if out_p is not None:
        with open(out_p, "w") as fh:
            for o in rows:
                fh.write(json.dumps(o) + "\n")
    return rows


# ------------------------------------------------------------------------------------------------ outcomes
def y_correct(r: dict[str, Any], cat_only: bool = False) -> int:
    lab = r.get("label")
    bad = {DEFAULT[r["task"]], "invalid"} | ({"other"} if cat_only else set())
    return int(bool(r.get("passed")) and lab not in bad and lab is not None)


def y_attempted(r: dict[str, Any]) -> int:
    lab = r.get("label")
    return int(lab is not None and lab not in (DEFAULT[r["task"]], "invalid"))


def wilson(k: int, n: int, z: float = 1.959964) -> list[float | None]:
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [max(0.0, c - h), min(1.0, c + h)]


def clopper_pearson(k: int, n: int, a: float = 0.05) -> list[float]:
    lo = 0.0 if k == 0 else float(stats.beta.ppf(a / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(stats.beta.ppf(1 - a / 2, k + 1, n - k))
    return [lo, hi]


def hill1_rarefied(labels: list[str], depth: int = 25, n_draw: int = 400, seed: int = SEED) -> tuple[float | None, bool]:
    """Expected exp(Shannon entropy) of the label composition of `depth` programs drawn without replacement
    (Monte Carlo); fewer than `depth` programs -> Hill-1 of all of them, flagged."""
    if not labels:
        return None, True
    def h1(ls: list[str]) -> float:
        c = np.array(list(Counter(ls).values()), dtype=float)
        p = c / c.sum()
        return float(np.exp(-(p * np.log(p)).sum()))
    if len(labels) < depth:
        return h1(labels), True
    rng = np.random.default_rng(seed)
    arr = np.array(labels)
    return float(np.mean([h1(list(rng.choice(arr, depth, replace=False))) for _ in range(n_draw)])), False


def mcnemar_exact(b: int, c: int) -> dict[str, Any]:
    """b = (A=1, B=0) discordant pairs, c = (A=0, B=1). Exact binomial test on b of b+c at 0.5."""
    n = b + c
    if n == 0:
        return {"b": b, "c": c, "p_two_sided": 1.0, "p_one_sided": 1.0}
    two = float(stats.binomtest(b, n, 0.5, alternative="two-sided").pvalue)
    one = float(stats.binomtest(b, n, 0.5, alternative="greater").pvalue)
    return {"b": b, "c": c, "p_two_sided": two, "p_one_sided": one}


# ------------------------------------------------------------------------------------------------ cells
def slot_key(r: dict[str, Any]) -> tuple:
    return (r["template"], int(r["slot"]), r.get("direction_seed") if str(r["arm"]).startswith("POP") else None)


def cell_index(rows: list[dict[str, Any]]) -> dict[tuple[str, str, str], dict[tuple, dict[str, Any]]]:
    idx: dict[tuple[str, str, str], dict[tuple, dict[str, Any]]] = defaultdict(dict)
    for r in rows:
        idx[(r["task"], r["precision"], r["arm"])][slot_key(r)] = r
    return idx


def summarise_cell(rs: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rs)
    if n == 0:
        return {"N": 0}
    yc = [y_correct(r) for r in rs]
    ycc = [y_correct(r, True) for r in rs]
    ya = [y_attempted(r) for r in rs]
    npass = sum(bool(r.get("passed")) for r in rs)
    corr = Counter(r["label"] for r in rs if r.get("passed") and r.get("label") not in ("invalid", None))
    att = Counter(r["label"] for r in rs if r.get("label") is not None)
    hill, flag = hill1_rarefied([r["label"] for r in rs if r.get("passed") and r.get("label") not in ("invalid", None)])
    return {"N": n, "pass": npass / n, "pass_wilson95": wilson(npass, n),
            "invalid": sum(r.get("label") == "invalid" for r in rs) / n,
            "cap_hit": sum(r.get("finish_reason") == "length" for r in rs) / n,
            "default_share": sum(r.get("label") == DEFAULT[rs[0]["task"]] for r in rs) / n,
            "k_correct_off": int(sum(yc)), "Y_correct": float(np.mean(yc)), "Y_correct_wilson95": wilson(sum(yc), n),
            "Y_correct_catalogue_only": float(np.mean(ycc)), "Y_attempted": float(np.mean(ya)),
            "Y_attempted_wilson95": wilson(sum(ya), n), "correct_composition": dict(corr),
            "attempted_composition": dict(att), "hill1_correct_rarefied25": hill, "hill1_flag_lt25_correct": flag}


def factorial(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        arm = r["arm"]
        if arm.startswith("POP_d"):
            by[(r["task"], r["precision"], "POP40_a2")].append(r)
        by[(r["task"], r["precision"], arm)].append(r)
    out = {}
    for (t, p, a), rs in sorted(by.items()):
        if a.startswith("POP_d"):
            continue
        out[f"{t}|{p}|{a}"] = summarise_cell(rs)
    return out


def paired(idx: dict, task: str, arm: str, pa: str, pb: str, arm_b: str | None = None,
           fn=y_correct) -> tuple[np.ndarray, np.ndarray, list[tuple]]:
    A = idx.get((task, pa, arm), {})
    Bc = idx.get((task, pb, arm_b or arm), {})
    keys = sorted(set(A) & set(Bc), key=str)
    a = np.array([fn(A[k]) for k in keys], dtype=float)
    b = np.array([fn(Bc[k]) for k in keys], dtype=float)
    return a, b, keys


def boot_diff(a: np.ndarray, b: np.ndarray, n_boot: int = N_BOOT, seed: int = SEED) -> list[float | None]:
    if len(a) == 0:
        return [None, None]
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a), size=(n_boot, len(a)))
    d = a[idx].mean(1) - b[idx].mean(1)
    return [float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))]


def contrast(idx: dict, task: str, arm: str, pa: str, pb: str, arm_b: str | None = None) -> dict[str, Any]:
    a, b, keys = paired(idx, task, arm, pa, pb, arm_b)
    if len(keys) == 0:
        return {"n_pairs": 0}
    t = {"11": int(((a == 1) & (b == 1)).sum()), "10": int(((a == 1) & (b == 0)).sum()),
         "01": int(((a == 0) & (b == 1)).sum()), "00": int(((a == 0) & (b == 0)).sum())}
    mc = mcnemar_exact(t["10"], t["01"])
    return {"n_pairs": len(keys), "share_A": float(a.mean()), "share_B": float(b.mean()),
            "diff": float(a.mean() - b.mean()), "diff_boot95": boot_diff(a, b), "table": t, "mcnemar": mc}


# ------------------------------------------------------------------------------------------------ primary
def primary(idx: dict, iter4: dict[str, Any] | None) -> dict[str, Any]:
    out: dict[str, Any] = {"definition": "Y_correct on PN_a2, W8A8 (EMU) vs W16A16, paired by CRN slot",
                           "thresholds": {"diff": THRESH_DIFF, "p": P_PRIMARY, "W8A8_min": PRED_W8A8_MIN,
                                          "W16A16_max": PRED_W16_MAX, "null_band": NULL_BAND,
                                          "holm_smallest": HOLM_SMALLEST}, "tasks": {}}
    hits, nulls, ps = [], [], []
    for t in ("T10", "T2"):
        c = contrast(idx, t, "PN_a2", "W8A8", "W16A16")
        if c.get("n_pairs", 0) == 0:
            out["tasks"][t] = {"missing": True}
            continue
        effect = c["diff"] >= THRESH_DIFF[t] and c["mcnemar"]["p_two_sided"] < P_PRIMARY
        within = abs(c["diff"]) <= NULL_BAND
        pred = {"W8A8_ge_min": c["share_A"] >= PRED_W8A8_MIN[t], "W16A16_le_max": c["share_B"] <= PRED_W16_MAX,
                "diff_ge_threshold": c["diff"] >= THRESH_DIFF[t], "p_lt_0.01": c["mcnemar"]["p_two_sided"] < P_PRIMARY}
        if iter4 and t in iter4:
            lo, hi = iter4[t]["PN_a2"]["Y_correct_cp95"]
            pred["W8A8_inside_iter4_CI"] = lo <= c["share_A"] <= hi
        c.update({"effect": effect, "within_null_band": within, "predictions": pred,
                  "PN_a1": contrast(idx, t, "PN_a1", "W8A8", "W16A16"),
                  "TWIN": contrast(idx, t, "TWIN", "W8A8", "W16A16"),
                  "PN_a0.5": contrast(idx, t, "PN_a0.5", "W8A8", "W16A16")})
        rc = contrast(idx, t, "PN_a2", "W8A8REAL", "W16A16")
        if rc.get("n_pairs"):
            rc["effect"] = rc["diff"] >= THRESH_DIFF[t] and rc["mcnemar"]["p_two_sided"] < P_PRIMARY
            c["REAL_in_place_of_EMU"] = rc
            c["EMU_vs_REAL_PN_a2"] = contrast(idx, t, "PN_a2", "W8A8", "W8A8REAL")
        out["tasks"][t] = c
        hits.append(effect)
        nulls.append(within)
        ps.append(c["mcnemar"]["p_two_sided"])
    if len(hits) < 2:
        verdict = "INCOMPLETE"
    elif all(hits):
        verdict = "PRECISION EFFECT"
    elif any(hits):
        verdict = "PARTIAL"
    elif all(nulls):
        verdict = "NO PRECISION EFFECT"
    else:
        verdict = "AMBIGUOUS"
    out["verdict_EMU"] = verdict
    out["smallest_p"] = min(ps) if ps else None
    out["holm_smallest_p_lt_0.0125"] = (min(ps) < HOLM_SMALLEST) if ps else None
    rh = [out["tasks"][t].get("REAL_in_place_of_EMU", {}).get("effect") for t in ("T10", "T2") if t in out["tasks"]]
    if rh and all(x is not None for x in rh):
        rv = "PRECISION EFFECT" if all(rh) else ("PARTIAL" if any(rh) else "NO PRECISION EFFECT or AMBIGUOUS")
        out["verdict_REAL"] = rv
        out["REAL_EMU_agree"] = (rv == verdict) or (rv.startswith("NO") and verdict in ("NO PRECISION EFFECT",
                                                                                         "AMBIGUOUS"))
    return out


# ------------------------------------------------------------------------------------------------ attribution
def _four(idx: dict, task: str, arm: str = "PN_a2") -> tuple[dict[str, np.ndarray], list[tuple]]:
    cells = {p: idx.get((task, p, arm), {}) for p in PRECS}
    keys = sorted(set.intersection(*[set(c) for c in cells.values()]) if all(cells.values()) else set(), key=str)
    return {p: np.array([y_correct(cells[p][k]) for k in keys], dtype=float) for p in PRECS}, keys


def effects(Y: dict[str, np.ndarray], sel: np.ndarray | None = None) -> dict[str, float]:
    m = {p: float(Y[p][sel].mean() if sel is not None else Y[p].mean()) for p in PRECS}
    return {"AME": 0.5 * ((m["W8A8"] - m["W8A16"]) + (m["W16A8"] - m["W16A16"])),
            "WME": 0.5 * ((m["W8A8"] - m["W16A8"]) + (m["W8A16"] - m["W16A16"])),
            "INT": (m["W8A8"] - m["W8A16"]) - (m["W16A8"] - m["W16A16"]),
            "d_W8A8": m["W8A8"] - m["W16A16"], "d_W8A16": m["W8A16"] - m["W16A16"],
            "d_W16A8": m["W16A8"] - m["W16A16"], **{f"share_{p}": m[p] for p in PRECS}}


def attribution_rule(e: dict[str, float], ci: dict[str, list[float]], thr: float) -> str:
    if e["AME"] >= ATTR_MAIN and e["WME"] < ATTR_OTHER and ci["AME"][0] > 0:
        return "ACTIVATION"
    if e["WME"] >= ATTR_MAIN and e["AME"] < ATTR_OTHER and ci["WME"][0] > 0:
        return "WEIGHT"
    if e["d_W8A8"] >= thr and e["d_W8A16"] < ATTR_OTHER and e["d_W16A8"] < ATTR_OTHER:
        return "INTERACTION"
    return "MIXED"


def gee_fit(task_rows: list[tuple[str, dict[str, np.ndarray], list[tuple]]]) -> dict[str, Any]:
    try:
        import pandas as pd
        import statsmodels.api as sm
        import statsmodels.formula.api as smf
    except ImportError as e:  # pragma: no cover
        return {"error": str(e)}
    recs = []
    for task, Y, keys in task_rows:
        for p in PRECS:
            for k, y in zip(keys, Y[p]):
                recs.append({"y": y, "Wq": int(p.startswith("W8")), "Aq": int(p.endswith("A8")), "task": task,
                             "slot": f"{task}|{k}"})
    df = pd.DataFrame(recs)
    if df.empty or df["y"].nunique() < 2:
        return {"error": "degenerate outcome"}
    form = "y ~ Wq * Aq" + (" + C(task)" if df["task"].nunique() > 1 else "")
    try:
        m = smf.gee(form, "slot", df, family=sm.families.Binomial(),
                    cov_struct=sm.cov_struct.Exchangeable()).fit()
        return {"formula": form, "params": m.params.to_dict(), "bse": m.bse.to_dict(), "pvalues": m.pvalues.to_dict(),
                "n_obs": int(len(df)), "n_clusters": int(df["slot"].nunique())}
    except (ValueError, np.linalg.LinAlgError, ZeroDivisionError) as e:
        return {"error": f"GEE failed: {e}"}


def attribution(idx: dict) -> dict[str, Any]:
    out: dict[str, Any] = {"rule": {"ACTIVATION": "AME >= 0.20 and WME < 0.10 and AME boot CI excludes 0",
                                    "WEIGHT": "WME >= 0.20 and AME < 0.10 and WME boot CI excludes 0",
                                    "INTERACTION": "W8A8-W16A16 >= threshold, W8A16-W16A16 < 0.10, W16A8-W16A16 < 0.10",
                                    "else": "MIXED"}, "tasks": {}}
    rng = np.random.default_rng(SEED)
    pooled_parts = []
    boot_by_task = {}
    for t in ("T10", "T2"):
        Y, keys = _four(idx, t)
        if not keys:
            out["tasks"][t] = {"missing": True}
            continue
        e = effects(Y)
        n = len(keys)
        bs = [effects(Y, rng.integers(0, n, n)) for _ in range(N_BOOT)]
        boot_by_task[t] = (Y, n)
        ci = {k: [float(np.quantile([b[k] for b in bs], 0.025)), float(np.quantile([b[k] for b in bs], 0.975))]
              for k in ("AME", "WME", "INT", "d_W8A8", "d_W8A16", "d_W16A8")}
        se_ame = float(np.std([b["AME"] for b in bs]))
        out["tasks"][t] = {"n_slots": n, "effects": e, "boot95": ci, "se_AME": se_ame,
                           "MDE_AME_80pct_power": 2.8 * se_ame, "verdict": attribution_rule(e, ci, THRESH_DIFF[t]),
                           "gee": gee_fit([(t, Y, keys)])}
        pooled_parts.append((t, Y, keys))
    if len(boot_by_task) == 2:
        pe = {k: 0.5 * (out["tasks"]["T10"]["effects"][k] + out["tasks"]["T2"]["effects"][k])
              for k in out["tasks"]["T10"]["effects"]}
        bs = []
        for _ in range(N_BOOT):
            parts = [effects(Y, rng.integers(0, n, n)) for (Y, n) in boot_by_task.values()]
            bs.append({k: 0.5 * (parts[0][k] + parts[1][k]) for k in parts[0]})
        ci = {k: [float(np.quantile([b[k] for b in bs], 0.025)), float(np.quantile([b[k] for b in bs], 0.975))]
              for k in ("AME", "WME", "INT", "d_W8A8", "d_W8A16", "d_W16A8")}
        se = float(np.std([b["AME"] for b in bs]))
        out["pooled"] = {"effects": pe, "boot95": ci, "se_AME": se, "MDE_AME_80pct_power": 2.8 * se,
                         "verdict": attribution_rule(pe, ci, 0.5 * (THRESH_DIFF["T10"] + THRESH_DIFF["T2"])),
                         "gee": gee_fit(pooled_parts), "stratified_by": "task (equal weights)"}
    return out


# ------------------------------------------------------------------------------------------------ population
def population40(rows: list[dict[str, Any]], idx: dict, fac: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"tasks": {}}
    e22 = read_jsonl(INP / "exp22" / "data" / "labels.jsonl")
    for t in ("T10", "T2"):
        per: dict[str, dict[int, dict[tuple, int]]] = defaultdict(lambda: defaultdict(dict))
        passm: dict[str, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
        for r in rows:
            if r["task"] == t and r["arm"].startswith("POP_d") and r["arm"].endswith("_a2.0"):
                d = int(r["direction_seed"])
                per[r["precision"]][d][(r["template"], int(r["slot"]))] = y_correct(r)
                passm[r["precision"]][d].append(int(bool(r.get("passed"))))
        if not per:
            out["tasks"][t] = {"missing": True}
            continue
        res: dict[str, Any] = {"per_direction": {}, "escape": {}, "pairs": {}}
        for p, dd in per.items():
            tw = fac.get(f"{t}|{p}|TWIN", {})
            tw_share, tw_pass = tw.get("Y_correct", 0.0), tw.get("pass", 1.0)
            res["per_direction"][p] = {str(d): {"n": len(v), "k_correct_off": int(sum(v.values())),
                                                "share": float(np.mean(list(v.values()))),
                                                "pass": float(np.mean(passm[p][d]))} for d, v in sorted(dd.items())}
            esc = {d for d, v in dd.items() if np.mean(list(v.values())) >= tw_share + 0.20
                   and np.mean(passm[p][d]) >= 0.8 * tw_pass}
            shares = [np.mean(list(v.values())) for v in dd.values()]
            res["escape"][p] = {"twin_share": tw_share, "twin_pass": tw_pass, "n_dirs": len(dd),
                                "escape_fraction": len(esc) / max(len(dd), 1), "escape_set": sorted(esc),
                                "mean_share": float(np.mean(shares)), "median_share": float(np.median(shares)),
                                "share_quartiles": [float(np.quantile(shares, q)) for q in (0.25, 0.5, 0.75)]}
        for pa, pb in itertools.combinations([p for p in ("W8A8", "W8A16", "W16A8", "W16A16", "W8A8REAL")
                                              if p in per], 2):
            dirs = sorted(set(per[pa]) & set(per[pb]))
            sa, sb = [], []
            for d in dirs:
                ks = sorted(set(per[pa][d]) & set(per[pb][d]))
                if ks:
                    sa.append(np.mean([per[pa][d][k] for k in ks]))
                    sb.append(np.mean([per[pb][d][k] for k in ks]))
            sa, sb = np.array(sa), np.array(sb)
            ea, eb = set(res["escape"][pa]["escape_set"]), set(res["escape"][pb]["escape_set"])
            b = len([d for d in dirs if d in ea and d not in eb])
            c = len([d for d in dirs if d in eb and d not in ea])
            try:
                wil = float(stats.wilcoxon(sa, sb, zero_method="wilcox").pvalue) if np.any(sa != sb) else 1.0
            except ValueError:
                wil = None
            rho = stats.spearmanr(sa, sb)[0] if len(sa) > 2 and np.std(sa) > 0 and np.std(sb) > 0 else None
            res["pairs"][f"{pa}_vs_{pb}"] = {
                "n_dirs": len(dirs), "mean_share_A": float(sa.mean()) if len(sa) else None,
                "mean_share_B": float(sb.mean()) if len(sb) else None,
                "mean_diff": float((sa - sb).mean()) if len(sa) else None, "wilcoxon_p": wil,
                "spearman": None if rho is None or not np.isfinite(rho) else float(rho),
                "jaccard_escape": len(ea & eb) / max(len(ea | eb), 1), "escape_both": sorted(ea & eb),
                "mcnemar_escape": mcnemar_exact(b, c)}
        # population-level attribution: the frozen rule on per-direction mean shares (bootstrap over directions)
        if all(p in per for p in PRECS):
            dirs = sorted(set.intersection(*[set(per[p]) for p in PRECS]))
            Y = {}
            for p in PRECS:
                Y[p] = np.array([np.mean([per[p][d][k] for k in sorted(set.intersection(
                    *[set(per[q][d]) for q in PRECS]))]) for d in dirs])
            e = effects(Y)
            rng = np.random.default_rng(SEED)
            bs = [effects(Y, rng.integers(0, len(dirs), len(dirs))) for _ in range(N_BOOT)]
            ci = {k: [float(np.quantile([b[k] for b in bs], 0.025)), float(np.quantile([b[k] for b in bs], 0.975))]
                  for k in ("AME", "WME", "INT", "d_W8A8", "d_W8A16", "d_W16A8")}
            res["population_attribution"] = {"n_dirs": len(dirs), "effects": e, "boot95": ci,
                                             "verdict": attribution_rule(e, ci, THRESH_DIFF[t])}
        # iteration-4 reproduction (exp22's per-direction counts at alpha 2, k 0-1)
        it4: dict[int, list[int]] = defaultdict(list)
        for r in e22:
            if r.get("task") == t and str(r.get("arm", "")).startswith("POP_d91") and str(r["arm"]).endswith("_a2.0") \
                    and int(r.get("sample_id", 9)) in (0, 1):
                lab = r.get("label")
                it4[int(r["arm"].split("_")[1][1:])].append(
                    int(bool(r.get("passed")) and lab not in (DEFAULT[t], "invalid", None)))
        if "W8A8" in per and it4:
            dirs = sorted(set(per["W8A8"]) & set(it4))
            a = np.array([np.mean(list(per["W8A8"][d].values())) for d in dirs])
            b = np.array([np.mean(it4[d]) for d in dirs])
            rho = stats.spearmanr(a, b)[0] if len(a) > 2 and np.std(a) > 0 and np.std(b) > 0 else None
            res["iter4_reproduction_W8A8_vs_exp22"] = {
                "n_dirs": len(dirs), "mean_W8A8": float(a.mean()), "mean_exp22": float(b.mean()),
                "mean_diff": float((a - b).mean()), "spearman": None if rho is None else float(rho)}
            if "W16A16" in per:
                c16 = np.array([np.mean(list(per["W16A16"][d].values())) if d in per["W16A16"] else np.nan
                                for d in dirs])
                res["iter4_vs_W16A16"] = {"mean_W16A16": float(np.nanmean(c16)), "mean_exp22": float(b.mean())}
        out["tasks"][t] = res
    return out


# ------------------------------------------------------------------------------------------------ other blocks
def unit_cross(idx: dict) -> dict[str, Any]:
    out: dict[str, Any] = {"tasks": {}}
    for t in ("T10", "T2"):
        cells = {("W8A8", "ban"): ("W8A8", "PN_a2"), ("W8A8", "banfree"): ("W8A8", "PNF_a2"),
                 ("W16A16", "ban"): ("W16A16", "PN_a2"), ("W16A16", "banfree"): ("W16A16", "PNF_a2")}
        sh = {}
        for (eng, unit), (p, arm) in cells.items():
            c = idx.get((t, p, arm), {})
            sh[f"{eng}|{unit}"] = {"N": len(c), "Y_correct": float(np.mean([y_correct(r) for r in c.values()]))
                                   if c else None}
        res = {"shares": sh,
               "engine_at_ban": contrast(idx, t, "PN_a2", "W8A8", "W16A16"),
               "engine_at_banfree": contrast(idx, t, "PNF_a2", "W8A8", "W16A16"),
               "unit_in_W8A8": contrast(idx, t, "PN_a2", "W8A8", "W8A8", arm_b="PNF_a2"),
               "unit_in_W16A16": contrast(idx, t, "PN_a2", "W16A16", "W16A16", arm_b="PNF_a2"),
               "PNF_a1": {p: (lambda c: float(np.mean([y_correct(r) for r in c.values()])) if c else None)(
                   idx.get((t, p, "PNF_a1"), {})) for p in ("W8A8", "W16A16")}}
        v = [sh[k]["Y_correct"] for k in ("W8A8|ban", "W8A8|banfree", "W16A16|ban", "W16A16|banfree")]
        if all(x is not None for x in v):
            w8b, w8f, w16b, w16f = v
            if min(w8b, w8f) >= 0.2 and max(w16b, w16f) <= 0.10:
                txt = "ENGINE: W8A8 high at both units, W16A16 low at both"
            elif w16b >= 0.2 and w16f <= 0.10:
                txt = "UNIT: W16A16 high at the ban unit, low at the ban-free unit"
            elif w16b >= 0.2:
                txt = "PROMPT/other: W16A16 high here at the ban unit (compare iteration 5's low share and Stage A.4)"
            else:
                txt = "MIXED: no single factor reproduces the pattern"
            res["decision"] = txt
        out["tasks"][t] = res
    return out


def t03_control(idx: dict) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for p in PRECS + ("W8A8REAL",):
        row = {}
        for arm in ("TWIN", "PN_a0.5", "PN_a1", "PN_a2"):
            c = idx.get(("T03", p, arm), {})
            if c:
                rs = list(c.values())
                row[arm] = {"N": len(rs), "Y_correct": float(np.mean([y_correct(r) for r in rs])),
                            "Y_attempted": float(np.mean([y_attempted(r) for r in rs])),
                            "pass": float(np.mean([bool(r.get("passed")) for r in rs]))}
        if row:
            out[p] = row
    out["moves_in_all_run"] = {p: (v.get("PN_a2", {}).get("Y_correct", 0) - v.get("TWIN", {}).get("Y_correct", 0)) >= 0.10
                               for p, v in out.items() if isinstance(v, dict) and "PN_a2" in v}
    out["paired_W8A8_vs_W16A16_PN_a2"] = contrast(idx, "T03", "PN_a2", "W8A8", "W16A16")
    return out


def dither_block(idx: dict) -> dict[str, Any]:
    out: dict[str, Any] = {"tasks": {}}
    for t in ("T10", "T2"):
        res = {}
        for v in (1, 2):
            dt, dp = f"DITHER_TWIN_v{v}", f"DITHER_PN2_v{v}"
            if not idx.get((t, "W16A16", dt)):
                continue
            r = {"DITHER_TWIN_vs_W16A16_TWIN": contrast(idx, t, dt, "W16A16", "W16A16", arm_b="TWIN"),
                 "DITHER_PN2_vs_W16A16_PN_a2": contrast(idx, t, dp, "W16A16", "W16A16", arm_b="PN_a2"),
                 "DITHER_PN2_vs_W8A8_PN_a2": contrast(idx, t, dp, "W16A16", "W8A8", arm_b="PN_a2")}
            a = r["DITHER_PN2_vs_W8A8_PN_a2"]
            b = r["DITHER_PN2_vs_W16A16_PN_a2"]
            c = r["DITHER_TWIN_vs_W16A16_TWIN"]
            if a.get("n_pairs") and b.get("n_pairs") and c.get("n_pairs"):
                if abs(a["diff"]) <= NULL_BAND and b["diff"] >= 0.15:
                    rd = "dither-PN2 ~ W8A8: re-rounding-sized noise amplification suffices"
                elif c["diff"] >= 0.15:
                    rd = "dither-twin alone moves: rounding-sized per-sample jitter suffices without displacement"
                elif b["diff"] < NULL_BAND:
                    rd = ("neither: independent rounding-sized noise does not recreate W8A8's movability; deterministic "
                          "re-rounding (not independent noise) or something else carries it (a dither null does NOT "
                          "rule out quantisation)")
                else:
                    rd = "partial: dither raises PN movability but not to W8A8's level"
                r["reading"] = rd
            res[f"v{v}"] = r
        out["tasks"][t] = res
    return out


def mechanism(idx: dict) -> dict[str, Any]:
    rows = read_jsonl(RES / "readouts_slots.jsonl")
    out: dict[str, Any] = {"n_slot_rows": len(rows), "precisions": {}}
    if not rows:
        return out
    rng = np.random.default_rng(SEED)

    def mean_ci(v: list[float]) -> dict[str, Any]:
        v = np.array([x for x in v if x is not None and np.isfinite(x)], dtype=float)
        if len(v) == 0:
            return {"mean": None}
        bs = v[rng.integers(0, len(v), size=(500, len(v)))].mean(1)
        return {"mean": float(v.mean()), "ci95": [float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))],
                "n": int(len(v))}

    by: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by[(r["task"], r["precision"])].append(r)
    for (t, p), rs in sorted(by.items()):
        d: dict[str, Any] = {"n": len(rs)}
        for cls in ("spec", "tail", "R"):
            d[f"divergence_{cls}"] = {l: mean_ci([r["divergence"][cls][l] for r in rs if cls in r["divergence"]])["mean"]
                                      for l in rs[0]["divergence"].get(cls, {})}
            d[f"cosine_{cls}"] = {l: mean_ci([r["cosine"][cls][l] for r in rs if cls in r["cosine"]])["mean"]
                                  for l in rs[0]["cosine"].get(cls, {})}
        for key in ("scale_change", "scale_changed_share", "rerounding_gain", "round_err"):
            agg: dict[str, dict[str, float | None]] = {}
            for cls in ("spec", "tail", "R"):
                if cls not in rs[0][key]:
                    continue
                agg[cls] = {k: mean_ci([r[key][cls].get(k) for r in rs])["mean"] for k in rs[0][key][cls]}
            d[key] = agg
        d["amplification_R"] = {l: mean_ci([r["amplification_R"][l] for r in rs])["mean"]
                                for l in rs[0]["amplification_R"]}
        d["kl_R"] = mean_ci([r["kl_R"] for r in rs])
        d["kl_tf_mean"] = mean_ci([r.get("kl_tf_mean") for r in rs if r.get("kl_tf_mean") is not None])
        d["argmax_R_changed_share"] = float(np.mean([r["argmax_R_changed"] for r in rs]))
        out["precisions"][f"{t}|{p}"] = d
    # per-slot output KL vs per-slot flip W8A8 vs W16A16 (Spearman across slots)
    for t in ("T10", "T2"):
        kl8 = {(r["template"], r["slot"]): r.get("kl_tf_mean") for r in rows if r["task"] == t and r["precision"] == "W8A8"}
        kl16 = {(r["template"], r["slot"]): r.get("kl_tf_mean") for r in rows if r["task"] == t and r["precision"] == "W16A16"}
        A = idx.get((t, "W8A8", "PN_a2"), {})
        Bc = idx.get((t, "W16A16", "PN_a2"), {})
        xs, ys, zs = [], [], []
        for (w, k), v in kl8.items():
            key = (w, int(k), None)
            if key in A and key in Bc and v is not None and kl16.get((w, k)) is not None:
                xs.append(v - kl16[(w, k)])
                zs.append(v)
                ys.append(int(A[key].get("label") != Bc[key].get("label")))
        if len(xs) > 3 and np.std(ys) > 0:
            out[f"{t}_spearman_klDiff_vs_labelflip"] = float(stats.spearmanr(xs, ys)[0])
            out[f"{t}_spearman_klW8A8_vs_labelflip"] = float(stats.spearmanr(zs, ys)[0])
            out[f"{t}_n_slots_kl_flip"] = len(xs)
    # clean-vs-clean divergence between precisions and the kernel-only floor (saved states)
    try:
        import torch
        floor: dict[str, Any] = {}
        sd = ROOT / "states"
        for t in ("T10", "T2"):
            for w in ("W1", "W2", "W3", "W4", "W5"):
                ref = sd / f"clean_{t}_{w}_W16A16.pt"
                if not ref.exists():
                    continue
                R = torch.load(ref)
                for p in ("W16A16mm", "W16A8", "W8A16", "W8A8", "W8A8REAL"):
                    f = sd / f"clean_{t}_{w}_{p}.pt"
                    if not f.exists():
                        continue
                    S = torch.load(f)
                    for l in R:
                        rel = float(((S[l].float() - R[l].float()).norm(dim=-1) / R[l].float().norm(dim=-1)).mean())
                        floor.setdefault(f"{t}|{p}_vs_W16A16", {}).setdefault(str(l), []).append(rel)
        out["clean_vs_clean_rel_divergence"] = {k: {l: float(np.mean(v)) for l, v in d.items()} for k, d in floor.items()}
    except (ImportError, RuntimeError, OSError) as e:
        out["clean_vs_clean_error"] = str(e)
    return out


def js_div(p: Counter, q: Counter) -> float:
    keys = sorted(set(p) | set(q))
    a = np.array([p.get(k, 0) for k in keys], dtype=float)
    b = np.array([q.get(k, 0) for k in keys], dtype=float)
    if a.sum() == 0 or b.sum() == 0:
        return float("nan")
    a, b = a / a.sum(), b / b.sum()
    m = 0.5 * (a + b)
    def kl(x, y):
        nz = x > 0
        return float((x[nz] * np.log2(x[nz] / y[nz])).sum())
    return 0.5 * kl(a, m) + 0.5 * kl(b, m)


def landing(idx: dict, ref: dict[str, Any] | None) -> dict[str, Any]:
    out: dict[str, Any] = {"rule": "modal correct off-default label ('other' never a landing); lead >= 15 points over "
                                   "the next; compared with the base runner-up r_u (exp24)", "cells": {}, "js": {}}
    ru = {t: LABEL_ALIAS.get(v, v) for t, v in (ref or {}).get("r_u", {}).items()}
    for (t, p, arm), c in sorted(idx.items()):
        if arm not in ("PN_a2", "PN_a1", "PNF_a2") and not arm.startswith("DITHER_PN2"):
            continue
        labs = [LABEL_ALIAS.get(r["label"], r["label"]) for r in c.values() if y_correct(r) and r["label"] != "other"]
        if len(labs) < 5:
            out["cells"][f"{t}|{p}|{arm}"] = {"n_correct_off_catalogue": len(labs), "landing": None}
            continue
        cnt = Counter(labs).most_common()
        lead = (cnt[0][1] - (cnt[1][1] if len(cnt) > 1 else 0)) / len(labs)
        out["cells"][f"{t}|{p}|{arm}"] = {"n_correct_off_catalogue": len(labs), "composition": dict(cnt),
                                          "modal": cnt[0][0], "lead": lead, "clear": lead >= 0.15,
                                          "equals_r_u": (cnt[0][0] == ru.get(t)) if ru.get(t) else None}
    rng = np.random.default_rng(SEED)
    for t in ("T10", "T2", "T03"):
        for pa, pb in itertools.combinations(PRECS + ("W8A8REAL",), 2):
            A = idx.get((t, pa, "PN_a2"), {})
            Bc = idx.get((t, pb, "PN_a2"), {})
            keys = sorted(set(A) & set(Bc), key=str)
            if not keys:
                continue
            def comp(rows_):
                return Counter(LABEL_ALIAS.get(r["label"], r["label"]) for r in rows_ if y_correct(r)
                               and r["label"] != "other")
            ca, cb = comp([A[k] for k in keys]), comp([Bc[k] for k in keys])
            if sum(ca.values()) < 5 or sum(cb.values()) < 5:
                continue
            obs = js_div(ca, cb)
            null = []
            for _ in range(N_BOOT):
                sw = rng.random(len(keys)) < 0.5
                ra = [Bc[k] if s else A[k] for k, s in zip(keys, sw)]
                rb = [A[k] if s else Bc[k] for k, s in zip(keys, sw)]
                v = js_div(comp(ra), comp(rb))
                if np.isfinite(v):
                    null.append(v)
            out["js"][f"{t}|{pa}_vs_{pb}"] = {"js_bits": obs, "perm_p": float((np.sum(np.array(null) >= obs) + 1) /
                                                                               (len(null) + 1)) if null else None,
                                              "n_correct_A": sum(ca.values()), "n_correct_B": sum(cb.values())}
    return out


def dose() -> dict[str, Any]:
    rows = read_jsonl(DATA / "realised.jsonl")
    out: dict[str, Any] = {}
    by: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        arm = "POP40_a2" if str(r.get("arm", "")).startswith("POP_d") else r.get("arm")
        by[(r["task"], r["precision"], arm)].append(r)
    for (t, p, a), rs in sorted(by.items()):
        d = {"n_prefills": len(rs)}
        d["disp_S_mean"] = {l: float(np.mean([r["disp_S"][l] for r in rs])) for l in ("12", "17", "23", "29", "35")}
        d["disp_R_mean"] = {l: float(np.mean([r["disp_R"][l] for r in rs])) for l in ("12", "23", "29", "35")}
        re_ = [max(r["rel_err_along_u"].values()) for r in rs if r.get("rel_err_along_u")]
        d["rel_err_along_u_max"] = float(max(re_)) if re_ else None
        comp = [r["u_component_mean"]["12"] / r["target_mean"]["12"] for r in rs if r.get("u_component_mean")]
        d["u_component_over_target_b12_mean"] = float(np.mean(comp)) if comp else None
        rr = [r["ratio_to_residual"] for r in rs if r.get("ratio_to_residual")]
        if rr:
            d["ratio_to_residual"] = {l: {"mean_of_ratios": float(np.mean([x[l]["mean_of_ratios"] for x in rr])),
                                          "ratio_of_means": float(np.mean([x[l]["ratio_of_means"] for x in rr]))}
                                      for l in rr[0]}
        out[f"{t}|{p}|{a}"] = d
    return out


# ------------------------------------------------------------------------------------------------ engine check
def engine_check(idx: dict, rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    raw = {r["sample_id"]: r for r in read_jsonl(DATA / "samples_raw.jsonl")}
    e19raw = {r["sample_id"]: r for r in read_jsonl(INP / "exp19" / "data" / "samples_raw.jsonl")
              if r["task"] in ("T10", "T2", "T03")}
    e19lab = {r["sample_id"]: r for r in read_jsonl(INP / "exp19" / "data" / "samples.jsonl")
              if r["task"] in ("T10", "T2", "T03")}

    def toks(r):
        t = r.get("token_ids")
        return json.loads(t) if isinstance(t, str) else t

    def cmp(prec: str, tasks: tuple[str, ...], arms: tuple[str, ...], ws: tuple[str, ...] | None = None) -> dict[str, Any]:
        n = same = lab_same = 0
        per_arm: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
        for r in rows:
            if r["precision"] != prec or r["task"] not in tasks or r["arm"] not in arms:
                continue
            if ws and r["template"] not in ws:
                continue
            sid19 = f"{r['task']}|{r['arm']}|{r['template']}|{r['slot']}"
            if sid19 not in e19raw:
                continue
            a = toks(raw[r["sample_id"]]) if r["sample_id"] in raw else None
            b = toks(e19raw[sid19])
            ident = a == b
            ls = (r.get("label") == e19lab.get(sid19, {}).get("label"))
            n += 1
            same += ident
            lab_same += ls
            pa = per_arm[r["arm"]]
            pa[0] += 1
            pa[1] += ident
            pa[2] += ls
        return {"n": n, "byte_identity_rate": same / n if n else None, "label_agreement": lab_same / n if n else None,
                "per_arm": {a: {"n": v[0], "byte_identity": v[1] / v[0], "label_agreement": v[2] / v[0]}
                            for a, v in per_arm.items()}}

    def gate25(prec: str, arm: str) -> dict[str, Any]:
        keys = [("W1", k) for k in range(10)] + [("W2", k) for k in range(10)] + [("W3", k) for k in range(5)]
        n = ident = lab = 0
        for w, k in keys:
            sid = f"T2|{prec}|{arm}|{w}|{k}"
            sid19 = f"T2|{arm}|{w}|{k}"
            r = next((x for x in rows if x["sample_id"] == sid), None)
            if r is None or sid19 not in e19raw:
                continue
            n += 1
            ident += toks(raw[sid]) == toks(e19raw[sid19])
            lab += r.get("label") == e19lab.get(sid19, {}).get("label")
        return {"n": n, "byte_identity": ident / n if n else None, "label_agreement": lab / n if n else None}

    out["REAL_vs_exp19"] = {"gate_25_TWIN": gate25("W8A8REAL", "TWIN"), "gate_25_PN_a1": gate25("W8A8REAL", "PN_a1"),
                            "all_rows": cmp("W8A8REAL", ("T10", "T2", "T03"), ("TWIN", "PN_a0.5", "PN_a1", "PN_a2"))}
    out["EMU_vs_exp19"] = {"gate_25_TWIN": gate25("W8A8", "TWIN"), "gate_25_PN_a1": gate25("W8A8", "PN_a1"),
                           "all_rows": cmp("W8A8", ("T10", "T2", "T03"), ("TWIN", "PN_a0.5", "PN_a1", "PN_a2"))}
    g = out["EMU_vs_exp19"]["gate_25_TWIN"]
    out["EMU_gate_twin_label_agreement_ge_0.9"] = (g["label_agreement"] or 0) >= 0.9 if g["n"] else None
    gr = out["REAL_vs_exp19"]["gate_25_TWIN"]
    out["REAL_gate_twin_label_agreement_ge_0.9"] = (gr["label_agreement"] or 0) >= 0.9 if gr["n"] else None
    # EMU vs REAL per cell (same slots)
    emu_real = {}
    for t in ("T10", "T2", "T03"):
        for arm in ("TWIN", "PN_a0.5", "PN_a1", "PN_a2"):
            A = idx.get((t, "W8A8", arm), {})
            Bc = idx.get((t, "W8A8REAL", arm), {})
            keys = sorted(set(A) & set(Bc), key=str)
            if not keys:
                continue
            ident = sum(toks(raw[A[k]["sample_id"]]) == toks(raw[Bc[k]["sample_id"]]) for k in keys)
            lab = sum(A[k].get("label") == Bc[k].get("label") for k in keys)
            emu_real[f"{t}|{arm}"] = {"n": len(keys), "byte_identity": ident / len(keys), "label_agreement": lab / len(keys),
                                      "Y_correct_EMU": float(np.mean([y_correct(A[k]) for k in keys])),
                                      "Y_correct_REAL": float(np.mean([y_correct(Bc[k]) for k in keys]))}
    out["EMU_vs_REAL"] = emu_real
    # W16A16 anchor: 25 exp27 TWIN slots (T10, W1-W5 k0-4)
    e27 = {(r["template"], int(r["slot"])): r for r in read_jsonl(INP / "exp27" / "data" / "samples_raw.jsonl")
           if r.get("task") == "T10" and r.get("arm") == "TWIN"}
    e27l = {r["sample_id"]: r for r in read_jsonl(INP / "exp27" / "data" / "labels.jsonl")}
    n = ident = lab = 0
    for w in ("W1", "W2", "W3", "W4", "W5"):
        for k in range(5):
            sid = f"T10|W16A16|TWIN|{w}|{k}"
            if sid not in raw or (w, k) not in e27:
                continue
            r = next((x for x in rows if x["sample_id"] == sid), None)
            n += 1
            ident += toks(raw[sid]) == toks(e27[(w, k)])
            l27 = e27l.get(e27[(w, k)].get("sample_id"), {}).get("label")
            lab += (r or {}).get("label") == l27
    out["W16A16_anchor_vs_exp27"] = {"n": n, "byte_identity": ident / n if n else None,
                                     "label_agreement": lab / n if n else None,
                                     "pass_ge_0.9": (lab / n >= 0.9) if n else None}
    return out


def iter4_reference() -> dict[str, Any]:
    p = RES / "iter4_reference.json"
    return json.loads(p.read_text()) if p.exists() else {}


def verdict_text(prim: dict[str, Any], attr: dict[str, Any], ec: dict[str, Any]) -> dict[str, Any]:
    v = prim.get("verdict_EMU")
    cls = attr.get("pooled", {}).get("verdict")
    gate = ec.get("EMU_gate_twin_label_agreement_ge_0.9")
    if gate is None:
        cond = " (EMU gate not evaluated)"
    elif gate:
        cond = ""
    else:
        cond = " (CONDITIONAL ON FP8 EMULATION: the EMU gate did not pass; an sm_89 rerun of W8A8 is requested)"
    if v == "PRECISION EFFECT":
        cons = ("Every iteration-4 internal claim (same-seed contrast, task-spec site, plan noise as the cheapest knob, "
                "frozen screen) is written as a property of the FP8 W8A8 engine; the effect is reported as a deployment "
                f"finding (an 8-bit engine changes how easily a model's algorithm choice can be nudged without changing "
                f"its default), attribution class {cls}.")
    elif v == "NO PRECISION EFFECT":
        cons = ("The unit cross locates the iteration-5 shrinkage and the iteration-4 claims are restored as model "
                "properties.")
    elif v == "PARTIAL":
        cons = ("The precision effect holds on one decisive task only: iteration-4 claims on that task are engine "
                "properties; the other task is reported as unresolved.")
    else:
        cons = "No frozen consequence applies; the result is reported as ambiguous."
    return {"verdict": v, "attribution_pooled": cls, "REAL_verdict": prim.get("verdict_REAL"),
            "consequence": cons + cond, "emu_gate_pass": gate}


def run(out_dir: Path = RES, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if rows is None:
        rows = merge_rows()
    idx = cell_index(rows)
    it4 = iter4_reference()
    fac = factorial(rows)
    prim = primary(idx, it4.get("tasks"))
    attr = attribution(idx)
    res = {"factorial": fac, "primary_E": prim, "attribution": attr, "population40": population40(rows, idx, fac),
           "unit_cross": unit_cross(idx), "t03_control": t03_control(idx), "dither": dither_block(idx),
           "landing": landing(idx, json.loads((PRED / "landing_ref.json").read_text())
                              if (PRED / "landing_ref.json").exists() else None)}
    if out_dir == RES:
        res["mechanism"] = mechanism(idx)
        res["dose"] = dose()
        res["engine_check"] = engine_check(idx, rows)
    else:
        res["engine_check"] = {}
    res["verdict"] = verdict_text(prim, attr, res["engine_check"])
    for k, v in res.items():
        write_json(out_dir / f"{k}.json", v)
    return res


# ------------------------------------------------------------------------------------------------ synthetic test
def synthetic_rows(kind: str, seed: int = 7) -> list[dict[str, Any]]:
    rng = np.random.default_rng(seed)
    alt = {"T10": "dfs", "T2": "bf_spfa"}
    rows = []
    for t in ("T10", "T2"):
        for w in ("W1", "W2", "W3", "W4", "W5"):
            for k in range(10):
                base = rng.random()
                for p in PRECS:
                    for arm in ("TWIN", "PN_a2"):
                        if arm == "TWIN":
                            pr = 0.0
                        elif kind == "activation":
                            pr = 0.6 if p.endswith("A8") else 0.05
                        else:
                            pr = 0.05
                        off = base < pr if arm == "PN_a2" else False
                        rows.append({"sample_id": f"{t}|{p}|{arm}|{w}|{k}", "task": t, "precision": p, "arm": arm,
                                     "template": w, "slot": k, "direction_seed": None, "passed": True,
                                     "label": alt[t] if off else DEFAULT[t], "finish_reason": "fence"})
    return rows


def synthetic_test(out_dir: Path) -> dict[str, Any]:
    res = {}
    for kind, want_v, want_a in (("activation", "PRECISION EFFECT", "ACTIVATION"), ("null", "NO PRECISION EFFECT", None)):
        rows = synthetic_rows(kind)
        r = run(out_dir / kind, rows)
        got_v = r["primary_E"]["verdict_EMU"]
        got_a = r["attribution"].get("pooled", {}).get("verdict")
        t = r["primary_E"]["tasks"]["T10"]["mcnemar"]
        sc = float(stats.binomtest(t["b"], t["b"] + t["c"], 0.5).pvalue) if t["b"] + t["c"] else 1.0
        res[kind] = {"verdict": got_v, "verdict_ok": got_v == want_v, "attribution": got_a,
                     "attribution_ok": (got_a == want_a) if want_a else True,
                     "mcnemar_matches_scipy": abs(sc - t["p_two_sided"]) < 1e-12}
    res["all_ok"] = all(v["verdict_ok"] and v["attribution_ok"] and v["mcnemar_matches_scipy"] for v in res.values())
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()
    if args.synthetic:
        od = Path(args.out_dir) if args.out_dir else RES / "synthetic"
        res = synthetic_test(od)
        write_json(od / "synthetic_test.json", res)
        print(json.dumps(res, indent=1))
        return
    r = run()
    print(json.dumps({"verdict": r["verdict"], "primary": {t: {k: v for k, v in d.items() if k in (
        "share_A", "share_B", "diff", "mcnemar", "n_pairs")} for t, d in r["primary_E"]["tasks"].items()}}, indent=1))


if __name__ == "__main__":
    main()
