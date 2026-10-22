#!/usr/bin/env python3
"""Assemble units.json and landing_events.json (schema iter6_landing_v1) from the committed unit predictions and the
final labels, exactly under the frozen definitions (plan 0.9; predictions/analysis_choices.json):
- a CELL is one (arm, alpha, direction) setting; it QUALIFIES iff pass_rate >= 0.8 x twin_pass;
- a LANDING EVENT pools the correct S-labelled programs of one nudge type's qualifying cells (ESC: every cell at
  N 10 or N 30; PN alpha 2 and 4; GTN alpha 2; BINT its single cell, content_free = false); is_event iff >= 5;
- modal landing = argmax over S if it leads the next algorithm by >= 15 points, else NO_CLEAR_LANDING;
- SCREEN events of the iteration-5 B units are rebuilt from the vendored iteration-5 rows (ESC alpha 1/2, PN alpha
  1/2) under the same definitions and scored against the fresh SCREEN forecasts (iter5_origin = true).
Also writes the escape table (every unit x direction x alpha cell), the per-event listing CSV and the list of correct
S-labelled nudged programs used by L2."""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg5 import (ESC_PASS_FRAC, NEW_UNITS, PRED_DIR, RESULTS_DIR, ROOT, SCREEN_B, UNITS_DIR, VENDOR,  # noqa: E402
                  read_json, read_jsonl, setup_logging, utc_now, write_json)
from labels6 import all_final, cell_summary, escape_table, twin_baseline  # noqa: E402
from labels_view import frozen_catalogue  # noqa: E402

MARGIN = 0.15


def modal(counts: dict[str, int], S: list[str]) -> tuple[str | None, float | None]:
    tot = sum(counts.get(a, 0) for a in S)
    if tot == 0:
        return None, None
    srt = sorted(S, key=lambda a: (-counts.get(a, 0), S.index(a)))
    lead = counts.get(srt[0], 0) / tot - (counts.get(srt[1], 0) / tot if len(srt) > 1 else 0.0)
    return (srt[0] if lead >= MARGIN - 1e-12 else "NO_CLEAR_LANDING"), round(100 * lead, 2)


def unit_row(u: str, c: dict[str, Any], tab: dict[str, Any] | None, kind: str, status: str) -> dict[str, Any]:
    ql = c.get("q_lik_block") or {}
    return {
        "unit_id": u, "panel": "II", "unit_kind": kind, "status": status,
        "source_ids": __import__("units_spec").UNITS[u]["source_ids"], "flags": c.get("flags", []),
        "catalogue": c["catalogue"], "K": c["K"], "default": c["default"], "default_share": c.get("default_share"),
        "default_T10_only": c.get("default_T10_only"), "twin": c.get("twin"), "q_tail": c.get("q_tail"),
        "tail_counts": c.get("tail_counts"), "t_u": c.get("t_u"), "tail_empty": c.get("tail_empty"),
        "q_lik": {"score_tok": ql.get("score_tok"), "score_raw": ql.get("score_raw"),
                  "n_programs": ql.get("n_programs"), "unscrubbed_score_tok": ql.get("unscrubbed_score_tok"),
                  "noise_floor": ql.get("noise_floor")},
        "q_lik_softmax": ql.get("q_lik"), "q_lik_raw_softmax": ql.get("q_lik_raw"), "qlik_top1": c.get("qlik_top1"),
        "q_lik_noise_floor": ql.get("noise_floor"), "fork_margin": ql.get("fork_margin"),
        "fork_margin_tok": ql.get("fork_margin_tok"), "base": c.get("base"), "q_base": c.get("q_base"),
        "r_u": c.get("r_u"), "discordant": c.get("discordant"), "support": c.get("support"),
        "low_correct": (c.get("base") or {}).get("low_correct"), "beta": c.get("beta"),
        "m_candidates": c.get("m_candidates"), "forced_compliance": c.get("forced_compliance"),
        "escape": None if tab is None else {str(a): [{"dir_seed": x["dir_seed"], "n": x["n"],
                                                      "pass_rate": x["pass_rate"], "share": x["share"],
                                                      "stage1": x["stage1_pass"], "confirmed": x["confirmed"],
                                                      "p": x["p"]} for x in tab["cells"] if x["alpha"] == a]
                                            for a in sorted({x["alpha"] for x in tab["cells"]})},
        "E_u_by_alpha": None if tab is None else tab["E_by_alpha"], "E_u": None if tab is None else tab["E_u"],
        "association_counts": c.get("association_counts"), "assoc": c.get("assoc"),
        "commit": {"sha256": None, "utc": c.get("utc")}, "enrolment": c.get("enrolment"),
        "priority": (c.get("enrolment") or {}).get("priority"),
        "engine_check_twin": c.get("engine_check_twin"), "base_engine_check": c.get("base_engine_check")}


def cells_of(rows: list[dict], u: str, d: str, tw: dict[str, Any], S: list[str]) -> dict[str, list[dict]]:
    """{nudge: [cell summaries]} for ESC (every direction x alpha), PN (per alpha), GTN (per alpha), BINT."""
    by: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["unit"] == u and r.get("family") in ("ESC", "PN", "GTN", "BINT"):
            by[r["arm"]].append(r)
    out: dict[str, list[dict]] = defaultdict(list)
    for arm, rr in sorted(by.items()):
        fam = rr[0]["family"]
        if fam == "ESC":
            s30 = [r for r in rr if r["slot"] in range(6)]
            use = s30 if len(s30) >= 30 else [r for r in rr if r["slot"] in (0, 1)]
        else:
            use = rr
        cs = cell_summary(use, set(S))
        qual = cs["pass_rate"] is not None and tw["pass"] is not None and \
            cs["pass_rate"] >= ESC_PASS_FRAC * tw["pass"] - 1e-12
        alpha = rr[0].get("alpha")
        if fam == "PN" and alpha not in (2.0, 4.0) or fam == "GTN" and alpha != 2.0:
            continue
        out[fam].append({"cell_id": arm, "alpha": alpha, "dir_seed": rr[0].get("direction_seed") if fam == "ESC"
                         else None, "n": cs["n"], "pass_rate": cs["pass_rate"], "qualifies": bool(qual),
                         "landing_counts": cs["landing_counts"], "other_correct": cs["other_correct"],
                         "share": cs["share"]})
    return out


def event_rows(u: str, c: dict[str, Any], cells: dict[str, list[dict]], set_: str, commit_sha: str | None,
               iter5_origin: bool = False) -> list[dict]:
    out = []
    d = c["default"]
    S = [a for a in c["catalogue"] if a != d]
    for nudge in ("ESC", "PN", "GTN", "BINT"):
        cs = cells.get(nudge, [])
        if not cs:
            continue
        q = [x for x in cs if x["qualifies"]]
        cnt = Counter()
        oth = 0
        for x in q:
            cnt.update(x["landing_counts"])
            oth += x["other_correct"]
        n = sum(cnt.get(a, 0) for a in S)
        m, lead = modal(cnt, S)
        out.append({
            "event_id": f"{u}|{nudge}" + ("|iter5" if iter5_origin else ""), "unit_id": u, "set": set_,
            "nudge": nudge, "content_free": nudge != "BINT", "alphas": sorted({x["alpha"] for x in cs
                                                                               if x["alpha"] is not None}),
            "cells_pooled": [{k: x[k] for k in ("cell_id", "alpha", "dir_seed", "n", "pass_rate", "qualifies")}
                             for x in cs],
            "counts": {a: cnt.get(a, 0) for a in S}, "n_offdefault_correct": n, "other_correct": oth,
            "is_event": n >= 5, "modal_landing": m if n >= 5 else None, "margin_pts": lead,
            "other_dominant": bool(m not in (None, "NO_CLEAR_LANDING") and oth > cnt.get(m, 0)),
            "default": d, "K": c["K"], "catalogue": c["catalogue"], "r_u": c.get("r_u"),
            "qlik_top1": c.get("qlik_top1"), "qlik_raw_top1": (c.get("q_lik_block") or {}).get("qlik_raw_top1"),
            "qlik_unscrubbed_top1": (c.get("q_lik_block") or {}).get("qlik_unscrubbed_top1"),
            "qlik_top2_gap": (c.get("q_lik_block") or {}).get("top2_gap_tok"), "t_u": c.get("t_u"),
            "tail_empty": c.get("tail_empty"), "discordant": c.get("discordant"), "q_base": c.get("q_base"),
            "q_lik": c.get("q_lik"), "q_lik_raw": c.get("q_lik_raw"),
            "q_lik_unscrubbed": (c.get("q_lik_block") or {}).get("q_lik_unscrubbed"), "q_tail": c.get("q_tail"),
            "assoc": c.get("assoc"), "support": c.get("support"), "commit_sha256": commit_sha,
            "iter5_origin": iter5_origin, "n_qualifying_cells": len(q), "n_cells": len(cs)})
    return out


def iter5_B_rows(u: str) -> list[dict]:
    out = []
    for r in read_jsonl(VENDOR / "exp26" / "samples_B_nocode.jsonl"):
        if r["unit"] != u or r["model_tag"] != "instruct":
            continue
        fam = r["arm"].split("_")[0]
        if fam not in ("ESC", "PN", "TWIN"):
            continue
        out.append({"unit": u, "arm": r["arm"], "family": fam, "template": r["template"], "slot": r["slot"],
                    "alpha": r.get("alpha"), "direction_seed": r.get("direction_seed"),
                    "label": r.get("label") or "disputed", "passed": bool(r.get("passed")), "engine": "hf",
                    "model_tag": "instruct"})
    return out


def main() -> None:
    setup_logging("events6")
    from commit5 import entries
    sha = {e["path"]: e["sha256"] for e in entries()}
    units, events, esc_rows, progs = [], [], [], []
    all_u = [u for u in NEW_UNITS if (PRED_DIR / "units" / f"{u}.json").exists()] + \
        [u for u in SCREEN_B if (PRED_DIR / "units" / f"{u}.json").exists()]
    for u in all_u:
        c = read_json(PRED_DIR / "units" / f"{u}.json")
        kind = "new_unit" if u.startswith("II") else "iter5_screen"
        cs = sha.get(f"predictions/units/{u}.json")
        if c["default"] == "NO_DEFAULT":
            row = unit_row(u, {**c, "K": c["K"]}, None, kind, "excluded_no_default")
            row["commit"]["sha256"] = cs
            units.append(row)
            continue
        rows = all_final({u})
        if u.startswith("B") and not any(r["arm"] == "TWIN" and r.get("engine") == "hf" for r in rows):
            from quantities6 import iter5_twin_rows
            rows = rows + iter5_twin_rows(u)
        eng = (c.get("engine_check_twin") or {}).get("pass", True)
        d = c["default"]
        S = [a for a in c["catalogue"] if a != d]
        alphas = (1.0, 2.0, 4.0) if kind == "new_unit" else (4.0,)
        tab = escape_table(rows, u, d, alphas, engine_ok=eng)
        tw = tab["twin"]
        has_nudge = any(r.get("family") in ("ESC", "PN", "GTN") for r in rows if r["unit"] == u)
        status = "enrolled" if has_nudge else "not_enrolled_time"
        row = unit_row(u, c, tab, kind, status)
        row["commit"]["sha256"] = cs
        units.append(row)
        for x in tab["cells"]:
            esc_rows.append({"unit": u, "set": "CONFIRMATION" if kind == "new_unit" else "SCREEN", "cell": x["arm"],
                             "alpha": x["alpha"], "dir_seed": x["dir_seed"], "n": x["n"], "pass_rate": x["pass_rate"],
                             "share": x["share"], "stage1": x["stage1_pass"], "confirmed": x["confirmed"],
                             "p": x["p"], "twin_off": tw["off"], "twin_pass": tw["pass"]})
        cells = cells_of(rows, u, d, tw, S)
        events += event_rows(u, c, cells, "CONFIRMATION" if kind == "new_unit" else "SCREEN", cs)
        for r in rows:
            if r["unit"] == u and r.get("family") in ("ESC", "PN", "GTN", "BINT") and r["passed"] and r["label"] in S:
                progs.append({"unit_id": u, "label": r["label"], "key": r["key"], "family": r["family"],
                              "content_free": r["family"] != "BINT", "set": "CONFIRMATION" if kind == "new_unit"
                              else "SCREEN"})
        if kind == "iter5_screen":
            r5 = iter5_B_rows(u)
            tw5 = twin_baseline(r5 + [], u, d, engine_ok=False)
            by: dict[str, list[dict]] = defaultdict(list)
            for r in r5:
                if r["family"] in ("ESC", "PN"):
                    by[r["arm"]].append(r)
            c5: dict[str, list[dict]] = defaultdict(list)
            for arm, rr in sorted(by.items()):
                fam = rr[0]["family"]
                use = rr
                if fam == "ESC":
                    s30 = [r for r in rr if r["slot"] in range(6)]
                    use = s30 if len(s30) >= 30 else [r for r in rr if r["slot"] in (0, 1)]
                cs5 = cell_summary(use, set(S))
                qual = cs5["pass_rate"] is not None and tw5["pass"] is not None and \
                    cs5["pass_rate"] >= ESC_PASS_FRAC * tw5["pass"] - 1e-12
                c5[fam].append({"cell_id": arm, "alpha": rr[0].get("alpha"), "dir_seed": rr[0].get("direction_seed"),
                                "n": cs5["n"], "pass_rate": cs5["pass_rate"], "qualifies": bool(qual),
                                "landing_counts": cs5["landing_counts"], "other_correct": cs5["other_correct"],
                                "share": cs5["share"]})
            events += event_rows(u, c, c5, "SCREEN", cs, iter5_origin=True)
    write_json(ROOT / "units.json", {"schema": "iter6_landing_v1", "panel": "II", "utc": utc_now(), "units": units})
    write_json(ROOT / "landing_events.json", {"schema": "iter6_landing_v1", "panel": "II", "utc": utc_now(),
                                              "events": events})
    write_json(RESULTS_DIR / "escape_table.json", esc_rows)
    write_json(RESULTS_DIR / "nudged_correct_S_programs.json", [x for x in progs if x["set"] == "CONFIRMATION"])
    write_json(RESULTS_DIR / "nudged_correct_S_programs_screen.json", [x for x in progs if x["set"] == "SCREEN"])
    with open(RESULTS_DIR / "events_listing.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["event_id", "set", "nudge", "content_free", "is_event", "n_offdefault_correct", "counts",
                    "modal_landing", "margin_pts", "default", "r_u", "qlik_top1", "t_u", "tail_empty", "discordant",
                    "hit_r_u", "hit_qlik_top1", "hit_t_u"])
        for e in events:
            ml = e["modal_landing"]
            w.writerow([e["event_id"], e["set"], e["nudge"], e["content_free"], e["is_event"],
                        e["n_offdefault_correct"], json.dumps(e["counts"]), ml, e["margin_pts"], e["default"],
                        e["r_u"], e["qlik_top1"], e["t_u"], e["tail_empty"], e["discordant"],
                        ml is not None and ml == e["r_u"], ml is not None and ml == e["qlik_top1"],
                        ml is not None and ml == e["t_u"]])
    print(f"units {len(units)}, events {len(events)} ({sum(e['is_event'] for e in events)} is_event)")


if __name__ == "__main__":
    main()
