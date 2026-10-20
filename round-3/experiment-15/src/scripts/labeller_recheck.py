#!/usr/bin/env python3
"""A3 / T0 labeller re-check with the copied (read-only) bench labellers: every reference must get its own label from
both the runtime and the AST labeller, and the runtime label must agree with the adjudicated gold label (exp11's gate
values were >= 0.91).  The exp10 canon re-check is quoted from exp10 (22/22, 0.966) because the canon gold set and
labeller are unchanged (SHA256SUMS verified in results/input_integrity.json)."""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.ws import BENCH, EXP10, FROZEN_TASKS, RESULTS, read_jsonl, write_json  # noqa: E402

from bench.common.astrules import ast_label  # noqa: E402
from bench.common.catalogue import TASKS  # noqa: E402
from bench.common.probes import run_trace  # noqa: E402
from bench.common.rtrules import runtime_label  # noqa: E402


def one(task: str, code: str) -> tuple[str, str]:
    return runtime_label(task, run_trace(code, task)), ast_label(task, code)


def main() -> None:
    out = {"tasks": {}}
    jobs = []
    for t in FROZEN_TASKS:
        tdir = BENCH / TASKS[t]["task_id"]
        for f in sorted((tdir / "references").glob("*.py")):
            jobs.append(("ref", t, f.stem, f.read_text()))
        for g in read_jsonl(tdir / "gold_set.jsonl"):
            jobs.append(("gold", t, g["adjudicated"], g["code"]))
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(lambda j: one(j[1], j[3]), jobs))
    for (kind, t, want, _), (rt, ast) in zip(jobs, res):
        e = out["tasks"].setdefault(t, {"ref_n": 0, "ref_ok": 0, "gold_n": 0, "gold_runtime_agree": 0, "ref_fail": []})
        if kind == "ref":
            e["ref_n"] += 1
            ok = rt == want and ast == want
            e["ref_ok"] += int(ok)
            if not ok:
                e["ref_fail"].append({"mode": want, "runtime": rt, "ast": ast})
        else:
            e["gold_n"] += 1
            e["gold_runtime_agree"] += int(rt == want)
    for t, e in out["tasks"].items():
        e["gold_agreement"] = e["gold_runtime_agree"] / max(e["gold_n"], 1)
        e["flag_below_0.90"] = e["gold_agreement"] < 0.90
    out["references_ok"] = sum(e["ref_ok"] for e in out["tasks"].values())
    out["references_n"] = sum(e["ref_n"] for e in out["tasks"].values())
    out["gold_agreement_overall"] = (sum(e["gold_runtime_agree"] for e in out["tasks"].values())
                                     / max(sum(e["gold_n"] for e in out["tasks"].values()), 1))
    out["flagged_tasks"] = sorted(t for t, e in out["tasks"].items() if e["flag_below_0.90"])
    ex10 = json.loads((EXP10 / "results" / "labeller_recheck.json").read_text())
    out["canon_exp10_quoted"] = {k: ex10.get(k) for k in ("references_ok", "references_n", "references_100pct")}
    out["passed"] = out["references_ok"] == out["references_n"] and not out["flagged_tasks"]
    write_json(RESULTS / "labeller_recheck.json", out)
    print({k: v for k, v in out.items() if k != "tasks"})


if __name__ == "__main__":
    main()
