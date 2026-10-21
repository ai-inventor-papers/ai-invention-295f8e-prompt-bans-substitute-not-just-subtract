"""(0b) Landing by route for the five gated tasks, and the exp16 pooled route fractions (plain and catalogue-only,
with and without residue-gated events)."""

from __future__ import annotations

import json
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
from loguru import logger

from src.labels import catalogue, default_of
from src.paths import WS, cite, p
from src.stats import js_div2, jackknife_ci

DATA, RES, TAB = WS / "data", WS / "results", WS / "tables"
ROUTE_TASKS = ["T03", "T05", "T06", "T10", "T13"]
ROUTE_ARMS = ["a", "c", "d", "K0", "V1"]
EXCL16 = ("invalid", "no_code", "disputed")


def _jsonl(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def survivors(t: str) -> list[str]:
    return [m for m in catalogue(t) if m != default_of(t)] + ["other"]


def dist_vec(counts: dict, cats: list[str], pseudo: float = 0.5) -> np.ndarray:
    return np.array([counts.get(c, 0) + pseudo for c in cats], float)


def landing_null(rows_a: list[dict], t: str, n: int, cats: list[str], n_rep: int = 2000, seed: int = 20261021) -> float:
    D = default_of(t)
    nond = [r for r in rows_a if r["label"] not in EXCL16 and r["label"] != D]
    byw = defaultdict(list)
    for r in nond:
        byw[r["template"]].append(r["label"])
    ws = sorted(byw)
    full = dist_vec(Counter(r["label"] for r in nond), cats)
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_rep):
        labs = [byw[w][rng.integers(len(byw[w]))] for w in (ws[i] for i in rng.integers(0, len(ws), n))]
        vals.append(js_div2(dist_vec(Counter(labs), cats), full))
    return float(np.quantile(vals, 0.95))


def load_exp16_rows() -> list[dict]:
    out, seen = [], set()
    for r in _jsonl(p("exp16", "data/samples.jsonl")):
        if r["uid"] in seen:
            continue
        seen.add(r["uid"])
        out.append({"task": r["task"], "arm": r["arm"], "template": r["template"], "k": int(r["k"]),
                    "label": "no_code" if r.get("label") is None else str(r["label"]),
                    "passed": r.get("passed") is True or str(r.get("passed")) == "True"})
    return out


def association_modal() -> dict[str, tuple[str, float]]:
    out = {}
    rows = _jsonl(p("exp11", "data/association.jsonl"))
    for t in ROUTE_TASKS + ["T04", "T08", "T11", "T14", "R1", "R3", "R6"]:
        D = default_of(t)
        ans = [r.get("mapped") for r in rows if r["task"] == t and r["X"] == D]
        c = Counter(a for a in ans if a)
        if c:
            m, n = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0]
            out[t] = (m, n / len(ans))
    return out


def frlp_runner_up() -> dict[str, tuple[str, float, float]]:
    """Highest-L_corr non-default mode in exp11 baseline FRLP cells (main variant, all halves); also its mass."""
    rows = [r for r in _jsonl(p("exp11", "data/frlp_cells.jsonl"))
            if r.get("condition") == "baseline" and r.get("variant") == "main" and r.get("half") == "all"]
    out = {}
    for t in sorted({r["task"] for r in rows}):
        D = default_of(t)
        cells = {r["algorithm"]: float(r["L_corr"]) for r in rows if r["task"] == t and r["L_corr"] is not None
                 and np.isfinite(float(r["L_corr"]))}
        if not cells:
            continue
        nd = {k: v for k, v in cells.items() if k != D}
        best = max(sorted(nd), key=lambda k: nd[k])
        m = max(cells.values())
        z = sum(np.exp(v - m) for v in cells.values())
        out[t] = (best, float(nd[best]), float(np.exp(nd[best] - m) / z))
    return out


def proximity_top1() -> dict[str, str]:
    pr = json.loads(p("exp13", "predictions/proximity.json").read_text())["tasks"]
    out = {}
    for t, d in pr.items():
        if d.get("nominee"):
            out[t] = d["nominee"]
            continue
        sv = {k: v for k, v in d["survivors"].items() if v.get("defined")}
        if sv:
            out[t] = min(sorted(sv), key=lambda k: (sv[k]["median"], sv[k].get("mean", 0)))
    return out


def route_landing_table(rows: list[dict], push_top1: dict[str, str | None]) -> tuple[pd.DataFrame, dict]:
    rec_lbr = json.loads(p("exp16", "results/landing_by_route.json").read_text())
    assoc, frlp, prox = association_modal(), frlp_runner_up(), proximity_top1()
    g = defaultdict(list)
    for r in rows:
        g[(r["task"], r["arm"])].append(r)
    recs, checks = [], []
    for t in ROUTE_TASKS:
        D = default_of(t)
        cats = survivors(t)
        ra = g[(t, "a")]
        ca = Counter(r["label"] for r in ra if r["label"] not in EXCL16 and r["label"] != D)
        for arm in ROUTE_ARMS:
            rx = g[(t, arm)]
            cx = Counter(r["label"] for r in rx if r["label"] not in EXCL16 and r["label"] != D)
            cc = Counter(r["label"] for r in rx if r["passed"] and r["label"] != D and r["label"] not in EXCL16)
            modal = sorted(cx.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if cx else None
            rec = {"task": t, "arm": arm, "default": D, "n_rows": len(rx),
                   "n_attempted": sum(r["label"] not in EXCL16 for r in rx),
                   "n_nondefault_attempted": sum(cx.values()),
                   "nondefault_attempted_composition": json.dumps(dict(cx.most_common())),
                   "nondefault_correct_composition": json.dumps(dict(cc.most_common())), "modal_nondefault": modal,
                   "modal_nondefault_excl_other": (sorted(((k, v) for k, v in cx.items() if k != "other"),
                                                          key=lambda kv: (-kv[1], kv[0])) or [(None, 0)])[0][0]}
            if arm != "a" and cx and ca:
                js = js_div2(dist_vec(cx, cats), dist_vec(ca, cats))
                q95 = landing_null(ra, t, sum(cx.values()), cats)
                recd = rec_lbr.get(t, {}).get(arm, {})
                rec.update({"JS_vs_a": js, "null_q95_rederived": q95, "within_null_rederived": bool(js < q95),
                            "JS_vs_a_recorded": recd.get("JS_vs_a"), "null_q95_recorded": recd.get("null_q95"),
                            "within_null_recorded": recd.get("within_null"),
                            "JS_match_1e-6": (abs(js - recd["JS_vs_a"]) < 1e-6) if recd.get("JS_vs_a") is not None else None})
            rec["association_modal"] = assoc.get(t, (None, None))[0]
            rec["frlp_runner_up"] = frlp.get(t, (None,))[0]
            rec["proximity_top1"] = prox.get(t)
            rec["push_top1"] = push_top1.get(t)
            for col in ("association_modal", "frlp_runner_up", "proximity_top1", "push_top1"):
                rec[f"hit_{col}"] = (rec[col] is not None and rec["modal_nondefault_excl_other"] == rec[col])
            recs.append(rec)
    df = pd.DataFrame(recs)
    # readings to verify
    def comp(t, arm):
        return json.loads(df[(df.task == t) & (df.arm == arm)].iloc[0].nondefault_attempted_composition)

    def allc(t, arm):
        rx = g[(t, arm)]
        return dict(Counter(r["label"] for r in rx if r["label"] not in EXCL16).most_common())

    readings = {
        "T10_a": (allc("T10", "a"), {"bfs": 75, "dfs": 25}), "T10_c": (allc("T10", "c"), {"dfs": 56, "bfs": 44}),
        "T10_d": (allc("T10", "d"), {"dfs": 70, "bfs": 10}), "T10_K0": (allc("T10", "K0"), {"dfs": 57, "bfs": 43}),
        "T03_d": (comp("T03", "d"), {"quickselect": 74, "size_k_heap": 1}),
        "T03_a": (comp("T03", "a"), {"quickselect": 70, "size_k_heap": 28}),
        "T06_K0": (comp("T06", "K0"), "floyd 3 of 5"),
    }
    for k, (got, exp) in readings.items():
        if isinstance(exp, dict):
            ok = all(got.get(l) == v for l, v in exp.items())
        else:
            ok = got.get("floyd") == 3 and sum(got.values()) == 5
        checks.append({"reading": k, "expected": exp, "recomputed": got, "match": bool(ok)})
    return df, {"readings": checks, "assoc": assoc, "frlp": frlp, "proximity": prox}


# ------------------------------------------------------------------------------------------------ route fractions
def slot_counts(rows: list[dict], tasks: list[str], mode: str) -> dict[str, dict[str, tuple[int, int]]]:
    """task -> arm -> (n_'banned', n_attempted). plain: banned = default; cat: banned = not a non-default
    catalogue mode (default or residue such as 'other')."""
    out: dict = {}
    for t in tasks:
        D = default_of(t)
        cat = set(catalogue(t))
        out[t] = {}
        for arm in ("a", "b", "c", "d", "K0"):
            rr = [r for r in rows if r["task"] == t and r["arm"] == arm and r["label"] not in EXCL16]
            if mode == "plain":
                nb = sum(r["label"] == D for r in rr)
            else:
                nb = sum(not (r["label"] in cat and r["label"] != D) for r in rr)
            out[t][arm] = (nb, len(rr))
    return out


def fractions(sc: dict, tasks: list[str]) -> dict[str, float]:
    s = {t: {a: (sc[t][a][0] / sc[t][a][1] if sc[t][a][1] else np.nan) for a in sc[t]} for t in tasks}
    den = sum(s[t]["b"] - s[t]["a"] for t in tasks)
    fp = sum(s[t]["b"] - s[t]["c"] for t in tasks) / den
    fd = sum(s[t]["b"] - s[t]["d"] for t in tasks) / den
    fk = sum(s[t]["b"] - s[t]["K0"] for t in tasks) / den
    return {"F_prompt": fp, "F_direct": fd, "I": 1 - fp - fd, "F_K0": fk}


def route_fraction_block(rows: list[dict], tasks: list[str], mode: str) -> dict:
    sc = slot_counts(rows, tasks, mode)
    pt = fractions(sc, tasks)
    out = {"tasks": tasks, "mode": mode, "point": pt, "per_task": {}}
    for k in ("F_prompt", "F_direct", "I", "F_K0"):
        jv = [fractions(sc, [u for u in tasks if u != t])[k] for t in tasks]
        out.setdefault("jackknife", {})[k] = {"ci95": jackknife_ci(pt[k], jv), "values": jv}
    for t in tasks:
        s = {a: sc[t][a][0] / sc[t][a][1] for a in sc[t] if sc[t][a][1]}
        den = s["b"] - s["a"]
        out["per_task"][t] = {"s": s, "F_prompt": (s["b"] - s["c"]) / den if den else None,
                              "F_direct": (s["b"] - s["d"]) / den if den else None,
                              "counts": {a: list(v) for a, v in sc[t].items()}}
    return out


def route_class(ft: dict) -> str:
    fp, fd = ft.get("F_prompt"), ft.get("F_direct")
    if fp is None or fd is None:
        return "undefined"
    if 1 - ft["s"]["a"] < 0.5:
        return f"not gated (full-ban avoidance {1 - ft['s']['a']:.2f} < 0.5): no route class"
    if fp >= 0.5 and fd >= 0.5:
        return "redundant"
    if fd >= 0.5 > fp:
        return "direct"
    if fp >= 0.5 > fd:
        return "prompt"
    return "superadditive"


def run_route_stage() -> None:
    rows = load_exp16_rows()
    screen = json.loads((WS / "screen.json").read_text())
    push = {t: v["push_top1"] for t, v in screen["tasks"].items()}
    df, info = route_landing_table(rows, push)
    df.to_csv(TAB / "route_landing.csv", index=False)
    rec_route = json.loads(p("exp16", "results/route.json").read_text())["route"]
    blocks = {}
    for mode in ("plain", "cat"):
        for name, tasks in (("all5", ROUTE_TASKS), ("wo_T13", [t for t in ROUTE_TASKS if t != "T13"])):
            blocks[f"{mode}_{name}"] = route_fraction_block(rows, tasks, mode)
    repro = {"F_prompt_recorded": rec_route["point"]["F_prompt"], "F_direct_recorded": rec_route["point"]["F_direct"],
             "F_prompt_jack_recorded": rec_route["intervals"]["F_prompt"]["jackknife"],
             "F_direct_jack_recorded": rec_route["intervals"]["F_direct"]["jackknife"],
             "F_prompt_rederived": blocks["plain_all5"]["point"]["F_prompt"],
             "F_direct_rederived": blocks["plain_all5"]["point"]["F_direct"],
             "F_prompt_jack_rederived": blocks["plain_all5"]["jackknife"]["F_prompt"]["ci95"],
             "F_direct_jack_rederived": blocks["plain_all5"]["jackknife"]["F_direct"]["ci95"]}
    repro["match"] = bool(abs(repro["F_prompt_recorded"] - repro["F_prompt_rederived"]) < 1e-9
                          and abs(repro["F_direct_recorded"] - repro["F_direct_rederived"]) < 1e-9)
    t13 = {"plain": route_class(blocks["plain_all5"]["per_task"]["T13"]),
           "cat_only": route_class(blocks["cat_all5"]["per_task"]["T13"]),
           "plain_F": blocks["plain_all5"]["per_task"]["T13"], "cat_F": blocks["cat_all5"]["per_task"]["T13"]}
    # lead paragraph from the table
    t10 = df[(df.task == "T10")].set_index("arm")
    t03 = df[(df.task == "T03")].set_index("arm")
    js_rows = df[df.arm != "a"].dropna(subset=["JS_vs_a"])
    n_out = int((js_rows.within_null_rederived == False).sum())  # noqa: E712
    lead = (f"Route-landing lead (exp16, five gated tasks): where a route alone reproduces avoidance, the landing it "
            f"produces can differ from the full ban's. On T10 the full ban (arm a) lands "
            f"{t10.loc['a', 'nondefault_attempted_composition']}, while the prompt route c lands "
            f"{t10.loc['c', 'nondefault_attempted_composition']} and the direct route d lands "
            f"{t10.loc['d', 'nondefault_attempted_composition']}: both routes together choose BFS, and DFS is the generic "
            f"landing of either route alone. On T03 the direct route lands {t03.loc['d', 'nondefault_attempted_composition']} "
            f"against {t03.loc['a', 'nondefault_attempted_composition']} under the full ban (the size-k heap needs the "
            f"ban-reading task-spec states). {n_out} of {len(js_rows)} route arms lie outside their re-derived JS null "
            f"(base-2 JS against arm a, template-then-program resampling). None of the ban-free predictors is a reliable "
            f"guide to the route-specific landing: association hits {int(df.hit_association_modal.sum())}, FRLP runner-up "
            f"hits {int(df.hit_frlp_runner_up.sum())}, proximity hits {int(df.hit_proximity_top1.sum())}, push-landing hits "
            f"{int(df.hit_push_top1.sum())} of {len(df)} task-arm cells (modal non-default landing, 'other' excluded).")
    out = {"table": "tables/route_landing.csv", "readings": info["readings"],
           "readings_matched": sum(c["match"] for c in info["readings"]), "n_readings": len(info["readings"]),
           "route_fractions": blocks, "exp16_reproduction": repro, "T13_route_class": t13, "lead_paragraph": lead,
           "sources": [cite("exp16", "data/samples.jsonl"), cite("exp16", "results/landing_by_route.json"),
                       cite("exp16", "results/route.json"), cite("exp11", "data/association.jsonl"),
                       cite("exp11", "data/frlp_cells.jsonl"), cite("exp13", "predictions/proximity.json")],
           "js_matches_recorded_1e-6": int(js_rows["JS_match_1e-6"].fillna(False).sum()), "n_js": int(len(js_rows))}
    (RES / "route.json").write_text(json.dumps(out, indent=1, default=str))
    logger.info(f"route: readings {out['readings_matched']}/{out['n_readings']}; JS match {out['js_matches_recorded_1e-6']}/"
                f"{out['n_js']}; exp16 repro {repro['match']}; wo_T13 plain {blocks['plain_wo_T13']['point']}; "
                f"cat {blocks['cat_all5']['point']}")
