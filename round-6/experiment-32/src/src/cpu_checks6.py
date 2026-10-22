#!/usr/bin/env python3
"""CPU checks (plan testing T1-T4, T6, T7, G5 and the seed-disjointness assertion of plan 0.5):
T1 every new-unit spec passes the banned-word audit and a planted-ban positive control is caught;
T2-T4 from the unit build reports (references pass at <= 0.25 x limit, mutants fail, excluded methods exceed the
limit, two oracles agree, labellers 100% on references, probes run);
T6 units.json / landing_events.json validate against schema/iter6_landing_v1.json;
T7 the commit chain verifies (audit/commit_order.py result);
G5 PN / GTN seeds are distinct per sample, and every new seed (ESC, PN, GTN) is disjoint from the seeds used in
iterations 4-5 (directions/rand_<seed>.npy names of exp19, exp20, exp22, exp25, exp26, exp28 and their per-sample
direction seeds)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg5 import NEW_UNITS, RAW, RESULTS_DIR, ROOT, UNITS_DIR, read_json, read_jsonl, utc_now, write_json  # noqa: E402

ITER = ROOT.parents[2]


def old_seeds() -> set[int]:
    out = set()
    for it, ex in (("round-4", "19"), ("round-4", "20"), ("round-4", "22"), ("round-5", "25"), ("round-5", "26"),
                   ("round-5", "28")):
        base = ITER / it / "." / f"gen_art_experiment_{ex}"
        for d in base.rglob("rand_*.npy"):
            m = re.match(r"rand_(\d+)\.npy", d.name)
            if m:
                out.add(int(m.group(1)))
        for f in list((base / "data").glob("samples*.jsonl"))[:2] if (base / "data").exists() else []:
            try:
                with open(f) as fh:
                    for line in fh:
                        if '"direction_seed"' in line:
                            m = re.search(r'"direction_seed":\s*(\d+)', line)
                            if m:
                                out.add(int(m.group(1)))
            except OSError:
                pass
    return out


def main() -> None:
    from units_spec import grep_banned, spec_text
    res: dict = {"utc": utc_now()}
    t1 = {}
    for u in NEW_UNITS:
        br = UNITS_DIR / u / "build_report.json"
        if not br.exists():
            continue
        planted = grep_banned(u, "Do not use a stack or two pointers for this task.\n\n" + spec_text(u))
        t1[u] = {"spec_hits": grep_banned(u, spec_text(u)), "planted_ban_caught": bool(planted)}
    res["T1"] = t1
    t24 = {}
    for u in NEW_UNITS:
        br = UNITS_DIR / u / "build_report.json"
        if br.exists():
            b = read_json(br)
            t24[u] = {"stage_i": b["stage_i"], "references_pass_all": b["references_pass_all"],
                      "slow_refs": {k: v for k, v in b["references_slow_cases"].items() if v},
                      "mutants_fail": all(v["fails"] for v in b["mutants"].values()),
                      "excluded_fail": all(v["fails_stress"] for v in b["excluded_by_limit"].values()),
                      "oracle_disagreements": b["oracle_disagreements"],
                      "labellers_on_references_ok": all(v["ok"] for v in b["labellers_on_references"].values()),
                      "probes_run": b["probes_run"]}
    res["T2_T4"] = t24
    try:
        import jsonschema
        sch = read_json(ROOT / "schema" / "iter6_landing_v1.json")
        ev = read_json(ROOT / "landing_events.json")
        un = read_json(ROOT / "units.json")
        errs = []
        for e in ev["events"]:
            try:
                jsonschema.validate(e, sch["definitions"]["event"])
            except jsonschema.ValidationError as x:
                errs.append(str(x.message)[:200])
        for u in un["units"]:
            try:
                jsonschema.validate(u, sch["definitions"]["unit"])
            except jsonschema.ValidationError as x:
                errs.append(str(x.message)[:200])
        res["T6_schema"] = {"n_events": len(ev["events"]), "n_units": len(un["units"]), "errors": errs[:20]}
    except FileNotFoundError as e:
        res["T6_schema"] = {"error": str(e)}
    co = RESULTS_DIR / "commit_order.json"
    res["T7_chain"] = read_json(co) if co.exists() else None
    raw = read_jsonl(RAW)
    pn = [r["direction_seed"] for r in raw if r.get("family") in ("PN", "GTN")]
    esc = sorted({r["direction_seed"] for r in raw if r.get("family") == "ESC"})
    old = old_seeds()
    new = set(pn) | set(esc)
    res["G5_seeds"] = {"n_pn_gtn_rows": len(pn), "n_distinct_pn_gtn": len(set(pn)),
                       "pn_gtn_distinct_per_sample": len(pn) == len(set(pn)), "n_esc_dirs": len(esc),
                       "n_old_seeds": len(old), "collisions_with_old": sorted(new & old)[:20],
                       "disjoint": not (new & old)}
    write_json(RESULTS_DIR / "tests_cpu.json", res)
    print(json.dumps({k: (v if k != "T2_T4" else {u: x["stage_i"] for u, x in v.items()}) for k, v in res.items()
                      if k != "T7_chain"}, indent=1)[:3000])


if __name__ == "__main__":
    main()
