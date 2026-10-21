#!/usr/bin/env python3
"""Stage A (CPU): input inventory + sha256 (predictions/e_inputs.json, committed), iteration-4 reference numbers under
this artifact's outcome definitions (results/iter4_reference.json), the prompt diff exp19 vs iteration 5
(results/prompt_diff.json), the unit table and the landing reference from exp24 (predictions/landing_ref.json)."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from loguru import logger

from cfg import TEMPLATE_IDS, V_BLOCKS, read_jsonl, rel, setup_logging, sha256_file, stable_seed, utc_now, write_json
from cfg_e import (DEFAULT_E, E19, E22, E23, E24, E27, INPUTS, K10, POP_SEEDS, PRED_DIR, RESULTS_DIR, ROOT)

TASKS = ("T10", "T2", "T03")


def inventory() -> dict[str, Any]:
    files = sorted(p for p in INPUTS.rglob("*") if p.is_file())
    return {rel(p): sha256_file(p) for p in files}


def e_inputs() -> dict[str, Any]:
    from sampling_v4 import load_norms

    prompts = {(r["task"], r["w"], r["kind"]): r for r in read_jsonl(ROOT / "data" / "prompts.jsonl")}
    out: dict[str, Any] = {"utc": utc_now(), "prompts": {}, "pn_seeds": {}, "units": {}, "directions": {},
                           "exp22_slots": "k 0-1 per template (W1-W5) -> N 10 per direction",
                           "hooks_sha256": sha256_file(ROOT / "src" / "hooks.py"),
                           "hooks_sha256_exp19": sha256_file(E19 / "src" / "hooks.py")}
    assert out["hooks_sha256"] == out["hooks_sha256_exp19"], "hooks.py differs from exp19's copy"
    for t in TASKS:
        nm = load_norms(t)
        for w in TEMPLATE_IDS:
            p = prompts[(t, w, "twin")]
            out["prompts"][f"{t}|{w}"] = {"prompt_sha256": p["prompt_sha256"], "p1": p["p1"],
                                          "spec_end": p["spec_end"], "P": p["P"], "segment": p["segment"]}
            assert nm.shape == (12, p["spec_end"] - p["p1"]), f"{t}/{w}: unit shape {nm.shape} != [12, |S|]"
            for arm in ("PN_a0.5", "PN_a1", "PN_a2"):
                out["pn_seeds"][f"{t}|{arm}|{w}"] = [stable_seed(t, arm, w, k) for k in K10]
        src = (ROOT / "inputs" / "exp17" / "directions" / f"norms_{t}.npy") if t == "T2" else \
            (ROOT / "inputs" / "exp13" / "results" / "tensors" / f"norms_{t}.npz")
        out["units"][t] = {"file": rel(src), "sha256": sha256_file(src), "shape": list(nm.shape),
                           "mean": float(nm.mean()), "per_block_mean": [float(x) for x in nm.mean(1)]}
    for s in POP_SEEDS:
        f = E22 / "directions" / f"rand_{s}.npy"
        out["directions"][str(s)] = sha256_file(f)
    rq = json.loads((E23 / "results" / "qwen_ratio.json").read_text())["r_Q"]
    out["r_Q"] = {l: rq[str(l)]["median"] for l in V_BLOCKS}
    out["engine_check_exp19_ids"] = [f"T2|{a}|{w}|{k}" for w in ("W1", "W2", "W3")
                                     for a in ("TWIN", "PN_a0.5", "PN_a1", "PN_a2") for k in K10]
    out["input_inventory_sha256"] = inventory()
    return out


def y_correct(r: dict[str, Any], cat: bool = False) -> int:
    bad = {DEFAULT_E[r["task"]], "invalid"} | ({"other"} if cat else set())
    return int(bool(r.get("passed")) and r.get("label") not in bad)


def iter4_reference() -> dict[str, Any]:
    from scipy import stats

    def cp(k: int, n: int) -> list[float]:
        lo = 0.0 if k == 0 else float(stats.beta.ppf(0.025, k, n - k + 1))
        hi = 1.0 if k == n else float(stats.beta.ppf(0.975, k + 1, n - k))
        return [lo, hi]

    rows = [r for r in read_jsonl(E19 / "data" / "samples.jsonl") if r["task"] in TASKS]
    out: dict[str, Any] = {"definition": "Y_correct = passed AND label not in {default, invalid}; Y_attempted = label "
                                         "not in {default, invalid}", "tasks": {}}
    for t in TASKS:
        out["tasks"][t] = {}
        for arm in ("TWIN", "PN_a0.5", "PN_a1", "PN_a2"):
            rs = [r for r in rows if r["task"] == t and r["arm"] == arm]
            n = len(rs)
            kc = sum(y_correct(r) for r in rs)
            kcc = sum(y_correct(r, True) for r in rs)
            ka = sum(r.get("label") not in (DEFAULT_E[t], "invalid") for r in rs)
            out["tasks"][t][arm] = {"N": n, "k_correct": kc, "Y_correct": kc / n, "Y_correct_cp95": cp(kc, n),
                                    "k_correct_catalogue": kcc, "k_attempted": ka, "Y_attempted": ka / n,
                                    "Y_attempted_cp95": cp(ka, n),
                                    "pass": sum(bool(r.get("passed")) for r in rs) / n,
                                    "composition": dict(Counter(r["label"] for r in rs))}
    out["note"] = ("exp19's published 0.60 (T10) / 0.54 (T2) are label-flip (attempted) shares; T2's correct-only "
                   "share is lower, and the like-for-like gate uses the correct-only counts recomputed here.")
    # exp22 per-direction counts (alpha 2, k 0-1)
    e22 = read_jsonl(E22 / "data" / "labels.jsonl")
    pd: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for r in e22:
        if r.get("task") in ("T10", "T2") and str(r.get("arm", "")).startswith("POP_d91") and \
                str(r["arm"]).endswith("_a2.0") and int(r.get("sample_id", 9)) in (0, 1):
            pd[r["task"]][r["arm"]].append(y_correct(r))
    out["exp22_population_alpha2"] = {t: {a: {"n": len(v), "k": sum(v)} for a, v in sorted(d.items())}
                                      for t, d in pd.items()}
    out["iter5_bf16_reference"] = iter5_reference()
    return out


def iter5_reference() -> dict[str, Any]:
    cells = json.loads((E27 / "results" / "cells.json").read_text())
    out = {}
    for t in TASKS:
        out[t] = {arm: {"N": cells[f"{t}|{arm}"]["N"],
                        "correct_only_off_default_share": cells[f"{t}|{arm}"]["correct_only_off_default_share"],
                        "off_default_share": cells[f"{t}|{arm}"]["off_default_share"],
                        "pass": cells[f"{t}|{arm}"]["pass"]}
                  for arm in ("TWIN", "PN_a1", "PN_a2") if f"{t}|{arm}" in cells}
    try:
        ea = json.loads((ROOT / "inputs" / "exp25" / "results" / "extra_arm_a.json").read_text())
        out["exp25_extra_arm_a"] = {t: {k: v for k, v in ea[t].items() if k in ("twin", "E1", "E2", "E")}
                                    for t in TASKS if t in ea}
    except (OSError, KeyError, json.JSONDecodeError) as e:
        out["exp25_extra_arm_a_error"] = str(e)
    return out


def prompt_diff() -> dict[str, Any]:
    e19 = {(r["task"], r["w"], r["kind"]): r for r in read_jsonl(E19 / "data" / "prompts.jsonl")}
    e27 = {(r["task"], r["w"], r["kind"]): r for r in read_jsonl(E27 / "prompts" / "prompts.jsonl")}
    out: dict[str, Any] = {"pairs": {}}
    n_same = n_tot = 0
    for t in TASKS:
        for w in TEMPLATE_IDS:
            a, b = e19.get((t, w, "twin")), e27.get((t, w, "twin"))
            if a is None or b is None:
                out["pairs"][f"{t}|{w}"] = {"missing": a is None and "exp19" or "exp27"}
                continue
            ia, ib = a["ids"], b["ids"]
            diff = [i for i in range(min(len(ia), len(ib))) if ia[i] != ib[i]]
            same = ia == ib
            n_same += same
            n_tot += 1
            out["pairs"][f"{t}|{w}"] = {"identical": same, "len_exp19": len(ia), "len_iter5": len(ib),
                                        "n_differing_positions": len(diff) + abs(len(ia) - len(ib)),
                                        "first_diff": diff[:10], "sha_exp19": a["prompt_sha256"],
                                        "sha_iter5": b["prompt_sha256"]}
    out["n_identical"] = n_same
    out["n_compared"] = n_tot
    out["conclusion"] = ("identical twin prompts: the 'prompt' explanation of the iteration-5 shrinkage is excluded"
                         if n_same == n_tot and n_tot else "prompts differ: see pairs")
    ur = json.loads((E27 / "results" / "unit_ratio.json").read_text())
    out["unit_ratio_iter5_banfree_over_ban"] = {t: ur[t]["banfree_over_ban_mean"] for t in TASKS if t in ur}
    return out


def landing_ref() -> dict[str, Any]:
    br = json.loads((E24 / "results" / "base_repertoire.json").read_text())["per_task"]
    out = {"r_u": {}, "q_base": {}, "source": "inputs/exp24/results/base_repertoire.json per_task[t]['r_t']"}
    for t in TASKS:
        d = br.get(t, {})
        out["r_u"][t] = d.get("r_t")
        out["q_base"][t] = d.get("base_chat", {}).get("composition_correct")
        out.setdefault("predicted_landing", {})[t] = d.get("predicted_landing")
    out["expected"] = {"T10": "dfs", "T2": "bellman_ford_spfa", "T03": "quickselect"}
    out["matches_expected"] = {t: (out["r_u"][t] or "").replace("bf_spfa", "bellman_ford_spfa") == v
                               for t, v in out["expected"].items()}
    return out


def main() -> None:
    from commit_e import commit

    setup_logging("stage_a")
    ei = e_inputs()
    write_json(PRED_DIR / "e_inputs.json", ei)
    commit([PRED_DIR / "e_inputs.json"], "stageA_inputs")
    ref = iter4_reference()
    write_json(RESULTS_DIR / "iter4_reference.json", ref)
    pdf = prompt_diff()
    write_json(RESULTS_DIR / "prompt_diff.json", pdf)
    lr = landing_ref()
    write_json(PRED_DIR / "landing_ref.json", lr)
    logger.info(f"Stage A: {len(ei['input_inventory_sha256'])} input files hashed; prompt diff {pdf['n_identical']}/"
                f"{pdf['n_compared']} identical; r_u {lr['r_u']}")
    for t in TASKS:
        logger.info(f"iter4 {t}: " + ", ".join(f"{a} {v['k_correct']}/{v['N']} (att {v['k_attempted']})"
                                               for a, v in ref["tasks"][t].items()))


if __name__ == "__main__":
    main()
