"""S3 analyses 0a-0e (engine, landing, movability, missing outputs, minor items). Refuses to run unless the S2
commit chain verifies, so no analysis output can predate the frozen screen inputs."""

from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from typing import Any

import numpy as np
from loguru import logger
from scipy import stats

from common import (EVAL3, TASK_NAME, WS, Inputs, bonett_wright_ci, bootstrap_spearman, clopper_pearson, fieller_ci,
                    fisher_greater, fisher_two_sided, mcnemar_exact, parse_dictish, poisson_binomial_upper, prov,
                    sha256_file, sha256_str, spearman, spearman_perm_p, wilcoxon_exact, write_json)
from load import (EXISTING, PANEL, PANEL_A, PANEL_B, PRIMARY13, base_pooled, beta_v6, load_units, t_u, twin_modal)

TAB, RES = WS / "tables", WS / "results"
DECISIVE = ["T10", "T2", "T05", "T1", "T03"]
ND10 = ["T04", "T06", "T08", "T11", "T13", "T14", "R1", "R2", "R3", "R6"]
BLOCKS = [str(b) for b in range(12, 24)]
DEFAULTS = {"T03": "full_sort", "T2": "dijkstra", "T05": "hash_map", "T10": "union_find", "T1": "bfs"}


def write_csv(name: str, rows: list[dict]) -> None:
    TAB.mkdir(exist_ok=True)
    if not rows:
        (TAB / name).write_text("")
        return
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with (TAB / name).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in r.items()})


def status(recorded: Any, recomputed: Any, tol: float, kind: str = "abs") -> str:
    if recorded is None:
        return "NEW"
    if recomputed is None:
        return "NOT_REPRODUCIBLE"
    if kind == "p":
        if recorded < 1e-4 and recomputed < 1e-4:
            return "MATCH" if abs(math.log10(recorded) - math.log10(max(recomputed, 1e-300))) < 1 else "CORRECTED"
        return "MATCH" if abs(recomputed - recorded) <= 0.1 * recorded + 1e-12 else "CORRECTED"
    return "MATCH" if abs(float(recomputed) - float(recorded)) <= tol + 1e-12 else "CORRECTED"


def verify_chain() -> list[dict]:
    lines = [ln for ln in (WS / "commitments.log").read_text().splitlines() if ln.strip()]
    prev = sha256_str("iter6_step0")
    out = []
    for ln in lines:
        utc, f, sha, p, ch = ln.split(" | ")
        ok = p == prev and sha256_str(prev + sha) == ch and sha256_file(WS / f) == sha
        out.append({"file": f, "ok": ok})
        if not ok:
            raise RuntimeError(f"commit chain broken at {f}")
        prev = ch
    return out


# ============================================================================================= 0a ENGINE
def engine(inp: Inputs, U: dict) -> dict[str, Any]:
    out: dict[str, Any] = {}
    # ---- M-0a.1 dose under two definitions
    ur_rec = inp.json("exp27", "results/unit_ratio.json")
    mpr_rows = defaultdict(list)
    mpr_blocks = defaultdict(lambda: defaultdict(list))
    for r in inp.jsonl("exp27", "data/samples_raw.jsonl"):
        if r.get("arm") in ("PN_a1", "PN_a2") and r.get("unit_ratio_banfree_over_ban"):
            ratio = r["unit_ratio_banfree_over_ban"]
            mpr_rows[r["task"]].append(float(np.mean([float(v) for v in ratio.values()])))
            for b, v in ratio.items():
                mpr_blocks[r["task"]][b].append(float(v))
    t27 = defaultdict(lambda: defaultdict(list))
    for r in inp.jsonl("exp27", "data/realised.jsonl"):
        if r.get("arm") in ("PN_a1", "PN_a2"):
            tm = parse_dictish(r["target_mean"])
            for b in BLOCKS:
                if b in tm:
                    t27[r["task"]][b].append(float(tm[b]) / float(r["alpha"]))
    t19 = defaultdict(lambda: defaultdict(list))
    t19_a1 = defaultdict(list)
    for r in inp.jsonl("exp19", "data/realised.jsonl"):
        if str(r.get("arm", "")).startswith("PN_a"):
            tm = parse_dictish(r["target_mean"])
            a = float(r["alpha"])
            for b in BLOCKS:
                if b in tm:
                    t19[r["task"]][b].append(float(tm[b]) / a)
            if r["arm"] == "PN_a1":
                t19_a1[r["task"]].append(float(np.mean([float(tm[b]) for b in BLOCKS if b in tm])))
    t174 = {"T1": (15.26, 0.75), "T2": (18.98, 0.83), "T03": (11.58, 0.97), "T04": (58.51, 0.30), "T05": (14.74, 0.78),
            "T06": (18.67, 0.62), "T08": (12.88, 0.88), "T10": (15.12, 0.75), "T11": (14.32, 0.80), "T13": (11.93, 0.95),
            "T14": (16.19, 0.70), "R1": (14.90, 0.76), "R3": (13.19, 0.86), "R6": (18.58, 0.62)}
    dose_rows, curves = [], {}
    for t in DECISIVE + ND10:
        if t not in t27 or t not in t19:
            dose_rows.append({"task": t, "name": TASK_NAME[t], "status": "NOT_REPRODUCIBLE: no realised rows"})
            continue
        A27 = {b: float(np.mean(t27[t][b])) for b in BLOCKS}
        A19 = {b: float(np.mean(t19[t][b])) for b in BLOCKS}
        r_rmn = {b: A27[b] / A19[b] for b in BLOCKS}
        r_mpr = {b: float(np.mean(mpr_blocks[t][b])) for b in BLOCKS} if t in mpr_blocks else {}
        D_rmn = float(np.mean(list(A27.values())) / np.mean(list(A19.values())))
        w = {b: A19[b] / sum(A19.values()) for b in BLOCKS}
        ident = float(sum(w[b] * r_rmn[b] for b in BLOCKS))
        D_mpr = float(np.mean(mpr_rows[t])) if mpr_rows.get(t) else None
        eq_rmn = float(np.mean(list(r_rmn.values())))
        eq_mpr = float(np.mean(list(r_mpr.values()))) if r_mpr else None
        rec_mpr = ur_rec.get(t, {}).get("banfree_over_ban_mean")
        rec_rmn = t174.get(t, (None, None))[1]
        ban_unit = float(np.mean(list(A19.values())))
        ban_a1 = float(np.mean(t19_a1[t])) if t19_a1.get(t) else None
        curves[t] = {"blocks": BLOCKS, "r_rmn": [r_rmn[b] for b in BLOCKS], "r_mpr": [r_mpr.get(b) for b in BLOCKS],
                     "w_ban": [w[b] for b in BLOCKS], "A19": [A19[b] for b in BLOCKS], "A27": [A27[b] for b in BLOCKS]}
        dose_rows.append({
            "task": t, "name": TASK_NAME[t], "decisive": t in DECISIVE, "n_rows_exp27_mpr": len(mpr_rows.get(t, [])),
            "D_mpr": D_mpr, "D_mpr_recorded": rec_mpr, "D_mpr_status": status(rec_mpr, D_mpr, 0.005),
            "D_rmn": D_rmn, "D_rmn_recorded_table174": rec_rmn,
            "D_rmn_status": status(rec_rmn, D_rmn, 0.01) if rec_rmn is not None else "NEW",
            "identity_weighted_mean_of_block_ratios": ident, "identity_residual": ident - D_rmn,
            "identity_holds": abs(ident - D_rmn) < 0.01,
            "equal_weight_mean_block_ratio_rmn": eq_rmn, "equal_weight_mean_block_ratio_mpr": eq_mpr,
            "gap_mpr_minus_rmn": (D_mpr - D_rmn) if D_mpr is not None else None,
            "gap_part_weighting": eq_rmn - D_rmn,
            "gap_part_within_block": (eq_mpr - eq_rmn) if eq_mpr is not None else None,
            "ban_unit_mean_norm_exp19": ban_unit, "ban_unit_alpha1_mean_over_blocks": ban_a1,
            "ban_unit_table174": t174.get(t, (None, None))[0],
            "ban_unit_status": status(t174.get(t, (None, None))[0], ban_unit, 0.05) if t in t174 else "NEW",
            "residual_norm_ratios": "carried from Table 174 (exp20/exp23 residual norms are not in this artifact's inputs)",
            "src_mpr": prov("exp27", "data/samples_raw.jsonl", "unit_ratio_banfree_over_ban"),
            "src_rmn": prov("exp27", "data/realised.jsonl", "target_mean") + " / " + prov("exp19", "data/realised.jsonl", "target_mean")})
    write_csv("dose_reconciliation.csv", dose_rows)
    out["dose"] = {"rows": dose_rows, "curves": curves}
    D = {r["task"]: r for r in dose_rows if "D_rmn" in r}
    # ---- M-0a.2 engine contrast (correct off-default share, N 50)
    cells = inp.json("exp27", "results/cells.json")
    sw = inp.json("exp19", "results/alpha_sweep.json")
    rec_contrast = {"T10": ((0.02, 0.02), (0.12, 0.60)), "T2": ((0.00, 0.04), (0.26, 0.54)), "T1": ((0.00, 0.02), (0.06, 0.24)),
                    "T03": ((0.08, 0.28), (0.28, 0.50)), "T05": ((0.00, 0.04), (0.00, 0.02))}
    fp8 = {}
    for t in DECISIVE:
        fp8[t] = {}
        for e in sw[t]["sweep"]:
            kc = sum(v for m, v in e["correct_comp"].items() if m != DEFAULTS[t])
            fp8[t][float(e["alpha"])] = {"n": e["n"], "k_correct_off": kc, "share_correct_off": kc / e["n"],
                                         "share_attempts_recorded": e["off_default_share"],
                                         "share_invalid_counts": e["off_default_share_invalid_counts"],
                                         "pass": e["pass"]}
    contrast = []
    for t in DECISIVE:
        for ai, a in enumerate((1.0, 2.0)):
            c = cells[f"{t}|PN_a{int(a)}"]
            nb = int(c["N"])
            kb_share = float(c["correct_only_off_default_share"])
            kb = round(kb_share * nb)
            f8 = fp8[t][a]
            k8, n8 = f8["k_correct_off"], f8["n"]
            k8a = round(f8["share_attempts_recorded"] * n8)
            p = fisher_two_sided(k8, n8 - k8, kb, nb - kb)
            pa = fisher_two_sided(k8a, n8 - k8a, kb, nb - kb)
            fold = ((k8 + 0.5) / (n8 + 1)) / ((kb + 0.5) / (nb + 1))
            fold_a = ((k8a + 0.5) / (n8 + 1)) / ((kb + 0.5) / (nb + 1))
            rb, r8 = rec_contrast[t][0][ai], rec_contrast[t][1][ai]
            contrast.append({"task": t, "name": TASK_NAME[t], "alpha": a, "bf16_k": kb, "bf16_n": nb, "bf16_share": kb / nb,
                             "bf16_share_recorded": rb, "bf16_status": status(rb, kb / nb, 0.005),
                             "bf16_off_default_share_attempts": float(c["off_default_share"]), "bf16_pass": float(c["pass"]),
                             "bf16_cp95": clopper_pearson(kb, nb),
                             "fp8_k_correct": k8, "fp8_n": n8, "fp8_share_correct": k8 / n8,
                             "fp8_share_attempts_recorded_field": f8["share_attempts_recorded"],
                             "fp8_share_recorded_in_report": r8,
                             "fp8_status_vs_correct_only": status(r8, k8 / n8, 0.005),
                             "fp8_status_vs_attempts_field": status(r8, f8["share_attempts_recorded"], 0.005),
                             "fp8_pass": f8["pass"], "fp8_cp95": clopper_pearson(k8, n8),
                             "fisher_p_correct_only": p, "fisher_p_attempt_shares": pa,
                             "fold_fp8_over_bf16_haldane": fold, "fold_attempt_shares_haldane": fold_a,
                             "src_bf16": prov("exp27", "results/cells.json", f"{t}|PN_a{int(a)}.correct_only_off_default_share"),
                             "src_fp8": prov("exp19", "results/alpha_sweep.json", f"{t}.sweep[alpha={a}].correct_comp")})
    write_csv("engine_contrast.csv", contrast)
    out["contrast"] = contrast
    # ---- M-0a.3 dose-matched test
    grid = [0.0, 0.5, 1.0, 2.0, 4.0]
    dm_rows = []
    for t in DECISIVE:
        twin_pass = fp8[t][0.0]["pass"]
        shares = [fp8[t][g]["share_correct_off"] for g in grid]
        lows = [clopper_pearson(fp8[t][g]["k_correct_off"], fp8[t][g]["n"])[0] for g in grid]
        for a in (1.0, 2.0):
            c = next(r for r in contrast if r["task"] == t and r["alpha"] == a)
            for dname in ("D_mpr", "D_rmn"):
                Dv = D[t][dname]
                if Dv is None:
                    continue
                dose = a * Dv
                p8 = float(np.interp(dose, grid, shares))
                p8_lo = float(np.interp(dose, grid, lows))
                flag = dose > 2.0 and fp8[t][4.0]["pass"] < 0.8 * twin_pass
                pb = float(stats.binom.cdf(c["bf16_k"], c["bf16_n"], p8))
                pb_lo = float(stats.binom.cdf(c["bf16_k"], c["bf16_n"], p8_lo))
                dm_rows.append({"task": t, "name": TASK_NAME[t], "alpha_bf16": a, "definition": dname, "D": Dv,
                                "dose_in_fp8_ban_units": dose, "fp8_share_interp": p8, "fp8_share_interp_cp_lower": p8_lo,
                                "bf16_k": c["bf16_k"], "bf16_n": c["bf16_n"], "p_binom_le_x": pb,
                                "p_binom_conservative": pb_lo, "flag_breakage_interval": flag,
                                "share_definition": "correct off-default programs / N on both engines"})
        # dose-dominance contrast: bf16 alpha 2 against FP8 alpha 1
        c2 = next(r for r in contrast if r["task"] == t and r["alpha"] == 2.0)
        k81, n81 = fp8[t][1.0]["k_correct_off"], fp8[t][1.0]["n"]
        dm_rows.append({"task": t, "name": TASK_NAME[t], "alpha_bf16": 2.0, "definition": "dominance: bf16 a2 vs FP8 a1",
                        "D": None, "dose_in_fp8_ban_units": f"{2 * D[t]['D_mpr']:.2f} (mpr) / {2 * D[t]['D_rmn']:.2f} (rmn) vs 1.00",
                        "fp8_k_a1": k81, "bf16_k": c2["bf16_k"], "bf16_n": c2["bf16_n"],
                        "fisher_p_two_sided": fisher_two_sided(k81, n81 - k81, c2["bf16_k"], c2["bf16_n"] - c2["bf16_k"]),
                        "fisher_p_fp8_greater": fisher_greater(k81, n81 - k81, c2["bf16_k"], c2["bf16_n"] - c2["bf16_k"])})
    write_csv("dose_matched.csv", dm_rows)
    out["dose_matched"] = dm_rows
    dec = [D[t] for t in DECISIVE]
    min_mpr = min(r["D_mpr"] for r in dec)
    min_rmn = min(r["D_rmn"] for r in dec)
    folds2 = {r["task"]: r["fold_fp8_over_bf16_haldane"] for r in contrast if r["alpha"] == 2.0}
    folds2_att = {r["task"]: r["fold_attempt_shares_haldane"] for r in contrast if r["alpha"] == 2.0}
    out["shortfall"] = {"one_minus_min_D_mpr": 1 - min_mpr, "one_minus_min_D_rmn": 1 - min_rmn,
                        "fold_alpha2_correct_only": folds2, "fold_alpha2_attempt_shares": folds2_att,
                        "statement": "the bf16 dose shortfall is at most "
                                     f"{100 * (1 - min_mpr):.0f}% (mean of per-position ratios) and {100 * (1 - min_rmn):.0f}% "
                                     "(ratio of mean norms) on the decisive tasks, against a fold drop at alpha 2 of "
                                     + ", ".join(f"{TASK_NAME[t]} {folds2[t]:.1f}x" for t in DECISIVE)
                                     + " (correct-only shares, Haldane +0.5); the cause is not established: engine, GPU, "
                                       "kernel and sampler streams all differ (Claim E decides it)"}
    return out


# ============================================================================================= 0b LANDING
def landing(inp: Inputs, U: dict, frozen_l3: dict) -> dict[str, Any]:
    a2 = inp.json("exp25", "results/a2_assoc_corrected.json")
    b2 = inp.json("exp26", "results/a2_panel.json")
    e2 = inp.json("exp28", "results/e_a2.json")
    pr = inp.json("exp28", "results/predictors.json")["units"]
    sc = inp.json("exp24", "results/screen_check.json")["r_t_vs_push_landing"]
    xa = inp.json("exp25", "results/extra_arm_a.json")
    br = inp.json("exp24", "results/base_repertoire.json")["per_task"]
    lc_by_event = {e["event"]: e for e in frozen_l3["events"]}
    events = []

    def lead(lc: dict) -> tuple[str | None, int, float]:
        if not lc:
            return None, 0, float("nan")
        s = sorted(lc.items(), key=lambda kv: (-kv[1], kv[0]))
        tot = sum(lc.values())
        nxt = s[1][1] if len(s) > 1 else 0
        return s[0][0], s[0][1], (s[0][1] - nxt) / tot

    def support_qwen(x: dict, r: str | None) -> dict:
        cv = x.get("base_chat_valid", sum(x["base_chat_attempted"].values()))
        pv = x.get("base_plain_valid", sum(x["base_plain_attempted"].values()))
        cc, pc = sum(x["base_chat_correct"].values()), sum(x["base_plain_correct"].values())
        return {"base_chat_valid": cv, "base_chat_correct": cc, "base_plain_valid": pv, "base_plain_correct": pc,
                "base_pooled_correct": cc + pc, "r_u_count_correct": int(base_pooled(x).get(r, 0)) if r else None,
                "r_u_count_valid": int((x["base_chat_attempted"] + x["base_plain_attempted"]).get(r, 0)) if r else None}

    for e in a2["events"]:
        u = e["unit"]
        x = U[u]
        lc = lc_by_event.get(f"QWEN_NEW_A|{u}", {}).get("landing_counts", {})
        m, k, ld = lead(lc)
        S = [c for c in x["catalogue"] if c != x["default"]]
        events.append({"set": "QWEN_NEW_A", "model": "Qwen3-8B", "unit": u, "name": TASK_NAME[u],
                       "nudge": "escape population (8 fixed directions, alpha 1-2, bf16, ban-free unit)",
                       "S": S, "landing": e["L"], "landing_count": k, "lead": ld, "landing_counts": lc, "r_u": e["r"],
                       "hit": int(bool(e["hit"])), "chance": float(e["chance"]), "K": len(x["catalogue"]),
                       **support_qwen(x, e["r"]), "twin_correct": dict(x["twin_correct"]), "twin_n": x["twin_n"],
                       "twin_valid": dict(x.get("base_chat_attempted") and {} or {}),
                       "src": prov("exp25", "results/a2_assoc_corrected.json", f"events[{u}]")})
    for e in b2["events"]:
        u = e["unit"]
        x = U[u]
        m, k, ld = lead(e["landing_composition"])
        S = [c for c in (x["forecasts"] or {}).get("BASE", {}) if c != "other"]
        events.append({"set": "QWEN_NEW_B", "model": "Qwen3-8B", "unit": u, "name": TASK_NAME[u],
                       "nudge": "escape population (8 fixed directions, alpha 1-2, bf16, ban-free unit)",
                       "S": S, "landing": e["push_landing"], "landing_count": k, "lead": ld,
                       "landing_counts": e["landing_composition"], "r_u": e["r_u"], "hit": int(e["hit"]),
                       "chance": float(e["chance"]), "K": len(x["catalogue"]), **support_qwen(x, e["r_u"]),
                       "twin_correct": dict(x["twin_correct"]), "twin_n": x["twin_n"],
                       "src": prov("exp26", "results/a2_panel.json", f"events[{u}]")})
    for i, e in enumerate(e2["events"]):
        t = e["unit"]
        p = pr[t]
        m, k, ld = lead(e["landing_composition"])
        ch_att = Counter(p["pt_chat"].get("attempt_counts", {}))
        pl_att = Counter(p["pt_plain"].get("attempt_counts", {}))
        valid = lambda c: sum(v for kk, v in c.items() if kk != "invalid")  # noqa: E731
        d = p["default"]["D"]
        events.append({"set": "GEMMA", "model": "gemma-3-4b", "unit": t, "name": TASK_NAME[t],
                       "nudge": "escape population (16 fresh directions, alpha 1-2, bf16)", "S": e["survivors"],
                       "landing": e["landing"], "landing_count": k, "lead": ld, "landing_counts": e["landing_composition"],
                       "r_u": e["r_u"], "hit": int(e["r_u"] == e["landing"]), "chance": float(e2["chance"][i]),
                       "K": e["K_u"], "base_chat_valid": valid(ch_att), "base_chat_correct": p["pt_chat"]["n_correct"],
                       "base_plain_valid": valid(pl_att), "base_plain_correct": p["pt_plain"]["n_correct"],
                       "base_pooled_correct": p["pt_chat"]["n_correct"] + p["pt_plain"]["n_correct"],
                       "r_u_count_correct": int((Counter(p["pt_chat"].get("correct_counts", {})) +
                                                 Counter(p["pt_plain"].get("correct_counts", {}))).get(e["r_u"], 0)),
                       "r_u_count_valid": int((ch_att + pl_att).get(e["r_u"], 0)),
                       "twin_correct": {kk: v for kk, v in p["default"]["correct_counts"].items()},
                       "twin_attempts": {kk: v for kk, v in p["default"].get("attempt_counts", {}).items()},
                       "twin_n": p["default"]["n_twin"], "default": d,
                       "src": prov("exp28", "results/e_a2.json", f"events[{t}]")})
    fp8_l3 = {e["unit"]: e for e in frozen_l3["events"] if e["event"].startswith("QWEN_FP8_SCREEN")}
    for t in ("T03", "T2", "T05", "T10", "T1"):
        v = sc[t]
        x = U[t]
        lc = fp8_l3.get(t, {}).get("landing_counts", {})
        m, k, ld = lead(lc)
        S = [c for c in x["catalogue"] if c != x["default"]]
        events.append({"set": "QWEN_FP8_SCREEN", "model": "Qwen3-8B", "unit": t, "name": TASK_NAME[t],
                       "nudge": "screen + 40 fresh directions (FP8 W8A8, bench unit)", "S": S, "landing": v["push_top1"],
                       "landing_count": k, "lead": ld, "landing_counts": lc, "r_u": v["r_t"], "hit": int(bool(v["agree"])),
                       "chance": 1 / len(S), "K": len(x["catalogue"]), **support_qwen(x, v["r_t"]),
                       "twin_correct": {"(FP8 twin, exp22)": "no correct off-default program (k_off 0)"}, "twin_n": 50,
                       "t_u_override": None,
                       "src": prov("exp24", "results/screen_check.json", f"r_t_vs_push_landing.{t}")})
    for t in ("T10", "T03"):
        x = U[t]
        lc = Counter()
        for c in xa[t]["cells"]:
            if str(c.get("confirmed")) == "True":
                lc.update({kk: int(vv) for kk, vv in parse_dictish(c.get("landing_counts")).items()})
        m, k, ld = lead(dict(lc))
        r = br[t]["r_t"]
        S = [c for c in x["catalogue"] if c != x["default"]]
        events.append({"set": "QWEN_BF16_REMEASURE", "model": "Qwen3-8B", "unit": t, "name": TASK_NAME[t],
                       "nudge": "8 fixed directions, alpha 1-2 (bf16, ban-free unit)", "S": S, "landing": xa[t]["landing"],
                       "landing_count": k, "lead": ld, "landing_counts": dict(lc), "r_u": r,
                       "hit": int(r == xa[t]["landing"]), "chance": 1 / len(S), "K": len(x["catalogue"]),
                       **support_qwen(x, r), "twin_correct": dict(x["twin_bf16_landing_correct"]) or {"(none)": 0},
                       "twin_n": 50, "t_u_override": t_u(Counter(x["twin_bf16_landing_correct"]), x["default"]),
                       "src": prov("exp25", "results/extra_arm_a.json", f"{t}.landing") + "; r_u " +
                       prov("exp24", "results/base_repertoire.json", f"per_task.{t}.r_t")})
    # t_u, twin-wrote-landing, unconfounded flags
    for e in events:
        default = U[e["unit"]]["default"] if e["set"] != "GEMMA" else e["default"]
        if e["set"] == "QWEN_FP8_SCREEN":
            e["t_u"] = None
        elif e["set"] == "QWEN_BF16_REMEASURE":
            e["t_u"] = e["t_u_override"]
        else:
            e["t_u"] = t_u(Counter({k: v for k, v in e["twin_correct"].items() if isinstance(v, int)}), default)
        tw = e["twin_correct"]
        e["TWIN_WROTE_LANDING"] = int(isinstance(tw.get(e["landing"]), int) and tw.get(e["landing"], 0) > 0)
        e["twin_has_correct_nondefault"] = int(e["t_u"] is not None)
        if e["set"] == "GEMMA":
            att = {k: v for k, v in e.get("twin_attempts", {}).items() if k not in ("invalid", default)}
            e["twin_has_valid_nondefault"] = int(sum(att.values()) > 0)
        elif e["set"] in ("QWEN_NEW_A", "QWEN_NEW_B"):
            x = U[e["unit"]]
            if e["set"] == "QWEN_NEW_A":
                pa = next(uu for uu in inp.json("exp25", "pooled_inputs.json")["units"] if uu["unit_id"] == e["unit"])
                tv = pa["twin"].get("comp_valid", {})
            else:
                pb = next(rr for rr in inp.json("exp26", "pooled_inputs.json")["records"] if rr["unit_id"] == e["unit"])
                tv = pb["twin"].get("attempted_composition", {})
            e["twin_has_valid_nondefault"] = int(sum(v for k, v in tv.items() if k not in (x["default"], "invalid", "other")) > 0)
        else:
            e["twin_has_valid_nondefault"] = None
        e["t_u_hit"] = int(e["t_u"] is not None and e["t_u"] == e["landing"])
        e["no_clear_landing"] = int(e["lead"] < 0.15) if not math.isnan(e["lead"]) else None
    write_csv("landing_events_iter5.csv", [{k: v for k, v in e.items() if k not in ("t_u_override",)} for e in events])
    # tallies
    def tally(es: list[dict]) -> dict:
        h = sum(e["hit"] for e in es)
        return {"n": len(es), "hits": h, "chances": [e["chance"] for e in es],
                "expected": float(sum(e["chance"] for e in es)),
                "p_poisson_binomial": poisson_binomial_upper([e["chance"] for e in es], h) if es else None}
    sets = ["QWEN_NEW_A", "QWEN_NEW_B", "GEMMA", "QWEN_FP8_SCREEN", "QWEN_BF16_REMEASURE"]
    tallies = {s: tally([e for e in events if e["set"] == s]) for s in sets}
    tallies["QWEN_NEW_A+B"] = tally([e for e in events if e["set"] in ("QWEN_NEW_A", "QWEN_NEW_B")])
    tallies["ALL21"] = tally(events)
    rec = {"QWEN_NEW_A+B": (6, 7, 0.0027), "GEMMA": (5, 7, 0.025), "QWEN_FP8_SCREEN": (5, 5, None),
           "QWEN_BF16_REMEASURE": (1, 2, None), "ALL21": (17, 21, None)}
    for s, (h, n, p) in rec.items():
        tallies[s]["recorded"] = f"{h}/{n}" + (f" p {p}" if p else "")
        tallies[s]["status"] = "MATCH" if tallies[s]["hits"] == h and tallies[s]["n"] == n and (
            p is None or status(p, tallies[s]["p_poisson_binomial"], 0, "p") == "MATCH") else "CORRECTED"
    # unit-clustered version: one landing per (model, task)
    clusters = defaultdict(list)
    for e in events:
        clusters[(e["model"], e["unit"])].append(e)
    rng = np.random.default_rng(6004)
    cl_obs = sum(int(np.mean([e["hit"] for e in es]) > 0.5) for es in clusters.values())
    sims = np.zeros(100_000)
    for es in clusters.values():
        draws = np.stack([rng.random(100_000) < e["chance"] for e in es], axis=1)
        sims += (draws.mean(axis=1) > 0.5)
    tallies["UNIT_CLUSTERED"] = {"n_clusters": len(clusters), "cluster_hits": cl_obs,
                                 "p_cluster_mc": float((np.sum(sims >= cl_obs) + 1) / (len(sims) + 1)),
                                 "rule": "cluster hit = majority hit over the cluster's events; a tie counts as a miss",
                                 "multi_event_clusters": {f"{k[0]}|{k[1]}": [e["hit"] for e in v] for k, v in clusters.items() if len(v) > 1}}
    write_csv("landing_tally.csv", [{"set": k, **{kk: vv for kk, vv in v.items() if kk != "chances"}} for k, v in tallies.items()])
    # twin-minority rival t_u
    tw_rows = []
    for scope, es in (("ALL21", events), ("QWEN_NEW_A+B", [e for e in events if e["set"] in ("QWEN_NEW_A", "QWEN_NEW_B")]),
                      ("GEMMA", [e for e in events if e["set"] == "GEMMA"])):
        defined = [e for e in es if e["t_u"] is not None]
        disc = [e for e in es if e["t_u"] is not None and e["t_u"] != e["r_u"]]
        r_only = sum(1 for e in disc if e["hit"] and not e["t_u_hit"])
        t_only = sum(1 for e in disc if e["t_u_hit"] and not e["hit"])
        tw_rows.append({"scope": scope, "n_events": len(es), "r_u_hits": sum(e["hit"] for e in es),
                        "t_u_defined": len(defined), "t_u_hits_matched(undefined=miss)": sum(e["t_u_hit"] for e in es),
                        "t_u_hits_defined_only": sum(e["t_u_hit"] for e in defined),
                        "r_u_hits_on_t_u_defined": sum(e["hit"] for e in defined),
                        "discordant_pairs(r_u!=t_u)": len(disc), "r_u_only_hits": r_only, "t_u_only_hits": t_only,
                        "sign_test_p_two_sided": mcnemar_exact(r_only, t_only)})
    write_csv("twin_rival.csv", tw_rows)
    # unconfounded subset
    unc = {}
    for scope, sel in (("QWEN_NEW_A+B", ("QWEN_NEW_A", "QWEN_NEW_B")), ("GEMMA", ("GEMMA",))):
        es = [e for e in events if e["set"] in sel and not e["twin_has_correct_nondefault"]]
        es_v = [e for e in events if e["set"] in sel and not e.get("twin_has_valid_nondefault")]
        unc[scope] = {**tally(es), "units": [e["unit"] for e in es],
                      "sensitivity_no_valid_nondefault": {**tally(es_v), "units": [e["unit"] for e in es_v]}}
    pooled = [e for e in events if e["set"] in ("QWEN_NEW_A", "QWEN_NEW_B", "GEMMA") and not e["twin_has_correct_nondefault"]]
    unc["POOLED"] = {**tally(pooled), "units": [f"{e['set']}|{e['unit']}" for e in pooled]}
    rec_u = {"QWEN_NEW_A+B": (3, 4, 0.052), "GEMMA": (2, 4, 0.42), "POOLED": (5, 8, 0.053)}
    for s, (h, n, p) in rec_u.items():
        unc[s]["recorded"] = f"{h}/{n} p {p}"
        unc[s]["status"] = "MATCH" if (unc[s]["hits"], unc[s]["n"]) == (h, n) and abs(unc[s]["p_poisson_binomial"] - p) <= 0.1 * p + 0.0015 else "CORRECTED"
    # mixed twins
    mixed = []
    for u in PANEL:
        x = U[u]
        tm, tk, tn = twin_modal(x)
        dshare = x["twin_correct"].get(x["default"], 0) / x["twin_n"]
        mixed.append({"unit": u, "name": TASK_NAME[u], "default": x["default"], "twin_default_share_of_N": dshare,
                      "twin_off_default_correct_share_of_N": sum(v for k, v in x["twin_correct"].items() if k != x["default"]) / x["twin_n"],
                      "twin_composition": dict(x["twin_correct"]), "beta_iter5": x["beta_committed"], "beta_v6": beta_v6(x),
                      "E_u": x["E"], "mixed_twin(default share < 0.9)": int(dshare < 0.9)})
    write_csv("mixed_twins.csv", mixed)
    support = [{k: e[k] for k in ("set", "unit", "name", "r_u", "base_chat_valid", "base_chat_correct", "base_plain_valid",
                                  "base_plain_correct", "base_pooled_correct", "r_u_count_correct", "r_u_count_valid")}
               for e in events]
    write_csv("base_support.csv", support)
    kth_note = inp.json("exp27", "results/cells.json")["T03|PN_a2"]["correct_composition"]
    return {"events": events, "tallies": tallies, "twin_rival": tw_rows, "unconfounded": unc, "mixed": mixed,
            "support": support, "kth_pn_note": {"exp27_T03_PN_a2_correct_composition": kth_note,
                                                "src": prov("exp27", "results/cells.json", "T03|PN_a2.correct_composition")}}


# ============================================================================================= 0c MOVABILITY
def _spearman_rows(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    rx = stats.rankdata(x, axis=1)
    ry = stats.rankdata(y, axis=1)
    rx = rx - rx.mean(axis=1, keepdims=True)
    ry = ry - ry.mean(axis=1, keepdims=True)
    den = np.sqrt((rx ** 2).sum(axis=1) * (ry ** 2).sum(axis=1))
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, (rx * ry).sum(axis=1) / den, 0.0)


def power_sim(beta_obs: np.ndarray, E_obs: np.ndarray, rhos: list[float], ns: list[int], n_sim: int,
              generators: tuple[str, ...], seed: int) -> list[dict]:
    rng = np.random.default_rng(seed)
    bq = np.sort(beta_obs)
    eq = np.sort(E_obs)

    def draw(gen: str, rho: float, n: int, m: int) -> tuple[np.ndarray, np.ndarray]:
        r = 2 * math.sin(math.pi * rho / 6)
        z1 = rng.standard_normal((m, n))
        z2 = r * z1 + math.sqrt(max(1 - r * r, 0)) * rng.standard_normal((m, n))
        if gen == "a":
            return z1, z2
        u1, u2 = stats.norm.cdf(z1), stats.norm.cdf(z2)
        x = bq[np.minimum((u1 * len(bq)).astype(int), len(bq) - 1)]
        y = eq[np.minimum((u2 * len(eq)).astype(int), len(eq) - 1)]
        return x, y

    rows = []
    for gen in generators:
        for n in ns:
            x0, y0 = draw(gen, 0.0, n, 20_000)
            null = _spearman_rows(x0, y0)
            crit = float(np.quantile(null, 0.95, method="higher"))
            size = float(np.mean(null >= crit))
            for rho in rhos:
                x, y = draw(gen, rho, n, n_sim)
                rs = _spearman_rows(x, y)
                rows.append({"generator": gen, "n": n, "rho": rho, "power": float(np.mean(rs >= crit)),
                             "crit_rho_0.05": crit, "null_size": size, "n_sim": n_sim})
    return rows


def r4_from_rows(inp: Inputs, U: dict) -> dict[str, dict]:
    """R4 = correct catalogue off-default share under the novelty instruction minus the twin's, from the labelled rows
    of both panels (panel A arm NOVELTY, N 30; panel B arm NOV, slots 0-29; twin arm TWIN)."""
    cnt: dict[tuple, list[int]] = defaultdict(lambda: [0, 0])
    for key, rel, nov_arms in (("exp25", "data/samples.jsonl", ("NOVELTY",)), ("exp26", "data/samples.jsonl", ("NOV",))):
        for r in inp.jsonl(key, rel):
            u = r.get("unit")
            if u not in U or u not in PANEL:
                continue
            arm = r.get("arm")
            if arm in nov_arms and (key == "exp25" or int(r.get("slot", 0)) < 30):
                a = "NOV"
            elif arm == "TWIN":
                a = "TWIN"
            else:
                continue
            x = U[u]
            ok = r.get("passed") in (True, "True") and r.get("label") in x["catalogue"] and r.get("label") != x["default"]
            cnt[(u, a)][0] += int(ok)
            cnt[(u, a)][1] += 1
    out = {}
    for u in PANEL:
        nv, tw = cnt.get((u, "NOV"), [0, 0]), cnt.get((u, "TWIN"), [0, 0])
        out[u] = {"nov_k": nv[0], "nov_n": nv[1], "twin_k": tw[0], "twin_n": tw[1],
                  "R4": (nv[0] / nv[1] - tw[0] / tw[1]) if nv[1] and tw[1] else None}
    return out


def movability(inp: Inputs, U: dict, frozen_m: dict, frozen_f2: dict) -> dict[str, Any]:
    out: dict[str, Any] = {}
    ci_rows = []
    for label, us in (("primary13", PRIMARY13), ("with_A8_A9_15", PANEL)):
        for bname in ("beta_iter5_committed", "beta_v6"):
            xs = np.array([frozen_m["units"][u][bname] for u in us], float)
            es = np.array([U[u]["E"] for u in us], float)
            r = spearman(xs, es)
            p = spearman_perm_p(xs, es, 200_000, 6005)
            bw, fi = bonett_wright_ci(r, len(us)), fieller_ci(r, len(us))
            bs = bootstrap_spearman(xs, es, 10_000, 6006)
            rec = {"primary13": 0.146, "with_A8_A9_15": 0.006}[label] if bname == "beta_iter5_committed" else None
            rec_p = {"primary13": 0.315, "with_A8_A9_15": 0.492}[label] if bname == "beta_iter5_committed" else None
            ci_rows.append({"units": label, "n": len(us), "beta": bname, "rho": r, "rho_recorded": rec,
                            "rho_status": status(rec, r, 0.005), "p_one_sided_perm_200k": p, "p_recorded": rec_p,
                            "p_status": status(rec_p, p, 0, "p") if rec_p else "NEW",
                            "bonett_wright_95": bw, "fieller_95": fi, "boot_pct_95": bs["pct"], "boot_bca_95": bs["bca"],
                            "boot_share_dropped_constant": bs["share_dropped"], "boot_n": bs["n_boot"]})
    write_csv("movability_ci.csv", ci_rows)
    out["ci"] = ci_rows
    # power (generator a: bivariate normal; b: Gaussian copula onto the observed 15-unit marginals)
    xs15 = np.array([frozen_m["units"][u]["beta_iter5_committed"] for u in PANEL], float)
    es15 = np.array([U[u]["E"] for u in PANEL], float)
    pw = power_sim(xs15, es15, [0.3, 0.5, 0.6], [6, 7, 13, 15, 20, 30], 10_000, ("a", "b"), 6007)
    ext = power_sim(xs15, es15, [0.5], [40, 50, 60, 70, 80, 100], 10_000, ("b",), 6008)
    pw_all = pw + ext
    n_req = None
    for nn in sorted({r["n"] for r in pw_all if r["generator"] == "b" and r["rho"] == 0.5}):
        rr = next(r for r in pw_all if r["generator"] == "b" and r["rho"] == 0.5 and r["n"] == nn)
        if rr["power"] >= 0.8:
            n_req = nn
            break
    write_csv("power_sim.csv", pw_all)
    out["power"] = {"rows": pw_all, "n_required_power0.8_rho0.5_copula": n_req,
                    "readme_statement_panel_A": "about 0.46 at rho 0.6 (n 6-8, one-sided 0.05)"}
    # harmonised rivals on the new units
    f2u = frozen_f2["units"]
    pa = {uu["unit_id"]: uu for uu in inp.json("exp25", "pooled_inputs.json")["units"]}
    pb = {rr["unit_id"]: rr for rr in inp.json("exp26", "pooled_inputs.json")["records"]}
    r4_raw = r4_from_rows(inp, U)

    def r4(u: str) -> float | None:
        return r4_raw[u]["R4"]
    riv = {"R1_margin": (-1, lambda u: f2u[u]["harmonised_m"]), "R4_novelty_excess": (1, r4),
           "R6_runtime_merit": (1, lambda u: frozen_m["units"][u]["runtime_merit"]),
           "R7_twin_modal_share": (-1, lambda u: frozen_m["units"][u]["twin_modal_share_correct"]),
           "K": (1, lambda u: frozen_m["units"][u]["K"])}
    old = {"R6_runtime_merit": "panel A merit rho -0.88 (orientation: larger runner-up/default time = less movable); "
                               "panel B merit runtime 0.54, length 0.58",
           "R7_twin_modal_share": "panel A -0.70; panel B R_modal 0.11", "R1_margin": "panel B R_margin 0.21",
           "R4_novelty_excess": "panel A novelty_excess (share minus twin); panel B R_novel -0.03 (no twin subtraction): "
                                "two definitions, recomputed here from rows with one", "K": "panel A catalogue size 0.07"}
    rv_rows, cmp_rows = [], []
    rng = np.random.default_rng(6009)
    for label, us in (("primary13", PRIMARY13), ("with_A8_A9_15", PANEL)):
        beta = np.array([frozen_m["units"][u]["beta_iter5_committed"] for u in us], float)
        E = np.array([U[u]["E"] for u in us], float)
        pvals = {}
        for name, (s, fn) in riv.items():
            v = np.array([fn(u) if fn(u) is not None else np.nan for u in us], float)
            ok = ~np.isnan(v)
            r = spearman(v[ok], E[ok])
            p = spearman_perm_p(s * v[ok], E[ok], 100_000, 6010) if not math.isnan(r) else float("nan")
            pvals[name] = p
            deltas = []
            n = len(us)
            for _ in range(10_000):
                idx = rng.integers(0, n, n)
                idx = idx[ok[idx]]
                if len(idx) < 4 or np.ptp(E[idx]) == 0 or np.ptp(v[idx]) == 0 or np.ptp(beta[idx]) == 0:
                    continue
                deltas.append(s * spearman(v[idx], E[idx]) - spearman(beta[idx], E[idx]))
            deltas = np.array(deltas)
            rv_rows.append({"units": label, "rival": name, "sign": s, "n": int(ok.sum()), "rho": r, "oriented_rho": s * r,
                            "p_one_sided_perm": p, "old_panel_values": old[name]})
            cmp_rows.append({"units": label, "rival": name, "delta_oriented_rival_minus_beta": s * r - spearman(beta[ok], E[ok]),
                             "boot_pct95": [float(np.quantile(deltas, 0.025)), float(np.quantile(deltas, 0.975))] if len(deltas) else None,
                             "n_boot_kept": len(deltas)})
        order = sorted(pvals, key=lambda k: pvals[k])
        m = len(order)
        holm, run = {}, 0.0
        for i, k in enumerate(order):
            run = max(run, min(1.0, (m - i) * pvals[k]))
            holm[k] = run
        for r_ in rv_rows:
            if r_["units"] == label:
                r_["p_holm_descriptive"] = holm[r_["rival"]]
    write_csv("rivals_harmonised.csv", rv_rows)
    write_csv("rival_comparison.csv", cmp_rows)
    out["rivals"] = rv_rows
    out["rival_comparison"] = cmp_rows
    out["r4_rows"] = r4_raw
    write_csv("r4_novelty_excess.csv", [{"unit": u, **v_} for u, v_ in r4_raw.items()])
    # re-timed merit beside old values
    rt = []
    for u in EXISTING + PANEL:
        d = frozen_m["units"][u]["runtime_merit_detail"]
        oldv = (pa[u]["rivals"].get("merit_runtime_min") if u in PANEL_A else
                pb[u]["rivals"].get("R_merit_runtime") if u in PANEL_B else None)
        rt.append({"unit": u, "name": TASK_NAME[u], "default": d["default"], "merit_log2_default_over_fastest_alt": d.get("merit"),
                   "fastest_alt": d.get("fastest_alt"), "t_default_s": d.get("t_default"), "t_fastest_alt_s": d.get("t_fastest_alt"),
                   "unstable": d.get("unstable"), "K_passing": d["K_passing"], "old_panel_value": oldv,
                   "old_definition": ("panel A merit_runtime_min" if u in PANEL_A else "panel B R_merit_runtime = -ln(t_fastest/t_default) on summed ref_times"
                                      if u in PANEL_B else "eval4 R6 ratio (other harness)")})
    out["retimed"] = rt
    return out


def retimed_table(retime: dict, frozen_m: dict, unit_rows: list[dict]) -> None:
    rows = []
    for r in retime["rows"]:
        if not r:
            continue
        rows.append({"unit": r["unit"], "ref": r["ref"], "mode": r["mode"], "passes_all": r.get("passes_all"),
                     "t_median_s": r.get("t_median"), "t_iqr_s": r.get("t_iqr"), "cv": r.get("cv"),
                     "n_repeats": r.get("n_repeats"), "unstable": r.get("unstable"), "n_stress": r.get("n_stress"),
                     "src": r.get("src")})
    old = {r["unit"]: r for r in unit_rows}
    for u, v in frozen_m["units"].items():
        d = v["runtime_merit_detail"]
        rows.append({"unit": u, "ref": "(unit merit)", "mode": f"default {d['default']} vs {d.get('fastest_alt')}",
                     "passes_all": None, "merit_log2_default_over_fastest_alt": d.get("merit"),
                     "unstable": d.get("unstable"), "old_panel_value": old.get(u, {}).get("old_panel_value"),
                     "old_definition": old.get(u, {}).get("old_definition"), "src": "frozen/m_candidates.json"})
    write_csv("rivals_retimed.csv", rows)


# ============================================================================================= 0d / 0e
def rarefied_hill(comp: dict, depth: int, n_sub: int, seed: int) -> tuple[float | None, int, bool]:
    labels = [k for k, v in comp.items() for _ in range(int(v))]
    n = len(labels)
    if n == 0:
        return None, 0, True
    d = min(depth, n)
    rng = np.random.default_rng(seed)
    arr = np.array(labels)
    hs = []
    for _ in range(n_sub):
        s = rng.choice(arr, size=d, replace=False)
        _, c = np.unique(s, return_counts=True)
        p = c / c.sum()
        hs.append(float(np.exp(-(p * np.log(p)).sum())))
    return float(np.mean(hs)), d, n < depth


def missing_outputs(inp: Inputs, U: dict) -> dict[str, Any]:
    out: dict[str, Any] = {}
    L = inp.json("exp27", "results/literal_cell.json")["per_T"]
    rec = {"LIT_T0.3": (2, 4, 8), "LIT_T0.7": (3, 3, 10), "LIT_T1.0": (2, 3, 9), "LIT_T1.3": (5, 7, 12), "LIT_REP_T0.7": (3, 6, 10)}
    ph = []
    for k, r in rec.items():
        p = L[k]["phrasing"]
        vals = [p[f"theta_{th}"] if not isinstance(p[f"theta_{th}"], dict) else p[f"theta_{th}"]["n_clusters"] for th in ("0.7", "0.8", "0.9")]
        ph.append({"cell": k, "theta_0.7": vals[0], "theta_0.8": vals[1], "theta_0.9": vals[2], "recorded": list(r),
                   "status": "MATCH" if tuple(vals) == r else "CORRECTED",
                   "src": prov("exp27", "results/literal_cell.json", f"per_T.{k}.phrasing")})
    t07, rep = ph[1], ph[4]
    ph.append({"cell": "noise floor |T0.7 - repeat|", **{f"theta_{th}": abs(t07[f"theta_{th}"] - rep[f"theta_{th}"]) for th in ("0.7", "0.8", "0.9")},
               "recorded": None, "status": "NEW", "src": "computed"})
    write_csv("t206_phrasing.csv", ph)
    out["phrasing"] = ph
    P = inp.json("exp27", "results/prices.json")
    B = inp.json("exp27", "results/bootstrap.json")
    knobs = ["PN", "IFG", "PSL", "EAP", "BINT"]
    pr_rows = []
    rec207 = {"T03": 1.98, "T10": 1.09, "T2": 1.18, "T05": 1.17, "T1": 1.06}
    for t in DECISIVE + ND10:
        if t not in P:
            continue
        row = {"task": t, "name": TASK_NAME[t], "set": "decisive" if t in DECISIVE else "ND10"}
        for k in knobs:
            v = P[t].get(k)
            if not v:
                row.update({f"{k}_H5": None, f"{k}_P15": None, f"{k}_P20": None})
                continue
            reps = B.get(t, [])
            def q(key: str) -> Any:
                xs = [r.get(key) for r in reps if isinstance(r, dict)]
                reached = [x for x in xs if x is not None]
                if not xs:
                    return None
                return {"share_reached": len(reached) / len(xs),
                        "ci95": [float(np.quantile(reached, 0.025)), float(np.quantile(reached, 0.975))] if reached else None}
            row.update({f"{k}_H5": v.get("H5"), f"{k}_P15": v.get("P15"), f"{k}_P20": v.get("P20"),
                        f"{k}_P15_boot": q(f"{k}_P15"), f"{k}_P20_boot": q(f"{k}_P20")})
        if t in rec207:
            row["PN_H5_recorded_T207"] = rec207[t]
            row["PN_H5_status"] = status(rec207[t], row.get("PN_H5"), 0.005)
        row["src"] = prov("exp27", "results/prices.json", f"{t}") + "; " + prov("exp27", "results/bootstrap.json", t)
        pr_rows.append(row)
    write_csv("t207_t208_prices.csv", pr_rows)
    out["prices"] = pr_rows
    uo = inp.json("exp26", "results/unit_outcomes.json")
    knob = []
    for u in PANEL_B:
        rec_u = uo.get(u) if isinstance(uo, dict) else None
        o = U[u]["outcomes"]
        cellsrc = {"twin": o.get("twin_cell"), "PN_a1": o.get("pn_cells", {}).get("1.0"),
                   "PN_a2": o.get("pn_cells", {}).get("2.0"), "T1.3": o.get("t13_cell")}
        for arm, c in cellsrc.items():
            if not c:
                continue
            comp = c.get("labels_correct", {})
            h, depth, flag = rarefied_hill(comp, 25, 1000, 6011)
            knob.append({"unit": u, "name": TASK_NAME[u], "arm": arm, "N": c.get("n_rows"), "pass": c.get("pass"),
                         "off_default_share": c.get("share"), "n_correct": c.get("n_correct"), "correct_composition": comp,
                         "hill1_rarefied": h, "depth": depth, "flag_below_25": flag,
                         "src": prov("exp26", "pooled_inputs.json", f"records[{u}].outcomes.{arm}")})
    write_csv("panelB_knob_rows.csv", knob)
    out["panelB_knob"] = knob
    out["panelB_unit_outcomes_keys"] = list(uo.keys())[:10] if isinstance(uo, dict) else None
    rc = inp.json("exp26", "results/repertoire_check.json")
    out["repertoire_check"] = rc
    # Table 126c from eval3 knob_table.csv rows K0522-K0524 (file lines 524-526)
    lines = inp.text("eval3", "tables/knob_table.csv").splitlines()
    rdr = list(csv.DictReader(lines))
    t126 = []
    want = {"K0522": (2.87, -12), "K0523": (2.96, -27), "K0524": (2.92, -15)}
    for r in rdr:
        if r["row_id"] in want:
            h = float(r["H1r25"])
            t126.append({"row_id": r["row_id"], "arm": r["arm"], "task": r["task"], "model": r["model"], "n": r["n"],
                         "n_correct": r["n_correct"], "pass_rate": r["pass_rate"], "ref_pass": r["ref_pass"],
                         "pass_cost_pts": float(r["pass_cost_pts"]), "pass_cost_ci95": r["pass_cost_ci95"],
                         "H1r25": h, "H1r25_ci90": r["H1r25_ci90"], "ci_unit": r["ci_unit"], "flags": r["flags"],
                         "qualify": r["qualify"], "recorded_hill": want[r["row_id"]][0],
                         "status": status(want[r["row_id"]][0], h, 0.005),
                         "src": prov("eval3", "tables/knob_table.csv", r["row_id"])})
    write_csv("t126c.csv", t126)
    out["t126c"] = t126
    return out


def minor(inp: Inputs) -> dict[str, Any]:
    D = inp.json("exp27", "results/pn_vs_dmd.json")
    rows = []
    for t in DECISIVE:
        for a in ("alpha1", "alpha2"):
            m = D["per_task"][t][a]["mcnemar_PN_vs_DMD"]
            rows.append({"task": t, "name": TASK_NAME[t], "alpha": a, "PN_only": m["x_only"], "DMD_only": m["y_only"],
                         "p_exact_recomputed": mcnemar_exact(m["x_only"], m["y_only"]), "p_recorded": m["p_exact"],
                         "src": prov("exp27", "results/pn_vs_dmd.json", f"per_task.{t}.{a}.mcnemar_PN_vs_DMD")})
    for a, key in (("alpha1", "1"), ("alpha2", "2")):
        b = sum(r["PN_only"] for r in rows if r["alpha"] == a)
        c = sum(r["DMD_only"] for r in rows if r["alpha"] == a)
        b4 = sum(r["PN_only"] for r in rows if r["alpha"] == a and r["task"] != "T03")
        c4 = sum(r["DMD_only"] for r in rows if r["alpha"] == a and r["task"] != "T03")
        rows.append({"task": "POOLED_D5", "alpha": a, "PN_only": b, "DMD_only": c, "p_exact_recomputed": mcnemar_exact(b, c),
                     "p_recorded": D["pooled_D5_exact"][key]["p_exact"], "src": prov("exp27", "results/pn_vs_dmd.json", f"pooled_D5_exact.{key}")})
        rows.append({"task": "POOLED_without_T03", "alpha": a, "PN_only": b4, "DMD_only": c4,
                     "p_exact_recomputed": mcnemar_exact(b4, c4), "p_recorded": None, "src": "computed"})
    write_csv("t211_pn_vs_dmd.csv", rows)
    e2 = inp.json("exp28", "results/e_a2.json")
    diffs = [r["q_base"] - r["q_assoc"] for r in e2["log_scores"]]
    dd = [r["q_base"] - r["q_assoc"] for r in e2["log_scores"] if r["q_assoc_defined"]]
    g = [{"scope": "all 7 (undefined association scored as uniform)", "n": len(diffs), "mean": float(np.mean(diffs)),
          "wilcoxon_exact_p_one_sided": wilcoxon_exact(diffs), "recorded_mean": 1.50, "recorded_p": 0.023,
          "status": status(1.50, float(np.mean(diffs)), 0.01) if abs(wilcoxon_exact(diffs) - 0.023) < 0.003 else "CORRECTED"},
         {"scope": "defined association only", "n": len(dd), "mean": float(np.mean(dd)),
          "wilcoxon_exact_p_one_sided": wilcoxon_exact(dd), "recorded_mean": 1.57, "recorded_p": None,
          "status": status(1.57, float(np.mean(dd)), 0.01)},
         {"scope": "undefined events", "units": [r["unit"] for r in e2["log_scores"] if not r["q_assoc_defined"]]}]
    write_csv("gemma_fill.csv", g)
    return {"t211": rows, "gemma_fill": g}


# ============================================================================================= run
def run(inp: Inputs) -> None:
    chain = verify_chain()
    logger.info(f"commit chain verified ({len(chain)} links); S3 may write")
    frozen = {n: json.loads((WS / "frozen" / n).read_text()) for n in
              ("m_candidates.json", "e_inputs.json", "l3_screen.json", "f2_screen.json")}
    U = load_units(inp)
    retime = json.loads((WS / "retime" / "raw_times.json").read_text())
    res: dict[str, Any] = {"chain": chain}
    logger.info("0a engine")
    res["0a"] = engine(inp, U)
    logger.info("0b landing")
    res["0b"] = landing(inp, U, frozen["l3_screen.json"])
    logger.info("0c movability (bootstrap, permutations and power simulation)")
    res["0c"] = movability(inp, U, frozen["m_candidates.json"], frozen["f2_screen.json"])
    retimed_table(retime, frozen["m_candidates.json"], res["0c"]["retimed"])
    logger.info("0d missing outputs")
    res["0d"] = missing_outputs(inp, U)
    logger.info("0e minor items")
    res["0e"] = minor(inp)
    # screen tables from the frozen files (copies for readers)
    m = frozen["m_candidates.json"]
    write_csv("m_candidates_screen.csv", [{"unit": u, **{k: v[k] for k in ("set", "default", "beta_v6", "beta_iter5_committed",
               "replacement_class", "runtime_merit", "twin_modal_share_correct", "K", "LOW_SUPPORT", "E_u")}} for u, v in m["units"].items()]
              + [{"unit": f"RANK:{s}:{c}", **v} for s, d in m["screen_ranking"].items() for c, v in d.items()])
    write_csv("l3_screen.csv", [{k: e.get(k) for k in ("event", "S", "n_landing_programs", "gamma_median", "heldout_logscore",
                                                     "kendall_tau_b_base_vs_tail", "assoc_defined", "status")} for e in frozen["l3_screen.json"]["events"]])
    write_csv("f2_screen.csv", [{"unit": u, **v} for u, v in frozen["f2_screen.json"]["units"].items()])
    write_json(RES / "s3_analyses.json", res)
    logger.info("S3 analyses written: results/s3_analyses.json and tables/*.csv")
