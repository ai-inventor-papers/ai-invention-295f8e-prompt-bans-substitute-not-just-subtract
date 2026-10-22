#!/usr/bin/env python3
"""C2b: how do knob displacements project on the plan subspace, and does the projection track the knob's recorded
effect? One table of (task, knob, template, source, recorded off-default share and N, ||delta|| in ban units,
pi(delta), s(delta)).

Displacements (forward passes only, states/states_<task>.npz): knob S-mean minus the template-matched twin S-mean at
blocks 12-23 (NOV: vs the mean twin); PLAIN-relative displacements are reported as a bracket. Pushes (exp17 RAND rows,
exp17 FP8 ban norms) use the realised prefill displacement (states/disp_<task>.npz, SCR keys).
Recorded outcomes: exp13 samples (nonce, ban = modal ban, bandpatch = the ban's own states patched in, novelty) for
the 12 bench tasks; exp17 labels (BAN; RAND9001-9015 pushes) for T03-T06 and T1/T2. Excluded (listed): token vetoes
(oneshot, persistent: no prompt-state displacement), iterative / sham prompts whose text is not on record, exp13
rand1-3 (directions not on record), exp7/exp6 T1/T2 novelty and mention seeds (outcomes purged with ITER1).
Committed rule: pooled within-task Spearman(pi(delta_knob), recorded off-default share) >= 0.5 and pi beats ||delta||
(paired bootstrap over knobs within task of rho_pi - rho_norm > 0).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
from scipy.stats import rankdata

from common import EXCLUDE, spearman
from cfg4 import (DEFAULT4, E13, E17, EDIT_BLOCKS, KNOB_TASKS, STATES_DIR, TEMPLATE_IDS, read_jsonl)
from screen import catalogue
import npz_parts

EXCLUDED = ["exp13 oneshot / persistent (token vetoes)", "exp13 iter1-3, sham (prompt text not on record here)",
            "exp13 rand1-3 (push directions not on record)", "exp7 / exp6 T1/T2 novelty, mention, seeds (no outcomes)"]


def _share(rows: list[dict[str, Any]], cat: set[str], d: str) -> tuple[float, int]:
    v = [r for r in rows if r["label"] not in EXCLUDE]
    if not v:
        return float("nan"), 0
    return sum(r["label"] in cat and r["label"] != d for r in v) / len(v), len(v)


def run(rows_unused, commit: dict[str, Any], esc: dict[str, Any]) -> dict[str, Any]:
    from ctx4 import ban_unit
    s13 = defaultdict(list)
    for r in read_jsonl(E13 / "data" / "samples.jsonl"):
        s13[(r["task"], r["condition"], r["template"])].append({"label": r["label"]})
    l17 = defaultdict(list)
    for r in read_jsonl(E17 / "data" / "labels.jsonl"):
        l17[(r["task"], r["arm"])].append({"label": r["label"]})
    table = []
    for t in KNOB_TASKS:
        z = npz_parts.load(STATES_DIR / f"states_{t}.npz")
        pids = [str(p) for p in z["pids"]]
        H = z["smean"].astype(np.float32)
        ix = {p: i for i, p in enumerate(pids)}
        sub = np.load(STATES_DIR / f"subspace_{t}.npz")
        blocks = [int(b) for b in sub["blocks"]]
        bi = [blocks.index(l) for l in EDIT_BLOCKS]
        Q, A = sub["Q"].astype(np.float64), sub["a"].astype(np.float64)
        nmean = ban_unit(t).mean(1)
        cat, d = set(catalogue(t)), DEFAULT4[t]

        def proj(dv: np.ndarray) -> tuple[float, float, float]:
            pis, nrm, sd = [], [], []
            for j, b in enumerate(bi):
                v = dv[b].astype(np.float64)
                pis.append(float(np.sum((Q[b].T @ v) ** 2) / max(v @ v, 1e-30)))
                nrm.append(float(np.linalg.norm(v)) / nmean[j])
                sd.append(float(v @ A[b]) / nmean[j])
            return float(np.mean(pis)), float(np.mean(nrm)), float(np.mean(sd))

        twin = {w: H[ix[f"{t}|twin|-|{w}|-"]] for w in TEMPLATE_IDS}
        plain = H[ix[f"{t}|plain|-|-|-"]]
        twin_mean = np.mean(list(twin.values()), 0)

        def add(knob, w, dv, dvp, src, rr):
            sh, n = _share(rr, cat, d)
            if n == 0:
                return
            pi, nrm, sd = proj(dv)
            pip, nrmp, _ = proj(dvp) if dvp is not None else (None, None, None)
            table.append({"task": t, "knob": knob, "template": w, "source": src, "share": sh, "n": n, "pi": pi,
                          "norm_ban_units": nrm, "s": sd, "pi_vs_plain": pip, "norm_vs_plain": nrmp})
        for w in TEMPLATE_IDS:
            kb = f"{t}|ban|{d}|{w}|-"
            if kb in ix:
                dv = H[ix[kb]] - twin[w]
                add("ban", w, dv, H[ix[kb]] - plain, "exp13 ban", s13.get((t, "ban", w), []))
                add("bandpatch", w, dv, None, "exp13 bandpatch", s13.get((t, "bandpatch", w), []))
            kn = f"{t}|knob_nonce|-|{w}|-"
            if kn in ix:
                add("nonce", w, H[ix[kn]] - twin[w], H[ix[kn]] - plain, "exp13 nonce", s13.get((t, "nonce", w), []))
        kv = f"{t}|knob_novelty|-|NOV|-"
        if kv in ix:
            add("novelty", "NOV", H[ix[kv]] - twin_mean, H[ix[kv]] - plain, "exp13 novelty",
                s13.get((t, "novelty", "NOV"), []))
        # exp17 rows: bans (pooled over templates) and RAND pushes (realised displacement)
        if (t, "BAN") in l17:
            dv = np.mean([H[ix[f"{t}|ban|{d}|{w}|-"]] - twin[w] for w in TEMPLATE_IDS], 0)
            add("ban_exp17", "W1-W5", dv, None, "exp17 BAN (FP8)", l17[(t, "BAN")])
        dz = STATES_DIR / f"disp_{t}.npz"
        if npz_parts.exists(dz):
            zf = npz_parts.load(dz)
            zz = {"delta": zf["delta"], "keys": zf["keys"]}
            keys = [str(k) for k in zz["keys"]]
            groups = defaultdict(list)
            for i, k in enumerate(keys):
                fam, s, a, w = k.split("|")
                if fam == "SCR":
                    groups[(s, a)].append(zz["delta"][i].astype(np.float32))
            for (s, a), dl in groups.items():
                arm = f"RAND{s}_a{a}"
                if (t, arm) in l17:
                    add("push_exp17", arm, np.mean(dl, 0), None, "exp17 RAND (realised)", l17[(t, arm)])
    out: dict[str, Any] = {"table": table, "excluded": EXCLUDED}
    # pooled within-task Spearman (ranks within task)
    by_t = defaultdict(list)
    for r in table:
        by_t[r["task"]].append(r)
    X, Y, N = [], [], []
    per_task = {}
    for t, rr in by_t.items():
        if len(rr) < 3:
            continue
        pi = np.array([r["pi"] for r in rr])
        nr = np.array([r["norm_ban_units"] for r in rr])
        sh = np.array([r["share"] for r in rr])
        per_task[t] = {"n_knobs": len(rr), "rho_pi": spearman(pi, sh), "rho_norm": spearman(nr, sh)}
        X.append(rankdata(pi) / len(pi))
        Y.append(rankdata(sh) / len(sh))
        N.append(rankdata(nr) / len(nr))

    def pooled(idx_sets):
        xs = np.concatenate([X[i][j] for i, j in idx_sets])
        ys = np.concatenate([Y[i][j] for i, j in idx_sets])
        ns = np.concatenate([N[i][j] for i, j in idx_sets])
        rp = float(np.corrcoef(xs, ys)[0, 1]) if np.std(ys) > 0 and np.std(xs) > 0 else 0.0
        rn = float(np.corrcoef(ns, ys)[0, 1]) if np.std(ys) > 0 and np.std(ns) > 0 else 0.0
        return rp, rn
    if X:
        full = [(i, np.arange(len(X[i]))) for i in range(len(X))]
        rp, rn = pooled(full)
        rng = np.random.default_rng(0)
        diffs = []
        for _ in range(2000):
            sets = [(i, rng.integers(0, len(X[i]), len(X[i]))) for i in range(len(X))]
            a, b = pooled(sets)
            diffs.append(a - b)
        out["pooled"] = {"rho_pi": rp, "rho_norm": rn, "d_rho_ci": [float(np.quantile(diffs, .025)),
                                                                     float(np.quantile(diffs, .975))],
                         "PASS": bool(rp >= 0.5 and np.quantile(diffs, 0.025) > 0)}
    out["per_task"] = per_task
    cls = defaultdict(list)
    for r in table:
        cls[r["knob"]].append(r)
    out["class_means"] = {k: {"n": len(v), "pi": float(np.mean([x["pi"] for x in v])),
                              "norm": float(np.mean([x["norm_ban_units"] for x in v])),
                              "share": float(np.nanmean([x["share"] for x in v]))} for k, v in cls.items()}
    return out
