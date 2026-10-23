#!/usr/bin/env python3
"""Stage 9 outputs: T5 placement tests, per-program predictions (leave-one-program-out nearest cell on the factorial
frame for the model states AND for the TF-IDF / AST-n-gram baselines; survivor / covert / PROBE placements on F0, F1,
S_disc), results/verdicts.json, and method_out.json (exp_gen_sol_out). Usage: python src/make_outputs.py"""

from __future__ import annotations

import json
import multiprocessing as mp
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402

import analysis_g2 as A  # noqa: E402
import geometry  # noqa: E402
import run_analysis as RA  # noqa: E402
from common import read_json, read_jsonl, sha256_file, utc_now  # noqa: E402
from tpg2 import (BANNED_DISC, CELL_INSTR, DATA, E46_STATES, IN46, K_PRIMARY, RESULTS, ROOT, cell_dc,  # noqa: E402
                  verify_chain, write_json)

B5 = ["bfs", "dfs", "iddfs", "astar", "gbfs"]


def _loo_one(args: tuple) -> tuple[int, str]:
    i, X, lab, k = args
    keep = np.ones(len(X), bool)
    keep[i] = False
    geo, _ = geometry.geodesics(X[keep], k)
    dv = A.oos(X[i], X[keep], geo, k)
    l2 = lab[keep]
    means = {c: float(dv[l2 == c].mean()) for c in sorted(set(l2.tolist()))}
    return i, min(means, key=means.get)


def loo(X: np.ndarray, lab: np.ndarray, k: int = K_PRIMARY) -> list[str]:
    with ProcessPoolExecutor(max_workers=6, mp_context=mp.get_context("spawn")) as ex:
        res = dict(ex.map(_loo_one, [(i, X, lab, k) for i in range(len(X))], chunksize=8))
    return [res[i] for i in range(len(X))]


def t5_checks(tag: str, D: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    Fs = RA.build_frames(D)
    F0 = Fs["F0"]
    geo, _ = geometry.geodesics(F0["X"], K_PRIMARY)
    i = 3
    dv = A.oos(F0["X"][i], F0["X"], geo, K_PRIMARY)
    out["exact_copy_insertion_max_abs_diff"] = float(np.abs(dv - geo[i]).max())
    # iteration 9's UD result on F0-without-top-ups (E46 PRIMARY frame, classes >= 10, cached states)
    ms = read_json(IN46 / "data" / "mcode_sets.json")
    ze = np.load(E46_STATES / f"mcode_{tag}.npz")
    keys = {str(k): j for j, k in enumerate(ze["keys"])}
    bi = [int(b) for b in ze["blocks"]].index(D["L"])
    rows = []
    for a, progs in ms["sets"]["PRIMARY"].items():
        if len(progs) >= 10:
            rows += [(p["scrubbed_sha256"], a) for p in progs]
    X = np.stack([ze["R"][keys[k], 0, bi].astype(np.float64) for k, _ in rows])
    lab = np.array([a for _, a in rows])
    g9, _ = geometry.geodesics(X, K_PRIMARY)
    B = [b for b in B5 if b in set(lab.tolist())]
    NB = [a for a in ["bibfs", "biastar", "idastar", "jps", "dijkstra_unit"] if a in set(lab.tolist())]
    g, _ = geometry.g_values(g9, lab, B, NB)
    cls, med = geometry.classify(g)
    ud = [p for p in ms["placement"] if p["set"] == "SURV" and p["algorithm"] == "dijkstra_unit"]
    n_edge = 0
    for p in ud:
        dv = A.oos(ze["R"][keys[p["scrubbed_sha256"]], 0, bi].astype(np.float64), X, g9, K_PRIMARY)
        gx = min(float(dv[lab == b].mean()) for b in B)
        n_edge += int(gx < med - 1e-12)
    ref = read_json(IN46 / "results" / "placement.json")[f"{tag}|mcode_PRIMARY_R1"]["udij_survivors"]
    out["iter9_UD_reproduction"] = {"n": len(ud), "n_edge": n_edge, "iter9_n_edge": ref["n_edge"],
                                    "exact": n_edge == ref["n_edge"] and len(ud) == ref["n"]}
    return out


def main() -> None:
    fr = read_json(DATA / "frames.json")
    items = {it["id"]: it for it in read_json(DATA / "state_items.json")["items"]}
    fact_rows = {r["uid"]: r for r in read_jsonl(DATA / "factorial.jsonl")}
    cells = [c["cell"] for c in fr["g1_cells"]]
    fact = [f for f in fr["factorial"] if f["cell"] in cells]
    probe = [f for f in fr["factorial"] if f["cell"] == "PROBE"]
    ids = [f["id"] for f in fact]
    lab = np.array([f["cell"] for f in fact])
    codes = [items[u]["scrubbed"] for u in ids]
    preds: dict[str, dict[str, str]] = {u: {} for u in ids}
    loo_acc: dict[str, Any] = {}
    t5: dict[str, Any] = {}
    place: dict[str, dict[str, dict[str, str]]] = {}
    for tag in ("8b", "32b"):
        D = RA.load_all(tag)
        X = RA.X_new(D, ids)
        nc = loo(X, lab)
        for u, c in zip(ids, nc):
            preds[u][f"predict_nearest_cell_{tag}"] = c
        acc = float(np.mean([a == b for a, b in zip(nc, lab)]))
        accd = float(np.mean([cell_dc(a)[0] == cell_dc(b)[0] for a, b in zip(nc, lab)]))
        accc = float(np.mean([cell_dc(a)[1] == cell_dc(b)[1] for a, b in zip(nc, lab)]))
        loo_acc[tag] = {"cell": acc, "discipline": accd, "container": accc, "chance_cell": 1 / len(cells),
                        "weakly_clustered_flag": acc < 0.5}
        t5[tag] = t5_checks(tag, D)
        # placements per program
        Fs = RA.build_frames(D)
        F0, F1 = Fs["F0"], Fs["F1"]
        g2 = read_json(RESULTS / f"g2_{tag}.json")["k15"]
        geo0, _ = geometry.geodesics(F0["X"], K_PRIMARY)
        geo1, _ = geometry.geodesics(F1["X"], K_PRIMARY)
        med0 = g2["frames_algorithm_level"]["F0"]["median"]
        med1 = g2["frames_algorithm_level"]["F1"]["median"]
        B0 = g2["frames_algorithm_level"]["F0"]["banned"]
        B1 = g2["frames_algorithm_level"]["F1"]["banned"]
        sdisc_cache: dict[str, Any] = {}
        placed = [("survivor", s) for s in fr["survivors"]] + [("covert", c) for c in fr["covert"]] + \
                 [("probe", p) for p in probe]
        for kind, s in placed:
            x = RA.X_new(D, [s["id"]])[0]
            dv0 = A.oos(x, F0["X"], geo0, K_PRIMARY)
            m0 = {a: float(dv0[F0["alg"] == a].mean()) for a in sorted(set(F0["alg"].tolist()))}
            g0 = min(m0[b] for b in B0)
            dv1 = A.oos(x, F1["X"], geo1, K_PRIMARY)
            m1a = {a: float(dv1[F1["alg"] == a].mean()) for a in sorted(set(F1["alg"].tolist()))}
            g1v = min(m1a[b] for b in B1)
            m1c = {c: float(dv1[F1["cell"] == c].mean()) for c in cells}
            p = {f"predict_class_F0_{tag}": A.class_of(g0, med0), f"predict_class_F1_{tag}": A.class_of(g1v, med1),
                 f"predict_nearest_algorithm_F0_{tag}": min(m0, key=m0.get),
                 f"predict_nearest_cell_{tag}": min(m1c, key=m1c.get)}
            if kind == "survivor":
                fam = g2["families"].get(s["family_split"], {})
                c_f = s["cont"]
                if c_f not in sdisc_cache:
                    F = RA.subframe(F1, F1["cont"] != c_f)
                    gs, _ = geometry.geodesics(F["X"], K_PRIMARY)
                    sdisc_cache[c_f] = (F, gs)
                F, gs = sdisc_cache[c_f]
                dvs = A.oos(x, F["X"], gs, K_PRIMARY)
                own = f"{s['disc']}_{c_f}"
                per = {}
                for d in BANNED_DISC:
                    mk = (F["disc"] == d) & (F["cell"] != own)
                    if mk.any():
                        per[d] = float(dvs[mk].mean())
                med_s = fam.get("S_disc", {}).get("median_ref")
                if per and med_s is not None:
                    p[f"predict_class_Sdisc_{tag}"] = A.class_of(min(per.values()), med_s)
                    p[f"predict_nearest_banned_discipline_Sdisc_{tag}"] = min(per, key=per.get)
            place.setdefault(s["id"], {}).update(p)
    # baselines: LOO nearest cell on TF-IDF and AST n-gram features
    reps = RA.baseline_reps(codes)
    for nm, R in reps.items():
        nc = loo(R, lab)
        for u, c in zip(ids, nc):
            preds[u][f"predict_nearest_cell_baseline_{nm}"] = c
        loo_acc[f"baseline_{nm}"] = {"cell": float(np.mean([a == b for a, b in zip(nc, lab)])),
                                     "discipline": float(np.mean([cell_dc(a)[0] == cell_dc(b)[0] for a, b in zip(nc, lab)])),
                                     "container": float(np.mean([cell_dc(a)[1] == cell_dc(b)[1] for a, b in zip(nc, lab)]))}
    write_json(RESULTS / "t5_placement.json", {"loo_nearest_cell_accuracy": loo_acc, "checks": t5, "utc": utc_now()})
    # ------------------------------------------------------------------ verdicts
    g1 = {t: read_json(RESULTS / f"g1_{t}.json") for t in ("8b", "32b")}
    ps = {t: g1[t]["perm"]["model"]["rho_d"]["p_greater"] for t in g1}
    ph = A.holm(ps)
    ver: dict[str, Any] = {"g1": {}, "g2": {}}
    for t in g1:
        r = g1[t]
        rd = r["point_model"]["rho_d"]
        pb = r["bootstrap"]["model_rho_d_minus_rho_c"]["P_rho_d_gt_rho_c"]
        v = A.verdict_g1(rd, ph[t], pb)
        vf = A.verdict_g1(r["point_model"]["rho_d_full"], 0.0 if r["perm"]["model"]["rho_d_full"]["p_greater"] < 0.05 else 1.0, pb)
        vcv = A.verdict_g1(r["sensitivities"]["crossval_euclid_centroid"]["rho_d"],
                           r["sensitivities"]["crossval_euclid_centroid"]["p_rho_d"], pb)
        ver["g1"][t] = {"rho_d": rd, "rho_c": r["point_model"]["rho_c"], "p_within_container": ps[t], "p_holm": ph[t],
                        "P_boot_rho_d_gt_rho_c": pb, "verdict": v, "verdict_full_control": vf,
                        "verdict_crossvalidated": vcv, "fragile": len({v, vf, vcv}) > 1,
                        "rho_d_full": r["point_model"]["rho_d_full"], "noise_ceiling_SB": r["noise_ceiling"]["spearman_brown"],
                        "selectivity_vs_baselines": {k: x["point"] for k, x in r["selectivity"].items()}}
    low_both = all(ver["g1"][t]["rho_d"] <= A.THRESH_DISCONF for t in g1)
    sup_any = any(ver["g1"][t]["verdict"] == "SUPPORTED" for t in g1)
    ver["g1"]["claim_G1"] = "SUPPORTED" if sup_any else ("DISCONFIRMED" if low_both else "NOT SUPPORTED (INTERMEDIATE)")
    ver["g1"]["note"] = ("rho_d is 0.104 on 8B and 0.090 on 32B: the DISCONFIRMED rule (<= 0.1 on BOTH models) misses by "
                         "0.004 on 8B; with surface, length and dispersion controls rho_d_full is <= 0.05 on both")
    for t in ("8b", "32b"):
        g2 = read_json(RESULTS / f"g2_{t}.json")
        ver["g2"][t] = {k: g2[k]["verdict"] for k in g2}
    ver["g2"]["claim_G2_8b_primary"] = ver["g2"]["8b"]["k15"]["verdict"]
    chain = verify_chain()
    ver["commitment_chain_ok"] = chain["ok"]
    ver["commitment_chain_problems"] = chain["problems"]
    write_json(RESULTS / "verdicts.json", ver)
    # ------------------------------------------------------------------ method_out.json
    hand = {}
    for h in read_jsonl(DATA / "hand_reads.jsonl"):
        hand[h["uid"]] = h
    ex_fact = []
    for f in fact + probe:
        r = fact_rows[f["id"]]
        instr = CELL_INSTR[f["requested_cell"]]
        e = {"input": f"CELL {f['requested_cell']} instruction: {instr}\n\nSCRUBBED PROGRAM:\n{items[f['id']]['scrubbed']}",
             "output": f"{f['disc']}|{f['cont']}",
             "metadata_uid": f["id"], "metadata_cell": f["cell"], "metadata_requested_cell": f["requested_cell"],
             "metadata_reassigned": bool(f["reassigned"]), "metadata_disputed": bool(f.get("disputed")),
             "metadata_round": r["round"], "metadata_template": r["template"], "metadata_seed": r.get("seed"),
             "metadata_call_index": r.get("call_index"), "metadata_model": "qwen/qwen3-32b",
             "metadata_provider": r.get("provider"), "metadata_engine": r.get("engine"),
             "metadata_code_sha256": r.get("code_sha256"), "metadata_scrubbed_sha256": r.get("scrubbed_sha256"),
             "metadata_suites": {"passed_48": r.get("passed_48"), "passed_41": r.get("passed_41"),
                                 "scrubbed_passed_48": r.get("scrubbed_passed_48"), "scrubbed_passed_41": r.get("scrubbed_passed_41")},
             "metadata_instrument": r.get("instrument"), "metadata_instrument_disc_cont": r.get("instrument_disc_cont") or [r.get("disc"), r.get("cont")],
             "metadata_hand_read": (hand.get(f["id"]) or {}).get("rationale"),
             "metadata_context_variant": items[f["id"]]["context_variant"],
             "metadata_in_g1": f["cell"] in cells}
        e.update(preds.get(f["id"], {}))
        if f["cell"] == "PROBE":
            e.update(place.get(f["id"], {}))
        e = {k: (v if k in ("input", "output") or not k.startswith("predict_") else str(v)) for k, v in e.items()}
        ex_fact.append(e)
    ex_top = []
    for t in fr["topups"]:
        h = hand.get(t["id"], {})
        ex_top.append({"input": f"TOP-UP ({t['source']}), named forced program, scrubbed:\n{items[t['id']]['scrubbed']}",
                       "output": t["algorithm"], "metadata_uid": t["id"], "metadata_measured_disc_cont": [t["disc"], t["cont"]],
                       "metadata_hand_read": h.get("rationale"), "metadata_in_f0": t["algorithm"] in fr["f0_classes"],
                       "metadata_context_variant": items[t["id"]]["context_variant"]})
    ex_place = []
    for kind, s in [("survivor", s) for s in fr["survivors"]] + [("covert", c) for c in fr["covert"]]:
        e = {"input": f"{kind.upper()} program ({s.get('source', 'E45 covert')}), scrubbed:\n{items[s['id']]['scrubbed']}",
             "output": (s["family_split"] if kind == "survivor" else f"covert {s['label_v9']}") + f" | measured {s['disc']}|{s['cont']}",
             "metadata_uid": s["id"], "metadata_kind": kind, "metadata_context_variant": items[s["id"]]["context_variant"]}
        if kind == "survivor":
            e["metadata_family"] = s["family"]
            e["metadata_instrument"] = s.get("instrument")
        e.update({k: str(v) for k, v in place.get(s["id"], {}).items()})
        ex_place.append(e)
    ex_g1 = []
    for t in ("8b", "32b"):
        r = g1[t]
        for rep in ("model", "block0", "tfidf", "astngram"):
            p = r["point_" + rep]
            b = r["bootstrap"][rep]
            ex_g1.append({"input": f"G1 {t} representation={rep} (k=15, cell RDM = mean kNN geodesic, {len(cells)} cells)",
                          "output": f"rho_d={p['rho_d']:.4f}",
                          "predict_rho_c": f"{p['rho_c']:.4f}", "predict_rho_d_full": f"{p['rho_d_full']:.4f}",
                          "predict_rho_d_ci95": str([round(x, 4) for x in b["rho_d"]["ci95"]]),
                          "predict_p_within_container": f"{r['perm'][rep]['rho_d']['p_greater']:.5f}",
                          "metadata_model": t, "metadata_representation": rep, "metadata_variant": "primary"})
        for nm, s in r["sensitivities"].items():
            ex_g1.append({"input": f"G1 {t} sensitivity={nm}", "output": f"rho_d={s['rho_d']:.4f}",
                          "predict_rho_c": f"{s['rho_c']:.4f}", "predict_p_within_container": f"{s.get('p_rho_d', float('nan')):.5f}",
                          "metadata_model": t, "metadata_variant": nm})
    costs = read_json(RESULTS / "costs.json")
    timing = read_jsonl(RESULTS / "timing.jsonl")
    meta = {"method_name": "TP-G2: factorial discipline x container decoupling of the Qwen3 program map",
            "description": "Verified, name-scrubbed grid path-search programs crossing measured expansion discipline with "
                           "frontier container; frozen iteration-9 M-code readout (R1, Qwen3-8B bf16 block 17, Qwen3-32B "
                           "NF4 block 33, k = 15 / 10); G1 restricted-permutation partial-Spearman RSA with lexical "
                           "baselines; G2 out-of-sample placement of survivor families, covert BFS/DFS and PROBE programs.",
            "verdicts": ver, "loo_nearest_cell_accuracy": loo_acc, "t5": t5,
            "design": read_json(RESULTS / "design.json"), "t4_synthetic": read_json(RESULTS / "t4_synthetic.json"),
            "deviations": read_json(RESULTS / "deviations.json"), "commitments": chain["entries"],
            "costs_usd": costs, "timing": timing, "gpu_hours_estimate": 0.25,
            "repro_gate": {t: {k: v for k, v in read_json(RESULTS / "repro_gate.json")[t].items() if k in
                               ("min_cosine", "g_dijkstra_unit_recomputed", "g_dijkstra_unit_recorded", "pass")}
                           for t in ("8b", "32b")},
            "instrument_gate": {k: v for k, v in read_json(RESULTS / "instrument_gate.json").items() if k != "rows"},
            "novelty_audit": read_json(RESULTS / "novelty_audit.json")["summary"],
            "judges": read_json(RESULTS / "judges.json") if (RESULTS / "judges.json").exists() else None,
            "rederive": {"n_mismatches": read_json(ROOT / "audit" / "rederive.json")["n_mismatches"]},
            "files_sha256": {p: sha256_file(ROOT / p) for p in ("data/frames.json", "predictions/commit1.json")},
            "utc": utc_now()}
    out = {"metadata": meta, "datasets": [{"dataset": "tpg2_factorial", "examples": ex_fact},
                                          {"dataset": "tpg2_topups", "examples": ex_top},
                                          {"dataset": "tpg2_placements", "examples": ex_place},
                                          {"dataset": "tpg2_g1", "examples": ex_g1}]}
    (ROOT / "method_out.json").write_text(json.dumps(out, indent=1, default=str))
    print({k: len(d["examples"]) for k, d in zip(["fact", "top", "place", "g1"], out["datasets"])}, loo_acc,
          {t: t5[t] for t in t5})


if __name__ == "__main__":
    main()
