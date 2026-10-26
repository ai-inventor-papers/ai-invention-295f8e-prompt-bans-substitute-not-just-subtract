#!/usr/bin/env python3
"""Placebos that must fail to show an effect (audit/placebos.json). Independent of src/.

P1 within-task label shuffle across arms (exp17 alpha-1 directions + twin, 1,000 draws): observed escape counts on
   T03 and T2 must exceed the placebo 95th percentile.
P2 task shuffle of catalogue-only ban avoidance against movability (1e5 draws): placebo median Fisher p >= 0.3.
P3 Llama landings replaced by permuted / chance landings: hits fall to within 1 of the expected chance hits.
P4 route arm labels permuted within task (exp16 a vs c/d/K0/V1): the JS divergence falls within its null.
"""

from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

def _dep(aid: str, env: str, folder: str) -> str:
    """AII_ITERn or the unpublished paths.local.json on the run server; else the published sibling folder under
    AII_DEPS_DIR (default: this workspace's parent), named by artifact id or by the original folder name."""
    base = os.environ.get(env)
    loc = Path(__file__).resolve().parent.parent / "paths.local.json"
    if not base and loc.exists():
        base = json.loads(loc.read_text()).get(env)
    if base:
        return f"{base}/{folder}"
    deps = Path(os.environ.get("AII_DEPS_DIR") or Path(__file__).resolve().parent.parent.parent)
    for cand in (deps / aid, deps / folder, *sorted(deps.glob(f"*{aid}*"))):
        if cand.is_dir():
            return str(cand)
    raise FileNotFoundError(f"dependency {aid} ({folder}) not found; set AII_DEPS_DIR or {env}")

WS = Path(__file__).resolve().parent.parent
E17 = _dep("art_pVlCZ272hDV7", "AII_ITER3", "gen_art_experiment_17")
E15 = _dep("art_Q-qh-9HhPoWo", "AII_ITER3", "gen_art_experiment_15")
E16 = _dep("art__5akZ9W9iZM4", "AII_ITER3", "gen_art_experiment_16")
DEF = {"T03": "full_sort", "T2": "dijkstra", "T03b": "full_sort"}
NOATT = {"invalid", "no_code", "unparseable", "disputed", "unresolved", ""}


def jl(path):
    with open(path) as f:
        return [json.loads(x) for x in f if x.strip()]


def tru(v):
    return v is True or str(v) == "True"


def escapes(arms: dict, twin: str, D: str) -> int:
    def stats_(rows):
        att = [r for r in rows if r[0] not in NOATT]
        off = 1 - sum(r[0] == D for r in att) / len(att) if att else np.nan
        return off, sum(r[1] for r in rows) / len(rows)
    to, tp = stats_(arms[twin])
    n = 0
    for a, rows in arms.items():
        if a == twin:
            continue
        o, p_ = stats_(rows)
        n += int(o - to >= 0.20 - 1e-9 and p_ >= 0.8 * tp - 1e-12)
    return n


def js2(p, q):
    p = np.asarray(p, float) / np.sum(p)
    q = np.asarray(q, float) / np.sum(q)
    m = 0.5 * (p + q)
    kl = lambda a, b: float((a[a > 0] * np.log2(a[a > 0] / b[a > 0])).sum())  # noqa: E731
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def main() -> None:
    rng = np.random.default_rng(20261021)
    out = {}
    # P1
    g = defaultdict(list)
    for r in jl(f"{E17}/data/labels.jsonl"):
        g[(r["task"], r["arm"])].append((r["label"], tru(r["passed"])))
    p1 = {}
    for t, D in (("T03", "full_sort"), ("T2", "dijkstra")):
        arms = {a: rows for (tt, a), rows in g.items() if tt == t and (a.endswith("_a1.0") and a.startswith("RAND") or a == "NEUTRAL")}
        obs = escapes(arms, "NEUTRAL", D)
        sizes = {a: len(v) for a, v in arms.items()}
        pool = [x for v in arms.values() for x in v]
        null = []
        for _ in range(1000):
            perm = [pool[i] for i in rng.permutation(len(pool))]
            k, sh = 0, {}
            for a, n in sizes.items():
                sh[a] = perm[k:k + n]
                k += n
            null.append(escapes(sh, "NEUTRAL", D))
        q95 = float(np.quantile(null, 0.95))
        p1[t] = {"observed_escapes": obs, "placebo_q95": q95, "placebo_mean": float(np.mean(null)),
                 "real_exceeds_placebo": bool(obs > q95)}
    out["P1_label_shuffle"] = {"per_task": p1, "placebo_failed_to_show_effect": all(v["real_exceeds_placebo"] for v in p1.values())}
    # P2
    scr = json.loads((WS / "screen.json").read_text())["tasks"]
    tasks = sorted(scr)
    mov = np.array([scr[t]["movable"] for t in tasks])
    comp = np.array([int(scr[t]["cat_only_ban_avoidance"] >= 0.5) for t in tasks])
    obs_p = stats.fisher_exact([[int(((mov == 1) & (comp == 1)).sum()), int(((mov == 1) & (comp == 0)).sum())],
                                [int(((mov == 0) & (comp == 1)).sum()), int(((mov == 0) & (comp == 0)).sum())]],
                               alternative="greater").pvalue
    # Fisher p depends only on the 2x2 table; tabulate by the overlap count k, then draw 1e5 shuffles
    n_m, n_c, N = int(mov.sum()), int(comp.sum()), len(tasks)
    pk = {}
    for k in range(0, min(n_m, n_c) + 1):
        tab = [[k, n_m - k], [n_c - k, N - n_m - n_c + k]]
        if min(tab[0] + tab[1]) >= 0:
            pk[k] = stats.fisher_exact(tab, alternative="greater").pvalue
    ks = []
    for _ in range(100_000):
        perm = rng.permutation(comp)
        ks.append(int(((mov == 1) & (perm == 1)).sum()))
    pv = np.array([pk[k] for k in ks])
    out["P2_task_shuffle"] = {"observed_fisher_p": float(obs_p), "placebo_median_p": float(np.median(pv)),
                              "placebo_share_p_le_obs": float(np.mean(pv <= obs_p + 1e-15)), "n_draws": 100_000,
                              "placebo_failed_to_show_effect": bool(np.median(pv) >= 0.3)}
    # P3
    evs = [e for e in jl(f"{E15}/results/c1_events.jsonl") if e["gate_pass"]]
    fc = json.load(open(f"{E15}/predictions/forecasts.json"))["events"]
    land, nom, S = [], [], []
    for e in evs:
        f = fc[e["event_id"]]
        nb = Counter()
        for k, v in e["landing_counts"].items():
            if k in ("invalid", "unresolved", "no_code", "disputed") or k == e["banned"]:
                continue
            nb[k if k in f["S"] else "other"] += v
        if e["event_type"] == "modal":
            c = {k: v for k, v in nb.items() if k != "other"}
            L = max(sorted(c), key=lambda k: c[k]) if c else None
        else:
            n = sum(nb.values())
            ex = {k: nb.get(k, 0) / n - f["B_S"].get(k, 0.0) for k in f["S"]}
            L = max(f["S"], key=lambda k: (ex[k], -f["S"].index(k)))
        land.append(L)
        nom.append(e["top1"].get("ASSOCIATE"))
        S.append(f["S"])
    chance = float(sum(1 / len(s) for s in S))
    real = sum(int(a is not None and a == b) for a, b in zip(nom, land))
    perm_h, chance_h = [], []
    for _ in range(10_000):
        pl = [land[i] for i in rng.permutation(len(land))]
        perm_h.append(sum(int(a is not None and a == b) for a, b in zip(nom, pl)))
        cl = [s[rng.integers(len(s))] for s in S]
        chance_h.append(sum(int(a is not None and a == b) for a, b in zip(nom, cl)))
    out["P3_llama_landing_permutation"] = {
        "family": "ASSOCIATE", "real_hits": real, "expected_chance_hits": chance,
        "placebo_mean_hits_permuted_across_events": float(np.mean(perm_h)),
        "placebo_mean_hits_random_survivor": float(np.mean(chance_h)),
        "placebo_failed_to_show_effect": bool(abs(np.mean(chance_h) - chance) <= 1 and np.mean(perm_h) <= chance + 1)}
    # P4
    rows, seen = [], set()
    for r in jl(f"{E16}/data/samples.jsonl"):
        if r["uid"] in seen:
            continue
        seen.add(r["uid"])
        rows.append((r["task"], r["arm"], str(r.get("label")), r["template"]))
    defs = {"T03": "full_sort", "T05": "hash_map", "T06": "hash_set", "T10": "union_find", "T13": "sort_sweep"}
    within, total = 0, 0
    detail = {}
    for t, D in defs.items():
        a = [x for x in rows if x[0] == t and x[1] == "a" and x[2] not in NOATT and x[2] != D]
        cats = sorted({x[2] for x in rows if x[0] == t and x[2] not in NOATT and x[2] != D})
        for X in ("c", "d", "K0", "V1"):
            b = [x for x in rows if x[0] == t and x[1] == X and x[2] not in NOATT and x[2] != D]
            if not a or not b:
                continue
            pool = a + b
            perm = [pool[i] for i in rng.permutation(len(pool))]
            pa, pb = perm[:len(a)], perm[len(a):]
            vec = lambda rr: np.array([sum(1 for x in rr if x[2] == c) + 0.5 for c in cats])  # noqa: E731
            js = js2(vec(pb), vec(pa))
            null = []
            for _ in range(500):
                rs = [pa[i] for i in rng.integers(0, len(pa), len(pb))]
                null.append(js2(vec(rs), vec(pa)))
            q95 = float(np.quantile(null, 0.95))
            total += 1
            within += int(js <= q95 + 1e-12)
            detail[f"{t}:{X}"] = {"js_permuted": js, "null_q95": q95}
    out["P4_route_arm_permutation"] = {"n_within_null": within, "n": total, "detail": detail,
                                       "placebo_failed_to_show_effect": bool(within >= 0.8 * total)}
    out["n_placebos_failed_as_required"] = sum(int(v["placebo_failed_to_show_effect"]) for k, v in out.items()
                                               if k.startswith("P"))
    (WS / "audit" / "placebos.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"placebos: {out['n_placebos_failed_as_required']}/4 failed to show an effect as required")


if __name__ == "__main__":
    main()
