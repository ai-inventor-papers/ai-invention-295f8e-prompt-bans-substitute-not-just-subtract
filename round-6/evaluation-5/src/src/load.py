"""Unit-level and event-level loaders: every value carries its provenance string (artifact:path#key)."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any

from common import WS, Inputs, prov

EXISTING = ["T03", "T04", "T05", "T06", "T08", "T10", "T11", "T13", "T14", "R1", "R2", "R3", "R6", "T1", "T2"]
PANEL_A = ["A1", "A2", "A3", "A4", "A5", "A7", "A8", "A9"]
PANEL_B = ["B1", "B2", "B3", "B4", "B5", "B6", "B7"]
PANEL = PANEL_A + PANEL_B
PRIMARY13 = ["A1", "A2", "A3", "A4", "A5", "A7"] + PANEL_B
UNITS30 = EXISTING + PANEL
PATH_CATALOGUE = {"T1": ["bfs", "dfs", "bibfs", "iddfs", "astar_gbfs", "dijkstra"],
                  "T2": ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"]}
BENCH_DIR = {"T03": "T03_kth_smallest", "T04": "T04_substring_search", "T05": "T05_two_sum",
             "T06": "T06_find_duplicate", "T08": "T08_fibonacci", "T10": "T10_connected_components",
             "T11": "T11_longest_increasing_subsequence", "T13": "T13_merge_intervals", "T14": "T14_top_k_frequent",
             "R1": "R1_non_overlapping_intervals", "R2": "R2_cycle_detection", "R3": "R3_topological_order",
             "R6": "R6_first_last_position"}


def _correct_ct(d: dict | None) -> Counter:
    return Counter({k: int(v) for k, v in (d or {}).items() if int(v) > 0})


def load_units(inp: Inputs) -> dict[str, dict[str, Any]]:
    """The 30 iteration-5 units: default, twin (N 50), base chat/plain correct compositions, committed beta, E_u."""
    U: dict[str, dict[str, Any]] = {}
    br = inp.json("exp24", "results/base_repertoire.json")["per_task"]
    xa = inp.json("exp25", "results/extra_arm_a.json")
    for t in EXISTING:
        b = br[t]
        cat = (PATH_CATALOGUE[t] if t in PATH_CATALOGUE else
               [c["mode"] for c in inp.json("exp25", f"inputs/exp11/bench/{BENCH_DIR[t]}/spec.json")["catalogue"]])
        U[t] = {"unit": t, "set": "existing", "default": b["default"], "catalogue": cat,
                "twin_correct": _correct_ct(b["twin_S1"]["composition_correct"]), "twin_n": int(b["twin_S1"]["n"]),
                "twin_src": prov("exp24", "results/base_repertoire.json", f"per_task.{t}.twin_S1"),
                "base_chat_correct": _correct_ct(b["base_chat"]["composition_correct"]),
                "base_plain_correct": _correct_ct(b["base_plain"]["composition_correct"]),
                "base_chat_attempted": _correct_ct(b["base_chat"].get("composition_attempted")),
                "base_plain_attempted": _correct_ct(b["base_plain"].get("composition_attempted")),
                "base_chat_n": int(b["base_chat"]["n"]), "base_plain_n": int(b["base_plain"]["n"]),
                "base_src": prov("exp24", "results/base_repertoire.json", f"per_task.{t}.base_chat|base_plain"),
                "beta_committed": b.get("beta"), "r_committed": b.get("r_t"),
                "beta_committed_src": prov("exp24", "results/base_repertoire.json", f"per_task.{t}.beta"),
                "E": xa[t]["E"], "E1": xa[t]["E1"], "E2": xa[t]["E2"], "landing": xa[t].get("landing"),
                "E_src": prov("exp25", "results/extra_arm_a.json", f"{t}.E"),
                "twin_bf16_labels": dict(xa[t]["twin"].get("labels", {})),
                "twin_bf16_landing_correct": dict(xa[t]["twin"].get("landing_correct", {}))}
    pa = inp.json("exp25", "pooled_inputs.json")
    for u in pa["units"]:
        if u["unit_id"] not in PANEL_A:
            continue
        b, tw, r = u["base"], u["twin"], u["rivals"]
        U[u["unit_id"]] = {
            "unit": u["unit_id"], "set": "panelA", "kind": u["unit_kind"], "default": u["default"],
            "catalogue": list(u["catalogue"]), "twin_correct": _correct_ct(tw["comp_correct"]), "twin_n": int(tw["n"]),
            "twin_src": prov("exp25", "pooled_inputs.json", f"units[{u['unit_id']}].twin"),
            "base_chat_correct": _correct_ct(b["chat"]["comp_correct"]),
            "base_plain_correct": _correct_ct(b["plain"]["comp_correct"]),
            "base_chat_attempted": _correct_ct(b["chat"].get("comp_valid")),
            "base_plain_attempted": _correct_ct(b["plain"].get("comp_valid")),
            "base_chat_n": int(b["chat"]["n_rows"]), "base_plain_n": int(b["plain"]["n_rows"]),
            "base_chat_valid": int(b["chat"]["n_valid"]), "base_plain_valid": int(b["plain"]["n_valid"]),
            "base_src": prov("exp25", "pooled_inputs.json", f"units[{u['unit_id']}].base.chat|plain"),
            "beta_committed": b.get("beta"), "r_committed": b.get("r"),
            "beta_committed_src": prov("exp25", "pooled_inputs.json", f"units[{u['unit_id']}].base.beta"),
            "E": u["escape"]["E"], "E1": u["escape"]["E1"], "E2": u["escape"]["E2"],
            "landing": u["escape"].get("landing"),
            "E_src": prov("exp25", "pooled_inputs.json", f"units[{u['unit_id']}].escape.E"),
            "escape_cells": u["escape"]["cells"], "rivals": r, "novelty_excess": r.get("novelty_excess"),
            "novelty_share": r.get("novelty_share"), "assoc_counts": r.get("assoc_counts"),
            "pn": u.get("pn"), "t13": u.get("t13")}
    pb = inp.json("exp26", "pooled_inputs.json")
    # panel B plain-completion base rows are not in pooled_inputs: read them from the labelled sample rows
    plain = defaultdict(Counter)
    plain_att = defaultdict(Counter)
    plain_n = Counter()
    for r in inp.jsonl("exp26", "data/samples.jsonl"):
        if r.get("model") == "Qwen/Qwen3-8B-Base" and r.get("arm") == "PLAIN" and r.get("unit") in PANEL_B:
            plain_n[r["unit"]] += 1
            if r.get("valid") in (True, "True") and r.get("label") not in (None, "invalid"):
                plain_att[r["unit"]][r["label"]] += 1
            if r.get("passed") in (True, "True") and r.get("label"):
                plain[r["unit"]][r["label"]] += 1
    for rec in pb["records"]:
        u = rec["unit_id"]
        if u not in PANEL_B:
            continue
        b, o, f = rec["base"], rec["outcomes"], rec["unit_facts"]
        U[u] = {"unit": u, "set": "panelB", "kind": rec["unit_kind"], "default": f["default"],
                "catalogue": list(f["catalogue"]), "twin_correct": _correct_ct(rec["twin"]["correct_composition"]),
                "twin_n": int(rec["twin"]["n"]),
                "twin_src": prov("exp26", "pooled_inputs.json", f"records[{u}].twin"),
                "base_chat_correct": _correct_ct(b["correct_composition"]), "base_plain_correct": plain[u],
                "base_chat_attempted": _correct_ct(b.get("attempted_composition")),
                "base_plain_attempted": plain_att[u],
                "base_chat_n": int(b["n_base"]), "base_plain_n": int(plain_n[u]),
                "base_src": prov("exp26", "pooled_inputs.json", f"records[{u}].base.correct_composition") +
                " + " + prov("exp26", "data/samples.jsonl", "model=Qwen3-8B-Base,arm=PLAIN"),
                "beta_committed": b.get("beta_u"), "beta_source": b.get("beta_source"), "r_committed": b.get("r_u"),
                "beta_committed_src": prov("exp26", "pooled_inputs.json", f"records[{u}].base.beta_u"),
                "E": o["E_u"], "E1": o["E_alpha1"], "E2": o["E_alpha2"], "landing": o.get("push_landing"),
                "E_src": prov("exp26", "pooled_inputs.json", f"records[{u}].outcomes.E_u"),
                "rivals": rec["rivals"], "forecasts": rec.get("forecasts"), "outcomes": o,
                "landing_composition": o.get("push_landing_composition")}
    return U


def base_pooled(u: dict) -> Counter:
    return u["base_chat_correct"] + u["base_plain_correct"]


def beta_v6(u: dict, include_other: bool = False) -> float | None:
    """v6 beta: q_base's correct-only share off the instruct default, chat and plain correct programs pooled.
    Numerator: correct base programs whose catalogue label differs from the default ('other' excluded unless
    include_other); denominator: all correct base programs (the iteration-5 convention of exp24)."""
    c = base_pooled(u)
    n = sum(c.values())
    if n == 0:
        return None
    off = sum(v for k, v in c.items() if k != u["default"] and (include_other or (k in u["catalogue"])))
    return off / n


def twin_modal(u: dict) -> tuple[str | None, int, int]:
    c = u["twin_correct"]
    if not c:
        return None, 0, 0
    m, k = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0]
    return m, k, sum(c.values())


def t_u(u_twin_correct: Counter, default: str) -> str | None:
    c = {k: v for k, v in u_twin_correct.items() if k != default and k != "other" and v > 0}
    if not c:
        return None
    return sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def write_index(obj: Any, name: str) -> None:
    (WS / "results").mkdir(exist_ok=True)
    (WS / "results" / name).write_text(json.dumps(obj, indent=1))
