#!/usr/bin/env python3
"""STEP 9 schedule: rows per cell, priorities P1-P9, and fixed-shape batches (20 rows of one (task, template)).

Arms: TWIN (alpha 0), <site>_a<alpha> for S0-S5/S1E/S2E, TOP5_a<alpha> (T1), ENG_r9002_a1 (T03) / ENG_r9004_a1 (T2)
(engine check), TWIN_X (filler twin rows on k >= 10 that complete the last batch of a (task, template); descriptive
only). S3 rows come in atomic (hooked, shadow) pairs; shadows are not programs.
Batches are packed per (task, template) in priority order, then ordered globally by their lowest priority, so the
never-drop cells (P1-P3) finish first and a time overrun drops the lowest priorities first.
"""

from __future__ import annotations

from typing import Any

from cfg import BATCH, FILL_K0, N50_K, N_GRID_K, SMOKE_K0, TASKS, TEMPLATE_IDS

PRIO_NAMES = {1: "P1 twin + engine check", 2: "P2 S0/S1/S3 a1,a2", 3: "P3 S0 a8 (N50)", 4: "P4 S2/S4/S5 a1,a2",
              5: "P5 S0/S1/S2/S3 a4", 6: "P6 TOP5 a1/2/4 + PN-T1 top-up a1,a2", 7: "P7 S4/S5 a4",
              8: "P8 PN-T1 top-up a4", 9: "P9 S1E/S2E a1"}


def arm_name(site: str, alpha: float) -> str:
    return f"{site}_a{alpha:g}"


def parse_arm(arm: str) -> tuple[str, float]:
    """'S0_a2' -> ('S0', 2.0); 'TWIN' -> ('TWIN', 0.0); 'ENG_r9002_a1' -> ('ENG', 1.0)."""
    if arm in ("TWIN", "TWIN_X"):
        return arm, 0.0
    site, a = arm.rsplit("_a", 1)
    if site.startswith("ENG"):
        return "ENG", float(a)
    return site, float(a)


def _row(task: str, w: str, k: int, arm: str, prio: int, shadow: bool = False) -> dict[str, Any]:
    site, alpha = parse_arm(arm)
    return {"task": task, "w": w, "k": k, "arm": arm, "site": site, "alpha": alpha, "prio": prio, "shadow": shadow}


def cell_rows(tasks: tuple[str, ...] = TASKS) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(task, arm, ks, prio):
        for w in TEMPLATE_IDS:
            for k in ks:
                rows.append(_row(task, w, k, arm, prio))
                if arm.startswith("S3_"):
                    rows.append(_row(task, w, k, arm, prio, shadow=True))

    for t in tasks:
        add(t, "TWIN", N50_K, 1)
        if t == "T03":
            add(t, "ENG_r9002_a1", N50_K, 1)
        if t == "T2":
            add(t, "ENG_r9004_a1", N50_K, 1)
        for a in (1.0, 2.0):
            for s in ("S0", "S1", "S3"):
                add(t, arm_name(s, a), N_GRID_K, 2)
        add(t, arm_name("S0", 8.0), N50_K, 3)
        for a in (1.0, 2.0):
            for s in ("S2", "S4", "S5"):
                add(t, arm_name(s, a), N_GRID_K, 4)
        for s in ("S0", "S1", "S2", "S3"):
            add(t, arm_name(s, 4.0), N_GRID_K, 5)
        if t == "T1":
            for a in (1.0, 2.0, 4.0):
                add(t, arm_name("TOP5", a), N50_K, 6)
            for a in (1.0, 2.0):
                add(t, arm_name("S0", a), [6, 7, 8, 9], 6)
            add(t, arm_name("S0", 4.0), [6, 7, 8, 9], 8)
        for s in ("S4", "S5"):
            add(t, arm_name(s, 4.0), N_GRID_K, 7)
        for s in ("S1E", "S2E"):
            add(t, arm_name(s, 1.0), N_GRID_K, 9)
    return rows


def _units(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Group S3 hooked rows with their shadow (atomic pairs); keep priority order."""
    out, i = [], 0
    while i < len(rows):
        r = rows[i]
        if r["site"] == "S3" and not r["shadow"]:
            sh = rows[i + 1]
            assert sh["shadow"] and sh["k"] == r["k"] and sh["arm"] == r["arm"]
            out.append([r, sh])
            i += 2
        else:
            out.append([r])
            i += 1
    return out


def pack(rows: list[dict[str, Any]], batch: int = BATCH, fill_k0: int = FILL_K0) -> list[dict[str, Any]]:
    """-> batches [{'task','w','rows','min_prio','id'}], each exactly `batch` rows of one (task, template)."""
    by: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for r in rows:
        by.setdefault((r["task"], r["w"]), []).append(r)
    batches = []
    for (t, w), rs in by.items():
        rs = sorted(rs, key=lambda r: (r["prio"], r["arm"], r["k"], r["shadow"]))
        units = _units(rs)
        cur: list[dict[str, Any]] = []
        fill_k = fill_k0
        while units:
            u = units.pop(0)
            if len(cur) + len(u) > batch:
                j = next((j for j, v in enumerate(units) if len(cur) + len(v) <= batch), None)
                if j is not None:
                    units.insert(0, u)
                    u = units.pop(j + 1)
                else:
                    while len(cur) < batch:
                        cur.append(_row(t, w, fill_k, "TWIN_X", 10))
                        fill_k += 1
                    batches.append(cur)
                    cur = []
            cur.extend(u)
            if len(cur) == batch:
                batches.append(cur)
                cur = []
        if cur:
            while len(cur) < batch:
                cur.append(_row(t, w, fill_k, "TWIN_X", 10))
                fill_k += 1
            batches.append(cur)
    order = {t: i for i, t in enumerate(TASKS)}
    out = []
    for b in batches:
        mp = min(r["prio"] for r in b)
        out.append({"task": b[0]["task"], "w": b[0]["w"], "rows": b, "min_prio": mp})
    out.sort(key=lambda b: (b["min_prio"], order.get(b["task"], 99), b["w"]))
    for i, b in enumerate(out):
        b["id"] = f"B{i:04d}:{b['task']}:{b['w']}:P{b['min_prio']}"
    return out


def smoke_rows() -> list[dict[str, Any]]:
    """Stage 10: 4 rows of every arm type on reserved slots k 100-103 (never analysed), T03 and T1, template W1."""
    rows = []
    for t in ("T03", "T1"):
        for arm in ("S0_a1", "S1_a1", "S2_a1", "S3_a1", "S4_a1", "S5_a1", "S1E_a1", "S2E_a1", "S0_a8") + \
                (("TOP5_a1",) if t == "T1" else ()):
            for k in range(SMOKE_K0, SMOKE_K0 + 4):
                rows.append(_row(t, "W1", k, "SMOKE_" + arm, 0))
                rows[-1]["site"], rows[-1]["alpha"] = parse_arm(arm)
                if arm.startswith("S3_"):
                    rows.append(dict(rows[-1], shadow=True))
    return rows


def summary(batches: list[dict[str, Any]]) -> dict[str, Any]:
    n_prog = sum(1 for b in batches for r in b["rows"] if not r["shadow"] and r["arm"] != "TWIN_X")
    n_sh = sum(1 for b in batches for r in b["rows"] if r["shadow"])
    n_fill = sum(1 for b in batches for r in b["rows"] if r["arm"] == "TWIN_X")
    by_prio: dict[int, int] = {}
    for b in batches:
        for r in b["rows"]:
            if not r["shadow"] and r["arm"] != "TWIN_X":
                by_prio[r["prio"]] = by_prio.get(r["prio"], 0) + 1
    return {"n_batches": len(batches), "n_programs": n_prog, "n_shadow_rows": n_sh, "n_filler_twin_rows": n_fill,
            "programs_by_priority": {f"P{k}": v for k, v in sorted(by_prio.items())}}
