#!/usr/bin/env python3
"""Label QA (testing plan): (a) style re-gate: 10 valid nudged programs per unit (ESC/PN/GTN, random, seeded) judged
blind by the two judge families; disagreement of the final label with the judge majority > 20% is flagged;
(b) base-audit summary: agreement of the final labels with each judge on the 15 audited base programs, raw and with
'invalid' and 'other' merged (both are non-catalogue for compositions), and the base runner-up r_u recomputed with the
audited rows relabelled by the judges where both judges agree (flag if r_u would change).
Writes results/label_qa.json."""

from __future__ import annotations

import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cfg6 import EXCLUDE, PRED_DIR, RESULTS_DIR, UNITS_DIR, read_json, write_json  # noqa: E402
from judge6 import JUDGE_A, JUDGE_B, judge_one, spent  # noqa: E402
from labels_view6 import load_final  # noqa: E402


def merge(x):
    return "non_catalogue" if x in ("invalid", "other") else x


def main() -> None:
    labs = load_final()
    units = read_json(ROOT / "units.json")["units"]
    out = {"style_regate": {}, "base_audit": {}}
    for U in units:
        u = U["unit"]
        rng = random.Random(f"style|{u}")
        pool = [l for l in labs if l["unit"] == u and l.get("src") == "hf" and l["family"] in ("ESC", "PN", "GTN")
                and l.get("valid") and l.get("final") not in (None, "disputed")]
        pick = rng.sample(pool, min(10, len(pool)))
        res = []
        for l in pick:
            a = judge_one(JUDGE_A, u, l["code"], f"style_regate:{u}")
            b = judge_one(JUDGE_B, u, l["code"], f"style_regate:{u}")
            maj = a if a == b else None
            res.append({"key": l["key"], "final": l["final"], "judge_a": a, "judge_b": b, "agree_majority":
                        (maj == l["final"]) if maj is not None else None})
        dec = [r for r in res if r["agree_majority"] is not None]
        dis = sum(1 for r in dec if not r["agree_majority"]) / len(dec) if dec else None
        out["style_regate"][u] = {"n": len(res), "n_judges_agree": len(dec), "disagreement": dis,
                                  "flag_gt_20pct": bool(dis is not None and dis > 0.2), "items": res}
        ba = read_json(UNITS_DIR / u / "base_audit.json")
        its = ba["items"]
        rec = read_json(PRED_DIR / "units" / f"{u}.json")
        relabel = {it["key"]: it["judge_a"] for it in its if it["judge_a"] is not None and it["judge_a"] ==
                   it["judge_b"]}
        base = [l for l in labs if l["unit"] == u and l["arm"] in ("BASE", "PLAIN")]
        D, cat = rec["default"], rec["catalogue"]
        nd = [m for m in cat if m != D]

        def runner_up(rows, rel):
            c = Counter((rel.get(l["key"], l["final"])) for l in rows if l.get("passed") and
                        rel.get(l["key"], l["final"]) not in EXCLUDE)
            cand = [(c.get(m, 0), -i, m) for i, m in enumerate(nd)]
            cand.sort(reverse=True)
            return cand[0][2] if cand and cand[0][0] > 0 else None
        ru_with = runner_up(base, relabel)
        out["base_audit"][u] = {
            "n": ba["n"], "agree_final_judge_a": ba["agreement_final_vs_judge_a"],
            "agree_final_judge_b": ba["agreement_final_vs_judge_b"],
            "agree_merged_invalid_other_a": sum(merge(it["final"]) == merge(it["judge_a"]) for it in its) / len(its),
            "agree_merged_invalid_other_b": sum(merge(it["final"]) == merge(it["judge_b"]) for it in its) / len(its),
            "flag_below_0.8": min(ba["agreement_final_vs_judge_a"], ba["agreement_final_vs_judge_b"]) < 0.8,
            "r_u_committed": rec["r_u"], "r_u_with_judge_relabels": ru_with,
            "r_u_changes": ru_with != rec["r_u"]}
    out["judge_spend_running"] = spent()
    write_json(RESULTS_DIR / "label_qa.json", out)
    print({u: (v["disagreement"], v["flag_gt_20pct"]) for u, v in out["style_regate"].items()})
    print({u: (round(v["agree_merged_invalid_other_a"], 2), round(v["agree_merged_invalid_other_b"], 2),
               v["r_u_changes"]) for u, v in out["base_audit"].items()})


if __name__ == "__main__":
    main()
