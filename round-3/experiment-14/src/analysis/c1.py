"""Frozen C1 analysis code (hash-committed in COMMIT #1 before any generation).

Scoring (plan 4.3): survivor set S = catalogue minus Y; raw forecast f over S plus 'other';
  q = 0.95 f + 0.05 Uniform(S);  p = 0.98 q + 0.02 delta_other;  logscore_F = mean over non-Y attempts of ln p_F(label);
  top1_F = argmax of raw f (ties keep all tied labels); an undefined forecast is Uniform(S).
Event: modal label = argmax of the non-Y landing; hit_F = |top1_F & modal| / (|top1_F| |modal|);
  disagreeing = the four top-1 sets are not all equal; gate_pass = avoidance >= 0.5 and n_nonY >= 20.
Advance rule (4.4): on each gated disagreeing event, F wins if logscore_F - max_{G != F} logscore_G >= 0.10;
  F advances if it wins >= 3 events.  With >= 10 such events: four two-sided paired Wilcoxon signed-rank tests
  (zeros dropped = zero_method 'wilcox'; exact for n <= 25) on per-event log-score differences
  SUBTRACT-ASSOCIATE, SUBTRACT-PROXIMITY, LADDER-ASSOCIATE, LADDER-PROXIMITY, Holm-corrected over the 4, with
  task-cluster bootstrap 95% CIs (10,000 resamples) of the mean differences.
C1-exposure (4.5): JS (base 2) between NAMED and veto non-Y landings against a cluster-bootstrap null
  (clusters = shown program x arm, at the observed sizes; 2,000 pairs).
"""

from __future__ import annotations

import math
import random
from collections import Counter

import numpy as np
from scipy.stats import wilcoxon

FAMILIES = ["SUBTRACT", "LADDER", "ASSOCIATE", "PROXIMITY"]
BAN_FREE = ("SUBTRACT", "LADDER")
SUBSTITUTION = ("ASSOCIATE", "PROXIMITY")
TEST_PAIRS = [("SUBTRACT", "ASSOCIATE"), ("SUBTRACT", "PROXIMITY"), ("LADDER", "ASSOCIATE"), ("LADDER", "PROXIMITY")]
OTHER = "other"
W_FORECAST = 0.95
W_OTHER = 0.02
WIN_MARGIN = 0.10
MIN_WINS = 3
MIN_EVENTS_TESTS = 10
MIN_EVENTS_RULE = 3
GATE_AVOID = 0.5
GATE_NONY = 20
ALPHA = 0.05
N_BOOT = 10_000
N_NULL = 2_000
EXACT_MAX_N = 25


# ------------------------------------------------------------------------------------------------- distributions
def normalise_label(label: str, y: str, survivors: list[str]) -> str | None:
    """None for 'invalid' (not an attempt); Y and survivors unchanged; anything else ('other', 'unknown') -> 'other'."""
    if label == "invalid":
        return None
    if label == y or label in survivors:
        return label
    return OTHER


def clean_forecast(f: dict | None, survivors: list[str]) -> dict:
    """Restrict a raw forecast to S + 'other' and renormalise; undefined / empty -> Uniform(S)."""
    s = list(survivors)
    if f:
        g = {k: float(v) for k, v in f.items() if (k in s or k == OTHER) and v > 0}
        tot = sum(g.values())
        if tot > 0:
            return {k: v / tot for k, v in g.items()}
    return {k: 1.0 / len(s) for k in s}


def smooth(f: dict | None, survivors: list[str]) -> dict:
    s = list(survivors)
    k = len(s)
    g = clean_forecast(f, s)
    q = {x: W_FORECAST * g.get(x, 0.0) + (1.0 - W_FORECAST) / k for x in s}
    q[OTHER] = W_FORECAST * g.get(OTHER, 0.0)
    p = {x: (1.0 - W_OTHER) * v for x, v in q.items()}
    p[OTHER] += W_OTHER
    return p


def log_score(f: dict | None, survivors: list[str], counts: dict) -> float:
    """Mean ln p(label) over the non-Y attempts given as label counts (labels already normalised)."""
    p = smooth(f, survivors)
    n = sum(counts.values())
    if n == 0:
        return float("nan")
    return sum(c * math.log(p[lab]) for lab, c in counts.items()) / n


def top1(f: dict | None, survivors: list[str]) -> list[str]:
    g = clean_forecast(f, survivors)
    mx = max(g.values())
    return sorted(k for k, v in g.items() if abs(v - mx) < 1e-12)


def modal(counts: dict, restrict: list[str] | None = None) -> list[str]:
    c = {k: v for k, v in counts.items() if v > 0 and (restrict is None or k in restrict)}
    if not c:
        return []
    mx = max(c.values())
    return sorted(k for k, v in c.items() if v == mx)


def hit(t1: list[str], mod: list[str]) -> float:
    if not t1 or not mod:
        return 0.0
    return len(set(t1) & set(mod)) / (len(t1) * len(mod))


def is_disagreeing(top1s: dict[str, list[str]]) -> bool:
    return len({tuple(sorted(v)) for v in top1s.values()}) > 1


def js_divergence(a: dict, b: dict) -> float:
    """Jensen-Shannon divergence, base 2, between two count / probability dicts."""
    keys = sorted(set(a) | set(b))
    pa = np.array([a.get(k, 0.0) for k in keys], dtype=float)
    pb = np.array([b.get(k, 0.0) for k in keys], dtype=float)
    if pa.sum() == 0 or pb.sum() == 0:
        return float("nan")
    pa, pb = pa / pa.sum(), pb / pb.sum()
    m = 0.5 * (pa + pb)

    def kl(x, y):
        nz = x > 0
        return float(np.sum(x[nz] * np.log2(x[nz] / y[nz])))

    return 0.5 * kl(pa, m) + 0.5 * kl(pb, m)


def hill_shannon(counts: dict) -> float:
    n = sum(counts.values())
    if n == 0:
        return float("nan")
    return math.exp(-sum((c / n) * math.log(c / n) for c in counts.values() if c > 0))


# ------------------------------------------------------------------------------------------------------ events
def gate(avoidance: float, n_nony: int) -> bool:
    return (not math.isnan(avoidance)) and avoidance >= GATE_AVOID and n_nony >= GATE_NONY


def score_event(survivors: list[str], landing: dict, forecasts: dict[str, dict | None]) -> dict:
    """landing: normalised non-Y label counts; forecasts: family -> raw distribution (None = undefined)."""
    mod = modal(landing)
    t1 = {f: top1(forecasts.get(f), survivors) for f in FAMILIES}
    return {"modal": mod,
            "top1": t1,
            "logscore": {f: log_score(forecasts.get(f), survivors, landing) for f in FAMILIES},
            "hit": {f: hit(t1[f], mod) for f in FAMILIES},
            "disagreeing": is_disagreeing(t1),
            "unaimed": bool(mod) and all(not (set(mod) & set(t1[f])) for f in FAMILIES)}


# ------------------------------------------------------------------------------------------------ advance rule
def advance_rule(events: list[dict], families: list[str] = FAMILIES) -> dict:
    wins = Counter()
    winners = []
    for ev in events:
        ls = ev["logscore"]
        w = None
        for f in families:
            others = [ls[g] for g in families if g != f]
            if ls[f] - max(others) >= WIN_MARGIN:
                wins[f] += 1
                w = f
        winners.append(w)
    adv = [f for f in families if wins[f] >= MIN_WINS]
    return {"n_events": len(events), "wins": {f: wins[f] for f in families}, "advancing": adv, "winners": winners}


def holm(pvals: list[float]) -> list[float]:
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvals[i]))
        adj[i] = running
    return adj


def wilcoxon_two_sided(d: list[float]) -> dict:
    nz = [x for x in d if x != 0]
    if not nz:
        return {"n": len(d), "n_nonzero": 0, "statistic": None, "p": 1.0, "method": "all-zero"}
    method = "exact" if len(nz) <= EXACT_MAX_N else "asymptotic"
    r = wilcoxon(nz, zero_method="wilcox", alternative="two-sided", method=method)
    return {"n": len(d), "n_nonzero": len(nz), "statistic": float(r.statistic), "p": float(r.pvalue), "method": method}


def cluster_bootstrap_mean(values: list[float], clusters: list[str], n_boot: int = N_BOOT, seed: int = 0) -> list[float]:
    """Percentile 95% CI of the mean, resampling clusters (tasks) with replacement."""
    by: dict[str, list[float]] = {}
    for v, c in zip(values, clusters):
        by.setdefault(c, []).append(v)
    keys = sorted(by)
    rng = random.Random(seed)
    means = []
    for _ in range(n_boot):
        vals = []
        for _k in keys:
            vals.extend(by[keys[rng.randrange(len(keys))]])
        means.append(sum(vals) / len(vals))
    return [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]


def paired_tests(events: list[dict], n_boot: int = N_BOOT, seed: int = 0) -> dict:
    if len(events) < MIN_EVENTS_TESTS:
        return {"run": False, "reason": f"{len(events)} < {MIN_EVENTS_TESTS} gated disagreeing events"}
    out = []
    for a, b in TEST_PAIRS:
        d = [ev["logscore"][a] - ev["logscore"][b] for ev in events]
        w = wilcoxon_two_sided(d)
        ci = cluster_bootstrap_mean(d, [ev["task"] for ev in events], n_boot=n_boot, seed=seed)
        out.append({"pair": f"{a}-{b}", "mean_diff": float(np.mean(d)), "median_diff": float(np.median(d)),
                    "ci95_task_cluster": ci, **w})
    adj = holm([r["p"] for r in out])
    for r, p in zip(out, adj):
        r["p_holm"] = p
        r["significant"] = p < ALPHA
        r["favours"] = (r["pair"].split("-")[0] if r["mean_diff"] > 0 else r["pair"].split("-")[1]) if r["significant"] else None
    return {"run": True, "tests": out}


def branch(rule: dict, tests: dict, unaimed_share: float, n_events: int) -> str:
    if n_events < MIN_EVENTS_RULE:
        return "UNDETERMINED"
    adv = set(rule["advancing"])
    adv_bf, adv_sub = adv & set(BAN_FREE), adv & set(SUBSTITUTION)
    fav = {r["favours"] for r in tests.get("tests", []) if r.get("significant")} if tests.get("run") else set()
    sig_bf, sig_sub = bool(fav & set(BAN_FREE)), bool(fav & set(SUBSTITUTION))
    if adv_bf and adv_sub:
        return "MIXED"
    if adv_bf and not sig_sub:
        return "SUBTRACTION/LADDER (" + "+".join(sorted(adv_bf)) + ")"
    if adv_sub and not sig_bf:
        return "SUBSTITUTION (" + "+".join(sorted(adv_sub)) + ")"
    if adv_bf or adv_sub:
        return "MIXED (advance contradicted by a Holm-significant test)"
    if unaimed_share >= 0.5:
        return "X-SPECIFIC BUT UNAIMED"
    return "NO FAMILY ADVANCES"


def run_c1(events: list[dict], n_boot: int = N_BOOT, seed: int = 0) -> dict:
    """events: dicts with task, gate_pass, disagreeing, logscore, unaimed.  Primary set = gated disagreeing."""
    sel = [e for e in events if e["gate_pass"] and e["disagreeing"]]
    rule = advance_rule(sel)
    tests = paired_tests(sel, n_boot=n_boot, seed=seed)
    unaimed = (sum(e["unaimed"] for e in sel) / len(sel)) if sel else float("nan")
    margins = []
    for e in sel:
        ls = e["logscore"]
        best = max(FAMILIES, key=lambda f: ls[f])
        margins.append({"Y": e.get("Y"), "task": e["task"], "best": best,
                        "margin": ls[best] - max(ls[g] for g in FAMILIES if g != best)})
    return {"n_events_total": len(events), "n_gated": sum(e["gate_pass"] for e in events),
            "n_gated_disagreeing": len(sel), "rule": rule, "tests": tests, "unaimed_share": unaimed,
            "branch": branch(rule, tests, unaimed if not math.isnan(unaimed) else 0.0, len(sel)),
            "margins": margins}


# ------------------------------------------------------------------------------------------------- C1-exposure
def js_null(clusters_a: list[list[str]], clusters_b: list[list[str]], n_null: int = N_NULL, seed: int = 0) -> dict:
    """Cluster-bootstrap null of JS(A, B): pool the clusters of both arms, draw |A| and |B| clusters with replacement.
    With fewer than 4 pooled clusters the null resamples programs instead (flagged)."""
    rng = random.Random(seed)
    pool = [c for c in clusters_a + clusters_b if c]
    level = "cluster"
    if len(pool) < 4:
        level = "program"
        progs = [x for c in pool for x in c]
        na, nb = sum(len(c) for c in clusters_a), sum(len(c) for c in clusters_b)
        vals = []
        for _ in range(n_null):
            a = Counter(progs[rng.randrange(len(progs))] for _ in range(na))
            b = Counter(progs[rng.randrange(len(progs))] for _ in range(nb))
            vals.append(js_divergence(a, b))
    else:
        na, nb = len([c for c in clusters_a if c]), len([c for c in clusters_b if c])
        vals = []
        for _ in range(n_null):
            a, b = Counter(), Counter()
            for _k in range(na):
                a.update(pool[rng.randrange(len(pool))])
            for _k in range(nb):
                b.update(pool[rng.randrange(len(pool))])
            vals.append(js_divergence(a, b))
    vals = [v for v in vals if not math.isnan(v)]
    return {"q95": float(np.quantile(vals, 0.95)) if vals else float("nan"), "level": level, "n": len(vals)}


def c1_exposure(items: list[dict], n_null: int = N_NULL, seed: int = 0) -> dict:
    """items: one per gated NAMED event with keys Y, task, survivors, coveto (modes), associate_top1, subtract_dist,
    proximity_top1, default, named_clusters / veto_clusters (lists of per-shown-program non-Y label lists)."""
    rows = []
    for it in items:
        s = it["survivors"]
        sub_mod = modal({k: v for k, v in (it["subtract_dist"] or {}).items() if k in s})
        assoc = it["associate_top1"]
        if not assoc or (set(assoc) & set(sub_mod)):
            continue  # the associate does not differ from SUBTRACT's modal survivor
        if set(assoc) & set(it["coveto"]) or it["default"] in it["coveto"]:
            continue
        allowed = [x for x in s if x not in it["coveto"]]
        a = Counter(x for c in it["named_clusters"] for x in c)
        b = Counter(x for c in it["veto_clusters"] for x in c)
        ma, mb = modal(a, allowed), modal(b, allowed)
        agree = bool(set(ma) & set(mb))
        js = js_divergence(a, b)
        nul = js_null(it["named_clusters"], it["veto_clusters"], n_null=n_null, seed=seed)
        disc = bool(set(ma) & (set(assoc) | set(it["proximity_top1"]))) and not bool(set(mb) & (set(assoc) | set(it["proximity_top1"])))
        rows.append({"task": it["task"], "Y": it["Y"], "named_modal": ma, "veto_modal": mb, "agree": agree, "js": js,
                     "js_null_q95": nul["q95"], "null_level": nul["level"], "js_consistent": js <= nul["q95"],
                     "disconfirming": disc, "associate": assoc, "subtract_modal": sub_mod})
    n = len(rows)
    if n == 0:
        return {"n_events": 0, "verdict": "EMPTY", "rows": []}
    ag = sum(r["agree"] for r in rows) / n
    di = sum(r["disconfirming"] for r in rows) / n
    if ag >= 2 / 3 and di >= 1 / 3:
        verdict = "CONFIRM+DISCONFIRM (mixed)"
    elif ag >= 2 / 3:
        verdict = "CONFIRM"
    elif di >= 1 / 3:
        verdict = "DISCONFIRM"
    else:
        verdict = "NEITHER"
    return {"n_events": n, "agreement_share": ag, "disconfirm_share": di,
            "js_consistent_share": sum(r["js_consistent"] for r in rows) / n, "verdict": verdict, "rows": rows}


# ---------------------------------------------------------------------------------------------------- placebos
def rescore(events: list[dict], new_forecasts: list[dict]) -> list[dict]:
    out = []
    for ev, fc in zip(events, new_forecasts):
        sc = score_event(ev["survivors"], ev["landing_counts_norm"], fc)
        out.append({**ev, **sc, "forecasts": fc})
    return out


def placebo_rotation(events: list[dict]) -> dict:
    """Rotate every family's forecast across Y within each task (event i gets event i+1's forecasts)."""
    by: dict[str, list[int]] = {}
    for i, ev in enumerate(events):
        by.setdefault(ev["task"], []).append(i)
    new = [None] * len(events)
    skipped = []
    for t, idx in by.items():
        if len(idx) < 2:
            skipped.append(t)
            for i in idx:
                new[i] = None
            continue
        for k, i in enumerate(idx):
            new[i] = events[idx[(k + 1) % len(idx)]]["forecasts"]
    keep = [i for i in range(len(events)) if new[i] is not None]
    res = run_c1(rescore([events[i] for i in keep], [new[i] for i in keep]), n_boot=2000)
    return {"skipped_single_event_tasks": skipped, "n_events": len(keep), "advancing": res["rule"]["advancing"],
            "wins": res["rule"]["wins"], "branch": res["branch"], "n_gated_disagreeing": res["n_gated_disagreeing"]}


def placebo_permutation(events: list[dict], n_draws: int = 200, seed: int = 0) -> dict:
    """Relabel each event's survivors by a random permutation (same permutation for all four families)."""
    rng = random.Random(seed)
    adv_any, counts = 0, Counter()
    for _ in range(n_draws):
        fcs = []
        for ev in events:
            s = list(ev["survivors"])
            perm = s[:]
            rng.shuffle(perm)
            mp = dict(zip(s, perm))
            fcs.append({f: ({mp.get(k, k): v for k, v in (fc or {}).items()} if fc else None)
                        for f, fc in ev["forecasts"].items()})
        sc = rescore(events, fcs)
        sel = [e for e in sc if e["gate_pass"] and e["disagreeing"]]
        r = advance_rule(sel)
        adv_any += bool(r["advancing"])
        counts.update(r["advancing"])
    return {"n_draws": n_draws, "share_any_family_advances": adv_any / n_draws,
            "share_by_family": {f: counts[f] / n_draws for f in FAMILIES}}
