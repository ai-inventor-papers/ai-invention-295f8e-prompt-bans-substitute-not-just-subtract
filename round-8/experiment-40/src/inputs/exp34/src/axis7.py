#!/usr/bin/env python3
"""P2 axis (A1-A6), fitted with no outcome data, committed as commit #2 before any outcome row is read.

A1  forced-runner-up prompts: prompts4 named(task, runner-up, F0-F9, display-name variant 0) (K = 10; T2's F0 is
    exp30's FORCED prompt) and their ' .' padding twins (identical ids from 'Task:' on, asserted)
A2  block outputs at blocks 12-35, spec positions, fp32: forced, pads, W1-W5 neutral twins, W1-W5 bans, exp30
    placebo twins (second neutral noun per template), forced prompts of every catalogue algorithm (F0-F4)
A3  a_L = unit(mean_i mean_j (h_forced_i[L,j] - h_pad_i[L,j])); leave-one-out sep(L); L_ax = argmax (ties -> smaller
    L; max sep < 2 -> 20); c_def(L,j) (twins), c_ru(L,j) (forced), D = c_ru - c_def, Dbar = mean_j D;
    natural-variance ratio (dormant-subspace guard): variance of neutral-prompt S-means along a_Lax / mean variance
    along 200 random unit directions
A4  U4 = top-4 right singular vectors of stacked S-mean differences {forced_i - pad_i} and {ban_w - twin_w} at L_ax;
    P_t = orthonormal basis of the centred forced-prompt centroids of all catalogue algorithms at L_ax
A6  predictions/commit2_axis.json + cache/states/axis_<task>.npz; fresh T03 seeds 97001-97024 checked disjoint
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import torch  # noqa: E402
from loguru import logger  # noqa: E402

import c7 as common  # noqa: E402
from c7 import (CAP_BLOCKS, CATALOGUE, DEFAULTS, PRED, RESULTS, ROOT, RUNNER_UP, SEED_RAND_TARGET, SEEDS_T03,  # noqa: E402
                STATES, TEMPLATES, commit, setup_logging, utc_now, write_json)
import engine7 as E  # noqa: E402
import prompts7 as PR  # noqa: E402


def capture(model: Any, rec: dict[str, Any], blocks: list[int] = CAP_BLOCKS) -> torch.Tensor:
    """[len(blocks), nS, D] fp32 (CPU) block outputs at the spec positions of a prompt."""
    H: dict[int, torch.Tensor] = {}
    E.prefill(model, rec["ids"], capture=E.capture_S(H, rec["p1"], rec["spec_end"], blocks))
    out = torch.stack([H[l] for l in blocks]).cpu()
    del H
    return out


def seed_disjointness() -> dict[str, Any]:
    """C7: fresh seeds vs every direction file / committed seed list reachable from the run's earlier artifacts."""
    import re
    fresh = set(SEEDS_T03) | set(SEED_RAND_TARGET.values())
    seen: set[int] = set()
    # The committed run scanned the earlier iterations' artifact folders (4,551 direction files; commit #2); a reader
    # can point AII_EARLIER_ARTIFACT_ROOTS (os.pathsep-separated) at their copies; by default the vendored copies under
    # vendor/ (which hold every direction file this artifact uses) are scanned.
    env = os.environ.get("AII_EARLIER_ARTIFACT_ROOTS", "")
    roots = [Path(x) for x in env.split(os.pathsep) if x] + [ROOT / "vendor"]
    n_files = 0
    for r in roots:
        if not r.exists():
            continue
        for p in r.rglob("rand_*.npy"):
            n_files += 1
            m = re.search(r"rand_(\d+)\.npy", p.name)
            if m:
                seen.add(int(m.group(1)))
    for p in [common.IN29 / "c2_commit.json", common.IN29 / "slot_map.json"]:
        txt = p.read_text()
        seen |= {int(x) for x in re.findall(r"\b(9[0-9]{4})\b", txt)}
    clash = sorted(fresh & seen)
    return {"fresh": sorted(fresh), "n_direction_files": n_files, "n_seen_5digit_9xxxx": len(seen),
            "clashes": clash, "disjoint": not clash}


def fit_task(model: Any, tok: Any, task: str) -> dict[str, Any]:
    t0 = time.time()
    ru = RUNNER_UP[task]
    forced = PR.named_list(task, ru, 10, 0)
    pads = [PR.pad_record(tok, r) for r in forced]
    for f, p in zip(forced, pads):
        assert f["ids"][f["p1"]:] == p["ids"][p["p1"]:] and len(f["ids"]) == len(p["ids"])
    twins = [PR.twin(task, w) for w in TEMPLATES]
    bans = [PR.ban(task, w) for w in TEMPLATES]
    placebos = [PR.p6(task, "placebo", w) for w in TEMPLATES]
    nS = twins[0]["spec_end"] - twins[0]["p1"]
    for r in forced + twins + bans + placebos:
        assert r["spec_end"] - r["p1"] == nS, (r["pid"], r["spec_end"] - r["p1"], nS)
        assert r["ids"][r["p1"]:r["spec_end"]] == twins[0]["ids"][twins[0]["p1"]:twins[0]["spec_end"]]
    Hf = torch.stack([capture(model, r) for r in forced])        # [K, 24, nS, D]
    Hp = torch.stack([capture(model, r) for r in pads])
    Ht = torch.stack([capture(model, r) for r in twins])         # [5, 24, nS, D]
    Hb = torch.stack([capture(model, r) for r in bans])
    Hpl = torch.stack([capture(model, r) for r in placebos])
    K = len(forced)
    diff = (Hf - Hp).mean(2)                                     # [K, 24, D] S-mean differences
    a = diff.mean(0)
    a = a / a.norm(dim=-1, keepdim=True)                          # [24, D]
    sep = []
    for li in range(len(CAP_BLOCKS)):
        d = []
        for i in range(K):
            m = torch.cat([diff[:i, li], diff[i + 1:, li]]).mean(0)
            m = m / m.norm()
            d.append(float(diff[i, li] @ m))
        d = np.array(d)
        sep.append(float(d.mean() / max(d.std(ddof=1), 1e-9)))
    best = int(np.argmax(sep))
    L_ax = CAP_BLOCKS[best] if max(sep) >= 2 else 20
    li_ax = CAP_BLOCKS.index(L_ax)
    proj_t = torch.einsum("wlsd,ld->wls", Ht, a)                 # [5, 24, nS]
    proj_f = torch.einsum("klsd,ld->kls", Hf, a)
    c_def = proj_t.mean(0)
    c_ru = proj_f.mean(0)
    D = c_ru - c_def                                             # [24, nS]
    Dbar = D.mean(1)                                             # [24]
    # natural variance along a_Lax across the 10 neutral prompts vs 200 random unit directions
    neutral = torch.cat([Ht[:, li_ax].mean(1), Hpl[:, li_ax].mean(1)])   # [10, D]
    var_a = float((neutral @ a[li_ax]).var(unbiased=True))
    g = torch.Generator().manual_seed(12345)
    R = torch.randn(200, neutral.shape[1], generator=g)
    R = R / R.norm(dim=-1, keepdim=True)
    var_r = (neutral @ R.T).var(dim=0, unbiased=True)
    nat = {"var_along_axis": var_a, "mean_var_random": float(var_r.mean()), "ratio": var_a / float(var_r.mean()),
           "pct_rank_vs_random": float((var_r < var_a).float().mean()), "n_prompts": int(neutral.shape[0]),
           "prompts": "W1-W5 neutral twins + exp30 placebo twins (second neutral noun per template)"}
    # U4 and P_t at L_ax
    stack = torch.cat([diff[:, li_ax], (Hb[:, li_ax] - Ht[:, li_ax]).mean(1)])     # [K + 5, D]
    _, Sv, Vh = torch.linalg.svd(stack, full_matrices=False)
    U4 = Vh[:4].T.contiguous()                                    # [D, 4]
    cents = {}
    for X in CATALOGUE[task]:
        recs = PR.named_list(task, X, 5, 0)
        cents[X] = torch.stack([capture(model, r, [L_ax])[0].mean(0) for r in recs]).mean(0)
    C = torch.stack([cents[X] for X in CATALOGUE[task]])
    Cc = C - C.mean(0, keepdim=True)
    _, Sc, Vc = torch.linalg.svd(Cc, full_matrices=False)
    rank = int((Sc > 1e-6 * Sc[0]).sum())
    Pt = Vc[:rank].T.contiguous()                                 # [D, rank]
    np.savez(STATES / f"axis_{task}.npz", a=a.numpy(), D=D.numpy(), Dbar=Dbar.numpy(), c_def=c_def.numpy(),
             c_ru=c_ru.numpy(), U4=U4.numpy(), Pt=Pt.numpy(), blocks=np.array(CAP_BLOCKS), L_ax=L_ax,
             sep=np.array(sep), centroids=C.numpy(), cat=np.array(CATALOGUE[task]),
             forced_smean=Hf.mean(2)[:, li_ax].numpy(), pad_smean=Hp.mean(2)[:, li_ax].numpy(),
             twin_smean=Ht.mean(2).numpy().astype(np.float32), ban_smean=Hb.mean(2).numpy().astype(np.float32))
    # per-position twin states at L_ax (for targeted pushes and realised-edit checks)
    out = {"task": task, "runner_up": ru, "K": K, "forced_pids": [r["pid"] for r in forced], "nS": nS,
           "sep": dict(zip(map(str, CAP_BLOCKS), sep)), "L_ax": L_ax, "max_sep": max(sep),
           "layer_rule": "argmax LOO sep" if max(sep) >= 2 else "flat (max sep < 2) -> 20",
           "Dbar": dict(zip(map(str, CAP_BLOCKS), Dbar.tolist())), "D_Lax_mean": float(D[li_ax].mean()),
           "D_Lax_min": float(D[li_ax].min()), "D_Lax_rms": float(D[li_ax].pow(2).mean().sqrt()),
           "natural_variance": nat, "U4_singular_values": Sv[:6].tolist(), "Pt_rank": rank,
           "Pt_singular_values": Sc.tolist(), "seconds": time.time() - t0,
           "ban_minus_twin_along_a_Lax": float(((Hb - Ht)[:, li_ax].mean(1) @ a[li_ax]).mean()),
           "forced_minus_twin_along_a_Lax": float(D[li_ax].mean())}
    del Hf, Hp, Ht, Hb, Hpl
    E.free_cuda()
    logger.info(f"{task}: L_ax {L_ax} (max sep {max(sep):.2f}), Dbar(L_ax) {float(Dbar[li_ax]):.3f}, natural "
                f"variance ratio {nat['ratio']:.2f}, Pt rank {rank}, {time.time() - t0:.0f}s")
    return out


def main() -> None:
    setup_logging("axis7")
    tok, model = E.load()
    res = {"name": "commit2_axis", "utc": utc_now(), "das": {"status": "skipped (drop item 5: P2 secondary DAS; "
                                                                       "time budget)"}}
    for task in ("T10", "T2", "T03"):
        res[task] = fit_task(model, tok, task)
    res["t03_fresh_seeds"] = SEEDS_T03
    res["seed_disjointness"] = seed_disjointness()
    assert res["seed_disjointness"]["disjoint"], res["seed_disjointness"]
    res["states_sha256"] = {t: common.sha256_file(STATES / f"axis_{t}.npz") for t in ("T10", "T2", "T03")}
    p = PRED / "commit2_axis.json"
    write_json(p, res)
    write_json(RESULTS / "axis.json", res)
    logger.info(f"commit2 -> {commit('commit2_axis', p)}")


if __name__ == "__main__":
    main()
