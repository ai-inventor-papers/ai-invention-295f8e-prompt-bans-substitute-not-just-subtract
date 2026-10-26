#!/usr/bin/env python3
"""The behavioural instrument (frozen in commit #1): exact-decision agreement on the committed probe states, the
stochastic RF matcher, the mechanism class rule and mechanistic compliance.

Decision vectors are uint16 arrays (remaining capacity of the chosen bin; 65535 = error) keyed by harness seed.
A_c(program) = mean over the program's harness seeds s of the share of states where the program's seed-s decision
equals reference c's decision (reference seed s for a stochastic reference, its seed-0 vector otherwise).
"""
from __future__ import annotations

from typing import Any

import numpy as np

ERR = 65535
CLASS_THRESHOLD = 0.95
NOVELTY_THRESHOLD = 0.90
STOCH_DIFF = 0.01            # seeds 0 and 1 differ on >= 1% of states -> STOCHASTIC (adds seeds 2 and 3)
RF_USED_MIN = 0.95           # (i)
RF_KS_MAX = 0.10             # (ii)
RF_S2S_MARGIN = 0.15         # (iii)
DET_RULES = ["BF", "FF", "WF", "AWF", "LF"]


def is_stochastic(vecs: dict[int, np.ndarray]) -> bool:
    if 0 not in vecs or 1 not in vecs or vecs[0] is None or vecs[1] is None:
        return False
    return float(np.mean(vecs[0] != vecs[1])) >= STOCH_DIFF


def agree(a: np.ndarray, b: np.ndarray, mask: np.ndarray | None = None) -> float:
    """Share of identical decisions; an error code on either side counts as a disagreement."""
    eq = (a == b) & (a != ERR) & (b != ERR)
    if mask is not None:
        eq = eq[mask]
        return float(eq.mean()) if eq.size else float("nan")
    return float(eq.mean())


def A(prog: dict[int, np.ndarray], ref: dict[int, np.ndarray], ref_stochastic: bool = False,
      mask: np.ndarray | None = None) -> float:
    vals = []
    for s, v in sorted(prog.items()):
        if v is None:
            continue
        r = ref.get(s) if ref_stochastic else ref.get(0)
        if r is None:
            r = ref.get(0)
        vals.append(agree(v, r, mask))
    return float(np.mean(vals)) if vals else float("nan")


# ---------------------------------------------------------------------------------------------- RF matcher
def norm_ranks(dec: np.ndarray, opened: list[list[int]]) -> np.ndarray:
    """Normalised rank of the chosen capacity among the open capacities:
    (#open capacities below the chosen one + 0.5 * #other open capacities equal to it) / (n_open - 1).
    An unused bin (or an error code) has every open capacity below it and no equal one, giving n_open/(n_open-1) > 1."""
    out = np.empty(len(opened))
    for j, (c, op) in enumerate(zip(dec.tolist(), opened)):
        o = np.asarray(op)
        below = int((o < c).sum())
        eq = int((o == c).sum())
        other_eq = eq - 1 if eq > 0 else 0
        out[j] = (below + 0.5 * other_eq) / (len(o) - 1)
    return out


def ks_2samp_stat(x: np.ndarray, y: np.ndarray) -> float:
    x = np.sort(np.asarray(x, float))
    y = np.sort(np.asarray(y, float))
    allv = np.concatenate([x, y])
    cx = np.searchsorted(x, allv, side="right") / len(x)
    cy = np.searchsorted(y, allv, side="right") / len(y)
    return float(np.max(np.abs(cx - cy)))


def seed_to_seed(vecs: dict[int, np.ndarray], idx: np.ndarray) -> float:
    ks = sorted(s for s, v in vecs.items() if v is not None)
    vals = [float(np.mean(vecs[a][idx] == vecs[b][idx])) for i, a in enumerate(ks) for b in ks[i + 1:]]
    return float(np.mean(vals)) if vals else 1.0


class RFMatcher:
    """Matcher on uniform probe states with n_open >= 2 under harness seeds 0-3 (committed rule, deviation D4)."""

    def __init__(self, states: list[list], meta: list[dict], rf_ref: dict[int, np.ndarray]):
        self.idx = np.array([i for i, m in enumerate(meta)
                             if m["source"].startswith("uniform") and len(states[i][1]) >= 2], dtype=int)
        self.opened = [list(states[i][1]) for i in self.idx]
        self.caps = np.array([states[i][3] for i in self.idx])
        self.ref = rf_ref
        self.ref_ranks = np.concatenate([norm_ranks(rf_ref[s][self.idx], self.opened) for s in sorted(rf_ref)])
        self.ref_s2s = seed_to_seed(rf_ref, self.idx)

    def stats(self, vecs: dict[int, np.ndarray]) -> dict[str, Any]:
        ks_ = sorted(s for s, v in vecs.items() if v is not None)
        if not ks_:
            return {"match": False, "reason": "no vectors"}
        used = np.concatenate([(vecs[s][self.idx] < self.caps) for s in ks_])
        ranks = np.concatenate([norm_ranks(vecs[s][self.idx], self.opened) for s in ks_])
        used_share = float(used.mean())
        ks = ks_2samp_stat(ranks, self.ref_ranks)
        s2s = seed_to_seed(vecs, self.idx)
        c1, c2, c3 = used_share >= RF_USED_MIN, ks <= RF_KS_MAX, s2s <= self.ref_s2s + RF_S2S_MARGIN
        return {"match": bool(c1 and c2 and c3), "used_share": used_share, "ks": ks, "seed_to_seed": s2s,
                "rf_ref_seed_to_seed": self.ref_s2s, "crit_i": bool(c1), "crit_ii": bool(c2), "crit_iii": bool(c3),
                "n_pairs": int(len(ranks)), "seeds": ks_}


# ---------------------------------------------------------------------------------------------- class rule
def classify(prog: dict[int, np.ndarray], refs: dict[str, dict[int, np.ndarray]], matcher: RFMatcher | None,
             stochastic: bool, threshold: float = CLASS_THRESHOLD, mask: np.ndarray | None = None) -> dict[str, Any]:
    """class = argmax_c A_c over {BF, FF, WF, AWF, LF} if that maximum >= threshold; else RF if the program is
    STOCHASTIC and matches RF; else 'other'."""
    Ac = {c: A(prog, refs[c], False, mask) for c in DET_RULES}
    Ac["RF"] = A(prog, refs["RF"], True, mask)
    best = max(DET_RULES, key=lambda c: (Ac[c], -DET_RULES.index(c)))
    rf = matcher.stats(prog) if (matcher is not None and stochastic) else None
    if Ac[best] >= threshold:
        cls = best
    elif stochastic and rf is not None and rf["match"]:
        cls = "RF"
    else:
        cls = "other"
    return {"class": cls, "A": Ac, "best_det": best, "rf_match": (rf or {}).get("match", False), "rf_stats": rf}


def mech_compliant(cls_info: dict[str, Any], banned: list[str], valid: bool,
                   threshold: float = CLASS_THRESHOLD) -> bool:
    """VALID, A_c < threshold for every deterministic c in the banned set, and no RF match if RF is banned."""
    if not valid:
        return False
    for c in banned:
        if c == "RF":
            if cls_info.get("rf_match"):
                return False
        elif cls_info["A"][c] >= threshold:
            return False
    return True


def max_agree_banned(cls_info: dict[str, Any], banned: list[str]) -> float | None:
    vals = [cls_info["A"][c] for c in banned if c != "RF"]
    return max(vals) if vals else None
