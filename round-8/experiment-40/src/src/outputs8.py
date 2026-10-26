#!/usr/bin/env python3
"""method_out.json (exp_gen_sol_out schema): one example per (unit, site, target class, slot) of the generation
cells (predict_<arm> = 'label|pass' or 'label|fail'), one per mediation clamp slot, and one per held-out teacher-forced
pair (predict_<fit> = Delta in nats). Metadata: verdicts, K2, controls, recovery tables, scan profiles, mediation,
deviations, timing, costs, commit chain.

Usage: python src/outputs8.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger

from cfg8 import (DATA, FAMILY, PRED, RESULTS, ROOT, model_path, read_json, read_jsonl, setup_logging, write_json)
from commit8 import verify

ARMS = ("BASE", "FULL", "DAS", "RAND", "PERM", "REV-DAS", "REV-FULL", "SRC", "DAS_k1", "DAS_k2", "DAS_k4", "DAS_k8")


def toks() -> dict[str, Any]:
    from transformers import AutoTokenizer
    out = {}
    for fam in ("qwen", "gemma"):
        f = FAMILY[fam]
        out[fam] = AutoTokenizer.from_pretrained(model_path(f["id"], f["rev"]))
    return out


def gen_examples(unit: str, site: str, T: Any, P: dict) -> list[dict[str, Any]]:
    cm = PRED / f"commit2_{unit}_{site}.json"
    if not cm.exists():
        return []
    c2 = read_json(cm)
    G = {r["sample_id"]: r for r in read_jsonl(DATA / f"labels_{unit}.jsonl")}
    ex = []
    for c, slots in c2["slot_map"].items():
        arms_n = {arm: n for (s_, arm, cc, n) in c2["cells"] if s_ == site and cc == c}
        for s, sm in enumerate(slots):
            b, src = sm["base"], sm["source"]
            row = {"input": (f"[{unit} | {site} site | target class {c} | slot {s}] BASE PROMPT: "
                             f"{T.decode(P[b]['ids'], skip_special_tokens=True)} || SOURCE PROMPT (edit source): "
                             f"{T.decode(P[src]['ids'], skip_special_tokens=True)}"),
                   "output": c, "metadata_unit": unit, "metadata_site": site, "metadata_target_class": c,
                   "metadata_slot": s, "metadata_base_key": b, "metadata_source_key": src}
            for arm, n in arms_n.items():
                if s >= n:
                    continue
                sid = f"{unit}|{site}|BASE|{b}|{s}" if arm == "BASE" else f"{unit}|{site}|{arm}|{c}|{s}"
                l = G.get(sid)
                if l is None:
                    continue
                key = "predict_" + arm.replace("-", "_")
                row[key] = f"{l['label']}|{'pass' if l.get('passed') else 'fail'}"
            ex.append(row)
    return ex


def med_examples() -> list[dict[str, Any]]:
    p = RESULTS / "mediation_T10.json"
    if not p.exists():
        return []
    med = read_json(p)
    G = {r["sample_id"]: r for r in read_jsonl(DATA / "labels_T10.jsonl")}
    ex = []
    for sd in med.get("top10_escaping", []):
        for s in range(30):
            row = {"input": f"[T10 mediation | direction rand_{sd} pushed at alpha 2 on twin W{s % 5 + 1} | slot {s}]",
                   "output": "escape = correct off-default program (bfs/dfs/label propagation)",
                   "metadata_direction_seed": sd, "metadata_slot": s,
                   "metadata_pi_committed": med["directions"][str(sd)]["pi"]}
            for arm in ("PUSH", "TASK", "RAND", "DEC"):
                l = G.get(f"T10|med|{arm}|{sd}|{s}")
                if l:
                    row[f"predict_{arm}"] = f"{l['label']}|{'pass' if l.get('passed') else 'fail'}"
            if len(row) > 5:
                ex.append(row)
    for sd, v in (med.get("prospective_pi") or {}).items():
        for s in range(10):
            l = G.get(f"T10|pro|PUSH|{sd}|{s}")
            if l:
                ex.append({"input": f"[T10 prospective | direction seed {sd} pushed at alpha 2 | slot {s}]",
                           "output": "escape = correct off-default program", "metadata_direction_seed": int(sd),
                           "metadata_slot": s, "metadata_pi_committed": v["pi"],
                           "predict_PUSH": f"{l['label']}|{'pass' if l.get('passed') else 'fail'}"})
    return ex


def tf_examples(unit: str, site: str, rtag: str = "") -> list[dict[str, Any]]:
    f = DATA / f"tf_{unit}_{site}{rtag}.jsonl"
    if not f.exists():
        return []
    rows = read_jsonl(f)
    by: dict[tuple, dict[str, Any]] = {}
    for r in rows:
        k = (r["src"], r["base"])
        e = by.setdefault(k, {"input": f"[{unit} | {site}{rtag} | teacher-forced held-out pair] source={r['src']} "
                                       f"base={r['base']}",
                              "output": r["class_src"], "metadata_class_src": r["class_src"],
                              "metadata_class_base": r["class_base"], "metadata_delta_full": r["delta_full"]})
        e[f"predict_{r['fit']}_k{r['rank_k']}"] = f"{r['delta']:.4f}"
    return list(by.values())


def main() -> None:
    setup_logging("outputs8")
    T = toks()
    from run_dec import load_prompts
    datasets = []
    for unit in ("T10", "GRID"):
        P = load_prompts(unit)
        tk = T["qwen" if unit == "T10" else "gemma"]
        for site in ("dec", "band"):
            ex = gen_examples(unit, site, tk, P)
            if ex:
                datasets.append({"dataset": f"{unit}_{site}_generation", "examples": ex})
        for site, rtag in (("dec", ""), ("band", ""), ("dec", "_L24")):
            ex = tf_examples(unit, site, rtag)
            if ex:
                datasets.append({"dataset": f"{unit}_{site}{rtag}_teacher_forced", "examples": ex})
    mx = med_examples()
    if mx:
        datasets.append({"dataset": "T10_mediation_clamp_prospective", "examples": mx})
    an = read_json(RESULTS / "analysis.json")
    meta: dict[str, Any] = {
        "method_name": "DAS8: one DAS protocol (linear orthonormal map, bounded KL objective, class-margin readout) at "
                       "the decision token and task band, with seven committed controls",
        "description": "Checks whether a low-rank causal variable for the chosen algorithm exists in Qwen3-8B (T10 "
                       "connected components) and gemma-3-4b-it (T1 grid path), against full-state, random-subspace, "
                       "label-control, random-init-network, reverse, natural-variance and seed-stability controls, and "
                       "validates in generation scored by hidden tests.",
        "verdicts": an.get("verdicts"), "K2": an.get("K2"), "mediation": an.get("mediation"),
        "commit_chain": verify(), "deviations": read_jsonl(RESULTS / "deviations.jsonl")}
    for name in ("dec_T10", "band_T10", "dec_GRID", "dec_T10_L24", "rinit_T10", "rinit_GRID", "rinit_T10_band",
                 "rinit_T10_L24", "s3_T10", "s3_GRID", "geometry", "novelty_audit", "costs", "post_T10",
                 "unit_tests_cpu", "unit_tests_gpu_T10", "unit_tests_gpu_GRID", "mediation_T10", "positioning",
                 "rederive", "scan_T10", "scan_GRID"):
        p = RESULTS / f"{name}.json"
        if p.exists():
            d = read_json(p)
            if name.startswith("s3_"):
                d = {k: v for k, v in d.items() if k != "tf_top50"}
            meta[name] = d
    for k, v in an.items():
        if k.startswith("gen_"):
            meta[k] = v
    out = {"metadata": meta, "datasets": datasets}
    write_json(ROOT / "method_out.json", out)
    logger.info(f"method_out.json: {len(datasets)} datasets, {sum(len(d['examples']) for d in datasets)} examples")


if __name__ == "__main__":
    main()
