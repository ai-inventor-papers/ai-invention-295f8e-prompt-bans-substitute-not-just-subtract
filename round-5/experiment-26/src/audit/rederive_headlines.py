#!/usr/bin/env python3
"""Short, separate re-derivation of the HEADLINE numbers from the raw rows (data/samples_raw.jsonl, data/labels.jsonl,
data/judge_labels.jsonl) through a different code path than analysis/a1a2.py: its own label join, escape rule, scipy's
spearmanr inside a brute-force permutation test, and a brute-force Poisson-binomial enumeration. Placebos (shuffled
beta, shuffled r_u, constant beta) must fail. Writes results/rederive_headlines.json."""

import hashlib
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

R = Path(__file__).resolve().parents[1]
jl = lambda p: [json.loads(l) for l in (R / p).read_text().splitlines() if l.strip()]  # noqa: E731
key = lambda r: f"{r['unit']}|{r['template']}|{r['arm']}|{r['slot']}|{r['model_tag']}"  # noqa: E731
raw = {key(r): r for r in jl("data/samples_raw.jsonl") if not r.get("engine_check")}
jud = {r["key"]: r.get("label") for r in jl("data/judge_labels.jsonl")}
units = [f"B{i}" for i in range(1, 8)]
rows = defaultdict(list)
for l in jl("data/labels.jsonl"):
    r = raw.get(l["key"])
    if r is None or r["family"] == "ASSOC" or l["unit"] not in units:
        continue
    cat = set(json.loads((R / "units" / l["unit"] / "catalogue_frozen.json").read_text())["catalogue"])
    lab = l.get("label") or jud.get(l["key"]) or "disputed"
    lab = lab if lab in cat | {"other", "invalid", "disputed"} else "other"
    rows[l["unit"]].append((r["arm"], r["family"], r["slot"], lab, bool(l.get("passed")), lab in cat))


def cell(rr, d):
    v = [x for x in rr if x[3] not in ("invalid", "disputed")]
    off = sum(1 for x in v if x[5] and x[3] != d)
    return off, len(v), sum(x[4] for x in rr) / max(len(rr), 1)


out, beta, E, PN, events = {}, [], [], [], []
for u in units:
    U = rows[u]
    tw = [x for x in U if x[0] == "TWIN" and x[2] < 10]
    c = Counter(x[3] for x in tw if x[4] and x[3] not in ("invalid", "disputed"))
    d = c.most_common(1)[0][0]
    base = [x for x in U if x[0] == "BASE" and x[2] < 40]
    bc = [x[3] for x in base if x[4] and x[3] != "disputed"]
    src = bc if len(bc) >= 20 else [x[3] for x in base if x[3] not in ("invalid", "disputed")]
    b = sum(l != d for l in src) / len(src)
    nd = Counter(l for l in src if l != d and l not in ("other", "invalid", "disputed"))
    ru = nd.most_common(1)[0][0]
    k0, n0, p_tw = cell(tw, d)
    sh_tw, p0 = k0 / n0, (k0 + 0.5) / (n0 + 1)
    conf, land = 0, Counter()
    for a in (1.0, 2.0):
        for k in range(8):
            s = int(hashlib.sha256(f"iter5|panelB|{u}|dir|{k}".encode()).hexdigest()[:8], 16)
            rr = [x for x in U if x[0] == f"ESC_d{s}_a{a}"]
            k1, n1, p1 = cell([x for x in rr if x[2] < 2], d)
            if not (n1 and k1 / n1 - sh_tw >= 0.2 - 1e-12 and p1 >= 0.8 * p_tw - 1e-12):
                continue
            r30 = [x for x in rr if x[2] < 6]
            k3, n3, p3 = cell(r30, d)
            if len(r30) >= 30 and k3 / n3 - sh_tw >= 0.2 - 1e-12 and p3 >= 0.8 * p_tw - 1e-12 and \
                    stats.binomtest(k3, n3, p0, alternative="greater").pvalue < 0.05:
                conf += 1
                land.update(x[3] for x in r30 if x[4] and x[5] and x[3] != d)
    e = conf / 16
    pn = []
    for a in (1.0, 2.0):
        k2, n2, p2 = cell([x for x in U if x[0] == f"PN_a{a}" and x[2] < 10], d)
        if n2 and p2 >= 0.8 * p_tw - 1e-12:
            pn.append(k2 / n2 - sh_tw)
    pnx = max(pn) if pn else 0.0
    K = len(json.loads((R / "units" / u / "catalogue_frozen.json").read_text())["catalogue"])
    out[u] = {"default": d, "beta": b, "r_u": ru, "E": e, "PN_excess": pnx, "landing": land.most_common(1)[0][0]
              if land else None}
    beta.append(b), E.append(e), PN.append(pnx)
    if e > 0 and b >= 0.05 and land:
        events.append((u, ru, land.most_common(1)[0][0], 1 / (K - 1)))


def perm_test(x, y):
    r0 = stats.spearmanr(x, y).statistic
    rs = [stats.spearmanr(x, [y[i] for i in p]).statistic for p in itertools.permutations(range(len(y)))]
    return float(r0), float(np.mean([r >= r0 - 1e-12 for r in rs]))


def pb_sf(h, ps):
    return float(sum(np.prod([p if b else 1 - p for p, b in zip(ps, bits)])
                     for bits in itertools.product([0, 1], repeat=len(ps)) if sum(bits) >= h))


rho, p = perm_test(beta, E)
rho_pn, p_pn = perm_test(beta, PN)
hits = sum(ru == land for _, ru, land, _ in events)
p_a2 = pb_sf(hits, [c for *_, c in events])
rng = np.random.default_rng(2026)
plac = [perm_test(list(rng.permutation(beta)), E)[1] for _ in range(100)]
plac_hits = [sum(ru == events[j][2] for (_, ru, _, _), j in zip(events, perm))
             for perm in itertools.permutations(range(len(events)))]
const = stats.spearmanr([0.3] * len(E), E).statistic
rep1, rep2 = (json.loads((R / "results" / f).read_text()) for f in ("a1_panel.json", "a2_panel.json"))
chk = {"A1_rho": (rep1["primary"]["rho"], rho), "A1_p": (rep1["primary"]["p"], p),
       "PN_rho": (rep1["secondary_PN"]["rho"], rho_pn), "PN_p": (rep1["secondary_PN"]["p"], p_pn),
       "A2_hits": (rep2["top1"]["hits"], float(hits)), "A2_p": (rep2["top1"]["poisson_binomial_p"], p_a2)}
res = {"units": out, "checks": {k: {"reported": a, "rederived": b, "match": abs(a - b) < 1e-9} for k, (a, b) in chk.items()},
       "placebo_shuffled_beta": {"n": len(plac), "share_p_lt_0.05": float(np.mean([q < 0.05 for q in plac])),
                                 "median_p": float(np.median(plac))},
       "placebo_shuffled_r_u": {"n_perms": len(plac_hits), "mean_hits": float(np.mean(plac_hits)),
                                "share_ge_observed": float(np.mean([h >= hits for h in plac_hits]))},
       "placebo_constant_beta_rho": None if not np.isfinite(const) else float(const)}
uo = {x["unit"]: x for x in json.loads((R / "results" / "unit_outcomes.json").read_text())["units"]}
for u in units:
    pr = json.loads((R / "predictions" / "units" / f"{u}.json").read_text())
    for name, a, b in (("default", pr["default"], out[u]["default"]), ("beta", pr["base"]["beta_u"], out[u]["beta"]),
                       ("r_u", pr["base"]["r_u"], out[u]["r_u"]), ("E", uo[u]["E_u"], out[u]["E"]),
                       ("PN_excess", uo[u]["PN_excess_u"], out[u]["PN_excess"]),
                       ("landing", uo[u]["push_landing"], out[u]["landing"])):
        same = a == b if not isinstance(a, float) else abs(a - b) < 1e-9
        res["checks"][f"{u}_{name}"] = {"reported": a, "rederived": b, "match": same}
res["all_match"] = all(v["match"] for v in res["checks"].values())
(R / "results" / "rederive_headlines.json").write_text(json.dumps(res, indent=1, default=str))
print(json.dumps({k: v for k, v in res.items() if k != "units"}, indent=1, default=str))

# ---- extended descriptive views (panel + parents, clustered) and the screen view, same independent path
ext_units = units + [p.stem for p in sorted((R / "predictions" / "units").glob("[PV]_*.json"))]
rows2 = defaultdict(list)
for l in jl("data/labels.jsonl"):
    r = raw.get(l["key"])
    if r is None or r["family"] == "ASSOC" or l["unit"] not in ext_units or l["unit"] in units:
        continue
    cat = set(json.loads((R / "units" / l["unit"] / "catalogue_frozen.json").read_text())["catalogue"])
    lab = l.get("label") or jud.get(l["key"]) or "disputed"
    lab = lab if lab in cat | {"other", "invalid", "disputed"} else "other"
    rows2[l["unit"]].append((r["arm"], r["family"], r["slot"], lab, bool(l.get("passed")), lab in cat))
vals = {u: (out[u]["beta"], out[u]["E"]) for u in units}
for u, U in rows2.items():
    tw = [x for x in U if x[0] == "TWIN" and x[2] < 10]
    c = Counter(x[3] for x in tw if x[4] and x[3] not in ("invalid", "disputed"))
    if not c or c.most_common(1)[0][1] / sum(c.values()) < 0.6 or c.most_common(1)[0][0] in ("other",):
        continue
    d = c.most_common(1)[0][0]
    base = [x for x in U if x[0] == "BASE" and x[2] < 40]
    bc = [x[3] for x in base if x[4] and x[3] != "disputed"]
    src = bc if len(bc) >= 20 else [x[3] for x in base if x[3] not in ("invalid", "disputed")]
    k0, n0, p_tw = cell(tw, d)
    sh_tw, p0 = k0 / n0, (k0 + 0.5) / (n0 + 1)
    conf = 0
    t = u[2:]
    for a in (1.0, 2.0):
        for k in range(8):
            s = int(hashlib.sha256(f"iter5|panelB|{t}|dir|{k}".encode()).hexdigest()[:8], 16)
            rr = [x for x in U if x[0] == f"ESC_d{s}_a{a}"]
            k1, n1, p1 = cell([x for x in rr if x[2] < 2], d)
            if not (n1 and k1 / n1 - sh_tw >= 0.2 - 1e-12 and p1 >= 0.8 * p_tw - 1e-12):
                continue
            k3, n3, p3 = cell([x for x in rr if x[2] < 6], d)
            if len([x for x in rr if x[2] < 6]) >= 30 and k3 / n3 - sh_tw >= 0.2 - 1e-12 and \
                    p3 >= 0.8 * p_tw - 1e-12 and stats.binomtest(k3, n3, p0, alternative="greater").pvalue < 0.05:
                conf += 1
    vals[u] = (sum(l != d for l in src) / len(src), conf / 16)
newpar = [u for u in vals if not u.startswith("V_")]
ext = json.loads((R / "results" / "a1_extended.json").read_text())
r_np = stats.spearmanr([vals[u][0] for u in newpar], [vals[u][1] for u in newpar]).statistic
r_all = stats.spearmanr([v[0] for v in vals.values()], [v[1] for v in vals.values()]).statistic
sv = json.loads((R / "results" / "screen_view.json").read_text())
snap = json.loads((R / "inputs" / "exp24_base_repertoire_snapshot.json").read_text())["per_task"]
esc = json.loads((R / "vendor" / "exp22" / "escape.json").read_text())
tasks = [t for t in snap if t in esc and snap[t].get("beta") is not None]
r_sv = stats.spearmanr([snap[t]["beta"] for t in tasks],
                       [np.mean([esc[t]["E_t"][a]["E_t"] for a in esc[t]["E_t"]]) for t in tasks]).statistic
res["checks"].update({
    "panel_plus_parents_rho": {"reported": ext["panel_plus_parents"]["rho"], "rederived": float(r_np),
                               "match": bool(abs(ext["panel_plus_parents"]["rho"] - r_np) < 1e-9)},
    "clustered_rho": {"reported": ext["clustered_all"]["rho"], "rederived": float(r_all),
                      "match": bool(abs(ext["clustered_all"]["rho"] - r_all) < 1e-9)},
    "screen_view_rho": {"reported": sv["spearman"]["rho"], "rederived": float(r_sv),
                        "match": bool(abs(sv["spearman"]["rho"] - r_sv) < 1e-9)}})
res["extended_units_rederived"] = {u: {"beta": v[0], "E": v[1]} for u, v in vals.items()}
res["all_match"] = all(v["match"] for v in res["checks"].values())
(R / "results" / "rederive_headlines.json").write_text(json.dumps(res, indent=1, default=str))
print("extended:", {k: res["checks"][k] for k in ("panel_plus_parents_rho", "clustered_rho", "screen_view_rho")},
      "all_match", res["all_match"])
