#!/usr/bin/env python3
"""Label worker (CPU; runs in its own process because the vendored labellers use clashing module names).

Frozen labellers, reused unchanged:
  B3, B6  iteration-5 exp26 unitlib.label_code (hidden tests + runtime tracer + AST; agree -> label, one side missing ->
          the other, disagreement -> 'disputed' unless a blind judge resolves it later)
  A3      iteration-5 exp25 newbench common.label5.mech_labels (same combine rule: agree, or AST 'unknown' -> runtime;
          real disagreement or runtime 'unknown' -> 'disputed' unless judged)
  T1, T2, T03, T10   iteration-6 label_worker_v4.label_rows (exp8 suite / exp11 bench labellers) + exp28's T2
          array-Dijkstra re-gate; no judge calls.
Usage: label7.py <in.jsonl> <out.jsonl>   rows: {"sid", "unit", "text"} -> one label row per input row.
"""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
E26 = ROOT / "inputs" / "iter5_exp26"
E25 = ROOT / "inputs" / "iter5_exp25"
I6 = ROOT / "inputs" / "iter6_exp30" / "src"
N_WORKERS = 10

_B: dict[str, Any] = {}


def _unitlib():
    if "u" not in _B:
        sys.path.insert(0, str(E26 / "src"))
        import unitlib  # noqa: E402
        _B["u"] = unitlib
        _B["tests"] = {}
    return _B["u"]


def label_b(unit: str, text: str) -> dict[str, Any]:
    U = _unitlib()
    code = U.extract_code(text)
    if unit not in _B["tests"]:
        _B["tests"][unit] = U.load_tests(unit)
    L = U.label_code(unit, code, cases=_B["tests"][unit])
    lab = L.get("label_pre")
    src = L.get("labeller_source")
    if lab is None:
        lab = "disputed"
    return {"label": lab, "labeller_source": src, "passed": bool(L.get("passed")) and bool(L.get("valid")),
            "valid": bool(L.get("valid")), "runtime_label": L.get("runtime_label"), "ast_label": L.get("ast_label"),
            "n_pass": L.get("n_pass"), "n_cases": L.get("n_cases"), "code": code}


def _newbench():
    if "nb" not in _B:
        sys.path.insert(0, str(E25))
        from newbench.common import harness5, label5  # noqa: E402
        _B["nb"] = (harness5, label5)
    return _B["nb"]


def label_a(unit: str, text: str) -> dict[str, Any]:
    H5, L5 = _newbench()
    code = H5.extract_code(text)
    m = L5.mech_labels(unit, code) if code else {"valid": False, "passed": False, "ast_label": "invalid",
                                                  "runtime_label": "invalid"}
    if not m["valid"]:
        lab, src = "invalid", "extraction"
    elif L5.needs_judge(m["runtime_label"], m["ast_label"]):
        lab, src = "disputed", "disagree"
    else:
        lab = m["runtime_label"]
        src = "agree" if m["ast_label"] == m["runtime_label"] else "runtime(ast_unknown)"
    return {"label": lab, "labeller_source": src, "passed": bool(m.get("passed")) and bool(m["valid"]),
            "valid": bool(m["valid"]), "runtime_label": m.get("runtime_label"), "ast_label": m.get("ast_label"),
            "n_pass": m.get("n_pass"), "n_cases": m.get("n_cases"), "code": code}


def _lw():
    if "lw" not in _B:
        sys.path.insert(0, str(I6))
        import label_worker_v4 as LW  # noqa: E402
        from regate_rules import apply_t2  # noqa: E402
        LW.N_WORKERS = 5
        _B["lw"] = (LW, apply_t2)
    return _B["lw"]


def label_collapsed(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    LW, apply_t2 = _lw()
    inp = [{"task": r["unit"], "text": r["text"], "sample_id": r["sid"]} for r in rows]
    for k in LW.KEEP:
        for x in inp:
            x.setdefault(k, None)
    res = LW.label_rows(inp, use_judge=False)
    by_sid = {o["sample_id"]: o for o in res}   # label_rows regroups path rows before bench rows
    out = []
    for r in rows:
        o = by_sid[r["sid"]]
        lab = o.get("label")
        if r["unit"] == "T2":
            lab2, changed = apply_t2(lab, o.get("code"))
            if changed:
                lab = lab2
        out.append({"label": lab, "labeller_source": o.get("labeller_source"), "passed": bool(o.get("passed")),
                    "valid": bool(o.get("valid")), "runtime_label": o.get("runtime_label"),
                    "ast_label": o.get("ast_label"), "code": o.get("code")})
    return out


def label_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any] | None] = [None] * len(rows)
    coll = [i for i, r in enumerate(rows) if r["unit"] in ("T1", "T2", "T03", "T10")]
    other = [i for i, r in enumerate(rows) if r["unit"] not in ("T1", "T2", "T03", "T10")]

    def one(i: int) -> dict[str, Any]:
        r = rows[i]
        try:
            return label_a(r["unit"], r["text"]) if r["unit"] == "A3" else label_b(r["unit"], r["text"])
        except Exception as e:  # noqa: BLE001 - a crashing labeller is recorded, never silently dropped
            return {"label": "label_error", "labeller_source": f"error:{type(e).__name__}:{str(e)[:120]}",
                    "passed": False, "valid": False, "runtime_label": None, "ast_label": None, "code": None}
    if other:
        _unitlib() if any(rows[i]["unit"] != "A3" for i in other) else None
        _newbench() if any(rows[i]["unit"] == "A3" for i in other) else None
        with ThreadPoolExecutor(N_WORKERS) as ex:
            for i, res in zip(other, ex.map(one, other)):
                out[i] = res
    if coll:
        for i0 in range(0, len(coll), 40):
            part = coll[i0:i0 + 40]
            for i, res in zip(part, label_collapsed([rows[i] for i in part])):
                out[i] = res
    return [{"sid": rows[i]["sid"], "unit": rows[i]["unit"], **out[i]} for i in range(len(rows))]


def main() -> None:
    inp, outp = Path(sys.argv[1]), Path(sys.argv[2])
    rows = [json.loads(l) for l in inp.read_text().splitlines() if l.strip()]
    t0 = time.time()
    res = label_rows(rows)
    with open(outp, "w") as fh:
        for r in res:
            fh.write(json.dumps(r) + "\n")
    print(f"labelled {len(res)} rows in {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
