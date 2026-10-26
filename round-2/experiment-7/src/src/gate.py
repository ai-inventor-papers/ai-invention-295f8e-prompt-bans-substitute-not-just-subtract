#!/usr/bin/env python3
"""Step 5: FRLP validity gate against the exp1 sampled events (definitions frozen in commitments.log).

(a) calibration on the exp1 baseline paraphrases: S = sum_j exp(L_j) over measurable j and m = exp(L_default)/S;
    PASS if mean S in [0.3, 3] and mean m >= 0.9.
(b) per event e and paraphrase k: q_ek(j) ~ exp(L_j(e,k)) over allowed labels (half-1 programs);
    q' = 0.93 q + 0.05 uniform(allowed) + 0.02 other; reference u = 0.98 uniform(allowed) + 0.02 other;
    d = mean over the paraphrase's own samples of log q'(label) - log u(label) (banned-label samples excluded);
    d_e = mean over paraphrases; PASS if mean_e d_e >= 0.3 nats.
(c) argmax_j mean_k q_ek equals the realised attempted mode in >= 80% of clear-mode events.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from loguru import logger
from scipy.stats import spearmanr

from config import (DEFAULT_MODE, ESS_FLAG, GATE_A_M_MIN, GATE_A_S_RANGE, GATE_B_MIN, GATE_C_MIN, MODES, OTHER,
                    RESULTS, TASKS, read_json, setup_logging, utc_now, write_json)
from frlp import VARIANTS, TaskData, build_task_data


def implied(td: TaskData, cond: str, allowed: list[str], half: str, vname: str) -> tuple[dict[str, float], dict]:
    Ls, ess = {}, {}
    for j in allowed:
        if j in td.measurable:
            c = td.cell(cond, j, half, vname)
            if c["n"] > 0 and np.isfinite(c["L"]):
                Ls[j] = c["L"]
                ess[j] = c["ess"]
    if not Ls:
        return {}, ess
    mx = max(Ls.values())
    z = sum(math.exp(v - mx) for v in Ls.values())
    return {j: (math.exp(Ls[j] - mx) / z if j in Ls else 0.0) for j in allowed}, ess


def gate(tds: dict[str, TaskData], vname: str = "primary", max_para: int = 5) -> dict[str, Any]:
    ev_file = read_json(RESULTS / "gate_events.json")
    res: dict[str, Any] = {"variant": vname, "events": [], "gate_a": {}}
    # (a)
    S_all, m_all = [], []
    for t in TASKS:
        td = tds[t]
        base = next(e for e in ev_file["events"] if e["event_id"] == f"{t}|baseline")
        rows = []
        for p in base["paraphrases"][:max_para]:
            cond = f"exp1|baseline|p{p['paraphrase_id']}"
            Ls = {j: td.cell(cond, j, "all", vname)["L"] for j in td.measurable}
            Ls = {j: v for j, v in Ls.items() if np.isfinite(v)}
            if not Ls:
                continue
            S = sum(math.exp(v) for v in Ls.values())
            m = math.exp(Ls.get(DEFAULT_MODE[t], -math.inf)) / S if S > 0 else math.nan
            rows.append({"paraphrase_id": p["paraphrase_id"], "S": S, "m_default": m,
                         "L": Ls})
            S_all.append(S)
            m_all.append(m)
        res["gate_a"][t] = rows
    mS = float(np.mean(S_all)) if S_all else math.nan
    mm = float(np.mean(m_all)) if m_all else math.nan
    res["a"] = {"mean_S": mS, "mean_m_default": mm,
                "pass": bool(GATE_A_S_RANGE[0] <= mS <= GATE_A_S_RANGE[1] and mm >= GATE_A_M_MIN)}
    # (b) and (c)
    d_events, hits, n_clear, low_ess, n_cells = [], 0, 0, 0, 0
    pooled_impl, pooled_real = [], []
    for e in ev_file["events"]:
        t = e["task"]
        td = tds[t]
        allowed = [j for j in MODES[t] if j not in e["banned"]]
        per_para, qs = [], []
        for p in e["paraphrases"][:max_para]:
            cond = f"exp1|{e['condition']}|p{p['paraphrase_id']}"
            q, ess = implied(td, cond, allowed, "h1", vname)
            for v in ess.values():
                n_cells += 1
                low_ess += int(v < ESS_FLAG)
            if not q:
                continue
            qs.append(q)
            ua = 0.98 / len(allowed)
            labs = [lbl if lbl in MODES[t] else OTHER for lbl in p["labels"]]
            excluded = sum(lbl in e["banned"] for lbl in labs)
            ds = []
            for lbl in labs:
                if lbl in e["banned"]:
                    continue
                if lbl == OTHER:
                    ds.append(0.0)
                else:
                    qp = 0.93 * q.get(lbl, 0.0) + 0.05 / len(allowed)
                    ds.append(math.log(qp) - math.log(ua))
            per_para.append({"paraphrase_id": p["paraphrase_id"], "d": float(np.mean(ds)) if ds else math.nan,
                             "n_scored": len(ds), "n_banned_excluded": excluded, "q": q,
                             "ess": ess})
        if not qs:
            continue
        qbar = {j: float(np.mean([q[j] for q in qs])) for j in allowed}
        d_e = float(np.nanmean([pp["d"] for pp in per_para]))
        arg = max(qbar, key=qbar.get)
        real = e["distribution_allowed"]
        n_real = sum(v for k, v in real.items() if k != OTHER) or 1
        for j in allowed:
            pooled_impl.append(qbar[j])
            pooled_real.append(real.get(j, 0) / n_real)
        hit = arg == e["realised_mode"]
        if e["clear_mode"]:
            n_clear += 1
            hits += int(hit)
        d_events.append(d_e)
        res["events"].append({"event_id": e["event_id"], "d_e": d_e, "implied_mean": qbar, "argmax": arg,
                              "realised_mode": e["realised_mode"], "realised_allowed": real, "hit": hit,
                              "clear_mode": e["clear_mode"], "paraphrases": per_para})
    mean_d = float(np.mean(d_events)) if d_events else math.nan
    res["b"] = {"mean_d_e": mean_d, "n_events": len(d_events), "pass": bool(mean_d >= GATE_B_MIN)}
    res["c"] = {"hits": hits, "n_clear": n_clear, "rate": hits / max(1, n_clear),
                "pass": bool(n_clear > 0 and hits / n_clear >= GATE_C_MIN)}
    res["pass"] = bool(res["a"]["pass"] and res["b"]["pass"] and res["c"]["pass"])
    rho = spearmanr(pooled_impl, pooled_real).correlation if len(pooled_impl) > 2 else math.nan
    res["pooled_spearman_implied_vs_realised"] = float(rho) if rho is not None else math.nan
    res["ess_cells"] = {"n": n_cells, "n_below_5": low_ess, "frac_below_5": low_ess / max(1, n_cells),
                        "flag_more_than_half_low": bool(low_ess > n_cells / 2)}
    if not res["pass"]:
        res["failure_kind"] = [k for k in ("a", "b", "c") if not res[k]["pass"]]
    return res


def succession_descriptive(tds: dict[str, TaskData]) -> dict[str, Any]:
    """Step 7.2 part: FRLP-implied landing under exp1's own step-2 prompts vs exp1's sampled step-2 labels."""
    ev_file = read_json(RESULTS / "gate_events.json")
    out = {}
    for e in ev_file["succession_step2_descriptive"]:
        t = e["task"]
        td = tds[t]
        allowed = [j for j in MODES[t] if j not in e["banned"]]
        qs, banned_mass = [], []
        for p in e["paraphrases"]:
            cond = f"exp1|succession:2|p{p['paraphrase_id']}"
            q, _ = implied(td, cond, allowed, "h1", "primary")
            if q:
                qs.append(q)
            Ls = {j: td.cell(cond, j, "h1", "primary")["L"] for j in td.measurable}
            Ls = {j: v for j, v in Ls.items() if np.isfinite(v)}
            if Ls:
                tot = sum(math.exp(v) for v in Ls.values())
                banned_mass.append(sum(math.exp(Ls[j]) for j in e["banned"] if j in Ls) / tot)
        out[e["event_id"]] = {
            "implied_landing": {j: float(np.mean([q[j] for q in qs])) for j in allowed} if qs else None,
            "implied_banned_mass": float(np.mean(banned_mass)) if banned_mass else None,
            "exp1_realised": e["distribution_attempted"], "exp1_banned_share":
                e["n_banned_label_samples"] / max(1, e["n_samples"])}
    return out


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("gate")
    tds = build_task_data()
    tp = read_json(RESULTS.parent / "logs" / "throughput.json")
    max_para = int(tp.get("gate_paraphrases", 5))
    out = {"utc": utc_now(), "primary": gate(tds, "primary", max_para)}
    out["sensitivity"] = {}
    for v in VARIANTS:
        if v == "primary":
            continue
        g = gate(tds, v, max_para)
        out["sensitivity"][v] = {k: g[k] for k in ("a", "b", "c", "pass", "pooled_spearman_implied_vs_realised")}
    out["verdict"] = "PASS" if out["primary"]["pass"] else "FAIL (FRLP descriptive)"
    out["succession_step2"] = succession_descriptive(tds)
    write_json(RESULTS / "gate.json", out)
    p = out["primary"]
    logger.info(f"GATE {out['verdict']}: a={p['a']} b={p['b']} c={p['c']} rho={p['pooled_spearman_implied_vs_realised']}")


if __name__ == "__main__":
    main()
