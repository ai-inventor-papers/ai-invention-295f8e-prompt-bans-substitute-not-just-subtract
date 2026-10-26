#!/usr/bin/env python3
"""Second independent re-derivation: headline numbers not covered by audit/rederive.py, recomputed from raw files
through different code (sklearn / scipy / math instead of src/stats.py), each statistical test also run on shuffled
input, where it must fail. Imports nothing from src/. Writes audit/rederive_extra.json.
"""

from __future__ import annotations

import copy
import json
import math
import os
import random
import signal
from collections import Counter
from pathlib import Path

import numpy as np
from scipy import stats
from sklearn.metrics import cohen_kappa_score

WS = Path(__file__).resolve().parent.parent


def _dep(aid: str, env: str, folder: str) -> Path:
    base = os.environ.get(env)
    loc = WS / "paths.local.json"
    if not base and loc.exists():
        base = json.loads(loc.read_text()).get(env)
    if base:
        return Path(base) / folder
    deps = Path(os.environ.get("AII_DEPS_DIR") or WS.parent)
    for cand in (deps / aid, deps / folder, *sorted(deps.glob(f"*{aid}*"))):
        if cand.is_dir():
            return cand
    raise FileNotFoundError(f"dependency {aid} not found; set AII_DEPS_DIR or {env}")


E11 = _dep("art_0ndRfWKBWclR", "AII_ITER2", "gen_art_experiment_11")
E13 = _dep("art_1AYTO1Epb_7t", "AII_ITER3", "gen_art_experiment_13")
E14 = _dep("art_WiY4wqHLb9Gy", "AII_ITER3", "gen_art_experiment_14")
E15 = _dep("art_Q-qh-9HhPoWo", "AII_ITER3", "gen_art_experiment_15")
E16 = _dep("art__5akZ9W9iZM4", "AII_ITER3", "gen_art_experiment_16")
RNG = random.Random(97)


def jl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


OUT: dict = {"checks": [], "placebos": []}


def check(name, got, exp, ok):
    OUT["checks"].append({"name": name, "rederived": got, "expected": exp, "match": bool(ok)})


def placebo(name, detail, failed_as_required):
    OUT["placebos"].append({"name": name, "detail": detail, "failed_as_required": bool(failed_as_required)})


def main() -> None:
    oa = json.loads((WS / "results" / "other_audit.json").read_text())
    jr = json.loads((WS / "audit" / "judge_results.json").read_text())
    v = jr["verdicts"]
    # 1. judge agreement (sklearn kappa) + shuffled-label placebo
    ids = [i for i in v if not i.startswith(("pos:", "neg:"))]
    pairs = [((v[i].get("A") or {}).get("class"), (v[i].get("B") or {}).get("class")) for i in ids]
    pairs = [(a, b) for a, b in pairs if a and b]
    A, B = [a for a, _ in pairs], [b for _, b in pairs]
    kap = cohen_kappa_score(A, B)
    check("judge_kappa_A_B", round(kap, 4), round(oa["judges"]["kappa_A_B"], 4), abs(kap - oa["judges"]["kappa_A_B"]) < 1e-9)
    null = []
    for _ in range(2000):
        Bs = B[:]
        RNG.shuffle(Bs)
        null.append(cohen_kappa_score(A, Bs))
    q95 = float(np.quantile(null, 0.95))
    placebo("kappa_shuffled_B", {"observed": kap, "null_mean": float(np.mean(null)), "null_q95": q95},
            abs(float(np.mean(null))) < 0.05 and kap > q95)
    # control gate
    ctrl = {j: sum((v[c].get(j) or {}).get("class") == "LABELLER_MISS" for c in v if c.startswith("pos:")) for j in "AB"}
    check("control_gate_positives", ctrl, {"A": 4, "B": 5}, ctrl == {"A": 4, "B": 5})
    # 2. final classes: manual where read, else judge B (A fails the gate)
    manual = json.loads((WS / "audit" / "manual_pass.json").read_text())["programs"]

    def man(h):
        for k, m in manual.items():
            if h.startswith(k):
                return m["final_class"]
        return None

    final = Counter((man(h) or (v[h].get("B") or {}).get("class") or "UNRESOLVED") for h in ids)
    check("final_class_counts", dict(final), oa["final_class_counts"], dict(final) == oa["final_class_counts"])
    check("novel_confirmed", final.get("NOVEL", 0), 0, final.get("NOVEL", 0) == 0)
    # 3. Llama snap-back / Table 102 (raw landing counts)
    evs = jl(E15 / "results" / "c1_events.jsonl")
    dflt = {e["task"]: e["banned"] for e in evs if e["event_type"] == "modal"}
    got = {}
    for e in evs:
        if e["event_type"] != "present_minor":
            continue
        nb = {k: c for k, c in e["landing_counts"].items() if k not in ("invalid", "unresolved", "no_code", "disputed")
              and k != e["banned"]}
        got[f"{e['task']}:{e['banned']}"] = (nb.get(dflt[e["task"]], 0), sum(nb.values()))
    exp_sb = {"T14:sort_by_count": (54, 75), "T04:kmp": (48, 66), "T10:dfs": (79, 85)}
    check("llama_snap_back", {k: got[k] for k in exp_sb}, exp_sb, all(got[k] == exp_sb[k] for k in exp_sb))
    # 4. exposure sentence (exp14 raw events)
    e14 = jl(E14 / "results" / "c1_events.jsonl")
    ys = {(e["task"], e["Y"]) for e in e14}
    dfn = {(e["task"], e["Y"]) for e in e14 if "subtract_undefined" not in (e.get("flags") or [])}
    hits = {arm: sum(1 for e in e14 if e["event_type"] == arm and (e["task"], e["Y"]) in dfn
                     and set(e["top1"].get("SUBTRACT") or []) & set(e.get("modal") or []))
            for arm in ("exposure_named", "exposure_unnamed")}
    check("exposure_sentence", {"n_Y": len(ys), "defined": len(dfn), **hits},
          {"n_Y": 33, "defined": 4, "exposure_named": 4, "exposure_unnamed": 4},
          len(ys) == 33 and len(dfn) == 4 and hits == {"exposure_named": 4, "exposure_unnamed": 4})
    # 5. exp13 contest, with and without the residue-gated T13
    e13 = [e for e in jl(E13 / "results" / "c1_events.jsonl") if e.get("gate_pass")]
    for tag, evs_ in (("all", e13), ("wo_T13", [e for e in e13 if e["task"] != "T13"])):
        m = {f: float(np.mean([e["logscore"][f] - e["logscore"]["UNIFORM"] for e in evs_])) for f in
             ("SUBTRACT", "LADDER", "ASSOCIATE", "PROXIMITY")}
        rec = oa["contest_exp13"]["with_residue_events" if tag == "all" else "without_residue_events"]
        check(f"contest_exp13_{tag}", {k: round(x, 3) for k, x in m.items()},
              {k: round(rec[k]["mean_minus_uniform"], 3) for k in m}, all(abs(m[k] - rec[k]["mean_minus_uniform"]) < 1e-9 for k in m))
    # 6. screen Fisher p by the hypergeometric formula + shuffled placebo
    scr = json.loads((WS / "screen.json").read_text())["tasks"]
    mov = [scr[t]["movable"] for t in sorted(scr)]
    comp = [int(scr[t]["cat_only_ban_avoidance"] >= 0.5) for t in sorted(scr)]
    k = sum(a and b for a, b in zip(mov, comp))
    N, K, n = len(mov), sum(comp), sum(mov)
    p_hyper = sum(math.comb(K, i) * math.comb(N - K, n - i) for i in range(k, min(K, n) + 1)) / math.comb(N, n)
    check("screen_fisher_p", p_hyper, 1 / 3003, abs(p_hyper - 1 / 3003) < 1e-12 and k == 6 and n == 6 and K == 6)
    ps = []
    for _ in range(5000):
        cs = comp[:]
        RNG.shuffle(cs)
        kk = sum(a and b for a, b in zip(mov, cs))
        ps.append(sum(math.comb(K, i) * math.comb(N - K, n - i) for i in range(kk, min(K, n) + 1)) / math.comb(N, n))
    placebo("fisher_shuffled_tasks", {"median_p": float(np.median(ps))}, float(np.median(ps)) >= 0.3)
    # 7. rival Spearman (scipy) + shuffled-outcome placebo
    import csv
    rows = list(csv.DictReader(open(WS / "tables" / "rival_predictor_values.csv")))
    y = [float(r["cat_only_ban_avoidance"]) for r in rows]
    x = [float(r["movable"]) for r in rows]
    rho = stats.spearmanr(x, y).statistic
    rec = [r for r in csv.DictReader(open(WS / "tables" / "rival_predictors.csv")) if r["predictor"] == "movable"][0]
    check("rival_rho_movability_scipy", round(float(rho), 4), round(float(rec["spearman_rho"]), 4),
          abs(rho - float(rec["spearman_rho"])) < 1e-9)
    null = []
    for _ in range(5000):
        ys_ = y[:]
        RNG.shuffle(ys_)
        null.append(abs(stats.spearmanr(x, ys_).statistic))
    placebo("spearman_shuffled_outcome", {"observed": float(rho), "null_q95_abs": float(np.quantile(null, 0.95)),
                                          "null_median_abs": float(np.median(null))},
            float(np.median(null)) < 0.3 and abs(rho) > float(np.quantile(null, 0.95)))
    # 8. T10 route readings straight from exp16 rows
    seen, cnt = set(), {a: Counter() for a in ("a", "c", "d", "K0")}
    for r in jl(E16 / "data" / "samples.jsonl"):
        if r["uid"] in seen or r["task"] != "T10" or r["arm"] not in cnt:
            continue
        seen.add(r["uid"])
        if str(r.get("label")) not in ("invalid", "no_code", "disputed", "None"):
            cnt[r["arm"]][r["label"]] += 1
    want = {"a": {"bfs": 75, "dfs": 25}, "c": {"dfs": 56, "bfs": 44}, "d": {"dfs": 70, "bfs": 10}, "K0": {"dfs": 57, "bfs": 43}}
    check("route_T10_readings", {a: dict(c) for a, c in cnt.items()}, want,
          all(cnt[a].get(l) == n for a, d in want.items() for l, n in d.items()))
    # 9. hidden-test re-run (in process, direct exec) of the one passing NOVEL-flagged program
    target = "ab8047e5e1f34ada3e95b11366204bbf7b2768618269427212a4bafc827167aa"
    code = None
    for f in (E15 / "data" / "samples.jsonl", E13 / "data" / "samples.jsonl", E16 / "data" / "samples.jsonl",
              E14 / "data" / "samples.jsonl"):
        for r in jl(f):
            if r.get("code_sha256") == target:
                code = r["code"]
                break
        if code:
            break
    ns: dict = {}
    exec(compile(code, "<candidate>", "exec"), ns)  # noqa: S102 - audited program, already run by the pipeline
    tests = jl(E11 / "bench" / "T03_kth_smallest" / "tests.jsonl")

    def _to(*_):
        raise TimeoutError

    signal.signal(signal.SIGALRM, _to)
    ok = 0
    for c in tests:
        signal.setitimer(signal.ITIMER_REAL, float(c.get("limit", 1.0)))
        try:
            out = ns["solve"](**copy.deepcopy(c["kwargs"]))
            ok += int(isinstance(out, int) and not isinstance(out, bool) and out == c["expected"])
        except (TimeoutError, Exception):  # noqa: BLE001 - any failure counts as a failed case
            pass
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
    check("novel_candidate_hidden_tests", f"{ok}/{len(tests)}", "60/60", ok == len(tests) == 60)
    OUT["n_checks"] = len(OUT["checks"])
    OUT["n_mismatches"] = sum(not c["match"] for c in OUT["checks"])
    OUT["n_placebos_failed_as_required"] = sum(p["failed_as_required"] for p in OUT["placebos"])
    OUT["n_placebos"] = len(OUT["placebos"])
    (WS / "audit" / "rederive_extra.json").write_text(json.dumps(OUT, indent=1, default=str))
    print(f"rederive_extra: {OUT['n_checks']} checks, {OUT['n_mismatches']} mismatches "
          f"{[c['name'] for c in OUT['checks'] if not c['match']]}; placebos {OUT['n_placebos_failed_as_required']}/"
          f"{OUT['n_placebos']} failed as required")


if __name__ == "__main__":
    main()
