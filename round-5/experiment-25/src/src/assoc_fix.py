#!/usr/bin/env python3
"""POST HOC correction of the association rival (deviation D-assoc-mapping).

Bug: unit_commit.map_assoc took the EARLIEST catalogue mention in each answer, but every answer restates the question
('The standard alternative to <default> for this task is ...'), so all 20 answers of every unit mapped to the default
and the committed survivor counts are all 0 (the committed association forecast was therefore uniform).
Fix (deterministic, on the same 20 answers per unit, all sampled before the unit's commitment): map each answer to the
earliest mention of a NON-default catalogue mode (display name or alias); answers naming no survivor stay unmapped.
The committed prediction files are left untouched; the corrected counts and the A2 analysis recomputed with them (frozen
analysis_a1a2.a2_analysis) are written beside them: results/assoc_corrected.json, results/a2_assoc_corrected.json.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg5 import NEW_UNITS, PRED, RAW_DIR, RESERVE_UNITS, RESULTS, read_json, read_jsonl, utc_now, write_json  # noqa
from specs5 import SPECS  # noqa: E402


def map_survivor(text: str, u: str, default: str) -> str | None:
    low = text.lower()
    sp = SPECS[u]
    display = {m: d for m, d, _ in sp["catalogue"]}
    best, pos = None, 10 ** 9
    for m, al in sp["aliases"].items():
        if m == default:
            continue
        for a in [display[m]] + al:
            mm = re.search(rf"(?<![a-z]){re.escape(a.lower())}(?![a-z])", low)
            if mm and mm.start() < pos:
                best, pos = m, mm.start()
    return best


def main() -> None:
    import analysis_a1a2 as A

    out = {"utc": utc_now(), "label": "POST HOC (deviation D-assoc-mapping)", "units": {}}
    corrected = {}
    for u in NEW_UNITS + RESERVE_UNITS:
        p = PRED / f"unit_{u}.json"
        if not p.exists():
            continue
        pr = read_json(p)
        if pr.get("status") != "OK":
            continue
        d = pr["default"]
        rows = [r for r in read_jsonl(RAW_DIR / f"{u}.jsonl") if r["arm"] == "ASSOC"]
        commit_utc = pr.get("committed_utc")
        before = all(r["utc"] < commit_utc for r in rows) if commit_utc else None
        mapped = [map_survivor(r["text"], u, d) for r in rows]
        surv = [m for m in pr["catalogue"] if m != d]
        counts = {m: sum(1 for x in mapped if x == m) for m in surv}
        top = sorted(counts, key=lambda m: (-counts[m], pr["catalogue"].index(m)))[0] if any(counts.values()) else None
        corrected[u] = counts
        out["units"][u] = {"n_answers": len(rows), "answers_sampled_before_commitment": before,
                           "committed_counts": pr["rivals"].get("assoc_counts"), "corrected_counts": counts,
                           "n_unmapped": sum(1 for x in mapped if x is None), "association_top1": top,
                           "base_r": pr.get("r"), "examples": [r["text"][:160] for r in rows[:3]]}
    write_json(RESULTS / "assoc_corrected.json", out)
    # A2 recomputed with the corrected association counts (frozen a2_analysis; same events as the frozen run)
    for name, a2f in (("primary", "a2.json"), ("with_extension", "a2_with_extension.json")):
        a2 = read_json(RESULTS / a2f)
        units_ev = [e["unit"] for e in a2["events"]]
        evs = []
        for u in units_ev:
            pr = read_json(PRED / f"unit_{u}.json")
            d, cat = pr["default"], pr["catalogue"]
            rows = A.labels(u)
            esc = A.rows_of(rows, prefix="ESC_", model="instruct")
            oc = A.unit_outcome(u, d, cat)
            surv = [m for m in cat if m != d]
            realised = []
            for c in oc["escape"]["cells"]:
                if c["confirmed"]:
                    sel = [r for r in esc if int(r["direction_seed"]) == c["seed"] and
                           abs(float(r["alpha"]) - c["alpha"]) < 1e-9 and int(r["slot"]) in range(6)]
                    realised += [r["label"] for r in sel if r.get("passed") and r["label"] in surv]
            pn_real = [r["label"] for r in rows if r["arm"].startswith("PN_a") and r.get("passed") and r["label"] in surv]
            bcc = pr["base_chat"]["comp_correct"]
            evs.append({"unit": u, "r": pr["r"], "L": oc["landing"], "K": len(cat), "survivors": surv,
                        "realised": realised, "realised_pn": pn_real, "base_counts": {s: bcc.get(s, 0) for s in surv},
                        "assoc_counts": corrected[u], "prox_dist": pr["rivals"].get("prox_dist")})
        res = A.a2_analysis(evs)
        res["label"] = "POST HOC: A2 with the corrected association mapping (D-assoc-mapping)"
        res["association_top1_hits"] = sum(1 for u in units_ev if out["units"][u]["association_top1"] ==
                                           next(e["L"] for e in evs if e["unit"] == u))
        write_json(RESULTS / f"a2_assoc_corrected{'' if name == 'primary' else '_with_extension'}.json", res)
        print(name, json.dumps({k: res[k] for k in ("n_events", "hits", "association_top1_hits")}),
              json.dumps([(e["unit"], {k: round(v, 3) if v is not None else None for k, v in e["log_scores"].items()})
                          for e in res["events"]]),
              "base-assoc", res["base_minus_assoc"]["mean"], res["base_minus_assoc"].get("p_two_sided"))
    print(json.dumps({u: (v["association_top1"], v["base_r"], v["corrected_counts"], v["answers_sampled_before_commitment"])
                      for u, v in out["units"].items()}, indent=0))


if __name__ == "__main__":
    main()
