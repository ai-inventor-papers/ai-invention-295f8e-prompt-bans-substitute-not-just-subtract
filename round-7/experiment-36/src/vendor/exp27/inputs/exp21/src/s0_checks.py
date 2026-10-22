#!/usr/bin/env python3
"""S0 checks: (T0) input hashes against exp11 bench/commitment.json and sha256 of every copied input; (T1) labeller
re-check -- bench references (100% expected) and gold-set runtime/AST agreement vs gate.json; exp8 suite references
(22/22) and gold-set mechanical agreement vs gate_report.json. Mechanical labels only (no judge spend)."""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from loguru import logger

from cfg import BENCH, E11, INPUTS, RESULTS_DIR, SUITE, read_json, read_jsonl, rel, sha256_file, write_json

for p in (str(SUITE), str(E11)):
    if p not in sys.path:
        sys.path.insert(0, p)


def input_hashes() -> dict[str, Any]:
    com = read_json(BENCH / "commitment.json")
    from label_worker import _bench_cases  # noqa: F401  (bench import path)
    from bench.common.catalogue import TASKS

    out: dict[str, Any] = {"bench": {}, "mismatches": []}
    for t, v in com["tasks"].items():
        d = BENCH / TASKS[t]["task_id"]
        ok = 0
        for f, h in v["files"].items():
            if f == "catalogue":
                continue
            p = d / f
            got = sha256_file(p) if p.exists() else None
            if got != h:
                out["mismatches"].append({"task": t, "file": f, "expected": h, "got": got})
            else:
                ok += 1
        out["bench"][t] = {"files_checked": ok}
    out["all_inputs_sha256"] = {rel(p): sha256_file(p) for p in sorted(INPUTS.rglob("*")) if p.is_file()
                                and "__pycache__" not in str(p) and p.stat().st_size < 50_000_000}
    out["pass"] = not out["mismatches"]
    return out


def bench_recheck() -> dict[str, Any]:
    from bench.common.catalogue import TASKS
    from bench.common.labeling import label_one
    from bench.common.testgen import read_tests

    res: dict[str, Any] = {}
    for t in ("T03", "T04", "T06", "T05", "T10", "R1", "T08", "R3", "T13", "R6", "T14", "T11"):
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
                  "within_0.02": abs(acc - exp) <= 0.02 + 1e-9,
                  "references_pass": ref_ok == len(refs)}
        logger.info(f"recheck {t}: refs {ref_ok}/{len(refs)}, gold runtime acc {acc:.3f} (gate {exp:.3f})")
    return res


def suite_recheck() -> dict[str, Any]:
    from labeller import ast_rules, runtime_rules
    from tasks.harness import evaluate_program

    gr = read_json(SUITE / "labeller" / "gate_report.json")
    refs = []
    for tdir, t in (("t1_grid", "t1"), ("t2_wsp", "t2")):
        for p in sorted((SUITE / "tasks" / tdir / "references").glob("*.py")):
            refs.append((t, p))
    ref_modes = {k: v["mode"] for k, v in (gr["references"].items() if isinstance(gr["references"], dict) else [])}

    def one(tp):
        t, p = tp
        code = p.read_text()
        ev = evaluate_program(t, code)
        rl = runtime_rules.label(t, ev["probes"])[0]
        al = ast_rules.label(code, t)[0]
        return {"file": f"{t}/{p.name}", "runtime": rl, "ast": al, "passed": bool(ev["tests"].get("passed")),
                "mode": ref_modes.get(f"{t}/{p.name}")}
    with ThreadPoolExecutor(4) as ex:
        rr = list(ex.map(one, refs))
    ok = sum(1 for r in rr if r["mode"] is not None and r["runtime"] == r["mode"] and r["ast"] == r["mode"])
    gold = [g for g in read_jsonl(SUITE / "labeller" / "gold_set.jsonl") if g.get("split") == "eval"]
    adj_key = next((k for k in ("adjudicated", "gold_label", "label") if gold and k in gold[0]), None)

    def gone(g):
        ev = evaluate_program(g["task"], g["code"])
        return runtime_rules.label(g["task"], ev["probes"])[0], ast_rules.label(g["code"], g["task"])[0]
    with ThreadPoolExecutor(4) as ex:
        gl = list(ex.map(gone, gold))
    out = {"references_ok": ok, "n_references": len(rr), "references": rr}
    if adj_key:
        acc_rt = sum(1 for g, (r, a) in zip(gold, gl) if r == g[adj_key]) / max(len(gold), 1)
        acc_ast = sum(1 for g, (r, a) in zip(gold, gl) if a == g[adj_key]) / max(len(gold), 1)
        em = gr["eval_metrics"]
        out.update({"gold_eval_n": len(gold), "acc_runtime_vs_adjudicated": acc_rt, "acc_ast_vs_adjudicated": acc_ast,
                    "gate_acc_runtime": em["acc_runtime_vs_adjudicated"], "gate_acc_ast": em["acc_ast_vs_adjudicated"],
                    "gate_acc_combined_with_judge": em["acc_combined_vs_adjudicated"],
                    "runtime_within_0.02": abs(acc_rt - em["acc_runtime_vs_adjudicated"]) <= 0.02 + 1e-9})
    else:
        out["gold_note"] = "gold_set.jsonl has no adjudicated-label field; agreement not recomputed"
    logger.info(f"suite recheck: refs {ok}/{len(rr)}; {({k: v for k, v in out.items() if k.startswith('acc')})}")
    return out


def run_s0() -> None:
    ih = input_hashes()
    write_json(RESULTS_DIR / "input_hashes.json", ih)
    logger.info(f"input hashes: pass={ih['pass']} mismatches={len(ih['mismatches'])}")
    lr = {"bench": bench_recheck(), "exp8_suite": suite_recheck(),
          "note": "mechanical labels only (runtime/AST); the judge is not re-run (spend)"}
    write_json(RESULTS_DIR / "labeller_recheck.json", lr)


if __name__ == "__main__":
    from cfg import setup_logging

    setup_logging("s0_checks")
    run_s0()
