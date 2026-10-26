"""(0g) Minor rigor: defined-only hit rates, the exposure sentence, Table 82 per distinct likelihood row (exp7)."""

from __future__ import annotations

import ast
import json
from collections import defaultdict

import numpy as np
import pandas as pd
from loguru import logger

from src.paths import WS, cite, p

RES, TAB = WS / "results", WS / "tables"
FAMS = ["SUBTRACT", "LADDER", "ASSOCIATE", "PROXIMITY"]


def _jsonl(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def _modal(counts: dict, banned: str | list | None) -> list[str]:
    ban = set(banned if isinstance(banned, list) else [banned])
    c = {k: v for k, v in counts.items() if k not in ban and k not in ("invalid", "no_code", "unresolved")}
    if not c:
        return []
    m = max(c.values())
    return sorted(k for k, v in c.items() if v == m)


def defined_only(contest: str, events: list[dict], defined_fn, top_fn, landing_fn) -> list[dict]:
    out = []
    for f in FAMS:
        n_def = hits = frac = 0
        for e in events:
            if not defined_fn(e, f):
                continue
            n_def += 1
            tops = top_fn(e, f)
            land = landing_fn(e)
            if tops and land:
                hits += int(len(tops) == 1 and tops[0] in land)
                frac += (1 / len(tops)) if any(t in land for t in tops) else 0.0
        out.append({"contest": contest, "family": f, "n_events": len(events), "n_defined": n_def,
                    "top1_hits_defined_only": hits, "hit_rate_defined_only": hits / n_def if n_def else None,
                    "fractional_tie_credit": frac, "fractional_rate": frac / n_def if n_def else None})
    return out


def table82() -> tuple[pd.DataFrame, dict]:
    cells = [r for r in _jsonl(p("exp7", "results/frlp_cells.jsonl")) if r.get("variant") == "primary"
             and r.get("half") == "all"]
    L = defaultdict(lambda: defaultdict(list))
    for r in cells:
        parts = r["condition"].split("|")
        # ban|X|W ; neutral|X|W|{A,B} (two token-matched twin variants, pooled)
        if (parts[0] == "ban" and len(parts) == 3) or (parts[0] == "neutral" and len(parts) == 4):
            try:
                L[(r["task"], parts[0], parts[1])][r["algorithm"]].append(float(r["L"]))
            except (TypeError, ValueError):
                continue
    lp = json.loads(p("exp7", "frozen/ladder_profile.json").read_text())
    ge = json.loads(p("exp7", "results/gate_events.json").read_text())["events"]
    realised_modal = {}
    for e in ge:
        if e["condition"].startswith("ban:"):
            dist = ast.literal_eval(e["distribution_allowed"]) if isinstance(e["distribution_allowed"], str) else e["distribution_allowed"]
            m = _modal(dist, e["condition"].split(":")[1])
            realised_modal[(e["task"], e["condition"].split(":")[1])] = m[0] if m else None
    default = {"t1": "bfs", "t2": "dijkstra"}
    rows = []
    for (t, kind, X), d in sorted(L.items()):
        if kind != "ban" or X in ("nonce", "two_step"):
            continue
        cat = list(lp[t]["measurable"])
        if X not in cat:
            continue
        ban = {j: float(np.mean(v)) for j, v in d.items() if j in cat}
        twin = {j: float(np.mean(v)) for j, v in L.get((t, "neutral", X), {}).items() if j in cat}
        surv = [j for j in cat if j != X and j in ban and j in twin]
        if not surv:
            continue
        gain = {j: ban[j] - twin[j] for j in surv}
        g = np.array([gain[j] for j in surv])
        u = np.array([lp[t]["u"][j] for j in surv])
        gc, uc = g - g.mean(), u - u.mean()
        a = float(gc @ uc / (uc @ uc)) if (uc @ uc) > 0 else 0.0
        resid = dict(zip(surv, (gc - a * uc).tolist()))
        allowed = surv
        m = max(ban[j] for j in cat if j in ban)
        z = sum(np.exp(ban[j] - m) for j in cat if j in ban)
        implied = {j: float(np.exp(ban[j] - m) / z) for j in cat if j in ban}
        row_type = "modal" if X == default[t] else "sham"
        realised = realised_modal.get((t, X)) if row_type == "modal" else default[t]
        if row_type == "modal" and realised is None:
            realised = None
        am_gain = max(surv, key=lambda j: gain[j])
        am_res = max(surv, key=lambda j: resid[j])
        am_imp = max(allowed, key=lambda j: implied[j])
        rows.append({"task": t, "condition": f"ban|{X}", "row_type": row_type, "realised_landing": realised,
                     "argmax_gain": am_gain, "argmax_residual_gain": am_res, "argmax_implied_mass": am_imp,
                     "hit_gain": am_gain == realised, "hit_residual": am_res == realised, "hit_implied": am_imp == realised,
                     "ladder_scale_a": a, "gain": json.dumps({k: round(v, 3) for k, v in gain.items()}),
                     "implied_mass": json.dumps({k: round(v, 4) for k, v in implied.items()})})
    df = pd.DataFrame(rows)
    summ = {"n_rows": int(len(df)), "n_modal": int((df.row_type == "modal").sum()), "n_sham": int((df.row_type == "sham").sum()),
            "hits_gain": int(df.hit_gain.sum()), "hits_residual": int(df.hit_residual.sum()),
            "hits_implied": int(df.hit_implied.sum()), "hits_implied_sham": int(df[df.row_type == "sham"].hit_implied.sum()),
            "definitions": "L = mean over W1-W5 of the primary yield-corrected FRLP log-likelihood (half 'all'); gain_j = "
                           "L(ban|X) - L(neutral|X) over survivors (neutral twins A and B pooled); residual = centred gain minus a x centred frozen ladder "
                           "profile u (a by least squares, exp7 c1.py decomposition); implied mass = softmax of L(ban|X) over "
                           "the measurable catalogue, argmax over allowed (non-banned) modes. Realised landing: modal "
                           "non-banned label of the exp1 event in gate_events.json for modal rows; the default for sham rows.",
            "divergence_note": "exp7 frlp_cells carry 'L' (yield-corrected, primary) rather than a column named L_corr; "
                               "L is used as L_corr. Sham rows are bans of algorithms absent from the default output.",
            "expected": "gain 0/11, residual 0/11, implied 8/11 (6 sham)",
            "sources": [cite("exp7", "results/frlp_cells.jsonl"), cite("exp7", "frozen/ladder_profile.json"),
                        cite("exp7", "results/gate_events.json")]}
    return df, summ


def run_rigor_stage() -> None:
    out = {}
    # (i) defined-only hit rates
    c13 = [e for e in _jsonl(p("exp13", "results/c1_events.jsonl")) if e.get("gate_pass")]
    rows = defined_only("bench (exp13, gated)", c13, lambda e, f: bool(e.get("defined", {}).get(f)),
                        lambda e, f: [e["top1"][f]] if e["top1"].get(f) else [],
                        lambda e: _modal(e["landing_counts"], e["banned"]))
    c14 = [e for e in _jsonl(p("exp14", "results/c1_events.jsonl")) if e.get("gate_pass")]
    rows += defined_only("exposure (exp14, gated)", c14,
                         lambda e, f: not (f == "SUBTRACT" and "subtract_undefined" in (e.get("flags") or [])),
                         lambda e, f: list(e["top1"].get(f) or []), lambda e: list(e.get("modal") or []))
    fc15 = json.loads(p("exp15", "predictions/forecasts.json").read_text())["events"]
    c15 = [e for e in _jsonl(p("exp15", "results/c1_events.jsonl")) if e.get("gate_pass")]
    rows += defined_only("Llama (exp15, gated)", c15, lambda e, f: bool(fc15[e["event_id"]]["families"][f].get("defined")),
                         lambda e, f: [e["top1"][f]] if e["top1"].get(f) else [], lambda e: [e.get("hit_label")])
    dfi = pd.DataFrame(rows)
    dfi.to_csv(TAB / "defined_only_hits.csv", index=False)
    out["defined_only"] = dfi.to_dict("records")
    # (ii) exposure sentence (exp14 SUBTRACT defined flags) and the bench analogue
    allc14 = _jsonl(p("exp14", "results/c1_events.jsonl"))
    ys = sorted({(e["task"], e["Y"]) for e in allc14})
    defined_y = sorted({(e["task"], e["Y"]) for e in allc14 if "subtract_undefined" not in (e.get("flags") or [])})
    per_arm = {}
    for arm in ("exposure_named", "exposure_unnamed"):
        evs = [e for e in allc14 if e["event_type"] == arm and (e["task"], e["Y"]) in defined_y]
        per_arm[arm] = {"n": len(evs), "names_landing": sum(1 for e in evs if set(e["top1"].get("SUBTRACT") or [])
                                                                & set(e.get("modal") or [])),
                        "pairs": [f"{e['Y']} -> {(e.get('modal') or [None])[0]} (SUBTRACT {e['top1'].get('SUBTRACT')})"
                                  for e in evs]}
    bench_def = [e for e in _jsonl(p("exp13", "results/c1_events.jsonl")) if e.get("defined", {}).get("SUBTRACT")]
    bench_hits = sum(1 for e in bench_def if e["top1"].get("SUBTRACT") in _modal(e["landing_counts"], e["banned"]))
    out["exposure_sentence"] = {
        "n_shown_algorithms": len(ys), "n_subtract_defined": len(defined_y), "defined_Y": defined_y, "per_arm": per_arm,
        "bench_modal_bans_subtract_defined": len(bench_def), "bench_hits": bench_hits,
        "sentence": (f"In the exposure contest the in-context SUBTRACT forecast was defined for {len(defined_y)} of {len(ys)} "
                     f"shown algorithms and named the landing {per_arm['exposure_named']['names_landing']} of "
                     f"{per_arm['exposure_named']['n']} times (NAMED) and {per_arm['exposure_unnamed']['names_landing']} of "
                     f"{per_arm['exposure_unnamed']['n']} (UNNAMED); on the modal bench bans it was defined "
                     f"{len(bench_def)} times and hit {bench_hits}."),
        "sources": [cite("exp14", "results/c1_events.jsonl"), cite("exp13", "results/c1_events.jsonl")]}
    # (iii) Table 82
    t82, s82 = table82()
    t82.to_csv(TAB / "table82_distinct_rows.csv", index=False)
    out["table82"] = s82
    (RES / "rigor.json").write_text(json.dumps(out, indent=1, default=str))
    logger.info(f"rigor: exposure {out['exposure_sentence']['sentence']}; table82 {s82['n_rows']} rows "
                f"gain {s82['hits_gain']} resid {s82['hits_residual']} implied {s82['hits_implied']} (sham {s82['hits_implied_sham']})")
