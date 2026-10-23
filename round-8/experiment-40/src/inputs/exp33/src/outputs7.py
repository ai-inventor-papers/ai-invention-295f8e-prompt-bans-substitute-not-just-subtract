#!/usr/bin/env python3
"""method_out.json (exp_gen_sol_out schema) + full_/mini_/preview_ variants, validated with jsonschema.

One dataset per task. One example per (task, source group, CRN slot): input = the base prompt's user text (with the
edit applied to it named in metadata), output = the algorithm the source carries (Y(source); the default for BASE /
reverse rows), predict_<arm> = '<label>|<pass>' for every arm of that group on that slot (BASE, full-state exchange,
DAS rank k, random / permuted / read-position / unlearned controls), metadata_code_<arm> = the extracted program.
Every analysis lives in the top-level metadata."""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import jsonschema

from cfg import ROOT, read_json, read_jsonl, utc_now
from cfg7 import DEFAULT7, LABELS7, PROMPTS7, SAMPLES7, results7

DS_NAME = {"T2": "T2_weighted_shortest_path", "T10": "T10_connected_components", "T03": "T03_kth_smallest"}


def group_of(arm: str) -> str:
    if arm == "UT_FULL18" or arm.startswith("UT_"):
        return "unit_tests"
    if arm in ("TWIN",) or re.match(r"^(F\d|PAD\d|BAN_W\d)", arm) or arm == "BAN_W5":
        return "stage0_" + arm
    if arm.startswith(("FULLF3_", "PADBASE_F3_")) or (arm.startswith("FULL_ban_") and arm != "FULL_ban"):
        return "confirm_" + ("forced" if "F3" in arm else "ban")
    if arm.startswith("LAM"):
        return "R_lambda_" + arm.split("_", 1)[1]
    if "W4" in arm:
        return "heldout_W4"
    if arm.startswith(("REV", "REVLY")):
        return "reverse"
    if arm.startswith("NULL"):
        return "null_source"
    m = re.search(r"_F_([a-z_]+?)_k\d+$", arm) or re.match(r"^FULL_F_([a-z_]+)$", arm)
    if m:
        return "forced_" + m.group(1)
    return "ban_W5"


def safe(a: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", a)


def main() -> None:
    P7 = {r["key"]: r for r in read_jsonl(PROMPTS7)}
    raw = {r["sample_id"]: r for r in read_jsonl(SAMPLES7)}
    labs = read_jsonl(LABELS7)
    T = {t: read_json(results7(f"targets_{t}.json")) for t in DEFAULT7 if results7(f"targets_{t}.json").exists()}
    groups: dict[tuple[str, str, int], dict[str, Any]] = defaultdict(dict)
    for r in labs:
        g = group_of(r["arm"])
        if g == "unit_tests":
            continue
        groups[(r["task"], g, int(r["slot_index"]))][r["arm"]] = r
    datasets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (task, g, s), arms in sorted(groups.items()):
        # base prompt = the unedited / first arm's base
        any_r = next(iter(arms.values()))
        rw = raw.get(any_r["sample_id"], {})
        base = P7.get(rw.get("base_key") or "", {})
        spec_seg = base.get("segment") or ""
        from prompts7 import task_spec
        spec, _ = task_spec(task)
        inp = (spec_seg + "\n\n" + spec) if spec_seg else spec
        D = DEFAULT7[task]
        landing = "+".join(T[task]["landing"]) if task in T else "?"
        if g.startswith("forced_"):
            out = g.split("_", 1)[1]
        elif g in ("ban_W5", "heldout_W4", "confirm_ban") or g.startswith("R_lambda"):
            out = landing
        elif g in ("reverse",):
            out = D
        elif g == "null_source":
            out = D
        elif g.startswith("stage0_"):
            a = g[len("stage0_"):]
            out = a.split("_", 1)[1] if re.match(r"^(F\d|PAD\d)", a) else (landing if a.startswith("BAN") else D)
            if a.startswith("PAD"):
                out = D
        else:
            out = rw.get("Y_source") or "?"
        ex = {"input": inp, "output": out, "metadata_task": task, "metadata_group": g, "metadata_slot": s,
              "metadata_base_key": rw.get("base_key"), "metadata_crn_key": rw.get("crn_key")}
        for arm, r in sorted(arms.items()):
            a = safe(arm)
            rr = raw.get(r["sample_id"], {})
            ex[f"predict_{a}"] = f"{r.get('label')}|{'pass' if r.get('passed') else 'fail'}"
            ex[f"metadata_code_{a}"] = r.get("code") or ""
            ex[f"metadata_edit_{a}"] = json.dumps({"source_key": rr.get("source_key"), "site": rr.get("site"),
                                                   "rank_k": rr.get("rank_k"), "fit": rr.get("fit"),
                                                   "lambda": rr.get("lambda"), "realised_disp": rr.get("realised_disp"),
                                                   "n_new_tokens": rr.get("n_new_tokens"),
                                                   "finish_reason": rr.get("finish_reason"),
                                                   "labeller_source": r.get("labeller_source")})
        datasets[DS_NAME[task]].append(ex)
    meta = {"method_name": "Finding the model's hidden algorithm switch (iteration 7, bf16 Qwen3-8B)",
            "description": "Distributed alignment search (DAS): one linear orthonormal map (nested ranks 1-16) fitted at "
                           "the task-specification states of decoder blocks 12-23 (declared band fallback), validated "
                           "by held-out generation scored with hidden tests (correct source-Y programs), against the "
                           "full-state exchange (ceiling), random rank-k subspaces, permuted-label DAS, read-position "
                           "DAS, a null source, DIM-1, PCA-16, the reverse interchange and a random-init network.",
            "utc": utc_now(), "n_rows": len(labs), "model": "Qwen/Qwen3-8B@b968826d (bf16, thinking off)"}
    for nm in ("p1", "c_routing", "dormant", "committed_map_pilot", "r_discreteness", "m_manifold", "novelty_audit",
               "unit_tests_gpu", "engine_check", "costs", "timing_summary"):
        p = results7(f"{nm}.json")
        if p.exists():
            d = read_json(p)
            if nm == "m_manifold":
                d = {k: v for k, v in d.items() if k != "coords"}
            meta[nm] = d
    for t in DEFAULT7:
        for nm in (f"site_{t}", f"targets_{t}", f"das_fits_{t}", f"das_fits_ly_{t}", f"tf_eval_{t}",
                   f"tf_eval_{t}_LY", f"kstar_{t}", f"p1_controls_{t}", f"randinit_{t}"):
            p = results7(f"{nm}.json")
            if p.exists():
                d = read_json(p)
                if nm.startswith("targets_"):
                    d = {k: v for k, v in d.items() if k not in ("targets", "targets_val")}
                if nm.startswith("das_fits"):
                    d = {k: v for k, v in d.items() if k != "fits"} | {"fits": {
                        f: {kk: vv for kk, vv in (x or {}).items() if kk != "curve"} for f, x in d.get("fits", {}).items()}}
                meta[nm] = d
    dev = ROOT / "results" / "deviations.json"
    if dev.exists():
        meta["deviations"] = read_json(dev)
    out = {"metadata": meta, "datasets": [{"dataset": k, "examples": v} for k, v in datasets.items()]}
    schema = json.loads((ROOT / "schemas" / "exp_gen_sol_out.json").read_text())
    jsonschema.validate(out, schema)
    (ROOT / "method_out.json").write_text(json.dumps(out, indent=1, default=str))

    def trunc(o: Any) -> Any:
        if isinstance(o, str):
            return o[:200]
        if isinstance(o, list):
            return [trunc(x) for x in o]
        if isinstance(o, dict):
            return {k: trunc(v) for k, v in o.items()}
        return o
    mini = {"metadata": meta, "datasets": [{"dataset": x["dataset"], "examples": x["examples"][:3]}
                                           for x in out["datasets"]]}
    for name, obj in (("full", out), ("mini", mini), ("preview", trunc(mini))):
        jsonschema.validate(obj, schema)
        (ROOT / f"{name}_method_out.json").write_text(json.dumps(obj, indent=1, default=str))
    print(f"method_out.json: {sum(len(x['examples']) for x in out['datasets'])} examples in "
          f"{len(out['datasets'])} datasets; schema OK")


if __name__ == "__main__":
    main()
