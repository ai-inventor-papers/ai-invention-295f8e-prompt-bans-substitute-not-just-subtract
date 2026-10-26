"""Frozen event assembly (hash-committed in COMMIT #1): per-(Y, arm) statistics, exposure events, the primary C1 run
and its pre-registered sensitivities, and the C1-exposure inputs.  Pure functions over per-sample rows."""

from __future__ import annotations

import math
from collections import Counter, defaultdict

from . import c1

ARMS_EVENT = {"named": "exposure_named", "unnamed": "exposure_unnamed"}


def wilson(k: int, n: int, z: float = 1.959964) -> list[float]:
    if n == 0:
        return [float("nan"), float("nan")]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [max(0.0, c - h), min(1.0, c + h)]


def arm_stats(rows: list[dict], y: str, survivors: list[str], default: str) -> dict:
    """rows: samples of one (Y, arm[, round]).  Labels: mode ids, 'other', 'unknown' or 'invalid'."""
    n = len(rows)
    raw = Counter(r["label"] for r in rows)
    att = [r for r in rows if r["label"] != "invalid"]
    n_att = len(att)
    n_y = sum(1 for r in att if r["label"] == y)
    non = [r for r in att if r["label"] != y]
    land = Counter(c1.normalise_label(r["label"], y, survivors) for r in non)
    land_c = Counter(c1.normalise_label(r["label"], y, survivors) for r in non if r.get("passed"))
    avoid = 1 - n_y / n_att if n_att else float("nan")
    per_p = defaultdict(Counter)
    for r in non:
        per_p[r.get("p_index")][c1.normalise_label(r["label"], y, survivors)] += 1
    return {"n_programs": n, "label_counts": dict(raw), "n_invalid": raw.get("invalid", 0), "n_attempts": n_att,
            "n_Y": n_y, "Y_share": n_y / n_att if n_att else float("nan"), "Y_share_ci95": wilson(n_y, n_att),
            "avoidance": avoid, "avoidance_ci95": wilson(n_att - n_y, n_att), "n_nonY": len(non),
            "landing_counts": dict(land), "correct_counts": dict(land_c),
            "other_share": land.get(c1.OTHER, 0) / len(non) if non else float("nan"),
            "pass_rate": sum(1 for r in rows if r.get("passed")) / n if n else float("nan"),
            "pass_rate_attempts": sum(1 for r in att if r.get("passed")) / n_att if n_att else float("nan"),
            "hill_cc": c1.hill_shannon(land_c),
            "default_share": sum(1 for r in att if r["label"] == default) / n_att if n_att else float("nan"),
            "n_default": sum(1 for r in att if r["label"] == default),
            "modal_nonY": c1.modal(dict(land)),
            "landing_by_program": {str(k): dict(v) for k, v in sorted(per_p.items(), key=lambda kv: str(kv[0]))}}


def subtract_top1(dist: dict | None, survivors: list[str]) -> dict | None:
    if not dist:
        return None
    s = {k: v for k, v in dist.items() if k in survivors and v > 0}
    if not s:
        return None
    mx = max(s.values())
    top = [k for k, v in s.items() if v == mx]
    return {k: 1.0 / len(top) for k in top}


def build_events(samples: list[dict], meta: dict, forecasts: dict, arms=("named", "unnamed"),
                 model: str = "Qwen/Qwen3-8B", commit_sha256: str | None = None,
                 landing_key: str = "landing_counts") -> list[dict]:
    """meta[key] = {task, Y, default, survivors, associate, n_pY, veto_round_used, coveto_modes, flags, priority};
    forecasts[key] = {SUBTRACT, LADDER, ASSOCIATE, PROXIMITY} raw distributions (None = undefined)."""
    by = defaultdict(list)
    for r in samples:
        by[(r["task"], r["Y"], r["arm"])].append(r)
    events = []
    for key, m in meta.items():
        for arm in arms:
            rows = by.get((m["task"], m["Y"], arm), [])
            if not rows:
                continue
            st = arm_stats(rows, m["Y"], m["survivors"], m["default"])
            land = st[landing_key]
            fc = forecasts[key]
            sc = c1.score_event(m["survivors"], land, fc)
            gate_pass = c1.gate(st["avoidance"], st["n_nonY"])
            if landing_key == "correct_counts":
                gate_pass = gate_pass and sum(land.values()) > 0
            events.append({"model": model, "task": m["task"], "event_type": ARMS_EVENT[arm], "banned": m["Y"],
                           "Y": m["Y"], "arm": arm, "default": m["default"], "associate": m["associate"],
                           "survivors": m["survivors"], "n_attempts": st["n_attempts"], "avoidance": st["avoidance"],
                           "avoidance_ci95": st["avoidance_ci95"], "n_nonY": st["n_nonY"], "gate_pass": gate_pass,
                           "landing_counts": st["landing_counts"], "correct_counts": st["correct_counts"],
                           "landing_counts_norm": land, "other_share": st["other_share"],
                           "forecasts": fc, "top1": sc["top1"], "logscore": sc["logscore"], "hit": sc["hit"],
                           "modal": sc["modal"], "disagreeing": sc["disagreeing"], "unaimed": sc["unaimed"],
                           "commit_sha256": commit_sha256, "n_pY": m["n_pY"], "veto_round_used": m["veto_round_used"],
                           "coveto": m["coveto_modes"], "flags": m["flags"], "priority": m["priority"],
                           "hill_cc": st["hill_cc"], "pass_rate": st["pass_rate"], "default_share": st["default_share"]})
    return events


def sensitivities(events_named: list[dict], forecasts: dict, prox_token: dict, n_boot: int = 2000) -> dict:
    """Pre-registered C1 sensitivities on the NAMED events."""
    out = {}
    ev2 = []
    for e in events_named:
        fc = dict(e["forecasts"])
        fc["SUBTRACT"] = subtract_top1(fc.get("SUBTRACT"), e["survivors"])
        ev2.append(fc)
    out["subtract_top1"] = _summ(c1.run_c1(c1.rescore(events_named, ev2), n_boot=n_boot))
    pair = {}
    for a, b in c1.TEST_PAIRS:
        sel = [e for e in events_named if e["gate_pass"] and set(e["top1"][a]) != set(e["top1"][b])]
        d = [e["logscore"][a] - e["logscore"][b] for e in sel]
        w = c1.wilcoxon_two_sided(d) if d else {"p": None, "n_nonzero": 0}
        wins_a = sum(1 for x in d if x >= c1.WIN_MARGIN)
        wins_b = sum(1 for x in d if x <= -c1.WIN_MARGIN)
        pair[f"{a}-{b}"] = {"n_events": len(sel), "mean_diff": (sum(d) / len(d)) if d else None, "p_uncorrected": w.get("p"),
                            "wins": {a: wins_a, b: wins_b}}
    out["per_pair_disagreeing"] = pair
    out["exclude_coveto_survivor"] = _summ(c1.run_c1([e for e in events_named if not e["coveto"]], n_boot=n_boot))
    out["priority_only"] = _summ(c1.run_c1([e for e in events_named if e["priority"]], n_boot=n_boot))
    ev_tok = []
    for e in events_named:
        fc = dict(e["forecasts"])
        fc["PROXIMITY"] = prox_token.get(f"{e['task']}:{e['Y']}")
        ev_tok.append(fc)
    out["token_distance_proximity"] = _summ(c1.run_c1(c1.rescore(events_named, ev_tok), n_boot=n_boot))
    return out


def correct_only(samples: list[dict], meta: dict, forecasts: dict, commit_sha256: str | None, n_boot: int = 2000) -> dict:
    ev = build_events(samples, meta, forecasts, arms=("named",), commit_sha256=commit_sha256,
                      landing_key="correct_counts")
    return _summ(c1.run_c1(ev, n_boot=n_boot))


def _summ(res: dict) -> dict:
    return {"n_gated_disagreeing": res["n_gated_disagreeing"], "n_gated": res["n_gated"], "wins": res["rule"]["wins"],
            "advancing": res["rule"]["advancing"], "branch": res["branch"], "unaimed_share": res["unaimed_share"],
            "tests": res["tests"]}


def exposure_items(events_named: list[dict], samples: list[dict], veto_round_used: dict) -> list[dict]:
    """C1-exposure inputs: per gated NAMED event, the per-shown-program non-Y labels under NAMED and under the veto
    round whose landing defines SUBTRACT."""
    by = defaultdict(list)
    for r in samples:
        by[(r["task"], r["Y"], r["arm"], r.get("round") or 0)].append(r)
    items = []
    for e in events_named:
        if not e["gate_pass"]:
            continue
        key = f"{e['task']}:{e['Y']}"
        rnd = veto_round_used.get(key)
        if not rnd:
            continue

        def clusters(rows):
            cl = defaultdict(list)
            for r in rows:
                lab = c1.normalise_label(r["label"], e["Y"], e["survivors"])
                if lab is None or lab == e["Y"]:
                    continue
                cl[r.get("p_index")].append(lab)
            return [cl[k] for k in sorted(cl, key=str)]

        items.append({"task": e["task"], "Y": e["Y"], "survivors": e["survivors"], "coveto": e["coveto"],
                      "default": e["default"], "associate_top1": e["top1"]["ASSOCIATE"],
                      "subtract_dist": e["forecasts"].get("SUBTRACT"), "proximity_top1": e["top1"]["PROXIMITY"],
                      "named_clusters": clusters(by[(e["task"], e["Y"], "named", 0)]),
                      "veto_clusters": clusters(by[(e["task"], e["Y"], "veto", rnd)])})
    return items
