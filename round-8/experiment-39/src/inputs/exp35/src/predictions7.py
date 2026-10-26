#!/usr/bin/env python3
"""Part D (CPU): turn the teacher-forced logits (cache/tf) and the token-conditional counts
(predictions/predictions_raw.json) into the committed numbers, then COMMIT #2 (before any S3/S4 sample).

D3 one-token concentration H(A | C) with a 1,000-replicate bootstrap over continuations.
D4 cell predictions for T in {0.3, 0.7, 1.0, 1.3} x {full, top-k 10}, per template and averaged; predicted on-opening
   share; predicted correct-A_min share; per-slot replay predictions for the 50 sweep slots; top-k 10 report; margins.
D5 collapsed margins (predictions/collapsed_raw.json): margin, exact predicted movement, bound check, record view.
D6 S4 teacher-forced predictions: pushed margins and shares (8 directions), exchange / MR / padding twin / forced.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import commit7 as CM  # noqa: E402
import forks as FK  # noqa: E402
import predict as PR  # noqa: E402
import replay  # noqa: E402
from cfg7 import (CACHE_DIR, DIRECTIONS, PRED_DIR, RESULTS_DIR, SAMPLERS, SWEEP_SLOTS, TEMPLATES, TEMPS, THRESH,  # noqa
                  UNITS, read_json, u_stream, utc_now, write_json)

TF_DIR = CACHE_DIR / "tf"


def norm(v: np.ndarray, fb: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    return v / v.sum() if v.sum() > 0 else np.asarray(fb, dtype=float)


def load_tf(u: str, cid: str) -> dict[str, dict[str, np.ndarray]]:
    z = np.load(TF_DIR / f"{u}_{cid}.npz")
    return {w: {"Z_open": z[f"Zo_{w}"].astype(np.float64), "z_fork": z[f"zf_{w}"].astype(np.float64)}
            for w in TEMPLATES}


def phat_tables(U: dict[str, Any], cl: dict[str, Any], q_rest: np.ndarray, u: str, cid: str,
                counts_override: dict[str, np.ndarray] | None = None) -> tuple[dict[int, np.ndarray], np.ndarray]:
    cnt = counts_override or {t: np.array(v, dtype=float) for t, v in cl["counts"].items()}
    ph = {int(t): norm(v, q_rest) for t, v in cnt.items()}
    res = norm(np.array(cl["resid_counts"], dtype=float), q_rest)
    return ph, res


def tree_adjust(u: str, cid: str, cl: dict[str, Any], ph: dict[int, np.ndarray], T: float, k: int, w: str,
                q_rest: np.ndarray) -> dict[int, np.ndarray]:
    """TREE mode: replace Phat(A | t) by sum_t2 pi_T(t2 | O + t) Phat(A | t, t2) (+ remainder at the token level)."""
    if not cl.get("tree"):
        return ph
    out = dict(ph)
    for t, tr in cl["tree"].items():
        p = TF_DIR / f"{u}_{cid}_tree_{t}.npz"
        if not p.exists():
            continue
        z = np.load(p)[f"zf_{w}"].astype(np.float64)
        d = PR.dist(z, T, k)
        mix = np.zeros_like(q_rest, dtype=float)
        mass = 0.0
        for t2 in tr["toks2"]:
            c2 = np.array(tr["counts2"][str(t2)], dtype=float)
            if c2.sum() == 0:
                continue
            mix += d[t2] * c2 / c2.sum()
            mass += d[t2]
        mix += max(0.0, 1 - mass) * ph[int(t)]
        out[int(t)] = mix
    return out


def unit_cells(u: str, U: dict[str, Any], edits_tf: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """Cell predictions (per template and averaged) for every T x sampler."""
    C = U["cats"]
    q_rest = np.array(U["q_rest"])
    out: dict[str, Any] = {}
    tfs = {cid: (edits_tf[cid] if edits_tf else load_tf(u, cid)) for cid in U["clusters"]}
    for T in TEMPS:
        for sname, k in SAMPLERS.items():
            per_w = {}
            for w in TEMPLATES:
                cls = []
                for cid, cl in U["clusters"].items():
                    ph, res = phat_tables(U, cl, q_rest, u, cid)
                    if U["mode"] == "TREE":
                        ph = tree_adjust(u, cid, cl, ph, T, k, w, q_rest)
                    tf = tfs[cid][w]
                    cls.append({"Z_open": tf["Z_open"], "O": cl["O"], "z_fork": tf["z_fork"], "phat": ph,
                                "resid": res})
                r = PR.cell_prediction(cls, q_rest, T, k)
                per_w[w] = {"P": r["P"].tolist(), "on_opening": r["on_opening"]}
            Pm = np.mean([per_w[w]["P"] for w in TEMPLATES], 0)
            out[f"T{T}_{sname}"] = {"P": Pm.tolist(), "a_min": float(Pm[C.index(U["A_min"])]),
                                    "default": float(Pm[C.index(U["D"])]),
                                    "on_opening": float(np.mean([per_w[w]["on_opening"] for w in TEMPLATES])),
                                    "per_template": per_w}
    return out


def h_conditional(U: dict[str, Any], rng: np.random.Generator | None = None) -> dict[str, Any]:
    """H(A | C) over all clusters (weighted by cluster coverage), C(t) = argmax_A Phat(A | t); the residual bin is its
    own token. With rng: one bootstrap replicate (multinomial resampling of every token's continuations)."""
    C = U["cats"]
    q_rest = np.array(U["q_rest"])
    covs = {cid: cl["cov"] for cid, cl in U["clusters"].items()}
    wsum = sum(covs.values())
    joint: dict[str, np.ndarray] = {}
    per_tok = []
    undecided_mass = 0.0
    for cid, cl in U["clusters"].items():
        wc = covs[cid] / wsum
        pis = {int(t): v for t, v in cl["pi1_avg"].items()}
        items = [(t, np.array(cl["counts"][str(t)], dtype=float), pis[t]) for t in pis]
        items.append(("resid", np.array(cl["resid_counts"], dtype=float), max(0.0, 1 - sum(pis.values()))))
        for t, cnt, m in items:
            if cnt.sum() == 0:
                continue
            if rng is not None:
                cnt = rng.multinomial(int(cnt.sum()), cnt / cnt.sum()).astype(float)
            ph = cnt / cnt.sum()
            cls = C[int(np.argmax(ph))]
            joint.setdefault(cls, np.zeros(len(C)))
            joint[cls] += wc * m * ph
            if rng is None:
                per_tok.append({"cluster": cid, "tok": t, "pi1": m, "class": cls, "phat": ph.tolist(),
                                "H_bits": FK.entropy_bits(ph), "n": int(cnt.sum())})
            dshare = ph[C.index(U["D"])]
            if 0.2 <= dshare <= 0.8:
                undecided_mass += wc * m
    tot = sum(v.sum() for v in joint.values())
    H = sum((v.sum() / tot) * FK.entropy_bits(v / v.sum()) for v in joint.values() if v.sum() > 0)
    return {"H_bits": float(H), "class_mass": {c: float(v.sum() / tot) for c, v in joint.items()},
            "per_token": per_tok, "undecided_mass": float(undecided_mass)}


def margins(U: dict[str, Any], tfs: dict[str, dict[str, dict[str, np.ndarray]]] | None = None,
            z_override: dict[str, dict[str, np.ndarray]] | None = None) -> dict[str, Any]:
    """m_c = log P_1(D-class tokens) - log P_1(non-D tokens) at the fork, per template (D-class: argmax Phat = D;
    tokens outside the expanded set count by the residual bin's class)."""
    C = U["cats"]
    out = {}
    for cid, cl in U["clusters"].items():
        ph = {int(t): np.array(v, dtype=float) for t, v in cl["counts"].items()}
        dtoks = [t for t, v in ph.items() if v.sum() and C[int(np.argmax(v))] == U["D"]]
        res = np.array(cl["resid_counts"], dtype=float)
        res_is_d = res.sum() > 0 and C[int(np.argmax(res))] == U["D"]
        ms = {}
        keys = list(z_override[cid]) if z_override and cid in z_override else list(TEMPLATES)
        for w in keys:
            z = (z_override or {}).get(cid, {}).get(w) if z_override else None
            if z is None:
                z = (tfs or {}).get(cid, {}).get(w, {}).get("z_fork") if tfs else None
            if z is None:
                z = load_tf_cached(U["_unit"], cid)[w]["z_fork"]
            p = PR.dist(z, 1.0, 0)
            exp_mass = float(sum(p[int(t)] for t in ph))
            pd = float(sum(p[t] for t in dtoks)) + (max(0.0, 1 - exp_mass) if res_is_d else 0.0)
            pd = min(max(pd, 1e-12), 1 - 1e-12)
            ms[w] = math.log(pd) - math.log(1 - pd)
        out[cid] = {"by_template": ms, "mean": float(np.mean(list(ms.values()))), "n_D_tokens": len(dtoks)}
    return out


_TFC: dict[str, Any] = {}


def load_tf_cached(u: str, cid: str) -> dict[str, dict[str, np.ndarray]]:
    k = f"{u}|{cid}"
    if k not in _TFC:
        _TFC[k] = load_tf(u, cid)
    return _TFC[k]


def replay_slots(u: str, U: dict[str, Any]) -> dict[str, Any]:
    """Per-slot replay predictions for the sweep slots: walk the openings with each slot's own uniforms
    (replay.pick); at the fork the picked token's argmax class; leaving every opening -> argmax q_rest."""
    C = U["cats"]
    q_rest = np.array(U["q_rest"])
    out = {}
    for w in TEMPLATES:
        tfs = {cid: load_tf_cached(u, cid)[w] for cid in U["clusters"]}
        for s in SWEEP_SLOTS:
            uu = u_stream("iter7T", u, w, s)
            for T in TEMPS:
                for sname, k in SAMPLERS.items():
                    cands = list(U["clusters"])
                    pred, path_tok, fork_tok = None, [], None
                    i = 0
                    while pred is None:
                        done_c = [c for c in cands if len(U["clusters"][c]["O"]) == i]
                        if done_c:
                            c = done_c[0]
                            t = replay.pick(tfs[c]["z_fork"], float(uu[i]), T, k)
                            fork_tok = t
                            cnt = U["clusters"][c]["counts"].get(str(t))
                            v = np.array(cnt if cnt is not None else U["clusters"][c]["resid_counts"], dtype=float)
                            pred = C[int(np.argmax(v))] if v.sum() else C[int(np.argmax(q_rest))]
                            break
                        live = [c for c in cands if len(U["clusters"][c]["O"]) > i]
                        if not live:
                            pred = C[int(np.argmax(q_rest))]
                            break
                        z = tfs[live[0]]["Z_open"][i]
                        t = replay.pick(z, float(uu[i]), T, k)
                        path_tok.append(t)
                        cands = [c for c in live if U["clusters"][c]["O"][i] == t]
                        if not cands:
                            pred = "rest:" + C[int(np.argmax(q_rest))]
                            break
                        i += 1
                    out[f"{w}|{s}|T{T}_{sname}"] = {"pred": pred, "n_open_tokens": len(path_tok),
                                                    "fork_token": fork_tok, "opening_tokens": path_tok}
    return out


def topk_report(U: dict[str, Any]) -> dict[str, Any]:
    C = U["cats"]
    out = {}
    for cid, cl in U["clusters"].items():
        rows = []
        for t, v in cl["counts"].items():
            v = np.array(v, dtype=float)
            if v.sum() == 0 or C[int(np.argmax(v))] != U["A_min"]:
                continue
            for w in TEMPLATES:
                rk = cl["rank_by_template"][w][t]
                rows.append({"tok": int(t), "text": cl["tok_text"][t], "template": w, "rank": rk,
                             "pi1": cl["pi1_by_template"][w][t], "outside_top10": rk > 10})
        mass_out = {w: sum(r["pi1"] for r in rows if r["template"] == w and r["outside_top10"]) for w in TEMPLATES}
        out[cid] = {"minority_tokens": rows, "minority_mass_outside_top10": mass_out}
    return out


def s4_predictions(u: str, U: dict[str, Any], S4: dict[str, Any]) -> dict[str, Any]:
    """Pushed / exchanged teacher-forced numbers through the same prediction function (T 1, full sampler)."""
    cid = S4["cluster"]
    cl = U["clusters"][cid]
    C = U["cats"]
    q_rest = np.array(U["q_rest"])
    ph, res = phat_tables(U, cl, q_rest, u, cid)
    def pred_of(tf_w: dict[str, dict[str, np.ndarray]]) -> dict[str, Any]:
        sh, on = [], []
        for w, tf in tf_w.items():
            r = PR.cell_prediction([{"Z_open": tf["Z_open"], "O": cl["O"], "z_fork": tf["z_fork"], "phat": ph,
                                     "resid": res}], q_rest, 1.0, 0)
            sh.append(float(r["P"][C.index(U["A_min"])]))
            on.append(r["on_opening"])
        Uc = {**U, "clusters": {cid: cl}}
        m = margins(Uc, z_override={cid: {w: tf["z_fork"] for w, tf in tf_w.items()}})[cid]["mean"]
        return {"s_pred": float(np.mean(sh)), "on_opening": float(np.mean(on)), "margin": m}
    base = pred_of({w: load_tf_cached(u, cid)[w] for w in TEMPLATES})
    out = {"twin": base, "push": {}, "exchange": {}}
    for d in DIRECTIONS:
        tfw = {}
        for w in TEMPLATES:
            z = np.load(TF_DIR / f"{u}_push{d}_{w}.npz")
            tfw[w] = {"Z_open": z["Zo"].astype(np.float64), "z_fork": z["zf"].astype(np.float64)}
        r = pred_of(tfw)
        r["d_margin"] = r["margin"] - base["margin"]
        r["d_s_pred"] = r["s_pred"] - base["s_pred"]
        out["push"][str(d)] = r
    for name in ("forced", "forced_pad", "exchange", "MR"):
        z = np.load(TF_DIR / f"{u}_{name}.npz")
        r = pred_of({"F": {"Z_open": z["Zo"].astype(np.float64), "z_fork": z["zf"].astype(np.float64)}})
        out["exchange"][name] = r
    pad = out["exchange"]["forced_pad"]
    for name in ("exchange", "MR", "forced"):
        out["exchange"][name]["d_margin_vs_pad"] = out["exchange"][name]["margin"] - pad["margin"]
    return out


def collapsed_view(raw: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for t, r in raw.items():
        m = r["margin_nats"]
        out[t] = {"margin_nats": m, "pass_4nats": bool(m >= THRESH["test3_margin_nats"]),
                  "pred_p_off": r["pred_p_off"], "delta_pred_13_03": r["delta_pred_13_03"],
                  "binary_closed_form_p_off": {T: PR.binary_closed_form(m, T) if math.isfinite(m) else 0.0
                                               for T in (0.3, 1.0, 1.3)},
                  "bound_check": r["bound_check"], "llr48": r["llr48"], "fork_node_index": r["fork_node_index"],
                  "fork_node_text": r["fork_node_text"], "alt_class_tokens": r["alt_class_tokens"],
                  "path": r.get("path")}
    # the record: 797/800 default up to T 1.3 (<= 1% off per cell) implies margin >= log(0.99/0.01) * 1.3 ~ 6 nats
    out["_record"] = {"record_default": "797/800", "record_flips": "0/20 same-seed",
                      "implied_margin_nats_at_T1.3_for_1pct": 1.3 * math.log(0.99 / 0.01),
                      "binary_4nats_off_default_T1.3": PR.binary_closed_form(4.0, 1.3)}
    return out


def build_commit2() -> dict[str, Any]:
    R = read_json(PRED_DIR / "predictions_raw.json")
    F = read_json(RESULTS_DIR / "forks.json")
    S4 = read_json(PRED_DIR / "s4_raw.json") if (PRED_DIR / "s4_raw.json").exists() else {}
    COL = read_json(PRED_DIR / "collapsed_raw.json") if (PRED_DIR / "collapsed_raw.json").exists() else {}
    out: dict[str, Any] = {"units": {}}
    for u, U in R.items():
        U = {**U, "_unit": u}
        rec: dict[str, Any] = {"D": U["D"], "A_min": U["A_min"], "cats": U["cats"], "mode": U["mode"],
                               "q_rest": U["q_rest"], "q_rest_n": U["q_rest_n"],
                               "twin_pass_rate_a_min": U["twin_pass_rate_a_min"]}
        hc = h_conditional(U)
        rng = np.random.default_rng(20261022)
        boots = [h_conditional(U, rng)["H_bits"] for _ in range(1000)]
        rec["test1"] = {"H_bits": hc["H_bits"], "H_boot_ci95": [float(np.percentile(boots, 2.5)),
                                                                float(np.percentile(boots, 97.5))],
                        "H_upper95": float(np.percentile(boots, 95)), "class_mass": hc["class_mass"],
                        "undecided_mass": hc["undecided_mass"], "per_token": hc["per_token"]}
        cells = unit_cells(u, U)
        rec["cells"] = cells
        for sname in SAMPLERS:
            rec[f"delta_pred_10_03_{sname}"] = cells[f"T1.0_{sname}"]["a_min"] - cells[f"T0.3_{sname}"]["a_min"]
            rec[f"delta_pred_10_13_{sname}"] = cells[f"T1.3_{sname}"]["a_min"] - cells[f"T1.0_{sname}"]["a_min"]
        rec["pred_correct_a_min"] = {c: v["a_min"] * U["twin_pass_rate_a_min"] for c, v in cells.items()}
        rec["margins"] = margins(U)
        rec["replay"] = replay_slots(u, U)
        rec["topk_report"] = topk_report(U)
        if u in S4:
            rec["s4"] = s4_predictions(u, U, S4[u])
        rec["fork_mode_rule"] = F[u]["mode"]
        out["units"][u] = rec
    out["collapsed"] = collapsed_view(COL) if COL else {}
    out["assumptions"] = ["Phat(A | t) estimated at T = 1 carries to other T (one-token concentration; Test 1)",
                          "q_rest (A's share among twin programs off every listed opening) is T-invariant",
                          "S4 pushed/exchanged predictions reuse the unpushed Phat(A | t)"]
    return out


def commit2() -> dict[str, str]:
    body = build_commit2()
    write_json(RESULTS_DIR / "predictions_view.json", body)
    code = CM.code_hashes(["src/analysis_T.py", "src/predictions7.py", "src/predict.py", "src/replay.py",
                           "src/forks.py", "src/opening_cls.py", "src/stages7b.py", "src/rederive.py"])
    return CM.commit("commit2_predictions", {"predictions": body, "scoring_code_sha256": code,
                                             "note": "committed before the first S3 sweep or S4 generation sample"})


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "view"
    if what == "commit2":
        print(commit2())
    else:
        b = build_commit2()
        write_json(RESULTS_DIR / "predictions_view.json", b)
        print(json.dumps({u: {"H": v["test1"]["H_bits"], "cells": {c: round(x["a_min"], 3) for c, x in
                                                                    v["cells"].items()}}
                          for u, v in b["units"].items()}, indent=1))
