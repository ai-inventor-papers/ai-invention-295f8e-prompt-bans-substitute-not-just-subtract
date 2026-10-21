#!/usr/bin/env python3
"""Descriptive SCREEN VIEW (plan section 11, 'panel + screen view'; NOT part of the frozen analysis): beta for the 15
iteration-4 screen tasks from the iteration-5 Step-1 artifact's base repertoire (read for beta only; snapshotted to
inputs/exp24_base_repertoire_snapshot.json with its sha256 -- it was not yet in that artifact's commit chain when read),
against E for the same tasks from iteration 4 (vendor/exp22/escape.json: ban unit, FP8 W8A8 engine, 40 directions on the
movable tasks, 8 on the others). Cross-engine and cross-unit: descriptive only."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "analysis"))

from a1a2 import perm_p  # noqa: E402
from cfg5 import RESULTS_DIR, utc_now, write_json  # noqa: E402

SRC = Path(os.environ.get("AII_STEP1_BASE_REPERTOIRE", str(ROOT / "inputs" / "exp24_base_repertoire_snapshot.json")))
SNAP = ROOT / "inputs" / "exp24_base_repertoire_snapshot.json"


def main() -> None:
    if SRC.exists() and SRC.resolve() != SNAP.resolve():
        shutil.copy2(SRC, SNAP)
    if not SNAP.exists():
        write_json(RESULTS_DIR / "screen_view.json", {"utc": utc_now(), "status": "Step-1 base repertoire not on disk"})
        return
    br = json.loads(SNAP.read_text())["per_task"]
    esc = json.loads((ROOT / "vendor" / "exp22" / "escape.json").read_text())
    rows = []
    for t, v in br.items():
        if t not in esc or v.get("beta") is None:
            continue
        E = esc[t]["E_t"]
        e = [E[a]["E_t"] for a in ("1.0", "2.0") if a in E and E[a].get("E_t") is not None]
        if not e:
            continue
        rows.append({"task": t, "beta": v["beta"], "beta_basis": v.get("beta_basis"), "stratum": v.get("stratum"),
                     "E_iter4": sum(e) / len(e), "E_iter4_by_alpha": {a: E[a]["E_t"] for a in E}})
    out = {"utc": utc_now(), "source_beta": "iteration-5 Step-1 artifact (gen_art_experiment_24) results/base_repertoire.json",
           "source_beta_sha256": hashlib.sha256(SNAP.read_bytes()).hexdigest(),
           "source_E": "iteration-4 gen_art_experiment_22 results/escape.json (ban unit, FP8, cross-engine)",
           "flags": ["beta file not in the Step-1 commit chain at read time", "E from iteration 4: ban unit, FP8",
                     "descriptive only"],
           "n": len(rows), "rows": rows,
           "spearman": perm_p([r["beta"] for r in rows], [r["E_iter4"] for r in rows]) if len(rows) >= 3 else None}
    write_json(RESULTS_DIR / "screen_view.json", out)
    print({k: v for k, v in out.items() if k != "rows"})


if __name__ == "__main__":
    main()
