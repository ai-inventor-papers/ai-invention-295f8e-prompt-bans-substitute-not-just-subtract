#!/usr/bin/env python3
"""Iteration-6 label views (plan 0.9): final labels (labeller agreement, else blind-judge adjudication, else
'disputed'), the T 1.0 twin baseline, per-cell summaries and the escape rule with the iteration-6 share definition
(correct S-labelled programs / ALL programs of the cell), the default over the 300 twin samples, and the landing
events. Every function is pure given data/labels.jsonl, data/judge_labels.jsonl and data/samples_raw.jsonl."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from scipy.stats import binomtest

from cfg5 import (DEFAULT_SHARE, ESC_EXCESS, ESC_PASS_FRAC, LABELS, PRED_DIR, RAW, UNITS_DIR, direction_seed,
                  read_json, read_jsonl)
from labels_view import JUDGED, frozen_catalogue

_CACHE: dict[str, Any] = {}


def raw_meta() -> dict[str, dict[str, Any]]:
    out = {}
    for r in read_jsonl(RAW):
        if r.get("engine_check"):
            continue
        k = f"{r['unit']}|{r['template']}|{r['arm']}|{r['slot']}|{r['model_tag']}"
        out[k] = {kk: r.get(kk) for kk in ("unit", "template", "arm", "slot", "model_tag", "family", "alpha",
                                            "direction_seed", "temperature", "utc", "finish_reason", "n_tokens",
                                            "prompt_sha256", "stage", "engine", "precision", "rel_err_max",
                                            "hook_sha256", "kernel", "gtn_rel_err_max", "gtn_disp_mean",
                                            "gtn_target_mean")}
    return out


def all_final(units: set[str] | None = None) -> list[dict[str, Any]]:
    meta = raw_meta()
    judged = {r["key"]: r for r in read_jsonl(JUDGED)}
    cats: dict[str, set[str]] = {}
    out = []
    for l in read_jsonl(LABELS):
        if units is not None and l["unit"] not in units:
            continue
        m = meta.get(l["key"])
        if m is None:
            continue
        if l.get("family") in ("ASSOC", "ASSOC6", "ASSOCALL", "BINTI"):
            out.append({**m, "key": l["key"], "label": None, "assoc_mapped_all": l.get("assoc_mapped_all"),
                        "assoc_answer": l.get("assoc_answer"), "intent_text": l.get("intent_text"),
                        "passed": False, "valid": False, "label_source": l.get("labeller_source")})
            continue
        lab = l.get("label")
        src = l.get("labeller_source")
        if lab is None:
            j = judged.get(l["key"])
            if j is not None and j.get("label") is not None:
                lab, src = j["label"], "judge_" + j["how"]
            else:
                lab, src = "disputed", ("judge_pending" if j is None else "judge_no_majority")
        cat = cats.setdefault(l["unit"], set(frozen_catalogue(l["unit"])))
        if lab not in cat and lab not in ("other", "invalid", "disputed"):
            lab = "other"
        out.append({**m, "key": l["key"], "label": lab, "label_source": src, "passed": bool(l.get("passed")),
                    "valid": bool(l.get("valid")), "runtime_label": l.get("runtime_label"),
                    "ast_label": l.get("ast_label"), "code_sha256": l.get("code_sha256"), "code": l.get("code")})
    return out


def twin_rows(rows: list[dict], u: str, temps: tuple[float, ...] = (1.0, 1.3)) -> list[dict]:
    out = []
    for r in rows:
        if r["unit"] != u or r["model_tag"] != "instruct":
            continue
        if r["arm"] == "TWIN" and 1.0 in temps:
            out.append(r)
        elif r["arm"] == "T13" and 1.3 in temps and r.get("engine") == "vllm":
            out.append(r)
    return out


def default_from(rows: list[dict], u: str) -> dict[str, Any]:
    """DEFAULT = modal CORRECT label over the 300 twin samples (T 1.0 + T 1.3), share >= 0.6, else NO_DEFAULT."""
    cat = set(frozen_catalogue(u))
    tw = twin_rows(rows, u)
    corr = Counter(r["label"] for r in tw if r["passed"] and r["label"] in cat)
    oth = sum(1 for r in tw if r["passed"] and r["label"] not in cat)
    n_corr = sum(corr.values()) + oth
    res: dict[str, Any] = {"n_twin": len(tw), "n_correct": n_corr, "counts_correct": dict(corr), "other_correct": oth}
    if corr:
        d, c = sorted(corr.items(), key=lambda kv: (-kv[1], list(frozen_catalogue(u)).index(kv[0])))[0]
        share = c / n_corr if n_corr else 0.0
        res.update(default=d if share >= DEFAULT_SHARE - 1e-12 else "NO_DEFAULT", default_share=share, modal=d)
    else:
        res.update(default="NO_DEFAULT", default_share=0.0, modal=None)
    t10 = Counter(r["label"] for r in twin_rows(rows, u, (1.0,)) if r["passed"] and r["label"] in cat)
    res["default_T10_only"] = t10.most_common(1)[0][0] if t10 else None
    return res


def committed(u: str) -> dict[str, Any] | None:
    p = PRED_DIR / "units" / f"{u}.json"
    return read_json(p) if p.exists() else None


def twin_baseline(rows: list[dict], u: str, d: str, engine_ok: bool = True) -> dict[str, Any]:
    """T 1.0 twin: 50 HF CRN slots (k 0-9) + 150 vLLM slots (k 10-39) if the unit passed the engine check."""
    cat = set(frozen_catalogue(u))
    S = cat - {d}
    tw = [r for r in rows if r["unit"] == u and r["model_tag"] == "instruct" and r["arm"] == "TWIN" and
          (r.get("engine") == "hf" and r["slot"] < 10 or (engine_ok and r.get("engine") == "vllm"))]
    n = len(tw)
    k_off = sum(1 for r in tw if r["passed"] and r["label"] in S)
    return {"n": n, "pass": (sum(r["passed"] for r in tw) / n) if n else None, "k_off": k_off,
            "off": k_off / n if n else None, "p0": (k_off + 0.5) / (n + 1)}


def cell_summary(rr: list[dict], S: set[str]) -> dict[str, Any]:
    n = len(rr)
    k = sum(1 for r in rr if r["passed"] and r["label"] in S)
    return {"n": n, "pass_rate": (sum(r["passed"] for r in rr) / n) if n else None, "k_off": k,
            "share": k / n if n else None,
            "landing_counts": dict(Counter(r["label"] for r in rr if r["passed"] and r["label"] in S)),
            "other_correct": sum(1 for r in rr if r["passed"] and r["label"] == "other"),
            "labels_attempted": dict(Counter(r["label"] for r in rr))}


def escape_table(rows: list[dict], u: str, d: str, alphas: tuple[float, ...], engine_ok: bool = True
                 ) -> dict[str, Any]:
    cat = set(frozen_catalogue(u))
    S = cat - {d}
    tw = twin_baseline(rows, u, d, engine_ok)
    by: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["unit"] == u and r.get("family") == "ESC":
            by[r["arm"]].append(r)
    cells = []
    for a in alphas:
        for kk in range(8):
            s = direction_seed(u, kk)
            arm = f"ESC_d{s}_a{a}"
            rr = by.get(arm, [])
            s1 = [r for r in rr if r["slot"] in (0, 1)]
            s30 = [r for r in rr if r["slot"] in range(6)]
            S1 = cell_summary(s1, S)
            S30 = cell_summary(s30, S)
            qual1 = S1["pass_rate"] is not None and tw["pass"] is not None and \
                S1["pass_rate"] >= ESC_PASS_FRAC * tw["pass"] - 1e-12
            st1 = len(s1) >= 10 and qual1 and S1["share"] - (tw["off"] or 0.0) >= ESC_EXCESS - 1e-12
            conf, p = False, None
            qual30 = S30["pass_rate"] is not None and tw["pass"] is not None and \
                S30["pass_rate"] >= ESC_PASS_FRAC * tw["pass"] - 1e-12
            if st1 and len(s30) >= 30:
                p = float(binomtest(S30["k_off"], S30["n"], tw["p0"], alternative="greater").pvalue)
                conf = p < 0.05 and qual30
            cells.append({"arm": arm, "dir_seed": s, "dir_k": kk, "alpha": a, "n": len(s30) if len(s30) >= 30 else
                          len(s1), "stage1": S1, "stage1_pass": st1, "pooled30": S30 if len(s30) >= 30 else None,
                          "confirmed": conf, "p": p, "qualifies": qual30 if len(s30) >= 30 else qual1,
                          "pass_rate": (S30 if len(s30) >= 30 else S1)["pass_rate"],
                          "share": (S30 if len(s30) >= 30 else S1)["share"],
                          "needs_confirmation": st1 and len(s30) < 30, "n_rows": len(rr)})
    E = {}
    for a in alphas:
        cs = [c for c in cells if c["alpha"] == a]
        if any(c["n_rows"] > 0 for c in cs):
            E[str(a)] = sum(c["confirmed"] for c in cs) / 8
    return {"twin": tw, "cells": cells, "E_by_alpha": E, "E_u": (sum(E.values()) / len(E)) if E else None}
