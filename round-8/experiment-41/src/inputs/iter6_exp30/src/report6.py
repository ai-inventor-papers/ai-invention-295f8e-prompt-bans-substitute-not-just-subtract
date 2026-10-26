#!/usr/bin/env python3
"""Markdown tables of every headline, generated from results/*.json only -> results/summary.md (pasted into the
README's results section, so prose and tables cannot disagree with the data)."""

from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import RESULTS_DIR, ROOT, read_json, read_jsonl
from cfg6 import DEFAULT6, Y6

CELLS = ["BAN", "X_0-11", "X_12-23", "X_24-35", "X_0-35", "COND", "RPOS", "MR_0-35", "MR_12-23", "PLACEBO"]


def f(x: Any, d: int = 2) -> str:
    if x is None:
        return "-"
    if isinstance(x, float):
        if math.isnan(x):
            return "-"
        if abs(x) < 1e-3 and x != 0:
            return f"{x:.1e}"
        return f"{x:.{d}f}"
    return str(x)


def comp(c: dict[str, int], k: int = 4) -> str:
    return ", ".join(f"{a} {b}" for a, b in list(c.items())[:k]) if c else "-"


def load(name: str) -> Any:
    p = RESULTS_DIR / name
    return read_json(p) if p.exists() else None


def stage_a_md(a: dict[str, Any]) -> list[str]:
    out = ["### Stage A: full-state exchange (N = 30 per cell, paired CRN slots 0-29)", ""]
    for t, v in a["tasks"].items():
        tw = v["TWIN"]
        out += [f"**{t}** (default {v['default']}, Y = {v['Y']}, route class of iterations 2-3: "
                f"{v['route_class_iter2_3']}). Twin (slots 0-29): Y share {f(tw['Y_share'])}, off-default "
                f"{f(tw['off_default'])}, pass {f(tw['pass'])}; twin correct composition: {comp(tw['correct_comp'])}.",
                "", "| cell | n | Y share [CP 95%] | transfer | off-default transfer | pass ratio | recovery | slot IIA |"
                    " McNemar b:c (p, Holm) | correct composition |",
                "|---|---|---|---|---|---|---|---|---|---|"]
        for c in CELLS:
            r = v["cells"].get(c)
            if not r:
                continue
            m = r["mcnemar_vs_twin"]
            lo, hi = r["Y_ci95_cp"]
            out.append(f"| {c} | {r['n']} | {f(r['Y_share'])} [{f(lo)}, {f(hi)}] | {f(r['transfer'])} | "
                       f"{f(r['off_default_transfer'])} | {f(r['pass_ratio'])} | {f(r['recovery'])} | "
                       f"{f(r['slot_IIA'])} | {m['b_Y_only_cell']}:{m['c_Y_only_twin']} ({f(m['p'], 3)}, "
                       f"{f(m.get('p_holm'), 3)}) | {comp(r['correct_comp'])} |")
        x = v["cells"].get("X_0-35", {}).get("mcnemar_vs_MR_0-35")
        if x:
            out.append(f"\nX_0-35 vs MR_0-35 on Y: {x['b_X_only']}:{x['c_MR_only']} discordant, exact p "
                       f"{f(x['p'], 4)} (Holm {f(x.get('p_holm'), 4)}).")
        out.append("")
    out += [f"- **P1 (committed)**: {a['P1']['verdict']}. Prompt-route tasks transferring at band 0-35 (transfer >= "
            f"0.5, pass ratio >= 0.8): {a['P1']['prompt_route_tasks_transferring']} (need 2 of T2, T03, T10). "
            f"T05/T06 transfer at band 0-35: {({k: f(v) for k, v in a['P1']['T05_T06_transfer'].items()})} "
            f"(upper 95%: {({k: f(v) for k, v in a['P1']['T05_T06_upper95'].items()})}; prediction <= 0.2).",
            f"- **Route check (secondary)**: COND transfer T05/T06 "
            f"{({k: f(v) for k, v in a['route_check']['COND_T05_T06_ge_0.5'].items()})} (predicted >= 0.5), T2 "
            f"{f(a['route_check']['COND_T2_le_0.2'])} (predicted <= 0.2) -> {a['route_check']['verdict_COND']}; "
            f"RPOS <= 0.2 everywhere -> {a['route_check']['verdict_RPOS']}.",
            f"- **PLACEBO** |transfer| <= 0.1: {({k: f(v) for k, v in a['placebo'].items()})} -> {a['placebo_verdict']}.",
            f"- **X_0-35 beats MR_0-35 where P1 transfers**: {a['MR_verdict']}.", ""]
    u6 = a.get("U6_COND_vs_exp16_arm_d")
    if u6 and "error" not in u6:
        out.append("U6 (COND vs exp16 route arm d): " + "; ".join(
            f"{t}: recovery {f(v['this_recovery'])}, off-default transfer {f(v['this_off_default_transfer'])}, exp16 "
            f"F_direct {f((v['exp16_F_direct'] or {}).get('point') if isinstance(v['exp16_F_direct'], dict) else v['exp16_F_direct'])}"
            for t, v in u6.items()))
        out.append("")
    return out


def st_md(s: dict[str, Any]) -> list[str]:
    out = ["### ST: noise-site grid in bf16 (T03, T10; N = 30 per cell)", ""]
    for t, v in s["tasks"].items():
        out += [f"**{t}** (twin correct off-default {f(v['twin_correct_off_default'])}).", "",
                "| site | alpha | n | correct off-default | off-default | pass | median D_R (b35) | median D_g1 (b35) |"
                " correct composition |", "|---|---|---|---|---|---|---|---|---|"]
        for k, c in sorted(v["cells"].items(), key=lambda kv: (kv[1]["site"], kv[1]["alpha"])):
            out.append(f"| {c['site']} | {f(c['alpha'], 0)} | {c['n']} | {f(c['correct_off_default'])} | "
                       f"{f(c['off_default'])} | {f(c['pass'])} | {f(c['median_D_R'], 3)} | {f(c['median_D_g1'], 3)} |"
                       f" {comp(c['correct_comp'])} |")
        ind = v["indicator"]
        out.append("")
        if "beta" in ind:
            out += [f"Firth indicator model (n {ind['n']}, events {ind['n_events']}, common support {v['common_support'].get('n_after')}"
                    f" of {v['common_support'].get('n_before')} rows):", "",
                    "| term | beta | profile 95% CI | cluster bootstrap 95% CI |", "|---|---|---|---|"]
            for nm, b in ind["beta"].items():
                if nm == "const":
                    continue
                pci = ind["profile_ci95"].get(nm)
                bci = (ind.get("cluster_bootstrap") or {}).get("ci95", {}).get(nm)
                out.append(f"| {nm} | {f(b)} | {('[' + f(pci[0]) + ', ' + f(pci[1]) + ']') if pci else '-'} | "
                           f"{('[' + f(bci[0]) + ', ' + f(bci[1]) + ']') if bci else '-'} |")
        else:
            out.append(f"Firth indicator model: {ind.get('error')} (n {ind.get('n')}, events {ind.get('n_events')}).")
        out.append(f"\nRule model: {v.get('rule_model')}; converged: {ind.get('converged')}.")
        for key, lab in (("indicator_alpha_le4_posthoc", "post-hoc sensitivity, alpha <= 4 only"),
                         ("indicator_logDR_only", "sensitivity, log D_R only"),
                         ("indicator_primary_all_trimmed_rows", "primary design on all trimmed rows")):
            sv = v.get(key)
            if not sv:
                continue
            if "beta" not in sv:
                out.append(f"- {lab}: {sv.get('error')}")
                continue
            parts = []
            for nm in ("S1", "S2", "S4", "S5"):
                if nm in sv["beta"]:
                    pci = (sv.get("profile_ci95") or {}).get(nm)
                    bci = ((sv.get("cluster_bootstrap") or {}).get("ci95") or {}).get(nm)
                    parts.append(f"{nm} {f(sv['beta'][nm])}" + (f" profile [{f(pci[0])}, {f(pci[1])}]" if pci else "")
                                 + (f" boot [{f(bci[0])}, {f(bci[1])}]" if bci else ""))
            out.append(f"- {lab} (n {sv.get('n')}, events {sv.get('n_events')}, converged {sv.get('converged')}): "
                       + "; ".join(parts))
        mh = v.get("mh", {})
        if mh:
            out.append("\nMantel-Haenszel OR within log D_R quintiles: " + "; ".join(
                f"{k}: {f(x.get('or'))} {('[' + f(x['ci95'][0]) + ', ' + f(x['ci95'][1]) + ']') if x.get('ci95') else ''}"
                for k, x in mh.items()))
        pf = v.get("paired_flips", {})
        if pf:
            out.append("\nPaired site flips (S0-only : other-only, exact McNemar p): " + "; ".join(
                f"{k} {x['S0_only']}:{x['other_only']} ({f(x['p'], 3)})" for k, x in pf.items()))
        out.append("")
    out.append(f"- **RULE (committed)**: {s['RULE']['verdict']}")
    out.append("")
    return out


def svt_md(d: dict[str, Any]) -> list[str]:
    out = ["### State noise (S3) vs departure-matched temperature (DMD), N = 50 paired slots", "",
           "| task, alpha | K_S3 (nats/token) | T_dmd | f_on | S3-only : DMD-only flips | exact p | S3 flip share | "
           "DMD flip share | S3 pass | DMD pass |", "|---|---|---|---|---|---|---|---|---|---|"]
    for k, v in d.items():
        if not isinstance(v, dict):
            continue
        c = v.get("calibration") or {}
        out.append(f"| {k} | {f(c.get('K_S3'), 4)} | {f(c.get('T_dmd'))} | {f(c.get('f_on'), 4)} | "
                   f"{v['S3_only_flips']}:{v['DMD_only_flips']} | {f(v['p_exact_mcnemar'], 4)} | {f(v['S3_flip_share'])} |"
                   f" {f(v['DMD_flip_share'])} | {f(v['S3_pass'])} | {f(v['DMD_pass'])} |")
    out += ["", f"- **Verdict (alpha 2, both tasks, p < 0.05)**: {d.get('verdict_alpha2')}", ""]
    return out


def top5_md(d: dict[str, Any]) -> list[str]:
    out = ["### T1 top-five plan push (exp20 u_top5, displacement-targeted at spec, blocks 12-23)", "",
           "| cell | n | pass | BFS share | correct non-BFS | landing composition | landing test |",
           "|---|---|---|---|---|---|---|"]
    lt = d.get("landing_test", {})
    for k, v in d["cells"].items():
        t = lt.get(k, {})
        out.append(f"| {k} | {v['n']} | {f(v['pass'])} | {f(v['bfs_share'])} | {v['correct_non_bfs']} | "
                   f"{comp(v['landing_comp'], 6)} | {t.get('reading', t.get('verdict', '-'))} "
                   f"(n on survivors {t.get('n_on_survivors', '-')}) "
                   f"{('(p closer than null ' + f(t['p_closer_than_null'], 3) + ')') if 'p_closer_than_null' in t else ''} |")
    g = d.get("geometry")
    if g:
        e = g["explained_by_pc1_pc2_of_centroids"]
        out.append(f"\nGeometry: PCA plane of the 10 forced-prompt centroids (PC1 {100 * e[0]:.0f}%, PC2 "
                   f"{100 * e[1]:.0f}% of centroid variance); points = this artifact's bf16 spec-mean states.")
    out.append("")
    return out


def l_md(d: dict[str, Any]) -> list[str]:
    out = ["### L: retrospective landing-forecast contest (21 recorded push-landing events)", "",
           "| event | landing | BASE top-1 | TWINMIN top-1 | OPEN top-1 | log score BASE / OPEN / TWINMIN |",
           "|---|---|---|---|---|---|"]
    for e in d["events"]:
        out.append(f"| {e['event']} | {e['landing_top1']} | {e['BASE_top1']} {'✓' if e['BASE_hit'] else '✗'} | "
                   f"{e.get('TWINMIN_top1') or '-'} {('✓' if e.get('TWINMIN_hit') else '✗') if e.get('TWINMIN_hit') is not None else ''} | "
                   f"{e.get('OPEN_top1') or '-'} {('✓' if e.get('OPEN_hit') else '✗') if e.get('OPEN_hit') is not None else ''} | "
                   f"{f(e.get('BASE_logscore'))} / {f(e.get('OPEN_logscore'))} / {f(e.get('TWINMIN_logscore'))} |")
    st = d["primary_sign_test"]
    out += ["", f"- Hits: BASE {d['BASE_hits']}, OPEN {d['OPEN_hits']}, OPEN (1/rank) {d['OPEN_rank_hits']}, TWINMIN "
                f"{d['TWINMIN_hits']}.",
            f"- **Primary sign test (BASE > OPEN)**: {st['base_wins']}:{st['open_wins']} on {st['n_discordant']} discordant "
            f"events (top-1 differ on {st['n_top1_differ']}), one-sided p {f(st['p_one_sided_base_gt_open'], 4)}; "
            f"minimum for p < 0.05 is 5 of 5. Verdict: {d['verdict']}.",
            f"- Log scores: BASE - OPEN {d.get('logscore_BASE_minus_OPEN')}; BASE - TWINMIN "
            f"{d.get('logscore_BASE_minus_TWINMIN')}.", ""]
    return out


def ext_md() -> list[str]:
    from analysis6 import load_rows
    rows = load_rows()
    out = ["### Extensions (forced sources, semantic seed, W4)", "",
           "| task | cell | n | Y / default share | off-default share | pass | composition |", "|---|---|---|---|---|---|---|"]
    by: dict[tuple[str, str], list] = {}
    for r in rows:
        if r["cell"] in ("EXT", "W4"):
            by.setdefault((r["task"], r["arm"]), []).append(r)
    Ys = {"T2": "bf_spfa", "T10": "bfs"}
    for (t, arm), rs in sorted(by.items()):
        n = len(rs)
        D = DEFAULT6[t]
        y = Ys.get(t) if arm.startswith("FORCED") else Y6.get(t)
        out.append(f"| {t} | {arm} | {n} | {f(sum(r['label'] == y for r in rs) / n)} ({y}) / "
                   f"{f(sum(r['label'] == D for r in rs) / n)} | {f(sum(r['label'] not in (D, 'invalid') for r in rs) / n)}"
                   f" | {f(sum(r['passed'] for r in rs) / n)} | {comp(dict(Counter(r['label'] for r in rs).most_common()))} |")
    out.append("")
    return out if by else []


def main() -> None:
    md = ["# Results tables (generated by src/report6.py from results/*.json)", ""]
    ec = load("engine_check.json")
    if ec:
        md += ["### Engine check and unit tests", ""]
        for t, v in ec.items():
            if isinstance(v, dict) and "label_agreement" in v:
                md.append(f"- {t}: per-slot label agreement with exp27's bf16 twin {f(v['label_agreement'], 3)} "
                          f"({v['n_pairs']} pairs){' (decisive)' if v['decisive'] else ''}.")
        md.append(f"- Verdict: {ec.get('verdict')}.")
        ut = ec.get("unit_tests", {})
        if ut:
            md.append(f"- U-tests: {ut.get('pass')}; U3 max |logit diff| at R "
                      f"{ {w: f(x['max_abs_logit_diff_at_R'], 3) for w, x in ut.get('U3', {}).items()} }, U3 label "
                      f"equality {ut.get('U3_label_equality')}, U4 max relative error along u "
                      f"{f(ut.get('U4', {}).get('max_rel_err_along_u'), 5)}.")
        md.append("")
    for name, fn in (("stage_a.json", stage_a_md), ("site_grid.json", st_md), ("state_vs_token.json", svt_md),
                     ("top5_push.json", top5_md), ("landing_forecast.json", l_md)):
        d = load(name)
        if d:
            try:
                md += fn(d)
            except (KeyError, TypeError) as e:
                md += [f"(table for {name} failed: {e})", ""]
    try:
        md += ext_md()
    except (KeyError, TypeError, FileNotFoundError) as e:
        md += [f"(extension table failed: {e})", ""]
    na = load("novelty_audit.json")
    if na:
        md += ["### Novelty audit", "", f"- {na['n_correct_other']} correct 'other' programs; classes {na['classes']}; "
                                        f"cost USD {na['cost_usd']}.", ""]
    rd = load("rederive.json")
    if rd:
        md += [f"### Independent re-derivation: {rd['n_checks']} checks, {rd['mismatches']} mismatches.", ""]
    (RESULTS_DIR / "summary.md").write_text("\n".join(md))
    print(f"summary.md: {len(md)} lines")


if __name__ == "__main__":
    main()
