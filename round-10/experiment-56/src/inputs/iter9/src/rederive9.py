#!/usr/bin/env python3
"""Independent re-derivation (Python standard library only; no numpy, no project imports) of every headline number from
the raw per-prompt rows, compared with the aggregated summaries; plus placebos that must FAIL.

Raw inputs: results/b2_tf_<unit>.jsonl (per prompt x arm margins), results/b1_tf_<model>.json (per prompt fork
margins and opening log-likelihoods), results/b3_heldout_rows.jsonl (per held-out prompt job values).
Writes results/rederive.json."""

from __future__ import annotations

import itertools
import json
import random
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
TOL = 1e-6


def jl(p: Path) -> list[dict]:
    with open(p) as fh:
        return [json.loads(x) for x in fh if x.strip()]


def pct(xs: list[float], q: float) -> float:
    """numpy-default (linear) percentile."""
    s = sorted(xs)
    k = (len(s) - 1) * q / 100
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def b2(mism: list, out: dict) -> None:
    summ = json.loads((RES / "b2_summary.json").read_text())
    for u in ("B3", "T10"):
        rows = jl(RES / f"b2_tf_{u}.jsonl")
        mI, mB, arm = {}, {}, {}
        for r in rows:
            mI[r["pid"]] = r["m_I"]
            mB[r["pid"]] = r["m_B"]
            arm.setdefault(r["arm"], {})[r["pid"]] = r["m"]
        pids = sorted(mI)
        den = sum(mI[p] - mB[p] for p in pids)

        def sh(a: str) -> float:
            return sum(mI[p] - arm[a][p] for p in pids) / den
        rec = {"FSTACK": sh("FSTACK"), "RSfork36": sh("RSfork36"), "RSfork23": sh("RSfork23"),
               "SPEC": sh("SPEC") if "SPEC" in arm else None, "gap_mean": statistics.mean(mI[p] - mB[p] for p in pids)}
        R = [sh(f"R{s}") for s in range(50)]
        rec["R_median"] = statistics.median(R)
        rec["R_p95"] = pct(R, 95)
        rec["R_empirical_p"] = (1 + sum(x >= rec["FSTACK"] for x in R)) / 51
        S = summ["units"][u]
        cmp_ = {"FSTACK": S["arms"]["FSTACK"]["share"], "RSfork36": S["RS_fork"]["36"],
                "RSfork23": S["RS_fork"]["23"], "SPEC": S["arms"].get("SPEC", {}).get("share"),
                "gap_mean": S["gap_mean"], "R_median": S["null_R"]["median"], "R_p95": S["null_R"]["p95"],
                "R_empirical_p": S["null_R"]["empirical_p_upper"]}
        for k, v in rec.items():
            if v is None or cmp_.get(k) is None:
                continue
            if abs(v - cmp_[k]) > TOL:
                mism.append(f"B2 {u} {k}: rederived {v} vs summary {cmp_[k]}")
        # placebo: node-label permutation -> treat a random R set as 'the circuit' against the other 49 sets
        rng = random.Random(7)
        ps = []
        for _ in range(200):
            j = rng.randrange(50)
            others = [x for i, x in enumerate(R) if i != j]
            ps.append((1 + sum(x >= R[j] for x in others)) / 50)
        rec["placebo_permuted_node_labels_frac_p_le_0.05"] = sum(p <= 0.05 for p in ps) / len(ps)
        rec["placebo_permuted_node_labels_fails"] = rec["placebo_permuted_node_labels_frac_p_le_0.05"] <= 0.10
        # placebo: swap the instruct and base anchors -> FSTACK 'share' sign flips relative to the gap
        rec["placebo_anchor_swap_share"] = sum(mB[p] - arm["FSTACK"][p] for p in pids) / sum(mB[p] - mI[p]
                                                                                             for p in pids)
        out[f"B2_{u}"] = rec


def b1(mism: list, out: dict) -> None:
    summ = json.loads((RES / "b1_summary.json").read_text())
    pairs = {"gemma": ("gemma", "gemma_pt"), "llama": ("llama", "llama_base")}
    for fam, (ki, kb) in pairs.items():
        pi, pb = RES / f"b1_tf_{ki}.json", RES / f"b1_tf_{kb}.json"
        if not (pi.exists() and pb.exists()):
            continue
        I, B = json.loads(pi.read_text()), json.loads(pb.read_text())
        units = json.loads((RES / "units.json").read_text())
        for u, ru in I["units"].items():
            U = units[u]
            byI = {r["pid"]: r for r in ru["prompts"]}
            byB = {r["pid"]: r for r in B["units"][u]["prompts"]}
            keep = [p["pid"] for p in U["prompts"]
                    if min(byI[p["pid"]]["forks"][f["fork_id"]]["chat"]["logp_opening"] for f in U["forks"]) >= -5.0]
            keep = keep[:U.get("max_prompts", 20)]
            if not keep:                       # committed rule drops every prompt -> descriptive on all prompts
                keep = [p["pid"] for p in U["prompts"]][:U.get("max_prompts", 20)]
                out[f"B1_{u}_descriptive_only"] = True
            for f in U["forks"]:
                fid = f["fork_id"]
                for mode in ("chat", "plain"):
                    g = [byI[k]["forks"][fid][mode]["margin"] - byB[k]["forks"][fid][mode]["margin"] for k in keep]
                    gm = statistics.mean(g)
                    ref = summ["units"][u]["forks"][fid][mode]["gain_mean"]
                    if abs(gm - ref) > TOL:
                        mism.append(f"B1 {fid} {mode} gain: rederived {gm} vs summary {ref}")
                    out[f"B1_{fid}_{mode}_gain"] = gm
                    # placebo: swapped labels -> the >= 2 nat gain criterion must fail
                    out[f"B1_{fid}_{mode}_placebo_swapped_gain"] = -gm
                    out[f"B1_{fid}_{mode}_placebo_fails"] = (-gm) < 2.0


def b3(mism: list, out: dict) -> None:
    p = RES / "b3_heldout_rows.jsonl"
    if not p.exists():
        return
    rows = jl(p)
    summ = json.loads((RES / "b3_summary.json").read_text())
    for key, v in summ["per_node"].items():
        if not key.startswith("aligned|") or v["mode"] not in ("ablate", "steer"):
            continue
        d = []
        for r in rows:
            node = r["res"].get(f"{key}|node")
            rv = [r["res"][f"{key}|r{j}"] for j in range(50) if f"{key}|r{j}" in r["res"]]
            if node is None or not rv:
                continue
            d.append(node - sum(rv) / len(rv))
        md = statistics.mean(d)
        if abs(md - v["mean_d_heldout"]) > TOL:
            mism.append(f"B3 {key} mean_d: rederived {md} vs summary {v['mean_d_heldout']}")
        obs = abs(md)
        cnt = sum(1 for s in itertools.product((1, -1), repeat=len(d))
                  if abs(sum(a * b for a, b in zip(d, s)) / len(d)) >= obs - 1e-12)
        pv = cnt / 2 ** len(d)
        if abs(pv - v["p_sign_flip_heldout"]) > TOL:
            mism.append(f"B3 {key} p: rederived {pv} vs summary {v['p_sign_flip_heldout']}")
        # placebo: random sign assignment of the per-prompt d (shuffled pairing) -> p should usually be large
        rng = random.Random(11)
        pl = []
        for _ in range(100):
            dd = [x * rng.choice((1, -1)) for x in d]
            o2 = abs(statistics.mean(dd))
            c2 = sum(1 for s in itertools.product((1, -1), repeat=len(dd))
                     if abs(sum(a * b for a, b in zip(dd, s)) / len(dd)) >= o2 - 1e-12)
            pl.append(c2 / 2 ** len(dd))
        out[f"B3_{key}"] = {"mean_d": md, "p": pv, "placebo_sign_shuffle_frac_p_le_0.05":
                            sum(x <= 0.05 for x in pl) / len(pl)}


def gen(mism: list, out: dict) -> None:
    raw = jl(RES.parent / "data" / "samples.jsonl")
    lab = {r["sid"]: r for r in jl(RES.parent / "data" / "labels_gen.jsonl")}
    summ = json.loads((RES / "b2_generation.json").read_text())
    minority = {"B3": {"prim_heap", "prim_array"}, "T10": {"dfs", "bfs"}}
    for u in ("B3", "T10"):
        ind = {}
        for r in raw:
            if r["task"] != u:
                continue
            L = lab[r["sid"]]
            ind.setdefault(r["arm"], {})[(r["template"], r["slot"])] = int(L["label"] in minority[u] and L["passed"])
        for a, b in (("FSTACK", "TWIN"), ("FSTACK", "RAND"), ("FSTACK", "FPD"), ("FPD", "TWIN")):
            ks = sorted(set(ind[a]) & set(ind[b]))
            n10 = sum(1 for k in ks if ind[a][k] == 1 and ind[b][k] == 0)
            n01 = sum(1 for k in ks if ind[a][k] == 0 and ind[b][k] == 1)
            ref = summ[u]["tests"][f"{a}_vs_{b}"]
            if (n10, n01) != (ref["b_first_only"], ref["c_second_only"]):
                mism.append(f"gen {u} {a}_vs_{b}: rederived {n10}:{n01} vs {ref['b_first_only']}:{ref['c_second_only']}")
            n = n10 + n01
            p = min(1.0, 2 * sum(__import__("math").comb(n, i) for i in range(0, min(n10, n01) + 1)) / 2 ** n) if n else 1.0
            out[f"gen_{u}_{a}_vs_{b}"] = {"b": n10, "c": n01, "p": p}
            # placebo: shuffle the CRN slot pairing of the second arm -> the paired McNemar should lose significance
            rng = random.Random(5)
            pl = []
            for _ in range(200):
                kk = ks[:]
                rng.shuffle(kk)
                m10 = sum(1 for k, k2 in zip(ks, kk) if ind[a][k] == 1 and ind[b][k2] == 0)
                m01 = sum(1 for k, k2 in zip(ks, kk) if ind[a][k] == 0 and ind[b][k2] == 1)
                nn = m10 + m01
                pl.append(min(1.0, 2 * sum(__import__("math").comb(nn, i) for i in range(0, min(m10, m01) + 1))
                              / 2 ** nn) if nn else 1.0)
            out[f"gen_{u}_{a}_vs_{b}"]["placebo_slot_shuffle_median_p"] = statistics.median(pl)
            out[f"gen_{u}_{a}_vs_{b}"]["note_slot_shuffle"] = ("uninformative when one arm has no minority programs "
                                                              "(the contrast is then marginal, pairing-free)")
            # placebo 2: swap the two arms' labels within each CRN pair at random (the null McNemar permutes)
            pl2 = []
            for _ in range(200):
                m10 = m01 = 0
                for k in ks:
                    x, y = (ind[a][k], ind[b][k]) if rng.random() < 0.5 else (ind[b][k], ind[a][k])
                    m10 += int(x == 1 and y == 0)
                    m01 += int(x == 0 and y == 1)
                nn = m10 + m01
                pl2.append(min(1.0, 2 * sum(__import__("math").comb(nn, i) for i in range(0, min(m10, m01) + 1))
                               / 2 ** nn) if nn else 1.0)
            out[f"gen_{u}_{a}_vs_{b}"]["placebo_within_pair_arm_swap_median_p"] = statistics.median(pl2)
            out[f"gen_{u}_{a}_vs_{b}"]["placebo_within_pair_arm_swap_frac_p_le_0.05"] = sum(x <= 0.05 for x in pl2) / 200


def chain(mism: list, out: dict) -> None:
    """Commit chain links (sha256(prev + file sha)) and 'decisive rows after their commit' (stdlib)."""
    import hashlib
    lines = [l.split() for l in (ROOT / "commitments.log").read_text().splitlines() if l.strip()]
    prev = hashlib.sha256(b"iter9_base").hexdigest()
    ok = True
    when = {}
    for utc, name, fsha, link in lines:
        fs = hashlib.sha256((ROOT / "predictions" / f"{name}.json").read_bytes()).hexdigest()
        ok &= fs == fsha and hashlib.sha256((prev + fsha).encode()).hexdigest() == link
        prev = link
        when[name] = utc
    first = {}
    for nm, path in (("b2_tf", RES / "b2_tf_B3.jsonl"), ("b3_heldout", RES / "b3_heldout_rows.jsonl"),
                     ("generation", RES.parent / "data" / "samples.jsonl")):
        rows = jl(path)
        first[nm] = min(r["utc"] for r in rows) if rows else None
    order = {"b2_tf_after_commit0": first["b2_tf"] > when.get("commit0", "~"),
             "b3_heldout_after_commitB3": first["b3_heldout"] > when.get("commitB3", "~"),
             "generation_after_commit1_gen": first["generation"] > when.get("commit1_gen", "~")}
    out["commit_chain"] = {"n": len(lines), "all_ok": ok, "commits": when, "first_rows": first, "order": order}
    if not ok:
        mism.append("commit chain does not verify")
    for k, v in order.items():
        if not v:
            mism.append(f"timestamp order fails: {k}")


def main() -> None:
    mism: list[str] = []
    out: dict = {}
    for fn in (b2, b1, b3, gen, chain):
        try:
            fn(mism, out)
        except FileNotFoundError as e:
            out[f"{fn.__name__}_missing"] = str(e)
    out["mismatches"] = mism
    out["n_mismatches"] = len(mism)
    (RES / "rederive.json").write_text(json.dumps(out, indent=1))
    print(f"rederive: {len(mism)} mismatches")
    for m in mism[:20]:
        print("  ", m)


if __name__ == "__main__":
    main()
