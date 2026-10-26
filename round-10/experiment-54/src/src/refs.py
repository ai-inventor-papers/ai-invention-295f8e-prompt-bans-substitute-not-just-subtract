#!/usr/bin/env python3
"""S2 catalogue references in the FunSearch priority interface, and stateful hand-coded packers (unit test U2).

Capacity is inferred as bins.max(): an unused full bin is always among the valid bins of the pre-allocated harness,
so used = bins < bins.max(). Six textbook rules: best fit (BF), first fit (FF), worst fit (WF), almost-worst fit
(AWF: second-emptiest used bin that fits, by sorted multiset position), last fit (LF: most recently opened used bin
that fits) and random fit (RF: a uniformly random used bin that fits). Every rule opens the first unused bin when no
used bin fits. Next fit and harmonic-k need state the interface does not pass and are not expressible.
"""
from __future__ import annotations

import numpy as np

import bp

CATALOGUE = ["BF", "FF", "WF", "AWF", "LF", "RF"]
DETERMINISTIC = ["BF", "FF", "WF", "AWF", "LF"]
FALLBACK_ORDER = ["BF", "FF", "WF", "AWF", "LF", "RF"]
DISPLAY = {"BF": "Best Fit", "FF": "First Fit", "WF": "Worst Fit", "AWF": "Almost Worst Fit", "LF": "Last Fit",
           "RF": "Random Fit"}
NOT_EXPRESSIBLE = {"NF": "next fit needs the identity of the current open bin (state outside priority(item, bins))",
                   "HARMONIC_K": "harmonic-k needs item-class bookkeeping across calls (state outside the interface)"}

SRC = {
    "BF": bp.SRC_BF,
    "FF": bp.SRC_FF,
    "WF": bp.SRC_WF,
    "AWF": ("def priority(item, bins):\n"
            "    used = bins < bins.max()\n"
            "    nu = int(used.sum())\n"
            "    if nu == 0:\n"
            "        return np.zeros(len(bins))\n"
            "    if nu == 1:\n"
            "        return used.astype(float)\n"
            "    t = np.sort(bins[used])[-2]\n"
            "    return np.where(used & (bins == t), 2.0, np.where(used, 1.0, 0.0))\n"),
    "LF": ("def priority(item, bins):\n"
           "    used = bins < bins.max()\n"
           "    return np.where(used, np.arange(len(bins)), -1.0)\n"),
    "RF": ("def priority(item, bins):\n"
           "    used = bins < bins.max()\n"
           "    r = np.random.random(len(bins))\n"
           "    return np.where(used, r, -1.0)\n"),
}


def prio_awf(item, bins):
    used = bins < bins.max()
    nu = int(used.sum())
    if nu == 0:
        return np.zeros(len(bins))
    if nu == 1:
        return used.astype(float)
    t = np.sort(bins[used])[-2]
    return np.where(used & (bins == t), 2.0, np.where(used, 1.0, 0.0))


def prio_lf(item, bins):
    used = bins < bins.max()
    return np.where(used, np.arange(len(bins)), -1.0)


def prio_rf(item, bins):
    used = bins < bins.max()
    r = np.random.random(len(bins))
    return np.where(used, r, -1.0)


FUNCS = {"BF": bp.prio_bf, "FF": bp.prio_ff, "WF": bp.prio_wf, "AWF": prio_awf, "LF": prio_lf, "RF": prio_rf}


# ---------------------------------------------------------------------------------------------- hand-coded packers
def _place(rem: list[int], s: int, cap: int, choose) -> None:
    cand = [i for i, r in enumerate(rem) if r >= s]
    if not cand:
        rem.append(cap - s)
    else:
        rem[choose(cand, rem)] -= s


def hand_pack(rule: str, items: list[int], cap: int) -> int:
    """Stateful packers over an explicit list of open bins in opening order."""
    rem: list[int] = []
    for s in items:
        if rule == "FF":
            _place(rem, s, cap, lambda c, r: c[0])
        elif rule == "BF":
            _place(rem, s, cap, lambda c, r: min(c, key=lambda i: (r[i], i)))
        elif rule == "WF":
            _place(rem, s, cap, lambda c, r: min(c, key=lambda i: (-r[i], i)))
        elif rule == "AWF":
            def ch(c, r):
                if len(c) == 1:
                    return c[0]
                t = sorted((r[i] for i in c), reverse=True)[1]       # second largest of the multiset
                return next(i for i in c if r[i] == t)
            _place(rem, s, cap, ch)
        elif rule == "LF":
            _place(rem, s, cap, lambda c, r: c[-1])
        else:
            raise ValueError(rule)
    return len(rem)


def unit_test_u2() -> dict:
    """U2: priority-form FF, BF, WF, AWF and LF equal the stateful hand-coded packers bin for bin on SEL-OR,
    P1SRC-OR and one SEL-W instance."""
    out = {}
    insts = bp.load_set("SEL-OR") + bp.load_set("P1SRC-OR") + bp.load_set("SEL-W")[:1]
    for r in DETERMINISTIC:
        a = [bp.pack(x["items"], x["capacity"], FUNCS[r]) for x in insts]
        b = [hand_pack(r, x["items"], x["capacity"]) for x in insts]
        out[r] = {"equal": a == b, "n_instances": len(insts), "priority_bins_first5": a[:5],
                  "hand_bins_first5": b[:5]}
    out["passed"] = all(v["equal"] for v in out.values())
    return out
