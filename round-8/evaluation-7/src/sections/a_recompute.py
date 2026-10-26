#!/usr/bin/env python3
"""STEP A5: recompute what the relabel touches with exp33's own definitions (a line-for-line port of
exp33 src/analysis7.py p1_task / pooled_recovery / boot_ci / routing: slot-cluster bootstrap, 2,000 resamples,
numpy default_rng(20261022), percentile 2.5/97.5). Placebo first: under the OLD labels the port must reproduce
Tables 293 and 295 (shortest path, connected components) and the old kth smallest values (1.59 / 1.57 / 1.55)."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

import numpy as np

from sections.common import clopper_pearson, dep, read_json, read_jsonl, src_ref

N = 30
BOOT = 2000
SEED = 20261022
RANKS = (1, 2, 4, 8, 16)
DEFAULT = {"T2": "dijkstra", "T10": "union_find", "T03": "full_sort"}


def load_rows() -> list[dict[str, Any]]:
    return read_jsonl(dep("exp33", "data/labels.jsonl"))


def arms_of(rows: list[dict[str, Any]], task: str, override: dict[str, str] | None = None
            ) -> dict[str, dict[int, dict[str, Any]]]:
    out: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    for r in rows:
        if r["task"] == task:
            rr = r
            if override and r["sample_id"] in override:
                rr = {**r, "label": override[r["sample_id"]]}
            out[r["arm"]][int(r["slot_index"])] = rr
    return out


def cy(r: dict[str, Any] | None, Y: list[str]) -> int:
    return int(bool(r) and bool(r.get("passed")) and r.get("label") in Y)


def vec(A: dict, arm: str | None, Y: list[str]) -> np.ndarray | None:
    if not arm or arm not in A:
        return None
    return np.array([cy(A[arm].get(s), Y) for s in range(N)])


def pass_rate(A: dict, arm: str) -> float | None:
    if arm not in A:
        return None
    rs = [A[arm].get(s) for s in range(N) if A[arm].get(s)]
    return float(np.mean([bool(r.get("passed")) for r in rs])) if rs else None


def sources(task: str) -> list[dict[str, Any]]:
    T = read_json(dep("exp33", f"results/targets_{task}.json"))
    ks = read_json(dep("exp33", f"results/kstar_{task}.json"))
    site = read_json(dep("exp33", f"results/site_{task}.json"))
    full = "FULL_ban_band" if site["site"] == "band" else f"FULL_ban_L{site['L_star']}"
    landing = T["landing"] or T["kept_Y"][:1]
    k = ks["k_star"]
    out = [{"name": "ban", "Y": landing, "base": "BASE_W5", "full": full,
            "das": {kk: f"DASLY_ban_k{kk}" for kk in RANKS},
            "rand": {16: ["RAND_ban_k16_d1", "RAND_ban_k16_d2", "RAND_ban_k16_d3"],
                     k: ([f"RAND_ban_k{k}"] if k != 16 else ["RAND_ban_k16_d1", "RAND_ban_k16_d2", "RAND_ban_k16_d3"])},
            "perm": {16: "PERMLY_ban_k16", k: f"PERMLY_ban_k{k}"}}]
    for Y in ks["kept_Y_cells"]:
        out.append({"name": f"F_{Y}", "Y": [Y], "base": "BASE_PAD", "full": f"FULL_F_{Y}",
                    "das": {kk: f"DASLY_F_{Y}_k{kk}" for kk in (1, 4, 16)}, "rand": {16: [f"RAND_F_{Y}_k16"]},
                    "perm": {16: f"PERMLY_F_{Y}_k16"}})
    return out


def pooled_recovery(A: dict, srcs: list[dict[str, Any]], k: int, slots: np.ndarray | None = None,
                    which: str = "das") -> tuple[float | None, float, float]:
    num = den = 0.0
    for s in srcs:
        b, f = vec(A, s["base"], s["Y"]), vec(A, s["full"], s["Y"])
        arms = ([s["das"].get(k)] if s["das"].get(k) else []) if which == "das" else s["rand"].get(k, [])
        vs = [v for v in (vec(A, a, s["Y"]) for a in arms) if v is not None]
        if b is None or f is None or not vs:
            continue
        idx = slots if slots is not None else np.arange(N)
        x = float(np.mean([v[idx].sum() for v in vs]))
        num += x - b[idx].sum()
        den += f[idx].sum() - b[idx].sum()
    return (num / den if den > 0 else None), num, den


def boot_ci(A: dict, srcs: list[dict[str, Any]], k: int, which: str = "das", seed: int = SEED,
            n_boot: int = BOOT) -> list[float | None]:
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, N, N)
        r, _, _ = pooled_recovery(A, srcs, k, idx, which)
        if r is not None:
            vals.append(r)
    if len(vals) < 100:
        return [None, None]
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def p1_task(rows: list[dict[str, Any]], task: str, override: dict[str, str] | None = None) -> dict[str, Any]:
    A = arms_of(rows, task, override)
    srcs = sources(task)
    ks = read_json(dep("exp33", f"results/kstar_{task}.json"))["k_star"]
    out: dict[str, Any] = {"per_k": {}, "per_source": {}}
    for s in srcs:
        b, f = vec(A, s["base"], s["Y"]), vec(A, s["full"], s["Y"])
        if b is None or f is None:
            continue
        ps = {"Y": s["Y"], "base_count": int(b.sum()), "full_count": int(f.sum()),
              "full_transfer": float((f.sum() - b.sum()) / N), "base_pass": pass_rate(A, s["base"]),
              "full_pass": pass_rate(A, s["full"]), "das": {}, "perm": {}, "rand": {}}
        for k, a in s["das"].items():
            v = vec(A, a, s["Y"])
            if v is not None:
                ps["das"][k] = {"count": int(v.sum()), "transfer": float((v.sum() - b.sum()) / N),
                                "recovery": float((v.sum() - b.sum()) / (f.sum() - b.sum())) if f.sum() > b.sum() else None,
                                "pass": pass_rate(A, a), "share_ci": clopper_pearson(int(v.sum()), N)}
        for k, arms in s["rand"].items():
            for a in arms:
                v = vec(A, a, s["Y"])
                if v is not None:
                    ps["rand"][a] = {"count": int(v.sum()), "transfer": float((v.sum() - b.sum()) / N)}
        for k, a in s["perm"].items():
            v = vec(A, a, s["Y"])
            if v is not None:
                ps["perm"][a] = {"count": int(v.sum()), "transfer": float((v.sum() - b.sum()) / N),
                                 "relative_to_full": float((v.sum() - b.sum()) / (f.sum() - b.sum()))
                                 if f.sum() > b.sum() else None}
        out["per_source"][s["name"]] = ps
    cand = sorted({16, ks})
    for k in RANKS:
        r, num, den = pooled_recovery(A, srcs, k)
        rr = pooled_recovery(A, srcs, k, which="rand")[0] if k in cand else None
        e = {"recovery": r, "num": num, "den": den, "recovery_ci": boot_ci(A, srcs, k) if r is not None else None,
             "random_recovery": rr}
        if k in cand:
            perm = []
            for s in srcs:
                a = s["perm"].get(k)
                b, v = vec(A, s["base"], s["Y"]), vec(A, a, s["Y"])
                if v is not None and b is not None:
                    perm.append(float((v.sum() - b.sum()) / N))
            e["permuted_transfer_max"] = max(perm) if perm else None
        out["per_k"][k] = e
    return out


def routing_cell(rows: list[dict[str, Any]], task: str, arm: str, Y: str, override: dict[str, str] | None = None
                 ) -> dict[str, Any]:
    A = arms_of(rows, task, override)
    rs = [A[arm][s] for s in range(N) if s in A.get(arm, {})]
    corr = [r for r in rs if r.get("passed")]
    offd = [r for r in corr if r["label"] != DEFAULT[task]]
    ny = sum(r["label"] == Y for r in corr)
    return {"n": len(rs), "correct_Y": ny, "correct_off_default": len(offd),
            "routing": ny / len(offd) if offd else None, "routing_ci": clopper_pearson(ny, len(offd)) if offd else None,
            "landing": dict(Counter(r["label"] for r in corr)), "fail": len(rs) - len(corr)}


def run(final_map: dict[str, str]) -> dict[str, Any]:
    """final_map: sample_id -> new label for every T03 row (rule_v2, or the adjudicated label where adjudicated)."""
    rows = load_rows()
    p1 = read_json(dep("exp33", "results/p1.json"))["tasks"]
    res: dict[str, Any] = {"placebo": {}, "old": {}, "new": {}}
    # placebo 1: the port under OLD labels reproduces exp33's per_k (point and CI) on all three tasks
    for t in ("T2", "T10", "T03"):
        mine = p1_task(rows, t)
        res["old"][t] = mine
        chk = []
        for k in RANKS:
            ex, me = p1[t]["per_k"][str(k)], mine["per_k"][k]
            ok = (ex["recovery"] is None and me["recovery"] is None) or (
                ex["recovery"] is not None and me["recovery"] is not None and abs(ex["recovery"] - me["recovery"]) < 1e-9
                and (ex["recovery_ci"] is None or (abs(ex["recovery_ci"][0] - me["recovery_ci"][0]) < 1e-9 and
                                                   abs(ex["recovery_ci"][1] - me["recovery_ci"][1]) < 1e-9)))
            chk.append({"k": k, "exp33": [ex["recovery"], ex["recovery_ci"]],
                        "port": [me["recovery"], me["recovery_ci"]], "match": bool(ok)})
        res["placebo"][t] = {"rows": chk, "all_match": all(c["match"] for c in chk)}
    # new labels on kth smallest
    res["new"]["T03"] = p1_task(rows, "T03", final_map)
    res["routing"] = {
        "old_full_counting": routing_cell(rows, "T03", "FULL_F_counting_sort", "counting_sort"),
        "new_full_counting": routing_cell(rows, "T03", "FULL_F_counting_sort", "counting_sort", final_map),
        "new_das_counting": {f"k{k}": routing_cell(rows, "T03", f"DASLY_F_counting_sort_k{k}", "counting_sort", final_map)
                             for k in (1, 4, 16)},
    }
    # 29 of the 36 catalogue variants of 7.3.9 come from FULL_F_counting_sort?
    na = read_json(dep("exp33", "results/novelty_audit.json"))
    res["novelty_audit"] = novelty_by_cell(na)
    res["source"] = src_ref("exp33", "data/labels.jsonl") + " + " + src_ref("exp33", "src/analysis7.py", "p1_task")
    return res


def novelty_by_cell(na: Any) -> dict[str, Any]:
    """Count the novelty-audit programs (correct, labelled other) by source cell and final class."""
    items = None
    if isinstance(na, dict):
        for k in ("items", "programs", "rows", "audited", "results"):
            if isinstance(na.get(k), list):
                items = na[k]
                break
    if items is None:
        return {"error": "no item list found", "keys": list(na.keys()) if isinstance(na, dict) else None}
    by = Counter()
    by_cls = Counter()
    for it in items:
        cell = it.get("arm") or it.get("cell") or (it.get("sample_id", "").split("|")[1] if "|" in it.get("sample_id", "") else None)
        cls = it.get("final_class") or it.get("class") or it.get("verdict") or it.get("label")
        by[(it.get("task"), cell)] += 1
        by_cls[(cell, cls)] += 1
    return {"n": len(items), "by_cell": {f"{t}|{c}": n for (t, c), n in by.most_common()},
            "by_cell_class": {f"{c}|{k}": n for (c, k), n in by_cls.most_common()}}
