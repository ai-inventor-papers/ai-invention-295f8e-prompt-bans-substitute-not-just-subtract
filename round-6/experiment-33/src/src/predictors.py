#!/usr/bin/env python3
"""Predictor table and COMMIT #1 (CPU; no push, plan-noise or transplant sample exists yet), plus the escape screen
helpers used by the confirmation stage.

Usage: python src/predictors.py draft    -> predictions/predictors_draft.json (D_u, r_u for the opening ladder)
       python src/predictors.py commit1  -> predictions/commit_E1.json + hash chain (needs the opening ladder)
"""

from __future__ import annotations

import collections
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (ALL_TASKS, ALPHAS, BAND, BENCH, BETA_DIVERSE, BETA_MOVABLE, CACHE_DIR, CYCLIC_ORDER, DATA_DIR,
                 DEFAULT_MIN_CORRECT, DEFAULT_SHARE, DIR_SEEDS, E23, EXT_DIR, IT_ID, IT_REV, MIN_CORRECT_BASE,
                 N_MASSIVE, PATH_TASKS, PRED_DIR, PT_ID, PT_REV, RESULTS_DIR, ROOT, SUITE, TEMPLATE_IDS, bench_paths,
                 read_json, read_jsonl, setup_logging, sha256_file, write_json)
import analysis_E as A
from regate_rules import EXTENDED_LABELS

bench_paths()
_LAB: dict[str, Any] = {}


# ------------------------------------------------------------------------------------------------ data access
def labels(refresh: bool = False) -> dict[str, dict[str, Any]]:
    if refresh or "x" not in _LAB:
        _LAB["x"] = {r["row_id"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl")}
    return _LAB["x"]


def rows(stage: str | None = None, task: str | None = None, arm: str | None = None) -> list[dict[str, Any]]:
    return [r for r in labels().values() if (stage is None or r.get("stage") == stage)
            and (task is None or r.get("task") == task) and (arm is None or r.get("arm") == arm)]


def catalogue(task: str) -> list[str]:
    import prompts as PG

    return list(PG.modes(task)) + [m for m in EXTENDED_LABELS.get(task, []) if m not in PG.modes(task)]


def twin_rows(t: str) -> list[dict[str, Any]]:
    return rows("twin", t, "twin")


# ------------------------------------------------------------------------------------------------ default + beta
def default_of(t: str) -> dict[str, Any]:
    cat = catalogue(t)
    tw = twin_rows(t)
    corr = [r for r in tw if r.get("passed") and r["label"] not in ("invalid", "disputed")]
    cnt = collections.Counter(r["label"] for r in corr)
    n_c = len(corr)
    out = {"n_twin": len(tw), "n_correct": n_c, "pass_rate": A.pass_rate(tw), "correct_counts": dict(cnt),
           "attempt_counts": dict(collections.Counter(r["label"] for r in tw))}
    if not cnt:
        return {**out, "D": None, "defaulted": False, "share": None, "reason": "no correct twin program"}
    top = max(cnt.values())
    tops = sorted(m for m, c in cnt.items() if c == top)
    lab = tops[0]
    share = top / n_c
    ok = lab in cat and share >= DEFAULT_SHARE and n_c >= DEFAULT_MIN_CORRECT and len(tops) == 1
    reason = None if ok else ("modal correct label is not a catalogue/extended label" if lab not in cat else
                              f"share {share:.2f} < {DEFAULT_SHARE}" if share < DEFAULT_SHARE else
                              f"{n_c} correct < {DEFAULT_MIN_CORRECT}" if n_c < DEFAULT_MIN_CORRECT else "tie")
    return {**out, "D": lab if ok else None, "modal_correct": lab, "share": share, "defaulted": ok,
            "reason": reason or "ok"}


def base_stats(t: str, D: str | None, prow: list[dict[str, Any]]) -> dict[str, Any]:
    """beta, r_u, q_base, Hill-1 from a set of pt rows."""
    cat = catalogue(t)
    surv = [m for m in cat if m != D]
    corr = [r for r in prow if r.get("passed") and r["label"] != "disputed"]
    n_c = len(corr)
    cc = collections.Counter(r["label"] for r in corr)
    ac = collections.Counter(r["label"] for r in prow)
    low = n_c < MIN_CORRECT_BASE
    if not low:
        beta = sum(cc.get(m, 0) for m in surv) / n_c if n_c else None
        beta_excl_other = (sum(cc.get(m, 0) for m in surv) / max(n_c - cc.get("other", 0), 1)) if n_c else None
        src = "correct"
    else:
        valid = [r for r in prow if r["label"] not in ("disputed", "invalid")]
        beta = (sum(1 for r in valid if r["label"] in surv) / len(valid)) if valid else None
        nv = len([r for r in valid if r["label"] != "other"])
        beta_excl_other = (sum(1 for r in valid if r["label"] in surv) / nv) if nv else None
        src = "attempts (LOW_CORRECT)"
    # r_u: argmax over catalogue minus D of the primary counts (correct counts; LOW_CORRECT: valid-attempt counts),
    # ties -> attempt count -> frozen catalogue order; undefined if the top count is 0
    vc = collections.Counter(r["label"] for r in prow if r["label"] not in ("disputed", "invalid"))
    prim_c = vc if low else cc
    ranked = sorted(surv, key=lambda m: (-prim_c.get(m, 0), -ac.get(m, 0), cat.index(m)))
    r_u = ranked[0] if ranked and prim_c.get(ranked[0], 0) > 0 else None
    q = {m: prim_c.get(m, 0) + 0.5 for m in surv}
    tot = sum(q.values())
    q = {m: v / tot for m, v in q.items()} if tot else {}
    hill = A.hill1_rarefied([r["label"] for r in corr], depth=25, n_sub=1000, seed=0) if n_c >= 2 else None
    return {"n_rows": len(prow), "n_correct": n_c, "pass_rate": A.pass_rate(prow), "beta": beta,
            "beta_excl_other": beta_excl_other, "beta_source": src, "low_correct": low, "r_u": r_u,
            "q_base": q, "base_hill1_d25": hill, "hill_flag_lt25": n_c < 25, "correct_counts": dict(cc),
            "attempt_counts": dict(ac),
            "format_failure_rate": (sum(1 for r in prow if r["label"] == "invalid") / len(prow)) if prow else None,
            "finish_reasons": dict(collections.Counter(r.get("finish_reason") for r in prow))}


def cls_of(beta: float | None) -> str | None:
    if beta is None:
        return None
    if beta < BETA_MOVABLE:
        return "COLLAPSED"
    if beta >= BETA_DIVERSE:
        return "DIVERSE"
    return "INTERMEDIATE"


# ------------------------------------------------------------------------------------------------ rivals
def novelty_off(t: str, D: str | None) -> dict[str, Any]:
    rr = rows("novelty", t, "novelty")
    if not rr or D is None:
        return {"off_cat": None, "pass": A.pass_rate(rr) if rr else None, "n": len(rr)}
    return {"off_cat": A.off_cat(rr, D, catalogue(t)), "off_corr": A.off_corr(rr, D, catalogue(t)),
            "pass": A.pass_rate(rr), "n": len(rr), "composition": A.composition(rr, correct_only=False)}


def reference_program(t: str, mode: str) -> Path | None:
    if t in PATH_TASKS:
        sub = {"T1": "t1_grid", "T2": "t2_wsp"}[t]
        pref = {"T1": {"bfs": ["bfs_"], "dfs": ["dfs_"], "bibfs": ["bibfs_"], "iddfs": ["iddfs_"],
                       "astar_gbfs": ["astar", "gbfs"], "dijkstra": ["dijkstra_"]},
                "T2": {"bf_spfa": ["spfa", "bellman"], "bidijkstra": ["bidijkstra_"], "dial": ["dial_"],
                       "dijkstra": ["dijkstra_lazy", "dijkstra_"], "floyd": ["floyd_"]}}[t].get(mode, [])
        for pfx in pref:
            c = sorted((SUITE / "tasks" / sub / "references").glob(f"{pfx}*.py"))
            if c:
                return c[0]
        return None
    if t in EXTENDED_LABELS and mode in EXTENDED_LABELS[t]:
        p = EXT_DIR / t / f"{mode}.py"
        return p if p.exists() else None
    from bench.common.catalogue import TASKS

    p = BENCH / TASKS[t]["task_id"] / "references" / f"{mode}.py"
    return p if p.exists() else None


_RT_CACHE = RESULTS_DIR / "reference_times.json"


def time_reference(t: str, path: Path, reps: int = 3) -> float | None:
    """Cached wrapper of _time_reference (results/reference_times.json, keyed by task and reference file)."""
    cache = read_json(_RT_CACHE) if _RT_CACHE.exists() else {}
    key = f"{t}|{path.name}"
    if key not in cache:
        cache[key] = _time_reference(t, path, reps)
        write_json(_RT_CACHE, cache)
    return cache[key]


def _time_reference(t: str, path: Path, reps: int = 3) -> float | None:
    """Sum of per-case hidden-test times (bench harness) or the wall time of the suite test run (T1/T2); median."""
    code = path.read_text()
    vals = []
    for _ in range(reps):
        if t in PATH_TASKS:
            from tasks.harness import run_tests

            t0 = time.time()
            r = run_tests({"T1": "t1", "T2": "t2"}[t], code)
            if not r.get("passed"):
                return None
            vals.append(time.time() - t0)
        else:
            from bench.common.catalogue import TASKS
            from bench.common.harness import run_tests as brt
            from bench.common.testgen import read_tests

            cases = read_tests(BENCH / TASKS[t]["task_id"] / "tests.jsonl")
            r = brt(code, t, cases)
            if not r.get("passed"):
                return None
            vals.append(float(np.nansum([x for x in r["times"] if x is not None])))
    return float(np.median(vals))


def merit_gap(t: str, D: str | None, r_u: str | None) -> dict[str, Any]:
    import prompts as PG

    if D is None:
        return {"defined": False}
    cat = catalogue(t)
    pd = reference_program(t, D)
    cand = r_u
    fallback = False
    if cand is None or reference_program(t, cand) is None:
        fallback = True
        times = {m: time_reference(t, reference_program(t, m)) for m in cat if m != D and reference_program(t, m)}
        times = {m: v for m, v in times.items() if v is not None}
        cand = min(times, key=times.get) if times else None
    pr = reference_program(t, cand) if cand else None
    if pd is None or pr is None:
        return {"defined": False, "D": D, "r": cand}
    tD, tR = time_reference(t, pd), time_reference(t, pr)
    tok = PG.tokenizer()
    lD = len(tok(pd.read_text(), add_special_tokens=False)["input_ids"])
    lR = len(tok(pr.read_text(), add_special_tokens=False)["input_ids"])
    return {"defined": tD is not None and tR is not None, "D": D, "r": cand, "fallback_fastest_nondefault": fallback,
            "ref_D": pd.name, "ref_r": pr.name, "time_D_s": tD, "time_r_s": tR,
            "runtime_ratio": (tR / tD) if (tD and tR) else None, "token_len_D": lD, "token_len_r": lR,
            "token_ratio": lR / lD}


# ------------------------------------------------------------------------------------------------ transplant set-up
def massive_set() -> dict[str, Any]:
    import torch

    idx: set[int] = set()
    shares = []
    for t in ALL_TASKS:
        for w in TEMPLATE_IDS:
            d = torch.load(CACHE_DIR / f"hit_{t}_{w}.pt")
            S = d["S"].float()                                   # [12, S, D]
            top = S.abs().topk(N_MASSIVE, dim=-1).indices        # [12, S, 5]
            idx |= set(int(i) for i in top.flatten().unique().tolist())
    M = sorted(idx)
    for t in ALL_TASKS:
        for w in TEMPLATE_IDS:
            d = torch.load(CACHE_DIR / f"hit_{t}_{w}.pt")
            S2 = d["S"].float() ** 2
            shares.append(float((S2[..., M].sum(-1) / S2.sum(-1)).mean()))
    return {"M": M, "size": len(M), "share_of_h2_mean": float(np.mean(shares)), "share_of_h2_min": float(np.min(shares))}


def transplant_norms(M: list[int], tasks: list[str]) -> dict[str, Any]:
    """Per block: median and IQR of ||d_ox[l,p]|| / n[l,p] (ban-free units) and ||d_M||^2 / ||d||^2."""
    import torch
    from units import r_at

    Mm = torch.zeros(2560, dtype=torch.bool)
    Mm[torch.tensor(M)] = True
    per_block = {l: {"ratio": [], "mshare": [], "d_norm": []} for l in BAND}
    per_task = {}
    for t in tasks:
        vals = []
        for w in TEMPLATE_IDS:
            hi = torch.load(CACHE_DIR / f"hit_{t}_{w}.pt")
            hp = torch.load(CACHE_DIR / f"hpt_{t}_{w}.pt")
            for i, l in enumerate(BAND):
                Si, Sp = hi["S"][i].float(), hp["S"][i].float()
                d = Sp - Si
                sq = Si ** 2
                hox = (sq.sum(-1) - sq.topk(N_MASSIVE, dim=-1).values.sum(-1)).clamp(min=1e-12).sqrt()
                n = r_at(l, "r_Q_ox") * hox
                dox = (d * (~Mm)).norm(dim=-1)
                ratio = (dox / n).numpy()
                ms = ((d[:, Mm] ** 2).sum(-1) / (d ** 2).sum(-1).clamp(min=1e-12)).numpy()
                per_block[l]["ratio"] += ratio.tolist()
                per_block[l]["mshare"] += ms.tolist()
                per_block[l]["d_norm"] += d.norm(dim=-1).numpy().tolist()
                vals += ratio.tolist()
        per_task[t] = {"median_units": float(np.median(vals))}
    out = {}
    for l, v in per_block.items():
        r = np.array(v["ratio"])
        out[str(l)] = {"median_units": float(np.median(r)), "iqr": [float(np.percentile(r, 25)), float(np.percentile(r, 75))],
                       "massive_share_median": float(np.median(v["mshare"])), "d_norm_median": float(np.median(v["d_norm"]))}
    allr = np.concatenate([np.array(v["ratio"]) for v in per_block.values()])
    return {"per_block": out, "per_task": per_task, "overall_median_units": float(np.median(allr)),
            "caveat_gt_4_units": bool(np.median(allr) > 4.0),
            "note": "random-noise breakage dose in iteration 4 was about 4 ban-free units"}


def donor_map() -> dict[str, str]:
    order = list(CYCLIC_ORDER)
    return {u: order[(i + 1) % len(order)] for i, u in enumerate(order)}


# ------------------------------------------------------------------------------------------------ escape (stage 2)
def commit_e1() -> dict[str, Any]:
    return read_json(PRED_DIR / "commit_E1.json")


def cells(t: str, stage: str) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for r in rows(stage, t):
        if str(r.get("arm", "")).startswith("esc"):
            s, a = r["arm"][3:].split("_a")
            out[f"{s}_a{a}"].append(r)
    return dict(out)


def stage1(t: str, kind: str = "cat") -> dict[str, Any]:
    c1 = commit_e1()
    u = c1["units"][t]
    if not u["defaulted"]:
        return {"passing": [], "note": "NO_DEFAULT"}
    labels(refresh=True)
    res = A.escape_unit(twin_rows(t), cells(t, "push"), {}, u["D"], u["catalogue"], len(DIR_SEEDS), ALPHAS, kind)
    passing = [(int(k.split("_a")[0]), float(k.split("_a")[1])) for k in res["passing"]]
    return {**res, "passing": passing}


# ------------------------------------------------------------------------------------------------ table
def build_table(ladder: dict[str, Any] | None) -> dict[str, Any]:
    labels(refresh=True)
    units: dict[str, Any] = {}
    for t in ALL_TASKS:
        dflt = default_of(t)
        D = dflt["D"]
        chat = rows("ptchat", t, "pt_chat")
        plain = rows("ptplain", t, "pt_plain")
        units[t] = {"task": t, "catalogue": catalogue(t), "K": len(catalogue(t)), "default": dflt, "D": D,
                    "defaulted": dflt["defaulted"], "pt_chat": base_stats(t, D, chat),
                    "pt_plain": base_stats(t, D, plain), "pt_pooled": base_stats(t, D, chat + plain)}
    defaulted = [t for t in ALL_TASKS if units[t]["defaulted"]]
    n_ok = sum(1 for t in defaulted if units[t]["pt_chat"]["n_correct"] >= MIN_CORRECT_BASE)
    gate = {"n_defaulted": len(defaulted), "n_defaulted_with_ge20_correct_ptchat": n_ok,
            "pass": n_ok >= 8, "primary": "pt_chat" if n_ok >= 8 else "pt_pooled",
            "rule": "fewer than 8 defaulted units with >= 20 correct pt-chat programs -> pooled chat + plain"}
    prim = gate["primary"]
    for t in ALL_TASKS:
        u = units[t]
        b = u[prim]
        u["primary_source"] = prim
        u["beta"], u["r_u"], u["q_base"] = b["beta"], b["r_u"], b["q_base"]
        u["low_correct"] = b["low_correct"]
        u["class"] = cls_of(b["beta"]) if u["defaulted"] else None
        u["predicted_movable"] = (b["beta"] is not None and b["beta"] >= BETA_MOVABLE) if u["defaulted"] else None
        u["base_hill1_d25"] = b["base_hill1_d25"]
        tw = twin_rows(t)
        cnt = collections.Counter(r["label"] for r in tw)
        u["rivals"] = {"twin_modal_share": (cnt.most_common(1)[0][1] / len(tw)) if tw else None,
                       "novelty": novelty_off(t, u["D"])}
        u["rivals"]["novelty_off_cat"] = u["rivals"]["novelty"]["off_cat"]
        lad = (ladder or {}).get(t) or {}
        u["rivals"]["opening_margin"] = lad.get("margin_D_vs_r")
        u["rivals"]["opening_margin_vs_best_survivor"] = lad.get("margin_D_vs_best")
        u["rivals"]["merit_gap"] = merit_gap(t, u["D"], u["r_u"]) if u["defaulted"] else {"defined": False}
        u["chat_vs_plain_agreement"] = {
            "beta_chat": u["pt_chat"]["beta"], "beta_plain": u["pt_plain"]["beta"],
            "r_chat": u["pt_chat"]["r_u"], "r_plain": u["pt_plain"]["r_u"],
            "same_r": u["pt_chat"]["r_u"] == u["pt_plain"]["r_u"]}
    S_T = [t for t in defaulted if (units[t]["beta"] or 0) >= BETA_DIVERSE]
    descriptive = False
    if len(S_T) < 3:
        S_T = [t for t in defaulted if (units[t]["beta"] or 0) >= BETA_MOVABLE]
        descriptive = True
    col = [t for t in defaulted if units[t]["class"] == "COLLAPSED"]
    S_C = sorted(col, key=lambda t: (-units[t]["default"]["pass_rate"], CYCLIC_ORDER.index(t)))[:3]
    return {"units": units, "defaulted": defaulted, "pt_chat_validity_gate": gate, "S_T": S_T, "S_C": S_C,
            "transplant_descriptive": descriptive}


def pt_weight_hashes() -> dict[str, Any]:
    from huggingface_hub import HfApi

    out = {}
    for mid, rev in ((PT_ID, PT_REV), (IT_ID, IT_REV)):
        info = HfApi().model_info(mid, revision=rev, files_metadata=True)
        meta = {s.rfilename: (s.lfs.sha256 if s.lfs else None) for s in info.siblings}
        snap = Path(os.environ["HF_HUB_CACHE"]) / ("models--" + mid.replace("/", "--")) / "snapshots" / rev
        files = {}
        for f in sorted(snap.glob("*.safetensors")):
            blob = Path(os.path.realpath(f)).name
            files[f.name] = {"blob_sha256": blob, "repo_lfs_sha256": meta.get(f.name), "match": blob == meta.get(f.name)}
        out[mid] = {"revision": rev, "sha_api": info.sha, "files": files, "all_match": all(v["match"] for v in files.values())}
    return out


def grep_audit() -> dict[str, Any]:
    import prompts as PG

    reg = read_jsonl(DATA_DIR / "prompts_fed.jsonl")
    return PG.grep_audit([(r["kind"], r["text"]) for r in reg], list(ALL_TASKS))


def main() -> None:
    cmd = sys.argv[1]
    setup_logging(f"predictors_{cmd}")
    from loguru import logger

    if cmd == "draft":
        tab = build_table(None)
        slim = {t: {"D": u["D"], "r_u": u["r_u"], "beta": u["beta"], "defaulted": u["defaulted"],
                    "catalogue": u["catalogue"], "class": u["class"], "n_correct_pt_chat": u["pt_chat"]["n_correct"],
                    "n_correct_pt_plain": u["pt_plain"]["n_correct"], "default_share": u["default"]["share"],
                    "modal_correct": u["default"].get("modal_correct"), "beta_chat": u["pt_chat"]["beta"],
                    "beta_plain": u["pt_plain"]["beta"], "beta_pooled": u["pt_pooled"]["beta"]}
                for t, u in tab["units"].items()}
        write_json(PRED_DIR / "predictors_draft.json", {"units": slim, "gate": tab["pt_chat_validity_gate"],
                                                         "S_T": tab["S_T"], "S_C": tab["S_C"]})
        for t, v in slim.items():
            logger.info(f"{t}: {v}")
        logger.info(f"gate {tab['pt_chat_validity_gate']}; S_T {tab['S_T']}; S_C {tab['S_C']}")
        return
    if cmd == "commit1":
        from commit import commit, verify_chain

        ladder = read_json(RESULTS_DIR / "opening_ladder.json") if (RESULTS_DIR / "opening_ladder.json").exists() else None
        tab = build_table(ladder)
        ms = massive_set()
        tab["transplant"] = {"S_T": tab["S_T"], "S_C": tab["S_C"], "descriptive": tab["transplant_descriptive"],
                             "M": ms["M"], "M_size": ms["size"], "M_share_of_h2_mean": ms["share_of_h2_mean"],
                             "M_share_of_h2_min": ms["share_of_h2_min"], "donor": donor_map(),
                             "lambda": 1.0, "validity_switch": "lambda 0.5 if T pass < 0.8 x twin on > half of S_T"}
        tab["transplant_norms"] = transplant_norms(ms["M"], tab["S_T"] + tab["S_C"])
        tab["grep_audit"] = grep_audit()
        tab["weights"] = pt_weight_hashes()
        tab["models"] = {"it": [IT_ID, IT_REV], "pt": [PT_ID, PT_REV]}
        tab["exp23_rivals_for_E_A2"] = {"association": "inputs/exp23/predictions/commit_preban.json",
                                        "proximity": "inputs/exp23/results/proximity.json"}
        tab["note"] = ("committed BEFORE any push, plan-noise or transplant sample (no raw_push / raw_transplant file "
                       "exists at this time)")
        assert not (DATA_DIR / "raw_push.jsonl").exists() and not (DATA_DIR / "raw_transplant.jsonl").exists()
        assert tab["grep_audit"]["pass"], "ban frame found in a fed prompt"
        write_json(PRED_DIR / "commit_E1.json", tab)
        write_json(RESULTS_DIR / "predictors.json", tab)
        write_json(RESULTS_DIR / "transplant_norms.json", tab["transplant_norms"])
        rec = commit("commit1_predictors_before_any_push", [PRED_DIR / "commit_E1.json", ROOT / "src" / "analysis_E.py",
                                                             ROOT / "src" / "regate_rules.py",
                                                             ROOT / "src" / "label_worker.py",
                                                             RESULTS_DIR / "regate.json"]
                     + ([RESULTS_DIR / "opening_ladder.json"] if ladder else []),
                     note="predictor table, transplant sets, M, donors, grep audit, pt weights")
        logger.info(f"commit #1 {rec['hash'][:16]} at {rec['utc']}; chain {verify_chain()}")
        for t in ALL_TASKS:
            u = tab["units"][t]
            logger.info(f"{t}: D={u['D']} beta={u['beta']} r={u['r_u']} class={u['class']} "
                        f"rivals: modal={u['rivals']['twin_modal_share']} nov={u['rivals']['novelty_off_cat']} "
                        f"open={u['rivals']['opening_margin']}")
        logger.info(f"S_T={tab['S_T']} S_C={tab['S_C']} M size={ms['size']} share={ms['share_of_h2_mean']:.4f}")


def precompute_reference_times() -> None:
    for t in ALL_TASKS:
        for m in catalogue(t):
            p = reference_program(t, m)
            if p is not None:
                v = time_reference(t, p)
                print(t, m, p.name, v, flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "reftimes":
        precompute_reference_times()
    else:
        main()
