#!/usr/bin/env python3
"""Exploratory activation geometry at layer 20 (the chosen convention), READ and SPEC positions (not pre-registered).

Per task: forced-mode centroids c_m (mean over the 5 'Implement m' paraphrases), the twin centroid and the ban
centroid. Reports
  - alignment of the ban displacement (h_ban - h_twin, per template) with every mode direction (c_m - c_twin):
    cosine and the projection length in residual units, beside the realised ban composition;
  - classical MDS (2-D) of the centroids with the twin / ban implemented counts per mode (for F8);
  - the distance of each condition's state to every forced centroid (does the twin sit nearest the default?).
Writes results/geometry.json."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TEMPL = ("W1", "W2", "W3", "W4", "W5")


def jl(p: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def cmds(D: np.ndarray, k: int = 2) -> np.ndarray:
    n = D.shape[0]
    J = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * J @ (D ** 2) @ J
    w, V = np.linalg.eigh(B)
    order = np.argsort(w)[::-1][:k]
    return V[:, order] * np.sqrt(np.clip(w[order], 0, None))


def main() -> dict[str, Any]:
    idx = jl(ROOT / "cache" / "states_index.jsonl")
    z = np.load(ROOT / "cache" / "states_L20.npz")
    conv = json.loads((ROOT / "results" / "layer_convention.json").read_text())["chosen"]
    H = z["H21"] if conv == "hs21" else z["H20"]
    c1 = json.loads((ROOT / "predictions" / "commit1_defaults.json").read_text())
    labels = jl(ROOT / "data" / "labels.jsonl")
    out: dict[str, Any] = {"convention": conv, "tasks": {}}
    for t in c1["tasks"]:
        D = c1["tasks"][t]["default"]
        T: dict[str, Any] = {"default": D}
        for pos in ("READ", "SPEC-1"):
            rows = [r for r in idx if r.get("task") == t and r["kind"] == "PREFILL" and r["position"] == pos]
            modes = sorted({r["mode"] for r in rows if r["condition"] == "forced"})
            cen = {m: H[[r["row"] for r in rows if r["condition"] == "forced" and r["mode"] == m]].mean(0) for m in modes}
            tw = {r["template"]: H[r["row"]] for r in rows if r["condition"] == "twin"}
            bn = {r["template"]: H[r["row"]] for r in rows if r["condition"] == "ban"}
            ctw = np.mean(list(tw.values()), 0)
            P: dict[str, Any] = {"dist_twin_to_forced": {m: float(np.linalg.norm(ctw - c)) for m, c in cen.items()},
                                 "norm_twin": float(np.linalg.norm(ctw))}
            if bn:
                align = {m: [] for m in modes}
                proj = {m: [] for m in modes}
                for w in TEMPL:
                    if w in bn and w in tw:
                        d = bn[w] - tw[w]
                        for m in modes:
                            u = cen[m] - tw[w]
                            align[m].append(float(d @ u / (np.linalg.norm(d) * np.linalg.norm(u) + 1e-12)))
                            proj[m].append(float(d @ u / (np.linalg.norm(u) + 1e-12)))
                P["ban_displacement_norm"] = float(np.mean([np.linalg.norm(bn[w] - tw[w]) for w in bn if w in tw]))
                P["ban_alignment_cos"] = {m: float(np.mean(v)) for m, v in align.items()}
                P["ban_projection"] = {m: float(np.mean(v)) for m, v in proj.items()}
                P["ban_aligned_mode"] = max(align, key=lambda m: np.mean(align[m]))
                # mode-specific contrast: remove the component shared by all forced prompts (c_m - mean of centroids)
                cbar = np.mean([cen[m] for m in modes], 0)
                contrast = {}
                for m in modes:
                    u = cen[m] - cbar
                    vals = [float((bn[w] - tw[w]) @ u / (np.linalg.norm(bn[w] - tw[w]) * np.linalg.norm(u) + 1e-12))
                            for w in TEMPL if w in bn and w in tw]
                    contrast[m] = float(np.mean(vals))
                P["ban_contrast_cos"] = contrast
                P["ban_contrast_mode"] = max(contrast, key=contrast.get)
                P["twin_contrast_cos"] = {m: float((ctw - cbar) @ (cen[m] - cbar) /
                                                   (np.linalg.norm(ctw - cbar) * np.linalg.norm(cen[m] - cbar) + 1e-12))
                                          for m in modes}
                cbn = np.mean(list(bn.values()), 0)
                P["dist_ban_to_forced"] = {m: float(np.linalg.norm(cbn - c)) for m, c in cen.items()}
            # MDS of centroids + twin + ban
            names = list(modes) + ["twin"] + (["ban"] if bn else [])
            X = np.stack([cen[m] for m in modes] + [ctw] + ([np.mean(list(bn.values()), 0)] if bn else []))
            Dm = np.linalg.norm(X[:, None] - X[None], axis=-1)
            Y = cmds(Dm)
            P["mds"] = {n: Y[i].tolist() for i, n in enumerate(names)}
            T[pos] = P
        tw_c = Counter(r["label"] for r in labels if r["task"] == t and r["arm"] == "TWIN" and r.get("passed"))
        bn_c = Counter(r["label"] for r in labels if r["task"] == t and r["arm"] == "BAN" and r.get("passed"))
        T["implemented_twin"] = dict(tw_c)
        T["implemented_ban"] = dict(bn_c)
        out["tasks"][t] = T
    (ROOT / "results" / "geometry.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    r = main()
    for t, v in r["tasks"].items():
        R = v["READ"]
        print(t, "default", v["default"], "ban-contrast", R.get("ban_contrast_mode"),
              {m: round(c, 3) for m, c in (R.get("ban_contrast_cos") or {}).items()}, "ban impl", v["implemented_ban"])
