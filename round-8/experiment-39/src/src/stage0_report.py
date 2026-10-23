#!/usr/bin/env python3
"""Stage 0 report: per-unit twin composition, per-slot label agreement with the source artifact's T = 1 programs at
the same slot streams (engine check, target >= 0.95; differences are kernel sensitivity, every contrast uses this
artifact's own twins), reached-decision share and decision tokens -> results/stage0.json."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg8 import LABELS, RESULTS_DIR, SAMPLES, THRESH, UNITS, read_jsonl, utc_now, write_json  # noqa: E402
import units8 as U8  # noqa: E402


def main() -> None:
    lab = {r["sid"]: r for r in read_jsonl(LABELS)}
    rows = [r for r in read_jsonl(SAMPLES) if r["arm"] == "A0"]
    out = {"utc": utc_now(), "units": {}}
    for u in UNITS:
        tw = {r["slot"]: r for r in rows if r["unit"] == u}
        if not tw:
            continue
        src = U8.source_twin_labels(u)
        both = [s for s in tw if s in src and lab.get(tw[s]["sid"])]
        agree = sum(1 for s in both if lab[tw[s]["sid"]]["label"] == src[s])
        comp = Counter(lab.get(r["sid"], {}).get("label") for r in tw.values())
        out["units"][u] = {"n": len(tw), "composition": dict(comp),
                           "pass_rate": sum(bool(lab.get(r["sid"], {}).get("passed")) for r in tw.values()) / len(tw),
                           "engine_check_n": len(both), "engine_check_agree": agree,
                           "engine_check_rate": agree / len(both) if both else None,
                           "engine_check_pass": (agree / len(both) >= THRESH["engine_agree"]) if both else None,
                           "reached_decision": sum(bool(r.get("reached_decision")) for r in tw.values()) / len(tw),
                           "decision_tokens": dict(Counter(r.get("decision_token_str") for r in tw.values()
                                                           if r.get("reached_decision"))),
                           "mean_new_tokens": sum(r["n_new_tokens"] for r in tw.values()) / len(tw)}
    write_json(RESULTS_DIR / "stage0.json", out)
    for u, v in out["units"].items():
        print(u, v["composition"], "pass", round(v["pass_rate"], 2), "engine", v["engine_check_agree"], "/",
              v["engine_check_n"], "reached", round(v["reached_decision"], 2), v["decision_tokens"])


if __name__ == "__main__":
    main()
