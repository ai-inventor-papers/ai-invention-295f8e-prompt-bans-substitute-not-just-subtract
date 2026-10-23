#!/usr/bin/env python3
"""Per-task GPU context: clean twin prefills (captures for h_ref and displacement logging), edited arm prefills with
realised-displacement records, ban units and random directions.

Realised displacement of an edited prefill against the template-matched clean twin:
  delta_l   = mean_{p in S} (h_arm[l,p] - h_twin[l,p])          (blocks 12-35; S-mean vector)
  delta_R_l = h_arm[l,R] - h_twin[l,R]
  rel_err_l = mean_p |(h_arm - h_twin)[l,p] . U_l - M_l[p]| / |M_l[p]|   (edited blocks; TARGET only)
  gain      = mean_p ||h_arm[35,p] - h_twin[35,p]|| / mean_{l in 12-23, p} M_l[p]   (per-position norms)
  gain_smean= ||delta_35|| / mean_l ||delta_l^target||  with delta_l^target = mean_p M_l[p] U_l
"""

from __future__ import annotations

from typing import Any

import numpy as np
import torch

from cfg4 import CAP_BLOCKS, D_MODEL, DIR_DIR, E13, E17, EDIT_BLOCKS, PATH_TASKS, RESULTS_DIR, read_json
from engine4 import prefill
from hooks4 import make_edits_v4


def rand_dir(seed: int) -> np.ndarray:
    """exp17 _RandDirs construction: PCG64(seed).standard_normal(4096), normalised; saved on first use."""
    p = DIR_DIR / f"rand_{seed}.npy"
    if p.exists():
        return np.load(p)
    src = E17 / "directions" / f"rand_{seed}.npy"
    if src.exists():
        v = np.load(src)
    else:
        x = np.random.Generator(np.random.PCG64(seed)).standard_normal(D_MODEL)
        v = (x / np.linalg.norm(x)).astype(np.float32)
    np.save(p, v)
    return v


def ban_unit(task: str, source: str = "plan") -> np.ndarray:
    """n[l,p] [12, |S|]: exp13 norms_<task>.npz['norm'] for bench tasks, exp17 norms_T1/T2 for path tasks (plan);
    source='exp17' returns exp17's own FP8 norms (engine check replication); R2 -> results/units.json n_free."""
    if source == "exp17":
        return np.load(E17 / "directions" / f"norms_{task}.npy").astype(np.float32)
    if task in PATH_TASKS:
        return np.load(E17 / "directions" / f"norms_{task}.npy").astype(np.float32)
    if task == "R2":
        return np.asarray(np.load(RESULTS_DIR / "units_nfree_R2.npy"), dtype=np.float32)
    return np.load(E13 / "results" / "tensors" / f"norms_{task}.npz")["norm"].astype(np.float32)


class TaskCtx:
    def __init__(self, model: Any, prompts: dict[str, dict[str, Any]], task: str):
        self.model, self.task, self.pr = model, task, prompts
        self.dev = model.device
        self.clean: dict[str, dict[str, Any]] = {}

    def prompt(self, kind: str, w: str, X: str | None = None) -> dict[str, Any]:
        return self.pr[f"{self.task}|{kind}|{X or '-'}|{w}|-"]

    def _capture(self, a: int, b: int, P: int, keep_S: bool):
        cap: dict[str, dict[int, torch.Tensor]] = {"S": {}, "smean": {}, "R": {}, "pnorm": {}}

        def mk(l):
            def g(h):
                hs = h[0, a:b].float()
                if keep_S:
                    cap["S"][l] = hs.clone()
                else:
                    cap["S"][l] = hs.clone() if l in (CAP_BLOCKS[-1],) or l in EDIT_BLOCKS else None
                cap["smean"][l] = hs.mean(0)
                cap["R"][l] = h[0, P - 1].float().clone()
            return g
        return cap, {l: mk(l) for l in CAP_BLOCKS}

    def twin(self, w: str) -> dict[str, Any]:
        if w not in self.clean:
            p = self.prompt("twin", w)
            a, b, P = p["p1"], p["spec_end"], p["P"]
            cap, hooks = self._capture(a, b, P, keep_S=True)
            pre = prefill(self.model, p["ids"], capture=hooks)
            self.clean[w] = {"pre": pre, "S": cap["S"], "smean": cap["smean"], "R": cap["R"], "a": a, "b": b,
                             "P": P, "prompt": p}
        return self.clean[w]

    def arm_prefill(self, w: str, spec: dict[str, Any], want_vectors: bool = False) -> tuple[dict[str, Any],
                                                                                              dict[str, Any]]:
        """spec: {'kind': None|'TARGET'|'CLAMP', 'U': {l: [D] tensor}, 'M': {l: [|S|] tensor}, 'Q': {l: [D,k]}}"""
        tw = self.twin(w)
        if spec.get("kind") is None:
            return tw["pre"], {}
        a, b, P = tw["a"], tw["b"], tw["P"]
        log: dict[int, list[float]] = {}
        edits = make_edits_v4(spec["kind"], a, b, spec["U"], spec["M"], {l: tw["S"][l] for l in EDIT_BLOCKS},
                              Q=spec.get("Q"), log=log)
        cap, hooks = self._capture(a, b, P, keep_S=False)
        pre = prefill(self.model, tw["prompt"]["ids"], edits=edits, capture=hooks)
        rec: dict[str, Any] = {}
        relerr = {}
        for l in EDIT_BLOCKS:
            d = cap["S"][l] - tw["S"][l]
            comp = d @ spec["U"][l]
            tgt = spec["M"][l]
            relerr[l] = float(((comp - tgt).abs() / tgt.abs().clamp(min=1e-6)).mean())
        rec["rel_err_along_U"] = relerr
        rec["rel_err_max"] = max(relerr.values())
        dl = torch.stack([cap["smean"][l] - tw["smean"][l] for l in CAP_BLOCKS])   # [24, D]
        dR = torch.stack([cap["R"][l] - tw["R"][l] for l in CAP_BLOCKS])
        rec["disp_smean_norm"] = {l: float(dl[i].norm()) for i, l in enumerate(CAP_BLOCKS)}
        rec["disp_R_norm"] = {l: float(dR[i].norm()) for i, l in enumerate(CAP_BLOCKS)}
        last = CAP_BLOCKS[-1]
        pp35 = float((cap["S"][last] - tw["S"][last]).norm(dim=-1).mean())
        mmean = float(torch.stack([spec["M"][l].abs().mean() for l in EDIT_BLOCKS]).mean())
        rec["disp_pos_norm_35"] = pp35
        rec["target_mean"] = mmean
        rec["gain"] = pp35 / max(mmean, 1e-9)
        tnorm = float(torch.stack([(spec["M"][l].mean() * spec["U"][l]).norm() for l in EDIT_BLOCKS]).mean())
        rec["gain_smean"] = float(dl[-1].norm()) / max(tnorm, 1e-9)
        if want_vectors:
            rec["_delta"] = dl.cpu().numpy().astype(np.float16)
            rec["_deltaR"] = dR.cpu().numpy().astype(np.float16)
        return pre, rec

    def release(self) -> None:
        self.clean.clear()
        torch.cuda.empty_cache()


def push_spec(dev: torch.device, u: np.ndarray, n: np.ndarray, alpha: float) -> dict[str, Any]:
    ut = torch.tensor(u, dtype=torch.float32, device=dev)
    nt = torch.tensor(n, dtype=torch.float32, device=dev)
    return {"kind": "TARGET", "U": {l: ut for l in EDIT_BLOCKS},
            "M": {l: alpha * nt[j] for j, l in enumerate(EDIT_BLOCKS)}}


def load_units_report() -> dict[str, Any]:
    return read_json(RESULTS_DIR / "units.json")
