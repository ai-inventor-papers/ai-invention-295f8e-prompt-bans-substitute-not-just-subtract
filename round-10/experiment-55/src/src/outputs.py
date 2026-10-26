#!/usr/bin/env python3
"""Stage 8 outputs: placebos, G1 verdict, verification summary, hardware record and method_out.json
(exp_gen_sol_out: datasets tpg2_factorial, tpg2_topups, tpg2_placements, tpg2_g1_rows)."""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import json
import platform
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import g1  # noqa: E402
import g2  # noqa: E402
import v10  # noqa: E402

TAGS = ["8b", "32b"]


def placebos() -> dict[str, Any]:
    import analysis

    out = {}
    rng = np.random.default_rng(13)
    for tag in TAGS:
        F = analysis.factorial(tag)
        bi = F["blocks"].index(v10.MODELS[tag]["primary_block"])
        DS = g1.d_state(F["R"][:, 0, bi].astype(np.float64))
        DC = g1.d_cont(F["cont"])
        DD = g1.d_disc(F["disc"])
        sh = list(np.array(F["disc"])[rng.permutation(len(F["disc"]))])
        a = g1.core_stats(DS, g1.d_disc(sh), DC)
        cont = np.array(F["cont"], dtype=object)
        disc = np.array(F["disc"])
        for d in np.unique(disc):
            idx = np.where(disc == d)[0]
            cont[idx] = cont[rng.permutation(idx)]
        b = g1.core_stats(DS, DD, g1.d_cont(list(cont)))
        g2r = v10.read_json(v10.RESULTS / f"g2_{tag}.json") if (v10.RESULTS / f"g2_{tag}.json").exists() else {}
        out[tag] = {"discipline_shuffled_all": {"rho_dc": a["rho_dc"], "must_fail": "rho_dc ~ 0 (< 0.3)",
                                                "fails_as_required": abs(a["rho_dc"]) < 0.3},
                    "container_shuffled_within_discipline": {"rho_cd": b["rho_cd"], "must_fail": "rho_cd ~ 0",
                                                             "fails_as_required": abs(b["rho_cd"]) < 0.1},
                    "family_membership_shuffled": g2r.get("placebo_family_shuffle")}
    v10.write_json(v10.RESULTS / "placebos.json", out)
    return out


def g1_verdict() -> dict[str, Any]:
    per = {t: v10.read_json(v10.RESULTS / f"g1_{t}.json")["primary"] for t in TAGS
           if (v10.RESULTS / f"g1_{t}.json").exists()}
    v = g1.verdict(per)
    core = {t: v10.read_json(v10.RESULTS / f"g1_{t}.json")["S1_crossed_core"] for t in per}
    v["crossed_core_view"] = g1.verdict(core)
    v["above_E0_and_RANDNET"] = {}
    for t in per:
        d = v10.read_json(v10.RESULTS / f"g1_{t}.json")
        v["above_E0_and_RANDNET"][t] = {"rho_dc": d["primary"]["rho_dc"],
                                        "E0": d.get("S7_E0_bag_of_tokens", {}).get("rho_dc"),
                                        "RANDNET": d.get("S7_RANDNET_block17", {}).get("rho_dc"),
                                        "rho_dc_ci_low": d["primary"]["bootstrap"]["rho_dc"]["ci95"][0]}
    v10.write_json(v10.RESULTS / "g1_verdict.json", v)
    return v


def verification_summary() -> dict[str, Any]:
    rows = v10.read_jsonl(v10.DATA / "programs_v10.jsonl")
    raws = v10.read_jsonl(v10.DATA / "gen_raw_v10.jsonl")
    hand = v10.read_jsonl(v10.DATA / "hand_reads_v10.jsonl")
    hv = {h["uid"]: h["verdict"] for h in hand}
    per: dict[str, Any] = defaultdict(lambda: Counter())
    cost = defaultdict(float)
    for r in raws:
        cost[r.get("cell")] += float(r.get("cost") or 0.0)
    for r in rows:
        c = r["cell"]
        tag = "pilot" if r.get("pilot") else ("smoke" if r.get("wave") == "smoke" else "main")
        per[c][f"{tag}_rows"] += 1
        if tag != "main":
            continue
        per[c]["attempts_initial"] += int(not r.get("repair"))
        per[c]["repairs"] += int(bool(r.get("repair")))
        per[c]["paraphrases"] += int(r.get("source") == "paraphrase")
        per[c][f"verdict_{r['verdict']}"] += 1
        if r["verdict"] == "HAND":
            per[c][f"hand_{hv.get(r['uid'], 'unread')}"] += 1
        for reason in r.get("reasons") or []:
            per[c][f"reason_{reason}"] += 1
    out = {"per_cell": {c: dict(v) | {"cost_usd": round(cost.get(c, 0.0), 5)} for c, v in sorted(per.items())},
           "costs": v10.read_json(v10.RESULTS / "costs_v10.json"), "n_hand_reads": len(hand),
           "hand_read_verdicts": dict(Counter(h["verdict"] for h in hand)),
           "frame_freeze": v10.read_json(v10.DATA / "frame_freeze.json")["counts"],
           "topup_freeze": v10.read_json(v10.DATA / "topup_freeze.json")["counts"]}
    v10.write_json(v10.RESULTS / "verification_summary.json", out)
    return out


def hardware() -> dict[str, Any]:
    import torch

    hw = {"utc": v10.utc_now(), "python": platform.python_version(), "platform": platform.platform(),
          "cpus_cgroup": 6, "ram_gb_cgroup": 28.0, "torch": torch.__version__,
          "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
          "vram_gb": round(torch.cuda.get_device_properties(0).total_memory / 1e9, 2) if torch.cuda.is_available()
          else None}
    try:
        import transformers
        import sklearn
        import scipy

        hw["packages"] = {"transformers": transformers.__version__, "scikit-learn": sklearn.__version__,
                          "scipy": scipy.__version__, "numpy": np.__version__}
    except ImportError:
        pass
    v10.write_json(v10.PRED / "hardware.json", hw)
    return hw


def frame_nearest(tag: str) -> dict[str, str]:
    """In-frame nearest class of every frame program (self excluded) on the full frame geodesics."""
    p = v10.STATES_V10 / f"g2frame_{tag}.npz"
    if not p.exists():
        return {}
    z = np.load(p)
    labels, geo = z["labels"], z["geo"].astype(np.float64)
    import analysis

    F = analysis.factorial(tag)
    _Xc, _lab, meta_c = analysis.catalogue(tag, v10.MODELS[tag]["primary_block"], 0)
    uids_all = [r["uid"] for r in F["rows"]] + [m["uid"] for m in meta_c]
    lab_all = list(F["cell"]) + _lab
    cnt = Counter(lab_all)
    uids = [u for u, lb in zip(uids_all, lab_all) if cnt[lb] >= v10.CLASS_FLOOR]
    out = {}
    classes = sorted(set(labels.tolist()))
    for i, u in enumerate(uids):
        best, bd = None, np.inf
        for c in classes:
            sel = labels == c
            sel[i] = False
            if sel.any():
                d = float(geo[i, sel].mean())
                if d < bd:
                    best, bd = c, d
        out[u] = best
    return out


def e0_nearest_cell(tag: str = "8b") -> dict[str, str]:
    import analysis

    F = analysis.factorial(tag)
    E = F["E0"].astype(np.float64)
    E = E / np.linalg.norm(E, axis=1, keepdims=True)
    cells = F["cell"]
    out = {}
    for i, r in enumerate(F["rows"]):
        best, bd = None, np.inf
        for c in sorted(set(cells.tolist())):
            sel = cells == c
            sel[i] = False
            d = float(np.mean(1 - E[sel] @ E[i]))
            if d < bd:
                best, bd = c, d
        out[r["uid"]] = best
    return out


def method_out() -> dict[str, Any]:
    import cells as cellmod

    near = {t: frame_nearest(t) for t in TAGS}
    e0n = e0_nearest_cell("8b")
    fac = v10.read_jsonl(v10.DATA / "factorial_set.jsonl")
    ex_f = []
    for r in fac:
        p = cellmod.cell_prompt(r["cell"], int(r["uid"].split("|")[2])) if r["uid"].count("|") >= 2 else None
        ex = {"input": f"CELL {r['cell']} ({cellmod.DISC_LONG[r['discipline']]} x {r['container']}); prompt:\n" +
                       (p["prompt"] if p else ""),
              "output": r["scrubbed"],
              "predict_nearest_class_8b": str(near["8b"].get(r["uid"])),
              "predict_nearest_class_32b": str(near["32b"].get(r["uid"])),
              "predict_nearest_cell_E0_baseline": str(e0n.get(r["uid"])),
              "metadata_uid": r["uid"], "metadata_cell": r["cell"], "metadata_discipline": r["discipline"],
              "metadata_container": r["container"], "metadata_heur_key": r.get("heur_key"),
              "metadata_wording": r.get("wording"), "metadata_repair": bool(r.get("repair")),
              "metadata_hand_read": r.get("hand_read"), "metadata_context_variant": r["context_variant"],
              "metadata_code_sha256": r["code_sha256"]}
        ex_f.append(ex)
    tops = v10.read_jsonl(v10.DATA / "topups_set.jsonl")
    ex_t = [{"input": f"TOP-UP class {r['cell']} ({r.get('wording')}); source {r.get('source')}",
             "output": r["scrubbed"], "predict_nearest_class_8b": str(near["8b"].get(r["uid"])),
             "predict_nearest_class_32b": str(near["32b"].get(r["uid"])), "metadata_uid": r["uid"],
             "metadata_class": r["cell"], "metadata_source": r.get("source"),
             "metadata_paraphrase_of": r.get("paraphrase_of"), "metadata_hand_read": r.get("hand_read")}
            for r in tops]
    placed = {r["uid"]: r for r in v10.read_jsonl(v10.DATA / "placed_programs.jsonl")}
    pl = {}
    for t in TAGS:
        p = v10.RESULTS / f"g2_{t}.json"
        if p.exists():
            pl[t] = {x["uid"]: x for x in v10.read_json(p)["placements_full"]}
    ex_p = []
    for u, r in placed.items():
        a, b = pl.get("8b", {}).get(u, {}), pl.get("32b", {}).get(u, {})
        ex_p.append({"input": f"PLACED program, family {r['family']} (source {r['source']}, config {r.get('config')}, "
                              f"author {r.get('author')}, label {r.get('label')}, name {r.get('other_name')})",
                     "output": r["scrubbed"],
                     "predict_nearest_class_8b": str(a.get("nearest_class")),
                     "predict_nearest_class_32b": str(b.get("nearest_class")),
                     "predict_landing_8b": str(a.get("class")), "predict_landing_32b": str(b.get("class")),
                     "metadata_uid": u, "metadata_family": r["family"], "metadata_g_8b": a.get("g"),
                     "metadata_g_32b": b.get("g"), "metadata_nearest_discipline_8b": a.get("nearest_discipline"),
                     "metadata_nearest_discipline_32b": b.get("nearest_discipline"),
                     "metadata_nearest_banned_8b": a.get("nearest_banned"),
                     "metadata_covert_kind": r.get("covert_kind"), "metadata_code_sha256": r["code_sha256"]})
    ex_g = []
    for t in TAGS:
        p = v10.RESULTS / f"g1_{t}.json"
        if not p.exists():
            continue
        d = v10.read_json(p)
        for key in ("primary", "S1_crossed_core"):
            r = d[key]
            for stat in ("rho_dc", "rho_cd", "delta"):
                ex_g.append({"input": f"G1 {t} {key} {stat} (block {d['block']} R1, partial Spearman, program "
                                      f"bootstrap CI, restricted permutations)",
                             "output": json.dumps({"value": r[stat], "ci95": r["bootstrap"][stat]["ci95"]}),
                             "predict_value": f"{r[stat]:.6f}", "metadata_model": t, "metadata_view": key,
                             "metadata_statistic": stat,
                             "metadata_perm_p": (r.get("perm_rho_dc") if stat == "rho_dc" else
                                                 r.get("perm_rho_cd") if stat == "rho_cd" else {}).get("p")
                             if stat != "delta" else None})
        for key in [k for k in d if k.startswith(("S3", "S4", "S5", "S6_readout", "S6_knn", "S7", "S10_without_r"))]:
            r = d[key]
            if isinstance(r, dict) and "rho_dc" in r:
                ex_g.append({"input": f"G1 {t} sensitivity {key}", "output": json.dumps(
                    {k: r[k] for k in ("rho_dc", "rho_cd", "delta") if k in r}),
                             "predict_value": f"{r['rho_dc']:.6f}", "metadata_model": t, "metadata_view": key,
                             "metadata_statistic": "rho_dc"})
    meta = {"method_name": "TP-G2: factorial discipline x container frame and survivor placement (iteration 10)",
            "artifact_plan": "gen_plan_experiment_5_idx5",
            "description": "Name-scrubbed grid path programs written by Qwen3-32B in a pre-committed 6x6 "
                           "discipline x container factorial (24 implementable cells, 12 verified programs each), "
                           "teacher-forced under iteration 9's neutral-twin context; program-state RDMs (Qwen3-8B bf16 "
                           "block 17, Qwen3-32B NF4 block 33, R1) tested for discipline vs container with partial "
                           "Spearman, restricted permutations and program bootstrap (G1); survivor families of the "
                           "five-name ban and covert BFS/DFS placed on the factorial + catalogue frame with iteration "
                           "9's geodesic landing code (G2).",
            "g1_verdict": v10.read_json(v10.RESULTS / "g1_verdict.json") if (v10.RESULTS / "g1_verdict.json").exists()
            else None,
            "g2": {t: {"families_full": v10.read_json(v10.RESULTS / f"g2_{t}.json")["families_full"],
                       "predictions": v10.read_json(v10.RESULTS / f"g2_{t}.json")["predictions"],
                       "frame_loo": v10.read_json(v10.RESULTS / f"g2_{t}.json").get("frame_loo")}
                   for t in TAGS if (v10.RESULTS / f"g2_{t}.json").exists()},
            "r0_reproduction": v10.read_json(v10.RESULTS / "r0_reproduction.json")["pass"],
            "robustness": v10.read_json(v10.RESULTS / "robustness.json") if (v10.RESULTS / "robustness.json").exists()
            else None,
            "placebos": v10.read_json(v10.RESULTS / "placebos.json") if (v10.RESULTS / "placebos.json").exists()
            else None,
            "audit_rederive_mismatches": v10.read_json(v10.RESULTS / "rederive.json")["n_mismatches"]
            if (v10.RESULTS / "rederive.json").exists() else None,
            "audit_rederive_g2": v10.read_json(v10.RESULTS / "rederive_g2.json")
            if (v10.RESULTS / "rederive_g2.json").exists() else None,
            "state_checks": {t: v10.read_json(v10.RESULTS / f"state_checks_{t}.json") for t in TAGS},
            "deviations": v10.read_json(v10.RESULTS / "deviations.json") if (v10.RESULTS / "deviations.json").exists()
            else [], "commitments": v10.verify_chain(),
            "openrouter_cost_usd": v10.read_json(v10.RESULTS / "costs_v10.json")["total_usd"],
            "hardware": v10.read_json(v10.PRED / "hardware.json") if (v10.PRED / "hardware.json").exists() else None,
            "engines": {"generation": "OpenRouter qwen/qwen3-32b provider=DeepInfra (thinking off)",
                        "states_8b": v10.M8["engine"], "states_32b": v10.M32["engine"]}}
    out = {"metadata": meta, "datasets": [{"dataset": "tpg2_factorial", "examples": ex_f},
                                          {"dataset": "tpg2_topups", "examples": ex_t},
                                          {"dataset": "tpg2_placements", "examples": ex_p},
                                          {"dataset": "tpg2_g1_rows", "examples": ex_g}]}
    (v10.ROOT / "method_out.json").write_text(json.dumps(out, indent=1, default=v10._default))
    return {"n": {d["dataset"]: len(d["examples"]) for d in out["datasets"]}}


def main() -> None:
    what = sys.argv[1:] or ["all"]
    if "all" in what or "placebos" in what:
        print("placebos", json.dumps(placebos(), default=str)[:600])
    if "all" in what or "verdict" in what:
        print("g1 verdict", g1_verdict())
    if "all" in what or "summary" in what:
        verification_summary()
        hardware()
    if "all" in what or "method_out" in what:
        print(method_out())


if __name__ == "__main__":
    main()
