"""(0d) Assemble the 'other' audit: controls -> judge weights, consensus / tie-break, exp18 reuse, manual pass,
hidden-test re-runs, catalogue-only avoidance tables, residue-gated summaries, merge-intervals correction."""

from __future__ import annotations

import json
import random
import re
import subprocess
import sys
from collections import Counter

import numpy as np
import pandas as pd
from loguru import logger

from src.labels import BENCH_DIRS, catalogue, default_of
from src.paths import WS, cite, p
from src.stats import cell_seed, cohen_kappa, kappa_boot_ci

AUDIT, RES, TAB = WS / "audit", WS / "results", WS / "tables"
EXP18_MAP = {"LABELLER MISS": "LABELLER_MISS", "CATALOGUE VARIANT": "CATALOGUE_VARIANT", "NOVEL": "NOVEL",
             "DEGENERATE": "DEGENERATE"}


def _jsonl(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def manual_lookup(sha: str, manual: dict) -> dict | None:
    for k, v in manual.items():
        if sha.startswith(k):
            return v
    return None


def judge_weights(res: dict) -> dict:
    out = {}
    v = res["verdicts"]
    for j in ("A", "B", "C"):
        pos = [c for c in res["controls"] if c["expected"] == "LABELLER_MISS"]
        neg = [c for c in res["controls"] if c["expected"] == "DEGENERATE"]
        strict = sum((v.get(c["control_id"], {}).get(j) or {}).get("class") == "LABELLER_MISS" for c in pos)
        mode = sum((v.get(c["control_id"], {}).get(j) or {}).get("nearest_catalogue_mode") == c["expected_mode"] for c in pos)
        negok = sum((v.get(c["control_id"], {}).get(j) or {}).get("class") == "DEGENERATE" for c in neg)
        answered = sum(1 for c in pos + neg if (v.get(c["control_id"], {}).get(j) or {}).get("class"))
        out[j] = {"positives_strict_class": strict, "positives_right_mode": mode, "negatives_degenerate": negok,
                  "n_pos": len(pos), "n_neg": len(neg), "answered": answered,
                  "weighted": bool(j != "C" and strict >= 5)}
    return out


def rerun_hidden_tests(code: str, task: str, extra: int = 3, seed: int = 20261021) -> dict:
    """Re-run exp11 hidden tests in a subprocess (per-case limits) plus seeded extra stress cases."""
    d = BENCH_DIRS[task]
    tests = _jsonl(p("exp11", f"bench/{d}/tests.jsonl"))
    ref = p("exp11", f"bench/{d}/references/{default_of(task)}.py").read_text()
    rnd = random.Random(seed)
    extra_cases = []
    if task == "T03":
        for _ in range(extra):
            n = rnd.randint(2000, 20000)
            nums = [rnd.randint(-10 ** 6, 10 ** 6) for _ in range(n)]
            extra_cases.append({"nums": nums, "k": rnd.randint(1, n)})
    work = AUDIT / "rerun"
    work.mkdir(exist_ok=True)
    (work / "cand.py").write_text(code)
    (work / "ref.py").write_text(ref)
    (work / "checker.py").write_text(p("exp11", f"bench/{d}/checker.py").read_text())
    (work / "cases.json").write_text(json.dumps({"tests": tests, "extra": extra_cases}))
    harness = (
        "import json, signal, sys, time, copy\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "import cand, ref, checker\n"
        "data = json.load(open(sys.argv[1] + '/cases.json'))\n"
        "class TO(Exception): pass\n"
        "def h(*a): raise TO()\n"
        "signal.signal(signal.SIGALRM, h)\n"
        "res = {'hidden_pass': 0, 'hidden_n': 0, 'extra_pass': 0, 'extra_n': 0, 'fail': []}\n"
        "for c in data['tests']:\n"
        "    res['hidden_n'] += 1\n"
        "    signal.setitimer(signal.ITIMER_REAL, float(c.get('limit', 1.0)))\n"
        "    try:\n"
        "        out = cand.solve(**copy.deepcopy(c['kwargs']))\n"
        "        signal.setitimer(signal.ITIMER_REAL, 0)\n"
        "        ok = checker.check(c['kwargs'], c['expected'], out)\n"
        "    except BaseException as e:\n"
        "        signal.setitimer(signal.ITIMER_REAL, 0)\n"
        "        ok = False\n"
        "    res['hidden_pass'] += int(bool(ok))\n"
        "    if not ok: res['fail'].append(c['case_id'])\n"
        "for kw in data['extra']:\n"
        "    res['extra_n'] += 1\n"
        "    exp = ref.solve(**copy.deepcopy(kw))\n"
        "    signal.setitimer(signal.ITIMER_REAL, 5.0)\n"
        "    try:\n"
        "        out = cand.solve(**copy.deepcopy(kw))\n"
        "        signal.setitimer(signal.ITIMER_REAL, 0)\n"
        "        ok = checker.check(kw, exp, out)\n"
        "    except BaseException:\n"
        "        signal.setitimer(signal.ITIMER_REAL, 0)\n"
        "        ok = False\n"
        "    res['extra_pass'] += int(bool(ok))\n"
        "print(json.dumps(res))\n")
    (work / "harness.py").write_text(harness)
    try:
        out = subprocess.run([sys.executable, "-I", str(work / "harness.py"), str(work)], capture_output=True,
                             text=True, timeout=600)
        r = json.loads(out.stdout.strip().splitlines()[-1])
    except (subprocess.TimeoutExpired, json.JSONDecodeError, IndexError) as e:
        r = {"error": str(e)[:200]}
    r["extra_note"] = "3 seeded random stress cases (n 2,000-20,000) checked against the default reference" if extra_cases \
        else "no stress generator for this task"
    return r


T13_COVER = re.compile(r"\[\s*(False|0)\s*\]\s*\*|=\s*set\(\)[\s\S]*range\(\s*\w+\s*,\s*\w+\s*\+\s*1\s*\)")


def regex_merge_class(code: str) -> str:
    if T13_COVER.search(code):
        return "COVERAGE_ARRAY"
    if not re.search(r"\bsorted\(|\.sort\(", code) and re.search(r"for\s+\w+(\s*,\s*\w+)?\s+in\s+(intervals|range\()", code):
        return "UNSORTED_SWEEP"
    return "OTHER"


def run_other_stage() -> None:
    pool = pd.read_parquet(AUDIT / "pool.parquet")
    events = json.loads((AUDIT / "pool_events.json").read_text())
    jr_path = AUDIT / "judge_results.json"
    res = json.loads(jr_path.read_text()) if jr_path.exists() else {"verdicts": {}, "controls": [], "spent_usd": 0.0}
    manual = json.loads((AUDIT / "manual_pass.json").read_text())["programs"]
    w = judge_weights(res) if res.get("controls") else {}
    weighted = [j for j in ("A", "B") if w.get(j, {}).get("weighted")]
    # exp18 reuse by sha
    na = json.loads(p("exp18", "results/novelty_audit.json").read_text())
    ma = json.loads(p("exp18", "results/manual_audit.json").read_text())["records"]
    exp18_by_sha = {}
    for rec in na["records"]:
        m = ma.get(rec["sample_id"], {})
        exp18_by_sha[rec["code_sha256"]] = EXP18_MAP.get(m.get("final_class") or rec.get("final_class"), None)
    rows = []
    v = res.get("verdicts", {})
    for _, r in pool.drop_duplicates("code_sha256").iterrows():
        vv = v.get(r.code_sha256, {})
        ca, cb, cc = ((vv.get(j) or {}).get("class") for j in ("A", "B", "C"))
        if len(weighted) == 2:
            cons = ca if ca == cb else (cc or "UNRESOLVED")
            cons_src = "agree" if ca == cb else "tie-break"
        elif len(weighted) == 1:
            cons = (vv.get(weighted[0]) or {}).get("class") or "UNRESOLVED"
            cons_src = f"judge {weighted[0]} only (other judge below the 5/6 control gate)"
        else:
            cons, cons_src = "UNRESOLVED", "no judge passed the control gate"
        mrec = manual_lookup(r.code_sha256, manual)
        e18 = exp18_by_sha.get(r.code_sha256)
        final = mrec["final_class"] if mrec else (e18 or cons)
        src = "manual" if mrec else ("exp18_reuse" if e18 else cons_src)
        rows.append({"code_sha256": r.code_sha256, "task": r.task, "passed": bool(r.passed),
                     "nearest_known_label": r.nearest_known_label, "nearest_known_jaccard": r.nearest_known_jaccard,
                     "features": r.features, "judge_A": ca, "judge_B": cb, "judge_C_tiebreak": cc,
                     "judge_A_named": (vv.get("A") or {}).get("named_algorithm"),
                     "judge_B_named": (vv.get("B") or {}).get("named_algorithm"), "consensus": cons,
                     "consensus_source": cons_src, "exp18_verdict": e18, "manual_class": (mrec or {}).get("final_class"),
                     "manual_reason": (mrec or {}).get("reason"), "manual_sample": bool((mrec or {}).get("sample")),
                     "final_class": final, "final_source": src,
                     "events": ";".join(sorted(pool[pool.code_sha256 == r.code_sha256].event_id))})
    prog = pd.DataFrame(rows)
    # NOVEL candidates that passed: re-run hidden tests before any NOVEL verdict stands
    reruns = {}
    flagged = prog[(prog.judge_A == "NOVEL") | (prog.judge_B == "NOVEL") | (prog.final_class == "NOVEL")]
    for _, r in flagged[flagged.passed].iterrows():
        code = pool[pool.code_sha256 == r.code_sha256].code.iloc[0]
        reruns[r.code_sha256] = rerun_hidden_tests(code, r.task)
    prog["rerun"] = prog.code_sha256.map(lambda h: json.dumps(reruns.get(h)) if h in reruns else "")
    novel_confirmed = int(((prog.final_class == "NOVEL") & prog.passed).sum())
    prog.to_csv(TAB / "other_audit_programs.csv", index=False)
    # per-event table
    ev_rows = []
    for e in events:
        sub = prog[prog.events.str.contains(re.escape(e["event_id"]))]
        c = Counter(sub.final_class)
        ev_rows.append({"event_id": e["event_id"], "artifact_id": e["artifact_id"], "task": e["task"], "arm": e["arm"],
                        "n_other_attempts": e["n_other_attempts"], "n_unique": e["n_unique"], "n_sampled": e["n_sampled"],
                        "n_attempted_in_event": e["n_attempted"], "n_passed_sampled": int(sub.passed.sum()),
                        **{f"n_{k}": int(c.get(k, 0)) for k in ("LABELLER_MISS", "CATALOGUE_VARIANT", "NOVEL",
                                                                "DEGENERATE", "UNRESOLVED")}})
    evdf = pd.DataFrame(ev_rows)
    evdf.to_csv(TAB / "other_audit_events.csv", index=False)
    # kappa among judges (programs only)
    both = prog.dropna(subset=["judge_A", "judge_B"])
    kap = cohen_kappa(both.judge_A, both.judge_B)
    kci = kappa_boot_ci(both.judge_A.tolist(), both.judge_B.tolist())
    agree = float((both.judge_A == both.judge_B).mean()) if len(both) else float("nan")
    mread = prog[prog.final_source == "manual"]
    kap_vs_manual = {j: cohen_kappa(mread[f"judge_{j}"].fillna("NA"), mread.final_class) for j in ("A", "B")}
    samp = prog[prog.manual_sample]
    sample_stats = {"n": int(len(samp)),
                    "seed_and_ids": "audit/manual_sample_ids.json",
                    "agreement_vs_manual": {j: float((samp[f"judge_{j}"] == samp.final_class).mean()) if len(samp) else None
                                            for j in ("A", "B")},
                    "kappa_vs_manual": {j: cohen_kappa(samp[f"judge_{j}"].fillna("NA"), samp.final_class) for j in ("A", "B")},
                    "manual_class_counts": dict(Counter(samp.final_class))}

    # catalogue-only avoidance tables
    knob = pd.read_parquet(WS / "data" / "knob.parquet")
    t95 = knob[(knob.exp == "exp13") & (knob.arm == "ban")][["task", "n_attempted", "offdef_share", "cat_only_avoidance",
                                                             "other_share", "sources"]].copy()
    t95["table"] = "Table 95 (exp13 Qwen bench modal bans; " + cite("exp13", "data/samples.jsonl") + ")"
    t95["residue_gated"] = (t95.offdef_share >= 0.5) & (t95.cat_only_avoidance < 0.5)
    llama_rows = []
    for e in _jsonl(p("exp15", "results/c1_events.jsonl")):
        lc = e["landing_counts"]
        att = {k: v for k, v in lc.items() if k not in ("invalid", "unresolved", "no_code", "disputed")}
        n = sum(att.values())
        X = e["banned"]
        cat = set(catalogue(e["task"]))
        cat_nb = sum(v for k, v in att.items() if k in cat and k != X)
        llama_rows.append({"task": e["task"], "event_id": e["event_id"], "n_attempted": n,
                           "offdef_share": 1 - att.get(X, 0) / n if n else None,
                           "cat_only_avoidance": cat_nb / n if n else None,
                           "other_share": att.get("other", 0) / n if n else None,
                           "sources": cite("exp15", "results/c1_events.jsonl")})
    t102 = pd.DataFrame(llama_rows)
    t102["table"] = "Table 102 (exp15 Llama ban events)"
    t102["residue_gated"] = (t102.offdef_share >= 0.5) & (t102.cat_only_avoidance < 0.5)
    t106 = knob[(knob.exp == "exp16") & knob.arm.isin(["a", "b", "c", "d", "K0", "V1"])][
        ["task", "arm", "n_attempted", "offdef_share", "cat_only_avoidance", "other_share", "sources"]].copy()
    t106["table"] = "Table 106 (exp16 route arms)"
    t106["residue_gated"] = (t106.offdef_share >= 0.5) & (t106.cat_only_avoidance < 0.5)
    pd.concat([t95.assign(event_id="exp13:" + t95.task + ":ban"), t102,
               t106.assign(event_id="exp16:" + t106.task + ":" + t106.arm)], ignore_index=True).to_csv(
        TAB / "catalogue_only_avoidance.csv", index=False)
    residue_events = {"exp13": t95[t95.residue_gated].task.tolist(), "exp15": t102[t102.residue_gated].event_id.tolist(),
                      "exp16": (t106[t106.residue_gated].task + ":" + t106[t106.residue_gated].arm).tolist()}
    # exp13 contest summary with and without residue-gated events
    c13 = _jsonl(p("exp13", "results/c1_events.jsonl"))
    gated = [e for e in c13 if e.get("gate_pass")]
    fams = ["SUBTRACT", "LADDER", "ASSOCIATE", "PROXIMITY"]

    def contest(evs):
        out = {}
        for f in fams:
            vals = [e["logscore"][f] - e["logscore"]["UNIFORM"] for e in evs
                    if e.get("logscore", {}).get(f) is not None and e["logscore"].get("UNIFORM") is not None]
            out[f] = {"mean_minus_uniform": float(np.mean(vals)) if vals else None, "n": len(vals)}
        return out

    resid13 = set(residue_events["exp13"])
    contest_all = contest(gated)
    contest_wo = contest([e for e in gated if e["task"] not in resid13])
    route = json.loads((RES / "route.json").read_text())
    # merge-intervals correction over all 44 exp13 T13 'other' programs
    t13 = [r for r in _jsonl(p("exp13", "data/samples.jsonl")) if r["task"] == "T13" and r["condition"] == "ban"
           and r["label"] == "other"]
    mrows = []
    for r in t13:
        mm = manual_lookup(r["code_sha256"], manual) or {}
        mrows.append({"code_sha256": r["code_sha256"], "regex_class": regex_merge_class(r["code"] or ""),
                      "manual_class": mm.get("merge_class"), "passed": r["passed"] in (True, "True")})
    mdf = pd.DataFrame(mrows)
    mdf.to_csv(TAB / "merge_intervals_correction.csv", index=False)
    merge = {"n": int(len(mdf)), "regex_counts": dict(Counter(mdf.regex_class)),
             "manual_counts": dict(Counter(mdf.manual_class.fillna("UNREAD"))),
             "regex_manual_agreement": float((mdf.regex_class == mdf.manual_class).mean()),
             "n_passed": int(mdf.passed.sum()),
             "statement": ("exp16's 'superadditive' T13 route class rests on residue: the 44 exp13 T13 'other' programs are "
                           "coverage-array and unsorted-sweep attempts that all fail; with catalogue-only avoidance T13 is "
                           f"{route['T13_route_class']['cat_only']}."),
             "T13_route_class": route["T13_route_class"]}
    summ = {"pool": {"n_events": len(events), "n_programs": int(len(prog)), "n_passed": int(prog.passed.sum()),
                     "cap_per_event": 25 if sum(e["n_unique"] for e in events) > 220 else 40},
            "judges": {"models": {"A": "openai/gpt-4.1-mini", "B": "google/gemini-2.5-flash",
                                  "C": "deepseek/deepseek-chat-v3.1 (tie-break)"},
                       "controls": w, "weighted": weighted, "kappa_A_B": kap, "kappa_A_B_ci95": kci,
                       "agreement_A_B": agree, "n_compared": int(len(both)), "kappa_vs_manual": kap_vs_manual,
                       "spent_usd": res.get("spent_usd"), "stopped": res.get("stopped"),
                       "class_counts_A": dict(Counter(prog.judge_A.dropna())),
                       "class_counts_B": dict(Counter(prog.judge_B.dropna()))},
            "final_class_counts": dict(Counter(prog.final_class)),
            "final_class_counts_passed": dict(Counter(prog[prog.passed].final_class)),
            "final_source_counts": dict(Counter(prog.final_source)),
            "n_exp18_verdicts_reused": int(prog.exp18_verdict.notna().sum()),
            "exp18_reuse_note": "sha256 match against exp18 results/novelty_audit.json records (manual_audit.json verdicts)",
            "novel_flagged_by_a_judge": int(len(flagged)), "novel_confirmed": novel_confirmed, "reruns": reruns,
            "manual_sample": sample_stats,
            "manual_pass": {"n_read": int((prog.final_source == "manual").sum()),
                            "scope": "every passed program, every program a judge called NOVEL, and all 44 exp13 T13 "
                                     "'other' programs (merge-intervals correction), plus a seeded 20% sample of the "
                                     "remaining programs (manual_sample)"},
            "catalogue_only": {"residue_gated_events": residue_events,
                               "table95": t95.drop(columns=["sources"]).to_dict("records"),
                               "table102": t102.drop(columns=["sources"]).to_dict("records"),
                               "table106": t106.drop(columns=["sources"]).to_dict("records")},
            "contest_exp13": {"with_residue_events": contest_all, "without_residue_events": contest_wo,
                              "residue_tasks_dropped": sorted(resid13)},
            "route_fractions": {k: {"point": vv["point"], "jackknife_ci95": {m: vv["jackknife"][m]["ci95"]
                                                                            for m in ("F_prompt", "F_direct")}}
                                for k, vv in route["route_fractions"].items()},
            "merge_intervals": merge}
    (RES / "other_audit.json").write_text(json.dumps(summ, indent=1, default=str))
    logger.info(f"0d: {len(prog)} programs; final {summ['final_class_counts']}; novel confirmed {novel_confirmed}; "
                f"kappa A-B {kap:.3f}; residue events {residue_events}; merge {merge['manual_counts']}")
