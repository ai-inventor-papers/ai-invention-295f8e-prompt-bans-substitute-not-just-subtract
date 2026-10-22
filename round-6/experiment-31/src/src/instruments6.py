#!/usr/bin/env python3
"""L instruments and the per-unit commit (plan S6, frozen; identical across iteration-6 artifacts), the engine check
(S5.2) and the enrolment order. Every quantity is computed from final labels (labeller + judge adjudication) only.

- twin rows (300): HF T1.0 k 0..9 (50, CRN) + vLLM T1.0 k 10..39 (150) + vLLM T1.3 k 10..29 (100).
- ENGINE CHECK: label-composition JS(HF-50, vLLM T1.0 k 10..19) vs a template-resampling null (2,000 resamples, each
  template's 20 rows split at random into two groups of 10); outside the null (> q95) -> ENGINE_NONEQUIV: D_u and p0
  from the HF rows only, q_tail reported with and without the vLLM rows.
- D_u = modal correct label over the twin rows if its share of the correct programs >= 0.6, else NO DEFAULT.
- q_tail = add-one-smoothed composition over the non-default modes plus 'other' of the correct non-default twin
  programs; t_u = most frequent correct non-default catalogue mode; TAIL_EMPTY = zero correct non-default programs.
- q_lik from results/qlik/<u>.json: score_raw(a) = mean lp48 over programs x W1..W5, score_norm = per-token mean;
  top-1 = argmax score_raw over the non-default modes with a verified program; q_lik = softmax(score_norm) over the
  defined non-default modes scaled to their share n_defined / n_nondefault, every undefined mode gets the uniform share
  1 / n_nondefault (uniform fill); q_lik_raw likewise with score_raw.
- fork margin m = mean over W of [mean lp48(D_u programs) - mean lp48(r_u programs)].
- q_base = add-one-smoothed correct-only composition over the non-default modes plus 'other' of 200 chat + 100 plain
  base rows (< 20 correct -> valid-attempt composition, flag BASE_ATTEMPTS); r_u = most frequent non-default
  catalogue mode (ties: more correct plain programs, then catalogue order); THIN_SUPPORT if r_u rests on < 3 valid
  programs. DISCORDANT = r_u != q_lik top-1. PREDICTED LANDING = r_u.
- M: beta (correct-only base share off D_u), replacement (base modal correct != D_u), runtime merit
  log2(median stress runtime of the D_u reference / that of the fastest non-default reference), twin modal share,
  K, m.
Usage: python src/instruments6.py commit I1,I2 | enrol I1,...  [--final]
"""

from __future__ import annotations

import math
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

from cfg6 import (DEFAULT_SHARE, EXCLUDE, PRED_DIR, RESULTS_DIR, TEMPLATE_IDS, UNITS_DIR, read_json, setup_logging,  # noqa
                  sha256_file, utc_now, write_json)
from commit6 import commit  # noqa: E402
from labels_view6 import cell_stats, load_final  # noqa: E402
from units_spec6 import UNITS, catalogue  # noqa: E402
from unitlib6 import load_tests  # noqa: E402


def js_div(a: Counter, b: Counter) -> float:
    keys = set(a) | set(b)
    na, nb = sum(a.values()), sum(b.values())
    if na == 0 or nb == 0:
        return float("nan")
    p = np.array([a.get(k, 0) / na for k in keys])
    q = np.array([b.get(k, 0) / nb for k in keys])
    m = (p + q) / 2

    def kl(x, y):
        msk = x > 0
        return float(np.sum(x[msk] * np.log2(x[msk] / y[msk])))
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def lab_of(r: dict) -> str:
    """Composition label of a row: the final label for passing programs, 'FAIL' otherwise (invalid kept apart)."""
    f = r.get("final")
    if f in ("invalid", "disputed"):
        return f
    return f if r.get("passed") else "FAIL"


def engine_check(u: str, rows: list[dict], n_null: int = 2000) -> dict[str, Any]:
    hf = [r for r in rows if r["arm"] == "TWINHF" and r["slot"] in range(10)]
    vl = [r for r in rows if r["arm"] == "TWIN" and r["src"] == "vllm" and r["slot"] in range(10, 20)]
    obs = js_div(Counter(lab_of(r) for r in hf), Counter(lab_of(r) for r in vl))
    rng = np.random.default_rng(0)
    by_w = {w: [lab_of(r) for r in hf + vl if r["template"] == w] for w in TEMPLATE_IDS}
    null = []
    for _ in range(n_null):
        A, Bc = Counter(), Counter()
        for w, labs in by_w.items():
            idx = rng.permutation(len(labs))
            h = len(labs) // 2
            A.update(labs[i] for i in idx[:h])
            Bc.update(labs[i] for i in idx[h:])
        null.append(js_div(A, Bc))
    q95 = float(np.nanquantile(null, 0.95))
    return {"unit": u, "js_observed": obs, "null_q95": q95, "null_mean": float(np.nanmean(null)),
            "inside_null": bool(obs <= q95 + 1e-12), "n_hf": len(hf), "n_vllm": len(vl),
            "comp_hf": dict(Counter(lab_of(r) for r in hf)), "comp_vllm": dict(Counter(lab_of(r) for r in vl))}


def addone(counts: Counter, support: list[str]) -> dict[str, float]:
    tot = sum(counts.get(k, 0) for k in support) + len(support)
    return {k: (counts.get(k, 0) + 1) / tot for k in support}


def softmax_fill(scores: dict[str, float | None], modes: list[str]) -> dict[str, float] | None:
    defined = {m: s for m, s in scores.items() if s is not None and m in modes}
    if not defined:
        return None
    n = len(modes)
    mx = max(defined.values())
    ex = {m: math.exp(s - mx) for m, s in defined.items()}
    z = sum(ex.values())
    out = {}
    for m in modes:
        out[m] = (ex[m] / z) * (len(defined) / n) if m in defined else 1.0 / n
    return out


def runtime_merit(u: str, D: str, nondef: list[str]) -> float | None:
    cases = [c for c in load_tests(u) if c["kind"] == "stress"]
    if not cases or D not in cases[0]["ref_times"]:
        return None
    med = {m: statistics.median(c["ref_times"][m] for c in cases) for m in cases[0]["ref_times"]}
    others = [med[m] for m in nondef if m in med]
    if not others or med[D] <= 0 or min(others) <= 0:
        return None
    return math.log2(med[D] / min(others))


def compute_unit(u: str) -> dict[str, Any]:
    cat = catalogue(u)
    rows = [r for r in load_final([u]) if r.get("labeller_source") not in ("assoc_alias_lexicon", "intent_text")]
    pend = [r for r in rows if r.get("final") is None]
    if pend:
        raise RuntimeError(f"{u}: {len(pend)} rows pending adjudication")
    twin_hf = [r for r in rows if r["arm"] == "TWINHF" and r["slot"] in range(10)]
    twin_v10 = [r for r in rows if r["arm"] == "TWIN" and r["src"] == "vllm"]
    twin_v13 = [r for r in rows if r["arm"] == "TWIN13" and r["src"] == "vllm"]
    twin = twin_hf + twin_v10 + twin_v13
    ec = engine_check(u, rows)
    flags: list[str] = []
    if not ec["inside_null"]:
        flags.append("ENGINE_NONEQUIV")
    dsrc = twin_hf if not ec["inside_null"] else twin
    corr = Counter(r["final"] for r in dsrc if r.get("passed") and r["final"] not in EXCLUDE)
    ncorr = sum(corr.values())
    D, Dshare = (corr.most_common(1)[0] if corr else (None, 0))
    Dshare = Dshare / ncorr if ncorr else 0.0
    default = D if (D is not None and Dshare >= DEFAULT_SHARE and D in cat) else None
    if default is None:
        flags.append("NO_DEFAULT")
    hf_corr = Counter(r["final"] for r in twin_hf if r.get("passed") and r["final"] not in EXCLUDE)
    hf_default = hf_corr.most_common(1)[0][0] if hf_corr else None
    nondef = [m for m in cat if m != default]
    support_tail = nondef + ["other"]
    # ---- q_tail / t_u
    tail_all = Counter(r["final"] for r in twin if r.get("passed") and r["final"] not in EXCLUDE
                       and r["final"] != default)
    tail_hf = Counter(r["final"] for r in twin_hf if r.get("passed") and r["final"] not in EXCLUDE
                      and r["final"] != default)
    q_tail = addone(tail_all, support_tail)
    q_tail_hf = addone(tail_hf, support_tail)
    tail_cat = Counter({k: v for k, v in tail_all.items() if k in nondef})
    t_u = None
    if tail_cat:
        best = max(tail_cat.values())
        t_u = next(m for m in nondef if tail_cat.get(m, 0) == best)
    tail_empty = sum(tail_all.values()) == 0
    # ---- q_base / r_u
    chat = [r for r in rows if r["arm"] == "BASE"]
    plain = [r for r in rows if r["arm"] == "PLAIN"]
    base = chat + plain
    bc = Counter(r["final"] for r in base if r.get("passed") and r["final"] not in EXCLUDE)
    n_bc = sum(bc.values())
    attempts_mode = n_bc < 20
    if attempts_mode:
        flags.append("BASE_ATTEMPTS")
        src_counts = Counter(r["final"] for r in base if r.get("valid") and r["final"] not in EXCLUDE)
    else:
        src_counts = bc
    q_base = addone(Counter({k: v for k, v in src_counts.items() if k != default}), support_tail)
    plain_corr = Counter(r["final"] for r in plain if r.get("passed") and r["final"] not in EXCLUDE)
    cand = [(src_counts.get(m, 0), plain_corr.get(m, 0), -i, m) for i, m in enumerate(nondef)]
    cand.sort(reverse=True)
    r_u = cand[0][3] if cand and cand[0][0] > 0 else None
    support = {}
    for m in cat + ["other"]:
        support[m] = {"chat_valid": sum(1 for r in chat if r.get("valid") and r["final"] == m),
                      "chat_correct": sum(1 for r in chat if r.get("passed") and r["final"] == m),
                      "plain_valid": sum(1 for r in plain if r.get("valid") and r["final"] == m),
                      "plain_correct": sum(1 for r in plain if r.get("passed") and r["final"] == m)}
        support[m]["total_valid"] = support[m]["chat_valid"] + support[m]["plain_valid"]
        support[m]["total_correct"] = support[m]["chat_correct"] + support[m]["plain_correct"]
    if r_u is not None and support[r_u]["total_valid"] < 3:
        flags.append("THIN_SUPPORT")
    if r_u is None:
        flags.append("NO_BASE_RUNNER_UP")
    # pilot runner-up (base chat k 0..5) for the enrolment priority rule
    pil = [r for r in chat if r["slot"] in range(6)]
    pc = Counter(r["final"] for r in pil if r.get("passed") and r["final"] in nondef)
    if not pc:
        pc = Counter(r["final"] for r in pil if r.get("valid") and r["final"] in nondef)
    pilot_ru = max(nondef, key=lambda m: (pc.get(m, 0), -nondef.index(m))) if pc else None
    # ---- q_lik + fork margin
    ql = read_json(RESULTS_DIR / "qlik" / f"{u}.json")
    by = ql["by_mode"]
    sraw = {m: (by[m]["score_raw"] if m in by and by[m]["n_programs"] >= 3 else None) for m in nondef}
    snorm = {m: (by[m]["score_norm"] if m in by and by[m]["n_programs"] >= 3 else None) for m in nondef}
    q_lik = softmax_fill(snorm, nondef)
    q_lik_raw = softmax_fill(sraw, nondef)
    defined_raw = {m: s for m, s in sraw.items() if s is not None}
    q_lik_top1 = max(defined_raw, key=lambda m: defined_raw[m]) if defined_raw else None
    if q_lik is None:
        flags.append("QLIK_UNDEFINED")
    fork_margin = None
    if default in by and r_u in by and by[default]["n_programs"] >= 1 and by[r_u]["n_programs"] >= 1:
        fork_margin = float(np.mean([by[default]["lp48_by_template"][w] - by[r_u]["lp48_by_template"][w]
                                     for w in TEMPLATE_IDS]))
    discordant = (r_u is not None and q_lik_top1 is not None and r_u != q_lik_top1)
    # ---- M values
    beta = sum(v for k, v in bc.items() if k != default) / n_bc if n_bc else None
    base_modal = bc.most_common(1)[0][0] if bc else None
    tw_corr = Counter(r["final"] for r in twin if r.get("passed") and r["final"] not in EXCLUDE)
    twin_modal_share = tw_corr.get(default, 0) / sum(tw_corr.values()) if tw_corr and default else None
    M = {"beta": beta, "replacement": (base_modal is not None and default is not None and base_modal != default),
         "runtime_merit": runtime_merit(u, default, nondef) if default else None,
         "twin_modal_share": twin_modal_share, "K": len(cat), "m": fork_margin}
    hf_st = cell_stats(twin_hf, default, cat)
    fv = read_json(UNITS_DIR / u / "forced_verified.json")
    rec = {"unit": u, "unit_kind": "new", "utc_computed": utc_now(), "catalogue": cat, "K": len(cat),
           "default": default, "default_share_correct": Dshare, "default_source": "hf_only" if not ec["inside_null"]
           else "twin_300", "hf50_default": hf_default, "n_twin_rows": len(twin),
           "twin_counts": {"hf": len(twin_hf), "vllm_t10": len(twin_v10), "vllm_t13": len(twin_v13)},
           "twin_correct_comp": dict(tw_corr), "q_tail": q_tail, "q_tail_hf_only": q_tail_hf, "t_u": t_u,
           "tail_empty": tail_empty, "tail_counts": dict(tail_all), "q_base": q_base, "r_u": r_u,
           "base_counts_used": dict(src_counts), "base_correct_n": n_bc, "base_support": support,
           "pilot_runner_up": pilot_ru, "q_lik": q_lik, "q_lik_raw": q_lik_raw, "q_lik_top1": q_lik_top1,
           "q_lik_scores_raw": sraw, "q_lik_scores_norm": snorm,
           "q_lik_n_programs": {m: (by[m]["n_programs"] if m in by else 0) for m in cat},
           "fork_margin": fork_margin, "discordant": discordant, "predicted_landing": r_u, "M": M,
           "hf_twin": {"n_attempts": hf_st["n_attempts"], "pass_rate": hf_st["pass_rate"], "k_off": hf_st["k_off"],
                       "off_share": hf_st["off_share"], "n_rows": hf_st["n_rows"]},
           "p0": (hf_st["k_off"] + 0.5) / (hf_st["n_attempts"] + 1), "engine_check": ec, "flags": flags,
           "forced_flags": fv.get("flags"), "inputs": {
               "forced_verified_sha256": sha256_file(UNITS_DIR / u / "forced_verified.json"),
               "qlik_sha256": sha256_file(RESULTS_DIR / "qlik" / f"{u}.json"),
               "gate_sha256": sha256_file(UNITS_DIR / u / ("gate_revision.json" if (UNITS_DIR / u /
                                                                                    "gate_revision.json").exists()
                                                          else "gate.json"))}}
    return rec


def commit_unit(u: str) -> dict[str, Any]:
    p = PRED_DIR / "units" / f"{u}.json"
    if p.exists():
        logger.warning(f"{u}: already committed; not overwritten")
        return read_json(p)
    rec = compute_unit(u)
    write_json(p, rec)
    e = commit([p], f"unit_commit:{u}")
    logger.info(f"{u} committed {e[0]['sha256'][:12]}: D={rec['default']} r_u={rec['r_u']} q_lik_top1="
                f"{rec['q_lik_top1']} t_u={rec['t_u']} tail_empty={rec['tail_empty']} discordant={rec['discordant']}"
                f" flags={rec['flags']}")
    return rec


def enrol(units: list[str], final: bool) -> dict[str, Any]:
    pr, rest = [], []
    for u in units:
        rec = read_json(PRED_DIR / "units" / f"{u}.json")
        if rec["default"] is None:
            continue
        no_tail_hf = rec["hf_twin"]["k_off"] == 0 and not any(
            v for k, v in rec["tail_counts"].items() if k == "other")
        pri = (rec["pilot_runner_up"] is not None and rec["q_lik_top1"] is not None and
               rec["pilot_runner_up"] != rec["q_lik_top1"]) or rec["hf_twin"]["k_off"] == 0
        (pr if pri else rest).append(u)
    order = [u for u in units if u in pr] + [u for u in units if u in rest]
    p = PRED_DIR / "enrolment.json"
    prev = read_json(p) if p.exists() else None
    if prev is not None:
        order = prev["order"] + [u for u in order if u not in prev["order"]]
        p = PRED_DIR / f"enrolment_addendum_{len(order)}.json"
    out = {"utc": utc_now(), "order": order, "priority": [u for u in order if u in pr], "final": final,
           "rule": "priority units (pilot runner-up != q_lik top-1, or HF twin-50 without a correct non-default "
                   "program) first, then the rest, each group in list order"}
    from cfg6 import write_json as wj
    wj(p, out)
    commit([p], "enrolment")
    if p.name != "enrolment.json":
        wj(PRED_DIR / "enrolment.json", out)   # the runner reads the current order; the addendum is the record
    logger.info(f"enrolment: {out}")
    return out


if __name__ == "__main__":
    setup_logging("instruments6")
    cmd, us = sys.argv[1], sys.argv[2].split(",")
    if cmd == "commit":
        for uu in us:
            commit_unit(uu)
    elif cmd == "enrol":
        enrol(us, "--final" in sys.argv)
    elif cmd == "show":
        import json
        for uu in us:
            print(json.dumps(compute_unit(uu), indent=1)[:3000])
