#!/usr/bin/env python3
"""Stages 1.6-1.8: top-up candidates (iteration 9's 600 forced top-ups re-adjudicated for bibfs / iddfs / jps /
biastar, plus any new v10 top-ups), the survivor families of the top-five ban (E45 k5 hand reads + iteration 8's
SURV programs) and the covert BFS/DFS set (E45 samples: banned BFS/DFS implemented with no banned alias in the code).
All go through the same acceptance pipeline (suites raw + scrubbed, scrub, alias audit, instrument).

Usage: python src/stage_sets.py topups | survivors | covert
"""

from __future__ import annotations

import random
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from loguru import logger  # noqa: E402

import programs  # noqa: E402
from accept import dedupe, pipeline  # noqa: E402
from common import alias_regex, read_json, read_jsonl, sha256_text, utc_now, write_jsonl  # noqa: E402
from tpg2 import DATA, IN45, IN46, RESULTS, write_json  # noqa: E402

TOPUP_ALGS = ["bibfs", "iddfs", "jps", "biastar"]


def _heuristic(code: str) -> bool:
    return bool(re.search(r"abs\(|heur|manh", code, re.IGNORECASE))


def jps_ratio(code: str) -> float | None:
    """Unique heap/container pops on the open probe grids relative to a BFS reference (expanded-set ratio)."""
    import instrument
    import orderclass

    P = [p for p in orderclass.probes() if p["family"] in ("open", "open_centre")]
    ref = (Path(__file__).resolve().parent.parent / "vendor/exp9/tasks/t1_grid/references/bfs_deque_parent.py").read_text()
    a = instrument.run_child(code, P, timeout_s=40)
    b = instrument.run_child(ref, P, timeout_s=40)
    ra = []
    for i in range(len(P)):
        if i in a and i in b:
            na = len({(e[1], e[2]) for e in (a[i].get("events") or []) if e[0] == 1})
            nb = len(instrument._useq(instrument._E(b[i])))
            if nb:
                ra.append(na / nb)
    return sum(ra) / len(ra) if ra else None


def auto_check(alg: str, r: dict[str, Any]) -> tuple[bool, str]:
    ins = r.get("instrument") or {}
    sc = r["scrubbed"]
    two = (ins.get("bidir_share") or 0) >= 0.5 or (ins.get("goal_early_share") or 0) >= 0.5
    if alg == "bibfs":
        ok = two and not _heuristic(sc)
        return ok, f"two-ended={two}, heuristic={_heuristic(sc)}"
    if alg == "biastar":
        rule, why = programs.ast_rule(sc, "biastar")
        ok = (two or rule) and _heuristic(sc)
        return ok, f"two-ended={two}, ast_rule={rule} ({why})"
    if alg == "iddfs":
        ok = (ins.get("id_share") or 0) >= 0.5 and not _heuristic(sc)
        return ok, f"id_share={ins.get('id_share')}, heuristic={_heuristic(sc)}"
    if alg == "jps":
        rule, why = programs.ast_rule(sc, "jps")
        ratio = jps_ratio(sc) if rule else None
        r["jps_expanded_ratio_open"] = ratio
        ok = bool(rule and ratio is not None and ratio <= 0.5)
        return ok, f"jump helper={rule}, expanded ratio vs BFS on open grids={ratio}"
    return False, "?"


def stage_topups() -> None:
    old = [r for r in read_jsonl(IN46 / "data" / "topups.jsonl") if r["algorithm"] in TOPUP_ALGS]
    new = [r for r in read_jsonl(DATA / "raw_topups_v10.jsonl")]
    rows = []
    for r in old:
        rows.append({**r, "uid": f"T9|{r['algorithm']}|{r['slot']}", "source": "E46 topups (iteration 9)",
                     "round": 0, "author": "qwen3-32b"})
    for r in new:
        rows.append({**r, "algorithm": r["cell"], "uid": f"T10|{r['cell']}|{r['slot']}",
                     "source": "v10 named top-up", "round": 1})
    rows = pipeline(rows)
    dedupe(rows)
    for r in rows:
        if r.get("valid"):
            ok, why = auto_check(r["algorithm"], r)
            r["auto_check"], r["auto_why"] = ok, why
    write_jsonl(DATA / "topup_candidates.jsonl", rows)
    c = Counter((r["algorithm"], r.get("valid", False), r.get("auto_check")) for r in rows)
    write_json(RESULTS / "topups_screen.json", {"counts": {str(k): v for k, v in sorted(c.items(), key=str)},
                                                "utc": utc_now()})
    for k, v in sorted(c.items(), key=str):
        logger.info(f"top-up {k}: {v}")


def stage_survivors() -> None:
    reads = {r["uid"]: r for r in read_jsonl(IN45 / "data" / "manual_reads_v9.jsonl")}
    surv = {r["uid"]: r for r in read_jsonl(IN45 / "data" / "survivors_for_tpg.jsonl")}
    smp = {r["uid"]: r for r in read_jsonl(IN45 / "data" / "samples_v9.jsonl")}
    rows = []
    for uid, m in reads.items():
        src = surv.get(uid) or smp.get(uid)
        if not src or not src.get("code"):
            logger.warning(f"survivor {uid}: no code found")
            continue
        rows.append({"uid": f"S9|{uid}", "orig_uid": uid, "source": "E45 k5 hand-read survivor", "cell_v9": src["cell"],
                     "family_v9": m["family"], "algorithm_read_v9": m["algorithm"], "code_in": src["code"],
                     "author": src.get("model"), "banned_set": src.get("banned_set"), "round": 0,
                     "slot": len(rows)})
    ms = read_json(IN46 / "data" / "mcode_sets.json")
    for p in ms["placement"]:
        if p["set"] != "SURV":
            continue
        rows.append({"uid": f"S8|{p['uid']}", "orig_uid": p["uid"], "source": "iteration-8 C6 survivor (E46 SURV)",
                     "family_v9": "UD" if p["algorithm"] == "dijkstra_unit" else None,
                     "algorithm_read_v9": p["algorithm"] if p["algorithm"] != "other" else p.get("other_name"),
                     "code_in": p["scrubbed"], "author": p.get("author"), "round": 1, "slot": len(rows),
                     "e46_scrubbed_sha256": p["scrubbed_sha256"]})
    rows = pipeline(rows, code_field="code_in")
    dedupe(rows)
    write_jsonl(DATA / "survivor_candidates.jsonl", rows)
    c = Counter((r.get("family_v9"), r.get("valid", False), r.get("disc"), r.get("cont")) for r in rows)
    for k, v in sorted(c.items(), key=str):
        logger.info(f"survivor {k}: {v}")


def stage_covert() -> None:
    smp = read_jsonl(IN45 / "data" / "samples_v9.jsonl")
    cand = []
    for r in smp:
        b = r.get("banned_set") or []
        if not (r.get("code") and r.get("passed") and r.get("passed_exp2")) or r.get("label") not in ("bfs", "dfs"):
            continue
        if r["label"] not in b:
            continue
        cls = {r.get("runtime_class") or "", r.get("order_class") or ""}
        if not (("BFS" in cls and r["label"] == "bfs") or ("DFS" in cls and r["label"] == "dfs")):
            continue
        if alias_regex(b).search(r["code"]):
            continue                                       # names a banned algorithm -> not covert
        cand.append(r)
    rng = random.Random(0)
    by: dict[str, list[dict[str, Any]]] = {}
    for r in cand:
        by.setdefault(r["cell"], []).append(r)
    pick = []
    for cell in sorted(by):
        xs = by[cell][:]
        rng.shuffle(xs)
        pick += xs[:6]
    pick = pick[:60]
    rows = [{"uid": f"C9|{r['uid']}", "orig_uid": r["uid"], "source": "E45 covert banned BFS/DFS", "cell_v9": r["cell"],
             "banned_set": r.get("banned_set"), "label_v9": r["label"], "code_in": r["code"], "author": r.get("model"),
             "round": 0, "slot": i} for i, r in enumerate(pick)]
    rows = pipeline(rows, code_field="code_in")
    dedupe(rows)
    for r in rows:
        r["kept"] = bool(r.get("valid") and r.get("disc") in ("LEV", "DFS"))
    write_jsonl(DATA / "placed_covert.jsonl", rows)
    logger.info(f"covert: {len(cand)} candidates, {len(pick)} picked (<= 6 per E45 cell), "
                f"{sum(r['kept'] for r in rows)} kept (measured LEV or DFS); "
                f"{Counter((r.get('label_v9'), r.get('disc')) for r in rows)}")
    _ = sha256_text


def stage_primary() -> None:
    """Iteration 9's PRIMARY M-code frame programs (cached states): measured (disc, cont) for the F1 analyses."""
    ms = read_json(IN46 / "data" / "mcode_sets.json")
    rows = []
    for alg, progs in ms["sets"]["PRIMARY"].items():
        for rank, p in enumerate(progs):
            rows.append({"uid": f"P9|{p['uid']}", "orig_uid": p["uid"], "algorithm": alg, "source": p["source"],
                         "code_in": p["scrubbed"], "e46_scrubbed_sha256": p["scrubbed_sha256"],
                         "context_variant": p.get("context_variant"), "rank": rank, "round": 0, "slot": len(rows)})
    rows = pipeline(rows, code_field="code_in")
    write_jsonl(DATA / "primary_measured.jsonl", rows)
    logger.info(f"PRIMARY measured: {Counter((r['algorithm'], r.get('disc'), r.get('cont')) for r in rows)}")


if __name__ == "__main__":
    {"topups": stage_topups, "survivors": stage_survivors, "covert": stage_covert,
     "primary": stage_primary}[sys.argv[1]]()
