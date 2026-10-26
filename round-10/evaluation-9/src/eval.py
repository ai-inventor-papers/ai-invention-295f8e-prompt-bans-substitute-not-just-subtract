#!/usr/bin/env python3
"""Stage CLI for the iteration-10 S0 record repair (CPU only, no model calls).

    uv run eval.py setup|controls|0a|0b|0c|0d|0e|0f|0g|0h|0i|0j|edits|figures|ledger|audit|spotcheck|readme|out|all

Every stage writes results/<stage>.json, appends to logs/run.log, updates STATUS.md and rewrites
eval_out_partial.json, so a stall leaves every finished item on disk.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from loguru import logger  # noqa: E402

from io_util import setup_logging  # noqa: E402

ORDER = ["setup", "controls", "0a", "0b", "0c", "0d", "0e", "0f", "0g", "0h", "0i", "0j", "edits", "figures",
         "ledger", "audit", "spotcheck", "readme", "out"]


def run_stage(name: str) -> None:
    setup_logging(name)
    t0 = time.time()
    logger.info(f"start {name}")
    if name == "setup":
        import s_setup
        s_setup.run()
    elif name == "controls":
        import s_controls
        s_controls.run()
    elif name in ("0a", "0b", "0c", "0h"):
        import s_rename
        getattr(s_rename, f"run_{name}")()
    elif name in ("0d", "0e"):
        import s_geometry
        getattr(s_geometry, f"run_{name}")()
    elif name in ("0f", "0g"):
        import s_base
        getattr(s_base, f"run_{name}")()
    elif name in ("0i", "0j"):
        import s_slips
        getattr(s_slips, f"run_{name}")()
    elif name == "edits":
        import apply_lint
        apply_lint.run()
    elif name == "figures":
        import s_figures
        s_figures.run()
    elif name == "ledger":
        import s_ledger
        s_ledger.run()
    elif name == "audit":
        import s_audit
        s_audit.run()
    elif name == "spotcheck":
        import s_spotcheck
        s_spotcheck.run()
    elif name == "readme":
        import s_readme
        s_readme.run()
    elif name == "out":
        pass
    else:
        raise SystemExit(f"unknown stage {name}")
    import s_out
    s_out.write_partial(final=(name == "out"))
    logger.info(f"done {name} in {time.time() - t0:.1f}s")


@logger.catch(reraise=True)
def main() -> None:
    args = sys.argv[1:] or ["all"]
    stages = ORDER if args == ["all"] else args
    for s in stages:
        run_stage(s)


if __name__ == "__main__":
    main()
