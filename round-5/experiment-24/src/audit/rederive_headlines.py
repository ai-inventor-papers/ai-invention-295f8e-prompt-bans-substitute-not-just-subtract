#!/usr/bin/env python3
"""Second, independent re-derivation of every HEADLINE number quoted in README.md and the artifact summary.

It reads only RAW files: data/labels.jsonl (one label row per program; raw generations in data/*_raw.jsonl), the
committed selections (predictions/commit1.json, commit2.json), inputs/exp22/escape.json, inputs/exp17/data/labels.jsonl
and the cached prefill states. It uses its own code path: pure-Python counting, exact binomial tails from math.comb,
a hand-written rank correlation, numpy state norms. It imports nothing from src/ and does not read results/*.json.
Every recomputed value is compared with the number quoted in README.md (CLAIMED below).

Placebos (each must FAIL to reproduce an effect): McNemar on arm labels shuffled within slots (T14, T03); the
Claim-A rank correlation on permuted escape fractions; a self-comparison T vs T.
Writes results/rederive_headlines.json.
"""

from __future__ import annotations

import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "inputs" / "exp11" / "bench"
PATH_CAT = {"T1": ["bfs", "dfs", "bibfs", "iddfs", "astar_gbfs", "dijkstra"],
            "T2": ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"]}
CLAIMED = {
    "n_div": 5, "claim_b_n_pass": 1, "claim_b_iii_fail": 4,
    "T14_T_heap/correct": (21, 49), "T14_twin_heap/correct": (0, 39), "T14_T_pass": 0.98, "T14_twin_pass": 0.78,
    "T14_MR_heap": 2, "T14_XT_heap": 5, "T14_MRP_heap": 0,
    "T14_N100_pairs": {"MR1.0": (44, 0), "XT1.0": (35, 3), "MRP0.5": (49, 0)},
    "T03_T_y/50": 3, "T03_MR_y/50": 21, "T03_T_vs_MR_pairs": (2, 20), "T03_T_vs_MR_p_two": 1.2e-4,
    "T10_S1_T0.5_y/50": 6, "T10_S1_T0.5_p_vs_twin": 0.016, "T10_S2_T0.5_y/50": 4,
    "T10_N100_vs_XT": (7, 0), "T03_N100_vs_XT": (6, 0),
    "EARLY_T03_y/50": 15, "EARLY_T10_y/50": 14, "READ_pass_le_0.53_tasks": 13,
    "ISO2_T03_off/30": 8, "DS_any_escape": False,
    "reverse_correct_BTWIN_to_RT": {"T03": (20, 31), "T2": (15, 20), "T1": (5, 11), "T10": (18, 19)},
    "reverse_T1_pairs": (9, 2), "claimA_spearman_a1": 0.78, "claimA_kendall_a1": 0.69, "r_t_eq_push_top1": 5,
    "engine_agree": {"T03|EC_RAND9002_a1.0": 0.74, "T2|EC_RAND9004_a1.0": 0.88, "T03|EC_NEUTRAL": 1.0,
                     "T2|EC_NEUTRAL": 0.98},
    "n_noncatalogue_correct_unique": 48, "share_cells_gt4_lambda1": 0.71,
}


def cat(t: str) -> list[str]:
    if t in PATH_CAT:
        return PATH_CAT[t]
    d = next(x for x in BENCH.iterdir() if x.is_dir() and x.name.startswith(t + "_"))
    return [c["mode"] for c in json.loads((d / "spec.json").read_text())["catalogue"]]


def ok_row(r: dict) -> bool:
    return bool(r.get("passed")) and r.get("label") not in (None, "invalid")


def binom_tail_ge(k: int, n: int) -> float:
    """P(X >= k), X ~ Bin(n, 1/2), exact via math.comb."""
    if n == 0:
        return 1.0
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n


def mcnemar(a: list[int], b: list[int]) -> tuple[int, int, float, float]:
    b_ = sum(1 for x, y in zip(a, b) if x and not y)
    c_ = sum(1 for x, y in zip(a, b) if y and not x)
    n = b_ + c_
    one = binom_tail_ge(b_, n)
    two = min(1.0, 2 * min(binom_tail_ge(b_, n), binom_tail_ge(c_, n))) if n else 1.0
    return b_, c_, one, two


def ranks(x: list[float]) -> list[float]:
    order = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and x[order[j + 1]] == x[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def pearson(a: list[float], b: list[float]) -> float:
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
    return num / den if den else float("nan")


def kendall_b(a: list[float], b: list[float]) -> float:
    conc = disc = ta = tb = 0
    for i in range(len(a)):
        for j in range(i + 1, len(a)):
            da, db = a[i] - a[j], b[i] - b[j]
            if da == 0 and db == 0:
                continue
            if da == 0:
                ta += 1
            elif db == 0:
                tb += 1
            elif da * db > 0:
                conc += 1
            else:
                disc += 1
    return (conc - disc) / math.sqrt((conc + disc + ta) * (conc + disc + tb))


def main() -> None:
    rows: dict[str, dict] = {}
    for line in (ROOT / "data" / "labels.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            rows.setdefault(r["sample_id"], r)
    c1 = json.loads((ROOT / "predictions" / "commit1.json").read_text())
    c2 = json.loads((ROOT / "predictions" / "commit2.json").read_text())
    by = defaultdict(dict)  # (task, arm) -> {(template, slot): row}
    for r in rows.values():
        by[(r["task"], r["arm"])][(r["template"], int(r["slot"]))] = r
    out: dict = {"checks": {}}

    def chk(name, got, claimed, tol=None):
        if tol is None:
            ok = got == claimed
        else:
            ok = abs(got - claimed) <= tol
        out["checks"][name] = {"recomputed": got, "claimed": claimed, "match": bool(ok)}

    def cell(task, arm, slots):
        return [v for (w, j), v in by[(task, arm)].items() if j in slots]

    tasks = list(c1["per_task"])
    # ---- base beta / strata recomputed from raw rows (twin default from S1 rows)
    defaults, betas, rt = {}, {}, {}
    for t in tasks:
        c = set(cat(t))
        tw = [r for r in cell(t, "TWIN", range(10)) if r.get("model") == "Qwen/Qwen3-8B"]
        cc = Counter(r["label"] for r in tw if ok_row(r))
        lab, k = cc.most_common(1)[0]
        d = lab if k / sum(cc.values()) >= 0.6 and lab in c else None
        defaults[t] = d
        base = list(by[(t, "BASE_CHAT")].values())
        corr = [r for r in base if ok_row(r)]
        pool = corr if len(corr) >= 20 else [r for r in base if r.get("label") not in (None, "invalid")]
        betas[t] = sum(1 for r in pool if r["label"] in c and r["label"] != d) / len(pool)
        nd = Counter(r["label"] for r in corr if r["label"] in c and r["label"] != d)
        att = Counter(r["label"] for r in base if r.get("label") in c)
        rt[t] = sorted(nd, key=lambda m: (-nd[m], -att[m], m))[0] if nd else None
    div = [t for t in tasks if betas[t] >= 0.2]
    chk("n_div", len(div), CLAIMED["n_div"])

    def y(r, t):
        return int(ok_row(r) and r["label"] in set(cat(t)) and r["label"] != defaults[t])

    # ---- Claim B frozen rule (N = 50, S2 slots 10-19)
    S2 = range(10, 20)
    fam, info = {}, {}
    for t in div:
        lam = c2["selection"][t]["lambda_star"]
        arms = [a for a, _ in c2["stage4_plan"][t]]
        T = by[(t, arms[0])]
        tw = {k: v for k, v in by[(t, "TWIN")].items() if k[1] in S2 and v.get("model") == "Qwen/Qwen3-8B"}
        Tr = {k: v for k, v in T.items() if k[1] in S2}
        p_T = sum(ok_row(v) for v in Tr.values()) / len(Tr)
        p_tw = sum(ok_row(v) for v in tw.values()) / len(tw)
        corrT = [v for v in Tr.values() if ok_row(v)]
        offT = sum(1 for v in corrT if v["label"] in set(cat(t)) and v["label"] != defaults[t]) / max(len(corrT), 1)
        nd = Counter(v["label"] for v in corrT if v["label"] in set(cat(t)) and v["label"] != defaults[t])
        modal = nd.most_common(1)[0][0] if nd else None
        for a in arms[1:]:
            C = {k: v for k, v in by[(t, a)].items() if k[1] in S2}
            ks = sorted(set(Tr) & set(C))
            b_, c_, one, _ = mcnemar([y(Tr[k], t) for k in ks], [y(C[k], t) for k in ks])
            ctl = "MRp" if a.startswith("MRP") else ("XT" if a.startswith("XT") else "MR")
            fam[(t, ctl)] = one
        info[t] = {"i": p_T >= 0.8 * p_tw, "ii": offT >= 0.5 * betas[t], "iv": modal == rt[t],
                   "broke": bool(c2["selection"][t]["MR_broken_at_lambda_star"])}
    keys = sorted(fam, key=fam.get)
    holm, run = {}, 0.0
    for i, k in enumerate(keys):
        run = max(run, min(1.0, (len(keys) - i) * fam[k]))
        holm[k] = run
    n_pass = n_iii_fail = 0
    for t in div:
        need = ["MR", "XT"] + (["MRp"] if info[t]["broke"] else [])
        iii = all(holm.get((t, c), 1.0) < 0.05 for c in need)
        n_iii_fail += int(not iii)
        n_pass += int(info[t]["i"] and info[t]["ii"] and iii and info[t]["iv"])
    chk("claim_b_n_pass", n_pass, CLAIMED["claim_b_n_pass"])
    chk("claim_b_iii_fail", n_iii_fail, CLAIMED["claim_b_iii_fail"])
    out["holm_T14_max"] = max(holm[("T14", c)] for c in ("MR", "XT", "MRp"))

    # ---- T14 counts
    def heap(task, arm, slots):
        rr = cell(task, arm, slots)
        if arm == "TWIN":
            rr = [r for r in rr if r.get("model") == "Qwen/Qwen3-8B"]
        corr = [r for r in rr if ok_row(r)]
        return sum(1 for r in corr if r["label"] == "heap"), len(corr), len(corr) / len(rr)
    h, n, p = heap("T14", "T1.0", S2)
    chk("T14_T_heap/correct", (h, n), CLAIMED["T14_T_heap/correct"])
    chk("T14_T_pass", round(p, 2), CLAIMED["T14_T_pass"])
    h, n, p = heap("T14", "TWIN", S2)
    chk("T14_twin_heap/correct", (h, n), CLAIMED["T14_twin_heap/correct"])
    chk("T14_twin_pass", round(p, 2), CLAIMED["T14_twin_pass"])
    chk("T14_MR_heap", heap("T14", "MR1.0", S2)[0], CLAIMED["T14_MR_heap"])
    chk("T14_XT_heap", heap("T14", "XT1.0", S2)[0], CLAIMED["T14_XT_heap"])
    chk("T14_MRP_heap", heap("T14", "MRP0.5", S2)[0], CLAIMED["T14_MRP_heap"])
    chk("T14_holm_max_le_7e-4", out["holm_T14_max"] <= 7e-4, True)
    S2x = range(10, 30)
    pairs = {}
    for a in ("MR1.0", "XT1.0", "MRP0.5"):
        Tr = {k: v for k, v in by[("T14", "T1.0")].items() if k[1] in S2x}
        C = {k: v for k, v in by[("T14", a)].items() if k[1] in S2x}
        ks = sorted(set(Tr) & set(C))
        b_, c_, _, _ = mcnemar([y(Tr[k], "T14") for k in ks], [y(C[k], "T14") for k in ks])
        pairs[a] = (b_, c_)
    chk("T14_N100_pairs", pairs, CLAIMED["T14_N100_pairs"])

    # ---- T03 / T10
    def ycount(task, arm, slots):
        rr = cell(task, arm, slots)
        if arm == "TWIN":
            rr = [r for r in rr if r.get("model") == "Qwen/Qwen3-8B"]
        return sum(y(r, task) for r in rr), len(rr)
    chk("T03_T_y/50", ycount("T03", "T1.0", S2)[0], CLAIMED["T03_T_y/50"])
    chk("T03_MR_y/50", ycount("T03", "MR1.0", S2)[0], CLAIMED["T03_MR_y/50"])
    Tr = {k: v for k, v in by[("T03", "T1.0")].items() if k[1] in S2}
    C = {k: v for k, v in by[("T03", "MR1.0")].items() if k[1] in S2}
    ks = sorted(set(Tr) & set(C))
    b_, c_, _, two = mcnemar([y(Tr[k], "T03") for k in ks], [y(C[k], "T03") for k in ks])
    chk("T03_T_vs_MR_pairs", (b_, c_), CLAIMED["T03_T_vs_MR_pairs"])
    chk("T03_T_vs_MR_p_two", round(two, 5), CLAIMED["T03_T_vs_MR_p_two"], tol=0.5e-5)
    S1 = range(10)
    chk("T10_S1_T0.5_y/50", ycount("T10", "T0.5", S1)[0], CLAIMED["T10_S1_T0.5_y/50"])
    Tr = {k: v for k, v in by[("T10", "T0.5")].items() if k[1] in S1}
    tw = {k: v for k, v in by[("T10", "TWIN")].items() if k[1] in S1 and v.get("model") == "Qwen/Qwen3-8B"}
    ks = sorted(set(Tr) & set(tw))
    chk("T10_S1_T0.5_p_vs_twin", round(mcnemar([y(Tr[k], "T10") for k in ks], [y(tw[k], "T10") for k in ks])[2], 3),
        CLAIMED["T10_S1_T0.5_p_vs_twin"])
    chk("T10_S2_T0.5_y/50", ycount("T10", "T0.5", S2)[0], CLAIMED["T10_S2_T0.5_y/50"])
    for t, a, key in (("T10", "XT0.5", "T10_N100_vs_XT"), ("T03", "XT1.0", "T03_N100_vs_XT")):
        Tarm = "T0.5" if t == "T10" else "T1.0"
        Tr = {k: v for k, v in by[(t, Tarm)].items() if k[1] in S2x}
        C = {k: v for k, v in by[(t, a)].items() if k[1] in S2x}
        ks = sorted(set(Tr) & set(C))
        chk(key, mcnemar([y(Tr[k], t) for k in ks], [y(C[k], t) for k in ks])[:2], CLAIMED[key])
    chk("EARLY_T03_y/50", ycount("T03", "EARLY1.0", S1)[0], CLAIMED["EARLY_T03_y/50"])
    chk("EARLY_T10_y/50", ycount("T10", "EARLY1.0", S1)[0], CLAIMED["EARLY_T10_y/50"])
    nread = 0
    for t in tasks:
        rr = cell(t, "READ1.0", range(6))
        nread += int(rr and sum(ok_row(r) for r in rr) <= 16)   # at most 16 of 30 correct (0.53)
    chk("READ_pass_le_0.53_tasks", nread, CLAIMED["READ_pass_le_0.53_tasks"])
    # ---- Claim D
    rr = cell("T03", "ISO2.0", range(10, 16))
    corr = [r for r in rr if ok_row(r)]
    chk("ISO2_T03_off/30", sum(1 for r in corr if r["label"] in set(cat("T03")) and r["label"] != defaults["T03"]),
        CLAIMED["ISO2_T03_off/30"])
    any_esc = False
    for t in c1["stage_sets"]["stage5_desharpen"]:
        tw = [r for r in cell(t, "TWIN", range(10, 16)) if r.get("model") == "Qwen/Qwen3-8B"]
        twc = [r for r in tw if ok_row(r)]
        tw_off = sum(1 for r in twc if r["label"] in set(cat(t)) and r["label"] != defaults[t]) / max(len(twc), 1)
        for a in (0.5, 1.0, 2.0):
            rr = cell(t, f"DS{a}", range(10, 16))
            cr = [r for r in rr if ok_row(r)]
            off = sum(1 for r in cr if r["label"] in set(cat(t)) and r["label"] != defaults[t]) / max(len(cr), 1)
            any_esc |= (off >= tw_off + 0.20 and len(cr) / len(rr) >= 0.8 * len(twc) / len(tw))
    chk("DS_any_escape", bool(any_esc), CLAIMED["DS_any_escape"])
    # ---- reverse
    rev = {}
    for t in ("T03", "T2", "T1", "T10"):
        rev[t] = (sum(ok_row(r) for r in by[(t, "BTWIN")].values()), sum(ok_row(r) for r in by[(t, "RT1.0")].values()))
    chk("reverse_correct_BTWIN_to_RT", rev, CLAIMED["reverse_correct_BTWIN_to_RT"])
    B, R = by[("T1", "BTWIN")], by[("T1", "RT1.0")]
    ks = sorted(set(B) & set(R))
    z = lambda r: int(ok_row(r) and r["label"] == defaults["T1"])  # noqa: E731
    chk("reverse_T1_pairs", mcnemar([z(R[k]) for k in ks], [z(B[k]) for k in ks])[:2], CLAIMED["reverse_T1_pairs"])
    # ---- Claim A (hand-written ranks)
    esc = json.loads((ROOT / "inputs" / "exp22" / "escape.json").read_text())
    ts = [t for t in tasks if t in esc]
    bv = [betas[t] for t in ts]
    ev = [esc[t]["E_t"]["1.0"]["E_t"] for t in ts]
    rho = pearson(ranks(bv), ranks(ev))
    chk("claimA_spearman_a1", round(rho, 2), CLAIMED["claimA_spearman_a1"])
    chk("claimA_kendall_a1", round(kendall_b(bv, ev), 2), CLAIMED["claimA_kendall_a1"])
    agree = 0
    for t in ts:
        push = esc[t].get("push_landing_v4") or {}
        if esc[t].get("movable") and push:
            agree += int(max(push, key=push.get) == rt[t])
    chk("r_t_eq_push_top1", agree, CLAIMED["r_t_eq_push_top1"])
    # ---- engine check vs the exp17 rows
    e17 = {}
    for line in (ROOT / "inputs" / "exp17" / "data" / "labels.jsonl").read_text().splitlines():
        r = json.loads(line)
        e17.setdefault((r["task"], r["arm"], r["template"], int(r["sample_id"])), r["label"])
    eng = {}
    for key in CLAIMED["engine_agree"]:
        t, arm = key.split("|")
        mine = by[(t, arm)]
        hits = [mine[k]["label"] == e17[(t, arm.replace("EC_", ""), k[0], k[1])] for k in mine
                if (t, arm.replace("EC_", ""), k[0], k[1]) in e17]
        eng[key] = round(sum(hits) / len(hits), 2)
    chk("engine_agree", eng, CLAIMED["engine_agree"])
    # ---- novelty pool size
    pool = {(r["task"], r.get("code_sha256")) for r in rows.values()
            if ok_row(r) and r.get("code") and r["label"] not in set(cat(r["task"]))}
    chk("n_noncatalogue_correct_unique", len(pool), CLAIMED["n_noncatalogue_correct_unique"])
    # ---- D size (spot check on all tasks, numpy path on the raw bf16 states)
    rq = {int(k): v["median"] for k, v in json.loads((ROOT / "inputs" / "exp23" / "qwen_ratio.json").read_text())
          ["r_Q"].items()}
    pr = {}
    for line in (ROOT / "predictions" / "prompts5.jsonl").read_text().splitlines():
        r = json.loads(line)
        if r["kind"] == "twin":
            pr[(r["task"], r["w"])] = r["spec_end"] - r["p1"]
    shares = []
    for t in tasks:
        for w in ("W1", "W2", "W3", "W4", "W5"):
            def ld(tag):
                a = np.load(ROOT / "cache" / "states" / f"{tag}_{t}_{w}.npy")
                return (a.astype(np.uint32) << 16).view(np.float32)   # bf16 bits -> float32, no torch
            hb, hi = ld("base"), ld("instr")
            nS = pr[(t, w)]
            vals = []
            for l in range(12, 24):
                dn = np.linalg.norm(hb[l, :nS] - hi[l, :nS], axis=-1)
                un = np.linalg.norm(hi[l, :nS], axis=-1) * rq[l]
                vals.append(float((dn / un > 4).mean()))
            shares.append(float(np.mean(vals)))
    chk("share_cells_gt4_lambda1", round(float(np.mean(shares)), 2), CLAIMED["share_cells_gt4_lambda1"])
    # ---- placebos
    rng = random.Random(20261021)
    plc = {}
    for t, a, Tarm in (("T14", "MR1.0", "T1.0"), ("T03", "MR1.0", "T1.0")):
        Tr = {k: v for k, v in by[(t, Tarm)].items() if k[1] in S2}
        C = {k: v for k, v in by[(t, a)].items() if k[1] in S2}
        ks = sorted(set(Tr) & set(C))
        ya, yb = [y(Tr[k], t) for k in ks], [y(C[k], t) for k in ks]
        rej = 0
        for _ in range(500):
            sw = [rng.random() < 0.5 for _ in ks]
            a2 = [yb[i] if s else ya[i] for i, s in enumerate(sw)]
            b2 = [ya[i] if s else yb[i] for i, s in enumerate(sw)]
            rej += mcnemar(a2, b2)[2] < 0.05
        plc[f"{t}_arm_shuffle_rejection"] = rej / 500
        plc[f"{t}_self_comparison_p"] = mcnemar(ya, ya)[2]
    nul = []
    for _ in range(2000):
        e2 = ev[:]
        rng.shuffle(e2)
        nul.append(pearson(ranks(bv), ranks(e2)))
    plc["claimA_perm_p_one_sided"] = (sum(1 for v in nul if v >= rho) + 1) / (len(nul) + 1)
    crit = sorted(nul)[int(0.95 * len(nul))]
    rej = 0
    for _ in range(500):
        e2 = ev[:]
        rng.shuffle(e2)
        rej += pearson(ranks(bv), ranks(e2)) > crit
    plc["claimA_shuffled_rejection_rate"] = rej / 500
    out["placebos"] = plc
    out["placebos_fail_as_required"] = bool(plc["T14_arm_shuffle_rejection"] <= 0.10
                                            and plc["T03_arm_shuffle_rejection"] <= 0.10
                                            and plc["T14_self_comparison_p"] == 1.0
                                            and plc["claimA_shuffled_rejection_rate"] <= 0.10)
    out["n_checks"] = len(out["checks"])
    out["n_mismatch"] = sum(1 for v in out["checks"].values() if not v["match"])
    (ROOT / "results" / "rederive_headlines.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"headline re-derivation: {out['n_checks']} checks, {out['n_mismatch']} mismatches; placebos {plc}")
    for k, v in out["checks"].items():
        if not v["match"]:
            print("MISMATCH", k, v)


if __name__ == "__main__":
    main()
