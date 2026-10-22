#!/usr/bin/env python3
"""results/report6.md: the result tables of README.md, built from results/*.json and predictions/forecasts_G6.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import ALL_TASKS, PRED_DIR, PUSH_TASKS6, RESULTS_DIR, ROOT, read_json


def f(x: Any, nd: int = 3) -> str:
    if x is None:
        return "–"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def p(x: Any) -> str:
    if x is None:
        return "–"
    return f"{x:.4f}" if x >= 1e-4 else f"{x:.1e}"


def safe(name: str) -> Any:
    q = RESULTS_DIR / f"{name}.json"
    return read_json(q) if q.exists() else None


def contest_lines(c: dict[str, Any], title: str) -> list[str]:
    if not c or not c.get("n_events"):
        return [f"**{title}:** no events.", ""]
    h, ht, hq = c["hits_r_u_all"], c["hits_t_u_all"], c["hits_qlik_all"]
    a, b, tr = c["L1a_tail_empty"], c["L1b_discordant_lik"], c["tail_rival_discordant"]
    L = [f"**{title}:** {c['n_events']} events, {c['n_clear_landing']} with a clear landing.", "",
         "| Readout | Value |", "|---|---|",
         f"| r_u = landing (all clear landings) | {h['hits']}/{h['n_events']}, mean chance {f(h['mean_chance'])}, "
         f"Poisson-binomial p = {p(h['poisson_binomial_p'])} |",
         f"| t_u = landing (t_u defined) | {ht['hits']}/{ht['n_events']}, p = {p(ht['poisson_binomial_p'])} |",
         f"| q_lik top-1 = landing (defined) | {hq['hits']}/{hq['n_events']}, p = {p(hq['poisson_binomial_p'])} |",
         f"| L1a (TAIL-EMPTY events) | {a['hits']}/{a['n_events']} hits, p = {p(a['poisson_binomial_p'])}; {a['verdict']} |",
         f"| L1b (r_u ≠ q_lik top-1) | {b['n_events']} events: base-only {b['base_only']}, lik-only {b['rival_only']}, "
         f"both {b['both']}, neither {b['neither']}; sign p = {p(b['sign_test_p_one_sided'])} |",
         f"| tail rival (r_u ≠ t_u) | {tr['n_events']} events: base-only {tr['base_only']}, tail-only {tr['rival_only']}, "
         f"both {tr['both']}, neither {tr['neither']}; sign p = {p(tr['sign_test_p_one_sided'])} |"]
    for k, nm in (("base_vs_tail", "q_base − q_tail"), ("base_vs_lik_norm", "q_base − q_lik (norm)"),
                  ("base_vs_lik_raw", "q_base − q_lik (raw)"), ("base_vs_assoc", "q_base − q_assoc")):
        x = c["logscore_contests"].get(k) or {}
        if not x.get("n_events"):
            continue
        bca, cb = x["bca95"], x["unit_cluster_boot95"]
        ni = f"; non-inferior (lower bound > −0.10): {f(x.get('noninferior'))}" if "noninferior" in x else ""
        L.append(f"| log score {nm} (nats/program, mean over events) | {f(x['mean_diff_nats'])} "
                 f"[BCa {f(bca.get('lo'))}, {f(bca.get('hi'))}; unit-cluster {f(cb.get('lo'))}, {f(cb.get('hi'))}], "
                 f"{x['n_positive']}/{x['n_events']} events > 0, exact Wilcoxon p = {p(x['wilcoxon_exact_p_one_sided'])}, "
                 f"unit sign-flip p = {p(x['unit_level_signflip_p'])} ({x['n_units']} units){ni} |")
    uc = c.get("unit_clustered") or {}
    if uc:
        L.append(f"| unit-clustered (one pooled landing per unit) | r_u {uc['hits_r_u']['hits']}/{uc['hits_r_u']['n_events']} "
                 f"(p = {p(uc['hits_r_u']['poisson_binomial_p'])}), t_u {uc['hits_t_u']['hits']}/{uc['hits_t_u']['n_events']}, "
                 f"q_lik {uc['hits_qlik']['hits']}/{uc['hits_qlik']['n_events']}; sign-flip base−tail p = "
                 f"{p((uc.get('signflip_base_vs_q_tail') or {}).get('p_one_sided'))} |")
    L += [f"| Holm within this artifact | {json.dumps({k: (round(v, 4) if v is not None else None) for k, v in c['holm_within_artifact'].items()})} |", ""]
    return L


def event_table(c: dict[str, Any], ev: list[dict[str, Any]]) -> list[str]:
    ls = {(r["unit"], r["nudge"]): r for r in (c.get("logscore_table") or [])}
    L = ["| Unit | Nudge | Landing | Composition (correct off-default catalogue) | other | r_u | t_u | q_lik top-1 | "
         "TAIL-EMPTY | log q_base | log q_tail | log q_lik |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for e in ev:
        if not e.get("event"):
            continue
        r = ls.get((e["unit"], e["nudge"]), {})
        land = e["landing"] or f"no clear landing (modal {e['modal']})"
        L.append(f"| {e['unit']} | {e['nudge']} | {land} | {json.dumps(e['composition'])} | {e['n_correct_other']} | "
                 f"{f(e['r_u'])} | {f(e['t_u'])} | {f(e['qlik_top1'])} | {f(e['TAIL_EMPTY'])} | {f(r.get('q_base'))} | "
                 f"{f(r.get('q_tail'))} | {f(r.get('q_lik'))} |")
    non = [e for e in ev if not e.get("event")]
    if non:
        L.append("")
        L.append("Below the 5-program floor (no event): " + ", ".join(
            f"{e['unit']} {e['nudge']} ({e['n_correct_offdefault_catalogue']})" for e in non) + ".")
    return L + [""]


def unit_table(fc: dict[str, Any]) -> list[str]:
    L = ["| Unit | D_u (share, N 300) | K | r_u (correct / valid support; flags) | t_u (tail counts) | q_lik top-1 (norm) | "
         "DISCORDANT | TAIL-EMPTY |", "|---|---|---|---|---|---|---|---|"]
    for t in ALL_TASKS:
        u = fc[t]
        b = u["base"]
        flags = [k for k in ("LOW_CORRECT", "THIN_RU", "TIE") if b.get(k)]
        if u.get("AUDIT_FAIL"):
            flags.append("AUDIT_FAIL")
        if u.get("exemplar_sensitive"):
            flags.append("exemplar-sensitive")
        tail = u["tail"]["correct_offdefault_counts"]
        L.append(f"| {t} | {u['D']} ({f(u['default']['share'], 2)}) | {u['K']} | {u['r_u']} ({b['r_u_correct_support']} / "
                 f"{b['r_u_valid_support']}; {', '.join(flags) or '–'}) | {u['t_u'] or '–'} ({json.dumps(tail)}) | "
                 f"{u['qlik_top1'] or '–'} | {f(u['DISCORDANT'])} | {f(u['TAIL_EMPTY'])} |")
    return L + [""]


def main() -> None:
    fc = read_json(PRED_DIR / "forecasts_G6.json")["units"]
    l1 = safe("l1_contest") or {}
    ev = safe("events_G6") or {}
    L: list[str] = ["# Report (iteration 6, step 5: Gemma, Claim L replication)", ""]
    L += contest_lines(l1.get("primary_pooled"), "Primary: pooled (old exp28 + fresh) events, REPLICATION")
    L += event_table(l1.get("primary_pooled") or {}, ev.get("pooled", []))
    L += contest_lines(l1.get("split_fresh_only"), "Split: fresh-only events (outcomes unseen at commit #1)")
    L += event_table(l1.get("split_fresh_only") or {}, ev.get("fresh", []))
    L += contest_lines(l1.get("split_old_only"), "Split: old-only events (exp28 rows, v6 definition)")
    L += ["### Per-unit forecasts (commit #1)", ""] + unit_table(fc)
    ot = safe("old_tally")
    if ot:
        L += ["### Iteration-5 tally rescored (7 exp28 E-A2 events)", "",
              "| Unit | exp28 landing | r_u exp28 | r_u repaired | changed | t_u | q_lik top-1 | twin-silent (exp28 N 50) |",
              "|---|---|---|---|---|---|---|---|"]
        for e in ot["events"]:
            L.append(f"| {e['unit']} | {e['landing_exp28']} | {e['r_u_exp28']} | {e['r_u_repaired']} | {f(e['CHANGED'])} | "
                     f"{f(e['t_u'])} | {f(e['qlik_top1'])} | {f(e['twin_silent_exp28_N50'])} |")
        a = ot["all7"]

        def dd(x: dict) -> str:
            return (f"{x['hits']}/7 (undefined = miss; p = {p(x['poisson_binomial_p'])}); defined-only "
                    f"{x['hits_defined_only']}/{x['n_defined']} (p = {p(x['poisson_binomial_p_defined_only'])})")
        ts = ot["twin_silent"]
        L += ["", f"All 7 — exp28 r_u: {dd(a['hit_exp28'])}; repaired r_u: {dd(a['hit_repaired'])}; t_u: {dd(a['hit_tail'])}; "
                  f"q_lik top-1: {dd(a['hit_qlik'])}.",
              f"Twin-silent subset ({', '.join(ts['units'])}): repaired r_u {ts['hit_repaired']['hits']}/{ts['n']} "
              f"(defined-only {ts['hit_repaired']['hits_defined_only']}/{ts['hit_repaired']['n_defined']}), t_u "
              f"{ts['hit_tail']['hits']}/{ts['n']}, q_lik {ts['hit_qlik']['hits']}/{ts['n']}.", ""]
    sens = (l1.get("sensitivities") or {})
    if sens:
        L += ["### Sensitivities (pooled events)", "", "| Variant | r_u hits | L1a | L1b |", "|---|---|---|---|"]
        for k, v in sens.items():
            if "hits" in v:
                h = v["hits"]
                la = v.get("L1a") or {}
                lb = v.get("L1b") or {}
                L.append(f"| {k} | {h['hits']}/{h['n_events']} (p = {p(h['poisson_binomial_p'])}) | "
                         f"{la.get('hits', '–')}/{la.get('n_events', '–')} | "
                         f"{lb.get('base_only', '–')} vs {lb.get('rival_only', '–')} |")
            elif "hits_qlik" in v:
                h = v["hits_qlik"]
                c = v["logscore_base_vs_lik"]
                L.append(f"| {k} | q_lik top-1 {h['hits']}/{h['n_events']} | – | {v['L1b']['base_only']} vs "
                         f"{v['L1b']['rival_only']}; base − lik {f(c.get('mean_diff_nats'))} nats |")
        for var in ("uniform_other", "other_excluded"):
            c = (l1.get("primary_pooled") or {}).get(f"logscore_contests_{var}") or {}
            if c:
                L.append(f"| log scores, {var} | base − tail {f(c['base_vs_tail'].get('mean_diff_nats'))} | – | "
                         f"base − lik {f(c['base_vs_lik_norm'].get('mean_diff_nats'))} |")
        L.append("")
    pr = safe("pt_repertoire")
    if pr:
        L += ["### Base-model (pt) support", "",
              "| Unit | exp28 chat correct/draws | exp28 plain correct/draws | few-shot correct/draws (valid) | pooled correct | "
              "q_base basis | r_u exp28 → repaired | priming p (few-shot vs zero-shot; F_bench vs F_he) |",
              "|---|---|---|---|---|---|---|---|"]
        for t in ALL_TASKS:
            u = pr["units"][t]
            b = u["by_source"]
            pa = (u.get("priming_fewshot_vs_zeroshot_plain") or {}).get("p")
            pb = (u.get("priming_F_bench_vs_F_he") or {}).get("p")
            L.append(f"| {t} | {b['exp28_chat']['correct']}/{b['exp28_chat']['draws']} | {b['exp28_plain']['correct']}/"
                     f"{b['exp28_plain']['draws']} | {b['fewshot']['correct']}/{b['fewshot']['draws']} ({b['fewshot']['valid']}) | "
                     f"{u['n_correct_pooled']} | {u['q_base_primary']} | {u['r_u_exp28_pooled']} → {u['r_u']} | "
                     f"{p(pa)}; {p(pb)} |")
        L += ["", f"Tasks with few-shot per-draw correct rate above exp28's zero-shot 12%: "
                  f"{pr['n_tasks_fewshot_correct_rate_above_exp28_zeroshot_12pct']}/15; tasks with >= 20 correct pooled: "
                  f"{pr['n_tasks_ge20_correct']}/15.", ""]
    au = safe("pt_label_audit6")
    if au:
        r1 = au["round1"]
        L += ["### pt label audit (two judge families + tie-break)", "",
              f"Round 1: overall (stratum-weighted) {f(r1['overall_stratum_weighted'])}, raw {f(r1['overall_raw'])}, r_u "
              f"stratum {f(r1['r_u_stratum'])} (n = {r1['n_r_u_stratum']}), kappa A–B {f(r1['kappa_A_B'])}; affected tasks "
              f"{au['affected_tasks']}; AUDIT_FAIL after the revision round: {au['AUDIT_FAIL']}.", "",
              "| Unit | n | agreement (weighted) | r_u stratum | correct | failing | kappa A–B |", "|---|---|---|---|---|---|---|"]
        for t in ALL_TASKS:
            v = r1["per_task"].get(t) or {}
            if not v.get("n"):
                continue
            L.append(f"| {t} | {v['n']} | {f(v['agree_stratum_weighted'])} | {f(v['agree_r_u_stratum'])} | "
                     f"{f(v['agree_correct'])} | {f(v['agree_failing'])} | {f(v['kappa_A_B'])} |")
        if au.get("round2"):
            r2 = au["round2"]
            L += ["", f"Revision re-audit (fresh sample): overall {f(r2['overall_stratum_weighted'])}, r_u stratum "
                      f"{f(r2['r_u_stratum'])}; per task " + json.dumps({t: round(v.get('agree_stratum_weighted') or 0, 3)
                                                                         for t, v in r2['per_task'].items()}) + "."]
        L.append("")
    pd = safe("push_descriptives")
    if pd:
        L += ["### Fresh pushes (alpha 2) beside exp28's directions", "",
              "| Unit | twin off-default correct (T1.0) | fresh FD off-corr median / max | exp28 α2 median / max | "
              "fresh stage-1 passing | fresh E_u(α2) | fresh PN α2 off-corr | exp28 PN α2 off-corr |",
              "|---|---|---|---|---|---|---|---|"]
        for t in PUSH_TASKS6:
            v = pd.get(t) or {}
            if "per_cell_FD" not in v:
                continue
            fr, o2 = v["fresh_alpha2_off_corr"], v["exp28_alpha2_off_corr"]
            pn_f = (v["PN"].get("fresh:pn6_a2") or {}).get("off_corr")
            pn_o = (v["PN"].get("old:pn_a2") or {}).get("off_corr")
            L.append(f"| {t} | {f(v['twin_off_corr_T10'])} | {f(fr['median'])} / {f(fr['max'])} | {f(o2['median'])} / "
                     f"{f(o2['max'])} | {len(v.get('fresh_stage1_passing') or [])} | "
                     f"{f(v['fresh_confirmed'].get('E_u_alpha2_fresh'))} | {f(pn_f)} | {f(pn_o)} |")
        L.append("")
    l2 = safe("l2")
    if l2:
        L += [f"**L2-G:** {l2['n_on_pt_absent_algorithms']} of {l2['n_correct_nudged_offdefault_catalogue']} correct nudged "
              f"off-default catalogue programs use an algorithm with zero valid and zero correct pt programs"
              + (f" (rule-of-three bound {f(l2['rule_of_three_upper_95'])})" if l2.get("rule_of_three_upper_95") else "") + ".", ""]
    nv = safe("novelty_audit6")
    if nv:
        a, b = nv["it_model_iteration6"], nv["pt_fewshot"]
        L += [f"**Novelty audit:** it model {a['n_correct_other']} correct 'other' programs, novel {a.get('novel_count')} "
              f"(rule-of-three {f(a.get('rule_of_three_upper_95'))}), classes {json.dumps(a.get('by_arm'))}; pt few-shot "
              f"{b['n_correct_other']} correct 'other', novel {b.get('novel_count')}.", ""]
    (RESULTS_DIR / "report6.md").write_text("\n".join(L) + "\n")
    print("\n".join(L[:60]))


if __name__ == "__main__":
    main()
