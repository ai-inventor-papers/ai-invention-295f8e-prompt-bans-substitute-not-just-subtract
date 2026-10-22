#!/usr/bin/env python3
"""Per-unit quantities and the per-unit COMMIT (plan section 8), run before the unit's first push sample.

DEFAULT  modal correct-only twin label (TWIN k 0-9, N = 50 attempts) if its share >= 0.6 and it is a catalogue mode,
         else NO_DEFAULT.
BASE     correct-only base composition (BASE, W1-W5 x k 0-39, N = 200; deviation base_n_200); beta_u = share of
         correct base programs whose label != default (disputed excluded); r_u = most frequent correct non-default
         CATALOGUE label (ties flagged). Hill-1 rarefied at depth 25 (1,000 subsamples), Good's coverage, bootstrap
         P(beta >= 0.05), P(beta >= 0.2) (2,000 resamples); fewer than 20 correct -> attempt composition, flagged.
RIVALS   R_margin, R_merit (runtime and length), R_modal, R_novel (+ correct-only), K_u (sign: higher = more movable).
FORECASTS over survivors + 'other' for A2: BASE / ASSOC / PROX, each p = 0.93 p_raw + 0.05 uniform(survivors) +
         0.02 'other' (identical smoothing for every predictor; +0.5 pseudo-counts for BASE and ASSOC).
COMMIT   grep audit (0 violations required) -> predictions/units/<u>.json -> hash chain (tag unit_commit:<u>).
"""

from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

from cfg5 import (DEFAULT_SHARE, LABELS, PRED_DIR, PROHIBITION_CUES, PROMPTS, RESULTS_DIR, SRC, UNITS_DIR,  # noqa: E402
                  read_json, read_jsonl, setup_logging, sha256_file, utc_now, write_json)
from commit5 import commit, verify_unit_commit  # noqa: E402
from labels_view import EXCLUDE, adjudicate_pending, final_rows, frozen_catalogue, summarise  # noqa: E402
from units_spec import UNITS, map_answer  # noqa: E402

BASE_SLOTS = set(range(40))
RNG = np.random.default_rng(20261021)


def hill1(labels: list[str]) -> float:
    c = Counter(labels)
    n = sum(c.values())
    if n == 0:
        return float("nan")
    H = -sum(v / n * math.log(v / n) for v in c.values())
    return math.exp(H)


def rarefied_hill(labels: list[str], depth: int = 25, n_sub: int = 1000) -> dict:
    if len(labels) < depth:
        return {"depth": len(labels), "hill1": hill1(labels), "flag": "fewer_than_depth"}
    arr = np.array(labels)
    vals = [hill1(list(RNG.choice(arr, size=depth, replace=False))) for _ in range(n_sub)]
    return {"depth": depth, "hill1": float(np.mean(vals)), "flag": None}


def goods_coverage(labels: list[str]) -> float | None:
    if not labels:
        return None
    c = Counter(labels)
    return 1.0 - sum(1 for v in c.values() if v == 1) / len(labels)


def boot_beta(labels: list[str], d: str, n_boot: int = 2000) -> dict:
    if not labels:
        return {"P_beta_ge_0.05": None, "P_beta_ge_0.2": None}
    arr = np.array([l != d for l in labels], dtype=float)
    bs = RNG.choice(arr, size=(n_boot, len(arr)), replace=True).mean(axis=1)
    return {"P_beta_ge_0.05": float((bs >= 0.05).mean()), "P_beta_ge_0.2": float((bs >= 0.2).mean()),
            "ci95": [float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))]}


def smooth(counts: dict[str, float], survivors: list[str], pseudo: float = 0.5) -> dict[str, float]:
    keys = survivors + ["other"]
    raw = {k: counts.get(k, 0.0) + (pseudo if k in survivors else 0.0) for k in keys}
    tot = sum(raw.values())
    p_raw = {k: (v / tot if tot > 0 else 1.0 / len(keys)) for k, v in raw.items()}
    return {k: 0.93 * p_raw[k] + (0.05 / len(survivors) if k in survivors else 0.0) + (0.02 if k == "other" else 0.0)
            for k in keys}


def prox_forecast(u: str, d: str, survivors: list[str], twin_default_codes: list[str]) -> dict:
    sys.path.insert(0, str(SRC.parent / "vendor" / "exp23"))
    from prox import zs_pair
    from unitlib import strip_comments_docstrings, unit_mod
    refs = unit_mod(u).REFERENCES
    codes = [strip_comments_docstrings(c) for c in twin_default_codes[:10]]
    dist = {}
    for j in survivors:
        rj = strip_comments_docstrings(refs[j])
        ds = [zs_pair(rj, c) for c in codes]
        ds = [x for x in ds if x is not None]
        dist[j] = float(np.mean(ds)) if ds else None
    vals = [v for v in dist.values() if v is not None]
    med = float(np.median(vals)) if vals else 1.0
    logits = {j: (-dist[j] / med if dist[j] is not None and med > 0 else 0.0) for j in survivors}
    mx = max(logits.values())
    ex = {j: math.exp(v - mx) for j, v in logits.items()}
    tot = sum(ex.values())
    p_raw = {j: ex[j] / tot for j in survivors}
    p_raw["other"] = 0.0
    p = {k: 0.93 * p_raw[k] + (0.05 / len(survivors) if k in survivors else 0.0) + (0.02 if k == "other" else 0.0)
         for k in survivors + ["other"]}
    return {"distribution": p, "distances": dist, "median": med, "n_twin_programs": len(codes)}


def grep_audit(u: str) -> dict:
    spec = UNITS[u]
    names = set()
    for m, (dn, _) in spec["modes"].items():
        names.add(dn.lower())
        names.add(re.sub(r"^(a|an|the)\s+", "", dn.lower()))
    for aa in spec["aliases"].values():
        names.update(a.lower() for a in aa if re.search(r"[a-z]", a.lower()) and len(a) > 2)
    viol = []
    n = 0
    for r in read_jsonl(PROMPTS):
        if r["unit"] != u:
            continue
        n += 1
        cond = r["segment"].lower() if r["kind"] in ("twin", "novelty") else (
            r["user_text"].split("\n\n")[-1].lower() if r["kind"] == "assoc" else "")
        cue = any(c in cond for c in PROHIBITION_CUES)
        if not cue:
            continue
        for nm in names:
            if re.search(r"(?<![a-z0-9_])" + re.escape(nm) + r"(?![a-z0-9_])", cond):
                viol.append({"pid": r["pid"], "name": nm})
    return {"n_prompts": n, "violations": viol, "pass": not viol}


def base_audit(u: str, rows: list[dict], d: str | None) -> dict:
    from judge5 import adjudicate_many
    labs = {l["key"]: l for l in read_jsonl(LABELS) if l["unit"] == u}
    corr = [r for r in rows if r["arm"] == "BASE" and r["slot"] in BASE_SLOTS and r["passed"]]
    nond = [r for r in corr if r["label"] != d]
    rest = [r for r in corr if r["label"] == d]
    pick = (nond + rest)[:15]
    items = [(r["key"], u, labs[r["key"]]["code"]) for r in pick]
    res = adjudicate_many(items, f"base_audit:{u}")
    lab = {r["key"]: r["label"] for r in pick}
    agree = [x["label"] == lab[x["id"]] for x in res if x["label"] is not None]
    return {"n": len(items), "n_adjudicated": len(agree), "agreement": (sum(agree) / len(agree)) if agree else None,
            "items": [{"key": x["id"], "labeller": lab[x["id"]], "judges": x["label"], "how": x["how"]} for x in res]}


def compute_unit(u: str, do_audit: bool = True) -> dict:
    adjudicate_pending([u])
    rows = final_rows(u)
    cat = frozen_catalogue(u)
    catset = set(cat)
    tw = [r for r in rows if r["arm"] == "TWIN" and r["model_tag"] == "instruct" and r["slot"] in range(10)]
    tw_corr = [r["label"] for r in tw if r["passed"] and r["label"] not in EXCLUDE]
    c = Counter(tw_corr)
    modal, mshare = (c.most_common(1)[0][0], c.most_common(1)[0][1] / len(tw_corr)) if tw_corr else (None, 0.0)
    default = modal if (modal in catset and mshare >= DEFAULT_SHARE and len(tw) >= 50) else "NO_DEFAULT"
    flags = []
    if len(tw_corr) < 10:
        flags.append(f"default_from_few_correct(n_correct={len(tw_corr)})")
    twin_pass = sum(r["passed"] for r in tw) / len(tw) if tw else None
    if twin_pass is not None and twin_pass < 0.7:
        flags.append(f"twin_pass_below_0.7({twin_pass:.2f})")
    write_json(UNITS_DIR / u / "default.json", {"unit": u, "default": default if default != "NO_DEFAULT" else None,
                                                 "modal_correct": modal, "modal_share": mshare,
                                                 "n_twin": len(tw), "n_twin_correct": len(tw_corr), "utc": utc_now()})
    d = default if default != "NO_DEFAULT" else None
    survivors = [m for m in cat if m != d]
    base = [r for r in rows if r["arm"] == "BASE" and r["model_tag"] == "base" and r["slot"] in BASE_SLOTS]
    b_corr = [r["label"] for r in base if r["passed"] and r["label"] != "disputed"]
    b_att = [r["label"] for r in base if r["label"] not in EXCLUDE]
    plain = [r for r in rows if r["arm"] == "PLAIN"]
    p_corr = [r["label"] for r in plain if r["passed"] and r["label"] != "disputed"]
    beta_correct = (sum(l != d for l in b_corr) / len(b_corr)) if b_corr and d else None
    beta_attempt = (sum(l != d for l in b_att) / len(b_att)) if b_att and d else None
    beta_plain = (sum(l != d for l in p_corr) / len(p_corr)) if p_corr and d else None
    use_attempt = len(b_corr) < 20
    beta = beta_attempt if use_attempt else beta_correct
    if use_attempt:
        flags.append(f"base_fewer_than_20_correct(n={len(b_corr)}): attempt composition used")
    comp_src = b_att if use_attempt else b_corr
    nd = Counter(l for l in comp_src if l in catset and l != d)
    if nd:
        top = nd.most_common()
        ties = [k for k, v in top if v == top[0][1]]
        r_u = ties[0] if len(ties) == 1 else "tie"
    else:
        ties, r_u = [], None
    bb = boot_beta(comp_src, d) if d else {}
    # rivals
    margins = read_json(RESULTS_DIR / "margins.json").get(u, {}).get("by_mode", {})
    R_margin = None
    if d and margins and d in margins:
        diffs = []
        for w in margins[d]["logp"]:
            best_s = max(margins[j]["logp"][w] for j in survivors if j in margins)
            diffs.append(margins[d]["logp"][w] - best_s)
        R_margin = -float(np.mean(diffs))
    tests = [json.loads(l) for l in (UNITS_DIR / u / "tests.jsonl").read_text().splitlines() if l.strip()]
    tot_t = {m: sum(c_["ref_times"][m] for c_ in tests) for m in cat if m in tests[0]["ref_times"]}
    from unitlib import unit_mod
    refs = unit_mod(u).REFERENCES
    R_merit_rt = R_merit_len = None
    if d and d in tot_t and survivors:
        fastest = min(tot_t[j] for j in survivors if j in tot_t)
        R_merit_rt = -math.log(max(fastest, 1e-9) / max(tot_t[d], 1e-9))
        shortest = min(len(refs[j].strip()) for j in survivors)
        R_merit_len = -math.log(shortest / len(refs[d].strip()))
    R_modal = 1.0 - mshare if tw_corr else None
    nov = [r for r in rows if r["arm"] == "NOV" and r["slot"] in range(30)]
    nsum = summarise(nov, catset, d) if d else None
    R_novel = nsum["share"] if nsum else None
    nov_c = [r for r in nov if r["passed"]]
    R_novel_correct = (sum(1 for r in nov_c if r["label"] in catset and r["label"] != d) / len(nov_c)) \
        if (nov_c and d) else None
    # forecasts
    fc = {}
    if d and survivors:
        bc = Counter(l if l in survivors else "other" for l in comp_src if l != d)
        fc["BASE"] = smooth(dict(bc), survivors)
        assoc = [l for l in read_jsonl(LABELS) if l["unit"] == u and l["arm"] == f"ASSOC_{d}" and l["slot"] < 20]
        ac = Counter(map_answer(u, l["assoc_answer"], modes=survivors) for l in assoc)
        fc["ASSOC"] = smooth(dict(ac), survivors)
        fc["ASSOC_raw_counts"] = dict(ac)
        labs = {l["key"]: l for l in read_jsonl(LABELS) if l["unit"] == u}
        tw_codes = [labs[r["key"]]["code"] for r in tw if r["passed"] and r["label"] == d][:10]
        px = prox_forecast(u, d, survivors, tw_codes)
        fc["PROX"] = px["distribution"]
        fc["PROX_detail"] = {k: v for k, v in px.items() if k != "distribution"}
    audit = base_audit(u, rows, d) if (do_audit and d) else None
    ga = grep_audit(u)
    rec = {
        "schema": "iter5_panelB_unit_commit_v1", "unit": u, "unit_id": UNITS[u]["unit_id"], "utc": utc_now(),
        "catalogue": cat, "K_u": len(cat), "excluded_by_limit": UNITS[u]["excluded_by_limit"],
        "default": default, "flags": flags,
        "twin": {"n": len(tw), "pass": twin_pass, "correct_composition": dict(c),
                 "attempted_composition": dict(Counter(r["label"] for r in tw)), "modal_share": mshare},
        "base": {"n": len(base), "n_correct": len(b_corr), "n_valid_attempts": len(b_att),
                 "correct_composition": dict(Counter(b_corr)), "attempted_composition": dict(Counter(b_att)),
                 "beta_u": beta, "beta_correct": beta_correct, "beta_attempt": beta_attempt, "beta_plain": beta_plain,
                 "beta_source": "attempt" if use_attempt else "correct", "r_u": r_u, "r_u_ties": ties,
                 "hill1_rarefied": rarefied_hill(comp_src) if comp_src else None,
                 "goods_coverage": goods_coverage(comp_src), **bb,
                 "plain": {"n": len(plain), "n_correct": len(p_corr), "correct_composition": dict(Counter(p_corr))}},
        "rivals": {"R_margin": R_margin, "R_merit_runtime": R_merit_rt, "R_merit_length": R_merit_len,
                   "R_modal": R_modal, "R_novel": R_novel, "R_novel_correct": R_novel_correct, "K_u": len(cat),
                   "ref_total_runtime_s": tot_t},
        "novelty_cell": nsum,
        "forecasts": fc,
        "predicted_class": None if beta is None else ("MOVABLE" if beta >= 0.05 else "IMMOVABLE"),
        "predicted_landing": r_u,
        "base_label_audit": audit, "grep_audit": ga,
        "input_hashes": {"labels.jsonl": sha256_file(LABELS), "spec": sha256_file(SRC / "units_spec.py"),
                         "tests": sha256_file(UNITS_DIR / u / "tests.jsonl"),
                         "labeller": sha256_file(SRC / "units" / f"{u.lower()}.py"),
                         "unitlib": sha256_file(SRC / "unitlib.py"),
                         "catalogue_frozen": sha256_file(UNITS_DIR / u / "catalogue_frozen.json"),
                         "gate": sha256_file(UNITS_DIR / u / "gate.json")},
    }
    return rec


def commit_unit(u: str, do_audit: bool = True) -> dict:
    v = verify_unit_commit(u)
    if v["ok"]:
        logger.info(f"{u} already committed: {v}")
        return read_json(PRED_DIR / "units" / f"{u}.json")
    g = read_json(UNITS_DIR / u / "gate.json")
    gh = UNITS_DIR / u / "gate_revision.json"
    status = read_json(gh)["status"] if gh.exists() else g["status"]
    assert status == "gated", f"{u} has not passed gate stage (ii): {status}"
    rec = compute_unit(u, do_audit)
    assert rec["grep_audit"]["pass"], f"{u} grep audit violations: {rec['grep_audit']['violations']}"
    p = PRED_DIR / "units" / f"{u}.json"
    write_json(p, rec)
    out = commit([p], f"unit_commit:{u}")
    logger.info(f"{u} COMMITTED: default {rec['default']} beta {rec['base']['beta_u']} r_u {rec['predicted_landing']} "
                f"class {rec['predicted_class']} -> {out[-1]['chain'][:12]}")
    return rec


if __name__ == "__main__":
    setup_logging("quantities")
    for uu in sys.argv[1].split(","):
        commit_unit(uu, do_audit="--no-audit" not in sys.argv)
