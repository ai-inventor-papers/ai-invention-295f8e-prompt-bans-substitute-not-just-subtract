#!/usr/bin/env python3
"""Markdown tables for the README, generated from results/*.json (so the README cannot disagree with them)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c6  # noqa: E402,F401
from c6 import RESULTS, read_json  # noqa: E402

ENGS = ("a", "b", "c", "d")
NAME = {"a": "a W8A8", "b": "b W8A16", "c": "c W16A8", "d": "d BF16"}


def f(x, nd=3):
    return "–" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def main() -> None:
    esc = read_json(RESULTS / "escape_by_engine.json")
    ver = read_json(RESULTS / "verdict.json")
    pair = read_json(RESULTS / "mcnemar.json")
    lines = ["### Escape fraction per engine (alpha 2, 40 directions, each engine against its own twin)", "",
             "| task | engine | twin off-default (k/n) | twin pass | screen passes | confirmed | E (Wilson 95%) | "
             "screen-level E | B |", "|---|---|---|---|---|---|---|---|---|"]
    for t in ("T10", "T2"):
        for e in ENGS:
            v = esc.get(e, {}).get(t)
            if not v:
                continue
            a2 = v["alpha"]["2.0"]
            E = f"{a2['E_t']:.3f} [{a2['E_wilson'][0]:.2f}, {a2['E_wilson'][1]:.2f}]" if a2["confirmation_complete"] \
                else f"incomplete ({a2['n_screen_pass_not_confirmed_tested']} screen passers below the full 30 pooled rows)"
            lines.append(f"| {t} | {NAME[e]} | {v['twin']['k_off']}/{v['twin']['n_valid']} | {v['twin']['pass']:.2f} | "
                         f"{a2['n_screen_pass']}/{a2['n_run']} | {a2['n_confirmed']} | {E} | {a2['E_screen']:.3f} | "
                         f"{'20' if e in ('a', 'b') else 'weight-set B'} |")
    lines += ["", "### Direction-paired engine contrasts (confirmed escapes; exact McNemar, Tango 90% CI, TOST 0.1)", "",
              "| task | pair | E_x | E_y | diff | n10/n01 | p (two-sided) | p Holm | 90% CI | TOST equiv. | kappa | "
              "Spearman share10 |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, v in pair.items():
        if k.count("|") != 2 or "n10" not in v:
            continue
        t, pr, lvl = k.split("|")
        if lvl != "confirmed":
            continue
        lines.append(f"| {t} | {pr} | {f(v['E_x'])} | {f(v['E_y'])} | {f(v['diff'])} | {v['n10']}/{v['n01']} | "
                     f"{f(v['p_two_sided'])} | {f(v.get('p_holm'))} | [{f(v['tango90'][0], 2)}, {f(v['tango90'][1], 2)}] | "
                     f"{v['tost_margin_0.1_equivalent']} | {f(v['kappa'], 2)} | {f(v['spearman_share10'], 2)} |")
    lines += ["", "### Verdict (COMMIT #0 table; literal reading leads)", ""]
    for t in ("T10", "T2"):
        v = ver[t]
        lines.append(f"- **{t}: {v['literal_verdict']}**. E(a, b, c, d) = {v['E_alpha2']}. Screen-level reading: "
                     f"{v['screen_level_verdict']} with {v['E_screen_alpha2']}. Iteration-4 E(a), relabelled: "
                     f"{v['E_iter4_relabelled_a']}.")
        if "feasibility_reading" in v:
            lines.append(f"  - T2 feasibility reading: {v['feasibility_reading']['verdict']} "
                         f"({v['feasibility_reading']['clauses']})")
    lines.append(f"- Claim-level: {ver['claim']}")
    pn = read_json(RESULTS / "pn.json") if (RESULTS / "pn.json").exists() else {}
    if pn:
        lines += ["", "### Per-sample plan noise (exp19 slots, N = 50 per cell, absolute unit)", "",
                  "| task | arm | exp19 FP8 (iteration 4) | a | b | c | d |", "|---|---|---|---|---|---|---|"]
        for t in ("T10", "T2"):
            for a in ("PN_a1", "PN_a2"):
                c = pn.get(t, {}).get(a, {})
                cells = []
                for e in ("exp19_fp8",) + ENGS:
                    v = c.get(e)
                    cells.append("–" if not v else f"{v['k_off']}/{v['n_valid']} ({v['share']:.2f})")
                lines.append(f"| {t} | {a} | " + " | ".join(cells) + " |")
    sf = read_json(RESULTS / "slot_flips.json") if (RESULTS / "slot_flips.json").exists() else {}
    if sf:
        lines += ["", "### CRN-paired screen slots under the alpha-2 pushes (k 0-1 of all 40 directions; same direction, "
                  "template, k and uniforms in both engines)", "",
                  "| task | pair | slots | off-default x | off-default y | discordant x:y | exact McNemar p | same label |",
                  "|---|---|---|---|---|---|---|---|"]
        for k, v in sf.items():
            if k.count("|") != 1:
                continue
            t, pr = k.split("|")
            lines.append(f"| {t} | {pr} | {v['n_slots']} | {v['offdefault_x']:.3f} | {v['offdefault_y']:.3f} | "
                         f"{v['n10']}:{v['n01']} | {v['p_two_sided']:.2g} | {v['same_label_frac']:.3f} |")
    rt = read_json(RESULTS / "relabel_table.json") if (RESULTS / "relabel_table.json").exists() else []
    if rt:
        lines += ["", "### Relabel table: earlier internal results -> the numerics class that reproduces them", "",
                  "| earlier result | class | deciding cells |", "|---|---|---|"]
        for r in rt:
            lines.append(f"| {r['iteration4_result']} | **{r['class']}** | {r['deciding_cells']} |")
    ds = read_json(RESULTS / "diagnostics_summary.json") if (RESULTS / "diagnostics_summary.json").exists() else {}
    if ds.get("KL_vs_bf16") or ds.get("FIDELITY"):
        lines += ["", "### Teacher-forced diagnostics", "", "| engine | task | mean KL(e || bf16) per token | argmax "
                  "disagreement with bf16 | FIDELITY median |logprob_sum diff| vs exp22 |", "|---|---|---|---|---|"]
        for e in ("a", "b", "c", "d"):
            for t in ("T10", "T2"):
                kl = ds.get("KL_vs_bf16", {}).get(e, {}).get(t, {})
                fi = ds.get("FIDELITY", {}).get(e, {}).get(t, {})
                if kl or fi:
                    lines.append(f"| {NAME[e]} | {t} | {f(kl.get('mean_kl_vs_bf16'), 4)} | "
                                 f"{f(kl.get('argmax_disagreement'), 4)} | {f(fi.get('median_abs_diff'), 3)} |")
        if ds.get("FIDELITY_rule"):
            lines.append(f"\nFIDELITY rule (median under a <= 0.25 x median under d): {ds['FIDELITY_rule']}")
        if ds.get("induced_ratio_to_d_median_blocks_13_35"):
            lines.append(f"\nInduced (non-nominal) perturbation, ratio to bf16, median over blocks 13-35: "
                         f"{ {k: (round(v, 3) if v is not None else None) for k, v in ds['induced_ratio_to_d_median_blocks_13_35'].items()} }")
    kn = read_json(RESULTS / "known_solutions.json") if (RESULTS / "known_solutions.json").exists() else {}
    if kn:
        lines += ["", f"### Nearest known solution (corpus: {kn['n_corpus']} code solutions from the declared dataset)", "",
                  "| engine/task | distinct correct off-default + 'other' programs | median max Jaccard | classes |",
                  "|---|---|---|---|"]
        for k, v in kn["per_engine_task"].items():
            lines.append(f"| {k.replace('|', ' / ')} | {v['n_distinct']} | {f(v['median_max_jaccard'])} | {v['classes']} |")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
