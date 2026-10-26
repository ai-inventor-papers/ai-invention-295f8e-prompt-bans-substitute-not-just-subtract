#!/usr/bin/env python3
"""Run every committed analysis (src/analysis7.py, src/m7.py) and write results/*.json, results/summary.md and the
figures. Usage: .venv/bin/python src/report7.py [--tasks T2,T10,T03]"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger

import analysis7 as A
import figures7 as F
from cfg import ROOT, read_json, read_jsonl, setup_logging, write_json
from cfg7 import CATALOGUE7, DEFAULT7, LABELS7, RANKS, results7


def fmt(x: Any, nd: int = 2) -> str:
    if x is None:
        return "-"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def cell_table(task: str) -> list[dict[str, Any]]:
    from collections import Counter
    rows = [r for r in read_jsonl(LABELS7) if r["task"] == task and r.get("stage") in ("gen", "r", "mgen")]
    by = {}
    for r in rows:
        by.setdefault(r["arm"], []).append(r)
    out = []
    for arm, rs in sorted(by.items()):
        corr = Counter(r["label"] for r in rs if r.get("passed"))
        out.append({"arm": arm, "n": len(rs), "pass": sum(bool(r.get("passed")) for r in rs) / len(rs),
                    "correct_composition": dict(corr.most_common()),
                    "n_length": sum(r.get("finish_reason") == "length" for r in rs)})
    return out


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="T2,T10,T03")
    args = ap.parse_args()
    setup_logging("report7")
    tasks = [t for t in args.tasks.split(",") if results7(f"kstar_{t}.json").exists()]
    core = [t for t in tasks if t in ("T2", "T10")]
    A.FIT["name"] = "MAIN_LY"
    p1 = A.p1_all(tasks)
    write_json(results7("p1.json"), p1)
    ctrl = {t: A.controls(t) for t in tasks}
    for t, c in ctrl.items():
        write_json(results7(f"p1_controls_{t}.json"), c)
    rt = {t: A.routing(t, p1["tasks"][t].get("P1_k")) for t in tasks}
    landing = {t: read_json(results7(f"targets_{t}.json"))["landing"] for t in tasks}
    cv = A.c_verdict(rt, landing)
    write_json(results7("c_routing.json"), {"per_task": rt, "verdict": cv})
    dm = {}
    for t in tasks:
        try:
            dm[t] = A.dormant(t, p1["tasks"][t])
        except (FileNotFoundError, KeyError) as e:
            logger.warning(f"dormant {t}: {e}")
    write_json(results7("dormant.json"), dm)
    pilot = {t: A.pilot_main(t) for t in core}
    write_json(results7("committed_map_pilot.json"), pilot)
    rr = A.r_discreteness("T2") if "T2" in tasks else None
    if rr:
        write_json(results7("r_discreteness.json"), rr)
    m = None
    if (ROOT / "cache" / "m_states_T2.npz").exists():
        import m7
        m = m7.analyse("T2")
        write_json(results7("m_manifold.json"), m)
    mg = A.mgen_summary("T2") if "T2" in tasks else None
    if mg:
        write_json(results7("m_behaviour.json"), mg)
    s2 = A.seed2_summary("T2") if "T2" in tasks else None
    if s2:
        write_json(results7("seed2_summary.json"), s2)
    cells = {t: cell_table(t) for t in tasks}
    write_json(results7("cells.json"), cells)
    # figures
    for fn, a in ((F.f1, (tasks,)), (F.f2, (p1, tasks)), (F.f3, (rt,)), (F.f7, (dm,)), (F.f8, (tasks,))):
        try:
            fn(*a)
        except Exception as e:  # noqa: BLE001 - a figure failure must not stop the report
            logger.exception(f"figure {fn.__name__} failed: {e}")
    if m:
        for fn in (F.f4, F.f5):
            try:
                fn(m)
            except Exception as e:  # noqa: BLE001
                logger.exception(f"figure {fn.__name__} failed: {e}")
    if rr:
        try:
            F.f6(rr)
        except Exception as e:  # noqa: BLE001
            logger.exception(f"figure f6 failed: {e}")
    logger.info(f"P1 overall {p1['overall']}; C {cv['verdict']}")
    print(json.dumps({"P1": {t: p1["tasks"][t].get("P1") for t in tasks}, "overall": p1["overall"],
                      "C": cv["verdict"]}, indent=1))


if __name__ == "__main__":
    main()
