#!/usr/bin/env python3
"""Supplementary readout (beyond the plan): natural-proposal FRLP.

The arm-b behaviour samples labelled X (BFS on T1, Dijkstra on T2) are exact draws from p(. | b_{w,n}) for their own
template w and neutral noun n, so for any arm c of the same (w, n)
    log mean_m exp(l(x_m | c) - l(x_m | b))  ->  log P(X-program | c) / P(X-program | b)   (self-normalised over X).
Their exact generated token ids are re-scored at batch 1 under every arm (no re-tokenisation, no proposal mismatch).
D_nat(arm) = template mean of that log ratio; route fractions as in the primary analysis; two-level bootstrap over
templates and programs. exp(D_nat(a)) is directly comparable with the behavioural banned-share ratio.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from typing import Any

import numpy as np
from loguru import logger

from arms import build_arm, ko_config
from cfg import DATA_DIR, PROMPTS_DIR, RESULTS_DIR, TASKS, TEMPLATE_IDS, X_KEY, read_jsonl, write_json, write_jsonl

ARMS = ("a", "b", "c", "d", "e", "f", "K0", "K1", "K2", "B1", "B2", "B3", "K0b")
OUT = DATA_DIR / "natural_frlp_scores.jsonl"


def score_all() -> list[dict[str, Any]]:
    from engine import free, load_model, prefill, score

    fp = json.loads((PROMPTS_DIR / "frozen_prompts.json").read_text())
    S = [s for s in read_jsonl(DATA_DIR / "samples.jsonl") if s["condition"] == "b" and s["label"] == X_KEY[s["task"]]]
    tok, model = load_model()
    rows = []
    t0 = time.time()
    for t in TASKS:
        for w in TEMPLATE_IDS:
            progs = [s for s in S if s["task"] == t and s["template"] == w]
            tw = fp["tasks"][t]["templates"][w]
            p0, p1 = tw["ban"]["p0"], tw["ban"]["p1"]
            pre = {"ban": prefill(model, tw["ban"]["ids"]), "A": prefill(model, tw["neutral_A"]["ids"]),
                   "B": prefill(model, tw["neutral_B"]["ids"])}
            for arm in ARMS:
                for noun in ("A", "B"):
                    pn = [s for s in progs if s["noun_slot"] == noun]
                    if not pn:
                        continue
                    a = build_arm(arm, pre, noun, p1)
                    lps = score(model, a, [s["token_ids"] for s in pn], ko=ko_config(arm, p0, p1))
                    for s, lp in zip(pn, lps):
                        rows.append({"task": t, "template": w, "noun": noun, "sample_id": s["sample_id"], "arm": arm,
                                     "ll": float(np.sum(lp.astype(np.float64))), "n_tokens": len(lp)})
                    del a
            free(pre)
            logger.info(f"natural FRLP {t}/{w}: {len(progs)} programs x {len(ARMS)} arms ({time.time() - t0:.0f}s)")
    write_jsonl(OUT, rows)
    return rows


def analyse(rows: list[dict[str, Any]], n_boot: int = 2000) -> dict[str, Any]:
    rng = np.random.default_rng(99)
    out: dict[str, Any] = {"per_task": {}}
    beh = defaultdict(dict)
    for s in read_jsonl(DATA_DIR / "samples.jsonl"):
        beh[(s["task"], s["condition"])].setdefault("n", 0)
        beh[(s["task"], s["condition"])]["n"] += 1
        beh[(s["task"], s["condition"])]["k"] = beh[(s["task"], s["condition"])].get("k", 0) + \
            int(s["label"] == X_KEY[s["task"]])
    boots = {}
    for t in TASKS:
        R = [r for r in rows if r["task"] == t]
        units = sorted({(r["template"], r["sample_id"]) for r in R})
        ll = {(r["template"], r["sample_id"], r["arm"]): r["ll"] for r in R}
        tmpl = {w: [u for u in units if u[0] == w] for w in TEMPLATE_IDS}
        lr = {arm: {w: np.array([ll[(w, u[1], arm)] - ll[(w, u[1], "b")] for u in tmpl[w]]) for w in TEMPLATE_IDS}
              for arm in ARMS}

        def D(arm: str, wsel: list[str], idx: dict[str, np.ndarray] | None = None) -> float:
            vals = []
            for w in wsel:
                v = lr[arm][w] if idx is None else lr[arm][w][idx[w]]
                m = v.max()
                vals.append(m + np.log(np.mean(np.exp(v - m))))
            return float(np.mean(vals))

        point = {arm: D(arm, TEMPLATE_IDS) for arm in ARMS}
        ess = {arm: {w: float(np.exp(2 * np.logaddexp.reduce(lr[arm][w]) - np.logaddexp.reduce(2 * lr[arm][w])))
                     for w in TEMPLATE_IDS} for arm in ARMS}
        bs = {arm: np.empty(n_boot) for arm in ARMS}
        for b in range(n_boot):
            ws = [TEMPLATE_IDS[i] for i in rng.integers(0, len(TEMPLATE_IDS), len(TEMPLATE_IDS))]
            idx = {w: rng.integers(0, len(tmpl[w]), len(tmpl[w])) for w in TEMPLATE_IDS}
            for arm in ARMS:
                bs[arm][b] = D(arm, ws, idx)
        boots[t] = bs

        def ci(x: np.ndarray) -> list[float]:
            x = x[np.isfinite(x)]
            return [float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))]

        def ratio(a: str, b_: str = "a") -> tuple[float, list[float]]:
            return point[a] / point[b_], ci(bs[a] / bs[b_])

        fd, fdci = ratio("d")
        fp_, fpci = ratio("c")
        ent = {"n_programs": len(units), "D_nat": point, "D_nat_ci": {a: ci(bs[a]) for a in ARMS},
               "ESS_per_template": ess, "F_direct_nat": fd, "F_direct_nat_ci": fdci,
               "F_prompt_nat": fp_, "F_prompt_nat_ci": fpci,
               "F_R_nat": point["e"] / point["a"], "F_spec_nat": point["f"] / point["a"],
               "knockout_restoration_nat": {k: (point[k] - point["a"]) / (-point["a"]) for k in
                                            ("K0", "K1", "K2", "B1", "B2", "B3")},
               "K0b_generic_damage_nat": point["K0b"]}
        # compare exp(D_nat(arm)) with the behavioural ratio P(X|arm) / P(X|b)
        cmp = {}
        for arm in ("a", "c", "d", "K1", "K2"):
            ka, na = beh[(t, arm)].get("k", 0), beh[(t, arm)].get("n", 0)
            kb, nb = beh[(t, "b")].get("k", 0), beh[(t, "b")].get("n", 0)
            if na and nb and kb:
                cmp[arm] = {"behavioural_ratio": (ka / na) / (kb / nb), "exp_D_nat": float(np.exp(point[arm]))}
        ent["behaviour_vs_natural_frlp"] = cmp
        out["per_task"][t] = ent
    sa = sum(out["per_task"][t]["D_nat"]["a"] for t in TASKS)
    sc = sum(out["per_task"][t]["D_nat"]["c"] for t in TASKS)
    sd = sum(out["per_task"][t]["D_nat"]["d"] for t in TASKS)
    ba = sum(boots[t]["a"] for t in TASKS)
    bc = sum(boots[t]["c"] for t in TASKS)
    bd = sum(boots[t]["d"] for t in TASKS)
    out["pooled"] = {"F_direct_nat": sd / sa, "F_direct_nat_ci": [float(np.percentile(bd / ba, 2.5)),
                                                                   float(np.percentile(bd / ba, 97.5))],
                     "F_prompt_nat": sc / sa, "F_prompt_nat_ci": [float(np.percentile(bc / ba, 2.5)),
                                                                   float(np.percentile(bc / ba, 97.5))]}
    write_json(RESULTS_DIR / "natural_frlp.json", out)
    return out


def main() -> None:
    from cfg import setup_logging

    setup_logging("natural_frlp")
    rows = read_jsonl(OUT) if OUT.exists() else score_all()
    res = analyse(rows)
    for t, e in res["per_task"].items():
        logger.info(f"{t}: D_nat={ {k: round(v, 2) for k, v in e['D_nat'].items()} } F_direct_nat={e['F_direct_nat']:.3f} "
                    f"{e['F_direct_nat_ci']} F_prompt_nat={e['F_prompt_nat']:.3f} {e['F_prompt_nat_ci']} "
                    f"beh-vs-nat={e['behaviour_vs_natural_frlp']}")
    logger.info(f"pooled: {res['pooled']}")


if __name__ == "__main__":
    main()
