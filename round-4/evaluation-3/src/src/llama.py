"""(0c) Llama hit rule: modal vs largest-excess landings, 'other' excluded, Poisson-binomial p, snap-back."""

from __future__ import annotations

import json

import pandas as pd
from loguru import logger

from src.labels import default_of
from src.paths import WS, cite, p
from src.stats import binom_sf, poisson_binomial_sf, wilson

RES, TAB = WS / "results", WS / "tables"
FAMILIES = ["SUBTRACT", "LADDER", "ASSOCIATE", "PROXIMITY"]
NOT_ATT = {"invalid", "unresolved", "no_code", "disputed", None}


def _argmax(d: dict, order: list[str]) -> str | None:
    if not d:
        return None
    return max(sorted(d), key=lambda k: d[k])


def realised_excess(landing: dict, S: list[str], B_S: dict) -> str | None:
    if not landing:
        return None
    ex = {k: landing.get(k, 0.0) - B_S.get(k, 0.0) for k in S}
    return max(S, key=lambda k: (ex[k], -S.index(k)))


def run_llama_stage() -> None:
    evs = [json.loads(l) for l in p("exp15", "results/c1_events.jsonl").read_text().splitlines() if l.strip()]
    fc = json.loads(p("exp15", "predictions/forecasts.json").read_text())["events"]
    recs = []
    for e in evs:
        f = fc[e["event_id"]]
        S, B_S, X = f["S"], f["B_S"], e["banned"]
        nb = {}
        for lab, c in e["landing_counts"].items():
            if lab in NOT_ATT or lab == X:
                continue
            key = lab if lab in S else "other"
            nb[key] = nb.get(key, 0) + c
        n_nb = sum(nb.values())
        land = {k: v / n_nb for k, v in nb.items()} if n_nb else {}
        modal_with = _argmax(land, S + ["other"])
        modal_wo = _argmax({k: v for k, v in land.items() if k != "other"}, S)
        excess = realised_excess(land, S, B_S)
        rec = {"event_id": e["event_id"], "task": e["task"], "event_type": e["event_type"], "banned": X,
               "survivors": ";".join(S), "n_S": len(S), "chance": 1 / len(S), "gate_pass": bool(e["gate_pass"]),
               "n_nonbanned_attempts": n_nb, "nonbanned_landing_counts": json.dumps(dict(sorted(nb.items(), key=lambda kv: -kv[1]))),
               "modal_with_other": modal_with, "modal_excl_other": modal_wo, "largest_excess": excess,
               "recorded_hit_label": e.get("hit_label"),
               "rule_recorded": "modal" if e["event_type"] == "modal" else "largest_excess (src/scoring.py:88-94)"}
        rec["recorded_rule_landing"] = modal_with if e["event_type"] == "modal" else excess
        rec["recorded_hit_label_reproduced"] = rec["recorded_rule_landing"] == e.get("hit_label")
        for fam in FAMILIES:
            ff = f["families"][fam]
            top = e["top1"].get(fam)
            fv = ff.get("f") if ff.get("defined") else None
            # recorded nominee unless it is 'other' (or undefined): then the family's best non-'other' survivor
            if top is not None and top != "other":
                top_wo = top
            else:
                top_wo = _argmax({k: v for k, v in fv.items() if k != "other" and v > 0}, S) if fv else None
            rec[f"{fam}_top1"] = top
            rec[f"{fam}_top1_excl_other"] = top_wo
            rec[f"{fam}_defined"] = bool(ff.get("defined"))
            rec[f"{fam}_hit_modal"] = bool(top is not None and top == modal_with)
            rec[f"{fam}_hit_excess"] = bool(top is not None and top == excess)
            rec[f"{fam}_hit_recorded_rule"] = bool(top is not None and top == rec["recorded_rule_landing"])
            land_wo = modal_wo if e["event_type"] == "modal" else excess
            # strict (primary): an 'other' nominee scores no hit and 'other' is never a landing
            rec[f"{fam}_hit_excl_other"] = bool(top not in (None, "other") and land_wo is not None and top == land_wo)
            # sensitivity: an 'other' nominee falls back to the family's best non-'other' survivor
            rec[f"{fam}_hit_excl_other_fallback"] = bool(top_wo is not None and land_wo is not None and top_wo == land_wo)
            rec[f"{fam}_hit_modal_excl_other"] = bool(top_wo is not None and top_wo == modal_wo)
        recs.append(rec)
    df = pd.DataFrame(recs)
    df.to_csv(TAB / "llama_hits.csv", index=False)
    g = df[df.gate_pass]
    summ = {"n_events": int(len(df)), "n_gated": int(len(g)), "families": {}}
    for fam in FAMILIES:
        s = {}
        for col in ("hit_modal", "hit_excess", "hit_recorded_rule", "hit_excl_other", "hit_excl_other_fallback",
                    "hit_modal_excl_other"):
            k = int(g[f"{fam}_{col}"].sum())
            s[col] = {"hits": k, "n": int(len(g)), "p_poisson_binomial": poisson_binomial_sf(k, g.chance.tolist()),
                      "p_binomial_mean_chance": binom_sf(k, int(len(g)), float(g.chance.mean()))}
        summ["families"][fam] = s
    # Table 102 side-by-side and snap-back (present-minor events)
    pm = df[df.event_type == "present_minor"]
    side = []
    for _, r in pm.iterrows():
        nb = json.loads(r.nonbanned_landing_counts)
        D = default_of(r.task, "llama")
        k = nb.get(D, 0)
        lo, hi = wilson(k, int(r.n_nonbanned_attempts))
        side.append({"event_id": r.event_id, "task": r.task, "banned": r.banned, "default": D,
                     "modal_with_other": r.modal_with_other, "modal_excl_other": r.modal_excl_other,
                     "largest_excess": r.largest_excess, "default_count": k, "n_nonbanned": int(r.n_nonbanned_attempts),
                     "default_share": k / r.n_nonbanned_attempts if r.n_nonbanned_attempts else None,
                     "wilson95": [lo, hi]})
    summ["table102_side_by_side"] = side
    exp_tbl = {("T14", "sort_by_count"): ("heap", 54, 75), ("T04", "kmp"): ("naive", 48, 66),
               ("T10", "dfs"): ("union_find", 79, 85)}
    checks = []
    for s in side:
        key = (s["task"], s["banned"])
        if key in exp_tbl:
            lab, k, n = exp_tbl[key]
            checks.append({"event": s["event_id"], "expected": f"{lab} {k} of {n}",
                           "recomputed": f"{s['modal_with_other']} {s['default_count']} of {s['n_nonbanned']}",
                           "match": s["modal_with_other"] == lab and s["default_count"] == k and s["n_nonbanned"] == n})
    summ["table102_checks"] = checks
    sb = [s for s in side if (s["task"], s["banned"]) in exp_tbl]
    summ["snap_back_sentence"] = (
        "Cross-model replication of exp14's snap-back: under Llama present-minor bans the banned minor mode is avoided "
        "but the model returns to its default rather than to another survivor - "
        + "; ".join(f"{s['task']} ban of {s['banned']}: default {s['default']} {s['default_count']}/{s['n_nonbanned']} "
                    f"= {s['default_share']:.2f} [{s['wilson95'][0]:.2f}, {s['wilson95'][1]:.2f}]" for s in sb)
        + " (default share among non-banned attempts, Wilson 95%; " + cite("exp15", "results/c1_events.jsonl") + ").")
    summ["section_3_5_note"] = ("Present-minor events were scored with the largest-excess rule (landing minus the "
                                "ban-free baseline B_S over survivors; " + cite("exp15", "src/scoring.py") +
                                " lines 88-94), modal events with the argmax of the landing.")
    summ["recorded_hit_labels_reproduced"] = int(df.recorded_hit_label_reproduced.sum())
    summ["sources"] = [cite("exp15", "results/c1_events.jsonl"), cite("exp15", "predictions/forecasts.json"),
                       cite("exp15", "src/scoring.py")]
    (RES / "llama.json").write_text(json.dumps(summ, indent=1, default=str))
    f = summ["families"]
    logger.info(f"llama: gated {len(g)}; LADDER excl-other {f['LADDER']['hit_excl_other']}; ASSOCIATE excl-other "
                f"{f['ASSOCIATE']['hit_excl_other']}; table102 {sum(c['match'] for c in checks)}/{len(checks)}; "
                f"hit labels reproduced {summ['recorded_hit_labels_reproduced']}/{len(df)}")
