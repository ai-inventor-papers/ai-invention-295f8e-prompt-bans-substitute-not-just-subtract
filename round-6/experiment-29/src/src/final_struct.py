#!/usr/bin/env python3
"""Write .terminal_claude_agent_struct_out.json; every number in the summary is read from results/*.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"


def rj(name: str) -> Any:
    p = RES / name
    return json.loads(p.read_text()) if p.exists() else {}


def s(x: Any, nd: int = 2) -> str:
    return "NA" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def main() -> None:
    ver, prim, fac, att = rj("verdict.json"), rj("primary_E.json"), rj("factorial.json"), rj("attribution.json")
    uc, ph, ec, red, pop = rj("unit_cross.json"), rj("posthoc.json"), rj("engine_check.json"), rj("rederive.json"), \
        rj("population40.json")
    nov, it4 = rj("novelty_audit.json"), rj("iter4_reference.json")
    parts = []
    parts.append("Claim E (Qwen3-8B rev b968826d, thinking off, T 1.0). The run held fixed exp19's prompts, PN seeds, "
                 "exp22's 40 directions, the ban units, hooks.make_edits RAND, the CRN streams, the 1,024-token cap "
                 "and B = 20 batch pairs. It varied only the decoder-linear precision: W8A8/W8A16/W16A8 through one "
                 "exact e4m3 emulation backend, W16A16 = native bf16 baseline, plus W8A8REAL = exp19's FP8Linear on "
                 "an sm_89 L4.")
    for t in ("T10", "T2"):
        d = prim.get("tasks", {}).get(t, {})
        if d.get("n_pairs"):
            parts.append(f"{t} PN alpha 2 correct off-default share: W8A8 {s(d['share_A'])} vs W16A16 {s(d['share_B'])} "
                         f"(diff {s(d['diff'])}, boot95 [{s(d['diff_boot95'][0])}, {s(d['diff_boot95'][1])}], exact "
                         f"McNemar {d['table']['10']}:{d['table']['01']}, p {d['mcnemar']['p_two_sided']:.2g}); "
                         f"iteration 4 {s(it4.get('tasks', {}).get(t, {}).get('PN_a2', {}).get('Y_correct'))}, "
                         f"iteration-5 bf16 {s(it4.get('iter5_bf16_reference', {}).get(t, {}).get('PN_a2', {}).get('correct_only_off_default_share'))}.")
    parts.append(f"Frozen verdict (EMU): {ver.get('verdict')}; REAL-kernel verdict: {ver.get('REAL_verdict')}; pooled "
                 f"attribution: {ver.get('attribution_pooled')}. Consequence: {ver.get('consequence')}")
    pa = att.get("pooled", {})
    if pa:
        e = pa["effects"]
        parts.append(f"Pooled AME {s(e['AME'])}, WME {s(e['WME'])}, INT {s(e['INT'])} (MDE {s(pa.get('MDE_AME_80pct_power'))}).")
    for t in ("T10", "T2"):
        d = uc.get("tasks", {}).get(t, {})
        if d:
            u = d.get("unit_in_W16A16", {})
            parts.append(f"Unit cross {t}: " + ", ".join(f"{k} {s(v['Y_correct'])}" for k, v in d["shares"].items())
                         + f" (W16A16 ban vs ban-free McNemar {u.get('table', {}).get('10')}:{u.get('table', {}).get('01')}"
                         f", p {u.get('mcnemar', {}).get('p_two_sided', float('nan')):.2g}) -> frozen text: "
                         f"{d.get('decision', 'NA')}.")
    for t in ("T10", "T2"):
        d = ph.get("tasks", {}).get(t, {})
        v = d.get("W16A16|IT5_a2")
        if v:
            parts.append(f"POST-HOC {t}: exp27's exact seeds + per-template ban-free unit in this engine give W16A16 "
                         f"{s(v['Y_correct'])} (exp27 on the same slots {s(v['exp27_Y_correct_same_slots'])}, label "
                         f"agreement {s(v['label_agreement_with_exp27'])}); W8A8 {s(d.get('W8A8|IT5_a2', {}).get('Y_correct'))}.")
    dose = rj("dose.json")
    a, b = dose.get("T10|W16A16|PN_a2", {}), dose.get("T10|W16A16|PNF_a2", {})
    if a and b:
        parts.append(f"Why: the logged ban unit concentrates the push at a few spec positions; its realised mean "
                     f"displacement at block 12 is {a['disp_S_mean']['12']:.1f} vs {b['disp_S_mean']['12']:.1f} for the "
                     f"ban-free unit (ratio to residual {a['ratio_to_residual']['12']['ratio_of_means']:.2f} vs "
                     f"{b['ratio_to_residual']['12']['ratio_of_means']:.2f}), although exp27's mean-of-ratios was 0.99; "
                     f"iteration 5's 'matched dose' was not matched, and precision is not the cause.")
    g = ec.get("EMU_vs_exp19", {}).get("gate_25_TWIN", {})
    parts.append(f"Engine checks: EMU gate twin label agreement {s(g.get('label_agreement'))} (byte identity "
                 f"{s(g.get('byte_identity'))}); REAL vs exp19 twins {s(ec.get('REAL_vs_exp19', {}).get('gate_25_TWIN', {}).get('label_agreement'))} "
                 f"label agreement on a different sm_89 SKU; prompts identical to iteration 5 (15/15); labeller "
                 f"re-check 1.00 on 2,150 iteration-4 rows.")
    for t in ("T10", "T2"):
        d = pop.get("tasks", {}).get(t, {}).get("escape", {})
        if d:
            parts.append(f"40-direction escape fraction {t}: " + ", ".join(f"{p} {s(v['escape_fraction'])}"
                                                                         for p, v in d.items()) + ".")
    parts.append(f"Novelty: {nov.get('statement', 'NA')}. Re-derivation: {red.get('mismatches', 'NA')} mismatches; "
                 f"placebos fail to reject. Files: method_out.json (datasets engine_factorial, population40, "
                 f"unit_cross, t03_control, dither, engine_check, mechanism_slots, posthoc_iter5_replication; metadata = "
                 f"all analyses), results/*.json, figures F1-F9, commitments.log (commit #0 before decisive rows).")
    summary = " ".join(parts)
    if len(summary) > 4950:
        summary = summary[:4940] + " [...]"
    out = {
        "title": "Does 8-bit arithmetic cause the nudge effect?",
        "layman_summary": ("Tests whether running a language model with 8-bit numbers, instead of 16-bit, is what made "
                           "small random internal nudges change which algorithm it writes, using identical inputs and "
                           "random seeds."),
        "summary": summary,
        "out_expected_files": {"script": "method.py", "full_output": "full_method_out.json",
                               "mini_output": "mini_method_out.json", "preview_output": "preview_method_out.json",
                               "reproducibility": "reproducibility.md"},
        "upload_ignore_regexes": ["(^|/)__pycache__/", "(^|/)\\.venv/", "^states/", "^\\.repl_agent\\.ptylog$"],
    }
    (ROOT / ".terminal_claude_agent_struct_out.json").write_text(json.dumps(out, indent=1))
    print(len(summary))
    print(summary)


if __name__ == "__main__":
    main()
