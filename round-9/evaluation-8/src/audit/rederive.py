#!/usr/bin/env python3
"""Independent re-derivation of the Step-0 numbers with the Python standard library only.

Shares no code with eval.py or src/: its own .npz/.npy reader (zipfile + header parsing + array), its own JSON key
navigation, its own ranks, Spearman, exact permutation enumeration, apply check and L1 lint. Run after eval.py:
    python -I audit/rederive.py
Writes audit/rederive_result.json {n_checks, n_mismatches, placebos_failed, checks[]}.
"""
import array
import ast
import hashlib
import itertools
import json
import math
import random
import re
import statistics
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEPS = Path(__import__("os").environ.get("S0_DEPS_DIR", ROOT.parents[2] / "round-8" / "."))
ARTS = {"art_vnyi0Fm5SyNH": "gen_art_experiment_39", "art_e-_q5mSJGrSb": "gen_art_experiment_40",
        "art_18XvfcJJZi1O": "gen_art_experiment_41", "art_FJMIE9T9_PMv": "gen_art_experiment_42",
        "art_lzuosbrb34wB": "gen_art_experiment_43", "art_R-HSmXq2t97f": "gen_art_experiment_44"}
CHECKS = []
_cache = {}


def apath(art, rel):
    for base in (DEPS, ROOT.parent):
        for name in (art, ARTS[art]):
            if (base / name).is_dir():
                return base / name / rel
    return DEPS / ARTS[art] / rel


def jload(art, rel):
    k = (art, rel)
    if k not in _cache:
        _cache[k] = json.loads(apath(art, rel).read_text())
    return _cache[k]


def check(name, expected, got, kind="independent", tol=1e-9):
    if isinstance(expected, str) or isinstance(got, str):
        ok = str(expected) == str(got)
    elif expected is None or got is None:
        ok = expected is got
    else:
        ok = abs(float(expected) - float(got)) <= tol * max(1.0, abs(float(expected)))
    CHECKS.append({"name": name, "expected": expected, "got": got, "ok": bool(ok), "kind": kind})
    return ok


# ------------------------------------------------------------------------------------------------ npz reader
def npy_member(zpath, member):
    with zipfile.ZipFile(zpath) as z:
        raw = z.read(member + ".npy")
    if raw[:6] != b"\x93NUMPY":
        raise ValueError("not an npy member")
    major = raw[6]
    if major == 1:
        hlen = int.from_bytes(raw[8:10], "little")
        off = 10
    else:
        hlen = int.from_bytes(raw[8:12], "little")
        off = 12
    header = ast.literal_eval(raw[off:off + hlen].decode("latin1"))
    data = raw[off + hlen:]
    descr, shape = header["descr"], header["shape"]
    n = 1
    for s in shape:
        n *= s
    if descr in ("<f8", "<i8"):
        arr = array.array("d" if descr == "<f8" else "q")
        arr.frombytes(data[: n * 8])
        if sys.byteorder != "little":
            arr.byteswap()
        out = list(arr)
    elif descr.startswith("<U"):
        w = int(descr[2:])
        out = [data[i * 4 * w:(i + 1) * 4 * w].decode("utf-32-le").rstrip("\x00") for i in range(n)]
    else:
        raise ValueError(f"unsupported dtype {descr}")
    return out, shape


# ------------------------------------------------------------------------------------------------ key navigation
def nav(obj, key):
    for part in re.findall(r"[^.\[\]]+|\[[^\]]*\]", key):
        if part.startswith("["):
            sel = part[1:-1]
            if "=" in sel:
                f, v = sel.split("=", 1)
                obj = [e for e in obj if str(e.get(f)) == v][0]
            else:
                obj = obj[int(sel)]
        else:
            obj = obj[part]
    return obj


def resolve_simple(src):
    art, rest = src.split(":", 1)
    rel, key = rest.split("#", 1)
    key = re.sub(r"\s*\(=.*\)$", "", key).strip()
    if art not in ARTS or not rel.endswith(".json") or re.search(r"[*{} ]|->|-n_heldout|- correct|1-twin", key):
        return None
    return nav(jload(art, rel), key)


# ------------------------------------------------------------------------------------------------ statistics
def ranks(x):
    order = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and x[order[j + 1]] == x[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return r


def spearman(x, y):
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    sy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return sxy / (sx * sy) if sx > 0 and sy > 0 else float("nan")


def arrangements(values):
    vals = sorted(set(values))
    counts = [values.count(v) for v in vals]
    n = len(values)

    def rec(free, k, cur):
        if k == len(vals):
            yield list(cur)
            return
        for pos in itertools.combinations(free, counts[k]):
            for p in pos:
                cur[p] = vals[k]
            yield from rec([f for f in free if f not in pos], k + 1, cur)

    yield from rec(list(range(n)), 0, [None] * n)


def exact_null(values):
    """rho of g-ranks 1..n against every distinct arrangement (rank vector of the arrangement precomputed per value)."""
    rv = ranks(values)
    rmap = {}
    for v, r in zip(values, rv):
        rmap[v] = r
    n = len(values)
    gr = [i + 1 - (n + 1) / 2 for i in range(n)]
    mean_r = sum(rv) / n
    sr = math.sqrt(sum((r - mean_r) ** 2 for r in rv))
    sg = math.sqrt(sum(g * g for g in gr))
    out = []
    for arr in arrangements(list(values)):
        out.append(sum((rmap[a] - mean_r) * g for a, g in zip(arr, gr)) / (sr * sg))
    return out


def p_lower(rho, null):
    return sum(1 for v in null if v <= rho + 1e-12) / len(null)


# ------------------------------------------------------------------------------------------------ main checks
def main():
    corr = json.loads((ROOT / "corrections.json").read_text())
    ledger = {v["name"]: v for v in corr["values"]}
    s0e = json.loads((ROOT / "results/s0e.json").read_text())

    # (1) generic ledger values with plain JSON key paths (every MATCH, NEW and CORRECTED value that has one)
    n_generic = 0
    for name, v in ledger.items():
        if v["source"].startswith("S0:"):
            continue
        try:
            got = resolve_simple(v["source"])
        except (KeyError, IndexError, ValueError):
            got = None
        if got is None:
            continue
        n_generic += 1
        check(f"ledger:{name}", v["recomputed"], got)

    # (2) composite ledger values, recomputed by hand
    circ = "art_18XvfcJJZi1O"
    S = jload(circ, "results/summary.json")
    V = S["validation"]
    check("ledger:0a.C1forced.n_pair", ledger["0a.C1forced.n_pair"]["recomputed"],
          V["C1forced"]["n_prompts"] - V["C1forced"]["n_heldout"])
    vrows = [json.loads(l) for l in apath(circ, "data/validation_rows_C1forced.jsonl").read_text().splitlines() if l]
    pair_t = {r["template"] for r in vrows if not r["heldout"]}
    held = [r for r in vrows if r["heldout"]]
    check("ledger:0a.cond_matches", ledger["0a.cond_matches"]["recomputed"],
          sum(1 for r in held if r["template"] in pair_t))
    zero = set()
    ident_ok = True
    for c in ("C1forced", "C2a", "C1nat"):
        nh = V[c]["n_heldout"]
        for mode in ("ablate", "steer"):
            for r in V[c]["per_node"][mode]:
                lhs = r["mean_d"] * r["n"]
                rhs = r["mean_d_pair_prompts"] * (r["n"] - nh) + r["mean_d_heldout"] * nh
                ident_ok &= abs(lhs - rhs) <= 1e-6 * max(1, abs(lhs))
                if r["mean_d_heldout"] == 0.0:
                    zero.add((c, r["node"]))
    check("0a.identity_all_nodes", True, ident_ok)
    check("ledger:0a.n_zero_nodes", ledger["0a.n_zero_nodes"]["recomputed"], len(zero))
    check("0a.zero_node_is_L0_COND", "C1forced|mlp|L0|H-1|COND", "|".join(sorted(zero)[0]) if len(zero) == 1 else "")
    l0 = [r for r in V["C1forced"]["per_node"]["ablate"] if r["node"] == "mlp|L0|H-1|COND"][0]
    check("0a.L0.worked_example", round(8.144148281097412 * 20 / 30, 6), round(l0["mean_d_pair_prompts"] * 20 / 30, 6))
    raw_zero = 0
    for r in held:
        for mode in ("ablate", "steer"):
            vals = [x for k, x in r["res"].items() if k.startswith(f"{mode}|mlp|L0|H-1|COND|")]
            raw_zero += int(len(vals) == 51 and all(x == 0.0 for x in vals))
    check("0a.raw_rows_unapplied_edit", 20, raw_zero)
    depths = []
    for c in ("C1nat", "C1forced", "C1mix", "C1natB"):
        q = S["motif"]["qwen"][c]
        for kk in ("dec_stack", "extended_top60_dec_stack"):
            if kk in q and q[kk] and q[kk].get("depth") is not None:
                depths.append(q[kk]["depth"])
    check("ledger:0a.motif.mst_depth_min", ledger["0a.motif.mst_depth_min"]["recomputed"], min(depths))
    check("ledger:0a.motif.mst_depth_max", ledger["0a.motif.mst_depth_max"]["recomputed"], max(depths))
    src_line = [l for l in apath(circ, "src/k3motif.py").read_text().splitlines() if l.startswith("BANDS =")][0]
    bands = ast.literal_eval(src_line.split("=", 1)[1].strip())
    check("ledger:0a.band.cond.lo", ledger["0a.band.cond.lo"]["recomputed"], bands["COND"][0])
    check("ledger:0a.band.cond.hi", ledger["0a.band.cond.hi"]["recomputed"], bands["COND"][1])
    check("ledger:0a.band.depth.lo", ledger["0a.band.depth.lo"]["recomputed"], bands["depth"][0])
    check("ledger:0a.band.depth.hi", ledger["0a.band.depth.hi"]["recomputed"], bands["depth"][1])
    das = jload("art_e-_q5mSJGrSb", "results/analysis.json")
    bfs = das["gen_T10_dec"]["classes"]["bfs"]["arms"]["DAS"]
    check("ledger:0b.bfs.fail", ledger["0b.bfs.fail"]["recomputed"], bfs["attempted_target"] - bfs["correct_target"])
    check("0b.mcnemar_exact_5_0", ledger["0b.bfs.mc_p"]["recomputed"], 2 * 0.5 ** 5)
    k1 = jload("art_vnyi0Fm5SyNH", "results/k1_verdict.json")["K1c"]
    dose = jload("art_vnyi0Fm5SyNH", "predictions/commit1_dose_table.json")["units"]
    med = {}
    with apath("art_vnyi0Fm5SyNH", "data/samples.jsonl").open() as f:
        for line in f:
            r = json.loads(line)
            if r.get("arm") == "A0" and r.get("stage") == "S0" and r.get("reached_decision") and \
                    r.get("decision_H1") is not None:
                med.setdefault(r["unit"], []).append(r["decision_H1"])
    tot = 0
    for u in ("G", "B3", "B6", "T10", "A3"):
        check(f"ledger:0c.{u}.above", ledger[f"0c.{u}.above"]["recomputed"], 1 - k1[u]["twin_dec_H_below_q90_frac"])
        check(f"ledger:0c.{u}.median_H", ledger[f"0c.{u}.median_H"]["recomputed"], statistics.median(med[u]))
        check(f"ledger:0c.{u}.q90_direct", ledger[f"0c.{u}.q90"]["recomputed"], dose[u]["q90"])
        tot += k1[u]["n"]
    check("ledger:0c.n_total", ledger["0c.n_total"]["recomputed"], tot)
    q = [dose[u]["q90"] for u in ("G", "B3", "B6", "T10", "A3")]
    check("ledger:0c.q90.min", ledger["0c.q90.min"]["recomputed"], min(q))
    check("ledger:0c.q90.max", ledger["0c.q90.max"]["recomputed"], max(q))
    mixed = [statistics.median(med[u]) for u in ("B3", "A3", "B6", "G")]
    check("ledger:0c.mixed_median.min", ledger["0c.mixed_median.min"]["recomputed"], min(mixed))
    check("ledger:0c.mixed_median.max", ledger["0c.mixed_median.max"]["recomputed"], max(mixed))
    law = jload("art_lzuosbrb34wB", "results/analysis_L.json")["verdict"]["per_unit"]
    check("ledger:0c.law.Hmax5", ledger["0c.law.Hmax5"]["recomputed"],
          max(law[u]["H"] for u in ("A3", "B6", "B3", "G-T04", "G-R6")))
    cells = jload("art_vnyi0Fm5SyNH", "results/k1_cells.json")
    check("0f.G.arms_missing", "A2,A4,A6", ",".join(a for a in ("A1", "A2", "A3g", "A4", "A5", "A6") if a not in cells["G"]))
    check("0f.A3.arms_missing", "A4,A6", ",".join(a for a in ("A1", "A2", "A3g", "A4", "A5", "A6") if a not in cells["A3"]))
    check("0f.B6.arms_missing", "A4,A6", ",".join(a for a in ("A1", "A2", "A3g", "A4", "A5", "A6") if a not in cells["B6"]))

    # (3) item 0e from the raw npz files
    tp = "art_R-HSmXq2t97f"
    gz = apath(tp, "cache/states/geo_C6_nf4.npz")
    sz = apath(tp, "cache/states/smean_C6_nf4.npz")
    labels, _ = npy_member(gz, "labels")
    if sz.exists():
        kind, _ = npy_member(sz, "kind")
        alg, _ = npy_member(sz, "algorithm")
        grp, _ = npy_member(sz, "group")
    else:   # published copy without the 181 MB states file: the vendored index of the same rows
        ix = json.loads((ROOT / "inputs/forced_index_C6_nf4.json").read_text())
        kind, alg, grp = ix["kind"], ix["algorithm"], ix["group"]
    F = [i for i, k in enumerate(kind) if k == "forced"]
    alg_f = [alg[i] for i in F]
    grp_f = [int(grp[i]) for i in F]
    check("0e.E1_labels_equal", True, alg_f == labels)
    common = (apath(tp, "src/common.py")).read_text()
    tree = ast.parse(common)
    lit = {}
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            tgt = node.targets[0] if isinstance(node, ast.Assign) else node.target
            if isinstance(tgt, ast.Name) and tgt.id in ("ALIAS_TABLE", "CANON_ORDER"):
                lit[tgt.id] = ast.literal_eval(node.value)
    canon = lit["CANON_ORDER"]
    expect = sorted((a, t, j) for a in canon for t in range(10) for j in range(3))
    check("0e.E2_multiset", True, sorted(zip(alg_f, [g // 3 for g in grp_f], [g % 3 for g in grp_f])) == expect)
    banned = ["bfs", "dfs", "iddfs", "astar", "gbfs"]
    nonb = ["bibfs", "dijkstra_unit", "idastar", "jps", "biastar"]
    m1 = jload(tp, "results/geometry_M1.json")["M1"]
    det = [r"\bbfs\b", r"breadth[-_ ]?first", r"\bdfs\b", r"depth[-_ ]?first", r"\biddfs\b", r"iterative[-_ ]?deepening",
           r"a\*|a[-_ ]?star|astar", r"greedy", r"best[-_ ]?first", r"manhattan", r"heuristic"]
    prim = [sum(1 for d in det if re.search(d, s, re.I)) for a in nonb for s in lit["ALIAS_TABLE"][a]]
    check("0e.primary_vector", "1,1,1,0,0,0,1,2,3,0,0,0,1,1,1", ",".join(map(str, prim)))
    null1 = exact_null([float(x) for x in prim])
    check("0e.null_size", 360360, len(null1))
    for k in (15, 10):
        geo, shape = npy_member(gz, f"geo_k{k}")
        N = shape[0]

        def mean_block(I, J):
            return sum(geo[i * N + j] for i in I for j in J) / (len(I) * len(J))

        bidx = {b: [i for i in range(N) if labels[i] == b] for b in banned}
        galg = {a: min(mean_block([i for i in range(N) if labels[i] == a], bidx[b]) for b in banned) for a in nonb}
        for a in nonb:
            check(f"0e.k{k}.g_alg.{a}", m1[f"k{k}"]["g"][a], galg[a], tol=1e-9)
        gal = []
        for a in nonb:
            for j in range(3):
                I = [i for i in range(N) if labels[i] == a and grp_f[i] % 3 == j]
                gal.append(min(mean_block(I, bidx[b]) for b in banned))
        for (a, j), gv in zip([(a, j) for a in nonb for j in range(3)], gal):
            check(f"0e.k{k}.g_alias.{a}|{j}", s0e["per_k"][f"k{k}"]["g_alias"][f"{a}|{j}"], gv)
        rho = spearman(gal, [float(x) for x in prim])
        check(f"ledger:0e.k{k}.rho_primary", ledger[f"0e.k{k}.rho_primary"]["recomputed"], rho)
        check(f"ledger:0e.k{k}.p_primary", ledger[f"0e.k{k}.p_primary"]["recomputed"], p_lower(rho, null1))
        xa = [sum(prim[3 * i:3 * i + 3]) / 3 for i in range(5)]
        ga = [galg[a] for a in nonb]
        r5 = spearman(ga, xa)
        perms = [spearman(ga, [xa[p] for p in perm]) for perm in itertools.permutations(range(5))]
        if k == 15:
            check("ledger:0e.k15.rho_5c", ledger["0e.k15.rho_5c"]["recomputed"], r5)
            check("ledger:0e.k15.p_5c", ledger["0e.k15.p_5c"]["recomputed"],
                  sum(1 for v in perms if v <= r5 + 1e-12) / 120)
            check("ledger:0e.k15.floor_5c", ledger["0e.k15.floor_5c"]["recomputed"],
                  sum(1 for v in perms if v <= min(perms) + 1e-12) / 120)
        # within-algorithm stratified test on content-token overlap
        stop = {"a", "an", "the", "with", "from", "both", "at", "once", "on", "run", "and", "of", "to", "s", "search",
                "algorithm"}
        tok = lambda s: {t for t in re.split(r"[^a-z0-9*]+", s.lower()) if t and t not in stop}  # noqa: E731
        bal = [tok(s) for b in banned for s in lit["ALIAS_TABLE"][b]]
        sec = [max(len(tok(s) & bt) / len(tok(s) | bt) for bt in bal) for a in nonb for s in lit["ALIAS_TABLE"][a]]
        G = [gal[3 * i:3 * i + 3] for i in range(5)]
        X = [sec[3 * i:3 * i + 3] for i in range(5)]

        def strat(Xs):
            vals = [spearman(G[i], Xs[i]) for i in range(5) if max(Xs[i]) - min(Xs[i]) > 1e-12]
            return sum(vals) / len(vals)

        def beta(Xs):
            num = den = 0.0
            for i in range(5):
                mg, mx = sum(G[i]) / 3, sum(Xs[i]) / 3
                num += sum((g - mg) * (x - mx) for g, x in zip(G[i], Xs[i]))
                den += sum((x - mx) ** 2 for x in Xs[i])
            return num / den

        so, bo = strat(X), beta(X)
        sts, bes = [], []
        for combo in itertools.product(list(itertools.permutations(range(3))), repeat=5):
            Xp = [[X[i][c] for c in combo[i]] for i in range(5)]
            sts.append(strat(Xp))
            bes.append(beta(Xp))
        ps = sum(1 for v in sts if v <= so + 1e-12) / len(sts)
        pb = sum(1 for v in bes if abs(v) >= abs(bo) - 1e-12) / len(bes)
        check(f"ledger:0e.k{k}.strat_p", ledger[f"0e.k{k}.strat_p"]["recomputed"], ps)
        if k == 15:
            check("ledger:0e.k15.strat", ledger["0e.k15.strat"]["recomputed"], so)
            check("ledger:0e.k15.beta", ledger["0e.k15.beta"]["recomputed"], bo)
            check("ledger:0e.k15.beta_p", ledger["0e.k15.beta_p"]["recomputed"], pb)
            check("ledger:0e.k15.rho_secondary", ledger["0e.k15.rho_secondary"]["recomputed"], spearman(gal, sec))
            g15, prim15 = gal, prim
    tert_p = ROOT / "results/s0e_tertiary.json"
    if tert_p.exists() and "0e.k15.bpe_strat" in ledger:
        T = json.loads(tert_p.read_text())
        x3 = [r["tertiary"] for r in T["rows"]]
        geo, shape = npy_member(gz, "geo_k15")
        N = shape[0]
        bidx = {b: [i for i in range(N) if labels[i] == b] for b in banned}
        gal = []
        for a in nonb:
            for j in range(3):
                I = [i for i in range(N) if labels[i] == a and grp_f[i] % 3 == j]
                gal.append(min(sum(geo[i * N + jj] for i in I for jj in bidx[b]) / (len(I) * len(bidx[b])) for b in banned))
        G3 = [gal[3 * i:3 * i + 3] for i in range(5)]
        X3 = [x3[3 * i:3 * i + 3] for i in range(5)]

        def strat3(Xs):
            vals = [spearman(G3[i], Xs[i]) for i in range(5) if max(Xs[i]) - min(Xs[i]) > 1e-12]
            return sum(vals) / len(vals)

        so3 = strat3(X3)
        null3 = [strat3([[X3[i][c] for c in combo[i]] for i in range(5)])
                 for combo in itertools.product(list(itertools.permutations(range(3))), repeat=5)]
        check("ledger:0e.k15.bpe_strat", ledger["0e.k15.bpe_strat"]["recomputed"], so3)
        check("ledger:0e.k15.bpe_strat_p", ledger["0e.k15.bpe_strat_p"]["recomputed"],
              sum(1 for v in null3 if v <= so3 + 1e-12) / len(null3))
        check("ledger:0e.k15.bpe_rho", ledger["0e.k15.bpe_rho"]["recomputed"], spearman(gal, x3))
    # consistency-only checks for randomised 0e quantities (bootstrap, placebos, E4 need numpy-scale work)
    stored = {"0e.k15.ci_lo": s0e["per_k"]["k15"]["ci95_primary"][0], "0e.k15.ci_hi": s0e["per_k"]["k15"]["ci95_primary"][1],
              "0e.P1": s0e["placebos"]["P1_shuffled_alias_labels"]["share_p_lt_0.05"],
              "0e.P2": s0e["placebos"]["P2_random_overlap_vector"]["share_p_lt_0.05"],
              "0e.C1.rho": s0e["placebos"]["C1_planted"]["seed0_rho"], "0e.C1.p": s0e["placebos"]["C1_planted"]["seed0_p_lower"],
              "0e.E4": s0e["gates"].get("E4_spearman_vs_stored_k15")}
    for nm, val in stored.items():
        if nm not in ledger:
            continue
        check(f"ledger:{nm}", ledger[nm]["recomputed"], val, kind="consistency")

    # (4) the apply test, independently
    orig = (ROOT / "inputs/report/current_report.md").read_text()
    edits = corr["edits"]
    spans = []
    for e in edits:
        spans.append((orig.index(e["old_text"]), e))
        check(f"apply.unique.{e['id']}", 1, orig.count(e["old_text"]))
    spans.sort(key=lambda t: t[0])
    out, last = [], 0
    for s, e in spans:
        assert s >= last, f"overlap at {e['id']}"
        out.append(orig[last:s])
        out.append(e["new_text"])
        last = s + len(e["old_text"])
    out.append(orig[last:])
    rebuilt = "".join(out)
    check("apply.rebuilt_equals_report_corrected", hashlib.sha256((ROOT / "report_corrected.md").read_bytes()).hexdigest(),
          hashlib.sha256(rebuilt.encode()).hexdigest())

    # (5) placebos that must FAIL
    plac = {}
    rnd = random.Random(20261023)
    geo, shape = npy_member(gz, "geo_k15")
    N = shape[0]
    pts = list(zip(labels, [g % 3 for g in grp_f]))
    rej = 0
    rhos = []
    for _ in range(200):
        sh = pts[:]
        rnd.shuffle(sh)
        bidx = {b: [i for i in range(N) if sh[i][0] == b] for b in banned}
        gal = []
        for a in nonb:
            for j in range(3):
                I = [i for i in range(N) if sh[i] == (a, j)]
                gal.append(min(sum(geo[i * N + jj] for i in I for jj in bidx[b]) / (len(I) * len(bidx[b]))
                               for b in banned))
        r = spearman(gal, [float(x) for x in prim15])
        rhos.append(r)
        rej += p_lower(r, null1) < 0.05
    plac["P1_shuffled_alias_labels"] = {"reject_share": rej / 200, "mean_rho": sum(rhos) / 200,
                                        "failed_as_required": rej / 200 <= 0.10}
    wrong = [r for r in V["C1forced"]["per_node"]["ablate"] if r["node"] == "head|L33|H14|DEC"][0]["mean_d_heldout"]
    plac["P2_wrong_node"] = {"ledger": ledger["0a.L0.abl.heldout"]["recomputed"], "wrong_node_value": wrong,
                             "failed_as_required": abs(wrong - ledger["0a.L0.abl.heldout"]["recomputed"]) > 1e-6}
    dup = orig + "\n" + edits[0]["old_text"]
    plac["P3_duplicated_old_text"] = {"count": dup.count(edits[0]["old_text"]),
                                      "failed_as_required": dup.count(edits[0]["old_text"]) != 1}
    corrected = (ROOT / "report_corrected.md").read_text()
    start = corrected.index("# Iteration 8: temperature at the fork")

    def l1_hits(text):
        n = 0
        body = text[start:]
        for m in re.finditer(r"same shape", body):
            w = body[max(0, m.start() - 300): m.end() + 300]
            n += ("circuit" in w or "Gemma" in w)
        return n

    clean = l1_hits(corrected)
    inj = corrected.replace("## 8.11 What the next iteration", "The circuit has the same shape as Gemma's circuit.\n\n## 8.11 "
                            "What the next iteration", 1)
    plac["P4_injected_same_shape"] = {"hits_clean": clean, "hits_injected": l1_hits(inj),
                                      "failed_as_required": clean == 0 and l1_hits(inj) >= 1}
    n_fail = sum(1 for p in plac.values() if p["failed_as_required"])
    res = {"n_checks": len(CHECKS), "n_mismatches": sum(1 for c in CHECKS if not c["ok"]),
           "n_independent": sum(1 for c in CHECKS if c["kind"] == "independent"),
           "n_consistency": sum(1 for c in CHECKS if c["kind"] == "consistency"),
           "n_ledger_generic": n_generic, "n_match_values_checked": sum(
               1 for c in CHECKS if c["name"].startswith("ledger:") and ledger.get(c["name"][7:], {}).get("status") == "MATCH"),
           "placebos_failed": n_fail, "placebos_total": len(plac), "placebos": plac,
           "mismatches": [c for c in CHECKS if not c["ok"]], "checks": CHECKS}
    (ROOT / "audit/rederive_result.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: res[k] for k in ("n_checks", "n_mismatches", "n_independent", "n_consistency",
                                          "n_match_values_checked", "placebos_failed", "placebos_total")}))
    print(json.dumps(res["mismatches"][:10], default=str))
    return 0 if res["n_mismatches"] == 0 and n_fail == len(plac) else 1


if __name__ == "__main__":
    sys.exit(main())
