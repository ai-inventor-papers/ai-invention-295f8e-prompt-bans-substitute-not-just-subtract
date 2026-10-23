#!/usr/bin/env python3
"""COMMIT #0: predictions/protocol.json (units, nodes, arms, thresholds, measures, drop order, code hashes)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg8 import (ADAPT, DOSE_GRID, EDT, GLOBAL_ARMS, K_HR, K_MAP, MINP, N_BOOT, PRED_DIR, SRC, THRESH,  # noqa: E402
                  TOP_P_GLOBAL, TOPK_DOSE, UNITS, sha256_file, slot_ukey, utc_now, write_json)
import units8 as U8  # noqa: E402

ARMS = {
    "A0": "twin: T = 1 everywhere (Stage 0)",
    "A1": f"global T {GLOBAL_ARMS['A1']} + top-p {TOP_P_GLOBAL} at every position",
    "A2": f"global T {GLOBAL_ARMS['A2']} + top-p {TOP_P_GLOBAL}",
    "A3g": f"global T {GLOBAL_ARMS['A3g']} + top-p {TOP_P_GLOBAL}",
    "A4": f"min-p {MINP['min_p']} on the T = 1 probabilities, then T {MINP['T']} over the survivors (dropped first)",
    "A5": f"EDT-style: T {EDT['T_hi']} where the T = 1 entropy > q90_u (twin, steps 1-64), T = 1 elsewhere",
    "A6": f"AdapT-style: T {ADAPT['T_hi']} at the first non-whitespace token after every line ending in ':'",
    "A7": "entropy-max at matched dose: T = d2, top-20 at the slot's highest-entropy twin step in 1..64",
    "A8": "random window at matched dose: T = d2, top-20 at a committed random step in 1..64 (width 2 on T10)",
    "A9": "fork-dosed d1: T = d1, top-20 at the decision index only (T10: second dose at index 11 if non-committal)",
    "A10": "fork-dosed d2",
    "A11": "class-uniform forcing: the committed most probable committal token(s) of a uniformly drawn class",
    "B1": "boundary window: T = T10's d2, top-20 at each of the first 16 body tokens",
}
DROP_ORDER = ["A4 min-p", "A12/A13 plan noise, base intent; A6 AdapT", "HR beyond T10 and B3", "G's A9 and A7/A8",
              "boundary arm on T03", "A3 (rain water) entirely", "A2 cut to N = 30"]
NEVER_DROP = ["commit #1", "T10, grid (T1 or G), B3 with A1, A3g, A5", "A9, A10, A11 on T10",
              "G's A10 with the ' queue' prediction", "A7 and A8 on T10", "HR on T10 and B3", "novelty audit"]


def main() -> None:
    code = {p.name: sha256_file(p) for p in sorted(SRC.glob("*.py"))}
    proto = {
        "name": "iteration 8 claim K1/HR protocol", "utc": utc_now(),
        "units": {u: {**UNITS[u], "slot_keys_example": [list(slot_ukey(u, s)) for s in (0, 10, 49)],
                      "nodes": [{"id": n["id"], "pos": n["pos"], "opening_len": len(n["opening"])}
                                for n in U8.nodes(u)]} for u in UNITS},
        "second_node": U8.second_node("T10"), "arms": ARMS, "dose_grid": DOSE_GRID, "top_k_dose": TOPK_DOSE,
        "K_map": K_MAP, "K_hr": K_HR, "n_boot": N_BOOT, "thresholds": THRESH, "drop_order": DROP_ORDER,
        "never_drop": NEVER_DROP,
        "dose_rules": {
            "collapsed": "d1/d2 = smallest grid T whose composed off-default ATTEMPTED share reaches 0.20 / 0.40; if "
                         "the T = 100 maximum is below target: d2 = smallest T reaching 0.95 of it, d1 = half of it",
            "mixed": "d1 = smallest T with predicted minority share >= 0.5 (else the T at the midpoint between the twin "
                     "share and the maximum); d2 = the attainable-maximum rule",
            "boundary": "window arm uses T10's d2"},
        "K1": {"a": "MAE over {d1, d2} x classes <= 0.10 on >= 80% of located units (+ replay MAE, noise ceiling)",
               "b": "collapsed: best of d1/d2 correct-only Hill-1 >= 1.8 at pass cost <= 5 points, comparators "
                    "<= 1.15, paired-bootstrap one-sided 97.5% lower bound > 0 vs each comparator (selection inside "
                    "each of 2,000 replicates); mixed: d1 within 0.10 of target, Hill-1 >= 1.8 on >= 4 of 6 units",
               "c": "twin decision-token entropy < q90_u in >= 90% of samples (T10; T1 or G)",
               "d": "boundary window moves <= 0.10 (untestable by breakage if pass < 0.5)",
               "e": "reversion <= 10% in A9/A10 pooled", "f": "G: |obs - committed pass cost| <= 0.10; A11 draws "
               "' queue' in 0 slots and its pass cost <= A10's",
               "disconfirming": "correct off-default share - twin < 0.10 on both collapsed units under both doses, "
                                "or pass cost > 10 points, or reversion > 30%",
               "primary_p": "IUT: max over validated collapsed units of the one-sided paired-bootstrap p for "
                            "(best fork-dosed Hill - best comparator Hill > 0)"},
        "HR": "count of units with ideas(HR) - ideas(K*) >= 1; predicted >= 3, all known, 0 novel",
        "code_sha256_at_commit0": code,
        "late_commit_note": "COMMIT #0 written after the Stage 0 twins started (reference data, T = 1); every "
                            "threshold and arm definition was fixed in cfg8.py before the twins ran",
    }
    write_json(PRED_DIR / "protocol.json", proto)
    print("protocol written")


if __name__ == "__main__":
    main()
