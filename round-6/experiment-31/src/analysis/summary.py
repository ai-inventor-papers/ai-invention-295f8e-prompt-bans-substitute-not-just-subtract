#!/usr/bin/env python3
"""Render results/summary.md (markdown tables pasted into README.md) from the result files; no recomputation."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results"


def j(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


def f(x, d=2):
    if x is None:
        return "-"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, float):
        return f"{x:.{d}f}"
    return str(x)


def main() -> None:
    units = j(ROOT / "units.json")["units"]
    events = j(ROOT / "landing_events.json")["events"]
    pool = j(R / "pool_l1_panelI.json")
    out = []
    out.append("### Units (forecasts committed before each unit's first nudge row)\n")
    out.append("| unit | default D_u | K | base runner-up r_u | q_lik top-1 | tail t_u | tail-empty | discordant | "
               "E_u (a=1/2/4) | HF twin pass | gate (kappa / rt-vs-adj) | flags |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for U in units:
        e = U["E_u_by_alpha"]
        g = U["gate"]
        out.append(f"| {U['unit']} | {U['default']} | {U['K']} | {U['r_u']} | {U['q_lik_top1']} | {f(U['t_u'])} | "
                   f"{f(U['tail_empty'])} | {f(U['discordant'])} | {f(e.get('1.0'))}/{f(e.get('2.0'))}/"
                   f"{f(e.get('4.0'))} | {f(U['hf_twin']['pass_rate'])} | {f(g.get('kappa_runtime_ast'))} / "
                   f"{f(g.get('runtime_vs_adjudicated'))} ({g['file'].replace('.json', '')}) | "
                   f"{', '.join(U['flags']) or '-'} |")
    out.append("\n### Landing events (cells with pass rate >= 0.8 x twin pooled per nudge type)\n")
    out.append("| unit | nudge | n attempts | pass | correct off-default catalogue programs | other (correct) | "
               "exists | modal | lead | clear | r_u hit | q_lik hit | t_u hit |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for e in events:
        cnt = ", ".join(f"{k} {v}" for k, v in e["correct_off_default_counts"].items() if v) or "0"
        h = lambda x: f(bool(e["clear_landing"] and x is not None and e["modal_landing"] == x))  # noqa: E731
        out.append(f"| {e['unit']} | {e['nudge_type']} | {e['n_attempts']} | {f(e['pass_rate'])} | {cnt} | "
                   f"{e['n_other_correct']} | {f(e['exists'])} | {f(e['modal_landing'])} | {f(e['margin'])} | "
                   f"{f(e['clear_landing'])} | {h(e['r_u']) if e['exists'] else '-'} | "
                   f"{h(e['q_lik_top1']) if e['exists'] else '-'} | {h(e['t_u']) if e['exists'] else '-'} |")
    a, b = pool["per_event"]["L1a"], pool["per_event"]["L1b"]
    ua, ub = pool["unit_clustered"]["L1a"], pool["unit_clustered"]["L1b"]
    out.append("\n### Claim L tests (pool_l1.py, frozen; panel I alone is descriptive below n = 6)\n")
    out.append("| test | scope | n | statistic | p | verdict |")
    out.append("|---|---|---|---|---|---|")
    out.append(f"| L1a (tail-empty events) | per event | {a['n']} | {a['hits']} hits (chance mean "
               f"{f(a['chance_mean'])}) | {f(a['p_poisson_binomial'], 3)} | {a['verdict']} |")
    out.append(f"| L1b (discordant events) | per event | {b['n_discordant']} | b = {b['b_base_only']}, c = "
               f"{b['c_qlik_only']} | {f(b['p_sign'], 3)} | {b['verdict']} |")
    out.append(f"| L1a | unit-clustered | {ua['n']} | {ua['hits']} hits | {f(ua['p_poisson_binomial'], 3)} | "
               f"{ua['verdict']} |")
    out.append(f"| L1b | unit-clustered | {ub['n_discordant']} | b = {ub['b_base_only']}, c = {ub['c_qlik_only']} | "
               f"{f(ub['p_sign'], 3)} | {ub['verdict']} |")
    t = pool["per_event"]["t_u_top1"]
    ra = pool["per_event"]["r_u_top1_all_events"]
    out.append(f"\nAll existing events: r_u named the modal landing in {ra['hits']}/{ra['n']}; t_u (tuned model's own "
               f"minority mode) in {t['hits']}/{t['n']} events where t_u is defined. Verdict note: {pool['note']}.\n")
    out.append("| log-score difference D = LS_base - LS_rival | events | mean D (nats) | one-sided 95% lower bound | "
               "non-inferior (> -0.10) | defined-only n / mean D |")
    out.append("|---|---|---|---|---|---|")
    for rival in ("q_lik", "q_lik_raw", "q_tail"):
        r = pool["per_event"]["log_scores"][rival]
        out.append(f"| base vs {rival} (event bootstrap) | {r['all']['n']} | {f(r['all']['mean_D'])} | "
                   f"{f(r['all']['lower95'])} | {f(r['all']['non_inferior'])} | {r['defined_only']['n']} / "
                   f"{f(r['defined_only']['mean_D'])} |")
        rc = pool["unit_clustered"]["log_scores_cluster_bootstrap"][rival]["all"]
        out.append(f"| base vs {rival} (unit-cluster bootstrap) | {rc['n']} | {f(rc['mean_D'])} | {f(rc['lower95'])} | "
                   f"{f(rc['non_inferior'])} | - |")
    l2 = j(R / "l2.json")
    if l2:
        out.append(f"\n**L2:** {l2['count_in_base_absent_modes']} of {l2['N']} correct nudged off-default programs "
                   f"fall in a mode with 0 valid and 0 correct base programs"
                   + (f" (rule-of-three upper bound {l2['rule_of_three_upper']:.3f})." if l2.get(
                       "rule_of_three_upper") else "."))
    l3 = j(R / "l3.json")
    if l3:
        out.append("\n**L3 (held-out log score of the nudged off-default programs, mean over 10 splits; units with "
                   ">= 4 programs):**\n")
        out.append("| unit | n | q_base^gamma | uniform | association | q_tail | Kendall tau(base, tail) |")
        out.append("|---|---|---|---|---|---|---|")
        for r in l3["units"]:
            h = r.get("heldout_log_score") or {}
            out.append(f"| {r['unit']} | {r['n_programs']} | {f(h.get('q_base_gamma'))} | {f(h.get('uniform'))} | "
                       f"{f(h.get('association'))} | {f(h.get('q_tail'))} | {f(r['kendall_tau_base_tail'])} |")
        out.append(f"\nPooled Kendall tau mean {f(l3['mean_tau'])}; sign test over units {l3['n_tau_pos']} positive / "
                   f"{l3['n_tau_neg']} negative, p = {f(l3['sign_test_p'], 3)}.")
    m = j(R / "m.json")
    if m:
        out.append("\n**M (movability candidates vs E_u; one panel, descriptive):**\n")
        out.append("| candidate | direction | n | Spearman rho | one-sided p | Holm p | supported |")
        out.append("|---|---|---|---|---|---|---|")
        for c, r in m["candidates"].items():
            out.append(f"| {c} | {r.get('direction', '-')} | {r['n']} | {f(r.get('rho'))} | "
                       f"{f(r.get('p_one_sided'), 3)} | {f(r.get('p_holm'), 3)} | {f(r.get('supported'))} |")
    k = j(R / "k.json")
    if k:
        out.append("\n**K (correct-only rarefied Hill-1 at depth 25; pass cost = twin pass rate minus knob pass rate, "
                   "points):**\n")
        out.append("| unit | Hill-1 twin | PN a2 (cost) | PN a4 (cost) | BINT (cost) | H5 / P15 / P20 (full hull) |")
        out.append("|---|---|---|---|---|---|")
        for r in k["units"]:
            pr, h = r["pass_rate"], r["hill1_depth25"]

            def kc(n):
                if n not in h:
                    return "-"
                return f"{f(h[n])} ({f(100 * (pr['twin'] - pr[n]), 0)})"
            hf_ = r["hull_full"]
            out.append(f"| {r['unit']} | {f(h.get('twin'))} | {kc('PN_a2')} | {kc('PN_a4')} | {kc('BINT')} | "
                       f"{f(hf_.get('5'))} / {f(hf_.get('15'))} / {f(hf_.get('20'))} |")
    nv = j(R / "novelty.json")
    if nv:
        out.append(f"\n**Novelty audit:** {nv['n_distinct_correct_other']} distinct correct 'other' programs among "
                   f"{nv['n_correct_programs']} correct programs; classes {nv['classes']}; {nv['statement']}"
                   + (f" (rule-of-three bound {nv['rule_of_three_upper_per_correct_program']:.5f} per correct "
                      "program)." if nv.get("rule_of_three_upper_per_correct_program") else "."))
    (R / "summary.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
