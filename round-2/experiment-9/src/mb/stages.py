#!/usr/bin/env python3
"""Sampling-side stages: smoke decision (descriptive variants), remaining forced programs, keep rule / program sets /
scrub (S4), and session 2 (S8)."""

from __future__ import annotations

import collections
import json
import math
from typing import Any

from loguru import logger

from common import (CATALOGUE, DATA_DIR, DESCRIPTIVE, M_MAX, MODES, RESULTS_DIR, THRESHOLDS, read_json, read_jsonl,
                    utc_now, write_json, write_jsonl)

VARIANTS = DATA_DIR / "variant_decisions.json"


def stage_smoke_decide() -> None:
    """Descriptive variant for an algorithm only if the smoke stage labels fewer than 7 of its 10 programs as
    requested (and a frozen description exists); logged before the remaining forced programs are generated."""
    lab = read_jsonl(DATA_DIR / "labelled_smoke.jsonl")
    dec: dict[str, Any] = {"utc": utc_now(), "rule": "descriptive if < 7/10 smoke programs labelled as requested and a "
                                                     "frozen description exists", "algorithms": {}}
    for task in MODES:
        for key in MODES[task]:
            rows = [r for r in lab if r["task"] == task and r["algorithm"] == key]
            k = sum(1 for r in rows if r["label"] == key)
            var = "desc" if (k < THRESHOLDS["smoke_descriptive_min"] and key in DESCRIPTIVE) else "plain"
            dec["algorithms"][f"{task}:{key}"] = {"n": len(rows), "as_requested": k, "variant": var,
                                                  "has_description": key in DESCRIPTIVE,
                                                  "labels": dict(collections.Counter(r["label"] for r in rows))}
            logger.info(f"smoke {task}:{key:<14} {k}/{len(rows)} as requested -> {var}")
    write_json(VARIANTS, dec)


def stage_forced_rest() -> None:
    from mb.gen import forced_requests, gen_stats, staged_run
    from mb.prompts import load_frozen

    dec = read_json(VARIANTS)["algorithms"]
    variants = {k: v["variant"] for k, v in dec.items()}
    frozen = load_frozen()
    plain = [tuple(k.split(":")) for k, v in variants.items() if v == "plain"]
    desc = [tuple(k.split(":")) for k, v in variants.items() if v == "desc"]
    reqs = forced_requests(frozen, "rest", 3, variants, only=plain)
    reqs += forced_requests(frozen, "desc", 4, variants, only=desc)
    logger.info(f"forced rest: {len(reqs)} requests ({sum(r['n'] for r in reqs)} samples); descriptive for {desc}")
    staged_run(reqs, DATA_DIR / "raw_forced_rest.jsonl", stages=(10, 100))
    logger.info(f"forced rest stats: {gen_stats(DATA_DIR / 'raw_forced_rest.jsonl')}")


def forced_program_rows() -> list[dict[str, Any]]:
    """The 40 forced programs per algorithm under its chosen variant (plain: smoke + rest; desc: the 4 descriptive)."""
    dec = read_json(VARIANTS)["algorithms"]
    smoke = read_jsonl(DATA_DIR / "labelled_smoke.jsonl")
    rest = read_jsonl(DATA_DIR / "labelled_forced_rest.jsonl")
    out = []
    for task in MODES:
        for key in MODES[task]:
            var = dec[f"{task}:{key}"]["variant"]
            if var == "plain":
                rows = [r for r in smoke + rest if r["task"] == task and r["algorithm"] == key
                        and r["condition"] == f"forced:{key}"]
            else:
                rows = [r for r in rest if r["task"] == task and r["algorithm"] == key
                        and r["condition"] == f"forced_desc:{key}"]
            # sample-major order (all 10 paraphrases' first sample, then the second, ...), so that P_j and its halves
            # are balanced over paraphrases
            rows.sort(key=lambda r: ((0 if r["stage"] == "smoke" else 1 + r["sample_index"]) if var == "plain"
                                     else r["sample_index"], r["paraphrase_id"]))
            out.extend(rows)
    return out


def stage_keep() -> None:
    """S4a: keep rule (T1: >= 70% of the 40 forced programs labelled as requested). With <= 6 kept T1 algorithms the
    extension has failed (F4); the analysis catalogue then also carries every non-kept T1 algorithm with >= 10 programs
    labelled as requested (flagged keep_failed; FRLP ratio-bias corrected by log of its as-requested share), so the
    literal five-name ban still leaves survivors (deviation D-catalogue)."""
    from common import deviation

    forced = forced_program_rows()
    write_jsonl(DATA_DIR / "labelled_forced_all.jsonl", forced)
    keep: dict[str, Any] = {"rule": "T1 kept if >= 70% of its 40 forced programs are labelled as requested (attempted, "
                                    "regardless of pass); T2 algorithms always run in LOS, FRLP flagged unavailable if "
                                    "< 10 programs are labelled", "tasks": {}}
    for task in MODES:
        keep["tasks"][task] = {}
        for key in MODES[task]:
            rows = [r for r in forced if r["task"] == task and r["algorithm"] == key]
            k = sum(1 for r in rows if r["label"] == key)
            share = k / max(len(rows), 1)
            kp = share >= THRESHOLDS["keep_forced_share"] if task == "t1" else True
            keep["tasks"][task][key] = {"n_forced": len(rows), "labelled_as_requested": k, "share": share,
                                        "passed_as_requested": sum(1 for r in rows if r["label"] == key and r["passed"]),
                                        "kept": kp, "frlp_available": k >= 10,
                                        "variant": read_json(VARIANTS)["algorithms"][f"{task}:{key}"]["variant"],
                                        "labels": dict(collections.Counter(r["label"] for r in rows))}
            logger.info(f"keep {task}:{key:<14} {k}/{len(rows)} ({share:.0%}) kept={kp} frlp={k >= 10}")
    n_kept = sum(v["kept"] for v in keep["tasks"]["t1"].values())
    keep["n_kept_t1"] = n_kept
    keep["extension_failed"] = n_kept <= 6
    keep["per_mode_reasons"] = {k: f"{v['labelled_as_requested']}/{v['n_forced']} forced programs labelled as requested "
                                   f"({v['variant']} prompt); labels {v['labels']}"
                                for k, v in keep["tasks"]["t1"].items() if not v["kept"]}
    analysis = [k for k in MODES["t1"] if keep["tasks"]["t1"][k]["kept"] or
                (keep["extension_failed"] and keep["tasks"]["t1"][k]["frlp_available"])]
    keep["analysis_catalogue"] = {"t1": analysis, "t2": [k for k in MODES["t2"] if keep["tasks"]["t2"][k]["frlp_available"]]}
    if keep["extension_failed"]:
        deviation("D-catalogue", f"Only {n_kept} of 10 grid algorithms pass the pre-registered keep rule (>= 70% of 40 "
                                 f"forced programs labelled as requested), so the extension has failed (F4). F4's reduced "
                                 f"form (TOP-5 over the kept catalogue) would ban every kept algorithm and leave no survivor; "
                                 f"instead the analysis catalogue adds every non-kept algorithm with >= 10 programs labelled "
                                 f"as requested ({[k for k in analysis if not keep['tasks']['t1'][k]['kept']]}), flagged "
                                 f"keep_failed, and cross-algorithm FRLP comparisons add log(as-requested share) to remove "
                                 f"the P(j | F_j) < 1 ratio bias. JPS and bidirectional A* (< 10 programs) are excluded.")
    write_json(RESULTS_DIR / "catalogue_keep.json", keep)
    logger.info(f"kept T1: {n_kept}; analysis catalogue {keep['analysis_catalogue']}")


def stage_psets() -> None:
    """S4b: program sets P_j (first min(30, n) labelled programs, sample-major), halves, scrubbing + verification."""
    from mb.scrub import scrub_program_rows

    keep = read_json(RESULTS_DIR / "catalogue_keep.json")
    forced = read_jsonl(DATA_DIR / "labelled_forced_all.jsonl")
    val = read_json(RESULTS_DIR / "labeller_ext_validation.json") if (RESULTS_DIR / "labeller_ext_validation.json").exists() \
        else {}
    excluded_gold = set((val.get("gold") or {}).get("excluded_algorithms") or [])
    psets: dict[str, Any] = {}
    for task in MODES:
        for key in keep["analysis_catalogue"][task]:
            if task == "t1" and key in excluded_gold:
                logger.warning(f"{key} excluded by the gold set")
                continue
            psets[f"{task}:{key}"] = [r for r in forced if r["task"] == task and r["algorithm"] == key
                                      and r["label"] == key]
    scrubbed = scrub_program_rows(psets)
    write_json(DATA_DIR / "program_sets.json", scrubbed)
    keep["excluded_by_gold"] = sorted(excluded_gold)
    keep["analysis_catalogue_final"] = {t: [k.split(":")[1] for k in scrubbed if k.startswith(t + ":")] for t in MODES}
    write_json(RESULTS_DIR / "catalogue_keep.json", keep)
    for k, v in scrubbed.items():
        logger.info(f"program set {k}: M={v['M']} (h1={sum(p['half'] == 1 for p in v['programs'])}), "
                    f"scrub replacements {v['n_replaced']}")


def stage_session2() -> None:
    """S8: TOP / ARC / SCATTER on T1, W1-W5 x 20, 10 -> 100 -> full; then labelled."""
    from mb.gen import ban_requests, gen_stats, staged_run

    sets = read_json(RESULTS_DIR / "planned_conditions.json")
    reqs = []
    for set_name, cond in sets["t1"].items():
        reqs += ban_requests("t1", f"multi:{set_name}", cond["templates"], "s2")
    logger.info(f"session 2: {len(reqs)} requests, {sum(r['n'] for r in reqs)} samples")
    staged_run(reqs, DATA_DIR / "raw_session2.jsonl", stages=(10, 100))
    logger.info(f"session-2 stats: {gen_stats(DATA_DIR / 'raw_session2.jsonl')}")


def halves(n: int) -> tuple[int, int]:
    h1 = math.ceil(n / 2)
    return h1, n - h1


def select_programs(cand: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return cand[:M_MAX]


__all__ = ["stage_smoke_decide", "stage_forced_rest", "stage_keep", "stage_session2", "forced_program_rows",
           "halves", "select_programs", "CATALOGUE", "json"]
