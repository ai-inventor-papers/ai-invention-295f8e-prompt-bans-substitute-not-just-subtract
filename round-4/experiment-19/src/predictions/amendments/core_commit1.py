#!/usr/bin/env python3
"""Committed analysis core (plan 6.1-6.5): per-arm rows, knob classes, hull pricing, the 2,000-replicate bootstrap
with the best-setting selection inside every replicate, and the pre-registered C1 rule.

Inputs: data/samples.jsonl (this artifact's labelled rows) and data/reused_rows.jsonl (iteration-3 veto rows and
their own twins). Correct = passed and label != 'invalid'. Idea categories = mechanism labels after the committed
'other' mapping (audit/other_map.json: LABELLER MISS -> catalogue label, CATALOGUE VARIANT -> parent mode or a named
variant, DEGENERATE -> excluded from Hill but counted as passed, NOVEL -> its own category; before the audit, and as
sensitivity s6, 'other' is one category or excluded).
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from typing import Any

import numpy as np

from analysis.hull import Hull, dial_interp_h5, fixed_uniforms
from analysis.stats_step0 import boot_rarefied_hill1, rarefied_hill1

DEPTH = 25
E6 = ("T03", "T05", "T06", "T10", "T1", "T2")
# knob classes: name -> (settings in dial order, reference arm). VETO classes use the reused rows' own twin.
CLASSES: dict[str, dict[str, Any]] = {
    "PN": {"settings": ["PN_a0.5", "PN_a1", "PN_a2", "PN_a4"], "ref": "TWIN", "na": False},
    "TEMP": {"settings": ["T1.3", "T1.6"], "ref": "TWIN", "na": True},
    "TOPK10": {"settings": ["TOPK10"], "ref": "TWIN", "na": True},
    "NONCE": {"settings": ["NONCE"], "ref": "TWIN", "na": True},
    "NOVELTY": {"settings": ["NOVELTY"], "ref": "TWIN", "na": True},
    "SEMSEED": {"settings": ["SEMSEED"], "ref": "TWIN", "na": True},
    "VETO_1SHOT": {"settings": ["VETO_1SHOT"], "ref": "REUSED_TWIN", "na": True, "reused": True},
    "VETO_PERSIST": {"settings": ["VETO_PERSIST"], "ref": "REUSED_TWIN", "na": True, "reused": True},
    "VETO_ITER": {"settings": ["VETO_ITER1", "VETO_ITER2", "VETO_ITER3"], "ref": "REUSED_TWIN", "na": True,
                  "reused": True},
    # pre-registered sensitivity s2 (added to NA only in s2)
    "MINP": {"settings": ["MINP_T1.6", "MINP_T2.0"], "ref": "TWIN", "na": False, "s2": True},
    "VS": {"settings": ["VS"], "ref": "TWIN", "na": False, "s2": True},
    # descriptive (never in the C1 rule)
    "PN_EXTRA": {"settings": ["PN_a0.5", "PN_a1", "PN_a2", "PN_a4", "PN_a8"], "ref": "TWIN", "na": False,
                 "descriptive": True},
    "PNPLAIN": {"settings": ["PNPLAIN_a1"], "ref": "PLAIN", "na": False, "descriptive": True},
}
NA_PRIMARY = [k for k, v in CLASSES.items() if v["na"]]
NA_S2 = NA_PRIMARY + ["MINP", "VS"]


def idea_label(r: dict[str, Any], other_map: dict[str, str] | None, convention: str = "mapped") -> str | None:
    """Hill category of a CORRECT program (None = excluded from Hill counts)."""
    lab = r["label"]
    if lab == "other":
        if convention == "exclude":
            return None
        if convention == "one" or other_map is None:
            return "other"
        m = other_map.get(r.get("code_sha256") or "", "other")
        return None if m == "DEGENERATE" else m
    return lab


def is_correct(r: dict[str, Any]) -> bool:
    return bool(r.get("passed")) and r.get("label") not in ("invalid", None)


class TaskData:
    """Per task: for each arm, arrays (category index or -1, passed, stratum index, slot key)."""

    def __init__(self, task: str, rows: list[dict[str, Any]], other_map: dict[str, str] | None,
                 convention: str = "mapped"):
        self.task = task
        cats: set[str] = set()
        by_arm: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in rows:
            by_arm[r["arm"]].append(r)
            if is_correct(r):
                c = idea_label(r, other_map, convention)
                if c is not None:
                    cats.add(c)
        self.cats = sorted(cats)
        ci = {c: i for i, c in enumerate(self.cats)}
        self.arms: dict[str, dict[str, Any]] = {}
        for arm, rs in by_arm.items():
            rs = sorted(rs, key=lambda r: (str(r.get("template")), str(r.get("slot"))))
            cat = np.array([ci[c] if (is_correct(r) and (c := idea_label(r, other_map, convention)) is not None)
                            else -1 for r in rs], dtype=int)
            pas = np.array([is_correct(r) for r in rs], dtype=bool)
            strata = [str(r.get("template")) for r in rs]
            su = sorted(set(strata))
            sidx = np.array([su.index(s) for s in strata], dtype=int)
            keys = [f"{r.get('template')}|{r.get('slot')}" for r in rs]
            self.arms[arm] = {"cat": cat, "pass": pas, "stratum": sidx, "n_strata": len(su), "keys": keys,
                              "engine": rs[0].get("engine"), "n": len(rs)}

    def vertex(self, arm: str, idx: np.ndarray | None = None) -> tuple[np.ndarray, float, int]:
        a = self.arms[arm]
        cat = a["cat"] if idx is None else a["cat"][idx]
        pas = a["pass"] if idx is None else a["pass"][idx]
        n = len(cat)
        r = np.bincount(cat[cat >= 0], minlength=len(self.cats)).astype(float) / max(n, 1)
        return r, float(pas.mean()) if n else float("nan"), n

    def counts(self, arm: str) -> Counter:
        a = self.arms[arm]
        return Counter(self.cats[c] for c in a["cat"] if c >= 0)


def class_vertices(td: TaskData, cls: str, ref_override: str | None = None) -> list[str] | None:
    spec = CLASSES[cls]
    ref = ref_override or spec["ref"]
    if ref not in td.arms:
        return None
    sets = [s for s in spec["settings"] if s in td.arms]
    if not sets:
        return None
    return [ref] + sets


def class_price(td: TaskData, cls: str, U: np.ndarray, idx_by_arm: dict[str, np.ndarray] | None = None,
                edges: str = "all", with_price: bool = True, refine: bool = True) -> dict[str, Any] | None:
    arms = class_vertices(td, cls)
    if arms is None:
        return None
    R, P = [], []
    for a in arms:
        r, p, _ = td.vertex(a, None if idx_by_arm is None else idx_by_arm.get(a))
        R.append(r)
        P.append(p)
    h = Hull(np.array(R), np.array(P), U, edges=edges)
    s = h.summary(refine=refine, with_price=with_price)
    s["arms"] = arms
    s["vertex_cost"] = h.cost_v.round(3).tolist()
    return s


def step0_hill(counts: Counter) -> float:
    c = [v for _, v in counts.most_common()]
    n = sum(c)
    if n == 0:
        return float("nan")
    if n < DEPTH:
        return rarefied_hill1(c, n, 1000, np.random.default_rng(0)) if n > 1 else 1.0
    return rarefied_hill1(c, DEPTH, 1000, np.random.default_rng(0))


def knob_rows(tds: dict[str, TaskData], ref_of: dict[str, str]) -> list[dict[str, Any]]:
    """Plan 6.1: one row per (task, arm), Step-0 statistic with its 90% interval."""
    out = []
    for t, td in tds.items():
        for arm, a in td.arms.items():
            cnt = td.counts(arm)
            n_c = sum(cnt.values())
            ref = ref_of.get(arm, "TWIN")
            p_ref = float(td.arms[ref]["pass"].mean()) if ref in td.arms else None
            p = float(a["pass"].mean())
            cc = [v for _, v in cnt.most_common()]
            ci = boot_rarefied_hill1(cc, DEPTH, n_boot=2000, n_sub=200, rng=np.random.default_rng(1), conf=0.90) \
                if n_c >= DEPTH else (float("nan"), float("nan"))
            out.append({"task": t, "arm": arm, "knob_class": knob_of(arm), "engine": a["engine"],
                        "reference_arm": ref, "n": a["n"], "n_correct": int(a["pass"].sum()),
                        "n_correct_hill": n_c, "pass": p,
                        "pass_cost_pts": (100 * (p_ref - p)) if p_ref is not None else None,
                        "correct_comp": dict(cnt.most_common()), "hill25_step0": step0_hill(cnt),
                        "ci90": list(ci), "depth_flag": n_c < DEPTH})
    return out


def knob_of(arm: str) -> str:
    for k, v in CLASSES.items():
        if k in ("PN_EXTRA",):
            continue
        if arm in v["settings"]:
            return k
    if arm in ("TWIN", "PLAIN", "REUSED_TWIN"):
        return "REF"
    if arm == "PN_a8":
        return "PN_EXTRA"
    return "OTHER"


# ------------------------------------------------------------------------------------------------ bootstrap
def resample_idx(td: TaskData, rng: np.random.Generator, scheme: str = "stratified") -> dict[str, np.ndarray]:
    """Programs resampled with replacement within each arm, stratified by template (primary); template-cluster (s4:
    resample templates, then programs within them); slot-paired (s5: resample (template, slot) keys jointly across
    every arm of this artifact; reused rows resample within their arm)."""
    out: dict[str, np.ndarray] = {}
    if scheme == "slot_paired":
        keyset = sorted({k for arm, a in td.arms.items() if not arm.startswith(("VETO", "REUSED")) for k in a["keys"]})
        draw = rng.choice(len(keyset), size=len(keyset), replace=True)
        drawn = [keyset[i] for i in draw]
    if scheme == "template_cluster":
        allw = sorted({k.split("|")[0] for a in td.arms.values() for k in a["keys"]})
        wdraw = [allw[i] for i in rng.choice(len(allw), size=len(allw), replace=True)]
    for arm, a in td.arms.items():
        n = a["n"]
        if scheme == "slot_paired" and not arm.startswith(("VETO", "REUSED")):
            pos = {k: i for i, k in enumerate(a["keys"])}
            idx = [pos[k] for k in drawn if k in pos]
            if len(idx) < max(1, n // 2):
                idx = list(rng.integers(0, n, size=n))
            out[arm] = np.array(idx, dtype=int)
            continue
        if scheme == "template_cluster":
            ws = [k.split("|")[0] for k in a["keys"]]
            groups = defaultdict(list)
            for i, w in enumerate(ws):
                groups[w].append(i)
            idx = []
            for w in wdraw:
                g = groups.get(w)
                if g:
                    idx.extend(rng.choice(g, size=len(g), replace=True).tolist())
            if not idx:
                idx = list(rng.integers(0, n, size=n))
            out[arm] = np.array(idx, dtype=int)
            continue
        idx = np.empty(n, dtype=int)
        pos = 0
        for s in range(a["n_strata"]):
            members = np.where(a["stratum"] == s)[0]
            k = len(members)
            idx[pos:pos + k] = members[rng.integers(0, k, size=k)]
            pos += k
        out[arm] = idx
    return out


def task_replicates(args: tuple) -> dict[str, Any]:
    """Worker: B bootstrap replicates of one task -> per-class H5/P15/P20 per replicate."""
    td, classes, B, seed, scheme, n_sub, edges = args
    U = fixed_uniforms(n_sub)
    rng = np.random.default_rng(seed)
    res: dict[str, dict[str, list]] = {c: {"H5": [], "P15": [], "P20": []} for c in classes}
    for b in range(B):
        idx = resample_idx(td, rng, scheme)
        for c in classes:
            s = class_price(td, c, U, idx, edges=edges, with_price=True, refine=False)
            for k in ("H5", "P15", "P20"):
                res[c][k].append(None if s is None else s[k])
    return {"task": td.task, "res": res}


def run_bootstrap(tds: dict[str, TaskData], classes: list[str], B: int, seed: int, scheme: str = "stratified",
                  n_sub: int = 200, edges: str = "all", workers: int = 6) -> dict[str, dict[str, Any]]:
    import multiprocessing as mp

    jobs = []
    chunk = max(1, B // workers)
    for t, td in tds.items():
        start = 0
        part = 0
        while start < B:
            nb = min(chunk, B - start)
            jobs.append((td, [c for c in classes if class_vertices(td, c) is not None], nb,
                         seed + 1000 * part + hash(t) % 997, scheme, n_sub, edges))
            start += nb
            part += 1
    out: dict[str, dict[str, Any]] = {t: {} for t in tds}
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as ex:
        for r in ex.map(task_replicates, jobs):
            for c, d in r["res"].items():
                o = out[r["task"]].setdefault(c, {"H5": [], "P15": [], "P20": []})
                for k in ("H5", "P15", "P20"):
                    o[k].extend(d[k])
    return out


def pct_ci(x: list, lo: float = 2.5, hi: float = 97.5) -> list[float | None]:
    v = np.array([np.nan if a is None else a for a in x], dtype=float)
    v = v[np.isfinite(v)]
    if len(v) == 0:
        return [None, None]
    return [float(np.percentile(v, lo)), float(np.percentile(v, hi))]


# ------------------------------------------------------------------------------------------------ C1
def best_na(h5: dict[str, float | None], na: list[str]) -> tuple[str | None, float | None]:
    cand = [(c, h5.get(c)) for c in na if h5.get(c) is not None and np.isfinite(h5.get(c))]
    if not cand:
        return None, None
    c, v = max(cand, key=lambda x: x[1])
    return c, v


def c1_decide(point: dict[str, dict[str, float | None]], boot: dict[str, dict[str, Any]], tasks: tuple[str, ...],
              na: list[str], B: int, seed: int) -> dict[str, Any]:
    """Pre-registered rule: CONFIRMED iff count1 >= 3 AND count2 >= 4 AND CI_low(D_bar) > 0; DISCONFIRMED iff
    count1 <= 1 OR #{t: H5_best > H5_PN} >= 4; otherwise PARTIAL."""
    per = {}
    D = {}
    for t in tasks:
        h5 = point.get(t, {})
        pn = h5.get("PN")
        bc, bv = best_na(h5, na)
        if pn is None or bv is None:
            per[t] = {"status": "UNDECIDABLE", "H5_PN": pn, "best_na": bc, "H5_best": bv}
            continue
        D[t] = pn - bv
        # per-task bootstrap probability P(H5_PN > H5_best), best chosen inside each replicate
        bt = boot.get(t, {})
        nrep = len(bt.get("PN", {}).get("H5", []))
        wins, dts = 0, []
        for b in range(nrep):
            hp = bt["PN"]["H5"][b]
            hb = [bt[c]["H5"][b] for c in na if c in bt and bt[c]["H5"][b] is not None]
            if hp is None or not hb:
                dts.append(np.nan)
                continue
            dts.append(hp - max(hb))
            wins += hp > max(hb)
        per[t] = {"H5_PN": pn, "best_na": bc, "H5_best": bv, "D_t": D[t], "P_boot_PN_gt_best": wins / max(nrep, 1),
                  "D_t_boot_ci95": pct_ci(dts), "D_t_boot": dts}
    decided = [t for t in tasks if t in D]
    count1 = sum(1 for t in decided if per[t]["H5_PN"] >= 1.5)
    count2 = sum(1 for t in decided if per[t]["H5_PN"] > per[t]["H5_best"])
    n_best_wins = sum(1 for t in decided if per[t]["H5_best"] > per[t]["H5_PN"])
    D_bar = float(np.mean([D[t] for t in decided])) if decided else None
    rng = np.random.default_rng(seed)
    Dstar = []
    for _ in range(B):
        draw = rng.choice(decided, size=len(decided), replace=True)
        vals = []
        for t in draw:
            dd = np.array(per[t]["D_t_boot"], dtype=float)
            dd = dd[np.isfinite(dd)]
            vals.append(dd[rng.integers(0, len(dd))] if len(dd) else D[t])
        Dstar.append(float(np.mean(vals)))
    Dstar = np.array(Dstar)
    ci = [float(np.percentile(Dstar, 2.5)), float(np.percentile(Dstar, 97.5))] if len(Dstar) else [None, None]
    p_c1 = float((1 + (Dstar <= 0).sum()) / (len(Dstar) + 1)) if len(Dstar) else None
    from scipy.stats import binomtest

    n_pos = sum(1 for t in decided if D[t] > 0)
    n_nonzero = sum(1 for t in decided if D[t] != 0)
    sign_p = float(binomtest(n_pos, n_nonzero, 0.5, alternative="greater").pvalue) if n_nonzero else None
    if count1 >= 3 and count2 >= 4 and ci[0] is not None and ci[0] > 0:
        verdict, failed = "CONFIRMED", []
    elif count1 <= 1 or n_best_wins >= 4:
        verdict = "DISCONFIRMED"
        failed = [x for x, ok in (("count1<=1", count1 <= 1), ("best>PN on >=4 tasks", n_best_wins >= 4)) if ok]
    else:
        verdict = "PARTIAL"
        failed = [x for x, ok in (("count1>=3", count1 >= 3), ("count2>=4", count2 >= 4),
                                  ("CI_low>0", ci[0] is not None and ci[0] > 0)) if not ok]
    for t in per:
        per[t].pop("D_t_boot", None)
    return {"verdict": verdict, "failed_thresholds": failed, "count1": count1, "count2": count2,
            "n_tasks_best_beats_PN": n_best_wins, "D_bar": D_bar, "D_bar_ci95": ci, "p_C1_one_sided": p_c1,
            "sign_test_p_one_sided": sign_p, "n_positive_D": n_pos, "decided_tasks": decided, "per_task": per,
            "undecidable_tasks": [t for t in tasks if t not in D]}
