#!/usr/bin/env python3
"""Iteration-8 Step 0: erratum and re-derivation pass over the iteration-7 record (review items 0a-0k).

Usage:  uv run eval.py --stages all            (= s0,a,b,c,d,e,f,g,h,i,j,k,apply,audit,out)
        uv run eval.py --stages s0,a,apply     (any subset; later stages read earlier results from results/)

CPU only. Judge calls (stage a) are cached in audit/judge_cache.jsonl, so a rerun spends nothing; live web evidence for
stage f is read from audit/web/ (refresh with audit/web/run_fetches.sh)."""

from __future__ import annotations

import argparse
import json
import resource
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from loguru import logger

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
(ROOT / "logs").mkdir(exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(ROOT / "logs" / "run.log", rotation="30 MB", level="DEBUG")

from sections import common as C  # noqa: E402
from sections.common import RESULTS, ROOT as _R, read_json, write_json  # noqa: E402

ALL = ["s0", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "apply", "audit", "out"]
ITEM_STAGES = {"a": "0a", "b": "0b", "c": "0c", "d": "0d", "e": "0e", "f": "0f", "g": "0g", "h": "0h", "i": "0i",
               "j": "0j", "k": "0k"}


def _limit_memory(gb: float = 16.0) -> None:
    b = int(gb * 1024 ** 3)
    resource.setrlimit(resource.RLIMIT_AS, (b * 3, b * 3))


def stage_a() -> dict[str, Any]:
    from sections import a_adjudicate as AD, a_labeller as AL, a_recompute as RC, manual_reads as MR
    base = AL.run()
    if not base["validation"]["relabel_allowed"]:
        raise RuntimeError("A2 validation failed: the relabel is blocked")
    rel = base["relabel"]["rows"]
    hashes = sorted({r["code_sha256"] for r in AD.programs(base["cells"], rel)})
    adj = AD.run(base["cells"], rel, MR.resolve(hashes))
    if adj["missing_manual_codes"] or adj["missing_sample_codes"]:
        raise RuntimeError(f"manual reads missing for {len(adj['missing_manual_codes'])} + {len(adj['missing_sample_codes'])} programs")
    fmap = {r["sample_id"]: r["rule_v2"] for r in rel}
    for r in adj["rows"]:
        if r["task"] == "T03":
            fmap[r["sample_id"]] = r["final_label"]
    write_json(RESULTS / "final_labels_T03.json", fmap)
    rc = RC.run(fmap)
    for t, v in rc["placebo"].items():
        if not v["all_match"]:
            raise RuntimeError(f"A5 placebo failed on {t}: the port does not reproduce exp33's pooled recovery")
    write_json(RESULTS / "a5_recompute.json", rc)
    return {"a2": base["validation"], "a3": base["relabel"], "a4": adj, "a5": rc}


def load_ctx() -> dict[str, Any]:
    return {"a2": read_json(RESULTS / "a2_validation.json"), "a3": read_json(RESULTS / "a3_relabel.json"),
            "a4": read_json(RESULTS / "a4_adjudication.json"), "a5": _int_keys(read_json(RESULTS / "a5_recompute.json"))}


def _int_keys(o: Any) -> Any:
    """JSON turns the per_k / das rank keys into strings; restore ints where a key is a rank."""
    if isinstance(o, dict):
        return {(int(k) if isinstance(k, str) and k.isdigit() else k): _int_keys(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_int_keys(x) for x in o]
    return o


def run_items(stages: list[str], ctx: dict[str, Any]) -> dict[str, Any]:
    from sections import item_a, item_b, item_cde, item_f, item_ghijk
    fn = {"a": item_a.run, "b": item_b.run, "c": item_cde.item_c, "d": item_cde.item_d, "e": item_cde.item_e,
          "f": item_f.run, "g": item_ghijk.item_g, "h": item_ghijk.item_h, "i": item_ghijk.item_i,
          "j": item_ghijk.item_j, "k": item_ghijk.item_k}
    out = {}
    for s in stages:
        if s in fn:
            t0 = time.time()
            n0 = len(C.VALUES)
            r = fn[s](ctx)
            r["values"] = C.VALUES[n0:]
            out[ITEM_STAGES[s]] = r
            write_json(RESULTS / f"item_{ITEM_STAGES[s]}.json", r)
            logger.info(f"item {ITEM_STAGES[s]}: {len(r['edits'])} edits, {len(r['values'])} values ({time.time() - t0:.1f}s)")
    return out


def write_corrections(items: dict[str, Any], s0: dict[str, Any], ap: dict[str, Any]) -> dict[str, Any]:
    edits = [e for it in items.values() for e in it["edits"]]
    vals = [v for it in items.values() for v in it["values"]]
    by_status = {s: sum(v["status"] == s for v in vals) for s in ("MATCH", "CORRECTED", "NEW", "CARRIED")}
    corr = {"read_date": C.READ_DATE, "report_sha256": s0["hashes"]["report"]["sha256"] if s0 else None,
            "schema": "mirrors art_LzP2qPwUrANz corrections.json: one record per edit (old_text occurs once in the vendored report) plus a value ledger",
            "n_edits": len(edits), "n_values": len(vals), "values_by_status": by_status,
            "n_edits_by_item": {k: len(v["edits"]) for k, v in items.items()},
            "apply": {k: ap.get(k) for k in ("apply_test_pass", "n_edits", "lint_before", "lint_after", "placebo_mutation_fails", "problems")},
            "corrections": edits, "values": vals}
    write_json(ROOT / "corrections.json", corr)
    return corr


def stage_audit() -> dict[str, Any]:
    """Both independent stdlib audits: the full re-derivation of every NEW/CORRECTED value and the short headline check."""
    for script in ("rederive.py", "headline_check.py"):
        p = subprocess.run([sys.executable, "-I", str(ROOT / "audit" / script)], capture_output=True, text=True, timeout=900)
        logger.info(f"{script}: " + p.stdout[-1500:])
        if p.returncode != 0:
            logger.error(p.stderr[-3000:])
    return {**read_json(ROOT / "audit" / "rederive_report.json"), "headline": read_json(ROOT / "audit" / "headline_check.json")}


@logger.catch(reraise=True)
def main() -> None:
    ap_ = argparse.ArgumentParser()
    ap_.add_argument("--stages", default="all")
    a = ap_.parse_args()
    stages = ALL if a.stages == "all" else a.stages.split(",")
    _limit_memory()
    t0 = time.time()
    from sections import s0_apply
    s0 = s0_apply.stage_s0() if "s0" in stages else None
    if s0:
        write_json(RESULTS / "s0.json", s0)
    else:
        s0 = read_json(RESULTS / "s0.json") if (RESULTS / "s0.json").exists() else None
    ctx = stage_a() if "a" in stages else load_ctx()
    if "a" in stages:
        ctx = load_ctx()
    items = run_items([s for s in stages if s in ITEM_STAGES], ctx)
    if "apply" in stages:
        if len(items) != 11:
            raise RuntimeError("apply needs every item stage a-k in the same run")
        edits = [e for it in items.values() for e in it["edits"]]
        apres = s0_apply.stage_apply(edits)
        write_json(RESULTS / "apply.json", apres)
        if not apres["apply_test_pass"]:
            raise RuntimeError("apply test failed")
        corr = write_corrections(items, s0, apres)
        write_json(RESULTS / "items_all.json", items)
    if "audit" in stages:
        write_json(RESULTS / "audit_summary.json", stage_audit())
    if "out" in stages:
        from sections import outputs
        outputs.write_all(read_json(RESULTS / "items_all.json"), read_json(ROOT / "corrections.json"),
                          read_json(RESULTS / "apply.json"), s0, load_ctx())
    logger.info(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
