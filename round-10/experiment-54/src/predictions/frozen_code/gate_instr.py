#!/usr/bin/env python3
"""S5 instrument gate (G-INSTR), run before any ban row: (a) self-agreement across two runs with the same harness
seeds, (b) renamed copies, (c) formulation / tie-break variants including the human-written xlcost_python adapters of
the dependency art_j3Rm_lr2nzR6, (d) planted different rules, (e) the RF matcher on planted random and near-random
rules. Writes results/instrument_gate.json."""
from __future__ import annotations

import time
from typing import Any

import numpy as np
from loguru import logger

import instr
import refs
import sandbox
from common import RESULTS, read_json, write_json
from corpus import probe_batch

# ---------------------------------------------------------------------------------------------- (b) renamed copies
RENAMED = {
    "BF": '''def priority(item, bins):
    """Score each candidate bin by how little room the item would leave."""
    # leftover room after placing the item; less is better
    leftover_room = bins - item
    return -leftover_room
''',
    "FF": '''def priority(item, bins):
    """Prefer bins in the order they were created."""
    # earlier positions get higher scores
    n_candidates = len(bins)
    return -np.arange(n_candidates)
''',
    "WF": '''def priority(item, bins):
    """Emptiest partly filled bin; fresh bins only as a last resort."""
    spare = (bins - item).astype(float)  # spare room after placement
    is_fresh = bins == bins.max()
    if not is_fresh.all():
        spare[is_fresh] = -1e9  # do not open a new bin while an old one fits
    return spare
''',
    "AWF": '''def priority(item, bins):
    """Runner-up emptiest partly filled bin."""
    occupied = bins < bins.max()  # bins that already hold something
    count = int(occupied.sum())
    if count == 0:
        return np.zeros(len(bins))
    if count == 1:
        return occupied.astype(float)
    runner_up = np.sort(bins[occupied])[-2]  # second-largest remaining room
    return np.where(occupied & (bins == runner_up), 2.0, np.where(occupied, 1.0, 0.0))
''',
    "LF": '''def priority(item, bins):
    """Newest partly filled bin that still fits."""
    occupied = bins < bins.max()
    position = np.arange(len(bins))  # creation order
    return np.where(occupied, position, -1.0)
''',
    "RF": '''def priority(item, bins):
    """Any partly filled bin, uniformly at random."""
    occupied = bins < bins.max()
    noise = np.random.random(len(bins))  # random tie-free scores
    return np.where(occupied, noise, -1.0)
''',
}

# ---------------------------------------------------------------------------------------------- (c) variants
_ONEHOT = "    s = np.zeros(len(bins))\n    s[{j}] = 1.0\n    return s\n"
VARIANTS: dict[str, dict[str, str]] = {
    "BF": {
        "onehot_argmin": "def priority(item, bins):\n    s = np.zeros(len(bins))\n"
                         "    s[np.argmin(bins - item)] = 1.0\n    return s\n",
        "reciprocal": "def priority(item, bins):\n    return 1.0 / (bins - item + 1e-9)\n",
        "exact_fit_bonus": "def priority(item, bins):\n    return np.where(bins == item, 1e6, -(bins - item))\n",
        "python_loop": ("def priority(item, bins):\n    best_j, best_r = 0, None\n    for j in range(len(bins)):\n"
                        "        r = bins[j] - item\n        if best_r is None or r < best_r:\n"
                        "            best_j, best_r = j, r\n" + _ONEHOT.format(j="best_j")),
    },
    "FF": {
        "zeros": "def priority(item, bins):\n    return np.zeros(len(bins))\n",
        "ones": "def priority(item, bins):\n    return np.ones(len(bins))\n",
        "loop_first_index": ("def priority(item, bins):\n    for j in range(len(bins)):\n        if bins[j] >= item:\n"
                             "            s = np.zeros(len(bins))\n            s[j] = 1.0\n            return s\n"
                             "    return np.zeros(len(bins))\n"),
    },
    "WF": {
        "masked_inf": ("def priority(item, bins):\n    used = bins < bins.max()\n    if not used.any():\n"
                       "        return np.zeros(len(bins))\n    return np.where(used, bins - item, -np.inf)\n"),
        "python_loop": ("def priority(item, bins):\n    cap = bins.max()\n    best_j, best_r = -1, -1\n"
                        "    for j in range(len(bins)):\n        if bins[j] < cap and bins[j] - item > best_r:\n"
                        "            best_j, best_r = j, bins[j] - item\n    if best_j < 0:\n"
                        "        best_j = int(np.argmax(bins == cap))\n" + _ONEHOT.format(j="best_j")),
        "argmax_masked": ("def priority(item, bins):\n    used = bins < bins.max()\n    s = np.zeros(len(bins))\n"
                          "    if used.any():\n        rem = np.where(used, bins, -1)\n"
                          "        s[int(np.argmax(rem))] = 1.0\n    else:\n        s[0] = 1.0\n    return s\n"),
    },
    "AWF": {
        "sort_based": ("def priority(item, bins):\n    used = bins < bins.max()\n    idx = np.flatnonzero(used)\n"
                       "    s = np.zeros(len(bins))\n    if len(idx) == 0:\n        s[0] = 1.0\n        return s\n"
                       "    if len(idx) == 1:\n        s[idx[0]] = 1.0\n        return s\n"
                       "    order = idx[np.argsort(-bins[idx], kind='stable')]\n    t = bins[order[1]]\n"
                       "    s[int(np.flatnonzero(used & (bins == t))[0])] = 1.0\n    return s\n"),
        "loop_based": ("def priority(item, bins):\n    cap = bins.max()\n    first = second = None\n"
                       "    for r in bins:\n        if r < cap:\n            if first is None or r > first:\n"
                       "                first, second = r, first\n            elif second is None or r > second:\n"
                       "                second = r\n    s = np.zeros(len(bins))\n    if first is None:\n"
                       "        s[0] = 1.0\n        return s\n    target = first if second is None else second\n"
                       "    for j in range(len(bins)):\n        if bins[j] < cap and bins[j] == target:\n"
                       "            s[j] = 1.0\n            return s\n    return s\n"),
        "last_index_tie": ("def priority(item, bins):\n    used = bins < bins.max()\n    idx = np.flatnonzero(used)\n"
                           "    s = np.zeros(len(bins))\n    if len(idx) == 0:\n        s[0] = 1.0\n        return s\n"
                           "    if len(idx) == 1:\n        s[idx[0]] = 1.0\n        return s\n"
                           "    t = np.sort(bins[idx])[-2]\n    s[int(np.flatnonzero(used & (bins == t))[-1])] = 1.0\n"
                           "    return s\n"),
    },
    "LF": {
        "reversed_loop": ("def priority(item, bins):\n    cap = bins.max()\n    for j in range(len(bins) - 1, -1, -1):\n"
                          "        if bins[j] < cap and bins[j] >= item:\n            s = np.zeros(len(bins))\n"
                          "            s[j] = 1.0\n            return s\n    return np.zeros(len(bins))\n"),
        "flatnonzero_last": ("def priority(item, bins):\n    idx = np.flatnonzero(bins < bins.max())\n"
                             "    s = np.zeros(len(bins))\n    s[idx[-1] if len(idx) else 0] = 1.0\n    return s\n"),
        "index_plus_one": ("def priority(item, bins):\n    return np.where(bins < bins.max(), np.arange(len(bins)) + 1.0,"
                           " 0.0)\n"),
    },
}

# Human-written xlcost_python programs from art_j3Rm_lr2nzR6 (full_data_out.json), hand-adapted: the human selection
# loop runs over the partly filled bins (blocks); 'Not Allocated' (no used bin fits) opens the first unused bin.
_HEAD = ("def priority(item, bins):\n    used = bins < bins.max()\n    idx_used = np.flatnonzero(used)\n"
         "    blockSize = [int(b) for b in bins[used]]\n    m = len(blockSize)\n    processSize = [int(item)]\n"
         "    n = 1\n")
_TAIL = ("    s = np.zeros(len(bins))\n    if allocation[0] != -1:\n        s[idx_used[allocation[0]]] = 1.0\n"
         "    else:\n        s[int(np.flatnonzero(~used)[0])] = 1.0\n    return s\n")
HUMAN = {
    "FF:xlcost2196_firstFit": ("FF", _HEAD + (
        "    allocation = [-1] * n\n    for i in range(n):\n        for j in range(m):\n"
        "            if blockSize[j] >= processSize[i]:\n                allocation[i] = j\n"
        "                blockSize[j] -= processSize[i]\n                break\n") + _TAIL, 2196),
    "BF:xlcost9219_bestFit": ("BF", _HEAD + (
        "    allocation = [-1] * n\n    for i in range(n):\n        bestIdx = -1\n        for j in range(m):\n"
        "            if blockSize[j] >= processSize[i]:\n                if bestIdx == -1:\n"
        "                    bestIdx = j\n                elif blockSize[bestIdx] > blockSize[j]:\n"
        "                    bestIdx = j\n        if bestIdx != -1:\n            allocation[i] = bestIdx\n"
        "            blockSize[bestIdx] -= processSize[i]\n") + _TAIL, 9219),
    "WF:xlcost5338_worstFit": ("WF", _HEAD + (
        "    allocation = [-1] * n\n    for i in range(n):\n        wstIdx = -1\n        for j in range(m):\n"
        "            if blockSize[j] >= processSize[i]:\n                if wstIdx == -1:\n"
        "                    wstIdx = j\n                elif blockSize[wstIdx] < blockSize[j]:\n"
        "                    wstIdx = j\n        if wstIdx != -1:\n            allocation[i] = wstIdx\n"
        "            blockSize[wstIdx] -= processSize[i]\n") + _TAIL, 5338),
    "FF:xlcost5342_binpacking_firstFit": ("FF", (
        "def priority(item, bins):\n    used = bins < bins.max()\n    idx_used = np.flatnonzero(used)\n"
        "    weight = [int(item)]\n    res = len(idx_used)\n    bin_rem = [int(b) for b in bins[used]] + [0]\n"
        "    choice = -1\n    for i in range(1):\n        j = 0\n        while (j < res):\n"
        "            if (bin_rem[j] >= weight[i]):\n                bin_rem[j] = bin_rem[j] - weight[i]\n"
        "                choice = j\n                break\n            j += 1\n"
        "    s = np.zeros(len(bins))\n    if choice >= 0:\n        s[idx_used[choice]] = 1.0\n    else:\n"
        "        s[int(np.flatnonzero(~used)[0])] = 1.0\n    return s\n"), 5342),
    "BF:xlcost9220_binpacking_titled_firstFit": ("BF", (
        "def priority(item, bins):\n    used = bins < bins.max()\n    idx_used = np.flatnonzero(used)\n"
        "    c = int(bins.max())\n    weight = [int(item)]\n    res = len(idx_used)\n"
        "    bin_rem = [int(b) for b in bins[used]] + [0]\n    for i in range(1):\n        j = 0\n"
        "        min = c + 1\n        bi = 0\n        for j in range(res):\n"
        "            if (bin_rem[j] >= weight[i] and bin_rem[j] - weight[i] < min):\n                bi = j\n"
        "                min = bin_rem[j] - weight[i]\n    s = np.zeros(len(bins))\n    if min == c + 1:\n"
        "        s[int(np.flatnonzero(~used)[0])] = 1.0\n    else:\n        s[idx_used[bi]] = 1.0\n    return s\n"),
        9220),
}
HUMAN_NOTES = {
    2196: "Program for First Fit algorithm in Memory Management (row 2196; row 3242 is its duplicate)",
    9219: "Program for Best Fit algorithm in Memory Management (row 9219)",
    5338: "Program for Worst Fit algorithm in Memory Management (row 5338)",
    5342: "Bin Packing Problem (Minimize number of used Bins), first fit online (row 5342)",
    9220: "Bin Packing Problem, titled 'first fit' but implements best fit; its decrement sits in the new-bin branch "
          "(a detokenisation bug that does not affect the single-item choice) (row 9220)",
    1427: "Program for Next Fit algorithm in Memory Management (row 1427): NOT expressible (the next-fit pointer is "
          "state that persists across calls)",
}

# ---------------------------------------------------------------------------------------------- (e) stochastic rules
RF_PLANTED = {
    "rf_default_rng_priority": ("def priority(item, bins):\n    rng = np.random.default_rng()\n"
                                "    used = bins < bins.max()\n    r = rng.random(len(bins))\n"
                                "    return np.where(used, r, -1.0)\n"),
    "rf_choice_onehot": ("def priority(item, bins):\n    used = np.flatnonzero(bins < bins.max())\n"
                         "    s = np.zeros(len(bins))\n    if len(used) == 0:\n        s[0] = 1.0\n        return s\n"
                         "    s[int(np.random.choice(used))] = 1.0\n    return s\n"),
    "rf_shuffle_first_used": ("def priority(item, bins):\n    cap = bins.max()\n"
                              "    order = np.random.permutation(len(bins))\n    s = np.zeros(len(bins))\n"
                              "    for j in order:\n        if bins[j] < cap:\n            s[j] = 1.0\n"
                              "            return s\n    s[0] = 1.0\n    return s\n"),
}
NEAR_RF = {
    "eps_greedy_bf_0.1": ("def priority(item, bins):\n    if np.random.random() < 0.1:\n"
                          "        return np.random.random(len(bins))\n    return -(bins - item)\n"),
    "random_two_tightest": ("def priority(item, bins):\n    used = np.flatnonzero(bins < bins.max())\n"
                            "    s = np.zeros(len(bins))\n    if len(used) == 0:\n        s[0] = 1.0\n        return s\n"
                            "    order = used[np.argsort(bins[used] - item, kind='stable')]\n"
                            "    pick = order[np.random.randint(min(2, len(order)))]\n    s[int(pick)] = 1.0\n"
                            "    return s\n"),
    "random_all_valid": "def priority(item, bins):\n    return np.random.random(len(bins))\n",
}
DIFFERENT = ["published:ab-FF(5,24)", "published:ab-WF(1,21)", "funsearch:c12_vec", "funsearch:c14"]


def run_gate(pool: sandbox.EvalPool, probe: str, states: list[list], meta: list[dict],
             corpus_vecs: dict[str, dict[int, np.ndarray]]) -> dict[str, Any]:
    t0 = time.time()
    seeds4 = [0, 1, 2, 3]
    out: dict[str, Any] = {"probe": probe, "n_states": len(states)}
    # references twice (a) under seeds 0-3 (RF needs 0-3; deterministic rules get 0-3 for the matcher test)
    run1 = probe_batch(pool, {c: refs.SRC[c] for c in refs.CATALOGUE}, probe=probe, force_seeds=seeds4)
    run2 = probe_batch(pool, {c: refs.SRC[c] for c in refs.CATALOGUE}, probe=probe, force_seeds=seeds4)
    R = {c: run1[c]["vecs"] for c in refs.CATALOGUE}
    a_res = {}
    for c in refs.CATALOGUE:
        same = all(np.array_equal(run1[c]["vecs"][s], run2[c]["vecs"][s]) for s in seeds4)
        a_res[c] = {"identical_across_runs": bool(same), "stochastic": bool(instr.is_stochastic(R[c])),
                    "err_share": run1[c]["err_share"]}
    # RF must differ under different seeds (U4)
    a_res["RF"]["differs_across_seeds"] = float(np.mean(R["RF"][0] != R["RF"][1]))
    out["a_self_agreement"] = a_res
    a_ok = all(v["identical_across_runs"] for v in a_res.values()) and \
        not any(a_res[c]["stochastic"] for c in refs.DETERMINISTIC) and a_res["RF"]["stochastic"]
    matcher = instr.RFMatcher(states, meta, R["RF"])
    # (b) renamed copies
    rb = probe_batch(pool, RENAMED, probe=probe, force_seeds=seeds4)
    b_res = {}
    for c, r in rb.items():
        stoch = c == "RF"
        b_res[c] = {"A_own": instr.A(r["vecs"], R[c], stoch), "class": instr.classify(
            r["vecs"], R, matcher, instr.is_stochastic(r["vecs"]))["class"]}
    b_ok = all(abs(v["A_own"] - 1.0) < 1e-12 and v["class"] == c for c, v in b_res.items())
    out["b_renamed"] = b_res
    # (c) variants + human adapters
    codes = {f"{c}:{k}": v for c, d in VARIANTS.items() for k, v in d.items()}
    codes.update({k: v[1] for k, v in HUMAN.items()})
    rc = probe_batch(pool, codes, probe=probe)
    c_res: dict[str, Any] = {}
    for name, r in rc.items():
        c = name.split(":")[0]
        info = instr.classify(r["vecs"], R, matcher, r["stochastic"])
        c_res[name] = {"rule": c, "A_own": info["A"][c], "class": info["class"], "stochastic": r["stochastic"],
                       "err_share": r["err_share"], "human": name in HUMAN,
                       "xlcost_row": HUMAN[name][2] if name in HUMAN else None}
    per_rule = {c: sum(1 for v in c_res.values() if v["rule"] == c and v["A_own"] >= instr.CLASS_THRESHOLD)
                for c in refs.DETERMINISTIC}
    c_ok = all(v["A_own"] >= instr.CLASS_THRESHOLD and v["class"] == v["rule"] for v in c_res.values()) and \
        all(n >= 3 for n in per_rule.values())
    out["c_variants"] = c_res
    out["c_variants_per_rule_passing"] = per_rule
    out["human_notes"] = {str(k): v for k, v in HUMAN_NOTES.items()}
    # (d) catalogue pairs + planted different rules
    pairs = {}
    for i, c1 in enumerate(refs.DETERMINISTIC):
        for c2 in refs.DETERMINISTIC[i + 1:]:
            pairs[f"{c1}~{c2}"] = instr.A(R[c1], R[c2])
    diff = {}
    for name in DIFFERENT:
        v = corpus_vecs[name]
        info = instr.classify(v, R, matcher, instr.is_stochastic(v))
        diff[name] = {"A": info["A"], "max_catalogue": max(info["A"][c] for c in refs.DETERMINISTIC),
                      "class": info["class"]}
    max_pair = max(pairs.values())
    d_ok = max_pair < instr.CLASS_THRESHOLD and all(v["max_catalogue"] < instr.CLASS_THRESHOLD and
                                                     v["class"] == "other" for v in diff.values())
    out["d_catalogue_pairs"] = pairs
    out["d_planted_different"] = diff
    out["min_margin"] = instr.CLASS_THRESHOLD - max_pair
    # informative-only view of the pairs (sensitivity)
    inf = np.array([m["informative"] for m in meta])
    out["d_catalogue_pairs_informative"] = {k: instr.A(R[k.split("~")[0]], R[k.split("~")[1]], False, inf)
                                            for k in pairs}
    # (e) RF matcher
    rr = probe_batch(pool, {**RF_PLANTED, **NEAR_RF}, probe=probe, force_seeds=seeds4)
    e_res = {}
    for name, r in rr.items():
        st = matcher.stats(r["vecs"])
        e_res[name] = {"should_match": name in RF_PLANTED, **st}
    for c in refs.DETERMINISTIC:
        st = matcher.stats(R[c])
        e_res[f"det:{c}"] = {"should_match": False, **st}
    st_rf = matcher.stats(run2["RF"]["vecs"])
    e_res["ref:RF(run2)"] = {"should_match": True, **st_rf}
    e_ok = all(v["match"] == v["should_match"] for v in e_res.values())
    out["e_rf_matcher"] = e_res
    out["rf_ref_seed_to_seed"] = matcher.ref_s2s
    out["rf_matcher_n_states"] = int(len(matcher.idx))
    out["parts"] = {"a": bool(a_ok), "b": bool(b_ok), "c": bool(c_ok), "d": bool(d_ok), "e": bool(e_ok)}
    out["passed"] = bool(a_ok and b_ok and c_ok and d_ok and e_ok)
    out["seconds"] = round(time.time() - t0, 1)
    out["reference_vectors"] = {c: {str(s): R[c][s].tolist() for s in seeds4} for c in refs.CATALOGUE}
    logger.info(f"G-INSTR on {probe}: parts {out['parts']} -> {'PASS' if out['passed'] else 'FAIL'}; "
                f"min margin {out['min_margin']:.3f}")
    return out


def save(res: dict[str, Any], name: str = "instrument_gate.json") -> None:
    write_json(RESULTS / name, res)


def load_reference_vectors(name: str = "instrument_gate.json") -> dict[str, dict[int, np.ndarray]]:
    g = read_json(RESULTS / name)
    return {c: {int(s): np.array(v, dtype=np.uint16) for s, v in sv.items()}
            for c, sv in g["reference_vectors"].items()}
