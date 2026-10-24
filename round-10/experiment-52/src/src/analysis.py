#!/usr/bin/env python3
"""S10 analysis (frozen at commit #1). Matched calls, descriptives, behaviour clusters (complete linkage at 0.95) and
sensitivities, discovery curves, the paired round-block bootstrap, the shuffled-arm placebo, best programs, V3
candidates, the V1/V2/V3/V6 verdict rules.

Stages: python src/analysis.py clusters | best | candidates | verdicts"""
from __future__ import annotations

import io
import json
import re
import sys
import tokenize
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

import clusters as CL  # noqa: E402
import common as C  # noqa: E402

ERR = 65535
CORE = ["T1.0", "T1.6", "DTB", "RPB"]
ALL_ARMS = CORE + ["IDEA", "NS"]
THR_CLUSTER = 0.95
THR_NOVEL = 0.9
V1_FACTOR = 0.8
BF_EXC = {"H-FSW5k": 0.039843042559613666, "H-OR3": 0.05367793240556666}  # gate values (3.9843 %, 5.3678 %)
V2_R_TEMP = 1.5
V2_R_RPB = 1.2
V2_DISC = 1.0
V6_SUP, V6_MARGIN, V6_DISC = 0.4, 0.1, 0.2
N_BOOT = 2000
N_PLACEBO = 200
N_RAREFY = 200
TOP_CLUSTERS_V3 = 20
LEX_A = r"\b(new|novel|different|alternative|instead|unlike|another)\b"
LEX_B = r"\b(idea|approach|strategy|heuristic|method|rule)\b"


# ------------------------------------------------------------------------------------------------ loading
def load_rows() -> tuple[dict, dict]:
    """gen rows and eval rows keyed by (seed, arm, call); superseded rows removed, the last row wins."""
    sup = {(r["seed"], r["arm"], r["call"], r["round"]) for r in C.read_jsonl(C.DATA / "superseded.jsonl")}
    gen: dict = {}
    for S in C.SEEDS:
        for r in C.read_jsonl(C.DATA / f"gen_s{S}.jsonl"):
            if (r["seed"], r["arm"], r["call"], r["round"]) in sup:
                continue
            gen[(r["seed"], r["arm"], r["call"])] = r
    ev: dict = {}
    for r in C.read_eval_rows():  # data/eval/eval_part_*.jsonl, in order
        ev[(r["seed"], r["arm"], r["call"])] = r
    return gen, ev


def load_decisions() -> np.ndarray:
    p = C.DATA / "decisions.bin"
    if not p.exists():
        return np.zeros((0, 2000), dtype=np.uint16)
    a = np.fromfile(p, dtype=np.uint16)
    return a[: (len(a) // 2000) * 2000].reshape(-1, 2000)


def matched_calls(ev: dict) -> dict[int, int]:
    """C per seed = completed (evaluated) calls of the least complete core arm-seed."""
    out = {}
    for S in C.SEEDS:
        n = []
        for a in CORE:
            calls = sorted(c for (s, arm, c) in ev if s == S and arm == a)
            k = 0
            while k < len(calls) and calls[k] == k:
                k += 1
            n.append(k)
        out[S] = int(min(n)) if n else 0
    return out


def arm_calls(ev: dict, S: int, arm: str, Cmax: int) -> list[dict]:
    return [ev[(S, arm, c)] for c in range(Cmax) if (S, arm, c) in ev]


# ------------------------------------------------------------------------------------------------ descriptives
def descriptives(gen: dict, ev: dict, S: int, arm: str, Cm: int) -> dict:
    rows = [gen.get((S, arm, c)) for c in range(Cm)]
    rows = [r for r in rows if r is not None]
    es = arm_calls(ev, S, arm, Cm)
    seen, dup_within = set(), 0
    for e in es:
        if e["key"] is not None:
            if e["key"] in seen:
                dup_within += 1
            seen.add(e["key"])
    et: dict[str, int] = {}
    for e in es:
        et[e["error_type"]] = et.get(e["error_type"], 0) + 1
    disc = 0
    for r in rows:
        br = r.get("branch")
        if br and not br.get("no_branch") and br.get("j") is not None:
            disc += int((r.get("r1_tokens") or 0) - br["j"])
    nf_only = sum(1 for e in es if e["error_type"] == "nonfinite")
    nf_fs_valid = sum(1 for e in es if e["error_type"] == "nonfinite" and e.get("fs_error_type") == "ok")
    return {"n_calls": len(es), "validity": float(np.mean([e["valid"] for e in es])) if es else None,
            "error_types": et, "truncated_share": float(np.mean([r["truncated"] for r in rows])) if rows else None,
            "cache_hit_share": float(np.mean([bool(e["cached"]) for e in es])) if es else None,
            "dup_within_share": dup_within / max(1, len(es)),
            "stochastic_share_valid": float(np.mean([e["stochastic"] for e in es if e["valid"]]))
            if any(e["valid"] for e in es) else None,
            "prompt_tokens": int(sum((r.get("prompt_tokens") or 0) + (r.get("r2_prompt_tokens") or 0) for r in rows)),
            "completion_tokens": int(sum(r.get("completion_tokens") or 0 for r in rows)),
            "discarded_r1_tokens": disc, "nonfinite_only": nf_only, "nonfinite_fs_valid": nf_fs_valid,
            "failed_generation": sum(1 for r in rows if r.get("failed")),
            "no_branch_share": float(np.mean([bool(r.get("branch", {}).get("no_branch")) for r in rows]))
            if rows and rows[0].get("branch") is not None else None}


# ------------------------------------------------------------------------------------------------ clusters
def offspring_vectors(es: list[dict], dec: np.ndarray, include_fs: bool = False, exclude_stochastic: bool = False,
                      max_err: float | None = None, F_below: float | None = None) -> tuple[np.ndarray, list[dict]]:
    keep, vecs = [], []
    for e in es:
        ok = e["valid"] or (include_fs and e["error_type"] == "nonfinite" and e.get("fs_error_type") == "ok")
        if not ok or e.get("probe_row") is None:
            continue
        if exclude_stochastic and e["stochastic"]:
            continue
        F = e["F"] if e["valid"] else e.get("fs_F")
        if F_below is not None and (F is None or F >= F_below):
            continue
        v = dec[e["probe_row"]]
        if max_err is not None and float((v == ERR).mean()) > max_err:
            continue
        keep.append(e)
        vecs.append(v)
    return (np.stack(vecs) if vecs else np.zeros((0, 2000), dtype=np.uint16)), keep


def cluster_programs(vecs: np.ndarray, mask=None) -> tuple[np.ndarray, int]:
    """Complete linkage over the UNIQUE vectors; returns the label of every program and the cluster count."""
    if len(vecs) == 0:
        return np.zeros(0, dtype=int), 0
    u, cnt, inv = CL.unique_with_counts(vecs)
    lab_u = CL.complete_linkage(u, THR_CLUSTER, mask)
    return lab_u[inv], int(len(np.unique(lab_u)))


def discovery_curve(es_kept: list[dict], labels: np.ndarray, Cm: int) -> list[int]:
    first = {}
    for e, lab in zip(es_kept, labels):
        first.setdefault(int(lab), e["call"])
    curve = np.zeros(Cm, dtype=int)
    for c in first.values():
        if c < Cm:
            curve[c] += 1
    return np.cumsum(curve).tolist()


def informative_mask() -> np.ndarray:
    d = json.loads((C.DATA / "probes" / "P10.json").read_text())
    return np.array([len(s[1]) >= 1 for s in d["states"]], dtype=bool)


def stage_clusters() -> dict:
    gen, ev = load_rows()
    dec = load_decisions()
    Cs = matched_calls(ev)
    inf = informative_mask()
    out: dict = {"matched_calls": Cs, "per_arm_seed": {}, "union": {}, "utc": C.utc()}
    labels_store: dict = {}
    for S in C.SEEDS:
        for arm in ALL_ARMS:
            n_arm = len([1 for (s, a, c) in ev if s == S and a == arm])
            Cm = min(Cs[S], n_arm) if arm in CORE + ["IDEA"] else n_arm
            if Cm == 0:
                continue
            es = arm_calls(ev, S, arm, Cm)
            d = {"C": Cm, "desc": descriptives(gen, ev, S, arm, Cm)}
            vecs, kept = offspring_vectors(es, dec)
            lab, k = cluster_programs(vecs)
            d["n_valid_with_vector"] = len(kept)
            d["clusters"] = k
            d["D_per_1000"] = 1000.0 * k / Cm
            leader = CL.leader_clusters(CL.unique_with_counts(vecs)[0], THR_CLUSTER) if len(vecs) else np.zeros(0)
            d["leader_clusters"] = int(len(np.unique(leader))) if len(vecs) else 0
            u = CL.unique_with_counts(vecs)[0] if len(vecs) else vecs
            d["n_unique_vectors"] = int(len(u))
            d["linkage_invariant"] = bool(CL.linkage_invariant(u, CL.complete_linkage(u, THR_CLUSTER), THR_CLUSTER)) \
                if 1 < len(u) <= 3000 else True
            d["discovery_curve"] = discovery_curve(kept, lab, Cm)
            v2, k2 = offspring_vectors(es, dec, F_below=1.0)
            d["clusters_F_below_1"] = cluster_programs(v2)[1]
            tok = d["desc"]["completion_tokens"]
            d["clusters_per_million_tokens"] = 1e6 * k / tok if tok else None
            d["sens_excl_stochastic"] = cluster_programs(offspring_vectors(es, dec, exclude_stochastic=True)[0])[1]
            d["sens_excl_err5"] = cluster_programs(offspring_vectors(es, dec, max_err=0.05)[0])[1]
            d["sens_informative"] = cluster_programs(vecs, inf)[1]
            d["sens_fs_rescored"] = cluster_programs(offspring_vectors(es, dec, include_fs=True)[0])[1]
            out["per_arm_seed"][f"S{S}-{arm}"] = d
            labels_store[(S, arm)] = (kept, lab)
    # rarefied clusters at the minimum valid count across arms within a seed (fixed labels)
    rng = np.random.default_rng(20261024)
    for S in C.SEEDS:
        arms = [a for a in CORE + ["IDEA"] if (S, a) in labels_store]
        if not arms:
            continue
        nmin = min(len(labels_store[(S, a)][1]) for a in arms)
        for a in arms:
            lab = labels_store[(S, a)][1]
            vals = [len(np.unique(rng.choice(lab, size=nmin, replace=False))) if nmin > 0 else 0
                    for _ in range(N_RAREFY)]
            out["per_arm_seed"][f"S{S}-{a}"]["rarefied_clusters"] = {"n": int(nmin), "mean": float(np.mean(vals)),
                                                                     "sd": float(np.std(vals))}
    # union clustering of both seeds per arm
    for arm in CORE + ["IDEA"]:
        vv = []
        for S in C.SEEDS:
            if (S, arm) in labels_store:
                es = labels_store[(S, arm)][0]
                if es:
                    vv.append(np.stack([dec[e["probe_row"]] for e in es]))
        if vv:
            allv = np.concatenate(vv)
            out["union"][arm] = {"clusters": cluster_programs(allv)[1],
                                 "calls": int(sum(out["per_arm_seed"][f"S{S}-{arm}"]["C"] for S in C.SEEDS
                                                  if f"S{S}-{arm}" in out["per_arm_seed"]))}
    out["V2_stats"] = v2_stats(out)
    out["bootstrap"] = round_block_bootstrap(labels_store, Cs)
    out["placebo_shuffled_arms"] = shuffled_arm_placebo(labels_store, Cs, dec)
    C.write_json(C.RESULTS / "analysis_clusters.json", out)
    logger.info("clusters: " + ", ".join(f"{k}: {v['clusters']} ({v['D_per_1000']:.1f}/1k)"
                                         for k, v in out["per_arm_seed"].items()))
    return out


def v2_stats(cl: dict) -> dict:
    pa = cl["per_arm_seed"]

    def rate(arm):
        k = sum(pa[f"S{S}-{arm}"]["clusters"] for S in C.SEEDS if f"S{S}-{arm}" in pa)
        n = sum(pa[f"S{S}-{arm}"]["C"] for S in C.SEEDS if f"S{S}-{arm}" in pa)
        return k / n if n else float("nan")

    R = {X: (rate("DTB") / rate(X) if rate(X) > 0 else float("inf")) for X in ["T1.0", "T1.6", "RPB", "IDEA"]
         if any(f"S{S}-{X}" in pa for S in C.SEEDS)}
    per_seed = {}
    for S in C.SEEDS:
        for X in ["T1.0", "T1.6", "RPB"]:
            a, b = pa.get(f"S{S}-DTB"), pa.get(f"S{S}-{X}")
            if a and b:
                ra, rb = a["clusters"] / a["C"], b["clusters"] / b["C"]
                per_seed[f"S{S}:DTB/{X}"] = ra / rb if rb > 0 else float("inf")
    return {"R": R, "per_seed": per_seed}


def _ratio_from_labels(labs: dict, rounds_by_seed: dict, arms=("DTB", "T1.0", "T1.6", "RPB")) -> dict:
    """Distinct-label rate per arm over the given round multisets, pooled over seeds; R_X = rate(DTB)/rate(X)."""
    rate = {}
    for a in arms:
        k = n = 0
        for S, rounds in rounds_by_seed.items():
            if (S, a) not in labs:
                continue
            kept, lab = labs[(S, a)]
            byr: dict[int, list[int]] = {}
            for e, l in zip(kept, lab):
                byr.setdefault(e["call"] // 20, []).append(int(l))
            seen = set()
            for r in rounds:
                seen.update(byr.get(int(r), []))
            k += len(seen)
            n += 20 * len(rounds)
        rate[a] = k / n if n else float("nan")
    return {X: (rate["DTB"] / rate[X] if rate[X] > 0 else float("inf")) for X in arms if X != "DTB"}


def round_block_bootstrap(labs: dict, Cs: dict) -> dict:
    """Paired block bootstrap over rounds (the same round indices for all arms within a seed; labels fixed)."""
    rng = np.random.default_rng(7)
    reps = {X: [] for X in ["T1.0", "T1.6", "RPB"]}
    for _ in range(N_BOOT):
        rb = {S: rng.integers(0, max(1, Cs[S] // 20), size=max(1, Cs[S] // 20)) for S in C.SEEDS}
        R = _ratio_from_labels(labs, rb)
        for X in reps:
            reps[X].append(R[X])
    return {X: {"median": float(np.median(v)), "ci95": [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]}
            for X, v in reps.items()}


def shuffled_arm_placebo(labs: dict, Cs: dict, dec: np.ndarray) -> dict:
    """Arm labels shuffled across round blocks within a seed (200 shuffles); cluster labels from a joint clustering
    of all core arms within the seed (stated approximation). Counts how often the V2 cluster conditions pass."""
    rng = np.random.default_rng(11)
    joint = {}
    for S in C.SEEDS:
        allk, allv = [], []
        for a in CORE:
            if (S, a) in labs:
                for e in labs[(S, a)][0]:
                    allk.append((a, e["call"]))
                    allv.append(dec[e["probe_row"]])
        if not allv:
            return {"n": 0}
        lab, _ = cluster_programs(np.stack(allv))
        joint[S] = {}
        for (a, c), l in zip(allk, lab):
            joint[S].setdefault((a, c // 20), []).append(int(l))
    n_sup = 0
    for _ in range(N_PLACEBO):
        rates = {a: [0, 0] for a in CORE}
        per_seed_ok = True
        for S in C.SEEDS:
            nr = Cs[S] // 20
            seen = {a: set() for a in CORE}
            for r in range(nr):
                perm = rng.permutation(len(CORE))
                for i, a in enumerate(CORE):
                    seen[CORE[perm[i]]].update(joint[S].get((a, r), []))
            rs = {a: len(seen[a]) / max(1, 20 * nr) for a in CORE}
            for a in CORE:
                rates[a][0] += len(seen[a])
                rates[a][1] += 20 * nr
            per_seed_ok &= all(rs["DTB"] > rs[X] for X in ("T1.0", "T1.6"))
        rr = {a: rates[a][0] / max(1, rates[a][1]) for a in CORE}
        R = {X: rr["DTB"] / rr[X] if rr[X] > 0 else float("inf") for X in ("T1.0", "T1.6", "RPB")}
        if R["T1.0"] >= V2_R_TEMP and R["T1.6"] >= V2_R_TEMP and R["RPB"] >= V2_R_RPB and per_seed_ok:
            n_sup += 1
    return {"n": N_PLACEBO, "supported_share": n_sup / N_PLACEBO, "pass": n_sup / N_PLACEBO <= 0.05,
            "note": "held-out condition of V2 treated as satisfied in every shuffle (conservative)"}


# ------------------------------------------------------------------------------------------------ best programs
def stage_best() -> dict:
    gen, ev = load_rows()
    Cs = matched_calls(ev)
    out = {"matched_calls": Cs, "seed_best": {}, "artifact_best": {}}
    for arm in ALL_ARMS:
        cands = []
        for S in C.SEEDS:
            n_arm = len([1 for (s, a, c) in ev if s == S and a == arm])
            Cm = min(Cs[S], n_arm) if arm != "NS" else n_arm
            es = [e for e in arm_calls(ev, S, arm, Cm) if e["valid"]]
            if not es:
                continue
            best = min(es, key=lambda e: (e["F"], len(gen[(S, arm, e["call"])]["code"]), e["call"]))
            rec = {"seed": S, "arm": arm, "call": best["call"], "F": best["F"], "key": best["key"],
                   "code": gen[(S, arm, best["call"])]["code"], "probe_row": best["probe_row"]}
            out["seed_best"][f"S{S}-{arm}"] = rec
            cands.append(rec)
        if cands:
            out["artifact_best"][arm] = min(cands, key=lambda r: (r["F"], len(r["code"]), r["seed"]))
    C.write_json(C.RESULTS / "best_programs.json", out)
    return out


def stage_candidates() -> dict:
    """V3 candidates: per arm-seed, the best-F program of each of its 20 best clusters (selection data only)."""
    gen, ev = load_rows()
    dec = load_decisions()
    Cs = matched_calls(ev)
    out = []
    for S in C.SEEDS:
        for arm in ALL_ARMS:
            n_arm = len([1 for (s, a, c) in ev if s == S and a == arm])
            Cm = min(Cs[S], n_arm) if arm != "NS" else n_arm
            es = arm_calls(ev, S, arm, Cm)
            vecs, kept = offspring_vectors(es, dec)
            if not kept:
                continue
            lab, _ = cluster_programs(vecs)
            best_by: dict[int, dict] = {}
            for e, l in zip(kept, lab):
                cur = best_by.get(int(l))
                code = gen[(S, arm, e["call"])]["code"]
                if cur is None or (e["F"], len(code), e["call"]) < (cur["F"], len(cur["code"]), cur["call"]):
                    best_by[int(l)] = {"seed": S, "arm": arm, "call": e["call"], "F": e["F"], "key": e["key"],
                                       "probe_row": e["probe_row"], "code": code, "cluster": int(l)}
            ranked = sorted(best_by.values(), key=lambda r: (r["F"], len(r["code"]), r["call"]))[:TOP_CLUSTERS_V3]
            out.extend(ranked)
    C.write_json(C.RESULTS / "v3_candidates.json", out)
    logger.info(f"V3 candidates: {len(out)}")
    return {"n": len(out)}


# ------------------------------------------------------------------------------------------------ verdicts
def v1_verdict(heldout: dict) -> dict:
    """heldout[arm] = {'H-FSW5k': excess, 'H-OR3': excess} for the artifact-best of each arm (fractions)."""
    lim = {s: V1_FACTOR * BF_EXC[s] for s in BF_EXC}
    passes = {a: bool(heldout[a]["H-FSW5k"] <= lim["H-FSW5k"] and heldout[a]["H-OR3"] <= lim["H-OR3"])
              for a in heldout if heldout[a].get("H-FSW5k") is not None and heldout[a].get("H-OR3") is not None}
    beats = {a: bool(heldout[a]["H-FSW5k"] < BF_EXC["H-FSW5k"] or heldout[a]["H-OR3"] < BF_EXC["H-OR3"])
             for a in passes}
    core = [a for a in CORE]
    if all(passes.get(a, False) for a in core):
        v = "SUPPORTED"
    elif not any(beats.get(a, False) for a in core):
        v = "DISCONFIRMED"
    else:
        v = "PARTIAL"
    return {"verdict": v, "limits": lim, "passes": passes, "beats_bf_on_a_primary_set": beats}


def v2_verdict(stats: dict, m: dict) -> dict:
    """m[arm] = mean of exc/exc_BF over the two primary held-out sets for the artifact-best of arm."""
    R, ps = stats["R"], stats["per_seed"]
    conds = {"R_T1.0>=1.5": R.get("T1.0", 0) >= V2_R_TEMP, "R_T1.6>=1.5": R.get("T1.6", 0) >= V2_R_TEMP,
             "per_seed_vs_temps>1": all(v > 1 for k, v in ps.items() if k.endswith("/T1.0") or k.endswith("/T1.6")),
             "R_RPB>=1.2": R.get("RPB", 0) >= V2_R_RPB,
             "m_DTB<=min(m_T1.0,m_T1.6)": (m.get("DTB") is not None and m.get("T1.0") is not None
                                           and m.get("T1.6") is not None and m["DTB"] <= min(m["T1.0"], m["T1.6"]))}
    if all(conds.values()):
        v = "SUPPORTED"
    elif R.get("T1.0", 0) <= V2_DISC or R.get("T1.6", 0) <= V2_DISC:
        v = "DISCONFIRMED"
    else:
        v = "PARTIAL"
    return {"verdict": v, "conditions": conds, "failed": [k for k, ok in conds.items() if not ok], "R": R,
            "per_seed": ps, "m": m}


def v3_verdict(cands: list[dict]) -> dict:
    """cands rows carry pass_08 (bool), max_corpus_agreement, judges {model: class}, manual_class."""
    novel = [c for c in cands if c.get("pass_08") and c.get("max_corpus_agreement", 1.0) < THR_NOVEL
             and c.get("judges_all_not_known") and c.get("manual_class") == "NOVEL"]
    judged = [c for c in cands if c.get("judged")]
    n = len(judged)
    return {"verdict": "SUPPORTED" if novel else "DISCONFIRMED", "n_novel_and_better": len(novel),
            "novel_ids": [c["cid"] for c in novel], "n_candidates": len(cands),
            "n_pass_08": sum(1 for c in cands if c.get("pass_08")),
            "n_pass_both_filters": sum(1 for c in cands if c.get("pass_08") and
                                       c.get("max_corpus_agreement", 1.0) < THR_NOVEL),
            "n_judged": n, "rule_of_three_upper_bound": (3.0 / n) if n else None}


def comment_texts(code: str) -> list[str]:
    out = []
    try:
        for t in tokenize.generate_tokens(io.StringIO(code).readline):
            if t.type == tokenize.COMMENT:
                out.append(t.string)
            elif t.type == tokenize.STRING and t.string.startswith(('"""', "'''")):
                out.append(t.string)
    except (tokenize.TokenError, SyntaxError):
        out = [ln.split("#", 1)[1] for ln in code.splitlines() if "#" in ln]
    return out


def claims_new_idea(code: str) -> bool:
    for c in comment_texts(code):
        if re.search(LEX_A, c, flags=re.I) and re.search(LEX_B, c, flags=re.I):
            return True
    return False


def rename_rates() -> dict:
    gen, ev = load_rows()
    dec = load_decisions()
    Cs = matched_calls(ev)
    pid_vec: dict[str, np.ndarray] = {}
    for (S, arm, c), e in ev.items():
        if e["valid"] and e.get("probe_row") is not None:
            pid_vec[f"S{S}-{arm}-c{c}"] = dec[e["probe_row"]]
    corpus = json.loads((C.RESULTS / "corpus.json").read_text())
    cdec = np.load(C.DATA / "corpus_decisions.npy")
    names = [e["name"] for e in corpus["entries"]]
    pid_vec["seed-BF"] = cdec[names.index("BF")]
    pid_vec["seed-FF"] = cdec[names.index("FF")]
    out = {}
    for arm in ["T1.0", "IDEA", "T1.6", "DTB", "RPB", "NS"]:
        ren, n, lex, nlex = 0, 0, 0, 0
        for S in C.SEEDS:
            n_arm = len([1 for (s, a, c) in ev if s == S and a == arm])
            Cm = min(Cs[S], n_arm) if arm != "NS" else n_arm
            for e in arm_calls(ev, S, arm, Cm):
                g = gen.get((S, arm, e["call"]))
                if g is None:
                    continue
                if g["code"]:
                    nlex += 1
                    lex += int(claims_new_idea(g["code"]))
                if not e["valid"] or e.get("probe_row") is None:
                    continue
                v = dec[e["probe_row"]]
                ags = [CL.agreement_matrix(v, pid_vec[p])[0, 0] for p in g["parent_ids"] if p in pid_vec]
                n += 1
                ren += int(bool(ags) and max(ags) >= THR_CLUSTER)
        out[arm] = {"rename": ren / n if n else None, "n_valid": n, "claims_new_idea_share": lex / nlex if nlex else None}
    return out


def v6_verdict(rr: dict) -> dict:
    ri, rt = rr["IDEA"]["rename"], rr["T1.0"]["rename"]
    if ri is None or rt is None:
        return {"verdict": "NOT_RUN"}
    if ri >= V6_SUP and ri >= rt - V6_MARGIN:
        v = "SUPPORTED"
    elif ri < V6_DISC:
        v = "DISCONFIRMED"
    else:
        v = "PARTIAL"
    return {"verdict": v, "rename_IDEA": ri, "rename_T1.0": rt}


def stage_verdicts() -> dict:
    cl = json.loads((C.RESULTS / "analysis_clusters.json").read_text())
    hb = json.loads((C.RESULTS / "heldout_best.json").read_text())
    heldout = {a: {s: hb["artifact_best"][a]["excess"].get(s) for s in ("H-FSW5k", "H-OR3")}
               for a in hb["artifact_best"]}
    m = {a: float(np.mean([heldout[a][s] / BF_EXC[s] for s in ("H-FSW5k", "H-OR3")]))
         if all(heldout[a].get(s) is not None for s in ("H-FSW5k", "H-OR3")) else None for a in heldout}
    out = {"V1": v1_verdict(heldout), "V2": v2_verdict(cl["V2_stats"], m)}
    out["V2"]["bootstrap"] = cl["bootstrap"]
    out["V2"]["placebo"] = cl["placebo_shuffled_arms"]
    vp = C.RESULTS / "v3_final.json"
    if vp.exists():
        out["V3"] = v3_verdict(json.loads(vp.read_text()))
    rr = rename_rates()
    out["V6"] = v6_verdict(rr)
    out["V6"]["rates"] = rr
    C.write_json(C.RESULTS / "verdicts.json", out)
    logger.info(json.dumps({k: v.get("verdict") for k, v in out.items()}))
    return out


@logger.catch(reraise=True)
def main() -> None:
    C.setup_logging("analysis")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "clusters"
    {"clusters": stage_clusters, "best": stage_best, "candidates": stage_candidates,
     "verdicts": stage_verdicts}[cmd]()


if __name__ == "__main__":
    main()
