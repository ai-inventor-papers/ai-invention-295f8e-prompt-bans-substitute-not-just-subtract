#!/usr/bin/env python3
"""S0.3 labeller re-check: every bench labeller (13 tasks incl. R2) on its references (must be 100%) and on its gold
set (must reproduce gate.json runtime-vs-adjudicated agreement exactly); the exp8 suite labeller on its 22
references and gold set. Mechanical labels only (no judge spend). -> results/labeller_recheck.json"""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

import cfg4  # noqa: E402,F401
import s0_checks as S  # noqa: E402
from cfg4 import BENCH, BENCH13, RESULTS_DIR, read_json, read_jsonl, setup_logging, write_json  # noqa: E402


def bench_recheck() -> dict[str, Any]:
    from bench.common.catalogue import TASKS
    from bench.common.labeling import label_one
    from bench.common.testgen import read_tests

    res: dict[str, Any] = {}
    for t in BENCH13:
        d = BENCH / TASKS[t]["task_id"]
        cases = read_tests(d / "tests.jsonl")
        refs = sorted((d / "references").glob("*.py"))

        def lab(code: str, sid: str) -> dict[str, Any]:
            return label_one({"sample_id": sid, "task": t, "condition": "recheck", "mode": None, "paraphrase_id": None,
                              "round": None, "attempt_idx": None, "seed": 0, "finish_reason": "stop",
                              "text": "```python\n" + code + "\n```"}, cases)
        with ThreadPoolExecutor(4) as ex:
            rl = list(ex.map(lambda p: (p.stem, lab(p.read_text(), p.stem)), refs))
        ref_ok = sum(1 for m, l in rl if l.get("runtime_label") == m and l.get("passed"))
        gold = read_jsonl(d / "gold_set.jsonl")
        with ThreadPoolExecutor(4) as ex:
            gl = list(ex.map(lambda g: lab(g["code"], g["gold_id"]), gold))
        agree = [l.get("runtime_label") == g["adjudicated"] for g, l in zip(gold, gl)]
        gate = read_json(d / "gate.json")
        exp = gate["gold"]["runtime_vs_adjudicated"]
        acc = sum(agree) / max(len(agree), 1)
        res[t] = {"references_ok": ref_ok, "n_references": len(refs), "gold_n": len(gold),
                  "gold_runtime_vs_adjudicated": acc, "gate_runtime_vs_adjudicated": exp,
                  "reproduces_gate_exactly": abs(acc - exp) < 1e-9, "references_pass": ref_ok == len(refs)}
        logger.info(f"recheck {t}: refs {ref_ok}/{len(refs)}, gold runtime acc {acc:.3f} (gate {exp:.3f})")
    return res


def main() -> None:
    setup_logging("recheck4")
    out = {"bench": bench_recheck(), "exp8_suite": S.suite_recheck(),
           "note": "mechanical labels only (runtime/AST); the judge is not re-run (spend)"}
    out["all_references_pass"] = all(v["references_pass"] for v in out["bench"].values()) and \
        out["exp8_suite"]["references_ok"] == out["exp8_suite"]["n_references"]
    out["all_gates_reproduced"] = all(v["reproduces_gate_exactly"] for v in out["bench"].values())
    write_json(RESULTS_DIR / "labeller_recheck.json", out)
    logger.info(f"recheck: refs pass {out['all_references_pass']}, gates {out['all_gates_reproduced']}")


if __name__ == "__main__":
    main()
