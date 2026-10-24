#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers (stdlib only; a separate code path from src/). Reads raw rows
(data/gen_s*.jsonl, data/eval/eval_part_*.jsonl, data/decisions.bin + index, data/instances, results/heldout_best.json bins) and
recomputes: selection F of every best program, BF's held-out bins (pure-python best-fit packer), every held-out excess,
the complete-linkage invariant and cluster counts (labels from method_out.json; leader clustering as an independent
algorithm), all V2 ratios, the rename rates and every verdict. Placebos that must FAIL: (a) arm labels shuffled across
round blocks, (b) a random-priority program under V1, (c) a disguised c14 must AGREE >= 0.9 with c14, (d) DTB's j
re-derived from a shuffled entropy vector must disagree with the logged j; plus a sign-flip test for V5."""
import array
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
ERR = 65535
SEEDS = [2, 3]
CORE = ["T1.0", "T1.6", "DTB", "RPB"]
OUT = {}


def jsonl(p):
    with open(p) as f:
        return [json.loads(x) for x in f if x.strip()]


def insts(name):
    return json.loads((D / "instances" / f"{name}.json").read_text())


def excess(bins, ins):
    l1 = [math.ceil(sum(x["items"]) / x["capacity"]) for x in ins]
    mb, ml = sum(bins) / len(bins), sum(l1) / len(l1)
    return (mb - ml) / ml


def bf_pack(items, cap):
    """Pure-python best fit (FunSearch semantics: tightest fitting opened bin, else a new bin)."""
    rem = []
    for s in items:
        best, bi = None, -1
        for i, r in enumerate(rem):
            if r >= s and (best is None or r < best):
                best, bi = r, i
        if bi < 0:
            rem.append(cap - s)
        else:
            rem[bi] -= s
    return len(rem)


def random_pack(items, cap, rng):
    """Random priority in the pre-allocated harness: uniform over all valid bins (opened that fit + empty ones)."""
    rem, n = [], len(items)
    for s in items:
        fit = [i for i, r in enumerate(rem) if r >= s]
        n_empty = n - len(rem)
        k = rng.randrange(len(fit) + n_empty)
        if k < len(fit):
            rem[fit[k]] -= s
        else:
            rem.append(cap - s)
    return len(rem)


def load_dec():
    idx = {r["key"]: r["row"] for r in jsonl(D / "decisions_index.jsonl")}
    a = array.array("H")
    with open(D / "decisions.bin", "rb") as f:
        a.frombytes(f.read())
    n = len(a) // 2000
    return (lambda row: a[row * 2000:(row + 1) * 2000]), idx, n


def agree(u, v):
    return sum(1 for x, y in zip(u, v) if x == y and x != ERR) / 2000.0


def main():
    gate = json.loads((R / "harness_gate.json").read_text())
    bf_or, bf_w = gate["sel_bf"]["or_excess"], gate["sel_bf"]["w_excess"]
    sel_or, sel_w = insts("SEL-OR"), insts("SEL-W")

    def F(b25):
        return 0.5 * excess(b25[:20], sel_or) / bf_or + 0.5 * excess(b25[20:], sel_w) / bf_w

    ev = {}
    for e in (r for part in sorted((D / "eval").glob("eval_part_*.jsonl")) for r in jsonl(part)):
        ev[(e["seed"], e["arm"], e["call"])] = e
    gen = {}
    for S in SEEDS:
        for g in jsonl(D / f"gen_s{S}.jsonl"):
            gen[(g["seed"], g["arm"], g["call"])] = g
    # ---------- 1. selection F of every best program (from stored bins) + the best-program choice itself
    bp = json.loads((R / "best_programs.json").read_text())
    f_ok, best_ok = [], []
    for k, r in bp["seed_best"].items():
        S, arm = int(k.split("-")[0][1:]), k.split("-", 1)[1]
        e = ev[(S, arm, r["call"])]
        f_ok.append(abs(F(e["bins25"]) - r["F"]) < 1e-12)
        valid = [(F(x["bins25"]), len(gen[(S, arm, c)]["code"]), c) for (s, a, c), x in ev.items()
                 if s == S and a == arm and x["valid"] and c < 2000 + (0 if arm != "NS" else 0)]
        best_ok.append(min(valid)[2] == r["call"])
    OUT["1_best_program_F_rederived"] = {"n": len(f_ok), "all_match": all(f_ok), "best_choice_match": all(best_ok)}
    # ---------- 2. BF held-out bins (pure python) + 3. every held-out excess
    hb = json.loads((R / "heldout_best.json").read_text())
    bfh = json.loads((R / "heldout_bf.json").read_text())
    sets = list(hb["bf"].keys())
    bf_match, exc_bf = {}, {}
    for s in sets:
        ins = insts(s)
        b = [bf_pack(x["items"], x["capacity"]) for x in ins]
        bf_match[s] = b == bfh[s]["bins"]
        exc_bf[s] = excess(b, ins)
    OUT["2_bf_heldout_bins_pure_python"] = {"all_match": all(bf_match.values()), "per_set": bf_match,
                                           "excess_pct": {s: round(100 * v, 4) for s, v in exc_bf.items()}}
    ex_ok = []
    exc = {}
    for k, r in hb["seed_best"].items():
        for s, b in r["bins"].items():
            v = excess(b, insts(s))
            ex_ok.append(abs(v - r["excess"][s]) < 1e-12)
            exc.setdefault(k, {})[s] = v
    OUT["3_heldout_excess_rederived"] = {"n": len(ex_ok), "all_match": all(ex_ok)}
    # ---------- V1 verdict (re-derived)
    lim = {"H-FSW5k": 0.8 * exc_bf["H-FSW5k"], "H-OR3": 0.8 * exc_bf["H-OR3"]}
    art = {}
    for arm in CORE + ["IDEA", "NS"]:
        cands = [(bp["seed_best"][f"S{S}-{arm}"]["F"], len(bp["seed_best"][f"S{S}-{arm}"]["code"]), S)
                 for S in SEEDS if f"S{S}-{arm}" in bp["seed_best"]]
        if cands:
            art[arm] = exc[f"S{min(cands)[2]}-{arm}"]
    passes = {a: art[a]["H-FSW5k"] <= lim["H-FSW5k"] and art[a]["H-OR3"] <= lim["H-OR3"] for a in art}
    beats = {a: art[a]["H-FSW5k"] < exc_bf["H-FSW5k"] or art[a]["H-OR3"] < exc_bf["H-OR3"] for a in art}
    v1 = "SUPPORTED" if all(passes[a] for a in CORE) else ("DISCONFIRMED" if not any(beats[a] for a in CORE) else "PARTIAL")
    OUT["V1"] = {"verdict": v1, "passes": passes,
                 "excess_pct": {a: {s: round(100 * v, 4) for s, v in art[a].items() if s in lim} for a in art}}
    # ---------- 4. clusters: labels from method_out.json, invariant, counts, leader clustering
    mo = json.loads((ROOT / "method_out.json").read_text())
    prog = [d for d in mo["datasets"] if d["dataset"] == "novb2_search_programs"][0]["examples"]
    get, idx, _ = load_dec()
    calls = {S: min(max(c for (s, a, c) in ev if s == S and a == arm) + 1 for arm in CORE) for S in SEEDS}
    lab = {}
    for x in prog:
        i = json.loads(x["input"])
        if x["predict_cluster"]:
            lab[(i["seed"], i["arm"], i["call"])] = x["predict_cluster"]
    counts, inv_ok, leader = {}, True, {}
    for S in SEEDS:
        for arm in CORE + ["IDEA", "NS"]:
            keys = [k for k in lab if k[0] == S and k[1] == arm and (arm == "NS" or k[2] < calls[S])]
            groups = {}
            for k in keys:
                groups.setdefault(lab[k], set()).add(ev[k]["probe_row"])
            counts[f"S{S}-{arm}"] = len(groups)
            for g, rows in groups.items():
                rows = sorted(rows)
                if len(rows) > 1 and len(rows) <= 60:
                    vs = [get(r) for r in rows]
                    for a_ in range(len(vs)):
                        for b_ in range(a_ + 1, len(vs)):
                            if agree(vs[a_], vs[b_]) < 0.95 - 1e-9:
                                inv_ok = False
            uniq = []
            seen = set()
            for k in sorted(keys, key=lambda t: t[2]):
                r_ = ev[k]["probe_row"]
                if r_ not in seen:
                    seen.add(r_)
                    uniq.append(get(r_))
            leaders = []
            for v in uniq:
                if not any(agree(v, l) >= 0.95 for l in leaders):
                    leaders.append(v)
            leader[f"S{S}-{arm}"] = len(leaders)
    cl = json.loads((R / "analysis_clusters.json").read_text())["per_arm_seed"]
    OUT["4_clusters"] = {"counts_from_labels": counts,
                         "match_analysis": all(counts[k] == cl[k]["clusters"] for k in counts if k in cl),
                         "complete_linkage_invariant_checked_clusters_le60": inv_ok, "leader_clusters": leader,
                         "D_per_1000": {k: 1000 * v / (calls[int(k[1])] if not k.endswith("NS") else 1000)
                                        for k, v in counts.items()}}
    # ---------- V2 ratios + verdict (re-derived)
    def rate(arm):
        return sum(counts[f"S{S}-{arm}"] for S in SEEDS) / sum(calls[S] for S in SEEDS)
    Rx = {X: rate("DTB") / rate(X) if rate(X) else float("inf") for X in ["T1.0", "T1.6", "RPB", "IDEA"]}
    per_seed = {f"S{S}:DTB/{X}": (counts[f"S{S}-DTB"] / counts[f"S{S}-{X}"]) for S in SEEDS for X in ["T1.0", "T1.6", "RPB"]}
    m = {a: (art[a]["H-FSW5k"] / exc_bf["H-FSW5k"] + art[a]["H-OR3"] / exc_bf["H-OR3"]) / 2 for a in art}
    conds = {"R_T1.0>=1.5": Rx["T1.0"] >= 1.5, "R_T1.6>=1.5": Rx["T1.6"] >= 1.5,
             "per_seed>1": all(v > 1 for k, v in per_seed.items() if "RPB" not in k), "R_RPB>=1.2": Rx["RPB"] >= 1.2,
             "m_DTB<=min": m["DTB"] <= min(m["T1.0"], m["T1.6"])}
    v2 = "SUPPORTED" if all(conds.values()) else ("DISCONFIRMED" if Rx["T1.0"] <= 1 or Rx["T1.6"] <= 1 else "PARTIAL")
    OUT["V2"] = {"verdict": v2, "R": Rx, "per_seed": per_seed, "conditions": conds, "m": m}
    # ---------- V6 rename rates (re-derived)
    cor = json.loads((R / "corpus.json").read_text())["entries"]
    import struct
    with open(D / "corpus_decisions.npy", "rb") as f:
        raw = f.read()
    hl = struct.unpack("<H", raw[8:10])[0]
    body = raw[10 + hl:]
    cvec = array.array("H")
    cvec.frombytes(body)
    names = [e["name"] for e in cor]
    cget = lambda name: cvec[names.index(name) * 2000:(names.index(name) + 1) * 2000]
    pvec = {"seed-BF": cget("BF"), "seed-FF": cget("FF")}
    for (S, arm, c), e in ev.items():
        if e["valid"] and e.get("probe_row") is not None:
            pvec[f"S{S}-{arm}-c{c}"] = e["probe_row"]
    ren = {}
    for arm in ["T1.0", "IDEA"]:
        n = k_ = 0
        for S in SEEDS:
            for c in range(calls[S]):
                e = ev.get((S, arm, c))
                if not e or not e["valid"] or e.get("probe_row") is None:
                    continue
                v = get(e["probe_row"])
                best = 0.0
                for p in gen[(S, arm, c)]["parent_ids"]:
                    pv = pvec.get(p)
                    if pv is None:
                        continue
                    pv = get(pv) if isinstance(pv, int) else pv
                    best = max(best, agree(v, pv))
                n += 1
                k_ += best >= 0.95
        ren[arm] = k_ / n
    v6 = "SUPPORTED" if (ren["IDEA"] >= 0.4 and ren["IDEA"] >= ren["T1.0"] - 0.1) else ("DISCONFIRMED" if ren["IDEA"] < 0.2 else "PARTIAL")
    OUT["V6"] = {"verdict": v6, "rename": ren}
    # ---------- V3 (re-derived from the per-candidate rows)
    v3 = json.loads((R / "v3_final.json").read_text())
    n08 = sum(1 for c in v3 if all(c["excess"].get(s, 9) <= lim[s] for s in lim))
    nb = sum(1 for c in v3 if all(c["excess"].get(s, 9) <= lim[s] for s in lim) and c["max_corpus_agreement"] < 0.9)
    novel = [c for c in v3 if c.get("manual_class") == "NOVEL" and c.get("judges_all_not_known")]
    nj = sum(1 for c in v3 if c.get("judged"))
    OUT["V3"] = {"verdict": "SUPPORTED" if novel else "DISCONFIRMED", "n_pass_08": n08, "n_pass_both": nb,
                 "n_judged": nj, "rule_of_three": 3 / nj if nj else None}
    # ---------- placebos
    rng = random.Random(7)
    # (a) shuffled arm labels across round blocks (diversity = distinct exact behaviours; 200 shuffles)
    rows_by = {}
    for (S, arm, c), e in ev.items():
        if S in SEEDS and arm in CORE and c < calls[S] and e["valid"] and e.get("probe_row") is not None:
            rows_by.setdefault((S, arm, c // 20), []).append(e["probe_row"])
    sup = 0
    for _ in range(200):
        seen = {a: set() for a in CORE}
        tot = {a: 0 for a in CORE}
        ok_seed = True
        for S in SEEDS:
            seen_s = {a: set() for a in CORE}
            for r_ in range(calls[S] // 20):
                perm = CORE[:]
                rng.shuffle(perm)
                for a, b in zip(CORE, perm):
                    seen_s[b].update(rows_by.get((S, a, r_), []))
            for a in CORE:
                seen[a] |= {(S, x) for x in seen_s[a]}
                tot[a] += calls[S]
            ok_seed &= all(len(seen_s["DTB"]) > len(seen_s[X]) for X in ("T1.0", "T1.6"))
        rr = {a: len(seen[a]) / tot[a] for a in CORE}
        Rp = {X: rr["DTB"] / rr[X] for X in ("T1.0", "T1.6", "RPB")}
        sup += (Rp["T1.0"] >= 1.5 and Rp["T1.6"] >= 1.5 and Rp["RPB"] >= 1.2 and ok_seed)
    OUT["placebo_a_shuffled_arms"] = {"supported_share": sup / 200, "fails_as_required": sup / 200 <= 0.05}
    # (b) a random-priority program must not pass V1
    rp = {}
    for s in ("H-FSW5k", "H-OR3"):
        ins = insts(s)
        rp[s] = excess([random_pack(x["items"], x["capacity"], rng) for x in ins], ins)
    OUT["placebo_b_random_priority"] = {"excess_pct": {s: round(100 * v, 2) for s, v in rp.items()},
                                        "fails_V1_as_required": not (rp["H-FSW5k"] <= lim["H-FSW5k"] and rp["H-OR3"] <= lim["H-OR3"])}
    # (c) a disguised c14 (pure python) must agree >= 0.9 with the stored c14 vector
    states = json.loads((D / "probes" / "P10.json").read_text())["states"]

    def disguised_c14(item, arr):
        top = max(arr)
        v = [(b - top) ** 2 / item + b ** 2 / item ** 2 + b ** 2 / item ** 3 for b in arr]
        v = [-x if b > item else x for x, b in zip(v, arr)]
        w = [v[0]] + [v[i] - v[i - 1] for i in range(1, len(v))]
        j = max(range(len(w)), key=lambda i: (w[i], -i))
        return arr[j]
    dvec = [disguised_c14(it, of + [cap] * ne) for it, of, ne, cap in states]
    agc = agree(dvec, cget("FunSearch-c14"))
    OUT["placebo_c_disguised_c14"] = {"agreement": agc, "passes_as_required": agc >= 0.9}
    # (d) DTB's j from a shuffled entropy vector must disagree with the logged j; unshuffled must agree
    same, dis, n = 0, 0, 0
    for (S, arm, c), g in gen.items():
        br = g.get("branch")
        if arm != "DTB" or not br or br.get("no_branch"):
            continue
        H, E = br["H"], br["E"]
        j0 = max(E, key=lambda t: (H[t], -t))
        same += j0 == br["j"]
        Hs = H[:]
        rng.shuffle(Hs)
        dis += max(E, key=lambda t: (Hs[t], -t)) != br["j"]
        n += 1
    OUT["placebo_d_shuffled_entropy"] = {"n": n, "unshuffled_rederive_agrees": same / n,
                                         "shuffled_disagree_share": dis / n, "fails_as_required": dis / n >= 0.5}
    # V5 sign-flip test: the observed mean (decision - control) reversion vs sign-flipped placebo
    v5 = json.loads((R / "v5.json").read_text())["offspring"]
    diffs = [o["decision_reversion"] - o["control_reversion"] for o in v5
             if o.get("decision_reversion") is not None and o.get("control_reversion") is not None]
    obs = sum(diffs) / len(diffs)
    flips = [sum(d * rng.choice((-1, 1)) for d in diffs) / len(diffs) for _ in range(5000)]
    p = sum(1 for f in flips if abs(f) >= abs(obs)) / len(flips)
    placebo_obs = sum(d * rng.choice((-1, 1)) for d in diffs) / len(diffs)
    p_placebo = sum(1 for f in flips if abs(f) >= abs(placebo_obs)) / len(flips)
    OUT["V5_sign_flip"] = {"n": len(diffs), "mean_diff": obs, "p_two_sided": p,
                           "placebo_sign_flipped_input_mean": placebo_obs, "placebo_p": p_placebo}
    (R / "audit_rederive.json").write_text(json.dumps(OUT, indent=1))
    print(json.dumps(OUT, indent=1)[:6000])


if __name__ == "__main__":
    sys.exit(main())
