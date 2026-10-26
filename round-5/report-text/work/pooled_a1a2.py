"""Pooled panel A + B view of Claims A1 and A2, computed for the iteration-5 report.

Neither confirmation panel ran the pooled test (both deferred it to the next round).
Inputs are read from the two panels' own result files; nothing is re-labelled here.
"""
import itertools, json, math, random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "."
A = json.load(open(ROOT / "experiment-25/src/results/a1.json"))
Aext = json.load(open(ROOT / "experiment-25/src/results/a1_with_extension.json"))
B = json.load(open(ROOT / "experiment-26/src/results/a1_panel.json"))
A2a = json.load(open(ROOT / "experiment-25/src/results/a2_assoc_corrected.json"))
A2b = json.load(open(ROOT / "experiment-26/src/results/a2_panel.json"))
A2a_committed = json.load(open(ROOT / "experiment-25/src/results/a2.json"))

def ranks(x):
    order = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x); i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and x[order[j + 1]] == x[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r

def spearman(x, y):
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den

def perm_p(x, y, n=200000, seed=0):
    obs = spearman(x, y); rng = random.Random(seed); y2 = list(y); hit = 0
    for _ in range(n):
        rng.shuffle(y2)
        if spearman(x, y2) >= obs - 1e-12:
            hit += 1
    return obs, (hit + 1) / (n + 1)

out = {}
units_a = A["units"]; beta_a = A["beta"]; E_a = A["E"]
units_ax = Aext["units"]; beta_ax = Aext["beta"]; E_ax = Aext["E"]
units_b = B["units"]; beta_b = B["beta"]; E_b = B["E"]
for name, (u, b, e) in {
    "primary_A6_plus_B7": (units_a + units_b, beta_a + beta_b, E_a + E_b),
    "with_extension_A8_plus_B7": (units_ax + units_b, beta_ax + beta_b, E_ax + E_b),
}.items():
    rho, p = perm_p(b, e)
    collapsed = [ei for bi, ei in zip(b, e) if bi < 0.05]
    diverse = [ei for bi, ei in zip(b, e) if bi >= 0.2]
    out[name] = {
        "units": u, "n": len(u), "spearman": rho, "perm_p_one_sided": p,
        "n_collapsed": len(collapsed), "collapsed_immovable": sum(1 for x in collapsed if x == 0),
        "n_diverse_beta_ge_0.2": len(diverse), "diverse_immovable": sum(1 for x in diverse if x == 0),
        "n_movable": sum(1 for x in e if x > 0),
    }

# A2 pooled: panel A (corrected association, plus committed uniform association) + panel B
ev = []
for e in A2a["events"]:
    ev.append({"unit": e["unit"], "hit": bool(e["hit"]), "chance": e["chance"],
               "base": e["log_scores"]["base"], "assoc": e["log_scores"]["assoc"], "prox": e["log_scores"]["prox"]})
comm = {e["unit"]: e["log_scores"]["assoc"] for e in A2a_committed["events"]}
for e in A2b["events"]:
    ev.append({"unit": e["unit"], "hit": e["hit"] == 1.0, "chance": e["chance"],
               "base": e["log_scores"]["BASE"], "assoc": e["log_scores"]["ASSOC"], "prox": e["log_scores"]["PROX"]})

def pb_tail(chances, h):
    dist = [1.0]
    for c in chances:
        new = [0.0] * (len(dist) + 1)
        for k, pr in enumerate(dist):
            new[k] += pr * (1 - c); new[k + 1] += pr * c
        dist = new
    return sum(dist[h:])

def wilcoxon_exact_greater(d):
    d = [x for x in d if x != 0]
    r = ranks([abs(x) for x in d]); n = len(d)
    w = sum(ri for ri, x in zip(r, d) if x > 0)
    cnt = tot = 0
    for signs in itertools.product([0, 1], repeat=n):
        ws = sum(ri for ri, s in zip(r, signs) if s)
        tot += 1; cnt += ws >= w - 1e-12
    return w, cnt / tot

hits = sum(e["hit"] for e in ev)
d_assoc = [e["base"] - e["assoc"] for e in ev]
d_assoc_comm = [(e["base"] - comm[e["unit"]]) if e["unit"] in comm else (e["base"] - e["assoc"]) for e in ev]
d_prox = [e["base"] - e["prox"] for e in ev]
out["A2_pooled"] = {
    "events": [e["unit"] for e in ev], "hits": hits, "n": len(ev),
    "expected_by_chance": sum(e["chance"] for e in ev),
    "poisson_binomial_p": pb_tail([e["chance"] for e in ev], hits),
    "base_minus_assoc_corrected": {"diffs": d_assoc, "mean": sum(d_assoc) / len(d_assoc),
                                   "wilcoxon_exact_one_sided": wilcoxon_exact_greater(d_assoc)},
    "base_minus_assoc_committed": {"diffs": d_assoc_comm, "mean": sum(d_assoc_comm) / len(d_assoc_comm),
                                   "wilcoxon_exact_one_sided": wilcoxon_exact_greater(d_assoc_comm)},
    "base_minus_prox": {"diffs": d_prox, "mean": sum(d_prox) / len(d_prox),
                        "wilcoxon_exact_one_sided": wilcoxon_exact_greater(d_prox)},
}
Path(__file__).with_name("pooled_a1a2.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
