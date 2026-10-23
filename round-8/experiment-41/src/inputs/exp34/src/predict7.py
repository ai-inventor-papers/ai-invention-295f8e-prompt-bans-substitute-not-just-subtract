#!/usr/bin/env python3
"""Predictors and margins (P.1-P.4): GPU forward passes only, committed as commit #3 before any outcome row.

One teacher-forced pass per (cell, template[, sample]) over [prompt + cell prefill edit] + o_t[0:f_J]:
  - next-token distribution at each fork f_j -> e_j = sum_tok p q_j / sum_mapped p; P_esc = 1 - prod (1 - e_j)
  - for POP / fresh-direction cells also the spec-position states at blocks 12-35 (prompt positions are unaffected
    by the appended opening) -> delta_v = h_push - h_twin -> (b)_L, (a), pi_Pt, norm, per-position RMS at L_ax
P.3: 48-token opening LLR: log-mean-exp log p(first 48 tokens) of >= 5 correct base-path programs per class.
Cells: T10/T2 POP 9101-9140 a2 (tier 1), TWIN, BAN, PN_a1/PN_a2 (per sample), FORCED, FORCEDPAD, FORCEDX_0-35,
X_0-35, X_12-23 (tier 2), X_24-35, X_0-11, PLACEBO (tier 3); T03 TWIN, BAN, X_* and the 24 fresh directions.
Exchange cells (exp30 Stage A): spec-position block outputs of the source prompt written into the twin prefill
(gpu6.set_rows_edit) at the band's blocks; FORCEDX: forced -> padding twin at blocks 0-35.
"""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402
from loguru import logger  # noqa: E402

import c7 as common  # noqa: E402
from c7 import (CAP_BLOCKS, PRED, RESULTS, SEEDS40, SEEDS_T03, STATES, TEMPLATES, commit, read_json,  # noqa: E402
                setup_logging, stable_seed, utc_now, write_json)
import engine7 as E  # noqa: E402
import fork7 as F  # noqa: E402
import gen7 as G  # noqa: E402
import prompts7 as PR  # noqa: E402

BANDS = {"X_0-35": list(range(0, 36)), "X_12-23": list(range(12, 24)), "X_24-35": list(range(24, 36)),
         "X_0-11": list(range(0, 12))}
FORCED_X = {"T2": "bf_spfa", "T10": "bfs"}     # exp30 FORCED prompts (prompts4 named F0 v0)


class TaskModel:
    def __init__(self, model: Any, tok: Any, task: str, forks: dict[str, Any], axis: dict[str, Any]):
        self.model, self.tok, self.task = model, tok, task
        self.ctx = G.Ctx(model, task, PR.p4())
        self.fk = forks
        z = np.load(STATES / f"axis_{task}.npz")
        dev = self.ctx.dev
        self.a = torch.tensor(z["a"], device=dev)               # [24, D]
        self.Dbar = torch.tensor(z["Dbar"], device=dev)         # [24]
        self.U4 = torch.tensor(z["U4"], device=dev)
        self.Pt = torch.tensor(z["Pt"], device=dev)
        self.L_ax = int(z["L_ax"])
        self.li = CAP_BLOCKS.index(self.L_ax)
        self.status = forks.get("status")
        self.forks = [int(f) for f in forks.get("forks", [])]
        self.opening = forks.get("opening_ids", [])
        self.qmaps = []
        for j, f in enumerate(self.forks):
            m = forks["token_maps"][str(f)]
            ids = [int(k) for k, v in m.items() if v["mapped"]]
            # sequential multi-fork rule (commit1c): staying on the default path at an earlier fork is scored by the
            # later forks, so the default-path token's q is 0 there
            qs = [0.0 if (j < len(self.forks) - 1 and k == int(self.opening[f])) else m[str(k)]["q"] for k in ids]
            self.qmaps.append((torch.tensor(ids, device=dev, dtype=torch.long),
                               torch.tensor(qs, device=dev, dtype=torch.float64)))
        self.llr_progs = None

    # ------------------------------------------------------------------ one pass
    def run(self, rec: dict[str, Any], edits: dict | None, want_states: bool) -> dict[str, Any]:
        fJ = max(self.forks) if self.forks else 0
        ids = rec["ids"] + self.opening[:fJ]
        H: dict[int, torch.Tensor] = {}
        cap = E.capture_S(H, rec["p1"], rec["spec_end"], CAP_BLOCKS) if want_states else None
        out: dict[str, Any] = {}
        if self.forks:
            P = len(rec["ids"])
            lp = E.forward_lp(self.model, [ids], [P - 1 + f for f in self.forks], edits=edits, capture=cap)[0]
            es, unm = [], []
            for j, (tids, qs) in enumerate(self.qmaps):
                p = lp[j].double().exp()
                pm = p[tids]
                mass = float(pm.sum())
                es.append(float((pm * qs).sum() / max(mass, 1e-300)) if mass > 0 else float("nan"))
                unm.append(1.0 - mass)
            out["e"] = es
            out["unmapped"] = unm
            out["P_esc"] = 1.0 - float(np.prod([1.0 - e for e in es]))
            out["p_default_tok"] = [float(lp[j, self.opening[f]].exp()) for j, f in enumerate(self.forks)]
        elif want_states:
            E.forward_lp(self.model, [ids], [len(ids) - 1], edits=edits, capture=cap)
        if want_states:
            out["H"] = H
        return out

    def llr(self, rec: dict[str, Any], edits: dict | None) -> float | None:
        if not self.llr_progs:
            return None
        res = {}
        for c, progs in self.llr_progs.items():
            lps = E.seq_logprob(self.model, rec["ids"], progs, edits=edits, chunk=16)
            res[c] = float(np.logaddexp.reduce(lps) - math.log(len(lps)))
        d = common.DEFAULTS[self.task]
        non = [v for c, v in res.items() if c != d]
        if d not in res or not non:
            return None
        return float(np.logaddexp.reduce(non) - res[d])

    # ------------------------------------------------------------------ predictors from states
    def predictors(self, w: str, H: dict[int, torch.Tensor]) -> dict[str, Any]:
        tw = self.ctx.twin(w)
        d = torch.stack([H[l] - tw["S"][l] for l in CAP_BLOCKS])          # [24, nS, D]
        proj = torch.einsum("lsd,ld->ls", d, self.a).mean(1)              # [24]
        b = (proj / self.Dbar).tolist()
        dbar = d.mean(1)                                                  # [24, D]
        x = dbar[self.li]
        nx = float(x.pow(2).sum())
        eU = float((self.U4.T @ x).pow(2).sum())
        eP = float((self.Pt.T @ x).pow(2).sum())
        rms = float(d[self.li].norm(dim=-1).pow(2).mean().sqrt())
        return {"b": b, "a_share": eU / max(nx, 1e-12), "a_abs": eU, "pi_Pt": eP / max(nx, 1e-12),
                "norm": math.sqrt(nx), "rms_pos_Lax": rms, "dbar": dbar.half().cpu().numpy()}


# ------------------------------------------------------------------------------------------------ cell edits
def pop_edits(tm: TaskModel, w: str, seed: int, alpha: float = 2.0, u: np.ndarray | None = None) -> dict:
    from ctx4 import ban_unit, push_spec, rand_dir
    from hooks4 import make_edits_v4
    uu = rand_dir(seed) if u is None else u
    sp = push_spec(tm.ctx.dev, uu, ban_unit(tm.task), alpha)
    tw = tm.ctx.twin(w)
    return make_edits_v4("TARGET", tw["a"], tw["b"], sp["U"], sp["M"], {l: tw["S"][l] for l in sp["U"]})


def pn_u(task: str, arm: str, w: str, k: int) -> np.ndarray:
    seed = stable_seed(task, arm, w, k)
    x = np.random.Generator(np.random.PCG64(seed)).standard_normal(4096)
    return (x / np.linalg.norm(x)).astype(np.float32)


def capture_all(model: Any, rec: dict[str, Any]) -> dict[int, torch.Tensor]:
    """Spec-position block outputs (model dtype, exact) at blocks 0-35 of a prompt."""
    H: dict[int, torch.Tensor] = {}
    a, b = rec["p1"], rec["spec_end"]

    def mk(l: int) -> Callable:
        def g(h: torch.Tensor) -> None:
            H[l] = h[0, a:b].clone()
        return g
    E.prefill(model, rec["ids"], capture={l: mk(l) for l in range(36)})
    return H


def set_rows(a: int, b: int, src: dict[int, torch.Tensor], blocks: list[int]) -> dict:
    """exp30 gpu6.set_rows_edit: overwrite block-l outputs at spec positions with the source's exact values."""
    def mk(l: int) -> Callable:
        def f(h: torch.Tensor) -> torch.Tensor:
            h = h.clone()
            h[0, a:b] = src[l].to(h.dtype)
            return h
        return f
    return {l: mk(l) for l in blocks}


# ------------------------------------------------------------------------------------------------ driver
def run_task(model: Any, tok: Any, task: str, forks: dict[str, Any], axis: dict[str, Any], tiers: tuple[int, ...]
             ) -> tuple[list[dict[str, Any]], dict[str, np.ndarray]]:
    tm = TaskModel(model, tok, task, forks, axis)
    if forks.get("_llr_progs"):
        tm.llr_progs = forks["_llr_progs"]
    rows: list[dict[str, Any]] = []
    dbars: dict[str, np.ndarray] = {}
    t0 = time.time()

    def add(cell: str, w: str, rec: dict, edits: dict | None, family: str, states: bool = False,
            seed: int | None = None, k: int | None = None) -> None:
        r = tm.run(rec, edits, states)
        row = {"task": task, "cell": cell, "family": family, "template": w, "sample": k, "direction_seed": seed,
               "e": r.get("e"), "unmapped": r.get("unmapped"), "P_esc": r.get("P_esc"),
               "p_default_tok": r.get("p_default_tok"), "llr48": tm.llr(rec, edits)}
        if states:
            pr = tm.predictors(w, r["H"])
            dbars[f"{cell}|{w}"] = pr.pop("dbar")
            row.update({"b_L": pr["b"], "b": pr["b"][tm.li], "a_share": pr["a_share"], "a_abs": pr["a_abs"],
                        "pi_Pt": pr["pi_Pt"], "norm": pr["norm"], "rms_pos_Lax": pr["rms_pos_Lax"]})
            del r["H"]
        rows.append(row)

    seeds = SEEDS_T03 if task == "T03" else SEEDS40
    for w in TEMPLATES:
        tw = tm.ctx.twin(w)
        rec_t = tw["prompt"]
        add("TWIN", w, rec_t, None, "TWIN")
        for s in seeds:
            add(f"POP_d{s}_a2.0", w, rec_t, pop_edits(tm, w, s), "POP", states=True, seed=s)
        logger.info(f"{task}/{w}: TWIN + {len(seeds)} directions ({time.time() - t0:.0f}s)")
        if 2 in tiers:
            add("BAN", w, PR.ban(task, w), None, "BAN")
            Hb = capture_all(model, PR.ban(task, w))
            a, b = rec_t["p1"], rec_t["spec_end"]
            for band in (["X_0-35", "X_12-23"] + (["X_24-35", "X_0-11"] if 3 in tiers else [])):
                add(band, w, rec_t, set_rows(a, b, Hb, BANDS[band]), "STAGEA")
            if 3 in tiers:
                Hpl = capture_all(model, PR.p6(task, "placebo", w))
                add("PLACEBO", w, rec_t, set_rows(a, b, Hpl, BANDS["X_0-35"]), "STAGEA")
                del Hpl
            del Hb
            if task in ("T10", "T2"):
                for arm, alpha in (("PN_a1", 1.0), ("PN_a2", 2.0)):
                    for k in range(10):
                        add(arm, w, rec_t, pop_edits(tm, w, 0, alpha, u=pn_u(task, arm, w, k)), "PN", k=k)
    if 2 in tiers and task in ("T10", "T2"):
        fr = PR.named(task, FORCED_X[task], 0, 0)
        pad = PR.pad_record(tok, fr)
        add("FORCED", "F", fr, None, "FORCED")
        add("FORCEDPAD", "F", pad, None, "FORCED")
        Hf = capture_all(model, fr)
        add("FORCEDX_0-35", "F", pad, set_rows(pad["p1"], pad["spec_end"], Hf, BANDS["X_0-35"]), "FORCED")
        del Hf
    tm.ctx.release()
    E.free_cuda()
    logger.info(f"{task}: {len(rows)} margin rows in {time.time() - t0:.0f}s")
    return rows, dbars


def llr_programs(task: str, forks_task: dict[str, Any]) -> dict[str, list[list[int]]]:
    """>= 5 correct programs per class from the F1 base-path pools, truncated to a common opening length
    L = min(48, shortest pooled program) so classes are compared on equal-length openings (T03 default programs are
    shorter than 48 tokens)."""
    rows = {(p["src"], p["arm"], p["template"], int(p["sample_id"])): p for p in F.labelled_programs(task)}
    by: dict[str, list[list[int]]] = {}
    for bp in forks_task.get("base_paths", []):
        p = rows.get((bp["src"], bp["arm"], bp["template"], int(bp["sample_id"])))
        if p:
            by.setdefault(bp["class"], []).append(p["ids"])
    by = {c: v[:6] for c, v in by.items() if len(v) >= 5}
    if not by:
        return {}
    L = min(48, min(len(x) for v in by.values() for x in v))
    return {c: [x[:L] for x in v] for c, v in by.items()}


def aggregate(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per (task, cell): Pbar = equal-weight mean over templates of the template means (per-sample cells averaged
    within template first); m = logit(Pbar); predictor means over templates."""
    df = pd.DataFrame(rows)
    out: dict[str, dict[str, Any]] = {}
    for (task, cell), g in df.groupby(["task", "cell"]):
        gw = g.groupby("template")
        pt = gw["P_esc"].mean() if g["P_esc"].notna().any() else None
        eps = 1e-12
        if pt is not None:
            Pbar = float(pt.mean())
            Pc = min(max(Pbar, eps), 1 - eps)
            m = math.log(Pc) - math.log(1 - Pc)
            src = "fork margin"
        else:   # pre-declared fallback for a task with no single fork: the 48-token opening LLR is the margin
            m = float(gw["llr48"].mean().mean()) if g["llr48"].notna().any() else float("nan")
            Pbar = 1 / (1 + math.exp(-m)) if m == m else float("nan")
            src = "llr48 (no single fork)"
        rec = {"task": task, "cell": cell, "family": g["family"].iloc[0], "n_templates": int(gw.ngroups),
               "Pbar": Pbar, "m": m, "margin_source": src,
               "direction_seed": None if g["direction_seed"].isna().all() else int(g["direction_seed"].iloc[0])}
        if "llr48" in g and g["llr48"].notna().any():
            rec["llr48"] = float(gw["llr48"].mean().mean())
        if "e" in g and g["e"].notna().any():
            E_ = np.array([x for x in g["e"] if x is not None], dtype=float)
            if E_.size:
                rec["e_mean"] = np.nanmean(E_, axis=0).tolist()
            U_ = np.array([x for x in g["unmapped"] if x is not None], dtype=float)
            if U_.size:
                rec["unmapped_mean"] = np.nanmean(U_, axis=0).tolist()
        if "b" in g and g["b"].notna().any():
            for c in ("b", "a_share", "a_abs", "pi_Pt", "norm", "rms_pos_Lax"):
                rec[c] = float(g[c].mean())
            rec["b_L"] = np.mean(np.stack([np.array(x) for x in g["b_L"] if x is not None]), axis=0).tolist()
        out[f"{task}|{cell}"] = rec
    return out


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiers", default="1,2,3")
    ap.add_argument("--tasks", default="T10,T2,T03")
    ap.add_argument("--merge", action="store_true")
    args = ap.parse_args()
    tiers = tuple(int(x) for x in args.tiers.split(","))
    setup_logging("predict7")
    fk_file = common.forks_path()
    forks = read_json(fk_file)["tasks"]
    logger.info(f"fork definitions from {fk_file.name}")
    axis = read_json(PRED / "commit2_axis.json")
    tok, model = E.load()
    rows_all = []
    if args.merge and (RESULTS / "predictors.parquet").exists():
        old = pd.read_parquet(RESULTS / "predictors.parquet")
        keep = old[~old["task"].isin(args.tasks.split(","))]
        rows_all = [{k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in r.items()}
                    for r in keep.to_dict("records")]
        logger.info(f"merge: kept {len(rows_all)} rows of tasks {sorted(set(keep['task']))}")
    for task in args.tasks.split(","):
        fk = dict(forks[task])
        fk["_llr_progs"] = llr_programs(task, forks[task])
        rows, dbars = run_task(model, tok, task, fk, axis.get(task, {}), tiers)
        rows_all += rows
        np.savez_compressed(STATES / f"dbar_{task}.npz", **{k.replace("|", "__"): v for k, v in dbars.items()})
    df = pd.DataFrame(rows_all)
    for c in ("b_L", "e", "unmapped", "p_default_tok"):
        if c in df:
            df[c] = df[c].apply(lambda x: None if x is None or (isinstance(x, float) and math.isnan(x)) else
                                list(map(float, x)))
    pq = RESULTS / "predictors.parquet"
    df.to_parquet(pq)
    agg = aggregate(rows_all)
    obj = {"name": "commit3_predictors", "utc": utc_now(), "tiers": tiers, "parquet_sha256": common.sha256_file(pq),
           "cells": agg, "L_ax": {t: axis[t]["L_ax"] for t in ("T10", "T2", "T03") if t in axis},
           "llr_programs": {t: {c: len(v) for c, v in llr_programs(t, forks[t]).items()} for t in forks},
           "rows_by_task": {t: int(sum(1 for r in rows_all if r["task"] == t)) for t in ("T10", "T2", "T03")},
           "note": "all predictor values fitted without outcome data; POP outcome rows of exp29 unopened until this "
                   "file exists (common.guarded_e29_rows)"}
    obj["fork_file"] = fk_file.name
    obj["llr_opening_len"] = {t: (len(next(iter(v.values()))[0]) if v else None)
                              for t, v in ((t, llr_programs(t, forks[t])) for t in forks)}
    name = "commit3b_predictors" if (PRED / "commit3_predictors.json").exists() else "commit3_predictors"
    if name == "commit3b_predictors":
        obj["amends"] = ("commit3_predictors read the superseded fork file commit1b (single T10 fork, q(' def') "
                         "pooled) instead of commit1c, and its T03 LLR fallback was NaN (default programs shorter "
                         "than 48 tokens). T10 and T03 recomputed (T2 rows reused unchanged) before any outcome row "
                         "was opened.")
    p = PRED / f"{name}.json"
    write_json(p, obj)
    logger.info(f"{name} -> {commit(name, p)}")


if __name__ == "__main__":
    main()
