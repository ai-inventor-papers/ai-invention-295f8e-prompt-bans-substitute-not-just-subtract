#!/usr/bin/env python3
"""Short, independent re-derivation of the headline numbers (stdlib only; no import from src/).

Reads raw per-row files (results/retrace.jsonl, results/tracer_gate_gold_round2.jsonl, data/labelled_v9_*.jsonl,
data/raw_*.jsonl) and recomputes, with its own code:
  - the tracer gate counts (references, planted controls, gold agreement);
  - N1: the pooled lexical-minus-mechanistic gap over the 10 configurations under both mechanism readings, the number of
    configurations with a positive gap, and an exact McNemar p per configuration;
  - N2: the share of C6 name-level survivors in a banned coarse class, under both readings;
  - the sampling spend summed from the per-row usage.cost fields.
Placebo: the same N1 gap and McNemar test with the lexical and mechanistic flags swapped at random within each program
(200 draws) must lose the effect (pooled gap near 0, few configurations significant).
Writes results/rederive_headlines.json.
"""

import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES, DATA = ROOT / "results", ROOT / "data"
BANNED = {"bfs", "dfs", "iddfs", "astar", "gbfs"}
BANNED_CLASSES = {"BFS", "DFS", "ID", "HEUR"}      # coarse order classes of the five banned algorithms (plan 1.11)
COARSE = {"bfs": "BFS", "dfs": "DFS", "dijkstra_unit": "BFS", "iddfs": "ID", "idastar": "ID", "astar": "HEUR",
          "gbfs": "HEUR", "jps": "HEUR", "bibfs": "BIDIR", "biastar": "BIDIR"}
UNKNOWN = {"", "unknown", "none", "null", "n/a"}


def rows(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def mech_class(r: dict, reading: str) -> str | None:
    """None = no mechanism reading for this program (no code / untraceable)."""
    if reading == "runtime":
        lab = r.get("runtime_label")
        return None if (not r.get("has_code") or lab in (None, "invalid")) else COARSE.get(lab, "OTHER")
    c = r.get("order_class")
    return None if c in (None, "UNTRACEABLE") else c


def mcnemar_p(b: int, c: int) -> float:
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def n1(ret: list[dict], reading: str, rng: random.Random | None = None) -> dict:
    by: dict[str, list[tuple[bool, bool]]] = {}
    for r in ret:
        m = mech_class(r, reading)
        if m is None:
            continue
        lex, mech = bool(r["lexical_L1"]), m not in BANNED_CLASSES
        if rng is not None and rng.random() < 0.5:
            lex, mech = mech, lex
        by.setdefault(r["config"], []).append((lex, mech))
    per = {}
    for cfg, xs in sorted(by.items()):
        b = sum(1 for lx, mc in xs if lx and not mc)
        c = sum(1 for lx, mc in xs if mc and not lx)
        per[cfg] = {"n": len(xs), "gap": (b - c) / len(xs), "mcnemar_p": mcnemar_p(b, c)}
    return {"pooled": sum(v["gap"] for v in per.values()) / len(per), "n_configs": len(per),
            "n_positive": sum(v["gap"] > 0 for v in per.values()),
            "n_sig": sum(v["mcnemar_p"] < 0.05 for v in per.values()), "per_config": per}


def named_survivor(r: dict) -> bool:
    lab = r.get("label")
    if not r.get("passed") or lab in (None, "invalid", "no_code") or lab in BANNED:
        return False
    return lab != "other" or str(r.get("label_other_name") or "").strip().lower() not in UNKNOWN


def main() -> None:
    out: dict = {}
    g2 = json.loads((RES / "tracer_gate_round2.json").read_text())
    gold = rows(RES / "tracer_gate_gold_round2.jsonl")
    unverified = set(g2.get("unverified_classes") or [])
    traced = [g for g in gold if g["class"] not in (None, "UNTRACEABLE")]
    scope = [g for g in traced if g["expected_fine"] not in unverified]
    out["gate"] = {"references_ok": sum(x["class"] == x["expected"] for x in g2["references"]),
                   "references_n": len(g2["references"]),
                   "controls_class_ok": sum(x["class"] == x["expected"] for x in g2["controls"]),
                   "controls_class_and_suite_ok": sum(x["class"] == x["expected"] and x["passes_48"]
                                                      for x in g2["controls"]),
                   "controls_n": len(g2["controls"]),
                   "gold_n": len(gold), "gold_traced": len(traced), "gold_in_scope": len(scope),
                   "gold_agree": sum(g["class"] == g["expected"] for g in scope)}
    out["gate"]["gold_agreement"] = out["gate"]["gold_agree"] / out["gate"]["gold_in_scope"]

    ret = rows(RES / "retrace.jsonl")
    out["n1_runtime"] = n1(ret, "runtime")
    out["n1_tracer"] = n1(ret, "tracer")
    plac = {}
    for reading in ("runtime", "tracer"):
        draws = [n1(ret, reading, random.Random(s)) for s in range(200)]
        pooled = sorted(d["pooled"] for d in draws)
        plac[reading] = {"draws": 200, "pooled_mean": sum(pooled) / 200, "pooled_q025_q975": [pooled[4], pooled[195]],
                         "mean_configs_significant": sum(d["n_sig"] for d in draws) / 200,
                         "share_draws_pooled_ge_0.3": sum(p >= 0.3 for p in pooled) / 200}
    out["placebo_swap_within_program"] = plac

    pool = [r for r in ret if r["config"] == "C6"]
    pool += rows(DATA / "labelled_v9_A_k5.jsonl") + rows(DATA / "labelled_v9_A_k5_ho.jsonl")
    surv = [r for r in pool if named_survivor(r)]
    for reading in ("runtime", "tracer"):
        cl = [mech_class(r, reading) for r in surv]
        cl = [c for c in cl if c is not None]
        out[f"n2_{reading}"] = {"n": len(cl), "banned_class": sum(c in BANNED_CLASSES for c in cl),
                                "share": sum(c in BANNED_CLASSES for c in cl) / max(len(cl), 1)}

    spend = sum(float(r.get("cost_usd") or 0.0) for p in sorted(DATA.glob("raw_*.jsonl")) for r in rows(p))
    out["sampling_spend_from_rows_usd"] = round(spend, 6)

    (RES / "rederive_headlines.json").write_text(json.dumps(out, indent=1))
    g, a, t = out["gate"], out["n1_runtime"], out["n1_tracer"]
    print(f"gate: refs {g['references_ok']}/{g['references_n']}, controls class {g['controls_class_ok']}/"
          f"{g['controls_n']} (class+suite {g['controls_class_and_suite_ok']}), gold {g['gold_agree']}/"
          f"{g['gold_in_scope']} = {g['gold_agreement']:.3f}")
    for name, d in (("runtime", a), ("tracer", t)):
        print(f"N1 {name}: pooled {d['pooled']:.4f}, positive {d['n_positive']}/{d['n_configs']}, McNemar p<0.05 in "
              f"{d['n_sig']}; placebo pooled mean {plac[name]['pooled_mean']:.4f} "
              f"[{plac[name]['pooled_q025_q975'][0]:.3f}, {plac[name]['pooled_q025_q975'][1]:.3f}], "
              f"configs significant {plac[name]['mean_configs_significant']:.2f}")
    for name in ("runtime", "tracer"):
        d = out[f"n2_{name}"]
        print(f"N2 {name}: {d['banned_class']}/{d['n']} = {d['share']:.3f}")
    print(f"sampling spend from rows: {out['sampling_spend_from_rows_usd']:.4f} USD")


if __name__ == "__main__":
    main()
