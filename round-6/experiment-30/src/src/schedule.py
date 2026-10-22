#!/usr/bin/env python3
"""Decisive schedule: cells, execution priorities and fixed-shape batches (exp20 schedule.py, this plan's cells).

Arms: TWIN (alpha 0), <site>_a<alpha> for S0/S4/S5/S1/S2/S3/S1E, TOP5_a<alpha> (the request's top-five prohibition
as a plan-site push: T03 top-5, T10 all-but-one, T1 iteration-4 u_top5), TOP3_a<alpha> (T03 top-3 variant),
ENG_r9002_a1 / ENG_r9004_a1 (positive control U8, not decisive), TWIN_X (filler twin rows on k >= 10 completing the
last batch of a (task, template); descriptive only). S3 rows come in atomic (hooked, shadow) pairs.

Execution priority (lower runs first; the plan's drop order is the reverse of execution, time-based only):
  10 P1 twins T03/T10/T2 (N 50)                 20 P2 T03/T10 x S0,S4,S1,S2,S5,S3 x alpha 1/2/4 (N 30; S2 k 0-3)
  30 P3 S1E T03/T10 alpha 1/2/4 (N 30)          40 P4 T2 x S0,S4,S5,S1,S2,S3 x alpha 2/4 (N 30)
  50 P5 T03 TOP5 alpha 1/2/4 (N 50)             51 P5 T1 twin, T1 TOP5 alpha 1/2/4, T1 S0 random control a1/a2 (N 50)
  55 S2 k 4-5 (T03/T10; drop step 6)            56 S1E on T2 (drop step 5)
  57 T10 all-but-one push (drop step 4)         58 T1 random control alpha 4 (drop step 3)
  59 T03 top-3 variant (drop step 2)            60 P6(a) S4 alpha 8 on T03/T10 (N 30)
  61 P6(b) top-up k 6-9 on T10                  62 P6(b) top-up k 6-9 on T03
"""

from __future__ import annotations

from typing import Any

from cfg import BATCH, FILL_K0, N30_K, N50_K, SMOKE_K0, TEMPLATE_IDS, TOPUP_K

TASK_ORDER = {"T03": 0, "T10": 1, "T2": 2, "T1": 3}
PRIO_NAMES = {10: "P1 twins", 20: "P2 site grid T03/T10", 30: "P3 S1E T03/T10", 40: "P4 T2 grid",
              50: "P5 T03 TOP5", 51: "P5 T1 twin/TOP5/RC a1-2", 55: "S2 k4-5", 56: "S1E T2", 57: "T10 TOP5 push",
              58: "T1 RC a4", 59: "T03 TOP3", 60: "P6a S4 a8", 61: "P6b T10 top-up", 62: "P6b T03 top-up"}


def arm_name(site: str, alpha: float) -> str:
    return f"{site}_a{alpha:g}"


def parse_arm(arm: str) -> tuple[str, float]:
    if arm in ("TWIN", "TWIN_X"):
        return arm, 0.0
    site, a = arm.rsplit("_a", 1)
    if site.startswith("ENG"):
        return "ENG", float(a)
    return site, float(a)


def _row(task: str, w: str, k: int, arm: str, prio: int, shadow: bool = False) -> dict[str, Any]:
    site, alpha = parse_arm(arm)
    return {"task": task, "w": w, "k": k, "arm": arm, "site": site, "alpha": alpha, "prio": prio, "shadow": shadow}


def cell_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(task, arm, ks, prio):
        for w in TEMPLATE_IDS:
            for k in ks:
                rows.append(_row(task, w, k, arm, prio))
                if arm.startswith("S3_"):
                    rows.append(_row(task, w, k, arm, prio, shadow=True))

    for t in ("T03", "T10", "T2"):
        add(t, "TWIN", N50_K, 10)
    for t in ("T03", "T10"):
        for a in (1.0, 2.0, 4.0):
            for s in ("S0", "S4", "S1", "S5", "S3"):
                add(t, arm_name(s, a), N30_K, 20)
            add(t, arm_name("S2", a), N30_K[:4], 20)
            add(t, arm_name("S2", a), N30_K[4:], 55)
            add(t, arm_name("S1E", a), N30_K, 30)
    for a in (2.0, 4.0):
        for s in ("S0", "S4", "S5", "S1", "S2", "S3"):
            add("T2", arm_name(s, a), N30_K, 40)
        add("T2", arm_name("S1E", a), N30_K, 56)
    for a in (1.0, 2.0, 4.0):
        add("T03", arm_name("TOP5", a), N50_K, 50)
    add("T1", "TWIN", N50_K, 51)
    for a in (1.0, 2.0, 4.0):
        add("T1", arm_name("TOP5", a), N50_K, 51)
    for a in (1.0, 2.0):
        add("T1", arm_name("S0", a), N50_K, 51)
    add("T1", arm_name("S0", 4.0), N50_K, 58)
    for a in (1.0, 2.0, 4.0):
        add("T10", arm_name("TOP5", a), N50_K, 57)
        add("T03", arm_name("TOP3", a), N50_K, 59)
    for t in ("T03", "T10"):
        add(t, arm_name("S4", 8.0), N30_K, 60)
    for t, pr in (("T10", 61), ("T03", 62)):
        for a in (1.0, 2.0, 4.0):
            for s in ("S0", "S4", "S1", "S2", "S5"):
                add(t, arm_name(s, a), TOPUP_K, pr)
    return rows


def eng_rows() -> list[dict[str, Any]]:
    rows = []
    for t, s in (("T03", 9002), ("T2", 9004)):
        for w in TEMPLATE_IDS:
            for k in N50_K:
                rows.append(_row(t, w, k, f"ENG_r{s}_a1", 0))
    return rows


def _units(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Group S3 hooked rows with their shadow (atomic pairs); keep order."""
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


def pack(rows: list[dict[str, Any]], fill_k0: int = FILL_K0) -> list[dict[str, Any]]:
    """-> batches [{'task','w','rows','min_prio','id'}], each exactly BATCH[task] rows of one (task, template)."""
    by: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for r in rows:
        by.setdefault((r["task"], r["w"]), []).append(r)
    batches = []
    for (t, w), rs in by.items():
        bsz = BATCH[t]
        rs = sorted(rs, key=lambda r: (r["prio"], r["arm"], r["k"], r["shadow"]))
        units = _units(rs)
        cur: list[dict[str, Any]] = []
        fill_k = fill_k0
        while units:
            u = units.pop(0)
            if len(cur) + len(u) > bsz:
                j = next((j for j, v in enumerate(units) if len(cur) + len(v) <= bsz), None)
                if j is not None:
                    units.insert(0, u)
                    u = units.pop(j + 1)
                else:
                    while len(cur) < bsz:
                        cur.append(_row(t, w, fill_k, "TWIN_X", 99))
                        fill_k += 1
                    batches.append(cur)
                    cur = []
            cur.extend(u)
            if len(cur) == bsz:
                batches.append(cur)
                cur = []
        if cur:
            while len(cur) < bsz:
                cur.append(_row(t, w, fill_k, "TWIN_X", 99))
                fill_k += 1
            batches.append(cur)
    out = []
    for b in batches:
        mp = min(r["prio"] for r in b)
        out.append({"task": b[0]["task"], "w": b[0]["w"], "rows": b, "min_prio": mp})
    out.sort(key=lambda b: (b["min_prio"], TASK_ORDER.get(b["task"], 99), b["w"]))
    for i, b in enumerate(out):
        b["id"] = f"B{i:04d}:{b['task']}:{b['w']}:P{b['min_prio']}"
    return out


def smoke_rows() -> list[dict[str, Any]]:
    """Mini batch per site type on reserved slots k >= 100 (never analysed): T03 W1, alpha 2, 2 slots each."""
    rows = []
    t = "T03"
    for arm in ("TWIN", "S0_a2", "S4_a2", "S5_a2", "S1_a2", "S2_a2", "S1E_a2", "S3_a2", "TOP5_a2"):
        for k in (SMOKE_K0 + 10, SMOKE_K0 + 11):
            site, alpha = parse_arm(arm)
            rows.append({"task": t, "w": "W1", "k": k, "arm": "SMOKE_" + arm, "site": site, "alpha": alpha,
                         "prio": 0, "shadow": False})
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
            "programs_by_priority": {f"{k} {PRIO_NAMES.get(k, '')}": v for k, v in sorted(by_prio.items())},
            "batch_shape": BATCH}
