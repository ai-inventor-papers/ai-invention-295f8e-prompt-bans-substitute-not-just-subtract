#!/usr/bin/env python3
"""S5 post-search: freeze C_s, behaviour clusters, best programs (held-out once), V1, V2 (+ bootstrap, rarefied,
secondaries, placebo), V3 candidates -> NB set -> joint clusters -> anonymised representatives, V6, evaluator effect.
Stages write results/*.json and are idempotent:  postsearch.py clusters|best|v12|v3|v6|placebo|all"""
from __future__ import annotations

import json
import multiprocessing as mp
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis  # noqa: E402
import bp  # noqa: E402
import cluster  # noqa: E402
import sandbox  # noqa: E402

ROOT = bp.ROOT
RES = ROOT / "results"
SEEDS = (0, 1)
ARMS_MAIN = ["T1.0", "T1.6", "DTB", "RPB", "IDEA"]
HELDOUT_ALL = ["H-FSW5k", "H-OR3", "H-OR1", "H-OR2", "H-OR4", "H-W5k", "H-W10k", "H-SHIFT"]
N_WORKERS = 10


def utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def wjson(name: str, obj) -> None:
    (RES / name).write_text(json.dumps(obj, indent=1, default=float))


def rjson(name: str):
    return json.loads((RES / name).read_text())


def heldout_pct(set_name: str, bins: list[int]) -> float:
    return 100.0 * bp.family_excess(bins, [x["l1"] for x in bp.load_set(set_name)])


def streams() -> list[tuple[str, str, int]]:
    out = [("main", a, s) for s in SEEDS for a in ARMS_MAIN]
    if (ROOT / "data" / "ns" / "programs.jsonl").exists():
        out += [("ns", "NS", s) for s in SEEDS]
    return out


def load_stream(run: str, arm: str, seed: int, c_s: int | None) -> tuple[list[dict], np.ndarray]:
    rows = analysis.stream_rows(analysis.load_rows(run), seed, arm, c_s)
    D = analysis.load_decisions(run, seed, arm)[:len(rows)]
    return rows, D


def c_s_main() -> int:
    rows = analysis.load_rows("main")
    n = {}
    for r in rows:
        n[(r["arm"], r["seed"])] = n.get((r["arm"], r["seed"]), 0) + 1
    core = [n.get((a, s), 0) for a in analysis.CORE for s in SEEDS]
    return min(core)


# ----------------------------------------------------------------------------------------------- (a, b) clusters
def stage_clusters() -> dict:
    t0 = time.time()
    c_s = c_s_main()
    ns_rows = analysis.load_rows("ns")
    c_ns = min([sum(1 for r in ns_rows if r["seed"] == s) for s in SEEDS]) if ns_rows else 0
    out = {"utc": utc(), "C_s": c_s, "C_ns": c_ns, "streams": {}}
    for run, arm, seed in streams():
        cs = c_ns if run == "ns" else c_s
        if arm == "IDEA":
            cs = min(cs, sum(1 for r in analysis.load_rows("main") if r["arm"] == "IDEA" and r["seed"] == seed))
        rows, D = load_stream(run, arm, seed, cs)
        vm = np.array([analysis.valid(r) and not r.get("probe_failed") for r in rows], dtype=bool)
        n_probe_failed = int(sum(analysis.valid(r) and r.get("probe_failed", False) for r in rows))
        Dv = D[vm]
        pre = cluster.unique_counts(Dv)
        lab, n = cluster.complete_linkage(Dv, pre)
        llab, leaders = cluster.leader(Dv)
        call_idx = np.array([r["call_id"] for r, m in zip(rows, vm) if m])
        curves = cluster.discovery_curves(Dv, call_idx, cs, step=100, pre=pre)
        codes = [r["code"] for r, m in zip(rows, vm) if m]
        slab, ns_ = cluster.surface_clusters(codes)
        F = np.array([r["F"] for r, m in zip(rows, vm) if m])
        lab_f1 = lab[F < 1]
        toks = sum(r["n_gen_tokens"] for r in rows)
        out["streams"][f"{run}:{seed}_{arm}"] = {
            "run": run, "arm": arm, "seed": seed, "calls": len(rows), "n_valid": int(vm.sum()),
            "n_probe_failed_singletons": n_probe_failed, "D": int(n + n_probe_failed),
            "D_complete_only": int(n), "leaders": len(leaders), "surface_clusters": int(ns_),
            "surface_per_behaviour": ns_ / max(1, n), "D_F_lt_1": int(len(np.unique(lab_f1))),
            "n_F_lt_1": int((F < 1).sum()), "gen_tokens": int(toks),
            "clusters_per_million_tokens": 1e6 * (n + n_probe_failed) / max(1, toks),
            "validity": float(np.mean([analysis.valid(r) for r in rows])) if rows else None,
            "curves": curves, "labels": lab.tolist(), "valid_call_ids": call_idx.tolist(),
            "leader_labels": llab.tolist(), "best_F": float(F.min()) if len(F) else None}
        logger.info(f"{run}:{seed}_{arm}: calls {len(rows)} valid {int(vm.sum())} D {n} leaders {len(leaders)} "
                    f"surface {ns_} ({time.time() - t0:.0f}s)")
    wjson("clusters.json", out)
    wjson("curves.json", {k: {"curves": v["curves"], "arm": v["arm"], "seed": v["seed"]} for k, v in out["streams"].items()})
    return out


# ----------------------------------------------------------------------------------------------- (c) best programs
def eval_heldout(codes: list[str], sets: list[str], limit: float = 120.0) -> list[dict]:
    pool = sandbox.EvalPool(N_WORKERS, ROOT, as_gib=2.0)
    futs = [pool.submit({"code": c, "sets": sets, "limit": limit, "fail_fast": False, "probes": []}) for c in codes]
    res = [f.result() for f in futs]
    pool.close()
    out = []
    for r in res:
        out.append({"heldout_excess_pct": {s: heldout_pct(s, b) for s, b in r["bins"].items()},
                    "heldout_bins": r["bins"], "error": None if r["error_type"] == "ok" else
                    f"{r['error_type']}: {r.get('msg', '')}"})
    return out


def stage_best() -> dict:
    cl = rjson("clusters.json")
    best = {}
    for key, st in cl["streams"].items():
        run, arm, seed = st["run"], st["arm"], st["seed"]
        rows, _ = load_stream(run, arm, seed, st["calls"])
        val = [r for r in rows if analysis.valid(r)]
        if not val:
            continue
        b = min(val, key=lambda r: (r["F"], len(r["code"])))
        best[key] = {"pid": b["pid"], "arm": arm, "seed": seed, "run": run, "F": b["F"], "code": b["code"],
                     "call_id": b["call_id"], "round": b["round"]}
    keys = list(best)
    ho = eval_heldout([best[k]["code"] for k in keys], HELDOUT_ALL)
    for k, h in zip(keys, ho):
        best[k].update(h)
    wjson("best_programs.json", {"utc": utc(), "best": best})
    return best


# ----------------------------------------------------------------------------------------------- V1 / V2
def best_of_arm(best: dict, arm: str) -> dict | None:
    cands = [v for v in best.values() if v["arm"] == arm]
    if not cands:
        return None
    b = min(cands, key=lambda v: (v["F"], len(v["code"])))
    ho = b.get("heldout_excess_pct", {})
    return {"pid": b["pid"], "F": b["F"], "exc_FSW5k": ho.get("H-FSW5k"), "exc_OR3": ho.get("H-OR3"),
            "heldout_excess_pct": ho, "seed": b["seed"]}


def _rarefy_job(args):
    D, n, reps, seed = args
    rng = np.random.default_rng(seed)
    return float(np.mean([cluster.complete_linkage(D[rng.choice(len(D), n, replace=False)])[1] for _ in range(reps)]))


def stage_v12() -> dict:
    cl, best = rjson("clusters.json"), rjson("best_programs.json")["best"]
    st = cl["streams"]
    c_s = cl["C_s"]
    bests = {a: best_of_arm(best, a) for a in ARMS_MAIN + ["NS"]}
    v1 = analysis.v1(bests)
    v1["per_arm_heldout"] = {a: (bests[a] or {}).get("heldout_excess_pct") for a in analysis.CORE}
    v1["per_arm_best"] = {a: {k: v for k, v in (bests[a] or {}).items()} for a in ARMS_MAIN + ["NS"]}
    corpus = json.loads((ROOT / "results" / "corpus.json").read_text())
    ref = {e["name"]: e["heldout_excess_pct"] for e in corpus["table"]}
    ref["c12"] = ref.get("c12_vec", ref.get("c12"))
    c2 = json.loads((ROOT / "predictions" / "commit2.json").read_text())
    v1["beside"] = {"IDEA": bests.get("IDEA"), "NS": bests.get("NS"),
                    "tuned_ab": {"name": c2["tuned_ab"]["name"], **ref.get(c2["tuned_ab"]["name"], {})},
                    "c12": ref.get("c12"), "c14": ref.get("c14"), "abFF_5_24": ref.get("abFF_5_24"),
                    "abWF_1_21": ref.get("abWF_1_21"), "BF": ref.get("BF")}
    v1["per_seed_best"] = {k: {"F": v["F"], **{s: v.get("heldout_excess_pct", {}).get(s) for s in ("H-FSW5k", "H-OR3")}}
                           for k, v in best.items()}
    wjson("v1.json", v1)
    D = {(st[f"main:{s}_{a}"]["arm"], s): st[f"main:{s}_{a}"]["D"] for a in analysis.CORE for s in SEEDS}
    C = {s: st[f"main:{s}_T1.0"]["calls"] for s in SEEDS}
    v2 = analysis.v2(D, C, bests)
    v2["C_s"] = c_s
    v2["D"] = {f"{a}|{s}": d for (a, s), d in D.items()}
    # secondaries
    sec = {}
    sec["rates_F_lt_1"] = {a: 1000 * sum(st[f"main:{s}_{a}"]["D_F_lt_1"] for s in SEEDS) / (C[0] + C[1])
                           for a in analysis.CORE}
    sec["clusters_per_million_tokens"] = {a: 1e6 * sum(st[f"main:{s}_{a}"]["D"] for s in SEEDS) /
                                          max(1, sum(st[f"main:{s}_{a}"]["gen_tokens"] for s in SEEDS))
                                          for a in analysis.CORE}
    sec["leader_counts"] = {f"{a}|{s}": st[f"main:{s}_{a}"]["leaders"] for a in analysis.CORE for s in SEEDS}
    sec["surface_per_behaviour"] = {f"{a}|{s}": st[f"main:{s}_{a}"]["surface_per_behaviour"]
                                    for a in ARMS_MAIN for s in SEEDS}
    for name, d in (("R1_F_lt_1", "T1.0"), ("R2_F_lt_1", "T1.6"), ("R3_F_lt_1", "RPB")):
        sec[name] = sec["rates_F_lt_1"]["DTB"] / sec["rates_F_lt_1"][d] if sec["rates_F_lt_1"][d] else None
    for name, d in (("R1_per_token", "T1.0"), ("R2_per_token", "T1.6"), ("R3_per_token", "RPB")):
        sec[name] = sec["clusters_per_million_tokens"]["DTB"] / sec["clusters_per_million_tokens"][d]
    # rarefied: per seed, at the minimum valid count across the four core arms (200 random subsets)
    keys, vals = [], []
    for s in SEEDS:
        n_min = min(st[f"main:{s}_{a}"]["n_valid"] for a in analysis.CORE)
        for a in analysis.CORE:
            rows, Dm = load_stream("main", a, s, c_s)
            vm = np.array([analysis.valid(r) and not r.get("probe_failed") for r in rows], dtype=bool)
            Dv = Dm[vm]
            pre = cluster.unique_counts(Dv)
            rng = np.random.default_rng(20261027 + s)
            n = min(n_min, len(Dv))
            vals.append(float(np.mean([cluster.clusters_in_subset(pre[1], pre[2], rng.choice(len(Dv), n, replace=False))
                                       for _ in range(200)])))
            keys.append((a, s, n_min))
    sec["rarefied"] = {f"{a}|{s}": {"n": n, "mean_clusters": v} for (a, s, n), v in zip(keys, vals)}
    rar = {a: sum(sec["rarefied"][f"{a}|{s}"]["mean_clusters"] for s in SEEDS) for a in analysis.CORE}
    sec["R1_rarefied"], sec["R2_rarefied"], sec["R3_rarefied"] = (rar["DTB"] / rar["T1.0"], rar["DTB"] / rar["T1.6"],
                                                                   rar["DTB"] / rar["RPB"])
    # paired round-block bootstrap on full-run labels
    labels, rounds = {}, {}
    for a in analysis.CORE:
        for s in SEEDS:
            ss = st[f"main:{s}_{a}"]
            lab = np.array(ss["labels"])
            rd = np.array(ss["valid_call_ids"]) // 25
            labels[(a, s)], rounds[(a, s)] = lab, rd
    n_rounds = {s: c_s // 25 for s in SEEDS}
    v2["bootstrap"] = analysis.round_block_bootstrap(labels, rounds, n_rounds, B=2000)
    v2["secondaries"] = sec
    wjson("v2.json", v2)
    logger.info(f"V1 {v1['verdict']}  V2 {v2['verdict']} R1 {v2['R1']:.3f} R2 {v2['R2']:.3f} R3 {v2['R3']:.3f}")
    return {"v1": v1, "v2": v2}


# ----------------------------------------------------------------------------------------------- V3
def corpus_vectors() -> tuple[list[str], np.ndarray, list[dict]]:
    c = json.loads((ROOT / "data" / "corpus" / "corpus.json").read_text())
    ents = [e for e in c["entries"] if e.get("decisions") is not None]
    return [e["name"] for e in ents], np.array([e["decisions"] for e in ents], dtype=np.uint16), ents


def stage_v3() -> dict:
    cl = rjson("clusters.json")
    names, CV, ents = corpus_vectors()
    ab = json.loads((ROOT / "data" / "corpus" / "ab_grid.json").read_text())
    ABV = np.array([p["decisions"] for p in ab["points"] if p["decisions"] is not None], dtype=np.uint16)
    ab_names = [f"ab{p['base']}({p['a']},{p['b']})" for p in ab["points"] if p["decisions"] is not None]
    cands = []
    for key, st in cl["streams"].items():
        rows, D = load_stream(st["run"], st["arm"], st["seed"], st["calls"])
        vm = [analysis.valid(r) and not r.get("probe_failed") for r in rows]
        vr = [r for r, m in zip(rows, vm) if m]
        Dv = D[np.array(vm, dtype=bool)]
        lab = np.array(st["labels"])
        clF = {}
        for i, (r, l) in enumerate(zip(vr, lab)):
            if l not in clF or (r["F"], len(r["code"])) < (vr[clF[l]]["F"], len(vr[clF[l]]["code"])):
                clF[l] = i
        top = sorted(clF.items(), key=lambda kv: (vr[kv[1]]["F"], len(vr[kv[1]]["code"])))[:20]
        for l, i in top:
            r = vr[i]
            cands.append({"pid": r["pid"], "stream": key, "arm": st["arm"], "seed": st["seed"], "F": r["F"],
                          "code": r["code"], "cluster": int(l), "dec": Dv[i]})
    logger.info(f"V3: {len(cands)} candidates")
    Dc = np.stack([c["dec"] for c in cands])
    A = cluster.agree_counts(Dc, CV) / cluster.N_STATES
    A_ab = cluster.agree_counts(Dc, ABV) / cluster.N_STATES
    ho = eval_heldout([c["code"] for c in cands], ["H-FSW5k", "H-OR3"])
    thr_fs, thr_or = analysis.THR_FSW5K, analysis.THR_OR3
    for c, a, aab, h in zip(cands, A, A_ab, ho):
        top3 = np.argsort(-a, kind="stable")[:3]
        c.update(max_corpus_agreement=float(a.max()), nearest_corpus=names[int(a.argmax())],
                 nearest3=[[names[int(j)], float(a[j])] for j in top3],
                 max_abgrid_agreement=float(aab.max()), nearest_abgrid=ab_names[int(aab.argmax())],
                 exc_FSW5k=h["heldout_excess_pct"].get("H-FSW5k"), exc_OR3=h["heldout_excess_pct"].get("H-OR3"),
                 heldout_error=h["error"])
        c["pass_FSW5k"] = c["exc_FSW5k"] is not None and c["exc_FSW5k"] <= thr_fs
        c["pass_OR3"] = c["exc_OR3"] is not None and c["exc_OR3"] <= thr_or
        c["pass_agree"] = c["max_corpus_agreement"] < 0.9
        c["NB"] = c["pass_FSW5k"] and c["pass_OR3"] and c["pass_agree"]
        c["NB_strict"] = c["NB"] and c["max_abgrid_agreement"] < 0.9
    nb = [c for c in cands if c["NB"]]
    out = {"utc": utc(), "n_candidates": len(cands), "n_NB": len(nb), "n_NB_strict": sum(c["NB_strict"] for c in cands),
           "fail_counts": {"OR3": sum(not c["pass_OR3"] for c in cands), "FSW5k": sum(not c["pass_FSW5k"] for c in cands),
                           "agreement": sum(not c["pass_agree"] for c in cands),
                           "pass_both_heldout": sum(c["pass_OR3"] and c["pass_FSW5k"] for c in cands)},
           "per_stream": {}}
    for key in cl["streams"]:
        cs = [c for c in cands if c["stream"] == key]
        out["per_stream"][key] = {"n_cand": len(cs), "n_NB": sum(c["NB"] for c in cs)}
    # positive control: permuting each corpus vector across states must raise the NB count
    rng = np.random.default_rng(20261030)
    CVp = np.stack([v[rng.permutation(len(v))] for v in CV])
    Ap = cluster.agree_counts(Dc, CVp) / cluster.N_STATES
    out["positive_control_NB_with_permuted_corpus"] = int(sum(c["pass_FSW5k"] and c["pass_OR3"] and ap.max() < 0.9
                                                              for c, ap in zip(cands, Ap)))
    best_ho = min((c for c in cands if c["exc_FSW5k"] is not None and c["exc_OR3"] is not None),
                  key=lambda c: c["exc_FSW5k"] / analysis.BF_FSW5K + c["exc_OR3"] / analysis.BF_OR3, default=None)
    beats_bf = [c for c in cands if c["F"] < 1]
    most_diff = min(beats_bf, key=lambda c: c["max_corpus_agreement"], default=None)
    strip = lambda c: None if c is None else {k: v for k, v in c.items() if k != "dec"}  # noqa: E731
    out["best_heldout_candidate"] = strip(best_ho)
    out["most_different_beating_BF"] = strip(most_diff)
    closest = min(cands, key=lambda c: c["max_corpus_agreement"]) if cands else None
    out["lowest_max_agreement_candidate"] = strip(closest)
    # joint clusters of the NB set + representatives
    reps = []
    if nb:
        Dn = np.stack([c["dec"] for c in nb])
        jl, nj = cluster.complete_linkage(Dn)
        for j in range(nj):
            mem = [c for c, l in zip(nb, jl) if l == j]
            r = min(mem, key=lambda c: (c["F"], len(c["code"])))
            r["joint_cluster"], r["joint_size"] = j, len(mem)
            r["joint_members"] = [m["pid"] for m in mem]
            reps.append(r)
        groups: dict[str, list] = {}
        for r in sorted(reps, key=lambda c: c["F"]):
            groups.setdefault(r["stream"], []).append(r)
        order = sorted(groups, key=lambda g: groups[g][0]["F"])
        audited = []
        while len(audited) < 30 and any(groups[g] for g in order):
            for g in order:
                if groups[g] and len(audited) < 30:
                    audited.append(groups[g].pop(0))
        perm = np.random.default_rng(20261029).permutation(len(audited))
        for k, (r, p) in enumerate(zip(audited, perm)):
            r["anon_id"] = f"cand_{int(p):02d}"
        out["n_joint_clusters"], out["n_representatives"] = nj, len(reps)
        out["n_audited"], out["n_unaudited_representatives"] = len(audited), len(reps) - len(audited)
        ho8 = eval_heldout([r["code"] for r in audited], HELDOUT_ALL)
        for r, h in zip(audited, ho8):
            r["heldout_all"] = h["heldout_excess_pct"]
        blind = [{"anon_id": r["anon_id"], "code": r["code"]} for r in sorted(audited, key=lambda r: r["anon_id"])]
        (ROOT / "audit" / "blind_read_sheet.json").write_text(json.dumps(blind, indent=1))
        (ROOT / "audit" / "arm_map_SEALED.json").write_text(json.dumps(
            {r["anon_id"]: {"pid": r["pid"], "stream": r["stream"]} for r in audited}, indent=1))
        out["audited"] = [strip(r) for r in audited]
    else:
        out["n_joint_clusters"] = out["n_representatives"] = out["n_audited"] = 0
        out["audited"] = []
    out["candidates"] = [strip(c) for c in cands]
    wjson("v3_candidates.json", out)
    logger.info(f"V3: NB {len(nb)} (strict {out['n_NB_strict']}), joint clusters {out['n_joint_clusters']}, "
                f"audited {out['n_audited']}; positive control NB {out['positive_control_NB_with_permuted_corpus']}")
    return out


# ----------------------------------------------------------------------------------------------- V6 / evaluator
def comment_text(code: str) -> str:
    parts = re.findall(r"#[^\n]*", code)
    parts += re.findall(r'"""(.*?)"""', code, re.S) + re.findall(r"'''(.*?)'''", code, re.S)
    return " ".join(parts)


def stage_v6() -> dict:
    names, CV, _ = corpus_vectors()
    bf_dec = CV[names.index("BF")]
    ff_dec = CV[names.index("FF")]
    rows = analysis.load_rows("main")
    decs = {(a, s): analysis.load_decisions("main", s, a) for a in ARMS_MAIN for s in SEEDS}
    pid_dec = {}
    for r in rows:
        f, i = r["dec_ref"]
        seed, arm = f[:-4].split("_", 1)
        pid_dec[r["pid"]] = (arm, int(seed), i)

    def dec_of(pid: str) -> np.ndarray:
        if pid == "seed-BF":
            return bf_dec
        if pid == "seed-FF":
            return ff_dec
        a, s, i = pid_dec[pid]
        return decs[(a, s)][i]

    cl = rjson("clusters.json")
    out = {}
    rx = re.compile(analysis.NEW_IDEA_RX, re.I)
    for arm in ARMS_MAIN:
        k = n = claims = 0
        for s in SEEDS:
            cs = cl["streams"][f"main:{s}_{arm}"]["calls"]
            for r in analysis.stream_rows(rows, s, arm, cs):
                if not analysis.valid(r) or r.get("probe_failed"):
                    continue
                d = dec_of(r["pid"])
                ag = max(cluster.agreement(d, dec_of(p)) for p in r["parent_ids"])
                k += int(ag >= 0.95)
                n += 1
                claims += int(bool(rx.search(comment_text(r["code"]))))
        out[arm] = {"renames": k, "n_valid": n, "rate": k / max(1, n), "new_idea_claim_share": claims / max(1, n),
                    "wilson": analysis.wilson(k, n)}
    v6 = analysis.v6(out["IDEA"]["renames"], out["IDEA"]["n_valid"], out["T1.0"]["renames"], out["T1.0"]["n_valid"])
    v6["per_arm"] = out
    # NS (fixed FF/BF parents) for reference
    ns_rows = analysis.load_rows("ns")
    if ns_rows:
        k = n = 0
        nsd = {s: analysis.load_decisions("ns", s, "NS") for s in SEEDS}
        for r in ns_rows:
            if not analysis.valid(r) or r.get("probe_failed"):
                continue
            d = nsd[r["seed"]][r["dec_ref"][1]]
            k += int(max(cluster.agreement(d, bf_dec), cluster.agreement(d, ff_dec)) >= 0.95)
            n += 1
        v6["NS_reference"] = {"renames": k, "n_valid": n, "rate": k / max(1, n)}
    wjson("v6.json", v6)
    logger.info(f"V6 {v6['verdict']}: IDEA {v6['rate_IDEA']:.3f} T1.0 {v6['rate_T1.0']:.3f}")
    return v6


def stage_evaluator() -> dict:
    """T1.0's first 1,000 calls against NS (1,000 per seed): best F, held-out of the best, clusters."""
    if not (ROOT / "data" / "ns" / "programs.jsonl").exists():
        wjson("evaluator_effect.json", {"skipped": "NS not run"})
        return {}
    out = {}
    for run, arm in (("main", "T1.0"), ("ns", "NS")):
        per = {}
        for s in SEEDS:
            rows, D = load_stream(run, arm, s, 1000)
            vm = np.array([analysis.valid(r) and not r.get("probe_failed") for r in rows], dtype=bool)
            val = [r for r, m in zip(rows, vm) if m]
            b = min(val, key=lambda r: (r["F"], len(r["code"]))) if val else None
            per[s] = {"calls": len(rows), "valid": int(vm.sum()), "D": cluster.complete_linkage(D[vm])[1],
                      "best_F": None if b is None else b["F"], "best_pid": None if b is None else b["pid"],
                      "best_code": None if b is None else b["code"]}
        out[arm] = per
    codes = [out[a][s]["best_code"] for a in ("T1.0", "NS") for s in SEEDS]
    ho = eval_heldout(codes, ["H-FSW5k", "H-OR3"])
    i = 0
    for a in ("T1.0", "NS"):
        for s in SEEDS:
            out[a][s]["best_heldout"] = ho[i]["heldout_excess_pct"]
            i += 1
    wjson("evaluator_effect.json", out)
    return out


def stage_placebo() -> dict:
    """(a) 200 within-seed arm-label shuffles of DTB and T1.0 rows; (b) a random-priority program fails V1;
    (c) a disguised c14 lands at agreement >= 0.9 to the corpus."""
    cl = rjson("clusters.json")
    c_s = cl["C_s"]
    da, db = {}, {}
    for s in SEEDS:
        for arm, store in (("DTB", da), ("T1.0", db)):
            rows, D = load_stream("main", arm, s, c_s)
            vm = np.array([analysis.valid(r) and not r.get("probe_failed") for r in rows], dtype=bool)
            store[s] = D[vm]
    vals = []
    rng = np.random.default_rng(20261028)
    pools = {s: cluster.unique_counts(np.concatenate([da[s], db[s]])) for s in SEEDS}
    for _ in range(200):
        a_cnt = b_cnt = 0
        for s in SEEDS:
            _, inv, C = pools[s]
            perm = rng.permutation(len(inv))
            na = len(da[s])
            a_cnt += cluster.clusters_in_subset(inv, C, perm[:na])
            b_cnt += cluster.clusters_in_subset(inv, C, perm[na:])
        vals.append(a_cnt / b_cnt if b_cnt else float("nan"))
    out = {"a_label_shuffle": {"n": len(vals), "share_R1_ge_1.5": float(np.mean([v >= 1.5 for v in vals])),
                               "R1_shuffled_p50": float(np.median(vals)), "R1_shuffled_p2.5": float(np.percentile(vals, 2.5)),
                               "R1_shuffled_p97.5": float(np.percentile(vals, 97.5))}}
    rnd = "def priority(item, bins):\n    return np.random.default_rng(int(item) * 7919 + len(bins)).random(len(bins))\n"
    disg = ("def priority(item, bins):\n    top = np.max(bins)\n    sq = bins * bins\n"
            "    s = (bins - top) * (bins - top) / item + sq / (item * item) + sq / (item * item * item)\n"
            "    over = bins > item\n    s[over] = -1.0 * s[over]\n    s[1:] = s[1:] - s[:-1]\n    return s\n")
    ho = eval_heldout([rnd, disg], ["H-FSW5k", "H-OR3"])
    r_ok = not ((ho[0]["heldout_excess_pct"].get("H-FSW5k", 99) <= analysis.THR_FSW5K) and
                (ho[0]["heldout_excess_pct"].get("H-OR3", 99) <= analysis.THR_OR3))
    out["b_random_priority_fails_V1"] = {"pass": bool(r_ok), "heldout": ho[0]["heldout_excess_pct"]}
    fn, _, _ = sandbox.compile_program(disg)
    st = json.loads((ROOT / "data" / "probes" / "P1.json").read_text())["states"]
    arrs = [(int(it), np.array(list(of) + [int(cap)] * int(ne))) for it, of, ne, cap in st]
    dd = sandbox._probe_decisions(fn, arrs)
    names, CV, _ = corpus_vectors()
    ag = cluster.agree_counts(dd[None, :], CV)[0] / cluster.N_STATES
    out["c_disguised_c14"] = {"pass": bool(ag.max() >= 0.9), "max_agreement": float(ag.max()),
                              "nearest": names[int(ag.argmax())]}
    wjson("placebos.json", out)
    return out


def _shuffle_job(args):
    da, db, n, seed = args
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n):
        a_cnt = b_cnt = 0
        for s in SEEDS:
            pool = np.concatenate([da[s], db[s]])
            perm = rng.permutation(len(pool))
            na = len(da[s])
            a_cnt += cluster.complete_linkage(pool[perm[:na]])[1]
            b_cnt += cluster.complete_linkage(pool[perm[na:]])[1]
        vals.append(a_cnt / b_cnt if b_cnt else float("nan"))
    return vals


@logger.catch(reraise=True)
def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(ROOT / "logs" / "postsearch.log", rotation="30 MB", level="DEBUG")
    stages = {"clusters": stage_clusters, "best": stage_best, "v12": stage_v12, "v3": stage_v3, "v6": stage_v6,
              "evaluator": stage_evaluator, "placebo": stage_placebo}
    todo = list(stages) if sys.argv[1] == "all" else sys.argv[1].split(",")
    for s in todo:
        t0 = time.time()
        logger.info(f"stage {s} ...")
        stages[s]()
        logger.info(f"stage {s} done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
