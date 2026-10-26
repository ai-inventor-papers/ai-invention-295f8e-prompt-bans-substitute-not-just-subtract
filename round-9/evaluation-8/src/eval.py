#!/usr/bin/env python3
"""Iteration-9 Step 0: repair of the iteration-8 research record (items 0a-0g of the blocking review).

uv run eval.py --stages all
  setup    vendor-check the report, hash every input (inputs_manifest.json)
  0e       alias-overlap geometry on iteration 8's stored geodesics (needs predictions/commit_s0e.json first)
  ledger   recompute every quoted number (0a circuit, 0b DAS, 0c entropy/law, 0f Gemma arms)
  edits    positioning (0d), figure markers (0g), 0e text, build edits, apply test, whole-report lint, outputs
  eval_out eval_out.json (exp_eval_sol_out) + inputs-unchanged assert
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import resource
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from loguru import logger

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
import alias_geometry as AG  # noqa: E402
import apply_lint as AL  # noqa: E402
import edits_spec  # noqa: E402
import recompute as RC  # noqa: E402
import s0_extra as SX  # noqa: E402
import stage_0e as S0E  # noqa: E402
import tertiary_bpe  # noqa: E402

REPORT_SRC = Path(os.environ.get("S0_REPORT_SRC", ROOT.parents[1] / "gen_strat" / "current_report.md"))
REPORT = ROOT / "inputs/report/current_report.md"
RESULTS, TABLES = ROOT / "results", ROOT / "tables"

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
(ROOT / "logs").mkdir(exist_ok=True)
logger.add(ROOT / "logs/eval.log", rotation="30 MB", level="DEBUG")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def input_files() -> list[tuple[str, Path]]:
    A = RC.ART
    rel = {
        RC.CIRC: ["results/summary.json", "data/validation_rows_C1forced.jsonl", "data/validation_rows_C2a.jsonl",
                  "data/validation_rows_C1nat.jsonl", "src/k3circuit.py", "src/k3motif.py", "results/positioning.json"],
        RC.DAS: ["results/analysis.json", "results/geometry.json", "results/positioning.json", "src/figures8.py"],
        RC.FORK: ["results/k1_verdict.json", "results/k1_cells.json", "results/amendment.json",
                  "predictions/commit1_dose_table.json", "data/samples.jsonl", "src/analysis_k1.py",
                  "results/geometry_f8.json", "results/positioning.json", "src/figures8.py"],
        RC.LAW: ["results/analysis_L.json", "results/positioning.json"],
        RC.GEM: ["results/positioning.json", "src/outputs8.py"],
        RC.TP: ["results/geometry_M1.json", "results/geometry_M2.json", "src/common.py", "src/prompts_tp.py",
                "src/geometry.py", "src/stages.py", "src/figures.py", "cache/states/geo_C6_nf4.npz",
                "cache/states/smean_C6_nf4.npz", "results/positioning.json"],
    }
    figs = {RC.FORK: ["F8_activation_geometry"], RC.DAS: ["F3_geometry_T10", "F3_geometry_GRID", "F3b_handle_axis_T10",
                                                          "F3b_handle_axis_GRID"],
            RC.GEM: ["F4_geometry"], RC.TP: ["F3_mds_C6_nf4", "F4_isomap_C6_nf4", "F5_M2_C6"]}
    out = [("report:inputs/report/current_report.md", REPORT)]
    for art, files in rel.items():
        out += [(f"{art}:{f}", A[art] / f) for f in files]
    for art, fs in figs.items():
        out += [(f"{art}:figures/{f}.{e}", A[art] / f"figures/{f}.{e}") for f in fs for e in ("png", "pdf")]
    return out


def stage_setup() -> dict[str, Any]:
    if REPORT_SRC.exists():
        if sha(REPORT) != sha(REPORT_SRC):
            raise RuntimeError("vendored report differs from the strategy's input")
    else:
        logger.info("strategy input not present (published copy): using the vendored report and its recorded sha256")
    if sha(REPORT) != "8b3804f3ecbfedd4c1d54586edd56fe02aaa5c81e4570f4a3aa171ad0cbd7438":
        raise RuntimeError("vendored report is not the report this repair was built for")
    man = {k: {"sha256": sha(p), "bytes": p.stat().st_size} for k, p in input_files()}
    man["_report_source"] = str(REPORT_SRC.name)
    (ROOT / "inputs_manifest.json").write_text(json.dumps(man, indent=1))
    logger.info(f"inputs manifest: {len(man) - 1} files hashed; report sha256 {man['report:inputs/report/current_report.md']['sha256'][:16]}")
    return man


def stage_0e() -> dict[str, Any]:
    commit = ROOT / "predictions/commit_s0e.json"
    if not commit.exists():
        raise RuntimeError("predictions/commit_s0e.json missing: run src/commit_s0e.py before any alias-level number")
    committed = json.loads(commit.read_text())["code_sha256"]
    now = {p: sha(ROOT / p) for p in committed}
    if now != committed:
        line = (f"{dt.datetime.now(dt.timezone.utc).isoformat()} AMENDMENT S0-0e code changed after commit: "
                + " ".join(f"{k}={v}" for k, v in now.items()) + "\n")
        log = ROOT / "commitments.log"
        if line.split(" ", 1)[1] not in log.read_text():
            with log.open("a") as f:
                f.write(line)
        logger.warning("0e code differs from the committed hash; amendment logged")
    t0 = time.time()
    res = S0E.run(RC.ART[RC.TP], ROOT)
    res["seconds"] = round(time.time() - t0, 1)
    res["code_matches_commit"] = now == committed
    (RESULTS / "s0e.json").write_text(json.dumps(res, indent=1, default=float))
    logger.info(f"0e verdict {res.get('verdict', {}).get('code')} in {res['seconds']} s")
    return res


def stage_ledger(led: RC.Ledger) -> dict[str, Any]:
    out = {"0a": RC.recompute_0a(led, ROOT), "0b": RC.recompute_0b(led), "0c": RC.recompute_0c(led, ROOT),
           "0f": RC.recompute_0f(led, ROOT)}
    logger.info(f"ledger: {Counter(r['status'] for r in led.rows)}")
    return out


def stage_edits(led: RC.Ledger, rec: dict[str, Any], z: dict[str, Any], tz: dict[str, Any] | None) -> dict[str, Any]:
    report = REPORT.read_text()
    pos = SX.positioning(ROOT)
    markers = SX.figure_markers(ROOT, z)
    alias_md = next(m for m in markers if m["id"] == "fig_alias_overlap")["block_md"]
    at = SX.alias_text(z, led, alias_md, tz)
    led.add("0e.M2.g16", "0e", RC.get(RC.TP, "results/geometry_M2.json", "label_decodability_balanced_acc.g16"),
            RC.src(RC.TP, "results/geometry_M2.json", "label_decodability_balanced_acc.g16"), ".2f", recorded="0.53")
    weak = []
    c2 = [r for r in rec["0a"]["table_rows"] if r["contrast"] == "C2a"]
    both = {n for n in {r["node"] for r in c2} if all(r["p_holm_20"] < 0.05 for r in c2 if r["node"] == n)}
    for r in c2:
        if r["node"] in both and (r["p_sign_flip_heldout"] or 1) > 0.05:
            weak.append(f"the {'ablation' if r['mode'] == 'ablate' else 'steering'} of the node '{RC.node_label(r['node'])}' "
                        f"({r['mean_d_heldout']:.2f} nats, p {r['p_sign_flip_heldout']:.2f})")
    weak396 = ("On the 10 held-out prompts every node that passes both tests keeps a held-out effect of the same sign "
               "with sign-flip p at most 0.003, except " + "; ".join(weak) + ".") if weak else \
        "On the 10 held-out prompts every node that passes both tests keeps a held-out effect of the same sign."
    ctx = {"weak396": weak396, "rec395": rec["0a"]["rec395"], "rec396": rec["0a"]["rec396"], "code_quotes": rec["0a"]["code_quotes"],
           "bands_line": rec["0a"]["bands"]["line"], "positioning_section": pos["section"], "new_refs": pos["new_refs"],
           "markers": SX.marker_edits(markers), "alias_paragraph": at["paragraph"], "alias_short": at["short"],
           "alias_value_names": at["value_names"], "z_printed": at["printed"]}
    edits = edits_spec.build(report, led.p, z, ctx)
    for e in edits:
        for v in e["values"]:
            if v not in led.by:
                raise KeyError(f"{e['id']} cites unknown value {v}")
    corrected, app = AL.apply_edits(report, edits)
    lint_before = AL.lint_report(report)
    lint_after = AL.lint_report(corrected) if app["apply_test_pass"] else {"n_unallowed": None}
    logger.info(f"apply_test_pass={app['apply_test_pass']} n_edits={app['n_edits']} problems={app['problems'][:5]}")
    logger.info(f"lint before {lint_before['by_pattern']} unallowed {lint_before['n_unallowed']}; after unallowed "
                f"{lint_after.get('n_unallowed')} {lint_after.get('unallowed_by_pattern')}")
    if app["apply_test_pass"]:
        (ROOT / "report_corrected.md").write_text(corrected)
        (ROOT / "report.diff").write_text(AL.unified_diff(report, corrected))
    occ = RC.classify_29of30(report)
    occ_after = RC.classify_29of30(corrected)
    with (TABLES / "occurrences_29of30.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["when", "line", "class", "context"])
        w.writeheader()
        w.writerows([{"when": "before", **o} for o in occ] + [{"when": "after", **o} for o in occ_after])
    with (TABLES / "lint_hits.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["when", "pattern", "line", "section", "iteration8_text", "allow_reason",
                                          "snippet"])
        w.writeheader()
        for when, L in (("before", lint_before), ("after", lint_after)):
            for h in L.get("unallowed", []) + L.get("allowlisted", []):
                w.writerow({"when": when, **{k: h.get(k) for k in w.fieldnames if k != "when"}})
    (ROOT / "lint_allowlist.json").write_text(json.dumps(
        {"rule": "hits in pre-iteration-8 text or in the iteration-8 prediction statements of 8.1 are allowlisted with a "
                 "reason; every other hit must be gone", "before": lint_before["allowlisted"],
         "after": lint_after.get("allowlisted", [])}, indent=1))
    with (TABLES / "ledger.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(led.rows[0].keys()))
        w.writeheader()
        w.writerows(led.rows)
    fm = [{k: m[k] for k in ("id", "art", "files", "section", "fields", "caption", "sha256", "n_fields", "code")}
          for m in markers]
    (ROOT / "figure_markers.json").write_text(json.dumps(fm, indent=1))
    return {"edits": edits, "apply": app, "lint_before": lint_before, "lint_after": lint_after, "positioning": pos,
            "markers": markers, "alias_text": at, "occ": occ, "occ_after": occ_after, "corrected": corrected}


CHECKLIST = {
    "0a": ("MUST-FIX", "Circuit shape and the unapplied held-out arm", "tables/circuit_heldout.csv; results/s0_core.json#0a"),
    "0b": ("MUST-FIX", "Qwen3-8B fork NO HANDLE under the committed rule", "art_e-_q5mSJGrSb:results/analysis.json#verdicts"),
    "0c": ("MUST-FIX", "Entropy superlative and temperature-law scope", "tables/entropy_scope.csv; tables/law_scope.csv"),
    "0d": ("MUST-FIX", "Iteration-8 positioning table", "tables/positioning_rows.csv; audit/web/"),
    "0e": ("MUST-FIX", "Alias-named manifold", "results/s0e.json; tables/alias_stats.csv; figures/alias_overlap.png"),
    "0f": ("minor", "Gemma comparators", "tables/gemma_arms.csv"),
    "0g": ("minor", "Missing figure markers", "figure_markers.json"),
}


def write_corrections(led: RC.Ledger, ed: dict[str, Any], man: dict[str, Any]) -> dict[str, Any]:
    edits = ed["edits"]
    vb = Counter(r["status"] for r in led.rows)
    for s in ("MATCH", "CORRECTED", "NEW", "CARRIED"):
        vb.setdefault(s, 0)
    items = {}
    for it in CHECKLIST:
        ids = [e["id"] for e in edits if e["item"] == it]
        items[it] = {"severity": CHECKLIST[it][0], "item": CHECKLIST[it][1], "edit_ids": ids,
                     "status": "ANSWERED" if ids and ed["apply"]["apply_test_pass"] else "OPEN",
                     "evidence": CHECKLIST[it][2]}
    corr = {"read_date": dt.date.today().isoformat(), "report_sha256": man["report:inputs/report/current_report.md"]["sha256"],
            "schema": "S0 corrections v1 (rebuilt from the plan: edits[] id/item/section/line_hint/old_text/new_text/"
                      "rationale/values; values[] name/recorded/recomputed/status/tolerance/source)",
            "n_edits": len(edits), "n_values": len(led.rows), "values_by_status": dict(vb),
            "n_edits_by_item": dict(Counter(e["item"] for e in edits)),
            "apply": {"apply_test_pass": ed["apply"]["apply_test_pass"], "n_edits": ed["apply"]["n_edits"],
                      "problems": ed["apply"]["problems"], "lint_before": ed["lint_before"]["n_unallowed"],
                      "lint_before_total_hits": ed["lint_before"]["n_hits"],
                      "lint_after": ed["lint_after"].get("n_unallowed"),
                      "lint_before_by_pattern": ed["lint_before"]["by_pattern"],
                      "lint_after_by_pattern": ed["lint_after"].get("by_pattern")},
            "item_checklist": items,
            "edits": [{**{k: e[k] for k in ("id", "item", "section")},
                       "line_hint": ed["apply"].get("line_of_edit", {}).get(e["id"]),
                       **{k: e[k] for k in ("old_text", "new_text", "rationale")},
                       "values": [led.by[v] for v in e["values"]]} for e in edits],
            "values": led.rows}
    (ROOT / "corrections.json").write_text(json.dumps(corr, indent=1, default=str))
    (ROOT / "apply_test.json").write_text(json.dumps(corr["apply"], indent=1))
    return corr


def ex(inp: str, out: str, **kw: Any) -> dict[str, Any]:
    d = {"input": inp, "output": out}
    if not any(k.startswith("predict_") for k in kw):
        d["predict_s0"] = out
    for k, v in kw.items():
        if k.startswith("eval_"):
            if v is None or (isinstance(v, float) and v != v):
                continue                      # not available (e.g. an arm that was not run): omit, never NaN
            d[k] = float(v)
        elif k.startswith("predict_"):
            d[k] = str(v)
        else:
            d[f"metadata_{k}"] = v
    return d


def write_eval_out(led: RC.Ledger, rec: dict[str, Any], z: dict[str, Any], ed: dict[str, Any], corr: dict[str, Any],
                   audit: dict[str, Any] | None) -> dict[str, Any]:
    k15, k10 = z["per_k"]["k15"], z["per_k"]["k10"]
    st = k15["stratified_secondary"]
    c5 = k15["five_centroid_primary"]
    a0 = rec["0a"]
    vb = corr["values_by_status"]
    metrics = {
        "items_answered": sum(1 for v in corr["item_checklist"].values() if v["status"] == "ANSWERED"),
        "items_total": len(CHECKLIST), "n_edits": corr["n_edits"], "apply_test_pass": int(corr["apply"]["apply_test_pass"]),
        "lint_before_unallowed": ed["lint_before"]["n_unallowed"], "lint_before_total": ed["lint_before"]["n_hits"],
        "lint_after_unallowed": ed["lint_after"].get("n_unallowed") or 0,
        "values_total": corr["n_values"], "values_match": vb["MATCH"], "values_corrected": vb["CORRECTED"],
        "values_new": vb["NEW"], "values_carried": vb["CARRIED"],
        "circuit_identity_check_pass": int(a0["identity_check_pass"]),
        "circuit_n_exact_zero_heldout_nodes": a0["n_exact_zero_heldout_nodes"],
        "circuit_cond_span_matches_heldout": a0["cond_span_matches_heldout"]["n_heldout_with_any_match"],
        "circuit_L0_pair_mean_ablate": led.by["0a.L0.abl.pair"]["recomputed"],
        "circuit_L0_pair_mean_steer": led.by["0a.L0.ste.pair"]["recomputed"],
        "circuit_natural_heldout_ablate": led.by["0a.nat.abl.heldout"]["recomputed"],
        "circuit_natural_heldout_p": led.by["0a.nat.abl.p_heldout"]["recomputed"],
        "das_T10_bfs_written": led.by["0b.bfs.written"]["recomputed"],
        "das_T10_bfs_correct": led.by["0b.bfs.correct"]["recomputed"],
        "das_T10_bfs_mcnemar_p": led.by["0b.bfs.mc_p"]["recomputed"],
        "das_n_29of30_occurrences": len(ed["occ"]),
        "entropy_n_twin_samples_above_q90": led.by["0c.n_total"]["recomputed"],
        "law_units_pass": led.by["0c.law.n_pass"]["recomputed"], "law_sign_test_p_vs_flat": led.by["0c.law.sign_p"]["recomputed"],
        "positioning_rows": len(ed["positioning"]["rows"]),
        "positioning_live_verified": ed["positioning"]["status_counts"].get("VERIFIED", 0),
        "positioning_live_verified_abstract": ed["positioning"]["status_counts"].get("VERIFIED-ABSTRACT", 0),
        "positioning_live_not_found": ed["positioning"]["status_counts"].get("NOT-FOUND", 0),
        "n_venue_or_version_corrections": ed["positioning"]["n_venue_or_version_corrections"],
        "alias_gate_E1": int(z["gates"]["E1_labels_equal"]), "alias_gate_E2": int(z["gates"]["E2_multiset_equal_forced_set"]),
        "alias_gate_E3": int(z["gates"]["E3_g_matches_M1"]),
        **({"alias_gate_E4_spearman": z["gates"]["E4_spearman_vs_stored_k15"]}
           if z["gates"].get("E4_spearman_vs_stored_k15") is not None else {}),
        "alias_rho_k15": k15["rho_primary"], "alias_p_k15": k15["primary_p_lower"],
        "alias_rho_k15_ci_low": k15["ci95_primary"][0], "alias_rho_k15_ci_high": k15["ci95_primary"][1],
        "alias_rho_k10": k10["rho_primary"], "alias_p_k10": k10["primary_p_lower"],
        "alias_rho_k15_secondary": k15["rho_secondary"], "alias_p_k15_secondary": k15["secondary_p_lower"],
        "alias_rho_5centroid": c5["rho"], "alias_p_5centroid": c5["p_lower"], "alias_5centroid_floor": c5["floor_lower"],
        "alias_stratified_stat": st["stat"], "alias_stratified_p": st["p_lower"], "alias_fe_beta": st["beta"],
        "alias_fe_beta_p_two_sided": st["beta_p_two_sided"],
        "alias_placebo_P1_reject_rate": z["placebos"]["P1_shuffled_alias_labels"]["share_p_lt_0.05"],
        "alias_placebo_P2_reject_rate": z["placebos"]["P2_random_overlap_vector"]["share_p_lt_0.05"],
        "alias_placebo_P3_mean": z["placebos"]["P3_within_algorithm_shuffles"]["stat_mean"],
        "alias_planted_control_pass": int(z["placebos"]["C1_planted"]["seed0_succeeds"]),
        **({"alias_bpe_rho_k15": led.by["0e.k15.bpe_rho"]["recomputed"],
            "alias_bpe_stratified_k15": led.by["0e.k15.bpe_strat"]["recomputed"],
            "alias_bpe_stratified_p_k15": led.by["0e.k15.bpe_strat_p"]["recomputed"],
            "alias_bpe_stratified_p_k10": led.by["0e.k10.bpe_strat_p"]["recomputed"]} if "0e.k15.bpe_rho" in led.by else {}),
        "alias_verdict_confounded": int(z["verdict"]["code"] == "CONFOUNDED"),
        "gemma_families_twin_fallback": sum(1 for v in rec["0f"]["family_status_G"].values() if v["status"] != "run arm"),
        "figure_markers_added": sum(1 for m in ed["markers"] if m["id"] != "fig_alias_overlap"),
        "figure_caption_fields_complete": sum(1 for m in ed["markers"] if m["n_fields"] == 6),
    }
    if audit:
        metrics.update({"audit_n_checks": audit["n_checks"], "audit_n_mismatches": audit["n_mismatches"],
                        "audit_placebos_failed": audit["placebos_failed"]})
        if "headline_all_match" in audit:
            metrics.update({"audit_raw_headlines_all_match": int(audit["headline_all_match"]),
                            "audit_raw_headline_placebos_failed": audit["headline_placebos_failed"]})
    metrics = {k: (float(v) if isinstance(v, float) else int(v)) for k, v in metrics.items()}
    ds = []
    ds.append({"dataset": "corrections", "examples": [
        ex(f"{r['name']} <- {r['source']}", str(r["printed"]), item=r["item"], status=r["status"], recorded=r["recorded"],
           recomputed=r["recomputed"] if not isinstance(r["recomputed"], float) else round(r["recomputed"], 12),
           tolerance=r["tolerance"], predict_recorded=str(r["recorded"]), predict_recomputed=str(r["printed"]),
           eval_match=1.0 if r["status"] == "MATCH" else 0.0) for r in led.rows]})
    ds.append({"dataset": "report_edits", "examples": [
        ex(e["old_text"], e["new_text"], id=e["id"], item=e["item"], section=e["section"], rationale=e["rationale"],
           line_hint=ed["apply"].get("line_of_edit", {}).get(e["id"]), values=e["values"],
           eval_n_values=len(e["values"]), eval_old_text_unique=float(ed["corrected"].count(e["old_text"]) == 0 or
                                                                       e["old_text"] in e["new_text"]))
        for e in ed["edits"]]})
    ds.append({"dataset": "circuit_heldout", "examples": [
        ex(f"{r['contrast']} {r['mode']} {r['node']}", f"held-out mean {r['mean_d_heldout']:.4f}",
           label=r["label"], n=r["n"], n_heldout=r["n_heldout"], eval_mean_d=r["mean_d"],
           eval_mean_d_pair_prompts=r["mean_d_pair_prompts"], eval_mean_d_heldout=r["mean_d_heldout"],
           eval_p_sign_flip_heldout=r["p_sign_flip_heldout"], eval_p_holm_20=r["p_holm_20"],
           eval_identity_pass=float(r["identity_pass"]), eval_n_exact_zero_heldout=r["n_exact_zero_heldout_entries"])
        for r in a0["table_rows"]]})
    ds.append({"dataset": "occurrences_29of30", "examples": [
        ex(o["context"], o["class"], line=o["line"], when="before", eval_das_fork=float(o["class"].startswith("DAS-fork")))
        for o in ed["occ"]] + [
        ex(o["context"], o["class"], line=o["line"], when="after", eval_das_fork=float(o["class"].startswith("DAS-fork")))
        for o in ed["occ_after"]]})
    ds.append({"dataset": "entropy_scope", "examples": [
        ex(f"{r['unit']} ({r['task']})", f"{r['argmax_entropy_hits_first64']} of {r['n_twin_reaching_fork']}",
           eval_share_above_q90=r["share_above_q90"], eval_q90_nats=r["q90_nats"],
           eval_argmax_hits=r["argmax_entropy_hits_first64"], eval_n=r["n_twin_reaching_fork"],
           eval_median_fork_entropy=r["median_fork_entropy_nats"]) for r in rec["0c"]["entropy_rows"]] + [
        ex(f"law {r['unit']}", f"law {r['law']:.3f}", eval_law_mae=r["law"], eval_flat_mae=r["flat_B0"],
           eval_tempering_mae=r["tempering_B1"], eval_H_bits=r["H_bits"], eval_pass=float(r["pass"]))
        for r in rec["0c"]["law_rows"]]})
    ds.append({"dataset": "positioning_rows", "examples": [
        ex(f"{r['claim']} | {r['neighbour']}", r["verdict"] or "n/a", status=r["status"], venue=r["venue_track"],
           url=r["url"], quote=r["quote"], adds=r["adds"], source=r["source"],
           eval_live_verified=float(r["status"] == "VERIFIED")) for r in ed["positioning"]["rows"]]})
    order = [(a, j) for a in AG.NONBANNED for j in range(3)]
    rows = z["overlap_rows"]
    ds.append({"dataset": "alias_overlap", "examples": [
        ex(f"{a} alias {j}: {r['alias']}", f"g_k15 {k15['g_alias'][f'{a}|{j}']:.3f}", detectors=r["detectors"],
           eval_primary_overlap=r["primary"], eval_secondary_overlap=r["secondary"],
           eval_g_k15=k15["g_alias"][f"{a}|{j}"], eval_g_k10=k10["g_alias"][f"{a}|{j}"]) for (a, j), r in zip(order, rows)]
        + [ex(f"{a} (algorithm centroid)", f"g_k15 {k15['g_algorithm'][a]:.3f}", eval_g_k15=k15["g_algorithm"][a],
              eval_g_k10=k10["g_algorithm"][a]) for a in AG.NONBANNED]})
    gam = []
    with (TABLES / "gemma_arms.csv").open() as f:
        for r in csv.DictReader(f):
            gam.append(ex(f"{r['unit']} {r['arm']} ({r['arm_name']})", "present" if r["present"] == "True" else "not run",
                          eval_present=float(r["present"] == "True"),
                          eval_pass_cost=float(r["pass_cost"]) if r["pass_cost"] not in ("", "None") else float("nan")))
    ds.append({"dataset": "gemma_arms", "examples": gam})
    ds.append({"dataset": "figure_markers", "examples": [
        ex(m["id"], m["caption"], art=m["art"], files=m["files"], sha256=m["sha256"], eval_n_fields=m["n_fields"])
        for m in ed["markers"]]})
    lh = []
    for when, L in (("before", ed["lint_before"]), ("after", ed["lint_after"])):
        for h in L.get("unallowed", []) + L.get("allowlisted", []):
            lh.append(ex(h["snippet"], h["pattern"], when=when, line=h["line"], section=h["section"],
                         allow_reason=h.get("allow_reason"), eval_unallowed=float(h.get("allow_reason") is None)))
    if not lh:
        lh.append(ex("no hits", "none", when="after"))
    ds.append({"dataset": "lint_hits", "examples": lh})
    sections = {}
    for it in CHECKLIST:
        sections[it] = {"edits": corr["item_checklist"][it]["edit_ids"],
                        "values": [r["name"] for r in led.rows if r["item"] == it],
                        "verdict": corr["item_checklist"][it]["status"]}
    sections["0a"]["metrics"] = {k: a0[k] for k in ("identity_check_pass", "n_exact_zero_heldout_nodes",
                                                     "cond_span_matches_heldout", "replication", "cause_evidence",
                                                     "code_quotes", "C2a_top10_has_COND", "bands", "zero_heldout")}
    sections["0b"]["metrics"] = rec["0b"] | {"occurrences_by_class_before": dict(Counter(o["class"] for o in ed["occ"]))}
    sections["0c"]["metrics"] = {"entropy_rows": rec["0c"]["entropy_rows"], "law_rows": rec["0c"]["law_rows"]}
    sections["0d"]["metrics"] = {"status_counts": ed["positioning"]["status_counts"],
                                 "n_venue_or_version_corrections": ed["positioning"]["n_venue_or_version_corrections"],
                                 "live": ed["positioning"]["live"], "n_carried_rows": ed["positioning"]["carried_n"]}
    sections["0e"]["metrics"] = {k: z[k] for k in ("gates", "verdict", "placebos", "null_sizes", "flags")} | {
        "per_k": {k: {kk: vv for kk, vv in v.items() if kk not in ("g_alias",)} for k, v in z["per_k"].items()}}
    sections["0e"]["verdict"] = z["verdict"]["sentence"]
    sections["0f"]["metrics"] = rec["0f"]
    sections["0g"]["metrics"] = {"markers": [{k: m[k] for k in ("id", "art", "files", "n_fields", "sha256")}
                                             for m in ed["markers"]]}
    flags = []
    if vb["CORRECTED"]:
        flags.append("direction_number_not_reproduced")
    meta = {"evaluation_name": "Iteration-9 Step 0: repair of the iteration-8 research record",
            "plan_id": "gen_plan_evaluation_1_idx1", "utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "report_sha256": corr["report_sha256"], "sections": sections, "flags": flags,
            "outputs": ["corrections.json", "report_corrected.md", "report.diff", "apply_test.json", "lint_allowlist.json",
                        "tables/*.csv", "figures/alias_overlap.(pdf|png)", "figure_markers.json",
                        "predictions/commit_s0e.json", "commitments.log", "audit/rederive.py"]}
    out = {"metadata": meta, "metrics_agg": metrics, "datasets": ds}
    json.dumps(out, allow_nan=False, default=str)        # raises if any NaN or infinity slipped in
    (ROOT / "eval_out.json").write_text(json.dumps(out, indent=1, default=str))
    (ROOT / "full_eval_out.json").write_text(json.dumps(out, indent=1, default=str))

    def trunc(x: Any) -> Any:
        if isinstance(x, str):
            return x[:200]
        if isinstance(x, list):
            return [trunc(v) for v in x]
        if isinstance(x, dict):
            return {k: trunc(v) for k, v in x.items()}
        return x

    mini = {"metadata": {k: v for k, v in meta.items() if k != "sections"} | {"sections_note": "see full_eval_out.json"},
            "metrics_agg": metrics, "datasets": [{"dataset": d["dataset"], "examples": d["examples"][:3]} for d in ds]}
    (ROOT / "mini_eval_out.json").write_text(json.dumps(mini, indent=1, default=str))
    (ROOT / "preview_eval_out.json").write_text(json.dumps(trunc(mini), indent=1, default=str))
    return out


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", default="all")
    args = ap.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (24 * 1024 ** 3, 24 * 1024 ** 3))
    for d in (RESULTS, TABLES, ROOT / "figures"):
        d.mkdir(exist_ok=True)
    t0 = time.time()
    man = stage_setup()
    if args.stages in ("all", "0e") or not (RESULTS / "s0e.json").exists():
        z = stage_0e()
    else:
        z = json.loads((RESULTS / "s0e.json").read_text())
    if args.stages == "0e":
        return
    import os
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    tz = tertiary_bpe.main()
    led = RC.Ledger()
    rec = stage_ledger(led)
    ed = stage_edits(led, rec, z, tz)
    corr = write_corrections(led, ed, man)
    import subprocess
    pr = subprocess.run([sys.executable, "-I", str(ROOT / "audit/rederive.py")], capture_output=True, text=True,
                        timeout=1800)
    logger.info(f"audit/rederive.py exit {pr.returncode}: {pr.stdout.strip()[:300]}")
    if pr.returncode != 0:
        logger.error(f"audit failed: {pr.stderr[-2000:]}")
    audit = json.loads((ROOT / "audit/rederive_result.json").read_text()) if (ROOT / "audit/rederive_result.json").exists() else None
    ph = subprocess.run([sys.executable, "-I", str(ROOT / "audit/headline_rederive.py")], capture_output=True, text=True,
                        timeout=1800)
    logger.info(f"audit/headline_rederive.py exit {ph.returncode}")
    hl = json.loads((ROOT / "audit/headline_rederive.json").read_text()) if ph.returncode == 0 else None
    if audit is not None and hl is not None:
        audit = audit | {"headline_all_match": hl["all_headlines_match"], "headline_placebos_failed": hl["placebos_failed_as_required"]}
    (RESULTS / "s0_core.json").write_text(json.dumps({"0a": {k: v for k, v in rec["0a"].items() if k != "table_rows"},
                                                      "0b": rec["0b"], "0c": rec["0c"], "0f": rec["0f"]}, indent=1,
                                                     default=str))
    write_eval_out(led, rec, z, ed, corr, audit)
    after = {k: sha(p) for k, p in input_files()}
    changed = [k for k, v in after.items() if v != man[k]["sha256"]]
    assert not changed, f"inputs changed during the run: {changed}"
    logger.info(f"done in {time.time() - t0:.0f} s; edits {corr['n_edits']}, values {corr['values_by_status']}, "
                f"lint {corr['apply']['lint_before']} -> {corr['apply']['lint_after']}; inputs unchanged")


if __name__ == "__main__":
    main()
