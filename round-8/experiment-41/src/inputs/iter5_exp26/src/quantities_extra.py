#!/usr/bin/env python3
"""Per-unit quantities + COMMIT for the extra arm (P_<t> parent re-measure, V_<t> disguised variant), before their
first push sample. Same definitions as src/quantities.py (default, beta_u, r_u, Hill-1, coverage, bootstrap,
R_modal); association, novelty, margins and proximity are not part of the extra arm. Variant gate: the parent's
labellers (100% on the parent's references, units/<u>/gate_stage_i.json) plus a blind-judge spot-check of the 10
variant gate-draw programs (agreement >= 0.8 required, reported)."""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

import units_extra  # noqa: E402  (registers cards)
from cfg5 import (DEFAULT_SHARE, LABELS, PRED_DIR, PROHIBITION_CUES, UNITS_DIR, read_json, read_jsonl,  # noqa: E402
                  setup_logging, sha256_file, utc_now, write_json)
from commit5 import commit, verify_unit_commit  # noqa: E402
from judge5 import adjudicate_many  # noqa: E402
from labels_view import EXCLUDE, adjudicate_pending, final_rows, frozen_catalogue  # noqa: E402
from quantities import boot_beta, goods_coverage, rarefied_hill  # noqa: E402
from units_spec import UNITS  # noqa: E402


def grep_audit_extra(u: str) -> dict:
    spec = UNITS[u]
    names = set()
    for m, (dn, _) in spec["modes"].items():
        names.add(dn.lower())
        names.add(re.sub(r"^(a|an|the)\s+", "", dn.lower()))
    for aa in spec["aliases"].values():
        names.update(a.lower() for a in aa if re.search(r"[a-z]", a.lower()) and len(a) > 2)
    viol, n = [], 0
    for r in read_jsonl(units_extra.PROMPTS_EXTRA):
        if r["unit"] != u:
            continue
        n += 1
        cond = r["segment"].lower()
        if not any(c in cond for c in PROHIBITION_CUES):
            continue
        for nm in names:
            if re.search(r"(?<![a-z0-9_])" + re.escape(nm) + r"(?![a-z0-9_])", cond):
                viol.append({"pid": r["pid"], "name": nm})
    return {"n_prompts": n, "violations": viol, "pass": not viol}


def variant_spot_check(u: str) -> dict:
    rows = [r for r in final_rows(u) if r["arm"] == "GATE" and r["valid"]][:10]
    labs = {l["key"]: l for l in read_jsonl(LABELS) if l["unit"] == u}
    res = adjudicate_many([(r["key"], u, labs[r["key"]]["code"]) for r in rows], f"variant_spot_check:{u}")
    lab = {r["key"]: r["label"] for r in rows}
    ok = [x["label"] == lab[x["id"]] for x in res if x["label"] is not None]
    agr = sum(ok) / len(ok) if ok else None
    rep = {"unit": u, "utc": utc_now(), "n": len(rows), "n_adjudicated": len(ok), "agreement": agr,
           "status": "gated" if (agr is not None and agr >= 0.8) else "failed",
           "items": [{"key": x["id"], "labeller": lab[x["id"]], "judges": x["label"], "how": x["how"]} for x in res]}
    write_json(UNITS_DIR / u / "gate.json", rep)
    return rep


def compute(u: str) -> dict:
    adjudicate_pending([u])
    rows = final_rows(u)
    cat = frozen_catalogue(u)
    catset = set(cat)
    tw = [r for r in rows if r["arm"] == "TWIN" and r["slot"] in range(10)]
    tw_corr = [r["label"] for r in tw if r["passed"] and r["label"] not in EXCLUDE]
    c = Counter(tw_corr)
    modal, mshare = (c.most_common(1)[0][0], c.most_common(1)[0][1] / len(tw_corr)) if tw_corr else (None, 0.0)
    default = modal if (modal in catset and mshare >= DEFAULT_SHARE and len(tw) >= 50) else "NO_DEFAULT"
    write_json(UNITS_DIR / u / "default.json", {"unit": u, "default": default if default != "NO_DEFAULT" else None,
                                                 "modal_correct": modal, "modal_share": mshare, "utc": utc_now()})
    d = default if default != "NO_DEFAULT" else None
    flags = []
    twin_pass = sum(r["passed"] for r in tw) / len(tw) if tw else None
    if twin_pass is not None and twin_pass < 0.7:
        flags.append(f"twin_pass_below_0.7({twin_pass:.2f})")
    base = [r for r in rows if r["arm"] == "BASE" and r["slot"] < 40]
    b_corr = [r["label"] for r in base if r["passed"] and r["label"] != "disputed"]
    b_att = [r["label"] for r in base if r["label"] not in EXCLUDE]
    beta_c = (sum(l != d for l in b_corr) / len(b_corr)) if (b_corr and d) else None
    beta_a = (sum(l != d for l in b_att) / len(b_att)) if (b_att and d) else None
    use_att = len(b_corr) < 20
    if use_att:
        flags.append(f"base_fewer_than_20_correct(n={len(b_corr)}): attempt composition used")
    beta = beta_a if use_att else beta_c
    src = b_att if use_att else b_corr
    nd = Counter(l for l in src if l in catset and l != d)
    ties = [k for k, v in nd.items() if nd and v == max(nd.values())]
    r_u = (ties[0] if len(ties) == 1 else "tie") if nd else None
    return {"schema": "iter5_panelB_unit_commit_v1", "unit": u, "unit_id": UNITS[u]["unit_id"], "utc": utc_now(),
            "unit_kind": "parent_remeasure" if u.startswith("P_") else "disguised_variant",
            "parent_id": units_extra.parent_of(u), "catalogue": cat, "K_u": len(cat), "excluded_by_limit": [],
            "default": default, "flags": flags,
            "twin": {"n": len(tw), "pass": twin_pass, "correct_composition": dict(c),
                     "attempted_composition": dict(Counter(r["label"] for r in tw)), "modal_share": mshare},
            "base": {"n": len(base), "n_correct": len(b_corr), "n_valid_attempts": len(b_att),
                     "correct_composition": dict(Counter(b_corr)), "attempted_composition": dict(Counter(b_att)),
                     "beta_u": beta, "beta_correct": beta_c, "beta_attempt": beta_a, "beta_plain": None,
                     "beta_source": "attempt" if use_att else "correct", "r_u": r_u, "r_u_ties": ties,
                     "hill1_rarefied": rarefied_hill(src) if src else None, "goods_coverage": goods_coverage(src),
                     **(boot_beta(src, d) if d else {})},
            "rivals": {"R_margin": None, "R_merit_runtime": None, "R_merit_length": None,
                       "R_modal": (1.0 - mshare) if tw_corr else None, "R_novel": None, "R_novel_correct": None,
                       "K_u": len(cat)},
            "forecasts": {}, "predicted_class": None if beta is None else ("MOVABLE" if beta >= 0.05 else "IMMOVABLE"),
            "predicted_landing": r_u, "grep_audit": grep_audit_extra(u),
            "input_hashes": {"labels.jsonl": sha256_file(LABELS),
                             "prompts_extra": sha256_file(units_extra.PROMPTS_EXTRA),
                             "catalogue_frozen": sha256_file(UNITS_DIR / u / "catalogue_frozen.json")}}


def commit_extra(u: str) -> dict:
    v = verify_unit_commit(u)
    if v["ok"]:
        return read_json(PRED_DIR / "units" / f"{u}.json")
    assert read_json(UNITS_DIR / u / "gate_stage_i.json")["status"] == "PROVISIONAL"
    if u.startswith("V_"):
        g = variant_spot_check(u)
        logger.info(f"{u} spot-check agreement {g['agreement']} -> {g['status']}")
    rec = compute(u)
    if u.startswith("V_"):
        rec["variant_spot_check"] = {k: v for k, v in read_json(UNITS_DIR / u / "gate.json").items() if k != "items"}
        if rec["variant_spot_check"]["status"] != "gated":
            rec["flags"].append("variant_spot_check_below_0.8")
    assert rec["grep_audit"]["pass"], rec["grep_audit"]
    p = PRED_DIR / "units" / f"{u}.json"
    write_json(p, rec)
    out = commit([p], f"unit_commit:{u}")
    logger.info(f"{u} COMMITTED: default {rec['default']} beta {rec['base']['beta_u']} r_u {rec['predicted_landing']} "
                f"-> {out[-1]['chain'][:12]}")
    return rec


if __name__ == "__main__":
    setup_logging("quantities_extra")
    for uu in sys.argv[1].split(","):
        commit_extra(uu)
