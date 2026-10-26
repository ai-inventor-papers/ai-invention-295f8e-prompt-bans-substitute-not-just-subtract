#!/usr/bin/env python3
"""STEP A4: the adjudicated column for every program in the exp33 cells whose OLD 'other' share exceeds 20% (all three
tasks): rule label (T03: the validated v2 labeller; T2: exp33's frozen path labeller, unchanged), judge A, judge B
(two families, gated on 10 known-class controls, 9/10 to count), and the executor's manual read of every program where
the counted readers disagree plus a fixed-seed 10-program sample where they agree."""

from __future__ import annotations

import asyncio
import random
from collections import Counter, defaultdict
from typing import Any

from loguru import logger

from sections.common import (AUDIT, BENCH_ROOT, RESULTS, TABLES, cohen_kappa, dep, read_json, read_jsonl, sha256_text,
                             src_ref, write_csv, write_json)
from sections.judges import JUDGES, JudgeClient
from labeller_v2.controls import POSITIVE

T03_DIR = BENCH_ROOT / "bench" / "T03_kth_smallest"
GATE_MIN = 9


def gate_controls() -> list[dict[str, Any]]:
    ctr = []
    for p in sorted((T03_DIR / "references").glob("*.py")):
        ctr.append({"id": f"ref:{p.stem}", "task": "T03", "known": p.stem, "code": p.read_text(), "origin": "bench reference"})
    gold = sorted((g for g in read_jsonl(T03_DIR / "gold_set.jsonl") if g["source"] != "reference"),
                  key=lambda g: g["gold_id"])
    for want in ("quickselect", "size_k_heap"):
        g = next(x for x in gold if x["adjudicated"] == want)
        ctr.append({"id": f"gold:{g['gold_id']}", "task": "T03", "known": want, "code": g["code"], "origin": "gold set"})
    for name, (want, code) in POSITIVE.items():
        ctr.append({"id": f"constructed:{name}", "task": "T03", "known": want, "code": code,
                    "origin": "executor-constructed (dictionary form)"})
    return ctr


def programs(cells: list[dict[str, Any]], relabel_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keep = {(c["task"], c["arm"]) for c in cells}
    v2 = {r["sample_id"]: r for r in relabel_rows}
    out = []
    for r in read_jsonl(dep("exp33", "data/labels.jsonl")):
        if (r["task"], r["arm"]) not in keep:
            continue
        rule = v2[r["sample_id"]]["rule_v2"] if r["task"] == "T03" else r["label"]
        out.append({"sample_id": r["sample_id"], "task": r["task"], "cell": r["arm"], "slot_index": r["slot_index"],
                    "passed": bool(r.get("passed")), "valid": bool(r.get("valid")), "old_label": r["label"],
                    "rule_label": rule, "code": r.get("code") or "", "code_sha256": sha256_text(r.get("code") or ""),
                    "finish_reason": r.get("finish_reason")})
    return out


async def _run_judges(ctr: list[dict[str, Any]], progs: list[dict[str, Any]]) -> dict[str, Any]:
    jc = JudgeClient()
    items = [(m, c["task"], c["code"], c["id"]) for m in JUDGES.values() for c in ctr]
    gres = await jc.batch(items)
    gate = {}
    for jn, m in JUDGES.items():
        rs = [r for (mm, _, _, _), r in zip(items, gres) if mm == m]
        right = [r.get("label") == c["known"] for r, c in zip(rs, ctr)]
        gate[jn] = {"model": m, "score": int(sum(right)), "n": len(ctr), "passes": sum(right) >= GATE_MIN,
                    "per_control": [{"id": c["id"], "known": c["known"], "label": r.get("label")} for r, c in zip(rs, ctr)]}
    logger.info(f"judge gate: " + ", ".join(f"{k} {v['model']} {v['score']}/{v['n']}" for k, v in gate.items()))
    # distinct programs only: identical code gets the identical label
    distinct = {}
    for p in progs:
        if p["valid"] and p["code"]:
            distinct.setdefault((p["task"], p["code_sha256"]), p)
    order = list(distinct.values())
    random.Random(20261023).shuffle(order)  # blind order: no cell or arm in the prompt, shuffled across cells
    items2 = [(m, p["task"], p["code"], f"prog:{p['code_sha256'][:12]}") for m in JUDGES.values() for p in order]
    pres = await jc.batch(items2)
    lab = defaultdict(dict)
    for (m, t, _, _), p, r in zip(items2, order * len(JUDGES), pres):
        jn = [k for k, v in JUDGES.items() if v == m][0]
        lab[(t, p["code_sha256"])][jn] = r.get("label")
    return {"gate": gate, "labels": lab, "spent_usd_this_run": jc.spent, "n_calls_this_run": jc.n_calls,
            "cached_cost_usd": jc.cached_cost, "refused": jc.refused,
            "key_before": getattr(jc, "key_before", None), "key_after": getattr(jc, "key_after", None),
            "n_distinct": len(order)}


def run(cells: list[dict[str, Any]], relabel_rows: list[dict[str, Any]], manual: dict[str, dict[str, str]]
        ) -> dict[str, Any]:
    ctr = gate_controls()
    progs = programs(cells, relabel_rows)
    jr = asyncio.run(_run_judges(ctr, progs))
    counted = [k for k, v in jr["gate"].items() if v["passes"]]
    rows = []
    for p in progs:
        jl = jr["labels"].get((p["task"], p["code_sha256"]), {})
        a, b = jl.get("A"), jl.get("B")
        readers = [p["rule_label"]] + [jl.get(k) for k in counted]
        agree = p["valid"] and len(set(readers)) == 1 and None not in readers
        rows.append({**{k: p[k] for k in ("sample_id", "task", "cell", "slot_index", "passed", "valid", "old_label",
                                          "rule_label", "code_sha256", "finish_reason")},
                     "judge_A": a, "judge_B": b, "counted_judges": "+".join(counted) or "none", "readers_agree": agree})
    # manual reads: every disagreement among counted readers (or every program when no judge counts) + agreement sample
    agree_rows = [r for r in rows if r["readers_agree"]]
    sample = set(r["sample_id"] for r in random.Random(7).sample(agree_rows, min(10, len(agree_rows))))
    need_manual = [r for r in rows if r["valid"] and (not r["readers_agree"] or not counted)]
    for r in rows:
        m = manual.get(r["code_sha256"])
        r["in_agreement_sample"] = r["sample_id"] in sample
        r["manual_read"] = m["label"] if m else None
        r["manual_note"] = m["note"] if m else None
        if not r["valid"]:
            r["final_label"], r["final_source"] = "invalid", "extraction"
        elif r["readers_agree"] and counted:
            r["final_label"], r["final_source"] = r["rule_label"], "rule+" + "+".join(counted)
        elif m:
            r["final_label"], r["final_source"] = m["label"], "manual read"
        else:
            r["final_label"], r["final_source"] = None, "MISSING manual read"
        r["manual_overrides_rule"] = bool(m and r["valid"] and m["label"] != r["rule_label"])
    missing = sorted({r["code_sha256"] for r in rows if r["final_source"] == "MISSING manual read"})
    miss_sample = sorted({r["code_sha256"] for r in rows if r["in_agreement_sample"] and not r["manual_read"]})
    v = [r for r in rows if r["valid"] and r["judge_A"] and r["judge_B"]]
    kap = {"rule_vs_A": cohen_kappa([r["rule_label"] for r in v], [r["judge_A"] for r in v]),
           "rule_vs_B": cohen_kappa([r["rule_label"] for r in v], [r["judge_B"] for r in v]),
           "A_vs_B": cohen_kappa([r["judge_A"] for r in v], [r["judge_B"] for r in v]), "n": len(v)}
    vm = [r for r in rows if r["valid"] and r["manual_read"]]
    rule_vs_manual = sum(r["rule_label"] == r["manual_read"] for r in vm) / max(len(vm), 1)
    final_counts = defaultdict(Counter)
    for r in rows:
        final_counts[r["cell"]][r["final_label"]] += 1
    res = {"gate": jr["gate"], "counted_judges": counted, "kappa": kap, "n_programs": len(rows),
           "n_distinct_judged": jr["n_distinct"], "n_need_manual": len(need_manual),
           "n_manual_reads": len({r["code_sha256"] for r in vm}), "manual_overrides": sum(r["manual_overrides_rule"] for r in rows),
           "rule_vs_manual_agreement": rule_vs_manual, "n_rule_vs_manual": len(vm),
           "missing_manual_codes": missing, "missing_sample_codes": miss_sample,
           "final_counts": {c: dict(v) for c, v in final_counts.items()},
           "spend": {"this_run_usd": jr["spent_usd_this_run"], "cached_usd": jr["cached_cost_usd"],
                     "n_calls_this_run": jr["n_calls_this_run"], "refused": jr["refused"]},
           "key_before": jr["key_before"], "key_after": jr["key_after"],
           "source": src_ref("exp33", "data/labels.jsonl", "cells with old other share > 0.2")}
    write_json(AUDIT / "judge_gate.json", {"controls": [{k: c[k] for k in ("id", "known", "origin")} for c in ctr],
                                           "gate": jr["gate"], "judges": JUDGES, "rule": f">= {GATE_MIN}/10 to count"})
    write_csv(TABLES / "counting_sort_adjudication.csv", rows,
              ["sample_id", "task", "cell", "slot_index", "passed", "valid", "old_label", "rule_label", "judge_A",
               "judge_B", "counted_judges", "readers_agree", "in_agreement_sample", "manual_read", "manual_note",
               "final_label", "final_source", "manual_overrides_rule", "code_sha256"])
    write_json(RESULTS / "a4_adjudication.json", {**res, "rows": rows})
    logger.info(f"A4: {len(rows)} programs, counted judges {counted}, kappa {kap}, need manual {len(need_manual)}, "
                f"missing manual {len(missing)}, spend ${jr['spent_usd_this_run']:.4f} (+cached ${jr['cached_cost_usd']:.4f})")
    return {**res, "rows": rows}
