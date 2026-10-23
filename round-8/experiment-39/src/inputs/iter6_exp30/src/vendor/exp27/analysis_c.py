#!/usr/bin/env python3
"""S8 Claim-C analyses (committed by sha256 in commit0C BEFORE the first decisive knob sample).

Reads data/samples_raw.jsonl + data/labels.jsonl (merged by sample_id), predictions/dmd_temperatures.json,
inputs/exp19 (ND10 defaults, ban-unit PN H5), inputs/exp5 (iteration-1 base compositions of T1/T2), and the audit
files (style re-gate flags, novelty-audit relabelling) when present. Writes results/claim_c.json, cells.json,
knob_table.json, pn_vs_dmd.json, plain_vs_twin.json, landings.json, unit_ratio.json.

FROZEN DEFINITIONS
- N per cell = rows attempted (invalid rows, including multi-stage parse failures, stay in the denominator).
- pass = passed / N; correct = passed rows; labels of correct rows feed Hill ('other' is its own category).
- DEFAULT: D5 -> this TWIN (N 50): the modal correct label if its correct-only share >= 0.6, else NO DEFAULT;
  ND10 -> exp19's TWIN (N 50) modal label, confirmed by this TWIN's modal correct label (else NO DEFAULT, flagged).
- off-default share = #(correct and label != default) / N; correct-only off-default share = same / #correct.
- Hill = correct-only Hill-1 rarefied at depth 25 (1,000 subsamples; own depth if < 25 correct, flagged).
- Hull: full simplex per (task, class), settings in CLASS_SETTINGS order with TWIN first (src/hull_full.py);
  H5 = max Hill at pass cost <= 0.05; P15/P20 = min cost reaching Hill 1.5 / 2.0.
- Bootstrap: B replicates (2,000 on D5 for the Claim-C classes, 500 elsewhere); each replicate resamples the slots
  k WITHIN each template, jointly for every arm of the task (CRN pairing kept), and re-selects every class's best
  mixture (grid 0.05 + local refinement 0.01 within +-0.04, 200 rarefaction draws).
- CLAIM C: for t in D5, best_text(t) = max over {IFG, PSL, EAP, BINT} of H5 (classes present); PN wins t if
  round(H5_PN, 2) >= round(best_text, 2). SUPPORTED if PN wins >= 3 of 5 decisive tasks, else DISCONFIRMED
  (text-level samplers dominate as a practical knob). Reported beside it: per-task P(PN >= best_text) over replicates
  (best setting and best sampler chosen inside each replicate), UNRESOLVED if P in [0.2, 0.8], the replicate
  distribution of the win count, D_bar = mean_t (H5_PN - best_text) with its percentile CI, all four samplers' H5.
- Sensitivities (point estimates): IFG_hot-only; PN+; edge-restricted hull (max 2 non-zero weights); leftpad arms
  dropped (text samplers = IFG only); style-re-gate-flagged tasks excluded (threshold 60% of the remaining tasks,
  rounded up); correct-only labels after the novelty-audit relabelling.
- PN vs DMD at matched departure: per (task, alpha) off-default share and Hill of PN_a vs DMD_a; per-slot indicator
  'correct and off-default'; exact McNemar (binomial on discordant slots) PN_a vs DMD_a and each vs TWIN; pooled
  exact stratified test over D5 (sum of discordants); H5_PN vs H5_DMD; K_PN vs f_on; token departures.
- PN plain vs PN twin: PNPLAIN_a1 vs PN_a1 paired by slot (same direction, same stream): exact McNemar on correct
  off-default; pass difference; Hill. PLAIN vs TWIN likewise.
- MOVES: correct-only off-default share >= TWIN's + 0.10 and one-sided Fisher p < 0.05 -> landing set; T1/T2 landing
  sets beside the iteration-1 base compositions (exp5, Qwen3-8B-Base under the chat template), with the fraction of
  landing mass outside base support; base_repertoire_step1 = null (filled at write-up).
"""

from __future__ import annotations

import json
import math
import multiprocessing as mp
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import AUDIT_DIR, DATA_DIR, INPUTS, PRED_DIR, RESULTS_DIR, read_json, read_jsonl, write_json  # noqa: E402
from cfg5 import (BOOT_RAREFY, BOOT_SEED5, CLAIM_C_MIN_WINS, CLASS_SETTINGS, D5, DEPTH, MOVE_EXCESS,  # noqa: E402
                  MOVE_FISHER_P, N_BOOT_D5, N_BOOT_ND, N_RAREFY, ND10, TASKS15, TEXT_SAMPLERS, UNRESOLVED_BAND)
from hull_exp20 import rarefied_hill  # noqa: E402
from hull_full import hull_prices_full  # noqa: E402

CLAIM_CLASSES = ["PN", "IFG", "PSL", "EAP", "BINT", "DMD", "IFG_hot_only"]
OTHER_CLASSES = ["TEMP", "TOPK10", "NOVELTY", "SEMSEED"]
LEFTPAD_ARMS = {"BINT", "PSL", "EAP"}


# ------------------------------------------------------------------------------------------------ data
def load_rows(relabel: dict[str, str] | None = None) -> list[dict[str, Any]]:
    labs = {r["sample_id"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl")}
    out = []
    seen = set()
    for r in read_jsonl(DATA_DIR / "samples_raw.jsonl"):
        sid = r["sample_id"]
        if sid in seen:
            continue
        seen.add(sid)
        l = labs.get(sid)
        if l is None:
            continue
        lab = l.get("label") or "invalid"
        if relabel and l.get("passed") and lab == "other" and l.get("code_sha256") in relabel:
            lab = relabel[l["code_sha256"]]
        out.append({"task": r["task"], "arm": r["arm"], "w": r["template"], "k": int(r["slot"]), "label": lab,
                    "passed": bool(l.get("passed")), "valid": bool(l.get("valid", True)),
                    "engine_path": r.get("engine_path"), "code_sha256": l.get("code_sha256"),
                    "labeller_source": l.get("labeller_source"), "finish_reason": r.get("finish_reason"),
                    "intent_valid": r.get("intent_valid"), "intent_capped": r.get("intent_capped"),
                    "parse_ok": r.get("parse_ok"), "picked_name": r.get("picked_name"),
                    "enum_list": r.get("enum_list"), "unit_ratio": r.get("unit_ratio_banfree_over_ban"),
                    "realised_disp": r.get("realised_disp")})
    return out


def index(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[tuple[str, int], dict[str, Any]]]:
    idx: dict[tuple[str, str], dict[tuple[str, int], dict[str, Any]]] = defaultdict(dict)
    for r in rows:
        idx[(r["task"], r["arm"])][(r["w"], r["k"])] = r
    return idx


def exp19_defaults() -> dict[str, dict[str, Any]]:
    out = {}
    rows = [r for r in read_jsonl(INPUTS / "exp19" / "data" / "samples.jsonl") if r.get("arm") == "TWIN"]
    by = defaultdict(list)
    for r in rows:
        by[r["task"]].append(r)
    for t, rs in by.items():
        corr = [r["label"] for r in rs if r.get("passed")]
        c = Counter(corr)
        modal, n = c.most_common(1)[0] if c else (None, 0)
        out[t] = {"modal": modal, "share": n / max(len(corr), 1), "N": len(rs), "n_correct": len(corr)}
    return out


def defaults(idx) -> dict[str, dict[str, Any]]:
    e19 = exp19_defaults()
    out = {}
    for t in TASKS15:
        tw = list(idx.get((t, "TWIN"), {}).values())
        corr = [r["label"] for r in tw if r["passed"]]
        c = Counter(corr)
        modal, n = c.most_common(1)[0] if c else (None, 0)
        share = n / max(len(corr), 1)
        if t in D5:
            d = modal if (modal is not None and share >= 0.6) else None
            out[t] = {"default": d, "source": "this TWIN (N 50)", "modal": modal, "share": share, "N": len(tw)}
        else:
            e = e19.get(t, {})
            d = e.get("modal") if (e.get("modal") is not None and e.get("share", 0) >= 0.6) else None
            agree = (modal == d) if d is not None and modal is not None else None
            out[t] = {"default": d if agree is not False else None, "source": "exp19 TWIN (N 50)",
                      "exp19_modal": e.get("modal"), "exp19_share": e.get("share"), "this_modal": modal,
                      "this_share": share, "this_N": len(tw), "confirmed": agree,
                      "flag": None if agree else ("NO DEFAULT (disagreement)" if agree is False else "unconfirmed")}
    return out


# ------------------------------------------------------------------------------------------------ stats
def wilson(k: int, n: int, z: float = 1.96) -> list[float | None]:
    if n == 0:
        return [None, None]
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [max(0.0, c - h), min(1.0, c + h)]


def mcnemar_exact(x: list[int], y: list[int]) -> dict[str, Any]:
    from scipy.stats import binomtest

    b = sum(1 for a, c in zip(x, y) if a == 1 and c == 0)
    c = sum(1 for a, cc in zip(x, y) if a == 0 and cc == 1)
    p = float(binomtest(b, b + c, 0.5).pvalue) if b + c > 0 else 1.0
    return {"n_pairs": len(x), "x_only": b, "y_only": c, "p_exact": p}


def cell_stats(rs: list[dict[str, Any]], default: str | None) -> dict[str, Any]:
    n = len(rs)
    corr = [r for r in rs if r["passed"]]
    labs = [r["label"] for r in corr]
    off = [r for r in corr if default is not None and r["label"] != default]
    rh = rarefied_hill(labs, depth=DEPTH, n_sub=N_RAREFY, seed=0) if labs else {"hill": None, "depth": 0,
                                                                                 "flag_own_depth": True, "n": 0}
    out = {"N": n, "pass": len(corr) / n if n else None, "pass_wilson95": wilson(len(corr), n),
           "n_correct": len(corr), "correct_composition": dict(Counter(labs)),
           "attempted_composition": dict(Counter(r["label"] for r in rs)),
           "invalid_rate": sum(r["label"] == "invalid" for r in rs) / n if n else None,
           "other_rate": sum(r["label"] == "other" for r in rs) / n if n else None,
           "off_default_share": len(off) / n if n else None,
           "correct_only_off_default_share": len(off) / len(corr) if corr else None,
           "hill_rarefied": rh["hill"], "hill_depth": rh["depth"], "hill_own_depth_flag": rh["flag_own_depth"],
           "cap_hits": sum(r["finish_reason"] == "length" for r in rs),
           "engine_paths": dict(Counter(r["engine_path"] for r in rs))}
    if any(r.get("intent_valid") is not None for r in rs):
        iv = [r for r in rs if r.get("intent_valid") is not None]
        out["intent_valid_rate"] = sum(bool(r["intent_valid"]) for r in iv) / len(iv)
        out["intent_capped_rate"] = sum(bool(r.get("intent_capped")) for r in iv) / len(iv)
    if any(r.get("parse_ok") is not None for r in rs):
        out["parse_ok_rate"] = sum(r.get("parse_ok") is not False for r in rs) / n
    return out


MIN_N = {"D5": 30, "ND10": 15}   # amendment A1: incomplete cells (e.g. a dropped arm's stage-100 rows) stay out


def min_n(task: str) -> int:
    return MIN_N["D5"] if task in D5 else MIN_N["ND10"]


def settings_of(idx, task: str, cls: str, slots: list[tuple[str, int]] | None = None) -> list[dict[str, Any]] | None:
    arms = CLASS_SETTINGS[cls]
    out = []
    for a in arms:
        cell = idx.get((task, a))
        if not cell or len(cell) < min_n(task):
            if a == "TWIN":
                return None
            continue
        rs = [cell[s] for s in slots if s in cell] if slots is not None else list(cell.values())
        if not rs:
            continue
        out.append({"arm": a, "correct_labels": [r["label"] for r in rs if r["passed"]],
                    "pass": sum(r["passed"] for r in rs) / len(rs)})
    if len(out) < 2 or out[0]["arm"] != "TWIN":
        return None
    return out


def price(idx, task: str, cls: str, **kw) -> dict[str, Any] | None:
    st = settings_of(idx, task, cls)
    if st is None:
        return None
    res = hull_prices_full(st, **kw)
    res["arms"] = [s["arm"] for s in st]
    return res


# ------------------------------------------------------------------------------------------------ bootstrap
def _boot_worker(args: tuple) -> list[dict[str, float]]:
    rows, task, classes, seeds = args
    idx = index(rows)
    slots_by_w = defaultdict(set)
    for (t, a), cell in idx.items():
        if t == task:
            for (w, k) in cell:
                slots_by_w[w].add(k)
    out = []
    for sd in seeds:
        rng = np.random.default_rng(sd)
        # resample slots within each template, jointly for every arm; duplicates become distinct pseudo-slots
        mapping = []
        for w in sorted(slots_by_w):
            ks = sorted(slots_by_w[w])
            draw = rng.choice(ks, size=len(ks), replace=True)
            mapping += [(w, int(k)) for k in draw]
        rec: dict[str, float] = {}
        for cls in classes:
            arms = CLASS_SETTINGS[cls]
            st = []
            for a in arms:
                cell = idx.get((task, a))
                if not cell or len(cell) < min_n(task):
                    continue
                rs = [cell[s] for s in mapping if s in cell]
                if not rs:
                    continue
                st.append({"arm": a, "correct_labels": [r["label"] for r in rs if r["passed"]],
                           "pass": sum(r["passed"] for r in rs) / len(rs)})
            if len(st) < 2 or st[0]["arm"] != "TWIN":
                continue
            k = len(st)
            r = hull_prices_full(st, n_draws=BOOT_RAREFY, seed=int(sd % (2 ** 31)), step=0.05 if k <= 4 else 0.1,
                                 refine=True, refine_step=0.01)
            rec[cls] = r["H5"]
            rec[cls + "_P15"] = r["P15"]
            rec[cls + "_P20"] = r["P20"]
        out.append(rec)
    return out


def bootstrap(rows, task: str, classes: list[str], n_boot: int, n_workers: int) -> list[dict[str, float]]:
    """Amendment A3 (computation only): replicates are cached per task in results/boot_cache/<task>.json, keyed by the
    sha256 of the task's (sample_id, arm, slot, label, passed) rows, the class list and n_boot; identical inputs ->
    identical replicates (the seeds are fixed), so reuse changes no number."""
    import hashlib
    trows = [r for r in rows if r["task"] == task]
    key = hashlib.sha256(json.dumps([sorted((r["arm"], r["w"], r["k"], r["label"], r["passed"]) for r in trows),
                                     sorted(classes), n_boot]).encode()).hexdigest()
    cp = RESULTS_DIR / "boot_cache" / f"{task}.json"
    if cp.exists():
        c = read_json(cp)
        if c.get("key") == key:
            return c["replicates"]
    out = _bootstrap(trows, task, classes, n_boot, n_workers)
    write_json(cp, {"key": key, "replicates": out})
    return out


def _bootstrap(trows, task: str, classes: list[str], n_boot: int, n_workers: int) -> list[dict[str, float]]:
    seeds = [BOOT_SEED5 * 1000 + i + 7919 * TASKS15.index(task) for i in range(n_boot)]
    chunks = [seeds[i::n_workers] for i in range(n_workers)]
    with ProcessPoolExecutor(max_workers=n_workers, mp_context=mp.get_context("spawn")) as ex:
        parts = list(ex.map(_boot_worker, [(trows, task, classes, c) for c in chunks if c]))
    out = [x for p in parts for x in p]
    return out


def ci(vals: list[float]) -> list[float | None]:
    v = [x for x in vals if x is not None and np.isfinite(x)]
    if not v:
        return [None, None]
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]


# ------------------------------------------------------------------------------------------------ claim C
def claim_c_point(h5: dict[str, dict[str, float]], text_classes: list[str], pn_class: str = "PN",
                  tasks: tuple[str, ...] = D5, min_wins: int | None = None) -> dict[str, Any]:
    per = {}
    wins = 0
    n_eval = 0
    for t in tasks:
        hp = h5.get(t, {}).get(pn_class)
        tx = {c: h5.get(t, {}).get(c) for c in text_classes if h5.get(t, {}).get(c) is not None}
        if hp is None or not tx:
            per[t] = {"evaluable": False}
            continue
        n_eval += 1
        best_c = max(tx, key=lambda c: tx[c])
        best = tx[best_c]
        win = round(hp, 2) >= round(best, 2)
        wins += win
        per[t] = {"H5_PN": hp, "best_text": best, "best_text_class": best_c, "text_H5": tx, "PN_wins": bool(win),
                  "tie": round(hp, 2) == round(best, 2), "D_t": hp - best}
    thr = min_wins if min_wins is not None else (CLAIM_C_MIN_WINS if n_eval == len(D5) else
                                                 math.ceil(0.6 * n_eval))
    verdict = "SUPPORTED" if wins >= thr else "DISCONFIRMED"
    dts = [v["D_t"] for v in per.values() if v.get("evaluable", True) and "D_t" in v]
    return {"per_task": per, "wins": wins, "n_tasks_evaluable": n_eval, "threshold": thr, "verdict": verdict,
            "D_bar": float(np.mean(dts)) if dts else None}


def run(n_workers: int = 12, n_boot_d5: int = N_BOOT_D5, n_boot_nd: int = N_BOOT_ND) -> dict[str, Any]:
    rows = load_rows()
    idx = index(rows)
    dfl = defaults(idx)
    write_json(RESULTS_DIR / "defaults.json", dfl)
    # ---------------------------------------------------------------- 8.2 cells
    cells = {}
    for (t, a), cell in sorted(idx.items()):
        cells[f"{t}|{a}"] = cell_stats(list(cell.values()), dfl.get(t, {}).get("default"))
    write_json(RESULTS_DIR / "cells.json", cells)
    write_json(RESULTS_DIR / "incomplete_cells.json",
               {k: v["N"] for k, v in cells.items() if v["N"] < min_n(k.split("|")[0])})
    # ---------------------------------------------------------------- 8.3 point prices
    prices: dict[str, dict[str, Any]] = defaultdict(dict)
    for t in TASKS15:
        for cls in CLASS_SETTINGS:
            p = price(idx, t, cls, n_draws=1000, seed=0, keep_frontier=True)
            if p is not None:
                pe = price(idx, t, cls, n_draws=1000, seed=0, max_nonzero=2)
                p["H5_edge"] = pe["H5"] if pe else None
                p["full_ge_edge"] = (p["H5"] >= pe["H5"] - 1e-9) if pe else None
                prices[t][cls] = p
    write_json(RESULTS_DIR / "prices.json", prices)
    h5 = {t: {c: v["H5"] for c, v in d.items()} for t, d in prices.items()}
    h5_edge = {t: {c: v.get("H5_edge") for c, v in d.items()} for t, d in prices.items()}
    # ---------------------------------------------------------------- 8.3 bootstrap
    boots: dict[str, list[dict[str, float]]] = {}
    for t in TASKS15:
        classes = [c for c in CLAIM_CLASSES + OTHER_CLASSES if c in prices.get(t, {})]
        nb = n_boot_d5 if t in D5 else n_boot_nd
        if classes:
            boots[t] = bootstrap(rows, t, classes, nb, n_workers)
    write_json(RESULTS_DIR / "bootstrap.json", boots)
    # ---------------------------------------------------------------- 8.4 Claim C
    primary = claim_c_point(h5, list(TEXT_SAMPLERS))
    rep_wins, rep_dbar = [], []
    p_win = {}
    for t in D5:
        bt = boots.get(t, [])
        ok = []
        for b in bt:
            tx = [b[c] for c in TEXT_SAMPLERS if c in b and b[c] is not None and np.isfinite(b[c])]
            if "PN" in b and tx:
                ok.append(round(b["PN"], 2) >= round(max(tx), 2))
        p_win[t] = float(np.mean(ok)) if ok else None
    nrep = min((len(boots.get(t, [])) for t in D5), default=0)
    for i in range(nrep):
        w_, d_ = 0, []
        for t in D5:
            b = boots[t][i]
            tx = [b[c] for c in TEXT_SAMPLERS if c in b and b[c] is not None and np.isfinite(b[c])]
            if "PN" in b and tx:
                w_ += round(b["PN"], 2) >= round(max(tx), 2)
                d_.append(b["PN"] - max(tx))
        rep_wins.append(w_)
        if d_:
            rep_dbar.append(float(np.mean(d_)))
    sens = {
        "IFG_hot_only": claim_c_point(h5, ["IFG_hot_only", "PSL", "EAP", "BINT"]),
        "PN_plus": claim_c_point(h5, list(TEXT_SAMPLERS), pn_class="PN+"),
        "edge_restricted_hull": claim_c_point(h5_edge, list(TEXT_SAMPLERS)),
        "leftpad_arms_dropped": claim_c_point(h5, ["IFG"]),
    }
    flags_p = AUDIT_DIR / "style_regate.json"
    if flags_p.exists():
        fl = read_json(flags_p).get("flagged_tasks", [])
        keep = tuple(t for t in D5 if t not in fl)
        sens["style_regate_flagged_excluded"] = {**claim_c_point(h5, list(TEXT_SAMPLERS), tasks=keep),
                                                 "excluded": fl}
    nov_p = AUDIT_DIR / "novelty_relabel.json"
    if nov_p.exists():
        relabel = read_json(nov_p).get("relabel", {})
        idx2 = index(load_rows(relabel))
        h5r = {t: {c: (lambda p: p["H5"] if p else None)(price(idx2, t, c, n_draws=1000, seed=0))
                   for c in ["PN"] + list(TEXT_SAMPLERS)} for t in D5}
        h5r = {t: {c: v for c, v in d.items() if v is not None} for t, d in h5r.items()}
        sens["novelty_audit_relabelled"] = claim_c_point(h5r, list(TEXT_SAMPLERS))
    claim = {"primary": primary, "verdict": primary["verdict"],
             "p_PN_ge_best_text": p_win,
             "unresolved": {t: (p is not None and UNRESOLVED_BAND[0] <= p <= UNRESOLVED_BAND[1]) for t, p in p_win.items()},
             "replicate_win_count_distribution": dict(Counter(rep_wins)), "n_replicates": nrep,
             "D_bar": primary["D_bar"], "D_bar_ci95": ci(rep_dbar),
             "class_ci95": {t: {c: ci([b.get(c) for b in boots.get(t, [])]) for c in CLAIM_CLASSES + OTHER_CLASSES}
                            for t in TASKS15},
             "sensitivities": sens,
             "rule": ("PN wins t if round(H5_PN,2) >= round(max_{IFG,PSL,EAP,BINT} H5,2); SUPPORTED if wins >= 3 of 5 "
                      "(D5 = T03, T10, T2, T05, T1), else DISCONFIRMED")}
    nd = {t: claim_c_point(h5, list(TEXT_SAMPLERS), tasks=(t,), min_wins=1)["per_task"].get(t) for t in ND10}
    claim["nd10_descriptive"] = nd
    write_json(RESULTS_DIR / "claim_c.json", claim)
    # ---------------------------------------------------------------- 8.5 PN vs DMD
    dmd = read_json(PRED_DIR / "dmd_temperatures.json") if (PRED_DIR / "dmd_temperatures.json").exists() else {}
    pvd: dict[str, Any] = {"per_task": {}}
    pooled = defaultdict(lambda: [0, 0])
    for t in TASKS15:
        d = dfl.get(t, {}).get("default")
        tw = idx.get((t, "TWIN"), {})
        rec = {}
        for alpha in ("1", "2"):
            pa, da = idx.get((t, f"PN_a{alpha}"), {}), idx.get((t, f"DMD_a{alpha}"), {})
            common = sorted(set(pa) & set(da) & set(tw))
            if not common or d is None:
                continue
            ind = lambda cell: [int(cell[s]["passed"] and cell[s]["label"] != d) for s in common]
            x, y, z = ind(pa), ind(da), ind(tw)
            m = mcnemar_exact(x, y)
            if t in D5:
                pooled[alpha][0] += m["x_only"]
                pooled[alpha][1] += m["y_only"]
            cal = dmd.get(t, {}).get(f"{float(alpha)}", {})
            rec[f"alpha{alpha}"] = {
                "n_slots": len(common), "PN_off_default_share": float(np.mean(x)), "DMD_off_default_share": float(np.mean(y)),
                "TWIN_off_default_share": float(np.mean(z)),
                "PN_hill": cells.get(f"{t}|PN_a{alpha}", {}).get("hill_rarefied"),
                "DMD_hill": cells.get(f"{t}|DMD_a{alpha}", {}).get("hill_rarefied"),
                "PN_pass": cells.get(f"{t}|PN_a{alpha}", {}).get("pass"),
                "DMD_pass": cells.get(f"{t}|DMD_a{alpha}", {}).get("pass"),
                "mcnemar_PN_vs_DMD": m, "mcnemar_PN_vs_TWIN": mcnemar_exact(x, z), "mcnemar_DMD_vs_TWIN": mcnemar_exact(y, z),
                "K_PN": cal.get("K_PN"), "f_on_DMD": cal.get("f_on"), "T_dmd": cal.get("T_dmd"),
                "token_departure_PN": cal.get("token_departure_PN"), "token_departure_DMD": cal.get("token_departure_DMD")}
        rec["H5_PN"] = h5.get(t, {}).get("PN")
        rec["H5_DMD"] = h5.get(t, {}).get("DMD")
        pvd["per_task"][t] = rec
    from scipy.stats import binomtest
    pvd["pooled_D5_exact"] = {a: {"PN_only": b, "DMD_only": c, "p_exact": float(binomtest(b, b + c, 0.5).pvalue)
                                  if b + c else 1.0} for a, (b, c) in pooled.items()}
    write_json(RESULTS_DIR / "pn_vs_dmd.json", pvd)
    # ---------------------------------------------------------------- 8.6 PN plain vs PN twin
    pvt = {}
    for t in TASKS15:
        d = dfl.get(t, {}).get("default")
        if d is None:
            continue
        rec = {}
        for a_x, a_y in (("PNPLAIN_a1", "PN_a1"), ("PLAIN", "TWIN")):
            cx, cy = idx.get((t, a_x), {}), idx.get((t, a_y), {})
            common = sorted(set(cx) & set(cy))
            if not common:
                continue
            ix = [int(cx[s]["passed"] and cx[s]["label"] != d) for s in common]
            iy = [int(cy[s]["passed"] and cy[s]["label"] != d) for s in common]
            rec[f"{a_x}_vs_{a_y}"] = {"n_slots": len(common), "mcnemar": mcnemar_exact(ix, iy),
                                      "pass_x": float(np.mean([cx[s]["passed"] for s in common])),
                                      "pass_y": float(np.mean([cy[s]["passed"] for s in common])),
                                      "hill_x": cells.get(f"{t}|{a_x}", {}).get("hill_rarefied"),
                                      "hill_y": cells.get(f"{t}|{a_y}", {}).get("hill_rarefied")}
        pvt[t] = rec
    write_json(RESULTS_DIR / "plain_vs_twin.json", pvt)
    # ---------------------------------------------------------------- 8.7 unit ratio
    ur = {}
    e19c1 = {}
    try:
        c1 = read_json(INPUTS / "exp19" / "results" / "c1.json")
        for t, v in (c1.get("primary", {}).get("per_task", {}) or {}).items():
            e19c1[t] = v.get("H5_PN")
    except (FileNotFoundError, KeyError, AttributeError):
        pass
    for t in TASKS15:
        rs = [r for r in rows if r["task"] == t and r["arm"] in ("PN_a1", "PN_a2") and r.get("unit_ratio")]
        ratios = [float(np.mean(list(r["unit_ratio"].values()))) for r in rs]
        ur[t] = {"banfree_over_ban_mean": float(np.mean(ratios)) if ratios else None, "n": len(ratios),
                 "H5_PN_banfree_bf16": h5.get(t, {}).get("PN"), "H5_PN_ban_unit_exp19_fp8": e19c1.get(t),
                 "note": "exp19 rows are FP8 W8A8 (other engine); descriptive only"}
    write_json(RESULTS_DIR / "unit_ratio.json", ur)
    # ---------------------------------------------------------------- 8.8 landings
    from scipy.stats import fisher_exact
    base = defaultdict(Counter)
    for r in read_jsonl(INPUTS / "exp5" / "samples.jsonl"):
        if r.get("passed") and r.get("label"):
            base[{"t1": "T1", "t2": "T2"}.get(r["task"], r["task"])][r["label"]] += 1
    land: dict[str, Any] = {"moves": {}, "base_compositions_iter1": {t: dict(base[t]) for t in ("T1", "T2")}}
    for (t, a), cell in sorted(idx.items()):
        d = dfl.get(t, {}).get("default")
        if a == "TWIN" or d is None or (t, "TWIN") not in idx:
            continue
        tw = list(idx[(t, "TWIN")].values())
        rs = list(cell.values())
        cx = [r for r in rs if r["passed"]]
        ct = [r for r in tw if r["passed"]]
        if not cx or not ct:
            continue
        ox = sum(r["label"] != d for r in cx)
        ot = sum(r["label"] != d for r in ct)
        sx, st_ = ox / len(cx), ot / len(ct)
        p = float(fisher_exact([[ox, len(cx) - ox], [ot, len(ct) - ot]], alternative="greater")[1])
        moves = (sx >= st_ + MOVE_EXCESS) and p < MOVE_FISHER_P
        rec = {"correct_only_off_default": sx, "twin_correct_only_off_default": st_, "fisher_p_one_sided": p,
               "moves": bool(moves)}
        if moves:
            ls = Counter(r["label"] for r in cx if r["label"] != d)
            rec["landing_set"] = dict(ls)
            if t in ("T1", "T2"):
                sup = set(base[t])
                outside = sum(v for k, v in ls.items() if k not in sup)
                rec["base_support"] = sorted(sup)
                rec["landing_mass_outside_base_support"] = outside / max(sum(ls.values()), 1)
            rec["base_repertoire_step1"] = None
        land["moves"][f"{t}|{a}"] = rec
    eap = {}
    try:
        from parsers import map_modes
        import prompts_v4 as P4
        from cfg import BENCH
        for t in TASKS15:
            rs = [r for r in rows if r["task"] == t and r["arm"] == "EAP" and r.get("enum_list")]
            if not rs:
                continue
            al = {}
            if t not in ("T1", "T2"):
                sp = read_json(BENCH / P4.bench_dir(t) / "spec.json")
                al = {m: list(v) + [c["display_name"] for c in sp["catalogue"] if c["mode"] == m]
                      for m, v in sp.get("aliases", {}).items()}
            else:
                al = {"dijkstra": ["dijkstra"], "bellman_ford": ["bellman-ford", "bellman ford"], "spfa": ["spfa"],
                      "bfs": ["bfs", "breadth-first", "breadth first"], "dfs": ["dfs", "depth-first", "depth first"],
                      "a_star": ["a*", "a-star", "a star"], "bidirectional": ["bidirectional"],
                      "floyd_warshall": ["floyd", "warshall"]}
            comp = Counter()
            match = []
            for r in rs:
                for it in r["enum_list"]:
                    ms = map_modes(it["name"], it.get("idea", ""), al)
                    comp.update(ms or ["unmapped"])
                pk = next((it for it in r["enum_list"] if it["name"] == r.get("picked_name")), None)
                if pk is not None and r["passed"]:
                    ms = map_modes(pk["name"], pk.get("idea", ""), al)
                    match.append(r["label"] in ms if ms else None)
            mm = [m for m in match if m is not None]
            eap[t] = {"list_mode_composition": dict(comp), "n_lists": len(rs),
                      "mean_list_len": float(np.mean([len(r["enum_list"]) for r in rs])),
                      "picked_matches_label_rate": float(np.mean(mm)) if mm else None, "n_match_eval": len(mm)}
    except (ImportError, FileNotFoundError, KeyError) as e:
        eap["error"] = str(e)
    land["eap"] = eap
    write_json(RESULTS_DIR / "landings.json", land)
    # ---------------------------------------------------------------- 8.9 knob table
    kt = {}
    for t in TASKS15:
        kt[t] = {}
        for cls, p in prices.get(t, {}).items():
            bt = boots.get(t, [])
            kt[t][cls] = {"H5": p["H5"], "H5_ci95": ci([b.get(cls) for b in bt]), "P15": p["P15"],
                          "P15_ci95": ci([b.get(cls + "_P15") for b in bt]), "P20": p["P20"],
                          "P20_ci95": ci([b.get(cls + "_P20") for b in bt]), "arms": p["arms"],
                          "engine": "hf_bf16 (this artifact)", "n_boot": len(bt)}
    write_json(RESULTS_DIR / "knob_table.json", kt)
    return {"claim_c": claim, "n_rows": len(rows)}


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--boot-d5", type=int, default=N_BOOT_D5)
    ap.add_argument("--boot-nd", type=int, default=N_BOOT_ND)
    a = ap.parse_args()
    out = run(a.workers, a.boot_d5, a.boot_nd)
    print(json.dumps({"verdict": out["claim_c"]["verdict"], "wins": out["claim_c"]["primary"]["wins"],
                      "p_win": out["claim_c"]["p_PN_ge_best_text"], "n_rows": out["n_rows"]}, indent=1))
