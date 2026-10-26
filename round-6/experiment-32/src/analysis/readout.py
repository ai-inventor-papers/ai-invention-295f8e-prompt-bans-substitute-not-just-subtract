#!/usr/bin/env python3
"""S9 readout analysis (committed: its sha256 is in commit #2, before any AV call).

PRIMARY N1. Units: ban states of eligible tasks (re-gated, defaulted, with a substitute Y*), templates W1/W2/W3/W5,
positions SPEC-3..READ. x = the majority (>= 2 of explanations #1-#3) of resolved EXPL 'planned' equals Y*;
y = TEXT-ONLY NAME 'planned' (the visible user text) equals Y*. Effect = mean(x) - mean(y), exact McNemar (b, c);
PASS iff effect >= 0.30 and p < 0.05. Task-cluster bootstrap CI, per-task / per-position tables, W4 apart;
sensitivities: per-explanation units, 'mentioned' instead of 'planned', unresolved items excluded.
SECONDARY (Holm): N1-swap (+ within-task condition permutation null), N1-rand, N1-predict, N2-default, N6.
DESCRIPTIVE: N3-forced, N4-seed, N5-gen curves, N7-template Spearman, N8-failure, judge agreement.

Usage: python analysis/readout.py   (writes results/readout.json)
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
from stats import cluster_bootstrap, holm, kappa, mcnemar_exact, rate, spearman  # noqa: E402

NAMED_EXCL = {"none_named", "other", "unresolved", None}
POS4 = ("SPEC-3", "SPEC-2", "SPEC-1", "READ")
PRIMARY_W = ("W1", "W2", "W3", "W5")


def jl(p: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


class Data:
    def __init__(self, root: Path = ROOT):
        self.c1 = json.loads((root / "predictions" / "commit1_defaults.json").read_text())
        self.c2 = json.loads((root / "predictions" / "commit2_readout.json").read_text())
        self.idx = {r["state_id"]: r for r in jl(root / "cache" / "states_index.jsonl")}
        self.jud = jl(root / "data" / "judgements.jsonl")
        self.labels = {r["sample_id"]: r for r in jl(root / "data" / "labels.jsonl")}
        self.expl: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.text: dict[str, dict[str, Any]] = {}
        for r in self.jud:
            if r["mode"] == "EXPL":
                self.expl[r["state_id"]].append(r)
            else:
                self.text[f"{r['mode']}|{r['text_id']}"] = r
        for v in self.expl.values():
            v.sort(key=lambda r: int(r["expl_id"].split("#")[-1]))
        self.tasks = self.c2["tasks"]

    def votes(self, sid: str, target: str, field: str = "planned", max_idx: int = 3,
              drop_unresolved: bool = False) -> tuple[int, int]:
        rs = [r for r in self.expl.get(sid, []) if int(r["expl_id"].split("#")[-1]) <= max_idx]
        if drop_unresolved:
            rs = [r for r in rs if r["resolved"] not in ("unresolved", None)]
        if field == "mentioned":
            hits = sum(target in (r.get("mentioned_any") or []) for r in rs)
        else:
            hits = sum(r["resolved"] == target for r in rs)
        return hits, len(rs)

    def x(self, sid: str, target: str, field: str = "planned", drop_unresolved: bool = False) -> int | None:
        h, n = self.votes(sid, target, field, drop_unresolved=drop_unresolved)
        if n == 0:
            return None
        return int(h >= 2) if n >= 2 else int(h >= 1)

    def planned_majority(self, sid: str) -> str | None:
        rs = [r["resolved"] for r in self.expl.get(sid, []) if int(r["expl_id"].split("#")[-1]) <= 3]
        if not rs:
            return None
        top, c = Counter(rs).most_common(1)[0]
        return top if c >= 2 else "no_majority"

    def name(self, text_id: str, target: str, mode: str = "NAME") -> int | None:
        r = self.text.get(f"{mode}|{text_id}")
        if r is None or r["resolved"] is None:
            return None
        return int(r["resolved"] == target)

    def name_label(self, text_id: str, mode: str = "NAME") -> str | None:
        r = self.text.get(f"{mode}|{text_id}")
        return None if r is None else r["resolved"]


def paired(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [u for u in units if u["x"] is not None and u["y"] is not None]


def test_block(units: list[dict[str, Any]], thr: float | None = 0.30) -> dict[str, Any]:
    u = paired(units)
    m = mcnemar_exact([v["x"] for v in u], [v["y"] for v in u])
    stat = lambda s: (float(np.mean([v["x"] for v in s]) - np.mean([v["y"] for v in s]))) if s else None
    m["cluster_bootstrap"] = cluster_bootstrap(u, stat) if u else None
    m["x_rate"] = rate([v["x"] for v in u])
    m["y_rate"] = rate([v["y"] for v in u])
    if thr is not None:
        m["pass"] = bool(m["effect"] is not None and m["effect"] >= thr and m["p"] < 0.05)
    return m


def by(units: list[dict[str, Any]], key: str) -> dict[str, Any]:
    g: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for u in paired(units):
        g[u[key]].append(u)
    return {k: {"n": len(v), "x": float(np.mean([a["x"] for a in v])), "y": float(np.mean([a["y"] for a in v]))}
            for k, v in sorted(g.items())}


def main() -> dict[str, Any]:
    d = Data()
    out: dict[str, Any] = {"eligible": [t for t, v in d.tasks.items() if v.get("eligible")]}
    # ---------------------------------------------------------------- N1 primary
    def n1_units(templates=PRIMARY_W, field="planned", drop=False, y_mode="NAME"):
        us = []
        for t in out["eligible"]:
            D, Y = d.tasks[t]["default"], d.tasks[t]["Ystar"]
            for w in templates:
                for p in POS4:
                    sid = f"{t}|ban|{D}|{w}|{p}"
                    us.append({"task": t, "template": w, "position": p, "sid": sid,
                               "x": d.x(sid, Y, field, drop), "y": d.name(f"{t}|ban|{D}|{w}|PREFILL", Y, y_mode)})
        return us
    u1 = n1_units()
    N1 = test_block(u1)
    N1["per_task"] = by(u1, "task")
    N1["per_position"] = by(u1, "position")
    N1["W4"] = test_block(n1_units(("W4",)), None)
    N1["sens_mentioned"] = test_block(n1_units(field="mentioned"))
    N1["sens_drop_unresolved"] = test_block(n1_units(drop=True))
    per_expl = []
    for u in u1:
        t = u["task"]
        Y = d.tasks[t]["Ystar"]
        for r in d.expl.get(u["sid"], [])[:3]:
            per_expl.append({"task": t, "x": int(r["resolved"] == Y), "y": u["y"]})
    N1["sens_per_explanation"] = test_block(per_expl) if per_expl else None
    out["N1"] = N1
    # ---------------------------------------------------------------- N1-swap / rand / predict
    sw = []
    for u in u1:
        t, w, p = u["task"], u["template"], u["position"]
        Y = d.tasks[t]["Ystar"]
        sw.append({"task": t, "template": w, "position": p, "x": u["x"], "y": d.x(f"{t}|twin|-|{w}|{p}", Y)})
    S = test_block(sw, None)
    pr = paired(sw)
    rng = np.random.default_rng(7)
    obs = np.mean([v["x"] - v["y"] for v in pr]) if pr else 0.0
    diffs = np.array([v["x"] - v["y"] for v in pr], dtype=float)
    perm = [np.mean(diffs * rng.choice([-1, 1], size=len(diffs))) for _ in range(10000)] if len(diffs) else [0.0]
    S["permutation_p"] = float((np.sum(np.abs(perm) >= abs(obs) - 1e-12) + 1) / (len(perm) + 1))
    out["N1_swap"] = S
    rd = []
    for u in u1:
        if u["position"] not in ("READ", "SPEC-1"):
            continue
        t, w, p = u["task"], u["template"], u["position"]
        rd.append({"task": t, "x": u["x"], "y": d.x(f"{t}|rand|-|{w}|{p}", d.tasks[t]["Ystar"])})
    out["N1_rand"] = test_block(rd, None)
    out["N1_predict"] = test_block(n1_units(y_mode="PREDICT"), None)
    # ---------------------------------------------------------------- N2 default (twin)
    def n2_units(templates=PRIMARY_W):
        us = []
        for t, v in d.tasks.items():
            D = v.get("default")
            if not D or not v.get("regate_pass", True):
                continue
            for w in templates:
                for p in POS4:
                    sid = f"{t}|twin|-|{w}|{p}"
                    us.append({"task": t, "template": w, "position": p, "x": d.x(sid, D),
                               "y": d.name(f"{t}|twin|-|{w}|PREFILL", D)})
        return us
    u2 = n2_units()
    N2 = test_block(u2)
    N2["per_task"] = by(u2, "task")
    N2["per_position"] = by(u2, "position")
    N2["W4"] = test_block(n2_units(("W4",)), None)
    out["N2_default"] = N2
    # ---------------------------------------------------------------- N3 forced positive control
    n3: dict[str, Any] = {}
    for t, v in d.tasks.items():
        if not v.get("regate_pass", True):
            continue  # a task failing the style re-gate is excluded from every readout test
        rows = []
        for m in v.get("forced_readout_modes", []):
            for w in ("W1", "W2", "W3", "W4", "W5"):
                for p in POS4:
                    xx = d.x(f"{t}|forced|{m}|{w}|{p}", m)
                    if xx is not None:
                        rows.append({"mode": m, "x": xx, "y": d.name(f"{t}|forced|{m}|{w}|PREFILL", m)})
        if rows:
            n3[t] = {"nla": rate([r["x"] for r in rows]),
                     "text_only": rate([r["y"] for r in rows if r["y"] is not None]),
                     "per_mode": {m: rate([r["x"] for r in rows if r["mode"] == m]) for m in v["forced_readout_modes"]},
                     "pass_0.7": bool(rate([r["x"] for r in rows])["rate"] >= 0.7)}
    out["N3_forced"] = {"tasks": n3, "n_tasks_pass": sum(v["pass_0.7"] for v in n3.values())}
    # ---------------------------------------------------------------- N4 seed
    seed_states = [s for s, r in d.idx.items() if r.get("condition") == "seed" and r["kind"] == "PREFILL"]
    realised = Counter(r["label"] for r in d.labels.values() if r.get("arm") == "SEED" and r.get("passed"))
    out["N4_seed"] = {"nla_planned_majority": dict(Counter(d.planned_majority(s) for s in seed_states)),
                      "text_only_name": dict(Counter(d.name_label(f"T2|seed|-|{w}|PREFILL") for w in ("W1", "W2", "W3", "W4", "W5"))),
                      "text_only_predict": dict(Counter(d.name_label(f"T2|seed|-|{w}|PREFILL", "PREDICT") for w in ("W1", "W2", "W3", "W4", "W5"))),
                      "realised_correct_labels": dict(realised)}
    # ---------------------------------------------------------------- N5 / N6 generated tokens
    gen_units = []
    for sid, r in d.idx.items():
        if r["kind"] != "GEN":
            continue
        lab = d.labels.get(r["sample_id"])
        if lab is None or not d.tasks.get(r["task"], {}).get("regate_pass", True):
            continue
        t = r["task"]
        tid = f"{t}|{r['condition']}|{r.get('mode') or '-'}|{r['template']}|{r['position']}|{r['slot']}"
        gen_units.append({"task": t, "condition": r["condition"], "g": int(r["position"][1:]), "sample_id": r["sample_id"],
                          "realised": lab["label"], "passed": bool(lab.get("passed")), "mixed": bool(r.get("mixed")),
                          "x": d.x(sid, lab["label"]), "y_name": d.name(tid, lab["label"]),
                          "y_pred": d.name(tid, lab["label"], "PREDICT"), "name_label": d.name_label(tid)})
    first_id: dict[str, int] = {}
    for u in sorted(gen_units, key=lambda u: u["g"]):
        if u["name_label"] not in NAMED_EXCL and u["sample_id"] not in first_id:
            first_id[u["sample_id"]] = u["g"]
    for u in gen_units:
        u["pre_identifying"] = u["g"] < first_id.get(u["sample_id"], 10 ** 6)
    curves: dict[str, Any] = {}
    for cond in sorted({u["condition"] for u in gen_units}):
        curves[cond] = {}
        for g in (1, 2, 4, 8, 16):
            us = [u for u in gen_units if u["condition"] == cond and u["g"] == g and u["pre_identifying"]]
            curves[cond][f"g{g}"] = {"nla": rate([u["x"] for u in us if u["x"] is not None]),
                                     "text_name": rate([u["y_name"] for u in us if u["y_name"] is not None]),
                                     "text_predict": rate([u["y_pred"] for u in us if u["y_pred"] is not None])}
    out["N5_gen"] = {"curves_pre_identifying": curves,
                     "share_pre_identifying": float(np.mean([u["pre_identifying"] for u in gen_units])) if gen_units else None}
    n6u = [{"task": u["task"], "x": u["x"], "y": u["y_pred"]} for u in gen_units if u["mixed"] and u["pre_identifying"]]
    out["N6_per_sample"] = test_block(n6u, None)
    out["N6_per_sample"]["n_samples"] = len({u["sample_id"] for u in gen_units if u["mixed"]})
    # ---------------------------------------------------------------- N7 template correlation
    a, b, rows7 = [], [], []
    for t in out["eligible"]:
        D, Y = d.tasks[t]["default"], d.tasks[t]["Ystar"]
        for w in ("W1", "W2", "W3", "W4", "W5"):
            hits = n = 0
            for p in POS4:
                h, k = d.votes(f"{t}|ban|{D}|{w}|{p}", Y)
                hits += h
                n += k
            bl = [r for r in d.labels.values() if r.get("arm") == "BAN" and r["task"] == t and r.get("template") == w]
            if n and bl:
                a.append(hits / n)
                b.append(sum(bool(r.get("passed")) and r["label"] == Y for r in bl) / len(bl))
                rows7.append({"task": t, "template": w, "nla_rate": hits / n, "realised_Ystar_share": b[-1]})
    out["N7_template"] = spearman(a, b) | {"rows": rows7}
    # ---------------------------------------------------------------- N8 ban-failure tasks
    n8 = {}
    for t, v in d.tasks.items():
        if v.get("default") and not v.get("Ystar") and v.get("regate_pass", True):
            D = v["default"]
            sub = Counter(d.name_label(f"{t}|ban|{D}|{w}|PREFILL", "PREDICT") for w in ("W1", "W2", "W3", "W4", "W5"))
            subst = next((k for k, _ in sub.most_common() if k not in NAMED_EXCL and k != D), None)
            sts = [f"{t}|ban|{D}|{w}|{p}" for w in ("W1", "W2", "W3", "W4", "W5") for p in POS4]
            maj = Counter(d.planned_majority(s) for s in sts)
            n8[t] = {"nla_majority": dict(maj), "names_default": rate([d.x(s, D) or 0 for s in sts]),
                     "outside_reader_substitute": subst,
                     "names_outside_substitute": rate([d.x(s, subst) or 0 for s in sts]) if subst else None}
    out["N8_failure"] = n8
    # N8b (paired): on ban-failure tasks the model still implements the forbidden default. Units = ban states
    # (W1/W2/W3/W5 x SPEC-3..READ); x = NLA names the default as planned; y = the outside reader (PREDICT on the
    # visible ban text) predicts the default; y2 = the text-only NAME reader calls the default planned.
    u8, u8n = [], []
    for t, v in d.tasks.items():
        if v.get("default") and not v.get("Ystar") and v.get("regate_pass", True):
            D = v["default"]
            for w in PRIMARY_W:
                for p in POS4:
                    sid = f"{t}|ban|{D}|{w}|{p}"
                    xx = d.x(sid, D)
                    u8.append({"task": t, "x": xx, "y": d.name(f"{t}|ban|{D}|{w}|PREFILL", D, "PREDICT")})
                    u8n.append({"task": t, "x": xx, "y": d.name(f"{t}|ban|{D}|{w}|PREFILL", D)})
    out["N8b_banfail_default_vs_predict"] = test_block(u8)
    out["N8b_banfail_default_vs_name"] = test_block(u8n)
    out["N8b_per_task"] = by(u8, "task")
    # ---------------------------------------------------------------- holm over secondary tests
    ps = {"N1_swap": out["N1_swap"]["p"], "N1_rand": out["N1_rand"]["p"], "N1_predict": out["N1_predict"]["p"],
          "N2_default": out["N2_default"]["p"], "N6_per_sample": out["N6_per_sample"]["p"],
          "N8b_vs_predict": out["N8b_banfail_default_vs_predict"]["p"], "N8b_vs_name": out["N8b_banfail_default_vs_name"]["p"]}
    out["holm_secondary"] = holm({k: v for k, v in ps.items() if v is not None})
    # ---------------------------------------------------------------- naming table (F2) and judge agreement
    table = defaultdict(lambda: defaultdict(list))
    for sid, r in d.idx.items():
        if r["kind"] not in ("PREFILL", "RAND") or r["task"] not in d.tasks:
            continue
        v = d.tasks[r["task"]]
        tgt = v.get("Ystar") if r["condition"] in ("ban", "rand") else (r.get("mode") if r["condition"] == "forced" else v.get("default"))
        if not tgt:
            continue
        xx = d.x(sid, tgt)
        if xx is not None:
            table[f"{r['condition']}"][r["position"]].append(xx)
    out["naming_table"] = {c: {p: rate(v) for p, v in ps_.items()} for c, ps_ in table.items()}
    agree = {}
    for mode in ("EXPL", "NAME", "PREDICT"):
        k = "predicted" if mode == "PREDICT" else "planned"
        prs = [(r["J1"][k], r["J2"][k]) for r in d.jud if r["mode"] == mode and r.get("J1") and r.get("J2")]
        if prs:
            agree[mode] = {"n": len(prs), "raw_agreement": float(np.mean([a_ == b_ for a_, b_ in prs])),
                           "kappa_J1_J2": kappa([p[0] for p in prs], [p[1] for p in prs]),
                           "n_J3": sum(1 for r in d.jud if r["mode"] == mode and r.get("J3")),
                           "n_unresolved": sum(1 for r in d.jud if r["mode"] == mode and r["resolved"] == "unresolved")}
    out["judge_agreement"] = agree
    # planned-label distributions per task and condition (F3)
    dist = defaultdict(Counter)
    for sid, r in d.idx.items():
        if r["kind"] in ("PREFILL", "GEN", "RAND") and sid in d.expl:
            for e in d.expl[sid][:3]:
                dist[f"{r['task']}|{r['condition']}"][e["resolved"]] += 1
    out["planned_distribution"] = {k: dict(v) for k, v in dist.items()}
    (ROOT / "results" / "readout.json").write_text(json.dumps(out, indent=1, default=float))
    return out


if __name__ == "__main__":
    res = main()
    print(json.dumps({k: res[k] for k in ("eligible",)}), "N1", {k: res["N1"][k] for k in ("n", "b", "c", "p", "effect", "pass")})
