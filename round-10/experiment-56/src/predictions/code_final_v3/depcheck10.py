#!/usr/bin/env python3
"""Independent correctness check of every generated CC (T10) program against the declared dependency art_j3Rm_lr2nzR6
(iteration-1 dataset): the parsed LeetCode I/O pairs of problem 323 (number of connected components, kwargs n, edges)
and 547 (number of provinces, isConnected matrix -> n, edge list), status 'ok' only. Each program's solve(n, edges) is
run in a spawned worker with a per-program time limit; the result is compared with the frozen labeller's pass flag.
Writes results/depcheck_leetcode.json.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import signal
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Any

from loguru import logger

from cfg10 import DATA_DIR, DEP_DATASET, RESULTS_DIR, detect_cpus, read_jsonl, setup_logging, utc_now, write_json

TIME_LIMIT_S = 20


def load_cases() -> dict[str, list[dict[str, Any]]]:
    d = json.loads((DEP_DATASET / "full_data_out.json").read_text())
    out: dict[str, list[dict[str, Any]]] = {}
    for ds in d["datasets"]:
        if ds["dataset"] != "leetcodedataset":
            continue
        for e in ds["examples"]:
            q = str(e.get("metadata_question_id"))
            if q in ("323", "547"):
                cases = json.loads(e["metadata_test_cases_json"])
                ok = []
                for c in cases:
                    if c.get("status") != "ok":
                        continue
                    kw = c["kwargs"]
                    if q == "323":
                        ok.append({"id": c["case_id"], "n": kw["n"], "edges": kw["edges"], "expected": c["expected"]})
                    else:
                        M = kw["isConnected"]
                        n = len(M)
                        edges = [[i, j] for i in range(n) for j in range(i + 1, n) if M[i][j]]
                        ok.append({"id": c["case_id"], "n": n, "edges": edges, "expected": c["expected"]})
                out[q] = ok
    return out


def _alarm(signum, frame):
    raise TimeoutError("time limit")


def run_program(code: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(TIME_LIMIT_S)
    n_pass, err = 0, None
    try:
        ns: dict[str, Any] = {"__name__": "candidate"}
        exec(compile(code, "<candidate>", "exec"), ns)
        fn = ns.get("solve")
        if fn is None:
            return {"n_pass": 0, "n": len(cases), "error": "no solve()"}
        for c in cases:
            try:
                got = fn(c["n"], [list(e) for e in c["edges"]])
                n_pass += int(got == c["expected"])
            except Exception as e:  # noqa: BLE001 - a candidate program may raise anything
                err = err or f"{type(e).__name__}: {str(e)[:80]}"
    except TimeoutError:
        err = "timeout"
    except Exception as e:  # noqa: BLE001
        err = f"{type(e).__name__}: {str(e)[:80]}"
    finally:
        signal.alarm(0)
    return {"n_pass": n_pass, "n": len(cases), "error": err}


def main() -> None:
    t0 = time.time()
    cases = load_cases()
    allc = cases.get("323", []) + cases.get("547", [])
    logger.info(f"LeetCode cases: 323 {len(cases.get('323', []))}, 547 {len(cases.get('547', []))}")
    raw = {r["sid"]: r for r in read_jsonl(DATA_DIR / "gen_samples.jsonl") if r["unit"] == "T10"}
    lab = {r["sid"]: r for r in read_jsonl(DATA_DIR / "gen_labels.jsonl")}
    sids = [s for s in raw if s in lab]
    codes = [lab[s].get("code") or "" for s in sids]
    nw = max(1, min(12, detect_cpus() - 1))
    with ProcessPoolExecutor(max_workers=nw, mp_context=mp.get_context("spawn")) as pool:
        res = list(pool.map(run_program, codes, [allc] * len(codes), chunksize=4))
    rows, agree, n_dep_pass, n_lab_pass = [], 0, 0, 0
    by_arm: dict[str, dict[str, int]] = {}
    for s, r in zip(sids, res):
        dep_pass = r["n"] > 0 and r["n_pass"] == r["n"]
        lab_pass = bool(lab[s]["passed"])
        agree += int(dep_pass == lab_pass)
        n_dep_pass += int(dep_pass)
        n_lab_pass += int(lab_pass)
        a = raw[s]["arm"]
        st = by_arm.setdefault(a, {"n": 0, "dep_pass": 0, "labeller_pass": 0, "dfs_dep_pass": 0})
        st["n"] += 1
        st["dep_pass"] += int(dep_pass)
        st["labeller_pass"] += int(lab_pass)
        st["dfs_dep_pass"] += int(dep_pass and lab[s]["label"] == "dfs")
        rows.append({"sid": s, "arm": a, "label": lab[s]["label"], "labeller_pass": lab_pass, "dep_n_pass": r["n_pass"],
                     "dep_n": r["n"], "dep_pass": dep_pass, "error": r["error"]})
    out = {"utc": utc_now(), "source": "art_j3Rm_lr2nzR6 full_data_out.json leetcodedataset 323 + 547 (status ok)",
           "n_cases": {"323": len(cases.get("323", [])), "547": len(cases.get("547", []))},
           "n_programs": len(rows), "n_dep_pass": n_dep_pass, "n_labeller_pass": n_lab_pass,
           "agreement_dep_vs_labeller_pass": agree / len(rows) if rows else None, "by_arm": by_arm,
           "disagreements": [r for r in rows if r["dep_pass"] != r["labeller_pass"]][:50],
           "seconds": round(time.time() - t0, 1)}
    write_json(RESULTS_DIR / "depcheck_leetcode.json", out)
    logger.info(f"depcheck: {n_dep_pass}/{len(rows)} pass the LeetCode pairs; labeller {n_lab_pass}; agreement "
                f"{out['agreement_dep_vs_labeller_pass']:.3f}")


if __name__ == "__main__":
    setup_logging("depcheck10")
    main()
