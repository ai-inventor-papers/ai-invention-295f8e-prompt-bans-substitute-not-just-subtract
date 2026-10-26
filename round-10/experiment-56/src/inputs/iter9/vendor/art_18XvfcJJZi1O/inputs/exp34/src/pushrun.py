#!/usr/bin/env python3
"""Generation stages after commit #3 (one model load, stages in order):

  t03      C.1 T03 confirmation: 24 fresh directions 97001-97024 x N = 10 (W1-W5 x k 0-1), alpha 2, absolute T03
           unit, push_spec at blocks 12-23 (predictions already committed in commit #3)
  targeted T.1 single-layer displacement-targeted edit at L_ax along a (AX_s) and along the matched random
           r_t = rand_dir(98001 + task index) with |s D| (RX_s), s in {0.1, 0.25, 0.5, 1}, N = 30 (k 0-5); the spec is
           committed (commit #4) before sampling
  top5     G.3 T1 in-manifold push: SURV / RSURV / AWAY at s in {0.25, 0.5, 1} and IDASTAR at 0.5, N = 30
  remeasure fallback 1 (engine mismatch at 0c): all 40 directions x N = 10 on T10 and T2 in this engine -> sealed
           data/samples_raw_s0b.jsonl
  clamp    P2-N: 4 confirmed escapers per task (largest y), N = 20 (k 0-3): POP unclamped (CLU), axis clamp at blocks
           L_ax..35 (CLA), matched random-direction clamp (CLR)
usage: python src/pushrun.py t03,targeted,top5,remeasure,clamp [--deadline-min N]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import torch  # noqa: E402
from loguru import logger  # noqa: E402

import c7 as common  # noqa: E402
from c7 import (CAP_BLOCKS, DATA, PRED, RESULTS, SEED_RAND_TARGET, SEEDS40, SEEDS_T03, STATES, TEMPLATES,  # noqa: E402
                commit, read_json, setup_logging, stable_seed, utc_now, write_json)
import engine7 as E  # noqa: E402
import gen7 as G  # noqa: E402
import prompts7 as PR  # noqa: E402

S_TARGET = (0.1, 0.25, 0.5, 1.0)
S_TARGET_EXT = (2.0, 4.0, 8.0)   # fallback 8 (no escape at s <= 1): descriptive doses to locate the crossing
S_TOP5 = (0.25, 0.5, 1.0)
S0B_RAW = DATA / "samples_raw_s0b.jsonl"
CLAMP_RAW = DATA / "samples_raw_clamp.jsonl"
TOP5_STATES = STATES / "top5_T1_states.npz"


def axis(task: str, dev: torch.device) -> dict[str, Any]:
    z = np.load(STATES / f"axis_{task}.npz")
    L = int(z["L_ax"])
    li = CAP_BLOCKS.index(L)
    return {"L": L, "a": torch.tensor(z["a"][li], device=dev), "D": torch.tensor(z["D"][li], device=dev),
            "a_all": torch.tensor(z["a"], device=dev)}


# ------------------------------------------------------------------------------------------------ arms
def targeted_arm(task: str, s: float, kind: str, ax: dict[str, Any]) -> G.Arm:
    """AX: u = a_Lax, M_j = s D(L_ax, j); RX: u = rand_dir(98001 + task index), M_j = s |D(L_ax, j)|."""
    from ctx4 import rand_dir
    L = ax["L"]

    def f(ctx: G.Ctx, w: str, k: int | None):
        tw = ctx.twin(w)
        if kind == "AX":
            u, M = ax["a"], s * ax["D"]
        else:
            u = torch.tensor(rand_dir(SEED_RAND_TARGET[task]), device=ctx.dev)
            M = s * ax["D"].abs()
        edits = {L: E.edit_target(tw["a"], tw["b"], u, M, tw["S"][L])}
        pre, rec = G.realised(ctx, w, edits, extra_dirs={"u": (L, u)})
        rec["target_mean"] = float(M.mean())
        rec["rel_err_along_u"] = abs(rec[f"proj_u_L{L}"] - float(M.mean())) / max(abs(float(M.mean())), 1e-9)
        return pre, rec
    return G.Arm(f"{kind}_s{s:g}", f, meta={"family": kind, "s": s, "site": f"spec positions, block {L}",
                                             "layer": L, "direction_seed": SEED_RAND_TARGET[task] if kind == "RX"
                                             else None})


def clamp_extra(ax: dict[str, Any], rand_u: torch.Tensor | None) -> Any:
    """Per-block clamp at blocks L_ax..35 (after the push's own edit at blocks 12-23)."""
    def extra(ctx: G.Ctx, w: str) -> dict:
        tw = ctx.twin(w)
        out = {}
        for l in range(ax["L"], 36):
            u = ax["a_all"][CAP_BLOCKS.index(l)] if rand_u is None else rand_u
            out[l] = E.edit_clamp(tw["a"], tw["b"], u, tw["S"][l])
        return out
    return extra


# ------------------------------------------------------------------------------------------------ T1 top-five
def top5_states(model: Any, tok: Any) -> dict[str, Any]:
    """Per-position forced-prompt centroids at blocks 12-23 (10 algorithms x 10 paraphrases) and S-means at blocks
    12-35 for every forced prompt, twin, top5ban and BFS ban (geometry)."""
    if TOP5_STATES.exists():
        z = np.load(TOP5_STATES, allow_pickle=True)
        return {k: z[k] for k in z.files}
    recs = PR.t1_forced(tok, 10)
    ref = PR.twin("T1", "W1")
    nS = ref["spec_end"] - ref["p1"]
    blocks = CAP_BLOCKS
    cent = {X: torch.zeros(12, nS, 4096) for X in PR.T1_CAT10}
    cnt = {X: 0 for X in PR.T1_CAT10}
    smean, labels, pids = [], [], []
    for r in recs:
        H: dict[int, torch.Tensor] = {}
        E.prefill(model, r["ids"], capture=E.capture_S(H, r["p1"], r["spec_end"], blocks))
        cent[r["X"]] += torch.stack([H[l] for l in common.EDIT_BLOCKS]).cpu()
        cnt[r["X"]] += 1
        smean.append(torch.stack([H[l].mean(0) for l in blocks]).cpu().numpy())
        labels.append(r["X"])
        pids.append(r["pid"])
        del H
    other = {}
    for kind, fn in (("twin", PR.twin), ("ban", PR.ban), ("top5ban", lambda t, w: PR.p6(t, "top5ban", w))):
        for w in TEMPLATES:
            r = fn("T1", w)
            H = {}
            E.prefill(model, r["ids"], capture=E.capture_S(H, r["p1"], r["spec_end"], blocks))
            other[f"{kind}__{w}"] = torch.stack([H[l].mean(0) for l in blocks]).cpu().numpy()
            del H
    C = np.stack([(cent[X] / max(cnt[X], 1)).numpy() for X in PR.T1_CAT10])      # [10, 12, nS, D]
    out = {"cent": C.astype(np.float32), "cat": np.array(PR.T1_CAT10), "smean": np.stack(smean).astype(np.float32),
           "labels": np.array(labels), "pids": np.array(pids), "blocks": np.array(blocks),
           **{k: v.astype(np.float32) for k, v in other.items()}}
    np.savez(TOP5_STATES, **out)
    return out


def top5_edits(ctx: G.Ctx, w: str, k: int | None, s: float, st: dict[str, Any], mode: str, X: str | None = None
               ) -> tuple[dict, str | None]:
    """Band edit at blocks 12-23 per position j: Delta = c_target[l,j] - c_ban[l,j], u = unit(Delta) (AWAY: u =
    unit(h_twin - c_ban), magnitude ||Delta_SURV||); h <- h + (s||Delta|| - (h - h_twin).u) u."""
    cat = list(st["cat"])
    C = st["cent"]
    c_ban = C[[cat.index(x) for x in PR.T1_TOP5]].mean(0)
    c_surv = C[[cat.index(x) for x in PR.T1_SURV]].mean(0)
    tw = ctx.twin(w)
    dev = ctx.dev
    if mode == "RSURV":
        rng = np.random.default_rng(stable_seed("T1", "RSURV", w, k) % (2 ** 32))
        Xk = PR.T1_SURV[int(rng.integers(0, 5))]
        tgt = C[cat.index(Xk)]
    elif mode == "ONE":
        Xk, tgt = X, C[cat.index(X)]
    else:
        Xk, tgt = None, c_surv
    edits = {}
    for j, l in enumerate(common.EDIT_BLOCKS):
        Dl = torch.tensor(tgt[j] - c_ban[j], device=dev)                      # [nS, D]
        mag = Dl.norm(dim=-1)
        if mode == "AWAY":
            mag = torch.tensor(c_surv[j] - c_ban[j], device=dev).norm(dim=-1)
            v = tw["S"][l] - torch.tensor(c_ban[j], device=dev)
            U = v / v.norm(dim=-1, keepdim=True).clamp(min=1e-9)
        else:
            U = Dl / mag[:, None].clamp(min=1e-9)
        edits[l] = E.edit_target(tw["a"], tw["b"], U, s * mag, tw["S"][l])
    return edits, Xk


def top5_arm(name: str, s: float, st: dict[str, Any], mode: str, X: str | None = None) -> G.Arm:
    def f(ctx: G.Ctx, w: str, k: int | None):
        edits, Xk = top5_edits(ctx, w, k, s, st, mode, X)
        pre, rec = G.realised(ctx, w, edits)
        rec["target_X"] = Xk
        return pre, rec
    return G.Arm(name, f, per_sample=(mode == "RSURV"), meta={"family": "TOP5PUSH", "s": s, "mode": mode,
                                                              "site": "spec positions, blocks 12-23"})


def top5_push_states(model: Any, st: dict[str, Any]) -> None:
    """Realised S-mean states (blocks 12-35) of the pushed twin for every arm, s and template (RSURV: slot k = 0)."""
    ctx = G.Ctx(model, "T1", PR.p4())
    out = {}
    for mode in ("SURV", "RSURV", "AWAY"):
        for s in S_TOP5:
            for w in TEMPLATES:
                edits, Xk = top5_edits(ctx, w, 0, s, st, mode)
                tw = ctx.twin(w)
                H: dict[int, torch.Tensor] = {}
                E.prefill(model, tw["prompt"]["ids"], edits=edits, capture=E.capture_S(H, tw["a"], tw["b"],
                                                                                         CAP_BLOCKS))
                out[f"{mode}_s{s:g}__{w}"] = torch.stack([H[l].mean(0) for l in CAP_BLOCKS]).cpu().numpy()
                del H
    np.savez(STATES / "top5_push_states.npz", **out)
    ctx.release()


# ------------------------------------------------------------------------------------------------ stages
def stage_t03(model, tok, deadline):
    ctx = G.Ctx(model, "T03", PR.p4())
    arms = {}
    for s in SEEDS_T03:
        a = G.pop_arm(s, 2.0, "T03")
        arms[a.name] = a
    G.run_cells(model, tok, ctx, arms, [(a, [0, 1]) for a in arms], "C1_t03", deadline=deadline)
    ctx.release()


def stage_targeted(model, tok, tasks, deadline):
    spec = {"name": "commit4_push_spec", "utc": utc_now(), "targeted": {}, "top5": {
        "arms": ["SURV", "RSURV", "AWAY", "IDASTAR"], "s": list(S_TOP5), "N": 30, "c_ban": "mean of TOP5 "
        "forced centroids", "survivors": PR.T1_SURV, "top5": PR.T1_TOP5}}
    for task in tasks:
        ax = axis(task, torch.device("cuda", 0))
        spec["targeted"][task] = {"L_ax": ax["L"], "s": list(S_TARGET), "N": 30, "random_seed": SEED_RAND_TARGET[task],
                                  "D_mean": float(ax["D"].mean()), "D_rms": float(ax["D"].pow(2).mean().sqrt())}
    p = PRED / "commit4_push_spec.json"
    if not p.exists():
        write_json(p, spec)
        logger.info(f"commit4 -> {commit('commit4_push_spec', p)}")
    for task in tasks:
        ax = axis(task, torch.device("cuda", 0))
        ctx = G.Ctx(model, task, PR.p4())
        arms = {}
        for s in S_TARGET:
            for kind in ("AX", "RX"):
                a = targeted_arm(task, s, kind, ax)
                arms[a.name] = a
        G.run_cells(model, tok, ctx, arms, [(a, list(range(6))) for a in arms], "T1_targeted", deadline=deadline)
        ctx.release()


def stage_targeted_ext(model, tok, tasks, deadline):
    """Fallback 8: the same AX / RX arms at s in {2, 4, 8} (descriptive; 8 added beyond the plan's {2, 4})."""
    for task in tasks:
        ax = axis(task, torch.device("cuda", 0))
        ctx = G.Ctx(model, task, PR.p4())
        arms = {}
        for s in S_TARGET_EXT:
            for kind in ("AX", "RX"):
                a = targeted_arm(task, s, kind, ax)
                arms[a.name] = a
        G.run_cells(model, tok, ctx, arms, [(a, list(range(6))) for a in arms], "T1_targeted_ext", deadline=deadline)
        ctx.release()


def stage_top5(model, tok, deadline, arms_sel=("SURV", "RSURV", "AWAY", "IDASTAR")):
    st = top5_states(model, tok)
    if not (STATES / "top5_push_states.npz").exists():
        top5_push_states(model, st)
    ctx = G.Ctx(model, "T1", PR.p4())
    arms = {}
    for s in S_TOP5:
        for mode in arms_sel:
            if mode == "IDASTAR":
                continue
            a = top5_arm(f"{mode}_s{s:g}", s, st, mode)
            arms[a.name] = a
    if "IDASTAR" in arms_sel:
        a = top5_arm("IDASTAR_s0.5", 0.5, st, "ONE", "idastar")
        arms[a.name] = a
    order = [n for n in arms if n.startswith(("SURV", "RSURV"))] + [n for n in arms if not n.startswith(("SURV",
                                                                                                       "RSURV"))]
    G.run_cells(model, tok, ctx, arms, [(n, list(range(6))) for n in order], "G3_top5", deadline=deadline)
    ctx.release()


def stage_remeasure(model, tok, deadline):
    orig = G.RAW
    G.RAW = S0B_RAW
    try:
        for task in ("T10", "T2"):
            ctx = G.Ctx(model, task, PR.p4())
            arms = {}
            for s in SEEDS40:
                a = G.pop_arm(s, 2.0, task)
                arms[a.name] = a
            G.run_cells(model, tok, ctx, arms, [(a, [0, 1]) for a in arms], "S0b_remeasure", deadline=deadline)
            ctx.release()
    finally:
        G.RAW = orig


def stage_clamp(model, tok, deadline):
    t0 = time.time()
    while not (RESULTS / "clamp_selection.json").exists() and time.time() - t0 < 900:
        time.sleep(10)        # the selection needs the post-commit-#3 analysis (CPU, concurrent)
    if not (RESULTS / "clamp_selection.json").exists():
        logger.warning("clamp selection missing: clamp not run")
        return
    sel = read_json(RESULTS / "clamp_selection.json")
    from ctx4 import rand_dir
    orig = G.RAW
    G.RAW = CLAMP_RAW
    try:
        for task, seeds in sel["seeds"].items():
            ax = axis(task, torch.device("cuda", 0))
            ru = torch.tensor(rand_dir(SEED_RAND_TARGET[task] + 100), device=torch.device("cuda", 0))
            ctx = G.Ctx(model, task, PR.p4())
            arms = {}
            for s in seeds:
                for nm, extra in (("CLU", None), ("CLA", clamp_extra(ax, None)), ("CLR", clamp_extra(ax, ru))):
                    a = G.pop_arm(s, 2.0, task, name=f"{nm}_d{s}", extra=extra, meta={"clamp": nm})
                    arms[a.name] = a
            G.run_cells(model, tok, ctx, arms, [(a, list(range(4))) for a in arms], "P2N_clamp", deadline=deadline)
            ctx.release()
    finally:
        G.RAW = orig


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stages")
    ap.add_argument("--deadline-min", type=float, default=600)
    ap.add_argument("--tasks", default="T10,T2,T03")
    args = ap.parse_args()
    setup_logging("pushrun")
    deadline = time.time() + 60 * args.deadline_min
    tok, model = E.load()
    for st in args.stages.split(","):
        t0 = time.time()
        if st == "t03":
            stage_t03(model, tok, deadline)
        elif st == "targeted":
            stage_targeted(model, tok, args.tasks.split(","), deadline)
        elif st == "targeted_ext":
            stage_targeted_ext(model, tok, args.tasks.split(","), deadline)
        elif st == "top5":
            stage_top5(model, tok, deadline)
        elif st == "top5core":
            stage_top5(model, tok, deadline, ("SURV", "RSURV"))
        elif st == "remeasure":
            stage_remeasure(model, tok, deadline)
        elif st == "clamp":
            stage_clamp(model, tok, deadline)
        logger.info(f"stage {st} done in {time.time() - t0:.0f}s")
        write_json(RESULTS / f"stage_{st}_done.json", {"utc": utc_now(), "seconds": time.time() - t0})


if __name__ == "__main__":
    main()
