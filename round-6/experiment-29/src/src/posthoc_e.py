#!/usr/bin/env python3
"""POST-HOC analyses (NOT pre-registered; added after commit #0 once the interim factorial showed W16A16 moving).

1. Iteration-5 replication: IT5_a1 / IT5_a2 = exp27's exact PN5 seeds (stable_seed(task,'PN5',w,k)) at exp27's
   per-template ban-free unit ||h_twin,w|| x r_Q(l), run in THIS engine (B = 20, exp19 batch path) under W16A16 and
   W8A8. Compared slot by slot with exp27's own PN_a1 / PN_a2 rows (same seeds, unit definition and CRN streams; exp27
   used its left-padded mixed-prompt batch path and a 1,536-token cap on T2).
2. Decomposition at W16A16 (paired by CRN slot): PN_a2 (exp19 seeds, ban unit) vs PNF_a2 (exp19 seeds, ban-free unit
   averaged over templates) vs IT5_a2 (exp27 seeds, per-template ban-free unit) -> unit vs direction sample.
3. Unit profile: ban unit n[l,p] vs this artifact's ban-free unit per block (mean ratio, position correlation, CV).
Output: results/posthoc.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

import analysis_e as A

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"


def main() -> None:
    rows = A.merge_rows(out_p=None)
    idx = A.cell_index(rows)
    out: dict[str, Any] = {"note": "POST-HOC, not pre-registered", "tasks": {}}
    e27 = {}
    for r in A.read_jsonl(ROOT / "inputs" / "exp27" / "data" / "labels.jsonl"):
        e27[r["sample_id"]] = r
    e27raw = {r["sample_id"]: r for r in A.read_jsonl(ROOT / "inputs" / "exp27" / "data" / "samples_raw.jsonl")
              if r.get("arm") in ("PN_a1", "PN_a2") and r.get("task") in ("T10", "T2")}
    for t in ("T10", "T2"):
        res: dict[str, Any] = {}
        for p in ("W16A16", "W8A8"):
            for a5, a in (("PN_a1", "IT5_a1"), ("PN_a2", "IT5_a2")):
                c = idx.get((t, p, a), {})
                if not c:
                    continue
                n = agree = same_corr = 0
                y27 = []
                for (w, k, _), r in c.items():
                    sid = f"{t}|{a5}|{w}|{k}"
                    if sid not in e27 or sid not in e27raw:
                        continue
                    assert e27raw[sid]["direction_seed"] == r["direction_seed"], "seed mismatch with exp27"
                    l27 = e27[sid]
                    n += 1
                    agree += l27.get("label") == r.get("label")
                    y = int(bool(l27.get("passed")) and l27.get("label") not in (A.DEFAULT[t], "invalid", None))
                    y27.append(y)
                    same_corr += y == A.y_correct(r)
                res[f"{p}|{a}"] = {"N": len(c), "Y_correct": float(np.mean([A.y_correct(r) for r in c.values()])),
                                   "exp27_matched_slots": n, "exp27_Y_correct_same_slots": float(np.mean(y27)) if y27 else None,
                                   "label_agreement_with_exp27": agree / n if n else None,
                                   "Y_correct_agreement_with_exp27": same_corr / n if n else None}
        res["W16A16_PN_a2_vs_PNF_a2"] = A.contrast(idx, t, "PN_a2", "W16A16", "W16A16", arm_b="PNF_a2")
        res["W16A16_PN_a2_vs_IT5_a2"] = A.contrast(idx, t, "PN_a2", "W16A16", "W16A16", arm_b="IT5_a2")
        res["W16A16_PNF_a2_vs_IT5_a2"] = A.contrast(idx, t, "PNF_a2", "W16A16", "W16A16", arm_b="IT5_a2")
        res["W8A8_vs_W16A16_IT5_a2"] = A.contrast(idx, t, "IT5_a2", "W8A8", "W16A16")
        # unit profile
        try:
            from sampling_v4 import load_norms

            ban = load_norms(t)
            prof = {}
            for p in ("W16A16", "W8A8"):
                f = RES / f"unit_banfree_{t}_{p}.npy"
                if f.exists():
                    nf = np.load(f)
                    prof[p] = {"mean_ratio_per_block": [float(x) for x in (nf / np.maximum(ban, 1e-6)).mean(1)],
                               "position_corr_per_block": [float(np.corrcoef(nf[j], ban[j])[0, 1])
                                                           for j in range(ban.shape[0])],
                               "cv_ban_per_block": [float(ban[j].std() / ban[j].mean()) for j in range(ban.shape[0])],
                               "cv_banfree_per_block": [float(nf[j].std() / nf[j].mean()) for j in range(ban.shape[0])],
                               "max_over_mean_ban_b12": float(ban[0].max() / ban[0].mean()),
                               "max_over_mean_banfree_b12": float(nf[0].max() / nf[0].mean())}
            res["unit_profile"] = prof
        except (ImportError, OSError, ValueError) as e:
            res["unit_profile_error"] = str(e)
        out["tasks"][t] = res
    A.write_json(RES / "posthoc.json", out)
    print(json.dumps({t: {k: (v if not isinstance(v, dict) or "share_A" not in v else
                              {kk: v[kk] for kk in ("share_A", "share_B", "diff", "mcnemar")})
                          for k, v in d.items() if k != "unit_profile"} for t, d in out["tasks"].items()}, indent=1,
                     default=str)[:4000])


if __name__ == "__main__":
    main()
