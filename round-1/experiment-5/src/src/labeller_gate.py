"""Labeller QA gate (STEP 3.6 a-b): both labellers on every catalogue reference, variant and mutant.

Gate: AST labeller 100% correct; runtime labeller never WRONG (it may say 'unknown' only for array-scan Dijkstra
and Dial, which have no distinctive runtime data-structure trace, as anticipated in the plan).
  .venv/bin/python src/labeller_gate.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from calibrate import REF_LABEL  # noqa: E402
from common import REFS, RESULTS, WS, setup_logging  # noqa: E402
from harness import score_many  # noqa: E402
from labeller_ast import label_ast  # noqa: E402
from labeller_runtime import label_many  # noqa: E402

RUNTIME_UNKNOWN_OK = {"t2/dijkstra_array", "t2/dial", "t2/mut:min_key"}


def programs() -> list[tuple[str, str, str, str]]:
    out = []
    for task in ("t1", "t2"):
        for name, lab in REF_LABEL[task].items():
            out.append((task, f"{task}/{name}", lab, (REFS / task / f"{name}.py").read_text()))
    for p in sorted((REFS / "mutants").glob("*.py")):
        task, lab, name = p.stem.split("__")
        out.append((task, f"{task}/mut:{name}", lab, p.read_text()))
    return out


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("labeller_gate")
    progs = programs()
    rt = label_many([(t, code, str(WS / "scratch_label"), key) for t, key, _, code in progs], n_workers=4)
    sc = score_many([(t, code, str(WS / "data" / "tests" / f"{t}.json"), str(WS / "scratch_harness"), key)
                     for t, key, _, code in progs], n_workers=4)
    rows = []
    ast_ok_all, rt_ok_all = True, True
    for (task, key, lab, code), r, s in zip(progs, rt, sc):
        al, feats = label_ast(code, task)
        ast_ok = al == lab
        rt_ok = r["label"] == lab or (r["label"] == "unknown" and key in RUNTIME_UNKNOWN_OK)
        ast_ok_all &= ast_ok
        rt_ok_all &= rt_ok
        rows.append({"program": key, "expected": lab, "ast": al, "runtime": r["label"], "runtime_why": r.get("why"),
                     "ast_ok": ast_ok, "runtime_ok": rt_ok, "passes_tests": s["passed"]})
        logger.info(f"{'OK ' if ast_ok and rt_ok else 'BAD'} {key:40s} exp={lab:18s} ast={al:18s} rt={r['label']:18s} "
                    f"pass={s['passed']} | {r.get('why')}" + ("" if ast_ok else f" | ast feats {feats}"))
    res = {"rows": rows, "ast_accuracy": sum(r["ast_ok"] for r in rows) / len(rows),
           "runtime_no_wrong_rate": sum(r["runtime_ok"] for r in rows) / len(rows),
           "runtime_exact_accuracy": sum(r["runtime"] == r["expected"] for r in rows) / len(rows),
           "gate_ok": ast_ok_all and rt_ok_all, "n_programs": len(rows),
           "all_programs_pass_tests": all(r["passes_tests"] for r in rows)}
    (RESULTS / "labeller_gate.json").write_text(json.dumps(res, indent=1))
    logger.info(f"GATE ok={res['gate_ok']} ast_acc={res['ast_accuracy']:.3f} rt_no_wrong={res['runtime_no_wrong_rate']:.3f} "
                f"rt_exact={res['runtime_exact_accuracy']:.3f} all_pass_tests={res['all_programs_pass_tests']}")


if __name__ == "__main__":
    main()
