#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers from raw files (a different code path from the pipeline:
pandas / sklearn / a fresh DiM implementation), plus placebo runs of the same statistics on shuffled labels.
Writes results/verify_headlines.json; every mismatch is listed.

  uv run src/verify_headlines.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
BANNED = {"t1": "bfs", "t2": "dijkstra"}
SUB = {"t1": "dfs", "t2": "bf_spfa"}
UNRES = {"no_code", "unresolved", None}


def jl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def within_auc_sk(y: np.ndarray, s: np.ndarray, g: np.ndarray) -> float:
    """Pairwise within-group AUC via explicit pair enumeration (ties count 1/2)."""
    num = den = 0.0
    for gg in np.unique(g):
        m = g == gg
        pos, neg = s[m & (y == 1)], s[m & (y == 0)]
        if len(pos) and len(neg):
            d = pos[:, None] - neg[None, :]
            num += (d > 0).sum() + 0.5 * (d == 0).sum()
            den += d.size
    return num / den if den else float("nan")


def main() -> None:
    out: dict = {"mismatches": [], "checks": {}}

    def check(name: str, ours: float | None, pipeline: float | None, tol: float = 1e-6) -> None:
        ok = (ours is None and pipeline is None) or (ours is not None and pipeline is not None and
                                                      abs(ours - pipeline) <= tol)
        out["checks"][name] = {"rederived": ours, "pipeline": pipeline, "match": bool(ok)}
        if not ok:
            out["mismatches"].append(name)

    # 1) fresh pool banned share per task (raw labelled rows, pandas)
    c1 = pd.DataFrame(jl(RES / "labelled_c1.jsonl"))
    fp = json.loads((RES / "fresh_pool_summary.json").read_text())
    for t in ("t1", "t2"):
        d = c1[(c1.task == t) & (~c1.label.isin(["no_code", "unresolved"])) & c1.label.notna()]
        check(f"fresh_pool_banned_share_{t}", float((d.label == BANNED[t]).mean()),
              fp["per_task"][t]["pooled"]["banned_share"])

    # 2) same-seed vs different-seed idea change rates (raw CRN rows joined to labels by crn_row)
    raw = {r["crn_row"]: r for r in jl(RES / "raw" / "e5_crn.jsonl")}
    lab = pd.DataFrame([{"crn_row": r["crn_row"], "label": r["label"]} for r in jl(RES / "labelled_crn.jsonl")])
    lab["task"] = lab.crn_row.map(lambda k: raw[k]["task"])
    lab["cond"] = lab.crn_row.map(lambda k: raw[k]["condition"])
    lab["seed"] = lab.crn_row.map(lambda k: raw[k]["seed"])
    lab["T"] = lab.crn_row.map(lambda k: raw[k]["T"])
    ss = json.loads((RES / "same_seed.json").read_text())
    rng = np.random.default_rng(0)
    for (t, cond), d in lab.groupby(["task", "cond"]):
        piv = d.pivot_table(index="seed", columns="T", values="label", aggfunc="first")
        for T in (0.7, 1.0, 1.3):
            a, b = piv[T], piv[0.3]
            ok = a.notna() & b.notna() & ~a.isin(list(UNRES - {None})) & ~b.isin(list(UNRES - {None}))
            same = float((a[ok] != b[ok]).mean()) if ok.any() else None
            A, B = a[ok].to_numpy(), b[ok].to_numpy()
            diff = float(np.mean([A[i] != B[j] for i in range(len(A)) for j in range(len(B)) if i != j])) \
                if len(A) > 1 else None
            cell = ss["cells"].get(f"{t}|{cond}|T{T}", {})
            check(f"idea_change_same_seed_{t}_{cond}_T{T}", same, cell.get("same_seed", {}).get("idea_change_rate"))
            check(f"idea_change_diff_seed_{t}_{cond}_T{T}", diff,
                  cell.get("different_seed", {}).get("idea_change_rate"))
            # placebo: shuffle which seed's T=0.3 program is paired -> same-seed rate should match diff-seed rate
            if len(A) > 1:
                pl = [float(np.mean(A != rng.permutation(B))) for _ in range(200)]
                out["checks"][f"placebo_shuffled_pairing_{t}_{cond}_T{T}"] = {
                    "same_seed_rate": same, "shuffled_pairing_mean": float(np.mean(pl)),
                    "different_seed_rate": diff}

    # 3) transfer-test ratios from the per-sequence CE lists
    tt = RES / "transfer_test.json"
    ts = RES / "transfer_summary.json"
    if tt.exists() and ts.exists():
        T_ = json.loads(tt.read_text())
        S_ = json.loads(ts.read_text())
        if "instruct" in T_ and "base" in T_:
            ci = np.array(T_["instruct"]["ce_clean_per_seq"])
            cb = np.array(T_["base"]["ce_clean_per_seq"])
            for L in T_["instruct"]["layers"]:
                di = np.array(T_["instruct"]["layers"][L]["ce_splice_per_seq"]) - ci
                db = np.array(T_["base"]["layers"][L]["ce_splice_per_seq"]) - cb
                check(f"transfer_ratio_L{L}", float(di.mean() / db.mean()), S_["layers"][L]["ratio"], tol=1e-9)

    # 4) exp3 discovery: DiM leave-one-paraphrase-out within-paraphrase AUC from the raw npz states
    try:
        sys.path.insert(0, str(ROOT / "src"))
        from core import EXP3_SRC  # only for the location of the read-only iteration-1 states

        lp = json.loads((RES / "layer_probe.json").read_text())
        disc = json.loads((RES / "readout_i_discovery.json").read_text())
        meta = json.loads((ROOT / "inputs" / "exp3" / "states" / "T2_meta.json").read_text())["rows"]
        parts = sorted((EXP3_SRC / "states").glob("T2_part_*.npz"))
        L = lp["choice"]["L1"]
        li = list(range(8, 29)).index(L)
        pj = ["R", "k8", "k16", "k32", "k64", "k_fork", "k_pre", "k_post"].index("k16")
        # float32 like the pipeline: near-identical states (shared prefixes) give near-tied DiM scores whose order
        # is precision-sensitive; the float64 value is reported separately as a precision sensitivity
        X = np.concatenate([np.load(p)["X"][:, pj, li, :] for p in parts]).astype(np.float32)
        Mk = np.concatenate([np.load(p)["mask"][:, pj] for p in parts])
        keep = [i for i, r in enumerate(meta) if r["arm"] == "G2" and r["label"] in ("dijkstra", "bellman_ford_spfa")
                and Mk[i]]
        y = np.array([int(meta[i]["label"] == "dijkstra") for i in keep])
        g = np.array([int(meta[i]["paraphrase_id"]) for i in keep])
        H = X[keep]

        def lopo_dim(yv: np.ndarray) -> np.ndarray:
            s = np.full(len(yv), np.nan)
            for gg in np.unique(g):
                tr, te = g != gg, g == gg
                w = H[tr][yv[tr] == 1].mean(0) - H[tr][yv[tr] == 0].mean(0)
                w /= np.linalg.norm(w)
                mid = (H[tr][yv[tr] == 1].mean(0) + H[tr][yv[tr] == 0].mean(0)) / 2
                st, se = (H[tr] - mid) @ w, (H[te] - mid) @ w
                s[te] = (se - st.mean()) / st.std()
            return s

        s = lopo_dim(y)
        key = f"t2|L{L}|k16"
        H64 = X[keep].astype(np.float64)
        H, H32 = H64, H
        out["checks"][f"precision_sensitivity_float64_{key}"] = {"within_auc_float64": within_auc_sk(y, lopo_dim(y), g)}
        H = H32
        check(f"discovery_dim_within_auc_{key}", within_auc_sk(y, s, g),
              disc["configs"][key]["methods"]["raw_dim"]["auc_within"], tol=1e-6)
        check(f"discovery_dim_pooled_auc_{key}", float(roc_auc_score(y, s)),
              disc["configs"][key]["methods"]["raw_dim"]["auc_pooled"], tol=1e-6)
        pl = []
        for _ in range(50):
            yp = y.copy()
            for gg in np.unique(g):
                m = g == gg
                yp[m] = rng.permutation(y[m])
            pl.append(within_auc_sk(yp, lopo_dim(yp), g))
        out["checks"][f"placebo_within_paraphrase_permuted_{key}"] = {
            "observed": within_auc_sk(y, s, g), "placebo_mean": float(np.nanmean(pl)),
            "placebo_q95": float(np.nanquantile(pl, 0.95))}
    except Exception as e:  # noqa: BLE001
        out["checks"]["discovery_rederivation_error"] = repr(e)[:300]

    # 5) replication: exp3-fitted DiM on the fresh pool's k_pre states (raw tensors + labels), sklearn AUC
    try:
        E = np.load(RES / "tensors" / "e2_states.npz")
        st, layers = E["states"], [int(x) for x in E["layers"]]
        runs = json.loads((RES / "e2_meta.json").read_text())["runs"]
        labs = {(r["task"], r["template"], r["sample_id"]): r["label"] for r in jl(RES / "labelled_c1.jsonl")}
        rep = json.loads((RES / "readout_i_replication.json").read_text())
        disc = json.loads((RES / "readout_i_discovery.json").read_text())
        for t in ("t1", "t2"):
            for L in layers:
                key = f"{t}|L{L}|k_pre"
                obj = disc["objects"].get(key)
                if obj is None or key not in rep["configs"] or "transfer_from_exp3" not in rep["configs"][key]:
                    continue
                w, mid = np.array(obj["raw_dim"]["w"]), obj["raw_dim"]["mid"]
                rows = [m for m in runs if m["task"] == t and labs.get((t, m["template"], m["sample_id"]))
                        in (BANNED[t], SUB[t]) and np.isfinite(st[m["i"], 0, 2, layers.index(L), 0])]
                y = np.array([int(labs[(t, m["template"], m["sample_id"])] == BANNED[t]) for m in rows])
                H = np.stack([st[m["i"], 0, 2, layers.index(L)].astype(np.float64) for m in rows])
                s = H @ w - mid
                if 0 < y.sum() < len(y):
                    check(f"replication_dim_auc_{key}", float(roc_auc_score(y, s)),
                          rep["configs"][key]["transfer_from_exp3"]["raw_dim"]["auc_pooled"], tol=2e-3)
                    out["checks"][f"placebo_replication_shuffled_{key}"] = {
                        "placebo_mean_auc": float(np.mean([roc_auc_score(rng.permutation(y), s) for _ in range(200)]))}
    except Exception as e:  # noqa: BLE001
        out["checks"]["replication_rederivation_error"] = repr(e)[:300]

    # 6) thought anchors: TVD of the first trace from the raw continuation rows
    try:
        ta = json.loads((RES / "thought_anchors.json").read_text())
        conts = jl(RES / "labelled_c3.jsonl")
        for tid, tr in list(ta.get("traces", {}).items())[:4]:
            cs = [c for c in conts if str(c["trace_id"]) == tid]

            def oc(c: dict) -> str:
                e = c.get("early_label")
                if e in (None, "None") and c.get("reached_code"):
                    return str(c.get("label") or "undecided")
                return str(e or "undecided")

            df = pd.DataFrame({"k": [c["boundary_k"] for c in cs], "o": [oc(c) for c in cs]})
            tab = pd.crosstab(df.k, df.o, normalize="index")
            tv = [float(0.5 * (tab.loc[k] - tab.loc[k - 1]).abs().sum()) for k in range(1, int(df.k.max()) + 1)]
            for k, (a, b) in enumerate(zip(tv, tr["tvd"]), start=1):
                check(f"thought_anchor_tvd_trace{tid}_k{k}", a, b, tol=1e-9)
    except Exception as e:  # noqa: BLE001
        out["checks"]["thought_anchor_rederivation_error"] = repr(e)[:300]

    out["n_checks"] = sum(1 for v in out["checks"].values() if isinstance(v, dict) and "match" in v)
    out["n_mismatches"] = len(out["mismatches"])
    (RES / "verify_headlines.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({"n_checks": out["n_checks"], "n_mismatches": out["n_mismatches"],
                      "mismatches": out["mismatches"]}, indent=1))


if __name__ == "__main__":
    main()
