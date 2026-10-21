#!/usr/bin/env python3
"""9.8 audit: recompute the headline behaviour numbers from data/samples_raw.jsonl + data/labels.jsonl with code that
shares nothing with src/analysis (plain dict counting), compare with results/c2d.json and results/c2f.json, run the
placebo (arm labels shuffled within CRN slots must erase the ADD-vs-RAND and target-vs-random-head contrasts), and
verify the hash chain and that commit #1 precedes the first sample and commit #2 the first S7 ban sample."""

from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = {"T1": "bfs", "T2": "dijkstra", "T03": "full_sort", "T04": "naive", "T06": "hash_set", "T05": "hash_map"}


def jl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def main() -> None:
    raw = jl(ROOT / "data" / "samples_raw.jsonl")
    labs = {r["key"]: r for r in jl(ROOT / "data" / "labels.jsonl")}
    rows = []
    for r in raw:
        k = f"{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}"
        if k in labs:
            rows.append({"task": r["task"], "arm": r["arm"], "w": r["template"], "k": int(r["sample_id"]),
                         "label": labs[k]["label"], "block": r["block_id"], "utc": r["utc"]})
    out: dict = {"n_rows": len(rows), "mismatches": []}
    # (1) avoidance per task x arm
    c2d = json.loads((ROOT / "results" / "c2d.json").read_text())
    for t, v in c2d["per_task"].items():
        for arm, s in v["arms"].items():
            rs = [r for r in rows if r["task"] == t and r["arm"] == arm and r["label"] not in ("invalid", "disputed")]
            if not rs:
                continue
            av = sum(r["label"] != DEFAULT[t] for r in rs) / len(rs)
            if abs(av - s["avoidance"]) > 1e-9:
                out["mismatches"].append({"task": t, "arm": arm, "rederived": av, "reported": s["avoidance"]})
    out["n_checked_arms"] = sum(len(v["arms"]) for v in c2d["per_task"].values())
    # (2) placebo: shuffle ADD/RAND arm labels within slots -> contrast ~ 0
    rnd = random.Random(0)
    plac = {}
    for t in DEFAULT:
        for al in ("1.0", "2.0"):
            for s in (9001, 9002, 9003):
                A = {(r["w"], r["k"]): r["label"] for r in rows if r["task"] == t and r["arm"] == f"ADD_a{al}" and r["k"] < 10}
                B = {(r["w"], r["k"]): r["label"] for r in rows if r["task"] == t and r["arm"] == f"RAND{s}_a{al}"}
                keys = [k for k in A if k in B and A[k] not in ("invalid", "disputed") and B[k] not in ("invalid", "disputed")]
                if not keys:
                    continue
                obs = sum((A[k] != DEFAULT[t]) - (B[k] != DEFAULT[t]) for k in keys) / len(keys)
                sh = []
                for _ in range(500):
                    d = 0
                    for k in keys:
                        a, b = (A[k], B[k]) if rnd.random() < 0.5 else (B[k], A[k])
                        d += (a != DEFAULT[t]) - (b != DEFAULT[t])
                    sh.append(d / len(keys))
                plac[f"{t}|a{al}|{s}"] = {"observed_contrast": obs, "placebo_mean": sum(sh) / len(sh),
                                          "placebo_abs_q95": sorted(abs(x) for x in sh)[int(0.95 * len(sh))]}
    out["placebo_c2d"] = plac
    out["placebo_c2d_mean_abs"] = (sum(abs(v["placebo_mean"]) for v in plac.values()) / len(plac)) if plac else None
    plf = {}
    for t in ("T1", "T2"):
        A = {(r["w"], r["k"]): r["label"] for r in rows if r["task"] == t and r["arm"] == "HEADS_target"}
        for s in (7101, 7102, 7103):
            B = {(r["w"], r["k"]): r["label"] for r in rows if r["task"] == t and r["arm"] == f"HEADS_rand{s}"}
            keys = [k for k in A if k in B and A[k] not in ("invalid", "disputed") and B[k] not in ("invalid", "disputed")]
            if not keys:
                continue
            obs = sum((A[k] == DEFAULT[t]) - (B[k] == DEFAULT[t]) for k in keys) / len(keys)
            sh = []
            for _ in range(500):
                d = 0
                for k in keys:
                    a, b = (A[k], B[k]) if rnd.random() < 0.5 else (B[k], A[k])
                    d += (a == DEFAULT[t]) - (b == DEFAULT[t])
                sh.append(d / len(keys))
            plf[f"{t}|{s}"] = {"observed_contrast": obs, "placebo_mean": sum(sh) / len(sh)}
    out["placebo_c2f"] = plf
    # (3) hash chain + commit timing
    prev = "0" * 64
    first = {}
    breaks = 0
    for line in (ROOT / "commitments.log").read_text().splitlines():
        if not line.strip():
            continue
        utc, rp, h, chain, tag = line.split()[:5]
        if hashlib.sha256((prev + h + utc + rp).encode()).hexdigest() != chain:
            breaks += 1
        first.setdefault(tag, utc)
        prev = chain
    s_first = min(r["utc"] for r in raw)
    s7 = [r["utc"] for r in raw if r["block_id"].startswith("S7")]
    out["hash_chain"] = {"breaks": breaks, "first_commit_utc": first}
    out["commit1_precedes_first_sample"] = first.get("commit1", "9") < s_first
    out["commit2_precedes_first_S7_ban_sample"] = bool(s7) and first.get("commit2", "9") < min(s7)
    out["first_sample_utc"] = s_first
    out["first_S7_sample_utc"] = min(s7) if s7 else None
    out["note"] = ("U7 (engine validation, T2 ban with exp8 keys) ran after commit #1 and before commit #2, as the "
                   "testing plan specifies; its rows are excluded from every analysis.")
    out["pass"] = (not out["mismatches"]) and breaks == 0 and out["commit1_precedes_first_sample"] and \
        out["commit2_precedes_first_S7_ban_sample"]
    (ROOT / "results" / "rederive.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if not k.startswith("placebo_c2d")}, indent=1)[:3000])


if __name__ == "__main__":
    sys.exit(main())
