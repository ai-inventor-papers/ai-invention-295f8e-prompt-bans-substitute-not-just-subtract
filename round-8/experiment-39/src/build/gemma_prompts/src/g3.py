#!/usr/bin/env python3
"""G3: the fork-margin account of temperature. Predictions (from teacher-forced logits only) are hash-committed
(COMMIT #1) before a same-seed sweep T in {0.3, 0.7, 1.0, 1.3} x {top-p 1, top-k 10}, N = 50 per cell.

pred_BFS(T) = P_cstar(T) * sum_t f_T(t) P(BFS | t) + (1 - P_cstar(T)) * pi_other, where P_cstar(T) is the product
of the c* token probabilities under softmax(z / T) (restricted to the top 10 for top-k), f_T the fork distribution
at p_f, P(BFS | t) the fork-token table (source chosen by the committed U6 rule) and pi_other the BFS share among
non-c* programs of the engine-check twin cell."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg import (B_IDS, D_IDS, DATA_DIR, I6_NATURAL, RESULTS_DIR, ROOT, SAMPLERS, TEMPLATE_IDS, TEMPS, TOPK,
                 read_json, read_jsonl, sha256_file, slot_key7, write_json)


def labels_by_row() -> dict[str, dict[str, Any]]:
    return {r["row_id"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl")}


def fork_class(tok_id: int | None) -> str:
    if tok_id is None:
        return "NA"
    if tok_id in B_IDS:
        return "B"
    if tok_id in D_IDS:
        return "D"
    return "O"


def exact_mcnemar(b: int, c: int, alternative: str = "two-sided") -> float:
    """b = pairs (x=1, y=0), c = pairs (x=0, y=1). one-sided 'greater': P(X >= b | n = b + c, p = 0.5)."""
    from scipy.stats import binomtest

    n = b + c
    if n == 0:
        return 1.0
    if alternative == "greater":
        return float(binomtest(b, n, 0.5, alternative="greater").pvalue)
    return float(binomtest(b, n, 0.5, alternative="two-sided").pvalue)


def u6_diagnosis() -> dict[str, Any]:
    import fork as F
    from scipy.stats import fisher_exact

    import prompts as PG

    raw = {r["row_id"]: r for r in read_jsonl(DATA_DIR / "raw_u6.jsonl")}
    lab = labels_by_row()
    tok = PG.tokenizer()
    out: dict[str, Any] = {}
    sets = {}
    for arm in ("u6a", "u6b"):
        rows = [raw[k] for k in sorted(raw) if k.startswith(arm + "|")]
        recs = []
        for r in rows:
            L = lab.get(r["row_id"])
            if L is None:
                continue
            resp = r["token_ids"]
            part_full = F.partial_label(r["text"]) or "other"
            part_320 = F.partial_label(tok.decode(resp[:320], skip_special_tokens=True)) or "other"
            recs.append({"row_id": r["row_id"], "slot": (r["template"], r["slot"]), "full": L["label"],
                         "passed": bool(L["passed"]), "partial_320": part_320, "partial_full": part_full})
        sets[arm] = recs
        n = len(recs)
        k_full = sum(x["full"] == "bfs" for x in recs)
        k_part = sum(x["partial_320"] == "bfs" for x in recs)
        n_bd = sum(x["partial_320"] in ("bfs", "dfs") for x in recs)
        out[arm] = {"n": n, "bfs_full": k_full, "share_full": k_full / max(n, 1), "bfs_partial_320": k_part,
                    "share_partial_320_of_all": k_part / max(n, 1),
                    "share_partial_320_of_bfs_dfs": k_part / max(n_bd, 1),
                    "label_counts_full": dict(Counter(x["full"] for x in recs)),
                    "label_counts_partial_320": dict(Counter(x["partial_320"] for x in recs)),
                    "vs_natural_fisher_p": float(fisher_exact([[k_full, n - k_full],
                                                               [I6_NATURAL["k"], I6_NATURAL["n"] - I6_NATURAL["k"]]]).pvalue)}
    a = {x["slot"]: x for x in sets["u6a"]}
    b = {x["slot"]: x for x in sets["u6b"]}
    common = sorted(set(a) & set(b))
    b_only = sum(a[s]["full"] == "bfs" and b[s]["full"] != "bfs" for s in common)
    c_only = sum(a[s]["full"] != "bfs" and b[s]["full"] == "bfs" for s in common)
    same_prog = sum(a[s]["full"] == b[s]["full"] for s in common)
    out["a_vs_b"] = {"n_pairs": len(common), "a_bfs_b_not": b_only, "b_bfs_a_not": c_only,
                     "label_agreement": same_prog / max(len(common), 1),
                     "mcnemar_p_two_sided": exact_mcnemar(b_only, c_only)}
    agree = sum(x["partial_320"] == (x["full"] if x["full"] in ("bfs", "dfs") else "other") for x in sets["u6a"])
    out["a_partial_vs_a_full"] = {"agreement": agree / max(len(sets["u6a"]), 1),
                                  "confusion": dict(Counter(f"{x['partial_320']}->{x['full']}" for x in sets["u6a"]))}
    na, nb = out["u6a"], out["u6b"]
    out["U6_pass_a"] = bool(na["vs_natural_fisher_p"] >= 0.05)
    out["U6_pass_b"] = bool(nb["vs_natural_fisher_p"] >= 0.05)
    reasons = []
    if out["a_vs_b"]["mcnemar_p_two_sided"] < 0.05:
        reasons.append("batching ((a) differs from (b))")
    if out["a_partial_vs_a_full"]["agreement"] < 0.95:
        reasons.append("partial labeller (a-partial vs a-full)")
    out["diagnosis"] = reasons or ["neither (sampling noise)"]
    out["resampling_path_differs_p_lt_0.05"] = bool(out["a_vs_b"]["mcnemar_p_two_sided"] < 0.05)
    return out


def g3cal_table() -> dict[str, Any]:
    raw = {r["row_id"]: r for r in read_jsonl(DATA_DIR / "raw_g3cal.jsonl")}
    lab = labels_by_row()
    tab: dict[int, dict[str, Any]] = {}
    pooled = []
    for rid, r in raw.items():
        L = lab.get(rid)
        if L is None:
            continue
        t = int(r["forced_fork_token"])
        tab.setdefault(t, {"n": 0, "n_bfs": 0, "n_dfs": 0, "n_other": 0, "n_invalid": 0, "n_pass": 0})
        d = tab[t]
        d["n"] += 1
        lb = L["label"]
        d["n_bfs"] += lb == "bfs"
        d["n_dfs"] += lb == "dfs"
        d["n_invalid"] += lb in ("invalid", "disputed")
        d["n_other"] += lb not in ("bfs", "dfs", "invalid", "disputed")
        d["n_pass"] += bool(L["passed"])
        pooled.append(lb == "bfs")
    for t, d in tab.items():
        d["p_bfs_of_all"] = d["n_bfs"] / max(d["n"], 1)
        d["p_bfs_of_bfs_dfs"] = d["n_bfs"] / max(d["n_bfs"] + d["n_dfs"], 1)
    return {"by_token": {str(k): v for k, v in tab.items()}, "pooled_bfs_share": float(np.mean(pooled)) if pooled else None}


def stage_g3a(args: Any) -> None:
    import commit as CM
    import fork7 as FK
    from gen7 import Runner

    import time as _t

    need = set()
    for f in ("raw_u6.jsonl", "raw_g3cal.jsonl", "raw_engine.jsonl"):
        need |= {r["row_id"] for r in read_jsonl(DATA_DIR / f)}
    t0 = _t.time()
    while need - set(labels_by_row()) and _t.time() - t0 < 900:
        logger.info(f"g3a: waiting for {len(need - set(labels_by_row()))} labels")
        _t.sleep(20)
    diag = u6_diagnosis()
    cal = g3cal_table()
    write_json(RESULTS_DIR / "u6.json", diag)
    write_json(RESULTS_DIR / "g3_cal.json", cal)
    tt6 = FK.token_table()
    src_primary = "G3cal" if diag["resampling_path_differs_p_lt_0.05"] else "iter6_token_table"
    p6 = {t: tt6[t]["p_bfs"] for t in list(B_IDS) + list(D_IDS) if t in tt6}
    pcal = {}
    for t in list(B_IDS) + list(D_IDS):
        d = cal["by_token"].get(str(t))
        if d and d["n"] > 0:
            pcal[t] = d["p_bfs_of_all"]
    pcal.setdefault(236809, p6.get(236809, 1.0))        # 'q' was not calibrated (rare); fall back to iteration 6
    p_other = cal["pooled_bfs_share"]
    # engine-check cell: BFS share among non-c* programs (pi_other)
    lab = labels_by_row()
    eng = [r for r in read_jsonl(DATA_DIR / "raw_engine.jsonl")]
    cs = FK.cstar()
    nonc = [lab[r["row_id"]]["label"] == "bfs" for r in eng if r["token_ids"][:32] != cs and r["row_id"] in lab]
    allb = [lab[r["row_id"]]["label"] == "bfs" for r in eng if r["row_id"] in lab]
    pi_other = float(np.mean(nonc)) if len(nonc) >= 5 else float(np.mean(allb))
    run = Runner()
    preds: dict[str, Any] = {"per_template": {}, "cells": {}}
    for w in TEMPLATE_IDS:
        p = FK.twin(w)
        ids = p["ids"] + cs
        P = p["P"]
        pos = list(range(P - 1, P + 32))                  # z_i predicting c*[i] (i = 0..31), then z_f at p_f
        with torch.no_grad():
            lg = run.logits_rows(ids, 1, positions=pos)[0].double().cpu()   # [33, V]
        per = {}
        for T in TEMPS:
            for smp in SAMPLERS:
                z = lg / T
                if smp == "topk10":
                    thr = torch.topk(z, TOPK, dim=-1).values[:, -1:]
                    z = torch.where(z < thr, torch.full_like(z, -math.inf), z)
                q = torch.softmax(z, -1)
                pc = float(np.prod([float(q[i, cs[i]]) for i in range(32)]))
                f = q[32]
                fB = {t: float(f[t]) for t in B_IDS}
                fD = {t: float(f[t]) for t in D_IDS}
                fO = float(1 - sum(fB.values()) - sum(fD.values()))
                out = {}
                for name, table in (("iter6_token_table", p6), ("G3cal", pcal)):
                    g = sum(fB[t] * table.get(t, 1.0) for t in B_IDS) + sum(fD[t] * table.get(t, 0.0) for t in D_IDS)
                    g += fO * (p_other if p_other is not None else pi_other)
                    out[name] = {"pred_bfs_given_cstar": g, "pred_bfs": pc * g + (1 - pc) * pi_other}
                top10 = set(torch.topk(lg[32], TOPK).indices.tolist())
                per[f"T{T}|{smp}"] = {"P_cstar": pc, "f_B": fB, "f_D": fD, "f_O": fO, "pred": out,
                                      "BD_outside_top10": [t for t in list(B_IDS) + list(D_IDS) if t not in top10]}
        preds["per_template"][w] = per
    for T in TEMPS:
        for smp in SAMPLERS:
            key = f"T{T}|{smp}"
            rows = [preds["per_template"][w][key] for w in TEMPLATE_IDS]
            cell = {"P_cstar": float(np.mean([r["P_cstar"] for r in rows])),
                    "f_O": float(np.mean([r["f_O"] for r in rows]))}
            for name in ("iter6_token_table", "G3cal"):
                cell[f"pred_bfs|{name}"] = float(np.mean([r["pred"][name]["pred_bfs"] for r in rows]))
                cell[f"pred_bfs_given_cstar|{name}"] = float(np.mean([r["pred"][name]["pred_bfs_given_cstar"]
                                                                    for r in rows]))
            cell["pred_bfs_primary"] = cell[f"pred_bfs|{src_primary}"]
            cell["pred_bfs_given_cstar_primary"] = cell[f"pred_bfs_given_cstar|{src_primary}"]
            preds["cells"][key] = cell
    c = preds["cells"]
    outside = sorted({t for w in TEMPLATE_IDS for k, v in preds["per_template"][w].items() for t in v["BD_outside_top10"]})
    directions = {"drop_T1.0_to_T0.3": c["T1.0|topp1"]["pred_bfs_primary"] - c["T0.3|topp1"]["pred_bfs_primary"],
                  "change_T1.0_to_T1.3": c["T1.3|topp1"]["pred_bfs_primary"] - c["T1.0|topp1"]["pred_bfs_primary"],
                  "BD_tokens_outside_top10_at_fork": outside,
                  "topk10_predicted_not_to_change_share": len(outside) == 0}
    preds.update({"source_primary": src_primary, "source_rule": "iteration-6 table unless U6 shows (a) != (b) at "
                  "p < 0.05 (then G3-cal)", "u6_a_vs_b_p": diag["a_vs_b"]["mcnemar_p_two_sided"],
                  "p_bfs_tables": {"iter6_token_table": {str(k): v for k, v in p6.items()},
                                   "G3cal": {str(k): v for k, v in pcal.items()}},
                  "p_other_tokens": p_other, "pi_other_non_cstar": pi_other, "n_non_cstar_engine": len(nonc),
                  "predicted_directions": directions})
    write_json(RESULTS_DIR / "g3_predictions.json", preds)
    c1 = CM.commit("commit1", {"g3_predictions": preds, "code_sha256": {"g3.py": sha256_file(ROOT / "src" / "g3.py")},
                               "u6_diagnosis": {k: diag[k] for k in ("a_vs_b", "diagnosis", "U6_pass_a", "U6_pass_b")}})
    logger.info(f"commit1 {c1['sha256'][:12]}; source {src_primary}; cells " +
                ", ".join(f"{k}: {v['pred_bfs_primary']:.3f}" for k, v in c.items()))
    run.free()


def stage_g3b(args: Any) -> None:
    import fork7 as FK
    from gen7 import Runner

    assert (ROOT / "predictions" / "commit1.json").exists(), "COMMIT #1 must precede any temperature sample"
    run = Runner()
    raw = DATA_DIR / "raw_g3.jsonl"
    done = {r["row_id"] for r in read_jsonl(raw)}
    order = [(T, "topp1") for T in (1.0, 0.3, 0.7, 1.3)] + [(T, "topk10") for T in (1.0, 0.3, 1.3, 0.7)]
    # one prompt per batch (fixed shape B), cells of the same template share batches: every row carries its own
    # temperature, top-k and CRN stream, so a row's computation does not depend on its batch-mates
    for w in TEMPLATE_IDS:
        p = FK.twin(w)
        rows = [{"row_id": f"g3|T{T}|{smp}|{w}|{k}", "ukey": slot_key7("G3", w, k), "temperature": T,
                 "top_k": TOPK if smp == "topk10" else 0,
                 "meta": {"part": "G3", "cell": f"T{T}|{smp}", "T": T, "sampler": smp, "template": w, "slot": k}}
                for T, smp in order for k in range(10)]
        rows = [r for r in rows if r["row_id"] not in done]
        if rows:
            run.run_cell(p["ids"], [], rows, raw, f"G3:{w}")
    run.free()


def g3_analysis() -> dict[str, Any]:
    import fork7 as FK
    from cfg import wilson_ci

    preds = read_json(RESULTS_DIR / "g3_predictions.json")
    lab = labels_by_row()
    cs = FK.cstar()
    rows = [r for r in read_jsonl(DATA_DIR / "raw_g3.jsonl") if r["row_id"] in lab]
    cells: dict[str, Any] = {}
    by_cell: dict[str, dict[tuple, dict]] = {}
    for r in rows:
        L = lab[r["row_id"]]
        oc = r["token_ids"][:32] == cs
        fc = fork_class(r["token_ids"][32] if oc and len(r["token_ids"]) > 32 else None) if oc else "NC"
        by_cell.setdefault(r["cell"], {})[(r["template"], r["slot"])] = {
            "label": L["label"], "passed": bool(L["passed"]), "cstar": oc, "fork_class": fc}
    H_all = []
    for cell, d in by_cell.items():
        n = len(d)
        k = sum(x["label"] == "bfs" for x in d.values())
        kc = sum(x["label"] == "bfs" and x["passed"] for x in d.values())
        pr = preds["cells"].get(cell, {})
        lo, hi = wilson_ci(k, n)
        obs = k / max(n, 1)
        ncs = [x for x in d.values() if x["cstar"]]
        obs_c = sum(x["label"] == "bfs" for x in ncs) / max(len(ncs), 1)
        cells[cell] = {"n": n, "attempted_bfs": k, "attempted_share": obs, "ci95": [lo, hi], "correct_bfs": kc,
                       "correct_share": kc / max(n, 1), "pass_rate": sum(x["passed"] for x in d.values()) / max(n, 1),
                       "observed_P_cstar": len(ncs) / max(n, 1), "predicted_P_cstar": pr.get("P_cstar"),
                       "observed_bfs_given_cstar": obs_c,
                       "pred_bfs_given_cstar_primary": pr.get("pred_bfs_given_cstar_primary"),
                       "pred_primary": pr.get("pred_bfs_primary"),
                       "pred_iter6": pr.get("pred_bfs|iter6_token_table"), "pred_g3cal": pr.get("pred_bfs|G3cal"),
                       "abs_err_primary": abs(obs - pr["pred_bfs_primary"]) if pr else None,
                       "pred_inside_ci": bool(lo <= pr["pred_bfs_primary"] <= hi) if pr else None,
                       "fork_class_counts": dict(Counter(x["fork_class"] for x in d.values())),
                       "label_counts": dict(Counter(x["label"] for x in d.values()))}
        H_all += [(x["fork_class"], x["label"]) for x in d.values()]

    def cond_entropy(pairs: list[tuple[str, str]]) -> float:
        if not pairs:
            return float("nan")
        n = len(pairs)
        h = 0.0
        for f, cnt in Counter(p[0] for p in pairs).items():
            sub = Counter(p[1] for p in pairs if p[0] == f)
            hf = -sum((c / cnt) * math.log2(c / cnt) for c in sub.values())
            h += cnt / n * hf
        return h

    rng = np.random.default_rng(0)
    boots = [cond_entropy([H_all[i] for i in rng.integers(0, len(H_all), len(H_all))]) for _ in range(1000)]
    H_by_T = {}
    for T in TEMPS:
        pp = [(x["fork_class"], x["label"]) for c, d in by_cell.items() if c.startswith(f"T{T}|") for x in d.values()]
        H_by_T[str(T)] = cond_entropy(pp)
    tp = [c for c in cells if c.endswith("topp1")]
    errs = [cells[c]["abs_err_primary"] for c in tp if cells[c]["abs_err_primary"] is not None]
    # McNemar T1.0 -> T0.3 on CRN pairs (attempted BFS), one-sided (predicted drop direction)
    mc = {}
    for smp in SAMPLERS:
        a, b = by_cell.get(f"T1.0|{smp}", {}), by_cell.get(f"T0.3|{smp}", {})
        com = sorted(set(a) & set(b))
        x = sum(a[s]["label"] == "bfs" and b[s]["label"] != "bfs" for s in com)
        y = sum(a[s]["label"] != "bfs" and b[s]["label"] == "bfs" for s in com)
        mc[smp] = {"n": len(com), "T1_bfs_T03_not": x, "T03_bfs_T1_not": y,
                   "p_one_sided_drop": exact_mcnemar(x, y, "greater"), "p_two_sided": exact_mcnemar(x, y)}
    flips = {}
    for smp in SAMPLERS:
        cs_ = [f"T{T}|{smp}" for T in TEMPS if f"T{T}|{smp}" in by_cell]
        if cs_:
            com = set.intersection(*[set(by_cell[c]) for c in cs_])
            flips[smp] = sum(len({by_cell[c][s]["label"] for c in cs_}) > 1 for s in com) / max(len(com), 1)
    Hp = cond_entropy(H_all)
    res = {"cells": cells, "H_label_given_fork_pooled_bits": Hp,
           "H_ci95": [float(np.nanpercentile(boots, 2.5)), float(np.nanpercentile(boots, 97.5))],
           "H_by_T": H_by_T, "MAE_topp1": float(np.mean(errs)) if errs else None,
           "max_abs_err_topp1": float(np.max(errs)) if errs else None,
           "G3_CONC": bool(Hp <= 0.3), "G3_LAW": bool(errs and max(errs) <= 0.10),
           "G3_DISCONFIRMED": bool(Hp > 0.5 or (errs and max(errs) > 0.2)), "mcnemar_T1_vs_T03": mc,
           "share_slots_label_changes_across_T": flips, "source_primary": preds["source_primary"]}
    write_json(RESULTS_DIR / "g3_sweep.json", res)
    return res
