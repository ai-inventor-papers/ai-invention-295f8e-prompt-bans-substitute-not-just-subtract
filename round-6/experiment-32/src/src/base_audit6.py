#!/usr/bin/env python3
"""Stage 4.1 base audit: 15 randomly drawn VALID base programs per unit (chat and plain mixed, seed 20261021) are
labelled blind by two judge families (gemini-2.5-flash, gpt-4.1-mini; deepseek on disagreement); agreement of the
frozen labeller's final label with the adjudicated label is reported; AUDIT_WEAK if < 0.85."""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

from cfg5 import RESULTS_DIR, read_json, setup_logging, utc_now, write_json  # noqa: E402
from judge5 import adjudicate_many, spent  # noqa: E402
from labels6 import all_final  # noqa: E402


def main(units: list[str]) -> None:
    setup_logging("base_audit6")
    p = RESULTS_DIR / "base_audit.json"
    out = read_json(p) if p.exists() else {}
    for u in units:
        if u in out and "agreement_correct_only" in out[u]:
            continue
        rows = [r for r in all_final({u}) if r["model_tag"] == "base" and r["arm"] in ("BASE", "PLAIN")
                and r["label"] not in ("invalid",) and r.get("code")]
        rng = random.Random(20261021)
        pick = rng.sample(rows, min(15, len(rows)))
        adj = adjudicate_many([(r["key"], u, r["code"]) for r in pick], f"base_audit:{u}")
        items = []
        for r, a in zip(pick, adj):
            items.append({"key": r["key"], "labeller": r["label"], "adjudicated": a["label"], "how": a["how"],
                          "judge_a": a["judge_a"], "judge_b": a["judge_b"], "passed": r["passed"]})
        ok = [i for i in items if i["adjudicated"] is not None]
        agr = sum(i["labeller"] == i["adjudicated"] for i in ok) / max(len(ok), 1)
        okc = [i for i in ok if i["passed"]]
        agc = sum(i["labeller"] == i["adjudicated"] for i in okc) / len(okc) if okc else None
        out[u] = {"utc": utc_now(), "n": len(items), "n_adjudicated": len(ok), "agreement": agr,
                  "n_correct": len(okc), "agreement_correct_only": agc,
                  "flag_AUDIT_WEAK": agr < 0.85, "items": items}
        write_json(p, out)
        logger.info(f"base audit {u}: agreement {agr:.2f} over {len(ok)}; spent {spent():.3f}")


if __name__ == "__main__":
    main(sys.argv[1].split(","))
