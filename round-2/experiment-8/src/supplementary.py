#!/usr/bin/env python3
"""Supplementary descriptive statistics (not part of the pre-registered decision; analysis.py stays as committed).

1. Per-program distributions of the banned-algorithm log-likelihood shift dl(p, arm) = l(p | arm) - l(p | b) for
   every arm and task (median, IQR, share negative), pooled over templates and per template.
2. Per-program FRLP leverage: the share of each cell's importance mass carried by its top program (ESS context).
3. Behavioural contrasts that bear on the knockout-vs-splice comparison (c vs a, d vs a matched flips).
4. Opening-line distribution per arm (all programs and banned-algorithm programs): where the ban acts.
5. The natural-proposal FRLP readout (natural_frlp.py), copied in for one place to read it.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

import numpy as np

from analysis import load_frlp, lw_tensor
from scipy import stats

from cfg import DATA_DIR, DATASET_DIR, RESULTS_DIR, TASKS, TEMPLATE_IDS, X_KEY, read_jsonl, wilson_ci, write_json

ARMS = ("a", "c", "d", "e", "f", "K0", "K1", "K2", "B1", "B2", "B3", "K0b", "mention")


def program_shift_distributions(F: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for t in TASKS:
        x = X_KEY[t]
        A = F[t]["alg"][x]
        conds = ("b",) + ARMS
        lw = lw_tensor(F, t, x, conds)
        llx = lw + A["den"][None, None, :]
        ent = {}
        for i, c in enumerate(conds[1:], start=1):
            d = llx[i] - llx[0]               # [W, M]
            if not np.isfinite(d).all():
                continue
            flat = d.ravel()
            top_share = []
            for wi in range(len(TEMPLATE_IDS)):
                v = lw[i, wi]
                w = np.exp(v - v.max())
                top_share.append(float(w.max() / w.sum()))
            ent[c] = {"median": float(np.median(flat)), "q25": float(np.percentile(flat, 25)),
                      "q75": float(np.percentile(flat, 75)), "mean": float(flat.mean()),
                      "share_negative": float(np.mean(flat < 0)),
                      "per_template_median": {w: float(np.median(d[wi])) for wi, w in enumerate(TEMPLATE_IDS)},
                      "per_program_mean_over_templates": d.mean(0).tolist(),
                      "top_program_weight_share_per_template": top_share}
        out[t] = ent
    return out


def behaviour_contrasts() -> dict[str, Any]:
    S = read_jsonl(DATA_DIR / "samples.jsonl")
    out = {}
    for t in TASKS:
        x = X_KEY[t]
        key = {}
        for s in S:
            if s["task"] == t:
                key.setdefault(s["condition"], {})[(s["template"], s["sample_id"])] = s["label"] == x
        ent = {}
        for a1, a2 in (("c", "a"), ("d", "a"), ("c", "K1"), ("c", "K2"), ("K0", "a"), ("c", "K0"), ("K0", "b")):
            if a1 in key and a2 in key:
                common = sorted(set(key[a1]) & set(key[a2]))
                n10 = sum(key[a1][k] and not key[a2][k] for k in common)
                n01 = sum(key[a2][k] and not key[a1][k] for k in common)
                p = stats.binomtest(n10, n10 + n01, 0.5).pvalue if n10 + n01 else 1.0
                ent[f"{a1}_vs_{a2}"] = {"n": len(common), f"{a1}_banned_only": n10, f"{a2}_banned_only": n01,
                                        "mcnemar_exact_p": float(p)}
        if "K0" in key:
            k = sum(key["K0"].values())
            n = len(key["K0"])
            ent["K0_banned_share"] = {"n": n, "banned": k, "share": k / n, "wilson_ci": wilson_ci(k, n)}
        out[t] = ent
    return out


def opening_lines() -> dict[str, Any]:
    S = read_jsonl(DATA_DIR / "samples.jsonl")
    out: dict[str, Any] = {}
    for t in TASKS:
        x = X_KEY[t]
        ent = {}
        for arm in ("a", "b", "c", "d", "K0", "K1", "K2"):
            A = [s for s in S if s["task"] == t and s["condition"] == arm]
            if not A:
                continue

            def first(s: dict[str, Any]) -> str:
                for ln in (s.get("code") or "").splitlines():
                    if ln.strip():
                        return "def" if ln.strip().startswith("def ") else ("import" if ln.strip().startswith(
                            ("import ", "from ")) else "other")
                return "no_code"

            allc = Counter(first(s) for s in A)
            xc = Counter(first(s) for s in A if s["label"] == x)
            ent[arm] = {"n": len(A), "opening_all": dict(allc), "opening_banned_algorithm_programs": dict(xc),
                        "share_import_opening": allc.get("import", 0) / max(1, len(A)),
                        "n_banned_algorithm": sum(1 for s in A if s["label"] == x)}
        out[t] = ent
    return out


DEP_FILE = str(DATASET_DIR / "full_data_out.json")  # art_j3Rm_lr2nzR6 (see cfg.DATASET_DIR)
USE_NOTE = {
    "concreteness_norms": "USED: the 718 neutral-noun candidates define the neutral twins (S1)",
    "llm_creativity": "context: cross-model T02 algorithm distribution vs the Dijkstra-ban landing distribution",
    "thealgorithms_python": "context: import-first opening rate of BFS / Dijkstra programs written by others",
    "kodcode_algorithmic": "context: import-first opening rate of BFS / Dijkstra programs written by others",
    "xlcost_python": "context: import-first opening rate of BFS / Dijkstra programs written by others",
    "leetcodedataset": "not used: other tasks; this experiment's tasks and hidden tests are exp1's canonical suite",
    "mercury": "not used: human solutions of other bench tasks",
    "clrs_text": "not used: tracer traces; the canonical labeller was re-checked on exp1's gold set instead",
    "humanevalplus": "not used: harness validation for other tasks",
    "enamel": "not used: efficiency references for other tasks",
}
DOC_PREFIXES = ("#", '"' * 3, "'" * 3)


def _named(e: dict[str, Any]) -> list[str]:
    na = e.get("metadata_named_algorithms") or []
    if isinstance(na, str):
        try:
            na = json.loads(na.replace("'", '"'))
        except json.JSONDecodeError:
            na = [na]
    return list(na)


def dependency_context(samples: list[dict[str, Any]]) -> dict[str, Any]:
    from pathlib import Path

    p = Path(DEP_FILE)
    if not p.exists():
        return {"available": False}
    d = json.loads(p.read_text())
    out: dict[str, Any] = {"inventory": {ds["dataset"]: {"n_examples": len(ds["examples"]),
                                                         "use": USE_NOTE.get(ds["dataset"], "not used")}
                                         for ds in d["datasets"]}}
    opening = {}
    for ds in d["datasets"]:
        if ds["dataset"] == "llm_creativity":
            c = Counter(e.get("metadata_t02_mode") or e.get("output") for e in ds["examples"]
                        if str(e.get("metadata_duplicate_of")) in ("None", ""))
            non = {k: v for k, v in c.items() if k != "dijkstra"}
            tot = sum(non.values())
            ours = Counter(s["label"] for s in samples if s["task"] == "t2" and s["condition"] == "a"
                           and s["label"] not in ("dijkstra", "no_code"))
            ot = sum(ours.values())
            out["llm_creativity_t02"] = {"population_counts": dict(c),
                                         "population_non_dijkstra_shares": {k: v / tot for k, v in non.items()},
                                         "qwen_ban_dijkstra_non_dijkstra_shares": {k: v / ot for k, v in ours.items()}}
        if ds["dataset"] not in ("thealgorithms_python", "kodcode_algorithmic", "xlcost_python"):
            continue
        for alg in ("bfs", "dijkstra"):
            rows = []
            for e in ds["examples"]:
                if alg not in _named(e) or str(e.get("metadata_duplicate_of")) not in ("None", ""):
                    continue
                code = e["input"] if ds["dataset"] == "thealgorithms_python" else e["output"]
                first = ""
                for ln in code.splitlines():
                    st = ln.strip()
                    if st and not st.startswith(DOC_PREFIXES):
                        first = st
                        break
                rows.append(first.startswith(("import ", "from ")))
            if rows:
                opening[f"{ds['dataset']}:{alg}"] = {"n": len(rows), "share_import_first": sum(rows) / len(rows)}
    out["import_first_opening_in_others_code"] = opening
    return out


def main() -> dict[str, Any]:
    F = load_frlp()
    res = {"program_shift_distributions": program_shift_distributions(F), "behaviour_contrasts": behaviour_contrasts(),
           "opening_lines": opening_lines()}
    p = RESULTS_DIR / "natural_frlp.json"
    if p.exists():
        res["natural_proposal_frlp"] = json.loads(p.read_text())
    res["dependency_context"] = dependency_context(read_jsonl(DATA_DIR / "samples.jsonl"))
    write_json(RESULTS_DIR / "supplementary.json", res)
    return res


if __name__ == "__main__":
    r = main()
    for t, e in r["program_shift_distributions"].items():
        print(t, {k: (round(v["median"], 2), round(v["share_negative"], 2)) for k, v in e.items()})
    print(json.dumps(r["behaviour_contrasts"]))
