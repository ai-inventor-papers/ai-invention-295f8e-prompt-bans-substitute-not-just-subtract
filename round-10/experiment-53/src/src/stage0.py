"""Stage 0: hardware record, instances, probe states, TSPLIB, LKH-3 references, gates, NN and reference baselines."""
from __future__ import annotations

import json
import multiprocessing as mp
import platform
import shutil
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (DATA, PRED, RESULTS, ROOT, append_jsonl, container_ram_bytes, detect_cpus, ledger,  # noqa: E402
                    read_jsonl, setup_logging, utc_now, write_json)
from tsp_task import TSPLIB_OPT, build_sets, dist_matrix, load_tsplib, ref_job, tour_length  # noqa: E402

logger = setup_logging("stage0")


def _ver(mod: str) -> str | None:
    try:
        m = __import__(mod)
        return getattr(m, "__version__", "unknown")
    except ImportError:
        return None


def write_hardware() -> None:
    gpu = {}
    try:
        q = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version,compute_cap",
                            "--format=csv,noheader"], capture_output=True, text=True, timeout=30).stdout.strip()
        gpu = dict(zip(["name", "memory_total", "driver", "compute_cap"], [x.strip() for x in q.split(",")]))
        cuda = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=30).stdout
        gpu["cuda_driver_version"] = cuda.split("CUDA Version:")[1].split()[0] if "CUDA Version:" in cuda else None
    except (OSError, subprocess.SubprocessError, IndexError) as e:
        gpu = {"error": str(e)}
    hw = {"utc": utc_now(), "gpu": gpu, "nproc_host": __import__("os").cpu_count(),
          "cgroup_cpu_quota": detect_cpus(), "cgroup_ram_bytes": container_ram_bytes(),
          "compiler": shutil.which("gcc") or shutil.which("cc"), "python": platform.python_version(),
          "versions": {m: _ver(m) for m in ("vllm", "torch", "elkai", "ortools", "numpy", "scipy", "transformers")}}
    write_json(PRED / "hardware.json", hw)
    logger.info(f"hardware: {json.dumps(hw)[:400]}")


REF_PATH = DATA / "references.jsonl"


def references(sets: dict, tsplib: list[dict], n_workers: int = 5) -> None:
    done = {(r["set"], r["idx"]) for r in read_jsonl(REF_PATH)}
    jobs = []
    for name in ("selection", "heldout", "heldout_ext"):
        for i, c in enumerate(sets[name]["coords"]):
            if (name, i) not in done:
                jobs.append(((name, i), dist_matrix(c), False, 10))
    for i, t in enumerate(tsplib):
        if ("tsplib", i) not in done:
            jobs.append((("tsplib", i), t["D_int"], True, 10))
    logger.info(f"references: {len(jobs)} to solve ({len(done)} cached)")
    import elkai  # noqa: F401  (fail early if missing -> OR-Tools path is used inside solve_reference)

    ver = {"elkai": _ver("elkai"), "ortools": _ver("ortools")}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=n_workers, mp_context=mp.get_context("spawn")) as pool:
        futs = {pool.submit(ref_job, j): j for j in jobs}
        for k, f in enumerate(as_completed(futs)):
            (name, i), D, integer, runs = futs[f]
            key, tour, solver, secs = f.result()
            if name == "tsplib":
                L = float(tour_length(tour, D))
                row = {"set": name, "idx": i, "name": tsplib[i]["name"], "n": len(D), "solver": solver, "runs": runs,
                       "time_s": round(secs, 3), "cost_int": int(L), "opt": TSPLIB_OPT[tsplib[i]["name"]],
                       "L_ref": L, "tour": tour, "versions": ver, "utc": utc_now()}
            else:
                L = tour_length(tour, D)
                Lint = float(np.rint(D * 1e6).astype(np.int64)[np.asarray(tour), np.roll(np.asarray(tour), -1)].sum())
                row = {"set": name, "idx": i, "seed": sets[name]["seeds"][i], "n": len(D), "solver": solver,
                       "runs": runs, "time_s": round(secs, 3), "L_ref": L, "L_int_over_1e6": Lint / 1e6,
                       "tour": tour, "versions": ver, "utc": utc_now()}
            append_jsonl(REF_PATH, row)
            if k % 20 == 0:
                logger.info(f"  ref {k + 1}/{len(jobs)} {name}[{i}] {solver} {secs:.2f}s L={L:.4f}")
    logger.info(f"references done in {time.time() - t0:.1f}s")


def summarise_references(tsplib: list[dict]) -> dict:
    rows = read_jsonl(REF_PATH)
    summ: dict = {"utc": utc_now(), "sets": {}, "tsplib": {}}
    for name in ("selection", "heldout", "heldout_ext"):
        rs = [r for r in rows if r["set"] == name]
        rel = [abs(r["L_ref"] - r["L_int_over_1e6"]) / r["L_ref"] for r in rs]
        # each edge is rounded to the nearest 1e-6, so |float - int/1e6| <= n * 0.5e-6 (exact bound per instance)
        within = all(abs(r["L_ref"] - r["L_int_over_1e6"]) <= r["n"] * 0.5e-6 + 1e-12 for r in rs)
        summ["sets"][name] = {"n_instances": len(rs), "solver": sorted({r["solver"] for r in rs}),
                              "runs": sorted({r["runs"] for r in rs}),
                              "mean_time_s": float(np.mean([r["time_s"] for r in rs])),
                              "max_rel_float_vs_int_objective": float(max(rel)) if rel else None,
                              "float_vs_int_within_rounding_bound": bool(within),
                              "mean_L_ref": float(np.mean([r["L_ref"] for r in rs]))}
    gate_ok = True
    for r in rows:
        if r["set"] != "tsplib":
            continue
        g = 100.0 * (r["cost_int"] - r["opt"]) / r["opt"]
        summ["tsplib"][r["name"]] = {"cost_int": r["cost_int"], "opt": r["opt"], "solver_gap_pct": g,
                                     "solver": r["solver"], "time_s": r["time_s"], "within_0.5pct": g <= 0.5}
        gate_ok &= g <= 0.5
    summ["tsplib_gate_passed"] = bool(gate_ok)
    summ["tsplib_reference_rule"] = ("TSPLIB gaps are always computed against the published optima "
                                     "(gap = 100 (cost_int - opt)/opt); the gate checks that elkai reaches them.")
    write_json(RESULTS / "references.json", summ)
    return summ


def nn_gate_and_baselines(sets: dict, tsplib: list[dict]) -> dict:
    """NN through the sandbox on every set, twice, in two different worker processes (must agree to 1e-9);
    plus the tour-length reference heuristics (other interface)."""
    import evaluator as ev
    from baselines import NN_PROGRAM, reference_heuristics

    refs = ev.load_references()
    pids = set()
    runs = []
    for rep in range(2):  # a fresh single-worker pool per repetition -> two different worker processes
        pool = ev.make_pool(1)
        out = {}
        for set_name in ("selection", "heldout", "heldout_ext", "tsplib"):
            f = pool.submit(ev.job_set, NN_PROGRAM, set_name, 600)
            out[set_name] = f.result()
        out["pid"] = pool.submit(ev.job_pid).result()
        runs.append(out)
        pids.add(out["pid"])
        if rep == 1:
            probe = pool.submit(ev.job_program, NN_PROGRAM, True).result()
        pool.shutdown()
    res: dict = {"NN": {}, "gate": {}}
    for set_name in ("selection", "heldout", "heldout_ext"):
        g = [ev.gaps_from_lengths(r[set_name]["lengths"], refs[set_name]) for r in runs]
        diff = float(np.max(np.abs(g[0] - g[1])))
        res["gate"][set_name] = {"max_abs_diff": diff, "ok": diff <= 1e-9}
        res["NN"][set_name] = {"gaps": g[0].tolist(), "mean_gap": float(g[0].mean())}
    nm = ev.load_payload.__module__  # noqa: F841
    names = [t["name"] for t in tsplib]
    tg = [ev.tsplib_gaps(r["tsplib"]["tours"], names) for r in runs]
    res["gate"]["tsplib"] = {"ok": tg[0] == tg[1]}
    res["NN"]["tsplib"] = {"gaps": tg[0], "mean_gap": float(np.mean(list(tg[0].values())))}
    res["gate"]["worker_pids"] = sorted(pids)
    res["gate"]["two_processes"] = len(pids) == 2
    sel = np.array(res["NN"]["selection"]["gaps"])
    res["NN"]["G50"] = float(sel[:32].mean())
    res["NN"]["G100"] = float(sel[32:].mean())
    res["NN"]["F"] = 1.0
    res["NN"]["G200"] = res["NN"]["heldout"]["mean_gap"]
    res["NN"]["G200_ext"] = res["NN"]["heldout_ext"]["mean_gap"]
    res["NN"]["probe_valid"] = probe.get("probe_label") == "probe_valid"
    res["NN"]["probe_err"] = probe.get("n_err")
    (DATA / "nn_probe_decisions.json").write_text(json.dumps(probe.get("decisions")))
    # tour-length reference heuristics (another interface; references only)
    other: dict = {}
    for set_name in ("selection", "heldout", "heldout_ext"):
        Ls: dict[str, list] = {}
        for c in sets[set_name]["coords"]:
            for k, v in reference_heuristics(dist_matrix(c)).items():
                Ls.setdefault(k, []).append(v)
        other[set_name] = {k: {"mean_gap": float(ev.gaps_from_lengths(v, refs[set_name]).mean()),
                               "gaps": ev.gaps_from_lengths(v, refs[set_name]).tolist()} for k, v in Ls.items()}
        if set_name == "selection":
            for k, d in other[set_name].items():
                g = np.array(d["gaps"])
                d["G50"], d["G100"] = float(g[:32].mean()), float(g[32:].mean())
                d["F"] = 0.5 * d["G50"] / res["NN"]["G50"] + 0.5 * d["G100"] / res["NN"]["G100"]
    from baselines import greedy_edge_tour, insertion_tour

    tsp_other: dict = {}
    for t in tsplib:
        Dn, Di = t["D_norm"], t["D_int"]
        for m in ("nearest", "farthest", "cheapest", "random"):
            tour = insertion_tour(Dn, m)
            cost = int(Di[np.asarray(tour), np.roll(np.asarray(tour), -1)].sum())
            tsp_other.setdefault(f"{m}_insertion", {})[t["name"]] = 100.0 * (cost - t["opt"]) / t["opt"]
        tour = greedy_edge_tour(Dn)
        cost = int(Di[np.asarray(tour), np.roll(np.asarray(tour), -1)].sum())
        tsp_other.setdefault("greedy_edge", {})[t["name"]] = 100.0 * (cost - t["opt"]) / t["opt"]
    other["tsplib"] = {k: {"gaps": v, "mean_gap": float(np.mean(list(v.values())))} for k, v in tsp_other.items()}
    res["reference_heuristics"] = other
    res["utc"] = utc_now()
    res["note"] = ("NN is the seed program and the baseline; insertion and greedy-edge tours use another "
                   "interface and are tour-length references only. TSPLIB: heuristics see D_norm, cost in EUC_2D.")
    write_json(RESULTS / "baselines.json", res)
    logger.info(f"NN: G50 {res['NN']['G50']:.3f} G100 {res['NN']['G100']:.3f} G200 {res['NN']['G200']:.3f} "
                f"EXT {res['NN']['G200_ext']:.3f} TSPLIB {res['NN']['tsplib']['mean_gap']:.3f}; gate {res['gate']}")
    return res


@logger.catch(reraise=True)
def main() -> None:
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("all", "hardware"):
        write_hardware()
    sets = build_sets()
    hashes = {k: v["sha256"] for k, v in sets.items()}
    from probes import build_probe_states

    pst = build_probe_states()
    hashes["probe_states"] = pst["sha256"]
    tsplib = load_tsplib()
    hashes["tsplib"] = {t["name"]: t["sha256"] for t in tsplib}
    write_json(DATA / "instance_hashes.json", hashes)
    logger.info(f"instances: { {k: len(v['seeds']) for k, v in sets.items()} }, probe states {len(pst['states'])}, "
                f"tsplib {len(tsplib)}")
    ledger("stage0_instances")
    if what in ("all", "references"):
        references(sets, tsplib)
        summ = summarise_references(tsplib)
        logger.info(f"TSPLIB gate passed: {summ['tsplib_gate_passed']}")
        ledger("stage0_references", tsplib_gate=summ["tsplib_gate_passed"])
    if what in ("all", "baselines"):
        nn_gate_and_baselines(sets, tsplib)
        ledger("stage0_baselines")


if __name__ == "__main__":
    main()
