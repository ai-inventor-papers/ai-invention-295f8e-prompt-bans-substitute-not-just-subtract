#!/usr/bin/env python3
"""S3 recompute + S6 COMMIT #1 (CPU; before the first new push row).

Per unit: D_u at N 300 (stability vs exp28's N 50), twin pass at T 1.0 (N 200), twin correct off-default share at
T 1.0 (the push stage-1 reference); q_base / r_u / flags (LOW_CORRECT, THIN_RU, TIE, AUDIT_FAIL, source-sensitive) with
per-source r_u (exp28 chat, exp28 plain, exp28 pooled, few-shot, F_bench, F_he, stage-A-only); q_tail / t_u /
TAIL-EMPTY; q_lik (norm, raw) / top-1 / THIN_QLIK / fork margin m_u; DISCORDANT and TAIL-DISCORDANT; exp28 q_assoc.
Also the 7 iteration-5 events rescored (exp28 r_u vs repaired r_u, CHANGED flags, new rivals' top-1s), the push plan
and a grep audit of every fed prompt. Usage: python src/forecasts6.py draft | commit1
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (ALL_TASKS, ALPHA6, DATA_DIR, DIR_SEEDS6, E28_DATA, E28_PRED, E28_RESULTS, FD6_CONFIRM_SLOTS,
                 FD6_STAGE1_SLOTS, NS_PN, PN6_SLOTS, PRED_DIR, PUSH_TASKS6, RESULTS_DIR, read_json, read_jsonl,
                 setup_logging, write_json)
import analysis_L as AL
import commit as C
import prompts as PG
import prompts6 as P6
from audit6 import all_labels, pt_rows, twin300


def per_source_ru(pr: list[dict[str, Any]], D: str | None, cat: list[str]) -> dict[str, Any]:
    srcs = {"exp28_chat": [r for r in pr if r["stage"] == "ptchat"],
            "exp28_plain": [r for r in pr if r["stage"] == "ptplain"],
            "exp28_pooled": [r for r in pr if r["stage"] in ("ptchat", "ptplain")],
            "fewshot": [r for r in pr if r["stage"] == "ptfs6"],
            "F_bench": [r for r in pr if r["stage"] == "ptfs6" and r.get("family") == "F_bench"],
            "F_he": [r for r in pr if r["stage"] == "ptfs6" and r.get("family") == "F_he"],
            "stageA_plus_exp28": [r for r in pr if r["stage"] in ("ptchat", "ptplain")
                                  or (r["stage"] == "ptfs6" and r.get("ptfs_stage") == "A")]}
    out = {}
    for k, rr in srcs.items():
        bf = AL.base_forecast(rr, D, cat)
        out[k] = {"r_u": bf["r_u"], "n_rows": bf["n_rows"], "n_correct": bf["n_correct"], "n_valid": bf["n_valid"],
                  "LOW_CORRECT": bf["LOW_CORRECT"], "correct_counts": bf["correct_counts"],
                  "valid_counts": bf["valid_counts"]}
    return out


def unit_table(labs: dict[str, dict[str, Any]], qlik: dict[str, Any] | None, audit: dict[str, Any] | None,
               assoc: dict[str, dict[str, float]]) -> dict[str, Any]:
    units = {}
    for t in ALL_TASKS:
        cat = P6.catalogue(t)
        tw = twin300(labs, t)
        tw10 = [r for r in tw if abs(float(r.get("temperature") or 1.0) - 1.0) < 1e-9]
        d300 = AL.default_rule(tw, cat)
        d50 = AL.default_rule([r for r in tw if r.get("stage") == "twin"], cat)
        D = d300["D"]
        nd = AL.nondef_of(cat, D)
        pr = pt_rows(labs, t)
        bf = AL.base_forecast(pr, D, cat)
        ps = per_source_ru(pr, D, cat)
        tail = AL.tail_forecast(tw, D, cat)
        lik = lik_raw = None
        m_u = None
        thin_q = {}
        if qlik is not None and t in qlik.get("own", {}):
            sc = qlik["own"][t]
            lik = AL.lik_forecast(sc, nd, "norm")
            lik_raw = AL.lik_forecast(sc, nd, "raw")
            thin_q = {m: v.get("n_programs", 0) < 3 for m, v in sc.items()}
            if D in sc and bf["r_u"] in sc:
                m_u = sc[D]["raw"] - sc[bf["r_u"]]["raw"]
        audit_fail = bool(audit and t in audit.get("AUDIT_FAIL", []))
        ru_src = {k: v["r_u"] for k, v in ps.items() if v["n_rows"] > 0}
        fam_sens = (ps["F_bench"]["r_u"] != ps["F_he"]["r_u"]) if (ps["F_bench"]["n_rows"] and ps["F_he"]["n_rows"]) else None
        u = {"task": t, "catalogue": cat, "K": len(cat), "D": D, "default": d300, "D_exp28_N50": d50["D"],
             "D_changed_vs_exp28": d50["D"] != D, "nondef": nd,
             "twin_n": len(tw), "twin_n_T10": len(tw10), "twin_pass_T10": AL.pass_rate(tw10),
             "twin_off_corr_T10": (sum(1 for r in tw10 if AL.is_correct(r) and r["label"] in nd) / len(tw10))
             if tw10 else None,
             "q_base": bf["q"], "r_u": bf["r_u"], "base": {k: v for k, v in bf.items() if k != "q"},
             "r_u_by_source": ru_src, "base_by_source": ps, "exemplar_sensitive": fam_sens,
             "source_sensitive": len({v for v in ru_src.values() if v is not None}) > 1,
             "AUDIT_FAIL": audit_fail, "q_tail": tail["q"], "t_u": tail["t_u"], "TAIL_EMPTY": tail["TAIL_EMPTY"],
             "tail": {k: v for k, v in tail.items() if k != "q"},
             "q_lik": lik["q"] if lik else None, "qlik_top1": lik["top1"] if lik else None,
             "qlik_defined": bool(lik and lik["defined"]), "q_lik_raw": lik_raw["q"] if lik_raw else None,
             "qlik_top1_raw": lik_raw["top1"] if lik_raw else None,
             "qlik_scores": qlik["own"].get(t) if qlik else None, "THIN_QLIK": thin_q, "fork_margin_raw": m_u,
             "q_assoc": assoc.get(t)}
        u["DISCORDANT"] = bool(u["r_u"] is not None and u["qlik_top1"] is not None and u["r_u"] != u["qlik_top1"])
        u["TAIL_DISCORDANT"] = bool(u["r_u"] is not None and u["t_u"] is not None and u["r_u"] != u["t_u"])
        units[t] = u
    return units


def assoc_table() -> dict[str, dict[str, float]]:
    e = read_json(E28_RESULTS / "e_a2.json")
    return {ev["unit"]: ev["q_assoc"] for ev in e.get("events", []) if ev.get("q_assoc")}


def old_events(units: dict[str, Any]) -> dict[str, Any]:
    e = read_json(E28_RESULTS / "e_a2.json")
    pred = read_json(E28_PRED / "commit_E1.json")["units"]
    twin28 = collections.defaultdict(list)
    for r in read_jsonl(E28_DATA / "labels.jsonl"):
        if r.get("stage") == "twin":
            twin28[r["task"]].append(r)
    rows = []
    for ev in e["events"]:
        t = ev["unit"]
        u = units[t]
        D28 = pred[t]["D"]
        silent = not any(AL.is_correct(r) and r["label"] != D28 and r["label"] in u["catalogue"] for r in twin28[t])
        rows.append({"unit": t, "landing_exp28": ev["landing"], "landing_composition": ev["landing_composition"],
                     "K_u": ev["K_u"], "r_u_exp28": ev["r_u"], "r_u_repaired": u["r_u"],
                     "CHANGED": ev["r_u"] != u["r_u"], "t_u": u["t_u"], "qlik_top1": u["qlik_top1"],
                     "D_exp28": D28, "D_N300": u["D"], "D_changed": D28 != u["D"], "twin_silent_exp28_N50": silent,
                     "hit_exp28": ev["r_u"] == ev["landing"], "hit_repaired": u["r_u"] == ev["landing"],
                     "hit_tail": u["t_u"] == ev["landing"], "hit_qlik": u["qlik_top1"] == ev["landing"]})
    return {"events": rows, "n": len(rows), "n_changed": sum(r["CHANGED"] for r in rows)}


def push_plan(units: dict[str, Any]) -> dict[str, Any]:
    return {"task_order": list(PUSH_TASKS6), "direction_seeds": list(DIR_SEEDS6), "alpha": ALPHA6,
            "fd_stage1_slots": list(FD6_STAGE1_SLOTS), "fd_confirm_slots": list(FD6_CONFIRM_SLOTS),
            "pn_namespace": NS_PN, "pn_slots": list(PN6_SLOTS),
            "stage1_rule": "catalogue off-default CORRECT share >= twin T1.0 share + 0.20 AND pass >= 0.8 x twin T1.0",
            "confirm_rule": "pooled N 30 keeps both + one-sided exact binomial p < 0.05 vs twin off-default rate (floor 0.01)",
            "committed_prediction": {t: {"modal_landing": units[t]["r_u"], "D": units[t]["D"]} for t in PUSH_TASKS6},
            "event_definition": "v6 (see protocol_G6.json)"}


def qlik_sanity(units: dict[str, Any], qlik: dict[str, Any]) -> dict[str, Any]:
    """Confirmation signal 5: q_lik should rank the default first among ALL catalogue algorithms on >= 10 of 15 units;
    per-template spread of the norm score (target < ~1 nat/token)."""
    rows = {}
    for t, u in units.items():
        sc = qlik.get("own", {}).get(t, {})
        allm = {m: v["norm"] for m, v in sc.items() if v.get("n_programs", 0) > 0}
        if not allm or u["D"] is None:
            rows[t] = {"default_rank": None}
            continue
        order = sorted(allm, key=lambda m: -allm[m])
        rows[t] = {"default_rank": order.index(u["D"]) + 1 if u["D"] in order else None, "order": order,
                   "max_template_range_norm": max(v.get("template_range_norm", 0.0) for v in sc.values())}
    n1 = sum(1 for v in rows.values() if v.get("default_rank") == 1)
    return {"per_unit": rows, "n_default_first": n1, "pass": n1 >= 10}


def grep_all() -> dict[str, Any]:
    reg = read_jsonl(DATA_DIR / "prompts_fed.jsonl")
    g = PG.grep_audit([(r["kind"], r["text"]) for r in reg], list(ALL_TASKS))
    return {**g, "n_registered_prompts": len(reg)}


@logger.catch(reraise=True)
def main() -> None:
    cmd = sys.argv[1]
    setup_logging(f"forecasts6_{cmd}")
    labs = all_labels()
    qp = RESULTS_DIR / "qlik_scores.json"
    qlik = read_json(qp) if qp.exists() else None
    ap = RESULTS_DIR / "pt_label_audit6.json"
    audit = read_json(ap) if ap.exists() else None
    units = unit_table(labs, qlik, audit, assoc_table())
    if cmd == "draft":
        write_json(PRED_DIR / "forecasts_draft.json", {"units": units, "note": "draft (not committed)"})
        for t, u in units.items():
            logger.info(f"{t}: D={u['D']} r_u={u['r_u']} t_u={u['t_u']} lik={u['qlik_top1']} "
                        f"TAIL_EMPTY={u['TAIL_EMPTY']} LOW={u['base']['LOW_CORRECT']} n_corr={u['base']['n_correct']}")
        return
    assert qlik is not None and audit is not None, "commit #1 needs q_lik scores and the pt audit"
    fc = {"units": units, "qlik_precision": qlik.get("precision"), "qlik_prefix": qlik.get("prefix"),
          "qlik_sanity": qlik_sanity(units, qlik),
          "audit_fail": audit.get("AUDIT_FAIL"), "grep_audit": grep_all(),
          "chain_note": "commit #1 precedes the first push6 row"}
    write_json(PRED_DIR / "forecasts_G6.json", fc)
    write_json(PRED_DIR / "old_events_rescored.json", old_events(units))
    write_json(PRED_DIR / "push_plan_G6.json", push_plan(units))
    assert fc["grep_audit"]["pass"], "ban frame found in a fed prompt"
    rec = C.commit("commit#1 forecasts", [PRED_DIR / "forecasts_G6.json", PRED_DIR / "old_events_rescored.json",
                                          PRED_DIR / "push_plan_G6.json"], note="before the first fresh push row")
    logger.info(f"commit #1 at {rec['utc']}: {rec['hash'][:16]}")
    for t, u in units.items():
        logger.info(f"{t}: D={u['D']} r_u={u['r_u']} t_u={u['t_u']} lik={u['qlik_top1']} TAIL_EMPTY={u['TAIL_EMPTY']} "
                    f"DISC={u['DISCORDANT']} LOW={u['base']['LOW_CORRECT']} n_corr={u['base']['n_correct']}")


if __name__ == "__main__":
    main()
