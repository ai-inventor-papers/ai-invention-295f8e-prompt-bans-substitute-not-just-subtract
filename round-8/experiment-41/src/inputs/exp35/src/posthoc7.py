#!/usr/bin/env python3
"""POST-HOC sensitivities (not committed tests; reported separately in results/posthoc.json):

1. Judged continuation labels: the committed token conditionals counted 'disputed' continuations as 'other'; here the
   blind judges' majority labels replace them and the committed prediction function is re-run.
2. Twin-referenced view: the A_min share of the same-seed T 1.0 sweep cell vs the twin (different slots, same
   sampler) - a binomial consistency check of the sweep's reference cell.
3. Top-k 10 identity: how many same-seed top-k 10 programs are token-identical to their top-p 1 counterparts, and the
   largest truncated mass along the generated paths' openings (teacher-forced, from cache/tf).
4. Prediction error decomposition per cell: the part of the predicted share carried by the opening (w_T x F_T) vs by
   q_rest (off-opening programs), observed on-opening vs predicted.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import fisher_exact

sys.path.insert(0, str(Path(__file__).resolve().parent))

import predictions7 as P7  # noqa: E402
from analysis_T import rows_with_labels  # noqa: E402
from cfg7 import (CONTS, DATA_DIR, PRED_DIR, RESULTS_DIR, SAMPLERS, TEMPS, read_json, read_jsonl,  # noqa: E402
                  write_json)


def judged_counts(u: str, U: dict[str, Any]) -> dict[str, Any]:
    C = U["cats"]
    J = {r["sid"]: r["label"] for r in read_jsonl(DATA_DIR / "judge_labels.jsonl") if r.get("label")}
    full = {r["sid"]: r["label"] for r in read_jsonl(DATA_DIR / "continuation_labels.jsonl")}
    newU = json.loads(json.dumps(U))
    changed = 0
    for cid, cl in newU["clusters"].items():
        cnt: dict[str, np.ndarray] = {}
        res = np.zeros(len(C))
        for r in read_jsonl(CONTS):
            if r["unit"] != u or r.get("cluster") != cid or r.get("kind") not in ("tok", "resid"):
                continue
            lab = r.get("label") or full.get(r["cid"]) or "other"
            if lab == "disputed" and r["cid"] in J:
                lab = J[r["cid"]]
                changed += 1
            i = C.index(lab) if lab in C else len(C) - 1
            if r["kind"] == "tok":
                cnt.setdefault(str(r["tok"]), np.zeros(len(C)))[i] += 1
            else:
                res[i] += 1
        cl["counts"] = {t: v.tolist() for t, v in cnt.items()}
        cl["resid_counts"] = res.tolist()
    newU["_unit"] = u
    cells = P7.unit_cells(u, newU)
    return {"n_continuation_labels_changed": changed,
            "cells_a_min": {c: v["a_min"] for c, v in cells.items()},
            "H_bits": P7.h_conditional(newU)["H_bits"]}


def main() -> dict[str, Any]:
    pv = read_json(RESULTS_DIR / "predictions_view.json")
    R = read_json(PRED_DIR / "predictions_raw.json")
    rows = rows_with_labels()
    t2 = read_json(RESULTS_DIR / "test2.json")
    out: dict[str, Any] = {"label": "POST HOC - not part of the committed tests"}
    for u, U in pv["units"].items():
        A = U["A_min"]
        rec: dict[str, Any] = {}
        try:
            rec["judged_continuations"] = judged_counts(u, {**R[u]})
            rec["judged_continuations"]["committed_cells_a_min"] = {c: v["a_min"] for c, v in U["cells"].items()}
        except (KeyError, ValueError) as e:
            rec["judged_continuations"] = {"error": str(e)}
        tw = [r for r in rows if r["unit"] == u and r["arm"] == "TWIN"]
        sw = [r for r in rows if r["unit"] == u and r["arm"] == "SWEEP" and r["cell"] == "T1.0_p1"]
        kt, ks = sum(r["label"] == A for r in tw), sum(r["label"] == A for r in sw)
        rec["twin_vs_sweep_T1"] = {"twin": [kt, len(tw)], "sweep_T1.0_p1": [ks, len(sw)],
                                   "fisher_p": float(fisher_exact([[kt, len(tw) - kt], [ks, len(sw) - ks]])[1])
                                   if sw else None}
        sweep = {(r["cell"], r["template"], r["slot"]): r for r in rows if r["unit"] == u and r["arm"] == "SWEEP"}
        same = n = 0
        for (c, w, s), r in sweep.items():
            if c.endswith("_p1") and (c.replace("_p1", "_k10"), w, s) in sweep:
                n += 1
                same += sweep[(c.replace("_p1", "_k10"), w, s)]["token_ids"] == r["token_ids"]
        rec["topk10_token_identical"] = [same, n]
        dec = {}
        for T in TEMPS:
            c = f"T{T}_p1"
            pw = U["cells"][c]["per_template"]
            on = np.mean([v["on_opening"] for v in pw.values()])
            q = U["q_rest"][U["cats"].index(A)]
            obs = t2["per_unit"].get(u, {}).get("cells", {}).get(c, {})
            dec[c] = {"pred_a_min": U["cells"][c]["a_min"], "pred_from_opening": U["cells"][c]["a_min"] - (1 - on) * q,
                      "pred_from_rest": (1 - on) * q, "pred_on_opening": on, "obs_on_opening": obs.get("on_opening_obs"),
                      "obs_a_min": obs.get("a_min")}
        rec["decomposition"] = dec
        # replay-implied share of the ACTUAL 50 sweep streams (committed per-slot replay predictions) vs observed:
        # separates the expectation-vs-realisation gap of a 50-stream cell from a mechanism error
        rs = {}
        for T in TEMPS:
            for sname in SAMPLERS:
                c = f"T{T}_{sname}"
                preds = [v["pred"] for k, v in U["replay"].items() if k.endswith("|" + c)]
                obs = t2["per_unit"].get(u, {}).get("cells", {}).get(c, {})
                rs[c] = {"replay_share": sum(p == A for p in preds) / max(len(preds), 1),
                         "committed_expectation": U["cells"][c]["a_min"], "observed": obs.get("a_min")}
        rec["replay_implied_share"] = rs
        out[u] = rec
    write_json(RESULTS_DIR / "posthoc.json", out)
    return out


if __name__ == "__main__":
    o = main()
    print(json.dumps({u: {k: v for k, v in r.items() if k != "decomposition"} for u, r in o.items()
                      if isinstance(r, dict)}, indent=1)[:3000])
