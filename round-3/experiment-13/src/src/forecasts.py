#!/usr/bin/env python3
"""S0.7-S0.8 nominees (ASSOCIATE, FRLP_FP8) and S1d: ban-free forecasts + hash-chained commitment before any ban
sample.

attempted = label != 'invalid'; avoidance = 1 - share of D among attempted; landing = counts over survivors S plus
'other' among attempted non-D programs.
SUBTRACT = landing of the LAST chain round (persistent = round 0, iterated rounds 1..3) with >= 20 non-D attempts;
  undefined (scored uniform, flagged) if no round has >= 20, or if D keeps >= 0.5 of attempts in every round
  ('not carried by a small set of surface tokens').
LADDER = summed non-D landing counts over the pushes (nonce, novelty, rand1-3) that each move >= 20 attempts off D;
  undefined otherwise; LADDER_EXISTS = at least 2 such pushes share a modal non-default label (a survivor).
ASSOCIATE, PROXIMITY = point masses on their nominees.  Descriptive: SUBTRACT_1SHOT (one-shot landing, same >= 20
rule), FRLP_FP8 (exp11 baseline FRLP mass over survivors with mass >= 0.01 and Kish ESS >= 5, renormalised).
DISAGREEING = among the four primary families with a defined top-1 (>= 2 defined), the top-1s are not all equal.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

from loguru import logger

from common import (COMMIT_LOG, DEFAULTS, FROZEN_CONSTANTS, INPUTS, N_BAN_PER_T, PRED, RESULTS, ROOT, TASK_ORDER, WS,
                    bench_import, canon, catalogue, read_json, read_jsonl, sha256_file, sha256_text, stable_seed,
                    survivors, task_dir, utc_now, write_json)
from score import PRIMARY, p_from_counts, p_point, top1

PUSHES = ["nonce", "novelty", "rand1", "rand2", "rand3"]
MIN_ND = FROZEN_CONSTANTS["forecast_min_non_default"]


# ------------------------------------------------------------------------------------------------ nominees
def associate_all() -> dict[str, Any]:
    out = {"rule": "modal mapped survivor among association.jsonl rows with X == D; ties -> catalogue order (flagged); "
                   "no survivor mapped -> undefined", "tasks": {}}
    for t in TASK_ORDER:
        D = DEFAULTS[t]
        S = survivors(t)
        rows = [r for r in read_jsonl(task_dir(t) / "association.jsonl") if r["X"] == D]
        c = Counter(r["mapped"] for r in rows if r.get("mapped") in S)
        if not c:
            out["tasks"][t] = {"nominee": None, "counts": dict(c), "n_rows": len(rows), "tie": False}
            continue
        m = max(c.values())
        tied = [s for s in S if c.get(s, 0) == m]
        out["tasks"][t] = {"nominee": tied[0], "counts": dict(c), "n_rows": len(rows), "tie": len(tied) > 1,
                           "unmapped_or_nonsurvivor": len(rows) - sum(c.values())}
    write_json(PRED / "associate.json", out)
    return out


def frlp_fp8_all() -> dict[str, Any]:
    cells = read_jsonl(INPUTS / "exp11" / "frlp_cells.jsonl")
    out = {"rule": "exp11 FP8 baseline FRLP: exp(L_corr) per survivor (variant main, half all); keep mass >= 0.01 and "
                   "Kish ESS >= 5; renormalise; none -> undefined.  Descriptive only (the FRLP gate failed).",
           "tasks": {}}
    for t in TASK_ORDER:
        S = survivors(t)
        mass = {}
        info = {}
        for c in cells:
            if c["task"] == t and c["variant"] == "main" and c["half"] == "all" and c["condition"] == "baseline" \
                    and c["algorithm"] in S:
                m = math.exp(c["L_corr"]) if c.get("L_corr") is not None else 0.0
                info[c["algorithm"]] = {"mass": m, "ess": c.get("ess"), "flags": c.get("flags")}
                if m >= 0.01 and (c.get("ess") or 0) >= 5:
                    mass[c["algorithm"]] = m
        tot = sum(mass.values())
        p = {s: mass.get(s, 0.0) / tot for s in S} if tot > 0 else None
        out["tasks"][t] = {"p": p, "cells": info, "defined": p is not None}
    write_json(PRED / "frlp_fp8.json", out)
    return out


# ------------------------------------------------------------------------------------------------ landings
def att(labs: list[dict], task: str) -> list[str]:
    return [r["label"] for r in labs if r["task"] == task and r["label"] != "invalid"]


def landing(labs: list[dict], task: str) -> Counter:
    D = DEFAULTS[task]
    S = survivors(task)
    c = Counter()
    for l in att(labs, task):
        if l == D:
            continue
        c[l if l in S else "other"] += 1
    return c


def arm_summary(labs: list[dict], task: str) -> dict[str, Any]:
    a = att(labs, task)
    D = DEFAULTS[task]
    n_all = sum(1 for r in labs if r["task"] == task)
    nd = sum(1 for l in a if l != D)
    return {"n": n_all, "n_attempted": len(a), "n_default": len(a) - nd, "n_non_default": nd,
            "default_share": (len(a) - nd) / len(a) if a else None, "avoidance": nd / len(a) if a else None,
            "landing": dict(landing(labs, task))}


def build(store_sub: str = "") -> dict[str, Any]:
    from vllm_stage import Store

    store = Store(store_sub)
    sfx = f"_{store_sub}" if store_sub else ""
    chain = read_json(PRED / f"iterated_chain{sfx}.json")
    ngr = read_json(PRED / f"ngrams{sfx}.json")["tasks"]
    prox = read_json(PRED / "proximity.json")["tasks"]
    assoc = read_json(PRED / "associate.json")["tasks"]
    frlp = read_json(PRED / "frlp_fp8.json")["tasks"]
    arms = {a: store.lab_rows(a) for a in ["twin", "oneshot", "sham", "persistent", "iter1", "iter2", "iter3",
                                           "nonce", "novelty", "rand", "hf_twin"]}
    for k in (1, 2, 3):
        arms[f"rand{k}"] = [r for r in arms["rand"] if r.get("arm") == f"rand{k}"]
    tasks = sorted({r["task"] for r in arms["twin"]}, key=TASK_ORDER.index)
    out: dict[str, Any] = {"rule": __doc__, "tasks": {}, "utc": utc_now()}
    for t in tasks:
        S = survivors(t)
        rec: dict[str, Any] = {"D": DEFAULTS[t], "S": S, "families": {}, "arms": {}}
        for a in arms:
            if a != "rand" and any(r["task"] == t for r in arms[a]):
                rec["arms"][a] = arm_summary(arms[a], t)
        # SUBTRACT
        ch = chain.get(t, {"rounds": [0]})
        rounds = ch.get("rounds", [0])
        rarms = ["persistent" if r == 0 else f"iter{r}" for r in rounds]
        rs = [rec["arms"].get(a) for a in rarms]
        rs_ok = [(a, s) for a, s in zip(rarms, rs) if s is not None]
        sub = {"rounds": rarms, "stop_reason": ch.get("stop_reason"), "flags": []}
        if rs_ok and all((s["default_share"] or 0) >= 0.5 for a, s in rs_ok):
            sub.update(defined=False, reason="D keeps >= 0.5 of attempts in every round",
                       p_raw=None)
            sub["flags"].append("not carried by a small set of surface tokens")
        else:
            cand = [(a, s) for a, s in rs_ok if s["n_non_default"] >= MIN_ND]
            if cand:
                a, s = cand[-1]
                sub.update(defined=True, source_round=a, counts=s["landing"], p_raw=p_from_counts(s["landing"], S))
            else:
                sub.update(defined=False, reason="no chain round with >= 20 non-D attempts", p_raw=None)
        rec["families"]["SUBTRACT"] = sub
        # LADDER
        qual, per = [], {}
        for p in PUSHES:
            s = rec["arms"].get(p)
            if s is None:
                continue
            per[p] = {"n_non_default": s["n_non_default"], "landing": s["landing"]}
            if s["n_non_default"] >= MIN_ND:
                qual.append(p)
        tot = Counter()
        for p in qual:
            tot.update(rec["arms"][p]["landing"])
        modal = {}
        for p in qual:
            l = Counter({k: v for k, v in rec["arms"][p]["landing"].items() if k in S})
            if l:
                mx = max(l.values())
                modal[p] = [k for k in S if l.get(k, 0) == mx][0]
        mc = Counter(modal.values())
        lad = {"qualifying_pushes": qual, "per_push": per, "modal_survivor_per_push": modal,
               "LADDER_EXISTS": bool(mc and max(mc.values()) >= FROZEN_CONSTANTS["ladder_exists_min_pushes"])}
        if qual:
            lad.update(defined=True, counts=dict(tot), p_raw=p_from_counts(dict(tot), S))
        else:
            lad.update(defined=False, reason="no push moved >= 20 attempts off D", p_raw=None)
        rec["families"]["LADDER"] = lad
        # ASSOCIATE / PROXIMITY
        an = assoc[t]["nominee"]
        rec["families"]["ASSOCIATE"] = {"defined": an is not None, "nominee": an, "p_raw": p_point(an, S),
                                        "tie": assoc[t].get("tie")}
        pn = prox[t].get("nominee")
        rec["families"]["PROXIMITY"] = {"defined": pn is not None, "nominee": pn, "p_raw": p_point(pn, S)}
        # descriptive
        s1 = rec["arms"].get("oneshot")
        if s1 and s1["n_non_default"] >= MIN_ND:
            rec["families"]["SUBTRACT_1SHOT"] = {"defined": True, "counts": s1["landing"],
                                                 "p_raw": p_from_counts(s1["landing"], S)}
        else:
            rec["families"]["SUBTRACT_1SHOT"] = {"defined": False, "p_raw": None,
                                                 "reason": "one-shot moved < 20 attempts off D"}
        fp = frlp[t]["p"]
        rec["families"]["FRLP_FP8"] = {"defined": fp is not None,
                                       "p_raw": ({**fp, "other": 0.0} if fp is not None else None)}
        rec["families"]["UNIFORM"] = {"defined": False, "p_raw": None, "note": "uniform reference"}
        for f, v in rec["families"].items():
            v["top1"], v["top1_tie"] = top1(v.get("p_raw"), S)
        tops = [rec["families"][f]["top1"] for f in PRIMARY if rec["families"][f]["top1"] is not None]
        rec["n_primary_defined"] = len(tops)
        rec["disagreeing"] = len(tops) >= 2 and len(set(tops)) > 1
        rec["co_veto"] = sorted(set(ngr[t]["distinctive"].get("co_veto", [])) |
                                set().union(*[set(ch.get(f"round{r}", {}).get("added", {}).get("co_veto", []))
                                              for r in rounds if r > 0]) if True else set())
        out["tasks"][t] = rec
        logger.info(f"{t}: top1 " + ", ".join(f"{f}={rec['families'][f]['top1']}" for f in PRIMARY) +
                    f" | disagreeing={rec['disagreeing']} LADDER_EXISTS={lad['LADDER_EXISTS']} "
                    f"SUBTRACT from {sub.get('source_round')}")
    write_json(PRED / f"forecasts{sfx}.json", out)
    return out


# ------------------------------------------------------------------------------------------------ commitment
def seeds_json(path: Path) -> None:
    seeds = {"rule": "int(sha256('iter3|exp|task|arm|template|idx')[:8], 16); veto redraw/continuation: "
                     "stable_seed('veto', sample_seed, round, n_vetoes, 'r'|'c'); HF uniforms: PCG64(stable_seed('u', "
                     "task, arm, template, idx)); random direction k at layer l: normal(PCG64-default_rng("
                     "int(sha256('rand{k}|L{l}')[:16], 16))), normalised; C2b null seed 20261021",
             "ban": {f"{t}:ban:{w}:{i}": stable_seed(t, "ban", w, i) for t in TASK_ORDER for w in WS
                     for i in range(N_BAN_PER_T)}}
    write_json(path, seeds, indent=None)


def commit_all(sub: str = "") -> dict:
    bench_import()
    from bench.common.commit import commit, verify_chain

    log = COMMIT_LOG if not sub else ROOT / "scratch" / "commitments_dryrun.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    sfx = f"_{sub}" if sub else ""
    if not sub and any(json.loads(l)["kind"] == "SEAL_BEFORE_BANS" for l in log.read_text().splitlines() if l):
        raise RuntimeError("already sealed; append a new versioned commitment instead of re-sealing")
    seeds_json(PRED / "seeds.json")
    write_json(PRED / "constants.json", FROZEN_CONSTANTS)
    norms = {p.name: sha256_file(p) for p in sorted((RESULTS / "tensors").glob("norms_*.npz"))}
    write_json(PRED / "norms_manifest.json", norms)
    files = [f"predictions/forecasts{sfx}.json", f"predictions/ngrams{sfx}.json", "predictions/ngrams_fp8.json",
             "predictions/proximity.json", "predictions/associate.json", "predictions/frlp_fp8.json",
             f"predictions/iterated_chain{sfx}.json", "predictions/seeds.json", "predictions/norms_manifest.json",
             "predictions/constants.json", "src/score.py", "src/c2b.py", "src/template_effect.py", "src/analyze.py",
             "src/common.py", "prompts/prompts.jsonl", "prompts/prompt_ids.json"]
    recs = []
    for f in files:
        p = ROOT / f
        if not p.exists():
            raise FileNotFoundError(f)
        recs.append(commit(log, "forecast_commit", sha256_file(p), {"path": f, "utc": utc_now()}))
    seal = commit(log, "SEAL_BEFORE_BANS", sha256_text(canon([r["sha256"] for r in recs])),
                  {"n_files": len(recs), "utc": utc_now()})
    head = sha256_text(log.read_text().splitlines()[-1])
    assert verify_chain(log)
    logger.info(f"SEALED ({log.name}): {len(recs)} files; chain head {head}")
    write_json(RESULTS / f"commitment_head{sfx}.json", {"chain_head": head, "seal_utc": seal["utc"],
                                                        "log": str(log.relative_to(ROOT))})
    return {"head": head, "seal": seal}


def tamper_test() -> dict:
    """T8: flipping one byte of a copied log must make verify_chain fail."""
    bench_import()
    from bench.common.commit import verify_chain

    src = ROOT / "scratch" / "commitments_dryrun.log"
    dst = ROOT / "scratch" / "commitments_tampered.log"
    txt = src.read_text()
    i = txt.index('"sha256":"') + 12
    dst.write_text(txt[:i] + ("0" if txt[i] != "0" else "1") + txt[i + 1:])
    res = {"original_verifies": verify_chain(src), "tampered_verifies": verify_chain(dst)}
    res["pass"] = res["original_verifies"] and not res["tampered_verifies"]
    write_json(RESULTS / "tamper_test.json", res)
    return res


if __name__ == "__main__":
    from common import setup_logging

    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["nominees", "build", "commit", "dryrun"])
    a = ap.parse_args()
    setup_logging(f"s1d_{a.what}")
    if a.what == "nominees":
        associate_all()
        frlp_fp8_all()
    elif a.what == "build":
        build("")
    elif a.what == "commit":
        commit_all("")
    else:
        build("smoke")
        commit_all("smoke")
        logger.info(f"tamper test: {tamper_test()}")
