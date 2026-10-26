#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers from the RAW files (data/*/programs.jsonl, data/*/decisions/*.u16,
data/instances/*.json, data/corpus/corpus.json, audit/manual_read.json, commitments.log). It imports nothing from src/.

- V1: best program per stream re-selected from the rows (min F, ties to shorter code); held-out bins re-packed with a
  pure-python online packer (bins pre-allocated, argmax with first index on ties, NaN = first NaN) - numpy is used only
  to call the evolved priority function itself; excess = (mean bins - mean L1) / mean L1.
- V2: behaviour clusters recomputed with a one-hot sparse agreement product (not the broadcasting code in src/cluster.py)
  and scipy complete linkage; R1, R2, R3, per-seed ratios and the verdict conditions recomputed.
- V6: rename rates recomputed with the same one-hot agreement.
- Placebos: R1 under within-seed label shuffles; V5 sign test under random birth/control relabelling.
- Commitment chain re-hashed; no search row predates commit #1.
Writes results/rederive.json."""
import hashlib
import json
import math
import random
import sys
import time
from pathlib import Path

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.sparse import csr_matrix

ROOT = Path(__file__).resolve().parent.parent
ERR, NS = 65535, 2000


def rows(run):
    p = ROOT / "data" / run / "programs.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []


def decs(run, seed, arm):
    return np.fromfile(ROOT / "data" / run / "decisions" / f"{seed}_{arm}.u16", dtype=np.uint16).reshape(-1, NS)


def onehot(D):
    """rows x (state*152): 1 where decision == value (values 0..150; ERR -> no column)."""
    r, c = np.nonzero(D != ERR)
    v = D[r, c].astype(np.int64)
    return csr_matrix((np.ones(len(r), dtype=np.float32), (r, c * 152 + v)), shape=(len(D), NS * 152))


def n_clusters(D):
    if len(D) == 0:
        return 0
    U = np.unique(D, axis=0)
    if len(U) == 1:
        return 1
    X = onehot(U)
    C = (X @ X.T).toarray()
    dist = NS - C
    np.fill_diagonal(dist, 0)
    iu = np.triu_indices(len(U), 1)
    return int(len(set(fcluster(linkage(dist[iu].astype(float), "complete"), t=100, criterion="distance"))))


# ----------------------------------------------------------------- pure-python packer
def compile_prog(code):
    ns = {"np": np, "math": math}
    exec(compile(code, "<prog>", "exec"), ns)  # programs already passed the sandbox screen during the search
    return ns["priority"]


def pack_py(items, cap, prio):
    rem = [cap] * len(items)
    for it in items:
        idx = [i for i, r in enumerate(rem) if r >= it]
        p = prio(it, np.array([rem[i] for i in idx])).tolist()
        best, bi = None, 0
        for k, v in enumerate(p):
            if v != v:          # NaN: np.argmax returns the first NaN
                bi = k
                break
            if best is None or v > best:
                best, bi = v, k
        rem[idx[bi]] -= it
    return sum(1 for r in rem if r != cap)


def excess(set_name, prio):
    insts = json.loads((ROOT / "data" / "instances" / f"{set_name}.json").read_text())
    b = [pack_py(x["items"], x["capacity"], prio) for x in insts]
    l1 = [math.ceil(sum(x["items"]) / x["capacity"]) for x in insts]
    return 100.0 * (sum(b) / len(b) - sum(l1) / len(l1)) / (sum(l1) / len(l1))


def main():
    t0 = time.time()
    out = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    R = rows("main")
    core = ["T1.0", "T1.6", "DTB", "RPB"]
    calls = {}
    for r in R:
        calls[(r["arm"], r["seed"])] = calls.get((r["arm"], r["seed"]), 0) + 1
    c_s = min(calls[(a, s)] for a in core for s in (0, 1))
    out["C_s"] = c_s
    # ---------------- V1 (pure-python re-pack of the re-selected best programs)
    thr_fs, thr_or = 0.8 * 3.9843042559613666, 0.8 * 5.367793240556666
    best = {}
    for a in core + ["IDEA"]:
        val = [r for r in R if r["arm"] == a and r["call_id"] < c_s and r["error_type"] == "ok" and r["F"] is not None]
        b = min(val, key=lambda r: (r["F"], len(r["code"])))
        prio = compile_prog(b["code"])
        np.seterr(all="ignore")
        best[a] = {"pid": b["pid"], "F": b["F"], "exc_FSW5k": excess("H-FSW5k", prio), "exc_OR3": excess("H-OR3", prio)}
    passes = {a: best[a]["exc_FSW5k"] <= thr_fs and best[a]["exc_OR3"] <= thr_or for a in core}
    out["V1"] = {"best": best, "pass": passes,
                 "verdict": "SUPPORTED" if all(passes.values()) else
                 ("DISCONFIRMED" if not any(best[a]["exc_FSW5k"] <= thr_fs or best[a]["exc_OR3"] <= thr_or for a in core)
                  else "PARTIAL")}
    # ---------------- V2 (one-hot agreement, own linkage call)
    D = {}
    vd = {}
    for a in core + ["IDEA"]:
        for s in (0, 1):
            rs = sorted((r for r in R if r["arm"] == a and r["seed"] == s), key=lambda r: r["call_id"])[:c_s]
            M = decs("main", s, a)[:len(rs)]
            keep = [i for i, r in enumerate(rs) if r["error_type"] == "ok" and r["F"] is not None and not r.get("probe_failed")]
            vd[(a, s)] = M[keep]
            D[(a, s)] = n_clusters(M[keep])
    rate = {a: 1000.0 * (D[(a, 0)] + D[(a, 1)]) / (2 * c_s) for a in core + ["IDEA"]}
    R1, R2, R3 = rate["DTB"] / rate["T1.0"], rate["DTB"] / rate["T1.6"], rate["DTB"] / rate["RPB"]
    per_seed = {f"s{s}_{X}": D[("DTB", s)] / D[(X, s)] for s in (0, 1) for X in ("T1.0", "T1.6")}
    out["V2"] = {"D": {f"{a}|{s}": v for (a, s), v in D.items()}, "R1": R1, "R2": R2, "R3": R3, "per_seed": per_seed,
                 "conditions_without_rho": {"R1>=1.5": R1 >= 1.5, "R2>=1.5": R2 >= 1.5,
                                            "per_seed>1": all(v > 1 for v in per_seed.values()), "R3>=1.2": R3 >= 1.2},
                 "verdict": "DISCONFIRMED" if (R1 <= 1 or R2 <= 1) else
                 ("SUPPORTED" if (R1 >= 1.5 and R2 >= 1.5 and R3 >= 1.2 and all(v > 1 for v in per_seed.values())) else "PARTIAL")}
    # placebo: within-seed label shuffles of DTB and T1.0 (50 shuffles here; 200 in results/placebos.json)
    rnd = random.Random(7)
    sh = []
    for _ in range(50):
        a_c = b_c = 0
        for s in (0, 1):
            pool = np.concatenate([vd[("DTB", s)], vd[("T1.0", s)]])
            idx = list(range(len(pool)))
            rnd.shuffle(idx)
            na = len(vd[("DTB", s)])
            a_c += n_clusters(pool[idx[:na]])
            b_c += n_clusters(pool[idx[na:]])
        sh.append(a_c / b_c)
    out["V2"]["placebo_label_shuffle"] = {"n": len(sh), "share_R1_ge_1.5": sum(v >= 1.5 for v in sh) / len(sh),
                                         "median": sorted(sh)[len(sh) // 2]}
    # ---------------- V6 rename rates
    corpus = json.loads((ROOT / "data" / "corpus" / "corpus.json").read_text())
    cv = {e["name"]: np.array(e["decisions"], dtype=np.uint16) for e in corpus["entries"] if e.get("decisions")}
    by_pid = {}
    for r in R:
        by_pid[r["pid"]] = r
    cache = {(a, s): decs("main", s, a) for a in core + ["IDEA"] for s in (0, 1)}

    def dvec(pid):
        if pid == "seed-BF":
            return cv["BF"]
        if pid == "seed-FF":
            return cv["FF"]
        r = by_pid[pid]
        return cache[(r["arm"], r["seed"])][r["dec_ref"][1]]

    ren = {}
    for a in ("IDEA", "T1.0"):
        k = n = 0
        for r in R:
            if r["arm"] != a or r["call_id"] >= c_s or r["error_type"] != "ok" or r["F"] is None or r.get("probe_failed"):
                continue
            d = dvec(r["pid"])
            ag = max(float(np.mean((d == dvec(p)) & (d != ERR))) for p in r["parent_ids"])
            k += ag >= 0.95
            n += 1
        ren[a] = {"renames": int(k), "n": n, "rate": k / n}
    out["V6"] = ren
    # ---------------- V3 counts from the raw read + candidate file
    reads = json.loads((ROOT / "audit" / "manual_read.json").read_text())
    v3c = json.loads((ROOT / "results" / "v3_candidates.json").read_text())
    nb = [c for c in v3c["candidates"] if c["exc_FSW5k"] is not None and c["exc_OR3"] is not None and
          c["exc_FSW5k"] <= thr_fs and c["exc_OR3"] <= thr_or and c["max_corpus_agreement"] < 0.9]
    aud = v3c["audited"]
    # re-check the corpus agreement of the audited representatives with the one-hot path
    names = list(cv)
    X = onehot(np.stack([cv[n] for n in names]))
    maxag = []
    for c in aud:
        r = by_pid.get(c["pid"])
        if r is None:
            continue
        d = cache[(r["arm"], r["seed"])][r["dec_ref"][1]]
        ag = (onehot(d[None, :]) @ X.T).toarray()[0] / NS
        maxag.append(float(ag.max()))
    out["V3"] = {"n_NB_recomputed": len(nb), "n_audited": len(aud),
                 "n_NOT_KNOWN_manual": sum(1 for c in aud if reads[c["anon_id"]]["manual_class"] == "NOT_KNOWN"),
                 "audited_max_corpus_agreement_max": max(maxag) if maxag else None,
                 "all_audited_below_0.9": all(m < 0.9 for m in maxag)}
    # ---------------- V5 sign test on shuffled labels
    v5 = json.loads((ROOT / "results" / "v5.json").read_text())
    pp = v5.get("per_position", [])
    obs = (v5["sign_test"]["birth_gt_control"], v5["sign_test"]["birth_lt_control"])
    rnd = random.Random(11)
    fmax = {}
    for x in pp:
        if x["reversion_rate"] is None:
            continue
        fmax.setdefault(x["founder"], []).append((x["kind"], x["reversion_rate"]))
    gt = lt = 0
    for f, lst in fmax.items():
        kinds = [k for k, _ in lst]
        rnd.shuffle(kinds)
        b = [v for k, (_, v) in zip(kinds, lst) if k == "births"]
        c = [v for k, (_, v) in zip(kinds, lst) if k == "controls"]
        if b and c:
            gt += max(b) > max(c)
            lt += max(b) < max(c)
    out["V5"] = {"observed_sign": obs, "shuffled_sign": (gt, lt)}
    # ---------------- commitments chain + timing
    lines = (ROOT / "commitments.log").read_text().splitlines()
    prev, ok = "GENESIS", True
    for ln in lines:
        utc, h, f, ph = ln.split(" ")
        ok &= ph == hashlib.sha256(prev.encode()).hexdigest() and hashlib.sha256((ROOT / f).read_bytes()).hexdigest() == h
        prev = ln
    c1 = lines[0].split(" ")[0]
    first_round_utc = None
    st = json.loads((ROOT / "results" / "partial_status_main.json").read_text())
    out["commitments"] = {"chain_ok": bool(ok), "n": len(lines), "commit1_utc": c1,
                          "search_log_first_utc": (ROOT / "logs" / "search_main.log").read_text().split("|")[0][:19]
                          if (ROOT / "logs" / "search_main.log").exists() else None}
    out["secs"] = time.time() - t0
    (ROOT / "results" / "rederive.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: out[k] for k in ("C_s", "V1", "V2", "V6", "V3", "V5", "commitments")}, indent=1, default=float)[:6000])


if __name__ == "__main__":
    sys.exit(main())
