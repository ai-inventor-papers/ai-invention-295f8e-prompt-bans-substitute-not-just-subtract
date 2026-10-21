"""Reference programs (the defaults' baseline programs) and forced programs (labelled as requested) per task, plus
the capability ceiling can(A) = #(plain forced attempts labelled A AND passed) / #(plain forced attempts for A).

Sources (all copied into inputs/):
- T1/T2 refs: exp8 data/samples.jsonl arm b (neutral twins, bf16, N=100 per task).
- T1/T2 forced: exp9 data/labelled_forced_all.jsonl (40 plain per algorithm; extended-labeller labels mapped onto
  the suite labels: astar/gbfs -> astar_gbfs, dijkstra_unit -> dijkstra) = primary 'can'; exp7
  data/forced_labelled.jsonl (suite labels) = second, separately reported estimate.
- Bench refs: exp11 samples_pilot_raw.jsonl (raw text) with pilot labels; forced: samples_forced_raw.jsonl (raw text)
  joined with samples_forced.jsonl labels (FP8, plain templates 0-4 plus the descriptive variant -1).
"""

from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
from typing import Any

from config import BENCH_DIR, INPUTS, TASKS, read_jsonl

EXP9_MAP = {"t1": {"astar": "astar_gbfs", "gbfs": "astar_gbfs", "dijkstra_unit": "dijkstra"}, "t2": {}}
SUITE2TASK = {"t1": "T1", "t2": "T2"}


def _truthy(v) -> bool:
    return v is True or v == "True" or v == 1


@lru_cache(maxsize=1)
def refs_default() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in read_jsonl(INPUTS / "exp8" / "samples.jsonl"):
        if r.get("condition") != "b":
            continue
        t = SUITE2TASK[r["task"]]
        out[t].append({"task": t, "label": r["label"], "passed": _truthy(r["passed"]), "text": r.get("text"),
                       "code": r.get("code"), "source": "exp8 arm b"})
    pil = {r["sample_id"]: r for t in ("T03", "T04", "T06", "T10")
           for r in read_jsonl(BENCH_DIR / TASKS[t]["task_id"] / "pilot_rows.jsonl")}
    for r in read_jsonl(INPUTS / "exp11" / "samples_pilot_raw.jsonl"):
        if r["task"] not in TASKS or r["sample_id"] not in pil:
            continue
        lab = pil[r["sample_id"]]
        out[r["task"]].append({"task": r["task"], "label": lab["label"], "passed": bool(lab["passed"]),
                               "text": r.get("text"), "code": lab.get("code"), "source": "exp11 pilot"})
    return dict(out)


@lru_cache(maxsize=1)
def forced_all() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for r in read_jsonl(INPUTS / "exp9" / "labelled_forced_all.jsonl"):
        st = r["task"]
        mp = EXP9_MAP[st]
        req = mp.get(r["algorithm"], r["algorithm"])
        lab = mp.get(r["label"], r["label"])
        rows.append({"task": SUITE2TASK[st], "requested": req, "requested_fine": r["algorithm"], "label": lab,
                     "passed": _truthy(r["passed"]), "plain": r.get("variant") == "plain", "text": r.get("text"),
                     "code": r.get("code"), "source": "exp9", "template": r.get("paraphrase_id")})
    for r in read_jsonl(INPUTS / "exp7" / "forced_labelled.jsonl"):
        rows.append({"task": SUITE2TASK[r["task"]], "requested": r["j"], "requested_fine": r["j"], "label": r["label"],
                     "passed": _truthy(r["passed"]), "plain": r.get("family") == "plain", "text": r.get("text"),
                     "code": r.get("code"), "source": "exp7", "template": r.get("paraphrase_id")})
    lab = {r["sample_id"]: r for r in read_jsonl(INPUTS / "exp11" / "samples_forced.jsonl")}
    for r in read_jsonl(INPUTS / "exp11" / "samples_forced_raw.jsonl"):
        if r["task"] not in TASKS or r["sample_id"] not in lab:
            continue
        L = lab[r["sample_id"]]
        pid = L.get("paraphrase_id")
        rows.append({"task": r["task"], "requested": L["forced_mode"], "requested_fine": L["forced_mode"],
                     "label": L["label"], "passed": bool(L["passed"]), "plain": pid is not None and int(pid) >= 0,
                     "text": r.get("text"), "code": L.get("code"), "source": "exp11", "template": pid})
    return rows


def forced_as_requested(task: str, algo: str, primary_only: bool = False) -> list[dict[str, Any]]:
    """Forced programs that requested `algo` and are labelled `algo` (all variants; both path sources)."""
    out = []
    for r in forced_all():
        if r["task"] != task or r["requested"] != algo or r["label"] != algo:
            continue
        if primary_only and r["source"] == "exp7":
            continue
        out.append(r)
    return out


def wilson(k: int, n: int, z: float = 1.959964) -> list[float]:
    if n == 0:
        return [0.0, 1.0]
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return [max(0.0, c - h), min(1.0, c + h)]


@lru_cache(maxsize=1)
def can_table() -> dict[str, dict[str, Any]]:
    """can(A) per task and algorithm, plain forced templates only; primary source per family, exp7 second."""
    out: dict[str, dict[str, Any]] = {}
    for t in TASKS:
        out[t] = {}
        for a in TASKS[t]["catalogue"]:
            res = {}
            for src in (("exp9",) if TASKS[t]["family"] == "path" else ("exp11",)) + (("exp7",) if TASKS[t]["family"]
                                                                                      == "path" else ()):
                rows = [r for r in forced_all() if r["task"] == t and r["requested"] == a and r["plain"]
                        and r["source"] == src]
                n = len(rows)
                k_lab = sum(r["label"] == a for r in rows)
                k_can = sum(r["label"] == a and r["passed"] for r in rows)
                desc = [r for r in forced_all() if r["task"] == t and r["requested"] == a and not r["plain"]
                        and r["source"] == src]
                res[src] = {"n_plain": n, "labelled_as_requested": k_lab, "can_k": k_can,
                            "can": (k_can / n) if n else None, "can_ci": wilson(k_can, n),
                            "labelled_share": (k_lab / n) if n else None,
                            "pass_given_labelled": (k_can / k_lab) if k_lab else None,
                            "n_desc": len(desc), "desc_can": (sum(r["label"] == a and r["passed"] for r in desc)
                                                              / len(desc)) if desc else None}
            prim = res.get("exp9") or res.get("exp11")
            if TASKS[t]["family"] == "path" and (prim is None or prim["n_plain"] == 0) and res.get("exp7", {}).get(
                    "n_plain"):
                prim = dict(res["exp7"], note="no plain exp9 attempts; exp7 plain used as primary")
            out[t][a] = {"primary": prim, "by_source": res}
    return out


def can(task: str, algo: str) -> float | None:
    p = can_table()[task][algo]["primary"]
    return p["can"] if p else None
