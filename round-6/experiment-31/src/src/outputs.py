#!/usr/bin/env python3
"""Build method_out.json (exp_gen_sol_out schema) from raw rows, labels and results/*.json.

datasets (one example per CRN slot or per unit; input = the prompt fed, output = the reference label|pass,
predict_<arm> = label|pass of every coupled arm):
  natural_split    S3: 600 samples (T1, T04, R6 x W1-W5 x slots 0-39)
  engine_check     T1/T04 slots 0-9: this artifact vs exp28 (predict_exp28)
  fork_resampling  S4: one example per (base path, prefix length t): output = base label, predict_* = P(BFS) etc.
  prompt_variants  S5/S6b: 120 neutral variants: output = y_v, predict_* = held-out-noun predictions
  clamp_cells      S8: 50 CRN slots: output = canonical-prefix twin label|pass, predict_<cell> per cell
  contrast_arms    S5/S11: 50 slots: output = free twin label|pass, predict_forced_*/ban_*/top5/top5_twin
metadata: every headline result (gate, fork, decodability, readout, clamps, geometry, novelty, ...), deviations,
commitments, costs and timing.
"""

from __future__ import annotations

import json
from typing import Any

from cfg import (COMMIT_LOG, DATA_DIR, LOG_DIR, PRED_DIR, RESULTS_DIR, TEMPLATE_IDS, read_json, read_jsonl,
                 write_json)


def _lp(r: dict[str, Any] | None) -> str:
    if r is None:
        return "missing"
    return f"{r.get('label')}|{'pass' if r.get('passed') else 'fail'}"


def _rj(name: str) -> Any:
    p = RESULTS_DIR / name
    return read_json(p) if p.exists() else None


def build(load_labelled, prompts_mod) -> dict[str, Any]:
    PG = prompts_mod
    datasets = []
    # ---------------- natural split
    ex = []
    s3 = {}
    for task in ("T1", "T04", "R6"):
        for r in load_labelled("raw_s3.jsonl", task):
            s3[(task, r["template"], r["slot"])] = r
            p = PG.p_twin(task, r["template"])
            ex.append({"input": p["text"], "output": _lp(r), "predict_gemma_3_4b_it_program": (r.get("code") or "")[:4000],
                       "metadata_task": task, "metadata_template": r["template"], "metadata_slot": r["slot"],
                       "metadata_label": r["label"], "metadata_passed": bool(r["passed"]),
                       "metadata_labeller_source": r.get("labeller_source"), "metadata_finish_reason": r.get("finish_reason"),
                       "metadata_n_new_tokens": r.get("n_new_tokens"), "metadata_prompt_sha256": r.get("prompt_sha256"),
                       "metadata_ukey": json.dumps(r.get("ukey"))})
    datasets.append({"dataset": "natural_split", "examples": ex})
    # ---------------- engine check
    ec = _rj("engine_check.json") or {}
    ref = {}
    for r in read_jsonl(RESULTS_DIR.parent / "inputs" / "exp28" / "data" / "samples.jsonl"):
        if r.get("arm") == "twin" and r.get("task") in ("T1", "T04"):
            ref[(r["task"], r["template"], int(r["slot"]))] = r
    ex = []
    for task in ("T1", "T04"):
        for w in TEMPLATE_IDS:
            for k in range(10):
                r = s3.get((task, w, k))
                q = ref.get((task, w, k))
                if r is None:
                    continue
                ex.append({"input": PG.p_twin(task, w)["text"], "output": _lp(r), "predict_exp28": _lp(q),
                           "metadata_task": task, "metadata_template": w, "metadata_slot": k,
                           "metadata_same_program": bool(q is not None and r.get("code_sha256") == q.get("code_sha256"))})
    datasets.append({"dataset": "engine_check", "examples": ex})
    # ---------------- fork resampling
    fk = _rj("fork.json")
    if fk:
        ex = []
        for p in fk["per_path"]:
            base = next((r for r in s3.values() if r["row_id"] == p["row_id"]), None)
            for t, pb, k, n in zip(p["t"], p["p_bfs"], p["k_own"], p["n"]):
                ids = (base or {}).get("token_ids", [])[:t]
                ex.append({"input": f"[{p['template']} twin prompt] + response prefix of {t} tokens: "
                                    + json.dumps(ids), "output": p["label"],
                           "predict_p_bfs_continuations": f"{pb:.4f}", "predict_own_class_share": f"{k / max(n, 1):.4f}",
                           "metadata_base_row": p["row_id"], "metadata_t": t, "metadata_n_continuations": n,
                           "metadata_path_fork_t": p["fork_t"], "metadata_change_point_p": p["cp"]["p_value"]})
        datasets.append({"dataset": "fork_resampling", "examples": ex})
    # ---------------- prompt variants
    try:
        import torch

        V = torch.load(RESULTS_DIR.parent / "cache" / "states" / "variants.pt")
        sv = {}
        for r in read_jsonl(DATA_DIR / "sampling_validation_labels.jsonl"):
            sv.setdefault((r["template"], r["noun"]), []).append(r["cls"])
        ex = []
        for v in V:
            s = sv.get((v["template"], v["noun"]))
            e = {"input": PG.p_noun_variant("T1", v["template"], v["noun"])["text"], "output": f"{v['y']:.5f}",
                 "metadata_template": v["template"], "metadata_noun": v["noun"],
                 "metadata_noun_source": v["noun_source"], "metadata_y_v": v["y"]}
            if s:
                e["predict_sampled_bfs_share"] = f"{sum(c == 'bfs' for c in s) / len(s):.3f}"
                e["metadata_n_sampled"] = len(s)
            ex.append(e)
        datasets.append({"dataset": "prompt_variants", "examples": ex})
    except (FileNotFoundError, RuntimeError, KeyError, TypeError):
        pass
    # ---------------- clamp cells
    cells = load_labelled("raw_cells.jsonl", "T1") if (DATA_DIR / "raw_cells.jsonl").exists() else []
    if cells:
        by: dict[tuple, dict] = {}
        arms = sorted({r["arm"] for r in cells})
        for r in cells:
            by.setdefault((r["template"], r["slot"]), {})[r["arm"]] = r
        c1 = read_json(PRED_DIR / "commit1.json")
        ex = []
        for (w, k), d in sorted(by.items()):
            e = {"input": PG.p_twin("T1", w)["text"] + "\n[forced response prefix c*] " + c1["cstar_text"],
                 "output": _lp(d.get("twin_cstar")), "metadata_template": w, "metadata_slot": k}
            for a in arms:
                if a == "twin_cstar":
                    continue
                key = "predict_" + a.replace("|", "_").replace("@", "_at_").replace("-", "_")
                e[key] = _lp(d.get(a))
            ex.append(e)
        datasets.append({"dataset": "clamp_cells", "examples": ex})
    # ---------------- contrast arms (prompting ceiling, bans, TOP5)
    con = load_labelled("raw_contrast.jsonl", "T1")
    if con:
        by = {}
        for r in con:
            w = r["template"] if r["template"].startswith("W") else "W" + r["template"][1:]
            by.setdefault((w, r["slot"]), {})[r["arm"]] = r
        ex = []
        for (w, k), d in sorted(by.items()):
            e = {"input": PG.p_twin("T1", w)["text"], "output": _lp(s3.get(("T1", w, k))),
                 "metadata_template": w, "metadata_slot": k}
            for a, r in sorted(d.items()):
                e["predict_" + a] = _lp(r)
            ex.append(e)
        datasets.append({"dataset": "contrast_arms", "examples": ex})
    # ---------------- metadata
    meta: dict[str, Any] = {"method_name": "Claim S: Gemma Scope 2 SAE readout and steering of gemma-3-4b-it's BFS/DFS fork",
                            "model": "google/gemma-3-4b-it@093f9f388b31de276ce2de164bdc2081324b9767 (bf16, text decoder)",
                            "instruments": _rj("../predictions/instrument_ids.json") if False else read_json(PRED_DIR / "instrument_ids.json")}
    for name in ("tests_gpu_s1", "natural_split", "engine_check", "gate", "fork", "nouns", "sampling_validation",
                 "decodability_within", "readout", "contrast_separability", "selection", "logit_sweep_summary",
                 "clamps", "top5", "geometry", "novelty_audit", "regate", "deviations", "analysis_errors", "attribution",
                 "das", "costs", "timing", "rederive", "rederive_headlines", "verify_chain", "matched_pass_dose",
                 "extra_cells"):
        v = _rj(f"{name}.json")
        if v is None:
            continue
        if name == "fork":
            v = {k: v[k] for k in v if k not in ("identifying", "per_path")} | {
                "per_path_summary": [{"row_id": p["row_id"], "label": p["label"], "fork_t": p["fork_t"], "rise": p["rise"],
                                      "cp_p": p["cp"]["p_value"]} for p in v["per_path"]]}
        if name in ("novelty_audit", "regate") and isinstance(v, dict):
            v = {k: v[k] for k in v if k != "items"} | {"n_items": len(v.get("items", []))}
        meta[name] = v
    meta["commitments"] = COMMIT_LOG.read_text().splitlines() if COMMIT_LOG.exists() else []
    tb = read_jsonl(LOG_DIR / "timing_batches.jsonl")
    meta["timing_summary"] = {"n_batches": len(tb), "gpu_seconds_generation": sum(r["seconds"] for r in tb)}
    out = {"metadata": meta, "datasets": [d for d in datasets if d["examples"]]}
    # never publish absolute server paths: workspace root -> '.', any other absolute /ai-inventor path -> <server>
    import re
    txt = json.dumps(out).replace(str(RESULTS_DIR.parent), ".")
    out = json.loads(re.sub(r"/ai-inventor/[^\"\s']*", "<server-path>", txt))
    write_json(RESULTS_DIR.parent / "method_out.json", out, indent=None)
    return out
