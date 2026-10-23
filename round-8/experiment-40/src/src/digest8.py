#!/usr/bin/env python3
"""Auto-generated tables (results/summary.md) straight from the result JSONs: per (unit, site) teacher-forced recovery
by rank and class, controls c1-c7, generation cells per class, verdicts, K2, mediation. No number is typed by hand.

Usage: python src/digest8.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg8 import RESULTS, read_json


def f(x: Any, nd: int = 2) -> str:
    if x is None:
        return "n/a"
    if isinstance(x, bool):
        return "PASS" if x else "FAIL"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def tf_block(name: str, d: dict[str, Any], rinit: dict[str, Any] | None) -> list[str]:
    L = [f"### {name}: teacher-forced (held-out pairs)", ""]
    L.append(f"L* = {d.get('L_star', 'band')}, k* = {d['k_star']}, held-out recovery at k* = {f(d['main']['recovery'])} "
             f"(95% two-way cluster CI {f(d['main']['ci95'][0])} to {f(d['main']['ci95'][1])}); mean DAS Delta "
             f"{f(d['main']['mean_delta_edit'])} nats vs full-state {f(d['main']['mean_delta_full'])} nats; "
             f"OFF-MANIFOLD flag: {d.get('off_manifold_flag')}")
    L += ["", "| rank | recovery (seed 0) | " + " | ".join(f"by class: {c}" for c in
                                                                   (d['recovery_by_rank']['1'].get('by_class') or {})) + " |",
          "|---|---|" + "---|" * len(d['recovery_by_rank']['1'].get('by_class') or {})]
    for k in ("1", "2", "4", "8"):
        r = d["recovery_by_rank"][k]
        bc = r.get("by_class") or {}
        L.append(f"| {k} | {f(r['recovery'])} | " + " | ".join(f(v.get('recovery')) for v in bc.values()) + " |")
    c = d
    L += ["", "| control | statistic | threshold | result |", "|---|---|---|---|"]
    ks = str(d["k_star"])
    c1 = c["c1"].get(ks, {})
    L.append(f"| c1 random subspaces (k*) | median {f(c1.get('median'), 3)}, p95 {f(c1.get('p95'), 3)} | median <= 0.05 | "
             f"{f(all(v['pass'] for v in c['c1'].values()))} |")
    for nm, v in c["c2"].items():
        if isinstance(v, dict) and "ratio_to_true_fit" in v:
            L.append(f"| c2 label control {nm} | ratio to true fit {f(v['ratio_to_true_fit'])} | <= 0.10 | {f(v['pass'])} |")
    if rinit:
        L.append(f"| c3 random-init network | ratio {f(rinit.get('ratio'))} (trained {f(rinit.get('mean_delta_trained'))} "
                 f"vs random-init {f(rinit.get('mean_delta_rinit'))} nats) | <= 0.25 | {f(rinit.get('pass'))} |")
    else:
        L.append("| c3 random-init network | not run | <= 0.25 | n/a |")
    L.append(f"| c4 reverse interchange | {f(c['c4'].get('recovery'))} ({c['c4'].get('n_pairs')} pairs) | >= 0.5 | "
             f"{f(c['c4'].get('pass'))} |")
    L.append(f"| c5 projection on 64 twin PCs | retention {f(c['c5']['twins'].get('retention'))} | >= 0.5 | "
             f"{f(c['c5'].get('pass'))} |")
    L.append(f"| c5b (twins + forced + bans basis) | retention {f(c['c5']['twins_forced_bans'].get('retention'))} | "
             f">= 0.5 | {f(c['c5'].get('pass_b'))} |")
    L.append(f"| c6 natural-variance share | {f(c['c6']['twins']['share'], 4)} vs random p95 "
             f"{f(c['c6']['twins']['random_p95'], 4)} | > p95 | {f(c['c6']['twins']['pass'])} |")
    L.append(f"| c7 seed principal cosine | median first cosine {f(c['c7'].get('median_first_cosine'))} (random p99 "
             f"{f(c['c7'].get('random_p99'))}) | >= 0.5 and > p99 | {f(c['c7'].get('pass'))} |")
    return L + [""]


def gen_block(name: str, g: dict[str, Any]) -> list[str]:
    L = [f"### {name}: generation (CRN slots; correct = target-class label AND hidden tests pass)", ""]
    for c, v in g["classes"].items():
        L.append(f"Target class **{c}**: generation recovery {f(v['gen_recovery'])}, pass ratio DAS/BASE "
                 f"{f(v['pass_ratio_DAS_vs_BASE'])}, McNemar DAS vs RAND {v['mcnemar_DAS_vs_RAND']}")
        L += ["", "| arm | n | correct target | attempted target | pass rate | labels |", "|---|---|---|---|---|---|"]
        for arm, t in v["arms"].items():
            L.append(f"| {arm} | {t['n']} | {t['correct_target']} | {t['attempted_target']} | {f(t['pass_rate'])} | "
                     f"{t['labels']} |")
        if v.get("reverse"):
            L.append(f"\nReverse (restored twin-class programs): {v['reverse']}")
        L.append("")
    return L


def main() -> None:
    an = read_json(RESULTS / "analysis.json")
    L = ["# Auto-generated result tables (src/digest8.py)", ""]
    for key, path, rpath in (("T10 decision site (Qwen3-8B)", "dec_T10.json", "rinit_T10.json"),
                             ("T10 task band (Qwen3-8B)", "band_T10.json", "rinit_T10_band.json"),
                             ("GRID decision site (gemma-3-4b-it)", "dec_GRID.json", "rinit_GRID.json"),
                             ("T10 decision site at block 24 (POST HOC sensitivity)", "dec_T10_L24.json", None)):
        p = RESULTS / path
        if p.exists():
            r = read_json(RESULTS / rpath) if rpath and (RESULTS / rpath).exists() else None
            L += tf_block(key, read_json(p), r)
    for k, v in an.items():
        if k.startswith("gen_"):
            L += gen_block(k.replace("gen_", ""), v)
    L += ["## Verdicts", "", "| unit-site | verdict | V0 | failed controls | untested |", "|---|---|---|---|---|"]
    for k, v in an.get("verdicts", {}).items():
        L.append(f"| {k} | {v.get('verdict')} | {f(v.get('V0'))} | {v.get('failed_controls')} | "
                 f"{v.get('untested_controls')} |")
    L += ["", f"K2: **{an.get('K2', {}).get('status')}**, p_K2 = {f(an.get('K2', {}).get('p_K2'), 4)}", ""]
    if an.get("mediation"):
        L += ["## Mediation (T10)", "", "```", str(an["mediation"])[:3000], "```"]
    (RESULTS / "summary.md").write_text("\n".join(L))
    print("\n".join(L)[:6000])


if __name__ == "__main__":
    main()
