#!/usr/bin/env python3
"""E3 analysis (exploratory): the S1 2x2 and the S2 profile tests re-run with the committed analysis functions on
(a) T10 fresh slots k 10-19 (an internal replication on 50 slots never used by S1/S2), (b) T10 pooled k 0-19 (N 100),
and (c) the T03 2x2 at alpha 2 (k 0-9; D1_a2 from S3). Writes results/e3_replicate.json.

usage: .venv/bin/python src/extensions_k.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

import k_cfg as K  # noqa: E402
import analysis_k as A  # noqa: E402

K_FRESH = list(range(10, 20))
K_ALL = list(range(20))


def profile_tests(rows: list[dict[str, Any]], task: str, ks: list[int]) -> dict[str, Any]:
    arms = {"D1": "D1_a2", "PTOP": "PTOP_a2", "PREST": "PREST_a2", "PSHUF": "PSHUF_a2", "D5": "D5_a2"}
    cells = {k: A.cell(rows, task, a, ks) for k, a in arms.items()}
    out: dict[str, Any] = {"cells": {k: A.describe(c) for k, c in cells.items() if c}}
    for name, (x, y) in {"PTOP_vs_PREST": ("PTOP", "PREST"), "D1_vs_PSHUF": ("D1", "PSHUF"),
                         "D1_vs_PTOP": ("D1", "PTOP")}.items():
        cx, cy = cells[x], cells[y]
        common = sorted(set(cx) & set(cy))
        if len(common) >= 10:
            t = A.mcnemar_exact([cx[s]["Y"] for s in common], [cy[s]["Y"] for s in common])
            t.update({"n": len(common), "share_x": sum(cx[s]["Y"] for s in common) / len(common),
                      "share_y": sum(cy[s]["Y"] for s in common) / len(common)})
            out[name] = t
    return out


@logger.catch(reraise=True)
def main() -> None:
    K.setup_logging("extensions_k")
    rows = A.load_joined()
    res: dict[str, Any] = {"note": "exploratory (E3), not pre-registered; committed before its first row"}
    for label, task, ks in (("T10_fresh_k10_19", "T10", K_FRESH), ("T10_pooled_k0_19", "T10", K_ALL),
                            ("T03_k0_9", "T03", K.K10)):
        r: dict[str, Any] = {}
        for key in ("Y", "A"):
            r[f"2x2|{key}"] = A.s1_table(rows, task, 2.0, key, ks)
            r[f"2x2|{key}"]["decision_rule_applied"] = A.decision(r[f"2x2|{key}"])
        r["twin"] = A.describe(A.cell(rows, task, "TWIN", ks))
        if task == "T10":
            r["profiles"] = profile_tests(rows, task, ks)
        else:
            r["cells"] = {d: A.describe(A.cell(rows, task, f"{d}_a2", ks)) for d in ("D1", "D2", "D3", "D4")}
        res[label] = r
    K.write_json(K.RESULTS / "e3_replicate.json", res)
    for label in ("T10_fresh_k10_19", "T10_pooled_k0_19", "T03_k0_9"):
        t = res[label]["2x2|Y"]
        if not t.get("incomplete"):
            logger.info(f"{label}: shares {t['shares']} RD_unit {t['RD_unit']:.3f} {t['RD_unit_ci95']} RD_seed "
                        f"{t['RD_seed']:.3f} {t['RD_seed_ci95']} INT {t['RD_int']:.3f} -> {t['decision_rule_applied']}")


if __name__ == "__main__":
    main()
