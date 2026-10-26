"""Build method_out.json (exp_gen_sol_out schema) from the raw rows and the analysis results, then the
full/mini/preview variants. Safe to run at any time: missing analysis pieces are listed in metadata.not_run."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, PRED, RESULTS, ROOT, read_jsonl, utc_now, verify_commit_chain, write_json  # noqa: E402

# aii-json skill (schema validation + mini/preview); set AII_JSON_SKILL to its folder, skipped when absent
SKILL = Path(os.environ.get("AII_JSON_SKILL", str(ROOT.parent / ".claude" / "skills" / "aii-json")))


def _load(p: Path):
    try:
        return json.loads(p.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _s(x, nd=6) -> str:
    if x is None:
        return "NA"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def calls_dataset(rows: list[dict]) -> dict:
    ex = []
    for r in sorted(rows, key=lambda r: (r["seed"], r["arm"], r["call_idx"])):
        out = f"valid|{r['F']:.6f}" if r["label"] == "valid" and r.get("F") is not None else r["label"]
        e = {"input": (f"arm={r['arm']} seed={r['seed']} call={r['call_idx']} round={r['round']} island={r['island']} "
                       f"k={r['k']} parents={','.join(r['parent_ids'])} parent_F="
                       f"{','.join(_s(f, 4) for f in r['parent_F'])}"),
             "output": out,
             "metadata_arm": r["arm"], "metadata_seed": r["seed"], "metadata_call_idx": r["call_idx"],
             "metadata_round": r["round"], "metadata_label": r["label"], "metadata_probe_valid": bool(r.get("probe_valid")),
             "metadata_F": r.get("F"), "metadata_G50": r.get("G50"), "metadata_G100": r.get("G100"),
             "metadata_gen_tokens": r.get("gen_tokens"), "metadata_prompt_tokens": r.get("prompt_tokens"),
             "metadata_discarded_tokens": r.get("discarded_tokens"), "metadata_truncated": r.get("truncated"),
             "metadata_trimmed_lines": r.get("trimmed_lines"), "metadata_ast_hash": r.get("ast_hash"),
             "metadata_code_sha256": r.get("code_sha256"), "metadata_engine": r.get("engine"),
             "metadata_body": (r.get("body") or "")[:4000]}
        d = r.get("dtb")
        if d:
            e.update({"predict_dtb_j_star": _s(d.get("j_star")), "predict_dtb_H_j_star": _s(d.get("H_j_star")),
                      "predict_dtb_forced_rank": _s(d.get("forced_rank")),
                      "predict_dtb_forced_text": _s(d.get("forced_text")),
                      "predict_dtb_sampled_text": _s(d.get("sampled_text")),
                      "predict_dtb_forced_class": _s(d.get("forced_class")),
                      "predict_dtb_no_branch": _s(d.get("no_branch")),
                      "predict_dtb_forced_eq_sampled": _s(d.get("forced_eq_sampled"))})
        ex.append(e)
    return {"dataset": "novt_calls", "examples": ex}


def best_dataset(held: dict | None, base: dict) -> dict:
    ex = []
    nn_g = base["NN"]["G200"]
    comps = {"NN": nn_g}
    if held:
        if held.get("P1", {}).get("G200") is not None:
            comps["P1"] = held["P1"]["G200"]
        for k in ("T1.0", "T1.6"):
            vals = [held.get("arm_best", {}).get(f"{k}|{s}", {}).get("G200") for s in (0, 1)]
            vals = [v for v in vals if v is not None]
            if vals:
                comps[k] = sum(vals) / len(vals)
        for key, v in held.get("arm_best", {}).items():
            e = {"input": f"selection-best probe-valid program of {key} (call {v.get('call_idx')}, F={_s(v.get('F'), 4)})",
                 "output": _s(v.get("G200"), 4), "metadata_kind": "arm_best", "metadata_arm_seed": key,
                 "metadata_G200": v.get("G200"), "metadata_G200_ext": v.get("G200_ext"),
                 "metadata_tsplib_mean": v.get("tsplib_mean"), "metadata_F": v.get("F"),
                 "metadata_ci_vs_NN": v.get("ci_vs_NN"), "metadata_code": (v.get("code") or "")[:4000]}
            for cname, cg in comps.items():
                e[f"predict_{cname.replace('.', '_')}"] = _s(cg, 4)
            ex.append(e)
        for name, v in held.get("others", {}).items():
            e = {"input": f"comparator {name}", "output": _s(v.get("G200"), 4), "metadata_kind": v.get("kind", "other"),
                 "metadata_G200_ext": v.get("G200_ext"), "metadata_tsplib_mean": v.get("tsplib_mean"),
                 "metadata_F": v.get("F")}
            for cname, cg in comps.items():
                e[f"predict_{cname.replace('.', '_')}"] = _s(cg, 4)
            ex.append(e)
    if not ex:
        e = {"input": "comparator NN (seed program)", "output": _s(nn_g, 4), "metadata_kind": "baseline",
             "metadata_G200_ext": base["NN"]["G200_ext"], "metadata_tsplib_mean": base["NN"]["tsplib"]["mean_gap"],
             "predict_NN": _s(nn_g, 4)}
        ex.append(e)
        for name, v in base.get("reference_heuristics", {}).get("heldout", {}).items():
            ex.append({"input": f"tour-length reference {name} (other interface)", "output": _s(v["mean_gap"], 4),
                       "metadata_kind": "reference_heuristic",
                       "metadata_G200_ext": base["reference_heuristics"]["heldout_ext"][name]["mean_gap"],
                       "predict_NN": _s(nn_g, 4)})
    return {"dataset": "novt_best", "examples": ex}


def clusters_dataset(cl: dict | None) -> dict | None:
    if not cl:
        return None
    ex = []
    for key, v in cl.get("per_arm_seed", {}).items():
        e = {"input": f"behaviour clusters of {key} ({v.get('calls')} calls, {v.get('probe_valid')} probe-valid programs)",
             "output": str(v.get("primary_clusters")),
             "metadata_arm_seed": key}
        for k2, v2 in v.items():
            if k2 in ("discovery_primary", "discovery_secondary"):
                continue
            e[f"metadata_{k2.replace('.', '_').replace('-', '_')}"] = v2
        for rk, rv in cl.get("ratios_per_seed", {}).items():
            if rk.endswith(key.split("|")[1]) and key.startswith("DTB"):
                e[f"predict_ratio_vs_{rk.replace('.', '_').replace('|', '_seed')}"] = _s(rv.get("ratio"), 4)
        ex.append(e)
    return {"dataset": "novt_clusters", "examples": ex} if ex else None


def main() -> None:
    rows = list({(r["arm"], r["seed"], r["call_idx"]): r for r in read_jsonl(DATA / "calls.jsonl")}.values())
    base = _load(RESULTS / "baselines.json")
    held = _load(RESULTS / "heldout.json")
    cl = _load(RESULTS / "clusters.json")
    v1 = _load(RESULTS / "verdict_v1.json")
    v2 = _load(RESULTS / "verdict_v2.json")
    datasets = [calls_dataset(rows), best_dataset(held, base)]
    c = clusters_dataset(cl)
    if c:
        datasets.append(c)
    not_run = [n for n, x in (("clusters", cl), ("heldout", held), ("verdict_v1", v1), ("verdict_v2", v2),
                              ("v3", _load(RESULTS / "v3.json")), ("corpus", _load(RESULTS / "corpus.json")),
                              ("judges", _load(RESULTS / "judges.json")),
                              ("positioning", _load(RESULTS / "positioning.json")),
                              ("rederive", _load(RESULTS / "rederive.json"))) if x is None]
    meta = {
        "method_name": "NOV-T: decision-token branching (DTB) vs temperature in a FunSearch-style constructive-TSP "
                       "heuristic search",
        "utc": utc_now(), "status": (_load(RESULTS / "run_status.json") or {}).get("status", "in_progress"),
        "verdict_v1": v1, "verdict_v2": v2, "v3": _load(RESULTS / "v3.json"),
        "commitments": verify_commit_chain(), "cstar": _load(PRED / "cstar.json"),
        "protocol_sha256": None, "baselines_NN": base["NN"] if base else None,
        "references": _load(RESULTS / "references.json"), "gpu_mechanics": _load(RESULTS / "gpu_mechanics.json"),
        "deviations": _load(RESULTS / "deviations.json"), "timing": _load(RESULTS / "timing.json"),
        "costs": _load(RESULTS / "costs.json"), "search_summary": _load(RESULTS / "search_summary.json"),
        "rederive": _load(RESULTS / "rederive.json"), "not_run": not_run,
        "engine": "vllm0.11.0|Qwen3-8B-FP8@220b46e|marlin|O3-piecewise+fulldecode (NVIDIA L4)",
        "n_calls": len(rows),
    }
    if meta["baselines_NN"]:
        meta["baselines_NN"] = {k: v for k, v in meta["baselines_NN"].items() if not isinstance(v, (dict, list))}
    obj = {"metadata": meta, "datasets": datasets}
    write_json(ROOT / "method_out.json", obj, indent=None)
    py = SKILL.parent / ".ability_client_venv" / "bin" / "python"
    if not py.exists():
        print("aii-json skill not found: method_out.json written without schema validation / variants")
        return
    r = subprocess.run([str(py), str(SKILL / "scripts" / "aii_json_validate_schema.py"), "--format", "exp_gen_sol_out",
                        "--file", str(ROOT / "method_out.json")], capture_output=True, text=True)
    print(r.stdout[-600:], r.stderr[-400:])
    r = subprocess.run([str(py), str(SKILL / "scripts" / "aii_json_format_mini_preview.py"), "--input",
                        str(ROOT / "method_out.json"), "--output-dir", str(ROOT)], capture_output=True, text=True)
    print(r.stdout[-800:], r.stderr[-400:])


if __name__ == "__main__":
    main()
