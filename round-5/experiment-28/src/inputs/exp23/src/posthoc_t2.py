#!/usr/bin/env python3
"""POST HOC (after commit #3; not part of the frozen analysis): mechanism re-audit of T2 programs labelled bf_spfa.

Finding that motivated it: the 60-program label audit (results/label_audit.json) disagreed on 3 of 4 T2 programs, and
reading them shows array-based Dijkstra (linear min-scan over unvisited nodes + a visited array, no heap), which the
frozen exp8 suite labeller returns as 'unknown' or 'bf_spfa' (its gate set had heap Dijkstra), and which the inline
judge then labelled bf_spfa. Mechanism-level labels count a disguised default as the default.

Here every T2 program labelled bf_spfa (all arms) is re-judged blind by google/gemini-2.5-flash with the frozen suite
judge prompt, and a deterministic structural rule is applied beside it (visited array + `dist[a] < dist[b]` min-scan,
no heapq / deque). T2's E_t (same escape rule) and A_t are recomputed under each relabelling and C3a is re-run with the
frozen analysis code. The primary result is unchanged; this is reported as a post-hoc sensitivity.
"""

from __future__ import annotations

import collections
import importlib.util
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (ALL_TASKS, DATA_DIR, PRED_DIR, RESULTS_DIR, bench_paths, read_json, read_jsonl, setup_logging,
                 write_json)

bench_paths()


def array_dijkstra(code: str | None) -> bool:
    if not code:
        return False
    return bool(re.search(r"visited", code)) and bool(re.search(r"dist\[\w+\]\s*<\s*dist\[\w+\]", code)) \
        and "heapq" not in code and "deque" not in code


def main() -> None:
    from loguru import logger

    import labeller.judge as J

    setup_logging("posthoc_t2")
    J.CACHE = DATA_DIR / "judge_cache_paths_posthoc.jsonl"
    J.COST_FILE = RESULTS_DIR / "openrouter_cost_paths_posthoc.json"
    labs = read_jsonl(DATA_DIR / "labels.jsonl")
    tgt = [r for r in labs if r["task"] == "T2" and r["label"] == "bf_spfa" and r.get("code")]
    res, stop = J.judge_many([{"task": "t2", "code": r["code"]} for r in tgt], "google/gemini-2.5-flash",
                             "posthoc_t2_relabel", 0.35)
    judge = {r["row_id"]: (x or {}).get("label") for r, x in zip(tgt, res)}
    heur = {r["row_id"]: array_dijkstra(r["code"]) for r in tgt}
    agree = collections.Counter((judge[k], heur[k]) for k in judge)
    logger.info(f"re-judged {len(tgt)} T2 bf_spfa programs; (judge, structural) = {dict(agree)}")

    spec = importlib.util.spec_from_file_location("analysis_c3_frozen", PRED_DIR / "analysis_c3.py")
    A = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(A)
    import predictors as PR

    pre = read_json(PRED_DIR / "commit_preban.json")
    bans = read_json(RESULTS_DIR / "bans.json")
    out: dict[str, Any] = {"n_rejudged": len(tgt), "judge_model": "google/gemini-2.5-flash", "stop": stop,
                           "judge_vs_structural": {f"{a}|{b}": v for (a, b), v in agree.items()}, "variants": {}}
    for name, relab in (("judge", {k: v for k, v in judge.items() if v}),
                        ("structural", {k: "dijkstra" for k, v in heur.items() if v})):
        newlabs = {r["row_id"]: ({**r, "label": relab.get(r["row_id"], r["label"])} if r["task"] == "T2" else r)
                   for r in labs}
        PR._LAB["x"] = newlabs
        conf = PR.confirm("T2")
        bt = [r for r in newlabs.values() if r["task"] == "T2" and r.get("stage") == "BAN" and r["arm"] == "ban"]
        S = set(pre["tasks"]["T2"]["survivors"])
        A_t2 = sum(1 for r in bt if r["label"] in S) / len(bt)
        comp = dict(collections.Counter(r["label"] for r in bt))
        E = {t: pre["tasks"][t]["E_t"] for t in ALL_TASKS}
        Av = {t: bans[t]["A_t"] for t in ALL_TASKS}
        mv = {t: bool(pre["tasks"][t]["movable"]) for t in ALL_TASKS}
        E["T2"], Av["T2"], mv["T2"] = conf["E_t"], A_t2, conf["E_t"] > 0
        r = A.c3a(list(ALL_TASKS), E, Av, mv, n_perm=20000, n_boot=1000)
        out["variants"][name] = {"T2_E_t": conf["E_t"], "T2_confirmed": conf["confirmed"], "T2_A_t": A_t2,
                                 "T2_ban_composition": comp, "n_relabelled": len(relab),
                                 "BA": r["balanced_accuracy"]["BA"], "fisher_p": r["fisher"]["p_two_sided"],
                                 "rho": r["spearman"]["rho"], "rho_p_one_sided": r["spearman"]["p_one_sided"],
                                 "verdict": r["verdict"], "table": r["fisher"]["table"]}
        logger.info(f"{name}: T2 E_t={conf['E_t']} A_t={A_t2:.2f} -> BA={r['balanced_accuracy']['BA']} "
                    f"rho={r['spearman']['rho']} {r['verdict']}")
    out["label"] = "POST HOC: not pre-registered; the frozen primary result stands as committed"
    write_json(RESULTS_DIR / "posthoc_t2_relabel.json", out)


if __name__ == "__main__":
    main()
