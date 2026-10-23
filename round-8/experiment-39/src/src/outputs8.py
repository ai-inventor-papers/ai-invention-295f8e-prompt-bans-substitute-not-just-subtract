#!/usr/bin/env python3
"""Stage 7: method_out.json (exp_gen_sol_out). Datasets:
  k1_cells       one example per (unit, slot): input = unit/template/slot description, output = the twin's
                 'label|pass', predict_<arm> = 'label|pass' for every arm run on that slot
  k1_tokenmap    one example per (unit, node, mapped token): output = class counts of its K continuations
  k1_locator     one example per (unit, base path): output = located decision indices
  hr_branches    one example per (unit, node, token) with HR or map continuations: output = idea counts
  novelty_audit  one example per distinct correct 'other' program
Every analysis result goes in metadata.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg8 import (CACHE_DIR, CONT_LABELS, CONTS, PRED_DIR, RESULTS_DIR, ROOT, TEMPLATES, UNITS, read_json,  # noqa
                  read_jsonl, slot_template, slot_ukey, utc_now, write_json)
import analysis_k1 as AK  # noqa: E402


def opt(p: Path):
    return read_json(p) if p.exists() else None


def main() -> None:
    adj = opt(RESULTS_DIR / "adjudicated_labels.json")
    data = AK.load_rows(adj)
    c1 = read_json(PRED_DIR / "commit1_dose_table.json")
    ds_cells = []
    for unit in sorted(data):
        arms = data[unit]
        if "A0" not in arms:
            continue
        for s in range(50):
            tw = arms["A0"].get(s)
            if tw is None:
                continue
            ex = {"input": f"unit {unit} ({UNITS[unit]['task']}, model {UNITS[unit]['model']}); prompt template "
                           f"{slot_template(s)}; CRN slot {s} (stream key {list(slot_ukey(unit, s))})",
                  "output": f"{tw['cls']}|{'pass' if tw['passed'] else 'fail'}",
                  "metadata_unit": unit, "metadata_slot": s, "metadata_template": slot_template(s),
                  "metadata_role": (c1["units"].get(unit) or {}).get("role", UNITS[unit]["role"]),
                  "metadata_twin_decision_token": tw.get("decision_token_str"),
                  "metadata_twin_decision_pos": tw.get("decision_pos"),
                  "metadata_twin_decision_H1": tw.get("decision_H1")}
            for a, rows in sorted(arms.items()):
                r = rows.get(s)
                if r is None or a == "A0":
                    continue
                ex[f"predict_{a}"] = f"{r['cls']}|{'pass' if r['passed'] else 'fail'}"
                ex[f"metadata_{a}_decision_token"] = r.get("decision_token_str")
            ds_cells.append(ex)
    # token maps
    ds_map = []
    for u, e in c1["units"].items():
        maps = dict(e.get("token_map") or {})
        if e.get("token_map_n11"):
            maps["n11"] = e["token_map_n11"]
        for nd, tm in maps.items():
            info = opt(CACHE_DIR / "nodes" / f"{u}_{nd}.json") or {}
            for t, m in tm.items():
                ds_map.append({"input": f"unit {u}, decision node {nd} (index {info.get('pos')}), forced token "
                                        f"{json.dumps((info.get('map_token_str') or {}).get(t, '?'))} (id {t})",
                               "output": json.dumps(m["counts"]), "predict_committal_class": str(m["committal"]),
                               "predict_pfail": f"{m['pfail']:.2f}", "metadata_unit": u, "metadata_node": nd,
                               "metadata_token_id": int(t), "metadata_committal": m["committal"],
                               "metadata_pfail": m["pfail"], "metadata_n": m["n"],
                               "metadata_T1_mass_template_avg": (info.get("pooled_p20") or {}).get(t)})
    # locator
    loc = opt(RESULTS_DIR / "locator.json")
    ds_loc = []
    for u, v in (loc or {}).get("units", {}).items():
        for p, x in v["paths"].items():
            ds_loc.append({"input": f"unit {u}, twin base path slot {p} ({x['own_class']}), prefixes {x['js'][0]}.."
                                    f"{x['js'][-1]} step 2, 8 continuations each",
                           "output": json.dumps(x["located_index"]),
                           "predict_within_1_of_known": str(x["within_1_of_known"]), "metadata_unit": u,
                           "metadata_path": int(p),
                           "metadata_within_1_of_known": x["within_1_of_known"],
                           "metadata_perm_p": x["perm"]["p_perm"], "metadata_known": v["known_indices"]})
    # HR branches
    labels = {r["sid"]: r for r in read_jsonl(CONT_LABELS)}
    agg = defaultdict(list)
    for r in read_jsonl(CONTS):
        if r.get("arm") == "HR" or (r.get("arm") == "MAP" and r.get("k", 9) < 5):
            L = labels.get(r["sid"])
            if L:
                agg[(r["unit"], r["node"], int(r["token"]), r.get("rank"))].append(
                    (AK.cls(r["unit"], L.get("label")), bool(L.get("passed"))))
    ds_hr = [{"input": f"unit {u}, node {nd}, forced token id {t}" + (f" (rank {rk})" if rk else " (map token)"),
              "output": json.dumps(dict(Counter(c for c, _ in v))),
              "predict_correct_ideas": json.dumps(dict(Counter(c for c, ok in v if ok))), "metadata_unit": u,
              "metadata_node": nd,
              "metadata_token_id": t, "metadata_rank": rk, "metadata_n_correct": sum(ok for _, ok in v),
              "metadata_correct_ideas": json.dumps(dict(Counter(c for c, ok in v if ok)))}
             for (u, nd, t, rk), v in sorted(agg.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][3] or 0))]
    nov = opt(RESULTS_DIR / "novelty_audit.json")
    ds_nov = [{"input": f"unit {it['unit']}, correct program labelled 'other' ({it['label']}), arm {it['arm']}:\n"
                        + (it.get("code") or "")[:3000],
               "output": str(it.get("final_class")),
               **{f"predict_judge_{i + 1}": str((j or {}).get("class")) for i, j in enumerate(it["judges"])},
               "predict_manual_read": str((it.get("manual_read") or {}).get("class")),
               "metadata_unit": it["unit"], "metadata_sids": it["sids"],
               "metadata_judges": json.dumps(it["judges"])[:2000], "metadata_manual_read": json.dumps(
                   it.get("manual_read")), "metadata_nearest": json.dumps(it["nearest"])[:2000]}
              for it in (nov or {}).get("items", [])]
    meta = {"method_name": "Temperature at one deciding token (iteration 8, claims K1 and HR)", "utc": utc_now(),
            "description": "Temperature applied only at located decision tokens of bf16 Qwen3-8B and Gemma-3-4b-it "
                           "code generation, against global temperature, min-p, EDT- and AdapT-style temperature, "
                           "same-dose placebos and class-uniform forcing, with committed predictions.",
            "k1_verdict": opt(RESULTS_DIR / "k1_verdict.json"), "hr": opt(RESULTS_DIR / "hr.json"),
            "commit1_dose_table_summary": {u: {k: e.get(k) for k in ("role", "dose", "q90", "classes")}
                                           for u, e in c1["units"].items()},
            "locator": {u: {k: v[k] for k in ("n_paths_ok", "n_paths_eligible", "success", "cost_continuations")}
                        for u, v in (loc or {}).get("units", {}).items()},
            "novelty_audit_summary": {k: v for k, v in (nov or {}).items() if k != "items"},
            "tests_cpu": opt(RESULTS_DIR / "tests_cpu.json"), "tests_gpu": opt(RESULTS_DIR / "tests_gpu.json"),
            "engine_check": opt(RESULTS_DIR / "stage0.json"), "geometry_f8": opt(RESULTS_DIR / "geometry_f8.json"),
            "positioning": opt(RESULTS_DIR / "positioning.json"), "deviations": opt(RESULTS_DIR / "deviations.json"),
            "costs": opt(RESULTS_DIR / "costs.json"), "commit_chain": opt(RESULTS_DIR / "commit_chain.json"),
            "amendment_commit3": opt(RESULTS_DIR / "amendment.json"), "adjudication_summary": {
                k: v for k, v in (opt(RESULTS_DIR / "adjudication.json") or {}).items() if k != "items"},
            "rederive": {k: v for k, v in (opt(RESULTS_DIR / "rederive.json") or {}).items() if k != "cells"},
            "rederive_tests": opt(RESULTS_DIR / "rederive_tests.json")}
    datasets = [d for d in ({"dataset": "k1_cells", "examples": ds_cells},
                            {"dataset": "k1_tokenmap", "examples": ds_map},
                            {"dataset": "k1_locator", "examples": ds_loc},
                            {"dataset": "hr_branches", "examples": ds_hr},
                            {"dataset": "novelty_audit", "examples": ds_nov}) if d["examples"]]
    out = {"metadata": meta, "datasets": datasets}
    (ROOT / "method_out.json").write_text(json.dumps(out, indent=1, default=str))
    print({d["dataset"]: len(d["examples"]) for d in datasets})


if __name__ == "__main__":
    main()
