#!/usr/bin/env python3
"""Committed analysis (amendment commit before it is first run on the full data).

E[e,t,alpha] = confirmed escapes / 40 (src/escape.py; each engine against its own twin); Wilson CIs. E_rule = alpha 2
for every engine (alpha 1 was not run for b, c, d; logged). Engines whose screen passers were not all topped up get
the screen-level indicator as well (flagged). Direction-paired exact McNemar for a-d, c-d, b-d, a-c, a-b (Holm over
{a-d, c-d, b-d} x {T10, T2}); 90% paired Tango score CIs and TOST at margin 0.1 beside every |x| <= 0.1 clause;
per-direction Spearman of first-10 off-default shares and Cohen's kappa of escape indicators. Literal verdict per
task (COMMIT #0 table), the T2 feasibility reading, the PN reading (CRN-paired McNemar by slot; Fisher vs exp19 FP8
rows), REPRO and B-sensitivity tables, landings, the relabel table, diagnostics summaries. Writes data/samples.jsonl
(every joined row of every engine, the input of src/rederive.py) and results/*.json.
"""

from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c6  # noqa: E402,F401
from c6 import (DATA, DEFAULTS, E19, E22, E27, PRED, REALISED, RESULTS, SEEDS_POP, append_jsonl, read_json,  # noqa: E402
                read_jsonl, utc_now, wilson, write_json)
from escape import escape_table, share  # noqa: E402
from rows6 import engine_rows, exp19_pn_rows  # noqa: E402

ENGS = ("a", "b", "c", "d")
TASKS = ("T10", "T2")
PAIRS = [("a", "d"), ("c", "d"), ("b", "d"), ("a", "c"), ("a", "b")]
PRIMARY = [("a", "d"), ("c", "d"), ("b", "d")]


def catalogue(task: str) -> set[str]:
    import cfg4  # noqa: F401
    from screen import catalogue as cat
    return set(cat(task))


# ------------------------------------------------------------------------------------------------ statistics
def mcnemar_exact(x: list[int], y: list[int]) -> dict[str, Any]:
    n10 = sum(1 for a, b in zip(x, y) if a and not b)
    n01 = sum(1 for a, b in zip(x, y) if b and not a)
    m = n10 + n01
    p2 = 1.0 if m == 0 else min(1.0, 2 * stats.binom.cdf(min(n10, n01), m, 0.5))
    p_gt = 1.0 if m == 0 else float(stats.binom.sf(n10 - 1, m, 0.5))   # H1: P(x) > P(y)
    return {"n10": n10, "n01": n01, "p_two_sided": float(p2), "p_one_sided_x_gt_y": p_gt}


def tango_ci(n10: int, n01: int, n: int, level: float = 0.90) -> tuple[float, float]:
    """Tango (1998) score CI for the paired difference p_x - p_y = (n10 - n01) / n."""
    if n == 0:
        return (float("nan"), float("nan"))
    z = stats.norm.ppf(0.5 + level / 2)
    grid = np.linspace(-1, 1, 8001)
    ok = []
    for d in grid:
        A = 2 * n
        B = -n10 - n01 + (2 * n - n10 + n01) * d
        C = -n01 * d * (1 - d)
        disc = max(B * B - 4 * A * C, 0.0)
        q21 = (math.sqrt(disc) - B) / (2 * A)
        var = n * (2 * q21 + d * (1 - d))
        if var <= 0:
            stat = 0.0 if (n10 - n01 - n * d) == 0 else float("inf")
        else:
            stat = (n10 - n01 - n * d) / math.sqrt(var)
        if abs(stat) <= z:
            ok.append(d)
    return (float(min(ok)), float(max(ok))) if ok else (float("nan"), float("nan"))


def holm(ps: dict[str, float]) -> dict[str, float]:
    items = sorted(ps.items(), key=lambda kv: kv[1])
    m = len(items)
    out, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


def kappa(x: list[int], y: list[int]) -> float:
    n = len(x)
    if n == 0:
        return float("nan")
    po = sum(1 for a, b in zip(x, y) if a == b) / n
    px, py = sum(x) / n, sum(y) / n
    pe = px * py + (1 - px) * (1 - py)
    return float("nan") if pe == 1 else (po - pe) / (1 - pe)


def spearman(x: list[float], y: list[float]) -> float | None:
    xx = np.array(x, float)
    yy = np.array(y, float)
    ok = ~(np.isnan(xx) | np.isnan(yy))
    if ok.sum() < 3 or np.std(xx[ok]) == 0 or np.std(yy[ok]) == 0:
        return None
    return float(stats.spearmanr(xx[ok], yy[ok]).statistic)


def perm_chi2(table: np.ndarray, n_perm: int = 10000, seed: int = 0) -> dict[str, Any]:
    """Monte-Carlo permutation test of independence for an r x c table (Fisher-Freeman-Halton surrogate)."""
    table = np.asarray(table, int)
    table = table[:, table.sum(0) > 0]
    if table.shape[1] < 2 or (table.sum(1) == 0).any():
        return {"chi2": None, "p_perm": None, "table": table.tolist()}
    rows = np.repeat(np.arange(table.shape[0]), table.sum(1))
    cols = np.concatenate([np.repeat(np.arange(table.shape[1]), table[i]) for i in range(table.shape[0])])

    def chi2(r, c):
        t = np.zeros(table.shape)
        np.add.at(t, (r, c), 1)
        e = t.sum(1, keepdims=True) * t.sum(0, keepdims=True) / t.sum()
        return float(((t - e) ** 2 / np.where(e > 0, e, 1)).sum())
    obs = chi2(rows, cols)
    rng = np.random.default_rng(seed)
    ge = sum(chi2(rows, rng.permutation(cols)) >= obs - 1e-9 for _ in range(n_perm))
    return {"chi2": obs, "p_perm": (ge + 1) / (n_perm + 1), "n_perm": n_perm, "table": table.tolist()}


# ------------------------------------------------------------------------------------------------ rows
def load_all() -> dict[str, dict[str, list[dict[str, Any]]]]:
    from rows6 import _labels
    labels = _labels()
    out: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for e in ENGS + ("aB",):
        for t in TASKS:
            rr = engine_rows(e, t, labels)
            if rr:
                out.setdefault(e, {})[t] = rr
    return out


def write_samples(R: dict[str, dict[str, list[dict[str, Any]]]]) -> int:
    p = DATA / "samples.jsonl"
    if p.exists():
        p.unlink()
    rows = [dict(r, engine=e) for e in R for t in R[e] for r in R[e][t]]
    append_jsonl(p, rows)
    return len(rows)


# ------------------------------------------------------------------------------------------------ escape
def escape_by_engine(R) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for e in ENGS:
        for t in TASKS:
            rr = R.get(e, {}).get(t)
            if not rr:
                continue
            alphas = tuple(sorted({float(r["alpha"]) for r in rr if r["family"] == "POP"
                                   and r.get("direction_seed") in SEEDS_POP} & {1.0, 2.0}))
            tab = escape_table(rr, SEEDS_POP, catalogue(t), DEFAULTS[t], alphas=alphas)
            pc = escape_table(rr, [9004], catalogue(t), DEFAULTS[t], alphas=(1.0,)) if t == "T2" else None
            per_alpha = {}
            for a in alphas:
                E = tab["E_t"][str(a)]
                cells = {s: tab["cells"].get(f"{s}|{a}") for s in SEEDS_POP}
                n_pass_untopped = sum(1 for c in cells.values() if c and c["screen_pass"] and c["pooled"]["n"] < 30)
                tw = tab["twin"]
                n_excess_only = sum(1 for c in cells.values() if c and not c["screen_pass"] and c["first10"]["n_valid"]
                                    and c["first10"]["share"] - tw["share"] >= 0.2 - 1e-12)
                per_alpha[str(a)] = {
                    **E, "n_excess_met_but_pass_clause_failed": n_excess_only,
                    "mean_share10": float(np.nanmean([c["first10"]["share"] for c in cells.values() if c])),
                    "mean_pass10": float(np.nanmean([c["first10"]["pass"] for c in cells.values() if c])),
                    "E_wilson": wilson(E["n_confirmed"], E["n_run"]) if E["n_run"] else None,
                    "E_screen_wilson": wilson(E["n_screen_pass"], E["n_run"]) if E["n_run"] else None,
                    "confirmation_complete": n_pass_untopped == 0, "n_screen_pass_not_confirmed_tested": n_pass_untopped,
                    "per_direction": {str(s): None if c is None else {
                        "share10": c["first10"]["share"], "pass10": c["first10"]["pass"], "screen": c["screen_pass"],
                        "confirmed": c["confirmed"], "share30": c["pooled"]["share"] if c["topped_up"] else None,
                        "n_invalid10": c["first10"]["n_invalid"], "binom_p": c["binom_p"]} for s, c in cells.items()}}
            out.setdefault(e, {})[t] = {"twin": tab["twin"], "alpha": per_alpha,
                                        "posctrl_9004_a1": None if pc is None else pc["cells"].get("9004|1.0")}
    return out


def pairs_table(ESC) -> dict[str, Any]:
    out: dict[str, Any] = {}
    raw_p = {}
    for t in TASKS:
        for (x, y) in PAIRS:
            if x not in ESC or y not in ESC or t not in ESC[x] or t not in ESC[y]:
                continue
            px = ESC[x][t]["alpha"]["2.0"]["per_direction"]
            py = ESC[y][t]["alpha"]["2.0"]["per_direction"]
            common = [s for s in px if px[s] is not None and py.get(s) is not None]
            complete = (ESC[x][t]["alpha"]["2.0"]["confirmation_complete"]
                        and ESC[y][t]["alpha"]["2.0"]["confirmation_complete"])
            for level in ("confirmed", "screen"):
                if level == "confirmed" and not complete:
                    out[f"{t}|{x}-{y}|{level}"] = {"status": "confirmation incomplete for an engine; see screen level"}
                    continue
                xs = [int(px[s][level]) for s in common]
                ys = [int(py[s][level]) for s in common]
                mc = mcnemar_exact(xs, ys)
                lo, hi = tango_ci(mc["n10"], mc["n01"], len(common))
                diff = (sum(xs) - sum(ys)) / len(common) if common else float("nan")
                rec = {"n_dirs": len(common), "E_x": sum(xs) / len(common) if common else None,
                       "E_y": sum(ys) / len(common) if common else None, "diff": diff, **mc,
                       "tango90": [lo, hi], "tost_margin_0.1_equivalent": bool(lo > -0.1 and hi < 0.1),
                       "kappa": kappa(xs, ys),
                       "spearman_share10": spearman([px[s]["share10"] for s in common],
                                                    [py[s]["share10"] for s in common])}
                out[f"{t}|{x}-{y}|{level}"] = rec
                if level == "confirmed" and (x, y) in PRIMARY:
                    raw_p[f"{t}|{x}-{y}"] = mc["p_two_sided"]
    hp = holm(raw_p) if raw_p else {}
    for k, v in hp.items():
        out[f"{k}|confirmed"]["p_holm"] = v
    out["holm_family"] = sorted(raw_p)
    return out


def slot_flips(R) -> dict[str, Any]:
    """CRN-paired per-slot comparison of POP alpha-2 rows (same direction, template, k and uniforms in both engines):
    off-default indicator per slot, exact McNemar on the discordant slots, and label identity of the paired slots."""
    out: dict[str, Any] = {}
    for t in TASKS:
        cat, dft = catalogue(t), DEFAULTS[t]
        ind = {}
        labs = {}
        for e in ENGS:
            rr = [r for r in R.get(e, {}).get(t, []) if r["family"] == "POP" and r.get("alpha") == 2.0
                  and r.get("direction_seed") in SEEDS_POP and r["label"] not in ("invalid", "disputed")]
            ind[e] = {(r["direction_seed"], r["template"], int(r["sample_id"])): int(r["label"] in cat and r["label"] != dft)
                      for r in rr}
            labs[e] = {(r["direction_seed"], r["template"], int(r["sample_id"])): r["label"] for r in rr}
        for (x, y) in PAIRS:
            if not ind.get(x) or not ind.get(y):
                continue
            # primary: the screen slots (k 0-1 of all 40 directions; run in every engine, no selection);
            # secondary: every common slot (adds confirmation slots, which exist only for screen-passing cells)
            for tag, keep in (("", lambda k: k[2] in (0, 1)), ("|all_common_slots", lambda k: True)):
                common = sorted(k for k in set(ind[x]) & set(ind[y]) if keep(k))
                mc = mcnemar_exact([ind[x][k] for k in common], [ind[y][k] for k in common])
                out[f"{t}|{x}-{y}{tag}"] = {
                    "n_slots": len(common), **mc,
                    "same_label_frac": float(np.mean([labs[x][k] == labs[y][k] for k in common])) if common else None,
                    "offdefault_x": float(np.mean([ind[x][k] for k in common])) if common else None,
                    "offdefault_y": float(np.mean([ind[y][k] for k in common])) if common else None}
    return out


def verdicts(ESC, PAIR, E4: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for t in TASKS:
        def E(e, level="E_t"):
            try:
                v = ESC[e][t]["alpha"]["2.0"]
            except KeyError:
                return None
            if level == "E_t" and not v["confirmation_complete"]:
                return None
            return v[level]
        Ea, Eb, Ec, Ed = (E(e) for e in ENGS)
        Ea_s, Eb_s, Ec_s, Ed_s = (E(e, "E_screen") for e in ENGS)
        e4 = E4[t]["2.0"]

        def rule(Ea, Eb, Ec, Ed, feas: bool = False):
            if None in (Ea, Ec, Ed):
                return "UNDECIDABLE (missing engine)", {}
            c1 = (Ec - Ed >= 0.2 - 1e-12) if not feas else (
                Ec - Ed >= (2 / 3) * (Ea - Ed) - 1e-12 and
                PAIR.get(f"{t}|c-d|confirmed", {}).get("p_one_sided_x_gt_y", 1) < 0.05)
            clauses = {"c-d": c1, "|a-c|<=0.1": abs(Ea - Ec) <= 0.1 + 1e-12,
                       "|b-d|<=0.1": None if Eb is None else abs(Eb - Ed) <= 0.1 + 1e-12}
            if clauses["c-d"] and clauses["|a-c|<=0.1"] and clauses["|b-d|<=0.1"]:
                return "ACTIVATION_ROUNDING", clauses
            if Eb is not None and Eb - Ed >= 0.2 - 1e-12:
                return "WEIGHT", clauses
            if Eb is not None and Ea - Ed >= 0.2 - 1e-12 and Eb - Ed < 0.1 and Ec - Ed < 0.1:
                return "INTERACTION", clauses
            if Ea - Ed < 0.1 and Ea < e4 - 0.15:
                return "NOT_REPRODUCED_LOW", clauses
            if Ea - Ed < 0.1 and Ed >= e4 - 0.15:
                return "NOT_REPRODUCED_HIGH", clauses
            if Eb is None:
                return "MIXED_OR_UNDECIDABLE (b missing)", clauses
            return "MIXED", clauses
        lit, cl = rule(Ea, Eb, Ec, Ed)
        scr, cls = rule(Ea_s, Eb_s, Ec_s, Ed_s)
        rec = {"E_alpha2": {"a": Ea, "b": Eb, "c": Ec, "d": Ed}, "E_screen_alpha2": {"a": Ea_s, "b": Eb_s, "c": Ec_s,
                                                                                    "d": Ed_s},
               "E_iter4_relabelled_a": e4, "literal_verdict": lit, "literal_clauses": cl,
               "screen_level_verdict": scr, "screen_level_clauses": cls}
        if min(E4[t]["1.0"], E4[t]["2.0"]) < 0.3:
            fv, fcl = rule(Ea, Eb, Ec, Ed, feas=True)
            rec["feasibility_reading"] = {"verdict": fv, "clauses": fcl,
                                          "rule": "E(c)-E(d) >= (2/3)(E(a)-E(d)) and one-sided exact McNemar c>d p<0.05"}
        out[t] = rec
    lits = [out[t]["literal_verdict"] for t in TASKS]
    out["claim"] = {"literal": lits[0] if len(set(lits)) == 1 else "TASKS_DISAGREE: " + " / ".join(lits),
                    "activation_rounding_claim_both_tasks": all(v == "ACTIVATION_ROUNDING" for v in lits)}
    return out


# ------------------------------------------------------------------------------------------------ PN
def pn_table(R) -> dict[str, Any]:
    out: dict[str, Any] = {}
    ref19 = {t: exp19_pn_rows(t) for t in TASKS}
    for t in TASKS:
        cat, dft = catalogue(t), DEFAULTS[t]
        slots: dict[str, dict[tuple, int]] = {}
        for e in ENGS:
            rr = [r for r in R.get(e, {}).get(t, []) if r["family"] == "PN"]
            for a in ("PN_a1", "PN_a2"):
                cell = [r for r in rr if r["arm"] == a]
                if not cell:
                    continue
                sh = share(cell, cat, dft)
                out.setdefault(t, {}).setdefault(a, {})[e] = {**sh, "wilson": wilson(sh["k_off"], sh["n_valid"]),
                                                             "sources": dict(Counter(r["source"] for r in cell))}
                slots[f"{e}|{a}"] = {(r["template"], int(r["sample_id"])): int(r["label"] in cat and r["label"] != dft)
                                     for r in cell if r["label"] not in ("invalid", "disputed")}
        for a in ("PN_a1", "PN_a2"):
            ref = [r for r in ref19[t] if r["arm"] == a]
            rs = share(ref, cat, dft)
            out.setdefault(t, {}).setdefault(a, {})["exp19_fp8"] = rs
            for (x, y) in PAIRS:
                kx, ky = slots.get(f"{x}|{a}"), slots.get(f"{y}|{a}")
                if not kx or not ky:
                    continue
                common = sorted(set(kx) & set(ky))
                mc = mcnemar_exact([kx[s] for s in common], [ky[s] for s in common])
                out[t][a][f"mcnemar_{x}-{y}"] = {"n": len(common), **mc}
            for e in ENGS:
                v = out[t][a].get(e)
                if v and v["n_valid"]:
                    tab = [[v["k_off"], v["n_valid"] - v["k_off"]], [rs["k_off"], rs["n_valid"] - rs["k_off"]]]
                    out[t][a][e]["fisher_vs_exp19_p"] = float(stats.fisher_exact(tab)[1])
    return out


# ------------------------------------------------------------------------------------------------ REPRO etc.
def repro_table(R) -> dict[str, Any]:
    rb = read_json(RESULTS / "repro_bytes.json")
    rel = {l["key"]: l for l in read_jsonl(DATA / "iter4_relabelled.jsonl")}
    out: dict[str, Any] = {"byte_identity_vs_exp22": {k: rb["vs_exp22"][k] for k in ("n_paired", "n_byte_identical",
                                                                                     "frac_identical")},
                           "pn_byte_identity_vs_exp19": {k: rb["pn_vs_exp19"][k] for k in ("n_paired",
                                                                                          "n_byte_identical",
                                                                                          "frac_identical")}}
    for t in TASKS:
        own = [r for r in R["a"][t] if r["source"] == "this_run" and r["stage"] == "REPRO"]
        agree = n = 0
        for r in own:
            l = rel.get(f"{t}|{r['template']}|{r['arm']}|{r['sample_id']}")
            if l:
                n += 1
                agree += l["label"] == r["label"]
        cat, dft = catalogue(t), DEFAULTS[t]
        pop_own = [r for r in own if r["family"] == "POP"]
        pop_ref = [{"label": rel[k]["label"], "passed": rel[k]["passed"]} for k in
                   (f"{t}|{r['template']}|{r['arm']}|{r['sample_id']}" for r in pop_own) if k in rel]
        so, sr = share(pop_own, cat, dft), share(pop_ref, cat, dft)
        fis = stats.fisher_exact([[so["k_off"], so["n_valid"] - so["k_off"]], [sr["k_off"], sr["n_valid"] - sr["k_off"]]])
        out[t] = {"per_slot_label_agreement": agree / n if n else None, "n_slots": n,
                  "pooled_offdefault_share_this_run": so["share"], "pooled_offdefault_share_exp22": sr["share"],
                  "abs_difference": abs(so["share"] - sr["share"]), "fisher_p": float(fis[1]),
                  "REPRO_FAIL": abs(so["share"] - sr["share"]) > 0.15}
    # realised displacement: this run's engine-a REPRO prefills vs exp22's logged ones
    mine = [r for r in read_jsonl(REALISED) if r.get("engine") == "a" and str(r.get("arm", "")).startswith("POP")]
    ref = {(r["task"], r["template"], r["arm"]): r for r in read_jsonl(E22 / "realised_disp.jsonl")}
    ratios = defaultdict(list)
    for r in mine:
        q = ref.get((r["task"], r["template"], r["arm"]))
        if not q:
            continue
        for l in range(24, 36):
            ratios["S_24_35"].append(r["disp_smean_norm"][str(l)] / q["disp_smean_norm"][str(l)]
                                     if str(l) in r["disp_smean_norm"] else
                                     r["disp_smean_norm"][l] / q["disp_smean_norm"][str(l)])
            ratios["R_24_35"].append(r["disp_R_norm"][str(l)] / q["disp_R_norm"][str(l)]
                                     if str(l) in r["disp_R_norm"] else r["disp_R_norm"][l] / q["disp_R_norm"][str(l)])
    out["realised_displacement_ratio_vs_exp22"] = {
        k: {"median": float(np.median(v)), "iqr": [float(np.percentile(v, 25)), float(np.percentile(v, 75))],
            "n": len(v)} for k, v in ratios.items()}
    return out


def bsens_table(R) -> dict[str, Any] | None:
    if "aB" not in R:
        return None
    from gen import raw_path
    ref = {(r["task"], r["template"], r["arm"], int(r["sample_id"])): r["token_ids"]
           for r in read_jsonl(raw_path("a")) if r["stage"] == "REPRO"}
    out = {}
    for t in TASKS:
        rows = [r for r in read_jsonl(raw_path("aB")) if r["task"] == t]
        same = [r["token_ids"] == ref.get((t, r["template"], r["arm"], int(r["sample_id"]))) for r in rows
                if (t, r["template"], r["arm"], int(r["sample_id"])) in ref]
        cat, dft = catalogue(t), DEFAULTS[t]
        jb = [r for r in R["aB"].get(t, []) if r["family"] == "POP"]
        ja = [r for r in R["a"][t] if r["family"] == "POP" and r["source"] == "this_run" and r["stage"] == "REPRO"]
        out[t] = {"n_paired": len(same), "n_byte_identical": int(sum(same)),
                  "B": rows[0]["B"] if rows else None,
                  "share_aB": share(jb, cat, dft)["share"], "share_a_B20": share(ja, cat, dft)["share"]}
    return out


def engine_check_exp27(R) -> dict[str, Any]:
    ref = defaultdict(Counter)
    for r in read_jsonl(E27 / "labels.jsonl"):
        if r["task"] in TASKS and r["arm"] == "TWIN":
            ref[r["task"]][r["label"]] += 1
    out = {}
    for t in TASKS:
        tw = Counter(r["label"] for r in R.get("d", {}).get(t, []) if r["arm"] == "TWIN" and int(r["sample_id"]) < 10)
        out[t] = {"this_run_d_twin": dict(tw), "exp27_bf16_twin": dict(ref[t]),
                  "modal_agree": (tw.most_common(1)[0][0] == ref[t].most_common(1)[0][0]) if tw and ref[t] else None}
    return out


def landings(R) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for t in TASKS:
        cat, dft = catalogue(t), DEFAULTS[t]
        comp = {}
        for e in ENGS:
            rr = [r for r in R.get(e, {}).get(t, []) if r["family"] == "POP" and r.get("alpha") == 2.0
                  and r["passed"] and r["label"] not in ("invalid", "disputed") and r["label"] != dft]
            comp[e] = dict(Counter(r["label"] for r in rr))
        labs = sorted({l for e in comp for l in comp[e]})
        sub = [e for e in ("a", "c", "d") if comp.get(e)]
        tab = np.array([[comp[e].get(l, 0) for l in labs] for e in sub]) if sub else np.zeros((0, 0))
        out[t] = {"composition_correct_offdefault": comp,
                  "top1": {e: (max(comp[e], key=comp[e].get) if comp[e] else None) for e in comp},
                  "in_catalogue": sorted(cat), "ffh_perm_a_c_d": perm_chi2(tab, 5000) if len(sub) >= 2 else None,
                  "engines_in_test": sub, "labels": labs}
    return out


def relabel_table(V, PN, ESC) -> list[dict[str, Any]]:
    def cls_from(Ea, Eb, Ec, Ed):
        if None in (Ea, Ec, Ed):
            return "UNTESTED HERE"
        if Ea - Ed < 0.1:
            return "MODEL"
        if Ec - Ed >= 0.2 and abs(Ea - Ec) <= 0.1 and (Eb is None or abs(Eb - Ed) <= 0.1):
            return "ACTIVATION ROUNDING"
        if Eb is not None and Eb - Ed >= 0.2:
            return "WEIGHT"
        return "W8A8-ONLY" if (Eb is not None and Eb - Ed < 0.1 and Ec - Ed < 0.1) else "MIXED"
    rows = []
    for t in TASKS:
        v = V[t]
        Es = v["E_alpha2"]
        if None in (Es["a"], Es["c"], Es["d"]):
            Es = v["E_screen_alpha2"]
        rows.append({"iteration4_result": f"C2a 40-direction escape fraction, {t} alpha 2 (iteration 4: "
                                          f"{v['E_iter4_relabelled_a']:.3f})", "class": cls_from(Es["a"], Es["b"],
                                                                                                  Es["c"], Es["d"]),
                     "deciding_cells": f"E(a,b,c,d) at alpha 2 on {t} = {Es}"})
        for a in ("PN_a1", "PN_a2"):
            p = PN.get(t, {}).get(a, {})
            sh = {e: (p[e]["share"] if e in p else None) for e in ENGS}
            rows.append({"iteration4_result": f"PN off-default share {t} {a} (exp19 FP8: "
                                              f"{p.get('exp19_fp8', {}).get('k_off')}/{p.get('exp19_fp8', {}).get('n_valid')})",
                         "class": cls_from(sh["a"], sh["b"], sh["c"], sh["d"]), "deciding_cells": f"PN shares {sh}"})
    pc = {e: (ESC.get(e, {}).get("T2", {}).get("posctrl_9004_a1") or {}).get("first10", {}).get("share")
          for e in ENGS}
    rows.append({"iteration4_result": "exp17 frozen-screen direction 9004 moves T2 (alpha 1)",
                 "class": "MODEL" if (pc.get("d") or 0) >= 0.2 else ("UNTESTED HERE" if pc.get("d") is None else
                                                                    "ENGINE-DEPENDENT"),
                 "deciding_cells": f"POSCTRL 9004 first-10 off-default share per engine {pc}"})
    sf = read_json(RESULTS / "slot_flips.json") if (RESULTS / "slot_flips.json").exists() else {}
    for t in TASKS:
        f = sf.get(f"{t}|a-d")
        if f:
            rows.append({"iteration4_result": f"per-slot off-default rate under the alpha-2 pushes, {t} (CRN-paired, "
                                              f"FP8 a vs bf16 d)",
                         "class": ("MODEL + FP8 BOOST" if f["p_two_sided"] < 0.05 and f["n10"] > f["n01"] else "MODEL"),
                         "deciding_cells": f"a {f['offdefault_x']:.3f} vs d {f['offdefault_y']:.3f}; discordant "
                                           f"{f['n10']}:{f['n01']}, exact McNemar p = {f['p_two_sided']:.2g}"})
    pt2 = PN.get("T10", {}).get("PN_a2", {})
    if "d" in pt2:
        rows.append({"iteration4_result": "iteration-5 bf16 PN null on T10 (1/50 at its ban-free unit, block-12 dose "
                                          "0.66 x this unit)",
                     "class": "DOSE (not reproduced at the absolute unit)" if pt2["d"]["share"] >= 0.2 else "MODEL",
                     "deciding_cells": f"PN_a2 T10 at the absolute unit: d {pt2['d']['k_off']}/{pt2['d']['n_valid']}, "
                                       f"a {pt2.get('a', {}).get('k_off')}/{pt2.get('a', {}).get('n_valid')}"})
    e2 = ESC.get("d", {}).get("T2", {}).get("alpha", {}).get("2.0")
    if e2:
        rows.append({"iteration4_result": "iteration-5: T2 loses 'movable' in bf16",
                     "class": "NOT REPRODUCED at the absolute unit" if e2["n_confirmed"] > 0 else "REPRODUCED",
                     "deciding_cells": f"E(d) T2 alpha 2 = {e2['n_confirmed']}/{e2['n_run']} confirmed escapes"})
    for name in ("site claim OR 5.72", "same-seed agreement 17.25/20", "C2a pi-rho (plan-subspace predictor)",
                 "C2c targeted runner-up pushes", "decomposition u_perp / u_P"):
        rows.append({"iteration4_result": name, "class": "UNTESTED HERE", "deciding_cells": "not re-run in this artifact"})
    return rows


def validity_table(R) -> dict[str, Any]:
    """Breakage vs change: invalid / disputed / other rates, pass rate, token length and KV-overflow count per
    engine x task x family (this run's rows and the reused iteration-4 rows alike)."""
    out: dict[str, Any] = {}
    for e in R:
        for t in R[e]:
            by = defaultdict(list)
            for r in R[e][t]:
                by[r["family"]].append(r)
            for fam, rr in by.items():
                n = len(rr)
                out[f"{e}|{t}|{fam}"] = {
                    "n": n, "invalid": sum(r["label"] == "invalid" for r in rr) / n,
                    "disputed": sum(r["label"] == "disputed" for r in rr) / n,
                    "other": sum(r["label"] == "other" for r in rr) / n, "pass": sum(r["passed"] for r in rr) / n,
                    "median_n_tokens": float(np.median([r["n_tokens"] for r in rr if r.get("n_tokens") is not None]))
                    if any(r.get("n_tokens") is not None for r in rr) else None,
                    "n_kv_overflow": sum(1 for r in rr if r.get("overflow_at_step") is not None),
                    "finish": dict(Counter(r["finish_reason"] for r in rr))}
    return out


def diagnostics_summary() -> dict[str, Any]:
    """FIDELITY verdict (pre-registered ratio), KL table, induced-perturbation ratios to BF16 (median over blocks
    13-35 per position group), rounding sanity (x_push == x_twin at blocks 0-12)."""
    D: dict[str, Any] = {}
    for ws in ("B", "Q"):
        p = RESULTS / f"diagnostics_{ws}.json"
        if p.exists():
            D[ws] = read_json(p)
    out: dict[str, Any] = {"available": sorted(D)}
    fid = {}
    for ws in D:
        for e, v in (D[ws].get("kl_fidelity", {}).get("FIDELITY", {}) or {}).items():
            fid.setdefault(e, {}).update(v)
    out["FIDELITY"] = fid
    if "a" in fid and "d" in fid:
        verdict = {}
        for t in TASKS:
            if t in fid["a"] and t in fid["d"]:
                ra, rd = fid["a"][t]["median_abs_diff"], fid["d"][t]["median_abs_diff"]
                verdict[t] = {"median_abs_diff_a": ra, "median_abs_diff_d": rd,
                              "ratio": ra / rd if rd else None,
                              "EMULATION_INFIDELITY": bool(rd and ra > 0.25 * rd)}
        out["FIDELITY_rule"] = verdict
    kl = {}
    for ws in D:
        for e, v in (D[ws].get("kl_fidelity", {}).get("KL", {}) or {}).items():
            kl.setdefault(e, {}).update(v)
    out["KL_vs_bf16"] = kl
    ind = {}
    for ws in D:
        for k, v in D[ws].items():
            if k.startswith("induced_") and isinstance(v, dict):
                ind[k.split("_")[1]] = v
    out["induced_engines"] = sorted(ind)
    if "d" in ind:
        ratios = {}
        for e in ind:
            for t in TASKS:
                if t not in ind[e] or t not in ind["d"]:
                    continue
                for g in ("S", "R", "G"):
                    xe = ind[e][t]["induced_ban_units"][g]
                    xd = ind["d"][t]["induced_ban_units"][g]
                    rr = [a / b for a, b in zip(xe[13:], xd[13:]) if a is not None and b]
                    ratios[f"{e}|{t}|{g}"] = float(np.median(rr)) if rr else None
        out["induced_ratio_to_d_median_blocks_13_35"] = ratios
    out["x_push_equals_x_twin_blocks_0_12"] = {f"{e}|{t}": ind[e][t]["x_push_equals_x_twin_blocks_0_12"]
                                               for e in ind for t in TASKS if t in ind[e]}
    rnd = {}
    for e in ind:
        for t in TASKS:
            if t in ind[e]:
                for s_, v in ind[e][t]["rounding"].items():
                    rr = [x for x in v["rel_rms"] if x is not None]
                    am = [x for x in v["amp"][13:] if x is not None]
                    sc = [x for x in v["scale_changed"][13:] if x is not None]
                    rnd[f"{e}|{t}|{s_}"] = {"median_rel_rms": float(np.median(rr)) if rr else None,
                                            "median_amp_blocks_13_35": float(np.median(am)) if am else None,
                                            "median_frac_scale_changed_13_35": float(np.median(sc)) if sc else None}
    out["rounding_summary"] = rnd
    return out


def main() -> None:
    R = load_all()
    n = write_samples(R)
    E4 = read_json(RESULTS / "cpu_gates.json")["C4"]["E_iter4_relabelled"]
    ESC = escape_by_engine(R)
    PAIR = pairs_table(ESC)
    V = verdicts(ESC, PAIR, E4)
    PN = pn_table(R)
    out = {"utc": utc_now(), "n_rows": n,
           "rows_per_engine_task": {e: {t: len(R[e][t]) for t in R[e]} for e in R},
           "sources_engine_a": {t: dict(Counter(r["source"] for r in R["a"][t])) for t in R.get("a", {})}}
    write_json(RESULTS / "escape_by_engine.json", ESC)
    write_json(RESULTS / "mcnemar.json", PAIR)
    write_json(RESULTS / "verdict.json", V)
    write_json(RESULTS / "pn.json", PN)
    write_json(RESULTS / "repro.json", repro_table(R))
    write_json(RESULTS / "bsens.json", bsens_table(R))
    write_json(RESULTS / "engine_check_exp27.json", engine_check_exp27(R))
    write_json(RESULTS / "landings.json", landings(R))
    write_json(RESULTS / "slot_flips.json", slot_flips(R))
    write_json(RESULTS / "relabel_table.json", relabel_table(V, PN, ESC))
    write_json(RESULTS / "diagnostics_summary.json", diagnostics_summary())
    write_json(RESULTS / "validity.json", validity_table(R))
    write_json(RESULTS / "analysis_run.json", out)
    print(out)
    for t in TASKS:
        print(t, V[t]["literal_verdict"], V[t]["E_alpha2"], V[t]["E_screen_alpha2"])


if __name__ == "__main__":
    main()
