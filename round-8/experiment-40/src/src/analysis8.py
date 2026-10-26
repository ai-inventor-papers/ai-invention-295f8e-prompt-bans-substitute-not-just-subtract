#!/usr/bin/env python3
"""Analysis: generation tables, verdicts per (unit, site), K2 and p_K2, mediation outcomes (clamp, prospective),
geometry figures (actual activation coordinates) and the method_out.json rows.

Usage: python src/analysis8.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from loguru import logger

import stats8 as ST
from cfg8 import (DATA, FIGS, PRED, RESULTS, THRESH, UNITS, read_json, read_jsonl, setup_logging, write_json)

OFF_T10 = ("bfs", "dfs", "label_propagation")


def load_gen(unit: str) -> dict[str, dict[str, Any]]:
    samples = {r["sample_id"]: r for r in read_jsonl(DATA / f"samples_{unit}.jsonl")}
    labels = {}
    for r in read_jsonl(DATA / f"labels_{unit}.jsonl"):
        labels.setdefault(r["sample_id"], r)
    out = {}
    for sid, s in samples.items():
        l = labels.get(sid)
        if l is None:
            continue
        row = dict(s)
        row.update({"label": l["label"], "passed": bool(l.get("passed")), "valid": bool(l.get("valid")),
                    "labeller_source": l.get("labeller_source"), "code": l.get("code")})
        out[sid] = row
    return out


def ok_label(r: dict[str, Any] | None, c: str) -> bool:
    return bool(r is not None and r["label"] == c and r["passed"])


def gen_tables(unit: str, site: str, G: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    cm = PRED / f"commit2_{unit}_{site}.json"
    if not cm.exists():
        return None
    c2 = read_json(cm)
    slot_map = c2["slot_map"]
    cells = c2["cells"]
    out: dict[str, Any] = {"unit": unit, "site": site, "classes": {}}
    pooled = {"DAS": [], "RAND": [], "BASE": [], "FULL": [], "pass_DAS": [], "pass_BASE": []}
    for c, slots in slot_map.items():
        n_by_arm = {arm: n for (s_, arm, cc, n) in cells if s_ == site and cc == c}
        tab: dict[str, Any] = {}
        rows_by_arm: dict[str, list] = {}
        for arm, n in n_by_arm.items():
            rr = []
            for s in range(n):
                sm = slots[s]
                sid = (f"{unit}|{site}|BASE|{sm['base']}|{s}" if arm == "BASE" else f"{unit}|{site}|{arm}|{c}|{s}")
                rr.append(G.get(sid))
            rows_by_arm[arm] = rr
            got = [r for r in rr if r is not None]
            tgt = c
            if arm in ("REV-DAS", "REV-FULL", "SRC"):
                tgt = got[0]["class_src"] if got and arm != "SRC" else (got[0]["class_base"] if got else c)
            k = sum(ok_label(r, c) for r in got)
            kdef = sum(ok_label(r, UNITS[unit]["default"] or "") for r in got) if UNITS[unit]["default"] else None
            labs = {}
            for r in got:
                labs[r["label"]] = labs.get(r["label"], 0) + 1
            tab[arm] = {"n_planned": n, "n": len(got), "correct_target": k, "share": k / len(got) if got else None,
                        "wilson95": ST.wilson(k, len(got)), "attempted_target": sum(r["label"] == c for r in got),
                        "pass_rate": float(np.mean([r["passed"] for r in got])) if got else None,
                        "other_share": float(np.mean([r["label"] == "other" for r in got])) if got else None,
                        "labels": labs, "correct_default": kdef,
                        "invalid": sum(r["label"] == "invalid" for r in got)}
        def paired(a: str, b: str) -> dict[str, Any] | None:
            if a not in rows_by_arm or b not in rows_by_arm:
                return None
            n = min(len(rows_by_arm[a]), len(rows_by_arm[b]))
            xa = [ok_label(rows_by_arm[a][i], c) for i in range(n) if rows_by_arm[a][i] and rows_by_arm[b][i]]
            xb = [ok_label(rows_by_arm[b][i], c) for i in range(n) if rows_by_arm[a][i] and rows_by_arm[b][i]]
            return ST.mcnemar(xa, xb)
        kb = tab.get("BASE", {}).get("correct_target", 0)
        kf = tab.get("FULL", {}).get("correct_target", 0)
        kd = tab.get("DAS", {}).get("correct_target", 0)
        rec = (kd - kb) / (kf - kb) if (kf - kb) else None
        pr = (tab["DAS"]["pass_rate"] / tab["BASE"]["pass_rate"]) if (tab.get("DAS", {}).get("pass_rate") and
                                                                     tab.get("BASE", {}).get("pass_rate")) else None
        dflt = UNITS[unit]["default"]
        rev = None
        if all(x in tab for x in ("REV-DAS", "REV-FULL", "SRC")):
            # restored programs of the twin's class (T10: the default); GRID: the base class of the twin
            def k_restore(arm: str) -> int:
                got = [r for r in rows_by_arm[arm] if r]
                tw_cls = got[0]["class_src"] if got and arm != "SRC" else None
                if tw_cls is None:
                    tw_cls = (rows_by_arm["REV-DAS"][0] or {}).get("class_src") if rows_by_arm.get("REV-DAS") else None
                return sum(ok_label(r, tw_cls or (dflt or "")) for r in got)
            ks, krd, krf = k_restore("SRC"), k_restore("REV-DAS"), k_restore("REV-FULL")
            rev = {"restored_SRC": ks, "restored_REV_DAS": krd, "restored_REV_FULL": krf,
                   "gen_c4": (krd - ks) / (krf - ks) if (krf - ks) else None}
        out["classes"][c] = {"arms": tab, "gen_recovery": rec, "pass_ratio_DAS_vs_BASE": pr,
                             "mcnemar_DAS_vs_RAND": paired("DAS", "RAND"), "mcnemar_DAS_vs_BASE": paired("DAS", "BASE"),
                             "mcnemar_FULL_vs_BASE": paired("FULL", "BASE"), "reverse": rev,
                             "extra_ranks": {arm: tab[arm] for arm in tab if arm.startswith("DAS_k")}}
        for arm in ("DAS", "RAND", "BASE", "FULL"):
            if arm in rows_by_arm:
                pooled[arm] += [ok_label(r, c) if r else None for r in rows_by_arm[arm]]
        if "DAS" in rows_by_arm:
            pooled["pass_DAS"] += [r["passed"] for r in rows_by_arm["DAS"] if r]
            pooled["pass_BASE"] += [r["passed"] for r in rows_by_arm.get("BASE", []) if r]
    # pooled over off-default classes (CRN-paired by slot within class)
    def cnt(x: list) -> int:
        return sum(1 for v in x if v)
    kd, kb, kf = cnt(pooled["DAS"]), cnt(pooled["BASE"]), cnt(pooled["FULL"])
    pairs_dr = [(a, b) for a, b in zip(pooled["DAS"], pooled["RAND"]) if a is not None and b is not None]
    out["pooled"] = {"DAS": kd, "BASE": kb, "FULL": kf, "RAND": cnt(pooled["RAND"]),
                     "n_DAS": len([v for v in pooled["DAS"] if v is not None]),
                     "gen_recovery": (kd - kb) / (kf - kb) if (kf - kb) else None,
                     "pass_ratio": (np.mean(pooled["pass_DAS"]) / np.mean(pooled["pass_BASE"]))
                     if pooled["pass_DAS"] and pooled["pass_BASE"] and np.mean(pooled["pass_BASE"]) else None,
                     "mcnemar_DAS_vs_RAND": ST.mcnemar([a for a, _ in pairs_dr], [b for _, b in pairs_dr])}
    return out


def verdict(tf: dict[str, Any] | None, gen: dict[str, Any] | None, rinit: dict[str, Any] | None) -> dict[str, Any]:
    if tf is None:
        return {"verdict": "NOT RUN"}
    main = tf["main"]
    v_tf = bool(main["recovery"] is not None and main["recovery"] >= THRESH["V0_tf"] and main["ci95"][0] is not None
                and main["ci95"][0] > THRESH["V0_tf_lo"])
    g = (gen or {}).get("pooled", {})
    v_gen = bool(g.get("gen_recovery") is not None and g["gen_recovery"] >= THRESH["V0_gen"])
    v_pass = bool(g.get("pass_ratio") is not None and g["pass_ratio"] >= THRESH["V0_pass_ratio"])
    mc = g.get("mcnemar_DAS_vs_RAND") or {}
    v_mc = bool(mc.get("p_one_sided_a_gt_b", 1) < THRESH["V0_mcnemar_p"] and mc.get("a_only", 0) > mc.get("b_only", 0))
    V0 = v_tf and v_gen and v_pass and v_mc
    c = {"c1": all(v["pass"] for v in tf["c1"].values()) if isinstance(tf["c1"], dict) else False,
         "c2": bool(tf["c2"].get("pass")),
         "c3": bool(rinit.get("pass")) if rinit else None,
         "c4": bool(tf["c4"].get("pass")),
         "c5": bool(tf["c5"].get("pass")),
         "c6": bool(tf["c6"]["twins"]["pass"]) if "twins" in tf["c6"] else False,
         "c7": bool(tf["c7"].get("pass"))}
    c1_k = tf["c1"].get(str(tf["k_star"])) or tf["c1"].get(tf["k_star"])
    failed = [k for k, v in c.items() if v is False]
    untested = [k for k, v in c.items() if v is None]
    if not V0:
        lab = "NO HANDLE"
    elif not failed and not untested:
        lab = "CERTIFIED VARIABLE"
    elif c["c1"]:
        lab = "SUFFICIENT HANDLE"
    else:
        lab = "NO HANDLE (c1 fails)"
    kinds = {"c2": "map-class capacity", "c3": "map-class capacity", "c4": "dormant/off-manifold",
             "c5": "dormant/off-manifold", "c6": "dormant/off-manifold", "c7": "unstable across seeds",
             "c1": "random subspaces suffice"}
    by_class = {}
    for cname, cv in ((gen or {}).get("classes") or {}).items():
        mcc = cv.get("mcnemar_DAS_vs_RAND") or {}
        by_class[cname] = {"gen_recovery": cv.get("gen_recovery"), "pass_ratio": cv.get("pass_ratio_DAS_vs_BASE"),
                           "mcnemar_p_das_gt_rand": mcc.get("p_one_sided_a_gt_b"),
                           "V0_class": bool(v_tf and cv.get("gen_recovery") is not None and cv["gen_recovery"] >= 0.5
                                            and (cv.get("pass_ratio_DAS_vs_BASE") or 0) >= 0.8
                                            and (mcc.get("p_one_sided_a_gt_b") or 1) < 0.05),
                           "full_minus_base_correct": ((cv["arms"].get("FULL") or {}).get("correct_target", 0) -
                                                       (cv["arms"].get("BASE") or {}).get("correct_target", 0))}
    return {"verdict": lab, "V0_by_class": by_class,
            "note_generation_recovery": "generation recovery divides by FULL - BASE correct counts; when the full-state "
                                        "exchange moves <= 2 slots the ratio is not a fraction of a ceiling",
            "V0": V0, "V0_parts": {"tf_recovery": v_tf, "gen_recovery": v_gen, "pass_ratio": v_pass,
                                                   "mcnemar_das_gt_rand": v_mc},
            "controls": c, "failed_controls": {k: kinds[k] for k in failed}, "untested_controls": untested,
            "off_manifold_flag": bool(tf.get("off_manifold_flag")), "tf_recovery": main["recovery"],
            "tf_ci95": main["ci95"], "gen_recovery": g.get("gen_recovery"), "pass_ratio": g.get("pass_ratio"),
            "mcnemar": mc, "c1_at_kstar": c1_k}


def mediation_outcomes(G: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    p = RESULTS / "mediation_T10.json"
    if not p.exists():
        return None
    med = read_json(p)
    top = med.get("top10_escaping", [])
    esc = lambda r: bool(r and r["passed"] and r["label"] in OFF_T10)  # noqa: E731
    arms = {}
    for arm in ("PUSH", "TASK", "RAND"):
        arms[arm] = {(sd, s): G.get(f"T10|med|{arm}|{sd}|{s}") for sd in top for s in range(30)}
    out: dict[str, Any] = {}
    push = arms["PUSH"]
    e_push = sum(esc(r) for r in push.values())
    out["escapes_PUSH"] = e_push
    out["n_PUSH"] = sum(r is not None for r in push.values())
    for arm in ("TASK", "RAND"):
        keys = [k for k in push if push[k] and arms[arm].get(k)]
        a = [esc(push[k]) for k in keys]
        b = [esc(arms[arm][k]) for k in keys]
        ea, eb = sum(a), sum(b)
        out[f"clamp_{arm}"] = {"n_pairs": len(keys), "escapes_push": ea, "escapes_clamp": eb,
                               "removal": 1 - eb / ea if ea else None, "mcnemar_push_vs_clamp": ST.mcnemar(a, b),
                               "pass_rate_clamp": float(np.mean([arms[arm][k]["passed"] for k in keys])) if keys else None}
    dec_keys = [(sd, s) for sd in top for s in range(10) if G.get(f"T10|med|DEC|{sd}|{s}")]
    if dec_keys:
        a = [esc(push.get(k)) for k in dec_keys]
        b = [esc(G.get(f"T10|med|DEC|{k[0]}|{k[1]}")) for k in dec_keys]
        out["clamp_DEC"] = {"n_reached": len(dec_keys), "reach_rate": med.get("dec_clamp_reach_rate"),
                            "escapes_push_reached": sum(a), "escapes_clamp": sum(b),
                            "removal": 1 - sum(b) / sum(a) if sum(a) else None, "mcnemar": ST.mcnemar(a, b)}
    else:
        out["clamp_DEC"] = {"n_reached": 0, "reach_rate": med.get("dec_clamp_reach_rate")}
    t = out.get("clamp_TASK", {})
    r = out.get("clamp_RAND", {})
    out["not_estimable"] = bool(e_push < 8)
    out["clamp_pass"] = bool(not out["not_estimable"] and (t.get("removal") or 0) >= 0.5 and
                             (r.get("removal") if r.get("removal") is not None else 1) <= 0.10)
    pro = med.get("prospective_pi", {})
    if pro:
        xs, ys = [], []
        for sd, v in pro.items():
            rows = [G.get(f"T10|pro|PUSH|{sd}|{s}") for s in range(10)]
            rows = [x for x in rows if x]
            if rows:
                xs.append(v["pi"])
                ys.append(float(np.mean([esc(x) for x in rows])))
        out["prospective"] = {"n_directions": len(xs), "spearman": ST.spearman_perm(np.array(xs), np.array(ys)),
                              "mean_escape": float(np.mean(ys)) if ys else None}
    out["retrospective"] = {k: med.get(k) for k in med if k.startswith("spearman") or k.startswith("partial")
                            or k.startswith("placebo")}
    return out


def main() -> None:
    setup_logging("analysis8")
    res: dict[str, Any] = {}
    gens = {}
    for unit in ("T10", "GRID"):
        G = load_gen(unit)
        gens[unit] = G
        for site in ("dec", "band"):
            gt = gen_tables(unit, site, G)
            if gt:
                res[f"gen_{unit}_{site}"] = gt
    tf = {("T10", "dec"): RESULTS / "dec_T10.json", ("T10", "band"): RESULTS / "band_T10.json",
          ("GRID", "dec"): RESULTS / "dec_GRID.json", ("T10", "dec_L24_posthoc"): RESULTS / "dec_T10_L24.json"}
    ri = {("T10", "dec"): RESULTS / "rinit_T10.json", ("T10", "band"): RESULTS / "rinit_T10_band.json",
          ("GRID", "dec"): RESULTS / "rinit_GRID.json", ("T10", "dec_L24_posthoc"): RESULTS / "rinit_T10_L24.json"}
    verdicts = {}
    for (unit, site), p in tf.items():
        t = read_json(p) if p.exists() else None
        r = read_json(ri[(unit, site)]) if ri[(unit, site)].exists() else None
        v = verdict(t, res.get(f"gen_{unit}_{site}"), r)
        if site.endswith("posthoc") and t is not None:
            v["verdict"] = "POST HOC, TF-only (no generation): controls " + (
                "all pass" if not v["failed_controls"] and not v["untested_controls"] else
                f"failed {sorted(v['failed_controls'])}, untested {v['untested_controls']}")
        verdicts[f"{unit}-{site}"] = v
    res["verdicts"] = verdicts
    # ---- K2 and p_K2 (intersection-union over the two decision sites)
    pk = {}
    for unit in ("T10", "GRID"):
        d = RESULTS / f"dec_{unit}.json"
        if not d.exists():
            continue
        dd = read_json(d)
        p_c2 = []
        post = RESULTS / f"post_{unit}.json"
        if post.exists():
            p_c2 = [v["test_true_gt_perm"]["p_cluster_boot"] for v in read_json(post)["perm"].values()]
        else:
            p_c2 = [v["test_true_gt_perm"]["p_cluster_boot"] for v in dd["c2"].values()
                    if isinstance(v, dict) and "test_true_gt_perm" in v]
        r = RESULTS / f"rinit_{unit}.json"
        p_c3 = read_json(r)["test_trained_gt_rinit"]["p_cluster_boot"] if r.exists() else None
        pk[unit] = {"p_c2_max": max(p_c2) if p_c2 else None, "p_c3": p_c3,
                    "max": max([x for x in [max(p_c2) if p_c2 else None, p_c3] if x is not None], default=None)}
    vt, vg = verdicts.get("T10-dec", {}), verdicts.get("GRID-dec", {})
    confirmed = vt.get("verdict") == "CERTIFIED VARIABLE" and vg.get("verdict") == "CERTIFIED VARIABLE"
    disc = any(v.get("controls", {}).get(c) is False for v in (vt, vg) for c in ("c2", "c3"))
    res["K2"] = {"confirmed": confirmed, "disconfirmed": disc,
                 "status": "CONFIRMED" if confirmed else ("DISCONFIRMED" if disc else "NOT CONFIRMED (inconclusive)"),
                 "p_by_site": pk,
                 "p_K2": max([v["max"] for v in pk.values() if v["max"] is not None], default=None),
                 "rule": "confirmed iff T10-dec and GRID-dec both CERTIFIED; disconfirmed iff a decision site fails "
                         "c2 or c3 in either family; p_K2 = max over sites of max(p_c2, p_c3)"}
    med = mediation_outcomes(gens["T10"])
    if med:
        res["mediation"] = med
    write_json(RESULTS / "analysis.json", res)
    logger.info(json.dumps({k: v.get("verdict") for k, v in verdicts.items()}))
    logger.info(f"K2: {res['K2']['status']} p_K2 {res['K2']['p_K2']}")


if __name__ == "__main__":
    main()
