"""Stage 5 analysis driver (uses the committed functions in src/analysis.py).

Writes results/{search_summary, clusters, rarefaction, heldout, heldout_raw, verdict_v1, verdict_v2, v3,
decisions_export, timing, deviations}.json. Usage: python src/analyze_run.py [--no-heldout] [--workers N]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis as an  # noqa: E402
from common import DATA, LOGS, PRED, RESULTS, ROOT, read_jsonl, setup_logging, utc_now, write_json  # noqa: E402

logger = setup_logging("analysis")
ARMS = ["T1.0", "T1.6", "DTB", "RPB", "IDEA"]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def load_rows() -> list[dict]:
    seen = {}
    for r in read_jsonl(DATA / "calls.jsonl"):
        seen.setdefault((r["arm"], r["seed"], r["call_idx"]), r)
    return list(seen.values())


def load_decisions() -> dict[str, np.ndarray]:
    idx = {r["ast_hash"]: r["rec"] for r in read_jsonl(DATA / "probe_index.jsonl")}
    raw = np.fromfile(DATA / "probe_decisions.bin", dtype=np.int16)
    M = raw.reshape(-1, 2000)
    return {h: M[k] for h, k in idx.items() if k < len(M)}


def matched_rounds(rows: list[dict]) -> dict[int, int]:
    """Last round completed (32 calls each) by every core arm and IDEA of a seed."""
    out = {}
    for s in (0, 1):
        last = []
        for a in ARMS:
            cnt = Counter(r["round"] for r in rows if r["arm"] == a and r["seed"] == s)
            r_ok = -1
            while cnt.get(r_ok + 1, 0) == 32:
                r_ok += 1
            last.append(r_ok)
        out[s] = min(last)
    return out


def per_arm_summary(rs: list[dict]) -> dict:
    n = len(rs)
    labs = Counter(r["label"] for r in rs)
    v = labs.get("valid", 0)
    pv = sum(bool(r.get("probe_valid")) for r in rs)
    best, curve = float("inf"), []
    for r in sorted(rs, key=lambda r: r["call_idx"]):
        if r.get("probe_valid") and r.get("F") is not None:
            best = min(best, r["F"])
        curve.append(best if math.isfinite(best) else None)
    return {"calls": n, "valid": v, "validity": v / n if n else None, "validity_wilson95": wilson(v, n),
            "probe_valid": pv, "probe_valid_share": pv / n if n else None,
            "error_shares": {k: c / n for k, c in labs.items()},
            "truncated_share": sum(bool(r.get("truncated")) for r in rs) / n if n else None,
            "trimmed_share": sum((r.get("trimmed_lines") or 0) > 0 for r in rs) / n if n else None,
            "gen_tokens": int(sum(r.get("gen_tokens") or 0 for r in rs)),
            "prompt_tokens": int(sum(r.get("prompt_tokens") or 0 for r in rs)),
            "discarded_tokens": int(sum(r.get("discarded_tokens") or 0 for r in rs)),
            "better_than_NN_share": sum(1 for r in rs if r.get("F") is not None and r["F"] < 1) / n if n else None,
            "best_F": None if not math.isfinite(best) else best, "best_so_far_F": curve,
            "ast_cache_dup_share": 1 - len({r["ast_hash"] for r in rs if r.get("ast_hash")}) /
            max(1, sum(1 for r in rs if r.get("ast_hash")))}


def dtb_diag(rs: list[dict]) -> dict:
    d = [r["dtb"] for r in rs if r.get("dtb")]
    br = [x for x in d if not x.get("no_branch")]
    by_rank = defaultdict(lambda: [0, 0])
    for r in rs:
        x = r.get("dtb")
        if x and not x.get("no_branch"):
            by_rank[x["forced_rank"]][0] += r["label"] == "valid"
            by_rank[x["forced_rank"]][1] += 1
    H = [x["H_j_star"] for x in br if x.get("H_j_star") is not None]
    return {"n": len(d), "no_branch_share": 1 - len(br) / len(d) if d else None,
            "H_j_star_median": float(np.median(H)) if H else None, "H_j_star_mean": float(np.mean(H)) if H else None,
            "H_j_star_values": H,
            "j_star_hist": dict(Counter(int(x["j_star"]) for x in br)),
            "position_frac": [x.get("position_frac") for x in br],
            "forced_rank_hist": dict(Counter(int(x["forced_rank"]) for x in br)),
            "validity_by_forced_rank": {k: v[0] / v[1] for k, v in sorted(by_rank.items())},
            "forced_eq_sampled_share": float(np.mean([bool(x.get("forced_eq_sampled")) for x in br])) if br else None,
            "forced_class_shares": {k: c / len(br) for k, c in Counter(x.get("forced_class") for x in br).items()},
            "sampled_class_shares": {k: c / len(br) for k, c in Counter(x.get("sampled_class") for x in br).items()},
            "id_op_kw_share": float(np.mean([x.get("forced_class") in ("identifier", "operator", "keyword")
                                             for x in br])) if br else None,
            "H_rank_among_eligible_hist": dict(Counter(int(x["H_rank_among_eligible"]) for x in br
                                                       if x.get("H_rank_among_eligible") is not None))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-heldout", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    rows_all = load_rows()
    dec = load_decisions()
    base = json.loads((RESULTS / "baselines.json").read_text())
    nn_g200 = base["NN"]["G200"]
    mr = matched_rounds(rows_all)
    rows = [r for r in rows_all if r["arm"] == "NOSEL" or r["round"] <= mr[r["seed"]]]
    logger.info(f"rows {len(rows_all)}; matched rounds per seed {mr}; analysed rows {len(rows)}")
    by = defaultdict(list)
    for r in rows:
        by[(r["arm"], r["seed"])].append(r)
    keys = [(x, s) for s in (0, 1) for x in ARMS if (x, s) in by]
    # ---------------- 5.1 summaries
    summary = {f"{x}|{s}": per_arm_summary(by[(x, s)]) for x, s in keys}
    if ("NOSEL", 0) in by:
        summary["NOSEL|0"] = per_arm_summary(by[("NOSEL", 0)])
    diag = {f"{x}|{s}": dtb_diag(by[(x, s)]) for x, s in keys if x in ("DTB", "RPB")}
    # ---------------- 5.2 clusters
    cl: dict = {"per_arm_seed": {}, "threshold": an.THRESH, "matched_rounds": mr}
    labels_by, rounds_by, cpr_by, ids_by = {}, {}, {}, {}
    for x, s in keys:
        rs = sorted(by[(x, s)], key=lambda r: r["call_idx"])
        pv = [r for r in rs if r.get("probe_valid") and r.get("ast_hash") in dec]
        X = np.array([dec[r["ast_hash"]] for r in pv]) if pv else np.zeros((0, 2000), np.int16)
        res = an.cluster_programs(X)
        sec_idx = [i for i, r in enumerate(pv) if r["F"] < 1]
        res2 = an.cluster_programs(X[sec_idx]) if sec_idx else {"n_clusters": 0, "labels": np.zeros(0, int)}
        N = len(rs)
        gen = sum(r.get("gen_tokens") or 0 for r in rs)
        ci = np.array([r["call_idx"] for r in pv])
        disc = an.discovery_curve(ci, res["labels"], N) if len(pv) else [0] * N
        disc2 = an.discovery_curve(ci[sec_idx], res2["labels"], N) if sec_idx else [0] * N
        cl["per_arm_seed"][f"{x}|{s}"] = {
            "calls": N, "probe_valid": len(pv), "unique_vectors": res["n_unique"],
            "primary_clusters": res["n_clusters"], "secondary_clusters": res2["n_clusters"],
            "secondary_programs": len(sec_idx),
            "rate_per_1000_calls": 1000 * res["n_clusters"] / N, "secondary_rate_per_1000": 1000 * res2["n_clusters"] / N,
            "rate_per_1M_gen_tokens": 1e6 * res["n_clusters"] / max(1, gen),
            "shannon": an.shannon(res["labels"]), "min_within_agreement": an.min_within_agreement(
                res["U"], res["labels_unique"]) if res["n_unique"] else None,
            "discovery_primary": disc, "discovery_secondary": disc2}
        labels_by[(x, s)] = res["labels"]
        rounds_by[(x, s)] = np.array([r["round"] for r in pv])
        cpr_by[(x, s)] = dict(Counter(r["round"] for r in rs))
        ids_by[(x, s)] = [r["ast_hash"] for r in pv]
    # rarefaction to the minimum number of probe-valid programs across the arms of a seed
    rare = {}
    for s in (0, 1):
        ks = [(x, s) for x in ARMS if (x, s) in labels_by]
        m = min(len(labels_by[k]) for k in ks)
        for k in ks:
            rare[f"{k[0]}|{s}"] = an.rarefy(labels_by[k], m, 1000, seed=s)
    cl["rarefaction"] = rare
    # paired round-block bootstrap of per-seed ratios DTB / X
    ratios = {}
    for s in (0, 1):
        for xx in ("T1.0", "T1.6", "RPB", "IDEA"):
            if ("DTB", s) not in labels_by or (xx, s) not in labels_by:
                continue
            c_d = cl["per_arm_seed"][f"DTB|{s}"]
            c_x = cl["per_arm_seed"][f"{xx}|{s}"]
            r_pt = an.per_seed_ratio({("DTB", s): c_d["primary_clusters"], (xx, s): c_x["primary_clusters"]},
                                     {("DTB", s): c_d["calls"], (xx, s): c_x["calls"]}, "DTB", xx, s)
            bs = an.round_block_bootstrap(rounds_by[("DTB", s)], labels_by[("DTB", s)], cpr_by[("DTB", s)],
                                          rounds_by[(xx, s)], labels_by[(xx, s)], cpr_by[(xx, s)], 1000, seed=s)
            r_sec = (c_d["secondary_rate_per_1000"] / c_x["secondary_rate_per_1000"]
                     if c_x["secondary_rate_per_1000"] > 0 else None)
            r_tok = (c_d["rate_per_1M_gen_tokens"] / c_x["rate_per_1M_gen_tokens"]
                     if c_x["rate_per_1M_gen_tokens"] > 0 else None)
            r_rare = (rare[f"DTB|{s}"]["exact_mean"] / rare[f"{xx}|{s}"]["exact_mean"]
                      if rare[f"{xx}|{s}"]["exact_mean"] > 0 else None)
            ratios[f"{xx}|{s}"] = {"ratio": r_pt, "boot95": bs, "secondary_ratio": r_sec, "per_token_ratio": r_tok,
                                   "rarefied_ratio": r_rare}
    cl["ratios_per_seed"] = ratios
    # pooled complete linkage over all arm-seeds (per seed if > 8000 unique vectors)
    allh = sorted({h for k in ids_by for h in ids_by[k]})
    pooled = {"mode": "all", "n_unique": len(allh)}
    groups = [list(ids_by)] if len(allh) <= 8000 else [[k for k in ids_by if k[1] == s] for s in (0, 1)]
    if len(allh) > 8000:
        pooled["mode"] = "per_seed (unique vectors > 8000)"
    pooled["per_arm_seed"] = {}
    for g in groups:
        hs = sorted({h for k in g for h in ids_by[k]})
        U = np.array([dec[h] for h in hs])
        lab = an.cluster_labels_unique(U)
        hl = dict(zip(hs, lab.tolist()))
        sets = {k: {hl[h] for h in ids_by[k]} for k in g}
        for k in g:
            others = set().union(*[sets[o] for o in g if o[0] != k[0] and o[1] == k[1]]) if len(g) > 1 else set()
            pooled["per_arm_seed"][f"{k[0]}|{k[1]}"] = {"distinct_pooled_clusters": len(sets[k]),
                                                        "unique_to_arm_within_seed": len(sets[k] - others)}
        pooled.setdefault("n_pooled_clusters", []).append(int(len(set(lab.tolist()))))
    cl["pooled"] = pooled
    cl["utc"] = utc_now()
    write_json(RESULTS / "clusters.json", cl)
    write_json(RESULTS / "rarefaction.json", rare)
    # decisions export for the stdlib re-derivation (hex bytes, ERR = 255)
    exp = {}
    for k in ids_by:
        for h in ids_by[k]:
            if h not in exp:
                v = dec[h]
                exp[h] = bytes([(int(t) if t >= 0 else 255) for t in v]).hex()
    write_json(RESULTS / "decisions_export.json", exp, indent=None)
    # ---------------- IDEA rename rate (and T1.0's same statistic)
    hash_of = {f"{r['arm']}|{r['seed']}|{r['call_idx']}": r.get("ast_hash") for r in rows_all}
    nn_dec = np.array(json.loads((DATA / "nn_probe_decisions.json").read_text()))
    rename = {}
    for x in ("IDEA", "T1.0", "T1.6", "DTB", "RPB"):
        for s in (0, 1):
            rs = [r for r in by.get((x, s), []) if r.get("probe_valid") and r.get("ast_hash") in dec]
            hit = 0
            for r in rs:
                v = dec[r["ast_hash"]]
                ag = []
                for pid in r["parent_ids"]:
                    pv_ = nn_dec if pid == "NN" else dec.get(hash_of.get(pid))
                    if pv_ is not None:
                        ag.append(float(np.mean(v == pv_)))
                hit += bool(ag) and max(ag) >= 0.95
            rename[f"{x}|{s}"] = {"n": len(rs), "share_agree_ge_0.95_with_a_parent": hit / len(rs) if rs else None}
    # ---------------- 5.3 held-out
    held: dict = {"arm_best": {}, "others": {}}
    raw: dict = {"arm_best": {}, "NN": {"heldout_gaps": base["NN"]["heldout"]["gaps"]}}
    if not a.no_heldout:
        import evaluator as ev
        from tsp_task import load_tsplib

        refs = ev.load_references()
        names = [t["name"] for t in load_tsplib()]
        pool = ev.make_pool(a.workers)
        todo = {}
        for x, s in keys:
            b = an.best_program(by[(x, s)])
            if b:
                todo[f"{x}|{s}"] = b
        if ("NOSEL", 0) in by:
            nos = by[("NOSEL", 0)]
            bN = an.best_program(nos)
            nN = len(nos)
            t10 = [r for r in by.get(("T1.0", 0), []) if r["call_idx"] < nN]
            if bN:
                todo["NOSEL|0"] = bN
            bT = an.best_program(t10)
            if bT:
                todo[f"T1.0|0_first{nN}"] = bT
        futs = {}
        for key, b in todo.items():
            for set_name in ("heldout", "heldout_ext", "tsplib"):
                futs[(key, set_name)] = pool.submit(ev.job_set, b["code"], set_name, 600)
        for (key, set_name), f in futs.items():
            r = f.result()
            b = todo[key]
            d = held["arm_best"].setdefault(key, {"call_idx": b["call_idx"], "F": b["F"], "G50": b["G50"],
                                                  "G100": b["G100"], "ast_hash": b["ast_hash"], "code": b["code"]})
            if r["label"] != "valid":
                d[f"{set_name}_label"] = r["label"]
                continue
            if set_name == "tsplib":
                tg = ev.tsplib_gaps(r["tours"], names)
                d["tsplib_gaps"] = tg
                d["tsplib_mean"] = float(np.mean(list(tg.values())))
                d["tsplib_tours"] = {n_: t for n_, t in zip(names, r["tours"]) if n_ in ("kroA100", "ch150")}
            else:
                g = ev.gaps_from_lengths(r["lengths"], refs[set_name])
                d["heldout_gaps" if set_name == "heldout" else "ext_gaps"] = g.tolist()
                d["G200" if set_name == "heldout" else "G200_ext"] = float(g.mean())
        nn_h = np.array(base["NN"]["heldout"]["gaps"])
        nn_e = np.array(base["NN"]["heldout_ext"]["gaps"])
        for key, d in held["arm_best"].items():
            if "heldout_gaps" in d:
                d["ci_vs_NN"] = an.paired_bootstrap_diff(np.array(d["heldout_gaps"]), nn_h)
                d["closes_frac_of_NN_gap"] = 1 - d["G200"] / nn_g200
            if "ext_gaps" in d:
                d["ci_vs_NN_ext"] = an.paired_bootstrap_diff(np.array(d["ext_gaps"]), nn_e)
            raw["arm_best"][key] = {"heldout_gaps": d.get("heldout_gaps"), "call_idx": d["call_idx"], "F": d["F"]}
        comp = {}
        for s in (0, 1):
            for xx in ("T1.0", "T1.6", "RPB", "IDEA"):
                A_, B_ = held["arm_best"].get(f"DTB|{s}", {}), held["arm_best"].get(f"{xx}|{s}", {})
                if "heldout_gaps" in A_ and "heldout_gaps" in B_:
                    comp[f"DTB-{xx}|{s}"] = an.paired_bootstrap_diff(np.array(A_["heldout_gaps"]),
                                                                    np.array(B_["heldout_gaps"]))
        held["paired_DTB_vs"] = comp
        # P1 at C* and corpus members (from results/corpus.json, evaluated by src/corpus.py)
        corpus = json.loads((RESULTS / "corpus.json").read_text()) if (RESULTS / "corpus.json").exists() else None
        if corpus:
            for m in corpus["members"]:
                if m.get("admitted") and m.get("G200") is not None:
                    o = {"kind": "corpus:" + m["family"], "G200": m["G200"], "G200_ext": m.get("G200_ext"),
                         "tsplib_mean": m.get("tsplib_mean"), "F": m.get("F")}
                    o["ci_vs_NN"] = an.paired_bootstrap_diff(np.array(m["heldout_gaps"]), nn_h)
                    held["others"][m["name"]] = o
                    if m["name"] == "tuned_P1_at_Cstar":
                        held["P1"] = o
        held["others"]["NN"] = {"kind": "baseline", "G200": nn_g200, "G200_ext": base["NN"]["G200_ext"],
                                "tsplib_mean": base["NN"]["tsplib"]["mean_gap"], "F": 1.0}
        for nm, v in base["reference_heuristics"]["heldout"].items():
            held["others"][nm] = {"kind": "reference (other interface)", "G200": v["mean_gap"],
                                  "G200_ext": base["reference_heuristics"]["heldout_ext"][nm]["mean_gap"],
                                  "tsplib_mean": base["reference_heuristics"]["tsplib"][nm]["mean_gap"],
                                  "F": base["reference_heuristics"]["selection"][nm]["F"]}
        # ---------------- 5.6 V3 pool: best member of each of the 5 best clusters per arm-seed -> HELDOUT
        corp_dec = {}
        if corpus:
            for m in corpus["members"]:
                p = DATA / "corpus_decisions" / f"{m['name']}.json"
                if m.get("admitted") and p.exists():
                    corp_dec[m["name"]] = np.array(json.loads(p.read_text()))
        v3pool = []
        for x, s in keys:
            rs = [r for r in by[(x, s)] if r.get("probe_valid") and r.get("ast_hash") in dec]
            lab = labels_by[(x, s)]
            best_in = {}
            for r, l in zip(sorted(rs, key=lambda r: r["call_idx"]), lab):
                if l not in best_in or (r["F"], r["call_idx"]) < (best_in[l]["F"], best_in[l]["call_idx"]):
                    best_in[l] = r
            top = sorted(best_in.values(), key=lambda r: (r["F"], r["call_idx"]))[:5]
            for r in top:
                v3pool.append((f"{x}|{s}", r))
        f2 = {i: pool.submit(ev.job_set, r["code"], "heldout", 600) for i, (_, r) in enumerate(v3pool)}
        v3 = {"pool": [], "candidates": [], "bar": 0.8 * nn_g200, "corpus_members": sorted(corp_dec)}
        for i, (key, r) in enumerate(v3pool):
            res = f2[i].result()
            g = (float(ev.gaps_from_lengths(res["lengths"], refs["heldout"]).mean()) if res["label"] == "valid"
                 else None)
            v = dec[r["ast_hash"]]
            ag = {nm: float(np.mean(v == cd)) for nm, cd in corp_dec.items()}
            near = sorted(ag.items(), key=lambda kv: -kv[1])[:3]
            item = {"arm_seed": key, "call_idx": r["call_idx"], "F": r["F"], "G200": g, "ast_hash": r["ast_hash"],
                    "max_corpus_agreement": max(ag.values()) if ag else None, "nearest_corpus": near,
                    "code": r["code"]}
            item["candidate"] = g is not None and g <= 0.8 * nn_g200 and (not ag or max(ag.values()) < 0.90)
            v3["pool"].append(item)
            if item["candidate"]:
                v3["candidates"].append(item)
        v3["n_candidates_per_arm"] = dict(Counter(c["arm_seed"].split("|")[0] for c in v3["candidates"]))
        write_json(RESULTS / "v3.json", v3)
        pool.shutdown()
    held["utc"] = utc_now()
    write_json(RESULTS / "heldout.json", held)
    write_json(RESULTS / "heldout_raw.json", raw)
    # ---------------- 5.4 / 5.5 verdicts
    g200 = {}
    for x in an.CORE_ARMS:
        for s in (0, 1):
            g200[(x, s)] = held["arm_best"].get(f"{x}|{s}", {}).get("G200")
    v1 = an.verdict_v1(g200, nn_g200)
    v1["IDEA"] = {s: held["arm_best"].get(f"IDEA|{s}", {}).get("G200") for s in (0, 1)}
    c = {(x, s): cl["per_arm_seed"][f"{x}|{s}"]["primary_clusters"] for x in an.CORE_ARMS for s in (0, 1)
         if f"{x}|{s}" in cl["per_arm_seed"]}
    N = {(x, s): cl["per_arm_seed"][f"{x}|{s}"]["calls"] for x in an.CORE_ARMS for s in (0, 1)
         if f"{x}|{s}" in cl["per_arm_seed"]}
    v2 = an.verdict_v2(c, N, g200)
    c2 = {(x, s): cl["per_arm_seed"][f"{x}|{s}"]["secondary_clusters"] for x, s in c}
    v2["secondary"] = {xx: an.pooled_ratio(c2, N, "DTB", xx) for xx in ("T1.0", "T1.6", "RPB")}
    tok = {(x, s): summary[f"{x}|{s}"]["gen_tokens"] for x, s in c}
    v2["per_1M_tokens"] = {xx: an.pooled_ratio(c, tok, "DTB", xx) for xx in ("T1.0", "T1.6", "RPB")}
    rar = {(x, s): rare[f"{x}|{s}"]["exact_mean"] for x, s in c}
    ones = {k: 1 for k in c}
    v2["rarefied"] = {xx: an.pooled_ratio(rar, ones, "DTB", xx) for xx in ("T1.0", "T1.6", "RPB")}
    pc = {(x, s): pooled["per_arm_seed"].get(f"{x}|{s}", {}).get("distinct_pooled_clusters", 0) for x, s in c}
    v2["pooled_linkage"] = {xx: an.pooled_ratio(pc, N, "DTB", xx) for xx in ("T1.0", "T1.6", "RPB")}
    sign_rev = []
    for nm in ("secondary", "per_1M_tokens", "rarefied", "pooled_linkage"):
        for xx in ("T1.0", "T1.6", "RPB"):
            if (v2["R"][xx] > 1) != (v2[nm][xx] > 1):
                sign_rev.append(f"{nm}:{xx}")
    v2["sign_reversals_in_sensitivities"] = sign_rev
    v2["single_run"] = any(N.get(("DTB", s), 0) < 1000 for s in (0, 1))
    v2["ratios_per_seed_boot"] = ratios
    write_json(RESULTS / "verdict_v1.json", v1)
    write_json(RESULTS / "verdict_v2.json", v2)
    # ---------------- search summary, timing
    ss = {"utc": utc_now(), "per_arm_seed": summary, "dtb_rpb_diagnostics": diag, "idea_rename_rate": rename,
          "matched_rounds": mr, "rows_total": len(rows_all), "rows_analysed": len(rows),
          "calls_by_arm_seed_total": dict(Counter(f"{r['arm']}|{r['seed']}" for r in rows_all))}
    write_json(RESULTS / "search_summary.json", ss)
    led = read_jsonl(LOGS / "time_ledger.jsonl")
    write_json(RESULTS / "timing.json", {"ledger": led, "rounds": read_jsonl(DATA / "rounds.jsonl")})
    logger.info(f"V1: {v1['verdict']} failing={v1['failing']}; V2: {v2['verdict']} {v2['branches']} R={v2['R']}")


if __name__ == "__main__":
    main()
