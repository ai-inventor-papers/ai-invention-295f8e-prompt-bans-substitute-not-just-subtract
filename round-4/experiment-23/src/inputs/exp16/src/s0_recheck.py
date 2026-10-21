#!/usr/bin/env python3
"""S0.5 labeller re-check (before any GPU work; rules are never edited).

Bench: for each task, the frozen labeller (runtime primary, AST second) on references/*.py (both labellers must
name the file's mode and the reference must pass: 100% required) and on gold_set.jsonl (no judge needed: gold rows
are already adjudicated). Recomputed runtime-vs-adjudicated and runtime-vs-AST raw agreement must equal gate.json's
recorded values within 0.02. T1/T2: exp8's suite labeller on its gold set and 22 references (exp8: 0.965, 22/22).
"""

from __future__ import annotations

import collections
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from cfg import BENCH, E8, RESULTS_DIR, STAGE_A, TASK_DIR, read_json, read_jsonl, write_json
from labelq import bench_mechanical, label_path_texts

TOL = 0.02


def _fence(code: str) -> str:
    return "```python\n" + code.rstrip("\n") + "\n```"


def recheck_bench() -> dict[str, Any]:
    out = {}
    from concurrent.futures import ThreadPoolExecutor

    for t in STAGE_A:
        d = BENCH / TASK_DIR[t]
        refs = sorted((d / "references").glob("*.py"))
        gold = read_jsonl(d / "gold_set.jsonl")
        gate = read_json(d / "gate.json")
        items = [(t, _fence(p.read_text())) for p in refs] + [(t, _fence(g["code"])) for g in gold]
        with ThreadPoolExecutor(max_workers=5) as ex:
            mech = list(ex.map(lambda it: bench_mechanical(*it), items))
        rm, gm = mech[:len(refs)], mech[len(refs):]
        ref_rows = [{"file": p.name, "mode": p.stem, "runtime": m["runtime_label"], "ast": m["ast_label"],
                     "passed": m["passed"], "ok": m["runtime_label"] == p.stem and m["ast_label"] == p.stem and m["passed"]}
                    for p, m in zip(refs, rm)]
        same_rt = [m["runtime_label"] == g["runtime"] for g, m in zip(gold, gm)]
        same_ast = [m["ast_label"] == g["ast"] for g, m in zip(gold, gm)]
        resolved = [(g, m) for g, m in zip(gold, gm) if g.get("adjudicated") not in (None, "unresolved")]
        rt_vs_adj = float(np.mean([m["runtime_label"] == g["adjudicated"] for g, m in resolved])) if resolved else float("nan")
        raw_agree = float(np.mean([m["runtime_label"] == m["ast_label"] for m in gm])) if gm else float("nan")
        g0 = gate["gold"]
        ok_refs = all(r["ok"] for r in ref_rows)
        ok_adj = abs(rt_vs_adj - g0["runtime_vs_adjudicated"]) <= TOL
        ok_raw = abs(raw_agree - g0["raw_agreement"]) <= TOL
        out[t] = {"references_ok": sum(r["ok"] for r in ref_rows), "references_n": len(ref_rows),
                  "references": ref_rows, "gold_n": len(gold), "runtime_vs_adjudicated": rt_vs_adj,
                  "gate_runtime_vs_adjudicated": g0["runtime_vs_adjudicated"], "raw_agreement_rt_ast": raw_agree,
                  "gate_raw_agreement": g0["raw_agreement"], "same_runtime_as_recorded": float(np.mean(same_rt)),
                  "same_ast_as_recorded": float(np.mean(same_ast)),
                  "pass": bool(ok_refs and ok_adj and ok_raw)}
        logger.info(f"recheck {t}: refs {out[t]['references_ok']}/{len(ref_rows)}, rt-vs-adj {rt_vs_adj:.3f} "
                    f"(gate {g0['runtime_vs_adjudicated']:.3f}), rt-ast {raw_agree:.3f} (gate {g0['raw_agreement']:.3f}), "
                    f"same-as-recorded rt {out[t]['same_runtime_as_recorded']:.2f} ast {out[t]['same_ast_as_recorded']:.2f}"
                    f" -> {'PASS' if out[t]['pass'] else 'FAIL'}")
    return out


def _ref_mode(task: str, fname: str) -> str:
    stem = Path(fname).stem
    if task == "t1":
        for pre, m in (("astar", "astar_gbfs"), ("gbfs", "astar_gbfs"), ("bibfs", "bibfs"), ("bfs", "bfs"),
                       ("iddfs", "iddfs"), ("dfs", "dfs"), ("dijkstra", "dijkstra")):
            if stem.startswith(pre):
                return m
    else:
        for pre, m in (("bidijkstra", "bidijkstra"), ("bidir", "bidijkstra"), ("dijkstra", "dijkstra"),
                       ("bf", "bf_spfa"), ("bellman", "bf_spfa"), ("spfa", "bf_spfa"), ("floyd", "floyd"),
                       ("dial", "dial")):
            if stem.startswith(pre):
                return m
    return stem


def recheck_suite() -> dict[str, Any]:
    gold = read_jsonl(E8 / "suite" / "labeller" / "gold_set.jsonl")
    res = label_path_texts([(g["task"], _fence(g["code"])) for g in gold], use_judge=True)
    rows = [{"adjudicated": g["adjudicated"], "combined": r["label"], "runtime": r["runtime_label"],
             "source": r["labeller_source"]} for g, r in zip(gold, res)]
    resolved = [r for r in rows if r["adjudicated"] != "unresolved"]
    acc = float(np.mean([r["combined"] == r["adjudicated"] for r in resolved])) if resolved else float("nan")
    refs = []
    for task, sub in (("t1", "t1_grid"), ("t2", "t2_wsp")):
        for p in sorted((E8 / "suite" / "tasks" / sub / "references").glob("*.py")):
            refs.append({"task": task, "file": p.name, "code": p.read_text(), "mode": _ref_mode(task, p.name)})
    rres = label_path_texts([(r["task"], _fence(r["code"])) for r in refs], use_judge=True)
    exp8_refs = {r["file"]: r["mode"] for r in read_json(E8 / "results" / "labeller_recheck.json")["references"]}
    ref_ok = []
    for r, x in zip(refs, rres):
        mode = exp8_refs.get(f"{r['task']}/{r['file']}", r["mode"])
        ref_ok.append({"file": f"{r['task']}/{r['file']}", "mode": mode, "label": x["label"], "passed": x["passed"],
                       "ok": x["label"] == mode and x["passed"]})
    n_ok = sum(r["ok"] for r in ref_ok)
    out = {"gold_n": len(rows), "gold_n_resolved": len(resolved), "acc_combined_vs_adjudicated": acc,
           "exp8_acc": 0.9645390070921985, "within_tol": bool(abs(acc - 0.9645390070921985) <= TOL),
           "references_ok": n_ok, "references_n": len(ref_ok), "references": ref_ok,
           "label_sources": dict(collections.Counter(r["source"] for r in rows)),
           "pass": bool(abs(acc - 0.9645390070921985) <= TOL and n_ok == len(ref_ok))}
    logger.info(f"suite recheck: combined vs adjudicated {acc:.3f} (exp8 0.965), refs {n_ok}/{len(ref_ok)}")
    return out


def stage_recheck() -> dict[str, Any]:
    bench = recheck_bench()
    suite = recheck_suite()
    out = {"bench": bench, "suite_t1_t2": suite,
           "bench_all_pass": all(v["pass"] for v in bench.values()),
           "failed_tasks": [t for t, v in bench.items() if not v["pass"]], "suite_pass": suite["pass"]}
    write_json(RESULTS_DIR / "labeller_recheck.json", out)
    logger.info(f"labeller recheck: bench all pass={out['bench_all_pass']} failed={out['failed_tasks']}; "
                f"suite pass={suite['pass']}")
    return out


if __name__ == "__main__":
    from cfg import setup_logging

    setup_logging("s0_recheck")
    stage_recheck()
