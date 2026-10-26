#!/usr/bin/env python3
"""Markdown tables for README.md, generated from results/*.json (never hand-copied numbers)."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
R = ROOT / "results"
TASKS = ["T03", "T05", "T06", "T10", "T1", "T2"]
SITES = ["S0", "S1", "S2", "S3", "S4", "S5"]


def rj(n: str):
    p = R / n
    return json.loads(p.read_text()) if p.exists() else None


def f(x, d=2):
    if x is None:
        return "n/a"
    if isinstance(x, float) and (math.isinf(x)):
        return "not reached"
    if isinstance(x, float) and math.isnan(x):
        return "n/a"
    return f"{x:.{d}f}" if isinstance(x, (float, int)) else str(x)


def c1_table() -> str:
    c1 = rj("c1_site.json")
    lines = ["| Task (default) | " + " | ".join(f"H5 {s}" for s in SITES) + " | best | D_t = H5(S0) - max other [95% CI] "
             "| P(S0 argmax) |", "|---" * (len(SITES) + 4) + "|"]
    from cfg import DEFAULT

    for t in TASKS:
        p = c1["per_task"].get(t)
        if not p:
            continue
        ci = p.get("D_t_ci95")
        lines.append(f"| {t} ({DEFAULT[t]}) | " + " | ".join(f(p["H5"].get(s)) for s in SITES) +
                     f" | {c1['best_site'].get(t) or 'tie'} | {f(p['D_t'])} [{f(ci[0]) if ci else 'n/a'}, "
                     f"{f(ci[1]) if ci else 'n/a'}] | {f(p.get('P_S0_argmax_boot'))} |")
    return "\n".join(lines)


def p15_table() -> str:
    c1 = rj("c1_site.json")
    lines = ["| Task | " + " | ".join(f"P15 {s}" for s in SITES) + " | " + " | ".join(f"P20 {s}" for s in SITES) + " |",
             "|---" * (2 * len(SITES) + 1) + "|"]
    for t in TASKS:
        p = c1["per_task"].get(t)
        if not p:
            continue
        lines.append(f"| {t} | " + " | ".join(f(p["P15"].get(s)) for s in SITES) + " | " +
                     " | ".join(f(p["P20"].get(s)) for s in SITES) + " |")
    return "\n".join(lines)


def cells_table(alpha: int) -> str:
    c = rj("cells.json")
    lines = [f"| Task | twin pass / off(correct) / Hill | " + " | ".join(
        f"{s}: pass / off(correct) / Hill / invalid" for s in SITES) + " |", "|---" * (len(SITES) + 2) + "|"]
    for t in TASKS:
        tw = c.get(f"{t}|TWIN|0", {})
        row = [f"{f(tw.get('pass_rate'))} / {f(tw.get('off_share_correct'))} / {f(tw.get('hill_correct'))}"]
        for s in SITES:
            x = c.get(f"{t}|{s}|{alpha}")
            row.append("n/a" if not x else f"{f(x['pass_rate'])} / {f(x['off_share_correct'])} / "
                                           f"{f(x['hill_correct'])} / {f(x['invalid_rate'])}")
        lines.append(f"| {t} | " + " | ".join(row) + " |")
    return "\n".join(lines)


def failure_table() -> str:
    fm = rj("failure_modes.json")["per_task_site"]
    lines = ["| Site | " + " | ".join(TASKS) + " |", "|---" * (len(TASKS) + 1) + "|"]
    for s in SITES:
        modes = [fm.get(f"{t}|{s}", {}).get("mode", "n/a") for t in TASKS]
        modes = ["weak movement†" if m.startswith("unclassified") else m for m in modes]
        lines.append(f"| {s} | " + " | ".join(modes) + " |")
    lines.append("")
    lines.append("† Not covered by the frozen rule (0.10 <= correct-only excess < 0.20 with pass >= 0.8 x twin); "
                 "reported as 'unclassified (weak movement)' in the JSON.")
    return "\n".join(lines)


def boundary_table() -> str:
    b = rj("boundary.json")["per_task"]
    lines = ["| Task | alpha: pass / invalid / Hill(correct) |", "|---|---|"]
    for t in TASKS:
        cv = b.get(t, {}).get("curve", [])
        lines.append(f"| {t} | " + "; ".join(f"{x['alpha']:g}: {f(x['pass'])} / {f(x['invalid'])} / "
                                            f"{f(x['hill_correct'])}" for x in cv) + " |")
    return "\n".join(lines)


def c3d_table() -> str:
    c = rj("c3d.json")
    lines = ["| Arm (T1, k 0-9) | n | correct | avoidance of TOP5 [Wilson 95%] | K=7 landing (bibfs / idastar) | "
             "D_obs, p_edge / p_opp | correct composition (K=7) |", "|---|---|---|---|---|---|---|"]
    for arm, v in c["by_arm"].items():
        k = v.get("k7", {})
        ci = k.get("avoidance_ci")
        lines.append(f"| {arm} | {v.get('n')} | {k.get('n_correct')} | {f(k.get('avoidance'))} "
                     f"[{f(ci[0]) if ci else 'n/a'}, {f(ci[1]) if ci else 'n/a'}] | {k.get('landing_counts')} | "
                     f"{f(k.get('D_obs'))}, {f(k.get('p_edge'))} / {f(k.get('p_opp'))} | "
                     f"{k.get('composition_correct')} |")
    return "\n".join(lines)


def flips_table(alpha: int = 2) -> str:
    pf = rj("paired_flips.json")
    lines = ["| Site vs S0 | " + " | ".join(TASKS) + " |", "|---" * (len(TASKS) + 1) + "|"]
    for s in SITES[1:]:
        row = []
        for t in TASKS:
            r = pf.get(f"{t}|{s}|{alpha}")
            if not r:
                row.append("n/a")
                continue
            tb = r["table_attempts[both,S0only,siteonly,neither]"]
            row.append(f"{tb[1]}:{tb[2]} (p={r['mcnemar_p_attempts']:.2g}; id={r['byte_identical_vs_twin']:.2f})")
        lines.append(f"| {s} | " + " | ".join(row) + " |")
    return "\n".join(lines)


if __name__ == "__main__":
    which = sys.argv[1]
    print({"c1": c1_table, "p15": p15_table, "fail": failure_table, "boundary": boundary_table, "c3d": c3d_table,
           "flips": flips_table}.get(which, lambda: cells_table(int(which)))())
