#!/usr/bin/env python3
"""STEP OUT: eval_out.json in the exp_eval_sol_out format (full, mini and preview variants), validated by aii-json."""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path
from typing import Any

from loguru import logger

from sections.common import ROOT, TABLES, READ_DATE, write_json


def _s(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, float):
        return f"{x:.6g}"
    if isinstance(x, (dict, list)):
        return json.dumps(x, ensure_ascii=False)
    return str(x)


def _num(x: Any) -> float | None:
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def _csv(name: str) -> list[dict[str, str]]:
    with (TABLES / name).open() as f:
        return list(csv.DictReader(f))


def datasets(corr: dict[str, Any], pos: dict[str, Any]) -> list[dict[str, Any]]:
    ds = []
    ex = []
    for v in corr["values"]:
        e = {"input": f"{v['name']} [{v['source']}]", "output": _s(v["recomputed"]), "predict_recorded_in_report": _s(v["recorded"]),
             "metadata_status": v["status"], "metadata_item": v.get("item", ""), "metadata_source": v["source"],
             "metadata_tolerance": _s(v["tolerance"]), "eval_status_match": 1.0 if v["status"] == "MATCH" else 0.0,
             "eval_status_corrected": 1.0 if v["status"] == "CORRECTED" else 0.0}
        if v.get("note"):
            e["metadata_note"] = v["note"]
        ex.append(e)
    ds.append({"dataset": "corrections", "examples": ex})
    ex = []
    for e in corr["corrections"]:
        ex.append({"input": e["old_text"], "output": e["new_text"], "metadata_id": e["id"], "metadata_item": e["item"],
                   "metadata_section": e["section"], "metadata_kind": e["kind"], "metadata_line_at_read": e.get("line_at_read"),
                   "eval_len_change": float(len(e["new_text"]) - len(e["old_text"]))})
    ds.append({"dataset": "report_edits", "examples": ex})
    ex = []
    for r in _csv("counting_sort_adjudication.csv"):
        ex.append({"input": f"{r['sample_id']} (cell {r['cell']}, sha {r['code_sha256'][:12]})", "output": r["final_label"],
                   "predict_rule": r["rule_label"], "predict_judge_A": r["judge_A"], "predict_judge_B": r["judge_B"],
                   "predict_manual_read": r["manual_read"], "predict_old_label": r["old_label"],
                   "metadata_task": r["task"], "metadata_final_source": r["final_source"], "metadata_passed": r["passed"],
                   "eval_rule_agrees_final": 1.0 if r["rule_label"] == r["final_label"] else 0.0,
                   "eval_old_agrees_final": 1.0 if r["old_label"] == r["final_label"] else 0.0})
    ds.append({"dataset": "counting_sort_adjudication", "examples": ex})
    ex = []
    for r in _csv("recovery_by_source.csv"):
        e = {"input": f"{r['task']} | {r['source']} | rank {r['rank']}", "output": r["recovery"] if r["generated"] == "y" else "not generated",
             "metadata_Y": r["Y"], "metadata_base": r["base"], "metadata_full": r["full"], "metadata_das_count": r.get("das_count", ""),
             "metadata_share_cp95": f"[{r.get('share_cp95_lo', '')}, {r.get('share_cp95_hi', '')}]"}
        rv = _num(r.get("recovery"))
        if rv is not None:
            e["eval_recovery"] = rv
        ex.append(e)
    ds.append({"dataset": "recovery_by_source", "examples": ex})
    ex = []
    for r in _csv("gemma_natural_variance.csv"):
        ex.append({"input": f"Gemma block {r['block']} rank {r['rank']}", "output": "below the random 95th percentile" if r["below_p95"] == "True" else "above the random 95th percentile",
                   "eval_share": float(r["share"]), "eval_random_p95": float(r["random_p95"]), "eval_random_mean": float(r["random_mean"])})
    ds.append({"dataset": "gemma_natural_variance", "examples": ex})
    ex = []
    for r in _csv("control_protocols.csv"):
        ex.append({"input": r["family"], "output": f"objective: {r['objective']}; readout: {r['site_and_readout']}; permutation: {r['permutation_scheme']}; untrained network: {r['untrained_network']}",
                   "metadata_pairs": r["pairs"]})
    ds.append({"dataset": "control_protocols", "examples": ex})
    ex = []
    for r in _csv("search_by_arm.csv"):
        ex.append({"input": f"T03 level b, arm {r['arm']} ({r['arm_name']})", "output": f"{r['level_b_programs']}/{r['calls']}",
                   "metadata_techniques": r["techniques"], "metadata_rate_cp95": f"[{float(r['rate_cp95_lo']):.4f}, {float(r['rate_cp95_hi']):.4f}]",
                   "eval_rate": float(r["rate"]), "eval_merged_clusters": float(r["merged_clusters"])})
    ds.append({"dataset": "search_by_arm", "examples": ex})
    ex = []
    for r in pos["rows"]:
        ex.append({"input": f"{r['name']} ({r['venue_claimed']})", "output": r["status"], "metadata_url": r["url"],
                   "metadata_version": r["version"], "metadata_arxiv_comment": r["arxiv_comment"] or "",
                   "metadata_title_quote": r["title_quote"] or "", "metadata_venue_quote": r["venue_quote"] or "",
                   "metadata_date": r["date"], "metadata_claim_group": r["claim_group"],
                   "eval_verified": 1.0 if r["status"].startswith("VERIFIED") else 0.0})
    for w in next(r for r in pos["rows"] if r["key"] == "tale")["workshop_posters"]:
        ex.append({"input": f"A Tale of Two Temperatures, ICML 2026 workshop poster ({w['workshop']})", "output": w["status"],
                   "metadata_url": w["url"], "metadata_quote": w["quote"] or "", "metadata_date": w["date"],
                   "eval_verified": 1.0 if w["status"] == "VERIFIED" else 0.0})
    ds.append({"dataset": "positioning_rows", "examples": ex})
    return ds


def _trunc(o: Any, n: int = 200) -> Any:
    if isinstance(o, str):
        return o if len(o) <= n else o[:n] + "..."
    if isinstance(o, dict):
        return {k: _trunc(v, n) for k, v in o.items()}
    if isinstance(o, list):
        return [_trunc(v, n) for v in o]
    return o


def write_all(items: dict[str, Any], corr: dict[str, Any], ap: dict[str, Any], s0: dict[str, Any] | None,
              ctx: dict[str, Any]) -> None:
    pos = json.loads((ROOT / "positioning.json").read_text())
    audit = json.loads((ROOT / "audit" / "rederive_report.json").read_text()) if (ROOT / "audit" / "rederive_report.json").exists() else {}
    a4, a2, a5 = ctx["a4"], ctx["a2"], ctx["a5"]
    sa = items["0a"]["summary"]
    se = items["0e"]["summary"]
    si = items["0i"]["summary"]
    sb = items["0b"]["summary"]
    vb = corr["values_by_status"]
    k = a4["kappa"]
    spend = a4["spend"]["this_run_usd"] + a4["spend"]["cached_usd"]
    m = {"lint_before": ap["lint_before"], "lint_after": ap["lint_after"], "n_corrections": corr["n_edits"],
         "n_values": corr["n_values"], "n_MATCH": vb["MATCH"], "n_CORRECTED": vb["CORRECTED"], "n_NEW": vb["NEW"],
         "n_CARRIED": vb["CARRIED"], "apply_test_pass": 1.0 if ap["apply_test_pass"] else 0.0,
         "apply_placebo_fails": 1.0 if ap["placebo_mutation_fails"] else 0.0,
         "n_checks": float(audit.get("n_checks", 0)), "n_mismatch": float(audit.get("n_mismatch", -1)),
         "placebos_failed": float(audit.get("n_placebos_failed", 0)), "n_placebos": float(audit.get("n_placebos", 0)),
         "judge_gate_A": float(a4["gate"]["A"]["score"]), "judge_gate_B": float(a4["gate"]["B"]["score"]),
         "kappa_rule_vs_A": k["rule_vs_A"], "kappa_rule_vs_B": k["rule_vs_B"], "kappa_A_vs_B": k["A_vs_B"],
         "manual_overrides": float(a4["manual_overrides"]), "n_manual_reads": float(a4["n_manual_reads"]),
         "labeller_ref_agreement": a2["ref_agreement_v2"], "labeller_gold_kappa_old": a2["gold_old_recomputed"]["kappa_runtime_ast"],
         "labeller_gold_kappa_new": a2["gold_new"]["kappa_runtime_ast"], "labeller_gold_agree_old": a2["gold_old_recomputed"]["runtime_vs_adjudicated"],
         "labeller_gold_agree_new": a2["gold_new"]["runtime_vs_adjudicated"], "labeller_controls_pass": float(a2["controls_pass"]),
         "relabel_transitions": float(ctx["a3"]["n_transitions"]),
         "kth_pooled_recovery_k1": sa["kth_pooled_recovery"][1] if 1 in sa["kth_pooled_recovery"] else sa["kth_pooled_recovery"]["1"],
         "kth_pooled_recovery_k4": sa["kth_pooled_recovery"][4] if 4 in sa["kth_pooled_recovery"] else sa["kth_pooled_recovery"]["4"],
         "kth_pooled_recovery_k16": sa["kth_pooled_recovery"][16] if 16 in sa["kth_pooled_recovery"] else sa["kth_pooled_recovery"]["16"],
         "counting_sort_full_state_count": float(sa["full_state_counting_sort"]),
         "untrained_ratio_committed": sb["untrained_ratios"]["committed_contrastive"], "untrained_ratio_fit": sb["untrained_ratios"]["fit_value"],
         "untrained_ratio_lmeY": sb["untrained_ratios"]["matched_lmeY"],
         "fork_margin_spearman": items["0d"]["summary"]["rho_margin"], "llr48_spearman": items["0d"]["summary"]["rho_llr48"],
         "gemma_ranks_below_p95": float(len(se["ranks_below_p95"])), "search_rate_ratio": si["rate_ratio"], "search_rate_ratio_LB": si["LB95"],
         "spend_usd": spend}
    hc_p = ROOT / "audit" / "headline_check.json"
    if hc_p.exists():
        hc = json.loads(hc_p.read_text())
        m.update({"headline_rederived_ok": hc["n_ok"], "headline_rederived_n": hc["n"],
                  "headline_placebos_failed": hc["placebos_failed"], "headline_n_placebos": hc["n_placebos"]})
    m = {kk: float(v) for kk, v in m.items()}
    sections = {}
    for key, it in items.items():
        sections[key] = {"verdict": it.get("verdict"), "n_edits": len(it["edits"]), "edit_ids": [e["id"] for e in it["edits"]],
                         "values": [{kk: v.get(kk) for kk in ("name", "recorded", "recomputed", "status", "source")} for v in it["values"]],
                         **({"summary": it["summary"]} if "summary" in it else {})}
    meta = {"evaluation_name": "iteration-8 Step 0: erratum and re-derivation pass over the iteration-7 record",
            "read_date": READ_DATE, "dependencies": ["art_veI9l_Rb9wDY", "art_pHL7LWNhpcCS", "art_MZAfDPVhM6Ui", "art_8O5eaNc5gxJs",
                                                     "art_VhaHGe7SxV95", "art_HY7uYZz-OjRW"],
            "read_by_path": ["art_LzP2qPwUrANz (positioning.json, report_corrected.md, corrections.json)", "iter_8 gen_strat current_report.md"],
            "report_sha256_in": ap.get("report_sha256_in"), "report_sha256_out": ap.get("report_sha256_out"),
            "sections": sections, "judges": {"A": a4["gate"]["A"]["model"], "B": a4["gate"]["B"]["model"]},
            "audit": {kk: audit.get(kk) for kk in ("n_checks", "n_mismatch", "n_placebos", "n_placebos_failed")},
            "headline_check": json.loads(hc_p.read_text()) if hc_p.exists() else None,
            "outputs": ["corrections.json", "report_corrected.md", "report.diff", "positioning.json", "tables/*.csv", "audit/rederive.py"]}
    out = {"metadata": meta, "metrics_agg": m, "datasets": datasets(corr, pos)}
    write_json(ROOT / "eval_out.json", out)
    import os
    sk = Path(os.environ.get("AII_JSON_SKILL_DIR", ROOT.parents[6] / ".claude" / "skills" / "aii-json"))
    py = sk / ".." / ".ability_client_venv" / "bin" / "python"
    fmt = subprocess.run([str(py), str(sk / "scripts" / "aii_json_format_mini_preview.py"), "--input", str(ROOT / "eval_out.json")],
                         capture_output=True, text=True, timeout=300) if py.exists() else None
    if fmt is None or fmt.returncode != 0:
        # fallback when the aii-json skill is absent: the same three files from this module (3 examples per dataset)
        logger.warning("aii-json format script unavailable; writing full/mini/preview with the built-in generator")
        write_json(ROOT / "full_eval_out.json", out)
        mini = {"metadata": meta, "metrics_agg": m, "datasets": [{"dataset": d["dataset"], "examples": d["examples"][:3]} for d in out["datasets"]]}
        write_json(ROOT / "mini_eval_out.json", mini)
        write_json(ROOT / "preview_eval_out.json", _trunc(mini))
    else:
        logger.info("full/mini/preview written by the aii-json format script")
    if not sk.exists():
        logger.warning(f"aii-json skill not found at {sk.name}; schema validation skipped")
        return
    for f in ("eval_out.json", "full_eval_out.json", "mini_eval_out.json", "preview_eval_out.json"):
        p = subprocess.run([str(sk / ".." / ".ability_client_venv" / "bin" / "python"), str(sk / "scripts" / "aii_json_validate_schema.py"),
                            "--format", "exp_eval_sol_out", "--file", str(ROOT / f)], capture_output=True, text=True, timeout=300)
        logger.info(f"schema {f}: {'PASSED' if 'PASSED' in p.stdout else 'FAILED'} {p.stdout[-400:] if 'PASSED' not in p.stdout else ''}")
