#!/usr/bin/env python3
"""Per-unit forecasts and the hash-chained unit commit (plan C5 iv), computed ONLY from predictor-side samples:
the 300 twin samples (HF CRN k 0-9 + vLLM k 10-39 at T 1.0, vLLM T 1.3 k 0-19), the base repertoire (200 chat with
token ids identical to the twin W1-W5 prompts + 100 plain completions; iteration-5 units pool their iteration-5 base
rows when the engine check passes), the forced-program likelihoods (results/qlik.json) and the association answers.

Frozen operational choices (spec_digest; written before any nudge sample, see predictions/analysis_choices.json):
- q_lik floor: algorithms of S without any verified forced program get no score; q_lik over S is the add-one
  smoothed softmax q(a) = (p(a) * M + 1) / (M + |S|), with p = softmax(score_tok) over the scored algorithms of S
  and M = number of scored programs among S (the plan's 'floor of the add-one smoothed softmax'); qlik_top1 is the
  argmax over SCORED algorithms only (None when none of S is scored).
- engine check (HF vs vLLM twin, iteration-5 vs new base rows): JS divergence of label compositions vs the 95th
  percentile of a template-stratified bootstrap null (1,000 reps, numpy default_rng(20261021)).
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

from cfg5 import (PRED_DIR, PROMPTS, RESULTS_DIR, ROOT, UNITS_DIR, VENDOR, append_jsonl, read_json, read_jsonl,  # noqa: E402
                  setup_logging, sha256_file, sha256_text, utc_now, write_json)
from labels6 import all_final, default_from, twin_baseline  # noqa: E402
from labels_view import frozen_catalogue  # noqa: E402

LIB_ONE_LINE = {  # frozen before any nudge: catalogue modes that are a library call or a one-line identity
    "II1": ["iterator_consumption"], "II2": ["counting_formula"], "II3": ["library_count"],
    "II4": ["index_of_max"], "II5": ["library_permutations"], "II6": ["replace_pairs"],
    "II7": ["concat_sort", "heapq_merge"], "II8": ["full_sort", "nsmallest"],
    "B1": ["arithmetic_sum"], "B2": ["set_sum_identity"], "B3": [], "B4": ["library_isqrt", "float_sqrt"],
    "B5": ["itertools_combinations"], "B6": ["sort_compare"], "B7": [],
}
EXCLUDE = ("invalid", "disputed")


def js(p: Counter, q: Counter, keys: list[str]) -> float:
    a = np.array([p.get(k, 0) for k in keys], float)
    b = np.array([q.get(k, 0) for k in keys], float)
    if a.sum() == 0 or b.sum() == 0:
        return float("nan")
    a, b = a / a.sum(), b / b.sum()
    m = (a + b) / 2

    def kl(x, y):
        nz = x > 0
        return float((x[nz] * np.log2(x[nz] / y[nz])).sum())
    return 0.5 * kl(a, m) + 0.5 * kl(b, m)


def engine_check(rows_a: list[dict], rows_b: list[dict], reps: int = 1000) -> dict[str, Any]:
    """JS(label composition A, B) vs the template-stratified bootstrap null of the pooled rows."""
    keys = sorted({r["label"] for r in rows_a + rows_b})
    ca, cb = Counter(r["label"] for r in rows_a), Counter(r["label"] for r in rows_b)
    obs = js(ca, cb, keys)
    rng = np.random.default_rng(20261021)
    pooled: dict[str, list[str]] = {}
    for r in rows_a + rows_b:
        pooled.setdefault(r.get("template", "-"), []).append(r["label"])
    na = Counter(r.get("template", "-") for r in rows_a)
    nb = Counter(r.get("template", "-") for r in rows_b)
    null = []
    for _ in range(reps):
        x, y = Counter(), Counter()
        for w, labs in pooled.items():
            if na.get(w):
                x.update(rng.choice(labs, size=na[w], replace=True).tolist())
            if nb.get(w):
                y.update(rng.choice(labs, size=nb[w], replace=True).tolist())
        null.append(js(x, y, keys))
    null = [v for v in null if not math.isnan(v)]
    q95 = float(np.quantile(null, 0.95)) if null else float("nan")
    ok = (math.isnan(obs) or obs <= q95 + 1e-12)
    return {"js": obs, "null_q95": q95, "pass": bool(ok), "n_a": len(rows_a), "n_b": len(rows_b),
            "comp_a": dict(ca), "comp_b": dict(cb)}


def smoothed(counts: dict[str, int], support: list[str]) -> dict[str, float]:
    tot = sum(counts.get(k, 0) for k in support) + len(support)
    return {k: (counts.get(k, 0) + 1) / tot for k in support}


def iter5_base_rows(u: str) -> list[dict]:
    p = VENDOR / "exp26" / "samples_B_nocode.jsonl"
    if not u.startswith("B") or not p.exists():
        return []
    out = []
    for r in read_jsonl(p):
        if r["unit"] == u and r["model_tag"] == "base" and r["arm"] in ("BASE", "PLAIN"):
            lab = r.get("label") or "disputed"
            out.append({"unit": u, "arm": r["arm"], "template": r["template"], "slot": r["slot"], "label": lab,
                        "passed": bool(r.get("passed")), "valid": bool(r.get("valid")), "engine": "hf_iter5",
                        "model_tag": "base", "key": r["key"]})
    return out


def runtime_merit(u: str, d: str, S: list[str]) -> float | None:
    cases = [json.loads(l) for l in (UNITS_DIR / u / "tests.jsonl").read_text().splitlines() if l.strip()]
    st = [c for c in cases if c.get("kind") == "stress" and c.get("ref_times")]
    if not st:
        return None
    tot = Counter()
    for c in st:
        for m, t in c["ref_times"].items():
            tot[m] += float(t)
    if d not in tot:
        return None
    alts = [tot[a] for a in S if a in tot and tot[a] > 0]
    if not alts:
        return None
    return float(math.log2(tot[d] / min(alts)))


def qlik_block(u: str, S: list[str], d: str, r_u: str | None) -> dict[str, Any]:
    allq = read_json(RESULTS_DIR / "qlik.json") if (RESULTS_DIR / "qlik.json").exists() else {}
    q = allq.get(u)
    out: dict[str, Any] = {"available": q is not None}
    if q is None:
        return out

    def scores(kind: str, key: str) -> dict[str, float]:
        return {m: v[kind][key] for m, v in q["by_mode"].items() if v.get(kind) and v[kind].get(key) is not None}

    out["score_tok"] = scores("scrubbed", "score_tok")
    out["score_raw"] = scores("scrubbed", "score_raw")
    out["unscrubbed_score_tok"] = scores("unscrubbed", "score_tok")
    out["unscrubbed_score_raw"] = scores("unscrubbed", "score_raw")
    out["n_programs"] = q["n_programs"]
    out["noise_floor"] = q.get("noise_floor")

    def soft(sc: dict[str, float]) -> tuple[dict[str, float], str | None, float | None]:
        defined = [a for a in S if a in sc]
        M = sum(min(q["n_programs"].get(a, 0), 10) for a in defined)
        if not defined:
            return {a: 1.0 / len(S) for a in S}, None, None
        x = np.array([sc[a] for a in defined])
        p = np.exp(x - x.max())
        p = p / p.sum()
        pd = dict(zip(defined, p.tolist()))
        res = {a: (pd.get(a, 0.0) * M + 1) / (M + len(S)) for a in S}
        top = max(defined, key=lambda a: (sc[a], -S.index(a)))
        srt = sorted((sc[a] for a in defined), reverse=True)
        gap = srt[0] - srt[1] if len(srt) > 1 else None
        return res, top, gap

    out["q_lik"], out["qlik_top1"], out["top2_gap_tok"] = soft(out["score_tok"])
    out["q_lik_raw"], out["qlik_raw_top1"], out["top2_gap_raw"] = soft(out["score_raw"])
    out["q_lik_unscrubbed"], out["qlik_unscrubbed_top1"], _ = soft(out["unscrubbed_score_tok"])
    if d in out["score_raw"] and r_u in out["score_raw"]:
        out["fork_margin"] = out["score_raw"][d] - out["score_raw"][r_u]
        out["fork_margin_tok"] = out["score_tok"][d] - out["score_tok"][r_u]
    else:
        out["fork_margin"] = None
        out["fork_margin_tok"] = None
    return out


def iter5_twin_rows(u: str) -> list[dict]:
    """Iteration-5 HF CRN twin slots k 0-9 (exp26, bf16 HF on an RTX 4090) of a B unit: the first 50 of its 300."""
    p = VENDOR / "exp26" / "samples_B_nocode.jsonl"
    if not u.startswith("B") or not p.exists():
        return []
    out = []
    for r in read_jsonl(p):
        if r["unit"] == u and r["model_tag"] == "instruct" and r["arm"] == "TWIN" and r["slot"] < 10:
            out.append({"unit": u, "arm": "TWIN", "template": r["template"], "slot": r["slot"],
                        "label": r.get("label") or "disputed", "passed": bool(r.get("passed")),
                        "valid": bool(r.get("valid")), "engine": "hf", "iter5": True, "model_tag": "instruct",
                        "family": "TWIN", "key": "iter5:" + r["key"]})
    return out


def unit_quantities(u: str) -> dict[str, Any]:
    rows = all_final({u})
    if u.startswith("B") and not any(r["arm"] == "TWIN" and r.get("engine") == "hf" for r in rows):
        rows = rows + iter5_twin_rows(u)
    cat = list(frozen_catalogue(u))
    dd = default_from(rows, u)
    d = dd["default"]
    out: dict[str, Any] = {"unit": u, "utc": utc_now(), "catalogue": cat, "K": len(cat), "default": d,
                           "default_share": dd["default_share"], "default_T10_only": dd["default_T10_only"],
                           "twin_default_detail": dd, "flags": []}
    if dd["default_T10_only"] and d != "NO_DEFAULT" and dd["default_T10_only"] != d:
        out["flags"].append("default_differs_T10_only")
    # ---------------- engine check: HF twin k 0-9 vs vLLM twin k 10-19 (same T 1.0)
    hf = [r for r in rows if r["arm"] == "TWIN" and r.get("engine") == "hf" and r["slot"] < 10]
    vl = [r for r in rows if r["arm"] == "TWIN" and r.get("engine") == "vllm" and 10 <= r["slot"] < 20]
    out["engine_check_twin"] = engine_check(hf, vl) if hf and vl else None
    engine_ok = out["engine_check_twin"]["pass"] if out["engine_check_twin"] else True
    if not engine_ok:
        out["flags"].append("ENGINE_SPLIT")
    tw10 = [r for r in rows if r["arm"] == "TWIN" and r["model_tag"] == "instruct"]
    out["twin"] = {"n_T10": len(tw10), "n_T13": sum(1 for r in rows if r["arm"] == "T13"),
                   "n_T10_hf": len(hf), "counts_correct_T10": dict(Counter(r["label"] for r in tw10 if r["passed"])),
                   "counts_correct_T13": dict(Counter(r["label"] for r in rows if r["arm"] == "T13" and r["passed"])),
                   "other_correct": sum(1 for r in rows if r["arm"] in ("TWIN", "T13") and r["passed"] and
                                        r["label"] == "other"),
                   "invalid": sum(1 for r in rows if r["arm"] in ("TWIN", "T13") and r["label"] == "invalid"),
                   "engine_check": out["engine_check_twin"]}
    if d == "NO_DEFAULT":
        out["enrol"] = False
        out["flags"].append("NO_DEFAULT")
        tb = twin_baseline(rows, u, cat[0], engine_ok)
        out["twin"]["pass_T10"] = tb["pass"]
        return out
    S = [a for a in cat if a != d]
    tb = twin_baseline(rows, u, d, engine_ok)
    out["twin"].update(pass_T10=tb["pass"], off_T10=tb["off"], twin_baseline=tb)
    if tb["pass"] is not None and tb["pass"] < 0.7:
        out["flags"].append(f"twin_pass_below_0.7({tb['pass']:.2f})")
    # ---------------- q_tail
    tw300 = [r for r in rows if r["arm"] in ("TWIN", "T13") and r["model_tag"] == "instruct"]
    tail = Counter(r["label"] for r in tw300 if r["passed"] and r["label"] != d and r["label"] not in EXCLUDE)
    tail_S = {a: tail.get(a, 0) for a in S}
    out["tail_counts"] = {**tail_S, "other": tail.get("other", 0)}
    out["q_tail_full"] = smoothed(out["tail_counts"], S + ["other"])
    out["q_tail"] = {a: out["q_tail_full"][a] / sum(out["q_tail_full"][b] for b in S) for a in S}
    out["tail_empty"] = sum(tail_S.values()) == 0
    t10c = Counter(r["label"] for r in tw300 if r["arm"] == "TWIN" and r["passed"])
    out["t_u"] = None if out["tail_empty"] else max(S, key=lambda a: (tail_S[a], t10c.get(a, 0), -S.index(a)))
    # ---------------- q_base
    base = [r for r in rows if r["model_tag"] == "base" and r["arm"] in ("BASE", "BASEX", "PLAIN")]
    out["base_engine_check"] = None
    i5 = iter5_base_rows(u)
    if i5:
        old_chat = [r for r in i5 if r["arm"] == "BASE" and r["label"] not in EXCLUDE]
        new_chat = [r for r in base if r["arm"] == "BASEX" and r["label"] not in EXCLUDE]
        ec = engine_check(old_chat, new_chat) if old_chat and new_chat else None
        out["base_engine_check"] = ec
        if ec is None or ec["pass"]:
            base = base + i5
        else:
            out["flags"].append("BASE_ENGINE_FAIL_fresh_only")
    chat = [r for r in base if r["arm"] in ("BASE", "BASEX")]
    plain = [r for r in base if r["arm"] == "PLAIN"]
    corr = Counter(r["label"] for r in base if r["passed"] and r["label"] not in EXCLUDE)
    valid = Counter(r["label"] for r in base if r["label"] not in EXCLUDE)
    n_corr = sum(corr.values())
    src = corr
    if n_corr < 20:
        out["flags"].append(f"LOW_CORRECT(n={n_corr})")
        src = valid
    counts = {a: src.get(a, 0) for a in cat}
    counts["other"] = src.get("other", 0)
    plain_c = Counter(r["label"] for r in plain if (r["passed"] or n_corr < 20) and r["label"] not in EXCLUDE)
    out["base"] = {"n_chat": len(chat), "n_plain": len(plain), "counts_correct": dict(corr),
                   "counts_valid": dict(valid), "n_correct_total": n_corr, "low_correct": n_corr < 20,
                   "engine_check": out["base_engine_check"], "counts_used": counts,
                   "pass_chat": (sum(r["passed"] for r in chat) / len(chat)) if chat else None,
                   "pass_plain": (sum(r["passed"] for r in plain) / len(plain)) if plain else None}
    qb = smoothed({a: counts[a] for a in S + ["other"]}, S + ["other"])
    out["q_base_full"] = qb
    out["q_base"] = {a: qb[a] / sum(qb[b] for b in S) for a in S}
    out["r_u"] = max(S, key=lambda a: (counts[a], plain_c.get(a, 0), -S.index(a)))
    out["r_u_has_support"] = counts[out["r_u"]] > 0
    out["support"] = {a: {"valid": valid.get(a, 0), "correct": corr.get(a, 0),
                          "valid_chat": sum(1 for r in chat if r["label"] == a),
                          "correct_chat": sum(1 for r in chat if r["label"] == a and r["passed"]),
                          "valid_plain": sum(1 for r in plain if r["label"] == a),
                          "correct_plain": sum(1 for r in plain if r["label"] == a and r["passed"])} for a in cat}
    tot_c = sum(corr.get(a, 0) for a in cat) + corr.get("other", 0)
    out["beta"] = 1 - corr.get(d, 0) / tot_c if tot_c else None
    # ---------------- q_lik and the fork margin
    ql = qlik_block(u, S, d, out["r_u"])
    out["q_lik_block"] = ql
    out["qlik_top1"] = ql.get("qlik_top1")
    out["q_lik"] = ql.get("q_lik")
    out["q_lik_raw"] = ql.get("q_lik_raw")
    out["discordant"] = out["qlik_top1"] is not None and out["r_u"] != out["qlik_top1"]
    if out["qlik_top1"] is None:
        out["flags"].append("QLIK_UNDEFINED_ON_S")
    # forced compliance (descriptive): share of forced attempts implementing the requested algorithm
    fc = {}
    for a in cat:
        fr = [r for r in rows if r["arm"] == f"FORCED_{a}"]
        fc[a] = {"n": len(fr), "verified": sum(1 for r in fr if r["passed"] and r["label"] == a),
                 "implemented": sum(1 for r in fr if r["label"] == a)}
    out["forced_compliance"] = fc
    # ---------------- association answers (20 for the default), mapped to S
    ar = [r for r in rows if r["arm"] == f"ASSOC6_{d}"]
    from units_spec import map_answer
    amap = Counter(map_answer(u, r.get("assoc_answer") or "", modes=S) for r in ar)
    out["association_counts"] = dict(amap)
    out["assoc"] = smoothed({a: amap.get(a, 0) for a in S}, S)
    # ---------------- M candidates
    rc = 1 if (out["r_u"] in LIB_ONE_LINE.get(u, []) or out["tail_counts"].get(out["r_u"], 0) > 0) else 0
    out["m_candidates"] = {"beta": out["beta"], "replacement_class": rc,
                           "runtime_merit": runtime_merit(u, d, S), "twin_modal_share": dd["default_share"],
                           "K": len(cat), "fork_margin": ql.get("fork_margin")}
    # ---------------- enrolment priority
    pilot = [r for r in chat if r["arm"] == "BASE" and r["slot"] < 6 and r.get("engine") != "hf_iter5"]
    pc = Counter(r["label"] for r in pilot if r["passed"] and r["label"] in S)
    pilot_ru = max(S, key=lambda a: (pc.get(a, 0), -S.index(a))) if pc else None
    tw50 = [r for r in rows if r["arm"] == "TWIN" and r.get("engine") == "hf" and r["slot"] < 10]
    out["enrolment"] = {"pilot_runner_up": pilot_ru,
                        "twin50_no_correct_S": not any(r["passed"] and r["label"] in S for r in tw50),
                        "priority": (pilot_ru != out["qlik_top1"]) or not any(r["passed"] and r["label"] in S
                                                                              for r in tw50)}
    out["predicted_landing"] = out["r_u"]
    out["enrol"] = True
    return out


def grep_audit_unit(u: str) -> dict[str, Any]:
    from units_spec import grep_banned
    rows = [r for r in read_jsonl(PROMPTS) if r["unit"] == u and r["kind"] in ("twin", "plain", "novelty")]
    bad = [{"pid": r["pid"], "hits": grep_banned(u, r["user_text"])} for r in rows]
    bad = [b for b in bad if b["hits"]]
    return {"n_prompts": len(rows), "ban_prompts": 0, "catalogue_hits": bad}


def commit_unit(u: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    from commit5 import commit, verify_unit_commit
    p = PRED_DIR / "units" / f"{u}.json"
    if p.exists():
        logger.warning(f"{u}: already committed; never edited")
        return read_json(p)
    q = unit_quantities(u)
    q["grep_audit"] = grep_audit_unit(u)
    if q["grep_audit"]["catalogue_hits"]:
        raise RuntimeError(f"{u}: grep audit failed {q['grep_audit']}")
    q["inputs_sha256"] = {"labels.jsonl": sha256_file(ROOT / "data" / "labels.jsonl"),
                          "qlik.json": sha256_file(RESULTS_DIR / "qlik.json") if (RESULTS_DIR / "qlik.json").exists()
                          else None, "tests.jsonl": sha256_file(UNITS_DIR / u / "tests.jsonl"),
                          "catalogue_frozen.json": sha256_file(UNITS_DIR / u / "catalogue_frozen.json")
                          if (UNITS_DIR / u / "catalogue_frozen.json").exists() else None}
    if extra:
        q.update(extra)
    write_json(p, q)
    e = commit([p], f"unit_commit:{u}")
    v = verify_unit_commit(u)
    logger.info(f"committed {u}: default {q['default']}, r_u {q.get('r_u')}, qlik_top1 {q.get('qlik_top1')}, "
                f"t_u {q.get('t_u')}, tail_empty {q.get('tail_empty')}, discordant {q.get('discordant')}, "
                f"flags {q['flags']}; verify {v}")
    enr = PRED_DIR / "enrolment" / f"{u}.json"      # one new file per unit (committed files are never edited)
    write_json(enr, {"unit": u, "utc": utc_now(), "enrol": q.get("enrol"),
                     "priority": (q.get("enrolment") or {}).get("priority"),
                     "pilot_runner_up": (q.get("enrolment") or {}).get("pilot_runner_up"),
                     "qlik_top1": q.get("qlik_top1"), "commit_sha256": e[0]["sha256"],
                     "queue_rule": "priority units first in list order, then the others; SCREEN units never "
                                   "pre-empt new units"})
    commit([enr], f"enrolment:{u}")
    return q


if __name__ == "__main__":
    setup_logging("quantities6")
    for uu in sys.argv[1].split(","):
        commit_unit(uu)
