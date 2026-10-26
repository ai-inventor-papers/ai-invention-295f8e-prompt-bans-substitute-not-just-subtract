#!/usr/bin/env python3
"""STEP 1 - inputs: read-only vendoring of the non-declared items, task definitions, stress inputs, verification.

Vendoring: one copy attempt per item into inputs/vendor/<item>/ (source path relative to <runs>, sha256 and UTC in
inputs/vendor_manifest.json); T03 files are verified against bench/commitment.json. Nothing is executed in place.
Tasks: T2 (exp8 suite t2_wsp: solve(n, edges, s, t)), T03 (exp11 bench T03_kth_smallest: solve(nums, k)), A3 (iteration-5
newbench A3_trapping_rain_water: solve(height)). Each task object holds the verbatim spec_text / format_line, the
catalogue, the references, the hidden tests split into the quick stage and the rest, and 10 stress inputs at maximum
size whose expected outputs come from the fastest reference.
"""

from __future__ import annotations

import json
import random
import shutil
import statistics
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from loguru import logger

from common import (INPUTS, RUNS_DIR, VENDOR, VENDOR_SOURCES, read_json, rel, sha256_file, utc_now, write_json)

MANIFEST = INPUTS / "vendor_manifest.json"
TASK_DIR = INPUTS / "tasks"

# what is copied from each source (None = whole tree); __pycache__ is never copied
VENDOR_PICK: dict[str, list[str] | None] = {
    "bench": ["__init__.py", "commitment.json", "common", "T03_kth_smallest"],
    "exp8_suite": ["__init__.py", "common.py", "labeller", "tasks"],
    "exp30_src": ["regate_rules.py", "label6.py", "prompts6.py", "engine6.py", "label_worker_v4.py"],
    "newbench": ["__init__.py", "common", "A3_trapping_rain_water"],
    "exp27": ["prompts/prompts.jsonl", "src/cfg5.py", "src/parsers.py"],
    "exp29_results": ["known_solutions.json"],
}

T2_MODES = ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"]
T2_CATALOGUE = [
    {"mode": "dijkstra", "display_name": "Dijkstra's algorithm",
     "mechanism": "settle nodes in order of tentative distance using a priority queue (binary heap) or a linear "
                  "minimum scan, relaxing the out-edges of each settled node once"},
    {"mode": "bf_spfa", "display_name": "Bellman-Ford (including its queue-based form SPFA)",
     "mechanism": "repeatedly relax every edge (n-1 full passes) or keep a FIFO queue of nodes whose distance improved "
                  "(label-correcting)"},
    {"mode": "bidijkstra", "display_name": "bidirectional Dijkstra",
     "mechanism": "run Dijkstra forward from s and backward from t on the reversed graph, alternating, and stop when "
                  "the two frontiers meet"},
    {"mode": "floyd", "display_name": "Floyd-Warshall",
     "mechanism": "all-pairs dynamic programme over intermediate nodes k: dist[i][j] = min(dist[i][j], "
                  "dist[i][k] + dist[k][j])"},
    {"mode": "dial", "display_name": "Dial's algorithm (bucket queue)",
     "mechanism": "a bucket queue indexed by integer distance (weights are small integers), scanning buckets in "
                  "increasing order"},
]
T2_REF_MODE = {"bellman_ford": "bf_spfa", "spfa": "bf_spfa", "bidijkstra_alternate": "bidijkstra",
               "bidijkstra_reverse": "bidijkstra", "dial_dict": "dial", "dial_list": "dial",
               "dijkstra_decreasekey": "dijkstra", "dijkstra_lazy": "dijkstra", "floyd_bigint": "floyd",
               "floyd_inf": "floyd"}
T2_SEED_REF = {"dijkstra": "dijkstra_lazy", "bf_spfa": "spfa", "bidijkstra": "bidijkstra_alternate",
               "floyd": "floyd_inf", "dial": "dial_list"}
DEFAULT_MODE = {"T2": "dijkstra", "T03": "full_sort", "A3": "prefix_suffix_max"}
GENERIC_FORCED = ["Implement {j} for this task.", "Use {j} to solve this task.", "Solve this task with {j}.",
                  "Your solution should use {j}.", "Write an implementation based on {j}.",
                  "Solve the task below using {j}.", "Your solution must implement {j}.",
                  "Write code that implements {j}.", "Base your solution on {j}.", "Apply {j} to solve this task."]
STRESS_SEED = {"T2": 770002, "T03": 770003, "A3": 770043}
N_STRESS = 10


# ------------------------------------------------------------------------------------------------ vendoring
def _copy_item(name: str) -> dict[str, Any]:
    src = RUNS_DIR / VENDOR_SOURCES[name]
    dst = VENDOR / name
    rec: dict[str, Any] = {"item": name, "source": "<runs>/" + VENDOR_SOURCES[name], "utc": utc_now(), "files": {},
                           "status": "missing"}
    if not src.exists():
        logger.warning(f"vendor {name}: source missing")
        return rec
    picks = VENDOR_PICK.get(name)
    entries = picks if picks is not None else [p.name for p in src.iterdir()]
    for e in entries:
        s = src / e
        d = dst / e
        if not s.exists():
            rec.setdefault("absent", []).append(e)
            continue
        d.parent.mkdir(parents=True, exist_ok=True)
        if s.is_dir():
            if d.exists():
                shutil.rmtree(d)
            shutil.copytree(s, d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(s, d)
    for f in sorted(dst.rglob("*")):
        if f.is_file():
            rec["files"][f.relative_to(dst).as_posix()] = sha256_file(f)
    rec["status"] = "copied"
    return rec


def vendor_all(include_b7: bool = False) -> dict[str, Any]:
    man = read_json(MANIFEST) if MANIFEST.exists() else {"items": {}}
    names = list(VENDOR_PICK) + (["B7"] if include_b7 else [])
    for n in names:
        if n in man["items"] and man["items"][n].get("status") == "copied" and (VENDOR / n).exists():
            continue
        man["items"][n] = _copy_item(n)
        logger.info(f"vendored {n}: {man['items'][n]['status']} ({len(man['items'][n]['files'])} files)")
    # T03: verify against the bench commitment (sha256 of every committed file)
    cm = VENDOR / "bench" / "commitment.json"
    if cm.exists():
        files = read_json(cm)["tasks"]["T03"]["files"]
        chk = {}
        for k, h in files.items():
            p = VENDOR / "bench" / "T03_kth_smallest" / k
            if p.exists():
                chk[k] = sha256_file(p) == h
        man["t03_commitment_check"] = {"n_checked": len(chk), "n_match": sum(chk.values()),
                                       "mismatch": [k for k, v in chk.items() if not v]}
    write_json(MANIFEST, man)
    return man


# ------------------------------------------------------------------------------------------------ tasks
def _split_format(spec_text: str, format_line: str) -> str:
    body = spec_text.replace(format_line, "").strip()
    return body


def _size(task: str, kw: dict[str, Any]) -> int:
    if task == "T2":
        return kw["n"] + len(kw["edges"])
    if task == "T03":
        return len(kw["nums"])
    return len(kw["height"])


def _case(cid: str, kw: dict[str, Any], exp: Any, lim: float) -> dict[str, Any]:
    return {"id": cid, "kw": json.dumps(kw), "exp": json.dumps(exp), "lim": float(lim)}


def _raw_task(task: str) -> dict[str, Any]:
    if task == "T2":
        d = VENDOR / "exp8_suite" / "tasks" / "t2_wsp"
        spec_text = (d / "spec.txt").read_text().strip()
        fmt = spec_text.split("\n\n")[-1].strip()
        lim = read_json(d / "limits.json")["limits"]
        tests = [{"case_id": c["id"], "kwargs": {"n": c["n"], "edges": c["edges"], "s": c["s"], "t": c["t"]},
                  "expected": c["expected"], "limit": float(lim.get(c["id"], 1.0))} for c in read_json(d / "tests.json")]
        refs = {p.stem: p.read_text() for p in sorted((d / "references").glob("*.py"))}
        ref_mode = {k: T2_REF_MODE[k] for k in refs}
        seeds = {m: T2_SEED_REF[m] for m in T2_MODES}
        catalogue = T2_CATALOGUE
        forced = GENERIC_FORCED
        signature = "solve(n, edges, s, t)"
    elif task == "T03":
        d = VENDOR / "bench" / "T03_kth_smallest"
        spec = read_json(d / "spec.json")
        spec_text, fmt = spec["spec_text"], spec["format_line"]
        tests = [json.loads(l) for l in (d / "tests.jsonl").read_text().splitlines() if l.strip()]
        refs = {p.stem: p.read_text() for p in sorted((d / "references").glob("*.py"))}
        ref_mode = {k: k for k in refs}
        seeds = {k: k for k in refs}
        catalogue = spec["catalogue"]
        forced = spec.get("forced_templates") or GENERIC_FORCED
        signature = spec["signature"]
    elif task == "A3":
        d = VENDOR / "newbench" / "A3_trapping_rain_water"
        spec = read_json(d / "spec.json")
        spec_text, fmt = spec["spec_text"], spec["format_line"]
        tests = [json.loads(l) for l in (d / "tests.jsonl").read_text().splitlines() if l.strip()]
        refs = {p.stem: p.read_text() for p in sorted((d / "references").glob("*.py"))}
        ref_mode = {k: k for k in refs}
        seeds = {k: k for k in refs}
        catalogue = spec["catalogue"]
        forced = spec.get("forced_templates") or GENERIC_FORCED
        signature = spec["signature"]
    else:
        raise ValueError(task)
    return {"task": task, "spec_text": spec_text, "format_line": fmt, "spec_body": _split_format(spec_text, fmt),
            "signature": signature, "tests": tests, "references": refs, "ref_mode": ref_mode, "seed_refs": seeds,
            "catalogue": catalogue, "modes": [c["mode"] for c in catalogue],
            "display": {c["mode"]: c["display_name"] for c in catalogue},
            "mechanism": {c["mode"]: c["mechanism"] for c in catalogue}, "default": DEFAULT_MODE[task],
            "forced_templates": forced}


def gen_stress(task: str, seed: int) -> list[dict[str, Any]]:
    """10 randomised inputs at maximum size (task bounds), seed fixed per task and never shown to the mutator."""
    rng = random.Random(seed)
    out = []
    if task == "T03":
        n = 2000
        for i in range(N_STRESS):
            kind = i % 5
            if kind == 0:
                nums = [rng.randint(-10000, 10000) for _ in range(n)]
            elif kind == 1:
                nums = [rng.randint(-5, 5) for _ in range(n)]
            elif kind == 2:
                nums = sorted(rng.randint(-10000, 10000) for _ in range(n))
            elif kind == 3:
                nums = sorted((rng.randint(-10000, 10000) for _ in range(n)), reverse=True)
            else:
                v = rng.randint(-10000, 10000)
                nums = [v if rng.random() < 0.7 else rng.randint(-10000, 10000) for _ in range(n)]
            k = [1, n, rng.randint(1, n), n // 2, rng.randint(1, n)][i % 5]
            out.append({"kwargs": {"nums": nums, "k": k}, "kind": f"stress{kind}"})
    elif task == "T2":
        n = 100
        for i in range(N_STRESS):
            kind = i % 5
            edges = []
            if kind == 0:
                edges = [[rng.randrange(n), rng.randrange(n), rng.randint(0, 100)] for _ in range(600)]
            elif kind == 1:
                edges = [[rng.randrange(n), rng.randrange(n), rng.choice([0, 0, 0, 1, rng.randint(0, 100)])]
                         for _ in range(600)]
            elif kind == 2:
                edges = [[j, j + 1, rng.randint(50, 100)] for j in range(n - 1)]
                edges += [[rng.randrange(n), rng.randrange(n), rng.randint(0, 100)] for _ in range(600 - len(edges))]
            elif kind == 3:
                layers = [list(range(j, min(j + 10, n))) for j in range(0, n, 10)]
                while len(edges) < 600:
                    li = rng.randrange(len(layers) - 1)
                    edges.append([rng.choice(layers[li]), rng.choice(layers[li + 1]), rng.randint(0, 100)])
            else:
                half = n // 2
                edges = [[rng.randrange(half), rng.randrange(half), rng.randint(0, 100)] for _ in range(550)]
                edges += [[rng.randrange(half, n), rng.randrange(half, n), rng.randint(0, 100)] for _ in range(50)]
            s = rng.randrange(n)
            t = rng.randrange(n)
            if kind == 4:
                s, t = rng.randrange(n // 2), rng.randrange(n // 2, n)
            if kind == 2:
                s, t = 0, n - 1
            out.append({"kwargs": {"n": n, "edges": edges, "s": s, "t": t}, "kind": f"stress{kind}"})
    elif task == "A3":
        n = 20000
        for i in range(N_STRESS):
            kind = i % 5
            if kind == 0:
                h = [rng.randint(0, 100000) for _ in range(n)]
            elif kind == 1:
                p = rng.randint(50, 500)
                h = [(j % p) * rng.randint(1, 100) for j in range(n)]
            elif kind == 2:
                c = rng.randrange(n)
                h = [max(0, 100000 - abs(j - c) * rng.randint(1, 10)) for j in range(n)]
            elif kind == 3:
                h = [rng.randint(0, 3) for _ in range(n)]
                h[0] = h[-1] = 100000
            else:
                h = [abs(j - n // 2) * 5 + rng.randint(0, 50) for j in range(n)]
            out.append({"kwargs": {"height": [min(100000, max(0, x)) for x in h]}, "kind": f"stress{kind}"})
    return out


def _ref_run(task: str, code: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    from sandbox import run_stages
    return run_stages(task, code, [cases])


def build_task(task: str, workers: int = 8, force: bool = False) -> dict[str, Any]:
    """Assemble + verify the task object; cache it in inputs/tasks/<task>.json."""
    out_p = TASK_DIR / f"{task}.json"
    if out_p.exists() and not force:
        return read_json(out_p)
    raw = _raw_task(task)
    tests = raw["tests"]
    # 1) every reference on the full hidden suite (3 repeats for timing), limits checked on THIS CPU
    cases = [_case(c["case_id"], c["kwargs"], c["expected"], max(float(c.get("limit", 1.0)), 1.0)) for c in tests]
    refs = raw["references"]
    with ThreadPoolExecutor(workers) as ex:
        runs = {k: list(ex.map(lambda _: _ref_run(task, refs[k], cases), range(3))) for k in refs}
    ref_report = {}
    per_case_max = [0.0] * len(cases)
    for k, rr in runs.items():
        ok = all(r["passed_all"] for r in rr)
        t = [statistics.median([r["times"][0][i] or 0.0 for r in rr]) for i in range(len(cases))]
        per_case_max = [max(a, b) for a, b in zip(per_case_max, t)]
        ref_report[k] = {"passed": ok, "first_fail": rr[0]["first_fail"], "total_s": round(sum(t), 5),
                         "max_case_s": round(max(t), 5)}
        if not ok:
            logger.error(f"{task}: reference {k} FAILS the hidden tests: {rr[0]['first_fail']} {rr[0]['load_error']}")
    limits = [c["lim"] for c in cases]
    worst_frac = max(t / l for t, l in zip(per_case_max, limits))
    factor = 1.0
    if any(l < 3 * t for t, l in zip(per_case_max, limits)):
        factor = max(3 * t / l for t, l in zip(per_case_max, limits))
        logger.warning(f"{task}: some limits < 3x reference time; rescaling all limits by {factor:.2f}")
    for c in cases:
        c["lim"] = round(c["lim"] * factor, 4)
    # 2) stage split: 6 smallest + 2 at maximum size = quick; rest = stage 2
    sizes = [_size(task, c["kwargs"]) for c in tests]
    order = sorted(range(len(tests)), key=lambda i: (sizes[i], i))
    quick_idx = order[:6] + sorted(range(len(tests)), key=lambda i: (-sizes[i], i))[:2]
    quick_idx = list(dict.fromkeys(quick_idx))
    rest_idx = [i for i in range(len(tests)) if i not in set(quick_idx)]
    # 3) stress inputs + expected from the fastest reference; all references must agree
    stress = gen_stress(task, STRESS_SEED[task])
    st_cases = [_case(f"stress:{i}", s["kwargs"], None, 30.0) for i, s in enumerate(stress)]
    fastest = min((k for k in refs if ref_report[k]["passed"]), key=lambda k: ref_report[k]["total_s"])
    from sandbox import SANDBOX_PY  # noqa: F401
    outs = _stress_outputs(task, refs, stress)
    exp = outs[fastest]["outputs"]
    agree = {k: outs[k]["outputs"] == exp for k in refs if ref_report[k]["passed"]}
    if not all(agree.values()):
        logger.error(f"{task}: references disagree on stress inputs: {agree}")
    st_times = {k: outs[k]["times"] for k in refs}
    st_lim = [max(1.0, 10 * max(st_times[k][i] for k in refs if ref_report[k]["passed"])) for i in range(len(stress))]
    stress_cases = [_case(f"stress:{i}", s["kwargs"], exp[i], st_lim[i]) for i, s in enumerate(stress)]
    obj = {k: v for k, v in raw.items() if k != "tests"}
    obj.update({
        "n_hidden": len(tests),
        "stages": {"quick": [cases[i] for i in quick_idx], "rest": [cases[i] for i in rest_idx],
                   "stress": stress_cases},
        "quick_ids": [tests[i]["case_id"] for i in quick_idx],
        "reference_check": ref_report, "limit_factor": factor, "worst_ref_frac_of_limit": round(worst_frac, 4),
        "fastest_ref": fastest, "fastest_ref_stress_s": round(sum(st_times[fastest]), 6),
        "stress_ref_times": {k: [round(x, 6) for x in v] for k, v in st_times.items()},
        "stress_refs_agree": agree, "stress_seed": STRESS_SEED[task], "stress_kinds": [s["kind"] for s in stress],
    })
    write_json(out_p, obj, indent=None)
    logger.info(f"{task}: {len(tests)} hidden cases ({len(quick_idx)} quick), refs pass "
                f"{sum(v['passed'] for v in ref_report.values())}/{len(refs)}, worst ref/limit {worst_frac:.3f}, "
                f"fastest {fastest} stress {obj['fastest_ref_stress_s']:.3f}s, refs agree {all(agree.values())}")
    return obj


def _stress_outputs(task: str, refs: dict[str, str], stress: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Run each reference on the stress inputs in the sandbox (3 repeats, median time) and capture outputs."""
    import subprocess
    from sandbox import SANDBOX_PY
    prog = r'''
import json, sys, time
job = json.loads(sys.stdin.read())
g = {}
exec(job["code"], g)
outs, times = [], []
for kw in job["inputs"]:
    best = None
    for rep in range(3):
        k = json.loads(kw)
        if job["task"] == "T2":
            k["edges"] = [tuple(e) for e in k["edges"]]
        t0 = time.perf_counter(); o = g["solve"](**k); t = time.perf_counter() - t0
        best = t if best is None else min(best, t)
    outs.append(o); times.append(best)
print(json.dumps({"outputs": outs, "times": times}))
'''
    res = {}
    for k, code in refs.items():
        job = {"code": code, "task": task, "inputs": [json.dumps(s["kwargs"]) for s in stress]}
        pr = subprocess.run([SANDBOX_PY, "-I", "-S", "-c", prog], input=json.dumps(job), capture_output=True,
                            text=True, timeout=600)
        if pr.returncode != 0:
            logger.error(f"{task} ref {k} stress run failed: {pr.stderr[-300:]}")
            res[k] = {"outputs": [None] * len(stress), "times": [999.0] * len(stress)}
            continue
        res[k] = json.loads(pr.stdout.strip().splitlines()[-1])
    return res


def load_task(task: str) -> dict[str, Any]:
    return read_json(TASK_DIR / f"{task}.json")


def cases_for_display(task_obj: dict[str, Any]) -> dict[str, Any]:
    return {"n_quick": len(task_obj["stages"]["quick"]), "n_rest": len(task_obj["stages"]["rest"]),
            "n_stress": len(task_obj["stages"]["stress"])}


if __name__ == "__main__":
    import sys
    from common import setup_logging
    setup_logging("inputs")
    vendor_all()
    for t in (sys.argv[1:] or ["T2", "T03", "A3"]):
        build_task(t, force=True)
    print(rel(MANIFEST))
