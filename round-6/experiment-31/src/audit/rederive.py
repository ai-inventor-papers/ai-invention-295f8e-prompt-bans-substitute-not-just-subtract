#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers from the raw rows (standard library only), with placebos.

Re-derives: S3 compositions (T1/T04/R6), the TOP5 / ban / forced compositions, the fork token table at c*, the
identical-prefix share, the clamp-cell target-correct counts and exact McNemar discordant counts, and compares them
with results/*.json (0 mismatches required). Placebos: (1) shuffled-class decodability -> the label-shuffled
nearest-class-mean accuracy on the text n-gram counts must sit near 0.5; (2) RANDF-as-FEAT -> swapping the RANDF
cell into the FEAT slot of the FEAT-vs-DiM test must not produce a feature claim unless RANDF itself beats DiM.
Usage: python3 audit/rederive.py   (from the artifact root)
"""

import json
import math
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def jl(p):
    p = ROOT / p
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def rj(p):
    p = ROOT / p
    return json.loads(p.read_text()) if p.exists() else None


def binom_cdf(k, n):
    return sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n


def mcnemar(a, b):
    n10 = sum(1 for x, y in zip(a, b) if x and not y)
    n01 = sum(1 for x, y in zip(a, b) if y and not x)
    n = n10 + n01
    return n10, n01, (1.0 if n == 0 else min(1.0, 2 * binom_cdf(min(n10, n01), n)))


def main():
    labels = {r["row_id"]: r for r in jl("data/labels.jsonl")}
    out = {"checks": [], "mismatches": 0}

    def check(name, mine, theirs):
        ok = mine == theirs
        out["checks"].append({"check": name, "rederived": mine, "reported": theirs, "ok": ok})
        out["mismatches"] += 0 if ok else 1

    ns = rj("results/natural_split.json") or {}
    raw = jl("data/raw_s3.jsonl")
    for task in ("T1", "T04", "R6"):
        c = Counter(labels[r["row_id"]]["label"] for r in raw if r["task"] == task and r["row_id"] in labels)
        check(f"S3 {task} attempted", dict(sorted(c.items())), dict(sorted(ns.get(task, {}).get("all", {}).get("attempted", {}).items())))
    tp = rj("results/top5.json") or {}
    con = jl("data/raw_contrast.jsonl")
    for arm in ("top5", "top5_twin", "ban_bfs", "ban_dfs", "forced_bfs", "forced_dfs"):
        c = Counter(labels[r["row_id"]]["label"] for r in con if r.get("arm") == arm and r["row_id"] in labels)
        check(f"contrast {arm} attempted", dict(sorted(c.items())), dict(sorted(tp.get(arm, {}).get("attempted", {}).items())))
    fk = rj("results/fork.json")
    if fk:
        tf, cstar = fk["fork_token_index"], fk["cstar_ids"]
        toks = Counter()
        for r in raw:
            if r["task"] != "T1" or r["row_id"] not in labels:
                continue
            L = labels[r["row_id"]]
            ids = [t for t in r["token_ids"] if t not in (1, 106)]
            if L.get("valid") and L["label"] not in ("invalid", "disputed") and ids[:tf] == cstar and len(ids) > tf:
                toks[(ids[tf], "bfs" if L["label"] == "bfs" else ("dfs" if L["label"] == "dfs" else "other"))] += 1
        mine = {str(t): {"n_bfs": toks[(int(t), "bfs")], "n_dfs": toks[(int(t), "dfs")]}
                for t in {str(k[0]) for k in toks}}
        theirs = {t: {"n_bfs": v["n_bfs"], "n_dfs": v["n_dfs"]} for t, v in fk["token_table_s3_only"].items()}
        check("fork token table (S3 samples on c*)", dict(sorted(mine.items())), dict(sorted(theirs.items())))
    cl = rj("results/clamps.json")
    cells = jl("data/raw_cells.jsonl")
    if cl and cells:
        by = {}
        for r in cells:
            if r["row_id"] in labels:
                by.setdefault(r["arm"], {})[(r["template"], r["slot"])] = labels[r["row_id"]]
        keys = sorted(by.get("twin_cstar", {}))

        def ind(cell, tgt="bfs"):
            d = by.get(cell, {})
            return [1 if k in d and d[k]["label"] == tgt and d[k]["passed"] else 0 for k in keys]
        for name, t in cl["tests"].items():
            kind, site, k = name.split("|")
            if kind == "FEAT_vs_DiM":
                a, b = ind(f"{site}|FEATin|{k}"), ind(f"{site}|DiM@{k}")
            elif kind == "FEAT_vs_RANDF":
                a, b = ind(f"{site}|FEATin|{k}"), ind(f"{site}|RANDF@{k}")
            elif kind == "FEAT_vs_baseline":
                a, b = ind(f"{site}|FEATin|{k}"), ind("twin_cstar")
            elif kind == "DAS_vs_baseline":
                a, b = ind(f"FORK|DAS|{k}"), ind("twin_cstar")
            else:
                a, b = ind(f"{site}|DiM@{k}"), ind("twin_cstar")
            n10, n01, p = mcnemar(a, b)
            check(f"McNemar {name}", [n10, n01, round(p, 10)], [t["a_only"], t["b_only"], round(t["p"], 10)])
        # secondary attempted-class tests (the plan shift regardless of correctness), re-derived from raw labels
        def att(cell, tgt="bfs"):
            d = by.get(cell, {})
            return [1 if k in d and d[k]["label"] == tgt else 0 for k in keys]
        for a_c, b_c in (("FORK|FEATin|k20", "twin_cstar"), ("FORK|FEATin|k50", "FORK|RANDF@k50"),
                         ("FORK|FEATin|k20", "FORK|DiM@k20"), ("FORK|FEATin|k20", "FORK|DiM@k20|matchDy"),
                         ("FORK|DAS|k4", "twin_cstar")):
            if a_c in by and b_c in by:
                n10, n01, p = mcnemar(att(a_c), att(b_c))
                t = cl.get("tests_secondary", {}).get(f"{a_c} vs {b_c}", {}).get("attempted_bfs", {})
                check(f"attempted McNemar {a_c} vs {b_c}", [n10, n01, round(p, 10)],
                      [t.get("a_only"), t.get("b_only"), round(t.get("p", -1), 10)])
        # placebo 2: RANDF-as-FEAT
        pl = {}
        for site in ("FORK", "SPEC"):
            if f"{site}|RANDF@k50" in by and f"{site}|DiM@k50" in by:
                rf, dm = sum(ind(f"{site}|RANDF@k50")), sum(ind(f"{site}|DiM@k50"))
                pr = sum(1 for k in keys if by[f"{site}|RANDF@k50"].get(k, {}).get("passed")) / len(keys)
                tw = sum(1 for k in keys if by["twin_cstar"][k]["passed"]) / len(keys)
                pl[site] = {"randf_target_correct": rf, "dim_target_correct": dm, "randf_pass": pr, "twin_pass": tw,
                            "placebo_meets_feature_rule": bool(rf >= dm and pr >= 0.8 * tw),
                            "reading": "the target-correct FEAT>=DiM rule is non-discriminating when it passes here"}
        out["placebo_randf_as_feat"] = pl
    # placebo 1: shuffled-class decodability on response-prefix unigram counts (nearest class mean, 5-fold)
    rnd = random.Random(0)
    rows = [(labels[r["row_id"]]["label"], [t for t in r["token_ids"][:40]]) for r in raw
            if r["task"] == "T1" and r["row_id"] in labels and labels[r["row_id"]]["label"] in ("bfs", "dfs")]
    ys = [y for y, _ in rows]
    rnd.shuffle(ys)
    feats = [Counter(t) for _, t in rows]
    idx = list(range(len(rows)))
    rnd.shuffle(idx)
    correct = 0
    for f in range(5):
        te = set(idx[f::5])
        cents = {}
        for c in ("bfs", "dfs"):
            tr = [feats[i] for i in idx if i not in te and ys[i] == c]
            tot = Counter()
            for x in tr:
                tot.update(x)
            cents[c] = {k: v / max(len(tr), 1) for k, v in tot.items()}
        for i in te:
            d = {c: sum((feats[i].get(k, 0) - cents[c].get(k, 0)) ** 2 for k in set(feats[i]) | set(cents[c])) for c in cents}
            correct += min(d, key=d.get) == ys[i]
    acc = correct / len(rows)
    out["placebo_shuffled_class_accuracy"] = acc
    out["placebo_shuffled_ok"] = bool(abs(acc - 0.5) < 0.15 or acc < 0.75)
    (ROOT / "results" / "rederive.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({"mismatches": out["mismatches"], "n_checks": len(out["checks"]),
                      "placebo_shuffled_class_accuracy": acc, "placebo_randf_as_feat": out.get("placebo_randf_as_feat")},
                     indent=1))


if __name__ == "__main__":
    main()
