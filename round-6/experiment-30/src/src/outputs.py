#!/usr/bin/env python3
"""STEP 11 method_out.json (exp_gen_sol_out schema): datasets site_grid, top5_manifold, f2_margins, engine_checks;
metadata holds every analysis, the deviations, the timing, the costs and the commitment chain."""

from __future__ import annotations

import os

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):  # 5-CPU cgroup: avoid BLAS oversubscription
    os.environ.setdefault(_v, "2")

import json
from collections import defaultdict
from typing import Any

import numpy as np
from loguru import logger

import decide as D
from cfg import (DATA_DIR, PRECISION, PRED_DIR, RESULTS_DIR, ROOT, read_json, read_jsonl, setup_logging, write_json)


def _lp(r: dict[str, Any] | None) -> str:
    if r is None:
        return "missing"
    return f"{r['label']}|{'pass' if r['passed'] else 'fail'}"


def _rj(name: str) -> Any:
    p = RESULTS_DIR / name
    return read_json(p) if p.exists() else None


def _strip(o: Any, drop: tuple[str, ...] = ("pairs_change", "embedding", "strata", "traces", "candidates")) -> Any:
    if isinstance(o, dict):
        return {k: _strip(v, drop) for k, v in o.items() if k not in drop}
    if isinstance(o, list):
        return [_strip(v, drop) for v in o]
    return o


def main() -> None:
    setup_logging("outputs")
    rows = read_jsonl(DATA_DIR / "samples.jsonl")
    base_prompts = {(r["task"], r["w"]): r["user_text"] for r in read_jsonl(ROOT / "inputs" / "exp17" / "prompts" /
                                                                             "prompts.jsonl") if r["kind"] == "twin"}
    idx = defaultdict(dict)
    for r in rows:
        idx[(r["task"], r["arm"])][(r["template"], int(r["k"]))] = r
    # ---------------- site_grid
    ex = []
    for (t, arm), cell in sorted(idx.items()):
        site = cell[next(iter(cell))]["site"]
        if site not in ("S0", "S4", "S5", "S1", "S2", "S3", "S1E") or t == "T1":
            continue
        twin = idx.get((t, "TWIN"), {})
        for (w, k), r in sorted(cell.items()):
            tw = twin.get((w, k))
            rd = r.get("realised_disp") or {}
            ex.append({"input": f"[{t} | template {w} | CRN slot {k} | site {site} | alpha {r['alpha']:g} | {PRECISION}] "
                                + base_prompts.get((t, w), ""),
                       "output": _lp(tw),
                       "predict_site_arm": _lp(r), "predict_twin": _lp(tw),
                       "metadata_task": t, "metadata_site": site, "metadata_alpha": r["alpha"],
                       "metadata_template": w, "metadata_slot": k, "metadata_y_correct_off_default": D.y_of(r),
                       "metadata_twin_y": D.y_of(tw) if tw else None,
                       "metadata_byte_identical_to_twin": (r["token_ids"] == tw["token_ids"]) if tw else None,
                       "metadata_disp_R35": rd.get("disp_R35"),
                       "metadata_disp_over_h": rd.get("disp_over_h_site_mean"),
                       "metadata_s3_kl_mean": (rd.get("s3") or {}).get("kl_mean_steps1_32"),
                       "metadata_direction_seed": r.get("direction_seed"), "metadata_finish_reason": r["finish_reason"],
                       "metadata_code_sha256": r.get("code_sha256"), "metadata_labeller_source": r["labeller_source"],
                       "metadata_precision": PRECISION})
    # ---------------- top5_manifold
    ex5 = []
    for key in ("T03|TOP5", "T03|TOP3", "T10|TOP5", "T1|TOP5"):
        t, site = key.split("|")
        for a in (1.0, 2.0, 4.0):
            cell = idx.get((t, f"{site}_a{a:g}"), {})
            rc = idx.get((t, f"S0_a{a:g}"), {})
            twin = idx.get((t, "TWIN"), {})
            for (w, k), r in sorted(cell.items()):
                lab = (lambda x: f"{x.get('label_k7', x['label'])}|{'pass' if x.get('passed_k7', x['passed']) else 'fail'}"
                       if x is not None else "missing") if t == "T1" else _lp
                ex5.append({"input": f"[{t} | {site} push | template {w} | slot {k} | alpha {a:g} | {PRECISION}] "
                                     + base_prompts.get((t, w), ""),
                            "output": lab(twin.get((w, k))),
                            "predict_push": lab(r), "predict_random_control": lab(rc.get((w, k))),
                            "predict_twin": lab(twin.get((w, k))),
                            "metadata_task": t, "metadata_setting": key, "metadata_alpha": a, "metadata_template": w,
                            "metadata_slot": k, "metadata_label_ext": r.get("label_ext"),
                            "metadata_code_sha256": r.get("code_sha256")})
    # ---------------- f2_margins
    f2 = _rj("f2.json") or {}
    ql = (_rj("q_lik_existing.json") or {}).get("tasks", {})
    exf = []
    for t, v in sorted(f2.items()):
        if not isinstance(v, dict) or "default" not in v:
            continue
        exf.append({"input": f"[{t}] twin margin: default {v.get('default')} vs runner-up {v.get('r_u')} "
                             f"(teacher-forced LP48, W1-W5, {PRECISION})",
                    "output": json.dumps({"m": v.get("m"), "verdict": v.get("verdict")}),
                    "predict_m_lp48": f"{v.get('m')}", "predict_m_lme": f"{v.get('m_lme')}",
                    "predict_m_tok": f"{v.get('m_tok')}", "predict_m_fork": f"{v.get('m_fork_median')}",
                    "predict_m_all": f"{v.get('m_all')}",
                    "metadata_task": t, "metadata_scoring_sd": v.get("scoring_sd"),
                    "metadata_q_lik": (ql.get(t) or {}).get("softmax_per_token_over_nondefault"),
                    "metadata_E_bf16": v.get("E_bf16_exp25"), "metadata_E_fp8": v.get("E_fp8_exp22")})
    if not exf:
        exf.append({"input": "F2 not run", "output": "not run"})
    # ---------------- engine_checks
    exe = []
    e25 = {(r["arm"], r["template"], int(r["slot"])): r for r in read_jsonl(ROOT / "inputs" / "exp25" / "data" /
                                                                           "samples.jsonl")
           if str(r["arm"]).startswith("ECBAN")}
    for r in rows:
        if not str(r["arm"]).startswith("ENG"):
            continue
        ref_arm = {"ENG_r9002_a1": "ECBAN_d9002_a1.0", "ENG_r9004_a1": "ECBAN_d9004_a1.0"}[r["arm"]]
        ref = e25.get((ref_arm, r["template"], int(r["k"])))
        exe.append({"input": f"[positive control U8 | {r['task']} | {r['arm']} | {r['template']} | slot {r['k']}]",
                    "output": _lp(ref) if ref else "missing", "predict_this_engine_w16a16": _lp(r),
                    "metadata_task": r["task"], "metadata_code_identical": (ref or {}).get("code") == r.get("code")})
    meta = {
        "method_name": "Site-specific random displacement in Qwen3-8B, W16A16 rerun of the iteration-4 site study",
        "precision": PRECISION, "model": "Qwen/Qwen3-8B@b968826d, thinking off, T 1.0",
        "s_a": _strip(_rj("s_a.json")), "s_b": _strip(_rj("s_b.json")), "s_c": _strip(_rj("s_c.json")),
        "s_d": _strip(_rj("s_d.json")), "f1": _strip(_rj("f1.json")), "f2": _strip(_rj("f2.json")),
        "landings": _strip(_rj("landings.json")), "dose_axis": _rj("dose_axis.json"),
        "failure_modes": _rj("failure_modes.json"), "engine_checks": _rj("engine_checks.json"),
        "unit_tests_gpu": _rj("unit_tests_gpu.json"), "unit_tests_cpu": _rj("unit_tests_cpu.json"),
        "units_summary": _rj("units_summary.json"), "push_progress": _rj("push_progress.json"),
        "banned_sets": read_json(PRED_DIR / "banned_sets.json")["sets"],
        "banned_sets_check": _rj("banned_sets_check.json"), "novelty_audit": _strip(_rj("novelty_audit.json"),
                                                                                   ("records",)),
        "fp8_vs_bf16_sites_n": len(_rj("fp8_vs_bf16_sites.json") or {}), "deviations": _rj("deviations.json"),
        "timing": _rj("timing_summary.json"), "costs": _rj("costs.json"), "rederive": _rj("rederive.json"),
        "rederive_extra": _rj("rederive_extra.json"),
        "commitments": _rj("commitment_audit.json"),
        "cells": {k: {kk: v[kk] for kk in ("n", "pass", "invalid", "share_correct_off_default", "share_ci",
                                            "composition_correct", "byte_identical_vs_twin")}
                  for k, v in (_rj("cells.json") or {}).items()}}
    out = {"metadata": meta, "datasets": [{"dataset": "site_grid", "examples": ex or [{"input": "none",
                                                                                       "output": "none"}]},
                                          {"dataset": "top5_manifold", "examples": ex5 or [{"input": "none",
                                                                                            "output": "none"}]},
                                          {"dataset": "f2_margins", "examples": exf},
                                          {"dataset": "engine_checks", "examples": exe or [{"input": "none",
                                                                                            "output": "none"}]}]}
    write_json(ROOT / "method_out.json", out, indent=None)
    logger.info(f"method_out.json: site_grid {len(ex)}, top5_manifold {len(ex5)}, f2 {len(exf)}, engine {len(exe)}")


if __name__ == "__main__":
    main()
