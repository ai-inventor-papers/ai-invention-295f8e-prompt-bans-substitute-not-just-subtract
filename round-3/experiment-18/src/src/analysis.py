"""S9 ANALYSIS: every reported number is computed here from data/*.jsonl, results/state_*.json and the committed
predictions (src/rederive.py recomputes the headline numbers independently).

Outputs: results/walk.json, results/can.json, results/reach.json, results/c3.json, results/list_independence.json,
results/disguise.json, results/two_step_scores.json, results/reach_events.jsonl, results/longform.json,
results/fp8_crosscheck.json, results/novelty_audit.json (merged with the manual pass), figures/fig*.{pdf,png}.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from typing import Any

from config import (ALL_TASKS, BENCH_TASKS, C3_CAN_MIN, C3_DISCONFIRM, C3_WILL_MAX, DATA, FIGS, INPUTS, PATH_TASKS,
                    PRED, RESULTS, TASKS, read_jsonl, write_json)
from stats import (cluster_bootstrap, cohen_kappa, exact_upper, hill1, hill1_rarefied, js_null, log_score, newcombe,
                   perm_chi2, wilson)

PATH_ALIASES = {
    "T1": {"bfs": ["bfs", "breadth"], "dfs": ["dfs", "depth"], "bibfs": ["bidirectional", "bibfs"],
           "iddfs": ["iddfs", "deepening"], "astar_gbfs": ["astar", "a*", "a_star", "greedy", "best-first",
                                                            "best_first", "heuristic"], "dijkstra": ["dijkstra"]},
    "T2": {"dijkstra": ["dijkstra"], "bf_spfa": ["bellman", "ford", "spfa"], "bidijkstra": ["bidirectional", "bidij"],
           "floyd": ["floyd", "warshall"], "dial": ["dial", "bucket"]},
}


def load(arm: str) -> list[dict[str, Any]]:
    return read_jsonl(DATA / f"samples_{arm}.jsonl")


def miss_map() -> dict[tuple[str, str], str]:
    """(task, code_sha256) -> catalogue label for programs the audit classed LABELLER MISS (manual pass)."""
    p = RESULTS / "manual_audit.json"
    j = RESULTS / "novelty_audit_judges.json"
    if not (p.exists() and j.exists()):
        return {}
    man = json.loads(p.read_text())["records"]
    out = {}
    for r in json.loads(j.read_text())["records"]:
        m = man.get(r["sample_id"])
        if m and m["final_class"] == "LABELLER MISS" and m.get("catalogue_label_if_miss"):
            out[(r["task"], r["code_sha256"])] = m["catalogue_label_if_miss"]
    return out


def corrected(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mm = miss_map()
    return [dict(r, label=mm.get((r["task"], r["code_sha256"]), r["label"])) for r in rows]


def state(arm: str, task: str) -> dict[str, Any] | None:
    p = RESULTS / f"state_{arm}_{task}.json"
    return json.loads(p.read_text()) if p.exists() else None


def comp(rows: list[dict[str, Any]], banned: list[str]) -> dict[str, Any]:
    n = len(rows)
    att = [r for r in rows if r["label"] != "invalid"]
    k_pass = sum(r["passed"] for r in att)
    nonb = [r for r in att if r["label"] not in banned]
    ok = [r for r in nonb if r["passed"]]
    cnt = Counter(r["label"] for r in rows)
    return {"n": n, "attempted": len(att), "counts": dict(cnt),
            "avoidance": len(nonb) / len(att) if att else None, "avoidance_ci": wilson(len(nonb), len(att)),
            "landing": dict(Counter(r["label"] for r in nonb)), "landing_correct": dict(Counter(r["label"] for r in ok)),
            "hill_cc": hill1(Counter(r["label"] for r in ok).values()),
            "hill_cc_rarefied20": hill1_rarefied([r["label"] for r in ok], 20),
            "other_share": cnt.get("other", 0) / n if n else None, "invalid_share": cnt.get("invalid", 0) / n if n else None,
            "pass_rate": k_pass / len(att) if att else None, "pass_ci": wilson(k_pass, len(att)),
            "per_template": {w: dict(Counter(r["label"] for r in rows if r.get("template") == w))
                             for w in sorted({r.get("template") for r in rows if r.get("template")})}}


# ------------------------------------------------------------------------------------------------ walk
def features_ext(code: str | None) -> set[str]:
    """AST surfaces (imports, calls, attributes, classes; walk.ast_features) plus assigned identifier names."""
    import ast as _ast

    from walk import ast_features

    out = set(ast_features(code))
    try:
        tree = _ast.parse(code or "")
    except (SyntaxError, ValueError):
        return out
    for n in _ast.walk(tree):
        if isinstance(n, _ast.Name) and isinstance(n.ctx, _ast.Store):
            out.add(f"name {n.id}")
        elif isinstance(n, _ast.arg):
            out.add(f"name {n.arg}")
    return out


def surfaces_ext(re_rows: list[dict[str, Any]], refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not re_rows:
        return []
    fr = Counter(f for r in re_rows for f in features_ext(r.get("code")))
    fref = Counter(f for r in refs for f in features_ext(r.get("code")))
    out = []
    for f, k in fr.most_common():
        a, b = k / len(re_rows), (fref[f] / len(refs) if refs else 0.0)
        if a >= 0.3 and b < 0.1:
            out.append({"feature": f, "share_reemerged": round(a, 3), "share_refs": round(b, 3)})
    lost = []
    for f, k in fref.most_common(40):
        b = k / max(1, len(refs))
        a = fr[f] / len(re_rows)
        if b >= 0.8 and a < 0.3:
            lost.append({"feature": f, "share_refs": round(b, 3), "share_reemerged": round(a, 3)})
    return out[:15] + [{"lost_feature": x} for x in lost[:10]]


def walk_results() -> dict[str, Any]:
    out: dict[str, Any] = {}
    walk_rows = load("walk")
    sham_rows = load("sham")
    for t in ALL_TASKS:
        st = state("walk", t)
        if not st:
            out[t] = {"status": "NOT_RUN"}
            continue
        steps = []
        from programs import forced_as_requested, refs_default

        def refs_for(a):
            if a == st["default"]:
                return [r for r in refs_default()[t] if r["label"] == a]
            return forced_as_requested(t, a)

        for h in st["history"]:
            s = h["summary"]
            rr = [r for r in walk_rows if r["task"] == t and r["step"] == h["step"] and r["round"] == h["round"]]
            surf_ext = {a: surfaces_ext([r for r in rr if r["label"] == a], refs_for(a)) for a in h["vetoed"]
                        if any(r["label"] == a for r in rr)}
            cc = dict(Counter(r["label"] for r in corrected(rr)))
            steps.append({"step": h["step"], "round": h["round"], "vetoed": h["vetoed"], "n": s["n"],
                          "counts_corrected": cc,
                          "attempted": s["attempted"], "counts": s["counts"], "pass_rate": s["pass_rate"],
                          "pass_ci": s["pass_ci"], "modal_nonvetoed": s["modal_nonvetoed"],
                          "landing": s["landing"], "landing_correct": s["landing_correct"], "hill_cc": s["hill_cc"],
                          "hill_cc_rarefied20": s["hill_cc_rarefied20"], "other_share": s["other_share"],
                          "invalid_share": s["invalid_share"], "reemergence": s["reemergence"],
                          "leak_rate": s["leak_rate"], "veto_occurrences_total": s["veto_occurrences_total"],
                          "truncated_share": s["truncated_share"], "decision": h.get("decision"),
                          "surfaces": h.get("surfaces"), "surfaces_ext": surf_ext, "per_template": s["per_template"]})
        masks = [{"kind": it["kind"], "algo": it["algo"], "step": it["step"], "round": it["round"], "ids": it["ids"],
                  "string": it["string"], "variants": [v["string"] for v in it["variants"]],
                  "collateral": it["info"].get("collateral"), "co_vetoed": it["info"].get("co_vetoed"),
                  "score": it["info"].get("score"), "presence_refs": it["info"].get("presence_refs"),
                  "surfaces": it["info"].get("surfaces")} for it in st["mask_items"]]
        reached = [r for r in st.get("rungs", []) if r["rung"] >= 2 and r["label"] not in ("other", "invalid")]
        rec = {"status": st["status"], "default": st["default"], "vetoed": st["vetoed"], "rungs": st.get("rungs"),
               "deepest_rung_reached": max([r["rung"] for r in reached], default=1), "steps": steps,
               "mask_items": masks, "notes": st.get("notes"), "distinctive_default": st.get("distinctive_default")}
        # sham vs distinctive veto (step-1 round-0) on the default share and pass rate
        sh = state("sham", t)
        s1 = [r for r in walk_rows if r["task"] == t and r["step"] == 1 and r["round"] == 0]
        if sh:
            srows = [r for r in sham_rows if r["task"] == t]
            D = st["default"]

            def dshare(rows):
                att = [r for r in rows if r["label"] != "invalid"]
                return sum(r["label"] == D for r in att), len(att)

            kd, nd = dshare(srows)
            kv, nv = dshare(s1)
            ps = [r for r in srows if r["label"] != "invalid"]
            pv = [r for r in s1 if r["label"] != "invalid"]
            rec["sham_vs_distinctive"] = {
                "sham_ngram": sh["mask_items"][0]["string"], "sham_default_share": kd / nd if nd else None,
                "sham_default_ci": wilson(kd, nd), "distinctive_default_share": kv / nv if nv else None,
                "distinctive_default_ci": wilson(kv, nv), "default_share_diff": newcombe(kd, nd, kv, nv),
                "sham_pass_rate": sum(r["passed"] for r in ps) / len(ps) if ps else None,
                "distinctive_pass_rate": sum(r["passed"] for r in pv) / len(pv) if pv else None,
                "pass_diff": newcombe(sum(r["passed"] for r in ps), len(ps), sum(r["passed"] for r in pv), len(pv)),
                "sham_invalid_share": sum(r["label"] == "invalid" for r in srows) / len(srows) if srows else None,
                "distinctive_invalid_share": sum(r["label"] == "invalid" for r in s1) / len(s1) if s1 else None,
                "sham_leak_rate": sh["history"][0]["summary"]["leak_rate"] if sh["history"] else None,
                "prediction": "sham keeps the default share >= 0.9",
                "prediction_met": (kd / nd >= 0.9) if nd else None,
                "flag_generic_masking": (1 - kd / nd >= 0.30) if nd else None}
        else:
            p = RESULTS / f"sham_not_constructible_{t}.json"
            rec["sham_vs_distinctive"] = json.loads(p.read_text()) if p.exists() else {"status": "NOT_RUN"}
        out[t] = rec
    # fixed-TOP5 (T1) vs exp9 TOP5 prompt ban
    st5 = state("fixed_top5", "T1")
    if st5:
        rows5 = load("fixed_top5")
        last_r = max(r["round"] for r in rows5) if rows5 else 0
        last = [r for r in rows5 if r["round"] == last_r]
        land = json.loads((INPUTS / "exp9" / "results" / "landing.json").read_text())
        top5 = land["conditions"].get("t1|multi:TOP5") or {}
        out["fixed_top5_T1"] = {"targets": st5["vetoed"], "rounds": [
            {"round": h["round"], "counts": h["summary"]["counts"], "pass_rate": h["summary"]["pass_rate"],
             "reemergence": h["summary"]["reemergence"], "leak_rate": h["summary"]["leak_rate"],
             "decision": h.get("decision")} for h in st5["history"]],
            "final_round": comp(last, st5["vetoed"]),
            "mask_items": [{"algo": it["algo"], "string": it["string"], "kind": it["kind"]} for it in st5["mask_items"]],
            "exp9_TOP5_prompt_ban": {"avoidance": top5.get("avoidance"), "counts": top5.get("counts"), "banned": top5.get("banned"), "pass_rate_attempted": top5.get("pass_rate_attempted"),
                                     "n": top5.get("n_samples")}}
    write_json(RESULTS / "walk.json", out)
    return out


# ------------------------------------------------------------------------------------------------ can
def can_results() -> dict[str, Any]:
    from programs import can_table

    ct = can_table()
    exp11 = json.loads((INPUTS / "exp11" / "forced_adherence.json").read_text())
    out = {"tasks": ct, "analysis_sets": {}, "exp11_forced_adherence_crosscheck": {}}
    for t in BENCH_TASKS:
        rec = {a: ct[t][a]["primary"]["can"] for a in TASKS[t]["catalogue"]}
        out["analysis_sets"][t] = {"recomputed": sorted([a for a, v in rec.items() if v is not None and v >= 0.5]),
                                   "plan": sorted(TASKS[t]["analysis_set"]),
                                   "match": sorted([a for a, v in rec.items() if v is not None and v >= 0.5]) ==
                                   sorted(TASKS[t]["analysis_set"])}
        for a in TASKS[t]["catalogue"]:
            fa = exp11.get(f"{t}:{a}")
            if fa:
                out["exp11_forced_adherence_crosscheck"][f"{t}:{a}"] = {
                    "exp11_adherence": fa.get("adherence"), "recomputed_labelled_share":
                    ct[t][a]["by_source"]["exp11"]["labelled_share"]}
    write_json(RESULTS / "can.json", out)
    return out


# ------------------------------------------------------------------------------------------------ reach / C3
def _aliases(task: str, mode: str) -> list[str]:
    if TASKS[task]["family"] == "bench":
        al = list(TASKS[task]["aliases"].get(mode, []))
        al.append(TASKS[task]["display"][mode].lower())
        return [a.lower() for a in al]
    return PATH_ALIASES[task][mode]


def _ident_text(code: str) -> str:
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", code or "")
    return s.replace("_", " ").lower()


def disguised(task: str, row: dict[str, Any], banned: list[str]) -> bool:
    txt = _ident_text(row.get("code") or "") + " " + (row.get("code") or "").lower()
    return not any(a in txt for m in banned for a in _aliases(task, m))


def reach_results() -> dict[str, Any]:
    los = load("los")
    two = load("two_step")
    forecasts = {}
    for g in ("path", "bench"):
        p = PRED / f"reach_forecasts_{g}.json"
        if p.exists():
            forecasts.update(json.loads(p.read_text())["tasks"])
    exp9 = json.loads((INPUTS / "exp9" / "results" / "los.json").read_text())
    walk = json.loads((RESULTS / "walk.json").read_text()) if (RESULTS / "walk.json").exists() else {}
    cells_out, by_task = [], defaultdict(list)
    events = []
    for t, fc in forecasts.items():
        for c in fc["c3_cells"]:
            S = c["S"]
            if t == "T2":
                e = exp9.get(S, {})
                will = e.get("will_attempted_share")
                n = (e.get("summary") or {}).get("attempted")
                k = round(will * n) if will is not None and n else None
                ci = e.get("will_ci")
                boot = (e.get("summary") or {}).get("cluster_bootstrap_ci", {}).get(f"surv_share:{S}")
                src = "exp9 LOS (not re-run)"
            else:
                rows = [r for r in los if r["task"] == t and r["condition"] == f"los:LOS({S})"]
                att = [r for r in rows if r["label"] != "invalid"]
                n, k = len(att), sum(r["label"] == S for r in att)
                catt = [r for r in corrected(rows) if r["label"] != "invalid"]
                c["will_corrected"] = (sum(r["label"] == S for r in catt) / len(catt)) if catt else None
                will = k / n if n else None
                ci = wilson(k, n)
                boot = cluster_bootstrap(att, lambda rs, S=S: (sum(r["label"] == S for r in rs) / len(rs)) if rs
                                         else None, "template", 2000, 0)
                src = "this artifact"
                banned = [m for m in TASKS[t]["catalogue"] if m != S]
                comp_ = comp(rows, banned)
                bm = [r for r in att if r["label"] in banned]
                dis = {m: {"n": sum(r["label"] == m for r in bm),
                           "disguised": sum(r["label"] == m and disguised(t, r, banned) for r in bm)} for m in banned}
                comp_c = comp(corrected(rows), banned)
                events.append({"event_type": "los", "task": t, "condition": f"LOS({S})", "banned": banned,
                               "survivor": S, "n": len(rows), **comp_, "counts_corrected": comp_c["counts"],
                               "will_corrected": c.get("will_corrected"), "will": will, "will_ci": ci,
                               "will_template_bootstrap_ci": boot, "disguise": dis,
                               "disguise_rate": (sum(v["disguised"] for v in dis.values()) / len(bm)) if bm else None})
            verdict = None
            if c["qualifies"] and will is not None:
                verdict = ("CONFIRM" if will <= C3_WILL_MAX else ("DISCONFIRM" if will >= C3_DISCONFIRM else "NEITHER"))
            cell = {**c, "will": will, "n_attempted": n, "k": k, "will_ci": ci, "will_template_bootstrap_ci": boot,
                    "will_source": src, "cell_verdict": verdict}
            cells_out.append(cell)
            by_task[t].append(cell)
    per_task = {}
    for t, cells in by_task.items():
        q = [c for c in cells if c["qualifies"] and c["will"] is not None]
        if not q:
            v = "UNTESTABLE"
        elif any(c["will"] >= C3_DISCONFIRM for c in q):
            v = "DISCONFIRMED"
        elif all(c["will"] <= C3_WILL_MAX for c in q):
            v = "CONFIRMED"
        else:
            v = "MIXED"
        per_task[t] = {"verdict": v, "n_qualifying": len(q)}
    allq = [c for c in cells_out if c["qualifies"] and c["will"] is not None]
    if not allq:
        overall = "UNTESTABLE"
    elif any(c["will"] >= C3_DISCONFIRM for c in allq):
        overall = "DISCONFIRMED"
    elif all(c["will"] <= C3_WILL_MAX for c in allq):
        overall = "CONFIRMED"
    else:
        overall = "MIXED"
    # walk will-under-veto vs prompt will
    walk_vs_prompt = {}
    for t in forecasts:
        w = walk.get(t, {})
        rungs = w.get("rungs") or []
        deep = [r for r in rungs if r["rung"] >= 3 and r.get("share", 0) >= 0.30]
        prompt_low = {c["S"]: c["will"] for c in by_task.get(t, []) if c["will"] is not None and c["will"] <= C3_WILL_MAX}
        hit = [r for r in deep if r["label"] in prompt_low]
        walk_vs_prompt[t] = {"walk_status": w.get("status"), "walk_deepest_rung": w.get("deepest_rung_reached"),
                             "walk_rungs": rungs, "rung3plus_reached_at_share_ge_0.30": deep,
                             "statement": ("the bottleneck is how a prompt is processed, not the repertoire" if hit else
                                           ("not decided at any single token; vetoes are bypassed" if
                                            w.get("status") in ("STALLED", "DEGENERATE") else "walk and prompt agree / "
                                                                                                "inconclusive"))}
    # two-step bans
    two_out = {}
    tsf = {}
    for g in ("path", "bench"):
        p = PRED / f"two_step_forecasts_{g}.json"
        if p.exists():
            tsf.update(json.loads(p.read_text())["tasks"])
    for t, f in tsf.items():
        rows = [r for r in two if r["task"] == t]
        if not rows:
            continue
        banned = f["banned"]
        comp_ = comp(rows, banned)
        att = [r for r in rows if r["label"] != "invalid"]
        nonb = [r["label"] for r in att if r["label"] not in banned]
        survivors = [m for m in TASKS[t]["catalogue"] if m not in banned]
        scores = {}
        w2 = f["WALK2"]["landing_counts"]
        if w2:
            scores["WALK2"] = log_score({k: v for k, v in w2.items() if k in survivors}, nonb, survivors)
        a = f["ASSOCIATE"]["for_R2"].get("label")
        if a and a in survivors:
            scores["ASSOCIATE"] = log_score({a: 1.0}, nonb, survivors)
        snap = sum(r["label"] == f["SNAPBACK"]["top1"] for r in att) / len(att) if att else None
        scores["SNAPBACK"] = {"snap_back_rate": snap, "top1_hit": (Counter(r["label"] for r in att).most_common(1)[0][0]
                                                                   == f["SNAPBACK"]["top1"]) if att else None}
        bm = [r for r in att if r["label"] in banned]
        dis = {m: {"n": sum(r["label"] == m for r in bm),
                   "disguised": sum(r["label"] == m and disguised(t, r, banned) for r in bm)} for m in banned}
        two_out[t] = {"banned": banned, "R2": f["R2"], **comp_, "compliance": comp_["avoidance"], "scores": scores,
                      "disguise": dis, "disguise_rate": (sum(v["disguised"] for v in dis.values()) / len(bm)) if bm
                      else None}
        events.append({"event_type": "two_step", "task": t, "condition": f"TWO({banned[0]},{banned[1]})",
                       "banned": banned, **comp_, "scores": scores, "disguise": dis})
    # walk / sham / fixed-top5 events
    for t, w in walk.items():
        if not isinstance(w, dict) or "steps" not in w:
            continue
        for s in w["steps"]:
            events.append({"event_type": "walk_step", "task": t, "step": s["step"], "round": s["round"],
                           "vetoed": s["vetoed"], "counts": s["counts"], "pass_rate": s["pass_rate"],
                           "landing": s["landing"], "reemergence": s["reemergence"], "leak_rate": s["leak_rate"]})
        sv = w.get("sham_vs_distinctive") or {}
        if "sham_ngram" in sv:
            events.append({"event_type": "sham_veto", "task": t, **sv})
    if "fixed_top5_T1" in walk:
        events.append({"event_type": "fixed_top5", "task": "T1", **walk["fixed_top5_T1"]["final_round"]})
    with (RESULTS / "reach_events.jsonl").open("w") as fh:
        for e in events:
            fh.write(json.dumps(e, default=str) + "\n")
    # post hoc sensitivity: rung 2 := the association modal answer for the default (instead of the flagged walk
    # fallback); recompute the qualifying cells from the same will values
    from reach import association_modal

    sens_cells = []
    for c in cells_out:
        t = c["task"]
        if TASKS[t]["family"] != "bench":
            sens_cells.append(dict(c))
            continue
        alt = association_modal(t, TASKS[t]["default"]).get("label")
        rung = 1 if c["S"] == TASKS[t]["default"] else (2 if c["S"] == alt else ">=3")
        q = rung == ">=3" and c["can"] is not None and c["can"] >= C3_CAN_MIN
        sens_cells.append({**c, "rung_alt": rung, "rung2_alt": alt, "qualifies_alt": q})
    sq = [c for c in sens_cells if c.get("qualifies_alt", c["qualifies"]) and c["will"] is not None]
    sens = {"cells": [{k: c.get(k) for k in ("task", "S", "rung", "rung_alt", "rung2_alt", "can", "will",
                                             "will_corrected", "qualifies", "qualifies_alt")} for c in sens_cells],
            "verdict_alt": ("UNTESTABLE" if not sq else "DISCONFIRMED" if any(c["will"] >= C3_DISCONFIRM for c in sq)
                            else "CONFIRMED" if all(c["will"] <= C3_WILL_MAX for c in sq) else "MIXED"),
            "note": "post hoc (not preregistered): the walk stalled at step 1 on T03 and T10, so their committed rung 2 "
                    "came from the flagged fallback chain; this recomputes C3 with rung 2 := the association modal "
                    "answer for the default"}
    c3 = {"cells": cells_out, "per_task": per_task, "overall": overall, "sensitivity_association_rung2": sens,
          "holm_family": "C3 reach is a SECONDARY Holm-family member (recorded for next-round pooling; no Holm "
                         "adjustment is applied inside this artifact because the verdict rule is a point-estimate rule)",
          "rule": f"CONFIRMED if every qualifying cell (rung >= 3, can >= {C3_CAN_MIN}) has will <= {C3_WILL_MAX} and "
                  f">= 1 cell exists; DISCONFIRMED if any has will >= {C3_DISCONFIRM}; else MIXED / UNTESTABLE",
          "scope": "Qwen3-8B only; bench cells from this artifact (FP8), T2 cells from exp9 (bf16, not re-run); T1 has "
                   "no LOS (C3 untestable on T1: can is low for most algorithms)"}
    write_json(RESULTS / "c3.json", c3)
    reach = {"walk_vs_prompt": walk_vs_prompt, "two_step": two_out, "los_events": [e for e in events if
                                                                                  e["event_type"] == "los"],
             "exp9_T1_multibans": json.loads((INPUTS / "exp9" / "results" / "posthoc_mix_homogeneity.json").read_text()),
             "exp9_T2_los": {S: {"will": v.get("will_attempted_share"), "can_labelled_as_requested":
                                 v.get("can_labelled_as_requested"), "can_pass_rate": v.get("can_pass_rate")}
                             for S, v in exp9.items() if isinstance(v, dict) and "will_attempted_share" in v}}
    write_json(RESULTS / "reach.json", reach)
    write_json(RESULTS / "disguise.json", {"los": {e["condition"] + "|" + e["task"]: {"disguise": e["disguise"],
                                                                                      "rate": e["disguise_rate"]}
                                                   for e in events if e["event_type"] == "los"},
                                           "two_step": {t: {"disguise": v["disguise"], "rate": v["disguise_rate"]}
                                                        for t, v in two_out.items()}})
    return {"c3": c3, "reach": reach}


def list_independence() -> dict[str, Any]:
    los, two = load("los"), load("two_step")
    out = {}
    p = PRED / "reach_forecasts_bench.json"
    if not p.exists():
        return {}
    fc = json.loads(p.read_text())["tasks"]
    for t, f in fc.items():
        li = f.get("list_independence")
        if not li:
            continue
        D, R2 = TASKS[t]["default"], f["rung_table"]["R2"]["R2"]
        groups = {}
        for g in li["groups"]:
            rows = (two if g.startswith("TWO") else los)
            cond = f"two_step:{g}" if g.startswith("TWO") else f"los:{g}"
            labs = [("D" if r["label"] == D else "R2") for r in rows if r["task"] == t and r["condition"] == cond
                    and r["label"] in (D, R2)]
            groups[g] = labs
        big = [g for g, v in groups.items() if len(v) >= 10]
        res = perm_chi2({g: v for g, v in groups.items() if v}, 10000, 0) if sum(bool(v) for v in groups.values()) >= 2 \
            else None
        shares = {g: (v.count("D") / len(v) if v else None, len(v)) for g, v in groups.items()}
        eff = None
        valid = [(g, s, n) for g, (s, n) in shares.items() if s is not None and n > 0]
        if len(valid) >= 2:
            best = None
            for i in range(len(valid)):
                for j in range(i + 1, len(valid)):
                    gi, si, ni = valid[i]
                    gj, sj, nj = valid[j]
                    d = abs(si - sj)
                    if best is None or d > best[0]:
                        best = (d, gi, gj, newcombe(round(si * ni), ni, round(sj * nj), nj))
            eff = {"max_pairwise_diff": best[0], "groups": [best[1], best[2]], "newcombe": best[3]}
        out[t] = {"D": D, "R2": R2, "groups": {g: {"D_share": s, "n": n} for g, (s, n) in shares.items()},
                  "n_groups_ge10": len(big), "descriptive_only": len(big) < 3, "test": res,
                  "prediction": li["prediction"], "prediction_met": (res["p_perm"] >= 0.05) if res else None,
                  "effect_size": eff}
    write_json(RESULTS / "list_independence.json", out)
    return out


# ------------------------------------------------------------------------------------------------ long-form
def _mech_check(rs: list[dict[str, Any]], cl: dict[str, Any], t: str) -> dict[str, Any]:
    """Mechanism-level check of the claims: among outputs whose rationale claims novelty (judge A), the share whose
    code the labeller assigns to a catalogue algorithm (the 'invention' is a known algorithm in code), the share that
    is the default, and the off-catalogue share; independent of the judges' ambiguous 'claimed_is_known' field."""
    nov = [r for r in rs if (cl.get(r["sample_id"], {}).get("A") or {}).get("claims_novelty")]
    valid = [r for r in nov if r["label"] != "invalid"]
    cat = [r for r in valid if r["label"] in TASKS[t]["catalogue"]]
    return {"n_claiming_novelty": len(nov), "n_with_valid_code": len(valid),
            "share_code_is_catalogue_algorithm": len(cat) / len(valid) if valid else None,
            "share_code_is_default": (sum(r["label"] == TASKS[t]["default"] for r in valid) / len(valid)) if valid
            else None,
            "share_code_off_catalogue": (sum(r["label"] == "other" for r in valid) / len(valid)) if valid else None,
            "share_no_code": (len(nov) - len(valid)) / len(nov) if nov else None}


def longform_results() -> dict[str, Any]:
    rows = load("longform")
    audit = json.loads((RESULTS / "novelty_audit.json").read_text()) if (RESULTS / "novelty_audit.json").exists() else {}
    novel_ids = {r["sample_id"] for r in audit.get("records", []) if r.get("final_class") == "NOVEL ALGORITHM"}
    claims = json.loads((RESULTS / "claims.json").read_text()) if (RESULTS / "claims.json").exists() else {}
    cl = {r["sample_id"]: r for r in claims.get("records", [])}
    cells = defaultdict(list)
    for r in rows:
        cells[(r["task"], r["prompt_id"], "on" if r["thinking"] else "off", r["engine_dtype"])].append(r)
    out = {}
    for (t, lf, th, dt), rs in sorted(cells.items()):
        c = comp(rs, [])
        n_novel = sum(r["sample_id"] in novel_ids for r in rs)
        n_ok = sum(r["passed"] for r in rs)
        cr = [cl[r["sample_id"]]["A"] for r in rs if r["sample_id"] in cl and cl[r["sample_id"]].get("A")]
        claims_novel = [x for x in cr if x.get("claims_novelty")]
        D = TASKS[t]["default"]
        prose_default = sum(1 for r in rs if r["sample_id"] in cl and (cl[r["sample_id"]].get("A") or {}).get(
            "claims_novelty") and r["label"] == D)
        rec = {**c, "N": len(rs), "n_correct": n_ok, "novel_count": n_novel,
               "novel_rate_upper95": exact_upper(n_novel, len(rs)),
               "novel_rate_upper95_among_correct": exact_upper(n_novel, n_ok) if n_ok else None,
               "mean_new_tokens": sum((r.get("n_new_tokens") or 0) for r in rs) / len(rs),
               "mean_rationale_words": sum(r.get("rationale_words") or 0 for r in rs) / len(rs),
               "extraction": dict(Counter(r.get("extract_method") for r in rs)),
               "truncated_share": sum(r.get("finish_reason") == "length" for r in rs) / len(rs),
               "claims": {"mechanism_check": _mech_check(rs, cl, t),
                          "n_with_claim_record": len(cr),
                          "share_claiming_novelty": len(claims_novel) / len(cr) if cr else None,
                          "share_of_claimed_inventions_known": (sum(bool(x.get("claimed_is_known")) for x in claims_novel)
                                                                / len(claims_novel)) if claims_novel else None,
                          "claim_code_consistency": dict(Counter(x.get("code_implements_claim") for x in cr)),
                          "novelty_in_prose_default_in_code": prose_default / len(rs)}}
        if th == "on":
            comp_runs = [r for r in rs if r.get("thinking_complete")]
            forced = [r for r in rs if not r.get("thinking_complete")]
            rec["thinking"] = {"completion_rate": len(comp_runs) / len(rs),
                               "mean_thinking_tokens": sum(r.get("thinking_tokens") or 0 for r in rs) / len(rs),
                               "mean_answer_tokens": sum(r.get("answer_tokens") or 0 for r in rs) / len(rs),
                               "pass_rate_complete": (sum(r["passed"] for r in comp_runs) / len(comp_runs))
                               if comp_runs else None,
                               "pass_rate_forced_stop": (sum(r["passed"] for r in forced) / len(forced)) if forced
                               else None, "n_complete": len(comp_runs), "n_forced_stop": len(forced)}
        out[f"{t}|{lf}|think_{th}|{dt}"] = rec
    write_json(RESULTS / "longform.json", out)
    # bf16 vs FP8 cross-check on LF1 thinking-off T2
    a = [r for r in rows if r["task"] == "T2" and r["prompt_id"] == "LF1" and not r["thinking"] and
         r["engine_dtype"] == "bf16"]
    b = [r for r in rows if r["task"] == "T2" and r["prompt_id"] == "LF1" and not r["thinking"] and
         r["engine_dtype"] == "fp8"]
    if a and b:
        ka, kb = sum(r["passed"] for r in a), sum(r["passed"] for r in b)
        xc = {"n_bf16": len(a), "n_fp8": len(b), "composition_bf16": dict(Counter(r["label"] for r in a)),
              "composition_fp8": dict(Counter(r["label"] for r in b)),
              "js": js_null([r["label"] for r in a], [r["label"] for r in b], 2000, 0),
              "pass_rate_bf16": ka / len(a), "pass_rate_fp8": kb / len(b), "pass_diff": newcombe(ka, len(a), kb, len(b)),
              "mean_tokens_bf16": sum(r["n_new_tokens"] or 0 for r in a) / len(a),
              "mean_tokens_fp8": sum(r["n_new_tokens"] or 0 for r in b) / len(b),
              "rationale_words_bf16": sum(r["rationale_words"] for r in a) / len(a),
              "rationale_words_fp8": sum(r["rationale_words"] for r in b) / len(b),
              "correct_other_bf16": sum(r["label"] == "other" and r["passed"] for r in a),
              "correct_other_fp8": sum(r["label"] == "other" and r["passed"] for r in b)}
    else:
        xc = {"status": "NOT_RUN", "n_bf16": len(a), "n_fp8": len(b)}
    write_json(RESULTS / "fp8_crosscheck.json", xc)
    return out


# ------------------------------------------------------------------------------------------------ audit merge
def merge_audit() -> dict[str, Any]:
    pj = RESULTS / "novelty_audit_judges.json"
    if not pj.exists():
        return {}
    judges = json.loads(pj.read_text())["records"]
    mp = RESULTS / "manual_audit.json"
    manual = json.loads(mp.read_text())["records"] if mp.exists() else {}
    recs = []
    for r in judges:
        m = manual.get(r["sample_id"]) or manual.get(r["code_sha256"]) or {}
        a, b = r["judge_A"].get("class"), r["judge_B"].get("class")
        final = m.get("final_class")
        if final is None:
            final = a if a == b else None
        novel_ok = final == "NOVEL ALGORITHM" and m.get("final_class") == "NOVEL ALGORITHM"
        recs.append({**{k: v for k, v in r.items() if k not in ("raw_A", "raw_B")}, "manual": m,
                     "final_class": final if (final != "NOVEL ALGORITHM" or novel_ok) else "UNRESOLVED",
                     "rater_mode": "two judges + manual" if m else "two judges only"})
    A = [r["judge_A"].get("class") or "NONE" for r in recs]
    B = [r["judge_B"].get("class") or "NONE" for r in recs]
    F = [r["final_class"] or "NONE" for r in recs]
    corr = [r for r in recs if r["audit_role"] == "correct_other"]
    out = {"n": len(recs), "n_correct_other": len(corr), "kappa_A_B": cohen_kappa(A, B),
           "kappa_A_final": cohen_kappa(A, F), "kappa_B_final": cohen_kappa(B, F),
           "final_classes_correct_other": dict(Counter(r["final_class"] for r in corr)),
           "final_classes_all": dict(Counter(r["final_class"] for r in recs)),
           "novel": [{"sample_id": r["sample_id"], "task": r["task"], "arm": r["arm"], "code_sha256": r["code_sha256"]}
                     for r in recs if r["final_class"] == "NOVEL ALGORITHM"],
           "records": recs}
    write_json(RESULTS / "novelty_audit.json", out)
    return out


def run_all() -> dict[str, Any]:
    res = {"can": can_results(), "walk": walk_results()}
    res.update(reach_results())
    res["list_independence"] = list_independence()
    res["audit"] = merge_audit()
    res["longform"] = longform_results()
    return res


if __name__ == "__main__":
    from config import setup_logging

    setup_logging("analysis")
    run_all()
