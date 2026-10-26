#!/usr/bin/env python3
"""Stage 0 (CPU part): input provenance, labeller re-check, T2 style re-gate, base-extraction test, precision rule.

0.1 every frozen input copied into inputs/ is compared byte for byte (sha256) with its source path in the earlier
    iterations (read-only); bench files are verified against bench/commitment.json (exp19 s0_checks.input_hashes);
    the frozen screen must hash to d6a2ca97...
0.2 labeller re-check (exp19 s0_checks.bench_recheck / suite_recheck, mechanical labels only) + the T2 STYLE
    RE-GATE: heap Dijkstra references -> dijkstra, SPFA / Bellman-Ford references -> bf_spfa, and an array-scan
    O(V^2) Dijkstra probe written here -> dijkstra.
0.3 precision rule from the hardware probe (written to predictions/precision_rule.json).
Testing-plan item 3: the base extraction (src/labels5.py) on 40 ITER1 exp5 raw base_chat outputs; their stored
labels are mapped to the exp8 suite's mode names; agreement >= 0.9 required.
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import (BENCH, E20, E22, E23, EVAL3, I1E5, INPUTS, ITER1, ITER2, ITER4, PRED_DIR, RESULTS_DIR, SUITE,  # noqa
                 bench_paths, read_json, read_jsonl, rel, setup_logging, sha256_file, utc_now, write_json)

SCREEN_SHA = "d6a2ca9711f461973c39482314a523d448d0590cb40e32432826dec1da4846e8"
SOURCES = {  # copy in inputs/ -> source path (read-only)
    "exp22/prompts4.jsonl": ITER4 / "experiment-22/src" / "prompts" / "prompts4.jsonl",
    "exp22/escape.json": ITER4 / "experiment-22/src" / "results" / "escape.json",
    "exp22/units.json": ITER4 / "experiment-22/src" / "results" / "units.json",
    "exp22/screen.json": ITER4 / "experiment-22/src" / "results" / "screen.json",
    "exp22/geometry.json": ITER4 / "experiment-22/src" / "results" / "geometry.json",
    "exp20/positions.json": ITER4 / "experiment-20/src" / "results" / "positions.json",
    "exp20/engine_check.json": ITER4 / "experiment-20/src" / "results" / "engine_check.json",
    "exp20/known_solutions_summary.json": ITER4 / "experiment-20/src" / "results" /
    "known_solutions_summary.json",
    "exp23/qwen_ratio.json": ITER4 / "experiment-23/src" / "results" / "qwen_ratio.json",
    "eval3/screen.json": ITER4 / "evaluation-3/src" / "screen.json",
    "iter1_exp5/labelled_base_chat__baseline.jsonl": ITER1 / "experiment-5/src" / "runs" /
    "labelled_base_chat__baseline.jsonl",
    "iter1_exp5/raw_base_chat__baseline.jsonl": ITER1 / "experiment-5/src" / "runs" /
    "raw_base_chat__baseline.jsonl",
    "iter1_exp5/reproducibility.md": ITER1 / "experiment-5/src" / "reproducibility.md",
}
ITER1_MAP = {"bellman_ford_spfa": "bf_spfa", "astar_greedy": "astar_gbfs", "dijkstra_unit": "dijkstra",
             "floyd_warshall": "floyd", "bidir_dijkstra": "bidijkstra"}
ARRAY_DIJKSTRA = '''def solve(n, edges, s, t):
    INF = float("inf")
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    dist = [INF] * n
    dist[s] = 0
    visited = [False] * n
    for _ in range(n):
        u = -1
        best = INF
        for i in range(n):
            if not visited[i] and dist[i] < best:
                best = dist[i]
                u = i
        if u == -1:
            break
        visited[u] = True
        for v, w in adj[u]:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
    return dist[t] if dist[t] < INF else -1
'''


def provenance() -> dict[str, Any]:
    out: dict[str, Any] = {"files": {}, "mismatch": []}
    for k, src in SOURCES.items():
        mine = INPUTS / k
        h_m = sha256_file(mine) if mine.exists() else None
        h_s = sha256_file(src) if src.exists() else None
        out["files"][k] = {"sha256": h_m, "source_sha256": h_s, "source_exists": src.exists()}
        if h_m is None or (h_s is not None and h_m != h_s):
            out["mismatch"].append(k)
    # bench and suite copies against the ITER2 originals
    for sub, src_root in (("exp11/bench", ITER2 / "experiment-11/src" / "bench"),
                          ("exp8/suite", ITER2 / "experiment-8/src" / "suite")):
        n = bad = 0
        for f in sorted((INPUTS / sub).rglob("*")):
            if not f.is_file() or "__pycache__" in f.parts:
                continue
            s = src_root / f.relative_to(INPUTS / sub)
            if not s.exists():
                continue
            n += 1
            if sha256_file(f) != sha256_file(s):
                bad += 1
                out["mismatch"].append(f"{sub}/{f.relative_to(INPUTS / sub)}")
        out[f"{sub}_vs_iter2"] = {"n_compared": n, "n_differ": bad}
    out["screen_sha256_ok"] = sha256_file(INPUTS / "eval3" / "screen.json") == SCREEN_SHA
    out["pass"] = not out["mismatch"] and out["screen_sha256_ok"]
    return out


def style_regate() -> dict[str, Any]:
    bench_paths()
    from labeller import ast_rules, runtime_rules
    from tasks.harness import evaluate_program

    res = {}
    progs = {p.stem: p.read_text() for p in sorted((SUITE / "tasks" / "t2_wsp" / "references").glob("*.py"))}
    progs["probe_array_scan_dijkstra"] = ARRAY_DIJKSTRA
    want = {"dijkstra_lazy": "dijkstra", "dijkstra_decreasekey": "dijkstra", "spfa": "bf_spfa",
            "bellman_ford": "bf_spfa", "probe_array_scan_dijkstra": "dijkstra"}
    for name, code in progs.items():
        ev = evaluate_program("t2", code)
        rl = runtime_rules.label("t2", ev["probes"])[0]
        al = ast_rules.label(code, "t2")[0]
        res[name] = {"passed": bool(ev["tests"].get("passed")), "runtime": rl, "ast": al, "want": want.get(name)}
    ok = all(v["runtime"] == v["want"] and v["passed"] for k, v in res.items() if v["want"])
    return {"programs": res, "pass": ok,
            "structural_note": "array-scan Dijkstra = min over a dist array with a visited set (no heap); it must "
                               "label dijkstra, not an edge-relaxation-to-fixpoint mode"}


def extraction_test(n: int = 40) -> dict[str, Any]:
    import labels5

    lab = {(r["task"], r["sample_id"], r["prompt_id"]): r for r in read_jsonl(I1E5 / "labelled_base_chat__baseline.jsonl")}
    raw = read_jsonl(I1E5 / "raw_base_chat__baseline.jsonl")
    rows = []
    for r in raw:
        L = lab.get((r["task"], r["sample_id"], r["prompt_id"]))
        if L is None or L.get("label") in (None, "None"):
            continue
        rows.append((r, L))
    rows = rows[:n]
    batch = [{"task": r["task"].upper(), "arm": "ITER1_BASE_CHAT", "template": "W1", "slot": i,
              "sample_id": f"X|{r['task']}|{r['prompt_id']}|{r['sample_id']}", "model": "Qwen/Qwen3-8B-Base",
              "prompt_kind": "twin", "text": r["text"], "finish_reason": r["finish_reason"]}
             for i, (r, _) in enumerate(rows)]
    out = labels5.label_batch(batch, use_judge=False)
    agree = []
    det = []
    for (r, L), o in zip(rows, out):
        old = str(L["label"])
        old = "other" if old.startswith("other") else ITER1_MAP.get(old, old)
        new = o["label"]
        agree.append(new == old)
        det.append({"old": old, "new": new, "src": o.get("labeller_source")})
    acc = sum(agree) / max(len(agree), 1)
    return {"n": len(agree), "agreement": acc, "pass": acc >= 0.9, "rows": det,
            "note": "ITER1 labels mapped to exp8 suite names; mechanical labels only (no judge)"}


def precision_probe() -> dict[str, Any]:
    import torch

    p = torch.cuda.get_device_properties(0)
    gib = p.total_memory / 1024 ** 3
    cc = p.major + p.minor / 10
    if gib >= 19.5:
        rule = "bf16"
    elif cc >= 8.9:
        rule = "fp8_w8a8"
    else:
        rule = "fp8_weight_only"
    return {"gpu": p.name, "compute_capability": cc, "total_GiB": round(gib, 2), "precision": rule,
            "rule": "cc >= 8.9 and GiB < 19.5 -> fp8_w8a8; GiB >= 19.5 -> bf16; cc < 8.9 and GiB < 19.5 -> "
                    "fp8_weight_only", "planned_gpu": "RTX A4500 (~19.99 GiB -> bf16)", "utc": utc_now()}


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("s0")
    pr = precision_probe()
    write_json(PRED_DIR / "precision_rule.json", pr)
    logger.info(f"precision rule: {pr}")
    prov = provenance()
    import s0_checks_v4 as S0

    ih = S0.input_hashes()
    prov["bench_commitment"] = {"mismatches": ih["mismatches"], "pass": ih["pass"]}
    prov["pass"] = prov["pass"] and ih["pass"]
    write_json(RESULTS_DIR / "input_hashes.json", {**prov, "all_inputs_sha256": ih["all_inputs_sha256"]})
    logger.info(f"provenance pass={prov['pass']} mismatches={prov['mismatch'][:5]}")
    lr = {"bench": S0.bench_recheck(), "exp8_suite": S0.suite_recheck(), "style_regate": style_regate(),
          "note": "mechanical labels only (runtime/AST); the judge is not re-run"}
    lr["pass"] = (all(v["references_pass"] and v["within_0.02"] for v in lr["bench"].values())
                  and lr["style_regate"]["pass"])
    write_json(RESULTS_DIR / "labeller_recheck.json", lr)
    logger.info(f"labeller recheck pass={lr['pass']}; style re-gate {lr['style_regate']['pass']}")
    et = extraction_test()
    write_json(RESULTS_DIR / "extraction_test.json", et)
    logger.info(f"extraction test: agreement {et['agreement']:.3f} on {et['n']} (pass={et['pass']})")
    (RESULTS_DIR / "s0_done.flag").write_text(utc_now())


if __name__ == "__main__":
    main()
