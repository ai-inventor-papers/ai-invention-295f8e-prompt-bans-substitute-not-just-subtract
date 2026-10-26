#!/usr/bin/env python3
"""Step F: ban-free forecasts for every event (computed before any ban is sampled).

Families (top-1 read on the TRANSFERRED component):
  SUBTRACT  = landing among non-banned attempts of the last persistent/iterated veto round with >= 20 non-banned
              attempts (weighted for present-minor events); transferred = landing of the hit samples only.
  LADDER    = modal events: pooled non-D landing over the generic pushes (nonce, novelty, randdir s0-s2) that each
              have >= 20 non-D attempts; present-minor events: B_S, transferred = delta(D).
  ASSOCIATE = (1 - s_X) B_S + s_X delta(ASSOCIATE_target(X))   [point mass delta(target) = sensitivity]
  PROXIMITY = (1 - s_X) B_S + s_X delta(PROXIMITY_target(X))   [point mass = sensitivity]
  RENORM    = B_S (descriptive), ONE-SHOT = one-shot veto landing (descriptive, C2b).
B_S = decision-set attempted composition over S + {other} without X (uniform if < 5 such programs);
s_X = X's attempted share in the decision set."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from src import prompts_llama as P
from src.scoring import bins_of, uniform

PUSHES = ["nonce", "novelty", "randdir:s0", "randdir:s1", "randdir:s2"]


def counts(labels: list[str], X: str, S: list[str], weights: list[float] | None = None) -> Counter:
    b = set(bins_of(S))
    c = Counter()
    for i, l in enumerate(labels):
        if l in b and l != X:
            c[l] += (weights[i] if weights else 1.0)
    return c


def normalise(c: Counter, S: list[str]) -> dict[str, float] | None:
    tot = sum(c.values())
    if tot <= 0:
        return None
    return {k: c.get(k, 0.0) / tot for k in bins_of(S)}


def argmax(d: dict[str, float] | None, S: list[str]) -> str | None:
    if not d:
        return None
    order = bins_of(S)
    return max(order, key=lambda k: (d.get(k, 0.0), -order.index(k)))


def mass_transfer(B_S: dict[str, float], s_x: float, target: str | None, S: list[str]) -> dict[str, float] | None:
    if target is None:
        return None
    return {k: (1 - s_x) * B_S.get(k, 0.0) + (s_x if k == target else 0.0) for k in bins_of(S)}


def build_event(ev: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    t, X, et = ev["task"], ev["banned"], ev["event_type"]
    D = ev["D"]
    S = [m for m in P.modes(t) if m != X]
    dec = ctx["decision_labels"][t]                     # list of labels (attempted + invalid)
    att = [l for l in dec if l not in ("invalid", "unresolved")]
    cB = counts(att, X, S)
    nB = sum(cB.values())
    B_S = normalise(cB, S) if nB >= 5 else uniform(S)
    s_x = sum(1 for l in att if l == X) / max(len(att), 1)
    fam: dict[str, dict[str, Any]] = {}
    fam_pm: dict[str, dict[str, Any]] = {}
    flags = []
    # ---------------- SUBTRACT
    vr = ctx["veto"].get(ev["event_id"], {})
    rounds = vr.get("persistent_rounds", [])
    chosen = None
    for r in rounds:
        nb = sum(counts(r["labels"], X, S, r["weights"]).values())
        r["n_nonbanned_w"] = nb
        if nb >= 20:
            chosen = r
    if chosen is not None:
        f = normalise(counts(chosen["labels"], X, S, chosen["weights"]), S)
        hl = [l for l, h in zip(chosen["labels"], chosen["hit"]) if h]
        hw = [w for w, h in zip(chosen["weights"], chosen["hit"]) if h]
        tr = normalise(counts(hl, X, S, hw), S)
        top = argmax(tr, S) if tr else argmax(f, S)
        if not tr:
            flags.append("SUBTRACT transferred component empty -> top-1 from full landing")
        fam["SUBTRACT"] = {"f": f, "top1": top, "defined": True, "round": chosen["round"], "transferred": tr,
                           "n_nonbanned_w": chosen["n_nonbanned_w"], "n_hit": sum(1 for h in chosen["hit"] if h)}
    else:
        why = vr.get("undefined_reason", "no persistent round with >= 20 non-banned attempts")
        fam["SUBTRACT"] = {"f": None, "top1": None, "defined": False, "reason": why}
        flags.append(f"SUBTRACT undefined: {why}")
    # ---------------- LADDER
    if et == "modal":
        per, qual = {}, []
        pooled = Counter()
        for pk in PUSHES:
            labs = ctx["push_labels"].get((t, pk), [])
            c = counts([l for l in labs if l not in ("invalid", "unresolved")], D, [m for m in P.modes(t) if m != D])
            n = sum(c.values())
            per[pk] = {"n_nonD": n, "modal_nonD": argmax(normalise(c, [m for m in P.modes(t) if m != D]),
                                                        [m for m in P.modes(t) if m != D]) if n else None,
                       "counts": dict(c)}
            if n >= 20:
                qual.append(pk)
                pooled.update(c)
        if qual:
            f = normalise(Counter({k: v for k, v in pooled.items() if k in bins_of(S)}), S)
            top = argmax(f, S)
            mods = Counter(per[p]["modal_nonD"] for p in qual)
            exists = any(v >= 2 for v in mods.values())
            fam["LADDER"] = {"f": f, "top1": top, "defined": f is not None, "qualifying_pushes": qual,
                             "per_push": per, "ladder_exists": exists}
        else:
            fam["LADDER"] = {"f": None, "top1": None, "defined": False, "per_push": per, "ladder_exists": False,
                             "reason": "no push with >= 20 non-D attempts"}
            flags.append("LADDER undefined")
    else:
        fam["LADDER"] = {"f": dict(B_S), "top1": D, "defined": True, "transferred": {D: 1.0},
                         "note": "present-minor: the default survives (B_S), transferred component = delta(D)"}
    # ---------------- ASSOCIATE
    at = ctx["assoc_targets"].get(f"{t}|{X}", {})
    tgt = at.get("target")
    if tgt is not None and tgt in S:
        fam["ASSOCIATE"] = {"f": mass_transfer(B_S, s_x, tgt, S), "top1": tgt, "defined": True,
                            "target": tgt, "survivor_counts": at.get("survivor_counts")}
        fam_pm["ASSOCIATE"] = {"f": {k: (1.0 if k == tgt else 0.0) for k in bins_of(S)}, "defined": True}
    else:
        fam["ASSOCIATE"] = {"f": None, "top1": None, "defined": False, "reason": "no answer maps to a survivor"}
        fam_pm["ASSOCIATE"] = {"f": None, "defined": False}
        flags.append("ASSOCIATE undefined")
    # ---------------- PROXIMITY
    px = ctx["proximity"].get(ev["event_id"], {})
    ptg = px.get("nominee_zs")
    if ptg is not None and ptg in S:
        fam["PROXIMITY"] = {"f": mass_transfer(B_S, s_x, ptg, S), "top1": ptg, "defined": True, "target": ptg,
                            "zs_median": px.get("zs_median"), "nominee_tok": px.get("nominee_tok")}
        fam_pm["PROXIMITY"] = {"f": {k: (1.0 if k == ptg else 0.0) for k in bins_of(S)}, "defined": True}
    else:
        fam["PROXIMITY"] = {"f": None, "top1": None, "defined": False, "reason": "no proximity nominee"}
        fam_pm["PROXIMITY"] = {"f": None, "defined": False}
        flags.append("PROXIMITY undefined")
    # point-mass sensitivity for SUBTRACT / LADDER = their own landings
    fam_pm["SUBTRACT"] = {"f": fam["SUBTRACT"]["f"], "defined": fam["SUBTRACT"]["defined"]}
    fam_pm["LADDER"] = {"f": fam["LADDER"]["f"], "defined": fam["LADDER"]["defined"]}
    # ---------------- descriptive
    one = vr.get("oneshot")
    one_f = normalise(counts(one["labels"], X, S, one["weights"]), S) if one else None
    out = {"event_id": ev["event_id"], "task": t, "event_type": et, "X": X, "D": D, "S": S, "bins": bins_of(S),
           "B_S": B_S, "n_B_S_programs": nB, "s_X": s_x, "families": fam, "families_pm": fam_pm,
           "RENORM": B_S, "ONESHOT": one_f, "oneshot_moved_share": (one or {}).get("moved_share"),
           "top1_transferred": {k: v["top1"] for k, v in fam.items()}, "flags": flags,
           "ngram": vr.get("ngrams")}
    tops = [v["top1"] for v in fam.values() if v["defined"]]
    out["disagreeing_forecast"] = len(set(tops)) > 1
    return out


def push_label_index(labels: list[dict[str, Any]]) -> dict[tuple[str, str], list[str]]:
    idx: dict[tuple[str, str], list[str]] = defaultdict(list)
    for r in labels:
        c = r.get("condition") or ""
        if r.get("phase") == "B5" and c in ("nonce", "novelty"):
            idx[(r["task"], c)].append(r["label"])
        elif r.get("phase") == "E3" and c.startswith("randdir:"):
            idx[(r["task"], c)].append(r["label"])
    return idx
