#!/usr/bin/env python3
"""Second independent re-derivation (headline numbers NOT covered by audit/rederive.py), from raw files only and
through a different code path (pandas groupby + scipy.special.logsumexp; nothing imported from src/):

- sampled event counts quoted in README (baseline, modal ban, two-step) from data/labelled.jsonl;
- the per-sample predictor comparison (FRLP top-1 vs sampled ladder / latent ladder / association), with a paired
  sign-flip permutation test of FRLP vs the sampled ladder and a PLACEBO (a random survivor predictor must not beat it);
- route-test fractions F_prompt / F_direct and the own-drop D_X table, from frlp/scores_<task>.parquet;
- Llama label-audit agreement (from the per-program pairs) and OpenRouter spend (from the judge cache records).
Writes results/independent_rederivation_headlines.json and prints mismatches (tolerance 1e-9 for model quantities).
Run: .venv/bin/python audit/rederive_headlines.py
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logsumexp

ROOT = Path(__file__).resolve().parent.parent
CAT = {"t1": ["bfs", "dfs", "bibfs", "iddfs", "astar_gbfs", "dijkstra"], "t2": ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"]}


def jl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def frlp_tables(task: str, excluded: set[str]) -> tuple[pd.DataFrame, list[str]]:
    """Long table of FRLP cells L(cond, j, half in {1, 2, 'all'}) via groupby + logsumexp."""
    meta = pd.DataFrame([r for r in jl(ROOT / "data" / "forced_set.jsonl") if r["task"] == task
                         and r["scrub_mode"] != "dropped" and f"{task}:{r['j']}" not in excluded])[["program_id", "j", "half"]]
    sc = pd.read_parquet(ROOT / "frlp" / f"scores_{task}.parquet").merge(meta, on="program_id")
    forced = sc[sc["condition_id"].str.match(r"forced(_desc)?:")]
    forced = forced[forced["condition_id"].str.split(":").str[1] == forced["j"]]
    lq = forced.groupby("program_id")["l_full"].apply(lambda x: logsumexp(x.to_numpy()) - np.log(len(x))).rename("lq")
    sc = sc.merge(lq, on="program_id")
    sc["D"] = sc["l_full"] - sc["lq"]
    agg = lambda x: logsumexp(x.to_numpy()) - np.log(len(x))  # noqa: E731
    half = sc.groupby(["condition_id", "j", "half"])["D"].apply(agg).reset_index()
    full = sc.groupby(["condition_id", "j"])["D"].apply(agg).reset_index().assign(half="all")
    algs = [a for a in CAT[task] if a in set(meta["j"])]
    return pd.concat([half, full], ignore_index=True).set_index(["condition_id", "j", "half"])["D"], algs


def main() -> int:
    summ = json.loads((ROOT / "results" / "forced_set_summary.json").read_text())["per_algorithm"]
    excluded = {k for k, v in summ.items() if v["excluded_M_lt_10"]}
    sel = json.loads((ROOT / "results" / "selections.json").read_text())
    lab = jl(ROOT / "data" / "labelled.jsonl")
    checks, fails = [], []

    def chk(name, mine, reported, tol=1e-9):
        ok = (mine == reported) if isinstance(mine, (str, int)) and not isinstance(mine, bool) and isinstance(reported, (str, int)) \
            else abs(float(mine) - float(reported)) <= tol * max(1.0, abs(float(reported)))
        checks.append({"quantity": name, "rederived": mine, "reported": reported, "match": bool(ok)})
        if not ok:
            fails.append(name)

    # ---- sampled events (counts)
    ev = json.loads((ROOT / "results" / "events.json").read_text())
    for task in ("t1", "t2"):
        d = sel[f"{task}_default"]
        for name, f in (("baseline", lambda r: r["kind"] == "baseline"),
                        (f"ban:{d} (modal)", lambda r: r["kind"] == "ban" and r["X"] == d and r["phase"] == "A4"),
                        ("twostep", lambda r: r["kind"] == "twostep")):
            c = collections.Counter(r["label"] for r in lab if r["task"] == task and f(r) and r["label"] != "no_code")
            rep = next(e for e in ev[task] if e["name"] == name or (name == "twostep" and e["name"].startswith("twostep")))
            for k in set(c) | set(rep["attempted_counts"]):
                chk(f"events.{task}.{name}.{k}", c.get(k, 0), rep["attempted_counts"].get(k, 0))
    # ---- FRLP tables and per-sample predictions
    tabs = {t: frlp_tables(t, excluded) for t in ("t1", "t2")}
    fr = jl(ROOT / "data" / "free_answers.jsonl")
    assoc = {t: collections.defaultdict(collections.Counter) for t in ("t1", "t2")}
    for r in fr:
        assoc[r["task"]][r["X"]][r["label"]] += 1
    base = {t: collections.Counter(r["label"] for r in lab if r["task"] == t and r["kind"] == "baseline") for t in ("t1", "t2")}
    rows = []
    for r in lab:
        if r["phase"] not in ("A1", "A4", "A5", "C"):
            continue
        t = r["task"]
        L, algs = tabs[t]
        banned = [r["X"]] if r["kind"] == "ban" else (r["X"].split("+") if r["kind"] == "twostep" else [])
        if r["label"] == "no_code" or r["label"] in banned:
            continue
        Se = [j for j in algs if j not in banned]
        Lc = np.array([L.get((r["condition"], j, "all"), np.nan) for j in Se])
        p_frlp = Se[int(np.nanargmax(Lc))]
        lat = np.array([np.mean([L[(f"baseline:s{s}", j, "all")] for s in range(5)]) for j in Se])
        p_lat = Se[int(np.argmax(lat))]
        p_smp = sorted(Se, key=lambda j: (-base[t].get(j, 0), Se.index(j)))[0]
        X = r["X"] if r["kind"] == "ban" else (sel[f"{t}_default"] if r["kind"] == "twostep" else None)
        if X is None:
            p_ass = p_lat
        else:
            cnt = assoc[t][X]
            best = sorted(Se, key=lambda j: (-cnt.get(j, 0), Se.index(j)))[0]
            p_ass = best if cnt.get(best, 0) > 0 else p_lat
        rows.append({"ev": f"{t}|{r['kind']}|{r['X']}", "y": r["label"], "frlp": p_frlp, "lat": p_lat, "smp": p_smp,
                     "ass": p_ass, "Se": Se, "ban": r["kind"] == "ban"})
    df = pd.DataFrame(rows)
    rep = json.loads((ROOT / "method_out.json").read_text())["metadata"]["predictor_comparison_per_event"]
    for col, key in (("frlp", "acc_frlp_top1"), ("lat", "acc_latent_ladder"), ("smp", "acc_sampled_ladder"), ("ass", "acc_association")):
        chk(f"predictors.ALL.{key}", float((df[col] == df["y"]).mean()), rep["ALL"][key])
        chk(f"predictors.SINGLE_BANS.{key}", float((df[df["ban"]][col] == df[df["ban"]]["y"]).mean()), rep["SINGLE_BANS"][key])
    chk("predictors.ALL.n", int(len(df)), rep["ALL"]["n"])
    # paired sign-flip permutation test: FRLP vs sampled ladder (all samples and single bans)
    rng = np.random.default_rng(0)

    def paired_test(a: np.ndarray, b: np.ndarray, n: int = 20000) -> dict:
        dlt = a.astype(float) - b.astype(float)
        obs = dlt.mean()
        flips = rng.choice([-1.0, 1.0], size=(n, len(dlt)))
        null = (flips * dlt).mean(axis=1)
        return {"mean_diff": float(obs), "p_two_sided": float(np.mean(np.abs(null) >= abs(obs) - 1e-12)),
                "p_frlp_better": float(np.mean(null >= obs - 1e-12))}

    tests = {}
    for scope, sub in (("ALL", df), ("SINGLE_BANS", df[df["ban"]])):
        tests[scope] = paired_test((sub["frlp"] == sub["y"]).to_numpy(), (sub["smp"] == sub["y"]).to_numpy())
        # placebo: a random survivor predictor in place of FRLP must NOT significantly beat the sampled ladder
        rnd = np.array([Se[rng.integers(len(Se))] for Se in sub["Se"]])
        tests[f"{scope}_placebo_random_vs_sampled_ladder"] = paired_test(rnd == sub["y"].to_numpy(), (sub["smp"] == sub["y"]).to_numpy())
    # ---- route test and own-drop
    num = {"a": 0.0, "c": 0.0, "d": 0.0}
    own = {}
    for t in ("t1", "t2"):
        L, algs = tabs[t]
        d = sel[f"{t}_default"]
        for w in range(1, 6):
            for h in (1, 2):
                b_ = L[(f"neutral:{d}:w{w}:h{h}", d, h)]
                num["a"] += L[(f"ban:{d}:w{w}", d, h)] - b_
                num["c"] += L[(f"route_c:{d}:w{w}:h{h}", d, h)] - b_
                num["d"] += L[(f"route_d:{d}:w{w}:h{h}", d, h)] - b_
        for X in algs:
            ban = np.mean([L[(f"ban:{X}:w{w}", X, h)] for w in range(1, 6) for h in (1, 2)])
            neu = np.mean([L[(f"neutral:{X}:w{w}:h{h}", X, h)] for w in range(1, 6) for h in (1, 2)])
            men = np.mean([L[(f"mention:{X}:w{w}", X, h)] for w in range(1, 6) for h in (1, 2)])
            own[f"{t}:{X}"] = {"D_X": ban - neu, "prime": men - neu, "veto": ban - men}
    c1 = json.loads((ROOT / "results" / "c1.json").read_text())
    chk("route.F_prompt", num["c"] / num["a"], c1["route"]["F_prompt"])
    chk("route.F_direct", num["d"] / num["a"], c1["route"]["F_direct"])
    chk("route.sum_D_a", num["a"], c1["route"]["sum_D_a"])
    for key, v in own.items():
        t, X = key.split(":")
        for k in ("D_X", "prime", "veto"):
            chk(f"own_drop.{key}.{k}", v[k], c1["cosine"][t]["own_drop"][X][k])
    # ---- label audit agreement and spend
    audit = json.loads((ROOT / "results" / "llama_label_audit.json").read_text())
    judged = [q for q in audit["pairs"] if q["audit_judge"]]
    chk("audit.agreement", sum(q["combined"] == q["audit_judge"] for q in judged) / len(judged), audit["agreement"])
    spend = sum(float(r.get("cost") or 0.0) for r in jl(ROOT / "data" / "judge_cache.jsonl"))
    cost = json.loads((ROOT / "results" / "openrouter_cost.json").read_text())
    out = {"n_checks": len(checks), "n_fail": len(fails), "fails": fails, "checks": checks,
           "predictor_tests": tests, "judge_cache_cost_sum_usd": spend, "ledger_total_usd": cost["total_usd"],
           "note": "the ledger also counts calls whose responses were retried (unparsable) and therefore not cached"}
    (ROOT / "results" / "independent_rederivation_headlines.json").write_text(json.dumps(out, indent=1, default=float))
    print(f"headline rederivation: {len(checks) - len(fails)}/{len(checks)} match")
    print("tests:", json.dumps(tests))
    print(f"spend: judge-cache sum {spend:.4f} vs ledger {cost['total_usd']:.4f}")
    for f_ in fails:
        print("MISMATCH", f_)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
