#!/usr/bin/env python3
"""Independent stdlib re-derivation of every NEW and CORRECTED value of corrections.json from raw rows (iteration-8
record repair). Imports nothing from eval.py or sections/; uses only the Python standard library.

Placebos that must FAIL (a placebo 'fails' when the quantity it perturbs no longer reproduces the corrected value):
 (i)   the OLD labels must reproduce the old kth values (0/30 and 1.59) and must NOT reproduce the corrected ones;
 (ii)  slot-shuffled DAS counts change the paired slot-bootstrap interval of the recovery (the pooled point value is a
       ratio of sums and is invariant to slot order, which is checked separately), and label-shuffled rows change it;
 (iii) permuted margins give a Spearman near 0;
 (iv)  the residual-claim lint run on the uncorrected report flags every phrase;
 (v)   the apply test on a mutated old_text fails.
Writes audit/rederive_report.json."""

import csv
import json
import math
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import os

# ONE constant for the inputs of other artifacts (same rule as sections/common.py): the run layout if present, else the
# repository layout where each artifact is a sibling folder; override with AII_DEP_ROOT. Folders by name, else by id.
_RUN_LAYOUT = ROOT.parents[2] / "round-7" / "."
DEP_ROOT = Path(os.environ.get("AII_DEP_ROOT") or (_RUN_LAYOUT if _RUN_LAYOUT.exists() else ROOT.parent))
IDS = {33: "art_veI9l_Rb9wDY", 34: "art_pHL7LWNhpcCS", 35: "art_MZAfDPVhM6Ui", 36: "art_8O5eaNc5gxJs", 37: "art_VhaHGe7SxV95",
       38: "art_HY7uYZz-OjRW"}


def _dep(i):
    by_name = DEP_ROOT / f"gen_art_experiment_{i}"
    return by_name if by_name.exists() or not (DEP_ROOT / IDS[i]).exists() else DEP_ROOT / IDS[i]


E33, E34, E35, E36, E37, E38 = (_dep(i) for i in (33, 34, 35, 36, 37, 38))
N = 30

CHECKS = []
PLACEBOS = []


def check(name, mine, theirs, tol=1e-6):
    if isinstance(mine, (int, float)) and isinstance(theirs, (int, float)) and not isinstance(mine, bool):
        ok = abs(float(mine) - float(theirs)) <= tol
    else:
        ok = mine == theirs
    CHECKS.append({"name": name, "audit": mine, "recorded": theirs, "tol": tol, "ok": bool(ok)})
    return ok


def placebo(name, failed, detail=""):
    PLACEBOS.append({"name": name, "placebo_failed_as_required": bool(failed), "detail": detail})


def jl(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def jr(p):
    return json.loads(Path(p).read_text())


# ------------------------------------------------------------------------------------------------ stdlib statistics
def betacf(a, b, x):
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 / ((1.0 + aa * d) if abs(1.0 + aa * d) > 1e-300 else 1e-300)
        c = (1.0 + aa / c) if abs(1.0 + aa / c) > 1e-300 else 1e-300
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 / ((1.0 + aa * d) if abs(1.0 + aa * d) > 1e-300 else 1e-300)
        c = (1.0 + aa / c) if abs(1.0 + aa / c) > 1e-300 else 1e-300
        de = d * c
        h *= de
        if abs(de - 1.0) < 3e-16:
            break
    return h


def ibeta(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x))
    return bt * betacf(a, b, x) / a if x < (a + 1) / (a + b + 2) else 1 - bt * betacf(b, a, 1 - x) / b


def bppf(q, a, b):
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if ibeta(a, b, mid) < q else (lo, mid)
    return (lo + hi) / 2


def cp(k, n):
    return [0.0 if k == 0 else bppf(0.025, k, n - k + 1), 1.0 if k == n else bppf(0.975, k + 1, n - k)]


def wilson(k, n, z=1.959963984540054):
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [max(0.0, c - h), min(1.0, c + h)]


def ranks(x):
    o = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and x[o[j + 1]] == x[o[i]]:
            j += 1
        for t in range(i, j + 1):
            r[o[t]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = ranks(a), ranks(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    return num / math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))


def fisher(a, b, c, d):
    r1, r2, c1 = a + b, c + d, a + c
    n = r1 + r2
    pmf = lambda x: math.comb(r1, x) * math.comb(r2, c1 - x) / math.comb(n, c1)
    p0 = pmf(a)
    return min(1.0, sum(pmf(x) for x in range(max(0, c1 - r2), min(r1, c1) + 1) if pmf(x) <= p0 * (1 + 1e-7)))


# ------------------------------------------------------------------------------------------------ kth smallest P1
def arms(rows, task, override=None):
    A = defaultdict(dict)
    for r in rows:
        if r["task"] == task:
            lab = override.get(r["sample_id"], r["label"]) if override else r["label"]
            A[r["arm"]][int(r["slot_index"])] = (bool(r.get("passed")), lab)
    return A


def vec(A, arm, Y):
    if arm not in A:
        return None
    return [int(bool(A[arm].get(s)) and A[arm][s][0] and A[arm][s][1] in Y) for s in range(N)]


def t03_sources():
    return [("ban", ["quickselect", "size_k_heap"], "BASE_W5", "FULL_ban_L16", {1: "DASLY_ban_k1", 4: "DASLY_ban_k4", 16: "DASLY_ban_k16"}),
            ("F_quickselect", ["quickselect"], "BASE_PAD", "FULL_F_quickselect", {k: f"DASLY_F_quickselect_k{k}" for k in (1, 4, 16)}),
            ("F_counting_sort", ["counting_sort"], "BASE_PAD", "FULL_F_counting_sort", {k: f"DASLY_F_counting_sort_k{k}" for k in (1, 4, 16)})]


def pooled(A, k, idx=None):
    idx = list(range(N)) if idx is None else idx
    num = den = 0.0
    for _, Y, base, full, das in t03_sources():
        b, f, v = vec(A, base, Y), vec(A, full, Y), vec(A, das.get(k), Y) if das.get(k) else None
        if b is None or f is None or v is None:
            continue
        num += sum(v[i] for i in idx) - sum(b[i] for i in idx)
        den += sum(f[i] for i in idx) - sum(b[i] for i in idx)
    return (num / den if den > 0 else None), num, den


def boot(A, k, seed=20261023, reps=2000):
    rng = random.Random(seed)
    vals = []
    for _ in range(reps):
        idx = [rng.randrange(N) for _ in range(N)]
        r = pooled(A, k, idx)[0]
        if r is not None:
            vals.append(r)
    vals.sort()
    return [vals[int(0.025 * len(vals))], vals[min(len(vals) - 1, int(0.975 * len(vals)))]]


def main():
    corr = jr(ROOT / "corrections.json")
    V = {v["name"]: v for v in corr["values"]}
    rows = jl(E33 / "data" / "labels.jsonl")
    adj = list(csv.DictReader((ROOT / "tables" / "counting_sort_adjudication.csv").open()))
    # final T03 labels: the adjudicated column for the adjudicated cells; every other T03 row keeps its label (the
    # relabel's 35 transitions all fall inside the adjudicated cells, checked here from results/a3_relabel.json)
    rel = jr(ROOT / "results" / "a3_relabel.json")
    adj_ids = {r["sample_id"] for r in adj}
    trans = [o for o in rel["rows"] if o["old_label"] != o["rule_v2"]]
    check("all relabel transitions fall inside the adjudicated cells", all(o["sample_id"] in adj_ids for o in trans), True)
    check("relabel transitions are all other->counting_sort", all(o["old_label"] == "other" and o["rule_v2"] == "counting_sort" for o in trans), True)
    final = {r["sample_id"]: r["final_label"] for r in adj if r["task"] == "T03"}
    A_old, A_new = arms(rows, "T03"), arms(rows, "T03", final)
    full_new = sum(vec(A_new, "FULL_F_counting_sort", ["counting_sort"]))
    full_old = sum(vec(A_old, "FULL_F_counting_sort", ["counting_sort"]))
    check(V["T03 forced counting sort: full state correct counting sort (of 30)"]["name"], full_new, V["T03 forced counting sort: full state correct counting sort (of 30)"]["recomputed"], 0)
    check("T03 F_counting_sort full-state count", full_new, V["T03 F_counting_sort full-state count"]["recomputed"], 0)
    p_old, p_new = {}, {}
    for k in (1, 4, 16):
        p_old[k], p_new[k] = pooled(A_old, k)[0], pooled(A_new, k)[0]
        check(f"T03 pooled recovery k{k}", p_new[k], V[f"T03 pooled recovery k{k}"]["recomputed"], 1e-9)
        check(f"T03 pooled recovery k{k} (old labels, placebo)", p_old[k], V[f"T03 pooled recovery k{k} (old labels, placebo)"]["recomputed"], 1e-9)
        ci = boot(A_new, k)
        note = V[f"T03 pooled recovery k{k}"]["note"]
        lo, hi = map(float, re.search(r"\[([\d.]+), ([\d.]+)\]", note).groups())
        check(f"T03 pooled recovery k{k}: stdlib slot bootstrap interval within 0.03 of the numpy one", abs(ci[0] - lo) <= 0.03 and abs(ci[1] - hi) <= 0.03, True)
    # placebo (i): old labels reproduce 0/30 and 1.59, and do not reproduce the corrected values
    placebo("(i) old labels give 0/30 and 1.59, not the corrected 29 and 1.01",
            full_old == 0 and round(p_old[1], 2) == 1.59 and full_old != full_new and abs(p_old[1] - p_new[1]) > 0.3,
            f"old full {full_old}, old k1 {p_old[1]:.3f}; new full {full_new}, new k1 {p_new[1]:.4f}")
    # placebo (ii): slot shuffle leaves the ratio of sums unchanged but breaks the paired bootstrap; label shuffle changes the point
    rng = random.Random(5)
    A_sh = {a: dict(v) for a, v in A_new.items()}
    for a in [x for x in A_sh if x.startswith("DASLY_")]:
        keys = list(A_sh[a].keys())
        vals = [A_sh[a][s] for s in keys]
        rng.shuffle(vals)
        A_sh[a] = dict(zip(keys, vals))
    p_sh = pooled(A_sh, 1)[0]
    check("slot shuffle leaves the pooled ratio of sums unchanged (k1)", p_sh, p_new[1], 1e-12)
    ci_new, ci_sh = boot(A_new, 1), boot(A_sh, 1)
    placebo("(ii-a) slot-shuffled DAS counts change the paired slot-bootstrap interval", ci_new != ci_sh, f"{ci_new} vs {ci_sh}")
    labs = [final.get(r["sample_id"], r["label"]) for r in rows if r["task"] == "T03"]
    random.Random(9).shuffle(labs)
    ov = {r["sample_id"]: l for r, l in zip([r for r in rows if r["task"] == "T03"], labs)}
    p_ls = pooled(arms(rows, "T03", ov), 1)[0]
    placebo("(ii-b) label-shuffled rows change the pooled recovery", p_ls is None or abs(p_ls - p_new[1]) > 0.05, f"{p_ls}")
    # routing and novelty
    cyf = [r for r in adj if r["cell"] == "FULL_F_counting_sort" and r["passed"] == "True"]
    offd = [r for r in cyf if r["final_label"] != "full_sort"]
    ny = sum(r["final_label"] == "counting_sort" for r in offd)
    check("Table 300 kth smallest | counting sort: full state routing", ny / len(offd), V["Table 300 kth smallest | counting sort: full state routing"]["recomputed"], 1e-9)
    lo, hi = cp(ny, len(offd))
    note = V["Table 300 kth smallest | counting sort: full state routing"]["note"]
    check("Table 300 CP interval (stdlib)", [round(lo, 2), round(hi, 2)], [float(x) for x in re.search(r"CP ([\d.]+), ([\d.]+)", note).groups()])
    na = jr(E33 / "results" / "novelty_audit.json")["rows"]
    c_full = sum(r["arm"] == "FULL_F_counting_sort" for r in na)
    c_forced = sum(r["arm"] in ("F1_counting_sort", "F2_counting_sort", "F3_counting_sort") for r in na)
    check("7.3.9 catalogue variants from FULL_F_counting_sort (of 36)", c_full, V["7.3.9 catalogue variants from FULL_F_counting_sort (of 36)"]["recomputed"], 0)
    check("7.3.9 catalogue variants from the forced counting sort prompts F1-F3 (of 36)", c_forced, V["7.3.9 catalogue variants from the forced counting sort prompts F1-F3 (of 36)"]["recomputed"], 0)
    # implementation form of the counting sorts (independent regex re-implementation)
    dict_rx = re.compile(r"=\s*\{\}|Counter\(|defaultdict\(int\)|dict\(\)")
    forms = defaultdict(Counter)
    for r in rows:
        if r["task"] == "T03" and r["arm"] in ("FULL_F_counting_sort", "DASLY_F_counting_sort_k1", "DASLY_F_counting_sort_k4", "DASLY_F_counting_sort_k16"):
            code = r.get("code") or ""
            f = "array" if re.search(r"\[0\]\s*\*", code) else ("dict_sorted_keys" if dict_rx.search(code) and "sorted(" in code else "dict_value_range" if dict_rx.search(code) else "neither")
            forms[r["arm"]][f] += 1
    for arm, d in forms.items():
        check(f"counting sort implementation form, {arm}", dict(sorted(d.items())), V[f"counting sort implementation form, {arm}"]["recomputed"])
    # the committed contrastive pilot on shortest path (Table 301 caption note)
    pil = [r for r in adj if r["task"] == "T2" and r["cell"].startswith("DAS_")]
    o_deg = sum(r["old_label"] == "other" and r["final_label"] == "other" for r in pil)
    o_dij = sum(r["old_label"] == "other" and r["final_label"] == "dijkstra" for r in pil)
    d_deg = sum(r["old_label"] == "dijkstra" and r["final_label"] == "other" for r in pil)
    n_oth, n_dij = sum(r["old_label"] == "other" for r in pil), sum(r["old_label"] == "dijkstra" for r in pil)
    check("Table 301 pilot: programs labelled other that are degenerate / attempted Dijkstra", f"{o_deg} / {o_dij} of {n_oth}",
          V["Table 301 pilot: programs labelled other that are degenerate / attempted Dijkstra"]["recomputed"])
    check("Table 301 pilot: programs labelled Dijkstra by the frozen path labeller that are degenerate text", f"{d_deg} of {n_dij}",
          V["Table 301 pilot: programs labelled Dijkstra by the frozen path labeller that are degenerate text"]["recomputed"])
    check("no relabelled pilot program passes", any(r["passed"] == "True" and r["old_label"] != r["final_label"] for r in pil), False)
    # judge gate and labeller controls, recounted from the stored files
    g = jr(ROOT / "audit" / "judge_gate.json")["gate"]
    for jn, nm in (("A", "judge gate A (deepseek-chat-v3.1), of 10"), ("B", "judge gate B (mistral-medium-3.1), of 10")):
        sc = sum(c["label"] == c["known"] for c in g[jn]["per_control"])
        check(nm, sc, V[nm]["recomputed"], 0)
    val = jr(ROOT / "results" / "a2_validation.json")
    check("labeller v2: controls passed (of 5)", sum(c["control_pass"] for c in val["controls"]), V["labeller v2: controls passed (of 5)"]["recomputed"], 0)
    # p1.json arithmetic: per-source counts and the untrained-network ratios
    ri, ly = jr(E33 / "results" / "randinit_T2.json"), jr(E33 / "results" / "randinit_ly_T2.json")
    check("untrained network: committed ratio (contrastive objective, against the diverged fit)",
          ri["random_net_heldout_das16_gain"] / ri["trained_heldout_das16_gain"], V["untrained network: committed ratio (contrastive objective, against the diverged fit)"]["recomputed"], 1e-9)
    check("untrained network: matched likelihood-gain ratio (ratio_lmeY)",
          ly["random_net_heldout_das16_lmeY_gain"] / ly["trained_heldout_das16_lmeY_gain"], V["untrained network: matched likelihood-gain ratio (ratio_lmeY)"]["recomputed"], 1e-9)
    p1 = jr(E33 / "results" / "p1.json")["tasks"]
    for t, arm, src in (("T2", "PERMLY_ban_k2", "ban"), ("T10", "PERMLY_ban_k16", "ban"), ("T03", "PERMLY_ban_k1", "ban")):
        ps = p1[t]["per_source"][src]
        A = arms(rows, t) if t != "T03" else A_new
        Y = ps["Y"]
        v = sum(vec(A, arm, Y))
        nm = f"{t} permuted-label transfer ({arm}), relative to the full-state effect"
        check(nm, (v - ps["base_count"]) / (ps["full_count"] - ps["base_count"]), V[nm]["recomputed"], 1e-9)
    # Gemma dial evidence
    g2 = (E38 / "src" / "g2.py").read_text().split("\n")
    check("g2.py:877 prefills the opening (cs) for the DAS, DiM and twin cells", "run.run_cell(ids, cs, rows_w, raw" in g2[876], True)
    check("g2.py:885 samples the forced-BFS ceiling with an empty prefix", 'run.run_cell(pfz["ids"], [], rows, raw, "G2:forced")' in g2[884], True)
    dose = jl(E38 / "data" / "raw_g2dose.jsonl")
    by = defaultdict(list)
    for r in dose:
        by[r["cell"]].append(r)
    same = sorted(map(tuple, (r["ukey"] for r in by["forced_bfs_F5"]))) == sorted(map(tuple, (r["ukey"] for r in by["twin"])))
    check("Gemma dial: forced-BFS cell shares the CRN slots of the twin and DAS cells", same, V["Gemma dial: forced-BFS cell shares the CRN slots of the twin and DAS cells"]["recomputed"])
    rd = (E38 / "README.md").read_text().split("\n")
    ceil = [l.strip() for l in rd if "ceiling" in l and "forced" in l.lower() and l.strip().startswith("| forced-BFS prompt F5")] + \
        [l.strip() for l in rd if "prompting ceiling" in l and l.strip().startswith("- **")]
    check("exp38 README: the sentences that describe the forced-BFS ceiling", ceil, V["exp38 README: the sentences that describe the forced-BFS ceiling"]["recomputed"])
    pre = {c: sorted({r.get("prefix_len") for r in by[c]}, key=str) for c in ("twin", "DAS|bfs|1.0", "forced_bfs_F5")}
    check("Gemma dial: prefix length of twin / DAS lambda 1 / forced-BFS cells", pre, V["Gemma dial: prefix length of twin / DAS lambda 1 / forced-BFS cells"]["recomputed"])
    # fork margin Spearman and placebo (iii)
    cells = jr(E34 / "results" / "f_analysis.json")["cells"]["T10"]
    m, y = [c["m"] for c in cells], [c["y"] for c in cells]
    check("fork margin vs escape share Spearman (T10, 40 directions)", spearman(m, y), V["fork margin vs escape share Spearman (T10, 40 directions)"]["recomputed"], 1e-9)
    check("48-token opening LLR vs escape share Spearman (T10)", spearman([c["llr48"] for c in cells], y), V["48-token opening LLR vs escape share Spearman (T10)"]["recomputed"], 1e-9)
    rng = random.Random(3)
    sims = []
    for _ in range(500):
        mm = m[:]
        rng.shuffle(mm)
        sims.append(spearman(mm, y))
    sims.sort()
    med = sims[len(sims) // 2]
    placebo("(iii) permuted margins give a Spearman near 0", abs(med) < 0.1, f"median {med:.3f} over 500 permutations")
    check("permuted-outcome placebo: median Spearman of margin vs shuffled outcomes", abs(V["permuted-outcome placebo: median Spearman of margin vs shuffled outcomes"]["recomputed"]) < 0.1, True)
    # natural variance comparisons
    gd = jr(E38 / "results" / "g2_decisions.json")
    b22 = gd["second_layer"]["22"]["natural_variance_k1"]
    check("Gemma natural variance share, block 22, rank 1", b22["share"], V["Gemma natural variance share, block 22, rank 1"]["recomputed"], 1e-12)
    check("block 22 rank 1 share lies above the random 95th percentile", b22["share"] > b22["random_p95"], True)
    below = [k for k in ("1", "2", "4", "8") if gd["natural_variance"][k]["share"] <= gd["natural_variance"][k]["random_p95"]]
    check("Gemma ranks below the random 95th percentile at block 17", below, ["1", "2", "4"])
    rho = gd["natural_variance"]["spearman_R1_coord_vs_yv"]["rho"]
    flag = gd["natural_variance"]["1"]["share"] <= gd["natural_variance"]["1"]["random_p95"] and abs(rho) < 0.2
    check("Gemma dormant_flag (g2.py:618 rule)", flag, V["Gemma dormant_flag (g2.py:618 rule)"]["recomputed"])
    # Table 346 rows
    e3 = jr(E36 / "results" / "e3_replicate.json")["T10_fresh_k10_19"]
    pc = e3["profiles"]["cells"]
    for key, nm in (("PTOP", "Table 346 fresh slots: PTOP top-quartile cells, share Y"), ("PREST", "Table 346 fresh slots: PREST rest of cells, share Y"),
                    ("PSHUF", "Table 346 fresh slots: PSHUF position-shuffled cells, share Y")):
        check(nm, pc[key]["Y"]["k"] / pc[key]["Y"]["n"], V[nm]["recomputed"], 1e-12)
    tr, ds = e3["profiles"]["PTOP_vs_PREST"], e3["profiles"]["D1_vs_PSHUF"]
    check("Table 346: McNemar top quartile vs rest (fresh slots)", f"{tr['n10']}:{tr['n01']}", V["Table 346: McNemar top quartile vs rest (fresh slots)"]["recomputed"])
    check("Table 346: McNemar full unit vs shuffled (fresh slots)", f"{ds['n10']}:{ds['n01']}", V["Table 346: McNemar full unit vs shuffled (fresh slots)"]["recomputed"])
    check("Table 346: fresh-slot seed effect RD_seed", e3["2x2|Y"]["RD_seed"], V["Table 346: fresh-slot seed effect RD_seed"]["recomputed"], 1e-12)
    sl = defaultdict(dict)
    for r in jl(E36 / "data" / "samples.jsonl"):
        if r["task"] == "T10" and r.get("stage") == "E3_fresh" and r["arm"] != "TWIN":
            sl[r["design"]][(r["template"], r["k"])] = int(r["Y"])
    sums = {d: sum(v.values()) for d, v in sl.items()}
    b10 = lambda a, b: sum(sl[a][k] == 1 and sl[b][k] == 0 for k in sl[a])
    ok346 = (sums["PTOP"], sums["PREST"], sums["PSHUF"], sums["D1"]) == (24, 9, 4, 21) and (b10("PTOP", "PREST"), b10("PREST", "PTOP")) == (15, 0) \
        and (b10("D1", "PSHUF"), b10("PSHUF", "D1")) == (17, 0) and abs(((sums["D1"] + sums["D3"]) - (sums["D2"] + sums["D4"])) / 100 - e3["2x2|Y"]["RD_seed"]) < 1e-9
    check("Table 346: slot-level recomputation (data/samples.jsonl, E3_fresh) reproduces the aggregates", ok346,
          V["Table 346: slot-level recomputation (data/samples.jsonl, E3_fresh) reproduces the aggregates"]["recomputed"])
    # search rates
    ar = jr(E37 / "results" / "arm_rates.json")["level_b"]["T03"]
    lvs = jr(E37 / "results" / "L_vs_S.json")
    for a in ("S", "L", "I0", "EAP", "NE", "BINT", "B0"):
        x = lvs["L"] if a == "L" else ar[a]
        check(f"search level b, T03, arm {a}: programs / calls", f"{x['X_b']}/{x['N']}", V[f"search level b, T03, arm {a}: programs / calls"]["recomputed"])
    check("search vs instruction-only rate ratio (level b, T03)", (ar["S"]["X_b"] / ar["S"]["N"]) / (ar["I0"]["X_b"] / ar["I0"]["N"]),
          V["search vs instruction-only rate ratio (level b, T03)"]["recomputed"], 1e-9)
    # scope: B3 Wilson, Fisher, semantic seed, training templates
    c10 = jr(E35 / "results" / "test2.json")["per_unit"]["B3"]["cells"]["T1.0_p1"]
    k10 = round(c10["a_min"] * c10["n"])
    w = wilson(k10, c10["n"])
    check("B3 T1.0 Wilson 95% for 20/50", [round(x, 6) for x in w], [round(x, 6) for x in V["B3 T1.0 Wilson 95% for 20/50"]["recomputed"]])
    check("B3 T1.0 prediction outside the Wilson interval", not (w[0] <= c10["pred_a_min"] <= w[1]), True)
    ph = jr(E35 / "results" / "posthoc.json")["B3"]["twin_vs_sweep_T1"]
    (tk, tn), (sk, sn) = ph["twin"], ph["sweep_T1.0_p1"]
    check("B3 stream-lean Fisher p (twin 20/100 vs sweep 20/50)", fisher(tk, tn - tk, sk, sn - sk), V["B3 stream-lean Fisher p (twin 20/100 vs sweep 20/50)"]["recomputed"], 1e-9)
    mm_ = jr(E33 / "results" / "m_manifold.json")
    sem = mm_["probes"]["T2|seed_sem|-|-"]
    check("semantic seed null percentile", sem["null_percentile"], V["semantic seed null percentile"]["recomputed"], 1e-9)
    check("semantic seed D below the null 95th percentile by less than 0.01", 0 < mm_["paraphrase_null"]["D_95"] - sem["D"] < 0.01, True)
    cfg7 = (E33 / "src" / "cfg7.py").read_text()
    check("manifold: training templates of the map", 'TRAIN_W = ("W1", "W2", "W3")' in cfg7 and 'HELD_W = "W5"' in cfg7, True)
    # deviations quoted verbatim in the corrected report
    rep_new = (ROOT / "report_corrected.md").read_text()
    for d in jr(E33 / "results" / "deviations.json"):
        if d["id"] in ("D-drop", "D-tfsets", "D-targets", "D-cap"):
            check(f"exp33 deviation {d['id']} appears verbatim in report_corrected.md", d["text"] in rep_new, True)
        if d["id"] in ("D-drop", "D-tfsets", "D-targets", "D-cap", "D-randinit", "D-C-k"):
            check(f"exp33 deviation {d['id']} quoted verbatim", d["text"][:80] + "...", V[f"exp33 deviation {d['id']} quoted verbatim"]["recomputed"])
    # retag
    rt = jr(E36 / "results" / "retag.json")
    check("retag: D_star", rt["D_star"], V["retag: D_star"]["recomputed"])
    check("retag: movable tasks at D*", [t for t, v in rt["movability_at_D_star"].items() if v["movable"]], V["retag: movable tasks at D*"]["recomputed"])
    # positioning statuses re-derived from the raw grep outputs with an independent rule: title text present
    pos = jr(ROOT / "positioning.json")
    hdr = re.compile(r"^(URL|Type|Pattern): |^No matches found|FutureWarning|warnings\.warn")
    for r in pos["rows"]:
        raw = "\n".join(l for f in r["raw"] if (ROOT / f).exists()
                        for l in (ROOT / f).read_text(errors="replace").split("\n") if not hdr.search(l))
        has_title = bool(r["title_quote"]) and r["title_quote"] in raw
        mine = "UNVERIFIED" if not has_title else ("VERIFIED" if (r["venue_quote"] and r["venue_quote"] in raw) or r["venue_quote"] is None and r["status"] == "VERIFIED" else "VERIFIED-ABSTRACT")
        check(f"positioning row {r['key']}: status", mine, V[f"positioning row {r['key']}: status"]["recomputed"])
    for w_ in next(r for r in pos["rows"] if r["key"] == "tale")["workshop_posters"]:
        raw = "\n".join(l for l in (ROOT / w_["raw"]).read_text(errors="replace").split("\n") if not hdr.search(l))
        mine = "VERIFIED" if ("A Tale of Two Temperatures" in raw and w_["workshop"] in raw) else "UNVERIFIED"
        check(f"ICML 2026 workshop poster ({w_['workshop']})", mine, V[f"ICML 2026 workshop poster ({w_['workshop']})"]["recomputed"])
    # file-name losses
    import difflib
    rx = re.compile(r"[A-Za-z0-9_./-]+\.(?:jsonl|json|py|md|npz)")
    old = (ROOT / "inputs" / "eval6" / "report_corrected.md").read_text().split("\n")
    cur = (ROOT / "inputs" / "report" / "current_report.md").read_text().split("\n")
    n_lost = 0
    for tg, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, cur, autojunk=False).get_opcodes():
        if tg == "replace":
            for a, b in zip(range(i1, i2), range(j1, j2)):
                n_lost += bool(set(rx.findall(old[a])) - set(rx.findall(cur[b])))
    check("file-name losses found by difflib (report_corrected.md -> current_report.md)", n_lost,
          V["file-name losses found by difflib (report_corrected.md -> current_report.md)"]["recomputed"], 0)
    restored = sum(1 for p in ("results/pn.json", "top5_push.json", "src/clamp.py", "results/geometry.json", "src/cfg.py") if p in rep_new)
    check("every lost file name is back in the corrected report", restored, 5, 0)
    # placebo (iv): the lint flags every phrase in the uncorrected report, none in the corrected one
    src = (ROOT / "sections" / "common.py").read_text()
    block = src[src.index("LINT_PHRASES = ["):src.index("]\n", src.index("LINT_PHRASES = ["))]
    phrases = [json.loads(m.group(0)) for m in re.finditer(r'"(?:[^"\\]|\\.)*"', block)]
    rep_old = "\n".join(cur)
    miss_before = [p for p in phrases if p not in rep_old]
    left_after = [p for p in phrases if p in rep_new]
    placebo("(iv) the lint flags every phrase in the uncorrected report", not miss_before, f"{len(phrases)} phrases; missing before: {miss_before}")
    check("lint after: no phrase survives in report_corrected.md", left_after, [])
    check("no undefined 'Step K' left", len(re.findall(r"\bStep K\b", rep_new)), 0, 0)
    # placebo (v): every old_text occurs once; a mutated one does not
    counts = [rep_old.count(e["old_text"]) for e in corr["corrections"]]
    check("apply test: every old_text occurs exactly once in the vendored report", all(c == 1 for c in counts), True)
    e0 = max(corr["corrections"], key=lambda e: len(e["old_text"]))
    o = e0["old_text"]
    mut = o[: len(o) // 2] + ("#" if o[len(o) // 2] != "#" else "@") + o[len(o) // 2 + 1:]
    placebo("(v) the apply test on a mutated old_text fails", rep_old.count(mut) != 1, f"mutated {e0['id']}: occurs {rep_old.count(mut)} times")
    # coverage: every NEW and CORRECTED value has an audit check
    names = {c["name"] for c in CHECKS}
    target = [v["name"] for v in corr["values"] if v["status"] in ("NEW", "CORRECTED")]
    unchecked = [n for n in target if n not in names]
    rep = {"n_checks": len(CHECKS), "n_mismatch": sum(not c["ok"] for c in CHECKS),
           "mismatches": [c for c in CHECKS if not c["ok"]], "n_placebos": len(PLACEBOS),
           "n_placebos_failed": sum(p["placebo_failed_as_required"] for p in PLACEBOS), "placebos": PLACEBOS,
           "n_new_or_corrected": len(target), "unchecked_new_or_corrected": unchecked, "checks": CHECKS}
    (ROOT / "audit" / "rederive_report.json").write_text(json.dumps(rep, indent=1, default=str))
    print(f"audit: {rep['n_checks']} checks, {rep['n_mismatch']} mismatches, {rep['n_placebos_failed']}/{rep['n_placebos']} placebos "
          f"failed as required, {len(unchecked)} NEW/CORRECTED values without a check")
    for c in rep["mismatches"]:
        print("MISMATCH", c["name"], c["audit"], c["recorded"])
    for p in PLACEBOS:
        print("PLACEBO", p["name"], p["placebo_failed_as_required"], p["detail"][:160])
    if unchecked:
        print("UNCHECKED", unchecked)
    return 0 if rep["n_mismatch"] == 0 and rep["n_placebos_failed"] == rep["n_placebos"] and not unchecked else 1


if __name__ == "__main__":
    sys.exit(main())
