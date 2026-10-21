#!/usr/bin/env python3
"""Figures (aii-data-fig-gen JSON specs, rendered deterministically) + the veto re-emergence table."""

from __future__ import annotations

import collections
import json
import subprocess
from pathlib import Path

import numpy as np
from loguru import logger

from src.ws import DATA, FIGS, PRED, RESULTS, WS, read_json, read_jsonl

def _skills_dir() -> Path:
    import os

    env = os.environ.get("AII_SKILLS_DIR")
    if env:
        return Path(env)
    for parent in [WS, *WS.parents]:
        if (parent / ".claude" / "skills" / "aii-data-fig-gen").is_dir():
            return parent / ".claude" / "skills"
    raise FileNotFoundError("set AII_SKILLS_DIR to the folder holding aii-data-fig-gen")


GEN = _skills_dir() / "aii-data-fig-gen" / "scripts" / "chart_gen.py"


def _render(spec: dict, name: str) -> None:
    sp = FIGS / f"{name}.json"
    sp.write_text(json.dumps(spec, indent=1))
    r = subprocess.run([str(WS / ".venv" / "bin" / "python"), str(GEN), "--spec", str(sp), "--out", str(FIGS / name)],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        logger.error(f"figure {name} failed: {r.stderr[-800:]}")
    else:
        logger.info(f"figure {name} written")


def landings() -> None:
    rows = read_jsonl(RESULTS / "c1_events.jsonl")
    cats, banned, hit, surv, other, = [], [], [], [], []
    for r in rows:
        lc = r["landing_counts"]
        n = sum(lc.values()) or 1
        X = r["banned"]
        h = r.get("hit_label")
        cats.append(r["event_id"].replace("|modal|", " ban ").replace("|present_minor|", " ban* "))
        nb = lc.get(X, 0)
        nh = lc.get(h, 0) if h and h not in (X, "other") else 0
        no = lc.get("other", 0)
        banned.append(nb)
        hit.append(nh)
        other.append(no)
        surv.append(max(sum(lc.values()) - nb - nh - no, 0))
    spec = {"type": "stacked_pct", "title": "Where Llama lands under each ban (attempted programs; * = present-minor)",
            "xlabel": "Event (task, banned algorithm)", "aspect": "16:9", "categories": cats,
            "series": [{"label": "banned X (not avoided)", "values": banned},
                       {"label": "modal/excess survivor (hit label)", "values": hit},
                       {"label": "other survivors", "values": surv}, {"label": "'other' (off-catalogue)", "values": other}]}
    _render(spec, "fig1_ban_landings")


def forest() -> None:
    rows = [r for r in read_jsonl(RESULTS / "c1_events.jsonl") if r["gate_pass"]]
    pairs = [("SUBTRACT", "ASSOCIATE"), ("SUBTRACT", "PROXIMITY"), ("LADDER", "ASSOCIATE"), ("LADDER", "PROXIMITY")]
    rng = np.random.default_rng(0)
    cats, vals, lo, hi = [], [], [], []
    for a, b in pairs:
        d = [(r["task"], r["logscore"][a] - r["logscore"][b]) for r in rows
             if r["logscore"].get(a) is not None and r["logscore"].get(b) is not None]
        if not d:
            continue
        tasks = sorted({t for t, _ in d})
        boots = []
        for _ in range(2000):
            tk = rng.choice(tasks, size=len(tasks), replace=True)
            boots.append(np.mean([x for t in tk for (tt, x) in d if tt == t]))
        m = float(np.mean([x for _, x in d]))
        cats.append(f"{a} - {b} (n={len(d)})")
        vals.append(round(m, 4))
        lo.append(round(m - float(np.percentile(boots, 2.5)), 4))
        hi.append(round(float(np.percentile(boots, 97.5)) - m, 4))
    if not cats:
        return
    spec = {"type": "forest", "null_line": 0.0, "title": "Family log-score differences on gated events (task-cluster bootstrap)",
            "xlabel": "Log-score difference (nats)",
            "aspect": "4:3", "categories": cats,
            "series": [{"values": vals, "errors": [round(max(l, h), 4) for l, h in zip(lo, hi)]}]}
    (RESULTS / "forest_cis.json").write_text(json.dumps({c: {"mean": v, "ci_lo": v - l, "ci_hi": v + h}
                                                         for c, v, l, h in zip(cats, vals, lo, hi)}, indent=1))
    try:
        _render(spec, "fig2_logscore_forest")
    except Exception as e:  # noqa: BLE001
        logger.error(f"forest failed: {e}")


def baseline_vs_pilot() -> None:
    labels = read_jsonl(DATA / "labels.jsonl")
    ev = read_json(PRED / "events.json")
    cats, pil, bf = [], [], []
    for t, v in ev["tasks"].items():
        D = v["D"]
        p = [r["label"] for r in labels if r["task"] == t and r.get("phase") == "pilot" and r["label"] != "invalid"]
        b = [r["label"] for r in labels if r["task"] == t and r.get("phase") in ("B1", "B4") and r["label"] != "invalid"]
        cats.append(f"{t} ({D})")
        pil.append(round(100 * p.count(D) / max(len(p), 1), 1))
        bf.append(round(100 * b.count(D) / max(len(b), 1), 1))
    spec = {"type": "bar", "title": "Share of the frozen default D: FP8 pilot vs bf16 neutral-twin baseline",
            "xlabel": "Task (default D)", "ylabel": "Share of attempted programs (%)", "aspect": "16:9",
            "categories": cats, "series": [{"label": "FP8 pilot (exp11, plain spec)", "values": pil},
                                           {"label": "bf16 neutral twins (B1+B4)", "values": bf}]}
    _render(spec, "fig3_baseline_vs_pilot")


def reemergence_table() -> None:
    vs = read_json(DATA / "veto_summary.json") if (DATA / "veto_summary.json").exists() else {}
    lines = ["| event | round | vetoed n-grams (decoded) | A share after veto | hit rows | hits in code | re-emergence imports |",
             "|---|--:|---|--:|--:|--:|---|"]
    for eid, v in vs.items():
        for r in v.get("rounds", []):
            imps = "; ".join(f"{a} ({b})" for a, b in r["surfaces"]["top_imports"][:3])
            dec = " + ".join(repr(d) for d in r["decoded"])
            lines.append(f"| {eid} | {r['round']} | {dec} | {r['A_share_weighted']:.2f} | {r['n_hit_rows']} | "
                         f"{r['hit_in_code_share']:.2f} | {imps} |")
    (RESULTS / "veto_reemergence_table.md").write_text("\n".join(lines) + "\n")


def run() -> None:
    for fn in (landings, forest, baseline_vs_pilot, reemergence_table):
        try:
            fn()
        except Exception as e:  # noqa: BLE001 - one failing figure must not block the others
            logger.error(f"{fn.__name__} failed: {e}")
