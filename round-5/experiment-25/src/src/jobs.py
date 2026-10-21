#!/usr/bin/env python3
"""Job builders for the GPU queue (queue/<id>.json). Priorities: P0 engine check/tests, P1 early draws (twins, base
pilots), P2 twins, P3 base repertoire, P4 rivals, P5 new-unit push arms, P6 Extra arm A, P7 sensitivities."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg5 import (ALPHAS, ESC_SEEDS, K_PN, K_STAGE1, K_T13, K_TWIN, N_ASSOC, N_NOVELTY, N_PLAIN, PATH_TASKS,  # noqa
                  QUEUE, TEMPLATE_IDS, utc_now, write_json)


def enqueue(jid: str, prio: int, model: str, task: str, batches: list[dict[str, Any]] | None = None,
            kind: str = "sample", requires: list[str] | None = None, out_file: str | None = None) -> Path:
    p = QUEUE / f"{jid}.json"
    if p.exists() or (QUEUE / "done" / p.name).exists():
        return p
    write_json(p, {"id": jid, "prio": prio, "model": model, "task": task, "kind": kind, "batches": batches or [],
                   "requires": requires or [], "out_file": out_file, "created": utc_now()}, indent=None)
    return p


def per_w(spec: list[tuple[str, list[int]]], templates: list[str] | None = None) -> list[dict[str, Any]]:
    return [{"w": w, "spec": spec} for w in (templates or TEMPLATE_IDS)]


def chunks(n: int, size: int) -> list[list[int]]:
    ks = list(range(n))
    return [ks[i:i + size] for i in range(0, n, size)]


def twin_job(task: str, prio: int, requires: list[str] | None = None, tag: str = "twin") -> Path:
    if task in PATH_TASKS:
        b = [{"w": w, "spec": [("TWIN", K_TWIN)]} for w in TEMPLATE_IDS]
    else:
        b = per_w([("TWIN", K_TWIN)])
    return enqueue(f"P{prio}_{tag}_{task}", prio, "instruct", task, b, requires=requires)


def base_job(task: str, prio: int = 3) -> Path:
    b = per_w([("BASE", list(range(0, 20)))])
    return enqueue(f"P{prio}_base_{task}", prio, "base", task, b)


def plainc_job(task: str, prio: int = 7) -> Path:
    b = [{"w": "PLAINC", "spec": [("PLAINC", ks)]} for ks in chunks(N_PLAIN, 25)]
    return enqueue(f"P{prio}_plainc_{task}", prio, "base", task, b)


def novelty_job(task: str, prio: int = 4) -> Path:
    b = [{"w": "ALL", "spec": [("NOVELTY", ks)]} for ks in chunks(N_NOVELTY, 15)]
    return enqueue(f"P{prio}_novelty_{task}", prio, "instruct", task, b)


def assoc_job(task: str, prio: int = 4) -> Path:
    b = [{"w": "ASSOC", "spec": [("ASSOC", list(range(N_ASSOC)))]}]
    return enqueue(f"P{prio}_assoc_{task}", prio, "instruct", task, b)


def states_job(task: str, prio: int = 2) -> Path:
    return enqueue(f"P{prio}_states_{task}", prio, "instruct", task, kind="states")


def margin_job(task: str, prio: int = 4, requires: list[str] | None = None) -> Path:
    return enqueue(f"P{prio}_margin_{task}", prio, "instruct", task, kind="margin", requires=requires)


def escape_stage1_job(task: str, prio: int, requires: list[str]) -> Path:
    """8 directions x alpha {1, 2} x k 0-1 x W1-W5; one batch per (w, alpha) holds the 8 directions (16 rows)."""
    b = []
    for a in ALPHAS:
        for w in TEMPLATE_IDS:
            spec = [(f"ESC_d{s}_a{a}", K_STAGE1) for s in ESC_SEEDS]
            if task in PATH_TASKS:  # 1,536 new tokens: half batches (8 rows) to fit the KV cache
                b.append({"w": w, "spec": spec[:4]})
                b.append({"w": w, "spec": spec[4:]})
            else:
                b.append({"w": w, "spec": spec})
    return enqueue(f"P{prio}_esc1_{task}", prio, "instruct", task, b, requires=requires)


def topup_job(task: str, cells: list[tuple[int, float]], prio: int, requires: list[str]) -> Path | None:
    if not cells:
        return None
    b = []
    per = 2 if task in PATH_TASKS else 5
    for w in TEMPLATE_IDS:
        for i in range(0, len(cells), per):
            b.append({"w": w, "spec": [(f"ESC_d{s}_a{a}", [2, 3, 4, 5]) for s, a in cells[i:i + per]]})
    tag = "_".join(f"{s}a{int(a)}" for s, a in cells)
    return enqueue(f"P{prio}_topup_{task}_{tag}"[:150], prio, "instruct", task, b, requires=requires)


def pn_job(task: str, alpha: float, prio: int, requires: list[str]) -> Path:
    b = per_w([(f"PN_a{alpha}", K_PN)])
    return enqueue(f"P{prio}_pn{int(alpha)}_{task}", prio, "instruct", task, b, requires=requires)


def t13_job(task: str, prio: int, requires: list[str]) -> Path:
    b = per_w([("T1.3", K_T13)])
    return enqueue(f"P{prio}_t13_{task}", prio, "instruct", task, b, requires=requires)


def enginecheck_jobs() -> list[Path]:
    out = []
    for task, seed in (("T03", 9002), ("T2", 9004)):
        b = per_w([("ECTWIN", K_TWIN), (f"ECBAN_d{seed}_a1.0", K_TWIN)])
        if task in PATH_TASKS:
            b = []
            for w in TEMPLATE_IDS:
                b.append({"w": w, "spec": [("ECTWIN", K_TWIN)]})
                b.append({"w": w, "spec": [(f"ECBAN_d{seed}_a1.0", K_TWIN)]})
        out.append(enqueue(f"P0_enginecheck_{task}", 0, "instruct", task, b, out_file="enginecheck.jsonl"))
    return out
