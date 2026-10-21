#!/usr/bin/env python3
"""Render results/summary.md (the README's results section) from results/*.json -- numbers are never typed by hand."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
PRECS = ("W16A16", "W16A8", "W8A16", "W8A8", "W8A8REAL")


def rj(name: str) -> Any:
    p = RES / name
    return json.loads(p.read_text()) if p.exists() else {}


def f(x: Any, nd: int = 2) -> str:
    if x is None:
        return "–"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def ci(c: list | None) -> str:
    return "–" if not c or c[0] is None else f"[{c[0]:.2f}, {c[1]:.2f}]"


def main() -> None:
    fac, prim, att, pop = rj("factorial.json"), rj("primary_E.json"), rj("attribution.json"), rj("population40.json")
    uc, t03, dith, ec = rj("unit_cross.json"), rj("t03_control.json"), rj("dither.json"), rj("engine_check.json")
    mech, land, nov, red = rj("mechanism.json"), rj("landing.json"), rj("novelty_audit.json"), rj("rederive.json")
    ver, it4, pdf = rj("verdict.json"), rj("iter4_reference.json"), rj("prompt_diff.json")
    L: list[str] = []
    L.append(f"**Verdict (EMU, frozen rule): {ver.get('verdict')}**; pooled attribution class: "
             f"**{ver.get('attribution_pooled')}**; REAL-kernel verdict: {ver.get('REAL_verdict')}.")
    L.append("")
    L.append(f"Consequence (frozen text): {ver.get('consequence')}")
    L.append("")
    L.append("### Primary contrast: PN alpha 2, W8A8 (EMU) vs W16A16, paired CRN slots")
    L.append("")
    L.append("| Task | W8A8 | W16A16 | diff [slot-bootstrap 95% CI] | discordant (W8A8 only : W16A16 only) | exact McNemar p | "
             "REAL in place of EMU: diff, p |")
    L.append("|---|---|---|---|---|---|---|")
    for t in ("T10", "T2"):
        d = prim.get("tasks", {}).get(t, {})
        if not d or d.get("missing"):
            continue
        r = d.get("REAL_in_place_of_EMU", {})
        L.append(f"| {t} | {f(d['share_A'])} | {f(d['share_B'])} | {f(d['diff'])} {ci(d['diff_boot95'])} | "
                 f"{d['table']['10']} : {d['table']['01']} | {d['mcnemar']['p_two_sided']:.2g} | "
                 f"{f(r.get('diff'))}, {('%.2g' % r['mcnemar']['p_two_sided']) if r.get('mcnemar') else '–'} |")
    L.append("")
    L.append("### Correct off-default share (Y_correct) per cell, N = 50 paired slots")
    L.append("")
    L.append("| Task | Arm | " + " | ".join(PRECS) + " | iteration 4 (exp19) | iteration 5 (exp27, bf16) |")
    L.append("|---|---|" + "---|" * (len(PRECS) + 2))
    i5 = it4.get("iter5_bf16_reference", {})
    for t in ("T10", "T2", "T03"):
        for arm in ("TWIN", "PN_a0.5", "PN_a1", "PN_a2", "POP40_a2"):
            vals = []
            for p in PRECS:
                c = fac.get(f"{t}|{p}|{arm}")
                vals.append(f"{c['Y_correct']:.2f} (n {c['N']}, pass {c['pass']:.2f})" if c else "–")
            r4 = it4.get("tasks", {}).get(t, {}).get(arm, {})
            r5 = i5.get(t, {}).get(arm, {})
            L.append(f"| {t} | {arm} | " + " | ".join(vals) + f" | {f(r4.get('Y_correct'))} | "
                     f"{f(r5.get('correct_only_off_default_share'))} |")
    L.append("")
    L.append("### Attribution (PN alpha 2; AME = activation main effect, WME = weight main effect)")
    L.append("")
    L.append("| Scope | AME [95% CI] | WME [95% CI] | INT [95% CI] | verdict | MDE(AME) |")
    L.append("|---|---|---|---|---|---|")
    for name, d in list(att.get("tasks", {}).items()) + [("pooled", att.get("pooled", {}))]:
        if not d or d.get("missing"):
            continue
        e, b = d["effects"], d["boot95"]
        L.append(f"| {name} | {f(e['AME'])} {ci(b['AME'])} | {f(e['WME'])} {ci(b['WME'])} | {f(e['INT'])} "
                 f"{ci(b['INT'])} | {d['verdict']} | {f(d.get('MDE_AME_80pct_power'))} |")
    L.append("")
    L.append("### Population check (40 fixed directions, alpha 2)")
    L.append("")
    for t in ("T10", "T2"):
        d = pop.get("tasks", {}).get(t, {})
        if not d or d.get("missing"):
            continue
        esc = "; ".join(f"{p}: escape {v['escape_fraction']:.2f} (mean share {v['mean_share']:.2f}, n dirs "
                        f"{v['n_dirs']})" for p, v in d.get("escape", {}).items())
        L.append(f"- {t}: {esc}")
        pr = d.get("pairs", {}).get("W8A8_vs_W16A16")
        if pr:
            L.append(f"  - W8A8 vs W16A16 per direction: mean diff {f(pr['mean_diff'])}, Wilcoxon p "
                     f"{f(pr['wilcoxon_p'], 3)}, Spearman {f(pr['spearman'])}, Jaccard of escape sets "
                     f"{f(pr['jaccard_escape'])}")
        pa = d.get("population_attribution")
        if pa:
            L.append(f"  - population attribution: AME {f(pa['effects']['AME'])}, WME {f(pa['effects']['WME'])} -> "
                     f"{pa['verdict']}")
        r4 = d.get("iter4_reproduction_W8A8_vs_exp22")
        if r4:
            L.append(f"  - W8A8 vs exp22 (iteration 4) per-direction shares: mean {f(r4['mean_W8A8'])} vs "
                     f"{f(r4['mean_exp22'])}, Spearman {f(r4['spearman'])}")
    L.append("")
    L.append("### Unit cross, T03 control, dither")
    L.append("")
    for t in ("T10", "T2"):
        d = uc.get("tasks", {}).get(t, {})
        if d:
            L.append(f"- Unit cross {t}: " + ", ".join(f"{k} {f(v['Y_correct'])}" for k, v in d["shares"].items()) +
                     f". Decision: {d.get('decision', '–')}")
    mv = t03.get("moves_in_all_run", {})
    if mv:
        L.append("- T03 positive control (PN alpha 2 minus twin >= 0.10): " +
                 ", ".join(f"{p} {'moves' if v else 'does not move'}" for p, v in mv.items()))
    for t in ("T10", "T2"):
        for v, d in dith.get("tasks", {}).get(t, {}).items():
            a = d.get("DITHER_PN2_vs_W16A16_PN_a2", {})
            b = d.get("DITHER_TWIN_vs_W16A16_TWIN", {})
            if a.get("n_pairs"):
                L.append(f"- Dither {v} {t}: dither-PN2 {f(a['share_A'])} vs W16A16 PN2 {f(a['share_B'])} "
                         f"(p {a['mcnemar']['p_two_sided']:.2g}); dither-twin {f(b.get('share_A'))}. "
                         f"{d.get('reading', '')}")
    L.append("")
    L.append("### Engine checks")
    L.append("")
    g = ec.get("EMU_vs_exp19", {}).get("gate_25_TWIN", {})
    gr = ec.get("REAL_vs_exp19", {}).get("gate_25_TWIN", {})
    L.append(f"- EMU gate (25 T2 twin slots): byte identity {f(g.get('byte_identity'))}, label agreement "
             f"{f(g.get('label_agreement'))} (pass = {ec.get('EMU_gate_twin_label_agreement_ge_0.9')}).")
    L.append(f"- REAL (exp19 FP8Linear on the L4) vs exp19 (RTX 2000 Ada): byte identity {f(gr.get('byte_identity'))}, "
             f"label agreement {f(gr.get('label_agreement'))}; all REAL rows: "
             f"{f(ec.get('REAL_vs_exp19', {}).get('all_rows', {}).get('byte_identity_rate'))} byte-identical.")
    an = ec.get("W16A16_anchor_vs_exp27", {})
    L.append(f"- W16A16 anchor vs exp27 (25 T10 twin slots): byte identity {f(an.get('byte_identity'))}, label "
             f"agreement {f(an.get('label_agreement'))}.")
    L.append(f"- Prompt diff exp19 vs iteration 5: {pdf.get('n_identical')}/{pdf.get('n_compared')} twin prompts "
             f"identical.")
    L.append("")
    L.append("### Mechanism readouts (forward passes, batch 1, 50 PN alpha-2 slots per task)")
    L.append("")
    for k, d in mech.get("precisions", {}).items():
        dr = d.get("divergence_R", {})
        L.append(f"- {k}: KL at R {f(d.get('kl_R', {}).get('mean'), 4)}, teacher-forced KL (32 tokens) "
                 f"{f(d.get('kl_tf_mean', {}).get('mean'), 4)}, argmax at R changed {f(d.get('argmax_R_changed_share'))},"
                 f" divergence at R block 35 {f(dr.get('35'), 3)}")
    cc = mech.get("clean_vs_clean_rel_divergence", {})
    for k, v in cc.items():
        L.append(f"- clean-vs-clean relative divergence {k}: " + ", ".join(f"b{l} {x:.4f}" for l, x in v.items()))
    L.append("")
    L.append(f"Novelty audit: {nov.get('statement', '–')} (spend {nov.get('spend_usd', '–')} USD).")
    L.append(f"Independent re-derivation: {red.get('mismatches', '–')} mismatches over {len(red.get('checks', []))} "
             f"checks; commit chain: {red.get('commit_chain', {})}.")
    (RES / "summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
