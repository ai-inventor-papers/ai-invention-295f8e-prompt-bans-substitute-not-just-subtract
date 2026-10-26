#!/usr/bin/env python3
"""Independent re-derivation of every headline from data/samples.jsonl, WITHOUT importing the pipeline code
(src/). Reads only data/samples.jsonl, the task catalogues (inputs/), the commits (predictions/) and the result files
it checks (results/). Writes results/rederive.json with every comparison and the placebos:
  (a) arm-shuffle placebo: on the S2 pairs, the T and control outcomes are swapped at random within each slot
      (200 shuffles); the one-sided exact McNemar must reject at about the nominal 5% (it must NOT reproduce B);
  (b) label-shuffle placebo: the BASE_CHAT rows are permuted across tasks (100 permutations); the strata pattern of
      the real data must not be reproduced (share of tasks keeping their stratum is reported).
"""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "inputs" / "exp11" / "bench"
PATH_CAT = {"T1": ["bfs", "dfs", "bibfs", "iddfs", "astar_gbfs", "dijkstra"],
            "T2": ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"]}


def cat(t: str) -> list[str]:
    if t in PATH_CAT:
        return PATH_CAT[t]
    d = next(x for x in BENCH.iterdir() if x.is_dir() and x.name.startswith(t + "_"))
    return [c["mode"] for c in json.loads((d / "spec.json").read_text())["catalogue"]]


def load(p: Path):
    return json.loads(p.read_text())


def correct(r) -> bool:
    return bool(r.get("passed")) and r.get("label") not in (None, "invalid")


def yoff(r, d, c) -> int:
    return int(correct(r) and r.get("label") in c and r.get("label") != d)


def offshare(rows, d, c, attempts=False):
    pool = [r for r in rows if (r.get("label") not in (None, "invalid")) if attempts] if attempts else \
        [r for r in rows if correct(r)]
    if not pool:
        return None, 0
    return sum(1 for r in pool if r["label"] in c and r["label"] != d) / len(pool), len(pool)


def mcn(a, b):
    b_ = sum(1 for x, y in zip(a, b) if x == 1 and y == 0)
    c_ = sum(1 for x, y in zip(a, b) if x == 0 and y == 1)
    return 1.0 if b_ + c_ == 0 else float(stats.binom.sf(b_ - 1, b_ + c_, 0.5))


def stratum(b):
    return None if b is None else ("BASE-DIVERSE" if b >= 0.2 else ("BASE-COLLAPSED" if b < 0.05 else "INTERMEDIATE"))


def main() -> None:
    S = [json.loads(l) for l in (ROOT / "data" / "samples.jsonl").read_text().splitlines() if l.strip()]
    c1 = load(ROOT / "predictions" / "commit1.json")
    c2p = ROOT / "predictions" / "commit2.json"
    c2 = load(c2p) if c2p.exists() else None
    tasks = list(c1["per_task"])
    by = {}
    for r in S:
        by.setdefault((r["task"], r["arm"]), []).append(r)
    checks, mism = {}, 0
    beta_mine = {}
    for t in tasks:
        c = cat(t)
        tw = [r for r in by.get((t, "TWIN"), []) if int(r["slot"]) < 10 and r["model"] == "Qwen/Qwen3-8B"]
        comp = Counter(r["label"] for r in tw if correct(r))
        n = sum(comp.values())
        lab, k = comp.most_common(1)[0] if comp else (None, 0)
        d = lab if (n and k / n >= 0.6 and lab in c) else None
        bc = by.get((t, "BASE_CHAT"), [])
        b, nc = offshare(bc, d, c)
        basis = "CORRECT"
        if nc < 20:
            b, _ = offshare(bc, d, c, attempts=True)
            basis = "ATTEMPT"
        beta_mine[t] = b
        ok_d = d == c1["per_task"][t]["default"]
        ok_b = (b is None and c1["per_task"][t]["beta"] is None) or abs((b or 0) - (c1["per_task"][t]["beta"] or 0)) < 1e-9
        ok_s = stratum(b) == c1["per_task"][t]["stratum"]
        ok_basis = basis == c1["per_task"][t]["beta_basis"]
        checks[f"{t}|default_beta_stratum"] = {"default": d, "beta": b, "stratum": stratum(b),
                                               "match": bool(ok_d and ok_b and ok_s and ok_basis)}
        mism += int(not (ok_d and ok_b and ok_s and ok_basis))
    out = {"checks": checks}
    if c2:
        conf = load(ROOT / "results" / "confirmation.json")
        for t, sel in c2["selection"].items():
            if sel["lambda_star"] is None and not sel.get("T_cells"):
                continue
            d, c = c1["per_task"][t]["default"], cat(t)
            tw = [r for r in by.get((t, "TWIN"), []) if int(r["slot"]) < 10 and r["model"] == "Qwen/Qwen3-8B"]
            twp = sum(correct(r) for r in tw) / max(len(tw), 1)
            best, bl = None, None
            if t in c1["strata"]["BASE-DIVERSE"] or t in c1["strata"]["INTERMEDIATE"]:
                for lam in (0.25, 0.5, 1.0):
                    rr = [r for r in by.get((t, f"T{lam}"), []) if int(r["slot"]) < 10]
                    if not rr:
                        continue
                    p = sum(correct(r) for r in rr) / len(rr)
                    s, _ = offshare(rr, d, c)
                    if p >= 0.8 * twp and s is not None and (best is None or s > best):
                        best, bl = s, lam
            ok = bl == sel["lambda_star"]
            checks[f"{t}|lambda_star"] = {"mine": bl, "committed": sel["lambda_star"], "match": ok}
            mism += int(not ok)
        fam = {}
        for t, r in conf["per_task"].items():
            d, c = c1["per_task"][t]["default"], cat(t)
            arms = list(r["arms"])
            T = arms[0]
            slots = set(range(10, 20 if r["N"] == 50 else 30))  # N counts programs: 5 templates x slots
            Tr = {(x["template"], int(x["slot"])): x for x in by.get((t, T), []) if int(x["slot"]) in slots}
            for a in arms[1:]:
                Cr = {(x["template"], int(x["slot"])): x for x in by.get((t, a), []) if int(x["slot"]) in slots}
                keys = sorted(set(Tr) & set(Cr))
                p = mcn([yoff(Tr[k], d, c) for k in keys], [yoff(Cr[k], d, c) for k in keys])
                q = r["arms"][a].get("mcnemar_T_vs_this", {}).get("p_one")
                ok = q is not None and abs(p - q) < 1e-9
                checks[f"{t}|{a}|mcnemar"] = {"mine": p, "pipeline": q, "match": ok}
                mism += int(not ok)
                if r["decisive"]:
                    fam[f"{t}|{r['arms'][a].get('control_class')}"] = p
        keys = sorted(fam, key=fam.get)
        run, holm = 0.0, {}
        for i, k in enumerate(keys):
            run = max(run, min(1.0, (len(keys) - i) * fam[k]))
            holm[k] = run
        okh = all(abs(holm[k] - conf["holm_adjusted"].get(k, -1)) < 1e-9 for k in holm)
        checks["holm"] = {"mine": holm, "match": okh}
        mism += int(not okh)
        # placebo (a): arm shuffle within slots
        rng = np.random.default_rng(5)
        rej = tot = 0
        for t, r in conf["per_task"].items():
            if not r["decisive"]:
                continue
            d, c = c1["per_task"][t]["default"], cat(t)
            arms = list(r["arms"])
            slots = set(range(10, 20 if r["N"] == 50 else 30))  # N counts programs: 5 templates x slots
            Tr = {(x["template"], int(x["slot"])): x for x in by.get((t, arms[0]), []) if int(x["slot"]) in slots}
            Mr = {(x["template"], int(x["slot"])): x for x in by.get((t, arms[1]), []) if int(x["slot"]) in slots}
            keys = sorted(set(Tr) & set(Mr))
            ya = np.array([yoff(Tr[k], d, c) for k in keys])
            yb = np.array([yoff(Mr[k], d, c) for k in keys])
            for _ in range(200):
                sw = rng.uniform(size=len(keys)) < 0.5
                a2, b2 = np.where(sw, yb, ya), np.where(sw, ya, yb)
                rej += mcn(a2.tolist(), b2.tolist()) < 0.05
                tot += 1
        out["placebo_arm_shuffle"] = {"rejection_rate": rej / max(tot, 1), "n": tot,
                                      "pass": (rej / max(tot, 1)) <= 0.10}
    # placebo (b): base rows permuted across tasks
    rng = np.random.default_rng(6)
    keep = []
    rows = {t: by.get((t, "BASE_CHAT"), []) for t in tasks}
    for _ in range(100):
        perm = rng.permutation(len(tasks))
        same = 0
        for i, t in enumerate(tasks):
            src = tasks[perm[i]]
            d, c = c1["per_task"][t]["default"], cat(t)
            b, nc = offshare(rows[src], d, c)
            same += int(stratum(b) == c1["per_task"][t]["stratum"])
        keep.append(same / len(tasks))
    out["placebo_label_shuffle"] = {"mean_share_tasks_keeping_stratum": float(np.mean(keep)),
                                    "note": "labels of another task are mostly outside this task's catalogue, so the "
                                            "permuted beta collapses; a high share would mean the strata are not "
                                            "task-specific"}
    out["n_mismatches"] = mism
    out["n_checks"] = len(checks)
    (ROOT / "results" / "rederive.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"rederive: {len(checks)} checks, {mism} mismatches; placebos {out.get('placebo_arm_shuffle')}, "
          f"{out['placebo_label_shuffle']['mean_share_tasks_keeping_stratum']:.2f}")


if __name__ == "__main__":
    main()
