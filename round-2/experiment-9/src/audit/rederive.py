#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers from the raw files, through code that shares nothing with the
pipeline modules (no imports from common / mb / analysis): plain json + hashlib + numpy + scipy.special.

Re-derived: forced keep shares; single-ban, multi-ban and LOS landing counts and avoidance; disguise counts for
the multi-bans; FRLP base cells (L, ESS) from data/scores.jsonl + data/denominators.json; FRLP-implied avoidance per
banned set from the raw scores; the commitment hash chain and its order against the first session-2 request; the
exact survivor-permutation p for ARC. Placebos: the permutation test on random survivor shares (must not reject more
than its level) and on shuffled condition labels (the realised avoidance contrast must vanish).
Writes results/independent_rederivation.json.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np
from scipy.special import logsumexp

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"
R = ROOT / "results"


def jl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def landing(rows: list[dict], banned: set[str]) -> dict:
    att = [r for r in rows if r.get("code") and r["label"] not in ("unknown", "no_code", "inconsistent")]
    nb = sum(1 for r in att if r["label"] in banned)
    c: dict[str, int] = {}
    for r in att:
        c[r["label"]] = c.get(r["label"], 0) + 1
    return {"n": len(rows), "attempted": len(att), "banned": nb, "avoidance": 1 - nb / len(att) if att else None,
            "counts": dict(sorted(c.items()))}


def ranks(v: list[float]) -> np.ndarray:
    a = np.asarray(v, float)
    order = np.argsort(a, kind="mergesort")
    rk = np.empty(len(a))
    i = 0
    while i < len(a):
        j = i
        while j + 1 < len(a) and a[order[j + 1]] == a[order[i]]:
            j += 1
        rk[order[i:j + 1]] = (i + j) / 2
        i = j + 1
    return rk


def rho(x: list[float], y: list[float]) -> float | None:
    rx, ry = ranks(x), ranks(y)
    if rx.std() == 0 or ry.std() == 0:
        return None
    return float(np.corrcoef(rx, ry)[0, 1])


def perm_p(pred: list[float], shares: list[float]) -> float | None:
    obs = rho(pred, shares)
    if obs is None:
        return None
    vals = [rho(pred, list(p)) for p in itertools.permutations(shares)]
    vals = [v for v in vals if v is not None]
    return sum(1 for v in vals if v >= obs - 1e-12) / len(vals)


def main() -> None:
    out: dict = {}
    # 1) keep shares: rebuild the 40 forced programs per algorithm from the raw labelled files
    var = json.loads((D / "variant_decisions.json").read_text())["algorithms"]
    smoke, rest = jl(D / "labelled_smoke.jsonl"), jl(D / "labelled_forced_rest.jsonl")
    keep = {}
    for k, v in var.items():
        task, alg = k.split(":")
        cond = f"forced_desc:{alg}" if v["variant"] == "desc" else f"forced:{alg}"
        pool = rest if v["variant"] == "desc" else smoke + rest
        rows = [r for r in pool if r["task"] == task and r["condition"] == cond]
        keep[k] = {"n": len(rows), "as_requested": sum(r["label"] == alg for r in rows)}
    out["keep"] = keep
    out["n_t1_kept_ge_70pct"] = sum(1 for k, v in keep.items() if k.startswith("t1:") and v["as_requested"] >= 0.7 * v["n"])
    # 2) landing counts
    s1, s2 = jl(D / "labelled_session1.jsonl"), jl(D / "labelled_session2.jsonl")
    out["single_bfs_t1"] = landing([r for r in s1 if r["condition"] == "single:bfs"], {"bfs"})
    out["single_dijkstra_t2"] = landing([r for r in s1 if r["condition"] == "single:dijkstra"], {"dijkstra"})
    plan = json.loads((R / "planned_conditions.json").read_text())["t1"]
    out["multi"] = {}
    for s, p in plan.items():
        rows = [r for r in s2 if r["condition"] == f"multi:{s}"]
        lg = landing(rows, set(p["banned"]))
        br = [r for r in rows if r["label"] in p["banned"]]
        fam = {"bfs": ["bfs", "breadth-first", "breadth first", "breadth_first"],
               "dfs": ["dfs", "depth-first", "depth first", "depth_first"],
               "gbfs": ["greedy", "best-first", "best first", "best_first"],
               "iddfs": ["iddfs", "iterative deepening", "iterative_deepening"],
               "astar": ["a*", "a-star", "astar", "a_star"], "bibfs": ["bidirectional", "bidir"],
               "idastar": ["ida*", "ida_star", "idastar"]}
        named = sum(1 for r in br if any(a in r["text"].lower() for a in fam.get(r["label"], [])))
        lg["disguised"] = len(br) - named
        lg["disguise_rate"] = (len(br) - named) / len(br) if br else None
        out["multi"][s] = lg
    out["los"] = {}
    for s in ("dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"):
        rows = [r for r in s1 if r["condition"] == f"los:{s}"]
        att = [r for r in rows if r.get("code") and r["label"] not in ("unknown", "no_code", "inconsistent")]
        out["los"][s] = {"attempted": len(att), "survivor": sum(r["label"] == s for r in att),
                         "will": sum(r["label"] == s for r in att) / len(att)}
    # 3) FRLP base cells from raw scores + denominators
    sc = {}
    for r in jl(D / "scores.jsonl"):
        sc[(r["prompt_key"], r["uid"])] = r["l"]
    den = json.loads((D / "denominators.json").read_text())
    psets = json.loads((D / "program_sets.json").read_text())
    base, base_unique = {}, {}
    for key, v in psets.items():
        task, alg = key.split(":")
        for q in v["programs"]:  # with multiplicity: a program generated twice is two IS samples
            d = den[q["uid"]]
            base.setdefault((task, alg), []).append(d["l_base"] - d["l_F"])
    for uid, d in den.items():
        base_unique.setdefault((d["task"], d["algorithm"]), []).append(d["l_base"] - d["l_F"])
    out["n_duplicate_programs"] = {k: len(v["programs"]) - len({q["uid"] for q in v["programs"]}) for k, v in psets.items()}
    out["frlp_base_unique_programs"] = {f"{t}:{a}": float(logsumexp(np.array(r)) - math.log(len(r)))
                                        for (t, a), r in sorted(base_unique.items())}
    out["frlp_base"] = {}
    for (task, alg), r in sorted(base.items()):
        r = np.array(r)
        out["frlp_base"][f"{task}:{alg}"] = {"L": float(logsumexp(r) - math.log(len(r))),
                                             "ess": float(math.exp(2 * logsumexp(r) - logsumexp(2 * r))), "M": len(r)}
    # l_F recomputed from the 10 raw forced-prompt scores of one program per algorithm
    chk = []
    for uid, d in list(den.items())[::25]:
        ks = [sc[(f"{d['task']}|forced:{d['algorithm']}|{k}", uid)] for k in range(10)]
        chk.append(abs(float(logsumexp(ks) - math.log(10)) - d["l_F"]))
    out["l_F_recompute_max_abs_diff"] = max(chk)
    # 4) FRLP-implied avoidance from raw scores (exp(L) mass of banned vs survivors under the ban prompts)
    keepj = json.loads((R / "catalogue_keep.json").read_text())["tasks"]["t1"]
    progs = json.loads((D / "program_sets.json").read_text())
    out["implied_avoidance"] = {}
    for s, p in plan.items():
        mass = {"surv": 0.0, "ban": 0.0}
        for w in ("W1", "W2", "W3", "W4", "W5"):
            pk = f"t1|multi:{s}|{w}|ban"
            for alg in p["survivors"] + p["banned"]:
                ps = [q for q in progs[f"t1:{alg}"]["programs"] if alg in p["survivors"] or q["half"] == 1]
                rr = np.array([sc[(pk, q["uid"])] - den[q["uid"]]["l_F"] for q in ps])
                L = float(logsumexp(rr) - math.log(len(rr))) + math.log(keepj[alg]["share"])
                mass["surv" if alg in p["survivors"] else "ban"] += math.exp(L) / 5
        out["implied_avoidance"][s] = mass["surv"] / (mass["surv"] + mass["ban"])
    # 5) commitment chain, independently re-hashed
    lines = (ROOT / "commitments.log").read_text().splitlines()
    prev, ok = "0" * 64, True
    for ln in lines:
        e = json.loads(ln)
        ok &= e["prev_line_sha256"] == prev
        p = ROOT / e["payload_path"]
        raw = p.read_bytes()
        h = hashlib.sha256(json.dumps(json.loads(raw), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                           .encode()).hexdigest() if p.suffix == ".json" else hashlib.sha256(raw).hexdigest()
        ok &= h == e["payload_sha256"]
        prev = hashlib.sha256(ln.encode()).hexdigest()
    first_s2 = min(r["gen_start_utc"] for r in jl(D / "raw_session2.jsonl"))
    out["commit_chain_ok"] = bool(ok)
    out["last_commit_before_first_session2_request"] = json.loads(lines[-1])["utc_time"] < first_s2
    # 6) exact permutation p for ARC (realised survivor shares vs the committed LADDER forecast)
    fc = json.loads((ROOT / "predictions" / "forecasts_ARC.json").read_text())
    att = [r for r in s2 if r["condition"] == "multi:ARC" and r.get("code")]
    shares = [sum(r["label"] == j for r in att) for j in fc["survivors"]]
    tot = sum(shares)
    shares = [x / tot for x in shares] if tot else shares
    out["ARC_perm_p"] = {f: perm_p([fc["forecasts_raw"][f][j] for j in fc["survivors"]], shares)
                         for f in fc["forecasts_raw"]}
    # placebo A: random survivor shares -> rejection rate at p <= 1/3 must stay near its level
    rng = np.random.default_rng(1)
    pred = [fc["forecasts_raw"]["LADDER"][j] for j in fc["survivors"]]
    ps = [perm_p(pred, list(rng.dirichlet(np.ones(len(pred))))) for _ in range(600)]
    ps = [p for p in ps if p is not None]
    out["placebo_random_shares"] = {"n": len(ps), "share_p_le_1/3": float(np.mean(np.array(ps) <= 1 / 3 + 1e-9)),
                                    "share_p_le_1/6": float(np.mean(np.array(ps) <= 1 / 6 + 1e-9))}
    # placebo B: shuffle condition labels among the four multi-ban conditions -> avoidance differences vanish
    rows = [r for r in s2 if r.get("code") and r["label"] not in ("unknown", "no_code", "inconsistent")]
    conds = [r["condition"] for r in rows]
    real = {c: 1 - np.mean([r["label"] in plan[c.split(':')[1]]["banned"] for r in rows if r["condition"] == c])
            for c in set(conds)}
    sh = []
    for _ in range(200):
        perm = rng.permutation(conds)
        av = {c: 1 - np.mean([r["label"] in plan[c.split(':')[1]]["banned"] for r, cc in zip(rows, perm) if cc == c])
              for c in set(conds)}
        sh.append(max(av.values()) - min(av.values()))
    out["placebo_shuffled_conditions"] = {"real_range": float(max(real.values()) - min(real.values())),
                                          "shuffled_range_mean": float(np.mean(sh)),
                                          "shuffled_range_95": float(np.percentile(sh, 95))}
    (R / "independent_rederivation.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1)[:6000])


if __name__ == "__main__":
    main()
