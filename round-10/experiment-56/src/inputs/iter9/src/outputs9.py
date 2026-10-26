#!/usr/bin/env python3
"""S8 outputs: method_out.json in the exp_gen_sol_out schema.

Datasets: b1_forks (unit x fork x prompt x template mode; Gemma it/pt and Llama instruct/base), b2_tf (Qwen unit x
prompt with every arm's margin and share), b3_heldout (node x mode x held-out prompt). b2_generation is not produced
(S4 dropped; see metadata.not_run). Metadata holds every analysis summary, the commit chain, deviations and costs."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
from loguru import logger

from cfg9 import (MODELS, ROOT, RESULTS_DIR, model_path, read_json, read_jsonl, setup_logging, utc_now, verify_chain,
                  write_json)


def toks() -> dict[str, Any]:
    from transformers import AutoTokenizer
    return {"qwen": AutoTokenizer.from_pretrained(model_path("qwen")),
            "gemma": AutoTokenizer.from_pretrained(model_path("gemma")),
            "llama": AutoTokenizer.from_pretrained(model_path("llama"))}


def b1_examples(T: dict, U: dict) -> list[dict[str, Any]]:
    ex = []
    pairs = {"gemma": ("gemma", "gemma_pt"), "llama": ("llama", "llama_base")}
    summ = read_json(RESULTS_DIR / "b1_summary.json")
    for fam, (ki, kb) in pairs.items():
        pi, pb = RESULTS_DIR / f"b1_tf_{ki}.json", RESULTS_DIR / f"b1_tf_{kb}.json"
        if not (pi.exists() and pb.exists()):
            continue
        I, B = read_json(pi), read_json(pb)
        tk = T[fam]
        for u, ru in I["units"].items():
            Uu = U[u]
            su = summ["units"].get(u, {})
            kept = set(su.get("on_policy", {}).get("kept", []))
            byB = {r["pid"]: r for r in B["units"][u]["prompts"]}
            byP = {p["pid"]: p for p in Uu["prompts"]}
            for r in ru["prompts"]:
                p = byP[r["pid"]]
                for f in Uu["forks"]:
                    fid = f["fork_id"]
                    for mode in ("chat", "plain"):
                        a, b = r["forks"][fid][mode], byB[r["pid"]]["forks"][fid][mode]
                        ids = (p["ids"] if mode == "chat" else p["ids_plain"]) + f["opening"]
                        ex.append({
                            "input": tk.decode(ids),
                            "output": tk.decode([a["argmax"]]),
                            "predict_instruct_argmax": tk.decode([a["argmax"]]),
                            "predict_base_argmax": tk.decode([b["argmax"]]),
                            "metadata_family": fam, "metadata_unit": u, "metadata_fork_id": fid,
                            "metadata_prompt_id": r["pid"], "metadata_template_mode": mode,
                            "metadata_on_policy_kept": r["pid"] in kept,
                            "metadata_descriptive_only": bool(su.get("descriptive_only")),
                            "metadata_D_tokens": f["D_str"], "metadata_A_tokens": f["A_str"],
                            "metadata_margin_instr": a["margin"], "metadata_margin_base": b["margin"],
                            "metadata_gain": a["margin"] - b["margin"], "metadata_pD_instr": a["pD"],
                            "metadata_pD_base": b["pD"], "metadata_pA_instr": a["pA"], "metadata_pA_base": b["pA"],
                            "metadata_entropy_instr": a["entropy"], "metadata_entropy_base": b["entropy"],
                            "metadata_logp_opening_instr": a["logp_opening"],
                            "metadata_models": [MODELS[ki][0], MODELS[kb][0]]})
    return ex


def b2_examples(T: dict, U: dict) -> list[dict[str, Any]]:
    ex = []
    tk = T["qwen"]
    for u in ("B3", "T10"):
        rows = read_jsonl(RESULTS_DIR / f"b2_tf_{u}.jsonl")
        if not rows:
            continue
        b2s = read_json(RESULTS_DIR / "b2_summary.json")["units"][u]
        rsh = b2s["null_R"]["shares"]
        med = int(np.argsort(rsh)[len(rsh) // 2])
        by: dict[str, dict[str, dict]] = {}
        for r in rows:
            by.setdefault(r["pid"], {})[r["arm"]] = r
        f = U[u]["forks"][0]
        P = {p["pid"]: p for p in U[u]["prompts"]}
        base_cap = {r["pid"]: r for r in read_json(RESULTS_DIR / "capture_base.json")[u]}
        for pid, arms in by.items():
            mI, mB = arms["none"]["m_I"], arms["none"]["m_B"]
            gap = mI - mB

            def sh(a: str) -> float | None:
                return (mI - arms[a]["m"]) / gap if a in arms and abs(gap) > 1e-9 else None
            am = lambda a: tk.decode([arms[a]["dist"]["argmax"]]) if a in arms and "dist" in arms[a] else ""  # noqa
            ex.append({
                "input": tk.decode(P[pid]["ids"] + f["opening"]),
                "output": am("none"),
                "predict_instruct_unpatched": am("none"),
                "predict_FSTACK_patched": am("FSTACK"),
                "predict_median_random_set_patched": am(f"R{med}"),
                "predict_RSfork36_patched": am("RSfork36"),
                "predict_base_model": tk.decode([base_cap[pid]["argmax"]]),
                "metadata_unit": u, "metadata_prompt_id": pid, "metadata_template": P[pid]["template"],
                "metadata_D_tokens": f["D_str"], "metadata_A_tokens": f["A_str"],
                "metadata_m_I": mI, "metadata_m_B": mB, "metadata_gap": gap,
                "metadata_m_FSTACK": arms["FSTACK"]["m"], "metadata_share_FSTACK": sh("FSTACK"),
                "metadata_share_F_MLP": sh("F_MLP"), "metadata_share_F_HEAD": sh("F_HEAD"),
                "metadata_share_F_MST": sh("F_MST"), "metadata_share_F_CC": sh("F_CC"),
                "metadata_share_SPEC": sh("SPEC"), "metadata_share_RSfork23": sh("RSfork23"),
                "metadata_share_RSfork36": sh("RSfork36"), "metadata_share_RSprefix23": sh("RSprefix23"),
                "metadata_share_RSall23": sh("RSall23"), "metadata_share_W_all": sh("W_all"),
                "metadata_share_median_random_set": sh(f"R{med}"),
                "metadata_share_random_sets": [sh(f"R{s}") for s in range(50)],
                "metadata_self_patch_dm": arms["self_FSTACK"]["dm"],
                "metadata_identity_heads_minus_RS36": arms["ALL_heads"]["m"] - arms["RSfork36"]["m"]})
    return ex


def b3_examples() -> list[dict[str, Any]]:
    rows = read_jsonl(RESULTS_DIR / "b3_heldout_rows.jsonl")
    s = read_json(RESULTS_DIR / "b3_summary.json")
    ex = []
    for key, v in s["per_node"].items():
        tag = f"{v['variant']}|{v['mode']}|{v['node']}"
        for r in rows:
            node = r["res"].get(f"{tag}|node")
            rv = [r["res"][f"{tag}|r{j}"] for j in range(50) if f"{tag}|r{j}" in r["res"]]
            if node is None or not rv:
                continue
            ex.append({"input": f"C1forced held-out prompt {r['vid']} (art_18XvfcJJZi1O k3prompts.b3_forced) + the "
                                f"61-token MST opening; edit {v['mode']} of {v['node']} ({v['variant']} means)",
                       "output": r["side"],
                       "predict_node_oriented_dm": f"{node:.6f}",
                       "predict_random_mean_oriented_dm": f"{float(np.mean(rv)):.6f}",
                       "metadata_node": v["node"], "metadata_mode": v["mode"], "metadata_variant": v["variant"],
                       "metadata_prompt": r["vid"], "metadata_d": node - float(np.mean(rv)),
                       "metadata_frac_random_beaten": float(np.mean(np.asarray(rv) < node)),
                       "metadata_label": v["label"]})
    return ex


def gen_examples() -> list[dict[str, Any]]:
    raw = read_jsonl(ROOT / "data" / "samples.jsonl")
    lab = {r["sid"]: r for r in read_jsonl(ROOT / "data" / "labels_gen.jsonl")}
    by: dict[tuple, dict[str, dict]] = {}
    for r in raw:
        by.setdefault((r["task"], r["template"], r["slot"]), {})[r["arm"]] = r
    ex = []
    for (u, w, slot), arms in sorted(by.items()):
        if "TWIN" not in arms:
            continue
        def lp(a):
            if a not in arms or arms[a]["sid"] not in lab:
                return ""
            L = lab[arms[a]["sid"]]
            return f"{L['label']}|{'pass' if L['passed'] else 'fail'}"
        tw = arms["TWIN"]
        ex.append({"input": f"{u} prompt {tw['prompt_id']} (template {w}), CRN slot {slot} (seed {tw['seed']}); the "
                            f"instruct model's on-policy opening is prefilled; arms differ only at the fork token",
                   "output": lp("TWIN"), "predict_FSTACK": lp("FSTACK"), "predict_RAND": lp("RAND"),
                   "predict_FPD": lp("FPD"),
                   "metadata_unit": u, "metadata_template": w, "metadata_slot": slot, "metadata_seed": tw["seed"],
                   "metadata_fork_tokens": {a: arms[a]["fork_token"] for a in arms},
                   "metadata_n_tokens": {a: arms[a]["n_tokens"] for a in arms},
                   "metadata_code_TWIN": tw["text"]})
    return ex


def main() -> None:
    U = read_json(RESULTS_DIR / "units.json")
    T = toks()
    datasets = []
    for name, fn in (("b1_forks", lambda: b1_examples(T, U)), ("b2_tf", lambda: b2_examples(T, U)),
                     ("b3_heldout", b3_examples), ("b2_generation", gen_examples)):
        try:
            ex = fn()
        except FileNotFoundError as e:
            logger.error(f"{name}: {e}")
            ex = []
        if ex:
            datasets.append({"dataset": name, "examples": ex})
        logger.info(f"{name}: {len(ex)} examples")
    summ = read_json(RESULTS_DIR / "summary.json") if (RESULTS_DIR / "summary.json").exists() else {}
    timing = read_jsonl(RESULTS_DIR / "stage_timing.jsonl")
    meta = {
        "artifact": "iteration-9 BASE artifact (claims B1-B3): where instruction tuning sharpened the algorithm choice",
        "method_name": "teacher-forced base-vs-instruct fork margins (B1); cross-model activation patching at the "
                       "fork with matched random nulls and residual swaps (B2); interpolated-mean held-out rerun (B3)",
        "baselines": ["both unpatched anchors (instruct, base) on identical ids", "50 write-norm-matched random "
                      "component sets (R, R-pure, R-scaled)", "exhaustive single-component sweep (36 MLPs + 1152 "
                      "heads)", "SPEC (task-specification) set + 20 matched random SPEC sets",
                      "residual-stream swaps RS-fork / RS-prefix / RS-all (upper bounds)", "base-entropy-matched and "
                      "rate-matched random positions (Cantarero)", "template-free arm"],
        "models": {k: {"id": v[0], "revision": v[1]} for k, v in MODELS.items()},
        "b1": summ.get("b1_summary"), "b2_verdict": (summ.get("b2_summary") or {}).get("verdict"),
        "b2": {u: {k: v for k, v in r.items() if k not in ("singles", "per_prompt_share")}
               for u, r in ((summ.get("b2_summary") or {}).get("units") or {}).items()},
        "b2_v1_sensitivity": (summ.get("b2_summary") or {}).get("v1_variable_batch_sensitivity"),
        "b3": summ.get("b3_summary"), "commit_chain": verify_chain(), "deviations": summ.get("deviations"),
        "gpu_seconds_by_stage": timing, "gpu_hours_total": round(sum(t["seconds"] for t in timing) / 3600, 3),
        "openrouter_usd": 0.0,
        "b2_generation": read_json(RESULTS_DIR / "b2_generation.json")
        if (RESULTS_DIR / "b2_generation.json").exists() else None,
        "weight_change_S7a": read_json(RESULTS_DIR / "weight_change.json")
        if (RESULTS_DIR / "weight_change.json").exists() else None,
        "rederive": read_json(RESULTS_DIR / "rederive.json") if (RESULTS_DIR / "rederive.json").exists() else None,
        "positioning": read_json(RESULTS_DIR / "positioning.json")
        if (RESULTS_DIR / "positioning.json").exists() else None,
        "not_run": ["L-SP Llama shortest-path unit (second in the drop order)", "B2 T1 / T2 units (optional)",
                    "S7b optional Gemma CMAP unit (S7a weight-change profile was run)",
                    "token maps for unmapped base fork tokens (forced continuations); unmapped mass is reported",
                    "novelty audit judges: no correct generated program is labelled 'other' (none novel; rule-of-"
                    "three bound 3/237 = 0.013 on the novel-class rate among correct programs); USD 0 spent"],
        "utc": utc_now(),
    }
    out = {"metadata": meta, "datasets": datasets}
    write_json(ROOT / "method_out.json", out)
    logger.info(f"method_out.json: {sum(len(d['examples']) for d in datasets)} examples")


if __name__ == "__main__":
    setup_logging("outputs9")
    main()
