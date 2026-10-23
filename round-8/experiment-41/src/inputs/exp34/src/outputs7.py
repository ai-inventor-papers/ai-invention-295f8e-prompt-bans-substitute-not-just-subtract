#!/usr/bin/env python3
"""method_out.json (exp_gen_sol_out schema): datasets f_cells, p2_directions, t03_confirmation, targeted_push,
top5_push, fork_resampling, engine_check; every analysis result goes into the top-level metadata."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import c7 as common  # noqa: E402
from c7 import (DATA, FORK_ROWS, LABELS, PRED, RESULTS, ROOT, SEEDS_T03, read_json, read_jsonl,  # noqa: E402
                verify_chain, write_json)


def opt(p: Path) -> Any:
    return read_json(p) if p.exists() else None


def fmt(x: Any) -> str:
    if x is None:
        return "NA"
    if isinstance(x, float):
        return f"{x:.6g}"
    return str(x)


def f_cells(fa: dict, c3: dict) -> list[dict[str, Any]]:
    import analysis7 as A
    Y = A.outcomes()
    out = []
    for key, c in sorted(c3["cells"].items()):
        if key not in Y:
            continue
        o = Y[key]
        task, cell = key.split("|", 1)
        out.append({"input": f"task {task}; cell {cell} ({c['family']}); Qwen3-8B bf16, thinking off, T=1.0; prefill "
                             f"edit as committed; outcome source {o['source']}",
                    "output": fmt(o["y"]), "predict_fork_margin": fmt(c["Pbar"]),
                    "predict_margin_logit_nats": fmt(c["m"]), "predict_llr48": fmt(c.get("llr48")),
                    "metadata_task": task, "metadata_cell": cell, "metadata_family": c["family"],
                    "metadata_n": o["n"], "metadata_k_correct_off_default": o["k"], "metadata_attempted": o["att"],
                    "metadata_pass": o["pass"], "metadata_labels": o["labels"],
                    "metadata_margin_source": c.get("margin_source")})
    return out


def p2_dirs(fa: dict, pa: dict) -> list[dict[str, Any]]:
    out = []
    for task in ("T10", "T2"):
        for r in fa["cells"][task]:
            out.append({"input": f"task {task}; fixed random direction rand_{r['seed']} pushed at alpha 2 (absolute "
                                 f"ban unit, blocks 12-23, task-spec positions, prefill only)",
                        "output": fmt(r["y"]), "predict_axis": fmt(r["b"]), "predict_pt": fmt(r["pi_Pt"]),
                        "predict_norm": fmt(r["norm"]), "predict_a_share": fmt(r["a_share"]),
                        "predict_fork_margin": fmt(r["m"]), "predict_llr48": fmt(r["llr48"]),
                        "metadata_task": task, "metadata_seed": r["seed"], "metadata_attempted": r["att"],
                        "metadata_confirmed_escaper_exp29": bool(r["confirmed"])})
    return out


def t03(tc: dict) -> list[dict[str, Any]]:
    return [{"input": f"task T03; fresh direction rand_{r['seed']} at alpha 2 (absolute T03 unit), N = 10; "
                      f"predictions committed in commit #3 before generation",
             "output": fmt(r["y"]), "predict_axis": fmt(r["b"]), "predict_margin_logit_nats": fmt(r["m"]),
             "metadata_seed": r["seed"], "metadata_attempted": r["att"]} for r in tc["rows"]]


def slot_table(task: str, arms_prefix: tuple[str, ...], lab_key: str = "label") -> list[dict[str, Any]]:
    L = read_jsonl(LABELS)
    by = defaultdict(dict)
    for r in L:
        if r["task"] != task or int(r["sample_id"]) > 5:
            continue
        if r["arm"] == "TWIN" or r["arm"].startswith(arms_prefix):
            by[(r["template"], int(r["sample_id"]))][r["arm"]] = r
    out = []
    for (w, k), d in sorted(by.items()):
        tw = d.get("TWIN")
        if tw is None:
            continue
        ex = {"input": f"task {task}; CRN slot ({w}, k={k}); same uniforms in every arm",
              "output": f"{tw.get(lab_key) or tw['label']}|{'pass' if tw['passed'] else 'fail'}",
              "metadata_task": task, "metadata_template": w, "metadata_k": k}
        for arm, r in sorted(d.items()):
            if arm == "TWIN":
                continue
            nm = "predict_" + arm.replace(".", "p").replace("-", "_")
            ex[nm] = f"{r.get(lab_key) or r['label']}|{'pass' if r['passed'] else 'fail'}"
        out.append(ex)
    return out


def forced_rows() -> list[dict[str, Any]]:
    L = read_jsonl(DATA / "labels_force.jsonl")
    tw = {(r["task"], r["template"], int(r["sample_id"])): r for r in read_jsonl(LABELS) if r["arm"] == "TWIN"}
    by = defaultdict(dict)
    for r in L:
        by[(r["task"], r["template"], int(r["sample_id"]))][r["arm"]] = r
    out = []
    for (task, w, k), d in sorted(by.items()):
        t = tw.get((task, w, k))
        if t is None:
            continue
        ex = {"input": f"task {task}; CRN slot ({w}, k={k}); neutral twin prompt; exploratory forced opening token",
              "output": f"{t['label']}|{'pass' if t['passed'] else 'fail'}", "metadata_task": task,
              "metadata_template": w, "metadata_k": k}
        for arm, r in sorted(d.items()):
            ex["predict_" + "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in arm)] = \
                f"{r['label']}|{'pass' if r['passed'] else 'fail'}"
        out.append(ex)
    return out


def fork_rows(forks: dict) -> list[dict[str, Any]]:
    out = []
    for task, v in forks["tasks"].items():
        for pid, a in v["per_path"].items():
            s = a["series"]
            for t, k, n, src in zip(s["t"], s["k"], s["n"], s["src"]):
                out.append({"input": f"task {task}; base path {pid} (class {a['class']}, cell {a['cell']}); resample "
                                     f"from generated position {t}",
                            "output": f"{k}/{n}",
                            "predict_fork_position": str(a["fork"]) if a["fork"] is not None else "none",
                            "predict_change_point_significant": str(a["cp"]["p_value"] < 0.01),
                            "metadata_task": task, "metadata_path": pid, "metadata_t": t,
                            "metadata_source": src, "metadata_class": a["class"],
                            "metadata_change_point_p": a["cp"]["p_value"], "metadata_fork": a["fork"]})
    return out


def engine_rows(ec: dict) -> list[dict[str, Any]]:
    out = []
    for k, v in ec.items():
        agree = v.get("label_agree") if isinstance(v, dict) else None
        out.append({"input": f"engine check {k}", "output": json.dumps(v)[:2000],
                    "predict_this_engine_agreement": "NA" if agree is None else f"{agree:.4f}", "metadata_check": k})
    return out


def main() -> None:
    fa, pa = read_json(RESULTS / "f_analysis.json"), read_json(RESULTS / "p2_analysis.json")
    c3 = read_json(common.c3_path())
    tc = read_json(RESULTS / "t03_confirmation.json")
    forks = read_json(RESULTS / "forks.json")
    ec = read_json(RESULTS / "engine_check.json")
    ds = [{"dataset": "f_cells", "examples": f_cells(fa, c3)},
          {"dataset": "p2_directions", "examples": p2_dirs(fa, pa)},
          {"dataset": "t03_confirmation", "examples": t03(tc) or [{"input": "none", "output": "NA"}]},
          {"dataset": "fork_resampling", "examples": fork_rows(forks)},
          {"dataset": "engine_check", "examples": engine_rows(ec)}]
    for task in ("T10", "T2", "T03"):
        ex = slot_table(task, ("AX_", "RX_"))
        if ex:
            ds.append({"dataset": f"targeted_push_{task}", "examples": ex})
    ex = slot_table("T1", ("SURV_", "RSURV_", "AWAY_", "IDASTAR_"), lab_key="label10")
    if ex:
        ds.append({"dataset": "top5_push_T1", "examples": ex})
    fr = forced_rows()
    if fr:
        ds.append({"dataset": "forced_token_exploratory", "examples": fr})
    meta = {"method_name": "fork margin (F) and default-to-runner-up axis projection (P2) vs P_t / norm / energy "
                           "baselines; targeted push vs matched random; in-manifold top-five push vs random-survivor "
                           "null",
            "model": "Qwen/Qwen3-8B b968826d9c46dd6066d109eabc6255188de91218, bf16, thinking off",
            "verdicts": fa["verdicts"], "F": fa["F"], "P2": pa["P2"], "t03_confirmation": tc,
            "forks": {t: {k: v for k, v in d.items() if k not in ("per_path", "opening_ids")}
                      for t, d in forks["tasks"].items()},
            "axis": opt(RESULTS / "axis.json"), "targeted_push": opt(RESULTS / "targeted_push.json"),
            "clamp": opt(RESULTS / "clamp.json"), "remeasure_same_engine": opt(RESULTS / "remeasure.json"),
            "top5_landing": opt(RESULTS / "top5_landing.json"), "top5_geometry": opt(RESULTS / "top5_geometry.json"),
            "engine_check": ec, "novelty_audit": opt(RESULTS / "novelty_audit.json"),
            "unit_tests_gpu": opt(RESULTS / "unit_tests_gpu.json"), "unit_tests_cpu": opt(RESULTS / "unit_tests_cpu.json"),
            "deviations": read_jsonl(RESULTS / "deviations.jsonl"), "hash_chain": verify_chain(),
            "dependency_usage": opt(RESULTS / "dependency_usage.json"), "costs": opt(RESULTS / "costs.json"),
            "hardware": opt(PRED / "hardware.json"), "timing_summary": opt(RESULTS / "timing_summary.json"),
            "exploratory_post_hoc": {"opening_llr_by_length": opt(RESULTS / "explore_llr.json"),
                                     "forced_token": opt(RESULTS / "force_token.json")},
            "commit_files": sorted(p.name for p in PRED.glob("commit*.json")),
            "independent_audit": opt(RESULTS / "rederive.json")}
    obj = {"metadata": meta, "datasets": [d for d in ds if d["examples"]]}
    write_json(ROOT / "method_out.json", obj)
    print({d["dataset"]: len(d["examples"]) for d in obj["datasets"]})


if __name__ == "__main__":
    main()
