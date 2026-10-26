#!/usr/bin/env python3
"""Smoke test of the figure code on a provisional (uncommitted) 32B M-name analysis with a small bootstrap.
Writes into a scratch copy of results (results/_test/), never into the committed result files."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(1, str(ROOT / "vendor" / "exp9"))


def main():
    import stage_analysis as sa
    import stage_figures as sf
    sa.N_BOOT_32B = 12
    (ROOT / "figures" / "coords").mkdir(parents=True, exist_ok=True)
    rec = {"manifolds": {"32b|mname": {"L_star": 31, "curve": {}, "best": 1.0}}}
    r = sa.analyse_manifold("32b", "mname", rec)
    sf.manifold_figs("32b", "mname", json.loads(json.dumps(r, default=str)))
    sf.class_table({"32b|mname": r})
    print("ok", sorted(p.name for p in sf.FIG.glob("*.png")))


if __name__ == "__main__":
    main()
