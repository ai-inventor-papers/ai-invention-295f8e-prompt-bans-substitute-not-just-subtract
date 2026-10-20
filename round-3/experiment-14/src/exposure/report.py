"""Stage 3 (CPU): per-sample table, per-(Y, arm) statistics, the frozen C1 analysis (analysis/), its sensitivities,
C1-exposure, placebos, the descriptive reports of plan 4.6, figures and method_out.json (exp_gen_sol_out)."""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict

import numpy as np
from loguru import logger

from analysis import c1
from analysis import events as EV

from .core import (COMMIT_LOG, DATA, FIGS, LOGS, MODEL_ID, PRED, RESULTS, ROOT, TASK_ORDER, deviation, load_spec,
                   read_json, read_jsonl, sha256_text, wilson, write_json)

CONDITION = {"copy": "copy_twin", "veto": "signature_veto", "named": "ban_named", "unnamed": "ban_unnamed",
             "baseline": "baseline", "W1": "ban_named_template", "W2": "ban_named_template",
             "W3": "ban_named_template", "W4": "ban_named_template"}


def _finite(x):
    return x is not None and not (isinstance(x, float) and (math.isnan(x) or math.isinf(x)))


def build_samples() -> list[dict]:
    from bench_copy.common.harness import extract_code
    gens = read_jsonl(DATA / "generations.jsonl")
    labs = {r["sample_id"]: r for r in read_jsonl(DATA / "labels_combined.jsonl")}
    rows, missing = [], 0
    for g in gens:
        lab = labs.get(g["sample_id"])
        if lab is None:
            missing += 1
            continue
        code = extract_code(g["text"])
        rows.append({"model": MODEL_ID, "task": g["task"], "condition": CONDITION.get(g["arm"], g["arm"]),
                     "template": g.get("template"), "arm": g["arm"], "round": g["round"], "Y": g["Y"],
                     "p_index": g["p_index"], "sample_id": g["sample_id"], "seed": g["seed"],
                     "prompt_sha256": g["prompt_sha256"], "label": lab["label"], "labeller_source": lab["labeller_source"],
                     "passed": bool(lab.get("passed")), "finish_reason": g["finish_reason"],
                     "n_new_tokens": g["n_new_tokens"], "code_sha256": lab["code_sha256"], "code": code,
                     "ast_label": lab.get("ast_label"), "runtime_label": lab.get("runtime_label"),
                     "judge_label": lab.get("judge_label"), "judge_skipped": bool(lab.get("judge_skipped")),
                     "veto_ngrams": g.get("veto"), "gen_utc": g.get("gen_utc")})
    if missing:
        deviation(f"{missing} generated programs have no label row (labelling failure); they are excluded")
    with (DATA / "samples.jsonl").open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    logger.info(f"samples.jsonl: {len(rows)} rows")
    return rows


def commit_sha(kind: str) -> str | None:
    recs = [r for r in read_jsonl(COMMIT_LOG) if r["kind"] == kind]
    return recs[-1]["sha256"] if recs else None


def meta_and_forecasts():
    elig = read_json(PRED / "eligibility.json")
    e_by = {f"{e['task']}:{e['Y']}": e for e in elig["eligible"]}
    shown = defaultdict(list)
    for r in read_jsonl(PRED / "shown_programs.jsonl"):
        shown[r["key"]].append(r)
    ngr = read_json(PRED / "ngrams.json")
    prox = read_json(PRED / "proximity.json")
    lad = read_json(PRED / "ladder.json")
    asc = read_json(PRED / "associate.json")
    sub = read_json(PRED / "subtract_in_context.json")
    flagged_tasks = set(elig.get("labeller_flagged_tasks", []))
    meta, fc, prox_tok = {}, {}, {}
    for key in shown:
        t, y = key.split(":")
        e = e_by[key]
        survivors = [m for m in elig["tasks"][t]["modes"] if m != y]
        flags = []
        if ngr[key]["n_ref_lt5"]:
            flags.append("n_ref_lt5")
        if len(shown[key]) < 5:
            flags.append("n_shown_lt5")
        if sub[key]["undefined"]:
            flags.append("subtract_undefined")
        if sub[key]["not_carried_by_surface_tokens"]:
            flags.append("not_carried_by_surface_tokens")
        if e["associate_tie"]:
            flags.append("associate_tie")
        if ngr[key]["default_coveto"]:
            flags.append("default_coveto")
        if ngr[key]["associate_coveto"]:
            flags.append("associate_coveto")
        if t in flagged_tasks:
            flags.append("labeller_recheck_flag")
        meta[key] = {"task": t, "Y": y, "default": e["default"], "survivors": survivors, "associate": asc[key],
                     "n_pY": len(shown[key]), "veto_round_used": sub[key]["round_used"],
                     "coveto_modes": ngr[key]["coveto_modes"], "flags": flags, "priority": e["priority"]}
        fc[key] = {"SUBTRACT": sub[key]["distribution"], "LADDER": lad[key], "ASSOCIATE": asc[key],
                   "PROXIMITY": prox[key]["distribution"]}
        prox_tok[key] = prox[key]["distribution_token_distance"]
    return meta, fc, prox_tok, sub


def _events_jsonable(evs: list[dict]) -> list[dict]:
    keep = ["model", "task", "event_type", "banned", "n_attempts", "avoidance", "avoidance_ci95", "n_nonY", "gate_pass",
            "landing_counts", "correct_counts", "other_share", "forecasts", "top1", "logscore", "hit", "modal",
            "disagreeing", "unaimed", "commit_sha256", "Y", "default", "associate", "n_pY", "veto_round_used", "coveto",
            "flags", "priority", "hill_cc", "pass_rate", "default_share", "survivors"]
    return [{k: e.get(k) for k in keep} for e in evs]


def arm_table(samples: list[dict], meta: dict) -> dict:
    by = defaultdict(list)
    for r in samples:
        if r["Y"]:
            by[(f"{r['task']}:{r['Y']}", r["arm"], r["round"])].append(r)
    out = {}
    for (key, arm, rnd), rows in sorted(by.items()):
        m = meta[key]
        st = EV.arm_stats(rows, m["Y"], m["survivors"], m["default"])
        out.setdefault(key, {})[f"{arm}" + (f"_r{rnd}" if arm == "veto" else "")] = st
    return out


def g_test(landing_by_program: dict) -> dict:
    from scipy.stats import chi2_contingency
    progs = [p for p, c in landing_by_program.items() if sum(c.values()) > 0]
    labs = sorted({l for p in progs for l in landing_by_program[p]})
    if len(progs) < 2 or len(labs) < 2:
        return {"testable": False}
    tab = np.array([[landing_by_program[p].get(l, 0) for l in labs] for p in progs])
    try:
        g, p, dof, _ = chi2_contingency(tab, lambda_="log-likelihood")
        return {"testable": True, "G": float(g), "dof": int(dof), "p": float(p), "n_programs": len(progs)}
    except ValueError as e:
        return {"testable": False, "error": str(e)}


def alias_regex(task: str, y: str) -> re.Pattern:
    spec = load_spec(task)
    names = list(spec["aliases"].get(y, [])) + [c["display_name"] for c in spec["catalogue"] if c["mode"] == y]
    names = [re.sub(r"^(a|an|the)\s+", "", n.lower()) for n in names]
    parts = [re.escape(n).replace(r"\ ", r"[\s_\-]*").replace(r"\-", r"[\s_\-]*") for n in names if len(n) >= 3]
    return re.compile(r"(" + "|".join(sorted(parts, key=len, reverse=True)) + r")")


def other_reports(samples: list[dict], meta: dict, arms: dict, sub: dict) -> dict:
    from bench_copy.common.scrub import text_has_alias
    rep = {"copy_rate": {}, "default_share_by_arm": {}, "named_vs_unnamed": {}, "disguise": {}, "heterogeneity": {},
           "veto_diagnostics": {}, "template_arm": {}}
    by = defaultdict(list)
    for r in samples:
        if r["Y"]:
            by[(f"{r['task']}:{r['Y']}", r["arm"], r["round"])].append(r)
    for key, m in meta.items():
        a = arms.get(key, {})
        cp = a.get("copy")
        if cp:
            rep["copy_rate"][key] = {"Y_share": cp["Y_share"], "ci95": cp["Y_share_ci95"], "n_attempts": cp["n_attempts"]}
        fr = m["veto_round_used"] or max([int(k.split("_r")[1]) for k in a if k.startswith("veto_r")] or [1])
        last_r = max([int(k.split("_r")[1]) for k in a if k.startswith("veto_r")] or [1])
        rep["default_share_by_arm"][key] = {arm: a[k]["default_share"] for arm, k in
                                            [("copy", "copy"), ("veto_final", f"veto_r{last_r}"), ("named", "named"),
                                             ("unnamed", "unnamed")] if k in a}
        nr, ur = by.get((key, "named", 0), []), by.get((key, "unnamed", 0), [])
        if nr and ur:
            def cl(rows):
                d = defaultdict(list)
                for r in rows:
                    lab = c1.normalise_label(r["label"], m["Y"], m["survivors"])
                    if lab is not None and lab != m["Y"]:
                        d[r["p_index"]].append(lab)
                return [d[k] for k in sorted(d)]
            ca, cb = cl(nr), cl(ur)
            la, lb = Counter(x for c in ca for x in c), Counter(x for c in cb for x in c)
            if la and lb:
                nul = c1.js_null(ca, cb, n_null=2000, seed=1)
                js = c1.js_divergence(la, lb)
                ma, mb = c1.modal(la), c1.modal(lb)
                rep["named_vs_unnamed"][key] = {"named_modal": ma, "unnamed_modal": mb, "modal_equal": bool(set(ma) & set(mb)),
                                                "js": js, "js_null_q95": nul["q95"], "null_level": nul["level"],
                                                "js_consistent": js <= nul["q95"]}
        ar = alias_regex(m["task"], m["Y"])
        y_named = [r for r in nr if r["label"] == m["Y"] and r["code"]]
        if y_named:
            rep["disguise"][key] = {"n_Y_named": len(y_named),
                                    "share_no_alias_of_Y": sum(1 for r in y_named if not ar.search(r["code"].lower())) / len(y_named),
                                    "share_no_alias_any_mode": sum(1 for r in y_named if not text_has_alias(r["code"])) / len(y_named)}
        if "named" in a:
            rep["heterogeneity"][key] = {"named": g_test(a["named"]["landing_by_program"]),
                                         "copy": g_test(a["copy"]["landing_by_program"]) if "copy" in a else None}
        vk = [k for k in a if k.startswith("veto_r")]
        if vk:
            rep["veto_diagnostics"][key] = {
                "rounds_run": len(vk), "round_used": m["veto_round_used"],
                "reemerge_by_round": {k: a[k]["Y_share"] for k in sorted(vk)},
                "pass_rate_by_round": {k: a[k]["pass_rate"] for k in sorted(vk)},
                "pass_rate_copy": a.get("copy", {}).get("pass_rate"),
                "pass_rate_cost_final": (a.get("copy", {}).get("pass_rate", float("nan")) - a[f"veto_r{last_r}"]["pass_rate"]),
                "invalid_share_final": a[f"veto_r{last_r}"]["n_invalid"] / max(a[f"veto_r{last_r}"]["n_programs"], 1),
                "not_carried_by_surface_tokens": sub[key]["not_carried_by_surface_tokens"],
                "subtract_undefined": sub[key]["undefined"]}
        for w in ("W1", "W2", "W3", "W4"):
            if w in a:
                rep["template_arm"].setdefault(key, {})[w] = {"avoidance": a[w]["avoidance"], "n_attempts": a[w]["n_attempts"],
                                                             "modal_nonY": a[w]["modal_nonY"], "landing": a[w]["landing_counts"]}
    cr = [v["Y_share"] for v in rep["copy_rate"].values() if _finite(v["Y_share"])]
    rep["copy_rate_summary"] = {"mean": float(np.mean(cr)) if cr else None, "median": float(np.median(cr)) if cr else None,
                                "n_Y_below_0.2": sum(1 for x in cr if x < 0.2), "n": len(cr)}
    ag = [v["modal_equal"] for v in rep["named_vs_unnamed"].values()]
    rep["named_vs_unnamed_summary"] = {"n": len(ag), "modal_equal_share": (sum(ag) / len(ag)) if ag else None,
                                       "js_consistent_share": (sum(v["js_consistent"] for v in rep["named_vs_unnamed"].values()) / len(ag)) if ag else None}
    return rep


def three_family(events: list[dict]) -> dict:
    """EXPLORATORY (not pre-registered): LADDER vs ASSOCIATE vs PROXIMITY on gated events where these three disagree.
    Motivation: SUBTRACT is undefined (uniform) for most Y, which makes almost every event 'disagreeing' through
    SUBTRACT's tie alone."""
    fams = ["LADDER", "ASSOCIATE", "PROXIMITY"]
    gated = [e for e in events if e["gate_pass"]]
    sel = [e for e in gated if len({tuple(sorted(e["top1"][f])) for f in fams}) > 1]
    rule = c1.advance_rule(sel, families=fams)
    pairs = [("LADDER", "ASSOCIATE"), ("LADDER", "PROXIMITY"), ("ASSOCIATE", "PROXIMITY")]
    tests = []
    for a, b in pairs:
        d = [e["logscore"][a] - e["logscore"][b] for e in sel]
        w = c1.wilcoxon_two_sided(d) if d else {"p": 1.0, "n_nonzero": 0}
        tests.append({"pair": f"{a}-{b}", "n": len(d), "mean_diff": float(np.mean(d)) if d else None, "p": w["p"],
                      "n_nonzero": w["n_nonzero"],
                      "ci95_task_cluster": c1.cluster_bootstrap_mean(d, [e["task"] for e in sel], n_boot=2000) if d else None})
    for t, q in zip(tests, c1.holm([t["p"] for t in tests])):
        t["p_holm"] = q
    return {"n_gated": len(gated), "n_three_family_disagreeing": len(sel), "wins": rule["wins"],
            "advancing": rule["advancing"],
            "hit_rate_gated": {f: (float(np.mean([e["hit"][f] for e in gated])) if gated else None) for f in fams},
            "hit_rate_disagreeing": {f: (float(np.mean([e["hit"][f] for e in sel])) if sel else None) for f in fams},
            "modal_is_default_share_gated": (float(np.mean([e["default"] in e["modal"] for e in gated])) if gated else None),
            "modal_is_other_share_gated": (float(np.mean(["other" in e["modal"] for e in gated])) if gated else None),
            "tests": tests}


def baseline_check(samples: list[dict]) -> dict:
    elig = read_json(PRED / "eligibility.json")
    out = {}
    for t in TASK_ORDER:
        labs = [r["label"] for r in samples if r["arm"] == "baseline" and r["task"] == t]
        att = [x for x in labs if x != "invalid"]
        d = elig["tasks"][t]["default"]
        k = sum(1 for x in att if x == d)
        out[t] = {"default": d, "n": len(labs), "n_attempts": len(att), "default_share": k / len(att) if att else None,
                  "ci95": wilson(k, len(att)), "labels": dict(Counter(labs))}
    return out


def analyze(args) -> None:
    samples = build_samples()
    meta, fc, prox_tok, sub = meta_and_forecasts()
    c2 = commit_sha("COMMIT2")
    evs = EV.build_events(samples, meta, fc, arms=("named", "unnamed"), model=MODEL_ID, commit_sha256=c2)
    named = [e for e in evs if e["arm"] == "named"]
    unnamed = [e for e in evs if e["arm"] == "unnamed"]
    res_named = c1.run_c1(named)
    res_unnamed = c1.run_c1(unnamed)
    logger.info(f"C1 NAMED: {res_named['n_gated']} gated, {res_named['n_gated_disagreeing']} gated disagreeing; wins "
                f"{res_named['rule']['wins']} -> {res_named['branch']}")
    logger.info(f"C1 UNNAMED (descriptive): {res_unnamed['n_gated_disagreeing']} gated disagreeing; wins "
                f"{res_unnamed['rule']['wins']} -> {res_unnamed['branch']}")
    sens = EV.sensitivities(named, fc, prox_tok)
    sens["correct_only"] = EV.correct_only(samples, meta, fc, c2)
    sens["exclude_subtract_undefined_or_not_surface"] = EV._summ(c1.run_c1(
        [e for e in named if not ({"subtract_undefined", "not_carried_by_surface_tokens"} & set(e["flags"]))], n_boot=2000))
    sens["exclude_labeller_flagged_tasks"] = EV._summ(c1.run_c1(
        [e for e in named if "labeller_recheck_flag" not in e["flags"]], n_boot=2000))
    exploratory = {"three_family_named": three_family(named), "three_family_unnamed": three_family(unnamed)}
    logger.info(f"EXPLORATORY 3-family (NAMED): {exploratory['three_family_named']['n_three_family_disagreeing']} events, "
                f"wins {exploratory['three_family_named']['wins']}, hit rates {exploratory['three_family_named']['hit_rate_gated']}")
    vr_used = {k: m["veto_round_used"] for k, m in meta.items()}
    expo = c1.c1_exposure(EV.exposure_items(named, samples, vr_used))
    logger.info(f"C1-exposure: {expo['n_events']} events -> {expo['verdict']}")
    plac = {"rotation": c1.placebo_rotation(named), "label_permutation": c1.placebo_permutation(named, n_draws=200, seed=7)}
    plac["rotation_unnamed"] = c1.placebo_rotation(unnamed)
    arms = arm_table(samples, meta)
    rep = other_reports(samples, meta, arms, sub)
    base = baseline_check(samples)
    # hit rates per family on gated named events
    gated = [e for e in named if e["gate_pass"]]
    hits = {f: (float(np.mean([e["hit"][f] for e in gated])) if gated else None) for f in c1.FAMILIES}
    hits_dis = {f: (float(np.mean([e["hit"][f] for e in gated if e["disagreeing"]])) if any(e["disagreeing"] for e in gated) else None)
                for f in c1.FAMILIES}
    mean_ls = {f: (float(np.mean([e["logscore"][f] for e in gated if e["disagreeing"]])) if any(e["disagreeing"] for e in gated) else None)
               for f in c1.FAMILIES}
    with (RESULTS / "c1_events.jsonl").open("w") as f:
        for e in _events_jsonable(evs):
            f.write(json.dumps(e) + "\n")
    correct_other = [{"sample_id": r["sample_id"], "task": r["task"], "Y": r["Y"], "arm": r["arm"], "code": r["code"]}
                     for r in samples if r["label"] == "other" and r["passed"]]
    with (RESULTS / "correct_other_programs.jsonl").open("w") as f:
        for r in correct_other:
            f.write(json.dumps(r) + "\n")
    spend = sum((r.get("cost") or 0.0) for r in read_jsonl(LOGS / "openrouter_spend.jsonl"))
    n_judge_calls = len(read_jsonl(LOGS / "openrouter_spend.jsonl"))
    tm = read_json(RESULTS / "timings.json")
    from bench_copy.common.commit import verify_chain
    chain_ok = verify_chain(COMMIT_LOG)
    c2_ts = [r["ts"] for r in read_jsonl(COMMIT_LOG) if r["kind"] == "COMMIT2"]
    ban_after = None
    if c2_ts:
        import datetime as dt
        t2 = dt.datetime.strptime(c2_ts[-1], "%Y-%m-%dT%H:%M:%S%z")
        bans = [r for r in samples if r["arm"] in ("named", "unnamed", "W1", "W2", "W3", "W4")]
        ban_after = all(dt.datetime.strptime(r["gen_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc) > t2
                        for r in bans if r.get("gen_utc"))
    summary = {
        "model": MODEL_ID, "stratum": "Qwen exposure stratum",
        "n_samples": len(samples), "n_by_arm": dict(Counter(r["arm"] for r in samples)),
        "n_Y": len(meta), "n_priority_Y": sum(m["priority"] for m in meta.values()),
        "c1_named": {k: res_named[k] for k in ("n_events_total", "n_gated", "n_gated_disagreeing", "rule", "tests",
                                               "unaimed_share", "branch", "margins")},
        "c1_unnamed": {k: res_unnamed[k] for k in ("n_events_total", "n_gated", "n_gated_disagreeing", "rule", "tests",
                                                   "unaimed_share", "branch")},
        "hit_rate_gated_named": hits, "hit_rate_gated_disagreeing_named": hits_dis,
        "mean_logscore_gated_disagreeing_named": mean_ls,
        "sensitivities": sens, "c1_exposure": expo, "placebos": plac, "exploratory_not_preregistered": exploratory,
        "openrouter_spend_usd": spend, "openrouter_judge_calls": n_judge_calls,
        "judge_skipped": sum(r["judge_skipped"] for r in samples),
        "labeller_sources": dict(Counter(r["labeller_source"] for r in samples)),
        "chain_verifies": chain_ok, "all_ban_samples_after_commit2": ban_after,
        "commit1_sha256": commit_sha("COMMIT1"), "commit2_sha256": c2,
        "gpu_hours": sum(v.get("gpu_s", 0) for v in tm.values()) / 3600, "timings": tm,
        "advance_rule_null_calibration": read_json(RESULTS / "advance_rule_null_calibration.json")
        if (RESULTS / "advance_rule_null_calibration.json").exists() else None,
    }
    write_json(RESULTS / "c1_summary.json", summary)
    write_json(RESULTS / "arm_stats.json", arms)
    write_json(RESULTS / "other_reports.json", rep)
    write_json(RESULTS / "bf16_baseline_check_final.json", base)
    from .figures import make_figures
    try:
        make_figures(samples, meta, fc, arms, named, res_named)
    except Exception as e:  # noqa: BLE001 - figures are secondary; never lose the analysis to a plotting error
        logger.error(f"figure generation failed: {e}")
    build_method_out(samples, evs, meta, summary, rep, base, arms)


def build_method_out(samples, evs, meta, summary, rep, base, arms) -> None:
    shown = defaultdict(list)
    for r in read_jsonl(PRED / "shown_programs.jsonl"):
        shown[r["key"]].append(r["code_sha256"])
    prompts = {r["prompt_key"]: r for r in read_jsonl(PRED / "prompts.jsonl")}
    ex_events = []
    for e in evs:
        key = f"{e['task']}:{e['Y']}"
        wording = prompts[f"{key}:{e['arm']}:p0"]["user_text"].split("\n\n")
        w = next((s for s in wording if s.startswith("Write a correct solution")), "")
        inp = json.dumps({"task": e["task"], "banned_Y": e["Y"], "wording": w, "shown_program_sha256": shown[key]})
        ex = {"input": inp, "output": "|".join(e["modal"]) if e["modal"] else "none",
              "predict_subtract": "|".join(e["top1"]["SUBTRACT"]), "predict_ladder": "|".join(e["top1"]["LADDER"]),
              "predict_associate": "|".join(e["top1"]["ASSOCIATE"]), "predict_proximity": "|".join(e["top1"]["PROXIMITY"]),
              "metadata_event_type": e["event_type"], "metadata_gate_pass": e["gate_pass"],
              "metadata_disagreeing": e["disagreeing"], "metadata_avoidance": e["avoidance"],
              "metadata_n_attempts": e["n_attempts"], "metadata_n_nonY": e["n_nonY"],
              "metadata_landing_counts": e["landing_counts"], "metadata_correct_counts": e["correct_counts"],
              "metadata_logscore": e["logscore"], "metadata_hit": e["hit"], "metadata_default": e["default"],
              "metadata_priority": e["priority"], "metadata_flags": e["flags"], "metadata_coveto": e["coveto"],
              "metadata_veto_round_used": e["veto_round_used"], "metadata_n_pY": e["n_pY"],
              "metadata_forecasts": e["forecasts"], "metadata_hill_cc": e["hill_cc"], "metadata_pass_rate": e["pass_rate"]}
        ex_events.append(ex)
    ex_samples = []
    for r in samples:
        ex_samples.append({"input": json.dumps({"prompt_sha256": r["prompt_sha256"], "task": r["task"], "Y": r["Y"],
                                                "arm": r["arm"], "round": r["round"], "p_index": r["p_index"]}),
                           "output": r["code"] or "",
                           "predict_label": r["label"],
                           "metadata_sample_id": r["sample_id"], "metadata_condition": r["condition"],
                           "metadata_template": r["template"], "metadata_seed": r["seed"], "metadata_passed": r["passed"],
                           "metadata_labeller_source": r["labeller_source"], "metadata_finish_reason": r["finish_reason"],
                           "metadata_n_new_tokens": r["n_new_tokens"], "metadata_code_sha256": r["code_sha256"]})
    meta_out = {
        "title": "Show a solution, ban it, see what replaces it (exposure-ban experiment, Qwen3-8B bf16)",
        "method": "exposure bans (NAMED / UNNAMED) scored against four committed forecast families: SUBTRACT-IN-CONTEXT "
                  "(iterated persistent signature veto under the copy-twin prompt), LADDER (default), ASSOCIATE (frozen "
                  "'standard alternative to Y'), PROXIMITY (Zhang-Shasha nearest survivor)",
        "baselines": "COPY twin (same prefix, no prohibition), UNNAMED generic 'different algorithm', the ban-free signature "
                     "veto counterfactual and the context-free default (bf16 baseline check)",
        "summary": summary, "other_reports": rep, "bf16_baseline_check": base,
        "deviations": [r["text"] for r in read_jsonl(RESULTS / "deviations.jsonl")],
        "veto_rounds": read_json(PRED / "veto_rounds.json"), "smoke_tests": read_json(RESULTS / "smoke_tests.json"),
        "labeller_recheck": read_json(RESULTS / "labeller_recheck.json"),
        "bench_verification": read_json(RESULTS / "bench_verification.json"),
    }
    out = {"metadata": meta_out, "datasets": [{"dataset": "exposure_events", "examples": ex_events},
                                              {"dataset": "exposure_samples", "examples": ex_samples}]}
    (ROOT / "method_out.json").write_text(json.dumps(out, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    logger.info(f"method_out.json: {len(ex_events)} events, {len(ex_samples)} samples")
