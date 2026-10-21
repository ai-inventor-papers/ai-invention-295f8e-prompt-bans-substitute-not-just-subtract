#!/usr/bin/env python3
"""Stage 3 (a)-(d) for one gated unit: default, base repertoire, rivals, base audit, then the sha256 commitment of
predictions/unit_<u>.json (tag UNIT_<u>), which releases the GPU worker's guard on the unit's push arms.

Steps (each resumable): wait for TWIN / BASE / NOVELTY labels -> default -> association prompt + job (P4) -> wait for
ASSOC rows and the margin file -> rivals (opening margin, merit gap, twin modal share, novelty share / excess,
association counts, proximity) -> base audit (15 programs, non-default labels first, blind judges) -> prediction file
(analysis_a1a2.unit_prediction) -> prompt audit rerun -> commit.
Usage: python src/unit_commit.py A1 [--no-wait]
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from loguru import logger  # noqa: E402

from cfg5 import (DATA, E23, LAB_DIR, PRED, RAW_DIR, RESULTS, append_jsonl, read_json, read_jsonl,  # noqa: E402
                  setup_logging, sha256_file, unit_dir, utc_now, write_json)


def n_labelled(u: str, arm: str, model: str) -> int:
    return sum(1 for r in read_jsonl(LAB_DIR / f"{u}.jsonl") if r["arm"] == arm and r["model"] == model)


def n_raw(u: str, arm: str, model: str) -> int:
    return sum(1 for r in read_jsonl(RAW_DIR / f"{u}.jsonl") if r["arm"] == arm and r["model"] == model)


def wait_for(u: str, needs: list[tuple[str, str, int]], timeout: float = 3600) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        miss = [(a, m, n, n_labelled(u, a, m)) for a, m, n in needs if n_labelled(u, a, m) < n]
        if not miss:
            return True
        logger.info(f"{u}: waiting for labels {miss}")
        time.sleep(20)
    return False


def map_assoc(text: str, aliases: dict[str, list[str]], display: dict[str, str]) -> str | None:
    """Map one association answer to a catalogue mode with the alias lexicon (earliest mention wins)."""
    low = text.lower()
    best, pos = None, 10 ** 9
    for m, al in aliases.items():
        for a in [display[m]] + al:
            mm = re.search(rf"(?<![a-z]){re.escape(a.lower())}(?![a-z])", low)
            if mm and mm.start() < pos:
                best, pos = m, mm.start()
    return best


def merit(u: str, default: str, cat: list[str]) -> dict[str, Any]:
    from transformers import AutoTokenizer

    from cfg5 import model_path

    tok = AutoTokenizer.from_pretrained(model_path("instruct"))
    d = unit_dir(u)
    cases = [json.loads(l) for l in (d / "tests.jsonl").read_text().splitlines() if l.strip()]
    stress = [c for c in cases if c["kind"] == "stress"]
    refs = {m: (d / "references" / f"{m}.py").read_text() for m in cat if (d / "references" / f"{m}.py").exists()}
    if default not in refs:
        return {"merit_runtime_min": None, "merit_length_min": None, "per_mode": {}}
    L = {m: len(tok(c, add_special_tokens=False)["input_ids"]) for m, c in refs.items()}
    per = {}
    for m in refs:
        if m == default:
            continue
        rts = [math.log(max(c["ref_times"][m], 1e-6) / max(c["ref_times"][default], 1e-6)) for c in stress]
        per[m] = {"runtime_ratio_gm": math.exp(sum(rts) / len(rts)) if rts else None,
                  "length_ratio": L[m] / L[default]}
    rt = [v["runtime_ratio_gm"] for v in per.values() if v["runtime_ratio_gm"] is not None]
    ln = [v["length_ratio"] for v in per.values()]
    return {"merit_runtime_min": min(rt) if rt else None, "merit_length_min": min(ln) if ln else None,
            "per_mode": per, "ref_tokens": L}


def proximity(u: str, default: str, cat: list[str], twin_rows: list[dict[str, Any]]) -> dict[str, Any]:
    sys.path.insert(0, str(E23 / "src"))
    from prox import zs_pair

    d = unit_dir(u)
    progs = [r["code"] for r in twin_rows if r.get("passed") and r["label"] == default and r.get("code")][:20]
    out = {}
    for m in cat:
        if m == default:
            continue
        p = d / "references" / f"{m}.py"
        if not p.exists() or not progs:
            out[m] = None
            continue
        ds = [zs_pair(p.read_text(), c) for c in progs]
        ds = [x for x in ds if x is not None]
        out[m] = float(statistics.median(ds)) if ds else None
    return out


def margin_value(u: str, default: str) -> float | None:
    p = RESULTS / "margins" / f"{u}.json"
    if not p.exists():
        return None
    j = read_json(p)
    vals = []
    for w, res in j["per_w"].items():
        if default not in res:
            return None
        others = [v for m, v in res.items() if m != default]
        if others:
            vals.append(res[default] - max(others))
    return float(sum(vals) / len(vals)) if vals else None


def base_audit(u: str, default: str, base_rows: list[dict[str, Any]]) -> dict[str, Any]:
    from newbench.common.judge5 import adjudicate
    from newbench.common.label5 import spec_of

    valid = [r for r in base_rows if r["label"] not in ("invalid",) and r.get("code")]
    nondef = [r for r in valid if r["label"] != default]
    pick = (nondef + [r for r in valid if r["label"] == default])[:15]
    res = adjudicate(u, spec_of(u), [r["code"] for r in pick]) if pick else []
    agree = [a.get("label") == r["label"] for r, a in zip(pick, res) if a.get("label")]
    cv = 0
    for r, a in zip(pick, res):
        if r["label"] == "other" and r.get("passed") and a.get("label") not in (None, "other", default):
            cv += 1
    rate = sum(agree) / len(agree) if agree else None
    return {"n": len(pick), "n_judged": len(agree), "agreement": rate, "audit_weak": rate is not None and rate < 0.8,
            "catalogue_variant_other_correct": cv,
            "items": [{"sample_id": r["sample_id"], "label": r["label"], "judge": a} for r, a in zip(pick, res)]}


@logger.catch(reraise=True)
def main() -> None:
    from analysis_a1a2 import catalogue, labels, rows_of, twin_default, unit_prediction
    from commit5 import commit, has_tag
    from escape_rule import share
    from jobs import assoc_job
    from specs5 import SPECS, assoc_record, audit, display_name, load_tokenizer, PROMPTS_NEW

    ap = argparse.ArgumentParser()
    ap.add_argument("unit")
    ap.add_argument("--timeout", type=float, default=3600)
    args = ap.parse_args()
    u = args.unit
    setup_logging(f"unit_commit_{u}")
    if has_tag(f"UNIT_{u}") or has_tag(f"NODEFAULT_{u}"):
        logger.info(f"{u}: already committed")
        return
    ok = wait_for(u, [("TWIN", "instruct", 50), ("BASE", "base", n_raw(u, "BASE", "base")),
                      ("NOVELTY", "instruct", 30)], args.timeout)
    if not ok:
        logger.error(f"{u}: labels incomplete; not committing")
        return
    cat = catalogue(u)
    rows = labels(u)
    twin = rows_of(rows, "TWIN", "instruct")
    td = twin_default(twin)
    default = td["default"]
    if default is None:
        pred = unit_prediction(u, {})
        write_json(PRED / f"unit_{u}.json", pred)
        commit([PRED / f"unit_{u}.json"], f"NODEFAULT_{u}")
        logger.warning(f"{u}: NO DEFAULT (modal {td.get('modal')} share {td.get('share')}); reported, no pushes")
        return
    # association prompt + job
    pa = DATA / "prompts_assoc.jsonl"
    if not any(r["task"] == u for r in read_jsonl(pa)):
        tok = load_tokenizer()
        append_jsonl(pa, [assoc_record(tok, u, default)])
    assoc_job(u, 4)
    t0 = time.time()
    while (n_raw(u, "ASSOC", "instruct") < 20 or not (RESULTS / "margins" / f"{u}.json").exists()) and \
            time.time() - t0 < args.timeout:
        logger.info(f"{u}: waiting for association rows / margin file")
        time.sleep(15)
    sp = SPECS[u]
    display = {m: d for m, d, _ in sp["catalogue"]}
    assoc_rows = [r for r in read_jsonl(RAW_DIR / f"{u}.jsonl") if r["arm"] == "ASSOC"]
    mapped = [map_assoc(r["text"], sp["aliases"], display) for r in assoc_rows]
    survivors = [m for m in cat if m != default]
    assoc_counts = {m: sum(1 for x in mapped if x == m) for m in survivors}
    nov = rows_of(rows, "NOVELTY", "instruct")
    ns = share(nov, set(cat), default)
    tws = share(twin, set(cat), default)
    mer = merit(u, default, cat)
    rivals = {"opening_margin": margin_value(u, default), "merit_runtime_min": mer["merit_runtime_min"],
              "merit_length_min": mer["merit_length_min"], "merit_per_mode": mer["per_mode"],
              "twin_modal_share": td["share"], "novelty_share": ns["share"],
              "novelty_excess": (ns["share"] - tws["share"]) if (ns["share"] is not None and tws["share"] is not None)
              else None, "assoc_counts": assoc_counts, "assoc_unmapped": sum(1 for x in mapped if x is None),
              "assoc_default_named": sum(1 for x in mapped if x == default),
              "prox_dist": proximity(u, default, cat, twin), "K": len(cat)}
    base_rows = rows_of(rows, "BASE", "base")
    ba = base_audit(u, default, base_rows)
    write_json(RESULTS / f"base_audit_{u}.json", ba)
    pred = unit_prediction(u, rivals, ba)
    pred["merit_r_variant"] = (mer["per_mode"].get(pred.get("r")) if pred.get("r") else None)
    pred["base_audit"] = {k: v for k, v in ba.items() if k != "items"}
    rep = audit(read_jsonl(PROMPTS_NEW))
    assert rep["units"][u]["pass"], f"{u}: prompt audit failed before commitment"
    d = unit_dir(u)
    pred["sha256"] = {"prompts_new": sha256_file(PROMPTS_NEW), "runtime_rules": sha256_file(d / "runtime_rules.py"),
                      "ast_rules": sha256_file(d / "ast_rules.py"), "tests": sha256_file(d / "tests.jsonl"),
                      "analysis_code": sha256_file(Path(__file__).resolve().parent / "analysis_a1a2.py")}
    pred["committed_utc"] = utc_now()
    write_json(PRED / f"unit_{u}.json", pred)
    commit([PRED / f"unit_{u}.json"], f"UNIT_{u}")
    logger.info(f"{u}: committed default={default} beta={pred['beta']} r={pred['r']} class={pred['predicted_class']}")


if __name__ == "__main__":
    main()
