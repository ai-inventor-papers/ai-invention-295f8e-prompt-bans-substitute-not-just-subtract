#!/usr/bin/env python3
"""Stage 12: data/points.jsonl, data/placements.jsonl, results/n4_verdict.json (P1-P8, named outcome) and
method_out.json (exp_gen_sol_out: tpg_points, tpg_placements, tpg_naming + metadata)."""

from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np
from loguru import logger

import prompts_tp
from common import (CANON_ORDER, read_json, read_jsonl, sha256_file, utc_now, verify_chain, write_json, write_jsonl)
from tpg import B5, DATA, K_SECOND, K_VERDICT, MODELS, NB5, PRED, RESULTS, ROOT, STATES_DIR, UDIJ

STATEMENT = ("The geometry is correlational: it describes where representations and survivors sit, not whether the "
             "model uses this geometry to choose an algorithm (iteration 7's in-manifold pushes moved 0/300).")


def _get(d: dict[str, Any], *ks: str, default: Any = None) -> Any:
    for k in ks:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d


def _verdict(geo: dict[str, Any], key: str, k: int) -> str | None:
    r = geo.get(key)
    if not r:
        return None
    return _get(r, "L_star", "landing", f"k{k}", "pooled", "verdict")


def _cls(geo: dict[str, Any], key: str, k: int) -> str | None:
    r = geo.get(key)
    if not r:
        return None
    return _get(r, "L_star", "describe", f"k{k}", "classes", UDIJ)


def n4_verdict() -> dict[str, Any]:
    geo = read_json(RESULTS / "geometry_all.json")
    rep = read_json(RESULTS / "repro_mname_32b.json")
    lex = read_json(RESULTS / "lexical_regression.json")
    beh = read_json(RESULTS / "behavioural_distance.json")
    rsa = read_json(RESULTS / "rsa.json")
    pl = read_json(RESULTS / "placement.json") if (RESULTS / "placement.json").exists() else {}
    P: dict[str, Any] = {}
    gr = rep["G_repro"]
    P["P1"] = {"pass": gr["pass"], "spearman": gr["spearman_vs_geo_C6_nf4_k15_block31"],
               "classes_equal": gr["classes_new"] == gr["classes_e44"], "max_abs_g_diff": gr["max_abs_g_diff"],
               "spearman_k10": rep["by_k"]["10"]["spearman_class_geodesic"] if "10" in rep["by_k"] else None,
               "note": "fallback F1 (0.85 <= rho < 0.95): new states used for every manifold; cached-state verdict "
                       "(iteration 8: OPPOSITE) reported beside"}
    code_key, desc_key = "32b|mcode_PRIMARY_R1", "32b|mdesc"
    c2 = read_json(PRED / "commit2.json")
    if _get(c2, "F8", "32b", "verdict_readout") == "R2":
        code_key = "32b|mcode_PRIMARY_R2"
    v = {key: {f"k{k}": {"verdict": _verdict(geo, key, k), "udij_class": _cls(geo, key, k)} for k in (K_SECOND, K_VERDICT)}
         for key in ("32b|mname", "32b|mlex", desc_key, code_key, "32b|mcode_M32_R1", "32b|mcode_M8_R1",
                     "32b|mcode_PRIMARY_R2", "8b|mname", "8b|mlex", "8b|mdesc", "8b|mcode_PRIMARY_R1")}
    P["P2"] = {"pass": all(v[key][f"k{k}"]["udij_class"] == "EDGE" for key in (code_key, desc_key)
                           for k in (K_SECOND, K_VERDICT)) and
               all(v[key][f"k{K_VERDICT}"]["verdict"] == "EDGE" for key in (code_key, desc_key)),
               "mcode": v[code_key], "mdesc": v[desc_key]}
    P["P3"] = {"pass": all(v[key][f"k{k}"]["udij_class"] == "OPPOSITE" for key in ("32b|mname", "32b|mlex")
                           for k in (K_SECOND, K_VERDICT)), "mname": v["32b|mname"], "mlex": v["32b|mlex"]}
    lm = lex.get("32b|mname") or {}
    P["P4"] = {"pass": bool(lm.get("P4_pass")),
               "spearman_L1": {f"k{k}": _get(lm, f"k{k}", "spearman_L1") for k in (K_SECOND, K_VERDICT)},
               "perm_p_L1": {f"k{k}": _get(lm, f"k{k}", "perm_p_L1") for k in (K_SECOND, K_VERDICT)},
               "within_algorithm": {f"k{k}": _get(lm, f"k{k}", "within_algorithm") for k in (K_SECOND, K_VERDICT)}}
    P["P5"] = {"descriptive": lex.get("descriptive_mdesc_mcode")}
    P["P6"] = {"pass": beh["P6_udij_nearest_to_bfs"], "d_beh_to_bfs": beh["P6_d_beh_to_bfs"],
               "note": "anchor: unit-weight Dijkstra expands in BFS order on a unit grid by construction"}

    def rho(key: str, m: str) -> float | None:
        return _get(rsa, key, "models", m, "rho")

    P["P7"] = {"rho": {key: {m: rho(key, m) for m in ("R_lex", "R_beh", "R_surface", "R_len")}
                       for key in ("32b|mname", desc_key, code_key, "32b|mlex")},
               "pattern": {"name_lex_gt_beh": (rho("32b|mname", "R_lex") or -9) > (rho("32b|mname", "R_beh") or -9),
                           "code_beh_gt_lex": (rho(code_key, "R_beh") or -9) > (rho(code_key, "R_lex") or -9),
                           "desc_beh_gt_lex": (rho(desc_key, "R_beh") or -9) > (rho(desc_key, "R_lex") or -9)},
               "p_exact": {key: {m: _get(rsa, key, "models", m, "p_exact") for m in ("R_lex", "R_beh")}
                           for key in ("32b|mname", desc_key, code_key)}, "descriptive": True}
    plc = pl.get("32b|mcode_PRIMARY_R1", {})
    P["P8"] = {"pass": plc.get("P8_pass"), "G_place": plc.get("G_place"), "udij_survivors": plc.get("udij_survivors")}
    # secondary statistics
    sec = {}
    for key in ("32b|mname", "32b|mlex", desc_key, code_key, "32b|mcode_M32_R1", "8b|mname", "8b|mdesc",
                "8b|mcode_PRIMARY_R1"):
        r = geo.get(key)
        if not r:
            continue
        d = r["L_star"]["describe"]
        bs = _get(r, "L_star", "bootstrap", f"k{K_VERDICT}") or {}
        sec[key] = {"L_star": r["L_star"]["block"],
                    **{f"k{k}": {"udij_class": d[f"k{k}"]["classes"].get(UDIJ), "udij_rank": d[f"k{k}"]["udij_rank"],
                                 "udij_ratio": d[f"k{k}"]["udij_ratio"],
                                 "nearest_banned": d[f"k{k}"]["nearest_banned"].get(UDIJ),
                                 "classes": d[f"k{k}"]["classes"]} for k in (5, K_SECOND, K_VERDICT)},
                    "bootstrap_k15": {"udij_edge_probability": _get(bs, "edge_probability", UDIJ),
                                      "udij_class_stability": _get(bs, "class_stability", UDIJ),
                                      "udij_ratio_ci95": bs.get("udij_ratio_ci95"), "n_boot": bs.get("n_boot")},
                    "robustness_udij_class_counts": _get(r, "L_star", "robustness", "udij_class_counts"),
                    "crossnobis_udij_class": _get(r, "L_star", "crossnobis", "classes", UDIJ),
                    "zscored_udij_class": _get(r, "L_star", "zscored", "classes", UDIJ),
                    "euclid_centroid_udij_class": _get(d, "euclid_centroid", "classes", UDIJ),
                    "split_half_spearman_brown_k15": _get(r, "L_star", "split_half", f"k{K_VERDICT}",
                                                          "spearman_brown"),
                    "nonbanned_used": d["nonbanned_used"]}
    # named outcome
    mc15, md15 = v[code_key][f"k{K_VERDICT}"]["udij_class"], v[desc_key][f"k{K_VERDICT}"]["udij_class"]
    mc10, md10 = v[code_key][f"k{K_SECOND}"]["udij_class"], v[desc_key][f"k{K_SECOND}"]["udij_class"]
    m32 = v["32b|mcode_M32_R1"][f"k{K_VERDICT}"]["udij_class"]
    source = "ROBUST" if m32 == mc15 else ("SOURCE-SENSITIVE" if m32 else "M32 frame not available")
    k_sensitive = (mc15 != mc10) or (md15 != md10)
    if mc15 is None or md15 is None:
        outcome = "UNTESTABLE"
    elif P["P2"]["pass"] and P["P3"]["pass"] and P["P4"]["pass"] and P["P6"]["pass"]:
        outcome = "CONFIRMED"
    elif mc15 == "OPPOSITE" and md15 == "OPPOSITE" and not k_sensitive and source != "SOURCE-SENSITIVE":
        outcome = "ROBUST-OPPOSITE"
    elif mc15 != md15 or k_sensitive or source == "SOURCE-SENSITIVE":
        outcome = "MIXED"
    elif P["P3"]["pass"] and P["P4"]["pass"] and mc15 in ("MIDDLE",) and md15 in ("MIDDLE",):
        outcome = "NAMES-ONLY"
    else:
        outcome = "NONE OF THE NAMED OUTCOMES"
    out = {"utc": utc_now(), "predictions": P, "secondary_statistics": sec, "verdict_table": v,
           "mcode_source_robustness": source, "k_sensitive": k_sensitive,
           "mcode_class_k15": mc15, "mdesc_class_k15": md15, "named_outcome": outcome,
           "mcode_verdict_key": code_key, "statement": STATEMENT,
           "mdesc_excluded_algorithms": [a for a in NB5 if a not in _get(geo.get(desc_key, {}), "L_star", "describe",
                                                                          "nonbanned_used", default=[])]}
    write_json(RESULTS / "n4_verdict.json", out)
    logger.info(f"N4 outcome {outcome}: M-code {mc15}/{mc10}, M-desc {md15}/{md10}, M32 {m32}; "
                f"P1 {P['P1']['pass']} P2 {P['P2']['pass']} P3 {P['P3']['pass']} P4 {P['P4']['pass']} "
                f"P6 {P['P6']['pass']} P8 {P['P8']['pass']}")
    return out


def _nearest_by_geo(model_tag: str, name: str) -> dict[str, str]:
    f = STATES_DIR / f"geo_{model_tag}_{name}_k{K_VERDICT}.npz"
    if not f.exists():
        return {}
    z = np.load(f, allow_pickle=False)
    geo, labels, ids = z["geo"], z["labels"], z["point_ids"]
    out = {}
    algs = sorted(set(labels.tolist()))
    for i in range(len(ids)):
        mask = np.ones(len(ids), bool)
        mask[i] = False
        means = {a: float(geo[i, mask & (labels == a)].mean()) for a in algs if (mask & (labels == a)).any()}
        out[str(ids[i])] = min(means, key=means.get)
    return out


def stage_outputs(*args: str) -> None:
    verdict = n4_verdict()
    ms = read_json(DATA / "mcode_sets.json")
    by_uid = {}
    for name, s in ms["sets"].items():
        for a, rows in s.items():
            for r in rows:
                by_uid[r["uid"]] = r
    for r in ms["placement"]:
        by_uid[r["uid"]] = r
    forced = {f"mname|{p['algorithm']}|t{p['template']}|j{p['alias']}": p for p in prompts_tp.forced_set()}
    ml = {f"mlex|{r['algorithm']}|t{r['template']}|j{r['alias_index']}": r
          for r in read_json(DATA / "mlex_prompts.json")["rows"]}
    md = {f"mdesc|{r['desc_id']}|t{r['template']}": r for r in read_json(DATA / "mdesc_prompts.json")["rows"]}
    points = []
    examples = []
    for model_tag in ("32b", "8b"):
        for name in ("mname", "mdesc", "mlex", "mcode_PRIMARY_R1", "mcode_M32_R1"):
            nn = _nearest_by_geo(model_tag, name)
            for pid, pred in nn.items():
                if name == "mname":
                    p = forced[pid]
                    inp, lab, extra = p["prompt"], p["algorithm"], {"template": p["template"], "alias": p["alias"]}
                elif name == "mlex":
                    p = ml[pid]
                    inp, lab, extra = p["prompt"] + "\n[twin] " + p["twin"], p["algorithm"], {"template": p["template"]}
                elif name == "mdesc":
                    p = md[pid]
                    inp, lab, extra = p["prompt"], p["algorithm"], {"template": p["template"], "desc_id": p["desc_id"]}
                else:
                    p = by_uid[pid]
                    inp, lab, extra = p["scrubbed"], p["algorithm"], {"source": p["source"],
                                                                     "context_variant": p["context_variant"]}
                cfg = MODELS[model_tag]
                row = {"model": cfg["repo"], "engine": cfg["engine"], "provider": None, "task": "T1",
                       "arm": name, "condition": name, "k": K_VERDICT, "label": lab, "point_id": pid,
                       "predict_nearest": pred, **extra}
                if name.startswith("mcode"):
                    row.update({"ds_signature": p.get("ds_flags"), "lexical_flag": p.get("lexical_flag"),
                                "code_sha256": p.get("code_sha256"), "code": p.get("scrubbed"), "passed": True})
                points.append(row)
                if model_tag == "32b":
                    examples.append({"input": inp, "output": lab, f"predict_nearest_{name}": pred,
                                     "metadata_model": cfg["repo"], "metadata_manifold": name,
                                     "metadata_point_id": pid, "metadata_k": K_VERDICT})
    write_jsonl(DATA / "points.jsonl", points)
    pl = read_json(RESULTS / "placement.json") if (RESULTS / "placement.json").exists() else {}
    prow = []
    pex = []
    for key, r in pl.items():
        for row in r["rows"]:
            p = by_uid.get(row["uid"], {})
            prow.append({"model": key.split("|")[0], "frame": r["frame"], "block": r["block"], "k": r["k"],
                         "readout": r["readout"], **row, "code_sha256": p.get("code_sha256"),
                         "code": p.get("scrubbed"), "ds_signature": p.get("ds_flags"),
                         "lexical_flag": p.get("lexical_flag"), "G_place_pass": r["G_place"]["pass"]})
            if key == "32b|mcode_PRIMARY_R1":
                pex.append({"input": p.get("scrubbed") or "", "output": row["label"] if row["label"] != "other"
                            else f"other: {row.get('other_name')}",
                            "predict_nearest_mcode": row["nearest_algorithm"], "predict_class": row["class"],
                            "metadata_set": row["set"], "metadata_uid": row["uid"], "metadata_g_x": row["g_x"],
                            "metadata_nearest_banned": row["nearest_banned"]})
    write_jsonl(DATA / "placements.jsonl", prow)
    ng = read_json(RESULTS / "naming_gate.json")
    nex = []
    for r in ng["rows"]:
        for att in r["attempts"]:
            nex.append({"input": att["text"], "output": att["algorithm"],
                        "predict_qwen32b_modal": str(att["modal"]), "metadata_rate": att["rate"],
                        "metadata_passed": att["pass"], "metadata_slot": r["slot"], "metadata_version": att["version"]})
    ok, problems, entries = verify_chain()
    meta = {"method_name": "TP-G: ten-algorithm grid manifold with and without names (iteration 9)",
            "description": "Qwen3-32B nf4 (truncated decoder) and Qwen3-8B bf16 activation manifolds of 10 path-search "
                           "algorithms from alias prompts (M-name), name-free descriptions (M-desc), alias-minus-twin "
                           "deltas (M-lex) and name-scrubbed programs (M-code); landing of iteration 8's survivors; "
                           "lexical regression; RSA against lexical/behavioural/surface RDMs; per-program placement.",
            "n4_verdict": {k: verdict[k] for k in ("named_outcome", "mcode_class_k15", "mdesc_class_k15",
                                                   "mcode_source_robustness", "k_sensitive", "statement")},
            "predictions_pass": {p: verdict["predictions"][p].get("pass") for p in verdict["predictions"]},
            "secondary_statistics": verdict["secondary_statistics"],
            "commitments": {"chain_ok": ok, "problems": problems,
                            "entries": [{"label": e["label"], "utc": e["utc"], "payload": e["payload_path"]}
                                        for e in entries]},
            "deviations": read_json(RESULTS / "deviations.json") if (RESULTS / "deviations.json").exists() else [],
            "costs": read_json(RESULTS / "costs.json"),
            "timing": read_jsonl(RESULTS / "timing.jsonl"),
            "baselines": {"lexical_model_rdm": "R_lex", "surface_code_rdm": "R_surface", "length_rdm": "R_len",
                          "behavioural_rdm": "R_beh", "name_condition": "M-name (iteration 8 instrument)",
                          "nulls": "landing U/F/P/C; exact label-permutation Mantel"},
            "files": {p.name: sha256_file(p) for p in sorted(RESULTS.glob("*.json"))}}
    out = {"metadata": meta, "datasets": [
        {"dataset": "tpg_points", "examples": examples},
        {"dataset": "tpg_placements", "examples": pex or [{"input": "", "output": "none"}]},
        {"dataset": "tpg_naming", "examples": nex}]}
    write_json(ROOT / "method_out.json", out, indent=None)
    logger.info(f"method_out.json: {len(examples)} points, {len(pex)} placements, {len(nex)} namings; "
                f"chain ok {ok}")
    _ = (Counter, B5, CANON_ORDER)
