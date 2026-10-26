#!/usr/bin/env python3
"""results/summary.md: every result table, generated from the result files (no recomputation)."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg7 import PRED_DIR, RESULTS_DIR, SAMPLERS, TEMPS, read_json  # noqa: E402


def f(x, d=3):
    if x is None:
        return "-"
    if isinstance(x, float):
        if not math.isfinite(x):
            return "inf" if x > 0 else "nan"
        return f"{x:.{d}f}"
    return str(x)


def main() -> str:
    L = []
    tw = read_json(RESULTS_DIR / "twins.json")
    L.append("## S0 twins (N = 100 per unit, T 1.0, top-p 1)\n")
    L.append("| unit | counts | A_min | A_min share | pass rate | iteration-5 record |")
    L.append("|---|---|---|---|---|---|")
    for u, v in tw.items():
        L.append(f"| {u} | {v['counts']} | {v['a_min']} | {f(v['share_a_min'], 2)} | {f(v['pass_rate'], 2)} | "
                 f"{v['record_share_iter5']} |")
    F = read_json(RESULTS_DIR / "forks.json")
    L.append("\n## S1 fork location\n")
    L.append("| unit | mode | |O| | coverage (clusters) | confirmed / base paths | on-O confirmed at |O|+1 | "
             "calibration (k=0 vs twin, Fisher p) |")
    L.append("|---|---|---|---|---|---|---|")
    for u, v in F.items():
        cl = ", ".join(f"{c['id']} {len(c['O'])} tok {c['cov']:.2f}" for c in v["opening"]["clusters"])
        c = v["calibration"]
        L.append(f"| {u} | {v['mode']} | {v['opening']['len_O']} | {cl} | {v['n_confirmed']}/{len(v['base_paths'])} | "
                 f"{v['n_at_O_plus_1']}/{v['n_confirmed_on_O']} | {f(c['k0_share'], 2)} vs {f(c['twin_share'], 2)} "
                 f"(p {f(c['fisher_p'], 2)}, {'pass' if c['pass'] else 'FAIL'}) |")
    L.append("\nConfirmed fork tokens:\n")
    for u, v in F.items():
        toks = [f"{ib.get('fork_token')!r} at k={ib.get('f')} (jump {f(ib['confirm']['jump'], 2)})"
                for ib in v["per_base_path"].values() if ib.get("confirmed")]
        L.append(f"- {u}: " + "; ".join(toks))
    pv = read_json(RESULTS_DIR / "predictions_view.json")
    t1 = read_json(RESULTS_DIR / "test1.json") if (RESULTS_DIR / "test1.json").exists() else None
    L.append("\n## Test (1): one-token concentration H(A | fork class)\n")
    L.append("| unit | H (bits) | bootstrap 95% CI | class mass | undecided-token mass | pass (<= 0.3) |")
    L.append("|---|---|---|---|---|---|")
    for u, U in pv["units"].items():
        t = U["test1"]
        L.append(f"| {u} | {f(t['H_bits'])} | [{f(t['H_boot_ci95'][0])}, {f(t['H_boot_ci95'][1])}] | "
                 f"{ {k: round(x, 3) for k, x in t['class_mass'].items()} } | {f(t['undecided_mass'])} | "
                 f"{'yes' if t['H_bits'] <= 0.3 else 'no'} |")
    t2 = read_json(RESULTS_DIR / "test2.json") if (RESULTS_DIR / "test2.json").exists() else None
    L.append("\n## Test (2): committed predictions vs the same-seed sweep (attempted A_min share, N = 50 per cell)\n")
    L.append("| unit | cell | predicted | observed [Wilson 95%] | correct A_min obs / pred | on-opening obs / pred | "
             "JS (bits) | replay acc |")
    L.append("|---|---|---|---|---|---|---|---|")
    for u, U in pv["units"].items():
        cells = (t2 or {}).get("per_unit", {}).get(u, {}).get("cells", {})
        for T in TEMPS:
            for s in SAMPLERS:
                c = f"T{T}_{s}"
                o = cells.get(c)
                if o:
                    L.append(f"| {u} | {c} | {f(U['cells'][c]['a_min'])} | {f(o['a_min'])} [{f(o['a_min_ci'][0], 2)}, "
                             f"{f(o['a_min_ci'][1], 2)}] | {f(o['correct_a_min'])} / {f(o['pred_correct_a_min'])} | "
                             f"{f(o['on_opening_obs'], 2)} / {f(o['on_opening_pred'], 2)} | {f(o['js_bits'])} | "
                             f"{f(o['replay_acc'], 2)} (n {o['replay_n']}) |")
                else:
                    L.append(f"| {u} | {c} | {f(U['cells'][c]['a_min'])} | - | - | - | - | - |")
    if t2:
        L.append("\n| unit | MAE | dObs 1.0->0.3 [slot bootstrap] | dPred | McNemar b:c, one-sided p | dObs 1.0->1.3 | "
                 "dPred 1.0->1.3 | slots changing idea across T (top-p 1) | pass |")
        L.append("|---|---|---|---|---|---|---|---|---|")
        for u, v in t2["per_unit"].items():
            if not v.get("complete"):
                continue
            L.append(f"| {u} | {f(v['MAE'])} | {f(v['delta_obs_10_03'])} [{f(v['delta_obs_ci95'][0], 2)}, "
                     f"{f(v['delta_obs_ci95'][1], 2)}] | {f(v['delta_pred_10_03'])} | {v['mcnemar_b_10only']}:"
                     f"{v['mcnemar_c_03only']}, {f(v['mcnemar_p_one_sided'], 4)} | {f(v['delta_obs_10_13'])} | "
                     f"{f(v['delta_pred_10_13'])} | {v['slot_flips_any_T_p1']}/50 | {'yes' if v['pass'] else 'no'} |")
        pb = t2["pooled_B3_A3"]
        L.append(f"\nPooled B3 + A3 exact one-sided McNemar (T 1.0 -> 0.3, top-p 1): b:c = {pb['b']}:{pb['c']}, "
                 f"p = {f(pb['p'], 5)} (unadjusted 0.05: {pb['unadjusted_0.05']}; Bonferroni 0.05/7: "
                 f"{pb['bonferroni_0.05/7']}).")
    t3 = read_json(RESULTS_DIR / "test3.json") if (RESULTS_DIR / "test3.json").exists() else None
    L.append("\n## Test (3): collapsed-task margins\n")
    L.append("| task | margin (nats) | >= 4 | p_off pred T0.3 / T1.0 / T1.3 (top-p 1) | dPred 1.3-0.3 | bound check "
             "(T 1.3, n off / n vs logit) | T 1.3 check off / N | 48-token LLR |")
    L.append("|---|---|---|---|---|---|---|---|")
    for t, v in ((t3 or {}).get("per_task") or {}).items():
        p = v["pred_p_off"]
        b = v["bound_check"]
        L.append(f"| {t} | {f(v['margin_nats'], 2)} | {'yes' if v['pass'] else 'no'} | {f(p['T0.3_p1'], 4)} / "
                 f"{f(p['T1.0_p1'], 4)} / {f(p['T1.3_p1'], 4)} | {f(v['delta_pred_13_03'], 4)} | {b['n_off']}/{b['n']} "
                 f"vs {f(b['logit_based_T13'], 4)}{' OVERSTATED' if b['overstated'] else ''} | "
                 f"{v['check_T13']['n_off_catalogue']}/{v['check_T13']['n']} | {f(v['llr48'], 2)} |")
    vd = read_json(RESULTS_DIR / "verdict.json") if (RESULTS_DIR / "verdict.json").exists() else None
    if vd:
        L.append(f"\n## Verdict: **{vd['verdict']}** (passes {vd['passes']}; disconfirming branches "
                 f"{vd['disconfirming']}; secondary raw p {f(vd['secondary_raw_p_pooled_mcnemar'], 5)})\n")
    for name in ("s4a", "s4b"):
        p = RESULTS_DIR / f"{name}.json"
        if p.exists():
            L.append(f"\n## {name.upper()}\n")
            L.append("```json\n" + json.dumps({u: {k: v for k, v in r.items() if k not in ("per_direction", "arms")}
                                                for u, r in read_json(p).items()}, indent=1, default=str)[:4000] +
                     "\n```")
    p = RESULTS_DIR / "table_1ac.json"
    if p.exists():
        T = read_json(p)
        L.append("\n## 1a-c: ideas x phrasings per cell (correct-only Hill-1 rarefied at depth 25; phrasing clusters "
                 "= identifier-normalised AST 4-gram Jaccard >= 0.8, single linkage)\n")
        L.append("| unit | cell | ideas (correct) | Hill-1@25 | phrasing clusters per idea (theta 0.8) | "
                 "10 literal trajectories: ideas | their phrasing clusters |")
        L.append("|---|---|---|---|---|---|---|")
        for u, v in T.items():
            for c, r in v["cells"].items():
                ph = {i: x["theta0.8"]["single"] for i, x in r["phrasing_clusters"].items()}
                L.append(f"| {u} | {c} | {r['ideas_correct']} | {f(r['hill1_correct_rarefied25'], 2)} | {ph} | "
                         f"{r['ten_trajectories']['ideas']} | {r['ten_trajectories']['phrasing_clusters_theta0.8']} |")
            L.append(f"| {u} | per-slot idea changes across T | {v['per_slot_idea_changes']} | | | | |")
    out = "\n".join(L) + "\n"
    (RESULTS_DIR / "summary.md").write_text(out)
    return out


if __name__ == "__main__":
    print(main()[:3000])
