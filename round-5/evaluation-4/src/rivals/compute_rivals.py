#!/usr/bin/env python3
"""(0i) Compute the eight ban-free rival task predictors R1-R8 and the affordance covariate K for the 15 Qwen3-8B
tasks, WITHOUT reading any escape fraction, ban outcome or push landing; then freeze them (rivals.json, its sha256,
and a hash-chained line in commitments.log) before rivals/score_rivals.py may open a target.

Every path this script opens is logged to audit/rival_inputs.log; outcome files are refused (PermissionError).
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

WS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WS / "src"))
from io_util import NAMES, TASKS, Inputs, as_bool, sha256_file  # noqa: E402
import stats_util as su  # noqa: E402

FORBIDDEN = ("results/escape.json", "alpha_sweep.json", "c3b.json", "c3a.json", "bans.json", "inputs/exp13",
             "inputs/exp16", "art_k6nzFCDLOjQP:data/samples.jsonl", "raw_bans", "explore.json", "c2a.json",
             "screen.json", "decomposition.json", "c1.json", "prices.json", "knob_rows")
BAD = su.NOT_ALT
LOG = WS / "audit" / "rival_inputs.log"
GENESIS = hashlib.sha256(b"iter5_dir1").hexdigest()
DEFS = {
    "R1": {"name": "twin opening margin", "transferable": True, "orientation": -1,
           "definition": "mean over the 5 templates of lp(default's modal opening) - max over non-default modes of lp("
                         "that mode's modal opening) (exp22 results/opening_lp.json); default = exp22 twin modal correct "
                         "label; larger margin -> less movable"},
    "R2": {"name": "forced can rate", "transferable": False, "orientation": 1,
           "definition": "max over non-default modes of the share of forced attempts (paraphrases 0-4 and top-ups; "
                         "descriptive variant -1 excluded) that pass the hidden tests AND carry the requested label "
                         "(bench data/samples_forced.jsonl); sensitivity: mean over non-default modes"},
    "R3": {"name": "association clarity", "transferable": False, "orientation": 1,
           "definition": "share of the modal mapped answer among the 20 free-form 'standard alternative to <default>' "
                         "answers (bench data/association.jsonl; T1/T2 exp7 freeform_labelled.jsonl); sensitivity: 1 - "
                         "entropy / ln(catalogue size)"},
    "R4": {"name": "novelty-instruction off-default share", "transferable": True, "orientation": 1,
           "definition": "exp19 NOVELTY rows (N = 50) minus exp19 TWIN rows: excess of the correct-only, catalogue-only "
                         "off-default share ('other' excluded)"},
    "R5": {"name": "human-solution diversity", "transferable": False, "orientation": 1,
           "definition": "correct-only Hill-1 of accepted Mercury human solutions of the primary LeetCode problem, "
                         "rarefied at depth min(20, n); labels: frozen bench AST rules + blind judge on unknowns; task "
                         "NOT_COMPUTABLE when the 10-program judge audit agreement < 0.8 (gate-lite)"},
    "R6": {"name": "merit gap (runtime)", "transferable": True, "orientation": -1,
           "definition": "summed per-case median CPU time (1 warm-up + 5 timed) of the runner-up's references over the "
                         "default's references on the hidden tests; runner-up = modal association answer (ban-free); "
                         "sensitivities: most competitive alternative (min ratio), AST-node length ratio, line ratio"},
    "R7": {"name": "twin modal share", "transferable": True, "orientation": -1,
           "definition": "correct-only modal share of the exp22 twin (rows de-duplicated by CRN seed); exp19 twin "
                         "(N = 50) as replication"},
    "R8": {"name": "ban-unit ratio (dose confound)", "transferable": False, "orientation": -1,
           "definition": "ban-free unit / ban unit per task (exp22 results/units.json ratio_mean_nfree_over_mean_n); a "
                         "small ratio means the ban unit is large relative to the ban-free scale (bigger effective dose); "
                         "secondary: ban unit / residual norm (exp20 S0, 6 tasks only)"},
    "K": {"name": "affordance covariate", "transferable": True, "orientation": 1,
          "definition": "catalogue size (bench spec.json; T1 6, T2 5); secondary: number of catalogue modes whose "
                        "reference passes the hidden tests (rivals/r6_merit_raw.json)"},
}


def canon(obj: Any) -> str:
    def rnd(x: Any) -> Any:
        if isinstance(x, float):
            return None if not math.isfinite(x) else round(x, 6)
        if isinstance(x, dict):
            return {str(k): rnd(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)):
            return [rnd(v) for v in x]
        return x
    return json.dumps(rnd(obj), sort_keys=True, separators=(",", ":"))


def chain_append(entry: dict[str, Any]) -> str:
    path = WS / "commitments.log"
    prev = GENESIS
    if path.exists():
        lines = [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]
        if lines:
            prev = lines[-1]["entry_hash"]
    ce = canon(entry)
    h = hashlib.sha256((prev + ce).encode()).hexdigest()
    with path.open("a") as fh:
        fh.write(json.dumps({"prev_hash": prev, "entry": json.loads(ce), "entry_hash": h}) + "\n")
    return h


def cohen_kappa(a: list[str], b: list[str]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    return 1.0 if pe >= 1 else (po - pe) / (1 - pe)


def flag(values: dict[str, float | None]) -> str | None:
    v = [x for x in values.values() if x is not None]
    return "non-informative (<= 3 distinct values)" if len(set(round(x, 9) for x in v)) <= 3 else None


@logger.catch(reraise=True)
def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(WS / "logs" / "compute_rivals.log", rotation="30 MB", level="DEBUG")
    LOG.parent.mkdir(exist_ok=True)
    LOG.write_text("")

    def log_open(s: str) -> None:
        with LOG.open("a") as fh:
            fh.write(f"{datetime.now(timezone.utc).isoformat()} {s}\n")

    I = Inputs(log=log_open, forbidden=FORBIDDEN)
    vals: dict[str, dict[str, Any]] = {k: {} for k in DEFS}
    extra: dict[str, dict[str, Any]] = {k: {} for k in DEFS}

    # ---------------------------------------------------------------- defaults: exp22 twin (deduplicated by seed)
    raw_twin = I.jsonl("exp22", "data/samples_raw.jsonl", must_contain='"arm": "TWIN"')
    seed_of = {f"{x['task']}|{x['template']}|{x['arm']}|{x['sample_id']}": x["seed"] for x in raw_twin}
    del raw_twin
    tw22 = I.jsonl("exp22", "data/labels.jsonl", must_contain='"arm": "TWIN"')
    seen, twin = set(), {t: [] for t in TASKS}
    for x in tw22:
        sd = seed_of.get(x["key"])
        if x["arm"] != "TWIN" or sd is None or (x["task"], sd) in seen:
            continue
        seen.add((x["task"], sd))
        twin[x["task"]].append(x)
    D = {}
    for t in TASKS:
        cc = Counter(x["label"] for x in twin[t] if x["passed"])
        D[t], k = su.modal(cc)
        n = sum(cc.values())
        vals["R7"][t] = k / n if n else None
        extra["R7"][t] = {"n_twin_rows": len(twin[t]), "n_correct": n, "composition": dict(cc)}
    # exp19 twin replication + R4 (only TWIN and NOVELTY lines are parsed; PN lines are skipped unparsed)
    r19 = I.jsonl("exp19", "data/samples.jsonl", must_contain='"arm": "TWIN"') + \
        I.jsonl("exp19", "data/samples.jsonl", must_contain='"arm": "NOVELTY"')
    log_open("note: exp19 data/samples.jsonl parsed for arms TWIN and NOVELTY only")
    for t in TASKS:
        tw = [x for x in r19 if x["task"] == t and x["arm"] == "TWIN"]
        nv = [x for x in r19 if x["task"] == t and x["arm"] == "NOVELTY"]
        ctw = Counter(x["label"] for x in tw if as_bool(x["passed"]))
        d19, k19 = su.modal(ctw)
        extra["R7"][t]["exp19_replication"] = (k19 / sum(ctw.values())) if ctw else None
        extra["R7"][t]["exp19_default"] = d19
        if not nv or not tw:
            vals["R4"][t] = None
            extra["R4"][t] = {"status": "NOT_COMPUTABLE: no exp19 novelty arm"}
            continue

        def share(rows: list[dict]) -> tuple[float | None, int]:
            corr = [x for x in rows if as_bool(x["passed"])]
            if not corr:
                return None, 0
            return sum(1 for x in corr if x["label"] not in BAD and x["label"] != D[t]) / len(corr), len(corr)
        s_nv, n_nv = share(nv)
        s_tw, n_tw = share(tw)
        vals["R4"][t] = (s_nv - s_tw) if s_nv is not None and s_tw is not None else None
        extra["R4"][t] = {"novelty_share": s_nv, "n_correct_novelty": n_nv, "twin_share": s_tw,
                          "n_correct_twin": n_tw, "n_novelty": len(nv), "n_twin": len(tw)}
    # ---------------------------------------------------------------- catalogue + K
    bench_root = Path(I.path("bench", "bench/commitment.json")).parent
    cat: dict[str, list[str]] = {}
    for td in sorted(p for p in bench_root.iterdir() if p.is_dir() and (p / "spec.json").exists()):
        t = td.name.split("_")[0]
        cat[t] = [c["mode"] for c in I.json("bench", f"bench/{td.name}/spec.json")["catalogue"]]
    cat["T1"] = ["bfs", "dfs", "bibfs", "iddfs", "astar_gbfs", "dijkstra"]
    cat["T2"] = ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"]
    r6raw = json.loads((WS / "rivals" / "r6_merit_raw.json").read_text())["rows"]
    log_open("open rivals/r6_merit_raw.json (this artifact: CPU timing of catalogue references)")
    tkey = {"t1": "T1", "t2": "T2"}
    refs: dict[str, list[dict]] = {}
    for x in r6raw:
        refs.setdefault(tkey.get(x["task"], x["task"]), []).append(x)
    for t in TASKS:
        vals["K"][t] = float(len(cat[t]))
        extra["K"][t] = {"catalogue": cat[t], "n_modes_reference_passes": len({x["mode"] for x in refs.get(t, [])
                                                                                 if x.get("passes_all")})}
    # ---------------------------------------------------------------- R1 opening margin
    olp = I.json("exp22", "results/opening_lp.json")["by_task"]
    for t in TASKS:
        if t not in olp or D[t] not in olp[t]:
            vals["R1"][t] = None
            extra["R1"][t] = {"status": "NOT_COMPUTABLE: no opening log-probabilities for this task"}
            continue
        lpD = np.array(olp[t][D[t]]["lp_per_template"])
        others = {m: np.array(v["lp_per_template"]) for m, v in olp[t].items() if m != D[t] and v.get("lp_per_template")}
        mx = np.max(np.vstack(list(others.values())), axis=0)
        vals["R1"][t] = float(np.mean(lpD - mx))
        distinct = {m: v for m, v in others.items() if not np.allclose(v, lpD)}
        extra["R1"][t] = {"default": D[t], "margin_of_means": float(lpD.mean() - max(v.mean() for v in others.values())),
                          "identical_opening_modes": sorted(set(others) - set(distinct)),
                          "margin_excluding_identical_openings": float(np.mean(lpD - np.max(np.vstack(list(
                              distinct.values())), axis=0))) if distinct else None}
    # ---------------------------------------------------------------- R2 forced can rate
    forced = I.jsonl("bench", "data/samples_forced.jsonl")
    for t in TASKS:
        if t in ("T1", "T2"):
            vals["R2"][t] = None
            extra["R2"][t] = {"status": "NOT_COMPUTABLE: no unselected forced attempts for the path tasks in a declared "
                                        "dependency (exp7 forced_selected.jsonl is post-selection)"}
            continue
        per = {}
        for m in cat[t]:
            if m == D[t]:
                continue
            rr = [x for x in forced if x["task"] == t and x["forced_mode"] == m and (x.get("paraphrase_id") or 0) >= 0]
            per[m] = {"n": len(rr), "can": (sum(1 for x in rr if x["passed"] and x["label"] == m) / len(rr)) if rr else None}
        cans = [v["can"] for v in per.values() if v["can"] is not None]
        vals["R2"][t] = max(cans) if cans else None
        extra["R2"][t] = {"per_mode": per, "mean_over_modes": float(np.mean(cans)) if cans else None}
    # ---------------------------------------------------------------- R3 association clarity (+ runner-up for R6)
    assoc = I.jsonl("bench", "data/association.jsonl")
    ff = I.jsonl("exp22", "inputs/exp7/data/freeform_labelled.jsonl")
    runner = {}
    for t in TASKS:
        if t in ("T1", "T2"):
            ans = [x["label"] for x in ff if x["task"] == t.lower() and x["X"] == D[t]]
        else:
            ans = [x["mapped"] for x in assoc if x["task"] == t and x["X"] == D[t]]
        c = Counter(ans)
        if not ans:
            vals["R3"][t] = None
            extra["R3"][t] = {"status": "NOT_COMPUTABLE: no association answers for the default"}
            runner[t] = None
            continue
        m, k = su.modal(c)
        p = np.array(list(c.values()), float) / len(ans)
        H = float(-(p * np.log(p)).sum())
        vals["R3"][t] = k / len(ans)
        # R6 runner-up: the modal association answer among catalogue modes (when the modal answer is off-catalogue,
        # e.g. 'other', the most frequent catalogue answer is used and the fact is recorded)
        cat_ans = Counter({a: v for a, v in c.items() if a in cat[t] and a != D[t]})
        runner[t] = su.modal(cat_ans)[0] if cat_ans else None
        extra["R3"][t] = {"n": len(ans), "answers": dict(c), "modal_answer": m, "runner_up_catalogue": runner[t],
                          "modal_answer_off_catalogue": m not in cat[t],
                          "one_minus_norm_entropy": 1 - H / math.log(len(cat[t])) if len(cat[t]) > 1 else None}
    # ---------------------------------------------------------------- R6 merit gap
    for t in TASKS:
        rr = refs.get(t, [])
        bym: dict[str, list[dict]] = {}
        for x in rr:
            if x.get("passes_all"):
                bym.setdefault(x["mode"], []).append(x)
        if D[t] not in bym or not runner.get(t) or runner[t] not in bym:
            vals["R6"][t] = None
            extra["R6"][t] = {"status": f"NOT_COMPUTABLE: reference missing for default {D[t]} or runner-up "
                                        f"{runner.get(t)}"}
            continue

        def med(m: str, key: str) -> float:
            return float(np.median([x[key] for x in bym[m]]))
        tD, nD, lD = med(D[t], "total_median_s"), med(D[t], "ast_nodes"), med(D[t], "sloc")
        ratios = {m: med(m, "total_median_s") / tD for m in bym if m != D[t]}
        vals["R6"][t] = ratios[runner[t]]
        extra["R6"][t] = {"default": D[t], "runner_up": runner[t], "runtime_ratio_runner_up": ratios[runner[t]],
                          "runtime_ratio_min_over_alternatives": min(ratios.values()),
                          "most_competitive_alternative": min(ratios, key=ratios.get),
                          "length_ratio_ast_nodes": med(runner[t], "ast_nodes") / nD,
                          "length_ratio_sloc": med(runner[t], "sloc") / lD, "runtime_ratios": ratios,
                          "default_time_s": tD}
    # ---------------------------------------------------------------- R5 human-solution diversity
    r5p = WS / "rivals" / "r5_human_raw.json"
    r5 = json.loads(r5p.read_text())["rows"] if r5p.exists() else []
    log_open("open rivals/r5_human_raw.json (this artifact: Mercury human-solution labels)")
    for t in TASKS:
        rr = [x for x in r5 if x["task"] == t and x["role"] == "primary"]
        if t == "T1":
            vals["R5"][t] = None
            extra["R5"][t] = {"status": "NOT_COMPUTABLE: only the related 8-directional LeetCode 1091 exists (returns a "
                                        "length; different problem)"}
            continue
        corr = [x for x in rr if x["passed"]]
        aud = [x for x in corr if x["judge_role"] == "audit" and x["judge_label"] not in (None, "NOT_JUDGED")]
        agree = (sum(1 for x in aud if x["judge_label"] == x["ast_label"]) / len(aud)) if aud else None
        lab = Counter(x["final_label"] for x in corr if x["final_label"] not in (None, "unlabelled"))
        n = sum(lab.values())
        h = su.hill1_rarefied(dict(lab), min(20, n)) if n else {"hill": None, "depth": 0, "flag": "none"}
        ok = agree is not None and agree >= 0.8 and n >= 5
        kap = cohen_kappa([x["ast_label"] for x in aud], [x["judge_label"] for x in aud]) if aud else None
        vals["R5"][t] = h["hill"] if ok else None
        extra["R5"][t] = {"n_mercury": len(rr), "n_correct": len(corr), "n_labelled": n, "composition": dict(lab),
                          "audit_n": len(aud), "audit_agreement": agree, "audit_kappa": kap, "hill_depth": h["depth"],
                          "hill_if_computable": h["hill"],
                          "non_default_share": (sum(v for k, v in lab.items() if k not in (D[t], "other")) / n) if n else None,
                          "status": "OK (gate-lite)" if ok else "NOT_COMPUTABLE: audit agreement < 0.8 or < 5 labelled",
                          "caveat": "Mercury is a runtime-stratified sample of accepted solutions, not a random one; the "
                                    "LeetCode problem may differ from the bench spec"}
    aud_all = [x for x in r5 if x["role"] == "primary" and x["passed"] and x["judge_role"] == "audit"
               and x["judge_label"] not in (None, "NOT_JUDGED")]
    extra["R5"]["_pooled_audit"] = {"n": len(aud_all), "agreement": (sum(x["judge_label"] == x["ast_label"] for x in aud_all)
                                                                     / len(aud_all)) if aud_all else None,
                                    "kappa": cohen_kappa([x["ast_label"] for x in aud_all],
                                                         [x["judge_label"] for x in aud_all])}
    # ---------------------------------------------------------------- R8 dose units
    u22 = I.json("exp22", "results/units.json")["per_task"]
    u20 = I.json("exp20", "results/units_summary.json")
    for t in TASKS:
        u = u22.get(t, {})
        vals["R8"][t] = u.get("ratio_mean_nfree_over_mean_n")
        extra["R8"][t] = {"unit_kind": u.get("unit"), "ban_unit_mean_norm": u.get("mean_n"),
                          "ban_unit_over_residual_norm_exp20_S0": (u20.get(t, {}).get("S0_blocks12_23") or {}).get("rel")}
        if vals["R8"][t] is None:
            extra["R8"][t]["status"] = "NOT_COMPUTABLE: no ban unit (ban-free unit used for this task)"
    # ---------------------------------------------------------------- freeze
    code_sha = sha256_file(Path(__file__))
    out = {"hypothesis_id": "iter5_dir1", "tasks": TASKS, "task_names": NAMES, "default_exp22_twin": D,
           "definitions": DEFS, "values": vals, "details": extra,
           "flags": {k: flag(v) for k, v in vals.items()},
           "n_tasks": {k: sum(1 for x in v.values() if x is not None) for k, v in vals.items()},
           "compute_rivals_sha256": code_sha,
           "r5_script_sha256": sha256_file(WS / "rivals" / "r5_human.py"),
           "r6_script_sha256": sha256_file(WS / "rivals" / "r6_merit.py"),
           "this_artifact_inputs_sha256": {"rivals/r6_merit_raw.json": sha256_file(WS / "rivals" / "r6_merit_raw.json"),
                                           "rivals/r5_human_raw.json": sha256_file(r5p) if r5p.exists() else None},
           "dependency_inputs_sha256": {k: v.get("sha256") for k, v in I.manifest.items()},
           "label": "SCREEN-ONLY scoring is descriptive; A1-transferable rivals R1, R4, R6, R7 (and K) are frozen for the "
                    "Step-2 confirmation on new units"}
    text = canon(out)
    sha = hashlib.sha256(text.encode()).hexdigest()
    old = (WS / "rivals.json").read_text() if (WS / "rivals.json").exists() else None
    if old == text:
        # identical re-computation: the existing freeze stands; nothing is appended to the chain
        logger.info(f"rivals.json unchanged (sha256 {sha[:16]}...); existing freeze kept")
        return
    log_lines = (WS / "commitments.log").read_text().splitlines() if (WS / "commitments.log").exists() else []
    if any('"targets opened' in ln for ln in log_lines):
        logger.warning("rivals.json CHANGED after targets were opened: recorded as a post-target re-freeze")
    (WS / "rivals.json").write_text(text)
    (WS / "rivals.json.sha256").write_text(sha + "  rivals.json\n")
    same_vals = None
    if old is not None:
        o = json.loads(old)
        n_ = json.loads(text)
        same_vals = all(o.get(k) == n_.get(k) for k in ("values", "definitions", "details", "default_exp22_twin"))
    h = chain_append({"seq": "freeze", "utc": datetime.now(timezone.utc).isoformat(), "what": "rivals.json frozen",
                      "rivals_sha256": sha, "compute_rivals_sha256": code_sha,
                      "post_target_refreeze": any('"targets opened' in ln for ln in log_lines),
                      "values_identical_to_previous_freeze": same_vals})
    (WS / "results").mkdir(exist_ok=True)
    (WS / "results" / "input_hashes_rivals.json").write_text(json.dumps(I.manifest, indent=1))
    logger.info(f"rivals frozen: sha256 {sha[:16]}..., chain {h[:16]}...; n per rival {out['n_tasks']}")


if __name__ == "__main__":
    main()
