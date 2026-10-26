#!/usr/bin/env python3
"""Plan 6: run the committed analysis once on the final data.

  python -m analysis.run_all [--boot 2000] [--workers 6]   (cwd = src/)

Writes data/samples.jsonl (merged raw + labels, one row per sample), results/knob_rows.jsonl, results/prices.json
(point estimates per task x class, incl. the twin-segment hull, dial interpolation, Step-0 vertices and the
3-vertex-face check), results/bootstrap_primary.json, results/c1.json (primary + sensitivities s1-s8) and the
descriptive files (analysis.descriptive).
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analysis.core import (CLASSES, E6, NA_PRIMARY, NA_S2, TaskData, c1_decide, class_price, class_vertices,
                           knob_rows, run_bootstrap, step0_hill, pct_ci)
from analysis.hull import Hull, dial_interp_h5, fixed_uniforms
from analysis.stats_step0 import rarefied_hill1
from cfg import (AUDIT_DIR, BOOT_SEED, DATA_DIR, DEFAULT, PATH_TASKS, RESULTS_DIR, read_json, read_jsonl,
                 setup_logging, utc_now, write_json, write_jsonl)

PRICE_CLASSES = ["PN", "TEMP", "TOPK10", "NONCE", "NOVELTY", "SEMSEED", "VETO_1SHOT", "VETO_PERSIST", "VETO_ITER",
                 "MINP", "VS", "PN_EXTRA", "PNPLAIN"]
BOOT_CLASSES = ["PN", "TEMP", "TOPK10", "NONCE", "NOVELTY", "SEMSEED", "VETO_1SHOT", "VETO_PERSIST", "VETO_ITER",
                "MINP", "VS"]


def td_key(td: TaskData, classes: list[str], B: int, seed: int, scheme: str, edges: str, n_sub: int) -> str:
    """Cache key of one task's bootstrap: its arms' arrays (categories, pass, strata, keys), the category names and
    every setting of the run. Identical data + settings -> identical replicates (the seeds are deterministic)."""
    import hashlib

    h = hashlib.sha256()
    h.update(json.dumps([td.task, td.cats, classes, B, seed, scheme, edges, n_sub]).encode())
    for arm in sorted(td.arms):
        a = td.arms[arm]
        h.update(arm.encode())
        h.update(a["cat"].tobytes())
        h.update(a["pass"].tobytes())
        h.update(a["stratum"].tobytes())
        h.update("|".join(a["keys"]).encode())
    return h.hexdigest()


def cached_bootstrap(tds: dict[str, TaskData], classes: list[str], B: int, seed: int, scheme: str = "stratified",
                     edges: str = "all", workers: int = 6, n_sub: int = 200) -> dict[str, Any]:
    """run_bootstrap per task with a result cache under results/boot_cache/ (speed only; same replicates)."""
    cdir = RESULTS_DIR / "boot_cache"
    cdir.mkdir(exist_ok=True)
    out, todo, keys = {}, {}, {}
    for t, td in tds.items():
        k = td_key(td, classes, B, seed, scheme, edges, n_sub)
        keys[t] = k
        f = cdir / f"{t}_{scheme}_{edges}_{k[:16]}.json"
        if f.exists():
            out[t] = json.loads(f.read_text())
        else:
            todo[t] = td
    if todo:
        res = run_bootstrap(todo, classes, B, seed, scheme=scheme, n_sub=n_sub, edges=edges, workers=workers)
        for t, r in res.items():
            (cdir / f"{t}_{scheme}_{edges}_{keys[t][:16]}.json").write_text(json.dumps(r))
            out[t] = r
    logger.info(f"bootstrap {scheme}/{edges}: {len(tds) - len(todo)} tasks from cache, {len(todo)} computed")
    return out


def merge_samples() -> list[dict[str, Any]]:
    raw: dict[str, dict[str, Any]] = {}
    for r in read_jsonl(DATA_DIR / "samples_raw.jsonl"):
        raw.setdefault(r["sample_id"], r)
    labs: dict[str, dict[str, Any]] = {}
    for r in read_jsonl(DATA_DIR / "labels.jsonl"):
        labs.setdefault(r["sample_id"], r)
    out = []
    for sid, r in raw.items():
        l = labs.get(sid)
        if l is None:
            continue
        o = {k: r.get(k) for k in ("task", "arm", "knob_class", "template", "slot", "sample_id", "crn_key",
                                   "u_seed", "direction_seed", "alpha", "site", "temperature", "top_k", "min_p",
                                   "thinking", "prompt_kind", "prompt_sha256", "model", "engine", "max_new",
                                   "stop_rule", "batch_B", "finish_reason", "n_new_tokens", "realised_disp")}
        o.update({k: l.get(k) for k in ("label", "labeller_source", "passed", "valid", "runtime_label", "ast_label",
                                        "judge_label", "code_sha256", "code", "is_default")})
        out.append(o)
    write_jsonl(DATA_DIR / "samples.jsonl", out)
    logger.info(f"merged {len(out)} labelled samples ({len(raw) - len(out)} raw rows without a label)")
    return out


def load_other_map() -> dict[str, str] | None:
    p = AUDIT_DIR / "other_map.json"
    if not p.exists():
        return None
    return read_json(p)["by_code_sha256"]


def task_rows(samples: list[dict[str, Any]], reused: list[dict[str, Any]], task: str,
              include_reused: bool = True) -> list[dict[str, Any]]:
    rows = [r for r in samples if r["task"] == task]
    if include_reused:
        rr = [r for r in reused if r["task"] == task]
        if not any(r["arm"] == "REUSED_TWIN" for r in rr):
            # T1: no iteration-3 twin -> price the reused vetoes against this artifact's TWIN (flagged)
            rr += [dict(r, arm="REUSED_TWIN", sample_id="reftwin|" + r["sample_id"]) for r in rows
                   if r["arm"] == "TWIN"]
        rows += rr
    return rows


def triangle_check(td: TaskData, cls: str, U: np.ndarray, step: float = 0.05) -> float | None:
    """Best Hill at cost <= 5 over every 3-vertex face (grid step 0.05) minus the edge-search H5."""
    arms = class_vertices(td, cls)
    if arms is None or len(arms) < 3:
        return None
    R = np.array([td.vertex(a)[0] for a in arms])
    P = np.array([td.vertex(a)[1] for a in arms])
    h = Hull(R, P, U)
    g = np.arange(0, 1 + 1e-9, step)
    best = -np.inf
    for tri in itertools.combinations(range(len(arms)), 3):
        L = []
        for a in g:
            for b in g:
                if a + b <= 1 + 1e-9:
                    v = np.zeros(len(arms))
                    v[tri[0]], v[tri[1]], v[tri[2]] = 1 - a - b, a, b
                    L.append(v)
        hh, cc = h.eval_lams(np.array(L))
        ok = (cc <= 5 + 1e-9) & np.isfinite(hh)
        if ok.any():
            best = max(best, float(hh[ok].max()))
    e = h.summary(with_price=False)["H5"]
    return (best - e) if (np.isfinite(best) and e is not None) else None


def alt_h5(td: TaskData, cls: str, kind: str) -> float | None:
    """s8: Step-0 hypergeometric vertices only (no mixing): max over {ref} u settings with cost <= 5.
    s3: dial interpolation of the Step-0 vertex Hill along the dial."""
    arms = class_vertices(td, cls)
    if arms is None:
        return None
    pts = []
    p0 = td.vertex(arms[0])[1]
    for a in arms:
        cnt = td.counts(a)
        h = step0_hill(cnt) if sum(cnt.values()) > 0 else float("nan")
        c = 100 * (p0 - td.vertex(a)[1])
        pts.append((c, h))
    if kind == "s8":
        ok = [h for c, h in pts if c <= 5 and np.isfinite(h)]
        return max(ok) if ok else None
    return dial_interp_h5(pts)


def point_prices(tds: dict[str, TaskData]) -> dict[str, Any]:
    U = fixed_uniforms(1000)
    out: dict[str, Any] = {}
    for t, td in tds.items():
        out[t] = {}
        for c in PRICE_CLASSES:
            s = class_price(td, c, U, refine=True)
            if s is None:
                continue
            s1 = class_price(td, c, U, edges="twin", refine=True, with_price=False)
            s["H5_s1_twin_segment"] = s1["H5"] if s1 else None
            s["H5_s3_dial"] = alt_h5(td, c, "s3")
            s["H5_s8_step0_vertices"] = alt_h5(td, c, "s8")
            s["triangle_minus_edge"] = triangle_check(td, c, fixed_uniforms(300)) if c in ("PN", "TEMP",
                                                                                         "VETO_ITER") else None
            # vertex gap: population-rarefied (hull) vs Step-0 hypergeometric at each vertex
            gaps = []
            for a in s["arms"]:
                r, p, n = td.vertex(a)
                if r.sum() > 0 and sum(td.counts(a).values()) >= 25:
                    hp = Hull(r[None], np.array([p]), U).eval_lams(np.ones((1, 1)))[0][0]
                    gaps.append(float(step0_hill(td.counts(a)) - hp))
            s["max_vertex_gap_step0_minus_pop"] = max(gaps, key=abs) if gaps else None
            out[t][c] = s
    return out


def c1_all(point: dict[str, Any], boot: dict[str, Any], extra_boots: dict[str, Any]) -> dict[str, Any]:
    def h5_of(src: dict[str, Any], key: str = "H5") -> dict[str, dict[str, float | None]]:
        return {t: {c: v.get(key) for c, v in src[t].items()} for t in src}

    res: dict[str, Any] = {"utc": utc_now(), "rule": "predictions/c1_rule.json"}
    res["primary"] = c1_decide(h5_of(point), boot, E6, NA_PRIMARY, 2000, BOOT_SEED)
    res["s1_twin_segment_hull"] = c1_decide(h5_of(point, "H5_s1_twin_segment"), extra_boots.get("s1", {}), E6,
                                            NA_PRIMARY, 2000, BOOT_SEED + 1)
    res["s2_minp_vs_added"] = c1_decide(h5_of(point), boot, E6, NA_S2, 2000, BOOT_SEED + 2)
    # s2b (added after the run, labelled): min-p only, because 81% of VS programs are runtime random dispatchers
    # whose mechanism label depends on the branch the labeller's trace hit (results/vs_dispatch.json)
    res["s2b_minp_only_added"] = c1_decide(h5_of(point), boot, E6, NA_PRIMARY + ["MINP"], 2000, BOOT_SEED + 22)
    res["s3_dial_interpolation"] = c1_decide(h5_of(point, "H5_s3_dial"), extra_boots.get("s3", {}), E6, NA_PRIMARY,
                                             2000, BOOT_SEED + 3)
    res["s4_template_cluster_bootstrap"] = c1_decide(h5_of(point), extra_boots.get("s4", {}), E6, NA_PRIMARY, 2000,
                                                     BOOT_SEED + 4)
    res["s5_slot_paired_bootstrap"] = c1_decide(h5_of(point), extra_boots.get("s5", {}), E6, NA_PRIMARY, 2000,
                                                BOOT_SEED + 5)
    for conv in ("exclude", "one"):
        if f"s6_{conv}" in extra_boots:
            res[f"s6_other_{conv}"] = c1_decide(extra_boots[f"s6_{conv}_point"], extra_boots[f"s6_{conv}"], E6,
                                                NA_PRIMARY, 2000, BOOT_SEED + 6)
    na7 = [c for c in NA_PRIMARY if not c.startswith("VETO")]
    res["s7_reused_vetoes_excluded"] = c1_decide(h5_of(point), boot, E6, na7, 2000, BOOT_SEED + 7)
    res["s8_step0_vertices_only"] = c1_decide(h5_of(point, "H5_s8_step0_vertices"), extra_boots.get("s8", {}), E6,
                                              NA_PRIMARY, 2000, BOOT_SEED + 8)
    return res


def boot_alt(tds: dict[str, TaskData], B: int, seed: int, kind: str, workers: int) -> dict[str, Any]:
    """Bootstrap of the s3/s8 alternative H5 (Step-0 vertices, n_sub 200 inside replicates)."""
    import multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor

    jobs = [(td, kind, B, seed + i) for i, td in enumerate(tds.values())]
    out = {}
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as ex:
        for t, r in zip(tds, ex.map(_alt_worker, jobs)):
            out[t] = r
    return out


def _alt_worker(args: tuple) -> dict[str, Any]:
    from analysis.core import resample_idx
    from analysis.hull import dial_interp_h5 as dih

    td, kind, B, seed = args
    rng = np.random.default_rng(seed)
    res: dict[str, dict[str, list]] = {}
    for b in range(B):
        idx = resample_idx(td, rng)
        for c in BOOT_CLASSES:
            arms = class_vertices(td, c)
            if arms is None:
                continue
            pts = []
            p0 = float(td.arms[arms[0]]["pass"][idx[arms[0]]].mean())
            for a in arms:
                cat = td.arms[a]["cat"][idx[a]]
                cnt = np.bincount(cat[cat >= 0], minlength=len(td.cats))
                cc = cnt[cnt > 0]
                n = int(cc.sum())
                if n == 0:
                    h = np.nan
                elif len(cc) == 1:
                    h = 1.0
                else:
                    d = min(25, n)
                    h = rarefied_hill1(cc.tolist(), d, 200, rng)
                pts.append((100 * (p0 - float(td.arms[a]["pass"][idx[a]].mean())), h))
            if kind == "s8":
                ok = [h for cst, h in pts if cst <= 5 and np.isfinite(h)]
                v = max(ok) if ok else None
            else:
                v = dih(pts)
            res.setdefault(c, {"H5": []})["H5"].append(v)
    return res


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--boot-sens", type=int, default=1000, help="replicates for s1/s3/s4/s5/s6/s8 bootstraps")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--skip-boot", action="store_true")
    ap.add_argument("--boot-tasks", default="", help="comma list: restrict the primary bootstrap to these tasks")
    args = ap.parse_args()
    setup_logging("analysis")
    t0 = time.time()
    samples = merge_samples()
    reused = read_jsonl(DATA_DIR / "reused_rows.jsonl")
    omap = load_other_map()
    tasks = sorted({r["task"] for r in samples})
    tds = {t: TaskData(t, task_rows(samples, reused, t), omap) for t in tasks}
    # knob rows (Step-0 statistic per arm)
    ref_of = {"PNPLAIN_a1": "PLAIN", "VETO_1SHOT": "REUSED_TWIN", "VETO_PERSIST": "REUSED_TWIN",
              "VETO_ITER1": "REUSED_TWIN", "VETO_ITER2": "REUSED_TWIN", "VETO_ITER3": "REUSED_TWIN"}
    kr = knob_rows(tds, ref_of)
    write_jsonl(RESULTS_DIR / "knob_rows.jsonl", kr)
    logger.info(f"knob rows: {len(kr)} ({time.time() - t0:.0f}s)")
    point = point_prices(tds)
    write_json(RESULTS_DIR / "prices.json", point)
    logger.info(f"point prices done ({time.time() - t0:.0f}s)")
    if args.skip_boot:
        return
    btasks = [t for t in args.boot_tasks.split(",") if t] or list(tds)
    boot = cached_bootstrap({t: tds[t] for t in btasks if t in tds}, BOOT_CLASSES, args.boot, BOOT_SEED,
                            workers=args.workers)
    write_json(RESULTS_DIR / "bootstrap_primary.json", {t: {c: {k: v for k, v in d.items()} for c, d in bt.items()}
                                                         for t, bt in boot.items()}, indent=None)
    logger.info(f"primary bootstrap done ({time.time() - t0:.0f}s)")
    e6 = {t: tds[t] for t in E6 if t in tds}
    extra: dict[str, Any] = {}
    Bs = args.boot_sens
    extra["s1"] = cached_bootstrap(e6, BOOT_CLASSES, Bs, BOOT_SEED + 11, edges="twin", workers=args.workers)
    extra["s4"] = cached_bootstrap(e6, BOOT_CLASSES, Bs, BOOT_SEED + 14, scheme="template_cluster",
                                   workers=args.workers)
    extra["s5"] = cached_bootstrap(e6, BOOT_CLASSES, Bs, BOOT_SEED + 15, scheme="slot_paired", workers=args.workers)
    extra["s3"] = boot_alt(e6, Bs, BOOT_SEED + 13, "s3", args.workers)
    extra["s8"] = boot_alt(e6, Bs, BOOT_SEED + 18, "s8", args.workers)
    logger.info(f"sensitivity bootstraps done ({time.time() - t0:.0f}s)")
    if omap is not None:
        U = fixed_uniforms(1000)
        for conv in ("exclude", "one"):
            tdc = {t: TaskData(t, task_rows(samples, reused, t), omap, conv) for t in E6 if t in tds}
            extra[f"s6_{conv}_point"] = {t: {c: (s["H5"] if (s := class_price(tdc[t], c, U)) else None)
                                             for c in BOOT_CLASSES} for t in tdc}
            extra[f"s6_{conv}"] = cached_bootstrap(tdc, BOOT_CLASSES, Bs, BOOT_SEED + 16, scheme=f"stratified_{conv}",
                                                   workers=args.workers)
    c1 = c1_all(point, boot, extra)
    # bootstrap intervals of each class's H5 / P15 / P20 per task
    cis = {}
    for t, bt in boot.items():
        cis[t] = {}
        for c, d in bt.items():
            p15 = [x for x in d["P15"]]
            cis[t][c] = {"H5_ci95": pct_ci(d["H5"]), "P15_ci95": pct_ci(p15), "P20_ci95": pct_ci(d["P20"]),
                         "share_reaching_1.5": float(np.mean([x is not None for x in p15])) if p15 else None,
                         "share_reaching_2.0": float(np.mean([x is not None for x in d["P20"]])) if d["P20"] else None}
    c1["class_ci"] = cis
    write_json(RESULTS_DIR / "c1.json", c1)
    logger.info(f"C1 primary: {c1['primary']['verdict']} (count1 {c1['primary']['count1']}, count2 "
                f"{c1['primary']['count2']}, D_bar {c1['primary']['D_bar']}, CI {c1['primary']['D_bar_ci95']}); "
                f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
