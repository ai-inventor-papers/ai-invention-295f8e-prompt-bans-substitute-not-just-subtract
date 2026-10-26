"""(0h) Replacement sentences for Section 3.10, each with numbers and sources."""

from __future__ import annotations

import json
from collections import Counter

from loguru import logger

from src.labels import default_of
from src.paths import WS, cite, p

RES = WS / "results"


def _jsonl(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def run_wording_stage() -> None:
    out = {}
    # item 2: calibration caveat + template-arm landings (exp14)
    cal = json.loads(p("exp14", "results/advance_rule_null_calibration.json").read_text())
    summ = json.loads(p("exp14", "results/c1_summary.json").read_text())
    lp = summ["placebos"]["label_permutation"]["share_any_family_advances"]
    rep = json.loads(p("exp14", "results/other_reports.json").read_text())
    evs = _jsonl(p("exp14", "results/c1_events.jsonl"))
    pri = sorted({(e["task"], e["Y"]) for e in evs if e.get("priority")})
    ta = rep["template_arm"]
    n14 = n5 = 0
    flips = []
    for t, y in pri:
        d = default_of(t)
        tam = ta.get(f"{t}:{y}", {})
        land = Counter()
        for w in ("W1", "W2", "W3", "W4"):
            land.update(tam.get(w, {}).get("landing", {}))
        land.pop(y, None)
        mod14 = sorted(land.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if land else None
        n14 += int(mod14 == d)
        named = [e for e in evs if e["task"] == t and e["Y"] == y and e["event_type"] == "exposure_named"]
        mod5 = (named[0].get("modal") or [None])[0] if named else None
        n5 += int(mod5 == d)
        assoc = max(named[0]["associate"], key=named[0]["associate"].get) if named and named[0].get("associate") else None
        if mod14 is not None and mod5 is not None and mod14 != mod5 and assoc in (mod14, mod5):
            flips.append(f"{t}:{y} (templates 1-4: {mod14}; template 5: {mod5}; associate {assoc})")
    out["item2"] = {
        "replacement": (f"Calibration caveat: under exp14's frozen advance rule a null with no real signal advances some "
                        f"family {cal['null_any_family_advances_rate']:.0%} of the time ({cal['n_draws']} draws, "
                        f"{cal['n_events']} events), and a label permutation advances one {lp:.0%} of the time, so an "
                        f"'advance' is not evidence by itself. In the template arm the default is the modal replacement for "
                        f"{n14} of {len(pri)} priority algorithms under templates 1-4 and {n5} of {len(pri)} under template 5; "
                        f"the replacement switches between the default and the associate across templates for "
                        f"{'; '.join(flips) if flips else 'none'}."),
        "numbers": {"null_false_advance": cal["null_any_family_advances_rate"], "label_permutation_advance": lp,
                    "default_modal_W1_4": n14, "default_modal_W5": n5, "n_priority": len(pri), "flips_to_associate": flips},
        "sources": [cite("exp14", "results/advance_rule_null_calibration.json"), cite("exp14", "results/c1_summary.json"),
                    cite("exp14", "results/other_reports.json"), cite("exp14", "results/c1_events.jsonl")]}
    # item 5: where the ban gives way (exp16 prefill depth curve)
    rp = json.loads(p("exp16", "results/replication.json").read_text())["prefill_depth_curve"]
    depth = {}
    for t, d in rp.items():
        pts = sorted([(v["n_prefix_tokens"], v["s_ban"]) for k, v in d.items() if k.startswith("D") and v.get("n_prefix_tokens")])
        holds = [n for n, s in pts if s < 0.5]
        gives = [n for n, s in pts if s >= 0.5]
        depth[t] = {"last_depth_ban_holds": max(holds) if holds else None,
                    "first_depth_ban_gives_way": min(gives) if gives else None, "curve": pts,
                    "SIG_P_open": d.get("SIG", {}).get("P_open"), "NEU_P_open": d.get("NEU", {}).get("P_open")}
    parts = []
    for t, v in depth.items():
        if v["first_depth_ban_gives_way"] is None:
            parts.append(f"{t} never within the swept depths")
        elif v["last_depth_ban_holds"] is None:
            parts.append(f"{t} by {v['first_depth_ban_gives_way']} prefix tokens")
        else:
            parts.append(f"{t} between {v['last_depth_ban_holds']} and {v['first_depth_ban_gives_way']} prefix tokens")
    out["item5"] = {
        "replacement": ("The ban gives way at the opening of the body: a neutral def line undoes none of it, forcing the "
                        "default's opening through its first body token undoes all of it, and the depth sweep places the "
                        "switch " + "; ".join(parts) + " (kth smallest switches at the first content token of its one-line "
                        "body; 10-30 tokens elsewhere)."),
        "numbers": depth, "sources": [cite("exp16", "results/prefill.json"), cite("exp16", "results/replication.json")]}
    # kth smallest depends on the rung definition (exp18)
    c3 = json.loads(p("exp18", "results/c3.json").read_text())
    t03 = [c for c in c3["cells"] if c["task"] == "T03"]
    sens = (c3.get("sensitivity_association_rung2") or {}).get("cells", [])
    qs = [c for c in sens if c.get("task") == "T03" and c.get("S") == "quickselect"]
    qs = qs[0] if qs else {}
    main_q = [c for c in t03 if c.get("S") == "quickselect"]
    main_q = main_q[0] if main_q else {}
    alt_txt = (f"under the association-rung sensitivity its rung is {qs.get('rung_alt') or qs.get('rung2_alt')} and it "
               f"{'still qualifies' if qs.get('qualifies_alt') else 'does not qualify'} (qualifies_alt = {qs.get('qualifies_alt')})")
    out["kth_rung"] = {
        "replacement": (f"Kth smallest's C3 verdict depends on the rung definition: under the frozen rule quickselect is "
                        f"at rung {main_q.get('rung')} (can {main_q.get('can')}, will {main_q.get('will')}, verdict "
                        f"{main_q.get('cell_verdict')}) via the flagged fallback rung rule; {alt_txt}. The T03 cell is "
                        f"therefore labelled rung-definition-dependent."),
        "association_rung_cell": qs,
        "cells": [{k: c.get(k) for k in ("S", "rung", "can", "will", "qualifies", "cell_verdict", "will_source")} for c in t03],
        "sensitivity_association_rung2": c3.get("sensitivity_association_rung2"),
        "sources": [cite("exp18", "results/c3.json"), cite("exp18", "results/reach.json")]}
    # 'carry more' -> both route fractions with jackknife intervals
    route = json.loads((RES / "route.json").read_text())["route_fractions"]
    a, b = route["plain_all5"], route["plain_wo_T13"]
    c = route["cat_all5"]
    fmt = lambda blk, k: f"{blk['point'][k]:.3f} [{blk['jackknife'][k]['ci95'][0]:.2f}, {blk['jackknife'][k]['ci95'][1]:.2f}]"  # noqa: E731
    out["carry_more"] = {
        "replacement": (f"Instead of 'the direct route carries more': pooled over the five gated tasks F_prompt = "
                        f"{fmt(a, 'F_prompt')} and F_direct = {fmt(a, 'F_direct')} (delete-one-task jackknife, t on 4 df); "
                        f"without the residue-gated T13, F_prompt = {fmt(b, 'F_prompt')} and F_direct = {fmt(b, 'F_direct')}; "
                        f"with catalogue-only avoidance F_prompt = {fmt(c, 'F_prompt')} and F_direct = {fmt(c, 'F_direct')}. "
                        "The intervals overlap, so neither route is shown to carry more."),
        "sources": [cite("exp16", "data/samples.jsonl"), cite("exp16", "results/route.json"), "results/route.json"]}
    (RES / "wording.json").write_text(json.dumps(out, indent=1, default=str))
    logger.info(f"wording: item2 W1-4 {n14}/{len(pri)}, W5 {n5}/{len(pri)}, flips {flips}; depth {parts}")
