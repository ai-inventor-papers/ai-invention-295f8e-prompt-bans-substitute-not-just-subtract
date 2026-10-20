#!/usr/bin/env python3
"""Step H: event table (H1), frozen C1 scoring per event (H2), sensitivities (H3), C2b-descriptive (H4),
present-minor X-specific gain (H5), knob view (H7), c1_events.jsonl in the shared row schema."""

from __future__ import annotations

import collections
import math
from typing import Any

import numpy as np
from loguru import logger

from src import prompts_llama as P
from src import scoring as SC
from src.stats_util import hill1, jsd, newcombe, rarefied_hill1, wilson
from src.ws import DATA, FROZEN_TASKS, MODEL_TAG, PRED, RESULTS, read_json, read_jsonl, sha256_file, write_json, write_jsonl

from bench.common.order import mentions  # noqa: E402


def _rows_by_event(labels: list[dict], raw_by: dict, phases: tuple[str, ...]) -> dict[str, list[dict]]:
    out = collections.defaultdict(list)
    for r in labels:
        if r.get("phase") in phases:
            raw = raw_by.get(r["row_id"], {})
            eid = raw.get("event_id")
            if eid:
                out[eid].append(dict(r, template=raw.get("template"), text=raw.get("text")))
    return out


def event_table(ev: dict, fc: dict, ban: list[dict], base_labels: list[str]) -> dict[str, Any]:
    X, S, t = fc["X"], fc["S"], fc["task"]
    labs = [r["label"] for r in ban]
    n_gen = len(labs)
    att = [l for l in labs if l not in ("invalid", "unresolved")]
    g = SC.gate(labs, X, S)
    land = collections.Counter(att)
    corr = collections.Counter(r["label"] for r in ban if r.get("passed") and r["label"] not in ("invalid", X))
    n_corr = sum(corr.values())
    other = land.get("other", 0)
    inv = sum(1 for l in labs if l == "invalid")
    bx = [l for l in base_labels if l not in ("invalid", "unresolved")]
    base_nonx = sum(1 for l in bx if l != X) / max(len(bx), 1)
    xs = [r for r in ban if r["label"] == X]
    disguised = sum(1 for r in xs if X not in mentions(t, r.get("text") or ""))
    return {"n_generations": n_gen, "n_attempts": len(att), "avoidance": g["avoidance"],
            "avoidance_wilson": wilson(len(att) - land.get(X, 0), len(att)) if att else None,
            "gate_pass": g["gate_pass"], "n_nonbanned": g["n_nonbanned"], "landing_counts": dict(land),
            "correct_counts": dict(corr), "n_correct_nonbanned": n_corr, "hill_cc": hill1(corr.values()),
            "hill_cc_rarefied10": rarefied_hill1(dict(corr), 10) if n_corr >= 10 else None,
            "hill_cc_interpretable": n_corr >= 10,
            "other_share": other / max(len(att), 1), "other_wilson": wilson(other, len(att)) if att else None,
            "invalid_share": inv / max(n_gen, 1), "baseline_nonX_share": base_nonx,
            "ban_nonX_share": 1 - land.get(X, 0) / max(len(att), 1),
            "disguise_rate": disguised / len(xs) if xs else None, "n_banned_mechanism": len(xs)}


def _score_rows(evs: list[dict], fcs: dict, ban_by: dict, *, pm: bool = False, correct_only: bool = False,
                drop_coveto: bool = False, drop_template: int | None = None) -> list[dict]:
    rows = []
    for e in evs:
        fc = fcs[e["event_id"]]
        ban = ban_by.get(e["event_id"], [])
        if drop_template is not None:
            ban = [r for r in ban if r.get("template") != drop_template]
        labs = [r["label"] for r in ban]
        labs_score = [r["label"] if (r.get("passed") or r["label"] == fc["X"]) else "invalid" for r in ban] \
            if correct_only else None
        fc2 = fc
        S = fc["S"]
        if drop_coveto:
            co = set()
            for ng in (fc.get("ngram") or []):
                co |= set((ng or {}).get("co_vetoed") or [])
            co -= {fc["X"]}
            if co:
                S = [m for m in fc["S"] if m not in co]
                if not S:  # every survivor co-vetoed: the event has no bins left in this sensitivity (excluded)
                    continue
                labs = [l for l in labs if l not in co]
                if labs_score is not None:
                    labs_score = [l for l in labs_score if l not in co]
                fc2 = _restrict(fc, S)
        if pm:
            fc2 = dict(fc2)
            fam = {}
            for k, v in fc2["families"].items():
                pmv = fc2["families_pm"].get(k, {})
                fam[k] = dict(v, f=pmv.get("f"), defined=bool(pmv.get("defined")) and v["defined"])
            fc2["families"] = fam
        sc = SC.score_event({"event_type": fc["event_type"], "X": fc["X"], "S": S}, fc2, labs)
        if labs_score is not None:  # correct-only rescoring: gate from attempts, log scores on passing programs
            sc2 = SC.score_event({"event_type": fc["event_type"], "X": fc["X"], "S": S}, fc2, labs_score)
            sc2["gate"] = sc["gate"]
            ls = {f: sc2["logscore"][f] for f in SC.FAMILIES if not math.isnan(sc2["logscore"][f])}
            if len(ls) >= 2:
                srt = sorted(ls.items(), key=lambda kv: -kv[1])
                sc2["best"], sc2["margin"] = srt[0][0], srt[0][1] - srt[1][1]
            else:
                sc2["best"], sc2["margin"] = None, float("nan")
            sc2["winner"] = sc2["best"] if (sc["gate"]["gate_pass"] and sc2["disagreeing"]
                                            and sc2["margin"] >= SC.ADV_MARGIN) else None
            sc = sc2
        rows.append({"event_id": e["event_id"], "task": e["task"], "scored": sc})
    return rows


def _restrict(fc: dict, S: list[str]) -> dict:
    keep = set(S) | {"other"}

    def rs(d):
        if d is None:
            return None
        dd = {k: v for k, v in d.items() if k in keep}
        tot = sum(dd.values())
        return {k: v / tot for k, v in dd.items()} if tot > 0 else None

    fam = {}
    for k, v in fc["families"].items():
        f = rs(v["f"]) if v["defined"] else None
        top = v["top1"] if v["top1"] in keep else (max(f, key=f.get) if f else None)
        fam[k] = dict(v, f=f, top1=top, defined=v["defined"] and f is not None)
    fpm = {}
    for k, v in fc["families_pm"].items():
        f = rs(v.get("f")) if v.get("defined") else None
        fpm[k] = dict(v, f=f, defined=bool(v.get("defined")) and f is not None)
    return dict(fc, S=S, families=fam, families_pm=fpm, B_S=rs(fc["B_S"]) or SC.uniform(S))


def run(labels: list[dict], raw_by: dict, ctx: dict) -> dict[str, Any]:
    ev = read_json(PRED / "events.json")
    fcs = read_json(PRED / "forecasts.json")["events"]
    dec = read_json(RESULTS / "decision_sets.json")
    lab_by = {r["row_id"]: r for r in labels}
    ban_by = _rows_by_event(labels, raw_by, ("G1", "G2"))
    commit_sha = sha256_file(PRED / "forecasts.json")
    audit = read_json(RESULTS / "llama_label_audit.json") if (RESULTS / "llama_label_audit.json").exists() else {}
    flagged_tasks = set(audit.get("flagged_tasks_below_0.85", []))
    evs = ev["events"]
    out: dict[str, Any] = {"events": {}}
    prim = _score_rows(evs, fcs, ban_by)
    c1rows = []
    for e, sr in zip(evs, prim):
        fc = fcs[e["event_id"]]
        base_labels = [lab_by[r]["label"] for r in dec[e["task"]]["decision_row_ids"] if r in lab_by]
        tab = event_table(e, fc, ban_by.get(e["event_id"], []), base_labels)
        sc = sr["scored"]
        pm = _score_rows([e], fcs, ban_by, pm=True)[0]["scored"]
        out["events"][e["event_id"]] = {"table": tab, "scored": sc, "scored_pm": pm}
        c1rows.append({
            "model": MODEL_TAG, "task": e["task"], "event_id": e["event_id"], "event_type": e["event_type"],
            "banned": e["banned"], "n_attempts": tab["n_attempts"], "avoidance": tab["avoidance"],
            "gate_pass": tab["gate_pass"], "landing_counts": tab["landing_counts"],
            "correct_counts": tab["correct_counts"], "other_share": tab["other_share"],
            "forecasts": {k: v["f"] for k, v in fc["families"].items()},
            "top1": sc["top1"], "logscore": sc["logscore"], "disagreeing": sc["disagreeing"],
            "commit_sha256": commit_sha, "forecasts_pm": {k: v.get("f") for k, v in fc["families_pm"].items()},
            "logscore_pm": pm["logscore"], "transferred_top1": fc["top1_transferred"], "s_X": fc["s_X"],
            "hill_cc": tab["hill_cc"], "invalid_share": tab["invalid_share"], "hit_label": sc["hit_label"],
            "winner": sc["winner"], "margin": sc["margin"], "flags": fc["flags"] + (
                ["D_from_attempts"] if read_json(PRED / "events.json")["tasks"][e["task"]]["D_from_attempts"] else []) + (
                ["label_audit_below_0.85"] if e["task"] in flagged_tasks else [])})
    write_jsonl(RESULTS / "c1_events.jsonl", c1rows)
    out["c1"] = SC.aggregate(prim)
    out["c1_pm"] = SC.aggregate(_score_rows(evs, fcs, ban_by, pm=True))
    # ---------------- H3 sensitivities
    sens = {"point_mass": {k: out["c1_pm"][k] for k in ("branch", "wins", "advances", "n_disagreeing_gated")}}
    for name, kw in (("drop_coveto", {"drop_coveto": True}), ("correct_only", {"correct_only": True})):
        a = SC.aggregate(_score_rows(evs, fcs, ban_by, **kw))
        sens[name] = {k: a[k] for k in ("branch", "wins", "advances", "n_disagreeing_gated", "n_gated")}
    tasks_ev = read_json(PRED / "events.json")["tasks"]
    keep = [e for e in evs if not tasks_ev[e["task"]]["D_from_attempts"] and e["task"] not in flagged_tasks]
    a = SC.aggregate(_score_rows(keep, fcs, ban_by))
    sens["excl_D_from_attempts_and_audit_flagged"] = {k: a[k] for k in ("branch", "wins", "advances",
                                                                         "n_disagreeing_gated", "n_gated")}
    loto = {}
    for w in range(1, 6):
        a = SC.aggregate(_score_rows(evs, fcs, ban_by, drop_template=w))
        loto[f"drop_W{w}"] = {k: a[k] for k in ("branch", "wins", "n_disagreeing_gated")}
    sens["leave_one_template_out"] = loto
    # decision set without the FP8 pilot (bf16 B1+B4): rebuild B_S / s_X dependent forecasts
    try:
        from src.forecasts import build_event
        ctx = dict(ctx)
        ctx["decision_labels"] = {t: [lab_by[r]["label"] for r in v["alt_row_ids"] if r in lab_by] if v["decision_set"].startswith("pooled")
                                  else [lab_by[r]["label"] for r in v["decision_row_ids"] if r in lab_by]
                                  for t, v in dec.items()}
        fcs_alt = {e["event_id"]: build_event(e, ctx) for e in evs}
        a = SC.aggregate(_score_rows(evs, fcs_alt, ban_by))
        sens["decision_set_bf16_only"] = {k: a[k] for k in ("branch", "wins", "advances", "n_disagreeing_gated")}
    except Exception as ex:  # noqa: BLE001 - sensitivity must not kill the primary analysis
        logger.error(f"bf16-only sensitivity failed: {ex}")
        sens["decision_set_bf16_only"] = {"error": str(ex)[:300]}
    out["sensitivities"] = sens
    # ---------------- H4 C2b descriptive
    c2b = []
    rng = np.random.default_rng(0)
    for e in evs:
        fc = fcs[e["event_id"]]
        one = fc.get("ONESHOT")
        mv = fc.get("oneshot_moved_share")
        if not one or mv is None or mv < 0.5:
            continue
        ban = ban_by.get(e["event_id"], [])
        X, S = fc["X"], fc["S"]
        co = set()
        for ng in (fc.get("ngram") or []):
            co |= set((ng or {}).get("co_vetoed") or [])
        Sx = [m for m in S if m not in co]
        land = collections.Counter(r["label"] for r in ban if r["label"] in Sx)
        if not land:
            continue
        b_mod = max(Sx, key=lambda k: (land.get(k, 0), -Sx.index(k)))
        o_mod = max(Sx, key=lambda k: (one.get(k, 0.0), -Sx.index(k)))
        bl = {k: land.get(k, 0) / sum(land.values()) for k in Sx}
        ol = {k: one.get(k, 0.0) for k in Sx}
        js = jsd(bl, ol)
        by_t = collections.defaultdict(list)
        for r in ban:
            if r["label"] in Sx:
                by_t[r.get("template")].append(r["label"])
        temps = sorted(by_t)
        null = []
        for _ in range(1000):
            reps = []
            for _k in range(2):
                tk = rng.choice(len(temps), size=len(temps), replace=True)
                labs = []
                for i in tk:
                    pool = by_t[temps[i]]
                    labs += list(rng.choice(pool, size=len(pool), replace=True))
                c = collections.Counter(labs)
                reps.append({k: c.get(k, 0) / max(len(labs), 1) for k in Sx})
            null.append(jsd(reps[0], reps[1]))
        q95 = float(np.nanpercentile(null, 95))
        c2b.append({"event_id": e["event_id"], "moved_share": mv, "ban_modal": b_mod, "oneshot_modal": o_mod,
                    "same_modal": b_mod == o_mod, "jsd": js, "null_q95": q95, "within_null": js <= q95,
                    "both": (b_mod == o_mod) and js <= q95})
    out["c2b_descriptive"] = {"events": c2b, "share_both": (sum(1 for c in c2b if c["both"]) / len(c2b)) if c2b else None,
                              "n": len(c2b), "pre_registered_bar_reference_only": "2/3"}
    # ---------------- H5 present-minor X-specific gain
    h5 = []
    for e in evs:
        if e["event_type"] != "present_minor":
            continue
        fc = fcs[e["event_id"]]
        tgt = fc["families"]["ASSOCIATE"].get("target")
        if tgt is None:
            continue
        ban = [r["label"] for r in ban_by.get(e["event_id"], []) if r["label"] not in ("invalid", "unresolved")]
        sub = fc["families"]["SUBTRACT"]
        # persistent-veto share of the associate (weighted, final round used by SUBTRACT, all attempts)
        vr = ctx["veto"].get(e["event_id"], {})
        pr = (vr.get("persistent_rounds") or [])
        if sub.get("defined") and pr:
            rr = [r for r in pr if r["round"] == sub["round"]][0]
            att = [(l, w) for l, w in zip(rr["labels"], rr["weights"]) if l not in (None, "invalid", "unresolved")]
            vk = sum(w for l, w in att if l == tgt)
            vn = sum(w for _, w in att)
        else:
            vk, vn = float("nan"), 0
        base = [l for l in ctx_dec(dec, lab_by, e["task"]) if l not in ("invalid", "unresolved")]
        bk = sum(1 for l in ban if l == tgt)
        d = newcombe(bk, len(ban), vk, vn) if vn else (float("nan"),) * 3
        h5.append({"event_id": e["event_id"], "associate": tgt, "ban_share": bk / max(len(ban), 1), "n_ban": len(ban),
                   "veto_share": (vk / vn) if vn else None, "n_veto_w": vn,
                   "baseline_share": sum(1 for l in base if l == tgt) / max(len(base), 1), "n_base": len(base),
                   "ban_minus_veto": d[0], "newcombe_ci": [d[1], d[2]],
                   "reading": "substitution predicts ban > veto; subtraction predicts equality"})
    out["present_minor_gain"] = h5
    # ---------------- H7 knob view
    knob = {}
    from src.forecasts import push_label_index
    pidx = push_label_index(labels)
    for t in FROZEN_TASKS:
        D = tasks_ev[t]["D"]
        row = {}
        for pk in ("nonce", "novelty", "randdir:s0", "randdir:s1", "randdir:s2"):
            labs = [l for l in pidx.get((t, pk), []) if l not in ("invalid", "unresolved")]
            rr = [lab_by[r] for r in lab_by if lab_by[r].get("task") == t and lab_by[r].get("condition") == pk
                  and lab_by[r].get("phase") in ("B5", "E3")]
            corr = collections.Counter(r["label"] for r in rr if r.get("passed") and r["label"] != "invalid")
            row[pk] = {"n_attempts": len(labs), "D_share": sum(1 for l in labs if l == D) / max(len(labs), 1),
                       "avoidance_D": 1 - sum(1 for l in labs if l == D) / max(len(labs), 1),
                       "hill_cc": hill1(corr.values()), "n_correct": sum(corr.values()),
                       "counts": dict(collections.Counter(labs))}
        base = [l for l in ctx_dec(dec, lab_by, t) if l not in ("invalid", "unresolved")]
        row["baseline_decision_set"] = {"n_attempts": len(base), "D_share": sum(1 for l in base if l == D) / max(len(base), 1)}
        knob[t] = row
    out["knob_view"] = knob
    # ---------------- per-round veto re-emergence recomputed with the final (decode-corrected) labels
    vr_out = {}
    for e in evs:
        ent = ctx["veto"].get(e["event_id"], {})
        rows_r = []
        for rr in ent.get("persistent_rounds") or []:
            att = [(l, w) for l, w in zip(rr["labels"], rr["weights"]) if l not in (None, "invalid", "unresolved")]
            wt = sum(w for _, w in att)
            wa = sum(w for l, w in att if l == e["banned"])
            rows_r.append({"round": rr["round"], "A_share": wa / wt if wt else None, "n_attempts_w": wt,
                           "n_nonbanned_w": wt - wa})
        vr_out[e["event_id"]] = rows_r
    out["veto_rounds_corrected"] = vr_out
    write_json(RESULTS / "analysis.json", out)
    return out


def ctx_dec(dec: dict, lab_by: dict, t: str) -> list[str]:
    return [lab_by[r]["label"] for r in dec[t]["decision_row_ids"] if r in lab_by]
