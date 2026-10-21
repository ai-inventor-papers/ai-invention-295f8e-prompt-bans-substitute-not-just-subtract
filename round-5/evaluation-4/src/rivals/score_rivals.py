#!/usr/bin/env python3
"""(0i) Descriptive scoring of the FROZEN rival predictors against the iteration-4 escape fractions.

Order is enforced: the script first verifies rivals.json against rivals.json.sha256 and the hash chain in
commitments.log (genesis = sha256('iter5_dir1')), appends a 'targets opened' entry after the freeze entry, and only
then opens a target file.  These escape fractions generated the hypothesis, 9 of 15 tasks are tied at 0, and n = 15:
every number here is SCREEN / descriptive; no rival is declared beaten or winning.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

WS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WS / "src"))
sys.path.insert(0, str(WS / "rivals"))
from io_util import Inputs, as_bool  # noqa: E402
import stats_util as su  # noqa: E402
from compute_rivals import GENESIS, canon, chain_append  # noqa: E402

RIVALS = ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "K"]


def verify_freeze() -> dict[str, Any]:
    text = (WS / "rivals.json").read_text()
    sha = hashlib.sha256(text.encode()).hexdigest()
    stored = (WS / "rivals.json.sha256").read_text().split()[0]
    assert sha == stored, "rivals.json does not match rivals.json.sha256"
    lines = [json.loads(ln) for ln in (WS / "commitments.log").read_text().splitlines() if ln.strip()]
    prev = GENESIS
    for ln in lines:
        assert ln["prev_hash"] == prev, "commitments.log chain broken"
        h = hashlib.sha256((prev + canon(ln["entry"])).encode()).hexdigest()
        assert h == ln["entry_hash"], "commitments.log entry hash mismatch"
        prev = h
    freeze = [ln for ln in lines if ln["entry"].get("what") == "rivals.json frozen"]
    assert freeze and freeze[-1]["entry"]["rivals_sha256"] == sha, "no freeze entry for this rivals.json"
    t_freeze = datetime.fromisoformat(freeze[-1]["entry"]["utc"])
    now = datetime.now(timezone.utc)
    assert t_freeze < now, "freeze timestamp is not before the first target read"
    return {"rivals_sha256": sha, "freeze_utc": freeze[-1]["entry"]["utc"], "chain_len": len(lines),
            "verified_utc": now.isoformat()}


@logger.catch(reraise=True)
def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(WS / "logs" / "score_rivals.log", rotation="30 MB", level="DEBUG")
    ver = verify_freeze()
    riv = json.loads((WS / "rivals.json").read_text())
    h = chain_append({"seq": "targets", "utc": datetime.now(timezone.utc).isoformat(),
                      "what": "targets opened by rivals/score_rivals.py", "rivals_sha256": ver["rivals_sha256"]})
    logger.info(f"freeze verified ({ver['rivals_sha256'][:12]}...); targets-opened entry {h[:12]}...")
    I = Inputs()
    esc = I.json("exp22", "results/escape.json")
    tasks = riv["tasks"]
    T: dict[str, dict[str, float]] = {"E1": {}, "E2": {}, "E_pool": {}, "PN_excess_alpha_le2": {}}
    for t in tasks:
        e = esc[t]["E_t"]
        T["E1"][t] = e["1.0"]["E_t"]
        T["E2"][t] = e["2.0"]["E_t"]
        T["E_pool"][t] = (e["1.0"]["n_confirmed"] + e["2.0"]["n_confirmed"]) / (e["1.0"]["n_run"] + e["2.0"]["n_run"])
    # secondary target: per-sample plan noise (exp19), attempts off-default share excess over the twin, max over
    # alpha 0.5 / 1 / 2
    pn = I.jsonl("exp19", "data/samples.jsonl", must_contain='"arm": "PN_a') + \
        I.jsonl("exp19", "data/samples.jsonl", must_contain='"arm": "TWIN"')
    sweep = I.json("exp19", "results/alpha_sweep.json")
    pn_detail = {}
    for t in tasks:
        tw = [x for x in pn if x["task"] == t and x["arm"] == "TWIN"]
        D = su.modal(Counter(x["label"] for x in tw if as_bool(x["passed"])))[0]

        def off(rows: list[dict]) -> float:
            return sum(1 for x in rows if x["label"] not in (D, "invalid", "disputed")) / len(rows)
        base = off(tw)
        ex = {a: off([x for x in pn if x["task"] == t and x["arm"] == f"PN_a{a}"]) - base for a in ("0.5", "1", "2")}
        T["PN_excess_alpha_le2"][t] = max(ex.values())
        pn_detail[t] = {"twin_off": base, "excess_by_alpha": ex}
        if t in sweep:
            rec = {str(s["alpha"]): s["off_default_share"] for s in sweep[t]["sweep"]}
            pn_detail[t]["alpha_sweep_check"] = {a: (rec.get(f"{float(a)}"), ex[a] + base) for a in ex}
    movable = {t: int(T["E_pool"][t] > 0) for t in tasks}
    ties = {k: {"n_at_zero": sum(1 for v in d.values() if v == 0), "n_distinct": len(set(d.values()))}
            for k, d in T.items()}
    vals = riv["values"]
    defs = riv["definitions"]
    rows, res = [], {}
    pE = {}
    for rv in RIVALS:
        res[rv] = {}
        for tg in T:
            tk = [t for t in tasks if vals[rv].get(t) is not None]
            x = [vals[rv][t] for t in tk]
            y = [T[tg][t] for t in tk]
            ps = su.perm_spearman(x, y)
            out = {"n": len(tk), "rho": ps["rho"], "rho_oriented": (ps["rho"] * defs[rv]["orientation"])
                   if ps["rho"] is not None else None, "p_perm_two_sided": ps["p_two_sided"],
                   "mc_se": ps["mc_se_two_sided"], "kendall_tau_b": su.kendall_b(x, y),
                   "boot_ci95": su.boot_spearman(x, y)["ci95"], "n_tied_target_at_zero": sum(1 for v in y if v == 0)}
            if rv not in ("K",):
                kk = [vals["K"][t] for t in tk]
                out["partial_rho_given_K"] = su.partial_spearman(x, y, kk)
            if rv not in ("R8", "K"):
                t8 = [t for t in tk if vals["R8"].get(t) is not None]
                out["partial_rho_given_R8"] = su.partial_spearman([vals[rv][t] for t in t8], [T[tg][t] for t in t8],
                                                                  [vals["R8"][t] for t in t8])
                out["n_partial_R8"] = len(t8)
            if tg == "E_pool":
                au = su.auc_exact([defs[rv]["orientation"] * v for v in x], [movable[t] for t in tk])
                out["auc_oriented_movable"] = au["auc"]
                out["auc_p_exact_two_sided"] = au["p_exact_two_sided"]
                out["auc_n_splits"] = au["n_splits"]
                pE[rv] = ps["p_two_sided"]
            res[rv][tg] = out
            rows.append({"rival": rv, "name": defs[rv]["name"], "A1_transferable": defs[rv]["transferable"],
                         "orientation": defs[rv]["orientation"], "target": tg, **out,
                         "flag": riv["flags"].get(rv)})
    holm = su.holm({k: v for k, v in pE.items() if k != "K"})
    for row in rows:
        if row["target"] == "E_pool":
            row["holm_p_descriptive"] = holm.get(row["rival"])
    # sensitivities (E_pool)
    det = riv["details"]
    sens_def = {
        "R1_excluding_identical_openings": {t: (det["R1"].get(t) or {}).get("margin_excluding_identical_openings")
                                            for t in tasks},
        "R1_margin_of_means": {t: (det["R1"].get(t) or {}).get("margin_of_means") for t in tasks},
        "R2_mean_over_modes": {t: (det["R2"].get(t) or {}).get("mean_over_modes") for t in tasks},
        "R3_one_minus_norm_entropy": {t: (det["R3"].get(t) or {}).get("one_minus_norm_entropy") for t in tasks},
        "R6_min_ratio_over_alternatives": {t: (det["R6"].get(t) or {}).get("runtime_ratio_min_over_alternatives")
                                           for t in tasks},
        "R6_length_ratio_ast_nodes": {t: (det["R6"].get(t) or {}).get("length_ratio_ast_nodes") for t in tasks},
        "R6_length_ratio_sloc": {t: (det["R6"].get(t) or {}).get("length_ratio_sloc") for t in tasks},
        "R7_exp19_replication": {t: (det["R7"].get(t) or {}).get("exp19_replication") for t in tasks},
        "R8_ban_unit_over_residual_exp20": {t: (det["R8"].get(t) or {}).get("ban_unit_over_residual_norm_exp20_S0")
                                            for t in tasks},
        "R5_non_default_share": {t: ((det["R5"].get(t) or {}).get("non_default_share")
                                     if str((det["R5"].get(t) or {}).get("status", "")).startswith("OK") else None)
                                 for t in tasks},
        "K_modes_with_passing_reference": {t: float((det["K"].get(t) or {}).get("n_modes_reference_passes") or 0)
                                           for t in tasks},
    }
    sens = {}
    for name, d in sens_def.items():
        tk = [t for t in tasks if d.get(t) is not None]
        x, y = [d[t] for t in tk], [T["E_pool"][t] for t in tk]
        ps = su.perm_spearman(x, y)
        sens[name] = {"n": len(tk), "rho": ps["rho"], "p_perm_two_sided": ps["p_two_sided"],
                      "auc_raw_movable": su.auc_exact(x, [movable[t] for t in tk])["auc"] if len(tk) > 2 else None}
    # intercorrelation
    inter = []
    for a in RIVALS:
        row = {"rival": a}
        for b in RIVALS:
            tk = [t for t in tasks if vals[a].get(t) is not None and vals[b].get(t) is not None]
            row[b] = su.spearman([vals[a][t] for t in tk], [vals[b][t] for t in tk])
        inter.append(row)
    out = {"label": "SCREEN / descriptive: these escape fractions generated the hypothesis; Holm shown only as a guide",
           "freeze_verification": ver, "targets": T, "movable_E_pool_gt_0": movable, "ties": ties,
           "pn_detail": pn_detail, "scores": res, "holm_E_pool": holm, "sensitivities_E_pool": sens,
           "intercorrelation": inter, "n_perm": su.N_PERM, "n_boot": su.N_BOOT, "seed": su.SEED,
           "inputs_sha256": {k: v.get("sha256") for k, v in I.manifest.items()}}
    (WS / "results" / "rival_scores.json").write_text(json.dumps(out, indent=1, default=float))
    import csv
    (WS / "tables").mkdir(exist_ok=True)
    for name, rr in (("rivals_scores.csv", rows), ("rivals_intercorr.csv", inter)):
        keys: list[str] = []
        for r_ in rr:
            keys += [k for k in r_ if k not in keys]
        with (WS / "tables" / name).open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            for r_ in rr:
                w.writerow({k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in r_.items()})
    with (WS / "tables" / "rivals_values.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["task", "name"] + RIVALS + list(T) + ["movable"])
        for t in tasks:
            w.writerow([t, riv["task_names"][t]] + [vals[rv].get(t) for rv in RIVALS] + [T[k][t] for k in T]
                       + [movable[t]])
    logger.info("rival scores written: " + ", ".join(f"{rv} rho={res[rv]['E_pool']['rho']}" for rv in RIVALS))


if __name__ == "__main__":
    main()
