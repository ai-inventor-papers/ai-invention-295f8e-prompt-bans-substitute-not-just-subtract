#!/usr/bin/env python3
"""S7 COMMIT: derived FRLP quantities and the five landing forecasts per banned set, hash-committed (commitments.log)
together with the multi-ban prompts and the sha256 of analysis/landing.py, before any multi-ban sample is drawn.

Forecasts over survivors S of set B (cross-algorithm FRLP comparisons use L^c_j = L_j + log(as-requested share_j)):
  LADDER          p_j ~ exp(L^c_j(base))
  PRIME-AND-VETO  p_j ~ exp(L^c_j(base) + PV_j),  PV_j = mean_w [L_j(mention_w B) - L_j(neutral_w B)] on half 1
  PROXIMITY       softmax(-d(j, B) / median Dbar),  d(j, B) = min_b Dbar[j, b]
  FRLP-BAN        p_j ~ mean_w exp(L^c_j(ban_w B))
  GENERIC         p_j ~ exp(L^c_j(base) + u_j),  u_j = mean_w [L_j(nonce_w) - L_j(neutral_w)] on half 1
Each stored raw and mixed: 0.93 * raw + 0.05 * uniform over survivors + 0.02 on 'other'.
"""

from __future__ import annotations

import collections
import math
from typing import Any

import numpy as np
from loguru import logger

from common import (COMMIT_LOG, RESULTS_DIR, ROOT, THRESHOLDS, commit_payload, read_json, read_jsonl, sha256_file,
                    utc_now, verify_chain, write_json)

PRED_DIR = ROOT / "predictions"
FORECASTS = ("LADDER", "PRIME_AND_VETO", "PROXIMITY", "FRLP_BAN", "GENERIC", "CORPUS")


def cells() -> list[dict[str, Any]]:
    return [r for r in read_jsonl(RESULTS_DIR / "frlp_cells.jsonl") if "variant" not in r]


def cell_index(rows: list[dict[str, Any]]) -> dict[tuple, dict[str, Any]]:
    """(task, condition, template, twin, algorithm, half) -> row (base cells have twin None)."""
    return {(r["task"], r["condition"], r["template"], r.get("twin"), r["algorithm"], r["half"]): r for r in rows}


def combine_halves(c1: dict[str, Any] | None, c2: dict[str, Any] | None) -> float | None:
    """Exact logmeanexp over the union of two halves from their per-half logmeanexps."""
    parts = [(c["L"], c["n_programs"]) for c in (c1, c2) if c is not None]
    if not parts:
        return None
    n = sum(k for _, k in parts)
    m = max(L for L, _ in parts)
    return m + math.log(sum(k * math.exp(L - m) for L, k in parts) / n)


def normalise(w: dict[str, float]) -> dict[str, float]:
    tot = sum(w.values())
    if not np.isfinite(tot) or tot <= 0:
        return {k: 1.0 / len(w) for k in w}
    return {k: v / tot for k, v in w.items()}


def softmax_log(x: dict[str, float]) -> dict[str, float]:
    m = max(x.values())
    return normalise({k: math.exp(v - m) for k, v in x.items()})


def mix(p: dict[str, float]) -> dict[str, float]:
    S = len(p)
    out = {k: (1 - THRESHOLDS["uniform_mix"] - THRESHOLDS["other_floor"]) * v + THRESHOLDS["uniform_mix"] / S
           for k, v in p.items()}
    out["other"] = THRESHOLDS["other_floor"]
    return out


def derived(set_name: str, plan: dict[str, Any], idx: dict[tuple, dict[str, Any]], Lc: dict[str, float],
            corr: dict[str, float]) -> dict[str, Any]:
    cname = f"multi:{set_name}"
    surv, banned = plan["survivors"], plan["banned"]
    tpls = [t["template"] for t in plan["templates"]]
    out: dict[str, Any] = {"G": {}, "G_h2": {}, "PV": {}, "PV_by_template": {}, "banned_drop": [], "L_ban_all": {}}
    for j in surv:
        g, gh2, pv, lb = [], [], [], []
        for w in tpls:
            b1, b2 = idx.get(("t1", cname, w, "ban", j, "h1")), idx.get(("t1", cname, w, "ban", j, "h2"))
            n1, n2 = idx.get(("t1", cname, w, "neutral", j, "h1")), idx.get(("t1", cname, w, "neutral", j, "h2"))
            m1 = idx.get(("t1", cname, w, "mention", j, "h1"))
            Lb, Ln = combine_halves(b1, b2), combine_halves(n1, n2)
            if Lb is not None and Ln is not None:
                g.append(Lb - Ln)
                lb.append(Lb)
            if b2 is not None and n2 is not None:
                gh2.append(b2["L"] - n2["L"])
            if m1 is not None and n1 is not None:
                pv.append(m1["L"] - n1["L"])
        out["G"][j] = float(np.mean(g)) if g else None
        out["G_h2"][j] = float(np.mean(gh2)) if gh2 else None
        out["PV"][j] = float(np.mean(pv)) if pv else None
        out["PV_by_template"][j] = pv
        out["L_ban_all"][j] = lb
    for b in banned:
        for t in plan["templates"]:
            w = t["template"]
            c, n = idx.get(("t1", cname, w, "ban", b, "h1")), idx.get(("t1", cname, w, "neutral", b, "h1"))
            if c is not None and n is not None:
                out["banned_drop"].append({"algorithm": b, "template": w, "drop": c["L"] - n["L"],
                                           "list_position": c.get("list_position"), "ess_ban": c["ess"]})
    # FRLP-implied avoidance (exp(L^c) ~ P(j | c))
    pb = {}
    for b in banned:
        vals = [idx[("t1", cname, t["template"], "ban", b, "h1")]["L"] + corr.get(b, 0.0) for t in plan["templates"]
                if ("t1", cname, t["template"], "ban", b, "h1") in idx]
        pb[b] = float(np.mean([math.exp(v) for v in vals])) if vals else 0.0
    ps = {j: float(np.mean([math.exp(v + corr.get(j, 0.0)) for v in out["L_ban_all"][j]])) if out["L_ban_all"][j]
          else 0.0 for j in surv}
    tot = sum(pb.values()) + sum(ps.values())
    out["frlp_implied_avoidance"] = (sum(ps.values()) / tot) if tot > 0 else None
    out["frlp_implied_banned_share"] = {b: v / tot for b, v in pb.items()} if tot > 0 else None
    out["frlp_mass_ban"] = {"survivors": ps, "banned": pb}
    return out


def generic_profile(idx: dict[tuple, dict[str, Any]], algs: list[str]) -> dict[str, float | None]:
    u = {}
    for j in algs:
        d = []
        for w in ("W1", "W2", "W3", "W4", "W5"):
            c, n = idx.get(("t1", "nonce", w, "ban", j, "h1")), idx.get(("t1", "nonce", w, "neutral", j, "h1"))
            if c is not None and n is not None:
                d.append(c["L"] - n["L"])
        u[j] = float(np.mean(d)) if d else None
    return u


def stage_commit() -> None:
    PRED_DIR.mkdir(exist_ok=True)
    geo = read_json(RESULTS_DIR / "sets_and_geometry.json")
    plan = read_json(RESULTS_DIR / "planned_conditions.json")
    rows = cells()
    idx = cell_index(rows)
    algs = geo["algorithms"]
    Lc = geo["L_base_corrected"]
    corr = {a: Lc[a] - geo["L_base_raw"][a] for a in algs}
    Dbar = np.array(geo["Dbar"])
    med = geo["median_offdiag"]
    u = generic_profile(idx, algs)
    aux = RESULTS_DIR / "aux_datasets.json"
    corpus = read_json(aux)["corpus_counts"]["t1"] if aux.exists() else {}
    landing_py = ROOT / "analysis" / "landing.py"
    assert landing_py.exists(), "analysis/landing.py must exist before the commit"
    payload_files = []
    summary = {}
    for set_name, p in plan["t1"].items():
        surv = p["survivors"]
        dv = derived(set_name, p, idx, Lc, corr)
        eo = geo["edge_opposite"].get(set_name) or {}
        dist = {j: float(min(Dbar[algs.index(j), algs.index(b)] for b in p["banned"])) for j in surv}
        f_raw = {
            "LADDER": softmax_log({j: Lc[j] for j in surv}),
            "PRIME_AND_VETO": softmax_log({j: Lc[j] + (dv["PV"][j] or 0.0) for j in surv}),
            "PROXIMITY": softmax_log({j: -dist[j] / med for j in surv}),
            "FRLP_BAN": normalise({j: dv["frlp_mass_ban"]["survivors"][j] for j in surv}),
            "GENERIC": softmax_log({j: Lc[j] + (u[j] or 0.0) for j in surv}),
        }
        if corpus:
            # addition beyond the plan: external popularity (add-one smoothed corpus naming counts)
            f_raw["CORPUS"] = normalise({j: corpus.get(j, 0) + 1.0 for j in surv})
        payload = {"set": set_name, "task": "t1", "banned": p["banned"], "survivors": surv,
                   "EDGE": eo.get("EDGE"), "OPPOSITE": eo.get("OPPOSITE"), "d_min": dist,
                   "PV_ranking": sorted(surv, key=lambda j: -(dv["PV"][j] if dv["PV"][j] is not None else -1e9)),
                   "forecasts_raw": f_raw, "forecasts_mixed": {k: mix(v) for k, v in f_raw.items()},
                   "top1": {k: max(v, key=v.get) for k, v in f_raw.items()},
                   "frlp_implied_avoidance": dv["frlp_implied_avoidance"],
                   "frlp_implied_banned_share": dv["frlp_implied_banned_share"],
                   "derived": {k: dv[k] for k in ("G", "G_h2", "PV", "PV_by_template", "banned_drop")},
                   "generic_u": {j: u[j] for j in surv}, "L_base_corrected": {j: Lc[j] for j in surv},
                   "prompts": {t["template"]: t["halves"]["1"]["prompts"]["ban"] for t in p["templates"]},
                   "analysis_landing_py_sha256": sha256_file(landing_py), "utc": utc_now()}
        fp = PRED_DIR / f"forecasts_{set_name}.json"
        write_json(fp, payload)
        payload_files.append(fp)
        summary[set_name] = {"survivors": surv, "top1": payload["top1"], "EDGE": eo.get("EDGE"),
                             "OPPOSITE": eo.get("OPPOSITE"), "avoidance_implied": dv["frlp_implied_avoidance"]}
        logger.info(f"{set_name}: banned {p['banned']} survivors {surv}; top1 {payload['top1']}; implied avoidance "
                    f"{dv['frlp_implied_avoidance']}")
    commit_payload(RESULTS_DIR / "planned_conditions.json", note="S7 multi-ban prompts (frozen rule) before sampling")
    for fp in payload_files:
        commit_payload(fp, note="S7 committed landing forecasts before session 2")
    commit_payload(landing_py, note="S7 analysis/landing.py committed before session 2")
    ok, probs = verify_chain()
    write_json(RESULTS_DIR / "commit_summary.json", {"sets": summary, "chain_ok": ok, "problems": probs,
                                                     "commit_log": str(COMMIT_LOG.name), "utc": utc_now()})
    logger.info(f"commit chain ok={ok} {probs}")


__all__ = ["stage_commit", "cells", "cell_index", "combine_halves", "derived", "generic_profile", "mix", "FORECASTS",
           "collections"]
