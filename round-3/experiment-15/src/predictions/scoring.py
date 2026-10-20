#!/usr/bin/env python3
"""FROZEN C1 scoring rule (hash-chained in commitments.log before the first ban sample).

Per event: bins = survivors S (catalogue minus the banned X) + 'other'.
  q = 0.93 f + 0.05 Uniform(S) + 0.02 delta(other)        (an undefined f is uniform over S + {other})
  log score = mean over non-banned attempts (valid programs, label != X, label in bins) of log q(label)
  gate_pass = avoidance >= 0.5 AND >= 20 non-banned attempts, avoidance = 1 - share of X among attempts
  hit (modal) = modal non-banned label of the ban landing; hit (present-minor) = argmax_S (ban share - B_S share)
  disagreeing = the top-1s (transferred component) of the DEFINED families in DISAGREEMENT_FAMILIES are not all equal
  ADVANCE: on each disagreeing gated event the best family 'wins' if it beats the runner-up by >= 0.10 nats;
           a family advances if it wins >= 3 events.
  Wilcoxon (only if >= 10 disagreeing gated events): paired signed-rank on per-event log-score differences for
           SUBTRACT-ASSOCIATE, SUBTRACT-PROXIMITY, LADDER-ASSOCIATE, LADDER-PROXIMITY; Holm at 0.05; task-cluster
           bootstrap CI (2,000 resamples) of the mean difference.
  BRANCH: UNDETERMINED (< 3 disagreeing gated events) > SUBTRACTION/LADDER (SUBTRACT or LADDER advances) /
          SUBSTITUTION (ASSOCIATE or PROXIMITY advances; both sides advancing -> CONFLICT) >
          X-SPECIFIC BUT UNAIMED (no family's top-1 hit rate on gated events exceeds chance, one-sided exact binomial
          p < 0.05 against the mean 1/|S|) > NO FAMILY ADVANCES (aimed, unresolved).
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

import numpy as np

SMOOTH_F, SMOOTH_U, SMOOTH_O = 0.93, 0.05, 0.02
FAMILIES = ["SUBTRACT", "LADDER", "ASSOCIATE", "PROXIMITY"]
DISAGREEMENT_FAMILIES = FAMILIES
ADV_MARGIN = 0.10
ADV_WINS = 3
MIN_NONBANNED = 20
MIN_AVOID = 0.5
PAIRS = [("SUBTRACT", "ASSOCIATE"), ("SUBTRACT", "PROXIMITY"), ("LADDER", "ASSOCIATE"), ("LADDER", "PROXIMITY")]


def bins_of(S: list[str]) -> list[str]:
    return list(S) + ["other"]


def uniform(S: list[str]) -> dict[str, float]:
    b = bins_of(S)
    return {k: 1.0 / len(b) for k in b}


def smooth(f: dict[str, float] | None, S: list[str]) -> dict[str, float]:
    b = bins_of(S)
    if f is None:
        f = uniform(S)
    tot = sum(max(f.get(k, 0.0), 0.0) for k in b)
    f = {k: (max(f.get(k, 0.0), 0.0) / tot if tot > 0 else 1.0 / len(b)) for k in b}
    q = {k: SMOOTH_F * f[k] + (SMOOTH_U / len(S) if k in S else 0.0) + (SMOOTH_O if k == "other" else 0.0) for k in b}
    return q


def nonbanned(labels: list[str], X: str, S: list[str], weights: list[float] | None = None) -> tuple[list[str], list[float]]:
    b = set(bins_of(S))
    w = weights or [1.0] * len(labels)
    out_l, out_w = [], []
    for l, ww in zip(labels, w):
        if l in ("invalid", "unresolved", None) or l == X:
            continue
        if l in b:
            out_l.append(l)
            out_w.append(ww)
    return out_l, out_w


def log_score(q: dict[str, float], labels: list[str], weights: list[float] | None = None) -> float:
    if not labels:
        return float("nan")
    w = weights or [1.0] * len(labels)
    return float(sum(ww * math.log(q[l]) for l, ww in zip(labels, w)) / sum(w))


def gate(attempt_labels: list[str], X: str, S: list[str]) -> dict[str, Any]:
    att = [l for l in attempt_labels if l not in ("invalid", "unresolved", None)]
    n_att = len(att)
    nx = sum(1 for l in att if l == X)
    nb, _ = nonbanned(att, X, S)
    avoid = 1 - nx / n_att if n_att else float("nan")
    return {"n_attempts": n_att, "n_banned": nx, "n_nonbanned": len(nb), "avoidance": avoid,
            "gate_pass": bool(n_att and avoid >= MIN_AVOID and len(nb) >= MIN_NONBANNED)}


def realised_hit(event_type: str, landing: dict[str, float], S: list[str], B_S: dict[str, float]) -> str | None:
    if not landing:
        return None
    if event_type == "modal":
        return max(sorted(landing), key=lambda k: landing[k])
    ex = {k: landing.get(k, 0.0) - B_S.get(k, 0.0) for k in S}
    return max(S, key=lambda k: (ex[k], -S.index(k)))


def score_event(ev: dict[str, Any], fc: dict[str, Any], ban_labels: list[str]) -> dict[str, Any]:
    """ev: {event_type, X, S}; fc: {family: {f, top1, defined}, family_pm: ...}; ban_labels: attempted labels."""
    X, S = ev["X"], ev["S"]
    g = gate(ban_labels, X, S)
    nb, _ = nonbanned(ban_labels, X, S)
    cnt = Counter(nb)
    landing = {k: cnt.get(k, 0) / len(nb) for k in bins_of(S)} if nb else {}
    hit = realised_hit(ev["event_type"], landing, S, fc["B_S"])
    out = {"gate": g, "landing": landing, "hit_label": hit, "logscore": {}, "logscore_pm": {}, "top1": {},
           "top1_hit": {}, "defined": {}}
    for fam in FAMILIES:
        f = fc["families"][fam]
        q = smooth(f["f"] if f["defined"] else None, S)
        out["logscore"][fam] = log_score(q, nb)
        out["top1"][fam] = f["top1"] if f["defined"] else None
        out["defined"][fam] = f["defined"]
        out["top1_hit"][fam] = (f["top1"] == hit) if (f["defined"] and hit is not None) else None
        fpm = fc["families_pm"].get(fam)
        if fpm is not None:
            qpm = smooth(fpm["f"] if fpm["defined"] else None, S)
            out["logscore_pm"][fam] = log_score(qpm, nb)
    out["logscore"]["RENORM"] = log_score(smooth(fc["B_S"], S), nb)
    out["logscore"]["UNIFORM"] = log_score(smooth(None, S), nb)
    tops = [out["top1"][f] for f in DISAGREEMENT_FAMILIES if out["defined"][f]]
    out["disagreeing"] = len(set(tops)) > 1
    out["n_defined"] = len(tops)
    ls = {f: out["logscore"][f] for f in FAMILIES if not math.isnan(out["logscore"][f])}
    if len(ls) >= 2:
        srt = sorted(ls.items(), key=lambda kv: -kv[1])
        out["best"], out["margin"] = srt[0][0], srt[0][1] - srt[1][1]
    else:
        out["best"], out["margin"] = None, float("nan")
    out["winner"] = out["best"] if (g["gate_pass"] and out["disagreeing"] and out["margin"] >= ADV_MARGIN) else None
    out["chance"] = 1.0 / len(S)
    return out


def holm(pvals: dict[str, float], alpha: float = 0.05) -> dict[str, dict[str, Any]]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    out = {}
    stop = False
    for i, (k, p) in enumerate(items):
        thr = alpha / (m - i)
        rej = (not stop) and p <= thr
        if not rej:
            stop = True
        out[k] = {"p": p, "holm_threshold": thr, "reject": rej, "p_adj": min(1.0, max(p * (m - j) for j, (_, p) in
                                                                                       enumerate(items[: i + 1])))}
    return out


def aggregate(rows: list[dict[str, Any]], seed: int = 0) -> dict[str, Any]:
    """rows: per-event {task, scored: score_event output}."""
    from scipy.stats import binomtest, wilcoxon

    gated_dis = [r for r in rows if r["scored"]["gate"]["gate_pass"] and r["scored"]["disagreeing"]]
    wins = Counter(r["scored"]["winner"] for r in gated_dis if r["scored"]["winner"])
    adv = {f: wins.get(f, 0) >= ADV_WINS for f in FAMILIES}
    res: dict[str, Any] = {"n_events": len(rows), "n_gated": sum(1 for r in rows if r["scored"]["gate"]["gate_pass"]),
                           "n_disagreeing_gated": len(gated_dis), "wins": dict(wins), "advances": adv}
    wil = {}
    if len(gated_dis) >= 10:
        pv = {}
        rng = np.random.default_rng(seed)
        for a, b in PAIRS:
            d = [(r["task"], r["scored"]["logscore"][a] - r["scored"]["logscore"][b]) for r in gated_dis]
            vals = np.array([x for _, x in d])
            try:
                st = wilcoxon(vals)
                p = float(st.pvalue)
            except ValueError:
                p = 1.0
            tasks = sorted({t for t, _ in d})
            boots = []
            for _ in range(2000):
                tk = rng.choice(tasks, size=len(tasks), replace=True)
                vv = [x for t in tk for (tt, x) in d if tt == t]
                boots.append(np.mean(vv))
            wil[f"{a}-{b}"] = {"mean_diff": float(vals.mean()), "n": len(vals), "p": p,
                               "boot_ci": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]}
            pv[f"{a}-{b}"] = p
        hh = holm(pv)
        for k in wil:
            wil[k].update(hh[k])
        res["wilcoxon"] = wil
    else:
        res["wilcoxon"] = {"not_run": f"{len(gated_dis)} disagreeing gated events < 10"}
    gated = [r for r in rows if r["scored"]["gate"]["gate_pass"]]
    hits = {}
    for f in FAMILIES:
        hh = [r for r in gated if r["scored"]["top1_hit"][f] is not None]
        k = sum(1 for r in hh if r["scored"]["top1_hit"][f])
        ch = float(np.mean([r["scored"]["chance"] for r in hh])) if hh else float("nan")
        p = float(binomtest(k, len(hh), ch, alternative="greater").pvalue) if hh else float("nan")
        hits[f] = {"hits": k, "n": len(hh), "rate": k / len(hh) if hh else float("nan"), "chance": ch, "p_binom": p}
    res["top1_hits_gated"] = hits
    if len(gated_dis) < 3:
        branch = "UNDETERMINED"
    else:
        sl = adv["SUBTRACT"] or adv["LADDER"]
        su = adv["ASSOCIATE"] or adv["PROXIMITY"]
        if sl and su:
            branch = "CONFLICT (both sides advance)"
        elif sl:
            branch = "SUBTRACTION/LADDER (" + ",".join(f for f in ("SUBTRACT", "LADDER") if adv[f]) + ")"
        elif su:
            branch = "SUBSTITUTION (" + ",".join(f for f in ("ASSOCIATE", "PROXIMITY") if adv[f]) + ")"
        elif not any((h["p_binom"] < 0.05) for h in hits.values() if not math.isnan(h["p_binom"])):
            branch = "X-SPECIFIC BUT UNAIMED"
        else:
            branch = "NO FAMILY ADVANCES (aimed, unresolved)"
    res["branch"] = branch
    res["branch_label"] = "within-Llama, pre-pooling"
    res["effective_n"] = {"events": len(rows), "gated": res["n_gated"], "disagreeing_gated": len(gated_dis)}
    return res
