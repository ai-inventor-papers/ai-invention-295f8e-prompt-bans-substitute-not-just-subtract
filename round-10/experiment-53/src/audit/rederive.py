"""Independent re-derivation of the NOV-T headline numbers (standard library only; a separate code path).

Reads the raw rows (data/calls.jsonl), the exported decision vectors (results/decisions_export.json: ast_hash ->
hex string, one byte per probe decision, ERR = 255) and the raw per-instance held-out gaps
(results/heldout_raw.json). Re-derives: the arm-seed best programs, the complete-linkage cluster counts (its own
nearest-neighbour-chain implementation on integer mismatch counts), rates, pooled and per-seed ratios, G200 means and
the V1-T / V2-T verdicts; then runs the four placebos, which must fail.
Usage: python audit/rederive.py   (writes results/rederive.json)
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
N_DEC = 2000
CORE = ["T1.0", "T1.6", "DTB", "RPB"]
SEEDS = [0, 1]


def mismatches(a: int, b: int) -> int:
    """Number of differing decisions between two byte-packed vectors."""
    return N_DEC - (a ^ b).to_bytes(N_DEC, "big").count(0)


def complete_linkage_count(hexes: list[str], max_diff: int) -> int:
    """Flat clusters of complete linkage cut at <= max_diff mismatches (NN-chain, scipy's loop order)."""
    n = len(hexes)
    if n <= 1:
        return n
    vals = [int(h, 16) for h in hexes]
    D = [[0] * n for _ in range(n)]
    for i in range(n):
        vi = vals[i]
        row = D[i]
        for j in range(i + 1, n):
            d = mismatches(vi, vals[j])
            row[j] = d
            D[j][i] = d
    size = [1] * n
    chain: list[int] = []
    merges_within = 0
    for _ in range(n - 1):
        if not chain:
            chain = [next(i for i in range(n) if size[i] > 0)]
        while True:
            x = chain[-1]
            if len(chain) > 1:
                y = chain[-2]
                cur = D[x][y]
            else:
                y, cur = -1, float("inf")
            Dx = D[x]
            for i in range(n):
                if size[i] == 0 or i == x:
                    continue
                if Dx[i] < cur:
                    cur = Dx[i]
                    y = i
            if len(chain) > 1 and y == chain[-2]:
                break
            chain.append(y)
        chain = chain[:-2]
        if x > y:
            x, y = y, x
        if cur <= max_diff:
            merges_within += 1
        size[y] = size[x] + size[y]
        size[x] = 0
        for i in range(n):
            if size[i] == 0 or i == y:
                continue
            nd = max(D[i][x], D[i][y])
            D[i][y] = nd
            D[y][i] = nd
    return n - merges_within


def read_jsonl(p: Path) -> list[dict]:
    out = []
    with open(p) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return out


def mean(x):
    x = list(x)
    return sum(x) / len(x) if x else None


def verdicts(c: dict, N: dict, g200: dict, g_nn: float) -> dict:
    bar = 0.8 * g_nn
    keys = [(a, s) for a in CORE for s in SEEDS]
    have = [k for k in keys if g200.get(k) is not None]
    if len(have) == len(keys) and all(g200[k] <= bar for k in keys):
        v1 = "SUPPORTED"
    elif not any(g200[k] < g_nn for k in have):
        v1 = "DISCONFIRMED"
    else:
        v1 = "PARTIAL"

    def rate(a, seeds=SEEDS):
        n = sum(N.get((a, s), 0) for s in seeds)
        return sum(c.get((a, s), 0) for s in seeds) / n if n else 0.0

    R = {x: (rate("DTB") / rate(x) if rate(x) > 0 else float("inf")) for x in ("T1.0", "T1.6", "RPB")}
    r = {}
    for x in ("T1.0", "T1.6", "RPB"):
        for s in SEEDS:
            rx = rate(x, [s])
            r[f"{x}|{s}"] = rate("DTB", [s]) / rx if rx > 0 else float("inf")
    gd = mean(g200[("DTB", s)] for s in SEEDS) if all(g200.get(("DTB", s)) is not None for s in SEEDS) else None
    gt = [mean(g200[(x, s)] for s in SEEDS) if all(g200.get((x, s)) is not None for s in SEEDS) else None
          for x in ("T1.0", "T1.6")]
    held = gd is not None and None not in gt and gd <= min(gt)
    ok = (R["T1.0"] >= 1.5 and R["T1.6"] >= 1.5 and all(r[f"{x}|{s}"] > 1 for x in ("T1.0", "T1.6") for s in SEEDS)
          and R["RPB"] >= 1.2 and held)
    if ok:
        v2 = "SUPPORTED"
    elif R["T1.0"] <= 1.0 or R["T1.6"] <= 1.0:
        v2 = "DISCONFIRMED"
    else:
        v2 = "PARTIAL"
    return {"V1": v1, "V2": v2, "R": R, "r": r, "mean_G200": {"DTB": gd, "T1.0": gt[0], "T1.6": gt[1]}}


def main() -> None:
    calls = read_jsonl(ROOT / "data" / "calls.jsonl")
    dec = json.loads((ROOT / "results" / "decisions_export.json").read_text())
    held = json.loads((ROOT / "results" / "heldout_raw.json").read_text())
    clusters_reported = json.loads((ROOT / "results" / "clusters.json").read_text())
    max_diff = int(round(0.05 * N_DEC))
    out: dict = {"utc_note": "stdlib re-derivation", "per_arm_seed": {}, "mismatch_vs_reported": []}
    c, N, hex_by = {}, {}, {}
    seen = {}
    for row in calls:
        seen[(row["arm"], row["seed"], row["call_idx"])] = row
    rows = list(seen.values())
    # matched rounds: last round in which every arm (core + IDEA) of a seed has all 32 calls (re-implemented)
    last = {}
    for s in SEEDS:
        per = []
        for a in CORE + ["IDEA"]:
            cnt = {}
            for r in rows:
                if r["arm"] == a and r["seed"] == s:
                    cnt[r["round"]] = cnt.get(r["round"], 0) + 1
            k = -1
            while cnt.get(k + 1, 0) == 32:
                k += 1
            per.append(k)
        last[s] = min(per)
    rows = [r for r in rows if r["arm"] == "NOSEL" or r["round"] <= last[r["seed"]]]
    out["matched_rounds"] = last
    for a in CORE + ["IDEA"]:
        for s in SEEDS:
            rs = [r for r in rows if r["arm"] == a and r["seed"] == s]
            if not rs:
                continue
            pv = [r for r in rs if r.get("probe_valid") and r.get("ast_hash") in dec]
            hexes = sorted({dec[r["ast_hash"]] for r in pv})
            k = complete_linkage_count(hexes, max_diff)
            c[(a, s)], N[(a, s)], hex_by[(a, s)] = k, len(rs), hexes
            best = min((r for r in rs if r.get("probe_valid") and r.get("F") is not None),
                       key=lambda r: (r["F"], r["call_idx"]), default=None)
            rep = clusters_reported.get("per_arm_seed", {}).get(f"{a}|{s}", {})
            n_valid = sum(1 for r in rs if r.get("label") == "valid")
            out["per_arm_seed"][f"{a}|{s}"] = {"calls": len(rs), "probe_valid": len(pv), "unique": len(hexes),
                                               "clusters": k, "rate_per_1000": 1000 * k / len(rs),
                                               "reported_clusters": rep.get("primary_clusters"),
                                               "validity": n_valid / len(rs),
                                               "best_call": best["call_idx"] if best else None,
                                               "best_F": best["F"] if best else None}
            if rep.get("primary_clusters") is not None and rep["primary_clusters"] != k:
                out["mismatch_vs_reported"].append({"arm_seed": f"{a}|{s}", "rederived": k,
                                                    "reported": rep["primary_clusters"]})
    g200 = {}
    for key, v in held.get("arm_best", {}).items():
        a, s = key.split("|")
        if not s.isdigit():  # e.g. 'T1.0|0_first252' (the NOSEL matched-N comparator), not an arm-seed best
            continue
        g = v.get("heldout_gaps")
        g200[(a, int(s))] = mean(g) if g else None
    g_nn = mean(held["NN"]["heldout_gaps"])
    out["G200_NN"] = g_nn
    out["G200"] = {f"{a}|{s}": g for (a, s), g in g200.items()}
    out["verdicts"] = verdicts(c, N, g200, g_nn)
    # ---------------- placebos (must fail)
    rnd = random.Random(12345)
    plc: dict = {}
    # (1) arm labels shuffled within a seed: pool the rows of the core arms of each seed and re-deal them
    c_sh, N_sh = {}, {}
    for s in SEEDS:
        pool = [r for r in rows if r["seed"] == s and r["arm"] in CORE]
        rnd.shuffle(pool)
        sizes = [N[(a, s)] for a in CORE]
        k0 = 0
        for a, n_a in zip(CORE, sizes):
            part = pool[k0:k0 + n_a]
            k0 += n_a
            hexes = sorted({dec[r["ast_hash"]] for r in part if r.get("probe_valid") and r.get("ast_hash") in dec})
            c_sh[(a, s)], N_sh[(a, s)] = complete_linkage_count(hexes, max_diff), n_a
    v_sh = verdicts(c_sh, N_sh, g200, g_nn)
    plc["shuffled_arm_labels"] = {"V2": v_sh["V2"], "R": v_sh["R"], "must": "V2 not SUPPORTED, ratios near 1",
                                  "passes": v_sh["V2"] != "SUPPORTED"}
    # (2) DTB and T1.0 labels swapped
    c_sw = dict(c)
    g_sw = dict(g200)
    for s in SEEDS:
        c_sw[("DTB", s)], c_sw[("T1.0", s)] = c[("T1.0", s)], c[("DTB", s)]
        g_sw[("DTB", s)], g_sw[("T1.0", s)] = g200.get(("T1.0", s)), g200.get(("DTB", s))
    N_sw = dict(N)
    for s in SEEDS:
        N_sw[("DTB", s)], N_sw[("T1.0", s)] = N[("T1.0", s)], N[("DTB", s)]
    v_sw = verdicts(c_sw, N_sw, g_sw, g_nn)
    real_supported = out["verdicts"]["V2"] == "SUPPORTED"
    plc["dtb_t10_swapped"] = {"V2": v_sw["V2"], "R": v_sw["R"], "must": "V2 not SUPPORTED",
                              "passes": v_sw["V2"] != "SUPPORTED" or not real_supported}
    # (3) thresholds: 0 mismatches -> one cluster per unique vector; 2000 -> one cluster per arm
    t0 = {f"{a}|{s}": complete_linkage_count(hex_by[(a, s)], 0) == len(hex_by[(a, s)]) for (a, s) in hex_by}
    t1 = {f"{a}|{s}": complete_linkage_count(hex_by[(a, s)], N_DEC) == min(1, len(hex_by[(a, s)]))
          for (a, s) in list(hex_by)[:4]}
    c_one = {k: min(1, len(v)) for k, v in hex_by.items()}
    v_one = verdicts(c_one, N, g200, g_nn)
    plc["threshold_0_equals_unique"] = {"ok": all(t0.values()), "passes": all(t0.values())}
    plc["threshold_all_one_cluster_per_arm"] = {"ok": all(t1.values()), "V2": v_one["V2"], "R": v_one["R"],
                                                "passes": all(t1.values()) and v_one["V2"] != "SUPPORTED"}
    # (4) NN's G200 replaced by the best arm's -> V1 not SUPPORTED
    g_best = min(g for g in g200.values() if g is not None)
    v_nn = verdicts(c, N, g200, g_best)
    plc["nn_replaced_by_best_arm"] = {"V1": v_nn["V1"], "must": "V1 not SUPPORTED",
                                      "passes": v_nn["V1"] != "SUPPORTED"}
    out["placebos"] = plc
    out["all_placebos_fail_as_required"] = all(v["passes"] for v in plc.values())
    out["clusters_match_reported"] = not out["mismatch_vs_reported"]
    (ROOT / "results" / "rederive.json").write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps({"verdicts": out["verdicts"], "placebos_ok": out["all_placebos_fail_as_required"],
                      "clusters_match": out["clusters_match_reported"],
                      "mismatches": out["mismatch_vs_reported"]}, indent=1, default=str))


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    main()
