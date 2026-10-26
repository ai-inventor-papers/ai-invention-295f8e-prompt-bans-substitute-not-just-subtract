#!/usr/bin/env python3
"""Independent re-derivation (plan T5), written separately from analysis/ and src/labels_view.py: recomputes every
headline number from the raw rows (data/samples_raw.jsonl, data/labels.jsonl, data/judge_labels.jsonl) and the frozen
catalogues/defaults, then compares with results/unit_outcomes.json and predictions/units/*.json (0 mismatches is the
bar). Placebos: shuffled beta (mean rho ~ 0), shuffled arm labels (twin vs push rows permuted within a unit), and
twin-as-push (the twin's own rows scored as every push cell -> E = 0). Writes results/rederive.json."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]


def jl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def seed(u: str, k: int) -> int:
    t = u[2:] if u[:2] in ("P_", "V_") else u
    return int(hashlib.sha256(f"iter5|panelB|{t}|dir|{k}".encode()).hexdigest()[:8], 16)


def load() -> dict[str, list[dict]]:
    raw = {f"{r['unit']}|{r['template']}|{r['arm']}|{r['slot']}|{r['model_tag']}": r
           for r in jl(ROOT / "data" / "samples_raw.jsonl") if not r.get("engine_check")}
    judged = {r["key"]: r for r in jl(ROOT / "data" / "judge_labels.jsonl")}
    out: dict[str, list[dict]] = defaultdict(list)
    cats = {}
    for l in jl(ROOT / "data" / "labels.jsonl"):
        r = raw.get(l["key"])
        if r is None or r["family"] == "ASSOC":
            continue
        u = l["unit"]
        if u not in cats:
            p = ROOT / "units" / u / "catalogue_frozen.json"
            cats[u] = set(json.loads(p.read_text())["catalogue"]) if p.exists() else set()
        lab = l.get("label")
        if lab is None:
            j = judged.get(l["key"])
            lab = j["label"] if (j and j.get("label")) else "disputed"
        if lab not in cats[u] and lab not in ("other", "invalid", "disputed"):
            lab = "other"
        out[u].append({"arm": r["arm"], "family": r["family"], "slot": r["slot"], "template": r["template"],
                       "label": lab, "passed": bool(l.get("passed")), "model_tag": r["model_tag"]})
    return out, cats


def cell(rows, cat, d):
    valid = [r for r in rows if r["label"] not in ("invalid", "disputed")]
    off = sum(1 for r in valid if r["label"] in cat and r["label"] != d)
    return {"n": len(rows), "nv": len(valid), "off": off, "share": off / len(valid) if valid else None,
            "pass": sum(r["passed"] for r in rows) / len(rows) if rows else None}


def escape_E(rows, cat, d, u, twin_rows=None, push_by_arm=None):
    tw = twin_rows if twin_rows is not None else [r for r in rows if r["arm"] == "TWIN" and r["slot"] < 10]
    T = cell(tw, cat, d)
    p0 = (T["off"] + 0.5) / (T["nv"] + 1)
    conf = {1.0: 0, 2.0: 0}
    land = Counter()
    by = push_by_arm or defaultdict(list)
    if push_by_arm is None:
        for r in rows:
            if r["family"] == "ESC":
                by[r["arm"]].append(r)
    for a in (1.0, 2.0):
        for k in range(8):
            rr = by.get(f"ESC_d{seed(u, k)}_a{a}", [])
            s1 = cell([r for r in rr if r["slot"] in (0, 1)], cat, d)
            if s1["n"] < 10 or s1["share"] is None or T["share"] is None:
                continue
            if not (s1["share"] - T["share"] >= 0.2 - 1e-12 and s1["pass"] >= 0.8 * T["pass"] - 1e-12):
                continue
            s30r = [r for r in rr if r["slot"] in range(6)]
            s30 = cell(s30r, cat, d)
            if s30["n"] < 30 or s30["nv"] == 0:
                continue
            p = stats.binomtest(s30["off"], s30["nv"], p0, alternative="greater").pvalue
            if s30["share"] - T["share"] >= 0.2 - 1e-12 and p < 0.05 and s30["pass"] >= 0.8 * T["pass"] - 1e-12:
                conf[a] += 1
                land.update(r["label"] for r in s30r if r["passed"] and r["label"] in cat and r["label"] != d)
    E = {a: conf[a] / 8 for a in conf}
    return {"E1": E[1.0], "E2": E[2.0], "E": (E[1.0] + E[2.0]) / 2,
            "landing": land.most_common(1)[0][0] if land else None}


def main() -> None:
    rows, cats = load()
    preds = {p.stem: json.loads(p.read_text()) for p in (ROOT / "predictions" / "units").glob("*.json")}
    uo = ROOT / "results" / "unit_outcomes.json"
    outcomes = {x["unit"]: x for x in json.loads(uo.read_text())["units"]} if uo.exists() else {}
    res = {"units": {}, "mismatches": []}
    betas, Es, names = [], [], []
    rng = np.random.default_rng(99)
    for u, pr in sorted(preds.items()):
        R, cat = rows.get(u, []), cats.get(u, set())
        tw = [r for r in R if r["arm"] == "TWIN" and r["slot"] < 10]
        corr = Counter(r["label"] for r in tw if r["passed"] and r["label"] not in ("invalid", "disputed"))
        nc = sum(corr.values())
        modal = corr.most_common(1)[0] if corr else (None, 0)
        d = modal[0] if (modal[0] in cat and nc and modal[1] / nc >= 0.6 and len(tw) >= 50) else "NO_DEFAULT"
        base = [r for r in R if r["arm"] == "BASE" and r["slot"] < 40]
        bc = [r["label"] for r in base if r["passed"] and r["label"] != "disputed"]
        ba = [r["label"] for r in base if r["label"] not in ("invalid", "disputed")]
        src = ba if len(bc) < 20 else bc
        beta = sum(l != d for l in src) / len(src) if (src and d != "NO_DEFAULT") else None
        nd = Counter(l for l in src if l in cat and l != d)
        top = nd.most_common()
        r_u = (top[0][0] if len(top) == 1 or top[0][1] != top[1][1] else "tie") if top else None
        e = escape_E(R, cat, d, u) if d != "NO_DEFAULT" else None
        rec = {"default": d, "beta": beta, "r_u": r_u, **(e or {})}
        res["units"][u] = rec
        chk = [("default", pr["default"], d), ("beta", pr["base"]["beta_u"], beta), ("r_u", pr["base"]["r_u"], r_u)]
        if u in outcomes and e is not None:
            o = outcomes[u]
            chk += [("E_u", o["E_u"], e["E"]), ("E_alpha1", o["E_by_alpha"].get("1.0"), e["E1"]),
                    ("E_alpha2", o["E_by_alpha"].get("2.0"), e["E2"]), ("push_landing", o["push_landing"], e["landing"])]
        for name, a, b in chk:
            same = (a == b) if not isinstance(a, float) else (b is not None and abs(a - b) < 1e-9)
            if not same:
                res["mismatches"].append({"unit": u, "quantity": name, "reported": a, "rederived": b})
        if u.startswith("B") and beta is not None and e is not None:
            betas.append(beta)
            Es.append(e["E"])
            names.append(u)
            # placebo: twin-as-push
            push = defaultdict(list)
            for a in (1.0, 2.0):
                for k in range(8):
                    push[f"ESC_d{seed(u, k)}_a{a}"] = [dict(r) for r in tw if r["slot"] < 6]
            rec["placebo_twin_as_push_E"] = escape_E(R, cat, d, u, push_by_arm=push)["E"]
            # placebo: shuffled arm labels (twin k 0-9 + every ESC row pooled and re-split at random)
            esc = [r for r in R if r["family"] == "ESC"]
            pool = tw + esc
            Esh = []
            for _ in range(20):
                perm = list(rng.permutation(len(pool)))
                new_tw = [pool[i] for i in perm[:len(tw)]]
                rest = [pool[i] for i in perm[len(tw):]]
                by = defaultdict(list)
                for r0, r1 in zip(rest, esc):
                    by[r1["arm"]].append({**r0, "slot": r1["slot"], "arm": r1["arm"]})
                Esh.append(escape_E(R, cat, d, u, twin_rows=new_tw, push_by_arm=by)["E"])
            rec["placebo_shuffled_arms_mean_E"] = float(np.mean(Esh))
    if len(betas) >= 3:
        rho = stats.spearmanr(betas, Es).statistic
        sh = [stats.spearmanr(rng.permutation(betas), Es).statistic for _ in range(1000)]
        sh = [x for x in sh if np.isfinite(x)]
        res["A1_rederived"] = {"units": names, "rho": float(rho) if np.isfinite(rho) else None,
                               "placebo_shuffled_beta_mean_rho": float(np.mean(sh)) if sh else None}
        a1 = ROOT / "results" / "a1_panel.json"
        if a1.exists():
            rep = json.loads(a1.read_text())["primary"]["rho"]
            r_ = res["A1_rederived"]["rho"]
            if not ((rep is None and r_ is None) or (rep is not None and r_ is not None and abs(rep - r_) < 1e-9)):
                res["mismatches"].append({"unit": "panel", "quantity": "rho_A1", "reported": rep, "rederived": r_})
    res["n_mismatches"] = len(res["mismatches"])
    res["placebo_twin_as_push_all_zero"] = all(v.get("placebo_twin_as_push_E", 0) == 0 for v in res["units"].values())
    (ROOT / "results" / "rederive.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: v for k, v in res.items() if k != "units"}, indent=1, default=str))
    sys.exit(0)


if __name__ == "__main__":
    main()
