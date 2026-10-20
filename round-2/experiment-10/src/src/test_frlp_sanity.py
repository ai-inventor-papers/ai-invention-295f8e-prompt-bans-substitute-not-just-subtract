#!/usr/bin/env python3
"""T6 FRLP sanity -> results/tests_frlp_sanity.json.

- Under its own forced prompts, L_j(F_j,k) should lie in [-0.7, 0.2] for most k (the mixture proposal makes the mean of
  exp(L_j(F_j,k)) over k equal 1 by construction, so the spread across k measures paraphrase heterogeneity);
- for the sampled default d under the baseline, L_d should be close to log of its sampled share (per segment s);
- the implied baseline distribution per task is listed beside the sampled one.
"""

from __future__ import annotations

import collections
import json

import numpy as np

from src.ws import DATA, RESULTS, read_jsonl, write_json
from src import analysis_c1 as A
from src import run_analysis as RA
from loguru import logger


@logger.catch(reraise=True)
def main() -> None:
    out: dict = {"own_forced": {}, "default_vs_sampled": {}}
    lab = read_jsonl(DATA / "labelled.jsonl")
    for task in RA.TASKS:
        td = RA.load_task(task)
        v = A.View(td, RA.variant_cells(td, "full"))
        for j in td.algs:
            conds = [c for c in td.conds if (c.startswith("forced:") or c.startswith("forced_desc:")) and c.split(":")[1] == j]
            L = np.array([v.a(c, [j])[0] for c in conds])
            out["own_forced"][f"{task}:{j}"] = {"n_prompts": len(conds), "L_min": float(np.min(L)), "L_max": float(np.max(L)),
                                                "L_median": float(np.median(L)),
                                                "share_in_[-0.7,0.2]": float(np.mean((L >= -0.7) & (L <= 0.2))),
                                                "mean_exp_L": float(np.mean(np.exp(L)))}
        d = td.d
        per_s = {}
        for s in range(5):
            rows = [r for r in lab if r["task"] == task and r["condition"] == f"baseline:s{s}" and r["label"] != "no_code"]
            share = sum(r["label"] == d for r in rows) / max(1, len(rows))
            Ld = float(v.a(f"baseline:s{s}", [d])[0])
            per_s[f"s{s}"] = {"L_d": Ld, "log_sampled_share": float(np.log(max(share, 1e-9))), "sampled_share": share,
                              "implied_mass_exp_L_d": float(np.exp(Ld))}
        cnt = collections.Counter(r["label"] for r in lab if r["task"] == task and r["kind"] == "baseline" and r["label"] != "no_code")
        n = sum(cnt.values())
        Lb = np.mean([v.a(f"baseline:s{s}", td.algs) for s in range(5)], axis=0)
        out["default_vs_sampled"][task] = {"default": d, "per_segment": per_s,
                                           "mean_abs_gap_nats": float(np.mean([abs(x["L_d"] - x["log_sampled_share"]) for x in per_s.values()])),
                                           "implied_exp_L_mean_over_s": dict(zip(td.algs, np.exp(Lb).tolist())),
                                           "sampled_share": {j: cnt.get(j, 0) / max(1, n) for j in td.algs + ["other"]}}
    own = [x["share_in_[-0.7,0.2]"] for x in out["own_forced"].values()]
    out["summary"] = {"mean_share_of_forced_prompts_in_range": float(np.mean(own)),
                      "algorithms_with_majority_in_range": int(sum(x > 0.5 for x in own)), "n_algorithms": len(own)}
    write_json(RESULTS / "tests_frlp_sanity.json", out)
    print(json.dumps(out["summary"]), json.dumps({t: round(x["mean_abs_gap_nats"], 3) for t, x in out["default_vs_sampled"].items()}))


if __name__ == "__main__":
    main()
