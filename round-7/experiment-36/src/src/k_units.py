#!/usr/bin/env python3
"""Dose units, direction seeds and profile masks of step K (CPU parts; the twin-norm unit U_bf needs the twin states
and is finished on the GPU by gen_k.TaskCtxK.unit()).

  U_abs[task]      exp19 load_norms(task, 'stage1') = the ban's own per-block, per-position displacement norm n[l, p]:
                   exp13 norms_<task>.npz['norm'] (T10, T03, T05) or exp17 norms_<task>.npy (T1, T2); [12, |S|].
  U_bf[task, w]    ||h_twin_w[l, p]||_2 * r_Q(l), r_Q(l) = interp((l + 1) / 36, depth, median) over exp23
                   qwen_ratio.json['r_Q'] (exp27 gen5.r_at / Ctx.banfree, verbatim arithmetic).
  U_bf*[task, w]   U_bf[l, :] * ||U_abs[l, :]||_2 / ||U_bf[l, :]||_2 (U_abs's per-block energy, U_bf's profile).
  P_top / P_rest   U_abs restricted to its top-quartile cells (n >= 75th percentile of the 12 x |S| grid) / to the
                   other cells, each rescaled to U_abs's Frobenius norm; masked cells are NOT edited.
  P_shuf           U_abs with spec positions permuted by one permutation shared by all blocks
                   (PCG64(stable_seed(task, 'SHUF'))); every cell edited.
  S4 seeds         PCG64(stable_seed(task, 'PN_a<alpha>', w, k)).standard_normal(4096), normalised (exp29 gen.pn_direction).
  S5 seeds         PCG64(stable_seed(task, 'PN5', w, k)).standard_normal(4096), normalised (exp27 gen5.pn5_direction).
"""

from __future__ import annotations

import numpy as np

from k_cfg import D_MODEL, E23, V22, read_json, s4_arm, stable_seed

E13V = V22 / "inputs" / "exp13"
E17V = V22 / "inputs" / "exp17"
PATH_TASKS = ("T1", "T2")


def u_abs(task: str) -> np.ndarray:
    """exp22 ctx4.ban_unit(task) (== exp19 load_norms(task, 'stage1')): float32 [12, |S|]."""
    if task in PATH_TASKS:
        return np.load(E17V / "directions" / f"norms_{task}.npy").astype(np.float32)
    return np.load(E13V / "results" / "tensors" / f"norms_{task}.npz")["norm"].astype(np.float32)


def r_q_table() -> tuple[np.ndarray, np.ndarray]:
    q = read_json(E23 / "results" / "qwen_ratio.json")["r_Q"]
    d = np.array([v["depth"] for v in q.values()])
    r = np.array([v["median"] for v in q.values()])
    o = np.argsort(d)
    return d[o], r[o]


_RQ: tuple[np.ndarray, np.ndarray] | None = None


def r_at(l: int) -> float:
    """exp27 gen5.r_at, verbatim."""
    global _RQ
    if _RQ is None:
        _RQ = r_q_table()
    return float(np.interp((l + 1) / 36, _RQ[0], _RQ[1]))


def s4_direction(task: str, alpha: float, w: str, k: int) -> tuple[int, np.ndarray]:
    """exp29 gen.pn_direction(task, arm, w, k) with arm = 'PN_a1' / 'PN_a2', verbatim arithmetic."""
    seed = stable_seed(task, s4_arm(alpha), w, k)
    x = np.random.Generator(np.random.PCG64(seed)).standard_normal(4096)
    return seed, (x / np.linalg.norm(x)).astype(np.float32)


def s5_direction(task: str, w: str, k: int, tag: str = "PN5") -> tuple[int, np.ndarray]:
    """exp27 gen5.pn5_direction, verbatim arithmetic (same u at alpha 1 and 2)."""
    seed = stable_seed(task, tag, w, k)
    x = np.random.Generator(np.random.PCG64(seed)).standard_normal(D_MODEL)
    return seed, (x / np.linalg.norm(x)).astype(np.float32)


def direction(seeds: str, task: str, alpha: float, w: str, k: int) -> tuple[int, np.ndarray]:
    return s4_direction(task, alpha, w, k) if seeds == "S4" else s5_direction(task, w, k)


def profile_masks(n: np.ndarray, task: str) -> dict[str, dict[str, np.ndarray]]:
    """S2 profiles of U_abs: unit [12, |S|] float32 and edit mask [12, |S|] bool for P_top, P_rest, P_shuf."""
    n = n.astype(np.float64)
    q75 = float(np.percentile(n, 75))
    top = n >= q75
    rest = ~top
    fro = float(np.linalg.norm(n))
    out = {}
    for name, m in (("P_top", top), ("P_rest", rest)):
        part = n * m
        scale = fro / float(np.linalg.norm(part))
        out[name] = {"unit": (part * scale).astype(np.float32), "mask": m.copy(), "scale": scale,
                     "energy_share": float((part ** 2).sum() / (n ** 2).sum()), "q75": q75}
    perm = np.random.Generator(np.random.PCG64(stable_seed(task, "SHUF"))).permutation(n.shape[1])
    out["P_shuf"] = {"unit": n[:, perm].astype(np.float32), "mask": np.ones_like(top), "perm": perm.tolist(),
                     "scale": 1.0, "energy_share": 1.0, "q75": q75}
    return out


def bf_star(u_bf: np.ndarray, n_abs: np.ndarray) -> np.ndarray:
    """U_bf*[l, :] = U_bf[l, :] * ||U_abs[l, :]|| / ||U_bf[l, :]|| (float64 arithmetic, float32 result)."""
    ub = u_bf.astype(np.float64)
    na = n_abs.astype(np.float64)
    s = np.linalg.norm(na, axis=1) / np.linalg.norm(ub, axis=1)
    return (ub * s[:, None]).astype(np.float32)


def dose_ratios(unit: np.ndarray, ref: np.ndarray) -> dict[str, float]:
    """Dose of a unit relative to D1's U_abs: mean of per-cell ratios, ratio of Frobenius norms, block-12 means."""
    u = unit.astype(np.float64)
    r = ref.astype(np.float64)
    return {"mean_cell_ratio": float((u / np.maximum(r, 1e-6)).mean()),
            "fro_ratio": float(np.linalg.norm(u) / np.linalg.norm(r)),
            "b12_mean_ratio": float(u[0].mean() / r[0].mean())}
