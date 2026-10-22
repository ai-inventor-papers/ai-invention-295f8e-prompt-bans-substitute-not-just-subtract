#!/usr/bin/env python3
"""S7 C5: does the residual state at the read position R predict per-wording compliance with a modal ban?

Wordings: the modal-ban paraphrases of exp1-exp5 (t1 ban BFS, t2 ban Dijkstra; ~100) + the 5 frozen templates of
this artifact (experiment 6, banned share from S4 arm a). References: the draw's mention twins, else its baseline.
Each prompt is rebuilt under its own scaffold (stored ids where they exist) and h_R taken at layers 8-28, where
layer l = hidden_states[l] = output of decoder block l-1 (exp4 convention; exp2 stores hidden_states[l+1]).
Projection onto a leave-one-experiment-out shared ban direction, z-scored per layer, averaged over 8-28; combined
within-cell Spearman with a stratified permutation null, a random-direction null and a split-half noise ceiling;
the same test on exp4's decommitment axis; substitute (DFS) decodability beyond the projection.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from cfg import (C5_LAYERS, DATA_DIR, INPUTS_ITER1, N_PERM_C5, N_RANDOM_DIRS, PROMPTS_DIR, RESULTS_DIR, TEMPLATE_IDS,
                 WORK_DIR, X_KEY, chat_ids, read_jsonl, write_json)

HS_IDX = list(range(8, 30))  # hidden_states indices computed (8..28 primary, 9..29 for the exp2 cross-check)
BANNED = {"exp1": {"t1": "bfs", "t2": "dijkstra"}, "exp2": {"t1": "bfs", "t2": "dijkstra"},
          "exp3": {"t1": "BFS", "t2": "dijkstra"}, "exp4": {"t1": "bfs", "t2": "dijkstra"},
          "exp5": {"t1": "bfs", "t2": "dijkstra"}, "exp6": {"t1": "bfs", "t2": "dijkstra"}}
SUBST = {"exp1": "dfs", "exp2": "dfs", "exp3": "DFS", "exp4": "dfs", "exp5": "dfs", "exp6": "dfs"}
NO_CODE = {"no_code", "None", None, "unparseable"}


def _s(v: Any) -> str:
    return str(v)


def _labels_summary(labels: list[Any], exp: str, task: str) -> dict[str, Any]:
    ban = BANNED[exp][task]
    y = np.array([lab == ban for lab in labels], dtype=float)
    att = [lab for lab in labels if lab not in NO_CODE]
    nonb = [lab for lab in att if lab != ban]
    return {"n": len(labels), "banned_share": float(y.mean()) if len(y) else float("nan"), "y": y.tolist(),
            "n_attempted_nonbanned": len(nonb),
            "subst_share_nonbanned": (sum(lab == SUBST[exp] for lab in nonb) / len(nonb)) if nonb else float("nan"),
            "composition": dict(Counter(_s(lab) for lab in labels))}


def build_wordings(tok: Any) -> list[dict[str, Any]]:
    W: list[dict[str, Any]] = []
    I = INPUTS_ITER1
    # ---------------- exp1 (canonical suite): conditions.json prompts, chat template, thinking off
    cond = json.loads((I / "exp1/prompts/conditions.json").read_text())
    s1 = read_jsonl(I / "exp1/data/samples.jsonl")
    for t, x in (("t1", "bfs"), ("t2", "dijkstra")):
        for kind in ("ban", "mention"):
            for c in cond["tasks"][t]["conditions"][f"{kind}:{x}"]:
                rec = {"exp": "exp1", "task": t, "kind": kind, "wid": f"exp1|{t}|{kind}|{c['paraphrase_id']}",
                       "text": c["segment"], "ids": chat_ids(tok, c["prompt"]), "ids_source": "rebuilt"}
                if kind == "ban":
                    labs = [r["label"] for r in s1 if r["task"] == t and r["condition"] == f"ban:{x}"
                            and _s(r["paraphrase_id"]) == _s(c["paraphrase_id"])]
                    rec.update(_labels_summary(labs, "exp1", t))
                W.append(rec)
    # ---------------- exp2: stored prompt ids; phase C labels
    p2 = read_jsonl(I / "exp2/prompts/prompts.jsonl")
    s2 = read_jsonl(I / "exp2/data/samples_phaseC.jsonl")
    for t, x in (("t1", "bfs"), ("t2", "dijkstra")):
        for kind in ("ban", "mention"):
            for r in p2:
                if r["task"] == t and r["condition"] == f"{kind}:{x}" and r["kind"] == "geom":
                    ids = r["prompt_ids"] if isinstance(r["prompt_ids"], list) else json.loads(r["prompt_ids"])
                    rec = {"exp": "exp2", "task": t, "kind": kind, "wid": f"exp2|{r['prompt_id']}",
                           "text": r["text"].split("\n\n")[0], "ids": ids, "ids_source": "stored",
                           "exp2_prompt_id": r["prompt_id"]}
                    if kind == "ban":
                        labs = [q["label"] for q in s2 if q["prompt_id"] == r["prompt_id"]]
                        rec.update(_labels_summary(labs, "exp2", t))
                    W.append(rec)
    # ---------------- exp3: stored prompt_token_ids; pools labels; reference = baseline
    p3 = json.loads((I / "exp3/prompts/prompts.json").read_text())
    s3 = read_jsonl(I / "exp3/generations/pools.jsonl")
    for key, r in p3.items():
        T, kind, pid = key.split("|")
        t = T.lower()
        ids = r["prompt_token_ids"] if isinstance(r["prompt_token_ids"], list) else json.loads(r["prompt_token_ids"])
        rec = {"exp": "exp3", "task": t, "kind": "ban" if kind == "ban" else "reference_baseline",
               "wid": f"exp3|{key}", "text": r["segment"], "ids": ids, "ids_source": "stored"}
        if kind == "ban":
            labs = [q["label"] for q in s3 if q["task"] == T and q["condition"] == "ban"
                    and _s(q["paraphrase_id"]) == _s(pid)]
            rec.update(_labels_summary(labs, "exp3", t))
        W.append(rec)
    # ---------------- exp4: rebuild from segments with exp4's scaffold (SPEC from exp4 common.py)
    spec4 = _exp4_spec()
    idx4 = json.loads((I / "exp4/cache/hR_index.json").read_text())["groups"]
    s4 = read_jsonl(I / "exp4/data/samples.jsonl")
    for T, x in (("T1", "bfs"), ("T2", "dijkstra")):
        t = T.lower()
        for kind in ("ban", "mention"):
            g = idx4[f"{T}|{kind}:{x}"]
            segs = g["segments"] if isinstance(g["segments"], list) else json.loads(g["segments"])
            for i, seg in enumerate(segs):
                text = seg + "\n\n" + spec4[T]
                rec = {"exp": "exp4", "task": t, "kind": kind, "wid": f"exp4|{T}|{kind}|{i}", "text": seg,
                       "ids": chat_ids(tok, text), "ids_source": "rebuilt", "exp4_row": i}
                if kind == "ban":
                    labs = [q["label"] for q in s4 if q["task"] == T and q["condition"] == f"ban:{x}"
                            and q.get("segment") == seg]
                    rec.update(_labels_summary(labs, "exp4", t))
                W.append(rec)
    # ---------------- exp5: instruct chat, stored token ids; reference = the chat baselines used
    p5 = json.loads((I / "exp5/data/prompts.json").read_text())
    s5b = read_jsonl(I / "exp5/runs/labelled_instruct_chat__ban.jsonl")
    s5n = read_jsonl(I / "exp5/runs/labelled_instruct_chat__baseline.jsonl")
    for t in ("t1", "t2"):
        used_base = {q["prompt_id"] for q in s5n if q["task"] == t}
        for kind in ("ban", "baseline"):
            for r in p5["chat"][t][kind]:
                if kind == "baseline" and r["id"] not in used_base:
                    continue
                rec = {"exp": "exp5", "task": t, "kind": "ban" if kind == "ban" else "reference_baseline",
                       "wid": f"exp5|{t}|{r['id']}", "text": r["seg"], "ids": list(r["token_ids"]),
                       "ids_source": "stored"}
                if kind == "ban":
                    labs = [q["label"] for q in s5b if q["task"] == t and q["prompt_id"] == r["id"]]
                    rec.update(_labels_summary(labs, "exp5", t))
                W.append(rec)
    # ---------------- exp6: this artifact's frozen templates (arm a samples) vs frozen mention twins
    fp = json.loads((PROMPTS_DIR / "frozen_prompts.json").read_text())
    s6 = read_jsonl(DATA_DIR / "samples.jsonl")
    for t in ("t1", "t2"):
        for w in TEMPLATE_IDS:
            tw = fp["tasks"][t]["templates"][w]
            labs = [q["label"] for q in s6 if q["task"] == t and q["condition"] == "a" and q["template"] == w]
            if labs:
                rec = {"exp": "exp6", "task": t, "kind": "ban", "wid": f"exp6|{t}|{w}", "text": tw["ban"]["segment"],
                       "ids": tw["ban"]["ids"], "ids_source": "frozen"}
                rec.update(_labels_summary(labs, "exp6", t))
                W.append(rec)
            W.append({"exp": "exp6", "task": t, "kind": "mention", "wid": f"exp6|{t}|{w}|mention",
                      "text": tw["mention"]["segment"], "ids": tw["mention"]["ids"], "ids_source": "frozen"})
    return W


def _exp4_spec() -> dict[str, str]:
    src = (INPUTS_ITER1 / "exp4" / "common.py").read_text()
    m = re.search(r"SPEC = (\{.*?\n\})", src, re.DOTALL)
    return eval(m.group(1), {"__builtins__": {}})  # literal dict of string constants from the snapshotted file


def compute_states(model: Any, W: list[dict[str, Any]]) -> np.ndarray:
    from engine import prefill

    H = np.zeros((len(W), len(HS_IDX), 4096), dtype=np.float32)
    for i, w in enumerate(W):
        pre = prefill(model, w["ids"], hidden_layers=HS_IDX)
        H[i] = np.stack([pre["hR"][l] for l in HS_IDX])
        del pre
    return H


def crosscheck(W: list[dict[str, Any]], H: np.ndarray) -> dict[str, Any]:
    """Cosine of recomputed h_R with exp2 (hidden_states[l+1]) and exp4 (hidden_states[l]) caches."""
    out: dict[str, Any] = {"exp2": [], "exp4": []}
    z = np.load(INPUTS_ITER1 / "exp2/cache/hR_subset.npz")
    idx2 = json.loads((INPUTS_ITER1 / "exp2/cache/hR_subset_index.json").read_text())
    pos2 = {r["prompt_id"]: k for k, r in enumerate(idx2)}
    for i, w in enumerate(W):
        if w["exp"] == "exp2" and w.get("exp2_prompt_id") in pos2:
            k = pos2[w["exp2_prompt_id"]]
            cs = []
            for l in C5_LAYERS:
                a = H[i, HS_IDX.index(l + 1)]
                b = z[f"L{l}"][k].astype(np.float32)
                cs.append(float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)))
            out["exp2"].append(min(cs))
    for T, x in (("T1", "bfs"), ("T2", "dijkstra")):
        for kind in ("ban", "mention"):
            arr = np.load(INPUTS_ITER1 / f"exp4/cache/hR_{T}_{kind}-{x}.npy").astype(np.float32)
            for i, w in enumerate(W):
                if w["exp"] == "exp4" and w["task"] == T.lower() and w["kind"] == kind:
                    r = w["exp4_row"]
                    cs = []
                    for li, l in enumerate(C5_LAYERS):
                        a = H[i, HS_IDX.index(l)]
                        b = arr[r, li]
                        cs.append(float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)))
                    out["exp4"].append(min(cs))
    res = {k: {"n": len(v), "min_cos": float(np.min(v)) if v else None,
               "share_ge_0_99": float(np.mean(np.array(v) >= 0.99)) if v else None} for k, v in out.items()}
    return res


def projections(W: list[dict[str, Any]], H: np.ndarray, dirs: dict[str, np.ndarray] | None = None,
                loeo: bool = True) -> np.ndarray:
    """pi_w: per layer (h_R(w) - mean ref_{e,t}) . d_l, z-scored within layer across ban wordings, mean over layers.
    dirs: fixed per-task directions {task: [L, d]} (decommitment axis) else leave-one-experiment-out ban direction."""
    Lidx = [HS_IDX.index(l) for l in C5_LAYERS]
    exps = sorted({w["exp"] for w in W})
    ban = [i for i, w in enumerate(W) if w["kind"] == "ban"]
    ref_mean: dict[tuple[str, str], np.ndarray] = {}
    shift: dict[tuple[str, str], np.ndarray] = {}
    for e in exps:
        for t in ("t1", "t2"):
            r = [i for i, w in enumerate(W) if w["exp"] == e and w["task"] == t and w["kind"] != "ban"]
            b = [i for i in ban if W[i]["exp"] == e and W[i]["task"] == t]
            if not r or not b:
                continue
            ref_mean[(e, t)] = H[r][:, Lidx].mean(0)
            shift[(e, t)] = H[b][:, Lidx].mean(0) - ref_mean[(e, t)]
    proj = np.zeros((len(ban), len(Lidx)))
    for k, i in enumerate(ban):
        e, t = W[i]["exp"], W[i]["task"]
        if dirs is not None:
            d = dirs[t]
        else:
            others = [s / np.linalg.norm(s, axis=-1, keepdims=True) for (ee, tt), s in shift.items() if ee != e]
            d = np.mean(others, axis=0)
        d = d / np.linalg.norm(d, axis=-1, keepdims=True)
        proj[k] = np.sum((H[i][Lidx] - ref_mean[(e, t)]) * d, axis=-1)
    z = (proj - proj.mean(0)) / (proj.std(0) + 1e-12)
    return z.mean(1), proj


def stage_c5() -> dict[str, Any]:
    from analysis import c5_test, split_half_ceiling
    from engine import load_model

    tok, model = load_model()
    W = build_wordings(tok)
    H = compute_states(model, W)
    np.savez(WORK_DIR / "c5_hR.npz", H=H, wids=np.array([w["wid"] for w in W]),
             kinds=np.array([w["kind"] for w in W]), tasks=np.array([w["task"] for w in W]),
             exps=np.array([w["exp"] for w in W]))
    xc = crosscheck(W, H)
    logger.info(f"C5 cross-check: {xc}")
    ban_idx = [i for i, w in enumerate(W) if w["kind"] == "ban" and w.get("n", 0) > 0]
    Wb = [W[i] for i in ban_idx]
    # keep only ban wordings with samples, but references for every experiment
    Wuse = [w for w in W if w["kind"] != "ban"] + Wb
    Huse = np.concatenate([H[[i for i, w in enumerate(W) if w["kind"] != "ban"]], H[ban_idx]], 0)
    ban_pos = [i for i, w in enumerate(Wuse) if w["kind"] == "ban"]
    share = np.array([Wuse[i]["banned_share"] for i in ban_pos])
    cells = [f"{Wuse[i]['exp']}|{Wuse[i]['task']}" for i in ban_pos]
    ys = [np.array(Wuse[i]["y"]) for i in ban_pos]
    pi, proj = projections(Wuse, Huse)
    res: dict[str, Any] = {"n_wordings": len(ban_pos), "n_references": len(Wuse) - len(ban_pos),
                           "per_experiment": dict(Counter(c for c in cells)), "crosscheck": xc,
                           "layer_convention": "layer l = hidden_states[l] (output of decoder block l-1), l = 8..28"}
    test = c5_test(pi, share, cells, n_perm=N_PERM_C5)
    # random-direction null: identical pipeline with random unit directions per layer
    rng = np.random.default_rng(11)
    null_rhos = []
    for k in range(N_RANDOM_DIRS):
        d = rng.normal(size=(len(C5_LAYERS), 4096))
        dirs = {"t1": d, "t2": d}
        pk, _ = projections(Wuse, Huse, dirs=dirs)
        null_rhos.append(c5_test(pk, share, cells, n_perm=1, n_boot=1, seed=k)["rho"])
    null_rhos = np.array(null_rhos)
    test["random_direction_null"] = {"mean": float(np.nanmean(null_rhos)), "p_2_5": float(np.nanpercentile(null_rhos, 2.5)),
                                     "share_le_observed": float(np.nanmean(null_rhos <= test["rho"]))}
    ceil = split_half_ceiling(ys, cells)
    per_layer = []
    for li, l in enumerate(C5_LAYERS):
        per_layer.append({"layer": l, "rho": c5_test(proj[:, li], share, cells, n_perm=1, n_boot=1)["rho"]})
    res["shared_ban_direction"] = {"test": test, "noise_ceiling": ceil, "per_layer_descriptive": per_layer}
    # decommitment axis (exp4, fixed per task)
    dc = {t: np.stack([np.load(INPUTS_ITER1 / f"exp4/directions/d_dc_T{t[-1]}_L{l}.npy") for l in C5_LAYERS])
          for t in ("t1", "t2")}
    pdc, projdc = projections(Wuse, Huse, dirs=dc)
    tdc = c5_test(pdc, share, cells, n_perm=N_PERM_C5)
    res["decommitment_axis"] = {"test": tdc, "noise_ceiling": ceil}
    # substitute decodability (T1): DFS share among attempted non-banned, LOEO ridge on PCA(10) + pi vs pi alone
    res["substitute_decodability"] = substitute_decodability(Wuse, Huse, ban_pos, pi)
    res["wordings"] = [{k: v for k, v in Wuse[i].items() if k not in ("ids", "y")} | {"pi": float(pi[j]),
                       "pi_dc": float(pdc[j])} for j, i in enumerate(ban_pos)]
    write_json(RESULTS_DIR / "c5.json", res)
    logger.info(f"C5 shared-direction rho={test['rho']:.3f} p={test['p_one_sided']:.4f}; decommitment rho="
                f"{tdc['rho']:.3f} p={tdc['p_one_sided']:.4f}; ceiling={ceil['mean_ceiling']:.3f}")
    return res


def substitute_decodability(W: list[dict[str, Any]], H: np.ndarray, ban_pos: list[int], pi: np.ndarray,
                            n_perm: int = 1000) -> dict[str, Any]:
    from sklearn.decomposition import PCA
    from sklearn.linear_model import Ridge

    out = {}
    Lidx = [HS_IDX.index(l) for l in C5_LAYERS]
    for t in ("t1", "t2"):
        rows = [(j, i) for j, i in enumerate(ban_pos) if W[i]["task"] == t and W[i]["n_attempted_nonbanned"] > 0
                and np.isfinite(W[i]["subst_share_nonbanned"])]
        if len(rows) < 10:
            out[t] = {"testable": False, "reason": f"only {len(rows)} wordings with non-banned samples"}
            continue
        y = np.array([W[i]["subst_share_nonbanned"] for _, i in rows])
        wts = np.array([W[i]["n_attempted_nonbanned"] for _, i in rows], dtype=float)
        if np.std(y) < 1e-9:
            out[t] = {"testable": False, "reason": "no variance in substitute share"}
            continue
        X = H[[i for _, i in rows]][:, Lidx].mean(1)
        p = pi[[j for j, _ in rows]][:, None]
        exps = np.array([W[i]["exp"] for _, i in rows])

        def loeo_r2(yy: np.ndarray, full: bool) -> float:
            pred = np.zeros_like(yy)
            for e in sorted(set(exps)):
                tr, te = exps != e, exps == e
                if tr.sum() < 5:
                    pred[te] = np.average(yy[tr], weights=wts[tr]) if tr.any() else 0.0
                    continue
                if full:
                    pca = PCA(n_components=min(10, tr.sum() - 1)).fit(X[tr])
                    Ztr = np.hstack([pca.transform(X[tr]), p[tr]])
                    Zte = np.hstack([pca.transform(X[te]), p[te]])
                else:
                    Ztr, Zte = p[tr], p[te]
                m = Ridge(alpha=1.0).fit(Ztr, yy[tr], sample_weight=wts[tr])
                pred[te] = m.predict(Zte)
            ybar = np.average(yy, weights=wts)
            return float(1 - np.sum(wts * (yy - pred) ** 2) / np.sum(wts * (yy - ybar) ** 2))

        r2_full, r2_pi = loeo_r2(y, True), loeo_r2(y, False)
        d_obs = r2_full - r2_pi
        rng = np.random.default_rng(5)
        null = []
        for _ in range(n_perm):
            yp = rng.permutation(y)
            null.append(loeo_r2(yp, True) - loeo_r2(yp, False))
        null = np.array(null)
        out[t] = {"testable": True, "n_wordings": len(rows), "r2_pca10_plus_pi": r2_full, "r2_pi_only": r2_pi,
                  "delta_r2": d_obs, "perm_p": float((1 + np.sum(null >= d_obs)) / (1 + n_perm)),
                  "null_mean": float(null.mean()), "prediction_no_gain_holds": bool(np.mean(null >= d_obs) > 0.05)}
    return out
