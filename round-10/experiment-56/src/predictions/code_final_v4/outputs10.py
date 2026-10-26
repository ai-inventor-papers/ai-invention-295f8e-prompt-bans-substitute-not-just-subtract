#!/usr/bin/env python3
"""method_out.json (exp_gen_sol_out schema). Datasets:
  w1_tf          one example per unit x prompt; output = m_B (base fork margin); predict_<arm> = the arm's margin
  w1_generation  one example per unit x CRN slot; output = TWIN 'label|pass'; predict_<arm> = 'label|pass'
  w2_tf          one example per unit x prompt; output = m_B; predict_<config> = margin under the weight swap
  w3_tf          one example per Gemma prompt; output = m_B; predict_<arm> = margin
metadata = every summary, verdict, commitment, deviation and cost.
"""

from __future__ import annotations

import re
from typing import Any

from loguru import logger

from cfg10 import (COMMITS, DATA_DIR, I9_RES, MODELS, RESULTS_DIR, ROOT, model_path, read_json, read_jsonl,
                   setup_logging, utc_now, verify_chain, write_json)


def key(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", s)


def user_text(tok: Any, ids: list[int]) -> str:
    s = tok.decode(ids)
    m = re.search(r"<\|im_start\|>user\n([\s\S]*?)<\|im_end\|>", s) or re.search(
        r"<start_of_turn>user\n([\s\S]*?)<end_of_turn>", s)
    return (m.group(1) if m else s).strip()


def main() -> None:
    from transformers import AutoTokenizer
    tq = AutoTokenizer.from_pretrained(model_path("qwen"))
    tg = AutoTokenizer.from_pretrained(model_path("gemma"))
    units = read_json(I9_RES / "units.json")
    datasets = []
    # ---------------- w1_tf
    rows = read_jsonl(RESULTS_DIR / "w1_tf_rows.jsonl")
    ex = []
    for u in ("T10", "B3"):
        U = units[u]
        f = U["forks"][0]
        byp = {p["pid"]: p for p in U["prompts"]}
        ur = [r for r in rows if r["unit"] == u]
        pids = list(dict.fromkeys(r["pid"] for r in ur))
        for pid in pids:
            pr = [r for r in ur if r["pid"] == pid]
            base = [r for r in pr if r["arm"] == "BASE"][0]
            e: dict[str, Any] = {"input": f"unit={u} prompt_id={pid} | task: {user_text(tq, byp[pid]['ids'])} | "
                                          f"opening: {f['opening_text']}",
                                 "output": f"{base['m_B']:.6f}"}
            for r in pr:
                if r["draw"] is None and r["arm"] != "BASE":
                    e[f"predict_{key(r['arm'])}"] = f"{r['m']:.6f}"
            for nt in ("RAND_ISO", "DELTA_SWAP", "RAND_RESID"):
                ms = sorted(r["m"] for r in pr if r["arm"] == nt)
                e[f"predict_{nt}_median_draw"] = f"{ms[len(ms) // 2]:.6f}"
            e["metadata_unit"] = u
            e["metadata_template"] = byp[pid]["template"]
            e["metadata_m_I"] = base["m_I"]
            e["metadata_gap"] = base["m_I"] - base["m_B"]
            e["metadata_D_tokens"] = f.get("D_str")
            e["metadata_A_tokens"] = f.get("A_str")
            ex.append(e)
    datasets.append({"dataset": "w1_tf", "examples": ex})
    # ---------------- w1_generation
    raw = read_jsonl(DATA_DIR / "gen_samples.jsonl")
    lab = {r["sid"]: r for r in read_jsonl(DATA_DIR / "gen_labels.jsonl")}
    ex = []
    for u in ("T10", "B3"):
        f = units[u]["forks"][0]
        byp = {p["pid"]: p for p in units[u]["prompts"]}
        slots = sorted({(r["template"], r["slot"], r["prompt_id"], r["seed"]) for r in raw if r["unit"] == u},
                       key=lambda x: x[1])
        for (w, s, pid, seed) in slots:
            rs = {r["arm"]: r for r in raw if r["unit"] == u and r["slot"] == s}
            if "TWIN" not in rs and "TWIN_EXTRA60" in rs:
                rs["TWIN"] = rs.pop("TWIN_EXTRA60")
            if "TWIN" not in rs:
                continue

            def lp(r: dict) -> str:
                L = lab.get(r["sid"], {})
                return f"{L.get('label')}|{'pass' if L.get('passed') else 'fail'}"
            e = {"input": f"unit={u} slot={s} seed={seed} prompt_id={pid} | task: {user_text(tq, byp[pid]['ids'])} | "
                          f"prefilled opening: {f['opening_text']}",
                 "output": lp(rs["TWIN"])}
            for a, r in rs.items():
                if a != "TWIN":
                    e[f"predict_{key(a)}"] = lp(r)
            e["metadata_unit"] = u
            e["metadata_template"] = w
            e["metadata_fork_tokens"] = {a: r["fork_token"] for a, r in rs.items()}
            e["metadata_n_tokens"] = {a: r["n_tokens"] for a, r in rs.items()}
            e["metadata_code_sha256"] = {a: r["code_sha256"] for a, r in rs.items()}
            ex.append(e)
    datasets.append({"dataset": "w1_generation", "examples": ex})
    # ---------------- w2_tf
    w2r = read_jsonl(RESULTS_DIR / "w2_rows.jsonl")
    if w2r:
        ex = []
        for u in ("T10", "B3"):
            byp = {p["pid"]: p for p in units[u]["prompts"]}
            ur = [r for r in w2r if r["unit"] == u]
            for pid in list(dict.fromkeys(r["pid"] for r in ur)):
                pr = {f"{r['scope']}_{r['config']}": r for r in ur if r["pid"] == pid}
                any_r = next(iter(pr.values()))
                e = {"input": f"unit={u} prompt_id={pid} | task: {user_text(tq, byp[pid]['ids'])}",
                     "output": f"{any_r['m_B']:.6f}"}
                for k, r in pr.items():
                    e[f"predict_{key(k)}"] = f"{r['m']:.6f}"
                    if "m_decomp_rows_norm" in r:
                        e[f"predict_{key(k)}_with_base_readout"] = f"{r['m_decomp_rows_norm']:.6f}"
                e["metadata_unit"] = u
                e["metadata_m_I"] = any_r["m_I"]
                ex.append(e)
        datasets.append({"dataset": "w2_tf", "examples": ex})
    # ---------------- w3_tf
    w3r = read_jsonl(RESULTS_DIR / "w3_rows.jsonl")
    if w3r:
        G = units["G-GRID"]
        byp = {p["pid"]: p for p in G["prompts"]}
        ex = []
        for pid in list(dict.fromkeys(r["pid"] for r in w3r)):
            pr = [r for r in w3r if r["pid"] == pid]
            e = {"input": f"unit=G-GRID@32 prompt_id={pid} | task: {user_text(tg, byp[pid]['ids'])} | opening: "
                          f"{G['forks'][0]['opening_text']}", "output": f"{pr[0]['m_B']:.6f}"}
            for r in pr:
                if r["draw"] is None:
                    e[f"predict_{key(r['arm'])}"] = f"{r['m']:.6f}"
            for nt in ("RAND_ISO", "DELTA_SWAP"):
                ms = sorted(r["m"] for r in pr if r["arm"] == nt)
                e[f"predict_{nt}_median_draw"] = f"{ms[len(ms) // 2]:.6f}"
            e["metadata_m_I"] = pr[0]["m_I"]
            ex.append(e)
        datasets.append({"dataset": "w3_tf", "examples": ex})
    # ---------------- metadata
    summ = read_json(RESULTS_DIR / "summary.json")
    meta = {
        "artifact": "iteration 10 BASE-W: which weights hold the default algorithm (Qwen3-8B vs Qwen3-8B-Base; "
                    "Gemma-3-4b descriptive)",
        "method_name": "exact readout-row restoration at the algorithm fork (W1, teacher forced and in generation) and "
                       "in-place late-MLP weight swaps (W2), each against matched-norm nulls",
        "baselines": ["TWIN (unmodified instruct readout)", "Fork-Patched Decoding (base fork logits; Cantarero et al.)",
                      "50 isotropic matched-norm random-row draws (RAND_ISO)", "50 delta-transplant draws (DELTA_SWAP)",
                      "50 residual-subspace random draws (RAND_RESID)", "Hungarian-matched early-MLP swaps",
                      "same-layer random weight deltas (RANDDELTA)"],
        "models": {k: {"id": v[0], "revision": v[1]} for k, v in MODELS.items()},
        "summary": summ, "w1_tf_summary_path": "results/w1_tf_summary.json",
        "commitments_log": COMMITS.read_text().splitlines(), "chain": verify_chain(),
        "not_run": {"T1_T2": "dropped (drop order position 2): the plan's single-position margin is degenerate at these "
                              "forks (every fork token has phat_off < 0.5, so the runner-up segment's first token is a "
                              "D token and A is a subset of D); the iteration-8 path margin is a different estimand",
                    "FULL_UNEMB_FORK": "not generated: committed TV(full base unembedding vs ROWS) at the fork = 0.0000 "
                                       "(T10) / 0.0005 (B3) < 0.05",
                    "novelty_judges": "no correct program labelled 'other' (USD 0)"},
        "dependency_check": {k: v for k, v in read_json(RESULTS_DIR / "depcheck_leetcode.json").items()
                             if k not in ("by_arm", "disagreements")}
        if (RESULTS_DIR / "depcheck_leetcode.json").exists() else None,
        "cost": {"openrouter_usd": 0.0, "gpu": "1 x RTX 4090 24 GB"}, "utc": utc_now()}
    out = {"metadata": meta, "datasets": datasets}
    write_json(ROOT / "method_out.json", out)
    logger.info(f"method_out.json: {[(d['dataset'], len(d['examples'])) for d in datasets]}")


if __name__ == "__main__":
    setup_logging("outputs10")
    main()
